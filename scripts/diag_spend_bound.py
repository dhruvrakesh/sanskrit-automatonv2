#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_spend_bound.py - how wrong can our spend figure possibly be? (2026-08-29)

Makes NO API calls. Answers three questions with arithmetic alone:

  1. WHICH ENGINE actually ran?  Pricing differs 8-16x between flash and pro.
     If the ledger says flash but the calls were pro, every figure is 8-16x low.
  2. What is the CEILING on the chars/4 error?  Cost scales as 1/ratio, and no
     tokenizer emits fewer than ~1 token per character for Devanagari, so
     pricing at 1.0 chars/token is a hard upper bound.
  3. Over WHAT PERIOD, so it can be lined up against the provider's invoice.

Opened read-write-but-query-only rather than mode=ro on purpose: a read-only
URI cannot attach to the -wal/-shm of a database another process is writing,
and fails with a bare "disk I/O error".

  python scripts\\diag_spend_bound.py
"""
from __future__ import annotations
import sqlite3, sys

DB = sys.argv[1] if len(sys.argv) > 1 else "data/context.db"
PRICES = {                       # USD per 1M tokens
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro":   (1.25, 10.00),
    "gemini-2.0-flash": (0.075, 0.30),
    "gpt-4o":           (2.50, 10.00),
}

c = sqlite3.connect(DB, timeout=30)
c.execute("PRAGMA busy_timeout=30000")
c.execute("PRAGMA query_only=ON")

print("=" * 72)
print("1. WHICH ENGINES ACTUALLY RAN")
print("=" * 72)
rows = c.execute("""SELECT engine, kind, COUNT(*), SUM(in_chars), SUM(out_chars),
                           ROUND(SUM(cost_usd),4)
                    FROM usage_log GROUP BY engine, kind ORDER BY 6 DESC""").fetchall()
for eng, kind, n, ic, oc, usd in rows:
    print(f"  {str(eng):30s} {str(kind):12s} calls={n:<7} "
          f"in={ic or 0:<11} out={oc or 0:<10} ${usd}")
print("\n  If an engine above is NOT the one you believe you configured, stop and")
print("  check MT_ENGINE in .env - the pricing table keys off this string.")

print("\n" + "=" * 72)
print("2. CEILING ON THE chars/4 ERROR (cost scales as 1/ratio)")
print("=" * 72)
row = c.execute("""SELECT SUM(in_chars), SUM(out_chars), ROUND(SUM(cost_usd),4)
                   FROM usage_log WHERE kind='translation'""").fetchone()
ic, oc, logged = row[0] or 0, row[1] or 0, row[2] or 0
print(f"  translation in_chars : {ic:,}")
print(f"  translation out_chars: {oc:,}")
print(f"  recorded             : ${logged}\n")
print(f"  {'ratio':>7} | " + " | ".join(f"{k:>16s}" for k in PRICES))
print("  " + "-" * 68)
for ratio in (4.0, 2.0, 1.5, 1.0):
    cells = []
    for k, (pin, pout) in PRICES.items():
        cells.append(f"${pin*(ic/ratio)/1e6 + pout*(oc/ratio)/1e6:15.2f}")
    tag = "  <- as logged" if ratio == 4.0 else ""
    print(f"  {ratio:>7.1f} | " + " | ".join(cells) + tag)
print("\n  Read DOWN your actual engine's column. The 1.0 row is the hard ceiling:")
print("  the true cost cannot be above it, whatever the tokenizer does.")

print("\n" + "=" * 72)
print("3. PERIOD TO RECONCILE AGAINST THE INVOICE")
print("=" * 72)
for day, n, usd in c.execute("""SELECT substr(ts,1,10), COUNT(*), ROUND(SUM(cost_usd),4)
                                FROM usage_log GROUP BY 1 ORDER BY 1"""):
    print(f"  {day}: calls={n:<7} ${usd}")
try:
    n = c.execute("SELECT COUNT(*) FROM mt_cache").fetchone()[0]
    print(f"\n  mt_cache entries (re-served with NO API call): {n:,}")
except Exception:
    pass

print("\n" + "=" * 72)
print("GROUND TRUTH IS NOT IN THIS DATABASE.")
print("=" * 72)
print("  Everything above is what the app COMPUTED from its own pricing table.")
print("  The only authority is the provider console:")
print("    Gemini via AI Studio key -> https://aistudio.google.com  (Usage / Billing)")
print("    Gemini via Google Cloud  -> Cloud Console > Billing > Reports,")
print("                                filter service = 'Generative Language API'")
print("    OpenAI                   -> https://platform.openai.com/usage")
print("  If the console total is far above the ceiling in section 2, the spend is")
print("  NOT coming from this application and you should look for another consumer")
print("  of the same API key before changing anything here.")
c.close()
