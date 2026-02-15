#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, pathlib, re
from normalize_text import normalize_sanskrit

HARD_BREAK = re.compile(r"-\s*\n\s*")
WS = re.compile(r"\s+")

def process_record(text: str) -> str:
    s = (text or "").replace("\r\n","\n").replace("\r","\n")
    s = HARD_BREAK.sub("", s)
    s = WS.sub(" ", s)
    s = normalize_sanskrit(s)
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inp = pathlib.Path(args.inp); out = pathlib.Path(args.out)
    rows = []
    with inp.open("r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if not ln.strip(): continue
            rec = json.loads(ln)
            rec["text"] = process_record(rec.get("text") or "")
            rows.append(rec)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"normalized {len(rows)} records -> {out}")

if __name__ == "__main__":
    main()
