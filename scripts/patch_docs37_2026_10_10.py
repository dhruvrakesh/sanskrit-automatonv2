#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs37_2026_10_10.py  DOCS37_2026_10_10

Records the rest of 10 Oct (NAV_RBAC_2026_10_10 published as Srangam ab15244, corner-mail deployed, email
on) and the release CORNER_UX_U1_2026_10_10: the Researchers' Corner, guided (Srangam), and C13 (the
Corner's researchers see the work in progress; the offering so far). docs/CORNER_UX_U1_2026-10-10.md
has the design.
Appends to docs/PLATFORM_2026-10-04.md (section 40), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 27) and docs/RESEARCHERS_CORNER_2026-10-09.md (section 11), each needing DOCS36_2026_10_10, and
to docs/SYNC_COMMANDS_2026-10-09.md (section 12), needing DOCS35_2026_10_09.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs37_<date>), line endings kept.

  python scripts/patch_docs37_2026_10_10.py --check
  python scripts/patch_docs37_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS37_2026_10_10"

PLATFORM = """

## 40. The Corner, guided; researchers see the work in progress (DOCS37_2026_10_10)

**10 Oct, the rest of the morning (IST).**
- NAV_RBAC_2026_10_10 was pushed and published as Srangam ab15244: the header's "Corpus" menu (with Learn and the Corner), "Admin" for admins only, "Sign in" while signed out, the phone's "Corpus" tab.
- Lovable deployed corner-mail with the other edge functions. The desk's next round logged `"mail": {"configured": true, "claimed": 0, ...}`.
- In Corner -> Settings: email on (Saved: on) and From saved (Srangam desk <desk@nartiang.org>). Reply-to showed no "Saved" note: its placeholder, desk@nartiang.org, looked like a saved value, and nartiang.org has no MX record (D2 of the C13 checks shows what is saved).

**Found, on Ask the desk:**
- Eleven forms were shown before a text was chosen.
- The 51 texts with English were in one list, with no sign of which had no story yet.
- Passages had to be typed, and the placeholders (25.2, 25.9) looked filled in.

**Found, in the database:**
- `corner._clean` accepts from a researcher: `story_write` (proposed episodes, drafts), `story_illustrate` (drafts), `story_edit` (proposed episodes, drafts), `novel_cast` and `novel_draw` (novels being drawn).
- The reader functions showed those to editors only.
- So a researcher's "Write a proposed episode" list was always empty, and the links on her own finished requests led to drafts she could not open.

**CORNER_UX_U1_2026_10_10 (Srangam; works with the database as it is).** Ask the desk is guided:
- the offering so far (one line);
- before a text, where to begin (texts with English and no story yet, the last text on this browser, "Surprise me") and no forms;
- after, what the text has, "What would you like to make?" (`?goal=`) and "Ready in this text", whose "Set it up" fills a form and asks nothing;
- passages chosen in the text itself (its own 5 kB chunk);
- Reply-to's placeholder and hint mended.
- A researcher's anthology editor offers approved stories only, as its save accepts from her.
- Tests: 17 new; the site's suite 311 tests, 308 passing, 2 skipped, the 3 known environment-only failures.
- Load: the entry is unchanged (565,270 bytes). The Corner's chunk grows from 54,421 to 71,330 bytes (21.2 kB gzip).
- Phase AE (invariants 47-49) in Srangam's docs/RELIABILITY_AUDIT.md.

**C13 (`docs/cloud/C13_corner_drafts_offering_2026-10-10.sql`, one paste, when chosen):**
- `corpus._sees_drafts()`: editors and invited researchers.
- `public.corner_offering()`: the strip's numbers.
- Five reader functions rewritten from their live definitions, one line each, all or none: `corpus_reader_stories`, `corpus_reader_media`, `corpus_reader_novels`, `corpus_reader_novel`, `corpus_reader_media_file`.
- Readers who are not invited see approved work only, as before.
- Checks: P1, V1-V3, D1 (the strip's numbers), D2 (the email settings as saved).
- Tests: `tests/test_corner_drafts_pg_2026_10_10.py` (6), against every file the live database has, then C13 twice.
"""

RUNBOOK = """

## The Corner, guided; C13 (DOCS37_2026_10_10)

1. **Srangam:**
   - `patch_srangam_corner_ux_u1_2026_10_10.py --check`, then without `--check`;
   - typecheck, tests and build;
   - commit the paths it prints;
   - pull before you push; push; Publish.
2. **Look, as a researcher:**
   - Ask the desk starts with "Where to begin" and shows no form;
   - choosing a text shows what it has, the goals and "Ready in this text";
   - "Choose them in the text" fills From and To.
3. **C13 (when you choose):** in the Lovable Cloud SQL editor, one query per paste:
   - `C13_checks` P1;
   - the whole of C13 in one paste;
   - V1, V2, V3;
   - D2, to see Reply-to as saved.
4. **Settings:** Reply-to = an inbox you read; Save. Then ask, as yourself, for "An idea for a cover" ($0.01): its email arrives after the desk's next round.
"""

EP = """

## Addendum 2026-10-10 (27) (DOCS37_2026_10_10)

| # | Item | State |
|---|---|---|
| N1 | The working corpus and Learn in the navigation, by role | Live (Srangam ab15244) |
| R6, A3 | Email from nartiang.org | Live: corner-mail deployed, email on. Next: Reply-to set to a real inbox, and a first email |
| U1 | The Corner, guided (`docs/CORNER_UX_U1_2026-10-10.md`) | Built and tested (CORNER_UX_U1_2026_10_10). Next: push and Publish |
| C13 | Researchers see the work in progress; the offering so far | Built and tested. Next: your paste (recommended) |
| U2 | Sparks across the corpus; a weekly team goal | Next: one read-only function; the goal is your decision |
| U3 (T2) | Learn, second round | Next: C10's kinds; the first story of a text |
| U4 (P2) | Sharing what is published | Your decision: pictures need a public path |
| U5 | The editors' queue, by value | Later |
| L2 | The first visit | P2 after a check in Hindi and Tamil, as before |
"""

CORNER = """

## 11. Ask the desk, guided (DOCS37_2026_10_10)

**Ask the desk, step by step:**
- It opens with one line on the working corpus so far, the team's, with no names.
- Then the text:
  - the list shows first the texts waiting for their first story;
  - "Where to begin" offers the ones with the most English;
  - "Continue with" offers the text chosen last time on this browser;
  - "Surprise me" picks one.
- No form appears until a text is chosen.
- Then "What would you like to make?": a story, a picture, a graphic novel, or everything.
- "Ready in this text" says what can be asked for now. "Set it up" fills that form and goes to it; the desk is still asked only by the form's own button.
- A story's passages, or a picture's, can be chosen in the text itself: "From here", "To here", "This one".

**Drafts:**
- Before C13, researchers see approved work only, so "Ready in this text" never offers them a proposed episode.
- After C13, researchers see the proposed episodes, drafts and novels in progress that the Corner already lets them act on. Readers who are not invited still see approved work only.
"""

SYNC = """

## 12. The Corner's strip and its email settings (DOCS37_2026_10_10)

In the Lovable Cloud SQL editor, read-only, one query per paste, from `docs/cloud/C13_checks_2026-10-10.sql`:
- **D1** gives the numbers of the Corner's strip ("the offering so far"), straight from the tables. The site calls `corner_offering()`, which the SQL editor (not signed in) may not.
- **D2** gives the email settings as saved, Reply-to included. The site does not show Reply-to back.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS36_2026_10_10"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS36_2026_10_10"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS36_2026_10_10"),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER, "DOCS36_2026_10_10"),
           (Path("docs/SYNC_COMMANDS_2026-10-09.md"), SYNC, "DOCS35_2026_10_09")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs37_" + stamp))
        t = p.with_name(p.name + ".tmp_docs37"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
