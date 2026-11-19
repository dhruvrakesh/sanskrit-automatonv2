## Phase AU - The way in by vamsa: the Suryavamsa and the Candravamsa across the texts (VAMSA_WAYIN_2026_11_18, 2026-11-18)

Asked on 17 and 18 Nov: "have we made it easy for the user find geneaologies of kings via well known texts and king /
vansha names . surya and chandravanshas", and on 18 Nov, night, that "the geneaologies work should carry tool tips and
reference to dishitar, raychaudhary, bc law". Measured that night: of the 500 lines on the Dynasties page only 65 hold a
founder of the solar or the lunar line, because each line is one father's longest line in one text; the desk's G6c
(vamsa_align.py in the automaton repo) sets the same dynasty side by side across the texts from its founder (10
dynasties, 174 generations, 725 names of 17 texts). That is the way in, sent by index_sync.py into corpus.index_vamsas
(docs/cloud/C29_index_vamsas_2026-11-18.sql in the automaton repo).

### AU.1 - What changes
- src/pages/corpus/CorpusVamsas.tsx (new), at /corpus/genealogies/vamsas (src/App.tsx, lazy): the Suryavamsa (the solar
  line, the Videhas) and the Candravamsa (Pururavas's line and its branches), each dynasty with its founder, the texts
  that tell it and how they agree; the list comes without the generations (corpus_reader_index_vamsas(NULL)), a
  dynasty's generations when it is opened (corpus_reader_index_vamsas(key)), kept 10 minutes. Each text's name for a
  king opens that text's line on the Dynasties page; a hover shows its verse and words; each generation shows
  Dikshitar's person in the Purana Index (a link to the person's page) and Raychaudhuri's claims the site carries
  already (C23): on the name (a link to the name's page) and on the two of a step. A king found by a plain spelling.
- src/pages/corpus/CorpusDynasties.tsx: ?work=&line= opens that text and that line; a link to the vamsa page.
- src/pages/corpus/CorpusGenealogies.tsx: a link to the vamsa page; the Dynasties link says seventeen texts.
- src/lib/indexSite.ts: VAMSAS, the types, loadVamsas(), GEN_STATUS, dynastyLineHref(), the guide and the credit.
- supabase/functions/corpus-index/lib.ts: the table vamsas (deploy corpus-index again after C29 is pasted).
- src/__tests__/vamsas.test.tsx: new.

### AU.2 - Not done, named
- B. C. Law's Ancient Indian Tribes is in copyright in India to the end of 2029: it is read on the desk only; what we
  find with it beside these lines comes later as our own findings, each cited (the automaton's R1).
- Raychaudhuri's Political History begins with Parikshit: of 174 generations he names 21 by their name and one step by
  both its persons; a name he uses may be another person of that name, and the page says so.
- The per-text Dynasties page shows no scholar beside a step yet (only the Purana Index's word, as before).
- Who may read is unchanged: the readers' gate (corpus_reader_allowed).

### Invariants added (Phase AU)
71. The vamsa page asks the database for the dynasties without their generations, and for one dynasty's generations only
    when it is opened; a generation shows a scholar's claim only when the site carries that claim already, and no
    claim of a work in copyright is ever on it.
