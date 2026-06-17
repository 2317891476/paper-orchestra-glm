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

"""StyleAgent: extract a writing-style guide from target-conference "best papers".

Optional pipeline stage (Step 1.5). Reads best-paper PDFs (text + rendered pages), distills
a style guide, and returns it for injection into the literature writer + section writer
system prompts. Graceful no-op when no papers are provided.
"""

import glob
import os
import re
import tempfile
from typing import List, Optional

from methods.prompts.style_agent import style_extraction_prompt
from utils.llm_backend_utils import call_llm_with_images
from utils.pdf_utils import load_paper, pdf_to_grid_images

_MAX_STYLE_PAPERS = 3  # bound token cost (visual extraction is expensive)


def _strip_markdown_fence(text: str) -> str:
    m = re.search(r"```markdown\s*(.*?)\s*```", text.strip(), re.DOTALL)
    if m:
        return m.group(1).strip()
    # fall back: any ```...``` block
    m = re.search(r"```\s*(.*?)\s*```", text.strip(), re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def resolve_style_papers(
    run_dir: Optional[str], conf_template_dir: Optional[str]
) -> List[str]:
    """Gather best-paper PDFs: run-level dir first, then conference-level fallback.

    - run_dir: raw_material/style_references/ (priority)
    - conf_template_dir: templates/<conf>/style_papers/ (fallback only if run_dir empty)
    Dedup by basename; cap at _MAX_STYLE_PAPERS.
    """
    candidates: List[str] = []
    seen = set()

    def _collect(d: str):
        nonlocal candidates
        if not d or not os.path.isdir(d):
            return
        for pdf in sorted(glob.glob(os.path.join(d, "*.pdf"))):
            base = os.path.basename(pdf)
            if base in seen:
                continue
            seen.add(base)
            candidates.append(pdf)

    _collect(run_dir)
    if not candidates:  # only fall back to conf-level if run-level had nothing
        _collect(os.path.join(conf_template_dir, "style_papers") if conf_template_dir else None)

    return candidates[:_MAX_STYLE_PAPERS]


class StyleAgent:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, paper_paths: List[str], output_path: str) -> Optional[str]:
        """Extract a style guide from the given PDFs. Returns the guide text, or None."""
        paper_paths = [p for p in (paper_paths or []) if os.path.exists(p)]
        paper_paths = paper_paths[:_MAX_STYLE_PAPERS]
        if not paper_paths:
            print(" >> [StyleAgent] no style papers provided — skipping style learning.")
            return None

        print(f" >> [StyleAgent] extracting style from {len(paper_paths)} paper(s)...")

        # --- text: concatenate first few pages of each paper ---
        text_parts = []
        for p in paper_paths:
            try:
                txt = load_paper(p, num_pages=6, min_size=50)
                text_parts.append(f"=== {os.path.basename(p)} ===\n{txt[:7000]}")
            except Exception as e:
                print(f"    [StyleAgent] could not read text from {p}: {e}")

        # --- visual: render first grid image per paper ---
        image_paths: List[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, p in enumerate(paper_paths):
                try:
                    grids = pdf_to_grid_images(p, os.path.join(tmpdir, f"paper_{idx}"))
                    if grids:
                        image_paths.append(grids[0])  # first 2x2 grid (pages 1-4)
                except Exception as e:
                    print(f"    [StyleAgent] could not render images for {p}: {e}")

            if not text_parts and not image_paths:
                print(" >> [StyleAgent] nothing extractable from style papers — skipping.")
                return None

            prompt = (
                style_extraction_prompt
                + "\n\n=== PAPER TEXT (concatenated, possibly truncated) ===\n"
                + "\n\n".join(text_parts)
            )

            try:
                resp = call_llm_with_images(
                    prompt=prompt,
                    images=image_paths,
                    model_name=self.model_name,
                    generation_configs={"temperature": 0.4},
                    return_json=False,
                    result_parsing_func=lambda x: x,  # raw string; fenced below
                    check_parsed_response_not_none=False,
                )
            except Exception as e:
                # Vision may be unsupported by the model → retry text-only.
                print(f"    [StyleAgent] visual call failed ({e}); retrying text-only.")
                from utils.llm_backend_utils import call_llm_with_text_prompt

                resp = call_llm_with_text_prompt(
                    prompt=prompt,
                    model_name=self.model_name,
                    generation_configs={"temperature": 0.4},
                    return_json=False,
                    check_parsed_response_not_none=False,
                )

        raw = resp.get("raw_response") or ""
        guide = _strip_markdown_fence(raw)
        if not guide.strip():
            print(" >> [StyleAgent] style extraction returned empty — skipping.")
            return None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(guide)
        print(f" >> [StyleAgent] style guide saved to {output_path}")
        return guide
