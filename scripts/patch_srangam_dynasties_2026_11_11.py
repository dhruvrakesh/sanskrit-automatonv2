#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_dynasties_2026_11_11.py  (2026-11-11)  DYNASTIES_2026_11_11

For the SRANGAM repo (run from D:\\srangam-42267, on main, with GENEALOGY_HEAL_2026_11_10: 91f9efd or later). Asked on
10 and 11 Nov: the dynasties, the vamshas, "an API call thing". The automaton reads the Puranas' own genealogical books
verse by verse (scripts\\vamsa_read.py), joins their lines to the Purana Index's persons (scripts\\vamsa_join.py) and sends
them (index_sync.py, the table dynasties of docs\\cloud\\C28_index_dynasties_2026-11-11.sql). This kit:
  - supabase/functions/corpus-index/lib.ts: the table dynasties among the tables it takes (deploy it again, after C28);
  - src/lib/indexSite.ts: the dynasties' rows, their loader (corpus_reader_index_dynasties), what the index says of a
    step in words (INDEX_SAYS), the person's page, the counts in words, the page's guide (DYNASTY_GUIDE);
  - src/pages/corpus/CorpusDynasties.tsx (new): /corpus/genealogies/dynasties, for signed-in readers: the texts, the lines
    (the first opened), each step with its verse, its Sanskrit words, the index's word and a link to the person's page;
    a name found in the lines; before C28 "not switched on yet", before the first send "nothing sent yet";
  - src/App.tsx: the route; src/pages/corpus/CorpusGenealogies.tsx: a link to it under the guide;
  - src/__tests__/dynasties.test.tsx (new).
The files travel in the automaton repository, docs\\srangam\\DYNASTIES_2026-11-11\\. A replaced file is written only over
the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is refused,
never overwritten. All-or-nothing; backups .bak_dynasties_<date>. Re-running changes nothing. The database change is the
automaton repo's docs\\cloud\\C28_index_dynasties_2026-11-11.sql (paste it first).

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_dynasties_2026_11_11.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_dynasties_2026_11_11.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, shutil
from pathlib import Path

MARK = "DYNASTIES_2026_11_11"
PREREQ = ("src/lib/indexSite.ts", "GENEALOGY_HEAL_2026_11_10")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "DYNASTIES_2026-11-11"
TAG = "dynasties"

# path -> md5 of the LF text main has (91f9efd)
REPLACE = {
    "supabase/functions/corpus-index/lib.ts": "8ee370b43ae1a50974d050efca8ed8f0",
    "src/lib/indexSite.ts": "d1de946839ff903b569e973f71d8b4b3",
    "src/App.tsx": "ad8b1b30cad95b39e65406c1aa2bd166",
    "src/pages/corpus/CorpusGenealogies.tsx": "eaa20b35543051020bc5203594c3e81c",
}
NEW = ["src/pages/corpus/CorpusDynasties.tsx", "src/__tests__/dynasties.test.tsx"]


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
