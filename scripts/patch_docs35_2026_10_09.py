#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs35_2026_10_09.py  DOCS35_2026_10_09

Records C10a live (corner_request_track answering, 9 Oct evening), and the release CORNER_C10 + MAIL_E1 +
LOAD_L2: desk worker 1.2 (eight new kinds, redo, the mail flush), C10b (the kinds), C12 (the Corner's
email outbox), the edge function corner-mail (Resend, nartiang.org), the site's edit forms, ideas and
email settings, and L2's two cuts to the first visit; with the order to switch them on.
Appends to docs/PLATFORM_2026-10-04.md (section 38), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 25), docs/RESEARCHERS_CORNER_2026-10-09.md (section 9) and docs/SYNC_COMMANDS_2026-10-09.md
(section 11). Needs DOCS34_2026_10_09 in the first three and the last, DOCS33_2026_10_09 in
RESEARCHERS_CORNER. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs35_<date>),
each file's line endings kept.

  python scripts/patch_docs35_2026_10_09.py --check
  python scripts/patch_docs35_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS35_2026_10_09"

PLATFORM = """

## 38. C10a live; the Corner level with the desk; email from nartiang.org; L2 (DOCS35_2026_10_09)

**9 Oct, evening (IST).**
- 20:08: corner and mirror tasks LastTaskResult 0. 20:12: a manual backup, `D:\\backups\\context_20261009_2012.db` (consistent, docs 68).
- C10a pasted after a read-only check that no request was claimed or running. docs34 released as 3c649baa.
- Checked on the live site: `corner_request_track` answers 200, and request #1 shows "Taken by the desk 14:58". The strip said "Mirror: in step at 20:32", "Pictures: 114 of 114 files on Drive at 20:32".

**The release (docs/CORNER_C10_MAIL_2026-10-09.md, docs/LOAD_L2_2026-10-09.md):**
- **Desk worker 1.2** (CORNER_C10_2026_10_09):
  - eight new kinds: story_edit, story_verify, picture_ideas, picture_cover, picture_draw, picture_edit, picture_restore, novel_page_edit;
  - redo for novel_cast and novel_draw;
  - the mail flush once a round.
  - Edits run in-process with the desk's own functions. No free text reaches a command line.
- **C10b:** the kinds; corner._clean and _estimate (C9's kinds unchanged but for "redo"); `corner_ideas`, `corner_retired_pictures`.
- **C12:** `corner.outbox`, `corner.mail_prefs`, a trigger on `corner.requests` that never fails a request, the claim/done functions (service role only), prefs, state, invitations, and four settings (mail off by default).
- **corner-mail:** the edge function that sends through Resend. The desk signs as for corpus-desk; a person sends their JWT and must be able to ask the desk.
- **The site:**
  - edit forms (lazy);
  - "Check again";
  - ideas and "Draw this idea";
  - retired pictures for editors;
  - "again" for a novel's cast and pages;
  - email settings and "Send it from nartiang.org" for invitations.
- **L2:** the home page no longer downloads the 548 kB terms dataset for a word not in it, and the toast hosts left the entry (607.3 -> 560.6 kB, 173.4 -> 159.7 kB gzip).
- **Tests:** worker 61, C9 7, C10a 16, C11 9, C10b 33, C12 51, corner-mail 14 (Deno). The site suite has 283 tests, 280 passing; the 3 known environment-only failures remain.

**DNS (nartiang.org, serial 2026100904).**
- Hosting: A 185.158.133.1 for @, www and srangam, with Lovable's verification records.
- Signing: a Resend DKIM key (`resend._domainkey`) and two sending CNAMEs.
- DMARC p=none.
- No MX: nothing receives mail at nartiang.org, so the Corner's Reply-to must be a real inbox.
"""

RUNBOOK = """

## C10, email and L2: switching on (DOCS35_2026_10_09)

The order matters: the desk's worker 1.2 before C10b.
1. **The desk**, between two rounds:
   - `python scripts\\patch_corner_worker_c10_2026_10_09.py --check`, then without `--check`;
   - `python scripts\\patch_tests_worker_client_2026_10_09.py`;
   - `python -m unittest tests.test_corner_worker_c10_2026_10_09 tests.test_corner_worker_state_2026_10_09 tests.test_corner_worker_2026_10_09`.
2. **`python scripts\\patch_docs35_2026_10_09.py`, then release.**
3. **The SQL editor** (in either order):
   - `docs/cloud/C10b_checks_2026-10-09.sql` P1, then C10b in one paste, then V1-V3;
   - `docs/cloud/C12_checks_2026-10-09.sql` P1, then C12 in one paste, then V1-V3.

   Re-run both after any re-run of C9.
4. **Srangam:**
   - `patch_srangam_c10_mail_2026_10_09.py`, then `patch_srangam_load_l2_2026_10_09.py`;
   - typecheck, tests and build;
   - commit the paths they print;
   - pull before you push; push; Publish.
5. **Lovable:**
   - deploy the edge function corner-mail without changing its code;
   - Cloud -> Secrets: `RESEND_API_KEY` (a Resend key with sending access for nartiang.org).
6. **Corner -> Settings (super admin):**
   - Reply-to: an inbox you read (nartiang.org receives no mail);
   - then Email on.

**To stop all email at once:** Settings -> Email off, or in the SQL editor `UPDATE corner.settings SET value = 'false', updated_at = now() WHERE key = 'mail_enabled';`. The outbox keeps what is waiting.
"""

EP = """

## Addendum 2026-10-09 (25) (DOCS35_2026_10_09)

| # | Item | State |
|---|---|---|
| C10a, S1, T1 | The Corner as it happens; Learn | Live (C10a pasted 9 Oct evening; corner_request_track answers) |
| C10 | The Corner level with the desk: edits, check again, ideas, covers, draw an idea, restore, novel page edits, redo | Built and tested (worker 1.2, C10b, the site). Next: switch on (RUNBOOK) |
| R6, A3 | Email from nartiang.org: requests done/failed/waiting/not approved, invitations | Built and tested (C12, corner-mail, the site). Needs RESEND_API_KEY and Email on |
| L2 | The first visit | Two cuts built (P3, P4). Next: P2 after a check in Hindi and Tamil; P1 by traffic mix |
| T2 | Learn quests for C10's kinds | Next |
| R5, B1, P2 | As in addendum 21 | As before |
"""

CORNER = """

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
"""

SYNC = """

## 11. The Corner's email (DOCS35_2026_10_09)

| What | From | To | How | When |
|---|---|---|---|---|
| A Corner email | `corner.outbox` (written by the database) | the person's inbox, through Resend | the edge function corner-mail | each desk round (worker 1.2), and right after a request, a decision or an invitation on the site |

**On the desk:**
- The worker's run log shows the mail flush: `Get-Content data\\corner_worker_log.jsonl -Tail 1`, its "mail" entry.
- `{"configured": false}`: RESEND_API_KEY is not in Lovable Secrets.
- "corner-mail is not deployed": ask Lovable to deploy it.

**In the SQL editor, read-only:** `docs/cloud/C12_checks_2026-10-09.sql`:
- D1: waiting, sent and failed, by kind;
- D2: the last 20, without addresses or bodies.

**On the site (editors):** the Sync tab's Mail line (`corner_mail_state`).
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS34_2026_10_09"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS34_2026_10_09"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS34_2026_10_09"),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER, "DOCS33_2026_10_09"),
           (Path("docs/SYNC_COMMANDS_2026-10-09.md"), SYNC, "DOCS34_2026_10_09")]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs.encode() not in raw:
            print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, needs)); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs35_" + stamp))
        t = p.with_name(p.name + ".tmp_docs35"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
