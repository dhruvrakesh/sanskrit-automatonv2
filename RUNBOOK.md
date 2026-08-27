# Sanskrit Automaton — Operations Runbook

*Canonical operational doc. Supersedes UPDATING.md. Companion docs: `README.md` (what it
is), `ENTERPRISE_ROADMAP.md` (forward plan), `BENCHMARKS.md` (measured baselines).*

---

## 0. Documentation map

| Doc | Purpose | When to read |
|-----|---------|--------------|
| `README.md` | What the system is, quickstart | first contact |
| `ARCHITECTURE.md` | Components, schema family, API routes, gotchas | understanding internals (⚠ predates the Phase-Q/HI additions — see below) |
| `docs/QUALITY_LOOP_DESIGN_*.md` | Phase Q: provenance + QA + history + retranslate + **Q4 judge (unbuilt)** | quality work |
| `docs/HINDI_TRACK_DESIGN_*.md` | Phase HI: sa→hi track, `translations_l10n`, hi-v1 prompt | Hindi work |
| `RUNBOOK.md` (this) | Every operational procedure | day-to-day operation |
| `ENTERPRISE_ROADMAP.md` | Phased forward plan + rationale | planning changes |
| `BENCHMARKS.md` | Dated measured baselines + metric semantics | before/after any change |

**System context.** This repo (`automaton`) is one of four siblings in the
`sanskrit-symphony` monorepo (`automaton`, `hub` = Srangam console :5050, `panchang`
:8501, `wisdomlib` = e-text crawler). A live **Srangam** website (Lovable + Supabase, its
own repo) is fed by `publish_srangam.py`. The **origin** repo
(`D:\Sanksrit Automatons\sanskrit-automatonv2`) is the LIVE system; the monorepo
`automaton/` is a code-only mirror pending data cutover — keep both in sync (§6).

**Two metrics, two axes** (see BENCHMARKS): `quality_score` = SOURCE Devanagari/OCR gate;
`translation_qa` = TRANSLATION structural QA. Neither certifies semantic fidelity — that
needs the Debroy benchmark + the unbuilt Q4 judge.

**Safety:** `.env` must keep `SA_SAFE_MODE=1` (disables destructive bulk ops). Never run
two Flask instances (in-memory `JOBS`).

---

## 1. Start / stop the dashboard

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
python scripts\dashboard.py                 # serves http://127.0.0.1:5057

# Stop cleanly: click "Pause All" in the UI (kills job subprocesses), then:
$p = (Get-NetTCPConnection -LocalPort 5057 -State Listen -EA SilentlyContinue).OwningProcess | Select-Object -Unique
$p | ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue }
```

Translation is idempotent — after a restart, press **Translate All OCR'd** and it resumes
where it left off (already-translated verses are skipped).

---

## 2. Concurrency model (what runs in parallel)

- **OCR** (`_OCR_SEM`, 2 slots) writes only JSONL, never the DB → runs **in parallel with
  translation**. "Import & Run Pipeline" OCRs under this lock, then auto-chains
  Ingest → Translate.
- **Translation** (`_TRANSLATE_SEM`, 1 slot) — one at a time by design (single SQLite
  writer). Extra translate jobs **queue** (Job Log shows `⏳ queued`; header reads
  `N running · M queued`).
- The dashboard suppresses system sleep while any job runs (keep-awake), so overnight
  batches are never paused. Belt-and-suspenders at OS level:
  `powercfg /change standby-timeout-ac 0`.

---

## 3. Sourcing policy (add texts the RIGHT way)

**Order of preference — always prefer clean Sanskrit source over OCR.** Leverage the
importers that already exist before reaching for OCR:

1. **Pure Sanskrit e-text (best) — use existing importers.** GRETIL / wisdomlib /
   sanskritdocuments.org give Unicode Devanagari with no OCR. The repo already has working
   pipelines: **`import_mbh_gretil.py`** (GRETIL → passages, as used for MBh), and
   **`import_wisdomlib.py`** + **`wisdomlib_to_jsonl.py`** (wisdomlib → JSONL → ingest).
   Use these first for any weak text. `archive_source_finder.py --gretil "<title>"` prints
   the GRETIL/SanskritDocs search URLs to locate the file.
2. **archive.org (vetted fallback).** Only when 1 has no copy.
   `archive_source_finder.py --search "<title>" --lang sanskrit`, then **`--preview <id>`**
   — accept ONLY when the Devanagari-ratio verdict is **ACCEPT**. `--save-text` is
   *purity-gated* (refuses below `--min-dev 0.85` unless `--force`). Reject "Sanskrit-Hindi"
   bilingual scans.
3. **Re-OCR a clean scan.** If only a good image PDF exists: `--save-pdf <id> --out
   downloads`, import it, OCR at 400–600 DPI (`ocr_pdf.py` / `ocr_batch.py`).

Never ingest un-previewed text. Record provenance for every added source.

---

## 4. Update the DATA (idle the jobs first; all steps idempotent)

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
python scripts\translate_both.py --db data\context.db --doc <code> --engine gemini:gemini-2.5-pro
python scripts\qa_scan.py        --db data\context.db --lang en --write     # score translations
python scripts\heal_lowqa.py     --db data\context.db --doc <code> --engine gemini:gemini-2.5-pro --below-qa 0.2
python scripts\build_embeddings.py --db data\context.db                     # semantic index
python scripts\extract_entities.py --db data\context.db --retry-empty       # entity layer
```

---

## 5. Backup & restore

Automated nightly at 04:00 via the `SanskritDBBackup` scheduled task →
`scripts\backup_runner.ps1` → dated + `context_daily.db` in `D:\backups`, pruned to 14,
logged to `backup_log.txt`.

```powershell
# Health check:
Get-Content "D:\backups\backup_log.txt" -Tail 6
Get-ScheduledTaskInfo -TaskName "SanskritDBBackup" | Format-List LastRunTime,LastTaskResult,NextRunTime

# On-demand backup:
python scripts\db_backup.py "data\context.db" "D:\backups\context_$(Get-Date -Format yyyyMMdd).db"

# RESTORE (stop writers first; rename, don't overwrite):
$stamp = Get-Date -Format yyyyMMdd_HHmmss
Move-Item "data\context.db" "data\context.db.broken_$stamp" -Force
Copy-Item "D:\backups\context_daily.db" "data\context.db" -Force
python scripts\qa_report.py --db data\context.db --coverage --all
```

---

## 6. Update the CODE (both repos stay identical)

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
git add scripts\*.py scripts\*.html *.md
git commit -m "<what changed>"; git push origin main
Copy-Item ".\scripts\*" "D:\sanskrit-symphony\automaton\scripts\" -Force
Copy-Item ".\*.md" "D:\sanskrit-symphony\automaton\" -Force
cd "D:\sanskrit-symphony"
git add automaton\scripts\* automaton\*.md
git commit -m "sync: <what changed>"; git push origin main
```

`LF will be replaced by CRLF` warnings are harmless. If `index.lock` exists: ensure no
`git` process runs, delete `.git\index.lock`, re-run.

---

## 7. Diagnostics (read-only; safe under load)

```powershell
python scripts\diag_baseline.py        # journal mode, counts, load-time, quality histogram
python scripts\diag_quality.py         # per-doc quality ranking (worst first)
python scripts\qa_report.py --db data\context.db --coverage --all
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Doc imports but pages don't OCR; pipeline "done" in ~2s | (fixed 2026-08-26) hyphen in doc name | ensure `pipeline_queue.py` regex allows `\-` |
| Translate shows green "done · 0/0" | no ingested verses | OCR → Ingest first (UI now shows amber notice) |
| "5 running" but throughput ~1× | 4 are queued behind the translate lock | expected; header now says `running · queued` |
| `database disk I/O error` | NOT sync (no client covers `D:\...`); likely AV scanning `-wal`/`-shm` | exclude `data\context.db*` from Defender real-time scan |
| PDF imports as one huge blob | corrupt PDF (`missing /Catalog`) | re-download the source; `qpdf --check` to confirm |
| Backup task result 0 but no file | writers held the DB at run time | 04:00 schedule + `backup_log.txt` now show the real cause |

---

## 9. Script inventory (the operational subset)

The `scripts\` folder holds 60+ files; many are one-off migrations. The ones that matter
day-to-day, by function:

**Source & ingest:** `ocr_pdf.py`, `ocr_batch.py` (OCR); `ingest_jsonl_fast.py`,
`ingest_pdf.py` (JSONL→DB); `import_mbh_gretil.py`, `import_wisdomlib.py`,
`wisdomlib_to_jsonl.py` (clean e-text importers); `archive_source_finder.py` (vetted
archive.org fallback); `segment_verses.py`, `resegment_doc.py`, `normalize_text.py`,
`sandhi_split.py`, `iast_utils.py`, `morph_parse.py` (text prep).

**Translate:** `translate_passages.py` (workhorse), `translate_both.py` (EN+HI),
`infer_mt.py` (engine layer), `retranslate.py`, `advance_pipeline.py`, `pipeline_queue.py`.

**Quality / QA:** `qa_scan.py` (score), `qa_report.py` (coverage), `heal_lowqa.py` (heal),
`text_filters.py` (scoring + salvage), `audit_translations.py`,
`polish_translation_debroy.py`, `style_debroy_post.py` (Debroy-style polish),
`benchmark_mbh01.py` (fidelity benchmark harness).

**Semantics / entities:** `build_embeddings.py`, `extract_entities.py`,
`build_gazetteer.py`, `ner_tag.py`.

**Ops / DB:** `dashboard.py`, `db_utils.py` (hardened connect helper — WAL+busy_timeout),
`db_backup.py`, `backup_runner.ps1`, `diag_baseline.py`, `diag_quality.py`,
`cost_tracker.py`, `wipe_doc.py`, `purge_empty_cache.py`.

**Export / publish:** `export_html.py`, `publish_api.py`, `publish_srangam.py`.

*Deprecated / one-off (do not run in normal ops):* `make_runs*.py`, `migrate_runs.py`,
`fts_hotfix.py`, `backfill_missing.py`, `train_mt.py`, `watch_inbox_notinuse.py`,
`scripts.zip`.
