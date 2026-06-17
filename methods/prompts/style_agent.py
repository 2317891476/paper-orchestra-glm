# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# NOTE: concrete per-section passages (the strong signal) are extracted separately into a
# style BANK and injected as few-shot exemplars at generation time. This prompt therefore
# focuses on VOICE / global conventions (the part exemplars under-specify), and is told the
# measured structure + available bank sections so it does not repeat them verbosely.

style_extraction_prompt = """Role: Senior researcher and copy-editor.
Task: Distill the WRITING-VOICE conventions of this target community from the provided
best-paper text (+ rendered page images). This summary will be injected into paper-writing
agents alongside a per-section exemplar bank — so focus on VOICE and GLOBAL conventions,
NOT on section ordering (already measured) or verbatim phrasing (already in the bank).

Measured structure (from the exemplars, do not restate — just use it):
{structure_json}

Exemplar bank sections available (real passages, injected separately): {bank_sections}

Study the text AND the page images (layout, figure/table presentation, two-column conventions).
Produce a concise Markdown guide with EXACTLY these sections (skip a section only with no evidence;
each section ≤ ~5 lines, concrete not generic):

## Voice & Tone
(formal density, first-person plural "we" usage, hedging, sentence-length tendencies)

## Citation & Related-Work Habits
(density, how baselines/prior work are introduced, grouping style)

## Math & Notation Conventions
(notation habits, definition usage, equation density)

## Figure & Table Conventions
(caption placement, single vs two-column figures, table style e.g. booktabs, results-table organization — reference the images)

## Per-Section Voice Notes
(one short line each for: abstract, introduction, related_work, method, evaluation, conclusion —
e.g. how intros open, how contributions are stated, how eval sections frame baselines)

## Do / Don't
(bullets of community conventions to follow and pitfalls to avoid)

Wrap the whole guide in a ```markdown ... ``` block. Output ONLY the guide.
"""


# --- sentence-level templates (ZeroStylus 2nd granularity) ------------------
# The paragraph exemplar bank carries structure/voice at the paragraph level; this prompt
# extracts SENTENCE-level phrasing templates grouped by rhetorical function, so writers get
# fine-grained "how this community phrases X" few-shot cues.

sentence_template_extraction_prompt = """Role: Senior researcher and copy-editor.
Task: From the following passages of target-community papers, extract SENTENCE-LEVEL phrasing
templates grouped by rhetorical function. These are short, imitable sentence patterns a writer
should reuse to match this community's voice.

For EACH function below, give 1-3 templates. A template = a concise representative sentence
lifted or lightly generalized from the text (keep it concrete and specific to THIS community,
not generic academic filler). If the function is not observable, give an empty list.

Functions:
- "opening_hook": how abstracts/intros open (the framing of the problem space).
- "problem_statement": how the gap/limitation of prior work is stated.
- "contribution": how contributions are asserted ("we propose / our key idea").
- "approach_overview": how the method is summarized in one sentence.
- "comparison": how the work is contrasted with prior/baseline work.
- "result_claim": how quantitative results are stated.
- "transition": section/linking transition phrases the community favors.
- "limitation_future": how limitations or future work are phrased.

Return ONLY a JSON object (wrapped in ```json ... ```):
{{
  "opening_hook": ["...", "..."],
  "problem_statement": ["..."],
  "contribution": ["..."],
  "approach_overview": ["..."],
  "comparison": ["..."],
  "result_claim": ["..."],
  "transition": ["..."],
  "limitation_future": ["..."]
}}

Passages:
---
{passages}
---
"""

