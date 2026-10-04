#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs4_2026_10_04.py  DOCS4_2026_10_04

Appends to RUNBOOK.md a short section that points at docs/PLATFORM_2026-10-04.md and the
new read-only status page. Marker-idempotent, backup first, atomic replace.

  python scripts/patch_docs4_2026_10_04.py --check
  python scripts/patch_docs4_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS4_2026_10_04"
TEXT = """

## Status page, image queue, context engine (DOCS4_2026_10_04)

- One read-only page with everything in one place:
  `python scripts/status_report.py`, which writes `exports/status/STATUS_latest.md`.
  It covers code HEAD, prompts, corpus verdicts and spend, semantic index (stale and orphaned vectors, guard triggers), images, 7-day spend, maintenance ticks, backups and the Srangam panel's age.
- Image jobs run one at a time, in the order asked, and are listed with progress on the Images page (IMAGES_QUEUE_2026_10_04). This needs one dashboard restart while idle.
- The SanskritMaintenance task (every 3 h, idle only) keeps embeddings current. Since BRAIN_FRESH_2026_10_04 it also re-embeds passages re-translated after their vector. `python scripts/build_embeddings.py --plan` shows the counts and makes no call.
- Findings, corrections and the UI path (U1 to U4): `docs/PLATFORM_2026-10-04.md`.
"""
P = Path("RUNBOOK.md")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not P.exists():
        print("FAIL: RUNBOOK.md not found. Run from the repo root."); return 2
    raw = P.read_bytes()
    if MARK.encode() in raw:
        print("Already patched (%s)." % MARK); return 0
    if args.check:
        print("CHECK OK: 1 file to append. Nothing written."); return 0
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    shutil.copy2(P, P.with_name(P.name + ".bak_docs4_" + datetime.date.today().strftime("%Y%m%d")))
    t = P.with_name(P.name + ".tmp_docs4"); t.write_bytes(raw + TEXT.replace("\n", nl).encode("utf-8")); os.replace(t, P)
    print("appended RUNBOOK.md"); return 0


if __name__ == "__main__":
    sys.exit(main())
