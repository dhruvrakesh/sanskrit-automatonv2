#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs125_2026_11_19.py  (2026-11-19)  DOCS125_2026_11_19

19 Nov, midday: corpus-index deployed again; the vamsas sent (10 tables equal); C27's S3 (untouched); 4090724 released;
R1's trial read by hand; R1 v2 built; the admin pages and the landing pages inventoried and their path written
(docs/ADMIN_REWIRE_2026-11-19.md); A1 built (C30, the kit ADMIN_STATUS). Adds:

  docs/ASKS_2026-10-22.md    section 37: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 59
  RUNBOOK.md                 "19 Nov, midday": the order of the steps
  ARCHITECTURE.md            the genealogies' road: step 8, the admin's watch (C30)

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs125_<date> copies.

  python scripts\\patch_docs125_2026_11_19.py --check
  python scripts\\patch_docs125_2026_11_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS125_2026_11_19'
TAG = 'docs125'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'ARCHITECTURE.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS124_2026_11_19', 'docs/STATE_2026-10-18.md': 'DOCS124_2026_11_19', 'RUNBOOK.md': 'DOCS124_2026_11_19', 'ARCHITECTURE.md': 'DOCS124_2026_11_19'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 19 Nov | Done in full? | No: the deploy and the send; R1's trial and review; C30 (approved findings on the vamsa page); P3; P4 | In that order |\n",
     '| 19 Nov | Done in full? | No: the deploy and the send; R1\'s trial and review; C30 (approved findings on the vamsa page); P3; P4 | In that order |\n\n## 37. 19 Nov, midday: the vamsas on the site; R1\'s trial read by hand; the admin pages rewired, first step (DOCS125_2026_11_19)\n\nAsked on 19 Nov, 12:02, with two CSV exports (11:54, 11:56), seven screens (11:26 to 12:00) and the review page of R1\'s\ntrial pasted: "alot of the admin dashboard and landing pages need to be reimagined and rewired to reflect present state\nof local and online reployment and linkages", with the asks of 18 Nov again (P2c, the credit, the scholars\' tooltips,\nthe standing ask). Read, read only: data\\vamsa_findings\\kuru.json and its pack (the backup of 18 Nov, immutable);\nSrangam\'s admin pages (src\\pages\\admin, 14 of them), AdminLayout.tsx, Home.tsx, CorpusStartSection.tsx, corpusMirror.ts;\ndocs\\cloud C4, C7, C9, C21, C27, C29; both repositories\' .git.\n\n**Done in full? No.** Done: the vamsas on the site (10 dynasties); C27\'s S3 (untouched); R1 and DOCS124 released;\nR1\'s trial read against its pack; R1\'s v2 built; the admin pages and the landing pages inventoried, their path written\n(docs\\ADMIN_REWIRE_2026-11-19.md), its first step built (A1). Left: R1 v2\'s reading and a person\'s review; A1 applied;\nA2 to A5 (the grouping and the words are yours); the approved findings on the vamsa page; P3; P4.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 19 Nov | corpus-index deployed again | Done by Lovable at your word: "Deployed corpus-index at cc32c10 ... I didn\'t change any files". It also "Committed platform-managed package changes": a commit after cc32c10 on GitHub; the PC\'s Srangam is at cc32c10 | You: git pull in D:\\srangam-42267 before the next kit |\n| 19 Nov | The send of the vamsas | Your screen: "vamsas here 10, there 0: 10 to send"; "sent 10 row(s) (10 changed), deleted 0; the site\'s genealogies equal the desk\'s (10 tables)". C29\'s A2 at 11:54: 10 rows, synced 05:58:22 UTC; solar 7 works, 14 generations, 10 with Dikshitar, 1 with Raychaudhuri; kroshtu 39 generations; puru 25; kuru 21 | Done |\n| 19 Nov | Lovable\'s security finding | C27\'s S3 at 11:56: the two geography columns (srangam_correlation_matrix.coordinates, srangam_inscriptions.coordinates); PostGIS 3.3.7; 8,500 rows, 8,500 inserted, 0 updated, 0 deleted; 4326 and 3857 both there: untouched. "Fix all" still offered: not pressed | You: mark it accepted with C27\'s reason |\n| 19 Nov | The release of R1 and DOCS124 | Done by you: 4090724 pushed (31da6d5..4090724, 9 files, 1,103 insertions) | Done |\n| 19 Nov | R1\'s trial (kuru) | Run by you at 11:55: $0.0382 (12,610 tokens in, 1,303 out); 5 findings, all passing the machine\'s checks. Read against the pack: the first names five texts it cites no verse of and calls the critical edition a "translation"; the second names the Garuda without its verse and says Law "only" names Sudhanvan (the pack holds 40 of his claims, not all); the third is sound (the generation is Aradhita\'s own, not the one after); the fourth calls Paryasravas another king where MBh 1,90.45 itself says he is Pratipa; the fifth is sound (which Janamejaya) | My reading: approve none of v1; v2 below |\n| 19 Nov | R1, v2 | Built: VAMSA_FINDINGS_V2_2026_11_19 (scripts\\patch_vamsa_findings_v2_2026_11_19.py): each text\'s title in the pack, the second names the texts state (16 in all; MBh 1,90.45 Paryasravas, "whom they call Pratipa"), three rules in the prompt, a warning on each finding that names a text it cites no verse of (on the trial\'s: five on the first, one on the second). Tests 13 | You: the patch; then all ten read under v2 (about $0.67) and reviewed |\n| 19 Nov | "the admin dashboard and landing pages ... reimagined and rewired" | Read: the admin\'s 14 pages read the articles\' tables only; nothing showed the desk\'s worker, the mirror\'s runs, the genealogies sent, who may read, or the AI calls, though the database holds them. The path: docs\\ADMIN_REWIRE_2026-11-19.md (A1 to A5). A1 built: docs\\cloud\\C30_admin_status_2026-11-19.sql (one read-only function, the super admin only) and the Srangam kit ADMIN_STATUS (/admin/desk-site, "Desk and site") | You: C30, the kit; then your word on A2\'s grouping and A3\'s words |\n| 19 Nov | I1, the first call | Your screen at 11:58: Tag Management open (51% uncategorized); no "suggest categories" result in the screens, the ledger not queried again | You: the click, then the query |\n| 19 Nov | The tests | The automaton: test_vamsa_findings (13), test_admin_status (7) and the module suite on a copy; C30 run in PGlite (PostgreSQL 17.5): B1, the change, A1, a refusal for a caller who is not the super admin, the status for the super admin (its numbers checked, the desk\'s own info not in it), a second paste, A2, the rollback. Srangam on a copy (vitest with its worker\'s start time raised): desk-site 5, vamsas 5, index-site 17, b2-site 13, genealogy-heal 6, nav-rbac 11, rbac-pages 17, corner-mail 14 passed; the typecheck clean but for the one test that needs supabase\\ | You: npm run typecheck; npx vitest run; npm run build |\n| 19 Nov | Done in full? | No: R1 v2\'s reading and review; C30 and the kit ADMIN_STATUS; A2 to A5; the approved findings on the vamsa page; P3; P4 | In that order |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | R1's review; C30 (approved findings on the vamsa page); P3; P4 |\n",
     '| Next | R1\'s review; C30 (approved findings on the vamsa page); P3; P4 |\n\n## 59. 19 Nov, midday: the vamsas on the site; A1 built (DOCS125_2026_11_19)\n\n| What | State |\n|---|---|\n| Verified | corpus-index deployed at cc32c10; the vamsas sent (10 tables equal); C29\'s A2 10 rows; C27\'s S3 untouched; 4090724 released; R1\'s trial $0.0382 |\n| The asks | docs\\ASKS_2026-10-22.md section 37; the path docs\\ADMIN_REWIRE_2026-11-19.md |\n| Built | VAMSA_FINDINGS_V2_2026_11_19; docs\\cloud\\C30_admin_status_2026-11-19.sql; the Srangam kit docs\\srangam\\ADMIN_STATUS_2026-11-19 (scripts\\patch_srangam_admin_status_2026_11_19.py); tests\\test_admin_status_2026_11_19.py; DOCS125 |\n| Not verified | the two AI functions\' first call; Srangam\'s vitest and build with the kits on the PC; Lovable\'s commit after cc32c10 |\n| To do | the RUNBOOK\'s "19 Nov, midday", in order |\n| Next | R1 v2 read and reviewed; A2 and A3 once their grouping and words are yours; the approved findings on the vamsa page; P3; P4 |\n')

edit('RUNBOOK.md', 1, '   "Try to fix" or "Fix all" on it (a fix by DROP EXTENSION postgis CASCADE would drop two columns of ours).\n',
     '   "Try to fix" or "Fix all" on it (a fix by DROP EXTENSION postgis CASCADE would drop two columns of ours).\n\n## 19 Nov, midday: R1 v2; the desk and the site (VAMSA_FINDINGS_V2_2026_11_19, ADMIN_STATUS_2026_11_19, DOCS125_2026_11_19)\n\ndocs\\ASKS_2026-10-22.md, section 37. In this order:\n\n1. The automaton: `python scripts\\patch_vamsa_findings_v2_2026_11_19.py --check`, then without; `python\n   scripts\\patch_docs125_2026_11_19.py --check`, then without; `python -m unittest tests.test_vamsa_findings_2026_11_19\n   tests.test_admin_status_2026_11_19 tests.test_docs125_2026_11_19`; release.ps1 with COMMIT_MSG_adminstatus_20261119.txt\n   (the dry run, then -Apply once).\n2. R1 v2: `python scripts\\vamsa_findings.py` (the plan: ten to read, kuru again under v2); `--dynasty all --yes` (about\n   $0.67); `--report`; read exports\\vamsa_findings.md; for each finding the report numbers, `--approve kuru:1` or\n   `--drop kuru:1` (its own dynasty and number in place of kuru:1).\n3. The Lovable Cloud SQL editor: docs\\cloud\\C30_admin_status_2026-11-19.sql, B1 (true x6, false), the change (one\n   paste), A1 (true, false, true), A2.\n4. Srangam, from D:\\srangam-42267: `git pull` first (Lovable committed after cc32c10); the kit\'s patch (--check, then\n   without); npm run typecheck; npx vitest run; npm run build; commit and push; Publish; open /admin/desk-site.\n')

edit('ARCHITECTURE.md', 1, "| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n| 7. Our findings (R1) | scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6's vamsas (generations, verses, Dikshitar, Raychaudhuri's claims on the site); B. C. Law's claims in claims.db, for the model only | data\\vamsa_findings\\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |\n\nThe rules of the road:",
     "| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n| 7. Our findings (R1) | scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6's vamsas (generations, verses, Dikshitar, Raychaudhuri's claims on the site); B. C. Law's claims in claims.db, for the model only | data\\vamsa_findings\\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |\n| 8. Watch, admin | public.corpus_admin_status() (C30, the super admin only, read-only); /admin/desk-site (Srangam's ADMIN_STATUS_2026_11_19, DOCS125_2026_11_19) | the mirror's runs, the index tables, the desk's worker, who may read, srangam_ai_usage | nothing | free |\n\nThe rules of the road:")


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

