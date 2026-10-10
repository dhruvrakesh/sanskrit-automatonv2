#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs39_2026_10_10.py  DOCS39_2026_10_10

Records the afternoon of 10 Oct:
- C13 applied and checked, the guided Corner live, Reply-to still empty;
- the releases (dd674a5a, hub a2b2315);
- Karan Aagama's OCR consensus run;
- the report "jobs are not queued, the console is not live" and its repair: LIVE_LOG_2026_10_10 and
  HUB_V2_1_2026_10_10. docs/LIVE_LOG_2026-10-10.md has the findings.

Appends to docs/PLATFORM_2026-10-04.md (section 42), RUNBOOK.md and docs/ENTERPRISE_PATH_2026-10-04.md
(addendum 29), each needing DOCS38_2026_10_10, and to docs/RESEARCHERS_CORNER_2026-10-09.md (section
12), needing DOCS37_2026_10_10.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs39_<date>), line endings kept.

  python scripts/patch_docs39_2026_10_10.py --check
  python scripts/patch_docs39_2026_10_10.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS39_2026_10_10"

PLATFORM = """

## 42. C13 live; every press makes a run, and the console says what it did (DOCS39_2026_10_10)

**10 Oct, afternoon (IST). Applied and checked.**
- **Releases.** Automaton dd674a5a (DESK_HEAL, HUB_V2, DOCS38). The hub's own repository a2b2315 is
  pushed (bd85c23..a2b2315).
- **DESK_HEAL is on disk.** Its checksums match. The page and maintenance have it; `dashboard.py` is
  not restarted yet (the OCR runs), so `/api/health` still answers 404.
- **C13, 13:01-13:04, one query per paste:**
  - P1: 5 rows, c13 false, helper false, old_line 1.
  - The script: "Query succeeded".
  - V1: 5 rows, c13 true, old_line false, security_definer true, anon false, authenticated true.
  - V2: `corner_offering()` security_definer, authenticated only. `corpus._sees_drafts()` has no
    grants of its own.
  - V3: Kanika and Parth, researcher, reader mode readers, sees_drafts true.
- **The live site, checked from a browser.**
  - Before C13, `corner_offering` answered 404 and the strip counted from the texts.
  - After: 200, and the strip reads "51 texts in English, 22,368 passages translated, 27 stories told,
    18 pictures, 1 request done this week. 47 texts are waiting for their first story."
  - The guided Corner (Srangam d1752d4) is published.
- **D2, 13:04 and 13:38:** `mail_reply_to` is empty (last changed 01:56 UTC). `mail_enabled` is true
  and `mail_from` is "Srangam desk <desk@nartiang.org>".
- **Karan Aagama's OCR consensus (13:05-16:31):**
  - 183 pages queued; 168 vision pages written.
  - Measured $0.00017-0.00038 a page on the first pages, against the $0.00319 estimate.
  - Merge: 183 pages. Drift: 38 current, 145 stale. Page 0026 to redo.
  - Not re-ingested: that is a decision (docs/LIVE_LOG_2026-10-10.md section 4).

**Reported at 16:31:** "queueing jobs from the Library or the dashboard does not queue them; the
console does not seem live."

**Found** (docs/LIVE_LOG_2026-10-10.md section 2): every press made a job, and every job ran.
- Ganita (both, then Hindi) ran: 7 of 186 translated, 185 below the OCR quality bar.
- Vasishtha Dhanur Veda ran: 1 of 1.
- Hayashirsha, Natyasastra, Karan and the Tantric Texts were held by the OCR-debris guard, in
  0.2-0.3 s.
- Nothing said so:
  - the dashboard's `communicate()` kept a job's output until its end;
  - jobs started outside the page were never followed;
  - a 0.3 s run fell between two looks;
  - the Log knew only [OK] and [FAIL].
- The Log also went silent past 6,000 characters, and the Live tab showed NaN.

**LIVE_LOG_2026_10_10** (`scripts/patch_live_log_2026_10_10.py`):
- `dashboard.py` (on a restart): `_run_job` reads output while the job runs (two readers), and
  `/api/job` shows the last 200 lines.
- The page (on a reload):
  - the Log follows every job, wherever it was started;
  - outcomes read [HELD] (with the consensus command), [NOTHING], [OK] (N of M), [STOPPED] or [FAIL];
  - short runs are caught from the job history;
  - the Log opens with the last five runs, and new lines keep coming past 6,000 characters;
  - the Live tab shows the time a run has taken.

**HUB_V2_1_2026_10_10** (`scripts/patch_hub_v2_1_2026_10_10.py`): the engine card lists the last runs
and what each did, the texts held for an OCR repair, and page N of M for a running OCR.

**Tests:** `tests/test_live_log_2026_10_10.py` (9) and `tests/test_hub_v2_1_2026_10_10.py` (6). The
DESK_HEAL tests, the hub v2 tests and the other dashboard tests still pass.
"""

RUNBOOK = """

## Every press makes a run; the console says what it did (DOCS39_2026_10_10)

1. **The page:**
   - `python scripts\\patch_live_log_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard with Ctrl+F5.
   - The Log opens with the last runs. A press in the Library shows in it within 8 s, as what it did.
2. **The hub:**
   - `python scripts\\patch_hub_v2_1_2026_10_10.py --check`, then without `--check`.
   - Close the hub's console and run `start-hub.bat`.
3. **A run marked [HELD]** is the OCR-debris guard, not a fault.
   - Plan the repair: `python scripts\\ocr_consensus.py --doc <code> --threshold 101 --include-unassessed`.
     This is a plan, with no spend; add `--yes` to run vision.
   - Re-ingesting a repaired text replaces its passages and their translations. Do it only while the
     dashboard is idle, after `scripts\\db_backup.py`, and only for a text you have decided on
     (docs/LIVE_LOG_2026-10-10.md section 4).
4. **Restart the dashboard** when idle, to bring in DESK_HEAL's Library and LIVE_LOG's live output.
   While an OCR runs:
   - press Pause All;
   - run `scripts\\restart_dashboard.ps1`;
   - press Full on the OCR's row. It resumes from the missing pages.
"""

EP = """

## Addendum 2026-10-10 (29) (DOCS39_2026_10_10)

| # | Item | State |
|---|---|---|
| C13 | Researchers see the work in progress; the offering so far | **Live** (13:04), checked P1, V1-V3; the strip reads from the database |
| U1 | The Corner, guided | **Live** (Srangam d1752d4, published) |
| R6, A3 | Email from nartiang.org | Reply-to still empty (D2). Next: set it, then a first email |
| D3 | Every press visible: the Log follows every job and says what it did; live output | Built and tested (LIVE_LOG_2026_10_10). Next: patch, reload; live output on the restart |
| H3 | The hub's last runs, held texts, OCR progress | Built and tested (HUB_V2_1_2026_10_10). Next: patch, restart the hub |
| O1 | Karan Aagama | Consensus run: 145 of 183 pages stale. Your decision: re-ingest (replaces 1,603 English and 1,425 Hindi) or translate the rest with `--allow-debris` |
| O3 | Natyasastra, Tantric Texts | Held; nothing to lose. Next: consensus plan, then vision, re-ingest, translate |
| O4 | Hayashirsha | Held; 1,174 Hindi exist. Your decision, as O1 |
| U1.1 | Two editions with one title in the Corner's list (Vasishtha and Shiva Dhanur Veda) | Next: tell them apart |
"""

CORNER = """

## 12. C13 live (DOCS39_2026_10_10)

- **C13 was applied on 10 Oct at 13:04 and checked** (P1, V1, V2, V3):
  - Kanika and Parth (researchers, reader mode readers) now see the proposed episodes, drafts and
    novels in progress that the Corner lets them act on.
  - Readers who are not invited still see approved work only.
- **The strip at the top of Ask the desk reads from the database** (`corner_offering()`): "51 texts in
  English, 22,368 passages translated, 27 stories told, 18 pictures, 1 request done this week. 47
  texts are waiting for their first story."
- **Still to do:**
  - Reply-to: D2 shows it empty; enter an inbox you read and press Save.
  - A first email: ask for "An idea for a cover" ($0.01).
  - Two editions each of Vasishtha and Shiva Dhanur Veda share a title in the list (38 and 39
    passages; 19 and 25). U1.1 is to tell them apart.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS38_2026_10_10"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS38_2026_10_10"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS38_2026_10_10"),
           (Path("docs/RESEARCHERS_CORNER_2026-10-09.md"), CORNER, "DOCS37_2026_10_10")]


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs39_" + stamp))
        t = p.with_name(p.name + ".tmp_docs39"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
