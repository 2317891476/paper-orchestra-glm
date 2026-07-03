# Paper Enrichment (add citations to an existing paper)

> Reusable: input an already-generated paper → find more refs → insert `\cite` + context → recompile.
> Status: **implemented** (`enrich_paper.py`).

## Why

Generated papers (especially fast drafts) often have too few citations. This script enriches
any existing paper by searching for relevant prior work and weaving citations into the text.

## Usage

```bash
python enrich_paper.py --paper_dir paper_output_hirca [--cutoff 2025-06] [--max_new 15]
```

Input: a `paper_output_X/` dir with `latex_writeup/raw_draft_paper.tex` + `references.bib`.

## Flow

1. **Citation-need analysis** (LLM): reads the paper, outputs up to 8 search queries for claims
   that need citation support.
2. **Multi-source search**: for each query, `search_papers()` (DeepXiv+S2+arXiv) → candidates.
   Filters to new papers (not already cited), within cutoff, with abstracts. Caps at `--max_new`.
3. **Bib append**: new entries (`make_bib_entry`) appended to `references.bib`.
4. **Citation insertion** (LLM): given the `.tex` + new candidates, inserts `\cite{key}` at
   relevant points **with brief contextual sentences**. Hard requirement: ≥10 new `\cite` commands.
   Preserves preamble, math, existing structure.
5. **Recompile**: engine-aware `compile_latex` → `final_paper_enriched.pdf`. Original backed up
   to `.tex.bak`.

## Verified result (SoC-HiRCA)

| | Before | After |
|---|---|---|
| `\cite` commands | 0 | **14** |
| distinct papers cited | 0 | **12** |
| bib entries | 4 | **16** |
| pages | 9 | 10 |
| cited keys missing from bib | — | **0** (all resolve) |

## Code pointers

- `enrich_paper.py` — main script (CLI args: `--paper_dir`, `--cutoff`, `--max_new`, `--model_name`)
- `utils/paper_search.py` — `search_papers`, `make_bib_entry` (the search + bib generation)
- Uses `call_llm_with_text_prompt` for citation-need analysis + citation insertion

## Gotchas
- The LLM's full-tex-rewrite is conservative by nature; the strong prompt (`min_cite` requirement)
  is critical to force material citation insertion.
- Bib `&`/`_`/`%` are escaped by `make_bib_entry` to prevent LaTeX errors.
- Re-running finds different papers (stochastic search); the `.tex.bak` preserves the previous version.
