#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_heal_2026_10_28.py  (2026-10-28)  HEAL_2026_10_28

Two mends found after INDEX_SITE_2026_10_25 went live.

1. scripts\\vamsa_view.py: a line of descent drawn through one of two parents of the same name that the index gives
   no entry for (two name-only "Diti"s, say) was chosen by the order of a Python set, which changes from run to run.
   So each run of index_sync.py found 80 to 150 persons whose line had "changed" and sent them again (the mirror's
   log, 26 to 28 Oct), and the line drawn for them flipped. Every choice and every list ordered by head word now ends
   with the entry, so the same stores draw the same line in every run, on the desk and on the site (the site already
   ordered siblings, other parents and children by head word, then entry: they now agree in every case).
2. tests\\test_edition_refs_2026_10_18.py: its replay compared the patched copy with export_html.py as it is now; the
   prose edition (PROSE_EDITION_2026_10_25) changed export_html.py since, so on the PC, where the .bak copies are,
   the suite failed there (1 of 207 modules, 25 Oct). It now compares with the file as that patch left it: the oldest
   later backup that already carries its marker.

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_heal_<date> copies; py_compile first.

  python scripts\\patch_heal_2026_10_28.py --check
  python scripts\\patch_heal_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'HEAL_2026_10_28'
TAG = 'heal'
FILES = ['scripts/vamsa_view.py', 'tests/test_edition_refs_2026_10_18.py']
NEEDS = {'scripts/vamsa_view.py': 'VAMSA_UI_2026_10_25', 'tests/test_edition_refs_2026_10_18.py': 'EDITION_REFS_2026_10_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_view.py', 1, '        if not ps:\n            break\n        ps.sort(key=lambda p: (p[1] < 0, g["sex"].get(p) != "m", g["sex"].get(p) == "f", -_strength(g, src, p[1], node[1]),\n                               -g["up"].get(p, 1), _head(g, src, p[1])))\n        node = ps[0]\n        seen.add(node[1]); out.append(node[1])',
     '        if not ps:\n            break\n        # HEAL_2026_10_28: the entry last, so a tie (two name-only parents of one name) is the same in every run\n        ps.sort(key=lambda p: (p[1] < 0, g["sex"].get(p) != "m", g["sex"].get(p) == "f", -_strength(g, src, p[1], node[1]),\n                               -g["up"].get(p, 1), _head(g, src, p[1]), p[1]))\n        node = ps[0]\n        seen.add(node[1]); out.append(node[1])')

edit('scripts/vamsa_view.py', 2, '        if not cs:\n            break\n        cs.sort(key=lambda c: (c[1] < 0, -g["down"].get(c, 1), g["sex"].get(c) == "f", _head(g, src, c[1])))\n        node = cs[0]\n        seen.add(node[1]); out.append(node[1])',
     '        if not cs:\n            break\n        cs.sort(key=lambda c: (c[1] < 0, -g["down"].get(c, 1), g["sex"].get(c) == "f", _head(g, src, c[1]), c[1]))\n        node = cs[0]\n        seen.add(node[1]); out.append(node[1])')

edit('scripts/vamsa_view.py', 3, '            "entity": g["entity_of"].get(node),\n            "spouses": [{"entry": s, "head": _head(g, src, s)} for s in sorted(g["spouses"].get(node, ()),\n                                                                              key=lambda z: _head(g, src, z))][:6]}\n\n',
     '            "entity": g["entity_of"].get(node),\n            "spouses": [{"entry": s, "head": _head(g, src, s)} for s in sorted(g["spouses"].get(node, ()),\n                                                                              key=lambda z: (_head(g, src, z), z))][:6]}\n\n')

edit('scripts/vamsa_view.py', 4, '            continue\n        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n)]\n        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1])))\n        kept = []\n        for n in roots:',
     '            continue\n        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n)]\n        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1]), n[1]))\n        kept = []\n        for n in roots:')

edit('scripts/vamsa_view.py', 5, '        node = (src, e)\n        par = line[i - 1] if i else None\n        sibs = sorted((c[1] for c in g["chi"].get((src, par), ()) if c[1] != e), key=lambda z: _head(g, src, z)) \\\n            if par is not None else []\n        others = sorted((p[1] for p in g["par"].get(node, ()) if p[1] != par), key=lambda z: _head(g, src, z))\n        rungs.append(dict(_person(g, src, e), generation=i - me,\n                          siblings=[{"entry": s, "head": _head(g, src, s)} for s in sibs[:16]],',
     '        node = (src, e)\n        par = line[i - 1] if i else None\n        sibs = sorted((c[1] for c in g["chi"].get((src, par), ()) if c[1] != e), key=lambda z: (_head(g, src, z), z)) \\\n            if par is not None else []\n        others = sorted((p[1] for p in g["par"].get(node, ()) if p[1] != par), key=lambda z: (_head(g, src, z), z))\n        rungs.append(dict(_person(g, src, e), generation=i - me,\n                          siblings=[{"entry": s, "head": _head(g, src, s)} for s in sibs[:16]],')

edit('scripts/vamsa_view.py', 6, '        nxt = []\n        for p in level:\n            for c in sorted((c[1] for c in g["chi"].get((src, p), ())), key=lambda z: _head(g, src, z)):\n                if c in seen:\n                    continue',
     '        nxt = []\n        for p in level:\n            for c in sorted((c[1] for c in g["chi"].get((src, p), ())), key=lambda z: (_head(g, src, z), z)):\n                if c in seen:\n                    continue')

edit('tests/test_edition_refs_2026_10_18.py', 1, '\n\nclass ThePatcher(unittest.TestCase):\n    FILES = ("scripts/export_html.py", "tests/test_scholar_edition_2026_10_17.py")',
     '\n\ndef as_left(rel: str) -> bytes:\n    """The file as this patch left it. HEAL_2026_10_28: a later patch of the same file (PROSE_EDITION_2026_10_25 changed\n    export_html.py) keeps that state in its own backup, the oldest one that already carries MARK; without one, the file\n    as it is now."""\n    p = REPO / rel\n    later = [b for b in p.parent.glob(p.name + ".bak_*")\n             if ".bak_editionrefs_" not in b.name and MARK in b.read_bytes()]\n    return min(later, key=lambda b: b.stat().st_mtime).read_bytes() if later else p.read_bytes()\n\n\nclass ThePatcher(unittest.TestCase):\n    FILES = ("scripts/export_html.py", "tests/test_scholar_edition_2026_10_17.py")')

edit('tests/test_edition_refs_2026_10_18.py', 2, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), as_left(f), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

