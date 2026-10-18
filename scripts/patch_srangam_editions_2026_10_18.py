#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_editions_2026_10_18.py  (2026-10-18)  EDITIONS_SITE_2026_10_18

For the SRANGAM repo (run from D:\\srangam-42267, on main, with TEST_WAIT_2026_10_16: a20b85ba or later). The
scholarly editions, open to everyone: /editions lists the static pages the automaton's scripts/publish_editions.py
writes into public/scholarly/ (with index.json):
  - src/lib/editions.ts, src/pages/Editions.tsx, src/__tests__/editions-page.test.tsx: new (4 tests);
  - src/App.tsx: the /editions route (lazy);
  - public/config/nav.config.json: "Editions" in the header, for everyone (the phone's menu too);
  - src/components/navigation/CorpusMenu.tsx: "Scholarly editions" in the Corpus menu;
  - public/sitemap.xml: /editions;
  - docs/RELIABILITY_AUDIT.md: Phase AK appended (invariant 58).
The files travel in the automaton repository, docs/srangam/EDITIONS_2026-10-18/. A replaced file is written only over
the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_editions_<date>. Re-running changes nothing. No database
change; nothing is deployed but what you commit.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_editions_2026_10_18.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_editions_2026_10_18.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "EDITIONS_SITE_2026_10_18"
PREREQ = ("vitest.config.ts", "TEST_WAIT_2026_10_16")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "EDITIONS_2026-10-18"
TAG = "editions"

# path -> md5 of the LF text main has (a20b85ba)
REPLACE = {
    "src/App.tsx": "2a03ed11d99a6e97e39626e2f960e970",
    "src/components/navigation/CorpusMenu.tsx": "f1fb92f273c000a30b64256e7fadbcca",
    "public/config/nav.config.json": "15ffdf0d319c81e90f43be649b404498",
    "public/sitemap.xml": "fa2282311687a30ac98508c000efc83f",
}
NEW = ["src/lib/editions.ts", "src/pages/Editions.tsx", "src/__tests__/editions-page.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "TEST_WAIT_2026_10_16"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAK.md"


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
        print("NOTE: %s is not in this checkout; Phase AK is not appended." % AUDIT)
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
