# Claude as an engine of the scholarly English, the Āgamas and Tantras first (2026-10-15)

Markers:
- **CLAUDE_ENGINE_2026_10_15:** new `scripts/claude_engine.py` and `scripts/scholar_duel.py`; `scripts/scholar_translate.py`
  and `scripts/cost_tracker.py` patched by `scripts/patch_claude_engine_2026_10_15.py`.
- **DOCS56_2026_10_15:** `scripts/patch_docs56_2026_10_15.py`.

It follows COST_TRUTH and REPO_HYGIENE (`8d14d39`), docs/COST_TRUTH_2026-10-15.md.

## 1. Why, and who wrote it

- **The credit:** $200 of Claude API credit came with the Max plan (Dhruv's Individual Org). It expires on 11 Nov 2026.
  It pays for the Claude API (Messages, Message Batches), not for Claude Code or the Claude apps.
- **The yardstick is the work of 14 Oct:** scholar-v2.1 (gemini-2.5-pro drafts; a critic, revisions, judge-v1 and a
  second judge). Claude is added as another engine of the same pipeline, with the same prompts, rules and judges.
- **Disclosure:** this code was written by Claude, and Claude is one of the contestants. So the choice is made blind:
  two judges, one from each family, neither told who made which, and your own reading on a blind page.

## 2. The Āgamas and Tantras here (state on 15 Oct)

| Text | Passages | Reading | Register | Working English | The scholarly English now |
|---|---|---|---|---|---|
| Hayaśīrṣa Pañcarātra (Ādikāṇḍa), `HAYASHIRSHA_PANCARATRA` | 1,614 | 98% vision, debris 0.16% | in_repair since 11 Oct, 22:50 (repaired; held from the site until translated) | 1 of 1,614 (queued) | with `--held-ok` |
| Kāraṇāgama, Kriyāpāda (1994), `Karan_Aagama_by_Prof_...` | 1,874 | 90% vision, debris 0.09% | in_repair since 11 Oct, 19:54 (held again: released before its translation was back) | 4 of 1,874 (queued) | with `--held-ok` |
| Tantrik Texts vol. I: Tantrābhidhāna, Bījanighaṇṭu, Mudrānighaṇṭu ..., `tantric_texts_series_edited_by_arthur_av` | 2,946 | 96% vision | restored | 2,830 | after its re-ingest (queued 14 Oct, 22:15): until then a run stops |
| Ākāśabhairavakalpa, `AkashBhairavaKalpam` | 2,039 | Tesseract only, debris moderate (1.84%) | - | none | after vision OCR (about $1.30, Google's) |
| Śāradātilaka II, `sharada_tilaka_tantra_ii` | 0 | one PDF, not read; its OCR failed on 28 Aug and 7 Sep | - | - | after the ingest |

**What the readings showed:**
- **The Hayaśīrṣa's edition prints its apparatus:** each page ends with the variants of manuscripts A, B, C, D by
  footnote number (`5 च-B. 6 चव-B,C. 7 यत् (?)-B,C.`), and the numbers stand in the verses (`तु5`, `चान्या6`). The
  vision reading kept both.
- **The Kāraṇāgama is bilingual:** the editor's Hindi rendering follows each verse as its own passage. A Hindi passage
  with fewer than three of the old Hindi words was taken for Sanskrit (30.9: `मनुष्य के दस या बारह ... हाथ के परिमाण
  वाला मण्डप ... के लिए ... चाहिए`). By the new list 712 of its 1,935 passages are Hindi (599 before).

## 3. CLAUDE_ENGINE_2026_10_15

**scripts/claude_engine.py (new):**
- one call: streamed (no time limit on a long answer), the text blocks joined, the thinking left out; the SDK retries a
  rate limit, an overload, a server error and a dropped connection (4 times);
- the request: no temperature, top_p or top_k (Sonnet 5.5 refuses a non-default value; none is sent to any model); the
  effort in `output_config` (an engine names it after an "@": `anthropic:claude-sonnet-5-5@medium`; without it, the
  model's own: high for Sonnet 5.5, medium for Opus 5.5 and Haiku 5.5); max_tokens counts the thinking;
- the price, from the usage the API reports (platform.claude.com, read 15 Oct), $ a million tokens:

  | Model | Input | Output | 5-minute cache write | Cache read |
  |---|---|---|---|---|
  | claude-opus-5-5 | 4.00 | 20.00 | 5.00 | 0.20 |
  | claude-sonnet-5-5 | 2.00 | 10.00 | 2.50 | 0.10 |
  | claude-haiku-5-5 (a prompt to 100,000 tokens) | 0.10 | 0.50 | 0.125 | 0.01 |

  The Batch API is half of each. The thinking is billed as output, and `usage.output_tokens` counts it;
- the meter: a row in usage_log (engine `anthropic:<model>`, the tokens as reported, token_source `provider`) and in
  usage_totals, so the dashboard and spend_audit.py show it; **not** in budget_state: Google's spend cap stays Google's;
- the credit: the usage_log rows of `anthropic:%` from 2026-10-15, capped at **$190** (the credit is $200; $10 is kept
  back for what this meter does not see), and nothing is sent from 11 Nov. `.env` may set `SA_CLAUDE_CREDIT_USD`,
  `SA_CLAUDE_CREDIT_SINCE`, `SA_CLAUDE_CREDIT_EXPIRES`. The check fails closed. The Console's Billing page is the truth;
- `--credit` (free) and `--probe` (one short call, recorded as kind `probe`).

**scripts/scholar_translate.py:**
- `--engine anthropic:claude-sonnet-5-5` (or `claude-opus-5-5`, `claude-haiku-5-5`, with or without an effort): the
  translator, the critic and the groups call by Claude (class `Claude`). The judge stays judge-v1 (gemini-2.5-flash)
  and the second judge gemini-2.5-pro (`--compare-engine`, refused if it names Claude): a Claude English is never judged
  by Claude. A run is capped by the credit for its Claude calls and by the spend cap for the Google part; the dry run
  prints the credit, and a warning when it does not cover the run;
- one place for the system prompts (`SYSTEMS`, `system_for`): every engine sends the same;
- **the Āgamas and Tantras** (a category or a name with agama, tantra, pancaratra, bhairava): rule 13 in the draft
  (agama-1, recorded as `+agama-1` in prompt_version): a mantra, a seed-syllable or a ritual formula stays in IAST and is
  not translated; a term of ritual, iconography, architecture or measure follows rule 6, and a measure is given as the
  text gives it; a Latin digit in a word is the edition's footnote number, left out; a plain misprint is read as it must
  be and said in the doubts. The critic and the judges are told that the IAST mantra and the missing digit are no
  issue;
- **the edition's apparatus** on the verse's page goes with the verse ("for understanding only ... a variant that
  changes the meaning: a note of kind textual"). It is never sent as a verse (its numbers make it an index);
- the texts' names in the prompts (`TITLES`): the Hayaśīrṣa Pañcarātra, the Kāraṇāgama (Kriyāpāda, ed. Rāmacandra
  Pāṇḍeya, 1994) and the Tantrik Texts vol. I; `--title` for another;
- **Hindi:** 30 words more that are Hindi only (लिए, चाहिए, वाला, होने, जाता, हुए, इस, भी, ने ...); across the
  database they catch Hindi passages only (113 more in the Kāraṇāgama; the rest are Hindi introductions or OCR debris
  that the debris rule leaves out first);
- `--held-ok`: a text in_repair is translated (nothing is written to the site or to its passages; a row goes stale, not
  wrong, if its reading changes). Without it the refusal says so. Withdrawn and set-aside texts are refused as before;
- `--no-glossary-adds`: a benchmark run; the glossary does not grow, so every engine sees the same one;
- the `NEXT:` line keeps `--engine`, `--held-ok`, `--no-glossary-adds` and `--title`; `--show-prompt` prints the system
  prompt as it is sent.
- runs side by side: two runs that number the same verse at once number it again (store), so the engines
  of a pilot can run at the same time.

**scripts/cost_tracker.py:** the three Claude models in the price table (for the priors, and anything that prices an
engine by its name; an "@effort" finds its model).

## 4. The head to head: scripts/scholar_duel.py (new)

- **What is read:** for each verse, each engine's latest current scholarly English. A sentence that one engine
  translated whole over several verses is read whole for every engine (a span). An engine without a current, whole
  English for every verse of a span is left out of it.
- **The judges:** gemini-2.5-pro and claude-opus-5-5 by default (`--judges`). Each gets the verse(s) with their
  context, the apparatus and the glossary without the entries a scholarly run added (they would carry one engine's
  spellings), and the translations as A, B, C ..., in an order shuffled for each judge. Each gives fidelity, prose and
  notes (1 to 5), the errors, a ranking and the best (duel-v1).
- **Stored:** scholar_duels, append-only. A span a judge has read on the same rows is not asked again (`--redo`).
  Spend: usage_log, kind `judge` (Gemini's in the spend cap, Claude's in the credit).
- **The page** (`--report`, free): blind by default. Each span shows the Sanskrit and "Translation 1, 2, 3, 4"; the
  judges' scores are under one fold and who made which under another; the tally (wins, ranks, scores, major errors,
  status, $ a verse, the judges' agreement) under a last fold, to be opened after reading. `--named` names them.
- **The person's pick:** `--pick` takes span=number pairs, comma-separated (the number is the page's Translation
  number, or `equal`), with `--by`. It is stored as judge `person:<name>`, and the tally counts it.

## 5. The pilot

- **The verses (18):**
  - Hayaśīrṣa 20.5 to 21.4 (10): the second paṭala: the Lord's answer and the twenty-five Pañcarātra tantras by name;
  - Kāraṇāgama 30.1 to 31.1 (8): the maṇḍapa of initiation: its measures, the trees at the quarters, the kuṇḍas and
    their shapes by direction.
- **The engines (4):** gemini-2.5-pro (scholar-v2.1, the yardstick), claude-sonnet-5-5 (effort high, its own),
  claude-sonnet-5-5@medium, claude-opus-5-5 (effort medium, its own). Each with `--held-ok --no-glossary-adds --redo`;
  they may run at once (the logs are named by the second: start them two seconds apart).
- **The cost, by the prior (the pilot measures it):** about $0.10 a verse an engine: some $1.80 of Google's for
  gemini-2.5-pro, some $6 of the credit for the three Claude runs; the head to head about $1 to $2, half each.
- **What decides, in order:** your picks; the two judges, and whether they agree; the cost a verse; the source doubts
  (they point at readings to mend).

## 6. After the pilot

- **The two Āgamas whole** with the engine chosen: about 2,600 passages to send (the dry runs give the numbers).
- **The Batch API (CE3):** half the price, and all at once instead of some 60 hours of calls one after another: drafts
  in one batch, critics in the next, revisions in a third. It is built after the pilot, on the engine chosen.
- **What the credit buys:** at $0.05 a verse (Sonnet in batch, to be measured) some 3,800 verses; at the interactive
  price about half that. The cap stops every run at $190.
- **Next in line:** the Tantrik Texts after its re-ingest (a lexicon: the code-names of letters, seed-syllables and
  gestures); the Ākāśabhairavakalpa after vision OCR; the Śāradātilaka after its ingest.

## 7. Tests

- **`tests/test_claude_engine_2026_10_15.py` (23):**
  - the prices (cache, batch, the long prompt, an unknown model at the dearest), the tokens, the price table by name;
  - the meter (usage_log and usage_totals, not budget_state), the credit (its day, its cap, the expiry, `.env`,
    closed when broken), the CLI (free credit; no probe without the key); two runs numbering one verse at once;
  - the request (no sampling, the effort in output_config, streamed, the thinking left out); the Claude asker (cut off
    and asked with room, a draft asked once more, a refusal not, a failure is CallFailed, compare and judge are
    Gemini's);
  - the systems, the Agamas' rule, the titles, the apparatus, the Hindi; a Claude run (its engine, `+agama-1`, no
    glossary adds); the credit stopping a run; `--held-ok` and the dry run;
  - the head to head: the spans, stale rows and half sentences left out, the judges' answers, blind messages and
    orders, the judges' glossary, a run, the page (blind), the pick;
  - the patcher (all or nothing, once), the files.
- **Follow:** `test_cost_truth_2026_10_15`'s replay chain ends at the `.bak_claude_` copies;
  `test_scholar_2026_10_14`'s file check looks for the `.replace("{title}", ...)` in `system_for`.
- **The suite here:** the 36 failures of before (the PG tests run together, the corner worker's environment), none new.
