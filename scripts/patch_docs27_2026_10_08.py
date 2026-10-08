#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs27_2026_10_08.py  DOCS27_2026_10_08

Records the library applied (C6, L1) and roles on the site (RBAC_RESEARCHERS_2026_10_08:
docs/cloud/C7a and C7, the Srangam patch scripts/patch_rbac_2026_10_08.py): one super admin,
invited fellow researchers, the reader gate with researchers, the audit log.
Appends to docs/PLATFORM_2026-10-04.md (section 30), RUNBOOK.md,
docs/ENTERPRISE_PATH_2026-10-04.md (addendum 17) and docs/CORPUS_MIRROR_2026-10-08.md.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs27_2026_10_08.py --check
  python scripts/patch_docs27_2026_10_08.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS27_2026_10_08"

PLATFORM = """

## 30. Roles on the site: a super admin and invited researchers (DOCS27_2026_10_08)

**Applied before this.**
- **C6 and L1.** C6 applied: the grants check showed anon false and authenticated true on all five functions. L1 released: automaton 5113170a (with docs26), Srangam f9fbde31.
- **What the mirror holds.**
  - Stories: 16 approved, 6 draft, 22 candidate. Readers see the 16 approved; admins see all 44.
  - Names by kind: other 2,822; person 2,392; deity 1,798; place 681; people 324; river 187; mountain 65.
  - srangam_texts: markandeya_purana has passage_count 1,219 and is published.

**The roles (public.app_role, public.user_roles, has_role).**

| Role | Who | May |
|---|---|---|
| super_admin | dhruv.rakesh@gmail.com | invite and remove researchers, set who reads the corpus, read the audit log, the only role that writes user_roles from the site; keeps 'admin' too |
| admin | editors | unchanged |
| researcher | invited fellow researchers | read the working corpus in modes signed_in and readers |

**C7a.** `docs/cloud/C7a_rbac_roles_2026-10-08.sql` adds the enum values `super_admin` and `researcher`. It is run alone, first, because PostgreSQL will not use a new enum value in the transaction that added it.

**C7.** `docs/cloud/C7_rbac_researchers_2026-10-08.sql` runs in one transaction and refuses to run if C7a or C5 is missing. It adds:
- **The super admin.** Grants super_admin (and admin, if missing) to the account dhruv.rakesh@gmail.com. If that account is not in auth.users, the whole file fails and nothing changes.
- **Schema `rbac`.** Not exposed through the API; RLS is on, with no policies and no grants.
  - `rbac.invites` keeps only the SHA-256 of each link token. There is at most one open invitation per email.
  - `rbac.audit` records invitations, acceptances, withdrawals, mode changes and, through a trigger on user_roles, every role change (one made in the SQL editor shows no actor).
- **The reader gate.** `corpus_reader_allowed()` keeps C5's rule and adds two cases:
  - the super admin may always read;
  - in mode 'readers', a researcher may read, as a user on corpus.readers already could.

  C7 does not change the mode. It stays signed_in until the super admin changes it.
- **Who writes roles.** The policy "Only admins can manage roles" becomes "Only super admins can manage roles". "Admins can view all roles" stays. No site code writes user_roles. If the editor's role does not own user_roles, this step and the trigger are skipped with a NOTICE.
- **12 functions, SECURITY DEFINER, search_path ''.**

  | Function | For |
  |---|---|
  | `research_invite_peek` | anyone; it returns only the status, a masked email and the expiry |
  | `my_roles`, `is_super_admin` | any signed-in user, about their own account |
  | `research_invite_accept` | signed-in users; it needs the invited email, confirmed, and an open link |
  | `research_invite_create`, `research_invites_list`, `research_invite_revoke`, `rbac_members_list`, `researcher_remove`, `rbac_audit_list`, `corpus_access_mode`, `corpus_access_mode_set` | the super admin |
- **Tested.** 14 PostgreSQL tests (`tests/test_rbac_researchers_pg_2026_10_08.py`). They cover:
  - C7 refusing without the account, and changing nothing;
  - the grants;
  - links and masking;
  - every outcome of accepting;
  - the gate in all three modes;
  - the user_roles policy as an admin, as a reader and as the super admin.

**The site (scripts/patch_rbac_2026_10_08.py, payload docs/srangam/RBAC_2026-10-08/).**
- **`/admin/researchers`.** The super admin's page; an admin who is not the super admin is told so. It has:
  - who may read (signed_in / readers / admins);
  - invite a researcher: email, private note, 7 to 90 days. The link is shown once, with Copy link and Email it (the super admin's own mail program; nothing is sent from the site);
  - invitations, with Withdraw;
  - people with access, with Remove;
  - the audit log.
- **`/invite/:token`.** The researcher's page:
  - signed out: sign up or sign in, and come back to this page;
  - signed in with the wrong address: told so, with Sign out;
  - signed in with the invited address: Accept, then on to /corpus.
- **AuthContext.** Adds `roles`, `isSuperAdmin`, `isResearcher` and `refreshRoles`. `my_roles()` is asked together with `has_role`. Before C7 it does not exist, and the roles follow has_role. `signUp(email, password, redirectPath)`: the confirmation email comes back to the page the reader came from.
- **Auth page.** `?next=/invite/...` and `?tab=signup`.
- **Admin sidebar.** A Researchers link (super admin only) and a Super admin badge. The header no longer overflows a phone screen.
- **Corpus refusal.** It says that researchers get in by invitation.
- **Tested.**
  - 26 new vitest tests; auth-role.test.tsx's mock now knows my_roles.
  - The full suite: 189 passed, apart from the one sandbox-only check.
  - Typecheck and eslint are clean.
  - The entry chunk is 488.9 kB (+1.1 kB). The new pages are lazy: Researchers 15.7 kB, InviteAccept 6.5 kB, rbac 5.0 kB.

**Not done (next).**
- **Automatic invitation email.** An edge function with the service role (`auth.admin.inviteUserByEmail`) or Resend. It needs `/invite/*` allowed as an auth redirect URL in Lovable Cloud, and a sending domain.
- **Researcher requests.** Corrections and text requests from researchers, through the L4 request queue.
"""

RUNBOOK = """

## Roles on Srangam: apply C7 and the RBAC patch (DOCS27_2026_10_08)

1. **Lovable Cloud SQL editor.**
   - Run `SELECT enum_range(NULL::public.app_role);`. Expect {admin,moderator,user}.
   - Run `docs/cloud/C7a_rbac_roles_2026-10-08.sql` ALONE.
   - Run the check again. Expect {admin,moderator,user,super_admin,researcher}.
2. **Run C7.** Paste the whole `docs/cloud/C7_rbac_researchers_2026-10-08.sql`, then run the checks V1 to V6 at its end:
   - V1: your email with admin and super_admin;
   - V2: two policies;
   - V3: anon true only for research_invite_peek;
   - V4: one trigger;
   - V5: the audit log;
   - V6: the mode is still signed_in.
3. **Srangam (D:\\srangam-42267, on main).**
   - Run `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_2026_10_08.py" --check`, then without --check.
   - Then `npm run typecheck`, `npx vitest run` and `npm run build`.
   - `git add` the explicit paths, commit, push, and Publish in Lovable.
4. **First invitation.**
   - Sign in. Open /admin/researchers (the sidebar shows Researchers and the badge says Super admin).
   - Invite an address you can read. Open the link in a private window. Create the account, confirm it if asked, and accept.
   - Check that the person appears under People with access.
5. **Close the corpus to plain sign-ups** (only after step 4 works). On /admin/researchers choose "Invited researchers", or run:

   `UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();`

   To reopen, set the mode back to signed_in.
6. **Rollback.** At the head of the C7 file. The site needs no rollback: without C7 it behaves as before.
"""

EP = """

## Addendum 2026-10-08 (17) (DOCS27_2026_10_08)

| # | Item | State |
|---|---|---|
| L1 | The desk's library on the site | Applied: C6 in the DB; automaton 5113170a; Srangam f9fbde31 |
| A1 | Roles: super admin, invited researchers, audit log (C7a, C7, RBAC_RESEARCHERS_2026_10_08) | Built and tested (14 PG, 26 vitest). To apply: C7a alone, C7, the Srangam patch, push, Publish |
| A2 | Close the corpus to plain sign-ups (mode 'readers') | After the first researcher has accepted: one switch on /admin/researchers |
| A3 | Automatic invitation email | Next: edge function (service role or Resend); needs the /invite/* redirect allowed and a sending domain |
| A4 | Researchers' requests (corrections, texts) | With L4: the request queue the desk pulls |
| V10 | The 10 withheld verses | In progress: markandeya_purana passage_count 1,219, published; the remaining --only files to paste |
"""

MIRROR = """

## Researchers (C7, DOCS27_2026_10_08)

- **Who reads, by mode.** `corpus_reader_allowed()` now reads:
  - mode 'signed_in': anyone signed in;
  - mode 'readers': researchers (role 'researcher', by invitation), users on corpus.readers, admins and the super admin;
  - mode 'admins': admins and the super admin.
- **Signed out.** No one reads while signed out.
- **Setting the mode.** The super admin sets it on /admin/researchers (`corpus_access_mode_set`), and every change goes to rbac.audit.
- **Researchers and stories.** Researchers see approved stories, like any reader. Drafts and candidates stay for admins (C6).
- **No change to the mirror run.**
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
        if b"DOCS26_2026_10_08" not in raw:
            print("REFUSE: %s has no DOCS26_2026_10_08 section (run patch_docs26 first). Nothing written." % p); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs27_" + stamp))
        t = p.with_name(p.name + ".tmp_docs27"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
