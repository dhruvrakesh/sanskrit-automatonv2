#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_genealogy_heal_2026_11_10.py  (2026-11-10)  GENEALOGY_HEAL_2026_11_10

For the SRANGAM repo (run from D:\\srangam-42267, on main, with LOAD_CARDS_2026_11_09: 9a22055 or later). Asked on
10 Nov: "such a genealogy front end does not make sense for anybody. at least explain what you are putting in graphs
here ... we cant even get the genealogy of Kaunteya (Arjun) right". docs\\GENEALOGY_2026-11-10.md in the automaton repo.
  - src/lib/indexSite.ts: an epithet's persons (same_as, gloss; docs\\cloud\\C26), "by the names both entries give"
    (a join of the desk), the index notes (SOURCE_NOTE) and the page in plain words (GUIDE);
  - src/components/corpus/GenealogyGuide.tsx (new): "How to read this page", and the note that sends an epithet
    ("Kaunteya, the son of Kunti, = Arjuna") to the person it names;
  - src/pages/corpus/CorpusGenealogy.tsx: the note, the guide, Soerensen's pages counting the epics' verses (his
    Calcutta references cannot be read verse by verse), the "shared" join explained;
  - src/pages/corpus/CorpusGenealogies.tsx: the guide; a found epithet links to its person; "the longest fathers'
    lines", said to be one index's statements joined, not a dynasty;
  - src/__tests__/genealogy-heal.test.tsx (new).
Before C26 is pasted nothing comes with same_as and the pages are as before, with the guide.
The files travel in the automaton repository, docs\\srangam\\GENEALOGY_HEAL_2026-11-10\\. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_genheal_<date>. Re-running changes nothing. No database
change here (C26 is the automaton repo's docs\\cloud\\C26_index_aliases_2026-11-10.sql).

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_genealogy_heal_2026_11_10.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_genealogy_heal_2026_11_10.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, shutil
from pathlib import Path

MARK = "GENEALOGY_HEAL_2026_11_10"
PREREQ = ("src/hooks/useArticles.ts", "LOAD_CARDS_2026_11_09")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "GENEALOGY_HEAL_2026-11-10"
TAG = "genheal"

# path -> md5 of the LF text main has (9a22055)
REPLACE = {
    "src/lib/indexSite.ts": "23fde8faa0a7caa7c68f7c07bfcf3834",
    "src/pages/corpus/CorpusGenealogy.tsx": "12b058e65defa36b92853641950df735",
    "src/pages/corpus/CorpusGenealogies.tsx": "c2886e9f4c5a770949749e85e821f97e",
}
NEW = ["src/components/corpus/GenealogyGuide.tsx", "src/__tests__/genealogy-heal.test.tsx"]


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
