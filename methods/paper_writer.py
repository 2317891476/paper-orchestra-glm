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

import os
import os.path as osp
import shutil
import traceback
import json
import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from methods.agents.outline_agent import OutlineAgent
from methods.agents.literature_review_agent import HybridLiteratureAgent
from methods.agents.section_writing_agent import SectionWritingAgent
from methods.agents.content_refinement_agent import ContentRefinementAgent
from methods.agents.style_agent import StyleAgent, resolve_style_papers

from utils.common_utils import (
    create_log_folder,
)

STAGES = ["outline", "style", "literature", "section", "refinement"]


def write_single_paper(
    base_dir,
    latex_template_dir,
    idea_filename="idea_dense.md",
    experimental_log_filename="experimental_log.md",
    writer_model_name: str = "gemini-3.1-pro-preview",
    reflection_model_name: str = "gemini-3.1-pro-preview",
    research_cutoff: str = "2024-11",
    local_references_dir: str = None,
    style_references_dir: str = None,
    use_style_learning: bool = True,
    stages: str = None,
    from_stage: str = None,
):
    """Run the paper pipeline, optionally a subset of stages (resume-safe).

    stages:     comma-list, e.g. "literature,section"
    from_stage: run from this stage through the end, e.g. "section" -> section,refinement
    Neither:    full run (all stages; wipe + retry as before).
    """
    selected = _resolve_stages(stages, from_stage)
    fresh = selected == STAGES
    ctx = _build_ctx(base_dir, latex_template_dir, idea_filename, experimental_log_filename)
    _setup(ctx, fresh=fresh)

    # Style profile: run the style stage, else reuse style_bank.json if present, else None.
    if "style" in selected:
        style_profile = _stage_style(
            ctx, writer_model_name, style_references_dir, use_style_learning
        )
    else:
        style_profile = _load_style_profile(ctx)

    def _run_selected():
        for stage in selected:
            _prepare_for_stage(stage, ctx)
            print(f"\n==== STAGE: {stage} ====")
            if stage == "outline":
                _stage_outline(ctx, writer_model_name, research_cutoff)
            elif stage == "style":
                pass  # produced above
            elif stage == "literature":
                _stage_literature(
                    ctx, writer_model_name, research_cutoff, local_references_dir, style_profile
                )
            elif stage == "section":
                _stage_section(ctx, writer_model_name, style_profile)
            elif stage == "refinement":
                _stage_refinement(ctx, reflection_model_name)

    if not fresh:
        _run_selected()
        _format_check(base_dir, latex_template_dir)
        return True

    # Full run keeps the original retry semantics.
    max_n_tries = 3
    for cur_try in range(max_n_tries):
        try:
            _run_selected()
            _format_check(base_dir, latex_template_dir)
            return True
        except Exception:
            print(f"[Try {cur_try+1}/{max_n_tries}] EXCEPTION in perform_writeup:")
            print(traceback.format_exc())
            if cur_try + 1 < max_n_tries:
                print("Try again now...")
    print(f"Writeup failed after {max_n_tries}! Stop here.")
    return False


def _format_check(base_dir, template_dir):
    """Run the format checker after paper generation (closed-loop QA)."""
    import subprocess as _sp
    script = os.path.join(os.path.dirname(__file__), "..", "check_paper.py")
    if not os.path.exists(script):
        return
    print("\n" + "=" * 60)
    print("  FORMAT CHECK (auto)")
    print("=" * 60)
    try:
        _sp.run(
            ["python3", script, "--paper_dir", base_dir, "--template_dir", template_dir],
            timeout=120,
        )
    except Exception as e:
        print(f"  (format check skipped: {e})")


# --- stage runner internals -------------------------------------------------


def _resolve_stages(stages, from_stage):
    if from_stage:
        if from_stage not in STAGES:
            raise ValueError(f"--from_stage must be one of {STAGES}, got '{from_stage}'")
        return STAGES[STAGES.index(from_stage):]
    if stages:
        parts = [s.strip() for s in stages.split(",") if s.strip()]
        bad = [p for p in parts if p not in STAGES]
        if bad:
            raise ValueError(f"Unknown stage(s) {bad}; valid: {STAGES}")
        return [s for s in STAGES if s in parts]  # canonical order, deduped
    return list(STAGES)


def _build_ctx(base_dir, latex_template_dir, idea_filename, experimental_log_filename):
    materials_dir = osp.join(base_dir, "raw_materials")
    latex_writeup_dir = osp.join(base_dir, "latex_writeup")
    return {
        "base_dir": base_dir,
        "latex_template_dir": latex_template_dir,
        "materials_dir": materials_dir,
        "latex_writeup_dir": latex_writeup_dir,
        "literature_agent_output_dir": osp.join(base_dir, "literature_agent_output"),
        "content_refinement_workdir": osp.join(base_dir, "content_refinement_workdir"),
        "outline_path": osp.join(base_dir, "outline.json"),
        "style_guide_path": osp.join(base_dir, "style_guide.md"),
        "style_bank_path": osp.join(base_dir, "style_bank.json"),
        "final_pdf_path": osp.join(base_dir, "final_paper.pdf"),
        "guidelines_path": osp.join(latex_writeup_dir, "guidelines.md"),
        "guidelines_src_path": osp.join(latex_template_dir, "guidelines.md"),
        "template_path": osp.join(latex_writeup_dir, "template.tex"),
        "raw_template_path": osp.join(latex_template_dir, "template.tex"),
        "references_bib_path": osp.join(latex_writeup_dir, "references.bib"),
        "raw_draft_path": osp.join(latex_writeup_dir, "raw_draft_paper.tex"),
        "figures_dir": osp.join(latex_writeup_dir, "figures"),
        "idea_path": osp.join(materials_dir, idea_filename),
        "log_path": osp.join(materials_dir, experimental_log_filename),
        "citation_map_path": osp.join(base_dir, "literature_agent_output", "citation_map.json"),
    }


def _setup(ctx, fresh: bool):
    os.makedirs(ctx["base_dir"], exist_ok=True)
    if fresh:
        if osp.exists(ctx["latex_writeup_dir"]):
            shutil.rmtree(ctx["latex_writeup_dir"])
        if osp.exists(ctx["final_pdf_path"]):
            os.remove(ctx["final_pdf_path"])
    os.makedirs(ctx["latex_writeup_dir"], exist_ok=True)

    # figures: copy once if missing
    old_figure_dir = osp.join(ctx["materials_dir"], "figures")
    new_figure_dir = ctx["figures_dir"]
    if osp.exists(old_figure_dir) and not osp.exists(new_figure_dir):
        shutil.copytree(old_figure_dir, new_figure_dir, dirs_exist_ok=True)

    if fresh:
        shutil.copytree(ctx["latex_template_dir"], ctx["latex_writeup_dir"], dirs_exist_ok=True)


def _load_style_profile(ctx):
    if osp.exists(ctx["style_bank_path"]):
        try:
            with open(ctx["style_bank_path"], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f" >> Could not load existing style profile: {e}")
    return None


def _prepare_for_stage(stage, ctx):
    """Assert upstream artifacts exist + restore stage invariants (resume-safe)."""
    if stage == "outline":
        assert osp.exists(ctx["materials_dir"]), (
            f"Please make sure '{ctx['materials_dir']}' exists!"
        )
        assert osp.exists(ctx["idea_path"]), f"No idea file detected at '{ctx['idea_path']}'!"
        assert osp.exists(ctx["log_path"]), (
            f"No experimental log detected at '{ctx['log_path']}'!"
        )

    elif stage == "style":
        pass  # style papers resolved inside the stage

    elif stage == "literature":
        assert osp.exists(ctx["outline_path"]), (
            f"outline.json missing at '{ctx['outline_path']}' — run the 'outline' stage first."
        )
        os.makedirs(ctx["latex_writeup_dir"], exist_ok=True)
        # restore the RAW template so re-running literature does not double-inject
        if osp.exists(ctx["raw_template_path"]):
            shutil.copy(ctx["raw_template_path"], ctx["template_path"])
        assert osp.exists(ctx["guidelines_path"]) or osp.exists(ctx["guidelines_src_path"]), (
            "No guidelines file detected in template dir."
        )

    elif stage == "section":
        needs = [
            (ctx["citation_map_path"], "citation_map.json (run 'literature' first)"),
            (ctx["template_path"], "template.tex (run 'literature' first)"),
            (ctx["references_bib_path"], "references.bib (run 'literature' first)"),
            (ctx["outline_path"], "outline.json (run 'outline' first)"),
        ]
        for path, label in needs:
            assert osp.exists(path), f"Section stage needs {label}: '{path}'"

    elif stage == "refinement":
        assert osp.exists(ctx["raw_draft_path"]), (
            f"raw_draft_paper.tex missing at '{ctx['raw_draft_path']}' — run 'section' first."
        )


def _guidelines(ctx):
    return ctx["guidelines_path"] if osp.exists(ctx["guidelines_path"]) else ctx["guidelines_src_path"]


def _stage_outline(ctx, writer_model_name, research_cutoff):
    outline_agent = OutlineAgent(model_name=writer_model_name, cutoff_date=research_cutoff)
    outline_agent.run(
        idea_file=ctx["idea_path"],
        experimental_log_file=ctx["log_path"],
        latex_template_file=ctx["raw_template_path"],
        conference_guidelines_file=_guidelines(ctx),
        output_filepath=ctx["outline_path"],
    )


def _stage_style(ctx, writer_model_name, style_references_dir, use_style_learning):
    if not use_style_learning:
        return None
    style_papers = resolve_style_papers(style_references_dir, ctx["latex_template_dir"])
    if not style_papers:
        print(" >> No style reference papers found — skipping style learning.")
        return None
    return StyleAgent(model_name=writer_model_name).run(style_papers, ctx["style_guide_path"])


def _stage_literature(ctx, writer_model_name, research_cutoff, local_references_dir, style_profile):
    literature_agent = HybridLiteratureAgent(
        idea_path=ctx["idea_path"],
        experimental_log_path=ctx["log_path"],
        latex_template_path=ctx["template_path"],
        conference_guidelines_path=_guidelines(ctx),
        output_dir=ctx["literature_agent_output_dir"],
        model_name=writer_model_name,
        max_workers=3,
        local_references_dir=local_references_dir,
        style_profile=style_profile,
    )
    literature_agent.run(outline_path=ctx["outline_path"], cutoff_date=research_cutoff)
    out = ctx["literature_agent_output_dir"]
    shutil.copy(osp.join(out, "outline_v1.json"), ctx["outline_path"])
    shutil.copy(osp.join(out, "updated_template.tex"), ctx["template_path"])
    shutil.copy(osp.join(out, "references.bib"), ctx["references_bib_path"])


def _stage_section(ctx, writer_model_name, style_profile):
    section_writing_agent = SectionWritingAgent(
        outline_path=ctx["outline_path"],
        template_path=ctx["template_path"],
        idea_path=ctx["idea_path"],
        experimental_log_path=ctx["log_path"],
        citation_map_path=ctx["citation_map_path"],
        figures_info_path=osp.join(ctx["figures_dir"], "info.json"),
        guidelines_path=_guidelines(ctx),
        model_name=writer_model_name,
        style_profile=style_profile,
    )
    section_writing_agent.run(output_path=ctx["raw_draft_path"])


def _stage_refinement(ctx, reflection_model_name):
    workdir = ctx["content_refinement_workdir"]
    if osp.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir, exist_ok=True)
    shutil.copytree(ctx["latex_writeup_dir"], workdir, dirs_exist_ok=True)

    agent = ContentRefinementAgent(
        experimental_log_path=ctx["log_path"],
        citation_map_path=ctx["citation_map_path"],
        guidelines_path=_guidelines(ctx),
        model_name=reflection_model_name,
        max_reflections=3,
        work_dir=workdir,
    )
    out_pdf = agent.run(texfile_path=ctx["raw_draft_path"])
    assert osp.exists(out_pdf), (
        f"Content Refinement Agent failed to produce PDF at {out_pdf}!"
    )
    shutil.copy(out_pdf, ctx["final_pdf_path"])
    print(f" >> Final PDF saved to:\n {ctx['final_pdf_path']}")


def process_paper_task(
    paper,
    output_dir,
    latex_template_dir,
    idea_filename,
    experimental_log_filename,
    writer_model_name,
    research_cutoff,
):
    """
    Worker function to process a single paper.
    Returns a dictionary with results to be handled by the main thread.
    """
    try:
        paper_id = paper["paper_id"]
        print(f"Starting processing for paper '{paper_id}'...")

        paper_dest_dir = osp.join(output_dir, paper_id)
        os.makedirs(paper_dest_dir, exist_ok=True)
        final_paper_path = osp.join(paper_dest_dir, "final_paper.pdf")

        result = {
            "paper_id": paper_id,
            "status": "failed",
            "paper_path": "",
        }

        if True:
            shutil.rmtree(paper_dest_dir, ignore_errors=True)
            os.makedirs(paper_dest_dir, exist_ok=True)

            content_dest_dir = osp.join(paper_dest_dir, "raw_materials")
            os.makedirs(content_dest_dir, exist_ok=True)
            print(
                f"Copying content_folder from {paper['content_folder']} to {content_dest_dir}..."
            )
            shutil.copytree(
                src=paper["content_folder"], dst=content_dest_dir, dirs_exist_ok=True
            )
            print(f"Copying original paper to {content_dest_dir}...")
            shutil.copy(
                src=paper["pdf_path"],
                dst=osp.join(content_dest_dir, "original_paper.pdf"),
            )

            success = write_single_paper(
                base_dir=paper_dest_dir,
                latex_template_dir=latex_template_dir,
                idea_filename=idea_filename,
                experimental_log_filename=experimental_log_filename,
                writer_model_name=writer_model_name,
                research_cutoff=research_cutoff,
            )

            if success:
                result["status"] = "success"
                result["paper_path"] = final_paper_path
                print(f"Paper {paper_id} successfully written!")
            else:
                print(f"Paper {paper_id} writing failed.")
                return result

        return result

    except Exception as e:
        print(f"CRITICAL ERROR in worker for paper {paper['paper_id']}: {e}")
        print(traceback.format_exc())
        return {"paper_id": paper["paper_id"], "status": "error", "error": str(e)}


def _load_papers_from_config(
    process_root_folder: bool,
    root_input_folder: str,
    paper_info_path: str,
    n_papers: int,
):
    """Loads a list of paper dictionaries from either a root folder or a JSON file."""
    if process_root_folder:
        if not root_input_folder:
            raise ValueError(
                "Please provide root_input_folder if process_root_folder is True."
            )
        all_papers_candidates = []
        all_paper_ids_raw = os.listdir(root_input_folder)
        all_paper_ids = [
            paper_id
            for paper_id in all_paper_ids_raw
            if os.path.isdir(os.path.join(root_input_folder, paper_id))
        ]
        for paper_id in all_paper_ids:
            content_folder = os.path.join(root_input_folder, paper_id, "raw_materials")
            pdf_path = os.path.join(root_input_folder, paper_id, f"{paper_id}.pdf")
            if not os.path.exists(content_folder) or not os.path.exists(pdf_path):
                continue
            paper_entry = {
                "paper_id": paper_id,
                "content_folder": content_folder,
                "pdf_path": pdf_path,
            }
            all_papers_candidates.append(paper_entry)
    else:
        if not paper_info_path:
            raise ValueError(
                "Please provide paper_info_path if process_root_folder is False."
            )
        with open(paper_info_path, "r") as f:
            all_papers_candidates = json.load(f)

    if n_papers < 0:
        n_papers = len(all_papers_candidates)
    else:
        n_papers = min(n_papers, len(all_papers_candidates))

    return all_papers_candidates[:n_papers]


def _load_logs(output_dir: str):
    """Loads existing logs to support resuming a batch job."""
    paper_writing_log_path = osp.join(output_dir, "paper_writing_log.json")
    write_log = {}
    if osp.exists(paper_writing_log_path):
        with open(paper_writing_log_path, "r") as f:
            write_log = json.load(f)
        print(f"Loaded existing writing log with {len(write_log)} entries.")

    return write_log


def _filter_and_prepare_papers(
    all_papers, write_log, process_root_folder, paper_info_path
):
    """Filters out completed papers and resolves paths."""
    papers_to_process = []
    base_info_dir = ""
    if (not process_root_folder) and (paper_info_path != ""):
        base_info_dir = osp.dirname(paper_info_path)

    for paper in all_papers:
        # Check if already successfully processed in log
        if (
            paper["paper_id"] in write_log
            and write_log[paper["paper_id"]].get("status") == "success"
            and osp.exists(write_log[paper["paper_id"]].get("paper_path", ""))
        ):
            continue

        if not osp.isabs(paper["content_folder"]):
            paper["content_folder"] = osp.join(base_info_dir, paper["content_folder"])
        if not osp.isabs(paper["pdf_path"]):
            paper["pdf_path"] = osp.join(base_info_dir, paper["pdf_path"])

        papers_to_process.append(paper)

    return papers_to_process


def run_batch_writeup(
    latex_template_dir: str,
    process_root_folder: bool = True,
    root_input_folder: str = "",
    paper_info_path: str = "",
    output_dir: str = "",
    output_dir_prefix: str = "",
    date_str: str = "",
    idea_filename: str = "idea_sparse.md",
    experimental_log_filename: str = "experimental_log.md",
    writer_model_name: str = "gemini-3.1-pro-preview",
    research_cutoff: str = "2024-11",
    n_papers=-1,
    max_workers=4,
):
    if output_dir == "":
        output_dir = create_log_folder(prefix=output_dir_prefix, date_str=date_str)
    else:
        print(f"Resuming from output_dir = {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    all_papers = _load_papers_from_config(
        process_root_folder, root_input_folder, paper_info_path, n_papers
    )
    write_log = _load_logs(output_dir)

    papers_to_process = _filter_and_prepare_papers(
        all_papers, write_log, process_root_folder, paper_info_path
    )

    print(
        f"Starting batch writeup for {len(papers_to_process)} papers (skipped {len(all_papers) - len(papers_to_process)} already done)."
    )
    print(f"Parallel execution with max_workers={max_workers}")

    paper_writing_log_path = osp.join(output_dir, "paper_writing_log.json")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_paper_task,
                paper,
                output_dir,
                latex_template_dir,
                idea_filename,
                experimental_log_filename,
                writer_model_name,
                research_cutoff,
            ): paper["paper_id"]
            for paper in papers_to_process
        }

        for future in tqdm.tqdm(
            as_completed(futures), total=len(futures), desc="Writing Papers"
        ):
            paper_id = futures[future]
            try:
                result = future.result()

                write_log[paper_id] = {
                    "status": result["status"],
                    "paper_path": result.get("paper_path", ""),
                }

                with open(paper_writing_log_path, "w") as f:
                    json.dump(write_log, f, indent=4)

            except Exception as e:
                print(f"Exception handling result for paper {paper_id}: {e}")

    success_count = sum(
        1 for entry in write_log.values() if entry.get("status") == "success"
    )
    error_count = sum(
        1 for entry in write_log.values() if entry.get("status") in ["failed", "error"]
    )

    print("\n" + "=" * 50)
    print("BATCH PROCESSING COMPLETE")
    print(f"Total Papers: {len(all_papers)}")
    print(f"Successfully written: {success_count}")
    print(f"Failed/Error: {error_count}")
    print(f"Logs saved to: {output_dir}")
    print("=" * 50 + "\n")

    return paper_writing_log_path
