# The Researchers' Corner (2026-10-09)

Marker: CORNER_C9_2026_10_09. With the Corner, invited researchers, admins and the super admin can ask the desk for new stories, pictures and graphic novels from the site. They can also put approved stories together into anthologies and publish them to the working corpus's readers.

Generation stays on the desk, in the scripts that already make, check and meter it. The site only asks, and an editor decides. This is the R1-R3 and M2 of `docs/MEDIA_AND_CORNER_2026-10-09.md`.

## 1. What a researcher can do now

The example is Kanika, invited as a researcher.

| She wants | On the site | What the desk runs | Cost (estimate) |
|---|---|---|---|
| A story from passages she chooses | Corner → Ask the desk → "A story from passages you choose": text, from 25.7 to 25.14, a working title, why | A candidate over those passages, then `stories.py write --id N --yes` | about $0.01 |
| The desk to find episodes in a text | "Find episodes in a text": text, at most N | `stories.py mine --doc X --max N --yes` | $0.01 per 150 translated passages |
| A proposed episode written | "Write a proposed episode", or "Write it" under the story | `stories.py write --id N --yes` | about $0.01 |
| A picture for a passage | "A picture for a passage": passage, title, what the picture should show | Her idea stored as a brief, then `images.py approve-brief` and `images.py generate --doc X --id ID --yes` | about $0.10 |
| A picture for a story | "Illustrate" under the story | `stories.py illustrate --id N --yes`, then the same two steps | about $0.11 |
| A picture drawn again | "Draw again" under the picture | `images.py regenerate ID --yes` | about $0.10 |
| A graphic novel from an approved story | "Plan a graphic novel" (pages 8-16; young, teen or general readers) | `novel.py plan --story N --pages P --audience A --yes` | about $0.02 |
| Its cast, then its pages | "Draw the cast", "Draw the pages" (or one page) under the novel | `novel.py cast --id K --yes`, `novel.py draw --id K [--pages ...] --yes` | about $0.40; about $0.10 a page |
| An anthology across texts | Corner → Anthologies → New: title, introduction, readers, approved stories in her order | Nothing on the desk: the site composes it from the mirror | free |
| A printed copy or a PDF | "Print or save as PDF" on the anthology | the browser's print | free |

**How a request moves.**
1. A researcher's paid request is created as "waiting for an editor". The editor sees it in Corner → Queue, with the estimate and her note, and approves or rejects it.
2. Once approved, the desk takes it on its next round. The round is every ten minutes while the PC is on, through the task SanskritCornerWorker.
3. The desk runs the script, then sends the text on at once with `corpus_sync.py --doc` and `corpus_media.py --doc`. It reports what it made and what it cost on the desk's ledger.
4. Kanika sees the result under My requests: the draft story's opening, its check against the citations, and links.
5. An editor approves it, from the story's own page ("Approve") or from the desk. Readers then see it.

**What editors do.** An editor's own request (admin or super admin) is approved at once, within the day's cap. Editors also decide from the site, and the desk carries each decision out:
- approve or retire a story;
- approve or retire a picture;
- approve a novel page;
- approve or retire a novel.

**Publishing.** An editor publishes an anthology once every story in it is approved. It is then listed for every reader of the working corpus, and anyone who can open it can print it.

This is publishing *under the Nartiang corpus*, inside the signed-in corpus. A public page, outside sign-in, is phase P2 in section 6; it is not done.

## 2. The parts

| Part | File | Tests |
|---|---|---|
| Database | `docs/cloud/C9_researchers_corner_2026-10-09.sql`, one paste. Schema `corner`: kinds, settings, requests, collections, collection_items, worker, events. 12 functions for the site, 4 for the desk | `tests/test_corner_pg_2026_10_09.py` (7) |
| Checks | `docs/cloud/C9_checks_2026-10-09.sql`: P1-P2, V1-V4, D1-D6 | each run against the test database |
| Edge function | `docs/cloud/C9_corpus-desk/` (`index.ts`, `lib.ts`), deployed as `corpus-desk`. POST from the desk only, signed with `CORPUS_SYNC_SECRET` as `corpus-ingest` and `corpus-media` are. Actions: hello, state, pull, report, heartbeat | `deno test`: 9 + 10 |
| Desk worker | `scripts/corner_worker.py`: `--hello`, the state, `--apply --max N`. One run at a time (`data\corner_worker.lock`). Log `data\corner_worker_log.jsonl`; a request's rows in `data\corner_worker_made.jsonl`, so a retried request does not make them twice | `tests/test_corner_worker_2026_10_09.py` (10, one against PostgreSQL) |
| Schedule | `scripts\corner_task.ps1`, the task SanskritCornerWorker every 10 minutes. It keeps the PC awake while it works and logs to `D:\backups\corner_worker_log.txt` | parsed with PowerShell |
| Site | `docs/srangam/CORNER_C9_2026-10-09/`, put in by `scripts/patch_srangam_corner_2026_10_09.py`: `/corpus/corner`, `/corpus/anthologies/new`, `/corpus/anthologies/:id`, the "Ask the desk" bar under stories, pictures and novels, the Corner tab | `src/__tests__/corpus-corner.test.tsx` (20) |

## 3. Money

- **The day's cap.** $2.00 a day, in India time, for all Corner requests together. The site will not approve a request past it.
  - Each request counts its estimate, then the desk's measured cost once it has run.
  - The super admin changes the cap in Corner → Settings (0 to 50).
- **The desk's own cap** (cost_tracker, `set_budget.py`) still gates every paid call. The worker refuses a paid request the remaining cap cannot cover, before any call, and says so in the request.
- **The estimates** are in `corner.kinds` and follow the desk's prices:
  - gemini-2.5-flash text: about $0.01 a call;
  - gemini-3.1-flash-image: about $0.091 a picture at 1K.

  The cost actually reported is summed from the desk's `usage_log` for that text while the request ran.
- **The spend gate.** A researcher's paid requests wait for an editor (`researchers_need_approval`, true). At most 20 may wait per person.

## 4. Switching it on, and keeping it running

The commands are in the reply of 2026-10-09 and in RUNBOOK ("The Researchers' Corner").
1. **Back up.** `python scripts\db_backup.py`.
2. **SQL editor.** C9 checks P1-P2, then C9 in one paste, then V1-V4.
3. **Srangam.**
   - `patch_srangam_corner_2026_10_09.py --check`, then without `--check`.
   - Typecheck, tests and build.
   - Commit the listed paths and push.
4. **Lovable.** Ask Lovable to deploy `corpus-desk` without changing its code, then Publish.
5. **The desk.**
   - `python scripts\corner_worker.py --hello`.
   - Register SanskritCornerWorker.
   - `Start-ScheduledTask -TaskName SanskritCornerWorker`.
6. **The first request.** Ask for one story from passages yourself as super admin. The next round writes it. Approve it from the story page; the round after carries the approval.

**When something is wrong.**

| Seen | Meaning | Do |
|---|---|---|
| "Desk last seen: never" or more than 30 minutes ago | The worker is not running: the PC is off or asleep, or the task is not registered | `Get-ScheduledTaskInfo SanskritCornerWorker`; the tail of `D:\backups\corner_worker_log.txt` |
| `--hello`: HTTP 404 | `corpus-desk` is not deployed | Step 4 |
| HTTP 422 `corner_desk_... Could not find` | C9 is not applied | Step 2 |
| A request "failed: the desk's spend cap ..." | The desk's own cap is reached | `set_budget.py --cap N --unpause` on the desk, then ask again |
| "Today's cap for the Corner is $2.00 ..." | The day's cap is reached | Wait until tomorrow (India time), or the super admin raises it |
| A request stays "the desk is working on it" for hours | The run was cut off (sleep, shutdown) | Nothing to do. After 3 hours it is taken again, and after 3 attempts it is failed |

## 5. Security

- **The desk.** It runs only the fixed list of request kinds.
  - Every parameter is checked twice: by the database (`corner._clean`) and by the worker against `context.db`.
  - Scripts get an argument list (no shell).
  - Only numbers, passage references and the documented flags reach a command line. A title, a brief or a reason is stored as data; a test checks that the brief never appears in any command.
- **Signing.** The desk talks only to `corpus-desk`, signed with the existing secret. The function never sees a user's token, and the service role stays in Supabase.
- **The schema.** `corner` is closed: RLS is on, there are no grants, and everything goes through the 16 SECURITY DEFINER functions.
  - Researchers see only their own requests.
  - Editors see everyone's, with the email of the person who asked.
  - Only the super admin changes the settings.
- **Results.** They arrive as drafts. Approval is a person's decision, on the site or at the desk.

## 6. Not yet (the next phases)

| Phase | What | Why not now |
|---|---|---|
| R5 | Young-reader and teen versions of a story (`stories.py retell`) | The versions (`doc_story_variants`) are not mirrored yet. That is a C4 addition, `variants`, with a reader view |
| P2 | A public page for a published anthology, outside sign-in, on srangam.nartiang.org | The pictures would need a public path: a public rendition, or a signed link per published picture. Making anything public is a decision for you |
| B1 | The desk's typeset books (`stories.py book`, Booksmith PDFs, `novel.py build`) on the site | The files run to tens of MB (pictures embedded), above one request's 6 MB. It needs chunked uploads to Drive. Until then the site's own print does the job |
| R6 | Notifications (an email when a request is done) | Optional. It needs a mail provider decision |


## 7. Live, and what the Corner does not do yet (DOCS32_2026_10_09)

**Live on 2026-10-09.**
- C9 is applied and `corpus-desk` deployed.
- SanskritCornerWorker comes every 10 minutes; the Corner's status strip shows when.
- The checks are in PLATFORM section 35.

**A correction to C9's check V2.** service_role may call all 16 functions, not only the 4 for the desk. The reason is Supabase's default privileges. It is harmless: the 12 for the site refuse any caller without a signed-in user.

**The desk's own pages do more than the Corner does now** (phase C10). From `scripts/stories_web.py`, `scripts/images_web.py`, `stories.py`, `images.py` and `novel.py`:

| On the desk | In the Corner | Plan |
|---|---|---|
| Edit a story by hand: title, English, Hindi. It is checked again and goes back to draft | No | C10 `story_edit` (free) |
| Check a story against its citations again (`stories.py verify`, no model call) | No | C10 `story_verify` (free) |
| Edit a picture's title, brief, captions, passage or licence (`images.py edit`) | No | C10 `picture_edit` (free) |
| Picture ideas for a text from the model (`images.py brief --doc --max N`) | No; only the researcher's own brief | C10 `picture_ideas` |
| A cover for a text (`images.py cover`) | No | C10 `picture_cover` |
| Edit a novel page's scene or captions; its picture is then marked to draw again | No | C10 `novel_page_edit` (free) |
| Draw a novel's pages or cast again (`--redo`) | No: only pages not yet drawn | C10: "draw again" on `novel_draw` and `novel_cast` |
| Restore a retired picture | No | C10 |
| Young and teen versions (`retell`, `variant`) | No | R5 |
| Typeset books, Booksmith PDFs, the novel print build | No (the site prints anthologies itself) | B1 |
| Upload edition plates and photos (`images.py add`) | No | With B1 |
| Duplicate pictures (`images.py dedupe`) | No | Stays on the desk |

**The guardrail is unchanged.** Edited text travels as data, through the desk's own Python functions, never on a command line.


## 8. The Corner as it happens; Learn (DOCS33_2026_10_09)

**The first round trip (9 Oct).** Request #1 (story_mine, Markandeya) took 1 min 30 s from the ask to done. Its 6 proposed episodes appeared at once under "Write a proposed episode".

**State (C10a, worker 1.1, the site).**
- The desk tells the site each step of a request. The site shows:
  - the stages with their times and the step;
  - when the next round is due;
  - what to do next.
- Editors see the mirror's and the pictures' last run, both on the strip and on the Sync tab.

**Learn (C11, the site).** `/corpus/learn` teaches every tool with 23 quests. The Corner's quests are checked from its own records, and a quest never starts a paid request.

The design, the rules and the order to switch it on are in `docs/RESEARCHER_EXPERIENCE_2026-10-09.md`.


## 9. The Corner level with the desk; email (DOCS35_2026_10_09)

**New kinds (C10b, worker 1.2), with their estimates:**
- **Free:** "Edit" (a story's titles, English, Hindi), "Check again", "Edit words" (a picture's title, captions and context; the licence for editors), "Edit page" (a novel page's scene and captions), "Restore" (editors, a retired picture).
- **Paid:** "Ideas for pictures in a text" ($0.02), "An idea for a cover" ($0.01), "Draw this idea" ($0.10), "Draw the cast again" ($0.40), "Draw every page again" ($0.10 a page).

**The rules:**
- A researcher never changes an approved story, picture or novel.
- A proposed episode changes only its titles.
- Ideas are not mirrored: they come back in the request's result, and `corner_ideas` lists them for the text.

**Email (C12, corner-mail):** off until the super admin turns it on.
- **Researchers:** email when a paid request is done, when one fails, or when one is not approved.
- **Editors:** email when a researcher's request waits.
- **Invitations** can be sent from nartiang.org.
- Everyone can turn their emails off in Corner -> Settings.

The design, the DNS review and the order are in `docs/CORNER_C10_MAIL_2026-10-09.md`.


## 10. How researchers find the corpus, the Corner and Learn (DOCS36_2026_10_10)

**Signed in as a researcher, an admin or the super admin:**
- the header has a "Corpus" menu: Library, Stories, Names, Pictures, Graphic novels, Researchers' Corner, Learn, Published texts;
- on a phone, the menu sheet has the same section and the bottom bar a "Corpus" tab;
- admins also find Library, Corner and Learn in the admin sidebar.

**Signed out,** the header offers "Sign in". After signing in, an admin goes to the admin pages and anyone else to the corpus.

The database still decides who reads: the menus only follow it.
