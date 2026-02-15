import sqlite3
con = sqlite3.connect(r"data/context.db"); cur = con.cursor()
for r in cur.execute(
    "select page_no, idx, substr(text,1,60) "
    "from passages join docs d on d.id=doc_id "
    "where d.code=? order by page_no, idx limit 8",
    ("MBh-01",)
):
    print(r)
