## Phase AD - The working corpus in the navigation, by role (NAV_RBAC_2026_10_10, 2026-10-10)

Until now the header linked to the working corpus nowhere: a researcher reached it only through the
invitation page, the sign-in redirect or a typed address, and Learn only from the corpus's own tabs. The
header showed "Admin" to everyone, signed in or not.

### AD.1 - What the navigation shows
- **Signed out:** "Sign in" (`/auth`, which sends an admin on to the admin pages and anyone else to the
  corpus). No corpus link and no question to the database.
- **A researcher, an admin or the super admin** (the roles AuthContext already holds, no extra request):
  - the header's "Corpus" menu: Library, Stories, Names, Pictures, Graphic novels, Researchers' Corner,
    Learn, Published texts;
  - the same section in the phone's menu sheet;
  - a "Corpus" tab in the phone's bottom bar.
- **"Admin"** (header and menu sheet): admins and the super admin only.
- **A signed-in account with none of those roles** asks `corpus_reader_allowed()` once (kept ten
  minutes). This is how a reader list, or the 'signed_in' access mode, shows the menu.
- **The admin sidebar** has a "Working corpus" group: Library, Corner (ask the desk), Learn.
- **The corpus home** says where to start: Learn and the Researchers' Corner.

### AD.2 - Load
- `CorpusMenu.tsx` and `corpusAccess.ts` are in the entry (they decide what the header shows): +4.6 kB
  (+1.3 kB gzip), measured with vite build. Popover and Button were in the entry already.

### Invariants added (Phase AD)
44. The menus never decide who reads the corpus: every corpus page still asks the database, and a
    refusal is shown as before.
45. The corpus menu, tab and sheet section appear only when the account may read the corpus. They do
    not appear signed out, nor while the roles are still being read.
46. "Admin" appears only to admins and the super admin; "Sign in" only while signed out, once the
    session is read.
