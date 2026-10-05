#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs10_2026_10_05.py  DOCS10_2026_10_05

Appends to docs/PLATFORM_2026-10-04.md (section 13), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: the Stories page (STORIES_UI_2026_10_05) and
gap accounting + running heads (GAPS_2026_10_05). Marker-idempotent per file, backup first.

  python scripts/patch_docs10_2026_10_05.py --check
  python scripts/patch_docs10_2026_10_05.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS10_2026_10_05"

PLATFORM = """

## 13. The Stories page; gaps; running heads (STORIES_UI_2026_10_05, GAPS_2026_10_05, DOCS10_2026_10_05)

**Stories page (`/stories`, `scripts/stories_web.py` + `stories_static.html`).** The front end of `stories.py`. It is registered from `dashboard.py` in its own try/except, after the Shelf, so a fault in it cannot stop the dashboard.
- Per text, one card per story: its plate (thumbnail from `/api/images/thumb`), status, check result, the Sanskrit epigraph, English and Hindi with clickable citations, editorial notes, and the problems the check found.
- A citation opens a drawer with the passages of the episode: Sanskrit as printed and the machine English, the cited ones shaded. Devanagari and IAST display properly here, which the PowerShell 5.1 console cannot do.
- Edit (title, Hindi title, English, Hindi, quotation and its ref, notes) re-runs the check. An edited story returns to draft and must be approved again; status and id are not editable.
- Approve follows the CLI rule: a failed or missing check shows only "Approve anyway". Retire and Restore are reversible.
- Find episodes, Write (one, drawn images, found episodes), Build anthology and Make PDF run as dashboard jobs (kind `stories`, general queue) through `launch()`, so they appear in the job list and `jobs.jsonl`; every paid call is still metered and asks the budget.
- The page never creates a database: a wrong path answers an error.

**verify, firmed up.** A citation written after the full stop ("... fled. [11.5] Later, he ...") had glued two sentences together. The first word of the second ("Later", "Simultaneously", "Enraged", "Despite") was then reported as an unknown name, and an uncited sentence after such a citation passed as cited. The split now also breaks after "]". A capital that opens quoted speech or follows a colon is not taken for a name. IAST words are still always checked.

**Prompt rule (6).** A translated detail that makes no sense in the story (story #1's "ash-buffalo", from a damaged line) is left out and described in the notes with its tag. The prompt hash stored per story records the change; stories written before it are not changed.

**Gaps (corpus_status).** A passage without English or Hindi is a gap, not work to do, when translate_passages already tried it and logged unusable output in `data/translate_outcomes.jsonl` (any cause but `salvaged`; matched by doc, lang, page, idx), or when its OCR quality_score is above 0 and below 0.35 (skipped by `--min-quality`). Gaps count with the lacunae against `--lacuna-ok`, as a share of all passages. Within it they are a note. Above it the text stays NEEDS-TRANSLATION with no paid command, because a re-run returns the same. New: `--outcomes`, and CSV/JSON columns `en_gap` and `hi_gap`.

**Running heads (classify_noise `--running-heads`).** An untranslated first or last line of a page whose text, with digits and punctuation ignored, is the first or last line of at least 3 pages, at most 60 characters long. A line with a danda (verse, refrains included), a speaker line (... uvaca) and a line that is translated more often than not are never tagged. It is a dry run until `--apply`, and reversible.

**Still true:** translation_qa measures form, not fidelity. An approved story is only as faithful as the passages it cites; damaged readings are fixed in the source (consensus or re-OCR), not in the story alone.
"""

RUNBOOK = """

## Stories page, gaps, running heads (DOCS10_2026_10_05)

- **Stories:** open `http://127.0.0.1:5057/stories` and pick the text.
  - Read each card's notes and problems.
  - Click a citation to see the passages.
  - Edit if needed (the check re-runs), then Approve.
  - Use the page, not PowerShell, for any edit with Devanagari or IAST.
- **After a prompt or verify change:** press "Check again" on the old drafts (free), and "Rewrite" a story the notes or problems condemn (about $0.01).
- **A text stuck at NEEDS-TRANSLATION with a few rows that never translate:**
  - First run `python scripts\\corpus_status.py --doc <code>`. Gaps within the allowance now show as a note.
  - Then `python scripts\\classify_noise.py --doc <code> --running-heads` (dry run) and read the listed lines.
  - Only then add `--apply`, with the dashboard idle and after a backup.
"""

EP = """

## Addendum 2026-10-05 (2): Stories page, gaps (DOCS10_2026_10_05)

| # | Item | State |
|---|---|---|
| 2.8 | Story review in the browser: write, check, edit, approve, anthology, PDF (`/stories`) | Built 2026-10-05 as its own page (not a panel on `/images`); cards link to the image library |
| 2.10 | verify: sentence split after a citation; speech openers | Built 2026-10-05 (STORIES_UI) |
| 2.11 | Untranslatable passages counted as gaps; running-heads tagging | Built 2026-10-05 (GAPS); first use markandeya_purana |
| 3.10 | Story fidelity: a judge on the cited passages, and a reader's correction loop back to the passage | Open (follows 3.9) |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


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
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs10_" + stamp))
        t = p.with_name(p.name + ".tmp_docs10"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
