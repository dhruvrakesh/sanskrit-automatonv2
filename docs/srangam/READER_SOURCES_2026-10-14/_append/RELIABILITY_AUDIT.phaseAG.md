
## Phase AG - Where the Sanskrit comes from, named (READER_SOURCES_2026_10_14, 2026-10-14)

The reader said "OCR confidence 52%" for every passage of MBh01, and marked 267 of its verses "the printed page was
hard to read". MBh01 is the BORI Critical Edition's own e-text (from GRETIL): nothing in it was read from a scan.
Its quality score is the automaton's OCR formula (0.6 x the share of Devanagari signs + 0.4 x the dandas), and the
e-text writes no dandas, so it scored 0.48 to 0.58 whatever its quality. The automaton now records the e-text's
engine and its e-text value, 0.98 (heal_etext_meta.py, ETEXT_META_2026_10_14; mirrored 14 Oct, 21:12). The reader
still called that "OCR confidence".

### AG.1 - What the reader does now
- `readingOf(engine)` (src/lib/corpusDisplay.ts, pure) names where a passage's Sanskrit comes from, from the
  mirror's `ocr_engine`: "the BORI Critical Edition e-text (from GRETIL)" (gretil-bori-etext), "an e-text, typed
  from the edition" (another gretil or etext engine), "read from the scan by a vision model"
  (gemini-vision:...), "read from the scan by Tesseract OCR" (tesseract, tesseract-fallback), "read from the scan,
  then cut into verses again" (resegment-...).
- **An e-text:** About this passage says "Source: the BORI Critical Edition e-text (from GRETIL)", with no OCR
  confidence, and "Typed from the edition (an e-text) and translated by machine; not reviewed." It is never
  marked "hard-to-read scan".
- **A scan:** its reader beside its confidence ("read from the scan by Tesseract OCR; OCR confidence 45%: the
  printed page was hard to read"); the chip as before.
- **No engine recorded** (19,700 passages of 43 texts went in before it was recorded): as before.

### AG.2 - The database
- One read-only function, `public.corpus_reader_sources(p_doc)` (docs/cloud/C17_reader_sources_2026-10-14.sql in
  the automaton repo): the live passages of one text counted by page and engine. It asks `corpus._reader_gate()`
  first, as the C5 reader functions do: signed-in readers only; SECURITY DEFINER, search_path ''. Nothing else
  changes; `corpus_reader_page` and what it returns are as they were.
- The corpus reader (/corpus/:docCode) asks it once a text (cached 10 minutes) and labels each page by the engine
  of most of its passages (`readingsByPage`). Until C17 is pasted the call fails and the reader shows what it
  showed before.
- The public reader (/texts/:docCode) reads srangam_text_passages, which has no engine: unchanged.

### AG.3 - Load
- One small call a text, after the text's first page. The change sits in the reader's lazy chunks (the shared
  reader chunk about 15.0 kB, measured with vite build); the entry chunk does not carry it.

### Invariants added (Phase AG)
52. A passage whose recorded engine is an e-text is never called "OCR" and never marked a hard-to-read scan; a
    passage without a recorded engine is shown exactly as before.
53. Where the Sanskrit comes from is read from the mirror (`corpus.passages.ocr_engine`, through C17), never guessed
    from the text's name or its quality score.
