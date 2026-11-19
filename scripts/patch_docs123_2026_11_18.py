#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs123_2026_11_18.py  (2026-11-18)  DOCS123_2026_11_18

18 Nov, late night: DOCS122 released; the live build seen; the site's genealogies counted; P2c built (the way in by
vamsa, VAMSA_WAYIN_2026_11_18, with Dikshitar and Raychaudhuri beside each generation); the Claude credit's next uses.
Adds:

  docs/ASKS_2026-10-22.md    section 35: each ask, done or not, with its evidence; the credit's plan
  docs/STATE_2026-10-18.md   section 57
  RUNBOOK.md                 "18 Nov, late night": the order of the steps
  ARCHITECTURE.md            the genealogies' road: the vamsas (C29, the vamsa page); two rules; what is not yet on it

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs123_<date> copies.

  python scripts\\patch_docs123_2026_11_18.py --check
  python scripts\\patch_docs123_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS123_2026_11_18'
TAG = 'docs123'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'ARCHITECTURE.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS122_2026_11_18', 'docs/STATE_2026-10-18.md': 'DOCS122_2026_11_18', 'RUNBOOK.md': 'DOCS122_2026_11_18', 'ARCHITECTURE.md': 'DOCS122_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 18 Nov | Done in full? | No: P2c (each line tagged with its dynasty and vamsa, a way in by Suryavamsa and Candravamsa), P3 (the 17 works on the desk's Vamsa page), P4 (a review list for the 44 proposed names and the 672 kept apart) | In that order |\n",
     '| 18 Nov | Done in full? | No: P2c (each line tagged with its dynasty and vamsa, a way in by Suryavamsa and Candravamsa), P3 (the 17 works on the desk\'s Vamsa page), P4 (a review list for the 44 proposed names and the 672 kept apart) | In that order |\n\n## 35. 18 Nov, late night: the way in by vamsa built; the scholars beside each generation; the credit (DOCS123_2026_11_18)\n\nAsked on 18 Nov, 21:33, with three CSV exports of the Lovable Cloud SQL editor (21:29:57 to 21:30:40) and five screens\n(21:29 to 21:31): the plan of P2c approved as written; "also give me next steps to use my claude api credit"; "the\ngeneaologies work should carry tool tips and reference to dishitar, raychaudhary, bc law and any analyses built from\niterative, statistical analysis of their works"; the standing ask again. Read, read only: docs\\B2_AND_X1C_2026-10-28.md,\ndocs\\PEOPLES_FINDINGS_2026-11-11.md, docs\\BRAIN_PATH_2026-10-21.md, sections 28 to 34 here; data\\shelf\\claims.db and\nkin.db (immutable); data\\vamsa_read\\aligned.json and dynasties_every.json; D:\\backups\\context_20261118.db (immutable;\nthe live database was not opened); data\\jobs.jsonl; docs\\cloud C5, C7, C21, C23, C28; Srangam\'s corpus-index, App.tsx,\nindexSite.ts, CorpusDynasties.tsx, CorpusGenealogies.tsx, _shared\\ai-usage.ts and its migrations.\n\n**Done in full? No.** Done tonight: DOCS122 released by you, the live build seen, the site\'s genealogies counted; P2c\nbuilt (the way in by vamsa, with Dikshitar and Raychaudhuri beside each generation) and tested. Left: P2c applied (yours,\nin the RUNBOOK\'s order), R1 (our findings, with B. C. Law), P3, P4.\n\nMeasured before P2c was built, and why it changed shape: of the 500 lines on the site only 65 hold a founder of the\nsolar or the lunar line, because each line is one father\'s longest line in one work (a tag on each line would have left\n435 lines without one, and some main lines, the Visnupurana\'s Iksvaku branch among them, are no line of their own). G6c\'s\nalignment (aligned.json) sets each dynasty side by side across the works from its founder: that is the way in. The site\ngets it as a table of its own (C29); corpus.index_dynasties and its reader are not changed.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 18 Nov | The release of DOCS122 | Done by you: 97b9fa21 pushed (d7c6eda..97b9fa2, 8 files, 284 insertions, 1 deletion; "verified: origin/main == local HEAD (97b9fa21)"). It also carried scripts\\corpus_mirror_task.ps1 (the task\'s last step of 18 Nov, not committed before) | Done |\n| 18 Nov | The live build | Your probe: index-DCdTjC-a.js, CorpusDynasties-D2CZ5603.js, indexSite-DKfqdnMs.js; the message present: True; work codes 17 of 17 | Done |\n| 18 Nov | The site\'s dynasties | Your SQL of 21:29 to 21:30: 17 works, 517 rows, last sent 18 Nov 15:49:22 UTC; vip4 (49 lines, 52 kB of steps) and bhp9 (47, 42 kB) last sent 17 Nov 04:22 UTC, bhp12 (7) 13 Nov 08:21 UTC: unchanged since, as they should be | Done |\n| 18 Nov | The AI calls (I1) | Your SQL: in seven days 28 calls, all gemini-2.5-flash, all ok, the last 18 Nov 03:01 UTC; no OpenAI call; no gateway; the two functions: no row | You: "suggest categories" once (/admin/tags), then the SQL |\n| 18 Nov | Who may read | Your SQL: corpus.reader_access mode readers since 2026-10-09 01:29:51 UTC; corpus.readers 0 rows. So today the corpus pages open only for admins, super admins and researchers (corpus_reader_allowed, C7) | Your decision: invite the team as researchers (/admin/researchers), or list them |\n| 18 Nov | P2c, the way in by vamsa | Built: VAMSA_WAYIN_2026_11_18 (vamsa_align.vamsa_of; index_sync.py\'s table vamsas); docs\\cloud\\C29_index_vamsas_2026-11-18.sql; the Srangam kit VAMSA_WAYIN (a page /corpus/genealogies/vamsas; the Dynasties page opens ?work=&line=). On the backup of 18 Nov: 10 dynasties (Suryavamsa 1, Candravamsa 9), 174 generations, 725 names of 17 works, 622 tied to their line, about 105 kB | You: the RUNBOOK\'s order |\n| 18 Nov | Tooltips; Dikshitar, Raychaudhuri, B. C. Law | Built into P2c: a hover on each name gives its verse and words, on each chip its meaning; Dikshitar\'s person in the Purana Index on 134 of 174 generations (132 with a page on the site); Raychaudhuri\'s claims the site carries already on 21 generations by the name (a link to the name\'s page, which says that a name may be more than one person) and on 1 step by both its persons. Raychaudhuri\'s book begins with Parikshit, so the early generations have little of him. B. C. Law\'s book is in copyright (to the end of 2029): read on the desk only, never on the site; what we find with it comes as our own findings (R1) | R1 next (below) |\n| 18 Nov | "analyses built from iterative, statistical analysis of their works" | What exists, all on the desk: Raychaudhuri\'s 6,062 claims (Parts I and II) and Law\'s 3,409, each tied to our names (claim_links: 5,784 ties); kin_index.py\'s verdict of Raychaudhuri on each kinship of the indexes (the B2 chip on the Genealogies pages); peoples_index.py: 54 peoples and their claims. What does not exist yet: a finding of ours that joins them on a line (R1, planned on 11 Nov in docs\\PEOPLES_FINDINGS_2026-11-11.md, not built) | R1 next |\n| 18 Nov | The tests | The automaton: 10 modules (this patch\'s 20 tests, the healed replays of VAMSA_SITE and VAMSA_NAMES, the index and dynasty modules) passed on a copy; C29 run in PGlite (PostgreSQL 17.5): B1, the change, A1, the send of the 10 rows (the digest equal to the desk\'s), the reader (the list without generations, one with them), A2, A3, a second paste (nothing changed) and the rollback. Srangam, on a copy: vitest vamsas 5, dynasties 6, dynasties-works 4 passed; the typecheck clean but for one test that needs supabase\\ (not in the copy); index-site, b2-site and genealogy-heal not run there | You: npm run typecheck; npx vitest run; npm run build |\n| 18 Nov | "next steps to use my claude api credit" | Planned below, from the rates measured | Yours, in that order |\n\n**The Claude credit, next** ($70.22 left at 16:33 on 18 Nov, to 11 Dec, your report; usage_log of the backup of 05:41 UTC\nshowed the Natyashastra\'s translation as the largest spend since 17 Nov: 2,063 passages, $9.09 to then; that job and the\nKarana Agama\'s ended together at 13:59 IST, rc 0; whether every passage of the Natyashastra is done is not verified):\n\n| # | Work | Before it | Rate measured | About |\n|---|---|---|---|---|\n| 1 | R1 on the ten dynasties: our findings, each a sentence or two in our own words joining what the verses, Dikshitar, Raychaudhuri and B. C. Law say of a dynasty\'s people (Law\'s Kasis, Kosalas, Asmakas, Magadhas and Bhojas meet the solar line, the lunar line\'s Kasis, Magadha and the Yadavas), every source cited by verse, page or claim; machine checks (every citation held, no run of eight words of Law, a new link cites two kinds of source); a person approves each; then on the vamsa page as "Our finding" | R1 built (free); a trial of one dynasty | Law\'s 195 pages read for $1.71 (11 Nov); R1 not measured | $1 to $3 |\n| 2 | Mallapurana\'s edition, the rest (827 of 1,004 verses) | a person reads 20 of its 54 flagged first (section 28) | $0.0457 a verse | about $38 |\n| 3 | The Akasa Bhairava Kalpa, the rest (2,805 passages less the 159 done on 15 and 17 Nov) | the dashboard restarted when idle | $0.004 to $0.008 a passage (17 Nov) | $11 to $21 |\n| - | Kept: about $8 to $20 for R1\'s re-reads and what the trials show | | | |\n\nThe credit is read with python scripts\\claude_engine.py --credit before each.\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | P2c; P3; P4 |\n',
     '| Next | P2c; P3; P4 |\n\n## 57. 18 Nov, late night: the way in by vamsa built (DOCS123_2026_11_18)\n\n| What | State |\n|---|---|\n| Verified | 97b9fa21 released; the live build (CorpusDynasties-D2CZ5603.js, 17 work codes); the site: 17 works, 517 rows; AI calls: 28 Gemini, no gateway; reader_access readers, corpus.readers 0 rows |\n| The asks | docs\\ASKS_2026-10-22.md section 35 |\n| Built | VAMSA_WAYIN_2026_11_18 (scripts\\patch_vamsa_wayin_2026_11_18.py, tests\\test_vamsa_wayin_2026_11_18.py); docs\\cloud\\C29_index_vamsas_2026-11-18.sql; the Srangam kit docs\\srangam\\VAMSA_WAYIN_2026-11-18 (scripts\\patch_srangam_vamsa_wayin_2026_11_18.py); DOCS123 |\n| Not verified | the two AI functions\' first call; whether the Natyashastra\'s translation finished; Srangam\'s index-site, b2-site and genealogy-heal tests with the kit (run on the PC) |\n| To do | the RUNBOOK\'s "18 Nov, late night", in order |\n| Next | R1 on the dynasties (the credit\'s first use); P3; P4 |\n')

edit('RUNBOOK.md', 1, '   and look for "No dynasty of this text has been sent from the desk yet." (the probe in the chat of 18 Nov, night).\n',
     '   and look for "No dynasty of this text has been sent from the desk yet." (the probe in the chat of 18 Nov, night).\n\n## 18 Nov, late night: the way in by vamsa (VAMSA_WAYIN_2026_11_18, DOCS123_2026_11_18)\n\ndocs\\ASKS_2026-10-22.md, section 35. In this order (each step\'s check before the next):\n\n1. The automaton, from its root: `python scripts\\patch_vamsa_wayin_2026_11_18.py --check`, then without;\n   `python scripts\\patch_docs123_2026_11_18.py --check`, then without; `python -m unittest\n   tests.test_vamsa_wayin_2026_11_18 tests.test_vamsa_site_2026_11_18 tests.test_vamsa_names_2026_11_18\n   tests.test_docs123_2026_11_18`; release.ps1 with COMMIT_MSG_vamsawayin_20261118.txt (the dry run, then -Apply once).\n2. The Lovable Cloud SQL editor: docs\\cloud\\C29_index_vamsas_2026-11-18.sql, B1 (expected true, true, false, false), the\n   change (one paste), A1 (true x5, 0, 517), A3 (false, true, false, false).\n3. Srangam, from D:\\srangam-42267: the kit\'s patch (--check, then without); npm run typecheck; npx vitest run; npm run\n   build; commit and push; ask Lovable\'s chat to deploy supabase/functions/corpus-index as it is; Publish.\n4. The desk: `python scripts\\index_sync.py --dynasty-works every` (the plan: vamsas here 10, there 0: 10 to send; the\n   dynasties 0), then with --apply ("equal the desk\'s (10 tables)"); then C29\'s A2.\n5. The live build: the probe of 18 Nov, night, and CorpusVamsas-*.js named in the index.\n')

edit('ARCHITECTURE.md', 1, "| 3. Register | scripts\\vamsa_register.py (G6d; VAMSA_NAMES) | steps 1 and 2 | data\\vamsa_read\\register.json; exports\\vamsa_register.csv and .md | free |\n| 4. Join | scripts\\vamsa_join.py (G5b; VAMSA_SITE) | step 1; data\\shelf\\kin.db (the Purana Index, kin_index.py); data\\context.db | data\\vamsa_read\\dynasties.json (vip4, bhp9, bhp12), dynasties_every.json (--work every) | free |\n| 5. Send | scripts\\index_sync.py --dynasty-works every; nightly from scripts\\corpus_mirror_task.ps1 | step 4 and the indexes (kin.db, vamsa.db, claims.db) | Srangam's nine corpus.index_* tables through the edge function corpus-index (the dynasties in corpus.index_dynasties, docs\\cloud\\C28); only rows whose row_hash changed | free |\n| 6. Show, site | public.corpus_reader_index_dynasties(p_work), behind corpus._reader_gate; /corpus/genealogies/dynasties asks for one work at a time (Srangam's DYNASTIES_WORKS_2026_11_18) | step 5 | nothing | free |\n| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n",
     "| 3. Register | scripts\\vamsa_register.py (G6d; VAMSA_NAMES) | steps 1 and 2 | data\\vamsa_read\\register.json; exports\\vamsa_register.csv and .md | free |\n| 4. Join | scripts\\vamsa_join.py (G5b; VAMSA_SITE) | step 1; data\\shelf\\kin.db (the Purana Index, kin_index.py); data\\context.db | data\\vamsa_read\\dynasties.json (vip4, bhp9, bhp12), dynasties_every.json (--work every) | free |\n| 5. Send | scripts\\index_sync.py --dynasty-works every; nightly from scripts\\corpus_mirror_task.ps1 | step 4 and the indexes (kin.db, vamsa.db, claims.db) | Srangam's corpus.index_* tables through the edge function corpus-index (the dynasties in corpus.index_dynasties, docs\\cloud\\C28; the vamsas in corpus.index_vamsas, C29); only rows whose row_hash changed | free |\n| 6. Show, site | public.corpus_reader_index_dynasties(p_work), behind corpus._reader_gate; /corpus/genealogies/dynasties asks for one work at a time (Srangam's DYNASTIES_WORKS_2026_11_18) | step 5 | nothing | free |\n| 6. Show, site, by vamsa | public.corpus_reader_index_vamsas(p_key) (C29), behind corpus._reader_gate: the list without generations, one dynasty with them; /corpus/genealogies/vamsas (Srangam's VAMSA_WAYIN_2026_11_18, DOCS123_2026_11_18) | step 5's vamsas: G6c's aligned.json (step 2), each name tied to its line of step 4, Dikshitar's person and Raychaudhuri's claims the site carries | nothing | free |\n| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n")

edit('ARCHITECTURE.md', 2, "  father and, where both give him, one grandfather); a second name only where a verse says it; names that differ are\n  shown side by side, never ruled on.\n- Not yet on the road: a dynasty and vamsa on each line, for a way in by Suryavamsa and Candravamsa (P2c); the 17 works\n  on the desk's /vamsa page (P3); a review list for the proposed names and the names kept apart (P4).\n",
     "  father and, where both give him, one grandfather); a second name only where a verse says it; names that differ are\n  shown side by side, never ruled on.\n- G6c's aligned.json is written by vamsa_align.py: run it after a new reading, before the send (DOCS123_2026_11_18).\n- A scholar's claim is shown only when the site carries it already (C23's rule: the public-domain works, the quotation\n  found on the page); B. C. Law's book (in copyright) never; what we find with it comes as our own findings (R1).\n- Not yet on the road: our findings on a dynasty (R1, with B. C. Law), Raychaudhuri beside each step of the per-work\n  page (P2d); the 17 works on the desk's /vamsa page (P3); a review list for the proposed names and the names kept\n  apart (P4).\n")


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

