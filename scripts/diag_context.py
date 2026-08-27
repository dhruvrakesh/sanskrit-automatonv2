import sqlite3, os
# Read-only inventory of tables + key ops rows. (fixed: use cursor.description)
c = sqlite3.connect("file:data/context.db?mode=ro", uri=True)
tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("TABLES:", ", ".join(tabs))
print("Q4 mt_reviews table exists :", "mt_reviews" in tabs)
print("Q4 judge_sample.py exists  :", os.path.exists("scripts/judge_sample.py"))
for t in ("budget_state", "usage_totals", "sources"):
    if t in tabs:
        cur = c.execute(f"SELECT * FROM {t} LIMIT 3")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print(f"\n{t} ({len(rows)} row(s) shown): cols={cols}")
        for r in rows:
            print("   ", dict(zip(cols, r)))
c.close()
