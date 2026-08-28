import sqlite3
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
cur=c.execute("""SELECT d.code, d.category,
  COUNT(p.id) AS passages,
  SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) AS en_done
  FROM docs d LEFT JOIN passages p ON p.doc_id=d.id
  WHERE d.code LIKE '%andilya%' OR d.code LIKE 'Aphorism%'
  GROUP BY d.code""")
cols=[x[0] for x in cur.description]
rows=cur.fetchall()
print("rows:", len(rows))
for r in rows: print(dict(zip(cols,r)))
c.close()
