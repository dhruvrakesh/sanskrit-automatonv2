# The researcher experience: state, learning, and the path after it (2026-10-09)

Markers:
- STATE_LEARN_2026_10_09, the release, which carries CORNER_STATE_C10A_2026_10_09 (the database and the desk), CORNER_STATE_S1_2026_10_09 (the site) and LEARN_T1_2026_10_09 (Learn).
- This plan follows `docs/RESEARCHERS_CORNER_2026-10-09.md` (C9) and `docs/SYNC_COMMANDS_2026-10-09.md`.

## 1. Why

On 9 Oct the Corner made its first round trip. Request #1 (find episodes in the Mārkaṇḍeya) went through:
- asked at 14:58:00 IST;
- taken by the desk at 14:58:18;
- done at 14:59:30, with 6 episodes proposed;
- cost $0.0341 against an estimate of $0.09.

The page could show only a status word: nothing about when the desk would come, how far it had got, or what to do next. Editors had no view of whether the mirror and the pictures were in step. That day the mirror stopped twice without anyone on the site knowing (PLATFORM section 36).

Researchers also had no guided way to learn the tools.

## 2. What this release adds

| Part | Where | What it does |
|---|---|---|
| C10a | `docs/cloud/C10a_corner_state_2026-10-09.sql`; checks `docs/cloud/C10a_checks_2026-10-09.sql` | `corner.requests.progress`; `corner_desk_report` keeps `started_at` and stores progress without overwriting the result, with one event per status change; `corner_request_track(ids)` for the site |
| Worker 1.1 | `docs/desk/CORNER_STATE_C10A_2026-10-09/corner_worker.py`, put in by `scripts/patch_corner_worker_state_2026_10_09.py` | Reports each step of a request ("Drawing page 3 of 12"), at most every 5 s, best effort (stops after one failed report); the heartbeat carries the mirror's and the pictures' last run |
| C11 | `docs/cloud/C11_learn_2026-10-09.sql`; checks `docs/cloud/C11_checks_2026-10-09.sql` | Schema `learn` (closed): 23 quests, marks; `learn_me`, `learn_summary`, `learn_mark`, `learn_team` |
| Site | `docs/srangam/STATE_LEARN_2026-10-09/`, put in by `scripts/patch_srangam_state_learn_2026_10_09.py` | The Corner as it happens (next round, stages, progress, next steps, live refresh, notices; editors: chips and a Sync tab); `/corpus/learn` with quests, XP, levels, badges, toolbox, how the desk works, the editors' Team panel |

**Tests:**
- Database: `tests/test_corner_state_pg_2026_10_09.py` (16, including the 7 of C9 on top of C10a) and `tests/test_learn_pg_2026_10_09.py` (9).
- Desk: `tests/test_corner_worker_state_2026_10_09.py` (22; the C9 worker test passes unchanged).
- Site: `corpus-corner-state.test.tsx` (22) and `corpus-learn.test.tsx` (13). The full site suite has 244 passing; only the 3 known environment-only failures remain.

### The order (it matters)
1. **C10a in the SQL editor, before the desk gets worker 1.1.** Otherwise C9's `corner_desk_report` would keep each progress report as the request's result.
2. **Worker 1.1** on the desk (`patch_corner_worker_state_2026_10_09.py`), then release.
3. **C11** in the SQL editor (independent of C10a).
4. **Srangam** (`patch_srangam_state_learn_2026_10_09.py`): tests, push (pull first), Publish.

A re-run of C9 would put C9's `corner_desk_report` back, so run C10a again after any re-run of C9.

## 3. Learn: the rules

- **Five tracks:**
  - Find your way (6 quests, self, 10 XP each);
  - Read what the desk made (4, self, 10);
  - Ask the desk (6, checked from the Corner, 20);
  - Make and publish (anthology 30, three stories 30, published 50, print 10);
  - For editors (3, checked, 20; editors only).
  - A researcher can earn 340 XP and an editor 400.
- **Levels:** Reader 0, Explorer 50, Storyteller 120, Curator 200, Keeper 280.
- **Badges:** one per finished track (Wayfinder, Close reader, Desk hand, Anthologist, Editor's hand).
- **Marking:** "self" quests are marked by the person after trying the tool. "Auto" quests are computed live from `corner.requests`, `corner.collections` and `corner.collection_items` and cannot be marked by hand.
- **No new costs:** a quest never starts a paid request. Researchers' paid requests still wait for an editor and count against the day's cap.
- **Privacy:** only editors see the team's progress (`learn_team`: email, roles, level, XP, quests done, last activity). There is no public leaderboard.

## 4. The path after this

| Phase | What | State |
|---|---|---|
| C10 | The Corner level with the desk's own pages (`stories_web.py`, `images_web.py`, `stories.py`, `images.py`, `novel.py`) | Next. See the list below |
| L2 | The first load: the entry chunk is 491 KB (173 KB gzip) on every first visit | Next: measure what the home and corpus pages load before changing any chunking |
| R5 | Young and teen versions on the site | Needs `doc_story_variants` in the mirror (a C4 addition) |
| B1 | The desk's typeset books and PDFs on the site | Needs chunked uploads to Drive; the site prints anthologies meanwhile |
| P2 | A public page for a published anthology | Your decision: its pictures would need a public path |
| R6 | Email when a request is done | Needs a mail provider decision |
| T2 | Learn, second round | Quests for C10's new kinds; optional reminders; quests that check the reader and search for you (needs a small, private event log) |

**C10 in full.** All of these travel as data through the desk's own Python functions, never on a command line.
- **Free kinds:**
  - `story_edit`: title, English and Hindi; the story is checked again and returns to draft.
  - `story_verify`: `stories.py verify`, no model call.
  - `picture_edit`: title, brief, captions, passage, licence.
  - `picture_restore`.
  - `novel_page_edit`: scene and captions; the picture is marked stale.
- **Paid kinds:**
  - `picture_ideas`: `images.py brief --doc --max N`.
  - `picture_cover`: `images.py cover`.
- **"Draw again":** a `redo` option on `novel_cast` and `novel_draw`.

## 5. How to see that it works

1. **SQL editor:**
   - C10a: V1 shows the column, V2 the grants, D1 the open requests with their progress.
   - C11: V1-V3, then D1 and D2 once people use Learn.
2. **The Corner:**
   - The strip says "Next round about HH:MM".
   - A new request shows its stages, and while it runs, "step i of n".
   - Editors see the Mirror, Pictures and Desk spend chips and the Sync tab.
3. **Learn:** a researcher sees 20 quests and an editor 23. Asking for a story turns "Ask the desk for anything" and "Ask for a story from passages you choose" done.
