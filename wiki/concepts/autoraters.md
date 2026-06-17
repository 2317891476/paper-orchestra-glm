# Autoraters (Automated Evaluation)

> Simulated reviewers / quality metrics used inside the pipeline and for batch eval.
> Status: **skeleton**.

## What's here (`autoraters/`)

| File | Role | Used in pipeline? |
| --- | --- | --- |
| `agent_review.py` | Multi-reviewer simulated peer review + meta-review | **Yes** — ContentRefinementAgent scoring |
| `citation_f1.py` | Citation precision/recall vs ground-truth (P0/P1) | batch eval only |
| `lit_review_quality.py` | Single-paper lit-review quality scoring | eval only |
| `sxs_paper_quality.py` | Side-by-side full-paper comparison | eval only |
| `sxs_lit_review_quality.py` | Side-by-side lit-review comparison | eval only |
| `prompts/*.py` | Reviewer system prompts | — |

## agent_review (the one that matters for writing)

- `perform_review_agentreview(text, model_name)` → dict with axes:
  Originality, Quality, Clarity, Significance, Soundness, Presentation, Contribution, Overall, Confidence.
- **This fork**: routed through `utils.llm_backend_utils.call_llm_with_text_prompt`
  (was hardcoded Gemini → caused 0.0 scores with GLM). See R1.1.
- Prompts made domain-neutral ("top-tier conferences in the target field").

## Notes / gotchas

- `Overall` is the score the refinement loop optimizes (0–10).
- `sxs_paper_quality.py` still imports gemini/openai directly (not yet routed) — only
  matters if you use the side-by-side eval tools.

## TODO / flesh out

- [ ] Document the review JSON schema fully
- [ ] Route `sxs_paper_quality.py` through the unified backend too
