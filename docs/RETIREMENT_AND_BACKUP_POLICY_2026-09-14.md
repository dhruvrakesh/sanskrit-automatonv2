# Retirement and backup policy - 2026-09-14

Written alongside the commit that adds `retire_doc.py`, `diag_retire_check.py`
and `diag_corpus_overlap.py`. Per the operating discipline in
`ENTERPRISE_ROADMAP.md`: "Docs updated in the same commit as the change."

## 1. Why a document is ever retired

`resegment_doc.py` (2026-08-02) produces a NEW document from an existing one
and never touches the source. Its docstring sets out the workflow:

> Ingest the output as a NEW doc, translate it, compare, and only then adopt
> it as canonical.

The compare-and-adopt step had never been performed for any pair. The result,
measured on 2026-09-14, was that `upapurana_nilamata_purana` (111 page-blobs,
median 137 words per row, 3.6% of rows verse-shaped) and `nilamata_seg`
(1,393 verses, median 9, 98.0% verse-shaped) were BOTH fully translated into
English and Hindi. The corpus paid twice for one text.

`nilamata_seg` is canonical. The page-blob source is retired.

## 2. The rule

A document may be retired only when all three hold:

1. `diag_retire_check.py --src <retiree> --keep <keeper>` reports zero
   unmatched verses. It applies `split_verses()` to the retiree and looks up
   every resulting verse in the keeper on three keys - exact Devanagari, then
   ignoring the sloka numbers the splitter consumes, then a 40-character
   prefix. Anything still unmatched is text that retirement would destroy, and
   it is printed in full rather than summarised.
2. The keeper has at least as many passages as the retiree. `retire_doc.py`
   refuses otherwise: a re-segmented copy has more rows, not fewer.
3. A verified backup of `data/context.db` exists from after the last write.

## 3. Why not wipe_doc.py

`wipe_doc.py` deletes `passages` and `passages_fts` and is honest about it.
What it leaves behind are the rows keyed to those passage ids:

    passage_embeddings.passage_id
    entity_mentions.passage_id
    translations_l10n.passage_id
    translation_history.passage_id

Those survive pointing at ids that no longer exist. `diag_brain.py` exists to
find that condition and its closing note explains it: "a wipe + re-ingest
gives passages NEW ids. Vectors and entity mentions keyed to the OLD ids
become orphans." The corpus stood at zero orphans on 2026-09-14 and retiring
one document with `wipe_doc.py` would have created 106 orphaned vectors and
several hundred orphaned mentions in a single command.

The foreign keys in `db_utils.BASE_SCHEMA` do declare `ON DELETE CASCADE`, but
SQLite honours that only under `PRAGMA foreign_keys=ON`, which is not in the
`PRAGMAS` list `db_utils.connect()` applies. `retire_doc.py` therefore deletes
every dependent row explicitly, in one transaction, and verifies the orphan
counts afterwards.

`wipe_doc.py` keeps its place: it is the right tool for wiping a document you
are about to re-ingest under the same code, where the links will be rebuilt.

## 4. What a retirement leaves behind

- The `docs` row, with its code and `src_path`. Nothing dangles and a future
  re-ingest can reuse the code. This is `wipe_doc.py`'s reasoning and it holds.
- A row in `doc_stage` as `(doc_code, 'retired')` whose reason names the
  superseding document and the date. `automaton.py` reads that row and
  excludes the document from the board, from `--next`, and from the backfill,
  so the driver cannot resurrect a retired document by seeing a code with zero
  passages and offering it as ready to ingest.
- Entities whose only mention was in the retired document. They are counted
  and reported, not deleted: an entity row is small and removing one could
  break an `entity_variants` row that points at it.

No `VACUUM`. Taking an exclusive lock on a 640 MB live database to reclaim a
few megabytes is not a trade worth making; SQLite reuses the freed pages.

## 5. Backups

`scripts/backup_runner.ps1` already rotates, and correctly: it keeps the 14
most recent files matching `context_2*.db` and copies the newest to
`context_daily.db`. The `SanskritDBBackup` scheduled task runs it at 04:00 and
returned 0x0 on 2026-09-14.

Two things were defeating it.

**Ad-hoc snapshots inside the rotation window.** Diagnostic blocks run on
2026-09-14 wrote `context_20260914_095301.db`, `context_20260914_100155.db`
and `context_20260914_101919.db`. Those match `context_2*.db`, so they occupied
three of the fourteen slots and would have evicted three genuine days of
history at the next 04:00 run. Diagnostic blocks now REUSE the most recent
verified snapshot when it is newer than `data/context.db` and only create one
when none exists.

**Files outside the rotation pattern.** `context_pre_langboth_*`,
`context_pre_noise_*` and `context_pre_vision_*` do not match `context_2*.db`
and are never pruned. They were manual pre-change snapshots from 28-29 August,
about 1.9 GB, superseded by every dated backup taken since.

Policy:

| what | keep |
|---|---|
| `context_YYYYMMDD.db` | 14, by `backup_runner.ps1` |
| `context_daily.db` | always, the newest copy |
| `context_pre_*.db` | until the change they precede is proven, then remove |
| `context_YYYYMMDD_HHMMSS.db` | the newest only; these are session rollbacks |
| `query_snapshot.db` | not a backup - the dashboard regenerates it |

`query_snapshot.db` in the repo root is written by `dashboard.py`'s
`/api/db/open` route, which snapshots the live DB with `db_backup.py` and
serves the copy to Datasette read-only. It is a working file, recreated on
demand, and safe to delete whenever Datasette is not serving it.

## 6. The measurement that justified all of this

`diag_corpus_overlap.py` v2. Three signals, reported separately:

- **Exact row match** across documents: zero. No passage's Devanagari text
  appears in two documents.
- **Document containment** on Devanagari 5-grams, requiring the containment to
  hold in BOTH directions. v1 required one direction and printed several
  hundred pairs, because half of a 419-gram text's 5-grams appear in an
  11,374-gram text for reasons that are facts about Sanskrit rather than about
  copying. Both directions leaves two pairs: nilamata at 100.0/85.7, and
  `dhanur_veda_shiva_dhanur_veda` with `shiva_dhanur_veda` at 70.2/69.1.
- **Provenance** from `passages.ocr_engine`, which `ingest_jsonl_fast.py`
  writes from the JSONL. Not `passages.engine`, which `db_utils.BASE_SCHEMA`
  documents as the translation engine and which translation overwrites.

The second pair, `dhanur_veda_shiva_dhanur_veda` (19 rows, 0 translated) and
`shiva_dhanur_veda` (19 rows, 19 translated), is unresolved. Both are page
blobs; neither is derived from the other by `resegment_doc.py`. It needs eyes
before anything is retired.