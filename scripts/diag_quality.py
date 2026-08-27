import sqlite3, sys
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
rows = c.execute("""
  SELECT d.code,
         COUNT(*)                                                   AS en,
         AVG(p.quality_score)                                       AS avg_q,
         SUM(CASE WHEN COALESCE(p.quality_score,0) < 0.4 THEN 1 ELSE 0 END)                          AS below_0_4,
         SUM(CASE WHEN p.quality_score>=0.4 AND p.quality_score<0.6 THEN 1 ELSE 0 END)               AS mid,
         SUM(CASE WHEN p.quality_score IS NULL THEN 1 ELSE 0 END)                                    AS unscored
  FROM docs d JOIN passages p ON p.doc_id = d.id
  WHERE TRIM(COALESCE(p.translation,'')) <> ''
  GROUP BY d.code
  ORDER BY AVG(p.quality_score) IS NULL, AVG(p.quality_score) ASC
""").fetchall()
print(f"{'doc':40s} {'en':>6} {'avg_q':>7} {'<0.4':>6} {'0.4-0.6':>8} {'unscored':>9}")
print("-" * 82)
for code, en, avg_q, below, mid, unscored in rows:
    avg_s = f"{avg_q:.3f}" if avg_q is not None else "n/a"
    print(f"{(code or '')[:40]:40s} {en:>6} {avg_s:>7} {below:>6} {mid:>8} {unscored:>9}")
c.close()
