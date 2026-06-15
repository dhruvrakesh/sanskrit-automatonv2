#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
infer_mt.py — Context-aware Sanskrit→English translation engine with cost tracking.

Phase 3 upgrade:
- Document-aware system prompt (text name, chapter, verse ref, chandas)
- Sliding context window (5 preceding verses passed to LLM)
- IAST alongside Devanagari in prompt
- Scholarly output: Bibek Debroy style with bracketed clarifications
- max_output_tokens raised to 2048
- Improved model refusal detection

Supported engine strings:
  openai:<model>      e.g.  openai:gpt-4o-mini
  gemini:<model>      e.g.  gemini:gemini-2.5-pro   (default quality)
                             gemini:gemini-2.0-flash  (fast/cheap)
  echo                passthrough for testing
"""
from __future__ import annotations
import os, time, sqlite3, hashlib, json
from typing import List, Tuple, Dict, Optional

DEFAULT_ENGINE = os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash")
SLEEP  = float(os.environ.get("MT_SLEEP",   "0.8"))
RETRIES = 3

# Cost tracking (imported lazily to avoid circular deps)
_cost_tracker_ok = False
try:
    from cost_tracker import log_translation_call, check_budget, ensure_usage_schema
    _cost_tracker_ok = True
except ImportError:
    pass  # graceful degradation if module missing

# ── System prompt templates ──────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """You are a Sanskrit scholar producing an authoritative English translation in the tradition of Bibek Debroy, Manmatha Nath Dutt, and the BORI critical edition translators.

Your translation principles:
1. FIDELITY: Translate what is written, not what you expect. Do not paraphrase.
2. PROPER NOUNS: Keep all Sanskrit proper nouns in IAST romanization — never translate names of persons, places, rivers, deities, or epithets. E.g.: Arjuna, Dharmarāja, Kurukṣetra, Gaṅgā.
3. VERSE STRUCTURE: For metrical verses (ślokas), reproduce the pāda structure with " / " between half-verses. Mark the full verse end with " //" if clearly a complete śloka.
4. BRACKETED ADDITIONS: Use [brackets] sparingly for essential clarifications only — e.g. "[i.e., Yudhiṣṭhira]" or "[referring to the Pāṇḍavas]".
5. TECHNICAL TERMS: For key Sanskrit philosophical/technical terms where no English equivalent exists, give the IAST term + a brief gloss on first use in the passage, e.g. "dharma (sacred duty)". Do not repeat the gloss.
6. EPITHETS: Translate epithets into English where they illuminate meaning: e.g. "Dhanañjaya (Winner of Wealth)" — but only on first occurrence.
7. CHANDAS: If the verse is metrical, your translation should reflect the dignity and rhythm of the original without being a forced metrical translation.
8. OUTPUT: Produce ONLY the English translation — no preamble, no "Translation:", no meta-commentary. If the text is illegible OCR noise, output exactly: [ILLEGIBLE]"""


def _build_system_prompt(
    doc_code: str,
    category: str = None,
    chapter: str = None,
    verse_ref: str = None,
    chandas: str = None,
    text_type: str = None,
) -> str:
    """Build a context-rich system prompt for a specific passage."""
    lines = [_SYSTEM_PROMPT_BASE, ""]

    # Document context
    ctx_parts = [f"Text: {doc_code.replace('_', ' ').title()}"]
    if category:
        ctx_parts.append(f"Category: {category}")
    if chapter:
        ctx_parts.append(f"Chapter/Adhyāya: {chapter}")
    if verse_ref:
        ctx_parts.append(f"Verse: {verse_ref}")
    if chandas:
        chandas_display = {
            "anustubh": "Anuṣṭubh (8-8-8-8 syllables, most common Purāṇic meter)",
            "tristubh":  "Triṣṭubh (11-11-11-11 syllables, Vedic)",
            "jagati":    "Jagatī (12-12-12-12 syllables)",
            "sloka":     "Śloka (Anuṣṭubh variant)",
            "sardula_vikridata": "Śārdūlavikrīḍita (19 syllables per pāda)",
            "malini":    "Mālinī (15 syllables per pāda)",
        }.get(chandas, chandas)
        ctx_parts.append(f"Meter (chandas): {chandas_display}")
    if text_type == "tika":
        ctx_parts.append("Note: This passage is commentary (ṭīkā), not the root text (mūla)")
    elif text_type == "colophon":
        ctx_parts.append("Note: This is a colophon or chapter-closing verse")
    elif text_type == "prose":
        ctx_parts.append("Note: This passage is Sanskrit prose, not metrical verse")

    if len(ctx_parts) > 1:
        lines.append("Context: " + " | ".join(ctx_parts))

    return "\n".join(lines)


def _build_user_message(
    devanagari: str,
    iast: str = None,
    context_verses: list[dict] = None,
) -> str:
    """Build the user message for translation."""
    parts = []

    # Preceding context (sliding window)
    if context_verses:
        parts.append("=== Preceding verses (for context only — do not translate these) ===")
        for cv in context_verses:
            ref = f"[{cv['verse_ref']}] " if cv.get('verse_ref') else ""
            tr  = cv.get('translation', '')
            if tr:
                parts.append(f"{ref}{tr}")
        parts.append("=== Verse to translate ===")

    # The Sanskrit to translate
    parts.append(devanagari.strip())

    # IAST aid (helps LLM with sandhi resolution and proper nouns)
    if iast and iast.strip():
        parts.append(f"\n[IAST aid: {iast.strip()}]")

    return "\n".join(parts)


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _cache_lookup(
    con: sqlite3.Connection,
    engine: str, src: str, tgt: str,
    texts: List[str],
) -> Dict[str, str]:
    if not texts:
        return {}
    q_marks = ",".join("?" for _ in texts)
    hashes = [_hash(t) for t in texts]
    rows = con.execute(
        f"""SELECT text_hash, output FROM mt_cache
            WHERE engine=? AND lang_in=? AND lang_out=? AND text_hash IN ({q_marks})""",
        (engine, src, tgt, *hashes),
    ).fetchall()
    return {h: o for (h, o) in rows} if rows else {}

def _cache_insert_many(
    con: sqlite3.Connection,
    engine: str, src: str, tgt: str,
    pairs: List[Tuple[str, str]],
) -> None:
    cur = con.cursor()
    for t, out in pairs:
        cur.execute(
            """INSERT OR IGNORE INTO mt_cache(engine,lang_in,lang_out,text_hash,text,output)
               VALUES(?,?,?,?,?,?)""",
            (engine, src, tgt, _hash(t), t, out),
        )
    con.commit()


# ── OpenAI engine ─────────────────────────────────────────────────────────────

def _openai_client():
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("OpenAI client not installed; pip install openai>=1.0") from e
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")
    return OpenAI(api_key=key)

def _openai_translate(
    texts: List[str],
    *,
    model: str,
    system_prompt: str,
    user_messages: List[str] = None,
) -> List[str]:
    client = _openai_client()
    outs: List[str] = []
    msgs_to_use = user_messages or texts
    for i, t in enumerate(texts):
        for attempt in range(RETRIES):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": msgs_to_use[i].strip()},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                outs.append((resp.choices[0].message.content or "").strip())
                break
            except Exception:
                if attempt + 1 >= RETRIES:
                    raise
                time.sleep(SLEEP * (attempt + 1))
        time.sleep(SLEEP)
    return outs


# ── Gemini engine ─────────────────────────────────────────────────────────────

def _gemini_client(model: str, system_prompt: str):
    """Return a configured GenerativeModel instance."""
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError(
            "google-generativeai not installed; pip install google-generativeai>=0.8"
        ) from e
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    generation_config = genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=2048,   # Raised from 1024 to handle long commentary passages
    )
    safety = [
        {"category": "HARM_CATEGORY_HARASSMENT",       "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    return genai.GenerativeModel(
        model_name=model,
        generation_config=generation_config,
        safety_settings=safety,
        system_instruction=system_prompt,
    )

def _gemini_translate(
    texts: List[str],
    *,
    model: str,
    system_prompt: str,
    user_messages: List[str] = None,
) -> List[str]:
    gm = _gemini_client(model, system_prompt)
    outs: List[str] = []
    msgs_to_use = user_messages or texts
    for i, t in enumerate(texts):
        for attempt in range(RETRIES):
            try:
                resp = gm.generate_content(msgs_to_use[i].strip())

                # ── Safe text extraction (handles finish_reason=2 SAFETY blocks) ──
                out = ""
                try:
                    out = (resp.text or "").strip()
                except Exception:
                    # finish_reason=2 (SAFETY) or finish_reason=3 (RECITATION)
                    # resp.text raises ValueError when there are no valid parts.
                    # Check candidates for finish reason
                    finish = None
                    try:
                        finish = resp.candidates[0].finish_reason if resp.candidates else None
                    except Exception:
                        pass
                    if finish == 2:
                        print(f"[gemini] SAFETY BLOCK p{i} — Gemini refused this text. "
                              f"Returning empty (will be skipped).")
                    elif finish == 3:
                        print(f"[gemini] RECITATION BLOCK p{i} — treating as empty.")
                    else:
                        print(f"[gemini] No text in response (finish_reason={finish}), returning empty.")
                    out = ""  # don't retry a safety block — it won't change

                outs.append(out)
                break

            except Exception as exc:
                err_str = str(exc)
                # Detect safety block masquerading as generic exception
                if "finish_reason" in err_str and ("is 2" in err_str or "is 3" in err_str):
                    print(f"[gemini] SAFETY/RECITATION block on attempt {attempt+1} — skipping verse.")
                    outs.append("")
                    break  # no point retrying safety blocks
                if attempt + 1 >= RETRIES:
                    outs.append("")  # don't crash whole batch on one bad verse
                    print(f"[gemini] FAILED after {RETRIES} attempts: {exc}")
                    break
                wait = SLEEP * (2 ** attempt)
                print(f"[gemini] retry {attempt+1}/{RETRIES} after {wait:.1f}s: {exc}")
                time.sleep(wait)
        time.sleep(SLEEP)
    return outs



# ── Echo (test) engine ────────────────────────────────────────────────────────

def _echo_translate(texts: List[str]) -> List[str]:
    return [f"[ECHO] {t[:80]}" for t in texts]


# ── Public API ────────────────────────────────────────────────────────────────

def translate_batch(
    con: sqlite3.Connection,
    texts: List[str],
    *,
    engine: str | None = None,
    src: str = "sa",
    tgt: str = "en",
    # New context-aware parameters
    iast_list:        List[Optional[str]]  = None,
    context_list:     List[Optional[list]] = None,
    doc_code:         str = "",
    category:         str = None,
    chapters:         List[Optional[str]] = None,
    verse_refs:       List[Optional[str]] = None,
    chandas_list:     List[Optional[str]] = None,
    text_types:       List[Optional[str]] = None,
) -> List[str]:
    """Translate a list of Sanskrit strings → English.
    
    New in Phase 3:
    - iast_list: parallel IAST strings for each text
    - context_list: parallel lists of preceding verse dicts for each text
    - doc_code, category, chapters, verse_refs, chandas_list, text_types:
      parallel metadata for building context-rich system prompts
    
    Cache key is still the Sanskrit text hash (context is passed but not cached per-context,
    since caching with full context would have near-zero hit rates).
    """
    engine = (engine or DEFAULT_ENGINE).strip()
    cached = _cache_lookup(con, engine, src, tgt, texts)

    outs:         List[str] = []
    missing_idx:  List[int] = []
    missing_texts:List[str] = []
    missing_msgs: List[str] = []

    for i, t in enumerate(texts):
        h = _hash(t)
        if h in cached:
            outs.append(cached[h])
        else:
            outs.append("")
            missing_idx.append(i)
            missing_texts.append(t)

            # Build context-rich user message
            iast_str  = iast_list[i]  if iast_list  and i < len(iast_list)  else None
            ctx_verses = context_list[i] if context_list and i < len(context_list) else None
            missing_msgs.append(_build_user_message(t, iast_str, ctx_verses))

    # Build context-rich system prompt
    chapter   = chapters[missing_idx[0]]    if chapters    and missing_idx else None
    verse_ref = verse_refs[missing_idx[0]]  if verse_refs  and missing_idx else None
    chandas   = chandas_list[missing_idx[0]] if chandas_list and missing_idx else None
    text_type = text_types[missing_idx[0]]  if text_types  and missing_idx else None

    system_prompt = _build_system_prompt(
        doc_code=doc_code,
        category=category,
        chapter=chapter,
        verse_ref=verse_ref,
        chandas=chandas,
        text_type=text_type,
    ) if (doc_code or missing_idx) else _SYSTEM_PROMPT_BASE

    generated: List[str] = []
    if missing_texts:
        # ── Budget gate ──────────────────────────────────────────────────────
        if _cost_tracker_ok:
            # Estimate cost of this batch before proceeding
            total_in  = sum(len(m) for m in missing_msgs) + len(system_prompt) * len(missing_msgs)
            total_out = total_in * 2  # conservative estimate: output ~ 2× input for translations
            from cost_tracker import estimate_cost_usd as _est
            est_cost = _est(engine, total_in, total_out)
            can_proceed, spent, budget = check_budget(con, est_cost)
            if not can_proceed:
                print(f"[BUDGET] BLOCKED — spent ${spent:.4f} of ${budget:.2f}. "
                      f"Estimated next batch: ${est_cost:.4f}. "
                      f"Call resume_budget() or increase budget to continue.")
                # Return empty strings for uncached — don't call API
                return [outs[i] or "" for i in range(len(texts))]

        t_start = time.time()

        if engine.startswith("openai:"):
            model = engine.split(":", 1)[1]
            generated = _openai_translate(
                missing_texts, model=model,
                system_prompt=system_prompt,
                user_messages=missing_msgs,
            )
        elif engine.startswith("gemini:"):
            model = engine.split(":", 1)[1]
            generated = _gemini_translate(
                missing_texts, model=model,
                system_prompt=system_prompt,
                user_messages=missing_msgs,
            )
        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
        else:
            print(f"[infer_mt] WARNING: unknown engine '{engine}', using echo")
            generated = _echo_translate(missing_texts)

        duration = time.time() - t_start

        # ── Log actual cost ──────────────────────────────────────────────────
        if _cost_tracker_ok and not engine.startswith("echo"):
            actual_in  = sum(len(m) for m in missing_msgs) + len(system_prompt) * len(missing_msgs)
            actual_out = sum(len(g) for g in generated)
            cost = log_translation_call(
                con, doc_code, engine,
                in_chars=actual_in,
                out_chars=actual_out,
                duration_s=duration,
                passages=len(missing_texts),
                ok=True,
            )
            rate = len(missing_texts) / max(0.01, duration) * 3600
            print(f"[COST] {len(missing_texts)} passages | {duration:.1f}s | "
                  f"${cost:.5f} | {rate:.0f} passages/hr | engine={engine}")

        _cache_insert_many(con, engine, src, tgt, list(zip(missing_texts, generated)))

    # Stitch back in original order
    it = iter(generated)
    final: List[str] = []
    for i, t in enumerate(texts):
        if outs[i]:
            final.append(outs[i])
        else:
            final.append(next(it))
    return final


    # Build context-rich system prompt (use first item's metadata for batch)
    # For per-passage accuracy, translate_passages.py should send batches of 1
    # for verse-level passages with unique chapter/verse context.
    chapter   = chapters[missing_idx[0]]    if chapters    and missing_idx else None
    verse_ref = verse_refs[missing_idx[0]]  if verse_refs  and missing_idx else None
    chandas   = chandas_list[missing_idx[0]] if chandas_list and missing_idx else None
    text_type = text_types[missing_idx[0]]  if text_types  and missing_idx else None

    system_prompt = _build_system_prompt(
        doc_code=doc_code,
        category=category,
        chapter=chapter,
        verse_ref=verse_ref,
        chandas=chandas,
        text_type=text_type,
    ) if (doc_code or missing_idx) else _SYSTEM_PROMPT_BASE

    generated: List[str] = []
    if missing_texts:
        if engine.startswith("openai:"):
            model = engine.split(":", 1)[1]
            generated = _openai_translate(
                missing_texts, model=model,
                system_prompt=system_prompt,
                user_messages=missing_msgs,
            )
        elif engine.startswith("gemini:"):
            model = engine.split(":", 1)[1]
            generated = _gemini_translate(
                missing_texts, model=model,
                system_prompt=system_prompt,
                user_messages=missing_msgs,
            )
        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
        else:
            print(f"[infer_mt] WARNING: unknown engine '{engine}', using echo")
            generated = _echo_translate(missing_texts)

        _cache_insert_many(con, engine, src, tgt, list(zip(missing_texts, generated)))

    # Stitch back in original order
    it = iter(generated)
    final: List[str] = []
    for i, t in enumerate(texts):
        if outs[i]:
            final.append(outs[i])
        else:
            final.append(next(it))
    return final
