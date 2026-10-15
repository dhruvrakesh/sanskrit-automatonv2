#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
claude_engine.py  (2026-10-15)  CLAUDE_ENGINE_2026_10_15

Claude (Anthropic's API) as an engine of the scholarly English, beside gemini-2.5-pro: one call, the text of its answer,
what it cost as Anthropic bills it, recorded in usage_log; and the credit it is paid from, counted apart from the spend
cap.

Why apart: the spend cap (budget_state; python scripts\\set_budget.py) is what Google bills. These calls are paid from
the API credit that came with the Max plan ($200, to 11 Nov 2026). They are recorded in usage_log (engine
"anthropic:<model>", the tokens as the API reports them, token_source "provider"), so the dashboard's spend and
spend_audit.py show them; they are not added to budget_state. Their own cap is the credit:
  CREDIT_USD      190 (the credit is $200: $10 is kept back for what is not metered here, such as a test by hand);
  CREDIT_SINCE    2026-10-15: the usage_log rows counted from;
  CREDIT_EXPIRES  2026-11-11: from this day nothing is sent (a call would then be paid for).
  .env may set SA_CLAUDE_CREDIT_USD, SA_CLAUDE_CREDIT_SINCE, SA_CLAUDE_CREDIT_EXPIRES. The Console's Billing page is the
  truth; this is the meter that stops a run before it.

The prices (platform.claude.com/docs/en/about-claude/pricing, read 2026-10-15), $ a million tokens:
  claude-opus-5-5     input 4.00   output 20.00   5-minute cache write 5.00    cache read 0.20
  claude-sonnet-5-5   input 2.00   output 10.00   5-minute cache write 2.50    cache read 0.10
  claude-haiku-5-5    input 0.10   output 0.50    5-minute cache write 0.125   cache read 0.01
                      (a prompt over 100,000 tokens: 0.50, 2.50, 0.625, 0.05)
  The Batch API: half of each. The thinking is billed as output, and usage.output_tokens counts it.
The requests (platform.claude.com/docs/en/build-with-claude/effort; the Sonnet 5.5 overview):
  - no temperature, top_p or top_k: Sonnet 5.5 refuses a value that is not its default, and none is sent to any;
  - the effort in output_config: low, medium, high, xhigh, max; unset, the model's own (high for Sonnet 5.5, medium
    for Opus 5.5 and Haiku 5.5). An engine names it after an "@": anthropic:claude-sonnet-5-5@medium;
  - max_tokens counts the thinking too; the answer is streamed (no time limit on a long one).
The key: ANTHROPIC_API_KEY in .env, read by the SDK from the environment; it is never printed.

  python scripts\\claude_engine.py --credit                         the credit: spent, left (free, read-only)
  python scripts\\claude_engine.py --probe                          one short call (claude-haiku-5-5, about $0.001)
  python scripts\\claude_engine.py --probe --model claude-sonnet-5-5 --effort medium
"""
from __future__ import annotations

import argparse
import datetime
import os
import sqlite3
import sys
import time
from pathlib import Path

MARK = "CLAUDE_ENGINE_2026_10_15"
PREFIX = "anthropic:"
# $ a million tokens: (input, output, 5-minute cache write, cache read)
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 5.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 0.10),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01),
}
LONG_PROMPT = {"claude-haiku-5-5": (100000, (0.50, 2.50, 0.625, 0.05))}
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EFFORT = {"claude-sonnet-5-5": "high", "claude-opus-5-5": "medium", "claude-haiku-5-5": "medium"}
CREDIT_USD = 190.0
CREDIT_SINCE = "2026-10-15"
CREDIT_EXPIRES = "2026-11-11"
MAX_RETRIES = 4          # the SDK's own: a rate limit, an overload, a server error, a dropped connection
TIMEOUT_S = 900.0

_warned = set()


def _warn_once(msg: str) -> None:
    if msg not in _warned:
        _warned.add(msg)
        print("[claude_engine] %s" % msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------------------------- names
def is_claude(engine) -> bool:
    return str(engine or "").startswith(PREFIX)


def parse_engine(engine: str) -> tuple:
    """'anthropic:claude-sonnet-5-5@medium' -> ('claude-sonnet-5-5', 'medium'); no '@': the model's own effort (None)."""
    e = str(engine or "")
    if e.startswith(PREFIX):
        e = e[len(PREFIX):]
    model, _, effort = e.partition("@")
    model, effort = model.strip(), (effort.strip().lower() or None)
    if effort is not None and effort not in EFFORTS:
        raise ValueError("effort %r is not one of %s" % (effort, ", ".join(EFFORTS)))
    return model, effort


def engine_name(model: str, effort=None) -> str:
    return PREFIX + model + ("@" + effort if effort else "")


def prices_of(model: str) -> tuple:
    """The model's prices; a model not in the table is priced as Opus 5.5 (the dearest), so the meter never says less
    than was spent."""
    if model in PRICES:
        return PRICES[model]
    for fam, key in (("haiku", "claude-haiku-5-5"), ("sonnet", "claude-sonnet-5-5"), ("opus", "claude-opus-5-5")):
        if fam in model:
            _warn_once("%s is not in the price table: priced as %s" % (model, key))
            return PRICES[key]
    _warn_once("%s is not in the price table: priced as claude-opus-5-5" % model)
    return PRICES["claude-opus-5-5"]


# --------------------------------------------------------------------------------------------- usage and price
def _get(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def tokens(usage) -> dict:
    """The usage the API reports (an SDK object or a dict, as the Batch API's results give it)."""
    det = _get(usage, "output_tokens_details")
    return {"input": int(_get(usage, "input_tokens") or 0),
            "cache_write": int(_get(usage, "cache_creation_input_tokens") or 0),
            "cache_read": int(_get(usage, "cache_read_input_tokens") or 0),
            "output": int(_get(usage, "output_tokens") or 0),
            "thinking": int(_get(det, "thinking_tokens") or 0)}


def price(model: str, usage, batch: bool = False) -> float:
    """$ of one answer: input, cache writes and reads, and the output with its thinking, at the model's prices."""
    t = tokens(usage)
    p = prices_of(model)
    if model in LONG_PROMPT and t["input"] + t["cache_write"] + t["cache_read"] > LONG_PROMPT[model][0]:
        p = LONG_PROMPT[model][1]
    cost = (t["input"] * p[0] + t["output"] * p[1] + t["cache_write"] * p[2] + t["cache_read"] * p[3]) / 1e6
    return cost * (0.5 if batch else 1.0)


def meter(con, kind: str, doc, model: str, usage, duration_s: float = 0.0, ok: bool = True, units: int = 1,
          batch: bool = False) -> float:
    """Record one answer in usage_log and usage_totals (not in budget_state: the credit pays for it). The $ it cost;
    the price still when the row cannot be written (for the run's own cap)."""
    cost = price(model, usage, batch)
    t = tokens(usage)
    engine = PREFIX + model
    if con is None:
        _warn_once("no database to record into: the calls are priced, not recorded")
        return cost
    try:
        import cost_tracker
        cost_tracker.ensure_usage_schema(con)
        con.execute("INSERT INTO usage_log(kind, doc, engine, in_chars, out_chars, in_tokens, out_tokens, cost_usd, "
                    "duration_s, passages, ok, token_source) VALUES (?,?,?,0,0,?,?,?,?,?,?,'provider')",
                    (kind, doc or "", engine, float(t["input"] + t["cache_write"] + t["cache_read"]), float(t["output"]),
                     cost, float(duration_s or 0.0), int(units or 0), 1 if ok else 0))
        con.execute("INSERT INTO usage_totals(engine, total_calls, total_in_chars, total_out_chars, total_cost_usd, "
                    "total_duration_s, total_passages) VALUES (?,1,0,0,?,?,?) ON CONFLICT(engine) DO UPDATE SET "
                    "total_calls = total_calls + 1, total_cost_usd = total_cost_usd + excluded.total_cost_usd, "
                    "total_duration_s = total_duration_s + excluded.total_duration_s, "
                    "total_passages = total_passages + excluded.total_passages, "
                    "last_updated = strftime('%Y-%m-%dT%H:%M:%fZ','now')",
                    (engine, cost, float(duration_s or 0.0), int(units or 0)))
        con.commit()
    except Exception as e:
        _warn_once("the meter could not write (%s: %s)" % (type(e).__name__, e))
    return cost


# --------------------------------------------------------------------------------------------- the credit
def settings() -> dict:
    def num(v, d):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d
    return {"cap": num(os.environ.get("SA_CLAUDE_CREDIT_USD"), CREDIT_USD),
            "since": (os.environ.get("SA_CLAUDE_CREDIT_SINCE") or CREDIT_SINCE).strip(),
            "expires": (os.environ.get("SA_CLAUDE_CREDIT_EXPIRES") or CREDIT_EXPIRES).strip()}


def credit(con, today=None) -> dict:
    """{cap, spent, left, since, expires, expired, calls}: the usage_log rows of engine anthropic:% from since."""
    s = settings()
    spent, calls = 0.0, 0
    try:
        have = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usage_log'").fetchone()
        if have:
            calls, spent = con.execute("SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE engine LIKE ? "
                                       "AND ts >= ?", (PREFIX + "%", s["since"])).fetchone()
    except sqlite3.Error as e:
        raise RuntimeError("the credit cannot be read (%s)" % e)
    day = (today or datetime.date.today()).isoformat()
    return dict(s, spent=float(spent or 0.0), calls=int(calls or 0), left=s["cap"] - float(spent or 0.0),
                expired=day >= s["expires"])


def credit_line(c: dict) -> str:
    return ("the Claude credit: $%.2f spent of $%.2f since %s (%d calls), $%.2f left; %s; the spend cap does not count it"
            % (c["spent"], c["cap"], c["since"], c["calls"], max(0.0, c["left"]),
               ("EXPIRED on %s: nothing is sent" % c["expires"]) if c["expired"] else "it expires on %s" % c["expires"]))


def budget_ok(con, next_cost: float = 0.0, today=None) -> bool:
    """True while the credit allows the next call. Fails closed: when the credit cannot be read, nothing is sent."""
    try:
        c = credit(con, today)
    except Exception as e:
        print("[CREDIT] the Claude credit cannot be read (%s): nothing is sent" % e, flush=True)
        return False
    if c["expired"]:
        print("[CREDIT] the Claude credit expired on %s: nothing is sent (SA_CLAUDE_CREDIT_EXPIRES in .env)"
              % c["expires"], flush=True)
        return False
    if c["spent"] + float(next_cost or 0.0) > c["cap"]:
        print("[CREDIT] the Claude credit's cap is reached: $%.4f spent of $%.2f (SA_CLAUDE_CREDIT_USD in .env)"
              % (c["spent"], c["cap"]), flush=True)
        return False
    return True


# --------------------------------------------------------------------------------------------- the calls
class Client:
    """One model, one effort. Built first: without the key or the SDK it raises, and nothing is called."""

    def __init__(self, model: str, effort=None, timeout: float = TIMEOUT_S, sdk=None):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set (.env)")
        if sdk is None:
            try:
                import anthropic as sdk
            except ImportError as e:
                raise RuntimeError("the anthropic SDK cannot be loaded (%s): python -m pip install anthropic" % e)
        if effort is not None and effort not in EFFORTS:
            raise RuntimeError("effort %r is not one of %s" % (effort, ", ".join(EFFORTS)))
        self.sdk, self.model, self.effort = sdk, model, effort
        self.client = sdk.Anthropic(max_retries=MAX_RETRIES, timeout=timeout)   # the key from the environment

    def request(self, system: str, user: str, max_tokens: int) -> dict:
        kw = {"model": self.model, "max_tokens": int(max_tokens), "system": system,
              "messages": [{"role": "user", "content": user}]}
        if self.effort:
            kw["output_config"] = {"effort": self.effort}
        return kw

    def create(self, system: str, user: str, max_tokens: int):
        """The final message, streamed. Raises what the SDK raises once its own retries are spent."""
        with self.client.messages.stream(**self.request(system, user, max_tokens)) as s:
            return s.get_final_message()


def text_of(msg) -> str:
    """The answer's text blocks, joined (the thinking blocks are left out)."""
    out = []
    for b in _get(msg, "content") or []:
        if _get(b, "type") == "text":
            out.append(_get(b, "text") or "")
    return "".join(out).strip()


def stop_of(msg) -> str:
    return str(_get(msg, "stop_reason") or "?")


# --------------------------------------------------------------------------------------------- by hand
PROBE_SYSTEM = "You translate Sanskrit into plain English. Reply with the translation only."
PROBE_USER = "\u0928\u093e\u0930\u093e\u092f\u0923\u0902 \u0928\u092e\u0938\u094d\u0915\u0943\u0924\u094d\u092f \u0928\u0930\u0902 \u091a\u0948\u0935 \u0928\u0930\u094b\u0924\u094d\u0924\u092e\u092e\u094d"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--credit", action="store_true", help="the credit: spent, left (free, read-only)")
    ap.add_argument("--probe", action="store_true", help="one short call, recorded (kind probe)")
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default=None, choices=EFFORTS)
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    if a.credit or not a.probe:
        con = sqlite3.connect(Path(a.db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            c = credit(con)
            rows = con.execute("SELECT engine, kind, COUNT(*), ROUND(SUM(cost_usd), 4) FROM usage_log WHERE engine LIKE ? "
                               "AND ts >= ? GROUP BY engine, kind ORDER BY 4 DESC", (PREFIX + "%", c["since"])).fetchall() \
                if con.execute("SELECT 1 FROM sqlite_master WHERE name='usage_log'").fetchone() else []
        finally:
            con.close()
        for r in rows:
            print("  %-32s %-10s %5d calls  $%s" % r)
        print("VERDICT: " + credit_line(c))
        print("NEXT: python scripts\\claude_engine.py --probe   (one short call, about $0.001)")
        return 0
    import db_utils
    con = db_utils.connect(a.db)
    try:
        if not budget_ok(con, 0.01):
            print("VERDICT: nothing sent"); print("NEXT: "); return 1
        try:
            cl = Client(a.model, a.effort)
        except RuntimeError as e:
            print("REFUSE: %s" % e); print("VERDICT: nothing sent"); print("NEXT: "); return 1
        t0 = time.time()
        try:
            msg = cl.create(PROBE_SYSTEM, PROBE_USER, 4096)
        except Exception as e:
            print("FAILED: %s: %s" % (type(e).__name__, str(e)[:300]))
            print("VERDICT: the API did not answer: see the error"); print("NEXT: "); return 1
        cost = meter(con, "probe", "", a.model, msg.usage, time.time() - t0)
        t = tokens(msg.usage)
        print("  %s (effort %s): %s" % (a.model, a.effort or "its own: %s" % DEFAULT_EFFORT.get(a.model, "?"), text_of(msg)))
        print("  stop %s; input %d, output %d (the thinking %d of it), cache %d/%d; %.1f s"
              % (stop_of(msg), t["input"], t["output"], t["thinking"], t["cache_write"], t["cache_read"], time.time() - t0))
        print("VERDICT: the API answers; $%.5f recorded in usage_log (kind probe); %s" % (cost, credit_line(credit(con))))
        print("NEXT: python scripts\\scholar_translate.py --doc HAYASHIRSHA_PANCARATRA --pages 20-21 --from-ref 20.5 "
              "--limit 10 --engine anthropic:claude-sonnet-5-5 --held-ok   (the dry run, free)")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
