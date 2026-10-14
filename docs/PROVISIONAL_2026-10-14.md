# What is redeemed, marked on the site too; the afternoon of 14 Oct (2026-10-14)

Markers:
- **REDEEM_FIX_2026_10_14:** `scripts/redeem.py`, patched by `scripts/patch_redeem_fix_2026_10_14.py`.
- **PROVISIONAL_EN_2026_10_14:** the Srangam reader, patched by `scripts/patch_srangam_provisional_2026_10_14.py`
  from `docs/srangam/PROVISIONAL_EN_2026-10-14/`.
- **C15_READER_GUARD_2026_10_14:** `docs/cloud/C15_reader_retired_guard_2026-10-14.sql`, with its checks.

It builds on REDEEM_2026_10_14 (`docs/REDEEM_2026-10-14.md`, released `5cf03b0`).

## 1. What the afternoon of 14 Oct showed

- **REDEEM was applied, tested, released and pushed** (`5cf03b0`; local and origin the same).
- **The dashboard was not running** when the jobs were asked for ("Unable to connect"). The last job it recorded
  ended on 13 Oct at 17:09 (the Tantric Texts' Hindi). The OCR it was running stopped with it: the Yoga
  Vasistha has 1,542 of its 1,982 pages read by Tesseract. It was restarted at 15:04, and `/redeem` is up.
- **The re-ingests went in** (`data/reingest/`, 15:05 to 15:10):
  - Karan Aagama: 7 pages; 91 passages out, 6 in, untranslated; no English lost;
  - the Natyasastra;
  - the 12 texts to use the repair;
  - the Upapuranas' pages not yet in: Narasimha, Parashara, Samba, Saura;
  - the Taittiriya Yajurveda: nothing to do.
- **The Tantric Texts were refused:** 6 English and 6 Hindi go with their 145 passages, and the command said
  `--replace 4`. The Hindi translation had reached those pages since the chart. They are still on the site.
- **The mirror** sent 4,810 passages and retired 153. It held two things:
  - **the two texts in repair** (Karan, the Hayashirsha), as it should: the site keeps their last version until
    `--release`;
  - **a retire it holds for a person to confirm:** every mention and vector of seven re-ingested texts (the
    Amoghanandini and Bharadvaja Shikshas, the Apastamba, Daksha, Brihaspati, Atri and Yama Smritis), and
    the Brihaspati's 6 Hindi rows. Each was all of that text's rows, which is right after a re-ingest.
- **The ledger at 15:13:**
  - 23,264 English in 40 texts; 19,168 kept (82%); 4,062 made from misread Sanskrit (17%); 34 judged wrong;
  - 5 redeemed, 8 mostly, 24 to translate again, 2 a source first, 15 replaced by a better reading, 1
    withdrawn;
  - $30.59 spent on the texts here: $7.39 of it on English that cannot be kept as it is, and $2.95 on English a
    better reading replaced. Translating those again costs about $3.56.
- **The chart at 15:13:**
  - 17 to translate, about $7.71: the Natyasastra (2,958 passages, $3.35), MBh01's Hindi ($3.84), the 12
    small texts, the Tantric Texts;
  - 2 in repair, $3.87: Karan $2.10, the Hayashirsha $1.77;
  - 3 to translate again, $0.03 (T2);
  - 34 scans to repair, about $24.41 (from $15.01 at the median text's price, up to $39.22);
  - 6 sources to find; 4 to OCR (the Yoga Vasistha, the Gandharva Veda, and two single PDFs).
- **The site (Lovable SQL, 16:20):**
  - 63 texts, 96,643 live passages, 24,245 English;
  - Karan's last version: 1,603 English, 404 of them made from misread pages; the Hayashirsha's: 158 English, 76
    of them so;
  - `corpus_reader_page` and `corpus_reader_outline` do not return the reading's engine.
- **`repair_text.py --release`** refused both texts in repair, as it should: their translation is not back.
- **Two faults found:**
  - `redeem.py --doc Mallapurana` printed "$30.33 was spent on texts no longer in the database". With
    `--doc`, the count holds one text, and every other text's spend was taken for gone;
  - the reader's meaning search (`corpus_reader_match`, "Ask the corpus"; `corpus_reader_similar`, "similar
    passages") takes the nearest live vectors and does not ask whether their passage is retired. While the
    mirror holds a vector, a question can be answered with a retired passage's English.

## 2. What this release does

- **REDEEM_FIX_2026_10_14:** "no longer in the database" is a text missing from `docs`, or retired, whatever is
  counted. With `--doc`, that corpus line is not printed. The full count is unchanged.
- **PROVISIONAL_EN_2026_10_14 (Srangam):**
  - **The chip:** a passage whose English was made from a misread reading gets a small "provisional English"
    chip, with its reason. About this passage says the same.
  - **The test:** the automaton's own: eight or more Devanagari signs and a Latin word among them, as
    `redeem.py` and `repair_text.JUNK`. So the site and the ledger agree.
  - **What it touches:** both readers. No database change; nothing stored is changed.
  - **Load:** the change is in the reader's shared chunk (about 14.7 kB); the entry is unchanged.
  - **Not marked:** a clean verse; a verse without English; the book's own English; a single stray letter.
- **C15_READER_GUARD_2026_10_14 (Lovable SQL, optional, one paste):**
  - in those two functions, the one join line gains `AND p.retired_at IS NULL`;
  - each is rewritten from its own live definition. If that line is not there exactly once, nothing is changed;
  - owner, grants, SECURITY DEFINER and search_path are kept. Rollback in the file;
  - tested on PostgreSQL 16 with C5's functions: before, the retired passage's English came back; after, it does
    not. Re-running changes nothing; the rollback gives back C5's text exactly; a changed function is refused.
  - The checks file asks first how many live vectors sit on retired passages, or on passages with no English
    (L1, L2).

**Tests:**
- Automaton: `tests/test_provisional_2026_10_14.py` (7), with `tests/test_redeem_2026_10_14.py` (21).
- Srangam: `src/__tests__/reader-provisional.test.tsx` (4). With the readers' own tests, 27 pass; typecheck and
  build pass. The full suite in the sandbox: 193 pass; the one failure, `meta-freshness`, fails without this
  change too.

## 3. Where every text stands, and what is next

| Step | What | Cost |
|---|---|---|
| 1 | The Tantric Texts: `reingest_pages.py ... --apply --replace 6`; then the mirror | free |
| 2 | The mirror, for the seven texts it held: `corpus_sync.py --doc ... --allow-mass-retire` (the plan first) | free |
| 3 | C15 in Lovable (L1, L2, P1 first); V1 after | free |
| 4 | Release this; the Srangam patch, its tests and build; push both repos | free |
| 5 | OCR the Yoga Vasistha's other 440 pages, then ingest it | free |
| 6 | T2: the 18 passages the judge marks | about $0.03 |
| 7 | Translate what the repairs gave: the Natyasastra, Karan, the Hayashirsha, the 12 small texts, the two Dhanur Vedas, the Tantric Texts. Then `--release` Karan and the Hayashirsha, and run the mirror | about $7.73 |
| 8 | MBh01's Hindi | about $3.84 |
| 9 | Repair the 34 scans; then translate again what was made from debris | about $24.41, then about $1.9 |
| 10 | A better source for the 6 texts the chart names (a person fetches the files) | - |
| 11 | Srangam S2: the reading's engine on each verse. This needs a new read-only reader function, because `corpus_reader_page` does not return it and changing its return type would break the reader. Then S3: each text's verdict on its card | free |
