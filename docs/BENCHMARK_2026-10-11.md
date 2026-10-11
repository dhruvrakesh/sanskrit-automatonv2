# The readings benchmarked: where the automaton improved the text and its translation (2026-10-11, night)

Marker: **BENCHMARK_2026_10_11**, in:
- `scripts/benchmark_sources.py` (new);
- `scripts/repair_text.py`, `scripts/etext_witness.py` and `scripts/dashboard.py` (patched by
  `scripts/patch_benchmark_2026_10_11.py`);
- `.gitignore`.

It builds on ETEXT_WITNESS_2026_10_11 (`docs/ETEXT_WITNESS_2026-10-11.md`).

## 1. What the night showed (22:10-22:50 IST, from the PowerShell output)

- **ETEXT_WITNESS was applied** (the four files' hashes as expected), recorded (DOCS43) and released
  (`73f426b`, with `data/source_judged/` taken out of git).
- **The tests: 78 ran, one class did not start.** `tests/test_etext_witness_2026_10_11.py` made a
  file named `bad"name.txt`, and Windows does not allow `"` in a name (`OSError: [Errno 22]`). The
  fixture now uses `bad;name.txt`; the class's five tests run.
- **Judge v2 on the 47 texts:** 26 material, 12 moderate, 9 cosmetic; 32 held by the guard (it was 24,
  11 and 12).
  - Shatpath Brahmanam went from material to cosmetic: two vision pages no longer decide.
  - Three texts cut into a passage a page went from moderate to material: the Daksha and Shankha
    smritis, and Harita's tritiya sthanam. Their misread letters are 2.1-2.2%.
  - Four went from cosmetic to moderate (1.5-1.7% of letters): Yajnavalkya and Parashara smritis, the
    Niti-prakashika and the Saura upapurana.
- **The repair of the Tantric Texts worked:**

  | | before | after |
  |---|---|---|
  | Debris | 57.4% | 3.9% |
  | Vision | 0% | 95.8% |
  | Passages translatable | 1,859 | 2,946 |

  Also:
  - 1,047 fragments (lone numerals and dandas) were tagged noise;
  - the drift check found 212 pages current and 0 stale;
  - the one English translation went.
- **Hayashirsha:**
  - its vision run finished: 185 of 189 pages. Vision failed on 4, which kept Tesseract; page 178 hit
    MAX_TOKENS and a DeadlineExceeded;
  - *Use the repaired text* started at 22:50, with a backup made, and the register holds it in repair.
    The site keeps its 158 English and 1,174 Hindi.
- **Ganita** was accepted as complete.
- **Natyasastra:** its vision repair is running (3 of 546 pages at 22:50, about $0.002 a page).
- **Karan Aagama** is still untranslated. `--release` refused, as it should: English 0 of 1,935.
- **The Source desk:**
  - Bodhicaryavatara: 23 editions found. Three are Asiatic Society editions whose archive.org OCR
    text is 100% Devanagari, among them Vidhushekhara Bhattacharya's (1960) and La Vallee Poussin's
    Panjika (1902).
  - LalitaVistara: 9 editions found. The best scored is a Nepal Bhasa book, not Sanskrit; the AI judge
    (`--ai`) is there for this.
  - Natyasastra: 25 editions found. The best is the Gaekwad's Oriental Series edition (Baroda; vol. 1,
    1926 and vol. 4, 1964), with its OCR text 100% Devanagari.
- **The placeholder commands were run as they were.**
  - `--url "<the GRETIL .htm link>"` and `--file "...<file>"` were refused, as they should be.
  - `repair_text.py --doc Bodhicaryavatara__w_gretil --release` wrote "released" for a text that does
    not exist. Nothing was published, since there is no such text.
  - Two consequences are fixed here: `--release` now refuses a text that is not in the database, and
    `--write` always marks a new witness local, whatever an earlier record says.

## 2. What is built

### `scripts/benchmark_sources.py` (free, read-only)

It compares every reading of a text on the scan's own pages.

**The readings:**
- `tesseract` (`data/raw`), `vision` (`data/raw_vision`) and `consensus` (`data/raw_merged`, the
  repair);
- `database`: the passages being translated now (noise and front matter left out);
- `before repair`: the oldest `D:\backups\context_pre_repair_<doc>_*.db`, read immutable. That is
  what was translated before the first repair;
- every witness (`data/witnesses.jsonl`), through its `align.json`;
- every text file in `sources\<doc>\` (an archive.org OCR text, a GRETIL file), aligned by
  `etext_witness.measure`. A file a witness was written from is read once.

**For each reading:**
- **pages** and **Devanagari letters**: how complete it is;
- **the Latin share** of its letters;
- **the letters misread and the pages they damage.** These are `repair_text.judge`'s short Latin runs
  that are not watermarks, notes or numbering. Each page is one row, so every reading is judged the
  same way, and a level is given;
- **its F1 with ours** (the repair, else the database): per page, on the six-letter n-grams of the
  consonant skeleton, as a median;
- **when a critical e-text is among the readings,** its recall and F1 with it, page by page. The first
  e-text that is not an archive.org OCR is the critical text; `--reference` names another.

The two measures do different work:
- the misread letters see what OCR turned into Latin;
- the F1 with the critical text sees Devanagari misread as other Devanagari, which no count of Latin
  letters can.

**The translation:**
- now and before the repair: the English, the Hindi and the heuristic QA (`translation_qa`);
- the LLM judge's fidelity and fluency (`mt_reviews`), where `judge_sample.py` ran;
- the share of the passages translated that carried misread letters (3% of their letters or more).
  That is the debris's effect on the translation, measured: **material** from 10%, moderate from 3%.

**The opinion, in plain lines:**
- how much misreading the repair removed;
- whether archive.org's OCR of the same pages is better than ours, level, or worse. With a critical
  text it is judged by the F1; without one, by the misread letters, a tenth of a point counting as
  level;
- each reading's share of the critical text;
- whether vision alone reads the critical text better than the consensus, which would mean the merge
  keeps Tesseract readings it should not;
- the effect of the debris on the English made before the repair, and the English now.

**NEXT** is the translation (unless the register says set aside or complete), or a better source when
our text still misreads 1% of its letters or more. **ALSO**, when archive.org's own OCR of the scan is
not yet fetched, gives the command to fetch it for the comparison (`source_desk.py --fetch <the scan's
identifier> --kind text --force`). It is not ingested.

**Output:** `data\benchmarks\<doc>.json`. `--all` benchmarks every text with vision or repaired pages,
a witness or a fetched file, and writes `data\benchmarks\_summary.json`.

### `repair_text.py --release`

Refuses a text that is not in the database, unless `--force`. The witness case keeps its own message,
which names the ingest command.

### `etext_witness.py --write`

Always writes the register's `witness` record. The witness cannot be in the database at that point
(that is refused above), so an earlier "released" of its name is stale.

### `dashboard.py` (on a restart)

- **The repair page's Source desk** has *Benchmark the readings (free)*. It shows the table and the
  opinion; `/api/repair/sources` carries the last benchmark.
- **`/benchmarks`** lists every text benchmarked:
  - the misread letters in Tesseract, in ours and in archive.org's OCR;
  - the critical text's F1;
  - the English before the repair, and how much of it came from damaged text;
  - the English now;
  - the opinion.

  It has *Benchmark every text again*. *Sources & repairs* links to it.
- **The new steps** are `benchmark` (one text) and `benchmark_all` (no text needed).

### `.gitignore`

`data/benchmarks/` stays local; it is made again on demand.

## 3. What the benchmark can and cannot say

- **Without a critical e-text, it measures debris, not truth.** A Devanagari misreading that stays
  Devanagari is invisible to the letter count. It shows only in the F1 with a critical text, or in a
  low F1 between our readings.
- **The F1 compares readings, not editions' merits.** A critical text with variant readings lowers
  every reading of a different edition's scan alike. Commentary in the scan (the critical text is
  usually the mula alone) lowers precision alike too. The ranking between readings of one scan is
  what it is for.
- **It does not judge the English against anyone's translation.** Third-party translations are not
  fetched or stored (as in `benchmark_mbh01.py` and `judge_sample.py`).
- **The fidelity of a translation can be judged against the critical text,** paid and capped, dry-run
  first, from `judge_sample.py`. That is the next step on the translation side (T1, section 4).

## 4. The path

- **Done:**
  - R1 and R1.1 (the repair path, healed);
  - J1, J1.1 and J2 (the debris judged, v2);
  - S1 (the Source desk);
  - S2 (an e-text as a witness);
  - S3, offered (the missing page shown);
  - **B1, the benchmark.**
- **Next:**
  - **R3, the in-place re-ingest:**
    - it keeps passage ids;
    - it takes an offered page from a witness;
    - it clears only the translations whose source changed.
  - **T1, the translation judged against the critical text:**
    - `judge_sample.py`'s judge, given the witness's aligned verses as the source;
    - it shows how far the English made from a damaged scan strayed;
    - it is capped and dry-run by default.
  - **R4, the distillate:** per passage, the best reading among the witnesses and the best
    translation, each with its provenance.
  - **C14, Sources on the site:** a corpus table filled by the mirror from `data/source_judged`,
    `data/source_desk`, `data/witnesses.jsonl` and `data/benchmarks`. It is shown in the Researchers'
    Corner as *Sources wanted*.

## 5. Tests

`tests/test_benchmark_2026_10_11.py` (13):

- **On a temp tree:**
  - Tesseract (every fourth word read as Latin), vision on 18 pages, the repair, the database, the
    text before its repair with 200 English, archive.org's OCR with form feeds, and a critical
    e-text;
  - every reading found, and the critical text chosen over archive.org's OCR;
  - the repair's misreading removed, and ours reading the critical text better than Tesseract and
    archive.org;
  - the English before: 200, all from damaged text, MATERIAL;
  - NEXT, the translation;
  - a text set aside is not offered it;
  - archive.org's OCR of the scan is suggested when it is not fetched;
  - another text's backup is not taken;
  - `--all`, and a text with nothing to benchmark;
  - `--release` of a text that is not there;
  - a stale "released" does not make a witness public;
  - the file a witness was written from is read once.
- **The dashboard:**
  - the steps (`benchmark`, and `benchmark_all` with no text);
  - the Source desk's answer;
  - `/benchmarks` and its script (node);
  - the repair page, and `_rpBench` run in node;
  - the link from Sources & repairs.
- **The patcher** replays on its backups, all or nothing; the files are ASCII.

`tests/test_etext_witness_2026_10_11.py`: its fixture name works on Windows; its patcher replay compares
with this patch's backups.
