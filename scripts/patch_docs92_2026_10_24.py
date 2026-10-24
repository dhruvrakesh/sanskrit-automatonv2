#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs92_2026_10_24.py  DOCS92_2026_10_24

Records 24 Oct: what of 23 Oct's work is done and running (measured on the PC and on the site), what failed and why,
and the two fixes of this release: kin_index.py closes its store (KIN_CLOSE_2026_10_24; the Windows test failure) and
C20 in three short pastes (NAME_LINKS_C20_SPLIT_2026_10_24; the site's "Server error"). Also the kinship trial's
measured results, the Nirukta's real cost, and the Daivat-Sanhita scan's terms.

Appends docs/DEBT_2026-10-22.md section 13, STATE section 27, a RUNBOOK section, PLATFORM section 95, ENTERPRISE_PATH
addendum 82, docs/ASKS_2026-10-22.md section 9 and docs/RELATIONS_AND_ASK_2026-10-22.md section 7, each needing
DOCS91_2026_10_23; and puts a SUPERSEDED note at the top of docs/cloud/C20_name_links_2026-10-23.sql and
C20_checks_2026-10-23.sql (each needing NAME_LINKS_C20_2026_10_23). Refuses unless what it records comes with this
release. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs92_ and the date), line endings kept.

  python scripts\\patch_docs92_2026_10_24.py --check
  python scripts\\patch_docs92_2026_10_24.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS92_2026_10_24"
NEEDS = "DOCS91_2026_10_23"
NEEDS_SQL = "NAME_LINKS_C20_2026_10_23"
SPLIT = "NAME_LINKS_C20_SPLIT_2026_10_24"
REQUIRES = {"scripts/patch_kin_close_2026_10_24.py": "KIN_CLOSE_2026_10_24",
            "tests/test_kin_close_2026_10_24.py": "KIN_CLOSE_2026_10_24",
            "docs/cloud/C20_preflight_2026-10-24.sql": SPLIT,
            "docs/cloud/C20a_name_links_view_2026-10-24.sql": SPLIT,
            "docs/cloud/C20b_name_links_fill_2026-10-24.sql": SPLIT,
            "docs/cloud/C20c_name_links_nightly_2026-10-24.sql": SPLIT,
            "docs/cloud/C20_checks_2026-10-24.sql": SPLIT,
            "tests/test_name_links_pg_2026_10_24.py": SPLIT}

DEBT = """
## 13. 24 Oct: what is done and running, what failed and why, the two fixes (DOCS92_2026_10_24)

- **Done on the PC (measured 24 Oct):** the patches ASK_PROF, ENTITY_LINKS_SCHED, HEALTH and DOCS91 applied, every
  hash as released; `541f2e64` pushed. The hourly task runs step d: at 12:01 "STEP d links 9s", entity_links.py
  --scheduled finding the names as at the last rebuild (nothing written), kin_index.py --check rewriting the exports.
  health_watch.py: all ok. The cap: $98.44 spent of $110.00.
- **The kinship trial, run on 23 Oct (19:43-19:49):** 100 entries of each index, 42 calls, 470 relations, $0.164 (the
  plan said about $0.11). Kept after the checks (the words in the entry, the direction): 448; the words not in the entry
  21, the direction against the words 1. Of the 448 kept: named together in our texts 60, near 20, both named but never
  near 94, one not in our texts 8, not tied 266. Raychaudhuri agrees 9 times and differs once (the Vedic Index makes
  Janamejaya a descendant of Pariksit; Raychaudhuri, his son). No father-to-son line of four yet (the trial is small).
- **Why so many are not tied (measured on the 04:00 backup):** of the 378 names left untied, 358 are names our texts'
  list does not hold at all, 10 are ambiguous, and 10 would tie once a homonym mark ("Jaratkaru[2]") or a gloss
  ("Sraddha(devi) (IV)") is set aside; 4 objects are counts ("four sons", "ten wives") and should be set aside as
  unnamed. So the gap is the coverage of our own names, not the tying: a free next step.
- **The Nirukta (GRETIL, Sarup):** 647 of its 649 units translated by Flash on 23 Oct, $5.51 for 647 calls: 2.3 times
  the $2.40 estimated (the estimate used the price of a verse; the Nirukta's units are long prose). Not yet judged: the
  passages' translation_score is a length ratio, not a judgement of meaning (judge_sample.py gives that).
- **Done by you:** the Shukla Yajurveda repaired (1,225 passages; vision 99.1%; to translate, then --release); the
  Daivat-Sanhita withdrawn at 08:27 (02:57 UTC), before the mirror's run of 03:03 UTC, whose groups went from 386 to
  375, all equal.
- **Done on the site:** C19 pasted and checked: the trigger on corner.worker enabled, the outbox's kind 'health'
  allowed, corner.health_state ok, the heartbeat's health ok (08:38), mail on. The alerts are live. Srangam `341cf7f`
  (NAME_LINKS_SITE) built and pushed; the section stays hidden until the view is filled.
- **Failed: tests.test_kin_index_2026_10_23 on Windows (errors=2).** kin_index.py's main() left data/shelf/kin.db
  open (measured: two handles in each of the two tests that read), and Windows will not delete an open file, so each
  test's temp folder could not be removed. Linux deletes open files, which is why the VM and the cloud passed. Fixed by
  KIN_CLOSE_2026_10_24: every store is closed when main() returns or raises. tests/test_kin_close_2026_10_24.py counts
  the open handles on Linux too, so the suite on GitHub (Ubuntu) now catches such a leak. Nothing on the PC was harmed:
  the PC's runs are processes, which close their files on exit.
- **Failed: C20 on the site ("Query failed - Server error", no detail; rolled back).** The same file runs clean on
  PostgreSQL 16 with pg_cron 1.6 as a role that is not a superuser (24 Oct), so the fault is the editor's, most likely
  giving up while the view was filled. Now three short pastes (NAME_LINKS_C20_SPLIT_2026_10_24): a read-only preflight
  (P1-P4: the editor's role and time limit, the volume, pg_cron, the fill's own time on the site); C20a the
  definitions, the view created WITH NO DATA (under a second); C20b the fill (it returns the pairs and the
  milliseconds); C20c the nightly job; checks V1-V6. The reader returns no rows while the view is empty. Measured here:
  600,000 mentions give 316,127 pairs; the fill 3.3 s, a refresh (CONCURRENTLY) 5.8 s. The site has about 41,000 live
  mentions.
- **The Daivat-Sanhita scan** (sources\\Daivat-Sanhita\\DaivatSanhita_201702.pdf, 27.0 MB, fetched by you): a 2017
  scan of Satavalekar's compilation, protected in India to the end of 2028 whatever the scan's date. Local and private:
  it may be imported as a witness for evaluation on the PC (witnesses are never mirrored); never --release, adopt,
  mirror or publish it before 1 January 2029.
"""

STATE = """
## 27. 24 Oct: done, running, failed, fixed (DOCS92_2026_10_24)

| What | State |
|---|---|
| Release | `541f2e64` pushed; KIN_CLOSE, the C20 split and DOCS92 ready |
| Links, scholars' check, kinships' check | hourly on the PC (step d), running |
| The kinship trial | run (300 entries, 470 relations, 448 kept, 182 tied, $0.164); the full run yours (about $4) |
| The Professor | on the PC's Ask (restart the dashboard when idle to load it); the site's waits for A2 |
| Health mail | live (C19 checked) |
| Named together online | C20 failed ("Server error"); the split (preflight, C20a, C20b, C20c) to paste; Srangam pushed |
| The Nirukta (GRETIL) | translated, 647 of 649 ($5.51); to judge, then to adopt |
| The Shukla Yajurveda | repaired by you; to translate, then --release |
| The Daivat-Sanhita | withdrawn before the 03:03 UTC mirror (groups 386 to 375); the 2017 scan local only |
| The vision round | Yajnavalkya and 7 failed pages to read again; the benchmark's Manu label to mend |
| test_kin_index on Windows | fixed (KIN_CLOSE) |
"""

RUNBOOK = """
## 24 Oct: KIN_CLOSE, C20 in three pastes, the rest (DOCS92_2026_10_24)

From the repository root (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`):

1. `python scripts\\patch_kin_close_2026_10_24.py --check`, then without --check; the same for
   `patch_docs92_2026_10_24.py`. Then `python -m unittest tests.test_kin_index_2026_10_23 tests.test_kin_close_2026_10_24`
   and `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.
2. Named together online, in the Lovable Cloud SQL editor, one paste each: docs\\cloud\\C20_preflight_2026-10-24.sql
   P1, P2, P3, P4 (read-only; P4 says how long the fill takes); C20a_name_links_view_2026-10-24.sql; V1 of
   C20_checks_2026-10-24.sql; C20b_name_links_fill_2026-10-24.sql; V1-V4; C20c_name_links_nightly_2026-10-24.sql; V5;
   after a night V6. Then Publish Srangam in Lovable. C20_name_links_2026-10-23.sql is superseded: never paste it.
3. The kinships' full run: `python scripts\\kin_index.py --per-source 0` (the plan), then
   `python scripts\\kin_index.py --yes --per-source 0 --max-usd 4.50`.
4. The Nirukta judged: `python scripts\\judge_sample.py --doc nirukta__w_gretil --sample-pct 10` (the dry run prices
   it), then the same with `--yes --max-usd 0.30`.
5. The Shukla Yajurveda: `python scripts\\translate_passages.py --db data\\context.db --doc
   yajur_veda_shukla_yajur_veda --engine gemini:gemini-2.5-flash --limit 20` (a trial), then without --limit; then
   `python scripts\\repair_text.py --doc yajur_veda_shukla_yajur_veda --release`.
"""

PLATFORM = """
## 95. kin_index's run and its stores; C20 in parts (DOCS92_2026_10_24)

- **scripts/kin_index.py** (KIN_CLOSE_2026_10_24): main(argv, caller) runs run(argv, caller) and closes every store
  open_store() opened (the module's _STORES), whatever run() returned or raised.
- **corpus.name_links** (C20a): created WITH NO DATA; filled by C20b and refreshed nightly by C20c's job.
- **corpus._refresh_name_links()** returns jsonb {pairs, was_filled, ms}: REFRESH when the view is empty, REFRESH
  CONCURRENTLY when it is filled; SECURITY DEFINER, the owner's only.
- **public.corpus_reader_name_links(p_canonical, k)** behind corpus._reader_gate(): no rows while the view is empty;
  k kept between 1 and 50.
- **cron.job srangam-corpus-name-links** (C20c): 40 4 * * *, `SELECT corpus._refresh_name_links();`.
"""

EP = """
## Addendum 2026-10-24 (82) (DOCS92_2026_10_24)

| Key | Item | State |
|---|---|---|
| relations-index | The indexes' kinships read and checked | Trial run (448 kept, 182 tied); the full run next (about $4) |
| relations-names | Our names' coverage of the indexes' people | Measured: 358 of 378 untied names are not in our list; next |
| names-ui | The name page: named together | C20 split to paste (preflight, C20a, C20b, C20c); Srangam pushed |
| alerts | A mail when the desk's tasks fail | Live (C19 checked 24 Oct) |
| kin-close | kin_index.py's store left open (Windows) | Fixed (KIN_CLOSE_2026_10_24) |
| nirukta-witness | GRETIL's Nirukta translated, judged, released | Translated ($5.51); judge next |
| yajur-shukla | The Shukla Yajurveda repaired | Yours: translate, then --release |
| daivat-rights | The Daivat-Sanhita | Withdrawn before the 03:03 UTC mirror; the 2017 scan local only until 2029 |
"""

ASKS = """
## 9. 24 Oct: "is all this done ... updated and cronning" (DOCS92_2026_10_24)

- **On the PC, running:** the links, the scholars' check and the kinships' check every hour (step d); the health in
  each heartbeat; the daily backup; the mirror. The Professor on the PC's Ask once the dashboard is restarted.
- **On the site, running:** the health mail (C19). Not yet: "Named together with" (C20 failed; the split to paste),
  then refreshed nightly; the Professor (A2) and the scholars' claims (B2) are not built.
- **Done:** the decisions (the Nirukta's PDF and translation, alerts, the kinship trial, H2, the Daivat-Sanhita); the
  kinship trial run; the Nirukta translated (not yet judged); the Daivat-Sanhita withdrawn (the mirror ran after).
- **Failed and fixed:** test_kin_index on Windows (KIN_CLOSE); C20 (the split).
"""

RELATIONS = """
## 7. 24 Oct: the trial measured; R4 in three pastes (DOCS92_2026_10_24)

- **R2 and R3, the trial:** 300 entries, 470 relations, 448 kept, 182 tied to our names; of the kept, 60 named together
  in our texts, 20 near, 94 never near, 8 with one side not in our texts, 266 not tied; Raychaudhuri agrees 9, differs 1.
- **The names' coverage:** 358 of the 378 untied names are not in our names' list; 10 more tie once homonym marks and
  glosses are set aside; counts of people ("four sons") are to be set aside as unnamed. The next free step: measure how
  many of those names our texts hold without our list naming them.
- **R4 on the site:** C20 in three pastes (preflight, C20a, C20b, C20c), because the one paste ended "Server error".
"""

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/ASKS_2026-10-22.md"), ASKS),
           (Path("docs/RELATIONS_AND_ASK_2026-10-22.md"), RELATIONS)]

SQL_NOTE = {
    Path("docs/cloud/C20_name_links_2026-10-23.sql"):
        "-- SUPERSEDED 2026-10-24 (DOCS92_2026_10_24): do not paste this file. On the site it ended \"Query failed -\n"
        "-- Server error\" and rolled back. Paste instead, one at a time: C20_preflight_2026-10-24.sql (P1-P4),\n"
        "-- C20a_name_links_view_2026-10-24.sql, C20b_name_links_fill_2026-10-24.sql,\n"
        "-- C20c_name_links_nightly_2026-10-24.sql, with C20_checks_2026-10-24.sql. Kept as the record of 23 Oct.\n",
    Path("docs/cloud/C20_checks_2026-10-23.sql"):
        "-- SUPERSEDED 2026-10-24 (DOCS92_2026_10_24): use C20_checks_2026-10-24.sql.\n",
}


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (it comes with this release). Nothing written." % (f, m))
            return 1
    plan = {}
    jobs = [(p, text, NEEDS, "append") for p, text in TARGETS] + \
           [(p, text, NEEDS_SQL, "prepend") for p, text in SQL_NOTE.items()]
    for p, text, needs, how in jobs:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if needs not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (p, needs)); return 1
        if how == "append":
            src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        else:
            src = text + src
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs92_" + stamp))
        t = p.with_name(p.name + ".tmp_docs92"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
