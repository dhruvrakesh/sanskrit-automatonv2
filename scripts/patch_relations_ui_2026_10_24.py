#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
RELATIONS_UI_2026_10_24: the Relations page on the PC's dashboard (http://127.0.0.1:5057/relations).

Asked on 24 Oct: "do we have an authoritative local and Srangam UI for these interrelationships, visually explaining
them, and selections?" Locally there was none: the relations lived in exports (CSV and Markdown) and in the
Professor's evidence. This adds the page and its API, read-only:

  * /relations (scripts/relations.html): a name, chosen with suggestions; a drawing of whom our texts name it with
    (the inner ring, the line's width by passages) and whom the indexes relate to it (the outer ring, coloured by the
    kind of relation, dashed where our texts never name the two together); "Named together in our texts" with the
    passages where they first meet; "In the indexes": each PERSON of that name as one index enters him or her, apart
    from the homonyms, with each relation's words, reference, verdict against our verses and Raychaudhuri's view; the
    line of descent through each, by the index's own entries; Raychaudhuri's claims. Selections: the index, the kind
    of relation, "named together only", the inner ring on or off. A click on any name goes to it.
  * /api/relations (scripts/relations_view.py, new): ?find= for the suggestions, ?id= for the page. context.db,
    data/shelf/kin.db and claims.db are opened mode=ro; nothing is written; no model is called.
  * Links to it: the dashboard's top bar, the Library's header, the Ask page's menu, and the Professor's names.

Restart the dashboard when it is idle. Run from the repo root:
  python scripts\\patch_relations_ui_2026_10_24.py --check   then without --check.
Backups: .bak_relations_ui_ and the date beside each file. Test: tests\\test_relations_ui_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'RELATIONS_UI_2026_10_24'
TAG = 'relations_ui'
FILES = ['scripts/dashboard.py', 'scripts/dashboard_static.html', 'scripts/ask.html']
NEEDS = {'scripts/dashboard.py': 'ASK_HOMONYM_2026_10_24', 'scripts/dashboard_static.html': 'UI_CLARITY_2026_10_22', 'scripts/ask.html': 'ASK_PROF_2026_10_23'}
REQUIRES = {'scripts/relations_view.py': 'RELATIONS_UI_2026_10_24', 'scripts/relations.html': 'RELATIONS_UI_2026_10_24'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, '  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>\n  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>\n</header>\n<main>{body}</main>',
     '  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>\n  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>\n  <a class="back" href="/relations" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128279; Relations</a>\n</header>\n<main>{body}</main>')

edit('scripts/dashboard.py', 2, '\n\n# \u2500\u2500 Launch Datasette (SQL explorer) on a consistent snapshot, from the UI \u2500\u2500\u2500\u2500\u2500\u2500\n_DATASETTE = {"proc": None, "port": 8001}',
     '\n\n# RELATIONS_UI_2026_10_24: the names and their relations, seen and chosen (scripts/relations.html), read-only.\n@app.get("/relations")\ndef relations_page():\n    return send_from_directory(str(SCRIPTS), "relations.html")\n\n\n@app.get("/api/relations")\ndef api_relations():\n    """RELATIONS_UI_2026_10_24: ?find=<text> -> {"names": [our names that match]}; ?id=<entity id> -> whom our texts\n    name it with, what the indexes state of each person of that name, the lines of descent, Raychaudhuri\'s claims\n    (scripts/relations_view.py). Read-only: context.db, data/shelf/kin.db and claims.db opened mode=ro."""\n    if str(SCRIPTS) not in sys.path:\n        sys.path.insert(0, str(SCRIPTS))\n    import relations_view as rv\n    db = str(ROOT / "data" / "context.db")\n    try:\n        if "id" in request.args:\n            eid = int(request.args.get("id") or 0)\n            k = max(1, min(60, int(request.args.get("k") or 24)))\n            return jsonify(rv.view(db, eid, ROOT / "data" / "shelf", k=k))\n        return jsonify({"names": rv.find(db, request.args.get("find", ""), limit=12), "mark": rv.MARK})\n    except (ValueError, sqlite3.Error) as e:\n        return jsonify({"error": "%s: %s" % (type(e).__name__, str(e)[:200])}), 400\n\n\n# \u2500\u2500 Launch Datasette (SQL explorer) on a consistent snapshot, from the UI \u2500\u2500\u2500\u2500\u2500\u2500\n_DATASETTE = {"proc": None, "port": 8001}')

edit('scripts/dashboard_static.html', 1, '    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#128172; Ask</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>',
     '    <details class="tn" ontoggle="if(this.open)document.querySelectorAll(\'details.tn[open]\').forEach(function(d){if(d!==this)d.open=false},this)" onmouseenter="clearTimeout(this._tnT)" onmouseleave="var d=this;clearTimeout(d._tnT);d._tnT=setTimeout(function(){d.open=false},450)"><summary>&#128172; Ask</summary><div class="tn-pop">\n      <a class="btn-refresh" href="/ask" target="_blank" style="text-decoration:none;margin-right:6px" title="Ask questions answered from the corpus, with cited verses">&#128172; Ask the Corpus</a>\n      <a class="btn-refresh" href="/relations" target="_blank" style="text-decoration:none;margin-right:6px" title="RELATIONS_UI_2026_10_24: whom our texts name together, what the indexes state of each person, the lines of descent and Raychaudhuri\'s claims">&#128279; Relations</a>\n      <button class="btn-refresh" onclick="openDatabase(this)" style="margin-right:6px" title="Open the corpus in Datasette for SQL querying (snapshots first, then launches)">&#128190; Database</button>\n    </div></details>')

edit('scripts/ask.html', 1, '      <a href="/">&larr; Dashboard</a>\n      <a href="/library">Library</a>\n    </nav>\n  </header>',
     '      <a href="/">&larr; Dashboard</a>\n      <a href="/library">Library</a>\n      <a href="/relations" title="RELATIONS_UI_2026_10_24: the names and their relations">Relations</a>\n    </nav>\n  </header>')

edit('scripts/ask.html', 2, '    $("schNames").innerHTML = (sc.names || []).map(function(n){\n      var t = (n.together || []).map(function(x){ return esc(x.name) + " " + x.passages; }).join(", ");\n      return "<div><b>" + esc(n.name) + "</b>" + (t ? " with " + t : "") + "</div>";\n    }).join("") || "<div>(none)</div>";\n    box.hidden = false;',
     '    $("schNames").innerHTML = (sc.names || []).map(function(n){\n      var t = (n.together || []).map(function(x){ return esc(x.name) + " " + x.passages; }).join(", ");\n      return "<div><a href=\\"/relations?name=" + encodeURIComponent(n.name) + "\\" title=\\"This name on the Relations page\\"><b>" +\n        esc(n.name) + "</b></a>" + (t ? " with " + t : "") + "</div>";   // RELATIONS_UI_2026_10_24\n    }).join("") || "<div>(none)</div>";\n    box.hidden = false;')


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
