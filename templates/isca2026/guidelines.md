# ISCA 2026 Paper Writing Guidelines

Instructions for the LaTeX writing process for ISCA 2026 (53rd IEEE/ACM International Symposium
on Computer Architecture). ISCA uses the **IEEE `IEEEtran`** conference class.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
ISCA reviewing is **double-blind**.
- The author block holds the **submission banner** ("ISCA 2026 Submission #... -- Confidential Draft"), NOT real authors.
- No identifying info; anonymize artifact links.
- Self-cite in third person with full citation.

## Paper Length
Maximum **11 pages** of two-column text, **not including references**. No page limit for
references. **List ALL authors** in every reference (no "et al.").

## Formatting (enforced by IEEEtran)
- Paper: US Letter 8.5in × 11in
- 2-column, single-spaced; body 10pt Times, leading 12pt
- Margins: top 0.75in, bottom 1in, left/right 0.625in
- `\bibliographystyle{IEEEtranS}`
- Do not manipulate vertical space.

## Structure notes
- IEEEtran: `\title{}`, `\author{}` (banner), then `\maketitle`, then `\begin{abstract}` (abstract AFTER maketitle).
- `\newcommand{\iscasubmissionnumber}{...}` holds the submission number for the banner.
- `booktabs`, `multirow`, `cleveref` are loaded by this template.

## Figures and Tables
- `booktabs` for tables; figures in `figures/` with the `figures/` prefix.
- Reference every figure/table in text; grayscale-legible.
- Single-column figures unless genuinely wide.

## Page Budget (section allocation)

| Section | Pages |
|---------|-------|
| Abstract | 0.3 |
| Introduction | 1.5 |
| Background & Motivation | 1–1.5 |
| Method / Architecture Design | 3–4 |
| Implementation | 0.5–1 |
| Evaluation Setup | 0.5–1 |
| Results & Ablation | 3–4 |
| Related Work | 0.5–1 |
| Conclusion | 0.3 |
| **Total** | **~11** |

The outline and section-writing agents should use this budget to allocate content depth per section.

## Important Rules
- Keep the IEEEtran preamble unchanged.
- Ensure all `\begin`/`\end` pairs match.
- References must list all authors.
