#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_source_finder.py — find higher-quality source texts on archive.org for a
scripture whose OCR is poor, so it can be re-sourced and re-translated (2026-08-27).

Why: the corpus quality ceiling is OCR noise, not the model. Archive.org hosts many
public-domain Sanskrit editions (DLI scans, Nirnaya Sagar, etc.), most with an OCR
full-text sidecar (`*_djvu.txt`) and/or a clean PDF you can re-OCR at high DPI. This
tool searches, ranks, lets you *preview the OCR text quality before committing*, and
downloads either the full-text or the PDF into a staging folder for the pipeline.

Stdlib only (urllib/json) — runs anywhere Python does; needs plain internet access.

Examples (run from the automaton/ root):
  python scripts/archive_source_finder.py --search "shatapatha brahmana" --lang sanskrit
  python scripts/archive_source_finder.py --preview <identifier>        # eyeball OCR quality
  python scripts/archive_source_finder.py --save-pdf  <identifier> --out downloads
  python scripts/archive_source_finder.py --save-text <identifier> --out sources
"""
from __future__ import annotations
import argparse, json, sys, os, pathlib, urllib.parse, urllib.request

UA = {"User-Agent": "SanskritAutomaton/1.0 (scholarly non-commercial translation)"}
BASE = "https://archive.org"


def _get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url: str, timeout: int = 45) -> dict:
    return json.loads(_get(url, timeout).decode("utf-8", "replace"))


def search(query: str, rows: int = 12, lang: str | None = None) -> list[dict]:
    q = f"({query}) AND language:({lang})" if lang else query
    parts = [("q", q), ("rows", str(rows)), ("output", "json"), ("sort[]", "downloads desc")]
    for f in ("identifier", "title", "year", "language", "mediatype"):
        parts.append(("fl[]", f))
    url = f"{BASE}/advancedsearch.php?" + "&".join(
        f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}" for k, v in parts)
    return _get_json(url).get("response", {}).get("docs", [])


def analyse(identifier: str) -> dict:
    """Fetch an item's file list and pick the best OCR-text and PDF sidecars."""
    meta = _get_json(f"{BASE}/metadata/{urllib.parse.quote(identifier)}")
    files = meta.get("files", [])
    md = meta.get("metadata", {})
    txt = pdf = None
    pdf_size = 0
    npages = None
    for f in files:
        fmt, name = (f.get("format") or ""), (f.get("name") or "")
        if (fmt == "DjVuTXT" or name.endswith("_djvu.txt")) and not txt:
            txt = name
        if (fmt == "Text PDF" or name.lower().endswith(".pdf")) and not pdf:
            pdf, pdf_size = name, int(f.get("size") or 0)
        if f.get("format") == "Djvu XML" and f.get("length"):
            try: npages = int(f["length"])
            except Exception: pass
    def one(v): return v[0] if isinstance(v, list) and v else v
    return {
        "identifier": identifier, "title": one(md.get("title")), "year": one(md.get("year")),
        "language": one(md.get("language")), "uploader": one(md.get("uploader")),
        "txt": txt, "pdf": pdf, "pdf_mb": round(pdf_size / 1e6, 1), "npages": npages,
        "txt_url": f"{BASE}/download/{identifier}/{txt}" if txt else None,
        "pdf_url": f"{BASE}/download/{identifier}/{pdf}" if pdf else None,
        "details": f"{BASE}/details/{identifier}",
    }


def _fmt_row(a: dict) -> str:
    flags = ("TXT" if a["txt"] else "---") + "/" + ("PDF" if a["pdf"] else "---")
    return (f"{a['identifier'][:38]:38s} {str(a.get('year') or ''):>5} "
            f"{(a.get('language') or '')[:10]:10s} {flags:8s} "
            f"{(str(a['pdf_mb'])+'MB' if a['pdf'] else ''):>8s}  {(a.get('title') or '')[:46]}")


def cmd_search(args):
    docs = search(args.search, rows=args.rows, lang=args.lang)
    if not docs:
        print("No results. Try broader keywords or drop --lang.")
        return
    print(f"{'identifier':38s} {'year':>5} {'language':10s} {'txt/pdf':8s} {'pdf':>8s}  title")
    print("-" * 118)
    for d in docs:
        try:
            print(_fmt_row(analyse(d["identifier"])))
        except Exception as e:
            print(f"{d.get('identifier','?')[:38]:38s}  (metadata error: {e})")
    print("\nNext: --preview <identifier> to judge OCR quality, then "
          "--save-pdf <identifier> --out downloads  (import + re-OCR)  or  "
          "--save-text <identifier> --out sources.")


def cmd_preview(args):
    a = analyse(args.preview)
    print(f"{a['identifier']}  |  {a.get('title')}  |  {a.get('year')}  |  {a.get('language')}")
    print(a["details"])
    if not a["txt"]:
        print("\n[no OCR text sidecar on this item — it has a PDF only]"
              if a["pdf"] else "\n[no text and no PDF found]")
        if a["pdf"]: print("PDF:", a["pdf_url"])
        return
    raw = _get(a["txt_url"]).decode("utf-8", "replace")
    n = len(raw)
    sample = raw[args.skip: args.skip + args.chars]
    print(f"\n--- OCR text sample ({n:,} chars total; showing {len(sample)} from offset {args.skip}) ---\n")
    print(sample)
    print("\n--- end sample ---")
    print("If this reads cleanly, --save-text will grab the whole thing; if it's noisy, "
          "prefer --save-pdf and re-OCR at 400-600 DPI.")


def _save(url: str, out_dir: str, filename: str) -> str:
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    dest = str(pathlib.Path(out_dir) / filename)
    data = _get(url, timeout=180)
    with open(dest, "wb") as fh:
        fh.write(data)
    return dest


def cmd_save_pdf(args):
    a = analyse(args.save_pdf)
    if not a["pdf"]:
        print("This item has no PDF. Try --save-text, or pick another identifier.")
        return
    dest = _save(a["pdf_url"], args.out, f"{a['identifier']}.pdf")
    print(f"Saved PDF -> {dest}  ({a['pdf_mb']} MB)")
    print("Import it via the dashboard (Choose PDF file / Import path to inbox) or "
          "'Import & Run Pipeline' — the splitter + OCR will handle it.")


def cmd_save_text(args):
    a = analyse(args.save_text)
    if not a["txt"]:
        print("This item has no OCR-text sidecar. Use --save-pdf and re-OCR instead.")
        return
    dest = _save(a["txt_url"], args.out, f"{a['identifier']}_djvu.txt")
    print(f"Saved OCR text -> {dest}")
    print("Provenance:", a["details"])
    print("(Text-file ingestion into passages is a follow-up; for now this lets you "
          "compare against the current source and decide.)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", help="search query, e.g. 'markandeya purana'")
    ap.add_argument("--lang", help="restrict by archive.org language facet, e.g. 'sanskrit'")
    ap.add_argument("--rows", type=int, default=12)
    ap.add_argument("--preview", help="identifier: print a sample of its OCR text")
    ap.add_argument("--skip", type=int, default=0, help="preview: start offset in the text")
    ap.add_argument("--chars", type=int, default=1600, help="preview: how many chars to show")
    ap.add_argument("--save-pdf", dest="save_pdf", help="identifier: download its PDF")
    ap.add_argument("--save-text", dest="save_text", help="identifier: download its OCR text")
    ap.add_argument("--out", default="downloads", help="output folder for --save-*")
    args = ap.parse_args()
    try:
        if args.search:        cmd_search(args)
        elif args.preview:     cmd_preview(args)
        elif args.save_pdf:    cmd_save_pdf(args)
        elif args.save_text:   cmd_save_text(args)
        else:                  ap.print_help()
    except urllib.error.URLError as e:
        print(f"[network] could not reach archive.org: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
