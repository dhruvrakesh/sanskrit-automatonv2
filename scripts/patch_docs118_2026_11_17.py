#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs118_2026_11_17.py  (2026-11-17)  DOCS118_2026_11_17

17 Nov, late: I1 live (eae2901, deployed by Lovable; no call of the two functions yet), the automaton released
(d5fca11), G6b running (206 of 248 parts at 22:46), G6d built (scripts\\vamsa_register.py: one register of the persons
of every work read; the two Parikshits kept two, Bhishma one in 8 works); G6e and G6f designed, not built. Adds:

  docs/ASKS_2026-10-22.md    section 31: each ask of 17 Nov, late, done or not, with its evidence; G6e's design
  docs/STATE_2026-10-18.md   section 53
  RUNBOOK.md                 "17 Nov, late": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs118_<date> copies.

  python scripts\\patch_docs118_2026_11_17.py --check
  python scripts\\patch_docs118_2026_11_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS118_2026_11_17'
TAG = 'docs118'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS117_2026_11_17', 'docs/STATE_2026-10-18.md': 'DOCS117_2026_11_17', 'RUNBOOK.md': 'DOCS117_2026_11_17'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '  Dynasties page, then the site) and G6f (with R1, our findings on a line).\n',
     '  Dynasties page, then the site) and G6f (with R1, our findings on a line).\n\n## 31. 17 Nov, late: I1 live, G6b running, G6d built; G6e and G6f next (DOCS118_2026_11_17)\n\nAsked on 17 Nov, 22:41, with exports\\vamsa_align.md, three CSV exports of the Lovable Cloud SQL editor (22:37 to\n22:39) and three screens (the Srangam build and push, Lovable\'s deploy, the SQL editor): "1. Finish G6b (about\n$2.95). 2. G6d, the person register (free). 3. G6e: one shared layout for dynasty pages, used on the desk\'s Dynasties\npage and then on the site. 4. G6f with R1: our findings on each line." Read on the PC, read only: data\\vamsa_read\n(G6b writing to it as it was read), the automaton\'s and Srangam\'s git logs (read as files).\n\n**Done in full? No.** Done tonight: I1 is live (released and deployed by you); G6c run by you; G6d built and tested\nhere. Running: G6b, on your PC. Not built: G6e and G6f (their design below).\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 17 Nov | I1 released and deployed | Your screens: eae2901 pushed (de1e346..eae2901; 4 files, 134 insertions, 68 deletions; the build passed in 34.22 s); Lovable "deployed detect-duplicate-articles and suggest-tag-categories exactly as they are at commit eae2901", without errors, and sent neither a test request | Done; their first call shows in srangam_ai_usage |\n| 17 Nov | I1, the ledger | Your SQL of 22:37 to 22:39: in 30 days the project\'s AI calls were gemini-2.5-flash, 120 succeeded (the last 17 Nov 03:01 UTC) and 1 failed (23 Oct); no OpenAI call; the two functions: no row (neither called since the deploy) | You: "suggest categories" once on the admin\'s tag page, then the SQL again |\n| 17 Nov | The automaton released | d5fca11 (G6c, the I1 kit, DOCS117) | Done |\n| 17 Nov | G6c run | By you at 22:27: exports\\vamsa_align.md and its 10 CSV files; the same 10 dynasties and counts as section 30 | Again when G6b ends |\n| 17 Nov | Your CSV: pg_cron | Jobs 2, 6, 7, 8, 9 and 10 each succeeded on 16 and 17 Nov (03:00 to 04:40 UTC) | Done |\n| 17 Nov | G6b, finish | Running on your PC: at 22:46, 206 of 248 parts (linga1, kurma1, garuda1, agni and markp read whole; mbh1 7 of 16; vipc4 0 of 33) | Its end (mbh1 9 parts, vipc4 33); then --report |\n| 17 Nov | G6d, the person register | Built: scripts\\vamsa_register.py (VAMSA_REGISTER_2026_11_17), free and read-only of the readings; writes data\\vamsa_read\\register.json, exports\\vamsa_register.csv and exports\\vamsa_register.md. tests\\test_vamsa_register_2026_11_17.py: 10 tests OK | You: run it when G6b ends |\n| 17 Nov | G6d, how | One person in two works is one entry when his names, his father and (where both works give him) his grandfather meet; where a grandfather is not given, when G6c sets the two in one generation of one dynasty, else on name and father alone; an entry never holds two grandfathers that differ, nor two persons of one work whose fathers differ, so no join goes through a third. A son named by "words" (the name not in the verse) is taken as a father only when a verified statement names him so in that chapter or the next. Two names said in a verse (vamsa_align\'s "other" statements) give one entry both, for the person, his father and his grandfather. Two names in one generation between one father and one son are proposed, never joined | Done |\n| 17 Nov | G6d, measured | On a copy of the readings of 22:46 (16 works): 5,672 persons in 3,289 entries; 1,062 in two works or more, 559 in three or more; joined 1,658 by name, father and grandfather, 24 by one generation of a dynasty, 701 by name and father; 580 pairs of one name kept as two; 24 second names said in a verse; 39 proposed; 111 persons rest on words | Again when G6b ends |\n| 17 Nov | G6d, the two Parikshits | Kept two: Abhimanyu\'s son is one entry in 7 works (bhp9, hv, matsya, brahma, garuda1, agni, and mbh1 1,90.90, which rests on words); Arugvan\'s son (MBh 1,90.43) stands alone; Kuru\'s son is a third (6 works). The Janamejayas likewise: Abhimanyu\'s grandson (bhp9, matsya, garuda1, mbh1 1,90.93), Kuru\'s grandson (vip4, hv), Puru\'s son, Somadatta\'s son, apart | Done |\n| 17 Nov | G6d, the double names | Bhishma is one entry in 8 works, Devavrata in hv, matsya, brahma and mbh1: the Adiparvan\'s grandfather Paryasravas is Pratipa by its own verse ("yam ahuh pratipam nama"). That Paryasravas is kept apart from the Puranas\' Pratipa: his grandfather there is Parikshit, theirs Rksa (one person told two ways, or two). Vrkodara: the readings give him only as Kunti\'s son begotten by Vayu (agni, bndp2; matsya in words); no verse read says he is Bhimasena, so he is not joined | G6f with R1 |\n| 17 Nov | G6e, G6f with R1 | Not built (designed below) | Next |\n\nG6e, the design: one page model and two pages drawing it.\n- scripts\\vamsa_pages.py (free): from G6c and G6d, for each dynasty its generations, each cell an entry of the\n  register with its names, verses and standing (agree, most, differ, one); for each entry of two works or more a\n  person page: names, father, sons, works and verses, the names kept apart from him, the names proposed for him.\n- The desk: a Dynasties page on the dashboard (one route and one HTML file, as /vamsa is), reading that model.\n- The site: the same model sent by index_sync to a new table (a docs\\cloud C file) and drawn by the site\'s Dynasties\n  page (a Srangam kit); the present page (G5a\'s three works joined to the Purana Index) stays until then.\nG6f with R1: on each line, where the works part, our reading beside the texts\' (the proposed names, the grandfathers\nthat differ), each approved or not by you, and never shown as the text\'s word.\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G6d (designed in section 30); G6e, G6f; I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3, R1 |\n",
     '| Next | G6d (designed in section 30); G6e, G6f; I3 to I6; Mallapurana\'s edition; the reviewers\' queue; U2, U3, R1 |\n\n## 53. 17 Nov, late: I1 live, G6d built (DOCS118_2026_11_17)\n\n| What | State |\n|---|---|\n| Verified | I1: eae2901 built, pushed, deployed by Lovable; the ledger reads (no call of the two yet); d5fca11 released; pg_cron\'s 6 nightly jobs succeeded on 16 and 17 Nov; G6d on a copy (10 tests) |\n| The asks | docs\\ASKS_2026-10-22.md section 31 |\n| Built | scripts\\vamsa_register.py (G6d); DOCS118 |\n| Measured | G6b 206 of 248 parts at 22:46, running; G6d 5,672 persons in 3,289 entries, 1,062 in two works or more |\n| Not verified | The two functions\' first call on the own keys (none yet); G6b\'s end and its cost |\n| To do | the patch, release; G6b\'s end, --report; vamsa_align, vamsa_register; one "suggest categories" and the SQL |\n| Next | G6e (designed in section 31); G6f with R1; I3 to I6; Mallapurana\'s edition; the reviewers\' queue; U2, U3 |\n')

edit('RUNBOOK.md', 1, '5. The credit: `python scripts\\claude_engine.py --credit`.\n',
     '5. The credit: `python scripts\\claude_engine.py --credit`.\n\n## 17 Nov, late: G6d, the person register; I1 checked (DOCS118_2026_11_17)\n\ndocs\\ASKS_2026-10-22.md, section 31. From the automaton\'s root, in PowerShell:\n\n1. The patch: `python scripts\\patch_docs118_2026_11_17.py --check`, then without; `python -m unittest\n   tests.test_vamsa_register_2026_11_17 tests.test_docs118_2026_11_17 tests.test_docs117_2026_11_17\n   tests.test_vamsa_align_2026_11_17`; release.ps1 with COMMIT_MSG_g6d_20261117.txt (the dry run, then -Apply once).\n2. G6b: let it end; if it stopped on a dropped connection, `python scripts\\vamsa_read.py --work g6 --yes --max-usd 8`\n   again; then `python scripts\\vamsa_read.py --work g6 --report`.\n3. G6c and G6d again, free: `python scripts\\vamsa_align.py`, then `python scripts\\vamsa_register.py`; on screen,\n   writing nothing: `python scripts\\vamsa_register.py --name Pariksit`, `--name Janamejaya`, `--name Devavrata`,\n   `--stats`; then exports\\vamsa_register.md.\n4. I1: on the site\'s admin tag page, "suggest categories" once; then in the Lovable Cloud SQL editor the query of\n   section 31\'s ledger row again: srangam_ai_usage by function_name, purpose, provider, model, ok.\n5. The credit: `python scripts\\claude_engine.py --credit`.\n')


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

