#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs127_2026_11_20.py  (2026-11-20)  DOCS127_2026_11_20

20 Nov, morning: C30's and C31's checks, the send of our findings; the $12.13 of Gemini the maintenance run's entity
extraction spent on 17 to 19 Nov with nobody asking, and its guard (ENTITY_ALLOWANCE); the scan's finding on C30 and
C30b; the standing prompt kept in memory; why the aligner's fixes wait for the findings to be pinned. Adds:

  docs/ASKS_2026-10-22.md    section 39: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 61
  RUNBOOK.md                 "20 Nov, morning": the order of the steps

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs127_<date> copies.

  python scripts\\patch_docs127_2026_11_20.py --check
  python scripts\\patch_docs127_2026_11_20.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS127_2026_11_20'
TAG = 'docs127'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS126_2026_11_19', 'docs/STATE_2026-10-18.md': 'DOCS126_2026_11_19', 'RUNBOOK.md': 'DOCS126_2026_11_19'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 19 Nov | The tests | The automaton: test_vamsa_findings_site (16), test_vamsa_wayin healed (its replay compares only while no later patch is on top), the module suite on a copy (the same 48 failing as before: 40 flask, 3 indic, 5 environment); C31 in PGlite (PostgreSQL 17.5): B1, the change, A1, the C29 rows again (0 changed), with the findings (9 changed), the other tables through the doors, the manifest's digest equal to the desk's, the reader gated, C29's reader unchanged, A2 (no Law citation with more than its page), A3, a second paste, the rollback. Srangam on a copy (vitest): vamsa-findings 4, vamsas 5, index-site 17, genealogy-heal 6; the typecheck clean but for the one test that needs supabase\\ | You: npm run typecheck; npx vitest run (the two files); npm run build |\n",
     '| 19 Nov | The tests | The automaton: test_vamsa_findings_site (16), test_vamsa_wayin healed (its replay compares only while no later patch is on top), the module suite on a copy (the same 48 failing as before: 40 flask, 3 indic, 5 environment); C31 in PGlite (PostgreSQL 17.5): B1, the change, A1, the C29 rows again (0 changed), with the findings (9 changed), the other tables through the doors, the manifest\'s digest equal to the desk\'s, the reader gated, C29\'s reader unchanged, A2 (no Law citation with more than its page), A3, a second paste, the rollback. Srangam on a copy (vitest): vamsa-findings 4, vamsas 5, index-site 17, genealogy-heal 6; the typecheck clean but for the one test that needs supabase\\ | You: npm run typecheck; npx vitest run (the two files); npm run build |\n\n## 39. 20 Nov, morning: our findings on the site; $12 of Gemini spent with nobody asking, and its guard; the scan\'s finding on C30 (DOCS127_2026_11_20)\n\nAsked on 20 Nov, 08:41, with five CSV exports (19 Nov, 16:46 to 16:58) and nine screens: "i ended up using 10 USD of my\ngemini credit without any actions on my part", the next round of 19 Nov again (the aligner\'s errors, the checker,\nRaychaudhuri by person, A2 and A3, the click and the invitations), "and tap memory for repetitive prompts". Read, read\nonly: the backup data\\context.db of 20 Nov 04:03 (immutable: usage_log, usage_totals, budget_state);\nD:\\backups\\maintenance_log.txt, the dashboard\'s log of 17 Nov; scripts\\maintenance_runner.ps1, extract_entities.py,\nusage_meter.py, set_budget.py, vamsa_align.py; C30; both repositories\' .git; data\\vamsa_findings\\*.json.\n\n**Done in full? No.** Done: C30\'s checks; C31, the send and its checks (20 findings, 131 citations on the site); the\nGemini spend traced to its step and a daily allowance built for it; C30 rebuilt without a command made at run time\n(C30b); the standing prompt kept in memory. Left: the allowance and C30b applied; the vamsa page and the desk and\nsite page seen on the site; the aligner\'s errors (the findings pinned to their generations first); the checker\'s\nrules; Raychaudhuri by person; A2, A3.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 20 Nov | C30\'s checks | Your exports of 19 Nov: A1 false, true, true; A2 desk last seen 11:09:11 UTC, the mirror\'s last run 11:03:12 UTC, 66 live texts, 517 dynasty rows, readers, 10 vamsas | Done |\n| 20 Nov | C31 and the send | B1 true, true, false, false, false; the change pasted ("Query succeeded"); A1 true x5, 10, 0; A3 false, false, true, false; index_sync.py: "vamsas here 10, there 10: 9 to send", then "sent 9 row(s) (9 changed), deleted 0; the site\'s genealogies equal the desk\'s (10 tables)"; A2: solar 4, lunar 1, yadu 0, haihaya 4, kroshtu 3, turvasu 1, druhyu 2, puru 2, kuru 2, magadha 1 (20 findings, 131 citations), law_with_words 0 on every row | Done |\n| 20 Nov | The releases | The automaton d6da526 pushed (28 files, data\\vamsa_findings\\*.json among them: read again for B. C. Law, 0 runs of 8 words shared with his claims in any of the ten). Srangam 808246d pushed (local equal to GitHub) | You: Publish; open the vamsa page |\n| 20 Nov | "10 USD of my gemini credit without any actions on my part" | Read in usage_log: the entity extraction (kind entities, gemini-2.5-flash) spent $1.99 on 17 Nov, $7.25 on 18 Nov, $2.89 on 19 Nov: $12.13 for 7,937 verses ($0.00153 a verse); the rest of Gemini on those three days $0.36 (OCR $0.24, embeddings $0.12). The chain: on 17 and 18 Nov the dashboard\'s translations (Claude, $49.97) added 6,493 translated passages; the 3-hourly maintenance run embedded them (Gemini, $0.12) and its step c read each for names (scripts\\extract_entities.py --limit 1500), six runs from 18 Nov 16:54 to 19 Nov 12:00 IST (the first two left no lines in the log; the last four read 1,498, 1,498, 1,499 and 1,434 verses). Only the budget cap stopped it: $161.36 of $162 (budget_state, 19 Nov 07:17 UTC). Nothing waits now (0 verses without names in the backup of 20 Nov 04:03). The dashboard\'s log ends with "[BUDGET] Set to $167.00" (between 06:01 and 07:10 IST on 20 Nov) | Built: ENTITY_ALLOWANCE_2026_11_20 (scripts\\patch_entity_allowance_2026_11_20.py): the scheduled run reads at most $0.25 a day, then asks with the count, the cost and the command. You: the patch; say whether the $167 was yours |\n| 20 Nov | Lovable\'s scan: "Stored data decides which commands corpus_admin_status runs" (Critical) | Read against C30: the table names came from a fixed list in the function, not from stored rows, and its first statement refuses all but the super admin (42501 in the tests): no one could steer it. Built: docs\\cloud\\C30b_admin_status_static_2026-11-20.sql: the ten tables read by name, no EXECUTE; the same answer (tested side by side in PGlite: equal but for as_of and scheme admin-status.2), the same grants | You: C30b (B1, the change, A1); then mark the finding with its reason |\n| 20 Nov | The scan\'s other three | spatial_ref_sys: PostGIS\'s own table, untouched since 11 Nov (C27\'s S3); never "Try to fix" or "Fix all". The warning (infrastructure) and the info (personal data) were not opened in the screens | You: their two screens, opened |\n| 20 Nov | "tap memory for repetitive prompts" | Done: the standing prompt of this project (revive the context from the documents, the code, the database, the edge functions and the logs; done in full or not; the pending work; the enterprise path; accurate, exhaustive, nothing invented; the PowerShell and SQL; the team\'s one-pager) and the rule of surgical changes are kept in memory, with the scholars\' tooltips as the genealogies\' requirement | Done |\n| 20 Nov | The aligner\'s errors | Read in vamsa_align.py: two names are one at 0.82 of their letters, so Ayati and Yayati are one (0.91), and a son is chosen by the most such names, then the longest line, then the person\'s key; in the Kurma both sons tie and Ayati\'s key wins. A name no other text has is placed by the alignment\'s tie, at the end (the Brahmanda\'s Samksheya at Arjuna\'s place). Both fixes change the generations\' numbers, and the 20 approved findings cite generations by number | Next: the findings pinned to the generations they were read against (a changed dynasty\'s findings held, not shown wrong), then the two fixes, then the dynasties they touch read again |\n| 20 Nov | The checker; Raychaudhuri by person; A2 and A3 | Not built this morning: the spend and the scan came first | Next, in that order |\n| 20 Nov | The tests | The automaton: test_entity_allowance (8), the module suite on a copy (the same 48 failing as before: 40 flask, 3 indic, 5 environment); C30b in PGlite (PostgreSQL 17.5): B1, the change, A1, the refusal for one who is not the super admin, the same answer as C30, a second paste, C30 again (its rollback) | You: python -m unittest tests.test_entity_allowance_2026_11_20 tests.test_docs127_2026_11_20 |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | the aligner's two errors and the checker's rules, the dynasties they touch read again; A2 and A3 once their grouping and words are yours; P3; P4 |\n",
     '| Next | the aligner\'s two errors and the checker\'s rules, the dynasties they touch read again; A2 and A3 once their grouping and words are yours; P3; P4 |\n\n## 61. 20 Nov, morning: the Gemini spend\'s guard; C30b (DOCS127_2026_11_20)\n\n| What | State |\n|---|---|\n| Verified | C30\'s A1 and A2; C31, the send of 9 rows and A2 (20 findings, 131 citations, no Law citation past its page); d6da526 and 808246d pushed |\n| The asks | docs\\ASKS_2026-10-22.md section 39 |\n| Built | ENTITY_ALLOWANCE_2026_11_20 (scripts\\patch_entity_allowance_2026_11_20.py); docs\\cloud\\C30b_admin_status_static_2026-11-20.sql; tests\\test_entity_allowance_2026_11_20.py; DOCS127 |\n| Not verified | Publish of 808246d; the vamsa page\'s findings and the desk and site page on the site; who set the budget to $167 |\n| To do | the RUNBOOK\'s "20 Nov, morning", in order |\n| Next | the findings pinned to their generations; the aligner\'s two fixes; the checker\'s rules; the dynasties touched read again (about $0.25); Raychaudhuri by person; A2 and A3 |\n')

edit('RUNBOOK.md', 1, '   /corpus/genealogies/vamsas signed in.\n',
     '   /corpus/genealogies/vamsas signed in.\n\n## 20 Nov, morning: the Gemini spend\'s guard; C30b (ENTITY_ALLOWANCE_2026_11_20, DOCS127_2026_11_20)\n\ndocs\\ASKS_2026-10-22.md, section 39. In this order:\n\n1. The automaton: `python scripts\\patch_entity_allowance_2026_11_20.py --check`, then without; `python\n   scripts\\patch_docs127_2026_11_20.py --check`, then without; `python -m unittest tests.test_entity_allowance_2026_11_20\n   tests.test_docs127_2026_11_20`; release.ps1 with COMMIT_MSG_entityallow_20261120.txt (the dry run, then -Apply once).\n   The next maintenance run reads names for at most $0.25 a day; past it, maintenance_log.txt says "ASK (allowance)".\n2. `python scripts\\set_budget.py` (the cap, the spend, the headroom); `--cap` only by your decision.\n3. The Lovable Cloud SQL editor: docs\\cloud\\C30b_admin_status_static_2026-11-20.sql, B1 (true, true, true), the change,\n   A1 (true, false, true, false, true); in Lovable\'s security view mark the C30 finding with its reason; leave\n   spatial_ref_sys as it is (C27).\n4. Publish Srangam (808246d); open /corpus/genealogies/vamsas (signed in) and /admin/desk-site (the super admin).\n')


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

