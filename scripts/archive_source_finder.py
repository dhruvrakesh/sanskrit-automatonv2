#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_source_finder.py — find and VET higher-quality source texts for a scripture
whose OCR is poor, so it can be re-sourced and re-translated (2026-08-27).

Sourcing policy (enterprise, surgical):
  1. PREFER a pure Sanskrit (Devanagari) e-text. Cleanest of all is GRETIL
     (gretil.sub.uni-goettingen.de) and sanskritdocuments.org — Unicode Devanagari,
     no OCR. Check those FIRST for the text you need; this tool prints the exact
     GRETIL search URL for you.
  2. archive.org is the fallback. Accept its data ONLY after measuring script purity:
     this tool computes the Devanagari ratio of the candidate's OCR text and gives a
     verdict (ACCEPT / CAUTION / REJECT). Bilingual "Sanskrit-Hindi" scans and
     Latin-heavy OCR are rejected by default — they pollute a Sanskrit corpus.
  3. Never ingest un-previewed. `--save-text` refuses below --min-dev unless --force.

Stdlib only (urllib/json). Runs anywhere Python does; needs plain internet.

Examples (from the automaton/ root):
  python scripts/archive_source_finder.py --gretil "markandeya purana"     # preferred first stop
  python scripts/archive_source_finder.py --search "markandeya purana" --lang sanskrit
  python scripts/archive_source_finder.py --preview <identifier>           # purity verdict
  python scripts/archive_source_finder.py --save-text <identifier> --out sources   # gated by purity
  python scripts/archive_source_finder.py --save-pdf  <identifier> --out downloads # for re-OCR
"""
from __future__ import annotations
import argparse, json, sys, pathlib, urllib.parse, urllib.request, urllib.error

UA = {"User-Agent": "SanskritAutomaton/1.0 (scholarly non-commercial)"}
BASE = "https://archive.org"
MIN_DEV_DEFAULT = 0.85   # accept as "pure Sanskrit" only at/above this Devanagari ratio


def _q(s: str) -> str:
    """URL-encode a path segment (archive.org filenames contain spaces/unicode)."""
    return urllib.parse.quote(s, safe="")


def _get(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def _get_json(url: str, timeout: int = 60) -> dict:
    return json.loads(_get(url, timeout).decode("utf-8", "replace"))


def dev_ratio(text: str) -> float:
    """Fraction of script-bearing characters that are Devanagari (U+0900–U+097F).
    Latin letters count against it; whitespace/digits/punct are ignored. 1.0 = pure
    Devanagari, ~0.5 = half-Latin (noisy OCR or bilingual), 0.0 = no Sanskrit."""
    dev = lat = 0
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            dev += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            lat += 1
    tot = dev + lat
    return (dev / tot) if tot else 0.0


def verdict(ratio: float, language: str | None) -> str:
    bi = language and ("hindi" in language.lower() or "-h" in language.lower())
    if ratio >= MIN_DEV_DEFAULT and not bi:
        return "ACCEPT   (clean Sanskrit)"
    if ratio >= 0.6:
        return "CAUTION  (mixed/bilingual or noisy OCR — preview more before use)"
    return "REJECT   (Latin-heavy / not usable Sanskrit source)"


def search(query: str, rows: int = 12, lang: str | None = None) -> list[dict]:
    q = f"({query}) AND language:({lang})" if lang else query
    parts = [("q", q), ("rows", str(rows)), ("output", "json"), ("sort[]", "downloads desc")]
    for f in ("identifier", "title", "year", "language", "mediatype"):
        parts.append(("fl[]", f))
    url = f"{BASE}/advancedsearch.php?" + "&".join(f"{_q(k)}={_q(v)}" for k, v in parts)
    return _get_json(url).get("response", {}).get("docs", [])


def analyse(identifier: str) -> dict:
    meta = _get_json(f"{BASE}/metadata/{_q(identifier)}")
    files, md = meta.get("files", []), meta.get("metadata", {})
    txt = pdf = None
    pdf_size = 0
    for f in files:
        fmt, name = (f.get("format") or ""), (f.get("name") or "")
        if (fmt == "DjVuTXT" or name.endswith("_djvu.txt")) and not txt:
            txt = name
        if (fmt == "Text PDF" or name.lower().endswith(".pdf")) and not pdf:
            pdf, pdf_size = name, int(f.get("size") or 0)
    def one(v): return v[0] if isinstance(v, list) and v else v
    lang = one(md.get("language"))
    return {
        "identifier": identifier, "title": one(md.get("title")), "year": one(md.get("year")),
        "language": lang, "txt": txt, "pdf": pdf, "pdf_mb": round(pdf_size / 1e6, 1),
        "txt_url": f"{BASE}/download/{_q(identifier)}/{_q(txt)}" if txt else None,
        "pdf_url": f"{BASE}/download/{_q(identifier)}/{_q(pdf)}" if pdf else None,
        "details": f"{BASE}/details/{identifier}",
    }


def _row(a: dict) -> str:
    flags = ("TXT" if a["txt"] else "---") + "/" + ("PDF" if a["pdf"] else "---")
    lang = (a.get("language") or "")[:12]
    return (f"{a['identifier'][:36]:36s} {str(a.get('year') or ''):>5} {lang:12s} "
            f"{flags:8s} {(str(a['pdf_mb'])+'MB' if a['pdf'] else ''):>8s}  {(a.get('title') or '')[:40]}")


def cmd_gretil(args):
    q = urllib.parse.quote(args.gretil)
    print("PREFERRED pure-Sanskrit sources — check these FIRST (Unicode Devanagari, no OCR):")
    print(f"  GRETIL search  : https://www.google.com/search?q=site:gretil.sub.uni-goettingen.de+{q}")
    print(f"  SanskritDocs   : https://www.google.com/search?q=site:sanskritdocuments.org+{q}")
    print("Download the Devanagari .txt/.xml from there and ingest it as text (highest fidelity).\n"
          "Only if the text is unavailable there, fall back to --search on archive.org and vet it.")


def cmd_search(args):
    docs = search(args.search, rows=args.rows, lang=args.lang)
    if not docs:
        print("No results. Broaden keywords or drop --lang."); return
    print(f"{'identifier':36s} {'year':>5} {'language':12s} {'txt/pdf':8s} {'pdf':>8s}  title")
    print("-" * 116)
    for d in docs:
        try:    print(_row(analyse(d["identifier"])))
        except Exception as e: print(f"{d.get('identifier','?')[:36]:36s}  (metadata error: {e})")
    print("\nNote: 'Sanskrit-Hindi' items are BILINGUAL — reject unless you specifically want Hindi.\n"
          "Next: --preview <identifier> for a Devanagari-purity verdict before you commit.")


def cmd_preview(args):
    a = analyse(args.preview)
    print(f"{a['identifier']}  |  {a.get('title')}  |  {a.get('year')}  |  language={a.get('language')}")
    print(a["details"])
    if not a["txt"]:
        print("\n[no OCR-text sidecar]" + ("  PDF: " + a["pdf_url"] if a["pdf"] else "  (no PDF either)"))
        return
    raw = _get(a["txt_url"]).decode("utf-8", "replace")
    ratio = dev_ratio(raw)
    print(f"\nOCR text: {len(raw):,} chars   Devanagari ratio: {ratio:.2f}   ->  {verdict(ratio, a.get('language'))}")
    sample = raw[args.skip: args.skip + args.chars]
    print(f"\n--- sample (offset {args.skip}, {len(sample)} chars) ---\n{sample}\n--- end ---")
    print("Rule of thumb: ACCEPT only pure Devanagari; if CAUTION/REJECT prefer GRETIL or --save-pdf + re-OCR.")


def _save(url: str, out_dir: str, filename: str) -> str:
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    dest = str(pathlib.Path(out_dir) / filename)
    with open(dest, "wb") as fh:
        fh.write(_get(url, timeout=240))
    return dest


def cmd_save_text(args):
    a = analyse(args.save_text)
    if not a["txt"]:
        print("No OCR-text sidecar. Use --save-pdf and re-OCR instead."); return
    raw = _get(a["txt_url"]).decode("utf-8", "replace")
    ratio = dev_ratio(raw)
    print(f"Devanagari ratio: {ratio:.2f}  ->  {verdict(ratio, a.get('language'))}")
    if ratio < args.min_dev and not args.force:
        print(f"REFUSED: purity {ratio:.2f} < --min-dev {args.min_dev}. This would pollute the corpus.\n"
              f"Prefer GRETIL, or pass --force only if you have verified the text by eye."); return
    dest = _save(a["txt_url"], args.out, f"{a['identifier']}_djvu.txt")
    print(f"Saved -> {dest}\nProvenance: {a['details']}\n"
          "(Text->passages ingestion is the next increment; this stages a vetted source.)")


def cmd_save_pdf(args):
    a = analyse(args.save_pdf)
    if not a["pdf"]:
        print("No PDF on this item. Try --save-text or another identifier."); return
    dest = _save(a["pdf_url"], args.out, f"{a['identifier']}.pdf")
    print(f"Saved PDF -> {dest}  ({a['pdf_mb']} MB)\n"
          "Import via the dashboard (Choose PDF / Import path) — splitter + OCR will handle it.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gretil", help="print preferred pure-Sanskrit source URLs for this title, then stop")
    ap.add_argument("--search", help="archive.org search query")
    ap.add_argument("--lang", help="archive.org language facet, e.g. 'sanskrit'")
    ap.add_argument("--rows", type=int, default=12)
    ap.add_argument("--preview", help="identifier: purity verdict + text sample")
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--chars", type=int, default=1600)
    ap.add_argument("--save-text", dest="save_text", help="identifier: download OCR text (purity-gated)")
    ap.add_argument("--save-pdf", dest="save_pdf", help="identifier: download PDF for re-OCR")
    ap.add_argument("--out", default="downloads")
    ap.add_argument("--min-dev", type=float, default=MIN_DEV_DEFAULT,
                    help=f"minimum Devanagari ratio to accept text (default {MIN_DEV_DEFAULT})")
    ap.add_argument("--force", action="store_true", help="override the purity gate (verify by eye first)")
    args = ap.parse_args()
    try:
        if args.gretil:        cmd_gretil(args)
        elif args.search:      cmd_search(args)
        elif args.preview:     cmd_preview(args)
        elif args.save_text:   cmd_save_text(args)
        elif args.save_pdf:    cmd_save_pdf(args)
        else:                  ap.print_help()
    except urllib.error.URLError as e:
        print(f"[network] could not reach archive.org: {e}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    main()
