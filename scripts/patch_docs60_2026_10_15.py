#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs60_2026_10_15.py  DOCS60_2026_10_15

Records 15 Oct, evening: the Claude credit first, Gemini after it (CLAUDE_FIRST_2026_10_15: Claude checks for a
Claude run; the engine anthropic: for the working English and the Hindi), and where Gemini goes by the ledger.
docs/CLAUDE_FIRST_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 63), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 50), each needing DOCS59_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs60_<date>), line endings kept.

  python scripts/patch_docs60_2026_10_15.py --check
  python scripts/patch_docs60_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS60_2026_10_15"

PLATFORM = """

## 63. The Claude credit first, Gemini after it (DOCS60_2026_10_15)

**15 Oct (IST), evening.** docs/CLAUDE_FIRST_2026-10-15.md has the details.
- **The decision (Dhruv):** the free Claude credit ($190 of it, to 11 Nov) pays for the translation work; Gemini after
  it. The Claude runs were still using Gemini for their checks, and Google's spend cap ($45, reached at 16:56)
  stopped the Karanagama's canary.
- **The ledger (usage_log) reads low:** Gemini recorded $5.24 in September and $29.94 in 1-15 October. Before 15 Oct
  the thinking was not counted (COST_TRUTH), and most rows were priced from characters. The bill (AI Studio) is the
  truth; spend_audit.py --days 30 is the ledger side. October by kind: the working English $13.45, OCR $6.41,
  pictures $5.55, entities $1.77, the scholarly checks about $1.5.
- **CLAUDE_FIRST_2026_10_15:**
  - scholar_translate.py: a Claude run's checks may be another Claude model's (--judge-engine, --compare-engine
    anthropic:...), never the translator's own; a run with no Gemini engine is gated by the credit only;
  - infer_mt.py: the engine anthropic: for the working English and the Hindi, on the credit (never budget_state),
    failing closed; MT_ENGINE stays Gemini's.
- **Independence:** the Gemini checks caught the Karanagama's 28.4, which Claude's critic had accepted. Kept by
  choice: the flash judge now (about Rs 80 for both texts), or a Gemini re-judge after the credit (CF2).

**Tests:**
- `tests/test_claude_first_2026_10_15.py` (13);
- test_claude_engine_2026_10_15, test_cost_truth_2026_10_15 and test_run_fix_2026_10_15 follow.
"""

RUNBOOK = """

## The Claude credit first (DOCS60_2026_10_15)

- **A scholarly run, no Gemini:** `--engine anthropic:claude-sonnet-5-5 --judge-engine anthropic:claude-haiku-5-5
  --compare-engine anthropic:claude-opus-5-5`. The dry run says "no Gemini call: Google's spend cap is not
  consulted". With the flash judge kept (the default --judge-engine), Google's cap still gates the run.
- **The working English on Claude, one text at a time:** only after the benchmark (`benchmark_mbh01.py --engines
  gemini:gemini-2.5-flash anthropic:claude-haiku-5-5 anthropic:claude-sonnet-5-5@low`). Then the dashboard's
  `/api/pipeline/translate-doc` with `"engine": "anthropic:claude-haiku-5-5"`. Never set MT_ENGINE to an anthropic:
  engine: Ask and extract_entities call Gemini with it.
- **When the credit is spent or expires,** the job stops ("the Claude credit is spent or expired"). Run it again with
  the default engine.
- **Watch:** `claude_engine.py --credit`; `spend_audit.py --days 30` against AI Studio's Spend page.
"""

EP = """

## Addendum 2026-10-15 (50) (DOCS60_2026_10_15)

| # | Item | State |
|---|---|---|
| CF1 | Claude checks for a Claude run; the engine anthropic: in infer_mt (CLAUDE_FIRST_2026_10_15) | Built and tested |
| CF2 | A Gemini flash re-judge of the rows the Claude checks passed, after the credit | To build (about $0.0004 a verse) |
| CF3 | The working English on Claude: the benchmark on three texts of the backlog (137,755 passages) | To run; a person reads it |
| CF4 | Entities and stories on Claude | Possible; not built |
| SP1 | The ledger against the bill: spend_audit.py --days 30 against AI Studio's Spend page, weekly | Standing |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS59_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS59_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS59_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs60_" + stamp))
        t = p.with_name(p.name + ".tmp_docs60"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
