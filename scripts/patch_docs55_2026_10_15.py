#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs55_2026_10_15.py  DOCS55_2026_10_15

Records 15 Oct: the thinking of gemini-2.5 was not metered (the SDK here does not name thoughts_token_count), so the
spend recorded, the spend cap and the scholarly English's price left it out; COST_TRUTH_2026_10_15 (the meter reads
total_token_count; the scholarly price counts only rows metered so; a job that only adds working English does not stop
the scholarly run; a queued job stopped does not start); REPO_HYGIENE_2026_10_15 (MBh01's e-text import and the heal
log were committed in 7d292ca; .gitignore and release.ps1 keep them out); the night's runs. docs/COST_TRUTH_2026-10-15.md
has the details.

Appends to docs/PLATFORM_2026-10-04.md (section 58), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 45), each needing DOCS54_2026_10_14.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs55_<date>), line endings kept.

  python scripts/patch_docs55_2026_10_15.py --check
  python scripts/patch_docs55_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS55_2026_10_15"

PLATFORM = """

## 58. What a call costs, metered as it is billed; the repo kept clean (DOCS55_2026_10_15)

**15 Oct (IST).** docs/COST_TRUTH_2026-10-15.md has the details.
- **The thinking was not metered.** Five gemini-2.5-pro drafts of 14 Oct came back empty at the 8,192-token limit and
  were metered as their input alone; the SDK here does not name thoughts_token_count, and total_token_count was not
  read. Google bills thinking as output ($10 a million tokens for gemini-2.5-pro, $2.50 for gemini-2.5-flash). The
  run that recorded $0.256 cost at least $0.67. The spend recorded, the spend cap and the scholarly English's price
  left the thinking out; how much for the working English (gemini-2.5-flash) is to be measured.
- **COST_TRUTH_2026_10_15:**
  - usage_meter.py, infer_mt.py, source_desk.py: the output billed is total - prompt when that is more;
  - scholar_translate.py: the price counts only rows metered so (METERED_SINCE 2026-10-15), the prior is 3,000
    output tokens a call (about $0.10 a verse); a job that only adds working English does not stop a run;
  - dashboard.py: a job stopped while queued does not start (after a restart).
- **REPO_HYGIENE_2026_10_15:** 7d292ca committed data/raw_mbh01_ce/ (MBh01's critical-edition e-text, BORI's: "do not
  provide copies") and data/heal/. .gitignore and release.ps1 now keep them out; git rm --cached takes them out of
  the repo; the copy in the history is the owner's decision if the repo is public.
- **The night's runs:** C17 is in the Lovable database (anon false, authenticated true); MBh01 is not in the public
  reader; the Natyasastra's English runs (2,101 of 2,793 at 09:26), with 19 jobs behind it; MBh01's prose waits for
  the queue to end.

**Tests:**
- `tests/test_cost_truth_2026_10_15.py` (9);
- `tests/test_repo_hygiene_2026_10_15.py` (4).
"""

RUNBOOK = """

## What a call really costs (DOCS55_2026_10_15)

1. One call shows the thinking (a fraction of a cent): its usage_metadata's total minus prompt minus candidates.
2. usage_log by day beside Google's bill for the same days shows how far the meter of before 15 Oct was off.
3. The cap: `python scripts\\set_budget.py` shows it; from COST_TRUTH_2026_10_15 it counts the thinking.
4. The scholarly English's dry run prices by the prior (about $0.10 a verse) until 10 rows are metered with the
   thinking; use the cap its `NEXT:` line gives.

## Keeping working files out of the repo (DOCS55_2026_10_15)

release.ps1 stages everything. A directory of working files goes into .gitignore before the release, and into the
safety check's list. One committed by mistake leaves the repo with `git rm -r --cached` and a release; the file stays
on disk.
"""

EP = """

## Addendum 2026-10-15 (45) (DOCS55_2026_10_15)

| # | Item | State |
|---|---|---|
| CT1 | The thinking metered as it is billed | Built and tested (COST_TRUTH_2026_10_15); measure the old gap against the bill |
| CT2 | The scholarly English priced from rows metered with the thinking | Built (prior about $0.10 a verse until 10 rows) |
| CT3 | Cheaper scholarly English (the second judge on a sample, one revision, a flash draft, batch mode) | Each measured on 1.1.15-1.1.23 first |
| DQ1 | A queued job stopped does not start | Built and tested; live after the next idle restart |
| RH1 | MBh01's e-text import and the heal logs out of the repo | Built and tested (REPO_HYGIENE_2026_10_15); git rm --cached by hand; the history is the owner's call |
| MB1 | MBh01's lost prose | Waits for the translate queue to end, then the re-ingest |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS54_2026_10_14"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS54_2026_10_14"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS54_2026_10_14")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs55_" + stamp))
        t = p.with_name(p.name + ".tmp_docs55"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
