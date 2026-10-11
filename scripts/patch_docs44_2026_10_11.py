#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs44_2026_10_11.py  DOCS44_2026_10_11

Records the night of 11 Oct, after ETEXT_WITNESS (73f426b): the Tantric Texts repaired (debris 57.4% to 3.9%),
judge v2 on the 47 texts, the placeholder that "released" a text that does not exist, and BENCHMARK_2026_10_11
(every reading of a text compared, against archive.org's OCR and a critical e-text; the debris's effect on the
translation, measured). docs/BENCHMARK_2026-10-11.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 47), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 34), each needing DOCS43_2026_10_11.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs44_<date>), line endings kept.

  python scripts/patch_docs44_2026_10_11.py --check
  python scripts/patch_docs44_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS44_2026_10_11"

PLATFORM = """

## 47. The readings benchmarked; the Tantric Texts repaired (DOCS44_2026_10_11)

**11 Oct, night (IST), after the release of ETEXT_WITNESS (`73f426b`).**
- **The Tantric Texts were repaired:** debris 57.4% to 3.9%, vision 0% to 95.8%, 2,946 passages to
  translate. Hayashirsha was repaired and is in repair (the site keeps its English). The Natyasastra's
  vision run started (546 pages). Ganita was accepted as complete.
- **Judge v2:** 26 material, 12 moderate, 9 cosmetic of 47. Shatpath became cosmetic. Three texts cut
  into a passage a page became material, and four became moderate.
- **The tests:** one fixture's file name (`bad"name.txt`) is not allowed on Windows; it is fixed.
- **A placeholder command** (`--doc Bodhicaryavatara__w_gretil --release`) wrote "released" for a
  text that does not exist. `--release` now refuses such a text, and a new witness is always local.

**BENCHMARK_2026_10_11** (`scripts/benchmark_sources.py`, `scripts/patch_benchmark_2026_10_11.py`):
- **Every reading of a text, on the same pages:** Tesseract, vision, the repair, the database, the
  text before its repair (the oldest repair backup, read immutable), the witnesses, archive.org's OCR
  and the critical e-texts in `sources\\<doc>\\`.
- **Each is measured by** the letters misread and, against a critical text, by its F1.
- **The translation:** the share of the English made before the repair that came from damaged text
  (material from 10%), and the English now.
- **Shown on** the repair page (*Benchmark the readings*) and on `/benchmarks`.

**Tests:** `tests/test_benchmark_2026_10_11.py` (13).
"""

RUNBOOK = """

## Benchmark the readings (DOCS44_2026_10_11)

1. **Patch:**
   - `python scripts\\patch_benchmark_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle.
2. **One text:** `python scripts\\benchmark_sources.py --doc <doc>`. It is free and read-only; it
   prints the table, the opinion and the next step.
3. **Every text:** `python scripts\\benchmark_sources.py --all`, then open
   `http://127.0.0.1:5057/benchmarks`.
4. **To compare with archive.org's own OCR of the scan:**
   `python scripts\\source_desk.py --doc <doc> --fetch <the scan's identifier> --kind text --force`
   (the benchmark's ALSO line names it), then benchmark again. The file stays in `sources\\<doc>\\`
   and is not ingested.
5. **Never paste a command with a `<placeholder>` in it.** Fill it in first.
"""

EP = """

## Addendum 2026-10-11 (34) (DOCS44_2026_10_11)

| # | Item | State |
|---|---|---|
| S2/S3 | E-text witness; the missing page offered | **Released** (73f426b) |
| J2 | Judge v2 | **Released**; 26 material, 12 moderate, 9 cosmetic of 47 |
| O3 | Tantric Texts repaired (57.4% to 3.9% debris); Hayashirsha re-ingested, in repair; Natyasastra vision running; Ganita complete | The user's: translate the Tantric Texts, Karan Aagama and Hayashirsha; release Karan and Hayashirsha after |
| B1 | The benchmark: readings against each other, archive.org's OCR and a critical e-text; the debris's effect on the translation | Built and tested (BENCHMARK_2026_10_11) |
| T1 | The translation judged against the critical text (judge_sample.py's judge, the witness as the source) | Next; paid, capped, dry-run first |
| R3 | The in-place re-ingest; taking an offered page | Next |
| C14 | Sources wanted on the site | Designed; with the benchmarks as a fourth input |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS43_2026_10_11"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS43_2026_10_11"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS43_2026_10_11")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs44_" + stamp))
        t = p.with_name(p.name + ".tmp_docs44"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
