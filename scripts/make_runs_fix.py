import sqlite3, os, time
db = os.path.join("data","context.db")
con = sqlite3.connect(db); cur=con.cursor()

def table_names():
    return {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")}

def cols(t):
    try: return [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
    except sqlite3.OperationalError: return []

# --- ensure correct schema -----------------------------------------------
exists = "runs" in table_names()
expected = ["doc","page_from","page_to"]
schema_bad = exists and cols("runs") != expected

if schema_bad:
    ts = time.strftime("%Y%m%d%H%M%S")
    cur.execute(f"ALTER TABLE runs RENAME TO runs_legacy_{ts}")

if (not exists) or schema_bad:
    cur.execute("CREATE TABLE runs(doc TEXT NOT NULL, page_from INTEGER NOT NULL, page_to INTEGER NOT NULL)")

cur.execute("DELETE FROM runs")  # start clean

# --- derive mappings ------------------------------------------------------
tables = table_names()
rows = []

if "passages" in tables:
    pcols = set(cols("passages"))
    if {"doc","page_no"}.issubset(pcols):
        # nice: passages has doc + page_no
        rows = list(cur.execute("SELECT doc, MIN(page_no), MAX(page_no) FROM passages GROUP BY doc"))
    elif "page_no" in pcols:
        # compat: only page_no, we’ll make one placeholder (edit later if needed)
        lo, hi = cur.execute("SELECT MIN(page_no), MAX(page_no) FROM passages").fetchone()
        rows = [("Bodhicaryavatara", int(lo or 1), int(hi or 1))]

if not rows and {"pages","docs"}.issubset(tables):
    # new schema: pages -> docs join
    q = """SELECT d.code, MIN(pg.page_no), MAX(pg.page_no)
           FROM pages pg JOIN docs d ON pg.doc_id=d.id
           GROUP BY d.code"""
    rows = list(cur.execute(q))

for doc, lo, hi in rows:
    cur.execute("INSERT INTO runs(doc,page_from,page_to) VALUES(?,?,?)", (str(doc), int(lo), int(hi)))

con.commit()

print("runs rows:", cur.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
for r in cur.execute("SELECT doc, page_from, page_to FROM runs ORDER BY doc, page_from"):
    print(r)
