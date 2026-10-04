#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_spend_2026_10_04.py  (2026-10-04)  SPEND_TRUTH_2026_10_04

Is API spend leak-proof? Read from the code on 2026-10-04: no. Four holes, all
"the meter reads low", none "money leaves without a record":

  1. Prices. cost_tracker prices gemini-2.5-flash (translation AND vision OCR) at
     $0.15 / $0.60 per 1M tokens. Google's pricing page no longer lists 2.5 Flash;
     two independent price trackers (pricepertoken.com, updated 2026-10-02;
     morphllm.com, 2026-08-21) give $0.30 input / $2.50 output. Output was priced
     at a quarter of its cost, so the budget cap trips 2-4x late.
  2. Translation is metered from CHARACTERS (chars/4), never from the provider's
     token counts. Devanagari costs more than one token per 4 characters
     (diag_token_ratio.py exists to measure it), and the dynamic THINKING tokens of
     2.5 Flash - billed as output - are not counted at all. Calls made by the
     MAX_TOKENS ladder (16k, 32k, fallback model, chunking) are not counted either.
  3. ocr_consensus.py --max-usd compares against COST_PER_PAGE_MEASURED = 0.00028.
     ocr_vision measured $0.00089-$0.00097 per Rgveda page on 2026-10-04 (at the old
     prices) and printed "Update COST_PER_PAGE". A --max-usd 1.00 cap therefore
     allowed about 3,500 pages.
  4. Paths that spend without asking the budget first: build_embeddings.py (run by
     the 3-hourly maintenance task), images.py brief. (Also, not changed here:
     extract_entities.py, the dashboard's Ask, judge_sample.py, ab_source_quality.py,
     diag_hindi_ab.py - each metered, none gated.)

This patch (all-or-nothing, marker-idempotent, backups, py_compile, atomic):
  scripts/cost_tracker.py   2.5-flash and vision 2.5-flash -> (0.30, 2.50); the
                            unknown-engine default -> (0.30, 2.50) (was 0.15/0.60).
                            Old rows keep their recorded cost; spend_audit.py reprices.
  scripts/infer_mt.py       every generate_content call (first try, retries, the whole
                            MAX_TOKENS ladder) adds the response's usage_metadata
                            (prompt + candidates + thoughts) to a per-batch counter;
                            the batch is logged with those PROVIDER counts
                            (token_source='provider'). If the SDK gives no counts, the
                            old chars/4 estimate is logged, as before.
  scripts/ocr_consensus.py  the vision estimate uses the MEASURED cost per page from
                            usage_log (median of the last 300 provider-metered
                            ocr_vision rows, repriced at the current table); fallback
                            $0.0015. Empty vision files that already had >= 2 retries
                            are not re-sent every run (--retry-refused still does).
  scripts/build_embeddings.py  refuses when the budget is paused or exhausted.

Raising recorded prices makes the cap trip sooner. Read spend_audit.py first and,
if needed, set the budget deliberately (python scripts\\set_budget.py).

  python scripts/patch_spend_2026_10_04.py --check
  python scripts/patch_spend_2026_10_04.py
Test: python -m unittest tests.test_spend_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "SPEND_TRUTH_2026_10_04"

CT_EDITS = [
    ("2.5 flash price",
     '    "gemini:gemini-2.5-flash":    (0.15,   0.60),\n',
     '    # SPEND_TRUTH_2026_10_04: $0.30 / $2.50 (pricepertoken.com 2026-10-02, morphllm.com 2026-08-21;\n'
     '    # Google\'s own page no longer lists 2.5 Flash). Was (0.15, 0.60), the 2025 preview price.\n'
     '    "gemini:gemini-2.5-flash":    (0.30,   2.50),\n', 1),
    ("vision price",
     '    "gemini-vision:gemini-2.5-flash": (0.15, 0.60),\n',
     '    "gemini-vision:gemini-2.5-flash": (0.30, 2.50),   # SPEND_TRUTH_2026_10_04\n', 1),
    ("default price",
     '    # Default: assume Gemini 2.5 Flash (the project default engine)\n    return (0.15, 0.60)\n',
     '    # Default: assume Gemini 2.5 Flash (the project default engine) - SPEND_TRUTH_2026_10_04\n'
     '    return (0.30, 2.50)\n', 1),
]

MT_EDITS = [
    ("usage counter",
     "def _gen(gm, msg):\n",
     "# SPEND_TRUTH_2026_10_04: provider token counts for every call in a batch, including\n"
     "# retries and the MAX_TOKENS ladder. Thinking tokens are billed as output.\n"
     "_USAGE = {\"in\": 0.0, \"out\": 0.0, \"calls\": 0}\n\n\n"
     "def _usage_reset():\n"
     "    _USAGE.update({\"in\": 0.0, \"out\": 0.0, \"calls\": 0})\n\n\n"
     "def _usage_add(resp):\n"
     "    try:\n"
     "        um = getattr(resp, \"usage_metadata\", None)\n"
     "        if um is None:\n"
     "            return\n"
     "        pin = getattr(um, \"prompt_token_count\", None)\n"
     "        out = getattr(um, \"candidates_token_count\", None)\n"
     "        think = getattr(um, \"thoughts_token_count\", None) or 0\n"
     "        if pin is None and out is None:\n"
     "            return\n"
     "        _USAGE[\"in\"] += float(pin or 0)\n"
     "        _USAGE[\"out\"] += float((out or 0) + think)\n"
     "        _USAGE[\"calls\"] += 1\n"
     "    except Exception:\n"
     "        pass\n\n\n"
     "def _gen(gm, msg):\n", 1),
    ("count each call",
     '    if _REQ_OPTS_OK and _REQ_TIMEOUT > 0:\n'
     '        return gm.generate_content(msg, request_options={"timeout": _REQ_TIMEOUT})\n'
     '    return gm.generate_content(msg)\n',
     '    if _REQ_OPTS_OK and _REQ_TIMEOUT > 0:\n'
     '        resp = gm.generate_content(msg, request_options={"timeout": _REQ_TIMEOUT})\n'
     '    else:\n'
     '        resp = gm.generate_content(msg)\n'
     '    _usage_add(resp)   # SPEND_TRUTH_2026_10_04\n'
     '    return resp\n', 1),
    ("reset per batch",
     '        t_start = time.time()\n\n        if engine.startswith("openai:"):\n',
     '        t_start = time.time()\n'
     '        _usage_reset()   # SPEND_TRUTH_2026_10_04\n\n'
     '        if engine.startswith("openai:"):\n', 1),
    ("log provider tokens",
     '            cost = log_translation_call(\n'
     '                con, doc_code, engine,\n'
     '                in_chars=actual_in,\n'
     '                out_chars=actual_out,\n'
     '                duration_s=duration,\n'
     '                passages=len(missing_texts),\n'
     '                ok=True,\n'
     '            )\n',
     '            if _USAGE["calls"] and (_USAGE["in"] + _USAGE["out"]) > 0:   # SPEND_TRUTH_2026_10_04\n'
     '                from cost_tracker import log_api_call as _log_api\n'
     '                cost = _log_api(con, kind="translation", doc=doc_code, engine=engine,\n'
     '                                in_chars=actual_in, out_chars=actual_out, duration_s=duration,\n'
     '                                passages=len(missing_texts), ok=True,\n'
     '                                in_tokens=_USAGE["in"], out_tokens=_USAGE["out"])\n'
     '            else:\n'
     '                cost = log_translation_call(\n'
     '                    con, doc_code, engine,\n'
     '                    in_chars=actual_in,\n'
     '                    out_chars=actual_out,\n'
     '                    duration_s=duration,\n'
     '                    passages=len(missing_texts),\n'
     '                    ok=True,\n'
     '                )\n', 1),
]

OC_HELPER = '''

def measured_cost_per_page(db, fallback: float = 0.0015) -> float:
    """SPEND_TRUTH_2026_10_04: median USD per vision page from usage_log (last 300
    provider-metered ocr_vision rows), repriced with cost_tracker's current table."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import cost_tracker
        uri = Path(db).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            rows = con.execute("""SELECT engine, in_tokens, out_tokens, passages FROM usage_log
                                  WHERE kind='ocr_vision' AND token_source='provider' AND COALESCE(ok,1)=1
                                  AND passages > 0 ORDER BY id DESC LIMIT 300""").fetchall()
        finally:
            con.close()
        vals = []
        for eng, tin, tout, n in rows:
            pin, pout = cost_tracker._get_pricing(eng or "")
            vals.append(((tin or 0) * pin + (tout or 0) * pout) / 1e6 / max(1, n))
        vals = sorted(v for v in vals if v > 0)
        return vals[len(vals) // 2] if len(vals) >= 5 else fallback
    except Exception:
        return fallback


def gave_up(p: Path) -> bool:
    """SPEND_TRUTH_2026_10_04: an EMPTY vision file that already had >= 2 retries is a
    blank or unreadable page; re-sending it every run only bills it again."""
    try:
        with open(p, encoding="utf-8") as f:
            rec = json.loads(next((l for l in f if l.strip()), "{}"))
        return (not (rec.get("text") or "").strip()) and int((rec.get("meta") or {}).get("retries") or 0) >= 2
    except Exception:
        return False


def plan_vision('''

OC_EDITS = [
    ("helpers", "\n\ndef plan_vision(", OC_HELPER, 1),
    ("skip gave-up", "        ok = nonempty_jsonl(vf) or (not retry_refused and refused(vf))\n",
     "        ok = nonempty_jsonl(vf) or (not retry_refused and (refused(vf) or gave_up(vf)))   # SPEND_TRUTH_2026_10_04\n", 1),
    ("measured estimate", "        est = len(todo) * COST_PER_PAGE_MEASURED\n",
     "        cpp = measured_cost_per_page(args.db)   # SPEND_TRUTH_2026_10_04\n"
     "        est = len(todo) * cpp\n", 1),
    ("print estimate", "              % (len(queue), len(done), len(todo), est, COST_PER_PAGE_MEASURED))\n",
     "              % (len(queue), len(done), len(todo), est, cpp))\n", 1),
]

EMB_EDITS = [
    ("budget gate",
     '    print(f"Embedding {total} passages with {args.model} (batch={args.batch})\u2026")\n',
     '    try:   # SPEND_TRUTH_2026_10_04: ask the budget before spending\n'
     '        from usage_meter import budget_ok as _budget_ok\n'
     '        if not _budget_ok(con):\n'
     '            print("Refusing: the spend cap is reached (budget_state). Nothing embedded.")\n'
     '            con.close()\n'
     '            return\n'
     '    except ImportError:\n'
     '        pass\n'
     '    print(f"Embedding {total} passages with {args.model} (batch={args.batch})\u2026")\n', 1),
]

TARGETS = [(Path("scripts/cost_tracker.py"), CT_EDITS), (Path("scripts/infer_mt.py"), MT_EDITS),
           (Path("scripts/ocr_consensus.py"), OC_EDITS), (Path("scripts/build_embeddings.py"), EMB_EDITS)]


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
        print("REFUSING: marker in some files only - inspect by hand."); return 1
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
        print("CHECK OK: %d anchored edits in 4 files. Nothing written." % sum(len(e) for _, e in TARGETS)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_spend")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_spend_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Effective at each script's next run. Run spend_audit.py to see recorded vs repriced spend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
