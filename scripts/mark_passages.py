#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
mark_passages.py  (2026-10-16)  MARK_PASSAGES_2026_10_16

A person's tag for the passages of some pages: text_type 'noise' (what the database holds is not what the page
prints: a vision OCR that wrote another text on a faded page, as on page 18 of the Tantrik Texts vol. I, where
gemini-2.5-flash wrote the opening of the Mahabharata's Adi Parva on a title page too faint to read), or 'frontmatter'
(title pages, prefaces the classifiers missed). Only text_type changes: the text, the translations and the scholarly
rows are not touched. The translators and the scholarly English leave such passages out; the site's reader folds
'noise' (PassageBlock.tsx), after the next mirror sync.

A dry run by default. --apply writes, through db_utils.connect (WAL, busy_timeout). Every change is logged
(data/mark_passages_log.jsonl: the passage, its old type, the new one, the reason, when); --undo puts the logged old
types back (and is logged too).

  python scripts\\mark_passages.py --doc tantric_texts_series_edited_by_arthur_av --pages 18 --type noise --reason "..."
  python scripts\\mark_passages.py --doc tantric_texts_series_edited_by_arthur_av --pages 18 --type noise --reason "..." --apply
  python scripts\\mark_passages.py --doc tantric_texts_series_edited_by_arthur_av --pages 18 --undo --apply
"""
from __future__ import annotations
import argparse, datetime, json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARK = "MARK_PASSAGES_2026_10_16"
TYPES = ("noise", "frontmatter")


def parse_list(s):
    """'18' or '17-19,21' -> sorted ints; None for None."""
    if not s:
        return None
    out = set()
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def targets(con, doc: str, pages: list, idxs=None) -> list:
    """[(passage_id, page, idx, text_type, text)] of the doc's passages on those pages (and idxs), in order."""
    row = con.execute("SELECT id FROM docs WHERE code = ?", (doc,)).fetchone()
    if not row:
        return []
    q = ("SELECT id, page_no, idx, COALESCE(text_type, ''), COALESCE(text, '') FROM passages WHERE doc_id = ? AND "
         "page_no IN (%s)" % ",".join("?" * len(pages)))
    rows = con.execute(q + " ORDER BY page_no, idx", [row[0]] + list(pages)).fetchall()
    return [r for r in rows if idxs is None or r[2] in idxs]


def logged(log: Path, doc: str) -> dict:
    """{passage_id: the last logged change of it} for this doc."""
    out = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("doc") == doc and d.get("passage_id") is not None:
                out[d["passage_id"]] = d
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="A person's text_type for the passages of some pages (a dry run unless --apply)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--pages", required=True, help="18 or 17-19,21")
    ap.add_argument("--idx", default=None, help="only these passages of the pages: 1 or 1-2")
    ap.add_argument("--type", choices=TYPES, default=None)
    ap.add_argument("--reason", default=None, help="why (kept in the log)")
    ap.add_argument("--undo", action="store_true", help="put back the old types the log has for these passages")
    ap.add_argument("--log", default="data/mark_passages_log.jsonl")
    ap.add_argument("--by", default="a person")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")   # a console that cannot print Devanagari gets escapes
    except Exception:
        pass
    if not a.undo and (not a.type or not (a.reason or "").strip()):
        print("REFUSE: --type and --reason are needed (or --undo)"); print("VERDICT: nothing written"); print("NEXT: ")
        return 1
    if not Path(a.db).exists():
        print("REFUSE: %s not found (run from the repo root)" % a.db); print("VERDICT: nothing written"); print("NEXT: ")
        return 2
    import sqlite3
    import db_utils
    pages, idxs = parse_list(a.pages), parse_list(a.idx)
    log = Path(a.log)
    con = (db_utils.connect(a.db) if a.apply else
           sqlite3.connect(Path(a.db).resolve().as_uri() + "?mode=ro", uri=True))
    try:
        rows = targets(con, a.doc, pages, idxs)
        if not rows:
            print("REFUSE: %s has no passages on page(s) %s" % (a.doc, a.pages)); print("VERDICT: nothing written")
            print("NEXT: "); return 1
        before = logged(log, a.doc)
        plan = []
        for pid, page, idx, cur, text in rows:
            if a.undo:
                d = before.get(pid)
                if d and d.get("new") == cur and d.get("old") != cur:
                    plan.append((pid, page, idx, cur, d.get("old") or None, text))
            elif cur != a.type:
                plan.append((pid, page, idx, cur, a.type, text))
        print("mark_passages.py  %s  %s  %s pages %s%s" % (MARK, "APPLY" if a.apply else "DRY RUN (nothing written)", a.doc,
                                                         a.pages, (" idx %s" % a.idx) if a.idx else ""))
        for pid, page, idx, cur, new, text in plan:
            print("  p%d.%d  %s -> %s   %s" % (page, idx, cur or "-", new or "-",
                                             text.replace("\n", " / ")[:70]))
        if not plan:
            print("VERDICT: nothing to change (%d passage(s) already as asked)" % len(rows))
            print("NEXT: ")
            return 0
        if not a.apply:
            print("VERDICT: %d passage(s) would change; nothing written" % len(plan))
            print("NEXT: the same command with --apply")
            return 0
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            for pid, page, idx, cur, new, _t in plan:
                con.execute("UPDATE passages SET text_type = ? WHERE id = ?", (new, pid))
                f.write(json.dumps({"at": now(), "doc": a.doc, "passage_id": pid, "page": page, "idx": idx,
                                    "old": cur or None, "new": new, "reason": "undo" if a.undo else a.reason,
                                    "by": a.by, "mark": MARK}) + "\n")
            con.commit()
    finally:
        con.close()
    print("VERDICT: %d passage(s) changed; the log: %s" % (len(plan), log))
    print("NEXT: the site shows it after the next mirror sync (SanskritCorpusMirror); --undo --apply puts it back")
    return 0


if __name__ == "__main__":
    sys.exit(main())
