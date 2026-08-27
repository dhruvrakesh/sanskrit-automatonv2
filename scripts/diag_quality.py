import sqlite3, sys
c = sqlite3.connect("file:data/context.db?mode=ro", uri=True, timeout=60)
rows = c.execute("""
  SELECT d.code,
         COUNT(*)                                                   AS en,
         ROUND(AVG(p.quality_score),3)                              AS avg_q,
         SUM(CASE WHEN p.quality_score < 0.4 THEN 1 ELSE 0 END)     AS below_0_4,
         SUM(CASE WHEN p.quality_score>=0.4 AND p.quality_score<0.6 THEN 1 ELSE 0 END) AS mid
  FROM docs d JOIN passages p ON p.doc_id = d.id
  WHERE TRIM(COALESCE(p.translation,'')) <> ''
  GROUP BY d.code
  ORDER BY avg_q ASC
""").fetchall()
print(f"{'doc':40s} {'en':>6} {'avg_q':>6} {'<0.4':>6} {'0.4-0.6':>8}")
for r in rows:
    print(f"{(r[0] or '')[:40]:40s} {r[1]:>6} {r[2]:>6} {r[3]:>6} {r[4]:>8}")
c.close()
