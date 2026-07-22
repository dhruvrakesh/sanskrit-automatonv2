#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_passages.py -- Context-aware Sanskrit passage translation.

Phase 4 upgrades:
- Live progress output to data/translation_progress.json (for UI dashboard)
- Runtime config from data/translation_config.json (mid-run model switch + pause)
- Quality threshold gate: skips passages with quality_score below --min-quality
- Gemini 2.5 Flash as default engine

Phase Q (2026-07-20):
- Provenance: writes mt_prompt_version + translated_at + translation_qa with
  every translation (heuristic QA from text_filters.score_translation_quality).
- Supersede, never destroy: when --retranslate overwrites an existing
  translation, the old one is archived to translation_history first.
- --min-quality default raised 0.0 → 0.35: OCR sludge is no longer attempted
  by default (pass --min-quality 0 to restore the old behaviour).
"""
from __future__ import annotations
import argparse, sqlite3, time, sys, json, os
from pathlib import Path
from datetime import datetime, timezone

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

from normalize_text import normalize_sanskrit
from text_filters import (should_translate, clean_for_mt,
                          is_translation_boilerplate, score_translation_quality)
from infer_mt import translate_batch, PROMPT_VERSION, QuotaExhausted
from db_utils import ensure_schema, migrate_schema

CONTEXT_WINDOW = 5
RECENT_MAX     = 20

_PROGRESS_PATH = Path("data/translation_progress.json")
_CONFIG_PATH   = Path("data/translation_config.json")


def _read_runtime_cfg():
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_progress(data):
    try:
        _PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _PROGRESS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_PROGRESS_PATH)
    except Exception:
        pass


def _get_doc_meta(con, doc):
    row = con.execute(
        "SELECT id, category FROM docs WHERE code=?", (doc,)
    ).fetchone()
    if not row:
        return {"id": None, "category": None}
    return {"id": row[0], "category": row[1]}


def _fetch_context(con, doc, page_no, idx, n=CONTEXT_WINDOW):
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
        {"verse_ref": r[0], "text": r[1], "translation": r[2],
         "page_no": r[3], "idx": r[4]}
        for r in reversed(rows)
    ]


def _update_fts(cur, rowid, text, iast, translation):
    cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rowid,))
    cur.execute(
        "INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",
        (rowid, text or "", iast or "", translation or "")
    )


def _archive_previous_translation(con, cur, rowid, reason="retranslate-overwrite"):
    """Phase Q: move an existing translation into translation_history before it
    is overwritten. No-op if the passage has no non-empty translation."""
    prev = con.execute(
        "SELECT translation, engine, mt_prompt_version, translation_score, "
        "translation_qa, translated_at FROM passages WHERE rowid=?",
        (rowid,),
    ).fetchone()
    if not prev or not (prev[0] or "").strip():
        return False
    cur.execute(
        "INSERT INTO translation_history(passage_id, translation, engine, "
        "mt_prompt_version, translation_score, translation_qa, translated_at, reason) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (rowid, prev[0], prev[1], prev[2], prev[3], prev[4], prev[5], reason),
    )
    return True


def main():
    global _PROGRESS_PATH, _CONFIG_PATH  # declared before first use (Python 3.12+)
    ap = argparse.ArgumentParser(description="Translate Sanskrit passages")
    ap.add_argument("--db",           default="data/context.db")
    ap.add_argument("--doc",          required=True)
    ap.add_argument("--since-page",   type=int,   default=1)
    ap.add_argument("--until-page",   type=int,   default=999999)
    ap.add_argument("--sleep",        type=float, default=0.6)
    ap.add_argument("--engine",       default=None,
                    help="e.g. gemini:gemini-2.5-flash. Overridable mid-run via config JSON.")
    ap.add_argument("--no-skip",      action="store_true")
    ap.add_argument("--min-dev",      type=float, default=0.05)
    ap.add_argument("--min-quality",  type=float, default=0.35,
                    help="Skip passages with quality_score below this. "
                         "Default 0.35 (Phase Q) — skips bad OCR. "
                         "Pass 0 to disable the gate entirely.")
    ap.add_argument("--limit",        type=int,   default=None)
    ap.add_argument("--context",      type=int,   default=CONTEXT_WINDOW)
    ap.add_argument("--retranslate",  action="store_true",
                    help="Also process passages that already have a translation. "
                         "The old translation is archived to translation_history "
                         "before being replaced (Phase Q).")
    ap.add_argument("--max-consecutive-failures", type=int, default=15,
                    help="Abort the run after this many consecutive empty/"
                         "failed translations (0 = never abort). Catches "
                         "quota exhaustion and bad-source docs instead of "
                         "grinding through hundreds of doomed calls.")
    ap.add_argument("--progress",     default=str(_PROGRESS_PATH))
    ap.add_argument("--config",       default=str(_CONFIG_PATH))
    args = ap.parse_args()

    _PROGRESS_PATH = Path(args.progress)
    _CONFIG_PATH   = Path(args.config)

    con = sqlite3.connect(args.db)
    ensure_schema(con)
    migrate_schema(con)

    doc_meta = _get_doc_meta(con, args.doc)
    if doc_meta["id"] is None:
        print(f"ERROR: doc '{args.doc}' not found in DB")
        sys.exit(1)

    base_engine = args.engine or None

    cols          = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    has_verse_ref = "verse_ref"          in cols
    has_chapter   = "chapter"            in cols
    has_chandas   = "chandas"            in cols
    has_text_type = "text_type"          in cols
    has_iast      = "iast"               in cols
    has_eng_col   = "engine"             in cols
    has_tr_score  = "translation_score"  in cols

    translation_filter = ("" if args.retranslate
                          else "AND COALESCE(TRIM(p.translation),'')=''")

    extra_cols = ", ".join([
        c for c in
        ["p.verse_ref", "p.chapter", "p.chandas", "p.text_type", "p.iast", "p.quality_score"]
        if c.split(".")[1] in cols
    ])
    if extra_cols:
        extra_cols = ", " + extra_cols

    rows = list(con.execute(
        f"""SELECT p.rowid, p.page_no, p.idx, p.text{extra_cols}
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ?
              {translation_filter}
              AND p.page_no BETWEEN ? AND ?
              AND COALESCE(p.text_type, 'mula') NOT IN ('noise', 'frontmatter')
            ORDER BY p.page_no, p.idx""",
        (args.doc, args.since_page, args.until_page),
    ))

    if not rows:
        print("todo = 0 rows")
        _write_progress({
            "status": "done", "doc": args.doc,
            "verses_done": 0, "verses_total": 0,
            "skipped_quality": 0, "errors": 0, "recent": [],
        })
        return

    todo = []
    for row in rows:
        rowid, page_no, idx, text = row[0], row[1], row[2], row[3]
        rest = {
            "verse_ref":     row[4]  if has_verse_ref and len(row) > 4 else None,
            "chapter":       row[5]  if has_chapter   and len(row) > 5 else None,
            "chandas":       row[6]  if has_chandas   and len(row) > 6 else None,
            "text_type":     row[7]  if has_text_type and len(row) > 7 else None,
            "iast":          row[8]  if has_iast      and len(row) > 8 else None,
            "quality_score": row[9]  if len(row) > 9  else 0.0,
        }
        normed  = normalize_sanskrit(text or "")
        if not args.no_skip and not should_translate(normed, min_dev=args.min_dev):
            continue
        cleaned = clean_for_mt(normed)
        if not cleaned:
            continue
        todo.append((rowid, page_no, idx, cleaned, rest))

    if args.limit:
        todo = todo[:args.limit]

    print(f"doc={args.doc!r}  engine={base_engine or 'default'}  "
          f"todo={len(todo)} verses  min_quality={args.min_quality}  "
          f"prompt={PROMPT_VERSION}")
    if not todo:
        _write_progress({
            "status": "done", "doc": args.doc,
            "verses_done": 0, "verses_total": 0,
            "skipped_quality": 0, "errors": 0, "recent": [],
        })
        return

    started_at   = datetime.now(timezone.utc).isoformat()
    cur          = con.cursor()
    ok_count     = 0
    skip_quality = 0
    err_count    = 0
    consec_fail  = 0   # consecutive empty/failed results (streak breaker)
    aborted      = None
    recent       = []

    _write_progress({
        "status": "running",
        "doc": args.doc,
        "engine": base_engine or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"),
        "started_at": started_at,
        "updated_at": started_at,
        "verses_done": 0,
        "verses_total": len(todo),
        "skipped_quality": 0,
        "errors": 0,
        "current_page": None,
        "current_idx": None,
        "current_text": None,
        "current_translation": None,
        "current_quality": None,
        "min_quality": args.min_quality,
        "recent": [],
    })

    for i, (rowid, page_no, idx, cleaned, meta_row) in enumerate(todo, 1):
        try:
            # Read runtime config (engine switch / pause / skip list)
            cfg = _read_runtime_cfg()

            # Handle pause
            if cfg.get("paused"):
                print(f"  [PAUSED] waiting for resume...")
                _write_progress({
                    "status": "paused", "doc": args.doc,
                    "engine": cfg.get("engine", base_engine or ""),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "verses_done": ok_count, "verses_total": len(todo),
                    "skipped_quality": skip_quality, "errors": err_count,
                    "current_page": page_no, "current_idx": idx,
                    "current_text": cleaned[:200],
                    "current_translation": None,
                    "current_quality": meta_row.get("quality_score"),
                    "min_quality": args.min_quality,
                    "recent": recent,
                })
                while True:
                    time.sleep(2)
                    cfg = _read_runtime_cfg()
                    if not cfg.get("paused"):
                        print("  [RESUMED]")
                        break

            # User-skipped rowids (set from Queue tab)
            if rowid in cfg.get("skip_rowids", []):
                print(f"  [SKIP-UI] p{page_no}.{idx}: skipped by user")
                skip_quality += 1
                continue

            # Mid-run engine and threshold from runtime config
            active_engine      = cfg.get("engine") or base_engine or None
            active_min_quality = cfg.get("min_quality", args.min_quality)

            # Quality threshold gate
            quality = float(meta_row.get("quality_score") or 0.0)
            if active_min_quality > 0.0 and quality > 0.0 and quality < active_min_quality:
                print(f"  [SKIP-QUALITY] p{page_no}.{idx}: "
                      f"quality={quality:.3f} < {active_min_quality:.3f} "
                      f"-- OCR quality too low for accurate translation")
                skip_quality += 1
                _write_progress({
                    "status": "running", "doc": args.doc,
                    "engine": active_engine or "",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "verses_done": ok_count, "verses_total": len(todo),
                    "skipped_quality": skip_quality, "errors": err_count,
                    "current_page": page_no, "current_idx": idx,
                    "current_text": cleaned[:200],
                    "current_translation": (
                        f"[SKIPPED -- quality {quality:.2f} below threshold {active_min_quality:.2f}]"
                    ),
                    "current_quality": quality,
                    "min_quality": active_min_quality,
                    "recent": recent,
                })
                time.sleep(0.05)
                continue

            # Write "translating now" state
            _write_progress({
                "status": "running", "doc": args.doc,
                "engine": active_engine or os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "verses_done": ok_count, "verses_total": len(todo),
                "skipped_quality": skip_quality, "errors": err_count,
                "current_page": page_no, "current_idx": idx,
                "current_text": cleaned[:400],
                "current_translation": "translating...",
                "current_quality": quality,
                "current_context_n": 0,
                "min_quality": active_min_quality,
                "recent": recent,
            })

            # Fetch context + translate
            context_verses = _fetch_context(con, args.doc, page_no, idx, n=args.context)

            outs = translate_batch(
                con,
                [cleaned],
                engine=active_engine,
                iast_list=[meta_row.get("iast") or ""],
                context_list=[context_verses] if context_verses else None,
                doc_code=args.doc,
                category=doc_meta["category"],
                chapters=[meta_row.get("chapter")],
                verse_refs=[meta_row.get("verse_ref")],
                chandas_list=[meta_row.get("chandas")],
                text_types=[meta_row.get("text_type")],
            )
            translation = outs[0] if outs else ""

            tr_score = None
            tr_qa    = None
            if translation:
                if is_translation_boilerplate(translation):
                    print(f"  [SKIP-JUNK] p{page_no}.{idx}: {translation[:60]!r}")
                    translation = ""
                else:
                    ratio    = len(translation) / max(1, len(cleaned))
                    tr_score = round(min(1.0, max(0.0, ratio / 5.0)), 3)
                    tr_qa    = score_translation_quality(cleaned, translation)

            # Phase Q: archive any existing translation before overwriting.
            # In default runs the SQL filter guarantees empties, so this is a
            # no-op; with --retranslate it preserves the superseded version.
            if translation:
                _archive_previous_translation(con, cur, rowid)

            # Write to DB (provenance: engine + prompt version + timestamp + QA)
            update_parts = ["translation=?", "mt_prompt_version=?",
                            "translated_at=?", "translation_qa=?"]
            update_vals  = [translation,
                            PROMPT_VERSION if translation else None,
                            datetime.now(timezone.utc).isoformat() if translation else None,
                            tr_qa]
            if has_eng_col and active_engine:
                update_parts.append("engine=?")
                update_vals.append(active_engine)
            if has_tr_score and tr_score is not None:
                update_parts.append("translation_score=?")
                update_vals.append(tr_score)
            update_vals.append(rowid)
            cur.execute(
                f"UPDATE passages SET {', '.join(update_parts)} WHERE rowid=?",
                update_vals,
            )
            iast_val = meta_row.get("iast") or ""
            _update_fts(cur, rowid, cleaned, iast_val, translation or "")
            con.commit()
            ok_count += 1
            if translation:
                consec_fail = 0
            else:
                consec_fail += 1

            # Update recent ring buffer
            recent.append({
                "page":        page_no,
                "idx":         idx,
                "verse_ref":   meta_row.get("verse_ref"),
                "text":        cleaned[:300],
                "translation": translation[:300] if translation else "",
                "quality":     quality,
                "tr_score":    tr_score,
                "tr_qa":       tr_qa,
                "engine":      active_engine or "",
                "skipped":     False,
                "ts":          datetime.now(timezone.utc).isoformat(),
            })
            if len(recent) > RECENT_MAX:
                recent.pop(0)

            ref_str  = f"[{meta_row.get('verse_ref')}] " if meta_row.get("verse_ref") else ""
            ctx_str  = f" ctx={len(context_verses)}" if context_verses else ""
            chan_str = f" [{meta_row.get('chandas')}]" if meta_row.get("chandas") else ""
            qa_str   = f" qa={tr_qa}" if tr_qa is not None else ""
            print(f"  [{i}/{len(todo)}] p{page_no}.{idx} {ref_str}{chan_str}{ctx_str}{qa_str}: "
                  f"{(translation or '[empty]')[:60]!r}")

            _write_progress({
                "status": "running", "doc": args.doc,
                "engine": active_engine or "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "verses_done": ok_count, "verses_total": len(todo),
                "skipped_quality": skip_quality, "errors": err_count,
                "current_page": page_no, "current_idx": idx,
                "current_text": cleaned[:400],
                "current_translation": translation or "",
                "current_quality": quality,
                "current_context_n": len(context_verses),
                "min_quality": active_min_quality,
                "recent": recent,
            })

            if (args.max_consecutive_failures
                    and consec_fail >= args.max_consecutive_failures):
                aborted = (f"{consec_fail} consecutive empty/failed translations "
                           f"— suspected quota exhaustion or unreadable source. "
                           f"Fix the cause, then re-run to resume (translated "
                           f"rows are never re-billed).")
                print(f"\n[ABORT] {aborted}")
                break

            time.sleep(args.sleep)

        except QuotaExhausted as exc:
            err_count += 1
            aborted = f"API quota/rate limit exhausted: {exc}"
            print(f"\n[ABORT] {aborted}")
            break

        except Exception as exc:
            err_count += 1
            consec_fail += 1
            print(f"  [ERR] p{page_no}.{idx}: {exc}")
            _write_progress({
                "status": "running", "doc": args.doc,
                "engine": cfg.get("engine", base_engine or ""),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "verses_done": ok_count, "verses_total": len(todo),
                "skipped_quality": skip_quality, "errors": err_count,
                "current_page": page_no, "current_idx": idx,
                "current_text": cleaned[:200],
                "current_translation": f"[ERROR: {exc}]",
                "current_quality": meta_row.get("quality_score"),
                "min_quality": args.min_quality,
                "recent": recent,
            })
            if (args.max_consecutive_failures
                    and consec_fail >= args.max_consecutive_failures):
                aborted = (f"{consec_fail} consecutive failures — aborting; "
                           f"see errors above.")
                print(f"\n[ABORT] {aborted}")
                break
            time.sleep(args.sleep)

    print(f"\nDone. {ok_count}/{len(todo)} translated | "
          f"{skip_quality} quality-skipped | {err_count} errors")
    _write_progress({
        "status": "aborted" if aborted else "done",
        "abort_reason": aborted,
        "doc": args.doc,
        "engine": base_engine or "",
        "started_at": started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "verses_done": ok_count, "verses_total": len(todo),
        "skipped_quality": skip_quality, "errors": err_count,
        "current_page": None, "current_idx": None,
        "current_text": None, "current_translation": None,
        "current_quality": None,
        "min_quality": args.min_quality,
        "recent": recent,
    })


if __name__ == "__main__":
    main()
