# An e-text as a witness; the missing page offered (2026-10-11, late night)

Marker: **ETEXT_WITNESS_2026_10_11**, in:
- `scripts/etext_witness.py` (new);
- `scripts/repair_text.py`, `scripts/corpus_sync.py`, `scripts/source_desk.py` and `scripts/dashboard.py`
  (patched by `scripts/patch_etext_witness_2026_10_11.py`);
- `.gitignore`.

It builds on JUDGE_DESK_2026_10_11 (`docs/JUDGE_DESK_2026-10-11.md`). It is the Source desk's S2 (an
e-text as a witness) and S3 (the missing page, offered on the repair page), and judge v2.

## 1. What the evening showed (20:11-21:47 IST)

- **The judge desk is applied and released** (`0e352ff`). `python -m unittest` ran 109 tests: OK.
- **`--judge-all` judged 47 texts:**
  - 24 material, 11 moderate, 12 cosmetic;
  - 32 held by the guard.
- **Two of the verdicts were not exact.** Both are fixed here (judge v2, section 3).
  - *Shatpath Brahmanam* was called material on the strength of two vision pages.
  - *upapurana_saura* is cut into a passage a page. That hid its misread letters under the 3% a verse
    that counts a verse as misread.
- **The repair chain** (read on the PC at 21:17 and 21:47 IST, read-only):
  - **Tantric Texts:** 210 vision pages and 212 repaired pages. It is ready for *Use the repaired text*;
    it has nothing translated to lose.
  - **Natyasastra:** 0 vision pages. Its queue (546 pages) was written at 20:45, but no page was read
    and no manifest was written. That is the vision meter's spending cap refusing before it spent. The
    repair says the cap it needs when it refuses.
  - **Hayashirsha:** 92 of 189 vision pages at 21:46. The pages come more slowly than the Tantric
    Texts' did; one page stood for about eight minutes at 21:09 and then went on.
  - **Karan Aagama:** in repair since 19:54. The site keeps its last version (1,603 English, 1,425
    Hindi). It is to be translated, then published.
  - **The Source desk** has not been run yet (`data/source_desk` does not exist).

## 2. What is built

### `scripts/etext_witness.py`

A Unicode text from GRETIL or sanskritdocuments.org, or an archive.org OCR text (`_djvu.txt`), becomes
a text of its own: `<doc>__w_<site>`.

- **It reads:**
  - HTML or plain text;
  - in Devanagari, IAST (and ISO 15919), Harvard-Kyoto, Velthuis or ITRANS. `--scheme` names the
    script; otherwise it is detected, and a file whose script cannot be told is refused.
- **English lines are dropped and counted:** headers, licences and notes.
- **Lines are grouped into verses.** A verse ends at its double danda or its reference:
  - `BhG_1.1`, `// 1.1 //`, `|| 12 ||` and the Devanagari numerals;
  - pada references (`1.1a`, `BhP_01.01.001/1`) keep one verse together;
  - `।।` typed for `॥` is read as `॥`.
- **Romanized text is put into Devanagari** with `indic_transliteration`, as `import_mbh_gretil.py`
  does. `/` and `//` become the dandas. Compound hyphens are joined; `ṁ` is read as the anusvara and
  `'` as the avagraha.
- **Its pages:**
  - an archive.org OCR text keeps the pages its form feeds mark, and is segmented at ingest;
  - an e-text is cut into pages of `--per-page` verses (20 by default), and a page never crosses a
    chapter.
- **It is measured against the scan, page by page.** The scan is the text's passages in the database,
  read-only.
  - Both are reduced to their consonants, a nasal before a consonant read as the anusvara. So sandhi
    spacing (*kim akurvata*, *kimakurvata*), *saṃjaya* beside *sañjaya*, the vowel signs and most OCR
    slips do not count. Six-letter n-grams of that skeleton are compared. On the Gita's first verses,
    GRETIL's IAST against sanskritdocuments.org's printed Devanagari, 87% of the n-grams agree.
  - A page is *read* when 30% of its n-grams are in the witness, or 30% of the witness's verses found
    there are on the page. The second condition is what lets a page with commentary around its
    verses be read.
  - A page is *readable* when it has at least 60 Devanagari letters and under 30% of its letters are
    Latin.
  - The result says:
    - how many readable pages the witness reads;
    - whether in the scan's order;
    - which of the witness's verses the scan covers;
    - an opinion: the same work in the same order (60% read, 80% in order); in part, or another
      recension (25%); or not the same text.
- **The missing page.** For each page the scan cannot read, the witness offers the verses between the
  nearest pages it does read on either side (up to five pages apart). That is each page that is:
  - absent from the database;
  - unreadable;
  - or readable but not found, between two pages that are.

  A gap of several pages is shared among them by verse count. A share too long for one page is not
  offered as text.
- **`--page N`** prints the witness's reading of page N of the scan.
- **`--url`** fetches a file into `sources\<doc>\`, with its provenance beside it. The hosts allowed
  are GRETIL, sanskritdocuments.org, archive.org and raw.githubusercontent.com; `SA_ETEXT_HOSTS` adds
  more. An archive.org *details* page is sent to `source_desk.py --fetch <id> --kind text`, which gates
  on Devanagari purity.
- **`--write`** writes:
  - `data/raw_witness/<witness>/<witness>_NNNN.jsonl`, with engine `etext:<site>` (`etext:archive-ocr`
    for an archive.org OCR text), the verse reference, the chapter, the text type, and quality 0.95
    for an e-text;
  - `witness.json` (provenance, sha256) and `align.json` (each page of the scan, and the offers);
  - a line in `data/witnesses.jsonl`;
  - the register's record `witness`.

  It refuses:
  - a file whose verses are more than 10% Latin letters (a wrong scheme);
  - a witness that reads under 10% of ten or more readable pages, unless `--force`;
  - a second witness of the same name, unless `--force` (which keeps the first as `.bak_<stamp>`);
  - a witness that is already in the database, since rewriting its pages would leave its translations
    beside a different text.
- **`--ingest`:**
  - it waits for the dashboard's database writers;
  - it makes a backup (`db_backup.py`, `D:\backups\context_pre_witness_<witness>_<stamp>.db`);
  - then `ingest_jsonl_fast.py --source given` runs, with `--no-segment` for an e-text, under the
    scan's category.

  The scan is not touched.
- **`--list`** lists the witnesses and their states.

### `repair_text.py --release`

A witness waits for its translation, by the rule for a text held after its re-ingest. It refuses
while fewer than about 86% of its passages have English, or about 77% have Hindi (95% of 90%, and of
90% of that). `--force` publishes it as it is. A witness that is not yet in the database is refused,
with the ingest command.

### `corpus_sync.py`

A text whose latest record in the register is `witness` is not live:
- it is not mirrored;
- its pictures and the Corner's requests are not either (`corpus_media.py` and `corner_worker.py`
  read the same `live_docs`).

It is mirrored once released.

### `source_desk.py`

A fetched OCR text's next step is `etext_witness.py --doc <doc> --file "<file>"`.

### `dashboard.py` (on a restart)

- **The repair page's Source desk:**
  - lists the files fetched into `sources\<doc>\`, with *Read it as a witness (free)*. A PDF says to
    import it as its own text and OCR it with vision;
  - takes a pasted e-text link (*Fetch it and read it as a witness*);
  - shows each witness: how much of the scan it reads and in what order, its opinion, and its state
    (*local only*, *adopted*), with these steps:
    - *Ingest it as its own text* (a database writer: it waits for the translate lock);
    - then *Translate it* and *Adopt it: publish it to the site*;
  - shows the pages the scan cannot read, each as the witness reads it (folded, page by page).
  - Every step's NEXT is a button: *Read it as a witness*, *Make it a witness*, *Ingest the witness*.
- **The Library's card of a witness** says what it is and that the site does not have it until it is
  adopted. It offers *Translate it now* and *Publish it to the site*. Its untranslated passages put it
  in *Not yet readable*.

### `.gitignore`

`data/raw_witness/` and `data/source_judged/` stay local. Both are made again on demand, and
`source_judged` changed on every run. `data/witnesses.jsonl` is committed, as the register is.

## 3. Judge v2 (`repair_text.py`)

- **A page vision failed on is not counted as a disagreement.** That is:
  - a page whose engine says `fallback` (the merge kept Tesseract);
  - a vision page under half the length of the stored page.
- **The vision agreement sets the level only when at least five pages were compared.**
- **For a text cut into long passages, the share of all letters misread counts.** A passage is long
  at 600 letters or more on average. There 2% is material and 1% is moderate.
  - On the 47 texts judged, where 25% of verses are misread, 2.0-2.5% of the letters are.
  - The rule is not used for verses. At 1.5% of letters, ten of the eleven texts judged moderate by
    their verses, and three judged cosmetic, would have become material.
- **`--judge-all` prints each kind:** misread verses, misread letters, furniture and notes.

## 4. The expert opinion on a witness, and its limits

- **The measure says whether pages correspond, not which reading is right.** Two editions of one
  work differ in readings, and both are read as the same work.
- **Where the witness offers a page, its verses come from between the scan's neighbouring pages.**
  Read it beside the scan before taking it: at a page's edges a verse or two can belong to the
  neighbour.
- **Taking an offered reading into the scan's passages is not built.** It is R3, the in-place
  re-ingest that keeps passage ids. Until then a witness is used whole, as its own text.
- **The thresholds (30% read, 10% touched) were set on synthetic texts.** The first real GRETIL file
  is their calibration; the numbers on its preview say whether they hold.

## 5. The path (where this sits)

- **Done:**
  - R1 (the repair path) and R1.1 (healed);
  - J1 and J1.1 (the debris judged, now v2);
  - S1 (the Source desk);
  - **S2** (an e-text as a witness);
  - **S3, offered** (the missing page, shown on the repair page).
- **Next:**
  - **R3, the in-place re-ingest:**
    - it keeps passage ids;
    - it clears only the translations whose source changed;
    - it takes an offered reading for one page;
    - it re-anchors pictures and stories by text.
  - **R4, the distillate:** per passage, the best reading among the witnesses and the best
    translation, each with its provenance.
  - **C14, Sources on the site:** a `corpus` table filled by the mirror from `data/source_judged`,
    `data/source_desk` and `data/witnesses.jsonl`. It is shown in the Researchers' Corner as *Sources
    wanted*. It needs:
    - a migration in the SQL editor;
    - the `corpus-ingest` function's `TABLES` whitelist;
    - a builder in `corpus_sync.py`;
    - a Corner panel.

## 6. Tests

`tests/test_etext_witness_2026_10_11.py` (23):

- **Reading:**
  - GRETIL IAST HTML: references, the speaker's line, the colophon, the header dropped;
  - Devanagari with its numerals and `।।`;
  - pada references;
  - an archive.org OCR text's pages;
  - Harvard-Kyoto, and a script it cannot tell.
- **The measure:**
  - the missing pages are offered from their neighbours, exactly, for unreadable, Latin and absent
    pages;
  - a page with commentary is still read;
  - GRETIL's IAST against a printed Devanagari edition (87% agree);
  - another text is not a witness;
  - what is readable.
- **The tool end to end:**
  - the preview writes nothing;
  - `--page`, `--write`, and refusing to write twice;
  - the release refuses before the ingest;
  - `--ingest` with the real `ingest_jsonl_fast.py` and `db_backup.py` on a temp database: 400
    passages, `etext:` engine, the scan's category, the scan untouched;
  - refusing to rewrite an ingested witness;
  - the release waits, then `--force`;
  - `--list`;
  - another text is refused unless forced;
  - fetching from a listed host only (a local server stands in).
- **Judge v2:**
  - letters misread count in long passages only;
  - two vision pages are not a measurement;
  - a page vision failed on is no disagreement.
- **The mirror** leaves a witness out until it is released; the Source desk's next step.
- **The dashboard:**
  - the witness step (file, write, url, ingest under the translate lock, bad input);
  - the Source desk's answer;
  - the repair page and its script (node);
  - the NEXT lines read as buttons;
  - the Library's card of a witness.
- **The patcher** replays on its backups, all or nothing, keeping the line endings of `.gitignore`;
  the files are ASCII.

Also changed:
- `tests/test_repair_heal_2026_10_11.py` and `tests/test_judge_desk_2026_10_11.py`: their patcher
  replays compare with this patch's backups.
- **In the sandbox's partial copy, the whole suite fails in the same 44 places before and after this
  patch.** Those are modules that are not in that copy; it has 23 more tests, all passing.
