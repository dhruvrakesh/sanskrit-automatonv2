# The scholarly English on Srangam as the desk has it; the rounds and the kinships mended (25 Oct 2026, evening)

Markers: **SCHOLAR_SITE_2026_10_25** (the Srangam kit docs/srangam/SCHOLAR_SITE_2026-10-25/, by
scripts/patch_srangam_scholar_site_2026_10_25.py), **C22_SCHOLAR_SITE_2026_10_25** (docs/cloud/C22_scholar_site_2026-10-25.sql,
checks C22_checks_2026-10-25.sql), **PROSE_EDITION_2026_10_25** (export_html.py, publish_editions.py),
**KIN_SALVAGE_2026_10_25** (kin_index.py), **VAMSA_NAMES_2026_10_25** (vamsa_check.py), **AUTO_TRANSLATE_2026_10_25**
(repair_auto.py, health_watch.py), **ESCAPES_2026_10_25** (the two patchers of the morning) and **DOCS96_2026_10_25**.
It follows docs/VAMSA_2026-10-25.md (release `422cb349`; Srangam `341cf7f`).

## 1. Why the site did not have it

Asked on 25 Oct: "why isnt scholary and prose available on srangam? i thought we were getting the best bits of our
local app on srangam online."

**On the desk** (scholar_translations, the latest row of each verse; read from the backup of 15:01 IST, read-only):

| Text | Verses | Passed | Flagged or doubted | On the site? |
|---|---:|---:|---:|---|
| HAYASHIRSHA_PANCARATRA | 1,431 | 1,195 | 236 | no: in repair since 11 Oct (the mirror holds it; the site keeps its last version) |
| markandeya_purana__w_gretil | 1,408 | 1,291 | 117 | yes: released 19 Oct; two editions public |
| Karanagama (Shaiva Bharati) | 1,018 | 867 | 151 | no: withdrawn 16 Oct (the editor's Hindi was translated as if Sanskrit) |
| jyotish_surya_siddhanta__w_etext | 510 | 415 | 95 | yes: released 21 Oct; its edition is off |
| MBh01 | 24 | 19 | 5 | yes (a pilot) |
| tantric_texts_series_edited_by_arthur_av | 16 | 10 | 6 | yes (a pilot) |

**On the site** before this build:
- /editions, open to everyone: two static editions, both of the GRETIL Markandeya (the Devimahatmya, 669 verses;
  adhyayas 19 to 31, 739), made on 18 Oct; verse by verse only.
- /corpus/<doc>, signed-in readers: the scholarly English above the working English, verse by verse (C18, Phase AL).
  The mirror is whole: the run of 14:33 IST checked 368 groups, 0 different.
- **Missing:** the desk's /scholar (every text with a scholarly English, with its counts) and /scholar/<doc>/prose
  (the text read as a book). Nothing in the site's library said which texts have a scholarly English.

## 2. What this build does

**The site's SQL (C22).** One partial index (the live scholarly rows) and two read-only functions behind the
readers' gate: `corpus_reader_scholar_docs()` (each live text with a scholarly English: verses, flagged, accepted,
the judge's mean fidelity, its first such verse and that verse's place in the reader) and
`corpus_reader_scholar_prose(p_doc, p_after_page, p_after_idx, p_limit)` (one text's scholarly rows in reading order,
at most 500 a call, after a (page, idx)). Nothing else changes; the mirror and its ingest are untouched. Tested on
PostgreSQL 16 with C4, C4b, C5 and C18 (tests/test_scholar_site_pg_2026_10_25.py: 8, with C18's 4).

**The site (the kit).** /corpus/scholarly (every text, "As prose" and "Verse by verse, beside the Sanskrit") and
/corpus/<doc>/prose (chapter by chapter; the chapters as the edition makes them, export_html.py _ref_chapters; a
sentence over verses whole after its range; a paragraph where a speaker begins; each verse number opens the verse
beside its Sanskrit; the notes at each chapter's end; a flagged verse underlined). A tab "Scholarly English" in the
corpus's own bar and in the Corpus menu; "read it as prose" beside the reader's count. 300 rows a call, the next as
the reader nears the end, or on "Read on". The new pages are their own chunks (3.2, 6.3 and 8.9 kB). Until C22 is
pasted both pages say so. RELIABILITY_AUDIT Phase AP (invariant 65). Found and mended on the way:
`npm run typecheck` failed on main at src/pages/Editions.tsx (r.error on a union the site's tsconfig does not narrow,
since Phase AK).

**The prose for everyone (PROSE_EDITION).** export_html.py --scholar --prose writes the edition read as prose (no
Sanskrit, the verse numbers small, the edition's chapters, notes and daggers); publish_editions.py writes it beside
each edition, public/scholarly/<slug>-prose.html, each page's bar linking the other, the index naming it; /editions
links it. The two verse editions are written once more (their bar gains the link).

## 3. The rounds and the kinships, mended

**KIN_SALVAGE.** The full run's overrun ($0.22 where the plan said $0.04) was two of Soerensen's longest entries,
12641 and 7692: each reply was cut short at about 20,000 characters, was not the JSON asked for, and was asked again,
three times a run. The six failed reads cost $0.388 in all. Read again from the store (free): 113 relations whole in
12641's last reply and 86 in 7692's. Now a cut reply keeps what it gives and is not asked again; in a call of one
entry every relation is that entry's (the model numbered them 150 and on); an entry that failed twice is given up
until --retry-failed; `--salvage` keeps the stored replies' relations, free.

**AUTO_TRANSLATE.** The dry run's "blocked" came from five texts whose morning judgement said "into the database" and
whose fresh step said "translate it": each was a try, and the five tries were spent before the vision work. Now a
decision, or a text ready to translate, is not a try; what is found waiting today is not asked again today; a text
ready to translate is listed with its price (redeem.py's measured price of a flash passage) and is not a block; and
the rounds translate, English then Hindi, only the texts you allow (`--allow-translate X --usd N`), at most $0.25 a
round, above the cap's reserve, not while the dashboard runs a job. A text in repair may be one of them (the Shukla
Yajurveda: 20 of 1,225 passages in English since its repair; the Taittiriya: in repair since 14:02 IST, 2,240
passages, 42 in English before); its release stays yours. The debris guard (exit 3; the Sama Veda's scan still reads
as half debris) or the register (exit 4) refusing is written down once. Translation is not paid from the repair's
$0.25 a day. swaps_per_day (1); the pre-repair backups counted (each 1.1 to 2.2 GB in D:\backups).

**What translating costs now** (redeem.py's price, measured on usage_log since the thinking is counted: $0.0047 a
flash passage; read from the backup of 15:01 IST): the Shukla Yajurveda 1,205 passages to English and 1,225 to Hindi,
about $11.48 (less: the cache answers the passages its repair did not change, free); the Taittiriya 2,273 and 2,273,
about $21.48; the Sama Veda 520 and 520, about $4.92 (refused by the debris guard until its scan is mended); the GRETIL
Sama Veda 468 and 468, about $4.42. At $0.25 a round the rounds translate about 53 passages a round (translate_round_usd
in data/auto_repair.json raises it). The cap had $13.72 left at 15:01 IST, $1.00 of it kept in reserve: the Shukla
Yajurveda's English first (--usd 6.00), then its Hindi when you raise its allowance.

**VAMSA_NAMES.** vamsa_check.py --name shows a statement once ("x n", with its best check) and counts the distinct ones.

**ESCAPES.** The morning's two patchers printed SyntaxWarnings on Python 3.12 and later; their docstrings now write a
backslash as two.

## 4. Tested

- PostgreSQL 16 (the session's workspace): C22 and C18, 12 tests.
- A copy of Srangam's main in the PC's Linux workspace, the kit applied by its patcher (CHECK OK, 11 files, then
  "Nothing to do"): `tsc` clean (app and node), Vitest 47 files, 385 passed, 2 skipped, `vite build` in 42 s.
- A copy of the automaton repository there, the five patchers applied in order: 204 test modules, none failed.

## 5. Not yet

- G3, the indexes' relations and the lines of descent on the site (C21, an edge function, index_sync.py, the name
  page's "In the indexes"): next.
- Search over the scholarly English (X1c); the Surya Siddhanta's edition (95 of its 510 verses flagged: a person's
  reading first).
