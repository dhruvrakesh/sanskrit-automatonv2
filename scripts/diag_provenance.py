#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_provenance.py — decide WHY translations score mid-tier, from the data itself,
so we pick the right lever (re-translate vs re-OCR vs re-source) instead of guessing.
Read-only. (2026-08-27)

Three tests:
  A. quality by ENGINE + PROMPT VERSION  -> is low score tied to OLD models/prompts?
  B. quality by translation MONTH        -> were the weak verses done in EARLIER efforts?
  C. SOURCE Devanagari purity per doc     -> is the Sanskrit OCR itself noisy (re-OCR)?
"""
from __future__ import annotations
import sqlite3, sys
from collections import defaultdict

db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=60)


def dev_ratio(s: str) -> float:
    dev = lat = 0
    for ch in s or "":
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            dev += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            lat += 1
    t = dev + lat
    return dev / t if t else 0.0


print("=== A. Translation quality by ENGINE + PROMPT VERSION (tests 'old models' hypothesis) ===")
try:
    rows = c.execute("""
      SELECT COALESCE(engine,'(none)')             AS e,
             COALESCE(mt_prompt_version,'(none)')  AS pv,
             COUNT(*)                              AS n,
             ROUND(AVG(quality_score),3)           AS avg_q,
             SUM(CASE WHEN COALESCE(quality_score,0) < 0.6 THEN 1 ELSE 0 END) AS below_0_6
      FROM passages WHERE TRIM(COALESCE(translation,'')) <> ''
      GROUP BY e, pv ORDER BY avg_q
    """).fetchall()
    print(f"{'engine':28s} {'prompt':12s} {'n':>7} {'avg_q':>7} {'<0.6':>7}")
    for e, pv, n, avg, b in rows:
        print(f"{e[:28]:28s} {str(pv)[:12]:12s} {n:>7} {str(avg):>7} {b:>7}")
except Exception as ex:
    print("  (columns missing?)", ex)

print("\n=== B. Quality by translation MONTH (tests 'earlier efforts' hypothesis) ===")
try:
    rows = c.execute("""
      SELECT substr(translated_at,1,7) AS ym, COUNT(*) AS n, ROUND(AVG(quality_score),3) AS avg_q
      FROM passages
      WHERE TRIM(COALESCE(translation,'')) <> '' AND translated_at IS NOT NULL
      GROUP BY ym ORDER BY ym
    """).fetchall()
    for ym, n, avg in rows:
        print(f"  {ym or '(null)'}: n={n:>7}  avg_q={avg}")
    nnull = c.execute("SELECT COUNT(*) FROM passages WHERE TRIM(COALESCE(translation,''))<>'' AND translated_at IS NULL").fetchone()[0]
    if nnull:
        print(f"  (null translated_at): n={nnull}  <- untracked/earliest imports")
except Exception as ex:
    print("  (columns missing?)", ex)

print("\n=== C. SOURCE (Sanskrit) cleanliness per doc (tests 'bad OCR' hypothesis) ===")
rows = c.execute("""
  SELECT d.code, p.text FROM docs d JOIN passages p ON p.doc_id = d.id
  WHERE TRIM(COALESCE(p.text,'')) <> ''
""").fetchall()
agg = defaultdict(lambda: [0.0, 0])
for code, text in rows:
    agg[code][0] += dev_ratio(text)
    agg[code][1] += 1
out = sorted(((code, s / n, n) for code, (s, n) in agg.items()), key=lambda x: x[1])
print(f"{'doc (worst source first)':40s} {'src_devanagari':>14} {'n':>7}")
for code, r, n in out[:20]:
    print(f"{(code or '')[:40]:40s} {r:>14.2f} {n:>7}")
print("\nRead it: src_devanagari < ~0.85 => noisy Sanskrit OCR => re-OCR/re-source helps.")
print("          src_devanagari >= ~0.9 => OCR is clean => low score is TRANSLATION, re-translate.")
c.close()
