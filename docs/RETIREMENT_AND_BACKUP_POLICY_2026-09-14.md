# Retirement, grafting and backup policy - 2026-09-14

Written alongside the commits that add `retire_doc.py`, `diag_retire_check.py`,
`graft_verses.py` and `diag_corpus_overlap.py`. Per the operating discipline in
`ENTERPRISE_ROADMAP.md`: "Docs updated in the same commit as the change."

## 1. Why a document is ever retired

`resegment_doc.py` (2026-08-02) produces a NEW document from an existing one and
never touches the source. Its docstring sets out the workflow:

> Ingest the output as a NEW doc, translate it, compare, and only then adopt it
> as canonical.

The compare-and-adopt step had never been performed for any pair. The result,
measured 2026-09-14: `upapurana_nilamata_purana` (111 page-blobs, median 137
words per row, 3.6% of rows verse-shaped) and `nilamata_seg` (1,393 verses,
median 9, 98.0% verse-shaped) were BOTH fully translated into English and
Hindi. The corpus paid twice for one text.

`nilamata_seg` is canonical. The page-blob source is retired - but only after
section 4.

## 2. The rule

A document may be retired only when all three hold:

1. `diag_retire_check.py --src <retiree> --keep <keeper>` reports zero unmatched
   verses.
2. The keeper has at least as many passages as the retiree. `retire_doc.py`
   refuses otherwise: a re-segmented copy has more rows, not fewer.
3. A verified backup exists from after the last write to `data/context.db`.

## 3. Why not wipe_doc.py

`wipe_doc.py` deletes `passages` and `passages_fts` and is honest about it. What
it leaves are the rows keyed to those passage ids:

    passage_embeddings.passage_id      entity_mentions.passage_id
    translations_l10n.passage_id       translation_history.passage_id

Those survive pointing at ids that no longer exist. `diag_brain.py` exists to
find that condition; its closing note explains it. The corpus stood at zero
orphans on 2026-09-14, and retiring the nilamata source with `wipe_doc.py`
would have created 109 orphaned vectors and 1,633 orphaned mentions in one
command.

The foreign keys in `db_utils.BASE_SCHEMA` do declare `ON DELETE CASCADE`, but
SQLite honours that only under `PRAGMA foreign_keys=ON`, which is not in the
`PRAGMAS` list `db_utils.connect()` applies. `retire_doc.py` therefore deletes
every dependent row explicitly, in one transaction, and verifies the orphan
counts afterwards.

`wipe_doc.py` keeps its place: it is the right tool for wiping a document you
are about to re-ingest under the same code, where the links get rebuilt.

## 4. The check earned its keep on its first real use

It refused. Of 1,400 verses the splitter finds in the source, 7 were not in
`nilamata_seg`, and they are not noise:

| where | what |
|---|---|
| page 1 | the title, `svasti`, `sri-ganesaya namah` |
| page 1 v1 | `namo bhagavate vasudevaya ...` - the mangalacarana |
| page 1 v2 | Pariksit's descendant Janamejaya asked Vaisampayana |
| page 1 v3 | in the Mahabharata war, kings of many lands came |
| page 1 v4 | why did the king of Kashmir not come there? |
| page 1 v5 | `kasmiramandalam caiva pradhanam jagati sthitam` |
| page 109 | the colophon, plus the edition: Ved Kumari, J and K Academy, Srinagar 1973 |

The first six are the opening frame of the entire Purana. The last is its
colophon and carries the only record in the database of which printed edition
the text came from.

A reading edition without its invocation and its colophon is not the text. The
answer is to complete the keeper, not to lower the bar on the check.

## 5. Grafting

`graft_verses.py` inserts the missing verses into the keeper VERBATIM. It does
not clean them, even where they carry OCR debris. That is the division of
labour this project already settled: the database holds what the scanner saw,
and `clean_for_mt` decides what the model sees - `ENTERPRISE_PATH 2026-09-06`
section 1c records that decision and the 1,321-passage measurement behind it.
A second cleaner would be a second place for that judgement to go wrong.

Placement preserves reading order: each graft follows the nearest preceding
verse the keeper already has, or goes to the front of its page. Only affected
pages are renumbered, in two passes inside one transaction so the
`UNIQUE(doc_id, page_no, idx)` constraint is never violated mid-flight.

Grafted rows carry `text_type=mula`, `ocr_engine=resegment-graft`, `source` set
to the origin code, `quality_score` = the Devanagari fraction, and an explicit
`passages_fts` row - nothing maintains that table automatically. The tool then
verifies that every id it inserted has an FTS row; a corpus-wide count would
false-alarm on any pre-existing gap and say nothing about the operation.

Grafted rows arrive untranslated and unlinked; the incremental passes pick them
up.

## 6. What a retirement leaves behind

- The `docs` row, with its code and `src_path`.
- A `doc_stage` row `(doc_code, 'retired')` naming the superseding document.
  `automaton.py` reads it and excludes the code from the board, from `--next`
  and from the backfill, so the driver cannot resurrect a retired document.
- Entities whose only mention was there: counted and reported, not deleted.

No `VACUUM`. An exclusive lock on a 640 MB live database to reclaim a few
megabytes is not a trade worth making.

## 7. Backups

`scripts/backup_runner.ps1` already rotates correctly: the 14 most recent
`context_2*.db`, newest copied to `context_daily.db`, run at 04:00 by
`SanskritDBBackup` (result 0x0 on 2026-09-14).

Two things defeated it.

**Ad-hoc snapshots inside the rotation window.** Diagnostic blocks wrote
`context_20260914_095301.db`, `_100155` and `_101919`. Those match
`context_2*.db`, occupied three of the fourteen slots, and would have evicted
three genuine days of history. Blocks now REUSE the most recent verified
snapshot when it is newer than `data/context.db`.

**Files outside the pattern.** `context_pre_langboth_*`, `context_pre_noise_*`
and `context_pre_vision_*` never match `context_2*.db` and are never pruned -
about 1.9 GB of manual snapshots from 28-29 August.

| what | keep |
|---|---|
| `context_YYYYMMDD.db` | 14, by `backup_runner.ps1` |
| `context_daily.db` | always |
| `context_pre_*.db` | until the change they precede is proven, then remove |
| `context_YYYYMMDD_HHMMSS.db` | the newest only - session rollbacks |
| `query_snapshot.db` | not a backup; `dashboard.py /api/db/open` regenerates it |

## 8. The measurement behind all of it

`diag_corpus_overlap.py` v2. Three signals, reported separately:

- **Exact row match** across documents: zero.
- **Document containment** on Devanagari 5-grams, required in BOTH directions.
  v1 required one direction and printed several hundred pairs, because half of
  a 419-gram text's 5-grams appear in an 11,374-gram text for reasons that are
  facts about Sanskrit, not about copying. Both directions leaves two pairs:
  nilamata at 100.0/85.7, and `dhanur_veda_shiva_dhanur_veda` with
  `shiva_dhanur_veda` at 70.2/69.1.
- **Provenance** from `passages.ocr_engine`. Not `passages.engine`, which
  `db_utils.BASE_SCHEMA` documents as the translation engine and which
  translation overwrites. 51.5% of rows predate the column (added 2026-08-29)
  and cannot carry it.

The second pair is unresolved: 19 rows each, both page blobs, one translated
and one not, neither derived from the other. It needs eyes.

## 9. Console encoding

Devanagari printed through PowerShell 5.1 arrives as runs of Greek and
box-drawing characters: UTF-8 rendered through codepage 437, three symbols per
character. The transcript file on disk was always correct.

Two fixes, both already patterns in this repo. Ops blocks set
`[Console]::OutputEncoding` and `PYTHONUTF8`. Scripts that print Sanskrit call
`_force_utf8_streams()`, which `patch_booksmith_utf8.py` introduced for the
same reason. And `diag_retire_check.py` prints IAST beside every verse it
reports, because IAST is ASCII and renders in any console whatever its codepage
or font.