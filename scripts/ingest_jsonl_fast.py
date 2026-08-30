#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_jsonl_fast.py — Context-preserving JSONL ingest to SQLite.

Phase 1 upgrade: integrates segment_verses.py for within-page verse segmentation.
Each JSONL file (one OCR page) is now split into individual ślokas before storage.
Each śloka gets its own row with: verse_ref, chapter, text_type, chandas, padas,
quality_score, iast.

Fix 2026-07-20 (idx collision): the per-page passage index previously restarted
at 1 for EVERY JSONL record, so multi-record files (e.g. MBh01: one record per
verse, 31 verses per adhyāya) collided on (doc_id, page_no, 1) and each record
silently overwrote the previous — only the LAST verse of each page survived
(225 of 6,957 for MBh01). The index is now a page-wide counter. Single-record
pages (standard OCR flow) produce identical idx values as before, so existing
docs and their translations are unaffected by re-ingest.

Also fixed: FTS rowid was taken from cur.lastrowid, which is unreliable after
ON CONFLICT DO UPDATE — the passage id is now looked up explicitly.

Usage:
  python scripts/ingest_jsonl_fast.py --doc nirukta --glob data/raw/nirukta_*.jsonl
"""
import argparse, json, sqlite3, sys, re, pathlib, glob as _glob
from typing import Iterable

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

from db_utils import connect, ensure_schema, migrate_schema, ensure_doc
from segment_verses import segment_page_to_dicts
from iast_utils import devanagari_to_iast
from text_filters import score_passage_quality

# Extract trailing digits after last underscore: ..._0001.jsonl → 1
PAGE_RE = re.compile(r"_(\d+)(?:\.[A-Za-z0-9]+)?$", re.UNICODE)


def parse_page_no_from_path(p: pathlib.Path) -> int:
    m = PAGE_RE.search(p.stem)
    return int(m.group(1)) if m else 1


def read_jsonl(path: pathlib.Path) -> list:
    items = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                items.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    return items


def decide_page_no(path: pathlib.Path, items: list) -> int:
    pn = parse_page_no_from_path(path)
    if pn and pn > 0:
        return pn
    if items:
        rec = items[0]
        for k in ("page_no", "page", "pageNumber"):
            v = rec.get(k)
            if isinstance(v, int) and v > 0:
                return v
    return 1


def _ensure_provenance(con):
    """Add passages.ocr_engine if missing. (2026-08-29)

    Which engine produced a line is a fact about the text, not a detail of the
    run that made it. Without it the corpus cannot be filtered, audited or
    honestly presented: a reader has no way to know whether a verse came from
    Tesseract at ~64% word accuracy or from a vision pass at ~93% ceiling, and
    a later quality pass cannot target the weaker half.
    """
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "ocr_engine" not in cols:
        con.execute("ALTER TABLE passages ADD COLUMN ocr_engine TEXT")
        con.commit()


def upsert_passages(
    con: sqlite3.Connection,
    doc_id: int,
    page_no: int,
    items: Iterable[dict],
    *,
    do_segment: bool = True,
    do_iast: bool = True,
) -> int:
    """Ingest JSONL records into passages table.

    Args:
        do_segment: Split page blob into individual ślokas using segment_verses
        do_iast: Generate IAST transliteration for each passage

    Returns number of rows inserted/updated.
    """
    cur = con.cursor()
    n_inserted = 0
    # Page-wide passage index. MUST be unique per (doc_id, page_no) across ALL
    # records in this file — a per-record enumerate() here collapsed
    # multi-record JSONL files to their last record (fix 2026-07-20).
    seg_counter = 0

    for rec in items:
        raw_text = (rec.get("text") or "").strip()
        if not raw_text:
            continue

        # Normalize: preserve dandas (FIXED from old code which destroyed them)
        from normalize_text import normalize_sanskrit
        normed = normalize_sanskrit(raw_text)

        if do_segment:
            # Split into individual verses
            segments = segment_page_to_dicts(normed)
            # If segmenter returned nothing useful, fall back to page-as-one
            if not segments:
                segments = [{
                    "text": normed,
                    "verse_ref": None,
                    "chapter": None,
                    "text_type": "prose",
                    "chandas": None,
                    "padas": 0,
                    "quality_score": score_passage_quality(normed),
                }]
        else:
            # E-text quality handling (2026-07-20): score_passage_quality() is
            # calibrated for OCR dandas and under-scores danda-less clean
            # e-texts (GRETIL MBh01 measured ~0.52). Honor an explicit
            # quality_score from the record, else trust the e-text engine
            # marker, else fall back to the OCR-calibrated scorer.
            if rec.get("quality_score") is not None:
                q = float(rec["quality_score"])
            elif str(rec.get("engine", "")).startswith("gretil"):
                q = 0.98
            else:
                q = score_passage_quality(normed)
            segments = [{
                "text": normed,
                "verse_ref": rec.get("verse_ref"),
                "chapter": rec.get("chapter"),
                "text_type": rec.get("text_type", "prose"),
                "chandas": rec.get("chandas"),
                "padas": rec.get("padas", 0),
                "quality_score": q,
            }]

        for seg in segments:
            text = seg["text"].strip()
            if not text:
                continue
            seg_counter += 1

            # Generate IAST transliteration
            iast = ""
            if do_iast:
                try:
                    iast = devanagari_to_iast(text)
                except Exception:
                    iast = ""

            cur.execute(
                """
                INSERT INTO passages(doc_id, page_no, idx,
                    text, norm, iast,
                    verse_ref, chapter, text_type, chandas, padas, quality_score,
                    translation, ocr_engine)
                VALUES(?,?,?, ?,?,?, ?,?,?,?,?,?, ?,?)
                ON CONFLICT(doc_id, page_no, idx) DO UPDATE SET
                    text=excluded.text,
                    norm=excluded.norm,
                    iast=excluded.iast,
                    verse_ref=COALESCE(excluded.verse_ref, verse_ref),
                    chapter=COALESCE(excluded.chapter, chapter),
                    text_type=COALESCE(excluded.text_type, text_type),
                    chandas=COALESCE(excluded.chandas, chandas),
                    padas=COALESCE(excluded.padas, padas),
                    quality_score=COALESCE(excluded.quality_score, quality_score),
                    ocr_engine=COALESCE(excluded.ocr_engine, ocr_engine)
                    -- NOTE: translation is NOT overwritten on re-ingest
                """,
                (
                    doc_id, page_no, seg_counter,
                    text, normed, iast,
                    seg.get("verse_ref"), seg.get("chapter"),
                    seg.get("text_type", "prose"),
                    seg.get("chandas"), seg.get("padas", 0),
                    seg.get("quality_score", 0.0),
                    "",  # translation starts empty
                    (rec.get("engine") or None),   # provenance, straight from the JSONL
                )
            )
            # cur.lastrowid is unreliable after ON CONFLICT DO UPDATE —
            # look the row id up explicitly so FTS stays aligned (fix 2026-07-20).
            rid = cur.execute(
                "SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?",
                (doc_id, page_no, seg_counter),
            ).fetchone()[0]
            # Update FTS (trigram tokenizer handles Devanagari partial matching)
            cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rid,))
            cur.execute(
                "INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",
                (rid, text or "", iast or "", "")
            )
            n_inserted += 1

    con.commit()
    return n_inserted


def main():
    ap = argparse.ArgumentParser(
        description="Ingest OCR JSONL into SQLite with verse segmentation"
    )
    ap.add_argument("--doc",      required=True, help="doc code, e.g. nirukta")
    ap.add_argument("--glob",     required=True, help="glob pattern for JSONL files")
    ap.add_argument("--db",       default="data/context.db")
    ap.add_argument("--category", default=None, help="scripture category for docs table")
    ap.add_argument("--no-segment",  action="store_true", help="skip verse segmentation")
    ap.add_argument("--no-iast",     action="store_true", help="skip IAST generation")
    args = ap.parse_args()

    con = connect(args.db)
    _ensure_provenance(con)      # idempotent; adds passages.ocr_engine if absent
    ensure_schema(con)
    migrate_schema(con)

    doc_id = ensure_doc(con, args.doc, category=args.category)

    paths = sorted(pathlib.Path(p) for p in _glob.glob(args.glob))
    if not paths:
        print(f"No files matched: {args.glob}")
        sys.exit(0)

    print(f"Ingesting {len(paths)} JSONL files for doc={args.doc!r}")
    total = 0
    for path in paths:
        items = read_jsonl(path)
        if not items:
            continue
        page_no = decide_page_no(path, items)
        n = upsert_passages(
            con, doc_id, page_no, items,
            do_segment=not args.no_segment,
            do_iast=not args.no_iast,
        )
        total += n
        print(f"  {path.name}  =>  {n} segment(s)  (page {page_no})")

    print(f"\nDone. Total passages upserted: {total}")


if __name__ == "__main__":
    main()
