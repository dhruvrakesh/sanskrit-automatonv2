#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_ocr_contamination.py - is the source-quality gate letting garbage through,
and what has that cost us?  (2026-08-29)  READ-ONLY. NO API CALLS.

THE PROBLEM
-----------
`passages.quality_score` = 0.6 * devanagari_density + 0.4 * danda_presence.
It measures how Devanagari a line LOOKS, never whether the Devanagari is real
words. A garbled Tesseract line such as

    VR (c) [+ जा as wa ¢ हस्तो वे गहः । स छम्मणाऽतिग्रहेण गहत हर्ताभ्या१९ हि कम करेति ॥

scores ~0.64 and sails past the 0.35 threshold. We then pay to translate it and
the model correctly returns nothing.

THE PROPOSED SIGNAL
-------------------
Inside a line that is Devanagari-dominant, stray LATIN LETTERS and OCR junk
symbols are near-zero in a genuine verse and abundant in a garbled one:

    contamination = (latin + junk) / (devanagari + latin + junk)

This script does NOT change anything. It measures whether that signal actually
separates the passages that produced a usable translation from the ones that
did not - on your own corpus - so the threshold is chosen from evidence.

  python scripts\\diag_ocr_contamination.py
  python scripts\\diag_ocr_contamination.py --doc 2015_405693_Shatpath-Brahmanam
  python scripts\\diag_ocr_contamination.py --show 15    # sample lines at each band
"""
from __future__ import annotations
import argparse, re, sqlite3, sys

DEV_LETTER = re.compile(r"[ऀ-ॣ॰-ॿ]")   # excludes danda + digits
DEV_DIGIT  = re.compile(r"[०-९]")
LATIN      = re.compile(r"[A-Za-z]")
JUNK       = re.compile(r"[©®¢£§¶†‡~^_=<>{}\\|@#$%*+]")

# translations that are not translations
_EMPTY_MARKS = ("[empty]", "[echo]", "<<no translation>>", "n/a", "[skipped",
                "[untranslatable", "translation unavailable")


def contamination(text: str) -> float:
    """0.0 = pure Devanagari, 1.0 = no Devanagari at all."""
    if not text:
        return 0.0
    dev = len(DEV_LETTER.findall(text))
    lat = len(LATIN.findall(text))
    junk = len(JUNK.findall(text))
    denom = dev + lat + junk
    return (lat + junk) / denom if denom else 0.0


def dev_frac(text: str) -> float:
    if not text:
        return 0.0
    return len(DEV_LETTER.findall(text)) / max(1, len(text))


def is_unusable(tr: str) -> bool:
    t = (tr or "").strip().lower()
    if not t:
        return True
    return any(t.startswith(m) or t == m.strip() for m in _EMPTY_MARKS)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--show", type=int, default=6, help="sample lines per band")
    ap.add_argument("--min-dev", type=float, default=0.30,
                    help="only score lines at least this Devanagari (skip English pages)")
    args = ap.parse_args()

    # NOT mode=ro: a read-only URI cannot attach to the -wal of a database the
    # translator is actively writing, and fails with a bare "disk I/O error".
    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")

    where = ["COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')",
             "d.code NOT LIKE '%-RETIRED'",
             "TRIM(COALESCE(p.text,'')) <> ''"]
    params = []
    if args.doc:
        where.append("d.code = ?"); params.append(args.doc)
    rows = con.execute(f"""
        SELECT d.code, p.id, p.text, COALESCE(p.translation,''),
               COALESCE(p.quality_score,0)
        FROM passages p JOIN docs d ON d.id = p.doc_id
        WHERE {' AND '.join(where)}
    """, params).fetchall()
    con.close()

    if not rows:
        sys.exit("no passages matched.")

    BANDS = [(0.00, 0.02), (0.02, 0.05), (0.05, 0.10),
             (0.10, 0.20), (0.20, 0.35), (0.35, 1.01)]
    stat = {b: {"n": 0, "translated": 0, "unusable": 0, "q": 0.0, "ex": []} for b in BANDS}
    scored = 0
    for code, pid, text, tr, q in rows:
        if dev_frac(text) < args.min_dev:
            continue                       # an English/Hindi page, not our target
        scored += 1
        c = contamination(text)
        for b in BANDS:
            if b[0] <= c < b[1]:
                s = stat[b]
                s["n"] += 1
                s["q"] += q or 0
                if (tr or "").strip():
                    s["translated"] += 1
                    if is_unusable(tr):
                        s["unusable"] += 1
                if len(s["ex"]) < args.show and (tr or "").strip():
                    s["ex"].append((code, pid, text[:90], (tr or "")[:60], q, c))
                break

    print("=" * 78)
    print(f"CONTAMINATION vs TRANSLATION OUTCOME   ({scored:,} Devanagari-dominant "
          f"passages of {len(rows):,})")
    print("=" * 78)
    print(f"  {'contamination':>16} | {'passages':>9} | {'mean q_score':>12} | "
          f"{'translated':>10} | {'UNUSABLE':>9} | {'fail rate':>9}")
    print("  " + "-" * 76)
    for b in BANDS:
        s = stat[b]
        if not s["n"]:
            continue
        mq = s["q"] / s["n"]
        fr = (100.0 * s["unusable"] / s["translated"]) if s["translated"] else 0.0
        flag = "  <-- garbage" if fr > 25 else ""
        print(f"  {b[0]:6.2f}-{b[1]:<9.2f} | {s['n']:>9,} | {mq:>12.3f} | "
              f"{s['translated']:>10,} | {s['unusable']:>9,} | {fr:>8.1f}%{flag}")

    print("\n  'UNUSABLE' = a translation was produced and paid for, but is empty or a")
    print("  refusal marker. If the fail rate climbs with contamination while mean")
    print("  q_score stays flat, quality_score is blind to the thing that matters.")

    print("\n" + "=" * 78)
    print("WHAT A CONTAMINATION GATE WOULD HAVE SAVED")
    print("=" * 78)
    for thresh in (0.05, 0.10, 0.15, 0.20):
        blocked = sum(s["n"] for b, s in stat.items() if b[0] >= thresh)
        blk_tr = sum(s["translated"] for b, s in stat.items() if b[0] >= thresh)
        blk_bad = sum(s["unusable"] for b, s in stat.items() if b[0] >= thresh)
        good_lost = blk_tr - blk_bad
        print(f"  reject contamination >= {thresh:.2f}: blocks {blocked:>6,} passages; "
              f"of the {blk_tr:,} already translated there, {blk_bad:,} were waste "
              f"and {good_lost:,} were usable")
    print("\n  Pick the threshold where waste-blocked is high and usable-lost is low.")
    print("  A gate that also blocks good verses is a worse bug than the one it fixes.")

    if args.show:
        print("\n" + "=" * 78)
        print("SAMPLES (judge these with your own eyes before trusting any threshold)")
        print("=" * 78)
        for b in BANDS:
            s = stat[b]
            if not s["ex"]:
                continue
            print(f"\n--- contamination {b[0]:.2f}-{b[1]:.2f} ---")
            for code, pid, text, tr, q, c in s["ex"]:
                print(f"  [{code[:28]}#{pid}] q={q:.2f} contam={c:.2f}")
                print(f"    SRC: {text}")
                print(f"    EN : {tr!r}")


if __name__ == "__main__":
    main()
