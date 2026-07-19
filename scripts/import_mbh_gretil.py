#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_mbh_gretil.py — Import the Mahābhārata critical edition (BORI e-text)
into the automaton as clean digital text. NO OCR involved.

Source: GRETIL, "Mahābhārata" electronic text — input by Muneo Tokunaga,
revised by John Smith (Cambridge); (C) BORI Pune 1999 e-text of the critical
edition. Book 1 (Ādiparvan): mbh_01_u.htm (romanized Unicode / IAST).

What it does:
  1. Downloads (or reads --src local file) the GRETIL book file.
  2. Keeps ONLY the constituted text of the critical edition:
     lines matching  BB,CCC.VVVp  (e.g. "01,001.003a").
     Star-passages / apparatus lines ("01,001.000*0001_01") are EXCLUDED —
     they are interpolations rejected by the BORI editors, and Debroy
     translates the constituted text, so the benchmark must match.
  3. Groups pāda-lines into verses, verses into adhyāyas.
  4. Transliterates IAST → Devanagari (indic-transliteration, already a
     pipeline dependency) so ingest's normalizer/IAST round-trip works as
     with every other doc.
  5. Writes one JSONL per adhyāya: data/raw/MBh01_0001.jsonl … with
     verse_ref ("1.1.3"), chapter, text_type filled in.

Then (existing pipeline, unchanged):
  python scripts/ingest_jsonl_fast.py --doc MBh01 --glob "data/raw/MBh01_*.jsonl" ^
         --category mahabharata --no-segment
  python scripts/benchmark_mbh01.py --doc MBh01 --n 30

Usage:
  python scripts/import_mbh_gretil.py --book 1 --dry-run
  python scripts/import_mbh_gretil.py --book 1
  python scripts/import_mbh_gretil.py --book 1 --src path\\to\\mbh_01_u.htm
"""
import argparse
import html as html_mod
import json
import pathlib
import re
import sys
import urllib.request

from indic_transliteration import sanscript

GRETIL_URL = "http://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/mbh_{book:02d}_u.htm"

# Constituted-text line:  01,001.003a <text>   (pāda letter optional for prose)
MAIN_RE = re.compile(r"^(\d{2}),(\d{3})\.(\d{3})([a-z]?)\s+(.*)$")
TAG_RE = re.compile(r"<[^>]+>")


def fetch(book: int, src: str | None) -> str:
    if src:
        return pathlib.Path(src).read_text(encoding="utf-8", errors="ignore")
    url = GRETIL_URL.format(book=book)
    print(f"Downloading {url} …")
    req = urllib.request.Request(url, headers={"User-Agent": "sanskrit-automaton/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", errors="ignore")


def parse(raw: str, book: int):
    """Return {chapter_int: [ {verse_ref, iast_text} ]} — constituted text only."""
    text = html_mod.unescape(TAG_RE.sub("", raw))
    chapters: dict[int, dict[int, list[str]]] = {}
    kept = skipped_star = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "*" in line.split(" ", 1)[0]:
            skipped_star += 1
            continue  # star-passage / apparatus — not constituted text
        m = MAIN_RE.match(line)
        if not m:
            continue
        b, ch, vs = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if b != book:
            continue
        payload = m.group(5).strip()
        if not payload:
            continue
        chapters.setdefault(ch, {}).setdefault(vs, []).append(payload)
        kept += 1
    print(f"Parsed: {kept} constituted pāda/prose lines kept, "
          f"{skipped_star} star-passage lines excluded, "
          f"{len(chapters)} adhyāyas found.")
    return chapters


def to_devanagari(iast: str) -> str:
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)


def write_jsonl(chapters, book: int, out_dir: pathlib.Path, doc_code: str,
                dry_run: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    n_files = n_verses = 0
    for page_no, ch in enumerate(sorted(chapters), start=1):
        records = []
        for vs in sorted(chapters[ch]):
            iast_lines = chapters[ch][vs]
            iast_verse = "\n".join(iast_lines)
            dev_verse = to_devanagari(iast_verse)
            records.append({
                "engine": "gretil-bori-etext",
                "page_no": page_no,
                "text": dev_verse,
                "verse_ref": f"{book}.{ch}.{vs}",
                "chapter": str(ch),
                "text_type": "verse" if len(iast_lines) > 1 else "prose",
                "padas": len(iast_lines) * 2,
                "meta": {"source": "GRETIL/BORI e-text (Tokunaga/Smith)",
                         "iast_source": iast_verse},
                "src_pdf": None,
            })
        n_verses += len(records)
        fname = out_dir / f"{doc_code}_{page_no:04d}.jsonl"
        if not dry_run:
            with fname.open("w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_files += 1
    verb = "Would write" if dry_run else "Wrote"
    print(f"{verb} {n_files} adhyāya files, {n_verses} verses → {out_dir}/{doc_code}_NNNN.jsonl")
    if not dry_run:
        print(f"\nNext:\n  python scripts/ingest_jsonl_fast.py --doc {doc_code} "
              f'--glob "data/raw/{doc_code}_*.jsonl" --category mahabharata --no-segment')
        print(f"  python scripts/benchmark_mbh01.py --doc {doc_code} --n 30 --dry-run")


def main():
    ap = argparse.ArgumentParser(description="Import GRETIL/BORI Mahabharata e-text")
    ap.add_argument("--book", type=int, default=1, help="parvan number 1-18")
    ap.add_argument("--src", default=None,
                    help="local mbh_NN_u.htm file (skips download)")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--doc-code", default=None,
                    help="default: MBh01 for book 1, MBh02 …")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc_code = args.doc_code or f"MBh{args.book:02d}"
    raw = fetch(args.book, args.src)
    chapters = parse(raw, args.book)
    if not chapters:
        sys.exit("ERROR: no constituted-text lines parsed — check the source file.")
    write_jsonl(chapters, args.book, pathlib.Path(args.out), doc_code, args.dry_run)


if __name__ == "__main__":
    main()
