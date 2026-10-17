# BM2's first reading: 24 units read blind by a person (17 Oct 2026)

The method: docs/BENCH_GOLD_2026-10-16.md. Read by: dhruvr, on the dashboard's /benchmarks/bm2, 17 Oct 05:24 to 11:38
UTC: 24 units (26 verses), three of each of the eight texts, in BM3's order. The numbers below were made from copies
of `D:\Sanksrit Automatons\benchmarks\bm2\person.jsonl`, BM1's databases and BM3's readings (read only, in a scratch
folder, not in the benchmarks' folders); `python scripts\bench_gold.py --report` makes the same report there (free).
I am Claude, and two of the arms are Claude's (sonnet1, scholar): the reading was blind, and the reader decides.

## 1. What the reader chose

| | The reader's best (weighted by verses) | Units | Marked wrong in meaning |
|---|---|---|---|
| sonnet1 (Claude Sonnet 5.5, one pass, the working prompt) | **50%** | 11 | 0 |
| flash (gemini-2.5-flash, one pass: the working English) | 19% | 5 | 0 |
| the published English | 19% | 5 | 2 (0.8 a ten verses) |
| scholar (the scholarly pipeline, its notes withheld) | 8% | 2 | 0 |
| "they are equally good" | 4% | 1 | |

The pairs (of the units where the reader chose one of the two; 95% bootstrap intervals):
- sonnet1 over flash 0.72 [0.50, 0.91] (16 units); sonnet1 over the published 0.72 [0.50, 0.90] (16);
- **scholar over sonnet1 0.13 [0.00, 0.33] (13 units)**; scholar over flash 0.29 [0.00, 0.57] (7);
- flash over the published 0.50 [0.20, 0.80] (10).
Without the Bhagavata (21 units): sonnet1 43%, flash 24%, the published 19%, scholar 10%.

## 2. The judges against the reader

- **As BM2's report had it (the judges of BM3's pilot, who were shown the scholarly notes):** the judge's best was the
  reader's best in 0.08 of the units (Claude Opus) and 0.12 (gemini-2.5-pro); chance is 0.20. Both judges chose the
  scholarly arm in 18 and 19 of the 24 units; the reader in 2.
- **That comparison was not like for like:** the reader reads without the notes (they would name the arm). BM3's check
  read the same units with the notes withheld. Against those readings (22 of the 24 units; counted by units, not
  verses): gemini-2.5-pro's best was the reader's in 7 (0.32), Claude Opus's in 5 (0.23); each judge then chose
  scholar in 10 and sonnet1 in 9 to 11. BENCH_GOLD_FAIR_2026_10_17 puts this second comparison in the report.
- **Errors:** the reader marked 2 translations wrong in meaning, both the published English; the judge caught one of
  the two. Of the 94 translations the reader did not mark, the judges found a "major" error in 18 (Opus) and 22
  (gemini-2.5-pro).

## 3. What it shows, and what it does not

- **The reader prefers Sonnet in one pass, plainly**, over the working English (flash) and over the scholarly English
  read without its notes. Three measures now agree on Sonnet in one pass against flash: BM1's chrF, both judges of
  BM3, and the reader.
- **The scholarly English read without its notes is the reader's least preferred.** It is not the critic's
  revisions: in 17 of the 24 units the scholarly English was the first draft, unrevised (BM1's S.db: one pass), and
  the reader chose another arm in 15 of them. It is the register: over BM1's 200 verses the scholarly arm puts its
  explanations in the notes (0.01 parentheses a verse, against sonnet1's 0.67 and flash's 0.47) and keeps fewer
  Sanskrit words (0.9 a verse, against 1.2 and 1.25); sonnet1 is longer (37 words a verse, against 34 and 32). Without the
  notes, sonnet1's English explains itself and the scholarly English does not. BM3's check found the same from the
  judges' side: the scholarly arm's lead was its notes.
- **The machine judges do not stand in for this reader's preference** (at or near chance with the notes withheld);
  they remain a screen for errors of meaning, whose "major" errors the reader did not confirm in 18 to 22 of 94.
- **Limits:** one reader; 24 units; about a minute a unit (the median between picks); a preference, which weighs
  readability, more than a search for errors. The intervals are wide. The 16 units of the 40 that both judges read
  are not yet read.

## 4. What follows (decisions yours)

- **The working English:** Sonnet in one pass (Tier R of the SOP) is the reader's choice and the judges' and chrF's,
  at the price of flash (about $0.005 a verse, BM1), on the Claude credit (about $66 left on 16 Oct; it ends on
  11 Nov). The SOP's addendum (DOCS70_2026_10_17) records it as recommended, a job at a time; `MT_ENGINE` stays
  gemini-2.5-flash.
- **The scholarly edition** is read with its notes (the scholarly edition's HTML, SCHOLAR_EDITION_2026_10_17, prints
  them as each chapter's notes). Whether its English should carry a short gloss inline as well is one variable to
  measure (the 40 pilot units again: about $2 of the scholarly pipeline and $3 of judges), not to change unmeasured.
- **BM2:** read the remaining 16 of the 40 units the judges read; then the report again (free).
