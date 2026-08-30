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


## Tesseract vs vision: word-level accuracy (2026-08-29)

**Why the earlier metrics all missed this.** `quality_score`
(0.6*devanagari + 0.4*danda) measures how Devanagari a page LOOKS. Latin-intrusion
"contamination" measures leaked junk. Character similarity between engines is 0.732
on Shatpatha and 0.803 on AphorismsOfSandilya - too close to separate a good book
from an unusable one, because garbled Tesseract still gets ~73% of individual
CHARACTERS right while destroying the words they belong to.

**Token agreement** is the metric that works: of Tesseract's Devanagari words on a
page, what fraction appear verbatim in a vision transcription of the same page? One
misread character makes a word a non-match, so it measures word integrity - which is
what a translator actually needs.

| document | T->V | V->T | reading |
|---|---|---|---|
| 2015_405693_Shatpath-Brahmanam | 0.302 | 0.293 | unusable |
| AphorismsOfSandilya | 0.403 | 0.352 | unusable |
| markandeya_purana | 0.513 | 0.518 | poor |
| nirukta | 0.545 | 0.505 | poor |
| harita_dvitiya_sthanam | 0.611 | 0.588 | best observed |
| harita_prathama_sthanam | 0.669 | 0.659 | best observed |

**The symmetry is the point.** T->V and V->T agree to within ~0.03 everywhere, and
both engines emit almost identical word counts (86 vs 89). If vision is the better
reading, both directions converge on Tesseract's word accuracy. So Tesseract is
30% accurate at worst and **67% accurate at best** - one word in three wrong in the
cleanest book in the corpus.

**Verified by eye, not asserted.** Every disagreement sampled from the BEST document
is a genuine Tesseract error: `सम्प्रवतत्यामि` for `सम्प्रवक्ष्यामि`,
`प्रथमोऽघ्यायः` for `प्रथमोऽध्यायः` (घ for ध), `व्याघयो` for `व्याधयो`,
`कमजा` for `कर्मजा`, `स्यः` for `स्युः`, `शुद्धस्फरिकवच्छुभ्रं` for
`शुद्धस्फटिकवच्छुभ्रं`.

**Vision is not perfect and must not be treated as ground truth.** In the same
sample Tesseract was right roughly one time in nine: `तरुणादित्यतेजसम्` (taruna,
young) where vision wrote the non-word `तरुश`; `उषितं` where vision wrote `उपितं`;
`अथातः`, the standard opening, where vision wrote `अथवातः`. A vision-only pipeline
silently loses those readings. This is the argument for keeping BOTH engines and
recording provenance, not for replacing one with the other.

**Sampling caveat.** The first probe took `cands[::step]`, which starts at index 0,
so short volumes were judged on their title page and opening chapter heading. The
probe now selects the DENSEST pages after dropping front matter. Figures above come
from the front-matter-inclusive pass and should be re-measured with `--pages 5` on
the dense sampler before being quoted as final.


### Dense-sample re-measurement, all 47 documents (2026-08-29)

The figures in the table above came from an evenly-spaced sampler that started at
index 0, so short volumes were judged on their title page. Re-measured on the five
DENSEST pages of each document after dropping front matter, at a cost of $0.0817:

    median shift +0.023, range -0.019 to +0.175
    Shatpatha moved most: 0.302 -> 0.477

So the earlier per-document numbers UNDERSTATED Tesseract, and any figure quoted
from the first pass should be replaced by the dense one.

**Distribution across 47 documents:** min 0.338, median 0.606, max 0.730.

    0.30-0.35  #            0.55-0.60  #########
    0.35-0.40  ##           0.60-0.65  ############
    0.40-0.45  #            0.65-0.70  #############
    0.45-0.50  ###          0.70-0.75  ##
    0.50-0.55  ####         0.75-0.80  (none)

One unimodal cluster from 0.477 to 0.730 with four clear outliers below 0.45
(tantric_texts 0.338, shiksha_avasananirnaya 0.382, AphorismsOfSandilya 0.388,
yajur_veda_shukla 0.413). The largest adjacent gap is 0.064 at ~0.445, which
separates those four from everything else - but it does NOT identify a "good"
band, because the whole cluster sits around 0.6.

**OPEN QUESTION - do not act on these numbers until it is closed.** Every figure
here is agreement WITH VISION. If vision agrees with itself only ~0.80 across two
passes, then 0.73 is near the ceiling and means something entirely different from
what it appears to mean. Measure the ceiling before drawing any conclusion:

```powershell
python scripts\ocr_probe.py --self-check --self-pages 12 --yes
python scripts\diag_probe_compare.py --ceiling <measured> data\ocr_probe_results_dense.json
```

  * ceiling ~0.95 -> the 0.34-0.73 spread is real Tesseract error, and no document
    in the corpus is safe on Tesseract alone.
  * ceiling ~0.75 -> the top of the spread is measurement noise and the whole
    per-document ranking must be re-interpreted before any book is re-OCR'd.


### CEILING MEASURED - the question is closed (2026-08-29)

Vision transcribed 12 already-probed pages a SECOND time at temperature 0.3 and
was compared with its own first pass:

    median vision-vs-vision agreement = 0.927
    11 of 12 pages fell between 0.894 and 0.978
    the outlier was Shatpatha p0002 at 0.707 - a page vision finds hard too
    cost: $0.0046

So 0.93 is what "the same reading" scores. Against that ceiling:

    best document   upapurana_kapila_purana   0.730 = 78% of achievable
    median document                           0.606 = 64% of achievable
    worst document  tantric_texts             0.338 = 36% of achievable

**No document in the corpus is safe on Tesseract alone.** The 0.34-0.73 spread is
real word-level error, not measurement noise. This closes the question the
previous section left open, and it settles the OCR architecture:

  * VISION is the source of record, for every document. 5,108 pages remain
    un-visioned; at the measured $0.00087/page that is **$4.44**.
  * TESSERACT is retained on every page as baseline, liveness check and per-page
    fallback. It has already caught six vision failures on Shatpatha alone that
    no vision-only pipeline could have seen.
  * PROVENANCE is recorded per passage (passages.ocr_engine), so a
    'tesseract-fallback' line can always be found, re-tried, or shown to a reader
    with the caveat it deserves.

Worked example, Shatpatha (320 pages): 314 vision, 6 tesseract-fallback, 0 lost.
