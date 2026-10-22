# The brain, wired: what is joined, what is not, and the path from here (21 Oct 2026, night)

Markers: **CLAIMS_FIX_2026_10_21** (scripts/scholar_claims.py, by scripts/patch_claims_fix_2026_10_21.py) and
**DOCS80_2026_10_21** (scripts/patch_docs80_2026_10_21.py). It follows docs/CLAIMS_AND_REFS_2026-10-21.md (`df8b35ae`).

Read for this page: STATE (sections 1 to 14), CLOUD_BRAIN, the C4 and C6 SQL in docs/cloud/, Srangam's
`supabase/functions/` and `src/` (the reader's RPCs), D:\backups\corpus_mirror_log.txt, the backup
`context_pre_mend_jyotish_surya_siddhanta__w_etext_20261021_184110.db` (read as immutable; data/context.db itself
was not opened from the VM), and data/shelf/claims.db (read as immutable). Nothing was guessed: where a number is
an estimate, it says so.

## 1. What the brain holds, and where (measured)

| Layer | On the PC | On the site (Supabase, `corpus`) | Read by the site |
|---|---|---|---|
| Texts | 73 rows in `docs` (65 live) | 65 | the library (C6) |
| Passages | 174,019 (100,141 in the live texts; the three withdrawn hold 73,878) | 99,966 live, measured 21 Oct 20:45 IST (DOCS81_2026_10_21: this row had said all are mirrored; section 7) | the reader (C5, C17) |
| Working English, Hindi | on the passages; `translations_l10n` 15,602 | mirrored | the reader |
| Scholarly English | `scholar_translations` 5,569 rows (every version) | mirrored as `en-x-scholar` rows, 1,671 live (measured 21 Oct): each verse's latest English, made from its Sanskrit as it reads now, not rejected; one row for a sentence over several verses | the reader (C18, Phase AL) |
| Names | `entities` 13,145 (5,399 other, 3,378 deities, 2,910 persons, 771 places, 400 peoples, 201 rivers, 86 mountains); `entity_variants` 30,520; `entity_mentions` 41,059 | `corpus.entities` 13,145, `corpus.mentions` 40,054 (measured 21 Oct) | the name chips and /corpus/names (C6) |
| Meaning | `passage_embeddings` 26,345 | `corpus.passage_vectors` (28,166 counted with the retired rows; the live count by section 7's check) | search by meaning, similar passages (C1 to C3) |
| Stories, pictures | `brain_items` 95 (30 episodes, 33 images, 32 stories), `doc_stories` 62, `doc_images` 110 | mirrored | the Stories and media pages |
| The shelf, step 1 | `shelf_entries` 33,993; `shelf_refs` 88,999; `shelf_xrefs` 4,624; `shelf_links` 17,893 (ties to our names) | not mirrored (your decision: on the PC only; Cologne's CC BY-NC-SA 3.0) | no |
| The shelf, step 2 | data/shelf/claims.db: Part I complete, 2,010 claims of 99 pages; their names tied to our entities by `--link` (CLAIMS_LINK_2026_10_21, section 7) | not mirrored (B2) | no |
| Glossary | `scholar_glossary` 4,213 | not mirrored | no |

**So:** the text-to-name graph is wired end to end (a verse, the names in it, every other verse that names them). The
scholars' layer is wired on the PC only, and only at reading time: `scholar_claims.py --show NAME` joins a name's claims
to the indexes and to our entities by its key; nothing stores that join yet, and nothing of it is on the site.

## 2. Whose shoulders: the rule for the scholars' layer

We stand on Indian scholarship: Hemchandra Raychaudhuri, R. G. and D. R. Bhandarkar, Jadunath Sarkar, R. C. Majumdar,
B. C. Law, B. B. Lal, Sita Ram Goel, B. G. Tilak, and Bibek Debroy's translations as the standard of our English. The
colonial-era indexes (Macdonell and Keith's Vedic Index, Soerensen's Mahabharata names) are kept as what they are,
indexes of where a name occurs, never as the authority on it; Dikshitar's Purana Index, an Indian scholar's, comes first
on every name. A Western scholar's view inside a claim (Pargiter, Hopkins, Oldenberg) is named as his, and the stance
(asserts, reports, rejects, doubts) records whether our scholar accepts it or argues against it. Above all of them
stands the text itself: a claim is checked against the passage it cites, wherever we hold that passage.

**What each may be used for** (the Copyright Act, 1957, section 22: 60 years from the beginning of the year after the
author's death; I am not a lawyer, and this is not legal advice):

| Scholar | Died | In India | What we do with his work |
|---|---|---|---|
| H. C. Raychaudhuri | 1957 | public domain since 2018 | claims with their quotations; on the site too |
| R. G. Bhandarkar | 1925 | public domain | the same |
| D. R. Bhandarkar | 1950 | public domain since 2011 | the same (Raychaudhuri cites his Carmichael Lectures, 1918, 15 times in Part I) |
| B. G. Tilak | 1920 | public domain | the same |
| Jadunath Sarkar | 1958 | public domain since 2019 | the same (his field is mostly the Mughal and Maratha periods) |
| B. C. Law | 1969 | in copyright to the end of 2029 | private reading: claims as facts, with page and a short quotation; not on the site |
| R. C. Majumdar | 1980 | to the end of 2040 | the same (Raychaudhuri cites his Corporate Life in Ancient India) |
| Sita Ram Goel | 2003 | to the end of 2063 | the same |
| B. B. Lal | 2022 | to the end of 2082 | the same; a report he wrote for the Archaeological Survey is a government work (section 28: 60 years from publication), to be checked item by item |
| Bibek Debroy | 2024 | to the end of 2084 | the standard our English is measured against; never ingested or published (as the Mitrasamgraha rule) |

## 3. What tonight's audit of the claims found, and mended (CLAIMS_FIX_2026_10_21)

- **The run of Part I:** 83 of its 99 pages read, 1,703 claims; their quotations 1,423 exact, 179 close (the OCR's
  misreadings), 15 not on the page, 86 too short to check. 13 pages failed and 4 (pdf 109 to 112) were not read.
- **Why 13 failed:** all for one reason. The model copied the scan's own backslashes (`l\Iahabharata`, `1\fatsya`: the
  OCR's M) into a quotation without doubling them, which JSON does not allow. The replies were whole. `--reparse` reads
  them again from claims.db, free: 12 pages (pdf 21 had failed twice), 260 claims. On a copy: 1,963 claims of 95 pages;
  quotations 1,633 exact, 224 close, 18 not on the page, 88 too short.
- **The money:** a failed page's attempts were metered in usage_log but its read recorded $0; a read after failed
  attempts recorded only its last. From the stored replies the run cost about $1.43 (the ok reads $0.86, the failed
  attempts about $0.57); the run's own count, which stopped it, includes every attempt. `--report` now prints the
  meter's exact sum.
- **The cites:** 678 of 1,245 named no work the reader knew (the scan's misreadings: Visht}u Puralfa, RamayaQ.a; the
  Jatakas by name; the modern works; Ibid), and a work with no number after it had misread letters for its place. With
  cites-v2, on a copy: 780 read by the book's abbreviation or the work's words, 173 by a close spelling (0.80 to 0.95,
  the score kept), 46 a bare place after a cite on the same page ("after"), 33 by the sentence's work, 5 Ibid; 208 left
  as printed. A place a work cannot have is left unread (a sutra of Panini is adhyaya 1 to 8, pada 1 to 4). Cites to a
  text we hold: 23 before, 62 after.
- **The order on a name:** the Purana Index (Dikshitar) first, then the Vedic Index and Soerensen, each with its credit.

## 4. The Things to know of 21 Oct, answered

- **The Satapatha.** Not done yet. GRETIL holds the Madhyandina recension's kandas 1 to 11, 13 and 14 (kanda 12 "not
  available"), input by John Robert Gardner, from Vedavid; the entry states no licence of its own (GRETIL's general
  terms apply; DOCS81_2026_10_21: so GRETIL's index says; the kanda 11 file's own header credits H. S. Ananthanarayana
  and W. P. Lehman: section 7). Ours is book 14 only. Bringing kandas 11 and 13 in (Janaka's dialogues, Janamejaya's horse sacrifice)
  is your download to approve; the commands are in the RUNBOOK section of DOCS80.
- **Dikshitar's abbreviations.** Read from the shapes of his own 39,508 references: **Br.** is cited by pada I to IV
  (the Brahmanda's four padas), **M.** by adhyaya up to 291 (the Matsya has 291), **Bhā.** by skandha up to XII (the
  Bhagavata's twelve), **Vi.** by amsa V and VI (the Vishnu's six), **Vā.** by adhyaya (the Vāyu); Ib. is ibidem. That
  is the key the Purana Index's front matter prints, read from the evidence, to be confirmed against a scan of volume I.
- **Those five Puranas in our corpus.** None: our Puranas are the Markandeya (the scan, and GRETIL's e-text), the Padma's
  Patala Khanda (the Venkateshwar Press, 1895), the Nilamata, and the upapuranas Kapila, Narasimha, Parasara, Samba and
  Saura.
- **Repos and site, now:** the Automaton `df8b35ae` and Srangam `aec5d41` are pushed (local equals origin, no lock
  files). The site has the Surya's spelling (the 18:31 mirror run: 523 passages, 933 scholarly rows, 14 retired); its
  references and chapters go with the 20:31 run (the plan: 503 passages, 156 translation rows).

## 5. The path (each phase surgical, tested, reversible; free unless it says)

| Phase | What | Where | Cost |
|---|---|---|---|
| B0 | CLAIMS_FIX: `--reparse`, `--recite`, the last 4 pages of Part I | PC | about $0.03 |
| B1 | The scholars' layer stored as links: each claim's names tied to our entities (exact, a vowel's length, the 1923 spelling); each cite to a text we hold located in it where the numbering allows (the Nirukta, the Brihadaranyaka with its Madhyandina numbering noted; MBh01 only through a concordance of the vulgate and the critical edition, else "not located"); the checked claims published into context.db (a backup first) | PC | free |
| B2 | The mirror: docs/cloud C19 (corpus.claims, claim_cites, claim_names, keyed by work, page and n; a reader function by name behind the reader's gate); a `claims` group in corpus_sync.py; only public-domain works; the Cologne shelf stays home unless you decide | PC, Lovable Cloud SQL | free |
| B3 | The site: /corpus/names/NAME gets "What the scholars say": the claims with page, quotation and stance, the cites, and the verse in our text where it is located | Srangam kit | free |
| B4 | The Professor Bot: an answer only from what the brain holds (passages by meaning, names, claims, the scholarly English), every sentence tied to a row it retrieved, a judge of the other family, metered; on the PC first, then an edge function | PC, then Srangam | Google cap, per question |
| C | More scholars, Indian first: Raychaudhuri Part II; D. R. Bhandarkar's Carmichael Lectures; R. G. Bhandarkar's Early History of the Dekkan; Tilak; then the copyrighted works, privately. Each from a scan whose md5 is registered, with its page map, a three-page trial first | PC | about $0.01 a page |
| D | The texts the claims cite: authoritative e-texts where they exist (GRETIL's Satapatha first), our own OCR and vision editions where none does | PC | per text |
| E | Load and health: the mirror splits a slow batch itself (21 Oct: 514 rows as 257 + 257); the reader's functions measured with read-only EXPLAIN before any index is added | Lovable Cloud SQL | free |

## 6. Yours to decide

The Satapatha download (kandas 11 and 13, or all thirteen); whether the Cologne shelf goes on the site (CC BY-NC-SA
3.0: credit, non-commercial, share-alike); the copyrighted scholars, private only; the next scholar after Part II.

## 7. B1 done; the counts corrected; the Satapatha and the Carmichael Lectures; B2 designed (DOCS81_2026_10_21)

**B1, the claims tied to our names (CLAIMS_LINK_2026_10_21).** `scholar_claims.py --link` (free; data/context.db only
read) ties each name of the current claims (their subjects and objects) to our entities and stores the ties in
claims.db (`claim_links`, `claim_link_runs`). The tiers, the first that ties winning: exact (the shelf's own key); a
variant our texts record; a vowel's length; a 1923 spelling (Rigveda, Kurukshetra, Asvapati, Chhandogya: only for a
name without diacritics, the vowel r read as ri on both sides, doubled letters kept); then a numbered namesake
(Parikshit I and II, Janaka I and II, Satanika II: our texts name one of each) and an English plural (the Mallas).
Never tied: a common English word (king, god, goddess, raja: our variants hold such English glosses); a variant or a
spelling of a name without a capital; a plural by a variant, or where its last letter is not the entity's (the
Gandharis are not Gandhari). A name that could be more than one of ours keeps each, with how many it could be.

Measured on a copy of claims.db against the 18:41 backup of context.db (the PC's own run prints its numbers):

| What | Count |
|---|---|
| Names on the 2,010 current claims | 3,917 |
| Tied | 1,706 (44%), in 1,816 tie rows |
| How | exact 1,342; a 1923 spelling 172; a vowel's length 88; a variant 36; a numbered namesake 28; plurals 40 |
| Tied to more than one of ours | 110 |
| The most claimed of ours | Janamejaya 91, Parikshit 75, Janaka 60, Kosala 51, Kuru 45, Pancala 40, Anga 31, Nimi 30 |
| Untied, the most named | Brahmadatta 31, the Aitareya Brahmana 28, the Licchavis 23 (and Licchavi 9), Assaka 18, the Bhagavati Sutra 18, Bimbisara 18 |

**For the entity mender (nothing merged here):** our own doubles, one key and two entities: Satapatha Brahmana 5726
and Satapathabrahmana 5767 (20 names), Rajasuya 95 and rajasuya 5371 (10), Matsyapurana 7715 and Matsya Purana 7769
(5), Visnupurana 5882 and Visnu Purana 5885 (4), Kurupancala 5838 and Kuru-Pancala 7089, Suci 12386 and suci 12433,
Uttarakuru 1573 and Uttara Kuru 3635, Taittiriyasamhita 2257 and Taittiriya Samhita 2415. Some kinds are wrong: Anga,
a kingdom, is "other". The untied names are names our entity list does not have; most are of texts we do not hold
(the Jatakas, the Aitareya Brahmana, the Jaina and Buddhist canon): phase D.

**Only an exact tie is certain.** The site will show an exact or a numbered tie as the name's; the others as probable,
with how each was made; and a name that could be more than one of ours not at all until our doubles are merged.

**The counts, corrected.** Section 1 said every passage is mirrored. The site holds 99,966 live passages (your count,
21 Oct, 20:45 IST). The three withdrawn texts (data/source_verdicts.jsonl) hold 73,878 here (the Yoga Vasistha 70,292,
the Karanagama 1,909, the Bodhicaryavatara's scan 1,677) and are off the site by design, which leaves 100,141 here. The
mirror's own check at 20:31 found its 386 groups equal, so the 175 between are differences it makes by design; the
first to look at is the Hayasirsa (1,706 here), held in repair, whose last version the site keeps. The names: 13,145
entities on both; mentions 40,054 there, 41,059 here. The vectors: 28,166 was counted with the retired rows.
docs/cloud/CHECKS_brain_counts_2026-10-21.sql counts the live rows text by text; the RUNBOOK's command counts them here.

**The Satapatha, for the translator.**
- Ours: `2015_405693_Shatpath-Brahmanam`, an OCR of kanda 14 only (its register: complete, "what is left is not
  Sanskrit").
- The edition of record is Albrecht Weber's of the Madhyandina recension (Berlin, 1855): its numbering (kanda,
  adhyaya, brahmana, kandika) is the one Raychaudhuri cites (Sat. Br. XIII. 5. 4. 1-3). There is no critical edition in
  the modern sense.
- Two e-texts: the Sanskrit Library's TEI text of the Madhyandina Satapatha (all fourteen kandas, from Weber's edition;
  kanda 12 input by Makoto Fushimi; CC BY-NC-SA 3.0), the better text of record; and GRETIL's (kandas 1 to 11, 13 and
  14; 12 not available), unaccented IAST, numbered 11.1.1.[1], the numbers "added mechanically", "for reference
  purposes only", copyright and terms "as for source file".
- The dandas: the Satapatha is prose and its unit is the kandika; GRETIL marks one pause a kandika (DOCS83_2026_10_22: section 9). Ours would
  take them from a scan of Weber's print as a witness (Weber died in 1901: public domain), or mark what we add as
  editorial, never as the edition's. A kandika's end, with its number, is certain.
- With the whole text in, the Satapatha's cites in Part I can be located (the same numbering).
- Yours: which e-text (the Sanskrit Library's licence is non-commercial and share-alike, so our English of it would
  carry the same terms; GRETIL's asks for credit), and the download. From the PC, GRETIL gave "Unable to connect to
  the remote server"; the RUNBOOK's commands show why.

**D. R. Bhandarkar's Carmichael Lectures, 1918** (Lectures on the Ancient History of India on the Period from 650 to
325 B.C., University of Calcutta, 1919; public domain in India since 2011). Raychaudhuri cites them 15 times in Part I.
The scans: the National Virtual Library of India (the Central Secretariat Library's repository), AS-002576.pdf; and
HathiTrust's record 001867818 (full view). Yours: the download (the RUNBOOK's command asks for the size first). Then
its entry in scholar_claims.py's WORKS (md5, pages, the page map, its parts) and a three-page trial, about $0.03.

**B2, designed from the code (not built).** corpus-ingest (Srangam, `supabase/functions/corpus-ingest/lib.ts`) accepts
only its eight tables (`TABLES`) and maps each action to one C4 function; C4's `corpus_ingest` is one function with a
branch per table, and `corpus._spec` lists their keys. So B2 adds and replaces nothing the mirror runs on:
1. C19 (Lovable Cloud SQL): `corpus.claim_works`, `corpus.claims` (keyed by work, pdf page and n), `corpus.claim_cites`,
   `corpus.claim_links` (with the entity's canonical, the site's key of a name, how and cands); their own functions
   (`corpus_claims_manifest`, `_keys`, `_ingest`, `_retire`; service_role only), C4's untouched; a reader function,
   `corpus_reader_name_claims(canonical)`, behind the reader's gate, giving only claims whose quotation is exact or
   close, and only exact or numbered ties.
2. corpus-ingest: a second list of tables routed to those functions, tested beside lib_test.ts, deployed by Lovable.
3. corpus_sync.py: a claims group read from data/shelf/claims.db (only read), public-domain works only.
4. B3: the name page (CorpusNames.tsx) gets "What the scholars say": the claim, its page, its quotation, its stance,
   its cites and where we hold them.
## 8. The counts explained; the Satapatha's sources; the Carmichael Lectures' (DOCS82_2026_10_21)

**The counts, explained** (your SQL of 21 Oct, 21:41 to 21:44 IST, beside the 18:41 backup and your list of the
texts). Every live text has on the site exactly the passages it has here but one: the Hayasirsa, 1,531 there (sent on
8 Oct, 10:07 UTC) and 1,706 here, held in repair, so the mirror keeps its last version. That is the 175. The withdrawn
texts have no live passage there (the Yoga Vasistha 70,292 retired; the Karanagama 2,084 retired, its version before
the repair; the Bodhicaryavatara's scan 1,677 retired). The site's live rows: 65 texts, 99,966 passages, 19,573
translation rows (1,671 of them the scholarly English), 13,145 names, 40,054 mentions, 25,504 vectors (28,166 with the
retired). Here, in the live texts but the Hayasirsa: 39,808 mentions and 25,346 vectors; the Hayasirsa's new passages
have 0 mentions and 1 vector. So the site's 246 more mentions and 158 more vectors should be the Hayasirsa's held
version: docs/cloud/CHECKS_held_2026-10-21.sql, H1, will say.

**B1 on the PC** (21:32 IST): what the copy gave, 1,706 of 3,917 names tied, 1,816 tie rows, 110 to more than one of
ours.

**The Satapatha's sources, read again:**
- Its makers: H. S. Anantanarayana typed kandas 1 to 11, 13 and 14 (GRETIL's file headers: "Data input by H.S.
  Ananthanarayana and W. P. Lehman"), Makoto Fushimi kanda 12, and J. R. Gardner re-edited them; GRETIL's index names
  Gardner, the Sanskrit Library all three. The edition: Weber's (Berlin, 1855; issued from 1849, the year the Sanskrit
  Library gives; reprinted at Varanasi in 1964 as Chowkhamba Sanskrit Series 96).
- GRETIL: thirteen files, sb_01_u.htm to sb_14_u.htm without 12, under gretil/1_sanskr/1_veda/2_bra/satapath/; each
  kandika under its own line (13.1.1.[1]); IAST without the Vedic accents (DOCS83_2026_10_22: and without its ch; one danda a kandika in kandas 1 to 9, a
  double space in its place in 10 to 14: section 9); the pluti written 3, the
  avagraha an apostrophe. etext_witness.py reads that shape now (ETEXT_PROSE_2026_10_21): each kandika a passage with
  its reference, the adhyaya its chapter, no danda added.
- The Sanskrit Library's XML edition (2010, version 0.1, CC BY-NC-SA 3.0) has all fourteen kandas; its page gives no
  download. TITUS (Frankfurt) has Gippert's edition, its download restricted.
- A print with its dandas, by an Indian editor: Satyavrata Samasrami's Satapatha with Sayana's commentary (Bibliotheca
  Indica, the Asiatic Society, Calcutta, 1903 to 1912; Samasrami died in 1911: public domain), on archive.org in the
  item Bibliotheca_Indica_Series (volumes 2 and 7 seen there). It is the witness for the dandas: its pages read by
  vision OCR beside GRETIL's kandikas, the danda taken where the print has it.
- The Vedic Heritage Portal (IGNCA, the Ministry of Culture) shows a Madhyandina Satapatha in two volumes as page
  images; its copyright policy forbids reproducing them without IGNCA's written permission: to read beside ours, not
  to ingest.

**The Carmichael Lectures of 1918:** NVLI's host (icvtesting.nvli.in) does not answer, from the PC or from here;
HathiTrust gives its copies in full only in the United States ("public domain only when viewed in the US"), and
outside a member library a page at a time. Found on the way: D. R. Bhandarkar's Lectures on Ancient Indian
Numismatics (the Carmichael Lectures of 1921; Calcutta, 1921) on rarebooksocietyofindia.org, public domain, for
later. The 1918 lectures wait for NVLI's host or another scan.

**Why the PC could not download:** Invoke-WebRequest gives "Unable to connect to the remote server" where curl.exe
reaches GRETIL (HTTP 200). DOCS83_2026_10_22: not a proxy, as this said: the PC has none (WinHTTP: direct access;
ProxyEnable 0); why Invoke-WebRequest fails is not known. The downloads use curl.exe.
## 9. The Satapatha read in full, and what it lacks; the held counts confirmed (DOCS83_2026_10_22)

**The held counts, confirmed** (your H1 to H3, 22 Oct, 08:31 to 08:35 IST): the Hayasirsa's held version has 246
mentions, 158 vectors and 1,184 translation rows on the site, and every other text's mentions and vectors equal the
PC's, text by text. The site and the PC differ only where the mirror means them to.

**What the brain reaches** (the backup of 21 Oct, 22:08): of 100,141 live passages, 25,335 have the working English
(25%), and only those have a vector (25,347) and names (14,535 passages name someone), because build_embeddings.py and
extract_entities.py read the working English only. Outside the search by meaning and the names: the Padma's Patala
Khanda (21,128 passages, 2 with English), the Daivata Samhita (13,887, none), the Rgveda's volume ii (12,112, none),
the Markandeya from GRETIL (5,240, none, though 1,408 have the scholarly English), the Lalitavistara (4,335, 47), the
Manu and Harita smritis (2,568 and 2,477; 18 and 59), the Krishna Yajurveda (2,250, 42), the Akashabhairava Kalpa
(2,113, none), the Siddhanta Shiromani (1,146, none); the Surya's scholarly English (510) reaches neither. Phase E, two
ways: a vector and names from the scholarly English where there is no working English; the working English for the
large texts, priced by the meter.

**What the meter says each costs** (usage_log, the calls that succeeded): the working English with gemini-2.5-flash
$0.00058 a passage in October ($0.00033 over July to October); the names $0.00019 a passage; a vector $0.000015; the
scholarly English with Claude Sonnet $0.0128 (the Markandeya) to $0.0205 (the Surya) a passage. Google's cap: $80.39 of
$85 spent at 21 Oct, 21:21 IST.

**GRETIL's Satapatha, read in full (ETEXT_PROSE2_2026_10_22).** Its thirteen files (2,203,647 bytes, on the PC since
21 Oct, 22:07 IST) give 7,173 kandikas: kandas 1 to 11, 13 and 14 (835, 548, 859, 649, 470, 529, 398, 437, 402, 369,
437, 430, 810), 1,375,765 Devanagari characters, the longest 952. Beside the 13.1.1.[1] ETEXT_PROSE read, the numbers
come in other shapes: 18 with their brackets put in wrongly (1.1.3[.1]1 is 1.1.3.11), 2 with one bracket too many, 64
with none (all of 14.4.1, and the appendix's 14.3.2), 81 brahmanas' own numbers (as headings, or over a brahmana of one
kandika: 14.6.4.; 14.8.13 three times), one number glued to its text and mistyped (11.7.4.2 for 1.7.4.2); and in
kanda 14, after a line of asterisks, an appendix: five passages under 14.3.1. and 14.3.2.1 to 31 again, 21 word for
word (left out) and 10 not (kept, marked). Every kandika is prose: five had been typed colophons for a word in them.
The kanda 14 ingested on 21 Oct (2015_405693_Shatpath-Brahmanam__w_gretil, 745 passages, measured against our OCR:
50% of its readable pages, in order 98%) was read before these were known: its 14.4.1, its brahmanas of one kandika
and the appendix ran into the kandika before them (14.9.4.33 held 6,085 characters). It has no translation; the
RUNBOOK writes the whole Satapatha again as one text.

**What GRETIL's Satapatha lacks: its ch.** Not one ch or cch in the thirteen files: gacati for gacchati, candas for
chandas, papraca for papraccha. GRETIL's Mahabharata and Markandeya, beside them, have theirs (1,279 and 501). At their
share (0.8% of the words) about 1,200 words of the Satapatha have lost it; 246 of them could be put back from the words
of those two texts alone (gacati, prayacati), the rest only from another witness. So GRETIL's Satapatha is the
skeleton, every kandika with Weber's number, not yet the text of record: a witness, local, untranslated and
unreleased, until its ch is restored.

**The dandas GRETIL has:** one a kandika, after its first clause, written | in kandas 1 to 9 (801 in kanda 1's 835
kandikas) and as a double space in 10 to 14 (365 in kanda 10's 369). Whether the print has more inside a kandika is
to be seen on its pages.

**The witness for both, an Indian edition:** Satyavrata Samasrami's Satapatha (Bibliotheca Indica, Calcutta, 1903 to
1912) on archive.org, each volume as a PDF (volume 5 16.9 MB, 6 20.3 MB, 7 17.8 MB, 9 7.3 MB), a PDF with a text
layer, and archive.org's own reading (volume 5 973 KB of text, 6 1.18 MB, 7 1.05 MB, 9 391 KB, 4 only 44 KB). The
path: those readings first (free), measured against the skeleton; where poor, the pages by vision ($0.0034 a page);
then the skeleton's kandikas aligned with the print, the ch and the dandas taken where the print has them, each change
with its source. Kanda 12, not in GRETIL, comes from the print.

**Raychaudhuri's Satapatha:** 72 cites in Part I; 40 read to a kandika (13.5.4.1, Janamejaya's horse sacrifice, among
them), 5 of those in kanda 12; the rest misread by the scan (XIll. 5.1.11) or without a place.

**The Carmichael Lectures:** NVLI's server does not answer (TCP to 117.250.156.42:443 failed; ping timed out).
