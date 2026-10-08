#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs24_2026_10_08.py  DOCS24_2026_10_08

Records C4b and C5 on the live project, the scheduled mirror task's first good runs (only what
changed travelled), the hidden dashboard launcher (DASH_HIDDEN_2026_10_08, ENTERPRISE_PATH D3)
and the sign-in loop fix for Srangam (AUTH_ROLE_2026_10_08). Appends to
docs/PLATFORM_2026-10-04.md (section 27), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 14) and docs/CORPUS_MIRROR_2026-10-08.md. Marker-idempotent per file, backup first, each
file's line endings kept.

  python scripts/patch_docs24_2026_10_08.py --check
  python scripts/patch_docs24_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS24_2026_10_08"

PLATFORM = """

## 27. The mirror keeps itself current; a dashboard no window can end; a sign-in that went round (DOCS24_2026_10_08)

**C4b on the live project.**
- The C4b file and the 8 rebuilds are applied.
- K1: indexed equals digested in every table. The counts are docs 63, entities 8,269, passages 75,734, translations 13,328, mentions 32,861, stories 44, stages 767, vectors 21,931.
- K2: no rows.

**The two-hourly task (T2).**
- **Why it had not run.** SanskritCorpusMirror did not start on battery (DisallowStartIfOnBatteries was True).
- **The fix.** It was set again with AllowStartIfOnBatteries and DontStopIfGoingOnBatteries.
- **The 16:35 run.** rc=0 in 16 s.
- **The 17:18 run.** It sent 4 new Ganita translations and nothing else, then checked 380 groups equal and 0 different, in 9.3 s.
- **What that shows.** Updates are incremental and idempotent: only changed rows travel, and nothing is uploaded again.

**C5 on the live project.**
- The C5 SQL is applied, and `corpus.reader_access.mode` is `signed_in`.
- Srangam commit 60fe0551 (the /corpus pages, search-corpus) is on origin/main.
- Still to be confirmed: search-corpus deployed, the site published, /corpus read signed in.

**D3: runs died when a console closed (DASH_HIDDEN_2026_10_08).**
- **How runs died.**
  - The dashboard ran in a visible window, and the runs it starts share that console.
  - Closing the window ended the dashboard and every run: exit 3221225786 (0xC000013A, STATUS_CONTROL_C_EXIT) for nine runs since 2026-09-08; on 2026-10-07 a run died with the dashboard.
- **The launcher.** `scripts/restart_dashboard.ps1` now starts it by default in a console that has no window (CreateNoWindow, through `cmd /s /c` so the output can go to a file).
  - **Logs.** Output goes to `D:\\backups\\dashboard_logs\\dashboard_<stamp>.out.log` and `.err.log`, in UTF-8, kept 14 days.
  - **Why UTF-8 is forced.** Output to a file is not a console, so without `PYTHONIOENCODING` Python would write in the ANSI code page, and the banner's box-drawing characters would stop it at startup.
- **Request lines.**
  - The page polls about once a second per open tab, so `SA_QUIET_REQUESTS=1` (set only by the launcher) leaves werkzeug's request lines out of the log.
  - Errors and tracebacks are still written.
- **Restarting.**
  - The script now refuses to restart or stop while a job is running or queued (RUNBOOK 9d); `-Force` overrides.
  - New switches: `-Status` (read-only), `-Stop`, and `-Window` (the old visible window).
- **Tested.** 8 unit tests (`tests/test_dash_hidden_2026_10_08.py`).
  - In a sandbox run of the patched dashboard, three requests left 0 request lines with the flag and 4 without it.
  - A route that fails still logs its traceback.

**The sign-in loop (AUTH_ROLE_2026_10_08, Srangam).**
- **The loop.**
  - A signed-in account that was not an admin, opening /auth, was sent to /admin/tags.
  - ProtectedRoute sent it back to /auth, round and round.
- **The same race for admins.** `isLoading` turned false before `has_role` had answered, so after each sign-in an admin was sent to /auth and back.
- **The fix.**
  - AuthContext adds `roleChecked`, and drops a late answer for a user who has signed out meanwhile.
  - ProtectedRoute waits for the role. Signed out goes to `/auth?next=<the page>`. Signed in but not an admin sees "This area is for the site's editors", with links to /corpus and home.
  - /auth sends a signed-in visitor to `?next=`, else an admin to /admin/tags and anyone else to /corpus.
- **Tested.**
  - 8 vitest tests: 6 failed before the change and all pass after it.
  - The full suite passes, apart from the one sandbox-only meta-freshness check.
  - Typecheck is clean; the build's entry chunk is 487.1 kB (+1.0 kB).
"""

RUNBOOK = """

## The dashboard runs with no window; signing in on Srangam (DOCS24_2026_10_08)

- **Apply, from the automaton root.**
  1. `python scripts\\patch_dash_hidden_2026_10_08.py --check`, then the same without `--check`.
  2. `python -m unittest tests.test_dash_hidden_2026_10_08`.
  3. With the dashboard idle: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1`.
- **Every day.** Each of these is `scripts\\restart_dashboard.ps1` with:
  - no switch: restart. It refuses while a job runs.
  - `-Status`: who listens, the jobs, the newest logs. It changes nothing.
  - `-Stop`: stop it. It refuses while a job runs.
  - `-Force`: cut running jobs off.
  - `-Window`: the old visible window.
- **The log.** `Get-Content -Wait -Tail 40 -Encoding UTF8 <the .err.log it names>`. The logs are in `D:\\backups\\dashboard_logs` and are kept 14 days.
- **What this changes about closing windows.** It replaces the DOCS20 advice to keep the dashboard's console open.
  - A dashboard started by the script has no window to close.
  - A dashboard started any other way (`python scripts\\dashboard.py` in a terminal, or `-Window`) still ends with its window, and so do its runs.
- **It does not come up.** The script prints the last lines of both logs.
- **Srangam sign-in.**
  - A signed-in account that is not an admin sees "This area is for the site's editors" at /admin.
  - /auth sends it to /corpus.
  - Admins are no longer bounced through /auth after signing in.
  - To apply, in `D:\\srangam-42267`, run `patch_auth_role_2026_10_08.py --check`, then the same without `--check`; then typecheck, the tests and the build; then push, then Publish.
"""

EP = """

## Addendum 2026-10-08 (14) (DOCS24_2026_10_08)

| # | Item | State |
|---|---|---|
| C4b | Mirror digests | Applied: K1 indexed = digested in all 8 tables, K2 none |
| T2 | Scheduled mirror task | Fixed (battery conditions). 16:35 and 17:18 runs rc=0; 17:18 sent only 4 changed translations, verify 380 equal |
| C5 | /corpus for signed-in readers | SQL applied, mode signed_in; Srangam 60fe0551 pushed. To confirm: search-corpus deployed, Publish, /corpus signed in |
| D3 | Runs die when the console closes | Fixed in code (DASH_HIDDEN_2026_10_08): no window, logs in D:\\backups\\dashboard_logs, refuses to restart mid-job. To apply: the patch, then a restart while idle |
| A1 | Sign-in loop for signed-in non-admins; admins bounced after sign-in | Fixed in code (AUTH_ROLE_2026_10_08). To apply: the patch in Srangam, push, Publish |
"""

MIRROR = """

## Kept current: the first scheduled runs (DOCS24_2026_10_08)

- After C4b and the 8 rebuilds, K1 showed indexed = digested in all 8 tables, and K2 showed none.
- The two-hourly task ran at 16:35 (rc=0) and again at 17:18.
  - At 17:18 it sent 4 new Ganita translations and nothing else.
  - Its check found 380 groups equal and 0 different, in 9.3 s.
  - New translations reach the mirror within two hours, and nothing is uploaded twice.
- The log is `D:\\backups\\corpus_mirror_log.txt`. `python scripts\\corpus_sync.py --status` compares counts on demand.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP), (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR)]


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
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs24_" + stamp))
        t = p.with_name(p.name + ".tmp_docs24"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
