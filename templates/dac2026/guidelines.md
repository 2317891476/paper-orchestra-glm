# DAC 2026 Paper Writing Guidelines

Instructions for the LaTeX writing process for DAC 2026 (63rd ACM/IEEE Design Automation
Conference). DAC is ACM-sponsored; this template uses the **ACM `acmart`** `sigconf` format.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
DAC review is **double-blind** (the `anonymous` + `review` class options are set).
- No author/affiliation info; no acknowledgments in submission.
- Anonymize artifact links. Self-cite in third person with full citation.

## Template
- `\documentclass[sigconf, anonymous, review]{acmart}`.
- In acmart, **abstract + `\keywords` come BEFORE `\maketitle`**.
- Keep the acmart preamble unchanged; do not compress spacing.

## Paper Length
DAC technical-paper page limits vary by year/track — verify on the DAC 2026 CFP. **List ALL
authors** in every reference (no "et al.").

## Scope note
DAC is **EDA / design automation** focused: logic synthesis, physical design, verification &
test, HLS, ML for EDA, hardware security. Frame contributions toward CAD/automation outcomes
(area/power/timing closure, tool throughput, QoR), not just architecture performance.

## Figures and Tables
- `booktabs` for tables; figures in `figures/` with the `figures/` prefix.
- Reference every figure/table; grayscale-legible.
- `\bibliographystyle{ACM-Reference-Format}`.

## Important Rules
- Keep the acmart preamble unchanged.
- All `\begin`/`\end` pairs must match. Leave `\begin{acks}` commented out for submission.
