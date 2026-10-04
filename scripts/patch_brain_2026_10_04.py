#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_brain_2026_10_04.py  (2026-10-04)  BRAIN_FRESH_2026_10_04 + ASK_VECTOR_CACHE_2026_10_04

What the code said on 2026-10-04 (read, not assumed):
  * build_embeddings.py embeds a passage only when it has NO vector for the model.
    A passage whose English was re-translated after its vector was made (--only-lacuna,
    --retranslate, a re-ingest that kept the row) keeps the OLD vector for ever, so
    "Ask the Corpus" retrieves by a meaning the text no longer has.
  * Nothing runs build_embeddings on its own. It runs when someone presses Embed in the
    dashboard (/api/embeddings) or runs the CLI. The semantic index therefore lags the
    corpus by however long ago that was.
  * /api/ask reads EVERY vector BLOB from SQLite on EVERY question
    (dashboard._ask_semantic_retrieve), then stacks them. Fine at 10^4 vectors; it is
    the slowest part of a question as the index grows.

This patch:
  scripts/build_embeddings.py  BRAIN_FRESH_2026_10_04: also re-embeds passages whose
      translated_at is newer than their vector's updated_at ("stale"), by default.
      --no-stale restores the old selection. --plan prints the counts (missing / stale)
      and exits without a call. A re-embed overwrites the row (ON CONFLICT), as before.
  scripts/dashboard.py  ASK_VECTOR_CACHE_2026_10_04: the vector matrix is built once and
      reused until the index changes (its row count or newest updated_at for the model).
      Needs one dashboard restart while idle.

scripts/brain_sync.py (new, separate file) runs the whole refresh in order and is safe to
schedule; see its header.

  python scripts/patch_brain_2026_10_04.py --check
  python scripts/patch_brain_2026_10_04.py
Test: python -m unittest tests.test_brain_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK_E = "BRAIN_FRESH_2026_10_04"
MARK_D = "ASK_VECTOR_CACHE_2026_10_04"
EMB = Path("scripts/build_embeddings.py")
DASH = Path("scripts/dashboard.py")

EMB_EDITS = [
    ("args",
     '    ap.add_argument("--refresh", action="store_true",\n',
     '    ap.add_argument("--no-stale", action="store_true",\n'
     '                    help="BRAIN_FRESH_2026_10_04: do NOT re-embed passages re-translated after their vector")\n'
     '    ap.add_argument("--plan", action="store_true",\n'
     '                    help="BRAIN_FRESH_2026_10_04: print missing/stale counts and exit (no API call)")\n'
     '    ap.add_argument("--refresh", action="store_true",\n', 1),
    ("selection",
     '    where_done = "" if args.refresh else (\n'
     '        "AND NOT EXISTS (SELECT 1 FROM passage_embeddings e "\n'
     '        "WHERE e.passage_id = p.id AND e.model = ?)"\n'
     '    )\n',
     '    # BRAIN_FRESH_2026_10_04: a vector made before the passage was (re)translated is stale.\n'
     '    where_done = "" if args.refresh else (\n'
     '        "AND NOT EXISTS (SELECT 1 FROM passage_embeddings e "\n'
     '        "WHERE e.passage_id = p.id AND e.model = ?"\n'
     '        + ("" if args.no_stale else\n'
     '           " AND NOT (p.translated_at IS NOT NULL AND e.updated_at IS NOT NULL"\n'
     '           " AND julianday(p.translated_at) > julianday(e.updated_at))")\n'
     '        + ")"\n'
     '    )\n', 1),
    ("plan",
     '    if args.limit:\n        rows = rows[: args.limit]\n',
     '    if args.plan:   # BRAIN_FRESH_2026_10_04\n'
     '        have = {r[0] for r in con.execute("SELECT passage_id FROM passage_embeddings WHERE model=?", (args.model,))}\n'
     '        stale = sum(1 for r in rows if r[0] in have)\n'
     '        print("PLAN %s: %d to embed (%d missing, %d stale: re-translated after their vector). No call made."\n'
     '              % (args.model, len(rows), len(rows) - stale, stale))\n'
     '        con.close()\n'
     '        return\n'
     '    if args.limit:\n        rows = rows[: args.limit]\n', 1),
]

DASH_OLD = '''    ids, mats = [], []
    for pid, blob in con.execute(
            "SELECT passage_id, vec FROM passage_embeddings WHERE model=?", (model,)):
        v = np.frombuffer(blob, dtype="float32")
        if dim and v.shape[0] != dim:
            continue
        ids.append(pid); mats.append(v)
    if not ids:
        return None
    sims = np.vstack(mats) @ qv          # both L2-normalised \u2192 dot == cosine
'''
DASH_NEW = '''    # ASK_VECTOR_CACHE_2026_10_04: read the matrix once; rebuild only when the index changes.
    _sig = con.execute("SELECT COUNT(*), MAX(updated_at) FROM passage_embeddings WHERE model=?",
                       (model,)).fetchone()
    _key = (model, dim, _sig[0], _sig[1])
    if _ASK_VEC_CACHE.get("key") != _key:
        ids, mats = [], []
        for pid, blob in con.execute(
                "SELECT passage_id, vec FROM passage_embeddings WHERE model=?", (model,)):
            v = np.frombuffer(blob, dtype="float32")
            if dim and v.shape[0] != dim:
                continue
            ids.append(pid); mats.append(v)
        if not ids:
            return None
        _ASK_VEC_CACHE.clear()
        _ASK_VEC_CACHE.update(key=_key, ids=ids, mat=np.vstack(mats))
    ids = _ASK_VEC_CACHE["ids"]
    sims = _ASK_VEC_CACHE["mat"] @ qv    # both L2-normalised \u2192 dot == cosine
'''
DASH_EDITS = [
    ("cache dict", "def _ask_semantic_retrieve(con, q, k=12):\n",
     "_ASK_VEC_CACHE = {}   # ASK_VECTOR_CACHE_2026_10_04: {key, ids, mat}\n\n\ndef _ask_semantic_retrieve(con, q, k=12):\n", 1),
    ("cached matrix", DASH_OLD, DASH_NEW, 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def apply(src, edits):
    probs = []
    for label, old, new, n in edits:
        c = src.count(old)
        if c != n:
            probs.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    return src, probs


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (EMB, DASH):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    e_src, e_nl = load(EMB); d_src, d_nl = load(DASH)
    have = (MARK_E in e_src, MARK_D in d_src)
    if all(have):
        print("Already patched. Nothing to do."); return 0
    if any(have):
        print("REFUSING: marker in one file only - inspect by hand."); return 1
    e_new, p1 = apply(e_src, EMB_EDITS)
    d_new, p2 = apply(d_src, DASH_EDITS)
    if p1 or p2:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in p1 + p2]; return 1
    if args.check:
        print("CHECK OK: %d + %d anchored edits. Nothing written." % (len(EMB_EDITS), len(DASH_EDITS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in ((EMB, e_new, e_nl), (DASH, d_new, d_nl)):
        t = p.with_name(p.name + ".tmp_brain")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_brain_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("build_embeddings: effective at its next run. dashboard: at the next restart while idle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
