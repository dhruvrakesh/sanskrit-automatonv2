# Is it done in full? The state on the morning of 19 Oct, and two faults found and mended

Markers: **LEAK_GUARD_2026_10_19** and **KEEP_ON_EMPTY_2026_10_19** (scripts/text_filters.py,
scripts/translate_passages.py, scripts/infer_mt.py, by scripts/patch_leak_guard_2026_10_19.py),
**HEAL_ENGLISH_2026_10_19** (scripts/heal_english.py) and **DOCS77_2026_10_19** (scripts/patch_docs77_2026_10_19.py).
It follows docs/SCHOLAR_READER_2026-10-18.md (`cf5217fa`; Srangam `beedafe5`).

## 1. What is done, read from the PC, the mirror's log and the two repos (11:05 IST, 19 Oct)

| Asked | State | The evidence |
|---|---|---|
| The scholarly English in the mirror | Done | corpus_sync.py SCHOLAR_MIRROR; the mirror grew from 189,705 to 197,632 rows: the GRETIL Markandeya's 5,240 passages, 2,686 scholarly rows (its 1,408 verses, MBh01's 24, the Tantrabhidhana's 16) and its title; 10:46 IST: 380 groups equal, 0 different |
| The site's reader functions (C18) | Pasted 18 Oct, 20:30 IST ("Query succeeded") | the checks' P1 and V1 after it are still to read |
| The reader shows it | Pushed (Srangam `beedafe5`) | /corpus/markandeya_purana__w_gretil?at=627.1 (adhyaya 81), ?at=81.3 (adhyaya 19) |
| The editions | Two on /editions | the Devimahatmya (669: 632 passed, 37 flagged); adhyayas 19 to 31 (739: 659 passed, 76 flagged, 4 doubted) |
| The top bars | Done | the dashboard's six menus; Srangam's "Editions" |
| The Devimahatmya in full | Done | adhyayas 81 to 93, every passage, in the edition and in the reader |
| The Markandeya Purana in full | No | 1,408 of the GRETIL text's 5,240 passages have a scholarly English (adhyayas 19 to 31 and 81 to 93) |
| The Surya Siddhanta | 422 of 515 | 337 passed, 84 flagged, 1 doubted; $20.36 for 402; it stopped at its cap at 25.3. Left: 88 verses (pages 25 to 28, and 18 on pages 3 to 8) and 5 headings |
| The Ganita Yukti Bhasa | Working English mended; no scholarly English | 1,793 judged; 45 marked (40 blame the Sanskrit) |
| The mending (T2) | 289 marked on 18 Oct, 149 (3%) now | Markandeya 24, Sandilya 17, Ganita 45, Mallapurana 45, Bodhicaryavatara 15, Satapatha 3 |

**The money.** The Claude credit: $185.84 of its $190 cap spent, **$4.16 left** (to 11 Nov). The Google cap: $75.31 of
$85, **$9.69 left**. The last 88 verses of the Surya cost about $4.45 on Sonnet (more than is left) or about $1.45 on
Gemini 2.5 Pro (judged by Gemini Flash: scholar_translate.py refuses a Claude judge for a Gemini run, CLAUDE_FIRST_2026_10_15;
corrected on 21 Oct, DOCS78_2026_10_21). The Ganita's scholarly English (about 1,800
verses) costs about $30 on Gemini 2.5 Pro and more on Sonnet: neither budget holds it now.

## 2. Fault 1: the model's words inside a translation (LEAK_GUARD_2026_10_19)

Seen in judge_review.py's list (markandeya 94.8: "Let me give a cleaner rendering:"). Searched in all 41,932 stored
translations: 14, every one read by eye.
- **A preamble** over the translation: nirukta 178.3, yajur 38.5, 191.3, 267.1, smriti_06 63.1 ("Here is the
  translation of the verse, adhering to your specified principles:"); Mallapurana 81.5 and Natyasastra 263.1 (a
  preamble over "[ILLEGIBLE]": nothing was translated); Satapatha 187.2's Hindi (a preamble over the Sanskrit).
- **A second version after the first:** markandeya 94.8, Mallapurana 112.4 ("Final rendering:"), Ganita 229.12
  ("Correction to the above").
- **The model reasoning aloud:** harita_dvitiya 14.1, harita_tritiya 66.1, nilamata 18.12's Hindi.
- **Not faults:** "let me be suffering", "according to the rules", "Certainly, O son", "I will provide you assistance"
  are the Sanskrit's own words (the guard leaves them; tests/test_leak_guard_2026_10_19.py holds them).
- **The scholarly English:** none (its answers are JSON, read field by field).

**The guard.** text_filters.model_chatter() names the model's words; strip_model_chatter() keeps the translation (the
version after the last "... rendering:" line, without a leading preamble or a "Note: the text reads ..." line).
translate_passages.py passes every answer through it before the existing filters; what still talks to us is kept as
nothing. infer_mt.py never caches it, so a retry asks again.

## 3. Fault 2: a re-translation that came back empty wiped the English (KEEP_ON_EMPTY_2026_10_19)

translate_passages.py --retranslate archived the old English only when the new one was not empty, and then wrote the
new one all the same: an empty answer (a refusal, an echo) emptied the passage with nothing in translation_history.
T2 did this four times: Mallapurana 11.9 (14 Oct), Mallapurana 11.5, markandeya_purana 28.2 and Ganita 217.6 (18 Oct);
their old English survives in data/retranslate/*.jsonl and in mt_cache. Now an empty attempt keeps the English a
passage has; only English that is itself the model's words is let go, archived first. The Hindi was never wiped (its
write is skipped when empty).

## 4. The mending (heal_english.py)

Through translate_passages.py, which archives what it replaces; never by hand. The plan (free) lists what it finds and
what each will hold. `--yes` reads each answer back from mt_cache with the engine that made it (free): the four lost
English come back; the preambles and first versions go; the reasoning is archived and emptied. `--yes --fresh` then
asks Sonnet for a fresh translation of what was emptied (five passages, a few cents). The next mirror run sends it all.

## 5. Tests

tests/test_leak_guard_2026_10_19.py (9: the 14 cases and the Sanskrit's own words; the write path on a temp database
with the echo engine and mt_cache: an empty attempt keeps the English, a preamble goes and the old answer is archived,
reasoning is archived and emptied, Hindi too; nothing of it cached; the patcher's replay),
tests/test_heal_english_2026_10_19.py (3: the plan writes nothing; --yes mends each; --fresh). The replay chains of
test_claude_first_2026_10_15 and test_scholar_2026_10_14 follow `.bak_leakguard_`.

## 6. Still to decide (yours)

1. The Surya's last 88 verses: Gemini 2.5 Pro with the Gemini Flash judge now (about $1.45 Google), or Sonnet when there
   is credit again (about $4.45). (21 Oct, DOCS78_2026_10_21: a Claude judge for a Gemini run is refused by
   scholar_translate.py; 70 of them were done on Sonnet that day, docs/SHELF_AND_SURYA_2026-10-21.md.)
2. The Ganita's scholarly English: raise the Google cap (scripts\set_budget.py), or wait for credit.
3. The Hayasirsa (held in repair; 236 of its scholarly verses flagged or doubted and unread) and the Karanagama
   (withdrawn).
4. Gemini writes Sanskrit terms in `backticks` (1,687 passages): the reader shows the marks. Shown as italics in the
   reader, or left as they are.
