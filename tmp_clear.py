import sqlite3
con = sqlite3.connect(r"data/context.db"); cur = con.cursor()
doc = cur.execute("select id from docs where code=?", ("MBh-01",)).fetchone()
if doc:
    cur.execute("delete from passages where doc_id=?", (doc[0],))
    con.commit()
    print("cleared MBh-01 passages")
else:
    print("MBh-01 doc not found; nothing to clear")
