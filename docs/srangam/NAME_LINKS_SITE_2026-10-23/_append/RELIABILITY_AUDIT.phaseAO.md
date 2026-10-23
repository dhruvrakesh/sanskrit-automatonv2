## Phase AO - Named together, on a name's page (NAME_LINKS_SITE_2026_10_23, 2026-10-23)

The desk now stores which names its texts name in one passage (the automaton's scripts/entity_links.py). The site
holds the same mentions already (corpus.mentions, mirrored), so it counts the same pairs itself: docs/cloud/C20 in the
automaton repo adds the materialized view corpus.name_links (two names in one passage of a live text; a passage
naming more than 12 names left out as a list, as on the desk), refreshed nightly by pg_cron at 04:40 UTC, and
public.corpus_reader_name_links(p_canonical, k) behind the reader gate.

### AO.1 - What changes
- src/lib/corpusLibrary.ts: NameLink and loadNameLinks (at most 50).
- src/pages/corpus/CorpusNames.tsx: a name's page lists "Named together with": each name, its passages and texts, a
  link to its own page and "first together" to the first passage that names both. The line under the heading says
  that being named together is not a kinship. The section is not shown until C20 is applied, nor when no name is
  named with it; the passages below are as before.
- src/__tests__/corpus-name-links.test.tsx: new (4 tests).
- Nothing stored changes on the site but C20's view and function; the desk sends nothing new.

### AO.2 - Not done, named
- The kinships the indexes state and Raychaudhuri's claims ("What the scholars say") are on the desk only; they come
  to this page with the claims' mirror (B2) and the decision H2 for the indexes' relations.

### Invariants added (Phase AO)
64. A name's page never presents two names named together as related: the count of shared passages is said to be a
    co-occurrence, and a kinship appears only with its source.
