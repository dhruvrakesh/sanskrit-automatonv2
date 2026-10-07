#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs12_2026_10_07.py  DOCS12_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 15), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: versions for younger readers, graphic novels,
Ask without running heads, what the logs showed on 2026-10-07, and cloud C0/C1.
Marker-idempotent per file, backup first.

  python scripts/patch_docs12_2026_10_07.py --check
  python scripts/patch_docs12_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS12_2026_10_07"

PLATFORM = """

## 15. Younger readers, graphic novels, Ask without running heads; the cloud's first two steps (STORY_VARIANTS, NOVEL, ASK_NOISE, CLOUD_BRAIN C0/C1 - 2026-10-07; DOCS12_2026_10_07)

**Versions for younger readers** (`stories.py retell` / `variant`; table `doc_story_variants`).
- Made only from an APPROVED story. It is rewritten for children aged 8-12 (`young`) or readers aged 13-16 (`teen`) from the same passages, the approved retelling and its notes. One call, about $0.01.
- The rules are the story's. Every sentence is cited, names are kept exactly, and no fact is added. An unfamiliar word may get a few plain words of explanation. Hard moments are told plainly and gently. The version's notes say what was left out or simplified.
- It is checked by the same verify, inheriting the story's quotation. A failed check needs "Approve anyway".
- In books, the Children 8-12 and Readers 13-16 layouts use the approved version for that age where there is one, and the approved story otherwise.

**Graphic novels** (`scripts/novel.py`, new; table `doc_novels`; pictures in `data/images/<doc>/novel_<id>/`).
- **plan** (about $0.01): 8-16 pages from an approved story. Each page has a scene to draw, a caption with a citation after every sentence, its Hindi, and speech only where a passage gives a speaker words. A cast sheet fixes each recurring figure's look and iconography. The plan is checked like a story.
- **cast**: one reference picture per figure, at most 4.
- **draw**: one picture per page. The cast sheets go to the image model as reference images so figures stay the same, and nothing is lettered in the pictures.
- **Editing.** Editing a page's scene marks its picture stale; it is redrawn on the next draw.
- **Approval.** Pages are approved one by one, and the novel only when every page is approved and the plan's check passes (`--force` overrides).
- **build** writes `exports/novel_<title>_<date>.html` (cover, pages, sources), then a PDF. Unapproved novels carry PROOF.
- **Cost:** pictures at the image library's rate, about $0.09 at 1K and $0.13 at 2K. A 12-page novel with 3 cast sheets is about $1.4-1.9 before redraws.
- **On the page:** the Stories page has a "Graphic novels" tab, and approved story cards have a "Graphic novel" button.

**Ask without running heads.** On 2026-10-07, 46 markandeya running heads were tagged noise. Each was checked against the 12:15 backup: "<n> markandeya puranam ||" and "<n> astamo 'dhyayah ||". Ask retrieved passages without looking at text_type, and 31 of these heads carry translations such as "Markandeya Purana //". Keyword and semantic retrieval now skip noise and frontmatter, as the export and the publication gate already did. Semantic retrieval also over-fetches 64 more candidates, so that a cluster of identical heads cannot crowd out the verses. No vector is deleted.

**What the logs showed (2026-10-07).**
- **Ganita.** translate_both on Ganita_Yukti_Bhasa ran from 16:34 on 6 Oct to 12:16 on 7 Oct (70,884 s) and ended with exit code 0xC000013A (Ctrl+C or the console closing) at 709 of 1,460 verses, when the dashboard was restarted. Done rows are kept; a re-run resumes.
- **Sleep.** One call in the ledger took 44,771 s, about 12.4 hours: the machine slept overnight. The keep-awake request prevents idle sleep, not a closed lid or a manual sleep. The maintenance task logged missed runs that caught up at 06:22 and 11:22.
- **Translation speed.** The measured rate is 16-20 s per call with gemini-2.5-flash.
- **Maintenance skipped.** It skipped every run from 18:00 on 6 Oct, because that one job kept the dashboard busy. The brain was not updated for 18 hours.
- **jobs.jsonl** line 4 is an old interleaved write from June 2026. Readers skip it.

**The cloud, C0 and C1** (docs/CLOUD_BRAIN_2026-10-07.md, revision 2).
- C0 (`docs/cloud/C0_preflight_2026-10-07.sql`) is read-only: the pgvector version, whether halfvec is available, whether C1 objects already exist, and what C1 builds on.
- C1 (`docs/cloud/C1_corpus_brain_DRAFT_2026-10-07.sql`) creates `srangam_passage_vectors` (halfvec 768, HNSW), `srangam_stories`, RLS and `match_text_passages`. It was tested on PostgreSQL 16 + pgvector 0.8.0 on top of B1: 13 of 13 objects, and an anonymous caller sees published texts only. It is not applied to the live database.
- Vectors will be made in the cloud from published passages (C2), so no key and no 100 MB of SQL are needed.
"""

RUNBOOK = """

## Younger readers, graphic novels, cloud pre-flight (DOCS12_2026_10_07)

- **A version for younger readers.** On an approved story's card, under "For younger readers", click "Write version" (about $0.01). Read it, Edit if needed, then Approve. Books for those ages use it.
  - From the command line: `python scripts\\stories.py retell --id N --audience young --yes`, then `python scripts\\stories.py variant --id N --audience young --action approve`.
- **A graphic novel.** In Stories, open "Graphic novels", choose the story, pages and readers, then "Plan the pages" (about $0.01).
  - Read every page and correct captions and scenes (Save checks them).
  - "Draw cast", then "Draw pages", then Approve each page, then "Make the book".
  - From the command line, `python scripts\\novel.py plan --story N --pages 12 --yes`, then `cast --id K --yes`, `draw --id K --yes`, `approve-page`, `approve`, `build`.
- **Before restarting the dashboard,** look at the header: a running translation is killed by a restart, and it resumes when started again. Keep the machine awake (lid open, sleep off) for long runs.
- **Cloud.** Paste `docs\\cloud\\C0_preflight_2026-10-07.sql` into the Lovable Cloud SQL editor one query at a time (read-only) and keep the results. C1 is applied only after that, and only after the file has been read through.
"""

EP = """

## Addendum 2026-10-07 (2): younger readers, graphic novels, cloud C0/C1 (DOCS12_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.15 | Versions for children 8-12 and readers 13-16 (`retell`, `variant`), used by the books for those ages | Built 2026-10-07 |
| 2.16 | Graphic novels: cited plan, cast sheets as references, pages, per-page approval, book (`novel.py`, "Graphic novels" tab) | Built 2026-10-07 |
| 1.11 | Ask skips noise and frontmatter (running heads) | Built 2026-10-07 |
| 1.12 | Maintenance runs while a long translation is going (embeddings serialised behind it by SQLite, not skipped) | Open: needs a measured test of concurrent writes first |
| 1.13 | Delete the vectors of noise rows (`build_embeddings --prune`) | Open; Ask already filters them |
| C0 | Read-only pre-flight (`docs/cloud/C0_preflight_2026-10-07.sql`) | Ready to run |
| C1 | Vectors, stories, RLS, `match_text_passages` (`docs/cloud/C1_corpus_brain_DRAFT_2026-10-07.sql`) | Drafted and tested on PostgreSQL 16 + pgvector 0.8.0; not applied |
| C2 | Edge function `embed-published-passages` in the Srangam repo | Next, after C1 |
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs12_" + stamp))
        t = p.with_name(p.name + ".tmp_docs12"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
