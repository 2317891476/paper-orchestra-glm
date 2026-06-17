# Agent — Outline

> Stage 1: turn idea + experimental log into a structured paper outline (JSON).
> Status: **skeleton**.

## Role

Reads the raw materials + target template + guidelines, produces `outline.json`:
section hierarchy, per-subsection bullets, citation hints, and a plotting plan.

## Code pointers

- Agent: `methods/agents/outline_agent.py` — `OutlineAgent`
- Prompt: `methods/prompts/outline_agent.py` — `outline_agent_system_prompt`
- Output schema keys: `plotting_plan`, `intro_related_work_plan`, `section_plan`

## Inputs / outputs

- In: `idea_sparse.md`, `experimental_log.md`, `template.tex`, `guidelines.md`, `cutoff_date`
- Out: `outline.json` (drives stages 2–3)

## Notes / gotchas

- Prompt is domain-neutral ("senior researcher"); domain comes from `guidelines.md`.
- The `plotting_plan` is only consumed when `--use_plotting true`.

## TODO / flesh out

- [ ] Document the full `outline.json` schema with an example
- [ ] Common failure: outline JSON malformed → how it's handled
