# The next books: the Devimahatmya before Ashtami, the Ganita Yukti Bhasa, the Surya Siddhanta (17 Oct 2026, night)

Decided on 17 Oct: the Markandeya Purana's scholarly English; Sonnet in one pass (Tier R) for the working English. Next
in line: the Ganita Yukti Bhasa and the Surya Siddhanta. Durga Ashtami is Monday 19 Oct 2026. TIER_R_2026_10_17
(`scripts/patch_tier_r_2026_10_17.py`) puts both decisions on the desk.

## 1. The Markandeya Purana: what we have, and the Devimahatmya

- **Our scan is adhyayas 1 to 15 only** (100 pages, 1,219 verses: from the opening to the dialogue of Yama's servant in
  the story of Jada). **The Devimahatmya (adhyayas 81 to 93) is not in the corpus.**
- **GRETIL has the Markandeya Purana, adhyayas 1 to 93**, typed by members of the Sansknet project, in IAST, each verse
  numbered `MarkP_<adhyaya>.<verse>`, under Creative Commons BY-NC-SA 4.0 (non-commercial, attribution, share alike):
  `https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_mArkaNDeyapurANa1-93.htm`.
  `etext_witness.py` reads that numbering (`MarkP_81.1` becomes 81.1) and puts the IAST into Devanagari; it becomes a
  text of its own, `markandeya_purana__w_gretil`, a witness of our scan (it does not touch the scan's passages).
  The licence is yours to weigh before its English goes on the site, as with the BORI e-text.
- **The plan:** the e-text in (free), then the scholarly English of adhyayas 81 to 93 (the Devimahatmya: about 600 to
  700 verses; about $25 to $30 at the Hayasirsa's $0.0425 a verse; at the Hayasirsa's pace, 350 to 400 verses an hour,
  about two hours), then its edition (free). The first verse of the plan should be the Devimahatmya's opening
  (savarnih suryatanayo ...); if adhyaya 81 is not where it begins in this e-text, the plan shows it before anything
  is spent.
- **Our scan's working English (adhyayas 1 to 15), on the site:** it holds flash's errors (page 4, passage 8: the
  invented gloss, read on the site on 17 Oct). Sonnet in one pass, every verse again: 1,219 verses, about $6.

## 2. The Surya Siddhanta

- **What we have:** `jyotish_surya_siddhanta` (55 page PDFs, Tesseract, 58 passages, almost all debris) and the Kashi
  Sanskrit Series edition (Kapileshwar Shastri, no. 144): `inbox\Surya_Siddhanta_of_Pt_Shri_Kapileshwar_Shastri_144_-_Kashi_Sanskrit_Series_0001.pdf`,
  320 page objects in 136 MB, **but the file is cut short**: it has no end-of-file marker or cross-reference table
  (qpdf and pypdf cannot read it). It must be downloaded again, whole, before it can be split and read.
- **GRETIL has the Surya Siddhanta**, typed by Michio Yano, the variants of other editions marked (among them FitzEdward
  Hall's, with the Gudharthaprakashaka), CC BY-NC-SA 4.0:
  `https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_sUryasiddhAnta.htm`. Its verses are
  numbered by half-line (`1.01a:`, `1.01b:`), with variants in brackets, a form `etext_witness.py` was not built for:
  its preview (free) shows how it reads it; if the verses do not come out whole, the reader needs a small addition
  first. The work has about 500 verses (the preview counts what the e-text holds): the scholarly English about $21.

## 3. The Ganita Yukti Bhasa

Its reading is Tesseract's only (339 pages; 474 of its English passages carry [ILLEGIBLE]), and the register calls it
"complete". The order: restore it in the register (free), the vision repair (about $1.4 to $3.0 on the Google cap),
the re-ingest of the changed pages (the plan free), the path again, then its English: Sonnet in one pass about $25
(its passages are long prose), or the scholarly English about $110 to $220.

## 4. The money

| | The Claude credit (about $66 on 16 Oct; it ends on 11 Nov) | The Google cap ($11.06 left on 17 Oct) |
|---|---|---|
| The Devimahatmya, scholarly | about $25 to $30 | its judge, about $2 |
| The Markandeya scan's working English again, Sonnet | about $6 | - |
| The Surya Siddhanta, scholarly | about $21 | its judge, about $1.5 |
| The Ganita Yukti Bhasa | Sonnet about $25; scholarly about $110 to $220 | the vision repair, about $1.4 to $3.0 |
| The Padma Purana's Patala Khanda, the rest of its vision | - | about $1.28 |

The first three fit the credit; the Ganita's English does not, beside them: its repair now, its English after (or
the credit raised). The credit's state: `python scripts\claude_engine.py --credit` (free); the cap's:
`python scripts\set_budget.py`.
