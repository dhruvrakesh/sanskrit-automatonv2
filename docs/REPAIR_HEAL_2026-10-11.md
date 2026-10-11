# The repair path, healed; the debris, judged; the Source desk (2026-10-11, evening)

Markers:
- **REPAIR_HEAL_2026_10_11**: `scripts/repair_text.py`, `scripts/ocr_consensus.py`,
  `scripts/translate_passages.py`, `scripts/corpus_sync.py`, `scripts/dashboard.py` and
  `scripts/dashboard_static.html`.
- **SOURCE_DESK_2026_10_11**: `scripts/source_desk.py` (new).

It builds on REPAIR_PATH_2026_10_10 (`docs/REPAIR_PATH_2026-10-10.md`).

## 1. What was reported

On 11 Oct the user reported three things:
- "Repair is not working, as the Agama texts show. The log shows nothing."
- An expert opinion was wanted: does the debris, and the rest of the text, have a material effect on
  what is ingested and translated? It should be shown.
- "Can we have a built-in browser that uses AI to source the best critical or near-critical Sanskrit
  text, from archive.org, wisdomlib and so on, and let the automaton loose on it?"

## 2. What was found (`data/jobs.jsonl`, 18:45-18:57 IST, and the dashboard in the browser)

| Seen | Cause |
|---|---|
| Every *Repair the scan* stopped in one second: Tantric Texts twice (18:45, 18:47) and Ganita (18:48). | `ocr_consensus.py --yes` refuses while the dashboard runs a job for the text ("stop them first"). The repair is itself such a job (kind `repair`), so it refused itself. No vision page was read. The Tantric Texts were then set aside (18:47, 18:48). |
| Karan Aagama: *Use the repaired text* worked. | Re-ingested at 18:51, after a backup. Debris went from 32% to 9%, vision from 0% to 87%; drift 183 of 183 current. 1,603 English and 1,425 Hindi were replaced, as the confirmation said. |
| After Karan's re-ingest, the path stopped. | The text, with no English, fell under *Waiting for a better source*, which had no translate buttons. A *held* note from 18:50 (before the re-ingest) stayed. The next step said "open the Library". |
| "The log shows nothing". | The Log did show the runs (checked in the browser at 19:00). But a repair's verdict read *done* when the job record's 400-character tail had lost the line's start. The Live tab showed only translations, so a running repair or OCR was not seen there. |
| The next mirror run would have changed the site. | Karan's passages are keyed by page and index. They would have gone to the site with the new Sanskrit and no English. Their Hindi rows on the site would then sit beside a changed text. |

The pictures are not lost. They are anchored by page and index (`doc_images.anchor_page`, `anchor_idx`),
not by passage id. A re-segmented page can move an anchor to a neighbouring verse; that is checked in R3.

## 3. The debris, judged (the expert opinion)

The guard counts a verse as debris when any two Latin letters stand in it. That puts four different
things in one number:

| Kind | Example | Effect on the translation |
|---|---|---|
| Furniture | "CC-0 Jangamwadi Math Collection. Digitized by eGangotri"; "Yajur Veda Adhyaya" (repeated on many pages) | None: it is not the text |
| Notes | "This line omitted in ..."; an English index | None on the verse; it is the editor's apparatus |
| Numbering | Roman numerals (XI, VIL, iv) | None |
| Misread letters | "aa", "ON", "TAT", "ee", "fan" where akshara should be | Material: the Devanagari is lost |

`repair_text.py` now separates them. It also measures how far the stored text agrees with vision OCR
(characters, page by page), where vision pages exist. Its levels:
- **cosmetic**: misread letters in under 10% of verses, and vision agreement 0.97 or more. Translate as
  is (`--as-is`); the guard lets it through.
- **moderate**: misread letters in 10-25% of verses, or agreement 0.90-0.97. A translation reads
  through most of it; the critical edition wants the repair.
- **material**: misread letters in 25% or more, or agreement under 0.90. Repair first, or find a
  better source.

On the backup of 10 Oct (read-only), the held texts:

| Text | Guard's debris | Misread verses (letters) | Furniture / notes / numbering | Vision agreement | Judged |
|---|---|---|---|---|---|
| Natyasastra (2015_368408) | 71% | 50% (3.4%) | 0 / 20% / 2% | no vision pages | **material** |
| Tantric Texts (Avalon) | 57% | 46% (5.5%) | 0 / 11% / 4% | 0.777 median, 37 pages | **material** |
| Hayashirsha Pancaratra | 64% | 44% (3.3%) | 0 / 12% / 8% | no vision pages | **material** |
| Karan Aagama (before 18:51) | 32% | 11% (0.9%) | 6.5% (the eGangotri watermark) / 3% / 0 | 0.950 median, 37 pages | **moderate** |

Other findings:
- **Ganita Yukti Bhasa.** It is not held. Its 189 verses below the OCR bar are English front and back
  matter read as Devanagari (an English title page read as Devanagari, with digits inside the akshara), lone dandas and an index. The Sanskrit is done
  (2,374 of 2,706). A repair would buy back English pages. The path now says so and offers
  *Accept as complete*.
- **Karan Aagama, in plain words.** Two-thirds of what held it was the scan's watermark. Its old
  translations were made from a text that agreed with vision OCR on about 95% of the characters. The
  repair was right for a critical edition: about one character in twenty was wrong. It was not
  needed for a readable translation.
- **The A/B test of 3 Oct** (`data/ab_source_quality.json`, Markandeya Purana, 10 pages, judged
  against the vision text) points the same way:
  - on some pages a translation from the better source wins clearly (fidelity 1 to 5, 1 to 4);
  - on most pages it ties;
  - the mean fidelity gain is +1.2.

## 4. What changed

- **`scripts/ocr_consensus.py`.** It looks past the dashboard jobs of the kinds named in
  `SA_CONSENSUS_SELF_KIND`. `repair_text.py --repair` names its own (`repair`); a re-ingest's drift
  check names `repair,repair_use`. A translation or an ingest of the text still stops it.
- **`scripts/repair_text.py`.**
  - It judges the debris (section 3) and prints a `JUDGED:` line, and `ALSO:` lines for the second
    choices.
  - Its new states, in `data/source_verdicts.jsonl` (the latest record of a text is its state):
    - `--as-is "why"`: translate as is;
    - `--accept "why"`: what is left is not to be translated;
    - `--hold ["why"]`: the site keeps its last version;
    - `--release`: publish it again.
  - `--use-repaired` writes *in repair* by itself when it replaces translations, with the counts
    before.
  - `--find-source [--ai]` runs the Source desk.
  - From the dashboard, *Use the repaired text* waits for a vision repair of the same text.
  - The next step after a repair is *Translate it now*.
- **`scripts/translate_passages.py`.** The debris guard lets a text through when its state is
  *translate as is*, and says so in its first line.
- **`scripts/corpus_sync.py`.** A text *in repair* is not compared or sent. The site keeps its last
  version, and the run's *held* list names it. After `--release` the next run sends it whole.
- **`scripts/source_desk.py` (new).**
  - It searches archive.org (texts, by title words, and their spellings without diacritics).
  - For the best six, it reads the item's files and the Devanagari purity of its OCR text (the first
    300 KB).
  - It also looks in the local wisdomlib archive.
  - It gives search links for GRETIL, sanskritdocuments.org, wisdomlib.org and archive.org.
  - It ranks by: the title's words, the marks of a critical edition, scholarly series and publishers,
    Sanskrit as the language, the purity, the pages, and the downloads. It marks "the scan you have",
    from the numbers in the text's code.
  - With `--ai`, one Gemini call (about $0.002, capped, recorded in `usage_log`) says whether each item
    is the same work and whether it is a critical, scholarly or popular edition.
  - `--fetch <identifier> --kind pdf|text` downloads into `sources\<doc>\`, never the inbox, with a
    provenance sidecar. A text is refused under 85% Devanagari.
- **`scripts/dashboard.py`** (on a restart).
  - **The Library:**
    - a repaired text says so, and offers *Translate it now: English, then Hindi*;
    - the states show on the cards (as is, complete, in repair with *Publish it to the site*, set
      aside with *Restore* and *Find a better source*);
    - *Not yet readable* (it was *Waiting for a better source*) lists the texts with no English, each
      with *Finish EN* and *Add Hindi*.
  - **The repair page:**
    - the debris judged, coloured by level;
    - the next step and the second choices as buttons;
    - the **Source desk**: *Find a better source* (with the AI box), the candidates with their reasons,
      *Preview here* (the archive.org reader inside the page), *Fetch the PDF* and *Fetch the OCR
      text*.
  - `POST /api/repair` takes the new steps (`as_is`, `accept`, `hold`, `release`, `find`, `fetch`).
    `GET /api/repair/sources` gives a text's last search.
  - `/api/jobs/running` says each job's mode.
  - A job record keeps its last `VERDICT` and `NEXT` in full.
- **`scripts/dashboard_static.html`** (on a reload). The Log reads a repair's verdict in full. The
  Live tab shows *Running now*: the jobs that are not translations, with their last three lines.

## 5. The enterprise path: from repair to a critical edition

- **R1** (REPAIR_PATH, 10 Oct) and **R1.1** (this): the path works end to end, judges the debris, and
  keeps the site whole while a text is rebuilt.
- **S1, the Source desk** (this): find, preview and fetch a better edition, with the reasons shown.
- **S2, a witness from an e-text.** A GRETIL, sanskritdocuments.org or wisdomlib text ingested as a
  witness of the same work: page JSONL with `ocr_engine = "etext:<site>"`. For wisdomlib,
  `wisdomlib_to_jsonl.py` already does the conversion. No OCR, no cost.
- **S3, the missing page.** For a page that the repair cannot read, the same verses are found in a
  fetched witness. Its OCR text or e-text is searched for the neighbouring verses (by n-grams of the
  akshara), and the passage is offered on the repair page as a reading to accept.
- **R3, the in-place re-ingest.** It keeps the passage ids where page and index match, clears a
  translation only where the source changed beyond a threshold, and re-anchors pictures and stories
  by text. That would have kept most of Karan's 1,603 English.
- **R4, the distillate.** Per passage:
  - the best reading among the witnesses, with its provenance;
  - the best translation by `translation_qa`.

  The corpus publishes that. A passage in repair says so on the site.
- **The site.** "Sources wanted" in the Researchers' Corner: the texts set aside and the Source desk's
  candidates, for a researcher to confirm or suggest an edition. This needs a C14 table, filled by
  the mirror. It is designed, and not built.

## 6. Apply and check

See the RUNBOOK section of DOCS41_2026_10_11 and the commands given with this release. In short:
1. Pause the mirror until Karan Aagama is held: `Disable-ScheduledTask -TaskName SanskritCorpusMirror`.
2. `python scripts\patch_repair_heal_2026_10_11.py --check`, then without `--check`.
3. Hold Karan Aagama: `python scripts\repair_text.py --doc Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi --hold`.
4. Re-enable the mirror: `Enable-ScheduledTask -TaskName SanskritCorpusMirror`.
5. Restart the dashboard when idle. Then translate Karan, restore and repair the Tantric Texts, and
   repair the Natyasastra.

## 7. Tests

- **`tests/test_repair_heal_2026_10_11.py` (28):**
  - the judge (furniture, misread, notes and numbering, vision agreement, what is left);
  - the path end to end: translate as is through the guard; the repair names itself; *in repair*
    after a re-ingest, then release; a hold by hand; no re-ingest during a vision repair of the same
    text; accept as complete; find a source;
  - `ocr_consensus.dashboard_jobs`;
  - a text in repair is not sent by `corpus_sync.py`, and is sent after release;
  - the Library's states and *Not yet readable*;
  - the new steps and their refusals;
  - the sources endpoint and the repair page;
  - the script's next steps, in node;
  - the job record's verdict and the jobs' mode;
  - the dashboard page;
  - the Source desk's words, ranking, search file and purity gate;
  - the patcher (it replays on its backups, and refuses a block that is not the released one).
- **`tests/test_repair_text_2026_10_10.py` (9) and `tests/test_repair_path_2026_10_10.py` (12):**
  updated for the new wording. The DESK_HEAL, LIVE_LOG and corpus_sync tests still pass.
- **The whole suite in the sandbox's partial copy:** the same tests fail with and without the patch,
  for files the copy does not carry. Nothing new fails.
- **By hand, in Chromium against stand-ins, with no script errors:**
  - the Library's cards for the four states;
  - *Not yet readable* with the repaired text;
  - the repair page's Source desk.
