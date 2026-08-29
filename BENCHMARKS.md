# Sanskrit Automaton — Benchmarks

*Dated, measured baselines. Re-run `scripts\diag_baseline.py` + `scripts\diag_quality.py`
after any material change and append a new dated block. Never compare against memory.*

---

## Baseline — 2026-08-27

### Storage & performance
| Metric | Value | Note |
|--------|-------|------|
| DB size | 419.1 MB | `context.db` |
| Disk | D: NTFS, **Fixed (local)** | not a Drive/stream placeholder |
| Sync clients on DB folder | **none** | Dropbox root is `C:\Users\dhruv\Dropbox`; no Drive mirror |
| `journal_mode` | `wal` | persistent on file |
| `page_size` | 4096 | |
| `busy_timeout` (raw `connect()`) | **5000 ms** | Python default; `db_utils` sets 30000 |
| Counts query | **0.07 s** | 27,472 passages |
| Per-doc coverage aggregate | **0.00 s** | 56 docs — DB layer is NOT a bottleneck |

**Conclusion:** query performance is already excellent; "improve load times" work should
target the front end and file-IO stalls (AV), not SQL.

### Corpus size
| Docs | Passages | EN | HI | Entities | Mentions | Embeddings |
|------|----------|----|----|----------|----------|------------|
| 56 | 27,472 | 13,746 | 5,136 | 5,169 | 22,894 | 13,544 |

Embeddings (13,544) lag EN (13,746) by ~200 → run `build_embeddings.py` after next batch.

### Two metrics measure TWO DIFFERENT axes (per `docs/QUALITY_LOOP_DESIGN`)
**Metric correction (2026-08-27), reconciled with the design docs:**
- **`quality_score` = SOURCE-corruption gate** — Devanagari density of the *source* text.
  It is the "is this OCR clean enough to translate?" signal (Q5: skip < 0.35). Low here →
  noisy source → **re-OCR/re-source** candidate. It is NOT a translation-quality metric.
- **`translation_qa` = TRANSLATION structural QA** — the Phase-Q scorer (`qa_scan.py`,
  `text_filters.score_translation_quality`): emptiness, length band, residual Devanagari,
  gloss-pairs, style artifacts. Low here → **heal/re-translate** candidate.
- **Neither certifies SEMANTIC fidelity.** Per `HINDI_TRACK_DESIGN` §4: "0.988 means
  structurally sound, NOT certified faithful." Semantic certification needs the manual
  Debroy benchmark sheet + the designed-but-unbuilt **Q4 LLM-judge** (`judge_sample.py`,
  `mt_reviews`).

My earlier diagnostics ranked docs by `quality_score` and mislabelled it "translation
quality" — that produced a false "69% mid-tier" crisis. By the correct metric,
`translation_qa`, the corpus is **mostly high quality**:

| Doc (sample) | n | translation_qa |
|--------------|---|----------------|
| MBh01 | 6,957 | 1.000 |
| nilamata_seg | 1,330 | 0.996 |
| markandeya_purana | 968 | 0.989 |
| nirukta | 1,988 | 0.953 |
| yajur_veda_shukla | 951 | 0.936 |
| Bodhicaryavatara | 781 | 0.933 |
| LalitaVistara | 47 | 0.943 |

Proof the legacy metric is noise: MBh01 = `quality_score` 0.52 but `translation_qa` 1.000
with clean source. **Conclusion: no mass re-translation, re-OCR, or archive re-sourcing is
warranted.**

### The real (small) heal target
Genuinely weak `translation_qa` is confined to **small** doc(s) and scattered individual
verses — not a systemic problem. Weakest docs (all small n): `harita_pancamam` 0.433 (3),
`smriti_01angirasa` 0.433 (3), `smriti_02vyasa` 0.460 (20), `shiksha_aranya` 0.525 (10),
`upapurana_samba` 0.545 (11), `shiksha_amoghanandini` 0.563 (19), `upapurana_nilamata`
0.608 (109). Plus small `0.0–0.2` pockets inside otherwise-good docs (garbled individual
verses). Total heal target is a few hundred verses — run `heal_lowqa.py --below-qa 0.6`
scoped to these, ~hundreds of API calls, not thousands.

### Provenance (from `diag_provenance.py`)
- Engine/prompt: the bulk (13,119 verses) is already on `gemini-2.5-flash` + current
  prompt `v2-2026-07`; only 201 are untracked `v1-legacy`. So "old models" is NOT the
  driver — the corpus is current.
- Source purity: low Devanagari ratio for `Bodhicaryavatara` (0.60), `bodhyana` (0.65) is
  **IAST/romanized source, not OCR noise** (their `translation_qa` is 0.93 / 0.83). Do not
  re-OCR on this signal alone.

### Metric hygiene — resolved
Keep BOTH columns; they are different axes. Diagnostics now label them correctly
(`quality_score` = source gate, `translation_qa` = translation QA; corrected 2026-08-27).
The dashboard QA panel should read `translation_qa` for translation quality (batched with
the next restart). The real open item is **semantic** certification — see roadmap Phase 3.5
(build the Q4 judge that `QUALITY_LOOP_DESIGN` already specifies).

---

## OCR A/B — measured 2026-08-28 (why we are NOT re-OCRing)

Hypothesis: the garbled Sanskrit in old scanned editions was a DPI problem, fixable by
re-OCR. **Tested and rejected.**

| Page | source | dev fraction | length |
|------|--------|--------------|--------|
| `AphorismsOfSandilya_0050` | stored (400 DPI, original run) | **0.98** | 999 |
| `AphorismsOfSandilya_0050` | fresh OCR, 400→600 DPI escalation, all preproc variants | **0.98** | 1040 |

**Verdict: no material gain.** The output is 98% Devanagari in both cases — the failure is
*character-level misrecognition inside Devanagari* (`प्राख्डिल्यग्रतखनीयं`, `amfafe:`), not
script confusion. Tesseract cannot read the 1861 Bibliotheca Indica founts accurately at
any DPI we can throw at it. **Do not spend hours re-OCRing these texts.** The remedy is a
clean e-text source (GRETIL / sanskritdocuments / the `wisdomlib` sibling), imported via
`import_mbh_gretil.py` / `import_wisdomlib.py`.

Separately, a genuine defect WAS found and fixed in `ocr_pdf.py`: acceptance was
`len(cand) >= min_chars` — **quantity only** — so a 400-DPI pass yielding 60+ chars of
Latin garbage was accepted and broke out of the retry loops, meaning the 450/600-DPI
escalation never fired for the pages that needed it. Acceptance now also requires
Devanagari-dominance (`--min-dev-frac`, default 0.45). This helps the *Latin-contaminated*
failure class; it does not (and cannot) help the misrecognised-Devanagari class above.

## Targets (what "good" looks like)
| Dimension | Baseline | Target |
|-----------|----------|--------|
| EN verses `translation_qa` ≥0.8 | already the majority | ≥95% (heal the small low-QA pocket) |
| Verses `translation_qa` <0.6 | a few hundred, in small docs | heal with `gemini-2.5-pro` |
| Canonical quality metric | split (`quality_score` vs `translation_qa`) | single: `translation_qa` |
| Embeddings vs EN | −200 | in sync |
| `disk I/O error` incidents | intermittent | 0 (after AV exclusion + error logging) |
| Backup freshness | nightly, verified | unchanged (keep green) |
