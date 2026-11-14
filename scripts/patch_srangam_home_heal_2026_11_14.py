#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_home_heal_2026_11_14.py  (2026-11-14)  HOME_HEAL_2026_11_14

For the SRANGAM repo (run from D:\\srangam-42267, on main, with DYNASTIES_2026_11_11: 6d8aad4 or later). Asked on 14 Nov:
"SACRED eCOLOGY LINK IS BROKEN AND 404. IS HOMEPAGE RATIONALISED AND REFLECTIVE OF OUR PRESENT IMPLEMENTATION AND STACK?"
and, on 13 Nov, a "start here" in plain words for amateur Sanskritists (U1). This kit:
  - src/components/home/GeomythologySection.tsx: each card links its article itself (/articles/<slug>); the fourth
    pointed at /sacred-ecology, which no route and no article has (the 404). It opens Part 1 of the Sacred Ecology
    series, "Under the Sacred Tree" (/articles/sacred-tree-harvest-rhythms), as the Ancient India theme page does;
  - src/App.tsx: /sacred-ecology redirects there, for links already out in the world;
  - src/components/home/CorpusStartSection.tsx (new): "Start here: the texts themselves", seven doors in plain words
    (the published texts and the scholarly editions, open to all; the scholarly English as prose, the dynasties, the
    names, the stories and the guided steps, for invited readers), static, lazy (3.7 kB, 1.6 kB gzipped);
  - src/pages/Home.tsx: it, lazily, after the opening section and before the featured articles;
  - src/__tests__/home-heal.test.tsx (new): every link written on the home page is a route; every card opens an
    article that exists; every door is a route.
The files travel in the automaton repository, docs\\srangam\\HOME_HEAL_2026-11-14\\. A replaced file is written only over
the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is refused,
never overwritten. All-or-nothing; backups .bak_homeheal_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_home_heal_2026_11_14.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_home_heal_2026_11_14.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, shutil
from pathlib import Path

MARK = "HOME_HEAL_2026_11_14"
PREREQ = ("src/App.tsx", "DYNASTIES_2026_11_11")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "HOME_HEAL_2026-11-14"
TAG = "homeheal"

# path -> md5 of the LF text main has (6d8aad4)
REPLACE = {
    "src/App.tsx": "297f0498e123eb7613da17a745e667c1",
    "src/pages/Home.tsx": "662e45f523b22d2f761431efd822d556",
    "src/components/home/GeomythologySection.tsx": "7b72404cc91f1a8e835a55cfbb846aa4",
}
NEW = ['src/components/home/CorpusStartSection.tsx', 'src/__tests__/home-heal.test.tsx']


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def crlf_style(raw: bytes) -> bool:
    return raw.count(b"\r\n") > raw.count(b"\n") // 2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "src" / "App.tsx").exists() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1].encode() not in pre.read_bytes():
        print("REFUSE: %s has no %s: apply that release first. Nothing written." % PREREQ); return 1
    if not PAYLOAD.exists():
        print("FAIL: the payload is not at %s. Nothing written." % PAYLOAD); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, want in REPLACE.items():
        p = root / rel
        if not p.exists():
            print("REFUSE: %s is not here. Nothing written." % rel); return 1
        raw = p.read_bytes()
        data = (PAYLOAD / rel).read_bytes()
        if lf(raw) == lf(data):
            print("skip %s (already %s)" % (rel, MARK)); continue
        if md5(lf(raw)) != want:
            print("REFUSE: %s is not the version main had (md5 %s, expected %s); it changed since. Nothing written."
                  % (rel, md5(lf(raw)), want)); return 1
        out = lf(data)
        if crlf_style(raw):
            out = out.replace(b"\n", b"\r\n")
        todo.append((rel, out))
    for rel in NEW:
        p = root / rel
        data = (PAYLOAD / rel).read_bytes()
        if p.exists():
            if lf(p.read_bytes()) == lf(data):
                print("skip %s (already there)" % rel); continue
            print("REFUSE: %s exists and differs from the payload. Nothing written." % rel); return 1
        todo.append((rel, data))
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo))
        for rel, _d in todo:
            print("  " + rel)
        return 0
    done = []
    try:
        for rel, data in todo:
            p = root / rel
            if p.exists():
                shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s): put back the .bak_%s_%s copies of %s" % (e, TAG, stamp, ", ".join(done))); return 1
    print("OK: %s. Then: npm run typecheck ; npx vitest run ; npm run build" % MARK)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
