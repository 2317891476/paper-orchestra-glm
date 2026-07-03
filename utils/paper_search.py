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

"""Unified multi-source paper search: DeepXiv + Semantic Scholar + arXiv.

Normalizes results from all three backends into a common record and dedups by arxiv_id
(preferred) or normalized title. Each backend degrades independently (errors → empty list).
"""

import json
import os
import re
import subprocess
import datetime
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
S2_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

_ARXIV_NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


# --- normalization helpers ---


def _normalize_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def _year_from_arxiv_id(arxiv_id: str) -> Optional[int]:
    """arxiv id YYMM.NNNN -> year (20YY)."""
    if not arxiv_id:
        return None
    m = re.match(r"(\d{2})(\d{2})\.", arxiv_id)
    if m:
        return 2000 + int(m.group(1))
    return None


def _coerce_authors(authors) -> List[str]:
    out = []
    for a in (authors or []):
        if isinstance(a, dict):
            a = a.get("name") or a.get("full_name") or ""
        if a:
            out.append(str(a))
    return out


def _make_key(authors, year: Optional[int], title: str) -> str:
    authors = _coerce_authors(authors)
    first = re.sub(r"[^a-zA-Z]", "", (authors[0].split()[-1] if authors else "Anon")).capitalize()
    yr = str(year) if year else "2024"
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", (title or "").lower())
    stop = {"the", "a", "an", "of", "for", "and", "to", "in", "on", "with"}
    words = [w.capitalize() for w in clean.split() if w not in stop]
    return f"{first}{yr}{(''.join(words[:2])) if words else 'Paper'}"


def _within_cutoff(year: Optional[int], date_str: Optional[str], cutoff: Optional[str]) -> bool:
    if not cutoff:
        return True
    try:
        cy, cm = map(int, cutoff.split("-"))
    except Exception:
        return True
    y = year
    if y is None and date_str:
        m = re.match(r"(\d{4})", str(date_str))
        y = int(m.group(1)) if m else None
    if y is None:
        return True
    if y < cy:
        return True
    if y == cy and cm >= 1:
        return True
    return False


def _record(*, title, authors, year, venue, abstract, arxiv_id, citation_count, source) -> Dict:
    return {
        "title": (title or "").strip(),
        "authors": authors or [],
        "year": year,
        "venue": venue or "arXiv",
        "abstract": (abstract or "").strip(),
        "arxiv_id": arxiv_id,
        "citation_count": citation_count or 0,
        "source": source,
    }


# --- backends ---


def search_deepxiv(query: str, limit: int = 8, cutoff_date: Optional[str] = None,
                   venues: Optional[List[str]] = None) -> List[Dict]:
    """DeepXiv (BAAI) hybrid search over arXiv+PMC via the `deepxiv` CLI."""
    cmd = ["deepxiv", "search", query, "--limit", str(limit), "--format", "json"]
    if cutoff_date:
        cmd += ["--date-to", cutoff_date]
    for v in (venues or []):
        cmd += ["--venue", v]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # CLI prints status lines before the JSON; find the first '{'
        out = r.stdout
        i = out.find("{")
        if i < 0:
            return []
        data = json.loads(out[i:])
    except Exception as e:
        print(f"   [search] deepxiv failed: {e}")
        return []
    recs = []
    for item in data.get("result", []):
        ax = item.get("arxiv_id")
        year = item.get("venue_year") or _year_from_arxiv_id(ax)
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        recs.append(_record(
            title=item.get("title"), authors=item.get("authors") or [],
            year=year, venue=item.get("venue") or "arXiv",
            abstract=(item.get("abstract") or item.get("tldr") or ""),
            arxiv_id=ax, citation_count=item.get("citation_count"), source="deepxiv",
        ))
    return recs


def search_arxiv(query: str, limit: int = 8) -> List[Dict]:
    """arXiv Atom API."""
    try:
        url = "http://export.arxiv.org/api/query"
        params = {"search_query": f"all:{query}", "max_results": str(limit), "sortBy": "relevance"}
        r = requests.get(url, params=params, timeout=30)
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"   [search] arxiv failed: {e}")
        return []
    recs = []
    for e in root.findall("a:entry", _ARXIV_NS):
        title = (e.findtext("a:title", default="", namespaces=_ARXIV_NS) or "").strip()
        abstract = (e.findtext("a:summary", default="", namespaces=_ARXIV_NS) or "").strip()
        authors = [a.findtext("a:name", default="", namespaces=_ARXIV_NS)
                   for a in e.findall("a:author", _ARXIV_NS)]
        idurl = e.findtext("a:id", default="", namespaces=_ARXIV_NS) or ""
        ax = idurl.rsplit("/abs/", 1)[-1].split("v")[0] if "/abs/" in idurl else None
        pub = e.findtext("a:published", default="", namespaces=_ARXIV_NS) or ""
        year = int(pub[:4]) if re.match(r"\d{4}", pub) else _year_from_arxiv_id(ax)
        recs.append(_record(title=title, authors=authors, year=year, venue="arXiv",
                            abstract=abstract, arxiv_id=ax, citation_count=0, source="arxiv"))
    return recs


def search_s2_keyword(query: str, limit: int = 8) -> List[Dict]:
    """Semantic Scholar keyword search."""
    headers = {"X-API-KEY": S2_API_KEY} if S2_API_KEY else {}
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
                         headers=headers, timeout=15,
                         params={"query": query, "limit": limit,
                                 "fields": "title,authors,year,venue,abstract,citationCount,externalIds"})
        if r.status_code != 200:
            return []
        results = r.json().get("data", [])
    except Exception as e:
        print(f"   [search] s2 failed: {e}")
        return []
    recs = []
    for p in results:
        ext = p.get("externalIds") or {}
        recs.append(_record(
            title=p.get("title"), authors=[a.get("name", "") for a in (p.get("authors") or [])],
            year=p.get("year"), venue=p.get("venue") or "arXiv",
            abstract=p.get("abstract") or "",
            arxiv_id=ext.get("ArXiv"), citation_count=p.get("citationCount"), source="s2",
        ))
    return recs


# --- unified entry point ---


def search_papers(query: str, limit: int = 8, cutoff_date: Optional[str] = None,
                  venues: Optional[List[str]] = None) -> List[Dict]:
    """Search all backends, normalize, dedup, cutoff-filter. Each backend degrades independently."""
    per = max(limit, 6)
    raw: List[Dict] = []
    for fn in (search_deepxiv, search_arxiv, search_s2_keyword):
        try:
            raw += fn(query, limit=per) if fn is not search_deepxiv else fn(query, limit=per, cutoff_date=cutoff_date, venues=venues)
        except Exception as e:
            print(f"   [search] {fn.__name__} error: {e}")

    dedup: Dict[str, Dict] = {}
    for r in raw:
        if not r["title"]:
            continue
        if not _within_cutoff(r["year"], None, cutoff_date):
            continue
        key = r["arxiv_id"] if r["arxiv_id"] else f"t:{_normalize_title(r['title'])}"
        if key in dedup:
            # merge: keep richer record (prefer one with abstract + citation count)
            cur = dedup[key]
            if (len(r["abstract"]) > len(cur["abstract"])
                    or r["citation_count"] > cur["citation_count"]):
                r2 = dict(r)
                # preserve any missing fields from current
                for k in ("authors", "year", "venue"):
                    if not r2.get(k) and cur.get(k):
                        r2[k] = cur[k]
                dedup[key] = r2
        else:
            dedup[key] = r
    out = list(dedup.values())
    out.sort(key=lambda r: (r["citation_count"], len(r["abstract"])), reverse=True)
    return out[:limit]


# --- bib / PaperData conversion ---


def make_bib_entry(rec: Dict) -> str:
    authors = _coerce_authors(rec["authors"])
    key = _make_key(authors, rec["year"], rec["title"])

    def esc(s):
        """Escape LaTeX-special chars in bib text fields."""
        return (s or "").replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")

    authors_str = " and ".join(authors) if authors else "Unknown"
    venue = rec["venue"] or "arXiv"
    is_journal = any(j in venue.lower() for j in ("journal", "transactions", "ieee t", "acm t"))
    etype = "article" if is_journal else "inproceedings"
    venue_field = "journal" if is_journal else "booktitle"
    note = f"\n  note = {{arXiv:{rec['arxiv_id']}}}," if rec.get("arxiv_id") else ""
    return (f"@{etype}{{{key},\n"
            f"  title = {{{esc(rec['title'])}}},\n"
            f"  author = {{{authors_str}}},\n"
            f"  {venue_field} = {{{esc(venue)}}},\n"
            f"  year = {{{rec['year'] or ''}}},{note}\n}}")


def to_paper_data(rec: Dict, found_in_section: str = "Search", reason: str = ""):
    """Convert a search record to a PaperData (lazy import to avoid cycles)."""
    from methods.agents.literature_review_agent import PaperData
    return PaperData(
        citation_key=_make_key(rec["authors"], rec["year"], rec["title"]),
        title=rec["title"], authors=_coerce_authors(rec["authors"]), venue=rec["venue"] or "arXiv",
        year=rec["year"] or 0, abstract=rec["abstract"],
        citation_count=rec.get("citation_count") or 0,
        found_in_section=found_in_section, reason=reason or f"via {rec.get('source')}",
    )
