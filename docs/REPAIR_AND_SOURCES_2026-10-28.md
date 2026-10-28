# Repair and sources: the corpus read again, the open texts weighed (28 Oct 2026)

Markers: REPAIR_PARTIAL_2026_10_28, RIGHTS_FRONTMATTER_2026_10_28, INLINE_MARKS_2026_10_28, VEDIC_LLA_2026_10_28,
DOCS99_2026_10_28. Every number here was read on 28 Oct from the backup `D:\backups\context_20261028.db` (opened
read-only and immutable), the mirror's log, the maintenance log, `data\witnesses.jsonl`,
`data\source_verdicts.jsonl`, `data\gretil\catalog.jsonl` and `match.jsonl`, or from a run of the tools named, on
copies. Nothing was written to `data\context.db` from outside.

## 1. In short

- **Local and cloud are in step.** The mirror's tick at 14:31 compared 368 groups: all equal, 0 different. The
  genealogies' tick at 14:33 found its 8 tables equal (the 1,904 claims included) and sent 0 rows: HEAL holds (before
  it, every tick sent 80 to 150 persons again). The scholarly English on the site matches the desk to the row. Held
  by design: the two Yajurvedas and the Hayasirsa (in repair). The only gap: 7 Surya Siddhanta verses whose Sanskrit
  changed after their scholarly English (the guard keeps them off the site).
- **The Hayasirsa is not beyond repair.** Vision read 1,407 of its 1,430 verses; the judge calls it cosmetic; its
  scholarly English is current on 1,370 verses. One defect is systematic: the edition's footnote numbers glued into
  the Sanskrit (854 of them, in 586 verses). `scripts\mend_marks.py` takes them out, free, and keeps the scholarly
  English with them. What it lacks is its working English and Hindi (1,614 passages, about $7.75 a language).
- **The Karanagama is nearer than "withdrawn" suggests.** The editor's Hindi (816 passages) was typed out on 16 Oct and
  the 99 scholarly rows made from it rejected. Read again today: about 33 more passages are wholly the editor's Hindi
  or notes, typed as verse; 2 mix a verse with a line of Hindi. Its scholarly English is current on 916 of its 1,046
  verses. What keeps it off the site now is those 35 passages and a rights decision (1994 edition).
- **The open texts: we hold more than we show.** 13 open e-texts are in the database (GRETIL's, and one other); 2 are
  on the site (the Markandeya and the Surya). 11 wait: for English, for a decision, or (the Satapatha) for a mend.
  Four more GRETIL texts were weighed today against our scans: the Astadhyayi and the Rgveda padapatha read as the
  same work, in order; the Natyasastra's verses in part; our Lalitavistara scan is too garbled to compare.
- **Four mends built, tested on real data:** REPAIR_PARTIAL (the rounds were stalled 9 times on one text),
  RIGHTS_FRONTMATTER (a modern edition's own matter never sent), INLINE_MARKS (the note numbers), VEDIC_LLA (the
  Vedic l read as a vowel in GRETIL's Vedic texts).

## 2. Local and cloud

| Check | 28 Oct | Where |
|---|---|---|
| The corpus mirror | 368 groups equal, 0 different; 64 texts live; 3 held (in repair) | `D:\backups\corpus_mirror_log.txt`, 14:31 tick |
| The genealogies | 8 tables equal; sent 0 rows (texts 12, persons 14,979, steps 10,861, statements 22,021, claims 1,904, lines 53, verses 5,702) | the same log, 14:33 |
| HEAL | 0 persons sent again (every tick before it: 80 to 150) | the same log |
| The scholarly English (S1 of C22) | Markandeya 1,198 English rows (+210 that share a sentence), Surya 433 (+70; 7 stale), MBh I 24, Tantrik Texts 16: the desk's exact counts | the CSV of S1 |
| C21 to C24 | all four present; the readers' mode "readers"; 10 functions with their grants | P1, V1 to V3 |

Nothing to mend between them. The Surya's 7 stale verses come back when their scholarly English is made again from
the mended Sanskrit (the desk's "re-judge" of those verses, or the next scholarly round).

## 3. The Hayasirsa (HAYASHIRSHA_PANCARATRA)

The edition: Kali Kumar Dutta Sastri, Bibliotheca Indica Work 306, (c) The Asiatic Society, 1976 (its title page).

| | |
|---|---|
| Passages | 1,706: verses 1,430, prose 121, colophons 63, the edition's own matter 44, noise 48 |
| Read by | gemini-vision 1,678 passages; Tesseract 28 (23 of them verses) |
| The judge | cosmetic: 1.3% of verses misread |
| Scholarly English | 1,431 current rows; on 1,370 of its 1,430 verses; none stale |
| Working English, Hindi | 1 of 1,614; none (the site still shows the version from before the repair, with its old Hindi) |
| The defect | the edition's footnote numbers read into the text: 854 numbers in 597 passages (586 of the 1,407 verses vision read, 41.6%): "caturmukhanca4", "dehamrta14stada" |
| Its witness | none open: GRETIL has no Hayasirsa (its nearest are the Agnipurana and the Visvaksenasamhita, other works); Muktabodha has an e-text, under terms that need its written consent for any use beyond personal reading |

**The mend (INLINE_MARKS_2026_10_28, `scripts\mend_marks.py`).** In the passages vision read, typed verse, prose or
colophon: one to three ASCII digits glued after a Devanagari letter or sign (the number that closes a reading), or
glued before one after a space, a line's start or a bracket (the number that opens it). Never after a danda, never a
decimal or a longer number, never a Devanagari numeral, never a Tesseract reading (there a 5 is often the avagraha),
never a text where a number follows nearly every syllable (the Sama Veda's svaras 1 2 3). The IAST is made again
from the mended text; the search row too; a scholarly English made from the old reading is carried to the new one
(its hash). The raw OCR page (`passages.norm`) and the OCR variants are evidence and stay as read. Each `--apply`
backs the database up first (`db_backup.py`, to `D:\backups`) and writes nothing if that fails; then a manifest;
`--undo` puts back exactly that.

Run on an extract of the real text (1,706 passages, 1,606 scholarly rows): 597 passages mended, 854 numbers out, 667
scholarly rows carried; the IAST equals the transliteration of the new text in 597 of 597 (and in all 847 untouched
verses before it); the raw OCR, the variants and the English untouched; the search finds the mended words; the undo
gives back the database byte for byte (passages, hashes, search rows).

The same census over the corpus: the Natyasastra (GOS) has 1,801 such numbers in 900 of its 2,697 vision-read
verses; no other text passes the 5% line (the Mallapurana 2.2%, the Tantrik Texts 1.5%: a person may look and use
--force).

**The way forward.** It is not beyond repair; it is one free mend and one translation away.

| Path | Cost | What the site shows |
|---|---|---|
| A (recommended): mend, then its working English through the rounds, then release; Hindi when the cap allows | $0, then about $7.75 (fits the $12.10 left above the reserve) | the mended Sanskrit, the scholarly English, the working English; Hindi later |
| B: mend, then release now (`--release --force`) | $0 | the mended Sanskrit and the scholarly English; the old working English and Hindi of the re-read passages leave the site until they are made again |
| C: as A, with Hindi too | about $15.50 (a cap raise of about $4) | everything |

The rights are yours to weigh: the Sanskrit as this 1976 edition constitutes it, with our own English; the edition's
introduction and notes (44 passages) are never sent (RIGHTS_FRONTMATTER).

## 4. The Karanagama

The edition: Ramachandra Pandey, Shaiva Bharati Shodha Pratishthanam, Varanasi, (c) 1994, with the editor's Hindi
translation and notes (its title page). The scan's pages carry "CC-0. Jangamwadi Math Collection. Digitized by
eGangotri": the digitizer's word for its images, not the publisher's for the book.

| | |
|---|---|
| Withdrawn | 16 Oct: "bilingual: the editor's Hindi under each verse was translated as if Sanskrit" |
| Passages | 1,909: verses 1,046; the editor's Hindi typed out 816 (classify_hindi, 16 Oct); prose 43; colophons 4 |
| Scholarly English | claude-sonnet-5-5: current on 916 of the 1,046 verses (775 passed, 137 flagged, 4 with a doubt of the source); the 99 rows made from the Hindi rejected; none stale |
| Working English | 174 of the 1,046 verses; Hindi: none |
| Left | about 33 passages typed as verse that are wholly the editor's Hindi or his numbered notes (classify_hindi passes them: OCR noise thins their Hindi); 2 that set a line of Hindi beside a verse (p32.5, p35.10) |
| Its witness | none open: GRETIL's catalogue has no Karanagama (its match: "none"); the nearest Saiva texts there (Kirana, Mrgendra, Svacchanda) are other works |

So "it stays withdrawn until its Sanskrit is separated from the editor's Hindi" was true on 16 Oct and is now true
only of those 35 passages. The way forward: type the 33 as the edition's own matter with `mark_passages.py` (a
person's tag, logged, undoable; the dry run shows each first), read the two mixed ones, then the decision on the 1994
rights. If you restore it: its Sanskrit and our scholarly English go to the site; the editor's Hindi and notes never
do (RIGHTS_FRONTMATTER); its working English (872 verses, about $4.20) through the rounds.

## 5. The library: are we using the best open Sanskrit?

**What we hold.** GRETIL's two archives (1_sanskr.zip, 1,181 texts catalogued with the licence each states; 6_sres.zip
listed with its rights), matched by content against our scans (`data\gretil\match.jsonl`). In the database:

| Open e-text (local name) | Passages | English | Scholarly | State |
|---|---:|---:|---:|---|
| markandeya_purana__w_gretil | 5,240 | 0 | 1,408 | on the site |
| jyotish_surya_siddhanta__w_etext | 515 | 503 | 510 | on the site |
| nirukta__w_gretil | 649 | 647 | 0 | local; 41 passages with the Vedic l misread (VEDIC_LLA) |
| satapatha_madhyandina__w_gretil | 7,173 | 0 | 0 | local; not until its "ch" is restored |
| upapurana_narasimha_purana__w_gretil | 3,586 | 0 | 0 | local |
| smriti_14manu_smriti_seg__w_gretil | 3,058 | 0 | 0 | local |
| smriti_06yagyavalkya_smriti__w_gretil | 1,392 | 0 | 0 | local |
| smriti_17gautama_smriti__w_gretil | 1,023 | 0 | 0 | local |
| smriti_13parashara_smriti__w_gretil | 955 | 0 | 0 | local |
| Bodhicaryavatara__w_gretil | 935 | 0 | 0 | local (its scan withdrawn) |
| 2015_405693_Shatpath-Brahmanam__w_gretil | 745 | 0 | 0 | local |
| sama_veda_sama_veda__w_gretil | 469 | 0 | 0 | local |
| smriti_18yama_smriti__w_gretil | 82 | 0 | 0 | local |

An e-text proofread by its editors reads cleaner than our scans of the same works (in the four weighed today: noise
in 0.0 to 0.8% of its words, against 0.4 to 6.3% in the scans). What holds these back is the working English (about
$0.0048 a passage) and, for each, the release: nothing in their Sanskrit.

**Weighed today** (`etext_witness.py`'s preview, on a copy; nothing written):

| Our scan | GRETIL text | The preview | So |
|---|---|---|---|
| Astadhyayi (528 verses, Tesseract) | Panini: Astadhyayi | the same work, in the same order: 91 of 128 readable pages (71%, in order 99%); noise 0.8% against the scan's 3.7%; 3,947 sutras | write it and ingest it: the better text of the two |
| 476948-Rgveda-samhita_Vol-ii (padapatha with commentary) | Rgvedasamhita, Padapatha | the same work, in order: 795 of 1,045 pages (76%, in order 100%); offers a reading for all 104 pages the scan cannot read | after VEDIC_LLA (it has the Vedic l 598 times) |
| 2015_368408_Natyasastra-With (with the Abhinavabharati) | Bharata: Natyasastra 1-16, 18-30, 33, 35-37 | in part: 290 of 498 pages (58%, in order 97%): the verses, not the commentary | a witness of the verses, local |
| LalitaVistara (Tesseract, noise 6.3%) | Lalitavistara | 82 of 578 pages (14%): the scan is too garbled to tell | the e-text as the text itself; the scan to be read by vision or retired |

**Other open sources, as their own terms say** (read from their pages; nothing fetched around a refusal):

| Source | What it has for us | Its terms |
|---|---|---|
| GRETIL | as above | most texts CC BY-NC-SA 4.0 (credit, non-commercial, share alike); some "reference only" |
| Muktabodha | an e-text of the Hayasirsapancaratra (announced 2017) and many Saiva and Pancaratra texts | "for internal, noncommercial, informational purposes only"; other uses need its written consent (info@muktabodha.org); no automated extraction |
| DCS (Hellwig) | lemmatised Sanskrit (CoNLL-U, on GitHub) | its licence not yet read by us |
| Ambuda | mostly GRETIL's texts, proofread | its licence not stated on the pages read |
| DSBC | Buddhist Sanskrit | "as indicated by the source(s) cited" |
| TITUS | the Vajasaneyi and Taittiriya Samhitas | restricted |

**Texts we do not have that GRETIL does** (new texts, not witnesses; for the Agama and Tantra shelf): the
Pauskarasamhita 27-43, the Satvatatantra, the Jnanamrtasarasamhita, the Prakasasamhita, the Visvaksenasamhita
(Pancaratra); the Kiranatantra 1-6 with Ramakantha, the Mrgendragama, the Svacchandatantra, the Malinivijayottara,
the Tantraloka (Saiva). Each is a free extract and a free ingest; the English is the cost.

## 6. Built today

| Marker | What | Verified |
|---|---|---|
| REPAIR_PARTIAL_2026_10_28 | `ocr_consensus.py --partial`: above `--max-usd`, read the pages that fit, the rest later; `repair_text.py --partial`; the rounds pass it. The rounds had refused 9 times on the Padma Patala ($1.2727 against $0.10) | its test (8), the suites of the rounds, OCR, repair |
| RIGHTS_FRONTMATTER_2026_10_28 | `configs\edition_rights.json` (6 editions, each with its edition, its notice where one was read, and the evidence); `corpus_sync.py` sends their own matter as a notice, and none of its Hindi, scholarly rows, names or vectors | its test (7); on real data it withholds 44, 816, 48, 43, 194 and 1 passages |
| INLINE_MARKS_2026_10_28 | `scripts\mend_marks.py` (section 3) | its test (5); the extract above |
| VEDIC_LLA_2026_10_28 | `etext_witness.to_deva()` reads the Vedic l (l with a dot below after a vowel) as the consonant, not the vowel indic_transliteration writes; `mend_witness.py` mends a witness already in the database; the replays of the six patches before it look for its backup | its test (5) and the 173 tests that touch the two files; the plan on the Nirukta: 41 respelled, 608 the same, 0 left alone |

## 7. What it costs, and the lever

Metered since 15 Oct, as billed: the working English on gemini-2.5-flash $0.0048 a passage (3,219 calls: 1,519
tokens in, 1,736 out on average, of which about 92% is the model's thinking); the scholarly English on
claude-sonnet-5-5 $0.01676 a verse; a page read by vision $0.00505. The cap: $125, spent $111.90, $13.10 left, $1.00
kept in reserve.

The lever: the thinking. If the working English kept its quality with a small thinking budget, the ten waiting
e-texts without English (19,418 passages, about $93 at today's price) would cost a fraction. That wants an A/B on 40 passages
of two texts, judged blind, before any change (the BM2 method); nothing is changed until it is read.

## 8. The path from here

1. Today's mends: the four patchers; mend_marks on the Hayasirsa; mend_witness on the Nirukta.
2. The Hayasirsa: path A, B or C (section 3).
3. The Karanagama: the 33 tagged, the 2 read; then the rights decision.
4. The open texts: the Nirukta released (its English is done); the Astadhyayi written and ingested; the Rgveda
   padapatha previewed again after VEDIC_LLA; the smaller smrtis opted into the rounds' translation, smallest first
   (Yama $0.39, Parashara $4.58, Gautama $4.91); the rest after the thinking A/B.
5. Muktabodha: ask in writing for the Hayasirsa e-text as a witness (for checking our readings, not for publication).
6. The Agama shelf: extract and ingest the GRETIL Pancaratra and Saiva texts listed in section 5, local until
   translated.
7. Srangam's own documentation: `docs\CURRENT_STATUS.md` there was last brought up to date on 12 Jul; its running
   ledger is `docs\RELIABILITY_AUDIT.md`. A map like this repository's `docs\DOCS_MAP.md` is the next step there.

## 9. Commands, in order

From the repository root (`D:\Sanksrit Automatons\sanskrit-automatonv2`), with the dashboard idle:

```powershell
python scripts\patch_repair_partial_2026_10_28.py --check
python scripts\patch_repair_partial_2026_10_28.py
python scripts\patch_rights_frontmatter_2026_10_28.py --check
python scripts\patch_rights_frontmatter_2026_10_28.py
python scripts\patch_vedic_lla_2026_10_28.py --check
python scripts\patch_vedic_lla_2026_10_28.py
python scripts\patch_docs99_2026_10_28.py --check
python scripts\patch_docs99_2026_10_28.py
python scripts\docs_map.py --write
powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1
python scripts\mend_marks.py --doc HAYASHIRSHA_PANCARATRA --show 8
python scripts\mend_marks.py --doc HAYASHIRSHA_PANCARATRA --apply
python scripts\mend_witness.py --doc nirukta__w_gretil
python scripts\mend_witness.py --doc nirukta__w_gretil --yes
python scripts\repair_auto.py --round --dry-run
```

## 10. Rollback

- A patcher: each file it wrote has a `.bak_` copy beside it, named with the patch's tag (repairpartial,
  rightsfront, vedlla, docs99) and the day: copy it back.
- mend_marks: its ALSO line prints the exact undo (`python scripts\mend_marks.py --undo` and the manifest it wrote in
  `data\`, then `--apply`); or the backup it made first in `D:\backups` (context_pre_mendmarks_...).
- mend_witness: its own backup (it makes one before it writes) and its log in `data\witness_mend`.
- mark_passages: `--undo --apply` for the same pages.
- RIGHTS_FRONTMATTER: a text taken out of `configs\edition_rights.json` is sent as before at the next tick.
