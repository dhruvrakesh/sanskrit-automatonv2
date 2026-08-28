# How Srangam Measures Quality

*Transparency note for readers and scholars. Every number this project shows is
defined here, with its formula, its purpose, and — just as important — its limits.
Nothing is hidden in code: the functions cited below are in `scripts/text_filters.py`.*

We measure **three different things**, and we keep them separate on purpose, because a
clean source can carry a weak translation and a noisy source can still be translated
faithfully. Conflating them is how quality claims become misleading.

---

## 1. Source quality — "is the Sanskrit we OCR'd clean enough to translate?"

Column: `passages.quality_score` · function: `score_passage_quality()` · range 0–1.

Formula:

```
quality_score = 0.60 × (fraction of characters that are Devanagari)
              + 0.40 × min(1.0, (single-daṇḍas + 2 × double-daṇḍas) / 5)
```

It rewards text that is densely Devanagari and carries verse punctuation (। ॥). A page
of clean scripture scores high; an OCR page speckled with Latin noise (`STITH`, `WSS Ble`)
or broken glyphs scores low. It is used as a **gate**: verses below ~0.35 are skipped as
too corrupt to translate faithfully (better an honest blank than a hallucinated verse).

**What it does NOT mean.** It is an *OCR cleanliness* signal, not a judgment of the
edition's scholarly value. A pristine critical edition and a rough scan of the same text
both score high if the Devanagari is clean. A high score means "readable," not "the best
edition available."

---

## 2. Translation quality — "is the translation structurally sound?"

Column: `passages.translation_qa` (and `translations_l10n.translation_qa` for Hindi) ·
function: `score_translation_quality()` · range 0–1. Free, no API calls. It starts at
**1.0** and deducts for defects:

**Hard fails → 0.0:** empty output; the honest‑refusal tokens `[ILLEGIBLE]` / `[अस्पष्ट]`;
boilerplate; or a "translation" that is just the source echoed back.

**English deductions:**
- length ratio (translation chars ÷ source chars): `<0.6` −0.4, `<1.0` −0.15,
  `>5.0` −0.3, `>3.5` −0.1 (catches truncations and rambling meta‑commentary);
- untranslated Devanagari left in the output: `>30%` −0.5, `>5%` −0.2;
- a repeated gloss‑pair like `word | word`: −0.6;
- mid‑sentence truncation (a long output not ending on a terminator): −0.85;
- excessive pāda‑slash density (` / ` litter): graded penalty.

**Hindi (Phase HI) inverts the script polarity:** the output must be Devanagari‑dominant
(Latin residue is penalised, not Devanagari), and the length band is recalibrated
(hi/sa ≈ 0.9–2.5, because Hindi tatsama vocabulary tracks the Sanskrit closely).

**What it does NOT mean.** This is a *structural* health check — emptiness, ratios,
residue, style artifacts. It cannot see whether the meaning is faithful. A fluent,
well‑formed but subtly wrong translation can still score high. As our design record puts
it: a 0.99 here means **"structurally sound," not "certified faithful."**

---

## 3. Semantic fidelity — "is the meaning actually right?"

Table: `mt_reviews` · tool: `scripts/judge_sample.py` (Phase Q4).

Because §2 cannot judge meaning, we run a **sampled LLM‑judge**: a slice of verses per
document is graded 1–5 on **fidelity** (is the Sanskrit meaning preserved?) and
**fluency** (is it natural English/Hindi?) against the Sanskrit source — never against any
copyrighted reference translation. This is the layer that actually speaks to faithfulness.
It is deliberately **sampled, not exhaustive** (cost‑bounded), so it certifies documents
with confidence intervals rather than verse‑by‑verse. Where the judge and the §2 heuristic
disagree is itself a signal we surface for review.

The ultimate gold standard remains **human scholarly comparison** (e.g. against Debroy's
critical‑edition English), done by eye — never fetched or stored.

---

## 4. Provenance — every verse carries its history

Each translated verse records **which engine** produced it (`engine`, e.g.
`gemini:gemini-2.5-flash` / `-pro`), **which prompt version** (`mt_prompt_version`), and
**when** (`translated_at`). Superseded translations are archived to `translation_history`
rather than overwritten, so any earlier attempt remains comparable. This is what lets us
re‑translate a specific model/prompt generation and measure the improvement.

---

## 5. How to read the numbers honestly

- A document's headline quality is the **mean `translation_qa`** of its translated verses;
  treat ≥0.8 as structurally strong, and inspect anything <0.6.
- `quality_score` (source) and `translation_qa` (translation) are **different axes** — do
  not average them together.
- Coverage (e.g. "EN 549/2581") counts verses with a stored translation; the remainder are
  either not yet translated, **skipped as too corrupt to translate** (the honest blank), or
  **not Sanskrit at all** — a scanned book's English front matter (title page, editorial
  preface). English source is detected, labelled "Source is English — no translation
  needed" in the reader, and tagged `frontmatter` so it is excluded from coverage and QA
  rather than counted as an untranslated verse.
- "Structurally sound" is a floor, not a ceiling. Semantic certification comes from §3 and
  human review, and we report those separately rather than letting a heuristic stand in for
  faithfulness.

*Last reviewed 2026-08-28. Formulas are authoritative to `scripts/text_filters.py`; if the
code changes, this document is updated in the same commit.*
