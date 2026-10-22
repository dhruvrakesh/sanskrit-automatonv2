#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_gretil_next_2026_10_22.py  GRETIL_NEXT_2026_10_22

scripts/gretil_library.py --match ended "NEXT: python scripts\\gretil_library.py --extract MEMBER --doc DOC": the
shape of a command, which was run as printed on 22 Oct ("not in 1_sanskr.zip: MEMBER"). It now prints the commands
themselves for the strong matches that have no witness yet (none in data\\raw_witness\\<doc>__w_*): the extract and
the preview, the first three, the others named; when every strong match has its witness, it points to
scripts\\ocr_benchmark.py. Nothing else changes.

Needs GRETIL_LIBRARY_2026_10_22. Anchored, all-or-nothing, marker-idempotent, backup first (.bak_gretilnext_<date>),
line endings kept, compiled before it is written.

  python scripts\\patch_gretil_next_2026_10_22.py --check
  python scripts\\patch_gretil_next_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'GRETIL_NEXT_2026_10_22'
TAG = 'gretilnext'
FILES = ['scripts/gretil_library.py']
NEEDS = {'scripts/gretil_library.py': 'GRETIL_LIBRARY_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/gretil_library.py', 1, '                  n_strong, int(STRONG * 100), RATIO, sum(1 for r in rows if r["verdict"] == "a part or a parallel"),\n                  sum(1 for r in rows if r["verdict"].startswith("possible"))))\n    print("NEXT: python scripts\\\\gretil_library.py --extract MEMBER --doc DOC, then python scripts\\\\etext_witness.py "\n          "--doc DOC --file sources\\\\DOC\\\\FILE (the preview)")\n    return 0\n',
     '                  n_strong, int(STRONG * 100), RATIO, sum(1 for r in rows if r["verdict"] == "a part or a parallel"),\n                  sum(1 for r in rows if r["verdict"].startswith("possible"))))\n    # GRETIL_NEXT_2026_10_22: the commands themselves, for the strong matches that have no witness yet (on 22 Oct\n    # "--extract MEMBER --doc DOC" was run as printed)\n    todo = [r for r in sorted(rows, key=lambda r: -(r["top"][0]["lift"] if r["top"] else 0))\n            if r["verdict"] == "strong" and not any((ROOT / "data" / "raw_witness").glob(r["doc"] + "__w_*"))\n            ] if not stopped else []\n    for r in todo[:3]:\n        m = r["top"][0]["html"]\n        print("NEXT: python scripts\\\\gretil_library.py --extract %s --doc %s" % (m, r["doc"]))\n        print("      python scripts\\\\etext_witness.py --doc %s --file sources\\\\%s\\\\%s   (the preview)" % (\n            r["doc"], r["doc"], Path(m).name))\n    if len(todo) > 3:\n        print("ALSO: %d more strong matches without a witness: %s" % (len(todo) - 3, ", ".join(r["doc"] for r in todo[3:])))\n    if not todo and not stopped:\n        print("NEXT: every strong match has its witness (data\\\\raw_witness); python scripts\\\\ocr_benchmark.py measures "\n              "our readings against them all")\n    return 0\n')


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
