#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wisdomlib_to_jsonl.py — Adapter: wisdomlib_archive pages -> automaton ingest JSONL.

PURELY ADDITIVE. Touches nothing else in the pipeline. It reads the archive
produced by D:\\wisdomlib\\scraper.py and emits page-JSONL files that
scripts/ingest_jsonl_fast.py already understands, so the existing
Ingest -> Translate -> Export chain runs unchanged (OCR stage is skipped —
the archive is already text).

Contract honoured (from ingest_jsonl_fast.py, verified 2026-07-18):
  * one JSONL file per page, filename ends _NNNN.jsonl  (page no = trailing digits)
  * each line is a JSON object; only "text" is required; "page_no" honoured
  * ingest normalizes, verse-segments, IAST-transliterates, scores quality
  * re-ingest never overwrites existing translations (ON CONFLICT keeps them)

What it extracts (default --mode sanskrit):
  Devanagari and dense-IAST blocks only — i.e. the public-domain source text.
  English prose (wisdomlib's own copyrighted translations/commentary) is
  deliberately NOT exported. Use it as local reference only.
  Book index pages (tables of contents) are skipped unless --include-index.

Usage (from sanskrit-automatonv2/ root):
  python scripts/wisdomlib_to_jsonl.py --archive D:/wisdomlib/wisdomlib_archive --list-books
  python scripts/wisdomlib_to_jsonl.py --archive D:/wisdomlib/wisdomlib_archive --dry-run
  python scripts/wisdomlib_to_jsonl.py --archive D:/wisdomlib/wisdomlib_archive --book buddha-carita
  python scripts/wisdomlib_to_jsonl.py --archive D:/wisdomlib/wisdomlib_archive --out data/raw

Then ingest as usual, e.g.:
  python scripts/ingest_jsonl_fast.py --doc wl_buddha_carita ^
      --glob "data/raw/wl_buddha_carita_*.jsonl" --category wisdomlib

Dependencies: beautifulsoup4 (already required by the wisdomlib scraper;
`pip install beautifulsoup4` in the automaton venv if missing). Falls back to
page.txt with boilerplate stripping when bs4 or page.html is unavailable.
"""

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

# ----------------------------------------------------------------------------
# Script detection
# ----------------------------------------------------------------------------

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
# IAST diacritics that essentially never occur in plain English prose
IAST_RE = re.compile(r"[āīūṛṝḷḹṃḥśṣṭḍṇñṅĀĪŪṚṜḶṂḤŚṢṬḌṆÑṄ]")
# Danda / double-danda — strong verse markers
DANDA_RE = re.compile(r"[।॥]")

# Navigation / boilerplate lines seen at the top of every page.txt
BOILERPLATE_LINES = {
    "home", "about", "contact", "newsletter", "shop", "links", "photos",
    "tools", "support me on patreon", "resources", "buddhism", "hinduism",
    "jainism", "india history", "shaivism", "shaktism", "vaishnavism",
    "pancaratra", "vedic hinduism", "theravada", "mahayana",
    "tibetan buddhism", "arts", "arthashastra", "ayurveda", "dharmashastra",
    "jyotisha", "kavya", "linguistics", "natyashastra", "philosophy",
    "purana", "rasa-shastra", "shilpa-shastra", "vastu-shastra", "yoga",
    "ganita", "sanskrit", "pali", "marathi", "science", "various traditions",
    "all glossaries", "subhashita", "buy now!", "buy relevant books",
    "< previous", "next >", "go directly to:", "footnotes", "like what you read?",
    "consider supporting this website:", "donate on patreon", "donate on ko-fi",
}

BOOK_URL_RE = re.compile(
    r"wisdomlib\.org/([^/]+)/book/([^/]+)(?:/d/doc(\d+)\.html)?", re.IGNORECASE
)


def sanskrit_stats(text: str) -> Tuple[int, int, int]:
    """Return (devanagari_chars, iast_diacritic_chars, danda_marks)."""
    return (
        len(DEVANAGARI_RE.findall(text)),
        len(IAST_RE.findall(text)),
        len(DANDA_RE.findall(text)),
    )


def line_is_sanskrit(line: str, min_ratio: float) -> bool:
    """A line qualifies if Devanagari dominates, or IAST diacritics are dense."""
    stripped = line.strip()
    if not stripped:
        return False
    n = len(stripped)
    dev, iast, danda = sanskrit_stats(stripped)
    if dev and (dev / n) >= min_ratio:
        return True
    if danda and (dev or iast):
        return True
    # IAST verse lines: diacritics are sparse by nature; 3+ marks in a short
    # line, or >2% density, is a strong signal
    if iast >= 3 and (iast / n) >= 0.02:
        return True
    return False


# ----------------------------------------------------------------------------
# Content extraction
# ----------------------------------------------------------------------------

def extract_content_html(html_path: pathlib.Path) -> Optional[str]:
    """Pull the article body out of page.html (div.pageContent)."""
    if not HAVE_BS4 or not html_path.exists():
        return None
    try:
        soup = BeautifulSoup(
            html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser"
        )
    except Exception:
        return None
    node = soup.find("div", class_="pageContent") or soup.find("article")
    if node is None:
        return None
    return node.get_text(separator="\n", strip=True)


def extract_content_txt(txt_path: pathlib.Path) -> Optional[str]:
    """Fallback: page.txt minus known navigation boilerplate."""
    if not txt_path.exists():
        return None
    lines = txt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    kept = [ln for ln in lines if ln.strip().lower() not in BOILERPLATE_LINES]
    return "\n".join(kept)


def sanskrit_blocks(content: str, min_ratio: float, min_block_chars: int) -> List[str]:
    """Group consecutive Sanskrit-qualifying lines into blocks (one per record).

    A single intervening non-Sanskrit line (e.g. a verse number) does not
    break a block; two consecutive misses do.
    """
    blocks: List[str] = []
    current: List[str] = []
    miss_streak = 0
    for line in content.splitlines():
        if line_is_sanskrit(line, min_ratio):
            current.append(line.strip())
            miss_streak = 0
        else:
            miss_streak += 1
            if current and miss_streak >= 2:
                block = "\n".join(current).strip()
                if len(block) >= min_block_chars:
                    blocks.append(block)
                current = []
    if current:
        block = "\n".join(current).strip()
        if len(block) >= min_block_chars:
            blocks.append(block)
    return blocks


# ----------------------------------------------------------------------------
# Archive walking
# ----------------------------------------------------------------------------

def doc_code_for_book(book_slug: str, prefix: str = "wl_") -> str:
    """wisdomlib book slug -> automaton doc code (safe for filenames/globs)."""
    slug = book_slug.lower()
    slug = re.sub(r"^(the|a|an)-", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    # Trailing digits would collide with the _NNNN page-number convention
    # used by ingest's filename parser, so guard them with a suffix.
    if re.search(r"\d$", slug):
        slug += "_x"
    return (prefix + slug)[:64]


def scan_archive(archive: pathlib.Path) -> List[Dict]:
    """Read every pages/*/meta.json; return page records with book grouping."""
    pages_dir = archive / "pages"
    if not pages_dir.is_dir():
        sys.exit(f"ERROR: {pages_dir} not found — is --archive correct?")
    out = []
    for meta_path in sorted(pages_dir.glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        url = meta.get("url", "")
        m = BOOK_URL_RE.search(url)
        if not m:
            continue  # definition/category/etc. pages — not book content
        section, book_slug, doc_id = m.group(1), m.group(2), m.group(3)
        out.append({
            "dir": meta_path.parent,
            "url": url,
            "title": meta.get("title", ""),
            "section": section,
            "book": book_slug,
            "doc_id": int(doc_id) if doc_id else None,  # None = book index page
        })
    return out


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert wisdomlib_archive pages to automaton ingest JSONL"
    )
    ap.add_argument("--archive", required=True,
                    help="path to wisdomlib_archive (contains pages/)")
    ap.add_argument("--out", default="data/raw",
                    help="output dir for JSONL (default: data/raw)")
    ap.add_argument("--book", default=None,
                    help="only process books whose slug contains this substring")
    ap.add_argument("--mode", choices=["sanskrit", "full"], default="sanskrit",
                    help="sanskrit: Devanagari/IAST blocks only (default); "
                         "full: whole page text (NOT for republication)")
    ap.add_argument("--min-ratio", type=float, default=0.25,
                    help="min Devanagari char ratio for a line (default 0.25)")
    ap.add_argument("--min-block-chars", type=int, default=20,
                    help="discard blocks shorter than this (default 20)")
    ap.add_argument("--include-index", action="store_true",
                    help="also process book index pages (default: chapters "
                         "only — index pages emit table-of-contents noise)")
    ap.add_argument("--list-books", action="store_true",
                    help="list books found in the archive and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written; write nothing")
    args = ap.parse_args()

    archive = pathlib.Path(args.archive)
    pages = scan_archive(archive)
    if not pages:
        sys.exit("No book pages found in archive (only book/chapter URLs are used).")

    # Group chapter pages by book; index pages (doc_id None) are recorded but
    # carry almost no source text — they are still scanned (some hold verses).
    books: Dict[str, List[Dict]] = defaultdict(list)
    for p in pages:
        books[p["book"]].append(p)

    if args.list_books:
        print(f"{'book slug':50s} {'pages':>5s}  sections")
        for slug in sorted(books):
            ps = books[slug]
            print(f"{slug:50s} {len(ps):5d}  {ps[0]['section']}")
        print(f"\n{len(books)} books, {len(pages)} book-pages in archive.")
        return

    out_dir = pathlib.Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    total_records = 0
    total_files = 0
    skipped_pages = 0
    manifest: List[Dict] = []

    for slug in sorted(books):
        if args.book and args.book.lower() not in slug.lower():
            continue
        doc_code = doc_code_for_book(slug)
        # Stable page ordering: index page first, then chapters by doc id
        chapters = sorted(books[slug], key=lambda p: (p["doc_id"] is not None,
                                                      p["doc_id"] or 0))
        page_no = 0
        book_records = 0
        for p in chapters:
            if p["doc_id"] is None and not args.include_index:
                skipped_pages += 1
                continue  # book index page: table-of-contents, not source text
            content = extract_content_html(p["dir"] / "page.html")
            if content is None:
                content = extract_content_txt(p["dir"] / "page.txt")
            if not content:
                skipped_pages += 1
                continue

            if args.mode == "sanskrit":
                blocks = sanskrit_blocks(content, args.min_ratio,
                                         args.min_block_chars)
            else:
                blocks = [content]

            if not blocks:
                skipped_pages += 1
                continue

            page_no += 1
            records = []
            for blk in blocks:
                records.append({
                    "engine": "wisdomlib-adapter",
                    "page_no": page_no,
                    "text": blk,
                    "meta": {
                        "source_url": p["url"],
                        "source_title": p["title"],
                        "wisdomlib_doc_id": p["doc_id"],
                        "book_slug": slug,
                        "mode": args.mode,
                    },
                    "src_pdf": None,
                })

            fname = f"{doc_code}_{page_no:04d}.jsonl"
            if not args.dry_run:
                with (out_dir / fname).open("w", encoding="utf-8") as f:
                    for rec in records:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_files += 1
            total_records += len(records)
            book_records += len(records)

        if book_records:
            manifest.append({"doc": doc_code, "book": slug,
                             "pages": page_no, "records": book_records})

    # Report
    verb = "Would write" if args.dry_run else "Wrote"
    print(f"\n{verb} {total_files} JSONL page-file(s), {total_records} record(s); "
          f"{skipped_pages} page(s) had no qualifying text.")
    if manifest:
        print(f"\n{'doc code':40s} {'pages':>5s} {'records':>7s}")
        for m in manifest:
            print(f"{m['doc']:40s} {m['pages']:5d} {m['records']:7d}")
        print("\nNext step for each doc, e.g.:")
        d = manifest[0]["doc"]
        print(f'  python scripts/ingest_jsonl_fast.py --doc {d} '
              f'--glob "data/raw/{d}_*.jsonl" --category wisdomlib')
    if not HAVE_BS4:
        print("\nNOTE: beautifulsoup4 not installed — used page.txt fallback. "
              "For cleaner extraction: pip install beautifulsoup4")


if __name__ == "__main__":
    main()
