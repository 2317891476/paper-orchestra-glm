# Agent — Style (StyleAgent)

> Optional Step 1.5: extract a writing-style guide from target-conference "best papers" and
> feed it to the literature + section writers. Status: **implemented**.

## Why

Writing agents default to generic academic style. To match a specific community's conventions
(HPCA vs CVPR vs ICLR), StyleAgent distills voice/structure/citation habits from example
best papers and injects the guide into the writers' system prompts.

## Input resolution (`resolve_style_papers`)

Priority:
1. `raw_material/style_references/` (run-level, priority) — or `--style_references_dir`
2. `templates/<conf>/style_papers/` (conference-level, fallback only if run-level empty)

Dedup by basename, cap at **3 papers** (visual extraction is token-heavy).

## What it does

`StyleAgent.run(paper_paths, output_path)`:
- Text: `load_paper` (first ~6 pages) per paper, concatenated.
- Visual: `pdf_to_grid_images` first 2×2 grid (pages 1–4) per paper.
- One `call_llm_with_images` call with `style_extraction_prompt` → markdown guide.
- Falls back to **text-only** if the model has no vision (vision call raises).
- Output saved to `<output_dir>/style_guide.md`; returns the guide text (or None).

## Guide structure (sections)

Voice & Tone · Section Structure & Ordering · Abstract & Introduction Pattern · Citation Style
& Density · Math/Notation/Definitions · Figures & Tables · Do/Don't · Representative Phrasings.

## Threading into writers

- `HybridLiteratureAgent`: appended to `writer_system_prompt` in `_synthesize_content`
  (after the `.format()` call, so placeholders are unaffected).
- `SectionWritingAgent`: appended to `self.system_prompt` in `__init__`.

## Code pointers

- `methods/agents/style_agent.py` — `StyleAgent`, `resolve_style_papers`, `_strip_markdown_fence`
- `methods/prompts/style_agent.py` — `style_extraction_prompt`
- Pipeline: `methods/paper_writer.py` Step 1.5; `methods/paper_writer_with_plotting.py` parity
- CLI: `--style_references_dir`, `--use_style_learning` (default True; no-op if no papers)

## Gotchas

- Requires a vision-capable model for the visual mode; auto-falls-back to text-only otherwise.
- The refinement agent does NOT currently consume the style guide (only literature + section).

## TODO / flesh out

- [ ] Confirm glm-5.2 vision availability for the visual mode
- [ ] Optionally feed style guide to ContentRefinementAgent too
