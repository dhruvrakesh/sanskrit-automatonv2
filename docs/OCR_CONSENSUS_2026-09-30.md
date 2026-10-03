# OCR consensus and Hindi independence (2026-09-30)

Markers: `OCR_CONSENSUS_2026_09_30`, `LACUNA_MEASURE_2026_09_30`, `HINDI_REF_AB_2026_09_30`.

Status: three new tools shipped. They add files and change no existing code. The pipeline wiring (C1 to C5 below) is proposed and waits for approval.

## 1. What was verified in the code

These facts were read from the code, not assumed.

| # | Finding | Where |
|---|---|---|
| F1 | The dashboard's OCR button, and `pipeline_queue.py`, run Tesseract only (`ocr_batch.py` into `data/raw`). Triage, vision and merge are manual CLI steps, and nothing calls them. | `dashboard.py` `/api/ocr`; `pipeline_queue.py` |
| F2 | The dashboard's Ingest reads `data/raw/{doc}_*.jsonl` only. Merged text in `data/raw_merged` reaches the DB only when you run the CLI ingest yourself. | `dashboard.py` `/api/ingest` |
| F3 | Re-ingest upserts on `(doc_id, page_no, idx)`. It never deletes and never replaces a translation. So a changed source text keeps its old translation, and that is why RUNBOOK 3b wipes first. | `ingest_jsonl_fast.py` |
| F4 | The translation cache key is `sha256(prompt_version + source text)`. Context and the English reference are not part of the key. As a result: (a) unchanged text re-translates from cache for free; (b) changed text always gets a new API call; (c) `--retranslate` on unchanged text returns the cached answer. | `infer_mt._hash`, `translate_batch` docstring |
| F5 | English never sees Hindi. Hindi is translated directly from the Sanskrit, but the QA-passed English of the same verse is added as `[Verified English reference ...]` whenever `translation_qa >= 0.6`. That is the default. No flag turns it off. | `translate_passages.py` ~L186-205, L346-361, L527 |
| F6 | `wipe_doc.py` opens SQLite with foreign keys off. The `translations_l10n` rows of wiped passages are orphaned, not cascaded. Passage ids are `AUTOINCREMENT`, so they are never reused, and the orphans cannot attach to new text. They are clutter, not corruption. | `wipe_doc.py`, `db_utils.py` |
| F7 | `inbox\siddhanta_shiromani_0001.pdf` is a whole 180-page book (13 MB) named as page 1. Tesseract spent 3.4 h on it before the 21:02 restart killed the job. | `inbox`, `jobs.jsonl` |

What F4 means: the translation layer already works as a learning system. The one missing piece is getting better source text into the DB. When a page's text improves, only its passages cost an API call. Every unchanged page is served from the cache. So the lever for quality is the OCR consensus, and it has to run by default rather than by hand.

## 2. What shipped today (additive, tested)

| Tool | What it does | Writes |
|---|---|---|
| `scripts/ocr_consensus.py --doc X [--yes]` | Runs triage, then vision (queue minus done, metered, `--max-usd` cap), then audit and repair (one redo round, rejected files kept in `_rejected\`), then merge, then a **drift report**. The drift report compares every consensus page on disk with the DB text for that page and lists pages as current, stale or missing. When the DB is behind, it prints the exact re-ingest commands and exits with code 3. Idempotent: run it any time. | `data/raw_vision`, `data/raw_merged`, `data/ocr_consensus/`. **Never writes the DB.** |
| `scripts/measure_lacunae.py [--doc X] [--csv f]` | Counts lacunas per document and per OCR engine, in English and Hindi. Unicode-safe, so it replaces the PowerShell `[???????]` query. The `hi_qmark` column flags Hindi damaged by encoding. | nothing (opens the DB read-only) |
| `scripts/diag_hindi_ab.py --doc X [--n 40] [--yes]` | Translates the same verses with and without the English reference, using the same prompt and context. It bypasses the cache. Scores: QA, lacunas, tatsama share (how much Sanskrit vocabulary is kept), and A-versus-B similarity. Also writes a side-by-side HTML. | `data/ab/`, plus one metered `api_usage` row |
| `tests/test_ocr_consensus.py` | 10 tests. Temp folders and a throwaway DB only. | nothing |

## 3. Proposed next (not written; each is one failure domain)

- **C1. Consensus button.** Add `/api/consensus` to the dashboard. It calls `ocr_consensus.py` and shows the drift summary on the row. Additive; the existing buttons are unchanged.
- **C2. Ingest prefers consensus.** In `/api/ingest`, use `data/raw_merged/{doc}_*.jsonl` when that set covers every page, and otherwise fall back to `data/raw`. The job log records which source it used.
- **C3. Re-ingest without losing unchanged work.** A `reconcile_doc.py` that does wipe, ingest and translate in one step. It archives the old translations to `translation_history` with reason `source-changed` before the wipe, so nothing is lost. F4 already makes unchanged passages free. It also cleans the orphans from F6.
- **C4. Hindi independence.** Decide from the A/B results. If Arm B, Sanskrit only, holds QA and has a higher tatsama share, add `--reference {auto,none}`, make `none` the default, and bump `PROMPT_VERSIONS['hi']` so the cache cannot return anchored answers. If Arm A wins on hard verses only, keep the reference but limit it to verses with low source quality. The numbers decide.
- **C5. Conjecture layer** (the earlier aspasht request). Keep a separate table, `translation_conjectures(passage_id, lang, text, confidence, basis, engine, created_at)`. The reader shows conjectures inside ⟨⟩, clearly labelled. They never overwrite the literal translation, and they are never counted in QA. Run it only after C1 to C3, because most lacunas are OCR failures that the consensus removes.
- **Chores.**
  - Set `COST_PER_PAGE` in `ocr_vision.py` to 0.00028 (measured).
  - Split `siddhanta_shiromani` with `--zero-pad 4`.

## 4. Measured 2026-09-30 / 10-01 (census, drift, triage)

- **Ingest fidelity is about 1.0.** Mallapurana was re-ingested from `data/raw_merged`. Its drift came back with 137 pages current: 132 at similarity 1.0, 4 at 0.95 or above, and 1 at 0.90 or above. So the 0.92 threshold separates "same text" from "different text".
- **Shatpatha is not current.** 34 pages are stale, all vision→vision at similarity 0.81–0.89, and most current pages sit at 0.90–0.95. All vision files are dated 08-29, so the DB text differs from today's consensus for a reason not yet known. Do not wipe it until `--explain` says why: `ocr_consensus.py --doc 2015_405693_Shatpath-Brahmanam --explain 0291,0164,0225`. That shows the DB rows by text_type and the word-level differences. Leftover noise rows (the 08-29 phrase-loop junk) are the first suspect.
- **Hindi damage check passed.** `hi_qmark = 0` everywhere, so stored Hindi has no encoding damage. The old `[???????]` query was simply wrong.
- **Hindi marks lacunas 5–20× more often than English on the same source:**

  | Book | English lacuna rate | Hindi lacuna rate |
  |---|---|---|
  | nilamata_seg | 0 % | 11.4 % |
  | nirukta | 1.8 % | 14.3 % |
  | harita_tritiya | 3.6 % | 53 % |
  | Shatpatha (vision) | 0.5 % | 4.4 % |
  | HAYASHIRSHA | 0 of 158 English done | 60 % |

  `hi_bare` is about 0, so these are partial lacunas inside otherwise complete Hindi. Most of this is a Hindi prompt or model effect, not OCR. Re-OCR alone will not remove it. `measure_lacunae.py` now prints three splits to locate it: by prompt version, by whether English was available, and paired (Hindi-only versus both).
- **Triage cannot run on most older books.** Pages OCR'd before 08-30 carry no Tesseract confidence. The fallback is to vision every page, which costs $0.00028 a page, about $0.21 for HAYASHIRSHA, markandeya, nirukta and harita_tritiya together: `--include-unassessed`. Two books cannot take this route:
  - Bodhicaryavatara has no page PDFs in `inbox`.
  - nilamata_seg is a resegmented derivative of upapurana_nilamata_purana and has no pages of its own.

## 5. Measured 2026-10-01 / 10-02: corrections and the Hindi finding

- **Correction: Shatpatha was never stale.** `ingest_jsonl_fast.py` normalizes text before storing it (`normalize_sanskrit`, which joins words hyphenated across line breaks), and the first drift report compared the *raw* consensus text. I re-normalized pages 0001, 0093, 0164, 0225 and 0291: their token counts come to 17, 144, 26, 99 and 102, exactly the DB's. Drift now compares what ingest would store (`ingest_view`, OCR_CONSENSUS_NORM_2026_10_02). One small edge remains: a hyphen before a *blank* line is also joined (`विश्व-\n\nअथ` becomes `विश्वअथ`). Leave it for now.
- **Mallapurana after consensus:**

  | Text source | English with lacuna | Hindi with lacuna |
  |---|---|---|
  | vision pages | 6.4 % | 5.7 % |
  | Tesseract pages (the 58 triage accepted + 4 vision failures) | 55.4 % | 57.2 % |

  Paired: of 704 verses translated in both languages, 122 have a lacuna in both, 0 in English only and 4 in Hindi only. **In this book the lacunas are OCR, and Tesseract confidence of 72 or more did not mean translatable.** At the measured $0.00028 a page, triage saves cents per book. Recommendation: vision every page (`--threshold 101`).
- **Hindi elsewhere is a prompt effect.** Paired counts are Hindi-only 125 vs both 0 for nilamata_seg, 123 vs 8 for harita_tritiya, and 43 vs 0 for HAYASHIRSHA.
- **A/B of the English reference** (5 runs, 200 verse-pairs):

  | | With the English reference | Without it |
  |---|---|---|
  | Lacunas, pooled | 65 | 76 |
  | Tatsama (Sanskrit vocabulary kept) | lower | higher in **all 5 runs** |
  | QA score | saturated, about equal | saturated, about equal |

  - Run-to-run noise on the same 40 verses: with the reference 15, 20 and 17; without it 18, 18 and 21.
  - The reference helps mainly where the OCR is garbled. English silently emends (for example, ṛṣiśārdūla from a garbled `षिशाह लो`), and Hindi copies that only when it can see the English.
  - **Neither setting fixes the problem.** On clean nilamata the current prompt still marked 8 to 13 of 40 verses.
- **Next measurement:** run `prompts/hi-v4-candidate.txt` with `diag_hindi_ab.py` arms a/b/c/d on the stored-lacuna population. The candidate keeps rules 1–9 verbatim; rule 11 says to conjecture damaged words inside ⟨ ⟩, to keep readable rare words as tatsama, and to use [अस्पष्ट] only for truly unreadable characters.
