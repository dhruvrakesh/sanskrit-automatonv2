# BM3: the blind side-by-side of BM1's English (16 Oct 2026)

- **BENCH_DUEL_2026_10_16:** `scripts/bench_duel.py` (new), `tests/test_bench_duel_2026_10_16.py` (7 tests); on the
  dashboard by `scripts/patch_bench_duel_desk_2026_10_16.py` (`scripts/dashboard.py`, `scripts/dashboard_static.html`,
  `docs/BENCH_MITRA_2026-10-16.md`), `tests/test_bench_duel_desk_2026_10_16.py` (8 tests). The replay chain of
  `test_bench_desk_2026_10_16` follows to `.bak_benchduel_`.
- BM1's results: docs/BM1_RESULTS_2026-10-16.md.

## 1. Why

BM1 scored each arm alone. chrF measures nearness to the published 19th-century English, not fidelity; judge-v1 gave
every arm 4.7 to 4.9 of 5 and passed 92 to 95% of their sentences, so it barely tells them apart; it is
gemini-2.5-flash judging, among others, gemini-2.5-flash's English; and the scholarly arm was revised against it. The
two measures order the arms differently. BM3 asks the question the house cares about, in its own terms: of the same
sentence, which English is the more faithful, read side by side.

## 2. How

- **The units:** BM1's 190 (a sentence the scholarly arm translated whole over several verses is one unit for every
  arm), from BM1's folder, read only.
- **The translations:** the three arms' English (flash, sonnet1, scholar); with `--with-reference` (the dashboard's
  buttons always), the published English as a fourth. The scholarly arm's notes are shown as its notes; the others
  have none.
- **The judges and the prompt: scholar_duel.py's duel-v1, unchanged.** gemini-2.5-pro and Claude Opus 5.5, one of each
  family. The system prompt asks for "an unabridged translation made from a critical edition, as Bibek Debroy's
  Mahabharata is from the BORI Critical Edition: every word rendered and nothing added". Each judge gives every
  translation fidelity, prose and notes (1 to 5) and its errors (major or minor), then a ranking and the best.
- **Blind:** who made each translation is not said; the order is shuffled for each unit and each judge (seeded). The
  verse comes with its context as the pipeline reads it (6 verses before, 2 after), in Sanskrit only: no arm's English.
  The glossary the scholarly runs grew is not shown (it would carry one arm's spellings).
- **The order of reading:** fixed (seed BM3-2026-10-16): the eight texts in turn, each text's units shuffled. A run
  stopped anywhere (`--units N`, `--max-usd`) has read a balanced random part; the next run goes on. A unit a judge has
  read on the same English is never asked again.

## 3. What is reported

For all eight texts, without the Bhagavata, and text by text (`BM3_report.html`, private; `BM3_summary.json`,
numbers only):
- **Each judge apart:** for each pair of arms, the share of units where the first is ranked above the second (a tie,
  "equal", counts a half), weighted by verses, with a 95% bootstrap interval (1,000 resamples); each arm's fidelity,
  prose and notes, major and minor errors per ten verses, how often it is ranked first; how often the first
  translation shown is ranked first, against chance (the order's effect).
- **Both judges:** how often they order a pair alike; the pair's share where they agree (a tie where they do not);
  and, for a pair of two families (flash against a Sonnet arm), how often they split by family: each ranking its own
  family's English above the other's.
- **How to read it:** a share above 0.50 means the first is preferred; it is in bold when its interval leaves out
  0.50. gemini-2.5-pro may favour the flash arm, Claude Opus the Sonnet arms. "scholar above sonnet1" read by
  gemini-2.5-pro is the cleanest comparison (neither is its family): it asks whether the pipeline does better than the
  same model alone. A pair the two judges order alike, against their families' pull, is the firmest.

## 4. The money and the licence

- Every call is metered into BM3's own ledger copy (`bm3\db\D.db`: the Claude credit's rows and the spend cap, pulled
  from `data/context.db`), checked before each call against the credit, the cap and `--max-usd`, and settled into
  `data/context.db` every 10 calls and at the end: `usage_log` as kind `bench_duel`, doc `BM3:<text>`; the Gemini part
  in the spend cap. A step refuses up front when its part does not fit.
- The price of a reading, until BM3 has 10 of its own: scholar_duel's duel calls of 15 Oct, on longer passages, so an
  upper estimate: about $0.065 (gemini-2.5-pro, its thinking included) and $0.047 (Claude Opus).
- **The pilot, the first 40 units:** 80 readings, about $4.48 ($2.60 Google, $1.88 Claude), at most $5.87. All 190: 380
  readings, about $21 at those prices ($12.4 Google, $8.9 Claude); BM3's own price, measured in the pilot, will say more.
  The spend cap had about $7.2 left after BM1's judge: the pilot fits; the rest needs the cap raised, a decision of
  yours (`python scripts\set_budget.py`).
- The published English goes to both judges' APIs (Google's and Anthropic's) as a translation to judge: a private
  evaluation, as BM1's `--judge-reference`. Nothing of the dataset is committed, published or put on the site; BM3's
  folder (`D:\Sanksrit Automatons\benchmarks\bm3`) is outside every repository, and the script refuses one inside.

## 5. The commands (PowerShell, from `D:\Sanksrit Automatons\sanskrit-automatonv2`)

```
python scripts\bench_duel.py --units 40 --with-reference
python scripts\bench_duel.py --units 40 --with-reference --yes --max-usd 6.00
python scripts\bench_duel.py --report
Start-Process "D:\Sanksrit Automatons\benchmarks\bm3\BM3_report.html"
python scripts\bench_duel.py --settle
```

Or the Benchmarks page: BM3's section shows what each judge has read, the next part with its price (the pilot, then
40 units more a press), and its buttons; a button is not offered when the spend cap cannot hold its Google part.

## 6. After BM3

- **BM2:** a person's blind reading of the same units (Translation 1, 2, 3, 4; the names under a fold), which decides
  where the judges disagree. It needs a page for picking, on the dashboard, next.
- **J2:** a judge told the translator's emendations (with the thinking off), after the baseline, as agreed.
