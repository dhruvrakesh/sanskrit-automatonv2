#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs49_2026_10_13.py  DOCS49_2026_10_13

Records READ_IN_2026_10_13 (after MIRROR_CAP, e51422b): the mirror healed (the withdrawn and retired texts are off
the site); a scan vision has read (80% of its pages, 95% merged) goes in now, in place; the pages vision failed on
twice are not pages to read; the drift check gives the in-place re-ingest first; where every part of the work
stands. docs/READ_IN_2026-10-13.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 52), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 39), each needing DOCS48_2026_10_12.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs49_<date>), line endings kept.

  python scripts/patch_docs49_2026_10_13.py --check
  python scripts/patch_docs49_2026_10_13.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS49_2026_10_13"

PLATFORM = """

## 52. A scan that is read goes in (DOCS49_2026_10_13)

**13 Oct (IST), after the release of MIRROR_CAP (`e51422b`).** docs/READ_IN_2026-10-13.md has the details.
- **The mirror healed:** the timed-out retire was sent again in halves; 383 groups equal, 0 different. The
  Bodhicaryavatara and the two Dhanur Veda copies are off the site; 62 texts, 90,655 live passages, 23,593 English.
- **The Natyasastra's vision read 513 of 546 pages** ($0.0070 a page). Every tool still said "repair the scan":
  - the merge leaves out blank pages, so it is never "complete";
  - the pages vision failed on twice were counted as pages to read.
- **No re-ingest was applied yet:** translation jobs were running, and a re-ingest waits for them.

**READ_IN_2026_10_13:**
- a scan vision has read (80% of its pages, 95% merged) goes in now, in place (`reingest_pages.py`), and the pages
  vision may still read come after;
- the pages left to Tesseract are not priced as pages to read; a scan whose every remaining page failed twice is
  "find a source";
- the drift check gives the in-place re-ingest before the whole text again.

**Tests:** `tests/test_read_in_2026_10_13.py` (9).
"""

RUNBOOK = """

## Before a re-ingest: is anything writing? (DOCS49_2026_10_13)

1. `(Invoke-RestMethod http://127.0.0.1:5057/api/jobs/running).running | Select-Object kind, doc, state`
2. **Only OCR jobs (or none):** a re-ingest may run. A translation, classify or ingest job running or queued: it is
   refused; wait for the job to finish.
3. **Then:** a backup, the plan, the `--apply` line the plan prints, and the mirror.

## Does the site leave retired rows out? (DOCS49_2026_10_13)

In the Lovable SQL editor, read-only: every `corpus_reader_*` function's definition should mention `retired_at`:

    SELECT p.proname, position('retired_at' in pg_get_functiondef(p.oid)) > 0 AS filters_retired
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname LIKE 'corpus\\_reader\\_%' AND p.prokind = 'f'
    ORDER BY p.proname;
"""

EP = """

## Addendum 2026-10-13 (39) (DOCS49_2026_10_13)

| # | Item | State |
|---|---|---|
| M1 | The mirror's retire of vectors and passages (halved on a timeout) | **Released** (e51422b); healed on 12 Oct |
| M2 | `--max-usd` stops a run before it passes | **Released** (e51422b) |
| R4 | A scan that is read goes in, in place | Built and tested (READ_IN_2026_10_13) |
| D1 | The re-ingests (Tantric Texts, Karan, the Natyasastra, 12 texts, 6 Tesseract texts) | Free; waiting for the translation jobs |
| T2 | The marked passages translated again, then judged again | Next; paid, capped, dry run first |
| VC1 | Vision's artefacts cleaned before ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS48_2026_10_12"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS48_2026_10_12"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS48_2026_10_12")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs49_" + stamp))
        t = p.with_name(p.name + ".tmp_docs49"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
