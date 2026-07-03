"""Fast DAC draft for method papers — outline + section only (skip literature/refinement).
No real experiments in the sources, so the agent is told NOT to fabricate numbers/tables."""
import os, shutil, json

from methods.agents.outline_agent import OutlineAgent
from methods.agents.section_writing_agent import SectionWritingAgent
from utils.pdf_utils import compile_latex

TEMPLATE = "templates/dac2026"
MODEL = "glm-5.2"
CUTOFF = "2025-06"

PAPERS = [
    ("hirca",  "SoC-HiRCA：面向超大规模处理器  SoC RTL 的 LLM 辅助证据驱动静态根因分析方法.md"),
    ("buglens","LLM-StaticBugLens：面向纯源码 RTL 的 LLM 语义视图驱动静态 bug 定位方法.md"),
]

DIRECTIVE = (
    "\n\n> **写作指令（重要）**：本文为**方法/立场论文（method/position paper）**，"
    "源材料中**没有运行时实验数据**。**严禁编造任何实验数字、性能结果或结果表格**。"
    "论文遵循 DAC 模板结构，内容聚焦：研究问题与意义、现有方法瓶颈、本文方法与设计、"
    "为什么能突破瓶颈、实现挑战与评估方案（Discussion/Evaluation Plan）。"
    "如模板有 Experiments 章节，请改写为『评估方案与讨论』（评估指标、对照、消融设计），不要给假数据。"
    "篇幅适中即可（这是快速初稿）。"
)


def run_one(name, src_md):
    out = f"paper_output_{name}"
    rm = f"{out}/raw_materials"
    lw = f"{out}/latex_writeup"
    lit = f"{out}/literature_agent_output"
    for d in (rm, f"{lw}/figures", lit):
        os.makedirs(d, exist_ok=True)

    # seed template + empty citation artifacts (skip literature search)
    shutil.copy(f"{TEMPLATE}/template.tex", f"{lw}/template.tex")
    shutil.copy(f"{TEMPLATE}/references.bib", f"{lw}/references.bib")
    # acmart isn't installed system-wide: copy the class + bst so it compiles
    for extra in ("acmart.cls", "ACM-Reference-Format.bst"):
        p = os.path.join(TEMPLATE, extra)
        if os.path.exists(p):
            shutil.copy(p, f"{lw}/{extra}")
    json.dump({}, open(f"{lit}/citation_map.json", "w"))
    open(f"{lw}/figures/info.json", "w").write("[]")

    # idea + log from source (+ directive)
    src = open(src_md, encoding="utf-8").read()
    open(f"{rm}/idea_sparse.md", "w", encoding="utf-8").write(src + DIRECTIVE)
    open(f"{rm}/experimental_log.md", "w", encoding="utf-8").write(src + DIRECTIVE)

    print(f"\n===== [{name}] OUTLINE =====")
    outline_path = f"{out}/outline.json"
    OutlineAgent(model_name=MODEL, cutoff_date=CUTOFF).run(
        idea_file=f"{rm}/idea_sparse.md",
        experimental_log_file=f"{rm}/experimental_log.md",
        latex_template_file=f"{TEMPLATE}/template.tex",
        conference_guidelines_file=f"{TEMPLATE}/guidelines.md",
        output_filepath=outline_path,
    )

    print(f"===== [{name}] SECTION =====")
    draft_path = f"{lw}/raw_draft_paper.tex"
    SectionWritingAgent(
        outline_path=outline_path,
        template_path=f"{lw}/template.tex",
        idea_path=f"{rm}/idea_sparse.md",
        experimental_log_path=f"{rm}/experimental_log.md",
        citation_map_path=f"{lit}/citation_map.json",
        figures_info_path=f"{lw}/figures/info.json",
        guidelines_path=f"{TEMPLATE}/guidelines.md",
        model_name=MODEL,
    ).run(output_path=draft_path)

    print(f"===== [{name}] COMPILE =====")
    compile_latex(lw, f"{out}/final_paper.pdf", "raw_draft_paper")
    ok = os.path.exists(f"{out}/final_paper.pdf")
    print(f"[{name}] DONE — PDF {'OK' if ok else 'FAILED'}: {out}/final_paper.pdf")


for name, src in PAPERS:
    try:
        run_one(name, src)
    except Exception as e:
        import traceback
        print(f"[{name}] ERROR: {e}")
        traceback.print_exc()
