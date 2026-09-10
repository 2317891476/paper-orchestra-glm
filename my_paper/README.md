# my_paper/ — example input folder

A ready-to-use template for one paper. Copy this folder, rename it, and fill in your content.

## Layout

```
my_paper/
├── idea_sparse.md          ← REQUIRED: problem / hypotheses / methodology / contributions
├── experimental_log.md     ← REQUIRED: datasets, metrics, result TABLES (markdown), ablations
├── figures/                ← OPTIONAL: your figures (png/jpg/pdf) + info.json manifest
│   └── info.json           ←   figure list: [{"name","caption"}]; [] if none
├── references/             ← OPTIONAL: local always-citable papers (*.bib and/or *.pdf)
└── style_references/       ← OPTIONAL: 1–3 target-venue "best paper" PDFs for style learning
```

Every file has inline guidance — open it and replace the placeholders.

## Run it

Full pipeline (GLM-5.3, HPCA template):

```bash
cd /home/illya/PaperOrchestra
conda activate paper_orchestra

python paper_writing_cli.py \
  --raw_materials_dir ./my_paper \
  --latex_template_dir templates/hpca2027 \
  --output_dir ./paper_output_my \
  --writer_model_name glm-5.3 \
  --reflection_model_name glm-5.3 \
  --research_cutoff 2025-06
```

`figures/`, `references/`, `style_references/` are auto-detected — no extra flags needed.

## Iterate by stage (resume-safe)

```bash
# only the outline
... --stages outline
# from section to the end (reuse existing outline/literature/style)
... --from_stage section
# just re-compile the PDF
... --stages refinement
```

Output lands in `--output_dir`; the final PDF is `paper_output_my/final_paper.pdf`.

See `../wiki/concepts/cli-and-frontend.md` for the full flag reference.
