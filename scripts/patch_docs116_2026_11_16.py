#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs116_2026_11_16.py  (2026-11-17)  DOCS116_2026_11_16

Is it done? What ran on 17 Nov (the release 12d9d0c, the dashboard started again, the trial read with the second
prompt: Arjuna's line from the verses; G6b to 91 of 248 parts, stopped by a dropped connection; the 18 failed jobs done
again; the site's genealogies equal the desk's), what is left; the site's schema traced to docs\\cloud (I2: the file
docs\\cloud\\SITE_SCHEMA_2026-11-17.md, which comes beside this patch). This patch adds:

  docs/ASKS_2026-10-22.md    section 29: each ask of 17 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 51
  RUNBOOK.md                 "17 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs116_<date> copies.

  python scripts\\patch_docs116_2026_11_16.py --check
  python scripts\\patch_docs116_2026_11_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS116_2026_11_16'
TAG = 'docs116'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS115_2026_11_16', 'docs/STATE_2026-10-18.md': 'DOCS115_2026_11_16', 'RUNBOOK.md': 'DOCS115_2026_11_16'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| P4, people | The 1,325 flagged verses of the scholarly editions to a reviewer's queue (100 read so far: 99 rejected, 1 accepted); U2, U3; R1's approvals | a person's time |\n",
     '| P4, people | The 1,325 flagged verses of the scholarly editions to a reviewer\'s queue (100 read so far: 99 rejected, 1 accepted); U2, U3; R1\'s approvals | a person\'s time |\n\n## 29. 17 Nov: is it done? What ran, what is left; the site\'s schema traced (DOCS116_2026_11_16)\n\nAsked on 17 Nov, 20:47, with the ask of 16 Nov again ("IS THIS DONE"), six CSV exports of the Lovable Cloud SQL editor\n(20:27 to 20:28) and eleven screens (09:50 to 20:29: the restart, the release, the join and the sync, the trial again,\nG6b, the translations, the backups\' list, the desk and its Library). Read on the PC, read only: data\\vamsa_read (every\nstored reading), data\\jobs.jsonl, the corner worker\'s and the maintenance logs, docs\\cloud. The live database was not\nopened (the backup of 17 Nov is from 04:00, before the day\'s runs, so the day\'s spend is read from your screen).\n\n**Done in full? No.** Of the ask of 16 Nov, done: the context read again, G6a and its trial, the reader made ready and\nread again (Arjuna\'s line now runs through Vicitravirya and Pandu), the failed translations of 15 Nov done again, the\ngenealogies and the site equal, the site\'s schema traced (I2), the plan and the one pager. Not done: G6b (91 of 248\nparts read), G6c to G6f, I1 and I3 to I6, Mallapurana\'s edition, the reviewers\' queue, U2, U3 and R1.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 17 Nov | "IS THIS DONE" | No; this section and the chat of 17 Nov say what is and what is not | The rest, in the order of section 28 |\n| 17 Nov | The release of CLAUDE_KEY_FRESH, VAMSA_G6B_READY, DOCS115 | Done by you: 12d9d0c pushed (ec35aee..12d9d0c; "verified: origin/main == local HEAD"), 13 files | Done |\n| 17 Nov | The dashboard | It was not running at 09:49 ("nothing is listening on port 5057"; its last log, of 13 Nov, was written last on 15 Nov 11:14); started by you at 09:49 (dashboard_20261117_094920); the probe answered | Done |\n| 17 Nov | The trial again, the second prompt | Run by you: mbh1 203 statements, 200 verified, 3 words, $0.19. Arjuna son_of Pandu, born_of Kunti, begotten_by Sakra; Pandu son_of Vicitravirya, begotten_by Dvaipayana; Vicitravirya son_of Samtanu: the line Pratipa > Samtanu > Vicitravirya > Pandu > Arjuna > Abhimanyu is read from the verses. Parikshit son_of Abhimanyu is still "words" (his name is two verses on) | Done; Parikshit to G6d |\n| 17 Nov | G6b, the whole reading | Begun by you at about 10:00: hv, ram1, ram2, matsya, bndp1 read whole; bndp2 14 of 45 parts; mbh1 the trial\'s 2 of 16; brahma, linga1, kurma1, garuda1, agni, markp, vipc4 not begun. In all 91 of 248 parts, 3,392 of 9,029 verses, $2.90 ($0.00086 a verse). It stopped at 10:24:49 on bndp2 63_2: "ReadError: [WinError 10054] An existing connection was forcibly closed by the remote host" (a dropped connection: the run stops at the first failed call, by design; the part is read again next time) | Yours: the same command again; 157 parts, 5,637 verses, about $4.82 at the rate measured |\n| 17 Nov | The stored readings checked again; the dynasties to the site | Done by you: vamsa_join 103 lines of three persons or more (vip4 715 persons, bhp9 750, bhp12 29); index_sync sent 83 rows, deleted 6, "the site\'s genealogies equal the desk\'s (9 tables)". Your SQL of 20:27 agrees: texts 12, persons 20,221, steps 10,839, statements 22,021, claims 6,134, lines 46, verses 5,702, dynasties 106, meta 1 | Done |\n| 17 Nov | The 18 failed jobs of 15 Nov again; the Ganita and the Sama Veda | Done by you from 10:40 (one queue), as each job\'s last line says, no error in any: the Siddhanta Siromani "640/640 translated, 15 quality-skipped"; the 16 small texts 272; the Akasa Bhairava Kalpa 40; the Ganita 767 of 787 (25 quality-skipped); the Sama Veda 510 of 517 (89 quality-skipped). The queue was sent again (11:16, three texts; 19:48 and 20:31, all): a run takes only passages without English, so those found little or nothing, but the Akasa Bhairava Kalpa (limit 40) read 40 new passages each time | Yours: the credit read (the day\'s spend is not in the backup) |\n| 17 Nov | What a passage cost | Your meter at 11:1x: $48.04 spent, $125.89 left. The jobs\' last lines show $0.011 to $0.041 a passage for the 16 small texts (above section 28\'s $0.0057 to $0.0207), $0.014 for the Siddhanta Siromani, $0.004 to $0.008 for the Akasa Bhairava Kalpa | Yours: claude_engine.py --credit |\n| 17 Nov | Your SQL: the schedule and the schema | pg_cron: 7 jobs active (1, 2, 6, 7, 8, 9, 10). The 40 newest runs are all the 5-minute watchdog, each succeeded (the nightly jobs need the query without it). The schema corpus: 26 tables, 48 functions public.corpus_*. I2: each traced to the docs\\cloud file that made it, and back: nothing missing either way (docs\\cloud\\SITE_SCHEMA_2026-11-17.md). A correction to section 28: docs\\cloud holds 70 SQL files besides one draft; 13 of them make tables, 7 in the schema corpus (section 28 said 14 files) | I2 done; Srangam\'s supabase/migrations still holds none of it (the record is here) |\n| 17 Nov | The corner worker | The lock of 21:28 freed itself: the round of 00:28 ran and sent 1 mail; none skipped since | Done |\n| 17 Nov | The backups | Your list: 148.0 GB in copies made before a step and older than 14 days; nothing moved | I5: the rule, then your choice |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | P1 to P4 (section 28): Sonnet's work by 11 Dec; G6c to G6f; I1 to I6; the reviewers' queue |\n",
     "| Next | P1 to P4 (section 28): Sonnet's work by 11 Dec; G6c to G6f; I1 to I6; the reviewers' queue |\n\n## 51. 17 Nov: is it done? (DOCS116_2026_11_16)\n\n| What | State |\n|---|---|\n| Verified | 12d9d0c released; the second prompt read Arjuna's line from the verses; the site's genealogies equal the desk's (SQL); the 18 failed jobs done again; the corner lock freed |\n| The asks | docs\\ASKS_2026-10-22.md section 29 |\n| Built | docs\\cloud\\SITE_SCHEMA_2026-11-17.md (I2: 26 tables and 48 functions traced to docs\\cloud, both ways); DOCS116 |\n| Measured | G6b 91 of 248 parts, 3,392 of 9,029 verses, $2.90; a dropped connection stopped it at bndp2 63_2; 148.0 GB of pre-step backups older than 14 days |\n| Not verified | The day's Claude spend (the backup is from 04:00); the nightly pg_cron runs |\n| To do | the patch, release; G6b again; claude_engine.py --credit |\n| Next | G6c to G6f; I1, I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3, R1 |\n")

edit('RUNBOOK.md', 1, '   corner_worker.lock.stale_20261116`).\n',
     "   corner_worker.lock.stale_20261116`).\n\n## 17 Nov: is it done? G6b again; the site's schema (DOCS116_2026_11_16)\n\ndocs\\ASKS_2026-10-22.md, section 29. From the automaton's root, in PowerShell:\n\n1. The patch: `python scripts\\patch_docs116_2026_11_16.py --check`, then without; `python -m unittest\n   tests.test_docs116_2026_11_16 tests.test_docs115_2026_11_16`; release.ps1 with COMMIT_MSG_docs116_20261117.txt\n   (the dry run, then -Apply once).\n2. G6b, the rest (about $4.82): `python scripts\\vamsa_read.py --work g6` (the plan), then `python scripts\\vamsa_read.py\n   --work g6 --yes --max-usd 8`; when it stops on a dropped connection, the same command again; then\n   `python scripts\\vamsa_read.py --work g6 --report`.\n3. The day's spend: `python scripts\\claude_engine.py --credit`.\n4. Each text the queue translated, read only: `python scripts\\text_path.py --doc siddhanta_shiromani` and the same for\n   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V, sama_veda_sama_veda and AkashBhairavaKalpam.\n5. The site's schema: docs\\cloud\\SITE_SCHEMA_2026-11-17.md; its two read-only queries check it again.\n")


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

