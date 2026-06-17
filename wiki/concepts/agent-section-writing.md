# Agent — Section Writing

> Stage 3: fill all remaining sections → `raw_draft_paper.tex`.
> Status: **skeleton**. This agent has the **preamble safety net** added in this fork.

## Role

`SectionWritingAgent` takes the outline + citation map + figures + idea/log, and writes
the LaTeX for every section not already produced by the literature agent. Builds tables
from the experimental log, inserts figures, cites from the reference library.

## Code pointers

- Agent: `methods/agents/section_writing_agent.py` — `SectionWritingAgent`
- Prompt: `methods/prompts/section_writing_agent.py` — `section_writing_agent_prompt`
- Backend call: `utils/llm_backend_utils.py::call_llm_with_images` (multimodal — sees figures)

## The preamble safety net (R1-critical)

LLMs frequently **drop the LaTeX preamble** (`\documentclass` + `\usepackage`) when asked
to "return the full template". This produces a PDF with body text but **no title/abstract**
(see [latex-compilation](latex-compilation.md)).

`_restore_preamble_if_missing(latex, template)`:
- If generated LaTeX lacks `\documentclass`, splice the preamble from the original template.
- Boundary markers: `\pdfpagewidth`, `\newcommand{\hpcayear}`, `\begin{document}`.

> If you touch this function, update this doc + devlog (R1.1).

## Inputs / outputs

- In: outline.json, template.tex, idea.md, experimental_log.md, citation_map.json,
  figures/info.json, guidelines.md
- Out: `raw_draft_paper.tex`

## Notes / gotchas

- Only raster figures (`.png/.jpg`) are passed to the VLM; PDFs are skipped.
- Prompt enforces `booktabs` table style → template must load `booktabs`.

## TODO / flesh out

- [ ] `figures/info.json` schema
- [ ] Known issue: figures not referenced in text
