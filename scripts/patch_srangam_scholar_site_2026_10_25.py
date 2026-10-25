#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_scholar_site_2026_10_25.py  (2026-10-25)  SCHOLAR_SITE_2026_10_25

For the SRANGAM repo (run from D:\\srangam-42267, on main, with NAME_LINKS_SITE_2026_10_23: 341cf7f or later). The
scholarly English as the desk has it (asked on 25 Oct: "why isnt scholary and prose available on srangam?"), from the
mirror's own rows, read through docs/cloud/C22 in the automaton repo (corpus_reader_scholar_docs,
corpus_reader_scholar_prose):
  - src/lib/scholarSite.ts, src/pages/corpus/CorpusScholarly.tsx, src/pages/corpus/CorpusProse.tsx,
    src/__tests__/scholar-site.test.tsx: new;
  - src/App.tsx: /corpus/scholarly and /corpus/:docCode/prose;
  - src/components/corpus/CorpusNav.tsx, src/components/navigation/CorpusMenu.tsx: "Scholarly English";
  - src/pages/corpus/CorpusDoc.tsx: "read it as prose" beside the header's count;
  - src/lib/editions.ts, src/pages/Editions.tsx: an edition's own prose page, when the index names it (and the
    typecheck error at Editions.tsx's r.error, there since EDITIONS_SITE_2026_10_18, mended);
  - docs/RELIABILITY_AUDIT.md: Phase AP appended (invariant 65).
Until C22 is pasted both new pages say so; the reader and the editions are as before.
The files travel in the automaton repository, docs/srangam/SCHOLAR_SITE_2026-10-25/. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_scholarsite_<date>. Re-running changes nothing. No
database change here; nothing is deployed but what you commit.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_scholar_site_2026_10_25.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_scholar_site_2026_10_25.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "SCHOLAR_SITE_2026_10_25"
PREREQ = ("src/lib/corpusLibrary.ts", "NAME_LINKS_SITE_2026_10_23")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "SCHOLAR_SITE_2026-10-25"
TAG = "scholarsite"

# path -> md5 of the LF text main has (341cf7f)
REPLACE = {
    "src/App.tsx": "5ca1af806923f63c762e558ce83ec2d1",
    "src/pages/corpus/CorpusDoc.tsx": "4b5e181252732ac70df91e9b7f4ab44a",
    "src/components/corpus/CorpusNav.tsx": "1b2eab684bd5231283beb354ab99cd9b",
    "src/components/navigation/CorpusMenu.tsx": "09fc320dc6a1f4899718d2c22ff6ae36",
    "src/lib/editions.ts": "c09089661a2f08660701dfbf2e7261cd",
    "src/pages/Editions.tsx": "1a735b9ea43cec21def41c75ad6df7c8",
}
NEW = ["src/lib/scholarSite.ts", "src/pages/corpus/CorpusScholarly.tsx", "src/pages/corpus/CorpusProse.tsx",
       "src/__tests__/scholar-site.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "NAME_LINKS_SITE_2026_10_23"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAP.md"


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
        print("NOTE: %s is not in this checkout; Phase AP is not appended." % AUDIT)
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
