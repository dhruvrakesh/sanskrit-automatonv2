#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Morph parsing:
- If HERITAGE_API is set -> use it.
- Else SAFE heuristic (default) that never crashes and returns useful tokens/lemmas.
- If SA_SAFE_MODE=0 and sanskrit_parser imports cleanly, use it instead.
"""
import os, sys, json, argparse
from typing import Dict, Any
import re

def call_heritage_api(text: str) -> Dict[str, Any]:
    import httpx
    base = os.environ.get("HERITAGE_API")
    if not base:
        raise RuntimeError("HERITAGE_API not set")
    url = base.rstrip("/") + "/analyze"
    payload = {"text": text, "mode": "best", "output": "json", "script": "DEVANAGARI"}
    r = httpx.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def heuristic_morph(text: str) -> Dict[str, Any]:
    # Tokenize on spaces/danda; very light lemmas via SLP1 transliteration
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    dev, slp = getattr(sanscript, "DEVANAGARI", "DEVANAGARI"), getattr(sanscript, "SLP1", "SLP1")
    tokens = [t for t in re.split(r"[|।॥\s]+", text) if t]
    morph = []
    for t in tokens:
        lemma = transliterate(t, dev, slp)  # heuristic lemma in SLP1
        morph.append({"form": t, "lemma": lemma, "pos": None})
    return {"engine": "heuristic", "tokens": tokens, "morph": morph}

def sp_morph(text: str) -> Dict[str, Any]:
    from indic_transliteration import sanscript
    from sanskrit_parser.base.sanskrit_base import SanskritObject
    from sanskrit_parser.api import Parser
    dev, slp = getattr(sanscript, "DEVANAGARI", "DEVANAGARI"), getattr(sanscript, "SLP1", "SLP1")
    p = Parser(input_encoding=dev)
    sobj = SanskritObject(text, encoding=dev)
    split_iter = p.split(sobj)
    first = next(iter(split_iter), [])
    tokens = [getattr(w, "transcoded", lambda *_: str(w))(dev) for w in first] if first else []
    morph = []
    for w in first:
        try:
            lemma = getattr(w, "lemma", None) or w.transcoded(slp)
            form = w.transcoded(dev)
        except Exception:
            lemma = getattr(w, "lemma", None) or str(w)
            form = str(w)
        morph.append({"form": form, "lemma": lemma, "pos": None})
    return {"engine": "sanskrit_parser", "tokens": tokens, "morph": morph}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = sys.stdin.read().strip()
    if not text:
        out = {"engine": "error", "error": "empty input"}
    else:
        try:
            if os.environ.get("HERITAGE_API"):
                out = call_heritage_api(text)
            else:
                safe = os.environ.get("SA_SAFE_MODE", "1") != "0"
                if safe:
                    out = heuristic_morph(text)
                else:
                    out = sp_morph(text)
        except Exception as e:
            out = {"engine": "error", "error": f"{type(e).__name__}: {e}"}

    print(json.dumps(out, ensure_ascii=False) if args.json else
          (" ".join(out.get("tokens", [])) if out.get("tokens") else json.dumps(out, ensure_ascii=False)))

if __name__ == "__main__":
    main()
