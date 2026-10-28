## Phase AR - The historian's view beside the genealogies, and a search in the scholarly English (B2_SITE_2026_10_28, X1C_SITE_2026_10_28, 2026-10-28)

Asked on 28 Oct: "B2 (Raychaudhuri's view of each step), then searching the scholarly English (X1c)", and "i dont see
the inter relationships and the sizeable context ... using our own substantial sanskrit corpus, on the srangam site".
The desk weighs every kinship of the three indexes against Hemchandra Raychaudhuri's Political History of Ancient India
(1923; public domain: the author died in 1957), read from its scan page by page, each claim checked against the
page's own words (scholar_claims.py, kin_index.py). None of it was on the site; nor could the scholarly English be
searched there. Both now are, behind the readers' gate, from the mirror's own rows.

### AR.1 - What changes
- Database (automaton repo): docs/cloud/C23_index_claims_2026-10-28.sql (after C21): corpus.index_claims (the claims
  of public-domain works whose quotation was found on the page, exact or close; the names tied to ours with one
  candidate only, and how), corpus.index_statements.scholars, corpus.index_steps.scholar; eight of C21's functions
  replaced with the same signatures and the claims added (the tree's `texts` stay GRETIL's; the work comes apart as
  `works`); corpus._index_claim. docs/cloud/C24_scholar_search_2026-10-28.sql (after C22):
  public.corpus_reader_scholar_search(q, k, p_doc) over the live scholarly rows, with a partial GIN index. Checks:
  docs/cloud/C23_checks_2026-10-28.sql. The desk sends the claims with scripts/index_sync.py (scheme i2); before C23
  or before the edge function is deployed again the claims wait and the rest is sent and verified as before.
- supabase/functions/corpus-index/{index.ts, lib.ts}: the table "claims" (FN_VERSION i2). The browser never calls it.
- src/lib/indexSite.ts: the types (ScholarView, Claim, WorkInfo; Statement.scholars, Step.scholar, Tree.works and
  .claims, OfName.claims and .claims_n, Overview.works, each optional); the historian's chip after the texts' chips;
  stepStrength (the best of a step's evidence; how the persons were told apart does not count), lineCounts,
  verdictText, tieLabel (certain: the same name or with its number; probable: a spelling, a variant, a plural),
  claimPage, viewClaims; CLAIMS_CREDIT.
- src/components/corpus/ScholarClaims.tsx: new; a claim with the book's words as the scan reads them, the page as the
  book prints it, the stance, the names tied to ours (certain or probable) and the works it cites (ours linked).
- src/pages/corpus/CorpusGenealogy.tsx: the historian's view in a statement's evidence; a strip over the line, one
  button a step coloured by what it rests on, that chooses the step; the header counts the steps the historian states
  too and otherwise; "In our corpus": our names on the line, how often our texts name the person (C6), the names named
  with it (C20, said not to be a kinship), what the historians say of it (C23), by the same query keys as the name's
  page; the credits name the work apart from GRETIL's texts.
- src/pages/corpus/CorpusGenealogies.tsx: "The historians' view", the work with its count; the credits.
- src/components/corpus/InTheIndexes.tsx: "What the historians say" on /corpus/names/:canonical, eight claims and the
  count, drawn also for a name that no person of the indexes carries. src/components/corpus/IndexCredits.tsx: works.
- src/lib/scholarSite.ts: searchScholar (2 to 200 characters, at most 50 verses; the English's own marks taken out of
  the snippet; before C24 it says so). src/components/corpus/ScholarSearch.tsx: new; the search and its hits, each
  with two ways to the verse (beside the Sanskrit, the text as prose). src/pages/corpus/CorpusHome.tsx: a third way,
  "In the scholarly English". src/pages/corpus/CorpusScholarly.tsx: the search, over every text or one.
- src/__tests__/b2-site.test.tsx: new. index-site.test.tsx and scholar-site.test.tsx pass unchanged.

### AR.2 - Not done, named
- Only public-domain works are sent (Raychaudhuri, 1923). The copyrighted scholars stay on the desk.
- A claim whose quotation was not found on the page (short 88, none 18 on 28 Oct) is not sent; a name tied to several
  of ours is not tied on the site.
- The genealogy is drawn as a ladder with a strip, not as a graph; the Professor stays on the desk (metered there);
  meaning search over the scholarly English waits for its vectors (E2, which costs money).
- Hayasirsa Pancaratra (in repair) and the Karanagama (withdrawn) are not on the site by the desk's own release states.

### Invariants added (Phase AR)
67. A scholar's view is shown only from a work in the public domain, credited with its edition and rights apart from
    the Sanskrit texts' credit, and only beside the book's own words and page; its verdict is said as what the book
    states ("states it too", "another relation of the two", "the other way round"), never as a proof, and a name of the
    book is linked to ours only when one name of ours was found for it, said to be certain or probable.
68. A search in the scholarly English reads only live verses of live texts, behind the readers' gate, at most 50, and
    its snippet is text with [[ ]] marks, never HTML; before C24 the site says the search is not switched on.
