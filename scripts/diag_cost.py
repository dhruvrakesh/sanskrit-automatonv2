import sqlite3, sys
# ACTUAL spend from the project's own tracker (usage_log / usage_totals / budget_state).
# Read-only. Schema-introspective: adapts to whatever columns cost_tracker.py created.
db = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
tabs = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def cols(t):
    return [r[1] for r in c.execute(f"PRAGMA table_info({t})")]

def show(title, sql, params=()):
    try:
        cur = c.execute(sql, params)
        names = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print(f"\n--- {title} ---")
        if not rows:
            print("  (no rows)"); return
        print("  " + " | ".join(names))
        for r in rows:
            print("  " + " | ".join("" if v is None else str(v) for v in r))
    except Exception as e:
        print(f"\n--- {title} ---\n  error: {e}")

print("tables present:", ", ".join(sorted(t for t in tabs if t in
      ("usage_log", "usage_totals", "budget_state", "mt_cache"))))
for t in ("usage_log", "usage_totals", "budget_state"):
    if t in tabs:
        print(f"  {t} columns: {cols(t)}")

if "budget_state" in tabs:
    show("BUDGET STATE (cap vs spent)", "SELECT * FROM budget_state")

if "usage_totals" in tabs:
    show("USAGE TOTALS (lifetime, by whatever key it tracks)", "SELECT * FROM usage_totals")

if "usage_log" in tabs:
    lc = cols("usage_log")
    # Find plausible column names without assuming
    cost_c = next((x for x in lc if "cost" in x.lower()), None)
    ts_c   = next((x for x in lc if x.lower() in ("created_at","ts","timestamp","at")), None)
    eng_c  = next((x for x in lc if "engine" in x.lower() or "model" in x.lower()), None)
    doc_c  = next((x for x in lc if x.lower() in ("doc","doc_code","code")), None)
    tin_c  = next((x for x in lc if "in" in x.lower() and "tok" in x.lower()), None)
    tout_c = next((x for x in lc if "out" in x.lower() and "tok" in x.lower()), None)
    print(f"\n  detected -> cost={cost_c} time={ts_c} engine={eng_c} doc={doc_c} "
          f"tok_in={tin_c} tok_out={tout_c}")
    n = c.execute("SELECT COUNT(*) FROM usage_log").fetchone()[0]
    print(f"  usage_log rows: {n}")
    if cost_c:
        show("TOTAL SPEND (all time)", f"SELECT ROUND(SUM({cost_c}),4) AS total_usd FROM usage_log")
        if ts_c:
            show("SPEND BY DAY (last 14)",
                 f"SELECT substr({ts_c},1,10) AS day, COUNT(*) AS calls, "
                 f"ROUND(SUM({cost_c}),4) AS usd FROM usage_log GROUP BY day ORDER BY day DESC LIMIT 14")
        if eng_c:
            show("SPEND BY ENGINE",
                 f"SELECT {eng_c} AS engine, COUNT(*) AS calls, ROUND(SUM({cost_c}),4) AS usd "
                 f"FROM usage_log GROUP BY {eng_c} ORDER BY usd DESC")
        if doc_c:
            show("SPEND BY DOC (top 15)",
                 f"SELECT {doc_c} AS doc, COUNT(*) AS calls, ROUND(SUM({cost_c}),4) AS usd "
                 f"FROM usage_log GROUP BY {doc_c} ORDER BY usd DESC LIMIT 15")
        if tin_c and tout_c:
            show("TOKENS (all time)",
                 f"SELECT SUM({tin_c}) AS tokens_in, SUM({tout_c}) AS tokens_out, "
                 f"ROUND(SUM({cost_c}),4) AS usd FROM usage_log")

print("\nNOTE: this is what the app RECORDED. Compare it against the provider's own billing")
print("page - if they disagree, the tracker is under-counting (likely: image/vision input")
print("tokens, or context tokens not being logged) and its per-call figures cannot be trusted.")
c.close()
