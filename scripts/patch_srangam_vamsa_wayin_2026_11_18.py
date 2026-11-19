#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_vamsa_wayin_2026_11_18.py  (2026-11-18)  VAMSA_WAYIN_2026_11_18

For the SRANGAM repo (run from D:\\srangam-42267, on main, at DYNASTIES_WORKS_2026_11_18: 72e109b or later). P2c of
the path of 18 Nov: the way in by vamsa, the Suryavamsa and the Candravamsa across the texts (/corpus/genealogies/
vamsas), each dynasty from its founder, generation by generation, as each text names each king, each name linked to its
line on the Dynasties page, each generation with Dikshitar's person in the Purana Index and Raychaudhuri's claims the
site carries already.
  - src/pages/corpus/CorpusVamsas.tsx: new; the list light (corpus_reader_index_vamsas(NULL)), a dynasty's generations
    when opened (corpus_reader_index_vamsas(key)), kept 10 minutes; hovers for the verse and the scholars;
  - src/App.tsx: the route /corpus/genealogies/vamsas (lazy);
  - src/pages/corpus/CorpusDynasties.tsx: ?work=&line= opens that text and that line; a link to the vamsa page;
  - src/pages/corpus/CorpusGenealogies.tsx: a link to the vamsa page; the Dynasties link says seventeen texts;
  - src/lib/indexSite.ts: VAMSAS, loadVamsas(), the types, GEN_STATUS, dynastyLineHref(), the guide, the credit;
  - supabase/functions/corpus-index/lib.ts: the table vamsas (FN_VERSION i4);
  - src/__tests__/vamsas.test.tsx: new;
  - docs/RELIABILITY_AUDIT.md: Phase AU appended (invariant 71).
Needs the automaton's docs/cloud/C29_index_vamsas_2026-11-18.sql pasted first (until then the page says the vamsas are
not switched on yet); then corpus-index deployed again; then index_sync.py --dynasty-works every --apply.
The files travel in the automaton repository, docs/srangam/VAMSA_WAYIN_2026-11-18/. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_vamsawayin_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_vamsa_wayin_2026_11_18.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_vamsa_wayin_2026_11_18.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "VAMSA_WAYIN_2026_11_18"
PREREQ = ("src/lib/indexSite.ts", "DYNASTIES_WORKS_2026_11_18")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "VAMSA_WAYIN_2026-11-18"
TAG = "vamsawayin"

# path -> md5 of the LF text main has (72e109b, DYNASTIES_WORKS_2026_11_18)
REPLACE = {
    "supabase/functions/corpus-index/lib.ts": "cc1cd679cd83f8e50358933ba4f0e9c5",
    "src/lib/indexSite.ts": "ebdde48d75c0846aaa2d555b99a4d51f",
    "src/pages/corpus/CorpusDynasties.tsx": "8133a849f314db187eebe229e31036a8",
    "src/pages/corpus/CorpusGenealogies.tsx": "6ccfb118f5eca1a6854b5e9c8293ac8e",
    "src/App.tsx": "fd9bf118ea455e297d21aaf9e8a7d27f",
}
NEW = ["src/pages/corpus/CorpusVamsas.tsx", "src/__tests__/vamsas.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "DYNASTIES_WORKS_2026_11_18"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAU.md"


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
        print("REFUSE: %s has no %s (apply the kit DYNASTIES_WORKS first). Nothing written." % PREREQ); return 1
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
        print("NOTE: %s is not in this checkout; Phase AU is not appended." % AUDIT)
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
    print("Then: paste the automaton's docs\\cloud\\C29_index_vamsas_2026-11-18.sql (B1, the change, A1, A3) if not yet;")
    print("ask Lovable to deploy supabase/functions/corpus-index as it is; Publish; then, on the desk,")
    print("python scripts\\index_sync.py --dynasty-works every --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
