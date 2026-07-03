# Multi-Source Paper Search (DeepXiv + S2 + arXiv)

> Unified search across three backends, normalized + deduped. Status: **implemented**.

## Why

S2 alone is rate-limited (~100 req/5min keyless) and sometimes returns 0 results, leaving
papers with too few references. Multiple independent sources give broader coverage + resilience.

## Backends (`utils/paper_search.py`)

| Backend | Coverage | Strength | Auth |
|---|---|---|---|
| **DeepXiv** (`deepxiv` CLI) | 2.9M arXiv + 7.5M PMC | hybrid relevance, fast, TLDRs | free token (1000/day, auto) |
| **Semantic Scholar** | 200M+ papers | citation counts, venues | optional `SEMANTIC_SCHOLAR_API_KEY` |
| **arXiv API** | arXiv only | broad, always-on, no key | none |

Each degrades independently (errors → empty list; other backends still return).

## API

```python
from utils.paper_search import search_papers, make_bib_entry, to_paper_data
recs = search_papers("LLM RTL bug localization", limit=8, cutoff_date="2025-06")
# recs: [{title, authors[], year, venue, abstract, arxiv_id, citation_count, source}, ...]
# deduped by arxiv_id (preferred) or normalized title; sorted by citation_count + abstract length
make_bib_entry(recs[0])  # -> "@inproceedings{Key, title={...}, ...}"
to_paper_data(recs[0])   # -> PaperData(...)
```

## Integration

- **Literature agent** (`_discover_candidates`): calls `search_papers` for each search task,
  merges results with LLM-knowledge candidates, dedups. Adds real papers even when S2 is down.
- **enrich_paper.py** (enrichment mode): uses `search_papers` to find new refs for an existing paper.

## Setup

```bash
pip install deepxiv-sdk   # auto-registers free token to ~/.env on first use
```

## Publication resolution (arXiv → formal venue)

`resolve_publication(rec, keep_preprints=False)` — for each arXiv-sourced result, tries to find
its **formally published** version (conference/journal):
- **DBLP** (`dblp.uni-trier.de/search/publ/api`) — primary; authoritative for CS venues.
- **S2** (`/paper/arXiv:{id}?fields=venue,publicationVenue`) — fallback; broader coverage.
- Returns updated record (venue/year/doi) if a formal venue is found; **None** (drop) if not.
- `keep_preprints=True` keeps preprint-only papers (default False = strict drop).
- `make_bib_entry` only shows `note={arXiv:...}` for genuine preprints, never for resolved papers.
  Adds `doi={...}` when available.

Wired into `search_papers` as a post-filter: over-fetches `limit*2`, resolves each, drops
preprint-only, returns top `limit`. ALL consumers (literature agent + enrichment) get formal
citations automatically.

## Gotchas
- DeepXiv CLI prints status lines before JSON; the module finds the first `{` to parse.
- `make_bib_entry` escapes `&`, `_`, `%` in titles/venues (prevents LaTeX errors).
- arXiv API returns Atom XML; parsed best-effort (missing fields tolerated).
- DBLP via `dblp.uni-trier.de` (the `dblp.org` domain may be unreachable from some networks).
- S2 rate-limits (429) — the resolver falls back gracefully (returns None = drop).
