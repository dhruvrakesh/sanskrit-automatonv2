## Phase AI - A printed ornament is not the scanner's debris (ORNAMENT_2026_10_16, 2026-10-16)

Lovable found, on 16 Oct, clean verses labelled "provisional English": verses printed next to an ornament. The vision
OCR writes an ornamental rule of the page as a line of its own, "<decorative line>"; the reader hides that line and
draws a short rule (READER_MARKS_2026_10_07). The provisional test (PROVISIONAL_EN_2026_10_14, invariant 51)
looked for a Latin word in the whole Sanskrit, the marker included, so the marker's own words made the verse look
misread. The automaton's tests had the same fault (scholar_translate.readiness left such a verse out as "OCR
debris"; redeem.py counted its English as made from a misread reading); they are mended in the same release
(ORNAMENT_2026_10_16 in the automaton repo). In data/context.db three verses carry the marker on a line of its own:
the Markandeya Purana 1.4 and 1.6, and the Tantric Texts series 135.1.

### AI.1 - What the reader does now
- madeFromMisread() sets aside the lines that are only the marker (splitDecoration, the reader's own rule) before
  it looks for a Latin word. Such a verse is not called provisional; the rule is drawn as before.
- The marker inside a line of text, and any other Latin word among the Devanagari, is debris as before: the chip
  and the "About this passage" line stay.

### AI.2 - Load
- No question to the database; one call of an existing pure function on text the reader already has.

### Invariants added (Phase AI)
56. A line that is only the OCR's ornament marker is never read as the scanner's debris: the reader's provisional
    test and the automaton's (scholar_translate.readiness, redeem.classify) set it aside alike; a Latin word anywhere
    else is debris as before.
