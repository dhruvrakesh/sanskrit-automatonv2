#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_inbox.py — batch all PDFs in an inbox, including page-sharded books

Recognized naming:
1) Whole book:            <doc>.pdf
2) Page-sharded PDFs:     <doc>_<page>.pdf            (page is 1.., 001.., 0001..)

Pipeline per doc:
OCR (each PDF) -> JSONL -> normalize -> ingest (DB backup+schema) -> translate (cached) -> export HTML

Requires: db_utils.py, post_normalize_ocr.py, translate_passages.py, export_html.py, ocr_pdf.py
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Iterable
import argparse, os, re, sys, json, sqlite3, subprocess, pathlib
import argparse, os, re, sys, json, sqlite3, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
RAW = DATA / "raw"

OCR = SCRIPTS / "ocr_pdf.py"
POST_NORM = SCRIPTS / "post_normalize_ocr.py"
TRANSLATE = SCRIPTS / "translate_passages.py"
EXPORT = SCRIPTS / "export_html.py"

from db_utils import connect, ensure_schema, backup_db, ensure_doc

PDF_RE = re.compile(r"(?i)\.pdf$")  # case-insensitive
PAGE_RE = re.compile(r"^(?P<doc>[a-z0-9_]+)_(?P<page>\d{1,6})$", re.I)


# ---- load .env without extra deps ----


def _load_dotenv_from_repo_root():
    if os.environ.get("OPENAI_API_KEY"):  # already set (e.g., CI or shell)
        return
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"): 
                continue
            k, sep, v = s.partition("=")
            if sep:
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_dotenv_from_repo_root()
# --------------------------------------


def scan_inbox(inbox: pathlib.Path) -> Dict[str, List[Tuple[int, pathlib.Path]]]:
    """
    Group PDFs by doc. Supports:
    - single file  :  <doc>.pdf
    - page shards  :  <doc>_<page>.pdf
    Returns: {doc: [(page_no, path), ...]} with page_no=1 for single-file PDFs.
    """
    groups: Dict[str, List[Tuple[int, pathlib.Path]]] = {}
    for p in sorted(inbox.glob("*.pdf")):
        stem = p.stem
        m = PAGE_RE.match(stem)
        if m:
            doc = m.group("doc")
            page = int(m.group("page"))
            groups.setdefault(doc, []).append((page, p))
        else:
            # Treat as a whole-book single PDF → give page=1 sentinel
            doc = stem
            groups.setdefault(doc, []).append((1, p))
    # sort by page within each doc
    for k in groups:
        groups[k].sort(key=lambda t: t[0])
    return groups

def run(cmd: List[str]) -> int:
    # use ASCII-only output to avoid Windows cp1252 hiccups
    print(">", " ".join(cmd))
    p = subprocess.run(cmd)
    return p.returncode

def ocr_to_jsonl(pdf: pathlib.Path) -> pathlib.Path:
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"{pdf.stem}.jsonl"
    cmd = [sys.executable, str(OCR), "--pdf", str(pdf), "--out", str(out)]
    code = run(cmd)
    if code != 0:
        raise SystemExit(code)
    return out

def post_normalize(inp: pathlib.Path) -> pathlib.Path:
    out = inp.with_name(inp.stem + "_norm.jsonl")
    cmd = [sys.executable, str(POST_NORM), "--in", str(inp), "--out", str(out)]
    code = run(cmd)
    if code != 0:
        raise SystemExit(code)
    return out

def ingest_jsonl(con: sqlite3.Connection, doc: str, jsonl: pathlib.Path) -> Tuple[int,int,int]:
    """
    Insert lines into passages (doc_id,page_no,idx,text), refresh FTS.
    Returns: (inserted_rows, page_lo, page_hi)
    """
    ensure_schema(con)
    doc_id = ensure_doc(con, doc)
    rows = []
    with open(jsonl, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            rec = json.loads(ln)
            page = int(rec.get("page_no") or rec.get("page") or 0) or 1
            text = (rec.get("text") or "").strip()
            idx = rec.get("idx") or rec.get("line_no") or rec.get("i")
            rows.append((page, idx, text))

    if not rows: 
        return (0, 0, 0)

    pages = [r[0] for r in rows]
    lo, hi = (min(pages), max(pages)) if pages else (1,1)

    cur = con.cursor(); cur.execute("BEGIN")
    inserted = 0
    for page, idx, text in rows:
        if not isinstance(idx, int):
            r = cur.execute("SELECT COALESCE(MAX(idx),0)+1 FROM passages WHERE doc_id=? AND page_no=?", (doc_id, page)).fetchone()
            idx = int(r[0] or 1)
        cur.execute("""
            INSERT INTO passages(doc_id,page_no,idx,text)
            VALUES(?,?,?,?)
            ON CONFLICT(doc_id,page_no,idx) DO UPDATE SET text=excluded.text
        """, (doc_id, page, idx, text))
        # update FTS
        rid = cur.execute("SELECT id FROM passages WHERE doc_id=? AND page_no=? AND idx=?", (doc_id, page, idx)).fetchone()[0]
        cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rid,))
        cur.execute("INSERT INTO passages_fts(rowid,text,translation) VALUES (?,?,COALESCE((SELECT translation FROM passages WHERE id=?),'') )", (rid, text, rid))
        inserted += 1
    con.commit()
    return (inserted, lo, hi)

def translate_doc(db: pathlib.Path, doc: str, engine: str | None, sleep: float) -> None:
    cmd = [sys.executable, str(TRANSLATE), "--db", str(db), "--doc", doc, "--sleep", str(sleep)]
    if engine: cmd += ["--engine", engine]
    run(cmd)

def export_doc(db: pathlib.Path, doc: str, out_dir: pathlib.Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"{doc} — English Translation"
    cmd = [sys.executable, str(EXPORT), "--db", str(db), "--doc", doc, "--out", str(out_dir), "--title", title, "--no-sanskrit"]
    run(cmd)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", required=True, help="Folder with PDFs (whole books or <doc>_<page>.pdf shards)")
    ap.add_argument("--db", default=str(DATA / "context.db"))
    ap.add_argument("--ocr", action="store_true", help="Run OCR (default if no specific stages chosen)")
    ap.add_argument("--ingest", action="store_true", help="Ingest JSONL into DB (default if no stages chosen)")
    ap.add_argument("--translate", action="store_true", help="Translate to English (default if no stages chosen)")
    ap.add_argument("--export", action="store_true", help="Export clean English HTML (default if no stages chosen)")
    ap.add_argument("--engine", default=None, help="MT engine, e.g. openai:gpt-4o-mini or echo")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--out", default="exports")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # If no stages specified, do the full pipeline.
    any_stage = args.ocr or args.ingest or args.translate or args.export
    run_ocr = args.ocr or not any_stage
    run_ingest = args.ingest or not any_stage
    run_translate = args.translate or not any_stage
    run_export = args.export or not any_stage

    inbox = pathlib.Path(args.inbox)
    if not inbox.exists(): raise SystemExit(f"Inbox not found: {inbox}")

    db_path = pathlib.Path(args.db)
    con = connect(str(db_path)); ensure_schema(con)
    if db_path.exists() and not args.no_backup:
        print("Creating DB backup...")
        print("Backup:", backup_db(str(db_path)))

    groups = scan_inbox(inbox)
    if not groups:
        print("No PDFs found in inbox.")
        return

    print(f"Discovered {len(groups)} document group(s).")
    for doc, items in groups.items():
        print(f"\n=== {doc}: {len(items)} PDF(s) ===")
        page_spans: List[Tuple[int,int]] = []
        for page_no, pdf in items:
            # 1) OCR -> JSONL
            if run_ocr:
                jsonl = ocr_to_jsonl(pdf)
                jsonl_norm = post_normalize(jsonl)
            else:
                jsonl_norm = RAW / f"{pdf.stem}_norm.jsonl"
                if not jsonl_norm.exists():
                    # fallback to raw jsonl if present
                    jsonl_norm = RAW / f"{pdf.stem}.jsonl"
                    if not jsonl_norm.exists():
                        print(f"Skip: no JSONL for {pdf}")
                        continue

            # 2) Ingest
            if run_ingest:
                ins, lo, hi = ingest_jsonl(con, doc, jsonl_norm)
                print(f"ingest: +{ins} rows (pages {lo}-{hi})")
                if lo and hi: page_spans.append((lo,hi))

        # 3) Translate
        if run_translate:
            translate_doc(db_path, doc, args.engine, args.sleep)

        # 4) Export
        if run_export:
            export_doc(db_path, doc, pathlib.Path(args.out))

    print("\nDONE.")

if __name__ == "__main__":
    main()
