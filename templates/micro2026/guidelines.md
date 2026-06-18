# MICRO 2026 Paper Writing Guidelines

Instructions for the LaTeX paper writing process for MICRO 2026 (59th IEEE/ACM International
Symposium on Microarchitecture). MICRO uses the **ACM `acmart`** class (`sigconf`).

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
MICRO reviewing is **double-blind**.
- **No author/affiliation info** anywhere (the template's author block is intentionally blank).
- **No acknowledgments** in the submission (do not use `\begin{acks}`).
- Fully anonymize any artifact links (e.g., GitHub).
- Self-citation: refer to your own prior work in the third person with a full citation.

## Paper Length
Maximum **11 pages** of two-column text, **not including references**. No page limit for
references. **No Appendix** is allowed. **Each reference must list ALL authors** (no "et al.").

## Formatting (enforced by the acmart template)
- Paper: US Letter 8.5in × 11in
- Margins: top/bottom 1in, left/right 0.75in
- Body: 2-column, single-spaced, 0.25in between columns
- Body font: 9pt Times; line leading 11pt
- Section headings: 12pt; subsection: 10pt; captions: ≥9pt
- References: 8pt
- **Do NOT compress spacing** (`\vspace`, space-squeezing packages) — submissions are
  auto-inspected and rejected if denser than the template.

## acmart-specific structure (IMPORTANT)
- `\documentclass[sigconf, screen, review]{acmart}`.
- The **abstract and `\keywords` MUST appear BEFORE `\maketitle`** (acmart requirement).
- The submission banner goes in `\subtitle{}` (keep the "MICRO 2026 Submission #... -- Confidential Draft" line).
- Keep `\setcopyright{none}`, `\settopmatter{printfolios=true, printacmref=false}` for the submission version.

## Mathematics
Number displayed equations with `\label{}` and reference via `\cref{}`.

## Figures and Tables
- Use `booktabs` (`\toprule/\midrule/\bottomrule`) for tables.
- Figures in the `figures/` dir; always use the `figures/` prefix in `\includegraphics`.
- Reference every figure/table in the text. Ensure legibility in grayscale.
- acmart prefers single-column figures (`\begin{figure}`) unless a figure is genuinely wide.

## Important Rules
- Keep the acmart preamble unchanged; do not switch document class.
- `\usepackage{booktabs}`, `multirow`, and `cleveref` are already loaded by this template.
- Ensure all `\begin`/`\end` pairs match (`figure*` ↔ `figure*`, etc.).
- Author placeholder: leave the author block blank (double-blind).
