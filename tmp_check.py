import sqlite3
con = sqlite3.connect("data/context.db")
cur = con.cursor()
print("rows =", cur.execute(
    "select count(*) from passages join docs d on d.id=doc_id where d.code=?",
    ("MBh-01",)
).fetchone()[0])
