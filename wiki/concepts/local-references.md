# Local References (user-provided, always-citable)

> Optional feature: supplement the LLM/Semantic-Scholar literature search with papers you
> already know are highly relevant. Status: **implemented**.

## Why

The literature agent may miss papers the user knows are central. Local refs guarantee those
papers are citable and nudges the writers to prefer them.

## Input

Drop files into `raw_material/references/` (or pass `--local_references_dir <dir>`):

- `*.bib` — parsed by a lightweight regex parser (`utils/local_reference_utils.py::parse_bib_file`).
- `*.pdf` — text extracted via `load_paper`, then one LLM call pulls
  `{title, authors, year, venue, abstract}` (`extract_paper_data_from_pdf`).

## Behavior

- Every local paper becomes a `PaperData` with `is_local=True`, registered directly into the
  literature agent's `unique_papers_registry` (Phase 1.5 of `HybridLiteratureAgent.run`).
- They **bypass** the Semantic Scholar enrichment and the cutoff-date filter — always citable.
- `references.bib` + `citation_map.json` include them automatically (`is_local` flag in the map).
- `_generate_citation_map` includes local papers **even without an abstract** (so they stay
  citable); non-local papers still require an abstract.
- `_inject_citations_into_outline` adds local keys to Introduction + every Related Work
  subsection's `citation_candidates` as a "prefer these" hint.
- Writers are nudged (prompts) to prefer `is_local=true` papers.

## Code pointers

- `utils/local_reference_utils.py` — `load_local_references`, `parse_bib_file`, `extract_paper_data_from_pdf`
- `methods/agents/literature_review_agent.py` — `PaperData.is_local`, `_load_and_register_local_references`,
  `_inject_citations_into_outline` (local-key attach), `_generate_citation_map` (always include local)
- CLI: `--local_references_dir` (auto-detects `<raw_materials_dir>/references/`)

## Gotchas

- `.bib` parser is best-effort; malformed entries are skipped (not fatal).
- Duplicate titles (normalized) are deduped across .bib + .pdf.
- No `bibtexparser` dependency — regex only.

## TODO / flesh out

- [ ] Example `references/` folder layout
- [ ] LLM-fallback for .bib entries missing abstracts
