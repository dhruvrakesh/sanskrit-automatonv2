# The Claude credit first, Gemini after it (CLAUDE_FIRST_2026_10_15)

Markers:
- **CLAUDE_FIRST_2026_10_15:** `scripts/scholar_translate.py` and `scripts/infer_mt.py`, patched by
  `scripts/patch_claude_first_2026_10_15.py`.
- **DOCS60_2026_10_15:** `scripts/patch_docs60_2026_10_15.py`.

It follows RUN_FIX_2026_10_15 (docs/CANARY_2026-10-15.md).

## 1. The decision (15 Oct, Dhruv)

**The decision:** the free Claude credit pays for the translation work, and Gemini comes after it. The credit is:
- $200 of API credit, capped here at $190 (SA_CLAUDE_CREDIT_USD);
- valid to 11 Nov;
- usable through the API only.

**Why:**
- Google's prepaid Gemini balance burns fast. Dhruv puts his whole monthly spend at ₹20–25k all inclusive.
- The automaton's own ledger has been reading low.

**What was seen on 15 Oct:**
- The Claude runs were still using Gemini for their checks.
- At 17:18 IST, the Kāraṇāgama's canary and the redo of 20.6 and 20.8 were stopped by Google's spend cap ($45.00,
  100% recorded; paused at 16:56 IST).

**The Gemini API account (AI Studio, billing account DKEGL, one project, Paid tier 3):**
- prepaid, with auto-reload on;
- ₹2,500 added on 14 Oct;
- the balance was ₹2,380.65, then ₹2,183.46 by 18:13 IST on 15 Oct (Dhruv's two screenshots).
- The "Transactions" rows (Oct 1–15, Sep 1–30) are not read here. Download them to see whether they are the charges or
  the balance.

## 2. Where Gemini goes: the ledger

The ledger is `usage_log`, read from the backup `context_pre_sonnet_20261015.db` (10:56 UTC, 15 Oct). It records what
it priced, not the bill.

| Month | Gemini calls | Recorded $ | Rows priced from the provider's tokens |
|---|---|---|---|
| Jun | 1,411 | 0.83 | 0% |
| Jul | 14,528 | 2.33 | 0% |
| Aug | 18,346 | 4.68 | 5% |
| Sep | 20,050 | 5.24 | 30% |
| Oct 1–15 | 28,399 | 29.94 | 77% |

**October by kind (recorded $):**

| Kind | Engine | Recorded $ | Calls |
|---|---|---|---|
| translation (the working English) | gemini-2.5-flash | 13.45 | 23,846 |
| ocr_vision | gemini-2.5-flash | 6.41 | 2,365 |
| image | gemini-3.1-flash-image | 5.55 | 60 |
| entities | gemini-2.5-flash | 1.77 | 1,311 |
| scholar | gemini-2.5-pro | 0.95 | 112 |
| story_mine, story | gemini-2.5-flash | 0.86 | 77 |
| judge | gemini-2.5-pro | 0.39 | 6 |
| image_brief | gemini-2.5-flash | 0.20 | 25 |
| judge | gemini-2.5-flash | 0.16 | 337 |
| embedding | gemini-embedding-001 | 0.13 | 193 |
| everything else | | under 0.08 | |

**Why the ledger reads low:**
- Before 15 Oct, the thinking of gemini-2.5-* (billed as output) was not counted. COST_TRUTH_2026_10_15 counts it
  from 15 Oct.
- 70% of September's rows, and 23% of October's, were priced from characters (chars/4). Devanagari has fewer
  characters per token than that, so the price comes out too low.
- If any other app uses the same key or project, the bill has it and the ledger does not.

The bill is the truth. `python scripts\spend_audit.py --days 30` gives the ledger side, to set against AI Studio's
Spend page.

**Scheduled jobs on the PC** (scripts\*.ps1) that run while nobody watches:
- `maintenance_runner.ps1` runs qa_scan, build_embeddings, brain_items and extract_entities (--limit 1500). Its header
  says the Gemini API must be reachable.
- `corpus_mirror_task.ps1` runs corpus_sync and corpus_media.
- `corner_task.ps1` runs corner_worker.
- The ledger by kind shows which of them spend.

## 3. What can move to Claude

| Work | Gemini now | Claude |
|---|---|---|
| The checks of a scholarly run (the judge, the audit, the second judge) | 2.5-flash judge; 2.5-pro audit and second judge | **Yes, now:** another Claude model (section 4) |
| The working English and the Hindi (translate_passages.py, the dashboard's jobs) | 2.5-flash | **Yes, after a benchmark:** the engine `anthropic:` (section 6) |
| Entities, stories, image briefs | 2.5-flash | Possible; not built |
| OCR (vision) | 2.5-flash vision | Not now: not built, and it would need its own benchmark |
| Pictures | 3.1-flash-image | No: Claude makes no pictures |
| Embeddings (the mirror, the brain) | gemini-embedding-001 | No: Anthropic has no embedding model |

## 4. CLAUDE_FIRST_2026_10_15: the code

**scholar_translate.py:**
- The checks of a Claude run may be another Claude model's:
  - `--judge-engine anthropic:...`: judge-v1, on every verse (and on the working English where there is one);
  - `--compare-engine anthropic:...`: the second judge and the audit.
- Each check is metered on the Claude credit (usage_log, kind "judge" or "scholar").
- The translator's own model may not check it: the run is refused, whatever the effort.
- **A run with no Gemini engine at all:**
  - is gated by the Claude credit only;
  - does not consult Google's spend cap;
  - does not need a Gemini key.
- Gemini runs and the defaults:
  - a Gemini run may not have Claude checks (refused);
  - the defaults (gemini-2.5-flash, gemini-2.5-pro) are as before.
- The dry run says whose bill each check is, and the NEXT line keeps both flags.

**infer_mt.py:** the engine `anthropic:<model>[@effort]`.
- It translates the working English and the Hindi with the same system prompt and message as Gemini.
- Every call is metered on the Claude credit (usage_log, kind "translation"). budget_state is never touched.
- The credit is asked before each passage. It fails closed: BudgetBlocked stops the job.
- An answer cut off is asked once more with twice the room; if it is still cut off it is left empty (an honest gap),
  as the Gemini ladder ends. A refusal is also left empty.
- Nothing is cached when the answer is empty.
- A missing key, a missing SDK, or an account that refuses to bill stops the job at once (ClaudeUnavailable).
- **The default is unchanged:** `MT_ENGINE` stays `gemini:gemini-2.5-flash`. It is also the engine of Ask and of
  extract_entities, which call Gemini directly, so it must not be set to an `anthropic:` engine. A job moves to
  Claude only when it is given the engine.
- translate_passages.py writes the engine it was given into `passages.engine` (or `translations_l10n.engine`), so
  every row says who made it. This was checked end to end on a fixture.

**Tests:**
- `tests/test_claude_first_2026_10_15.py` (13): a scripted SDK and a Gemini stub, so nothing is called.
- `test_claude_engine_2026_10_15`: another Claude model may check it; its own may not.
- `test_cost_truth_2026_10_15` (infer_mt.py) and `test_run_fix_2026_10_15` (scholar_translate.py): their replay chains
  end at the .bak_claudefirst_ copies.
- In the sandbox: 653 passed; the 36 failures are the same environment ones as before.

## 5. Independence: what this gives up

**What was given up:** the checks were cross-family by design: a Claude English was never judged by Claude.

**Evidence that it mattered:** on the Kāraṇāgama's canary, Claude's own critic accepted 28.4. All three Gemini checks
caught it:
- the flash judge gave fidelity 2;
- the Pro audit found a major misreading;
- the Pro second judge read the working English as the better one.

**What the new checks risk:**
- Opus audits and Haiku judges; the translator's own model is refused.
- They are the same family, so they may share blind spots.
- In the pilot's duel, the Opus judge preferred Opus.

**Two ways to keep a cross-family reading:**
1. **Now, for about ₹80 in all:** keep the flash judge (the default `--judge-engine`) and move only the audit and the
   second judge to Opus (`--compare-engine anthropic:claude-opus-5-5`). Google's spend cap then still gates the run.
2. **After the credit (from 11 Nov):** a Gemini flash re-judge of the rows that the Claude checks passed. It costs
   about $0.0004 a verse. Not built yet: CF2.

## 6. The working English on Claude: a benchmark first

**The backlog** (the backup of 15 Oct): 137,755 passages without English in 65 texts, 15.9 M characters. Not all of
it is Sanskrit, or ready.

The largest pending texts:

| Text | Passages without English |
|---|---|
| Yoga Vasistha (Thakur Prasad Dwivedi, Lala Baijnath) | 68,189 |
| Padma Purana, Patala Khanda | 21,128 |
| Daivat-Sanhita | 13,887 |
| Rgveda-samhita vol. ii | 11,565 |
| LalitaVistara | 4,247 |

**The benchmark:** `scripts/benchmark_mbh01.py` runs the real pipeline (translate_batch) on N passages per engine,
side by side, and writes `exports/<doc>_benchmark_<n>.html`.
- Engines: gemini-2.5-flash, claude-haiku-5-5 and claude-sonnet-5-5@low.
- Texts: three of the backlog, 12 passages each.
- A person reads the three columns.
- The cost per passage comes from usage_log; no estimate stands in for it.

**If a Claude column holds up:**
- Run the jobs per text, from the dashboard's API:
  `POST /api/pipeline/translate-doc {"doc": ..., "engine": "anthropic:claude-haiku-5-5"}`.
- They run under the dashboard's translate lock, as every translate job does.
- After the credit, the same jobs run with the default engine.

## 7. The credit to 11 Nov (a forecast; `--status` and `--credit` are the truth)

**Where it stands:** $174.75 left at 12:42 UTC, 15 Oct.

**What today's runs measured:**
- The Hayaśīrṣa, three windows, 41 minutes:
  - 266 verses: 224 passed (84%), 36 flagged, 6 source doubts, none failed;
  - $0.0456 a verse all in, with the Gemini checks at 1 in 10.
- The Kāraṇāgama's canary:
  - 16 verses: 14 passed (88%);
  - $0.078 a verse, with the audit and the second judge on 1 in 3.

**What is left:**

| Text | Verses left | $ a verse | Credit |
|---|---|---|---|
| The Hayaśīrṣa | about 1,159 | about $0.048 | about $56 |
| The Kāraṇāgama | 1,012 | about $0.066 | about $67 |

- The rates are with the Claude checks (Haiku judge; Opus audit 1 in 10 at an estimated $0.05 each).
- **The Kāraṇāgama is over the canary's $0.05 cost gate.** It passes on quality, and the credit covers it.
- That leaves about $45–55 for the working English, if the benchmark passes.

## 8. Guardrails kept

**On the checks:**
- The translator's own model never checks its English.
- A check that does not answer flags the verse.
- A person reads what is flagged.
- `judge_engine` and the audit's "by" say who checked each row.

**On the money:**
- The credit fails closed.
- Each window has its own `--max-usd`.
- Google's cap still gates any run with a Gemini part.

**On the rest:**
- Nothing moves to Claude unless a job is given the engine. MT_ENGINE is unchanged.
- The rows are append-only.
