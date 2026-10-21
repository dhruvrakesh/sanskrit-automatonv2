# 21 Oct (evening): the Surya's references, Raychaudhuri read into claims (the shelf, step 2), an e-text's noise named

Markers: **ETEXT_REFS_2026_10_21** (scripts/etext_witness.py and scripts/mend_witness.py, by
scripts/patch_etext_refs_2026_10_21.py), **CLAIMS_2026_10_21** (scripts/scholar_claims.py), **ETEXT_NOISE_2026_10_21**
(the Srangam kit: docs/srangam/ETEXT_NOISE_2026-10-21/, scripts/patch_srangam_etext_noise_2026_10_21.py) and
**DOCS79_2026_10_21** (scripts/patch_docs79_2026_10_21.py). It follows docs/SHELF_AND_SURYA_2026-10-21.md (`6f8380af`).

## 1. The Surya's references (ETEXT_REFS_2026_10_21)

Found after the mend of the afternoon, reading the witness's `verse_ref` and `chapter`. Each verse of GRETIL's
Suryasiddhanta is one line that begins with its pada label (`1.31a: ... 1.31b: ...//`), and for a verse of numbers the
e-text gives the value of its word-numerals in brackets at the end (`//(364220)`: Jupiter's revolutions in a yuga).
`etext_witness.take_ref()` read that bracket (its rule R_PAR, for e-texts that end a verse with "(12)") as the verse's
reference.

| What | Passages | Was | Now |
|---|---|---|---|
| The value in brackets at a verse's end | 18 | its `verse_ref` (364220, 146568, 232238, 1603000080, 25082252, 39, 1953720000, 3438, 225 three times, 260.40, 115, 1043209, 4331500, 38328484, 80572864, 25980012), and taken out of the text and of the romanized line | put back in the text (as Devanagari digits, as the other values are); the reference the label's (1.31, 1.32, ... 12.89) |
| The other verses | 485 | no reference | the label's (1.1 ... 14.27) |
| The chapter | 503 | the colophons' count (1, then 2; "260" once) | the label's: 1 to 14 |
| A chapter's first verse | 12 | (no label read: the line begins with the chapter's title, `[spaṣṭādhikāraH] 2.01a: ...`) | the label after the title |
| The scholarly English | 18 + 485 | | the 18 re-based (a new version, the same English, made from the restored text); the latest row of the others given the verse's reference (the English untouched) |

The verses in each chapter, from the labels: 71 (with the title line), 69, 52, 26, 17, 24, 24, 21, 18, 16, 23, 90, 26,
27. The e-text gives three references to two verses each, its own slips, named by the plan and left as written:
**3.13** (pages 10.5 and 10.6), **10.13** (19.7, 19.8), **13.21** (27.1, 27.2); and one verse is labelled `2.34a ...
3.34b` (its first label is taken).

**How it was checked:** on a copy of the page files and of the source (sha256 `44f66737...`), with a database built from
them, the plan gave respelled 18, the reference only 485, the same 12 (the 11 header lines and the title); after
`--yes` a fresh parse of the source by the patched etext_witness.py gives the same 504 texts, references and chapters
as the mended records, and a second plan finds nothing to mend.

**What the mend does now:** the plan reads each record's line again from the witness's source file, but only when the
file's sha256 is the one in witness.json (otherwise from the romanized line kept: the labels are read, the value cannot
be put back). New kinds: "the reference only" (the text the same) and "the value in brackets" among a respelled
verse's changes. `--yes` writes `verse_ref` and `chapter` into the page files and the database (ingest_jsonl_fast.py;
the ids stay), checks them, re-bases the 18, and sets the reference of the 485 latest scholarly rows in one transaction
after a backup. The mirror compares every passage's row, so the next run sends the 503 passages again, and the
re-based verses' scholarly rows.

**Order:** after the Gemini run of the verses of numbers, which wrote scholarly rows for some of the same verses. It
finished at 17:48 IST (data/scholar/jyotish_surya_siddhanta__w_etext_20261021_170823.jsonl: 18 verses, 15 passed, 3
flagged, $2.10 (the run's own count; DOCS80_2026_10_21: its log's rows sum to $2.01)); its rows still carry the old references (39, 3438, 115 among them), which the mend re-bases.

## 2. Raychaudhuri read into claims (CLAIMS_2026_10_21)

**The book:** Hemchandra Raychaudhuri, *Political History of Ancient India, from the Accession of Parikshit to the
Extinction of the Gupta Dynasty* (University of Calcutta, 1923; the title page; the printer's line is dated
28.8.23). The scan: Dhananjayarao Gadgil Library, Gokhale Institute of Politics and Economics, Pune, GIPE-004595
(handle 10973/29602), 372 pdf pages, md5 `75e8d7bd429f9396997cc9e1c2e9f4bd`, now at
`data/shelf/phai1923/GIPE-004595.pdf` on the PC (data/shelf/ is not committed). Published in 1923, its author died in
1957: in the public domain in India (60 years after the author's death) and in the United States (published before
1929).

**The pages:** pdf 14 to 18 are Part I's Foreword (i to v); pdf 19 is page 1, and so on (pdf − 18: pdf 50 prints 32,
pdf 112 prints 94). Part I, *From the Accession of Parikshit to the Coronation of Bimbisara*, is pdf 14 to 112 (pp. i-v,
1-94); Part II begins at pdf 113 (p. 95). The list of abbreviations is on pp. xv-xvi (pdf 12-13); the errata on pdf 7.

**How a page is read:** its text is the scan's own text layer (Adobe Paper Capture, 2014; it misreads, `Brahma1;1a`
for Brāhmaṇa), read with pypdf, free. gemini-2.5-flash reads one page at a time (Google's cap, metered as kind
`claims`; the cap is asked before each page; the thinking capped at 1,024 tokens) and returns JSON: the subject and
the object in standard IAST and as printed, a relation from a fixed list (son_of, priest_of, performed, dated_to,
named_in, ...), the claim in at most 35 words with nothing added, a quotation of 8 to 30 words copied from the page,
the cites as printed, the stance (asserts, reports, rejects, doubts), his hedge, and the scholar he reports.

**Nothing is taken on the model's word:** each quotation is checked against the page's text: *exact* (the same words,
diacritics and case aside), *close* (similarity at least 0.85: the OCR's misreadings), or *none* (not on the page; the
report lists them for a person). Each cite is read into the work it names, from the book's own abbreviations (Sat. Br.,
Ait. Br., Brih. Up., Chh. Up., Mbh., Mat., Ved. Ind., J., ...), and marked when our corpus holds that place: the
Śatapatha only for book xiv, the Bṛhadāraṇyaka (ours is the Mādhyandina, numbered otherwise), the Mahābhārata only
for book i (ours is the critical edition's Ādiparvan, Poona 1933, numbered otherwise than the editions of 1923), the
Nirukta, the Vājasaneyi and Taittirīya Saṃhitās and the Sāmaveda (OCR readings: whether they hold the place is not
checked). A Vedic Index cite gets the page of the Cologne file (Ved. Ind. I. 274: `1-274`). Names are keyed across the
1923 spellings (Parikshit and Parikṣit, Chhandogya and Chāndogya, Rig-Veda and Ṛgveda, Panchala and Pañcāla).

**Where it lives:** `data/shelf/claims.db` (tables claim_works, claim_pages, claim_reads, claims, claim_cites,
claim_names). `data/context.db` is only read (the shelf, our entities) and gets the meter's row of each call. A page
read again (`--redo`, or a new prompt) gets a new read; the latest is the page's claims; a failed page is read on the
next run.

**What it costs:** the plan says about $0.007 a page: Part I (99 pages) about $0.69; `--max-usd 1.50` stops a run.

```
python scripts\scholar_claims.py                       # the plan; writes nothing
python scripts\scholar_claims.py --extract             # free: the 372 pages' text (about 30 s)
python scripts\scholar_claims.py --pages 1-3 --yes     # a trial, about $0.02
python scripts\scholar_claims.py --part 1 --yes        # Part I; resumes
python scripts\scholar_claims.py --show Janamejaya     # his claims, the indexes, our texts
python scripts\scholar_claims.py --report
python scripts\scholar_claims.py --csv data\shelf\phai1923_claims.csv
```

**What it is, and is not:** a claim is Raychaudhuri's, with his page and his words; whether the texts bear it out is the
next step, and the report lists the cites to texts we hold for it. Nothing goes to the site.

## 3. Our corpus: the scholars' e-texts where they exist, our own where they do not

As the user put it on 21 Oct: the corpus our translation engine works on should be authoritative e-texts where they
exist (GRETIL, the BORI critical editions) and, where they do not, the e-text we make ourselves from the best scan, by
OCR and vision. 21 Oct showed the condition of the first half: an e-text has its own conventions (H for the visarga,
+a, pada labels, sigla, values in brackets, an English header), and each must be read as its editor meant it, then
checked against the scan's reading, before it is translated. The next e-text to bring in for the shelf's work is
GRETIL's Śatapatha Brāhmaṇa (books 1 to 11 and 13; ours holds book 14 only): Janamejaya's horse sacrifice (xiii) and
Janaka's dialogues (xi) are there. Its address is to be checked before anything is downloaded.

## 4. The site: an e-text's noise named (ETEXT_NOISE_2026_10_21)

The reader called the 11 header lines "Scanner noise, not text."; an e-text has no scanner. PassageBlock.tsx now
names noise in an e-text (readingOf: not a scan) "Not the text: the e-text's own header or notes." (folded as before;
its note and its About say what it is); a scan's noise, and noise whose reading is not recorded, are as before.
Srangam's RELIABILITY_AUDIT gets Phase AM (invariant 60).

## 5. Tests

test_etext_refs_2026_10_21 (6), test_scholar_claims_2026_10_21 (8), test_srangam_etext_noise_kit_2026_10_21 (4),
test_docs79_2026_10_21 (3); the replay chain of test_etext_ortho_2026_10_21 (.bak_etextrefs_). In Srangam:
src/__tests__/reader-etext-noise.test.tsx (2).

## 6. The estimate of the verses of numbers (owned)

ENTERPRISE_PATH addendum 68 (DOCS78) said the Surya's 18 verses of numbers would cost "about $0.30 of Google's cap".
That was wrong. The dry runs priced them at $0.65 on Sonnet (within the $0.92 left of the Claude credit) and $1.84 on
Gemini 2.5 Pro (judged by Gemini Flash, the same family); the Gemini run was the one made: 18 verses, 15 passed, 3
flagged, $2.10 (the run's own count; DOCS80_2026_10_21: its log's rows sum to $2.01).

## 7. Still to decide (yours)

- Part I in full, after the three-page trial; then Part II (pdf 113 on).
- The claims and the shelf on the site: the claims are Raychaudhuri's words (public domain); the Cologne indexes are
  CC BY-NC-SA 3.0.
- GRETIL's Śatapatha as a witness (its address checked first).
- The book's errata (pdf 7) applied to the claims of the pages they correct.
