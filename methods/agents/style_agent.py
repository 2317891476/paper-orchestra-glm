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

"""StyleAgent v2 — exemplar-bank + retrieval style learning (ZeroStylus-inspired).

Instead of a single static style-summary (the weak "direct prompting" baseline), this agent:
  1. Segments each best paper by section (intro / related-work / method / eval / conclusion).
  2. Builds a per-section EXEMPLAR BANK (real passages) — the few-shot corpus.
  3. Computes a quantitative STRUCTURE profile (section ordering, paragraph length, ...).
  4. Distills a tight per-section VOICE summary (voice/tone; structure carried by exemplars).

At generation time the writers RETRIEVE the relevant section's real exemplars and inject them
as few-shot examples (concrete text >> abstract description — see arXiv:2505.07888 ZeroStylus).

Graceful no-op when no style papers are provided.
"""

import glob
import json
import os
import re
import tempfile
from typing import Dict, List, Optional

from methods.prompts.style_agent import style_extraction_prompt, sentence_template_extraction_prompt
from utils.llm_backend_utils import call_llm_with_images, call_llm_with_text_prompt
from utils.pdf_utils import load_paper, pdf_to_grid_images

_MAX_STYLE_PAPERS = 3
_MAX_EXCERPTS_PER_SECTION = 2
_MAX_EXCERPT_CHARS = 1200

# canonical section -> heading aliases (case-insensitive substring match on a heading line)
_SECTION_ALIASES: Dict[str, List[str]] = {
    "abstract": ["abstract"],
    "introduction": ["introduction", "intro"],
    "related_work": ["related work", "related works", "prior work", "background"],
    "method": [
        "method", "methodology", "approach", "design", "framework",
        "our approach", "model", "architecture", "implementation", "overview",
    ],
    "evaluation": [
        "evaluation", "experiment", "experiments", "experimental", "results",
        "experimental setup", "setup", "methodology and evaluation",
    ],
    "conclusion": ["conclusion", "conclusions", "summary", "discussion", "future work"],
}
_CANONICAL_ORDER = ["abstract", "introduction", "related_work", "method", "evaluation", "conclusion"]


# --- helpers ----------------------------------------------------------------


def _strip_markdown_fence(text: str) -> str:
    m = re.search(r"```markdown\s*(.*?)\s*```", text.strip(), re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)\s*```", text.strip(), re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _classify_heading(line: str) -> Optional[str]:
    """Return canonical section if `line` looks like a section heading, else None."""
    s = line.strip()
    if not (2 <= len(s) <= 60):
        return None
    # headings often: "1 Introduction", "1.2 Related Work", "Abstract", "III. METHOD"
    s_norm = re.sub(r"^(section\s+)?(\d+(\.\d+)*\.?|[ivxlc]+\.?)\s*", "", s, flags=re.I).strip(": -")
    if not s_norm or len(s_norm) < 3:
        return None
    low = s_norm.lower()
    for canon, aliases in _SECTION_ALIASES.items():
        for a in aliases:
            if low == a or low.startswith(a):
                return canon
    return None


def segment_paper(text: str) -> Dict[str, str]:
    """Split a paper's full text into {canonical_section: text} by heading detection."""
    chunks: Dict[str, List[str]] = {}
    current = None
    for line in text.splitlines():
        canon = _classify_heading(line)
        if canon:
            current = canon
            chunks.setdefault(current, [])
            continue
        if current:
            chunks[current].append(line)
    return {k: "\n".join(v).strip() for k, v in chunks.items() if v}


def _take_excerpt(text: str) -> str:
    """First ~1 paragraph(s), capped."""
    text = text.strip()
    if not text:
        return ""
    # first paragraph break
    parts = re.split(r"\n\s*\n", text)
    out = parts[0] if parts else text
    if len(out) < 200 and len(parts) > 1:
        out = (out + "\n\n" + parts[1]).strip()
    return out[:_MAX_EXCERPT_CHARS]


def build_style_bank(paper_texts: List[str]) -> Dict[str, List[str]]:
    """Aggregate per-section real-passage exemplars across papers (capped)."""
    bank: Dict[str, List[str]] = {c: [] for c in _CANONICAL_ORDER}
    for text in paper_texts:
        sections = segment_paper(text)
        for canon, body in sections.items():
            if canon not in bank:
                continue
            ex = _take_excerpt(body)
            if ex and len(bank[canon]) < _MAX_EXCERPTS_PER_SECTION:
                bank[canon].append(ex)
    return {k: v for k, v in bank.items() if v}


def compute_structure_profile(bank: Dict[str, List[str]]) -> Dict:
    """Quantitative style facts measured from the exemplars."""
    present = [c for c in _CANONICAL_ORDER if bank.get(c)]
    para_lengths = []
    for exs in bank.values():
        for ex in exs:
            for para in re.split(r"\n\s*\n", ex):
                para = para.strip()
                if para:
                    para_lengths.append(len(para))
    return {
        "section_order": present,
        "avg_paragraph_chars": int(sum(para_lengths) / len(para_lengths)) if para_lengths else 0,
        "has_related_work": "related_work" in present,
        "n_section_types_observed": len(present),
    }


# --- retrieval helpers (used by the writers) --------------------------------


def style_summary(profile: Optional[dict]) -> str:
    return (profile or {}).get("summary", "") or ""


def exemplars_block(profile: Optional[dict], sections: List[str], max_per_section: int = 1) -> str:
    """Format real exemplars for the requested sections as a few-shot injection block."""
    if not profile:
        return ""
    bank: Dict[str, List[str]] = profile.get("bank", {}) or {}
    lines = []
    for sec in sections:
        exs = bank.get(sec) or []
        if not exs:
            continue
        for ex in exs[:max_per_section]:
            lines.append(f"--- exemplar · {sec.replace('_', ' ')} ---\n{ex}\n")
    if not lines:
        return ""
    return (
        "=== TARGET-CONFERENCE STYLE EXEMPLARS (real passages to mimic in voice & structure) ===\n\n"
        + "\n".join(lines)
        + "\n=== END EXEMPLARS ==="
    )


def sentence_templates_block(
    profile: Optional[dict], functions: Optional[List[str]] = None, max_per_function: int = 2
) -> str:
    """Format sentence-level phrasing templates (by rhetorical function) for injection.

    ZeroStylus 2nd granularity: concrete sentence patterns the community reuses.
    """
    if not profile:
        return ""
    tmpl: Dict[str, List[str]] = profile.get("sentence_templates", {}) or {}
    if not tmpl:
        return ""
    fns = functions or list(tmpl.keys())
    lines = []
    for fn in fns:
        items = tmpl.get(fn) or []
        if not items:
            continue
        for s in items[:max_per_function]:
            lines.append(f"- [{fn}] {s}")
    if not lines:
        return ""
    return (
        "=== TARGET-CONFERENCE SENTENCE TEMPLATES (reuse these phrasings where natural) ===\n"
        + "\n".join(lines)
        + "\n=== END SENTENCE TEMPLATES ==="
    )


# --- input resolution -------------------------------------------------------


def resolve_style_papers(
    run_dir: Optional[str], conf_template_dir: Optional[str]
) -> List[str]:
    """run-level dir first, then templates/<conf>/style_papers/ fallback. Dedup, cap 3."""
    candidates: List[str] = []
    seen = set()

    def _collect(d: str):
        nonlocal candidates
        if not d or not os.path.isdir(d):
            return
        for pdf in sorted(glob.glob(os.path.join(d, "*.pdf"))):
            base = os.path.basename(pdf)
            if base in seen:
                continue
            seen.add(base)
            candidates.append(pdf)

    _collect(run_dir)
    if not candidates:
        _collect(os.path.join(conf_template_dir, "style_papers") if conf_template_dir else None)
    return candidates[:_MAX_STYLE_PAPERS]


# --- agent ------------------------------------------------------------------


class StyleAgent:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, paper_paths: List[str], output_path: str) -> Optional[dict]:
        """Return a style profile dict {summary, bank, structure, bank_path} or None.

        `output_path` is where style_guide.md is written; style_bank.json is written next to it.
        """
        paper_paths = [p for p in (paper_paths or []) if os.path.exists(p)]
        paper_paths = paper_paths[:_MAX_STYLE_PAPERS]
        if not paper_paths:
            print(" >> [StyleAgent] no style papers provided — skipping style learning.")
            return None

        print(f" >> [StyleAgent] extracting style from {len(paper_paths)} paper(s)...")

        # --- text + per-section bank + structure ---
        paper_texts: List[str] = []
        for p in paper_paths:
            try:
                paper_texts.append(load_paper(p, num_pages=8, min_size=50))
            except Exception as e:
                print(f"    [StyleAgent] could not read text from {p}: {e}")
        bank = build_style_bank(paper_texts)
        structure = compute_structure_profile(bank)
        if not bank:
            print(" >> [StyleAgent] could not segment any sections — skipping.")
            return None

        # --- LLM summary (voice-focused; structure already in the bank) ---
        summary = self._extract_summary(paper_paths, paper_texts, bank, structure)

        # --- sentence-level templates (ZeroStylus 2nd granularity) ---
        sentence_templates = self._extract_sentence_templates(bank)

        profile = {
            "summary": summary,
            "bank": bank,
            "structure": structure,
            "sentence_templates": sentence_templates,
        }

        # --- persist ---
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self._render_guide(profile))
        bank_path = os.path.join(os.path.dirname(output_path), "style_bank.json")
        with open(bank_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        profile["bank_path"] = bank_path
        print(f" >> [StyleAgent] style guide → {output_path}; exemplar bank → {bank_path}")
        return profile

    def _extract_summary(
        self,
        paper_paths: List[str],
        paper_texts: List[str],
        bank: Dict[str, List[str]],
        structure: Dict,
    ) -> str:
        joined_text = "\n\n".join(
            f"=== {os.path.basename(p)} ===\n{t[:5000]}" for p, t in zip(paper_paths, paper_texts)
        )
        prompt = style_extraction_prompt.format(
            structure_json=json.dumps(structure, indent=2),
            bank_sections=", ".join(bank.keys()),
        ) + "\n\n=== PAPER TEXT (truncated) ===\n" + joined_text

        # visual mode first (the rendered pages show layout / figure conventions)
        image_paths: List[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, p in enumerate(paper_paths):
                try:
                    grids = pdf_to_grid_images(p, os.path.join(tmpdir, f"paper_{idx}"))
                    if grids:
                        image_paths.append(grids[0])
                except Exception:
                    pass
            try:
                if image_paths:
                    resp = call_llm_with_images(
                        prompt=prompt,
                        images=image_paths,
                        model_name=self.model_name,
                        generation_configs={"temperature": 0.4},
                        return_json=False,
                        result_parsing_func=lambda x: x,
                        check_parsed_response_not_none=False,
                    )
                else:
                    raise RuntimeError("no images")
            except Exception as e:
                print(f"    [StyleAgent] visual call failed ({e}); falling back to text-only.")
                resp = call_llm_with_text_prompt(
                    prompt=prompt,
                    model_name=self.model_name,
                    generation_configs={"temperature": 0.4},
                    return_json=False,
                    check_parsed_response_not_none=False,
                )
        raw = resp.get("raw_response") or ""
        return _strip_markdown_fence(raw)

    def _extract_sentence_templates(self, bank: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Extract sentence-level phrasing templates by rhetorical function (text-only LLM call)."""
        # flatten bank passages into one blob (bounded)
        passages = "\n\n".join(ex for exs in bank.values() for ex in exs)[:6000]
        if not passages.strip():
            return {}
        prompt = sentence_template_extraction_prompt.format(passages=passages)
        try:
            resp = call_llm_with_text_prompt(
                prompt=prompt,
                model_name=self.model_name,
                generation_configs={"temperature": 0.3},
                return_json=True,
                check_parsed_response_not_none=False,
            )
            parsed = resp.get("parsed_response") or {}
        except Exception as e:
            print(f"    [StyleAgent] sentence-template extraction failed: {e}")
            return {}
        # keep only well-formed function -> list[str]
        out: Dict[str, List[str]] = {}
        for k, v in (parsed or {}).items():
            if isinstance(v, list):
                cleaned = [str(x).strip() for x in v if str(x).strip()]
                if cleaned:
                    out[k] = cleaned
        return out

    @staticmethod
    def _render_guide(profile: dict) -> str:
        """Human-readable style_guide.md = summary + observed structure + section index."""
        out = ["# Target-Conference Style Guide", ""]
        out.append("## Voice & Conventions (summary)")
        out.append("")
        out.append(profile.get("summary", "_(no summary extracted)_"))
        out.append("")
        out.append("## Observed Structure (measured from exemplars)")
        out.append("")
        out.append("```json")
        out.append(json.dumps(profile.get("structure", {}), indent=2))
        out.append("```")
        out.append("")
        out.append("## Exemplar Bank Sections")
        out.append("")
        for sec in _CANONICAL_ORDER:
            exs = profile.get("bank", {}).get(sec) or []
            if exs:
                out.append(f"- `{sec}`: {len(exs)} passage(s)")
        out.append("")
        st = profile.get("sentence_templates", {}) or {}
        if st:
            out.append("## Sentence-Level Phrasing Templates")
            out.append("")
            for fn, items in st.items():
                if items:
                    out.append(f"**{fn}**")
                    for s in items:
                        out.append(f"- {s}")
                    out.append("")
        out.append(
            "> Concrete per-section passages live in `style_bank.json` and are injected as "
            "few-shot exemplars + sentence templates into the writers at generation time."
        )
        return "\n".join(out)
