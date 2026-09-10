# Agent — Plotting

> Optional stage 2.5: generate figures (plots + diagrams) from code.
> Status: **skeleton**. Only runs with `--use_plotting true`.

## Role

`PlottingAgent` turns the `plotting_plan` from the outline into actual figures:
retrieve examples → predict content → style refine → generate visual → critique-revise
→ caption. Enabled via `--use_plotting true`.

## Code pointers

- Agent: `methods/agents/plotting_agent.py` — `PlottingAgent`
- Orchestrator: `methods/paper_writer_with_plotting.py::write_single_paper`
- Image model: `--image_model_name` (Gemini image preview by default)

## CLI flags

- `--use_plotting true`
- `--plotting_model_name glm-5.3`
- `--image_model_name <vision model>`
- `--plotting_max_critic_rounds 3`

## Notes / gotchas

- The image-generation path currently leans on Gemini's image model; GLM/OpenAI-compatible
  image generation may need adaptation. **Verify before relying on this** (R1: not yet tested
  with GLM-5.3 in this fork).

## TODO / flesh out

- [ ] Confirm plotting works end-to-end on GLM-5.3 (or document the gap)
- [ ] Diagram vs plot generation paths
