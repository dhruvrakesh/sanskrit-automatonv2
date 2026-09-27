#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_empty_translations.py - ask the model again, and show what it said.
(TRANSLATION_FILTERS_2026_09_27)

For up to --n verses of one doc that are eligible, attempted (a later verse
of the doc is translated) and still EMPTY, this rebuilds exactly what
translate_passages sends - the same system prompt, context window, IAST aid
and, for Hindi, the English anchor - calls the model ONCE, and prints:

    the raw output,
    what the pre-2026-09-27 filters do with it   (frozen copy),
    what scripts/text_filters.py does with it NOW.

That turns "valid Sanskrit came back empty" into a per-verse cause:
refusal-filter false positive, echo-filter false positive, model [ILLEGIBLE],
safety / recitation block (infer_mt prints those), or nothing returned.

WRITES: nothing to passages, translations_l10n or mt_cache - the call runs
against an in-memory database, the way the dashboard's quick-translate does.
The ONE write is the spend, recorded through usage_meter.meter(kind=
'translate_probe') as RUNBOOK 5c requires of every paid call.
Cost: about $0.0002 a verse on gemini-2.5-flash. Refuses without --yes.

  python scripts/probe_empty_translations.py --db data/context.db --doc AphorismsOfSandilya --n 6
  python scripts/probe_empty_translations.py --db data/context.db --doc AphorismsOfSandilya --n 6 --yes
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

import text_filters as tf                                   # noqa: E402
from normalize_text import normalize_sanskrit               # noqa: E402
import translate_passages as tp                             # noqa: E402
from infer_mt import translate_batch                        # noqa: E402
from db_utils import ensure_schema, migrate_schema          # noqa: E402
import diag_empty_translations as dg                        # noqa: E402

LIVE = dg.LIVE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--lang", default="en", choices=["en", "hi"])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--engine", default=None)
    ap.add_argument("--min-quality", type=float, default=0.35)
    ap.add_argument("--yes", action="store_true", help="actually call the model (paid)")
    a = ap.parse_args()
    if a.n > 25:
        print("--n is capped at 25 for a probe."); return 2
    engine = a.engine or os.environ.get("MT_ENGINE") or "gemini:gemini-2.5-flash"

    ro = sqlite3.connect(a.db, timeout=60)
    ro.execute("PRAGMA busy_timeout=60000")
    ro.execute("PRAGMA query_only=ON")
    meta = ro.execute("SELECT id, category FROM docs WHERE code=?", (a.doc,)).fetchone()
    if not meta:
        print("doc %r not found" % a.doc); return 2
    did, category = meta
    cols = {r[1] for r in ro.execute("PRAGMA table_info(passages)")}
    pick = lambda c: ("p." + c) if c in cols else "NULL"
    if a.lang == "en":
        done = "TRIM(COALESCE(p.translation,''))<>''"
        empty = "TRIM(COALESCE(p.translation,''))=''"
    else:
        done = ("EXISTS (SELECT 1 FROM translations_l10n l WHERE l.passage_id=p.id "
                "AND l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>'')")
        empty = "NOT " + done
    last = ro.execute("SELECT MAX(p.page_no) FROM passages p WHERE p.doc_id=? AND %s" % done,
                      (did,)).fetchone()[0] or 0
    rows = ro.execute(
        "SELECT p.id, p.page_no, p.idx, p.text, COALESCE(p.quality_score,0), %s, %s, %s, %s, %s, "
        "COALESCE(p.translation,''), COALESCE(p.translation_qa,0) FROM passages p "
        "WHERE p.doc_id=? AND %s AND %s AND p.page_no<=? ORDER BY p.quality_score DESC, p.page_no"
        % (pick("verse_ref"), pick("chapter"), pick("chandas"), pick("text_type"), pick("iast"),
           LIVE, empty), (did, last)).fetchall()
    todo = []
    for r in rows:
        normed = normalize_sanskrit(r[3] or "")
        if not tf.should_translate(normed):
            continue
        if 0 < r[4] < a.min_quality:
            continue
        cleaned = tf.clean_for_mt(normed)
        if cleaned:
            todo.append((r, cleaned))
        if len(todo) >= a.n:
            break
    print("probe  doc=%s lang=%s engine=%s  attempted-but-empty candidates shown: %d"
          % (a.doc, a.lang, engine, len(todo)))
    try:
        b = ro.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
    except sqlite3.OperationalError:
        b = None
    if b:
        print("budget: cap $%.2f spent $%.4f paused=%s" % b)
    if not a.yes:
        for r, cleaned in todo:
            print("  id %-7s p%s.%s q=%.2f  %s" % (r[0], r[1], r[2], r[4], cleaned[:100].replace("\n", " / ")))
        print("\nno call made. Re-run with --yes to spend ~$%.4f." % (0.0002 * len(todo)))
        return 0
    if b and (b[2] or b[1] >= b[0]):
        print("REFUSED: the budget is capped or paused - the probe would only measure that.")
        return 3

    mem = sqlite3.connect(":memory:")
    ensure_schema(mem)
    try:
        migrate_schema(mem)
    except Exception:
        pass
    try:
        from usage_meter import meter
    except Exception:
        meter = None
    tally = {}
    for r, cleaned in todo:
        pid, page, idx, _t, qs, vref, chap, chan, ttype, iast, en, en_qa = r
        if a.lang == "hi":
            ctx = tp._fetch_context_l10n(ro, a.doc, "hi", page, idx, n=tp.CONTEXT_WINDOW)
            ref = en if (en.strip() and en_qa >= 0.6) else None
        else:
            ctx = tp._fetch_context(ro, a.doc, page, idx, n=tp.CONTEXT_WINDOW)
            ref = None
        print("\n--- id %s  p%s.%s  q=%.2f  ctx=%d" % (pid, page, idx, qs, len(ctx)))
        print("    SRC: %s" % cleaned[:300].replace("\n", " / "))
        t0 = time.time()
        try:
            outs = translate_batch(mem, [cleaned], engine=engine, src="sa", tgt=a.lang,
                                   iast_list=[iast or ""], context_list=[ctx] if ctx else None,
                                   reference_list=[ref] if a.lang == "hi" else None,
                                   doc_code=a.doc, category=category, chapters=[chap],
                                   verse_refs=[vref], chandas_list=[chan], text_types=[ttype])
        except Exception as e:
            print("    CALL FAILED: %s: %s" % (type(e).__name__, e)); tally["call-failed"] = tally.get("call-failed", 0) + 1
            continue
        dt = time.time() - t0
        raw = outs[0] if outs else ""
        if meter is not None:
            meter(kind="translate_probe", doc=a.doc, engine=engine,
                  in_chars=len(cleaned) + sum(len(c.get("translation") or "") for c in ctx),
                  out_chars=len(raw), units=1, duration_s=dt, db=a.db)
        ls = dg.legacy_salvage(raw, a.lang)
        le = a.lang == "en" and bool(ls) and dg.legacy_echo_en(ls)
        ns = tf.salvage_translation(raw, lang=a.lang)
        ne = bool(ns) and tf.is_source_echo(cleaned, ns, a.lang)
        old, new = dg.verdict(ls, le, raw or " "), dg.verdict(ns, ne, raw or " ")
        if not raw.strip():
            old = new = "model-empty"
        print("    RAW: %s" % (raw[:400].replace("\n", " / ") or "[nothing returned]"))
        print("    pre-patch filter: %-6s   current filter: %s" % (old, new))
        key = "%s -> %s" % (old, new)
        tally[key] = tally.get(key, 0) + 1
    print("\nSUMMARY (pre-patch -> current):")
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %3d  %s" % (v, k))
    print("keep = stored as is; cut = salvaged with [...]; empty/echo = stored empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
