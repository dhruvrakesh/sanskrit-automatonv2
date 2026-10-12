# The mirror's retire, a real cap, the median price (2026-10-12, afternoon)

Marker: **MIRROR_CAP_2026_10_12**, in `scripts/corpus_sync.py`, `scripts/ocr_consensus.py`, `scripts/text_path.py`
and `scripts/dashboard.py` (patched by `scripts/patch_mirror_cap_2026_10_12.py`).

It builds on PATH_2026_10_12 (`docs/PATH_2026-10-12.md`, released `408e11b`).

## 1. What the afternoon showed

- **PATH was applied, tested (110 tests, OK), released and pushed:** `408e11b` is on origin.
- **The chart on the live database** (13:37): 69 texts. 12 use the repair, 2 retire, 10 ingest, 28 repair the scan,
  6 find a source, 4 translate, 3 translate again (the judge: Shatapatha 11%, Mallapurana 18%, Markandeya 13% wrong
  meanings), 2 in repair, 2 done (Sandilya 5%; Ganita Yukti Bhasa). About $45.61 of vision and judging at the corpus
  price (section 3), then about $49.99 of translation.
- **Hayashirsha is not what the backup said.** On the live database it is 98.5% vision with 0 English: its repair
  went in at 22:50 on 11 Oct, after the 22:30 backup the session charted. Its path is right: translate, then
  `--release`. docs/PATH_2026-10-12.md section 3 says otherwise; this corrects it.
- **The two Dhanur Veda copies were retired** (`retire_doc.py --yes`: 19 and 38 passages, the keepers kept), and
  **the Bodhicaryavatara was withdrawn** (13:56).
- **The mirror run (13:57) stopped:** `corpus-ingest HTTP 422: corpus_retire: canceling statement due to statement
  timeout`. The scheduled run at 14:32 stopped the same way. Before the retire, it sent what had changed (the Sama
  Veda's 524 new passages, 468 Hindi translations of the Tantric Texts) and retired the three texts' rows in
  `corpus.docs`. Their passages are still live: the site's figures at 14:28 still show the Bodhicaryavatara 1,677
  live (824 English), shiva_dhanur_veda 19 and vasishtha_dhanur_veda 38; 65 texts, 92,389 live passages, 23,700
  English.
- **No re-ingest has been applied yet** (there is no `data/reingest/`): the 12 texts to use the repair, the Tantric
  Texts' 7 pages and Karan's 7 wait. The Natyasastra's repair has not run again (268 of 546 pages read).
- **The OCR queue runs:** the Parashara Upapurana is read (72 of 72); the Samba (153 of 241) and Saura (86 of 289)
  are being read; the Taittiriya Yajurveda and the Yoga Vasistha wait their turn.

## 2. Why the retire timed out, and the fix

The run retires a text that is gone from here table by table, the vectors first. The Bodhicaryavatara's 824
vectors went in one call, and a vector retired is a new entry in the HNSW index, as an insert is: the vectors are
sent 25 to a call for that reason since 9 Oct (SYNC_SPLIT). **The fix:** vectors are retired 25 to a call, and a
retire the database cancels for its timeout is sent again in two halves, down to one key, as an ingest is. A
second call is safe: `corpus_retire` retires only rows still live. Any other error, and a one-key timeout, stops
the run as before.

## 3. A cap that holds, and the price

- **`--max-usd` was only an estimate check.** `ocr_consensus.py` refused a run whose estimate was above it; once
  started, nothing stopped it. A text dearer than its estimate could spend past it. "It stops before spending more"
  (PATH's NEXT lines) was not true until now. **The fix:** before each page, the vision calls of this text since
  the run began are read from usage_log and priced as `measured_cost_per_page` prices them. The run stops before a
  page would take it past `--max-usd`; the redo round too.
- **The corpus price is the last 300 vision calls.** After the Natyasastra's run (its pages cost $0.0111, with
  their billed retries) it is $0.0100 a page. The ten texts measured on their own cost $0.0011 to $0.0111, with the
  median about $0.0024. The estimate and the cap stay at the corpus price, because the run refuses an estimate above
  its cap. The chart now gives the median text's price beside it, as what a text not yet measured most likely
  costs.

**Tests:** `tests/test_mirror_cap_2026_10_12.py` (11); the PATH patcher replay in `tests/test_path_2026_10_12.py`
compares with this patch's backups. The full suite in the sandbox: 701 tests, the same 69 failures and errors as
before (none new).

## 4. State after this patch is applied

| Where | State |
|---|---|
| Automaton repo | `408e11b` on origin; MIRROR_CAP to release |
| Srangam repo | `d1752d4`, the same as origin at the last fetch; nothing to change this round |
| The site | three texts half retired until the next mirror run |
| The dashboard | running the code from before PATH; `/path` and the new steps after a restart, when idle |
| Data | 12 + 2 re-ingests, the Natyasastra's vision, the OCR queue, the translations: see the RUNBOOK |
