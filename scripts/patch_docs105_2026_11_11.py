#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs105_2026_11_11.py  (2026-11-11)  DOCS105_2026_11_11

The desk said what was so a fortnight before; the credit's line; Lovable's finding on spatial_ref_sys. This patch adds:

  docs/ASKS_2026-10-22.md    section 18: each ask of 11 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 40
  RUNBOOK.md                 "11 Nov: the desk, the credit's line, spatial_ref_sys": the commands in order

Beside it (new files, not patched): scripts\\patch_desk_fresh_2026_11_11.py, docs\\cloud\\C27_spatial_ref_sys_2026-11-11.sql.
Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs105_<date> copies.

  python scripts\\patch_docs105_2026_11_11.py --check
  python scripts\\patch_docs105_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS105_2026_11_11'
TAG = 'docs105'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS104_2026_11_10', 'docs/STATE_2026-10-18.md': 'DOCS104_2026_11_10', 'RUNBOOK.md': 'DOCS104_2026_11_10'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 10 Nov | The Professor asked again | Not in the backup of 10 Nov (the last ask_prof row is of 28 Oct) | Yours |\n',
     '| 10 Nov | The Professor asked again | Not in the backup of 10 Nov (the last ask_prof row is of 28 Oct) | Yours |\n\n## 18. 11 Nov: the desk said what was so a fortnight before; the credit\'s line (DOCS105_2026_11_11)\n\nAsked on 11 Nov, with a screenshot of /desk/gandharva_veda_natya_shastra: "why is python action not updating here in\nnatya shastra", with the asks of 10 Nov again (the genealogies, the dynasties, B. C. Law\'s EPUB). Read from the\nrepositories, data/text_path.json, data/ocr_consensus, data/raw_merged, data/jobs.jsonl and .env\'s time (not its\nvalues), on the PC at 10:08 to 10:27 UTC.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 11 Nov | Why the Natyasastra\'s desk does not move | Found: the desk reads each text\'s path from data/text_path.json, written last on 28 Oct (17:48, 88 texts). Vision read the Gandharva Veda\'s pages on 10 and 11 Nov; the consensus of 15:27 (11 Nov) says 507 pages current, 0 stale, 0 missing in the database: 506 pages vision\'s, page 422 Tesseract\'s (vision failed on it at 10:47). So the desk showed the path of 28 Oct: "repair the scan: vision has read 0 of its 507 pages". Built (DESK_FRESH_2026_11_11): `text_path.py --doc X --write` charts one text again (its e-text witness with it) and puts its row in with its own time; the desk dates a text by its row, says what changed since (the consensus, the merged pages, the register) and offers "Chart this text again (free)" | Yours: the patch, a dashboard restart when no job runs; or now, without it: `python scripts\\text_path.py` (every text, free) |\n| 11 Nov | The credit\'s line on the desk: "$0.00 left (it expires 2026-11-11)" | Found: the dashboard was started before .env had the credit\'s settings (.env written 9 Nov, 03:31 UTC), so it shows claude_engine\'s defaults ($190 from 15 Oct, until 11 Nov), and the jobs it starts inherit them: from 11 Nov a Claude job started from the dashboard is refused as expired. The command line reads .env ($200 from 9 Nov, until 11 Dec). Built: the dashboard reads those three settings from .env again when it changes (the desk, the Usage tab, BM1\'s caps, every job it starts) | Yours: a restart is enough today; the patch keeps it so |\n| 11 Nov | The Gandharva Veda\'s English | Its reading in the database is now vision\'s (none of it translated). The GRETIL Natyasastra is here as its e-text witness (4,423 passages; the credit\'s step 7, about $49, is its English and Hindi). Translate one of them, not both: first `benchmark_sources.py --doc gandharva_veda_natya_shastra` (free) says which reading is the better text | Yours: the benchmark, then the choice |\n| 11 Nov | The genealogies, the dynasties (asked again) | Done on 10 Nov and live: release a5561d72; C26; Srangam 91f9efd published; index_sync sent 7,010 rows and deleted 206 (the genealogies\' 8 tables equal) | G5a (the dynasties from the Visnu\'s book IV and the Bhagavata\'s book IX verse by verse: about $3 to $8 of the credit); kin-long (Sorensen\'s 52 longest entries, about $1 to $2 of the spend cap) |\n| 11 Nov | B. C. Law\'s EPUB, as Raychaudhuri was | Done by you on 10 and 11 Nov: 195 pages read ($1.71), 3,409 claims, 1,929 linked; peoples_index carries them as private reading (never on the site, in copyright in India to the end of 2029). Raychaudhuri\'s page 252 read again from the stored reply (`--reparse`, 07:59) | - |\n| 11 Nov | Lovable\'s security findings (public.spatial_ref_sys) | docs\\cloud\\C27_spatial_ref_sys_2026-11-11.sql: a read-only check (PostGIS, the table\'s owner, anon\'s and authenticated\'s privileges, any geometry columns of ours, the public tables without RLS), then the writes revoked from anon and authenticated (a GRANT undoes it), then the check again. Nothing dropped | Yours: S1, S2, S1 |\n| 11 Nov | The tests on the credit\'s default day | Two tests of test_claude_engine_2026_10_15 ran on the default\'s last day (2026-11-11) and now set a later one. Ten modules (bench_*, claude_first, pilot_fix) pass with .env\'s credit (the PC\'s) and fail without it (the VM\'s copy has no .env) | Before 11 Dec: those ten set their own expiry |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G5a (the dynasties: about $3 to $8 of the credit); kin-long (about $1 to $2); the credit's steps 4 to 7; load-js |\n",
     '| Next | G5a (the dynasties: about $3 to $8 of the credit); kin-long (about $1 to $2); the credit\'s steps 4 to 7; load-js |\n\n## 40. 11 Nov: the desk said what was so a fortnight before (DOCS105_2026_11_11)\n\n| What | State |\n|---|---|\n| Release | Automaton `a5561d72` (DOCS104); Srangam `91f9efd` published; C26 live (A1 true, true, true; A3 false, true, false); index_sync: 7,010 rows sent, 206 deleted |\n| Verified | data/text_path.json of 28 Oct 17:48; the Gandharva Veda\'s consensus of 11 Nov 15:27 (507 current, 0 stale, 0 missing); .env written 9 Nov 03:31 UTC; the VM\'s suite: 232 modules, 1,731 tests, 10 modules failing without .env\'s credit (they pass with it) |\n| The asks | docs\\ASKS_2026-10-22.md section 18 |\n| Found | the desk read a chart of a fortnight before; the dashboard\'s credit (and its jobs\') was the defaults, expired on 11 Nov |\n| Built | DESK_FRESH_2026_11_11 (text_path.py --doc X --write; translation_desk.py row_at, changed_since; claude_engine.py dotenv_credit; dashboard.py: the row\'s date, what changed, "Chart this text again (free)", path_doc, the credit read again); C27 (spatial_ref_sys); DOCS105 |\n| To do | the two patchers, run_tests, a dashboard restart when idle; `text_path.py` (every text) or the button; C27 S1, S2, S1 |\n| Next | the Gandharva Veda: the benchmark (free), then one English; G5a; kin-long; the credit\'s steps 4 to 7; the ten tests\' expiry before 11 Dec; load-js |\n')

edit('RUNBOOK.md', 1, "6. Raychaudhuri's page 252: `python scripts\\scholar_claims.py --reparse` (free), `python scripts\\scholar_claims.py --link`.\n",
     '6. Raychaudhuri\'s page 252: `python scripts\\scholar_claims.py --reparse` (free), `python scripts\\scholar_claims.py --link`.\n\n## 11 Nov: the desk, the credit\'s line, spatial_ref_sys (DOCS105_2026_11_11)\n\ndocs\\ASKS_2026-10-22.md, section 18. From the automaton\'s root:\n\n1. Now, without any patch (free, read-only on the database): `python scripts\\text_path.py` (every text, a few\n   minutes). The desk and /path read the new chart at once.\n2. The patches: `python scripts\\patch_desk_fresh_2026_11_11.py --check`, then without; the same for\n   `patch_docs105_2026_11_11.py`; `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with\n   COMMIT_MSG_deskfresh_20261111.txt.\n3. Restart the dashboard when no job runs (the History says). After it: one text charted again from its desk page\n   ("Chart this text again (free)"), or `python scripts\\text_path.py --doc gandharva_veda_natya_shastra --write`.\n4. The Gandharva Veda: `python scripts\\benchmark_sources.py --doc gandharva_veda_natya_shastra` (free): which reading,\n   vision\'s of the edition or the GRETIL e-text, is the better text; then translate that one only.\n5. C27 in the Lovable Cloud SQL editor (docs\\cloud\\C27_spatial_ref_sys_2026-11-11.sql): S1 (read-only), S2 (the\n   writes revoked, one paste), S1 again.\n')


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

