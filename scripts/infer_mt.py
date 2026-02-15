#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, time, sqlite3, hashlib
from typing import List, Tuple, Dict

DEFAULT_ENGINE = os.environ.get("MT_ENGINE", "openai:gpt-4o-mini")
SLEEP = float(os.environ.get("MT_SLEEP", "0.6"))
RETRIES = 3

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _cache_lookup(con: sqlite3.Connection, engine: str, src: str, tgt: str, texts: List[str]) -> Dict[str, str]:
    if not texts: return {}
    q_marks = ",".join("?" for _ in texts)
    hashes = [_hash(t) for t in texts]
    rows = con.execute(f"""
        SELECT text_hash, output FROM mt_cache
        WHERE engine=? AND lang_in=? AND lang_out=? AND text_hash IN ({q_marks})
    """, (engine, src, tgt, *hashes)).fetchall()
    return {h:o for (h,o) in rows} if rows else {}

def _cache_insert_many(con: sqlite3.Connection, engine: str, src: str, tgt: str, pairs: List[Tuple[str,str]]) -> None:
    cur = con.cursor()
    for t, out in pairs:
        cur.execute("""INSERT OR IGNORE INTO mt_cache(engine,lang_in,lang_out,text_hash,text,output)
                       VALUES(?,?,?,?,?,?)""", (engine, src, tgt, _hash(t), t, out))
    con.commit()

def _openai_client():
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("OpenAI client not installed; pip install openai>=1.0") from e
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=key)

def _openai_translate(texts: List[str], *, model: str) -> List[str]:
    client = _openai_client()
    system = "You are a precise Sanskrit→English translator. Preserve proper nouns; output only the translation."
    outs : List[str] = []
    for t in texts:
        for attempt in range(RETRIES):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role":"system","content":system},
                              {"role":"user","content":t.strip()}],
                    temperature=0.1,
                )
                outs.append((resp.choices[0].message.content or "").strip())
                break
            except Exception:
                if attempt+1 >= RETRIES: raise
                time.sleep(SLEEP*(attempt+1))
        time.sleep(SLEEP)
    return outs

def _echo_translate(texts: List[str]) -> List[str]:
    return [f"[ECHO] {t}" for t in texts]

def translate_batch(con: sqlite3.Connection, texts: List[str], *, engine: str | None = None, src="sa", tgt="en") -> List[str]:
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
            outs.append("")  # placeholder
            missing_idx.append(i)
            missing_texts.append(t)

    generated: List[str] = []
    if missing_texts:
        if engine.startswith("openai:"):
            model = engine.split(":",1)[1]
            generated = _openai_translate(missing_texts, model=model)
        elif engine.startswith("echo"):
            generated = _echo_translate(missing_texts)
        else:
            generated = _echo_translate(missing_texts)

        pairs = [(t,o) for t,o in zip(missing_texts, generated)]
        _cache_insert_many(con, engine, src, tgt, pairs)

    # stitch back
    it = iter(generated)
    final: List[str] = []
    for i, t in enumerate(texts):
        if outs[i]:
            final.append(outs[i])
        else:
            final.append(next(it))
    return final
