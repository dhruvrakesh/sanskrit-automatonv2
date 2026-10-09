#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_state_learn_2026_10_09.py  (2026-10-09)  STATE_LEARN_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORNER_C9_2026_10_09 and
LOAD_L1_2026_10_09). Two things for researchers and editors:
  CORNER_STATE_S1_2026_10_09 - the Corner as it happens: when the desk's next round is due, each
    request's stages with their times and the desk's progress ("Drawing page 3 of 12"), the next steps of
    a finished request, a live refresh while a request is open, a notice when one finishes, and for
    editors the desk's report of the mirror and the pictures (chips and a Sync tab). New
    src/lib/cornerState.ts and src/components/corpus/CornerState.tsx (only /corpus/corner imports them);
    src/lib/corner.ts gains a link for story_mine's proposed episodes and exports four helpers.
  LEARN_T1_2026_10_09 - /corpus/learn and a Learn tab: 23 quests in five tracks, XP, levels, badges,
    "Your toolbox", "How the desk works", and the editors' Team panel.
Needs, in the database, docs/cloud/C10a_corner_state_2026-10-09.sql and docs/cloud/C11_learn_2026-10-09.sql
(automaton repo); before them the pages behave as before and say so quietly.

The files travel in the automaton repository, docs/srangam/STATE_LEARN_2026-10-09/, under the paths they
take in Srangam. This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file (corner.ts, CorpusCorner.tsx, CorpusNav.tsx) is written only over the exact version
    CORNER_C9_2026_10_09 left (md5, line endings ignored), so a file changed since is refused;
  - src/App.tsx gets two anchored insertions (a lazy page and a route), marker-idempotent;
  - docs/RELIABILITY_AUDIT.md gets Phase AB appended, marker-idempotent (after Phase AA);
  - every payload file is checked against its recorded md5 first.
All-or-nothing: everything is checked before anything is written. Backups .bak_statelearn_<date>.
A replaced or edited file keeps its own line endings; new files are LF. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_state_learn_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_state_learn_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "STATE_LEARN_2026_10_09"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "STATE_LEARN_2026-10-09"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/RESEARCHER_EXPERIENCE_2026-10-09.md', '130a4b6fc918f3b6c86b1b89f9f69217', None),
    ('src/__tests__/corpus-corner-state.test.tsx', 'd8a813f3e9a29fdf0d1bdeb3a346f5ff', None),
    ('src/__tests__/corpus-learn.test.tsx', '68be12e0c48a73f970b5fd1815dbff98', None),
    ('src/components/corpus/CornerState.tsx', 'be89d3499b6b8781eab8aacf8c352d7a', None),
    ('src/components/corpus/CorpusNav.tsx', '1b2eab684bd5231283beb354ab99cd9b', '369a3e40aa4023d99562ec11b3c36e3c'),
    ('src/lib/corner.ts', '17df1668f6052cdb029b36019c0bac88', '47c3da69f001c773c8884791c0d22159'),
    ('src/lib/cornerState.ts', '3ede74be00e1d7ef56b823be3ed05762', None),
    ('src/lib/learn.ts', 'f4503755d98466b76022ebdd448bed19', None),
    ('src/pages/corpus/CorpusCorner.tsx', '854ae8bf73c1dfb5f87f138d5ec0d137', 'cef1fb30dcaca2d0c4aea29cecdd708e'),
    ('src/pages/corpus/CorpusLearn.tsx', '1b69248e95ff95392b9136ec72cd96b4', None),
]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_PART = ("_append/RELIABILITY_AUDIT.phaseAB.md", "658c007795402e8dc38901d7fa7b6a87")
AUDIT_NEEDS = "LOAD_L1_2026_10_09"

APP = "src/App.tsx"
APP_EDITS = [
    ("lazy page",
     'const CorpusAnthology = lazy(() => import("./pages/corpus/CorpusAnthology"));\n',
     'const CorpusAnthology = lazy(() => import("./pages/corpus/CorpusAnthology"));\n'
     "// " + MARK + ": Learn, the quests that teach every tool\n"
     'const CorpusLearn = lazy(() => import("./pages/corpus/CorpusLearn"));\n'),
    ("route",
     '              <Route path="/corpus/anthologies/:collectionId" element={<CorpusAnthology />} />\n',
     '              <Route path="/corpus/anthologies/:collectionId" element={<CorpusAnthology />} />\n'
     '              {/* ' + MARK + ' */}\n'
     '              <Route path="/corpus/learn" element={<CorpusLearn />} />\n'),
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
    if not Path("src/lib/corner.ts").exists() or b"LOAD_L1_2026_10_09" not in Path("src/contexts/AuthContext.tsx").read_bytes():
        print("REFUSE: CORNER_C9_2026_10_09 and LOAD_L1_2026_10_09 must be applied first."); return 1
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
            problems.append("%s has no Phase AA (%s); apply LOAD_L1 first" % (AUDIT, AUDIT_NEEDS))
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
                bak = dest.with_name(dest.name + ".bak_statelearn_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_statelearn")
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
