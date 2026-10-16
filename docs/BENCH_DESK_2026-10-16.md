# The dashboard shows BM1, the Claude credit and each text's state (16 Oct 2026)

- **BENCH_DESK_2026_10_16:** `scripts/dashboard.py`, `scripts/dashboard_static.html`, `scripts/bench_mitra.py` and
  `docs/BENCH_MITRA_2026-10-16.md`, patched by `scripts/patch_bench_desk_2026_10_16.py`;
  `tests/test_bench_desk_2026_10_16.py` (9 tests).
- Replay chains: `test_classify_hindi_2026_10_16` (dashboard.py) and `test_judge_desk_2026_10_11`
  (dashboard_static.html) follow to `.bak_benchdesk_`.
- No database change. Nothing reaches the site.

## 1. What was asked

"UI/UX on the dashboard here needs to reflect the latest state and intuitive wiring."

## 2. What the dashboard did not show (16 Oct, before this)

- **BM1 at all.** Its spend appeared among the last calls as `bench_translation BM1:Rgveda`, nothing more; the
  steps had to be typed in PowerShell, and the report opened by hand (the `start ""` line it printed is cmd's and
  fails in PowerShell).
- **The Claude credit.** The Usage tab's "Spent, all time" was the spend cap's count (Google only), beside an engine
  table holding Claude's spend: two bills read as one.
- **A text's register state** (withdrawn from the site, set aside, in repair) and **its scholarly English**, on the
  main table's rows: they were on the Sources and Library pages only.

## 3. What it shows now

**The Benchmarks page** (a link in the header) opens with BM1:
- the caps: the Claude credit left (and when it expires), the spend cap (Google) left, paused or not;
- **Next:** the one step to take, with its price and its bill (an arm with verses to make, then the judge, then
  the report); "Done" when every arm has its English, the judge has read it and the report is up to date;
- a grid, text by arm: verses made of 25 (a tick when complete); the spend per arm (Claude and Google apart); the
  price of a verse per arm, measured on BM1's own verses once an arm has made 10 (the tooltip says which);
- the judge's line: what it waits for (the arms and texts still to make), or how many English it has read and has
  to read;
- the buttons (section 4), and a link to the full report;
- the last report's numbers: chrF per arm (diacritics folded in the tooltip), judge-v1 per arm and for the published
  English, the paired differences with their 95% intervals (bold when the interval holds no nought), for all eight
  texts, without the Bhagavata, and without the misaligned units; text by text in a fold. The report says when it is
  partial ("scored on 6 of the 8 texts", "the judge has not read them yet: chrF only") and when a step has run since
  it was made ("make it again").

**The main table:** on each row, a chip for the register's state of its text ("withdrawn from the site", with the
date and the reason in the tooltip) and one for its scholarly English (verses, passed, flagged; a link to
`/scholar/<doc>`).

**The Usage tab:** the spend cap (Google) and the Claude credit side by side, each with its bar; BM1's line (what
it has spent, its next step, a link); Google and Claude apart in the totals and the engine table (a Bill column);
the steps since the credit began, by name (translation, scholarly English, judge, BM1's bench steps apart); the last
calls with their step and engine named.

## 4. The wiring: what a button does

- A button runs one step of `scripts/bench_mitra.py` as a dashboard job (kind `bench`, doc `BM1`): it is queued as
  any job, its last 16 lines show under the buttons while it runs, its outcome and the harness's NEXT line show when
  it ends, and the page reads BM1 again. A job running when the page opens is followed the same way. The History
  tab keeps it as any job.
- **Free:** Make the sample; Make the report again; Settle the ledger.
- **Paid:** Run an arm (on the verses it has not made); Judge them (the arms' English and the published, with
  `--judge-reference`). Each asks first, naming what it may spend and on which bill, and runs with
  `--yes --max-usd N`, where N is the estimate and a third more (at least $0.25). The harness's own refusals hold as
  on the command line: it refuses up front when the step does not fit the credit, the spend cap or `--max-usd`, and
  stops between texts when `--max-usd` is reached. One press may spend at
  most $12.00 (`/api/bench` refuses more and gives the command to run by hand).
- `/api/bench`: GET BM1's state (read only, from the bench folder and `data/context.db`); POST a step.
- `/benchmarks/bm1/report` serves `BM1_report.html` from the bench folder with `Cache-Control: no-store` and
  `X-Robots-Tag: noindex`. The dashboard listens on 127.0.0.1 only, so the report (it holds the dataset's text) is
  seen on this computer only; nothing of it is copied into the repository.
- The bench folder is `D:\Sanksrit Automatons\benchmarks\bm1` (`SA_BENCH_DIR` overrides it, for the tests).

## 5. Two corrections to BM1

- **The price of a verse is measured.** gemini-2.5-flash cost $0.005 a BM1 verse, twice what the corpus's rows said
  ($0.00247: BM1's verses carry their context), so the flash arm stopped at `--max-usd 0.75` with 150 of its 200
  verses made (the Satapatha Brahmana and the Ramayana to do). `bench_mitra.prices(mcon, out)` now prices an arm
  that has made 10 verses or more by its own spend; the dry run, the dashboard and each step's refusal use it.
- **The report's NEXT line is PowerShell's:** `Start-Process "...\BM1_report.html"`, in the harness and in
  docs/BENCH_MITRA_2026-10-16.md.

## 6. Where the benchmarks stand (16 Oct)

| | State |
|---|---|
| BM1 scholar | 200 of 200 verses, $8.52 |
| BM1 sonnet1 | 200 of 200, $1.03 |
| BM1 flash | 150 of 200, $0.75; the Satapatha Brahmana and the Ramayana to make (about $0.25) |
| BM1 judge | Not run: it waits for the flash arm (up to about $2.2, the published English included) |
| BM1 report | Partial: chrF only, 6 of 8 texts (141 units, 150 verses) |
| BM3 | The blind side-by-side: to build, after BM1's judge |
| BM2 | A gold set read by a person: a person's time |

The partial report (chrF against the published English; not fidelity, which the judge reads): flash 34.52,
sonnet1 36.72, scholar 35.06 over the six texts. Sonnet one pass is ahead of flash, +2.20 [1.32, 3.10]; the
scholarly arm is not shown ahead of flash over all six, +0.54 [-0.40, 1.38], but is without the Bhagavata,
+1.18 [0.21, 2.16]; it is behind Sonnet one pass, -1.66 [-2.48, -0.81]. chrF rewards nearness to 19th-century
English, from which the scholarly register departs by design; whether that departure is fidelity or loss is what
the judge and, later, BM3 and BM2 decide. No misaligned unit is counted yet: the Satapatha, where they are, is not
scored.

## 7. Commands (PowerShell, from `D:\Sanksrit Automatons\sanskrit-automatonv2`)

```
python scripts\patch_bench_desk_2026_10_16.py --check
python scripts\patch_bench_desk_2026_10_16.py
python -m unittest tests.test_bench_desk_2026_10_16 tests.test_bench_mitra_2026_10_16
.\scripts\restart_dashboard.ps1 -Status
.\scripts\restart_dashboard.ps1
```

Then BM1 from the Benchmarks page (Run flash, Judge them, Make the report again), or by hand:

```
python scripts\bench_mitra.py --arm flash --yes --max-usd 0.60
python scripts\bench_mitra.py --score --judge-reference --yes --max-usd 2.75
python scripts\bench_mitra.py --report
Start-Process "D:\Sanksrit Automatons\benchmarks\bm1\BM1_report.html"
```
