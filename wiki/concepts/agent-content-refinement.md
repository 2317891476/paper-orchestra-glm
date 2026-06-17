# Agent — Content Refinement

> Stage 4: review → revise → score-gated accept, then a formatting pass.
> Status: **skeleton**.

## Role

`ContentRefinementAgent` compiles the draft, generates a simulated peer review
(`autoraters/agent_review.py`), revises the LaTeX to address weaknesses, and only
**accepts a revision if the overall score improves**. A separate formatting loop fixes
layout issues found by a VLM looking at PDF screenshots.

## Code pointers

- Agent: `methods/agents/content_refinement_agent.py` — `ContentRefinementAgent`
- Prompt: `methods/prompts/content_refinement_agent.py` — `content_refinement_agent_system_prompt`
- Reviewer: `autoraters/agent_review.py` — `perform_review_agentreview`
- Compile: `utils/pdf_utils.py::compile_latex`

## The score-gated loop (core mechanism)

For each iteration (up to `max_reflections`, default 3):
1. Revise LaTeX from previous review feedback.
2. Compile → simulate review → new score.
3. **Accept** if overall ↑ (or neutral with sub-axis gain ≥ drop); **revert** if ↓.

This is why a revision can lower the score and the system correctly keeps the prior draft
(verified 2026-06 on BugHypo-HW: 4→1 reverted → final 4).

## Notes / gotchas

- The work dir must contain all LaTeX deps (`.cls`, `.bst`, `hpca-template.tex`, `figures/`,
  `references.bib`). In `write_single_paper` this is set up via `shutil.copytree`; when
  running the agent standalone, copy `latex_writeup/*` into the work dir first.
- Reviewer uses the same `LLM_BACKEND` as the writer (fixed in this fork — was hardcoded Gemini).

## TODO / flesh out

- [ ] Document the three accept/reject cases + the metrics extraction
- [ ] Formatting loop details (`_get_formatting_review`)
