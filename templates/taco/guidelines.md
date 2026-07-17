# TACO Paper Writing Guidelines

Instructions for the LaTeX writing process for TACO (ACM Transactions on Architecture and Code
Optimization). TACO is an **ACM journal** using the `acmart` `acmsmall` format.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
TACO uses **single-blind or double-blind review** (check the current cycle). For double-blind:
- `anonymous` and `review` options are set in the documentclass.
- No author info; no acknowledgments.
- Anonymize artifact links. Self-cite in third person.

## Paper Length
- **Initial submission**: up to **20 pages** of two-column text (excluding references).
- **References**: typically 2–4 additional pages, no hard limit.
- **Total PDF**: approximately 21–24 pages.
- **Recommended target**: 17–19 pages body (leaves room for revision).

## Page Budget (section allocation)

| Section | Pages |
|---------|-------|
| Abstract | 0.3 |
| Introduction | 1.5–2 |
| Background & Motivation | 2–3 |
| Key Observations / Problem Analysis | 2–3 |
| Method & Microarchitecture Design | 4–6 |
| Implementation Details | 1–2 |
| Experimental Methodology | 1.5–2 |
| Experimental Results & Ablation | 5–7 |
| Related Work | 1–2 |
| Conclusion | 0.5 |
| **Total** | **~18–20** |

The outline and section-writing agents should use this budget to allocate content depth per section.
Journal papers are longer than conference papers — each section should have deeper analysis, more
figures/tables, and more thorough discussion than a typical 11-page conference paper.

## Formatting (acmsmall)
- `\documentclass[acmsmall,manuscript,review,anonymous]{acmart}`.
- In acmart, abstract + `\keywords` + CCS concepts come BEFORE `\maketitle`.
- `\bibliographystyle{ACM-Reference-Format}`.
- TACO requires **CCS concepts** (use `\ccsdesc` — placeholders in template).
- Keep the acmart preamble unchanged.

## Mathematics
Number displayed equations with `\label{}` and reference via `\cref{}`.

## Figures and Tables
- `booktabs` for tables; figures in `figures/` with the `figures/` prefix.
- Journal papers can use `figure*`/`table*` (spanning both columns) more freely than conferences.
- Reference every figure/table; ensure grayscale legibility.

## Important Rules
- Keep the acmart preamble unchanged.
- `\usepackage{booktabs}`, `multirow`, `subcaption` are loaded by this template.
- All `\begin`/`\end` pairs must match. Leave `\begin{acks}` commented out for submission.
- List ALL authors in references (no "et al.").
