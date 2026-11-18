#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_dynasties_works_2026_11_18.py  (2026-11-18)  DYNASTIES_WORKS_2026_11_18

For the SRANGAM repo (run from D:\\srangam-42267, on main, at AI_GATEWAY_OFF_2026_11_17: eae2901 or later). P2b of
the path of 17 Nov, night: the Dynasties page (/corpus/genealogies/dynasties) asks for one work's lines at a time
instead of every work's at once, so that the desk may send the 17 works it reads (index_sync.py --dynasty-works every)
without a heavier page; it lists the 17 works by title and finds a name typed in plain letters.
  - src/pages/corpus/CorpusDynasties.tsx: loadDynasties(work) for the chosen work, kept 10 minutes; the texts' buttons
    from WORK_ORDER; "No dynasty of this text has been sent from the desk yet."; the find box by foldPlain;
  - src/lib/indexSite.ts: WORK_ORDER and WORK_TITLE of the 17 works; foldPlain() (for finding only);
  - src/__tests__/dynasties.test.tsx: the first call asks for vip4; "nothing sent" said of the text;
  - src/__tests__/dynasties-works.test.tsx: new;
  - docs/RELIABILITY_AUDIT.md: Phase AT appended (invariant 70).
Measured on 18 Nov: the page asked for 106 rows (123 kB) at once; it now asks for one work's (vip4 50 rows, 64 kB).
No database change; who may read is unchanged (the readers' gate).
The files travel in the automaton repository, docs/srangam/DYNASTIES_WORKS_2026-11-18/. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_dynworks_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_dynasties_works_2026_11_18.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_dynasties_works_2026_11_18.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "DYNASTIES_WORKS_2026_11_18"
PREREQ = ("src/lib/indexSite.ts", "export function loadDynasties(")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "DYNASTIES_WORKS_2026-11-18"
TAG = "dynworks"

# path -> md5 of the LF text main has (eae2901, AI_GATEWAY_OFF_2026_11_17)
REPLACE = {
    "src/lib/indexSite.ts": "4a9bd6101e59a96d417f021c3f602f21",
    "src/pages/corpus/CorpusDynasties.tsx": "3167c30b8f1f730f90f1e489355bb47c",
    "src/__tests__/dynasties.test.tsx": "2ecfb0c23df0b31f03396276ebbaa0f1",
}
NEW = ["src/__tests__/dynasties-works.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "AI_GATEWAY_OFF_2026_11_17"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAT.md"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def crlf_style(raw: bytes) -> bool:
    return raw.count(b"\r\n") > raw.count(b"\n") // 2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "src" / "lib").is_dir() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1].encode() not in pre.read_bytes():
        print("REFUSE: %s has no %s (the shared AI provider). Nothing written." % PREREQ); return 1
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
        print("NOTE: %s is not in this checkout; Phase AT is not appended." % AUDIT)
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
    print("Then Publish in Lovable; then, on the desk, index_sync.py --dynasty-works every --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
