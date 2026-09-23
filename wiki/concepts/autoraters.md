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

## Tri-state verdicts (added 2026-09-23)

Alongside the numeric scores, reviews now carry a `Verdicts` object with five
rejection-risk dimensions (adapted from
[Research-Paper-Writing-Skills](https://github.com/Master-cai/Research-Paper-Writing-Skills),
MIT): `Contribution`, `Writing_Clarity`, `Experimental_Strength`,
`Evaluation_Completeness`, `Method_Soundness` — each exactly one of
`pass` / `needs_revision` / `needs_new_experiment` (the last marks gaps only
new experiments can close).

- `normalize_verdicts(review)` coerces raw LLM output to the allowed values
  and drops malformed dimensions; applied to every review and the meta-review.
- Ensemble mode: majority vote per dimension across the N reviewers.
- The refinement loop's score gate still uses the numeric axes; verdicts are
  advisory signal (surfaced in review JSON / worklogs).

## Notes / gotchas

- `Overall` is the score the refinement loop optimizes (0–10).
- `sxs_paper_quality.py` still imports gemini/openai directly (not yet routed) — only
  matters if you use the side-by-side eval tools.

## TODO / flesh out

- [ ] Document the review JSON schema fully
- [ ] Route `sxs_paper_quality.py` through the unified backend too
