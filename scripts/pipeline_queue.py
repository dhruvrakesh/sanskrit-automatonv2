#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_queue.py — Serial full-pipeline runner for Sanskrit Automaton.

Runs: OCR (serial) → Ingest → Translate → Export for one doc at a time.
Called by dashboard's /api/queue/run endpoint.

Usage:
  python scripts/pipeline_queue.py --doc nirukta --inbox inbox --raw data/raw
      --db data/context.db --exports exports --engine gemini:gemini-2.5-flash
"""
import argparse, subprocess, sys, pathlib, time, os, re

ROOT    = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

def py(*args):
    return [sys.executable] + [str(a) for a in args]

def run(label, cmd, cwd=None):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  {' '.join(str(c) for c in cmd)}")
    print(f"{'='*60}")
    start = time.time()
    pr = subprocess.run(cmd, cwd=str(cwd or ROOT),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = pr.stdout.decode("utf-8", "replace")
    print(out)
    dur = round(time.time() - start, 1)
    ok  = pr.returncode == 0
    print(f"[{'OK' if ok else 'FAIL'}] {label}  ({dur}s)")
    return ok


def ocr_missing(doc, inbox, raw, dpi="400", lang_tries=None):
    if lang_tries is None:
        lang_tries = ["san+hin+eng", "san", "hin", "eng"]
    PDF_RE = re.compile(r"^([A-Za-z0-9_]+)_(\d{4})\.pdf$", re.IGNORECASE)
    inbox_p = pathlib.Path(inbox)
    raw_p   = pathlib.Path(raw)
    missing = []
    for p in sorted(inbox_p.glob(f"{doc}_*.pdf")):
        m = PDF_RE.match(p.name)
        if not m: continue
        pg = m.group(2)
        if not (raw_p / f"{doc}_{pg}.jsonl").exists() and \
           not (raw_p / f"{doc}_{pg}_norm.jsonl").exists():
            missing.append(p)
    if not missing:
        print(f"[OCR] Nothing to OCR for {doc}")
        return True

    print(f"[OCR] {len(missing)} pages to OCR for {doc} (serial, one at a time)")
    ok_count = 0
    for i, pdf in enumerate(missing, 1):
        out_path = str(raw_p / (pdf.stem + ".jsonl"))
        cmd = py(SCRIPTS / "ocr_pdf.py",
                 "--pdf",       str(pdf),
                 "--out",       out_path,
                 "--dpi",       dpi,
                 "--max-dpi",   "600",
                 "--lang-tries", *lang_tries)
        label = f"OCR [{i}/{len(missing)}] {pdf.name}"
        if run(label, cmd):
            ok_count += 1
        else:
            print(f"[WARN] OCR failed for {pdf.name}, continuing...")
    print(f"\n[OCR] Done: {ok_count}/{len(missing)} pages succeeded")
    return ok_count > 0


def ingest(doc, raw, db):
    glob_pat = str(pathlib.Path(raw) / f"{doc}_*.jsonl")
    cmd = py(SCRIPTS / "ingest_jsonl_fast.py",
             "--doc",  doc,
             "--glob", glob_pat,
             "--db",   db)
    return run(f"Ingest {doc}", cmd)


def translate(doc, db, engine, limit=None, sleep="0.6"):
    cmd = py(SCRIPTS / "translate_passages.py",
             "--doc",    doc,
             "--db",     db,
             "--engine", engine,
             "--sleep",  sleep)
    if limit:
        cmd += ["--limit", str(limit)]
    return run(f"Translate {doc}", cmd)


def export_html(doc, db, exports, title=None):
    title = title or f"{doc} — Sanskrit with English Translation"
    cmd = py(SCRIPTS / "export_html.py",
             "--doc",   doc,
             "--db",    db,
             "--out",   exports,
             "--title", title)
    return run(f"Export {doc}", cmd)


def main():
    ap = argparse.ArgumentParser(description="Run full pipeline for one doc (serial)")
    ap.add_argument("--doc",      required=True)
    ap.add_argument("--inbox",    default="inbox")
    ap.add_argument("--raw",      default="data/raw")
    ap.add_argument("--db",       default="data/context.db")
    ap.add_argument("--exports",  default="exports")
    ap.add_argument("--engine",   default=os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"))
    ap.add_argument("--dpi",      default="400")
    ap.add_argument("--langs",    default="san+hin+eng")
    ap.add_argument("--sleep",    default="0.6",  help="seconds between translation API calls")
    ap.add_argument("--tr-limit", type=int, default=None, help="max passages to translate per run")
    ap.add_argument("--skip-ocr",     action="store_true")
    ap.add_argument("--skip-ingest",  action="store_true")
    ap.add_argument("--skip-translate", action="store_true")
    ap.add_argument("--skip-export",  action="store_true")
    args = ap.parse_args()

    lang_tries = [args.langs] + [l for l in ["san","hin","eng"] if l not in args.langs]

    print(f"\n{'#'*60}")
    print(f"  Sanskrit Pipeline — {args.doc}")
    print(f"  Engine: {args.engine}  DPI: {args.dpi}")
    print(f"{'#'*60}")

    stages = []

    if not args.skip_ocr:
        ok = ocr_missing(args.doc, args.inbox, args.raw, args.dpi, lang_tries)
        stages.append(("OCR", ok))
        if not ok:
            print("[ABORT] OCR failed — stopping pipeline.")
            sys.exit(1)

    if not args.skip_ingest:
        ok = ingest(args.doc, args.raw, args.db)
        stages.append(("Ingest", ok))

    if not args.skip_translate:
        ok = translate(args.doc, args.db, args.engine, args.tr_limit, args.sleep)
        stages.append(("Translate", ok))

    if not args.skip_export:
        ok = export_html(args.doc, args.db, args.exports)
        stages.append(("Export", ok))

    print(f"\n{'#'*60}")
    for name, ok in stages:
        print(f"  {name:12s}: {'OK' if ok else 'FAIL'}")
    print(f"{'#'*60}\n")
    all_ok = all(ok for _, ok in stages)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
