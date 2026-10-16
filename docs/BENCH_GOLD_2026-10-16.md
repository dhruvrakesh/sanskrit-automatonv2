# BM2: your blind reading, the gold the judges are measured against (16 Oct 2026)

- **BENCH_GOLD_2026_10_16:** `scripts/bench_gold.py` (new), `tests/test_bench_gold_2026_10_16.py` (5 tests); on the
  dashboard by `scripts/patch_bench_gold_desk_2026_10_16.py` (`scripts/dashboard.py`),
  `tests/test_bench_gold_desk_2026_10_16.py` (6 tests). The replay chain of `test_bench_duel_desk_2026_10_16` follows to
  `.bak_benchgold_`.
- BM1: docs/BENCH_MITRA_2026-10-16.md and docs/BM1_RESULTS_2026-10-16.md. BM3: docs/BENCH_DUEL_2026-10-16.md.
  BM3's pilot: docs/BM3_PILOT_2026-10-16.md.
- The same patch shows BM3's check on the Benchmarks page (BENCH_DUEL_NOTES_2026_10_16, `scripts/patch_bench_duel_notes_2026_10_16.py`,
  `tests/test_bench_duel_notes_2026_10_16.py`, 3 tests): the pilot's units again, the scholarly arm's notes withheld.

## 1. Why

BM1's two measures disagree (chrF puts Sonnet in one pass first; judge-v1 puts the scholarly pipeline and flash
first) and both have known blind spots. BM3's two judges read the arms side by side, but they are machines, each may
favour its own family, and both may miss the same thing. A person who reads the Sanskrit decides where they disagree
and shows whether either can be trusted where they agree.

## 2. What the reader sees (the dashboard, /benchmarks/bm2)

- BM3's units in BM3's order of reading, so the units both judges have read come first.
- The unit's Sanskrit in Devanagari and IAST; the verses before (3) and after (2), Sanskrit only, folded.
- Four translations as **Translation 1 to 4**: the three arms' English and the published English, in an order
  shuffled for each unit (seed BM2-2026-10-16, not the judges' orders). Nothing says who made which; the scholarly
  arm's notes are kept back (they would name it).
- The reader picks the best (or "they are equally good"), may mark any translation **wrong in meaning**, and may add
  a note. Keys: 1 to 4 pick, E says equal, Enter saves.
- Then, and only then: who made each translation, the scholarly arm's notes, and what each BM3 judge chose and where
  it found a major error. "Next unit" goes on.
- The reader's name is kept in this browser only (local storage); it labels the picks.
- Free: nothing is called and nothing is paid. The page reads BM1's bench databases and BM3's readings, read only.

## 3. What is stored

`D:\Sanksrit Automatons\benchmarks\bm2\person.jsonl`, append-only, outside every repository: the unit, the reader,
the order shown, the best, the translations marked wrong, the note, the English's fingerprints (a pick is refused
when the unit's English has changed since the page was made), the time. A reader's latest pick of a unit counts.

## 4. What is reported (Make the report, free)

`BM2_report.html` (private: the dataset's text and the reader's notes) and `BM2_summary.json` (numbers only), for all
eight texts and without the Bhagavata, per reader:
- how often each arm is the reader's best (weighted by verses, "equal" apart), and how often it is marked wrong in
  meaning, per ten verses;
- for each pair of arms, of the units where the reader chose one of the two, the share for the first, with a 95%
  bootstrap interval;
- **each judge against the reader:** how often its best is the reader's best (with the chance level, one in five);
  of the translations the reader marked wrong in meaning, how many the judge gave a major error; of the others, how
  many it gave one anyway (its false alarms).

## 5. How many to read

Each unit takes a minute or two. The 40 units of BM3's pilot (both judges read them) are the first 40; reading them
gives each judge's agreement with you on the same units. 80 units (two sittings) narrow the intervals; all 190 are the
full gold set.

## 6. The commands (PowerShell, from `D:\Sanksrit Automatons\sanskrit-automatonv2`)

```
Start-Process "http://127.0.0.1:5057/benchmarks/bm2"
python scripts\bench_gold.py
python scripts\bench_gold.py --report
Start-Process "D:\Sanksrit Automatons\benchmarks\bm2\BM2_report.html"
```
