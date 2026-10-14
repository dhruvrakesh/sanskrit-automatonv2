#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs51_2026_10_14.py  DOCS51_2026_10_14

Records the afternoon of 14 Oct (after REDEEM, 5cf03b0): the re-ingests that went in; the Tantric Texts' refusal
(--replace 6); the mirror's held retire of seven re-ingested texts; the dashboard found stopped (the Yoga
Vasistha's OCR with it); REDEEM_FIX_2026_10_14 (redeem.py --doc); PROVISIONAL_EN_2026_10_14 (the Srangam reader
marks English made from a misread reading); C15_READER_GUARD_2026_10_14 (the reader's meaning search leaves
retired passages out). docs/PROVISIONAL_2026-10-14.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 54), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 41), each needing DOCS50_2026_10_14.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs51_<date>), line endings kept.

  python scripts/patch_docs51_2026_10_14.py --check
  python scripts/patch_docs51_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS51_2026_10_14"

PLATFORM = """

## 54. What is redeemed, marked on the site too (DOCS51_2026_10_14)

**14 Oct (IST), after the release of REDEEM (`5cf03b0`).** docs/PROVISIONAL_2026-10-14.md has the details.
- **Went in, in place:** Karan Aagama (7 pages), the Natyasastra, the 12 texts to use the repair, the
  Upapuranas' pages not yet in. The Tantric Texts were refused: 6 English and 6 Hindi go (`--replace 6`).
- **The mirror** sent 4,810 passages and held the retire of every mention and vector of seven re-ingested texts,
  for a person to confirm (`--allow-mass-retire`, those texts named).
- **The dashboard was found stopped.** The Yoga Vasistha's OCR stopped with it, at 1,542 of 1,982 pages.
- **The ledger:** 23,264 English in 40 texts, 82% kept, 17% made from misread Sanskrit; $30.59 spent here. Of
  it, $7.39 is on English that cannot be kept as it is and $2.95 on English a better reading replaced.
- **REDEEM_FIX_2026_10_14:** `redeem.py --doc` no longer calls every other text's spend gone.
- **PROVISIONAL_EN_2026_10_14 (Srangam):** a passage whose English was made from a misread reading is marked
  "provisional English". It uses the automaton's own test, so the site and the ledger agree.
- **C15_READER_GUARD_2026_10_14 (Lovable SQL):** `corpus_reader_match` and `corpus_reader_similar` leave retired
  passages out, even while the mirror holds their vectors.

**Tests:**
- `tests/test_provisional_2026_10_14.py` (7);
- Srangam `src/__tests__/reader-provisional.test.tsx` (4);
- C15 on PostgreSQL 16 with C5's functions.
"""

RUNBOOK = """

## The mirror held a retire (DOCS51_2026_10_14)

`corpus_sync.py` holds a retire of most or all of a text's rows ("HELD: ... use --allow-mass-retire if that is
right"). After a re-ingest, that is right: the old passages' mentions and vectors go.

1. Name only the texts the HELD lines name, and plan first:

       python scripts\\corpus_sync.py --doc smriti_04daksha_smriti --allow-mass-retire

2. Then the same with `--apply`. Never `--allow-mass-retire` without `--doc`.

## English made from a misread reading, on the site (DOCS51_2026_10_14)

The reader marks such a passage "provisional English". The rule is `redeem.py`'s: eight or more Devanagari signs
and a Latin word among them. A change to one is a change to the other, with the tests of both:
- `tests/test_provisional_2026_10_14.py`;
- Srangam `src/__tests__/reader-provisional.test.tsx`.

## Before a re-ingest's --replace (DOCS51_2026_10_14)

The number after `--replace` is the plan's, not the chart's: translations made since the chart change it. Run
the plan, and use the `--apply` line it prints.
"""

EP = """

## Addendum 2026-10-14 (41) (DOCS51_2026_10_14)

| # | Item | State |
|---|---|---|
| RD1 | What of the translation is redeemed (the ledger, the Library, /redeem) | **Released** (5cf03b0); REDEEM_FIX built and tested |
| T2 | The marked passages translated again, then judged again | **Released** (5cf03b0); not run yet (18 passages, about $0.03) |
| D1 | The re-ingests | Karan, the Natyasastra, 12 texts, 4 Upapuranas in; the Tantric Texts wait for `--replace 6` |
| M3 | The mirror's held retire of seven re-ingested texts | `--allow-mass-retire` with those texts named |
| S1 | Srangam: "provisional English" on English made from a misread reading | Built and tested (PROVISIONAL_EN_2026_10_14) |
| C15 | The reader's meaning search leaves retired passages out | Built and tested (Lovable SQL, one paste) |
| S2 | Srangam: the reading's engine on each verse | Next; a new read-only reader function (corpus_reader_page does not return it) |
| S3 | Srangam: each text's verdict on its card | After S2 |
| D2 | Translate what the repairs gave; then release Karan and the Hayashirsha | About $7.73 |
| O1 | The Yoga Vasistha's OCR, stopped with the dashboard (1,542 of 1,982 pages) | Free; start it again |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS50_2026_10_14"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS50_2026_10_14"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS50_2026_10_14")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs51_" + stamp))
        t = p.with_name(p.name + ".tmp_docs51"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
