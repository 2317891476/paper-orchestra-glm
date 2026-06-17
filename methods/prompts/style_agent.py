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

style_extraction_prompt = """Role: Senior researcher and copy-editor.
Task: Analyze the provided target-conference "best papers" (their full text + rendered page images)
and distill a concise, actionable WRITING STYLE GUIDE that another author should mimic to match
this community's conventions. This guide will be injected into paper-writing agents.

Study BOTH the text (for voice, structure, phrasing) AND the page images (for layout, figure/table
presentation, two-column conventions, typography).

Produce the guide as Markdown with EXACTLY these sections (omit a section only if you have no
evidence for it; keep each section short and concrete, max ~6 lines):

## Voice & Tone
(e.g., formal/technical density, use of first-person plural "we", hedging level, sentence length)

## Section Structure & Ordering
(the canonical section sequence this community expects, e.g., Intro → Background → Design →
Implementation → Evaluation → Related Work → Conclusion; note where Related Work sits)

## Abstract & Introduction Pattern
(how abstracts are framed: problem → insight → approach → result numbers; how intros open and
what the contribution bullets look like)

## Citation Style & Density
(approximate citation density, natbib/\\cite style, how related work is grouped, how baselines
are introduced)

## Math, Notation & Definitions
(notation habits, whether definitions/environments are used, equation density)

## Figures & Tables
(figure conventions: captions above/below, single vs two-column figures, table style like
booktabs, how results tables are organized; reference what you see in the images)

## Do / Don't
(bullet list of community-specific conventions to follow and pitfalls to avoid)

## Representative Phrasings
(2-3 short verbatim phrasings or sentence templates lifted from these papers that capture the voice)

Wrap the entire guide in a ```markdown ... ``` block. Output ONLY the guide.
"""
