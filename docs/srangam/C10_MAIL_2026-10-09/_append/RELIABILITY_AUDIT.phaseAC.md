
## Phase AC — The Corner level with the desk; email from nartiang.org (CORNER_C10_MAIL_2026_10_09, 2026-10-09)

The SQL is in the automaton repository: `docs/cloud/C10b_corner_kinds_2026-10-09.sql` (eight kinds of
request, `corner_ideas`, `corner_retired_pictures`) and `docs/cloud/C12_corner_mail_2026-10-09.sql` (the
outbox, each person's choice, `corner_mail_*`), each with its checks. The edge function
`supabase/functions/corner-mail` is `docs/cloud/E1_corner-mail` (index.ts, lib.ts), copied in unchanged.

### AC.1 — What the site may do
- Ask the desk, as requests like any other (`corner_request_create`, checked by `corner._clean` and again
  by the desk): edit a story, a picture's words or a graphic novel's page (only the fields that changed),
  check a story again, ideas for pictures or a cover, draw one of those ideas, draw a novel's cast or every
  page again (`redo`), and, as an editor, restore a retired picture.
- Read the ideas the desk proposed for a text (`corner_ideas`) and, as an editor, a text's retired pictures
  (`corner_retired_pictures`).
- Read and set one's own email choice (`corner_mail_prefs`, `corner_mail_prefs_set`); editors read the
  queue (`corner_mail_state`); the super admin turns email on or off and sets From, Reply-to and the
  site's address (`corner_settings_set`), and queues an invitation's email right after making it
  (`corner_mail_invite`: the token is in the page's memory only, as before; the mailto path stays).
- Ask `corner-mail` to send what is waiting (`{action: 'flush'}` with the person's own JWT) after a
  request or an editor's decision. It answers with counts only: the site never sees an address, a body
  or the Resend key.

### AC.2 — Load
- The edit forms are `DeskEdit.tsx`, loaded when Edit is clicked; the reading pages load the mail code
  only after a request is made. The Corner's new panels are `CornerPanels.tsx`, loaded when first shown.
- Measured (vite build): the entry and the story, picture and novel pages' own chunks within about
  0.1 kB of before; DeskActions 4.9 -> 6.9 kB and the Corner's shared chunk 16.0 -> 17.8 kB; CorpusCorner
  51.1 -> 54.4 kB (CornerPanels 15.3 kB and DeskEdit 3.9 kB load on first use).

### Invariants added (Phase AC)
40. Before C10b the pages offer none of its kinds (`corner_kinds()` must list a kind first); before C12
    no email control is shown anywhere.
41. An edit sends only the fields that changed; a researcher is never offered Edit on an approved story,
    picture, novel or page (and the database refuses it).
42. Sending the waiting emails is fire and forget: a missing or failing `corner-mail` never shows an
    error and never holds up a request.
43. An invitation's link reaches the outbox only through `corner_mail_invite`, called by the super admin
    with the token in hand; the database wipes the link once the email is sent or given up.
