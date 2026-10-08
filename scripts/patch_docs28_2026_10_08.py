#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs28_2026_10_08.py  DOCS28_2026_10_08

Records where RBAC_RESEARCHERS_2026_10_08 stands after the evening's releases (automaton e470c1f6,
Srangam 4d70389f), the first attempt at C7 in the SQL editor (21:14: rolled back whole, nothing
changed), the corrected order with its own checks file (docs/cloud/C7_checks_2026-10-08.sql), the
Srangam documentation follow-up (scripts/patch_rbac_docs_2026_10_08.py) and the path forward.
Appends to docs/PLATFORM_2026-10-04.md (section 31), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md (addendum 18). Needs DOCS27_2026_10_08 in each.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs28_2026_10_08.py --check
  python scripts/patch_docs28_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS28_2026_10_08"

PLATFORM = """

## 31. Roles: where they stand, and the first attempt at C7 (DOCS28_2026_10_08)

**Released.**
- **Automaton.** e470c1f6 (21:23): C7a, C7, the PostgreSQL tests, the Srangam payload, the patcher, docs27.
- **Srangam.** 4d70389f (21:24), pushed: the RBAC pages and AuthContext roles (patch_rbac_2026_10_08.py applied; a re-run writes nothing).
- **Until C7 is applied, the site behaves exactly as before.**
  - `my_roles()` does not exist, so the roles follow `has_role`.
  - `/admin/researchers` says that C7 is not applied.
  - The browser logs one 404 for `my_roles` at each sign-in.

**The first attempt at C7 (21:14).**
- **The preflight was as expected.**
  - app_role was {admin,moderator,user}.
  - dhruv.rakesh@gmail.com exists (email confirmed 2025-11-10) and holds admin only.
  - user_roles has two policies: "Admins can view all roles" (SELECT) and "Only admins can manage roles" (ALL).
  - The table's owner and the editor's role are both postgres.
- **C7a was pasted together with `SELECT enum_range(...)`.** The editor runs one paste as one transaction, and PostgreSQL refuses to read a new enum value in the transaction that added it. The result was error 55P04, "unsafe use of new value", and the whole paste, values included, rolled back.
- **C7 was then refused by its own guard** ("run C7a first, on its own"). Nothing was created.
- **A re-check showed {admin,moderator,user}.** The database is as it was.
- **The fault was in the instructions given with docs27, not in the files.** They put that check in the same block as C7a. The files behaved as designed: C7a is two statements, and C7 checks its preconditions first.

**What changed (no change to what C7 does).**
- **`docs/cloud/C7_checks_2026-10-08.sql`.** The read-only checks, one query per paste:
  - P1-P7 before. They include the policy expressions (P4) and the reader gate's definition (P6), which are the exact source for a rollback.
  - V0 after C7a.
  - V1-V7 after C7. V4 is new: rbac.invites and rbac.audit are closed to anon and authenticated.
- **C7a's and C7's headers.** They give the order and say that C7a is pasted alone. The SQL statements are unchanged.
- **`tests/test_rbac_researchers_pg_2026_10_08.py`, 16 tests (was 14).**
  - On a fresh database it replays the 21:14 sequence. C7 before C7a is refused with nothing created. C7a with a SELECT in its paste gives 55P04 and keeps nothing. C7a alone then works, and works again harmlessly.
  - Every check in C7_checks is one SELECT that runs.
- **Srangam documentation, `scripts/patch_rbac_docs_2026_10_08.py` (RBAC_DOCS_2026_10_08).** Documentation only:
  - `docs/RBAC_RESEARCHERS_2026-10-08.md` gains the order and the 21:14 note. It is replaced only over the version 4d70389f wrote.
  - `docs/RELIABILITY_AUDIT.md` gains Phase X: the roles, the user_roles policy, the RPCs callable by anon and authenticated under Invariant 15, and invariants 23-26.

**Within the documented guardrails.**
- **Roles.** They stay in `user_roles` behind the SECURITY DEFINER `has_role()` (RELIABILITY_AUDIT M.2; ENTERPRISE_AUDIT finding 3). C7 extends that model; it does not add a second one.
- **Applying it.**
  - Through the Lovable Cloud SQL editor only, one block per paste, with read-only checks before and after, kept as CSV exports (ENTERPRISE_PATH "Rules for every phase"; the C0 and S1 precedent).
  - No file is added to supabase/migrations, and no history row is written (S1/S2).
- **Edge functions.** Unchanged. `requireAdmin()` checks `has_role(uid, 'admin')`, which the super admin keeps.
- **Rollback.** At the head of C7, with P4 and P6 as the exact "before" record.
"""

RUNBOOK = """

## Roles on Srangam: apply C7 (corrected order) and the docs follow-up (DOCS28_2026_10_08)

Srangam 4d70389f already carries the pages. Only the database and the docs remain.

1. **Preflight.** Open `docs/cloud/C7_checks_2026-10-08.sql`. In the Lovable Cloud SQL editor, run P1 to P7, one query per paste, and Export CSV each result into `D:\\backups\\rbac_2026-10-08\\`.
2. **C7a, alone.** Clear the editor. Paste ONLY `docs/cloud/C7a_rbac_roles_2026-10-08.sql` and run it.
   - Then clear the editor and run V0 on its own. Expect {admin,moderator,user,super_admin,researcher}.
   - Never add anything to C7a's paste. A SELECT there is error 55P04, and the whole paste rolls back.
3. **C7, in one paste.** Clear the editor. Paste the whole `docs/cloud/C7_rbac_researchers_2026-10-08.sql` and run it.
   - If it says "run C7a first", step 2 did not commit: repeat step 2.
4. **Verify.** Run V1 to V7, one query per paste, and export each result.
5. **Srangam docs (D:\\srangam-42267).**
   - Run `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_docs_2026_10_08.py" --check`, then without --check.
   - `git add` the two docs, commit, push. Publish is not needed for docs.
6. **Check on the site** (after Publish of 4d70389f).
   - Sign in. /admin/researchers shows the Super admin badge, and no notice that the roles functions are missing.
   - Invite an address you can read. Open the link in a private window, create the account, confirm it, and accept. The person appears under People with access.
7. **Close the corpus to plain sign-ups,** only after step 6. Choose "Invited researchers" on /admin/researchers; this is audited.
"""

EP = """

## Addendum 2026-10-08 (18) (DOCS28_2026_10_08)

| # | Item | State |
|---|---|---|
| A1 | Roles: super admin, invited researchers, audit log | Site: Srangam 4d70389f, pushed. Database: first attempt 21:14 rolled back cleanly, so C7 is still to apply: P1-P7, C7a ALONE, V0, C7, V1-V7 (C7_checks) |
| A1d | Srangam docs: the order; RELIABILITY_AUDIT Phase X and invariants 23-26 | patch_rbac_docs_2026_10_08.py, after A1 or before it (documentation only) |
| A2 | Close the corpus to plain sign-ups (mode 'readers') | After the first researcher has accepted: the switch on /admin/researchers |
| A3 | Invitation email sent by the site | Next: an edge function on `_shared/auth-gate.ts` (requireUser, then `is_super_admin()`), using the service role for `auth.admin.inviteUserByEmail` (new accounts) or a provider such as Resend. Needs `/invite/*` allowed as an auth redirect URL in Lovable Cloud |
| A4 | Researchers' requests (corrections, texts) | With L4: a request queue the desk pulls |
| A5 | Types | Lovable regenerates `types.ts` with the new enum values and functions when it next syncs the schema; the site does not depend on it (typed wrappers in `src/lib/rbac.ts`) |
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
        if b"DOCS27_2026_10_08" not in raw:
            print("REFUSE: %s has no DOCS27_2026_10_08 section (run patch_docs27 first). Nothing written." % p); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs28_" + stamp))
        t = p.with_name(p.name + ".tmp_docs28"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
