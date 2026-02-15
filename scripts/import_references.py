#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import reference translations (BORI / Debroy / Dutt) into SQLite.

Usage:
  python scripts/import_references.py --csv refs.csv --db data/context.db --auto-normalize
  # or
  python scripts/import_references.py --jsonl refs.jsonl --db data/context.db
CSV headers accepted: normalized OR sanskrit (then we normalize), bori, debroy, dutt, notes
"""
import os, sys, csv, json, argparse, sqlite3, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def normalize(text: str) -> str:
    # call existing normalizer to avoid duplicates
    cmd = [sys.executable, str(ROOT/"scripts"/"normalize_text.py"), "--json"]
    p = subprocess.run(cmd, input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if p.returncode != 0:
        return text.strip()
    import json as _j
    return (_j.loads(p.stdout.decode("utf-8")).get("normalized") or text).strip()

def ensure_table(db: sqlite3.Connection):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS reference_translations(
      norm TEXT PRIMARY KEY,
      bori TEXT,
      debroy TEXT,
      dutt TEXT,
      notes TEXT
    );
    """)
    db.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--jsonl")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--auto-normalize", action="store_true", help="use normalize_text.py for 'sanskrit' column")
    args = ap.parse_args()

    if not args.csv and not args.jsonl:
        ap.error("Provide --csv or --jsonl")

    db = sqlite3.connect(args.db)
    ensure_table(db)

    rows = []
    if args.csv:
        with open(args.csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    else:
        with open(args.jsonl, "r", encoding="utf-8") as f:
            for ln in f:
                rows.append(json.loads(ln))

    n_ins = 0
    for r in rows:
        norm = r.get("normalized")
        if not norm and args.auto_normalize and r.get("sanskrit"):
            norm = normalize(r["sanskrit"])
        if not norm:
            continue
        db.execute(
            "INSERT OR REPLACE INTO reference_translations(norm, bori, debroy, dutt, notes) VALUES (?,?,?,?,?)",
            (norm, r.get("bori",""), r.get("debroy",""), r.get("dutt",""), r.get("notes",""))
        )
        n_ins += 1
    db.commit()
    print(f"Imported {n_ins} reference rows into {args.db}")

if __name__ == "__main__":
    main()
