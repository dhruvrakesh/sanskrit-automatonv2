#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
spend_audit.py  (2026-10-04)  SPEND_AUDIT_2026_10_04

READ-ONLY. "What has the API really cost, and can it run away?"

  1. usage_log by kind and engine: calls, units, tokens, RECORDED cost, and the cost
     REPRICED at the current price table (PRICE_NOW below, sources named), with the
     share of rows whose tokens came from the provider vs a chars/4 estimate.
     Estimated rows cannot be repriced exactly: they are shown, flagged, and a
     factor range is printed for translation (see diag_token_ratio.py to measure).
  2. budget_state: cap, recorded spend, paused.
  3. Last 7 days and last 24 hours by kind.
  4. Static check of the code: every script that calls a paid endpoint, whether it
     meters (usage_meter / cost_tracker) and whether it asks the budget first.

The only ground truth is Google Cloud Billing for the project that owns the key.
This script tells you how far the local ledger is from it, not what the bill is.

  python scripts\\spend_audit.py
  python scripts\\spend_audit.py --days 30 --csv exports\\spend_audit.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

MARK = "SPEND_AUDIT_2026_10_04"
SCRIPTS = Path(__file__).resolve().parent

# USD per 1M tokens (input, output). Sources as read on 2026-10-04.
PRICE_NOW = [
    # (substring of engine, (in, out), source)
    ("flash-lite-image", (0.25, 30.00), "ai.google.dev/gemini-api/docs/pricing (3.1 Flash Lite Image)"),
    ("3.1-flash-image", (0.50, 60.00), "ai.google.dev/gemini-api/docs/pricing (3.1 Flash Image)"),
    ("2.5-flash-image", (0.30, 30.00), "images.py IMAGE_PRICING (2025; not re-verified)"),
    ("2.5-flash", (0.30, 2.50), "pricepertoken.com 2026-10-02 / morphllm.com 2026-08-21"),
    ("2.5-pro", (1.25, 10.00), "cost_tracker table (not re-verified)"),
    ("embedding-001", (0.15, 0.00), "cost_tracker table (not re-verified)"),
]

PAID_CALL = re.compile(r"generate_content\(|embed_content\(|:generateContent|generativelanguage")
METERS = re.compile(r"usage_meter|log_api_call|log_translation_call|\bmeter\(")
GATES = re.compile(r"budget_ok|check_budget")


def price_now(engine: str):
    e = (engine or "").lower()
    for key, p, src in PRICE_NOW:
        if key in e:
            return p, src
    return None, None


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def ledger(con, since_days: int | None = None) -> list[dict]:
    cols = {r[1] for r in con.execute("PRAGMA table_info(usage_log)")}
    src = "COALESCE(token_source,'estimated')" if "token_source" in cols else "'estimated'"
    where = "WHERE ts >= strftime('%Y-%m-%dT%H:%M:%fZ','now', ?)" if since_days else ""
    params = ("-%d days" % since_days,) if since_days else ()
    agg = defaultdict(lambda: {"calls": 0, "units": 0, "in_tok": 0.0, "out_tok": 0.0, "recorded": 0.0,
                               "repriced": 0.0, "provider_rows": 0, "estimated_rows": 0, "unpriced": 0})
    for kind, eng, tin, tout, cost, n, tsrc in con.execute(
            f"""SELECT kind, engine, COALESCE(in_tokens,0), COALESCE(out_tokens,0), COALESCE(cost_usd,0),
                       COALESCE(passages,0), {src} FROM usage_log {where}""", params):
        a = agg[(kind or "?", eng or "?")]
        a["calls"] += 1; a["units"] += n or 0
        a["in_tok"] += tin; a["out_tok"] += tout; a["recorded"] += cost
        if tsrc == "provider":
            a["provider_rows"] += 1
        else:
            a["estimated_rows"] += 1
        p, _ = price_now(eng)
        if p is None:
            a["repriced"] += cost; a["unpriced"] += 1
        else:
            a["repriced"] += (tin * p[0] + tout * p[1]) / 1e6
    out = []
    for (kind, eng), a in sorted(agg.items(), key=lambda kv: -kv[1]["repriced"]):
        r = {"kind": kind, "engine": eng}
        r.update(a)
        r["per_unit"] = (r["repriced"] / r["units"]) if r["units"] else None
        out.append(r)
    return out


def budget(con) -> dict:
    try:
        r = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
        return {"budget_usd": r[0], "spent_usd": r[1], "paused": bool(r[2])} if r else {}
    except sqlite3.Error:
        return {}


def static_check(folder: Path) -> list[tuple]:
    rows = []
    for p in sorted(folder.glob("*.py")):
        if p.name.startswith(("patch_", "test_")) or ".bak" in p.name or p.name == Path(__file__).name:
            continue
        try:
            s = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not PAID_CALL.search(s):
            continue
        rows.append((p.name, bool(METERS.search(s)), bool(GATES.search(s))))
    return rows


def fmt(r: dict) -> str:
    pu = ("%.5f" % r["per_unit"]) if r["per_unit"] is not None else "-"
    est = r["estimated_rows"] * 100.0 / max(1, r["calls"])
    return "%-14s %-36s %7d %8d %9.4f %9.4f %9s %5.0f%%" % (
        r["kind"][:14], r["engine"][:36], r["calls"], r["units"], r["recorded"], r["repriced"], pu, est)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only API spend audit")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    con = open_ro(args.db)
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usage_log'").fetchone():
            print("No usage_log table: nothing has been metered."); return 0
        allrows, recent, day = ledger(con), ledger(con, args.days), ledger(con, 1)
        b = budget(con)
    finally:
        con.close()
    hdr = "%-14s %-36s %7s %8s %9s %9s %9s %6s" % ("kind", "engine", "calls", "units", "recorded$",
                                                   "repriced$", "$/unit", "est%")
    print("%s   prices: %s" % (MARK, "; ".join("%s %s/%s (%s)" % (k, p[0], p[1], s) for k, p, s in PRICE_NOW)))
    for title, rows in (("ALL TIME", allrows), ("LAST %d DAYS" % args.days, recent), ("LAST 24 HOURS", day)):
        print("\n== %s" % title); print(hdr); print("-" * len(hdr))
        for r in rows:
            print(fmt(r))
        tr = sum(r["recorded"] for r in rows); tp = sum(r["repriced"] for r in rows)
        print("%-59s %9.4f %9.4f" % ("TOTAL", tr, tp))
    tr_est = [r for r in allrows if r["kind"] == "translation" and r["estimated_rows"]]
    if tr_est:
        n = sum(r["estimated_rows"] for r in tr_est)
        print("\nNOTE: %d translation rows were metered from characters (chars/4), not provider tokens." % n)
        print("      Their repriced figure is still too LOW: Devanagari input tokenises denser than 4 chars/token")
        print("      and 2.5 Flash thinking tokens (billed as output) were never counted. Measure the input factor")
        print("      with: python scripts\\diag_token_ratio.py --sample 40   (count_tokens is not billed).")
    if b:
        print("\n== BUDGET  cap $%.2f   recorded spend $%.4f   paused=%s" % (b["budget_usd"], b["spent_usd"], b["paused"]))
        print("   The cap compares against RECORDED spend. Repriced all-time: $%.4f." % sum(r["repriced"] for r in allrows))
    print("\n== CODE: scripts that call a paid endpoint")
    print("%-28s %-8s %s" % ("script", "metered", "asks budget first"))
    for name, m, g in static_check(SCRIPTS):
        print("%-28s %-8s %s" % (name, "yes" if m else "NO", "yes" if g else "no"))
    print("\nOnly Google Cloud Billing is the bill. Set a budget alert and lower the API quota there for a hard cap.")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(allrows[0].keys()) if allrows else ["kind"])
            w.writeheader()
            for r in allrows:
                w.writerow(r)
        print("wrote", args.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
