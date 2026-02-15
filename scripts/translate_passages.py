#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sqlite3, time
from normalize_text import normalize_sanskrit
from text_filters import should_translate, clean_for_mt
from infer_mt import translate_batch
from db_utils import ensure_schema

def _page_col(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    for c in ("page_no","pageno","page","pg","pageNumber","page_num"):
        if c in cols: return c
    return "page_no"

def _idx(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    for c in ("idx","line_no","line","lineno","i"):
        if c in cols: return c
    return "rowid"

def _doc_join(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "doc_id" in cols and "docs" in tabs: return "JOIN docs d ON d.id=p.doc_id", "d.code"
    if "doc" in cols: return "", "p.doc"
    if "doc_code" in cols: return "", "p.doc_code"
    return "", None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--since-page", type=int, default=1)
    ap.add_argument("--until-page", type=int, default=999999)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--engine", default=None)
    ap.add_argument("--no-skip", action="store_true")
    ap.add_argument("--min-dev", type=float, default=0.08)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    con = sqlite3.connect(args.db); ensure_schema(con)
    pg = _page_col(con); ix = _idx(con); join, docexpr = _doc_join(con)
    if docexpr is None:
        raise SystemExit("DB schema missing doc indicator on passages")

    rows = list(con.execute(f"""
        SELECT p.rowid, {pg}, {ix}, p.text
        FROM passages p {join}
        WHERE {docexpr}=? AND COALESCE(TRIM(p.translation),'')=''
          AND {pg} BETWEEN ? AND ?
        ORDER BY {pg}, {ix}
    """, (args.doc, args.since_page, args.until_page)))

    if args.limit:
        rows = rows[:args.limit]

    if not rows:
        print("todo = 0 rows"); return

    todo = []
    for rowid, page, idx, text in rows:
        s = normalize_sanskrit(text or "")
        if args.no_skip or should_translate(s, min_dev=args.min_dev):
            todo.append((rowid, clean_for_mt(s)))

    print(f"todo = {len(todo)} rows")
    if not todo: return

    B = 20
    for i in range(0, len(todo), B):
        batch = todo[i:i+B]
        outs = translate_batch(con, [t for _, t in batch], engine=args.engine)
        con.execute("BEGIN")
        for (rowid, _), out in zip(batch, outs):
            con.execute("UPDATE passages SET translation=? WHERE rowid=?", (out, rowid))
        con.commit()
        lo = (i+1); hi = (i+len(batch))
        print(f"[{lo}:{hi}] ✓")
        time.sleep(args.sleep)

if __name__ == "__main__":
    main()
