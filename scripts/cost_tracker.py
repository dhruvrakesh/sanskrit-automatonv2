#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cost_tracker.py — Real-time cost tracking, budget enforcement, and rate limiting
for Sanskrit Automaton v2.

Tracks:
  - Per-call token estimates (src chars / 4 ≈ tokens)
  - Cumulative USD cost per engine
  - Budget ceiling with auto-pause
  - OCR compute time
  - Translation throughput (passages/hour)
  - Writes to usage_log table in SQLite

Pricing (as of June 2026):
  Gemini 2.5 Pro:   $1.25/M in  | $10.00/M out  (>200k tokens: $2.50/$15.00)
  Gemini 2.0 Flash: $0.075/M in | $0.30/M out
  GPT-4o-mini:      $0.15/M in  | $0.60/M out
  GPT-4o:           $2.50/M in  | $10.00/M out
"""
from __future__ import annotations
import sqlite3, time, os, threading
from typing import Optional

# ── Pricing table (USD per 1M tokens) ────────────────────────────────────────
_PRICING: dict[str, tuple[float, float]] = {
    "gemini:gemini-2.5-pro":      (1.25,  10.00),
    "gemini:gemini-2.5-flash":    (0.15,   0.60),
    "gemini:gemini-2.0-flash":    (0.075,  0.30),
    "gemini:gemini-1.5-pro":      (1.25,   5.00),
    "openai:gpt-4o-mini":         (0.15,   0.60),
    "openai:gpt-4o":              (2.50,  10.00),
    "openai:gpt-4o-mini-2024-07-18": (0.15, 0.60),
}
_CHARS_PER_TOKEN = 4.0  # approximate for Sanskrit/English mixed content

_lock = threading.Lock()


def _get_pricing(engine: str) -> tuple[float, float]:
    """Return (in_price_per_M, out_price_per_M) for an engine."""
    for k, v in _PRICING.items():
        if k in engine or engine in k:
            return v
    # Default: assume Gemini 2.5 Flash (the project default engine)
    return (0.15, 0.60)


def chars_to_tokens(chars: int) -> float:
    return chars / _CHARS_PER_TOKEN


def estimate_cost_usd(
    engine: str,
    in_chars: int,
    out_chars: int,
) -> float:
    """Estimate USD cost for one API call."""
    in_price, out_price = _get_pricing(engine)
    in_tokens  = chars_to_tokens(in_chars)  / 1_000_000
    out_tokens = chars_to_tokens(out_chars) / 1_000_000
    return in_price * in_tokens + out_price * out_tokens


def ensure_usage_schema(con: sqlite3.Connection):
    """Create usage_log and usage_totals tables if they don't exist."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            kind         TEXT NOT NULL,       -- 'translation' | 'ocr' | 'ingest'
            doc          TEXT,
            engine       TEXT,
            in_chars     INTEGER DEFAULT 0,
            out_chars    INTEGER DEFAULT 0,
            in_tokens    REAL    DEFAULT 0,
            out_tokens   REAL    DEFAULT 0,
            cost_usd     REAL    DEFAULT 0,
            duration_s   REAL    DEFAULT 0,
            passages     INTEGER DEFAULT 0,   -- passages processed in this call
            ok           INTEGER DEFAULT 1    -- 1=success, 0=failure/refusal
        );

        CREATE TABLE IF NOT EXISTS usage_totals (
            engine       TEXT PRIMARY KEY,
            total_calls  INTEGER DEFAULT 0,
            total_in_chars  INTEGER DEFAULT 0,
            total_out_chars INTEGER DEFAULT 0,
            total_cost_usd  REAL    DEFAULT 0,
            total_duration_s REAL   DEFAULT 0,
            total_passages  INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS budget_state (
            id           INTEGER PRIMARY KEY CHECK (id=1),
            budget_usd   REAL    DEFAULT 8.0,
            spent_usd    REAL    DEFAULT 0.0,
            paused       INTEGER DEFAULT 0,   -- 1 = auto-paused by budget
            updated_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        INSERT OR IGNORE INTO budget_state(id, budget_usd, spent_usd)
        VALUES (1, 8.0, 0.0);
    """)
    con.commit()


def log_translation_call(
    con: sqlite3.Connection,
    doc: str,
    engine: str,
    in_chars: int,
    out_chars: int,
    duration_s: float,
    passages: int = 1,
    ok: bool = True,
) -> float:
    """Log one translation API call. Returns cost_usd for this call."""
    cost = estimate_cost_usd(engine, in_chars, out_chars)
    in_tok  = chars_to_tokens(in_chars)
    out_tok = chars_to_tokens(out_chars)

    with _lock:
        ensure_usage_schema(con)
        con.execute("""
            INSERT INTO usage_log(kind, doc, engine, in_chars, out_chars,
                                  in_tokens, out_tokens, cost_usd, duration_s, passages, ok)
            VALUES('translation',?,?,?,?, ?,?,?,?,?,?)
        """, (doc, engine, in_chars, out_chars, in_tok, out_tok, cost, duration_s, passages, 1 if ok else 0))

        # Update running totals
        con.execute("""
            INSERT INTO usage_totals(engine, total_calls, total_in_chars, total_out_chars,
                                     total_cost_usd, total_duration_s, total_passages)
            VALUES(?,1,?,?,?,?,?)
            ON CONFLICT(engine) DO UPDATE SET
                total_calls     = total_calls + 1,
                total_in_chars  = total_in_chars  + excluded.total_in_chars,
                total_out_chars = total_out_chars + excluded.total_out_chars,
                total_cost_usd  = total_cost_usd  + excluded.total_cost_usd,
                total_duration_s= total_duration_s + excluded.total_duration_s,
                total_passages  = total_passages  + excluded.total_passages,
                last_updated    = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """, (engine, in_chars, out_chars, cost, duration_s, passages))

        # Update cumulative spend in budget_state
        con.execute("""
            UPDATE budget_state SET
                spent_usd  = spent_usd + ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE id=1
        """, (cost,))

        con.commit()
    return cost


def log_ocr_call(
    con: sqlite3.Connection,
    doc: str,
    duration_s: float,
    pages: int = 1,
    ok: bool = True,
):
    """Log one OCR call (no API cost, just compute time)."""
    with _lock:
        ensure_usage_schema(con)
        con.execute("""
            INSERT INTO usage_log(kind, doc, engine, duration_s, passages, ok)
            VALUES('ocr',?,'tesseract',?,?,?)
        """, (doc, duration_s, pages, 1 if ok else 0))
        con.execute("""
            INSERT INTO usage_totals(engine, total_calls, total_duration_s, total_passages)
            VALUES('tesseract',1,?,?)
            ON CONFLICT(engine) DO UPDATE SET
                total_calls      = total_calls + 1,
                total_duration_s = total_duration_s + excluded.total_duration_s,
                total_passages   = total_passages   + excluded.total_passages,
                last_updated     = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """, (duration_s, pages))
        con.commit()


def check_budget(
    con: sqlite3.Connection,
    next_call_cost_estimate: float = 0.0,
) -> tuple[bool, float, float]:
    """Check if budget allows another call.
    
    Returns (can_proceed, spent_usd, budget_usd).
    If would_exceed is True, logs a pause event.
    """
    ensure_usage_schema(con)
    row = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
    if not row:
        return True, 0.0, 8.0
    budget, spent, paused = row
    if paused:
        return False, spent, budget
    if spent + next_call_cost_estimate > budget:
        # Auto-pause
        con.execute("""
            UPDATE budget_state SET paused=1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE id=1
        """)
        con.commit()
        print(f"[BUDGET] PAUSED — spent ${spent:.4f} of ${budget:.2f} budget. "
              f"Next call would cost ~${next_call_cost_estimate:.4f}.")
        return False, spent, budget
    return True, spent, budget


def set_budget(con: sqlite3.Connection, budget_usd: float):
    """Set the total budget ceiling."""
    ensure_usage_schema(con)
    con.execute("UPDATE budget_state SET budget_usd=?, paused=0 WHERE id=1", (budget_usd,))
    con.commit()
    print(f"[BUDGET] Set to ${budget_usd:.2f}")


def resume_budget(con: sqlite3.Connection):
    """Resume a paused budget."""
    ensure_usage_schema(con)
    con.execute("UPDATE budget_state SET paused=0 WHERE id=1")
    con.commit()


def get_summary(con: sqlite3.Connection) -> dict:
    """Return a summary dict for the dashboard /api/usage endpoint."""
    ensure_usage_schema(con)
    row = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
    budget = {"budget_usd": 8.0, "spent_usd": 0.0, "paused": False}
    if row:
        budget = {"budget_usd": row[0], "spent_usd": round(row[1], 6), "paused": bool(row[2])}

    totals = {}
    for r in con.execute("SELECT * FROM usage_totals ORDER BY total_cost_usd DESC"):
        eng = r[0]
        totals[eng] = {
            "calls":       r[1],
            "in_chars":    r[2],
            "out_chars":   r[3],
            "cost_usd":    round(r[4], 6),
            "duration_s":  round(r[5], 1),
            "passages":    r[6],
            "passages_per_hour": round(r[6] / max(1, r[5]) * 3600, 1) if r[5] else 0,
        }

    # Recent calls
    recent = []
    for r in con.execute("""
        SELECT ts, kind, doc, engine, cost_usd, duration_s, passages, ok
        FROM usage_log ORDER BY id DESC LIMIT 20
    """):
        recent.append({
            "ts": r[0], "kind": r[1], "doc": r[2], "engine": r[3],
            "cost_usd": round(r[4] or 0, 6), "duration_s": round(r[5] or 0, 1),
            "passages": r[6], "ok": bool(r[7]),
        })

    return {
        "budget": budget,
        "by_engine": totals,
        "recent": recent,
    }


def migrate_cache_costs(con: sqlite3.Connection):
    """One-time: backfill usage_totals from existing mt_cache entries (no duration data)."""
    ensure_usage_schema(con)
    rows = con.execute(
        "SELECT engine, COUNT(*), SUM(LENGTH(text)), SUM(LENGTH(output)) FROM mt_cache GROUP BY engine"
    ).fetchall()
    for engine, count, in_chars, out_chars in rows:
        cost = estimate_cost_usd(engine, in_chars or 0, out_chars or 0)
        con.execute("""
            INSERT INTO usage_totals(engine, total_calls, total_in_chars, total_out_chars,
                                     total_cost_usd, total_passages)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(engine) DO UPDATE SET
                total_calls     = total_calls     + excluded.total_calls,
                total_in_chars  = total_in_chars  + excluded.total_in_chars,
                total_out_chars = total_out_chars + excluded.total_out_chars,
                total_cost_usd  = total_cost_usd  + excluded.total_cost_usd,
                total_passages  = total_passages  + excluded.total_passages,
                last_updated    = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """, (engine, count, in_chars or 0, out_chars or 0, cost, count))
        con.execute("""
            UPDATE budget_state SET spent_usd = spent_usd + ? WHERE id=1
        """, (cost,))
    con.commit()
    print(f"[MIGRATE] Backfilled costs from {sum(r[1] for r in rows)} cached translations")


if __name__ == "__main__":
    con = sqlite3.connect("data/context.db")
    ensure_usage_schema(con)
    migrate_cache_costs(con)
    summary = get_summary(con)
    import json
    print(json.dumps(summary, indent=2))
