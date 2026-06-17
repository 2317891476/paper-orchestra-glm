# Architecture Overview

> The 5-stage multi-agent pipeline at a glance. Start here.
> Status: **skeleton**. Update when pipeline shape changes (R1.1).

## What it does

Turns unstructured research materials into a submission-ready LaTeX PDF by splitting
"writing a paper" across specialized agents — like a human research team.

## The pipeline

```
raw_material/{idea_sparse.md, experimental_log.md, figures/}
   │
   ▼
1. OutlineAgent            → outline.json            (section plan + citation hints)
   │
   ▼
1.5 StyleAgent (optional)  → style_guide.md          (writing-style guide from best papers)
   │
   ▼
2. HybridLiteratureAgent   → updated_template.tex    (intro + related work)
   · + local references    references.bib            (real, S2-verified + user-provided citations)
     (optional, Phase 1.5) citation_map.json
   │
   ▼
3. SectionWritingAgent     → raw_draft_paper.tex     (all sections + tables + figures)
   │
   ▼
4. ContentRefinementAgent  → final_refined_paper.pdf (review → revise → score-gated accept)
   │
   ▼
   final_paper.pdf
```

Optional: **PlottingAgent** (stage 2.5, parallel) generates figures from code when
`--use_plotting true`.

## Orchestrators

- `methods/paper_writer.py::write_single_paper` — the 4-stage run (no plotting). Now a
  **per-stage runner**: pass `stages=` / `from_stage=` to run a resume-safe subset
  (see [cli-and-frontend](cli-and-frontend.md)). Stages share a context built by `_build_ctx`;
  each has a `_stage_*` function + a resume-safe `_prepare_for_stage` invariant.
- `methods/paper_writer_with_plotting.py::write_single_paper` — adds plotting; delegates
  stage subsets to the non-plotting runner.
- `methods/paper_writer.py::run_batch_writeup` — parallel many papers.

## Key design principles

- **Decomposition**: each agent owns one cognitive task → low load, fewer hallucinations.
- **External truth anchors**: Semantic Scholar (real citations), `pdflatex` (must compile),
  PDF screenshots + VLM (format checking).
- **Score-gated refinement**: only accept revisions that raise the reviewer score.

## Related

- Per-agent detail: [agent-outline](agent-outline.md), [agent-literature-review](agent-literature-review.md),
  [agent-section-writing](agent-section-writing.md), [agent-content-refinement](agent-content-refinement.md),
  [agent-plotting](agent-plotting.md), [agent-style](agent-style.md)
- [local-references](local-references.md) (optional Phase-1.5 reference injection)
- [pipeline.canvas](../pipeline.canvas)
