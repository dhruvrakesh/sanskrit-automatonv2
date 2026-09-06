#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ui_phase_g_js.py - Phase G part 2: the front-end wiring. (2026-09-06)

Run AFTER patch_ui_phase_g.py, which added the CSS variables, the sortable
headers, the date fields and the /api/embeddings + /api/entities endpoints.

Adds:
  * two draggable splitters between the three panes, widths persisted in
    localStorage (per-browser, safe to lose, falls back to the defaults)
  * click-to-sort on the pipeline headers, including the new Added / Last run
    columns; sort key and direction also persisted
  * the two date cells in each row
  * per-doc "Embed" and "Entities" buttons and their doAction branches

Same safety contract: anchors asserted unique, backup first, full rollback if
anything fails, idempotent via the marker.

  python scripts\\patch_ui_phase_g_js.py
  python scripts\\patch_ui_phase_g_js.py --apply
"""
from __future__ import annotations
import argparse, io, os, shutil, sys, time

MARKER = "PHASE_G_JS_2026_09_06"
HTML = os.path.join("scripts", "dashboard_static.html")

EDITS = [
    # 1. splitter elements between the panes (grid is now 5 columns)
    ('''  <main class="main">''',
     '''  <div class="splitter" id="splitL" title="Drag to resize"></div>
  <main class="main">'''),

    ('''  <aside class="log-panel">''',
     '''  <div class="splitter" id="splitR" title="Drag to resize"></div>
  <aside class="log-panel">'''),

    # 2. the two date cells, right after the Ingested progress cell
    ("""      '<td>' + progBar(r.ingested_pages, ingestDenom, false) + '</td>' +""",
     """      '<td>' + progBar(r.ingested_pages, ingestDenom, false) + '</td>' +
      '<td><span class="num-cell" title="' + fullDate(r.first_seen) + '">' + shortDate(r.first_seen) + '</span></td>' +
      '<td><span class="num-cell" title="' + fullDate(r.last_activity) + '">' + shortDate(r.last_activity) + '</span></td>' +"""),

    # 3. Embed / Entities buttons
    ("""        '<button class="btn-act exp" data-act="export" data-doc="' + esc(r.doc) + '">Export</button>' +""",
     """        '<button class="btn-act emb" data-act="embeddings" data-doc="' + esc(r.doc) + '"' +
          ' title="Rebuild this doc\\'s semantic index so search and Ask the Corpus see it">Embed</button>' +
        '<button class="btn-act ent" data-act="entities" data-doc="' + esc(r.doc) + '"' +
          ' title="Extract named entities for cross-linking">Entities</button>' +
        '<button class="btn-act exp" data-act="export" data-doc="' + esc(r.doc) + '">Export</button>' +"""),

    # 4. behaviour: sorting, dates, splitters, and the two new actions
    ('''function renderPipeline(rows) {''',
     '''// ---- PHASE_G_JS_2026_09_06 -------------------------------------------------
// Dates, sorting and resizable panes. /api/status had no dates at all until
// Phase G, so the table could only be ordered by name.
var _sortKey = null, _sortDir = -1;
try {
  var _ss = localStorage.getItem('pipeSort');
  if (_ss) { var _o = JSON.parse(_ss); _sortKey = _o.k; _sortDir = _o.d; }
} catch(e) {}

function shortDate(ts){
  if (!ts) return '\\u2014';
  var d = new Date(ts * 1000), now = Date.now() / 1000;
  var days = (now - ts) / 86400;
  if (days < 1) return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  if (days < 7) return Math.floor(days) + 'd ago';
  return d.toLocaleDateString([], {day:'2-digit', month:'short'});
}
function fullDate(ts){ return ts ? new Date(ts * 1000).toLocaleString() : 'no date recorded'; }

function sortRows(rows){
  if (!_sortKey) return rows;
  var out = rows.slice();
  out.sort(function(a, b){
    var x = a[_sortKey], y = b[_sortKey];
    // Rows with no value sort last in BOTH directions - a missing date is not
    // "oldest", it is unknown, and burying it is less misleading.
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    if (typeof x === 'string') return _sortDir * x.localeCompare(y);
    return _sortDir * (x - y);
  });
  return out;
}

function wirePipelineSort(){
  document.querySelectorAll('th.sortable').forEach(function(th){
    var k = th.dataset.sort;
    var arrow = th.querySelector('.arrow');
    if (arrow) arrow.textContent = (_sortKey === k) ? (_sortDir > 0 ? '\\u25B2' : '\\u25BC') : '';
    th.onclick = function(){
      if (_sortKey === k) { _sortDir = -_sortDir; } else { _sortKey = k; _sortDir = -1; }
      try { localStorage.setItem('pipeSort', JSON.stringify({k:_sortKey, d:_sortDir})); } catch(e) {}
      if (window._lastPipeRows) renderPipeline(window._lastPipeRows);
    };
  });
}

(function initSplitters(){
  function restore(){
    try {
      var lw = localStorage.getItem('paneL'), rw = localStorage.getItem('paneR');
      if (lw) document.documentElement.style.setProperty('--lw', lw);
      if (rw) document.documentElement.style.setProperty('--rw', rw);
    } catch(e) {}
  }
  function drag(id, varName, storeKey, fromLeft){
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('mousedown', function(ev){
      ev.preventDefault();
      el.classList.add('dragging');
      function move(e){
        var w = fromLeft ? e.clientX : (window.innerWidth - e.clientX);
        w = Math.max(200, Math.min(700, w));          // keep both panes usable
        var px = w + 'px';
        document.documentElement.style.setProperty(varName, px);
        try { localStorage.setItem(storeKey, px); } catch(_) {}
      }
      function up(){
        el.classList.remove('dragging');
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', up);
    });
    el.addEventListener('dblclick', function(){    // double-click resets
      document.documentElement.style.removeProperty(varName);
      try { localStorage.removeItem(storeKey); } catch(_) {}
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){
      restore(); drag('splitL', '--lw', 'paneL', true); drag('splitR', '--rw', 'paneR', false);
    });
  } else {
    restore(); drag('splitL', '--lw', 'paneL', true); drag('splitR', '--rw', 'paneR', false);
  }
})();

function renderPipeline(rows) {
  window._lastPipeRows = rows;
  rows = sortRows(rows);'''),

    # 5. wire the header clicks after each render.
    #    The pipeline renders into #pipelineWrap, not #main - #main is the READER's
    #    container in dashboard.py, a different file. Anchored on the real call site.
    ("""  wrap.innerHTML = html;
  applyPipeFilter();""",
     """  wrap.innerHTML = html;
  wirePipelineSort();
  applyPipeFilter();"""),

    # 6. the two new doAction branches
    ('''  if (act === 'translate') {
    const eng   = getEngine(doc);''',
     '''  if (act === 'embeddings') {
    const r = await fetch('/api/embeddings', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, 'Embed ' + doc, 'embeddings', doc);
                 toast('Rebuilding semantic index for ' + doc); }
    else toast(j.error || 'Embeddings failed', 'err');
  }
  if (act === 'entities') {
    const r = await fetch('/api/entities', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({doc, db: cfg.db})});
    const j = await r.json();
    if (j.job) { trackJob(j.job, 'Entities ' + doc, 'entities', doc);
                 toast('Extracting entities for ' + doc); }
    else toast(j.error || 'Entity extraction failed', 'err');
  }
  if (act === 'translate') {
    const eng   = getEngine(doc);'''),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(HTML):
        sys.exit(f"not found: {HTML} - run from the repo root")
    s = io.open(HTML, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return
    if "PHASE_G_2026_09_06" not in s:
        sys.exit("Run patch_ui_phase_g.py FIRST - this patch builds on its CSS and headers.")

    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        if n != 1:
            print(f"  edit {i}: found {n} times (need 1) -> {old.splitlines()[0][:66]}")
            bad = True
    print(f"  {len(EDITS)-sum(1 for i,(o,_) in enumerate(EDITS) if s.count(o)!=1)}/{len(EDITS)} anchors matched")
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAll anchors OK. Re-run with --apply."); return

    b = os.path.join("backups", f"dashboard_static.html.preGjs.{time.strftime('%Y%m%d_%H%M%S')}")
    os.makedirs("backups", exist_ok=True)
    shutil.copy2(HTML, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        s = s.replace("<style>", f"<style>\n/* {MARKER} */", 1)
        io.open(HTML, "w", encoding="utf-8", newline="\n").write(s)
    except Exception as exc:
        shutil.copy2(b, HTML)
        sys.exit(f"FAILED ({exc}) - restored from backup.")
    print("\nApplied. Restart:")
    print("  powershell -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1")


if __name__ == "__main__":
    main()
