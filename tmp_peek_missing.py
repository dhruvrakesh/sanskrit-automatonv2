import sqlite3
con=sqlite3.connect(r"data/context.db"); cur=con.cursor()
rows=cur.execute("""
  SELECT p.page_no, p.idx, substr(p.text,1,120)
  FROM passages p JOIN docs d ON d.id=p.doc_id
  WHERE d.code=? AND (p.translation IS NULL OR trim(p.translation)='')
  ORDER BY p.page_no, p.idx
""",("MBh-01",)).fetchall()
for r in rows: print(r)
