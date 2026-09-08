#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sample_translation_fidelity.py - does a translation over garbled OCR say what
the Sanskrit says, or does it fluently invent?  (2026-09-08)  READ-ONLY.

WHY THIS EXISTS
---------------
diag_ocr_contamination.py answered a narrower question: how often does a
translation come back EMPTY or as a refusal marker. Its answer was reassuring -
zero unusable translations in every contamination band - and that reassurance
is exactly the problem. `is_unusable()` detects a model that gave up. It cannot
detect a model that did not give up and should have.

The rendered Harita proof showed the failure mode we actually fear: complete,
confident English sitting over a source line containing "Waa". Nothing in the
pipeline flags that. Only a human reading the pair can.

So this draws a sample and hands it to you. It does NOT decide anything.

THE DESIGN THAT MAKES THE ANSWER WORTH HAVING
---------------------------------------------
Two files come out:

  review_sample.csv - what you read. Sanskrit, English, and (when the schema
                      has them) IAST and Hindi. SHUFFLED, and carrying NO
                      contamination score, NO quality score, NO document name.
  review_key.csv    - what you do not read until you are done. Maps each row
                      back to its band, its document, and its passage id.

The blinding is the point. If the sheet said "contamination 0.42" you would
read the English expecting garbage and find it. A control group of clean
passages, indistinguishable on the page, is the only way to know whether a
verdict tracks the damage or tracks the expectation.

USAGE
-----
  python scripts\\sample_translation_fidelity.py
  python scripts\\sample_translation_fidelity.py --n 150
  python scripts\\sample_translation_fidelity.py --doc Bodhicaryavatara
  python scripts\\sample_translation_fidelity.py --score reviewed.csv

Fill in the `verdict` column, then run --score against the filled file.

VERDICT VOCABULARY (one letter, in the verdict column)
  F  faithful   - the English plausibly renders this Sanskrit
  P  partial    - part of it renders; part has no basis in the source
  I  invented   - fluent English with no basis in the visible Sanskrit
  E  empty      - blank, a refusal, or a marker
  ?  illegible  - the source is too damaged for you to judge either way

'?' is a real finding, not an abstention. A source no human can read is a
source no model could have read either.
"""
from __future__ import annotations

import argparse
import csv
import random
import sqlite3
import sys
from pathlib import Path

# Reuse the repo's own contamination maths. Importing rather than copying is
# deliberate: a second implementation is a second thing to drift. My first pass
# at this measure reinvented it and was wrong by 3x.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from diag_ocr_contamination import contamination, dev_frac, is_unusable
except ImportError:
    sys.exit("Cannot import diag_ocr_contamination.py - it must sit beside this "
             "script in scripts/. Aborting rather than reimplementing it.")

BANDS = [("low", 0.00, 0.05), ("mid", 0.05, 0.15), ("high", 0.15, 1.01)]

# Column names this script will use if the schema happens to have them.
OPTIONAL = {
    "iast":    ("iast", "translit", "transliteration", "iast_text"),
    "hindi":   ("translation_hi", "hindi", "hi", "translation_hindi"),
}


def scope_slug(doc: str | None) -> str:
    """Each scope gets its own directory. Two draws must not share a path."""
    if not doc:
        return "corpus"
    return "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in doc)[:60]


def resolve_columns(con) -> dict:
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    required = {"id", "doc_id", "text", "translation"}
    missing = required - cols
    if missing:
        sys.exit(f"passages is missing required column(s): {sorted(missing)}. "
                 f"Found: {sorted(cols)}")
    found = {}
    for label, candidates in OPTIONAL.items():
        for c in candidates:
            if c in cols:
                found[label] = c
                break
    found["_has_text_type"] = "text_type" in cols
    found["_has_quality"] = "quality_score" in cols
    return found


def connect(db: str):
    # Same approach as diag_ocr_contamination.py: NOT mode=ro. A read-only URI
    # cannot attach to the -wal of a database the translator may be writing,
    # and fails with a bare "disk I/O error".
    con = sqlite3.connect(db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")
    return con


def draw(args):
    db = Path(args.db)
    if not db.exists():
        sys.exit(f"No database at {db}. Run from the repo root, or pass --db.")

    con = connect(str(db))
    found = resolve_columns(con)

    select = ["d.code", "p.id", "p.text", "COALESCE(p.translation,'')"]
    if found["_has_quality"]:
        select.append("COALESCE(p.quality_score,0)")
    else:
        select.append("0")
    for label in ("iast", "hindi"):
        select.append(f"COALESCE(p.{found[label]},'')" if label in found else "''")

    where = ["d.code NOT LIKE '%-RETIRED'", "TRIM(COALESCE(p.text,'')) <> ''",
             "TRIM(COALESCE(p.translation,'')) <> ''"]
    if found["_has_text_type"]:
        where.append("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
    params = []
    if args.doc:
        where.append("d.code LIKE ?")
        params.append(f"%{args.doc}%")

    sql = (f"SELECT {', '.join(select)} FROM passages p "
           f"JOIN docs d ON d.id = p.doc_id WHERE {' AND '.join(where)}")
    rows = con.execute(sql, params).fetchall()
    con.close()

    if not rows:
        sys.exit("No translated passages matched. Check --doc, or the filters.")

    # Bucket by contamination, over Devanagari-dominant lines only - the same
    # gate diag_ocr_contamination.py applies, for the same reason: an English
    # or Hindi page is not what we are measuring.
    buckets = {name: [] for name, _, _ in BANDS}
    skipped_not_dev = 0
    skipped_empty = 0
    for code, pid, text, tr, q, iast, hi in rows:
        if dev_frac(text) < args.min_dev:
            skipped_not_dev += 1
            continue
        # Already-detected empties and refusals are excluded by default. We know
        # that answer; reviewer attention is the scarce resource. The useful
        # consequence: any 'E' a reviewer marks is then a failure mode
        # is_unusable() does NOT catch, which is worth knowing on its own.
        if is_unusable(tr) and not args.include_empties:
            skipped_empty += 1
            continue
        c = contamination(text)
        for name, lo, hi_ in BANDS:
            if lo <= c < hi_:
                buckets[name].append((code, pid, text, tr, q, iast, hi, c))
                break

    print("=" * 78)
    print("POPULATION (translated, Devanagari-dominant, after filters)")
    print("=" * 78)
    print(f"  translated passages considered : {len(rows):,}")
    print(f"  skipped, under {args.min_dev:.2f} Devanagari : {skipped_not_dev:,}")
    print(f"  skipped, already empty/refusal : {skipped_empty:,}"
          + ("" if not args.include_empties else "  (kept: --include-empties)"))
    for name, lo, hi_ in BANDS:
        print(f"  {name:>5} contamination {lo:.2f}-{hi_:<5.2f} : "
              f"{len(buckets[name]):>7,} eligible")

    per = max(1, args.n // len(BANDS))
    rng = random.Random(args.seed)
    picked = []
    for name, _, _ in BANDS:
        pool = buckets[name]
        if not pool:
            print(f"\n  WARNING: band '{name}' is empty - no control for it.")
            continue
        take = min(per, len(pool))
        if take < per:
            print(f"\n  NOTE: band '{name}' has only {len(pool)} rows; taking all.")
        for r in rng.sample(pool, take):
            picked.append((name,) + r)

    if not picked:
        sys.exit("Nothing to sample.")

    rng.shuffle(picked)

    out_dir = Path(args.out_dir) / scope_slug(args.doc)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / "review_sample.csv"
    key_path = out_dir / "review_key.csv"

    # A second run must never silently erase the first. The original version of
    # this script wrote both draws to one path, and a corpus-wide sample was
    # destroyed by the --doc run that followed it thirty seconds later.
    if sample_path.exists() and not args.force:
        sys.exit(f"{sample_path} already exists.\n"
                 f"Refusing to overwrite a sample that may already hold verdicts.\n"
                 f"Pass --force to replace it, or --out-dir to write elsewhere.\n"
                 f"(The draw is seeded, so --force with the same --seed and --n "
                 f"reproduces it exactly.)")

    has_iast = "iast" in found
    has_hindi = "hindi" in found

    # utf-8-sig so Excel on Windows renders Devanagari instead of mojibake.
    with sample_path.open("w", newline="", encoding="utf-8-sig") as f:
        cols = ["row_id", "sanskrit"]
        if has_iast:
            cols.append("iast")
        cols += ["english"]
        if has_hindi:
            cols.append("hindi")
        cols += ["verdict", "notes"]
        w = csv.writer(f)
        w.writerow(cols)
        for i, (band, code, pid, text, tr, q, iast, hi, c) in enumerate(picked, 1):
            row = [i, text]
            if has_iast:
                row.append(iast)
            row.append(tr)
            if has_hindi:
                row.append(hi)
            row += ["", ""]
            w.writerow(row)

    with key_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "band", "contamination", "quality_score",
                    "doc_code", "passage_id", "already_flagged_unusable"])
        for i, (band, code, pid, text, tr, q, iast, hi, c) in enumerate(picked, 1):
            w.writerow([i, band, f"{c:.4f}", f"{q:.3f}", code, pid,
                        "yes" if is_unusable(tr) else "no"])

    print("\n" + "=" * 78)
    print("WRITTEN")
    print("=" * 78)
    print(f"  {sample_path}   <- read and fill the 'verdict' column")
    print(f"  {key_path}      <- do NOT open until the verdicts are in")
    print(f"\n  {len(picked)} rows, shuffled, seed={args.seed}.")
    if not has_iast:
        print("  NOTE: no IAST column in the schema - judging from Devanagari alone.")
    print("\n  verdict: F faithful | P partial | I invented | E empty | ? illegible")
    print(f"\n  When done:  python {Path(__file__).name} --score \"{sample_path}\"")


def score(args):
    sample_path = Path(args.score)
    if not sample_path.exists():
        sys.exit(f"No such file: {sample_path}")
    # The key lives beside its own sample. Deriving it from the sample's
    # directory rather than recomputing --out-dir means a renamed or moved
    # review folder still scores against the right key, and a sample can never
    # be scored against another scope's key.
    key_path = sample_path.parent / "review_key.csv"
    if not key_path.exists():
        sys.exit(f"No key at {key_path}.\n"
                 f"The key must sit in the same directory as the sample it "
                 f"belongs to. If you moved the sample, move review_key.csv "
                 f"with it.")

    key = {}
    with key_path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key[r["row_id"]] = r

    tally = {}
    ungraded = 0
    unknown = []
    with sample_path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rid = (r.get("row_id") or "").strip()
            v = (r.get("verdict") or "").strip().upper()
            if not v:
                ungraded += 1
                continue
            if v not in ("F", "P", "I", "E", "?"):
                unknown.append((rid, v))
                continue
            if rid not in key:
                continue
            band = key[rid]["band"]
            tally.setdefault(band, {k: 0 for k in "FPIE?"})[v] += 1

    print("=" * 78)
    print("FIDELITY BY CONTAMINATION BAND")
    print("=" * 78)
    if ungraded:
        print(f"  {ungraded} row(s) still blank - graded rows only below.\n")
    if unknown:
        print(f"  {len(unknown)} row(s) with an unrecognised verdict: "
              f"{unknown[:5]}\n")
    print(f"  {'band':>6} | {'n':>5} | {'faithful':>8} | {'partial':>7} | "
          f"{'INVENTED':>8} | {'empty':>5} | {'illegible':>9}")
    print("  " + "-" * 72)
    for name, _, _ in BANDS:
        t = tally.get(name)
        if not t:
            continue
        n = sum(t.values())
        print(f"  {name:>6} | {n:>5} | {t['F']:>8} | {t['P']:>7} | "
              f"{t['I']:>8} | {t['E']:>5} | {t['?']:>9}")

    print("\n  Read it this way:")
    print("   - INVENTED climbing with contamination while the low band stays at")
    print("     zero is the finding. It means the pipeline pays for fluent fiction")
    print("     over damaged sources, and re-OCR must precede re-translation.")
    print("   - INVENTED flat across all three bands means your reviewer is")
    print("     judging the English, not the pair. The blinding did its job by")
    print("     exposing that, and the sample needs a second reader.")
    print("   - A large '?' count in the high band is its own answer: those")
    print("     passages cannot be validated by anyone and should not be")
    print("     published as translations regardless of how they read.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="substring match on the doc code")
    ap.add_argument("--n", type=int, default=90, help="total rows (split evenly across bands)")
    ap.add_argument("--seed", type=int, default=20260908, help="reproducible draw")
    ap.add_argument("--min-dev", type=float, default=0.30)
    ap.add_argument("--out-dir", default="data/fidelity_review")
    ap.add_argument("--include-empties", action="store_true",
                    help="also sample translations is_unusable() already flags")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing sample in this scope's directory")
    ap.add_argument("--score", default=None, help="path to the filled review_sample.csv")
    args = ap.parse_args()

    if args.score:
        score(args)
    else:
        draw(args)


if __name__ == "__main__":
    main()
