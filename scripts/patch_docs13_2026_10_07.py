#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs13_2026_10_07.py  DOCS13_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 16), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: why the story buttons were greyed out and the
bulk re-check (STORY_RECHECK), brain_items from the command line (BRAIN_ENV), gaps the
translator never sends (GAPS2), and what the Srangam audit of 2026-10-07 showed (S1).
Marker-idempotent per file, backup first.

  python scripts/patch_docs13_2026_10_07.py --check
  python scripts/patch_docs13_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS13_2026_10_07"

PLATFORM = """

## 16. Greyed-out buttons, the brain from the command line, gaps the translator never sends, the Srangam audit (STORY_RECHECK, BRAIN_ENV, GAPS2, SRANGAM_HEAL_S1 - 2026-10-07; DOCS13_2026_10_07)

**Why the story buttons were greyed out.** Books, versions for younger readers and graphic novels are made from APPROVED stories only, and markandeya_purana had 13 drafts and none approved. Most drafts read "check failed" for a stale reason:
- Stories #3-#13 were written at 19:45 on 2026-10-05, before the verify fix of STORIES_UI_2026_10_05. That fix stopped a citation after the full stop gluing two sentences, and stopped words such as "Later" being taken for names.
- The stored results were never recomputed, so they still showed the old failures.

**Re-checking in bulk** (`stories.py verify-all`; `POST /api/stories/verify-all`; the "Check all again (free)" button).
- It re-runs the check on every written story of a text and on its versions for younger readers. There is no API call.
- It uses the 60-passage window the page and the writer use. The single `verify --id N` now uses it too; it used 40, which could report a long episode as citing outside its own range.
- It stores each result and prints what changed: now passing, still failing (with the first problem), and unchanged. It approves nothing; approval stays a reading step.
- The Review tab gains the filters "draft, check passes" and "draft, check fails", and a "Next:" line with the counts and buttons that open those filters.
- The Book and Graphic novels tabs say why their buttons are greyed and what to do: approve in Review, or tick Proof for a proof copy of drafts.

**The brain from the command line** (BRAIN_ENV_2026_10_07). `brain_items.py` did not load the repo's `.env`, so a run from PowerShell or from maintenance step b2 said "GEMINI_API_KEY not set" and embedded nothing. Only the dashboard's "Update brain" worked, because it inherits the dashboard's environment; it embedded 32 items on 2026-10-07. The script now calls `env_loader.load_env()` as build_embeddings, images and stories do.

**Gaps the translator never sends** (GAPS2_2026_10_07). corpus_status kept markandeya_purana at NEEDS-TRANSLATION ("1 passages without English; 1 passages without Hindi", $0.00). The commands it printed translated nothing, because translate_passages.py silently skips three kinds of row, with no outcome record:
- a page numbered below 1 (`--since-page` defaults to 1);
- text that `should_translate()` rejects (too little Devanagari, `--min-dev 0.05`);
- text that `clean_for_mt()` reduces to nothing.

corpus_status now counts these as gaps, reported as "N never sent: page 0 or no translatable Sanskrit". It uses the same functions as the translator, so the two agree. It is still read-only.

**The Srangam audit of 2026-10-07** (ops/srangam_migration_audit_2026_10_04.sql, run 13:19-13:32).
- **Q1, migration history.** 57 versions are in the repo and not recorded, and 56 are recorded and not in the repo. 55 of these pair up within 6 seconds of each other: Lovable records the apply time and the file carries its own timestamp, so they are the same migrations. The expectation of "exactly 1 row" was wrong.
  - The real differences are three. 20260201064547 is recorded with no file; S1 H1 shows what it did. 20260718120000 (B1) was applied through the editor on 2026-09-08 and is live. 20260910120000 (the stats view) was never applied.
- **Q2, B1 objects.** All present: 2 tables, 3 indexes, 4 policies, 2 triggers, and RLS on both tables. `srangam_cross_reference_stats` is absent. `src/pages/ResearchNetwork.tsx` line 148 reads that view and returns null on error, so /research-network shows blank totals.
- **Q3, published texts.** AphorismsOfSandilya is published, with 439 of 439 passages present; the last write was at 09:20 UTC on 2026-09-27.
- **Q4, history table.** Its columns are version, statements, name, created_by, idempotency_key and rollback. No row is written by hand.
- **Q5, pg_cron.** 5 jobs, all active, with no failure in 7 days; the watchdog alone ran 2,016 times.
- **Q6, pg_net.** One 202 at 03:00 UTC and one 200 at 04:00 UTC, with no errors. By default pg_net keeps responses for only 6 hours, so this covers the morning, not the week.

**S1** (`docs/cloud/S1_srangam_heal_2026-10-07.sql`). These blocks are pasted one at a time into the Lovable Cloud SQL editor:
- H1 and H2 only read.
- H3 creates the view verbatim from the repo's own migration (security_invoker, select granted to anon and authenticated). It is reversible with `DROP VIEW`.
- H4 verifies, followed by `block_BE_reader.ps1 -Verify`.

It was tested on PostgreSQL 16, where all four ran.
"""

RUNBOOK = """

## Greyed-out story buttons, the brain from the command line, Srangam S1 (DOCS13_2026_10_07)

- **The Book, Graphic novel or "For younger readers" buttons are greyed.** Nothing of that text is approved yet.
  - On the Stories page press "Check all again (free)". Then choose the status filter "draft, check passes", read each story (click a citation to see its passages) and press Approve.
  - Drafts in "draft, check fails" need Edit, Rewrite or "Approve anyway".
  - From the command line: `python scripts\\stories.py verify-all --doc markandeya_purana`.
  - For a proof copy before anything is approved, tick Proof in the Book tab.
- **Update the brain from PowerShell.** Run `python scripts\\brain_items.py --db data\\context.db`. It now reads `.env` itself. Maintenance step b2 does the same every 3 hours when the dashboard is idle.
- **A translation gap that never closes.** If corpus_status says "N never sent", those rows are page 0 or carry no translatable Sanskrit (a lone danda, a stray mark). The translator will not send them, and that is correct; they are not work.
- **Srangam S1.** Paste `docs\\cloud\\S1_srangam_heal_2026-10-07.sql` into the Lovable Cloud SQL editor one block at a time: H1, H2, H3, H4. Then run `block_BE_reader.ps1 -Verify`. Never insert into supabase_migrations.schema_migrations by hand.
"""

EP = """

## Addendum 2026-10-07 (3): healing after the audit (DOCS13_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.17 | Bulk re-check of stories, "draft passes / fails" filters, "Next:" line, greyed-button explanations (STORY_RECHECK) | Built 2026-10-07 |
| 1.14 | brain_items loads `.env` (CLI and maintenance b2 failed with "GEMINI_API_KEY not set") | Built 2026-10-07 |
| 1.15 | corpus_status counts rows the translator never sends as gaps (GAPS2) | Built 2026-10-07 |
| S1 | Srangam: inspect 20260201064547 (H1), apply `srangam_cross_reference_stats` (H3), verify (H4) | Ready to run in the SQL editor |
| T1 | Ganita_Yukti_Bhasa translate_both: 709 of 1,460, stopped by the 12:16 restart on 2026-10-07 | Open: resume from the dashboard, machine kept awake |
| 1.12 | Maintenance alongside long translations | Open: measure concurrent writes first |
| 1.13 | Delete the vectors of noise rows | Open; Ask already filters them |
| C0 / C1 / C2 | Cloud pre-flight, corpus brain schema, `embed-published-passages` | C0 ready to run; C1 drafted and tested, not applied; C2 next |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs13_" + stamp))
        t = p.with_name(p.name + ".tmp_docs13"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
