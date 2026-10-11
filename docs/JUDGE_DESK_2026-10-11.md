# The debris judged, shown where it is needed; Sources & repairs (2026-10-11, night)

Marker: **JUDGE_DESK_2026_10_11**, in `scripts/repair_text.py`, `scripts/dashboard.py` and
`scripts/dashboard_static.html`. It builds on REPAIR_HEAL_2026_10_11 (`docs/REPAIR_HEAL_2026-10-11.md`).

## 1. What the evening showed (19:41-20:01 IST)

- **The heal patch was applied, the dashboard restarted, and `/api/repair` answers.** It shows
  `heal: REPAIR_HEAL_2026_10_11`, with the steps `as_is`, `accept`, `hold`, `release`, `find` and
  `fetch`. The release went to `79aedee`.
- **Karan Aagama was held, and the plan showed it held.** The mirror plan said "HELD: ... in repair:
  not compared or sent". Then, at 19:47:36, `--release` was run before the text was translated again.
  The register's latest record said *released*, and the next mirror run (20:31) would have sent it
  without its English. **It was held again at 19:54:12**, with the counts from before the re-ingest
  (1,603 English, 1,425 Hindi). `--release` now refuses until the translation is back (section 2).
- **The repair works.**
  - `ocr_consensus.py` saw "no jobs for tantric_texts_series_edited_by_arthur_av". The vision step
    queued 212 pages, found 140 done and ran the 72 left (estimate $0.115 at $0.0016 a page).
  - By 20:01 there were 143 vision pages, about one every 17 seconds. One page took longer: the
    MAX_TOKENS ladder, then a DeadlineExceeded retry; `ocr_vision.py` handles both.
  - The Natyasastra, Hayashirsha and Ganita steps follow in the same PowerShell chain.
- **The tests did not run:** `C:\Python313\python.exe: No module named pytest`. The tests are unittest
  files: `python -m unittest ...` runs them without pytest (section 4).
- **The Library on the live data** (checked in the browser):
  - it is 102 KB and builds in 0.8 s;
  - 15 repair bars;
  - *Not yet readable* lists the Natyasastra, Karan Aagama and Siddhanta Shiromani;
  - Karan shows *In repair* and *Repaired: Translate it now*.

  The debris judged showed only on the repair page, after an assessment. That is what is fixed here.

## 2. What changed

- **`scripts/repair_text.py`:**
  - Every assessment is cached in `data/source_judged/<doc>.json`. The cache holds the level, the four
    kinds, the vision agreement, the verdict and the next step, the state, and the counts.
  - `--judge-all` judges every text with untranslated passages or a state in the register (read-only),
    caches each, and sums them up.
  - `--release` refuses while English is under 95% of what the text had before its re-ingest, or Hindi
    is under 95% (or, held after the re-ingest, under 90% of the passages). `--force` publishes anyway.
- **`scripts/dashboard.py`** (on a restart):
  - **The Library's cards.** Each shows one line: "Debris judged MATERIAL (date): misread letters in
    50% of verses; vision agreement 0.78". It is coloured by level. It appears under the notes of a
    text the scan stopped, a text with a state, or a text whose debris is not cosmetic. The
    texts in *Not yet readable* show it too.
  - **`/sources`, Sources & repairs.** It lists, in one place, every text that is held by the guard,
    stuck below the OCR bar, judged moderate or material, or in the register. For each it shows:
    - its English and Hindi;
    - its state;
    - the debris judged;
    - what is next;
    - the best edition the Source desk found (or "not searched").

    It has *Find a better source* per text, and *Judge the texts again* for all of them. Held texts
    come first, then material, moderate, cosmetic. It reads small files only, never the database.
  - The repair page shows the same line.
  - `POST /api/repair {"step": "judge_all"}` runs `repair_text.py --judge-all`.
  - The Library's header links to *Sources & repairs*.
- **`scripts/dashboard_static.html`** (on a reload): the header links to *Sources*.

## 3. The expert opinion, as it now stands

The levels and their evidence are in `docs/REPAIR_HEAL_2026-10-11.md` section 3:
- the Natyasastra, Tantric Texts and Hayashirsha are **material**: Devanagari read as Latin in 44-50%
  of verses;
- Karan Aagama was **moderate**: two-thirds of its debris was a watermark, and it agreed with vision
  OCR on 95% of characters;
- what is left of Ganita is not Sanskrit.

After a repair, the same assessment measures the text again. A repaired text that goes in should
read: debris under 10%, vision over 80%, nothing held.

## 4. The enterprise path (where this sits)

- **Done:**
  - R1 (the repair path);
  - R1.1 (healed);
  - J1 (the debris judged), now J1.1 (shown on the cards; Sources & repairs);
  - S1 (the Source desk).
- **S2, an e-text as a witness. Next, once a first text is fetched.** A GRETIL, sanskritdocuments.org or
  archive.org OCR text becomes the page JSONL that `ingest_jsonl_fast.py` reads, as a separate text
  (`<doc>__w_<source>`, `ocr_engine = "etext:<site>"`). For wisdomlib, `wisdomlib_to_jsonl.py` does this
  already. Pages are split by the file's own page marks where it has them (to be checked on the first
  fetched file, not assumed).
- **S3, the missing page.** For a page the repair cannot read, its neighbouring verses are found in a
  witness (by n-grams of the akshara), and that witness's passage is offered on the repair page as a
  reading to accept. Local only, as the translation engine is local.
- **R3, the in-place re-ingest.** It keeps passage ids, clears only the translations whose source
  changed, and re-anchors pictures and stories by text.
- **R4, the distillate.** Per passage, the best reading among the witnesses and the best translation,
  each with its provenance.
- **C14, Sources on the site.** A table in schema corpus, filled by the mirror from
  `data/source_judged` and `data/source_desk`:
  - per text: the level, the misread share, the agreement, the state, the next step, and the best
    edition (title, link, score);
  - readable by researchers and admins, through the same role check as the Corner;
  - shown in the Researchers' Corner as *Sources wanted*, where a researcher can confirm an edition or
    suggest one.

  It needs a migration in the SQL editor, the `corpus-ingest` function to accept the new table, and a
  Corner panel. The function and its schema are read first, before any of it is written.

## 5. Tests

- **`tests/test_judge_desk_2026_10_11.py` (11):**
  - an assessment is cached;
  - `--judge-all` leaves out retired texts and judges a text with a state;
  - `--release` waits, and `--force` publishes;
  - the folder is read;
  - the cards' line, and no line for a cosmetic text nothing stopped;
  - `/sources`: held and material first, the best edition (not the scan you have), its script parses;
  - `judge_all` needs no text;
  - the repair page;
  - the dashboard's link;
  - the patcher replays on its backups.
- **`tests/test_repair_heal_2026_10_11.py`:** updated, since release now waits for the translation.
- **The whole suite in the sandbox's partial copy:** nothing fails that did not fail before.
