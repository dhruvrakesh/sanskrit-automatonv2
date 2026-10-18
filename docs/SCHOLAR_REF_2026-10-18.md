# The night of 17 Oct read: the screen calibrated, the Devimahatmya missed, the judge's quota (18 Oct 2026)

Marker: **SCHOLAR_REF_2026_10_18**, in `scripts/scholar_translate.py` (patched by
`scripts/patch_scholar_ref_2026_10_18.py`), and **DOCS73_2026_10_18**. It follows JUDGE_SCREEN_2026_10_17 (`b4b1b9e3`),
docs/JUDGE_SCREEN_2026-10-17.md.

## 1. What the night did (read from the PowerShell output, data/scholar/, data/retranslate/ and the site's SQL)

- **Released:** `b4b1b9e3` (JUDGE_SCREEN, TEST_ISOLATION, DOCS72).
- **The Markandeya's verse 4.8** (the invented gloss): Sonnet's English and a new Hindi, on the site since 17 Oct 15:02
  UTC (the site's SQL: engine anthropic:claude-sonnet-5-5, the Hindi made beside it).
- **The calibration of the screen** (judge-v1 by Haiku beside flash's verdicts, 229 passages, $0.0634, $0.00028 a
  verdict):
  - marked (fidelity 2 or less) by both 13, by flash only 12, by Haiku only 12, by neither 192;
  - Haiku finds 13 of flash's 25 marks (52%); the same score in 32%, within one in 84%; Haiku is the stricter (mean
    fidelity 3.77 against 4.42).
  - **The referee (Opus) on the 24 disagreements (23 answered): with Haiku in 16, with flash in 7.** Of the marks flash
    made alone, Opus confirmed none of 11 ("a plausible reading of a corrupt text"); of Haiku's alone, 5 of 12.
  - **By the rule set before the run** (docs/JUDGE_SCREEN_2026-10-17.md, section 4: two thirds of flash's marks, *or*
    the referee with Haiku at least as often as with flash), **Haiku is the screen.**
- **T2 on the Markandeya** (18 Oct 07:48 IST): its two marked verses (27.8, 82.8) translated again by Sonnet and judged
  again by Haiku: 2 to 3, 2 to 4, mended; the mirror sent them.
- **The GRETIL e-text in:** `markandeya_purana__w_gretil`, 5,240 passages on 780 pages (20 verses a page), local only
  (the register's "witness"; corpus.docs on the site holds markandeya_purana alone). The Devimahatmya is adhyayas 81 to 93
  on pages 626 to 780: 588 numbered verses (MarkP_81.1 on page 627 to MarkP_93.17 on page 779) and 89 unnumbered
  passages (75 speaker lines, 12 colophons, 2 verses).

## 2. What went wrong

**The scholarly run did not begin at the Devimahatmya.** `--from-ref 81.1` matched page 81, passage 1 first: a chapter
heading ("Chapter Nineteen") with no reference of its own, which `ref_of()` names by its page.idx, "81.1". The 40-verse
canary (21:44 IST) and the run of 700 (22:06 to 01:40 IST) made the scholarly English of **adhyayas 19 to 31** (pages 81
to 124; 740 verses; $20.63 of the credit): the Dattatreya and Alarka chapters, which our scan (1 to 15) does not have.
That English is kept; it is not the Devimahatmya. The canary's plan showed its first verse, and the safeguard of
docs/NEXT_BOOKS_2026-10-17.md section 1 ("the plan shows it before anything is spent") relied on a person reading it: it
was not enough.

**The judge's quota.** From 23:34 IST the flash judge answered `ResourceExhausted` (Google's quota) to every verse: 482
of the 740 have no score and so are "flagged". Google's vision reading of the Nirukta (216 pages) ran that night too.
The Claude English was made and paid for; only its reading by the judge is missing. By 08:05 IST the vision of the
Ganita Yukti Bhasa was answered again.

## 3. SCHOLAR_REF_2026_10_18

- **`--from-ref` matches a verse's own reference** (an e-text's, as ref_of trusts it) whenever a verse of the text has
  it; the page.idx fallback is used only when none has (an OCR reading, as before). `own_ref()` beside `ref_of()`.
- **`--rejudge` reads again the verses whose judge did not answer** (no fidelity, English there), whoever the judge
  was, besides those a Claude judge read; its dry run and help say so. The Gemini judge, as before, in the spend cap.

**Tests:** `tests/test_scholar_ref_2026_10_18.py` (5): the e-text's own reference first (the bug, reproduced on the
pre-patch copy, picks page 81); page.idx kept for a reading without references; an unanswered verse read again (not
one Gemini scored, nor one without English), its status decided again; the patcher replayed on its backup.
`tests/test_ornament_2026_10_16.py` follows `.bak_scholarref_`. test_rejudge, test_scholar, test_triage,
test_ready_price, test_classify_hindi, test_run_fix and test_audit pass unchanged.

## 4. In order

1. The patch, its tests, the release.
2. **The Devimahatmya** (before Ashtami, 19 Oct): `--from-ref 81.1 --pages 627-780`, a canary of 20 first; about 680
   passages at the run's measured $0.028, about $19. One Gemini job at a time while it runs (no vision repair beside
   it). If the judge answers `ResourceExhausted` again, the English goes on; step 3 reads it afterwards.
3. **The re-judge** of the 482 (and of any the Devimahatmya leaves unanswered): `--rejudge`, about $0.0027 a verse on
   the cap.
4. **The editions:** `export_html.py --scholar --from 626 --to 780` (the Devimahatmya) and `--from 81 --to 124`
   (adhyayas 19 to 31); the prose by `scholar_translate.py --report` (exports\scholar_<doc>_prose.html) or
   /scholar/markandeya_purana__w_gretil/prose.
5. **The screen** (JUDGE_SCREEN), a text at a time, the Markandeya, Sandilya and the Mallapurana first; then T2 by
   Sonnet and Haiku.
6. **The Ganita Yukti Bhasa:** the re-ingest of its 108 repaired pages (`--apply --replace 138`), Tier R for the verses
   without English, the screen; its scholarly English (2,583 verses, about $72 at $0.028) is more than the credit left
   after steps 2 to 5: yours to decide (a part of it, or the credit raised).
7. **The Surya Siddhanta:** GRETIL's e-text, the preview (free) first.

## 5. Not decided here

GRETIL's licence (CC BY-NC-SA 4.0) before the witness goes on the site; whether the GRETIL text becomes the Markandeya's
reading of record (the scan, adhyayas 1 to 15, its witness); the Ganita's scholarly English; the Hindi of mended verses.
