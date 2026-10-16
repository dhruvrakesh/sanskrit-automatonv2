#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_frontmatter_2026_10_16.py  (2026-10-16)  CLASSIFY_HINDI_2026_10_16

For the SRANGAM repo (run from D:\\srangam-42267, on main, 4c37d48 or later with READER_SOURCES_2026_10_14). The
automaton's classification stage now tags an edition's own Hindi (the editor's translation under each verse, his
preface) 'frontmatter', so it is not translated (docs/CLASSIFY_HINDI_2026-10-16.md in the automaton repo). The
corpus reader showed such a passage in full, with "Not translated yet." under it:
  - src/components/reader/PassageBlock.tsx: a passage typed frontmatter is folded like scanner noise ("The
    edition's own matter, not the Sanskrit.", Show it), and never says "Not translated yet."; its note says what it
    is. A verse and scanner noise are as before;
  - src/__tests__/reader-frontmatter.test.tsx: new (2 tests);
  - docs/RELIABILITY_AUDIT.md: Phase AH appended (invariants 54-55).
The files travel in the automaton repository, docs/srangam/FRONTMATTER_FOLD_2026-10-16/. The replaced file is
written only over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file
changed since is refused, never overwritten. All-or-nothing; backups .bak_frontmatter_<date>. Re-running changes
nothing. No database change.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_frontmatter_2026_10_16.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_frontmatter_2026_10_16.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "CLASSIFY_HINDI_2026_10_16"
PREREQ = ("src/components/reader/PassageBlock.tsx", "READER_SOURCES_2026_10_14")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "FRONTMATTER_FOLD_2026-10-16"
TAG = "frontmatter"

# path -> md5 of the LF text main has (4c37d48)
REPLACE = {
    "src/components/reader/PassageBlock.tsx": "c74ecf176e16d2be16844444a6f2ec88",
}
NEW = ["src/__tests__/reader-frontmatter.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "READER_SOURCES_2026_10_14"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAH.md"


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
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, want in REPLACE.items():
        p = root / rel
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
    a = root / AUDIT
    if a.exists():
        raw = a.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (AUDIT, MARK))
        elif AUDIT_NEEDS.encode() not in raw:
            print("REFUSE: %s has no %s phase (apply that release first). Nothing written." % (AUDIT, AUDIT_NEEDS)); return 1
        else:
            text = (PAYLOAD / AUDIT_APPEND).read_bytes()
            nl = b"\r\n" if crlf_style(raw) else b"\n"
            body = raw if raw.endswith(b"\n") else raw + nl
            todo.append((AUDIT, body + nl + lf(text).replace(b"\n", nl)))
    else:
        print("NOTE: %s is not in this checkout; Phase AH is not appended." % AUDIT)
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
            t = p.with_name(p.name + ".tmp_" + TAG)
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
