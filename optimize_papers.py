"""Optimize the two DAC papers using the new concepts/ implementation docs.
Enrich idea (method docs) + log (eval docs), re-run outline+section (EN), translate (CN)."""
import os, shutil, re
from methods.agents.outline_agent import OutlineAgent
from methods.agents.section_writing_agent import SectionWritingAgent
from utils.pdf_utils import compile_latex
from utils.llm_backend_utils import call_llm_with_text_prompt

TEMPLATE = "templates/dac2026"
MODEL = "glm-5.2"
CUTOFF = "2025-06"
CAP = 9000  # cap each concept file (chars) to bound context

METHOD_FILES = [
    "pipeline-overview.md", "static-extraction-design-ir.md",
    "semantic-objective-dsl.md", "llm-objective-generation.md",
    "signal-resolution.md", "architecture-evolution.md", "candidate-discovery.md",
]
EVAL_FILES = [
    "benchmark-datasets.md", "setup-synthesis.md",
    "cocotb-icarus-validation.md", "formal-artifacts.md", "reporting-debugging.md",
]

DIRECTIVE = (
    "\n\n> **写作指令（重要）**：本文为方法论文。下方附有**详细实际实现文档（concept）**，"
    "请在 Method/Implementation 章节中**充分利用这些真实实现细节**（管线、DesignIR、DSL、抽取流程、"
    "候选枚举、验证门禁、信号解析等），写出有技术深度的实现描述（可含小型代码/数据结构示意、阶段流程）。"
    "**评估章节**用 experimental_log 中**真实的数据集、指标定义、工具链与验证流程**写成"
    "『评估方案』（数据集、指标如 Top-K hit/MFR/EXAM、对照与消融设计）。"
    "**严禁编造任何实验运行结果数字**（数据集/指标定义是真的，但没有实测结果，不要伪造 %/pass@/提升倍数）。"
    "保持 DAC 模板结构，篇幅可比初稿更充实。"
)

# for benchmark-datasets: keep the dataset + metric prose, drop the giant command reference
def slim_benchmark(text):
    out = []
    keep = True
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## ") and ("命令" in s or "command" in s.lower()):
            keep = False
        if s.startswith("## ") and ("数据集" in s or "指标" in s or "解读" in s or "维护" in s):
            keep = True
        if keep:
            out.append(line)
    return "\n".join(out)[:CAP]


def gather(concepts_dir, files):
    parts = []
    for fn in files:
        p = os.path.join(concepts_dir, fn)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        if fn == "benchmark-datasets.md":
            txt = slim_benchmark(txt)
        else:
            txt = txt[:CAP]
        parts.append(f"\n\n===== concept: {fn} =====\n{txt}")
    return "".join(parts)


def run_one(name, src_md):
    out = f"paper_output_{name}"
    rm = f"{out}/raw_materials"
    lw = f"{out}/latex_writeup"
    lit = f"{out}/literature_agent_output"
    for d in (rm, f"{lw}/figures", lit):
        os.makedirs(d, exist_ok=True)
    shutil.copy(f"{TEMPLATE}/template.tex", f"{lw}/template.tex")
    shutil.copy(f"{TEMPLATE}/references.bib", f"{lw}/references.bib")
    for extra in ("acmart.cls", "ACM-Reference-Format.bst"):
        if os.path.exists(f"{TEMPLATE}/{extra}"):
            shutil.copy(f"{TEMPLATE}/{extra}", f"{lw}/{extra}")
    json.dump({}, open(f"{lit}/citation_map.json", "w"))
    open(f"{lw}/figures/info.json", "w").write("[]")

    concepts = f"{rm}/concepts"
    src = open(src_md, encoding="utf-8").read()
    method_md = gather(concepts, METHOD_FILES)
    eval_md = gather(concepts, EVAL_FILES)
    open(f"{rm}/idea_sparse.md", "w", encoding="utf-8").write(src + DIRECTIVE + method_md)
    open(f"{rm}/experimental_log.md", "w", encoding="utf-8").write(
        "# 评估素材：数据集 / 指标 / 工具链 / 验证流程（来自实际实现文档）\n" + eval_md + DIRECTIVE
    )
    print(f"[{name}] idea={os.path.getsize(rm+'/idea_sparse.md')} log={os.path.getsize(rm+'/experimental_log.md')} chars")

    print(f"[{name}] outline...")
    OutlineAgent(model_name=MODEL, cutoff_date=CUTOFF).run(
        idea_file=f"{rm}/idea_sparse.md",
        experimental_log_file=f"{rm}/experimental_log.md",
        latex_template_file=f"{TEMPLATE}/template.tex",
        conference_guidelines_file=f"{TEMPLATE}/guidelines.md",
        output_filepath=f"{out}/outline.json",
    )
    print(f"[{name}] section...")
    SectionWritingAgent(
        outline_path=f"{out}/outline.json",
        template_path=f"{lw}/template.tex",
        idea_path=f"{rm}/idea_sparse.md",
        experimental_log_path=f"{rm}/experimental_log.md",
        citation_map_path=f"{lit}/citation_map.json",
        figures_info_path=f"{lw}/figures/info.json",
        guidelines_path=f"{TEMPLATE}/guidelines.md",
        model_name=MODEL,
    ).run(output_path=f"{lw}/raw_draft_paper.tex")
    print(f"[{name}] compile EN...")
    compile_latex(lw, f"{out}/final_paper.pdf", "raw_draft_paper")
    print(f"[{name}] EN {'OK' if os.path.exists(f'{out}/final_paper.pdf') else 'FAIL'}")


def strip_fence(s):
    m = re.search(r"```(?:latex|tex)?\s*(.*?)\s*```", s.strip(), re.DOTALL)
    return m.group(1).strip() if m else s.strip()


TPROMPT = """你是专业学术翻译。把下面英文 LaTeX 中的英文文字翻译成简体中文，输出完整可编译的 .tex 文件。
- 只翻译自然语言（标题、摘要、章节名、正文、caption）；保持所有 LaTeX 命令/宏包/\\cite/\\label/公式/结构不变。
- 技术术语可"中文(英文)"。输出整个 .tex，不加解释。
```latex
{tex}
```"""


def translate(name):
    src_tex = open(f"paper_output_{name}/latex_writeup/raw_draft_paper.tex", encoding="utf-8").read()
    resp = call_llm_with_text_prompt(
        prompt=TPROMPT.replace("{tex}", src_tex), model_name=MODEL,
        return_json=False, check_parsed_response_not_none=False,
    )
    zh = strip_fence(resp.get("raw_response", ""))
    zh = re.sub(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]*\})",
                r"\1\n\\usepackage[fontset=fandol]{xeCJK}", zh, count=1)
    if "% !tex program = xelatex" not in zh.lower():
        zh = "% !TeX program = xelatex\n" + zh
    out_dir = f"paper_output_{name}/zh"
    os.makedirs(out_dir, exist_ok=True)
    open(f"{out_dir}/paper_zh.tex", "w", encoding="utf-8").write(zh)
    for f in ("acmart.cls", "ACM-Reference-Format.bst", "references.bib"):
        p = f"paper_output_{name}/latex_writeup/{f}"
        if os.path.exists(p):
            shutil.copy(p, f"{out_dir}/{f}")
    compile_latex(out_dir, f"paper_output_{name}/final_paper_zh.pdf", "paper_zh")
    print(f"[{name}] CN {'OK' if os.path.exists(f'paper_output_{name}/final_paper_zh.pdf') else 'FAIL'}")


import json
PAPERS = [
    ("hirca", "SoC-HiRCA：面向超大规模处理器  SoC RTL 的 LLM 辅助证据驱动静态根因分析方法.md"),
    ("buglens", "LLM-StaticBugLens：面向纯源码 RTL 的 LLM 语义视图驱动静态 bug 定位方法.md"),
]
for name, src in PAPERS:
    try:
        run_one(name, src)
        translate(name)
    except Exception as e:
        import traceback
        print(f"[{name}] ERROR: {e}"); traceback.print_exc()
