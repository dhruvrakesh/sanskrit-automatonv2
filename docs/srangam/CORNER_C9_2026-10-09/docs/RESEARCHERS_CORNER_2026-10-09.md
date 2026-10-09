# The Researchers' Corner (2026-10-09)

Marker: CORNER_C9_2026_10_09. Invited researchers, admins and the super admin ask the translation desk for stories, pictures and graphic novels from the site. They also make anthologies of the approved stories.

The site never generates anything itself. The desk (a PC) carries every request out with its own scripts, inside its own spend cap. Results come back through the mirror (C4) and the pictures (C8) as drafts until an editor approves them.

The design, the request kinds and the desk's commands are in the automaton repo: `docs/RESEARCHERS_CORNER_2026-10-09.md`.

## Pages

| Page | What it does |
|---|---|
| `/corpus/corner` | **Ask the desk.** Forms grouped as Stories, Pictures and Graphic novels, each with its estimate. Forms can be filled from a link, e.g. `?tab=ask&kind=novel_plan&doc=nilamata_seg&story_id=36`. **My requests.** Status, the desk's answer, a draft story's opening and check, and links; a request can be withdrawn while it is waiting. **Queue** (editors). Approve or reject, with a note, plus recent history. **Anthologies.** **Settings** (super admin). The day's cap, whether researchers' paid requests wait, and how many may wait per person. **Status strip.** When the desk last came, what is queued, and for editors today's spend against the cap. |
| `/corpus/anthologies/new`, `/corpus/anthologies/:id` | **Builder.** A title in English and Hindi, an introduction, the readers, and approved stories from any text in any order. **Reader.** Each story with its picture, the Sanskrit line, English and/or Hindi, and its passages as links. **Print or save as PDF.** **Editors.** Publish, unpublish, retire. |
| Under a story, a picture, a novel | **"Ask the desk" bar** (only for those who may ask). Write it, Illustrate (when the story has no picture), Plan a graphic novel, Draw again, Draw the cast, Draw the pages, Draw page N. **Editors.** Approve, retire, approve page N, approve the novel. Retire needs a second click. |

**Who sees what.** Readers who are not invited see a card on how to get in, and the published anthologies. Everyone else's pages are unchanged.

**Before C9.** The Corner says it is not available yet, and the bars do not appear.

## Code

- `src/lib/corner.ts`: loaders and actions, with the server's own messages kept, plus the shared rules.
- `src/components/corpus/CornerParts.tsx` and `src/components/corpus/DeskActions.tsx`.
- `src/pages/corpus/CorpusCorner.tsx` and `src/pages/corpus/CorpusAnthology.tsx`.
- `supabase/functions/corpus-desk/` (`index.ts`, `lib.ts`): the desk's door. POST only, signed with `CORPUS_SYNC_SECRET`; the browser never calls it. Its tests are in the automaton repo: `docs/cloud/C9_corpus-desk/`.
- `src/__tests__/corpus-corner.test.tsx`: 20 tests.

## Switching it on

1. Apply C9 in the Lovable Cloud SQL editor, with its checks before and after.
2. Push, then ask Lovable to deploy `corpus-desk` without changing its code. It needs no new secret.
3. On the desk, register the SanskritCornerWorker task.
4. Publish.
