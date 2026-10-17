# The translation desk: the scholarly English from the dashboard, and the path first (17 Oct 2026)

Markers:
- **TRANSLATION_DESK_2026_10_17:** `scripts/translation_desk.py` (new: the desk's rules); `scripts/dashboard.py` and
  `scripts/dashboard_static.html`, patched by `scripts/patch_translation_desk_2026_10_17.py` (needs
  BENCH_GOLD_2026_10_16 and BENCH_DUEL_2026_10_16); `tests/test_translation_desk_2026_10_17.py` (13 tests). The replay
  chains of `test_bench_duel_desk_2026_10_16` and `test_bench_gold_desk_2026_10_16` follow to `.bak_transdesk_`.
- **DOCS69_2026_10_17:** `scripts/patch_docs69_2026_10_17.py`.
- The SOP this desk carries: docs/SOP_TRANSLATION_2026-10-17.md (a draft until BM2). BM3's check:
  docs/BM3_CHECK_2026-10-17.md.

## 1. What was asked, and what was so

Asked on 17 Oct: translation from the dashboard offers no path to the scholarly English and the method honed on
15 and 16 Oct; why can the dashboard not be used for translation better, with a separate face for the texts well
translated or on the way to it.

What was so, read from the code and the data on 16 and 17 Oct:
- **One method behind every button.** The main dashboard's Translate and Start, and the Library's Finish EN, ran the
  working English in one pass (`translate_passages.py`, `MT_ENGINE` gemini-2.5-flash, `--min-quality 0.35`). The engine
  menu offers Gemini and GPT models; nothing on the dashboard started `scholar_translate.py`.
- **The path was not asked.** On 16 Oct the Padma Purana's Patala Khanda (SP_4214) was started from the main page on
  its Tesseract reading; the job showed `[ILLEGIBLE]` lines at quality 0.38 to 0.56 and was stopped after 34 s. Its
  path (text_path.py, 14 Oct): repair: debris moderate (1.56% of letters misread), vision has read none of its 364
  pages; the next step `repair_text.py --repair --max-usd 1.90` (about $1.47), then the re-ingest's plan (free).
- **The pieces were on pages of their own:** the path (`/path`), the register (`/sources`), the repair
  (`/repair/<doc>`), the scholarly English (`/scholar`, `/scholar/<doc>`, `/scholar/<doc>/prose`, read only), the
  benchmarks (`/benchmarks`), the redemption of marked passages (`/redeem`), the reader (`/reader/<doc>`).

## 2. What this release does

**D0, the guard.** `/api/translate` and `/api/pipeline/translate-doc` answer 409 (`needs_force`, with the path's
reason and next step) for a text whose path says the reading comes first: repair the scan, use the repair, ingest,
find a source, retire, or a translate path whose first step is not a translation (a re-ingest of changed pages).
`{"force": true}` goes on. The main page's Translate and Start and the Library's button ask ("Translate it anyway?")
and send `force` only on a yes; Translate ALL leaves the guarded texts and says which. A text the register withdraws
or sets aside is held, as before, by `translate_passages.py` itself (HOLD_2026_10_14). Not guarded: a text the chart
has not charted, and a text whose path is translate or in repair with a translation as its first step.

**D0, the chips.** Each row of the main page shows its path ("the reading first: repair the scan" in red, or "path:
translate" in green), linked to its page on the desk. `/api/status` carries it on each row (`path`: its path, the next
step, the chart's date, held or not).

**D1, the desk (`/desk`).** Every text by its stage, from the path chart, the register and the scholarly English:

| Stage | From |
|---|---|
| The scholarly edition | the scholarly English is begun (current verses in scholar_translations) |
| Ready to translate | the path: translate (or in repair), its first step a translation |
| Translated: to judge | the path: judge, retranslate |
| Done | the path: done |
| The reading first | the path: repair, use the repair, ingest, find a source, retire, or a re-ingest first; or the register: withdrawn, set aside |
| Not charted | the chart has no row for it |

Each row: its English (of the verses), its scholarly English (verses, passed, flagged, doubted, accepted), its one
next step. The page shows the chart's date (with "old: chart it again" from three days), "Chart the path again
(free)", the Google cap's headroom and the Claude credit left, and the desk's jobs running.

**D2, a text's page (`/desk/<doc>`).** Where it stands; the path's steps with links to the repair page and the path;
the working English ("Translate the rest (working English)", where the text is ready and not held: English only, the
Library has Add Hindi); the scholarly English:
- **Plan them (free):** the dry run of `scholar_translate.py` with the standard flags (Sonnet drafts and criticises,
  Opus audits one sentence in ten, judge-v1 reads every sentence; translation_desk.SCHOLAR_SOP = BM1's SCHOLAR_FLAGS),
  Pages and Verses (1 to 400) to choose; it prints the verses ready and the price;
- **Run these verses: at most $X:** the plan's own `--max-usd`, shown only at $12.00 or less; it asks first;
- **Status, Report, Triage what is not passed (free).**
The scholarly steps are refused (409) for a text withdrawn or set aside, or whose path says the reading comes first;
a text in repair runs with `--held-ok`, said on the page. A text whose scholarly English is begun is not refused for
its path (the Hayasirsa, in repair, is one); its page says when the path holds its working English. The jobs are of
kind "scholar", doc "scholar:<doc>" (so that the script's own check of the dashboard's jobs on the text does not see
itself), under the dashboard's general limit (three at a time), as when it was run from PowerShell beside the
dashboard's translations: it writes its own tables and the usage log, through db_utils (WAL, a 30 s wait for the
lock). Logged in the History like every job.

**Load time.** The desk reads the database read only (`mode=ro`) and keeps what it found for 30 s; the chart is read
again only when its file's time or size changes (the main page's status poll asks for it each time: 2.4 ms to read
and parse it on the VM, a file's stat when it has not changed); the guard reads the chart and the register only. Nothing is added to the main page's load but the chips. Not yet
measured on the real database: the command in section 6 measures it.

**Not changed:** `MT_ENGINE`, the engines' menu, judge-v1, the scholarly pipeline itself, the database's schema, the
site.

## 3. Two faces of one dashboard (the "separate frontend")

- **The workbench:** `/desk` and `/desk/<doc>`: what each text needs next, and the buttons for it, the guard before
  them.
- **The reading room:** `/scholar` and `/scholar/<doc>/prose` (the scholarly English read as prose, with its notes),
  `/reader/<doc>` (the working English); the desk groups the scholarly editions first and links to them.
- **The site (Srangam):** the working English only, until S4 (D5).

One server, one port (5057), as the runbook keeps it: a second dashboard would contend for the database and the
translate lock.

## 4. The path forward (each phase surgical, each tested before the next; decisions yours)

| Phase | What | Cost | Needs | Done when |
|---|---|---|---|---|
| D0 to D2 | The guard, the chips, the desk, the scholarly steps (this release) | free to build | BENCH_GOLD, BENCH_DUEL | built; 13 tests; applied and released by you |
| D3 | The review in the browser: each flagged or doubted verse with Accept, Reject, a note, a glossary entry, on the text's desk page; each a job of `scholar_translate.py --review / --term` (free), so that the script stays the one writer | free | D2 | a person's verdicts on the desk and in `--status`; tests on a fixture |
| D4 | The SOP confirmed: BM2's first 40 units read by you, its report; then Tier R decided. If yes: a second button on a ready text, the working English by Sonnet (the Claude credit; per job, `MT_ENGINE` unchanged), priced first | BM2 free; Tier R about $0.005 a verse | your reading; the credit ends 11 Nov | the SOP loses "draft"; the decision written down |
| D5 | S4, the scholarly layer on the site: its design first; then a table and its read function (the Lovable Cloud SQL editor, checks before and after), `corpus_sync.py` sending the current passed and accepted verses only, Srangam's reader showing it above the working English with its notes and status, and a label for the working English ("a draft") | Lovable; no model calls | Srangam's TEST_WAIT patch applied; D3 | a scholarly text readable on the site; the reader's tests pass |
| D6 | The source-first queue: the 34 texts to repair (vision about $24, $15 to $39, on the Google cap), each repair then its re-ingest's plan (free) then the chart again, then its English (about $71 at flash's corpus price) | about $24 then $71 (estimates) | the cap raised, by you; an order of texts, by you | the texts move from "the reading first" to "ready" on the desk |
| D7 | The chart kept current: charted again (free) when a job of OCR, repair, re-ingest or ingest ends well; the measures of section 6 on the real database, and a cache only where they are slow | free | D2 | the desk's date never older than the last such job |
| D8 | The benchmarks as the regression test of any change of a tier (BM1's subset, BM3's 40 units, with and without notes); J2 after the baseline | about $3 to $13 a run | BM2 | written into the SOP |

## 5. Guardrails kept

- Every paid step plans first and stops at its cap; the desk's Run is the plan's own cap, at most $12.00 a press, and
  asks.
- The register and the path are asked before every translation; a person may go on, and the button says what goes
  with it.
- No new server, no new port, no change to the database's schema, no change to the site; the patch is anchored,
  all-or-nothing, marker-idempotent, backs up first (`.bak_transdesk_<date>`), keeps line endings, compiles before
  it writes.
- The scholarly English stays off the site until S4; the benchmarks' outputs never go there.
- Scripts that post to `/api/translate` by hand (the commands `plan_empty_retries.py` prints) get the guard's 409 on
  a guarded text: repair it first, or add `"force": true` knowing why.

## 6. Commands (PowerShell, from `D:\Sanksrit Automatons\sanskrit-automatonv2`)

```
python scripts\patch_translation_desk_2026_10_17.py --check
python scripts\patch_translation_desk_2026_10_17.py
python -m unittest tests.test_translation_desk_2026_10_17
.\scripts\restart_dashboard.ps1 -Status
python scripts\text_path.py
Start-Process "http://127.0.0.1:5057/desk"
Measure-Command { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5057/desk" | Out-Null } | Select-Object TotalMilliseconds
Measure-Command { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5057/api/status" | Out-Null } | Select-Object TotalMilliseconds
```
