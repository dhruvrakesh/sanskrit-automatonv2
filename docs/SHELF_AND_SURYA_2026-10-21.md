# 21 Oct: the Surya Siddhanta's spelling mended, its verses of numbers, and the scholars' shelf (step 1)

Markers: **ETEXT_ORTHO_2026_10_21** (scripts/etext_witness.py, by scripts/patch_etext_ortho_2026_10_21.py),
**WITNESS_MEND_2026_10_21** (scripts/mend_witness.py), **NUMERAL_VERSE_2026_10_21** (scripts/scholar_translate.py, by
scripts/patch_numeral_verse_2026_10_21.py), **SHELF_2026_10_21** (scripts/scholar_shelf.py) and **DOCS78_2026_10_21**
(scripts/patch_docs78_2026_10_21.py). It follows docs/LEAK_GUARD_2026-10-19.md (`9c321712`).

## 1. What happened on 21 Oct

- **The last Sonnet run of the Surya Siddhanta** (13:09 IST, `--engine anthropic:claude-sonnet-5-5 --no-compare`,
  judged by gemini-2.5-flash): 70 verses of pages 25 to 28, 63 passed, 7 flagged, $3.21
  (data/scholar/jyotish_surya_siddhanta__w_etext_20261021_130958.jsonl). The Claude credit: $189.08 of its $190 cap
  spent, $0.92 left (it ends on 11 Nov).
- **Released at 16:03 IST** (repair_text.py --release); **the 16:31 mirror run sent it**: 515 passages and 915 rows of
  scholarly English (the site's reader, signed in).
- **Found at 16:10 IST, reading the 18 verses the run had left:** the e-text's Sanskrit was read wrongly.

## 2. The e-text read wrongly (ETEXT_ORTHO_2026_10_21) and mended in place (WITNESS_MEND_2026_10_21)

The source is GRETIL's Suryasiddhanta (sa_sUryasiddhAnta.htm: Michio Yano's input of 2002, GRETIL's TEI conversion of
2020, CC BY-NC-SA 4.0). It writes IAST with **H for the visarga** (namaH, tejaHsahaH), **+a for an a merged into the
vowel before it** (puruSo +ayaM), **N.NNa:** for a verse's pada, and **an edition's variant** as (B kevalam), (C ...),
once (D ...) typed with a dot under the D; its header names the editions B, C and D. etext_witness.to_deva() lowered the
text before transliterating it. So:

| What | Passages | Was | Now |
|---|---|---|---|
| The visarga | 362 of 515 | h with a virama (namah) | the visarga |
| +a | 101 | "+" and a | the avagraha (as printed editions write it) |
| The pada labels | every verse | Devanagari, the b a consonant with a virama | 1.01a: as the e-text writes them |
| The sigla | 43, in 39 passages | Devanagari consonants | B, C, D |
| GRETIL's English header | 11 lines of page 1 | Devanagari "verses" (7 given a scholarly English) | the English, as noise |
| The inputter's note "checked" | 1 | Devanagari | dropped (it stays in the page file's roman_source) |

The translator had read through it (26 of its doubts quote the e-text's h and + forms, and say that they stand for
the visarga and the avagraha), so the English stands. mend_witness.py reads each passage again from its own romanized line:

- the old reading must be what the old to_deva gives (all 515 are; 0 left alone), and the database's text what was
  ingested (else it refuses);
- the page files are rewritten (each kept as .bak_mend_<date>) and ingested as etext_witness.py --ingest does
  (ingest_jsonl_fast.py updates by page and index): **the ids stay**;
- a verse's latest scholarly English made from the old spelling gets **a new version made from the new one**: the
  same English, notes, doubts, scores and review, with the reason "[re-based ...]", as --rejudge does;
- the header lines become noise in Latin letters; their 7 "translations" are not carried over: the src_hash guard
  takes them off the site and the edition;
- a backup first, a log in data/witness_mend/, a line in data/witnesses.jsonl.

The plan on the 03:52 IST backup (before the Sonnet run): 503 passages respelled, 11 header lines, the title the same;
415 scholarly English to re-base and 7 to drop. On the PC now it should say 485 and 7. **The Markandeya's GRETIL
witness** (5,240 passages): its verses read the same with the new reading (the e-text writes the visarga with its
dot); 9 lines of its page 1 are GRETIL's header ("Header", "Source:", "(www.sansknet.org)", ... "Text"), to noise.

**After the mend:** the Surya has 503 verses. 485 have their scholarly English (394 passed, 90 flagged, 1 in doubt;
from the run logs). The 18 verses of numbers are left.

## 3. The verses of numbers (NUMERAL_VERSE_2026_10_21)

18 verses (1.30, 1.41 to 1.43, 2.17 to 2.27, 2.34, 2.35 and 2.53: the revolutions of the planets, their epicycles,
the sines) give each
word-numeral's value in brackets, (57753336), (224, 449, 691). readiness() called them "numbers among the words: an
index". In a typed edition (an e-text, GRETIL, BORI: the engines ref_of() already trusts) the numbers in brackets no
longer count; a scan's reading is judged as before, and an index without brackets is still an index.

They cost about $0.05 each on Sonnet (about $0.90; the credit has $0.92, and the run stops when it runs out) or about
$0.017 each on Gemini 2.5 Pro (about $0.30 of Google's cap), which a Gemini Flash judge would read (the same family:
scholar_translate.py refuses a Claude judge for a Gemini run). Your choice.

## 4. The scholars' shelf, step 1 (SHELF_2026_10_21)

Three indexes of names, digitized by the Cologne Digital Sanskrit Lexicon (the Sanskrit Library and Thomas Malten,
CC BY-NC-SA 3.0: non-commercial, the credit "exactly as described" in each header, the same licence for what is
derived). The files stay on the PC (data/shelf/ is in .gitignore) and the shelf_ tables are not mirrored.

| Index | Entries | What it gives |
|---|---|---|
| Macdonell and Keith, Vedic Index of Names and Subjects (1912) | 3,834 | each name, what the Vedic texts say of it, its references (25,027 read), the names it refers to |
| Soerensen, Index to the Names in the Mahabharata (1904) | 12,647 | each name and its places in the Calcutta edition (24,464 read) |
| Dikshitar, The Purana Index (1951 to 1955) | 17,512 | each name in five Puranas, by the abbreviations it prints (39,508 read) |

The Purana Index's abbreviations (Va. 7,501 times, Br. 7,307, M. 5,876, Bha. 4,504, Vi. 3,370; Ib. 2,642) are kept
as printed: their key is in the printed front matter, which the digitization does not hold. Of the references, these
point to a text our corpus holds: the Vedic Index's 2,817 (the Satapatha only in book 14, which is ours; the
Brihadaranyaka (ours is the Madhyandina recension, numbered otherwise); the Vajasaneyi and Taittiriya Samhitas, the
Samaveda (OCR readings: whether they hold the place is not checked); the Nirukta) and Soerensen's 4,511 in book I
(Calcutta numbering; our MBh01 is the critical edition's). The Rigveda's 4,326 are not counted: ours is one volume of a
scan, not yet read.

**Download** (about 4.7 MB; the md5 of the files of 21 Oct, which Cologne dated 13 Oct 2026):

```powershell
$A = "D:\Sanksrit Automatons\sanskrit-automatonv2"
Set-Location $A
New-Item -ItemType Directory -Force data\shelf\cologne | Out-Null
foreach ($c in "vei","inm","pui") {
  $z = "data\shelf\cologne\$($c)txt.zip"
  Invoke-WebRequest -Uri "https://www.sanskrit-lexicon.uni-koeln.de/scans/$($c.ToUpper())Scan/2020/downloads/$($c)txt.zip" -OutFile $z -UseBasicParsing
  Expand-Archive -Path $z -DestinationPath "data\shelf\cologne\$c" -Force
  Get-FileHash $z -Algorithm MD5 | Format-List Hash, Path
}
```

veitxt.zip e16c7fcbff96a79936a4874fb1547c0b, inmtxt.zip 85eb0f80bdd4a012043a12fc85a42a37, puitxt.zip
0405dc3d0eae95bd5238bcfe3ab06bee. A different md5 means Cologne has corrected the files since: the importer reads
them all the same and records each file's sha256.

**Then:** `python scripts\scholar_shelf.py` (the plan: the entries, the references, how many of our 13,145 names each
index holds; writes nothing), `--yes` (a backup, then the tables), `--show Janaka` (what each index says of a name,
where its references are ours, and where our texts name it), `--credits` (the credit lines).

**What it is for.** The shelf is the map the scholars already drew: the Vedic Index says that Janaka of Videha was a
contemporary of Yajnavalkya Vajasaneya, of Svetaketu Aruneya and of Ajatasatru of Kasi, with the verses. Step 2 reads
Raychaudhuri's Political History of Ancient India (1923; public domain in India since 2018) into claims with their
pages and the verses he cites; step 3 checks each claim and each index entry against our verses (the verse says so,
says otherwise, is not in our texts, or a new tie of ours).

**Our Satapatha is book 14 only** (the Brihadaranyaka with a commentary). It holds Bhujyu's question at Janaka's court,
where the Parikshitas had gone (our pages 108 and 109), but not Janamejaya's horse sacrifice (book 13) nor Janaka's
other dialogues (book 11). GRETIL has books 1 to 11 and 13 to 14.

## 5. Tests

**OPS_GUARD_TEST_2026_10_21** (scripts/patch_ops_guard_test_2026_10_21.py): the whole suite, run on a copy of the PC's
repo, had one failure of its own, before any of this: tests/test_ops_guard.py's test_no_direct_generate_calls_left,
failing since SPEND_TRUTH_2026_10_04 (it took _gen()'s own calls for calls that bypass it). It now asserts that every
generate_content call in infer_mt.py is inside _gen().

tests/test_etext_ortho_2026_10_21.py (5), tests/test_numeral_verse_2026_10_21.py (4),
tests/test_witness_mend_2026_10_21.py (3), tests/test_scholar_shelf_2026_10_21.py (4), tests/test_docs78_2026_10_21.py (3).
The replay chains of test_etext_page_2026_10_18 (.bak_etextortho_) and test_scholar_ref_2026_10_18 (.bak_numeral_).

## 6. Still to decide (yours)

1. The Surya's 18 verses of numbers: Gemini 2.5 Pro now (about $0.30), or Sonnet with new credit.
2. The shelf on the site: the licence allows a non-commercial site that gives the credit and the same licence.
3. Step 2, Raychaudhuri's book as claims: about $1 of Google's cap on Gemini Flash.
4. From before: the Ganita's scholarly English (about $30), the Hayasirsa (held) and the Karanagama (withdrawn), the
   backticks in Gemini's working English.
