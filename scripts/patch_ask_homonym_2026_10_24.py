#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
ASK_HOMONYM_2026_10_24: the Professor keeps apart the persons who share a name.

The fault (24 Oct, found with the kinship lines): one of our names stands for every person of that name, and the
indexes number them (among the entries with relations, 1,036 names are borne by more than one entry of the same
index: Janamejaya (I), son of Puru; Janamejaya (II), son of Pariksit). The Professor's evidence gives each index statement with its entry (s.v.
Janamejaya (II)), but its instruction did not say what the number means, so an answer could join two persons' lives.

The fix: one sentence added to the Professor's instruction (_ASK_SYSTEM_PROF in scripts/dashboard.py): a numbered name
is one of several persons in its index; keep each apart, never join two into one life or one line of descent, and say
which person a statement is about. Nothing else changes. Restart the dashboard when it is idle.

Run from the repo root:  python scripts\\patch_ask_homonym_2026_10_24.py --check   then without --check.
Backup: scripts\\dashboard.py.bak_ask_homonym_ and the date. Test: tests\\test_ask_homonym_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ASK_HOMONYM_2026_10_24'
TAG = 'ask_homonym'
FILES = ['scripts/dashboard.py']
NEEDS = {'scripts/dashboard.py': 'ASK_PROF_2026_10_23'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, '    "evidence does not answer the question, say so plainly and name what would settle it (a text the scholars cite "\n    "that is not among the passages). Begin with a short answer, then the evidence and the reasoning. English, "\n    "precise and plain; Sanskrit names in IAST."\n)\n_PROF_SHELF = {"pui": "Purana Index (Dikshitar)", "vei": "Vedic Index (Macdonell and Keith)",',
     '    "evidence does not answer the question, say so plainly and name what would settle it (a text the scholars cite "\n    "that is not among the passages). Begin with a short answer, then the evidence and the reasoning. English, "\n    "precise and plain; Sanskrit names in IAST. "\n    # ASK_HOMONYM_2026_10_24: the indexes number the persons who share a name; one of our names stands for them all\n    "A name with a number, as Janamejaya (II) or Jaratkaru[2], is one of several persons of that name in its index "\n    "(the entry is given as s.v.): keep each numbered person apart, never join two of them into one life or one line "\n    "of descent, and say which person a statement is about."\n)\n_PROF_SHELF = {"pui": "Purana Index (Dikshitar)", "vei": "Vedic Index (Macdonell and Keith)",')


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
