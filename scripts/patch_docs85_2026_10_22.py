#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs85_2026_10_22.py  DOCS85_2026_10_22

Records the debt collected and resolved on 22 Oct (docs/DEBT_2026-10-22.md, which comes with this release): the top
bar's menus (UI_CLARITY_2026_10_22); the two Englishes of the Hayasirsa and why it is held; "% Devanagari" is not
fidelity; the vote of two readings and its independence (TRIANGULATE_2026_10_22); the benchmark letter by letter
(BENCH_LETTERS_2026_10_22); any engine's pages measured by our checks (ENGINES_2026_10_22); GRETIL's Nirukta read as
written (ETEXT_DOTS_2026_10_22); the PostgreSQL tests run (PG_TESTS_2026_10_22); the intake rule proposed; what is
yours (the Hayasirsa's release, the Daivat-Sanhita's rights and source, a second engine, the cap).

Appends the brain page's section 11, PLATFORM section 88, a RUNBOOK section, ENTERPRISE_PATH addendum 75 and STATE
section 20, each needing DOCS84_2026_10_22; and corrects docs/FIDELITY_2026-10-22.md, section 6: the Surya's "about
$0.02" was written on 12 Oct, before REINGEST_2026_10_12 priced repairs from the meter, not by today's fallback.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs85_<date>), line endings kept.

  python scripts\\patch_docs85_2026_10_22.py --check
  python scripts\\patch_docs85_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS85_2026_10_22"
BP = "docs/BRAIN_PATH_2026-10-21.md"
FID = "docs/FIDELITY_2026-10-22.md"
DEBT = "docs/DEBT_2026-10-22.md"
NEEDS = "DOCS84_2026_10_22"

FID_OLD = """- The meter's vision price in October is $0.0032 a page (2,987 calls, $9.57). `repair_text.py` prices a repair at the
  text's own measured rate, and at a fallback of $0.0004 a page where the text has none (the Surya's "about $0.02" for
  55 pages): an eighth of October's price. Read such an estimate as about $0.18.
"""
FID_NEW = """- The meter's vision price in October is $0.0032 a page (2,987 calls, $9.57). `repair_text.py` prices a repair at the
  text's own measured rate (20 delivered pages or more), else at the last 300 vision calls corpus-wide, and at its
  fallback of $0.0004 a page only where nothing is metered. The Surya's "about $0.02" for 55 pages was written on 12
  Oct, before REINGEST_2026_10_12 priced repairs from the meter (corrected by DOCS85_2026_10_22; this page said the
  fallback wrote it): a judged file carries the price of its day; judge it again for today's (about $0.18 at
  October's rate).
"""
EDITS = {FID: [(FID_OLD, FID_NEW)]}

BRAIN = """
## 11. The debt collected and resolved; any engine, our checks (DOCS85_2026_10_22)

docs/DEBT_2026-10-22.md is the register: what was found, the evidence, the fix or whose decision it is.

**The three questions of 22 Oct.** The top bar's menus closed on the way to them (a 6px gap): mended. The Hayasirsa's
EN 1 of 1,614 and SC 1,431 are two Englishes: the repair of 11 Oct replaced its Sanskrit and cleared the working
English made from the old misreading; the scholarly English was made after, from the new Sanskrit; the working English
was not made again, so the release gate holds the text and the site keeps its last version. The source search works:
for the Daivat-Sanhita it found 35 candidates, six close; but their "100% Devanagari" is the script, not the fidelity.

**What decides fidelity is independence.** archive.org's OCR is Tesseract; its text of a scan we hold makes
Tesseract's mistakes (alike 0.25 and 0.40, where independent pairs are 0.04 to 0.06), so it is no second witness.
TRIANGULATE_2026_10_22 measures that before two readings may outvote a third.

**The intake rule (proposed, yours to adopt).** A reading of a print becomes the Sanskrit we translate only when it is
measured letter by letter: against an e-text, close or faithful (agreement 90% or more of the e-text's aksharas); or,
where none exists, beside an independent second reading of the same print (not alike by TRIANGULATE's check), with
5 or fewer own misread aksharas in 100. Otherwise it stays a witness, and the places two independent readings outvote
it are the mends to read beside the page. Any engine qualifies the same way: ENGINES_2026_10_22 reads its pages from
any folder (`pages:<dir>/<doc>`), so an open model, Gemini 2.5 Pro or another is measured by the checks ours passed
(Gemini 2.5 Flash: 3.58 and 3.62 own; Tesseract 18.15 and 24.49) before a page of it is ingested. The rule is written
here, not built into the ingest; building it is the next phase if you adopt it.

**The witnesses.** GRETIL's Nirukta is now read as written (ETEXT_DOTS_2026_10_22: no danda between every two words,
its quotation marks, its references and sigla in Latin); its witness is to be written again (free, local).
"""

PLATFORM = """
## 88. The debt of 22 Oct: seven patches, the PostgreSQL tests, the intake rule (DOCS85_2026_10_22)

docs/DEBT_2026-10-22.md. Applied in this order, each anchored, all or nothing, with its test:

| Marker | Files | What |
|---|---|---|
| UI_CLARITY_2026_10_22 | dashboard_static.html, dashboard.py (+2 tests' replay chains) | the menus' bridge and 450 ms close; EN and SC named; the repair note; "% Devanagari" is the script |
| TRIANGULATE_2026_10_22 | source_fidelity.py | --pair counts the outvoted places; the independence check (alike 0.12 own, 0.30 outvoted; same text 0.001) |
| BENCH_LETTERS_2026_10_22 | benchmark_sources.py (+ test_reingest's chain) | letters on sample pages (--letters-pages 80), own and outvoted, two columns |
| ENGINES_2026_10_22 | source_fidelity.py | `pages:<dir>/<doc>`: any engine's page JSONL, measured as ours |
| ETEXT_DOTS_2026_10_22 | etext_witness.py (+ test_etext_prose2's chain) | a line whose words are joined by full stops read as written; other e-texts byte for byte as before |
| PG_TESTS_2026_10_22 | tests/test_corpus_sync_pg_2026_10_08.py | the test-only Supabase stand-ins applied first, as in the 18 other modules |
| DOCS85_2026_10_22 | this section, the brain page 11, RUNBOOK, ENTERPRISE_PATH 75, STATE 20, FIDELITY 6 | the record |

- **Tests:** the suite on a copy with the six code patches: 161 modules, 1,298 tests, 0 failures, 191 skipped (184 of
  them the PostgreSQL tests); test_docs85_2026_10_22 (5) beside it. The 19 PostgreSQL modules in a throwaway PostgreSQL 16 (UTF8, pgvector 0.8.0), a fresh database
  each: 283 tests, 0 failures; they need pgvector 0.7 or later (halfvec) and a UTF8 database.
- **Corrected:** section 87's "repair_text.py's fallback vision price ($0.0004 a page)" is the fallback only where
  nothing is metered; a repair is priced at the text's own rate or the last 300 vision calls (FIDELITY, section 6).
- **Mirror:** 152 runs; 7 failed, all from 10 to 12 Oct; the last four of 22 Oct verified 386 groups equal.
"""

RUNBOOK = """
## Debt of 22 Oct: apply, test, measure (DOCS85_2026_10_22)

docs/DEBT_2026-10-22.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`, then
`Set-Location $A`. Nothing below spends unless it says so.
1. Apply in this order, each with `--check` first, then without: `scripts\\patch_ui_clarity_2026_10_22.py`,
   `scripts\\patch_triangulate_2026_10_22.py`, `scripts\\patch_bench_letters_2026_10_22.py`,
   `scripts\\patch_engines_2026_10_22.py`, `scripts\\patch_etext_dots_2026_10_22.py`,
   `scripts\\patch_pg_tests_2026_10_22.py`, `scripts\\patch_docs85_2026_10_22.py`. Then `python -m unittest
   tests.test_ui_clarity_2026_10_22 tests.test_triangulate_2026_10_22 tests.test_bench_letters_2026_10_22
   tests.test_engines_2026_10_22 tests.test_etext_dots_2026_10_22 tests.test_pg_tests_2026_10_22
   tests.test_docs85_2026_10_22`, then the whole suite. Restart the dashboard only when it reads idle.
2. The Nirukta's witness again (free, local; it has no English): with the dashboard idle, `python scripts\\db_backup.py
   data\\context.db D:\\backups\\context_pre_etextdots_nirukta_20261022.db`; `python scripts\\wipe_doc.py --doc
   nirukta__w_gretil --dry-run`, then `--yes`; `python scripts\\etext_witness.py --doc nirukta --file
   sources\\nirukta\\sa_yAska-nirukta.htm --category vedanga` (the preview), then the same with `--write --force` (the
   pages before are kept beside, .bak_); `python scripts\\etext_witness.py --doc nirukta --ingest --witness
   nirukta__w_gretil`; then `python scripts\\source_fidelity.py --ref db:nirukta__w_gretil --cand db:nirukta --cand
   vision:nirukta --cand raw:nirukta --pair vision:nirukta,raw:nirukta`.
3. The Daivat-Sanhita (free): on the Source desk, fetch the OCR text of the 2017 upload (DaivatSanhita_201702; the
   download is yours), then `python scripts\\benchmark_sources.py --doc Daivat-Sanhita`. Its rights and its repair
   are yours (DEBT, Y2): `python scripts\\repair_text.py --doc Daivat-Sanhita --repair --max-usd 5.30` (about $4.20).
4. A second engine, a pilot (yours, DEBT Y3; paid): `python scripts\\ocr_vision.py --glob
   "inbox\\markandeya_purana_*.pdf" --limit 20 --outdir data\\raw_vision_pro --model gemini-2.5-pro --doc
   markandeya_purana_pro_pilot` is a dry run (its pre-flight prices at Flash's metered rate; Pro's tokens cost about 4
   times as much, so read about $0.27); `--yes` calls. Then `python scripts\\source_fidelity.py --ref
   db:markandeya_purana__w_gretil --cand pages:data/raw_vision_pro/markandeya_purana --cand vision:markandeya_purana
   --cand raw:markandeya_purana --pair pages:data/raw_vision_pro/markandeya_purana,vision:markandeya_purana --pair
   pages:data/raw_vision_pro/markandeya_purana,raw:markandeya_purana`: its own misreadings, and whether its mistakes
   are Flash's (TRIANGULATE's check).
5. The site, read-only: `docs\\cloud\\CHECKS_debt_2026-10-22.sql`, one block at a time (H1 the Hayasirsa, H2 the
   witnesses, H3 the Daivat-Sanhita, H4 the mirror's runs).
6. The PostgreSQL tests on this PC (optional): PostgreSQL 16 with pgvector 0.7 or later and a UTF8 database. With
   Docker Desktop: `docker run --name corpus-test -e POSTGRES_PASSWORD=corpus_test_only -p 5433:5432 -d
   pgvector/pgvector:pg16`; for each module a database (`docker exec corpus-test createdb -U postgres t1`) and
   `$env:CORPUS_TEST_DSN = "postgresql://postgres:corpus_test_only@localhost:5433/t1"`, then `python -m unittest
   tests.test_corpus_sync_pg_2026_10_08`. Never a Supabase host: the tests refuse one.
"""

EP = """
## Addendum 2026-10-22 (75) (DOCS85_2026_10_22)

| # | Item | State |
|---|---|---|
| T1 | The top bar's menus | Done: UI_CLARITY_2026_10_22 |
| T2 | The vote of two readings; their independence | Done: TRIANGULATE_2026_10_22 |
| T3 | The benchmark, letter by letter | Done: BENCH_LETTERS_2026_10_22 |
| T4 | Any engine's pages, measured by our checks | Done: ENGINES_2026_10_22 |
| T5 | GRETIL's Nirukta read as written | Done: ETEXT_DOTS_2026_10_22; yours: its witness written again (free) |
| T6 | The PostgreSQL tests | Run: 283 pass; PG_TESTS_2026_10_22 for the one that failed on a fresh database |
| T7 | The intake rule: measured, independent, or a witness | Proposed (the brain page, 11); yours to adopt, then built |
| T8 | A second engine | Yours: Gemini 2.5 Pro (about $0.013 a page), an open model, or Claude; a 20-page pilot first |
| H1 | The Hayasirsa | Yours: the 236 verses read; Finish EN (about $0.94), Add Hindi, release |
| Y2 | The Daivat-Sanhita | Yours: Satavalekar's rights (to the end of 2028), then the vision repair (about $4.20) |
| R1 | Srangam's other edge functions | Next round: not reviewed this round |
"""

STATE = """
## 20. 22 Oct, afternoon: the debt collected and resolved (DOCS85_2026_10_22)

- **Resolved:** the top bar's menus; EN and SC named; "% Devanagari" is not fidelity; the vote of two readings and its
  independence; the benchmark letter by letter; any engine's pages measured; GRETIL's Nirukta read as written; the
  PostgreSQL tests run (283 pass). The register: docs/DEBT_2026-10-22.md.
- **Yours:** the Hayasirsa's release; the Daivat-Sanhita's rights and repair; a second engine; the cap ($95).
- **The repos:** the Automaton `2f68fb95` and Srangam `aec5d41`, pushed, until this release.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, NEEDS),
           (Path("RUNBOOK.md"), RUNBOOK, NEEDS),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, NEEDS),
           (Path("docs/STATE_2026-10-18.md"), STATE, NEEDS),
           (Path(BP), BRAIN, NEEDS),
           (Path(FID), "", "## 6. Limits")]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    plan = {}
    if not Path(DEBT).exists():
        print("FAIL: %s not found (it comes with this release). Nothing written." % DEBT); return 2
    for p, text, needs in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if needs not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (p, needs[:40])); return 1
        for k, (old, new) in enumerate(EDITS.get(str(p).replace("\\", "/"), []), 1):
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (p, k, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if text:
            src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (p, MARK)); return 2
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs85_" + stamp))
        t = p.with_name(p.name + ".tmp_docs85"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
