#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_page_2026_10_18.py  (2026-10-18)  ETEXT_PAGE_2026_10_18

Found on 18 Oct: etext_witness.py's ALSO line read "... --page N   (the witness's reading of one page of the scan)",
and "--page N" was run as it stood (argparse: "argument --page: invalid int value: 'N'").

scripts/etext_witness.py (needs QUALITY_2026_10_11):
  - the ALSO line names a real page: the first page of the scan the witness reads, else the first page it offers for
    a page the scan cannot read, else the scan's first page; with no scan to compare (--page would refuse) no ALSO
    line at all. page_example() and also_page(), used in the three places that printed "--page N".
tests/test_quality_2026_10_11.py (its replay chain): etext_witness.py's later backup may be .bak_etextpage_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_etextpage_<date>. No database change; nothing is called. The dashboard's next-step reader (_rpNext) already
makes no button of a line with --page, so the desk is unchanged.
  python scripts\\patch_etext_page_2026_10_18.py --check
  python scripts\\patch_etext_page_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_PAGE_2026_10_18'
NEEDS = {'scripts/etext_witness.py': 'QUALITY_2026_10_11', 'tests/test_quality_2026_10_11.py': 'QUALITY_2026_10_11'}
FILES = list(NEEDS)
TAG = 'etextpage'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, r'''def show_page(m: dict, verses: list, page: int):
''', r'''def page_example(m) -> list:
    """ETEXT_PAGE_2026_10_18: a real page for the ALSO line (on 18 Oct its "--page N" was run as it stood): the first
    page of the scan the witness reads, else the first it offers for a page the scan cannot read, else the scan's first
    page; [] with no scan to compare (--page would refuse)."""
    if not m:
        return []
    pages = m.get("pages") or {}
    hit = sorted(p for p, r in pages.items() if (r or {}).get("status") == "match")
    off = sorted(o.get("page") for o in (m.get("offers") or []) if o.get("text") and o.get("page") is not None)
    first = hit or off or sorted(pages)
    return [first[0]] if first else []


def also_page(q: str, m, what: str) -> list:
    """ETEXT_PAGE_2026_10_18: the ALSO line, with a page that exists, or none."""
    return [q + " --page %d   (%s)" % (p, what) for p in page_example(m)]


def show_page(m: dict, verses: list, page: int):
''')

edit('scripts/etext_witness.py', 2, r'''                src.name, op, ": its own text is damaged (noise %.1f%%)" % wq["noise_pct"] if noisy else ""), "",
                [q + " --page N   (the witness's reading of one page of the scan)"])
''', r'''                src.name, op, ": its own text is damaged (noise %.1f%%)" % wq["noise_pct"] if noisy else ""), "",
                also_page(q, m, "the witness's reading of one page of the scan"))   # ETEXT_PAGE_2026_10_18
''')

edit('scripts/etext_witness.py', 3, r'''        say("%s reads as %d verses in %d pages: %s" % (src.name, len(verses), len(pages), op), q + " --write",
            [q + " --page N   (the witness's reading of one page of the scan)"])
''', r'''        say("%s reads as %d verses in %d pages: %s" % (src.name, len(verses), len(pages), op), q + " --write",
            also_page(q, m, "the witness's reading of one page of the scan"))   # ETEXT_PAGE_2026_10_18
''')

edit('scripts/etext_witness.py', 4, r'''        ["python scripts\\etext_witness.py --doc %s --file \"%s\" --page N   (the witness's reading of a page)" % (doc, src)])
''', r'''        also_page('python scripts\\etext_witness.py --doc %s --file "%s"' % (doc, src), m,
                  "the witness's reading of a page"))   # ETEXT_PAGE_2026_10_18
''')

edit('tests/test_quality_2026_10_11.py', 1, r'''                    or sorted(SCRIPTS.glob(f + ".bak_costtruth_*"))   # COST_TRUTH_2026_10_15 (source_desk.py)
''', r'''                    or sorted(SCRIPTS.glob(f + ".bak_costtruth_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_etextpage_*"))   # COST_TRUTH_2026_10_15; ETEXT_PAGE_2026_10_18
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_etext_page_2026_10_18 tests.test_etext_witness_2026_10_11 tests.test_quality_2026_10_11 tests.test_benchmark_2026_10_11 tests.test_path_2026_10_12')
    return 0


if __name__ == "__main__":
    sys.exit(main())
