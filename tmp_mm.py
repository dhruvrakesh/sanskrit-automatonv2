import sqlite3
con = sqlite3.connect(r"data/context.db"); cur = con.cursor()
print("rows =", cur.execute(
    "select count(*) from passages join docs d on d.id=doc_id where d.code=?",
    ("MBh-01",)
).fetchone()[0])
print("min/max page_no =", cur.execute(
    "select min(page_no), max(page_no) from passages join docs d on d.id=doc_id where d.code=?",
    ("MBh-01",)
).fetchone())
