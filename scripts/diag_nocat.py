import sqlite3
c=sqlite3.connect("file:data/context.db?mode=ro",uri=True)
cur=c.execute("SELECT code FROM docs WHERE category IS NULL OR TRIM(COALESCE(category,''))='' ORDER BY code")
rows=[r[0] for r in cur.fetchall()]
print(f"{len(rows)} docs with NO category (would fall under 'other' in the reader):")
for code in rows: print("  ", code)
print("\nExisting categories in use:")
for cat,n in c.execute("SELECT COALESCE(category,'(none)'), COUNT(*) FROM docs GROUP BY category ORDER BY 2 DESC"):
    print(f"  {cat}: {n}")
c.close()
