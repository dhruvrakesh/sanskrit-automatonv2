# Empty translations of valid Sanskrit: causes, fix, and the outcome ledger

MARK `TRANSLATION_FILTERS_2026_09_27`. This document goes with `scripts/patch_translation_filters.py`, `scripts/diag_empty_translations.py`, `scripts/probe_empty_translations.py`, `scripts/remediate_hi_artifacts.py` and `tests/test_translation_filters.py`.

## 1. What "empty" means on the dashboard

The translate panel shows `[empty]`, and its `skip` counter adds four different things together:

| Printed as | Meaning | Paid? |
|---|---|---|
| `[SKIP-UI]` | A row id the user put on the skip list | no |
| `[SKIP-QUALITY]` | `quality_score` is above 0 and below `--min-quality` (0.35) | no |
| `[SKIP-JUNK]` | The model answered, and `salvage_translation` threw the whole answer away | yes |
| `[SKIP-ECHO]` | The model answered, and `is_source_echo` judged it to be the source | yes |
| (none) | The model returned nothing: a safety, recitation or no-text finish, a failure after 3 retries, or — before this patch — the budget cap | yes |

A verse that ends empty is written back as `''`, so the next run tries it again. It is never cached.

Before this patch, the raw model output behind the three paid-but-empty cases was thrown away. That meant nobody could tell a correct refusal from a filter false positive.

## 2. Causes found (2026-09-27)

All of these were measured or reproduced. None is assumed.

1. **Refusal phrases that are ordinary language.**
   - `JUNK_PHRASES` / `_CAVEAT_EXTRA` are substring tests over the whole output. A match with no complete sentence before it empties the whole verse.
   - English: *vākyaśeṣa* is correctly rendered "the remainder of the sentence", and that matches the caveat "the remainder of". The same goes for "I am sorry", "cannot identify" and "the rest of the text".
   - Hindi: "यह पाठ", "शेष पाठ", "स्पष्ट नहीं", "क्षमा कर" and "मैं असमर्थ" are all normal in commentary and narrative.
   - The test fixtures reproduce each case. Aphorisms of Śāṇḍilya p64.8 (`इतिवाक्यशेषे…`) is empty in English and fits this cause. The probe is what confirms it for a given verse.
2. **A copied citation read as an echo.** The English echo test marks an output as an echo if it contains *any* Devanagari digit. Śatapatha and Aphorisms commentary cite as `( मा. श. प. ब्रा. ७ । २ । १ । २४ )` or `(विष्णुपु०१अ०१७श्लो०५८)`. If the model keeps that citation verbatim, the whole translation is emptied. Aphorisms p77.6 is valid verse: its English is empty while its Hindi is present.
3. **The Hindi hard-fail token was stored.**
   - The Hindi prompt asks the model to output exactly `[अस्पष्ट]` for illegible text. Nothing filtered that token, so it was stored, cached and printed as a translation.
   - Its English twin `[ILLEGIBLE]` was always emptied.
   - This is one reason Hindi counts run ahead of English. The larger reason is that `translate_passages.py` translates sa→hi directly by default; `HINDI_TRACK_DESIGN` rule D1 applies only with `--require-anchor`.
4. **The Hindi prompt invented a speaker.** Rule 7 gave "वैशम्पायन ने कहा —" as its example. Ten of the 450 Aphorisms Hindi units open with it, and the Sanskrit never names Vaiśampāyana.
5. **A capped budget produced silent empties.** When the cap was reached, `translate_batch` returned `''` for every verse. `translate_passages` counts that as untranslatable source, so it walked the whole queue and then reported `Done`.

## 3. The fix

The fix is surgical: 3 files, 16 anchored edits, all-or-nothing, with a backup of each file first.

- **`text_filters.py`**
  - An *ambiguous* phrase counts only when the sentence it sits in also talks about the input: OCR, legibility, the text supplied, translating it, or the like. Every other phrase still counts anywhere, and a test proves that for each one.
  - An output that is nothing but `[अस्पष्ट]` is now empty. The token *inside* a translation is a lacuna mark and is left alone.
  - A bracketed Devanagari citation, or a daṇḍa-verse number, is set aside before the echo test.
- **`infer_mt.py`**
  - `BudgetBlocked(QuotaExhausted)` now aborts the run with the reason, instead of returning empties.
  - Hindi rule 7 now gives a speaker line only when the Sanskrit itself has one.
  - `PROMPT_VERSIONS['hi']` is now `hi-v2-2026-09-27`. That changes every Hindi cache key; English keys are byte-identical.
- **`translate_passages.py`**
  - Every empty or salvaged paid result is appended to `data/translate_outcomes.jsonl`. Each record carries its cause (`model-empty`, `refusal-filter`, `echo-filter` or `salvaged`), the raw output and the source.
  - The run prints `[EMPTY:<cause>]` for each such verse and a per-cause total at the end.

The Aphorisms of Śāṇḍilya rows (453 English, 450 Hindi) were replayed through the old and new filters. The patch changes **no stored English row**, and the only rows it would now reject are the 5 Hindi rows that are nothing but `[अस्पष्ट]`. For the whole corpus, see section 3 of `diag_empty_translations.py`.

## 4. Existing rows

`remediate_hi_artifacts.py` handles the two artefacts already in the data. By default it only reports.

- A Hindi row that is only `[अस्पष्ट]` is archived to `translation_history` (reason `bare-illegible-token-2026-09-27`) and then removed, so the next `translate_hi` run tries it again.
- For a Hindi row that opens with the invented speaker, the old row is archived (reason `invented-speaker-strip-2026-09-27`) and only that opening phrase is removed.

The apply step needs a backup, runs in one transaction and prints the SQL that reverses it. It touches no English, no `mt_cache` and no `passages` row.

## 5. Operating rules

- Run `diag_empty_translations.py` (read-only) before and after any change to `text_filters.py`. Its section 3 must not show a stored English row newly rejected.
- `probe_empty_translations.py` costs about $0.0002 per verse and records that spend through `usage_meter`. It is the only way to learn why a particular verse came back empty.
- Running jobs keep the code they imported. The patch applies to jobs started after it.
- Do not use `purge_empty_cache.py --yes` casually: it runs `VACUUM`, and RETIREMENT_AND_BACKUP_POLICY §6 says never to. It is not needed here, because empties are not cached and the Hindi version bump already retires the old Hindi keys.

RUNBOOK §3g is a short pointer to this document.

## 6. Second pass, from the live corpus (TRANSLATION_FILTERS2_2026_09_27)

Measured by Block AY on the live database:

- **Replay of every stored translation.** 18,481 English rows are unchanged. One row loosened: id 37517, a real sentence that the old filter had emptied. One row tightened: id 12574, which contains no English at all. The only Hindi rows affected were the 1,157 that are nothing but `[asphuta]`.
- **Remediation.** The 1,157 bare-token Hindi rows were archived and removed. The invented "Vaisampayana said -" opening was stripped from 35 rows: Shatapatha 20, Aphorisms 10, nirukta 3, nilamata 2.
- **Paid probe of 12 verses.**
  - Shatapatha p297.12 ("the remainder of the sutra") was emptied by the old filter and is kept by the new one.
  - Shatapatha p131.2 and p251.3 came back as complete, faithful translations with one `[ILLEGIBLE]` where a word is damaged. The first-pass filter still emptied them, because "illegible" is a refusal phrase.
  - Seven of the 12 answers were the bare `[ILLEGIBLE]` token. Four were on the errata apparatus (now frontmatter) and one on garbled OCR, but two were on largely legible Brhadaranyaka text in the Shatapatha (p194.4, quality 0.91; p139.4, quality 0.89).

What changed in the second pass:

- **Filter.** A lacuna token *inside* a translation is a mark, not a refusal; only an output that is nothing but the token is left empty.
- **Prompts.** English rule 12 and Hindi rule 10 now allow the bare token only when no part of the text can be read; otherwise the model translates what it can and marks the gap. The prompt versions are now `v3-2026-09-27` and `hi-v3-2026-09-27`. That changes the cache keys, but rows already translated are never requested again, so nothing is billed twice.
- **Dashboard.** `/api/translate` accepts an optional `until_page`. `plan_empty_retries.py` (read-only) uses it to plan retries that cover only the verses a run has already passed.
- **Library.** A build made in audit mode is now labelled "audit proof PDF".

## 7. Decision: Hindi is translated directly from Sanskrit (2026-09-27)

For fidelity, Hindi is translated straight from the Sanskrit. A QA-passed English translation, where one exists, is passed to the model only as a meaning reference. This supersedes rule D1 of HINDI_TRACK_DESIGN_2026-08-01 ("Hindi only where English exists and passed QA"). `--require-anchor` restores the old gating for any run that needs it.
