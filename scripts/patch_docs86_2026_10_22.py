#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs86_2026_10_22.py  DOCS86_2026_10_22

Records what your run of 22 Oct, afternoon, showed (the release 33b50ae5 and its checks): every patched file equal to
the copy tested; the site as the register said (CHECKS_debt H1 to H4); and what the run found, mended by
WITNESS_FIX_2026_10_22 (the Nirukta's witness was not written again: the Latin guard; an e-text reference read as
ours) and LEGACY_TESTS_2026_10_22 (three pytest-style tests that never ran; test_docs76's replay); what is open (the
three errors of test_mbh_prose on the PC alone; GRETIL forbids directory listings; the Daivat-Sanhita in the corpus).

Appends docs/DEBT_2026-10-22.md section 7, STATE section 21, a RUNBOOK section, PLATFORM section 89 and
ENTERPRISE_PATH addendum 76, each needing DOCS85_2026_10_22; needs docs/cloud/CHECKS_followup_2026-10-22.sql, which
comes with this release. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs86_<date>), line endings
kept.

  python scripts\\patch_docs86_2026_10_22.py --check
  python scripts\\patch_docs86_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS86_2026_10_22"
NEEDS = "DOCS85_2026_10_22"
CHECKS = "docs/cloud/CHECKS_followup_2026-10-22.sql"

DEBT = """
## 7. After the release: what the run of 22 Oct, afternoon, showed (DOCS86_2026_10_22)

- **Released:** `33b50ae5`, pushed and verified. The sixteen files the seven patchers wrote are, byte for byte, the
  copies tested (md5, read from the PC).
- **The site (CHECKS_debt):** the Hayasirsa's held version, 1,531 passages, 158 with the working English, 1,174 Hindi,
  158 vectors, 246 mentions, and no scholarly rows (a held text sends none); of the witnesses only the two adopted
  (the Surya's 515, GRETIL's Markandeya 5,240); the Daivat-Sanhita 13,887 live passages, no English, no title; the
  mirror's last ten runs all finished (none between 19:02 and 02:39 UTC: the PC off). At 09:02 UTC it sent 274
  passages of the Surya e-text's new working English (your run: 483 of 483 translated, mean QA 0.990; names; vectors),
  386 groups equal.
- **Found, and mended (WITNESS_FIX_2026_10_22):** the Nirukta's witness was not written again. ETEXT_DOTS keeps its
  references, sigla and English notes in Latin, and the Latin guard counted them as debris (16.5% of its verses; it
  refuses above 10%), so `--write` stopped after the wipe, and `--ingest` took the pages of 11:00 again (34,183 dandas
  still). The guard now leaves out what is kept in Latin (1.1%); checked end to end: 649 verses in 54 pages, 4,676
  dandas, 57 avagrahas, 804 quotation marks. And with an e-text as the reference (db:nirukta__w_gretil),
  TRIANGULATE read it as ours and called GRETIL's text "usable: mend it"; where our print's two readings agree
  against an e-text, the print reads otherwise (11.27 aksharas in 100 against GRETIL's Nirukta, from Lakshman
  Sarup's edition by its header): not mends. Our readings of the Nirukta: vision 4.16 own misreadings in 100,
  Tesseract 8.72; 67.07% and 62.02% agreement with GRETIL.
- **Found, and mended (LEGACY_TESTS_2026_10_22):** test_morph_parse, test_normalize and test_sandhi_split were pytest
  functions: unittest ran none ("NO TESTS RAN"); test_normalize called a command line normalize_text.py no longer
  has. They are unittest tests now. test_docs76 failed on the PC (its replay against docs that DOCS77 to DOCS85 wrote
  again); it skipped on copies without its backups, which is why the VM suite was green.
- **Found, and corrected in the RUNBOOK:** the loop of the DOCS85 section printed each module's last line, not its
  verdict, so passing modules showed their own prints; the DOCS86 section's loop prints the failing ones only.
- **Open:** test_mbh_prose_2026_10_14 has 3 errors on the PC alone (the same files pass in the VM copy): its
  traceback decides. GRETIL forbids directory listings (403 Forbidden for /gretil/1_sanskr/1_veda/), so the Rgveda's
  and the Samaveda's files are to be found from GRETIL's own pages, not listed. The Daivat-Sanhita is live in the
  corpus: whether a signed-in reader sees it is CHECKS_followup J1; `repair_text.py --doc Daivat-Sanhita --withdraw`
  takes it off the site (undone by --restore), if you so decide. The Pro pilot's pre-flight priced 20 pages at
  Flash's metered $0.00387 a page ($0.077); Pro's tokens cost about 4 times as much: about $0.31.
"""

STATE = """
## 21. 22 Oct, afternoon: released, checked, two mends (DOCS86_2026_10_22)

- **Released:** the Automaton `33b50ae5` (the seven patches of DOCS85), pushed; Srangam `aec5d41`, unchanged.
- **Checked:** the patched files as tested; the site as the register said; the Surya e-text's working English made
  (483) and on its way to the site (274 passages sent at 09:02 UTC).
- **Mended:** WITNESS_FIX_2026_10_22 (the Nirukta's witness; an e-text reference) and LEGACY_TESTS_2026_10_22 (three
  tests that never ran; test_docs76). Open: test_mbh_prose's three errors on the PC; the Daivat-Sanhita's rights.
"""

RUNBOOK = """
## The afternoon's follow-up: the Nirukta again, the old tests (DOCS86_2026_10_22)

docs/DEBT_2026-10-22.md, section 7. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`,
then `Set-Location $A`. Nothing below spends.
1. Apply, each with `--check` first: `scripts\\patch_witness_fix_2026_10_22.py`, `scripts\\patch_legacy_tests_2026_10_22.py`,
   `scripts\\patch_docs86_2026_10_22.py`. Then `python -m unittest tests.test_witness_fix_2026_10_22
   tests.test_legacy_tests_2026_10_22 tests.test_docs86_2026_10_22 tests.test_etext_dots_2026_10_22
   tests.test_engines_2026_10_22 tests.test_morph_parse tests.test_normalize tests.test_sandhi_split
   tests.test_docs76_2026_10_18`.
2. The whole suite, each module's verdict (the DOCS85 section's loop printed each module's last line instead):
   `$fail = 0; Get-ChildItem tests\\test_*.py | ForEach-Object { $m = "tests." + $_.BaseName; $o = (python -m unittest
   $m 2>&1 | Out-String); if ($o -match "(?m)^FAILED.*$") { $fail++; "$m : " + $Matches[0] } elseif ($o -match
   "NO TESTS RAN") { "$m : no tests" } }; "modules failing: $fail"`.
3. The Nirukta's witness, the preview first: `python scripts\\etext_witness.py --doc nirukta --file
   sources\\nirukta\\sa_yAska-nirukta.htm --category vedanga` must end "reads as 649 verses in 54 pages" with NEXT
   `--write`. Only then, with the dashboard idle: the backup (db_backup.py), `wipe_doc.py --doc nirukta__w_gretil
   --yes`, the same preview with `--write --force`, `etext_witness.py --doc nirukta --ingest --witness
   nirukta__w_gretil`, and the measure (`source_fidelity.py --ref db:nirukta__w_gretil --cand db:nirukta --cand
   vision:nirukta --cand raw:nirukta --pair vision:nirukta,raw:nirukta`). The witness's pages then hold 4,676 dandas.
4. The site, read-only: `docs\\cloud\\CHECKS_followup_2026-10-22.sql`, one block at a time (J1 who may read the
   corpus, J2 whether the site lists the Daivat-Sanhita, J3 the Surya e-text after the mirror's runs).
"""

PLATFORM = """
## 89. After the release: two mends found by the run (DOCS86_2026_10_22)

| Marker | Files | What |
|---|---|---|
| WITNESS_FIX_2026_10_22 | etext_witness.py, source_fidelity.py (+ the replay chains of test_etext_dots and test_engines) | kept_out() leaves out what ETEXT_DOTS keeps in Latin (the Nirukta 16.5% to 1.1%, under the guard's 10%); is_ours(): a db: witness (an e-text) is not one of our readings |
| LEGACY_TESTS_2026_10_22 | tests/test_morph_parse.py, test_normalize.py, test_sandhi_split.py, test_docs76_2026_10_18.py | three pytest functions made unittest tests; docs76's replay accepts a later patch's backup |
| DOCS86_2026_10_22 | DEBT 7, STATE 21, RUNBOOK, this section, ENTERPRISE_PATH 76 | the record; CHECKS_followup (read-only) |

- **Released before them:** `33b50ae5`; every file the seven patchers wrote equal to the copy tested.
- **Open:** test_mbh_prose's three errors on the PC alone; GRETIL's directories are not listed (403).
"""

EP = """
## Addendum 2026-10-22 (76) (DOCS86_2026_10_22)

| # | Item | State |
|---|---|---|
| T5b | The Nirukta's witness written again | Mended: WITNESS_FIX_2026_10_22; yours: preview, then wipe, write, ingest (free) |
| T2b | An e-text reference read as ours | Mended: WITNESS_FIX_2026_10_22 |
| T9 | Tests that never ran (pytest style); test_docs76 | Mended: LEGACY_TESTS_2026_10_22 |
| T10 | test_mbh_prose: 3 errors on the PC alone | Open: its traceback |
| F3b | GRETIL's Rgveda and Samaveda | Open: no directory listing (403); from GRETIL's own pages |
| Y2b | The Daivat-Sanhita live in the corpus | Yours: J1 and J2, then keep or --withdraw |
"""

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT, NEEDS),
           (Path("docs/STATE_2026-10-18.md"), STATE, NEEDS),
           (Path("RUNBOOK.md"), RUNBOOK, NEEDS),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, NEEDS),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, NEEDS)]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    plan = {}
    if not Path(CHECKS).exists():
        print("FAIL: %s not found (it comes with this release). Nothing written." % CHECKS); return 2
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
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs86_" + stamp))
        t = p.with_name(p.name + ".tmp_docs86"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
