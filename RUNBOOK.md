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
| `QUALITY_METHODOLOGY.md` | How source/translation/semantic quality are computed (public-facing; served at `/methodology`) | transparency, reader-facing |

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

## 1. Start / stop / restart the dashboard

**Use the restart script** — it stops the old listener, starts the server DETACHED in its
own window, and health-checks the port, so your terminal stays free:

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
# add -NoNewWindow to run it hidden instead of in a visible log window
```

**Do NOT** run `python scripts\dashboard.py` directly in a terminal you still need:
it runs in the FOREGROUND, so pressing Ctrl+C to get the prompt back kills the server
(the classic "ERR_CONNECTION_REFUSED right after a restart").

```powershell
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

## 3b. Vision re-OCR of an old scanned edition (the remediation playbook)

Tesseract misreads pre-1900 Devanagari founts into confident nonsense; a vision model
reads the same clean scan correctly (see BENCHMARKS: dev 0.98 garbage -> 0.996 clean).
This is the procedure. **Order matters** — the text change invalidates translations and
every derived tag, so they must be rebuilt after, not before.

```powershell
cd "D:\Sanksrit Automatons\sanskrit-automatonv2"
$DOC = "<DocCode>"

# 1. BACKUP first (the ingest rewrites passage text).
python scripts\db_backup.py "data\context.db" "D:\backups\context_pre_vision_$(Get-Date -Format yyyyMMdd_HHmmss).db"

# 2. Vision-OCR every page to a SEPARATE folder (resumable; per-page cost is now MEASURED and printed - see 5c).
python scripts\ocr_vision.py --glob "inbox\$($DOC)_*.pdf" --outdir "data\raw_vision" --skip-existing --yes

# 3. WIPE then re-ingest. Do NOT plain-upsert: upsert never deletes, so a shrinking
#    source leaves stale high-idx rows of the OLD garbled text interleaved with the new
#    (observed: 680 rows where the new ingest wrote 599). wipe_doc gives a clean slate;
#    the backup from step 1 is the safety net.
python scripts\wipe_doc.py --db data\context.db --doc $DOC
python scripts\ingest_jsonl_fast.py --doc $DOC --glob "data\raw_vision\$($DOC)_*.jsonl" --db data\context.db

# 4. Re-derive EVERY tag from the new text (all were computed on text that no longer exists).
python scripts\classify_frontmatter.py --doc $DOC            # preview, then --apply
python scripts\classify_noise.py --doc $DOC --show           # preview, then --apply

# 5. Translate from the clean source, then score.
python scripts\translate_passages.py --db data\context.db --doc $DOC --engine gemini:gemini-2.5-flash
python scripts\qa_scan.py --db data\context.db --doc $DOC --lang en --write
python scripts\diag_post_vision.py $DOC
python scripts\diag_coverage.py
```

**Why wipe rather than upsert:** translations produced from the OLD garbled text do not
correspond to the NEW text (observed: source `अं०४ । अ` under translation
`Prose 10. 3 12 Viṣṇupu° //`). They are translations of noise and are not worth
preserving; the pre-vision backup keeps them recoverable if ever needed.

**Bilingual editions:** many 19th-century volumes are Sanskrit first, English translation
second (AphorismsOfSandilya: Sanskrit pp. 5-80, English pp. 81-206). The English half is
correctly tagged `frontmatter` by step 4 and excluded from Sanskrit coverage.

### Vision OCR fails in three ways - audit before you ingest (2026-08-29)

Vision OCR is a large, MEASURED quality win over Tesseract. On 185 like-for-like
Shatpatha pages, Latin/junk contamination inside Devanagari lines fell from
**0.1004 to 0.0023** (44x) at the same text volume (median 2,367 vs 2,414 chars),
vision cleaner on 183 of 185 pages. But 12 of 197 pages came back damaged, in
three distinct ways, and ingesting any of them poisons every downstream metric.

| Failure | What it looks like | Detected by | Action |
|---|---|---|---|
| Runaway character | page 0003: 129,421 chars, real text is the first ~200, rest one run of `_` | `collapse_runs()` - 8+ identical chars | repaired in place, lossless |
| Phrase loop | page 0017: one Sanskrit phrase repeated to 21,639 chars; 27 distinct lines | compression ratio < 0.08 | **flagged, never repaired** |
| Empty page | page 0102: 0 chars where Tesseract read 2,141 | length < 5 chars | re-OCR |

**Why the phrase loop is not auto-repaired.** The repeated content is real
Sanskrit, so no character rule and no `quality_score` can see it. Brahmana texts
genuinely repeat formulae, so a collapser would risk destroying real refrains.
Compression ratio separates them cleanly - measured over 194 pages, the 9
degenerate pages scored 0.0035-0.0292 and the 185 ordinary pages 0.1347-0.4766 -
but the honest limit is that a genuinely refrain-heavy long page will be flagged
too. That costs one wasted re-OCR, never lost text.

**A caution about `dev_frac`.** It divides Devanagari by (Devanagari + Latin), so
it ignores punctuation entirely: a page of 129,000 underscores reports
`dev=1.00`. It is not a health check. That is exactly how nine bad pages slipped
past the progress line.

```powershell
# ALWAYS audit before ingesting a vision run
python scripts\repair_vision_jsonl.py --glob "data\raw_vision\<CODE>_*.jsonl"

# repair the character runs (originals copied to _pre_repair\ first)
python scripts\repair_vision_jsonl.py --glob "data\raw_vision\<CODE>_*.jsonl" --apply

# re-OCR only the pages the audit could not repair
Get-Content data\vision_redo.txt | ForEach-Object {
  $stem = [IO.Path]::GetFileNameWithoutExtension($_)
  Remove-Item "data\raw_vision\$stem.jsonl" -ErrorAction SilentlyContinue
  python scripts\ocr_vision.py --pdf $_ --out "data\raw_vision\$stem.jsonl" --doc <CODE> --yes
}
```


## 3c. Mixed-language books, and the two OCR failures behind them (Phase L1, 2026-08-29)

Most scanned editions are NOT pure Sanskrit. A typical volume carries an English
title page and preface, a Hindi or English commentary beside the mula, running
heads, page numbers and OCR crumbs. Three things were wrong.

**1. Big books could not OCR at all.** `/api/ocr` passed every page-PDF as a
separate argument. Windows caps a command line at ~32,767 characters; the
Rgveda's 1,064 pages is ~80,000, so the job died in 0.0s with
`FileNotFoundError: [WinError 206] The filename or extension is too long` and
the UI showed a red `OCR 0/1064` with no cause. Books under roughly 430 pages
fit, which made it look random. `ocr_batch.py` now takes `--pdfs-from
<manifest>` (one path per line) and the dashboard writes
`data/manifests/ocr_<DOC>.txt` instead of splatting arguments. `--pdfs` still
works for small CLI runs.

**2. Classification was manual and easily forgotten.** `classify_frontmatter.py`
and `classify_noise.py` had to be remembered and run by hand after ingest. If
you forgot, the preface counted as untranslated Sanskrit, coverage was wrong,
and the translator spent money on English prose. `classify_doc.py` wraps both
into one stage, and `/api/ingest` now chains it automatically via `then=`, so a
freshly ingested book arrives already sorted. `classify` shares the TRANSLATE
semaphore because it writes `passages.text_type` - it must never run while a
translator is writing.

**3. The UI implied every line was a verse.** Each pipeline row now shows a
composition bar and a `N Sanskrit / N En-Hi / N noise` line from the new
`composition` field in `/api/status`, plus a per-doc **Classify** button.

```powershell
# classification: dry run, then apply
python scripts\classify_doc.py --doc <CODE>
python scripts\classify_doc.py --doc <CODE> --apply
python scripts\classify_doc.py --apply                 # whole corpus

# a big book can now OCR; check the manifest it wrote
python scripts\ocr_batch.py --pdfs-from data\manifests\ocr_<CODE>.txt --outdir data\raw --dpi 400
```

### The quality gate's blind spot (measure before changing it)

`passages.quality_score` = `0.6 * devanagari_density + 0.4 * danda_presence`. It
measures how Devanagari a line LOOKS, never whether the Devanagari is real
words. A garbled Tesseract line scores ~0.64 and passes the 0.35 threshold; we
then pay to translate it and the model correctly returns `[empty]`.

A better signal is Latin/junk characters INSIDE a Devanagari-dominant line:
`contamination = (latin + junk) / (devanagari + latin + junk)`. Measured on our
own examples: garbled 0.155, clean verse 0.000. **But a legitimate Sanskrit
verse followed by an English gloss scores 0.667** - so a naive contamination
gate would reject exactly the mixed-language pages this section is about.
Segmentation must come first; the gate is only safe on rows already tagged
`mula`.

```powershell
# evidence before any threshold change - read-only, no API calls
python scripts\diag_ocr_contamination.py --doc <CODE> --show 8
```


## 3d. The OCR standard (settled 2026-08-29, measured not assumed)

**Both engines, distinct jobs.** Tesseract on every page; vision on every page;
merge picks the better source per page and records which.

| step | command |
|---|---|
| 1. Tesseract (free, local) | dashboard OCR button, or `ocr_batch.py --pdfs-from ...` |
| 2. Vision | `ocr_vision.py --glob "inbox\<CODE>_*.pdf" --outdir data\raw_vision --skip-existing --doc <CODE> --yes` |
| 3. Audit vision (GATE) | `repair_vision_jsonl.py --glob "data\raw_vision\<CODE>_*.jsonl" --apply` |
| 4. Re-OCR what failed | loop over `data\vision_redo.txt` |
| 5. Merge + fallback | `merge_ocr_sources.py --doc <CODE> --apply` |
| 6. Ingest merged | `ingest_jsonl_fast.py --doc <CODE> --glob "data\raw_merged\<CODE>_*.jsonl" --db data\context.db` |
| 7. Classify | `classify_doc.py --doc <CODE> --apply` |

Ingest now writes `passages.ocr_engine` from the JSONL `engine` field (the column
is added automatically on first run). Find weak pages later with:

```sql
SELECT d.code, COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id
WHERE p.ocr_engine = 'tesseract-fallback' GROUP BY d.code ORDER BY 2 DESC;
```

**Never skip step 3.** On 2026-08-29 an audit correctly reported 6 phrase loops
and the ingest ran anyway, putting 250 junk passages into Shatpatha (213 from one
page) and losing page 102 entirely. The audit now exits non-zero; gate on it:

```powershell
python scripts\repair_vision_jsonl.py --glob "data\raw_vision\<CODE>_*.jsonl" --apply
if ($LASTEXITCODE -eq 0) { <merge + ingest> } else { "not safe to ingest" }
```


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

## 5b. Automated idle maintenance

A Scheduled Task **`SanskritMaintenance`** (every 3 h, `scripts\maintenance_runner.ps1`)
keeps the search index and QA scores current using spare runtime — but only when SAFE:

1. **Idle guard** — queries `/api/jobs/running`; if any job is running or queued it skips
   (a translation is the single DB writer; maintenance must never contend).
2. **Connectivity guard** — skips if the Gemini API host is unreachable.
3. Then runs, all idempotent + incremental: `qa_scan` (free, re-score),
   `build_embeddings` (cheap, only new verses), `extract_entities --retry-empty`.
4. Logs every tick (RUN / SKIP / DONE / FAIL) to `D:\backups\maintenance_log.txt`.

Because embeddings/entities call the API, cost accrues against the `$8` budget
(`cost_tracker.py`); incremental runs are near-zero when nothing new was translated.

```powershell
Get-Content "D:\backups\maintenance_log.txt" -Tail 8      # what it did / why it skipped
Start-ScheduledTask -TaskName "SanskritMaintenance"        # run on demand
```

## 5c. Cost accounting (what we actually spend, and how much of it we can prove)

**The problem this fixes (2026-08-29).** `usage_log` had `kind` hard-coded to
`'translation'` inside `cost_tracker.log_translation_call()`. Every other paid
call — Gemini vision OCR, entity extraction, embeddings, the Phase-Q4 judge —
executed against a billed endpoint and wrote **nothing**. So
`budget_state.spent_usd` was never "what we have spent"; it was "what we have
spent on translation", and the cap was structurally unable to stop the other
four. A reported $7.06 was a true number answering the wrong question.

**What changed.**

| Piece | Change |
|---|---|
| `cost_tracker.py` | new `log_api_call(con, kind, ...)` — `kind` is a parameter now, not a literal. Prices from **token counts** when the provider reports them. Exact-match pricing lookup before the old substring fallback. Embedding + vision + tesseract price rows added. |
| `usage_log.token_source` | new column: `provider` (exact, from `response.usage_metadata`), `estimated` (chars/4), `reconstructed` (backfilled, see below). Legacy rows were labelled `estimated` — correctly, that is what they are. |
| `usage_meter.py` | **new.** Thin façade the job scripts call. Never raises: a metering fault must not kill a 4,000-page OCR run. Opens its own connection when the caller has none. |
| `ocr_vision.py` | meters every page from the provider's own token counts (an image's cost *cannot* be derived from characters), refuses to start if the cap is already reached, prints measured $/page at the end and flags the hard-coded estimate when it is >25% wrong. |
| `extract_entities.py` | meters each batch; new `--debug-raw`; and a reply that parses but has no `verses` key is no longer treated as success (it used to mark the whole batch `ents='[]'`, i.e. permanently done, having extracted nothing). |
| `build_embeddings.py` | meters each batch (`estimated` — the embedding API reports no tokens); new `--doc` filter. |
| `judge_sample.py` | meters each verdict; prints measured spend against its own pre-flight estimate. |

**The honest numbers, measured 2026-08-29.** Recorded translation spend
$6.9648 across 32,341 calls; `budget_state.spent_usd` $7.0594 (the $0.0946
gap is `migrate_cache_costs()`, which adds to `spent_usd` without writing
`usage_log` rows). Reconstructed unmetered spend: embeddings $0.2360
(15,091 vectors — input length exact, token ratio approximated), entities
$0.4193 (13,648 verses / ~1,365 calls — **output size is an assumption**),
judge $0.0110 (40 verdicts — thinking tokens assumed at 350/call, the weakest
figure here). **True spend, best estimate: $7.73**, plus 207 vision OCR pages
that stay *deliberately unpriced* until a metered run measures them.

The `$0.0004/page` vision constant in `ocr_vision.py` was an unverified guess.
It is now printed as an estimate, checked against reality after every run, and
must be replaced with the measured figure.

```powershell
# The honest report (read-only): spend by kind, measured vs guessed, still-silent kinds
python scripts\diag_cost_v2.py data\context.db

# What the unmetered past cost (read-only)
python scripts\reconstruct_untracked_spend.py --vision-glob "data\raw_vision\*.jsonl"

# Measure the real vision $/page on ONE page, then price the backlog with it
python scripts\ocr_vision.py --pdf "<one page pdf>" --out data\tmp_cost_probe.jsonl --doc COSTPROBE --yes
python scripts\reconstruct_untracked_spend.py --vision-glob "data\raw_vision\*.jsonl" --page-cost <measured>

# Charge the reconstruction to the cap (idempotent; will not double-charge)
python scripts\reconstruct_untracked_spend.py --vision-glob "data\raw_vision\*.jsonl" --page-cost <measured> --apply

# Cap management
python scripts\set_budget.py                 # show
python scripts\set_budget.py --cap 25        # change
python scripts\set_budget.py --unpause       # clear a tripped pause
```

**Rule going forward: any script that calls a paid endpoint calls
`usage_meter.meter()`.** `diag_cost_v2.py` lists every expected `kind` and
marks the ones with no rows `SILENT` — that list is the regression test. A
`SILENT` kind you know you have run is an unwired script, not an idle one.

**These figures are what the app recorded, not a bill.** Check them against the
provider console; if they disagree, the pricing table in `cost_tracker.py` is
stale and every number above moves with it.


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

## 6b. Releasing (use the script; do not paste git commands)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release.ps1                       # dry run
powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -ClearLocks           # clear stale locks
powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -MessageFile COMMIT_MSG.txt -Apply
powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -Repo "D:\sanskrit-symphony" -MessageFile "D:\Sanksrit Automatons\sanskrit-automatonv2\COMMIT_MSG.txt" -Apply
```

**Three failures on 2026-08-30 are why this is a script.** All three were silent
or actively misleading:

1. **Stale `.git/index.lock`.** A read-only `git status` was run over a file
   bridge that cannot delete files, so git created the lock and could never
   remove it. Every subsequent `git add` and `git commit` failed. **Never run
   git through the device bridge - only from a real shell on the machine.**
2. **`git push` printed "Everything up-to-date".** True, and useless: nothing
   had been committed, so there was nothing to push. A success message for work
   that never happened. The script therefore fetches after pushing and compares
   `origin/<branch>` to local HEAD, failing loudly if they differ.
3. **A multi-line `-m` message** containing `$` and backticks is a PowerShell
   interpolation minefield. Commit messages go in a FILE, passed with
   `git commit -F`.

The script also refuses to stage `context.db`, `backups/`, the OCR working
directories, or any file over 5 MB - `backups/` alone had reached 523 MB and was
not in `.gitignore` until this release.

**Lock safety rule:** the script clears a lock ONLY when it is zero-length AND
no `git` process is running. A non-empty lock, or a running git, means a real
client (VS Code, GitHub Desktop, Fork) holds it - close that client instead.


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
