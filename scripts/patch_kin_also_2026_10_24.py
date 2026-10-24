#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
KIN_ALSO_2026_10_24: kin_index.py's ALSO line names the run that reads what is left.

The fault (24 Oct): after "python scripts\\kin_index.py --per-source 0" (the plan of the full run) it said "2243 entries
of the trial are not read yet: python scripts\\kin_index.py --yes". That command reads the trial (100 entries of each
index), which was read long ago: it would read nothing. The line now says "in all" and gives --per-source and a
--max-usd of twice the plan (Soerensen's long entries cost about twice their plan on 24 Oct). Nothing else changes.

Run from the repo root:  python scripts\\patch_kin_also_2026_10_24.py --check   then without --check.
Backup: scripts\\kin_index.py.bak_kin_also_ and the date. Test: tests\\test_kin_also_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'KIN_ALSO_2026_10_24'
TAG = 'kin_also'
FILES = ['scripts/kin_index.py']
NEEDS = {'scripts/kin_index.py': 'KIN_LINES_2026_10_24'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/kin_index.py', 1, '        "--per-source 0 --max-usd 4.50 (the plan prices it first: about $4)" if a.per_source and unread != 0 else\n        "read exports\\\\kin_lineages.md and kin_cards.md; one name: python scripts\\\\kin_index.py --show Janamejaya",\n        ["%d entries of the trial are not read yet: python scripts\\\\kin_index.py --yes" % left] if left else [])\n    return 0\n',
     '        "--per-source 0 --max-usd 4.50 (the plan prices it first: about $4)" if a.per_source and unread != 0 else\n        "read exports\\\\kin_lineages.md and kin_cards.md; one name: python scripts\\\\kin_index.py --show Janamejaya",\n        ["%d entries %s are not read yet: python scripts\\\\kin_index.py --yes%s" % (   # KIN_ALSO_2026_10_24\n            left, "of the trial" if a.per_source else "in all",\n            "" if a.per_source == 100 else " --per-source %d --max-usd %.2f (twice the plan: long entries cost more)" % (\n                a.per_source, max(a.max_usd, round(planned * 2 + 0.005, 2))))] if left else [])\n    return 0\n')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
