#!/usr/bin/env python3
"""Comprehensive paper format checker.

Validates a generated paper against venue requirements by inspecting the
.tex, .bib, .log, and PDF. Run standalone or after pipeline/enrichment.

Usage:
  python check_paper.py --paper_dir paper_output_logicbranch
  python check_paper.py --paper_dir paper_output_se --template_dir templates/software_se
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.stdout + r.stderr
    except Exception:
        return ""


def _pdf_pages(pdf):
    out = _run(["pdfinfo", pdf])
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else 0


def _pdf_fonts(pdf):
    out = _run(["pdffonts", pdf])
    fonts = []
    for line in out.splitlines()[2:]:  # skip header
        parts = line.split()
        if parts:
            fonts.append(parts[0])
    return fonts


def _parse_guidelines(template_dir):
    """Extract page limit, font, format info from guidelines.md."""
    g = {}
    md = _read(os.path.join(template_dir or "", "guidelines.md"))
    # page limit
    m = re.search(r"(\d+)\s*pages?\s*(?:excl|\(not including)", md, re.I)
    if not m:
        m = re.search(r"(\d+)\s*pages?\s*(?:two.column|body|text)", md, re.I)
    g["page_limit"] = int(m.group(1)) if m else None
    # font size
    m = re.search(r"(\d+)\s*pt.*(?:font|body|times)", md, re.I)
    g["font_pt"] = int(m.group(1)) if m else None
    # format hints
    g["is_chinese"] = "ctexart" in _read(os.path.join(template_dir or "", "template.tex"))
    g["is_acmart"] = "acmart" in _read(os.path.join(template_dir or "", "template.tex"))
    g["is_ieeetran"] = "IEEEtran" in _read(os.path.join(template_dir or "", "template.tex"))
    return g


# ── individual checks ────────────────────────────────────────────────────────

def check_compilation(lw_dir):
    """Check LaTeX compile errors and overfull warnings."""
    log = _read(os.path.join(lw_dir, "raw_draft_paper.log"))
    errors = re.findall(r"^! (.+)", log, re.MULTILINE)
    overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)
    big_overfull = [f for f in overfull if float(f) > 20]
    return {
        "errors": len(errors),
        "error_samples": errors[:5],
        "overfull_total": len(overfull),
        "overfull_large": len(big_overfull),
        "status": "PASS" if not errors else "FAIL",
    }


def check_fonts(pdf, guide):
    """Check embedded fonts against expected ACM/IEEE/Chinese fonts."""
    fonts = _pdf_fonts(pdf)
    fonts_lower = " ".join(fonts).lower()
    issues = []
    if guide.get("is_acmart"):
        if "libert" not in fonts_lower:
            issues.append("ACM template should use Linux Libertine/Biolinum fonts")
            if "lmroman" in fonts_lower or "lmsans" in fonts_lower:
                issues.append("  → currently using Latin Modern (fallback). Install texlive-fonts-extra.")
    if guide.get("is_ieeetran"):
        if "libert" in fonts_lower:
            pass  # some IEEE templates now use Libertine
    if guide.get("is_chinese"):
        # check for a CJK font
        if not any(k in fonts_lower for k in ("droid", "fandol", "noto", "sim", "cjk")):
            issues.append("Chinese paper: no CJK font detected in PDF")
    return {
        "fonts_found": fonts[:8],
        "issues": issues,
        "status": "PASS" if not issues else "WARN",
    }


def check_font_size(lw_dir, guide):
    """Check the body font size from the log."""
    log = _read(os.path.join(lw_dir, "raw_draft_paper.log"))
    m = re.search(r"Using fontsize (\d+)pt", log)
    actual = int(m.group(1)) if m else None
    expected = guide.get("font_pt")
    issues = []
    if actual and expected and actual != expected:
        issues.append(f"Font size {actual}pt, expected {expected}pt per guidelines")
    return {
        "actual_pt": actual,
        "expected_pt": expected,
        "issues": issues,
        "status": "PASS" if not issues else ("INFO" if not expected else "WARN"),
    }


def check_page_count(pdf, guide):
    """Check page count vs venue limit."""
    pages = _pdf_pages(pdf)
    limit = guide.get("page_limit")
    issues = []
    if limit and pages > limit:
        issues.append(f"{pages} pages EXCEEDS limit of {limit}")
    elif limit and pages < limit * 0.5:
        issues.append(f"Only {pages} pages (limit is {limit}) — paper may be too short")
    return {
        "pages": pages,
        "limit": limit,
        "issues": issues,
        "status": "FAIL" if (limit and pages > limit) else "PASS",
    }


def check_references(lw_dir):
    """Check citation consistency: orphans, missing keys, count."""
    tex = _read(os.path.join(lw_dir, "raw_draft_paper.tex"))
    bib = _read(os.path.join(lw_dir, "references.bib"))
    cited = set()
    for c in re.findall(r"\\cite\{([^}]+)\}", tex):
        for k in c.split(","):
            cited.add(k.strip())
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    orphans = bib_keys - cited
    missing = cited - bib_keys
    # arXiv notes on non-preprint entries
    arxiv_notes = re.findall(r"note\s*=\s*\{arXiv:", bib)
    formal_with_arxiv = 0
    for entry in re.split(r"(?=@\w+\{)", bib):
        m = re.match(r"@\w+\{([^,]+),", entry)
        if not m:
            continue
        venue_m = re.search(r"(?:booktitle|journal)\s*=\s*\{([^}]+)\}", entry)
        venue = (venue_m.group(1) or "").lower() if venue_m else ""
        has_arxiv_note = "arxiv:" in entry.lower()
        is_real_venue = venue and "arxiv" not in venue
        if has_arxiv_note and is_real_venue:
            formal_with_arxiv += 1
    return {
        "cite_commands": len(re.findall(r"\\cite\{", tex)),
        "distinct_cited": len(cited),
        "bib_entries": len(bib_keys),
        "orphans": len(orphans),
        "missing_keys": len(missing),
        "arxiv_notes_total": len(arxiv_notes),
        "arxiv_notes_on_formal": formal_with_arxiv,
        "issues": ([f"{len(orphans)} orphan bib entries (uncited)"] if orphans else [])
                 + ([f"{len(missing)} cited keys missing from bib"] if missing else [])
                 + ([f"{formal_with_arxiv} formal-venue entries still have arXiv notes"] if formal_with_arxiv else []),
        "status": "FAIL" if missing else ("WARN" if orphans or formal_with_arxiv else "PASS"),
    }


def check_figures(lw_dir):
    """Check all \\includegraphics resolve and are referenced."""
    tex = _read(os.path.join(lw_dir, "raw_draft_paper.tex"))
    includes = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
    missing_files = []
    for inc in includes:
        # try several base dirs
        found = False
        for base in [lw_dir, os.path.join(lw_dir, "figures"), os.path.join(lw_dir, "picture")]:
            p = os.path.join(base, inc)
            if os.path.exists(p):
                found = True
                break
            # also try with figures/ prefix
            p2 = os.path.join(base, "figures", os.path.basename(inc))
            if os.path.exists(p2):
                found = True
                break
        if not found:
            missing_files.append(inc)
    # check all figures have \\label and \\cref/\\ref
    labels = set(re.findall(r"\\label\{(fig:[^}]+)\}", tex))
    refs = set()
    for r in re.findall(r"\\(?:cref|ref|Cref)\{([^}]+)\}", tex):
        for k in r.split(","):
            refs.add(k.strip())
    unlabeled = max(0, len(includes) - len(labels))
    unreferenced = max(0, len(labels - refs))
    return {
        "figures_total": len(includes),
        "missing_files": missing_files[:5],
        "unlabeled": unlabeled,
        "unreferenced": unreferenced,
        "issues": ([f"{len(missing_files)} figure file(s) not found: {missing_files[:3]}"] if missing_files else [])
                 + ([f"{unlabeled} figure(s) without \\label"] if unlabeled > 0 else [])
                 + ([f"{unreferenced} labeled figure(s) never \\ref'd"] if unreferenced > 0 else []),
        "status": "FAIL" if missing_files else "PASS",
    }


def check_structure(lw_dir, guide):
    """Check required sections are present."""
    tex = _read(os.path.join(lw_dir, "raw_draft_paper.tex"))
    sections = re.findall(r"\\section\*?\{([^}]+)\}", tex)
    section_lower = [s.lower() for s in sections]
    # standard expected sections
    expected = ["introduction", "conclusion"]
    if guide.get("is_chinese"):
        # Chinese template: intro is often unnumbered text before first \section;
        # check for 引言 OR 国内外研究进展 OR 正文 before sections
        intro_present = bool(re.search(r"引言|国内外研究进展|基本概念", tex))
        conclusion_present = bool(re.search(r"结束语|结论", tex))
        missing = []
        if not intro_present:
            missing.append("引言/研究进展")
        if not conclusion_present:
            missing.append("结束语/结论")
    else:
        missing = []
        for exp in expected:
            if not any(exp in s for s in section_lower):
                missing.append(exp)
    return {
        "sections_found": sections,
        "missing_required": missing,
        "issues": [f"Missing required section: {m}" for m in missing],
        "status": "FAIL" if missing else "PASS",
    }


def check_anonymity(lw_dir, guide):
    """Check double-blind compliance (no real author info if anonymous)."""
    tex = _read(os.path.join(lw_dir, "raw_draft_paper.tex"))
    has_anonymous = "anonymous" in tex.lower() and "documentclass" in tex.lower()
    issues = []
    if has_anonymous or guide.get("is_acmart"):
        # check for real names/emails in the tex
        emails = re.findall(r"\\email\{([^}]+)\}", tex)
        real_emails = [e for e in emails if not e.startswith("xxx") and "@" in e and "example" not in e]
        if real_emails and "anonymous" in tex.lower():
            issues.append(f"Anonymous mode but {len(real_emails)} real email(s) found")
        # check for non-placeholder authors
        if "anonymous author" not in tex.lower() and "作者姓名" in tex:
            pass  # Chinese template placeholder
    return {
        "anonymous_mode": "anonymous" in tex.lower(),
        "issues": issues,
        "status": "WARN" if issues else "PASS",
    }


def check_overfull(lw_dir):
    """Detailed overfull analysis."""
    log = _read(os.path.join(lw_dir, "raw_draft_paper.log"))
    overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)
    vals = [float(v) for v in overfull] if overfull else []
    return {
        "total": len(vals),
        "negligible": sum(1 for v in vals if v <= 5),
        "minor": sum(1 for v in vals if 5 < v <= 20),
        "large": sum(1 for v in vals if v > 20),
        "max_pt": max(vals) if vals else 0,
        "status": "PASS" if not any(v > 20 for v in vals) else "WARN",
    }


# ── main ─────────────────────────────────────────────────────────────────────

CHECKS = [
    ("Compilation",     lambda lw, pdf, g: check_compilation(lw)),
    ("Fonts",           lambda lw, pdf, g: check_fonts(pdf, g)),
    ("Font Size",       lambda lw, pdf, g: check_font_size(lw, g)),
    ("Page Count",      lambda lw, pdf, g: check_page_count(pdf, g)),
    ("References",      lambda lw, pdf, g: check_references(lw)),
    ("Figures",         lambda lw, pdf, g: check_figures(lw)),
    ("Structure",       lambda lw, pdf, g: check_structure(lw, g)),
    ("Anonymity",       lambda lw, pdf, g: check_anonymity(lw, g)),
    ("Overfull Boxes",  lambda lw, pdf, g: check_overfull(lw)),
]


def main():
    ap = argparse.ArgumentParser(description="Comprehensive paper format checker.")
    ap.add_argument("--paper_dir", required=True, help="paper_output_X dir")
    ap.add_argument("--template_dir", default=None, help="templates/<conf> for guidelines")
    args = ap.parse_args()

    lw = os.path.join(args.paper_dir, "latex_writeup")
    # find the PDF
    pdf = os.path.join(args.paper_dir, "final_paper.pdf")
    if not os.path.exists(pdf):
        pdf = os.path.join(args.paper_dir, "final_paper_enriched.pdf")
    if not os.path.exists(pdf):
        for f in os.listdir(lw):
            if f.endswith(".pdf"):
                pdf = os.path.join(lw, f)
                break

    guide = _parse_guidelines(args.template_dir)

    print("=" * 70)
    print(f"  PAPER FORMAT CHECK — {args.paper_dir}")
    print(f"  PDF: {pdf}")
    print(f"  Template: {args.template_dir or '(none — generic checks)'}")
    print("=" * 70)

    all_pass = True
    for name, fn in CHECKS:
        result = fn(lw, pdf, guide)
        status = result.get("status", "?")
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(status, "?")
        if status in ("FAIL", "WARN"):
            all_pass = False
        print(f"\n{icon} {name} [{status}]")
        for k, v in result.items():
            if k == "status" or k == "issues":
                continue
            if isinstance(v, list) and len(v) > 5:
                v = v[:5] + [f"... ({len(v)} total)"]
            print(f"   {k}: {v}")
        for issue in result.get("issues", []):
            print(f"   → {issue}")

    print("\n" + "=" * 70)
    print(f"  OVERALL: {'✅ ALL CHECKS PASSED' if all_pass else '⚠️  ISSUES FOUND — see above'}")
    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
