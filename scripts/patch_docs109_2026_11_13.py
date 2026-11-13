#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs109_2026_11_13.py  (2026-11-13)  DOCS109_2026_11_13

The page's first verses (BANNER_HEAD), Mallapurana's edition (DESK_SCHOLAR_NEXT), the correction on corpus-index (Publish
does not deploy an edge function), the credit's steps priced again, and the answer on amateur readers. This patch adds:

  docs/ASKS_2026-10-22.md    section 22: each ask of 13 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 44
  RUNBOOK.md                 "13 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs109_<date> copies.

  python scripts\\patch_docs109_2026_11_13.py --check
  python scripts\\patch_docs109_2026_11_13.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS109_2026_11_13'
TAG = 'docs109'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS108_2026_11_11', 'docs/STATE_2026-10-18.md': 'DOCS108_2026_11_11', 'RUNBOOK.md': 'DOCS108_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 11 Nov | The dashboard | restart_dashboard.ps1 refused: an OCR job, sharada_tilaka_tantra_ii, running for 1,476,991 seconds (17 days) | Yours: its pages counted (below), then Pause or let it finish |\n',
     '| 11 Nov | The dashboard | restart_dashboard.ps1 refused: an OCR job, sharada_tilaka_tantra_ii, running for 1,476,991 seconds (17 days) | Yours: its pages counted (below), then Pause or let it finish |\n\n## 22. 13 Nov: the page\'s first verses; Mallapurana\'s edition; is it done, and for whom (DOCS109_2026_11_13)\n\nAsked on 13 Nov, with C28\'s B1, A1 and A3 exported, the screenshots of vamsa_join, the credit\'s lines, index_sync and the\nthree texts\' status: "why dont we have prose type scholarly editions for mallapurana or a ui/ux locally to get to one? are\nwe done with this in full? have we made local and srangam ui/ux good enough for non technical amateur sanskritists to use\nthis", with the asks of 11 Nov again. Read from the exports, the screenshots, data\\jobs.jsonl, data\\text_path.json (13\nNov, 09:40 UTC), data\\source_verdicts.jsonl, both repositories\' git logs and the backup of 13 Nov (read immutable).\n\n**Done in full? No.** The dynasties wait on one step of yours (corpus-index deployed); the Gandharva English stopped at 383\npassages for a fault found today; Mallapurana\'s edition was never planned; the asks of 11 Nov after the Gandharva (R1,\nkin-long, the credit\'s steps 4 to 7) are not begun.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 13 Nov | "why dont we have prose type scholarly editions for mallapurana or a ui/ux locally to get to one?" | Found: the way is there (/desk/Mallapurana, its box "The scholarly English (the edition)": Plan, then Run; then "As prose", /scholar/Mallapurana/prose; on the site /corpus/Mallapurana/prose once the mirror sends it), but the desk\'s list called Mallapurana "Done: nothing to do". Its stage is set by its working English (993 of 1,004 passages, Hindi 993; the register "complete", 13 Nov 08:10), and no scholarly English was ever planned for it: the credit\'s plan of 9 Nov named the Nirukta, the Markandeya, the Ganita and the Natyasastra. Built DESK_SCHOLAR_NEXT_2026_11_13: a Done text without a scholarly English says so, with its verses and the measured price; its page begins with a press of 250 verses | Yours: the patch. Money: Mallapurana\'s scholarly English, 970 verses and 6 prose passages, about $25 to $44, in presses of 250 (each under $12) |\n| 13 Nov | Done in full: the dynasties | C28 pasted: B1 true, true, true, false; the change succeeded; A1 true, true, true, true, 0; A3 false, true, false, false (signed-in readers read; no one else; no one writes). The Srangam kit pushed (6d8aad4). vamsa_join: 111 lines. index_sync --apply (12 Nov, 09:43 IST) sent 37 rows, the 8 tables equal, and said "dynasties: corpus-index does not take them yet (deploy it again)". Publish does not deploy an edge function: the RUNBOOK of 11 Nov, night, step 4 said it does, and was wrong | Yours: ask Lovable, in its chat, to deploy supabase/functions/corpus-index as it is; then index_sync --apply; A2 |\n| 13 Nov | The Gandharva English | 383 passages by Sonnet: the trial, 40 (e7d6c2c0); 339 (49033e7c, 11 Nov, 22:22 to 22:58 IST); 4 (ed759396, 12 Nov). Found: the 504 left are each page\'s first passage. They begin with the edition\'s running head ("MAHARISHI UNIVERSITY OF MANAGEMENT / VEDIC LITERATURE COLLECTION"), and text_filters called any passage with "vedic literature" in it front matter, so the translator passed over them without a word, and the chart counted them as debris (57%). The same in 20 other texts of that collection. Built BANNER_HEAD_2026_11_13: on the backup of 13 Nov, 1,924 passages of 21 texts become translatable, 1,745 of them untranslated (the Gandharva 501, the Taittiriya 444, the Sukla Yajurveda 280, the Samaveda 241, the smrtis, dhanurvedas and siksas the rest); none that was translatable stops being so | Yours: the patch, the path charted again, then the Gandharva\'s 501 (about $4 to $6 of the credit, at the 383\'s $0.009 a passage) |\n| 13 Nov | The credit | .env changed by your command: $173.93 from 2026-11-11T11:53:00Z, until 2026-12-11. `--credit` (12 Nov): $5.55 spent, $168.38 left | - |\n| 13 Nov | The credit\'s steps 4 to 6, priced again | The plan of 9 Nov priced the scholarly English at $0.0128 to $0.0205 a verse; the meter (usage_log, kind scholar, Sonnet, 15 to 21 Oct) says $0.026 to $0.045: the Markandeya witness $36.65 for 1,408 verses, the Karanagama $42.19 for 1,018, the Hayasirsa $62.11 for 1,431, the Surya $22.22 for 492. Your status of the three (12 Nov): the Nirukta witness 631 verses ready, none made; the Markandeya witness 1,408 of 5,156 made (1,291 passed, 113 not: 42 serious, 71 mild; 4 source doubts); the Ganita 1,795 ready, none made | Money, at the measured price: the Nirukta about $16 to $28; the Markandeya\'s 113 read again about $3 to $5; the Ganita about $47 to $81. Step 7 held: the Gandharva edition\'s English stands in for it |\n| 13 Nov | Good enough for non-technical amateur Sanskritists? | No, not yet. On Srangam (reading) the texts, their scholarly English and its prose, the genealogies, the dynasties, the stories and the names are there for signed-in readers, and three pages explain themselves in plain words (Genealogies, a genealogy, Dynasties); but no page says where to begin, the others assume the project\'s terms, and no amateur has been watched using it. The desk (making) is an operator\'s console of 42 pages: many steps need PowerShell or SQL, and its words (Tier R, BM1, the SOP\'s flags, judge-v1) are the project\'s own | Next: U1, a "start here" for readers on Srangam; U2, the desk\'s "make a scholarly edition" in plain words (the whole text in presses, one approval of the price, then "read it as prose"); U3, three amateur Sanskritists, five tasks each, timed, and what fails mended |\n| 13 Nov | B. C. Law\'s EPUB (asked again) | Done on 10 and 11 Nov: 195 pages ($1.71), 3,409 claims, 1,929 linked; private reading. R1 is how our findings use it | - |\n| 13 Nov | R1, kin-long, the credit\'s steps 4 to 7 | Not begun: the two faults above came first | Next: R1 (about $1 to $3 of the credit); kin-long (about $1 to $2 of Google\'s cap) |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | R1 (our findings: where the Puranas, the index and the historians agree or differ); kin-long; the credit's steps 4 to 7; load-js |\n",
     '| Next | R1 (our findings: where the Puranas, the index and the historians agree or differ); kin-long; the credit\'s steps 4 to 7; load-js |\n\n## 44. 13 Nov: the page\'s first verses; Mallapurana\'s edition (DOCS109_2026_11_13)\n\n| What | State |\n|---|---|\n| Verified | C28 on the site (B1, the change, A1, A3 as expected); the Srangam kit pushed (6d8aad4); the release of DOCS108 (the automaton\'s main fbfedc7d); vamsa_join\'s 111 lines; the credit\'s lines ($168.38 left on 12 Nov) |\n| Waiting | corpus-index deployed again (index_sync: "dynasties: corpus-index does not take them yet") |\n| The asks | docs\\ASKS_2026-10-22.md section 22 |\n| Built | BANNER_HEAD_2026_11_13 (text_filters.strip_banner_head; should_translate and clean_for_mt use it); DESK_SCHOLAR_NEXT_2026_11_13 (the desk\'s next step and first press for a Done text without a scholarly English); DOCS109 |\n| Measured | 1,924 passages of 21 texts translatable that were not, 1,745 of them untranslated, 0 lost; the scholarly English $0.026 to $0.045 a verse (the meter) |\n| To do | the patches, run_tests, release; corpus-index deployed; index_sync --apply; A2; text_path.py; the Gandharva\'s 501 |\n| Next | U1 to U3 (for amateur readers and makers); R1; kin-long; the credit\'s steps 4 to 6 at the measured price; Mallapurana\'s edition when you choose; load-js |\n')

edit('RUNBOOK.md', 1, '   Open /corpus/genealogies/dynasties signed in.\n',
     '   Open /corpus/genealogies/dynasties signed in.\n\n## 13 Nov: the page\'s first verses; corpus-index; Mallapurana\'s edition (DOCS109_2026_11_13)\n\ndocs\\ASKS_2026-10-22.md, section 22. From the automaton\'s root unless said:\n\n1. The patches: `python scripts\\patch_banner_head_2026_11_13.py --check`, then without; the same for\n   `patch_docs109_2026_11_13.py`; `python -m unittest tests.test_banner_head_2026_11_13 tests.test_leak_guard_2026_10_19\n   tests.test_docs109_2026_11_13`; `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with\n   COMMIT_MSG_bannerhead_20261113.txt.\n2. The dashboard restarted when no job runs; then `python scripts\\text_path.py` (every text charted again, free: the\n   Maharishi University\'s texts lose the debris that was their pages\' first verses).\n3. corpus-index (a correction to 11 Nov, night, step 4: Publish does not deploy an edge function). In Lovable\'s chat:\n   deploy supabase/functions/corpus-index as it is in the repository, without changing its code. Then\n   `python scripts\\index_sync.py` (the plan: dynasties 114 to send), `python scripts\\index_sync.py --apply`, and A2 of\n   docs\\cloud\\C28_index_dynasties_2026-11-11.sql.\n4. The Gandharva Veda\'s rest, 501 passages: its desk page, "Translate the rest", or `/api/translate` with the engine\n   anthropic:claude-sonnet-5-5 and limit 0, as on 12 Nov.\n5. Mallapurana\'s scholarly English, when you choose (about $25 to $44): /desk/Mallapurana, "Plan them (free)" (250 verses),\n   then "Run"; again until done; then "As prose".\n')


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

