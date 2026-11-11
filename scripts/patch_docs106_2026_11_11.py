#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs106_2026_11_11.py  (2026-11-11)  DOCS106_2026_11_11

The tests apart from this PC (TESTS_HERMETIC); the dynasties read verse by verse (G5a, scripts\\vamsa_read.py); our own
findings from Law, Raychaudhuri and the texts may be published with citations (docs\\PEOPLES_FINDINGS_2026-11-11.md);
spatial_ref_sys (C27 with S3). This patch adds:

  docs/ASKS_2026-10-22.md    section 19: each ask of 11 Nov (later), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 41
  RUNBOOK.md                 "11 Nov, later": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs106_<date> copies.

  python scripts\\patch_docs106_2026_11_11.py --check
  python scripts\\patch_docs106_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS106_2026_11_11'
TAG = 'docs106'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS105_2026_11_11', 'docs/STATE_2026-10-18.md': 'DOCS105_2026_11_11', 'RUNBOOK.md': 'DOCS105_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 11 Nov | The tests on the credit's default day | Two tests of test_claude_engine_2026_10_15 ran on the default's last day (2026-11-11) and now set a later one. Ten modules (bench_*, claude_first, pilot_fix) pass with .env's credit (the PC's) and fail without it (the VM's copy has no .env) | Before 11 Dec: those ten set their own expiry |\n",
     '| 11 Nov | The tests on the credit\'s default day | Two tests of test_claude_engine_2026_10_15 ran on the default\'s last day (2026-11-11) and now set a later one. Ten modules (bench_*, claude_first, pilot_fix) pass with .env\'s credit (the PC\'s) and fail without it (the VM\'s copy has no .env) | Before 11 Dec: those ten set their own expiry |\n\n## 19. 11 Nov, later: the tests apart from this PC; the dynasties read (G5a); our findings may be published (DOCS106_2026_11_11)\n\nAsked at 17:20 to 17:24, with screenshots (run_tests failing in test_claude_engine_2026_10_15; the dashboard; the\nClaude Console\'s keys; the SQL editor) and S1\'s export: "I have added a fresh Anthropic key with credit and validity in\nthe env ... we might not publish BC Law\'s book on the site, but our analysis through the reading of both Law and\nRaychaudhuri and our own research, if pointing to something original, is our research and can be used/published with\nproper citations", with the asks of 10 Nov again. Read from the repositories, .env\'s names and its credit\'s three\nsettings (no key\'s value), data/text_path.json, the GRETIL archive on this PC, Supabase\'s pages on spatial_ref_sys.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 11 Nov | The fresh key and its credit | Found: .env written at 11:53 UTC; it has ANTHROPIC_API_KEY and ANTHROPIC_API_KEY2, and the scripts read ANTHROPIC_API_KEY only (claude_engine.Client); the credit\'s settings are $200 from 9 Nov until 11 Dec. The Console: srangam-nartiang2 made on 11 Nov (no end date), srangam-nartiang1 ends on 14 Nov; the balance $173.93. The dashboard still showed the defaults at 17:20 ($0.00, "expired"): it had not been restarted (an OCR job ran) | Yours: the new key on the ANTHROPIC_API_KEY line; the dashboard restarted when idle; `claude_engine.py --credit`, then `--probe` |\n| 11 Nov | The Natyasastra\'s desk | Done: the chart made again at 16:17 (89 texts); the Gandharva Veda\'s path is "translate" (884 passages, none translated; vision\'s reading, debris 0.10%); its GRETIL witness 4,422 passages | Yours: `benchmark_sources.py`, then one English |\n| 11 Nov | run_tests failed on the PC | Found: the tests read this PC\'s .env (its keys, its credit) through env_loader and the dashboard: with .env\'s $200 a test written for the $190 credit failed ("the API (or the key) is not answering", then WinError 32 on its temp database); without .env ten modules failed from 11 Nov. Built TESTS_HERMETIC_2026_11_11: tests\\__init__.py sets SA_NO_DOTENV=1 and SA_TEST_TODAY=2026-10-20 and takes the keys out; seven loaders of .env respect it; claude_engine.credit takes the tests\' day. With a copy of this PC\'s settings (fake keys) and python-dotenv: 235 modules, 1,752 tests, none failing | Yours: the patch, run_tests |\n| 11 Nov | Lovable\'s finding on spatial_ref_sys | Found (S1, 17:24): PostGIS 3.3.7 in public, the table owned by supabase_admin, RLS off, anon and authenticated may write it, two columns of ours of PostGIS types. The REVOKE (S2) cannot work: supabase_admin made those grants, and Supabase\'s pages say a revoke by our role does nothing, silently. C27 now says so and adds S3 (which two columns; any write through the API) | Yours: S3; the finding marked accepted with C27\'s reason; Lovable\'s support asked to move PostGIS into "extensions" (Supabase\'s way, keeping the columns). Never DROP EXTENSION postgis CASCADE |\n| 11 Nov | Our own findings from Law, Raychaudhuri and the texts, published with citations | The rule written down (docs\\PEOPLES_FINDINGS_2026-11-11.md): Law\'s book stays private (its text, its pages, his claims as extracted); a finding in our words that joins the sources (an agreement, a disagreement, a new link) may be published with each source cited by page or verse, once a person has read it; a machine check keeps any run of eight words of Law\'s out of it. R1 (the findings made, checked, read, sent) is planned and priced, not built | R1 after G5a: about $1 to $3 |\n| 11 Nov | The dynasties, "an API call thing" | Built G5a (VAMSA_READ_2026_11_11): scripts\\vamsa_read.py reads GRETIL\'s Visnupurana book 4, Bhagavatapurana book 9 and 12.1 (already on this PC) with Claude chapter by chapter into kinship statements, each checked against its verse by machine (verified, words, unsupported, bad); the plan on the real archive: 64 parts, 2,349 verses, about $1.82 (a guess until the trial); tested with a stubbed Claude (9 tests) | Yours: the trial (two chapters), then the rest (at most $8); then G5b (joined to the index\'s persons, free) and G5c (C28, the Dynasties page) |\n| 11 Nov | Kaunteya, the pages explained (asked again) | Done on 10 Nov and live (a5561d72, C26, Srangam 91f9efd) | - |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | the Gandharva Veda: the benchmark (free), then one English; G5a; kin-long; the credit's steps 4 to 7; the ten tests' expiry before 11 Dec; load-js |\n",
     "| Next | the Gandharva Veda: the benchmark (free), then one English; G5a; kin-long; the credit's steps 4 to 7; the ten tests' expiry before 11 Dec; load-js |\n\n## 41. 11 Nov, later: the tests apart from this PC; G5a; our findings (DOCS106_2026_11_11)\n\n| What | State |\n|---|---|\n| Applied on the PC | DESK_FRESH_2026_11_11 and DOCS105 (their marks in the files); the chart made again at 16:17 |\n| Verified | .env's credit settings ($200, 9 Nov to 11 Dec) and its key names (not their values); S1's export (17:24); a copy of the suite with this PC's settings: 235 modules, 1,752 tests, none failing |\n| The asks | docs\\ASKS_2026-10-22.md section 19 |\n| Found | the tests read the PC's .env; the REVOKE on spatial_ref_sys cannot work (supabase_admin's grants); two of our columns use PostGIS; ANTHROPIC_API_KEY2 is read by nothing |\n| Built | TESTS_HERMETIC_2026_11_11 (tests\\__init__.py; env_loader, dashboard, ingest_pdf, run_inbox, corpus_sync, publish_api, publish_srangam; claude_engine.test_today); VAMSA_READ_2026_11_11 (G5a, scripts\\vamsa_read.py); C27 with S3; docs\\PEOPLES_FINDINGS_2026-11-11.md; DOCS106 |\n| To do | the two patchers, run_tests; the dashboard restarted; the key on its line; G5a's trial; S3 and the finding accepted |\n| Next | G5a in full, then G5b, G5c; R1 (our findings); the Gandharva Veda's benchmark; kin-long; the credit's steps 4 to 7; load-js |\n")

edit('RUNBOOK.md', 1, '   writes revoked, one paste), S1 again.\n',
     '   writes revoked, one paste), S1 again.\n\n## 11 Nov, later: the tests apart from this PC; G5a; spatial_ref_sys (DOCS106_2026_11_11)\n\ndocs\\ASKS_2026-10-22.md, section 19; docs\\PEOPLES_FINDINGS_2026-11-11.md. From the automaton\'s root:\n\n1. The patches: `python scripts\\patch_tests_hermetic_2026_11_11.py --check`, then without; the same for\n   `patch_docs106_2026_11_11.py`; `python -m unittest tests.test_tests_hermetic_2026_11_11 tests.test_vamsa_read_2026_11_11\n   tests.test_claude_engine_2026_10_15`; `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1\n   with COMMIT_MSG_g5a_20261111.txt.\n2. The key: the new key on the line `ANTHROPIC_API_KEY=` of .env (ANTHROPIC_API_KEY2 is read by nothing). Restart the\n   dashboard when no job runs; then `python scripts\\claude_engine.py --credit` (free) and\n   `python scripts\\claude_engine.py --probe` (about $0.001; the Console\'s key list then shows which key it used).\n3. G5a: `python scripts\\vamsa_read.py` (the plan, free); `python scripts\\vamsa_read.py --work vip4 --chapters 1-2 --yes`\n   (the trial); `python scripts\\vamsa_read.py --report`; then `python scripts\\vamsa_read.py --work all --yes --max-usd 8`\n   and `--report` again.\n4. C27\'s S3 (read-only) in the Lovable Cloud SQL editor; mark the finding on spatial_ref_sys accepted in Lovable\'s\n   security view with C27\'s reason; ask Lovable\'s support to move PostGIS into the schema "extensions".\n5. The Gandharva Veda: `python scripts\\benchmark_sources.py --doc gandharva_veda_natya_shastra` (free).\n')


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

