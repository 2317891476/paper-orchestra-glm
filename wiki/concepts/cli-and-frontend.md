# CLI, Frontend & Batch

> Entry points: CLI, Streamlit demo, batch runner.
> Status: **skeleton**.

## CLI — `paper_writing_cli.py`

Key flags (defaults reflect this fork):

| Flag | Default | Note |
| --- | --- | --- |
| `--raw_materials_dir` | (required) | must contain `idea_sparse.md`, `experimental_log.md` |
| `--latex_template_dir` | (required) | e.g. `templates/hpca2027` |
| `--output_dir` | auto-timestamp | raw_materials are copied in |
| `--writer_model_name` | `glm-5.3` | writer + literature |
| `--reflection_model_name` | `glm-5.3` | refinement reviewer |
| `--research_cutoff` | current `YYYY-MM` | literature cutoff |
| `--use_plotting` | `false` | enable PlottingAgent |
| `--plotting_model_name` | `glm-5.3` | |
| `--image_model_name` | gemini image | vision for plotting |
| `--local_references_dir` | auto (`<raw>/references/`) | user PDF/.bib, always-citable ([local-references](local-references.md)) |
| `--style_references_dir` | auto (`<raw>/style_references/`) | best-paper PDFs for style learning |
| `--use_style_learning` | `true` | StyleAgent on/off (no-op if no papers) |
| `--stages` | all | comma-list to run a subset, **resume-safe** |
| `--from_stage` | (none) | run from this stage to the end (overrides `--stages`) |

## Running individual stages (resume-safe)

Stages: `outline → style → literature → section → refinement`. You can run a subset and
resume from existing artifacts in `--output_dir`:

```bash
# just regenerate the outline
python paper_writing_cli.py ... --stages outline

# rerun section + refinement only (e.g. after a prompt tweak), reusing outline/literature/style
python paper_writing_cli.py ... --from_stage section

# rerun literature and everything after it
python paper_writing_cli.py ... --from_stage literature
```

**Resume-safety guarantees** (in `methods/paper_writer.py`):
- Stage mode never wipes `latex_writeup/`; only the `refinement` stage clears its own workdir.
- Re-running `literature` first restores the RAW `template.tex` (prevents double-injection —
  literature reads and overwrites `template.tex`).
- Later stages assert their upstream artifacts exist (clear error, no silent crash).
- `style` profile is reused: if `style_bank.json` exists in `--output_dir`, literature/section
  load it even when the `style` stage isn't re-run.
- Plotting path (`--use_plotting`) delegates stage subsets to the non-plotting runner (plotting
  is a full-pipeline feature, not individually selectable).

Full run (no `--stages`/`--from_stage`) keeps the original wipe + 3× retry behavior.

## Utility scripts (repo root)

| Script | Purpose |
| --- | --- |
| `check_paper.py` | **Format checker** — validates PDF against template's `format.yaml` (13 checks). Runs **automatically** after pipeline + enrichment. Also standalone: `python check_paper.py --paper_dir X --template_dir templates/Y`. Compile artifacts are resolved robustly (`raw_draft_paper.*` → `final_refined_paper.*` → newest PDF-backed `*.log`/`*.tex` across `latex_writeup/` + `content_refinement_workdir/`) so rejected iteration attempts can't shadow the shipped compile. `Tables` check: `\hline`-only or `\hline`-dense tabulars vs booktabs style → WARN (Research-Paper-Writing-Skills, MIT). `AI Slop` check (2026-09-23): EN+ZH LLM-pattern lexicon + negative parallelism + em-dash density → WARN (Wikipedia "Signs of AI writing" via claude-scholar, MIT). |
| `rebuttal_writer.py` | **Rebuttal letter generator** (standalone, 2026-09-23) — point-by-point responses from reviews + the paper tex. Reviews from `--reviews_file` (md/txt/JSON incl. agent_review dicts) or `--self_review` (simulated via autoraters). Per-concern classification (factual-clarification / wording-change / new-experiment / limitation-acknowledge / out-of-scope), responses grounded with quoted paper passages, `[NEW EXPERIMENT]` marker never claims run. Output `<paper_dir>/rebuttal/rebuttal_letter.md`. |
| `enrich_paper.py` | Add citations to an existing paper (see [enrich-paper](enrich-paper.md)). Now runs format check after enrichment if `--template_dir` given. |
| `fast_dac_draft.py` | Quick DAC draft from a method .md (outline+section only, no literature/refinement) |
| `optimize_papers.py` | Re-run outline+section with `concepts/` implementation docs folded into the materials |
| `translate_to_chinese.py` | Translate an English LaTeX paper to a readable Chinese PDF (xeCJK + xelatex) |

## Expected raw_materials layout

```
raw_material/
├── idea_sparse.md
├── experimental_log.md
└── figures/            # .pdf/.png/.jpg; info.json optional
```

## Streamlit — `frontend/`

- `frontend/app.py` — interactive UI; paste idea + log, upload figures, run, email PDF.
- Run: `streamlit run frontend/app.py` (see `frontend/README.md`).

## Batch — `methods/paper_writer.py::run_batch_writeup`

Processes a folder of papers in parallel (`max_workers`). Resumable via
`paper_writing_log.json`. Drives the original paper's experiments, not the typical
single-paper use case.

## Notes / gotchas

- CLI copies `raw_materials` into `output_dir/raw_materials` (so the run is self-contained).
- If `--use_plotting false` and no figures exist, you get a warning (compile may fail later).

## TODO / flesh out

- [ ] Document `frontend/examples/cvpr_example.json` as the input shape reference
- [ ] Batch config (`process_root_folder` vs `paper_info_path`)
