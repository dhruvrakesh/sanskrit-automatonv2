#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_library_l1_2026_10_08.py  (2026-10-08)  CORPUS_LIBRARY_C6_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main, after READER_NAV_2026_10_08). Brings the
translation desk's library to the site for signed-in readers: /corpus as the Shelf (shelves,
titles, series, coverage, pipeline stages, stories, filter and sort), /corpus/stories (approved
stories; drafts for editors), /corpus/names (the names index and every passage that names one),
name chips in the corpus reader, and ?at=<page>.<passage> links. Needs
docs/cloud/C6_corpus_library_2026-10-08.sql in the database (pages leave out what is not there).

The files travel in the automaton repository, docs/srangam/LIBRARY_L1_2026-10-08/, under the paths
they take in Srangam. This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file is written only over the exact version it was made from (md5, line endings
    ignored), so a file changed since (by Lovable or by hand) is refused, never overwritten;
  - src/App.tsx gets two anchored insertions (two lazy pages, four routes), marker-idempotent;
  - every payload file is checked against its recorded md5 first.
All-or-nothing: everything is checked before anything is written. Backups .bak_library_<date>.
A replaced file keeps its own line endings; new files are LF. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_library_l1_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_library_l1_2026_10_08.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "CORPUS_LIBRARY_C6_2026_10_08"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "LIBRARY_L1_2026-10-08"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/CORPUS_LIBRARY_2026-10-08.md', 'ccabc153d679fc1d21666e0a544b572e', None),
    ('src/__tests__/corpus-library.test.tsx', 'eac1984c59be062e612117d30d680052', None),
    ('src/components/corpus/CorpusNav.tsx', 'b069d5c16d0bdae8de27c9816b9fc7d3', None),
    ('src/components/corpus/LibraryShelves.tsx', '16fe21e0bdb3e80b262575ad2e5e9ff4', None),
    ('src/components/reader/PassageNames.tsx', '04562b9828fcd15c69d20ba0f5dc2e0f', None),
    ('src/components/reader/ReaderToolbar.tsx', 'a8cdbbb1d3dd7d2f7bf16ee27ee4c6b8', 'c72c92c91a95e31d8a92731ee239f71e'),
    ('src/data/corpusShelf.json', 'f94c6f766492d72b5b31845731e84fbb', None),
    ('src/lib/corpusLibrary.ts', 'e9a4813b619e069a48a0572a29f52e21', None),
    ('src/lib/corpusMirror.ts', '0329b76353847cdbb7ca7bcd4c64d33f', '498360f50e06e4b3b5434fe59c58d355'),
    ('src/lib/readerPrefs.ts', '887470a9da5e7fef23398db17e344af8', 'f7d64f26c6c2c67ab95b7cdd205f24f2'),
    ('src/pages/corpus/CorpusDoc.tsx', '9570acce7573b62fd83b49fd21648011', '9f9588cc02c95c3f69ad1ae8cd7db175'),
    ('src/pages/corpus/CorpusHome.tsx', '1cc07cc0fcb812af415c6aa0fcc9dabb', 'd35cdf74dc8719833934e660a90a20f9'),
    ('src/pages/corpus/CorpusNames.tsx', 'afa6a764269d2da2a910ea299e223a66', None),
    ('src/pages/corpus/CorpusStories.tsx', 'dd5ee964fc56d4db2cf564023a552a67', None),
]

APP = "src/App.tsx"
APP_EDITS = [
    ("lazy pages",
     'const CorpusDoc = lazy(() => import("./pages/corpus/CorpusDoc"));\n',
     'const CorpusDoc = lazy(() => import("./pages/corpus/CorpusDoc"));\n'
     "// " + MARK + ": the library's stories and names\n"
     'const CorpusStories = lazy(() => import("./pages/corpus/CorpusStories"));\n'
     'const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));\n'),
    ("routes",
     '              <Route path="/corpus/:docCode" element={<CorpusDoc />} />\n',
     '              {/* ' + MARK + ' */}\n'
     '              <Route path="/corpus/stories" element={<CorpusStories />} />\n'
     '              <Route path="/corpus/stories/:docCode/:storyId" element={<CorpusStories />} />\n'
     '              <Route path="/corpus/names" element={<CorpusNames />} />\n'
     '              <Route path="/corpus/names/:canonical" element={<CorpusNames />} />\n'
     '              <Route path="/corpus/:docCode" element={<CorpusDoc />} />\n'),
]


def md5_lf(b: bytes) -> str:
    return hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest()


def nl_of(raw: bytes) -> bytes:
    return b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else b"\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path(APP).exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    if not PAYLOAD.is_dir():
        print("FAIL: the payload folder is missing: %s" % PAYLOAD); return 2
    if not Path("src/components/reader/PassageBlock.tsx").exists():
        print("REFUSE: READER_NAV_2026_10_08 is not applied (src/components/reader is missing)."); return 1
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

    app = Path(APP)
    raw = app.read_bytes()
    nl = nl_of(raw).decode()
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in text:
        skip.append(APP)
    else:
        out = text
        for name, anchor, new in APP_EDITS:
            c = out.count(anchor)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (APP, name, c)); continue
            out = out.replace(anchor, new, 1)
        todo.append((app, out.replace("\n", nl).encode("utf-8"), True))

    for rel in skip:
        print("skip %s (already this version)" % rel)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write (%d replaced or edited, %d new). Nothing written."
              % (len(todo), sum(1 for t in todo if t[2]), sum(1 for t in todo if not t[2])))
        return 0
    if not todo:
        print("Nothing to do."); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    try:
        for dest, data, replaced in todo:
            dest.parent.mkdir(parents=True, exist_ok=True)
            bak = None
            if replaced:
                bak = dest.with_name(dest.name + ".bak_library_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_library")
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
