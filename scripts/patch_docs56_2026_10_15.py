#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs56_2026_10_15.py  DOCS56_2026_10_15

Records 15 Oct, afternoon: the $200 Claude API credit put to the scholarly English (CLAUDE_ENGINE_2026_10_15): Claude as
an engine beside gemini-2.5-pro, metered as Anthropic bills it and capped by the credit, judged by Gemini; the Agamas and
Tantras read as such (a rule more, the edition's apparatus, the Karanagama's Hindi left out); the engines read side by
side and blind (scholar_duel.py); the pilot on the Hayasirsa Pancaratra and the Karanagama.
docs/CLAUDE_ENGINE_2026-10-15.md has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 59), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 46), each needing DOCS55_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs56_<date>), line endings kept.

  python scripts/patch_docs56_2026_10_15.py --check
  python scripts/patch_docs56_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS56_2026_10_15"

PLATFORM = """

## 59. Claude as an engine of the scholarly English; the Agamas and Tantras first (DOCS56_2026_10_15)

**15 Oct (IST), afternoon.** docs/CLAUDE_ENGINE_2026-10-15.md has the details.
- **The credit:** $200 of Claude API credit with the Max plan, to 11 Nov 2026 (the API only). The code was written by
  Claude, one of the contestants: the choice of engine is made blind, by a judge of each family and by a person.
- **CLAUDE_ENGINE_2026_10_15:**
  - scripts/claude_engine.py (new): one streamed call, no sampling parameters, the effort in output_config
    (anthropic:claude-sonnet-5-5@medium); the price from the reported usage (cache, batch, thinking as output); a row in
    usage_log and usage_totals, not in budget_state; the credit's own cap ($190 of the $200, nothing after 11 Nov,
    failing closed); --credit, --probe;
  - scholar_translate.py: --engine anthropic:...; the judge stays judge-v1 and the second judge gemini-2.5-pro, never
    Claude; one place for the system prompts; the Agamas and Tantras: rule 13 (agama-1: mantras in IAST, footnote
    digits left out) and the edition's apparatus with the verse; the texts' names; 30 Hindi-only words (the
    Karanagama's Hindi rendering was sent as Sanskrit); --held-ok (in_repair texts, nothing written to the site);
    --no-glossary-adds (a benchmark); the NEXT line keeps them;
  - scholar_duel.py (new): the engines' Englishes read span by span by gemini-2.5-pro and claude-opus-5-5, blind and
    shuffled; scholar_duels; a blind page; the person's pick;
  - cost_tracker.py: the Claude models in the price table.
- **The texts:** the Hayasirsa Pancaratra and the Karanagama are repaired and held from the site until their working
  English is back (queued); the Tantrik Texts vol. I waits for its re-ingest; the Akasabhairavakalpa for vision OCR;
  the Saradatilaka for its ingest.
- **The pilot:** 18 verses (Hayasirsa 20.5-21.4, Karanagama 30.1-31.1) on gemini-2.5-pro, claude-sonnet-5-5,
  claude-sonnet-5-5@medium and claude-opus-5-5; then the head to head; then the Batch API (CE3) on the engine chosen.

**Tests:**
- `tests/test_claude_engine_2026_10_15.py` (23);
- the replay chain of `test_cost_truth_2026_10_15` and the file check of `test_scholar_2026_10_14` follow.
"""

RUNBOOK = """

## The Claude credit (DOCS56_2026_10_15)

1. `python scripts\\claude_engine.py --credit` (free): spent, left, the expiry. The Console's Billing page is the truth.
2. `python scripts\\claude_engine.py --probe` (about $0.001): the key, the SDK and the meter answer.
3. A scholarly run on Claude: `--engine anthropic:claude-sonnet-5-5` (an effort after "@"); the dry run prints the
   credit; the run stops before the cap ($190) and from 11 Nov.
4. A text in repair (in_repair) needs `--held-ok`; a benchmark run `--no-glossary-adds --redo`.

## Reading engines side by side (DOCS56_2026_10_15)

1. `python scripts\\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --pages 20-21 --limit 12` (the dry run, free), then
   its NEXT line.
2. `--report` writes exports\\scholar_duel_HAYASHIRSHA_PANCARATRA.html, blind; read it before opening the folds.
3. `--pick` with span=number pairs (the page's Translation number) and `--by` with your name records your choice; the
   tally counts it.
"""

EP = """

## Addendum 2026-10-15 (46) (DOCS56_2026_10_15)

| # | Item | State |
|---|---|---|
| CE1 | Claude as an engine of the scholarly English, metered and capped by its credit | Built and tested (CLAUDE_ENGINE_2026_10_15) |
| CE2 | The head to head, blind (two judges of two families, the person's pick) | Built and tested; the pilot of 18 verses, four engines |
| CE3 | The Batch API (half the price) for the engine chosen | After the pilot |
| AG1 | The Agamas and Tantras read as such (rule 13, the apparatus, the Hindi left out) | Built and tested |
| AG2 | The Hayasirsa Pancaratra and the Karanagama whole (about 2,600 passages) | After CE3; --release after their working English |
| AG3 | The Tantrik Texts vol. I, the Akasabhairavakalpa, the Saradatilaka | After the re-ingest, the vision OCR, the ingest |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS55_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS55_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS55_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs56_" + stamp))
        t = p.with_name(p.name + ".tmp_docs56"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
