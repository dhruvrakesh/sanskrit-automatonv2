# Parking lacuna-only verses; Srangam display titles (2026-09-27)

Markers: `PARK_ILLEGIBLE_2026_09_27` (text_filters.py, translate_passages.py,
plan_empty_retries.py) and `PUBLISH_TITLE2_2026_09_27` (publish_srangam.py).
Patch: `scripts/patch_park_title.py`. Tests: `tests/test_park_title.py`.

## 1. Why parking

The ledger `data/translate_outcomes.jsonl` records the raw answer of every paid
call that ends empty. On 2026-09-27 (15:35 IST) it held 62 records:

| doc | lang | cause | n |
|---|---|---|---|
| Bodhicaryavatara | en | refusal-filter | 45 |
| 2015_405693_Shatpath-Brahmanam | en | refusal-filter | 7 |
| Karan_Aagama... | en | refusal-filter | 7 |
| AphorismsOfSandilya | hi | echo-filter | 3 (fixed by FILTERS3) |

All 59 refusal-filter answers are **only** the lacuna token (`[ILLEGIBLE]`,
sometimes with `//` or a verse number). The source behind them is mixed
Latin/Devanagari OCR noise (Bodhicaryavatara p39: `SATAN ANS IAN SAS ...`). The
filter is right to store nothing. But `plan_empty_retries` counts every such
verse as a retry, so each new plan pays for the same answer again. That is not
a lot of money (about $0.0002 a verse), but it is endless, and it keeps
re-OCR work hidden inside the translation queue.

## 2. The rule

A verse is **parked** when all of the following are true:

- The ledger holds at least `--park-after` records for it (default 2).
- Each of those records has cause `refusal-filter`.
- Each raw answer is lacuna-only: the tokens `[ILLEGIBLE]` / `[asphuta]` / `[?]`, plus punctuation, verse numbers and whitespace.
- The records are for the same language, under the **current** prompt version.
- The records are for the **same** cleaned source text (the ledger's `source` field).

Parked verses are skipped:

- `translate_passages` prints `[PARKED] n verse(s) skipped` and repeats the count in its summary.
- `plan_empty_retries` leaves them out of the retries and lists them per document under "parked - re-OCR these". The JSON plan carries a `parked` map.

Nothing in `context.db` is written or deleted. A verse leaves the parked set
by itself when:

- **the prompt version changes.** Every ledger record now carries `prompt`. Older records without it count as current only if they were written after `2026-09-27T07:16:04Z`, the moment the v3 prompts went live in `infer_mt.py`.
- **the source text changes**, for example after re-OCR or a manual fix.
- **you ask for it.** `translate_passages --retry-illegible` or `plan_empty_retries --include-parked` switches parking off for that one run.

## 3. Srangam titles

`srangam_texts.title` was the raw doc code (`AphorismsOfSandilya`). The title
is now chosen in this order:

1. `publish_srangam.py --title "..."`;
2. the Booksmith edition's `projects/<slug>/book.yaml` `title:` (the curated
   one, set with `block_AX -SetTitle`), ignoring scan-id titles like
   `2015 405693 ...`;
3. `doc_title()`, which now also splits CamelCase.

On re-upsert, `00_text.sql` overwrites the site title **only** when `--title`
is given. A title corrected in the Lovable SQL editor therefore survives every
later re-emit. `MANIFEST.txt` names the title and where it came from.

## 4. Operating it

```
python scripts/plan_empty_retries.py --db data/context.db            # shows parked per doc
python scripts/translate_passages.py --doc X --retry-illegible        # ask parked verses anyway
python scripts/publish_srangam.py --doc X --emit-sql DIR --title "..." # set/replace the site title
```

Undo: copy each `*.bak_pk_20260927` back over its file.
