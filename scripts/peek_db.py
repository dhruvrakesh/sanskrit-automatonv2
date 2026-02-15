# scripts/peek_db.py
import sqlite3, os
DB = os.environ.get("SA_DB_PATH", "data/context.db")
con = sqlite3.connect(DB); cur = con.cursor()
print("DB:", DB)
print("runs:", cur.execute(
    "select id,status,doc_code,started_at,finished_at from runs order by rowid desc limit 5"
).fetchall())
pc = cur.execute("select count(*) from passages").fetchone()[0]
print("passages:", pc)
rows = cur.execute(
    "select page_no,idx,substr(text,1,60),substr(ifnull(translation,''),1,120) "
    "from passages order by id desc limit 5"
).fetchall()
print("sample:")
for r in rows: print(" -", r)
con.close()
