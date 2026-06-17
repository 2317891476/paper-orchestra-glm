# LaTeX Compilation & Common Errors

> How the pipeline compiles `.tex` → `.pdf`, and the errors we've already hit.
> Status: **skeleton**. This is the troubleshooting hub (R1.1).

## Compiler

`utils/pdf_utils.py::compile_latex(cwd, pdf_file, texfile_name)` runs:

```
pdflatex → bibtex → pdflatex → pdflatex
```

(`-interaction=nonstopmode`, 30s timeout per step.)

## Local install (this machine)

- `texlive-latex-base/recommended/extra`, `texlive-fonts-recommended`,
  `texlive-bibtex-extra`, `texlive-science`, `latexmk` via Ubuntu apt.
- Apt mirror switched to Tsinghua (`/etc/apt/sources.list`) for speed.

## Errors we've hit & fixes

| Symptom | Cause | Fix |
| --- | --- | --- |
| PDF has body but **no title/abstract**; `nullfont` missing-char warnings | SectionWritingAgent dropped `\documentclass` + preamble | preamble safety net in `section_writing_agent.py` |
| `Undefined control sequence \toprule/\midrule/\bottomrule` | template missing `booktabs` | added `\usepackage{booktabs}` (+`multirow`) to HPCA template |
| `Undefined control sequence \fancypagestyle` | `fancyhdr` loaded after `\input{hpca-template}` | keep `\usepackage{fancyhdr}` before the `\input` |
| `No such file or directory: 'pdflatex'` | LaTeX not installed | install texlive (see above) |
| Garbled glyphs in some viewers | Computer Modern Type1 + Builtin encoding | viewer issue; open in Chrome/Edge or re-distill with ghostscript |

## Compiling by hand

```bash
cd <dir with main.tex + deps>
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

## TODO / flesh out

- [ ] Add Overleaf-export checklist (which files to include)
- [ ] Font-embedding / viewer-compatibility recipe
