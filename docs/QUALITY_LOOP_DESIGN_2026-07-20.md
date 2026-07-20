# Phase Q — Translation Quality Loop (Design)
**Date:** 2026-07-20 · **Status:** design for review, no code yet
**Goal:** the automaton reviews the quality of its own translations, so each prompt/engine improvement can be applied retroactively and measurably — iterative development with context preservation and authenticity.

## Current rerun semantics (post-2026-07-20 fixes)

- Re-ingest: idempotent. Texts refresh, translations survive, idx stable. Caveat: upsert never deletes — if a source shrinks, stale high-idx rows linger (use wipe_doc.py for a clean slate).
- Translate-all: fills empty translations only. Existing rows untouched → corpus becomes a MIX of prompt-v1 and prompt-v2 output. Error docs (nirukta, smriti) are re-attempted every run because the pre-filter checks Devanagari density, not stored quality_score.
- Provenance gap: passages do not record which engine/prompt produced their translation. "Retranslate everything made under v1" is not currently queryable.

## Q1 — Provenance columns (prerequisite for everything else)

Extend `passages` via the existing migrate_schema pattern (additive, no data loss):

    mt_engine          TEXT   -- e.g. gemini:gemini-2.5-flash
    mt_prompt_version  TEXT   -- e.g. v2-2026-07-20
    translated_at      TEXT   -- ISO timestamp
    translation_qa     REAL   -- Q2 heuristic score 0–1

Populated by the translate job at write time. Existing rows: mt_prompt_version backfilled as 'v1-legacy' wherever translation != ''.

## Q2 — Heuristic QA scorer (free, no API)

`score_translation_quality(src, translation) -> float` in text_filters.py:

- 0.0 hard fails: empty, is_translation_boilerplate(), '[ILLEGIBLE]'
- Length-ratio band: translation chars / source chars expected ~1.2–3.5 for Devanagari→English; outside band → penalty (catches truncations and rambles)
- Residual Devanagari in output → penalty (untranslated fragments)
- Repeated-gloss pattern ("X | X", "word. | word.") → penalty (the nirukta failure signature)
- Mid-sentence " / " density → penalty (v1 pāda-literalism artifact — flags style-stale rows)
- ASCII-letter fraction sanity (is it actually English?)

Run as a batch job over all translated passages (pure SQL+Python, seconds), writes translation_qa. Dashboard gets a per-doc QA histogram — the "go over its own translations" panel.

## Q3 — Translation history + retranslate queue (never destroy, always supersede)

New table:

    translation_history(id, passage_id, translation, mt_engine,
                        mt_prompt_version, translated_at, superseded_at, reason)

`scripts/retranslate.py`:

    python scripts/retranslate.py --doc shiksha --below-qa 0.6 --dry-run
    python scripts/retranslate.py --all --prompt-version v1-legacy --limit 500 --yes

Moves the current translation into history (reason = 'qa<0.6' / 'prompt-upgrade'), clears the passage's translation, and lets the normal translate job refill it under the current prompt. Nothing is ever silently overwritten; every earlier attempt remains comparable — that's the context-preservation guarantee, and it gives before/after pairs for measuring each prompt iteration.

## Q4 — Sampled LLM-judge pass (cheap, bounded)

`scripts/judge_sample.py`: sample ~5% of translated passages per doc (stratified by page), ask Flash to grade fidelity and fluency 1–5 with a one-line reason against the source + IAST. Store in:

    mt_reviews(id, passage_id, engine, prompt_version,
               score_fidelity, score_fluency, comment, created_at)

Cost: 5% of MBh01 ≈ 350 calls ≈ $0.03–0.05. Aggregate per doc → dashboard. Human spot-checks (your Debroy column) stay the gold standard; the judge is the wide-coverage early-warning layer. Disagreement between judge and heuristic QA is itself a signal worth surfacing.

## Q5 — Translate-all guards

- Skip passages with quality_score < 0.35 (source too corrupt to translate — stops the smriti burn) — override per doc with --force.
- Per-doc skip list honored by advance_pipeline (nirukta stays parked until a lexicon-mode prompt exists).

## Rollout order

Q1 (migration + write-path) → Q2 (scorer + backfill + dashboard histogram) → Q3 (history + retranslate) → Q5 (guards) → Q4 (judge). Each step is one commit, each testable read-only before touching live data (--dry-run everywhere). The loop closes when: prompt vN ships → retranslate flags stale/weak rows → refill under vN → Q2/Q4 scores confirm the improvement → benchmark sheet validates against Debroy.
