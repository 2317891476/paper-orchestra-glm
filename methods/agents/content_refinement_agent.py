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

import os
import threading
import traceback
import json
import shutil

from utils.pdf_utils import compile_latex, load_paper, pdf_to_grid_images
from utils.llm_backend_utils import (
    call_llm_with_text_prompt,
    call_llm_with_pdf,
    call_llm_with_images,
    parse_latex_results,
    parse_json_latex_response,
)

from autoraters.agent_review import perform_review_agentreview

from methods.prompts.content_refinement_agent import (
    content_refinement_agent_system_prompt,
)


class ContentRefinementAgent:
    def __init__(
        self,
        experimental_log_path: str,
        citation_map_path: str,
        guidelines_path: str,
        model_name: str = "gemini-3.1-pro-preview",
        max_reflections: int = 3,
        work_dir: str = "./paper_workspace",
    ):
        """
        Agent responsible for refining a paper by dynamically generating reviews
        and addressing feedback in a loop.
        """
        self.model_name = model_name
        self.max_reflections = max_reflections
        self.system_prompt = content_refinement_agent_system_prompt
        self.work_dir = work_dir

        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs(
            os.path.join(self.work_dir, "pdf_screenshots", "content_refinement"),
            exist_ok=True,
        )
        os.makedirs(
            os.path.join(self.work_dir, "pdf_screenshots", "format_refinement"),
            exist_ok=True,
        )
        os.makedirs(os.path.join(self.work_dir, "peer_reviews"), exist_ok=True)
        print(f" >> Work directory: {self.work_dir}")

        self.experimental_log_path = experimental_log_path
        self.guidelines_path = guidelines_path
        self.citation_map_path = citation_map_path

        self.worklogs = {}
        self.format_worklogs = {}
        self.current_tex = ""
        self.initial_score = 0
        self.current_score = 0

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f" >> Warning: File not found at {path}")
            return ""

    def _get_peer_review(self, pdf_path: str, iteration_label: str) -> dict:
        """Helper to call the external reviewer."""
        print(f" >> [AgentReview] Generating feedback for {iteration_label} paper...")
        try:
            paper_text = load_paper(pdf_path=pdf_path)

            review = perform_review_agentreview(
                text=paper_text,
                model_name=self.model_name,
            )

            score = review.get("Overall", 0)
            print(f" >> [Reviewer] Score for {iteration_label}: {score}/10")

            version_name = "v0" if iteration_label == "initial" else iteration_label
            review_path = os.path.join(
                self.work_dir, "peer_reviews", f"review_{version_name}.json"
            )
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(review, f, indent=4)

            return review, float(score)
        except Exception as e:
            print(f" >> [Reviewer] Error generating review: {e}")
            traceback.print_exc()
            return {"Error": str(e), "Overall": 0}, 0.0

    def _get_formatting_review(self, pdf_path: str, iteration_label: str) -> dict:
        """Helper to call VLM for formatting feedback."""
        print(
            f" >> [VLM] Generating formatting feedback for {iteration_label} paper..."
        )
        try:
            v_num = iteration_label.split("_")[-1]
            screenshots_dir = os.path.join(
                self.work_dir, "pdf_screenshots", "format_refinement", f"v{v_num}"
            )
            image_paths = pdf_to_grid_images(pdf_path, screenshots_dir)

            guidelines = self._read_file(self.guidelines_path)

            prompt = (
                """
Analyze the provided page images of a research paper for formatting issues.
You must strictly follow the provided formatting guidelines and examples. Do not create rules based on your own assumptions or general knowledge if they are not explicitly supported by the guidelines or contradicted by the examples.

You must output the status for EVERY SINGLE figure and table found in the paper, and then list any other text content or layout issues.
Pay attention to column margins and page edges. Only report issues if a figure or table clearly overflows into the gutter or margin. Do not flag figures or tables that are simply filling the column width fully.

Formatting Guidelines:
"""
                + guidelines
                + """

Respond in JSON format with the following structure:
```json
{
  "figure_and_tables": {
    "Figure 1": {
      "detected_issue": "The figure is too wide and spills into the right margin.",
      "suggested_fix": "Use `[width=\\\\linewidth]` in `\\\\includegraphics` to scale the figure to the column width."
    },
    "Table 1": {
      "detected_issue": "None",
      "suggested_fix": "None"
    },
    # ...
  },
  "other_issues": [
    {
      "page": "Integer (page number starting from 1)",
      "element": "String ('Section x, Paragraph y' or other specific location details)",
      "detected_issue": "String describing the layout or text content issue",
      "suggested_fix": "String suggesting the fix"
    },
    # ...
  ]
}
```
"""
            )
            response_dict = call_llm_with_images(
                prompt=prompt,
                images=image_paths,
                model_name=self.model_name,
            )

            formatting_review = response_dict["parsed_response"]

            return formatting_review
        except Exception as e:
            print(
                f" >> [VLM] Image-based formatting review unavailable ({e})."
                " Falling back to text-based review."
            )
            try:
                return self._get_text_formatting_review(pdf_path)
            except Exception as e2:
                print(f" >> [Text review] also failed: {e2}")
                traceback.print_exc()
                return {"Error": str(e)}

    def _get_text_formatting_review(self, pdf_path: str) -> dict:
        """Text-only formatting review for backends without vision support.

        Feeds the LLM machine-truth signals (overfull warnings from the newest
        compile log, page count) plus the figure/table inventory parsed from the
        current LaTeX, and asks for the same JSON schema as the VLM review.
        """
        import re
        import subprocess

        def _sh(cmd):
            try:
                return subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60
                ).stdout
            except Exception:
                return ""

        # Machine signals: page count + overfull warnings from the newest log.
        pages = 0
        m = re.search(r"Pages:\s+(\d+)", _sh(["pdfinfo", pdf_path]))
        if m:
            pages = int(m.group(1))

        logs = sorted(
            (f for f in os.listdir(self.work_dir) if f.endswith(".log")),
            key=lambda f: os.path.getmtime(os.path.join(self.work_dir, f)),
        )
        overfull_lines = []
        if logs:
            log_text = self._read_file(os.path.join(self.work_dir, logs[-1]))
            overfull_lines = [
                l.strip()
                for l in log_text.splitlines()
                if l.startswith("Overfull") or l.startswith("Underfull")
            ][:40]

        # Figure/table inventory from the current LaTeX source.
        floats = re.findall(
            r"\\begin\{(figure|table)\*?\}.*?\\caption\{([^}]{0,120})",
            self.current_tex,
            re.DOTALL,
        )
        float_list = "\n".join(
            f"- {kind.capitalize()} (caption starts: '{cap.strip()[:80]}')"
            for kind, cap in floats
        ) or "(none found)"

        guidelines = self._read_file(self.guidelines_path)

        prompt = f"""You are reviewing a compiled research paper for formatting issues WITHOUT page images — you get machine signals instead.

Paper facts:
- Compiled page count: {pages}
- Float inventory (from LaTeX source):
{float_list}
- Overfull/Underfull warnings from the compile log ({len(overfull_lines)} total; log line numbers point into the .tex source):
{chr(10).join(overfull_lines) or "(none)"}

Formatting Guidelines:
{guidelines}

Rules:
- Every reported issue MUST be grounded in the signals above (an Overfull hbox at known lines, a page-count violation vs the guidelines' page budget, a float without width control, etc.). Do NOT invent issues you cannot trace to a signal.
- Use the same JSON schema as below. Set "detected_issue" to "None" for floats with no issue.
- Suggested fixes must be concrete LaTeX fixes (e.g. add `[width=\\\\linewidth]`, wrap in `\\\\resizebox{{\\\\linewidth}}{{!}}{{...}}`, split a paragraph, trim text to meet the page budget).

Respond in JSON format:
```json
{{
  "figure_and_tables": {{
    "Figure 1": {{
      "detected_issue": "...or 'None'",
      "suggested_fix": "...or 'None'"
    }}
  }},
  "other_issues": [
    {{
      "page": "integer",
      "element": "e.g. 'paragraph at source lines 812-820' or 'whole paper'",
      "detected_issue": "...",
      "suggested_fix": "..."
    }}
  ]
}}
```
"""
        response_dict = call_llm_with_text_prompt(
            prompt=prompt,
            model_name=self.model_name,
        )
        return response_dict["parsed_response"]

    def _page_budget_limit(self):
        """page_limit_body from the template's format.yaml, or None."""
        import re

        candidates = [
            os.path.join(os.path.dirname(self.guidelines_path), "format.yaml"),
            os.path.join(self.work_dir, "format.yaml"),
        ]
        for path in candidates:
            if os.path.exists(path):
                m = re.search(
                    r"page_limit_body:\s*(\d+)", self._read_file(path)
                )
                if m:
                    return int(m.group(1))
        return None

    def _pdf_page_count(self, pdf_path: str) -> int:
        import re
        import subprocess

        try:
            out = subprocess.run(
                ["pdfinfo", pdf_path], capture_output=True, text=True, timeout=60
            ).stdout
            m = re.search(r"Pages:\s+(\d+)", out)
            return int(m.group(1)) if m else 0
        except Exception:
            return 0

    def _repair_candidate_tex(self, new_tex: str) -> str:
        """Mechanically repair hallucinated references in a revision.

        Two failure modes seen under compression (2026-09-11, TRACE-RTL):
        the LLM renames the .bib file (`\\bibliography{refs}`) and invents
        figures that exist nowhere (`figures/kintsugi-overview.pdf`). Repairs:
        - `\\bibliographystyle{...}` / `\\bibliography{...}` args copied from
          the current (trusted) tex;
        - any `\\includegraphics` whose path neither exists in the work dir
          (with common extensions) nor appears verbatim in the current tex is
          commented out.
        """
        import re

        for cmd in ("bibliographystyle", "bibliography"):
            m = re.search(r"\\" + cmd + r"\{([^}]+)\}", self.current_tex)
            if m:
                new_tex = re.sub(
                    r"\\" + cmd + r"\{[^}]*\}",
                    lambda _m: m.group(0),
                    new_tex,
                )

        def _keep(match):
            path = match.group("path")
            if path and path in self.current_tex:
                return match.group(0)
            stem = path.replace("figures/", "") if path else ""
            probes = [
                path,
                path + ".pdf",
                path + ".png",
                path + ".jpg",
                "figures/" + stem if stem else None,
                "figures/" + stem + ".pdf" if stem else None,
                "figures/" + stem + ".png" if stem else None,
            ]
            for p in probes:
                if p and os.path.exists(os.path.join(self.work_dir, p)):
                    return match.group(0)
            print(f" >> [repair] commenting out hallucinated figure '{path}'")
            return "% [repair] hallucinated figure removed: " + match.group(0)

        new_tex = re.sub(
            r"\\includegraphics(?:\[[^\]]*\])?\{(?P<path>[^}]+)\}", _keep, new_tex
        )
        return new_tex

    def _compile_is_complete(self, tex_name: str) -> bool:
        """A compile is acceptable only if the tex is complete and TeX didn't abort.

        TeX flushes already-typeset pages even on a fatal abort — a truncated
        LLM revision without \\end{document} yields 'Emergency stop / no legal
        \\end found' yet still writes a partial PDF. So 'a PDF exists' is NOT
        sufficient proof of success; check the log's fatal markers and the
        tex's closing tag too.
        """
        import re

        log = self._read_file(os.path.join(self.work_dir, f"{tex_name}.log"))
        fatal = any(
            m in log
            for m in ("Emergency stop", "Fatal error", "no legal \\end", "Job aborted")
        )
        if fatal:
            return False
        tex = self._read_file(os.path.join(self.work_dir, f"{tex_name}.tex"))
        return "\\end{document}" in tex

    def _llm_call_with_deadline(self, prompt: str, timeout_sec: int = 300):
        """Run a plain-text LLM call under a hard wall-clock deadline.

        The OpenAI SDK's read timeout only guards the gap between bytes, so a
        backend that accepts a request and then trickles nothing (seen on the
        GLM coding endpoint: a section-compression call wedged 28+ min with no
        error) blocks the pipeline forever. A daemon worker thread lets us
        abandon the hung call and carry on; daemon threads also never block
        process exit when the abandoned socket never closes.
        """
        holder = {}

        def _run():
            try:
                holder["res"] = call_llm_with_text_prompt(
                    prompt=prompt,
                    model_name=self.model_name,
                    return_json=False,
                    result_parsing_func=lambda x: x,
                    check_parsed_response_not_none=False,
                    generation_configs={
                        # Compression is mechanical rewriting, not reasoning.
                        # glm-5.3's thinking mode wedges server-side on these
                        # prompts (28+ min, zero bytes; verified 2026-09-11 —
                        # same prompt returns in 10s with thinking disabled).
                        "extra_body": {"thinking": {"type": "disabled"}}
                    },
                )
            except Exception as e:
                holder["err"] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout_sec)
        if "res" in holder:
            return holder["res"]
        if "err" in holder:
            raise holder["err"]
        raise TimeoutError(f"LLM call exceeded {timeout_sec}s wall clock")

    def _split_latex_paragraphs(self, sec: str):
        """Split a LaTeX section into paragraphs at blank lines, but ONLY
        outside \\begin/\\end environments — a table/figure/equation/list stays
        one indivisible piece, so paragraph deletion can never break an
        environment. Returns a list of (is_structural, text) tuples where
        structural = headings, bare labels, floats, equations (never deleted)."""
        import re

        env_re = re.compile(r"\\(begin|end)\{([^}]*)\}")
        head_re = re.compile(
            r"\\(section|subsection|subsubsection|paragraph|label)\b"
        )
        pieces, buf, depth = [], [], 0

        def flush():
            if buf:
                text = "\n".join(buf)
                # Structural = headings at the start, OR any piece that
                # DEFINES a \label — deleting a definition would dangle every
                # \ref to it elsewhere. (Merely \ref-ing a label is harmless to
                # delete: the target stays defined.)
                structural = bool(head_re.match(text.lstrip())) or "\\label{" in text
                pieces.append((structural, text))
                del buf[:]

        for ln in sec.split("\n"):
            if not ln.strip() and depth == 0:
                flush()
                continue
            for m in env_re.finditer(ln):
                if m.group(1) == "begin":
                    depth += 1
                else:
                    depth = max(0, depth - 1)
            buf.append(ln)
        flush()
        return pieces

    def _compress_by_deletion(self, sec: str, target_chars: int, heading: str) -> str:
        """Compress an oversized section by letting the LLM CHOOSE whole
        paragraphs to delete (indexed listing, JSON reply) and applying the
        deletions mechanically. With thinking disabled, glm-5.3 barely shrinks
        a large section by rewriting (39KB section → 99.7%), but ranking
        paragraphs for deletion is a judgment call it does make. One follow-up
        round runs if the first cut misses the target. Returns '' on any
        failure (caller falls back to the rewrite path / original)."""
        import re

        pieces = self._split_latex_paragraphs(sec)
        deletable = [i for i, (s, _) in enumerate(pieces) if not s]
        if len(deletable) < 3:
            return ""
        keep = [True] * len(pieces)

        for round_no in (1, 2):
            cur_len = sum(len(p[1]) for i, p in enumerate(pieces) if keep[i])
            if cur_len <= int(target_chars * 1.1):
                break
            listing = []
            for i, (struct, text) in enumerate(pieces):
                if not keep[i]:
                    continue
                tag = "[S]" if struct else "   "
                listing.append(f"{tag} [{i}] {text[:160].replace(chr(10), ' ⏎ ')}")
            del_chars = [len(pieces[i][1]) for i in deletable if keep[i]]
            avg = max(1, sum(del_chars) // max(1, len(del_chars)))
            need = cur_len - target_chars
            k_guess = max(1, -(-need // avg))  # ceil
            prompt = f"""The LaTeX section "\\section{{{heading}}}" is {cur_len} characters; the venue's page budget allows at most {target_chars} characters, so ≥{need} characters must go.

Paragraph index listing ([S] = STRUCTURAL: headings, labels, floats, equations — MUST be kept):
{chr(10).join(listing)}

Choose whole non-structural paragraphs to DELETE: ones that repeat content covered elsewhere, restate motivation or the abstract, or elaborate minor details. Roughly {k_guess} paragraph deletions are needed — gentle rewording is NOT an option. Losing a citation that appears only inside a deleted motivational paragraph is acceptable.

Reply ONLY with JSON, no other text: {{"delete": [paragraph indices]}}"""
            try:
                resp = self._llm_call_with_deadline(prompt, timeout_sec=240)
            except Exception as e:
                print(f" >> [DeleteRound {round_no}] call failed: {e}")
                break  # keep whatever earlier rounds deleted
            raw = resp["raw_response"]
            m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
            try:
                idxs = json.loads(m.group(0))["delete"] if m else []
                idxs = [i for i in idxs if isinstance(i, int) and 0 <= i < len(pieces) and not pieces[i][0]]
            except Exception:
                idxs = [int(x) for x in re.findall(r"\b\d+\b", raw)
                        if int(x) < len(pieces) and not pieces[int(x)][0]]
            if not idxs:
                print(f" >> [DeleteRound {round_no}] no valid deletions parsed.")
                break  # model declines to cut more — keep current state
            for i in set(idxs):
                keep[i] = False

        out = "\n\n".join(p[1] for i, p in enumerate(pieces) if keep[i])
        # Sanity: must actually shrink, must not collapse the section.
        if not (0.3 * len(sec) < len(out) < 0.95 * len(sec)):
            return ""
        if not out.lstrip().startswith("\\section"):
            # Keep the heading even if the listing missed it.
            head_m = re.match(r"(?s)\\section\{.*?\}\s*", sec)
            if head_m:
                out = head_m.group(0) + "\n" + out
        return out

    def _compress_sectionwise(self, target_ratio: float = 0.6) -> str:
        """Compress the paper one section at a time (whole-doc fallback).

        Whole-document rewrites degenerate easily (output-token limits →
        summaries/placeholders instead of the document). Compressing each
        \\section chunk separately keeps every call's output small and lets a
        single bad section be retried without redoing the rest. Returns the
        reassembled tex, or '' on failure (caller keeps the previous version).
        """
        import re

        tex = self.current_tex
        parts = re.split(r"(?m)(?=\\section\{)", tex, maxsplit=0)
        if len(parts) < 2:
            print(" >> [Sectionwise] no \\section boundaries found; aborting.")
            return ""

        preamble, sections = parts[0], parts[1:]
        # Tail (bibliography + \end{document}) rides on the last section; cut it
        # off mechanically so the LLM cannot mangle it.
        tail = ""
        m = re.search(r"(?m)^\\bibliographystyle\{", sections[-1])
        if m:
            tail = sections[-1][m.start():]
            sections[-1] = sections[-1][: m.start()].rstrip() + "\n\n"

        compressed, ok_sections = [], 0
        import hashlib

        for idx, sec in enumerate(sections):
            heading_m = re.match(r"\\section\{([^}]*)\}", sec)
            heading = heading_m.group(1) if heading_m else f"part {idx+1}"
            # Checkpoint keyed by section content hash: a killed sweep resumes
            # at the first uncompressed section, and stale checkpoints from an
            # older (longer) source never match.
            sec_hash = hashlib.md5(sec.encode("utf-8")).hexdigest()[:10]
            ck_path = os.path.join(
                self.work_dir, f"sectionwise_{sec_hash}_{idx:02d}.tex"
            )
            if os.path.exists(ck_path):
                raw = self._read_file(ck_path)
                ok_sections += 1
                compressed.append(raw)
                print(f" >> [Sectionwise] '{heading[:50]}': checkpoint hit")
                continue
            target_chars = max(800, int(len(sec) * target_ratio))
            if len(sec) > 15000:
                # Non-thinking rewrites barely shrink large sections; let the
                # model pick whole paragraphs to delete instead.
                deleted = self._compress_by_deletion(sec, target_chars, heading)
                if deleted:
                    ok_sections += 1
                    with open(ck_path, "w", encoding="utf-8") as f:
                        f.write(deleted)
                    compressed.append(deleted)
                    print(
                        f" >> [Sectionwise] '{heading[:50]}' [delete-protocol]: "
                        f"{len(sec)} → {len(deleted)} chars"
                    )
                    continue
            prompt = f"""Compress the following LaTeX section. HARD LIMIT: your output must be at most {target_chars} characters (currently {len(sec)}; the venue's page budget forces this cut). Count the characters and stay under the limit.

Section: \\section{{{heading}}}

Rules (STRICT):
1. PRESERVE every technical claim, definition, research question, \\cite, \\label and \\ref in this section.
2. To reach the limit, DELETE whole paragraphs that repeat points, restate the abstract, or give motivational background — deleting redundancy is expected, gentle rewording is NOT enough.
3. Merge overlapping paragraphs; tighten verbose phrasing; convert enumerations to compact prose.
4. Do NOT delete the section, do NOT add new content, figures or tables, and do NOT touch any LaTeX markup you don't show (labels/refs must survive verbatim).
5. Output ONLY the compressed LaTeX for this section (from its \\section line to its end), no commentary, no code fences.

LaTeX source:
{sec}
"""
            try:
                response_dict = self._llm_call_with_deadline(prompt, timeout_sec=300)
            except Exception as e:
                # One wedged/timed-out call must not kill the sweep: keep this
                # section's original text and move on (a later sweep can retry
                # it — no checkpoint was written).
                print(
                    f" >> [Sectionwise] '{heading}' call failed ({e}); keeping original."
                )
                compressed.append(sec)
                continue
            raw = response_dict["raw_response"].strip()
            if "```latex" in raw:
                raw = raw.split("```latex")[1].split("```")[0].strip()
            good = (
                raw.startswith("\\section")
                and "\\end{document}" not in raw
                and len(raw) > 0.3 * len(sec)
                and len(raw) < 0.95 * len(sec)  # must actually shrink; else a later sweep retries
            )
            if not good:
                print(
                    f" >> [Sectionwise] '{heading}' rejected "
                    f"({len(raw)} chars vs {len(sec)}); keeping original."
                )
                raw = sec  # fall back to the uncompressed section
            else:
                ok_sections += 1
                with open(ck_path, "w", encoding="utf-8") as f:
                    f.write(raw)
            compressed.append(raw)
            print(
                f" >> [Sectionwise] '{heading[:50]}': "
                f"{len(sec)} → {len(raw)} chars"
            )

        if ok_sections == 0:
            print(" >> [Sectionwise] every section failed; aborting.")
            return ""
        self.sectionwise_stats = {
            "sections": len(sections),
            "compressed": ok_sections,
            "chars_before": sum(len(s) for s in sections),
            "chars_after": sum(len(c) for c in compressed),
        }
        return preamble + "".join(compressed) + tail

    def _compress_to_page_budget(
        self, pdf_path: str, max_loops: int = 5, ref_slack: int = 2
    ) -> str:
        """Compress the paper toward the venue's page budget (format.yaml).

        Runs LLM compression iterations until the compiled PDF fits
        page_limit_body + ref_slack (references overhead), or no further
        reduction is achieved. Whole-document rounds come first; after two
        degenerate responses — or an accepted round that shaves under 8% while
        still over target — the loop switches to section-wise compression.
        Content-preserving: technical claims, RQs, section structure and
        citations must survive.
        """
        limit = self._page_budget_limit()
        if not limit:
            print(" >> [Length] No page_limit_body in format.yaml — skipping compression.")
            return pdf_path

        pages = self._pdf_page_count(pdf_path)
        target = limit + ref_slack
        print(f" >> [Length] {pages} pages vs body limit {limit} (target ≤ {target}).")
        if pages <= target:
            return pdf_path

        guidelines = self._read_file(self.guidelines_path)
        self.compress_worklogs = {}
        consecutive_degenerate = 0
        force_sectionwise = False
        sectionwise_attempted = False

        for i in range(max_loops):
            if pages <= target:
                break
            print(f"\n=== Compression Iteration {i+1}/{max_loops} ({pages}p → ≤{target}p) ===")
            degenerate = False
            try:
                if force_sectionwise:
                    # Previous whole-doc rounds were too gentle — take the
                    # per-section char-budget path directly.
                    force_sectionwise = False
                    sectionwise_attempted = True
                    new_tex = self._compress_sectionwise()
                    if not new_tex:
                        print(" >> Section-wise compression failed. Stopping.")
                        break
                else:
                    prompt = f"""You are compressing a research paper to meet a strict page budget. The compiled paper is currently {pages} pages; the venue allows {limit} body pages (target ≤ {target} compiled pages including references).

Conference page budget from the guidelines (per-section targets):
{guidelines}

Compression rules (STRICT):
1. PRESERVE all technical claims, research questions, the section structure, every \\cite, every table/figure reference, and the abstract's core message. Do NOT delete whole sections.
2. Condense prose: merge redundant paragraphs, remove repetition, tighten verbose phrasing, convert long enumerations to compact prose or a single table, shorten over-long introductions/related work.
3. Prefer cutting filler, restatements of the abstract, and motivational padding over cutting technical substance.
4. Keep the LaTeX preamble, documentclass options, \\bibliographystyle, and the \\bibliography{{...}} argument EXACTLY as in the source — do not rename the .bib file.
5. It is acceptable to reduce float sizes ([width=0.8\\linewidth]) and trim table columns with verbose text.
6. Do NOT add ANY new figure, table, includegraphics, or content that is not in the source. If the source has no figures, the compressed paper must have no figures.

--- CURRENT LATEX SOURCE ({len(self.current_tex)} chars) ---
{self.current_tex}

Output the FULL revised LaTeX document (from \\documentclass to \\end{{document}}) inside a single ```latex code block. The block must contain the complete compressed document itself — never a placeholder, summary, or excerpt. You will output roughly {int(0.6 * len(self.current_tex) / 1000)}K characters of LaTeX; do not stop early.
"""
                    try:
                        response_dict = self._llm_call_with_deadline(prompt, timeout_sec=600)
                        raw = response_dict["raw_response"]
                        if "```latex" in raw:
                            new_tex = raw.split("```latex")[1].split("```")[0].strip()
                        else:
                            new_tex = raw.strip()

                        # Sanity gate: the model sometimes echoes the placeholder
                        # ("paper_content") or truncates instead of emitting the doc.
                        degenerate = not (
                            "\\documentclass" in new_tex
                            and "\\end{document}" in new_tex
                            and len(new_tex) > 0.3 * len(self.current_tex)
                        )
                    except Exception as e:
                        print(f" >> Compression LLM call failed: {e}")
                        consecutive_degenerate += 1
                        if consecutive_degenerate >= 2:
                            print(
                                " >> Whole-document compression keeps failing;"
                                " switching to section-wise compression."
                            )
                            new_tex = self._compress_sectionwise()
                            if not new_tex:
                                print(" >> Section-wise compression failed too. Stopping.")
                                break
                            consecutive_degenerate = 0
                        else:
                            continue

                if degenerate:
                    reason = (
                        f"degenerate response ({len(new_tex)} chars vs current "
                        f"{len(self.current_tex)}); likely placeholder echo or truncation"
                    )
                    print(f" >> Compression iteration {i+1} rejected: {reason}.")
                    # Keep the rejected raw for diagnosis (what did the model do?)
                    with open(
                        os.path.join(
                            self.work_dir, f"compression_rejected_v{i+1}.txt"
                        ),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(raw)
                    self.compress_worklogs[f"v{i+1}"] = {
                        "pages_before": pages,
                        "pages_after": 0,
                        "compiled": False,
                        "outcome": f"REJECTED_{reason}",
                    }
                    with open(
                        os.path.join(self.work_dir, "compression_worklog.json"), "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(self.compress_worklogs, f, indent=4)
                    consecutive_degenerate += 1
                    if consecutive_degenerate >= 2:
                        print(
                            " >> Whole-document compression keeps degenerating;"
                            " switching to section-wise compression."
                        )
                        new_tex = self._compress_sectionwise()
                        if not new_tex:
                            print(" >> Section-wise compression failed too. Stopping.")
                            break
                        consecutive_degenerate = 0
                    else:
                        continue  # retry next iteration; do not abandon the loop

                # Mechanical repair of hallucinated references before compiling:
                # restore the original \bibliography / \bibliographystyle args and
                # comment out \includegraphics of files that neither exist on disk
                # nor appeared in the source (LLMs invent figures under compression).
                new_tex = self._repair_candidate_tex(new_tex)

                cand_name = f"compressed_candidate_v{i+1}"
                cand_tex = os.path.join(self.work_dir, f"{cand_name}.tex")
                cand_pdf = os.path.join(self.work_dir, f"{cand_name}.pdf")
                with open(cand_tex, "w", encoding="utf-8") as f:
                    f.write(new_tex)
                compile_latex(self.work_dir, cand_pdf, cand_name)

                new_pages = (
                    self._pdf_page_count(cand_pdf)
                    if os.path.exists(cand_pdf) and self._compile_is_complete(cand_name)
                    else 0
                )
                accepted = new_pages and new_pages < pages
                self.compress_worklogs[f"v{i+1}"] = {
                    "pages_before": pages,
                    "pages_after": new_pages,
                    "compiled": bool(new_pages),
                    "outcome": "ACCEPTED" if accepted else "REJECTED",
                }
                with open(
                    os.path.join(self.work_dir, "compression_worklog.json"), "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(self.compress_worklogs, f, indent=4)

                if not new_pages:
                    print(f" >> Compression iteration {i+1} failed to compile. Retrying.")
                    continue
                consecutive_degenerate = 0
                if accepted:
                    reduction = pages - new_pages
                    print(f" >> Compression iteration {i+1}: {pages}p → {new_pages}p. Accepted.")
                    self.current_tex = new_tex
                    pdf_path = cand_pdf
                    pages = new_pages
                    if pages > target and reduction < max(1, int(0.08 * (pages + reduction))):
                        # Whole-doc compression is accepted but too gentle
                        # (under 8%/round) — force a section-wise sweep next.
                        print(
                            " >> Reduction rate too low while still over target;"
                            " forcing section-wise compression next iteration."
                        )
                        force_sectionwise = True
                else:
                    if not sectionwise_attempted and not force_sectionwise:
                        # Whole-doc hit a plateau while still over target —
                        # give the per-section char-budget path one chance
                        # before giving up.
                        print(
                            " >> Whole-doc plateau with no reduction;"
                            " forcing one section-wise sweep before stopping."
                        )
                        force_sectionwise = True
                        sectionwise_attempted = True
                        continue
                    print(
                        f" >> Compression iteration {i+1}: no reduction ({pages}p → {new_pages}p). Stopping."
                    )
                    break
            except Exception as e:
                print(f" >> Error during compression iteration: {e}")
                traceback.print_exc()
                break

        print(f" >> [Length] Compression finished at {pages} pages (limit {limit} body).")
        return pdf_path

    def _extract_scores(self, review: dict) -> dict:
        """Extracts numerical scores from the review dictionary for comparison."""
        axes = [
            "Originality",
            "Quality",
            "Clarity",
            "Significance",
            "Soundness",
            "Presentation",
            "Contribution",
            "Overall",
            "Confidence",
        ]
        scores = {}
        for axis in axes:
            val = review.get(axis, 0)
            try:
                scores[axis] = float(val)
            except ValueError:
                scores[axis] = 0.0
        return scores

    def run(self, texfile_path: str) -> str:
        """
        Main execution loop:
        1. Compile Initial Draft -> Review.
        2. Refine -> Compile -> Review.
        3. Repeat until score increases or max_reflections reached.
        """
        self.current_tex = self._read_file(texfile_path)
        worklog_save_path = os.path.join(
            self.work_dir, "content_refinement_worklog.json"
        )

        context_files = {
            "guidelines": self._read_file(self.guidelines_path),
            "experimental_log": self._read_file(self.experimental_log_path),
            "citations": self._read_file(self.citation_map_path),
        }

        # --- STEP 0: Initial Compilation & Baseline Review ---
        print("\n=== Initial Baseline Review ===")
        initial_pdf_path = os.path.join(self.work_dir, "initial_draft.pdf")

        with open(
            os.path.join(self.work_dir, "initial_draft.tex"), "w", encoding="utf-8"
        ) as f:
            f.write(self.current_tex)

        compile_latex(self.work_dir, initial_pdf_path, "initial_draft")
        print(f" >> Initial PDF saved to {initial_pdf_path}")

        if not os.path.exists(initial_pdf_path):
            print(" >> Error: Initial PDF failed to compile. Cannot review.")
            return f" >> Error: Initial PDF '{initial_pdf_path}' failed to compile. Cannot review."

        v0_screenshots_dir = os.path.join(
            self.work_dir, "pdf_screenshots", "content_refinement", "v0"
        )
        print(f" >> Generating snapshots for V0...")
        pdf_to_grid_images(initial_pdf_path, v0_screenshots_dir)

        current_peer_review, self.current_score = self._get_peer_review(
            initial_pdf_path, "initial"
        )
        self.initial_score = self.current_score

        final_valid_pdf_path = initial_pdf_path

        # --- Content Refinement Loop ---
        for i in range(self.max_reflections):
            print(f"\n=== Refinement Iteration {i+1}/{self.max_reflections} ===")

            cur_filename = f"refined_paper_v{i+1}"
            cur_pdf_path = os.path.join(self.work_dir, f"{cur_filename}.pdf")

            previous_log_str = (
                json.dumps(self.worklogs, indent=4) if self.worklogs else "None"
            )

            user_prompt_text = f"""
REFLECTION ITERATION {i+1}.

--- PREVIOUS ITERATION LOG ---
{previous_log_str}

--- CURRENT REVIEWER FEEDBACK (Score: {self.current_score}) ---
{json.dumps(current_peer_review, indent=2)}

--- CONFERENCE GUIDELINES ---
{context_files['guidelines']}

--- EXPERIMENTAL LOG (Data Truth) ---
{context_files['experimental_log']}

--- CITATION MAP (Reference Truth) ---
{context_files['citations']}

--- CURRENT LATEX SOURCE ---
{self.current_tex}

INSTRUCTION: 
1. Your goal is to IMPROVE the reviewer score (Current: {self.current_score}).
2. Address the 'Weaknesses' and 'Questions' in the Reviewer Feedback above.
3. Output the JSON Worklog first, then the Full Revised LaTeX.
"""

            valid_pdf_for_context = final_valid_pdf_path

            print(" >> calling Refinement Agent...")
            try:
                response_dict = call_llm_with_pdf(
                    pdf_path=valid_pdf_for_context,
                    prompt=user_prompt_text,
                    model_name=self.model_name,
                    system_instruction=self.system_prompt,
                    result_parsing_func=parse_json_latex_response,
                )

                parsed = json.loads(response_dict["parsed_response"])

                new_tex = parsed["latex"]
                if not new_tex:
                    print(" >> Error: No LaTeX generated.")
                    break

                with open(
                    os.path.join(self.work_dir, f"{cur_filename}.tex"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(new_tex)

                print(" >> Compiling new draft...")
                compile_latex(self.work_dir, cur_pdf_path, cur_filename)

                if not os.path.exists(cur_pdf_path) or not self._compile_is_complete(cur_filename):
                    print(" >> Compilation Failed (no PDF, truncated tex, or TeX abort). Retrying with previous version...")
                    continue

                print(f" >> New PDF saved to {cur_pdf_path}")

                screenshots_dir = os.path.join(
                    self.work_dir, "pdf_screenshots", "content_refinement", f"v{i+1}"
                )
                print(f" >> Generating snapshots for v{i+1}...")
                pdf_to_grid_images(cur_pdf_path, screenshots_dir)

                new_review, new_score = self._get_peer_review(cur_pdf_path, f"v{i+1}")

                # --- COMPARISON LOGIC & METRICS EXTRACTION ---
                old_metrics = self._extract_scores(current_peer_review)
                new_metrics = self._extract_scores(new_review)

                excluded_axes = ["Overall", "Confidence"]
                comparison_axes = [
                    k for k in new_metrics.keys() if k not in excluded_axes
                ]

                total_gain = 0.0
                total_drop = 0.0
                deltas = {}

                for k in comparison_axes:
                    delta = new_metrics.get(k, 0) - old_metrics.get(k, 0)
                    deltas[k] = delta
                    if delta > 0:
                        total_gain += delta
                    elif delta < 0:
                        total_drop += abs(delta)

                current_log_entry = {
                    "round": i + 1,
                    "agent_plan": parsed["json"],
                    "scores_before": old_metrics,
                    "scores_after": new_metrics,
                    "deltas": deltas,
                    "total_gain": total_gain,
                    "total_drop": total_drop,
                    "outcome": "UNKNOWN",  # Will be updated below
                }

                print(f" >> Score Analysis v{i+1}:")
                print(
                    f"    Overall: {old_metrics['Overall']} -> {new_metrics['Overall']}"
                )
                print(f"    Sub-axes Gain: +{total_gain} | Drop: -{total_drop}")
                print(f"    Sub-axes Deltas: {deltas}")

                # Case 1: Overall Increased -> SUCCESS -> ACCEPT & CONTINUE
                if new_metrics["Overall"] > old_metrics["Overall"]:
                    print(
                        " >> SUCCESS: Overall Score increased! Progressing to next iteration..."
                    )

                    current_log_entry["outcome"] = "ACCEPTED_SCORE_INCREASE"
                    self.worklogs[f"v{i+1}"] = current_log_entry

                    self.current_tex = new_tex
                    self.current_score = new_score
                    current_peer_review = new_review
                    final_valid_pdf_path = cur_pdf_path

                    # Save Log and Continue loop
                    with open(worklog_save_path, "w", encoding="utf-8") as f:
                        json.dump(self.worklogs, f, indent=4)

                # Case 2: Overall Decreased -> FAIL -> BREAK & REVERT
                elif new_metrics["Overall"] < old_metrics["Overall"]:
                    print(
                        " >> STOP: Overall Score decreased. Reverting to previous iteration."
                    )

                    current_log_entry["outcome"] = "REJECTED_SCORE_DECREASE"
                    self.worklogs[f"v{i+1}"] = current_log_entry

                    # Save Log and Break
                    with open(worklog_save_path, "w", encoding="utf-8") as f:
                        json.dump(self.worklogs, f, indent=4)
                    break

                # Case 3: Overall Same
                else:
                    if total_drop > total_gain:
                        # Case 3b: Too much internal degradation -> BREAK & REVERT
                        print(
                            " >> STOP: Overall same, but sub-axes degraded (Drop > Gain). Reverting."
                        )

                        current_log_entry["outcome"] = "REJECTED_DEGRADATION"
                        self.worklogs[f"v{i+1}"] = current_log_entry

                        # Save Log and Break
                        with open(worklog_save_path, "w", encoding="utf-8") as f:
                            json.dump(self.worklogs, f, indent=4)
                        break
                    else:
                        # Case 3a: Gain >= Drop -> ACCEPT & CONTINUE
                        print(
                            " >> ACCEPT & CONTINUE: Overall same, internal metrics stable/improved. Progressing to next iteration..."
                        )

                        current_log_entry["outcome"] = "ACCEPTED_NEUTRAL_IMPROVEMENT"
                        self.worklogs[f"v{i+1}"] = current_log_entry

                        self.current_tex = new_tex
                        self.current_score = new_score
                        current_peer_review = new_review
                        final_valid_pdf_path = cur_pdf_path

                        # Save Log and Continue loop
                        with open(worklog_save_path, "w", encoding="utf-8") as f:
                            json.dump(self.worklogs, f, indent=4)
            except Exception as e:
                print(f" >> Error during refinement loop: {e}")
                traceback.print_exc()
                break

        # End of Loop

        # Save format v0 (baseline for formatting)
        format_v0_tex_path = os.path.join(self.work_dir, "format_candidate_v0.tex")
        with open(format_v0_tex_path, "w", encoding="utf-8") as f:
            f.write(self.current_tex)

        format_v0_screenshots_dir = os.path.join(
            self.work_dir, "pdf_screenshots", "format_refinement", "v0"
        )
        print(f" >> Generating snapshots for format v0...")
        pdf_to_grid_images(final_valid_pdf_path, format_v0_screenshots_dir)

        # --- Formatting Loop ---
        print(" >> Starting dedicated formatting loop...")
        max_formatting_loops = 1
        for fmt_i in range(max_formatting_loops):
            print(f"\n=== Formatting Iteration {fmt_i+1}/{max_formatting_loops} ===")

            formatting_review = self._get_formatting_review(
                final_valid_pdf_path, f"fmt_loop_{fmt_i+1}"
            )

            has_issues = False

            fig_tabs = formatting_review.get("figure_and_tables", {})
            if isinstance(fig_tabs, dict):
                for item, details in fig_tabs.items():
                    if isinstance(details, dict):
                        issue = details.get("detected_issue", "")
                        if issue and issue.lower() != "none":
                            has_issues = True
                            break

            if not has_issues:
                other = formatting_review.get("other_issues", [])
                if isinstance(other, list):
                    for item in other:
                        if isinstance(item, dict):
                            issue = item.get("detected_issue", "")
                            if issue and issue.lower() != "none":
                                has_issues = True
                                break
                        elif isinstance(item, str) and item.lower() != "none":
                            has_issues = True
                            break
                elif isinstance(other, str) and other.lower() != "none":
                    has_issues = True

            if not has_issues:
                print(" >> No critical formatting issues found. Breaking loop.")
                break

            print(" >> [VLM] Found formatting issues. Calling Gemini to fix...")

            prompt = f"""You are a LaTeX formatting expert. Your task is to fix the formatting issues identified in the feedback below.
You must STRICTLY follow the provided formatting guidelines.
CRITICAL: You are ONLY allowed to make formatting, layout, and spacing adjustments. You MUST NOT change any content, text, claims, data, or citations in the paper unless explicitly allowed by the feedback.

--- CURRENT FORMATTING FEEDBACK ---
{json.dumps(formatting_review, indent=2)}

--- CONFERENCE GUIDELINES ---
{self._read_file(self.guidelines_path)}

--- CURRENT LATEX SOURCE ---
{self.current_tex}

Output the Full Revised LaTeX only, inside a 
```latex 
paper_content
``` 
block.
"""

            try:
                response_dict = call_llm_with_text_prompt(
                    prompt=prompt,
                    model_name=self.model_name,
                    return_json=False,
                    result_parsing_func=lambda x: x,
                    check_parsed_response_not_none=False,
                )

                raw_response = response_dict["raw_response"]
                if "```latex" in raw_response:
                    new_tex = raw_response.split("```latex")[1].split("```")[0].strip()
                else:
                    new_tex = raw_response.strip()

                candidate_tex_name = f"formatted_candidate_v{fmt_i+1}"
                candidate_tex_path = os.path.join(
                    self.work_dir, f"{candidate_tex_name}.tex"
                )
                candidate_pdf_path = os.path.join(
                    self.work_dir, f"{candidate_tex_name}.pdf"
                )

                with open(candidate_tex_path, "w", encoding="utf-8") as f:
                    f.write(new_tex)

                compile_latex(self.work_dir, candidate_pdf_path, candidate_tex_name)

                if os.path.exists(candidate_pdf_path) and self._compile_is_complete(candidate_tex_name):
                    print(f" >> Formatting iteration {fmt_i+1} compiled successfully.")
                    self.current_tex = new_tex
                    final_valid_pdf_path = candidate_pdf_path

                    log_entry = {
                        "outcome": "ACCEPTED_COMPILE_SUCCESS",
                        "formatting_feedback": formatting_review,
                    }
                    self.format_worklogs[f"v{fmt_i+1}"] = log_entry
                else:
                    print(
                        f" >> Formatting iteration {fmt_i+1} failed to compile. Skipping."
                    )
                    log_entry = {
                        "outcome": "REJECTED_COMPILE_FAILURE",
                        "formatting_feedback": formatting_review,
                    }
                    self.format_worklogs[f"v{fmt_i+1}"] = log_entry

                format_worklog_save_path = os.path.join(
                    self.work_dir, "format_refinement_worklog.json"
                )
                with open(format_worklog_save_path, "w", encoding="utf-8") as f:
                    json.dump(self.format_worklogs, f, indent=4)

            except Exception as e:
                print(f" >> Error during formatting iteration: {e}")
                traceback.print_exc()

        # --- Page-budget compression (length control) ------------------------
        final_valid_pdf_path = self._compress_to_page_budget(final_valid_pdf_path)

        # Save Final Output
        final_pdf_output_path = os.path.join(self.work_dir, "final_refined_paper.pdf")
        final_tex_path = os.path.join(self.work_dir, "final_refined_paper.tex")

        with open(final_tex_path, "w", encoding="utf-8") as f:
            f.write(self.current_tex)

        if os.path.exists(final_valid_pdf_path):
            shutil.copy(final_valid_pdf_path, final_pdf_output_path)
        else:
            compile_latex(self.work_dir, final_pdf_output_path, "final_refined_paper")

        print(
            f" >> Process Complete. Final Score: {self.current_score}, Final PDF at: {final_pdf_output_path}"
        )
        return final_pdf_output_path
