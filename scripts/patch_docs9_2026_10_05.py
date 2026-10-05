#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs9_2026_10_05.py  DOCS9_2026_10_05

Appends to docs/PLATFORM_2026-10-04.md (section 12), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: vignettes (scripts/stories.py) and the anthology.
Marker-idempotent per file, backup first.

  python scripts/patch_docs9_2026_10_05.py --check
  python scripts/patch_docs9_2026_10_05.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS9_2026_10_05"

PLATFORM = """

## 12. Vignettes: cited retellings for images and an anthology (VIGNETTES_2026_10_05, DOCS9_2026_10_05)

**Why.** A plate explains little on its own. A short retelling of the episode it shows, cited to the passages, does. The same tool can mine a book for its readable episodes and compile the approved ones into an illustrated, cited anthology.

**Why the care.** On 2026-10-05, image idea #86 (markandeya_purana) called the sage "Mrnjiga".
- The passages name him Samika (11.5, 11.8, 21.8).
- The one "Mrnjiga" is at 14.11, "saha putrena mrnjiga". This reading looks damaged: probably an OCR misreading of the name of Samika's son. The translation took it for the sage's name. The idea sampler then picked it up, because it sees only about 40,000 characters of a book.
- The same English has other errors where the printed Sanskrit is damaged: "dog's dwelling" (14.5) and "ash-buffalo" (10.9).
- translation_qa is 0.99 there. It measures the form of a translation, not whether it is faithful.

**What `scripts/stories.py` does:**
- **`mine`** reads the whole English of a book in chunks. It proposes episodes, each with a passage range, as candidates. It costs about $0.03-0.05 a book.
- **`write`** sends the episode's passages, Sanskrit plus English, to the model. It works from a mined candidate, one image, or every drawn image of a book (`--images`).
  - The model writes 120-220 words of English and the same story in Hindi, with a citation after every sentence.
  - It quotes one Sanskrit line verbatim, and gives editorial notes for damaged readings instead of guessing.
  - Cost: about $0.01 a story.
- **`verify`** runs without the API, and runs automatically after `write`. It checks that:
  - every sentence is cited;
  - all citations fall inside the range given;
  - the Sanskrit quote is found verbatim in the passage it cites;
  - every proper name appears in the cited passages.
  
  A draft that fails cannot be approved without `--force`.
- **`approve` / `retire`.** Nothing is published until a person approves it.
- **`anthology`** writes `exports/anthology_<date>.html` from the approved stories. Each story carries its plate, Sanskrit epigraph, English, Hindi and editorial notes. A Sources table lists every cited passage: the Sanskrit as printed and the machine English. `export_pdf.py` turns it into a PDF.
- **Under the plate.** With `export_html --images approved`, an approved story linked to a placed image prints under that image (`patch_vignettes`). The output is unchanged when no story is approved.

**Storage.** A new table, `doc_stories`, is keyed by (page, idx), as `doc_images` is. A re-ingest therefore does not orphan it. It is metered as kinds `story_mine` and `story`, and each call asks the budget first.

**Not yet built:**
- a Story panel on the `/images` cards (UI phase U1);
- using the mined episodes to place image ideas, instead of the 40,000-character sample;
- a fidelity judge on cited passages before approval.
"""

RUNBOOK = """

## Vignettes and the anthology (DOCS9_2026_10_05)

Every step is a dry run unless `--yes` is given.

- **Stories for drawn images:**
  - `python scripts\\stories.py write --doc <code> --images --max 6` (dry run), then add `--yes`.
  - `python scripts\\stories.py list --doc <code>`, then `show --id N`, then `approve --id N`.
  - A draft whose check failed needs `--force` after you have read it.
- **Mining episodes:**
  - `python scripts\\stories.py mine --doc <code> --max 12` (dry run), then add `--yes`.
  - Then `write --doc <code> --candidates --max 6 --yes`.
- **Anthology:**
  - `python scripts\\stories.py anthology --docs a,b --title "..."`.
  - Then `python scripts\\export_pdf.py exports\\anthology_<date>.html`.
- **Approve the story only after reading its notes.** Where the notes flag a damaged reading, fix the source passage first, through consensus or re-OCR. Never fix it in the story alone.
"""

EP = """

## Addendum 2026-10-05: vignettes and the anthology (DOCS9_2026_10_05)

| # | Item | State |
|---|---|---|
| 1.9 | Cited retellings for drawn images; episode mining; anthology export (`scripts/stories.py`, `patch_vignettes`) | Built 2026-10-05; first runs on markandeya_purana and Mallapurana |
| 2.8 | A Story panel on the `/images` cards (write, verify, approve from the page) | Next UI item, alongside U1 |
| 2.9 | Image ideas placed from mined episodes rather than a 40,000-character sample | After 1.9 has run on two books |
| 3.9 | A fidelity check of the cited passages before approval (judge_sample on those passages) | Before an anthology goes outside the team |
| S9 | Approved stories to the Srangam reader beside the passages (needs a site table; Lovable side) | After S4 |
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs9_" + stamp))
        t = p.with_name(p.name + ".tmp_docs9"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
