#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_meter_gates_2026_10_04.py  (2026-10-04)  METER_GATES_2026_10_04

The second half of "is API spend leak-proof?", and two false alarms.

1. corpus_status.py printed vision estimates and --max-usd caps at $0.0015/page.
   After SPEND_TRUTH, ocr_consensus measures the cost from usage_log at today's
   prices (about $0.0054/page repriced on 2026-10-04). So corpus_status was
   proposing a --max-usd that ocr_consensus would REFUSE, and its totals read
   about 3.6x low. Now:
     - it uses the same ocr_consensus.measured_cost_per_page() with 15% headroom
       in the cap (the median moves a little between the two runs);
     - the fallback is $0.0054 when fewer than 5 measured pages exist;
     - translation $/passage is repriced at today's prices, preferring the
       provider-metered rows (which include thinking tokens) once 200 or more
       passages of them exist.
   The header now says which source each figure came from.
2. images.py printed "~$0.078 each (about 1,300 output tokens)" at every size.
   Google's pricing page (read 2026-10-04) gives 3.1 Flash Image per image at
   1K $0.067, 2K $0.101 and 4K $0.151, which is 1,120 / 1,680 / 2,520 image
   tokens at $60/M. usage_log shows the provider reporting about 400 more output
   tokens per image (1,482-1,551 at 1K, 2,080 at 2K), all priced by the ledger
   at $60/M. The estimate now follows SA_IMAGE_SIZE and adds that overhead:
   1K ~$0.091, 2K ~$0.125, 4K ~$0.175. (The ledger meters the provider's own
   counts; if Google bills those extra tokens at a lower text rate, the ledger
   reads HIGH, which is the safe direction.)
3. retire_doc.py's post-check is corpus-wide, so pre-existing orphans read as
   this retirement's fault. The 157 orphaned mentions it reported for manu on
   2026-10-04 were already in STATUS_20261004_1304.md, before that retirement.
   It now counts orphans before and after, warns and exits 1 only on an
   INCREASE, and points pre-existing ones to fix_orphans.py.
4. Paid calls that did not ask the budget (or were not metered):
     dashboard.py  Ask: the answer call and the query embedding are now metered
                   (kind 'ask' / 'ask_embed'); the answer call asks the budget
                   first and returns HTTP 402 with the retrieved sources when
                   the cap is reached.
     extract_entities.py  asks the budget before every batch and stops cleanly
                   (resumable, as on any other stop).
     judge_sample.py, ab_source_quality.py, diag_hindi_ab.py  ask the budget
                   once, after --yes.
     diag_hindi_ab.py  logs the provider's token counts (kind 'ab_test') when
                   infer_mt collected them. Before, it logged chars/4 as
                   kind 'translation', which also skewed translation $/passage.

All-or-nothing, marker-idempotent, backups (.bak_meter_<date>), py_compile,
atomic replace.

  python scripts/patch_meter_gates_2026_10_04.py --check
  python scripts/patch_meter_gates_2026_10_04.py
Test: python -m unittest tests.test_meter_gates_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "METER_GATES_2026_10_04"

# --------------------------------------------------------------------------- corpus_status
CS_EDITS = [
    ("vision fallback",
     "VISION_COST_PER_PAGE = 0.0015\n",
     "# METER_GATES_2026_10_04: fallback only, used when usage_log has fewer than 5 measured pages.\n"
     "# Was 0.0015 (the old 2.5 Flash price). Repriced median, ocr_vision, 24 h to 2026-10-04: ~$0.0054.\n"
     "VISION_COST_PER_PAGE = 0.0054\n"
     "VISION_CPP = {\"value\": None, \"source\": \"fallback $%.4f\" % VISION_COST_PER_PAGE}\n"
     "CPP_SOURCE = {\"source\": \"?\"}\n", 1),
    ("translation cpp repriced",
     '''def translation_cost_per_passage(con: sqlite3.Connection) -> float | None:
    """Measured: total translation spend / passages it produced, from usage_log."""
    try:
        r = con.execute("""SELECT SUM(cost_usd), SUM(passages) FROM usage_log
                           WHERE kind = 'translation' AND passages > 0 AND COALESCE(ok, 1) = 1""").fetchone()
        return (r[0] / r[1]) if r and r[0] and r[1] else None
    except sqlite3.Error:
        return None
''',
     '''def translation_cost_per_passage(con: sqlite3.Connection) -> float | None:
    """USD per translated passage at TODAY's prices (METER_GATES_2026_10_04).

    Prefers provider-metered rows (token_source='provider', which count thinking
    tokens and the MAX_TOKENS ladder) once they cover 200+ passages; else every
    row's stored tokens repriced (chars/4 estimates: reads low); else the recorded
    cost, as before, when usage_log has no token columns."""
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(usage_log)")}
        if {"engine", "in_tokens", "out_tokens"} <= cols:
            import cost_tracker

            def priced(rows):
                usd = n = 0.0
                for eng, tin, tout, k in rows:
                    pin, pout = cost_tracker._get_pricing(eng or "")
                    usd += ((tin or 0) * pin + (tout or 0) * pout) / 1e6
                    n += k or 0
                return (usd / n) if n and usd else None
            base = ("SELECT engine, in_tokens, out_tokens, passages FROM usage_log WHERE kind = 'translation' "
                    "AND passages > 0 AND COALESCE(ok, 1) = 1")
            if "token_source" in cols:
                rows = con.execute(base + " AND token_source = 'provider' ORDER BY rowid DESC LIMIT 3000").fetchall()
                if sum(r[3] or 0 for r in rows) >= 200:
                    v = priced(rows)
                    if v:
                        CPP_SOURCE["source"] = "provider tokens, last %d calls, today's prices" % len(rows)
                        return v
            v = priced(con.execute(base).fetchall())
            if v:
                CPP_SOURCE["source"] = "chars/4 estimates repriced (no thinking tokens: reads low)"
                return v
        r = con.execute("""SELECT SUM(cost_usd), SUM(passages) FROM usage_log
                           WHERE kind = 'translation' AND passages > 0 AND COALESCE(ok, 1) = 1""").fetchone()
        CPP_SOURCE["source"] = "recorded cost"
        return (r[0] / r[1]) if r and r[0] and r[1] else None
    except sqlite3.Error:
        return None


def vision_cost_per_page(db: str) -> float | None:
    """METER_GATES_2026_10_04: the same measured figure ocr_consensus uses for --max-usd."""
    try:
        import ocr_consensus
        v = ocr_consensus.measured_cost_per_page(db, fallback=0.0)
    except Exception:
        v = 0.0
    if v:
        VISION_CPP.update(value=v, source="measured: median of the last 300 metered vision pages, today's prices")
        return v
    VISION_CPP.update(value=None, source="fallback $%.4f (fewer than 5 measured pages)" % VISION_COST_PER_PAGE)
    return None
''', 1),
    ("consensus cap",
     "    usd = max(0.05, round(todo * VISION_COST_PER_PAGE + 0.005, 2))\n",
     "    cpp = VISION_CPP[\"value\"] or VISION_COST_PER_PAGE   # METER_GATES_2026_10_04\n"
     "    usd = max(0.05, round(todo * cpp * 1.15 + 0.01, 2))   # 15% headroom: the median moves between runs\n", 1),
    ("consensus est",
     "             % (code, usd, todo)], todo * VISION_COST_PER_PAGE)\n",
     "             % (code, usd, todo)], todo * cpp)\n", 1),
    ("collect measures vision",
     "        cpp = translation_cost_per_passage(con)\n",
     "        cpp = translation_cost_per_passage(con)\n"
     "        vision_cost_per_page(db)   # METER_GATES_2026_10_04\n", 1),
    ("commands header",
     "        print(\"# Back up first:  python scripts\\\\db_backup.py \\\"data\\\\context.db\\\" \"\n",
     "        print(\"# vision $/page %.4f (%s); translation $/passage from %s\"   # METER_GATES_2026_10_04\n"
     "              % (VISION_CPP[\"value\"] or VISION_COST_PER_PAGE, VISION_CPP[\"source\"], CPP_SOURCE[\"source\"]))\n"
     "        print(\"# Back up first:  python scripts\\\\db_backup.py \\\"data\\\\context.db\\\" \"\n", 1),
    ("table header",
     "    hdr = \"%-40s %-18s %6s %5s %4s %5s %6s %6s %6s %6s %6s %4s %8s\" % (\n",
     "    print(\"vision $/page %.4f (%s); translation $/passage from %s\"   # METER_GATES_2026_10_04\n"
     "          % (VISION_CPP[\"value\"] or VISION_COST_PER_PAGE, VISION_CPP[\"source\"], CPP_SOURCE[\"source\"]))\n"
     "    hdr = \"%-40s %-18s %6s %5s %4s %5s %6s %6s %6s %6s %6s %4s %8s\" % (\n", 1),
]

# --------------------------------------------------------------------------- images
IM_EDITS = [
    ("size tokens",
     'IMAGE_SIZE = os.environ.get("SA_IMAGE_SIZE") or None       # "1K" | "2K" | "4K"\n',
     'IMAGE_SIZE = os.environ.get("SA_IMAGE_SIZE") or None       # "1K" | "2K" | "4K"\n'
     '# METER_GATES_2026_10_04: image tokens per image by size, from Google\'s per-image prices for\n'
     '# 3.1 Flash Image (read 2026-10-04): 1K $0.067, 2K $0.101, 4K $0.151 at $60/M. Unset = 1K.\n'
     '# The provider also reports about 400 more output tokens per image (thinking/text): measured\n'
     '# 1,482-1,551 at 1K and 2,080 at 2K in usage_log on 2026-10-04. The ledger prices all output at\n'
     '# the image rate, so the estimate does too.\n'
     'IMAGE_OUT_TOKENS = {"1K": 1120, "2K": 1680, "4K": 2520}\n'
     'IMAGE_OVERHEAD_TOKENS = int(os.environ.get("SA_IMAGE_OVERHEAD_TOKENS", "400"))\n', 1),
    ("size-aware estimate",
     '''            print("generate: %d image(s) with %s, ~$%.3f each (about 1,300 output tokens at $%.0f/M)"
                  % (len(todo), args.model, 1300 * out_p / 1e6, out_p))
''',
     '''            _img = IMAGE_OUT_TOKENS.get((IMAGE_SIZE or "1K").upper(), 1120)   # METER_GATES_2026_10_04
            _tok = _img + IMAGE_OVERHEAD_TOKENS
            print("generate: %d image(s) with %s at %s, ~$%.3f each (about %d image + %d other output tokens, "
                  "at $%.0f/M as the ledger records them)"
                  % (len(todo), args.model, IMAGE_SIZE or "1K (default)", _tok * out_p / 1e6, _img,
                     IMAGE_OVERHEAD_TOKENS, out_p))
''', 1),
]

# --------------------------------------------------------------------------- retire_doc
RD_EDITS = [
    ("orphans before",
     '    print("  applying, in one transaction...")\n',
     '    # METER_GATES_2026_10_04: the post-check is corpus-wide. Count BEFORE, so orphans that\n'
     '    # were already there (157 mentions in STATUS_20261004_1304.md, before the manu\n'
     '    # retirement) are not reported as this retirement\'s fault, and a new leak still is.\n'
     '    ov0 = one("SELECT COUNT(*) FROM passage_embeddings e LEFT JOIN passages p "\n'
     '              "ON p.id=e.passage_id WHERE p.id IS NULL")\n'
     '    om0 = one("SELECT COUNT(*) FROM entity_mentions m LEFT JOIN passages p "\n'
     '              "ON p.id=m.passage_id WHERE p.id IS NULL")\n'
     '    print("  applying, in one transaction...")\n', 1),
    ("orphans report",
     '''    print("    orphaned vectors corpus-wide  : %d" % ov)
    print("    orphaned mentions corpus-wide : %d" % om)
''',
     '''    print("    orphaned vectors corpus-wide  : %d  (before: %d)" % (ov, ov0))
    print("    orphaned mentions corpus-wide : %d  (before: %d)" % (om, om0))
''', 1),
    ("orphans verdict",
     '''    if ov or om:
        print("    NON-ZERO ORPHANS. Something dependent was missed; investigate")
        print("    before the next retirement.")
    con.close()
    return 1 if (ov or om or left) else 0
''',
     '''    if ov > ov0 or om > om0:
        print("    NEW ORPHANS (+%d vectors, +%d mentions). Something dependent was"
              % (ov - ov0, om - om0))
        print("    missed; investigate before the next retirement.")
    elif ov or om:
        print("    Pre-existing orphans, not made by this retirement. Report them with")
        print("    python scripts\\\\diag_orphans.py, clean with fix_orphans.py --apply.")
    con.close()
    return 1 if (ov > ov0 or om > om0 or left) else 0
''', 1),
]

# --------------------------------------------------------------------------- dashboard (Ask)
DB_EDITS = [
    ("meter query embedding",
     '''        res = genai.embed_content(model=model, content=q, task_type="retrieval_query")
''',
     '''        res = genai.embed_content(model=model, content=q, task_type="retrieval_query")
        try:   # METER_GATES_2026_10_04: about $0.000001 a question, but recorded like any paid call
            from usage_meter import meter as _meter
            _dbf = (con.execute("PRAGMA database_list").fetchone() or (None, None, ""))[2]
            if _dbf:   # the file this question was asked of, never a default path
                _meter(kind="ask_embed", doc="", engine=model, in_chars=len(q), units=1, db=_dbf)
        except Exception:
            pass
''', 1),
    ("budget gate before answer",
     '''    user_msg = "PASSAGES:\\n" + "\\n".join(ctx) + f"\\n\\nQUESTION: {q}\\n\\nAnswer, citing [tags]:"
''',
     '''    user_msg = "PASSAGES:\\n" + "\\n".join(ctx) + f"\\n\\nQUESTION: {q}\\n\\nAnswer, citing [tags]:"
    # METER_GATES_2026_10_04: Ask is a paid call like any other. It asks the budget first and is metered.
    try:
        from usage_meter import budget_ok as _bok
        if not _bok(db):
            return jsonify({"error": "The spend cap is reached, so Ask is paused. The passages below were "
                                     "found without a paid call. Raise the cap with python scripts\\\\set_budget.py.",
                            "sources": sources, "mode": mode}), 402
    except Exception:
        pass
''', 1),
    ("meter answer",
     '''        resp = genai.GenerativeModel(**kwargs).generate_content(user_msg)
        answer = (getattr(resp, "text", "") or "").strip() or \\
''',
     '''        _t0 = time.time()
        resp = genai.GenerativeModel(**kwargs).generate_content(user_msg)
        try:   # METER_GATES_2026_10_04
            from usage_meter import meter as _meter
            try:
                _out = len(getattr(resp, "text", "") or "")
            except Exception:
                _out = 0
            _meter(kind="ask", doc="", engine=engine, resp=resp, in_chars=len(user_msg) + len(_ASK_SYSTEM),
                   out_chars=_out, units=1, duration_s=time.time() - _t0, db=db)
        except Exception:
            pass
        answer = (getattr(resp, "text", "") or "").strip() or \\
''', 1),
]

# --------------------------------------------------------------------------- extract_entities
EE_EDITS = [
    ("import gate",
     "    cur = con.cursor()\n    done = ment_total = barren_total = 0\n",
     "    cur = con.cursor()\n    done = ment_total = barren_total = 0\n"
     "    try:   # METER_GATES_2026_10_04: ask the budget before every batch, as translation does\n"
     "        from usage_meter import budget_ok as _budget_ok\n"
     "    except Exception:\n"
     "        _budget_ok = lambda _c: True\n", 1),
    ("gate each batch",
     "        chunk = rows[start : start + args.batch]     # already (pid, iast, tr)\n",
     "        chunk = rows[start : start + args.batch]     # already (pid, iast, tr)\n"
     "        if not _budget_ok(con):\n"
     "            print(\"  Stopping: the spend cap is reached. Raise it, then re-run to resume.\")\n"
     "            break\n", 1),
]

# --------------------------------------------------------------------------- judge_sample
JS_EDITS = [
    ("gate after --yes",
     "    genai.configure(api_key=key)\n    # response_mime_type forces pure JSON",
     "    genai.configure(api_key=key)\n"
     "    try:   # METER_GATES_2026_10_04\n"
     "        from usage_meter import budget_ok as _bok\n"
     "        if not _bok(args.db):\n"
     "            print(\"Refusing: the spend cap is reached.\"); con.close(); return\n"
     "    except Exception:\n"
     "        pass\n"
     "    # response_mime_type forces pure JSON", 1),
]

# --------------------------------------------------------------------------- ab_source_quality
AB_EDITS = [
    ("gate after --yes",
     '        print("\\nRe-run with --yes. Nothing was called.")\n        con.close(); return\n',
     '        print("\\nRe-run with --yes. Nothing was called.")\n        con.close(); return\n'
     '    try:   # METER_GATES_2026_10_04\n'
     '        from usage_meter import budget_ok as _bok\n'
     '        if not _bok(con):\n'
     '            print("Refusing: the spend cap is reached."); con.close(); return\n'
     '    except Exception:\n'
     '        pass\n', 1),
]

# --------------------------------------------------------------------------- diag_hindi_ab
DH_EDITS = [
    ("gate and reset",
     '    model = args.engine.split(":", 1)[1]\n    t0, out_chars = time.time(), 0\n',
     '    try:   # METER_GATES_2026_10_04\n'
     '        from usage_meter import budget_ok as _bok\n'
     '        if not _bok(args.db):\n'
     '            print("  Refusing: the spend cap is reached."); return 1\n'
     '    except Exception:\n'
     '        pass\n'
     '    if hasattr(infer_mt, "_usage_reset"):\n'
     '        infer_mt._usage_reset()\n'
     '    model = args.engine.split(":", 1)[1]\n    t0, out_chars = time.time(), 0\n', 1),
    ("provider tokens",
     '''            from cost_tracker import log_translation_call
            wcon = sqlite3.connect(args.db, timeout=30)
            log_translation_call(wcon, args.doc, args.engine, in_chars=in_chars, out_chars=out_chars,
                                 duration_s=dur, passages=n_calls, ok=True)
''',
     '''            from cost_tracker import log_translation_call, log_api_call
            wcon = sqlite3.connect(args.db, timeout=30)
            _u = getattr(infer_mt, "_USAGE", None) or {}
            if _u.get("calls"):   # METER_GATES_2026_10_04: provider counts, and not booked as 'translation'
                log_api_call(wcon, kind="ab_test", doc=args.doc or "", engine=args.engine, in_chars=in_chars,
                             out_chars=out_chars, duration_s=dur, passages=n_calls, ok=True,
                             in_tokens=_u["in"], out_tokens=_u["out"])
            else:
                log_translation_call(wcon, args.doc, args.engine, in_chars=in_chars, out_chars=out_chars,
                                     duration_s=dur, passages=n_calls, ok=True)
''', 1),
]

TARGETS = [(Path("scripts/corpus_status.py"), CS_EDITS), (Path("scripts/images.py"), IM_EDITS),
           (Path("scripts/retire_doc.py"), RD_EDITS), (Path("scripts/dashboard.py"), DB_EDITS),
           (Path("scripts/extract_entities.py"), EE_EDITS), (Path("scripts/judge_sample.py"), JS_EDITS),
           (Path("scripts/ab_source_quality.py"), AB_EDITS), (Path("scripts/diag_hindi_ab.py"), DH_EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    marks = [MARK in s for _, s, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand:")
        for (p, _s, _n, _e), m in zip(loaded, marks):
            print("  %-34s %s" % (p, "patched" if m else "not patched"))
        return 1
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written."
              % (sum(len(e) for _, e in TARGETS), len(TARGETS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_meter")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_meter_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Scripts take effect at their next run; the dashboard's Ask after the next idle restart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
