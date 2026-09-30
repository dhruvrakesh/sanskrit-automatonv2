#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pipeline_inventory.py - where every book actually stands. READ-ONLY.
(PIPELINE_INVENTORY_2026_09_30, v2: aliases, empty-doc count, page-sized passages)

The dashboard has no per-book pipeline state: a book is "split" if its page PDFs
are in inbox/, "OCR'd" if data/raw/ has a JSONL per page, "ingested" if
context.db has passages for those pages, "translated" if the passages carry
English / Hindi. Nothing computes these together, so a book can stop between
two stages and no screen says so (Mallapurana, 2026-09-29: split five times,
never OCR'd; 9 other books stranded the same way since June).

This script derives the state from those artifacts - the files and the
database ARE the source of truth - and prints one row per book with the stage
it is stuck at and why, using data/jobs.jsonl for the last attempt of each step.

  python scripts/pipeline_inventory.py                 # stuck books only
  python scripts/pipeline_inventory.py --all           # every book
  python scripts/pipeline_inventory.py --json out.json # machine-readable

context.db is opened mode=ro + query_only (reads the WAL, writes nothing, never
blocks the pipeline writer). No network, no API key.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PDF_RE = re.compile(r"^([A-Za-z0-9_\-]+)_(\d{4})\.pdf$", re.I)          # = dashboard.PDF_RE
JSONL_RE = re.compile(r"^([A-Za-z0-9_\-]+)_(\d{4})(?:_norm)?\.jsonl$", re.I)  # = dashboard.JSONL_RE
LIVE = "p.id IS NOT NULL AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
# v2 2026-09-30: "p.id IS NOT NULL" - with the LEFT JOIN, a doc with no passages
# produced one all-NULL row that counted as 1 live passage.
# Tokens that name a genre, not a work, so aliases can be matched on what is left.
GENERIC = {"seg", "purana", "upapurana", "veda", "dhanur", "smriti", "the", "of", "with"}


def pages_by_doc(folder: Path, rx) -> dict:
    out = {}
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for n in names:
        m = rx.match(n)
        if m:
            out.setdefault(m.group(1), set()).add(int(m.group(2)))
    return out


def db_facts(db: Path) -> dict:
    out = {}
    if not db.exists():
        return out
    con = sqlite3.connect("file:%s?mode=ro" % db.resolve().as_posix(), uri=True, timeout=30)
    con.execute("PRAGMA query_only=ON")
    try:
        for code, pages, live, en, avg_len in con.execute(
                "SELECT d.code, COUNT(DISTINCT p.page_no), "
                f"SUM(CASE WHEN {LIVE} THEN 1 ELSE 0 END), "
                f"SUM(CASE WHEN {LIVE} AND TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END), "
                f"AVG(CASE WHEN {LIVE} THEN LENGTH(p.text) END) "
                "FROM docs d LEFT JOIN passages p ON p.doc_id = d.id "
                "WHERE d.code NOT LIKE '%-RETIRED' GROUP BY d.id"):
            out[code] = {"db_pages": pages or 0, "live": live or 0, "en": en or 0, "hi": 0,
                         "avg_len": int(avg_len or 0)}
        try:
            for code, hi in con.execute(
                    "SELECT d.code, COUNT(*) FROM translations_l10n l "
                    "JOIN passages p ON p.id = l.passage_id JOIN docs d ON d.id = p.doc_id "
                    "WHERE l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>'' GROUP BY d.id"):
                if code in out:
                    out[code]["hi"] = hi
        except sqlite3.OperationalError:
            pass
    finally:
        con.close()
    return out


def last_jobs(path: Path) -> dict:
    """{doc: {kind: last record}} from the append-only job history."""
    out = {}
    try:
        fh = open(path, encoding="utf-8")
    except OSError:
        return out
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            d, k = r.get("doc"), r.get("kind")
            if d and k:
                out.setdefault(d, {})[k] = r
    return out


def when(r) -> str:
    t = (r or {}).get("end") or (r or {}).get("start")
    return _dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "-"


def classify(pdf: set, ocr: set, f: dict, jobs: dict) -> tuple:
    """(stage, stuck: bool, reason)."""
    n_pdf, n_ocr = len(pdf), len(ocr & pdf) if pdf else len(ocr)
    missing_ocr = len(pdf - ocr) if pdf else 0
    ocr_job = jobs.get("ocr") or jobs.get("pipeline")
    if pdf and n_ocr == 0:
        if not ocr_job:
            return "split", True, "split; OCR never started (no OCR job in history)"
        return "split", True, "split; last OCR attempt %s failed/stopped (ok=%s rc=%s)" % (
            when(ocr_job), ocr_job.get("ok"), ocr_job.get("rc"))
    if missing_ocr:
        why = ("last OCR %s ok=%s rc=%s" % (when(ocr_job), ocr_job.get("ok"), ocr_job.get("rc"))
               if ocr_job else "no OCR job in history")
        return "ocr-partial", True, "%d of %d pages have no OCR output; %s" % (missing_ocr, n_pdf, why)
    ocr_pages = len(ocr)
    if ocr_pages and f.get("db_pages", 0) == 0:
        return "ocr-done", True, "OCR complete (%d pages) but nothing ingested" % ocr_pages
    if ocr_pages and f.get("db_pages", 0) < ocr_pages * 0.9:
        return "ingest-partial", True, "%d OCR pages, %d pages in the database" % (ocr_pages, f["db_pages"])
    if f.get("live", 0) and f.get("en", 0) == 0:
        return "ingested", False, "ingested, not translated"
    if f.get("live", 0):
        return "translating" if f["en"] < f["live"] else "translated", False, ""
    return "empty", False, "no live passages"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--all", action="store_true", help="every book, not only stuck ones")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    pdfs = pages_by_doc(root / "inbox", PDF_RE)
    raws = pages_by_doc(root / "data" / "raw", JSONL_RE)
    facts = db_facts(root / a.db if not Path(a.db).is_absolute() else Path(a.db))
    jobs = last_jobs(root / "data" / "jobs.jsonl")

    rows = []
    for doc in sorted(set(pdfs) | set(raws) | set(facts)):
        pdf, ocr, f = pdfs.get(doc, set()), raws.get(doc, set()), facts.get(doc, {})
        stage, stuck, reason = classify(pdf, ocr, f, jobs.get(doc, {}))
        rows.append({"doc": doc, "pdf_pages": len(pdf), "ocr_pages": len(ocr & pdf) if pdf else len(ocr),
                     "db_pages": f.get("db_pages", 0), "live": f.get("live", 0), "en": f.get("en", 0),
                     "hi": f.get("hi", 0), "avg_len": f.get("avg_len", 0), "stage": stage, "stuck": stuck, "reason": reason,
                     "in_database": doc in facts})
    # v2: aliases. The same work imported under two codes (a "_seg" re-segmentation,
    # or "dhanur_veda_vasishtha_dhanur_veda" vs "vasishtha_dhanur_veda") shows up
    # as one stranded code and one healthy one. Match on the distinctive tokens AND
    # an equal OCR page count; report, never merge.
    def key(c):
        return frozenset(t for t in c.lower().split("_") if t and t not in GENERIC)
    by = {r["doc"]: r for r in rows}
    for r in rows:
        k = key(r["doc"])
        if not k:
            continue
        twins = [o for o in rows if o is not r and key(o["doc"]) == k
                 and o["ocr_pages"] and o["ocr_pages"] == r["ocr_pages"]]
        if not twins:
            continue
        r["twins"] = [o["doc"] for o in twins]
        live_twins = [o for o in twins if o["live"]]
        if not r["live"] and live_twins:
            r["stage"], r["stuck"] = "alias", False
            r["reason"] = "same work as %s (same %d OCR pages, in the database) - not stranded" % (
                ", ".join(o["doc"] for o in live_twins), r["ocr_pages"])
        elif r["live"] and live_twins:
            r["stage"], r["stuck"] = "duplicate", True
            r["reason"] = "also in the database as %s (%s live passages): one of the two is legacy" % (
                ", ".join(o["doc"] for o in live_twins), ", ".join(str(o["live"]) for o in live_twins))
    # v2: a book ingested as one passage per page was not verse-segmented.
    for r in rows:
        f = facts.get(r["doc"], {})
        if r["stage"] in ("ingested", "translating") and r["live"] and r["db_pages"] \
                and r["live"] <= r["db_pages"] and f.get("avg_len", 0) > 600:
            r["stuck"] = True
            r["reason"] = ("one passage per page (avg %d chars): not verse-segmented; "
                           "translating it would send whole pages" % f["avg_len"])
    shown = rows if a.all else [r for r in rows if r["stuck"]]
    print("pipeline_inventory  (read-only)  books: %d  stuck: %d  stranded pages (no OCR): %d"
          % (len(rows), sum(r["stuck"] for r in rows),
             sum(max(0, r["pdf_pages"] - r["ocr_pages"]) for r in rows)))
    print("  %-46s %6s %6s %6s %7s %7s %6s  %-14s %s" % ("doc", "pdf", "ocr", "db-pg", "live", "en", "hi", "stage", "why"))
    for r in shown:
        print("  %-46s %6d %6d %6d %7d %7d %6d  %-14s %s" % (
            r["doc"][:46], r["pdf_pages"], r["ocr_pages"], r["db_pages"], r["live"], r["en"], r["hi"],
            r["stage"], r["reason"]))
    if a.json:
        Path(a.json).write_text(json.dumps({"generated": _dt.datetime.now().isoformat(timespec="seconds"),
                                            "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  written: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
