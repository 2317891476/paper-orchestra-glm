"""Translate the English DAC drafts to readable Chinese PDFs.
glm-5.2 translates the LaTeX body; we inject xeCJK (-> auto xelatex) and compile."""
import os, shutil, re
from utils.llm_backend_utils import call_llm_with_text_prompt
from utils.pdf_utils import compile_latex

MODEL = "glm-5.2"
PAPERS = ["hirca", "buglens"]

PROMPT = """你是专业学术翻译。把下面这份英文 LaTeX 源码中的**英文文字翻译成简体中文**，输出**完整可编译的 .tex 文件**。

规则：
- 只翻译自然语言内容：论文标题(\\title)、摘要、各章节标题(\\section/\\subsection)、正文段落、图表标题(caption)。
- **保持不变**：所有 LaTeX 命令与结构、\\documentclass、宏包(\\usepackage)、\\cite{...}、\\label{...}、\\bibliography{...}、数学公式、bib key、注释行、环境(\\begin/\\end)。
- 技术术语可保留英文或"中文(英文)"形式，如 RTL、LLM、Root Cause Analysis、SAT/BMC 等。
- 保持原段落结构与编号。
- 输出**整个 .tex 文件内容**，不要加任何解释说明，不要省略任何部分。

LaTeX 源码：
```latex
{tex}
```
"""


def strip_fence(s):
    m = re.search(r"```(?:latex|tex)?\s*(.*?)\s*```", s.strip(), re.DOTALL)
    return m.group(1).strip() if m else s.strip()


def translate_one(name):
    src_dir = f"paper_output_{name}/latex_writeup"
    src_tex = open(f"{src_dir}/raw_draft_paper.tex", encoding="utf-8").read()
    print(f"[{name}] translating ({len(src_tex)} chars)...")

    resp = call_llm_with_text_prompt(
        prompt=PROMPT.replace("{tex}", src_tex),
        model_name=MODEL,
        return_json=False,
        check_parsed_response_not_none=False,
    )
    zh = strip_fence(resp.get("raw_response", ""))

    # inject xeCJK after \documentclass{...} so Chinese compiles (auto -> xelatex)
    zh = re.sub(
        r"(\\documentclass(?:\[[^\]]*\])?\{[^}]*\})",
        r"\1\n\\usepackage[fontset=fandol]{xeCJK}  % Chinese support (auto xelatex)",
        zh,
        count=1,
    )
    # make sure engine hint is present (compile_latex detects ctex/xeCJK -> xelatex)
    if "% !tex program = xelatex" not in zh.lower():
        zh = "% !TeX program = xelatex\n" + zh

    out_dir = f"paper_output_{name}/zh"
    os.makedirs(out_dir, exist_ok=True)
    tex_path = f"{out_dir}/paper_zh.tex"
    open(tex_path, "w", encoding="utf-8").write(zh)
    # copy deps so it compiles
    for f in ("acmart.cls", "ACM-Reference-Format.bst", "references.bib"):
        p = os.path.join(src_dir, f)
        if os.path.exists(p):
            shutil.copy(p, f"{out_dir}/{f}")

    compile_latex(out_dir, f"paper_output_{name}/final_paper_zh.pdf", "paper_zh")
    ok = os.path.exists(f"paper_output_{name}/final_paper_zh.pdf")
    print(f"[{name}] Chinese PDF {'OK' if ok else 'FAILED'}: paper_output_{name}/final_paper_zh.pdf")


for n in PAPERS:
    try:
        translate_one(n)
    except Exception as e:
        import traceback
        print(f"[{n}] ERROR: {e}")
        traceback.print_exc()
