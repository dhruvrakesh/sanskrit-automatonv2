#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs62_2026_10_16.py  DOCS62_2026_10_16

Records 16 Oct: the two Agamas done (the Hayasirsa 1,418 verses, 83% passed; the Karanagama 1,018, 85%), the credit
($80.51 left), what Gemini really costs (the thinking), TRIAGE_2026_10_16, the Tantrik Texts vol. I (its pages; page 18
a vision OCR's invention), MARK_PASSAGES_2026_10_16 and THINKING_PROBE_2026_10_16. docs/TRIAGE_2026-10-16.md has the
details.

Appends to docs/PLATFORM_2026-10-04.md (section 65), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 52), each needing DOCS61_2026_10_15.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs62_<date>), line endings kept.

  python scripts/patch_docs62_2026_10_16.py --check
  python scripts/patch_docs62_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS62_2026_10_16"

PLATFORM = """

## 65. The two Agamas done; the triage; the Tantrik Texts vol. I; what Gemini costs (DOCS62_2026_10_16)

**16 Oct (IST).** docs/TRIAGE_2026-10-16.md has the details.
- **Done on claude-sonnet-5-5** (15 Oct, 13:36 to 16:12 UTC): the Hayasirsa Pancaratra 1,418 verses (1,176 passed,
  220 flagged, 22 source doubts); the Karanagama 1,018 (867, 147, 4). 116 of the Hayasirsa's were judged by Haiku:
  --rejudge reads them again. Both stay held until their working English is back (1 and 368 passages of it).
- **The credit:** $109.49 spent, $80.51 left to 11 Nov.
- **Gemini, 15 Oct, $19.54 by the ledger:** entities $6.48, the flash judge $5.69, the working English $4.73, Pro
  $2.58. The thinking is most of it (a judge call: 1,053 output tokens, $0.00274). The flash judge of both texts cost
  about $5.7, not the Rs 80 estimated on 15 Oct (that prior did not count the thinking).
- **TRIAGE_2026_10_16 (scholar_translate.py):** triage_of (rejected, source, serious, mild); --triage (a CSV for a
  person, free); --only-flagged ENGINE [--serious]; --status counts the tiers; the re-judge priced as measured. Today:
  the Hayasirsa 84 serious, 22 source, 136 mild; the Karanagama 62, 4, 85.
- **The Tantrik Texts vol. I:** pages 19-74 are the index (not verse), 75-156 the verse texts (849 ready), 157-210
  the code tables (403). Page 18's two passages are a vision OCR's invention (the opening of the Mahabharata on a
  faded title page): MARK_PASSAGES_2026_10_16 (scripts/mark_passages.py) tags them noise, logged and undoable.
- **THINKING_PROBE_2026_10_16 (scripts/gemini_thinking_probe.py):** the judge with and without gemini-2.5-flash's
  thinking (thinkingBudget 0), on N verses, metered: what it saves and how far the scores agree. A person decides.

**Tests:**
- `tests/test_triage_2026_10_16.py` (6), `tests/test_mark_probe_2026_10_16.py` (5);
- test_rejudge_2026_10_15 follows (its chain ends at .bak_triage_; the re-judge priced as measured).
"""

RUNBOOK = """

## The verses that did not pass (DOCS62_2026_10_16)

1. `--engine anthropic:claude-sonnet-5-5 --rejudge --limit 2000` (a dry run), then with `--yes`: the verses a Claude
   judge read get the Gemini judge's reading.
2. `--engine anthropic:claude-sonnet-5-5 --triage` (free): exports\\scholar_triage_<doc>.csv; rejected, source,
   serious, mild.
3. `--engine anthropic:claude-opus-5-5 --only-flagged anthropic:claude-sonnet-5-5 --serious --compare-engine
   anthropic:claude-sonnet-5-5 --audit-every 1`: another model reads the serious again (a dry run first).
4. A person reads (`--report`), and marks what was read (`--review ... --verdict accept|reject --by ...`).

## A page whose reading is not what it prints (DOCS62_2026_10_16)

- `python scripts\\mark_passages.py --doc <doc> --pages <n> --type noise --reason "..."` (a dry run), then
  `--apply`; `--undo --apply` puts it back. Only text_type changes; the log is data\\mark_passages_log.jsonl.
"""

EP = """

## Addendum 2026-10-16 (52) (DOCS62_2026_10_16)

| # | Item | State |
|---|---|---|
| AG2 | The Hayasirsa and the Karanagama whole | Done 15 Oct (1,418 and 1,018 verses) |
| TR1 | The triage; another model on the serious (TRIAGE_2026_10_16) | Built and tested |
| AG3 | The Tantrik Texts vol. I: the verse texts, pages 75-156 (849) | The canary first (pages 75-77) |
| AG3b | Its code tables, pages 157-210 (403) | After AG3, if the credit allows |
| MP1 | A person's text_type for a page (mark_passages.py); the Tantrik Texts' page 18 | Built and tested |
| TB1 | Gemini 2.5 Flash's thinking: the probe, then a person's decision per kind | The probe built; not decided |
| WE1 | The working English of the two Agamas (about 2,900 passages) | After the benchmark (CF3) |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS61_2026_10_15"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS61_2026_10_15"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS61_2026_10_15")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs62_" + stamp))
        t = p.with_name(p.name + ".tmp_docs62"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
