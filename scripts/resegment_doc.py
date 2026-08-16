#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resegment_doc.py — Split an OCR page-blob doc into per-verse records (2026-08-02).

Some OCR-sourced texts (e.g. the Nilamata Purāṇa) were ingested one-page-per-
passage: each DB passage is a whole page holding many ślokas. That forces
all-or-nothing translation — a single garbled verse in a page empties the whole
page, discarding the good verses around it. The general segmenter
(segment_verses.py) splits on daṇḍas (॥); these OCR blobs have almost none —
their verses are delimited by a trailing Devanagari śloka-number (…समनोहरम् १२).

This tool reads a source doc's page-blobs and splits each at those trailing
verse-numbers, emitting one JSONL record per verse into data/raw/<new>_NNNN.jsonl
(one file per source page). It is NON-DESTRUCTIVE: the source doc is never
touched. Ingest the output as a NEW doc, translate it, compare, and only then
adopt it as canonical.

Workflow:
  python scripts/resegment_doc.py --src-doc upapurana_nilamata_purana \
         --new-doc nilamata_seg --dry-run          # inspect the split first
  python scripts/resegment_doc.py --src-doc upapurana_nilamata_purana \
         --new-doc nilamata_seg --yes               # write the JSONL
  python scripts/ingest_jsonl_fast.py --doc nilamata_seg \
         --glob "data/raw/nilamata_seg_*.jsonl" --category upapurana --no-segment
  python scripts/translate_passages.py --doc nilamata_seg --engine gemini:gemini-2.5-flash
  python scripts/export_html.py --db data/context.db --doc nilamata_seg
"""
from __future__ import annotations
import argparse, json, pathlib, re, sqlite3, sys

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

# A trailing Devanagari śloka-number closes a verse: "<verse text> १२\n".
# 1–3 digits, optionally wrapped in daṇḍas/spaces, at end of a line.
_VERSE_NUM_RE = re.compile(r"[।॥\s]*([०-९]{1,3})[।॥\s]*(?:\n|$)")
_DEV2AR = str.maketrans("०१२३४५६७८९", "0123456789")
_DEV_RE = re.compile(r"[ऀ-ॿ]")
# Publisher/title header lines to drop from the first verse of a doc.
_HEADER_RE = re.compile(r"^\s*\[[^\]]*\]|COLLECTION|नीलमतपुराणम्|^\s*$", re.MULTILINE)


def _frac_dev(s: str) -> float:
    return len(_DEV_RE.findall(s)) / max(1, len(s)) if s else 0.0


def split_verses(blob: str):
    """Split a page-blob into [{text, verse_ref}] at trailing Devanagari
    verse-numbers. A trailing fragment with no number is kept with ref=None
    (it is usually a verse continued on the next page)."""
    verses = []
    last = 0
    for m in _VERSE_NUM_RE.finditer(blob):
        seg = blob[last:m.start()].strip()
        num = m.group(1).translate(_DEV2AR)
        if seg:
            verses.append({"text": seg, "verse_ref": num})
        last = m.end()
    tail = blob[last:].strip()
    if tail:
        verses.append({"text": tail, "verse_ref": None})
    return verses


def _clean_first(text: str) -> str:
    """Strip a publisher/title header from the very first verse only."""
    return _HEADER_RE.sub("", text).strip()


def main():
    ap = argparse.ArgumentParser(description="Split an OCR page-blob doc into per-verse JSONL")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--src-doc", required=True, help="existing page-blob doc code")
    ap.add_argument("--new-doc", required=True, help="new doc code for the segmented output")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--min-dev", type=float, default=0.4,
                    help="drop segments below this Devanagari fraction (OCR noise)")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--yes", action="store_true", help="write the JSONL files")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    row = con.execute("SELECT id FROM docs WHERE code=?", (args.src_doc,)).fetchone()
    if not row:
        sys.exit(f"source doc {args.src_doc!r} not found")
    did = row[0]
    blobs = con.execute(
        "SELECT page_no, text FROM passages WHERE doc_id=? AND text IS NOT NULL "
        "ORDER BY page_no, idx", (did,)).fetchall()
    con.close()

    out_dir = pathlib.Path(args.out)
    total_verses = kept = dropped = 0
    first_done = False
    per_page_preview = []
    to_write = []  # (path, records)

    for page_no, blob in blobs:
        verses = split_verses(blob or "")
        recs = []
        for v in verses:
            text = v["text"]
            if not first_done:
                text = _clean_first(text)
                first_done = True
            total_verses += 1
            if _frac_dev(text) < args.min_dev or len(text.strip()) < 4:
                dropped += 1
                continue
            recs.append({
                "text": text,
                "verse_ref": v["verse_ref"],
                "page_no": page_no,
                "engine": "resegment-devnum",
                "meta": {"src_doc": args.src_doc, "src_page": page_no},
            })
            kept += 1
        if recs:
            fname = out_dir / f"{args.new_doc}_{page_no:04d}.jsonl"
            to_write.append((fname, recs))
        if len(per_page_preview) < 3:
            per_page_preview.append((page_no, recs[:3]))

    print(f"src={args.src_doc}  pages={len(blobs)}  "
          f"verses found={total_verses}  kept={kept}  dropped(noise)={dropped}")
    print("preview (first pages):")
    for pg, recs in per_page_preview:
        print(f"  page {pg}:")
        for r in recs:
            print(f"    ref={r['verse_ref']!r}  {r['text'][:64]!r}")

    if args.dry_run or not args.yes:
        print("\nDry run — nothing written. Re-run with --yes to emit JSONL, then:")
        print(f"  python scripts/ingest_jsonl_fast.py --doc {args.new_doc} "
              f'--glob "data/raw/{args.new_doc}_*.jsonl" --category upapurana --no-segment')
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    n_files = 0
    for fname, recs in to_write:
        with fname.open("w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n_files += 1
    print(f"\nWrote {n_files} JSONL files ({kept} verses) to {out_dir}/{args.new_doc}_NNNN.jsonl")
    print("Next:")
    print(f"  python scripts/ingest_jsonl_fast.py --doc {args.new_doc} "
          f'--glob "data/raw/{args.new_doc}_*.jsonl" --category upapurana --no-segment')
    print(f"  python scripts/translate_passages.py --doc {args.new_doc} --engine gemini:gemini-2.5-flash")
    print(f"  python scripts/export_html.py --db data/context.db --doc {args.new_doc}")


if __name__ == "__main__":
    main()
