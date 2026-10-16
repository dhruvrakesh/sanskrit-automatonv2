# BM1: our English against published translations, and a printed ornament (16 Oct 2026)

- **BENCH_MITRA_2026_10_16:** `scripts/bench_mitra.py` (new), `tests/test_bench_mitra_2026_10_16.py` (12 tests).
- **ORNAMENT_2026_10_16:** `scripts/scholar_translate.py` and `scripts/redeem.py`, patched by
  `scripts/patch_ornament_2026_10_16.py`; `tests/test_ornament_2026_10_16.py` (4 tests). Srangam:
  `scripts/patch_srangam_ornament_2026_10_16.py` with `docs/srangam/ORNAMENT_2026-10-16/` (corpusDisplay.ts,
  reader-ornament.test.tsx with 4 tests, RELIABILITY_AUDIT Phase AI).
- Replay chains: `test_ready_price_2026_10_16` (redeem.py) and `test_classify_hindi_2026_10_16`
  (scholar_translate.py) follow to `.bak_ornament_`.

## 1. What was asked

"Benchmark against existing solutions"; then, on the judge, "let us not change too many variables and establish a
worthy baseline"; BM1 on the eight Hindu-tradition files only, with the side-by-side: "OK".

So BM1 measures the pipeline **as it is today** and changes nothing in it: the same prompts, the same engines, the
same judge (judge-v1, gemini-2.5-flash with its thinking), the same flags as the 15 Oct scholarly runs.

## 2. What BM1 is

**The verses.** The Mitrasamgraha test set (cloned by hand to `D:\Sanksrit Automatons\benchmarks\mitrasamgraha-dataset`),
eight files of the Hindu traditions: the Kathasaritsagara, the Bhagavata Purana, the Skanda Purana, the Manusmrti,
the Yogavasistha, the Rgveda, the Satapatha Brahmana and the Ramayana. Not the Gita (GE07bhg: a sectarian
translation) and not the three Buddhist files (GK19asvbh, K10vimkn_u, T04tat). From each file, a window of 25 lines
in a row, chosen by a fixed seed (`BM1-2026-10-16`) among the windows whose every line converts cleanly and would be
sent by both translating scripts; with the 6 lines before and the 2 after, as the context the pipeline reads. 200
verses in all. The IAST is written in Devanagari by the project's own transliterator (`iast_utils`,
indic-transliteration 2.3.55), as passages are stored: ISO 15919's r with a ring below and m with a dot above are
read as IAST's; the Vedic consonant ळ (written ḷ before a vowel) is not taken for the vowel ऌ.

**The arms.**

| Arm | What it is | How it is run |
|---|---|---|
| flash | gemini-2.5-flash, one pass: the working English | `translate_passages.py --engine gemini:gemini-2.5-flash` |
| sonnet1 | Claude Sonnet 5.5, one pass, the same prompt: the model without the pipeline | `translate_passages.py --engine anthropic:claude-sonnet-5-5` |
| scholar | the scholarly pipeline, as the 15 Oct runs of the Hayasirsa and the Karanagama (read from their logs) | `scholar_translate.py --engine anthropic:claude-sonnet-5-5 --compare-engine anthropic:claude-opus-5-5 --audit-every 10 --no-compare` |

The scholarly arm: Sonnet drafts and criticises, up to 2 revisions, a sentence over several verses translated
whole, the glossary growing from the verses that pass; Opus audits about one sentence in ten; judge-v1 reads every
sentence. The two one-pass arms see the five verses before (their own English) as production does.

**The scores.**
- **chrF** against the published English, as the dataset's paper scores (sacrebleu's chrF2: characters 1 to 6,
  whitespace removed; the implementation here matches sacrebleu 2.6.0 to six places). Also **folded chrF**: the
  diacritics and the case folded, so that Tawney's "Sataváhana" and our "Sātavāhana" meet. The house's emphasis
  (`*term*`) and verse-end marks (`//`) are removed first, for every arm.
- **judge-v1** on the Sanskrit alone, unchanged, on every arm's English; with `--judge-reference` on the published
  English too, not told what it is: a calibration of the judge against the translators of record.
- **Units:** a sentence the scholarly arm translated whole over several verses is one unit for every arm (the
  one-pass arms' verses joined), so every comparison is paired.
- **Intervals:** paired bootstrap over the units (1,000 resamples, a fixed seed): a difference whose 95% interval
  holds nought is not shown to be more than chance.
- **Scopes:** all eight; without the Bhagavata (see 4); all eight without the units whose published English seems a
  neighbour's (see 4); each text.
- **The judge read twice:** the pipeline's own judge-v1 read each scholarly sentence when it was made; the scoring
  step reads it again. How often the two agree is the judge's own noise, reported.

## 3. The licence, and the site

The dataset is for **private evaluation** here: never trained on, never published, never put on the site.
- Everything made of it (the sample, the bench databases, the English, the judgements, the report) stays in
  `D:\Sanksrit Automatons\benchmarks\bm1`, outside every repository; the script refuses an `--out` inside one.
  `BM1_summary.json` holds numbers only (no Sanskrit, no English), so it can be quoted.
- The published English is never sent to a translator. With `--judge-reference`, judge-v1 (Google's API) reads it as
  a translation to score: a private evaluation, opt-in.
- The site mirror (`corpus_sync.py`) and publish_srangam read `data/context.db`; the bench databases are other files,
  so nothing of BM1 can reach the site or the dashboard's Library.

## 4. What to bear in mind when reading it

- **The references are not one standard.** Tawney, Tagare, Buhler, Mitra, Griffith (the catalogue says Oldenberg; the
  lines read as Griffith's), Eggeling, Dutt. They are 19th-century or older-style English, some free, some
  interpretive. chrF rewards nearness to *that* English, not fidelity to the Sanskrit; the judge reads fidelity.
- **The Bhagavata's reference is devotional and interpretive** (it reads as the Bhaktivedanta Book Trust's: "back
  home, back to Godhead"), and its Sanskrit, like the Rgveda's, is split word by word. Every summary is given with it
  and without it.
- **The Ramayana file jumps between passages**, so a window may cross a seam; the context then misleads every arm.
- **Some pairs are shifted.** In the Satapatha's window (from line 155) the published English of a line is often the
  translation of the line before it (line 156's English renders line 155's "atha rcam anucya rca yajati"). The report
  marks a unit whose published English fits the arms' English better at a neighbouring line (by 10 chrF points or
  more, on the average of the arms: the same test for every arm), counts them, and gives a scope without them
  ("aligned"). The judge, which reads the Sanskrit alone, is not touched by it.
- **The Rgveda's Sanskrit is the dataset's word-split form**, with its own slips ("suvrkt i bhih" for suvrktibhih)
  and its own spellings (the particle u before iti written "om iti", which the transliterator writes as the sign
  om). It is given to every arm as the dataset has it: BM1 measures our pipeline on the dataset's Sanskrit, not a
  mended one.
- **25 verses a text is small**: the per-text intervals are wide; the 200 together decide.
- **The paper's numbers are a frame, not a target:** Mitrasamgraha's paper reports chrF on its whole test set
  (Google Translate 28.28; GPT-4o 32.63; Claude 3.7 Sonnet 33.42; Gemini 2.0 Flash 34.24; with retrieval 38.8;
  a fine-tuned Gemma 2 9B 38.36). BM1 is 200 of those verses, in our pipeline's own form; it is not their benchmark run.

## 5. The money

Every call is metered as the pipeline meters it, into the bench database of its arm, whose ledger is a copy of the
real one (the Claude credit's rows since 15 Oct and the spend cap), so the scripts' own caps hold as in a real run.
After each text, the step writes those calls into `data/context.db`: `usage_log` as kind `bench_<kind>` (bench_translation,
bench_scholar, bench_judge), doc `BM1:<text>`; `usage_totals`; and, for a Gemini call, the spend cap's `spent_usd`, as
`cost_tracker` writes them. So the Claude credit and the spend cap count BM1; the prices the Library measures (kinds
translation, scholar, judge) do not. A call is never written twice (the bench database marks it settled); a step
stopped half way is settled by the next one, or by `--settle`.

The estimate on 16 Oct (the dry run measures it again from `data/context.db`):

| Step | Verses or calls | About | Paid from |
|---|---|---|---|
| flash | 200 | $0.49 | Google (spend cap) |
| sonnet1 | 200 | $2.40 (a guess: no Sonnet one-pass rows yet) | the Claude credit |
| scholar | 200 | $8.76 ($8.22 Claude, $0.54 the judge) | both |
| score (with the reference) | up to 800 | $2.20 | Google |
| **in all** | | **about $13.9: $10.6 Claude, $3.2 Google** | |

The spend cap had $5.61 left on the 16 Oct morning backup; BM1's Google part fits, with little to spare for other
runs. Each step refuses up front when its part does not fit (the credit, the cap, or `--max-usd`), and stops between
texts when `--max-usd` is reached.

## 6. The commands (PowerShell, from `D:\Sanksrit Automatons\sanskrit-automatonv2`)

```
python scripts\bench_mitra.py --sample
python scripts\bench_mitra.py
python scripts\bench_mitra.py --arm flash --yes --max-usd 0.75
python scripts\bench_mitra.py --arm sonnet1 --yes --max-usd 4.00
python scripts\bench_mitra.py --arm scholar --yes --max-usd 11.00
python scripts\bench_mitra.py --score --judge-reference
python scripts\bench_mitra.py --score --judge-reference --yes --max-usd 2.75
python scripts\bench_mitra.py --report
Start-Process "D:\Sanksrit Automatons\benchmarks\bm1\BM1_report.html"   # BENCH_DESK_2026_10_16 (or the Benchmarks page)
```

- `--files GSD36manu,GV01rvh` runs some texts only (a canary, or the scholarly arm in parts).
- The three arms can run at once in three windows (each has its own bench database; each settles per text).
- The scholarly arm prints `scholar_translate.py`'s own NEXT lines: ignore them; the harness prints its own.
- The judge waits until every arm has English for every text: the scholarly arm's sentences decide the units.

## 7. ORNAMENT_2026_10_16: a printed ornament is not the scanner's debris

Lovable found, on 16 Oct, clean verses labelled "provisional English" on the site. gemini-2.5-flash vision writes an
ornamental rule of the printed page as a line of its own, `<decorative line>`; the reader hides it and draws a rule,
but the debris test (two Latin letters in a row) read the marker's words as debris. The automaton made the same
mistake: `scholar_translate.readiness` left such a verse out as "OCR debris", and `redeem.py` counted its English as
made from a misread reading. In `data/context.db` (the 16 Oct, 07:51 backup) three verses carry the marker on a
line of its own and are otherwise clean: the Markandeya Purana 1.4 and 1.6, and the Tantric Texts series 135.1.

- The automaton: a line that is exactly the marker is set aside before the debris test (`ORNAMENT`, in both
  scripts). The verse is still sent as stored. The marker inside a line of text, and any other Latin word, is
  debris as before. `repair_text.py` and `translate_passages.py` count debris over a whole text (a share): three
  lines do not move it; they are unchanged.
- Srangam: `madeFromMisread()` sets aside the same lines (the reader's own `splitDecoration`), so the reader's test
  and the automaton's stay one rule (RELIABILITY_AUDIT invariants 51 and 56). No database change; Lovable's
  "Try to fix" is not needed.

BM1's verses carry no ornament, so this changes nothing in the benchmark.

## 8. After BM1

- **BM3:** the blind side-by-side of the arms, by judges of both families (scholar_duel.py's way), once BM1's numbers
  are read; its Google part needs room under the spend cap.
- **BM2:** a gold set of our own, read by a person: it decides where the references and the judge disagree.
- **J2:** a judge told the translator's emendations (with the thinking off) comes after the baseline, as asked.
