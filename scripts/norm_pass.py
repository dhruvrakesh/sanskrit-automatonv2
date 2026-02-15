#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pre-normalize OCR JSONL files (strip ZW*, NFC, danda unify) into data/norm/*.jsonl
Keeps page/idx; does not translate or NER.
"""
import argparse, json, unicodedata, pathlib, sys

ZWS = ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff")
DANDAS = ("\u0964", "\u0965")
HYPHS  = ("-\u2010\u2011\u2012\u2013")

def nfc_clean(s: str) -> str:
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFC", s)
    for z in ZWS: s = s.replace(z, "")
    for d in DANDAS: s = s.replace(d, "|")
    for h in HYPHS:  s = s.replace(h, "-")
    return s.strip()

def norm_file(src: pathlib.Path, dst: pathlib.Path):
    out = []
    with src.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip(): continue
            row = json.loads(line)
            row["text"] = nfc_clean(row.get("text",""))
            # carry forward page / idx if present; otherwise try to infer idx order
            out.append(row)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as g:
        for row in out:
            g.write(json.dumps(row, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir",  default="data/raw",  help="folder with OCR .jsonl files")
    ap.add_argument("--out-dir", default="data/norm", help="folder to write normalized .jsonl")
    ap.add_argument("--glob",    default="*.jsonl",   help="pattern (default: *.jsonl)")
    args = ap.parse_args()

    ind  = pathlib.Path(args.in_dir)
    outd = pathlib.Path(args.out_dir)
    files = sorted(ind.glob(args.glob))
    if not files:
        print(f"No files found in {ind} matching {args.glob}", file=sys.stderr); sys.exit(1)

    for i,src in enumerate(files, 1):
        dst = outd/src.name
        norm_file(src, dst)
        print(f"[{i}/{len(files)}] normalized → {dst}")

if __name__ == "__main__":
    main()
