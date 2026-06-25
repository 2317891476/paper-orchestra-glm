# LaTeX Compilation & Common Errors

> How the pipeline compiles `.tex` → `.pdf`, and the errors we've already hit.
> Status: **skeleton**. This is the troubleshooting hub (R1.1).

## Compiler

`utils/pdf_utils.py::compile_latex(cwd, pdf_file, texfile_name)` runs:

```
pdflatex → bibtex → pdflatex → pdflatex
```

(`-interaction=nonstopmode`, 30s timeout per step.)

### Engine selection (auto)
`compile_latex` reads the first ~2 KB of `{texfile}.tex` and picks the engine:
- **XeLaTeX** when it sees `% !TeX program = xelatex`, `ctex*` documentclass, or `\usepackage{xeCJK}`
  (Chinese templates). XeLaTeX's first run is slow (font-cache setup) → timeout bumped to ≥120s.
- **pdfLaTeX** otherwise (IEEE/ACM English templates).
bibtex runs in both cases (works under xelatex). Requires `texlive-xetex` + `texlive-lang-chinese`.

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
| Wide comparison table overflows the margin (`Overfull \hbox` ~50pt+) | many `p{}` columns sum beyond text width | wrap the `tabular` in `\resizebox{\linewidth}{!}{…}` (auto-scales to page width) |
| Chinese template fails to compile | needs XeLaTeX + ctex, not pdfLaTeX | `compile_latex` auto-selects xelatex for ctex/xeCJK; install `texlive-xetex` + `texlive-lang-chinese` |

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
