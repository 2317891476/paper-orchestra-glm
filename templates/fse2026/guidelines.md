# FSE 2026 Paper Writing Guidelines

Instructions for the LaTeX writing process for FSE 2026 (ACM International Conference on the
Foundations of Software Engineering). FSE 2026 uses the **PACMSE** (Proceedings of the ACM
on Software Engineering) format — single-column journal style.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
FSE 2026 uses **double-anonymous** review.
- `anonymous` + `review` options are set in the documentclass.
- No author info; no acknowledgments.
- Anonymize artifact links (GitHub repos etc.).
- Self-cite in third person with full citation.

## Paper Length
- **18 pages** single-column (including all text and figures)
- Plus up to **4 additional pages** for references only
- Total maximum: **22 pages**

## Page Budget (section allocation)

| Section | Pages |
|---------|-------|
| Abstract | 0.3 |
| Introduction | 2 |
| Background | 1–2 |
| Approach / Methodology | 4–5 |
| Study Design / Experimental Setup | 2 |
| Results and Analysis | 4–5 |
| Discussion & Threats to Validity | 1.5–2 |
| Related Work | 1.5 |
| Conclusion | 0.5 |
| **Total** | **~18** |

The outline and section-writing agents should use this budget to allocate content depth per section.
FSE papers are **empirical/software engineering** focused — emphasize study design (RQs),
methodology rigor, and threats to validity.

## Formatting (acmart manuscript mode)
- `\documentclass[manuscript,review,anonymous]{acmart}`.
- In acmart, abstract + `\keywords` come BEFORE `\maketitle`.
- `\bibliographystyle{ACM-Reference-Format}`.
- Single-column layout (PACMSE journal style).
- Keep the acmart preamble unchanged.

## Mathematics
Number displayed equations with `\label{}` and reference via `\cref{}`.

## Figures and Tables
- `booktabs` for tables; figures in `figures/` with the `figures/` prefix.
- Single-column format means figures can be wider; use `\linewidth` freely.
- Reference every figure/table; ensure grayscale legibility.

## Algorithms and Code
- Use `algorithm` + `algpseudocode` for algorithms (already loaded).
- Use `listings` for code snippets (already loaded, with basic Java style).

## Important Rules
- Keep the acmart preamble unchanged.
- `\usepackage{booktabs}`, `multirow`, `subcaption`, `algorithm`, `algpseudocode`, `listings`
  are already loaded by this template.
- All `\begin`/`\end` pairs must match. Leave `\begin{acks}` commented out for submission.
- List ALL authors in references (no "et al.").
- FSE values **empirical rigor**: state research questions (RQ1, RQ2...), describe methodology,
  report effect sizes/confidence intervals where appropriate, discuss threats to validity.
