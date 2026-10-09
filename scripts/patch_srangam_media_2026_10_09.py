#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_media_2026_10_09.py  (2026-10-09)  CORPUS_MEDIA_C8_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after RBAC_RESEARCHERS_2026_10_08). The
pictures and graphic novels of the working corpus: /corpus/images (the gallery, one picture by
?pic=), /corpus/novels and /corpus/novels/:id (the reader: cast, pages, captions in English and
Hindi with linked citations, speech, the scene asked for, the check), the story's picture and its
novel link at the head of each story, the Pictures and Graphic novels tabs, and the edge function
supabase/functions/corpus-media (pictures from the private Drive folder, as the reader). Needs
docs/cloud/C8 in the database and corpus-media deployed; before them the two pages say the
pictures are not available yet and the stories read as before.

The files travel in the automaton repository, docs/srangam/MEDIA_M1_2026-10-09/, under the paths they
take in Srangam. This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file (CorpusNav.tsx, CorpusStories.tsx) is written only over the exact version it was
    made from (md5, line endings ignored), so a file changed since is refused, never overwritten;
  - src/App.tsx gets two anchored insertions (two lazy pages, three routes), marker-idempotent;
  - docs/RELIABILITY_AUDIT.md gets Phase Y appended, marker-idempotent (after Phase X);
  - every payload file is checked against its recorded md5 first;
  - supabase/functions/_shared/google-drive.ts must be the one whose uploadToDrive can skip sharing.
All-or-nothing: everything is checked before anything is written. Backups .bak_media_<date>.
A replaced or edited file keeps its own line endings; new files are LF. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_media_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_media_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "CORPUS_MEDIA_C8_2026_10_09"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "MEDIA_M1_2026-10-09"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/CORPUS_MEDIA_2026-10-09.md', '0362956dd8b7793d2452021ff7b6be66', None),
    ('src/__tests__/corpus-media.test.tsx', '7c25e13bf396a385b57dba997f95524e', None),
    ('src/components/corpus/CorpusImage.tsx', '9d47f3c4b4f39752dc3449af4d7ff1c4', None),
    ('src/components/corpus/CorpusNav.tsx', '60cfd54dec972202828f45ad640343e0', 'b069d5c16d0bdae8de27c9816b9fc7d3'),
    ('src/components/corpus/MediaParts.tsx', '9264cc508e0cdb93c5dd32204b4574fb', None),
    ('src/components/corpus/StoryPlate.tsx', '31af37ff372ab7fa80de0ffe68fd4939', None),
    ('src/lib/corpusMedia.ts', 'e22dcac398c4c0efc030e43a3354e412', None),
    ('src/pages/corpus/CorpusImages.tsx', 'eb6445a273faebe2742a3e24a0dfda41', None),
    ('src/pages/corpus/CorpusNovels.tsx', 'e1152819537794e22f2fdbf7e45228b8', None),
    ('src/pages/corpus/CorpusStories.tsx', '83a2388fb165fb9f3ed1399203e650f6', 'dd5ee964fc56d4db2cf564023a552a67'),
    ('supabase/functions/corpus-media/index.ts', '4182054aded87d2e5f099dcc1933fb7e', None),
    ('supabase/functions/corpus-media/lib.ts', 'f8b1e5af2facf687420999ed15e6f854', None),
]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_PART = ("_append/RELIABILITY_AUDIT.phaseY.md", "13cbd1a4cfbd24e03ed8fcd02846316b")
AUDIT_NEEDS = "RBAC_RESEARCHERS_2026_10_08"
DRIVE = "supabase/functions/_shared/google-drive.ts"
DRIVE_NEEDS = ("export async function uploadToDrive", "opts.shareAnyone !== false", "export function loadServiceAccount",
               "export async function getDriveAccessToken")

APP = "src/App.tsx"
APP_EDITS = [
    ("lazy pages",
     'const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));\n',
     'const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));\n'
     "// " + MARK + ": the pictures and the graphic novels\n"
     'const CorpusImages = lazy(() => import("./pages/corpus/CorpusImages"));\n'
     'const CorpusNovels = lazy(() => import("./pages/corpus/CorpusNovels"));\n'),
    ("routes",
     '              <Route path="/corpus/names/:canonical" element={<CorpusNames />} />\n',
     '              <Route path="/corpus/names/:canonical" element={<CorpusNames />} />\n'
     '              {/* ' + MARK + ' */}\n'
     '              <Route path="/corpus/images" element={<CorpusImages />} />\n'
     '              <Route path="/corpus/novels" element={<CorpusNovels />} />\n'
     '              <Route path="/corpus/novels/:novelId" element={<CorpusNovels />} />\n'),
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
    if not Path("src/lib/corpusLibrary.ts").exists() or not Path("src/lib/rbac.ts").exists():
        print("REFUSE: CORPUS_LIBRARY_C6_2026_10_08 and RBAC_RESEARCHERS_2026_10_08 must be applied first."); return 1
    problems, todo, skip = [], [], []

    d = Path(DRIVE)
    if not d.exists():
        problems.append("%s is missing (corpus-media imports it)" % DRIVE)
    else:
        txt = d.read_text(encoding="utf-8", errors="replace")
        for need in DRIVE_NEEDS:
            if need not in txt:
                problems.append("%s no longer has %r (corpus-media relies on it)" % (DRIVE, need))

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
                bak = dest.with_name(dest.name + ".bak_media_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_media")
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
