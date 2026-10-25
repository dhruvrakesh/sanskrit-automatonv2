# The genealogies of the indexes on Srangam (25 Oct 2026, night)

Markers: **INDEX_SITE_2026_10_25** (scripts/index_sync.py; the Srangam kit docs/srangam/INDEX_SITE_2026-10-25/, by
scripts/patch_srangam_index_site_2026_10_25.py; the mirror task's step, by scripts/patch_index_task_2026_10_25.py),
**C21_INDEX_SITE_2026_10_25** (docs/cloud/C21_index_site_2026-10-25.sql, its checks C21_checks_2026-10-25.sql, the
edge function docs/cloud/C21_corpus-index/) and **DOCS97_2026_10_25**. It follows docs/SCHOLAR_SITE_2026-10-25.md
(release `a551ac97`; Srangam `9cef3f6`, with C22 pasted and checked).

## 1. Why

Asked on 25 Oct: "i dont see the inter relationships and the sizeable context and vectors associated with tht and the
analysis and build up to that using our own substantial sanskrit corpus , on the srangam site via navigation etc. i
thought ill see the geneaologies of kings on a react front end and our carefully built db mirrored from local to
supabase!"

What the desk had and the site did not:

| On the desk | Made by | On the site before tonight |
|---|---|---|
| the kept relations of three indexes of names (22,021 distinct on 25 Oct), each checked against the entry's own words | kin_index.py (data/shelf/kin.db) | nothing |
| each relation's citations read in GRETIL's Sanskrit (both names in the cited verse, one, neither) | vamsa_check.py (data/shelf/vamsa.db) | nothing |
| the lines of descent, each step with what it rests on; the longest lines | vamsa_view.py, /vamsa | nothing |
| a name's relations in the indexes, the line through each homonym | relations_view.py, /relations | the name, its passages, the names one passage names beside it (C20) |

The mirror (C4) already carried the texts, the passages, our names and their mentions, the translations and the
vectors; the meaning search (search-corpus) and "Named together with" (C20) read them. The indexes' relations, the
verse checks and the lines were the desk's alone.

## 2. The path

```
data/context.db, data/shelf/kin.db, data/shelf/vamsa.db      (the PC; read-only, as the dashboard's /vamsa reads them)
  -> scripts/index_sync.py: the rows, by the same functions as /vamsa (vamsa_view._graph, _main_up, _main_down,
     _evidence, lines); no model; 6 s
  -> what differs only: the server's digest of each table, then its keys and hashes, then the rows (1,000 or 3 MB a
     request, gzip), then the keys the desk no longer has are deleted; verified by the digests again
  -> the edge function corpus-index (HMAC-SHA256 with CORPUS_SYNC_SECRET, as corpus-ingest; service_role inside)
  -> seven tables in the private schema corpus (C21; row level security, no grant to anon or authenticated)
  -> five reader functions behind the readers' gate (C5: signed-in readers only)
  -> /corpus/genealogies, /corpus/genealogies/<index>/<entry>, and "In the indexes" on /corpus/names/<name>
```

**The rows, 25 Oct** (context.db: the backup of 15:01 IST; kin.db and vamsa.db of 13:54; built in 5.9 s on the PC's
Linux workspace, 26.6 MB of JSON, 4.5 MB gzip):

| Table | Rows | What a row is |
|---|---:|---|
| index_texts | 11 | the three indexes and the eight texts whose verses are read, with edition and rights |
| index_persons | 14,979 | a person with a parent, a child or a spouse in an index: head word, sex where stated, how far the lines run, our name when tied, the line the desk draws up and down |
| index_steps | 10,861 | a step from parent to child: how the persons were told apart, both entries or one, the best check of the cited verse and of our passages, the epics' verses that name both, its statements, its verses |
| index_statements | 22,021 | a kept relation (all 23 kinds: family, marriage, siblings, rule, learning, time) with the entry's words and references, its checks and up to three of our passages that name both |
| index_lines | 53 | the longest lines of each index (six generations or more) |
| index_verses | 5,702 | a GRETIL verse where the checks found a name (shown texts only) |
| index_meta | 1 | the run: the marker, the scheme, the counts, when the verses were checked |

| Index | Persons in a line | Tied to our names | Steps | Steps whose cited verse names both | Relations | Longest line |
|---|---:|---:|---:|---:|---:|---:|
| Purana Index (Dikshitar, 1951-55) | 10,147 | 2,625 | 7,779 | 3,580 | 12,130 | 38 |
| Soerensen, Index to the Names in the Mahabharata | 3,773 | 1,010 | 2,909 | 0 | 8,495 | 24 |
| Vedic Index (Macdonell and Keith, 1912) | 275 | 54 | 173 | 0 | 1,396 | (none of six) |

The cited-verse check reads the Purana Index's citations of the Puranas GRETIL holds. Soerensen's references (to
the Calcutta Mahabharata) and the Vedic Index's are given as printed; for every step the verses of the Mahabharata,
the Harivamsa and the Ramayana that name both are counted.

On PostgreSQL 16 with these rows: the first sync 2.5 s, a second one sends nothing; a person's tree 23 to 26 ms (the
Purana Index's Janamejaya (VI), 34 generations, 98 kB of JSON), the overview 21 ms, a search 4 ms, a name 6 ms; the
seven tables 23 MB.

## 3. What is sent, and what is not

| What | On the site | Why |
|---|---|---|
| The indexes' relations, with the entry's own words and references | yes, credited, with the licence linked | H2: the Cologne Digital Sanskrit Dictionaries' digitizations, CC BY-NC-SA 3.0, while the site is non-commercial |
| GRETIL's verses where the names stand (Visnu 1910 and critical, Bhagavata, Brahmanda, Matsya 1-176, Harivamsa, Ramayana) | yes, credited (edition and data entry) | CC BY-NC-SA 4.0 |
| The Mahabharata e-text (BORI) | its counts and first references only; never a verse (C21 check E3: 0 and 0) | BORI asks that the text not be given to others |
| Our passages that name both | links into the reader, only of texts the mirror carries (corpus_sync.live_docs: 9,940 of 10,008 places; those of the withdrawn Karanagama and of two texts not on the site are left out) | the site is never sent a place it cannot open |
| The forms of the two names in a verse (to mark them) | only for a shown text | |
| Raychaudhuri's claims (the desk's "R agrees") | no | their mirror is B2 |
| The shelf's entries themselves | no | only the relations derived from them (H2) |

## 4. The pages

- **/corpus/genealogies**: the three indexes with their counts, edition and licence; a filter by index; "Find a
  person" by the index's own head word (folded as the desk folds it: diacritics, the honorific and the homonym's
  number left out, so "dasaratha" finds Dasaratha (I) and (II), the longer line first); the longest lines of each
  index, each opening on its eldest; the credits.
- **/corpus/genealogies/<index>/<entry>** (?via=<parent>): the line as the desk draws it (the father's line before the
  mother's, then the better attested step, then the longer line), the generations numbered from the person (-8 ...
  0 ... +25); each rung with its spouses, its other parents (with "line through" for one that has an entry), its
  siblings, a name the index gives without an entry in several places shown once with its count; between the rungs
  each step's chips (verse ✓, one name, MBh n, HV n, ours: together, a name only, the index alone; solid when both
  entries state it, dashed when one); the chosen step's statements: the entry's words and references, the GRETIL
  verse with both names marked (a long Harivamsa passage cut around the names until opened), the epics' verses in
  words, our own passages as links into the reader (?at=page.idx), our names as links to their pages; the children
  and grandchildren (the line's own child marked); the credits and the caution.
- **/corpus/names/<name>**: "In the indexes": the persons tied to the name, each a link to its line, and what the
  indexes state of it in the desk's groups (the family first), 12 shown of up to 80, with the count of the rest.
- The tab "Genealogies" in the corpus's own bar and the Corpus menu (Library no longer claims the address).
- Until C21 is pasted both pages say "not switched on yet" and the names page is as before; before the first sync
  the genealogies page says nothing has been sent; a refusal is a refusal.

Every word from the database is rendered as text; none as HTML (the tests put `<b>` in an entry's words).

## 5. The edge function corpus-index

Made as corpus-ingest is: `x-corpus-ts` (unix seconds, within 5 minutes) and `x-corpus-sig` = hex HMAC-SHA256
(CORPUS_SYNC_SECRET, ts + "." + body as sent), the body gzip or JSON, at most 8 MB sent and 48 MB unpacked. Actions:
hello and manifest (corpus_index_manifest), keys (corpus_index_keys), ingest (corpus_index_ingest, at most 2,000 rows),
delete (corpus_index_delete, at most 5,000 keys); each one database call as service_role; 401 signature, 400 request,
413 size, 422 the database's refusal, 500 and 503 configuration. The log line names the action and the counts, never
the rows. No config.toml entry (as corpus-ingest). Deploy it as it is.

## 6. The steps, in order

1. The automaton: `python scripts\patch_index_task_2026_10_25.py --check`, then without; `python
   scripts\patch_docs97_2026_10_25.py --check`, then without; the tests.
2. The site's SQL: P1 of docs\cloud\C21_checks_2026-10-25.sql; then the whole of docs\cloud\C21_index_site_2026-10-25.sql
   in one paste; then V1 and V2.
3. Srangam: the patcher (`--check`, then without), `npm run typecheck`, `npx vitest run`, `npm run build`, commit and
   push; ask Lovable to deploy supabase/functions/corpus-index as it is.
4. The PC: `python scripts\index_sync.py` (the plan: 53,628 rows to send), then `python scripts\index_sync.py --apply`;
   then E1, E2 and E3 of the checks; open /corpus/genealogies signed in.
5. From then on the mirror task sends what changed, last in each tick (`index_sync.py --apply --if-configured`).

Rollback: the DROP lines in C21's header (one paste); `git revert` of the Srangam commit; delete corpus-index in
Lovable Cloud; the task from scripts\corpus_mirror_task.ps1.bak_indextask_<date>. Nothing else depends on them.

## 7. What it cannot yet say

- A line follows the desk's rule, so it can join layers the texts keep apart: Soerensen's longest line runs Anga,
  Antardhaman, Havirdhaman, Pracinabarhis, Pracetas, Daksa, Aditi, Visnu, Brahman, Marici, Kasyapa, Indra, Arjuna,
  Abhimanyu, Pariksit, Janamejaya, a cosmogony joined to a dynasty through the indexes' own statements; each step says
  what it rests on, and many rest on the index alone. The caution stands on both pages.
- The cited-verse check covers the Purana Index only; Soerensen's citations are not read against the critical
  edition (its e-text may not be shown, and its numbering differs from Calcutta's).
- Siblings of identical head words (two entries "Suhma (II)") are ordered by entry on the site, by the desk's set
  order on /vamsa: 2 of 13 persons compared differed in that order only.
- Raychaudhuri's view of a step (B2); the Professor (it is metered on the desk); a search over the statements' words.

## 8. Tested

- The edge function: `deno test` lib_test.ts (8, the golden signature shared with corpus_sync.sign) and
  _test/handler_test.ts (7, the handler end to end with the gateway and the database faked).
- PostgreSQL 16: tests/test_index_site_pg_2026_10_25.py (24: 13 build tests without a database, 11 against C4, C4b,
  C5 and C21 applied twice, with the made-up shelf of test_vamsa: every person's tree equal to vamsa_view.tree, the
  gate, the service door, a row deleted and sent back, chunks of three rows).
- tests/test_srangam_index_site_2026_10_25.py (9: the patcher over a made-up checkout, the payload, C21's text, the
  task's patch replayed).
- A copy of Srangam's main (`9cef3f6`) in the PC's Linux workspace with the kit: `tsc` clean (app and node), Vitest 48
  files, 402 passed, 2 skipped (index-site 17), `vite build` 56 s (the two pages 3.4 and 4.3 kB gzip, their own chunks). The patcher's
  --check on the PC's own checkout: CHECK OK, 13 files.
- The pages drawn with the real rows (the overview, Janamejaya (VI) of the Purana Index, Soerensen's Janamejaya, a
  name), at 1280 and 390 pixels.
- A copy of the automaton repository there, the two patchers applied: 207 test modules, none failed.
