## Phase AH - The edition's own matter, folded (CLASSIFY_HINDI_2026_10_16, 2026-10-16)

The automaton found, on 16 Oct, that an edition's own Hindi had been translated as if it were the Sanskrit: of the
Karanagama's passages that read as Hindi (the editor's translation under each verse, his preface), 194 carried
English made from the Hindi, and the mirror's copy of the text 291 (and 132 Hindi rows on such passages). Its
classification stage now tags such passages `frontmatter`, the label it gives "genuine English/Hindi body text and
front matter" (scripts/classify_hindi.py, scripts/edition_hindi.py in the automaton repo), so the translators leave
them out.

### AH.1 - What the reader does now
- A passage typed `frontmatter` is folded, like scanner noise: one line, "The edition's own matter, not the
  Sanskrit.", with "Show it". Shown, it never says "Not translated yet.": it is not the Sanskrit, and is not to be
  translated.
- Its note (the chip's tooltip, and "Kind" in About this passage) says what it is: the edition's front matter, or
  its editor's translation or notes in a modern language.
- A verse without English still says "Not translated yet."; scanner noise and a colophon are as before.
- The public reader (/texts/:docCode) reads srangam_text_passages, which publish_srangam.py fills without noise
  and frontmatter: unchanged. The change is for the corpus reader (/corpus/:docCode).

### AH.2 - Load
- No question to the database; the rule runs on the type the reader already has. The change is a few lines of
  the reader's shared chunk.

### Invariants added (Phase AH)
54. A passage typed `frontmatter` is folded until asked for and never says "Not translated yet."; the fold hides,
    changes or reorders nothing that is published.
55. A passage's kind comes from the automaton's classification stage (classify_frontmatter.py for English,
    classify_hindi.py for an edition's own Hindi); the reader never guesses a passage's language.
