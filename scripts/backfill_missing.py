#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sqlite3, time
from infer_mt import translate_batch
from db_utils import ensure_schema


def main():
ap = argparse.ArgumentParser()
ap.add_argument("--db", default="data/context.db")
ap.add_argument("--doc", required=True)
ap.add_argument("--engine", default=None)
ap.add_argument("--sleep", type=float, default=0.6)
args = ap.parse_args()


con = sqlite3.connect(args.db); ensure_schema(con)
rows = list(con.execute("""
SELECT p.rowid, p.text FROM passages p
JOIN docs d ON d.id=p.doc_id
WHERE d.code=? AND COALESCE(TRIM(p.translation),'')=''
ORDER BY p.page_no, p.idx
""", (args.doc,)))
if not rows:
print("nothing to backfill"); return


B=20
for i in range(0,len(rows),B):
batch = rows[i:i+B]
outs = translate_batch(con, [t for _,t in batch], engine=args.engine)
con.execute("BEGIN")
for (rowid,_), out in zip(batch, outs):
con.execute("UPDATE passages SET translation=? WHERE rowid=?", (out, rowid))
con.commit()
print(f"[{i+1}:{min(i+B,len(rows))}] ✓")
time.sleep(args.sleep)


if __name__ == "__main__":
main()