#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_brain_items_2026_10_07.py  (2026-10-07)  BRAIN_ITEMS_2026_10_07

Gives the "sanskritic brain" (Ask, /ask) the project's editorial layer: approved
stories, found episodes and approved images, indexed by scripts/brain_items.py (a
new file beside this patch) with the same embedding model as the passages.

  dashboard.py   /api/ask keeps its passage retrieval exactly as it is. When that
                 retrieval was semantic, the SAME question vector (no extra paid
                 call) also finds up to 3 editorial items (cosine >= 0.55). They go
                 to the model after the passages, labelled EDITORIAL, and the
                 system prompt says they are not scripture. Response: "editorial".
                 With no brain_items table, nothing changes.
  ask.html       a source card links to its story, episode or picture (not the
                 reader) and shows its label.
  maintenance_runner.ps1   step b2 after the passage embeddings: brain_items.py,
                 so stories, episodes and pictures enter the index every run
                 (incremental; about $0.00002 an item).

All-or-nothing, marker-idempotent, backup .bak_brainitems_<date>, py_compile.
  python scripts\\patch_brain_items_2026_10_07.py --check
  python scripts\\patch_brain_items_2026_10_07.py
Test: python -m unittest tests.test_brain_items_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "BRAIN_ITEMS_2026_10_07"

DASH = [
    ("question vector kept",
     '''    if n > 0:
        qv = qv / n
    # ASK_VECTOR_CACHE_2026_10_04: read the matrix once; rebuild only when the index changes.
''',
     '''    if n > 0:
        qv = qv / n
    _ASK_QV[q] = (model, qv)   # BRAIN_ITEMS_2026_10_07: the same vector finds editorial items, no second call
    while len(_ASK_QV) > 64:
        _ASK_QV.pop(next(iter(_ASK_QV)))
    # ASK_VECTOR_CACHE_2026_10_04: read the matrix once; rebuild only when the index changes.
''', 1),
    ("editorial retrieval helper",
     '''_ASK_VEC_CACHE = {}   # ASK_VECTOR_CACHE_2026_10_04: {key, ids, mat}
''',
     '''_ASK_VEC_CACHE = {}   # ASK_VECTOR_CACHE_2026_10_04: {key, ids, mat}
_ASK_QV = {}          # BRAIN_ITEMS_2026_10_07: question -> (model, normalised vector), briefly


def _ask_brain_items(con, q, data):
    """BRAIN_ITEMS_2026_10_07: approved stories, found episodes and approved images close to the
    question, from brain_items (scripts/brain_items.py). [] when there is no such index."""
    got = _ASK_QV.pop(q, None)
    if not got:
        return []
    try:
        import brain_items as _bi
        try:
            k = max(0, min(6, int(data.get("k_editorial", 3))))
        except (TypeError, ValueError):
            k = 3
        return _bi.retrieve(con, got[1], got[0], k=k, include_drafts=True if data.get("drafts") else None)
    except Exception as e:
        print(f"[ask] editorial items skipped: {type(e).__name__}: {e}")
        return []
''', 1),
    ("retrieve editorial items",
     '''    mode = "keyword"
    try:
        rows = _ask_semantic_retrieve(con, q, k)   # meaning-based if embeddings built
        if rows:
            mode = "semantic"
''',
     '''    mode = "keyword"
    extra = []   # BRAIN_ITEMS_2026_10_07
    try:
        rows = _ask_semantic_retrieve(con, q, k)   # meaning-based if embeddings built
        if rows:
            mode = "semantic"
            extra = _ask_brain_items(con, q, data)
''', 1),
    ("editorial items into the context",
     '''    user_msg = "PASSAGES:\\n" + "\\n".join(ctx) + f"\\n\\nQUESTION: {q}\\n\\nAnswer, citing [tags]:"
''',
     '''    for j, it in enumerate(extra, len(sources) + 1):   # BRAIN_ITEMS_2026_10_07
        sources.append({"n": j, "tag": it["tag"], "doc": it["doc"], "verse_ref": None, "page_no": it["page"],
                        "idx": it["idx"], "english": it["text"][:600], "kind": it["kind"], "link": it["link"],
                        "label": it["label"]})
        ctx.append(f"[{j}] [{it['tag']}] ({it['label']}) {it['text'][:700]}")
    user_msg = "PASSAGES:\\n" + "\\n".join(ctx) + f"\\n\\nQUESTION: {q}\\n\\nAnswer, citing [tags]:"
''', 1),
    ("system prompt",
     '''    "not add outside knowledge unless you clearly label it as background context."
''',
     '''    "not add outside knowledge unless you clearly label it as background context."
    # BRAIN_ITEMS_2026_10_07
    " Items labelled EDITORIAL (a retelling, an episode pointer or an illustration) were made from this corpus "
    "by the project; they are not scripture. Ground every claim in the passages, and cite an editorial item only "
    "for what it adds, such as where an episode is told or that a retelling or picture of it exists."
''', 1),
    ("response field",
     '''    return jsonify({"answer": answer, "sources": sources, "engine": engine,
                    "k": k, "mode": mode})
''',
     '''    return jsonify({"answer": answer, "sources": sources, "engine": engine,
                    "k": k, "mode": mode, "editorial": len(extra)})   # BRAIN_ITEMS_2026_10_07
''', 1),
]

ASK = [
    ("source link and label",
     """      html += '<a class="src" id="src-'+s.n+'" href="/reader/'+encodeURIComponent(s.doc)+'" target="_blank">'
            + '<span class="open">open in reader &#8599;</span>'
            + '<span class="num">'+s.n+'</span><span class="tag">['+esc(s.tag)+']</span>'
""",
     """      // BRAIN_ITEMS_2026_10_07: an editorial item opens its story, episode or picture
      html += '<a class="src" id="src-'+s.n+'" href="'+(s.link ? esc(s.link) : '/reader/'+encodeURIComponent(s.doc))+'" target="_blank">'
            + '<span class="open">'+(s.link ? 'open &#8599;' : 'open in reader &#8599;')+'</span>'
            + '<span class="num">'+s.n+'</span><span class="tag">['+esc(s.tag)+']</span>'
            + (s.label ? ' <i style="color:#b18a45">'+esc(s.label)+'</i>' : '')
""", 1),
]

PS1 = [
    ("maintenance step b2",
     '''    Log ("STEP b embeddings   {0:n0}s" -f ((Get-Date) - $tb).TotalSeconds)
''',
     '''    Log ("STEP b embeddings   {0:n0}s" -f ((Get-Date) - $tb).TotalSeconds)

    # b2) BRAIN_ITEMS_2026_10_07: stories, found episodes and drawn images into the Ask index (CHEAP,
    #     incremental: only new or changed items are embedded; retired ones are dropped)
    #     A failure here is logged and skipped; it never stops step c.
    $tb2 = Get-Date
    try {
        & $py scripts\\brain_items.py --db data\\context.db 2>&1 | Add-Content $log
        Log ("STEP b2 brain items {0:n0}s" -f ((Get-Date) - $tb2).TotalSeconds)
    } catch {
        Log ("STEP b2 brain items SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $tb2).TotalSeconds, $_)
    }
''', 1),
]

TARGETS = [(Path("scripts/dashboard.py"), DASH), (Path("scripts/ask.html"), ASK),
           (Path("scripts/maintenance_runner.ps1"), PS1)]
NEW_FILES = [Path("scripts/brain_items.py")]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    missing = [str(p) for p in NEW_FILES if not p.exists()]
    if missing:
        print("FAIL: copy these new files into scripts\\ first: " + ", ".join(missing)); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    marks = [MARK in s for _, s, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand:")
        for (p, _s, _n, _e), m in zip(loaded, marks):
            print("  %-32s %s" % (p, "patched" if m else "not patched"))
        return 1
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    for p in NEW_FILES:
        if p.suffix == ".py":
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                print("REFUSING: %s does not compile:\n%s" % (p, e)); return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files; new files present. Nothing written."
              % (sum(len(e) for _, e in TARGETS), len(TARGETS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_brainitems")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        if p.suffix == ".py":
            try:
                py_compile.compile(str(t), doraise=True)
            except py_compile.PyCompileError as e:
                for x, _ in tmps + [(t, p)]:
                    x.unlink(missing_ok=True)
                print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_brainitems_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Restart the dashboard when no job is running. Then: python scripts\\brain_items.py --db data\\context.db")
    return 0


if __name__ == "__main__":
    sys.exit(main())
