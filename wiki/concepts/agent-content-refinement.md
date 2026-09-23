# Agent — Content Refinement

> Stage 4: review → revise → score-gated accept → formatting pass → page-budget compression.
> Status: **implemented (v2)**.

## Role

`ContentRefinementAgent` compiles the draft, generates a simulated peer review
(`autoraters/agent_review.py`), revises the LaTeX to address weaknesses, and only
**accepts a revision if the overall score improves**. A formatting loop then fixes
layout issues (VLM screenshots, text fallback on GLM), and finally a compression
loop enforces the venue's page budget from `format.yaml`.

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

## Compile-verification gate (`_compile_is_complete`)

**"A PDF exists" is NOT proof a compile succeeded.** TeX flushes already-typeset
pages even on a fatal abort: a truncated LLM revision without `\end{document}`
produces `Emergency stop / no legal \end found` in the log yet still writes a
partial PDF. Every acceptance point (reflection revisions, formatting
iterations, compression candidates) now also requires:

- the log has no fatal markers (`Emergency stop`, `Fatal error`,
  `no legal \end`, `Job aborted`), and
- the candidate `.tex` contains `\end{document}`.

(Found 2026-09-11 on TRACE-RTL: a formatting-fix iteration shipped a paper
missing Conclusion + bibliography because the truncated PDF passed the old
existence-only check.)

## Formatting loop — text fallback for vision-less backends

`_get_formatting_review` sends PDF page screenshots to a VLM. The GLM coding
endpoint rejects image content (error 1210, `messages.content.type` text-only),
so on this backend the call fails 5× and the loop used to no-op silently.
Now it falls back to `_get_text_formatting_review`, which feeds the LLM
machine-truth signals instead of images:

- page count (`pdfinfo`),
- Overfull/Underfull warnings from the newest compile log (first 40, with
  source line numbers),
- figure/table inventory parsed from the current LaTeX,

plus the conference guidelines, and asks for the **same JSON schema** — so the
downstream `has_issues` / fix-iteration logic is unchanged. Issues must be
grounded in a signal; the model is told not to invent problems.

## Page-budget compression (`_compress_to_page_budget`)

After the formatting loop, the agent enforces the venue's length limit:

1. `_page_budget_limit()` reads `page_limit_body` from `format.yaml`
   (next to the guidelines, or in the work dir); no key → skip.
2. If compiled pages > limit + 2 (reference-slack), run up to
   **5 compression iterations**:
   - Prompt = current pages, target, the guidelines' per-section Page Budget
     table, and STRICT rules: preserve all technical claims, RQs, section
     structure, every `\cite`; cut repetition/filler; preamble and
     bibliography untouched; **no new figures/tables** (LLMs invent figures
     under compression — seen 2026-09-11: `figures/kintsugi-overview.pdf`
     fabricated from nothing).
   - Sanity gate on the parsed response: must contain `\documentclass` +
     `\end{document}` and be ≥ 30% of current length (rejects placeholder
     echoes like a literal `paper_content`) → rejected rounds retry;
     the rejected raw is dumped to `compression_rejected_v*.txt` for diagnosis.
   - `_repair_candidate_tex` mechanically fixes hallucinated references
     before compiling: restores the original `\bibliographystyle` /
     `\bibliography` args (model renamed `references` → `refs`) and comments
     out any `\includegraphics` whose path neither exists on disk nor
     appeared in the source.
   - Compile + `_compile_is_complete`; accept only if **pages strictly
     decrease**, else stop.
3. Progress logged to `compression_worklog.json` (pages_before/after, outcome).

### Section-wise fallback (`_compress_sectionwise`)

Whole-document rewrites are unreliable in both directions — output can
degenerate (summaries/refusals instead of the document) or land too gently
(page plateau). The loop switches to compressing one `\section` at a time
(~60% length target each) on any of **three triggers**:

1. two consecutive degenerate whole-doc responses,
2. an accepted whole-doc round that shaves < 8% while still over target,
3. a no-reduction plateau while still over target (one forced sweep before
   stopping).

The tex is split on `(?m)(?=\\section\{)`; the bibliography tail is cut off
and re-attached verbatim (the model can't mangle it); each section call is
small enough to avoid output truncation; a rejected section falls back to its
original text (one bad section never kills the sweep — the same holds for a
**failed or timed-out call**). Each accepted section
is checkpointed to `sectionwise_<md5-of-source>_<idx>.tex`, so a killed sweep
resumes at the first uncompressed section and stale checkpoints (from an older,
longer source) never match. The result re-enters the normal
repair → compile → verify → accept path. Stats in `self.sectionwise_stats`.

### Wall-clock deadline on LLM calls (`_llm_call_with_deadline`)

The OpenAI SDK's read timeout only guards the *gap between bytes* — a backend
that accepts a request and then goes silent blocks forever (seen 2026-09-11 on
the GLM coding endpoint: a section-compression call wedged 28+ min, no error,
and four consecutive attempts hung on the same call). Compression LLM calls
therefore run on a **daemon thread with a hard wall-clock deadline**
(300s per section, 600s per whole-document round). On expiry the call raises
`TimeoutError`; the abandoned thread is a daemon, so it never blocks process
exit even if the socket never closes. Section-wise sweeps treat a timed-out
section like a rejected one: keep the original text, keep sweeping (no
checkpoint ⇒ a later sweep retries it).

Compression calls also pass `extra_body: {thinking: {type: disabled}}` —
**the wedge root cause**: glm-5.3's thinking mode deadlocks server-side on
compression prompts (A/B probe 2026-09-11: same prompt, thinking on = 28+ min
zero bytes; thinking off = 10.3 s). Compression is mechanical rewriting and
does not need thinking.

### Delete-protocol for oversized sections (`_compress_by_deletion`)

With thinking off, the model **rewrites gently but does not structurally
shrink large sections** (39KB "Approach" → 99.7% by rewriting; small sections
~93–95%). Sections over 15KB therefore use a two-step protocol instead of
asking for a rewrite:

1. `_split_latex_paragraphs` splits the section at blank lines **outside**
   `\begin/\end` environments (tables/figures/equations/lists stay one
   indivisible piece) and marks *structural* pieces: headings, and any piece
   **defining a `\label`** (deleting a definition would dangle every `\ref`
   to it; merely *using* a `\ref` is safe to delete).
2. The LLM sees an indexed paragraph listing (structural marked `[S]`) plus
   the hard char target and replies `{"delete": [indices]}` — deletion is a
   judgment call the non-thinking model makes reliably. Deletions are applied
   mechanically; a second round runs if the first misses the target. A round
   that yields no deletions keeps the current state (round-1 cuts survive).

Verified on the 39KB Approach section: 38986 → 22225 chars (57%) with all
17 labels intact, 4.2 s. The result is checkpointed through the normal
section-wise path (`[delete-protocol]` log tag).

## Notes / gotchas

- The work dir must contain all LaTeX deps (`.cls`, `.bst`, `hpca-template.tex`, `figures/`,
  `references.bib`). In `write_single_paper` this is set up via `shutil.copytree`; when
  running the agent standalone, copy `latex_writeup/*` into the work dir first.
- Reviewer uses the same `LLM_BACKEND` as the writer (fixed in this fork — was hardcoded Gemini).
- `_get_text_formatting_review` judges from log signals, not rendered pages — it
  cannot see visual issues (spacing, float placement) a VLM would; treat its
  reviews as conservative.
- Whole-document compression needs the LLM to emit ~100KB of LaTeX in one
  response; if a backend truncates, every round is rejected by the sanity gate
  (worklog shows `REJECTED_degenerate response`) — consider section-wise
  compression before raising `max_loops`.

## TODO / flesh out

- [ ] Document the three accept/reject cases + the metrics extraction
- [x] Section-wise compression (avoid whole-doc output-token limits) —
  done 2026-09-11, plus the delete-protocol for >15KB sections (verified on
  TRACE-RTL: 28p → 20p over 3 sweeps)

## Known limitations

- Compression can silently drop `\label`s (seen on TRACE-RTL: the whole-doc
  round dropped `\label{sec:approach}`/`\label{sec:design}`; a rewrite once
  deleted a listing that a later `\ref` still pointed at). The delete-protocol
  protects label-defining paragraphs, but the *rewrite* path has no such guard
  and the final assembled paper is not ref-checked. Cheap manual check after
  any compression run: compare `\label{...}` vs `\ref{...}` sets.
- Rejected LLM rewrites may return without a trailing newline, gluing the next
  `\section{` onto the previous paragraph's last line. LaTeX accepts this
  (compiles + renders identically); line-anchored grep counting does not.
