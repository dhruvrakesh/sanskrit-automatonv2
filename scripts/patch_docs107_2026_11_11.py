#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs107_2026_11_11.py  (2026-11-11)  DOCS107_2026_11_11

The dynasties read (G5a's run) and mended (VAMSA_HEAL); the path charted on a schedule (PATH_SCHED); is it done in
full, on the desk, on the site, on a schedule? This patch adds:

  docs/ASKS_2026-10-22.md    section 20: each ask of 11 Nov (evening), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 42
  RUNBOOK.md                 "11 Nov, evening": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs107_<date> copies.

  python scripts\\patch_docs107_2026_11_11.py --check
  python scripts\\patch_docs107_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS107_2026_11_11'
TAG = 'docs107'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS106_2026_11_11', 'docs/STATE_2026-10-18.md': 'DOCS106_2026_11_11', 'RUNBOOK.md': 'DOCS106_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 11 Nov | Kaunteya, the pages explained (asked again) | Done on 10 Nov and live (a5561d72, C26, Srangam 91f9efd) | - |\n',
     '| 11 Nov | Kaunteya, the pages explained (asked again) | Done on 10 Nov and live (a5561d72, C26, Srangam 91f9efd) | - |\n\n## 20. 11 Nov, evening: the dynasties read and mended; is it done in full, on the desk, on the site, on a schedule? (DOCS107_2026_11_11)\n\nAsked at 19:10, with the release of 0afe36df, the probe, G5a\'s run and report, the Gandharva Veda\'s benchmark and S3\'s\nexport: "is this done in full and local and online ui/ux reflecting this fully along with all cron jobs for maintaining\nand updating local and postgres database state to offer this platform to a select audience and myself", and "I hope we\ncan use our new claude api key that does not expire ... we still saw around 173 USD worth of pending api credit". Read\nfrom your screenshots, data\\vamsa_read (the stored replies, on a copy), data\\text_path.json, the benchmark, the four\ntasks\' logs in D:\\backups and docs\\PLATFORM_2026-10-04.md.\n\n**Done in full? No.** The dynasties are read and checked on this PC; they are not yet joined to the index\'s persons\n(G5b) nor on the site (G5c); the findings (R1), Sorensen\'s long entries (kin-long) and the credit\'s steps 4 to 7 wait.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 11 Nov | The dynasties, read | Done by you, 18:52 to 19:10: 56 parts of 60 read, 1,975 statements, 1,449 verified (73%), $2.00. Found: four replies corrected themselves (not read: "Extra data"); one part\'s 35 statements came without their verse; 281 of 309 "unsupported" were dictionary forms (putrah for the verse\'s putras) or "..."; the report\'s longest lines (42, 40, 36) ran through homonyms of different dynasties (Srnjaya, Candra, Nara) | - |\n| 11 Nov | The dynasties, mended | Built VAMSA_HEAL_2026_11_11; on a copy of the stored replies, free: 64 parts read, 2,098 statements, 1,767 verified (84%: Visnupurana 4, 880 of 1,047; Bhagavatapurana 9, 836 of 999; 12.1, 51 of 52), "bad" 1, "unsupported" 74. The lines keep homonyms apart: the Bhagavatapurana\'s Vaisali line Marici to Trnabindu (27), the Videha line to Bhanuman (25); the Visnupurana\'s Vrsni line Kratha to Yugandhara (29). Each line with its verses: data\\vamsa_read\\vip4_lines.json (bhp9, bhp12 alike), exports\\vamsa_lines_vip4.csv (bhp9, bhp12 alike) | Yours: the patch, `--reparse`, `--report`. Left: G5b, the index\'s persons joining a line across chapters and books (a homonym told apart by the index\'s father); G5c, C28 and the Dynasties page |\n| 11 Nov | The Gandharva Veda | The benchmark (19:10): ours (vision, 507 pages) misreads 0.10% of the letters; the GRETIL e-text covers 378 pages and is another edition (ours reads 74% of it, F1 0.76; letter by letter 89.7% alike). Translate ours: it is the whole text. The path\'s estimate: $13.77 for English and Hindi with flash | Yours: a trial of 40 passages with Sonnet through the dashboard (its lock), then the rest |\n| 11 Nov | The new key and the credit | The probe answers (claude-haiku-5-5, $0.00002); `--credit` said $36.61 of $200 since 9 Nov, $163.39 left, before G5a\'s $2.00. The Console said $173.93 at 17:23, before G5a. A key that does not expire is not a credit that does not: the Console\'s Billing page says when the credit ends (Anthropic\'s credit terms). The dashboard was not restarted: "[REFUSED] something already answers on 127.0.0.1:5057" | Yours: .env\'s three lines from the Console; `scripts\\restart_dashboard.ps1` |\n| 11 Nov | spatial_ref_sys | S3 (18:54): the columns of ours on PostGIS are srangam_correlation_matrix.coordinates and srangam_inscriptions.coordinates (geography); spatial_ref_sys has 8,500 rows, 0 updated, 0 deleted: untouched | Yours: the finding marked accepted, with C27\'s reason; PostGIS stays |\n| 11 Nov | The schedule (local and PostgreSQL) | Four tasks on this PC, from their logs: SanskritDBBackup (04:00, OK, 11 Nov), SanskritCorpusMirror (every 2 hours; 18:31 rc 0, the genealogies\' 8 tables equal), SanskritMaintenance (every 3 hours when nothing writes; 18:00 done), SanskritCornerWorker (every 10 minutes; 19:08 rc 0). On the site: Srangam\'s pg_cron jobs 1, 2, 6, 7, 8 and 9 (docs\\PLATFORM_2026-10-04.md; H1 confirms). Built PATH_SCHED_2026_11_11: the maintenance task charts the path again when the chart is 20 hours old (what left the Natyasastra\'s desk a fortnight behind) | Yours: the patch; `Get-ScheduledTask` and H1 (below) to see each one\'s last run |\n| 11 Nov | For a select audience | The site lets researchers in by invitation (rbac: invitations, roles, the audit; Kanika and Parth accepted theirs); the reader functions need a signed-in user; the mode "readers" is there when wanted (docs\\PLATFORM_2026-10-04.md) | The dynasties and the findings reach them with G5c and R1 |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G5a in full, then G5b, G5c; R1 (our findings); the Gandharva Veda's benchmark; kin-long; the credit's steps 4 to 7; load-js |\n",
     '| Next | G5a in full, then G5b, G5c; R1 (our findings); the Gandharva Veda\'s benchmark; kin-long; the credit\'s steps 4 to 7; load-js |\n\n## 42. 11 Nov, evening: the dynasties read and mended (DOCS107_2026_11_11)\n\n| What | State |\n|---|---|\n| Release | Automaton `0afe36df` (TESTS_HERMETIC, G5a, DOCS106) pushed and verified |\n| Verified | G5a\'s run ($2.00, 1,975 statements); its replies parsed again on a copy (2,098 statements, 1,767 verified); the benchmark of the Gandharva Veda; S3; the probe; the four tasks\' logs |\n| The asks | docs\\ASKS_2026-10-22.md section 20 |\n| Found | replies that correct themselves; a part without references; dictionary forms against sandhi; homonyms joined into one line; the path never charted on a schedule; the dashboard not restarted |\n| Built | VAMSA_HEAL_2026_11_11 (vamsa_read.py: the last object read, the reference from the words, sandhi and "...", persons apart by their fathers, the lines with their verses); PATH_SCHED_2026_11_11 (maintenance step f); DOCS107 |\n| To do | the two patchers, `--reparse`, `--report`, run_tests; restart_dashboard.ps1; .env\'s credit from the Console; the Gandharva trial; the finding accepted |\n| Next | G5b (the index\'s persons join the lines), G5c (C28, the Dynasties page); the Gandharva English; R1; kin-long; the credit\'s steps 4 to 7; load-js |\n')

edit('RUNBOOK.md', 1, '5. The Gandharva Veda: `python scripts\\benchmark_sources.py --doc gandharva_veda_natya_shastra` (free).\n',
     "5. The Gandharva Veda: `python scripts\\benchmark_sources.py --doc gandharva_veda_natya_shastra` (free).\n\n## 11 Nov, evening: the dynasties mended; the path on a schedule (DOCS107_2026_11_11)\n\ndocs\\ASKS_2026-10-22.md, section 20. From the automaton's root:\n\n1. The patches: `python scripts\\patch_vamsa_heal_2026_11_11.py --check`, then without; the same for\n   `patch_path_sched_2026_11_11.py` and `patch_docs107_2026_11_11.py`; `python -m unittest tests.test_vamsa_read_2026_11_11\n   tests.test_path_sched_2026_11_11 tests.test_docs107_2026_11_11 tests.test_auto_repair_2026_10_25`;\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_vamsaheal_20261111.txt.\n2. The dynasties again, free: `python scripts\\vamsa_read.py --reparse`, then `python scripts\\vamsa_read.py --report`.\n3. The dashboard: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1` (it refuses while\n   a job runs; `-Status` shows them).\n4. The schedule: `Get-ScheduledTask -TaskName SanskritCorpusMirror, SanskritMaintenance, SanskritDBBackup,\n   SanskritCornerWorker | Get-ScheduledTaskInfo`; on the site, H1 of docs\\cloud\\OPS_health_2026-10-08.sql.\n5. The Gandharva Veda: a trial of 40 passages with Sonnet through the dashboard (`/api/translate`, engine\n   anthropic:claude-sonnet-5-5, limit 40), then the rest from its desk page.\n")


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

