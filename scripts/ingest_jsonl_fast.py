#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast ingest for OCR JSONL → SQLite (Windows-safe)
- Creates baseline schema automatically if missing (docs, passages, FTS)
- Parses page number from filename suffix: <doc>_<0001>.jsonl → page_no=1
- UPSERT by (doc_id, page_no, idx) and keeps FTS in sync

Usage
  python scripts/ingest_jsonl_fast.py --doc Bodhicaryavatara --glob data/raw/Bodhicaryavatara_0001.jsonl --db data/context.db
"""
import argparse, json, sqlite3, sys, re, pathlib, glob
from typing import Iterable

from db_utils import connect, ensure_schema, ensure_doc

# Extract trailing digits after last underscore: ..._0001.jsonl -> 1
PAGE_RE = re.compile(r"_(\d+)(?:\.[A-Za-z0-9]+)?$", re.UNICODE)


def parse_page_no_from_path(p: pathlib.Path) -> int:
    m = PAGE_RE.search(p.name)
    return int(m.group(1)) if m else 1


def read_jsonl(path: pathlib.Path):
    items = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            items.append(json.loads(ln))
    return items


def decide_page_no(path: pathlib.Path, items):
    pn = parse_page_no_from_path(path)
    if pn and pn > 0: return pn
    if items:
        rec = items[0]
        for k in ("page_no", "page", "pageNumber"):
            v = rec.get(k)
            if isinstance(v, int) and v > 0:
                return v
    return 1


def upsert_passages(con: sqlite3.Connection, doc_id: int, page_no: int, items: Iterable[dict]):
    cur = con.cursor()
    for i, rec in enumerate(items, 1):  # idx is 1-based
        text = (rec.get("text") or "").strip()
        tr   = (rec.get("translation") or "").strip()
        cur.execute(
            """
            INSERT INTO passages(doc_id, page_no, idx, text, translation)
            VALUES(?,?,?,?,?)
            ON CONFLICT(doc_id,page_no,idx) DO UPDATE SET
              text=excluded.text,
              translation=excluded.translation
            """,
            (doc_id, page_no, i, text, tr)
        )
        rid = cur.lastrowid  # same as passages.id for INTEGER PRIMARY KEY
        # refresh FTS
        cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rid,))
        cur.execute("INSERT INTO passages_fts(rowid, text, translation) VALUES (?,?,?)", (rid, text or "", tr or ""))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True, help="doc code like MBh-01")
    ap.add_argument("--glob", required=True, help="file path or glob pattern")
    ap.add_argument("--db", default="data/context.db")
    args = ap.parse_args()

    con = connect(args.db)
    ensure_schema(con)

    doc_id = ensure_doc(con, args.doc)

    # Resolve files (supports absolute paths and globs)
    paths = sorted({pathlib.Path(p) for p in glob.glob(args.glob)})
    if not paths:
        p = pathlib.Path(args.glob)
        if p.exists(): paths = [p]
    if not paths:
        print("No files matched:", args.glob, file=sys.stderr)
        sys.exit(1)

    for p in paths:
        items = read_jsonl(p)
        page_no = decide_page_no(p, items)
        upsert_passages(con, doc_id, page_no, items)
        print(f"ingested {len(items):5d} items from {p.name} (page={page_no})")

if __name__ == "__main__":
    main()
