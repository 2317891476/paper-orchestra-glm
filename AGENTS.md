# AGENTS.md — PaperOrchestra (personal fork)

Operating manual for any AI agent working in this repo. **R1 (wiki sync) is
duplicated here so it cannot be missed, regardless of which file an agent reads first.**

## Repository map

```
paper_writing_cli.py        # CLI entry point
methods/
  agents/                   # Outline / Literature / Section / Refinement / Plotting agents
  prompts/                  # System prompts for each agent
  paper_writer.py           # orchestrates the 4-stage pipeline (no plotting)
  paper_writer_with_plotting.py
utils/
  llm_backend_utils.py      # unified LLM routing (Gemini | OpenAI-compatible)
  gemini_utils.py           # lazy Gemini client
  openai_utils.py           # lazy OpenAI-compatible client (supports OPENAI_BASE_URL)
  scholar_utils.py          # Semantic Scholar search
  pdf_utils.py              # compile_latex, PDF<->text/image
  prompt_utils.py
templates/<conf>/           # template.tex + guidelines.md + venues.md + references.bib
autoraters/                 # citation_f1, agent_review, sxs quality
frontend/                   # Streamlit demo
wiki/                       # THIS PROJECT'S KNOWLEDGE BASE (see R1)
```

## Before you change anything

1. Read `CLAUDE.md` (project context + R1).
2. Check `wiki/INDEX.md` for the current state and `wiki/devlog/` for recent changes.
3. Find the concept doc that covers the subsystem you're about to touch.

## Verified current configuration (re-check before relying on it)

- `LLM_BACKEND=openai_compatible`, model `glm-5.3`, base URL = Zhipu coding endpoint.
- Active template: `templates/hpca2027/` (IEEEtran, with `hpca-template.tex` header).
- `pdflatex` / `bibtex` / `latexmk` installed system-wide (Ubuntu, Tsinghua mirror).

---

# R1 — Mandatory Wiki Sync Rule (NON-NEGOTIABLE)

> **Every code/template change MUST update the wiki in the same change.**
> "I'll sync the wiki later" is a rules violation, not a plan.

## R1.1 — Trigger → wiki map

| Change | Must update (same change) |
| --- | --- |
| `methods/agents/*.py` · `methods/prompts/*.py` | `wiki/concepts/agent-*.md` + devlog |
| `utils/{llm_backend_utils,gemini_utils,openai_utils}.py` | `wiki/concepts/llm-backend-routing.md` + devlog |
| `templates/<conf>/` files | `wiki/concepts/latex-templates.md` + devlog |
| build/compile logic, package deps | `wiki/concepts/latex-compilation.md` + devlog |
| `autoraters/` | `wiki/concepts/autoraters.md` + devlog |
| `paper_writing_cli.py` · `frontend/` | `wiki/concepts/cli-and-frontend.md` + devlog |
| add/rename/delete file | `wiki/INDEX.md` (+ concept doc) + devlog |
| behavior change (default, routing, output, env var) | concept doc **+ `INDEX.md` timeline** + devlog |

## R1.2 — Devlog append format

Append to `wiki/devlog/YYYY-MM.md` (newest entry at TOP):

```
## YYYY-MM-DD — <short title>
- **Changed**: <files / what>
- **Why**: <reason>
- **Wiki**: <concept docs updated>
- **Verified**: <how confirmed, or "NOT YET">
```

## R1.3 — Anti-patterns (violations)

- ❌ Deferring wiki sync ("下次再 sync").
- ❌ Code change with no devlog append.
- ❌ Wiki referencing a deleted/renamed symbol (drift).
- ❌ Experimental state in `INDEX.md` timeline.
- ❌ Code pasted into wiki without `file:line`.
- ❌ New concept file not registered in `INDEX.md`.
- ❌ "Verified" claimed without actually checking.

## R1.4 — Pre-finish self-check

1. Code/templates changed? → R1.1 applies.
2. Devlog appended (R1.2 format)?
3. Concept doc(s) updated?
4. New files in `INDEX.md`?
5. Every "Verified" actually verified?

Not all yes ⇒ task not done.

## Agent workflow for a change

1. Make the code change.
2. Run it (or at least import/syntax-check).
3. Update the concept doc(s) from R1.1 — fix any `file:line` pointers.
4. Append a devlog entry (R1.2), set `Verified` truthfully.
5. Update `INDEX.md` timeline if it's a landed milestone.
6. Then (and only then) consider the task complete.
