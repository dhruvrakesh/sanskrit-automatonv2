#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs68_2026_10_16.py  DOCS68_2026_10_16

Records 16 Oct (late night): BM3's pilot (docs/BM3_PILOT_2026-10-16.md), its check with the scholarly arm's notes
withheld (BENCH_DUEL_NOTES_2026_10_16), and BM2, your blind reading on the dashboard (BENCH_GOLD_2026_10_16,
docs/BENCH_GOLD_2026-10-16.md).

Appends to docs/PLATFORM_2026-10-04.md (section 71), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 58), each needing DOCS67_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs68_<date>), line endings kept.

  python scripts/patch_docs68_2026_10_16.py --check
  python scripts/patch_docs68_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS68_2026_10_16"

PLATFORM = """

## 71. BM3's pilot; its check; BM2, your blind reading (DOCS68_2026_10_16)

**16 Oct (IST).** docs/BM3_PILOT_2026-10-16.md and docs/BENCH_GOLD_2026-10-16.md have the details.
- **BM3's pilot** (40 units, 42 verses, both duel-v1 judges, the published English as a fourth; $3.26): the
  scholarly pipeline above Sonnet alone 0.80 [0.68, 0.91] (gemini-2.5-pro, which has no stake in it) and 0.79 [0.65,
  0.90] (Claude Opus); above flash 0.89 and 0.83; Sonnet above flash 0.70 and 0.86. Major errors per ten verses:
  scholar 0.24 (both judges), sonnet1 1.19 / 0.24, flash 3.81 / 3.57. The opposite of BM1's chrF, which measures
  nearness to 19th-century English. A pilot: five units a text; only the scholarly arm has notes (they name it).
- **BENCH_DUEL_NOTES_2026_10_16 (bench_duel.py --no-notes):** the check, the pilot's units again with the scholarly
  arm's notes withheld; its readings stored apart, its own report (BM3_nonotes_*). About $3.0.
- **BENCH_GOLD_2026_10_16 (scripts/bench_gold.py, BM2):** the dashboard's /benchmarks/bm2: BM3's units in its
  order, the Sanskrit and four translations as Translation 1 to 4 (an order of their own, no names, no notes), the best
  and the wrong marked, a note; then who made each and what each judge chose. Stored in BM2's folder (person.jsonl);
  the report says how often each judge's best is the reader's, and how many of the wrong the judge caught. Free.
  The Benchmarks page has BM2's section and BM3's check.

**Tests:** `tests/test_bench_gold_2026_10_16.py` (5), `tests/test_bench_gold_desk_2026_10_16.py` (6),
`tests/test_bench_duel_notes_2026_10_16.py` (3); test_bench_duel_desk_2026_10_16 follows (.bak_benchgold_).
"""

RUNBOOK = """

## BM2, your blind reading; BM3's check (DOCS68_2026_10_16)

1. The Benchmarks page, BM2's section: Read blind (or http://127.0.0.1:5057/benchmarks/bm2). Say who is reading
   (kept in this browser), pick the best of the four (keys 1 to 4, E for equal), mark any wrong in meaning, Enter.
2. Make the report (free) when you stop; read each judge against you.
3. BM3's check (once the pilot is read): Run the check (about $3.0), then Make the check's report (free); or
   `python scripts\\bench_duel.py --units 40 --with-reference --no-notes --yes --max-usd 4.50` and
   `python scripts\\bench_duel.py --report --no-notes`.
"""

EP = """

## Addendum 2026-10-16 (58) (DOCS68_2026_10_16)

| # | Item | State |
|---|---|---|
| BM3 | The blind side-by-side, duel-v1 judges of both families | The pilot done (40 units, $3.26): the scholarly pipeline first; more units need the spend cap |
| BM3c | The check, the scholarly arm's notes withheld (BENCH_DUEL_NOTES_2026_10_16) | Built and tested; to run (about $3.0) |
| BM2 | Your blind reading on the dashboard (BENCH_GOLD_2026_10_16) | Built and tested; a person's time (40 units first) |
| J2 | A judge told the emendations, the thinking off | After the baseline, as agreed |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS67_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS67_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS67_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs68_" + stamp))
        t = p.with_name(p.name + ".tmp_docs68"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
