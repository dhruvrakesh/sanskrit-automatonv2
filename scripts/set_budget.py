#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_budget.py - read or change the API spend cap in budget_state. (2026-08-29)

The cap is a real guard: cost_tracker pauses work when spent_usd reaches budget_usd.
Raising it should be a deliberate act, not a fragile shell one-liner (which is how the
last attempt broke on PowerShell quote escaping).

  python scripts/set_budget.py                 # show current cap / spend / headroom
  python scripts/set_budget.py --cap 25        # raise (or lower) the cap
  python scripts/set_budget.py --unpause       # clear a tripped pause flag
"""
from __future__ import annotations
import argparse, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def show(con):
    row = con.execute(
        "SELECT id, budget_usd, spent_usd, paused, updated_at FROM budget_state ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        print("budget_state is empty."); return None
    _id, cap, spent, paused, upd = row
    left = (cap or 0) - (spent or 0)
    pct = (100.0 * spent / cap) if cap else 0.0
    print(f"  cap      : ${cap:.2f}")
    print(f"  spent    : ${spent:.4f}   ({pct:.1f}% of cap)")
    print(f"  headroom : ${left:.4f}")
    print(f"  paused   : {'YES - jobs are blocked' if paused else 'no'}")
    print(f"  updated  : {upd}")
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--cap", type=float, default=None, help="new spend cap in USD")
    ap.add_argument("--unpause", action="store_true", help="clear the paused flag")
    args = ap.parse_args()

    con = sqlite3.connect(args.db, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    print("BEFORE:")
    row = show(con)
    if row is None:
        con.close(); return

    changed = False
    if args.cap is not None:
        con.execute("UPDATE budget_state SET budget_usd=?, updated_at=datetime('now') WHERE id=?",
                    (args.cap, row[0]))
        changed = True
    if args.unpause:
        con.execute("UPDATE budget_state SET paused=0, updated_at=datetime('now') WHERE id=?", (row[0],))
        changed = True

    if changed:
        con.commit()
        print("\nAFTER:")
        show(con)
    else:
        print("\n(no change requested; pass --cap and/or --unpause)")
    con.close()


if __name__ == "__main__":
    main()
