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
| `--writer_model_name` | `glm-5.2` | writer + literature |
| `--reflection_model_name` | `glm-5.2` | refinement reviewer |
| `--research_cutoff` | current `YYYY-MM` | literature cutoff |
| `--use_plotting` | `false` | enable PlottingAgent |
| `--plotting_model_name` | `glm-5.2` | |
| `--image_model_name` | gemini image | vision for plotting |

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
