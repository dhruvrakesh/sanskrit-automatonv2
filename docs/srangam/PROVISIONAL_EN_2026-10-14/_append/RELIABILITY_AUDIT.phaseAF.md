## Phase AF - English made from a misread reading, marked (PROVISIONAL_EN_2026_10_14, 2026-10-14)

The automaton's ledger of what of the translation is redeemed (scripts/redeem.py, REDEEM_2026_10_14) found, on
14 Oct, 4,062 of 23,264 English verses (17%) made from Sanskrit the scanner misread: Latin letters among the
Devanagari. The reader showed a whole misread line muted (READER_MARKS_2026_10_07), but a verse with a few Latin
letters inside its Devanagari, and its English, looked like any other.

### AF.1 - What the reader does now
- **"provisional English"**, a small chip at the foot of a passage, when the passage has English and its
  Sanskrit carries the debris: eight or more Devanagari signs and a Latin word among them (a letter followed by
  a letter or a stray ' ! "). It is the automaton's own test (redeem.py, repair_text.JUNK), so the site and the
  ledger agree. Its tooltip says why: the scanner misread letters of the verse, the English was made from that
  reading, and it will be translated again once the scan is repaired.
- **About this passage** says the same, under "English".
- Not marked: a clean verse; a verse with no English yet ("Not translated yet."); the book's own English (no
  Devanagari); a single stray letter; and nothing when the reader has hidden the English.
- `madeFromMisread()` and `PROVISIONAL_NOTE` are in `src/lib/corpusDisplay.ts`, pure, beside the other display
  rules. Nothing stored is changed: the Sanskrit and the English are shown as published.

### AF.2 - Load
- The change is in the reader's shared chunk (about 14.7 kB, measured with vite build); the entry is unchanged.
  No question to the database: the test runs on the Sanskrit the reader already has.

### Invariants added (Phase AF)
50. A passage is marked "provisional English" only when it has English and its Sanskrit passes the automaton's
    debris test; the mark never hides, changes or reorders what is published.
51. The reader's test and the automaton's are the same rule (eight Devanagari signs and a Latin word); a change to
    one is a change to the other, with the tests of both.
