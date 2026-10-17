# SOP: how a text of the corpus is translated (17 Oct 2026; a draft until BM2 is read)

**Status: a draft.** Its grounds are BM1 (docs/BM1_RESULTS_2026-10-16.md), BM3's pilot (docs/BM3_PILOT_2026-10-16.md)
and BM3's check (docs/BM3_CHECK_2026-10-17.md). BM2, a person's blind reading (docs/BENCH_GOLD_2026-10-16.md), has not
begun: until it is read, every judgement below is a machine's, and section 3 is a proposal, not a rule. I am Claude,
and two of the arms measured are Claude's: the judging was blind and one judge was Gemini's; a person decides.

The desk that carries this SOP on the dashboard: docs/TRANSLATION_DESK_2026-10-17.md (`/desk`, TRANSLATION_DESK_2026_10_17).

## 0. The principles

1. **The source first.** No English is made from a reading that is to be replaced. The path chart
   (`scripts/text_path.py`, free) says, per text, whether the reading is ready; the register
   (`data/source_verdicts.jsonl`) says whether the text is withdrawn, set aside or in repair.
2. **One method per tier, its flags fixed and measured.** A method changes one variable at a time, against the
   baseline (judge-v1, gemini-2.5-flash, unchanged until the baseline is settled; J2 after it).
3. **A dry run before every paid step; a cap on every press.** Every paid command prints its price first and stops
   at its `--max-usd`.
4. **Say what is shown.** On the site, a passage whose English was made from a misread reading carries a
   "provisional English" chip (PROVISIONAL_EN_2026_10_14); the rest of the working English carries no tier label yet
   (D5 in docs/TRANSLATION_DESK_2026-10-17.md). The scholarly English is not on the site until its layer (S4) exists.
5. **A person accepts.** A machine's pass is not an acceptance: a person reads the flagged verses and accepts or
   rejects (section 5).

## 1. The gate (every text, before any translation)

| The register | The path (text_path.py) | The desk's stage | What may run |
|---|---|---|---|
| withdrawn, set aside | any | the reading first | nothing (translate_passages.py holds it, HOLD_2026_10_14; the desk refuses, 409) |
| in repair | in_repair | ready or the reading first | the scholarly English with `--held-ok` only; the working English as the path says |
| - | repair, use_repair, ingest, source, retire | the reading first | the path's first step (the Repair page, `/repair/<doc>`) |
| - | translate (its first step a translation) | ready | Tier W, or Tier S |
| - | translate (its first step a re-ingest or the like) | the reading first | that first step, then chart again |
| - | judge, retranslate | translated: to judge | the judge's sample; the marked passages again (`/redeem`) |
| - | done | done | nothing, or Tier S where an edition is wanted |

- **Chart again** (`python scripts\text_path.py`, or "Chart the path again (free)" on `/desk`) after every OCR, vision
  repair, re-ingest or change of the register. The chart of today was made on 14 Oct (2026-10-14T22:18:42).
- **The guard (TRANSLATION_DESK_2026_10_17):** the dashboard's Translate and Start buttons, `/api/translate` and
  `/api/pipeline/translate-doc` hold a text whose path says the reading comes first, with the path's reason and next
  step (409, `needs_force`). The person may go on: the button asks, and sends `force` only on a yes.
- **What the chart of 14 Oct says** (73 texts): repair 34 (vision about $24.41, $15.01 to $39.22; then about
  $71.16 to translate them), translate 17 (about $7.67), done 9, source 7, ingest 3, in repair 2 (about $4.10),
  retranslate 1 (about $0.01). Its prices: vision $0.00404 a page (the corpus price), a passage $0.000604 (the usage
  log). Estimates, not bills.
- **Example (16 Oct):** the Padma Purana's Patala Khanda (SP_4214) was started from the dashboard on its Tesseract
  reading. Its path: repair (debris moderate, 1.56% of letters misread; vision has read none of its 364 pages); next
  `python scripts\repair_text.py --doc SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press --repair --max-usd 1.90`,
  then `python scripts\reingest_pages.py --doc SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press`
  (the plan, free). The guard now holds such a start.

## 2. Tier W: the working English (and its Hindi)

- **What:** `translate_passages.py`, the engine `MT_ENGINE` (gemini-2.5-flash), one pass, the context window,
  `--min-quality 0.35`; the edition's own Hindi kept out (CLASSIFY_HINDI_2026_10_16). The Library's Finish EN, then
  Add Hindi; or, on a ready text's desk page, "Translate the rest (working English)".
- **What it is:** a draft. BM3's check: 3.8 to 4.5 major errors in ten verses (the most of our arms); ranked first in
  12% of units by both judges. BM1: judge-v1 passes 95% of it, so judge-v1's pass is not a measure of a draft's
  errors.
- **Price:** about $0.005 a verse on BM1's verses; the corpus price $0.0006 a passage (the path chart). On the
  Google spend cap.
- **After it:** the judge's sample (the path's judge step); the marked passages again (`/redeem`); the mirror sends
  it to the site (the provisional chip where its reading was misread).

## 3. Tier R: a better working English (a proposal; your decision, after BM2)

- **What:** the same `translate_passages.py` with the engine given per job: `anthropic:claude-sonnet-5-5`
  (CLAUDE_FIRST_2026_10_15). `MT_ENGINE` stays `gemini:gemini-2.5-flash` (Ask and extract_entities call Gemini
  directly; it must not be set to an `anthropic:` engine).
- **Why it is proposed:** BM3 (pilot and check): Sonnet in one pass above flash 0.68 to 0.86, with 0.7 to 1.9 major
  errors in ten verses against flash's 3.8 to 4.5, for about the same price ($0.0052 a verse against $0.0051, BM1).
  BM1's chrF puts it nearest the published English.
- **Why not yet:** BM2 has not been read; it would bill the Claude credit (it ends on 11 Nov), not the Google cap;
  two of the judges' families are at stake (section 0). The dashboard does not offer it yet (D4 in
  docs/TRANSLATION_DESK_2026-10-17.md); by hand, a job at a time:
  `POST /api/pipeline/translate-doc {"doc": ..., "engine": "anthropic:claude-sonnet-5-5"}`.

## 4. Tier S: the scholarly edition

- **What:** `scholar_translate.py` with the flags of 15 Oct that BM1 and BM3 measured (bench_mitra.SCHOLAR_FLAGS;
  translation_desk.SCHOLAR_SOP): `--engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5
  --audit-every 10 --no-compare`. Sonnet drafts and criticises, Opus audits one sentence in ten, judge-v1 reads every
  sentence. A glossary that grows, at most three notes a verse, the critic's revisions, the source's doubts.
- **When:** a text with a clean reading (ready, done, or an e-text witness) that is to be an edition: where its notes
  are wanted. Not a text the register withdraws or sets aside; a text in repair with `--held-ok` only.
- **How (the desk, `/desk/<doc>`):** Plan (the dry run, free) prints the verses ready and the price; Run sends the
  NEXT line's own cap. At most 400 verses and $12 a press. By hand: the plan prints its NEXT line, e.g.
  `python scripts\scholar_translate.py --doc ... --limit 40 <the flags> --yes --max-usd ...`.
- **What it is, measured:** above Sonnet alone 0.79 to 0.80 with its notes shown, 0.51 to 0.52 without them (a coin
  toss): its value, to the judges, is its notes, and fewer major errors by gemini-2.5-pro (0.24 against 1.90; Opus
  counts them equal). Above flash 0.70 to 0.89. On clean e-texts; on OCR the critic and the source's doubts may matter
  more (not measured).
- **Price:** about $0.043 a verse (BM1: $8.02 Claude, $0.50 Google for 200 verses).
- **After it:** Triage (free; `exports\scholar_triage_<doc>.csv`), the report (free; `exports\scholar_<doc>.html`),
  the prose (`/scholar/<doc>/prose`), then section 5.

## 5. Review and acceptance (a person)

- Read the flagged and doubted verses first (Triage), then a sample of the passed.
- Accept or reject: `python scripts\scholar_translate.py --doc ... --review 1.1.8,1.1.9 --verdict accept --by Dhruv`
  (`--verdict reject`, `--note ...`). A glossary entry: `--term ... --rendering ... --kind ...` (a person's entries
  win over the model's).
- BM2 calibrates the judges: how often each judge's best is the reader's, how many of the wrong it catches. Until it
  is read, a judge's pass is a screen, not a verdict.

## 6. Publishing

- The working English: the mirror (`corpus_sync.py`, Srangam's `corpus-ingest`); the provisional chip where the
  reading was misread.
- The scholarly English: not on the site. S4 (a) is the plan: a layer of its own, mirrored, with its notes and its
  status (docs/LIBRARY_SCHOLAR_2026-10-16.md section 9; D5 in docs/TRANSLATION_DESK_2026-10-17.md).
- Never on the site: the benchmarks' outputs (the Mitrasamgraha dataset is for private evaluation only), a withdrawn
  text, a beneficiary's details.

## 7. Money

- The Google spend cap ($70; about $3.5 left on 16 Oct, an estimate): vision, the working English, judge-v1, BM3's
  Gemini judge. `python scripts\set_budget.py` (it shows the cap, the spend and the headroom; read only without
  `--cap`) is the truth where it differs.
- The Claude credit ($190; about $66 left on 16 Oct; it ends on 11 Nov): the scholarly English, Tier R if adopted, BM3's
  Opus judge. `python scripts\claude_engine.py --credit` (free, read only) is the truth. At the measured prices, $66 is about 1,500 verses of Tier S or about 12,000 of Tier R (arithmetic, not
  a plan).
- The source-first queue (34 repairs, about $24 of vision on the Google cap) does not fit in what is left of the cap:
  a decision of yours (D6).

## 8. Benchmarks as the regression test

- A change of engine, prompt or flags in a tier: BM1's subset again (chrF and judge-v1), then BM3 on the pilot's 40
  units (both judges, with and without the notes), before the change goes to the corpus.
- BM2: a person's reading, the gold against which the judges are measured; 40 units first.
- judge-v1 unchanged until the baseline is settled ("let us not change too many variables"); J2 after it.

## 9. What this SOP does not decide

Tier R; S4's design; raising either cap; the order of the source-first queue; the Karanagama's path. Each is yours.


## Addendum (17 Oct, evening): BM2's first reading (DOCS70_2026_10_17)

docs/BM2_FIRST_READING_2026-10-17.md. A person read 24 units blind: Sonnet in one pass was the best in 50% (by verses),
flash 19%, the published English 19%, the scholarly English read without its notes 8%.
- **Tier R is recommended** for the working English, a job at a time (the engine `anthropic:claude-sonnet-5-5` given to
  the job; `MT_ENGINE` unchanged): the reader, both judges of BM3 and BM1's chrF agree, at flash's price. Your
  decision; I am Claude, and the arm is Claude's.
- **Tier S is read with its notes.** Its English without them is the reader's least preferred: it puts its
  explanations in the notes. The scholarly edition (SCHOLAR_EDITION_2026_10_17) prints them; a short gloss inline is
  one variable to measure before it is changed.
- **The judges are a screen, not a verdict:** their best was this reader's at or near chance.
- **"Done" is not "correct":** a flash verse of the Markandeya Purana with an invented gloss passed with a QA of 1.0;
  the Ganita Yukti Bhasa, "complete" in the register, is a Tesseract reading with 474 [ILLEGIBLE] passages in its
  English. A book is made from a clean reading (the gate, section 1) and read by a person (section 5).


## Addendum (17 Oct, late): the English already made (DOCS72_2026_10_17)

docs/JUDGE_SCREEN_2026-10-17.md. Tier R is for English not yet made, or a text measured to need it; English already
made is kept, read by a judge of the other family, and fixed where it is marked, by its cause. "Every verse again" is
for a text whose screen marks a fifth or more of its verses (your threshold to set), or whose Sanskrit changed.
