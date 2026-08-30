#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_embeddings.py — semantic-search index for the corpus (Phase 2, 2026-08-23).

Computes a dense vector for every translated passage using a Gemini embedding
model (reuses the SAME GEMINI_API_KEY the translation engine already uses — no
torch, no local models) and stores it in a new, additive `passage_embeddings`
table. The Ask-the-Corpus endpoint uses these vectors for meaning-based
retrieval, and falls back to keyword (FTS) search wherever they are absent, so
building this is purely additive — it never breaks anything.

Design guarantees
-----------------
* ADDITIVE: creates only `passage_embeddings`; touches no existing table/row.
* IDEMPOTENT + RESUMABLE: only embeds passages that lack an up-to-date vector
  (same model). Re-run any time; interrupt with Ctrl+C and re-run to continue —
  every row is committed as it is embedded, so nothing is re-billed.
* SAFE UNDER LOAD: read/writes its own table with a busy_timeout; run it when
  the DB is otherwise idle to avoid the Google-Drive lock, like any writer.

Vectors are L2-normalised at store time, so cosine similarity is a plain dot
product at query time. Stored as float32 BLOBs.

Usage (from the automaton/ root):
  python scripts/build_embeddings.py --db data/context.db                 # build/continue
  python scripts/build_embeddings.py --db data/context.db --limit 500     # a first taste
  python scripts/build_embeddings.py --db data/context.db --refresh       # rebuild all
  python scripts/build_embeddings.py --db data/context.db --model models/text-embedding-004
"""
from __future__ import annotations
import argparse
import sqlite3
import sys
import time
from datetime import datetime, timezone

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS passage_embeddings(
               passage_id INTEGER PRIMARY KEY,
               model      TEXT,
               dim        INTEGER,
               vec        BLOB,
               updated_at TEXT
           )"""
    )
    con.commit()


def _normalise(vec):
    import numpy as np
    a = np.asarray(vec, dtype="float32")
    n = float(np.linalg.norm(a))
    if n > 0:
        a = a / n
    return a


def _embed_batch(genai, model, texts, task_type):
    """Return a list of float lists for `texts`. Tries a single batched call,
    falls back to per-item if the installed client rejects a list."""
    try:
        res = genai.embed_content(model=model, content=texts, task_type=task_type)
        emb = res["embedding"] if isinstance(res, dict) else res.embedding
        # batched call returns a list-of-lists; a single string returns one list
        if emb and not isinstance(emb[0], (list, tuple)):
            emb = [emb]
        if len(emb) == len(texts):
            return emb
    except Exception:
        pass
    out = []
    for t in texts:
        res = genai.embed_content(model=model, content=t, task_type=task_type)
        out.append(res["embedding"] if isinstance(res, dict) else res.embedding)
    return out


def main():
    ap = argparse.ArgumentParser(description="Build semantic-search embeddings for the corpus")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--model", default="auto",
                    help="Gemini embedding model, or 'auto' (default) to discover a "
                         "working one from your account via ListModels")
    ap.add_argument("--list-models", action="store_true",
                    help="print the embedding models your key supports, then exit")
    ap.add_argument("--batch", type=int, default=64, help="passages per embed call")
    ap.add_argument("--limit", type=int, default=None, help="cap total passages this run")
    ap.add_argument("--sleep", type=float, default=0.4, help="pause between batches (rate limit)")
    ap.add_argument("--doc", default=None, help="limit to one doc code (also labels the spend)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-embed everything, even passages already embedded with this model")
    args = ap.parse_args()

    try:
        import numpy as np  # noqa: F401
    except Exception:
        sys.exit("numpy is required (pip install numpy).")
    try:
        import google.generativeai as genai
    except Exception:
        sys.exit("google-generativeai is required (pip install google-generativeai>=0.8).")

    import os
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)

    # Discover which embedding models THIS key actually supports — names differ by
    # API version (e.g. text-embedding-004 may 404 while embedding-001 works).
    def _embed_models():
        names = []
        try:
            for m in genai.list_models():
                methods = getattr(m, "supported_generation_methods", []) or []
                if "embedContent" in methods:
                    names.append(m.name)
        except Exception as e:
            print(f"(could not list models: {e})")
        return names

    available = _embed_models()
    if args.list_models:
        print("Embedding models your key supports:")
        for n in available:
            print("  ", n)
        if not available:
            print("  (none returned — check the key / API access)")
        return

    def _resolve(requested):
        if requested and requested != "auto":
            # accept with or without the 'models/' prefix
            cands = {requested, f"models/{requested}", requested.replace("models/", "")}
            for a in available:
                if a in cands or a.replace("models/", "") in cands:
                    return a
            if not available:            # can't verify — trust the user's choice
                return requested
            print(f"Requested model '{requested}' not in your account; auto-selecting.")
        # preference order among what's actually available
        pref = ("text-embedding-004", "gemini-embedding-001", "text-embedding-005",
                "embedding-001")
        for p in pref:
            for a in available:
                if p in a:
                    return a
        return available[0] if available else None

    model = _resolve(args.model)
    if not model:
        sys.exit("No embedding model available for this key. Run with --list-models "
                 "to see what your key supports, then pass --model <name>.")
    args.model = model
    print(f"Using embedding model: {model}")

    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    _ensure_table(con)

    # Passages worth embedding: have a real English translation, not noise.
    # Embed the English (retrieval target) prefixed with the IAST so proper
    # nouns anchor — keeps names searchable even when the English paraphrases.
    where_done = "" if args.refresh else (
        "AND NOT EXISTS (SELECT 1 FROM passage_embeddings e "
        "WHERE e.passage_id = p.id AND e.model = ?)"
    )
    params = [] if args.refresh else [args.model]
    where_doc = ""
    if args.doc:
        where_doc = "AND d.code = ?"
        params.append(args.doc)          # bound AFTER the model param above
    rows = con.execute(
        f"""SELECT p.id, COALESCE(p.iast,''), p.translation
            FROM passages p
            JOIN docs d ON d.id = p.doc_id
            WHERE TRIM(COALESCE(p.translation,'')) <> ''
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
              AND d.code NOT LIKE '%-RETIRED'
              {where_done}
              {where_doc}
            ORDER BY p.id""",
        params,
    ).fetchall()

    if args.limit:
        rows = rows[: args.limit]
    total = len(rows)
    if not total:
        print("Nothing to embed — all up to date for model", args.model)
        con.close()
        return

    print(f"Embedding {total} passages with {args.model} (batch={args.batch})…")
    cur = con.cursor()
    done = 0
    spend_usd = 0.0
    t0 = time.time()
    for i in range(0, total, args.batch):
        chunk = rows[i : i + args.batch]
        texts = []
        for _pid, iast, tr in chunk:
            t = (tr or "").strip()
            if iast:
                t = f"{iast.strip()} — {t}"
            texts.append(t[:2000])
        t_batch = time.time()
        try:
            embs = _embed_batch(genai, args.model, texts, "retrieval_document")
        except Exception as exc:
            print(f"  [ERR] batch at {i}: {exc}  — stopping; re-run to resume.")
            break
        # 2026-08-29: embeddings were billed but never recorded, so the budget
        # cap was blind to them. embed_content returns no usage_metadata, so
        # this is the chars/4 estimate and is logged as token_source='estimated'.
        try:
            from usage_meter import meter as _meter
            spend_usd += _meter(kind="embedding", doc=args.doc, engine=args.model,
                                in_chars=sum(len(t) for t in texts), out_chars=0,
                                units=len(chunk), duration_s=time.time() - t_batch,
                                con=con)
        except Exception:
            pass
        for (pid, _iast, _tr), vec in zip(chunk, embs):
            a = _normalise(vec)
            cur.execute(
                "INSERT INTO passage_embeddings(passage_id, model, dim, vec, updated_at) "
                "VALUES(?,?,?,?,?) ON CONFLICT(passage_id) DO UPDATE SET "
                "model=excluded.model, dim=excluded.dim, vec=excluded.vec, "
                "updated_at=excluded.updated_at",
                (pid, args.model, int(a.shape[0]), a.tobytes(), _now()),
            )
        con.commit()
        done += len(chunk)
        rate = done / max(1e-6, time.time() - t0)
        print(f"  {done}/{total}  ({100*done//total}%)  ~{rate:.0f}/s", flush=True)
        time.sleep(args.sleep)

    have = con.execute("SELECT COUNT(*) FROM passage_embeddings WHERE model=?",
                       (args.model,)).fetchone()[0]
    con.close()
    print(f"Done. {done} embedded this run; {have} total vectors for {args.model}.")
    print(f"Recorded spend this run: ${spend_usd:.4f} (estimated from characters; the "
          f"embedding API does not report token counts) - kind='embedding' in usage_log.")


if __name__ == "__main__":
    main()
