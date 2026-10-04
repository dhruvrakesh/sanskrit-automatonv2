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

## 6. Measured 2026-10-03: Mallapurana complete, and the empty-vision cause

- **Mallapurana after vision on every page** (`--threshold 101`):

  | | Before (all Tesseract) | After |
  |---|---|---|
  | English translated | 705 / 1037 | 1005 / 1036 (QA mean 0.994) |
  | English lacuna rate | 64 % | 7.8 % |
  | Hindi lacuna rate | 65 % | 8.1 % |
  | Lacuna rate on vision pages | — | 4.5 % (English) / 4.7 % (Hindi) |

  Paired: 72 in both languages, 6 English only, 8 Hindi only. The remaining lacunas sit on 53 passages from 10 pages that vision returned **empty**: 71 % English lacuna rate on those.
- **Likely cause** (not yet confirmed). `ocr_vision.transcribe` uses `max_output_tokens=8192`, and gemini-2.5-* thinking tokens count against that budget. Its retries change only temperature, and it discards `finish_reason`. `patch_ocr_vision_finish.py` (VISION_FINISH_2026_10_03) does four things:
  - adds the 16384/32768 budget ladder that `infer_mt.py` already uses;
  - records `finish` and `retries` in each page's meta, so the next empty page names its cause;
  - meters paid retries;
  - sets `COST_PER_PAGE` to 0.00028.

  Corpus-wide, 12 vision pages are empty where Tesseract has text: Mallapurana 10, Shatpatha 1, Aphorisms 1.
- **Hygiene census** (`diag_text_hygiene.py`, 54,818 passages):

  | Defect | Rows | Note |
  |---|---|---|
  | Apparatus rows | 36 | 35 Mallapurana. 15 were paid in English and 15 in Hindi |
  | 2–4-character vision loops | 20 | |
  | Bracketed meta outputs | 1 | on an apparatus row |

  These are small. `classify_apparatus.py` (APPARATUS_TAG_2026_10_03) tags apparatus rows as noise and keeps their translations; it is reversible with `--undo`. The unit loops are left for the next merge change.

## 7. Measured 2026-10-03 (afternoon)

- **`ab_source_quality.py` on markandeya (10 pages, judge-graded against the vision text):**

  | | Old translations (from Tesseract text) | New translations (from vision text) | Change |
  |---|---|---|---|
  | Fidelity | 1.20 | 2.40 | +1.20 |
  | Fluency | 2.60 | 3.60 | +1.00 |

  New was better on 4 pages, tied on 4 and worse on 2. That is past the BENCHMARKS decision line (+0.5), so **re-OCR plus re-translation is justified on translation quality**, not only on provenance.
  - Caveat: one judge, 10 pages.
  - Absolute scores are low because this experiment translates a whole page in one call, which is not the production verse-by-verse path.
  - The first attempt died on a 504 inside `ocr_vision.transcribe`, which has no transient retry when called directly.
- **Vision on the refused pages:**
  - RECITATION is not beaten by splitting the page into bands. Mallapurana pages 0022, 0026 and 0029 were refused again after 4–5 paid calls; 0024 ended on a 504.
  - VISION_FINISH3 turns banding off by default (`OCR_RECITATION_TILES` turns it back on), stops temperature retries on RECITATION, and retries once on transient errors.
  - These pages stay on Tesseract and are marked `finish=RECITATION` in their meta.
- **Apparatus rule refined (APPARATUS_TAG2_2026_10_03).** The first rule tagged 3 chapter colophons (p59.2, p63.8 and one more) and a verse with footnotes (p56.11) as noise. The rule now excludes colophons and rows that open with a danda-marked verse; `--reconcile` restores them.

## 8. Hindi: the four-way test (2026-10-03) and the production switch (HI_PROMPT_FILE_2026_10_03)

**Measured.** The population was 160 verses whose stored Hindi already had a lacuna, 40 each from nilamata_seg, harita_tritiya, HAYASHIRSHA and markandeya. Every arm used the same verses, the same context and the same model.

| Arm | Verses with lacuna | Lacuna marks | Conjectures ⟨…⟩ | Damage left unmarked* |
|---|---|---|---|---|
| a: hi-v3, with English (production today) | 143 / 159 | 496 | 0 | 8 |
| b: hi-v3, Sanskrit only | 150 / 160 | 527 | 0 | 4 |
| c: hi-v4 candidate, with English | 89 / 160 | 178 | 533 | 11 |
| d: hi-v4 candidate, Sanskrit only | **74 / 160** | **170** | 565 | 9 |

\*Unmarked damage means the verse contains Latin OCR debris, but the output has neither a lacuna nor a conjecture mark. 136 of the 160 verses contain debris.

- **Per book, arm d against arm a.**

  | Book | Verses with lacuna, a → d |
  |---|---|
  | nilamata_seg | 33 → 18 |
  | harita_tritiya | 39 → 28 |
  | HAYASHIRSHA | 38 → 16 |
  | markandeya | 33 → 12 |

  Conjectures make up 5–16 % of the output characters.
- **What the conjectures are.** Read by hand, most are real OCR corrections: घाव्री → ⟨धात्री⟩, सेन्यव → ⟨सैन्धव⟩, शोभाझनक → ⟨शोभाञ्जनक⟩, wa → ⟨वकार⟩, चलुरख → ⟨चतुरस्र⟩.
- **Defects in hi-v4:**
  - Phrase-length guesses, e.g. ⟨स्वादु मधु और घृत⟩.
  - Sanskrit stems left inside ⟨⟩, e.g. ⟨तोयसमाम्⟩.
  - Silent handling of damage: HAYASHIRSHA p77.5 drops `afaeay` and `ASAT` without any mark, and markandeya p61.7 adds "मार डाला" from `TET` without one.
- **hi-v5 (`prompts/hi-v5-candidate.txt`).** Rules 1–10 are unchanged. Rule 11 now says:
  - (क) Put the *Hindi* rendering inside ⟨⟩, at most three words to a mark.
  - (ख) Never mark a word that can be read.
  - (ग) Use [अस्पष्ट] only for unreadable characters.
  - (घ) Every damaged spot must carry one mark or the other; nothing may be dropped or added silently.

**Production path (data, not code).** `patch_hindi_prompt_file.py`:
- `infer_mt` uses `prompts/hi-production.txt` when that file exists, with version `hi-file-<content hash>`. That gives a new cache key and a new `mt_prompt_version` automatically.
- `translate_passages` gains `--reference none`, which appends `+noref` to the version so a cached answer made with the reference is never reused.
- It also gains `--only-lacuna`, which re-translates only rows that carry a lacuna; old rows are archived to `translation_history`.
- Nothing changes until the file exists. To activate, copy the validated candidate to `prompts/hi-production.txt`. To revert, delete it.

**Gate before activation:** arm d with hi-v5, on the same population, should show:
- lacunas no higher than hi-v4 d (74 of 160);
- unmarked damage at or below 4 (arm b's rate);
- a hand check of 20 conjectures.


## 9. The hi-v5 gate, paired, and the decision (2026-10-04, DOCS_2026_10_04)

hi-v5 (`hi-file-37e6ff9a2b`) was put into production on 2026-10-03 before its gate was read. The four v5 runs are now compared with the v4 runs of the same morning. For three books the 40 verses are **the same verses** (passage ids overlap 40 of 40), so the comparison is paired. All runs use arm d (no English reference) and the lacuna population.

| Book (same 40 verses) | Verses with a lacuna, v4 / v5 | Lacuna tokens, v4 / v5 | Conjectures, v4 / v5 | Unmarked damage, v4 / v5 |
|---|---|---|---|---|
| HAYASHIRSHA_PANCARATRA | 16 / 25 | 28 / 38 | 94 / 124 | 2 / 0 |
| harita_tritiya_sthanam | 28 / 33 | 100 / 146 | 344 / 523 | 2 / 0 |
| nilamata_seg | 18 / 24 | 23 / 29 | 49 / 56 | 1 / 1 |
| **Total (120 verses)** | **62 / 82** | **151 / 213** | **487 / 703** | **5 / 1** |

markandeya_purana is not paired (the samples share 1 verse). Its unpaired figures are v4 12/40 and v5 16/40.

**Hand check.** I read six verses where the two prompts disagree on whether to mark a lacuna:

- v4 is better in four:
  - `facta` gave v4 ⟨विदीर्ण करो⟩; v5 left the sentence without its verb.
  - `SHEET` gave v4 ⟨देखकर⟩; v5 both marked the gap and guessed.
  - Verse 60251 is fluent under v4.
  - In verse 101301, v5 put the readable चैव in ⟨⟩, breaking its own rule 11(ख).
- v5 is better in one. In 101221, v4 echoed the Sanskrit lines into the Hindi. Echoes are rare under both prompts: v4 1-2 per 40 verses, v5 1-4.
- Neither is right in one. In 101423, शरगुष्व is शृणुष्व ("listen"), and both prompts missed it.

**Decision: production goes back to v4.** Copy `prompts/hi-v4-candidate.txt` over `prompts/hi-production.txt`; the version becomes `hi-file-18a0d5f5eb`. v5 has one real gain, "every damaged spot is marked" (unmarked 5 to 1), and it costs 20 more verses with gaps out of 120. The candidate for that gain is a v6 that adds only rule 11(घ) to v4, gated paired against v4 on the same 120 verses before any switch.

**What prompts cannot do.** The source-junk column of the A/B files shows that 29 to 40 of every 40 sampled verses carry Tesseract debris (Latin fragments inside Devanagari). After the production `--only-lacuna` runs, these books still carry lacunas on 37-57% of their Hindi rows: markandeya, HAYASHIRSHA, nilamata. The damage is in the source text. The order that converges is:

1. vision consensus;
2. wipe and re-ingest from raw_merged;
3. translate. Changed text is a new cache key, so only changed verses are paid for.

`scripts/corpus_status.py` now says this per book (RUNBOOK, "Is the corpus up to date?").

**Upsert caveat, verified in `ingest_jsonl_fast.py`.** On re-ingest, `ON CONFLICT ... DO UPDATE` replaces `text` but deliberately not `translation`. Re-ingesting changed text on top of a doc, without `wipe_doc.py` first, would therefore leave old translations attached to new text, possibly to different verses if segmentation moved. `reingest_commands()` always wipes first. Keep it that way.


## 10. The first corpus-wide status, and why v1 of it was wrong (2026-10-04, DOCS2_2026_10_04)

`corpus_status.py` v1 ran on 36 docs (at least 20 passages each). It returned NEEDS-OCR for 15 and NEEDS-TRANSLATION for 21. It judged source damage from **lacuna rates**, which is the wrong evidence. It went wrong in two directions:

- **It sent clean-English books to OCR on Hindi lacunae alone.** For example, vasishtha_dhanur_veda had English 0.0% and Hindi 72.7%, and harita_prathama_sthanam had English 2.7% and Hindi 56.4%. Older Hindi prompts produce those lacunae.
- **It sent untranslated Tesseract books to translation.** A book with no translations has no lacunae, so v1 read it as clean. Examples are 476948-Rgveda-samhita_Vol-ii (7,053 passages) and SP_4214_Pataal_Khanda (19,071 passages). Translating Tesseract debris is the most expensive mistake available.

**v2 (`CORPUS_STATUS2_2026_10_04`) measures the source.** Source debris is the share of passages with at least 8 Devanagari characters that contain Latin-letter runs. It is the same JUNK test that `diag_hindi_ab.py` uses. I calibrated it on the page files on 2026-10-04, counting per text line:

| Producer | Debris |
|---|---|
| Tesseract (`data/raw`) | Ganita 10.3%, Karan 13.5%, manu 17.7%, jyotish 19.4%, upapurana_nilamata 20.2%, harita smriti 21.3%, harita_tritiya 22.2%, nirukta 24.5%, markandeya 26.4%, Natyasastra 29.6%, Bodhicaryavatara 33.8%, tantric texts 35.2%, vasishtha 35.8%, shukla yajur 35.8%, HAYASHIRSHA 36.0%, Sandilya 38.4%, Mallapurana 43.6%, Pataal Khanda 48.5%, LalitaVistara 49.6%, Rgveda 53.9%, Shatapatha 58.5%, bodhyana 70.9% |
| Vision (`data/raw_vision`) | Shatapatha 0.0% (merged 0.9%), Rgveda 0.5%, Sandilya 1.8%. Mallapurana is 10.4% (merged 11.7%); that comes from plate captions and its 5 refused pages. |
| E-text | MBh01 0.0% (raw engine `gretil-bori-etext`) |

So `--debris-ok` defaults to 5%. NEEDS-OCR now means: debris above 5%, fewer than half the passages from vision, and page PDFs present in inbox. No translation is recommended until consensus is done.

**Provenance is read from the page files, not inferred.** Three docs carry engine `resegment-devnum` with `meta.src_doc`:

| Derived doc | Source doc |
|---|---|
| nilamata_seg | upapurana_nilamata_purana |
| smriti_14manu_smriti_seg | smriti_14manu_smriti |
| smriti_16harita_smriti_seg | smriti_16harita_smriti |

Their pages match their sources' pages at only 0.06-0.19 similarity (sampled pages 10, 30 and 60). That is expected, because they are the same text cut at different places. So a derived doc is never re-OCR'd itself. The order is:

1. vision on the source;
2. re-ingest the source;
3. `resegment_doc.py`;
4. wipe the derived doc and ingest it with `--no-segment`.

The verdict for these is DERIVED-NEEDS-OCR. This follows the rule `diag_corpus_overlap.py` records: row counts are not evidence.

**Source PDFs.** vision needs `inbox/<code>_NNNN.pdf`. None exist for LalitaVistara, Bodhicaryavatara, bodhyana, vasishtha_dhanur_veda or shiva_dhanur_veda; their verdict is NO-SOURCE-PDF. MBh01 is e-text and needs none.

For vasishtha_dhanur_veda and shiva_dhanur_veda, inbox holds `dhanur_veda_vasishtha_dhanur_veda_*` (32 pages) and `dhanur_veda_shiva_dhanur_veda_*` (19 pages), the same page counts as their raw files. That is a hint only; their raw pages 10, 30 and 60 matched at 0.47, 0.10 and 1.0. The report offers a copy-with-rename command, to run after a person compares two pages.

**Fixed with it (`MAINT_2026_10_04`):**

- `resegment_doc.py` wrote one file per source page but opened it once per source passage. On a segmented source, only each page's last passage survived. Consecutive entries are now merged. Page-blob sources give identical output.
- `images.py approve` stopped at the first already-approved id (`approve 3 4 5 6 10` left 6 and 10 as drafts). It now skips and continues.
- `tests/test_translation_filters2.py` asserted the built-in Hindi version, so it failed whenever a reviewed prompt file was active. It now checks the built-in prompt in a child process with the file switched off. That was the one failure in the 117-test suite.


## 11. Two doors, two guards (2026-10-04 afternoon, DOCS3_2026_10_04)

**The pilot did not run.** `ocr_consensus.py --doc markandeya_purana --threshold 101 --yes` stopped at triage: "100 page(s) have no confidence recorded (OCR'd before 2026-08-30)". Pages OCR'd before that date carry no Tesseract confidence, so triage has nothing to rank. `--include-unassessed` queues every inbox page; corpus_status now prints it on every consensus command. Nothing was spent and nothing was written.

**INGEST_SOURCE_2026_10_04 (scripts/ingest_jsonl_fast.py).** Two faults were found in the code and files:

- *The glob caught other books.* The glob `<doc>_*.jsonl` also matches docs whose code starts with `<doc>_`. data/raw holds 208 `smriti_14manu_smriti_seg_*` files beside the 208 `smriti_14manu_smriti_*` files, and the same holds for `smriti_16harita_smriti`. Ingesting the source doc therefore also ingested the derived doc's files on the same page numbers. Both manu docs show 2,568 rows, which is consistent with this.
  - Only `<doc>_NNNN.jsonl` and `<doc>_NNNN_norm.jsonl` are taken now.
  - The others are named in the log.
- *Ingest could undo consensus.* The dashboard Ingest button and `advance_pipeline.py` ("Translate All OCR'd") ingest `data/raw/<doc>_*.jsonl`, which is Tesseract text. For a doc with consensus, that put Tesseract text back over vision text, and upsert keeps the old translations on the new text. Now:

  | Situation | What ingest does |
  |---|---|
  | `data/raw_merged` covers every page | ingests raw_merged and says so |
  | `data/raw_merged` covers only some pages | refuses (exit 3) |
  | `--source raw` | Tesseract, deliberately |
  | `--source given` | the glob exactly as given (the old behaviour) |

  This fixes plan item C2 at the one place every path goes through.

**TRANSLATE_DEBRIS_GUARD_2026_10_04 (scripts/translate_passages.py).** Before any API call, it refuses (exit 3) when all three of these hold:

- more than 30% of passages carry debris (`--debris-max`, env `SA_DEBRIS_MAX`);
- fewer than half the passages come from vision;
- inbox holds page PDFs for the doc.

On the page-file measurements, that stops Rgveda Vol-ii (53.9%), Pataal Khanda (48.5%) and HAYASHIRSHA (36.0%). It lets these through:

- Ganita (10.3%), whose translation was running at 12:21 (1,069 of 2,592 verses);
- Natyasastra (29.6%);
- every book with no source PDF.

You can override it with `--allow-debris`, or with env `SA_ALLOW_DEBRIS=1` for dashboard runs. Single-verse reader requests are never blocked.

**Measured translation cost:** $0.00021 per passage (corpus_status, from usage_log). For example, Ganita's 2,592 verses cost about $0.54, a lower bound. A Tesseract-to-vision re-ingest later changes nearly every verse's text, so those translations are paid for again.

**Release:** `release.ps1` without `-Apply` is a dry run. The 2026-10-04 dry run listed 19 clean paths.
