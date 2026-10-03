# Editions and images: HTML as the master edition, a managed image library (2026-10-03)

Marker: `EDITIONS_IMAGES_2026_10_03`.

Status: E1 is shipped and was tested on the Mallapurana exports. The rest is a plan awaiting approval. Nothing here changes Booksmith.

## 1. What was verified

| # | Finding | Evidence |
|---|---|---|
| F1 | The export HTML already has a careful screen design: a title page with provenance, contents, three columns (Sa / En / Hi) and footnotes. Its print rules are minimal. There is no `@page` size, margins or page numbers. `.chapter { break-inside: avoid-page }` pushes whole sections to new pages, leaving large gaps. Every verse repeats its column headings. | `scripts/export_html.py` CSS, lines 300–333 |
| F2 | Booksmith renders with ReportLab 4.5.1. The Devanagari font is registered `shapable=True`, but `uharfbuzz` is **not installed** in the Booksmith venv. Without HarfBuzz, ReportLab does not shape Devanagari, which breaks conjuncts and puts the short-i sign in the wrong place. This is the likely cause of the broken formatting. | `renderer.py:90`; `.venv\Lib\site-packages` has `reportlab` but no `uharfbuzz` |
| F3 | Booksmith's "illustrations" are static files listed in `book.yaml` (`plate_paths`). They are spaced evenly through the book (`illustrations_per_volume`, default 3). Nothing is generated or managed, and nothing ties an image to a passage. Its roadmap puts generated imagery out of scope ("generated maps or scientific diagrams presented as evidence"). | `renderer.py:305-310`, `docs/roadmap.md` |
| F4 | Srangam already has a media-asset model for OG images: versioned assets stored in Drive, soft-retired and never deleted. The image library below copies those semantics, so a later sync is natural. | `supabase/functions/generate-article-og`, `retire-og-image` |
| F5 | The export's methodology box is Mahābhārata boilerplate ("1.1.0 is the benedictory maṅgala verse; star-passages excluded by the critical edition"). It is wrong for Mallapurana, whose source page 1 names *Gaekwad's Oriental Series No. 144*. A Hindi-only export also prints empty "Page N" sections. | the Mallapurana `_tri` and `_hi` exports of 2026-10-03 |

## 2. Shipped: E1, `scripts/export_pdf.py` (EXPORT_PDF_2026_10_03)

It prints an export HTML to PDF with a browser engine, which shapes Devanagari with HarfBuzz. It adds print-only CSS:

- A4 or B5 pages, with a running title and "page / pages" numbers;
- the title page and contents each on their own page;
- verses never split across pages;
- column headings once per section.

The HTML on disk is unchanged; the print styles go on a temporary copy in `exports\_print\`. The engine is Playwright Chromium if it is installed, otherwise headless Edge or Chrome (page numbers need Chromium 131 or later). Tested on Mallapurana:

| Edition | A4 | B5 |
|---|---|---|
| Trilingual | 76 pages, 3.2 s | 88 pages, 3.4 s |
| Hindi | 46 pages, 1.8 s | 64 pages, 1.4 s |

`tests/test_export_pdf.py` covers it.

## 3. Proposed, each phase one failure domain

- **E2: `export_html.py` hygiene** (patch plus tests):
  - a per-document methodology text built from provenance (source edition, OCR engines, prompt versions, counts), replacing the Mahābhārata boilerplate;
  - skip sections that end up empty;
  - move the print CSS from `export_pdf.py` into the export, so a browser's own "Print" gives the same result;
  - optionally group sections by adhyāya, using colophons ("इति … अध्यायः") when `chapter` is missing.
- **E3: dashboard "PDF" button.** Each row gets "PDF (A4/B5)", which runs `export_pdf.py` after an export. Booksmith stays available and is not modified. If you want Booksmith kept, `pip install uharfbuzz` in its venv is a one-line test of finding F2.
- **I1: image library, schema and CLI** (additive, local):
  - Files go in `data/images/<doc>/<id>.<ext>`, gitignored and included in backups.
  - A new table `doc_images`, holding:

    | Group | Fields |
    |---|---|
    | Identity | `id`, `doc_id`, `version`, `sha256`, `path`, `width`, `height` |
    | Kind | `kind`: `edition-plate` (scanned from the source book), `generated`, `diagram` or `photo` |
    | Description | `title`, `caption_en`, `caption_hi`, `context_note` (why the image belongs at this point) |
    | Placement | `anchor_page`, `anchor_idx`, `anchor_verse_ref` |
    | Origin | `provenance` (source page, or model, prompt and seed), `prompt_hash`, `license` |
    | Review | `status`: `draft`, `approved` or `retired`, plus `created_at`, `approved_at`, `retired_at` |
  - Never deleted, only retired (Srangam semantics).
  - `scripts/images.py add|list|approve|retire|export` with dry-run defaults.
- **I2: dashboard "Images" tab per document.**
  - A grid with status filters.
  - Edit title, captions and context note; pick an anchor from the reader (page and verse).
  - Upload your own image or crop a plate from the source scan; approve or retire.
  - Loads thumbnails only, so it stays fast.
- **I3: suggestions and one-time generation.**
  - An LLM reads the text and proposes a small number of anchor points and image briefs. The default cap is one per adhyāya, with a hard cap per book; a human approves each brief.
  - Generation then runs **once** per (doc, anchor, prompt_hash). The result is cached and never generated on view or click.
  - Regenerating creates a new version and retires the old one.
  - Spend is metered through `usage_meter.py` with `kind='image'`.
  - Every generated image carries a visible label: "Illustration — generated, not a historical source".
- **I4: export integration.** Approved images render as `<figure>` at their anchor, with caption and provenance line, and are kept whole on one page in print.
- **I5: Srangam sync.** Publish approved images and captions to Srangam's media assets via Lovable. Planned separately.

Guardrails that hold throughout:

- Generated images are never presented as evidence, and never placed without human approval.
- Source-edition plates keep their page reference.
- No image is ever regenerated automatically.

## 4. Update 2026-10-03 (afternoon)

- **E1 confirmed on Windows.** `export_pdf.py` produced Mallapurana trilingual A4 (74 pages, 8–14 s) and Hindi B5 (67 pages, 2 s). `uharfbuzz` is confirmed **absent** from the Booksmith venv (`ModuleNotFoundError`), which confirms F2.
- **I1 shipped: `scripts/images.py` (IMAGE_LIBRARY_2026_10_03).**
  - The `doc_images` table is created on first use and is additive. Files go in `data/images/<doc>/`.
  - Statuses run brief → brief-approved → draft → approved, with retired available from any status. Approving a new version retires the old one in its lineage.
  - Generation is keyed by `prompt_hash`, so an identical brief is never generated twice.
  - Briefs are anchored only to real (page, idx) passages; a cap of 6 per call applies by default, with a hard cap of 12.
  - Every generated image carries the label "generated, not a historical source".
  - Calls go through the REST API with the key from `.env`. Spend is metered (`kind='image'`, `'image_brief'`).
  - The default image model is `gemini-3.1-flash-image`, listed on the Gemini pricing page on 2026-10-03 at about $0.045 per image. `images.py models` shows what this key can use.
  - `tests/test_images.py` covers it (5 tests, HTTP faked).
- **Pricing caveat.** `cost_tracker._PRICING` still prices `gemini-2.5-flash` at $0.15 / $0.60 per million tokens. The pricing page read today no longer lists 2.5 Flash, so recorded spend may understate the real bill. Reconcile against Google Cloud billing before trusting `budget_state`.
- **Next:**
  - I2: an Images tab in the dashboard (grid, edit captions and anchors, approve or retire).
  - I4: approved images placed in `export_html`, which `export_pdf` then prints.
  - E2: export hygiene (methodology text, empty sections).
  - E3: a PDF button in the dashboard.

## 5. I2 shipped: the Images tab (IMAGES_UI_2026_10_03, IMAGE_DEDUPE_2026_10_03)

- **What it is.** `scripts/images_web.py` and `scripts/images_static.html` add a page at `http://127.0.0.1:5057/images`, reached by an "Images" link in the dashboard top bar. `scripts/patch_images_ui.py` adds the link and registers the routes; it is guarded so a broken module cannot stop the dashboard, and it needs one restart while the dashboard is idle.
- **What the page does:**
  - Pick a text, filter by status, and see thumbnails (360-px JPEGs, made once and cached in `_thumbs/`).
  - Edit title, idea, the note on why the image belongs, English and Hindi captions, and the verse anchor, with a preview of that verse.
  - Approve an idea, generate, approve the image, redraw as a new version, retire, or restore.
  - Propose ideas and remove duplicates.
  - Calls to the model run as dashboard jobs (`images_brief` and `images_gen`), with a per-image job identity so one image's job never swallows another's.
- **Duplicate ideas, measured.** `brief --yes` was run twice on 2026-10-03, creating rows 1–6 and 7–12. Five of the six new rows sat at the same verse as an earlier one; the sixth moved from 73.10 to 77.8.
  - `brief` now refuses while unreviewed ideas exist (unless `--more` is given), and skips an idea already present at the same verse with the same title.
  - `dedupe` retires later ideas at the same verse.
- **Refused pages.** `ocr_consensus.py` no longer re-sends pages whose vision file records a RECITATION or SAFETY refusal, because a retry only costs a call; `--retry-refused` re-sends them.
- **Tests.** `tests/test_images_web.py` (5, Flask test client) and `test_images.py` (6). The full suite is 62 tests.
