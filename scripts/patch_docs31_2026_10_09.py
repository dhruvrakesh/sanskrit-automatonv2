#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs31_2026_10_09.py  DOCS31_2026_10_09

Records M1 live (C8 applied, corpus-media deployed, the first push: 57 pictures, 114 renditions,
13.7 MB on Drive, folder 1A9yLVNC4iLWuYoueP6b3aECEyne2XQXa; automaton c42cace2, Srangam cb280ccc),
and the Researchers' Corner (CORNER_C9_2026_10_09, docs/RESEARCHERS_CORNER_2026-10-09.md): requests
from the site carried out on the desk, anthologies, and every sync command in one place
(docs/SYNC_COMMANDS_2026-10-09.md). Appends to docs/PLATFORM_2026-10-04.md (section 34), RUNBOOK.md,
docs/ENTERPRISE_PATH_2026-10-04.md (addendum 21) and docs/CORPUS_MIRROR_2026-10-08.md, and keeps the
worker's run log, lock and ledger out of git. Needs DOCS30_2026_10_09 in the first three.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs31_2026_10_09.py --check
  python scripts/patch_docs31_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS31_2026_10_09"

PLATFORM = """

## 34. Pictures live; the Researchers' Corner (DOCS31_2026_10_09)

**M1 is live (2026-10-09, 10:00-10:20 IST).**
- **C8.** C8 was applied, with P1-P3 before and V1-V3 after, all as expected:
  - V1: four tables, RLS on and closed;
  - V2: 12 functions, the readers' 4 for authenticated and the desk's 8 for service_role.
- **The function.** Lovable deployed `corpus-media` unchanged and checked that an unsigned call is refused with 401.
- **The push.** `corpus_media.py --apply` sent 57 pictures, 113 uploads plus 1 skipped on a retry (no duplicate) and 2 novels, in 774 s. The second plan had nothing to send.
- **What the site holds.** D1: generated 17 approved / 12 draft, cover 1 / 1, novel_page 20 draft, novel_cast 6 draft, 2 novels drawing. D3: 57 + 57 renditions, 12.1 + 1.6 MB. D4: the folder `1A9yLVNC4iLWuYoueP6b3aECEyne2XQXa`.
- **Releases.** Automaton c42cace2 and Srangam cb280ccc. The site shows the Pictures and Graphic novels tabs and the novel reader with its cast.
- **The task.** SanskritCorpusMirror now runs the pictures step, and has WakeToRun on.

**The Researchers' Corner (CORNER_C9_2026_10_09).** `docs/RESEARCHERS_CORNER_2026-10-09.md`.
- **What researchers can ask the desk for:**
  - a story from passages they choose;
  - an episode written;
  - episodes found in a text;
  - a picture for a passage, from their own brief, or for a story;
  - a picture drawn again;
  - a graphic novel planned from an approved story, its cast and its pages.
- **Who decides.** Editors approve researchers' paid requests and the results, within a day's cap of $2.00 (India time).
- **Where the work runs.** The desk does every request with its own scripts (`scripts/corner_worker.py`, task SanskritCornerWorker every 10 minutes) and sends the results on at once, as drafts.
- **Anthologies.** Approved stories across texts are composed on the site, printed or saved as PDF, and published to the working corpus's readers.

| Part | File | Tests |
|---|---|---|
| Database | `docs/cloud/C9_researchers_corner_2026-10-09.sql`; checks `docs/cloud/C9_checks_2026-10-09.sql` | `tests/test_corner_pg_2026_10_09.py` (7) |
| Edge function | `docs/cloud/C9_corpus-desk/` (`corpus-desk`) | `deno test`: 9 + 10 |
| Desk worker | `scripts/corner_worker.py`, `scripts/corner_task.ps1` | `tests/test_corner_worker_2026_10_09.py` (10) |
| Site | `docs/srangam/CORNER_C9_2026-10-09/`, put in by `scripts/patch_srangam_corner_2026_10_09.py` | `src/__tests__/corpus-corner.test.tsx` (20) |

**Every sync command** is in `docs/SYNC_COMMANDS_2026-10-09.md`:
- the mirror, the pictures and the Corner;
- the published texts and the cloud's vectors;
- the tasks and their logs;
- the SQL checks.
"""

RUNBOOK = """

## The Researchers' Corner (DOCS31_2026_10_09)

**Switching it on, once.** The commands are in `docs/RESEARCHERS_CORNER_2026-10-09.md` and in the reply of 2026-10-09.
1. **Back up.** `python scripts\\db_backup.py`.
2. **SQL editor.** C9 checks P1-P2, then C9 in one paste, then V1-V4.
3. **Srangam.**
   - `patch_srangam_corner_2026_10_09.py --check`, then without `--check`.
   - Typecheck, tests and build.
   - Commit the listed paths and push.
4. **Lovable.** Ask Lovable to deploy `corpus-desk` unchanged, then Publish.
5. **The desk.**
   - `python scripts\\corner_worker.py --hello`.
   - Register SanskritCornerWorker (every 10 minutes, `scripts\\corner_task.ps1`).
   - `Start-ScheduledTask -TaskName SanskritCornerWorker`.
6. **The first request.** Ask for a story from passages as the super admin. Approve it from its page once written.

**Every day.**
- **Corner, Queue.** Approve or reject researchers' requests.
- **When the desk last came.** The Corner's status strip, or C9 D3.
- **What it did.** `D:\\backups\\corner_worker_log.txt`.
- **Every sync command.** `docs/SYNC_COMMANDS_2026-10-09.md`.
"""

EP = """

## Addendum 2026-10-09 (21) (DOCS31_2026_10_09)

| # | Item | State |
|---|---|---|
| M1 | Pictures and graphic novels on the site | Live: C8 applied and checked, corpus-media deployed, 57 pictures / 114 renditions / 2 novels pushed; the task carries them every 2 h |
| R1-R3, M2 | The Researchers' Corner: requests carried out on the desk, the editors' queue and decisions, anthologies, print | Built and tested (C9 7, corpus-desk 19, worker 10, site 20). Next: the RUNBOOK steps |
| R5 | Young and teen versions on the site | Next: mirror `doc_story_variants` (a C4 addition) |
| P2 | A public page for published anthologies | Your decision: it needs a public path for their pictures |
| B1 | The desk's typeset books (Booksmith, `stories.py book`, `novel.py build`) on the site | Next: chunked uploads to Drive; the site's print covers it until then |
| A1p | Publish and one invitation end to end | Still open |
| V10 | The withheld verses | Still open |
"""

MIRROR = """

## The Corner sends its results on (DOCS31_2026_10_09)

- After each request, `scripts/corner_worker.py` runs these, so a result is on the site within a minute of the desk finishing, not two hours later:
  - `corpus_sync.py --apply --if-configured --doc <code> --tables docs,stories` for stories;
  - `corpus_media.py --apply --if-configured --doc <code>` for pictures and novels.
- Both are the same idempotent pushes the two-hourly task runs, limited to that text.
- Every sync command is in `docs/SYNC_COMMANDS_2026-10-09.md`.
"""

GITIGNORE = """
# CORNER_C9_2026_10_09 (DOCS31_2026_10_09): the Corner worker's run log, lock and ledger stay local
data/corner_worker_log.jsonl
data/corner_worker.lock
data/corner_worker_made.jsonl
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, True), (Path("RUNBOOK.md"), RUNBOOK, True),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, True),
           (Path("docs/CORPUS_MIRROR_2026-10-08.md"), MIRROR, False), (Path(".gitignore"), GITIGNORE, False)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text, needs30 in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs30 and b"DOCS30_2026_10_09" not in raw:
            print("REFUSE: %s has no DOCS30_2026_10_09 section (run patch_docs30 first). Nothing written." % p); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs31_" + stamp))
        t = p.with_name(p.name + ".tmp_docs31"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
