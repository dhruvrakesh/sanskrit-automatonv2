# scripts/audit_headings.py
import argparse, sqlite3
from text_filters import strip_leading_headings, frac_devanagari

ap = argparse.ArgumentParser()
ap.add_argument("--doc", required=True)
ap.add_argument("--since-page", type=int, default=1)
ap.add_argument("--until-page", type=int, default=10**9)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--db", default="data/context.db")
args = ap.parse_args()

con = sqlite3.connect(args.db); cur = con.cursor()
rows = cur.execute("""
  select p.page_no, p.idx, p.text
    from passages p join docs d on d.id=p.doc_id
   where d.code=? and p.page_no between ? and ?
   order by p.page_no, p.idx
""", (args.doc, args.since_page, args.until_page)).fetchall()
if args.limit: rows = rows[:args.limit]

skip, keep, examples = 0, 0, []
for page_no, idx, text in rows:
    cleaned, reason = strip_leading_headings(text or "")
    if reason:
        skip += 1
        if len(examples) < 15:
            preview = (text or "").replace("\n"," ")[:90]
            examples.append((page_no, idx, reason, preview))
    else:
        keep += 1

print(f"total={len(rows)}  keep={keep}  skip={skip}  skip%={(100.0*skip/max(1,len(rows))):.1f}")
print("\nSample skipped:")
for p,i,r,pr in examples:
    print(f"  [{p}:{i}] {r:>24} | {pr}")
