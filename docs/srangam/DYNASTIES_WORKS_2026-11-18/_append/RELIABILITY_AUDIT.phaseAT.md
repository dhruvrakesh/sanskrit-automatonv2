## Phase AT - The dynasties, one work at a time; a name in plain letters (DYNASTIES_WORKS_2026_11_18, 2026-11-18)

Asked on 17 and 18 Nov: "have we made it easy for the user find geneaologies of kings via well known texts and king /
vansha names ... locally and on srangam", and "surgical changes that dont kill it, rather heal it and improve load
times". The desk now reads the genealogies of 17 works (vamsa_read.py) and can send all of them by the road the first
three take (index_sync.py --dynasty-works every, VAMSA_SITE_2026_11_18 in the automaton repo). The page asked for every
work's rows at once (loadDynasties(null)): 106 rows, 123 kB in corpus.index_dynasties on 18 Nov; with every work, 517
rows, about four times as much.

### AT.1 - What changes
- src/pages/corpus/CorpusDynasties.tsx: the page asks for the chosen work's rows only (loadDynasties(work), kept 10
  minutes by react-query); the texts' buttons come from WORK_ORDER, so they show before any row; a text whose lines
  have not been sent yet says so ("No dynasty of this text has been sent from the desk yet."); the find box matches
  names typed in plain letters (foldPlain).
- src/lib/indexSite.ts: WORK_ORDER and WORK_TITLE name the 17 works (the three of before first); foldPlain(), the desk's
  rule (vamsa_register.qkey): the nasals an n, the visarga dropped, sh, ch, double vowels and ri set aside on both
  sides. For finding only; nothing is joined by it.
- src/__tests__/dynasties.test.tsx: the first call asks for vip4; "nothing sent" is said of the text. New:
  src/__tests__/dynasties-works.test.tsx.

### AT.2 - Not done, named
- A way in by vamsa (Suryavamsa, Candravamsa) across the works waits for the desk to tag each line with its dynasty.
- The page stays behind the readers' gate (corpus_reader_allowed); who may read is unchanged.
- The 14 other works appear on the site only after the desk sends them (index_sync.py --dynasty-works every --apply).

### Invariants added (Phase AT)
70. The Dynasties page asks the database for one work's lines at a time, never for every work's at once; a name typed
    in plain letters finds its IAST form there, and that rule finds, it never joins two persons.
