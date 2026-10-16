#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs67_2026_10_16.py  DOCS67_2026_10_16

Records 16 Oct (night): BM1's results (docs/BM1_RESULTS_2026-10-16.md), BM3 built and on the dashboard
(BENCH_DUEL_2026_10_16, docs/BENCH_DUEL_2026-10-16.md), and Srangam's tests given the waits a busy computer needs
(TEST_WAIT_2026_10_16).

Appends to docs/PLATFORM_2026-10-04.md (section 70), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 57), each needing DOCS66_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs67_<date>), line endings kept.

  python scripts/patch_docs67_2026_10_16.py --check
  python scripts/patch_docs67_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS67_2026_10_16"

PLATFORM = """

## 70. BM1's results; BM3, the blind side-by-side; Srangam's tests wait as a busy computer needs (DOCS67_2026_10_16)

**16 Oct (IST).** docs/BM1_RESULTS_2026-10-16.md and docs/BENCH_DUEL_2026-10-16.md have the details.
- **BM1, done** (200 verses, three arms, 760 judgements; about $12.75): chrF against the published English flash
  35.85, sonnet1 38.26, scholar 36.59 (sonnet1 - flash +2.41 [1.65, 3.16]; scholar - sonnet1 -1.67 [-2.33, -0.98]);
  judge-v1 fidelity 4.84 / 4.67 / 4.87 (scholar - sonnet1 +0.20 [0.11, 0.29]; scholar - flash +0.03 [-0.08, 0.12]),
  the published English 3.47 (46.7% passed). judge-v1 is saturated and partial (the flash model judging; the scholarly
  arm revised against it); the two measures disagree; no change to the pipeline follows from BM1 alone. Two
  judgements failed (a timeout) and are read again by the next score step. The method page's Satapatha claim is
  corrected: the pairs drift, none is marked; whole-window chrF orders the arms as before.
- **BENCH_DUEL_2026_10_16 (scripts/bench_duel.py, BM3):** BM1's units, the three arms' English and the published
  English side by side, blind and shuffled, read by scholar_duel.py's duel-v1 judges (gemini-2.5-pro, Claude Opus 5.5;
  the Debroy register); per judge the pairs' shares with intervals, errors and ranks; both judges' agreement and splits
  by family. A fixed balanced order, so any part read is a random part; kind bench_duel, doc BM3:<text>. On the
  dashboard (patch_bench_duel_desk): BM3's section, the pilot (40 units, about $4.5) then 40 more a press, the button
  withheld when the spend cap cannot hold its Google part; /benchmarks/bm3/report; on a phone the sections scroll.
- **TEST_WAIT_2026_10_16 (Srangam):** findBy* and waitFor wait 5 s (setup.ts), a test 20 s (vitest.config.ts): on
  16 Oct a busy computer failed six tests in one run and another in the next, none in the code changed.

**Tests:** `tests/test_bench_duel_2026_10_16.py` (7), `tests/test_bench_duel_desk_2026_10_16.py` (8);
test_bench_desk_2026_10_16 follows (.bak_benchduel_). Srangam: src/__tests__/test-wait.test.ts (2).
"""

RUNBOOK = """

## BM3, the blind side-by-side (DOCS67_2026_10_16)

1. BM1 complete (the Benchmarks page says Done), then BM3's section: Next names the part to read and its price.
2. The pilot (40 units, both judges, the published English among the translations): the button, or
   `python scripts\\bench_duel.py --units 40 --with-reference --yes --max-usd 6.00`.
3. Make the report again (free); read each judge apart, then where both agree.
4. More units: the button reads 40 more a press, when the spend cap can hold its Google part
   (`python scripts\\set_budget.py` shows the cap).
5. A run stopped half way: `python scripts\\bench_duel.py --settle` (free).
"""

EP = """

## Addendum 2026-10-16 (57) (DOCS67_2026_10_16)

| # | Item | State |
|---|---|---|
| BM1 | Mitrasamgraha, 200 verses, three arms, chrF and judge-v1 | Done (2 judgements to read again); results in docs/BM1_RESULTS_2026-10-16.md |
| BM3 | The blind side-by-side, duel-v1 judges of both families (BENCH_DUEL_2026_10_16) | Built and tested; the pilot to run (about $4.5) |
| BM2 | A person's blind reading of the same units | Its page on the dashboard, next |
| TW1 | Srangam's tests: the waits set once (TEST_WAIT_2026_10_16) | Built and tested |
| J2 | A judge told the emendations, the thinking off | After the baseline, as agreed |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS66_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS66_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS66_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs67_" + stamp))
        t = p.with_name(p.name + ".tmp_docs67"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
