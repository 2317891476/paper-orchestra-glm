# CLAUDE.md — PaperOrchestra (personal fork)

This file gives Claude Code the project context and the **R1 wiki-sync rule** that
governs every change.

## What this project is

PaperOrchestra is a multi-agent framework that turns raw research materials
(`idea_sparse.md` + `experimental_log.md`) into a submission-ready LaTeX paper.
Pipeline: **Outline → Literature Review → Section Writing → Content Refinement → PDF**.

This fork adapts the original Google Research code to:
- use **any OpenAI-compatible LLM** (GLM-5.2 by default) via `LLM_BACKEND` routing,
- target **HPCA 2027** (with per-template venue targeting via `venues.md`),
- compile locally with a system `pdflatex`.

## Key facts (verify before relying on these — code may have moved)

- Entry point: `paper_writing_cli.py`
- Backend routing: `utils/llm_backend_utils.py` (`LLM_BACKEND` env: `auto` | `openai_compatible` | `gemini`)
- Agents: `methods/agents/*.py`, prompts: `methods/prompts/*.py`
- Templates: `templates/<conf>/{template.tex, guidelines.md, venues.md, references.bib}`
- Config: `.env` (`LLM_BACKEND`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `SEMANTIC_SCHOLAR_API_KEY`)
- Run env: conda env `paper_orchestra` (Python 3.11)

## The wiki lives in `wiki/`

- `wiki/INDEX.md` — homepage + cheat sheet + timeline
- `wiki/concepts/` — 11 concept articles (one per subsystem/agent)
- `wiki/devlog/` — monthly append-only dev logs
- `wiki/*.canvas` — Obsidian Canvas topology maps

---

# R1 — Mandatory Wiki Sync Rule (NON-NEGOTIABLE)

> **Every code/template change MUST update the wiki in the same change.**
> Never defer. "I'll sync the wiki later" is a rules violation, not a plan.

## R1.1 — Trigger conditions

When you do **any** of the following, you MUST also do the matching wiki update
**in the same commit/turn** (concept doc + `wiki/devlog/<month>.md` append):

| Change you make | Wiki you must update |
| --- | --- |
| `methods/agents/*.py` or `methods/prompts/*.py` | `wiki/concepts/agent-*.md` (matching agent) + devlog |
| `utils/llm_backend_utils.py`, `utils/gemini_utils.py`, `utils/openai_utils.py` | `wiki/concepts/llm-backend-routing.md` + devlog |
| `templates/<conf>/` (template.tex / guidelines.md / venues.md / references.bib) | `wiki/concepts/latex-templates.md` + devlog |
| Build / compile logic (`compile_latex`, package deps) | `wiki/concepts/latex-compilation.md` + devlog |
| `autoraters/` | `wiki/concepts/autoraters.md` + devlog |
| `paper_writing_cli.py` or `frontend/` | `wiki/concepts/cli-and-frontend.md` + devlog |
| Add / rename / delete a file | `wiki/INDEX.md` (+ concept doc if new subsystem) + devlog |
| Behavior change (default param, routing logic, output format, new env var) | relevant concept doc **+ `INDEX.md` timeline** + devlog |

## R1.2 — Devlog append format

Append to `wiki/devlog/YYYY-MM.md` (create if missing; newest entry at TOP):

```
## YYYY-MM-DD — <short title>
- **Changed**: <files / what>
- **Why**: <reason>
- **Wiki**: <which concept docs updated>
- **Verified**: <how you confirmed it works, or "NOT YET">
```

## R1.3 — Anti-patterns (these are violations)

- ❌ **"下次再 sync" / "回头补 wiki"** — deferring wiki sync is itself the bug R1 exists to kill.
- ❌ Changing code without appending to `wiki/devlog/`.
- ❌ Wiki describing a function/param/file that no longer exists (code drift).
- ❌ Writing throwaway/experimental state into `INDEX.md`'s timeline (timeline = landed milestones only).
- ❌ Pasting code into the wiki without a `file:line` pointer (it will rot).
- ❌ Adding a concept file without registering it in `wiki/INDEX.md`.
- ❌ Claiming "Verified" in a devlog entry without actually having run/checked it.

## R1.4 — Self-check before finishing any task

1. Did this change touch code/templates? → R1.1 applies.
2. Did I append a devlog entry with the format in R1.2?
3. Did I update the concept doc(s) R1.1 points to?
4. Did I add new files to `INDEX.md`?
5. Is every "Verified" claim actually verified?

If any answer is no, the task is **not done**.
