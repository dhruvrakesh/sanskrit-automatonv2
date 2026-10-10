# The Corner level with the desk, and email from nartiang.org (2026-10-09)

**Markers:**
- CORNER_C10_2026_10_09: the desk's worker 1.2.
- CORNER_C10B_2026_10_09: the new kinds of request.
- CORNER_MAIL_C12_2026_10_09: the database's email outbox.
- MAIL_E1_2026_10_09: the edge function `corner-mail`.
- CORNER_C10_MAIL_2026_10_09: the site.

This follows `docs/RESEARCHER_EXPERIENCE_2026-10-09.md` (state and Learn) and `docs/RESEARCHERS_CORNER_2026-10-09.md` (C9).

## 1. What a researcher can now do from the site

| She wants | On the site | What the desk does | Cost (estimate) |
|---|---|---|---|
| To correct a story's words | "Edit" under the story | the edit of the desk's Stories page, in-process (`stories_web.stories_edit`'s update): the check runs again; the story is a draft until an editor approves it | free |
| A story checked again | "Check again" | `stories.verify` over its passages | free |
| Ideas for pictures in a text | Corner -> Ask -> "Ideas for pictures in a text" (1-12) | `images.py brief --doc X --max N --more --yes` | about $0.02 |
| An idea for a cover | "An idea for a cover" | `images.py cover --doc X --more --yes` | about $0.01 |
| One of those ideas drawn | "Ideas waiting to be drawn" -> "Draw this idea" | `images.py approve-brief`, then `generate --id` | about $0.10 |
| A picture's words corrected | "Edit words" under the picture: title, captions, context; the licence for editors | `images.set_status` with the fields (the desk's Pictures page edit) | free |
| A retired picture back (editors) | Corner -> Ask -> "Retired pictures" -> "Restore" | back to draft, `retired_at` cleared, so the mirror shows it again | free |
| A novel page's scene or captions corrected | "Edit page" under the page | `novel.edit_page`: the plan is checked again; a changed scene marks the page's picture stale; an approved novel goes back to plan | free |
| The cast or every page drawn again | "Draw the cast again" / "Draw every page again" (asks twice) | `novel.py cast/draw --redo` | about $0.40 / $0.10 a page |

**Rules:**
- Free requests are approved at once. A researcher's paid requests wait for an editor, as in C9, within the day's cap.
- A researcher never edits an approved story, picture or novel. A proposed episode changes only its titles, and only editors change a licence.
- The database checks every request (`corner._clean`), and the desk checks it again against `context.db` before acting.
- Free text (a story, a caption, a scene) travels as data, never on a command line.

**Ideas are not mirrored.** `corpus.media` carries only drawn pictures.
- The desk returns its new ideas in the request's result.
- `corner_ideas(doc)` lists them for everyone who may ask the desk, and says whether each is drawn.

## 2. Email from nartiang.org

**What sends mail:**
- The database queues each email in `corner.outbox`; a trigger on `corner.requests` writes it. Nothing is queued while `mail_enabled` is false, which is the default.
- The edge function `corner-mail` sends them through Resend. It is called:
  - by the desk once a round;
  - by the site right after someone asks the desk, an editor decides, or the super admin sends an invitation.

**Who gets which email:**

| When | Who | Email |
|---|---|---|
| A researcher's paid request waits | every editor except the asker, unless they turned it off | "Request #N waits for approval", with the queue link |
| A paid request is done, or any request failed | the asker, unless turned off | "Request #N is done" / "could not be done", with what the desk said and the cost |
| An editor did not approve a request | the asker | "was not approved", with the editor's note |
| The super admin sends an invitation | the invited address | the link `/invite/<token>`; the link is deleted from the outbox once sent |

**Privacy:**
- Bodies are plain text, with no story text.
- Every Corner email ends with how to stop them (Corner -> Settings).
- Only editors see the outbox counts (`corner_mail_state`).
- Addresses never appear in a log line or in a function's answer.
- The key `RESEND_API_KEY` lives only in Lovable Secrets and is read only by `corner-mail`.

### 2.1 The nartiang.org DNS zone (exported 9 Oct, 14:59 UTC, serial 2026100904)

**What the zone has:**
- **Hosting.** `@`, `www` and `srangam` are A records to 185.158.133.1 (TTL 300). `_lovable.srangam` and `_lovable.www` are the Lovable verification records. The site is served by Lovable.
- **Signing.** `resend._domainkey` TXT carries a DKIM public key: nartiang.org was set up as a sending domain in Resend.
- **Two CNAMEs.** `send` -> `send.forge.rmta.net` and `rsend` -> `rsend-apne1.forge.rmta.net`. These are the sending subdomain records. Resend's own dashboard is the place to confirm they are what it expects.
- **DMARC.** `_dmarc` TXT `v=DMARC1; p=none;`: monitoring only, with no report address.
- **Search Console.** `google-site-verification` TXT.
- **No MX for nartiang.org.** Mail sent to an @nartiang.org address cannot be received.

**What to do:**
1. **Resend -> Domains -> nartiang.org must say Verified** (DKIM and the sending records). If it does not, add exactly the records Resend lists there.
2. **Resend -> API Keys:** make one with "Sending access" for nartiang.org. Add it in Lovable -> Cloud -> Secrets as `RESEND_API_KEY`. Never paste it anywhere else.
3. **The sender is `Srangam desk <desk@nartiang.org>`.** Nothing receives mail at nartiang.org, so set Corner -> Settings -> Reply-to to an inbox you read. Otherwise replies bounce.
4. **Later, optional:**
   - DMARC `v=DMARC1; p=none; rua=mailto:<an inbox you read>` to receive reports.
   - Once the reports show the Corner's mail passing, `p=quarantine`.
   - Do not add CAA records unless you know Lovable's certificate issuer.

## 3. The parts

| Part | Files | Tests |
|---|---|---|
| Worker 1.2 | `docs/desk/CORNER_C10_2026-10-09/corner_worker.py`, put in by `scripts/patch_corner_worker_c10_2026_10_09.py` (md5-guarded over 1.1) | `tests/test_corner_worker_c10_2026_10_09.py` (29). The 1.1 tests pass once `scripts/patch_tests_worker_client_2026_10_09.py` makes their two version checks compare with `cw.CLIENT`. 61 with the database |
| C10b | `docs/cloud/C10b_corner_kinds_2026-10-09.sql`; checks `docs/cloud/C10b_checks_2026-10-09.sql` | `tests/test_corner_kinds_pg_2026_10_09.py` (33, with C9's and C10a's tests on top) |
| C12 | `docs/cloud/C12_corner_mail_2026-10-09.sql`; checks `docs/cloud/C12_checks_2026-10-09.sql` | `tests/test_corner_mail_pg_2026_10_09.py` (51, with C9's and C10a's tests on top, mail off and on) |
| corner-mail | `docs/cloud/E1_corner-mail/` (index.ts, lib.ts), copied to `supabase/functions/corner-mail/` by the site patch | `lib_test.ts` (`deno test --no-remote`, 14) |
| The site | `docs/srangam/C10_MAIL_2026-10-09/`, put in by `scripts/patch_srangam_c10_mail_2026_10_09.py` | `corpus-corner-c10.test.tsx` (19), `corner-mail.test.tsx` (14); full suite 280 passing, the 3 known environment-only failures |

**The site's code size:**
- The edit forms (`DeskEdit`, 3.9 kB) and the Corner's new panels (`CornerPanels`, 15.3 kB) load only when used.
- The story, picture and novel pages are within 0.1 kB of before.
- The entry is unchanged by this part. L2, below, makes it smaller.

**Checked together:**
- In one database, the SQL went in the live order, then C10b and C12 again: C4 ... C9, C10a, C11, C12, C10b, C10b, C12.
- All the checks files ran against it without error.
- Every test ran against fresh databases: C9 7, C10a 16, C11 9, C10b 33, C12 51, worker 61.

## 4. The order (it matters)

1. **The desk:**
   - worker 1.2, between rounds;
   - then the test patch;
   - then its tests.

   Worker 1.2 is harmless before the SQL. Worker 1.1 would fail a request of a kind it does not know.
2. **Release** the automaton repo (`patch_docs35_2026_10_09.py` first).
3. **The SQL editor**, in either order:
   - C10b: P1, the paste, V1-V3;
   - C12: P1, the paste, V1-V3.

   A re-run of C9 puts back C9's `corner._clean` and `corner_settings_set`. Re-run C10b and C12 after any re-run of C9.
4. **Srangam:**
   - the C10_MAIL patch, then the L2 patch (`docs/LOAD_L2_2026-10-09.md`);
   - typecheck, tests, build;
   - commit, pull, push, Publish.
5. **Lovable:**
   - ask it to deploy the edge function `corner-mail` without changing its code;
   - add the secret `RESEND_API_KEY`.
6. **The super admin**, in Corner -> Settings:
   - Reply-to: an inbox you read;
   - then turn email on.

## 5. Rollback

- **Worker:** copy `scripts/corner_worker.py.bak_c10_<date>` back. It is 1.1.
- **C10b and C12:** the rollback blocks in their headers, one paste each. Turning email off is enough to stop every email: the switch in Settings, or in the SQL editor `UPDATE corner.settings SET value = 'false', updated_at = now() WHERE key = 'mail_enabled';`.
- **Site:** the `.bak_c10mail_<date>` and `.bak_load_l2_<date>` copies, or `git revert` of the commit.

## 6. Next

- **T2:** Learn quests for the new kinds (edit, check again, ideas, draw an idea).
- **L2, second step:** P2 (languages on demand) after a check in Hindi and Tamil; P1 (Home out of the entry) only if most first visits land elsewhere than `/`.
- **C10 left over:**
  - A "draw again" for a single cast sheet.
  - The young and teen versions (R5, needs `doc_story_variants` in the mirror).
- **B1:** the desk's typeset books on the site.
- **P2:** a public anthology page (your decision).
