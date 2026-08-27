import sqlite3, sys
# CANONICAL translation-quality metric is translation_qa (written by qa_scan.py).
# quality_score is a LEGACY inline heuristic that clusters ~0.5 and is NOT reliable —
# shown only for reference. Rank docs by the real metric. (corrected 2026-08-27)
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)
rows = c.execute("""
  SELECT d.code,
         COUNT(*)                                                              AS en,
         AVG(p.translation_qa)                                                 AS qa,
         SUM(CASE WHEN COALESCE(p.translation_qa,0) < 0.4 THEN 1 ELSE 0 END)   AS qa_lt40,
         SUM(CASE WHEN p.translation_qa>=0.4 AND p.translation_qa<0.6 THEN 1 ELSE 0 END) AS qa_40_60,
         AVG(p.quality_score)                                                  AS legacy,
         SUM(CASE WHEN p.translation_qa IS NULL THEN 1 ELSE 0 END)             AS unscored
  FROM docs d JOIN passages p ON p.doc_id = d.id
  WHERE TRIM(COALESCE(p.translation,'')) <> ''
  GROUP BY d.code
  ORDER BY AVG(p.translation_qa) IS NULL, AVG(p.translation_qa) ASC
""").fetchall()
print(f"{'doc (worst translation_qa first)':40s} {'en':>6} {'qa':>6} {'<0.4':>6} {'0.4-0.6':>8} {'legacy':>7} {'unscd':>6}")
print("-" * 90)
for code, en, qa, lt, mid, legacy, unsc in rows:
    qs  = f"{qa:.3f}"     if qa     is not None else "n/a"
    lg  = f"{legacy:.3f}" if legacy is not None else "n/a"
    print(f"{(code or '')[:40]:40s} {en:>6} {qs:>6} {lt:>6} {mid:>8} {lg:>7} {unsc:>6}")
c.close()
