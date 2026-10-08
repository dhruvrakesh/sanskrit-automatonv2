#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs29_2026_10_08.py  DOCS29_2026_10_08

Records C7 applied and verified (21:41 IST; V0-V7 as expected), the releases that carry the roles
(automaton 455522a2, Srangam bdc5b797), the evening's health of everything that runs on a schedule
(mirror, maintenance embeddings, backups, dashboard, the cloud's nightly embed), and the read-only
health file docs/cloud/OPS_health_2026-10-08.sql. Appends to docs/PLATFORM_2026-10-04.md
(section 32), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 19) and
docs/CORPUS_MIRROR_2026-10-08.md. Needs DOCS28_2026_10_08 in the first three.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs29_2026_10_08.py --check
  python scripts/patch_docs29_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS29_2026_10_08"

PLATFORM = """

## 32. Roles live; the evening's health of everything scheduled (DOCS29_2026_10_08)

**C7 applied at 21:41 IST** (rbac.audit: 16:11:37 UTC). Each paste was run alone, and every result was exported to `D:\\backups\\rbac_2026-10-08\\`.
- **P1-P7, before.**
  - app_role was {admin,moderator,user}. dhruv.rakesh@gmail.com is confirmed and held admin only.
  - user_roles had its two policies from the Srangam migration, both on 'admin'. P4 kept their expressions.
  - The owner of user_roles and the editor's role are both postgres.
  - P6 kept `corpus_reader_allowed()` as C5 wrote it.
  - The mode was signed_in, with corpus.readers empty and no rbac schema.
- **C7a alone, then V0.** {admin,moderator,user,super_admin,researcher}.
- **C7 in one paste.** It succeeded.
- **V1-V7, after.**
  - V1: admin and super_admin.
  - V2: "Admins can view all roles" (SELECT) and "Only super admins can manage roles" (ALL).
  - V3: 12 functions, anon only on research_invite_peek.
  - V4: rbac.invites and rbac.audit closed to anon and authenticated.
  - V5: the trigger rbac_log_role_change.
  - V6: one role_granted super_admin row, with no actor.
  - V7: signed_in.
- **Releases.**
  - Automaton e470c1f6, then 455522a2 (the order, the checks file, 16 tests, docs28).
  - Srangam 4d70389f (the pages), then bdc5b797 (docs and RELIABILITY_AUDIT Phase X), both pushed.
- **Still to do.**
  - Publish in Lovable, if it has not been done since 4d70389f.
  - One invitation end to end with an address you can read.
  - Then, only if wanted, the mode 'readers'.

**What runs on a schedule, and how it stood at about 21:45 IST.**

| What | Where it runs | Evidence | State |
|---|---|---|---|
| The mirror to schema corpus | PC, task SanskritCorpusMirror, every 2 h (corpus_sync.py) | `D:\\backups\\corpus_mirror_log.txt`: 16:35, 18:32, 20:33, all rc=0. At 20:33: 14,458 passages, 374 translations and 21 stories sent; check 392 groups equal, 0 different | Healthy. The next run is about 22:33 |
| Mirror vectors | PC, task SanskritMaintenance, every 3 h when the dashboard is idle (build_embeddings.py, gemini-embedding-001) | `D:\\backups\\maintenance_log.txt` 21:00: "Nothing to embed, all up to date" over 21,915 translated passages. The mirror has sent no new vectors since the full push (vec 0 per run), as expected | Healthy. 14:22 and 18:00 skipped because the dashboard was busy, as designed |
| Vectors of published texts (/texts) | Cloud, pg_cron job 9 'srangam-embed-passages-nightly', 04:15 UTC (embed-published-passages) | Created on 2026-10-07 (section 22, R6). Checked by OPS_health H1-H4 | To confirm with H1-H4. The withheld verses are embedded the night after they are pasted |
| Other nightly jobs (watchdog, pins, OG, terms, context snapshot) | Cloud, pg_cron 1, 2, 6, 7, 8 | docs/CRON_OPS_PLAYBOOK.md (Srangam). H1 | To confirm with H1 |
| The local database backup | PC, task SanskritDBBackup | `backup_log.txt` 07:27: `context_20261008.db` and `context_daily.db`, integrity ok, docs 66, English 21,915, Hindi 12,502 | Healthy. It ran on waking, not at 04:00 |
| The dashboard | PC, D3 launcher (no window) | `D:\\backups\\dashboard_logs\\dashboard_20261008_195219.*`: running since 19:52, the error log empty, keep-awake while jobs run | Healthy. The D3 restart is done |

**The health file.** `docs/cloud/OPS_health_2026-10-08.sql` holds H1-H9, read-only, one per paste:
- H1: every srangam pg_cron job with its last run (the playbook's query);
- H2: the nightly embed's last 7 runs;
- H3: published passages against vectors;
- H4: what is pending;
- H5: the mirror's last runs;
- H6: the mirror's totals;
- H7: texts whose English lacks vectors in the mirror;
- H8: the digests (C4b K1);
- H9: the database size.

pg_net keeps responses for about 6 hours, so H1's http_status is empty for older runs. The proof is then H3 and H4, as the playbook says.
"""

RUNBOOK = """

## Health of everything scheduled (DOCS29_2026_10_08)

1. **On the PC (PowerShell).**
   - `Get-ScheduledTaskInfo` for SanskritCorpusMirror, SanskritMaintenance and SanskritDBBackup: LastTaskResult 0.
   - Then the tails of `D:\\backups\\corpus_mirror_log.txt`, `maintenance_log.txt` and `backup_log.txt`.
2. **In the Lovable Cloud SQL editor.** `docs/cloud/OPS_health_2026-10-08.sql`, H1 to H9, one per paste, read-only. Export the results to `D:\\backups\\ops_<date>\\`.
3. **If H3 shows passages > vectors, or H4 shows rows pending:** the nightly job 9 has not run since they were pasted. Wait for 04:15 UTC, or run C2's R3 once (`docs/cloud/C2_run_and_schedule_2026-10-07.sql`) and then R2.
4. **If H7 lists a text:** its English is newer than the last idle maintenance run. The next SanskritMaintenance run embeds it, and the mirror carries it two hours later at most.
"""

EP = """

## Addendum 2026-10-08 (19) (DOCS29_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Roles: super admin, invited researchers, audit log | Applied: C7 at 21:41 IST, V0-V7 as expected; automaton 455522a2, Srangam bdc5b797 pushed |
| A1p | Publish and one invitation end to end | Next: Publish in Lovable; invite an address you can read; accept in a private window |
| A2 | Mode 'readers' | After A1p, if wanted (the switch on /admin/researchers) |
| D3 | The dashboard without a window | Done: running through the launcher since 19:52; the error log is empty |
| O1 | Health of everything scheduled | PC side healthy (mirror, maintenance embeddings, backup, dashboard). Cloud side: OPS_health H1-H4 to confirm |
| V10 | The 10 withheld verses | In progress: H3 shows passage_count against passages and vectors per text; job 9 embeds them the night after |
"""

MIRROR = """

## Health on 2026-10-08 evening (DOCS29_2026_10_08)

- **Runs.** 16:35, 18:32 and 20:33 IST, all rc=0. At 20:33: 14,458 passages, 374 translations and 21 stories sent; the check found 392 groups equal and 0 different.
- **Vectors.** No new vectors since the full push, because maintenance at 21:00 found nothing to embed among the 21,915 translated passages. A passage gets a mirror vector only after an idle maintenance run embeds it on the PC.
- **Checking it from the cloud side.** `docs/cloud/OPS_health_2026-10-08.sql`: H5 for the runs, H6 for the totals, H7 for English without vectors, H8 for the digests.
- **C7.** Nothing in the mirror changed. `corpus_reader_allowed()` now also admits the super admin always, and researchers in mode 'readers'. The mode is still signed_in.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, True), (Path("RUNBOOK.md"), RUNBOOK, True),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, True),
           (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR, False)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs28 in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs28 and b"DOCS28_2026_10_08" not in raw:
            print("REFUSE: %s has no DOCS28_2026_10_08 section (run patch_docs28 first). Nothing written." % p); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs29_" + stamp))
        t = p.with_name(p.name + ".tmp_docs29"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
