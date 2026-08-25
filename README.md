# Sanskrit Automaton v2 — Srangam

A local pipeline and research database that turns scanned Sanskrit scriptures into a
**trilingual, semantically searchable, entity–cross-linked corpus** — carrying the
genealogical and geographical correlation tradition of classical Indology into a
queryable database.

OCR → normalize → translate (English + Hindi) → export, plus a web dashboard, a
trilingual reader, retrieval-augmented **Ask the Corpus** Q&A, semantic (vector)
search, and a named-entity **cross-linkage** layer with footnotes.

---

## Corpus at a glance

- **53** source texts ingested
- **~12,850** verses translated to English; Hindi track growing
- **Semantic index**: one embedding vector per translated verse (`gemini-embedding-001`)
- **Entity layer**: ~5,100 distinct entities / ~22,800 mentions across all texts
- Database: `data/context.db` (SQLite, ~210 MB) — **code is versioned, the DB is not**

---

## Quick start

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
python scripts\dashboard.py --inbox inbox --db data\context.db --raw data\raw --exports exports --host 127.0.0.1 --port 5057
```

Open **http://127.0.0.1:5057/**. The toolbar links: **Translate · Library · Ask the
Corpus · Database · Refresh**.

Requirements: Python 3.13, `google-generativeai`, `numpy`, `datasette` (for the
Database button), Tesseract + Poppler (for OCR). A `GEMINI_API_KEY` in `.env` powers
translation, Ask, embeddings, and entity extraction.

---

## The web UI

- **/** — pipeline dashboard. Left: the **Scripture Corpus** browser (click a
  category to expand and tick PDFs) and **Add from disk** (import any PDF or folder
  by absolute path — not limited to the corpus root). Right: per-doc pipeline status
  with OCR / Ingest / Translate / Export controls and an engine picker.
- **/library** — every readable text, grouped by category, with EN/HI coverage and
  "Finish EN" / "Add Hindi" buttons to translate what's pending.
- **/reader/<doc>** — trilingual reader (Sanskrit · English · Hindi) with chandas,
  quality, and IAST notes, plus per-verse on-demand translation.
- **/ask** — **Ask the Corpus**: retrieval-augmented Q&A. Full-text or semantic
  search finds the most relevant verses; the chosen Gemini model answers *using only
  those verses* and cites each `[doc verse_ref]`. Falls back to keyword search when
  the embedding index isn't built.
- **💾 Database** — snapshots the DB and opens it in **Datasette** for read-only SQL.

---

## Data model (SQLite)

Core: `docs`, `passages` (Sanskrit `text`, `iast`, `translation` [EN], `chandas`,
`verse_ref`, `quality_score`, `translation_qa`, `ents`), `translations_l10n`
(Hindi and other languages), `translation_history` (supersede-never-destroy),
`passages_fts` (FTS5 full-text), `mt_cache`.

Semantic layer: `passage_embeddings` (per-verse L2-normalised float32 vector).

Entity / cross-linkage layer: `entities` (canonical IAST + kind), `entity_variants`,
`entity_mentions` (entity ↔ passage, the cross-linkage edges), `footnotes`
(annotations keyed to a verse and optionally an entity).

Convenience views (create once; additive/reversible): `v_trilingual`, `v_coverage`.

---

## Scripts

| Script | Purpose |
|---|---|
| `dashboard.py` | Flask web app: pipeline UI, reader, library, Ask, Database, import |
| `translate_passages.py` | Sanskrit→EN or →HI translation (context-aware, QA-scored) |
| `translate_both.py` | Run EN then HI in one job (`--hi-pure` for no-English-influence Hindi) |
| `infer_mt.py` | Translation engine (Gemini/OpenAI) + robust MAX_TOKENS ladder |
| `text_filters.py` | Pre/post filters + heuristic QA scorer (truncation, echo, salvage) |
| `qa_scan.py` / `heal_lowqa.py` | Re-score stored QA; re-translate low-QA verses |
| `qa_report.py` | Read-only QA / truncation / OCR-legibility / `--coverage` report |
| `build_embeddings.py` | Build the semantic index (auto-discovers a working model) |
| `extract_entities.py` | Extract named entities into the cross-linkage tables |
| `db_backup.py` | Verified, consistent DB snapshot (never copies a locked/corrupt DB) |

All long-running scripts are **idempotent and resumable** (skip finished work,
commit per batch/verse) and **safe under load** (busy_timeout). Run writers when the
DB is otherwise idle to avoid the Google-Drive lock.

---

## Common workflows

**Translate pending verses** (from the Library buttons, or CLI):

```powershell
python scripts\translate_both.py --db data\context.db --doc <code> --engine gemini:gemini-2.5-pro
python scripts\heal_lowqa.py --db data\context.db --doc <code> --engine gemini:gemini-2.5-pro --below-qa 0.2
```

**Build / refresh the semantic index** (run after new translations land):

```powershell
python scripts\build_embeddings.py --db data\context.db --list-models   # see supported models
python scripts\build_embeddings.py --db data\context.db                 # build / continue
```

**Extract / refresh entities** (whole corpus; resilient to 504s):

```powershell
python scripts\extract_entities.py --db data\context.db --retry-empty
```

**Back up the database** (independent of git — the DB is not versioned):

```powershell
python scripts\db_backup.py "data\context.db" "D:\backups\context.db"
```

---

## Cross-linkage queries (Datasette / DB Browser)

```sql
-- entities threading through the most texts
SELECT e.canonical, e.kind, COUNT(DISTINCT d.code) texts, COUNT(*) mentions,
       GROUP_CONCAT(DISTINCT d.code) appears_in
FROM entities e JOIN entity_mentions m ON m.entity_id=e.id
JOIN passages p ON p.id=m.passage_id JOIN docs d ON d.id=p.doc_id
GROUP BY e.id HAVING texts>=2 ORDER BY texts DESC, mentions DESC LIMIT 50;

-- every verse referencing an entity, across all texts
SELECT d.code, p.verse_ref, p.translation
FROM entities e JOIN entity_mentions m ON m.entity_id=e.id
JOIN passages p ON p.id=m.passage_id JOIN docs d ON d.id=p.doc_id
WHERE e.canonical='Gaṅgā' ORDER BY d.code, p.page_no, p.idx;

-- entities that co-occur in the same verse (relationship signal)
SELECT a.canonical, b.canonical, COUNT(*) shared_verses
FROM entity_mentions ma JOIN entity_mentions mb
  ON mb.passage_id=ma.passage_id AND mb.entity_id<ma.entity_id
JOIN entities a ON a.id=ma.entity_id JOIN entities b ON b.id=mb.entity_id
GROUP BY a.id,b.id HAVING shared_verses>=2 ORDER BY shared_verses DESC;
```

> **Writes** (e.g. inserting a footnote) must be done in **DB Browser for SQLite**
> against the live DB — Datasette is read-only by design.

---

## Reading vs writing the DB

- **Read** anywhere, anytime with `?mode=ro` (Datasette, `qa_report.py`) — safe even
  while jobs write.
- **Write** (translate, heal, embeddings, entities, footnotes) one at a time, when the
  dashboard/jobs are idle; the DB lives on a Google-Drive-synced disk, so a read
  during a mid-write sync can throw "disk I/O error" — snapshot first for GUIs.

---

## Repositories

- Origin: `sanskrit-automatonv2` (this project)
- Monorepo mirror: `sanskrit-symphony` under `automaton/`

The DB, embeddings, and entity tables are **not** in git (code-only repos) — they are
regenerated by the scripts above and backed up with `db_backup.py`.

See **UPDATING.md** for the exact commands to update code (both repos) and refresh data.
