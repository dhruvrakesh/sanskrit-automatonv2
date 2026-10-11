# The repair path, there and then (2026-10-10, evening)

Marker: **REPAIR_PATH_2026_10_10**, in `scripts/repair_text.py` (new), `scripts/dashboard.py` and
`scripts/dashboard_static.html`. Builds on DESK_HEAL_2026_10_10 and LIVE_LOG_2026_10_10.

## 1. What was asked

"In case re-OCR is needed to start translation, rather than crashing, the resolution path and action
should be there and then; else we discard that PDF and look for a better resolution. We need a clean
corpus with the distillate of the best quality translations: our own critical-edition brain for the
texts it ingests."

## 2. Why a translation stops

A translation stops for two reasons. Both are about the scan, not the translator:

- **Held by the OCR-debris guard** (`translate_passages.py`, TRANSLATE_DEBRIS_GUARD_2026_10_04,
  exit 3). More than 30% of the verses carry Tesseract debris (Latin letters inside the Devanagari),
  less than half come from vision OCR, and the page PDFs are in the inbox. Held now: Hayashirsha,
  Natyasastra (2015_368408), Karan Aagama and the Tantric Texts.
- **Most of what is left is below the OCR quality bar** (`quality_score` < 0.35), so it is not sent.
  Example: Ganita Yukti Bhasa, where 185 of 186 were below the bar.

Until now each run ended with a command to copy (`ocr_consensus.py ...`), and re-ingesting was five
more commands. Now the next step is a button, where the stop is seen.

## 3. The path

`scripts/repair_text.py` is the one place the advice lives. Each step ends with two lines:
- `VERDICT:` says what it found;
- `NEXT:` says the next step.

The dashboard offers NEXT as a button.

| Step | Command | What it does | Writes |
|---|---|---|---|
| Assess | `python scripts\repair_text.py --doc X` | Counts passages, English, Hindi, vectors, pictures and stories; debris and vision shares; page PDFs, Tesseract, vision and repaired pages; the last drift check. Says why the text stops, and what next. | nothing (database read-only) |
| Repair the scan | `... --repair [--max-usd 1.00]` | `ocr_consensus.py --yes`: vision OCR on the queued pages (every page when held: threshold 101), audit, merge, drift. If the meter's estimate is above the cap, it spends nothing and names the cap it needs. | page files only (`data\raw_vision`, `data\raw_merged`, `data\ocr_consensus`) |
| Use the repaired text | `... --use-repaired [--replace N]` | Back up (`db_backup.py`), then `wipe_doc.py`, then `ingest_jsonl_fast.py` (from the repaired pages), then `classify_doc.py --apply`, then a drift check, then assess again. | the database |
| Set aside | `... --set-aside "why"` | Records that the scan cannot be repaired here: a better scan is wanted. The PDFs and page files are kept. | `data\source_verdicts.jsonl` |
| Restore | `... --restore` | Undoes Set aside. Use it when a better scan is in the inbox. | `data\source_verdicts.jsonl` |
| List | `... --list` | Lists the texts set aside. | nothing |

**Use the repaired text** refuses, and changes nothing, unless:
- the repaired text covers every page, and every repaired page file reads;
- it loses nothing, or `--replace N` names the N English translations it replaces;
- the dashboard runs no other database writer. As the dashboard's own job it runs under the translate
  lock;
- the backup was made.

If a step fails after the wipe, it prints the backup's path and how to put it back.

"Nothing to lose" means:
- at most 5 English translations;
- no Hindi;
- no pictures;
- no stories.

## 4. Where the path is offered

The dashboard's Python file needs a restart (when idle). The page needs only a reload.

- **The Library.**
  - **A held text, or one that left most of its text below the OCR bar.** The card's note gets a bar
    under it: *Repair path: what now?* (assess, free), *Set aside*, and *details*. The assessment's
    verdict shows under the bar, with the next step as a button, for example:
    - *Repair the scan (at most $1.00)*;
    - *Use the repaired text (replaces 1603 English)*;
    - *Set aside: a better scan is wanted*.
  - **A text set aside** shows why, and *Restore*, in place of *Finish EN* and *Add Hindi*.
  - **Texts with no English yet that a run could not translate**, such as Natyasastra, were not listed
    before. They are now listed at the end, under *Waiting for a better source*, with the same bar.
- **`/repair/<doc>`, the text's repair page.** It shows:
  - its passages, English and Hindi;
  - the four steps;
  - the last runs' notes;
  - the bar;
  - the live output of each run.

  It opens with a free assessment.
- **The dashboard's Log.** These runs are followed by a line that opens the text's repair page:
  - a run *[HELD]* by the guard;
  - a run that left most of its text below the OCR bar;
  - a repair step's outcome (*[REPAIR]*, with its verdict).

  Until the dashboard is restarted with the path, the line gives the command instead.
- **`POST /api/repair`** `{doc, step, max_usd?, replace?, reason?}`. Each step is a run of
  `repair_text.py --from-dashboard`.
  - `use` is kind `repair_use`, under the translate lock. The other steps are kind `repair`.
  - One press spends at most $5.00. Above that, run it by hand.
  - `GET /api/repair` answers when the path is there.

## 5. The four held texts

These counts are from the backup of 10 Oct (docs/LIVE_LOG_2026-10-10.md section 4).

| Text | English | Hindi | Pictures | What the path will say | Your decision |
|---|---|---|---|---|---|
| Natyasastra (2015_368408) | 0 | 0 | 0 | the scan can be repaired: vision on its pages | none: nothing to lose. Repair, then Use. |
| Tantric Texts (Avalon) | 1 | 0 | 0 | as above | none: nothing to lose |
| Hayashirsha Pancaratra | 158 | 1,174 | 0 | repair; then "replaces 158 English" | yes: the 1,174 Hindi rows point at the old passages |
| Karan Aagama | 1,603 | 1,425 | 14 (2 approved) | repaired already (145 of 183 pages stale): "replaces 1603 English" | yes, and it is the costly one: pictures are anchored to its passages |

For Karan Aagama there are three choices:
1. **Use the repaired text.** It replaces the passages; translating again costs nothing where a
   passage's text did not change.
2. **Translate what is left with `--allow-debris`**, for that text only.
3. **Wait for R3's in-place re-ingest** (section 6). It would keep the passage ids, and so the Hindi,
   vectors and pictures.

## 6. The enterprise path: from repair to a critical edition

- **R1. The repair path. Built and tested (this).** A stop says what it needs. The repair is one press
  away and capped. A text that cannot be repaired is set aside, with its files kept and the reason
  recorded.
- **R2. Sources wanted (next).**
  - The hub and the Corner list the texts set aside as *Sources wanted*: the edition, the reason, and
    what a better scan must have.
  - A better scan dropped into the inbox is OCRed as a new witness of the same text.
  - Pages vision could not read get a second try at a higher resolution before a text is set aside.
- **R3. Keep what is good while the text improves.**
  - Today, re-ingesting deletes and re-creates the passages (`wipe_doc.py`). The Hindi rows, vectors
    and picture anchors are left pointing at passages that no longer exist.
  - `ingest_jsonl_fast.py` already upserts on (doc, page, index) and does not overwrite translations.
  - An in-place mode would build on that:
    1. keep the passage ids where page and index match;
    2. clear the translation only where the source text changed beyond a threshold;
    3. re-translate those passages. `mt_cache` answers the passages that did not change.
  - That turns Karan Aagama's decision into a refresh. It needs its own tests before it touches a
    text.
- **R4. The distillate.**
  - For each passage: the best reading among its witnesses (Tesseract, vision, a second scan), chosen
    by consensus and the quality score, with its provenance (engine, witness, page). Then the best
    translation, chosen by `translation_qa`, with its model and date.
  - What the corpus publishes is that distillate. Passages below the bar are marked *in repair*, not
    hidden.
  - This is the critical-edition brain: every reading and every translation says where it came from
    and why it was chosen.

## 7. Apply and check

1. **The page, now:**
   - `python scripts\patch_repair_path_2026_10_10.py --check`, then the same without `--check`.
   - Reload the dashboard with Ctrl+F5.
   - A held run in the Log is followed by its repair command.
2. **The dashboard, when idle:** restart it (`scripts\restart_dashboard.ps1`). The Library then shows
   the repair bars, `/repair/<doc>` answers, and the Log's line opens the repair page.
3. **By hand, at any time:**
   - `python scripts\repair_text.py --doc 2015_368408_Natyasastra` (free);
   - then `--repair`;
   - then `--use-repaired`, while the dashboard is idle.

## 8. Tests

- **`tests/test_repair_text_2026_10_10.py` (9).** It uses stand-ins for `ocr_consensus.py`,
  `db_backup.py`, `wipe_doc.py`, `ingest_jsonl_fast.py` and `classify_doc.py`, on a temp tree. It
  checks:
  - a held text is assessed (nothing runs) and offered its repair;
  - repair, then use, when nothing is lost: backup first, then the clean text in, and the guard no
    longer holds it;
  - translations are not replaced without `--replace N`;
  - an incomplete or unreadable repair changes nothing, and no backup is taken;
  - it refuses while the dashboard writes, except as the dashboard's own job;
  - set aside, restore and list work;
  - without its PDFs a text is pointed to Set aside;
  - a repair above its cap spends nothing and names the cap it needs;
  - the file is ASCII and carries the marker.
- **`tests/test_repair_path_2026_10_10.py` (12).** It checks:
  - `/api/repair` starts the right run for each step, and refuses bad input, starting nothing;
  - `use` waits for the translate lock, and an assessment does not;
  - the Library's bars, the card of a text set aside, and *Waiting for a better source*;
  - the repair page, with no placeholder left;
  - the register's latest-record rule;
  - in node: the next step read from NEXT, and the Log's verdicts (held names its text, stuck,
    [REPAIR]);
  - the patcher applies once to the files as LIVE_LOG left them, keeps CRLF, and refuses without its
    prerequisites (all or nothing).
- **Existing tests:**
  - the DESK_HEAL tests (Library notes, card count) and the LIVE_LOG tests still pass;
  - across the suite, the same tests fail in this sandbox's partial copy of the repository with and
    without the patch (Corner worker, sync and site stand-ins it does not carry).
- **By hand, in Chromium against stand-ins:**
  - the Library card's bar, *Repair the scan (at most $1.00)* offered after the assessment, the
    set-aside card with Restore, and *Waiting for a better source*;
  - the repair page at 1100 px and at 390 px;
  - no script errors.
