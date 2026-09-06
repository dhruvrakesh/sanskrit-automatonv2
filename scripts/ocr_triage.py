#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_triage.py - decide DETERMINISTICALLY which pages need a vision pass.
(2026-08-30)

THE ARCHITECTURE THIS IMPLEMENTS
--------------------------------
Tesseract on every page (free, local, unlimited), a deterministic evaluation of
which pages it handled badly, and vision ONLY on those. Not a per-document
verdict - a per-page one, because a book is not uniformly hard.

WHAT WAS TRIED AND REJECTED, so nobody re-treads it
---------------------------------------------------
  * Latin-intrusion contamination: did not separate usable from unusable
    documents; superseded.
  * Devanagari orthographic validity: measured on 314 Shatpatha page-pairs,
    correlation with token agreement 0.363, and 305 of 314 pages fell in a
    single band. It fails because Tesseract's errors are orthographically LEGAL
    but wrong - शातपथ for शतपथ is a perfectly valid letter sequence.
  * Per-document token agreement: works, but costs a vision pass to compute, so
    it cannot decide whether to spend a vision pass.

WHAT WORKS
----------
Tesseract's OWN per-word confidence, which ocr_pdf.py now records into each
page's meta (conf_mean, conf_p10, conf_lt60). It costs nothing, it is available
BEFORE any vision spend, and Tesseract is honest about not being able to read -
English OCR on a Devanagari page returns conf_mean 25.7 with 93% of words under
60.

  # 1. Calibrate on pages where BOTH engines have run, so the threshold is
  #    chosen from evidence rather than assumed:
  python scripts\\ocr_triage.py --calibrate --doc 2015_405693_Shatpath-Brahmanam

  # 2. Then queue only the pages that need vision:
  python scripts\\ocr_triage.py --doc <CODE> --threshold 72
  python scripts\\ocr_triage.py --doc <CODE> --threshold 72 --write-queue
"""
from __future__ import annotations
import argparse, glob as globmod, json, math, os, re, statistics, sys

DEV = re.compile(r"[ऀ-ॣ॰-ॿ]")


def toks(t):
    return [w for w in re.split(r"[^ऀ-ॣ॰-ॿ]+", t or "") if len(w) >= 3]


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return json.loads(line) if line else None
    except Exception:
        return None


def conf_of(rec):
    m = (rec or {}).get("meta") or {}
    return m.get("conf_mean"), m.get("conf_lt60"), m.get("conf_words")


def calibrate(args):
    """Does Tesseract confidence predict the need for vision?

    Ground truth = token agreement against the vision reading on the same page,
    which we already paid for. If confidence predicts it, we can stop paying.
    """
    rows = []
    for tp in sorted(globmod.glob(os.path.join(args.tesseract_dir, f"{args.doc}_*.jsonl"))):
        base = os.path.basename(tp)
        vp = os.path.join(args.vision_dir, base)
        if not os.path.exists(vp):
            continue
        trec, vrec = read(tp), read(vp)
        if not trec or not vrec:
            continue
        cm, clt, cw = conf_of(trec)
        if cm is None:
            continue
        a, b = toks(trec.get("text") or ""), set(toks(vrec.get("text") or ""))
        if len(a) < 30 or not b:
            continue
        rows.append((base, cm, clt or 0.0, sum(1 for w in a if w in b) / len(a)))

    if not rows:
        print("No pages carry confidence yet.")
        print("ocr_pdf.py records it from 2026-08-30 onward, so pages OCR'd before")
        print("that have none. Re-run Tesseract on this doc to populate it:")
        print(f"   python scripts\\ocr_batch.py --pdfs-from data\\manifests\\ocr_{args.doc}.txt "
              f"--outdir data\\raw --dpi 400")
        return

    print("=" * 74)
    print(f"CALIBRATION: does Tesseract confidence predict the need for vision?")
    print("=" * 74)
    print(f"  pages with both engines and a confidence figure: {len(rows)}")
    n = len(rows)
    mx = statistics.mean(r[1] for r in rows); my = statistics.mean(r[3] for r in rows)
    sx = math.sqrt(sum((r[1]-mx)**2 for r in rows)/n) or 1e-9
    sy = math.sqrt(sum((r[3]-my)**2 for r in rows)/n) or 1e-9
    corr = sum((r[1]-mx)*(r[3]-my) for r in rows)/n/(sx*sy)
    print(f"  mean confidence {mx:.1f}   mean token agreement {my:.3f}")
    print(f"  correlation(confidence, agreement) = {corr:.3f}")

    print(f"\n  {'confidence band':>18} {'pages':>6} {'mean agreement':>16}")
    print("  " + "-" * 46)
    for lo, hi in [(0,60),(60,70),(70,75),(75,80),(80,85),(85,101)]:
        sel = [r for r in rows if lo <= r[1] < hi]
        if sel:
            print(f"  {lo:>7}-{hi:<10} {len(sel):>6} "
                  f"{statistics.mean(x[3] for x in sel):>16.3f}")

    print("\n  VERDICT")
    if abs(corr) < 0.35:
        print(f"   correlation {corr:.3f} is too weak. Tesseract confidence does NOT")
        print("   predict which pages need vision on this corpus. Do not build a gate")
        print("   on it - that would be the orthographic-validity mistake again.")
        print("   Fall back to: vision every page of documents the probe rates poorly.")
    else:
        rows.sort(key=lambda r: r[1])
        best = None
        for cut in range(50, 95):
            below = [r for r in rows if r[1] < cut]
            above = [r for r in rows if r[1] >= cut]
            if len(below) < 5 or len(above) < 5:
                continue
            gap = statistics.mean(x[3] for x in above) - statistics.mean(x[3] for x in below)
            if best is None or gap > best[1]:
                best = (cut, gap, len(below))
        if best:
            cut, gap, nb = best
            print(f"   correlation {corr:.3f} is usable.")
            print(f"   Best split at confidence {cut}: pages below it agree {gap:.3f} less")
            print(f"   with vision. That queues {nb} of {len(rows)} pages "
                  f"({100.0*nb/len(rows):.0f}%) for a vision pass,")
            print(f"   costing about ${nb*0.00087:.2f} instead of ${len(rows)*0.00087:.2f}"
                  f" for the whole book.")
            print(f"\n   Use: --threshold {cut}")


def triage(args):
    pages, missing = [], 0
    for tp in sorted(globmod.glob(os.path.join(args.tesseract_dir, f"{args.doc}_*.jsonl"))):
        m = re.match(rf"^{re.escape(args.doc)}_(\d{{4}})(_norm)?\.jsonl$", os.path.basename(tp))
        if not m:
            continue
        rec = read(tp)
        cm, clt, cw = conf_of(rec)
        if cm is None:
            missing += 1
            continue
        pages.append((m.group(1), cm, clt or 0.0, len(toks(rec.get("text") or ""))))

    if missing:
        print(f"  [warn] {missing} page(s) have no confidence recorded (OCR'd before")
        print("         2026-08-30). Re-run Tesseract on this doc to populate them.")
    if not pages:
        sys.exit("no pages carry confidence; nothing to triage.")

    need = [p for p in pages if p[1] < args.threshold]
    ok = len(pages) - len(need)
    print("=" * 74)
    print(f"TRIAGE  {args.doc}   threshold: confidence < {args.threshold}")
    print("=" * 74)
    print(f"  pages with confidence : {len(pages)}")
    print(f"  Tesseract accepted    : {ok}  ({100.0*ok/len(pages):.1f}%)  - no vision spend")
    print(f"  queued for vision     : {len(need)}  ({100.0*len(need)/len(pages):.1f}%)"
          f"  ~${len(need)*0.00087:.2f}")
    if need:
        print(f"\n  {'page':>6} {'conf':>7} {'<60':>7} {'words':>6}")
        print("  " + "-" * 30)
        for pg, cm, clt, nw in sorted(need, key=lambda x: x[1])[:25]:
            print(f"  {pg:>6} {cm:>7.1f} {clt:>7.2f} {nw:>6}")
        if len(need) > 25:
            print(f"  ... and {len(need)-25} more")

    if args.write_queue and need:
        os.makedirs(os.path.dirname(args.queue) or ".", exist_ok=True)
        with open(args.queue, "w", encoding="utf-8", newline="\n") as f:
            for pg, *_ in sorted(need):
                f.write(os.path.join("inbox", f"{args.doc}_{pg}.pdf") + "\n")
        print(f"\n  wrote {len(need)} page path(s) -> {args.queue}")
        print("  Vision only those:")
        print(f"    Get-Content {args.queue} | ForEach-Object {{")
        print(f"      $stem = [IO.Path]::GetFileNameWithoutExtension($_)")
        print(f"      python scripts\\ocr_vision.py --pdf $_ "
              f"--out \"data\\raw_vision\\$stem.jsonl\" --doc {args.doc} --yes }}")
    elif not need:
        print("\n  Nothing needs vision. Merge and ingest the Tesseract output directly.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--tesseract-dir", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--threshold", type=float, default=72.0,
                    help="mean Tesseract confidence below which a page gets vision")
    ap.add_argument("--queue", default=None)
    ap.add_argument("--write-queue", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="measure whether confidence predicts the need, using pages "
                         "where both engines have already run")
    args = ap.parse_args()
    if not args.queue:
        args.queue = f"data/vision_queue_{args.doc}.txt"
    if args.calibrate:
        calibrate(args)
    else:
        triage(args)


if __name__ == "__main__":
    main()
