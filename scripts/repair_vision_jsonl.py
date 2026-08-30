#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repair_vision_jsonl.py - audit and repair vision-OCR pages. (2026-08-29)

TWO DEFECTS THIS FINDS
----------------------
1. RUNAWAY REPEATS. A vision model can latch onto a horizontal rule or a dotted
   leader and emit tens of thousands of identical characters until its output
   budget is exhausted. Measured on Shatpatha: 9 of 194 pages, worst was page
   0003 at 129,421 chars where the genuine transcription is the first ~200.
   These are repairable in place - the real text is intact at the front, the
   tail is a single collapsible run.

2. PHRASE LOOPS. The nastier cousin: the model repeats a whole PHRASE hundreds
   of times inside one line - page 0017 repeats
   "ज्ञानकर्मणोर्हेतुं पुरुषविधब्रह्मदर्शनं मे स्तोतुं" to 21,639 chars. Line
   dedup sees 27 distinct lines and single-char collapse never fires, and the
   repeated text is REAL Sanskrit, so it would pass every quality check and be
   translated. These are NOT auto-repaired: Brahmana texts genuinely repeat
   formulae, and a collapser that truncated a real refrain would be worse than
   the bug. They are detected by compression ratio and queued for re-OCR.
   Measured on 194 Shatpatha pages: 9 degenerate pages scored 0.0035-0.0292,
   185 ordinary pages scored 0.1347-0.4766. The 0.08 cut-off sits in that gap.

3. EMPTY PAGES. A page that came back with no text at all. Tesseract read
   1,700-2,100 chars from the same scans, so these are model failures, not
   blank leaves. They are NOT repairable here - they must be re-OCR'd, and this
   script writes the list so you can re-run just those pages.

Ingesting either kind unrepaired puts a hole (or 129,000 underscores) into the
book, and every downstream metric - coverage, quality, embeddings - inherits it.

  python scripts\\repair_vision_jsonl.py --glob "data\\raw_vision\\*.jsonl"
  python scripts\\repair_vision_jsonl.py --glob "data\\raw_vision\\*.jsonl" --apply
"""
from __future__ import annotations
import argparse, glob as globmod, json, os, re, shutil, sys, zlib

RUN_RE = re.compile(r"(.)\1{7,}", re.S)
DEV = re.compile(r"[ऀ-ॣ॰-ॿ]")
RUNAWAY_CHARS = 20000
# Two different thresholds on purpose. Under 5 chars a page is unambiguously a
# model failure. Between 5 and 40 it may be a genuine section-title or colophon
# page - Shatpatha has a real 37-char page - so those are REPORTED for a human
# to glance at, never auto-queued for re-OCR. A repair tool that silently
# re-runs legitimate pages is a worse bug than the one it fixes.
DEFINITELY_EMPTY = 5
SHORT_REVIEW = 40
# Compression ratio catches phrase-level loops that no character rule can see.
# It is alignment-free and needs no assumption about the repeating unit.
# KNOWN LIMIT: a synthetic page of a genuinely repeated Vedic refrain scores
# ~0.049, i.e. below this cut-off; it escapes only because of LOOP_MIN_CHARS.
# On 185 real pages the worst ordinary score was 0.1347, so the margin holds in
# practice - but a truly refrain-heavy long page WILL be flagged. The cost of
# that false positive is one wasted re-OCR, never lost text, which is why this
# flags and never truncates.
LOOP_RATIO = 0.08      # measured gap: degenerate <=0.0292, ordinary >=0.1347
LOOP_MIN_CHARS = 3000  # short pages compress oddly; do not judge them


def compress_ratio(s: str) -> float:
    b = (s or "").encode("utf-8")
    return len(zlib.compress(b, 6)) / len(b) if b else 1.0


def collapse_runs(s: str, keep: int = 8) -> str:
    return RUN_RE.sub(lambda m: m.group(1) * keep, s or "")


def tesseract_len(vision_path: str, tess_dir: str) -> int | None:
    """How many characters Tesseract read from the SAME scan.

    A second opinion we already have on disk and were not using. On 2026-08-29
    vision returned just the page number on two pages - '(८)' for page 0009 and
    '(१८८)' for 0289 - which the length bands read as 'probably a genuine short
    page'. Tesseract had read 1,717 and 2,404 characters from those very scans,
    so they were plainly failures. Returns None when there is no counterpart.
    """
    cand = os.path.join(tess_dir, os.path.basename(vision_path))
    if not os.path.exists(cand):
        return None
    try:
        with open(cand, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return len((json.loads(line).get("text") or "")) if line else 0
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glob", dest="globpat", default="data/raw_vision/*.jsonl")
    ap.add_argument("--apply", action="store_true", help="write the repairs (default: dry run)")
    ap.add_argument("--backup-dir", default=None,
                    help="where to copy originals before rewriting (default: <dir>/_pre_repair)")
    ap.add_argument("--redo-list", default="data/vision_redo.txt",
                    help="file to write the list of pages needing re-OCR")
    ap.add_argument("--tesseract-dir", default="data/raw",
                    help="where the Tesseract JSONL for the same pages lives, used as a "
                         "second opinion on suspiciously short pages")
    ap.add_argument("--shortfall", type=float, default=10.0,
                    help="a vision page this many times shorter than its Tesseract "
                         "counterpart is a failure, not a short page")
    args = ap.parse_args()

    files = sorted(globmod.glob(args.globpat))
    if not files:
        sys.exit(f"no files matched {args.globpat}")

    repaired, empties, shorts, loops, clean, failed = [], [], [], [], 0, []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                line = next((l for l in f if l.strip()), None)
            if not line:
                empties.append((path, 0, "file has no JSON line")); continue
            rec = json.loads(line)
        except Exception as exc:
            failed.append((path, str(exc)[:60])); continue

        text = rec.get("text") or ""
        fixed = collapse_runs(text)
        n_fixed = len(fixed.strip())
        if n_fixed < DEFINITELY_EMPTY:
            empties.append((path, n_fixed, "no usable text"))
        elif n_fixed < SHORT_REVIEW:
            tl = tesseract_len(path, args.tesseract_dir)
            if tl and tl > n_fixed * args.shortfall:
                # Tesseract read far more from the same scan: this is a vision
                # failure wearing the costume of a short page.
                empties.append((path, n_fixed, f"Tesseract read {tl:,} chars here"))
            else:
                shorts.append((path, n_fixed, fixed.strip()[:50]))
        elif (len(fixed) >= LOOP_MIN_CHARS
              and compress_ratio(fixed) < LOOP_RATIO):
            # Measured AFTER collapsing, so underscore runs that the char rule
            # already fixed are not double-counted here.
            loops.append((path, len(fixed), compress_ratio(fixed)))
        elif len(fixed) < len(text):
            repaired.append((path, len(text), len(fixed)))
        elif len(text) > RUNAWAY_CHARS:
            failed.append((path, f"{len(text):,} chars, no collapsible run"))
        else:
            clean += 1

        if args.apply and len(fixed) < len(text):
            bdir = args.backup_dir or os.path.join(os.path.dirname(path), "_pre_repair")
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(path, os.path.join(bdir, os.path.basename(path)))
            rec["text"] = fixed
            meta = rec.get("meta") or {}
            meta.update({"raw_len": len(text), "collapsed": True,
                         "repaired_by": "repair_vision_jsonl.py"})
            rec["meta"] = meta
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("=" * 72)
    print(f"VISION OCR AUDIT   ({len(files):,} pages)   "
          f"{'APPLYING REPAIRS' if args.apply else 'DRY RUN'}")
    print("=" * 72)
    print(f"  clean                       : {clean:,}")
    print(f"  runaway repeats (repairable): {len(repaired):,}")
    print(f"  empty (must re-OCR)         : {len(empties):,}")
    print(f"  very short (review by eye)  : {len(shorts):,}")
    print(f"  phrase loops (must re-OCR)  : {len(loops):,}")
    print(f"  unreadable or odd           : {len(failed):,}")

    if repaired:
        print("\n--- runaway repeats ---")
        for p, before, after in sorted(repaired, key=lambda r: -r[1])[:15]:
            print(f"  {os.path.basename(p):52s} {before:>9,} -> {after:>6,} chars")
        if len(repaired) > 15:
            print(f"  ... and {len(repaired)-15} more")

    if loops:
        print("\n--- phrase loops: real Sanskrit repeated to death, NOT repairable ---")
        for p, ln, r in sorted(loops, key=lambda x: x[2]):
            print(f"  {os.path.basename(p):52s} {ln:>8,} chars  compress={r:.4f}")
        print("  Auto-collapsing these would risk destroying genuine Vedic refrains.")
        print("  They are queued for re-OCR instead.")

    if empties or loops:
        print("\n--- empty pages (these need re-OCR, not repair) ---")
        for p, n, why in empties[:15]:
            print(f"  {os.path.basename(p):46s} {n:>5} chars  {why}")
        if len(empties) > 15:
            print(f"  ... and {len(empties)-15} more")
        if not empties:
            print("  (none - the redo list below is the phrase-looped pages)")
        # Write the page-PDF paths so the re-run is a one-liner.
        try:
            with open(args.redo_list, "w", encoding="utf-8", newline="\n") as f:
                for p in [e[0] for e in empties] + [l[0] for l in loops]:
                    stem = os.path.splitext(os.path.basename(p))[0]
                    f.write(os.path.join("inbox", stem + ".pdf") + "\n")
            print(f"\n  wrote {len(empties)+len(loops)} page path(s) to {args.redo_list}")
            print("  Delete those .jsonl files and re-run ocr_vision.py on just those pages.")
        except Exception as exc:
            print(f"  [warn] could not write redo list: {exc}")

    if shorts:
        print("\n--- very short pages: probably real (title/colophon), verify ---")
        for p, n, sample in shorts[:15]:
            print(f"  {os.path.basename(p):46s} {n:>3} chars  {sample!r}")
        if len(shorts) > 15:
            print(f"  ... and {len(shorts)-15} more")
        print("  These are NOT in the redo list. If one is genuinely blank, delete its")
        print("  .jsonl and re-run ocr_vision.py for that page.")

    if failed:
        print("\n--- needs human eyes ---")
        for p, why in failed[:10]:
            print(f"  {os.path.basename(p):52s} {why}")

    if not args.apply and repaired:
        print("\n(dry run - nothing written. Re-run with --apply. Originals are copied")
        print(" to _pre_repair/ before any file is rewritten.)")

    # EXIT CODE IS THE GATE. On 2026-08-29 an audit correctly reported 6 phrase
    # loops and the wipe+re-ingest ran anyway, putting 250 junk passages into the
    # book (213 from one page) and losing page 102 entirely. A report nobody is
    # forced to read is not a safeguard. Non-zero here means DO NOT INGEST, so a
    # caller can gate on it:
    #   python scripts\repair_vision_jsonl.py --glob "..."
    #   if ($LASTEXITCODE -eq 0) { <wipe + ingest> } else { "not safe to ingest" }
    blocking = len(empties) + len(loops)
    if blocking:
        print("\n" + "!" * 72)
        print(f"NOT SAFE TO INGEST: {len(empties)} empty and {len(loops)} looped page(s) "
              f"remain.")
        print(f"Re-OCR the pages in {args.redo_list} first, then run this audit again.")
        print("!" * 72)
        sys.exit(1)
    print("\nSAFE TO INGEST: no empty pages and no phrase loops remain.")
    sys.exit(0)


if __name__ == "__main__":
    main()
