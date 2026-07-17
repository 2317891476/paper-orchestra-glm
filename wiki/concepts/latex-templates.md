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

- `templates/hpca2027/` — **IEEEtran**; HPCA header via `hpca-template.tex`. Preamble loads
  `booktabs`, `multirow`, `cleveref` (added in this fork so tables compile).
- `templates/isca2026/` — **IEEEtran** (conference); ISCA 2026. Simpler than HPCA: submission
  banner is inline in `\author{}`, no `\input`. `\bibliographystyle{IEEEtranS}`.
- `templates/micro2026/` — **ACM `acmart`** (`sigconf`); MICRO 2026. Carries `acmart.cls` +
  `ACM-Reference-Format.bst`. Key difference: **abstract + `\keywords` go BEFORE `\maketitle`**,
  the submission banner is in `\subtitle{}`, double-blind (no `\begin{acks}`, blank authors),
  `\bibliographystyle{ACM-Reference-Format}`. No appendix allowed.
- `templates/asplos2026/` — **ACM `acmart`** (`sigplan, 10pt, review, anonymous`); ASPLOS 2026.
  Same acmart gotchas as MICRO; SIGPLAN format.
- `templates/dac2026/` — **ACM `acmart`** (`sigconf, anonymous, review`); DAC 2026. EDA-focused.
- `templates/software_se/` — **中文综述** (`ctexart`, XeLaTeX, A4 single-column); "前瞻科技" journal
  style. Survey structure (引言 / 国内外研究进展 / 关键技术挑战 / 发展趋势与建议 / 结束语);
  **GB/T 7714** bibliography format (`\usepackage[numbers,super]{gbt7714}` +
  `gbt7714-numerical.bst`) — produces `[C]`/`[J]` type markers, `et al.` after 3 authors.
  Chinese head macros. `compile_latex` auto-uses xelatex.
- `templates/cvpr2025/` — CVPR (original).
- `templates/iclr2025/` — ICLR (original).

## Venue targeting (this fork)

`venues.md` lives next to `guidelines.md`. The literature agent reads it to bias paper
discovery toward the target community. Edit to retarget. See
[agent-literature-review](agent-literature-review.md).

## Page budgets (`guidelines.md`)

Every hardware-conf `guidelines.md` carries a `## Page Budget (section allocation)` table
(inserted just before `## Important Rules`) that gives the outline and section-writing agents an
explicit per-section depth target so generated papers hit the venue page limit.

- **HPCA 2027 / ISCA 2026 / MICRO 2026 / ASPLOS 2026** share the **~11-page** budget: Abstract 0.3,
  Introduction 1.5, Background & Motivation 1–1.5, Method / Architecture Design 3–4, Implementation
  0.5–1, Evaluation Setup 0.5–1, Results & Ablation 3–4, Related Work 0.5–1, Conclusion 0.3.
- **DAC 2026** uses a **~6-page** budget (6+1 format, 7th page refs only): Abstract 0.2, Introduction
  0.5–0.8, Background & Motivation 0.5, Method / Design 1.5–2, Results & Ablation 1.5–2,
  Conclusion 0.2.

These are advisory allocations, not hard limits; the `## Paper Length` section remains authoritative
for the total.

## Adding a new template

1. Create `templates/<conf>/` with the 4 files (+ any `.sty`/`.cls`/`.bst`).
2. Make sure `template.tex` compiles standalone with `pdflatex` + `bibtex`.
3. Load `booktabs`/`multirow` if the section agent should make tables.
4. Register nothing extra — `--latex_template_dir templates/<conf>` is enough.

## Notes / gotchas

- HPCA's `\input{hpca-template}` pulls in `\begin{document}\maketitle`; abstract comes after.
- MICRO (acmart): abstract + `\keywords` come **before** `\maketitle`; banner in `\subtitle{}`.
- The section agent's preamble-safety-net splits on `\begin{document}`, which exists in BOTH
  IEEEtran and acmart skeletons — so it works for every current template.
- Author placeholder (per guidelines): "Ambitious AI Researcher, AI Research Institute…"

## TODO / flesh out

- [ ] Add a minimal template-authoring checklist
- [ ] Document `hpca-template.tex` header/footer logic
