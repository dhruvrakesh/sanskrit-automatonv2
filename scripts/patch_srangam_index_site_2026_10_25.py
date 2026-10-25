#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_index_site_2026_10_25.py  (2026-10-25)  INDEX_SITE_2026_10_25

For the SRANGAM repo (run from D:\\srangam-42267, on main, with SCHOLAR_SITE_2026_10_25: 9cef3f6 or later). The
genealogies of the three indexes on the site (asked on 25 Oct: "i thought ill see the geneaologies of kings on a react
front end and our carefully built db mirrored from local to supabase!"), read from the mirror through docs/cloud/C21
in the automaton repo, sent there by the PC's scripts/index_sync.py through the new edge function corpus-index:
  - supabase/functions/corpus-index/index.ts, lib.ts: new (the desk's signed door; deploy it as it is);
  - src/lib/indexSite.ts, src/pages/corpus/CorpusGenealogies.tsx, src/pages/corpus/CorpusGenealogy.tsx,
    src/components/corpus/IndexCredits.tsx, src/components/corpus/InTheIndexes.tsx, src/__tests__/index-site.test.tsx:
    new;
  - src/App.tsx: /corpus/genealogies and /corpus/genealogies/:source/:entry;
  - src/components/corpus/CorpusNav.tsx, src/components/navigation/CorpusMenu.tsx: "Genealogies";
  - src/pages/corpus/CorpusNames.tsx: "In the indexes" on a name's page;
  - docs/RELIABILITY_AUDIT.md: Phase AQ appended (invariant 66).
Until C21 is pasted both new pages say so and the names page is as before.
The files travel in the automaton repository, docs/srangam/INDEX_SITE_2026-10-25/. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_indexsite_<date>. Re-running changes nothing. No database
change here; nothing is deployed but what you commit (and corpus-index when Lovable is asked to deploy it).

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_index_site_2026_10_25.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_index_site_2026_10_25.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "INDEX_SITE_2026_10_25"
PREREQ = ("src/lib/scholarSite.ts", "SCHOLAR_SITE_2026_10_25")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "INDEX_SITE_2026-10-25"
TAG = "indexsite"

# path -> md5 of the LF text main has (9cef3f6)
REPLACE = {
    "src/App.tsx": "f6393fb720aebf27eebdc81076403074",
    "src/components/corpus/CorpusNav.tsx": "804fefbb5ecfea762ed9db00ab95cd8c",
    "src/components/navigation/CorpusMenu.tsx": "a79b40923620975f11fda1ef3ed56f3f",
    "src/pages/corpus/CorpusNames.tsx": "1e1a7e0b7910be61c19247150d1e1dbf",
}
NEW = ["supabase/functions/corpus-index/index.ts", "supabase/functions/corpus-index/lib.ts",
       "src/lib/indexSite.ts", "src/pages/corpus/CorpusGenealogies.tsx", "src/pages/corpus/CorpusGenealogy.tsx",
       "src/components/corpus/IndexCredits.tsx", "src/components/corpus/InTheIndexes.tsx",
       "src/__tests__/index-site.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "SCHOLAR_SITE_2026_10_25"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAQ.md"


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
        print("NOTE: %s is not in this checkout; Phase AQ is not appended." % AUDIT)
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
