# The researchers' side of the working corpus: state and learning (2026-10-09)

Markers: CORNER_STATE_S1_2026_10_09 (the Corner, as it happens) and LEARN_T1_2026_10_09 (Learn). The
SQL is in the automaton repository: `docs/cloud/C10a_corner_state_2026-10-09.sql` and
`docs/cloud/C11_learn_2026-10-09.sql`, each one paste in the Lovable Cloud SQL editor, with their
checks beside them. Until each is applied, the pages behave exactly as before and say so quietly.

## 1. The Corner, as it happens (`/corpus/corner`)

**The status strip** says when the desk was last seen and when its next round is due:
- "Next round about 15:48" means the desk came at 15:38 and comes every 10 minutes.
- "A round is due" means more than 2 minutes have passed that time.
- "The desk is away - last seen 15:02" means it was last seen more than 30 minutes ago.

Editors also see three chips, each linking to the Sync tab:
- the mirror, in step or stopped, with its error;
- the pictures on Drive, as files on Drive of files needed;
- the desk's spend left.

**Every request** shows its stages: Asked, Approved, Taken by the desk, Working, Done. Each reached stage shows its local time.
- Waiting for an editor, Rejected, Withdrawn and Failed are shown in words and colour.
- While the desk works, it shows its progress, such as "Drawing page 3 of 12", with a progress bar.
- A finished request offers its next steps, such as "Write one of the proposed episodes", "Ask for a picture of it" or "Draw the pages". Editors also see "Approve it".

**Live.** While any listed request is open, the lists refresh every 20 seconds and the desk's state every 60 seconds. When nothing is open, the lists stay as they are and the desk's state refreshes every 5 minutes. When a request finishes while the page is open, a line and a toast say so once.

**The Sync tab** (editors) has three cards: the desk, the mirror and the pictures. Each card shows the command to run on the desk when it is out of step.

**Where it comes from:**
- `corner_request_track(ids)` (C10a) gives the claim time and the progress.
- `corner_me().worker_info.sync` (desk worker 1.1) gives the mirror's and the pictures' last runs.

**The files:**
- `src/lib/cornerState.ts` and `src/components/corpus/CornerState.tsx` hold this work, and only `/corpus/corner` imports them.
- The parts that the story, picture and novel pages share stay small, in `corner.ts` and `CornerParts.tsx`.

## 2. Learn (`/corpus/learn`, the Learn tab)

**Quests.** There are 23 quests in five tracks:
- Find your way (6);
- Read what the desk made (4);
- Ask the desk (6);
- Make and publish (4);
- For editors (3, editors only).

**Marking.** Exploration quests are marked by the person ("I did this", after "Try it"). The Corner's quests are checked live from its own records and cannot be marked by hand.

**XP, levels and badges.**
- XP adds up to levels: Reader 0, Explorer 50, Storyteller 120, Curator 200, Keeper 280.
- Each finished track gives a badge: Wayfinder, Close reader, Desk hand, Anthologist, Editor's hand.

**What everyone sees.** Every reader of the page sees "Your toolbox", one card per tool, and "How the desk works" in four steps.

**What editors see.** Editors also see the team's progress (email, roles, level, XP, quests done, last activity). Researchers see only their own.

**What the database holds.** It holds the rules: quests, XP, mode, editors-only, levels, badges and marks. `src/lib/learn.ts` holds the words.

## 3. Tests

- `src/__tests__/corpus-corner-state.test.tsx` (22): the stages for every status, the next-round text, the next steps, the sync parsing and the live announcement. It also checks that the page works when the track function is missing.
- `src/__tests__/corpus-learn.test.tsx` (13): the tracks, XP, levels and badges, marking, the editors' Team panel, and the page when the functions are missing. It also checks the Learn tab in the nav.
- The existing Corner and media tests pass unchanged.
