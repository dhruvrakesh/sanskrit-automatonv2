#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs65_2026_10_16.py  DOCS65_2026_10_16

Records 16 Oct (evening): BM1, the first benchmark against published translations (BENCH_MITRA_2026_10_16), and a
printed ornament no longer taken for the scanner's debris (ORNAMENT_2026_10_16). docs/BENCH_MITRA_2026-10-16.md has
the details.

Appends to docs/PLATFORM_2026-10-04.md (section 68), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 55), each needing DOCS64_2026_10_16.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs65_<date>), line endings kept.

  python scripts/patch_docs65_2026_10_16.py --check
  python scripts/patch_docs65_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS65_2026_10_16"

PLATFORM = """

## 68. BM1: our English against published translations; a printed ornament is not debris (DOCS65_2026_10_16)

**16 Oct (IST).** docs/BENCH_MITRA_2026-10-16.md has the details.
- **The ask:** benchmark against what exists, and "establish a worthy baseline" without changing variables. BM1
  measures the pipeline as it is: the same prompts, engines, flags and judge (judge-v1, unchanged).
- **BENCH_MITRA_2026_10_16 (scripts/bench_mitra.py):** 200 verses (25 in a row from each of eight Mitrasamgraha test
  files of the Hindu traditions; not the Gita, not the Buddhist files), three arms (gemini-2.5-flash one pass, Sonnet
  5.5 one pass, the scholarly pipeline as on 15 Oct), scored by chrF against the published English (as sacrebleu,
  also with the diacritics folded) and by judge-v1 on the Sanskrit (the published English too, opt-in), paired
  bootstrap intervals. Every step runs the pipeline's own scripts on a bench database outside the repository; its
  calls go into data/context.db's usage_log as kind bench_<kind>, doc BM1:<text> (the credit and the spend cap count
  them; the Library's prices do not). Private evaluation only: nothing of the dataset is committed or reaches the
  site. About $13.9 in all: $10.6 the Claude credit, $3.2 Google.
- **ORNAMENT_2026_10_16:** a line that is only the vision OCR's ornament marker ("<decorative line>") is no longer
  read as OCR debris: scholar_translate.readiness sends such a verse, redeem.py counts its English as clean, and
  Srangam's provisional chip (found by Lovable on clean verses) follows the same rule. Three verses carry it.

**Tests:** `tests/test_bench_mitra_2026_10_16.py` (12), `tests/test_ornament_2026_10_16.py` (4);
test_ready_price_2026_10_16 and test_classify_hindi_2026_10_16 follow (.bak_ornament_). Srangam:
src/__tests__/reader-ornament.test.tsx (4).
"""

RUNBOOK = """

## BM1, the benchmark against published translations (DOCS65_2026_10_16)

1. `python scripts\\bench_mitra.py --sample` (free): the 200 verses and the bench databases, in
   D:\\Sanksrit Automatons\\benchmarks\\bm1 (outside the repository; private).
2. `python scripts\\bench_mitra.py` (free): what each arm would send and cost, the credit and the cap.
3. `--arm flash`, `--arm sonnet1`, `--arm scholar`, each with `--yes --max-usd N` (they can run at once).
4. `--score --judge-reference --yes --max-usd N`, then `--report` (free): BM1_report.html (private) and
   BM1_summary.json (numbers only).
5. A step stopped half way: run it again (it goes on), or `--settle` (free) to put its spend in the ledger.
"""

EP = """

## Addendum 2026-10-16 (55) (DOCS65_2026_10_16)

| # | Item | State |
|---|---|---|
| BM1 | Mitrasamgraha, 8 files of the Hindu traditions, 200 verses, three arms, chrF and judge-v1 (BENCH_MITRA_2026_10_16) | Built and tested; to run (about $13.9) |
| BM3 | The blind side-by-side of the arms by judges of both families | After BM1's numbers |
| BM2 | Our own gold set, read by a person | A person's time |
| OR1 | A printed ornament not taken for debris (ORNAMENT_2026_10_16), the automaton and Srangam alike | Built and tested |
| J2 | A judge told the emendations, the thinking off | After the baseline, as asked |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS64_2026_10_16"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS64_2026_10_16"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS64_2026_10_16")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs65_" + stamp))
        t = p.with_name(p.name + ".tmp_docs65"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
