#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_runbook_consensus.py  (2026-09-30)  RUNBOOK_CONSENSUS_2026_09_30
Docs only. Appends RUNBOOK section 3j: the one-command OCR consensus, the
lacuna census, and the Hindi reference A/B. Marker-idempotent, backup, atomic.
  python scripts/patch_runbook_consensus.py [--check]
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "RUNBOOK_CONSENSUS_2026_09_30"
RB = Path("RUNBOOK.md")
ANCHOR = "## 3i. Export editions"

SECTION = """

## 3j. OCR consensus in one command (RUNBOOK_CONSENSUS_2026_09_30)

Sections 3b, 3e and 3f describe the agreed standard. Tesseract runs on every page. Triage uses Tesseract confidence. Vision runs only on the pages that fail triage. The two readings are then merged, with vision as the source of record and Tesseract kept as the apparatus and the fallback. Until 2026-09-30 that chain was five manual steps. Nothing ran it, so most books were translated from raw Tesseract. See docs/OCR_CONSENSUS_2026-09-30.md.

```powershell
python scripts\\ocr_consensus.py --doc <DOC>          # PLAN: triage + cost estimate + dry-run audit/merge. No spend.
python scripts\\ocr_consensus.py --doc <DOC> --yes    # vision (metered, --max-usd 1.00 cap) -> repair -> merge --apply -> drift
python scripts\\ocr_consensus.py --doc <DOC> --drift-only
```

- **Idempotent.** Every step skips work that is already done. The script never writes the database.
- **Drift report.** It lists every consensus page on disk as current, stale or missing-in-db, compared with the DB text. Exit code 3 means the DB is behind; the script then prints the exact re-ingest commands (backup, wipe, ingest from `data\\raw_merged`, classify, translate en, QA, translate hi). Run those only while the dashboard reads "idle".
- **Re-translation after re-ingest is cheap.** The cache key is prompt version + source text. Pages whose text did not change are answered from the cache at no cost; only changed passages call the API.

**Lacuna census** (read-only, unicode-safe). It replaces SQL typed into PowerShell 5, which turns Devanagari into `?`:

```powershell
python scripts\\measure_lacunae.py
python scripts\\measure_lacunae.py --doc <DOC> --csv exports\\lacunae_<DOC>.csv
```

**Hindi with or without the English reference.** Measure it before changing anything:

```powershell
python scripts\\diag_hindi_ab.py --doc <DOC> --n 40          # dry run + cost
python scripts\\diag_hindi_ab.py --doc <DOC> --n 40 --yes    # writes data\\ab\\hindi_ref_<DOC>_<stamp>.html
```
"""


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not RB.exists():
        print("FAIL: RUNBOOK.md not found. Run from the repo root."); return 2
    raw = RB.read_bytes(); crlf = raw.count(b"\r\n")
    nl = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if src.count(ANCHOR) != 1:
        print("REFUSING TO WRITE: '%s' matched %d times, expected 1." % (ANCHOR, src.count(ANCHOR))); return 1
    src = src.rstrip("\n") + SECTION
    if args.check:
        print("CHECK OK. Nothing written."); return 0
    bak = RB.with_name(RB.name + ".bak_consensus_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(RB, bak)
    tmp = RB.with_name(RB.name + ".tmp_consensus")
    tmp.write_bytes(src.replace("\n", nl).encode("utf-8"))
    os.replace(tmp, RB)
    print("PATCHED RUNBOOK.md (backup %s)." % bak); return 0


if __name__ == "__main__":
    sys.exit(main())
