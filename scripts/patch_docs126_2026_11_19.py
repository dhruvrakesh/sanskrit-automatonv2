#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs126_2026_11_19.py  (2026-11-19)  DOCS126_2026_11_19

19 Nov, afternoon: 64f58d70 released; C30 in the database; why the Srangam push was refused, and 31419c7 pushed; R1 v2's
49 findings, each read against its verses (20 approved, 29 dropped); our findings for the vamsa page built (C31, the
desk's VAMSA_FINDINGS_SITE, the Srangam kit). Adds:

  docs/ASKS_2026-10-22.md    section 38: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 60
  RUNBOOK.md                 "19 Nov, afternoon": the order of the steps
  ARCHITECTURE.md            the genealogies' road: step 9, our findings on the site (C31)

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs126_<date> copies.

  python scripts\\patch_docs126_2026_11_19.py --check
  python scripts\\patch_docs126_2026_11_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS126_2026_11_19'
TAG = 'docs126'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'ARCHITECTURE.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS125_2026_11_19', 'docs/STATE_2026-10-18.md': 'DOCS125_2026_11_19', 'RUNBOOK.md': 'DOCS125_2026_11_19', 'ARCHITECTURE.md': 'DOCS125_2026_11_19'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 19 Nov | Done in full? | No: R1 v2's reading and review; C30 and the kit ADMIN_STATUS; A2 to A5; the approved findings on the vamsa page; P3; P4 | In that order |\n",
     '| 19 Nov | Done in full? | No: R1 v2\'s reading and review; C30 and the kit ADMIN_STATUS; A2 to A5; the approved findings on the vamsa page; P3; P4 | In that order |\n\n## 38. 19 Nov, afternoon: the desk and site page pushed; the 49 findings reviewed; our findings for the vamsa page (DOCS126_2026_11_19)\n\nAsked on 19 Nov, 13:15 ("regenerate carefully", with the export of 13:09 and four screens) and 15:19 (the ask of\n12:02 again: the admin pages, P2c, the credit, the scholars\' tooltips, the standing ask; two screens). Read, read only:\nSrangam\'s .git (its objects, by Python: HEAD, origin/main, Lovable\'s two commits, the blobs of c01665e), bun.lock;\ndata\\vamsa_findings\\*.json and the ten packs rebuilt from the backup of 19 Nov (immutable; solar\'s 11,276 characters as\nsent); the verses of KurmP 1,21 in data\\vamsa_read; index_sync.py, vamsa_findings.py; C29; corpus-index (lib.ts);\nCorpusVamsas.tsx, indexSite.ts.\n\n**Done in full? No.** Done: the desk and site page committed and pushed (31419c7); C30 in the database; R1 v2 read\nall ten ($0.237, 49 findings); each finding read against its verses, 20 approved and 29 dropped (your decisions);\nour findings for the vamsa page built (C31, the desk\'s VAMSA_FINDINGS_SITE, the Srangam kit). Left: Publish and C30\'s\nA1 and A2; C31 and the kit applied; the aligner\'s two errors and the checker\'s next rules; A2 to A5; P3; P4.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 19 Nov | The release of R1 v2, C30, the kit ADMIN_STATUS, DOCS125 | Done by you: 64f58d70 pushed (4090724..64f58d7), "verified: origin/main == local HEAD" | Done |\n| 19 Nov | C30 in the database | The change pasted (13:08, "Query succeeded"); the export of 13:09 (the columns of B1, run after): access, ai_ledger, c29, c30, desk_worker, mirror_runs, rbac all true: the function is there | You: A1 (true, false, true) and A2 |\n| 19 Nov | Why the Srangam push was refused | Read in .git: git pull --ff-only (13:11) fetched Lovable\'s 9074589 ("Work in progress": types.ts, the vamsas\' reader typed) and 33f9301 (package.json and bun.lock: @lovable.dev/vite-plugin-hmr-gate ^1.8.0 to ^1.8.3) but did not move main: bun.lock carried a change of 14 Nov never committed (caniuse-lite 1.0.30001727 to 1.0.30001814). The commands went on (they were not gated): c01665e on cc32c10, the push refused. c01665e held the kit\'s five files exactly (blob by blob); Lovable\'s two commits touch none of them | Done: the commands given again, each block stopping at the first failure |\n| 19 Nov | The Srangam push | Done by you: bun.lock set aside (bun.lock.bak_local_20261119), the commit replayed on 33f9301, typecheck, the five test files, build (39.69 s), pushed 33f9301..31419c7; "local 31419c7... GitHub 31419c7..." | You: Publish; open /admin/desk-site |\n| 19 Nov | R1 v2, the ten dynasties | Done by you at 12:52 to 12:53: 10 read, 49 proposed, 0 refused, $0.237 (solar 6, lunar 5, yadu 4, haihaya 5, kroshtu 5, turvasu 5, druhyu 4, puru 5, kuru 5, magadha 5) | Done |\n| 19 Nov | The 49 findings | Each read against its pack and its verses: 20 hold up (solar 1, 3, 4, 5; lunar 2; haihaya 1, 2, 4, 5; kroshtu 1, 2, 3; turvasu 2; druhyu 1, 4; puru 1, 4; kuru 1, 2; magadha 1). 29 dropped: a verse misread (R 2,102.7 makes Vikuksi Kuksi\'s son; Marutta adopted the Paurava Dusyanta, BndP 2,74.3; the Matsya and the Brahmanda make Babhru and Setu brothers), the aligner\'s places read as the texts\' order (the Brahmanda\'s Samksheya is Kunti\'s son, BndP 2,69.5; the Kurma names both Yayati and Ayati, KurmP 1,21.5), the desk\'s own words ("the pack", "the desk aligns"), a count wrong (Mahismat is four or five generations after Haihaya). Recorded by you: "48 decision(s) recorded"; 0 proposed, 20 approved, 29 dropped, 0 refused | Done |\n| 19 Nov | "tool tips and reference to dikshitar, raychaudhary, bc law and any analyses" | Built: our findings on the vamsa page. The desk: VAMSA_FINDINGS_SITE_2026_11_19 (scripts\\patch_vamsa_findings_site_2026_11_19.py): index_sync.py sends the approved findings with their dynasty, each citation resolved from what the site carries (a generation, a verse with its words, a second name, Dikshitar\'s person, Raychaudhuri\'s claim, B. C. Law\'s page only), only once the site says it takes them. The site: docs\\cloud\\C31_vamsa_findings_2026-11-19.sql (a column, a door before C29\'s, the manifest\'s word, one reader); the Srangam kit VAMSA_FINDINGS_SITE (the count on a dynasty, "Our findings" above its generations, each source\'s words on hover, Law by page). On the backup of 19 Nov: 20 findings, 131 citations (67 verses, 26 generations, 17 Index, 13 Law pages, 8 Raychaudhuri), none left unresolved | You: the patch; C31; the kit; then index_sync.py --dynasty-works every --apply |\n| 19 Nov | What the review found wrong on the desk | The vamsa page shows the Kurma\'s Ayati at Yayati\'s place (the aligner picked the wrong son of a verse naming several); the Brahmanda\'s Samksheya at Arjuna\'s place; Raychaudhuri\'s count tied by name (Puru\'s son Janamejaya shows the count of Pariksit\'s son); the checker\'s warning blind to a cited generation; the desk\'s words reaching a finding | Next: the aligner\'s fix and the checker\'s rules, then the affected dynasties read again (about $0.25) |\n| 19 Nov | The admin pages and the landing pages (A2, A3) | Unchanged since 12:02: the plan, docs\\ADMIN_REWIRE_2026-11-19.md | You: your word on A2\'s grouping and A3\'s words |\n| 19 Nov | The tests | The automaton: test_vamsa_findings_site (16), test_vamsa_wayin healed (its replay compares only while no later patch is on top), the module suite on a copy (the same 48 failing as before: 40 flask, 3 indic, 5 environment); C31 in PGlite (PostgreSQL 17.5): B1, the change, A1, the C29 rows again (0 changed), with the findings (9 changed), the other tables through the doors, the manifest\'s digest equal to the desk\'s, the reader gated, C29\'s reader unchanged, A2 (no Law citation with more than its page), A3, a second paste, the rollback. Srangam on a copy (vitest): vamsa-findings 4, vamsas 5, index-site 17, genealogy-heal 6; the typecheck clean but for the one test that needs supabase\\ | You: npm run typecheck; npx vitest run (the two files); npm run build |\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | R1 v2 read and reviewed; A2 and A3 once their grouping and words are yours; the approved findings on the vamsa page; P3; P4 |\n',
     '| Next | R1 v2 read and reviewed; A2 and A3 once their grouping and words are yours; the approved findings on the vamsa page; P3; P4 |\n\n## 60. 19 Nov, afternoon: our findings for the vamsa page (DOCS126_2026_11_19)\n\n| What | State |\n|---|---|\n| Verified | 64f58d70 released; C30 in the database; Srangam 31419c7 pushed (local equal to GitHub); R1 v2: 49 proposed, $0.237; 20 approved, 29 dropped |\n| The asks | docs\\ASKS_2026-10-22.md section 38 |\n| Built | VAMSA_FINDINGS_SITE_2026_11_19; docs\\cloud\\C31_vamsa_findings_2026-11-19.sql; the Srangam kit docs\\srangam\\VAMSA_FINDINGS_SITE_2026-11-19 (scripts\\patch_srangam_vamsa_findings_site_2026_11_19.py); tests\\test_vamsa_findings_site_2026_11_19.py; DOCS126 |\n| Not verified | Publish of 31419c7; C30\'s A1 and A2; the desk and site page on the site; Srangam\'s vitest and build with the kit on the PC |\n| To do | the RUNBOOK\'s "19 Nov, afternoon", in order |\n| Next | the aligner\'s two errors and the checker\'s rules, the dynasties they touch read again; A2 and A3 once their grouping and words are yours; P3; P4 |\n')

edit('RUNBOOK.md', 1, '   without); npm run typecheck; npx vitest run; npm run build; commit and push; Publish; open /admin/desk-site.\n',
     "   without); npm run typecheck; npx vitest run; npm run build; commit and push; Publish; open /admin/desk-site.\n\n## 19 Nov, afternoon: our findings for the vamsa page (VAMSA_FINDINGS_SITE_2026_11_19, DOCS126_2026_11_19)\n\ndocs\\ASKS_2026-10-22.md, section 38. In this order:\n\n1. The automaton: `python scripts\\patch_vamsa_findings_site_2026_11_19.py --check`, then without; `python\n   scripts\\patch_docs126_2026_11_19.py --check`, then without; `python -m unittest\n   tests.test_vamsa_findings_site_2026_11_19 tests.test_vamsa_wayin_2026_11_18 tests.test_docs126_2026_11_19`;\n   release.ps1 with COMMIT_MSG_findingssite_20261119.txt (the dry run, then -Apply once).\n2. The Lovable Cloud SQL editor: docs\\cloud\\C31_vamsa_findings_2026-11-19.sql, B1 (true, true, false, false, false),\n   the change (one paste), A1 (true x5, 10, 0), A3 (false, true, false, false).\n3. Srangam, from D:\\srangam-42267: git status and git pull --ff-only (each stopping at the first failure); the kit's\n   patch (--check, then without); npm run typecheck; npx vitest run src/__tests__/vamsa-findings.test.tsx\n   src/__tests__/vamsas.test.tsx; npm run build; commit and push; Publish.\n4. The desk: `python scripts\\index_sync.py --dynasty-works every` (the plan: vamsas 9 to send), then with --apply;\n   C31's A2 (solar 4, lunar 1, haihaya 4, kroshtu 3, turvasu 1, druhyu 2, puru 2, kuru 2, magadha 1); open\n   /corpus/genealogies/vamsas signed in.\n")

edit('ARCHITECTURE.md', 1, "| 7. Our findings (R1) | scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6's vamsas (generations, verses, Dikshitar, Raychaudhuri's claims on the site); B. C. Law's claims in claims.db, for the model only | data\\vamsa_findings\\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |\n| 8. Watch, admin | public.corpus_admin_status() (C30, the super admin only, read-only); /admin/desk-site (Srangam's ADMIN_STATUS_2026_11_19, DOCS125_2026_11_19) | the mirror's runs, the index tables, the desk's worker, who may read, srangam_ai_usage | nothing | free |\n\nThe rules of the road:",
     '| 7. Our findings (R1) | scripts\\vamsa_findings.py (VAMSA_FINDINGS_2026_11_19); a person approves each (--approve, --drop) | step 6\'s vamsas (generations, verses, Dikshitar, Raychaudhuri\'s claims on the site); B. C. Law\'s claims in claims.db, for the model only | data\\vamsa_findings\\<dynasty>.json (Law cited by id and page; a finding that shares 8 words with his pages withheld); exports\\vamsa_findings.md (the review page, not in git) | paid: Claude Sonnet, about $0.07 a dynasty (estimate of 19 Nov) |\n| 8. Watch, admin | public.corpus_admin_status() (C30, the super admin only, read-only); /admin/desk-site (Srangam\'s ADMIN_STATUS_2026_11_19, DOCS125_2026_11_19) | the mirror\'s runs, the index tables, the desk\'s worker, who may read, srangam_ai_usage | nothing | free |\n| 9. Our findings, on the site | index_sync.findings_for (VAMSA_FINDINGS_SITE_2026_11_19): the approved findings with their citations resolved; corpus.index_vamsas.findings and public.corpus_reader_index_vamsa_findings() (C31); the vamsa page\'s "Our findings" (Srangam\'s VAMSA_FINDINGS_SITE, DOCS126_2026_11_19) | data\\vamsa_findings\\*.json (approved only), the vamsas\' rows, the claims the site carries | corpus.index_vamsas.findings | free |\n\nThe rules of the road:')


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

