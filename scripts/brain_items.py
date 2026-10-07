#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
brain_items.py  (2026-10-05)  BRAIN_ITEMS_2026_10_05

The "sanskritic brain" (Ask the Corpus, /ask) retrieves PASSAGES by meaning through
passage_embeddings (build_embeddings.py). It knew nothing of the project's own
editorial layer. This adds that layer as a second, small index, beside the first:

  story     a written retelling (scripts/stories.py), draft or approved, with its range
  episode   a mined episode (candidate): title, one-line summary, passage range
  image     a drawn image (draft or approved): title, English caption, context note

Table brain_items (additive, created on first use), one row per item, keyed by
(kind, ref_id). Vectors use the SAME model as passage_embeddings, so one question
vector serves both. Incremental: an item is embedded again only when its text
changes; an item whose source is retired or gone is dropped (this table is an index,
never a source of truth).

Ask uses it (dashboard.py, BRAIN_ITEMS_2026_10_05): after the passages, up to 3 items
with cosine >= SA_BRAIN_MIN_SIM (default 0.55) are given to the model labelled
EDITORIAL, never as scripture. Drafts are retrieved only when SA_BRAIN_DRAFTS=1.

Kept current by scripts/maintenance_runner.ps1 (step b2, every run) and by the
"Update brain" button on /stories. Metered as kind 'embedding' (doc '(brain)') and
budget-gated. Cost: about $0.00002 an item.

  python scripts\\brain_items.py --db data\\context.db --plan     # counts only, no call
  python scripts\\brain_items.py --db data\\context.db            # add / update / drop
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
import time
import warnings
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARK = "BRAIN_ITEMS_2026_10_05"
SCHEMA = """
CREATE TABLE IF NOT EXISTS brain_items(
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref_id INTEGER NOT NULL, doc_code TEXT, status TEXT,
  title TEXT, text TEXT, link TEXT, page INTEGER, idx INTEGER, text_hash TEXT,
  model TEXT, dim INTEGER, vec BLOB, updated_at TEXT, UNIQUE(kind, ref_id));
"""
MIN_SIM = float(os.environ.get("SA_BRAIN_MIN_SIM", "0.55"))
DRAFTS = os.environ.get("SA_BRAIN_DRAFTS", "") == "1"
LABEL = {"story": "EDITORIAL retelling", "episode": "EDITORIAL episode pointer", "image": "EDITORIAL illustration"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tables(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def ensure_schema(con) -> None:
    con.executescript(SCHEMA)
    con.commit()


def _ref(p, i) -> str:
    return "%s.%s" % (p, i)


def model_of(con) -> str | None:
    """The passage index's model: the question vector made for passages is reused here."""
    if "passage_embeddings" not in _tables(con):
        return None
    r = con.execute("SELECT model FROM passage_embeddings GROUP BY model ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    return r[0] if r else None


def collect(con) -> list:
    """Every item the brain should hold now, from doc_stories and doc_images."""
    t = _tables(con)
    out = []
    if "doc_stories" in t:
        for sid, code, st, title, why, story, fp, fi, tp, ti in con.execute(
                """SELECT s.id, d.code, s.status, COALESCE(s.title,''), COALESCE(s.why,''), COALESCE(s.story_en,''),
                          s.from_page, s.from_idx, s.to_page, s.to_idx
                   FROM doc_stories s JOIN docs d ON d.id = s.doc_id
                   WHERE s.status IN ('candidate','draft','approved') AND d.code NOT LIKE '%-RETIRED'"""):
            rng = "%s-%s" % (_ref(fp, fi), _ref(tp, ti))
            link = "/stories?doc=%s#s%d" % (code, sid)
            if st in ("draft", "approved") and story.strip():
                out.append({"kind": "story", "ref_id": sid, "doc": code, "status": st, "title": title,
                            "text": "%s. Retelling of %s, passages %s. %s" % (title, code, rng, story.strip()),
                            "link": link, "page": fp, "idx": fi, "range": rng})
            elif st == "candidate" and title.strip():
                out.append({"kind": "episode", "ref_id": sid, "doc": code, "status": st, "title": title,
                            "text": "%s. Episode in %s, passages %s. %s" % (title, code, rng, why.strip()),
                            "link": link, "page": fp, "idx": fi, "range": rng})
    if "doc_images" in t:
        for iid, code, st, kind, title, cap, note, pg, ix in con.execute(
                """SELECT i.id, d.code, i.status, i.kind, COALESCE(i.title,''), COALESCE(i.caption_en,''),
                          COALESCE(i.context_note,''), i.anchor_page, i.anchor_idx
                   FROM doc_images i JOIN docs d ON d.id = i.doc_id
                   WHERE i.status IN ('draft','approved') AND i.path IS NOT NULL
                     AND d.code NOT LIKE '%-RETIRED'"""):
            text = " ".join(x for x in (title.strip(), cap.strip(), note.strip()) if x)
            if not text:
                continue
            where = "cover" if kind == "cover" else "at passage %s" % _ref(pg, ix)
            out.append({"kind": "image", "ref_id": iid, "doc": code, "status": st, "title": title,
                        "text": "Illustration (%s) in %s, %s: %s" % (kind, code, where, text),
                        "link": "/api/images/file/%d" % iid, "page": pg, "idx": ix, "range": _ref(pg, ix)})
    for it in out:
        it["hash"] = hashlib.sha256(it["text"].encode("utf-8")).hexdigest()[:20]
    return out


def plan(con, model: str | None = None) -> dict:
    """{'model', 'items', 'indexed', 'add', 'update', 'drop'} - no API call, no write."""
    model = model or model_of(con)
    items = collect(con)
    have = {}
    if "brain_items" in _tables(con):
        have = {(k, r): (h, m) for k, r, h, m in con.execute("SELECT kind, ref_id, text_hash, model FROM brain_items")}
    want = {(i["kind"], i["ref_id"]): i for i in items}
    add = [i for k, i in want.items() if k not in have]
    upd = [i for k, i in want.items() if k in have and (have[k][0] != i["hash"] or have[k][1] != model)]
    drop = [k for k in have if k not in want]
    return {"model": model, "items": len(items), "indexed": len(have), "add": len(add), "update": len(upd),
            "drop": len(drop), "_todo": add + upd, "_drop": drop, "_want": want}


def _genai_embedder(model: str):
    warnings.filterwarnings("ignore")   # a warning on stderr fails the PowerShell runner (ErrorAction Stop)
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)

    def embed(texts):
        res = genai.embed_content(model=model, content=texts, task_type="retrieval_document")
        emb = res["embedding"] if isinstance(res, dict) else res.embedding
        if emb and not isinstance(emb[0], (list, tuple)):
            emb = [emb]
        if len(emb) != len(texts):
            emb = []
            for t in texts:
                r = genai.embed_content(model=model, content=t, task_type="retrieval_document")
                emb.append(r["embedding"] if isinstance(r, dict) else r.embedding)
        return emb
    return embed


def sync(con, db: str, embed=None, model: str | None = None, batch: int = 32, limit: int | None = None) -> dict:
    """Drop gone items, embed new and changed ones. Returns the plan with 'embedded'."""
    import numpy as np
    ensure_schema(con)
    p = plan(con, model)
    model = p["model"]
    for k, r in p["_drop"]:
        con.execute("DELETE FROM brain_items WHERE kind=? AND ref_id=?", (k, r))
    # a status change alone (draft -> approved) keeps the text: refresh it without re-embedding
    for (k, r), it in p["_want"].items():
        con.execute("UPDATE brain_items SET status=?, link=? WHERE kind=? AND ref_id=? AND status IS NOT ?",
                    (it["status"], it["link"], k, r, it["status"]))
    con.commit()
    todo = p["_todo"][:limit] if limit else p["_todo"]
    p["embedded"] = 0
    if not todo:
        return p
    if not model:
        raise SystemExit("No passage index yet (passage_embeddings is empty): run build_embeddings.py first, "
                         "so stories and passages share one model.")
    try:
        from usage_meter import budget_ok, meter
    except ImportError:
        budget_ok, meter = (lambda _db: True), None
    if not budget_ok(db):
        print("Refusing: the spend cap is reached (budget_state). Nothing embedded.")
        return p
    embed = embed or _genai_embedder(model)
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        texts = [it["text"][:2000] for it in chunk]
        t0 = time.time()
        vecs = embed(texts)
        if meter:
            try:
                meter(kind="embedding", doc="(brain)", engine=model, in_chars=sum(len(t) for t in texts),
                      out_chars=0, units=len(chunk), duration_s=time.time() - t0, con=con)
            except Exception:
                pass
        for it, v in zip(chunk, vecs):
            a = np.asarray(v, dtype="float32")
            n = float(np.linalg.norm(a))
            if n > 0:
                a = a / n
            con.execute(
                """INSERT INTO brain_items(kind, ref_id, doc_code, status, title, text, link, page, idx, text_hash,
                                           model, dim, vec, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(kind, ref_id) DO UPDATE SET doc_code=excluded.doc_code, status=excluded.status,
                     title=excluded.title, text=excluded.text, link=excluded.link, page=excluded.page,
                     idx=excluded.idx, text_hash=excluded.text_hash, model=excluded.model, dim=excluded.dim,
                     vec=excluded.vec, updated_at=excluded.updated_at""",
                (it["kind"], it["ref_id"], it["doc"], it["status"], it["title"], it["text"], it["link"], it["page"],
                 it["idx"], it["hash"], model, int(a.shape[0]), a.tobytes(), _now()))
        con.commit()
        p["embedded"] += len(chunk)
    return p


def retrieve(con, qv, model: str, k: int = 3, include_drafts: bool | None = None, min_sim: float | None = None) -> list:
    """Items closest to the (L2-normalised) question vector qv. Read-only; [] when there is no index."""
    import numpy as np
    if "brain_items" not in _tables(con):
        return []
    drafts = DRAFTS if include_drafts is None else include_drafts
    floor = MIN_SIM if min_sim is None else min_sim
    q = np.asarray(qv, dtype="float32")
    got = []
    for kind, rid, code, st, title, text, link, pg, ix, blob in con.execute(
            "SELECT kind, ref_id, doc_code, status, title, text, link, page, idx, vec FROM brain_items "
            "WHERE model=? AND vec IS NOT NULL", (model,)):
        if kind in ("story", "image") and st != "approved" and not drafts:
            continue
        v = np.frombuffer(blob, dtype="float32")
        if v.shape != q.shape:
            continue
        s = float(v @ q)
        if s >= floor:
            got.append((s, kind, rid, code, st, title, text, link, pg, ix))
    got.sort(key=lambda x: -x[0])
    out = []
    for s, kind, rid, code, st, title, text, link, pg, ix in got[:k]:
        tag = "%s #%d %s" % (kind, rid, code)
        out.append({"tag": tag, "kind": kind, "id": rid, "doc": code, "status": st, "title": title, "text": text,
                    "link": link, "page": pg, "idx": ix, "sim": round(s, 4),
                    "label": LABEL.get(kind, "EDITORIAL") + ("" if st == "approved" or kind == "episode"
                                                              else ", unreviewed draft")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Stories, episodes and image captions in the Ask index")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--plan", action="store_true", help="counts only; no API call, no write")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=32)
    args = ap.parse_args()
    if not os.path.isfile(args.db):
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    con = sqlite3.connect(args.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    try:
        if args.plan:
            p = plan(con)
            print("PLAN brain items (%s): %d item(s), %d indexed; %d to add, %d to update, %d to drop. No call made."
                  % (p["model"] or "no passage index yet", p["items"], p["indexed"], p["add"], p["update"], p["drop"]))
            return 0
        try:
            p = sync(con, args.db, model=None, batch=args.batch, limit=args.limit)
        except SystemExit as e:
            print("brain items: %s" % e); return 1
        except Exception as e:   # stdout, not stderr: the maintenance runner treats stderr as a failure
            print("brain items: FAILED %s: %s" % (type(e).__name__, e)); return 1
        n = con.execute("SELECT COUNT(*) FROM brain_items").fetchone()[0]
        print("brain items (%s): %d embedded, %d dropped; %d in the index. %s"
              % (p["model"] or "-", p["embedded"], p["drop"], n, MARK))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
