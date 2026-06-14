#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
infer_mt.py — translation engine dispatcher

Supported engine strings:
  openai:<model>      e.g.  openai:gpt-4o-mini
  gemini:<model>      e.g.  gemini:gemini-2.5-pro   (default quality)
                             gemini:gemini-2.0-flash  (fast/cheap)
  echo                passthrough for testing
"""
from __future__ import annotations
import os, time, sqlite3, hashlib
from typing import List, Tuple, Dict

DEFAULT_ENGINE = os.environ.get("MT_ENGINE", "gemini:gemini-2.5-pro")
SLEEP = float(os.environ.get("MT_SLEEP", "0.6"))
RETRIES = 3

# Sanskrit → English system prompt (shared across all engines)
_SYSTEM_PROMPT = (
    "You are an expert Sanskrit scholar and translator grounded in Pāṇinian grammar, "
    "BORI critical editions, and the traditions of Bibek Debroy and Manmatha Nath Dutt. "
    "Translate the given Sanskrit passage to clear, scholarly English. "
    "Preserve proper nouns (names of persons, places, tribes, rivers, deities) without translation. "
    "Output only the English translation — no commentary, no bracketed notes, no preamble."
)


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _cache_lookup(
    con: sqlite3.Connection, engine: str, src: str, tgt: str, texts: List[str]
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
    engine: str,
    src: str,
    tgt: str,
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

def _openai_translate(texts: List[str], *, model: str) -> List[str]:
    client = _openai_client()
    outs: List[str] = []
    for t in texts:
        for attempt in range(RETRIES):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": t.strip()},
                    ],
                    temperature=0.1,
                )
                outs.append((resp.choices[0].message.content or "").strip())
                break
            except Exception:
                if attempt + 1 >= RETRIES:
                    raise
                time.sleep(SLEEP * (attempt + 1))
        time.sleep(SLEEP)
    return outs


# ── Gemini engine ──────────────────────────────────────────────────────────────

def _gemini_client(model: str):
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
        max_output_tokens=1024,
    )
    safety = [
        {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH",        "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",  "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",  "threshold": "BLOCK_NONE"},
    ]
    return genai.GenerativeModel(
        model_name=model,
        generation_config=generation_config,
        safety_settings=safety,
        system_instruction=_SYSTEM_PROMPT,
    )

def _gemini_translate(texts: List[str], *, model: str) -> List[str]:
    gm = _gemini_client(model)
    outs: List[str] = []
    for t in texts:
        for attempt in range(RETRIES):
            try:
                resp = gm.generate_content(t.strip())
                out = (resp.text or "").strip() if resp.text else ""
                outs.append(out)
                break
            except Exception as exc:
                if attempt + 1 >= RETRIES:
                    raise
                wait = SLEEP * (2 ** attempt)
                print(f"[gemini] retry {attempt+1}/{RETRIES} after {wait:.1f}s: {exc}")
                time.sleep(wait)
        time.sleep(SLEEP)
    return outs


# ── Echo (test) engine ─────────────────────────────────────────────────────────

def _echo_translate(texts: List[str]) -> List[str]:
    return [f"[ECHO] {t}" for t in texts]


# ── Public API ────────────────────────────────────────────────────────────────

def translate_batch(
    con: sqlite3.Connection,
    texts: List[str],
    *,
    engine: str | None = None,
    src: str = "sa",
    tgt: str = "en",
) -> List[str]:
    """Translate a list of Sanskrit strings → English using cache + chosen engine.

    engine examples:
      "gemini:gemini-2.5-pro"    — highest quality
      "gemini:gemini-2.0-flash"  — fast & cheap
      "openai:gpt-4o"            — OpenAI GPT-4o
      "openai:gpt-4o-mini"       — OpenAI mini
      "echo"                     — passthrough (testing)
    """
    engine = (engine or DEFAULT_ENGINE).strip()
    cached = _cache_lookup(con, engine, src, tgt, texts)

    outs: List[str] = []
    missing_idx: List[int] = []
    missing_texts: List[str] = []

    for i, t in enumerate(texts):
        h = _hash(t)
        if h in cached:
            outs.append(cached[h])
        else:
            outs.append("")          # placeholder
            missing_idx.append(i)
            missing_texts.append(t)

    generated: List[str] = []
    if missing_texts:
        if engine.startswith("openai:"):
            model = engine.split(":", 1)[1]
            generated = _openai_translate(missing_texts, model=model)
        elif engine.startswith("gemini:"):
            model = engine.split(":", 1)[1]
            generated = _gemini_translate(missing_texts, model=model)
        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
        else:
            # Unknown engine — fall back to echo with warning
            print(f"[infer_mt] WARNING: unknown engine '{engine}', using echo passthrough")
            generated = _echo_translate(missing_texts)

        _cache_insert_many(con, engine, src, tgt, list(zip(missing_texts, generated)))

    # Stitch cached + newly generated back in original order
    it = iter(generated)
    final: List[str] = []
    for i, t in enumerate(texts):
        if outs[i]:
            final.append(outs[i])
        else:
            final.append(next(it))
    return final
