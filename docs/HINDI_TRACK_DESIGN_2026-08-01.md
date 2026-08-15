# Phase HI — Sanskrit → Śuddha Hindi Track (Design)
**Date:** 2026-08-01 · **Status:** design for review; implementation on "go"
**Inspiration:** as Debroy made the critical edition readable in scholarly English,
this track makes the same corpus readable in pure (śuddha) Hindi — same fidelity
discipline, same guardrails, same measured quality loop.

## 0. What already supports Hindi (verified, not assumed)

- `mt_cache` is keyed `(engine, lang_in, lang_out, text_hash)` — `sa→hi` rows
  coexist with `sa→en` untouched. Verified: cache currently holds only sa→en.
- `translate_batch(..., src, tgt)` already threads language codes end-to-end.
- srangam articles are multilingual JSONB with an `hi` key — the public window,
  when Track B unparks, already knows how to hold Hindi.
- The Phase Q loop (provenance, QA, history, retranslate) is language-agnostic
  in design; only the QA scorer and prompt are English-specific today.

## 1. The four load-bearing design decisions

**D1 — Translate from Sanskrit, anchored by our verified English.**
Direct sa→hi (never en→hi relay: double-translation loss, and Hindi's tatsama
vocabulary sits closer to Sanskrit than English does). But the prompt ALSO
receives our QA-passed English translation as a semantic reference with the
instruction: "translate the Sanskrit; the English is a verified reference for
meaning — do not translate the English." This turns 9,966 QA'd English rows
into a hallucination guardrail for Hindi. Corollary: **Hindi is generated only
for passages whose English exists and passed QA** — the English pass is the
scout, the Hindi pass never walks unscouted ground.

**D2 — Storage: one new table, English stays where it is.**
`passages.translation` (English) is load-bearing across dashboard, FTS,
exports, context windows — migrating it would violate the surgical rule.
New table instead:

    CREATE TABLE IF NOT EXISTS translations_l10n(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      passage_id        INTEGER NOT NULL,
      lang              TEXT NOT NULL,          -- 'hi' first; extensible
      translation       TEXT,
      engine            TEXT,
      mt_prompt_version TEXT,
      translation_qa    REAL,
      translated_at     TEXT,
      UNIQUE(passage_id, lang),
      FOREIGN KEY(passage_id) REFERENCES passages(id) ON DELETE CASCADE
    );

translation_history gains a `lang` column (default 'en') so supersede-never-
destroy covers Hindi identically.

**D3 — Per-language prompt versions, per-language cache keys.**
`PROMPT_VERSION` becomes `PROMPT_VERSIONS = {"en": "v2-2026-07-20",
"hi": "hi-v1"}` and the cache hash mixes in the version FOR THAT TARGET —
so iterating the Hindi prompt never invalidates the English cache and vice
versa. (Today's single shared constant would couple them — a latent defect
this track fixes before it bites.)

**D4 — Language-aware QA.**
`score_translation_quality(src, out, lang='en')`: for `hi`, the polarity of
two checks INVERTS — output must be Devanagari-dominant (Latin residue is the
penalty, not Devanagari); length band recalibrated (hi/sa char ratio ~0.9–2.5
vs en/sa 1.0–3.5). Empty/boilerplate/gloss-pair checks stay; `[अस्पष्ट]` joins
`[ILLEGIBLE]` as the honest-refusal token.

## 2. The Hindi prompt (hi-v1) — Debroy discipline in śuddha Hindi

Principles (mirrors English v2, adapted):
1. FIDELITY: जो लिखा है वही अनुवाद करें; व्याख्या नहीं।
2. LANGUAGE: शुद्ध, प्रवाहमयी खड़ीबोली हिन्दी। तत्सम शब्दावली को वरीयता, किन्तु
   पठनीयता की कीमत पर नहीं; अनावश्यक उर्दू-फ़ारसी शब्दों से बचें।
3. PROPER NOUNS: देवनागरी में यथावत् (अर्जुन, कुरुक्षेत्र, गङ्गा) — no IAST
   apparatus needed; this is Hindi's structural advantage over English.
4. VERSE FLUENCY: पूरे श्लोक का एक-दो प्रवाहमयी वाक्यों में अनुवाद; पाद-क्रम की
   नकल नहीं। श्लोकान्त पर " //"।
5. PARTICLES: एव, हि, वै, ह आदि केवल-बलसूचक निपात छोड़ें।
6. TECHNICAL TERMS: धर्म, कर्म, यज्ञ आदि हिन्दी में स्वयं स्पष्ट हैं — no gloss;
   gloss only genuinely technical ritual/philosophical terms on first use.
7. FRAMES: "वैशम्पायन ने कहा —" style for speaker frames.
8. AGREEMENT & NAMES: explicit subjects; one spelling per name throughout.
9. REFERENCE: the provided English is verified reference for MEANING only.
10. OUTPUT: केवल हिन्दी अनुवाद; अपठनीय OCR के लिए exactly: [अस्पष्ट]

## 3. Implementation map (each = one commit, gates as always)

- **HI-0** db_utils: `translations_l10n` + history.lang column (additive
  migration). infer_mt: PROMPT_VERSIONS dict + per-lang hash + `_SYSTEM_PROMPT_HI`
  + tgt-based prompt selection. text_filters: lang-aware scorer.
- **HI-1** translate_passages `--lang hi`: selects passages with QA-passed
  English and no Hindi row; context window built from preceding HINDI rows
  (Hindi context for Hindi consistency) + the row's own English as reference;
  writes translations_l10n with full provenance. All Phase Q protections
  inherited: no-cache-empties, quota abort, streak breaker, min-quality gate.
- **HI-2** qa_scan/retranslate `--lang` flag (history-preserving, per-language).
- **HI-3** Pilot: MBh01 adhyāya 1 (210 verses, ≈$0.05). Export a trilingual
  sample sheet (Sanskrit / English / Hindi). Manual benchmark against a
  classical Hindi rendering (e.g. Gita Press Mahābhārata) — SAME copyright
  discipline as Debroy: never fetched, never stored, compared by eye only.
- **HI-4** On pilot pass: corpus rollout over all QA-passed English rows
  (≈10k passages ≈ $2 at Flash rates — English-in-context raises input cost
  slightly). Then export_html trilingual mode; srangam `hi` surfacing waits
  for Track B unparking, where the article JSONB is already shaped for it.
- **HI-5 (with HI-3)** Q4 LLM-judge lands here, bilingual from birth: one
  sampled judge pass grades BOTH en and hi fidelity/fluency — the semantic
  verification layer the heuristic QA cannot provide, amortized across both
  languages.

## 4. English quality — evaluation of record (2026-08-01)

- 9,966 passages translated; mean heuristic QA 0.988; 15 rows below 0.6;
  740 v1-legacy remaining (upgradeable via retranslate --prompt-version).
- MBh01: 6,957/6,957 (100%), mean QA 1.0, prompt v2, source GRETIL/BORI 0.98.
- Honest limits of that number: heuristic QA measures surface health
  (emptiness, ratios, residue, style artifacts), NOT semantic fidelity.
  Semantic evidence still pending: (a) the manual MBh01-vs-Debroy benchmark
  sheet — the human gold standard; (b) the Q4 judge (HI-5). Until (a) is
  scored, "0.988" means "structurally sound", not "certified faithful".

## 5. Sequencing

Hindi work starts only after: current English sweeps drain, LalitaVistara +
Śukla Yajurveda overnight runs complete, and the Debroy sheet is scored —
that scoring calibrates the judge and locks the engine before the corpus is
translated twice. Budget check at HI-4 gate: ~$2 within the $8 envelope.
