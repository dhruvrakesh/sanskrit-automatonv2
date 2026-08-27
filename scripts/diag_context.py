import sqlite3, os
c = sqlite3.connect("file:data/context.db?mode=ro", uri=True)
tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("TABLES:", ", ".join(tabs))
print("Q4 mt_reviews table exists :", "mt_reviews" in tabs)
print("Q4 judge_sample.py exists  :", os.path.exists("scripts/judge_sample.py"))
for t in ("budget_state","usage_totals"):
    if t in tabs:
        row = c.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
        print(f"{t}:", dict(zip([d[0] for d in c.description], row)) if row else "(empty)")
c.close()
