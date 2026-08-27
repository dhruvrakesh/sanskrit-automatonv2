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

### Translation quality — use `translation_qa`, NOT `quality_score`
**Metric correction (2026-08-27):** two quality columns exist and they disagree.
`quality_score` is a legacy inline heuristic that clusters ~0.5 and is **not reliable**;
`translation_qa` (written by `qa_scan.py`) is the real QA pass. Earlier drafts of this
file reported `quality_score` and painted a false "69% mid-tier" crisis. The truth, by
`translation_qa`, is that the corpus is **mostly high quality**:

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

### Metric hygiene TODO
Retire or recompute `quality_score`; make `translation_qa` the single canonical column in
all diagnostics and the dashboard (`diag_quality.py` corrected 2026-08-27).

---

## Targets (what "good" looks like)
| Dimension | Baseline | Target |
|-----------|----------|--------|
| EN verses `translation_qa` ≥0.8 | already the majority | ≥95% (heal the small low-QA pocket) |
| Verses `translation_qa` <0.6 | a few hundred, in small docs | heal with `gemini-2.5-pro` |
| Canonical quality metric | split (`quality_score` vs `translation_qa`) | single: `translation_qa` |
| Embeddings vs EN | −200 | in sync |
| `disk I/O error` incidents | intermittent | 0 (after AV exclusion + error logging) |
| Backup freshness | nightly, verified | unchanged (keep green) |
