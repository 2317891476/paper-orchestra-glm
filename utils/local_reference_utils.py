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

"""Local reference loading: ingest user-provided PDFs + .bib into PaperData records.

These papers are marked `is_local=True`, bypass the Semantic Scholar / cutoff pipeline,
and are registered directly into the literature agent's pool so they are always citable.
"""

import glob
import json
import os
import re
from typing import List, Optional

from methods.agents.literature_review_agent import PaperData
from utils.llm_backend_utils import call_llm_with_text_prompt
from utils.pdf_utils import load_paper

# --- citation-key sanitization (mirrors scholar_utils / agent conventions) ---


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _make_key(authors: List[str], year: Optional[int], title: str) -> str:
    if authors:
        first_author = re.sub(r"[^a-zA-Z]", "", authors[0].split()[-1]).capitalize()
    else:
        first_author = "Local"
    year_str = str(year) if year else "2024"
    clean_title = re.sub(r"[^a-zA-Z0-9\s]", "", (title or "").lower())
    words = clean_title.split()
    stopwords = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "is", "are", "with", "by"}
    meaningful = [w.capitalize() for w in words if w not in stopwords]
    title_part = "".join(meaningful[:2]) if meaningful else "Paper"
    return f"{first_author}{year_str}{title_part}"


# --- .bib parsing (lightweight, best-effort regex + brace matching) ---


def _extract_braced(text: str, start: int) -> str:
    """Return the content inside the braces starting at `start` (which points at '{')."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
        i += 1
    return text[start + 1 :]


def _split_authors(raw: str) -> List[str]:
    raw = raw.replace("\n", " ").strip()
    parts = re.split(r"\s+and\s+", raw)
    return [p.strip().rstrip(",") for p in parts if p.strip()]


def _clean_bib_value(val: str) -> str:
    # strip surrounding braces/quotes already removed by caller; collapse whitespace
    val = re.sub(r"\s+", " ", val).strip()
    # unwrap one level of {...}
    if val.startswith("{") and val.endswith("}"):
        val = val[1:-1]
    return val.strip()


def parse_bib_file(bib_path: str) -> List[PaperData]:
    """Parse a .bib file into PaperData records (best-effort; skips junk)."""
    with open(bib_path, "r", encoding="utf-8") as f:
        text = f.read()

    papers: List[PaperData] = []
    for m in re.finditer(r"@(\w+)\s*\{", text):
        entry_type = m.group(1).lower()
        if entry_type in ("comment", "string", "preamble"):
            continue
        brace_start = text.index("{", m.start())
        body = _extract_braced(text, brace_start)
        if not body:
            continue

        # key is everything up to the first comma
        first_comma = body.find(",")
        if first_comma == -1:
            continue
        key = body[:first_comma].strip()
        rest = body[first_comma + 1 :]

        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", rest):
            field_name = fm.group(1).lower()
            j = fm.end()
            # skip whitespace
            while j < len(rest) and rest[j] == " ":
                j += 1
            if j >= len(rest):
                continue
            if rest[j] == "{":
                value = _extract_braced(rest, j)
            elif rest[j] == '"':
                k = rest.index('"', j + 1)
                value = rest[j + 1 : k]
            else:
                # bare value up to next comma
                k = rest.find(",", j)
                value = rest[j : k if k != -1 else len(rest)]
            fields[field_name] = _clean_bib_value(value)

        title = fields.get("title")
        if not title:
            continue

        year_raw = fields.get("year")
        try:
            year = int(re.sub(r"[^0-9]", "", year_raw)[:4]) if year_raw else None
        except (ValueError, TypeError):
            year = None

        authors = _split_authors(fields["author"]) if fields.get("author") else []

        papers.append(
            PaperData(
                citation_key=key or _make_key(authors, year, title),
                title=title,
                authors=authors,
                venue=fields.get("booktitle") or fields.get("journal") or "arXiv",
                year=year or 0,
                abstract=fields.get("abstract") or "",
                citation_count=0,
                found_in_section="Local Reference",
                reason="User-provided local reference (.bib)",
                journal=fields.get("journal"),
                volume=fields.get("volume"),
                pages=fields.get("pages"),
                is_local=True,
            )
        )
    return papers


# --- PDF metadata extraction via LLM ---


_PDF_META_PROMPT = """Extract bibliographic metadata from the following paper text.
Return ONLY a JSON object (wrapped in ```json ... ```) with exactly these keys:
{{
  "title": string,
  "authors": [string, ...],
  "year": integer or null,
  "venue": string (conference/journal name, or "arXiv" if unknown),
  "abstract": string (the paper's abstract, verbatim if findable, else a 2-3 sentence summary)
}}

Paper text:
---
{text}
---
"""


def extract_paper_data_from_pdf(pdf_path: str, model_name: str) -> Optional[PaperData]:
    """Extract a PaperData from a PDF via load_paper + one LLM call."""
    try:
        text = load_paper(pdf_path, num_pages=4, min_size=50)
    except Exception as e:
        print(f"   [local-refs] could not read {pdf_path}: {e}")
        return None

    # bound the text we send
    snippet = text[:8000]
    resp = call_llm_with_text_prompt(
        prompt=_PDF_META_PROMPT.format(text=snippet),
        model_name=model_name,
        return_json=True,
    )
    meta = resp.get("parsed_response") or {}

    title = (meta.get("title") or "").strip()
    if not title:
        print(f"   [local-refs] no title extracted from {pdf_path}, skipping")
        return None

    authors = meta.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",")]
    year = meta.get("year")
    try:
        year = int(year) if year else None
    except (ValueError, TypeError):
        year = None

    return PaperData(
        citation_key=_make_key(authors, year, title),
        title=title,
        authors=authors,
        venue=(meta.get("venue") or "arXiv").strip(),
        year=year or 0,
        abstract=(meta.get("abstract") or "").strip(),
        citation_count=0,
        found_in_section="Local Reference",
        reason="User-provided local reference (PDF)",
        is_local=True,
    )


# --- public entry point ---


def load_local_references(references_dir: str, model_name: str) -> List[PaperData]:
    """Load all *.bib and *.pdf from a directory into PaperData records (dedup by title)."""
    if not references_dir or not os.path.isdir(references_dir):
        return []

    papers: List[PaperData] = []
    seen_titles = set()

    for bib_path in sorted(glob.glob(os.path.join(references_dir, "*.bib"))):
        try:
            for p in parse_bib_file(bib_path):
                norm = _normalize_title(p.title)
                if norm and norm not in seen_titles:
                    seen_titles.add(norm)
                    papers.append(p)
                    print(f"   [local-refs] loaded .bib entry: {p.title}")
        except Exception as e:
            print(f"   [local-refs] failed to parse {bib_path}: {e}")

    for pdf_path in sorted(glob.glob(os.path.join(references_dir, "*.pdf"))):
        p = extract_paper_data_from_pdf(pdf_path, model_name)
        if p is None:
            continue
        norm = _normalize_title(p.title)
        if norm and norm in seen_titles:
            continue
        seen_titles.add(norm)
        papers.append(p)
        print(f"   [local-refs] loaded PDF: {p.title}")

    return papers
