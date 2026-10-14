#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs50_2026_10_14.py  DOCS50_2026_10_14

Records REDEEM_2026_10_14 and T2_2026_10_14 (after READ_IN, 13bcfbb): what of the translation already paid for is
kept, and what is not, text by text (scripts/redeem.py, read-only; the Library and /redeem show it); the passages
the judge marks translated again with the stronger engine and judged again (scripts/retranslate_marked.py, a dry
run by default). docs/REDEEM_2026-10-14.md has the ledger and the details.

Appends to docs/PLATFORM_2026-10-04.md (section 53), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 40), each needing DOCS49_2026_10_13.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs50_<date>), line endings kept.

  python scripts/patch_docs50_2026_10_14.py --check
  python scripts/patch_docs50_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS50_2026_10_14"

PLATFORM = """

## 53. What of the translation is redeemed (DOCS50_2026_10_14)

**14 Oct (IST), after the release of READ_IN (`13bcfbb`).** docs/REDEEM_2026-10-14.md has the ledger.
- **Asked:** what of the translation already paid for can be kept, and what cannot, clearly marked.
- **On the backup of 14 Oct:** 23,334 English verses in 47 texts; 19,172 kept (82%), 4,128 (18%) made from
  misread Sanskrit, 34 judged wrong.
- **The money:** $30.59 on the texts here, plus $1.03 on texts no longer here (repriced):
  - $7.66 on English that cannot be kept as it is;
  - $2.67 on English a better reading replaced (Karan Aagama, the Hayashirsha, six small Smritis);
  - making it all again costs about $3.56. What lasts is the clean reading.
- **Verdicts:** 5 redeemed, 8 mostly redeemed, 31 to translate again (after the repair), 2 not redeemable as they
  are (a source first), 8 replaced by a better reading, 1 withdrawn.

**REDEEM_2026_10_14:**
- `scripts/redeem.py` (read-only) classes each English verse: judged sound / judged wrong / vision / no debris
  seen / debris. It gives each text a verdict, with its money, and writes `data/redeem.json`;
- the dashboard shows it after a restart:
  - a line under each Library card (and under a "Not yet readable" card that was paid for);
  - the English kept, in the header;
  - `/redeem`, with Count again;
- the chart gives a text the judge marks `retranslate_marked.py` as its NEXT.

**T2_2026_10_14:** `scripts/retranslate_marked.py`:
- the passages the judge marks are translated again with gemini-2.5-pro, then judged again; the Hindi of a mended
  passage is made again;
- a dry run by default; `--yes` is capped by `--max-usd`, stops at the spend cap and while the dashboard writes
  the same text, and logs to `data/retranslate/`;
- on the backup: 18 passages, about $0.03.

**Tests:** `tests/test_redeem_2026_10_14.py` (21).
"""

RUNBOOK = """

## What is redeemed (DOCS50_2026_10_14)

1. `python scripts\\redeem.py --html exports\\redeem.html --csv exports\\redeem.csv`: free and read-only. It
   writes `data/redeem.json`, which the Library and `/redeem` show. Count again on `/redeem` does the same.
2. `python scripts\\redeem.py --doc Mallapurana`: one text, with the passages the judge marks.
3. Green is kept; amber is mostly kept, or replaced by a better reading (translate it); red is to translate
   again after the repair, or a source first.

## The passages the judge marks, translated again (T2) (DOCS50_2026_10_14)

1. `python scripts\\retranslate_marked.py`: the dry run (free). It shows what it would do, what it leaves out and
   why, and the price.
2. `python scripts\\retranslate_marked.py --yes --max-usd 0.10`: the run. It stops before the cap, at the spend
   cap, or while the dashboard writes the same text. The log is in `data/retranslate/`.
3. `python scripts\\judge_review.py`: what the judge says now. A passage still marked goes to a person.

## Does the reader return the reading's engine? (Srangam S2) (DOCS50_2026_10_14)

In the Lovable SQL editor, read-only:

    SELECT p.proname, position('ocr_engine' in pg_get_functiondef(p.oid)) > 0 AS returns_engine
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname IN ('corpus_reader_page', 'corpus_reader_outline') AND p.prokind = 'f'
    ORDER BY p.proname;
"""

EP = """

## Addendum 2026-10-14 (40) (DOCS50_2026_10_14)

| # | Item | State |
|---|---|---|
| R4 | A scan that is read goes in, in place | **Released** (13bcfbb) |
| RD1 | What of the translation is redeemed, text by text (the ledger, the Library, /redeem) | Built and tested (REDEEM_2026_10_14) |
| T2 | The marked passages translated again, then judged again | Built and tested (T2_2026_10_14); 18 passages, about $0.03 |
| D1 | The re-ingests (Tantric Texts, Karan, the Natyasastra, 12 texts, 6 Tesseract texts) | Free; waiting for the jobs |
| D2 | Karan and the Hayashirsha translated, then released | About $1.61 for the English |
| S1 | Srangam: a mark on a verse made from a misread page | Next; no database change |
| S2 | Srangam: the reading's engine on each verse | Next; the RUNBOOK's SQL check first |
| S3 | Srangam: each text's verdict on its card | Designed after S1 and S2 |
| VC1 | Vision's artefacts cleaned before ingest | Next |
| C14 | Sources wanted on the site | Designed; not started |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS49_2026_10_13"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS49_2026_10_13"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS49_2026_10_13")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs50_" + stamp))
        t = p.with_name(p.name + ".tmp_docs50"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
