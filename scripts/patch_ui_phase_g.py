#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ui_phase_g.py - Phase G: operable semantic layer + resizable, sortable UI.
(2026-09-06)

WHY
---
1. "Why can't we update embeddings etc via frontend?" Because nobody built it.
   dashboard.py contains ZERO occurrences of build_embeddings or extract_entities.
   /api/ask (RAG query) exists, so the corpus can be QUERIED from the UI but the
   index behind it can only be refreshed from a terminal. That is the gap.

2. The three panes are fixed at `320px 1fr 340px`, so nothing resizes.

3. The pipeline table has a text filter but no sorting, and /api/status returns
   no dates at all - so "arrange by date uploaded / started" needs new FIELDS,
   not just new UI.

WHAT THIS CHANGES  (all additive; nothing existing is removed)
  dashboard.py
    - 'embeddings' and 'entities' join the TRANSLATE semaphore family. They
      write to the DB, so they must serialize with translators exactly as
      classify/qa_scan already do. Getting this wrong is a concurrent-writer bug.
    - POST /api/embeddings  and  POST /api/entities   (per-doc or whole corpus)
    - /api/status gains first_seen, last_ocr, last_activity (epoch seconds)
  dashboard_static.html
    - draggable splitters on both side panes, widths persisted in localStorage
    - sortable column headers, including the new date columns
    - per-doc "Embed" and "Entities" buttons

SAFETY
  Backs up both files first. Every edit is anchored and asserted unique; if any
  anchor is missing NOTHING is written and the backups are left in place. Run
  --verify afterwards to confirm. Idempotent: re-running detects the marker and
  exits without touching anything.

  python scripts\\patch_ui_phase_g.py            # dry run, checks every anchor
  python scripts\\patch_ui_phase_g.py --apply
  python scripts\\patch_ui_phase_g.py --verify
"""
from __future__ import annotations
import argparse, io, os, py_compile, re, shutil, sys, time

MARKER = "PHASE_G_2026_09_06"
PY = os.path.join("scripts", "dashboard.py")
HTML = os.path.join("scripts", "dashboard_static.html")


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- dashboard.py
PY_EDITS = [
    # 1. embeddings/entities are DB writers -> translate semaphore family
    ('''    if (kind.startswith("translate")
            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal", "classify")):''',
     '''    # embeddings and entities WRITE to the DB (passage_embeddings, entity_*),
    # so they serialize with the translators exactly as classify/qa_scan do.
    # Leaving them out would reintroduce concurrent writers. (PHASE_G_2026_09_06)
    if (kind.startswith("translate")
            or kind in ("advance_pipeline", "pipeline", "qa_scan", "qa_heal", "classify",
                        "embeddings", "entities")):'''),

    # 2. the two missing endpoints, added next to /api/classify
    ('''@app.post("/api/translate")''',
     '''@app.post("/api/embeddings")
def api_embeddings():
    """Rebuild the semantic index from the UI. (PHASE_G_2026_09_06)

    This did not exist: the corpus could be QUERIED through /api/ask but its
    index could only be refreshed from a terminal, so the 'sanskritic brain'
    silently went stale after every ingest.
    """
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    doc  = data.get("doc")
    argv = [script("build_embeddings.py"), "--db", db]
    if doc:
        doc = _validate_doc(doc)
        if not doc:
            return jsonify({"error": "invalid doc"}), 400
        argv += ["--doc", doc]
    if data.get("refresh"):
        argv.append("--refresh")
    return jsonify({"job": launch("embeddings", doc or "(corpus)", py(*argv))})


@app.post("/api/entities")
def api_entities():
    """Extract named entities into the cross-linkage tables, from the UI."""
    data = request.get_json(force=True) or {}
    db   = data.get("db") or "data/context.db"
    doc  = data.get("doc")
    argv = [script("extract_entities.py"), "--db", db]
    if doc:
        doc = _validate_doc(doc)
        if not doc:
            return jsonify({"error": "invalid doc"}), 400
        argv += ["--doc", doc]
    if data.get("retry_empty"):
        argv.append("--retry-empty")
    return jsonify({"job": launch("entities", doc or "(corpus)", py(*argv))})


@app.post("/api/translate")'''),

    # 3. dates on every status row (both loops), so the UI can sort by them
    ('''                    "exports":          count_exports(exports, doc),
                    "composition":      doc_composition(con, doc),
                })
                seen.add(doc)''',
     '''                    "exports":          count_exports(exports, doc),
                    "composition":      doc_composition(con, doc),
                    **doc_times(inbox, raw, doc),
                })
                seen.add(doc)'''),

    ('''                    "exports":          count_exports(exports, doc),
                    "composition":      doc_composition(con, doc),
                })
        rows.sort''',
     '''                    "exports":          count_exports(exports, doc),
                    "composition":      doc_composition(con, doc),
                    **doc_times(inbox, raw, doc),
                })
        rows.sort'''),

    # 4. the helper itself
    ('''def doc_composition(con, doc: str) -> dict:''',
     '''def doc_times(inbox, raw, doc: str) -> dict:
    """When was this book added, and when did work last touch it?

    /api/status carried no dates at all, so the pipeline table could not be
    ordered by anything but name. first_seen is the OLDEST inbox page (when the
    book arrived); last_ocr is the NEWEST OCR output (when work last ran).
    Epoch seconds, or None. Cheap: a directory stat, no DB. (PHASE_G_2026_09_06)
    """
    out = {"first_seen": None, "last_ocr": None, "last_activity": None}
    try:
        ins = [p.stat().st_mtime for p in pathlib.Path(inbox).glob(f"{doc}_*.pdf")]
        if ins:
            out["first_seen"] = min(ins)
    except Exception:
        pass
    try:
        js = [p.stat().st_mtime for p in pathlib.Path(raw).glob(f"{doc}_*.jsonl")]
        if js:
            out["last_ocr"] = max(js)
    except Exception:
        pass
    cands = [v for v in (out["first_seen"], out["last_ocr"]) if v]
    out["last_activity"] = max(cands) if cands else None
    return out


def doc_composition(con, doc: str) -> dict:'''),
]

# ------------------------------------------------------- dashboard_static.html
HTML_EDITS = [
    # 1. resizable panes: CSS variables + splitter styling
    ('''.app{display:grid;grid-template-columns:320px 1fr 340px;grid-template-rows:56px 1fr;height:100vh}''',
     '''/* PHASE_G_2026_09_06: panes were fixed at 320px 1fr 340px so nothing resized.
   Widths are CSS variables driven by two draggable splitters and remembered in
   localStorage, which is per-browser and safe to lose. */
.app{display:grid;grid-template-columns:var(--lw,320px) 6px 1fr 6px var(--rw,340px);
     grid-template-rows:56px 1fr;height:100vh}
/* grid-row:2 is LOAD-BEARING. .sidebar/.main/.log-panel all declare
   grid-row:2, and CSS Grid places definite-row items BEFORE auto-placed
   ones - so a splitter without it is swept to columns 4-5 and .main is
   squeezed into the 6px track. Caught only by rendering the page. */
.splitter{grid-row:2;cursor:col-resize;background:var(--border-v,#2a2a2a);transition:background .12s}
.splitter:hover,.splitter.dragging{background:var(--gold,#c9a227)}
th.sortable{cursor:pointer;user-select:none;white-space:nowrap}
th.sortable:hover{color:var(--gold,#c9a227)}
th.sortable .arrow{opacity:.45;font-size:9px;margin-left:3px}
/* Embed + Entities push the actions cell onto a 4th wrapped line
   (132.5px -> 162.5px a row). Scoped to the pipeline table: .btn-act is
   used in other panels too. Measured back to 143.5px. */
.pipeline-table .btn-act{padding:3px 7px;font-size:10px}
/* Once the panes really resize, a narrow middle pane clips the Actions
   column and there is no way to scroll to it. Measured at 200px/620px:
   a 900px table in an 808px box. */
#pipelineWrap{overflow-x:auto}'''),

    # 2. sortable headers + date columns
    ("""    '<th>Document</th><th>PDFs</th><th>Ingested</th>' +""",
     """    '<th class="sortable" data-sort="doc">Document<span class="arrow"></span></th>' +
    '<th class="sortable" data-sort="pdf_count">PDFs<span class="arrow"></span></th>' +
    '<th class="sortable" data-sort="ingested_pages">Ingested<span class="arrow"></span></th>' +
    '<th class="sortable" data-sort="first_seen">Added<span class="arrow"></span></th>' +
    '<th class="sortable" data-sort="last_activity">Last run<span class="arrow"></span></th>' +"""),
]


def check(path, edits):
    s = read(path)
    missing = []
    for i, (old, _new) in enumerate(edits, 1):
        n = s.count(old)
        if n != 1:
            missing.append((i, n, old.splitlines()[0][:70]))
    return s, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    for p in (PY, HTML):
        if not os.path.exists(p):
            sys.exit(f"not found: {p} - run from the repo root")

    if args.verify:
        ok = True
        for p in (PY, HTML):
            has = MARKER in read(p)
            print(f"  {p:34s} patched={has}")
            ok &= has
        try:
            py_compile.compile(PY, doraise=True)
            print("  dashboard.py compiles OK")
        except Exception as exc:
            print(f"  dashboard.py DOES NOT COMPILE: {exc}"); ok = False
        for ep in ("/api/embeddings", "/api/entities"):
            print(f"  endpoint {ep:18s} present={ep in read(PY)}")
        sys.exit(0 if ok else 1)

    if MARKER in read(PY) and MARKER in read(HTML):
        print("Already applied (marker found). Nothing to do."); return

    print("Checking every anchor before touching anything...")
    bad = False
    for path, edits in ((PY, PY_EDITS), (HTML, HTML_EDITS)):
        _s, missing = check(path, edits)
        print(f"  {path}: {len(edits)-len(missing)}/{len(edits)} anchors matched")
        for i, n, frag in missing:
            print(f"    edit {i}: found {n} times (need exactly 1) -> {frag}")
            bad = True
    if bad:
        sys.exit("\nABORTED - an anchor is missing or ambiguous. Nothing was written.\n"
                 "The file has probably drifted from what this patch expects.")
    if not args.apply:
        print("\nAll anchors OK. Re-run with --apply."); return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs("backups", exist_ok=True)
    backups = {}
    for path in (PY, HTML):
        b = os.path.join("backups", f"{os.path.basename(path)}.preG.{stamp}")
        shutil.copy2(path, b); backups[path] = b
        print(f"  backup: {b}")

    try:
        for path, edits in ((PY, PY_EDITS), (HTML, HTML_EDITS)):
            s = read(path)
            for old, new in edits:
                assert s.count(old) == 1
                s = s.replace(old, new, 1)
            write(path, s)
        py_compile.compile(PY, doraise=True)
    except Exception as exc:
        for path, b in backups.items():
            shutil.copy2(b, path)
        sys.exit(f"FAILED ({exc}) - both files restored from backup.")

    print("\nApplied. Now add the front-end wiring with patch_ui_phase_g_js.py,")
    print("then restart:  powershell -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1")


if __name__ == "__main__":
    main()
