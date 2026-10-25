#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_vamsa_names_2026_10_25.py  (2026-10-25)  VAMSA_NAMES_2026_10_25

scripts\\vamsa_check.py --name X listed a statement as often as the index makes it (147 relations of Janamejaya, many
the same: an entry that lists it twice, or two entries of the name). Each statement (one index, the same subject,
relation and object) is now shown once, "x n", with its best check (cited both, then one, then neither; then the most
epic verses), and the count of distinct statements is said. Nothing stored changes.

Needs VAMSA_CHECK_2026_10_25. Anchored, all-or-nothing, marker-idempotent; line endings kept; a
.bak_vamsanames_<date> copy; compiled before anything is written. Test: tests\\test_vamsa_names_2026_10_25.py.

  python scripts\\patch_vamsa_names_2026_10_25.py --check
  python scripts\\patch_vamsa_names_2026_10_25.py
  python scripts\\vamsa_check.py --name Janamejaya
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_NAMES_2026_10_25'
TAG = 'vamsanames'
FILES = ['scripts/vamsa_check.py']
NEEDS = {'scripts/vamsa_check.py': 'VAMSA_CHECK_2026_10_25'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_check.py', 1, '    finally:\n        con.close()\n    print("%s: %d relation(s) name %s" % (MARK, len(rows), who))\n    for r in rows[:200]:\n        g = got.get(r["kin_id"])\n        if not g:\n            continue\n        where = ref_text(g[2], tuple(int(x) for x in g[3].split("."))) if g[3] else ""\n        print("  [%s] %s %s %s | cited: %s%s%s | together: MBh %s%s, HV %s, Ram %s" % (\n            SHORT[r["source"]], r["subject"], r["relation"], r["object"], g[1] or "-",\n            (" at " + where) if where else "", (" (%s / %s)" % (g[4], g[5])) if (g[4] or g[5]) else "",\n            g[6] or 0, (" first " + g[7]) if g[7] else "", g[8] or 0, g[10] or 0))\n    print("VERDICT: %d relation(s) of %s shown" % (len(rows), who)); print("NEXT: open /vamsa on the dashboard")\n    return 0\n',
     '    finally:\n        con.close()\n    # VAMSA_NAMES_2026_10_25: a statement an index makes more than once (the same subject, relation and object in one\n    # source: an entry that lists it twice, or two entries of the name) is shown once, "x n", with its best check\n    groups = collections.OrderedDict()\n    for r in rows:\n        g = got.get(r["kin_id"])\n        if g:\n            groups.setdefault((r["source"], nfc(r["subject"]), r["relation"], nfc(r["object"])), []).append((r, g))\n    print("%s: %d relation(s) name %s, %d distinct statement(s)" % (MARK, len(rows), who, len(groups)))\n    for items in list(groups.values())[:200]:\n        r, g = min(items, key=lambda x: (ORDER.index(x[1][1]) if x[1][1] in ORDER else len(ORDER), -(x[1][6] or 0),\n                                         x[0]["kin_id"]))\n        where = ref_text(g[2], tuple(int(x) for x in g[3].split("."))) if g[3] else ""\n        print("  [%s] %s %s %s%s | cited: %s%s%s | together: MBh %s%s, HV %s, Ram %s" % (\n            SHORT[r["source"]], r["subject"], r["relation"], r["object"], (" x%d" % len(items)) if len(items) > 1 else "",\n            g[1] or "-", (" at " + where) if where else "", (" (%s / %s)" % (g[4], g[5])) if (g[4] or g[5]) else "",\n            g[6] or 0, (" first " + g[7]) if g[7] else "", g[8] or 0, g[10] or 0))\n    print("VERDICT: %d relation(s) of %s shown as %d distinct statement(s)" % (len(rows), who, len(groups)))\n    print("NEXT: open /vamsa on the dashboard")\n    return 0\n')


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
