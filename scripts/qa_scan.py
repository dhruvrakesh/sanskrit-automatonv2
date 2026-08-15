#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_scan.py — Phase Q2: score every stored translation with the heuristic QA
scorer (free, no API calls) and backfill provenance for pre-Phase-Q rows.

What it does:
  1. For every passage with a non-empty translation, computes
     text_filters.score_translation_quality(text, translation) and writes it
     to passages.translation_qa.
  2. Backfills passages.mt_prompt_version = 'v1-legacy' where a translation
     exists but no prompt version was recorded (everything translated before
     2026-07-20).
  3. Prints a per-doc QA histogram so weak docs and style-stale rows are
     visible at a glance.

Read-only until you pass --write. Safe to re-run any time (idempotent).
Do NOT run while a translate job is writing (SQLite single-writer).

Usage:
  python scripts/qa_scan.py                 # report only, whole corpus
  python scripts/qa_scan.py --doc MBh01     # report only, one doc
  python scripts/qa_scan.py --write         # persist scores + backfill
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
from text_filters import score_translation_quality

BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def bar(n: int, total: int, width: int = 30) -> str:
    filled = int(round(width * n / max(1, total)))
    return "#" * filled + "." * (width - filled)


def main():
    ap = argparse.ArgumentParser(description="Heuristic QA scan of stored translations")
    ap.add_argument("--db",  default="data/context.db")
    ap.add_argument("--doc", default=None, help="limit to one doc code")
    ap.add_argument("--write", action="store_true",
                    help="persist translation_qa + backfill mt_prompt_version "
                         "(default: report only)")
    ap.add_argument("--below", type=float, default=None,
                    help="also list passages scoring below this (max 20 shown)")
    ap.add_argument("--tag-prompt-version", default=None, metavar="VERSION",
                    help="with --doc and --write: set mt_prompt_version=VERSION on "
                         "this doc's translated rows instead of the v1-legacy "
                         "backfill. Use for runs whose write-path predates "
                         "Phase Q but whose prompt was already newer (e.g. the "
                         "2026-07-20 MBh01 run: --doc MBh01 "
                         "--tag-prompt-version v2-2026-07-20 --write).")
    ap.add_argument("--lang", default="en",
                    help="Which translations to score. 'en' (default) scores "
                         "passages.translation with the English scorer. Any "
                         "other code (e.g. 'hi') scores translations_l10n rows "
                         "of that language with the language-aware scorer.")
    args = ap.parse_args()

    if args.tag_prompt_version and not args.doc:
        sys.exit("--tag-prompt-version requires --doc (refusing corpus-wide tag).")

    con = sqlite3.connect(args.db)
    ensure_schema(con)
    migrate_schema(con)

    LANG = (args.lang or "en").strip()
    IS_L10N = LANG != "en"

    where_doc = "AND d.code = ?" if args.doc else ""
    params: list = [args.doc] if args.doc else []

    if IS_L10N:
        rows = con.execute(
            f"""SELECT l.id, d.code, p.page_no, p.idx, p.text, l.translation,
                       l.mt_prompt_version
                FROM translations_l10n l
                JOIN passages p ON p.id = l.passage_id
                JOIN docs d ON d.id = p.doc_id
                WHERE l.lang = ? AND TRIM(COALESCE(l.translation,'')) <> ''
                  {where_doc}
                ORDER BY d.code, p.page_no, p.idx""",
            [LANG] + params,
        ).fetchall()
    else:
        rows = con.execute(
            f"""SELECT p.id, d.code, p.page_no, p.idx, p.text, p.translation,
                       p.mt_prompt_version
                FROM passages p JOIN docs d ON d.id = p.doc_id
                WHERE TRIM(COALESCE(p.translation,'')) <> '' {where_doc}
                ORDER BY d.code, p.page_no, p.idx""",
            params,
        ).fetchall()

    if not rows:
        print(f"No translated passages found (lang={LANG}).")
        return

    per_doc: dict[str, list[float]] = {}
    updates: list[tuple[float, int]] = []
    backfills: list[int] = []
    low: list[tuple[str, int, int, float, str]] = []

    for pid, code, page_no, idx, text, translation, pv in rows:
        qa = score_translation_quality(text or "", translation or "", lang=LANG)
        per_doc.setdefault(code, []).append(qa)
        updates.append((qa, pid))
        if not (pv or "").strip():
            backfills.append(pid)
        if args.below is not None and qa < args.below:
            low.append((code, page_no, idx, qa, (translation or "")[:70]))

    print(f"Scanned {len(rows)} translated passages (lang={LANG}) "
          f"across {len(per_doc)} doc(s).\n")

    for code in sorted(per_doc):
        scores = per_doc[code]
        n = len(scores)
        mean = sum(scores) / n
        print(f"{code:<28} n={n:<6} mean qa={mean:.3f}")
        for lo, hi in BUCKETS:
            k = sum(1 for s in scores if lo <= s < hi)
            label = f"  {lo:.1f}-{min(hi,1.0):.1f}"
            print(f"{label:<10} {bar(k, n)} {k}")
        print()

    if args.below is not None and low:
        print(f"Passages below qa {args.below} (showing up to 20 of {len(low)}):")
        for code, page_no, idx, qa, snippet in low[:20]:
            print(f"  {code} p{page_no}.{idx}  qa={qa:.3f}  {snippet!r}")
        print()

    if args.write:
        cur = con.cursor()
        table = "translations_l10n" if IS_L10N else "passages"
        cur.executemany(f"UPDATE {table} SET translation_qa=? WHERE id=?", updates)
        n_backfill = 0
        if backfills:
            version = args.tag_prompt_version or "v1-legacy"
            cur.executemany(
                f"UPDATE {table} SET mt_prompt_version=? WHERE id=?",
                [(version, pid) for pid in backfills],
            )
            n_backfill = len(backfills)
        con.commit()
        print(f"Wrote translation_qa for {len(updates)} passages; "
              f"tagged mt_prompt_version='{args.tag_prompt_version or 'v1-legacy'}' "
              f"on {n_backfill} previously untagged rows.")
    else:
        n_backfill = sum(1 for _ in backfills)
        print(f"Report only — nothing written. "
              f"(--write would set {len(updates)} QA scores and backfill "
              f"{n_backfill} legacy prompt versions.)")


if __name__ == "__main__":
    main()
