import sqlite3, os
db = os.path.join("data","context.db")
con = sqlite3.connect(db); cur = con.cursor()

# reset runs
cur.execute("DROP TABLE IF EXISTS runs")
cur.execute("CREATE TABLE runs(doc TEXT NOT NULL, page_from INTEGER NOT NULL, page_to INTEGER NOT NULL)")

# detect page column
page_col = "page_no"
cols = {r[1] for r in cur.execute("PRAGMA table_info(passages)")}
if "page_no" not in cols and "page" in cols:
    page_col = "page"

tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}

if {"docs","pages"}.issubset(tables):
    cur.execute(f"""
      INSERT INTO runs(doc,page_from,page_to)
      SELECT d.code, MIN(pg.page_no), MAX(pg.page_no)
      FROM pages pg JOIN docs d ON pg.doc_id=d.id
      GROUP BY d.code
    """)
elif "passages" in tables and "doc" in cols:
    cur.execute(f"""
      INSERT INTO runs(doc,page_from,page_to)
      SELECT doc, MIN({page_col}), MAX({page_col})
      FROM passages GROUP BY doc
    """)
else:
    # fallback single run covering whole book
    lo, hi = cur.execute(f"SELECT MIN({page_col}), MAX({page_col}) FROM passages").fetchone()
    cur.execute("INSERT INTO runs VALUES (?,?,?)", ("Bodhicaryavatara", int(lo or 1), int(hi or 1)))

con.commit()
print("runs rows:", cur.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
