#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_library_booksmith.py  (2026-09-12)  BOOKSMITH_WIRING_2026_09_12

"i want to be able to select books from here (english and hindi
 translations), and then convert them into publishable PDFs as envisioned
 in booksmith, also wired here."

Booksmith was NOT wired here. `grep -ri booksmith` across this repository
returned nothing at all. What was true is better: somebody did it by hand
on 8 September and left the evidence.

  projects/harita-pancamam/source/source.html
    is byte-identical to
  exports/harita_pancamam_kalpa_sthanam_1-11_tri.html

Same for harita-prathama-sthanam and harita-tritiya-sthanam; checked by
sha256 before any of this was written. The classes export_html.py emits -
chapter, verse, vref, footnotes, sa, iast, en, hi - are exactly the ones
book.yaml's parser profile maps. And harita-pancamam went the whole way:
build/book.pdf, 22 pages, 11 units, a sha256 release identity.

So the seam is proven and the automation is missing. This adds the
automation and nothing else.

WHAT THIS TOUCHES
  1. three new API routes, inserted ahead of /api/queue/run
  2. a checkbox on each Library card
  3. a selection bar with a language chooser and a Build button
  4. per-card Download PDF / Open in Booksmith links, filled from state

WHAT IT DOES NOT TOUCH
  Any existing route, the reader, the translate buttons, or any book.yaml
  that a human wrote. Six of the seven existing projects are parked at
  Booksmith's review gate with an audit but no manifest; this does not
  push them through it. It builds the audit edition, which readiness.py
  explicitly permits, and links you into Booksmith for the reading one.

Run from the repo root:  python scripts/patch_library_booksmith.py
Add --check to verify anchors without writing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARK = "BOOKSMITH_WIRING_2026_09_12"
DASH = Path("scripts/dashboard.py")
ORCH = Path("scripts/booksmith_build.py")

# ---------------------------------------------------------------- 1. routes
ROUTES_ANCHOR = '@app.post("/api/queue/run")'
ROUTES_NEW = '''# ─────────────────────────────────────────────────────────────────────────
# BOOKSMITH_WIRING_2026_09_12
# Library selection -> Booksmith project -> PDF.
#
# Booksmith lives in its own tree with its own .venv (Python 3.13, native
# bits), so it cannot be imported into this process. Every step runs as a
# subprocess inside scripts/booksmith_build.py, launched through the same
# job runner as every other long task here, so it inherits the duplicate
# guard, the semaphore, /api/job/<id> and the history.
#
# 'booksmith' is not in the translate family, so launch() gives it the
# general semaphore - PDF builds do not write to context.db and must not
# serialise behind translation.
# ─────────────────────────────────────────────────────────────────────────
BOOKSMITH_ROOT = pathlib.Path(os.getenv(
    "BOOKSMITH_ROOT",
    r"D:\\Nartiang_Booksmith_v0.1.0_2026-08-29\\nartiang-booksmith"))
BOOKSMITH_UI = os.getenv("BOOKSMITH_UI", "http://127.0.0.1:8765")
BOOKSMITH_MODES = ("tri", "en", "hi")


def _bs_slug(doc: str) -> str:
    """Must agree with slug_for() in booksmith_build.py. Verified against the
    six projects created by hand: harita_caturtha_sthanam ->
    harita-caturtha-sthanam, and so on for all six."""
    s = re.sub(r"[^a-z0-9_-]+", "-", (doc or "").strip().lower().replace("_", "-"))
    return re.sub(r"-{2,}", "-", s).strip("-")[:64]


def _bs_pdf_path(doc: str):
    """The PDF for a doc, preferring the full audit build over the sampled
    layout proof. Returns (path, kind) or (None, None)."""
    project = BOOKSMITH_ROOT / "projects" / _bs_slug(doc)
    for name, kind in (("book.pdf", "book"), ("layout-proof.pdf", "proof")):
        p = project / "build" / name
        if p.exists():
            return p, kind
    return None, None


def _bs_state_one(doc: str) -> dict:
    slug = _bs_slug(doc)
    project = BOOKSMITH_ROOT / "projects" / slug
    state = {"doc": doc, "slug": slug,
             "project": project.exists() and (project / "book.yaml").exists(),
             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}
    side = ROOT / "exports" / "booksmith" / f"{doc}.json"
    if side.exists():
        try:
            state["last"] = json.loads(side.read_text(encoding="utf-8"))
        except Exception:
            pass
    pdf, kind = _bs_pdf_path(doc)
    if pdf:
        st = pdf.stat()
        state["pdf"] = {"kind": kind, "bytes": st.st_size,
                        "mtime": time.strftime("%Y-%m-%d %H:%M",
                                               time.localtime(st.st_mtime))}
    for j in list(JOBS.values()):
        if j.kind == "booksmith" and j.doc == doc and j.ok is None:
            state["job"] = j.id
            break
    return state


@app.get("/api/booksmith/state")
def api_booksmith_state():
    raw = (request.args.get("docs") or "").strip()
    docs = [d for d in (x.strip() for x in raw.split(",")) if d]
    if not docs:
        return jsonify({"error": "docs is required"}), 400
    if len(docs) > 200:
        return jsonify({"error": "too many docs"}), 400
    return jsonify({"root": str(BOOKSMITH_ROOT),
                    "installed": (BOOKSMITH_ROOT / ".venv" / "Scripts" / "booksmith.exe").exists(),
                    "states": [_bs_state_one(d) for d in docs]})


@app.post("/api/booksmith/build")
def api_booksmith_build():
    data = request.get_json(force=True) or {}
    docs = data.get("docs") or []
    if not isinstance(docs, list) or not docs:
        return jsonify({"error": "docs must be a non-empty list"}), 400
    if len(docs) > 40:
        return jsonify({"error": "select 40 texts or fewer per run"}), 400
    mode = (data.get("mode") or "tri").strip()
    if mode not in BOOKSMITH_MODES:
        return jsonify({"error": f"mode must be one of {BOOKSMITH_MODES}"}), 400
    product = (data.get("product") or "audit").strip()
    if product not in ("audit", "proof"):
        return jsonify({"error": "product must be audit or proof"}), 400
    exe = BOOKSMITH_ROOT / ".venv" / "Scripts" / "booksmith.exe"
    if not exe.exists():
        return jsonify({"error": f"Booksmith is not installed at {BOOKSMITH_ROOT}. "
                                 f"Run Launch_Booksmith.bat there once."}), 409

    db = data.get("db") or "data/context.db"
    started, rejected = [], []
    for raw in docs:
        doc = _validate_doc(raw)
        if not doc:
            rejected.append({"doc": str(raw)[:80], "why": "invalid doc code"})
            continue
        cmd = py(script("booksmith_build.py"), "--db", db, "--doc", doc,
                 "--mode", mode, "--product", product,
                 "--booksmith-root", str(BOOKSMITH_ROOT))
        started.append({"doc": doc, "job": launch("booksmith", doc, cmd)})
    return jsonify({"started": started, "rejected": rejected,
                    "mode": mode, "product": product})


@app.get("/api/booksmith/pdf/<doc>")
def api_booksmith_pdf(doc):
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    pdf, kind = _bs_pdf_path(doc)
    if not pdf:
        return jsonify({"error": "no PDF built yet for this text"}), 404
    # Read and return rather than send_file, so no new Flask import is needed
    # and the download is named after the text instead of book.pdf every time.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{doc}_{kind}") + ".pdf"
    resp = Response(pdf.read_bytes(), mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp


'''

# ------------------------------------------------------------- 2. checkbox
CARD_OLD = """            body += (
                f'<div class="card-wrap">'
                f'<a class="card" href="/reader/{code}">'"""
CARD_NEW = """            body += (
                f'<div class="card-wrap" data-doc="{_html.escape(code)}">'
                # BOOKSMITH_WIRING_2026_09_12 - the checkbox sits OUTSIDE the
                # <a>, or clicking it would navigate to the reader instead of
                # selecting the text.
                f'<label class="pick" title="Select this text for a PDF">'
                f'<input type="checkbox" class="pickbox" value="{_html.escape(code)}"/>'
                f'</label>'
                f'<a class="card" href="/reader/{code}">'"""

ACTS_OLD = """            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''"""
ACTS_NEW = """            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
            # Filled in by refreshBooksmith() once /api/booksmith/state answers.
            acts_html += f'<div class="bsacts" id="bs-{_html.escape(code)}"></div>'"""

# ------------------------------------------------------------------ 3. CSS
CSS_OLD = """.tr-rest:disabled{{opacity:.6;cursor:default}}
</style>"""
CSS_NEW = """.tr-rest:disabled{{opacity:.6;cursor:default}}
/* BOOKSMITH_WIRING_2026_09_12 */
.card-wrap{{position:relative}}
.pick{{position:absolute;top:8px;right:8px;z-index:3;cursor:pointer;padding:4px}}
.pickbox{{width:15px;height:15px;accent-color:var(--gold);cursor:pointer}}
.card-wrap.sel .card{{border-color:var(--gold);background:var(--card2)}}
.bsacts{{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}}
.bsacts a,.bsacts span{{font-family:'Inter',sans-serif;font-size:10px;font-weight:600;
  border-radius:7px;padding:4px 8px;text-decoration:none;border:1px solid var(--border)}}
.bsacts a.pdf{{color:var(--green);border-color:#23492f}}
.bsacts a.pdf:hover{{background:#12351f}}
.bsacts a.bsui{{color:var(--muted)}}
.bsacts a.bsui:hover{{color:var(--gold);border-color:var(--gold)}}
.bsacts span.warn{{color:#d98a8a;border-color:#3a1616}}
.bsacts span.busy{{color:var(--gold);border-color:#3a2f0f}}
#buildbar{{position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:40;
  display:none;align-items:center;gap:12px;background:var(--card2);
  border:1px solid var(--gold);border-radius:12px;padding:10px 16px;
  font-family:'Inter',sans-serif;font-size:12.5px;box-shadow:0 10px 30px #0009}}
#buildbar b{{color:var(--gold)}}
#buildbar select{{background:var(--card);color:var(--cream);border:1px solid var(--border);
  border-radius:7px;padding:5px 8px;font-family:'Inter',sans-serif;font-size:12px}}
#buildbar button{{background:var(--card);border:1px solid var(--border);color:var(--cream);
  border-radius:7px;padding:6px 12px;font-weight:600;cursor:pointer;font-size:12px}}
#buildbar button.go{{border-color:var(--gold);color:var(--gold)}}
#buildbar button:hover{{background:#000}}
#buildbar button:disabled{{opacity:.55;cursor:default}}
#buildbar .hint{{color:var(--muted);font-size:11px;max-width:300px}}
</style>"""

# ----------------------------------------------------------------- 4. bar
BAR_OLD = "<main>{body}</main>"
BAR_NEW = """<main>{body}</main>
<!-- BOOKSMITH_WIRING_2026_09_12 -->
<div id="buildbar">
  <span><b id="bbn">0</b> selected</span>
  <select id="bbmode" title="Which languages go into the witness Booksmith parses">
    <option value="tri">Sanskrit + IAST + English + Hindi</option>
    <option value="en">Sanskrit + IAST + English</option>
    <option value="hi">Sanskrit + IAST + Hindi</option>
  </select>
  <select id="bbproduct" title="Audit edition is the whole text and is never gated. Layout proof is eight representative units.">
    <option value="audit">Audit edition &mdash; whole text</option>
    <option value="proof">Layout proof &mdash; 8 units</option>
  </select>
  <button class="go" id="bbgo" onclick="buildSelected()">Build PDFs</button>
  <button onclick="clearSel()">Clear</button>
  <span class="hint">Every mode carries the Sanskrit source: Booksmith requires two to four reading languages, so a single-language witness is outside its model.</span>
</div>"""

# ------------------------------------------------------------------ 5. JS
JS_OLD = """}}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}
}}
</script>"""
JS_NEW = """}}catch(e){{ _toast('Request failed: '+e); btn.textContent=orig; btn.disabled=false; }}
}}

/* BOOKSMITH_WIRING_2026_09_12
   Selection, dispatch, and per-card state. The state endpoint is the single
   source of truth for what exists on disk; this script never infers that a
   PDF was produced from the fact that a job was started. */
var SEL = new Set();
function allDocs(){{
  return Array.from(document.querySelectorAll('.card-wrap[data-doc]'))
              .map(function(w){{ return w.getAttribute('data-doc'); }});
}}
function syncBar(){{
  var bar=document.getElementById('buildbar');
  document.getElementById('bbn').textContent=SEL.size;
  bar.style.display = SEL.size ? 'flex' : 'none';
}}
function clearSel(){{
  SEL.clear();
  document.querySelectorAll('.pickbox').forEach(function(b){{
    b.checked=false; b.closest('.card-wrap').classList.remove('sel');
  }});
  syncBar();
}}
document.addEventListener('change', function(e){{
  if(!e.target.classList.contains('pickbox')) return;
  var doc=e.target.value, wrap=e.target.closest('.card-wrap');
  if(e.target.checked){{ SEL.add(doc); wrap.classList.add('sel'); }}
  else {{ SEL.delete(doc); wrap.classList.remove('sel'); }}
  syncBar();
}});

function bsRender(s){{
  var el=document.getElementById('bs-'+s.doc);
  if(!el) return;
  var h='';
  if(s.job){{ h+='<span class="busy">building\\u2026</span>'; }}
  if(s.pdf){{
    var kb=Math.round(s.pdf.bytes/1024);
    var label = s.pdf.kind==='book' ? 'Download PDF' : 'Download layout proof';
    h+='<a class="pdf" href="/api/booksmith/pdf/'+encodeURIComponent(s.doc)+'" '+
       'title="'+kb+' KB, built '+s.pdf.mtime+'">\\u2b07 '+label+'</a>';
  }}
  if(s.project){{
    h+='<a class="bsui" target="_blank" rel="noopener" href="'+s.ui+'" '+
       'title="Open this project in Booksmith to review findings and build the reading edition">Booksmith \\u2197</a>';
  }}
  if(s.last && s.last.blocked){{
    h+='<span class="warn" title="'+(s.last.blockers||[]).join(' ').replace(/"/g,'')+
       '">reading edition blocked</span>';
  }}
  el.innerHTML=h;
}}

var BS_TIMER=null;
async function refreshBooksmith(once){{
  var docs=allDocs();
  if(!docs.length) return;
  try{{
    var r=await fetch('/api/booksmith/state?docs='+encodeURIComponent(docs.join(',')));
    var d=await r.json();
    if(d.states) d.states.forEach(bsRender);
    var busy=(d.states||[]).some(function(s){{ return s.job; }});
    if(BS_TIMER) clearTimeout(BS_TIMER);
    if(busy && !once) BS_TIMER=setTimeout(refreshBooksmith,3000);
  }}catch(e){{ /* the dashboard may be restarting; the next tick retries */ }}
}}

async function buildSelected(){{
  if(!SEL.size) return;
  var go=document.getElementById('bbgo');
  var mode=document.getElementById('bbmode').value;
  var product=document.getElementById('bbproduct').value;
  go.disabled=true; var orig=go.textContent; go.textContent='starting\\u2026';
  try{{
    var r=await fetch('/api/booksmith/build',{{method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{docs:Array.from(SEL),mode:mode,product:product}})}});
    var d=await r.json();
    if(d.error){{ _toast(d.error); }}
    else{{
      _toast('Queued '+d.started.length+' build(s). Export, ingest, audit, then PDF \\u2014 watch the cards.');
      if(d.rejected && d.rejected.length) _toast(d.rejected.length+' rejected: '+d.rejected[0].why);
      clearSel();
      setTimeout(function(){{ refreshBooksmith(); }},800);
    }}
  }}catch(e){{ _toast('Request failed: '+e); }}
  go.textContent=orig; go.disabled=false;
}}
document.addEventListener('DOMContentLoaded',function(){{ refreshBooksmith(true); }});
</script>"""


def replace_one(text: str, old: str, new: str, label: str):
    n = text.count(old)
    if n != 1:
        return text, ["%s: matched %d times, expected exactly 1" % (label, n)]
    return text.replace(old, new), []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not DASH.exists():
        print("FAIL: %s not found. Run from the repo root." % DASH)
        return 2
    if not ORCH.exists():
        print("FAIL: %s is missing. The routes would launch a script that does not exist." % ORCH)
        return 2

    # dashboard.py is 2,720 lines of pure CRLF. read_text() normalises to \n,
    # so writing back with newline="\n" would silently convert every line in
    # the file and turn a six-edit change into an unreviewable 2,720-line
    # diff. Detect the convention and write it back unchanged.
    raw = DASH.read_bytes()
    crlf_before = raw.count(b"\r\n")
    lf_before = raw.count(b"\n") - crlf_before
    newline = "\r\n" if crlf_before > lf_before else "\n"

    src = DASH.read_text(encoding="utf-8")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0

    problems: list[str] = []
    src, p = replace_one(src, ROUTES_ANCHOR, ROUTES_NEW + ROUTES_ANCHOR, "routes"); problems += p
    src, p = replace_one(src, CARD_OLD, CARD_NEW, "card checkbox"); problems += p
    src, p = replace_one(src, ACTS_OLD, ACTS_NEW, "card actions slot"); problems += p
    src, p = replace_one(src, CSS_OLD, CSS_NEW, "css"); problems += p
    src, p = replace_one(src, BAR_OLD, BAR_NEW, "build bar"); problems += p
    src, p = replace_one(src, JS_OLD, JS_NEW, "javascript"); problems += p

    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1

    if args.check:
        print("All 6 anchors matched exactly once. --check: nothing written.")
        return 0

    DASH.write_text(src, encoding="utf-8", newline=newline)

    # Prove we did not churn the file. Every line we added is a new line; not
    # one existing line should have changed its ending.
    after = DASH.read_bytes()
    crlf_after = after.count(b"\r\n")
    lf_after = after.count(b"\n") - crlf_after
    mixed_before = crlf_before and lf_before
    mixed_after = crlf_after and lf_after
    if not mixed_before and mixed_after:
        raise SystemExit(
            "REVERTED NOTHING BUT STOP: the file was uniformly %s and is now mixed "
            "(%d CRLF / %d LF). Restore from backups/ before doing anything else."
            % ("CRLF" if crlf_before else "LF", crlf_after, lf_after))
    added = (crlf_after + lf_after) - (crlf_before + lf_before)
    print("Patched: %s  (6 edits, +%d lines, endings preserved as %s)"
          % (DASH, added, "CRLF" if newline == "\r\n" else "LF"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
