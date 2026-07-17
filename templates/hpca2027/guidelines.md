# HPCA 2027 Paper Writing Guidelines

Below are the instructions to help you with the LaTeX paper writing process for HPCA 2027.

## Language
All manuscripts must be in English.

## Submission Policies & Anonymity
HPCA reviewing is double-blind. Authors must not know the names of the reviewers, and reviewers must not know the names of the authors.

* **No Identifying Information:** Do not provide information that may identify the authors in the acknowledgments or in the supplementary material.
* **Links:** Do not provide links to websites that identify the authors.
* **GitHub:** Links to GitHub must be anonymous.
* **Self-Citation:** If you need to cite any of your own papers that are being submitted concurrently, include anonymized versions in the supplementary material and cite them as anonymous. Do not use the words "my" or "our" when citing previous work; treat your own prior work as if it were written by someone else.

## Paper Length
Papers must be at most **11 pages** (not including references) in a two-column format. There is no page limit for references. Each reference must specify all authors (no "et al.").

## Formatting
* **Paper Size:** US Letter 8.5in x 11in
* **Top Margin:** 0.7in
* **Bottom Margin:** 1in
* **Left/Right Margin:** 0.7in
* **Body:** 2-column, single-spaced
* **Space Between Columns:** 0.1in
* **Line Spacing:** 12pt
* **Body Font:** 10pt, Times
* **Abstract Font:** 9pt, Times, bold
* **Section Headings:** 12pt, Small Caps, Roman Numbering (I, II, ...)
* **Subsection Headings:** 10pt, italic, Alpha numbering (A, B, ...)
* **Captions:** 9pt minimum
* **References:** 8pt, no page limit

## Mathematics
Please number all of your sections and displayed equations as in these examples:
```latex
\begin{equation}
  E = m\cdot c^2
  \label{eq:important}
\end{equation}
```

## Cross-references
Use the `\cref{...}` command for cross-referencing to figures, tables, equations, or sections.

## Figures and Tables
Ensure that figures and tables are legible. Please also ensure that you refer to your figures in the main text. If you use colors for your figures, ensure that the different colors are highly distinguishable in gray-scale.

## Example Code for Tables
```latex
\begin{table}[h!]
  \centering
  \caption{Results.}
  \label{tab:example}
  \begin{tabular}{|l|l|}
    \hline
    \textbf{Method} & \textbf{Accuracy} \\
    \hline
    Baseline & 85.2\% \\
    Ours & \textbf{92.1\%} \\
    \hline
  \end{tabular}
\end{table}
```

## Example Code for Figures
```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=0.8\linewidth]{figures/example.pdf}
  \caption{Example of caption.}
  \label{fig:example}
\end{figure}
```

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
* Keep the existing packages in the template unchanged.
* For consistent compilation across environments, all figures will reside in the `figures` directory. Always include the `figures/` prefix in your `\includegraphics` command.
* Always use the following author information placeholder in your writeup:
  * Ambitious AI Researcher, AI Research Institute, 123 AI Avenue, ML City, researcher@institute.ai
* Do NOT use "et al." in references — list all authors' names.
