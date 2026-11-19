#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_vamsa_findings_site_2026_11_19.py  (2026-11-19)  VAMSA_FINDINGS_SITE_2026_11_19

For the SRANGAM repo (run from D:\\srangam-42267, on main, at ADMIN_STATUS_2026_11_19: 31419c7 or later). Our findings
on the vamsa page: the findings a person approved on the desk (the automaton's R1), beside their dynasty, each source
with its words on hover; B. C. Law by page only (in copyright).
  - src/pages/corpus/CorpusVamsas.tsx: the count on a dynasty; "Our findings" above its generations when opened; an id
    on each generation for a finding to point at;
  - src/lib/indexSite.ts: the types, loadVamsaFindings (one read: corpus_reader_index_vamsa_findings), FINDING_KIND,
    findingCiteText, findingMade, dayOf; the guide's "Our findings";
  - src/__tests__/vamsa-findings.test.tsx: new;
  - docs/RELIABILITY_AUDIT.md: Phase AW appended (invariant 73).
Needs the automaton's docs/cloud/C31_vamsa_findings_2026-11-19.sql pasted for the findings to show (until then the page
shows nothing new). No edge function changes.
The files travel in the automaton repository, docs/srangam/VAMSA_FINDINGS_SITE_2026-11-19/. A replaced file is written
only over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since
is refused, never overwritten. All-or-nothing; backups .bak_findingssite_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_vamsa_findings_site_2026_11_19.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_vamsa_findings_site_2026_11_19.py"
Then: npm run typecheck ; npx vitest run src/__tests__/vamsa-findings.test.tsx src/__tests__/vamsas.test.tsx ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "VAMSA_FINDINGS_SITE_2026_11_19"
PREREQ = ("src/App.tsx", "ADMIN_STATUS_2026_11_19")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "VAMSA_FINDINGS_SITE_2026-11-19"
TAG = "findingssite"

# path -> md5 of the LF text main has (31419c7, ADMIN_STATUS_2026_11_19)
REPLACE = {
    "src/lib/indexSite.ts": "1c74a270161fe134f9fe00efd9e62792",
    "src/pages/corpus/CorpusVamsas.tsx": "5946d46e4eb6c2866fb076eae81b4d19",
}
NEW = ["src/__tests__/vamsa-findings.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "ADMIN_STATUS_2026_11_19"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAW.md"


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
        print("REFUSE: %s has no %s (apply the kit ADMIN_STATUS first). Nothing written." % PREREQ); return 1
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
        print("NOTE: %s is not in this checkout; Phase AW is not appended." % AUDIT)
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
    print("\nNext: npm run typecheck ; npx vitest run src/__tests__/vamsa-findings.test.tsx src/__tests__/vamsas.test.tsx ;"
          " npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    print("Then: paste the automaton's docs\\cloud\\C31_vamsa_findings_2026-11-19.sql (B1, the change, A1) if not yet;")
    print("Publish; then python scripts\\index_sync.py --dynasty-works every --apply on the desk, and open")
    print("/corpus/genealogies/vamsas signed in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
