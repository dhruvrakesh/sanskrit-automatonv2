# Enterprise path forward — 2026-09-06

State of the system as measured today, what is proven, what is not, and the
order in which the remaining work should be done. Nothing in this document is
estimated where it could be measured; where a number is a projection it says so.

---

## 0. What is true right now

| | |
|---|---|
| Dashboard | running, Phase G loaded (`/api/embeddings`, `/api/entities` live) |
| Live job | Shatpatha **Hindi** translation → `translations_l10n`, ~211/2376 |
| Rate | ~6 verses/min ⇒ ~6h total; the previous attempt died at 4h17m |
| Errors | ~1 per 30 verses, accumulating linearly |
| Git | `main` = `origin/main` = `f44c5bc`; this session's work uncommitted |
| DB | 560 MB, WAL 7 MB, single writer held by the translator |

**Do not restart while that job runs.** `_run_job` uses `subprocess.Popen` with
pipes, no `creationflags`, no Job Object; `restart_dashboard.ps1` kills only the
port listener. Children are not killed — they fill the ~64 KB pipe and block
forever, holding DB connections, invisible to the new `JOBS` list. That is what
destroyed 4h17m of work at 10:16 today. Procedure: RUNBOOK §9d.

---

## 1. Fixed today, with the evidence

### 1a. Phase G rendered a 40px-wide dashboard
`.sidebar`, `.main`, `.log-panel` declare `grid-row:2`; the two new `.splitter`
divs did not. CSS Grid places definite-row items before auto-placed ones, so the
splitters were swept into columns 4–5 and `.main` was crushed into the 6px
track. **Every static check passed**: `py_compile`, `node --check`, braces
138/138, both markers, both endpoints, zero JS errors in the browser.

A layout change is not verified until something lays the page out.
`scripts/verify_ui.py` now does, 19 assertions, and was confirmed as a negative
control against the broken file (5/9, naming the cause). RUNBOOK §9c.

### 1b. A failed job left no trace
`py()` was `[sys.executable, *args]`. No `-u`. CPython block-buffers stdout at
8 KB when it is a pipe, and `_run_job` pipes both streams, so a job that does
not exit cleanly loses everything it printed. The `entities` job on Shatpatha
recorded `ok:false, out_lines:0, err_preview:""` after 32.9 seconds of work.
Fixed: `-u`, plus `rc` and `out_tail` in `jobs.jsonl`. Takes effect at the next
restart.

### 1c. The corpus is paying to translate the printed page's headers
Five layers could have caught this and none could:

| layer | why it could not |
|---|---|
| `segment_verses` | keeps the running head attached to the page's first verse |
| `classify_noise.is_noise` | `dev < min_dev AND lat < min_lat` — a **whole-passage** test. Header + real verse is mostly Devanagari, so it can never fire |
| `classify_frontmatter` | looks for English/Hindi body text; this is Sanskrit |
| `clean_for_mt` | every rule in it was **Latin-script** (`^Page \d+$`, `[\d+°]`, `[fol. 3]`). Not one Devanagari rule. `_PUBLISHER_BANNERS` likewise all ASCII |
| `score_translation_quality` | scores whether the **output** is well formed. A fluent translation of a page header scores **1.0** |

Fixed in `clean_for_mt` — the single gate between the DB and the model
(`translate_passages.py:333`, the only caller). It changes what is **sent**;
it rewrites no rows and is reversible by restoring one file.

Measured on 1,321 real Shatpatha passages:

```
226 furniture-carrying passages  ->  226 stripped   (100%)
   losing >45% of their Devanagari ->   0
1,095 clean passages             ->   20 touched
   all 20 were running heads the DETECTOR had missed
   (सायणाचार्यभाष्यसमेतम्, अनन्तदेवीयभाष्यसमेतम्, बृ० ३ अ०),
   printed rules ('________'), or bare page numbers ('**(१७६)**')
genuine false positives          ->    0
```

The stripper matches folio **abbreviations** (का० प्र० ब्रा० बृ० अ० पृ०) and
title **suffixes** (…ब्राह्मणम्, …संहिता, …भाष्यसमेतम्) — never a commentator's
name, because OCR renders सायण as सायणा, सायणे and सायणाचार्य within one book.

---

## 2. Corrected today

**"1,705 duplicate pairs" was wrong.** 1,705 of 2,059 is 83%; that is a broken
gate, not a finding, and acting on it would have damaged the corpus.
Classified by cause:

```
  726  fans out, no furniture     NOT duplicates — formulaic repetition
  306  commentary quoting mula    NOT duplicates — Sāyaṇa doing his job
  281  unexplained 1:1            needs eyes
  244  furniture, but fans out    ambiguous
  148  REAL duplicate (1:1)       ← the actual defect; 42 already translated
```

Two errors: deciding "damaged" by **Devanagari share** (Sāyaṇa's lemma-quoting
`' वागेव ' प्रथमं ' ह '` is full of quote marks, so legitimate commentary scored
as noise — that measures typographic density, not corruption); and never
checking **fan-out** (passage 113067 paired with twelve different verses; 67% of
pairs involved a member with 2+ partners). A real duplicate is one-to-one; a
one-to-many fan is a commentary block.

Also corrected: `tr_score` is a **length ratio** (`min(1.0, ratio/5.0)`,
`db_utils.py:68` calls it legacy). 0.27–0.37 means translations run 1.4–1.9×
source length. It is not a quality signal and must not be read as one.

---

## 3. Ran today, and what it returned

`ocr_triage.py --calibrate --doc 2015_405693_Shatpath-Brahmanam`:

> No pages carry confidence yet.

`ocr_pdf.py` has recorded `conf_mean` only since 2026-08-30; Shatpatha was
OCR'd before that. **The deterministic triage gate remains unproven, and cannot
be proven without re-running Tesseract on a document to populate confidence.**
That is free (local Tesseract, no API) but costs wall-clock. Until it is run,
the architecture you chose — Tesseract everywhere, vision only where needed —
has no measured threshold, and the fallback stands: vision every page of a
document the probe rates poorly.

---

## 4. The order of the remaining work

Sequenced so that nothing expensive is spent before the measurement that would
justify it, and nothing touches the DB while the translator holds the writer.

**Now — safe alongside the running job (read-only or file-only)**

1. `diag_duplicate_verses.py --sql` — review the reclassify statements. Do not
   apply yet.
2. `ocr_triage.py --calibrate` on a doc OCR'd after 2026-08-30, if one exists;
   otherwise pick the cheapest document and re-run Tesseract to populate
   confidence, then calibrate. This unblocks the whole OCR-spend question.
3. Reconcile the provider console against `usage_log`. 89.3% of the ledger is
   still a `chars/4` estimate and `infer_mt.py` is not wired to provider token
   counts. Until reconciled, every cost figure in this project is an estimate
   wearing a dollar sign.

**When Shatpatha finishes — needs the writer, or a restart**

4. Restart (picks up `-u`, `rc`, `out_tail`), then re-click **Entities** on
   Shatpatha. The failure will finally say why.
5. Apply the reviewed reclassify SQL, after `db_backup.py`. Sets `text_type`,
   never deletes.
6. Re-translate the 42 damaged copies that already hold an English translation —
   or, better, let the reclassify remove them from the translatable set and
   leave the clean copy as the reading.
7. Clear the 746 orphaned vectors and 1,231 orphaned mentions.
8. Rebuild embeddings + entities for Shatpatha so search sees the corrected set.

**Then, and only then — the spending decisions**

9. `ab_source_quality.py` (~3¢, never run). It tests whether better OCR produces
   better **translations**, which has never been measured. It is the only thing
   standing between you and an ~$11 corpus rebuild decision made on instinct.
10. Rgveda: 1,065 pages, never OCR'd by any engine. Vision at the measured
    $0.00087/page is ~$0.93 for the whole book; Tesseract is free. The triage
    calibration (item 2) decides the split.
11. Shatpatha **English**. The job running now is Hindi. English is the track
    whose 608 translations were lost, and it is still outstanding.

**Structural, not urgent**

12. Nothing adjudicates an engine disagreement. `ocr_variants` records both
    readings and no code chooses between them. Today's finding suggests the
    adjudicator should be source-side, not output-side: `tr_qa` scoring 1.0 on
    an inverted verse is proof that output well-formedness cannot detect input
    damage.
13. `_run_job` still has no Job Object, so a restart still orphans children.
    That is a real fix with real risk and does not belong in a patch alongside
    a logging change.

---

## 5. The thing worth saying plainly

The most expensive defect found today was not a crash. It was
`तं न पश्यति` ("no one sees him") becoming `तत्र पश्यन्त्य` ("they see him as
incomplete") — an OCR slip that reversed a Brāhmaṇa's meaning, translated
fluently, scored `tr_qa 1.0`, and stored beside the correct reading where search
and RAG will surface either.

Every quality gate in the pipeline scores the **output**. None scores whether
the **input** survived the scanner. That is the gap this project should close
next, and it is the one that matters for a corpus meant to be trusted.
