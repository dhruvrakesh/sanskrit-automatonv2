#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
heal_etext_meta.py  (2026-10-14)  ETEXT_META_2026_10_14

An e-text's passages should say they are an e-text. MBh01 (the BORI Critical Edition e-text, from GRETIL) went in
before the ingest knew an e-text: its passages have no ocr_engine, and their quality_score is the one made for OCR,
0.6 x the share of Devanagari signs + 0.4 x the dandas (up to 5). The e-text has no dandas, so it scores 0.48 to
0.58 (the mean 0.52) whatever its quality. The dashboard shows "Q:53%"; the Srangam reader shows "OCR confidence 52%",
and on the 267 verses below 0.5 "the printed page was hard to read". ingest_jsonl_fast.py gives a GRETIL record 0.98
today, and its engine.

For the passages whose page file (data/raw/<doc>_NNNN.jsonl) has a record of an e-text engine (gretil..., or one that
says etext) with the same verse and the same text (normalized as the ingest normalizes it), this sets:
  ocr_engine = the record's engine, where it is empty;
  quality_score = 0.98 (the ingest's e-text value), where it is lower.
Nothing else: no text, no translation. A dry run by default (read-only). --apply: refused while the dashboard runs a
job that changes this text's Sanskrit or English (a Hindi job does not stop it), then a backup (db_backup.py), then one
transaction; the values before go to data/heal/etext_meta_<doc>_<stamp>.jsonl, and --undo that file puts them back.
The site gets the change at the next mirror run (corpus_sync.py: those passages' rows change).

  python scripts\\heal_etext_meta.py --doc MBh01                 the plan, free
  python scripts\\heal_etext_meta.py --doc MBh01 --apply
  python scripts\\heal_etext_meta.py --doc MBh01 --undo data\\heal\\etext_meta_MBh01_20261014_210000.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

MARK = "ETEXT_META_2026_10_14"
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PY = sys.executable
ETEXT_QUALITY = 0.98          # = ingest_jsonl_fast.py, a gretil record
QUIET_KINDS = ("translate_hi", "ocr", "judge", "judge_all", "benchmark", "benchmark_all", "redeem_all", "path_all",
               "export", "pdf", "booksmith")


def is_etext(engine) -> bool:
    e = str(engine or "").lower()
    return e.startswith("gretil") or "etext" in e


def records(raw: Path, doc: str) -> dict:
    """{(page_no, verse_ref): (engine, text)} of the doc's page files whose records are an e-text's."""
    rx = re.compile(r"^%s_(\d{4})\.jsonl$" % re.escape(doc))
    out = {}
    if not raw.is_dir():
        return out
    for p in sorted(raw.iterdir()):
        m = rx.match(p.name)
        if not m:
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and is_etext(r.get("engine")) and r.get("verse_ref"):
                    out[(int(r.get("page_no") or m.group(1)), str(r["verse_ref"]))] = (str(r["engine"]), r.get("text") or "")
    return out


def plan(con, doc: str, raw: Path) -> dict:
    from normalize_text import normalize_sanskrit
    recs = records(raw, doc)
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "ocr_engine" not in cols:
        return {"error": "passages has no ocr_engine column"}
    rows = con.execute("SELECT p.id, p.page_no, p.verse_ref, p.text, p.quality_score, p.ocr_engine FROM passages p JOIN "
                       "docs d ON d.id = p.doc_id WHERE d.code = ? ORDER BY p.page_no, p.idx", (doc,)).fetchall()
    out = {"passages": len(rows), "records": len(recs), "engine": 0, "quality": 0, "differs": 0, "no_record": 0,
           "changes": [], "below_half": 0}
    for pid, pg, ref, text, q, eng in rows:
        rec = recs.get((pg, str(ref)))
        if rec is None:
            out["no_record"] += 1
            continue
        if normalize_sanskrit((rec[1] or "").strip()) != (text or ""):
            out["differs"] += 1
            continue
        new_e = rec[0] if not (eng or "").strip() else None
        new_q = ETEXT_QUALITY if (q is None or q < ETEXT_QUALITY) else None
        if new_e is None and new_q is None:
            continue
        out["engine"] += 1 if new_e else 0
        out["quality"] += 1 if new_q else 0
        out["below_half"] += 1 if (q is not None and q < 0.5) else 0
        out["changes"].append({"id": pid, "page_no": pg, "verse_ref": ref, "quality_before": q, "engine_before": eng,
                               "quality": new_q if new_q is not None else q, "engine": new_e or eng})
    return out


def busy_with(doc: str):
    try:
        import repair_text as rt
        jobs = rt.dashboard_jobs()
    except Exception:
        return None
    if jobs is None:
        return None
    return [j for j in jobs if j.get("doc") == doc and j.get("kind") not in QUIET_KINDS]


def backup(db: str, backup_dir: str, doc: str, stamp: str):
    dst = Path(backup_dir) / ("context_pre_etextmeta_%s_%s.db" % (doc, stamp))
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([PY, str(SCRIPTS / "db_backup.py"), db, str(dst)], capture_output=True, text=True)
    return dst if r.returncode == 0 and dst.exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--raw", default=None, help="the page files (default: raw beside the database)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", default=None, help="a log this wrote: put its values back")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--log-dir", default="data/heal")
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    raw = Path(a.raw) if a.raw else Path(a.db).resolve().parent / "raw"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if a.undo:
        rows = []
        with open(a.undo, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("mark") == MARK and r.get("doc") == a.doc:
                    rows.append(r)
        if not rows:
            print("REFUSE: %s holds no %s row of %s" % (a.undo, MARK, a.doc)); print("VERDICT: nothing to undo"); return 1
        if not backup(a.db, a.backup_dir, a.doc, stamp):
            print("REFUSE: the backup failed; nothing was changed."); return 1
        con = sqlite3.connect(a.db, timeout=60)
        try:
            with con:
                con.executemany("UPDATE passages SET quality_score = ?, ocr_engine = ? WHERE id = ?",
                                [(r["quality_before"], r["engine_before"], r["id"]) for r in rows])
        finally:
            con.close()
        print("VERDICT: %d passage(s) of %s back as they were" % (len(rows), a.doc))
        print("NEXT: python scripts\\corpus_sync.py   (the plan: the site gets them back at the next mirror run)")
        return 0
    ro = sqlite3.connect(Path(a.db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        p = plan(ro, a.doc, raw)
    finally:
        ro.close()
    print("heal_etext_meta.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing written)"))
    if p.get("error"):
        print("REFUSE: " + p["error"]); print("VERDICT: nothing to do"); print("NEXT: "); return 1
    print("  %s: %s passages; %s e-text records in %s" % (a.doc, "{:,}".format(p["passages"]), "{:,}".format(p["records"]),
                                                         raw))
    print("  to set: the engine on %s, the quality (%.2f) on %s (%s of them below 0.5, which the reader marks hard to "
          "read)" % ("{:,}".format(p["engine"]), ETEXT_QUALITY, "{:,}".format(p["quality"]), "{:,}".format(p["below_half"])))
    if p["differs"] or p["no_record"]:
        print("  left as they are: %d whose text is not the record's, %d with no e-text record"
              % (p["differs"], p["no_record"]))
    if not p["changes"]:
        print("VERDICT: nothing to change"); print("NEXT: "); return 0
    if not a.apply:
        print("VERDICT: %d passage(s) to mend (their text and translations are not touched)" % len(p["changes"]))
        print("NEXT: python scripts\\heal_etext_meta.py --doc %s --apply" % a.doc)
        return 0
    busy = busy_with(a.doc)
    if busy:
        print("REFUSE: the dashboard changes %s now (%s): run this when it is done"
              % (a.doc, ", ".join(str(j.get("kind")) for j in busy)))
        print("VERDICT: not now"); print("NEXT: python scripts\\heal_etext_meta.py --doc %s --apply" % a.doc)
        return 1
    dst = backup(a.db, a.backup_dir, a.doc, stamp)
    if not dst:
        print("REFUSE: the backup failed; nothing was changed."); print("VERDICT: not done"); return 1
    logp = Path(a.log_dir) / ("etext_meta_%s_%s.jsonl" % (re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc), stamp))
    logp.parent.mkdir(parents=True, exist_ok=True)
    with open(logp, "w", encoding="utf-8") as f:
        for c in p["changes"]:
            f.write(json.dumps(dict(c, doc=a.doc, mark=MARK), ensure_ascii=False) + "\n")
    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    try:
        with con:
            con.executemany("UPDATE passages SET quality_score = ?, ocr_engine = ? WHERE id = ?",
                            [(c["quality"], c["engine"], c["id"]) for c in p["changes"]])
    except sqlite3.Error as e:
        print("FAILED: %s. Nothing was changed (rolled back); the backup is %s" % (e, dst)); return 1
    finally:
        con.close()
    print("  done: %d passage(s); the backup %s; the values before: %s" % (len(p["changes"]), dst, logp))
    print("VERDICT: %s's passages now say they are an e-text" % a.doc)
    print("NEXT: python scripts\\corpus_sync.py   (the plan; then --apply: the site's reader stops calling it OCR)")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
