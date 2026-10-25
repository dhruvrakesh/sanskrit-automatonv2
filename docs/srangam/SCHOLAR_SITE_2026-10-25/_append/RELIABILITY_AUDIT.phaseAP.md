## Phase AP - The scholarly English as the desk has it: every text, and each as prose (SCHOLAR_SITE_2026_10_25, 2026-10-25)

Asked on 25 Oct: "why isnt scholary and prose available on srangam? i thought we were getting the best bits of our
local app on srangam online." The desk has /scholar (every text with a scholarly English, with its counts) and
/scholar/<doc>/prose (the text read as a book). The site had the scholarly English only verse by verse inside the
reader (Phase AL) and in two static editions (Phase AK); nothing listed the texts that have it, nothing read it as
prose, and the library did not say which texts have it.

### AP.1 - What changes
- docs/cloud/C22 in the automaton repo: a partial index on the live scholarly rows, and two reader functions behind
  the gate: corpus_reader_scholar_docs() (every live text with a scholarly English: its verses, flagged, accepted,
  mean fidelity, first such verse and its place in the reader) and corpus_reader_scholar_prose(doc, page, idx, n)
  (one text's scholarly rows in reading order, at most 500 a call, after a (page, idx)).
- src/lib/scholarSite.ts: the loaders; the chapters as the edition makes them (export_html.py _ref_chapters and
  _section_key: the verses' own two-part references when half or more carry one, a heading with the next verse, a
  colophon with the one before; else a numeric chapter; else the scan page); the paragraphs (a speaker begins one, eight
  verses at most); each note numbered after its anchor's first appearance, the translator's doubt last.
- src/pages/corpus/CorpusScholarly.tsx: /corpus/scholarly, every text in scholarly English with its counts, "As prose"
  and "Verse by verse, beside the Sanskrit" (the reader at its first such verse).
- src/pages/corpus/CorpusProse.tsx: /corpus/:docCode/prose, chapter by chapter; each verse number opens the verse
  beside its Sanskrit (?at=); the notes at each chapter's end; a flagged verse underlined, its standing as its title;
  PROSE_BATCH (300) rows a call, the rest as the reader nears the end or on "Read on".
- src/App.tsx: the two routes (before /corpus/:docCode). src/components/corpus/CorpusNav.tsx: the tab "Scholarly
  English" (current on both pages; Library no longer claims /corpus/scholarly). src/components/navigation/CorpusMenu.tsx:
  the same in the Corpus menu. src/pages/corpus/CorpusDoc.tsx: "read it as prose" beside the header's count.
- src/lib/editions.ts, src/pages/Editions.tsx: an edition's prose page (public/scholarly/<slug>-prose.html, written by
  the automaton's publish_editions.py with PROSE_EDITION_2026_10_25) is linked when the index names it, and only its
  own. Editions.tsx read r.error on a union that the site's tsconfig (no strictNullChecks) does not narrow on !r.ok:
  `npm run typecheck` failed there since Phase AK; it now reads `'error' in r`.
- src/__tests__/scholar-site.test.tsx: new.
- Until C22 is pasted both pages say so (the reader and the editions are as before); nothing else asks for it.

### AP.2 - Not done, named
- Search over the scholarly English (words and meaning) still reads the working English (X1c).
- The Hayasirsa's 1,431 verses are held while the text is in repair, and the Karanagama's 1,018 are withdrawn; they
  reach these pages when the desk releases them.

### Invariants added (Phase AP)
65. The scholarly English is shown only from the mirror's own rows, labelled as such and as machine translation; a
    verse flagged by the judge and not yet read by a person is marked wherever it is read (verse by verse or as prose),
    and the prose never shows a verse given with an earlier one twice.
