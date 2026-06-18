# ASPLOS 2026 Paper Writing Guidelines

Instructions for the LaTeX writing process for ASPLOS 2026 (31st International Conference on
Architectural Support for Programming Languages and Operating Systems). ASPLOS uses the
**ACM `acmart` SIGPLAN proceedings** template.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
ASPLOS reviewing is **double-blind** during review (the `anonymous` class option is set).
- No author/affiliation info; no acknowledgments in submission.
- Anonymize artifact links. Self-cite in third person with full citation.

## Template
- `\documentclass[sigplan, 10pt, review, anonymous]{acmart}`.
- SIGPLAN format. Keep the acmart preamble unchanged.
- In acmart, **abstract + `\keywords` come BEFORE `\maketitle`**.

## Paper Length
Follow the ASPLOS 2026 CFP page limit (typically ~12 pages excl. references, but verify on the
CFP). **List ALL authors** in every reference (no "et al."). No page limit for references.

## Figures and Tables
- `booktabs` for tables; figures in `figures/` with the `figures/` prefix.
- Reference every figure/table; grayscale-legible.
- `\bibliographystyle{ACM-Reference-Format}`.

## Scope note
ASPLOS spans architecture + compilers/PL + OS/runtime. Frame contributions to resonate across
these communities (e.g., quantify both hardware-level and software-level benefits).

## Important Rules
- Keep the acmart preamble unchanged; do not switch document class or compress spacing.
- All `\begin`/`\end` pairs must match. Leave `\begin{acks}` commented out for submission.
