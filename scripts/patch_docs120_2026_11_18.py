#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs120_2026_11_18.py  (2026-11-18)  DOCS120_2026_11_18

18 Nov: the enterprise way (the page of 17 Nov held, not released; DOCS119 held with it); the baselines of the desk and
the site; P1 (scripts\\patch_vamsa_names_2026_11_18.py, the register healed) and P2a (scripts\\patch_vamsa_site_2026_11_18.py,
the site's road for every work, by default as before) built beside this; the team's page of 16 to 18 Nov. Adds:

  docs/ASKS_2026-10-22.md    section 32: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 54
  RUNBOOK.md                 "18 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs120_<date> copies.

  python scripts\\patch_docs120_2026_11_18.py --check
  python scripts\\patch_docs120_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS120_2026_11_18'
TAG = 'docs120'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS118_2026_11_17', 'docs/STATE_2026-10-18.md': 'DOCS118_2026_11_17', 'RUNBOOK.md': 'DOCS118_2026_11_17'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "that differ), each approved or not by you, and never shown as the text's word.\n",
     'that differ), each approved or not by you, and never shown as the text\'s word.\n\n## 32. 18 Nov: the enterprise way; P0 baselines, P1 and P2a built; the team\'s page (DOCS120_2026_11_18)\n\nAsked on 17 Nov, 23:54: "are you sure this is the enterprise way? ... surgical changes that dont kill it, rather heal\nit and improve load times, UI/UX and firm up logic and documentation ... chart an enterprise path forward"; and on 18\nNov, 15:03, with four CSV exports of the Lovable Cloud SQL editor (15:00) and four screens (11:33 to 15:01), the\nstanding ask again ("are we done in full? ... a layperson\'s one pager for my erp team ..."). Read on the PC, read\nonly: the handover\'s rules, scripts\\vamsa.html and the dashboard\'s routes, scripts\\vamsa_join.py, scripts\\index_sync.py,\ndocs\\cloud\\C5 and C28, Srangam\'s CorpusDynasties.tsx and indexSite.ts; the backup of 18 Nov read immutable.\n\n**The answer of 17 Nov, 23:54: not the enterprise way in part.** The page of 17 Nov (vamsa_pages.py: one 2.1 MB file in\nexports\\) was a third surface beside the desk\'s Vamsa page and the site\'s genealogies, outside the dashboard, its data\nloaded whole; DOCS119 recorded it as "the desk\'s page built". Both were held before any release: the six files are in\nD:\\Sanksrit Automatons\\hold\\vamsa_pages_20261117 (seen there on 18 Nov; the Move-Item errors of 11:34 came after they\nhad moved). The way taken instead extends what runs: the register healed (P1), the site\'s own road for the dynasties\n(P2a, P2b), the desk\'s own Vamsa page (P3).\n\n**Done in full? No.** Built and tested on copies: P1, P2a. Not built: P2b (the Srangam kit), P3 to P5.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 18 Nov | The hold (P0) | Done by you: the six files of 17 Nov are in the hold folder; git status shows none of them; the repository is at b956084 | Done |\n| 18 Nov | Baselines, the desk (P0) | Your screens: the Vamsa page answered in 49.8 ms and 83.2 ms; index_sync\'s dump built in 6.7 s and 5.6 s, 5,458,038 bytes, dynasties 106 rows (0.2 MB); vamsa_register --stats as on 17 Nov (27 second names said: the heal not yet applied); the credit report: translation 3,158 calls $49.30, vamsa_read 323 calls $11.19 | Done |\n| 18 Nov | Baselines, the site (P0) | Your SQL of 15:00: corpus.index_dynasties holds 106 rows, 123 kB (vip4 50 rows, 493 persons in lines, 52 kB of steps; bhp9 48, 478, 42 kB; bhp12 8, 31, 4,339 bytes, last sent 13 Nov); corpus_reader_index_dynasties: anon may not call it, signed-in may; corpus_reader_allowed() lets in admins and super admins, then by corpus.reader_access\'s mode (signed_in: every signed-in user; readers: the listed readers and researchers; no row: admins only) | The mode itself: the SQL of the RUNBOOK |\n| 18 Nov | I1, the first call | Your SQL of 15:00: still no row for detect-duplicate-articles or suggest-tag-categories | You: "suggest categories" once, then the SQL |\n| 18 Nov | P1, the register healed | Built: scripts\\patch_vamsa_names_2026_11_18.py (vamsa_align.py, vamsa_register.py; the heal of 17 Nov alone, marker VAMSA_NAMES_2026_11_18): a second name only where the verse says it of him (not Ripunjaya\'s minister, Sraddhadeva\'s mother, Mandhatr\'s daughters\' husband, the land Kuruksetra); each said once; --name in plain letters, the exact name first; the father\'s entry only where most works agree. tests\\test_vamsa_names_2026_11_18.py: 7 tests OK, with the replay | You: the patch, then vamsa_register again |\n| 18 Nov | P2a, the site\'s road for 17 works | Built: scripts\\patch_vamsa_site_2026_11_18.py (vamsa_join.py, index_sync.py; VAMSA_SITE_2026_11_18): a G6 work\'s title and source from vamsa_read, no index text code; vamsa_join --work all, g6, every or one work (G5a\'s files as before); index_sync --dynasty-works all or every, by default all, as before. Measured on the backup of 18 Nov: all 106 rows, 218 kB of rows (the site\'s 106); every 517 rows, 911 kB (vip4 49 lines, bhp9 47, hv 48, matsya 38, bndp2 57, brahma 39, garuda1 47, agni 40, vipc4 47, the rest fewer). tests\\test_vamsa_site_2026_11_18.py: 5 tests OK; with the tests of the road (vamsa_join, b2_site, index_site, genealogy_heal) 81 OK, 24 skipped (no test database here) | Do not send every until P2b is live; from then on every run with every, the scheduled one too |\n| 18 Nov | P2b, the site\'s page | Not built. The page asks for every row at once (loadDynasties(null)); with every work that is about four times today\'s rows (911 kB against 218 kB of rows). The kit: one work at a time (loadDynasties(work)), the 17 works\' titles, a way in by Suryavamsa and Candravamsa, a name typed in plain letters found | Next |\n| 18 Nov | P3, the desk\'s page | Not built: the 17 works and the register inside the Vamsa page (/vamsa), one route and one read-only endpoint, the same menu | After P2b |\n| 18 Nov | The one pager | Made: https://claude.ai/artifact/PSQpG5t46vLgXiSMWaBSf6 (16 to 18 Nov, for the ERP team; the page of 14 to 16 Nov is linked from it) | Done |\n| 18 Nov | Done in full? | No: P2b, P3, P4 (G6f with R1: a review list for the 44 proposed names and the 672 kept apart), P5 (ARCHITECTURE.md, the genealogies\' road; I3) | In that order |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G6e (designed in section 31); G6f with R1; I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3 |\n",
     "| Next | G6e (designed in section 31); G6f with R1; I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3 |\n\n## 54. 18 Nov: the enterprise way; P1 and P2a built (DOCS120_2026_11_18)\n\n| What | State |\n|---|---|\n| Verified | The hold (the six files of 17 Nov out of the repository); the baselines (desk and site); P1 and P2a on copies (7 and 5 tests; 81 of the road's tests OK) |\n| The asks | docs\\ASKS_2026-10-22.md section 32 |\n| Built | scripts\\patch_vamsa_names_2026_11_18.py (P1); scripts\\patch_vamsa_site_2026_11_18.py (P2a); DOCS120; the team's page of 16 to 18 Nov |\n| Measured | The site: 106 dynasty rows, 123 kB; every work: 517 rows, 911 kB of rows; the desk's Vamsa page 50 to 83 ms |\n| Not verified | corpus.reader_access's mode; the two AI functions' first call |\n| To do | the patches, release; vamsa_register; the dump with every (nothing sent) |\n| Next | P2b (the Srangam kit: one work at a time); then every sent; P3; P4; P5 |\n")

edit('RUNBOOK.md', 1, "   section 31's ledger row again: srangam_ai_usage by function_name, purpose, provider, model, ok.\n5. The credit: `python scripts\\claude_engine.py --credit`.\n",
     "   section 31's ledger row again: srangam_ai_usage by function_name, purpose, provider, model, ok.\n5. The credit: `python scripts\\claude_engine.py --credit`.\n\n## 18 Nov: P1, the register healed; P2a, the site's road for every work (DOCS120_2026_11_18)\n\ndocs\\ASKS_2026-10-22.md, section 32. From the automaton's root, in PowerShell:\n\n1. The patches: `python scripts\\patch_vamsa_names_2026_11_18.py --check`, then without;\n   `python scripts\\patch_vamsa_site_2026_11_18.py --check`, then without; `python scripts\\patch_docs120_2026_11_18.py\n   --check`, then without; `python -m unittest tests.test_vamsa_names_2026_11_18 tests.test_vamsa_site_2026_11_18\n   tests.test_docs120_2026_11_18 tests.test_vamsa_join_2026_11_11 tests.test_vamsa_register_2026_11_17`; release.ps1\n   with COMMIT_MSG_vamsanames_20261118.txt (the dry run, then -Apply once).\n2. Free: `python scripts\\vamsa_register.py`, `python scripts\\vamsa_register.py --name Bhishma`, then\n   `python scripts\\vamsa_join.py --work every` (writes data\\vamsa_read\\dynasties_every.json and\n   exports\\vamsa_dynasties_every.csv; G5a's files as before).\n3. Nothing sent: `python scripts\\index_sync.py --dynasty-works every --dump exports\\index_rows_every_20261118.json.gz`.\n   Do not run index_sync with --apply and --dynasty-works every until the Srangam kit of P2b is live.\n4. In the Lovable Cloud SQL editor, read only: the mode of corpus.reader_access and the count of corpus.readers.\n")


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

