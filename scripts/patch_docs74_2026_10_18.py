#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs74_2026_10_18.py  DOCS74_2026_10_18

Records 18 Oct (afternoon): the Devimahatmya's scholarly English made; T2 on the Mallapurana; the Surya Siddhanta's
e-text in; the state of all repos and how they join consolidated in docs/STATE_2026-10-18.md; ETEXT_PAGE_2026_10_18.

Appends to docs/PLATFORM_2026-10-04.md (section 77), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md (addendum 64),
each needing DOCS73_2026_10_18. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs74_<date>), line
endings kept.

  python scripts/patch_docs74_2026_10_18.py --check
  python scripts/patch_docs74_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS74_2026_10_18"

PLATFORM = """

## 77. The Devimahatmya made; the state of every repo in one page (DOCS74_2026_10_18)

**18 Oct (afternoon).** docs/STATE_2026-10-18.md: where everything is, how the repos join, what remains.
- **The Devimahatmya** (`markandeya_purana__w_gretil`, from MarkP_81.1, pages 627 to 780): a canary of 20 ($0.58),
  then 649 (612 passed, 37 flagged, $19.05): 669 passages, 632 passed, $19.63. Its exports of 05:10 UTC predate the
  run's end: made again by the RUNBOOK.
- **T2 on the Mallapurana:** 58 marked; 52 mended, 5 not mended, 1 failed (its log ends 10:05 UTC). The site's export,
  made while it ran, shows Mallapurana 986 by flash and 6 by gemini-2.5-pro, AphorismsOfSandilya 454 and 2,
  markandeya_purana 1,252, 3 by Sonnet and 3 by gemini-2.5-pro: the Mallapurana wants a mirror run.
- **The Surya Siddhanta's e-text in:** `jyotish_surya_siddhanta__w_etext`, 515 verses on 28 pages (engine
  `etext:etext`), reading 52 of the scan's 54 readable pages in order; local only.
- **ETEXT_PAGE_2026_10_18** (etext_witness.py): the ALSO line names a real page, not "--page N" (run as it stood).

**Tests:** `tests/test_etext_page_2026_10_18.py` (7); test_quality_2026_10_11's replay chain follows `.bak_etextpage_`.
"""

RUNBOOK = """

## The day's order: the Devimahatmya's editions, the mirror, the Ganita, the Surya (DOCS74_2026_10_18)

docs/STATE_2026-10-18.md, section 6. One Gemini job at a time.
1. **The Devimahatmya:** the editions and the prose again (DOCS73 above, step 3, free); its 37 flagged verses on the
   desk (Triage); the re-judge (DOCS73 above, step 2: the dry run, then its NEXT).
2. **The mirror:** `python scripts\\corpus_sync.py --doc Mallapurana` (the plan, free), then the same with `--apply`.
3. **The Sandilya:** `python scripts\\retranslate_marked.py --doc AphorismsOfSandilya --engine anthropic:claude-sonnet-5-5
   --judge-engine anthropic:claude-haiku-5-5` (the dry run), its NEXT; then `python scripts\\corpus_sync.py --doc
   AphorismsOfSandilya` and `--apply`.
4. **The Ganita Yukti Bhasa:** `python scripts\\reingest_pages.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (the
   plan, free), its NEXT (`--apply --replace`, as the plan counts); then on its desk page "The working English by Sonnet
   in one pass", the rest (Plan, free; then Run); then the screen (DOCS72 above, step 2, `--doc
   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`) and T2 (step 3).
5. **The Surya Siddhanta:** `python scripts\\scholar_translate.py --doc jyotish_surya_siddhanta__w_etext --pages 1-28
   --limit 20 --engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5 --audit-every 10
   --no-compare` (the plan, free: its first verse is the text's first), then `--yes --max-usd 1.50`; then the same with
   `--limit 600` and `--yes --max-usd 16.00`.
"""

EP = """

## Addendum 2026-10-18 (64) (DOCS74_2026_10_18)

| # | Item | State |
|---|---|---|
| E3 | The Devimahatmya, scholarly | Made: 669 passages, 632 passed, 37 flagged ($19.63); editions again; the 37 read |
| E3b | Adhyayas 19 to 31 (740) | The re-judge of the 482 next (about $1.30, Google) |
| T2m | The Mallapurana | 52 of 58 mended; a mirror run |
| T2s | The Sandilya | 30 marked; T2 next |
| G1 | The Ganita Yukti Bhasa | The re-ingest, Tier R, the screen; its scholarly English (about $72) yours to decide |
| S1 | The Surya Siddhanta | The e-text in (515); its scholarly English next (about $14) |
| D74 | The state of all repos | docs/STATE_2026-10-18.md |
| X1 | The scholarly English on the site | To build (a docs/cloud SQL file, a corpus_sync step, a reader patch) |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS73_2026_10_18"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS73_2026_10_18"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS73_2026_10_18")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs74_" + stamp))
        t = p.with_name(p.name + ".tmp_docs74"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
