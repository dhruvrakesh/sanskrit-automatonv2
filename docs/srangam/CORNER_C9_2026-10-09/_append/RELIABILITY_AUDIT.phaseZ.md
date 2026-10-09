
## Phase Z — The Researchers' Corner: requests to the desk, anthologies (CORNER_C9_2026_10_09, 2026-10-09)

The SQL is in the automaton repository: `docs/cloud/C9_researchers_corner_2026-10-09.sql`, with its checks
in `docs/cloud/C9_checks_2026-10-09.sql`; applied through the Lovable Cloud SQL editor, as C4-C8 were.
The design is in `docs/RESEARCHERS_CORNER_2026-10-09.md`.

### Z.1 — What the site may do
- Ask, decide, withdraw, make and publish anthologies: 12 SECURITY DEFINER functions for
  `authenticated` (`corner_me`, `corner_kinds`, `corner_request_create`, `corner_requests`,
  `corner_request_decide`, `corner_request_cancel`, `corner_settings_set`, `corner_collection_save`,
  `corner_collections`, `corner_collection`, `corner_collection_publish`, `corner_collection_retire`).
  Each passes the corpus gate (C5/C7) first; asking needs `researcher`, `admin` or `super_admin`;
  deciding and publishing need `admin` or `super_admin`; the settings need `super_admin`.
- A request is one of 16 fixed kinds, its parameters checked against the mirror (`corner._clean`).
  A researcher's paid request waits for an editor; nothing past the day's cap (India time) is approved.
- The site never generates anything and never calls a model.

### Z.2 — What the desk may do
- `service_role` only, through `corpus-desk` (POST, HMAC-signed with `CORPUS_SYNC_SECRET`):
  `corner_desk_pull`, `corner_desk_report`, `corner_desk_heartbeat`, `corner_desk_state`. The function
  reads no user token; the desk's worker re-checks every parameter against `context.db`, runs the desk's
  own scripts with argument lists (no shell, no free text on a command line), within the desk's spend cap.
- Results arrive as drafts through the mirror (C4) and the pictures (C8); approval stays a person's act.

### Accepted (by design)
- A request waits for the desk PC (every ten minutes while it is on); the Corner shows when it last came.
- An anthology is published to the readers of the working corpus only; a public page is a later decision.

### Invariants added (Phase Z)
30. The site never runs generation: every paid act is a row in `corner.requests`, carried out on the desk.
31. A researcher's paid request runs only after an editor approves it, within the day's cap.
32. Only `service_role`, through the signed `corpus-desk`, takes or reports requests.
33. A published anthology holds approved stories only.
