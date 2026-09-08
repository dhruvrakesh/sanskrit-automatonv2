import sqlite3
db="data/context.db"; doc="panchatantra"
con=sqlite3.connect(db); cur=con.cursor()
tot = cur.execute("select count(*) from passages where doc=?", (doc,)).fetchone()[0]
miss= cur.execute("select count(*) from passages where doc=? and (en is null or trim(en)='')", (doc,)).fetchone()[0]
print(f"total={tot}  missing_en={miss}  covered={tot-miss}")
