#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
classify_apparatus.py  (2026-10-03)  APPARATUS_TAG_2026_10_03

Tags an edition's footnote apparatus - numbered variant readings with manuscript
sigla, e.g. "<25> sukham P. <26> agnivrddhau vinasasca P.", or "B does not give
Slokas 9-17" - as text_type='noise', so it is no longer translated, exported,
scored or counted as a verse.

Measured 2026-10-03 (diag_text_hygiene.py): 36 such rows in the corpus (35
Mallapurana, 1 HAYASHIRSHA). 15 had already been translated into English and 15
into Hindi. One of them produced the stored "translation" "[The Sanskrit verse to
be translated is missing from the prompt.]" (translation_qa 0.85).

HOW IT DIFFERS FROM classify_noise.py: classify_noise only touches UNTRANSLATED
rows, because its rule (almost no letters) cannot be wrong about content. This
rule is about STRUCTURE (numeral + reading + siglum, at least twice), so it can
safely include rows that were translated: the stored translation is kept, not
deleted; only text_type changes, and every exporter, the translator and QA
already skip 'noise'.

SAFE: dry-run by default. --apply writes a reversal manifest first
(data/apparatus_tagged_<stamp>.json: id, doc, previous text_type) and --undo
restores exactly those rows. Back up first (RUNBOOK 5). Run with the dashboard idle.

  python scripts\\classify_apparatus.py --show
  python scripts\\classify_apparatus.py --doc Mallapurana --show
  python scripts\\classify_apparatus.py --doc Mallapurana --apply
  python scripts\\classify_apparatus.py --undo data\\apparatus_tagged_20261003_101500.json
  python scripts\\classify_apparatus.py --reconcile data\\apparatus_tagged_20261003_071721.json

APPARATUS_TAG2_2026_10_03: the rule now excludes chapter colophons and rows that
open with a danda-marked verse (3 colophons and 1 verse were tagged on
2026-10-03); --reconcile restores exactly the rows the refined rule rejects.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_text_hygiene import is_apparatus  # noqa: E402

MARK = "APPARATUS_TAG_2026_10_03"


def find(con: sqlite3.Connection, doc: str | None = None) -> list[tuple]:
    """[(id, doc_code, page_no, idx, previous_text_type, translated_en, text)] for apparatus rows."""
    sql = """SELECT p.id, d.code, p.page_no, p.idx, COALESCE(p.text_type,'mula'),
                    CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END, p.text
             FROM passages p JOIN docs d ON d.id=p.doc_id
             WHERE COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"""
    params = []
    if doc:
        sql += " AND d.code=?"; params.append(doc)
    return [r for r in con.execute(sql, params) if is_apparatus(r[6] or "")]


def apply_tags(con: sqlite3.Connection, hits: list[tuple], manifest: Path) -> int:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"marker": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"),
                                    "rows": [{"id": h[0], "doc": h[1], "page": h[2], "idx": h[3], "prev": h[4]}
                                             for h in hits]}, indent=1), encoding="utf-8")
    con.executemany("UPDATE passages SET text_type='noise' WHERE id=?", [(h[0],) for h in hits])
    con.commit()
    return len(hits)


def undo(con: sqlite3.Connection, manifest: Path) -> int:
    rows = json.loads(manifest.read_text(encoding="utf-8"))["rows"]
    con.executemany("UPDATE passages SET text_type=? WHERE id=? AND text_type='noise'",
                    [(r["prev"], r["id"]) for r in rows])
    con.commit()
    return len(rows)


def reconcile(con: sqlite3.Connection, manifest: Path) -> list[tuple]:
    """APPARATUS_TAG2_2026_10_03: re-test every row a manifest tagged, with the
    current rule; restore the previous text_type of rows that no longer qualify.
    Returns [(id, page, idx, prev)] restored. Rows tagged by hand are unaffected."""
    rows = json.loads(manifest.read_text(encoding="utf-8"))["rows"]
    restored = []
    for r in rows:
        cur = con.execute("SELECT text, text_type FROM passages WHERE id=?", (r["id"],)).fetchone()
        if not cur or cur[1] != "noise":
            continue
        if not is_apparatus(cur[0] or ""):
            con.execute("UPDATE passages SET text_type=? WHERE id=?", (r["prev"], r["id"]))
            restored.append((r["id"], r["page"], r["idx"], r["prev"]))
    con.commit()
    return restored


def _connect(db: str) -> sqlite3.Connection:
    try:
        from db_utils import connect
        return connect(db)
    except Exception:
        con = sqlite3.connect(db, timeout=30)
        con.execute("PRAGMA busy_timeout=30000")
        return con


def main() -> int:
    ap = argparse.ArgumentParser(description="Tag footnote-apparatus rows as noise (dry-run by default)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", default=None, help="a manifest written by --apply")
    ap.add_argument("--reconcile", default=None,
                    help="a manifest: restore the rows the CURRENT rule no longer calls apparatus")
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    con = _connect(args.db)
    try:
        if args.reconcile:
            res = reconcile(con, Path(args.reconcile))
            for rid, pg, ix, prev in res:
                print("  restored id %d p%s.%s -> %s" % (rid, pg, ix, prev))
            print("Restored %d row(s) the refined rule no longer tags (APPARATUS_TAG2_2026_10_03)." % len(res))
            return 0
        if args.undo:
            n = undo(con, Path(args.undo))
            print("Restored text_type on %d rows from %s." % (n, args.undo)); return 0
        hits = find(con, args.doc)
        by: dict = {}
        for h in hits:
            b = by.setdefault(h[1], [0, 0]); b[0] += 1; b[1] += h[5]
        print("Apparatus rows to tag as 'noise'  (%s):" % ("APPLY" if args.apply else "DRY-RUN"))
        if not hits:
            print("  none found."); return 0
        for code, (n, tr) in sorted(by.items(), key=lambda kv: -kv[1][0]):
            print("  %-40s %4d rows  (%d already translated; translations are kept)" % (code, n, tr))
        if args.show:
            for h in hits[:40]:
                print("    id %d  %s p%s.%s  [%s]  %s" % (h[0], h[1][:24], h[2], h[3], h[4],
                                                       " ".join((h[6] or "").split())[:80]))
        if not args.apply:
            print("\nDRY-RUN. Inspect with --show, back up, then --apply. Reversible with --undo.")
            return 0
        man = Path("data") / ("apparatus_tagged_%s.json" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        n = apply_tags(con, hits, man)
        print("\nTagged %d rows as 'noise'. Reversal manifest: %s" % (n, man)); return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
