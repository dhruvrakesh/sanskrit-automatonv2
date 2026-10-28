#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
docs_map.py  (2026-10-28)  DOCS98_2026_10_28

The map of the documentation, made from the files' own first lines, so it cannot drift from them:
  - the files at the root and in docs\\ (Markdown): each file's title (its first "# " line), its date (from its name),
    the markers it names in its first lines, grouped by what it is about, newest first;
  - docs\\cloud\\: the SQL for the Lovable Cloud SQL editor in the order it is pasted (C0, C1, C1c, C2 ... C24), each
    with its title line and what it needs (its own "-- Needs" line), its checks beside it, and the edge functions;
  - docs\\srangam\\: the Srangam kits, by date.
Read-only but for --write; no model, no network.

  python scripts\\docs_map.py            print the map
  python scripts\\docs_map.py --write    write docs\\DOCS_MAP.md (only when it changes)
  python scripts\\docs_map.py --check    exit 1 when docs\\DOCS_MAP.md is not the map of the files as they are
"""
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path

MARK = "DOCS98_2026_10_28"
OUT = Path("docs") / "DOCS_MAP.md"
MARKER = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_20\d\d_\d\d_\d\d\b")
DATE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
TAIL_MARKS = re.compile(r"\s*\((?:\s*[A-Z][A-Z0-9_]*_20\d\d_\d\d_\d\d\s*,?)+\)\s*$")
HEAD_LINES = 40

# What a dated file is about, by its name (the first rule that matches wins).
THEMES = [
    ("Start here", r"^(STATE|EVOLUTION|ASKS|README|RUNBOOK|ARCHITECTURE|STEPS_TO_RUN|UPDATING)"),
    ("Plans and paths", r"^(ENTERPRISE|PATH|BRAIN_PATH|OPERATING_MODEL|PLATFORM|CLOUD_BRAIN|PIPELINE_STATE|"
                        r"RETIREMENT|SOP_|QUALITY_METHODOLOGY|DEBT|.*_DESIGN_)"),
    ("Names, relations and genealogies", r"^(RELATIONS|VAMSA|INDEX_SITE|B2_AND_X1C|CLAIMS_AND_REFS|SHELF_AND)"),
    ("The site and the mirror", r"^(CORPUS_MIRROR|SRANGAM|SYNC_COMMANDS|MIRROR_CAP|SCHOLAR_READER|SCHOLAR_SITE|"
                                r"EDITIONS_SITE|LOAD_|MEDIA_AND_CORNER|RESEARCHERS?_|CORNER_)"),
    ("The desk (dashboard)", r"^(DESK_HEAL|BUTTONS|LIVE_LOG|BENCH_DESK|TRANSLATION_DESK|LIBRARY_SCHOLAR|JUDGE_DESK)"),
    ("Translation and its quality", r"^(SCHOLAR|CLAUDE|GEMINI|PILOT|SONNET|CANARY|TRIAGE|JUDGE|QUALITY|REDEEM|"
                                    r"PROVISIONAL|FIDELITY|BENCH|BM\d|CLASSIFY|HINDI|TRANSLATION|COST|LEAK)"),
    ("Texts: scans, repair and editions", r"^(REPAIR|REINGEST|READ_IN|OCR|ETEXT|EDITIONS|NEXT_BOOKS|PARK|"
                                          r"CONSOLIDATION)"),
]
ORDER = [t for t, _ in THEMES] + ["Other"]


def theme_of(name: str) -> str:
    for t, rx in THEMES:
        if re.match(rx, name):
            return t
    return "Other"


def head(p: Path, n: int = HEAD_LINES) -> list[str]:
    out = []
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= n:
                    break
                out.append(line.rstrip("\r\n"))
    except OSError:
        pass
    return out


def date_of(name: str) -> str:
    m = DATE.search(name)
    return "%s-%s-%s" % m.groups() if m else ""


def markers(lines: list[str]) -> list[str]:
    seen: list[str] = []
    for line in lines:
        for m in MARKER.findall(line):
            if m not in seen:
                seen.append(m)
    return seen


def cell(s: str) -> str:
    return s.replace("|", "\\|").strip()


def md_entry(p: Path, root: Path) -> dict:
    lines = head(p)
    title = next((x[2:].strip() for x in lines if x.startswith("# ")), "") or p.stem
    return {"path": p.relative_to(root).as_posix(), "name": p.name, "date": date_of(p.name),
            "title": TAIL_MARKS.sub("", title), "marks": markers(lines)[:4], "theme": theme_of(p.name)}


def c_key(name: str):
    """C0, C1, C1c, C2 ... C10a, C24 in the order they are pasted (a preflight before its change, the checks after
    it); then the others by name."""
    m = re.match(r"^C(\d+)([a-z]?)_", name)
    step = 0 if "_preflight_" in name else 2 if re.search(r"_(checks|verify)_", name) else 1
    return (0, int(m.group(1)), m.group(2), step, name) if m else (1, 0, "", 0, name)


def sql_entry(p: Path, root: Path) -> dict:
    lines = head(p, 60)
    comments = [x for x in lines if x.startswith("--")]
    title = ""
    for x in comments:
        t = x.lstrip("-").strip()
        if t and not set(t) <= set("=-"):
            title = t
            break
    needs = next((x.lstrip("-").strip() for x in comments if re.match(r"^--\s*Needs\b", x)), "")
    needs = needs.split(". ")[0].rstrip(".")
    if title.upper().startswith("SUPERSEDED"):
        kind = "superseded"
    elif re.search(r"_(checks|preflight|verify)_", p.name) or re.match(r"^(CHECKS|OPS)_", p.name) \
            or "read-only" in title.lower():
        kind = "checks"
    else:
        kind = "draft" if "DRAFT" in p.name else "change"
    return {"path": p.relative_to(root).as_posix(), "name": p.name, "date": date_of(p.name), "title": title,
            "needs": needs, "kind": kind}


def build(root: Path) -> str:
    docs = root / "docs"
    rows = []
    for p in sorted(list(root.glob("*.md")) + list(docs.glob("*.md"))):
        if p.name == OUT.name or ".bak_" in p.name:
            continue
        rows.append(md_entry(p, root))
    newest = max([r["date"] for r in rows if r["date"]] or [""])
    L = ["# The map of the documentation (%s)" % MARK, "",
         "Made by `python scripts\\docs_map.py --write` from the files' own first lines (their titles, the dates in",
         "their names, the markers they name); not written by hand. `--check` says when it is stale.",
         "%d %s; the newest is of %s." % (len(rows), "document" if len(rows) == 1 else "documents", newest or "no date"),
         ""]
    for t in ORDER:
        group = [r for r in rows if r["theme"] == t]
        if not group:
            continue
        group.sort(key=lambda r: (r["date"] or "0000", r["name"]), reverse=True)
        L += ["## %s" % t, "", "| Date | File | What it is | Markers |", "|---|---|---|---|"]
        for r in group:
            L.append("| %s | [%s](%s) | %s | %s |" % (r["date"] or "-", r["name"], os.path.relpath(
                root / r["path"], docs).replace(os.sep, "/"), cell(r["title"]), ", ".join(r["marks"]) or "-"))
        L.append("")
    cloud = docs / "cloud"
    if cloud.is_dir():
        sqls = [sql_entry(p, root) for p in cloud.glob("*.sql") if ".bak_" not in p.name]
        sqls.sort(key=lambda r: c_key(r["name"]))
        L += ["## The cloud SQL, in the order it is pasted", "",
              "Each file once, whole, in the Lovable Cloud SQL editor; its checks one query per paste.", "",
              "| File | Kind | What it is | Needs |", "|---|---|---|---|"]
        for r in sqls:
            L.append("| [%s](cloud/%s) | %s | %s | %s |" % (r["name"], r["name"], r["kind"], cell(r["title"]),
                                                          cell(r["needs"]) or "-"))
        fns = sorted((p for p in cloud.iterdir() if p.is_dir()), key=lambda p: c_key(p.name))
        if fns:
            L += ["", "Edge functions (deployed by Lovable, as they are): " +
                  ", ".join("[%s](cloud/%s)" % (p.name, p.name) for p in fns) + "."]
        L.append("")
    kits = docs / "srangam"
    if kits.is_dir():
        ks = sorted((p for p in kits.iterdir() if p.is_dir()), key=lambda p: (date_of(p.name), p.name), reverse=True)
        L += ["## The Srangam kits", "",
              "Each applied in D:\\srangam-42267 by its scripts\\patch_srangam_*.py, over the exact files main had.", "",
              "| Date | Kit | Files |", "|---|---|---|"]
        for p in ks:
            n = sum(1 for x in p.rglob("*") if x.is_file())
            L.append("| %s | [%s](srangam/%s) | %d |" % (date_of(p.name) or "-", p.name, p.name, n))
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="the map of the documentation (%s)" % MARK)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="write docs\\DOCS_MAP.md when it changes")
    g.add_argument("--check", action="store_true", help="exit 1 when docs\\DOCS_MAP.md is stale")
    args = ap.parse_args()
    root = Path.cwd()
    if not (root / "docs").is_dir():
        print("FAIL: run this from the repository root (there is no docs folder here)."); return 2
    text = build(root)
    out = root / OUT
    old = out.read_bytes().replace(b"\r\n", b"\n").decode("utf-8", "replace") if out.exists() else None
    if args.check:
        if old == text:
            print("docs\\DOCS_MAP.md is current."); return 0
        print("docs\\DOCS_MAP.md is stale: python scripts\\docs_map.py --write"); return 1
    if args.write:
        if old == text:
            print("Nothing to do: docs\\DOCS_MAP.md is current."); return 0
        tmp = out.with_name(out.name + ".tmp_docsmap")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, out)
        print("wrote docs\\DOCS_MAP.md (%d lines)" % text.count("\n")); return 0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
