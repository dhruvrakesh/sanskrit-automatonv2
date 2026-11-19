#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs124_2026_11_19.py  (2026-11-19)  DOCS124_2026_11_19

19 Nov: VAMSA_WAYIN and DOCS123 released (31da6d5); C29 pasted and checked; the Srangam kit pushed (cc32c10) and
published; the send waits for corpus-index to be deployed again; R1 built (scripts\\vamsa_findings.py); Lovable's
security scan read against C27. Adds:

  docs/ASKS_2026-10-22.md    section 36: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 58
  RUNBOOK.md                 "19 Nov": the order of the steps
  ARCHITECTURE.md            the genealogies' road: step 7, our findings (R1); what is not yet on it

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs124_<date> copies.

  python scripts\\patch_docs124_2026_11_19.py --check
  python scripts\\patch_docs124_2026_11_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS124_2026_11_19'
TAG = 'docs124'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'ARCHITECTURE.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS123_2026_11_18', 'docs/STATE_2026-10-18.md': 'DOCS123_2026_11_18', 'RUNBOOK.md': 'DOCS123_2026_11_18', 'ARCHITECTURE.md': 'DOCS123_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, 'The credit is read with python scripts\\claude_engine.py --credit before each.\n',
     'The credit is read with python scripts\\claude_engine.py --credit before each.\n\n## 36. 19 Nov: the vamsas on the site but for one deploy; R1 built; Lovable\'s security scan (DOCS124_2026_11_19)\n\nAsked on 19 Nov, 10:04: "proceed", with four CSV exports of the Lovable Cloud SQL editor (09:00 to 10:03) and eight\nscreens (09:00 to 10:01). Read, read only: sections 18, 34 and 35 here; docs\\cloud\\C27_spatial_ref_sys_2026-11-11.sql;\ndocs\\PEOPLES_FINDINGS_2026-11-11.md; data\\shelf\\peoples_index.json, claims.db and kin.db (immutable); D:\\backups\\\ncontext_20261118.db (immutable; the live database was not opened); Srangam\'s TagManagement.tsx and corpus-index.\n\n**Done in full? No.** Done: VAMSA_WAYIN and DOCS123 released (31da6d5), C29 pasted and checked, the Srangam kit pushed\n(cc32c10) and published. Left: corpus-index deployed again (the send waits for it), R1\'s trial and a person\'s review,\nthe findings on the vamsa page (C30, after approvals), P3, P4.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 19 Nov | The release of VAMSA_WAYIN and DOCS123 | Done by you: 31da6d5 pushed (97b9fa2..31da6d5, 23 files, 3,464 insertions, 9 deletions; "verified: origin/main == local HEAD (31da6d5c)") | Done |\n| 19 Nov | C29 in the Lovable Cloud SQL editor | Your exports: B1 at 09:00:28 true, true, false, false; the change pasted ("Query succeeded"); A1 at 09:01:21 true, true, true, true, true, 0 vamsa rows, 517 dynasty rows; A3 at 09:01:51 anon reads false, signed-in reads true, signed-in writes false, anon manifest false. Set-Clipboard failed on the PC ("Requested Clipboard operation did not succeed"); the block was pasted another way | Done |\n| 19 Nov | The Srangam kit VAMSA_WAYIN | Done by you: built in 51.56 s; cc32c10 pushed (72e109b..cc32c10, 8 files, 577 insertions, 14 deletions). The typecheck\'s and vitest\'s output are not in the screens | Done |\n| 19 Nov | Published | Your probe: CorpusVamsas-BYYDBSh0.js in the live build | Done |\n| 19 Nov | The send | Your screen 10:01: "vamsas corpus-index does not take them yet (deploy it again): left for later"; meta 1 sent; "the site\'s genealogies equal the desk\'s (9 tables)". C29\'s A2 then had no row. The page says the vamsas are not sent yet until they are | You: ask Lovable to deploy corpus-index as it is, then the send |\n| 19 Nov | The Claude credit | Your report: $103.71 spent of $173.93 since 11 Nov (8,799 calls), $70.22 left, to 11 Dec: unchanged since 18 Nov 16:33. Translation 7,373 calls $68.16; scholar (Sonnet) 941 $19.90; vamsa_read 323 $11.19; scholar (Opus) 155 $4.45; probe (Haiku) 7 | Section 35\'s plan |\n| 19 Nov | Who may read | Your SQL at 10:03: 1 admin, 1 super admin, 3 researchers (public.user_roles); corpus.readers 0 rows | Your decision: invite the team (/admin/researchers) |\n| 19 Nov | I1, the first call | Your SQL: still no row for detect-duplicate-articles or suggest-tag-categories | You: Admin, Tags, "suggest categories" once |\n| 19 Nov | Lovable\'s security scan | Your screen: 3 findings. Critical: "Anyone can read, change and delete all of spatial_ref_sys": C27 (11 Nov) found it is PostGIS\'s own catalogue in public, owned by supabase_admin; a REVOKE by us cannot work; only Supabase\'s support can move PostGIS into "extensions" while two columns of ours use it (srangam_correlation_matrix.coordinates and srangam_inscriptions.coordinates); S3 on 11 Nov: 8,500 rows, 0 updated, 0 deleted. A warning (infrastructure and configuration) and an info (personal and sensitive data) were not opened in the screen: not read | You: not "Try to fix" or "Fix all" on spatial_ref_sys; C27\'s S3; mark it accepted with C27\'s reason; the other two opened and sent |\n| 19 Nov | R1, our findings on the dynasties (the credit\'s first use) | Built: scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19): a pack a dynasty (generations, verses, Dikshitar, Raychaudhuri\'s claims the site carries, Law\'s claims for the model only), one call of Claude Sonnet, the machine\'s checks (every id in the pack; a new link of two kinds of source; no run of 8 words of Law\'s 226 pages), a person\'s approval. The plan on the backup of 18 Nov: 10 dynasties, about $0.67 in all, kuru (the trial) about $0.074 with 60 claims of Raychaudhuri and 40 of Law. Tests: 10, no API called | You: the plan, the trial, the review |\n| 19 Nov | Done in full? | No: the deploy and the send; R1\'s trial and review; C30 (approved findings on the vamsa page); P3; P4 | In that order |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | R1 on the dynasties (the credit's first use); P3; P4 |\n",
     '| Next | R1 on the dynasties (the credit\'s first use); P3; P4 |\n\n## 58. 19 Nov: the vamsas wait for one deploy; R1 built (DOCS124_2026_11_19)\n\n| What | State |\n|---|---|\n| Verified | 31da6d5 released; C29 B1, A1, A3 as expected; cc32c10 pushed and published (CorpusVamsas-BYYDBSh0.js); the credit $70.22 left; roles: 1 admin, 1 super admin, 3 researchers |\n| The asks | docs\\ASKS_2026-10-22.md section 36 |\n| Built | scripts\\vamsa_findings.py (R1, VAMSA_FINDINGS_2026_11_19), tests\\test_vamsa_findings_2026_11_19.py; DOCS124 |\n| Not verified | corpus-index deployed again; the two AI functions\' first call; Srangam\'s typecheck and vitest with the kit; the security scan\'s warning and info |\n| To do | the RUNBOOK\'s "19 Nov", in order |\n| Next | R1\'s review; C30 (approved findings on the vamsa page); P3; P4 |\n')

edit('RUNBOOK.md', 1, '5. The live build: the probe of 18 Nov, night, and CorpusVamsas-*.js named in the index.\n',
     '5. The live build: the probe of 18 Nov, night, and CorpusVamsas-*.js named in the index.\n\n## 19 Nov: the vamsas sent; R1\'s trial (VAMSA_FINDINGS_2026_11_19, DOCS124_2026_11_19)\n\ndocs\\ASKS_2026-10-22.md, section 36. In this order:\n\n1. Lovable\'s chat: "Deploy the edge function supabase/functions/corpus-index exactly as it is at commit cc32c10. Change\n   no file." Then, from the automaton\'s root: `python scripts\\index_sync.py --dynasty-works every` (the plan: vamsas\n   here 10, there 0), then with --apply ("equal the desk\'s (10 tables)"); then C29\'s A2.\n2. The automaton: `python scripts\\patch_docs124_2026_11_19.py --check`, then without; `python -m unittest\n   tests.test_vamsa_findings_2026_11_19 tests.test_docs124_2026_11_19`; release.ps1 with\n   COMMIT_MSG_vamsafindings_20261119.txt (the dry run, then -Apply once).\n3. R1: `python scripts\\vamsa_findings.py` (the plan, free); `--show kuru` (the pack, free); `--dynasty kuru --yes` (the\n   trial, about $0.07); `--report`, then read exports\\vamsa_findings.md; for each finding the report numbers, `--approve kuru:1`\n   or `--drop kuru:1` (its own number in place of 1).\n   Only after the trial reads well: `--dynasty all --yes` (about $0.60 more).\n4. Lovable\'s security view: C27\'s S3 (read-only); the spatial_ref_sys finding marked accepted with C27\'s reason; never\n   "Try to fix" or "Fix all" on it (a fix by DROP EXTENSION postgis CASCADE would drop two columns of ours).\n')

edit('ARCHITECTURE.md', 1, "## The genealogies' road (DOCS122_2026_11_18, 18 Nov 2026)\n\nHow the lines of kings travel from the Sanskrit verses to the desk and to the site. Only the first step spends.\n\n| Step | Where | Reads | Writes | Cost |",
     "## The genealogies' road (DOCS122_2026_11_18, 18 Nov 2026)\n\nHow the lines of kings travel from the Sanskrit verses to the desk and to the site. Only the first step spends, and step 7 (our findings, DOCS124_2026_11_19) after it.\n\n| Step | Where | Reads | Writes | Cost |")

edit('ARCHITECTURE.md', 2, "| 6. Show, site, by vamsa | public.corpus_reader_index_vamsas(p_key) (C29), behind corpus._reader_gate: the list without generations, one dynasty with them; /corpus/genealogies/vamsas (Srangam's VAMSA_WAYIN_2026_11_18, DOCS123_2026_11_18) | step 5's vamsas: G6c's aligned.json (step 2), each name tied to its line of step 4, Dikshitar's person and Raychaudhuri's claims the site carries | nothing | free |\n| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n\nThe rules of the road:",
     "| 6. Show, site, by vamsa | public.corpus_reader_index_vamsas(p_key) (C29), behind corpus._reader_gate: the list without generations, one dynasty with them; /corpus/genealogies/vamsas (Srangam's VAMSA_WAYIN_2026_11_18, DOCS123_2026_11_18) | step 5's vamsas: G6c's aligned.json (step 2), each name tied to its line of step 4, Dikshitar's person and Raychaudhuri's claims the site carries | nothing | free |\n| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n| 7. Our findings (R1) | scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6's vamsas (generations, verses, Dikshitar, Raychaudhuri's claims on the site); B. C. Law's claims in claims.db, for the model only | data\\vamsa_findings\\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |\n\nThe rules of the road:")

edit('ARCHITECTURE.md', 3, "- A scholar's claim is shown only when the site carries it already (C23's rule: the public-domain works, the quotation\n  found on the page); B. C. Law's book (in copyright) never; what we find with it comes as our own findings (R1).\n- Not yet on the road: our findings on a dynasty (R1, with B. C. Law), Raychaudhuri beside each step of the per-work\n  page (P2d); the 17 works on the desk's /vamsa page (P3); a review list for the proposed names and the names kept\n  apart (P4).\n",
     "- A scholar's claim is shown only when the site carries it already (C23's rule: the public-domain works, the quotation\n  found on the page); B. C. Law's book (in copyright) never; what we find with it comes as our own findings (R1).\n- Not yet on the road: the approved findings on the vamsa page (C30, once a person has approved some), Raychaudhuri\n  beside each step of the per-work page (P2d); the 17 works on the desk's /vamsa page (P3); a review list for the\n  proposed names and the names kept apart (P4).\n")


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

