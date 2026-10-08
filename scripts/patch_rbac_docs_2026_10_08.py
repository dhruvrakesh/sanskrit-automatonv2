#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_rbac_docs_2026_10_08.py  (2026-10-08)  RBAC_DOCS_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main, after RBAC_RESEARCHERS_2026_10_08, which is
Srangam 4d70389f). Documentation only; no code changes:
  - docs/RBAC_RESEARCHERS_2026-10-08.md: the order in which the SQL is applied (checks P1-P7, C7a
    ALONE, V0, C7, V1-V7), why C7a shares its paste with nothing (55P04), what the first attempt at
    21:14 did (rolled back whole, nothing changed), and that the site behaves as before until C7.
    Replaced only over the version RBAC_RESEARCHERS_2026_10_08 wrote (md5, line endings ignored).
  - docs/RELIABILITY_AUDIT.md: Phase X appended (the roles, the user_roles policy, the RPCs callable
    by anon and authenticated under Invariant 15, invariants 23-26). Marker-idempotent, its line
    endings kept.
All-or-nothing: everything is checked before anything is written. Backups .bak_rbacdocs_<date>.
Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_docs_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_docs_2026_10_08.py"
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "RBAC_DOCS_2026_10_08"
ROLE_MARK = "RBAC_RESEARCHERS_2026_10_08"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "RBAC_DOCS_2026-10-08"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces)
FILES = [
    ('docs/RBAC_RESEARCHERS_2026-10-08.md', '3e9cb3fb79131824b50f3dcb59159e02', '1523911bc9f148fc906f5288743ed4d1'),
]

D = "\u2014"   # the em dash RELIABILITY_AUDIT.md uses in its headings
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_TEXT = """

---

## Phase X """ + D + """ Roles: a super admin and invited researchers (""" + ROLE_MARK + """, """ + MARK + """, 2026-10-08)

The SQL is in the automaton repository: `docs/cloud/C7a_rbac_roles_2026-10-08.sql`,
`docs/cloud/C7_rbac_researchers_2026-10-08.sql`, and the checks in `docs/cloud/C7_checks_2026-10-08.sql`.
It is applied through the Lovable Cloud SQL editor, as S1-S4 were: no file in supabase/migrations,
no history row. What follows holds once C7 is applied. Before it, the site behaves as in Phase N
(`my_roles()` is missing, roles follow `has_role`, the new pages say C7 is not applied).

### X.1 """ + D + """ Roles
- `app_role` gains `super_admin` and `researcher` (C7a, in its own paste: PostgreSQL will not use a new
  enum value in the transaction that added it).
- `super_admin` is held by one account, always alongside `admin`, so every `has_role(auth.uid(),'admin')`
  policy and every `requireAdmin()` edge gate treats it exactly as before.
- `researcher` reads the working corpus in the modes `signed_in` and `readers` (`corpus_reader_allowed()`),
  and gains nothing else.

### X.2 """ + D + """ Who writes roles
- `"Only admins can manage roles"` (FOR ALL) is replaced by `"Only super admins can manage roles"`.
  `"Admins can view all roles"` (SELECT) stays. No site code writes `user_roles`.
- A trigger records every insert, update and delete on `user_roles` in `rbac.audit`, including changes
  made in the SQL editor (with no actor).

### X.3 """ + D + """ Invitations
- `rbac.invites` (schema `rbac`, not exposed; RLS on, no policies, no grants) keeps only the SHA-256 of
  each link token. One open invitation per email; a new one voids the old.
- Accepting needs the signed-in account's email to equal the invited one and to be confirmed (email
  verification is required, M.3), and the link to be open (not accepted, withdrawn or expired).

### X.4 """ + D + """ RPCs (Invariant 15)
- `anon`: `research_invite_peek` only (status, a masked email, the expiry; never the email itself).
- `authenticated`: `my_roles` (the caller's own roles only, so no enumeration, M.2), `is_super_admin`,
  `research_invite_accept`, and, each re-checking the caller for `super_admin`: `research_invite_create`,
  `research_invites_list`, `research_invite_revoke`, `rbac_members_list`, `researcher_remove`,
  `rbac_audit_list`, `corpus_access_mode`, `corpus_access_mode_set`.
- All SECURITY DEFINER with `SET search_path = ''`.

### Accepted (by design)
- `rbac.invites` and `rbac.audit` have RLS enabled and no policies: they are read only through the
  functions above, as the `corpus` schema is.

### Invariants added (Phase X)
23. Only `super_admin` writes `user_roles` from the site; the super admin also holds `admin`.
24. Invitation tokens are stored only as SHA-256; a link works once, for one confirmed address, until it expires.
25. The only RBAC function callable by `anon` is `research_invite_peek`.
26. Every change to `user_roles` is recorded in `rbac.audit`.
"""


def md5_lf(b: bytes) -> str:
    return hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest()


def nl_of(raw: bytes) -> bytes:
    return b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else b"\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    if not PAYLOAD.is_dir():
        print("FAIL: the payload folder is missing: %s" % PAYLOAD); return 2
    if not Path("src/lib/rbac.ts").exists():
        print("REFUSE: RBAC_RESEARCHERS_2026_10_08 is not applied (src/lib/rbac.ts is missing)."); return 1
    problems, todo, skip = [], [], []
    for rel, want, old in FILES:
        src = PAYLOAD / rel
        if not src.exists():
            problems.append("payload file missing: %s" % rel); continue
        data = src.read_bytes()
        if hashlib.md5(data).hexdigest() != want:
            problems.append("payload file differs from the one released: %s" % rel); continue
        dest = Path(rel)
        if not dest.exists():
            problems.append("%s not found (RBAC_RESEARCHERS_2026_10_08 writes it)" % rel); continue
        raw = dest.read_bytes()
        have = md5_lf(raw)
        if have == want:
            skip.append(rel); continue
        if have != old:
            problems.append("%s has changed since RBAC_RESEARCHERS_2026_10_08 (md5 %s, expected %s)" % (rel, have, old)); continue
        if nl_of(raw) == b"\r\n":
            data = data.replace(b"\n", b"\r\n")
        todo.append((dest, data))

    audit = Path(AUDIT)
    if not audit.exists():
        problems.append("%s not found" % AUDIT)
    else:
        araw = audit.read_bytes()
        if MARK.encode() in araw:
            skip.append(AUDIT)
        elif b"## Phase X " in araw:
            problems.append("%s already has a Phase X section that is not this one (left alone)" % AUDIT)
        else:
            anl = nl_of(araw)
            sep = b"" if araw.endswith(b"\n") else anl
            todo.append((audit, araw + sep + AUDIT_TEXT.replace("\n", anl.decode()).encode("utf-8")))

    for rel in skip:
        print("skip %s (already this version)" % rel)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do."); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    try:
        for dest, data in todo:
            bak = dest.with_name(dest.name + ".bak_rbacdocs_" + stamp)
            shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_rbacdocs")
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            done.append((dest, bak))
            print("updated %s" % dest.as_posix())
    except Exception as e:
        print("FAIL while writing: %s: %s. Restoring." % (type(e).__name__, e))
        for dest, bak in done:
            shutil.copy2(bak, dest)
            print("restored %s" % dest)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
