#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_cost_ratio_2026_10_05.py  (2026-10-05)  COST_RATIO_2026_10_05

The vision estimate was still wrong, and I said otherwise. Measured on the
04:00 backup of 2026-10-05 (context_20261005.db, read immutable):

  ocr_vision, 2026-10-03 12:00 -> now, provider-metered:
    557 calls that delivered a page        $1.94
     93 calls that delivered nothing       $1.08   (ladder attempts, units=0)
  -> $3.02 for 557 pages = $0.00542 a page. spend_audit printed exactly that
     ("0.00542" $/unit, last 24 h). The mean and median per row, used since
     SPEND_TRUTH and CREDITS_COST, skipped the 93 zero-page rows (36% of spend).

  per text, all provider-metered history:
    Rgveda Vol-ii    539 calls, 447 pages, $2.89 -> $0.00646 a page
    Shatpatha        336 calls, 336 pages, $1.17 -> $0.00348
    markandeya       101 calls, 100 pages, $0.13 -> $0.00132
    Mallapurana      301 calls, 202 pages, $0.23 -> $0.00115
  One corpus-wide figure therefore under-prices Rgveda about 2.5x and
  over-prices small clean books. corpus_status on 2026-10-05 proposed
  "--max-usd 1.82 # ~618 pages" for Rgveda; at Rgveda's own rate that is
  about $4.0, so the pre-check would pass and the spend would be twice the cap.

Fixes (all-or-nothing, marker-idempotent, backups .bak_ratio_<date>, py_compile):
  ocr_consensus.py  measured_cost_per_page(): ratio of sums, zero-page calls
                    included; doc= uses that text's own last 600 calls when it has
                    >= 20 delivered pages. Consensus passes its doc.
  corpus_status.py  each text's consensus estimate and --max-usd use that text's
                    own rate (falls back to the corpus figure).
  ocr_vision.py     the pre-flight estimate comes from the ledger (was a fixed
                    $0.00028); the "Update COST_PER_PAGE" note no longer prints on
                    every one-page run (it printed 51 times on 2026-10-05).
  spend_audit.py    the closing line names the prepaid credit as the bill.

  python scripts/patch_cost_ratio_2026_10_05.py --check
  python scripts/patch_cost_ratio_2026_10_05.py
Test: python -m unittest tests.test_cost_ratio_2026_10_05 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "COST_RATIO_2026_10_05"

OC_OLD = '''def measured_cost_per_page(db, fallback: float = 0.0015) -> float:
    """SPEND_TRUTH_2026_10_04: USD per vision page from usage_log (last 300
    provider-metered ocr_vision rows), repriced with cost_tracker's current table.
    CREDITS_COST_2026_10_04: the MEAN, not the median - an estimate of a total is
    n x mean, and page cost is right-skewed (2026-10-04: median $0.00282, mean
    $0.00313, max $0.04282)."""
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
        return (sum(vals) / len(vals)) if len(vals) >= 5 else fallback   # CREDITS_COST_2026_10_04: mean
    except Exception:
        return fallback
'''
OC_NEW = '''def measured_cost_per_page(db, fallback: float = 0.0015, doc: str | None = None) -> float:
    """USD per DELIVERED vision page, from usage_log, repriced with cost_tracker's table.

    COST_RATIO_2026_10_05: total cost of the calls / pages they delivered (a ratio of
    sums). The mean and median used before (SPEND_TRUTH, CREDITS_COST) counted only
    rows with passages > 0, and so left out the ladder attempts that ocr_vision meters
    with units=0 - which are billed. On 2026-10-03/04: 93 such calls cost $1.08 of
    $3.02 (36%), almost all on Rgveda. Pages differ by book too (Rgveda $0.00646 a
    page, Mallapurana $0.00115), so with doc= a text that already has >= 20 delivered
    pages is priced from its own last 600 calls; otherwise the last 300 calls
    corpus-wide are used."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import cost_tracker
        uri = Path(db).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            base = ("SELECT engine, in_tokens, out_tokens, passages FROM usage_log "
                    "WHERE kind='ocr_vision' AND token_source='provider'")
            rows = []
            if doc:
                rows = con.execute(base + " AND doc=? ORDER BY id DESC LIMIT 600", (doc,)).fetchall()
                if sum((r[3] or 0) for r in rows) < 20:
                    rows = []
            if not rows:
                rows = con.execute(base + " ORDER BY id DESC LIMIT 300").fetchall()
        finally:
            con.close()
        usd = pages = 0.0
        for eng, tin, tout, n in rows:
            pin, pout = cost_tracker._get_pricing(eng or "")
            usd += ((tin or 0) * pin + (tout or 0) * pout) / 1e6
            pages += max(0, n or 0)
        return (usd / pages) if (pages >= 5 and usd > 0) else fallback
    except Exception:
        return fallback
'''
OC_EDITS = [
    ("ratio of sums", OC_OLD, OC_NEW, 1),
    ("per doc in consensus",
     "        cpp = measured_cost_per_page(args.db)   # SPEND_TRUTH_2026_10_04\n",
     "        cpp = measured_cost_per_page(args.db, doc=doc)   # COST_RATIO_2026_10_05: this text's own rate\n", 1),
]

CS_EDITS = [
    ("remember db",
     '''        VISION_CPP.update(value=v, source="measured: mean of the last 300 metered vision pages, today's prices")
        return v
''',
     '''        VISION_CPP.update(value=v, db=db, source="measured: cost / pages delivered, last 300 vision calls "
                                                  "incl. ladder retries, today's prices; per text where it has its own")
        return v
''', 1),
    ("per-doc helper",
     "def drift_counts(db: str, doc: str, merged: dict) -> dict:\n",
     '''def _doc_vision_cpp(code: str) -> float:
    """COST_RATIO_2026_10_05: this text's own measured $/page when it has >= 20 delivered pages."""
    base = VISION_CPP["value"] or VISION_COST_PER_PAGE
    db = VISION_CPP.get("db")
    if not db:
        return base
    try:
        import ocr_consensus
        return ocr_consensus.measured_cost_per_page(db, fallback=base, doc=code)
    except Exception:
        return base


def drift_counts(db: str, doc: str, merged: dict) -> dict:
''', 1),
    ("use it",
     '    cpp = VISION_CPP["value"] or VISION_COST_PER_PAGE   # METER_GATES_2026_10_04\n',
     '    cpp = _doc_vision_cpp(code)   # COST_RATIO_2026_10_05 (was the corpus-wide figure for every text)\n', 1),
]

OV_EDITS = [
    ("measured pre-flight",
     '''    print(f"  pre-flight estimate: ${len(targets)*COST_PER_PAGE:.3f} at ${COST_PER_PAGE}/page "
''',
     '''    _cpp = COST_PER_PAGE   # COST_RATIO_2026_10_05: the ledger's own figure for this text when it has one
    try:
        import ocr_consensus as _oc
        _cpp = _oc.measured_cost_per_page(args.db, fallback=COST_PER_PAGE, doc=args.doc)
    except Exception:
        pass
    print(f"  pre-flight estimate: ${len(targets)*_cpp:.3f} at ${_cpp:.5f}/page "
''', 1),
    ("no per-page nag",
     '''        if ok and abs(per - COST_PER_PAGE) / max(per, 1e-9) > 0.25:
            print(f"  NOTE: the ${COST_PER_PAGE}/page pre-flight estimate is off by more than "
                  f"25%. Update COST_PER_PAGE to {per:.5f} in ocr_vision.py.")
''',
     '''        if ok >= 5 and abs(per - _cpp) / max(per, 1e-9) > 0.25:   # COST_RATIO_2026_10_05
            print(f"  NOTE: this run cost ${per:.5f}/page against the ledger's ${_cpp:.5f}/page. "
                  f"Estimates follow the ledger; nothing needs editing.")
''', 1),
]

SA_EDITS = [
    ("prepaid footer",
     '    print("\\nOnly Google Cloud Billing is the bill. Set a budget alert and lower the API quota there for a hard cap.")\n',
     '    # COST_RATIO_2026_10_05: jobs.jsonl 2026-10-04 shows HTTP 402 "prepayment credits are depleted".\n'
     '    print("\\nThe provider\'s record is the bill, not this ledger. This key draws PREPAID credit (AI Studio):"\n'
     '          "\\nreconcile the two weekly, and keep the app cap (set_budget.py) a little below the remaining"\n'
     '          "\\nbalance, so the app stops cleanly before the provider refuses.")\n', 1),
]

TARGETS = [(Path("scripts/ocr_consensus.py"), OC_EDITS), (Path("scripts/corpus_status.py"), CS_EDITS),
           (Path("scripts/ocr_vision.py"), OV_EDITS), (Path("scripts/spend_audit.py"), SA_EDITS)]


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
            print("  %-30s %s" % (p, "patched" if m else "not patched"))
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
        t = p.with_name(p.name + ".tmp_ratio")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        if p.suffix == ".py":
            try:
                py_compile.compile(str(t), doraise=True)
            except py_compile.PyCompileError as e:
                for x, _ in tmps + [(t, p)]:
                    x.unlink(missing_ok=True)
                print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_ratio_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Takes effect at each script's next run. No restart needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
