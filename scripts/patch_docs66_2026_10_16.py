#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs66_2026_10_16.py  DOCS66_2026_10_16

Records 16 Oct (night): the dashboard shows BM1, the Claude credit and each text's state (BENCH_DESK_2026_10_16).
docs/BENCH_DESK_2026-10-16.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 69), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 56), each needing DOCS65_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs66_<date>), line endings kept.

  python scripts/patch_docs66_2026_10_16.py --check
  python scripts/patch_docs66_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS66_2026_10_16"

PLATFORM = """

## 69. The dashboard shows BM1, the Claude credit and each text's state (DOCS66_2026_10_16)

**16 Oct (IST).** docs/BENCH_DESK_2026-10-16.md has the details.
- **The ask:** "UI/UX on the dashboard here needs to reflect the latest state and intuitive wiring."
- **BENCH_DESK_2026_10_16 (scripts/dashboard.py, scripts/dashboard_static.html):** the Benchmarks page (a link in
  the header) opens with BM1: the caps, the next step with its price, a grid of what each arm has made per text, the
  spend and the measured price of a verse per arm, the judge's line, the last report's numbers with their intervals
  (marked partial or stale), and the steps as buttons (a job of kind "bench", doc BM1; a paid one asks first and
  runs with --yes --max-usd, at most $12.00 a press). /api/bench; /benchmarks/bm1/report (the private report, on
  127.0.0.1 only). The main table: a chip for the register's state of a text (withdrawn, set aside, in repair) and
  one for its scholarly English. The Usage tab: the spend cap (Google) and the Claude credit apart, the steps since
  the credit began by name, BM1's line.
- **bench_mitra.py:** an arm is priced by its own spend once it has made 10 verses (gemini-2.5-flash cost $0.005 a
  BM1 verse, twice the corpus's: the flash arm had stopped at its --max-usd with 150 of 200); the report's NEXT line
  is PowerShell's Start-Process.
- **Where BM1 stands:** scholar and sonnet1 complete; flash 150 of 200 (the Satapatha and the Ramayana to make);
  the judge and the full report to run. BM3 and BM2 come after.

**Tests:** `tests/test_bench_desk_2026_10_16.py` (9); test_classify_hindi_2026_10_16 (dashboard.py) and
test_judge_desk_2026_10_11 (dashboard_static.html) follow (.bak_benchdesk_).
"""

RUNBOOK = """

## BM1 from the dashboard (DOCS66_2026_10_16)

1. The Benchmarks page (the header's link): BM1's Next line names the step to take and its price.
2. A paid button (Run an arm, Judge them) asks first, then runs bench_mitra.py with --yes --max-usd (the estimate and
   a third more); its last lines show below the buttons; the page reads BM1 again when it ends.
3. Make the report again (free), then "The full report" (served on this computer only).
4. The same steps by hand: docs/BENCH_MITRA_2026-10-16.md, section 6.
"""

EP = """

## Addendum 2026-10-16 (56) (DOCS66_2026_10_16)

| # | Item | State |
|---|---|---|
| BD1 | The dashboard shows BM1 and runs its steps; the Claude credit and the spend cap apart; a text's register state and scholarly English on its row (BENCH_DESK_2026_10_16) | Built and tested |
| BM1 | Mitrasamgraha, 200 verses, three arms | scholar and sonnet1 done; flash 150 of 200; the judge and the full report to run |
| BM3 | The blind side-by-side of the arms by judges of both families | After BM1's judge |
| BM2 | Our own gold set, read by a person | A person's time |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS65_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS65_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS65_2026_10_16")]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs.encode() not in raw:
            print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, needs)); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs66_" + stamp))
        t = p.with_name(p.name + ".tmp_docs66"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
