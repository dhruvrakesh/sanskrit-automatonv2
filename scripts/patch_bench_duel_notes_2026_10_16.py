#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_duel_notes_2026_10_16.py  (2026-10-16)  BENCH_DUEL_NOTES_2026_10_16

BM3's pilot (40 units, both judges, 16 Oct) put the scholarly pipeline first by a wide margin. One thing in its
method could lean that way: only the scholarly arm has notes, and duel-v1 shows each translation's notes, so the notes
name it, and a judge may rank an annotated translation higher for its notes (the rubric ranks fidelity first, but a
judge is not bound by it). The check: the same units again with the notes withheld.

scripts/bench_duel.py (needs BENCH_DUEL_2026_10_16):
  - --no-notes: the scholarly arm's notes are not shown to the judges (every translation then has none); its readings
    are stored apart (the English the judges saw differs, so a reading with the notes is not taken for one without);
    each reading says notes_shown;
  - --report --no-notes writes BM3_nonotes_report.html and BM3_nonotes_summary.json; BM3_report.html and
    BM3_summary.json stay the readings with the notes (duel-v1 as it is). The dashboard reads BM3_summary.json as
    before.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_duelnotes_<date>. No database change.
  python scripts\\patch_bench_duel_notes_2026_10_16.py --check
  python scripts\\patch_bench_duel_notes_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "BENCH_DUEL_NOTES_2026_10_16"
NEEDS = {"scripts/bench_duel.py": "BENCH_DUEL_2026_10_16"}
FILES = list(NEEDS)
TAG = "duelnotes"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/bench_duel.py', 1, r'''  python scripts\\bench_duel.py --settle                                          what a stopped run left (free)
''', r'''  python scripts\\bench_duel.py --settle                                          what a stopped run left (free)
  python scripts\\bench_duel.py --units 40 --with-reference --no-notes --yes --max-usd 4.50
      BENCH_DUEL_NOTES_2026_10_16: the check of the pilot, the scholarly arm's notes withheld (only it has notes, so
      they name it, and a judge may rank an annotated translation higher for its notes); its own report,
      BM3_nonotes_report.html and BM3_nonotes_summary.json (python scripts\\bench_duel.py --report --no-notes).
''')

edit('scripts/bench_duel.py', 2, r'''SOURCE = "a digital e-text"
''', r'''SOURCE = "a digital e-text"
NOTES_SHOWN = True   # BENCH_DUEL_NOTES_2026_10_16: --no-notes withholds the scholarly arm's notes (a check)
NAME = "BM3"         # the report's files: BM3_report.html, BM3_summary.json (BM3_nonotes_* with --no-notes)
''')

edit('scripts/bench_duel.py', 3, r'''        if arm == "scholar":
            notes = ST._loads(''', r'''        if arm == "scholar" and NOTES_SHOWN:   # BENCH_DUEL_NOTES_2026_10_16: --no-notes withholds them
            notes = ST._loads(''')

edit('scripts/bench_duel.py', 4, r'''    if a.with_reference:
        print("  the published English is the fourth translation''', r'''    if not NOTES_SHOWN:   # BENCH_DUEL_NOTES_2026_10_16
        print("  the scholarly arm's notes are withheld (the check: only it has notes, so they name it)")
    if a.with_reference:
        print("  the published English is the fourth translation''')

edit('scripts/bench_duel.py', 5, r'''                           "version": SD.DUEL_VERSION, "contestants": sorted(t["texts"]), "shas": t["shas"],
''', r'''                           "version": SD.DUEL_VERSION, "notes_shown": NOTES_SHOWN,   # BENCH_DUEL_NOTES_2026_10_16
                           "contestants": sorted(t["texts"]), "shas": t["shas"],
''')

edit('scripts/bench_duel.py', 6, r'''               "units_total": len(order_of(items)), "with_reference": with_ref, "scopes": nums, "spend": sp,
''', r'''               "units_total": len(order_of(items)), "with_reference": with_ref, "scopes": nums, "spend": sp,
               "notes_shown": NOTES_SHOWN,   # BENCH_DUEL_NOTES_2026_10_16
''')

edit('scripts/bench_duel.py', 7, r'''    jp = out / "BM3_summary.json"
''', r'''    jp = out / (NAME + "_summary.json")   # BENCH_DUEL_NOTES_2026_10_16: BM3_nonotes_* with --no-notes
''')

edit('scripts/bench_duel.py', 8, r'''    hp = out / "BM3_report.html"
''', r'''    hp = out / (NAME + "_report.html")
''')

edit('scripts/bench_duel.py', 9, r'''         "<h1>BM3: the blind side-by-side of BM1's English</h1>",
''', r'''         "<h1>BM3: the blind side-by-side of BM1's English%s</h1>" % ("" if NOTES_SHOWN else ": the check, the scholarly "
                                                                         "arm's notes withheld"),
''')

edit('scripts/bench_duel.py', 10, r'''    ap.add_argument("--with-reference", action="store_true", help="the published English as a fourth translation")
''', r'''    ap.add_argument("--with-reference", action="store_true", help="the published English as a fourth translation")
    ap.add_argument("--no-notes", action="store_true", help="the scholarly arm's notes withheld (a check: they name it); "
                    "its report is BM3_nonotes_report.html")   # BENCH_DUEL_NOTES_2026_10_16
''')

edit('scripts/bench_duel.py', 11, r'''    global ME
''', r'''    global ME, NOTES_SHOWN, NAME
    NOTES_SHOWN, NAME = (False, "BM3_nonotes") if a.no_notes else (True, "BM3")   # BENCH_DUEL_NOTES_2026_10_16
''')

edit('scripts/bench_duel.py', 12, r'''        (" --judges %s" % a.judges) if a.judges != ",".join(SD.JUDGES) else "")
''', r'''        (" --judges %s" % a.judges) if a.judges != ",".join(SD.JUDGES) else "") + (" --no-notes" if a.no_notes else "")
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
    if not Path("scripts/bench_duel.py").exists():
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
    print("  python -m unittest tests.test_bench_duel_notes_2026_10_16 tests.test_bench_duel_2026_10_16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
