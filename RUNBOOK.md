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
| `docs/ENTERPRISE_PATH_2026-09-06.md` | Measured state and ordered plan as of 2026-09-06 | planning (read with ENTERPRISE_ROADMAP) |
| `docs/RETIREMENT_AND_BACKUP_POLICY_2026-09-14.md` | retire_doc / graft_verses / backup policy | before retiring or grafting a doc |
| `docs/OPERATING_MODEL_2026-09-27.md` | What feeds what, how often, who presses the button; guardrails | operating the system |
| `docs/TRANSLATION_EMPTY_OUTCOMES_2026-09-27.md` | Why valid Sanskrit got empty translations; the outcome ledger | empty / filtered translations |
| `docs/PARK_AND_TITLE_2026-09-27.md` | Parking lacuna-only verses; Srangam display titles | lacunas, publishing titles |
| `docs/SRANGAM_BRIDGE_2026-09-27.md` | Automaton -> Srangam publish bridge and SQL-editor route | publishing to Srangam |
| `docs/PIPELINE_STATE_2026-09-30.md` | Why a book stops between stages; the plan | a book is stuck |
| `docs/OCR_CONSENSUS_2026-09-30.md` | One-command OCR consensus, drift, lacuna census, Hindi A/B and findings | OCR or lacuna work |

**System context.** This repo (`automaton`) is one of four siblings in the
`sanskrit-symphony` monorepo (`automaton`, `hub` = Srangam console :5050, `panchang`
:8501, `wisdomlib` = e-text crawler). A live **Srangam** website (Lovable + Supabase, its
own repo) is fed by `publish_srangam.py`. The **origin** repo
(`D:\Sanksrit Automatons\sanskrit-automatonv2`) is the LIVE system; the monorepo
`automaton/` is a code-only mirror pending data cutover — keep both in sync (§6). **Superseded 2026-09-30:** SOURCES_OF_TRUTH.md rule 2 - the symphony repo holds cross-project docs only; release this repo with §6b. (DOCS_MAP_2026_10_02)

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
# --doc finds the pages itself; --pdfs-from only works if the dashboard's OCR
# button already wrote a manifest (that is the only thing that creates one).
python scripts\ocr_batch.py --doc <CODE> --outdir data\raw --dpi 400
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


## 3e. Engine disagreement: the apparatus criticus (2026-08-30)

**The question this answers:** when Tesseract and vision read the same
good-quality scan differently, which wins?

**Old behaviour, and why it was wrong.** merge_ocr_sources.py preferred
Tesseract only when vision FAILED (empty, phrase loop, drastically shorter). On
ordinary disagreement vision won silently and the Tesseract reading was
discarded with no record. But vision is not always right: on a sampled page
Tesseract carried the correct reading roughly ONE TIME IN NINE -
`तरुण` where vision wrote the non-word `तरुश`, `उषितं` for `उपितं`, `अथातः`
for `अथवातः`. Those readings were being thrown away.

**New behaviour.** Vision is still the source of record - it is right about
eight times in nine - but the losing reading is KEPT:

  * `merge_ocr_sources.py` aligns the two token streams and records 1:1
    replacements whose similarity is >= 0.5 (below that they are different
    places in the text, not two readings of one word).
  * `passages.ocr_variants` stores the variants for that passage as JSON.
  * The reader underlines the disputed word; hovering shows the Tesseract
    reading and the similarity. A badge under each verse names the producing
    engine and the disagreement count.

This costs NOTHING - both transcriptions are already on disk. It is a critical
apparatus generated automatically, and it is the honest presentation: the reader
can see that a machine made a choice, and what it chose against.

```powershell
python scripts\merge_ocr_sources.py --doc <CODE> --apply     # records variants
python scripts\ingest_jsonl_fast.py --doc <CODE> --glob "data\raw_merged\<CODE>_*.jsonl" --db data\context.db
```

```sql
-- verses where the engines disagreed most
SELECT d.code, p.page_no, p.verse_ref,
       json_array_length(p.ocr_variants) AS n
FROM passages p JOIN docs d ON d.id = p.doc_id
WHERE p.ocr_variants IS NOT NULL
ORDER BY n DESC LIMIT 25;
```

**Not yet done (be honest about it):** nothing ADJUDICATES a disagreement. A
third opinion on disputed tokens only - a second vision pass at a different
temperature, or a stronger model on that word alone - is the obvious next step
and would be cheap, because disputed tokens are a small fraction of the text.


## 3f. Deterministic OCR triage: Tesseract first, vision only where needed (2026-08-30)

**The standing architecture.** Tesseract on every page (free, local, unlimited),
a deterministic per-page evaluation of where it failed, and vision ONLY on those
pages. Per PAGE, not per document - a book is not uniformly hard.

**Signals tried and REJECTED - do not re-tread these:**

| signal | why it failed |
|---|---|
| Latin-intrusion contamination | did not separate usable from unusable documents |
| Devanagari orthographic validity | correlation 0.363 over 314 Shatpatha page-pairs; 305 of 314 pages in one band. Tesseract's errors are orthographically LEGAL but wrong - `शातपथ` for `शतपथ` |
| per-document token agreement | works, but needs a vision pass to compute, so it cannot decide whether to spend one |

**The signal that is actually available: Tesseract's own per-word confidence.**
`ocr_pdf.py` was calling `image_to_string` and discarding it. It now records
`conf_mean`, `conf_p10`, `conf_lt60` and `conf_words` into each page's meta,
computed from the winning rendering. Costs one extra local pass. Sanity check:
English OCR on a Devanagari page returns `conf_mean 25.7` with 93% of words
under 60 - Tesseract is honest about not being able to read.

```powershell
# 1. CALIBRATE on pages where both engines have already run. Chooses the
#    threshold from evidence, and says plainly if confidence does NOT predict.
python scripts\ocr_batch.py --doc 2015_405693_Shatpath-Brahmanam --outdir data\raw_conf --dpi 400
python scripts\ocr_triage.py --calibrate --doc 2015_405693_Shatpath-Brahmanam --tesseract-dir data\raw_conf

# 2. Triage a document; only the failing pages are queued for vision
python scripts\ocr_triage.py --doc <CODE> --threshold 72 --tesseract-dir data\raw_conf
python scripts\ocr_triage.py --doc <CODE> --threshold 72 --tesseract-dir data\raw_conf --write-queue

# 3. Vision only the queue, then the usual gate -> merge -> ingest -> classify
Get-Content data\vision_queue_<CODE>.txt | ForEach-Object {
  $stem = [IO.Path]::GetFileNameWithoutExtension($_)
  python scripts\ocr_vision.py --pdf $_ --out "data\raw_vision\$stem.jsonl" --doc <CODE> --yes }
```

**Never re-OCR into `data\raw` on a live system to get confidence.** That
directory holds the Tesseract text serving as the per-page fallback and as the
apparatus's second opinion; overwriting it mid-flight would change source under
a running merge. Write to `data\raw_conf` and point `--tesseract-dir` at it.

**Pages OCR'd before 2026-08-30 carry no confidence.** The triage says so rather
than guessing. Re-running Tesseract on a document populates it and costs nothing
but time.

**If calibration reports a weak correlation, believe it.** Building a gate on a
signal that does not predict is exactly the orthographic-validity mistake. The
fallback is the per-document probe verdict: vision every page of the documents
`ocr_probe.py` rates poorly.


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

> **SUPERSEDED 2026-09-30 (RUNBOOK_EXPORT_2026_09_30).** Do not copy scripts into
> `D:\sanskrit-symphony`. SOURCES_OF_TRUTH.md rule 2: symphony holds cross-project
> docs and the register only, and must not contain a copy of any other project.
> Release this repo with section 6b (`scripts\release.ps1`) and nothing else. The
> commands below are kept for history only.

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

## 9b. Phase G - operable semantic layer, resizable and sortable UI (2026-09-06)

**"Why can't we update embeddings/RAG from the frontend?" Because it was never
built.** `dashboard.py` contained ZERO references to `build_embeddings.py` or
`extract_entities.py`. `/api/ask` existed, so the corpus could be QUERIED from
the UI while its index could only be refreshed from a terminal - which is how
the semantic layer went stale after every ingest without anyone being told.

| added | what it does |
|---|---|
| `POST /api/embeddings` | rebuild the semantic index, per doc or whole corpus |
| `POST /api/entities` | extract entities into the cross-linkage tables |
| **Embed** / **Entities** buttons | per-doc, beside Ingest / Classify / Export |
| `first_seen`, `last_ocr`, `last_activity` in `/api/status` | there were NO dates at all, so the table could only sort by name |
| draggable splitters | panes were hard-coded `320px 1fr 340px`; widths persist in localStorage, double-click resets |
| sortable headers | click any column incl. Added / Last run; sort persists |

**Both new kinds join the TRANSLATE semaphore family.** They write to
`passage_embeddings` and `entity_*`, so they must serialize with translators
exactly as `classify` and `qa_scan` do. Omitting that would reintroduce the
concurrent-writer bug the semaphore exists to prevent.

Dates come from file mtimes (`doc_times()` in dashboard.py) - `first_seen` is
the oldest inbox page, `last_ocr` the newest OCR output. A directory stat, no DB
cost. Rows with no date sort LAST in both directions: a missing date is unknown,
not oldest.

```powershell
python scripts\patch_ui_phase_g.py --apply       # backend  (idempotent)
python scripts\patch_ui_phase_g_js.py --apply    # frontend (idempotent)
python scripts\patch_ui_phase_g.py --verify
powershell -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1
```

Both patchers assert every anchor is unique BEFORE writing, back up first, and
roll back completely on any failure. Re-running is a no-op.

**Still not in the UI:** nothing triggers `ocr_vision.py`, `ocr_triage.py`,
`merge_ocr_sources.py` or `repair_vision_jsonl.py`. The vision path remains
CLI-only and deliberately so - the audit gate must stay a hard stop, and a
button that can be clicked past is not a gate.


## 9c. Verifying a UI change before it is served (2026-09-06)

Phase G shipped a layout bug past every check the project had. The checks were
not weak — they were the wrong kind:

| check                                   | result on the broken file |
|-----------------------------------------|---------------------------|
| `py_compile dashboard.py`               | clean                     |
| `node --check` on the extracted script  | clean                     |
| CSS braces balanced                     | 138 / 138                 |
| both patch markers present              | yes                       |
| `/api/embeddings`, `/api/entities` present | yes                    |
| JavaScript errors in the browser        | **none**                  |
| the page as a human sees it             | **destroyed**             |

`.sidebar`, `.main` and `.log-panel` each declare `grid-row:2`. The two new
`.splitter` divs did not. CSS Grid's auto-placement (css-grid-1 §8.5) positions
definite-row items first, in document order, and only then fills the leftover
cells with fully-auto items. So the three panes took columns 1–3 and the
splitters were swept into 4 and 5:

```
                       measured, headless Chromium 1680x980
  sidebar    x=0     w=320    column 1
  splitL     x=1334  w=6      column 4     <- wrong
  main       x=320   w=40     column 2     <- crushed into the 6px track
  splitR     x=1340  w=340    column 5     <- wrong
  log-panel  x=326   w=1008   column 3     <- wrong
```

The pipeline table — the entire screen — rendered 40px wide. Nothing threw.

**The rule this establishes: a layout change is not verified until something
has laid the page out.** Parsing it is not laying it out.

### The harness

`scripts/verify_ui.py` serves `dashboard_static.html` on 127.0.0.1:8899 with a
stand-in API (six documents chosen to hit the edges, including one with no
dates at all) and asserts 19 properties in a real browser. It never opens
`data/context.db`, never calls a provider and never touches the running
dashboard.

```powershell
# once, on a dev machine only - NOT a runtime dependency
pip install playwright
playwright install chromium

# every time dashboard_static.html changes
python scripts\verify_ui.py
python scripts\verify_ui.py --shots out\ui   # + screenshots for the record
```

Exit 0 means every assertion held. Non-zero means do not restart the dashboard.

The first three assertions are the ones that would have caught this:

```
  pane order left to right          panes appear in DOM order
  main is the widest pane           the content pane is not a sliver
  neither splitter is wider than 8px
```

Confirmed against the broken file as a negative control: 5/9, with the failure
naming the cause (`got ['sidebar','main','log-panel','splitL','splitR']`).

### Two further defects the render caught

* **Row height.** Embed + Entities pushed the actions cell onto a fourth
  wrapped line: 132.5px → 162.5px a row, one fewer book per screen. Tightening
  `.btn-act` padding *inside `.pipeline-table` only* (the class is used in other
  panels) brings it to 143.5px. Net cost of the two buttons: 11px, not 30px.
* **Reachability.** Once the panes genuinely resize, dragging the middle one
  narrow clips the Actions column, and with `overflow:visible` there is no way
  to scroll to it — Export, Full and the reader link become unclickable.
  Measured at `--lw 200px / --rw 620px`: a 900px table in an 808px box.
  `#pipelineWrap{overflow-x:auto}` fixes it. This defect did not exist before
  Phase G, because the panes could not be resized.

All three are in `scripts/patch_ui_phase_g_fix.py`, and folded into
`patch_ui_phase_g.py` so a fresh application is correct from the start.

### Applying the hotfix

`dashboard.py` serves the HTML with `send_from_directory` (line 511), i.e. it is
read from disk on every request. **The HTML fix therefore needs a hard refresh,
not a restart** — no job is interrupted:

```powershell
python scripts\patch_ui_phase_g_fix.py            # dry run
python scripts\patch_ui_phase_g_fix.py --apply
# then Ctrl+F5 in the browser
```

The `/api/embeddings` and `/api/entities` endpoints live in `dashboard.py` and
do require a restart — see §1, and the correction in §9d.

## 9d. Restarting the dashboard while jobs are running — a correction (2026-09-06)

I told you the running jobs "are subprocesses and survive" a dashboard restart.
That was asserted, not verified, and it is **wrong**. Reading the code:

`scripts/dashboard.py`, `_run_job`:

```python
proc = subprocess.Popen(
    job.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=str(ROOT), env=_child_env()
)
job.proc = proc
out, err = proc.communicate()
```

No `creationflags`, no Windows Job Object. `restart_dashboard.ps1` does
`Stop-Process -Id $procId -Force` on the **port listener only**. So:

* the children are **not** killed — Windows does not cascade the kill;
* but their stdout/stderr pipes have no reader any more. Each child runs until
  it fills the ~64 KB pipe buffer and then **blocks forever on write**;
* `proc.communicate()` dies with the parent, so `_persist_job()` never runs and
  `data/jobs.jsonl` never records the outcome.

They neither finish nor die. They sit there holding a DB connection, invisible
to the new dashboard's in-memory `JOBS` list, and a translate job that blocks
mid-document leaves the semaphore family with a writer nobody is tracking.

`_kill_proc()` does the right thing — `taskkill /F /T`, a tree kill — and that
is what the UI's **Pause All Jobs** button calls.

**RUNBOOK §1 already said this**: *"Stop cleanly: click 'Pause All' in the UI
(kills job subprocesses), then:"*. And `ENTERPRISE_ROADMAP.md`: *"No
multi-change restarts of a live system without a stated rollback."* The
procedure existed; I went around it.

### The procedure, in order

```powershell
Set-Location "C:\path\to\sanskrit-automatonv2"     # your repo root

# 1. Click "Pause All Jobs" in the dashboard (top of the Pipeline panel).
#    Then CONFIRM it, rather than trusting the button:
(Invoke-RestMethod http://127.0.0.1:5057/api/jobs/running).Count      # want 0

# 2. Only when that reads 0:
powershell -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1

# 3. Confirm the new endpoints answer (405 = "exists, wrong verb" = good;
#    404 = the restart did not pick up the patched dashboard.py):
foreach ($e in '/api/embeddings','/api/entities') {
  try   { Invoke-WebRequest "http://127.0.0.1:5057$e" -Method GET -ErrorAction Stop | Out-Null }
  catch { "{0,-18} {1}" -f $e, $_.Exception.Response.StatusCode.value__ }
}
```

Paused jobs are not lost work: OCR, ingest and translate are all resumable and
skip what is already done. A blocked-forever job **is** lost work.

### Rollback, and proving it before you need it

```powershell
# what Phase G backed up
Get-ChildItem backups\dashboard*.preG*,backups\dashboard*.preGjs*,backups\dashboard*.preGfix* |
  Sort-Object LastWriteTime | Format-Table Name,Length,LastWriteTime

# prove the rollback restores byte-for-byte, WITHOUT rolling back:
$b = (Get-ChildItem backups\dashboard_static.html.preG.* | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
Copy-Item $b "$env:TEMP\rollback_test.html"
python scripts\patch_ui_phase_g_js.py --help *> $null   # no-op, just proves the script runs
"backup bytes : {0}" -f (Get-Item $b).Length
"live bytes   : {0}" -f (Get-Item scripts\dashboard_static.html).Length

# actual rollback, if ever needed (UI only - no restart):
Copy-Item $b scripts\dashboard_static.html -Force        # then Ctrl+F5

# full rollback including the endpoints (needs Pause All + restart):
Copy-Item (Get-ChildItem backups\dashboard.py.preG.* | Sort-Object LastWriteTime | Select-Object -Last 1).FullName scripts\dashboard.py -Force
```

## 3g. Empty translations - causes and the outcome ledger (TRANSLATION_FILTERS_2026_09_27)

"[empty]" on the dashboard and its "skip" count mix never-sent rows
(SKIP-UI, SKIP-QUALITY) with PAID rows that came back empty. Since
2026-09-27 every paid-but-empty or salvaged verse is appended, with its
cause (model-empty | refusal-filter | echo-filter | salvaged) and the raw
model output, to data/translate_outcomes.jsonl, and the run prints
[EMPTY:<cause>]. Measure with scripts/diag_empty_translations.py (read-only);
ask the model again for specific verses with scripts/probe_empty_translations.py
(paid, metered). A capped budget now ABORTS a run (BudgetBlocked). The Hindi
prompt is hi-v2-2026-09-27. Full account:
docs/TRANSLATION_EMPTY_OUTCOMES_2026-09-27.md.


## 3h. Routine: measure, retry, rebuild (CONTINUITY_2026_09_27)

After any translate sweep, and at least weekly:

1. `& 'D:\Sanksrit Automatons\_ops_2026-09-10\block_BA_continuity.ps1' -Status`
   - This is read-only. It lists running jobs, shows the outcome ledger by cause, and prints the retry plan.
2. `... block_BA_continuity.ps1 -Queue`
   - This queues one dashboard job per document and language, covering only the verses a run went past and left empty.
   - It refuses to run if the estimate exceeds half the budget headroom.
   - A document marked mostly-new (mostly never-attempted verses) is skipped unless `-IncludeNew` is given.
3. When a document's jobs have finished, rebuild its Booksmith editions:
   - `python scripts/booksmith_build.py --db "data\context.db" --doc <code> --mode tri`
   - then the same command with `--mode hi`
4. Human review happens in Booksmith (http://127.0.0.1:8765). Only a project with `output_mode: reading` and no open findings is a reading edition. Everything else is an audit proof, and the Library labels it that way.

5. Refresh the public status on Srangam (it is a generated file, not live):
   `& 'D:\Sanksrit Automatons\_ops_2026-09-10\block_BD_status.ps1' -Emit -Commit`, then press Publish in Lovable.
   - This runs `D:\srangam-42267\scripts\emit_project_status.py`, which measures `context.db` read-only and commits only `src/data/projectStatus.ts`.
   - It refuses to commit if the Srangam repo has diverged from origin.

Operating rules (RUNBOOK_OPS_2026_09_27):
- **Run blocks in their own PowerShell window.** Closing the "Sanskrit Dashboard" window, or pressing Ctrl+C in it, kills the dashboard. It also drops every queued job (2026-09-27 14:46). The plan rebuilds them: `block_BA_continuity.ps1 -Queue`.
- **A second dashboard now refuses to start** (`[REFUSED]`, exit 3). The hub also refuses when port 5057 is taken.
  - To check for strays: `Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ? CommandLine -match 'dashboard.py'`.
  - More than one is a fault. Keep the one that owns port 5057, `(Get-NetTCPConnection -LocalPort 5057 -State Listen).OwningProcess`, and stop the other only if it has no child processes.
- **Model calls are bounded** by `MT_REQUEST_TIMEOUT` (seconds, default 120, set in `.env`). A stalled job (no change to `data\translation_progress.json` for 10+ minutes) is a network hang. Stop that job's `translate_passages` process, never the dashboard; the next job starts and the verse is retried by the next plan.

Never: run two dashboards, run `purge_empty_cache.py --yes` (it runs VACUUM), or edit `translations_l10n` by hand. `remediate_hi_artifacts.py` supersedes rows and archives the old ones to `translation_history`.

## 3i. Export editions (RUNBOOK_EXPORT_2026_09_30)

The Export button produces one of three editions, chosen by **Export As** in the left panel:

| Export As | File name | Contents |
|---|---|---|
| English only | `<doc>_<from>-<to>.html` | English |
| Hindi only | `<doc>_<from>-<to>_hi.html` | Hindi |
| Trilingual (Sa/En/Hi) | `<doc>_<from>-<to>_tri.html` | Sanskrit, English and Hindi side by side |

- **Export As is remembered** in the browser (localStorage) across reloads and restarts. Since EXPORT_MODE_VISIBLE_2026_09_30 each row button names the edition it will produce, and Export All asks for confirmation.
- **The edition is recorded** in `data/jobs.jsonl` as `"mode"` on export records (EXPORT_MODE_JOBLOG_2026_09_30). Older records have no `mode`; read the suffix of the output file instead.
- **"Trilingual export is broken"** on 2026-09-30 was a Hindi export: Export As had been left on Hindi. Check the newest files before debugging:

```powershell
Get-ChildItem exports\*.html | Select Name, @{n='Edition';e={ if ($_.BaseName -match '_tri$') {'tri'} elseif ($_.BaseName -match '_hi$') {'hi'} else {'en'} }}, LastWriteTime |
  Sort LastWriteTime -Desc | Select -First 15 | Format-Table -Auto
```

- **Export from PowerShell** (reads the database only; safe while the dashboard runs):

```powershell
python scripts\export_html.py --db data\context.db --doc <DOC> --out exports --sanskrit --hindi --side-by-side --title "<DOC> - Sanskrit / English / Hindi"
```

## 3j. OCR consensus in one command (RUNBOOK_CONSENSUS_2026_09_30)

Sections 3b, 3e and 3f describe the agreed standard. Tesseract runs on every page. Triage uses Tesseract confidence. Vision runs only on the pages that fail triage. The two readings are then merged, with vision as the source of record and Tesseract kept as the apparatus and the fallback. Until 2026-09-30 that chain was five manual steps. Nothing ran it, so most books were translated from raw Tesseract. See docs/OCR_CONSENSUS_2026-09-30.md.

```powershell
python scripts\ocr_consensus.py --doc <DOC>          # PLAN: triage + cost estimate + dry-run audit/merge. No spend.
python scripts\ocr_consensus.py --doc <DOC> --yes    # vision (metered, --max-usd 1.00 cap) -> repair -> merge --apply -> drift
python scripts\ocr_consensus.py --doc <DOC> --drift-only
```

- **Idempotent.** Every step skips work that is already done. The script never writes the database.
- **Drift report.** It lists every consensus page on disk as current, stale or missing-in-db, compared with the DB text. Exit code 3 means the DB is behind; the script then prints the exact re-ingest commands (backup, wipe, ingest from `data\raw_merged`, classify, translate en, QA, translate hi). Run those only while the dashboard reads "idle".
- **Re-translation after re-ingest is cheap.** The cache key is prompt version + source text. Pages whose text did not change are answered from the cache at no cost; only changed passages call the API.

**Lacuna census** (read-only, unicode-safe). It replaces SQL typed into PowerShell 5, which turns Devanagari into `?`:

```powershell
python scripts\measure_lacunae.py
python scripts\measure_lacunae.py --doc <DOC> --csv exports\lacunae_<DOC>.csv
```

**Hindi with or without the English reference.** Measure it before changing anything:

```powershell
python scripts\diag_hindi_ab.py --doc <DOC> --n 40          # dry run + cost
python scripts\diag_hindi_ab.py --doc <DOC> --n 40 --yes    # writes data\ab\hindi_ref_<DOC>_<stamp>.html
```


## Is the corpus up to date? (CORPUS_STATUS_2026_10_04, DOCS_2026_10_04)

`python scripts/corpus_status.py` is read-only and safe while jobs run. It gives one line per text.

It measures:

- OCR source share;
- drift against raw_merged;
- English and Hindi completeness, prompt currency and lacuna rate;
- approved images.

It returns one verdict in pipeline order: NEEDS-OCR, then NEEDS-REINGEST, then NEEDS-TRANSLATION, then AGED, then CURRENT.

`--commands` prints the next commands, in that order. Every one of them is idempotent, so running the status, then the commands, then the status again converges. "Negligible lacunae" is `--lacuna-ok` (default 5%). AGED means complete and clean, with some rows on older prompt versions; that is acceptable, and re-translation there is a choice, not a repair.


### Verdicts as of corpus_status v2 (CORPUS_STATUS2_2026_10_04, DOCS2_2026_10_04)

The verdicts, in order:

1. DERIVED-NEEDS-OCR
2. NEEDS-OCR
3. NO-SOURCE-PDF
4. NEEDS-REINGEST
5. NEEDS-TRANSLATION
6. AGED
7. CURRENT

Source damage is judged from **source debris** (`--debris-ok`, default 5%), never from lacuna rates. A derived doc (`resegment-devnum`) is repaired through its source. Each command line carries a cost estimate:

- vision at $0.0015 per page;
- translation at the measured $/passage from usage_log, which is a lower bound.

Work one book at a time, only when the dashboard reads idle, and re-run the status after each book.


### Ingest and translate guards (INGEST_SOURCE_2026_10_04, TRANSLATE_DEBRIS_GUARD_2026_10_04, DOCS3_2026_10_04)

**Ingest:**

- If complete OCR consensus exists in `data/raw_merged`, ingest uses it, even when it is asked for `data/raw`.
- With only partial consensus, ingest refuses. Finish the consensus, or pass `--source raw` deliberately.
- The plain glob `<doc>_*.jsonl` no longer picks up another doc's files (for example `<doc>_seg_*`).

**Translate:** it refuses repairable Tesseract text when all of these hold:

- more than 30% of passages carry debris;
- fewer than half the passages come from vision;
- page PDFs are in inbox.

Run `ocr_consensus.py --threshold 101 --include-unassessed` first. Override with `--allow-debris`, or with `SA_ALLOW_DEBRIS=1` for the dashboard.

Both refusals exit with code 3 and print the next command.


## Status page, image queue, context engine (DOCS4_2026_10_04)

- One read-only page with everything in one place:
  `python scripts/status_report.py`, which writes `exports/status/STATUS_latest.md`.
  It covers code HEAD, prompts, corpus verdicts and spend, semantic index (stale and orphaned vectors, guard triggers), images, 7-day spend, maintenance ticks, backups and the Srangam panel's age.
- Image jobs run one at a time, in the order asked, and are listed with progress on the Images page (IMAGES_QUEUE_2026_10_04). This needs one dashboard restart while idle.
- The SanskritMaintenance task (every 3 h, idle only) keeps embeddings current. Since BRAIN_FRESH_2026_10_04 it also re-embeds passages re-translated after their vector. `python scripts/build_embeddings.py --plan` shows the counts and makes no call.
- Findings, corrections and the UI path (U1 to U4): `docs/PLATFORM_2026-10-04.md`.


## Shelf, covers, spend (DOCS5_2026_10_04)

- **Shelf:** `http://127.0.0.1:5057/shelf`, after one restart while idle.
  - Collections: `python scripts/collections_cfg.py --show`. `--draft` writes `configs/collections.json` for editing.
  - Titles confirmed on the page go to `configs/doc_titles.json`.
- **Covers:** `python scripts/images.py cover --doc <code> --yes` (or `--brief "..."` to write the idea yourself). Then approve the idea, generate, and approve the image. Use `export_html --images approved` to put it on the title page.
- **Plates at book proportions:** `$env:SA_IMAGE_ASPECT="3:4"; $env:SA_IMAGE_SIZE="2K"` before `images.py generate` or `regenerate`. A WARN means the API ignored the setting.
- **Spend:**
  - `python scripts/spend_audit.py` shows recorded vs repriced spend, estimated rows, and the call sites.
  - Check the budget before translating after SPEND_TRUTH; recorded prices rose.


## Meters, gates, orphans (DOCS6_2026_10_04)

- **Orphans:**
  - `python scripts\diag_orphans.py` shows where they are (read-only). Add `--db <backup>` to see whether they were already there.
  - `python scripts\fix_orphans.py --apply` removes them. Run it while the dashboard is idle; it takes a backup first.
- **Spend before a run:**
  - `python scripts\corpus_status.py --commands`: the vision $/page line says "measured" or "fallback".
  - `python scripts\spend_audit.py --days 1`: Ask now appears as `ask` and `ask_embed`.
- **Cap reached:** Ask returns 402 with sources, and `extract_entities` stops at a batch boundary. Raise the cap with `python scripts\set_budget.py --cap <usd> --unpause`.


## Documentation map addendum (DOCS7_2026_10_04)

The map in section 0 predates these. Read them as part of it:

- `docs/ENTERPRISE_PATH_2026-10-04.md`: the forward plan, phases 0-4, and what is true where documents disagree. It supersedes `docs/ENTERPRISE_PATH_2026-09-06.md` section 4 and `ENTERPRISE_ROADMAP.md` as the plan.
- `docs/PLATFORM_2026-10-04.md`: this week's changes. Section 10 corrects section 9.
- `docs/EDITIONS_AND_IMAGES_2026-10-03.md`: editions, plates, the image library.

Rules added on 2026-10-04:

- **Reading a backup:** `python scripts\diag_orphans.py --db <backup> --backup`. For any other read-only open of a backup, use the URI `?mode=ro&immutable=1`. Never use `immutable` on the live `data/context.db`.
- **Prepaid credit:** a translation run that prints `[ABORT] ... prepaid credits are depleted (HTTP 402)` has stopped cleanly. Top up in AI Studio, then re-run; done verses are kept.
- **Srangam migrations:** `_ops_2026-09-10\srangam_migration_audit_2026_10_04.sql` is read-only. Do not hand-insert rows into `supabase_migrations.schema_migrations`.


## Vignettes and the anthology (DOCS9_2026_10_05)

Every step is a dry run unless `--yes` is given.

- **Stories for drawn images:**
  - `python scripts\stories.py write --doc <code> --images --max 6` (dry run), then add `--yes`.
  - `python scripts\stories.py list --doc <code>`, then `show --id N`, then `approve --id N`.
  - A draft whose check failed needs `--force` after you have read it.
- **Mining episodes:**
  - `python scripts\stories.py mine --doc <code> --max 12` (dry run), then add `--yes`.
  - Then `write --doc <code> --candidates --max 6 --yes`.
- **Anthology:**
  - `python scripts\stories.py anthology --docs a,b --title "..."`.
  - Then `python scripts\export_pdf.py exports\anthology_<date>.html`.
- **Approve the story only after reading its notes.** Where the notes flag a damaged reading, fix the source passage first, through consensus or re-OCR. Never fix it in the story alone.


## Stories page, gaps, running heads (DOCS10_2026_10_05)

- **Stories:** open `http://127.0.0.1:5057/stories` and pick the text.
  - Read each card's notes and problems.
  - Click a citation to see the passages.
  - Edit if needed (the check re-runs), then Approve.
  - Use the page, not PowerShell, for any edit with Devanagari or IAST.
- **After a prompt or verify change:** press "Check again" on the old drafts (free), and "Rewrite" a story the notes or problems condemn (about $0.01).
- **A text stuck at NEEDS-TRANSLATION with a few rows that never translate:**
  - First run `python scripts\corpus_status.py --doc <code>`. Gaps within the allowance now show as a note.
  - Then `python scripts\classify_noise.py --doc <code> --running-heads` (dry run) and read the listed lines.
  - Only then add `--apply`, with the dashboard idle and after a backup.


## Pictures, books and the brain from the Stories page (DOCS11_2026_10_07)

- **A picture for a story** (in Review): Propose image (about $0.003), then read the idea. Then Draw it (about $0.09-0.13), then Approve image. Edit the idea in `/images` when the iconography is wrong. Drop it to start again.
- **A book** (in Make a book):
  - Tick the texts, then the stories, then set the order, the title and the readers.
  - "Make reading book" writes `exports\book_<title>_<date>.html` and its PDF.
  - "Booksmith edition" builds through Booksmith. It writes the sidecar `exports\booksmith\stories-<title>__story.json`, and the PDF link appears under Recent books.
- **The brain.** The chip in the header says how many items are not yet in the Ask index. Maintenance adds them every run; "Update brain" adds them now.
- **Running heads**, in order:
  - `python scripts\classify_noise.py --doc <code> --running-heads` (dry run). Read the listed lines.
  - Back up.
  - Add `--apply`, and add `--include-translated` to also tag the translated copies.
  - Then run `corpus_status --doc <code>`.


## Younger readers, graphic novels, cloud pre-flight (DOCS12_2026_10_07)

- **A version for younger readers.** On an approved story's card, under "For younger readers", click "Write version" (about $0.01). Read it, Edit if needed, then Approve. Books for those ages use it.
  - From the command line: `python scripts\stories.py retell --id N --audience young --yes`, then `python scripts\stories.py variant --id N --audience young --action approve`.
- **A graphic novel.** In Stories, open "Graphic novels", choose the story, pages and readers, then "Plan the pages" (about $0.01).
  - Read every page and correct captions and scenes (Save checks them).
  - "Draw cast", then "Draw pages", then Approve each page, then "Make the book".
  - From the command line, `python scripts\novel.py plan --story N --pages 12 --yes`, then `cast --id K --yes`, `draw --id K --yes`, `approve-page`, `approve`, `build`.
- **Before restarting the dashboard,** look at the header: a running translation is killed by a restart, and it resumes when started again. Keep the machine awake (lid open, sleep off) for long runs.
- **Cloud.** Paste `docs\cloud\C0_preflight_2026-10-07.sql` into the Lovable Cloud SQL editor one query at a time (read-only) and keep the results. C1 is applied only after that, and only after the file has been read through.


## Greyed-out story buttons, the brain from the command line, Srangam S1 (DOCS13_2026_10_07)

- **The Book, Graphic novel or "For younger readers" buttons are greyed.** Nothing of that text is approved yet.
  - On the Stories page press "Check all again (free)". Then choose the status filter "draft, check passes", read each story (click a citation to see its passages) and press Approve.
  - Drafts in "draft, check fails" need Edit, Rewrite or "Approve anyway".
  - From the command line: `python scripts\stories.py verify-all --doc markandeya_purana`.
  - For a proof copy before anything is approved, tick Proof in the Book tab.
- **Update the brain from PowerShell.** Run `python scripts\brain_items.py --db data\context.db`. It now reads `.env` itself. Maintenance step b2 does the same every 3 hours when the dashboard is idle.
- **A translation gap that never closes.** If corpus_status says "N never sent", those rows are page 0 or carry no translatable Sanskrit (a lone danda, a stray mark). The translator will not send them, and that is correct; they are not work.
- **Srangam S1.** Paste `docs\cloud\S1_srangam_heal_2026-10-07.sql` into the Lovable Cloud SQL editor one block at a time: H1, H2, H3, H4. Then run `block_BE_reader.ps1 -Verify`. Never insert into supabase_migrations.schema_migrations by hand.


## Stories that still fail the check; the Ganita code; Srangam S2 (DOCS14_2026_10_07)

- **After `patch_verify_names_2026_10_07.py`,** run `python scripts\stories.py verify-all --doc markandeya_purana`. Expect 11 pass and 2 fail. Approve only after reading.
  - **#3:** fix who Vapu is first (see PLATFORM section 17).
  - **#5:** change "Draupadi" to "the daughter of Drupada", or approve anyway with a note.
  - **#10:** Rewrite.
- **Ganita.** `python scripts\corpus_status.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`. A wrong `--doc` now says which codes are close.
  - Resume from the dashboard (translate_both, as on 6 Oct) with the machine kept awake. Allow 6-11 hours for the English alone at the measured rate.
- **Srangam S2.** Paste `docs\cloud\S2_srangam_followup_2026-10-07.sql` one block at a time (G1-G5, all read-only) and keep the CSVs.


## Srangam: refresh the status panel, lock down functions, publish a text; Ganita OCR first (DOCS15_2026_10_07)

- **Ganita.** Do not resume translation. Run `python scripts\corpus_status.py --commands --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` and follow its order: `ocr_consensus.py` plan (free), then `--yes --max-usd`, then `--drift-only` (the re-ingest block), then translate.
- **S3.** Paste L1, L2, L3 and L4, then L5 ten minutes later, and L5 again the next day for the nightly jobs. Re-run L4 after any Lovable change that adds a database function.
- **The status panel.** Git runs by hand, in `D:\srangam-42267`; no script pushes main.
  1. Look first: `git status -sb`, `git fetch origin`, `git rev-list --left-right --count HEAD...origin/main`.
  2. Switch and update: `git switch main`, then `git pull --ff-only origin main`.
  3. Run `block_BE_reader.ps1 -ReaderLive -NoPush`. It regenerates the panel with fresh numbers and the reading page, and commits locally.
  4. Read `git show --stat HEAD`.
  5. Push main yourself, then Publish in Lovable.
  - Branch feat/s1-nartiang-backlink (6b15ee7) is then superseded; delete it when you are content.
- **Publishing a text to /texts.**
  1. `python scripts\publish_srangam.py --doc <code> --gate-report`, then `--dry-run`, then `--emit-sql <dir>`.
  2. Paste 00_text.sql, each NN_passages.sql and 99_verify.sql. The text lands unpublished.
  3. After review, run `UPDATE public.srangam_texts SET published = true WHERE doc_code = '<code>';`, then `block_BE_reader.ps1 -Verify`.


## Srangam: refresh the status panel, apply C1, deploy and run C2 (DOCS16_2026_10_07)

- **Run an ops script as a file, never by pasting its text:** `& 'D:\Sanksrit Automatons\_ops_2026-09-10\block_BE_reader.ps1' -Verify`. Pasted text runs with no switches.
- **The status panel** (git by hand, in `D:\srangam-42267`):
  1. `git status -sb`, then `git switch main`, then `git pull --ff-only origin main`.
  2. `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_site_line_2026_10_07.py" --check`, then the same without `--check`.
  3. `python scripts\emit_project_status.py --db "D:\Sanksrit Automatons\sanskrit-automatonv2\data\context.db" --site-reader --check`, then the same without `--check`.
  4. `git diff --stat`, then commit the two files.
  5. Push main yourself, then Publish in Lovable.
- **C1.** Paste `docs\cloud\C1_corpus_brain_2026-10-07.sql` whole, run it once, then V1-V4 one at a time.
- **C2.**
  1. On main in `D:\srangam-42267`, copy `index.ts` and `lib.ts` from `docs\cloud\C2_embed-published-passages` into `supabase\functions\embed-published-passages\`.
  2. Append `[functions.embed-published-passages]` / `verify_jwt = false` to `supabase\config.toml`.
  3. Commit, push, Publish.
  4. Confirm the function is listed in Lovable Cloud (Edge functions); if it is not, ask Lovable in its chat to deploy it.
  5. Then run `docs\cloud\C2_run_and_schedule_2026-10-07.sql` R1-R5.
- **Recall check, any time:** `python scripts\recall_check_768.py --db "D:\backups\<a backup>.db" --immutable` (add `--dims 1536` to measure 1536).


## Finish C2; install search by meaning (C3a) (DOCS17_2026_10_07)

- **C2.** Run `docs\cloud\C2_run_and_schedule_2026-10-07.sql` R3, then R2, three more times, until R4 shows 1,655 vectors. Then run R5, and R6 if you want it nightly.
- **C3a**, in `D:\srangam-42267` on main:
  1. `git pull --ff-only origin main`.
  2. `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_texts_search_2026_10_07.py" --check`, then the same without `--check`.
  3. `npm run typecheck`.
  4. `npx vitest run src/__tests__/corpus-search.test.ts src/__tests__/corpus-texts-loader.test.ts src/__tests__/query-bounds.test.ts`.
  5. `npm run build`.
  6. Commit the 8 paths, push main yourself, then ask Lovable to deploy the edge functions and Publish.
  7. Open /texts and search, for example "why did the king sell his wife and son".
- **The patch refuses** if any of its files already exists with other content, or if an anchor moved. Nothing is written in either case.


## Finish C2; story fixes; Srangam W8 and W5 (DOCS18_2026_10_07)

- **C2.** Run R3 once more, then R2: expect "taken":155 and "pending_after_estimate":0. Then R4: 1655 | 1 | 1536 | 1536, and no pending rows. R6 (nightly at 04:15 UTC) is optional.
- **Story fixes**, from the automaton root, with the dashboard idle:
  1. Back up: `python scripts\db_backup.py data\context.db D:\backups\context_pre_storyfix_20261007.db`.
  2. `python scripts\story_fix.py --file docs\stories\fix_markandeya_2026-10-07.json --check`, then the same without `--check`.
  3. `python scripts\stories.py verify-all --doc markandeya_purana`: expect 13 pass, 0 fail.
  4. Read each story (`stories.py show --id N` or the Stories page), then approve it: `python scripts\stories.py approve --id N`. Approval stays a person's decision.
- **Srangam**, in `D:\srangam-42267` on main after `git pull --ff-only origin main`:
  1. `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_load_w8_2026_10_07.py" --check`, then the same without `--check`.
  2. The same two steps for `patch_reader_marks_2026_10_07.py`.
  3. Checks: `npm run typecheck`; `npx vitest run src/__tests__/load-w8.test.ts src/__tests__/reader-marks.test.ts src/__tests__/texts-reader.test.tsx src/__tests__/corpus-search.test.ts src/__tests__/query-bounds.test.ts`; `npm run build`.
  4. Commit the 6 paths, push main yourself, then click Publish in Lovable. No edge function changes.


## Exports, novel layout and the publication gate (DOCS19_2026_10_07)

- **Apply.** From the automaton root: `python scripts\patch_exports_gate_2026_10_07.py --check`, then the same without `--check`.
- **Test.** `python -m unittest tests.test_exports_gate_2026_10_07 tests.test_publish_bridge tests.test_publish_engine_2026_10_07 tests.test_novel_2026_10_07 tests.test_export_images tests.test_export_pdf`.
- **The ten withheld verses**, published without re-pasting whole texts:
  1. `python scripts\publish_srangam.py --doc markandeya_purana --emit-sql D:\backups\srangam_sql --only 11.2,73.3,99.2`
  2. `python scripts\publish_srangam.py --doc AphorismsOfSandilya --emit-sql D:\backups\srangam_sql --only 57.6,57.7,69.8,72.2,72.3,72.6,75.6`
  3. Paste each doc's 00_text.sql, 01_passages.sql and 99_verify.sql in the Lovable Cloud SQL editor. 99_verify should show local = remote (1,219 and 446) and stale_on_site 0.
  4. Cron job 9 embeds them at 04:15 UTC, or run R3 once now (expect "taken":10).
  5. The folder for each doc then holds only these files (emit_sql writes a fresh set each time).
- **Novel #1, rebuilt.** `python scripts\novel.py build --id 1 --cover 8`, then `python scripts\export_pdf.py "<the html it names>"`.


## When the Live tab says "stopped"; the spend cap (DOCS20_2026_10_08)

- **"Stopped."** The run ended without finishing. Start Translate for that text again: verses already translated are skipped. Keep the dashboard's console open while a translation runs; closing it ends the run (exit code 3221225786).
- **Spend cap.** In the dashboard, open Usage, press Reload, set "New cap" and press Set cap; Resume appears when the cap has paused paid work. From a terminal: `python scripts\set_budget.py --cap 40 --unpause`.
- **Load the dashboard change.** `python scripts\patch_live_budget_2026_10_08.py --check`, then the same without `--check`, then restart the dashboard while it is idle.


## The private corpus mirror (DOCS21_2026_10_08)

- **What it is.** A private PostgreSQL copy of the whole brain, for querying from anywhere: `docs/CORPUS_MIRROR_2026-10-08.md`, steps 1-9.
- **The plan.** `python scripts\corpus_sync.py` prints what would be sent and sends nothing. Add `--apply` to send.
- **Check the connection.** `python scripts\corpus_sync.py --hello`.
- **One document.** `python scripts\corpus_sync.py --apply --doc markandeya_purana`. A partial run never retires documents.
- **HELD lines.** A large retire (a re-segmented or emptied document) is held. Read the line, then re-run with `--allow-mass-retire` if it is right.
- **"stopped=budget".** `--max-mb` was reached; the next run carries on.
- **The scheduled tick.** `scripts\corpus_mirror_task.ps1`, every 2 hours, logs to `D:\backups\corpus_mirror_log.txt`. It skips quietly until CORPUS_SYNC_SECRET is in .env.
- **Rotating the secret.** Make a new one, replace it in .env and in Lovable Cloud -> Secrets. Requests signed with the old one get 401.


## Watching a mirror push (DOCS22_2026_10_08)

- **Lines while it runs.** A run prints `[m:ss]` lines: what the mirror holds, each document as it is sent, batches of large ones, and "compared N/63 documents".
- **From a second window.** `python scripts\corpus_sync.py --status` shows mirror rows against rows here, per table. It is read-only and safe during a push.
- **No new line for several minutes?** Run --status twice, a minute apart. If the mirror's counts rise, it is working. If they do not, press Ctrl+C and run it again; it sends only what is missing.


## The mirror after C4b; reading it on the site (DOCS23_2026_10_08)

- **"_scheme" error from corpus_sync.py.** The mirror is on the old digest: apply `docs/cloud/C4b_mirror_digests_2026-10-08.sql` (steps A and B in its header), then run again.
- **Check the digests in the SQL editor.** K1-K3 at the end of the C4b file. If K2 lists a table, run `SELECT corpus._rebuild_index('<table>');` for it.
- **Who may read /corpus.** `SELECT mode FROM corpus.reader_access;`
  - Readers only: `UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();`
  - Add a reader: `INSERT INTO corpus.readers (user_id, note) VALUES ('<id from auth.users>', 'name');`
  - Admins only: mode `'admins'`.
- **"Meaning search is not switched on yet" on /corpus.** Deploy the edge function `search-corpus` through Lovable. Word search and reading work without it.


## The dashboard runs with no window; signing in on Srangam (DOCS24_2026_10_08)

- **Apply, from the automaton root.**
  1. `python scripts\patch_dash_hidden_2026_10_08.py --check`, then the same without `--check`.
  2. `python -m unittest tests.test_dash_hidden_2026_10_08`.
  3. With the dashboard idle: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_dashboard.ps1`.
- **Every day.** Each of these is `scripts\restart_dashboard.ps1` with:
  - no switch: restart. It refuses while a job runs.
  - `-Status`: who listens, the jobs, the newest logs. It changes nothing.
  - `-Stop`: stop it. It refuses while a job runs.
  - `-Force`: cut running jobs off.
  - `-Window`: the old visible window.
- **The log.** `Get-Content -Wait -Tail 40 -Encoding UTF8 <the .err.log it names>`. The logs are in `D:\backups\dashboard_logs` and are kept 14 days.
- **What this changes about closing windows.** It replaces the DOCS20 advice to keep the dashboard's console open.
  - A dashboard started by the script has no window to close.
  - A dashboard started any other way (`python scripts\dashboard.py` in a terminal, or `-Window`) still ends with its window, and so do its runs.
- **It does not come up.** The script prints the last lines of both logs.
- **Srangam sign-in.**
  - A signed-in account that is not an admin sees "This area is for the site's editors" at /admin.
  - /auth sends it to /corpus.
  - Admins are no longer bounced through /auth after signing in.
  - To apply, in `D:\srangam-42267`, run `patch_auth_role_2026_10_08.py --check`, then the same without `--check`; then typecheck, the tests and the build; then push, then Publish.


## Reading the texts: apply READER_NAV; search-corpus deploy (DOCS25_2026_10_08)

1. **Lovable Cloud SQL editor.** Paste `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql`, then run N1: anon false, authenticated true.
2. **Srangam, in `D:\srangam-42267` on main.**
   - Run `git pull --ff-only origin main`.
   - Run `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_reader_nav_2026_10_08.py" --check`, then the same without `--check`.
   - Run `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Add the 16 paths it names, commit, and push main yourself.
3. **Lovable.** Deploy `search-corpus` (it now imports only from its own folder), then Publish.
4. **Check.**
   - Open `/corpus/nirukta` and choose Contents: pages with scan ranges.
   - Go to scan page 18.
   - Find "earth" by words, then by meaning.
   - Read `/texts/markandeya_purana` with "Side by side" on a wide screen.
- **If Contents says "not available yet".** C5b is not applied. The pages are still listed.
- **If find by meaning says "not switched on yet".** search-corpus is not deployed.


## The library on the site: apply C6 and the Srangam patch (DOCS26_2026_10_08)

1. **Lovable Cloud SQL editor.** Paste `docs/cloud/C6_corpus_library_2026-10-08.sql`. Then run L1 at its end: anon false and authenticated true on all five functions.
2. **Srangam, in `D:\srangam-42267` on main.**
   - Run `git pull --ff-only origin main`.
   - Run `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_library_l1_2026_10_08.py" --check`, then the same without `--check`.
   - Run `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Add the 15 paths it names, commit, push, then Publish in Lovable. There is no edge function in this one.
3. **When the shelves change** (the Shelf page's "move to", or an edit of collections.json):
   - Run `python scripts\emit_corpus_shelf.py --srangam D:\srangam-42267 --check`.
   - If it says STALE, run it without `--check`, then commit `src/data/corpusShelf.json` in Srangam.
4. **Stories appear on the site** when they are approved on the desk. Use `python scripts\stories.py approve --id N`, or the Stories page; the next mirror run carries the approval. Editors (admins) see drafts on the site, marked as drafts.


## Roles on Srangam: apply C7 and the RBAC patch (DOCS27_2026_10_08)

1. **Lovable Cloud SQL editor.**
   - Run `SELECT enum_range(NULL::public.app_role);`. Expect {admin,moderator,user}.
   - Run `docs/cloud/C7a_rbac_roles_2026-10-08.sql` ALONE.
   - Run the check again. Expect {admin,moderator,user,super_admin,researcher}.
2. **Run C7.** Paste the whole `docs/cloud/C7_rbac_researchers_2026-10-08.sql`, then run the checks V1 to V6 at its end:
   - V1: your email with admin and super_admin;
   - V2: two policies;
   - V3: anon true only for research_invite_peek;
   - V4: one trigger;
   - V5: the audit log;
   - V6: the mode is still signed_in.
3. **Srangam (D:\srangam-42267, on main).**
   - Run `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_rbac_2026_10_08.py" --check`, then without --check.
   - Then `npm run typecheck`, `npx vitest run` and `npm run build`.
   - `git add` the explicit paths, commit, push, and Publish in Lovable.
4. **First invitation.**
   - Sign in. Open /admin/researchers (the sidebar shows Researchers and the badge says Super admin).
   - Invite an address you can read. Open the link in a private window. Create the account, confirm it if asked, and accept.
   - Check that the person appears under People with access.
5. **Close the corpus to plain sign-ups** (only after step 4 works). On /admin/researchers choose "Invited researchers", or run:

   `UPDATE corpus.reader_access SET mode = 'readers', updated_at = now();`

   To reopen, set the mode back to signed_in.
6. **Rollback.** At the head of the C7 file. The site needs no rollback: without C7 it behaves as before.


## Roles on Srangam: apply C7 (corrected order) and the docs follow-up (DOCS28_2026_10_08)

Srangam 4d70389f already carries the pages. Only the database and the docs remain.

1. **Preflight.** Open `docs/cloud/C7_checks_2026-10-08.sql`. In the Lovable Cloud SQL editor, run P1 to P7, one query per paste, and Export CSV each result into `D:\backups\rbac_2026-10-08\`.
2. **C7a, alone.** Clear the editor. Paste ONLY `docs/cloud/C7a_rbac_roles_2026-10-08.sql` and run it.
   - Then clear the editor and run V0 on its own. Expect {admin,moderator,user,super_admin,researcher}.
   - Never add anything to C7a's paste. A SELECT there is error 55P04, and the whole paste rolls back.
3. **C7, in one paste.** Clear the editor. Paste the whole `docs/cloud/C7_rbac_researchers_2026-10-08.sql` and run it.
   - If it says "run C7a first", step 2 did not commit: repeat step 2.
4. **Verify.** Run V1 to V7, one query per paste, and export each result.
5. **Srangam docs (D:\srangam-42267).**
   - Run `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_rbac_docs_2026_10_08.py" --check`, then without --check.
   - `git add` the two docs, commit, push. Publish is not needed for docs.
6. **Check on the site** (after Publish of 4d70389f).
   - Sign in. /admin/researchers shows the Super admin badge, and no notice that the roles functions are missing.
   - Invite an address you can read. Open the link in a private window, create the account, confirm it, and accept. The person appears under People with access.
7. **Close the corpus to plain sign-ups,** only after step 6. Choose "Invited researchers" on /admin/researchers; this is audited.


## Health of everything scheduled (DOCS29_2026_10_08)

1. **On the PC (PowerShell).**
   - `Get-ScheduledTaskInfo` for SanskritCorpusMirror, SanskritMaintenance and SanskritDBBackup: LastTaskResult 0.
   - Then the tails of `D:\backups\corpus_mirror_log.txt`, `maintenance_log.txt` and `backup_log.txt`.
2. **In the Lovable Cloud SQL editor.** `docs/cloud/OPS_health_2026-10-08.sql`, H1 to H9, one per paste, read-only. Export the results to `D:\backups\ops_<date>\`.
3. **If H3 shows passages > vectors, or H4 shows rows pending:** the nightly job 9 has not run since they were pasted. Wait for 04:15 UTC, or run C2's R3 once (`docs/cloud/C2_run_and_schedule_2026-10-07.sql`) and then R2.
4. **If H7 lists a text:** its English is newer than the last idle maintenance run. The next SanskritMaintenance run embeds it, and the mirror carries it two hours later at most.


## Pictures and graphic novels on the site (DOCS30_2026_10_09)

**Switching it on, once.** Each step's commands are in `docs/MEDIA_AND_CORNER_2026-10-09.md` and in the reply of 2026-10-09.
1. **Back up.** `python scripts\db_backup.py`.
2. **In the SQL editor.** `docs/cloud/C8_checks_2026-10-09.sql` P1-P3, then C8 in one paste, then V1-V3. One query per paste; export each to `D:\backups\media_2026-10-09\`.
3. **Srangam.**
   - `scripts\patch_srangam_media_2026_10_09.py --check`, then without `--check`.
   - `npm run typecheck`, `npx vitest run` and `npm run build`.
   - Commit the listed paths and push.
4. **Lovable.** Ask Lovable to deploy `corpus-media` without changing its code. No new secret is needed.
5. **The desk.**
   - `python scripts\corpus_media.py --hello`. Expect `corpus-media c8.1` and `drive: true`.
   - Then `python scripts\corpus_media.py` (the plan).
   - Then `--apply`.
6. **Check.** D1-D5 in the SQL editor. Publish in Lovable.
   - `/corpus/images` as an admin shows drafts.
   - In a private window, as a reader, only approved pictures appear.
7. **The schedule.**
   - `python scripts\patch_media_task_2026_10_09.py --check`, then without `--check`.
   - The next SanskritCorpusMirror tick logs "DONE - corpus media rc=0".

**When something is wrong.**

| Seen | Meaning | Do |
|---|---|---|
| `--hello`: HTTP 404 | The function is not deployed | Step 4 |
| HTTP 422 `corpus_media_state ... Could not find` | C8 is not applied | Step 2 |
| HTTP 401 `bad signature` | The secret in `.env` and in Lovable Secrets differ | Make them the same, as for the mirror |
| `HELD: ... not in the mirror yet` | That text is not in schema corpus | `corpus_sync.py --apply` first |
| HTTP 502 `Drive upload failed` | The service account cannot write to the Shared Drive | Check `GOOGLE_SERVICE_ACCOUNT_JSON` and that the account is a member of the Shared Drive (as for `tts-save-drive`) |
| The site says "not available here yet" | C8 is not applied, or not published | Steps 2 and 6 |
| A picture shows "This picture is not available" | No rendition for it, or it is not visible to this reader | D2; run `--apply` again |
| `refusing to retire N of the site's M pictures` | `--db` points at the wrong database | Check `--db`; `--allow-mass-retire` only if it is right |


## The Researchers' Corner (DOCS31_2026_10_09)

**Switching it on, once.** The commands are in `docs/RESEARCHERS_CORNER_2026-10-09.md` and in the reply of 2026-10-09.
1. **Back up.** `python scripts\db_backup.py`.
2. **SQL editor.** C9 checks P1-P2, then C9 in one paste, then V1-V4.
3. **Srangam.**
   - `patch_srangam_corner_2026_10_09.py --check`, then without `--check`.
   - Typecheck, tests and build.
   - Commit the listed paths and push.
4. **Lovable.** Ask Lovable to deploy `corpus-desk` unchanged, then Publish.
5. **The desk.**
   - `python scripts\corner_worker.py --hello`.
   - Register SanskritCornerWorker (every 10 minutes, `scripts\corner_task.ps1`).
   - `Start-ScheduledTask -TaskName SanskritCornerWorker`.
6. **The first request.** Ask for a story from passages as the super admin. Approve it from its page once written.

**Every day.**
- **Corner, Queue.** Approve or reject researchers' requests.
- **When the desk last came.** The Corner's status strip, or C9 D3.
- **What it did.** `D:\backups\corner_worker_log.txt`.
- **Every sync command.** `docs/SYNC_COMMANDS_2026-10-09.md`.


## Srangam: pull before you push; LOAD_L1 (DOCS32_2026_10_09)

**Lovable pushes its own commits.** For example, it regenerates `src/integrations/supabase/types.ts` after a database change. A push from the desk is then refused ("fetch first"). Before every Srangam push:

    git fetch origin
    git log --oneline -3 origin/main
    git diff --stat HEAD...origin/main
    git pull --rebase --autostash origin main
    npm run typecheck ; npx vitest run ; npm run build
    git push origin main

`--autostash` puts the local `bun.lock` aside and back. If a rebase stops, `git rebase --abort` returns to where you were.

**LOAD_L1_2026_10_09** (fewer questions per page):
1. `python "D:\Sanksrit Automatons\sanskrit-automatonv2\scripts\patch_srangam_load_l1_2026_10_09.py" --check`, from `D:\srangam-42267`.
2. The same without `--check`.
3. Typecheck, tests and build.
4. Commit the five files it names, pull before you push, push, and Publish in Lovable.

Afterwards a page asks `has_role` and `my_roles` once each.

**Was the database slow?** Run this read-only check in the SQL editor. If `extensions.pg_stat_statements` is not found, use `pg_stat_statements`.

    SELECT calls, round(mean_exec_time::numeric, 1) AS mean_ms, round(max_exec_time::numeric, 1) AS max_ms,
           left(regexp_replace(query, '\s+', ' ', 'g'), 100) AS query
    FROM extensions.pg_stat_statements
    WHERE query ILIKE '%corpus_reader_%' OR query ILIKE '%corner_%' OR query ILIKE '%my_roles%'
    ORDER BY max_exec_time DESC LIMIT 20;


## State and Learn: switching on (DOCS33_2026_10_09)

The order matters: C10a goes in before the desk gets worker 1.1.
1. **SQL editor.**
   - `docs/cloud/C10a_checks_2026-10-09.sql` P1, then C10a in one paste, then V1-V2.
   - `docs/cloud/C11_checks_2026-10-09.sql` P1-P2, then C11 in one paste, then V1-V3.
2. **The desk.**
   - `python scripts\patch_corner_worker_state_2026_10_09.py --check`, then without `--check`.
   - Then `python -m unittest tests.test_corner_worker_2026_10_09 tests.test_corner_worker_state_2026_10_09`.
   - Release.
   - The next SanskritCornerWorker round runs 1.1.
3. **Srangam.**
   - `patch_srangam_state_learn_2026_10_09.py --check`, then without `--check`.
   - Typecheck, tests and build.
   - Commit the paths it names, pull before you push, push, then Publish.
4. **Look.**
   - The Corner says "Next round about HH:MM".
   - Editors see the Mirror, Pictures and Desk spend chips and the Sync tab.
   - `/corpus/learn` shows 20 quests to a researcher, 23 to an editor.

**When a mirror run stops with a statement timeout.** The database allows each write 8 seconds.
- Send that table in small batches: `python scripts\corpus_sync.py --apply --doc <code> --tables vectors --batch-kb 120`.
- Client 4.3 does the halving by itself.
- If one row times out, check for locks and long transactions (`docs/RESEARCHER_EXPERIENCE_2026-10-09.md`; the Sync Console's "Diagnose a timeout").


## State and Learn: if worker 1.1 went on before C10a (DOCS34_2026_10_09)

C10a must go in before the desk runs worker 1.1. Without C10a, C9's `corner_desk_report` takes each progress report as the request's result and as a new start.
1. **SQL editor, read-only:** `SELECT id, status FROM corner.requests WHERE status IN ('claimed', 'running');`
2. **No rows:** nothing was touched. Paste C10a (`docs/cloud/C10a_corner_state_2026-10-09.sql`) in one paste, then its V1 and V2.
3. **A request ran under 1.1 before C10a:**
   - Its result is right once it is done, because the done report carries the whole result.
   - Its `started_at` is the time of its last progress report.
   - `corner.events` has one `desk_running` row per report.
   - Nothing needs repairing by hand. Paste C10a as in step 2.

**A backup by hand.** `db_backup.py` takes a source and a destination:

```powershell
python scripts\db_backup.py "D:\Sanksrit Automatons\sanskrit-automatonv2\data\context.db" "D:\backups\context_$(Get-Date -Format yyyyMMdd_HHmm).db"
powershell -ExecutionPolicy Bypass -File scripts\backup_runner.ps1     # what SanskritDBBackup runs nightly
```


## C10, email and L2: switching on (DOCS35_2026_10_09)

The order matters: the desk's worker 1.2 before C10b.
1. **The desk**, between two rounds:
   - `python scripts\patch_corner_worker_c10_2026_10_09.py --check`, then without `--check`;
   - `python scripts\patch_tests_worker_client_2026_10_09.py`;
   - `python -m unittest tests.test_corner_worker_c10_2026_10_09 tests.test_corner_worker_state_2026_10_09 tests.test_corner_worker_2026_10_09`.
2. **`python scripts\patch_docs35_2026_10_09.py`, then release.**
3. **The SQL editor** (in either order):
   - `docs/cloud/C10b_checks_2026-10-09.sql` P1, then C10b in one paste, then V1-V3;
   - `docs/cloud/C12_checks_2026-10-09.sql` P1, then C12 in one paste, then V1-V3.

   Re-run both after any re-run of C9.
4. **Srangam:**
   - `patch_srangam_c10_mail_2026_10_09.py`, then `patch_srangam_load_l2_2026_10_09.py`;
   - typecheck, tests and build;
   - commit the paths they print;
   - pull before you push; push; Publish.
5. **Lovable:**
   - deploy the edge function corner-mail without changing its code;
   - Cloud -> Secrets: `RESEND_API_KEY` (a Resend key with sending access for nartiang.org).
6. **Corner -> Settings (super admin):**
   - Reply-to: an inbox you read (nartiang.org receives no mail);
   - then Email on.

**To stop all email at once:** Settings -> Email off, or in the SQL editor `UPDATE corner.settings SET value = 'false', updated_at = now() WHERE key = 'mail_enabled';`. The outbox keeps what is waiting.


## The corpus in the navigation; mail still to switch on (DOCS36_2026_10_10)

1. **Srangam:**
   - `patch_srangam_nav_rbac_2026_10_10.py --check`, then without `--check`;
   - typecheck, tests and build;
   - commit the paths it prints;
   - pull before you push; push; Publish.
2. **Look, signed in as a researcher:** the header shows "Corpus" (with Learn and the Corner) and no "Admin". Signed out it shows "Sign in". On a phone the bottom bar has a "Corpus" tab.
3. **Email:**
   - Lovable: deploy the edge function corner-mail without changing its code.
   - The next desk round's log has `"mail": {"configured": true, ...}`.
   - Then Corner -> Settings: Reply-to, then Email on.


## The Corner, guided; C13 (DOCS37_2026_10_10)

1. **Srangam:**
   - `patch_srangam_corner_ux_u1_2026_10_10.py --check`, then without `--check`;
   - typecheck, tests and build;
   - commit the paths it prints;
   - pull before you push; push; Publish.
2. **Look, as a researcher:**
   - Ask the desk starts with "Where to begin" and shows no form;
   - choosing a text shows what it has, the goals and "Ready in this text";
   - "Choose them in the text" fills From and To.
3. **C13 (when you choose):** in the Lovable Cloud SQL editor, one query per paste:
   - `C13_checks` P1;
   - the whole of C13 in one paste;
   - V1, V2, V3;
   - D2, to see Reply-to as saved.
4. **Settings:** Reply-to = an inbox you read; Save. Then ask, as yourself, for "An idea for a cover" ($0.01): its email arrives after the desk's next round.


## The desk, healed; the hub v2 (DOCS38_2026_10_10)

1. **The hub, at once.** From the automaton folder:
   - `python scripts\patch_hub_v2_2026_10_10.py --check`, then without `--check`.
   - Close the hub's console window and run `start-hub.bat`.
   - The hub works against the dashboard as it runs now.
2. **The dashboard's files.**
   - `python scripts\patch_desk_heal_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard page and the Library (Ctrl+F5).
   - The maintenance task takes it at its next run.
3. **The dashboard itself, only when idle.** `scripts\restart_dashboard.ps1` refuses while jobs run.
   - While the OCR of Yoga Vasistha runs (about a day at a page a minute), you can wait: maintenance no
     longer waits for it.
   - Or press Pause All, restart, then start that text's OCR again. It resumes from the missing pages.
4. **A text the Library marks "held":** run the OCR consensus plan it shows (no spend). Translate it
   after the repair, or start the dashboard with `SA_ALLOW_DEBRIS=1` to translate it anyway.
5. **Check:**
   - `Invoke-RestMethod http://127.0.0.1:5057/api/health` (after the restart).
   - `Get-Content D:\backups\maintenance_log.txt -Tail 6` (after the next tick).


## Every press makes a run; the console says what it did (DOCS39_2026_10_10)

1. **The page:**
   - `python scripts\patch_live_log_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard with Ctrl+F5.
   - The Log opens with the last runs. A press in the Library shows in it within 8 s, as what it did.
2. **The hub:**
   - `python scripts\patch_hub_v2_1_2026_10_10.py --check`, then without `--check`.
   - Close the hub's console and run `start-hub.bat`.
3. **A run marked [HELD]** is the OCR-debris guard, not a fault.
   - Plan the repair: `python scripts\ocr_consensus.py --doc <code> --threshold 101 --include-unassessed`.
     This is a plan, with no spend; add `--yes` to run vision.
   - Re-ingesting a repaired text replaces its passages and their translations. Do it only while the
     dashboard is idle, after `scripts\db_backup.py`, and only for a text you have decided on
     (docs/LIVE_LOG_2026-10-10.md section 4).
4. **Restart the dashboard** when idle, to bring in DESK_HEAL's Library and LIVE_LOG's live output.
   While an OCR runs:
   - press Pause All;
   - run `scripts\restart_dashboard.ps1`;
   - press Full on the OCR's row. It resumes from the missing pages.


## The repair path (DOCS40_2026_10_10)

1. **Patch:**
   - `python scripts\patch_repair_path_2026_10_10.py --check`, then without `--check`.
   - Reload the dashboard with Ctrl+F5.
2. **Restart the dashboard when idle** (`scripts\restart_dashboard.ps1`) for the Library's repair bars
   and `/repair/<doc>`.
3. **A text a run could not translate because of its scan:**
   - In the Library press *Repair path: what now?*, or open `http://127.0.0.1:5057/repair/<code>`.
   - Press the button it offers next:
     - Repair the scan (capped);
     - Use the repaired text (a backup first);
     - Set aside.
   - By hand: `python scripts\repair_text.py --doc <code>`, then the step its NEXT line names.
4. **Put a database back after a failed re-ingest:**
   - the step prints its backup (`context_pre_repair_<code>_<stamp>.db`);
   - stop the dashboard (`scripts\restart_dashboard.ps1 -Stop`);
   - copy the backup over `data\context.db`;
   - start the dashboard.
5. **The texts set aside:** `python scripts\repair_text.py --list`. Restore one with `--restore` when a
   better scan is in the inbox.


## The repair path, healed (DOCS41_2026_10_11)

1. **Before a re-ingest replaces translations,** the text is held from the site. `--use-repaired` does
   this by itself. By hand: `python scripts\repair_text.py --doc <code> --hold`.
   - Publish it when it is translated again: `--release`.
   - A text in repair is named in the mirror run's *held* list.
2. **Debris that is cosmetic:**
   - `python scripts\repair_text.py --doc <code>` judges it;
   - `--as-is "debris judged cosmetic"` lets the guard pass it;
   - `--restore` undoes that.
3. **What is left is not Sanskrit** (English front and back matter, lone dandas): `--accept "what is
   left is not Sanskrit"`.
4. **A better edition:**
   - On the repair page, the Source desk: *Find a better source*, *Preview here*, *Fetch the PDF*.
   - By hand: `python scripts\source_desk.py --doc <code>`, then `--fetch <identifier> --kind pdf`.
   - A fetched PDF lands in `sources\<code>\`. Import it as a new witness (Import path to inbox) once
     you have looked at it.
5. **Pause the mirror** while a text is being rebuilt and the patch is not in place:
   - `Disable-ScheduledTask -TaskName SanskritCorpusMirror`;
   - `Enable-ScheduledTask -TaskName SanskritCorpusMirror` afterwards.


## The debris judged; Sources & repairs (DOCS42_2026_10_11)

1. **Patch:**
   - `python scripts\patch_judge_desk_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle;
   - `python scripts\repair_text.py --judge-all` (free, read-only, about a minute).
2. **Open `http://127.0.0.1:5057/sources`.** Held texts come first, then material, moderate, cosmetic.
   Each row links to the text's repair page.
3. **Publish a text in repair** only when it is translated again:
   - `python scripts\repair_text.py --doc <code> --release` refuses until then;
   - `--release --force` publishes as it is.
4. **Tests without pytest:** `python -m unittest tests.test_judge_desk_2026_10_11 tests.test_repair_heal_2026_10_11 -v`.
   Or `python -m pip install pytest` once.


## An e-text as a witness (DOCS43_2026_10_11)

1. **Patch:**
   - `python scripts\patch_etext_witness_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle;
   - `python scripts\repair_text.py --judge-all`.
2. **Stop tracking the judged cache:** `git rm -r --cached data/source_judged`. It is in
   `.gitignore` now; the files stay on disk.
3. **Find an e-text:**
   - the repair page's Source desk: *Find a better source*, then a GRETIL or sanskritdocuments.org
     link;
   - or download the file into `sources\<doc>\`.
4. **Read it as a witness (free, read-only):**
   `python scripts\etext_witness.py --doc <doc> --file "sources\<doc>\<file>"`. Or paste the link on
   the repair page.
   - `WITNESS:` says whether it is the same work.
   - `--page N` shows the witness's reading of one page of the scan.
5. **Make it a witness:**
   - `--write`, then `python scripts\etext_witness.py --doc <doc> --ingest` (a backup first; the scan
     is not touched);
   - translate the witness from the Library;
   - `python scripts\repair_text.py --doc <doc>__w_<site> --release` to adopt it.
6. **Only if the witness replaces the scan:**
   - `python scripts\diag_retire_check.py --src <doc> --keep <doc>__w_<site>`;
   - then `python scripts\retire_doc.py --doc <doc> --supersedes <doc>__w_<site> --dry-run`.


## Benchmark the readings (DOCS44_2026_10_11)

1. **Patch:**
   - `python scripts\patch_benchmark_2026_10_11.py --check`, then without `--check`;
   - restart the dashboard when idle.
2. **One text:** `python scripts\benchmark_sources.py --doc <doc>`. It is free and read-only; it
   prints the table, the opinion and the next step.
3. **Every text:** `python scripts\benchmark_sources.py --all`, then open
   `http://127.0.0.1:5057/benchmarks`.
4. **To compare with archive.org's own OCR of the scan:**
   `python scripts\source_desk.py --doc <doc> --fetch <the scan's identifier> --kind text --force`
   (the benchmark's ALSO line names it), then benchmark again. The file stays in `sources\<doc>\`
   and is not ingested.
5. **Never paste a command with a `<placeholder>` in it.** Fill it in first.


## Are we sure of a text? (DOCS45_2026_10_11)

1. **The figures:** `python scripts\benchmark_sources.py --all` (free, read-only). Read the noise
   beside the misread letters:
   - vision OCR of a clean print is under 1%;
   - Tesseract is 2.7-7.4%;
   - over 3% is a damaged text.
2. **A repaired text merged before QUALITY_2026_10_11, with no English yet:**
   - merge again: `python scripts\merge_ocr_sources.py --doc tantric_texts_series_edited_by_arthur_av`,
     then the same with `--apply`;
   - use the repaired text through the dashboard (its translate lock): the repair page's button when
     Assess offers it, or `Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/repair` with
     the body `{"doc": "...", "step": "use"}` (by hand, `--use-repaired` refuses while the dashboard
     runs another job);
   - a text with English waits for R3.
3. **A witness** with noise over 3% is refused. It is no cleaner than Tesseract; look for an e-text.
4. **The translation's QA figure is structural.** The meaning is read by `scripts\judge_sample.py`
   (an LLM judge of fidelity and fluency on a sample, into mt_reviews; a dry run first, `--yes` to
   call it, capped by `--limit`), and by a person's spot check of about 20 passages.


## Re-ingest only the pages that changed (DOCS46_2026_10_12)

1. **Plan (free, read-only):** `python scripts\reingest_pages.py --doc tantric_texts_series_edited_by_arthur_av`.
   It lists each changed page: passages kept, new and gone, and what goes with them.
2. **Apply:** the same with `--apply`.
   - A backup is made first.
   - If it removes English, Hindi, a picture or a story, it refuses and prints the exact line with
     `--replace N`.
   - It is refused while the dashboard runs a database writer.
3. **Restarted, the dashboard** has *Plan: only the changed pages* and *Re-ingest the changed pages* on
   the repair page.
4. **After it:** the drift check should find the changed pages current. The site gets the change at the
   next mirror run.

## The judge's reading (DOCS46_2026_10_12)

1. **A dry run first:** `python scripts\judge_sample.py --doc Mallapurana --sample-pct 4 --limit 40`
   prints its cost (about $0.00015 a passage). Then the same with `--yes`.
2. **The figures, and the passages it marks:**
   `python scripts\judge_review.py --html exports\judge_review.html`.
3. **A person reads what it marks** before a translation is called wrong or right.


## The path of every text (DOCS47_2026_10_12)

1. **Chart it (free, read-only):** `python scripts\text_path.py --html exports\text_path.html`, or
   *Chart the path again* on `http://127.0.0.1:5057/path` (after a restart). One text with every fact:
   `--doc nirukta`.
2. **Follow each text's NEXT**, in the order of the groups. The free ones first: use the repair, retire
   (dry run first), ingest. Then the paid ones, each capped: repair the scan, translate, judge.
3. **Chart it again** after a run: the next step and the price change with what was done (a repaired text's
   own price replaces the corpus price after its first 20 pages).

## Withdraw a damaged text from the site (DOCS47_2026_10_12)

1. `python scripts\repair_text.py --doc Bodhicaryavatara --withdraw "its text is damaged: a better source is wanted"`
   writes the register; nothing is deleted.
2. **The next full mirror run** (`python scripts\corpus_sync.py`, then `--apply`; not `--doc`) retires its
   rows on the site. Ask the Corpus here leaves it out at once.
3. **`--restore`** undoes it; the next mirror run sends it back.


## When the mirror says "corpus_retire: ... statement timeout" (DOCS48_2026_10_12)

1. **Nothing is lost:** the call was rolled back whole, and the rows it was to retire are still live on the site.
2. **After MIRROR_CAP_2026_10_12:** vectors are retired 25 to a call, and a timed-out call is sent again in halves.
   Run the plan, then `--apply`: `python scripts\corpus_sync.py`, then `python scripts\corpus_sync.py --apply`.
3. **Check** in the SQL editor that the text's live passages are 0.

## --max-usd (DOCS48_2026_10_12)

- `repair_text.py --repair --max-usd X` refuses a run whose estimate is above X, and stops a run before a page
  would take it past X (what this run has spent, from usage_log). The spend cap (`set_budget.py`) still stops
  everything.


## Before a re-ingest: is anything writing? (DOCS49_2026_10_13)

1. `(Invoke-RestMethod http://127.0.0.1:5057/api/jobs/running).running | Select-Object kind, doc, state`
2. **Only OCR jobs (or none):** a re-ingest may run. A translation, classify or ingest job running or queued: it is
   refused; wait for the job to finish.
3. **Then:** a backup, the plan, the `--apply` line the plan prints, and the mirror.

## Does the site leave retired rows out? (DOCS49_2026_10_13)

In the Lovable SQL editor, read-only: every `corpus_reader_*` function's definition should mention `retired_at`:

    SELECT p.proname, position('retired_at' in pg_get_functiondef(p.oid)) > 0 AS filters_retired
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname LIKE 'corpus\_reader\_%' AND p.prokind = 'f'
    ORDER BY p.proname;


## What is redeemed (DOCS50_2026_10_14)

1. `python scripts\redeem.py --html exports\redeem.html --csv exports\redeem.csv`: free and read-only. It
   writes `data/redeem.json`, which the Library and `/redeem` show. Count again on `/redeem` does the same.
2. `python scripts\redeem.py --doc Mallapurana`: one text, with the passages the judge marks.
3. Green is kept; amber is mostly kept, or replaced by a better reading (translate it); red is to translate
   again after the repair, or a source first.

## The passages the judge marks, translated again (T2) (DOCS50_2026_10_14)

1. `python scripts\retranslate_marked.py`: the dry run (free). It shows what it would do, what it leaves out and
   why, and the price.
2. `python scripts\retranslate_marked.py --yes --max-usd 0.10`: the run. It stops before the cap, at the spend
   cap, or while the dashboard writes the same text. The log is in `data/retranslate/`.
3. `python scripts\judge_review.py`: what the judge says now. A passage still marked goes to a person.

## Does the reader return the reading's engine? (Srangam S2) (DOCS50_2026_10_14)

In the Lovable SQL editor, read-only:

    SELECT p.proname, position('ocr_engine' in pg_get_functiondef(p.oid)) > 0 AS returns_engine
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname IN ('corpus_reader_page', 'corpus_reader_outline') AND p.prokind = 'f'
    ORDER BY p.proname;


## The mirror held a retire (DOCS51_2026_10_14)

`corpus_sync.py` holds a retire of most or all of a text's rows ("HELD: ... use --allow-mass-retire if that is
right"). After a re-ingest, that is right: the old passages' mentions and vectors go.

1. Name only the texts the HELD lines name, and plan first:

       python scripts\corpus_sync.py --doc smriti_04daksha_smriti --allow-mass-retire

2. Then the same with `--apply`. Never `--allow-mass-retire` without `--doc`.

## English made from a misread reading, on the site (DOCS51_2026_10_14)

The reader marks such a passage "provisional English". The rule is `redeem.py`'s: eight or more Devanagari signs
and a Latin word among them. A change to one is a change to the other, with the tests of both:
- `tests/test_provisional_2026_10_14.py`;
- Srangam `src/__tests__/reader-provisional.test.tsx`.

## Before a re-ingest's --replace (DOCS51_2026_10_14)

The number after `--replace` is the plan's, not the chart's: translations made since the chart change it. Run
the plan, and use the `--apply` line it prints.


## The scholarly English (DOCS52_2026_10_14)

`scripts/scholar_translate.py` is a dry run unless `--yes`: what it sends, what it leaves out, what it costs.

1. The dry run, and the prompt the first verse gets (free):

       python scripts\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --show-prompt

2. The run, capped: the `NEXT:` line it prints, or `--yes --max-usd 1.50`.
3. Read it: http://127.0.0.1:5057/scholar/MBh01, or `--report` (exports\scholar_MBh01.html).
4. A person's word:
   - `--review 1.1.8 --verdict accept --by NAME` on the current version;
   - `--term T --rendering R --kind K --note N` for a glossary entry that wins.
5. A verse the critic calls a **source doubt** wants another edition, not another run.

It refuses a text withdrawn, set aside or in repair (exit 3). It stops at `--max-usd`, at the spend cap, and while
the dashboard changes the text's Sanskrit or English. A Hindi job does not stop it.

## A text held by the register (DOCS52_2026_10_14)

`translate_passages.py` refuses a whole-text run on a text withdrawn or set aside: "REFUSING (HOLD_2026_10_14)",
exit 4.
- One page (`--only-page`) is not held.
- To translate it anyway: `--allow-held`, or start the dashboard with `SA_ALLOW_HELD=1`.

The Library holds the buttons of a text whose path is repair the scan, a better source or retire. Chart again on
The path after a repair.

## MBh01's prose (DOCS52_2026_10_14)

1. Save the book's e-text by hand from the GRETIL or BORI page to `sources\mbh_01_u.htm`. Mind BORI's terms: not to
   be passed on.
2. The dry run:

       python scripts\import_mbh_gretil.py --book 1 --src sources\mbh_01_u.htm --out data\raw_mbh01_ce --dry-run

   It says how many prose lines it read, and "NOT READ" if a reference-like line was not.
3. The same without `--dry-run`.
4. The plan (free):

       python scripts\reingest_pages.py --doc MBh01 --merged-dir data\raw_mbh01_ce --no-segment

5. Its `--apply` line only when the verses stay and only the prose comes in.


## The scholarly English, version 2 (DOCS53_2026_10_14)

`scholar_translate.py` now reads sentences, not only verses, and asks a second judge. Both are on by default.

1. The dry run says how many sentences run over verses, and what it costs (free):

       python scripts\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --redo

2. The run, capped: its `NEXT:` line, or `--redo --yes --max-usd 0.75` (about $0.36 for the pilot's 24 verses).
3. Read it two ways:
   - as verses: http://127.0.0.1:5057/scholar/MBh01 (the earlier version is under each verse);
   - as prose: http://127.0.0.1:5057/scholar/MBh01/prose;
   - or `--report`: exports\scholar_MBh01.html and exports\scholar_MBh01_prose.html.
4. A verse the second judge calls worse, or flags, is read by a person (`--review`).
5. `--no-groups` and `--no-compare` give the v1 behaviour.

The dashboard serves `/scholar/<doc>/prose` only after a restart. Restart when it is idle:

    .\scripts\restart_dashboard.ps1 -Status
    .\scripts\restart_dashboard.ps1

`-Force` cuts the running jobs off; `--force` is not a PowerShell form.

## An e-text that says it is one (DOCS53_2026_10_14)

A text that came in from an e-text before 20 Jul 2026 has the OCR formula's quality (no dandas: 0.6 at most) and no
engine. The site then calls it "OCR confidence" and marks verses "hard to read".

1. The plan (free, read-only):

       python scripts\heal_etext_meta.py --doc MBh01

2. `--apply` (a backup to D:\backups first, the values before to data\heal\). Refused while the dashboard changes
   that text; a Hindi job does not stop it.
3. The mirror: `python scripts\corpus_sync.py`, then its `--apply`.
4. To put it back: `--undo data\heal\etext_meta_MBh01_<stamp>.jsonl` (the file the apply printed).


## The scholarly English 2.1 (DOCS54_2026_10_14)

1. A sentence flagged or failed under scholar-v2 is made again with v2.1, the dry run first (free):

       python scripts\scholar_translate.py --doc MBh01 --pages 1 --from-ref 1.1.15 --limit 9 --redo

2. Its `NEXT:` line runs it (capped).
3. A failure now says how the answer ended ("it ended MAX_TOKENS, ..."); a sentence that fails is translated verse by
   verse, and the summary counts it ("split").
4. The pages show a v2.1 sentence whole after its range (1.1.15-19); "Verse by verse" opens its segments.

## The reading on the site (DOCS54_2026_10_14)

1. In the Lovable Cloud SQL editor: docs/cloud/C17_checks_2026-10-14.sql E1 and P1, then
   docs/cloud/C17_reader_sources_2026-10-14.sql in one paste, then V1 and V2.
2. Srangam's reader then names each page's reading. Before C17 it shows what it showed before.
3. Rollback: `DROP FUNCTION IF EXISTS public.corpus_reader_sources(text);`

## Queueing translations (DOCS54_2026_10_14)

The dashboard runs one translate job at a time. Queue the small texts first and a long one (MBh01's Hindi, about 13
hours) last, or the small ones wait behind it.


## What a call really costs (DOCS55_2026_10_15)

1. One call shows the thinking (a fraction of a cent): its usage_metadata's total minus prompt minus candidates.
2. usage_log by day beside Google's bill for the same days shows how far the meter of before 15 Oct was off.
3. The cap: `python scripts\set_budget.py` shows it; from COST_TRUTH_2026_10_15 it counts the thinking.
4. The scholarly English's dry run prices by the prior (about $0.10 a verse) until 10 rows are metered with the
   thinking; use the cap its `NEXT:` line gives.

## Keeping working files out of the repo (DOCS55_2026_10_15)

release.ps1 stages everything. A directory of working files goes into .gitignore before the release, and into the
safety check's list. One committed by mistake leaves the repo with `git rm -r --cached` and a release; the file stays
on disk.


## The Claude credit (DOCS56_2026_10_15)

1. `python scripts\claude_engine.py --credit` (free): spent, left, the expiry. The Console's Billing page is the truth.
2. `python scripts\claude_engine.py --probe` (about $0.001): the key, the SDK and the meter answer.
3. A scholarly run on Claude: `--engine anthropic:claude-sonnet-5-5` (an effort after "@"); the dry run prints the
   credit; the run stops before the cap ($190) and from 11 Nov.
4. A text in repair (in_repair) needs `--held-ok`; a benchmark run `--no-glossary-adds --redo`.

## Reading engines side by side (DOCS56_2026_10_15)

1. `python scripts\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --pages 20-21 --limit 12` (the dry run, free), then
   its NEXT line.
2. `--report` writes exports\scholar_duel_HAYASHIRSHA_PANCARATRA.html, blind; read it before opening the folds.
3. `--pick` with span=number pairs (the page's Translation number) and `--by` with your name records your choice; the
   tally counts it.


## Engines side by side, without stopping them (DOCS57_2026_10_15)

1. Start each run in its own window (Start-Process powershell -ArgumentList "-NoExit", ...): its progress shows, and
   Ctrl-C in one window stops only that run.
2. A run that stopped goes on with the same command and `--fill-engine` (no `--redo`, which redoes everything).
3. Never set MT_ENGINE to an anthropic: engine: the working translation would fall back to echo.


## A long scholarly run (DOCS58_2026_10_15)

1. Back up first, under the run's name: `python scripts\db_backup.py data\context.db
   D:\backups\context_pre_sonnet_20261015.db`.
2. The canary: a few pages with `--audit-every 3`; read the flagged verses and the audits (`--report`) before the
   whole.
3. The whole: one window a range (Start-Process powershell -ArgumentList "-NoExit", ...), each with `--fill-engine
   --audit-every 10 --compare-every 10` and its own `--max-usd`.
4. Watch from another window: `--status` (free). A window that stopped goes on with its own command.


## A scholarly run that stops (DOCS59_2026_10_15)

- "the dashboard changes <doc> now (...)": see the dashboard's jobs (`Invoke-RestMethod
  http://127.0.0.1:5057/api/jobs/running`, read-only). A pipeline that is translating or exporting no longer stops a
  run (RUN_FIX_2026_10_15); anything else that changes the text does. Run the same command again when it is done.
- "this run's --max-usd ... is reached": the same command again goes on (--fill-engine); the cap is a window's.
- "the critic's answer could not be read" in a verse's doubts: the answer is in data\scholar\unparsed_<doc>.jsonl.
  Redo that verse alone, as 20.6 was: `--only-page 20 --only-idx 6 --redo --fill-engine --audit-every 1`.
- Watch every window with `--status` (free); a person reads the flagged and the source doubts (`--report`).


## The Claude credit first (DOCS60_2026_10_15)

- **A scholarly run, no Gemini:** `--engine anthropic:claude-sonnet-5-5 --judge-engine anthropic:claude-haiku-5-5
  --compare-engine anthropic:claude-opus-5-5`. The dry run says "no Gemini call: Google's spend cap is not
  consulted". With the flash judge kept (the default --judge-engine), Google's cap still gates the run.
- **The working English on Claude, one text at a time:** only after the benchmark (`benchmark_mbh01.py --engines
  gemini:gemini-2.5-flash anthropic:claude-haiku-5-5 anthropic:claude-sonnet-5-5@low`). Then the dashboard's
  `/api/pipeline/translate-doc` with `"engine": "anthropic:claude-haiku-5-5"`. Never set MT_ENGINE to an anthropic:
  engine: Ask and extract_entities call Gemini with it.
- **When the credit is spent or expires,** the job stops ("the Claude credit is spent or expired"). Run it again with
  the default engine.
- **Watch:** `claude_engine.py --credit`; `spend_audit.py --days 30` against AI Studio's Spend page.


## A Claude run, checked by Gemini (DOCS61_2026_10_15)

- **The standing flags:** `--engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5`, and the
  default --judge-engine (gemini-2.5-flash). The dry run says "the judge gemini:gemini-2.5-flash (Google's bill, in
  the spend cap); the second judge and the audit anthropic:claude-opus-5-5 (the Claude credit)".
- **The spend cap:** a run stops when Google's spend cap is reached; `set_budget.py` shows it.
- **Rows a Claude judge read:** `--engine anthropic:claude-sonnet-5-5 --rejudge` (a dry run: counted, free), then with
  `--limit 2000 --yes`. Run it when the windows of that text are stopped or done, or let it leave the verses they
  redo alone.


## The verses that did not pass (DOCS62_2026_10_16)

1. `--engine anthropic:claude-sonnet-5-5 --rejudge --limit 2000` (a dry run), then with `--yes`: the verses a Claude
   judge read get the Gemini judge's reading.
2. `--engine anthropic:claude-sonnet-5-5 --triage` (free): exports\scholar_triage_<doc>.csv; rejected, source,
   serious, mild.
3. `--engine anthropic:claude-opus-5-5 --only-flagged anthropic:claude-sonnet-5-5 --serious --compare-engine
   anthropic:claude-sonnet-5-5 --audit-every 1`: another model reads the serious again (a dry run first).
4. A person reads (`--report`), and marks what was read (`--review ... --verdict accept|reject --by ...`).

## A page whose reading is not what it prints (DOCS62_2026_10_16)

- `python scripts\mark_passages.py --doc <doc> --pages <n> --type noise --reason "..."` (a dry run), then
  `--apply`; `--undo --apply` puts it back. Only text_type changes; the log is data\mark_passages_log.jsonl.


## The scholarly English in the Library (DOCS63_2026_10_16)

- The Library's cards: "SC n" is the scholarly English (scholar_translations); "EN n/N" is the working English, the
  one the site shows. The reader shows both, the scholarly above. Read-only; restart the dashboard (when no job runs)
  after the patch.
- After READY_PRICE_2026_10_16: `python scripts\redeem.py` (free) writes the Library's estimates at the measured price.
- Do not press Finish EN or Add Hindi on a bilingual edition (the Karanagama) until H1 is decided: the working English
  would translate the editor's Hindi.


## An edition's own Hindi (DOCS64_2026_10_16)

1. `python scripts\classify_hindi.py --show 3` (free): every text, what reads as Hindi, and what carries English.
2. A text whose Hindi carries no English: `python scripts\classify_hindi.py --doc <code> --apply`.
3. A text whose Hindi was translated: back up first, then `--with-english --reject-scholarly --by <name> --apply`.
4. `--undo --apply` puts back what the log says; `python scripts\build_embeddings.py --doc <code>` remakes the
   vectors of English put back.
5. New texts: classify_doc.py runs it after every ingest (only what carries no English).


## BM1, the benchmark against published translations (DOCS65_2026_10_16)

1. `python scripts\bench_mitra.py --sample` (free): the 200 verses and the bench databases, in
   D:\Sanksrit Automatons\benchmarks\bm1 (outside the repository; private).
2. `python scripts\bench_mitra.py` (free): what each arm would send and cost, the credit and the cap.
3. `--arm flash`, `--arm sonnet1`, `--arm scholar`, each with `--yes --max-usd N` (they can run at once).
4. `--score --judge-reference --yes --max-usd N`, then `--report` (free): BM1_report.html (private) and
   BM1_summary.json (numbers only).
5. A step stopped half way: run it again (it goes on), or `--settle` (free) to put its spend in the ledger.


## BM1 from the dashboard (DOCS66_2026_10_16)

1. The Benchmarks page (the header's link): BM1's Next line names the step to take and its price.
2. A paid button (Run an arm, Judge them) asks first, then runs bench_mitra.py with --yes --max-usd (the estimate and
   a third more); its last lines show below the buttons; the page reads BM1 again when it ends.
3. Make the report again (free), then "The full report" (served on this computer only).
4. The same steps by hand: docs/BENCH_MITRA_2026-10-16.md, section 6.


## BM3, the blind side-by-side (DOCS67_2026_10_16)

1. BM1 complete (the Benchmarks page says Done), then BM3's section: Next names the part to read and its price.
2. The pilot (40 units, both judges, the published English among the translations): the button, or
   `python scripts\bench_duel.py --units 40 --with-reference --yes --max-usd 6.00`.
3. Make the report again (free); read each judge apart, then where both agree.
4. More units: the button reads 40 more a press, when the spend cap can hold its Google part
   (`python scripts\set_budget.py` shows the cap).
5. A run stopped half way: `python scripts\bench_duel.py --settle` (free).


## BM2, your blind reading; BM3's check (DOCS68_2026_10_16)

1. The Benchmarks page, BM2's section: Read blind (or http://127.0.0.1:5057/benchmarks/bm2). Say who is reading
   (kept in this browser), pick the best of the four (keys 1 to 4, E for equal), mark any wrong in meaning, Enter.
2. Make the report (free) when you stop; read each judge against you.
3. BM3's check (once the pilot is read): Run the check (about $3.0), then Make the check's report (free); or
   `python scripts\bench_duel.py --units 40 --with-reference --no-notes --yes --max-usd 4.50` and
   `python scripts\bench_duel.py --report --no-notes`.


## The translation desk (DOCS69_2026_10_17)

1. http://127.0.0.1:5057/desk: every text by its stage. If the chart is old (three days or more), Chart the path
   again (free) or `python scripts\text_path.py`.
2. A text's page (/desk/<doc>): its path's next step first (the repair page for the reading first).
3. The scholarly English: Plan them (free), read the verdict and the price, then Run these verses (the plan's own cap,
   at most $12.00; it asks). Then Triage and Report (free); accept or reject by hand:
   `python scripts\scholar_translate.py --doc ... --review 1.1.8,1.1.9 --verdict accept --by Dhruv`.
4. Translate on a text the path holds: the button says why and asks; going on sends force.
5. The SOP: docs/SOP_TRANSLATION_2026-10-17.md.


## The scholarly edition; the buttons; the repair's next step (DOCS70_2026_10_17)

1. The edition of a text with scholarly English: its desk page, "Make the edition (free)", then "Open the newest";
   or Export As "The scholarly edition"; or
   `python scripts\export_html.py --db data\context.db --doc HAYASHIRSHA_PANCARATRA --scholar --sanskrit --side-by-side`.
2. Translate All OCR'd is retired; the desk has each text's next step.
3. Ingest or Full on a text with English asks first: the Repair page's re-ingest of the changed pages (the plan free)
   is the safe way.
4. BM2: read on (/benchmarks/bm2), then `python scripts\bench_gold.py --report` (free): both comparisons.


## Tier R; the Devimahatmya from GRETIL (DOCS71_2026_10_17)

1. Tier R: a text's desk page, "The working English by Sonnet in one pass": the rest, or every verse again. It asks,
   bills the Claude credit, stops when the credit does.
2. The Devimahatmya: `python scripts\etext_witness.py --doc markandeya_purana --url https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_mArkaNDeyapurANa1-93.htm` (the
   preview, free; the file is kept in sources\markandeya_purana), then
   `python scripts\etext_witness.py --doc markandeya_purana --file sources\markandeya_purana\sa_mArkaNDeyapurANa1-93.htm --write`,
   then `python scripts\etext_witness.py --doc markandeya_purana --ingest`; `python scripts\text_path.py`; on the desk
   page of markandeya_purana__w_gretil: Begin at 81.1, Plan them (free), Run.


## The flash corpus redeemed; GRETIL by PowerShell (DOCS72_2026_10_17)

1. **The calibration (free dry run; then about $0.06 on the credit):**
   `python scripts\judge_sample.py --all --calibrate --engine anthropic:claude-haiku-5-5`, then the same with
   `--yes --max-usd 0.20`. The referee on where they disagree:
   `python scripts\judge_sample.py --all --calibrate --engine anthropic:claude-opus-5-5 --only-ids data\retranslate\judge_screen\calibrate_claude-haiku-5-5_disagree.jsonl`,
   then with `--yes --max-usd 2.00`. The rule (docs/JUDGE_SCREEN_2026-10-17.md, section 4) decides.
2. **The screen, a text at a time:** `python scripts\judge_sample.py --doc markandeya_purana --sample-pct 100 --limit 2000
   --skip-judged --clean-only --engine anthropic:claude-haiku-5-5` (dry run), then with `--yes --max-usd 0.50`. The
   others likewise (MBh01, the Natyasastra, the Tantric Texts, the Shatapatha, the Mallapurana, Sandilya).
3. **The fix:** `python scripts\retranslate_marked.py --doc markandeya_purana --engine anthropic:claude-sonnet-5-5
   --judge-engine anthropic:claude-haiku-5-5` (dry run); its NEXT. Then `python scripts\judge_review.py --doc
   markandeya_purana`, `python scripts\redeem.py`, `python scripts\text_path.py`, the mirror's plan and --apply.
4. **GRETIL (the Markandeya Purana, 1 to 93):** in PowerShell, from the repo root:
   `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12`, then
   `Invoke-WebRequest -Uri https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_mArkaNDeyapurANa1-93.htm -OutFile sources\markandeya_purana\sa_mArkaNDeyapurANa1-93.htm -UseBasicParsing`;
   then `python scripts\etext_witness.py --doc markandeya_purana --file sources\markandeya_purana\sa_mArkaNDeyapurANa1-93.htm --slug gretil`
   (the preview, free), the same with `--write`, then `python scripts\etext_witness.py --doc markandeya_purana --ingest`.


## The Devimahatmya, its re-judge and editions (DOCS73_2026_10_18)

1. **The run:** `python scripts\scholar_translate.py --doc markandeya_purana__w_gretil --from-ref 81.1 --pages 627-780
   --limit 20 --engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5 --audit-every 10
   --no-compare` (the plan: its first verse must be MarkP_81.1, savarnih suryatanayo), then `--yes --max-usd 1.50`; then
   the same with `--limit 700` and `--yes --max-usd 24.00`. No vision repair beside it.
2. **The re-judge** of the verses no judge answered: `python scripts\scholar_translate.py --doc
   markandeya_purana__w_gretil --engine anthropic:claude-sonnet-5-5 --rejudge --limit 900` (the dry run), then its NEXT.
3. **The editions:** `python scripts\export_html.py --db data\context.db --doc markandeya_purana__w_gretil --scholar
   --sanskrit --side-by-side --from 626 --to 780` (the Devimahatmya) and `--from 81 --to 124` (adhyayas 19 to 31); the
   prose: `python scripts\scholar_translate.py --doc markandeya_purana__w_gretil --report`.


## The day's order: the Devimahatmya's editions, the mirror, the Ganita, the Surya (DOCS74_2026_10_18)

docs/STATE_2026-10-18.md, section 6. One Gemini job at a time.
1. **The Devimahatmya:** the editions and the prose again (DOCS73 above, step 3, free); its 37 flagged verses on the
   desk (Triage); the re-judge (DOCS73 above, step 2: the dry run, then its NEXT).
2. **The mirror:** `python scripts\corpus_sync.py --doc Mallapurana` (the plan, free), then the same with `--apply`.
3. **The Sandilya:** `python scripts\retranslate_marked.py --doc AphorismsOfSandilya --engine anthropic:claude-sonnet-5-5
   --judge-engine anthropic:claude-haiku-5-5` (the dry run), its NEXT; then `python scripts\corpus_sync.py --doc
   AphorismsOfSandilya` and `--apply`.
4. **The Ganita Yukti Bhasa:** `python scripts\reingest_pages.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (the
   plan, free), its NEXT (`--apply --replace`, as the plan counts); then on its desk page "The working English by Sonnet
   in one pass", the rest (Plan, free; then Run); then the screen (DOCS72 above, step 2, `--doc
   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`) and T2 (step 3).
5. **The Surya Siddhanta:** `python scripts\scholar_translate.py --doc jyotish_surya_siddhanta__w_etext --pages 1-28
   --limit 20 --engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5 --audit-every 10
   --no-compare` (the plan, free: its first verse is the text's first), then `--yes --max-usd 1.50`; then the same with
   `--limit 600` and `--yes --max-usd 16.00`.


## The scholarly editions on Srangam (DOCS75_2026_10_18)

docs/EDITIONS_SITE_2026-10-18.md.
1. **The editions (the automaton):** `python scripts\publish_editions.py` (the plan, free; it lists each edition and
   what it would write), then `python scripts\publish_editions.py --apply`. An edition is turned on or off in
   configs/editions.json (`"enabled"`).
2. **The site (once):** in D:\srangam-42267, `git pull --rebase --autostash`; `python "D:\Sanksrit
   Automatons\sanskrit-automatonv2\scripts\patch_srangam_editions_2026_10_18.py" --check`, then without --check;
   `npm run typecheck`; `npx vitest run`; `npm run build`.
3. **The commit (yours):** `git add -- public/scholarly` and the files the kit printed; `git commit`; `git push`. Then
   https://srangam.nartiang.org/editions.
4. **After a new scholarly run:** step 1 again, then `git add -- public/scholarly`, commit, push.


## The scholarly English in the reader (DOCS76_2026_10_18)

docs/SCHOLAR_READER_2026-10-18.md. In a new PowerShell window: `$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"`,
`$S = "D:\srangam-42267"`.
1. **The automaton:** `Set-Location $A`; `python scripts\patch_scholar_mirror_2026_10_18.py --check`, then without
   --check; the same for `scripts\patch_docs76_2026_10_18.py`; `python -m unittest tests.test_scholar_mirror_2026_10_18
   tests.test_corpus_sync_2026_10_08 tests.test_mirror_cap_2026_10_12 tests.test_publish_editions_2026_10_18
   tests.test_srangam_scholar_reader_kit_2026_10_18 tests.test_docs76_2026_10_18`; `python scripts\corpus_sync.py` (the
   plan: the scholarly rows of MBh01 and the Tantrabhidhana); release.ps1 with COMMIT_MSG_scholarreader_20261018.txt.
2. **The site's SQL** (Lovable Cloud SQL editor): docs/cloud/C18_checks_2026-10-18.sql E1 and P1, one per paste; then
   `Get-Content -Raw -Encoding UTF8 "$A\docs\cloud\C18_reader_scholar_2026-10-18.sql" | Set-Clipboard`, paste it whole,
   Run; then V1 and V2.
3. **Srangam:** `Set-Location $S`; `git pull --rebase --autostash`; `python
   "$A\scripts\patch_srangam_scholar_reader_2026_10_18.py" --check`, then without --check; `npm run typecheck`; `npx
   vitest run`; `npm run build`. Then the editions: `Set-Location $A`; `python scripts\publish_editions.py`, then
   `--apply`. Then `Set-Location $S`; `git add --` the files the kit printed and `public/scholarly`; `git commit -F
   "$A\docs\srangam\SCHOLAR_READER_2026-10-18\COMMIT_MSG.txt"`; `git push`.
4. **The GRETIL Markandeya on the site (your decision):** `python scripts\repair_text.py --doc
   markandeya_purana__w_gretil --release --force`; `python scripts\corpus_sync.py` (the plan); the scheduled mirror
   sends it. Then E1 and E2 of the checks.


## The model's words in a translation, and the English a T2 run emptied (DOCS77_2026_10_19)

docs/LEAK_GUARD_2026-10-19.md. In a new PowerShell window: `$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\patch_leak_guard_2026_10_19.py --check`, then without --check; the same for
   `scripts\patch_docs77_2026_10_19.py`; `python -m unittest tests.test_leak_guard_2026_10_19 tests.test_heal_english_2026_10_19
   tests.test_docs77_2026_10_19 tests.test_guards_2026_10_04 tests.test_claude_first_2026_10_15 tests.test_scholar_2026_10_14`.
2. `python scripts\db_backup.py data\context.db D:\backups\context_pre_heal_20261019.db`; `python scripts\heal_english.py` (the plan, free); `python scripts\heal_english.py
   --yes` (free: from mt_cache); `python scripts\heal_english.py --yes --fresh` (Sonnet, a few cents, for what was
   emptied); `python scripts\corpus_sync.py` (the plan); the scheduled mirror sends it.
3. Release with COMMIT_MSG_leakguard_20261019.txt.


## The Surya's spelling, its verses of numbers, the scholars' shelf (DOCS78_2026_10_21)

docs/SHELF_AND_SURYA_2026-10-21.md. In a new PowerShell window: `$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"`.
1. `Set-Location $A`; each of `scripts\patch_etext_ortho_2026_10_21.py`, `scripts\patch_numeral_verse_2026_10_21.py`,
   `scripts\patch_ops_guard_test_2026_10_21.py`, `scripts\patch_docs78_2026_10_21.py` with `--check`, then without
   it; then `python -m unittest tests.test_ops_guard
   tests.test_etext_ortho_2026_10_21 tests.test_numeral_verse_2026_10_21 tests.test_witness_mend_2026_10_21
   tests.test_scholar_shelf_2026_10_21 tests.test_docs78_2026_10_21 tests.test_etext_page_2026_10_18
   tests.test_scholar_ref_2026_10_18 tests.test_etext_witness_2026_10_11`.
2. `python scripts\mend_witness.py --doc jyotish_surya_siddhanta__w_etext` (the plan), then `--yes` (a backup first);
   the same for `markandeya_purana__w_gretil`. Both are released, so the scheduled mirror sends the mended text (do
   not --hold a released text to mend it: the site would keep the misspelt version until it is released again).
3. The shelf: download the three txt zips (the doc's section 2), `python scripts\scholar_shelf.py` (the plan), `--yes`,
   `--show Janaka`.
4. Release with COMMIT_MSG_orthoshelf_20261021.txt.


## The Surya's references; Raychaudhuri as claims; an e-text's noise named (DOCS79_2026_10_21)

docs/CLAIMS_AND_REFS_2026-10-21.md. In a new PowerShell window: `$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"`.
1. `Set-Location $A`; `scripts\patch_etext_refs_2026_10_21.py` and `scripts\patch_docs79_2026_10_21.py`, each with
   `--check`, then without it; then `python -m unittest tests.test_etext_refs_2026_10_21 tests.test_etext_ortho_2026_10_21
   tests.test_witness_mend_2026_10_21 tests.test_etext_page_2026_10_18 tests.test_etext_witness_2026_10_11
   tests.test_scholar_claims_2026_10_21 tests.test_srangam_etext_noise_kit_2026_10_21 tests.test_docs79_2026_10_21`.
2. When the Gemini run of the verses of numbers has finished: `python scripts\mend_witness.py --doc
   jyotish_surya_siddhanta__w_etext` (the plan: respelled 18, the reference only 485), then `--yes` (a backup first).
   The scheduled mirror sends it; docs/cloud/CHECKS_surya_refs_2026-10-21.sql (read-only) before and after.
3. The claims: `python scripts\scholar_claims.py --extract` (free), `--pages 1-3 --yes` (about $0.02), `--report`,
   `--show Janamejaya`; then `--part 1 --yes` (about $0.69).
4. Srangam (`Set-Location D:\srangam-42267`; `git pull --rebase --autostash`): `python
   "$A\scripts\patch_srangam_etext_noise_2026_10_21.py" --check`, then without it; `npm run typecheck`; `npx vitest
   run`; `npm run build`; then the `git add` line it prints, a commit and a push.
5. Release the automaton with COMMIT_MSG_refsclaims_20261021.txt.

## The claims mended; the brain's path (DOCS80_2026_10_21)

docs/BRAIN_PATH_2026-10-21.md. In a new PowerShell window: `$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"`.
1. `Set-Location $A`; `scripts\patch_claims_fix_2026_10_21.py` and `scripts\patch_docs80_2026_10_21.py`, each with
   `--check`, then without it; then `python -m unittest tests.test_claims_fix_2026_10_21 tests.test_scholar_claims_2026_10_21
   tests.test_docs80_2026_10_21 tests.test_docs79_2026_10_21`.
2. `python scripts\scholar_claims.py --reparse` (free), `--recite` (free), `--part 1 --yes` (the last 4 pages, about
   $0.03), `--report`, `--show Janamejaya`, `--csv data\shelf\phai1923_claims.csv`.
3. After the 20:31 IST mirror run: docs/cloud/CHECKS_surya_refs_2026-10-21.sql, R1 to R4 (read-only).
4. The Satapatha from GRETIL, if you approve the download: kandas 11 and 13 (or 1 to 11, 13, 14) into
   `sources\satapatha_gretil\`, their sha256 recorded; nothing is ingested until its kit comes.
5. Release with COMMIT_MSG_claimsfix_20261021.txt.
