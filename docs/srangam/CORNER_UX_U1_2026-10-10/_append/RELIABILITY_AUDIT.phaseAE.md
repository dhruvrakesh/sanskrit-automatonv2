## Phase AE - The Corner, guided (CORNER_UX_U1_2026_10_10, 2026-10-10)

Ask the desk was a wall of eleven forms under one list of texts, all shown before a text was chosen
(each saying "Choose a text first."). Passages had to be typed as numbers (25.2), and the forms'
placeholders looked like values already filled in. The Reply-to field of the email settings showed
desk@nartiang.org as its placeholder: it looked saved, and nartiang.org receives no mail.

### AE.1 - What Ask the desk does now
- **The offering so far** (one quiet line): texts in English, passages translated, stories told,
  pictures, graphic novels, anthologies published, requests done this week (from `corner_offering()`
  once the database has it, docs/cloud/C13 in the automaton repo; before that, from the texts alone),
  and how many texts wait for their first story (from the texts, as the list counts them). No names
  and no ranks.
- **Before a text is chosen:** no forms. "Where to begin": the texts with English and no story yet
  (the most English first), the text chosen last time on this browser (offered, never chosen for the
  researcher), and "Surprise me". The list of texts is grouped: waiting for their first story, with
  stories.
- **After:** what the text has (Hindi, stories by status, pictures, graphic novels; links to read it,
  its stories, its pictures); "What would you like to make?" (a story, a picture, a graphic novel,
  everything; `?goal=`, or the goal of `?kind=`); and "Ready in this text": what can be asked for now
  (find its episodes, write a proposed episode, a picture for a story without one, a graphic novel of an
  approved story without one, ideas for its first pictures), at most four, each with its estimate and
  "Set it up". "Find its episodes" only when the text has no story of any status. The picture, novel and
  ideas suggestions only for a viewer shown the work in progress (an editor; a researcher once C13 is
  in), since otherwise "none" may only mean "none approved yet".
- **What to make** hides the other goals' forms without unmounting them: a note typed, or a request's
  answer, is still there when its goal is shown again.
- **Set it up** only fills the form, goes to it and puts the cursor in it. Every request is still made
  by its own form's button, at the estimate the form shows.
- **Passages chosen in the text:** "Choose them in the text" (a story) and "Choose it in the text" (a
  picture) open the text a reader page at a time (`corpus_reader_page`, the reader's own query), each
  passage with its reference and first English words. "From here", "To here", "This one" fill the
  reference; only a passage the desk takes can be chosen (translated, and not a running head or front
  matter, as corner._passage_ok); the range's length is shown, and more than 60 is flagged before the
  desk is asked. A picture's brief starts from the passage's English, and follows the passage chosen
  until the researcher writes in it. Choosing another text clears the passages chosen. The picker is
  its own chunk, loaded when first opened.
- **After a request:** a line pointing to Learn, where it counts. An empty My requests points there too.
- **Email settings:** Reply-to's placeholder is "an inbox you read", and its hint says why an address at
  nartiang.org loses every reply (no MX record). The site's address placeholder says "such as".
- **Anthologies:** a researcher's anthology editor offers approved stories only, as
  `corner_collection_save` accepts from her (once C13 shows her drafts, they are still not offered
  there). Editors see drafts too, as before.

### AE.2 - Load
- The Corner's chunk: 54,421 to 71,330 bytes (21.2 kB gzip), measured with vite build. The picker is a
  separate 5,333-byte chunk. The entry is unchanged (565,270 bytes).
- No question to the database on page load beyond what the Corner asked before, except
  `corner_offering()` (one row, once per five minutes).

### Invariants added (Phase AE)
47. Nothing in the guide asks the desk for anything: suggestions, "Set it up", the passage picker and
    "Surprise me" only fill forms or choose a text. A request is made only by a form's "Ask the desk".
48. The guide shows only what the database returns to this viewer and offers a kind only when
    `corner_kinds()` lets this viewer ask for it; the database still checks every request.
49. What is remembered is remembered on this browser only (the last text), every read and write of it
    guarded; a private window or blocked storage changes nothing but the "Continue with" button.
