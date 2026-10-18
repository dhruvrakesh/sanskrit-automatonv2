# The scholarly English in the mirror and in Srangam's reader (18 Oct 2026, night)

Markers: **SCHOLAR_MIRROR_2026_10_18** (scripts/corpus_sync.py, by scripts/patch_scholar_mirror_2026_10_18.py),
**C18_READER_SCHOLAR_2026_10_18** (docs/cloud/C18_reader_scholar_2026-10-18.sql, checks C18_checks_2026-10-18.sql),
**SCHOLAR_READER_2026_10_18** (the Srangam kit docs/srangam/SCHOLAR_READER_2026-10-18/, by
scripts/patch_srangam_scholar_reader_2026_10_18.py) and **DOCS76_2026_10_18**. It follows
docs/EDITIONS_SITE_2026-10-18.md (`ecd71e52`; Srangam `707effd9`).

Asked on 18 Oct (night): "why is only 1 scholarly text available on srangam.. i thought we had a complete mirror from
local to srangam.. like a react based browser through our local db. is this done".

## 1. Why one, in plain words

There are two Englishes in the brain. The **working English** (Tier R and T2: fast, every passage) and the
**scholarly English** (scholar_translate.py: slow, a verse at a time, in the register of an unabridged critical
translation, with notes, read by a critic, judged against the Sanskrit).

- **The mirror is complete for what it was built to carry.** corpus_sync.py (8 Oct) sends every live text's passages,
  working English, Hindi, names, stories, stages and vectors to the site's private copy, every two hours, and checks
  every group after (18:33 IST: 374 groups equal, 0 different). The React reader at /corpus/<doc> reads that copy.
- **The scholarly English came six days later** (14 Oct) in its own table, and nothing sent it. So the reader never had
  it, and the only way it reached the site was the static edition (/editions, 18 Oct afternoon).
- **Editions are published only for a finished, judged text.** On 18 Oct that was the Devimahatmya alone. Adhyayas 19
  to 31 were waiting for their re-judge (done since: 659 passed, 76 flagged, 4 doubted of 739); the Surya Siddhanta has
  20 of 515; the Hayasirsa is held in repair; the Karanagama is withdrawn; MBh01 (24) and the Tantrabhidhana (16) are
  pilots.
- **Both Markandeya texts with scholarly English are a GRETIL witness** (`markandeya_purana__w_gretil`), and a witness
  stays on the PC until it is adopted (`repair_text.py --release`). The scan-based Markandeya on the site is a
  different text code.

## 2. What this build does

**The mirror (SCHOLAR_MIRROR_2026_10_18).** Each verse with a current scholarly English travels as two rows of the
site's `corpus.translations`, beside the Hindi:
- `en-x-scholar`: the English; `translation_score` its fidelity and `translation_qa` its fluency (1 to 5, the judge's);
  the engine, the prompt version, the date;
- `en-x-scholar-meta`: JSON: status (passed, flagged, source_doubt), flag (waits for a person), accepted (a person
  read it), the judge, the notes and the doubts (on a sentence's first verse), the range of a sentence over several
  verses (on its first verse) and "with" (on the others, which have no English row).

As the edition takes them: a verse's latest version, made from its Sanskrit as it reads now (src_hash), not rejected
by a person. A rejected or stale verse's rows are retired on the site. Nothing else changes: the Hindi rows and every
other table keep their hashes (SCHEMA_VERSION stays c4.1), the ingest and the edge function take any lang, and every
site function asks for lang 'hi'. A witness stays local until adopted; a text in repair is held; a withdrawn one retired.

**The site (C18).** Two read-only functions behind the reader's gate (signed-in readers):
`corpus_reader_scholar(p_doc, p_offset, p_limit)` (the scholarly rows of the window corpus_reader_page reads) and
`corpus_reader_scholar_count(p_doc)` (how many verses have one, how many wait for a person). No table, no index (the
primary key serves both), no change to any other function. Tested on PostgreSQL 16 with C4, C4b and C5
(tests/test_reader_scholar_pg_2026_10_18.py: 4).

**The reader (the Srangam kit).** On /corpus/<doc>, a verse with a scholarly English shows it first, labelled
"Scholarly English", with its standing as a chip (judged faithful; flagged by the judge; the Sanskrit in doubt; read by
a person), a sentence's range, and a popover with its notes, doubts, maker and judge; *terms* in italics, nothing
rendered as HTML. The working English folds under it ("Working English (machine)"). A verse whose sentence is given
with an earlier verse says so. The header counts "N in scholarly English" and says what it is. One call a text (the
count); one a page only for a text that has them (prefetched with the next page). Before C18 is pasted the reader is
exactly as before. Tests: src/__tests__/reader-scholar.test.tsx (16), run here on the site's own React, Testing
Library, Radix and Vitest with the six reader suites (68 passed), the TypeScript clean.

**The editions.** Adhyayas 19 to 31 are on in configs/editions.json (judged; every tenth sentence audited by Claude
Opus 5.5, 91 readings), with a subtitle from their own first verses: Kartavirya and Dattatreya; Kuvalayasva and
Madalasa; Madalasa's teaching of Alarka (the householder's duties, the sraddha).

## 3. In order (the commands are in RUNBOOK.md, DOCS76)

1. The automaton: the two patchers, the tests, DOCS76; release.
2. The site's SQL: C18 in the Lovable Cloud SQL editor (checks E1, P1 before; V1, V2 after).
3. Srangam: the kit, typecheck, tests, build; the editions (publish_editions.py --apply); commit and push.
4. The first mirror run with the scholarly rows: MBh01 and the Tantrabhidhana (they are live).
5. **Yours to decide:** adopt the GRETIL Markandeya (`repair_text.py --doc markandeya_purana__w_gretil --release
   --force`): 5,240 passages of Sanskrit and IAST go on the site as a text of their own, 1,408 of them with scholarly
   English (adhyayas 19 to 31 and the Devimahatmya), no working English yet. --force because it has no working English;
   the GRETIL licence is already decided (credit, CC BY-NC-SA 4.0). The scan-based Markandeya stays as it is.
6. Then E1 and E2 of the checks show what arrived.

## 4. Not yet

- **Search** over the scholarly English (words and meaning): the reader shows it; search still reads the working
  English (X1c).
- **The published reader** (/texts/<doc>, srangam_texts) shows the working English only.
- **The Hayasirsa** (1,431 verses in scholarly English; 236 flagged or doubted not yet read): held in repair, so
  neither mirrored nor published until you lift the hold. **The Karanagama** stays withdrawn until it is made again
  from the Sanskrit alone.
- **The Surya Siddhanta:** 472 verses to make (the dry run: $16.43), then its edition and its adoption.
