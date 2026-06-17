# LaTeX Templates

> How a conference template is defined: 4 files per `templates/<conf>/`.
> Status: **skeleton**.

## The 4 files every template needs

| File | Purpose | Consumed by |
| --- | --- | --- |
| `template.tex` | Main LaTeX skeleton (`\documentclass`, preamble, empty sections) | Outline, Section, Refinement agents |
| `guidelines.md` | Formatting rules + tone for the agents | all agents (domain context) |
| `venues.md` | Target conference list for literature search | HybridLiteratureAgent |
| `references.bib` | Seed bibliography | literature + compilation |

## Active templates

- `templates/hpca2027/` — IEEEtran, HPCA header via `hpca-template.tex`. Preamble loads
  `booktabs`, `multirow`, `cleveref` (added in this fork so tables compile).
- `templates/cvpr2025/` — CVPR (original).
- `templates/iclr2025/` — ICLR (original).

## Venue targeting (this fork)

`venues.md` lives next to `guidelines.md`. The literature agent reads it to bias paper
discovery toward the target community. Edit to retarget. See
[agent-literature-review](agent-literature-review.md).

## Adding a new template

1. Create `templates/<conf>/` with the 4 files (+ any `.sty`/`.cls`/`.bst`).
2. Make sure `template.tex` compiles standalone with `pdflatex` + `bibtex`.
3. Load `booktabs`/`multirow` if the section agent should make tables.
4. Register nothing extra — `--latex_template_dir templates/<conf>` is enough.

## Notes / gotchas

- HPCA's `\input{hpca-template}` pulls in `\begin{document}\maketitle`; abstract comes after.
- Author placeholder (per guidelines): "Ambitious AI Researcher, AI Research Institute…"

## TODO / flesh out

- [ ] Add a minimal template-authoring checklist
- [ ] Document `hpca-template.tex` header/footer logic
