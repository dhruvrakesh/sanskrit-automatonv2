#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resilient sandhi splitting.

- Safe mode (default): simple, deterministic splits (never crashes).
- If SA_SAFE_MODE=0 and sanskrit_parser imports cleanly, use it for better splits.
"""
import sys, os, json, argparse, re, warnings

warnings.filterwarnings("ignore", category=UserWarning)
os.environ.setdefault("SQLALCHEMY_SILENCE_UBER_WARNING", "1")

def _fallback_splits(dev_text: str):
    text = dev_text.strip()
    parts = re.split(r"[|।॥]+", text)
    parts = [p.strip() for p in parts if p.strip()] or [text]
    splits = []
    for p in parts:
        toks = re.split(r"\s+", p)
        toks = [t for t in toks if t]
        if toks:
            splits.append(toks)
    return splits or [[text]]

def _sp_splits(dev_text: str, topk: int):
    try:
        from indic_transliteration import sanscript
        from sanskrit_parser.base.sanskrit_base import SanskritObject
        from sanskrit_parser.api import Parser
    except Exception as e:
        raise RuntimeError(f"sanskrit_parser import failed: {e}")
    dev = getattr(sanscript, "DEVANAGARI", "DEVANAGARI")
    parser = Parser(input_encoding=dev)
    sobj = SanskritObject(dev_text, encoding=dev)
    out = []
    for seg in parser.split(sobj):
        try:
            out.append([w.transcoded(dev) for w in seg])
        except Exception:
            out.append([str(w) for w in seg])
        if len(out) >= topk:
            break
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = sys.stdin.read().strip()
    if not text:
        resp = {"text": "", "splits": []}
        print(json.dumps(resp, ensure_ascii=False) if args.json else "")
        return

    safe = os.environ.get("SA_SAFE_MODE", "1") != "0"  # default SAFE
    try:
        if safe:
            splits = _fallback_splits(text)
            resp = {"text": text, "engine": "fallback", "splits": splits}
        else:
            splits = _sp_splits(text, args.topk)
            resp = {"text": text, "engine": "sanskrit_parser", "splits": splits}
    except Exception as e:
        resp = {"text": text, "engine": "fallback",
                "warning": f"{type(e).__name__}: {e}",
                "splits": _fallback_splits(text)}

    if args.json:
        print(json.dumps(resp, ensure_ascii=False))
    else:
        for i, s in enumerate(resp["splits"], 1):
            print(f"{i}. {' + '.join(s)}")

if __name__ == "__main__":
    main()
