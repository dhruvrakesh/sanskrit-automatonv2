#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_runbook_export_editions.py  (2026-09-30)  RUNBOOK_EXPORT_2026_09_30

Docs only (RUNBOOK.md):
  1. Section 6 still says "both repos stay identical" and copies scripts into
     D:\\sanskrit-symphony\\automaton\\. That contradicts SOURCES_OF_TRUTH.md
     rule 2 (symphony holds cross-project docs only and MUST NOT contain a copy
     of any other project). On 2026-09-30 following section 6 made release.ps1
     commit an unrelated SOURCES_OF_TRUTH backup into symphony under the export
     commit message (7eb5acd). A superseded-notice is inserted under the heading;
     the old text is kept, not deleted.
  2. New section 3i, "Export editions": modes, file suffixes, the persisted
     Export As choice, the recovery command, and where the edition is recorded.

Run from the repo root:  python scripts/patch_runbook_export_editions.py [--check]
"""
from __future__ import annotations
import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

MARK = "RUNBOOK_EXPORT_2026_09_30"
RB = Path("RUNBOOK.md")

H6_OLD = "## 6. Update the CODE (both repos stay identical)\n"
H6_NEW = H6_OLD + """
> **SUPERSEDED 2026-09-30 (RUNBOOK_EXPORT_2026_09_30).** Do not copy scripts into
> `D:\\sanskrit-symphony`. SOURCES_OF_TRUTH.md rule 2: symphony holds cross-project
> docs and the register only, and must not contain a copy of any other project.
> Release this repo with section 6b (`scripts\\release.ps1`) and nothing else. The
> commands below are kept for history only.
"""

SECTION_3I = """

## 3i. Export editions (RUNBOOK_EXPORT_2026_09_30)

The Export button produces one of three editions, chosen by **Export As** in the left panel:

| Export As | File name | Contents |
|---|---|---|
| English only | `<doc>_<from>-<to>.html` | English |
| Hindi only | `<doc>_<from>-<to>_hi.html` | Hindi |
| Trilingual (Sa/En/Hi) | `<doc>_<from>-<to>_tri.html` | Sanskrit, English and Hindi side by side |

- **Export As is remembered** in the browser (localStorage) across reloads and restarts. Since EXPORT_MODE_VISIBLE_2026_09_30 each row button names the edition it will produce, and Export All asks for confirmation.
- **The edition is recorded** in `data/jobs.jsonl` as `"mode"` on export records (EXPORT_MODE_JOBLOG_2026_09_30). Older records have no `mode`; read the suffix of the output file instead.
- **"Trilingual export is broken"** on 2026-09-30 was a Hindi export: Export As had been left on Hindi. Check the newest files before debugging:

```powershell
Get-ChildItem exports\\*.html | Select Name, @{n='Edition';e={ if ($_.BaseName -match '_tri$') {'tri'} elseif ($_.BaseName -match '_hi$') {'hi'} else {'en'} }}, LastWriteTime |
  Sort LastWriteTime -Desc | Select -First 15 | Format-Table -Auto
```

- **Export from PowerShell** (reads the database only; safe while the dashboard runs):

```powershell
python scripts\\export_html.py --db data\\context.db --doc <DOC> --out exports --sanskrit --hindi --side-by-side --title "<DOC> - Sanskrit / English / Hindi"
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not RB.exists():
        print("FAIL: RUNBOOK.md not found. Run from the repo root.")
        return 2
    raw = RB.read_bytes()
    crlf = raw.count(b"\r\n")
    newline = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    n = src.count(H6_OLD)
    if n != 1:
        print("REFUSING TO WRITE: section 6 heading matched %d times, expected 1." % n)
        return 1
    src = src.replace(H6_OLD, H6_NEW).rstrip("\n") + SECTION_3I
    if args.check:
        print("CHECK OK. Nothing written.")
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    bak = RB.with_name(RB.name + ".bak_export_" + stamp)
    shutil.copy2(RB, bak)
    tmp = RB.with_name(RB.name + ".tmp_export")
    tmp.write_bytes(src.replace("\n", newline).encode("utf-8"))
    os.replace(tmp, RB)
    print("PATCHED RUNBOOK.md (backup %s)." % bak)
    return 0


if __name__ == "__main__":
    sys.exit(main())
