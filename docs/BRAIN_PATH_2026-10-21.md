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
| Passages | 174,019 | mirrored (row hashes, digests) | the reader (C5, C17) |
| Working English, Hindi | on the passages; `translations_l10n` 15,602 | mirrored | the reader |
| Scholarly English | `scholar_translations` 5,569 rows | mirrored as `en-x-scholar` rows | the reader (C18, Phase AL) |
| Names | `entities` 13,145 (5,399 other, 3,378 deities, 2,910 persons, 771 places, 400 peoples, 201 rivers, 86 mountains); `entity_variants` 30,520; `entity_mentions` 41,059 | `corpus.entities`, `corpus.mentions` | the name chips and /corpus/names (C6) |
| Meaning | `passage_embeddings` 26,345 | `corpus.passage_vectors` | search by meaning, similar passages (C1 to C3) |
| Stories, pictures | `brain_items` 95 (30 episodes, 33 images, 32 stories), `doc_stories` 62, `doc_images` 110 | mirrored | the Stories and media pages |
| The shelf, step 1 | `shelf_entries` 33,993; `shelf_refs` 88,999; `shelf_xrefs` 4,624; `shelf_links` 17,893 (ties to our names) | not mirrored (your decision: on the PC only; Cologne's CC BY-NC-SA 3.0) | no |
| The shelf, step 2 | data/shelf/claims.db: 1,703 claims of 83 pages (1,963 of 95 once `--reparse` is run) | not mirrored | no |
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
  terms apply). Ours is book 14 only. Bringing kandas 11 and 13 in (Janaka's dialogues, Janamejaya's horse sacrifice)
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
