## Phase AM - An e-text's noise is not a scanner's (ETEXT_NOISE_2026_10_21, 2026-10-21)

Found on 21 Oct, reading the Surya Siddhanta's e-text witness (GRETIL; Michio Yano's input): eleven lines of
GRETIL's English header ("Header", "Contribution: Michio Yano", "Source:", ... "Text") had stood on its page 1 as
Sanskrit verses. The automaton's mend_witness.py (WITNESS_MEND_2026_10_21) keeps them in Latin letters, typed noise,
so the reader folds them; but the reader called them "Scanner noise, not text.", and an e-text has no scanner.

### AM.1 - What changes
- src/components/reader/PassageBlock.tsx: a passage typed noise whose reading is an e-text (readingOf: kind etext,
  not a scan) is folded as before and says "Not the text: the e-text's own header or notes."; its note
  (TYPE_NOTES.etext_noise) and its "About" say what it is. A scan's noise, and noise whose reading is not recorded,
  are "Scanner noise, not text." as before. Nothing stored changes; nothing more is asked of the database.
- src/__tests__/reader-etext-noise.test.tsx (2 tests).

### Invariants added (Phase AM)
60. The reader names what it folds by where the text came from: noise in an e-text is the e-text's own matter, never
    a scanner's; noise in a scan, or where the source is not recorded, is scanner noise as before.
