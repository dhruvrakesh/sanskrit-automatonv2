# The scholarly English in the Library and the reader; are the Āgamas done; are we gaining; the benchmarks (16 Oct)

Markers:
- **LIBRARY_SCHOLAR_2026_10_16:** `scripts/dashboard.py`, patched by `scripts/patch_library_scholar_2026_10_16.py`.
- **READY_PRICE_2026_10_16:** `scripts/scholar_translate.py` and `scripts/redeem.py`, patched by
  `scripts/patch_ready_price_2026_10_16.py`.
- **DOCS63_2026_10_16:** `scripts/patch_docs63_2026_10_16.py`.

**Sources:**
- the daily backup `D:\backups\context_daily.db` (22:31 UTC, 15 Oct), read with `mode=ro&immutable=1`;
- `scripts\dashboard.py`, `scripts\scholar_translate.py`, `scripts\translate_passages.py`, `scripts\redeem.py`;
- `docs\cloud\C4_corpus_mirror_2026-10-08.sql` (the site's mirror);
- the papers and pages listed in section 6, read on 16 Oct.

Asked on 16 Oct: "the library does not seem to reflect the substantial amount of work done by sonnet api in
translation. fix that too!"; whether something that exists already could be a benchmark; whether this is the
enterprise way; and whether this translator could become the basis of better Indic translators.

## 1. Why the Library did not show it

The Library's cards count the **working English** (`passages.translation`). It is the English the site shows, made by
gemini-2.5-flash a passage at a time.

The **scholarly English** (`scholar_translations`) is a separate layer: 2,460 verses, 2,436 of them by
claude-sonnet-5-5 on 15 Oct. It was only on `/scholar` (the "Scholarly English" button in the Library's header). So:
- the Hayaśīrṣa's card said "EN 1/1614";
- the Kāraṇāgama's said "EN 368/1908".

Nothing was lost: the rows are all there.

## 2. LIBRARY_SCHOLAR_2026_10_16 (dashboard.py)

**The Library:**
- A card carries **SC n** beside **EN n/N**. Under it a line: "Scholarly English: n verses by <engine>; passed,
  flagged, source doubts", with a person's verdicts and the stale rows when there are any. It links to the text verse
  by verse (`/scholar/<doc>`) and as prose.
- A text with scholarly English and no working English is listed too.
- The header counts the verses in scholarly English and links to `/scholar`.

**The reader** (`/reader/<doc>`, `/api/passages/<doc>`):
- In English, a verse's scholarly English stands above its working English. It shows:
  - its status: passed, flagged, source doubt, or accepted or rejected by a person;
  - the sentence it belongs to, when a Sanskrit sentence runs over several verses;
  - its engine;
  - a link to its notes and checks on `/scholar/<doc>`.
- The header says how many verses are in scholarly English.
- "Not yet translated" now says that it is the working English, the one the site shows, that is not.

**What is counted:**
- Each verse's latest row, as `/scholar/<doc>` shows it.
- A row whose Sanskrit has changed since it was made is stale. It is counted apart and not shown.

**It is read-only:** the working English, the site and the scholarly rows are not changed.

**The cost of the count:**
- The first count read 0.6 s on the 15 Oct backup (in the VM).
- It is kept for 2 minutes, or until a row or a passage is added.
- A reader page adds about 0.01 s.

**What the Library shows now:**

| Text | Working English (EN) | Scholarly English (SC) | Passed | Flagged | Source doubts |
|---|---|---|---|---|---|
| The Hayaśīrṣa Pañcarātra | 1 of 1,614 | 1,418 | 1,176 | 220 | 22 |
| The Kāraṇāgama | 368 of 1,908 | 1,018 | 867 | 147 | 4 |
| MBh01 (the pilot) | | 24 | 19 | 5 | 0 |

The header reads "2,460 verses in scholarly English".

**Tests:** `tests/test_library_scholar_2026_10_16.py` (6).
- The cards, the header, a text with no working English.
- The cover follows the rows and fails quietly.
- The reader: the page's verses only; stale rows not shown; English only.
- Nothing is written.
- The patcher's replay.

`test_cost_truth_2026_10_15`'s replay chain now ends at the `.bak_libsch_` copy for dashboard.py.

The page was also opened in Chromium on a fixture: the cards and the reader drew as meant, with no script error.

## 3. Are the two Āgamas done?

Yes, for their Sanskrit verse: all but 17 verses of the Hayaśīrṣa and 10 of the Kāraṇāgama. Each passage that is not
in scholarly English, by why (the 15 Oct backup; readiness at `--min-quality 0.35`, as the runs chose):

**The Hayaśīrṣa Pañcarātra** (1,706 passages):

| Passages | What |
|---|---|
| 1,418 | in scholarly English |
| 92 | noise or front matter |
| 89 | the edition's apparatus: the footnotes with the manuscripts' readings ("This verse is omitted in B,C"). Not verse. Where a page has three or more, the translator gets them beside the verse |
| 35 | other Latin letters: title pages, English |
| 26 | a reading below quality 0.35 |
| 17 | the सूचीपत्रम्, the table of contents (pages 6–7): not verse |
| 15 | **verses whose reading carries the vision OCR's footnote marks, `<sup>6</sup>`** (pages 18 and 78). The debris test read "sup" as Latin letters. READY_PRICE_2026_10_16 makes them ready |
| 2 | ready and not done (pages 22 and 100) |
| 7 | numbers among the words (an index, errata) |
| 5 | fewer than 8 Devanagari signs |

**The Kāraṇāgama** (1,909 passages):

| Passages | What |
|---|---|
| 1,018 | in scholarly English |
| 651 | the edition's own Hindi: Prof. Rama Chandra Pandey's translation and preface. Not Sanskrit |
| 88 | the scan's watermark ("Digitized by eGangotri", "Jangamwadi Math Collection"). With that line taken out, the watermarked passages that would pass (24, of every kind) are title pages, Hindi sentences and the index of half-verses (pages 163–176): no verse |
| 69 | fewer than 8 Devanagari signs |
| 62 | other Latin letters: title pages, English |
| 10 | ready and not done: one each on pages 11, 26, 41, 51, 55, 59, 78, 79, 87, 143 |
| 9 | numbers among the words |
| 2 | noise; a reading below 0.35 |

**What is left:** 17 + 10 verses, about $1.25 of the credit at $0.046 a verse. The dry run says which (section 9,
step 9). Pages 11 and 26 of the Kāraṇāgama are front matter by their look: a person decides from the dry run.

## 4. A finding: the working English translates the edition's Hindi

**The Kāraṇāgama's 368 passages of working English** (gemini-2.5-flash, 14–15 Oct):

| Passages | What the English was made from |
|---|---|
| 172 | the Sanskrit verse (168 of them in scholarly English too) |
| 159 | Prof. Pandey's Hindi (for example, his preface's blessing from the Jagadguru of the Kāśī pīṭha) |
| 36 | debris |
| 1 | an index |

**Why:**
- `translate_passages.py` has no guard for an edition's own Hindi; `scholar_translate.py` has one (its readiness).
- So the Library's **Finish EN** would translate about 490 more Hindi passages into English: about $1.2, and the
  entities after it.
- The site keeps the reading from before the repair (1,603 English, 1,425 Hindi), which probably holds such passages
  too. The read-only SQL below (H1) counts them.

**Why it matters:**
- An English made from the editor's Hindi is not a translation of the Sanskrit.
- The editor's Hindi is a modern work (Śaivabhāratī Śodhapratiṣṭhāna, Varanasi), so an English of it, published as
  the text's translation, raises a question of his rights. It is the user's decision, as with the BORI e-text notice.

**Until H1 is decided:** do not press Finish EN or Add Hindi on the Kāraṇāgama.

**H1, the site's count** (Lovable Cloud SQL editor; read-only; one block). The rule is two or more Hindi-only words in
a passage. On the local copy it finds 349 of the 651 passages readiness calls Hindi, and 11 verses that carry a line
of Hindi. So read its count as at least half of the Hindi there.

```sql
-- H1 (16 Oct) READ-ONLY: the Karanagama on the site; the passages that read as the edition's Hindi.
WITH k AS (
  SELECT p.page_no, p.idx, p.translation,
         (position(' है' in p.text) > 0)::int + (position(' में' in p.text) > 0)::int
       + (position(' नहीं' in p.text) > 0)::int + (position(' और ' in p.text) > 0)::int
       + (position(' चाहिए' in p.text) > 0)::int + (position(' करना' in p.text) > 0)::int
       + (position(' होता' in p.text) > 0)::int + (position(' जाता' in p.text) > 0)::int
       + (position(' किया' in p.text) > 0)::int + (position(' भी ' in p.text) > 0)::int AS hindi_words
  FROM corpus.passages p
  WHERE p.doc_code = 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi'
    AND p.retired_at IS NULL)
SELECT count(*) AS passages,
       count(*) FILTER (WHERE coalesce(k.translation, '') <> '') AS with_english,
       count(*) FILTER (WHERE k.hindi_words >= 2) AS read_as_hindi,
       count(*) FILTER (WHERE k.hindi_words >= 2 AND coalesce(k.translation, '') <> '') AS hindi_with_english,
       (SELECT count(*) FROM corpus.translations t JOIN k k2 ON k2.page_no = t.page_no AND k2.idx = t.idx
         WHERE t.doc_code = 'Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi'
           AND t.lang = 'hi' AND t.retired_at IS NULL AND k2.hindi_words >= 2) AS hindi_with_hindi
FROM k;
```

**The options for H1** (a person decides; nothing is built yet):
1. **A guard in `translate_passages.py`:** skip a passage readiness calls the edition's Hindi, unless asked
   (`--include-edition-hindi`). This is the small, safe part.
2. **A text_type for an edition's own translation:** the reader folds it as "the editor's Hindi, not translated
   here"; the site's reader does the same after a mirror run.
3. **At the Kāraṇāgama's release:** its English-of-Hindi rows are left out, so the site's copy loses them.

## 5. Are we gaining anything? What our own rows say

**The flash judge** (judge-v1: no context, scores 1 to 5). On the Kāraṇāgama's 168 verses that have both Englishes:

| | Fidelity | Fluency |
|---|---|---|
| The scholarly English | 4.70 | 4.77 |
| The working English | 4.73 | 4.85 |

By fidelity, the scholarly English was better on 24 verses, the same on 124 and worse on 20. **This judge cannot tell
the two apart:** its scores sit near 5 for both.

**The second judge** (blind, pairwise, with the context; Gemini 2.5 Pro or Opus):

| Text | Verses | The scholarly English more faithful | As faithful | Less faithful |
|---|---|---|---|---|
| The Kāraṇāgama | 17 | 10 | 4 | 3 |
| MBh01 | 20 | 13 | 5 | 2 |

This favours the scholarly English, but on 37 verses only.

**The critic** accepted 1,936 of 2,435 first drafts (79%). It sent 499 back, 139 of them with a major issue.

**The price:**
- The scholarly English: about $0.046 a verse on claude-sonnet-5-5 (the Hayaśīrṣa $65.50 for 1,418; the Kāraṇāgama
  $46.95 for 1,018).
- The working English: $0.00247 a passage on gemini-2.5-flash, by the ledger of 15 Oct.
- So the scholarly English costs about 19 times as much.

**So: the gain is not yet shown on an objective measure.** The one test that discriminates favours it, on a small
sample. Two things follow:
- Measuring it (section 7) comes before spending the rest of the credit on new texts. The Tantrik Texts' 849 verses
  wait for it; their canary does not.
- The flash judge's scores alone do not decide pass or flag well. That is one reason for the 393 verses not passed:
  the triage and a person read them.

## 6. What exists already (read on 16 Oct)

| What | What it is | Use to us |
|---|---|---|
| **Mitrasaṃgraha** ([arXiv 2601.07314](https://arxiv.org/html/2601.07314v1), Jan 2026; Dharmamitra, UC Berkeley) | 391,548 Sanskrit–English pairs from existing human translations (40+ translators), six domains, about three millennia. Validation 5,587 and test 5,552 pairs, manually post-corrected. CC BY-NC-ND 4.0 for the whole; a research subset (372,791) CC BY-SA 4.0. The dataset and a fine-tuned checkpoint on GitHub (dharmamitra/mitrasamgraha-dataset) | **The external benchmark.** Its Table 3 (test set) gives chrF, BLEURT and GEMBA for Google Translate, GPT-4o, Claude 3.7 Sonnet, Gemini 2.0 Flash, the last two with retrieval, IndicTrans2, NLLB and fine-tuned open models |
| **MITRA** ([arXiv 2601.06400](https://arxiv.org/html/2601.06400v1)) | 1.74 million automatically aligned pairs (Sanskrit, Buddhist Chinese, Tibetan); Gemma 2 MITRA-MT (9B) for translation into English; open weights | Buddhist corpora: a model to compare, not our genre |
| **Itihāsa** ([ACL Anthology 2021.wat-1.22](https://aclanthology.org/2021.wat-1.22)) | 93,000 Rāmāyaṇa and Mahābhārata ślokas with English; "even state-of-the-art transformer architectures perform poorly" | The epics only |
| **IndicTrans2** ([AI4Bharat](https://github.com/AI4Bharat/IndicTrans2)) | All 22 scheduled languages, Sanskrit (san_Deva) among them; MIT licence; 1B and distilled models; IN22 benchmarks | Modern prose; a baseline for Sanskrit→Hindi and English→Indic |
| **Sarvam-Translate** ([Hugging Face](https://huggingface.co/sarvamai/sarvam-translate)) | Gemma-3-4B, 22 languages, document-level (8k tokens), GPL-3.0. [Sarvam's own post](https://www.sarvam.ai/blogs/sarvam-translate) lists Sanskrit among the lower-quality languages, with "occasional incomplete outputs" | A baseline for the Indic step |
| **Google Translate** | Sanskrit since May 2022, by zero-shot machine translation; [Google](https://blog.google/products/translate/24-new-languages/) says it "isn't perfect" | The floor |
| **PaliBench** ([arXiv 2605.16881](https://arxiv.org/html/2605.16881v1), May 2026) | A multi-reference Pāli→English benchmark (1,700 passages; three translators), with a reusable recipe; it names Sanskrit as a natural extension | How to build a multi-reference benchmark of our own |
| **Dharmamitra.org** ([Indology list, Aug 2024](https://list.indology.info/pipermail/indology/2024-August/059589.html)) | Sanskrit segmentation, lemmas, morphology (with Oliver Hellwig, on the DCS), and translation; API access offered | A grammar aid; a system to compare |

**What Mitrasaṃgraha's test set says** (Table 3; chrF / GEMBA):

| System | chrF | GEMBA |
|---|---|---|
| Google Translate | 28.28 | 56.09 |
| GPT-4o | 32.63 | 82.37 |
| Claude 3.7 Sonnet | 33.42 | 86.24 |
| Gemini 2.0 Flash | 34.24 | 87.04 |
| Claude 3.7 Sonnet with retrieval | 38.83 | 89.32 |
| Gemini 2.0 Flash with retrieval | 38.80 | 88.61 |
| Gemma 2 9B, fine-tuned | 38.36 | 83.34 |

The paper also finds:
- chrF and BLEU agree weakly with experts; BLEURT and GEMBA agree much better.
- Compounds, metaphor, philosophical terms and free word order stay hard.

Our pipeline is a form of retrieval (the context and the glossary), with a critic on top. **No public set covers the
Āgamas or the Pañcarātra:** Mitrasaṃgraha's scriptural domain has the Tantrāloka; Āgama texts are not mentioned. So:
- for Sanskrit→English in general, we measure ourselves against Mitrasaṃgraha;
- for our genre, we make our own gold set.

**The licences:**
- Mitrasaṃgraha (the whole) is non-commercial with no derivatives: we evaluate on it inside the automaton, never
  publish its references, and never train on them.
- Debroy's translation and Prof. Pandey's Hindi are in copyright.

## 7. The benchmark plan (BM)

| # | What | How | About |
|---|---|---|---|
| BM1 | **External:** 200 pairs of Mitrasaṃgraha's test set, by domain | Three Englishes of each: the scholarly pipeline (Sonnet), Sonnet's single pass (the working-English prompt, `anthropic:` engine), gemini-2.5-flash. Scored by chrF against the reference (free, computed here) and a GEMBA-style judge. Set beside Table 3, which is another sample and another judge, so it is a guide, not a ranking | $14 (scholarly $9.2, single pass $2, flash $0.5, judge $1.6) |
| BM2 | **Our gold set:** 60 verses (30 Hayaśīrṣa, 30 Kāraṇāgama), across the tiers | A person writes or corrects the reference English; chrF and the judge against it. It is the regression test for every later prompt or model | A person's time |
| BM3 | **Blind and pairwise, with the context:** 100 verses, the scholarly English against the working English | Judges Gemini 2.5 Pro and Opus (one of each family); the person picks on 30 (`scholar_duel.py`'s blind page) | About $10 |
| BM4 | **The person's review** of the triage CSVs | The accept and reject rate: the KPI | Time |

**The rule for spending after it:**
- The full pipeline (draft, critic, revisions, judge) goes on to new texts only if BM3 gives it 60% or more of the
  decided duels, and BM1 gives it no less than the single pass.
- Otherwise new texts go single pass, then the judge and the triage, at about a fifth of the cost.

**Before BM1 can be built:**
- The dataset's files must be seen (it is cloned by hand; section 9). Its fetch from here was not permitted, so its
  layout is not assumed.
- The harness must keep the benchmark out of the site's mirror and inside the credit ledger. A separate database would
  hide its spend from the credit gate.

## 8. Can this become the basis of better Indic translators?

**What carries over to Hindi and the other languages:** the method. It is language-agnostic:
- the verse with its context and the text's glossary;
- a critic who reads word by word, and revisions;
- a judge from another vendor;
- the triage, and a person's verdict;
- every row versioned, with its engine, prompt, judge and cost.

The Sanskrit→Hindi path exists already (`translate_passages.py --lang hi`, from the Sanskrit, with the English as
reference). What is per language: the prompts, the glossary's conventions, and a judge calibrated on a gold set in
that language.

**What we have that the public sets do not:** reviewed verse pairs in genres they lack (Āgama, Pañcarātra), each with
its notes, doubts, critiques and provenance. Once a person has read them, they are a gold set, and in time training
data whose rights are clear.

**What to watch:**
- Google Translate is the weakest system on Mitrasaṃgraha (GEMBA 56 against 82–89 for the LLMs). LLMs given context
  do best. So the gap is real, and context is what closes it; that is our approach.
- **Training on the models' outputs:** Anthropic's Commercial Terms bar using the services "to build a competing
  product or service, including to train competing AI models"; the Gemini API's Additional Terms (20 Nov 2025):
  "You may not use the Services to develop models that compete with the Services". Read them, and ask, before
  planning a fine-tune on their outputs.
- **Copyright:** not Debroy's or Pandey's work; not Mitrasaṃgraha's full set (no derivatives).
- **A fine-tune can reach the commercial level:** on Mitrasaṃgraha, a fine-tuned Gemma 2 9B came within half a chrF
  point of Claude 3.7 Sonnet with retrieval (38.36 against 38.83). An open model, fine-tuned on reviewed pairs whose
  rights are clear, is the long road to a Bhāratīya translator we own.

**The order:**
1. BM1–BM4.
2. Hindi from the scholarly English and the Sanskrit, with the same critic and judge, on a Hindi gold set; IndicTrans2
   and Sarvam-Translate as baselines.
3. Then the other languages, one at a time.

## 9. What the site shows (S4)

The scholarly English is not on the site. There are two ways:

**(a) A layer of its own (the end state):**
- a mirrored scholarly table (Lovable Cloud SQL: a `corpus` table and its RPC, as C4 did);
- `corpus_sync.py` sends it;
- Srangam's reader shows it above the working English, with its notes and its status.

**(b) Adopt:** the passed scholarly English is copied into the working English of a held text, logged and undoable,
and the mirror carries it as it is. It is faster, but it drops the notes and mixes the layers.

**(a) is recommended.** Its design comes next, after LIBRARY_SCHOLAR has been seen locally.

## 10. READY_PRICE_2026_10_16

**scholar_translate.py** (needs TRIAGE_2026_10_16):
- `readiness()`: `<sup>n</sup>` is not debris (15 Hayaśīrṣa verses).
- The edition's apparatus is still left out.

**redeem.py** (needs REDEEM_FIX_2026_10_14):
- The price of a passage of working English is measured on the rows since 15 Oct, when the thinking began to be
  counted: 100 passages or more (pro: 50); otherwise on all the rows, as before.
- Since 15 Oct, only Gemini's flash rows price flash, and its pro rows pro.
- The effect: the Library's "about $0.731" for the Hayaśīrṣa's 1,614 verses came from the rows before 15 Oct
  ($0.00045 a passage). At $0.00247 it is about $4.0, and the entities add about $0.0016 a passage. `python
  scripts\redeem.py` (free) writes the new estimates.

**A correction to docs/TRIAGE_2026-10-16.md:**
- A working-English call cost $0.00247 (808 output tokens) on 15 Oct, not $0.0052 (1,910). The $0.0052 and the 1,910
  were the retried calls' figures in docs/COST_TRUTH_2026-10-15.md.
- An entities call reads about 8 passages: $0.0016 a passage.
- Corrected there and in `gemini_thinking_probe.py`'s docstring.

**Tests:** `tests/test_ready_price_2026_10_16.py` (5). The replay chains of `test_triage_2026_10_16` and
`test_provisional_2026_10_14` now end at the `.bak_readyprice_` copies.

## 11. Checks

- **The sandbox:** 373 tests of the scholarly, dashboard and redeem families OK.
- **The whole suite:** 682 passed; the 36 failures are the same environment ones as before.
- **The device:** the hashes after each patch are in the RUNBOOK's steps.
