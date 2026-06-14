#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_passages.py — Context-aware Sanskrit passage translation.

Phase 3 upgrade:
- Fetches 5 preceding verse translations as context window for each passage
- Passes doc metadata (category, chandas, text_type, verse_ref, chapter) to LLM
- Translates verse-by-verse (not page-blob) for precision
- Skips noise/frontmatter automatically
- Updates FTS on every translation write (Bug B6 fix)
- Stores engine name in passages.engine column
"""
from __future__ import annotations
import argparse, sqlite3, time, sys

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

from normalize_text import normalize_sanskrit
from text_filters import should_translate, clean_for_mt, is_translation_boilerplate
from infer_mt import translate_batch
from db_utils import ensure_schema, migrate_schema

# How many preceding verse translations to pass as context
CONTEXT_WINDOW = 5


def _get_doc_meta(con: sqlite3.Connection, doc: str) -> dict:
    """Fetch doc-level metadata."""
    row = con.execute(
        "SELECT id, category FROM docs WHERE code=?", (doc,)
    ).fetchone()
    if not row:
        return {"id": None, "category": None}
    return {"id": row[0], "category": row[1]}


def _fetch_context(
    con: sqlite3.Connection,
    doc: str,
    page_no: int,
    idx: int,
    n: int = CONTEXT_WINDOW,
) -> list[dict]:
    """Fetch the N most recent translated verses before this one."""
    rows = con.execute("""
        SELECT p.verse_ref, p.text, p.translation, p.page_no, p.idx
        FROM passages p
        JOIN docs d ON d.id = p.doc_id
        WHERE d.code = ?
          AND TRIM(COALESCE(p.translation, '')) <> ''
          AND (p.page_no < ? OR (p.page_no = ? AND p.idx < ?))
        ORDER BY p.page_no DESC, p.idx DESC
        LIMIT ?
    """, (doc, page_no, page_no, idx, n)).fetchall()
    return [
        {
            "verse_ref":   r[0],
            "text":        r[1],
            "translation": r[2],
            "page_no":     r[3],
            "idx":         r[4],
        }
        for r in reversed(rows)  # chronological order
    ]


def _update_fts(cur: sqlite3.Cursor, rowid: int, text: str, iast: str, translation: str):
    """Update FTS index row after translation."""
    cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rowid,))
    cur.execute(
        "INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",
        (rowid, text or "", iast or "", translation or "")
    )


def main():
    ap = argparse.ArgumentParser(
        description="Translate Sanskrit passages with context window"
    )
    ap.add_argument("--db",         default="data/context.db")
    ap.add_argument("--doc",        required=True)
    ap.add_argument("--since-page", type=int,   default=1)
    ap.add_argument("--until-page", type=int,   default=999999)
    ap.add_argument("--sleep",      type=float, default=0.6)
    ap.add_argument("--engine",     default=None)
    ap.add_argument("--no-skip",    action="store_true",
                    help="translate even passages with low Devanagari density")
    ap.add_argument("--min-dev",    type=float, default=0.05)
    ap.add_argument("--limit",      type=int,   default=None)
    ap.add_argument("--context",    type=int,   default=CONTEXT_WINDOW,
                    help="number of preceding verses to pass as context")
    ap.add_argument("--retranslate", action="store_true",
                    help="re-translate passages that already have a translation")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    ensure_schema(con)
    migrate_schema(con)

    # Resolve doc metadata
    meta = _get_doc_meta(con, args.doc)
    if meta["id"] is None:
        print(f"ERROR: doc '{args.doc}' not found in DB")
        sys.exit(1)

    engine = args.engine or None  # None → uses MT_ENGINE env var

    # Columns available (handle both old and new schema)
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    has_verse_ref  = "verse_ref"  in cols
    has_chapter    = "chapter"    in cols
    has_chandas    = "chandas"    in cols
    has_text_type  = "text_type"  in cols
    has_iast       = "iast"       in cols
    has_engine_col = "engine"     in cols
    has_tr_score   = "translation_score" in cols

    # Select passages to translate
    translation_filter = "" if args.retranslate else \
        "AND COALESCE(TRIM(p.translation),'')=''"

    extra_cols = ", ".join([
        c for c in ["p.verse_ref","p.chapter","p.chandas","p.text_type","p.iast","p.quality_score"]
        if c.split(".")[1] in cols
    ])
    if extra_cols:
        extra_cols = ", " + extra_cols

    rows = list(con.execute(f"""
        SELECT p.rowid, p.page_no, p.idx, p.text{extra_cols}
        FROM passages p
        JOIN docs d ON d.id = p.doc_id
        WHERE d.code = ?
          {translation_filter}
          AND p.page_no BETWEEN ? AND ?
          AND COALESCE(p.text_type, 'mula') NOT IN ('noise', 'frontmatter')
        ORDER BY p.page_no, p.idx
    """, (args.doc, args.since_page, args.until_page)))

    if not rows:
        print("todo = 0 rows")
        return

    # Build todo list
    todo = []
    for row in rows:
        rowid, page_no, idx, text = row[0], row[1], row[2], row[3]
        rest = {
            "verse_ref":     row[4] if has_verse_ref  and len(row) > 4 else None,
            "chapter":       row[5] if has_chapter    and len(row) > 5 else None,
            "chandas":       row[6] if has_chandas    and len(row) > 6 else None,
            "text_type":     row[7] if has_text_type  and len(row) > 7 else None,
            "iast":          row[8] if has_iast        and len(row) > 8 else None,
            "quality_score": row[9] if len(row) > 9 else 0.0,
        }

        normed = normalize_sanskrit(text or "")
        if not args.no_skip and not should_translate(normed, min_dev=args.min_dev):
            continue
        cleaned = clean_for_mt(normed)
        if not cleaned:
            continue

        todo.append((rowid, page_no, idx, cleaned, rest))

    if args.limit:
        todo = todo[:args.limit]

    print(f"doc={args.doc!r}  engine={engine or 'default'}  todo={len(todo)} verses")
    if not todo:
        return

    # Translate one verse at a time for maximum context precision
    cur = con.cursor()
    ok_count = 0

    for i, (rowid, page_no, idx, cleaned, meta_row) in enumerate(todo, 1):
        try:
            # Fetch context window for this verse
            context_verses = _fetch_context(con, args.doc, page_no, idx, n=args.context)

            # Translate (batch of 1 for per-verse context)
            outs = translate_batch(
                con,
                [cleaned],
                engine=engine,
                iast_list=[meta_row.get("iast") or ""],
                context_list=[context_verses] if context_verses else None,
                doc_code=args.doc,
                category=meta["category"],
                chapters=[meta_row.get("chapter")],
                verse_refs=[meta_row.get("verse_ref")],
                chandas_list=[meta_row.get("chandas")],
                text_types=[meta_row.get("text_type")],
            )
            translation = outs[0] if outs else ""

            # Score translation quality
            tr_score = None
            if translation:
                from text_filters import is_translation_boilerplate
                if is_translation_boilerplate(translation):
                    print(f"  [SKIP-JUNK] p{page_no}.{idx}: {translation[:60]!r}")
                    translation = ""  # don't store garbage
                else:
                    # Rough quality: ratio of length makes sense
                    ratio = len(translation) / max(1, len(cleaned))
                    tr_score = round(min(1.0, max(0.0, ratio / 5.0)), 3)

            # Write back to DB
            update_parts = ["translation=?"]
            update_vals  = [translation]

            if has_engine_col and engine:
                update_parts.append("engine=?")
                update_vals.append(engine)
            if has_tr_score and tr_score is not None:
                update_parts.append("translation_score=?")
                update_vals.append(tr_score)

            update_vals.append(rowid)
            cur.execute(
                f"UPDATE passages SET {', '.join(update_parts)} WHERE rowid=?",
                update_vals
            )

            # Fix Bug B6: update FTS in sync
            iast_val = meta_row.get("iast") or ""
            _update_fts(cur, rowid, cleaned, iast_val, translation or "")

            con.commit()
            ok_count += 1

            ref_str = f"[{meta_row.get('verse_ref')}] " if meta_row.get("verse_ref") else ""
            ctx_str = f" ctx={len(context_verses)}" if context_verses else ""
            chan_str = f" [{meta_row.get('chandas')}]" if meta_row.get("chandas") else ""
            print(f"  [{i}/{len(todo)}] p{page_no}.{idx} {ref_str}{chan_str}{ctx_str}: "
                  f"{(translation or '[empty]')[:60]!r}")

            time.sleep(args.sleep)

        except Exception as exc:
            print(f"  [ERR] p{page_no}.{idx}: {exc}")
            time.sleep(args.sleep)

    print(f"\nDone. {ok_count}/{len(todo)} passages translated.")


if __name__ == "__main__":
    main()
