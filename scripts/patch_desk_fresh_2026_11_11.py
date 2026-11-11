#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_desk_fresh_2026_11_11.py  (2026-11-11)  DESK_FRESH_2026_11_11

Asked on 11 Nov, with a screenshot of /desk/gandharva_veda_natya_shastra: "why is python action not updating here in
natya shastra". The desk reads each text's path from data/text_path.json, the chart of every text; it was last
written on 28 Oct (17:48), before vision read the Gandharva Veda's 506 pages (10 and 11 Nov), so the desk still said
"repair the scan: vision has read 0 of its 507 pages" and offered that step. Its credit line said "$0.00 left (it
expires 2026-11-11)" because the dashboard was started before .env had the credit's settings (9 Nov): it showed
claude_engine's defaults, and the jobs it starts inherit them (the credit "expired" on 11 Nov for them).

This patch:
  scripts/text_path.py        --doc X --write: one text charted again (its e-text witness with it) and its row put
                              into the chart with its own time ("at"); the others as they were; a text whose path was
                              "retire" waits for the whole chart; without --write nothing is written, as before
  scripts/translation_desk.py row_at (a text's own chart time), changed_since (the OCR consensus, its merged pages,
                              the register: what changed it after its chart)
  scripts/claude_engine.py    dotenv_credit: the credit's three settings as .env has them (only those keys read)
  scripts/dashboard.py        the desk dates a text by its own row and says what changed since; "Chart this text
                              again (free)" (/api/repair step path_doc); the credit's settings read again from .env
                              when it changes (the desk, the Usage tab, BM1's caps and every job it starts); the
                              shell's own settings win, as at start
  tests/test_claude_engine_2026_10_15.py  two tests that ran on the default's last day (2026-11-11) set a later one
  tests/test_tier_r_2026_10_17.py, tests/test_redeem_2026_10_14.py  their patchers' results are now the .bak_deskfresh_
                              copies (this patch came after)

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_deskfresh_<date> copies.
Restart the dashboard (when no job runs) to load it.

  python scripts\\patch_desk_fresh_2026_11_11.py --check
  python scripts\\patch_desk_fresh_2026_11_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DESK_FRESH_2026_11_11'
TAG = 'deskfresh'
FILES = ['scripts/dashboard.py', 'scripts/text_path.py', 'scripts/translation_desk.py', 'scripts/claude_engine.py', 'tests/test_claude_engine_2026_10_15.py', 'tests/test_tier_r_2026_10_17.py', 'tests/test_redeem_2026_10_14.py']
NEEDS = {'scripts/dashboard.py': 'TRANSLATION_DESK_2026_10_17', 'scripts/text_path.py': 'PATH_2026_10_12', 'scripts/translation_desk.py': 'TRANSLATION_DESK_2026_10_17', 'scripts/claude_engine.py': 'CLAUDE_ENGINE_2026_10_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/dashboard.py', 1, '            os.environ.setdefault(k.strip(), v.strip().strip(\'"\').strip("\'"))\n\n_load_env()\n\nCORPUS_ROOT = pathlib.Path(os.environ.get("CORPUS_ROOT", r"D:\\hindu.holy.scriptures.all.sanskrit.pdf.entIDity"))',
     '            os.environ.setdefault(k.strip(), v.strip().strip(\'"\').strip("\'"))\n\n# DESK_FRESH_2026_11_11: the Claude credit\'s three settings the dashboard was started with from its shell win, as at\n# start; the others are read from .env again whenever it changes (_credit_env_fresh), for the desk, the Usage tab and\n# every job it starts (they inherit its environment): on 11 Nov the dashboard, started before .env had them (9 Nov),\n# showed "$0.00 left (it expires 2026-11-11)", the defaults, beside the CLI\'s $163.39 until 2026-12-11.\n_CREDIT_SHELL = {k for k in ("SA_CLAUDE_CREDIT_USD", "SA_CLAUDE_CREDIT_SINCE", "SA_CLAUDE_CREDIT_EXPIRES")\n                 if k in os.environ}\n_load_env()\n_CREDIT_ENV_SEEN = {"key": None}\n\n\ndef _credit_env_fresh() -> None:\n    """DESK_FRESH_2026_11_11: the credit\'s settings as .env has them now (claude_engine.dotenv_credit: those three keys\n    only), when .env changed since last read; never raises."""\n    try:\n        p = ROOT / ".env"\n        st = p.stat()\n        key = (st.st_mtime_ns, st.st_size)\n        if _CREDIT_ENV_SEEN["key"] == key:\n            return\n        import claude_engine as _ce\n        got = _ce.dotenv_credit(p)\n        for k in _ce.CREDIT_KEYS:\n            if k in _CREDIT_SHELL:\n                continue\n            if k in got:\n                os.environ[k] = got[k]\n            else:\n                os.environ.pop(k, None)\n        _CREDIT_ENV_SEEN["key"] = key\n    except Exception:\n        pass\n\n\nCORPUS_ROOT = pathlib.Path(os.environ.get("CORPUS_ROOT", r"D:\\hindu.holy.scriptures.all.sanskrit.pdf.entIDity"))')

edit('scripts/dashboard.py', 2, '    Windows encodes as cp1252 and raises UnicodeEncodeError(\'charmap\'), which\n    shows up as spurious per-verse errors (the infamous err:NNN counter)."""\n    env = dict(os.environ)\n    env["PYTHONUTF8"] = "1"                 # interpreter-wide UTF-8 mode',
     '    Windows encodes as cp1252 and raises UnicodeEncodeError(\'charmap\'), which\n    shows up as spurious per-verse errors (the infamous err:NNN counter)."""\n    _credit_env_fresh()   # DESK_FRESH_2026_11_11: a job bills the credit as .env has it now\n    env = dict(os.environ)\n    env["PYTHONUTF8"] = "1"                 # interpreter-wide UTF-8 mode')

edit('scripts/dashboard.py', 3, '                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed\n                 "withdraw", "path_all",                    # PATH_2026_10_12: off the site; the path of every text\n                 "redeem_all")                              # REDEEM_2026_10_14: what of the translation is kept\n_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand\n_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness',
     '                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed\n                 "withdraw", "path_all",                    # PATH_2026_10_12: off the site; the path of every text\n                 "redeem_all",                              # REDEEM_2026_10_14: what of the translation is kept\n                 "path_doc")                                # DESK_FRESH_2026_11_11: one text charted again (free)\n_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand\n_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness')

edit('scripts/dashboard.py', 4, '    elif step == "path_all":   # PATH_2026_10_12: free and read-only\n        argv = [script("text_path.py"), "--from-dashboard"]\n    elif step == "redeem_all":   # REDEEM_2026_10_14: free and read-only\n        argv = [script("redeem.py"), "--from-dashboard"]',
     '    elif step == "path_all":   # PATH_2026_10_12: free and read-only\n        argv = [script("text_path.py"), "--from-dashboard"]\n    elif step == "path_doc":   # DESK_FRESH_2026_11_11: free; the database read-only, its row put into the chart\n        argv = [script("text_path.py"), "--doc", doc, "--write", "--from-dashboard"]\n    elif step == "redeem_all":   # REDEEM_2026_10_14: free and read-only\n        argv = [script("redeem.py"), "--from-dashboard"]')

edit('scripts/dashboard.py', 5, '                try:\n                    p = bm.prices(mcon, BM1_DIR)\n                    caps = bm.caps(mcon)\n                finally:',
     '                try:\n                    p = bm.prices(mcon, BM1_DIR)\n                    _credit_env_fresh()   # DESK_FRESH_2026_11_11\n                    caps = bm.caps(mcon)\n                finally:')

edit('scripts/dashboard.py', 6, '                try:\n                    import claude_engine as _ce\n                    c = _ce.credit(con)\n                    res["caps"]["credit_left"] = max(0.0, float(c["left"]))',
     '                try:\n                    import claude_engine as _ce\n                    _credit_env_fresh()   # DESK_FRESH_2026_11_11\n                    c = _ce.credit(con)\n                    res["caps"]["credit_left"] = max(0.0, float(c["left"]))')

edit('scripts/dashboard.py', 7, '                "engines": dict(cv.get("engines") or {}), "spent": float(cv.get("spent") or 0.0),\n                "next": td.next_step(st, prow, cv, int(n.get("mula") or 0)),\n                "guard": td.guard(prow, rg, chart["at"])})\n    except Exception as ex:   # the dashboard is never stopped by the desk\n        res["error"] = "%s: %s" % (type(ex).__name__, str(ex)[:300])',
     '                "engines": dict(cv.get("engines") or {}), "spent": float(cv.get("spent") or 0.0),\n                "next": td.next_step(st, prow, cv, int(n.get("mula") or 0)),\n                "at": td.row_at(prow, chart["at"]),   # DESK_FRESH_2026_11_11: the row\'s own chart time\n                "guard": td.guard(prow, rg, td.row_at(prow, chart["at"]))})\n    except Exception as ex:   # the dashboard is never stopped by the desk\n        res["error"] = "%s: %s" % (type(ex).__name__, str(ex)[:300])')

edit('scripts/dashboard.py', 8, '        import translation_desk as td\n        chart = td.load_path(PATH_FILE)\n        return td.guard(chart["texts"].get(doc), _source_verdicts(pathlib.Path(DESK_DB).parent).get(doc), chart["at"])\n    except Exception:\n        return None',
     '        import translation_desk as td\n        chart = td.load_path(PATH_FILE)\n        return td.guard(chart["texts"].get(doc), _source_verdicts(pathlib.Path(DESK_DB).parent).get(doc),\n                        td.row_at(chart["texts"].get(doc), chart["at"]))   # DESK_FRESH_2026_11_11\n    except Exception:\n        return None')

edit('scripts/dashboard.py', 9, "    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); btn.disabled = false; return; }\n    _dkWatch(d.job, function(j){ o.textContent = j.ok ? 'charted: the page reads it again' : 'it did not finish (the History has why)'; if (j.ok) setTimeout(function(){ location.reload(); }, 1500); }, null);\n  }catch(e){ o.textContent = 'Request failed: ' + e; btn.disabled = false; }\n}",
     "    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); btn.disabled = false; return; }\n    _dkWatch(d.job, function(j){ o.textContent = j.ok ? 'charted: the page reads it again' : 'it did not finish (the History has why)'; if (j.ok) setTimeout(function(){ location.reload(); }, 1500); }, null);\n  }catch(e){ o.textContent = 'Request failed: ' + e; btn.disabled = false; }\n}\nasync function deskChartOne(doc, btn){   /* DESK_FRESH_2026_11_11: this text's path charted again, free */\n  btn.disabled = true; var o = document.getElementById('chartone'); o.textContent = 'charting this text...';\n  try{\n    var r = await fetch('/api/repair', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({step: 'path_doc', doc: doc})});\n    var d = await r.json();\n    if (!d.job){ o.textContent = 'Could not start: ' + (d.error || 'unknown'); btn.disabled = false; return; }\n    _dkWatch(d.job, function(j){\n      var out = String(j.out || '') + _DK_NL + String(j.err || ''), v = _dkLine(out, 'VERDICT: ');\n      o.textContent = j.ok ? ('charted: ' + (v || 'the page reads it again')) : ('it did not finish: ' + (v || 'the History has why'));\n      if (j.ok) setTimeout(function(){ location.reload(); }, 2500); else btn.disabled = false;\n    }, null);\n  }catch(e){ o.textContent = 'Request failed: ' + e; btn.disabled = false; }\n}")

edit('scripts/dashboard.py', 10, '                 (\'<span class="chip c-source">%s: %s</span>\' % (e(held.replace("_", " ")), e(r.get("held_reason") or "")))\n                 if held in td.HOLDS or held == "in_repair" else "", e(r["doc"]),\n                 (" (charted %s)" % e(str(s.get("chart_at") or "")[:10])) if s.get("chart_at") else "",\n                 e(td.PATH_LABEL.get(r["path"] or "", r["path"] or "not charted")), e(r["why"]), e(r["next"])))\n    if r["path"] and r["next_path"]:\n        h.append(\'<p class="small">The path\\\'s steps: %s. <a href="/repair/%s">The repair page</a> &middot; \'',
     '                 (\'<span class="chip c-source">%s: %s</span>\' % (e(held.replace("_", " ")), e(r.get("held_reason") or "")))\n                 if held in td.HOLDS or held == "in_repair" else "", e(r["doc"]),\n                 (" (charted %s)" % e(str(r.get("at") or "")[:16].replace("T", " "))) if r.get("at") else "",   # DESK_FRESH_2026_11_11\n                 e(td.PATH_LABEL.get(r["path"] or "", r["path"] or "not charted")), e(r["why"]), e(r["next"])))\n    try:   # DESK_FRESH_2026_11_11: what changed the text since its path was charted, and its own chart again\n        _chg = td.changed_since(r["doc"], r.get("at") or "", pathlib.Path(DESK_DB).parent)\n    except Exception:\n        _chg = []\n    h.append(\'<p class="%s" id="dkfresh">%s <button class="btn dkbtn" onclick="deskChartOne(\\\'%s\\\', this)">Chart this text \'\n             \'again (free)</button> <span class="small" id="chartone"></span></p>\' % (\n                 "warn" if _chg else "small",\n                 e("Changed since its path was charted (%s): %s. The path above is of before: chart this text again "\n                   "(free, a minute; the database is read, not changed), and the page reads it again." % (\n                       str(r.get("at") or "")[:16].replace("T", " "), "; ".join("%s %s" % (w, t) for w, t in _chg)))\n                 if _chg else e("Nothing has changed this text since its path was charted."), e(r["doc"], quote=True)))\n    if r["path"] and r["next_path"]:\n        h.append(\'<p class="small">The path\\\'s steps: %s. <a href="/repair/%s">The repair page</a> &middot; \'')

edit('scripts/dashboard.py', 11, '        if td.stage_of(prow, cover, reg) == "source":\n            return jsonify({"error": "its path says the reading comes first (%s): %s" % (\n                td.PATH_LABEL.get((prow or {}).get("path") or "", ""), td.guard(prow, reg, chart["at"])["say"]\n                if td.guard(prow, reg, chart["at"]) else "")}), 409\n    argv, why = td.scholar_argv(doc, step, data.get("pages") or "", data.get("limit") or td.STEP_VERSES,\n                                data.get("max_usd") or 0, reg.get("status") == "in_repair",',
     '        if td.stage_of(prow, cover, reg) == "source":\n            return jsonify({"error": "its path says the reading comes first (%s): %s" % (\n                td.PATH_LABEL.get((prow or {}).get("path") or "", ""), td.guard(prow, reg, td.row_at(prow, chart["at"]))["say"]\n                if td.guard(prow, reg, td.row_at(prow, chart["at"])) else "")}), 409   # DESK_FRESH_2026_11_11\n    argv, why = td.scholar_argv(doc, step, data.get("pages") or "", data.get("limit") or td.STEP_VERSES,\n                                data.get("max_usd") or 0, reg.get("status") == "in_repair",')

edit('scripts/dashboard.py', 12, '        if _p and _td is not None:   # TRANSLATION_DESK_2026_10_17\n            x["path"] = {"path": _p.get("path"), "label": _td.PATH_LABEL.get(_p.get("path"), _p.get("path")),\n                         "next": str((list(_p.get("next") or []) or [""])[0])[:300], "at": _chart["at"][:10],\n                         "held": bool(_td.guard(_p, reg.get(r.get("doc")), _chart["at"]))}\n        g = reg.get(r.get("doc"))\n        if g:',
     '        if _p and _td is not None:   # TRANSLATION_DESK_2026_10_17\n            x["path"] = {"path": _p.get("path"), "label": _td.PATH_LABEL.get(_p.get("path"), _p.get("path")),\n                         "next": str((list(_p.get("next") or []) or [""])[0])[:300],\n                         "at": _td.row_at(_p, _chart["at"])[:10],   # DESK_FRESH_2026_11_11\n                         "held": bool(_td.guard(_p, reg.get(r.get("doc")), _td.row_at(_p, _chart["at"])))}\n        g = reg.get(r.get("doc"))\n        if g:')

edit('scripts/dashboard.py', 13, '    try:\n        import claude_engine as _ce\n        c = _ce.credit(con)\n        d["credit"] = {"cap": c["cap"], "spent": round(c["spent"], 4), "left": round(max(0.0, c["left"]), 4),',
     '    try:\n        import claude_engine as _ce\n        _credit_env_fresh()   # DESK_FRESH_2026_11_11\n        c = _ce.credit(con)\n        d["credit"] = {"cap": c["cap"], "spent": round(c["spent"], 4), "left": round(max(0.0, c["left"]), 4),')

edit('scripts/text_path.py', 1, '  python scripts\\\\text_path.py --doc nirukta         one text, with every fact\n  python scripts\\\\text_path.py --html exports\\\\text_path.html\n"""\nfrom __future__ import annotations',
     '  python scripts\\\\text_path.py --doc nirukta         one text, with every fact\n  python scripts\\\\text_path.py --html exports\\\\text_path.html\n\nDESK_FRESH_2026_11_11: --doc X --write charts one text again and puts its row into data/text_path.json (the others as\nthey were), with the row\'s own time ("at"): the desk (/desk/<doc>) reads a text\'s path from that chart, and after a\nrepair or a new reading the chart of a fortnight before kept saying "vision has read 0 of its 507 pages". A text whose\npath was "retire" (a duplicate: that needs every text) is charted again only by the whole chart.\n\n  python scripts\\\\text_path.py --doc gandharva_veda_natya_shastra --write\n"""\nfrom __future__ import annotations')

edit('scripts/text_path.py', 2, '    live = [c for c in dbf["codes"] if not c.endswith("-RETIRED")]\n    retired = [c for c in dbf["codes"] if c.endswith("-RETIRED")]\n    only = [a.only] if a.only else live\n    facts = {}\n    for i, code in enumerate(only, 1):',
     '    live = [c for c in dbf["codes"] if not c.endswith("-RETIRED")]\n    retired = [c for c in dbf["codes"] if c.endswith("-RETIRED")]\n    only = ([a.only] + [c for c in live if c.startswith(a.only + "__w_")]) if a.only else live   # DESK_FRESH_2026_11_11: its witnesses too\n    facts = {}\n    for i, code in enumerate(only, 1):')

edit('scripts/text_path.py', 3, '                          "next": [], "also": [], "cost": 0.0, "then": 0.0, "facts": {"doc": c}, "retired": True})\n    texts.sort(key=lambda t: (ORDER.get(t["path"], 99), -(t.get("cost") or 0), t["doc"]))\n    totals = {}\n    for t in texts:\n        if t.get("retired"):\n            continue\n        x = totals.setdefault(t["path"], {"texts": 0, "cost": 0.0, "cost_hi": 0.0, "cost_lo": 0.0, "then": 0.0})\n        x["texts"] += 1; x["cost"] += t.get("cost") or 0.0; x["then"] += t.get("then") or 0.0\n        x["cost_hi"] += t.get("cost_hi") or t.get("cost") or 0.0\n        x["cost_lo"] += t["cost_lo"] if t.get("cost_lo") is not None else (t.get("cost") or 0.0)\n    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices": pr, "texts": texts,\n            "totals": totals, "paths": [list(p) for p in PATHS]}',
     '                          "next": [], "also": [], "cost": 0.0, "then": 0.0, "facts": {"doc": c}, "retired": True})\n    texts.sort(key=lambda t: (ORDER.get(t["path"], 99), -(t.get("cost") or 0), t["doc"]))\n    totals = totals_of(texts)\n    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices": pr, "texts": texts,\n            "totals": totals, "paths": [list(p) for p in PATHS]}')

edit('scripts/text_path.py', 4, '\n\ndef main(argv=None) -> int:\n    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)',
     '\n\ndef totals_of(texts: list) -> dict:\n    """{path: {"texts", "cost", "cost_hi", "cost_lo", "then"}} of the texts not retired."""\n    totals = {}\n    for t in texts:\n        if t.get("retired"):\n            continue\n        x = totals.setdefault(t["path"], {"texts": 0, "cost": 0.0, "cost_hi": 0.0, "cost_lo": 0.0, "then": 0.0})\n        x["texts"] += 1; x["cost"] += t.get("cost") or 0.0; x["then"] += t.get("then") or 0.0\n        x["cost_hi"] += t.get("cost_hi") or t.get("cost") or 0.0\n        x["cost_lo"] += t["cost_lo"] if t.get("cost_lo") is not None else (t.get("cost") or 0.0)\n    return totals\n\n\ndef merge_row(path: Path, row) -> dict:\n    """DESK_FRESH_2026_11_11: the chart at path with one text\'s row put in (its place kept, or added; the others and the\n    chart\'s own time as they were); written atomically. row None: only read. Returns {"at", "rows": {doc: row}}."""\n    try:\n        d = json.loads(path.read_text(encoding="utf-8"))\n    except (OSError, ValueError):\n        d = {}\n    if not isinstance(d, dict):\n        d = {}\n    texts = [t for t in (d.get("texts") or []) if isinstance(t, dict)]\n    if row is not None:\n        for i, t in enumerate(texts):\n            if t.get("doc") == row.get("doc"):\n                texts[i] = row\n                break\n        else:\n            texts.append(row)\n        texts.sort(key=lambda t: (ORDER.get(t.get("path"), 99), -(t.get("cost") or 0), str(t.get("doc") or "")))\n        d["texts"] = texts\n        d["totals"] = totals_of([t for t in texts if t.get("path")])\n        d.setdefault("at", row.get("at"))\n        d.setdefault("mark", MARK)\n        path.parent.mkdir(parents=True, exist_ok=True)\n        tmp = path.with_suffix(".tmp")\n        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")\n        os.replace(tmp, path)\n    return {"at": str(d.get("at") or ""), "rows": {t.get("doc"): t for t in texts if t.get("doc")}}\n\n\ndef main(argv=None) -> int:\n    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)')

edit('scripts/text_path.py', 5, '    ap.add_argument("--progress", action="store_true")\n    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)\n    a = ap.parse_args(argv)\n    if not Path(a.db).exists():',
     '    ap.add_argument("--progress", action="store_true")\n    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)\n    ap.add_argument("--write", action="store_true",   # DESK_FRESH_2026_11_11\n                    help="with --doc: put this text\'s row into the chart (data/text_path.json), the others as they were")\n    a = ap.parse_args(argv)\n    if not Path(a.db).exists():')

edit('scripts/text_path.py', 6, '    if a.from_dashboard:\n        a.progress = True\n    res = chart(a)\n    show(res, bool(a.only))\n    if not a.only:\n        p = Path(a.out)',
     '    if a.from_dashboard:\n        a.progress = True\n    if a.only and a.write:   # DESK_FRESH_2026_11_11: refused before the work when the text\'s path needs every text\n        old = merge_row(Path(a.out), None)\n        prev = (old.get("rows") or {}).get(a.only) or {}\n        if prev.get("path") == "retire":\n            print("VERDICT: %s\'s path is retire (a duplicate of another text): only the whole chart decides it; nothing "\n                  "written" % a.only)\n            print("NEXT: python scripts\\\\text_path.py   (every text, free)")\n            return 1\n    res = chart(a)\n    show(res, bool(a.only))\n    if a.only and a.write:\n        row = next((t for t in res["texts"] if t.get("doc") == a.only), None)\n        if row is None:\n            print("VERDICT: %s was not charted (not in the database?): nothing written" % a.only)\n            print("NEXT: python scripts\\\\text_path.py --doc %s" % a.only)\n            return 1\n        got = merge_row(Path(a.out), dict(row, at=res["at"]))\n        print("  wrote %s (%s charted again at %s; the chart of the others is of %s)" % (a.out, a.only, res["at"],\n                                                                                   got.get("at") or "-"))\n        print("VERDICT: %s: %s (%s)" % (a.only, row.get("path"), str(row.get("why") or "")[:200]))\n        print("NEXT: " + ((row.get("next") or [""])[0] or "-"))\n        return 0\n    if not a.only:\n        p = Path(a.out)')

edit('scripts/translation_desk.py', 1, '            holds it withdrawn or set aside)\n  uncharted the path has not charted it (chart the path again: python scripts\\\\text_path.py, free)\n"""\nfrom __future__ import annotations',
     '            holds it withdrawn or set aside)\n  uncharted the path has not charted it (chart the path again: python scripts\\\\text_path.py, free)\n\nDESK_FRESH_2026_11_11: a text\'s own chart time (text_path.py --doc X --write puts one row in with its "at"), and what\nchanged since it (changed_since: the OCR consensus, the merged pages, the register), so that the desk says when the\npath it shows is older than the text: on 11 Nov the Gandharva Veda\'s desk still said "vision has read 0 of its 507\npages" a day after vision had read 506.\n"""\nfrom __future__ import annotations')

edit('scripts/translation_desk.py', 2, '    except (OSError, ValueError, TypeError, KeyError, AttributeError):\n        return {"at": "", "texts": {}}\n\n',
     '    except (OSError, ValueError, TypeError, KeyError, AttributeError):\n        return {"at": "", "texts": {}}\n\n\ndef _ts(at: str):\n    try:\n        return time.mktime(time.strptime(str(at)[:19], "%Y-%m-%dT%H:%M:%S"))\n    except (ValueError, TypeError):\n        return None\n\n\ndef row_at(prow, chart_at: str = "") -> str:\n    """DESK_FRESH_2026_11_11: when this text was charted: its own row\'s time, else the chart\'s."""\n    return str((prow or {}).get("at") or chart_at or "")\n\n\ndef changed_since(doc: str, at: str, data) -> list:\n    """DESK_FRESH_2026_11_11: [(what, when)] that changed the text after its chart (at), in the data folder (beside the\n    database): the OCR consensus written (ocr_consensus/<doc>.json), pages merged (raw_merged/<doc>_NNNN.jsonl), the\n    register (source_verdicts.jsonl). Read-only; [] when the chart\'s time cannot be read."""\n    t0 = _ts(at)\n    if t0 is None or not doc:\n        return []\n    data = Path(data)\n    out = []\n\n    def when(ts):\n        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))\n    try:\n        m = (data / "ocr_consensus" / ("%s.json" % doc)).stat().st_mtime\n        if m > t0 + 60:\n            out.append(("the OCR consensus (vision) written", when(m)))\n    except OSError:\n        pass\n    try:\n        newest = 0.0\n        for p in (data / "raw_merged").glob("%s_*.jsonl" % doc):\n            if re.match(r"^%s_\\d{4}\\.jsonl$" % re.escape(doc), p.name):\n                newest = max(newest, p.stat().st_mtime)\n        if newest > t0 + 60:\n            out.append(("its merged pages written", when(newest)))\n    except OSError:\n        pass\n    try:\n        last = None\n        for line in (data / "source_verdicts.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():\n            try:\n                r = json.loads(line)\n            except ValueError:\n                continue\n            if isinstance(r, dict) and r.get("doc") == doc:\n                last = r\n        lt = _ts((last or {}).get("at") or "")\n        if last and lt is not None and lt > t0 + 60:\n            out.append(("the register: %s" % (last.get("status") or "?"), str(last.get("at"))[:16].replace("T", " ")))\n    except OSError:\n        pass\n    return out\n\n')

edit('scripts/claude_engine.py', 1, '\n\ndef credit(con, today=None) -> dict:\n    """{cap, spent, left, since, expires, expired, calls}: the usage_log rows of engine anthropic:% from since."""',
     '\n\nCREDIT_KEYS = ("SA_CLAUDE_CREDIT_USD", "SA_CLAUDE_CREDIT_SINCE", "SA_CLAUDE_CREDIT_EXPIRES")\n\n\ndef dotenv_credit(path) -> dict:\n    """DESK_FRESH_2026_11_11: the credit\'s three settings as the .env file at path has them now ({} when it has none);\n    only those keys are read, nothing else of the file. A process started before .env changed (the dashboard, on 11 Nov\n    showing "$0.00 left, it expires 2026-11-11", the defaults) puts them in its environment with this."""\n    out = {}\n    try:\n        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():\n            s = line.strip()\n            if s.startswith("export "):\n                s = s[7:].lstrip()\n            k, sep, v = s.partition("=")\n            k = k.strip()\n            if sep and k in CREDIT_KEYS:\n                v = v.split(" #", 1)[0].strip().strip(\'"\').strip("\'")\n                if v:\n                    out[k] = v\n    except OSError:\n        pass\n    return out\n\n\ndef credit(con, today=None) -> dict:\n    """{cap, spent, left, since, expires, expired, calls}: the usage_log rows of engine anthropic:% from since."""')

edit('tests/test_claude_engine_2026_10_15.py', 1, '            con = usage_db(Path(d)); con.close()\n            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}\n            r = subprocess.run([sys.executable, str(SCRIPTS / "claude_engine.py"), "--db", str(Path(d) / "u.db"), "--credit"],\n                               capture_output=True, text=True, env=env, cwd=d)',
     '            con = usage_db(Path(d)); con.close()\n            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}\n            env["SA_CLAUDE_CREDIT_EXPIRES"] = "2099-12-31"   # DESK_FRESH_2026_11_11: the default\'s last day (2026-11-11) is past\n            r = subprocess.run([sys.executable, str(SCRIPTS / "claude_engine.py"), "--db", str(Path(d) / "u.db"), "--credit"],\n                               capture_output=True, text=True, env=env, cwd=d)')

edit('tests/test_claude_engine_2026_10_15.py', 2, '            DUEL.make_judge = lambda eng, a, meta: judges.setdefault(eng, StubJudge())\n            os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-a-key")\n            try:\n                cwd = os.getcwd(); os.chdir(d)',
     '            DUEL.make_judge = lambda eng, a, meta: judges.setdefault(eng, StubJudge())\n            os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-a-key")\n            exp = os.environ.get("SA_CLAUDE_CREDIT_EXPIRES")   # DESK_FRESH_2026_11_11: the default\'s last day is past\n            os.environ["SA_CLAUDE_CREDIT_EXPIRES"] = "2099-12-31"\n            try:\n                cwd = os.getcwd(); os.chdir(d)')

edit('tests/test_claude_engine_2026_10_15.py', 3, '            finally:\n                DUEL.make_judge = keep\n\n',
     '            finally:\n                DUEL.make_judge = keep\n                if exp is None:\n                    os.environ.pop("SA_CLAUDE_CREDIT_EXPIRES", None)\n                else:\n                    os.environ["SA_CLAUDE_CREDIT_EXPIRES"] = exp\n\n')

edit('tests/test_tier_r_2026_10_17.py', 1, '            for f in self.FILES:\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after\n                         or sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*")))   # UI_CLARITY_2026_10_22\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            for f in self.FILES:\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_navmenus_*"))   # NAV_MENUS_2026_10_18 came after\n                         or sorted((REPO / f).parent.glob(Path(f).name + ".bak_uiclarity_*"))   # UI_CLARITY_2026_10_22\n                         or sorted((REPO / f).parent.glob(Path(f).name + ".bak_deskfresh_*")))   # DESK_FRESH_2026_11_11\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_redeem_2026_10_14.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = sorted(SCRIPTS.glob(f + ".bak_scholar_*"))   # SCHOLAR_2026_10_14 came after (dashboard.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                later = (sorted(SCRIPTS.glob(f + ".bak_scholar_*"))   # SCHOLAR_2026_10_14 came after (dashboard.py)\n                         or sorted(SCRIPTS.glob(f + ".bak_deskfresh_*")))   # DESK_FRESH_2026_11_11 (text_path.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

