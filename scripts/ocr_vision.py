#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_vision.py - LLM-vision OCR for pages Tesseract cannot read (2026-08-28).

WHY THIS EXISTS (measured, not assumed):
  Tesseract misreads pre-1900 Devanagari founts (e.g. the 1861 Bibliotheca Indica) into
  confident but WRONG Devanagari - "प्राख्डिल्यग्रतखनीयं भाव्यम् [अव्शब्यान््र]". An A/B at
  400 vs 600 DPI with every preprocessing variant produced dev=0.98 both times: no gain
  (see BENCHMARKS.md). The scans themselves are clean and perfectly legible - a vision
  model reads them without difficulty. So the fix is a better READER, not a better scan.

Writes the SAME JSONL record shape as ocr_pdf.py, so the existing ingest path
(ingest_jsonl_fast.py) consumes it unchanged. engine='gemini-vision' marks provenance.

COST-AWARE: dry-run by default (renders + reports, no API call). Roughly $0.0004/page on
flash - a 300-page book is about $0.12. Use --limit to bound any run.

  python scripts/ocr_vision.py --pdf inbox\\AphorismsOfSandilya_0050.pdf --out tmp.jsonl
  python scripts/ocr_vision.py --pdf inbox\\AphorismsOfSandilya_0050.pdf --out tmp.jsonl --yes
  python scripts/ocr_vision.py --glob "inbox\\AphorismsOfSandilya_*.pdf" --outdir data\\raw --yes
"""
from __future__ import annotations
import argparse, glob as globmod, io, json, os, re, sys, time
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

DEV_LETTER_RE = re.compile(r"[ऀ-ॣ॰-ॿ]")
LAT_RE        = re.compile(r"[A-Za-z]")
COST_PER_PAGE = 0.0004          # rough flash vision estimate, for the pre-run report
MODEL_DEFAULT = "gemini-2.5-flash"

PROMPT = (
    "You are transcribing a page from a printed Sanskrit book (19th-century Indian press, "
    "Devanagari with occasional Latin footnote markers).\n"
    "Transcribe EXACTLY what is printed. Rules:\n"
    "1. Output the Devanagari text verbatim, preserving line breaks, dandas (। ॥) and "
    "verse numbers as printed.\n"
    "2. Do NOT translate, explain, correct, normalise or add anything.\n"
    "3. If a portion of the page is printed in English (running heads, footnotes, an "
    "English translation section), transcribe it as English, in place.\n"
    "4. If a character is genuinely illegible use a single '?' - never guess a whole word.\n"
    "5. Ignore page furniture that is not text (library stamps, scan watermarks).\n"
    "6. Output ONLY the transcription. No preamble, no commentary, no code fences."
)


def dev_frac(s: str) -> float:
    d, l = len(DEV_LETTER_RE.findall(s or "")), len(LAT_RE.findall(s or ""))
    t = d + l
    return d / t if t else 0.0


def render_page(pdf: str, dpi: int, poppler_bin: str | None):
    from pdf2image import convert_from_path
    kw = dict(dpi=dpi)
    if poppler_bin:
        kw["poppler_path"] = poppler_bin
    pages = convert_from_path(pdf, **kw)
    if not pages:
        raise RuntimeError(f"no pages rendered from {pdf}")
    return pages[0]


def transcribe(img, model_name: str, timeout_s: int = 120) -> str:
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=8192)
    gm = genai.GenerativeModel(model_name=model_name, generation_config=cfg,
                               system_instruction=PROMPT)
    resp = gm.generate_content([{"mime_type": "image/png", "data": buf.getvalue()}],
                               request_options={"timeout": timeout_s})
    try:
        txt = (resp.text or "").strip()
    except Exception:
        txt = ""
    if txt.startswith("```"):
        txt = re.sub(r"^```[A-Za-z]*\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt).strip()
    return txt


def page_no_from_name(name: str) -> int:
    m = re.search(r"_(\d{4})\.pdf$", name, re.IGNORECASE)
    return int(m.group(1)) if m else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", help="single page-PDF")
    ap.add_argument("--glob", dest="globpat", help="glob of page-PDFs, e.g. \"inbox\\Doc_*.pdf\"")
    ap.add_argument("--out", help="output JSONL (single --pdf mode)")
    ap.add_argument("--outdir", help="output dir (glob mode); one .jsonl per page-PDF")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--dpi", type=int, default=300, help="render DPI sent to the model (300 is plenty)")
    ap.add_argument("--poppler-bin", default=os.environ.get("POPPLER_BIN") or os.environ.get("POPPLER_PATH"))
    ap.add_argument("--limit", type=int, default=0, help="cap pages processed (0 = no cap)")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--skip-existing", action="store_true", help="glob mode: skip pages whose .jsonl exists")
    ap.add_argument("--yes", action="store_true", help="actually call the API (default: dry-run)")
    args = ap.parse_args()

    if not args.pdf and not args.globpat:
        ap.error("give --pdf <file> or --glob <pattern>")

    targets = [args.pdf] if args.pdf else sorted(globmod.glob(args.globpat))
    if args.outdir and args.skip_existing:
        targets = [t for t in targets
                   if not (Path(args.outdir) / (Path(t).stem + ".jsonl")).exists()]
    if args.limit:
        targets = targets[:args.limit]
    if not targets:
        print("nothing to do."); return

    print(f"pages: {len(targets)}   model: {args.model}   dpi: {args.dpi}   "
          f"est. cost: ${len(targets)*COST_PER_PAGE:.3f}   ({'LIVE' if args.yes else 'DRY-RUN'})")
    if not args.yes:
        for t in targets[:10]:
            print(f"  would transcribe: {Path(t).name}")
        if len(targets) > 10:
            print(f"  ... and {len(targets)-10} more")
        print("Re-run with --yes to transcribe. Nothing was called or written.")
        return

    ok = err = 0
    for n, pdf in enumerate(targets, 1):
        name = Path(pdf).name
        try:
            img = render_page(pdf, args.dpi, args.poppler_bin)
            text = transcribe(img, args.model)
            rec = {
                "engine": f"gemini-vision:{args.model}",
                "page_no": page_no_from_name(name),
                "text": text,
                "meta": {"dpi": args.dpi, "model": args.model, "dev": round(dev_frac(text), 3)},
                "src_pdf": name,
            }
            out_path = Path(args.out) if args.pdf else Path(args.outdir) / (Path(pdf).stem + ".jsonl")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ok += 1
            print(f"  [{n}/{len(targets)}] {name}: {len(text)} chars  dev={dev_frac(text):.2f} -> {out_path}")
        except Exception as e:
            err += 1
            print(f"  [{n}/{len(targets)}] {name}: ERROR {type(e).__name__}: {e}")
        time.sleep(args.sleep)

    print(f"\nDone. transcribed={ok} errors={err}")
    if args.outdir:
        print("Next: ingest with  python scripts\\ingest_jsonl_fast.py --doc <CODE> "
              f"--glob \"{args.outdir}\\<CODE>_*.jsonl\" --db data\\context.db")


if __name__ == "__main__":
    main()
