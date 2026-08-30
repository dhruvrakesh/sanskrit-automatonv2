import sqlite3, sys
# Project the cost of an entity-extraction run from THIS project's own history,
# rather than from a guess. Read-only.
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
pending = int(sys.argv[2]) if len(sys.argv) > 2 else 6190
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)

print("=== what 'kind' values does usage_log record? ===")
for kind, n, usd in c.execute(
        "SELECT kind, COUNT(*), ROUND(SUM(cost_usd),4) FROM usage_log GROUP BY kind ORDER BY 3 DESC"):
    print(f"  {str(kind):22s} calls={n:<7} usd={usd}")

print("\n=== entity-extraction history (any kind containing 'entit') ===")
row = c.execute("""SELECT COUNT(*), ROUND(SUM(cost_usd),5), ROUND(AVG(cost_usd),6),
                          SUM(COALESCE(passages,0))
                   FROM usage_log WHERE kind LIKE '%entit%'""").fetchone()
calls, total, avg, psg = row
if calls:
    print(f"  calls={calls}  total=${total}  avg/call=${avg}  passages_covered={psg}")
    per_passage = (total / psg) if psg else None
    if per_passage:
        print(f"  observed cost per VERSE: ${per_passage:.6f}")
        print(f"\n  PROJECTION for {pending} pending verses: ${per_passage*pending:.4f}")
else:
    print("  no rows with kind like '%entit%' - extraction may log under another kind,")
    print("  or may not be logged at all (in which case its spend is INVISIBLE to the cap).")

print("\n=== today's spend so far ===")
for day, n, usd in c.execute("""SELECT substr(ts,1,10), COUNT(*), ROUND(SUM(cost_usd),4)
                                FROM usage_log GROUP BY substr(ts,1,10)
                                ORDER BY substr(ts,1,10) DESC LIMIT 3"""):
    print(f"  {day}: calls={n} usd={usd}")

cap, spent = c.execute("SELECT budget_usd, spent_usd FROM budget_state LIMIT 1").fetchone()
print(f"\n  cap=${cap:.2f} spent=${spent:.4f} headroom=${cap-spent:.4f}")
c.close()
