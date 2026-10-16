#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_ornament_2026_10_16.py  (2026-10-16)  ORNAMENT_2026_10_16

For the SRANGAM repo (run from D:\\srangam-42267, on main, with CLASSIFY_HINDI_2026_10_16: the frontmatter fold,
a77740d or later). Lovable found clean verses labelled "provisional English": verses printed next to an ornament. The
vision OCR writes a printed rule as a line of its own, "<decorative line>"; the reader hides it and draws a rule, but
the provisional test read the marker's words as the scanner's Latin-letter debris. The automaton's own tests are
mended in the same release (scripts/patch_ornament_2026_10_16.py):
  - src/lib/corpusDisplay.ts: madeFromMisread() sets aside the lines that are only the marker (splitDecoration);
    the marker inside a line, and any other Latin word, is debris as before;
  - src/__tests__/reader-ornament.test.tsx: new (4 tests);
  - docs/RELIABILITY_AUDIT.md: Phase AI appended (invariant 56).
The files travel in the automaton repository, docs/srangam/ORNAMENT_2026-10-16/. The replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_ornament_<date>. Re-running changes nothing. No database
change.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_ornament_2026_10_16.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_ornament_2026_10_16.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "ORNAMENT_2026_10_16"
PREREQ = ("src/components/reader/PassageBlock.tsx", "CLASSIFY_HINDI_2026_10_16")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "ORNAMENT_2026-10-16"
TAG = "ornament"

# path -> md5 of the LF text main has (a77740d)
REPLACE = {
    "src/lib/corpusDisplay.ts": "c7b6ff86d1fc329fb896f9e3aff23cea",
}
NEW = ["src/__tests__/reader-ornament.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "CLASSIFY_HINDI_2026_10_16"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAI.md"


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
        print("NOTE: %s is not in this checkout; Phase AI is not appended." % AUDIT)
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
