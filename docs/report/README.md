# Report figures (pgfplots)

Vector bar charts for the LaTeX report, drawn natively by `pgfplots` so they
use the document's fonts and stay sharp at any zoom.

| File | Content |
|---|---|
| `figures/style.tex` | Shared colours (from `design-system/tokens.css`) and the `hbarchart` style |
| `figures/requirement-statements.tex` | 154 requirement statements by readiness for deterministic rules |
| `figures/constraint-families.tex` | 84 deterministic parameters by hard-constraint family |
| `figures-preview.tex` / `.pdf` | Standalone document showing both figures with captions |

## Use in the report

Preamble:

```latex
\usepackage{pgfplots}
\input{figures/style.tex}
```

Body:

```latex
\begin{figure}[t]
  \centering
  \input{figures/requirement-statements.tex}
  \caption{...}
  \label{fig:requirement-statements}
\end{figure}
```

Each figure file contains only the `tikzpicture`: titles and notes belong in
`\caption`. `width` in each file sets the plot area only (tick labels sit
outside it); lower it if your text block is narrower than A4 with 2.5 cm margins.

Preview: `pdflatex figures-preview.tex` (needs `pgfplots` and `lmodern`).
