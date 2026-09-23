#!/usr/bin/env python3
"""Generate a point-by-point rebuttal letter from reviews + the final paper.

Standalone tool (outside the pipeline): after reviews come in — real
reviewer reports, or a simulated review from our own `autoraters` — draft
responses grounded in the paper's own text. Two modes:

  1. --reviews_file PATH   reviews as markdown/text, or JSON (one review dict
                           or a list of them, e.g. agent_review output)
  2. --self_review         no reviews at hand: generate one simulated review
                           via autoraters.agent_review first, then rebut it

Every drafted response is classified and grounded:
  - factual-clarification  reviewer misread -> quote the exact passage
  - wording-change         propose the concrete new sentence
  - new-experiment         describe it, marked [NEW EXPERIMENT]; never claim
                           it was run
  - limitation-acknowledge concede precisely, state scope
  - out-of-scope           politely boundary it
Never fabricate results; never promise what the paper doesn't show.

Usage:
  python rebuttal_writer.py --paper_dir paper_output_trace_rtl \
      --reviews_file reviews.md
  python rebuttal_writer.py --paper_dir paper_output_x --self_review \
      --model_name glm-5.3
"""

import argparse
import json
import os
import re
import sys
import threading

from utils.llm_backend_utils import call_llm_with_text_prompt

CONCERN_TYPES = [
    "factual-clarification",
    "wording-change",
    "new-experiment",
    "limitation-acknowledge",
    "out-of-scope",
]


def _llm(prompt, model_name, timeout_sec=600, system=None):
    """Deadline-wrapped LLM call (daemon thread — a wedged request must not
    hang the tool; see content_refinement_agent._llm_call_with_deadline)."""
    holder = {}

    def run():
        try:
            kwargs = {
                "prompt": prompt,
                "model_name": model_name,
                "return_json": False,
                "result_parsing_func": lambda x: x,
                "check_parsed_response_not_none": False,
            }
            if system:
                kwargs["generation_configs"] = {"system_instruction": system}
            holder["res"] = call_llm_with_text_prompt(**kwargs)
        except Exception as e:
            holder["err"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout_sec)
    if "res" in holder:
        return holder["res"]["raw_response"]
    if "err" in holder:
        raise holder["err"]
    raise TimeoutError(f"LLM call exceeded {timeout_sec}s")


def _load_paper_tex(paper_dir):
    """final_refined_paper.tex (refinement workdir) -> raw_draft_paper.tex."""
    for cand in (
        os.path.join(paper_dir, "content_refinement_workdir", "final_refined_paper.tex"),
        os.path.join(paper_dir, "latex_writeup", "raw_draft_paper.tex"),
    ):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                return f.read(), cand
    raise FileNotFoundError(f"No paper .tex found under {paper_dir}")


def _paper_title(tex):
    m = re.search(r"\\title\{([^}]*)\}", tex)
    return m.group(1) if m else "(title not found)"


def _load_reviews(path):
    """Accept JSON (dict / list of agent_review dicts) or free text. Returns a
    list of review blocks (plain text each)."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [raw.strip()] if raw.strip() else []

    if isinstance(data, dict):
        data = [data]

    blocks = []
    for r in data:
        if not isinstance(r, dict):
            continue
        lines = []
        for k in ("Summary", "Strengths", "Weaknesses", "Questions",
                  "Limitations", "Soundness", "Presentation", "Contribution",
                  "Overall", "Confidence", "Verdicts", "Decision"):
            if k in r:
                lines.append(f"## {k}\n{json.dumps(r[k], ensure_ascii=False, indent=1)}")
        blocks.append("\n\n".join(lines) if lines else json.dumps(r, indent=1))
    return blocks


def _self_review(paper_tex, model_name):
    from autoraters.agent_review import perform_review_agentreview

    review = perform_review_agentreview(
        paper_tex, model_name=model_name, num_review_ensemble=1
    )
    return review


def _rebut_one(paper_tex, review_text, model_name):
    """Draft point-by-point responses for one review. Returns a list of
    concern dicts (validated, possibly empty on failure)."""
    prompt = f"""You are drafting a point-by-point REBUTTAL for a paper. Be grounded, precise, and calm — never defensive, never promotional.

REVIEW:
```
{review_text}
```

PAPER (LaTeX source — the ground truth for what the paper does/does not say):
```
{paper_tex}
```

For EVERY distinct concern, weakness, or question in the review:
1. "quote": the reviewer's concern, quoted or closely paraphrased (one sentence).
2. "type": exactly one of: factual-clarification (reviewer misread; the paper already answers it), wording-change (paper text should be adjusted), new-experiment (only new experiments can answer it), limitation-acknowledge (valid limitation; concede precisely and state scope), out-of-scope (beyond what this paper claims).
3. "response": 2-6 sentences. HARD RULES:
   - Every factual statement must be grounded in the paper text above; when correcting a misreading, quote or cite the exact passage (section/equation/table).
   - For wording-change: include the concrete replacement sentence.
   - For new-experiment: describe the experiment; write the marker [NEW EXPERIMENT] and do NOT claim it was run or report invented numbers.
   - Never fabricate results, numbers, citations, or author intent.
4. "change": the specific edit to make in the revision (file section + new text), or "none".

Answer every concern — skipping one is the fastest way to lose a reviewer.

Reply ONLY with JSON:
{{"concerns": [{{"quote": "...", "type": "...", "response": "...", "change": "..."}}]}}"""
    raw = _llm(prompt, model_name)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return []
    try:
        concerns = json.loads(m.group(0)).get("concerns", [])
    except json.JSONDecodeError:
        return []
    return [
        c for c in concerns
        if isinstance(c, dict) and c.get("quote") and c.get("response")
        and c.get("type", "x") in CONCERN_TYPES
    ]


def _render_letter(title, blocks):
    """blocks: list of (review_idx, source_label, [concern dicts])."""
    out = [f"# Rebuttal — {title}", "",
           "One response per concern. `[NEW EXPERIMENT]` marks experiments "
           "proposed but not run; no numbers are reported for them.", ""]
    total = 0
    for idx, label, concerns in blocks:
        out.append(f"## Review {idx} ({label}) — {len(concerns)} concern(s)")
        out.append("")
        for i, c in enumerate(concerns, 1):
            total += 1
            out.append(f"### R{idx}.{i} [{c['type']}] — {c['quote']}")
            out.append("")
            out.append(c["response"])
            if c.get("change") and c["change"].lower() != "none":
                out.append("")
                out.append(f"**Planned change:** {c['change']}")
            out.append("")
    if total == 0:
        out.append("(No concerns were parsed from the reviews.)")
    return "\n".join(out), total


def main():
    ap = argparse.ArgumentParser(description="Point-by-point rebuttal writer.")
    ap.add_argument("--paper_dir", required=True)
    ap.add_argument("--reviews_file", default=None,
                    help="reviews as .md/.txt or JSON (agent_review format)")
    ap.add_argument("--self_review", action="store_true",
                    help="generate a simulated review first (autoraters), then rebut it")
    ap.add_argument("--model_name", default="glm-5.3")
    ap.add_argument("--out", default=None, help="output .md (default: <paper_dir>/rebuttal/rebuttal_letter.md)")
    args = ap.parse_args()

    if not args.reviews_file and not args.self_review:
        ap.error("provide --reviews_file or --self_review")

    tex, tex_path = _load_paper_tex(args.paper_dir)
    title = _paper_title(tex)
    print(f"paper: {tex_path} ({len(tex)} chars), title: {title!r}")

    if args.reviews_file:
        review_blocks = _load_reviews(args.reviews_file)
        print(f"loaded {len(review_blocks)} review block(s) from {args.reviews_file}")
        if not review_blocks:
            print("no review content found; aborting.")
            return 1
        blocks = [(i + 1, "provided", b) for i, b in enumerate(review_blocks)]
    else:
        print("generating simulated review (--self_review)...")
        review = _self_review(tex, args.model_name)
        with open(os.path.join(args.paper_dir, "rebuttal", "self_review.json")
                  if os.path.isdir(os.path.join(args.paper_dir, "rebuttal"))
                  else "/tmp/self_review.json", "w", encoding="utf-8") as f:
            json.dump(review, f, indent=2, ensure_ascii=False)
        blocks = [(1, "self-review", json.dumps(review, indent=1))]

    out_blocks = []
    for idx, label, review_text in blocks:
        print(f"drafting rebuttal for review {idx} ({label})...")
        concerns = _rebut_one(tex, review_text, args.model_name)
        print(f"  -> {len(concerns)} concern(s) answered")
        out_blocks.append((idx, label, concerns))

    letter, total = _render_letter(title, out_blocks)
    out_path = args.out or os.path.join(args.paper_dir, "rebuttal", "rebuttal_letter.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(letter)
    print(f"\nrebuttal letter ({total} responses) -> {out_path}")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
