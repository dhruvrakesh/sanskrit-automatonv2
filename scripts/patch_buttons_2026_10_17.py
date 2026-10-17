#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_buttons_2026_10_17.py  (2026-10-17)  BUTTONS_2026_10_17

Asked on 17 Oct to check the main page's buttons, their wiring and their rationale (docs/BUTTONS_2026-10-17.md).
Two of them could undo the path's work in one press:
  - Translate All OCR'd ran advance_pipeline.py (8 Sep): 22 texts named then, each ingested again from data/raw
    (Tesseract's pages) and translated with flash, whatever its path or register says; several have since been
    repaired, renamed or retired. Retired: /api/pipeline/advance answers 410 and says where to go; the button is a
    link to the desk. The script stays, unrun.
  - Ingest (and Full, whose second step is the same ingest) writes a text's pages over its passages in place and
    keeps each English where it stands: where the pages now read differently, an English can stand beside a verse it
    was not made from. For a text with English, /api/ingest and /api/queue/run answer 409 with the reason and the safe
    way (the re-ingest of the changed pages, reingest_pages.py, planned free on the Repair page); the button asks and
    goes on with force. Full also asks the path's question (the translation desk's guard). Ingest All leaves the texts
    with English and names them.

scripts/dashboard.py and scripts/dashboard_static.html (need SCHOLAR_EDITION_2026_10_17). Anchored, all-or-nothing,
marker-idempotent; keeps line endings; py_compile before the atomic replace; backups .bak_buttons_<date>. No database
change.
  python scripts\\patch_buttons_2026_10_17.py --check
  python scripts\\patch_buttons_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'BUTTONS_2026_10_17'
NEEDS = {'scripts/dashboard.py': 'SCHOLAR_EDITION_2026_10_17', 'scripts/dashboard_static.html': 'SCHOLAR_EDITION_2026_10_17'}
FILES = list(NEEDS)
TAG = 'buttons'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, r'''@app.post("/api/ingest")
def api_ingest():
''', r'''# BUTTONS_2026_10_17 -----------------------------------------------------------------------------------------------
# The main page's buttons, read on 17 Oct against what they run (docs/BUTTONS_2026-10-17.md). Ingest (and Full, whose
# second step is the same ingest) writes a text's pages into the database again: ingest_jsonl_fast.py updates each
# passage in place by its page and its place on the page and keeps its English, so when the pages read differently
# now (a repair, a new OCR) an English can stand beside a verse it was not made from. For a text that has English the
# re-ingest of the changed pages (reingest_pages.py: the Repair page, the plan free) is the safe way; Ingest asks
# first. Translate All OCR'd (advance_pipeline.py, 8 Sep) is retired: it re-ingested 22 texts named then from
# Tesseract's pages, some since repaired, renamed or retired, and translated them with flash whatever their path.
def _ingest_warning(doc: str, db: str):
    """Why an ingest of doc asks first ({"say", "english", "passages", "mark"}), or None. Never raises."""
    try:
        p = pathlib.Path(db)
        if not p.exists():
            return None
        con = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            n, en = con.execute("SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(p.translation, '')) <> '' THEN 1 ELSE 0 "
                                "END) FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ?", (doc,)).fetchone()
        finally:
            con.close()
    except Exception:
        return None
    n, en = int(n or 0), int(en or 0)
    if not en:
        return None
    return {"passages": n, "english": en, "mark": "BUTTONS_2026_10_17",
            "say": ("%s has %d passages, %d of them with English. Ingesting its pages again writes their reading over the "
                    "passages in place and keeps each English where it stands: where the pages now read differently (a "
                    "repair, a new OCR), an English can stand beside a verse it was not made from. The safe way is the "
                    "re-ingest of the changed pages: the Repair page plans it, free (python scripts\\reingest_pages.py "
                    "--doc %s)." % (doc, n, en, doc))}


@app.post("/api/ingest")
def api_ingest():
''')

edit('scripts/dashboard.py', 2, r'''    db   = data.get("db")  or "data/context.db"
    raw  = data.get("raw") or "data/raw"
    glob = str(pathlib.Path(raw) / f"{doc}_*.jsonl")
''', r'''    db   = data.get("db")  or "data/context.db"
    raw  = data.get("raw") or "data/raw"
    if not data.get("force"):   # BUTTONS_2026_10_17: a text with English: the re-ingest of the changed pages first
        _w = _ingest_warning(doc, db)
        if _w:
            return jsonify(dict(_w, error=_w["say"], needs_force=True)), 409
    glob = str(pathlib.Path(raw) / f"{doc}_*.jsonl")
''')

edit('scripts/dashboard.py', 3, r'''    skip_export    = bool(data.get("skip_export"))

    base = [script("pipeline_queue.py"),
''', r'''    skip_export    = bool(data.get("skip_export"))
    if not data.get("force"):   # BUTTONS_2026_10_17: Full ingests again and translates: the same questions first
        _g = None if skip_translate else _desk_guard(doc)
        _w = None if skip_ingest else _ingest_warning(doc, db)
        if _g or _w:
            _say = " ".join(x["say"] for x in (_g, _w) if x)
            return jsonify({"error": _say, "say": _say, "needs_force": True, "mark": "BUTTONS_2026_10_17",
                            "label": (_g or {}).get("label") or "it has English"}), 409

    base = [script("pipeline_queue.py"),
''')

edit('scripts/dashboard.py', 4, r'''    cmd = py(script("advance_pipeline.py"))
    jid = launch("advance_pipeline", "all_docs", cmd)
    return jsonify({"job": jid, "message": "Advancing all OCRd docs through pipeline"})
''', r'''    # BUTTONS_2026_10_17: retired. advance_pipeline.py (8 Sep) re-ingested 22 texts named then from data/raw
    # (Tesseract), some since repaired, renamed or retired, and translated them with flash whatever their path.
    return jsonify({"error": "Translate All OCR'd is retired (17 Oct): it re-ingested 22 texts named on 8 Sep from "
                             "Tesseract's pages and translated them whatever their path. The desk (/desk) has each "
                             "text's next step; Translate ALL leaves the texts whose path says the reading comes "
                             "first.", "retired": True, "desk": "/desk", "mark": "BUTTONS_2026_10_17"}), 410
''')

edit('scripts/dashboard_static.html', 1, r'''      <button class="btn-batch" id="advanceBtn" onclick="advancePipeline()" style="background:linear-gradient(135deg,#1a3a1a,#0f2a0f);color:#5aaa7a;border:1px solid #2d6a2d;font-weight:700" title="Translate all already-OCRd docs in priority order (no new OCR)">
        &#x26A1; Translate All OCR'd
      </button>
''', r'''      <a class="btn-batch" id="advanceBtn" href="/desk" target="_blank" style="background:linear-gradient(135deg,#1a3a1a,#0f2a0f);color:#5aaa7a;border:1px solid #2d6a2d;font-weight:700;text-decoration:none" title="BUTTONS_2026_10_17: Translate All OCR'd is retired (it re-ingested 22 texts named on 8 Sep from Tesseract's pages and translated them whatever their path). The desk has each text's next step.">
        &#x26A1; The desk: each text's next step
      </a>
''')

edit('scripts/dashboard_static.html', 2, r'''async function doAction(act, doc) {
''', r'''async function doAction(act, doc, opts) {   // BUTTONS_2026_10_17: opts.bulk leaves a text that asks, quietly
''')

edit('scripts/dashboard_static.html', 3, r'''  if (act === 'ingest') {
    const r = await fetch('/api/ingest', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, raw: cfg.raw})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, 'Ingest ' + doc, 'ingest', doc); toast('Ingest started for ' + doc); }
  }
''', r'''  if (act === 'ingest') {
    let r = await fetch('/api/ingest', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, raw: cfg.raw})});
    let j = await r.json();
    if (r.status === 409 && j.needs_force) {   // BUTTONS_2026_10_17: it has English
      if ((opts || {}).bulk) return 'held';
      if (!confirm(j.say + '\n\nIngest it again anyway?')) { toast('Not ingested: ' + doc + ' (the Repair page plans the changed pages, free)', 'fail'); return; }
      r = await fetch('/api/ingest', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({doc, db: cfg.db, raw: cfg.raw, force: true})});
      j = await r.json();
    }
    if (j.job) { trackJob(j.job, 'Ingest ' + doc, 'ingest', doc); toast('Ingest started for ' + doc); }
    else if (j.error) toast(j.error, 'fail');
  }
''')

edit('scripts/dashboard_static.html', 4, r'''    const r = await fetch('/api/queue/run', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, inbox: cfg.inbox, raw: cfg.raw,
                            exports: cfg.exports, engine: eng})});
    const j = await r.json();
''', r'''    let r = await fetch('/api/queue/run', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db, inbox: cfg.inbox, raw: cfg.raw,
                            exports: cfg.exports, engine: eng})});
    let j = await r.json();
    if (r.status === 409 && j.needs_force) {   // BUTTONS_2026_10_17: the path, or English that an ingest would leave in place
      if (!confirm(j.say + '\n\nRun the full pipeline anyway?')) { toast('Not run: ' + doc + ' (the desk has its steps)', 'fail'); return; }
      r = await fetch('/api/queue/run', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({doc, db: cfg.db, inbox: cfg.inbox, raw: cfg.raw, exports: cfg.exports, engine: eng, force: true})});
      j = await r.json();
    }
    if (!j.job && j.error) toast(j.error, 'fail');
''')

edit('scripts/dashboard_static.html', 5, r'''  if (act === 'export') {  // EXPORT_MODE_VISIBLE_2026_09_30
    var nExp''', r'''  if (act === 'ingest') {   // BUTTONS_2026_10_17: one at a time; the texts with English are left, and named
    var _left = [], _bs = Array.from(document.querySelectorAll('button[data-act="ingest"]'));
    for (var _k = 0; _k < _bs.length; _k++) { if (await doAction('ingest', _bs[_k].dataset.doc, {bulk: true}) === 'held') _left.push(_bs[_k].dataset.doc); }
    if (_left.length) toast(_left.length + ' text(s) with English left as they are (the Repair page plans their changed pages, free): ' + _left.slice(0, 6).join(', ') + (_left.length > 6 ? ' ...' : ''), 'fail');
    return;
  }
  if (act === 'export') {  // EXPORT_MODE_VISIBLE_2026_09_30
    var nExp''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_buttons_2026_10_17')
    print('  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
