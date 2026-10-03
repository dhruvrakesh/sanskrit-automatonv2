#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
export_pdf.py  (2026-10-03)  EXPORT_PDF_2026_10_03

Prints an export_html.py edition (English / Hindi / trilingual) to PDF with the
browser engine, adding a print stylesheet: A4 or B5 pages, running title,
"page / pages" numbers, a title page and contents on their own pages, verses
kept whole across page breaks, column headings shown once per section.

WHY: the HTML editions read better than the Booksmith PDFs. Booksmith renders
with ReportLab, and ReportLab shapes Devanagari (conjuncts, pre-base vowel signs)
only when the optional `uharfbuzz` package is installed - it is not installed in
the Booksmith venv. A browser engine shapes Devanagari with HarfBuzz always, and
it renders the same HTML the reader already approved.

The print styles apply only to print. The HTML file on disk and its on-screen
layout are not changed: a temporary copy with the print styles is written to
exports\\_print\\ and printed.

Engine, in order: Playwright Chromium (if installed), else Microsoft Edge or
Google Chrome in headless mode (installed on Windows by default; page numbers
need Chromium 131 or later).

  python scripts\\export_pdf.py exports\\Mallapurana_1-137_tri.html
  python scripts\\export_pdf.py exports\\Mallapurana_1-137_hi.html --size B5
  python scripts\\export_pdf.py --glob "exports\\*_tri.html"
"""
from __future__ import annotations

import argparse
import glob as globmod
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MARK = "EXPORT_PDF_2026_10_03"
SIZES = {"A4": "A4", "B5": "176mm 250mm", "A5": "A5", "LETTER": "letter"}

PRINT_CSS = """
/* EXPORT_PDF_2026_10_03 - print only; the screen layout is unchanged. */
@page { size: %(size)s; margin: 16mm 14mm 18mm 14mm;
  @top-center { content: "%(title)s"; font: italic 8.5pt 'Noto Serif','Iowan Old Style',Georgia,serif; color: #7a7a7a; }
  @bottom-center { content: counter(page) " / " counter(pages); font: 8.5pt 'Noto Serif',Georgia,serif; color: #7a7a7a; } }
@page :first { @top-center { content: none; } @bottom-center { content: none; } }
@media print {
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { background: #fff; max-width: none; margin: 0; padding: 0; font-size: 10pt; line-height: 1.5; }
  .titlepage { break-after: page; border-bottom: none; padding-top: 30mm; }
  .titlepage h1 { font-size: 24pt; }
  .toc { break-after: page; break-inside: auto; background: none; border: none; padding: 0; }
  .toc ol { columns: %(toc_cols)d; column-gap: 6mm; font-size: 8.5pt; }
  .chapter { break-inside: auto; margin: 0 0 6mm; }
  .chapter > h2 { break-after: avoid; font-size: 13pt; margin: 0 0 3mm; }
  .verse { break-inside: avoid; margin: 0 0 3.2mm; padding-left: 9mm; }
  .vref { width: 8mm; font-size: 6.5pt; }
  .pair { gap: 4mm; }
  .pair .col h4 { font-size: 6.5pt; margin: 0 0 1mm; }
  .chapter .verse ~ .verse .col h4 { display: none; }
  .verse .sa { font-size: 9.5pt; line-height: 1.55; }
  .verse .iast { font-size: 7.5pt; }
  .verse .hi { font-size: 9.5pt; line-height: 1.7; }
  .verse .en { font-size: 9.5pt; }
  .footnotes { break-inside: auto; font-size: 7.5pt; }
  .footnotes li { break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/chromium", "/usr/bin/google-chrome",
]


def build_print_html(src: str, size: str = "A4") -> str:
    """The source HTML with the print stylesheet appended to <head>."""
    m = re.search(r"<title>(.*?)</title>", src, re.S | re.I)
    title = html.unescape(m.group(1)).strip() if m else ""
    title = title.replace("\\", "").replace('"', "'").replace("\n", " ")[:120]
    css = PRINT_CSS % {"size": SIZES.get(size.upper(), "A4"), "title": title,
                       "toc_cols": 3 if size.upper() in ("B5", "A5") else 4}
    tag = "<style>" + css + "</style>"
    if MARK in src:
        return src
    i = src.lower().find("</head>")
    return (src[:i] + tag + src[i:]) if i >= 0 else (tag + src)


def find_browser(explicit: str | None = None, candidates=None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() else None
    for c in (candidates if candidates is not None else BROWSERS):
        if Path(c).exists():
            return c
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        w = shutil.which(name)
        if w:
            return w
    return None


def _print_playwright(uri: str, out: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(uri, wait_until="load")
            pg.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
            b.close()
        return out.exists() and out.stat().st_size > 0
    except Exception as e:
        print("  [playwright] %s: %s" % (type(e).__name__, str(e)[:160]))
        return False


def _print_browser(exe: str, uri: str, out: Path, timeout: int) -> bool:
    prof = tempfile.mkdtemp(prefix="export_pdf_profile_")   # own profile: never hands off to a running browser
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--no-pdf-header-footer", "--user-data-dir=" + prof, "--print-to-pdf=" + str(out), uri]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")   # Linux root (containers) only; never needed on Windows
    try:
        subprocess.run(cmd, timeout=timeout, capture_output=True)
    except subprocess.TimeoutExpired:
        print("  [browser] timed out after %ds" % timeout)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    return out.exists() and out.stat().st_size > 0


def export_one(src_path: Path, out: Path | None, size: str, browser: str | None, timeout: int,
               engine: str = "auto") -> Path | None:
    src = src_path.read_text(encoding="utf-8")
    work = src_path.parent / "_print"
    work.mkdir(parents=True, exist_ok=True)
    tmp = work / (src_path.stem + ".print.html")
    tmp.write_text(build_print_html(src, size), encoding="utf-8")
    out = out or src_path.with_suffix(".pdf")
    if out.exists():
        out.unlink()
    uri = tmp.resolve().as_uri()
    t0 = time.time()
    ok = False
    if engine in ("auto", "playwright"):
        ok = _print_playwright(uri, out)
    if not ok and engine in ("auto", "browser"):
        exe = find_browser(browser)
        if not exe:
            print("  FAIL: no Playwright and no Edge/Chrome found. Pass --browser <path to msedge.exe>.")
            return None
        ok = _print_browser(exe, uri, out, timeout)
    if not ok:
        print("  FAIL: the engine produced no PDF for %s" % src_path.name)
        return None
    pages = ""
    try:
        from pypdf import PdfReader
        pages = ", %d pages" % len(PdfReader(str(out)).pages)
    except Exception:
        pass
    print("  %s -> %s  (%.1f s, %.0f KB%s)" % (src_path.name, out, time.time() - t0, out.stat().st_size / 1024, pages))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Print export_html editions to PDF with a browser engine")
    ap.add_argument("html", nargs="?", help="an exported .html edition")
    ap.add_argument("--glob", dest="globpat", default=None)
    ap.add_argument("--out", default=None, help="output .pdf (single file only)")
    ap.add_argument("--size", default="A4", choices=sorted(SIZES))
    ap.add_argument("--engine", default="auto", choices=["auto", "playwright", "browser"])
    ap.add_argument("--browser", default=None, help="path to msedge.exe / chrome.exe")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    files = [Path(args.html)] if args.html else [Path(p) for p in sorted(globmod.glob(args.globpat or ""))]
    files = [f for f in files if f.suffix.lower() == ".html" and "_print" not in f.parts]
    if not files:
        print("FAIL: no .html edition given (path or --glob)."); return 2
    print("EXPORT PDF  %d file(s)  size=%s  engine=%s  %s" % (len(files), args.size, args.engine, MARK))
    bad = 0
    for f in files:
        if not f.exists():
            print("  missing: %s" % f); bad += 1; continue
        r = export_one(f, Path(args.out) if (args.out and len(files) == 1) else None,
                       args.size, args.browser, args.timeout, args.engine)
        bad += 0 if r else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
