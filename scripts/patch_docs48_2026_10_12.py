#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs48_2026_10_12.py  DOCS48_2026_10_12

Records MIRROR_CAP_2026_10_12 (after PATH, 408e11b): the mirror run that was to retire the withdrawn
Bodhicaryavatara and the two retired Dhanur Veda copies timed out on the vectors (now 25 to a call, and halved
on a timeout); --max-usd now stops a vision run before a page would pass it; the chart gives the median text's
price beside the corpus's; Hayashirsha's repair was in the live database already (the backup charted predated
it). docs/MIRROR_CAP_2026-10-12.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 51), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 38), each needing DOCS47_2026_10_12.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs48_<date>), line endings kept.

  python scripts/patch_docs48_2026_10_12.py --check
  python scripts/patch_docs48_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS48_2026_10_12"

PLATFORM = """

## 51. The mirror's retire; a cap that holds (DOCS48_2026_10_12)

**12 Oct, afternoon (IST), after the release of PATH (`408e11b`).** docs/MIRROR_CAP_2026-10-12.md has the
details.
- **The mirror run stopped twice** (13:57 and the scheduled 14:32): "corpus_retire: canceling statement due to
  statement timeout". The withdrawn Bodhicaryavatara and the two retired Dhanur Veda copies were retired in
  `corpus.docs`; their passages stayed live.
- **The cause:** the Bodhicaryavatara's 824 vectors were retired in one call, and each is a new entry in the
  HNSW index.
- **`--max-usd` only checked the estimate.** A run could spend past it.
- **Hayashirsha's repair was already in the live database** (98.5% vision); the backup the session charted
  predated it.

**MIRROR_CAP_2026_10_12:**
- vectors are retired 25 to a call, and a timed-out retire is sent again in halves (`corpus_retire` retires
  only live rows);
- a vision run stops before a page would take it past `--max-usd`, from what usage_log says it has spent;
- the chart and `/path` give the median text's price ($0.0024) beside the corpus's ($0.0100 after the
  Natyasastra's run).

**Tests:** `tests/test_mirror_cap_2026_10_12.py` (11).
"""

RUNBOOK = """

## When the mirror says "corpus_retire: ... statement timeout" (DOCS48_2026_10_12)

1. **Nothing is lost:** the call was rolled back whole, and the rows it was to retire are still live on the site.
2. **After MIRROR_CAP_2026_10_12:** vectors are retired 25 to a call, and a timed-out call is sent again in halves.
   Run the plan, then `--apply`: `python scripts\\corpus_sync.py`, then `python scripts\\corpus_sync.py --apply`.
3. **Check** in the SQL editor that the text's live passages are 0.

## --max-usd (DOCS48_2026_10_12)

- `repair_text.py --repair --max-usd X` refuses a run whose estimate is above X, and stops a run before a page
  would take it past X (what this run has spent, from usage_log). The spend cap (`set_budget.py`) still stops
  everything.
"""

EP = """

## Addendum 2026-10-12 (38) (DOCS48_2026_10_12)

| # | Item | State |
|---|---|---|
| P1 | The path of every text (text_path.py, /path) | **Released** (408e11b); `/path` after a dashboard restart |
| P3 | Withdraw a damaged text (reversible) | **Released**; the Bodhicaryavatara withdrawn on 12 Oct |
| M1 | The mirror's retire of vectors (25 to a call, halved on a timeout) | Built and tested (MIRROR_CAP_2026_10_12) |
| M2 | `--max-usd` stops a run before it passes | Built and tested (MIRROR_CAP_2026_10_12) |
| T2 | The marked passages translated again, then judged again | Next; paid, capped, dry run first |
| B2 | The spend | The user's decision |
| VC1 | Vision's artefacts cleaned before ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS47_2026_10_12"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS47_2026_10_12"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS47_2026_10_12")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs48_" + stamp))
        t = p.with_name(p.name + ".tmp_docs48"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
