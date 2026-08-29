#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust OCR for page-PDFs -> JSONL (one record per page).

- Safe Windows prints (no UnicodeEncodeError)
- Multiple OCR retries: preproc variants, higher DPI, alt psm
- Writes UTF-8 JSONL compatible with ingest_jsonl_fast.py
- Honors POPPLER and Tesseract paths from env or args

Usage:
  python scripts/ocr_pdf.py --pdf inbox\\shiva_dhanur_veda_0001.pdf \
    --out data\\raw\\shiva_dhanur_veda_0001.jsonl --dpi 350 \
    --lang-tries san+hin+eng san hin eng
"""

from __future__ import annotations
import argparse, json, os, re, sys, tempfile
from pathlib import Path
from typing import List, Tuple, Optional

# ---- Safe prints on Windows -------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # py3.7+
except Exception:
    pass

# ---- Imports (lazy for nicer error messages) --------------------------------
def _need(mod, pip_name=None):
    try:
        __import__(mod)
    except Exception as e:
        n = pip_name or mod
        raise SystemExit(f"Missing dependency '{n}'. Install with:  pip install {n}\n{e}")

_need("PIL")
from PIL import Image, ImageOps, ImageFilter
_need("pytesseract", "pytesseract")
import pytesseract
_need("pdf2image", "pdf2image")
from pdf2image import convert_from_path

# Optional but recommended for better preproc
try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

# ---- Helpers ----------------------------------------------------------------
def _is_file(p: Optional[str]) -> bool:
    return bool(p and Path(p).is_file())

def _guess_poppler_bin() -> Optional[str]:
    # Typical Windows install
    for p in ("C:\\poppler\\bin", "C:\\Program Files\\poppler\\bin"):
        if Path(p).exists():
            return p
    return None

def _ensure_tesseract_path(tess_path: Optional[str]) -> None:
    if tess_path and Path(tess_path).is_file():
        pytesseract.pytesseract.tesseract_cmd = tess_path
        return
    # Common default on Windows
    for p in (
        "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
    ):
        if Path(p).is_file():
            pytesseract.pytesseract.tesseract_cmd = p
            return
    # Let pytesseract search PATH; if it fails later, the error will mention it.

# Devanagari LETTERS only: excludes digits (U+0966-096F) and dandas (U+0964-0965),
# which are page furniture rather than script content (2026-08-28).
_DEV_LETTER_RE = re.compile(r"[\u0900-\u0963\u0970-\u097F]")
_LAT_RE        = re.compile(r"[A-Za-z]")


def _render_pages(pdf_path: str, dpi: int, poppler_bin: Optional[str]) -> List[Image.Image]:
    kw = dict(dpi=dpi)
    if poppler_bin:
        kw["poppler_path"] = poppler_bin
    return convert_from_path(pdf_path, **kw)

def _pil_to_cv(img: Image.Image):
    import numpy as np
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

def _cv_to_pil(arr) -> Image.Image:
    from PIL import Image
    import numpy as np
    if len(arr.shape) == 2:
        return Image.fromarray(arr)
    raise ValueError("Expected a single-channel image")

def _preproc_variants(img: Image.Image) -> List[Tuple[str, Image.Image]]:
    """Return (name, image) variants from light to heavy processing."""
    out: List[Tuple[str, Image.Image]] = []

    # v1: autocontrast + slight sharpen
    v1 = ImageOps.autocontrast(img.convert("L"))
    v1 = v1.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=4))
    out.append(("autocontrast", v1))

    # v2: adaptive threshold (OpenCV) if available
    if cv2 is not None:
        g = _pil_to_cv(img)
        v2 = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 35, 11)
        out.append(("adaptive", _cv_to_pil(v2)))

        # v3: Otsu + mild denoise
        v3 = cv2.GaussianBlur(g, (3,3), 0)
        _, v3 = cv2.threshold(v3, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        out.append(("otsu", _cv_to_pil(v3)))
    else:
        # Fallback: simple grayscale + more aggressive sharpen
        v3 = v1.filter(ImageFilter.UnsharpMask(radius=1.6, percent=180, threshold=2))
        out.append(("sharpen", v3))

    return out

def _ocr_once(img: Image.Image, lang: str, psm: int = 6, oem: int = 1) -> str:
    config = f"--oem {oem} --psm {psm}"
    return pytesseract.image_to_string(img, lang=lang, config=config)

def _clean(s: str) -> str:
    if not s:
        return ""
    # collapse common weird whitespace
    return "\n".join([line.strip() for line in s.splitlines()]).strip()

def _write_jsonl(out_path: Path, records: List[dict]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# ---- Main OCR logic ----------------------------------------------------------
def ocr_pdf(
    pdf: str,
    out_jsonl: str,
    dpi: int,
    lang_tries: List[str],
    poppler_bin: Optional[str],
    tess_path: Optional[str],
    min_chars: int,
    max_dpi: int,
    min_dev_frac: float = 0.45,
) -> Tuple[int, int]:
    _ensure_tesseract_path(tess_path)
    pages = _render_pages(pdf, dpi, poppler_bin)
    records: List[dict] = []
    base_name = Path(pdf).name

    print(f"[ocr] tesseract={getattr(pytesseract.pytesseract,'tesseract_cmd','<on PATH>')}  "
          f"TESSDATA_PREFIX={os.environ.get('TESSDATA_PREFIX','<unset>')}")
    print(f"[ocr] poppler={poppler_bin or '<none>'}  dpi={dpi}")
    print(f"[ocr] lang tries: {lang_tries}")

    for i, pil in enumerate(pages, 1):
        text = ""
        used = {"dpi": dpi, "psm": 6, "preproc": "raw", "lang": lang_tries[0]}
        # QUALITY-AWARE acceptance (2026-08-28). Previously a candidate was accepted on
        # LENGTH ALONE, so a 400-DPI pass yielding 60+ chars of Latin/OCR garbage
        # ("DU Ashe de ४ ^+ ॥") was accepted immediately and broke out of every loop —
        # the 450/600-DPI escalation NEVER fired for exactly the pages that needed it.
        # Now a candidate must ALSO be Devanagari-dominant to be accepted early; every
        # attempt is scored, and if none qualifies we keep the BEST one seen rather than
        # the first long one. Set --min-dev-frac 0 to restore the old length-only rule.
        best_text, best_score, best_used = "", -1.0, dict(used)

        def _dev_frac(s: str) -> float:
            # letters only: exclude Devanagari digits (U+0966-096F) and dandas (U+0964-65)
            dev = len(_DEV_LETTER_RE.findall(s))
            lat = len(_LAT_RE.findall(s))
            tot = dev + lat
            return (dev / tot) if tot else 0.0

        # Try multiple passes
        tried = 0
        for cur_dpi in (dpi, min(450, max_dpi), max_dpi):
            if cur_dpi != dpi:
                # Re-render this page at a higher dpi
                try:
                    re_pages = _render_pages(pdf, cur_dpi, poppler_bin)
                    pil = re_pages[i-1]
                except Exception as e:
                    print(f"[warn] re-render at {cur_dpi} DPI failed for page {i}: {e}")
                    continue

            for lang in lang_tries:
                # Preproc ladder
                for pname, pimg in [("raw", pil)] + _preproc_variants(pil):
                    for psm in (6, 4):  # regular lines, then “block of text”
                        tried += 1
                        try:
                            cand = _clean(_ocr_once(pimg, lang=lang, psm=psm, oem=1))
                        except Exception as e:
                            print(f"[warn] OCR error p{ i } {pname}/{lang}/psm{psm}@{cur_dpi}: {e}")
                            cand = ""
                        # Score EVERY candidate: enough characters AND Devanagari-dominant.
                        cand_len = len(cand)
                        cand_dev = _dev_frac(cand)
                        # score favours a clean script mix, with length as a tie-breaker
                        cand_score = cand_dev * min(1.0, cand_len / max(20, min_chars))
                        if cand_score > best_score:
                            best_text, best_score = cand, cand_score
                            best_used = {"dpi": cur_dpi, "psm": psm, "preproc": pname, "lang": lang}
                        long_enough = cand_len >= max(20, min_chars)
                        good_script = (min_dev_frac <= 0.0) or (cand_dev >= min_dev_frac)
                        if long_enough and good_script:
                            text = cand
                            used = {"dpi": cur_dpi, "psm": psm, "preproc": pname, "lang": lang}
                            break
                    if text:
                        break
                if text:
                    break
            if text:
                break

        # Nothing satisfied BOTH length and script quality after escalating to max DPI:
        # keep the best-scoring attempt rather than discarding the work (and rather than
        # the old behaviour of silently keeping the first merely-long one).
        if not text and best_text:
            text = best_text
            used = best_used
            print(f"page {i}: no candidate passed the quality gate; keeping best "
                  f"(dev={_dev_frac(text):.2f}, dpi={used.get('dpi')}, preproc={used.get('preproc')})")

        # Always record something (even empty), so downstream knows the page exists
        print(f"page {i}: {len(text)} chars (from {base_name})  "
              f"dev={_dev_frac(text):.2f} dpi={used.get('dpi')} preproc={used.get('preproc')}")
        rec = {
            "engine": "tesseract",
            "page_no": i,
            "text": text,
            "meta": used,
            "src_pdf": base_name,
        }
        records.append(rec)

    _write_jsonl(Path(out_jsonl), records)
    print(f"OCR wrote {len(records)} pages -> {out_jsonl}")
    nonempty = sum(1 for r in records if r["text"])
    return len(records), nonempty

# ---- CLI ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="OCR a single-page PDF (or multi) to JSONL (one record per page).")
    ap.add_argument("--pdf", required=True, help="Input PDF (usually 1 page)")
    ap.add_argument("--out", required=True, help="Output JSONL file")
    ap.add_argument("--dpi", type=int, default=350, help="Initial DPI for rasterizing (default: 350)")
    ap.add_argument("--max-dpi", type=int, default=600, help="Upper DPI bound for retries (default: 600)")
    ap.add_argument("--lang-tries", nargs="+", default=["san+hin+eng", "san", "hin", "eng"],
                    help="Language tries in order (Tesseract -l values). Default: san+hin+eng san hin eng")
    ap.add_argument("--poppler-bin", default=os.environ.get("POPPLER_BIN") or os.environ.get("POPPLER_PATH"),
                    help="Path to Poppler 'bin' dir (Windows). If omitted, will try to guess.")
    ap.add_argument("--tesseract", default=os.environ.get("TESSERACT_PATH"),
                    help="Full path to tesseract.exe (Windows). Otherwise uses PATH.")
    ap.add_argument("--min-dev-frac", type=float, default=0.45,
                    help="Minimum Devanagari fraction for a candidate to be accepted early; "
                         "below this the page escalates to higher DPI. 0 = old length-only rule "
                         "(default: 0.45)")
    ap.add_argument("--min-chars", type=int, default=60,
                    help="Minimum acceptable chars for a page before retry escalation (default: 60)")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    poppler_bin = args.poppler_bin or _guess_poppler_bin()
    total, nonempty = ocr_pdf(
        str(pdf),
        args.out,
        dpi=args.dpi,
        lang_tries=args.lang_tries,
        poppler_bin=poppler_bin,
        tess_path=args.tesseract,
        min_chars=args.min_chars,
        min_dev_frac=args.min_dev_frac,
        max_dpi=args.max_dpi,
    )
    if nonempty < total:
        print(f"[warn] {total - nonempty} page(s) ended up empty after all retries.")

if __name__ == "__main__":
    main()
