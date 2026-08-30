#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_ocr_sources.py - build the FINAL per-page OCR set from both engines.
(2026-08-29)

WHY BOTH ENGINES, MEASURED
--------------------------
Vision-vs-vision agreement across two passes is 0.927 (12 pages, 11 of them
0.894-0.978). That is the ceiling of what agreement can show. Against it,
Tesseract's word accuracy across 47 documents runs 0.338 to 0.730 - the best
book in the corpus reaches 78% of achievable, the median 64%. So vision is the
source of record everywhere; there is no document where Tesseract is safe.

But vision is not infallible and must not be trusted blindly. It returned three
characters on Shatpatha page 0009 where Tesseract read 1,717, and it produced
the non-word `तरुश` where Tesseract correctly had `तरुण`. A vision-only corpus
loses those pages and those readings silently.

WHAT THIS DOES
--------------
For every page it picks the better source and RECORDS WHICH:

  vision            vision passed the audit  -> use it
  tesseract-fallback vision failed (empty, phrase loop, or far shorter than
                     Tesseract on the same scan) -> use Tesseract, flagged
  none              neither engine produced usable text -> page is reported,
                     never silently filled

The output is one merged JSONL per page in --outdir, carrying `engine` so
ingest_jsonl_fast.py writes it into passages.ocr_engine. Downstream, a
tesseract-fallback page can be found, re-tried, or shown to a reader with the
caveat it deserves.

  python scripts\\merge_ocr_sources.py --doc <CODE>
  python scripts\\merge_ocr_sources.py --doc <CODE> --apply
"""
from __future__ import annotations
import argparse, glob as globmod, json, os, re, sys, zlib

DEV = re.compile(r"[ऀ-ॣ॰-ॿ]")
RUN_RE = re.compile(r"(.)\1{7,}", re.S)
DEFINITELY_EMPTY = 5
SHORTFALL = 10.0        # vision this many times shorter than Tesseract = failure
LOOP_RATIO = 0.08       # see BENCHMARKS.md; degenerate <=0.029, ordinary >=0.135
LOOP_MIN_CHARS = 3000


def collapse_runs(s, keep=8):
    return RUN_RE.sub(lambda m: m.group(1) * keep, s or "")


def compress_ratio(s):
    b = (s or "").encode("utf-8")
    return len(zlib.compress(b, 6)) / len(b) if b else 1.0


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return json.loads(line) if line else None
    except Exception:
        return None


def verdict(vtext: str, ttext: str) -> tuple[str, str]:
    """Which source to use for this page, and why."""
    v = collapse_runs(vtext or "").strip()
    t = (ttext or "").strip()
    if len(v) < DEFINITELY_EMPTY:
        return ("tesseract-fallback" if len(t) >= DEFINITELY_EMPTY else "none",
                "vision returned nothing")
    if len(v) >= LOOP_MIN_CHARS and compress_ratio(v) < LOOP_RATIO:
        return ("tesseract-fallback" if len(t) >= DEFINITELY_EMPTY else "none",
                f"vision phrase loop (compress={compress_ratio(v):.4f})")
    if t and len(t) > len(v) * SHORTFALL:
        return "tesseract-fallback", f"vision {len(v)} chars vs Tesseract {len(t)}"
    return "vision", ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--tesseract-dir", default="data/raw")
    ap.add_argument("--outdir", default="data/raw_merged")
    ap.add_argument("--apply", action="store_true", help="write the merged files")
    args = ap.parse_args()

    tess = {}
    for p in globmod.glob(os.path.join(args.tesseract_dir, f"{args.doc}_*.jsonl")):
        m = re.match(rf"^{re.escape(args.doc)}_(\d{{4}})(_norm)?\.jsonl$", os.path.basename(p))
        if m:
            tess.setdefault(m.group(1), p)
    vis = {}
    for p in globmod.glob(os.path.join(args.vision_dir, f"{args.doc}_*.jsonl")):
        m = re.match(rf"^{re.escape(args.doc)}_(\d{{4}})\.jsonl$", os.path.basename(p))
        if m:
            vis[m.group(1)] = p

    pages = sorted(set(tess) | set(vis))
    if not pages:
        sys.exit(f"no pages found for {args.doc}")

    counts = {"vision": 0, "tesseract-fallback": 0, "none": 0}
    notes = []
    if args.apply:
        os.makedirs(args.outdir, exist_ok=True)

    for pg in pages:
        vrec = read(vis[pg]) if pg in vis else None
        trec = read(tess[pg]) if pg in tess else None
        vtext = (vrec or {}).get("text") or ""
        ttext = (trec or {}).get("text") or ""
        src, why = verdict(vtext, ttext)
        counts[src] += 1
        if src != "vision":
            notes.append((pg, src, why, len(vtext), len(ttext)))
        if not args.apply:
            continue
        if src == "none":
            continue                       # never fabricate a page
        if src == "vision":
            text, engine = collapse_runs(vtext), (vrec or {}).get("engine") or "gemini-vision"
        else:
            text, engine = ttext, "tesseract-fallback"
        out = {
            "engine": engine,
            "page_no": int(pg),
            "text": text,
            "meta": {"merged_from": src, "reason": why,
                     "vision_chars": len(vtext), "tesseract_chars": len(ttext)},
            "src_pdf": f"{args.doc}_{pg}.pdf",
        }
        with open(os.path.join(args.outdir, f"{args.doc}_{pg}.jsonl"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    total = len(pages)
    print("=" * 74)
    print(f"OCR SOURCE MERGE  {args.doc}   {total} pages   "
          f"{'WRITING' if args.apply else 'DRY RUN'}")
    print("=" * 74)
    for k in ("vision", "tesseract-fallback", "none"):
        pct = 100.0 * counts[k] / total
        print(f"  {k:20s} {counts[k]:>5}  ({pct:5.1f}%)")
    if notes:
        print("\n  pages NOT taken from vision:")
        for pg, src, why, nv, nt in notes[:25]:
            print(f"    page {pg}  {src:19s} {why}")
        if len(notes) > 25:
            print(f"    ... and {len(notes)-25} more")
    if counts["none"]:
        print(f"\n  {counts['none']} page(s) have NO usable text from either engine.")
        print("  They are omitted rather than filled with something false.")
    if counts["tesseract-fallback"]:
        print(f"\n  {counts['tesseract-fallback']} page(s) fall back to Tesseract, whose word")
        print("  accuracy on this corpus is 34-73% of achievable. They are marked")
        print("  engine='tesseract-fallback' in the DB so they can be found and redone.")
    if args.apply:
        print(f"\n  merged files -> {args.outdir}")
        print(f"  ingest with:\n    python scripts\\ingest_jsonl_fast.py --doc {args.doc} "
              f"--glob \"{args.outdir}\\{args.doc}_*.jsonl\" --db data\\context.db")
    else:
        print("\n(dry run - nothing written. Add --apply.)")


if __name__ == "__main__":
    main()
