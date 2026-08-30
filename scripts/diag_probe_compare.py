#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_probe_compare.py - compare two ocr_probe result sets. (2026-08-29)
READ-ONLY. NO API CALLS.

Written because the equivalent PowerShell one-liner was a nested-quote disaster.

  python scripts\\diag_probe_compare.py data\\ocr_probe_results_v1_evenspaced.json ^
                                        data\\ocr_probe_results_dense.json
  python scripts\\diag_probe_compare.py --ceiling 0.94 data\\ocr_probe_results_dense.json
"""
from __future__ import annotations
import argparse, json, statistics, sys


def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"cannot read {p}: {exc}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="one or two probe results JSON files")
    ap.add_argument("--ceiling", type=float, default=None,
                    help="vision-vs-vision agreement from `ocr_probe.py --self-check`. "
                         "Given this, each score is expressed as a FRACTION OF ACHIEVABLE, "
                         "which is the only fair way to read it.")
    args = ap.parse_args()

    if len(args.files) == 2:
        a, b = load(args.files[0]), load(args.files[1])
        keys = sorted(set(a) & set(b))
        print("=" * 74)
        print("SAMPLING COMPARISON  (does page choice change the verdict?)")
        print("=" * 74)
        print(f"  {'document':42s} {'A':>7} {'B':>7} {'delta':>8}")
        print("  " + "-" * 70)
        deltas = []
        for k in keys:
            x, y = a[k]["token_agreement"], b[k]["token_agreement"]
            deltas.append(y - x)
            print(f"  {k[:42]:42s} {x:>7.3f} {y:>7.3f} {y-x:>+8.3f}")
        if deltas:
            print(f"\n  median shift {statistics.median(deltas):+.3f}   "
                  f"range {min(deltas):+.3f} to {max(deltas):+.3f}")
            print("  A positive shift means the second sampler chose better pages;")
            print("  it does NOT mean the OCR improved.")
        results = b
    else:
        results = load(args.files[0])

    print("\n" + "=" * 74)
    print("DISTRIBUTION  (is there a clean band to threshold on?)")
    print("=" * 74)
    vals = sorted(r["token_agreement"] for r in results.values())
    n = len(vals)
    print(f"  documents {n}   min {vals[0]:.3f}   median {statistics.median(vals):.3f}   "
          f"max {vals[-1]:.3f}")
    # Largest gap between consecutive sorted values = the only natural threshold.
    gaps = [(vals[i+1] - vals[i], vals[i], vals[i+1]) for i in range(n - 1)]
    g, lo, hi = max(gaps)
    print(f"  largest gap between adjacent documents: {g:.3f}  ({lo:.3f} -> {hi:.3f})")
    if g < 0.05:
        print("  VERDICT: no natural break. The scores form a continuum, so any")
        print("  threshold would be arbitrary. A continuum means every document sits")
        print("  somewhere on one slope of badness, not in a good camp or a bad camp.")
    else:
        print(f"  VERDICT: a break exists at ~{(lo+hi)/2:.3f} - that is your threshold,")
        print("  chosen by the data rather than by assumption.")

    print("\n  histogram")
    for lo_ in [x / 20 for x in range(6, 16)]:
        c = sum(1 for v in vals if lo_ <= v < lo_ + 0.05)
        print(f"    {lo_:.2f}-{lo_+0.05:.2f}  {'#' * c}{'' if c else ' .'} {c}")

    if args.ceiling:
        print("\n" + "=" * 74)
        print(f"AGAINST THE MEASURED CEILING ({args.ceiling:.3f})")
        print("=" * 74)
        print("  'achievable' = score / ceiling. 1.00 means indistinguishable from")
        print("  a second vision pass; anything less is genuine Tesseract error.")
        rows = sorted(results.items(), key=lambda kv: kv[1]["token_agreement"])
        for k, r in rows:
            frac = r["token_agreement"] / args.ceiling
            bar = "#" * int(frac * 30)
            print(f"  {k[:40]:40s} {r['token_agreement']:.3f}  {frac:>5.0%} {bar}")
        best = rows[-1][1]["token_agreement"] / args.ceiling
        print(f"\n  Even the best document reaches only {best:.0%} of achievable.")
        print("  If that is well under 100%, no document is safe on Tesseract alone.")


if __name__ == "__main__":
    main()
