
## Phase AA — Fewer questions per page (LOAD_L1_2026_10_09, 2026-10-09)

Seen on the live site on 2026-10-09: every page asked `has_role` and `my_roles` three times each within a
few milliseconds (the auth listener and `getSession()` each started the same check), and the Pictures page
asked `corpus_reader_media` twice for the same rows (the text buttons' index and the list).

### AA.1 — What changed
- `AuthContext`: one role check per user at a time. Calls that arrive while it is on its way share its
  answer; `refreshRoles()` (after accepting an invitation) always asks anew; signing out forgets it.
  Later events (a token refresh, signing in again) still ask again, so a role changed since is seen.
- `/corpus/images`: with no text chosen, the list is the first rows of the index (the same function and
  order), so the database is asked once; a chosen text is asked for itself, as before.

### Invariants added (Phase AA)
34. At most one role question per signed-in user is on its way at any time; `refreshRoles` always asks.
35. The Pictures page asks `corpus_reader_media` once when no text is chosen.
