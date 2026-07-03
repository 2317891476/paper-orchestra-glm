# Generated Works — Catalog

Papers generated with this fork of PaperOrchestra (GLM-5.2). Each entry lists the target
venue/template, source materials, and output paths. All outputs are local (gitignored).

> Paths are relative to the repo root (`/home/illya/PaperOrchestra/`).
> Open a PDF: e.g. `paper_output_g10/final_paper.pdf`.

---

## 1. BugHypo-HW — Multi-Agent Hardware Bug Detection (HPCA)

- **Template / venue**: `templates/hpca2027/` (IEEEtran, HPCA 2027)
- **Source**: `raw_material/` (idea_sparse.md + experimental_log.md, LLM-driven pre-silicon HW verification)
- **Outputs**:
  - `paper_output_bughypo_full/final_paper.pdf` — EN, 6p (canonical; GLM-5.2 full run)
  - `paper_output_bughypo/final_paper.pdf` — EN, 4p (early GLM-5.1 run; superseded)
- **Notes**: First end-to-end run; local refs + venue targeting validated here. Title/abstract once
  broken by preamble loss → fixed via the section-agent safety net.

## 2. G10 Reproduction — Unified GPU Memory & Storage (MICRO)

- **Template / venue**: `templates/micro2026/` (acmart sigconf, MICRO 2026)
- **Source**: `g10_paper/` (split from a 46 KB reproduction report of G10, MICRO '23)
- **Output**: `paper_output_g10/final_paper.pdf` — EN, 7p
- **Notes**: Refinement 3→6→8 (v2 kept, v3 reverted); 9 figures embedded; G10 cited after adding
  local refs (S2 was rate-limited). Wide-table overflow post-fixed via `\resizebox`.

## 3. LLM-Driven Software Engineering — Survey (前瞻科技, Chinese)

- **Template / venue**: `templates/software_se/` (ctexart / XeLaTeX, 前瞻科技 journal, Chinese)
- **Source**: `se_survey/` (split from `software/deep-research-report.md`, 46 KB)
- **Output**: `paper_output_se/final_paper.pdf` — ZH, 7p
- **Notes**: 综述与述评; refinement 4→8; 3 booktabs comparison tables; XeLaTeX engine auto-selected
  by `compile_latex`. ≥6-page course requirement met.

## 4. SoC-HiRCA — Evidence-Driven Static Root Cause Analysis (DAC)

- **Template / venue**: `templates/dac2026/` (acmart sigconf, DAC 2026)
- **Source**: `SoC-HiRCA：….md` + `paper_output_hirca/raw_materials/concepts/` (implementation docs)
- **Outputs**:
  - `paper_output_hirca/final_paper.pdf` — EN, 9p
  - `paper_output_hirca/final_paper_zh.pdf` — ZH, 7p (translated for reading)
- **Notes**: Fast draft (outline+section only, no literature); enriched with real implementation
  docs (pipeline/DesignIR/DSL). 0 fabricated results. Fixed `\argmin`/lstlisting issues.

## 5. LLM-StaticBugLens — Source-Only Static RTL Bug Localization (DAC)

- **Template / venue**: `templates/dac2026/` (acmart sigconf, DAC 2026)
- **Source**: `LLM-StaticBugLens：….md` + `paper_output_buglens/raw_materials/concepts/`
- **Outputs**:
  - `paper_output_buglens/final_paper.pdf` — EN, 9p
  - `paper_output_buglens/final_paper_zh.pdf` — ZH, 7p
- **Notes**: Same fast-draft flow as SoC-HiRCA; semantic-scaffolding + generate-and-critique method.

---

## Test / scratch outputs (not deliverables)

- `paper_output_style_test/` — StyleAgent v2 standalone test
- `paper_output_micro_test/`, `paper_output_stage_test/` — template/stage-runner smoke tests

## Regenerating any of these

```bash
conda activate paper_orchestra
# e.g. re-run G10 end-to-end:
python paper_writing_cli.py --raw_materials_dir ./g10_paper \
  --latex_template_dir templates/micro2026 --output_dir ./paper_output_g10 \
  --writer_model_name glm-5.2 --reflection_model_name glm-5.2
# fast DAC draft (no literature): see fast_dac_draft.py
# Chinese translation of a draft: see translate_to_chinese.py
```
