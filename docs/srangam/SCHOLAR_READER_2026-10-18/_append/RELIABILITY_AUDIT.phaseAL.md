## Phase AL - The scholarly English in the reader (SCHOLAR_READER_2026_10_18, 2026-10-18)

Asked on 18 Oct: "why is only 1 scholarly text available on srangam.. i thought we had a complete mirror from local
to srangam.. like a react based browser through our local db". The mirror (8 Oct) carried every live text's working
English, Hindi, names, stories and vectors; the automaton's scholarly English (14 Oct) came after it and reached the
site only as a static edition (/editions, Phase AK).

### AL.1 - What changes
- The automaton's corpus_sync.py (SCHOLAR_MIRROR_2026_10_18) sends a verse's scholarly English into
  corpus.translations beside the Hindi: lang `en-x-scholar` (the English; translation_score its fidelity,
  translation_qa its fluency) and `en-x-scholar-meta` (JSON: status, flag, accepted, judge, notes, doubts, range,
  with). Only a verse's latest version, made from its Sanskrit as it reads now, not rejected by a person. Every reader
  function asks for lang `hi`, so nothing shown changed until the reader asked for the new rows.
- docs/cloud/C18 (automaton repo): `public.corpus_reader_scholar(p_doc, p_offset, p_limit)`, the scholarly rows of
  the window corpus_reader_page reads, and `public.corpus_reader_scholar_count(p_doc)`; both behind the reader's gate
  (signed-in readers), SECURITY DEFINER, search_path ''.
- src/lib/corpusMirror.ts: loadMirrorScholar, loadMirrorScholarCount. src/lib/scholarReading.ts: the rows parsed
  defensively (a malformed meta row gives the English alone), *terms* as italics without HTML, the engines named, a
  verse's standing (judged faithful, flagged by the judge, the Sanskrit in doubt, read by a person).
- src/components/reader/ScholarEnglish.tsx: the scholarly English, labelled, its standing as a chip, its notes,
  doubts, maker and judge in a popover; a verse whose sentence is given with an earlier verse says so.
- src/components/reader/PassageBlock.tsx: the scholarly English above the working English, which folds under it
  ("Working English (machine)"); a verse with a scholarly English is never "Not translated yet". Without one, as before.
- src/pages/corpus/CorpusDoc.tsx: the count once a text, the page's rows only for a text that has them (and the next
  page's prefetched); the header's "N in scholarly English" and a line saying what it is.
- src/__tests__/reader-scholar.test.tsx (16 tests).

### AL.2 - Load
- One small call a text (the count). For a text with scholarly English, one more call a page (50 passages, two
  primary-key lookups each), prefetched with the next page. A text without it asks nothing more. Before C18 is pasted
  the count fails quietly and the reader is exactly as before.

### Invariants added (Phase AL)
59. The reader shows a scholarly English only from the mirror's own rows (corpus_reader_scholar), labelled as such
    with its standing; it never renders their text as HTML, a malformed row never breaks a page, and a reader without
    C18 is the reader as it was.
