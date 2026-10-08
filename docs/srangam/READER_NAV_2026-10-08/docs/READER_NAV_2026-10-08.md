# Reading the texts: navigation and layout (2026-10-08)

Marker: READER_NAV_2026_10_08. It covers `/texts/:docCode` (published texts, anyone) and `/corpus/:docCode` (the working corpus, signed-in readers).

## What a reader gets

| | Before | Now |
|---|---|---|
| Moving through a text | Previous / Next only, 50 passages a page | **Bar.** A bar under the site header (tablets and wider) with Previous, Next, any page from a list, and the arrow keys. **Contents.** A panel listing every page with the scan pages it covers, the chapter ends (colophons, corpus only) and a box to go to a scan page of the printed book. **Pager.** A pager at the foot of the page. |
| Layout | Sanskrit, IAST, English and Hindi stacked; the reference on its own line above | **Wide screens.** Sanskrit and IAST on the left, English and Hindi on the right, as in the Booksmith editions and the HTML exports. **Phones**, or with "Side by side" off: stacked. **Reference.** In the margin: scan page and passage, with the edition's own number under it. |
| What to show | Hindi only (corpus) | IAST, English, Hindi, Side by side and Scanner noise. They are remembered in this browser only. |
| Bad scans | Garbled lines shown as if they were text | **Misread lines.** A line with Latin letters and no Devanagari letter, inside a passage that has Devanagari, is shown muted with a note ("ay Trae:" in nirukta 1.1). **Noise.** Passages the automaton typed as noise are folded behind "Show it". Nothing stored is changed. |
| Notes | none | **Tooltips** on the reference, the edition number, the hard-to-read badge (with the OCR confidence) and the passage kind. **ⓘ popover** per passage: where it is, OCR confidence, translation engine and date, automatic check. |
| Find | Whole-corpus search on `/corpus` and `/texts` | **Find in this text.** In the bar: by words or by meaning (corpus), and by meaning (published texts). Results link straight to the passage, including on the same page. |
| Speed | Each page fetched on demand | The next page is fetched while this one is read. The contents are read only when the panel opens. |
| Titles | The code when no title was recorded ("nirukta") | The code made readable ("Nirukta"). A recorded title is shown as recorded. |

## Why there is no chapter list

`corpus.passages.chapter` mostly holds the division word without its number (nirukta: 5 distinct values on 179 of 2,095 passages; 'sarga', 'parva'). A chapter list built on it would mislead. The contents therefore use what the data supports: reader pages with their scan-page ranges, and colophons, the closing lines of chapters.

## Pieces

- **`src/components/reader/PassageBlock.tsx`**: one passage.
- **`src/components/reader/ReaderToolbar.tsx`**: the bar, the arrow keys, and the foot pager.
- **`src/components/reader/ReaderContents.tsx`**: the contents panel.
- **`src/lib/readerPrefs.ts`**: what to show, in localStorage; every access is guarded.
- **`src/lib/corpusDisplay.ts`**: pure helpers.
  - `isMisreadLine`, `sourceLines`, `displayTitle`, `gutterRef`, `passageWhere`.
  - `readerPageOf`, `outlineFromKeys`, `readerPageForScan`, `scanRange`.
- **`src/lib/corpusMirror.ts`**: `loadMirrorOutline` calls the database function `corpus_reader_outline`. Until that SQL is applied, `outlineMissing` makes the panel fall back to plain page numbers.
- **`src/lib/corpusTexts.ts`**: `loadPassageKeys`, the (page_no, idx) of a published text for its contents.
  - It reads 1,000 rows a request, each bounded with `.range()`.
- **`supabase/functions/search-corpus/embed.ts`**: a verbatim copy of the search-texts embedding helpers.
  - Lovable deploys a function's own folder and `_shared/` only, so the import from the search-texts folder failed to deploy.
  - `src/__tests__/search-corpus-embed.test.ts` fails if the copy drifts.
  - search-texts is not touched.

## Database

One read-only function, `corpus_reader_outline(p_doc, p_per_page)`, in the automaton repository: `docs/cloud/C5b_corpus_reader_outline_2026-10-08.sql`. It has the same gate as the six C5 functions, and only signed-in callers may execute it. On a test document of 21,128 passages it answered in 30 ms. No migration file is added here, and no row is written to `supabase_migrations.schema_migrations`.

## Tests

- **`src/__tests__/reader-nav.test.tsx`**: the display rules, the passage block, the bar, and the corpus reader: contents, a scan page, the fallback, find in this text, and the page fetched ahead.
- **`src/__tests__/texts-reader-nav.test.tsx`**: the published reader's contents and paging.
- **`src/__tests__/search-corpus-embed.test.ts`**: the copied embedding helpers.
- **Existing tests.** `texts-reader.test.tsx` and `corpus-mirror.test.tsx` pass unchanged.
