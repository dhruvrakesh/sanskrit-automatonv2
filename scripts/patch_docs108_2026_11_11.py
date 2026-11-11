#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs108_2026_11_11.py  (2026-11-11)  DOCS108_2026_11_11

The dynasties joined to the Purana Index (VAMSA_JOIN), the database change (C28) and the Dynasties page (the Srangam kit
DYNASTIES). This patch adds:

  docs/ASKS_2026-10-22.md    section 21: each ask of 11 Nov (night), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 43
  RUNBOOK.md                 "11 Nov, night": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs108_<date> copies.

  python scripts\\patch_docs108_2026_11_11.py --check
  python scripts\\patch_docs108_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS108_2026_11_11'
TAG = 'docs108'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS107_2026_11_11', 'docs/STATE_2026-10-18.md': 'DOCS107_2026_11_11', 'RUNBOOK.md': 'DOCS107_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 11 Nov | For a select audience | The site lets researchers in by invitation (rbac: invitations, roles, the audit; Kanika and Parth accepted theirs); the reader functions need a signed-in user; the mode "readers" is there when wanted (docs\\PLATFORM_2026-10-04.md) | The dynasties and the findings reach them with G5c and R1 |\n',
     '| 11 Nov | For a select audience | The site lets researchers in by invitation (rbac: invitations, roles, the audit; Kanika and Parth accepted theirs); the reader functions need a signed-in user; the mode "readers" is there when wanted (docs\\PLATFORM_2026-10-04.md) | The dynasties and the findings reach them with G5c and R1 |\n\n## 21. 11 Nov, night: the dynasties joined to the index and made a page (DOCS108_2026_11_11)\n\nAsked at 21:27 with the release of VAMSA_HEAL, the report, the credit, the four tasks and H1\'s export: "join the\ndynasties to the index\'s people (free), then the database change and the Dynasties page, then the Gandharva English\nafter the trial", with the asks of 10 Nov again. Read from your screenshots, H1\'s export (21:28), data\\jobs.jsonl, the\nGRETIL readings (data\\vamsa_read), kin.db and the backup of 11 Nov (read immutable).\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 11 Nov | The dynasties joined to the index\'s persons (G5b) | Built VAMSA_JOIN_2026_11_11: scripts\\vamsa_join.py finds each person of a line in the Purana Index, by the father the index gives him, else by a name it has once; a line\'s root named in another chapter is joined by the index. On the backup of 11 Nov and kin.db: Visnupurana 4, 715 persons, 528 found (493 with the same father), 33 with another father there, 187 not in it; Bhagavatapurana 9, 716, 506 found (481), 20, 210; 12.1, 29, 18 (16), 2, 11. 111 lines of three persons or more; the longest: the Vrsnis, Kratha to Yugandhara (29) | Yours: `python scripts\\vamsa_join.py` |\n| 11 Nov | The database change (G5c) | Built C28_INDEX_DYNASTIES_2026_11_11 (docs\\cloud\\C28_index_dynasties_2026-11-11.sql): the table corpus.index_dynasties, C26\'s ingest and manifest kept and a door put before them, the reader corpus_reader_index_dynasties for signed-in readers; tested on PostgreSQL 16 on top of C21, C23 and C26, twice (it changes nothing the second time), C26\'s tables untouched. index_sync.py sends the table as it sent the claims: only when the site has it and corpus-index takes it | Yours: B1, the change, A1, A3; then the Srangam kit; then `index_sync.py --apply` and A2 |\n| 11 Nov | The Dynasties page | Built the Srangam kit DYNASTIES_2026_11_11 (docs\\srangam\\DYNASTIES_2026-11-11): /corpus/genealogies/dynasties for signed-in readers, the texts as buttons, the lines (the first opened), each step with its verse, its Sanskrit words, what the index says and a link to the person\'s page; a name found in the lines; the page in plain words; linked from Genealogies; corpus-index takes the table. typecheck clean; vitest: the new file 6 tests, genealogy-heal 6, index-site 17 | Yours: the kit, typecheck, vitest, build, push, Publish |\n| 11 Nov | The Gandharva English, the trial | Done by you: job e7d6c2c0, 40 of 40 passages translated with Sonnet, no error, 255 seconds; a passage about $0.005 (the last line\'s $0.00452) | Yours: `claude_engine.py --credit` (what the trial cost), then the rest from its desk page |\n| 11 Nov | The credit\'s lines in .env | They were typed into PowerShell ("CommandNotFoundException"): they belong in the file .env. A command below changes those three lines only (a copy first), and prints nothing of the keys | Yours: the command, then the dashboard restarted when the OCR ends |\n| 11 Nov | The schedule | H1 (21:28): the site\'s pg_cron jobs 1, 2, 6, 7, 8, 9 and 10 active, each last run succeeded (10: srangam-corpus-name-links, 04:40 UTC). The four tasks of this PC: LastTaskResult 0 each (backup 04:00, mirror 20:31, corner 21:18, maintenance 21:00) | - |\n| 11 Nov | The dashboard | restart_dashboard.ps1 refused: an OCR job, sharada_tilaka_tantra_ii, running for 1,476,991 seconds (17 days) | Yours: its pages counted (below), then Pause or let it finish |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G5b (the index's persons join the lines), G5c (C28, the Dynasties page); the Gandharva English; R1; kin-long; the credit's steps 4 to 7; load-js |\n",
     "| Next | G5b (the index's persons join the lines), G5c (C28, the Dynasties page); the Gandharva English; R1; kin-long; the credit's steps 4 to 7; load-js |\n\n## 43. 11 Nov, night: the dynasties joined and made a page (DOCS108_2026_11_11)\n\n| What | State |\n|---|---|\n| Verified | VAMSA_HEAL's release and report on the PC (2,098 statements, 1,767 verified); H1 (seven pg_cron jobs, each last run succeeded); the four tasks (result 0); the Gandharva trial (40 of 40) |\n| The asks | docs\\ASKS_2026-10-22.md section 21 |\n| Built | VAMSA_JOIN_2026_11_11 (vamsa_join.py; index_sync.py's table dynasties); C28_INDEX_DYNASTIES_2026_11_11; the Srangam kit DYNASTIES_2026_11_11; DOCS108 |\n| Measured | 2,098 statements, 1,460 persons in lines; 1,052 found in the Purana Index, 990 steps with the same father there, 55 with another, 408 persons not in it; 111 lines of three or more |\n| To do | the two automaton patchers, run_tests, release; C28; the Srangam kit; index_sync --apply; A2; the credit's lines; the Gandharva English |\n| Next | R1 (our findings: where the Puranas, the index and the historians agree or differ); kin-long; the credit's steps 4 to 7; load-js |\n")

edit('RUNBOOK.md', 1, '   anthropic:claude-sonnet-5-5, limit 40), then the rest from its desk page.\n',
     "   anthropic:claude-sonnet-5-5, limit 40), then the rest from its desk page.\n\n## 11 Nov, night: the dynasties to the site (DOCS108_2026_11_11)\n\ndocs\\ASKS_2026-10-22.md, section 21. From the automaton's root unless said:\n\n1. The patches: `python scripts\\patch_vamsa_join_2026_11_11.py --check`, then without; the same for\n   `patch_docs108_2026_11_11.py`; `python -m unittest tests.test_vamsa_join_2026_11_11 tests.test_b2_site_pg_2026_10_28\n   tests.test_docs108_2026_11_11`; `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with\n   COMMIT_MSG_dynasties_20261111.txt.\n2. `python scripts\\vamsa_join.py` (free): the counts, data\\vamsa_read\\dynasties.json, exports\\vamsa_dynasties.csv.\n3. C28 in the Lovable Cloud SQL editor (docs\\cloud\\C28_index_dynasties_2026-11-11.sql): B1, the change (one paste),\n   A1, A3.\n4. Srangam (D:\\srangam-42267): `git pull --rebase --autostash`; the kit's patcher (`--check`, then without);\n   `npm run typecheck`; `npx vitest run`; `npm run build`; `git add` the six files by name; commit; push; Publish (it\n   deploys corpus-index again).\n5. `python scripts\\index_sync.py` (the plan: the dynasties to send), then `python scripts\\index_sync.py --apply`; A2.\n   Open /corpus/genealogies/dynasties signed in.\n")


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

