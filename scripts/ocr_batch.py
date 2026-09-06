#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_batch.py  --  called by dashboard to OCR a list of PDF pages in sequence.

Usage:
  python scripts/ocr_batch.py --pdfs p1.pdf p2.pdf ... --outdir data/raw
                               --dpi 400 --lang-tries san+hin+eng san hin eng
  python scripts/ocr_batch.py --pdfs-from manifest.txt --outdir data/raw

--pdfs-from (2026-08-29) exists because Windows caps a command line at ~32,767
characters. A 1,064-page book listed as 1,064 arguments is ~80,000 characters,
so the process could never even start: it died instantly with
  FileNotFoundError: [WinError 206] The filename or extension is too long
and the dashboard showed a red OCR job with 0/1064 and no explanation. Books
under roughly 430 pages fit and worked, which is why this looked random.
The manifest is one path per line, UTF-8.
"""
import argparse
import subprocess
import sys
import pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs",       nargs="+", default=None,
                    help="page PDFs as arguments (fine for small books)")
    ap.add_argument("--pdfs-from",  dest="pdfs_from", default=None,
                    help="file listing one page-PDF path per line - use this for "
                         "large books; immune to the Windows command-line limit")
    ap.add_argument("--doc", default=None,
                    help="doc code: find its page-PDFs in --inbox directly. Added "
                         "2026-08-30 because the manifest is written by the dashboard's "
                         "OCR button, so a CLI run had no manifest to point at.")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--skip-existing", action="store_true",
                    help="with --doc: skip pages whose .jsonl already exists in --outdir")
    ap.add_argument("--outdir",     required=True)
    ap.add_argument("--dpi",        default="400")
    ap.add_argument("--max-dpi",    default="600")
    ap.add_argument("--lang-tries", nargs="+", default=["san+hin+eng", "san", "hin", "eng"])
    args = ap.parse_args()

    _given = sum(1 for x in (args.pdfs, args.pdfs_from, args.doc) if x)
    if _given != 1:
        ap.error("give exactly one of --pdfs, --pdfs-from or --doc")

    ROOT   = pathlib.Path(__file__).resolve().parent.parent
    scr    = str(ROOT / "scripts" / "ocr_pdf.py")
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.pdfs_from:
        with open(args.pdfs_from, "r", encoding="utf-8") as fh:
            pdfs = [ln.strip() for ln in fh if ln.strip()]
        print(f"[ocr_batch] {len(pdfs)} pages from manifest {args.pdfs_from}", flush=True)
    elif args.doc:
        import glob as _glob, re as _re
        _re_pg = _re.compile(r"_(\d{4})\.pdf$", _re.IGNORECASE)
        pdfs = sorted(p for p in _glob.glob(str(pathlib.Path(args.inbox) / f"{args.doc}_*.pdf"))
                      if _re_pg.search(p))
        if args.skip_existing:
            before = len(pdfs)
            pdfs = [p for p in pdfs
                    if not (outdir / (pathlib.Path(p).stem + ".jsonl")).exists()]
            print(f"[ocr_batch] --skip-existing: {before - len(pdfs)} already done", flush=True)
        print(f"[ocr_batch] {len(pdfs)} page-PDFs for doc={args.doc} in {args.inbox}", flush=True)
    else:
        pdfs = args.pdfs
    if not pdfs:
        print("[ocr_batch] nothing to do: empty page list."); sys.exit(0)
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
