# The English already paid for: what was measured, what was not, and how it is redeemed (17 Oct 2026, night)

Marker: **JUDGE_SCREEN_2026_10_17**, in `scripts/judge_sample.py` and `scripts/retranslate_marked.py` (patched by
`scripts/patch_judge_screen_2026_10_17.py`). Also **TEST_ISOLATION_2026_10_17** (`tests/test_bench_desk_2026_10_16.py`)
and **DOCS72_2026_10_17**. It follows TIER_R_2026_10_17 (`c83cb23`), docs/NEXT_BOOKS_2026-10-17.md.

## 1. The question

Asked on 17 Oct: "Has the existing translation corpus, on which we have spent substantially, been properly analysed
and redeemed? It used Gemini flash, and that too performed reasonably well. Are you sure this is the enterprise way?"

The plan of the evening (docs/NEXT_BOOKS_2026-10-17.md, section 1) proposed the Markandeya scan's 1,219 verses "every
verse again" by Sonnet. That is a replacement, not a redemption. This note corrects it.

## 2. What was measured (read on 17 Oct from data/redeem.json, data/text_path.json, data/retranslate/ and the 14 Oct backup)

**The reading the English was made from: measured on all of it.** REDEEM_2026_10_14's ledger (counted again on 16 Oct,
11:06):
- 26,589 English in 56 texts; **22,371 (84%) were made from a clean reading** and are kept; 4,192 were made from
  misread Sanskrit and are made again after their scan's repair (the reading is what costs, not the translation).
- $37.90 was spent on the translation in all; $7.70 of it on English that cannot be kept as it is.
- The verdicts: redeemed 20, mostly redeemed 8, to translate again 24, not redeemable as it is 2, replaced 1,
  withdrawn 1. "Redeemed" means made from a clean reading with no more than a tenth judged wrong; it does not mean
  every verse was read.

**The meaning: measured on 0.9%.** `mt_reviews` holds 240 verdicts, all by the flash judge (judge-v1), 27 Aug to 12 Oct;
mean fidelity 4.32 of 5; 34 at 2 or less.

| Text | English | Judged | Wrong in meaning (fidelity 2 or less) |
|---|---|---|---|
| MBh01 | 6,957 | 31 | 0 |
| Natyasastra | 2,901 | 0 | - |
| Tantric Texts | 2,824 | 0 | - |
| Ganita Yukti Bhasa | 2,374 | 0 | - (a Tesseract reading; repair first) |
| Shatapatha Brahmana | 2,230 | 45 | 3 |
| Nirukta | 2,031 | 0 | - (repair first) |
| Nilamata | 1,380 | 0 | - (a better source first) |
| Markandeya Purana | 1,219 | 37 | 2 |
| Mallapurana | 992 | 39 | 5 |
| Bodhicaryavatara | 824 | 40 | 15 (withdrawn from the site) |
| Sandilya | 451 | 36 | 1 |
| the other 45 texts | 2,406 | 0 | - |

- In the five judged texts on the site: **11 wrong of 188 (5.9%)**; of the ledger's 26 wrong, **18 are blamed by the
  judge on the Sanskrit** (garbled, misread aksharas), not on the translation.
- **The reader (BM2, 24 units, blind) marked no flash English wrong**; Sonnet in one pass was the reader's best in 50%,
  flash in 19%, the published English in 19%. Flash did reasonably well, as you say.
- **A 1% sample estimates a rate; it does not find the verses.** The Markandeya's verse with the invented gloss (page 4,
  passage 8) was not among the judge's 38; it was found by a person, on the site.

**What was redeemed: once, 18 passages.** T2_2026_10_14 (14 Oct) translated again with gemini-2.5-pro what the judge
had marked: 7 mended, 9 not, 2 unchanged or failed. About half of the 9 name the Sanskrit itself (garbled, a typo, a
misread word): a better engine does not mend a misread verse.

## 3. What it costs now

Since COST_TRUTH_2026_10_15 counts the thinking Google bills as output:

| Step | Engine | $ a verse, as measured | Paid from |
|---|---|---|---|
| The working English | gemini-2.5-flash | 0.00247 (1,917 calls, 15 Oct) | the spend cap |
| The working English (Tier R) | claude-sonnet-5-5, one pass | 0.0052 (BM1, 199 calls) | the Claude credit |
| A verdict (judge-v1) | gemini-2.5-flash | 0.00274 (2,079 calls, 15 Oct) | the spend cap |
| A verdict (judge-v1) | claude-haiku-5-5 | 0.000247 (74 calls, 15 Oct) | the Claude credit |
| An audit | claude-opus-5-5 | about 0.047 | the Claude credit |

- **Every kept verse read by the flash judge: about $60** on a cap with $11.04 left (17 Oct). Not possible.
- **The same read by Haiku: about $4.30** for the seven texts below, on a credit with $66.22 left that ends on 11 Nov.
- Flash, its thinking billed, costs about half of Sonnet's one pass: it is no longer the bargain it seemed.

## 4. The enterprise way: keep, measure every verse, fix only what fails, a person on what the machines dispute

1. **Keep.** No English is replaced wholesale because a better engine exists. Every re-translation keeps the English
   before in `translation_history`, as now.
2. **The judge is of the other family:** Claude's English is judged by Gemini (decided 15 Oct); Gemini's English by
   Claude. Haiku reads the flash corpus; flash keeps reading the scholarly English.
3. **Calibrate the instrument before measuring with it.** Haiku reads again the ~240 passages flash read (about $0.06).
   Where the two disagree, Opus reads them as referee (about $0.05 each). **Haiku becomes the screen when it finds at
   least two thirds of what flash marked, or when Opus sides with Haiku at least as often as with flash where they
   disagree.** Otherwise it is not the screen, and section 6 has the alternatives. This rule is set before the run.
4. **Screen every clean verse of the texts on the site**, once (`--skip-judged --clean-only`): MBh01, the Natyasastra,
   the Tantric Texts, the Shatapatha, the Markandeya, the Mallapurana, Sandilya: 17,386 English kept, about 17,200 not
   yet read; about $4.30. A judge is a screen, not a verdict: on BM2 the judges also called "major" 18 to 22 of the 94
   translations the reader did not mark. A false alarm costs one re-translation and nothing is lost; a miss is the
   risk. So the screen is tuned for what it finds, and its alarms are mended, not believed.
5. **Fix what is marked, by its cause:**
   - the judge blames the translation: `retranslate_marked.py` with Sonnet (Tier R's engine) and Haiku's re-judge;
     about $0.0055 a verse on the credit, and the Hindi of a mended verse again by flash ($0.0025 on the cap), or later
     with `--no-hindi`;
   - the judge blames the Sanskrit, or the Devanagari carries debris: the source first (the repair, or a critical
     e-text: GRETIL's Markandeya covers our adhyayas 1 to 15; `benchmark_sources.py --reference gretil` measures our
     reading against it, free).
6. **A person reads what is not mended** (`judge_review.py`), and a sample of what passed, as BM2 did.
7. **A whole text again only by measure:** when its screen marks a fifth or more of its verses (the Mallapurana's
   sample: 15%), or when its Sanskrit changes (a repair, a re-ingest). The threshold is yours to set.
8. **The ledger says it:** `redeem.py` counts again; `text_path.py` charts it; the judged share becomes all of it.

At the rate of the judged sample (6%), the screen would mark about 1,000 verses: perhaps half for the translation (about
$3 by Sonnet), half for the Sanskrit (the source path).

## 5. JUDGE_SCREEN_2026_10_17 (what is built)

- **`judge_sample.py`:**
  - `--engine anthropic:<model>`: the same judge-v1 (its prompt, its reading of the answer), by Claude, asked once more
    with twice the room when cut off (as `scholar_translate.py`'s ClaudeCheck.judge), metered on the Claude credit
    (usage_log, kind judge) and stopped by it;
  - `--skip-judged` (leave out a passage with a verdict newer than its English), `--clean-only` (leave out a passage
    whose Sanskrit carries Latin letters), `--only-ids FILE`, `--max-usd`;
  - `--calibrate`: reads again the passages another judge read, on the English it read; writes
    `data/retranslate/judge_screen/calibrate_<model>.jsonl` (a dated copy beside it) and `calibrate_<model>_disagree.jsonl`
    (kept local, as the T2 logs: data/retranslate/ is in .gitignore);
    **nothing in mt_reviews**. With a calibration's file as `--only-ids`, a third judge (the referee) says whom it
    sides with;
  - the dry run prices a verdict as measured (usage_log's own rows since 15 Oct, the thinking counted), says what it
    leaves out and why, and shows the credit; `--report` adds a line by judge once there is more than one.
  - A run as before (flash, no new option) runs exactly as before.
- **`retranslate_marked.py`:** `--engine` and `--judge-engine` may be Claude's (priced by their own rows in usage_log,
  else by the model's prices on BM1's one pass; stopped when the credit is); a run in which nothing bills Google (both
  Claude's, with `--no-hindi`) is not stopped by the spend cap; the dry run's NEXT carries the options it was given
  (before, it dropped them, and the NEXT would have run gemini-2.5-pro).
- **One verdict a passage** (judge-v1), as before: the screen's verdict replaces an older one; `--skip-judged` keeps
  flash's 240 where they stand, and the calibration's files keep both readings.

**Tests:** `tests/test_judge_screen_2026_10_17.py` (13): the dry run's filters and price; a Claude screen writes its
verdicts under its judge and meters on the credit; the cap and the credit stop it; the calibration and the referee;
nothing to calibrate on; the measured price; ClaudeJudge with a stand-in SDK (its prompt, the second ask, the meter);
retranslate_marked's Claude judge, prices, gates and NEXT; the patcher replayed on its backups.
`tests/test_redeem_2026_10_14.py` and `tests/test_meter_gates_2026_10_04.py` pass unchanged.

**TEST_ISOLATION_2026_10_17:** `tests/test_bench_desk_2026_10_16.py` failed on your PC on 17 Oct ("The last report"
found: the real BM2 report, made that day, was read by the test's page) and erred (WinError 32: the ledger still open
when its temp folder was removed). Its TheDesk now points BM2 and BM3 at its own temp folders and lets a connection
close before the folder goes. Test-only.

## 6. If Haiku is not the screen

- Sonnet as the screen on the texts most read (about $0.005 a verse: some $85 for all seven; a text at a time).
- The flash judge on a larger sample (10% of the seven, about $4.80 on the cap): rates by text, not the verses.
- A person's reading of a stratified sample per text (BM2's desk), the gold.

## 7. Not decided here (yours)

Haiku as the screen (after the calibration); the threshold for a whole text again; the Hindi of mended verses now or
later; GRETIL's licence (CC BY-NC-SA 4.0) for the Devimahatmya on the site; raising either cap.
