#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_judge_desk_2026_10_11.py  (2026-10-11)  JUDGE_DESK_2026_10_11

The debris judged, shown where it is needed, and every text that needs a better source in one place.
Asked again on 11 Oct: "we need an expert opinion from you, and displayed, whether the debris and the
remaining % of the text is having a material effect on the actual text being ingested and translated";
"a built-in browser that uses AI to source the best critical or near-critical text".

  scripts/repair_text.py (delivered beside this patcher) caches each assessment in
    data/source_judged/<doc>.json; --judge-all judges every text with something untranslated or a state;
    --release refuses while the translation is not back (as on 11 Oct, 19:47), unless --force.
  scripts/dashboard.py (on a restart):
    the Library's cards: "Debris judged MATERIAL (date): misread letters in 50% of verses; vision 0.78",
      coloured by level, under the notes of a text the scan stopped, or with a state;
    /sources, "Sources & repairs": every text held by the guard, stuck below the OCR bar, judged moderate
      or material, or in the register; its state, the debris judged, what is next, the best edition the
      Source desk found, and Find a better source; "Judge the texts again" (repair_text.py --judge-all);
    the repair page shows the same line; the Library's header links to /sources.
  scripts/dashboard_static.html (on a reload): the header links to Sources & repairs.

Needs REPAIR_HEAL_2026_10_11 in both files. Anchored, all-or-nothing, marker-idempotent per file; keeps
line endings; the .py is compiled before it replaces the original; backups .bak_judgedesk_<date>.
  python scripts\\patch_judge_desk_2026_10_11.py --check
  python scripts\\patch_judge_desk_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "JUDGE_DESK_2026_10_11"
NEEDS = "REPAIR_HEAL_2026_10_11"

E = []   # (file, name, old, new)
def edit(f, name, old, new):
    E.append((f, name, old, new))

D = "scripts/dashboard.py"
edit(D, "a step that judges every text",
     '''_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore", "as_is", "accept", "hold", "release",
                 "find", "fetch")
''',
     '''_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore", "as_is", "accept", "hold", "release",
                 "find", "fetch", "judge_all")   # JUDGE_DESK_2026_10_11: judge_all
''')
edit(D, "the step's words",
     "fetch: 'fetching...', translate: 'translating...'};",
     "fetch: 'fetching...', translate: 'translating...',\n                 judge_all: 'judging the texts (about a minute)...'};")
edit(D, "reload after judging",
     "/^(set_aside|restore|use|as_is|accept|hold|release|translate)$/.test(step)",
     "/^(set_aside|restore|use|as_is|accept|hold|release|translate|judge_all)$/.test(step)")
edit(D, "the card takes the judgement",
     "def _repair_html(code: str, acts_html: str, shown: list, rec) -> str:\n",
     "def _repair_html(code: str, acts_html: str, shown: list, rec, jd=None) -> str:   # JUDGE_DESK_2026_10_11: jd\n")
edit(D, "a set-aside card says why it was judged so",
     '''                % (at, why or "needs a better scan", _repair_bar(code, "aside")))
''',
     '''                % (at, why or "needs a better scan", _judged_note(jd, (), st) + _repair_bar(code, "aside")))
''')
edit(D, "the judgement under the notes",
     '''    kinds = {n.get("kind") for n in shown}
    if st == "in_repair":
        acts_html += _repair_bar(code, "in_repair")
''',
     '''    kinds = {n.get("kind") for n in shown}
    acts_html += _judged_note(jd, kinds, st)   # JUDGE_DESK_2026_10_11
    if st == "in_repair":
        acts_html += _repair_bar(code, "in_repair")
''')
edit(D, "the texts not yet readable take it too",
     "def _repair_waiting(rows, cats, notes, aside) -> str:\n",
     "def _repair_waiting(rows, cats, notes, aside, judged=None) -> str:   # JUDGE_DESK_2026_10_11: judged\n")
edit(D, "and pass it on",
     "        inner = _repair_html(code, acts, list(notes.get(code, [])), aside.get(code))\n",
     "        inner = _repair_html(code, acts, list(notes.get(code, [])), aside.get(code), (judged or {}).get(code))\n")
edit(D, "judge_all needs no text",
     '''    data = request.get_json(silent=True) or {}
    doc = _validate_doc(data.get("doc"))
    step = str(data.get("step") or "assess")
    if not doc:
''',
     '''    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step == "judge_all" else _validate_doc(data.get("doc"))   # JUDGE_DESK_2026_10_11
    if not doc:
''')
edit(D, "judge_all runs repair_text.py --judge-all",
     '''    kind = "repair_use" if step == "use" else "repair"
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})
''',
     '''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    kind = "repair_use" if step == "use" else "repair"
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})
''')
edit(D, "the repair page shows the judgement",
     '''    st = (rec or {}).get("status")
    if st == "set_aside":
        notes = _repair_html(doc, "", shown, rec)
        bar = ""
    else:
        notes = _repair_html(doc, "", shown, rec)
        bar = "" if 'class="repairbar"' in notes else _repair_bar(doc, "standard")
    page = (_REPAIR_PAGE.replace("__REPAIR_CSS__", _REPAIR_CSS)
''',
     '''    st = (rec or {}).get("status")
    jd = _judged(pathlib.Path(db_path).parent).get(doc)   # JUDGE_DESK_2026_10_11
    if st == "set_aside":
        notes = _repair_html(doc, "", shown, rec, jd)
        bar = ""
    else:
        notes = _repair_html(doc, "", shown, rec, jd)
        bar = "" if 'class="repairbar"' in notes else _repair_bar(doc, "standard")
    page = (_REPAIR_PAGE.replace("__REPAIR_CSS__", _REPAIR_CSS + _JUDGED_CSS)
''')
edit(D, "the Library reads the judgements",
     "    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside\n",
     "    aside = _source_verdicts(pathlib.Path(db_path).parent)   # REPAIR_PATH_2026_10_10: the texts set aside\n"
     "    judged = _judged(pathlib.Path(db_path).parent)   # JUDGE_DESK_2026_10_11: the last assessments\n")
edit(D, "the Library's cards take them",
     "            acts_html = _repair_html(code, acts_html, _shown, aside.get(code))\n",
     "            acts_html = _repair_html(code, acts_html, _shown, aside.get(code), judged.get(code))\n")
edit(D, "and the texts not yet readable",
     "    body += _repair_waiting(rows, cats, notes, aside)   # REPAIR_PATH_2026_10_10: no English yet, held by its scan\n",
     "    body += _repair_waiting(rows, cats, notes, aside, judged)   # REPAIR_PATH_2026_10_10: no English yet, held by its scan\n")
edit(D, "the Library's css",
     "{_REPAIR_CSS}\n",
     "{_REPAIR_CSS}\n{_JUDGED_CSS}\n")
edit(D, "the Library links to /sources",
     '''  <a class="back" href="/methodology" title="How source and translation quality are measured" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
''',
     '''  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
''')
edit(D, "/sources",
     '@app.get("/repair/<doc>")\n',
     None)   # filled below with the block
S = "scripts/dashboard_static.html"
edit(S, "the header links to /sources",
     '''    <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>
''',
     '''    <a class="btn-refresh" href="/library" target="_blank" style="text-decoration:none;margin-right:6px" title="Browse & read translated texts">&#128218; Library</a>
    <a class="btn-refresh" href="/sources" target="_blank" style="text-decoration:none;margin-right:6px" title="JUDGE_DESK_2026_10_11: the texts whose scan stops their translation, the debris judged, the editions found">&#128269; Sources</a>
''')

BLOCK = r'''# JUDGE_DESK_2026_10_11 -----------------------------------------------------------------------
# The debris judged, shown where it is needed: on the Library's cards (from the last assessment, cached
# by repair_text.py in data/source_judged/<doc>.json) and on /sources, every text whose scan stops its
# translation in one place, with what it is, what is next, and the best edition the Source desk found.
_JUDGE_LEVELS = ("cosmetic", "moderate", "material")


def _judged(folder=None) -> Dict[str, dict]:
    """doc -> the last assessment repair_text.py cached (data/source_judged/<doc>.json, beside the
    database). Small files, read on each Library request; a missing folder is none."""
    d = pathlib.Path(folder if folder is not None else (ROOT / "data")) / "source_judged"
    out: Dict[str, dict] = {}
    try:
        for p in d.glob("*.json"):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get("doc"):
                out[str(r["doc"])] = r
    except OSError:
        return {}
    return out


def _judged_note(jd, kinds=(), st=None) -> str:
    """One line under a card: the debris judged, when the card says the scan stopped a run, the text has
    a state, or the debris is not cosmetic."""
    import html as _html
    if not jd or jd.get("level") not in _JUDGE_LEVELS or not jd.get("debris_pct"):
        return ""
    if not (set(kinds) & {"held", "quality", "nothing", "repaired"} or st or jd.get("level") != "cosmetic"):
        return ""
    bits = ["misread letters in %.0f%% of verses" % float(jd.get("misread_pct") or 0)]
    if jd.get("agree_pages"):
        bits.append("vision agreement %.2f" % float(jd.get("agree_median") or 0))
    if jd.get("furniture_pct"):
        bits.append("page furniture %.0f%%" % float(jd.get("furniture_pct") or 0))
    return ('<div class="cardnote judged" data-level="%s" title="%s">Debris judged %s (%s): %s.</div>'
            % (jd["level"], _html.escape(str(jd.get("judged") or "")), jd["level"].upper(),
               _html.escape(str(jd.get("at") or "?")[:10]), _html.escape("; ".join(bits))))


_SOURCES_CSS = r"""
.srcpage{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
.srcsum{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 16px}
.srcsum span{background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:4px 9px;font-size:12px}
.srcsum span[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.srcsum span[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.srcsum span[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.srcwrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px}
table.srct{width:100%;border-collapse:collapse;font-size:12px;min-width:860px}
table.srct th{text-align:left;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border);background:var(--card)}
table.srct td{padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:top;line-height:1.45}
table.srct td a{color:var(--gold);text-decoration:none}
.lv{display:inline-block;border-radius:5px;padding:1px 7px;font-size:11px;border:1px solid var(--border)}
.lv[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.lv[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.lv[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
.muted{color:var(--muted)}"""
_JUDGED_CSS = r"""
.cardnote.judged[data-level=material]{color:#e8a3a3;border-left-color:#7a3a3a}
.cardnote.judged[data-level=moderate]{color:#e6c27a;border-left-color:#6b5420}
.cardnote.judged[data-level=cosmetic]{color:#9fd8b5;border-left-color:#2f6b4a}"""


@app.get("/sources")
def sources_page():
    """Every text whose scan stops its translation, in one place: the debris judged (cached by
    repair_text.py), its state, what is next, and the best edition the Source desk found. Reads small
    files only (never the database); "Judge the texts again" runs repair_text.py --judge-all."""
    import html as _html
    db_path = request.args.get("db", "data/context.db")
    folder = pathlib.Path(db_path).parent
    jd = _judged(folder)
    reg = _source_verdicts(folder)
    rows = []
    for code in sorted(set(jd) | set(reg)):
        j, r = jd.get(code) or {}, reg.get(code) or {}
        keep = (r or j.get("held") or j.get("guard") or j.get("quality_stuck")
                or (j.get("level") in ("moderate", "material") and j.get("debris_pct")))
        if keep:
            rows.append((code, j, r))
    order = {"material": 0, "moderate": 1, "cosmetic": 2}
    rows.sort(key=lambda x: (0 if x[1].get("held") else 1, order.get(x[1].get("level"), 3), x[0]))
    counts = {}
    for _c, j, _r in rows:
        lv = j.get("level") if j.get("debris_pct") else None
        counts[lv] = counts.get(lv, 0) + 1
    last = max([str(j.get("at") or "") for j in jd.values()] or [""])
    e = _html.escape
    trs = ""
    for code, j, r in rows:
        c = e(code, quote=True)
        st = r.get("status") or j.get("state") or ""
        lv = j.get("level") if j.get("debris_pct") else ""
        judged = ""
        if lv:
            judged = ('<span class="lv" data-level="%s">%s</span><br><span class="muted">misread %.0f%% of verses%s</span>'
                      % (lv, lv, float(j.get("misread_pct") or 0),
                         ("; vision %.2f" % float(j.get("agree_median"))) if j.get("agree_pages") else ""))
        elif j:
            judged = '<span class="muted">no debris</span>'
        best = ""
        try:
            sd = json.loads((SOURCE_DESK_DIR / ("%s.json" % code)).read_text(encoding="utf-8"))
            b = next((x for x in sd.get("candidates") or [] if not x.get("current_scan")), None)
            if b:
                best = ('<a href="%s" target="_blank" rel="noopener">%s</a><br><span class="muted">score %.0f; %s</span>'
                        % (e(b.get("details_url") or "#"), e((b.get("title") or b.get("identifier") or "")[:80]),
                           float(b.get("score") or 0), e("; ".join((b.get("why") or [])[:2]))))
            else:
                best = '<span class="muted">searched: nothing better on archive.org</span>'
        except (OSError, ValueError):
            best = '<span class="muted">not searched</span>'
        nxt = str(j.get("next") or "")
        nxt_label = ""
        for key, label in (("--use-repaired", "use the repaired text"), ("--as-is", "translate as is"),
                           ("--accept", "accept as complete"), ("--set-aside", "set aside"), ("--restore", "restore"),
                           ("--release", "publish"), ("--find-source", "find a better source"), ("--repair", "repair the scan"),
                           ("Finish EN", "translate it")):
            if key in nxt:
                nxt_label = label
                break
        trs += ('<tr><td><a href="/repair/%s">%s</a><br><span class="muted">EN %s/%s &middot; HI %s</span></td>'
                '<td>%s</td><td>%s</td><td>%s%s</td><td>%s</td>'
                '<td><div class="repairbar" id="rp-%s"><button class="tr-rest rp" data-doc="%s" '
                'onclick="repairStep(this.dataset.doc,&#39;find&#39;,this)">Find a better source</button>'
                '<div class="rpout"></div></div></td></tr>'
                % (c, e(code), j.get("english", "?"), j.get("passages", "?"), j.get("hindi", "?"),
                   e(st.replace("_", " ")) or ('<span class="muted">held by the guard</span>' if j.get("held") else ""),
                   judged, ("<b>%s</b><br>" % e(nxt_label)) if nxt_label else "", e(str(j.get("verdict") or "")[:220]),
                   best, c, c))
    summary = "".join('<span data-level="%s">%d %s</span>' % (k or "none", v, k or "without debris")
                      for k, v in sorted(counts.items(), key=lambda x: order.get(x[0], 3)))
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Every text whose scan stops its translation: what '
            'its debris is and whether it touches the text, its state, what is next, and the best edition the Source desk '
            'found. Judged last: %s. Open a text for its repair path, the debris in full and the Source desk.</p>'
            '<div class="srcsum">%s</div>'
            '<div class="repairbar" id="rp-corpus"><button class="tr-rest rp" data-doc="corpus" onclick="repairStep('
            'this.dataset.doc,&#39;judge_all&#39;,this)">Judge the texts again (free, about a minute)</button>'
            '<div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>State</th>'
            '<th>Debris, judged</th><th>Next</th><th>Best edition found</th><th></th></tr></thead><tbody>%s</tbody>'
            '</table></div>%s</div>'
            % (e(last[:16].replace("T", " ")) or "never: press Judge the texts again", summary, trs,
               "" if rows else '<p class="srcnone">Nothing judged yet. Press Judge the texts again.</p>'))
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sources &amp; repairs</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.srcnone{color:var(--muted);font-size:12px;margin:10px 0}
""" + _REPAIR_CSS + _SOURCES_CSS + _JUDGED_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><h1>Sources &amp; repairs</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


'''

E = [(f, n, o, (BLOCK + '@app.get("/repair/<doc>")\n') if new is None else new) for (f, n, o, new) in E]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    rt = Path("scripts/repair_text.py")
    if not rt.exists() or MARK.encode() not in rt.read_bytes():
        print("REFUSE: scripts\\repair_text.py with %s is not there (it comes with this patcher). Nothing written." % MARK)
        return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in (D, S):
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS not in src:
            problems.append("%s does not carry %s: apply scripts\\patch_repair_heal_2026_10_11.py first" % (rel, NEEDS)); continue
        out = src
        for f, name, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        if p.suffix == ".py":
            fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
            Path(tmp).write_bytes(data)
            try:
                py_compile.compile(tmp, doraise=True)
            except py_compile.PyCompileError as e:
                print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
            finally:
                os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_judgedesk_" + stamp))
        t = p.with_name(p.name + ".tmp_judgedesk"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Reload the dashboard page (Ctrl+F5). dashboard.py takes /sources and the cards' judgements when restarted,")
    print("only when idle: scripts\\restart_dashboard.ps1. Then: python scripts\\repair_text.py --judge-all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
