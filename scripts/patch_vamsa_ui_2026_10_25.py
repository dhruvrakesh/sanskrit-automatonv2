#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_vamsa_ui_2026_10_25.py  (2026-10-25)  VAMSA_UI_2026_10_25

The Vamsa page on the dashboard: the lines of descent of the three indexes, generation by generation, each step with
the index's words, the Sanskrit verse where both names stand (GRETIL's editions, read by scripts\vamsa_check.py), the
verses of the Mahabharata, the Harivamsa and the Ramayana that name both, our own passages and Raychaudhuri's view.

  scripts/dashboard.py          /vamsa (scripts/vamsa.html) and /api/vamsa (scripts/vamsa_view.py: ?lines=1,
                                ?find=, ?src=&entry=[&path=|&via=]), read-only; and a Vamsa link in the library's header
  scripts/dashboard_static.html a Vamsa button after Relations
  scripts/relations.html        a Vamsa link in its header, and "the whole line" beside each line of descent
  scripts/ask.html              a Vamsa link; a question brought in the address (/ask?q=...&mode=professor) is put
                                in the box, not asked (each answer is metered: the reader asks it)

Needs RELATIONS_UI_2026_10_24 in each file, and scripts/vamsa_view.py, scripts/vamsa.html and scripts/vamsa_check.py
in place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_vamsaui_<date> copy of each file;
dashboard.py compiled before anything is written. Restart the dashboard (scripts\restart_dashboard.ps1) when it is
idle; the page reads data\shelf\vamsa.db (python scripts\vamsa_check.py --yes, free).

  python scripts\patch_vamsa_ui_2026_10_25.py --check
  python scripts\patch_vamsa_ui_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_UI_2026_10_25'
TAG = 'vamsaui'
FILES = ['scripts/dashboard.py', 'scripts/dashboard_static.html', 'scripts/relations.html', 'scripts/ask.html']
NEEDS = {'scripts/dashboard.py': 'RELATIONS_UI_2026_10_24', 'scripts/dashboard_static.html': 'RELATIONS_UI_2026_10_24', 'scripts/relations.html': 'RELATIONS_UI_2026_10_24', 'scripts/ask.html': 'RELATIONS_UI_2026_10_24'}
REQUIRES = {'scripts/vamsa_view.py': 'VAMSA_UI_2026_10_25', 'scripts/vamsa.html': 'VAMSA_UI_2026_10_25', 'scripts/vamsa_check.py': 'VAMSA_CHECK_2026_10_25'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, '  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>\n  <a class="back" href="/relations" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128279; Relations</a>\n</header>\n<main>{body}</main>',
     '  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>\n  <a class="back" href="/relations" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128279; Relations</a>\n  <a class="back" href="/vamsa" title="VAMSA_UI_2026_10_25: the lines of descent, generation by generation, each step with the Sanskrit verse where both names stand" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#127795; Vamsa</a>\n</header>\n<main>{body}</main>')

edit('scripts/dashboard.py', 2, '\n\n# \u2500\u2500 Launch Datasette (SQL explorer) on a consistent snapshot, from the UI \u2500\u2500\u2500\u2500\u2500\u2500\n_DATASETTE = {"proc": None, "port": 8001}',
     '\n\n# VAMSA_UI_2026_10_25: the lines of descent, generation by generation, each step with its verse (scripts/vamsa.html).\n@app.get("/vamsa")\ndef vamsa_page():\n    return send_from_directory(str(SCRIPTS), "vamsa.html")\n\n\n@app.get("/api/vamsa")\ndef api_vamsa():\n    """VAMSA_UI_2026_10_25: ?lines=1[&src=] -> the longest lines of each index; ?find=<text>[&src=] -> the index\'s\n    persons of that name; ?src=<pui|inm|vei>&entry=<id>[&path=<ids>|&via=<a parent>] -> the line up and down, each\n    step with the index\'s words, the verse where both names stand, the epics\' verses and our passages\n    (scripts/vamsa_view.py).\n    Read-only: context.db, data/shelf/kin.db and vamsa.db opened mode=ro; no model is called."""\n    if str(SCRIPTS) not in sys.path:\n        sys.path.insert(0, str(SCRIPTS))\n    import vamsa_view as vv\n    db = str(ROOT / "data" / "context.db")\n    shelf = ROOT / "data" / "shelf"\n    src = (request.args.get("src") or "").strip()\n    try:\n        if request.args.get("lines"):\n            return jsonify(vv.lines(db, str(shelf / "kin.db"), src=src))\n        if "find" in request.args:\n            return jsonify({"persons": vv.find(db, str(shelf / "kin.db"), request.args.get("find", ""), src=src),\n                            "mark": vv.MARK})\n        entry = int(request.args.get("entry") or 0)\n        path = [int(x) for x in (request.args.get("path") or "").split(",") if x.strip()][:400] or None\n        via = int(request.args["via"]) if (request.args.get("via") or "").lstrip("-").isdigit() else None\n        return jsonify(vv.tree(db, str(shelf / "kin.db"), str(shelf / "vamsa.db"), src, entry, path=path, via=via))\n    except (ValueError, sqlite3.Error) as e:\n        return jsonify({"error": "%s: %s" % (type(e).__name__, str(e)[:200])}), 400\n\n\n# \u2500\u2500 Launch Datasette (SQL explorer) on a consistent snapshot, from the UI \u2500\u2500\u2500\u2500\u2500\u2500\n_DATASETTE = {"proc": None, "port": 8001}')

edit('scripts/dashboard_static.html', 1, '      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <a class="btn-refresh" href="/relations" target="_blank" style="text-decoration:none;margin-right:6px" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent and Raychaudhuri\'s claims">&#128279; Relations</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>',
     '      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <a class="btn-refresh" href="/relations" target="_blank" style="text-decoration:none;margin-right:6px" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent and Raychaudhuri\'s claims">&#128279; Relations</a>\n      <a class="btn-refresh" href="/vamsa" target="_blank" style="text-decoration:none;margin-right:6px" title="VAMSA_UI_2026_10_25: the lines of descent, generation by generation, each step with the Sanskrit verse where both names stand">&#127795; Vamsa</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>')

edit('scripts/relations.html', 1, '      <a href="/">&larr; Dashboard</a>\n      <a href="/ask">Ask</a>\n      <a href="/library">Library</a>\n    </nav>',
     '      <a href="/">&larr; Dashboard</a>\n      <a href="/ask">Ask</a>\n      <a href="/vamsa" title="VAMSA_UI_2026_10_25: the lines of descent, each step with its verse">Vamsa</a>\n      <a href="/library">Library</a>\n    </nav>')

edit('scripts/relations.html', 2, '  }\n  function lineOf(p){\n    var h = "<h3>Line of descent in the " + esc(p.index) + "</h3><div class=\\"line\\">";\n    var up = p.up.slice().reverse();\n    up.forEach(function(gen, i){',
     '  }\n  function lineOf(p){\n    var h = "<h3>Line of descent in the " + esc(p.index) + " <a href=\\"/vamsa?src=" + encodeURIComponent(p.source) + "&entry=" + p.entry +\n      "\\" style=\\"text-transform:none;letter-spacing:0;font-weight:500\\" title=\\"VAMSA_UI_2026_10_25: the whole line, each step with its verse\\">the whole line &rarr;</a></h3><div class=\\"line\\">";\n    var up = p.up.slice().reverse();\n    up.forEach(function(gen, i){')

edit('scripts/ask.html', 1, '      <a href="/library">Library</a>\n      <a href="/relations" title="RELATIONS_UI_2026_10_24: the names and their relations">Relations</a>\n    </nav>\n  </header>',
     '      <a href="/library">Library</a>\n      <a href="/relations" title="RELATIONS_UI_2026_10_24: the names and their relations">Relations</a>\n      <a href="/vamsa" title="VAMSA_UI_2026_10_25: the lines of descent, each step with its verse">Vamsa</a>\n    </nav>\n  </header>')

edit('scripts/ask.html', 2, '  document.querySelectorAll("[data-mode]").forEach(function(b){ b.addEventListener("click", function(){ setMode(b.dataset.mode); }); });\n  setMode(store("askMode") || "verses");\n\n  $("k").addEventListener("input", function(){ $("kv").textContent = this.value; });',
     '  document.querySelectorAll("[data-mode]").forEach(function(b){ b.addEventListener("click", function(){ setMode(b.dataset.mode); }); });\n  setMode(store("askMode") || "verses");\n  /* VAMSA_UI_2026_10_25: a question brought from another page (/ask?q=...&mode=professor) is put in the box, not asked:\n     each answer is metered, so the reader asks it */\n  (function(){\n    var P = new URLSearchParams(location.search);\n    if (P.get("mode")) setMode(P.get("mode"));\n    if (P.get("q")) setQ(P.get("q").slice(0, 600));\n  })();\n\n  $("k").addEventListener("input", function(){ $("kv").textContent = this.value; });')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
