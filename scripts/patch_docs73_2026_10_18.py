#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs73_2026_10_18.py  DOCS73_2026_10_18

Records 18 Oct (morning): the night of 17 Oct read (docs/SCHOLAR_REF_2026-10-18.md): the screen calibrated (Haiku is the
screen by the rule set before), the scholarly run's start missed (adhyayas 19 to 31, not the Devimahatmya), the judge's
quota; SCHOLAR_REF_2026_10_18.

Appends to docs/PLATFORM_2026-10-04.md (section 76), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md (addendum 63),
each needing DOCS72_2026_10_17. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs73_<date>), line
endings kept.

  python scripts/patch_docs73_2026_10_18.py --check
  python scripts/patch_docs73_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS73_2026_10_18"

PLATFORM = """

## 76. The screen calibrated; the Devimahatmya's start missed; the judge's quota (DOCS73_2026_10_18)

**18 Oct (IST, morning).** docs/SCHOLAR_REF_2026-10-18.md.
- **The calibration:** Haiku beside flash on 229 passages: both 13, flash only 12, Haiku only 12; Haiku finds 52% of
  flash's marks and is the stricter (3.77 against 4.42). Opus on the disagreements: with Haiku 16, with flash 7 (it
  confirmed none of flash's lone marks, 5 of 12 of Haiku's). **Haiku is the screen**, by the rule set before the run.
- **T2 on the Markandeya:** 27.8 and 82.8 by Sonnet, judged again by Haiku, mended; verse 4.8 on the site by Sonnet.
- **The GRETIL Markandeya in** (5,240 passages, 780 pages, local only): the Devimahatmya is pages 626 to 780 (588
  numbered verses, 89 unnumbered).
- **The scholarly run began at page 81** (a heading whose page.idx is "81.1"), not MarkP_81.1: 740 verses of adhyayas
  19 to 31, $20.63, kept; 482 of them unjudged ("ResourceExhausted", Google's quota, from 23:34 IST).
- **SCHOLAR_REF_2026_10_18** (scholar_translate.py): --from-ref matches a verse's own reference first; --rejudge reads
  again the verses whose judge did not answer.

**Tests:** `tests/test_scholar_ref_2026_10_18.py` (5); test_ornament_2026_10_16 follows `.bak_scholarref_`.
"""

RUNBOOK = """

## The Devimahatmya, its re-judge and editions (DOCS73_2026_10_18)

1. **The run:** `python scripts\\scholar_translate.py --doc markandeya_purana__w_gretil --from-ref 81.1 --pages 627-780
   --limit 20 --engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5 --audit-every 10
   --no-compare` (the plan: its first verse must be MarkP_81.1, savarnih suryatanayo), then `--yes --max-usd 1.50`; then
   the same with `--limit 700` and `--yes --max-usd 24.00`. No vision repair beside it.
2. **The re-judge** of the verses no judge answered: `python scripts\\scholar_translate.py --doc
   markandeya_purana__w_gretil --engine anthropic:claude-sonnet-5-5 --rejudge --limit 900` (the dry run), then its NEXT.
3. **The editions:** `python scripts\\export_html.py --db data\\context.db --doc markandeya_purana__w_gretil --scholar
   --sanskrit --side-by-side --from 626 --to 780` (the Devimahatmya) and `--from 81 --to 124` (adhyayas 19 to 31); the
   prose: `python scripts\\scholar_translate.py --doc markandeya_purana__w_gretil --report`.
"""

EP = """

## Addendum 2026-10-18 (63) (DOCS73_2026_10_18)

| # | Item | State |
|---|---|---|
| Q1 | The screen's calibration | Done: Haiku is the screen (Opus with Haiku 16, flash 7) |
| E3 | The Devimahatmya, scholarly | The first run began at adhyaya 19 (SCHOLAR_REF_2026_10_18 mends it); again, about $19 |
| E3b | Adhyayas 19 to 31, scholarly (740 verses) | Made; 482 to judge again (--rejudge) |
| G1 | The Ganita Yukti Bhasa | Vision read 109 pages; the re-ingest of 108 (--replace 138) next |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS72_2026_10_17"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS72_2026_10_17"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS72_2026_10_17")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs73_" + stamp))
        t = p.with_name(p.name + ".tmp_docs73"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
