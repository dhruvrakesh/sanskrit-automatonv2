#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs122_2026_11_18.py  (2026-11-18)  DOCS122_2026_11_18

18 Nov, night: every work on the site (the send of 412 rows; 17 works, 517 rows), the task's last step, P2b pushed;
P5: the genealogies' road written down. Adds:

  docs/ASKS_2026-10-22.md    section 34: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 56
  RUNBOOK.md                 "18 Nov, night": the commands in order
  ARCHITECTURE.md            "The genealogies' road": read, align, register, join, send, show; the rules

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs122_<date> copies.

  python scripts\\patch_docs122_2026_11_18.py --check
  python scripts\\patch_docs122_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS122_2026_11_18'
TAG = 'docs122'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'ARCHITECTURE.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS121_2026_11_18', 'docs/STATE_2026-10-18.md': 'DOCS121_2026_11_18', 'RUNBOOK.md': 'DOCS121_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 18 Nov | Done in full? | No: the send of every (after Publish), P2c (each line tagged with its dynasty and vamsa on the desk, then a way in by Suryavamsa and Candravamsa), P3 (the desk's Vamsa page), P4 (G6f with R1), P5 (ARCHITECTURE.md) | In that order |\n",
     '| 18 Nov | Done in full? | No: the send of every (after Publish), P2c (each line tagged with its dynasty and vamsa on the desk, then a way in by Suryavamsa and Candravamsa), P3 (the desk\'s Vamsa page), P4 (G6f with R1), P5 (ARCHITECTURE.md) | In that order |\n\n## 34. 18 Nov, night: every work on the site; the road written down (DOCS122_2026_11_18)\n\nAsked on 18 Nov, 21:21, with three CSV exports of the Lovable Cloud SQL editor (21:19 to 21:20) and four screens (17:37\nto 21:2x), the standing ask again. Read on the PC, read only: the release log, scripts\\corpus_mirror_task.ps1,\nARCHITECTURE.md, Srangam\'s .git (main at 72e109bf33) and its supabase\\functions\\_shared\\ai-usage.ts. Read on the\nlive site: https://srangam.nartiang.org/ and three of its files (index-DCdTjC-a.js, CorpusDynasties-D2CZ5603.js,\nindexSite-DKfqdnMs.js). Nothing on the PC was run.\n\n**Done in full? No.** Done today: P1, P2a, P2b (published: the live site carries it), the send of every work, the task\'s last step;\ntonight P5 (the road\nwritten down in ARCHITECTURE.md) and the team\'s page brought up to date. Left: P2c, P3, P4.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 18 Nov | The release of P2b\'s kit, the task patch, DOCS121 | Done by you: d7c6eda9 pushed (ded5ed5..d7c6eda, 17 files; "verified: origin/main == local HEAD (d7c6eda9)"); it carried data\\vamsa_read\\dynasties_every.json | Done |\n| 18 Nov | P2b on Srangam | Done by you: the kit applied; the build passed in 1 min 12 s; 72e109b pushed (eae2901..72e109b, 5 files, 171 insertions, 28 deletions). Published: the live site\'s CorpusDynasties-D2CZ5603.js carries "No dynasty of this text has been sent from the desk yet." and the query key index-dynasties; its indexSite-DKfqdnMs.js carries all 17 work codes (read 18 Nov, night). The typecheck\'s and vitest\'s output are not in the screens | Done |\n| 18 Nov | The task\'s last step | Done by you: corpus_mirror_task.ps1 lines 40 and 43 carry VAMSA_EVERY_2026_11_18 and --dynasty-works every (Select-String) | Done |\n| 18 Nov | The send of every work | Done by you: the plan "dynasties here 517, there 106: 411 to send, 0 to delete"; the send "sent 412 row(s) (412 changed), deleted 0; the site\'s genealogies equal the desk\'s (9 tables)" | Done |\n| 18 Nov | The site, after the send | Your SQL of 21:19: 17 works, 517 rows. The 14 new works sent 18 Nov 15:49 UTC: agni 41 rows (38 kB), bndp1 7, bndp2 58 (59 kB), brahma 40, garuda1 48, hv 49 (53 kB), kurma1 33, linga1 18, markp 6, matsya 39, mbh1 13, ram1 8, ram2 3, vipc4 48 (60 kB); vip4 50, bhp9 48, bhp12 8 as before | Done |\n| 18 Nov | Who may read it | Your SQL of 21:20: corpus.reader_access mode readers, since 2026-10-09 01:29 UTC: admins, super admins, the listed readers and researchers; not the public | Your decision, unchanged |\n| 18 Nov | I1, the first call | Your SQL: still no row for detect-duplicate-articles or suggest-tag-categories in public.srangam_ai_usage (the ledger that supabase\\functions\\_shared\\ai-usage.ts writes) | You: "suggest categories" once |\n| 18 Nov | The team\'s page | Brought up to date (rev 3): all 17 works on the site, one text at a time; who may see it; plain spellings found since 18 Nov; the status | Done |\n| 18 Nov | P5, the road written down | Built: ARCHITECTURE.md, "The genealogies\' road": read, align, register, join, send, show; what each reads and writes, what it costs, the rules (only the reading spends; every send carries --dynasty-works every) | You: this patch |\n| 18 Nov | Done in full? | No: P2c (each line tagged with its dynasty and vamsa, a way in by Suryavamsa and Candravamsa), P3 (the 17 works on the desk\'s Vamsa page), P4 (a review list for the 44 proposed names and the 672 kept apart) | In that order |\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | P2c; P3; P4; P5 |\n',
     '| Next | P2c; P3; P4; P5 |\n\n## 56. 18 Nov, night: every work on the site (DOCS122_2026_11_18)\n\n| What | State |\n|---|---|\n| Verified | d7c6eda9 released; 72e109b pushed and published (the live chunks); the send: 412 rows, 0 deleted, the site equal to the desk (9 tables); the site: 17 works, 517 rows; reader_access: readers |\n| The asks | docs\\ASKS_2026-10-22.md section 34 |\n| Built | ARCHITECTURE.md, "The genealogies\' road" (P5); DOCS122; the team\'s page, rev 3 |\n| Not verified | the typecheck\'s and vitest\'s output of 72e109b; the two AI functions\' first call (public.srangam_ai_usage) |\n| To do | the patch, release |\n| Next | P2c; P3; P4 |\n')

edit('RUNBOOK.md', 1, '   `python scripts\\index_sync.py --dynasty-works every --apply`; the SQL of section 33 again (17 works, 517 rows).\n',
     '   `python scripts\\index_sync.py --dynasty-works every --apply`; the SQL of section 33 again (17 works, 517 rows).\n\n## 18 Nov, night: every work on the site; the road written down (DOCS122_2026_11_18)\n\ndocs\\ASKS_2026-10-22.md, section 34. From the automaton\'s root, in PowerShell:\n\n1. The patch: `python scripts\\patch_docs122_2026_11_18.py --check`, then without; `python -m unittest\n   tests.test_docs122_2026_11_18`; release.ps1 with COMMIT_MSG_docs122_20261118.txt (the dry run, then -Apply once).\n2. The live build, after any later Publish: fetch https://srangam.nartiang.org/, its /assets/index-*.js, the CorpusDynasties chunk it names,\n   and look for "No dynasty of this text has been sent from the desk yet." (the probe in the chat of 18 Nov, night).\n')

edit('ARCHITECTURE.md', 1, '  semantic fidelity certification. Designed in `QUALITY_LOOP_DESIGN`, not yet built.\n',
     '  semantic fidelity certification. Designed in `QUALITY_LOOP_DESIGN`, not yet built.\n\n## The genealogies\' road (DOCS122_2026_11_18, 18 Nov 2026)\n\nHow the lines of kings travel from the Sanskrit verses to the desk and to the site. Only the first step spends.\n\n| Step | Where | Reads | Writes | Cost |\n|---|---|---|---|---|\n| 1. Read | scripts\\vamsa_read.py (G5a, G6a, G6b) | the genealogical chapters of 17 works on this PC (vip4, vipc4, bhp9, bhp12, hv, ram1, ram2, mbh1, matsya, brahma, bndp1, bndp2, linga1, kurma1, garuda1, agni, markp) | data\\vamsa_read\\<work>\\*.json: kinship statements, each checked by machine against its verse (verified, words, unsupported, bad) | paid: Claude Sonnet (claude-sonnet-5-5), prompt vamsa-read-v1 for vip4, bhp9, bhp12 and v2 for the rest; 323 calls, $11.19 to 18 Nov; a run resumes where it stopped |\n| 2. Align | scripts\\vamsa_align.py (G6c) | step 1 | exports\\vamsa_align.md and .csv; data\\vamsa_read\\aligned.json | free |\n| 3. Register | scripts\\vamsa_register.py (G6d; VAMSA_NAMES) | steps 1 and 2 | data\\vamsa_read\\register.json; exports\\vamsa_register.csv and .md | free |\n| 4. Join | scripts\\vamsa_join.py (G5b; VAMSA_SITE) | step 1; data\\shelf\\kin.db (the Purana Index, kin_index.py); data\\context.db | data\\vamsa_read\\dynasties.json (vip4, bhp9, bhp12), dynasties_every.json (--work every) | free |\n| 5. Send | scripts\\index_sync.py --dynasty-works every; nightly from scripts\\corpus_mirror_task.ps1 | step 4 and the indexes (kin.db, vamsa.db, claims.db) | Srangam\'s nine corpus.index_* tables through the edge function corpus-index (the dynasties in corpus.index_dynasties, docs\\cloud\\C28); only rows whose row_hash changed | free |\n| 6. Show, site | public.corpus_reader_index_dynasties(p_work), behind corpus._reader_gate; /corpus/genealogies/dynasties asks for one work at a time (Srangam\'s DYNASTIES_WORKS_2026_11_18) | step 5 | nothing | free |\n| 6. Show, desk | /vamsa (scripts\\vamsa.html; /api/vamsa through scripts\\vamsa_view.py, read only) | kin.db, vamsa.db, context.db | nothing | free |\n\nThe rules of the road:\n- The site shows what the desk last sent: on 18 Nov, 17 works and 517 rows. Every send carries --dynasty-works every\n  (the nightly task does since VAMSA_EVERY_2026_11_18); a send without it takes the 14 works of G6 off the site.\n- Who may read on the site: corpus_reader_allowed() (admins and super admins; corpus.reader_access\'s mode, "readers"\n  since 9 Oct: the listed readers and researchers). The public may not; changing that is the owner\'s decision.\n- What is shown is what the texts state, each step with its verse. A join of two works\' persons is ours (one name, one\n  father and, where both give him, one grandfather); a second name only where a verse says it; names that differ are\n  shown side by side, never ruled on.\n- Not yet on the road: a dynasty and vamsa on each line, for a way in by Suryavamsa and Candravamsa (P2c); the 17 works\n  on the desk\'s /vamsa page (P3); a review list for the proposed names and the names kept apart (P4).\n')


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

