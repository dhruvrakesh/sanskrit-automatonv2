#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_reader_nav_2026_10_08.py  (2026-10-08)  READER_NAV_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main, after AUTH_ROLE_2026_10_08). Brings in the
navigation and layout of the two readers, /texts/:docCode and /corpus/:docCode, and makes the edge
function search-corpus deployable (its own copy of the search-texts embedding helpers).

The files travel in the automaton repository, docs/srangam/READER_NAV_2026-10-08/, under the paths
they take in Srangam (reviewable, and released with the automaton). This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file is written only over the exact version it was made from (md5, line endings
    ignored), so a file changed since (by Lovable or by hand) is refused, never overwritten;
  - every payload file is checked against its recorded md5 first (a partial copy is refused).
All-or-nothing: everything is checked before anything is written. Backups .bak_readernav_<date>
beside each replaced file. Line endings: a replaced file keeps its own; new files are LF.
Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_reader_nav_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_reader_nav_2026_10_08.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "READER_NAV_2026_10_08"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "READER_NAV_2026-10-08"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/READER_NAV_2026-10-08.md', '2104d0d7921cca4d1af4cf786ee43554', None),
    ('src/__tests__/reader-nav.test.tsx', '0b38f69580f7724f98cbabae9f185d39', None),
    ('src/__tests__/search-corpus-embed.test.ts', 'a78180740be03a9372821a3ec573d9ed', None),
    ('src/__tests__/texts-reader-nav.test.tsx', '500017f147c0891c0e3a3af61757a389', None),
    ('src/components/reader/PassageBlock.tsx', '7d83b32b3707a2869aa247d2286f0142', None),
    ('src/components/reader/ReaderContents.tsx', 'f1d6ea543e34dd5b97e4f275bd1a7d1e', None),
    ('src/components/reader/ReaderToolbar.tsx', 'c72c92c91a95e31d8a92731ee239f71e', None),
    ('src/lib/corpusDisplay.ts', 'ff69da779a977037035f153502a2d456', 'd04ef134d8940829ec6ed9b02326ecfb'),
    ('src/lib/corpusMirror.ts', '498360f50e06e4b3b5434fe59c58d355', '8e6bf26d15e45a7d315b0399c2f8eb98'),
    ('src/lib/corpusTexts.ts', 'f2464d19a7e63f3cdf8a4c7cfe7b95ce', '4727f0ca92d61bd504ac582c8aaa5499'),
    ('src/lib/readerPrefs.ts', 'f7d64f26c6c2c67ab95b7cdd205f24f2', None),
    ('src/pages/corpus/CorpusDoc.tsx', '9f9588cc02c95c3f69ad1ae8cd7db175', 'c005eb25eaeeef6ce5fbac1ae3f1b432'),
    ('src/pages/corpus/CorpusHome.tsx', 'd35cdf74dc8719833934e660a90a20f9', 'cade7e196056b2ba43a5b49f5fda14ac'),
    ('src/pages/texts/TextReader.tsx', 'c9d3c4337e23b8a6444cf015882848ef', 'a422dc2341b4af5736f36f8772adfb9a'),
    ('supabase/functions/search-corpus/embed.ts', '8e512be6aa306db5004cece4b0775149', None),
    ('supabase/functions/search-corpus/index.ts', '83e1d00815f166c3231fc7da6594c256', '169ec581307038e54ae81f3109f87fad'),
]


def md5_lf(b: bytes) -> str:
    return hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest()


def nl_of(raw: bytes) -> bytes:
    return b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else b"\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    if not PAYLOAD.is_dir():
        print("FAIL: the payload folder is missing: %s" % PAYLOAD); return 2
    if "AUTH_ROLE_2026_10_08" not in Path("src/pages/Auth.tsx").read_text(encoding="utf-8"):
        print("REFUSE: src/pages/Auth.tsx lacks AUTH_ROLE_2026_10_08: apply that patch first."); return 1
    problems, todo, skip = [], [], []
    for rel, want, old in FILES:
        src = PAYLOAD / rel
        if not src.exists():
            problems.append("payload file missing: %s" % rel); continue
        data = src.read_bytes()
        if hashlib.md5(data).hexdigest() != want:
            problems.append("payload file differs from the one released: %s" % rel); continue
        dest = Path(rel)
        if dest.exists():
            raw = dest.read_bytes()
            have = md5_lf(raw)
            if have == want:
                skip.append(rel); continue
            if old is None:
                problems.append("%s already exists and is not this file (left alone)" % rel); continue
            if have != old:
                problems.append("%s has changed since this patch was made (md5 %s, expected %s)" % (rel, have, old)); continue
            if nl_of(raw) == b"\r\n":
                data = data.replace(b"\n", b"\r\n")
            todo.append((dest, data, True))
        else:
            if old is not None:
                problems.append("%s not found (it should exist and be replaced)" % rel); continue
            todo.append((dest, data, False))
    for rel in skip:
        print("skip %s (already this version)" % rel)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write (%d replaced, %d new). Nothing written."
              % (len(todo), sum(1 for t in todo if t[2]), sum(1 for t in todo if not t[2])))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    try:
        for dest, data, replaced in todo:
            dest.parent.mkdir(parents=True, exist_ok=True)
            bak = None
            if replaced:
                bak = dest.with_name(dest.name + ".bak_readernav_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_readernav")
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            done.append((dest, bak))
            print("%s %s" % ("replaced" if replaced else "added", dest.as_posix()))
    except Exception as e:
        print("FAIL while writing: %s: %s. Restoring." % (type(e).__name__, e))
        for dest, bak in done:
            if bak is not None:
                shutil.copy2(bak, dest)
            elif dest.exists():
                dest.unlink()
            print("restored %s" % dest)
        return 2
    print("Next: npm run typecheck ; npx vitest run ; npm run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
