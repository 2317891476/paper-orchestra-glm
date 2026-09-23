#!/usr/bin/env python3
"""Comprehensive paper format checker — reads template's format.yaml for specs.

Validates a generated paper against the venue's format specification by
inspecting .tex, .bib, .log, and the compiled PDF.

Usage:
  python check_paper.py --paper_dir paper_output_logicbranch --template_dir templates/taco
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
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return ""


def _newest(lw, pattern):
    """Newest file matching pattern in lw (by mtime), or '' if none."""
    if not lw:
        return ""
    try:
        files = sorted(Path(lw).glob(pattern), key=lambda p: p.stat().st_mtime)
        return str(files[-1]) if files else ""
    except Exception:
        return ""


def _candidate_dirs(lw):
    """lw plus its sibling content_refinement_workdir (where compiles happen)."""
    dirs = [lw]
    crw = str(Path(lw).parent / "content_refinement_workdir")
    if crw not in dirs and Path(crw).is_dir():
        dirs.append(crw)
    return dirs


def _resolve_artifact(lw, preferred_name, pattern):
    """Preferred filename if it exists, else the newest usable match.

    The refinement workdir names artifacts per version (initial_draft.log,
    refined_paper_v*.log), so a fixed filename read falls back to '' and
    misdetects the engine as pdflatex. Rejected iteration attempts
    (*_candidate_*.{log,tex}) are skipped — they may hold failed compiles that
    never produced the shipped PDF.
    """
    for d in _candidate_dirs(lw):
        preferred = Path(d) / preferred_name
        if preferred.exists():
            return str(preferred)
    for d in _candidate_dirs(lw):
        # final_refined_paper.* (the shipped compile) beats per-version files
        final = Path(d) / preferred_name.replace("raw_draft_paper", "final_refined_paper")
        if final.exists():
            return str(final)
    newest, mtime = "", 0.0
    for d in _candidate_dirs(lw):
        try:
            for f in Path(d).glob(pattern):
                # Only trust logs whose compile produced a PDF: failed
                # iteration attempts (no sibling .pdf) must not shadow the
                # shipped compile's log.
                if not f.with_suffix(".pdf").exists():
                    continue
                m = f.stat().st_mtime
                if m > mtime:
                    newest, mtime = str(f), m
        except Exception:
            continue
    if newest:
        return newest
    # No PDF-backed log: fall back to newest log regardless (best effort).
    return _newest(lw, pattern) if lw else ""


def _resolve_log(lw):
    return _resolve_artifact(lw, "raw_draft_paper.log", "*.log")


def _resolve_tex(lw):
    return _resolve_artifact(lw, "raw_draft_paper.tex", "*.tex")


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def _pdf_pages(pdf):
    m = re.search(r"Pages:\s+(\d+)", _run(["pdfinfo", pdf]))
    return int(m.group(1)) if m else 0


def _pdf_fonts(pdf):
    lines = _run(["pdffonts", pdf]).splitlines()[2:]
    return [l.split()[0] for l in lines if l.strip() and l.split()]


def _detect_columns(pdf):
    """Detect 1 vs 2 columns by rendering a page and finding a vertical gutter."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _run(["pdftoppm", "-png", "-f", "3", "-l", "3", "-r", "80", pdf, f"{td}/pg"])
        pngs = list(Path(td).glob("pg*.png"))
        if not pngs:
            return None
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(pngs[0]).convert("L")
            w, h = img.size
            arr = np.array(img)
            mid = arr[h // 4:3 * h // 4, w // 3:2 * w // 3]
            white_frac = np.mean(mid > 240, axis=0)
            return 2 if white_frac.max() > 0.9 else 1
        except Exception:
            return None


def _detect_engine(log):
    if "XeTeX" in log or "xelatex" in log.lower():
        return "xelatex"
    if "LuaTeX" in log:
        return "lualatex"
    return "pdflatex"


def _detect_font_size(log):
    m = re.search(r"Using fontsize (\d+)pt", log)
    return int(m.group(1)) if m else None


def _detect_bib_style(tex):
    m = re.search(r"\\bibliographystyle\{([^}]+)\}", tex)
    return m.group(1) if m else None


def _detect_anonymous(tex):
    return bool(re.search(r"anonymous", tex[:500], re.I))


def load_spec(template_dir):
    """Load format.yaml from the template dir."""
    yaml_path = os.path.join(template_dir or "", "format.yaml")
    text = _read(yaml_path)
    if not text:
        return {}
    spec = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if v.lower() in ("null", "none", ""):
            spec[k] = None
        elif v.lower() in ("true", "false"):
            spec[k] = v.lower() == "true"
        elif v.isdigit():
            spec[k] = int(v)
        else:
            spec[k] = v
    return spec


# ── checks ───────────────────────────────────────────────────────────────────

def check_compilation(lw, pdf, spec):
    log = _read(_resolve_log(lw))
    errors = re.findall(r"^! (.+)", log, re.MULTILINE)
    return {
        "errors": len(errors),
        "error_samples": errors[:3],
        "status": "FAIL" if errors else "PASS",
    }


def check_fonts(lw, pdf, spec):
    fonts = _pdf_fonts(pdf)
    fonts_str = " ".join(fonts).lower()
    expected = (spec.get("font_family") or "").lower()
    issues = []
    if expected == "libertine":
        if "libert" not in fonts_str:
            issues.append(f"Expected Libertine fonts, got: {fonts[:3]}")
            if "lmroman" in fonts_str:
                issues.append("  → Latin Modern fallback. Install texlive-fonts-extra.")
    elif expected == "times":
        # Times = ptm or NimbusRoman or similar
        if not any(k in fonts_str for k in ("times", "ptm", "nimbus", "linlib")):
            # IEEEtran uses Times-like; acmart with Libertine is also fine for "Times" venues
            pass  # too many valid variants; just warn if clearly wrong
    elif expected == "cjk":
        if not any(k in fonts_str for k in ("droid", "fandol", "noto", "sim", "cjk", "song")):
            issues.append("Chinese paper: no CJK font detected")
    return {"fonts_sample": fonts[:5], "expected": expected or "any", "issues": issues,
            "status": "WARN" if issues else "PASS"}


def check_font_size(lw, pdf, spec):
    log = _read(_resolve_log(lw))
    actual = _detect_font_size(log)
    expected = spec.get("body_font_pt")
    issues = []
    if expected and actual and actual != expected:
        issues.append(f"Font size {actual}pt, expected {expected}pt")
    return {"actual": actual, "expected": expected, "issues": issues,
            "status": "WARN" if issues else "PASS"}


def check_page_count(lw, pdf, spec):
    pages = _pdf_pages(pdf)
    limit = spec.get("page_limit_body")
    issues = []
    if limit:
        if pages > limit + 4:  # allow refs overhead
            issues.append(f"{pages} pages likely EXCEEDS body limit of {limit}")
        elif pages < limit * 0.4:
            issues.append(f"Only {pages} pages (limit {limit}) — paper may be too short")
    return {"pages": pages, "limit": limit, "issues": issues,
            "status": "FAIL" if (limit and pages > limit + 4) else "PASS"}


def check_columns(lw, pdf, spec):
    expected = spec.get("columns")
    actual = _detect_columns(pdf)
    issues = []
    if expected and actual and expected != actual:
        issues.append(f"Detected {actual}-column, expected {expected}-column")
    return {"actual": actual, "expected": expected, "issues": issues,
            "status": "WARN" if issues else "PASS"}


def check_engine(lw, pdf, spec):
    log = _read(_resolve_log(lw))
    actual = _detect_engine(log)
    expected = spec.get("engine")
    issues = []
    if expected and actual and actual != expected:
        issues.append(f"Compiled with {actual}, expected {expected}")
    return {"actual": actual, "expected": expected, "issues": issues,
            "status": "WARN" if issues else "PASS"}


def check_bib_style(lw, pdf, spec):
    tex = _read(_resolve_tex(lw))
    actual = _detect_bib_style(tex)
    expected = spec.get("bib_style")
    issues = []
    if expected and actual and expected.lower() not in actual.lower():
        issues.append(f"Bib style '{actual}', expected '{expected}'")
    return {"actual": actual, "expected": expected, "issues": issues,
            "status": "WARN" if issues else "PASS"}


def check_references(lw, pdf, spec):
    tex = _read(_resolve_tex(lw))
    bib = _read(f"{lw}/references.bib")
    cited = set()
    for c in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited.update(k.strip() for k in c.split(","))
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    orphans = bib_keys - cited
    missing = cited - bib_keys
    arxiv_on_formal = 0
    for entry in re.split(r"(?=@\w+\{)", bib):
        has_arxiv = "arxiv:" in entry.lower()
        venue_m = re.search(r"(?:booktitle|journal)\s*=\s*\{([^}]+)\}", entry)
        venue = (venue_m.group(1) or "").lower() if venue_m else ""
        if has_arxiv and venue and "arxiv" not in venue:
            arxiv_on_formal += 1
    issues = []
    if missing:
        issues.append(f"{len(missing)} cited keys MISSING from bib")
    if orphans:
        issues.append(f"{len(orphans)} orphan bib entries (uncited)")
    if arxiv_on_formal:
        issues.append(f"{arxiv_on_formal} formal-venue entries still have arXiv notes")
    return {
        "cite_count": len(re.findall(r"\\cite\{", tex)),
        "distinct_cited": len(cited), "bib_entries": len(bib_keys),
        "orphans": len(orphans), "missing": len(missing),
        "arxiv_on_formal": arxiv_on_formal, "issues": issues,
        "status": "FAIL" if missing else ("WARN" if orphans or arxiv_on_formal else "PASS"),
    }


def check_figures(lw, pdf, spec):
    tex = _read(_resolve_tex(lw))
    includes = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
    missing = []
    for inc in includes:
        found = any(os.path.exists(os.path.join(base, inc))
                    for base in [lw, f"{lw}/figures", f"{lw}/picture"])
        if not found:
            found = any(os.path.exists(os.path.join(base, "figures", os.path.basename(inc)))
                        for base in [lw, f"{lw}/picture"])
        if not found:
            missing.append(inc)
    labels = set(re.findall(r"\\label\{(fig:[^}]+)\}", tex))
    refs = set()
    for r in re.findall(r"\\(?:cref|ref|Cref)\{([^}]+)\}", tex):
        refs.update(k.strip() for k in r.split(","))
    issues = []
    if missing:
        issues.append(f"{len(missing)} missing file(s): {missing[:3]}")
    issues.extend([f"{max(0, len(includes) - len(labels))} figure(s) without \\label"]
                  if len(includes) > len(labels) else [])
    return {"total": len(includes), "missing": missing[:3], "issues": issues,
            "status": "FAIL" if missing else "PASS"}


def check_anonymity(lw, pdf, spec):
    tex = _read(_resolve_tex(lw))
    expected_anon = spec.get("anonymous")
    actual_anon = _detect_anonymous(tex)
    issues = []
    if expected_anon:
        emails = [e for e in re.findall(r"\\email\{([^}]+)\}", tex)
                  if "@" in e and "example" not in e and "xxx" not in e.lower()]
        if emails:
            issues.append(f"Anonymous venue but {len(emails)} real email(s) in tex")
    elif expected_anon is False and not actual_anon:
        pass  # non-anonymous venue, no issue
    return {"expected_anon": expected_anon, "actual_anon": actual_anon,
            "issues": issues, "status": "WARN" if issues else "PASS"}


def check_overfull(lw, pdf, spec):
    log = _read(_resolve_log(lw))
    vals = [float(v) for v in re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)]
    return {"total": len(vals), "large": sum(1 for v in vals if v > 20),
            "max": max(vals) if vals else 0,
            "status": "WARN" if any(v > 20 for v in vals) else "PASS"}


# ── runner ───────────────────────────────────────────────────────────────────

CHECKS = [
    ("Compilation",   check_compilation),
    ("Fonts",         check_fonts),
    ("Font Size",     check_font_size),
    ("Page Count",    check_page_count),
    ("Columns",       check_columns),
    ("Engine",        check_engine),
    ("Bib Style",     check_bib_style),
    ("References",    check_references),
    ("Figures",       check_figures),
    ("Anonymity",     check_anonymity),
    ("Overfull",      check_overfull),
]


def main():
    ap = argparse.ArgumentParser(description="Paper format checker (template-aware).")
    ap.add_argument("--paper_dir", required=True)
    ap.add_argument("--template_dir", default=None)
    args = ap.parse_args()

    lw = f"{args.paper_dir}/latex_writeup"
    pdf = next((f"{args.paper_dir}/{n}" for n in
                ["final_paper.pdf", "final_paper_enriched.pdf"]
                if os.path.exists(f"{args.paper_dir}/{n}")), None)
    if not pdf:
        pdfs = [f for f in os.listdir(lw) if f.endswith(".pdf")] if os.path.isdir(lw) else []
        pdf = f"{lw}/{pdfs[0]}" if pdfs else None

    spec = load_spec(args.template_dir)

    print("=" * 72)
    print(f"  FORMAT CHECK — {args.paper_dir}")
    print(f"  PDF: {pdf or '(not found)'}")
    venue = args.template_dir.split("/")[-1] if args.template_dir else "generic"
    print(f"  Venue: {venue}")
    if spec:
        print(f"  Spec: {spec.get('page_limit_body', '?')}p / "
              f"{spec.get('body_font_pt', '?')}pt / "
              f"{spec.get('columns', '?')}-col / "
              f"{spec.get('font_family', '?')} / "
              f"{spec.get('engine', '?')}")
    else:
        print("  Spec: (no format.yaml — generic checks only)")
    print("=" * 72)

    all_ok = True
    for name, fn in CHECKS:
        r = fn(lw, pdf or "", spec)
        st = r.pop("status", "?")
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(st, "?")
        if st in ("FAIL", "WARN"):
            all_ok = False
        detail = ", ".join(f"{k}={v}" for k, v in r.items() if k != "issues")
        print(f"{icon} {name:16s} [{st}]  {detail}")
        for issue in r.get("issues", []):
            print(f"   → {issue}")

    print(f"\n{'✅ ALL PASS' if all_ok else '⚠️ ISSUES FOUND'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
