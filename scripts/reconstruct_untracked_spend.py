#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reconstruct_untracked_spend.py - what did the UNMETERED work already cost?
(2026-08-29)

Until today, usage_log recorded only kind='translation'. Vision OCR, entity
extraction, embeddings and the Q4 judge all ran against paid endpoints and
wrote nothing, so `budget_state.spent_usd` under-states real spend by an
unknown amount. Metering is now wired in, but that only fixes the FUTURE.

This script reconstructs the PAST from the artefacts each job left behind:

  embeddings  <- passage_embeddings rows x the length of the text embedded
  entities    <- passages.ents rows    x prompt/response size, modelled
  judge       <- mt_reviews rows       x prompt/response size, modelled
  ocr_vision  <- vision JSONL files    x measured tokens/page (see --page-cost)

READ-ONLY by default. Nothing is written and the budget does not move.
`--apply` writes one summary row per kind into usage_log marked
token_source='reconstructed' and adds the total to budget_state.spent_usd, so
the cap starts guarding against a true figure.

HONESTY NOTE, read this before quoting any number below:
  * Embedding input length is exact (the text is still in the DB); the
    chars/4 token ratio is not.
  * Entity and judge OUTPUT sizes are modelled, not stored - the replies were
    never persisted. They are the weakest numbers here.
  * Vision OCR per-page cost is unknown until a metered run measures it.
    Pass --page-cost with the figure the next `ocr_vision.py --yes` run
    prints, or leave it and the page count is reported with NO dollar figure
    rather than an invented one.

  python scripts/reconstruct_untracked_spend.py --db data/context.db
  python scripts/reconstruct_untracked_spend.py --page-cost 0.00061 --apply
"""
from __future__ import annotations
import argparse, glob as globmod, json, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EMBED_MODEL_PRICE_PER_M = 0.15      # gemini-embedding-001, input only
FLASH_IN, FLASH_OUT = 0.15, 0.60    # gemini-2.5-flash per 1M tokens
CHARS_PER_TOKEN = 4.0

# Modelled overheads (documented so they can be argued with):
ENTITY_SYS_CHARS = 1200   # system instruction resent on every batch call
ENTITY_OUT_CHARS = 90     # JSON emitted per verse, observed order of magnitude
JUDGE_SYS_CHARS  = 900
JUDGE_OUT_CHARS  = 120    # {"reason","fidelity","fluency"} minified
JUDGE_THINK_TOK  = 350    # 2.5-flash thinking tokens, billed as output


def _tok(chars: float) -> float:
    return chars / CHARS_PER_TOKEN


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--vision-glob", default="data/raw/*.jsonl",
                    help="where vision OCR wrote its JSONL pages")
    ap.add_argument("--page-cost", type=float, default=None,
                    help="MEASURED USD/page from a metered ocr_vision run")
    ap.add_argument("--entity-batch", type=int, default=10,
                    help="verses per model call used by the extraction runs")
    ap.add_argument("--apply", action="store_true",
                    help="write reconstructed rows and charge them to the budget")
    args = ap.parse_args()

    ro = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=30)
    tabs = {r[0] for r in ro.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    lines = []
    total = 0.0

    # ---------------- embeddings ----------------
    if "passage_embeddings" in tabs:
        row = ro.execute("""
            SELECT COUNT(*),
                   SUM(LENGTH(COALESCE(p.iast,'')) + 3 + LENGTH(COALESCE(p.translation,'')))
            FROM passage_embeddings e JOIN passages p ON p.id = e.passage_id
        """).fetchone()
        n, chars = row[0] or 0, row[1] or 0
        # build_embeddings truncates each text at 2000 chars
        chars = min(chars, n * 2000) if n else 0
        usd = EMBED_MODEL_PRICE_PER_M * _tok(chars) / 1e6
        total += usd
        lines.append(("embedding", n, chars, 0, usd,
                      "input length exact; token ratio approximated"))

    # ---------------- entity extraction ----------------
    if "passages" in tabs:
        pcols = {r[1] for r in ro.execute("PRAGMA table_info(passages)")}
        if "ents" in pcols:
            row = ro.execute("""
                SELECT COUNT(*),
                       SUM(LENGTH(COALESCE(iast,'')) + MIN(LENGTH(COALESCE(translation,'')),700))
                FROM passages WHERE ents IS NOT NULL AND TRIM(ents) <> ''
            """).fetchone()
            n, body = row[0] or 0, row[1] or 0
            calls = max(1, -(-n // args.entity_batch)) if n else 0
            in_chars = body + calls * ENTITY_SYS_CHARS
            out_chars = n * ENTITY_OUT_CHARS
            usd = (FLASH_IN * _tok(in_chars) + FLASH_OUT * _tok(out_chars)) / 1e6
            total += usd
            lines.append(("entities", n, in_chars, out_chars, usd,
                          f"{calls} modelled calls; OUTPUT size is an assumption"))

    # ---------------- Q4 judge ----------------
    if "mt_reviews" in tabs:
        row = ro.execute("""
            SELECT COUNT(*),
                   SUM(LENGTH(COALESCE(p.text,'')) + LENGTH(COALESCE(p.iast,''))
                       + LENGTH(COALESCE(p.translation,'')))
            FROM mt_reviews r JOIN passages p ON p.id = r.passage_id
        """).fetchone()
        n, body = row[0] or 0, row[1] or 0
        in_chars = body + n * JUDGE_SYS_CHARS
        out_tok = n * (_tok(JUDGE_OUT_CHARS) + JUDGE_THINK_TOK)
        usd = (FLASH_IN * _tok(in_chars) + FLASH_OUT * out_tok) / 1e6
        total += usd
        lines.append(("judge", n, in_chars, int(out_tok * CHARS_PER_TOKEN), usd,
                      "thinking tokens assumed at 350/call - the largest guess here"))

    # ---------------- vision OCR ----------------
    pages = 0
    for path in globmod.glob(args.vision_glob):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    if "gemini-vision" in (json.loads(ln).get("engine") or ""):
                        pages += 1
        except Exception:
            continue
    if pages:
        if args.page_cost:
            usd = pages * args.page_cost
            total += usd
            lines.append(("ocr_vision", pages, 0, 0, usd,
                          f"{pages} pages x ${args.page_cost}/page (measured)"))
        else:
            lines.append(("ocr_vision", pages, 0, 0, None,
                          "NO dollar figure: run one metered page first, then "
                          "re-run with --page-cost <usd>"))

    # ---------------- report ----------------
    print("=" * 74)
    print("RECONSTRUCTED SPEND ON WORK THAT WAS NEVER METERED")
    print("=" * 74)
    for kind, units, ic, oc, usd, note in lines:
        amt = f"${usd:.4f}" if usd is not None else "  (unpriced)"
        print(f"  {kind:11s} units={units:<7} in_chars={ic:<10} out_chars={oc:<9} {amt}")
        print(f"              ^ {note}")
    print(f"\n  RECONSTRUCTED TOTAL (priced items only): ${total:.4f}")

    try:
        cap, spent = ro.execute("SELECT budget_usd, spent_usd FROM budget_state WHERE id=1").fetchone()
        logged = ro.execute("SELECT ROUND(SUM(cost_usd),4) FROM usage_log").fetchone()[0] or 0
        print(f"\n  recorded so far (translation only) : ${logged:.4f}")
        print(f"  budget_state.spent_usd             : ${spent:.4f}")
        print(f"  TRUE spend, best estimate          : ${spent + total:.4f}  of ${cap:.2f} cap")
        if pages and not args.page_cost:
            print(f"  ...PLUS {pages} vision OCR pages, still unpriced.")
    except Exception:
        pass
    ro.close()

    if not args.apply:
        print("\n(read-only; nothing written. Add --apply to charge these to the budget.)")
        return

    con = sqlite3.connect(args.db, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    import cost_tracker
    cost_tracker.ensure_usage_schema(con)
    written = 0
    for kind, units, ic, oc, usd, note in lines:
        if usd is None:
            continue
        if con.execute("SELECT COUNT(*) FROM usage_log WHERE kind=? AND token_source='reconstructed'",
                       (kind,)).fetchone()[0]:
            print(f"  [skip] {kind}: a reconstructed row already exists (not double-charging).")
            continue
        con.execute("""INSERT INTO usage_log(kind, doc, engine, in_chars, out_chars,
                          in_tokens, out_tokens, cost_usd, duration_s, passages, ok, token_source)
                       VALUES(?,?,?,?,?,?,?,?,0,?,1,'reconstructed')""",
                    (kind, "(backfill)", "reconstructed", ic, oc,
                     _tok(ic), _tok(oc), usd, units))
        con.execute("UPDATE budget_state SET spent_usd = spent_usd + ?, "
                    "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=1", (usd,))
        written += 1
    con.commit()
    cap, spent = con.execute("SELECT budget_usd, spent_usd FROM budget_state WHERE id=1").fetchone()
    con.close()
    print(f"\n  wrote {written} reconstructed row(s). spent_usd is now ${spent:.4f} of ${cap:.2f}.")
    print("  These rows are labelled token_source='reconstructed' so they can always be told")
    print("  apart from measured spend, and re-running this script will not double-charge.")


if __name__ == "__main__":
    main()
