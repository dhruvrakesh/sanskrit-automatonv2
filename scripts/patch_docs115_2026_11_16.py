#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs115_2026_11_16.py  (2026-11-16)  DOCS115_2026_11_16

The trial read (the Harivamsa 9-10 and the Mahabharata 1.90), what failed on 15 Nov (18 Sonnet jobs, a refused key,
nothing billed), Sonnet's next work priced, the desk and the site rationalised (what was found, the path P0 to P4), the
team's one pager. This patch adds:

  docs/ASKS_2026-10-22.md    section 28: each ask of 16 Nov, done or not, with its evidence; Sonnet's work; the path
  docs/STATE_2026-10-18.md   section 50
  RUNBOOK.md                 "16 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs115_<date> copies.

  python scripts\\patch_docs115_2026_11_16.py --check
  python scripts\\patch_docs115_2026_11_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS115_2026_11_16'
TAG = 'docs115'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS114_2026_11_15', 'docs/STATE_2026-10-18.md': 'DOCS114_2026_11_15', 'RUNBOOK.md': 'DOCS114_2026_11_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 15 Nov | "the commands for me to run a trial reading" | In RUNBOOK ("15 Nov, evening"): the plan, --show and --verses (free), then the Harivamsa 9-10 (Manu\'s sons, the Iksvakus: about $0.23) and the Mahabharata 1.90 (Puru\'s line to Janamejaya in prose, where Arjuna\'s line runs through Vicitravirya and Santanu: about $0.07) | Yours |\n',
     '| 15 Nov | "the commands for me to run a trial reading" | In RUNBOOK ("15 Nov, evening"): the plan, --show and --verses (free), then the Harivamsa 9-10 (Manu\'s sons, the Iksvakus: about $0.23) and the Mahabharata 1.90 (Puru\'s line to Janamejaya in prose, where Arjuna\'s line runs through Vicitravirya and Santanu: about $0.07) | Yours |\n\n## 28. 16 Nov: the trial read; what failed on 15 Nov; Sonnet\'s next work; the desk and the site rationalised (DOCS115_2026_11_16)\n\nAsked on 16 Nov, 22:03, with the screens of G5a\'s report, the release of G6a (ec35aee), the free looks at the new works\nand the trial\'s report: "what next to put claude ssonnet to work and rationalising our app and its integration with\nsrangam. are we done in full? give me a layperson\'s one pager for my erp team ... going through project documentation,\ncodebase, database and edge functions and detailed logs first to revive context and then plan this multi phase\nimplementation ... chart an enterprise path forward ... proceed with pending work". Read: the handover of 15 Nov;\nsections 25 to 27 here; ARCHITECTURE.md and ENTERPRISE_ROADMAP.md; both repositories\' .git logs (by Python, no git run);\nSrangam\'s 38 edge functions, its 66 migrations and supabase/config.toml; docs\\cloud (14 SQL files, C1 to C28); the\nbackup of 16 Nov 04:00, immutable (usage_log, scholar_translations, budget_state; the live database was not opened);\ndata\\jobs.jsonl, data\\translate_outcomes.jsonl, data\\text_path.json (charted 16 Nov 15:13); the trial\'s stored replies;\nD:\\backups (the corpus mirror\'s, the corner worker\'s and the maintenance logs, the dashboard\'s logs).\n\n**Done in full? No.** G6a is done and its trial read well; the reader is now ready for the whole reading (G6b), and the\ncause of the translations that failed on 15 Nov is mended. G6b, G6c to G6f, R1, U2, U3 and the rationalisation of the\ndesk and the site (the path below) are still ahead.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 16 Nov | The release of G6a | Done by you: ec35aee pushed (b391f48..ec35aee; "verified: origin/main == local HEAD"). The second run said "nothing to commit": nothing was left to send, nothing failed | Done |\n| 16 Nov | The trial: the Harivamsa 9-10, the Mahabharata 1.90 | Run by you: hv 6 parts, 175 statements (151 verified, 20 words, 3 unsupported, 1 bad), $0.18; mbh1 2 parts, 181 (173, 7, 1, 0), $0.16. Read: most "words" were a name given with the word that tells it apart (Manu Vaivasvata, 10 of hv\'s 20), a father named two verses back, or an avagraha (\'mbika, \'mrtam); lines broke where a mother was taken for a father (Rathamtari > Duhsanta) and where the verse names the begetter (Pandu son_of Dvaipayana, Arjuna son_of Kunti: Arjuna\'s line still runs through Vyasa) | Mended below |\n| 16 Nov | The screen: "--chapters 1-2" and "nothing to read" | Found: when all that was asked was read, NEXT named chapters 1-2, which hv and mbh1 do not have; the run then said "nothing to read: every part asked for is read"; --report without --work showed G5a\'s three only | Mended (VAMSA_G6B_READY) |\n| 16 Nov | "proceed with pending work": G6b made ready | Built VAMSA_G6B_READY_2026_11_16 (vamsa_read.py): the works of G6 read with a second prompt (vamsa-read-v2: son_of the father, born_of the mother, begotten_by a begetter whose child the text counts as another man\'s); G5a\'s three keep the first and are not read again; a part read again keeps its first reading beside it. The checks: a name by each of its words, an avagraha read as its a, a pronoun\'s person two verses back, a statement whose words are in another verse of its part takes that verse. Measured on the stored readings: 108 statements become verified (G5a 88: vip4 30, bhp9 57, bhp12 1; hv 14; mbh1 6), 2 unsupported become words, none goes down; mbh1\'s longest line from 17 to 24 persons (Puru to Ajamidha). Not mended here: one person by two names (Vrkodara for Bhimasena, Paryasravas for Pratipa) and two persons of one name in a chapter (Arugvan\'s Pariksit and Abhimanyu\'s): G6d | Yours: the patch, --reparse (free), the trial again (about $0.34), then G6b |\n| 16 Nov | Found in the logs: the translations of 15 Nov | data\\jobs.jsonl: 18 Sonnet jobs started from the dashboard on 15 Nov, 09:54 to 10:19 (16 small texts, the Siddhanta Siromani\'s 640 passages, 40 of the Akasa Bhairava Kalpa), each "Done. N/N translated, N quality-skipped" with "empty after a paid call"; data\\translate_outcomes.jsonl: 952 empty answers; 13 of the 18 logs show "401 invalid x-api-key" (the other 5 end before it); usage_log: no row for any of them, nothing billed. The cause: the dashboard, started on 13 Nov 22:35 (its last log in D:\\backups\\dashboard_logs), keeps the key it started with; its jobs inherit it; python-dotenv does not replace a key already set (override=False); the scholarly runs from PowerShell had the new key. Built CLAUDE_KEY_FRESH_2026_11_16 (claude_engine.py): each Client reads the key from .env again and uses it when it differs; a refused key is said once | Yours: the patch, the dashboard restarted when no job runs, the 18 jobs again |\n| 16 Nov | "what next to put claude sonnet to work" | Planned and priced below, from the rates usage_log measured | Yours, in that order |\n| 16 Nov | "rationalising our app and its integration with srangam" | Read; the findings and the path below | I1 to I6 |\n| 16 Nov | "a layperson\'s one pager for my erp team" | Written as a Claude doc: "The Sanskrit desk and Srangam: what is new, 14 to 16 Nov" (https://claude.ai/artifact/UGG6uRRMsfqBSk1pCgLQo2): the two systems, the family-line reader step by step, a mended scan, the site\'s pages, five rules that save money, what is not ready | Done |\n| 16 Nov | The corner worker | Its log: no round finished after 21:28; data\\corner_worker.lock was taken at 21:28:14 by process 40108; the rounds of 21:38 to 22:08 were skipped ("another run is going"); the lock counts as stale after 3 hours (00:28) | Yours: the check in RUNBOOK |\n\n**Sonnet\'s next work, in order** (the Claude credit: $128.92 left on 16 Nov, 20:35, to 11 Dec; the rates are usage_log\'s):\n\n| # | Work | Before it | Rate measured | About |\n|---|---|---|---|---|\n| 1 | The trial again with the second prompt: hv 9-10, mbh1 90 | the two patches; the dashboard restarted | $0.18 and $0.16 (15 and 16 Nov) | $0.34 |\n| 2 | G6b: the 14 works, 9,029 verses (8,753 not read) | the trial: Arjuna\'s line through Vicitravirya and Pandu; three in four verified | $0.0010 a verse (hv, G5a), $0.0017 (mbh1) | $9 to $15 |\n| 3 | The 18 jobs of 15 Nov again, 952 passages | the restart; the probe | $0.0057 to $0.0207 a passage (Sonnet\'s working English by text) | $6 to $20 |\n| 4 | The Ganita\'s 963 passages without English | its pick: ready (15 Nov) | $0.0064 a passage (its own 93) | about $6 |\n| 5 | The Sama Veda\'s working English, 530 passages | its pick: ours (15 Nov) | $0.006 to $0.014 | $3 to $8 |\n| 6 | Mallapurana\'s edition, the rest (827 of 1,004 verses) | a person reads 20 of its 54 flagged first (177 made, 54 flagged) | $0.0457 a verse | about $38 |\n\nIn all about $62 to $87; $42 to $67 would be left for the Akasa Bhairava Kalpa (2,805 passages, about $17 at $0.006), the\nNirukta\'s edition, or kept. Google\'s cap: $148.73 of $160 spent this month (maintenance log, 16 Nov), so the Hindi and\nthe judge (Gemini) wait for 1 Dec.\n\n**The desk and the site: what was found.**\n- Two of Srangam\'s edge functions call the Lovable AI gateway (detect-duplicate-articles: google/gemini-2.5-flash;\n  suggest-tag-categories: google/gemini-3-flash-preview), against your rule (your own Gemini, then OpenAI key;\n  _shared/ai-provider.ts does that for the others).\n- The site\'s tables for the desk (corpus.docs, passages, translations, the index_ tables, index_dynasties ...) were made\n  by the 14 SQL files of docs\\cloud in the Lovable Cloud SQL editor; Srangam\'s supabase/migrations has 66 files, the\n  last of 10 Sep: the site\'s repository does not describe the database it runs on.\n- ARCHITECTURE.md and ENTERPRISE_ROADMAP.md (August) describe a desk of Gemini and OpenAI: no Claude engine, no shelf\n  (kin.db, claims.db, vamsa.db), none of the four scheduled tasks, no Srangam.\n- The repository holds 190 scripts beside 330 applied patchers, 797 .bak copies, 130 commit-message files at its root\n  and 253 test modules; dashboard.py is 7,317 lines. Srangam\'s root holds 24 patch scripts and SQL files.\n- D:\\backups: 143 files and 5 folders, 210 GB of files: 14 nightly copies, 32 GB; 115 copies made before a step,\n  175 GB (the largest kinds: pre_witness 38 GB, pre_reingest 37 GB, pre_repair 26 GB).\n- The integration itself runs: the corpus mirror at 20:33 (374 groups equal), the media, the genealogies (9 tables\n  equal), the corner worker every 10 minutes (tonight\'s lock apart).\n\n**The path ahead.**\n\n| Phase | What | Gate |\n|---|---|---|\n| P0, today, free | The patches CLAUDE_KEY_FRESH, VAMSA_G6B_READY, DOCS115; the tests; the release; the dashboard restarted when idle; the probe; --reparse; the corner lock | run_tests: no new failure; the probe answers |\n| P1, to 11 Dec, the credit | Sonnet\'s work 1 to 6 above | each begun by its trial; the credit read before each |\n| P2, free builds | G6c the same dynasty across the works, generation by generation; G6d one person register (two names of one person, one name of two); G6e one page model, the desk\'s Dynasties page, then the site; G6f with R1 our findings on a line, approved by a person | G6b read; G6d before anything of G6 goes to the site |\n| P3, the integration | I1 the two edge functions on ai-provider.ts (a Srangam kit); I2 the site\'s schema recorded: docs\\cloud catalogued, a read-only parity check in the SQL editor; I3 ARCHITECTURE.md written for the system as it is; I4 a tidy round: applied patchers, .bak copies and commit-message files older than 30 days moved (not deleted) to _archive, after the replay tests learn to skip without them; I5 a rule for D:\\backups (14 nightly copies, pre-step copies 14 days), listed before anything moves; I6 a run that sent nothing billable and translated nothing says FAIL, not Done; the health watch shows a stale lock and a dashboard older than .env | each a patch with its test; I5 only after you read its list |\n| P4, people | The 1,325 flagged verses of the scholarly editions to a reviewer\'s queue (100 read so far: 99 rejected, 1 accepted); U2, U3; R1\'s approvals | a person\'s time |\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | G6b (the reading, after the trial), G6c to G6f; R1; kin-long; U2, U3; the free prose view of the working English |\n',
     "| Next | G6b (the reading, after the trial), G6c to G6f; R1; kin-long; U2, U3; the free prose view of the working English |\n\n## 50. 16 Nov: the trial read; what failed on 15 Nov (DOCS115_2026_11_16)\n\n| What | State |\n|---|---|\n| Verified | The release of G6a (ec35aee); the trial (hv 151 of 175 verified, mbh1 173 of 181, $0.34); the corpus mirror and the genealogies equal (16 Nov 20:33) |\n| The asks | docs\\ASKS_2026-10-22.md section 28 |\n| Built | CLAUDE_KEY_FRESH_2026_11_16 (claude_engine.py); VAMSA_G6B_READY_2026_11_16 (vamsa_read.py: the second prompt for G6, the checks, the lines, the NEXT lines); DOCS115 |\n| Measured | 108 statements verified more on --reparse, none fewer; 952 passages of 15 Nov unread for a refused key, nothing billed; D:\\backups 210 GB (175 GB of it copies made before a step); the credit $128.92 to 11 Dec |\n| Not verified | The second prompt has read nothing yet (the trial again is the first); whether the home page's kit was published in Lovable |\n| To do | the patches, run_tests, release; the dashboard restarted; the trial again; G6b; the 18 jobs again |\n| Next | P1 to P4 (section 28): Sonnet's work by 11 Dec; G6c to G6f; I1 to I6; the reviewers' queue |\n")

edit('RUNBOOK.md', 1, '   site.\n',
     "   site.\n\n## 16 Nov: the Claude key read fresh; the reader ready for G6b (DOCS115_2026_11_16)\n\ndocs\\ASKS_2026-10-22.md, section 28. From the automaton's root, in PowerShell:\n\n1. The patches and the tests: `python scripts\\patch_claude_key_fresh_2026_11_16.py --check`, then without; the same\n   for `patch_vamsa_g6b_ready_2026_11_16.py` and `patch_docs115_2026_11_16.py`; `python -m unittest\n   tests.test_claude_key_fresh_2026_11_16 tests.test_vamsa_g6b_ready_2026_11_16 tests.test_vamsa_g6a_2026_11_15\n   tests.test_vamsa_read_2026_11_11 tests.test_vamsa_join_2026_11_11 tests.test_desk_fresh_2026_11_11\n   tests.test_claude_engine_2026_10_15 tests.test_docs115_2026_11_16`; `powershell -ExecutionPolicy Bypass -File\n   scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_g6bready_20261116.txt (the dry run, then -Apply).\n2. The dashboard, when no job runs: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1\n   -Status`, then `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1`; then\n   `python scripts\\claude_engine.py --probe` and `python scripts\\claude_engine.py --credit`.\n3. Free: `python scripts\\vamsa_read.py --reparse` (G5a's three), `python scripts\\vamsa_read.py --work g6 --reparse`,\n   `python scripts\\vamsa_read.py --report`, `python scripts\\vamsa_join.py`, `python scripts\\index_sync.py` (the plan:\n   the dynasties' rows that would change; the scheduled mirror sends them).\n4. The trial again (about $0.34): `python scripts\\vamsa_read.py --work hv --chapters 9-10 --yes --max-usd 0.50`;\n   `python scripts\\vamsa_read.py --work mbh1 --chapters 90 --yes --max-usd 0.50`; `python scripts\\vamsa_read.py --work\n   mbh1 --report`. Good: Pandu son_of Vicitravirya and begotten_by Dvaipayana; three in four verified.\n5. G6b: `python scripts\\vamsa_read.py --work g6` (the plan), then `python scripts\\vamsa_read.py --work g6 --yes\n   --max-usd 15`.\n6. The 18 jobs of 15 Nov again, through the dashboard (/api/translate, engine anthropic:claude-sonnet-5-5): the loop is\n   in the chat of 16 Nov.\n7. The corner lock: `Get-Content data\\corner_worker.lock`; `Get-Process -Id 40108 -ErrorAction SilentlyContinue`. No\n   such process: the lock frees itself at 00:28, or rename it (`Rename-Item data\\corner_worker.lock\n   corner_worker.lock.stale_20261116`).\n")


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

