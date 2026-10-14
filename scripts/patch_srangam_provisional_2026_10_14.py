#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_provisional_2026_10_14.py  (2026-10-14)  PROVISIONAL_EN_2026_10_14

For the SRANGAM repo (run from D:\\srangam-42267, on main, d1752d4 or later with READER_NAV_2026_10_08). English
made from a misread reading is marked (docs/PROVISIONAL_2026-10-14.md in the automaton repo):
  - src/lib/corpusDisplay.ts: madeFromMisread() (the automaton's own debris test: eight or more Devanagari signs and
    a Latin word among them, as scripts/redeem.py and repair_text.JUNK) and PROVISIONAL_NOTE;
  - src/components/reader/PassageBlock.tsx: a "provisional English" chip at the foot of such a passage, with its
    reason, and the same under "English" in About this passage. Both readers (/texts and /corpus) use it;
  - src/__tests__/reader-provisional.test.tsx: new (4 tests);
  - docs/RELIABILITY_AUDIT.md: Phase AF appended (invariants 50-51).
The files travel in the automaton repository, docs/srangam/PROVISIONAL_EN_2026-10-14/. Each replaced file is
written only over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file
changed since is refused, never overwritten. All-or-nothing; backups .bak_provisional_<date>. Re-running changes
nothing. No database change.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_provisional_2026_10_14.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_provisional_2026_10_14.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "PROVISIONAL_EN_2026_10_14"
PREREQ = ("src/lib/corpusDisplay.ts", "READER_NAV_2026_10_08")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "PROVISIONAL_EN_2026-10-14"

# path -> md5 of the LF text main has (d1752d4)
REPLACE = {
    "src/lib/corpusDisplay.ts": "ff69da779a977037035f153502a2d456",
    "src/components/reader/PassageBlock.tsx": "7d83b32b3707a2869aa247d2286f0142",
}
NEW = ["src/__tests__/reader-provisional.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "CORNER_UX_U1_2026_10_10"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAF.md"


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
        if not p.exists():
            print("REFUSE: %s not found. Nothing written." % rel); return 1
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
        print("NOTE: %s is not in this checkout; Phase AF is not appended." % AUDIT)
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
                shutil.copy2(p, p.with_name(p.name + ".bak_provisional_" + stamp))
            p.parent.mkdir(parents=True, exist_ok=True)
            t = p.with_name(p.name + ".tmp_provisional")
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_provisional_%s copies: %s" % (e, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
