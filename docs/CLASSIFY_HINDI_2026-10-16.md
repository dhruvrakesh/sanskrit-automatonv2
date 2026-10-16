# An edition's own Hindi, kept out of the translation; the serious flags, read; the benchmark's make-up (16 Oct)

Markers:
- **CLASSIFY_HINDI_2026_10_16:**
  - `scripts/edition_hindi.py`, `scripts/classify_hindi.py`;
  - `scripts/classify_doc.py`, `scripts/scholar_translate.py` and `scripts/dashboard.py`, patched by
    `scripts/patch_classify_hindi_2026_10_16.py`;
  - for Srangam, `scripts/patch_srangam_frontmatter_2026_10_16.py` (its payload: `docs/srangam/FRONTMATTER_FOLD_2026-10-16/`).
- **DOCS64_2026_10_16:** `scripts/patch_docs64_2026_10_16.py`.

**Sources:**
- the daily backup `D:\backups\context_daily.db` (22:31 UTC, 15 Oct), read with `mode=ro&immutable=1`;
- the triage CSVs of 16 Oct (`exports\scholar_triage_*.csv`);
- the H1 count on the site (Lovable Cloud SQL editor, 16 Oct);
- `D:\Sanksrit Automatons\benchmarks\mitrasamgraha-dataset` (its `final_catalog.tsv` and `data\test\`);
- the thinking probe of 16 Oct.

## 1. The question

Asked on 16 Oct: "why do we not get our own scholarly English and Hindi translations directly from the Sanskrit
source? I thought our automaton was separating contextual Sanskrit text for translation at the ingestion stage
itself."

**It was meant to.** `classify_doc.py` is the stage the dashboard runs after every ingest, and after every repair and
re-ingest. It sorts a text into:
- `mula`, the Sanskrit to translate;
- `frontmatter`, "genuine English/Hindi body text and front matter";
- `noise`.

**But its `frontmatter` stage, `classify_frontmatter.py`, recognises English only:** at least 85% Latin letters.
An edition's own Hindi is Devanagari, as the Sanskrit is, so it stayed `mula`. The working English translated it.

**The scholarly English has its own check:** three words of a short Hindi list. It caught 651 of the Kāraṇāgama's
Hindi passages, and missed 99, which claude-sonnet-5-5 then translated: $3.75 of the credit. The flash judge
passed 89 of those 99, because the English was faithful to what it was given.

The translators themselves do read the Sanskrit:
- the working Hindi is made from the Sanskrit, with the English only as a reference;
- the scholarly English is made from the Sanskrit, with its context and glossary.

The fault is the sorting before them.

## 2. What was found (15 Oct backup; the passages not already noise or front matter)

| Text | Read as Hindi | With working English made from it | With scholarly English made from it |
|---|---|---|---|
| The Kāraṇāgama (Prof. Rama Chandra Pandey's Hindi under each verse, his preface) | 815 | 194 | 99 |
| The AkashBhairavaKalpam (its Hindi introduction) | 107 | 0 | 0 |
| The Daivat-Sanhita (its Hindi introduction) | 17 | 0 | 0 |
| The Ṛgveda-saṃhitā vol. ii (Hindi notes to the variants) | 10 | 0 | 0 |
| The Yoga-vāsiṣṭha (Lala Baijnath's Hindi; withdrawn on 14 Oct for this reason) | 8,485 | 0 | 0 |
| siddhanta_shiromani, Bodhicaryavatara (garbled OCR) | 3, 1 | 0 | 0 |
| The Hayaśīrṣa Pañcarātra, MBh01, the Tantrik Texts vol. I | **0** | | |

**The site's copy of the Kāraṇāgama** (the reading from before the repair; the H1 count of 16 Oct):
- 2,084 passages, 1,603 of them with English;
- 333 passages read as Hindi;
- 291 of those carry English, and 132 a Hindi row.

## 3. The rule (`scripts/edition_hindi.py`)

A passage reads as Hindi when all of these hold:
- it has six Devanagari words or more;
- it has no OCR debris: fewer than two Latin words, once a scan's watermark line ("Digitized by eGangotri",
  "Jangamwadi Math Collection") is taken out;
- it has two different Hindi words or more, at least one of them from STRONG, the words Sanskrit does not have (hai,
  mein, nahin, chahie, karna, kiya, aur, se ...). WEAK holds the Hindi words that are Sanskrit forms too (ka, ke, ko,
  par, dvara, kare, hota, gaya, jata, jate, bhi): they count, but cannot decide alone;
- the Hindi words (with Hindi's plural oblique -on and its subjunctive -aen) are 12% of the words or more, and more
  than the Sanskrit marks (a visarga, a word ending in a virama).

**How it was checked:**
- On the whole corpus it finds nothing in the Sanskrit-only texts.
- The garbled readings it took at first are left out by the STRONG word and the debris test: Vedic -on forms, a
  Mallapurāṇa compound, garbled Padma Purāṇa lines, and the Tantrik Texts' index entries ("subhadra-i6", "-ka").
- Each of the Kāraṇāgama's lowest-scoring detections, read, is Hindi.

## 4. CLASSIFY_HINDI_2026_10_16

**`scripts/classify_hindi.py`:**
- It tags such passages `frontmatter`, the label `classify_doc.py` already gives an edition's own body text. Every
  translator, the QA, the exports, the embeddings and the Library already leave that label out.
- **By default** (the stage): only passages that carry no English are tagged.
- **`--with-english`:** a passage that carries English is tagged too, because that English was made from the Hindi.
  - Its English is archived (`translation_history`, reason "edition-hindi CLASSIFY_HINDI_2026_10_16") and cleared.
  - Its search row is made again without the English, and its vector is removed.
- **`--reject-scholarly --by Dhruv`:** the latest scholarly row of each such passage gets a person's verdict
  "reject", with the note "the passage is the edition's own Hindi, not Sanskrit".
- **`translations_l10n` is never touched:** its rows are counted and reported.
- **`--undo --apply`** puts back the types, the English and the verdicts.
- Everything is logged to `data\classify_hindi_log.jsonl`. It is a dry run by default.

**`classify_doc.py`:** a new stage after `classify_frontmatter.py`. A freshly ingested, repaired or re-ingested text
arrives sorted.

**`scholar_translate.py`:**
- Its readiness reads Hindi with the new rule as well as the old one.
- `--status` counts no row on a passage typed noise or front matter, and adds a "set aside: N" line; `--triage` lists
  none.

**`dashboard.py`:**
- The Library's scholarly count sets such rows aside and says so: "N set aside (not Sanskrit verse ...)".
- The reader shows no scholarly English on them, and does not offer to translate them: "the edition's own matter".

**Srangam (`patch_srangam_frontmatter_2026_10_16.py`):**
- The corpus reader folds a passage typed `frontmatter` like scanner noise: "The edition's own matter, not the
  Sanskrit." with "Show it".
- It never says "Not translated yet." of it, and its note says what it is.
- The public reader never receives such passages: `publish_srangam.py` leaves out noise and front matter.
- Phase AH of `docs/RELIABILITY_AUDIT.md`, invariants 54–55.

**The Kāraṇāgama on the site:** its 291 English-of-Hindi rows stay until a mirror run carries a new reading of the
text. There are two ways (a person decides):
1. Withdraw it now, as the Yoga-vāsiṣṭha was on 14 Oct (`repair_text.py --withdraw`): the mirror retires its
   passages until it is restored and released.
2. Keep it until its release, when the reading from after the repair, tagged, replaces it.

## 5. Our own English and Hindi, from the Sanskrit only

| Layer | From | State |
|---|---|---|
| The working English (`passages.translation`) | the Sanskrit, a passage at a time (gemini-2.5-flash) | Right once a text is sorted: the guard is the sorting |
| The working Hindi (`translations_l10n`) | the Sanskrit, with the English as a reference | The same |
| The scholarly English (`scholar_translations`) | the Sanskrit, with its context, the glossary, a critic and a judge | The 99 rows made from Hindi are rejected by `--reject-scholarly` |
| **A scholarly Hindi** | the Sanskrit, with the passed scholarly English as a reference, the same critic and judge in Hindi | **Not built.** Devanagari takes several times the tokens of English. A 20-verse canary measures its price before any text, after the benchmarks (BM) |

## 6. The serious flags, read

The triage of 16 Oct lists 85 serious for the Hayaśīrṣa and 62 for the Kāraṇāgama. Each was sorted by what its
doubts and its passage show, and a sample was read by hand.

| Why it is serious | The Hayaśīrṣa | The Kāraṇāgama |
|---|---|---|
| The printed or OCR Sanskrit is corrupt; the translator emended it and said so in its doubts; the judge, who reads the corrupt Sanskrit without the doubts, marks it down | 66 | 35 |
| The editor's footnotes (the Vedic sources of mantras, "(śu. ya. 16.2)") cut as a verse | 1 | 8 |
| The edition's Hindi in the passage (CLASSIFY_HINDI) | 0 | 7 |
| A mantra kept in IAST, as rule 13 asks; the judge counts it untranslated | 0 | 3 |
| Other (to read) | 18 | 9 |

**So another model would mostly re-emend the same corrupt readings.** That is the Opus pass ($4.72 and $3.44 by its
dry runs). What would help instead:
1. **CLASSIFY_HINDI**, which removes the Hindi.
2. **A judge that is told the emendations** (judge-v2): the translator's doubts beside the Sanskrit. With the
   thinking off, as measured below, all 2,436 verses cost about $0.25 to judge.
3. **A person** who reads the source tier and the emendations (accept or reject), and a better edition for the
   corrupt verses (the source desk).

The Opus pass waits until these are done.

## 7. The thinking probe (TB1)

Twelve Hayaśīrṣa verses, judged twice (judge-v1):

| | Cost | Thinking tokens a call |
|---|---|---|
| With gemini-2.5-flash's thinking | $0.0447 | 1,421 |
| With thinkingBudget 0 | $0.0020 | 0 |

**The result:** without the thinking, the judge costs 4% of what it costs with it.
- The fidelity score was the same in 9 of 12 verses and within one point in 11.
- Pass or flag was the same in 11.

**The installed SDK** (google-generativeai 0.8.5) cannot set a thinking budget. The change goes through the REST call
the probe uses, or the newer SDK.

**Proposed:** a 60-verse probe first, then judge-v2 with the thinking off.

## 8. Mitrasaṃgraha: what it is made of

**From its `final_catalog.tsv` and its test files** (cloned on 16 Oct). The English is that of the translations
already published, chiefly:
- Ganguly (the Mahābhārata);
- Wilson (the Viṣṇu Purāṇa, the Sāṃkhyakārikā);
- Bühler (Manu, Āpastamba, Gautama);
- Griffith, Oldenberg and Keith (the Vedas);
- Eggeling (the Śatapatha);
- Jha (the Tantravārttika, the Bhāmatī, the Chāndogya bhāṣya, the Tattvasaṅgraha);
- Tagare (the Skanda Purāṇa);
- Singh (the Tantrāloka);
- Tawney (the Kathāsaritsāgara).

**The training texts:** 50 are listed, with 393,189 pairs. 44,128 of them (11%) are Buddhist:
- the Tattvasaṅgraha and its Pañjikā;
- the Yogācāra works;
- the Abhidharmakośa;
- the Jātakamālā, the Dhammapada and the Arthaviniścaya.

The rest are the Veda, the Itihāsa, the Purāṇas, Dharmaśāstra, Kāvya, Śāstra and the darśanas (Nyāya, Mīmāṃsā,
Sāṃkhya, Vedānta, Kashmir Śaiva).

**The test set:** 12 files, 5,552 pairs:

| Files | Pairs | What |
|---|---|---|
| 8 | 4,000 | The Ṛgveda, the Śatapatha, Manu, the Bhāgavata, the Skanda, the Yogavāsiṣṭha, the Kathāsaritsāgara, an Itihāsa extract (500 each) |
| 1 | 220 | The Gītā |
| 3 | 1,332 | Buddhist: the Buddhacarita (344), the Vimalakīrtinirdeśa (488), the Tattvasaṅgraha (500) |

**The Sanskrit is given in IAST, its words split** ("adṛṣṭa pūrvam hṛṣitaḥ asmi"), not as printed.

**What it is not:** a tract against Sanātana Dharma.
- It is a corpus of existing translations of classical works, mostly of the Hindu tradition.
- The Tattvasaṅgraha argues against Nyāya, Mīmāṃsā and the Veda's authority because that is what the text, a
  Buddhist śāstra of the 8th century, does. The Nyāyamañjarī and the Tantravārttika in the same corpus argue against
  the Buddhists.

**What it does carry:**
1. **The references' readings:** 19th- and early 20th-century English, and some colonial framing. The Gītā test's
   English is sectarian Vaiṣṇava ("the Personality of Godhead").
2. **A metric that rewards resembling them:** chrF and BLEU. The paper itself finds that they agree weakly with
   experts.
3. **A form unlike ours:** IAST with its words split, against our Devanagari with sandhi.

**So BM1, if it is run:**
- It uses the 8 files of the Hindu tradition only; the Gītā and the 3 Buddhist files are left out.
- It is scored by the judge, who reads the Sanskrit and not the reference, with chrF beside it, file by file.
- It is a yardstick only: never training, never the site, never published. That is its licence too (non-commercial;
  no derivatives).

**The decision is ours either way:**
- **BM2,** our own gold set of Āgama verses read by a person (you, or a Sanskritist you choose), is the measure that
  decides.
- **BM3,** blind and pairwise, with the context, is the second.

## 9. Tests

- **`tests/test_classify_hindi_2026_10_16.py` (8):**
  - the reading (Hindi; Sanskrit, with words that are both; an index; debris; a watermark);
  - the dry run and the safe default;
  - `--with-english`, `--reject-scholarly` and `--undo`: the archive, the search row, the vector, l10n untouched;
  - readiness, `--status` and `--triage`;
  - the Library's count and the reader;
  - the stage;
  - the patcher's replay.
- **The replay chains:** `test_library_scholar_2026_10_16` and `test_ready_price_2026_10_16` now end at the
  `.bak_hindi_` copies.
- **The whole sandbox suite:** 690 passed; the 36 failures are the same environment ones as before.
- **Srangam:** `src/__tests__/reader-frontmatter.test.tsx` (2) and the reader-provisional tests (4) passed under
  vitest 4.1.6, and PassageBlock.tsx typechecks, both in a sandbox with the reader's own files. Run the full suite in
  the repo before pushing.
