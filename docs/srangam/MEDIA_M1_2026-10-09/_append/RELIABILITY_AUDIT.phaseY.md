
## Phase Y — Pictures and graphic novels of the working corpus (CORPUS_MEDIA_C8_2026_10_09, 2026-10-09)

The SQL is in the automaton repository: `docs/cloud/C8_corpus_media_2026-10-09.sql`, with its checks
in `docs/cloud/C8_checks_2026-10-09.sql`. It is applied through the Lovable Cloud SQL editor, as C4-C7
were: no file in supabase/migrations, no history row. The design is in `docs/CORPUS_MEDIA_2026-10-09.md`.
Before C8 and the function are in, `/corpus/images` and `/corpus/novels` say the pictures are not
available yet and the story pages are unchanged.

### Y.1 — Storage
- Two renditions of each picture (480 px and 1600 px JPEG) in the Srangam Shared Drive, folder
  "Srangam corpus media", created by the service account and NOT shared by link (no `permissions`
  call is ever made; `uploadToDrive({ shareAnyone: false })`). The originals stay on the desk.
- `corpus.media_files` maps (sha256, rendition) to the Drive file id; a picture is uploaded once.

### Y.2 — Reading (Invariant 15)
- `authenticated`: `corpus_reader_media`, `corpus_reader_novels`, `corpus_reader_novel`,
  `corpus_reader_media_file`. Each calls `corpus._reader_gate()` first. Readers see approved pictures
  and approved novels; `admin` / `super_admin` also see drafts. Retired is never returned.
- The bytes: `GET /functions/v1/corpus-media?sha=&r=` with the reader's JWT in `Authorization`. The
  function calls `corpus_reader_media_file` with that JWT (as the reader), and reads Drive only when
  it returns a file: 401 without a token, 403 when the gate refuses, 404 when not visible.
- `Cache-Control: private, max-age=2592000, immutable`, `Vary: Authorization`, ETag/304. The page keeps
  pictures in Cache Storage under the user's id; no token is ever put in a URL.

### Y.3 — Writing
- `service_role` only: `corpus_media_state`, `corpus_media_upsert`, `corpus_novels_upsert`,
  `corpus_media_retire`, `corpus_media_file_get`, `corpus_media_file_put`, `corpus_media_config_get`,
  `corpus_media_config_set`, reached only through `corpus-media` POST, HMAC-signed with
  `CORPUS_SYNC_SECRET` (the same scheme and secret as `corpus-ingest`), 5-minute clock window,
  6 MB body ceiling, every upload's bytes checked against the sha256 the desk declares.
- The site never writes pictures. Approval is a person's decision on the desk.

### Accepted (by design)
- Drive is not a CDN: the first view of each picture takes a moment (edge function, database
  check, Drive). Repeat views come from the browser.
- Files of retired pictures stay on Drive; C8 check D5 lists them for tidying by hand.

### Invariants added (Phase Y)
27. No corpus picture is shared by link or served without the reader's JWT and C8's visibility rule.
28. Only `service_role`, through the signed `corpus-media` POST, writes `corpus.media`, `corpus.media_files`, `corpus.novels`.
29. A picture row reaches the site only after both of its renditions are on Drive.
