
## Phase AB — The Corner as it happens; Learn (STATE_LEARN_2026_10_09: CORNER_STATE_S1_2026_10_09, LEARN_T1_2026_10_09, 2026-10-09)

The SQL is in the automaton repository: `docs/cloud/C10a_corner_state_2026-10-09.sql` (a request's
progress, `corner_request_track`) and `docs/cloud/C11_learn_2026-10-09.sql` (schema `learn`), each with
its checks; the design is in `docs/RESEARCHER_EXPERIENCE_2026-10-09.md`.

### AB.1 — What the site may do
- Read the state of up to 100 of the viewer's own requests (editors: any) with `corner_request_track`;
  read the desk's report of the mirror and the pictures only as an editor (`corner_me().worker_info`).
- Learn: `learn_me`, `learn_summary`, `learn_mark` (exploration quests only), `learn_team` (editors).
  Each passes the corpus gate first and is open to researchers and editors only.
- The site still never generates anything, and a quest never starts a paid request by itself.

### AB.2 — Load
- The Corner's new parts live in `cornerState.ts` and `CornerState.tsx`, imported only by
  `/corpus/corner`; the story, picture and novel pages load no more than before.
- Live refresh runs only while a listed request is open (20 s); otherwise the desk's state every 5 min.

### Invariants added (Phase AB)
36. A request's progress comes from the desk only (`corner_desk_report`, service_role); the site only reads it.
37. Without C10a or C11 in the database, the Corner and Learn behave as before and show no error.
38. Auto quests are computed from the Corner's own records and cannot be marked by hand.
39. Only editors see other people's progress (`learn_team`) or the desk's sync report.
