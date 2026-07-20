#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retranslate.py — Phase Q3: flag translations for redo WITHOUT destroying them.

Selects passages by QA score and/or prompt version, archives their current
translation into translation_history (with a reason), then clears the
translation slot so the normal translate job refills it under the current
prompt/engine. Nothing is ever silently overwritten; every superseded
attempt remains queryable for before/after comparison.

Selection filters (combine freely):
  --doc CODE              one doc (or --all for the whole corpus)
  --below-qa 0.6          translation_qa below threshold (run qa_scan --write first)
  --prompt-version v1-legacy   rows translated under a given prompt version
  --limit N               cap the batch

Safety:
  - default is a dry run (prints what WOULD move); nothing changes without --yes
  - refuses to run without at least one selection filter beyond --doc/--all
  - do NOT run while a translate job is writing (SQLite single-writer)

After running, refill with:
  python scripts/translate_passages.py --doc CODE --engine gemini:gemini-2.5-flash

Usage:
  python scripts/retranslate.py --doc shiksha --below-qa 0.6
  python scripts/retranslate.py --doc shiksha --below-qa 0.6 --yes
  python scripts/retranslate.py --all --prompt-version v1-legacy --limit 500 --yes
"""
from __future__ import annotations
import argparse
import sqlite3
import sys

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

from db_utils import ensure_schema, migrate_schema


def main():
    ap = argparse.ArgumentParser(description="Archive + clear translations for redo")
    ap.add_argument("--db",  default="data/context.db")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", default=None, help="doc code")
    g.add_argument("--all", action="store_true", help="whole corpus")
    ap.add_argument("--below-qa", type=float, default=None,
                    help="select rows with translation_qa below this")
    ap.add_argument("--prompt-version", default=None,
                    help="select rows translated under this prompt version "
                         "(e.g. v1-legacy)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--yes", action="store_true",
                    help="actually archive+clear (default: dry run)")
    args = ap.parse_args()

    if args.below_qa is None and args.prompt_version is None:
        sys.exit("Refusing: give at least one selection filter "
                 "(--below-qa and/or --prompt-version). "
                 "Clearing a whole doc unconditionally is what wipe_doc.py is for.")

    con = sqlite3.connect(args.db)
    ensure_schema(con)
    migrate_schema(con)

    where = ["TRIM(COALESCE(p.translation,'')) <> ''"]
    params: list = []
    reasons: list[str] = []
    if args.doc:
        where.append("d.code = ?")
        params.append(args.doc)
    if args.below_qa is not None:
        where.append("p.translation_qa IS NOT NULL AND p.translation_qa < ?")
        params.append(args.below_qa)
        reasons.append(f"qa<{args.below_qa}")
    if args.prompt_version is not None:
        where.append("COALESCE(p.mt_prompt_version,'') = ?")
        params.append(args.prompt_version)
        reasons.append(f"prompt-upgrade:{args.prompt_version}")
    reason = ";".join(reasons)

    limit_sql = f"LIMIT {int(args.limit)}" if args.limit else ""
    rows = con.execute(
        f"""SELECT p.id, d.code, p.page_no, p.idx, p.translation_qa,
                   p.mt_prompt_version, substr(p.translation,1,60)
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE {' AND '.join(where)}
            ORDER BY d.code, p.page_no, p.idx
            {limit_sql}""",
        params,
    ).fetchall()

    if not rows:
        print("Nothing matches the selection — no rows to retranslate.")
        return

    per_doc: dict[str, int] = {}
    for _, code, *_ in rows:
        per_doc[code] = per_doc.get(code, 0) + 1
    print(f"Selected {len(rows)} translated passages "
          f"(reason: {reason}):")
    for code in sorted(per_doc):
        print(f"  {code:<28} {per_doc[code]}")
    print("\nSample:")
    for pid, code, page_no, idx, qa, pv, snippet in rows[:10]:
        print(f"  {code} p{page_no}.{idx}  qa={qa}  prompt={pv}  {snippet!r}")

    if not args.yes:
        print(f"\nDry run — nothing changed. Re-run with --yes to archive these "
              f"{len(rows)} translations to translation_history and clear them "
              f"for retranslation.")
        return

    cur = con.cursor()
    ids = [r[0] for r in rows]
    n_archived = 0
    for pid in ids:
        cur.execute(
            """INSERT INTO translation_history(passage_id, translation, engine,
                   mt_prompt_version, translation_score, translation_qa,
                   translated_at, reason)
               SELECT id, translation, engine, mt_prompt_version,
                      translation_score, translation_qa, translated_at, ?
               FROM passages WHERE id=?""",
            (reason, pid),
        )
        n_archived += cur.rowcount
        cur.execute(
            """UPDATE passages
               SET translation='', translation_score=NULL, translation_qa=NULL,
                   mt_prompt_version=NULL, translated_at=NULL
               WHERE id=?""",
            (pid,),
        )
        # Keep FTS consistent: re-index this row with an empty translation.
        row = cur.execute(
            "SELECT text, iast FROM passages WHERE id=?", (pid,)
        ).fetchone()
        cur.execute("DELETE FROM passages_fts WHERE rowid=?", (pid,))
        cur.execute(
            "INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",
            (pid, (row[0] or "") if row else "", (row[1] or "") if row else "", ""),
        )
    con.commit()
    print(f"\nArchived {n_archived} translations to translation_history and "
          f"cleared them. Refill with:\n"
          f"  python scripts/translate_passages.py --doc <CODE> "
          f"--engine gemini:gemini-2.5-flash")


if __name__ == "__main__":
    main()
