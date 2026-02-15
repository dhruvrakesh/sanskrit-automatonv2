# Repo audit: bugs, cruft, inefficiencies

Quick audit of `sanskrit-automatonv2` for bugs, extra files, and inefficiencies.

---

## 1. Bugs / risks

### 1.1 Dashboard API: `doc` not validated (path / injection)

**Where:** `scripts/dashboard.py` — `api_ocr`, `api_ingest`, `api_translate`, `api_export`

**Issue:** `doc` comes from `request.get_json()` and is used in paths and subprocess args, e.g.:

- `inbox.glob(f"{doc}_*.pdf")`
- `pathlib.Path(raw) / f"{doc}_*.jsonl"`
- Passed to CLI as `--doc`, then used in `ingest_jsonl_fast.py` and others.

If a client sends `doc` like `../../something` or `x\y`, you can get path traversal or surprising behavior. The UI only shows docs derived from PDF filenames (alphanumeric + underscore), but the HTTP API is not restricted.

**Recommendation:** Validate `doc` before use, e.g. allow only `[A-Za-z0-9_\-]+` and reject otherwise with 400.

---

### 1.2 Schema drift: two different “baseline” schemas

**Where:**  
- `scripts/ingest_jsonl_fast.py`: its own `ensure_schema()` — minimal (docs, passages with `text`/`translation`, FTS).  
- `scripts/db_utils.py`: `BASE_SCHEMA` — richer (passages with `norm`, `sandhi`, `morph`, `translation`, `ents`, `source`, `created_at`, plus `mt_cache`, `sources`).

**Issue:**  
- If the DB is created by `ingest_jsonl_fast.py` first, `passages` never gets the extra columns.  
- Scripts that assume `norm`, `sandhi`, `morph`, etc. (e.g. pipeline steps or `publish_api`) may fail or behave oddly on such DBs.  
- `translate_passages` uses `db_utils.ensure_schema`, so `mt_cache` exists when translating, but the passages table can still be the “minimal” one.

**Recommendation:**  
- Prefer a single source of truth for schema (e.g. `db_utils`).  
- Have `ingest_jsonl_fast` call `db_utils.ensure_schema` (and optionally `ensure_doc`) instead of defining its own minimal schema, or add a one-off migration that adds missing columns if they don’t exist.

---

### 1.3 `translate_passages` and `passages.id` vs `rowid`

**Where:** `scripts/translate_passages.py` — uses `p.rowid` in SELECT and `WHERE rowid=?` in UPDATE.

**Status:** In SQLite, for a table with `INTEGER PRIMARY KEY`, `rowid` and that column are the same. So for the usual `passages(id INTEGER PRIMARY KEY, ...)` this is correct. No change needed unless you introduce a table without an integer PK.

---

## 2. Inefficiencies

### 2.1 Extra SELECT per row in `ingest_jsonl_fast.upsert_passages`

**Where:** `scripts/ingest_jsonl_fast.py` around lines 96–97.

**Issue:** After each `INSERT ... ON CONFLICT DO UPDATE`, the code does an extra:

```python
rid = cur.execute("SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?", (doc_id, page_no, i)).fetchone()[0]
```

to get `id` for FTS. In SQLite, `lastrowid` after that INSERT/UPDATE is exactly that row’s rowid (same as `id` for this table). So you do one extra query per passage for no reason.

**Recommendation:** Use `rid = cur.lastrowid` after the `cur.execute("""INSERT INTO passages ...""")` and drop the SELECT. Then keep using `rid` for FTS as you do now.

---

### 2.2 FTS updates inside loop with single commit

**Where:** Same function: for every passage you `DELETE FROM passages_fts` and `INSERT INTO passages_fts` then call `con.commit()` once at the end.

**Status:** Reasonable for correctness. For very large ingests you could consider batching commits (e.g. every N rows) to reduce transaction size; only worth it if you see slowdowns or lock contention.

---

### 2.3 Repeated schema detection

**Where:** `api.py`, `scripts/export_html.py`, `scripts/translate_passages.py`, etc.

**Issue:** Several scripts re-detect column names (`_page_col`, `_idx`, `_doc_join`, etc.) with multiple `PRAGMA table_info` and `sqlite_master` queries per run. For a single process it’s cheap; if you ever expose many short requests (e.g. per-doc or per-page), caching the detected schema per connection (or per DB path) could help. Low priority unless you see load issues.

---

## 3. Extra / cruft files

### 3.1 Root-level temporary / scratch files

- **`tmp_check.py`**, **`tmp_peek.py`**, **`tmp_peek_missing.py`**, **`tmp_mm.py`**, **`tmp_clear.py`** — look like one-off DB/script checks. Safe to remove or move to a `scripts/scratch/` or `tools/` if you still use them occasionally.
- **`tmp.txt`** — likely scratch; remove if not needed.

### 3.2 Root-level “private” or one-off scripts

- **`_mt_stats.py`**, **`_scan_low_pages.py`** — underscore-prefixed, ad-hoc. Either integrate into `scripts/` with clear names or move to a dev/scratch folder so the root stays clean.

### 3.3 Archives and backups in repo

- **`scripts/scripts.zip`** — likely a one-off backup of `scripts/`. Prefer not keeping zip archives in the repo; remove or add to `.gitignore` if you want to keep it locally.
- **`data/context_backup_*.db`** — DB backups. Usually better not to commit these; keep them local or in a backup location and add `data/*_backup_*.db` (or similar) to `.gitignore`.

### 3.4 Unused / legacy script

- **`scripts/watch_inbox_notinuse.py`** — name says “not in use”. Safe to delete or rename to something like `watch_inbox_legacy.py` and leave in a `legacy/` folder if you might reference it later.

### 3.5 Duplicate / overlapping docs

- **`howtouse.txt`**, **`howtouse2.txt`** — if content is redundant with `README.md` or `readme_sanskrit_automaton_v_2_windows.md`, consider merging and removing.

---

## 4. Minor / nice-to-have

- **Dashboard HTML in Python string:** The whole dashboard UI is in a large triple-quoted string in `dashboard.py`. Moving it to `scripts/dashboard_static.html` and serving that file (as you do for `index`) would make editing and versioning easier. The readme already mentions `dashboard_static.html`; if that file is generated by the script, consider inverting so the file is the source and the script only serves it.
- **`api.py` vs `scripts/publish_api.py`:** Two entry points for “API” (export vs analyze/entities/translate). A short note in the main README or in a single “Running the project” section would clarify when to use which and on which port.

---

## 5. Summary

| Category              | Item                                                                 | Severity / impact      |
|-----------------------|----------------------------------------------------------------------|------------------------|
| Bug / security        | Dashboard API `doc` not validated                                   | Medium (path/API abuse)|
| Bug / correctness      | Two baseline schemas (ingest_jsonl_fast vs db_utils)                 | Medium (drift, missing cols) |
| Inefficiency          | Extra SELECT per row in `ingest_jsonl_fast.upsert_passages`         | Low (use `lastrowid`)  |
| Cruft                 | Root `tmp_*.py`, `tmp.txt`, `_mt_stats.py`, `_scan_low_pages.py`    | Cleanup                |
| Cruft                 | `scripts/scripts.zip`, `data/context_backup_*.db`                   | Don’t commit / ignore  |
| Cruft                 | `watch_inbox_notinuse.py`, duplicate howtouse*.txt                  | Optional cleanup      |

Fixing the `doc` validation and unifying schema (or documenting the two paths) gives the most benefit; then removing or relocating cruft and using `lastrowid` in ingest for a small performance gain.
