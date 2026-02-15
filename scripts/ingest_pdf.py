#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, os, sqlite3, pathlib, json, subprocess, sys, hashlib
from db_utils import connect, ensure_schema, ensure_doc, backup_db
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OCR = ROOT / "scripts" / "ocr_pdf.py"

def _load_dotenv_from_repo_root():
    if os.environ.get("OPENAI_API_KEY"):
        return
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"): continue
            k, sep, v = s.partition("=")
            if sep: os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_dotenv_from_repo_root()

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd):
    p = subprocess.run(cmd, text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    if os.path.exists(args.db) and not args.no_backup:
        print("DB backup:", backup_db(args.db))

    con = connect(args.db); ensure_schema(con)

    out_jsonl = ROOT / "data" / "raw" / (pathlib.Path(args.pdf).stem + ".jsonl")
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(OCR), "--pdf", args.pdf, "--out", str(out_jsonl)])

    items = []
    with open(out_jsonl, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if ln: items.append(json.loads(ln))
    if not items:
        print("No OCR items produced"); return

    doc_id = ensure_doc(con, args.doc)
    pages = [int(r.get("page_no") or r.get("page") or 0) or 1 for r in items]
    lo, hi = (min(pages), max(pages)) if pages else (1,1)

    cur = con.cursor(); cur.execute("BEGIN")
    for rec in items:
        pg = int(rec.get("page_no") or rec.get("page") or 0) or 1
        text = (rec.get("text") or "").strip()
        # idx is 1-based per page
        r = cur.execute("SELECT COALESCE(MAX(idx),0)+1 FROM passages WHERE doc_id=? AND page_no=?", (doc_id, pg)).fetchone()
        idx = int(r[0] or 1)
        cur.execute("""
            INSERT INTO passages(doc_id,page_no,idx,text) VALUES (?,?,?,?)
            ON CONFLICT(doc_id,page_no,idx) DO UPDATE SET text=excluded.text
        """, (doc_id, pg, idx, text))
        rid = cur.execute("SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?", (doc_id, pg, idx)).fetchone()[0]
        cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rid,))
        cur.execute("INSERT INTO passages_fts(rowid,text,translation) VALUES (?,?,COALESCE((SELECT translation FROM passages WHERE id=?),'') )", (rid, text, rid))
    con.commit()
    print(f"ingested {len(items)} items (pages {lo}-{hi})")

if __name__ == "__main__":
    main()
