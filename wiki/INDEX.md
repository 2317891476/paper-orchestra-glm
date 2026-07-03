# PaperOrchestra Wiki — Index

> Personal fork of [google-research/paper-orchestra](https://github.com/google-research/paper-orchestra).
> This fork: **GLM-5.2** backend + **HPCA 2027** target + local LaTeX compile.
> See `CLAUDE.md` / `AGENTS.md` for the **R1 wiki-sync rule** that governs this wiki.

## Cheat sheet

```bash
# Activate env
conda activate paper_orchestra

# Run the full pipeline (GLM-5.2, HPCA)
python paper_writing_cli.py \
  --raw_materials_dir ./raw_material \
  --latex_template_dir templates/hpca2027 \
  --output_dir ./paper_output \
  --writer_model_name glm-5.2 \
  --reflection_model_name glm-5.2 \
  --research_cutoff 2025-06
```

| Need | File |
| --- | --- |
| Pick LLM backend / model | `.env` → `LLM_BACKEND`, `OPENAI_*` |
| Change what papers get cited | `templates/hpca2027/venues.md` |
| Change formatting rules | `templates/hpca2027/guidelines.md` |
| Change an agent's behavior | `methods/prompts/*.py` (+ `methods/agents/*.py`) |
| Fix a compile error | [concepts/latex-compilation.md](concepts/latex-compilation.md) |

## Pipeline (5 stages)

`raw_material/` → **Outline** → **Literature** → **Section Writing** → **Content Refinement** → `final_paper.pdf`

## Concept articles (11)

**Pipeline & agents**
- [architecture-overview](concepts/architecture-overview.md) — the 5-stage multi-agent pipeline at a glance
- [agent-outline](concepts/agent-outline.md) — OutlineAgent
- [agent-style](concepts/agent-style.md) — StyleAgent (optional Step 1.5: style guide from best papers)
- [agent-literature-review](concepts/agent-literature-review.md) — HybridLiteratureAgent + venue targeting
- [local-references](concepts/local-references.md) — user-provided always-citable references (PDF + .bib)
- [agent-section-writing](concepts/agent-section-writing.md) — SectionWritingAgent + preamble safety net
- [agent-content-refinement](concepts/agent-content-refinement.md) — ContentRefinementAgent + score-driven loop
- [agent-plotting](concepts/agent-plotting.md) — PlottingAgent (figures from code)

**Infrastructure**
- [llm-backend-routing](concepts/llm-backend-routing.md) — Gemini vs OpenAI-compatible (GLM/DeepSeek/Ollama)
- [paper-search](concepts/paper-search.md) — multi-source search (DeepXiv + S2 + arXiv)
- [latex-templates](concepts/latex-templates.md) — template.tex / guidelines.md / venues.md / references.bib
- [latex-compilation](concepts/latex-compilation.md) — compile_latex + common errors (preamble loss, missing packages)

**Evaluation & interfaces**
- [autoraters](concepts/autoraters.md) — agent_review, citation_f1, sxs quality
- [cli-and-frontend](concepts/cli-and-frontend.md) — CLI flags + Streamlit demo + batch mode

**Generated works**
- [works](works.md) — catalog of papers produced with this fork (paths, venues, stats)
- [enrich-paper](concepts/enrich-paper.md) — add citations to an existing paper (reusable enrichment)

## Topology

- [pipeline.canvas](pipeline.canvas) — Obsidian Canvas of the 5-stage flow

## Dev logs (newest month first)

- [2026-07](devlog/2026-07.md)
- [2026-06](devlog/2026-06.md)

## Timeline (landed milestones only)

- **2026-07** — arXiv→formal publication resolution (DBLP+S2); GB/T 7714 国标 citation format for Chinese papers; enrichment post-cleanup (orphan removal + stronger prompt).
- **2026-06** — Chinese survey support: engine-aware `compile_latex` (auto xelatex for ctex/xeCJK) + `templates/software_se/` (ctexart survey) + `se_survey/` example. Generated an 8-page Chinese SE survey end-to-end.
- **2026-06** — Added `templates/{isca2026,asplos2026,dac2026}/` (ISCA IEEEtran + ASPLOS/DAC acmart). Architecture "big-three" + EDA now all covered.
- **2026-06** — Added `templates/micro2026/` (ACM `acmart` MICRO template) + `my_paper/` example input folder.
- **2026-06** — Added per-stage runner (`--stages` / `--from_stage`, resume-safe) to run/iterate individual pipeline stages.
- **2026-06** — Added **local references** (PDF + .bib, always-citable, `is_local` flag) and **StyleAgent** (Step 1.5, text+visual style guide from best papers); both optional, CLI-flagged.
- **2026-06** — Fork adapted to GLM-5.2 (OpenAI-compatible backend, `LLM_BACKEND` routing, lazy clients).
- **2026-06** — Added `templates/hpca2027/` with `venues.md` conference-specific literature targeting.
- **2026-06** — Made all prompts domain-neutral; domains now live in `guidelines.md` + `venues.md`.
- **2026-06** — Added preamble-safety-net to SectionWritingAgent; added `booktabs`/`multirow` to HPCA template.
- **2026-06** — Installed local `texlive`; pipeline now compiles to PDF end-to-end.
- **2026-06** — Seeded this wiki + `CLAUDE.md`/`AGENTS.md` with R1 sync rule.
