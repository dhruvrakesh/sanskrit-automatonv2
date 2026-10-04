#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs6_2026_10_04.py  DOCS6_2026_10_04

Appends to docs/PLATFORM_2026-10-04.md (section 9) and RUNBOOK.md: what METER_GATES and
DIAG_ORPHANS changed. Marker-idempotent per file, backup first.

  python scripts/patch_docs6_2026_10_04.py --check
  python scripts/patch_docs6_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS6_2026_10_04"

PLATFORM = """

## 9. Meters, gates and orphans (METER_GATES_2026_10_04, DIAG_ORPHANS_2026_10_04, DOCS6_2026_10_04)

**Every paid call site is now metered and asks the budget:**

- **The dashboard's Ask.**
  - The answer call is recorded as kind `ask`, from provider tokens.
  - The query embedding is recorded as kind `ask_embed`.
  - The answer call asks the budget first. When the cap is reached it returns HTTP 402 with the passages it found, which need no paid answer call. The query embedding still runs; it costs about a millionth of a dollar.
- **`extract_entities.py`** asks before every batch, stops cleanly, and resumes on the next run.
- **`judge_sample.py`, `ab_source_quality.py` and `diag_hindi_ab.py`** ask once, after `--yes`.
- **`diag_hindi_ab.py`** logs the provider's token counts as kind `ab_test`. Before, it logged chars/4 estimates as kind `translation`, which also skewed the translation cost per passage.

**The estimates follow the meter:**

- `corpus_status.py` uses the same measured vision cost per page as `ocr_consensus.py`: the median of the last 300 metered pages at today's prices, about $0.0054 on 2026-10-04.
  - The `--max-usd` it proposes carries 15% headroom, so consensus does not refuse the command it was given.
  - The translation cost per passage is repriced, preferring provider-metered rows.
  - The header names the source of both figures.
- The `images.py` estimate follows `SA_IMAGE_SIZE`.
  - Google's page (read 2026-10-04) prices an image at 1K $0.067, 2K $0.101, 4K $0.151.
  - The provider reports about 400 more output tokens per image, measured at 1,482-1,551 at 1K and 2,080 at 2K. The ledger prices these at the image rate too.
  - So the estimate is 1K ~$0.091, 2K ~$0.125, 4K ~$0.175.
  - If Google bills those extra tokens at a lower text rate, the ledger reads high, which is the safe direction. Compare one day in Cloud Billing to settle it.

**Orphans:**

- `retire_doc.py`'s post-check counts the whole corpus. It now compares before and after the retirement, warns and exits 1 only when the count rises, and points earlier orphans to `diag_orphans.py`.
  - The manu retirement reported 157 orphaned entity mentions. That count was already in `STATUS_20261004_1304.md`, written before the retirement ran.
- `diag_orphans.py` is read-only and works on any database, including a backup. For every table keyed by `passage_id` it shows:
  - the orphaned id blocks;
  - the live document just below and just above each block;
  - whether any orphaned id is above the current maximum passage id (a reuse risk without AUTOINCREMENT);
  - sample rows and the entities named.
- `fix_orphans.py --apply` deletes only rows whose passage no longer exists. The cascade triggers (`--guard`, 6 installed) take dependent rows with any later passage delete.
"""

RUNBOOK = """

## Meters, gates, orphans (DOCS6_2026_10_04)

- **Orphans:**
  - `python scripts\\diag_orphans.py` shows where they are (read-only). Add `--db <backup>` to see whether they were already there.
  - `python scripts\\fix_orphans.py --apply` removes them. Run it while the dashboard is idle; it takes a backup first.
- **Spend before a run:**
  - `python scripts\\corpus_status.py --commands`: the vision $/page line says "measured" or "fallback".
  - `python scripts\\spend_audit.py --days 1`: Ask now appears as `ask` and `ask_embed`.
- **Cap reached:** Ask returns 402 with sources, and `extract_entities` stops at a batch boundary. Raise the cap with `python scripts\\set_budget.py --cap <usd> --unpause`.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs6_" + stamp))
        t = p.with_name(p.name + ".tmp_docs6"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
