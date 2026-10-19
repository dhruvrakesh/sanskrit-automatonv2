#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs77_2026_10_19.py  DOCS77_2026_10_19

Records 19 Oct (morning): what is done in full and what is not; the model's words found in 14 stored translations and
the guard (LEAK_GUARD_2026_10_19); the English a T2 run emptied (KEEP_ON_EMPTY_2026_10_19); heal_english.py
(HEAL_ENGLISH_2026_10_19); docs/LEAK_GUARD_2026-10-19.md.

Appends to docs/PLATFORM_2026-10-04.md (section 80), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 67)
and docs/STATE_2026-10-18.md (section 12), each needing DOCS76_2026_10_18. Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs77_<date>), line endings kept.

  python scripts\\patch_docs77_2026_10_19.py --check
  python scripts\\patch_docs77_2026_10_19.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS77_2026_10_19"

PLATFORM = """

## 80. Is it done in full; the model's words in a translation; an empty re-translation (DOCS77_2026_10_19)

**19 Oct (morning).** docs/LEAK_GUARD_2026-10-19.md.
- **Done:** the scholarly English in the mirror (the site grew by 7,927 rows: the GRETIL Markandeya adopted, 2,686
  scholarly rows), C18 pasted, the reader pushed (Srangam `beedafe5`), two editions (the Devimahatmya; adhyayas 19 to
  31). **Not yet:** the Surya Siddhanta (422 of 515), the rest of the Markandeya (1,408 of 5,240), the Ganita's
  scholarly English (beyond both budgets: the Claude credit $4.16, Google $9.69).
- **LEAK_GUARD_2026_10_19:** 14 of 41,932 stored translations held the model's words to us (a preamble, a second
  version, its reasoning). text_filters.model_chatter / strip_model_chatter; translate_passages.py keeps only the
  translation; infer_mt.py never caches the rest.
- **KEEP_ON_EMPTY_2026_10_19:** a re-translation that came back empty wiped the English, unarchived (four T2 passages).
  Now it keeps it.
- **HEAL_ENGLISH_2026_10_19:** scripts/heal_english.py mends what is stored through translate_passages.py, from mt_cache.

**Tests:** test_leak_guard_2026_10_19 (9), test_heal_english_2026_10_19 (3), test_docs77_2026_10_19 (2).
"""

RUNBOOK = """

## The model's words in a translation, and the English a T2 run emptied (DOCS77_2026_10_19)

docs/LEAK_GUARD_2026-10-19.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\\patch_leak_guard_2026_10_19.py --check`, then without --check; the same for
   `scripts\\patch_docs77_2026_10_19.py`; `python -m unittest tests.test_leak_guard_2026_10_19 tests.test_heal_english_2026_10_19
   tests.test_docs77_2026_10_19 tests.test_guards_2026_10_04 tests.test_claude_first_2026_10_15 tests.test_scholar_2026_10_14`.
2. `python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_heal_20261019.db`; `python scripts\\heal_english.py` (the plan, free); `python scripts\\heal_english.py
   --yes` (free: from mt_cache); `python scripts\\heal_english.py --yes --fresh` (Sonnet, a few cents, for what was
   emptied); `python scripts\\corpus_sync.py` (the plan); the scheduled mirror sends it.
3. Release with COMMIT_MSG_leakguard_20261019.txt.
"""

EP = """

## Addendum 2026-10-19 (67) (DOCS77_2026_10_19)

| # | Item | State |
|---|---|---|
| Q7 | The model's words in a stored translation | Guarded: LEAK_GUARD_2026_10_19; 14 found, mended by heal_english.py |
| Q8 | An empty re-translation wipes the English | Fixed: KEEP_ON_EMPTY_2026_10_19; 4 lost, back from mt_cache |
| S2 | The Surya Siddhanta's scholarly English | 422 of 515; 88 verses left (yours: Gemini 2.5 Pro now, or Sonnet with credit) |
| G2 | The Ganita's scholarly English | Waiting: about $30 on Gemini 2.5 Pro; neither budget holds it |
| U2 | Sanskrit terms in backticks (Gemini's working English, 1,687 passages) | Yours: italics in the reader, or as they are |
"""

STATE = """

## 12. The morning of 19 Oct: what is done in full (DOCS77_2026_10_19)

- **Done:** the scholarly English in the mirror and the reader (the GRETIL Markandeya adopted; the site 197,632 rows,
  380 groups equal at 10:46 IST); C18 pasted (P1 and V1 still to read); Srangam `beedafe5` pushed; the editions: the
  Devimahatmya and adhyayas 19 to 31; the top bars.
- **Not yet:** the Surya 422 of 515 (337 passed, 84 flagged, 1 doubted; $20.36); the Markandeya 1,408 of 5,240 in
  scholarly English; the Ganita's scholarly English.
- **The money:** the Claude credit $4.16 left of its $190 cap (to 11 Nov); Google $9.69 left of $85.
- **The screen's wrong meanings:** 149 of 4,591 (3%): the Markandeya 24 (19 blame the Sanskrit), the Sandilya 17 (13),
  the Ganita 45 (40), the Mallapurana 45 (34), the Bodhicaryavatara 15 (7), the Satapatha 3.
- **Found and mended:** the model's words in 14 translations (LEAK_GUARD); four English a T2 run emptied (KEEP_ON_EMPTY);
  heal_english.py. docs/LEAK_GUARD_2026-10-19.md.
- **Section 9's table** now reads to docs/LEAK_GUARD_2026-10-19.md for the translation guards.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS76_2026_10_18"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS76_2026_10_18"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS76_2026_10_18"),
           (Path("docs/STATE_2026-10-18.md"), STATE, "DOCS76_2026_10_18")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs77_" + stamp))
        t = p.with_name(p.name + ".tmp_docs77"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
