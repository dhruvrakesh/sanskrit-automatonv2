#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs32_2026_10_09.py  DOCS32_2026_10_09

Records the Researchers' Corner switched on (C9 applied and checked, corpus-desk deployed, the desk's
worker live, the site published, Kanika and Parth invited), the Srangam pull-before-push rule (Lovable
pushes its own commits), what the live site showed (three role questions per page, the Pictures page
asking twice) and its fix LOAD_L1_2026_10_09, and the gaps between the Corner and the desk's own pages
(phase C10). Appends to docs/PLATFORM_2026-10-04.md (section 35), RUNBOOK.md,
docs/ENTERPRISE_PATH_2026-10-04.md (addendum 22) and docs/RESEARCHERS_CORNER_2026-10-09.md (section 7).
Needs DOCS31_2026_10_09 in the first three and CORNER_C9_2026_10_09 in the last.
Marker-idempotent per file, backup first, each file's line endings kept.

  python scripts/patch_docs32_2026_10_09.py --check
  python scripts/patch_docs32_2026_10_09.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS32_2026_10_09"

PLATFORM = """

## 35. The Corner switched on; fewer questions per page (DOCS32_2026_10_09)

**C9 applied (2026-10-09, about 12:30 IST)**, with P1-P2 before and V1-V4 after:
- P1: true | true | true | true. P2: true.
- V1: the seven tables have RLS on, and anon and authenticated may not read or write them.
- V2: 16 SECURITY DEFINER functions. anon may call none; authenticated the 12 for the site.
  - service_role may call all 16, not only the 4 for the desk. Supabase's default privileges give it EXECUTE on new public functions, and C9 revokes only PUBLIC, anon and authenticated.
  - This is harmless: service_role is the server-only key, and the 12 refuse a caller without a signed-in user. `SELECT * FROM public.corner_kinds();` in the SQL editor answers 42501 "The working corpus is open to signed-in readers only."
- V3: 16 kinds and 3 settings (2.00, true, 20). V4: an empty queue, scheme corner.1.

**The site.**
- The Corner commit was pushed after Lovable's own commit 3524708 ("Deployed corpus-media edge func", which regenerated `src/integrations/supabase/types.ts` only). A rebase put it on top as b3a604c, and the typecheck passed against the new types.
- Lovable deployed `corpus-desk` unchanged: an unsigned POST answers 401 "missing or malformed x-corpus-ts".
- The live site serves the Corner and anthology pages (their chunks are in the published entry).

**The desk.**
- SanskritCornerWorker runs every 10 minutes. Its rounds skipped quietly until corpus-desk was deployed, then reported "0 taken" from 13:08 IST.
- The heartbeat reaches the site with the desk's spend cap: $32, $26.59 spent, $5.41 left at 13:29 IST.

**People.** Kanika and Parth accepted their invitations as researchers. No request had been made by 14:03 IST.

**Seen on the live site** (Chrome, signed in as the super admin):
- Every page asked `has_role` and `my_roles` three times each, within a few milliseconds.
- The Pictures page asked `corpus_reader_media` twice for the same rows.
- Fixed by LOAD_L1_2026_10_09 (Srangam: `AuthContext`, `CorpusImages`, 4 tests, RELIABILITY_AUDIT Phase AA).
- Once, in a background tab, `/corpus/stories` said "The working corpus took too long to answer" (the site waits 15 s). The reload answered in 0.44 s. The OPS check `pg_stat_statements` in RUNBOOK shows whether the database itself was slow.
"""

RUNBOOK = """

## Srangam: pull before you push; LOAD_L1 (DOCS32_2026_10_09)

**Lovable pushes its own commits.** For example, it regenerates `src/integrations/supabase/types.ts` after a database change. A push from the desk is then refused ("fetch first"). Before every Srangam push:

    git fetch origin
    git log --oneline -3 origin/main
    git diff --stat HEAD...origin/main
    git pull --rebase --autostash origin main
    npm run typecheck ; npx vitest run ; npm run build
    git push origin main

`--autostash` puts the local `bun.lock` aside and back. If a rebase stops, `git rebase --abort` returns to where you were.

**LOAD_L1_2026_10_09** (fewer questions per page):
1. `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_l1_2026_10_09.py" --check`, from `D:\\srangam-42267`.
2. The same without `--check`.
3. Typecheck, tests and build.
4. Commit the five files it names, pull before you push, push, and Publish in Lovable.

Afterwards a page asks `has_role` and `my_roles` once each.

**Was the database slow?** Run this read-only check in the SQL editor. If `extensions.pg_stat_statements` is not found, use `pg_stat_statements`.

    SELECT calls, round(mean_exec_time::numeric, 1) AS mean_ms, round(max_exec_time::numeric, 1) AS max_ms,
           left(regexp_replace(query, '\\s+', ' ', 'g'), 100) AS query
    FROM extensions.pg_stat_statements
    WHERE query ILIKE '%corpus_reader_%' OR query ILIKE '%corner_%' OR query ILIKE '%my_roles%'
    ORDER BY max_exec_time DESC LIMIT 20;
"""

EP = """

## Addendum 2026-10-09 (22) (DOCS32_2026_10_09)

| # | Item | State |
|---|---|---|
| R1-R3, M2 | The Researchers' Corner | Switched on: C9 applied and checked, corpus-desk deployed, the worker live, the site published, two researchers invited. Next: the first story, picture and novel plan through it |
| L1 | Fewer questions per page | Built: one role check per user at a time; the Pictures page asks once (Srangam LOAD_L1, 4 new tests) |
| C10 | The Corner level with the desk's own pages | Next, after the first round trip. Free kinds: edit a story, check it again, edit a picture, restore a picture, edit a novel page. Paid kinds: picture ideas for a text, a cover. A "draw again" option for a novel's pages and cast (`--redo`) |
| L2 | The first load | Next: the entry chunk is 498 KB (175 KB gzip) on every first visit. Measure what the home and corpus pages load before changing any chunking |
| R5, B1, P2, R6 | Young and teen versions; the desk's books on the site; a public anthology page; notifications | As in addendum 21 |
| A1p | Publish and one invitation end to end | Done for the invitations (Kanika, Parth) |
| V10 | The withheld verses | Still open |
"""

CORNER = """

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
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS31_2026_10_09"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS31_2026_10_09"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS31_2026_10_09"),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER, "CORNER_C9_2026_10_09")]


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
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs32_" + stamp))
        t = p.with_name(p.name + ".tmp_docs32"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
