#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_load_l1_2026_10_09.py  (2026-10-09)  LOAD_L1_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORNER_C9_2026_10_09). Fewer questions
per page, as seen on the live site on 2026-10-09:
  - src/contexts/AuthContext.tsx: one role check (has_role + my_roles) per user at a time; the auth
    listener and getSession() asked it three times over on every page load. refreshRoles() always
    asks anew; signing out forgets the check on its way.
  - src/pages/corpus/CorpusImages.tsx: with no text chosen, the list is the first rows of the index, so
    corpus_reader_media is asked once, not twice, for the same rows.
  - src/__tests__/auth-role.test.tsx, src/__tests__/corpus-media.test.tsx: 4 new tests (each fails on
    the old code).
  - docs/RELIABILITY_AUDIT.md: Phase AA appended (invariants 34-35), after Phase Z.

The files travel in the automaton repository, docs/srangam/LOAD_L1_2026-10-09/. Each is written only
over the exact version CORNER_C9_2026_10_09 left (md5, line endings ignored), so a file changed since
is refused, never overwritten. All-or-nothing; backups .bak_load_l1_<date>; a replaced file keeps its
own line endings. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_l1_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_l1_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "LOAD_L1_2026_10_09"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "LOAD_L1_2026-10-09"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces)
FILES = [
    ('src/contexts/AuthContext.tsx', 'f4178011141fc506a2f0e23b53cb764f', '536da1528f195179509af5a509d00546'),
    ('src/pages/corpus/CorpusImages.tsx', '2b4c7560669488804ab247ece1031cab', '5581491bd40c67382dfcf7347fe6d026'),
    ('src/__tests__/auth-role.test.tsx', 'b7859fe76e9af565d26e42941edfb561', '5b59bbf59e523dfc70684777c5993315'),
    ('src/__tests__/corpus-media.test.tsx', '05e9c150995ddb98e970e38a147bc422', '7c25e13bf396a385b57dba997f95524e'),
]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_PART = ("_append/RELIABILITY_AUDIT.phaseAA.md", "2e5da1e2f8aa8888efe9b9bd9382c429")
AUDIT_NEEDS = "CORNER_C9_2026_10_09"


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
    if not Path("src/lib/corner.ts").exists():
        print("REFUSE: CORNER_C9_2026_10_09 must be applied first."); return 1
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
            problems.append("%s has no Phase Z (%s); apply the Corner first" % (AUDIT, AUDIT_NEEDS))
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
                bak = dest.with_name(dest.name + ".bak_load_l1_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_load_l1")
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
