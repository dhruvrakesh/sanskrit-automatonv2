#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_cost_v2.py - honest spend report. (2026-08-29)  READ-ONLY.

Answers three questions the old report could not:
  1. What have we spent, BY KIND (translation / ocr_vision / entities /
     embedding / judge)?  Before today only 'translation' existed.
  2. How much of that figure is MEASURED (provider token counts) and how much
     is a chars/4 GUESS?  A number you cannot separate this way is not an
     accounting, it is an assertion.
  3. Which kinds are still silent - i.e. work we know we ran but that has no
     rows at all?

  python scripts/diag_cost_v2.py [data/context.db]
"""
import sqlite3, sys

db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
cols = {r[1] for r in c.execute("PRAGMA table_info(usage_log)")}
has_src = "token_source" in cols

print("=" * 68)
print("SPEND BY KIND")
print("=" * 68)
rows = c.execute("""SELECT kind, COUNT(*), SUM(COALESCE(passages,0)),
                           ROUND(SUM(cost_usd),4)
                    FROM usage_log GROUP BY kind ORDER BY 4 DESC""").fetchall()
if not rows:
    print("  (usage_log is empty)")
tot = 0.0
for kind, n, units, usd in rows:
    tot += (usd or 0)
    per = (usd / units) if units else 0
    print(f"  {str(kind):14s} calls={n:<7} units={units or 0:<7} "
          f"${usd or 0:<9} (${per:.6f}/unit)")
print(f"  {'TOTAL':14s} ${tot:.4f}")

if has_src:
    print("\n" + "=" * 68)
    print("MEASURED vs ESTIMATED  (can we defend this number?)")
    print("=" * 68)
    for src, n, usd in c.execute(
            """SELECT COALESCE(token_source,'estimated'), COUNT(*), ROUND(SUM(cost_usd),4)
               FROM usage_log GROUP BY 1 ORDER BY 3 DESC"""):
        label = {"provider": "from provider token counts (exact)",
                 "estimated": "chars/4 approximation (indicative only)"}.get(src, src)
        share = (100.0 * (usd or 0) / tot) if tot else 0
        print(f"  {src:10s} calls={n:<7} ${usd or 0:<9} {share:5.1f}%   {label}")
else:
    print("\n  usage_log has no token_source column yet - every figure below is a")
    print("  chars/4 estimate. Deploy the patched cost_tracker.py to fix that.")

print("\n" + "=" * 68)
print("STILL SILENT  (paid work with no rows = invisible to the cap)")
print("=" * 68)
seen = {r[0] for r in c.execute("SELECT DISTINCT kind FROM usage_log")}
expected = {
    "translation": "translate_passages.py / translate_both.py",
    "ocr_vision":  "ocr_vision.py  (Gemini vision OCR)",
    "entities":    "extract_entities.py",
    "embedding":   "build_embeddings.py",
    "judge":       "judge_sample.py  (Phase Q4)",
}
missing = [k for k in expected if k not in seen]
for k in sorted(expected):
    mark = "OK    " if k in seen else "SILENT"
    print(f"  [{mark}] {k:12s} <- {expected[k]}")
if missing:
    print("\n  SILENT kinds have either never been run since metering was wired in,")
    print("  or are still unwired. If you have run one of them, it is unwired.")

print("\n" + "=" * 68)
print("BUDGET")
print("=" * 68)
try:
    cap, spent, paused = c.execute(
        "SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
    print(f"  cap      : ${cap:.2f}")
    print(f"  spent    : ${spent:.4f}  ({100*spent/cap if cap else 0:.1f}% of cap)")
    print(f"  headroom : ${cap-spent:.4f}")
    print(f"  paused   : {'YES - jobs blocked' if paused else 'no'}")
    drift = spent - tot
    if abs(drift) > 0.01:
        print(f"  NOTE: budget_state.spent_usd and SUM(usage_log.cost_usd) differ by "
              f"${drift:+.4f}. migrate_cache_costs() adds to spent_usd without writing "
              f"usage_log rows, which explains a positive drift.")
except Exception as e:
    print(f"  error: {e}")

print("\nThis is what the APP recorded. It is not a bill. Check it against the")
print("provider's console; if they disagree the pricing table in cost_tracker.py")
print("is stale and every figure here moves with it.")
c.close()
