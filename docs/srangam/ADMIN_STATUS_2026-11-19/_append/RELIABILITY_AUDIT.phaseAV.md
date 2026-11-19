## Phase AV - The desk and the site at a glance, for the super admin (ADMIN_STATUS_2026_11_19, 2026-11-19)

Asked on 19 Nov: "alot of the admin dashboard and landing pages need to be reimagined and rewired to reflect present
state of local and online deployment and linkages". Read that day: the admin pages read the articles' tables only
(srangam_articles, tags, cross-references, bibliography, pins); none said what the desk on the PC (the automaton) sends
to this site, when it last did, whether its worker is alive, who may read the working corpus, or which AI keys the
site's functions used, though all of it is in this database. The first step of the rewiring (the automaton's
docs/ADMIN_REWIRE_2026-11-19.md, A1) is one read-only page for the super admin.

### AV.1 - What changes
- src/pages/admin/DeskSite.tsx (new), at /admin/desk-site (src/App.tsx, lazy; the sidebar's "Desk and site", super
  admin only, src/components/admin/AdminLayout.tsx): the desk's worker (last seen, the Corner's queue); the library
  mirror (texts, withdrawn, passages and translations about, the last run); the genealogies sent (each index table's
  rows and when a row last changed); who may read (the setting, since, the readers listed, the roles); the AI calls of
  the last 7 days by provider and model, with a warning when a call went through anything but the own Gemini or OpenAI
  key, or failed. "As of" the time it was read; read again on Refresh or after 10 minutes. A late desk (30 minutes) or
  mirror (3 hours) is said plainly.
- One function, read-only, the super admin only: public.corpus_admin_status() (docs/cloud/C30_admin_status_2026-11-19.sql
  in the automaton repo).
- src/__tests__/desk-site.test.tsx: new.

### AV.2 - Not done, named
- The admin dashboard (/admin) and the sidebar's grouping, the home page's "Start here" and the Library's landing are
  the next steps (A2, A3 of the plan), each its own kit.
- The desk's own figures (the Claude credit, its jobs) stay on the desk; they are not sent to the site.

### Invariants added (Phase AV)
72. The admin's status of the desk and the site reads only: one function, the super admin only, nothing written; it
    says when it was read, and a late desk, a late mirror, a failed AI call or a call not through the own keys is said
    in words, never hidden.
