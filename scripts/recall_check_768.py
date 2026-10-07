#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
recall_check_768.py  (2026-10-07)  RECALL_768_2026_10_07

The cloud plan (docs/CLOUD_BRAIN_2026-10-07.md, C2 gate) stores 768-dimension vectors
(halfvec(768), HNSW) instead of the local 3,072. gemini-embedding-001 is trained so that its
leading dimensions work on their own (Matryoshka). This measures what is lost, for free and
without any API call: for a fixed sample of passages it compares the nearest neighbours found
with the full local vectors against those found with the first 768 dimensions, renormalised.

  recall@k = share of the full-vector top k that the 768-dimension search also returns.

Read-only: the database is opened with mode=ro (and immutable=1 with --immutable, for a
backup copy). Writes nothing. Needs numpy.

  python scripts\\recall_check_768.py --db "D:\\backups\\context_pre_vnames_<stamp>.db" --immutable
  python scripts\\recall_check_768.py --db data\\context.db --sample 200 --k 12
Test: python -m unittest tests.test_recall_check_768 -v
"""
from __future__ import annotations
import argparse, sqlite3, sys, time
from pathlib import Path

MARK = "RECALL_768_2026_10_07"


def open_ro(db: str, immutable: bool = False) -> sqlite3.Connection:
    uri = Path(db).resolve().as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro")
    con = sqlite3.connect(uri, uri=True)
    con.execute("PRAGMA query_only=1")
    return con


def load(con, model: str | None = None, text_only: bool = True):
    """(ids, matrix float32 [n, d]) for every stored vector of the most common dimension."""
    import numpy as np
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    where, args = [], []
    if model:
        where.append("e.model = ?"); args.append(model)
    join = ""
    if text_only and "text_type" in cols:
        join = "JOIN passages p ON p.id = e.passage_id"
        where.append("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
    dim = con.execute("SELECT dim, COUNT(*) FROM passage_embeddings GROUP BY dim ORDER BY 2 DESC LIMIT 1").fetchone()
    if not dim:
        raise SystemExit("no rows in passage_embeddings")
    where.append("e.dim = ?"); args.append(dim[0])
    sql = "SELECT e.passage_id, e.vec FROM passage_embeddings e %s WHERE %s ORDER BY e.passage_id" % (
        join, " AND ".join(where))
    ids, vecs = [], []
    for pid, blob in con.execute(sql, args):
        a = np.frombuffer(blob, dtype=np.float32)
        if a.shape[0] != dim[0]:
            continue
        ids.append(pid); vecs.append(a)
    return ids, np.vstack(vecs) if vecs else np.zeros((0, dim[0]), dtype=np.float32)


def unit(m):
    import numpy as np
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


def recall(full, dims: int = 768, sample: int = 200, ks=(5, 12), seed: int = 7) -> dict:
    """Mean recall@k of the truncated (first `dims`, renormalised) search against the full one."""
    import numpy as np
    full = unit(full.astype(np.float32))
    short = unit(full[:, :dims].copy())
    n = full.shape[0]
    rng = np.random.default_rng(seed)
    q = rng.choice(n, size=min(sample, n), replace=False)
    kmax = max(ks)
    sf = full[q] @ full.T
    ss = short[q] @ short.T
    for j, i in enumerate(q):          # a passage is not its own neighbour
        sf[j, i] = -np.inf; ss[j, i] = -np.inf
    tf = np.argsort(-sf, axis=1)[:, :kmax]
    ts = np.argsort(-ss, axis=1)[:, :kmax]
    out = {"vectors": int(n), "dims_full": int(full.shape[1]), "dims_short": int(dims), "queries": int(len(q))}
    for k in ks:
        hits = [len(set(tf[j, :k]) & set(ts[j, :k])) / k for j in range(len(q))]
        out["recall@%d" % k] = float(np.mean(hits))
        out["worst@%d" % k] = float(np.min(hits))
    top1 = [int(np.where(ts[j] == tf[j, 0])[0][0]) + 1 if tf[j, 0] in ts[j] else None for j in range(len(q))]
    out["full_top1_in_short_top%d" % kmax] = sum(1 for r in top1 if r is not None) / len(q)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Recall of 768-dimension search against the full local vectors")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--immutable", action="store_true", help="for a backup copy only")
    ap.add_argument("--dims", type=int, default=768)
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default=None)
    ap.add_argument("--all-rows", action="store_true", help="include noise / frontmatter rows")
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found." % args.db); return 2
    t0 = time.time()
    con = open_ro(args.db, args.immutable)
    try:
        ids, m = load(con, args.model, not args.all_rows)
    finally:
        con.close()
    if m.shape[0] < args.k + 2:
        print("FAIL: only %d vectors." % m.shape[0]); return 2
    if args.dims >= m.shape[1]:
        print("FAIL: --dims %d is not shorter than the stored %d." % (args.dims, m.shape[1])); return 2
    r = recall(m, args.dims, args.sample, (5, args.k), args.seed)
    print("%s  %d vectors of %d dimensions; %d sample passages (seed %d); %.1fs"
          % (MARK, r["vectors"], r["dims_full"], r["queries"], args.seed, time.time() - t0))
    for k in (5, args.k):
        print("  recall@%-3d %.3f   (worst single passage %.3f)" % (k, r["recall@%d" % k], r["worst@%d" % k]))
    print("  the full search's nearest passage is in the %d-dim top %d for %.1f%% of the sample"
          % (args.dims, args.k, 100 * r["full_top1_in_short_top%d" % args.k]))
    print("  reading: 0.90 or more at k=%d means 768 dimensions keep the neighbourhoods; below 0.80, "
          "store more dimensions or re-embed." % args.k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
