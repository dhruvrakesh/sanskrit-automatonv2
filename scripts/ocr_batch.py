#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_batch.py  --  called by dashboard to OCR a list of PDF pages in sequence.

Usage:
  python scripts/ocr_batch.py --pdfs p1.pdf p2.pdf ... --outdir data/raw
                               --dpi 400 --lang-tries san+hin+eng san hin eng
"""
import argparse
import subprocess
import sys
import pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs",       nargs="+", required=True)
    ap.add_argument("--outdir",     required=True)
    ap.add_argument("--dpi",        default="400")
    ap.add_argument("--max-dpi",    default="600")
    ap.add_argument("--lang-tries", nargs="+", default=["san+hin+eng", "san", "hin", "eng"])
    args = ap.parse_args()

    ROOT   = pathlib.Path(__file__).resolve().parent.parent
    scr    = str(ROOT / "scripts" / "ocr_pdf.py")
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pdfs = args.pdfs
    ok = 0
    for i, pdf_path in enumerate(pdfs, 1):
        stem    = pathlib.Path(pdf_path).stem
        outpath = str(outdir / (stem + ".jsonl"))
        cmd = [
            sys.executable, scr,
            "--pdf",       pdf_path,
            "--out",       outpath,
            "--dpi",       args.dpi,
            "--max-dpi",   args.max_dpi,
            "--lang-tries",
        ] + args.lang_tries

        pr = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(ROOT))
        out = pr.stdout.decode("utf-8", "replace")
        sys.stdout.write(out)
        status = "ok" if pr.returncode == 0 else f"FAIL(rc={pr.returncode})"
        sys.stdout.write(f"[{i}/{len(pdfs)}] {pathlib.Path(pdf_path).name} -> {status}\n")
        sys.stdout.flush()
        if pr.returncode == 0:
            ok += 1

    print(f"\nDone: {ok}/{len(pdfs)} pages OCRd successfully.")
    sys.exit(0 if ok == len(pdfs) else 1)

if __name__ == "__main__":
    main()
