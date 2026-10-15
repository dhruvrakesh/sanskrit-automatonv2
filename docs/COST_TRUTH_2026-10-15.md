# What a call costs, metered as it is billed; the repo kept clean (2026-10-15)

Markers:
- **COST_TRUTH_2026_10_15:** `scripts/usage_meter.py`, `scripts/infer_mt.py`, `scripts/source_desk.py`,
  `scripts/scholar_translate.py` and `scripts/dashboard.py`, patched by `scripts/patch_cost_truth_2026_10_15.py`.
- **REPO_HYGIENE_2026_10_15:** `.gitignore` and `scripts/release.ps1`, patched by
  `scripts/patch_repo_hygiene_2026_10_15.py`.
- **DOCS55_2026_10_15:** `scripts/patch_docs55_2026_10_15.py`.

It follows SCHOLAR_V21 and READER_SOURCES (`7d292ca`; Srangam `4c37d48`), docs/SCHOLAR_V21_2026-10-14.md.

## 1. The thinking was not metered

**What usage_log showed (scholar-v2's run of 14 Oct, 21:13 to 22:11 IST, 49 calls of gemini-2.5-pro):**
- **Five calls came back empty, cut off at the 8,192-token limit.** Each was metered as its input alone: out_tokens
  0, $0.0038 to $0.0052. Their retries (16,384 tokens) were metered for their visible output only: for example
  1,235 tokens for 3,931 characters.
- **An empty answer at the limit means the model's thinking used all 8,192 tokens.** Google bills thinking as
  output: gemini-2.5-pro at $10 a million tokens, gemini-2.5-flash at $2.50 (`cost_tracker.py`'s table).

**Why it was missed:**
- `usage_from_response()` (usage_meter.py) and `_usage_add()` (infer_mt.py) add `thoughts_token_count` when the SDK
  names it. The SDK on this PC does not, so the thinking was left out.
- `total_token_count` (prompt + candidates + thoughts) was never read.

**What it means:**
- **The run of 14 Oct cost more than the $0.256 it recorded.** The five empty calls alone used at least 40,960
  thinking tokens, which is $0.41 more. Its real cost was at least $0.67, and likely more: the other 44 calls
  thought too, unmetered.
- **The pilot of 18:25 ($0.238) was metered the same way.**
- **The scholarly English's price was set from these rows:** "about $0.012 a verse" was low.
- **The working English and Hindi run on gemini-2.5-flash, which also thinks by default.** Their recorded spend may
  be low as well. How low is measured, not assumed: section 5 has the one call that shows it, and the comparison
  with Google's bill.
- **The spend cap (`budget_state`) sums the same rows.** It allowed more than it showed.

## 2. COST_TRUTH_2026_10_15

**The meter:**
- the output billed is `total_token_count - prompt_token_count` whenever that is more than the candidates and the
  thoughts the SDK names;
- the same in `infer_mt._usage_add` (the working English and Hindi) and in `source_desk.py`, which read the
  candidates only;
- the rows already in usage_log stay as they were metered.

**The scholarly English:**
- **The price counts only rows metered so** (`created_at` from `METERED_SINCE`, 2026-10-15). Before 10 of them it
  uses the prior, which now assumes 3,000 output tokens a call with the thinking (it said 1,500): about $0.10 a verse
  for a draft, a critique and half a revision.
- **A job that only adds working English** (`translate`, `translate_both`, `translate_one`) no longer stops a run,
  as a Hindi job already did not. Such a job never changes the Sanskrit a row is made from. A job that changes the
  Sanskrit (a repair, a re-ingest) still stops it.
- **Why it matters today:** MBh01's Finish EN / Add Hindi job sits in the queue, and until now the scholarly run
  refused while it was there ("the dashboard changes MBh01 now (translate_both)").

**The dashboard (after a restart, when idle):**
- **A job stopped while it waits for its lock no longer starts.** Before, it waited, then ran in full when its turn
  came, and was called "[KILLED by user]" afterwards.
- `/api/job/<id>/kill` says `"queued": true` for such a job.

## 3. REPO_HYGIENE_2026_10_15

**What `7d292ca` committed by mistake:**
- `data/raw_mbh01_ce/`: 225 files, MBh01's critical-edition e-text in Devanagari with its IAST;
- `data/heal/`: the heal's log.

**Why:**
- `release.ps1` stages everything (`git add -A`), and its safety check refuses only backups, raw_vision, raw_merged
  and probe;
- `.gitignore` had `data/raw/` and `sources/`, not these two.

**The patch:**
- `.gitignore`: `data/raw_*_ce/` and `data/heal/`;
- `release.ps1` refuses those two directories, and never refuses a path being taken out (a `D` in the status), so the
  removal can be released.

**The files stay on disk.** Taking them out of the repo is `git rm -r --cached data/raw_mbh01_ce data/heal`, by hand,
before the release.

**BORI's notice on the e-text reads "Please do not provide copies of the text to others".** Commit `7d292ca` keeps a
copy in the history:
- if the repository is private, nobody else has it;
- if it is public, the choice is the owner's: make it private, or rewrite the history (destructive; not done here).

## 4. The night's runs (14 to 15 Oct)

- **The two releases:**
  - automaton `7d292ca`: SCHOLAR_V21, READER_SOURCES, DOCS54; SCHOLAR_V21 applied on 15 Oct;
  - Srangam `4c37d48`: the reader names the reading.
- **C17 is in the Lovable database.** `corpus_reader_sources(text)`: anon false, authenticated true, SECURITY
  DEFINER, search_path "" (the export of 09:22).
- **MBh01 is not in the public reader** (`srangam_texts` has no row for it), so there is nothing to mend there.
- **The mirror of 08:52** sent 6 passages of the Natyasastra; 374 groups equal.
- **The translate queue:**
  - the Natyasastra's English has run since the night: 2,101 of 2,793 at 09:26, one translate job at a time;
  - behind it the Tantric Texts' re-ingest (queued at 22:15), then the 17 texts queued at 08:55 (about $7.78 by the
    old meter), then the Tantric Texts' translation and MBh01's (about $3.77 by the old meter).
- **MBh01's prose is not in yet.** The re-ingest refuses while the dashboard runs a writer, and the queue will run
  for a day or more. It goes in when the queue is done; then a Finish EN / Add Hindi for the 241 new passages.
- **The scholarly runs of v2.1 are not made yet.** Under the old rule they would have refused while MBh01's job was
  queued.

## 5. Keeping the cost under control

**First, measure:**
- one call of gemini-2.5-flash (a fraction of a cent) prints its `usage_metadata`: the total minus the prompt and the
  visible output is the thinking;
- usage_log's sums by day, set beside Google's bill for the same days, show how far the old meter was off.

**Then the scholarly English, by what it really costs:**
- 1.1.15 to 1.1.23 again (9 verses) is the measure: about $0.90 by the new prior, capped by its `NEXT:` line;
- before MBh01's whole book (7,197 passages), the ways to make it cheaper are, in order of risk:
  - the second judge on a sample, not on every verse;
  - one revision, not two;
  - a draft by gemini-2.5-flash with gemini-2.5-pro as the critic only;
  - the Gemini API's batch mode, which Google prices below the interactive calls (to be checked when it is used);
- each is a change measured on the same 9 verses first.

**The working translations:**
- the queue of 08:55 runs on gemini-2.5-flash;
- the meter is right from the next job: infer_mt.py is read again by each new job;
- the cap (`python scripts\set_budget.py`) then counts the thinking, and pauses the work when it is reached.

## 6. Tests

- **`tests/test_cost_truth_2026_10_15.py` (9):**
  - the meter (the thinking counted where it is not named, as before where it is or where there is no total), the
    translation meter;
  - the price counts only rows metered so;
  - a job that adds working English does not stop a run, one that changes the Sanskrit does;
  - a queued job stopped never starts;
  - the patcher, the files.
- **`tests/test_repo_hygiene_2026_10_15.py` (4):** what git leaves out, the release check, the patcher, the files.
- **Follow:**
  - `test_scholar_v2_2026_10_14` and `test_scholar_v21_2026_10_14`: the price rows carry `created_at`; their
    replay chains end at the `.bak_costtruth_` copies;
  - `test_quality_2026_10_11`: source_desk.py's replay chain ends at its `.bak_costtruth_` copy.
