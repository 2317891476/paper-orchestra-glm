# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Reusable literature enrichment for an already-generated paper.

Input: a paper output dir (has latex_writeup/raw_draft_paper.tex + references.bib).
Process: LLM finds citation needs -> multi-source search (DeepXiv+S2+arXiv) for new papers ->
append bib -> LLM inserts \\cite + brief contextual sentences -> recompile.
"""

import argparse
import json
import os
import re
import shutil

from utils.llm_backend_utils import call_llm_with_text_prompt
from utils.pdf_utils import compile_latex
from utils.paper_search import search_papers, make_bib_entry, _make_key, _coerce_authors, _normalize_title

MODEL = "glm-5.2"

NEED_PROMPT = """You are a senior researcher. Analyze the LaTeX paper below and find places that
need citation support. Output a JSON list of search queries (strings) that would find relevant
prior work to cite — focus on claims, methods, baselines, datasets, or concepts mentioned without
a citation. Up to 8 queries, each a concise web-search-style phrase (English).
Return ONLY json: ```json
["query 1", "query 2", ...]
```

Paper:
```latex
{tex_head}
```
"""

INSERT_PROMPT = """You are enhancing a LaTeX paper's related-work grounding. The paper source and
a set of NEW candidate references (key -> title/abstract) are below. Your job is to MATERIALLY
increase the citation count by weaving these new references into the paper.

HARD REQUIREMENTS:
- You MUST insert at least **{min_cite}** new \\cite{{key}} commands using the new keys.
- Cite at least {min_cite} DISTINCT new keys. Spread them across Introduction, Related Work, and
  Methodology/Background where the cited concept is mentioned.
- Where a claim/concept currently has NO citation, add \\cite{{newkey}} (or \\cite{{newkey,existing}}).
- You MAY add 1 new "Related Work" / "Background" paragraph (a few sentences) that cites 3-5 new
  keys together, if the paper's related-work grounding is thin.
- You MAY add a brief contextual clause (e.g., ", an approach also explored in prior work \\cite{{k}}")
  to existing sentences — keep edits minimal and faithful (no fabricated results/claims).

KEEP UNCHANGED: the preamble (\\documentclass, packages), all math, \\label, the \\title/\\abstract,
and the \\bibliography line. Do NOT add \\bibitem (keys are already in references.bib).

Output the COMPLETE updated .tex file. Do NOT output anything else.

NEW CANDIDATES (cite these):
{candidates}

LATEX SOURCE:
```latex
{tex}
```
"""


def _strip_fence(s: str) -> str:
    m = re.search(r"```(?:latex|tex)?\s*(.*?)\s*```", s.strip(), re.DOTALL)
    return m.group(1).strip() if m else s.strip()


def _existing_keys(tex: str, bib: str) -> set:
    keys = set(re.findall(r"\\cite\{([^}]+)\}", tex))
    for k in re.findall(r"@\w+\{([^,]+),", bib):
        keys.add(k.strip())
    return {k.strip() for k in keys for k in k.split(",")}


def _cleanup_orphans(tex_path: str, bib_path: str) -> int:
    """Remove bib entries that are never \\cite'd in the tex. Returns count removed."""
    tex = open(tex_path, encoding="utf-8").read()
    bib = open(bib_path, encoding="utf-8").read()
    cited = set()
    for c in re.findall(r"\\cite\{([^}]+)\}", tex):
        for k in c.split(","):
            cited.add(k.strip())
    # split bib into entries (each starts with @type{key,)
    entries = re.split(r"(?=@\w+\{)", bib)
    kept = []
    removed = 0
    for entry in entries:
        m = re.match(r"@\w+\{([^,]+),", entry)
        if m and m.group(1).strip() not in cited:
            removed += 1
            print(f"    orphan removed: {m.group(1).strip()}")
            continue
        kept.append(entry)
    if removed:
        open(bib_path, "w", encoding="utf-8").write("".join(kept))
    return removed


def main():
    ap = argparse.ArgumentParser(description="Enrich an existing paper with more citations.")
    ap.add_argument("--paper_dir", required=True, help="paper_output_X dir (has latex_writeup/)")
    ap.add_argument("--cutoff", default=None, help="YYYY-MM cutoff for new refs")
    ap.add_argument("--max_new", type=int, default=15, help="max new references to add")
    ap.add_argument("--model_name", default=MODEL)
    ap.add_argument("--template_dir", default=None, help="templates/<conf> for format check")
    args = ap.parse_args()

    lw = os.path.join(args.paper_dir, "latex_writeup")
    tex_path = os.path.join(lw, "raw_draft_paper.tex")
    bib_path = os.path.join(lw, "references.bib")
    if not os.path.exists(tex_path):
        print(f"Error: {tex_path} not found"); return
    tex = open(tex_path, encoding="utf-8").read()
    bib = open(bib_path, encoding="utf-8").read() if os.path.exists(bib_path) else ""

    existing = _existing_keys(tex, bib)
    print(f"Existing citation keys: {len(existing)}")

    # 1. citation-need queries
    print("Step 1: identifying citation needs...")
    head = tex[:9000]
    resp = call_llm_with_text_prompt(
        prompt=NEED_PROMPT.format(tex_head=head), model_name=args.model_name,
        return_json=True, check_parsed_response_not_none=False,
    )
    queries = resp.get("parsed_response") or []
    if isinstance(queries, dict):
        queries = queries.get("queries") or list(queries.values())
    queries = [str(q) for q in queries if q][:8]
    print(f"  -> {len(queries)} search queries: {queries}")

    # 2. multi-source search
    print("Step 2: multi-source search (DeepXiv + S2 + arXiv)...")
    new_papers = []
    seen_titles = set()
    for q in queries:
        for r in search_papers(q, limit=6, cutoff_date=args.cutoff):
            t = _normalize_title(r["title"])
            if not t or t in seen_titles:
                continue
            key = _make_key(_coerce_authors(r["authors"]), r["year"], r["title"])
            if key in existing:
                continue
            seen_titles.add(t)
            r["_key"] = key
            new_papers.append(r)
        if len(new_papers) >= args.max_new:
            break
    new_papers = new_papers[: args.max_new]
    print(f"  -> {len(new_papers)} new candidate papers")

    if not new_papers:
        print("No new papers found; nothing to enrich."); return

    # 3. append bib entries
    added_keys = []
    bib_block = []
    for r in new_papers:
        entry = make_bib_entry(r)  # already uses _make_key == r["_key"]
        bib_block.append(entry)
        added_keys.append(r["_key"])
    with open(bib_path, "a", encoding="utf-8") as f:
        f.write("\n\n% === enriched references (auto-added) ===\n" + "\n\n".join(bib_block) + "\n")
    print(f"  appended {len(added_keys)} entries to references.bib")

    # 4. LLM insert citations
    print("Step 3: inserting citations into the paper...")
    cand_str = "\n".join(
        f"- {r['_key']}: {r['title']} — {(r['abstract'] or '')[:240]}"
        for r in new_papers
    )
    resp = call_llm_with_text_prompt(
        prompt=INSERT_PROMPT.format(candidates=cand_str, tex=tex, min_cite=min(10, len(new_papers))),
        model_name=args.model_name, return_json=False,
        check_parsed_response_not_none=False,
    )
    enriched = _strip_fence(resp.get("raw_response", ""))
    if not enriched.strip() or "\\documentclass" not in enriched:
        print("Warning: enriched output malformed; keeping original tex."); return

    # backup + write
    shutil.copy(tex_path, tex_path + ".bak")
    open(tex_path, "w", encoding="utf-8").write(enriched)

    # 4.5 cleanup: remove orphan bib entries (in bib but never \cite'd) -> clean numbering
    removed = _cleanup_orphans(tex_path, bib_path)
    if removed:
        print(f"  cleanup: removed {removed} orphan bib entries (uncited -> numbering now clean)")

    # 5. recompile
    print("Step 4: recompiling...")
    compile_latex(lw, os.path.join(args.paper_dir, "final_paper_enriched.pdf"), "raw_draft_paper")
    ok = os.path.exists(os.path.join(args.paper_dir, "final_paper_enriched.pdf"))
    n_new_cite = len(re.findall(r"\\cite\{[^}]+\}", enriched)) - len(re.findall(r"\\cite\{[^}]+\}", tex))
    print(f"\nDONE — {'PDF OK' if ok else 'PDF FAILED'}")
    print(f"  new refs in bib: {len(added_keys)}")
    print(f"  new \\cite added (approx): {max(0, n_new_cite)}")
    print(f"  keys: {added_keys}")
    print(f"  original backed up to {tex_path}.bak")

    # 6. format check (closed-loop QA)
    if args.template_dir:
        import subprocess as _sp
        print("\n" + "=" * 60)
        print("  FORMAT CHECK (auto after enrichment)")
        print("=" * 60)
        try:
            _sp.run(["python3", "check_paper.py",
                     "--paper_dir", args.paper_dir,
                     "--template_dir", args.template_dir], timeout=120)
        except Exception as e:
            print(f"  (format check skipped: {e})")


if __name__ == "__main__":
    main()
