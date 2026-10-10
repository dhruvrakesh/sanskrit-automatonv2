#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs36_2026_10_10.py  DOCS36_2026_10_10

Records the morning of 10 Oct (worker 1.2 live, C10b and C12 applied, Srangam 852d852 published, the
corner-mail function not yet deployed) and the release NAV_RBAC_2026_10_10: the working corpus and
Learn in the site's navigation, by role.
Appends to docs/PLATFORM_2026-10-04.md (section 39), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 26) and docs/RESEARCHERS_CORNER_2026-10-09.md (section 10). Needs DOCS35_2026_10_09 in each.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs36_<date>), line endings kept.

  python scripts/patch_docs36_2026_10_10.py --check
  python scripts/patch_docs36_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS36_2026_10_10"
NEEDS = "DOCS35_2026_10_09"

PLATFORM = """

## 39. C10 and email switched on; the corpus in the navigation (DOCS36_2026_10_10)

**10 Oct, morning (IST).**
- 07:22: the mirror run ended done (392 groups equal); pictures 114 of 114 on Drive.
- 07:28: desk worker 1.2 took its first round (md5 ffee71c3ed7e15675f349c2b3d838cee). Its mail flush answered "corner-mail is not deployed": the edge function is in the repo but Lovable has not deployed it yet.
- docs35 released as 5717c590.
- **C10b in the SQL editor:** P1 `true | true | true | true | false | false`, then the paste.
  - V1: 24 kinds, as listed.
  - V2: `corner_ideas` and `corner_retired_pictures` for authenticated only.
  - V3: `_clean` and `_estimate` owner-only, with c10b true.
- **C12 in the SQL editor:** P1 `... | settings_key_check | true`, then the paste.
  - V1: `mail_prefs` and `outbox` with RLS on and no grants.
  - V2: 10 functions as expected.
  - V3: the seven-key CHECK, mail_enabled false, the trigger enabled.
- `RESEND_API_KEY` was added in Lovable Secrets on 9 Oct.
- Srangam 852d852 (19 files) was pushed and published.
  - The live entry `index-RqufY-rO.js` (450,224 characters) loads the toast hosts lazily.
  - The Corner asks `corner_mail_prefs` (200).

**Found:** the header linked to the working corpus nowhere.
- Researchers reached it only through the invitation page, the sign-in redirect or a typed address.
- Learn was reachable only from the corpus's own tabs.
- The header showed "Admin" to everyone.

**NAV_RBAC_2026_10_10 (Srangam, no database change):**
- A "Corpus" menu with Learn and the Corner (header, phone menu sheet, phone bottom tab), for whoever may read the corpus.
  - Roles researcher, admin and super_admin decide with no request.
  - Any other signed-in account asks `corpus_reader_allowed()` once.
- "Admin" for admins only; "Sign in" while signed out.
- The admin sidebar gets a "Working corpus" group.
- The corpus home says where to start.
- Tests: 11 new; site suite 294 tests, 291 passing; the 3 known environment-only failures remain.
- Entry +4.6 kB (+1.3 kB gzip).
"""

RUNBOOK = """

## The corpus in the navigation; mail still to switch on (DOCS36_2026_10_10)

1. **Srangam:**
   - `patch_srangam_nav_rbac_2026_10_10.py --check`, then without `--check`;
   - typecheck, tests and build;
   - commit the paths it prints;
   - pull before you push; push; Publish.
2. **Look, signed in as a researcher:** the header shows "Corpus" (with Learn and the Corner) and no "Admin". Signed out it shows "Sign in". On a phone the bottom bar has a "Corpus" tab.
3. **Email:**
   - Lovable: deploy the edge function corner-mail without changing its code.
   - The next desk round's log has `"mail": {"configured": true, ...}`.
   - Then Corner -> Settings: Reply-to, then Email on.
"""

EP = """

## Addendum 2026-10-10 (26) (DOCS36_2026_10_10)

| # | Item | State |
|---|---|---|
| C10 | The Corner level with the desk | Live: worker 1.2 (07:28), C10b, Srangam 852d852 |
| R6, A3 | Email from nartiang.org | Database and site live; RESEND_API_KEY added; next: Lovable deploys corner-mail, then Reply-to and Email on |
| L2 | The first visit | P3 and P4 live (852d852). Next: P2 after a check in Hindi and Tamil |
| N1 | The working corpus and Learn in the navigation, by role | Built and tested (NAV_RBAC_2026_10_10). Next: push and Publish |
| T2 | Learn quests for C10's kinds | Next |
"""

CORNER = """

## 10. How researchers find the corpus, the Corner and Learn (DOCS36_2026_10_10)

**Signed in as a researcher, an admin or the super admin:**
- the header has a "Corpus" menu: Library, Stories, Names, Pictures, Graphic novels, Researchers' Corner, Learn, Published texts;
- on a phone, the menu sheet has the same section and the bottom bar a "Corpus" tab;
- admins also find Library, Corner and Learn in the admin sidebar.

**Signed out,** the header offers "Sign in". After signing in, an admin goes to the admin pages and anyone else to the corpus.

The database still decides who reads: the menus only follow it.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if NEEDS.encode() not in raw:
            print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, NEEDS)); return 1
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    if not todo:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs36_" + stamp))
        t = p.with_name(p.name + ".tmp_docs36"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
