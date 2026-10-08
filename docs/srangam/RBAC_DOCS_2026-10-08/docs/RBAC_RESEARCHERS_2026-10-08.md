# Roles and research invitations (RBAC_RESEARCHERS_2026_10_08)

The site's roles, who may do what, and how a fellow researcher is invited to read the working
corpus. The database decides everything. The pages only show what it allows.

The SQL is in the automaton repository. It is applied in the Lovable Cloud SQL editor, as S1-S4
were: no file is added to `supabase/migrations` and no history row is written.

- `docs/cloud/C7_checks_2026-10-08.sql`: read-only checks, one query per paste (P1-P7 before, V0 after C7a, V1-V7 after C7);
- `docs/cloud/C7a_rbac_roles_2026-10-08.sql`: two enum values, pasted ALONE;
- `docs/cloud/C7_rbac_researchers_2026-10-08.sql`: everything else, one transaction, in one paste.

The order is P1-P7, C7a alone, V0, C7, V1-V7. The editor runs one paste as one transaction, and
PostgreSQL will not read a new enum value in the transaction that added it (55P04). So nothing
else may share C7a's paste, not even a `SELECT enum_range(...)`. A first attempt on 2026-10-08
(21:14) did exactly that and was rolled back whole; C7's guard then refused to run. Nothing changed.

Before C7 the site behaves exactly as before: `my_roles()` does not exist, the roles follow
`has_role`, and the new pages say that C7 is not applied.

## The roles

| Role | Who | May |
|---|---|---|
| `super_admin` | dhruv.rakesh@gmail.com | invite and remove researchers; choose who may read the corpus; read the audit log; the only role that may write `user_roles` from the site. Also holds `admin`. |
| `admin` | editors | the admin pages; drafts and candidates among the stories; always read the corpus (signed in) |
| `researcher` | invited fellow researchers | read the working corpus (Shelf, Stories, Names, search) in the modes `signed_in` and `readers` |
| `moderator`, `user` | unused | nothing beyond a signed-in user |

Roles live in `public.user_roles` and are checked with `public.has_role()`. The site asks two
SECURITY DEFINER functions:

- `has_role(uid, 'admin')`, as before;
- `my_roles()`, the caller's own roles and no one else's (C7).

Before C7 is applied, `my_roles()` does not exist. The roles then follow `has_role` alone, and the
site behaves as it did.

## Who may read the working corpus

`corpus.reader_access.mode`. The super admin sets it on `/admin/researchers`.

| Mode | Who reads |
|---|---|
| `signed_in` (as installed) | anyone signed in (the sign-up page is open) |
| `readers` | researchers, anyone on the older list `corpus.readers`, admins, the super admin |
| `admins` | admins and the super admin only |

Nobody reads while signed out, in any mode.

## Inviting a researcher

1. **Create the invitation.** On `/admin/researchers`, the super admin enters an email address, an optional private note, and how long the link stays valid (7 to 90 days). They press **Create invitation**.
2. **Copy the link.** The page shows the link once: `https://<site>/invite/<64 hex characters>`. The database keeps only its SHA-256 hash, so a lost link cannot be shown again. The super admin can:
   - press **Copy link**; or
   - press **Email it**, which opens their own email program with the text filled in.

   Nothing is sent from the site.
3. **Sign in.** The researcher opens the link. They sign in, or create an account, with the invited address. Any confirmation email brings them back to the invitation.
4. **Accept.** They press **Accept the invitation**. The database:
   - checks that the account's email is the invited one and is confirmed;
   - checks that the link is still open;
   - then adds the role `researcher`.

A few rules apply to links:

- A link works once, for one address.
- Inviting the same address again voids the old link.
- The super admin can withdraw an invitation that has not yet been accepted.

## Removing a researcher

On **People with access**, use **Remove**. The account stays. Only the role `researcher` goes.

## The audit log

`rbac.audit` records every invitation, re-issue, withdrawal and acceptance, every change of the mode, and every change to `user_roles`. The last kind is recorded by a trigger, so a role granted in the SQL editor is logged too, with no actor. The super admin reads the log on `/admin/researchers`.

## Where it is in the code

| Path | What |
|---|---|
| `src/lib/rbac.ts` | the calls and the shared rules (links, the email text, what each answer means) |
| `src/pages/admin/Researchers.tsx` | `/admin/researchers` |
| `src/pages/InviteAccept.tsx` | `/invite/:token` |
| `src/contexts/AuthContext.tsx` | `roles`, `isSuperAdmin`, `isResearcher`, `refreshRoles`; `signUp(email, password, redirectPath)` |
| `src/pages/Auth.tsx` | `?next=/invite/...` and `?tab=signup` |
| `src/components/admin/AdminLayout.tsx` | the Researchers link (super admin only), the Super admin badge |
| `src/components/corpus/CorpusGate.tsx` | the refusal tells a signed-in reader how researchers get in |
| `src/__tests__/rbac-auth.test.tsx`, `src/__tests__/rbac-pages.test.tsx` | 26 tests |

## Not done here (next)

- **Automatic invitation email.** An edge function could do this with the service role (`auth.admin.inviteUserByEmail`), or with an email provider such as Resend. That needs:
  - the site's `/invite/*` path allowed as a redirect URL in Lovable Cloud's auth settings;
  - a sending domain.
- **Researchers' own requests.** Requests such as "propose a correction" or "request a text" would go through a queue that the desk pulls.
