#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs72_2026_10_17.py  DOCS72_2026_10_17

Records 17 Oct (late): the English already paid for, what was measured and how it is redeemed (JUDGE_SCREEN_2026_10_17,
docs/JUDGE_SCREEN_2026-10-17.md); the test made independent of the real BM2 and BM3 (TEST_ISOLATION_2026_10_17); the
GRETIL download by PowerShell (Python's certificate check fails on this PC).

Appends to docs/PLATFORM_2026-10-04.md (section 75), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md (addendum 62),
each needing DOCS71_2026_10_17, and to docs/SOP_TRANSLATION_2026-10-17.md (an addendum), needing DOCS70_2026_10_17.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs72_<date>), line endings kept.

  python scripts/patch_docs72_2026_10_17.py --check
  python scripts/patch_docs72_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS72_2026_10_17"

PLATFORM = """

## 75. The English already paid for: measured, then redeemed (DOCS72_2026_10_17)

**17 Oct (IST, late).** Asked: has the flash corpus been properly analysed and redeemed? docs/JUDGE_SCREEN_2026-10-17.md.
- **Measured on all of it: the reading** (REDEEM: 22,371 of 26,589 English, 84%, from a clean reading). **The meaning:
  on 0.9%** (240 verdicts of the flash judge; in five texts on the site 11 wrong of 188, 18 of the ledger's 26 wrong
  blamed on the Sanskrit). Redeemed once: T2, 18 passages, 7 mended. The reader of BM2 marked no flash English wrong.
- **Costs as billed:** the flash judge $0.00274 a verdict (every kept verse: about $60 on the cap); Haiku's judge-v1
  $0.000247 (the seven texts on the site: about $4.30 on the credit).
- **The way:** keep; the judge of the other family (Claude reads Gemini's English, Gemini reads Claude's); calibrate
  Haiku on flash's 240 (Opus the referee) by a rule set before the run; screen every clean verse once; fix what is
  marked by its cause (Sonnet for the translation, the source path for the Sanskrit); a person on what is not mended;
  a whole text again only by measure.
- **JUDGE_SCREEN_2026_10_17** (judge_sample.py, retranslate_marked.py): Claude's judge-v1, --skip-judged, --clean-only,
  --only-ids, --max-usd, --calibrate (files, nothing in mt_reviews; a referee's sides); retranslate_marked with
  Claude's engines, priced, stopped by the credit, its NEXT carrying its options.
- **TEST_ISOLATION_2026_10_17:** test_bench_desk_2026_10_16 no longer reads the real BM2 and BM3, and lets the ledger
  close before its temp folder goes (Windows).
- **GRETIL from this PC:** Python's urllib fails the certificate check ("unable to get local issuer certificate");
  PowerShell's Invoke-WebRequest (the Windows certificate store) downloads the file, and `etext_witness.py --file ...
  --slug gretil` reads it (engine etext:gretil, as --url would name it).

**Tests:** `tests/test_judge_screen_2026_10_17.py` (13).
"""

RUNBOOK = """

## The flash corpus redeemed; GRETIL by PowerShell (DOCS72_2026_10_17)

1. **The calibration (free dry run; then about $0.06 on the credit):**
   `python scripts\\judge_sample.py --all --calibrate --engine anthropic:claude-haiku-5-5`, then the same with
   `--yes --max-usd 0.20`. The referee on where they disagree:
   `python scripts\\judge_sample.py --all --calibrate --engine anthropic:claude-opus-5-5 --only-ids data\\retranslate\\judge_screen\\calibrate_claude-haiku-5-5_disagree.jsonl`,
   then with `--yes --max-usd 2.00`. The rule (docs/JUDGE_SCREEN_2026-10-17.md, section 4) decides.
2. **The screen, a text at a time:** `python scripts\\judge_sample.py --doc markandeya_purana --sample-pct 100 --limit 2000
   --skip-judged --clean-only --engine anthropic:claude-haiku-5-5` (dry run), then with `--yes --max-usd 0.50`. The
   others likewise (MBh01, the Natyasastra, the Tantric Texts, the Shatapatha, the Mallapurana, Sandilya).
3. **The fix:** `python scripts\\retranslate_marked.py --doc markandeya_purana --engine anthropic:claude-sonnet-5-5
   --judge-engine anthropic:claude-haiku-5-5` (dry run); its NEXT. Then `python scripts\\judge_review.py --doc
   markandeya_purana`, `python scripts\\redeem.py`, `python scripts\\text_path.py`, the mirror's plan and --apply.
4. **GRETIL (the Markandeya Purana, 1 to 93):** in PowerShell, from the repo root:
   `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12`, then
   `Invoke-WebRequest -Uri https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_mArkaNDeyapurANa1-93.htm -OutFile sources\\markandeya_purana\\sa_mArkaNDeyapurANa1-93.htm -UseBasicParsing`;
   then `python scripts\\etext_witness.py --doc markandeya_purana --file sources\\markandeya_purana\\sa_mArkaNDeyapurANa1-93.htm --slug gretil`
   (the preview, free), the same with `--write`, then `python scripts\\etext_witness.py --doc markandeya_purana --ingest`.
"""

EP = """

## Addendum 2026-10-17 (62) (DOCS72_2026_10_17)

| # | Item | State |
|---|---|---|
| Q1 | The flash corpus: the meaning measured on every clean verse (JUDGE_SCREEN_2026_10_17) | Built and tested; the calibration first (about $0.06) |
| Q2 | The screen of the seven texts on the site | About $4.30 on the credit, if Haiku passes the calibration |
| Q3 | The marked verses fixed by cause (Sonnet; the source path) | About $3 by Sonnet at the sample's rate; the Hindi after |
| T4 | test_bench_desk independent of the real BM2 and BM3 (TEST_ISOLATION_2026_10_17) | Built; to run on the PC |
"""

SOP = """

## Addendum (17 Oct, late): the English already made (DOCS72_2026_10_17)

docs/JUDGE_SCREEN_2026-10-17.md. Tier R is for English not yet made, or a text measured to need it; English already
made is kept, read by a judge of the other family, and fixed where it is marked, by its cause. "Every verse again" is
for a text whose screen marks a fifth or more of its verses (your threshold to set), or whose Sanskrit changed.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS71_2026_10_17"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS71_2026_10_17"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS71_2026_10_17"),
           (Path("docs/SOP_TRANSLATION_2026-10-17.md"), SOP, "DOCS70_2026_10_17")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs72_" + stamp))
        t = p.with_name(p.name + ".tmp_docs72"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
