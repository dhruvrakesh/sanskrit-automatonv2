#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_entities.py — the entity / cross-linkage layer (Phase 3, 2026-08-23).

Reads each translated verse and extracts NAMED ENTITIES (persons, deities,
places, rivers, mountains, peoples/dynasties) with a canonical IAST form, using
the SAME Gemini engine + key the translator uses. Stores them in additive tables
so you can ask "every text that references the Nāga king Nīla" across the whole
corpus, and attach footnotes to verses and entities — carrying the genealogical /
geographical correlation tradition into a queryable database.

Additive & non-destructive
--------------------------
* Creates only: entities, entity_variants, entity_mentions, footnotes (+ indexes).
* Also fills the EXISTING but empty passages.ents column with a JSON list of the
  canonical entities in that verse (fast display + a 'done' marker).
* IDEMPOTENT + RESUMABLE: skips verses whose ents is already set (unless
  --refresh); commits every batch, so Ctrl+C then re-run continues. No verse is
  re-billed.
* SAFE UNDER LOAD: a writer with busy_timeout — run when the DB is otherwise idle
  (Google-Drive lock), like any heal/translate job.

Accuracy discipline (matters for scholarship): the prompt extracts only genuine
proper names, gives a canonical IAST spelling, classifies a kind, and is told NOT
to invent entities or split epithets. entity_mentions is a full audit trail, so
you can review and merge — nothing is destructive.

Usage (from the automaton/ root):
  python scripts/extract_entities.py --db data/context.db --limit 200      # taste
  python scripts/extract_entities.py --db data/context.db                  # full / resume
  python scripts/extract_entities.py --db data/context.db --doc MBh01      # one text
  python scripts/extract_entities.py --db data/context.db --refresh        # redo all
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

try:
    from infer_mt import _GEMINI_SAFETY as _SAFETY
except Exception:
    _SAFETY = None

_KINDS = ("person", "deity", "place", "river", "mountain", "people", "other")

_SYSTEM = (
    "You are a philologist indexing a Sanskrit corpus. For each numbered verse "
    "(given as its IAST transliteration and English translation), extract the "
    "NAMED ENTITIES actually referred to: persons, deities, places, rivers, "
    "mountains, and peoples/dynasties. For each entity give: surface (as written "
    "in the verse), canonical (the standard IAST spelling with diacritics, e.g. "
    "Gaṅgā, Yudhiṣṭhira, Naimiṣāraṇya), and kind (one of: person, deity, place, "
    "river, mountain, people, other). Rules: include ONLY genuine proper names; do "
    "NOT include common nouns, abstract concepts, or generic descriptive epithets "
    "unless the epithet is used as the name itself; do NOT invent entities that are "
    "not in the text; merge obvious spelling variants under one canonical form. "
    "Return STRICT JSON only: "
    '{"verses":[{"i":<index int>,"ents":[{"surface":"..","canonical":"..","kind":".."}]}]}'
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_schema(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS entities(
            id INTEGER PRIMARY KEY, canonical TEXT UNIQUE, kind TEXT,
            notes TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS entity_variants(
            entity_id INTEGER, variant TEXT, UNIQUE(entity_id, variant));
        CREATE TABLE IF NOT EXISTS entity_mentions(
            id INTEGER PRIMARY KEY, entity_id INTEGER, passage_id INTEGER,
            surface TEXT, created_at TEXT, UNIQUE(entity_id, passage_id));
        CREATE TABLE IF NOT EXISTS footnotes(
            id INTEGER PRIMARY KEY, passage_id INTEGER, entity_id INTEGER,
            note TEXT, author TEXT, created_at TEXT);
        CREATE INDEX IF NOT EXISTS ix_mentions_entity  ON entity_mentions(entity_id);
        CREATE INDEX IF NOT EXISTS ix_mentions_passage ON entity_mentions(passage_id);
        CREATE INDEX IF NOT EXISTS ix_footnotes_passage ON footnotes(passage_id);
        """
    )
    con.commit()


def _parse_json(text: str):
    """Robustly pull the JSON object out of a model reply (handles ``` fences)."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _as_text(v) -> str:
    """Coerce whatever the model put in a field into a plain string.

    2026-08-29: a run died at verse 1110/1431 with
    "'list' object has no attribute 'strip'" because the model answered
    "canonical": ["Shiva", "Rudra"] instead of a string, and
    `(canonical or "").strip()` happily returned the list. Model output shape
    varies; one odd verse must never be able to kill a 1,400-verse job.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (list, tuple)):
        # take the first non-empty element; the rest become variants elsewhere
        for item in v:
            t = _as_text(item)
            if t:
                return t
        return ""
    if isinstance(v, dict):
        for k in ("canonical", "name", "surface", "value", "text"):
            if k in v:
                return _as_text(v[k])
        return ""
    return str(v).strip()


def _upsert_entity(con, cur, canonical, kind):
    canonical = _as_text(canonical)
    if not canonical:
        return None
    row = con.execute("SELECT id, kind FROM entities WHERE canonical=?", (canonical,)).fetchone()
    if row:
        if (not row[1]) and kind:
            cur.execute("UPDATE entities SET kind=? WHERE id=?", (kind, row[0]))
        return row[0]
    cur.execute("INSERT INTO entities(canonical, kind, created_at) VALUES(?,?,?)",
                (canonical, kind or None, _now()))
    return cur.lastrowid


def _apply_extraction(con, cur, batch, parsed):
    """batch: list of (idx_in_batch, passage_id). parsed: model JSON.
    Writes entities/variants/mentions and fills passages.ents. Returns
    (n_verses_marked, n_mentions, n_verses_with_no_entities). The third value
    exists because a run that prints "+0 mentions" is ambiguous: it can mean the
    model found nothing, or it can mean every mention already existed and the
    INSERT OR IGNORE was a no-op. Those are very different situations and the
    old two-value return could not tell them apart. Pure DB logic —
    unit-testable without the API."""
    by_i = {}
    for v in (parsed or {}).get("verses", []):
        try:
            by_i[int(v.get("i"))] = v.get("ents") or []
        except (TypeError, ValueError):
            continue
    marked = mentions = barren = 0
    for i, pid in batch:
        ents = by_i.get(i, [])
        canon_list = []
        for e in ents:
            if not isinstance(e, dict):
                continue
            canonical = _as_text(e.get("canonical")) or _as_text(e.get("surface"))
            kind = _as_text(e.get("kind")).lower()
            if kind not in _KINDS:
                kind = "other"
            surface = _as_text(e.get("surface")) or canonical
            if not canonical:
                continue
            eid = _upsert_entity(con, cur, canonical, kind)
            if eid is None:
                continue
            cur.execute("INSERT OR IGNORE INTO entity_variants(entity_id, variant) VALUES(?,?)",
                        (eid, surface))
            cur.execute(
                "INSERT OR IGNORE INTO entity_mentions(entity_id, passage_id, surface, created_at) "
                "VALUES(?,?,?,?)", (eid, pid, surface, _now()))
            if cur.rowcount:
                mentions += 1
            if canonical not in canon_list:
                canon_list.append(canonical)
        # Always set ents (even to '[]') so the verse counts as processed/resumable.
        cur.execute("UPDATE passages SET ents=? WHERE id=?",
                    (json.dumps(canon_list, ensure_ascii=False), pid))
        if not canon_list:
            barren += 1          # counted AFTER processing: covers both an empty
                                 # model reply and entries we had to skip as malformed
        marked += 1
    return marked, mentions, barren


def _gemini_extract(genai, model, prompt, max_tokens=8192):
    # 8192 (was 4096): a 10-verse batch rich in names can exceed 4096 output
    # tokens and truncate the JSON mid-object, which then fails to parse and
    # (previously) silently dropped the whole batch. More headroom + the
    # split-on-failure retry below make batches self-healing.
    try:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=max_tokens,
                                     response_mime_type="application/json")
        kwargs = dict(model_name=model, generation_config=cfg, system_instruction=_SYSTEM)
        if _SAFETY is not None:
            kwargs["safety_settings"] = _SAFETY
        gm = genai.GenerativeModel(**kwargs)
    except TypeError:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=max_tokens)
        kwargs = dict(model_name=model, generation_config=cfg, system_instruction=_SYSTEM)
        if _SAFETY is not None:
            kwargs["safety_settings"] = _SAFETY
        gm = genai.GenerativeModel(**kwargs)
    # A stalled gRPC call with no timeout blocks FOREVER, and the retry/backoff
    # around this function never gets control back - an overnight run just stops,
    # silently, with no error. Observed 2026-08-29. 180s is generous for a 10-verse
    # batch; anything slower is a hung socket, not a slow model.
    resp = gm.generate_content(prompt, request_options={"timeout": 180})
    return (getattr(resp, "text", "") or "").strip(), resp


def _extract_chunk(con, cur, genai, model, chunk, engine=None, doc=None, debug_raw=False):
    """Extract one chunk = list of (pid, iast, tr). On a JSON-parse failure,
    recursively SPLIT the chunk and retry each half, so a single problematic
    verse can never sink its neighbours. A lone verse that still won't parse is
    left UNMARKED (ents stays NULL) so a later run retries it — never silently
    dropped. Returns (verses_marked, mentions_added)."""
    lines, batch = [], []
    for i, (pid, iast, tr) in enumerate(chunk):
        batch.append((i, pid))
        _iast, _tr = _as_text(iast), _as_text(tr)
        src = (f"IAST: {_iast}\n" if _iast else "") + f"EN: {_tr[:700]}"
        lines.append(f"[verse {i}]\n{src}")
    prompt = "Verses:\n\n" + "\n\n".join(lines)
    # Transient API errors (504 deadline, 503 unavailable, 429 rate) are common on
    # a long run — retry with exponential backoff instead of stopping the whole job.
    reply, _tries = None, 5
    for attempt in range(_tries):
        try:
            t0 = time.time()
            reply, _resp = _gemini_extract(genai, model, prompt)
            # 2026-08-29: entity extraction used to spend money invisibly - the
            # budget cap never saw a single one of these calls.
            try:
                from usage_meter import meter as _meter
                _meter(kind="entities", doc=doc, engine=engine or f"gemini:{model}",
                       resp=_resp, in_chars=len(prompt), out_chars=len(reply or ""),
                       units=len(chunk), duration_s=time.time() - t0, con=con)
            except Exception:
                pass
            if debug_raw:
                print(f"    [raw {len(reply or '')} chars] {(reply or '')[:400]}", flush=True)
            break
        except Exception as exc:
            msg = str(exc).lower()
            transient = any(s in msg for s in
                            ("504", "503", "429", "deadline", "unavailable", "timeout", "rate limit"))
            if transient and attempt < _tries - 1:
                wait = 2 ** attempt
                print(f"    [retry {attempt+1}/{_tries-1}] {str(exc)[:70]} — waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    parsed = _parse_json(reply)
    if parsed is not None:
        # A reply that parses but carries no "verses" key is NOT a success: every
        # verse in the batch would be marked ents='[]' and never retried. Treat
        # that shape mismatch as a parse failure so the split-retry path runs.
        if not isinstance(parsed, dict) or "verses" not in parsed:
            print(f"    [shape] reply parsed but has no 'verses' key "
                  f"(keys={list(parsed)[:6] if isinstance(parsed, dict) else type(parsed).__name__}) "
                  f"- not marking these {len(chunk)} verses.", flush=True)
        else:
            m, mm, bare = _apply_extraction(con, cur, batch, parsed)
            con.commit()
            return m, mm, bare
    if len(chunk) > 1:                              # split and retry each half
        mid = len(chunk) // 2
        a = _extract_chunk(con, cur, genai, model, chunk[:mid], engine, doc, debug_raw)
        b = _extract_chunk(con, cur, genai, model, chunk[mid:], engine, doc, debug_raw)
        return a[0] + b[0], a[1] + b[1], a[2] + b[2]
    # single verse still unparseable → leave ents NULL (retryable next run)
    print(f"    [skip] passage {chunk[0][0]}: unparseable, left for a later run.")
    return 0, 0, 0


def main():
    ap = argparse.ArgumentParser(description="Extract named entities into the cross-linkage tables")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="limit to one doc code")
    ap.add_argument("--engine", default=os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"))
    ap.add_argument("--batch", type=int, default=10, help="verses per model call")
    ap.add_argument("--limit", type=int, default=None, help="cap verses this run")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--refresh", action="store_true", help="re-extract even verses already done")
    ap.add_argument("--retry-empty", action="store_true",
                    help="also re-process verses whose ents is '[]' (e.g. left empty by an "
                         "earlier JSON-parse failure) — recovers dropped verses")
    ap.add_argument("--debug-raw", action="store_true",
                    help="print the first 400 chars of each raw model reply — use this when a "
                         "run reports '+0 mentions' to see what the model actually returned")
    args = ap.parse_args()

    try:
        import google.generativeai as genai
    except Exception:
        sys.exit("google-generativeai is required (pip install google-generativeai>=0.8).")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    model = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine

    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    _ensure_schema(con)
    if "ents" not in {r[1] for r in con.execute("PRAGMA table_info(passages)")}:
        con.execute("ALTER TABLE passages ADD COLUMN ents TEXT")
        con.commit()

    where = ["TRIM(COALESCE(p.translation,'')) <> ''",
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')",
             "d.code NOT LIKE '%-RETIRED'"]
    params = []
    if args.refresh:
        pass                                         # re-do everything
    elif args.retry_empty:
        where.append("(p.ents IS NULL OR TRIM(p.ents) IN ('', '[]'))")
    else:
        where.append("(p.ents IS NULL OR TRIM(p.ents) = '')")
    if args.doc:
        where.append("d.code = ?"); params.append(args.doc)
    rows = con.execute(
        f"""SELECT p.id, COALESCE(p.iast,''), p.translation
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE {' AND '.join(where)}
            ORDER BY p.id""", params).fetchall()
    if args.limit:
        rows = rows[: args.limit]
    total = len(rows)
    if not total:
        print("Nothing to extract — all verses already processed (use --refresh to redo).")
        con.close()
        return

    print(f"Extracting entities from {total} verses with {model} (batch={args.batch})…")
    cur = con.cursor()
    done = ment_total = barren_total = 0
    for start in range(0, total, args.batch):
        chunk = rows[start : start + args.batch]     # already (pid, iast, tr)
        try:
            m, mm, bare = _extract_chunk(con, cur, genai, model, chunk,
                                         engine=args.engine, doc=args.doc,
                                         debug_raw=args.debug_raw)
        except Exception as exc:
            print(f"  [ERR] batch at {start}: {exc} — stopping; re-run to resume.")
            break
        done += m; ment_total += mm; barren_total += bare
        print(f"  {min(start+len(chunk),total)}/{total} seen · {done} marked · "
              f"+{ment_total} mentions · {barren_total} verses with no entity",
              flush=True)
        time.sleep(args.sleep)

    n_ent = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    n_men = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
    print(f"Done. {done} verses processed this run; corpus now has "
          f"{n_ent} distinct entities / {n_men} mentions.")
    if done and ment_total == 0:
        # Say plainly which of the two causes it was, instead of leaving a bare
        # "+0" that reads like a silent failure.
        if barren_total >= done:
            print("  All verses this run genuinely returned NO entities from the model. "
                  "Re-run one batch with --debug-raw to see the replies before assuming "
                  "the corpus is simply name-free.")
        else:
            print("  Entities were found but every mention already existed "
                  "(UNIQUE(entity_id, passage_id) - nothing new to add). This is a no-op, "
                  "not a failure.")
    try:
        spent = con.execute("SELECT ROUND(SUM(cost_usd),4) FROM usage_log "
                            "WHERE kind='entities'").fetchone()[0]
        print(f"  recorded entity-extraction spend, all time: ${spent or 0}")
    except Exception:
        pass
    con.close()


if __name__ == "__main__":
    main()
