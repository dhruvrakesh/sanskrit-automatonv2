import sqlite3
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True,timeout=30)
q=lambda s: c.execute(s).fetchone()[0]
D="AND d.code='AphorismsOfSandilya'"
print("doc rows        :", q("SELECT COUNT(*) FROM docs WHERE code='AphorismsOfSandilya'"))
print("total passages  :", q(f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE 1=1 {D}"))
print("EN non-empty    :", q(f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE TRIM(COALESCE(p.translation,''))<>'' {D}"))
print("EN empty/blank  :", q(f"SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id WHERE TRIM(COALESCE(p.translation,''))='' {D}"))
c.close()
