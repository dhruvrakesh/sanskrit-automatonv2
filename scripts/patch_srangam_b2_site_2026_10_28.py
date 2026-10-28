#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_b2_site_2026_10_28.py  (2026-10-28)  B2_SITE_2026_10_28, X1C_SITE_2026_10_28

For the SRANGAM repo (run from D:\\srangam-42267, on main, with INDEX_SITE_2026_10_25: fdd80b5 or later). Asked on
28 Oct: "B2 (Raychaudhuri's view of each step), then searching the scholarly English (X1c)". docs/B2_AND_X1C_2026-10-28.md
in the automaton repo; the database side is docs/cloud/C23_index_claims_2026-10-28.sql (the historian's claims beside
the genealogies) and docs/cloud/C24_scholar_search_2026-10-28.sql (a search in the scholarly English):
  - src/lib/indexSite.ts: the claims' types, the historian's chip, a step's strength, the line's counts;
  - src/components/corpus/ScholarClaims.tsx (new): a claim with the book's words, page, stance, ties and citations;
  - src/pages/corpus/CorpusGenealogy.tsx: the historian's view in the evidence; a strip over the line that shows each
    step by what it rests on and chooses one; "In our corpus" (our names on the line, how often our texts name the
    person, the names named with it, what the historians say of it); the credits name the work apart;
  - src/pages/corpus/CorpusGenealogies.tsx, src/components/corpus/IndexCredits.tsx: the work, its count, its credit;
  - src/components/corpus/InTheIndexes.tsx: "What the historians say" on a name's page;
  - src/lib/scholarSite.ts, src/components/corpus/ScholarSearch.tsx (new), src/pages/corpus/CorpusHome.tsx (a third
    way: "In the scholarly English"), src/pages/corpus/CorpusScholarly.tsx: the search in the scholarly English;
  - supabase/functions/corpus-index/{index.ts, lib.ts}: the table "claims" (the same as docs/cloud/C23_corpus-index);
  - src/__tests__/b2-site.test.tsx (new); docs/RELIABILITY_AUDIT.md: Phase AR appended (invariants 67, 68).
Until C23 is pasted the genealogies are as before; until C24 the search says it is not switched on.
The files travel in the automaton repository, docs/srangam/B2_SITE_2026-10-28/. A replaced file is written only over
the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_b2site_<date>. Re-running changes nothing. No database
change here; nothing is deployed but what you commit (and corpus-index, when you ask Lovable to deploy it).

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_b2_site_2026_10_28.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_b2_site_2026_10_28.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "B2_SITE_2026_10_28"
PREREQ = ("src/lib/scholarSite.ts", "SCHOLAR_SITE_2026_10_25")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "B2_SITE_2026-10-28"
TAG = "b2site"

# path -> md5 of the LF text main has (fdd80b5, INDEX_SITE_2026_10_25)
REPLACE = {
    "src/lib/indexSite.ts": "971d9f5538df520d256cbe6f17f6b363",
    "src/pages/corpus/CorpusGenealogy.tsx": "265a576b979730ffa9a111a042f30506",
    "src/pages/corpus/CorpusGenealogies.tsx": "7ec0cb013262d36c9c871adf219d7f9a",
    "src/components/corpus/InTheIndexes.tsx": "992f92b124fe1c933962b360e136364d",
    "src/components/corpus/IndexCredits.tsx": "cc835703845dce42d2b8c2a1af139f62",
    "src/lib/scholarSite.ts": "039e2ccdb1b44f8c62592835faa337dc",
    "src/pages/corpus/CorpusHome.tsx": "c55426aab71d92810ec283a5097f93a0",
    "src/pages/corpus/CorpusScholarly.tsx": "e08a0967bda145ba2cf21e9b8ee819ef",
    "supabase/functions/corpus-index/lib.ts": "3edeaf811fab2ba383591fd5505dfb8e",
    "supabase/functions/corpus-index/index.ts": "a5b361aabf293bf029925c92d97af372",
}
NEW = ["src/components/corpus/ScholarClaims.tsx", "src/components/corpus/ScholarSearch.tsx",
       "src/__tests__/b2-site.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "INDEX_SITE_2026_10_25"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAR.md"


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
    if not PAYLOAD.exists():
        print("FAIL: the payload %s is not here (release the automaton repo first)." % PAYLOAD); return 2
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
        print("NOTE: %s is not in this checkout; Phase AR is not appended." % AUDIT)
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
