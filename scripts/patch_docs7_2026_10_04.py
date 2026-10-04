#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs7_2026_10_04.py  DOCS7_2026_10_04

Appends to docs/PLATFORM_2026-10-04.md (section 10) and RUNBOOK.md: corrections to section 9,
and the documentation-map addendum (ENTERPRISE_PATH_2026-10-04.md is a new file, committed beside
this patch). Marker-idempotent per file, backup first.

  python scripts/patch_docs7_2026_10_04.py --check
  python scripts/patch_docs7_2026_10_04.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS7_2026_10_04"

PLATFORM = """

## 10. Corrections to section 9 (DOCS7_2026_10_04, CREDITS_COST_2026_10_04)

- **Vision cost.** Section 9 said the measured vision cost was "about $0.0054" a page. The ledger does not show that. Repriced at today's prices, from the 17:58 backup:
  - the last 300 metered pages: median $0.00282, mean $0.00313, p90 $0.00350;
  - all metered history: $0.00407 per delivered page, retries included (1,278 calls for 1,086 pages).
  - At 19:49, `corpus_status` printed "vision $/page 0.0028 (measured: median ...)".
  - Estimates now use the **mean**, because a total is n x mean and page cost is right-skewed. The `corpus_status` fallback is $0.0041.
- **The provider account is prepaid.** `data/jobs.jsonl` shows that at 2026-10-04 10:55 UTC two image jobs got HTTP 402: "Your prepayment credits are depleted". Before CREDITS_COST, translation treated that answer as an ordinary error. It retried three times per verse, then wrote an empty result for every remaining verse. It now aborts the run with `[ABORT]` (CreditsDepleted). The "hard stop" that section 8 placed in Google Cloud is, in practice, the prepaid balance in AI Studio; reconcile it against `usage_log` weekly.
- **Fallback model.** `gemini-2.0-flash` is not in the key's model list (list_models, 2026-10-04 19:49), so the MAX_TOKENS fallback rung never recovered anything. The default is now `gemini-2.5-flash-lite`. `MT_FALLBACK_MODEL` overrides it.
- **Shelf.** The edition badge no longer covers the series number. Titles that repeat inside a collection show their document codes.
- **Backup reads.** A read-only check of `context_pre_orphanfix_20261004_171631.db` on 2026-10-04 left a 0-byte `-wal` and a 32 KB `-shm` beside it. The backup itself is unchanged; its modification time is still 11:46:33 UTC. `diag_orphans.py --backup` opens a backup `immutable=1`, which leaves nothing behind.
- **Forward plan:** `docs/ENTERPRISE_PATH_2026-10-04.md`.
"""

RUNBOOK = """

## Documentation map addendum (DOCS7_2026_10_04)

The map in section 0 predates these. Read them as part of it:

- `docs/ENTERPRISE_PATH_2026-10-04.md`: the forward plan, phases 0-4, and what is true where documents disagree. It supersedes `docs/ENTERPRISE_PATH_2026-09-06.md` section 4 and `ENTERPRISE_ROADMAP.md` as the plan.
- `docs/PLATFORM_2026-10-04.md`: this week's changes. Section 10 corrects section 9.
- `docs/EDITIONS_AND_IMAGES_2026-10-03.md`: editions, plates, the image library.

Rules added on 2026-10-04:

- **Reading a backup:** `python scripts\\diag_orphans.py --db <backup> --backup`. For any other read-only open of a backup, use the URI `?mode=ro&immutable=1`. Never use `immutable` on the live `data/context.db`.
- **Prepaid credit:** a translation run that prints `[ABORT] ... prepaid credits are depleted (HTTP 402)` has stopped cleanly. Top up in AI Studio, then re-run; done verses are kept.
- **Srangam migrations:** `_ops_2026-09-10\\srangam_migration_audit_2026_10_04.sql` is read-only. Do not hand-insert rows into `supabase_migrations.schema_migrations`.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs7_" + stamp))
        t = p.with_name(p.name + ".tmp_docs7"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
