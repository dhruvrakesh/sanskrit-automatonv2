#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs11_2026_10_07.py  DOCS11_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 14), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: pictures from stories, books from the Stories
page (reading book, Booksmith edition), the brain's editorial index, running heads
v2, and the next phases (age-group retellings, graphic novels, the cloud brain -
docs/CLOUD_BRAIN_2026-10-07.md). Marker-idempotent per file, backup first.

  python scripts/patch_docs11_2026_10_07.py --check
  python scripts/patch_docs11_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS11_2026_10_07"

PLATFORM = """

## 14. Pictures from stories, books, and the brain's editorial index (STORY_BOOKS, BOOKSMITH_STORIES, BRAIN_ITEMS, HEADS2 - 2026-10-07; DOCS11_2026_10_07)

**The "Write story" button worked before this change.** The job log shows story #5 written at 19:45 on 2026-10-05 (30.9 s, ok). But its only feedback was a line at the top of a page the reader had scrolled away from. Now the job list stays in the sticky header and the card shows that its job is running. When the job finishes, the list refreshes, the card flashes, and a toast gives the result. Several jobs can run together.

**Pictures from a story.**
- "Propose image" runs `stories.py illustrate`. It makes one gemini-2.5-flash call (about $0.003), working from the passages, the retelling and the editorial notes. It never depicts what the notes doubt. The idea is stored as an ordinary image-library idea (status `brief`) and linked to the story.
- "Draw it" approves the idea and generates it through the image library's own routes: about $0.09 at 1K, $0.13 at 2K.
- "Approve image" approves the picture, keeping one approved version per lineage, and relinks the story.
- "Redraw" makes a new version. The card always shows the newest version that is not retired.
- "Drop idea" retires an idea so that another can be proposed.

**Books (the "Make a book" tab).** Choose texts, then stories, then their order, then the readers. Approved stories only, unless Proof is ticked.
- *Reading book* (`stories.py book`): HTML with each story's own plate, followed by a PDF through `export_pdf.py`.
  - Young readers: large type, the picture first, no citation marks and no notes.
  - General: citations shown as small marks, notes, and an English source table.
  - Scholars: adds the Sanskrit of every cited passage.
  - The readers setting changes the layout, not the wording.
- *Booksmith edition*: `stories.py booksmith-source` writes a Booksmith witness with one chapter section per story. In each, `vref` carries the number, title, book and range; `sa` is the quotation; `en` and `hi` are the retelling; the footnotes are the cited passages and the editorial notes. `booksmith_build.py --source-html ... --mode story` then builds it with reading languages sanskrit, english and hindi. `--plate-ids` passes approved pictures in order.
  - Verified on 2026-10-07 against a copy of Booksmith 0.2.1: init, ingest (mode=leaf), audit (0 issues), and a build with one plate produced book.pdf.
  - Booksmith spaces its plates evenly through the book (at most 12) rather than placing each beside its story. For a picture beside every story, use the reading book.

**The brain's editorial index (`brain_items.py`).**
- What it indexes: approved and draft stories, found episodes, and drawn images. It uses the same embedding model as the passages.
- How it is kept current: incrementally, by text hash. Retired items are dropped, and a status change alone is not re-embedded.
- How Ask uses it: Ask (`/api/ask`) keeps its passage retrieval unchanged. When that retrieval is semantic, the same question vector also finds up to 3 approved items with cosine at least 0.55. No second call is made. The items are labelled EDITORIAL and given after the passages, and the system prompt says they are not scripture. Drafts are used only with SA_BRAIN_DRAFTS=1.
- How it is updated: by `maintenance_runner.ps1` step b2 on every run (a failure is logged and skipped), and by the "Update brain" button on `/stories`.
- Cost: about $0.00002 an item.

**Running heads v2.** markandeya_purana prints its running head as a page number, the title and a double danda. The first rule refused every line with a danda, so it found nothing. A danda is now allowed only in a short first line of a page that carries a page number (at most 24 Devanagari letters). A group whose page numbers change is a running head even where some copies were translated; `--include-translated` tags those copies too. Refrains, speaker lines and long lines are never tagged.

**Already true (2026-10-05):** the passage index is updated every three hours by the Windows maintenance task (qa_scan, build_embeddings, extract_entities), which runs only when the dashboard is idle. The 18:00 run embedded 56 new passages for $0.0015.
"""

RUNBOOK = """

## Pictures, books and the brain from the Stories page (DOCS11_2026_10_07)

- **A picture for a story** (in Review): Propose image (about $0.003), then read the idea. Then Draw it (about $0.09-0.13), then Approve image. Edit the idea in `/images` when the iconography is wrong. Drop it to start again.
- **A book** (in Make a book):
  - Tick the texts, then the stories, then set the order, the title and the readers.
  - "Make reading book" writes `exports\\book_<title>_<date>.html` and its PDF.
  - "Booksmith edition" builds through Booksmith. It writes the sidecar `exports\\booksmith\\stories-<title>__story.json`, and the PDF link appears under Recent books.
- **The brain.** The chip in the header says how many items are not yet in the Ask index. Maintenance adds them every run; "Update brain" adds them now.
- **Running heads**, in order:
  - `python scripts\\classify_noise.py --doc <code> --running-heads` (dry run). Read the listed lines.
  - Back up.
  - Add `--apply`, and add `--include-translated` to also tag the translated copies.
  - Then run `corpus_status --doc <code>`.
"""

EP = """

## Addendum 2026-10-07: pictures, books, brain items; next phases (DOCS11_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.12 | Pictures from stories: propose, draw, approve and redraw on `/stories` | Built 2026-10-07 |
| 2.13 | Book composer: choose texts and stories, order, readers; reading book HTML and PDF; Booksmith edition | Built 2026-10-07 (Booksmith verified on a copy of 0.2.1) |
| 1.10 | Editorial index for Ask (`brain_items`): stories, episodes and images; maintenance step b2 | Built 2026-10-07 |
| 2.14 | Running heads with a page number and a danda (markandeya) | Built 2026-10-07 |
| 2.15 | Retellings per age group (`stories.py retell --audience young`): a variant row with the same checks; citations kept in the data and hidden in the young layout | Next. About $0.01 a story |
| 2.16 | Graphic novels of 10-15 pages from a story or a text (see below) | After 2.15 |
| C0-C4 | The cloud brain on the existing Supabase (Lovable Cloud): vectors as halfvec(768), approved stories and images, an Ask Edge Function. See docs/CLOUD_BRAIN_2026-10-07.md | After the audit Q1-Q6 |

**Graphic novel, as designed (2.16).** Nothing in it is drawn or captioned without a passage behind it.
- **novel plan --story N --pages 12** makes one call (about $0.01). Inputs: the story's passages, the approved retelling and its notes. Output: the pages and their panels, each with a scene, a caption of at most 25 words with its [page.idx] citation, and dialogue only where a passage quotes speech. It also writes a cast sheet that fixes each figure's iconography. The output is checked by the existing verify rules: citations present and in range, and names found in the cited passages.
- **novel cast** draws a reference sheet for each main figure (2-4 images).
- **novel draw** draws one image per page, giving the cast sheets to the image model as reference images so the figures stay the same from page to page. No lettering goes in the images. Captions are typeset in HTML, because script drawn by an image model is unreliable, Devanagari above all.
- Layout is an HTML comic template (page image and caption boxes), then a PDF through `export_pdf.py`. A person approves each page.
- **Cost:** about $1.4 to $1.9 for 12 pages at 1K-2K (13 to 16 images at $0.09-0.13, plus the plan), plus redraws. Budget-gated, a dry run first.
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs11_" + stamp))
        t = p.with_name(p.name + ".tmp_docs11"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
