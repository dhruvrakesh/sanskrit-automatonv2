# The scholarly editions on Srangam, the chapters of an e-text, and the dashboard's menus (18 Oct 2026)

Markers: **EDITIONS_SITE_2026_10_18** (scripts/publish_editions.py, configs/editions.json, the Srangam kit
docs/srangam/EDITIONS_2026-10-18/ with scripts/patch_srangam_editions_2026_10_18.py), **EDITION_REFS_2026_10_18**
(scripts/export_html.py, by scripts/patch_edition_refs_2026_10_18.py), **NAV_MENUS_2026_10_18**
(scripts/dashboard_static.html, by scripts/patch_nav_menus_2026_10_18.py) and **DOCS75_2026_10_18**. It follows
docs/STATE_2026-10-18.md (DOCS74, ETEXT_PAGE, `3959cf62`).

Asked on 18 Oct (afternoon): "top nav bar needs to be more extensive and accommodate all features. is this done and
scholarly works available on srangam as well for max effect and distribution". Decided the same day: the GRETIL
texts are published **with their credit** (CC BY-NC-SA 4.0: Srangam is non-commercial; our English made from them
is shared on the same terms), and **both** bars are extended (the dashboard's, and Srangam's header).

## 1. What the afternoon did (read from the PowerShell output, the PC's files and the site's SQL)

- **Released:** `3959cf62` (DOCS74, ETEXT_PAGE).
- **The Devimahatmya's edition made again** (11:36 UTC, 1.04 MB, all 669 passages) and its prose.
- **The Mallapurana's mended verses are on the site:** the scheduled mirror of 16:32 IST sent 81 passages; the
  site's count of 18:01 IST reads 80 by Sonnet, 908 by flash, 3 by gemini-2.5-pro. The same run sent the Ganita's 30
  new English verses and their vectors (2,266 with English on the site: 2,236 flash, 30 Sonnet).
- **The Sandilya's T2** (17:07 IST): 21 records, 19 mended, 2 not; the next mirror run sends them (the site's count of
  18:01 still reads 454 flash and 2 gemini-2.5-pro).
- **The Ganita's re-ingest** had run that morning (08:34 UTC, data/reingest/): the plan now reads "339 unchanged,
  nothing to do".
- **The Surya Siddhanta's canary:** 20 verses (1.3 to 2.5): 19 passed, 1 flagged (1.5), $0.558; the credit $24.68.
- **judge_review.py** (the screen's verdicts, 4,591 passages): a wrong meaning (fidelity 2 or less) in 289 (6%):
  the Markandeya 85 of 1,254 (17 blame the Sanskrit), the Ganita 100 of 1,793 (37), the Sandilya 41 of 456 (11), the
  Mallapurana 45 of 963 (34), the Bodhicaryavatara 15 of 40 (7), the Satapatha 3 of 45, MBh01 0 of 40.
- **The site:** no witness on it (`position('__w_' in doc_code)`: no rows); 63 texts live of 68.
- **Not yet run:** the re-judge of the 482 (its dry run only).

## 2. The scholarly editions on Srangam (EDITIONS_SITE_2026_10_18)

**The design.** An edition is a static page: the export the dashboard already makes (`export_html.py --scholar`:
the Sanskrit, its IAST, the scholarly English, the notes and doubts at each chapter's end, a dagger on what a person
has not yet read), given a bar back to the site, its credits and licence and its canonical address. It is written
into the Srangam repo as `public/scholarly/<slug>.html`, with `public/scholarly/index.json`, and the site's new
`/editions` page lists them. **No database, no sign-in, no edge function, no SQL**: the files go live when you push
Srangam's main and Lovable builds it. Open to everyone, and to search engines (canonical address, sitemap entry).

**The automaton (scripts/publish_editions.py, configs/editions.json).**
- The config names each edition: its slug, text, pages, title, subtitle, its Sanskrit's source (name, link, credit,
  licence) and its English's licence; `"enabled": false` keeps an entry without publishing it.
- Refused: a text the register holds in repair or has withdrawn (the Hayasirsa); a witness (`<doc>__w_<site>`)
  without its source and licence; an edition with no scholarly English; a bad slug.
- The plan (the default) prints what it would write; `--apply` writes; an unchanged edition is left as it is, its
  date too; it never runs git (you push Srangam).
- **On 18 Oct:** the Devimahatmya on (pages 626 to 780, GRETIL's Markandeyapurana 1-93, data entry by the Sansknet
  Project, CC BY-NC-SA 4.0, GRETIL's own note that the e-text is not proof-read); the Surya Siddhanta off until its
  515 verses are made; adhyayas 19 to 31 off until the re-judge.

**The site (the kit, 8 files).** `/editions` (src/pages/Editions.tsx, src/lib/editions.ts): each edition with its
counts, its credits, its licence and a link to its page; no index yet is "none yet", any other failure is shown as a
failure; an entry with an unsafe file or a non-https link is dropped. "Editions" in the header for everyone
(public/config/nav.config.json, so the phone's menu too); "Scholarly editions" in the Corpus menu; /editions in the
sitemap. RELIABILITY_AUDIT Phase AK (invariant 58). Tests: src/__tests__/editions-page.test.tsx (4), run here on the
site's own versions of React, Testing Library and Vitest (4 passed, the TypeScript clean).

**What it is not yet.** The scholarly English inside the reader (/corpus/<doc>) and in search by meaning: that needs a
site table, a mirror step and a reader change (the "X1" of the register), and for the GRETIL texts their adoption as
texts of their own. The editions are the publication; the reader is the next build.

## 3. The chapters of an e-text (EDITION_REFS_2026_10_18)

Found while preparing the Devimahatmya for the site: its contents read "Adhyaya 77, 81, 78, 82, 79, 83, 80, 84 ...".
The GRETIL file's speaker lines and headings carry an earlier heading's number ("77" inside adhyaya 81), and the
edition grouped by it; and a sentence begun by a speaker's line was labelled by that line's page.idx ("628.1-18").
- `_ref_chapters()`: when half or more of the passages carry a two-part reference of their own (81.1), the chapter is
  the reference's; a heading or a speaker's line goes with the next verse, a colophon ("iti ...") with the one before.
  Three-part references (MBh 1.1.8) and texts without references are as they were.
- `_own_range()`: a sentence's range from its verses' own references (81.18-19).
- The notes numbered in the order their anchors are read (the first sentence's read 1, 4, 3, 2: they came in the
  order the translator listed them), an italic *term* found as printed, and a note's *term* in italics.
- Tests: tests/test_edition_refs_2026_10_18.py (6); test_scholar_edition_2026_10_17 passes unchanged.

## 4. The dashboard's menus (NAV_MENUS_2026_10_18)

The main page's top bar held three links and seven buttons; on a laptop the last ran off the edge, and five pages had
no link. Now six menus: **Texts** (Shelf, Library, Desk, Path, Sources), **Translate** (Translate, Scholarly English,
Redeem), **Check** (Benchmarks, BM2, Methodology), **Make** (Stories, Images), **Ask** (Ask the Corpus, Database),
**Site** (Srangam's editions, its working corpus, the Researchers' Corner, the Hub). Every link that was there is
kept as it was; one menu open at a time, closed when the pointer leaves; no script block added; the engine selector
narrower. Seen in Chromium at 1,280 and 1,536 pixels: the bar fits, a menu opens below it. Tests:
tests/test_nav_menus_2026_10_18.py (5). The dashboard needs no restart (it serves the file as it is).

## 5. In order

1. The automaton's release: the three patchers, their tests, DOCS75; `release.ps1`.
2. **The Devimahatmya on Srangam:** `python scripts\publish_editions.py` (the plan), then `--apply`; the Srangam kit
   (`--check`, then the patcher), `npm run typecheck`, `npx vitest run`, `npm run build`; then Srangam's commit and
   push (the RUNBOOK). Then https://srangam.nartiang.org/editions.
3. The re-judge of the 482 (about $1.30, Google), then adhyayas 19 to 31 on (`"enabled": true`) and the publisher.
4. The Surya Siddhanta's scholarly English (the rest of its 515, about $14 at the canary's $0.028), then on.
5. The Sandilya: the next mirror run sends its 19; T2 for the Markandeya (85 marked, 68 for Sonnet) and the Ganita
   (100, 63), the dry run first.
6. Later: the scholarly English in the reader (X1).
