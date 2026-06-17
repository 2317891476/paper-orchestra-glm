# Agent — Style (StyleAgent v2: exemplar bank + retrieval)

> Optional Step 1.5: learn the target community's writing style from "best papers" and condition
> the literature + section writers on it. Status: **implemented (v2)**.

## Why (and what changed in v2)

v1 produced a single static style-summary injected into the system prompt — the weak
"direct prompting" baseline. Research (ZeroStylus, arXiv:2505.07888; few-shot style
conditioning; stylometry) shows **concrete per-section exemplars retrieved at generation
time beat abstract descriptions**. v2 therefore builds a **per-section exemplar bank** +
**quantitative structure profile** and retrieves the relevant passages for each writer.

## Input resolution (`resolve_style_papers`)

Priority: `raw_material/style_references/` (run-level, or `--style_references_dir`) →
`templates/<conf>/style_papers/` (conference-level fallback). Dedup by basename, cap **3**.

## What v2 does (`StyleAgent.run` → returns a profile dict or None)

1. `load_paper` (first ~8 pages) per paper.
2. `segment_paper(text)` — split by section-heading detection into canonical sections
   (`abstract / introduction / related_work / method / evaluation / conclusion`).
3. `build_style_bank(...)` — first ~1–2 paragraphs per section per paper → **exemplar corpus**
   (`{section: [real passages]}`), capped.
4. `compute_structure_profile(...)` — measured facts: `section_order`,
   `avg_paragraph_chars`, `has_related_work`, `n_section_types_observed`.
5. LLM `style_extraction_prompt` (voice-focused; told the measured structure + bank sections
   so it doesn't restate them) → markdown summary. Visual mode (page grid) with text-only fallback.
6. Persist: `style_guide.md` (summary + structure + bank index, human-readable) +
   `style_bank.json` (full profile).

Return: `{"summary", "bank", "structure", "bank_path"}` or `None` (graceful no-op).

## Retrieval into writers (the core SOTA mechanism)

Helpers in `style_agent.py`:
- `style_summary(profile)` → str (for system prompt)
- `exemplars_block(profile, sections, max_per_section=1)` → formatted **real passages** (for user prompt)

- `HybridLiteratureAgent._synthesize_content`: summary → system prompt; exemplars for
  `["introduction", "related_work"]` → user prompt.
- `SectionWritingAgent.run`: summary → system prompt; exemplars for
  `["method", "evaluation", "conclusion", "introduction"]` → user prompt.

So each writer gets **concrete few-shot passages** for exactly the sections it writes.

## Code pointers

- `methods/agents/style_agent.py` — `StyleAgent`, `segment_paper`, `build_style_bank`,
  `compute_structure_profile`, `style_summary`, `exemplars_block`, `resolve_style_papers`
- `methods/prompts/style_agent.py` — voice-focused prompt (structure/bank placeholders)
- Pipeline: `methods/paper_writer.py` Step 1.5; `methods/paper_writer_with_plotting.py` parity
- CLI: `--style_references_dir`, `--use_style_learning` (default True; no-op if no papers)

## Gotchas / limits

- Section segmentation is a heading heuristic; mis-segmented papers fall back to fewer bank
  entries (non-fatal; writers just get fewer exemplars).
- Visual mode needs a vision-capable model; auto text-only fallback otherwise.
- Refinement agent does NOT yet consume the style profile (TODO: add a style-adherence axis).

## TODO / flesh out

- [ ] Confirm glm-5.2 vision for the visual summary step
- [ ] Add a style-adherence signal to the autorater/refinement loop
- [ ] Sentence-level templates (ZeroStylus 2nd granularity) — currently paragraph-level only
