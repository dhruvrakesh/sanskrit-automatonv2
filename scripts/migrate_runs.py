import sqlite3, os
db = os.path.join("data","context.db")
con = sqlite3.connect(db); c = con.cursor()

def cols(tbl):
    try: return {r[1] for r in c.execute(f"PRAGMA table_info({tbl})")}
    except: return set()

# If 'runs' is the old 3-col mapping table, rename it to doc_ranges
rc = cols("runs")
if rc and "doc" in rc and "id" not in rc:
    print("Renaming legacy runs(doc,page_from,page_to) -> doc_ranges …")
    c.execute("ALTER TABLE runs RENAME TO doc_ranges")
    c.execute("CREATE INDEX IF NOT EXISTS doc_ranges_doc_idx ON doc_ranges(doc)")
    con.commit()

# Ensure pipeline runs table exists (the one ingest_pdf.py expects)
rc = cols("runs")
if "id" not in rc:
    print("Creating pipeline runs table …")
    c.execute("""
      CREATE TABLE IF NOT EXISTS runs(
        id TEXT PRIMARY KEY,
        doc_id INTEGER,
        doc_code TEXT,
        src_hash TEXT,
        started_at TEXT,
        status TEXT,
        budget_usd REAL,
        spent_usd REAL,
        finished_at TEXT,
        error TEXT
      )
    """)
    con.commit()

# Show result
print("runs cols:", [r[1] for r in c.execute("PRAGMA table_info(runs)")])
if "doc_ranges" in {t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
    print("doc_ranges cols:", [r[1] for r in c.execute("PRAGMA table_info(doc_ranges)")])
con.close()
