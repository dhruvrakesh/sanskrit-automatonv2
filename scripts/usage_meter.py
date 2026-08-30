#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
usage_meter.py - one honest place to record what an API call actually cost.
(2026-08-29)

WHY THIS EXISTS
---------------
Until today `usage_log` contained exactly one kind of row: 'translation'.
Vision OCR, entity extraction, embeddings and the Q4 judge all called paid
Gemini endpoints and recorded nothing. So `budget_state.spent_usd` was not
"what we have spent" - it was "what we have spent on translation", and the
budget cap could not stop the other four from running past it.

This module is deliberately tiny and defensive:

  * it NEVER raises. A metering failure must not kill a 4,000-page OCR run.
  * it prefers the provider's own token counts (Gemini puts them in
    `response.usage_metadata`) over the chars/4 approximation, and records
    which of the two was used in `usage_log.token_source`.
  * it opens its own short-lived SQLite connection when the caller has none,
    so a script with no DB handle (ocr_vision.py) can still report.

USAGE
-----
    from usage_meter import meter, usage_from_response

    resp = gm.generate_content(...)
    meter(kind="ocr_vision", doc="AphorismsOfSandilya",
          engine="gemini-vision:gemini-2.5-flash",
          resp=resp, units=1, duration_s=dt, db=db_path)

`units` is pages / verses / passages - whatever this call processed.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_warned = False
_lock = threading.Lock()

DEFAULT_DB = os.environ.get("SA_DB", "data/context.db")


def _warn_once(msg: str) -> None:
    global _warned
    if not _warned:
        _warned = True
        print(f"[usage_meter] metering disabled: {msg}", file=sys.stderr, flush=True)


def usage_from_response(resp) -> tuple[float | None, float | None]:
    """Pull (prompt_tokens, output_tokens) out of a Gemini response.

    Returns (None, None) when the SDK version does not expose usage_metadata,
    in which case the caller falls back to the chars/4 estimate. Vision calls
    are the important case: an image's token cost cannot be derived from
    characters at all, so without this the page cost was pure guesswork.
    """
    um = getattr(resp, "usage_metadata", None)
    if um is None:
        return None, None
    try:
        pin = getattr(um, "prompt_token_count", None)
        out = getattr(um, "candidates_token_count", None)
        # Thinking models bill reasoning tokens as output too; count them when present.
        think = getattr(um, "thoughts_token_count", None) or 0
        if pin is None and out is None:
            return None, None
        return float(pin or 0), float((out or 0) + (think or 0))
    except Exception:
        return None, None


def meter(
    kind: str,
    doc: str | None,
    engine: str,
    resp=None,
    in_chars: int = 0,
    out_chars: int = 0,
    units: int = 1,
    duration_s: float = 0.0,
    ok: bool = True,
    con: sqlite3.Connection | None = None,
    db: str | None = None,
) -> float:
    """Record one paid call. Returns the USD charged (0.0 if metering failed)."""
    try:
        import cost_tracker
    except Exception as exc:                       # pragma: no cover
        _warn_once(f"cannot import cost_tracker ({exc})")
        return 0.0

    in_tok = out_tok = None
    if resp is not None:
        in_tok, out_tok = usage_from_response(resp)

    own = False
    try:
        if con is None:
            path = db or DEFAULT_DB
            con = sqlite3.connect(path, timeout=30)
            con.execute("PRAGMA busy_timeout=30000")
            own = True
        with _lock:
            return cost_tracker.log_api_call(
                con, kind=kind, doc=doc or "", engine=engine,
                in_chars=in_chars, out_chars=out_chars,
                duration_s=duration_s, passages=units, ok=ok,
                in_tokens=in_tok, out_tokens=out_tok,
            )
    except Exception as exc:
        _warn_once(f"{type(exc).__name__}: {exc}")
        return 0.0
    finally:
        if own and con is not None:
            try:
                con.close()
            except Exception:
                pass


def budget_ok(con_or_db, next_cost: float = 0.0) -> bool:
    """True if the cap still allows work. Never raises; fails OPEN (returns
    True) if the check itself breaks, because a broken meter must not be able
    to halt the pipeline - it should only be able to warn."""
    try:
        import cost_tracker
        own = False
        con = con_or_db
        if isinstance(con_or_db, str):
            con = sqlite3.connect(con_or_db, timeout=30); own = True
        try:
            proceed, spent, cap = cost_tracker.check_budget(con, next_cost)
            if not proceed:
                print(f"[BUDGET] cap reached: spent ${spent:.4f} of ${cap:.2f}. "
                      f"Raise it with: python scripts/set_budget.py --cap <usd> --unpause",
                      flush=True)
            return proceed
        finally:
            if own:
                con.close()
    except Exception as exc:
        _warn_once(f"budget check failed ({exc}) - proceeding")
        return True
