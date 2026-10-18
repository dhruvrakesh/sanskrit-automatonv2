#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs75_2026_10_18.py  DOCS75_2026_10_18

Records 18 Oct (evening): the scholarly editions on Srangam (EDITIONS_SITE_2026_10_18), an e-text's chapters
(EDITION_REFS_2026_10_18), the dashboard's menus (NAV_MENUS_2026_10_18); docs/EDITIONS_SITE_2026-10-18.md.

Appends to docs/PLATFORM_2026-10-04.md (section 78), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 65)
and docs/STATE_2026-10-18.md (its evening), each needing DOCS74_2026_10_18. Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs75_<date>), line endings kept.

  python scripts/patch_docs75_2026_10_18.py --check
  python scripts/patch_docs75_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS75_2026_10_18"

PLATFORM = """

## 78. The scholarly editions on Srangam; an e-text's chapters; the dashboard's menus (DOCS75_2026_10_18)

**18 Oct (evening).** docs/EDITIONS_SITE_2026-10-18.md. Decided: the GRETIL texts published with their credit (CC
BY-NC-SA 4.0, our English on the same terms); both top bars extended.
- **EDITIONS_SITE_2026_10_18:** scripts/publish_editions.py writes the editions of configs/editions.json into the
  Srangam repo (public/scholarly/<slug>.html, index.json): the scholarly export with a bar back to /editions, its
  credits, licence and canonical address; refuses a text in repair, a witness without source and licence, an edition
  without scholarly English. The Srangam kit (scripts/patch_srangam_editions_2026_10_18.py, docs/srangam/
  EDITIONS_2026-10-18/): /editions, "Editions" in the header, the Corpus menu, the sitemap, Phase AK.
- **EDITION_REFS_2026_10_18** (export_html.py): an e-text's chapters from its own references (the Devimahatmya's
  contents read 77, 81, 78, 82 ...); a sentence labelled by its verses' own references; the notes in reading order.
- **NAV_MENUS_2026_10_18** (dashboard_static.html): six menus; Scholarly English, Path, Redeem, BM2, Methodology,
  Srangam and the Hub linked.
- **The afternoon:** the Mallapurana's mended verses and the Ganita's 30 on the site (the mirror of 16:32 IST); the
  Sandilya's T2 19 mended of 21; the Surya's canary 19 of 20 passed; judge_review 289 of 4,591 marked (6%).

**Tests:** test_edition_refs_2026_10_18 (6), test_publish_editions_2026_10_18 (5), test_srangam_editions_kit_2026_10_18
(4), test_nav_menus_2026_10_18 (5); the site's editions-page.test.tsx (4).
"""

RUNBOOK = """

## The scholarly editions on Srangam (DOCS75_2026_10_18)

docs/EDITIONS_SITE_2026-10-18.md.
1. **The editions (the automaton):** `python scripts\\publish_editions.py` (the plan, free; it lists each edition and
   what it would write), then `python scripts\\publish_editions.py --apply`. An edition is turned on or off in
   configs/editions.json (`"enabled"`).
2. **The site (once):** in D:\\srangam-42267, `git pull --rebase --autostash`; `python "D:\\Sanksrit
   Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_editions_2026_10_18.py" --check`, then without --check;
   `npm run typecheck`; `npx vitest run`; `npm run build`.
3. **The commit (yours):** `git add -- public/scholarly` and the files the kit printed; `git commit`; `git push`. Then
   https://srangam.nartiang.org/editions.
4. **After a new scholarly run:** step 1 again, then `git add -- public/scholarly`, commit, push.
"""

EP = """

## Addendum 2026-10-18 (65) (DOCS75_2026_10_18)

| # | Item | State |
|---|---|---|
| X1a | The scholarly editions on Srangam | Built: publish_editions.py and /editions (EDITIONS_SITE_2026_10_18); the Devimahatmya first |
| X1b | The scholarly English in the reader and in search | To build (a site table, a mirror step, a reader change) |
| E3c | An e-text's chapters in its edition | Done: EDITION_REFS_2026_10_18 |
| U1 | The dashboard's top bar | Done: NAV_MENUS_2026_10_18 (six menus) |
| L1 | GRETIL's licence | Decided: published with credit, CC BY-NC-SA 4.0, our English on the same terms |
"""

STATE = """

## 10. The evening of 18 Oct (DOCS75_2026_10_18)

- **Srangam carries the scholarly editions:** public/scholarly/ and /editions (docs/EDITIONS_SITE_2026-10-18.md):
  the Devimahatmya first, the Surya and adhyayas 19 to 31 when they are complete. The site serves them as files: no
  database step. The scholarly English inside the reader and in search (X1b) is still to build.
- **The licence:** GRETIL's texts published with their credit; our English from them under CC BY-NC-SA 4.0.
- **The dashboard:** its top bar in six menus; every page linked.
- **The counts that moved:** the Mallapurana 80 verses by Sonnet on the site, the Ganita 30; the Sandilya 19 mended,
  waiting for the mirror; the Surya 20 of 515 in scholarly English; the screen's wrong meanings 289 of 4,591 (6%).
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS74_2026_10_18"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS74_2026_10_18"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS74_2026_10_18"),
           (Path("docs/STATE_2026-10-18.md"), STATE, "DOCS74_2026_10_18")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs75_" + stamp))
        t = p.with_name(p.name + ".tmp_docs75"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
