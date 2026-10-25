## Phase AQ - The genealogies of the indexes, each step with what it rests on (INDEX_SITE_2026_10_25, 2026-10-25)

Asked on 25 Oct: "i thought ill see the geneaologies of kings on a react front end and our carefully built db mirrored
from local to supabase!" The desk reads the kinships of three indexes of names (the Purana Index, Soerensen's index to
the Mahabharata, the Vedic Index: kin_index.py), checks each against the Sanskrit verse it cites (vamsa_check.py) and
against our own passages (entity_links), and draws the lines of descent (/vamsa). None of it was on the site.

### AQ.1 - What changes
- docs/cloud/C21 in the automaton repo: seven tables in the private schema corpus (index_texts, index_persons,
  index_steps, index_statements, index_lines, index_verses, index_meta), filled by the PC's scripts/index_sync.py
  through the edge function corpus-index (HMAC-signed with CORPUS_SYNC_SECRET, as corpus-ingest), and five reader
  functions behind the readers' gate: corpus_reader_index_overview(), corpus_reader_index_lines(source),
  corpus_reader_index_find(fold, source, k), corpus_reader_index_tree(source, entry, via, down),
  corpus_reader_index_of_name(canonical). The overview, a tree and a name come as one row (result jsonb).
- supabase/functions/corpus-index/{index.ts, lib.ts}: new; the desk's signed door (hello, manifest, keys, ingest,
  delete), each one call of a C21 service function as service_role; the browser never calls it.
- src/lib/indexSite.ts: the loaders; the head word folded as the desk folds it (relations_view.fold of split_mark);
  each step's chips as the desk draws them (vamsa.html verdict); the citations' verses as the desk shows them, two at
  most, only of texts whose words may be shown; the names marked without any HTML from the server.
- src/pages/corpus/CorpusGenealogies.tsx: /corpus/genealogies, the three indexes with their counts and credits, a
  search by head word (?q=, ?source=), the longest lines of each index, each opening on its eldest.
- src/pages/corpus/CorpusGenealogy.tsx: /corpus/genealogies/:source/:entry (?via= a parent): the line as the desk draws
  it, the generations numbered from the person; each rung with its spouses, its other parents ("line through" for one
  with an entry) and its siblings, a name given without an entry in several places once with its count; between the
  rungs each step's chips; the chosen step's statements with the entry's words and references, the GRETIL verse where
  both names stand (a long passage cut around the names until opened), the epics' verses counted, our own passages as
  links into the reader (?at=), our names as links to their pages; the children and grandchildren; the credits.
- src/components/corpus/IndexCredits.tsx, src/components/corpus/InTheIndexes.tsx: new; the second on
  /corpus/names/:canonical ("In the indexes": the persons tied to the name, each a link to its line, and what the
  indexes state of it in the desk's groups, the family first), drawn only when there is something to show.
- src/App.tsx: the two routes. src/components/corpus/CorpusNav.tsx: the tab "Genealogies" (Library no longer claims
  /corpus/genealogies). src/components/navigation/CorpusMenu.tsx: the same in the Corpus menu.
  src/pages/corpus/CorpusNames.tsx: the section. src/__tests__/index-site.test.tsx: new.
- Until C21 is pasted both pages say so and the names page is as before; before the desk's first sync the
  genealogies page says nothing has been sent.

### AQ.2 - Not done, named
- Raychaudhuri's claims (the desk's "R agrees") are not on the site: their mirror is B2.
- The Professor (the desk's "Ask the Professor about this step") stays on the desk: it is metered there.
- A line follows the desk's rule (the father's line before the mother's, then the better attested, then the longer),
  so it can join layers the texts keep apart (Aditi, Visnu, Brahma, Marici, Kasyapa, Indra, Arjuna in Soerensen's
  index); each such step says what it rests on, and many rest on the index alone.

### Invariants added (Phase AQ)
66. A step of a genealogy is shown with what it rests on, and only that: the index's own words and references (the
    Cologne digitizations, credited, with their licence's notice, CC BY-NC-SA 3.0), the Sanskrit of GRETIL's texts
    only (credited; the Mahabharata e-text's verses are counted and referred to, never quoted), our own passages only
    in the texts the mirror carries; the caution that a verse where both names stand does not by itself prove the
    relation is on both pages of the genealogies.
