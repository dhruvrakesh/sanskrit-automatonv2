#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_corner_2026_10_09.py  (2026-10-09)  CORNER_C9_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORPUS_MEDIA_C8_2026_10_09). The
Researchers' Corner: /corpus/corner (ask the desk for stories, pictures and graphic novels; my
requests; the editors' queue; anthologies; the super admin's settings), /corpus/anthologies/new and
/corpus/anthologies/:id (the builder, the reader, print or save as PDF, publish), the "Ask the desk"
bar under stories, pictures and graphic novels (only for those who may ask), the Corner tab, and the
edge function supabase/functions/corpus-desk (the desk's signed door; the browser never calls it).
Needs docs/cloud/C9 in the database and corpus-desk deployed; before them the Corner says it is not
available yet and the bars do not appear.

The files travel in the automaton repository, docs/srangam/CORNER_C9_2026-10-09/, under the paths they
take in Srangam. This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file (CorpusNav, CorpusStories, CorpusImages, CorpusNovels) is written only over the
    exact version CORPUS_MEDIA_C8_2026_10_09 left (md5, line endings ignored), so a file changed
    since is refused, never overwritten;
  - src/App.tsx gets two anchored insertions (two lazy pages, three routes), marker-idempotent;
  - docs/RELIABILITY_AUDIT.md gets Phase Z appended, marker-idempotent (after Phase Y);
  - every payload file is checked against its recorded md5 first.
All-or-nothing: everything is checked before anything is written. Backups .bak_corner_<date>.
A replaced or edited file keeps its own line endings; new files are LF. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_corner_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_corner_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "CORNER_C9_2026_10_09"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "CORNER_C9_2026-10-09"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/RESEARCHERS_CORNER_2026-10-09.md', '88b901003e0dee8de6df020e3335bc4a', None),
    ('src/__tests__/corpus-corner.test.tsx', 'd0ce63d6f25f8234fdd4ba53d724f305', None),
    ('src/components/corpus/CornerParts.tsx', '24e1c3ad6a7502acf64038f7b4adbf59', None),
    ('src/components/corpus/CorpusNav.tsx', '369a3e40aa4023d99562ec11b3c36e3c', '60cfd54dec972202828f45ad640343e0'),
    ('src/components/corpus/DeskActions.tsx', 'edbe32ca8a6c43fe6f9c1a66c7412e41', None),
    ('src/lib/corner.ts', '47c3da69f001c773c8884791c0d22159', None),
    ('src/pages/corpus/CorpusAnthology.tsx', '099eb43a9b156b21ae05c935ad4d1714', None),
    ('src/pages/corpus/CorpusCorner.tsx', 'cef1fb30dcaca2d0c4aea29cecdd708e', None),
    ('src/pages/corpus/CorpusImages.tsx', '5581491bd40c67382dfcf7347fe6d026', 'eb6445a273faebe2742a3e24a0dfda41'),
    ('src/pages/corpus/CorpusNovels.tsx', '956b1bc610d740789eecd6b3f6579d62', 'e1152819537794e22f2fdbf7e45228b8'),
    ('src/pages/corpus/CorpusStories.tsx', '792899376417e4038677de20ab92b0bf', '83a2388fb165fb9f3ed1399203e650f6'),
    ('supabase/functions/corpus-desk/index.ts', 'ba99746e05358bc9283cb96a24ddd849', None),
    ('supabase/functions/corpus-desk/lib.ts', 'f421709c63bf2b6dd9ed91b791dddb76', None),
]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_PART = ("_append/RELIABILITY_AUDIT.phaseZ.md", "122fd1fb6aa50e94c7f9457fe31d9eec")
AUDIT_NEEDS = "CORPUS_MEDIA_C8_2026_10_09"

APP = "src/App.tsx"
APP_EDITS = [
    ("lazy pages",
     'const CorpusNovels = lazy(() => import("./pages/corpus/CorpusNovels"));\n',
     'const CorpusNovels = lazy(() => import("./pages/corpus/CorpusNovels"));\n'
     "// " + MARK + ": the Researchers' Corner and its anthologies\n"
     'const CorpusCorner = lazy(() => import("./pages/corpus/CorpusCorner"));\n'
     'const CorpusAnthology = lazy(() => import("./pages/corpus/CorpusAnthology"));\n'),
    ("routes",
     '              <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />\n',
     '              <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />\n'
     '              {/* ' + MARK + ' */}\n'
     '              <Route path="/corpus/corner" element={<CorpusCorner />} />\n'
     '              <Route path="/corpus/anthologies/new" element={<CorpusAnthology />} />\n'
     '              <Route path="/corpus/anthologies/:collectionId" element={<CorpusAnthology />} />\n'),
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
    if not Path("src/lib/corpusMedia.ts").exists() or not Path("src/lib/rbac.ts").exists():
        print("REFUSE: CORPUS_MEDIA_C8_2026_10_09 and RBAC_RESEARCHERS_2026_10_08 must be applied first."); return 1
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

    part = PAYLOAD / AUDIT_PART[0]
    audit = Path(AUDIT)
    if not part.exists() or hashlib.md5(part.read_bytes()).hexdigest() != AUDIT_PART[1]:
        problems.append("payload file missing or changed: %s" % AUDIT_PART[0])
    elif not audit.exists():
        problems.append("%s not found" % AUDIT)
    else:
        raw = audit.read_bytes()
        if MARK.encode() in raw:
            skip.append(AUDIT)
        elif AUDIT_NEEDS.encode() not in raw:
            problems.append("%s has no Phase X (%s); apply the RBAC docs first" % (AUDIT, AUDIT_NEEDS))
        else:
            anl = nl_of(raw)
            sep = b"" if raw.endswith(b"\n") else anl
            todo.append((audit, raw + sep + part.read_bytes().replace(b"\n", anl), True))

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
                bak = dest.with_name(dest.name + ".bak_corner_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_corner")
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
