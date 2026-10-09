#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs30_2026_10_09.py  DOCS30_2026_10_09

Records phase M1 (CORPUS_MEDIA_C8_2026_10_09): the desk's pictures and graphic novels on the site,
kept private in the Srangam Shared Drive (docs/MEDIA_AND_CORNER_2026-10-09.md), how to switch it on
and run it, and the path to the Researchers' Corner (M2, R1-R4, P1). Appends to
docs/PLATFORM_2026-10-04.md (section 33), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 20) and docs/CORPUS_MIRROR_2026-10-08.md, and keeps the pictures' run log
(data/corpus_media_log.jsonl) out of git, as the mirror's is. Needs DOCS29_2026_10_08 in the first three.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs30_2026_10_09.py --check
  python scripts/patch_docs30_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS30_2026_10_09"

PLATFORM = """

## 33. Pictures and graphic novels on the site; the path to the Researchers' Corner (DOCS30_2026_10_09)

**Phase M1** (CORPUS_MEDIA_C8_2026_10_09). The design and its numbers are in `docs/MEDIA_AND_CORNER_2026-10-09.md`.
- **What the site gets.** The image library and the graphic novels, in the working corpus:
  - `/corpus/images`: each picture linked to its passage;
  - `/corpus/novels/:id`: cast, pages, English and Hindi captions with linked citations, speech with its verse, the scene asked for, the check;
  - the story's picture at the head of each story.
- **Who sees what.** Readers see approved pictures; admins and the super admin also see drafts.
- **Storage.** The Srangam Shared Drive, folder "Srangam corpus media", not shared by link.
  - The bytes are served by the edge function `corpus-media`, as the reader, after the database says yes.
  - The browser keeps each picture after its first view.
- **The parts.**

| Part | File | Tests |
|---|---|---|
| Database | `docs/cloud/C8_corpus_media_2026-10-09.sql` (one paste) and `docs/cloud/C8_checks_2026-10-09.sql` (P1-P3, V1-V3, D1-D5) | `tests/test_corpus_media_pg_2026_10_09.py` (8) |
| Edge function | `docs/cloud/C8_corpus-media/` (`index.ts`, `lib.ts`) | `deno test`: `lib_test.ts` (6), `_test/handler_test.ts` (4) |
| Desk | `scripts/corpus_media.py` (plan by default, `--apply`, `--hello`, `--status`) | `tests/test_corpus_media_2026_10_09.py` (15, one against PostgreSQL) |
| Site | `docs/srangam/MEDIA_M1_2026-10-09/`, put in by `scripts/patch_srangam_media_2026_10_09.py` | `src/__tests__/corpus-media.test.tsx` (12) |
| Schedule | `scripts/patch_media_task_2026_10_09.py`: the pictures after the mirror, and the PC kept awake for the tick | parsed with PowerShell |

- **Measured 2026-10-09** on `context_20261009.db`:
  - 57 pictures would travel (31 library pictures, 26 pictures of 2 novels being drawn);
  - their 114 renditions are 14.3 MB, made in 4.4 s;
  - 71 briefs not drawn stay home.
- **The path after M1** (section 3 of the design document):
  - **M2.** Editors act from the site, and the desk applies it.
  - **R1.** The Corner: saved passages, notes, my requests.
  - **R2.** Requests, approved by an admin when they cost money.
  - **R3.** A desk worker runs the existing CLIs within the live budget; results arrive as drafts.
  - **R4.** Spend and audit.
  - **P1.** A bucket for display renditions, only if first views feel slow.
"""

RUNBOOK = """

## Pictures and graphic novels on the site (DOCS30_2026_10_09)

**Switching it on, once.** Each step's commands are in `docs/MEDIA_AND_CORNER_2026-10-09.md` and in the reply of 2026-10-09.
1. **Back up.** `python scripts\\db_backup.py`.
2. **In the SQL editor.** `docs/cloud/C8_checks_2026-10-09.sql` P1-P3, then C8 in one paste, then V1-V3. One query per paste; export each to `D:\\backups\\media_2026-10-09\\`.
3. **Srangam.**
   - `scripts\\patch_srangam_media_2026_10_09.py --check`, then without `--check`.
   - `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Commit the listed paths and push.
4. **Lovable.** Ask Lovable to deploy `corpus-media` without changing its code. No new secret is needed.
5. **The desk.**
   - `python scripts\\corpus_media.py --hello`. Expect `corpus-media c8.1` and `drive: true`.
   - Then `python scripts\\corpus_media.py` (the plan).
   - Then `--apply`.
6. **Check.** D1-D5 in the SQL editor. Publish in Lovable.
   - `/corpus/images` as an admin shows drafts.
   - In a private window, as a reader, only approved pictures appear.
7. **The schedule.**
   - `python scripts\\patch_media_task_2026_10_09.py --check`, then without `--check`.
   - The next SanskritCorpusMirror tick logs "DONE - corpus media rc=0".

**When something is wrong.**

| Seen | Meaning | Do |
|---|---|---|
| `--hello`: HTTP 404 | The function is not deployed | Step 4 |
| HTTP 422 `corpus_media_state ... Could not find` | C8 is not applied | Step 2 |
| HTTP 401 `bad signature` | The secret in `.env` and in Lovable Secrets differ | Make them the same, as for the mirror |
| `HELD: ... not in the mirror yet` | That text is not in schema corpus | `corpus_sync.py --apply` first |
| HTTP 502 `Drive upload failed` | The service account cannot write to the Shared Drive | Check `GOOGLE_SERVICE_ACCOUNT_JSON` and that the account is a member of the Shared Drive (as for `tts-save-drive`) |
| The site says "not available here yet" | C8 is not applied, or not published | Steps 2 and 6 |
| A picture shows "This picture is not available" | No rendition for it, or it is not visible to this reader | D2; run `--apply` again |
| `refusing to retire N of the site's M pictures` | `--db` points at the wrong database | Check `--db`; `--allow-mass-retire` only if it is right |
"""

EP = """

## Addendum 2026-10-09 (20) (DOCS30_2026_10_09)

| # | Item | State |
|---|---|---|
| M1 | Pictures and graphic novels on the site, private in the Shared Drive | Built and tested: C8 (8 PG tests), corpus-media (10 Deno tests), corpus_media.py (15), the site (12 vitest, typecheck, build). Next: the RUNBOOK steps (C8, Srangam patch, deploy, the first push) |
| M1s | The pictures in the two-hourly tick, and the PC kept awake for it | `patch_media_task_2026_10_09.py`, after the first manual push |
| M2 | Editors approve, retire or redraw from the site; the desk applies it | Next after M1 |
| R1 | The Researchers' Corner `/corpus/corner`: saved passages, notes, my requests | Designed (docs/MEDIA_AND_CORNER_2026-10-09.md, section 3) |
| R2 | Requests (story, picture, novel, correction), with approval for spend | Designed; defaults in section 3 |
| R3 | The desk worker runs requests with the existing CLIs, within the live budget | Designed |
| R4 | Spend, caps and audit per request and researcher | Designed |
| A1p | Publish and one invitation end to end | Still open |
| V10 | The withheld verses (markandeya 01/99; Sandilya 00/01/99) | Still open |
"""

MIRROR = """

## The pictures in the same tick (DOCS30_2026_10_09)

- After the mirror, `corpus_mirror_task.ps1` runs `scripts\\corpus_media.py --apply --if-configured --max-mb 40`, once `scripts/patch_media_task_2026_10_09.py` is applied.
  - It uses the same secret, URL and key, and the same signature, against the function `corpus-media`.
  - It is read-only on `context.db`.
  - When nothing changed, it only asks the site what it has.
- Its log lines go to the same `D:\\backups\\corpus_mirror_log.txt` ("DONE - corpus media rc=..."), and each run is also recorded in `data\\corpus_media_log.jsonl`.
- A picture can travel only for a text that is already in schema corpus, so the mirror runs first.
- The tick keeps the PC awake while it runs. The night tick of 2026-10-08 stretched to 7.5 h when the PC slept in the middle of it.
"""

GITIGNORE = """
# CORPUS_MEDIA_C8_2026_10_09 (DOCS30_2026_10_09): the pictures' run log stays local
data/corpus_media_log.jsonl
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, True), (Path("RUNBOOK.md"), RUNBOOK, True),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, True),
           (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR, False), (Path(".gitignore"), GITIGNORE, False)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs29 in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs29 and b"DOCS29_2026_10_08" not in raw:
            print("REFUSE: %s has no DOCS29_2026_10_08 section (run patch_docs29 first). Nothing written." % p); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs30_" + stamp))
        t = p.with_name(p.name + ".tmp_docs30"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
