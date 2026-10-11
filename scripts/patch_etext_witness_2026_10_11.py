#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_witness_2026_10_11.py  (2026-10-11)  ETEXT_WITNESS_2026_10_11

An e-text as a witness, and the missing page offered on the repair page (the Source desk's S2 and S3);
and the judge made more exact (judge v2). Asked on 11 Oct: "a built-in browser that uses AI to source the
best critical or near-critical Sanskrit text ... that we can then let loose our automaton on ... and then
source the missing page for the user via the front end in translation repairs".

  scripts/etext_witness.py (delivered beside this patcher): a GRETIL, sanskritdocuments.org or archive.org
    e-text becomes the page JSONL of a text of its own (<doc>__w_<site>), measured against the scan page by
    page; the pages the scan cannot read are offered as the witness reads them.
  scripts/repair_text.py:
    judge v2: a page whose vision OCR failed (the merge fell back to Tesseract) or came back short is not
      a disagreement; five pages at least before the vision agreement sets the level; for a text cut into
      long passages (600 letters or more), the share of all letters misread counts (2% material, 1%
      moderate); --judge-all prints each kind of debris;
    --release: a witness waits for its translation, as a text in repair does.
  scripts/corpus_sync.py: a witness is not mirrored (nor its pictures, nor the Corner's) until adopted.
  scripts/source_desk.py: a fetched OCR text's next step is etext_witness.py.
  scripts/dashboard.py (on a restart): the repair page's Source desk lists the files fetched into
    sources\\<doc>\\ (Read it as a witness), takes a pasted e-text link, shows each witness (how much of the
    scan it reads, in order or not; Ingest it as its own text; Translate it; Adopt it) and the pages the scan
    cannot read as the witness reads them; the Library's card of a witness says what it is.
  .gitignore: data/raw_witness/ and data/source_judged/ stay local (both are made again on demand).

Needs JUDGE_DESK_2026_10_11 (repair_text.py, dashboard.py), REPAIR_HEAL_2026_10_11 (corpus_sync.py) and
SOURCE_DESK_2026_10_11 (source_desk.py). Anchored, all-or-nothing, marker-idempotent per file; keeps line
endings; each .py is compiled before it replaces the original; backups .bak_etextwitness_<date>.
  python scripts\\patch_etext_witness_2026_10_11.py --check
  python scripts\\patch_etext_witness_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "ETEXT_WITNESS_2026_10_11"
NEEDS = {"scripts/repair_text.py": "JUDGE_DESK_2026_10_11", "scripts/dashboard.py": "JUDGE_DESK_2026_10_11",
         "scripts/corpus_sync.py": "REPAIR_HEAL_2026_10_11", "scripts/source_desk.py": "SOURCE_DESK_2026_10_11"}

E = []   # (file, name, old, new)
def edit(f, name, old, new):
    E.append((f, name, old, new))


# ---- repair_text.py: judge v2, and a witness waits for its translation ----------------------------------
R = "scripts/repair_text.py"
edit(R, "judge v2: the pages vision failed on",
     '''    stored = {}
    for pg, text, eng, has_tr, q in rows:
        if "vision" not in (eng or "").lower():
            stored.setdefault(pg, []).append(text or "")
''',
     '''    stored, skip = {}, set()
    for pg, text, eng, has_tr, q in rows:
        e = (eng or "").lower()
        if "fallback" in e:          # ETEXT_WITNESS_2026_10_11 (judge v2): the merge kept Tesseract, vision failed there
            skip.add(pg)
        elif "vision" not in e:
            stored.setdefault(pg, []).append(text or "")
''')
edit(R, "judge v2: leave those pages out",
     '''    both = sorted(int(p) for p in vis if int(p) in stored)
''',
     '''    both = sorted(int(p) for p in vis if int(p) in stored and int(p) not in skip)
''')
edit(R, "judge v2: a short vision page",
     '''        if len(a) < 80 or len(b) < 80 or len(a) > 8000:
            continue
''',
     '''        if len(a) < 80 or len(b) < 80 or len(a) > 8000 or len(b) < 0.5 * len(a):
            continue                 # a short vision page is a failed one, not a disagreement (judge v2)
''')
edit(R, "judge v2: letters misread, and five pages",
     '''    elif out["misread_pct"] >= 10:
        lvl = 1
    if sims:
        lvl = max(lvl, 2 if out["agree_median"] < 0.90 else (1 if out["agree_median"] < 0.97 else 0))
''',
     '''    elif out["misread_pct"] >= 10:
        lvl = 1
    # ETEXT_WITNESS_2026_10_11 (judge v2): a text cut into long passages (a page each) hides its misreadings
    # under the 3% a verse; there the share of all letters misread counts (2% material, 1% moderate: where
    # 25% of verses are misread, 2.0-2.5% of the letters are, on the 47 texts judged on 11 Oct). Not for
    # verses, where 1.5% of letters would have made ten of the eleven moderate texts, and three cosmetic, material.
    if nv and tchars / float(nv) >= 600:
        lvl = max(lvl, 2 if out["misread_letters_pct"] >= 2.0 else (1 if out["misread_letters_pct"] >= 1.0 else 0))
    if len(sims) >= 5:               # two pages are not a measurement
        lvl = max(lvl, 2 if out["agree_median"] < 0.90 else (1 if out["agree_median"] < 0.97 else 0))
''')
edit(R, "judge v2: each kind of debris in --judge-all",
     '''        print("  [%d/%d] %-60s %-9s debris %5.1f%% | %s" % (i, len(todo), code[:60], lvl, r["debris_pct"], v[:90]), flush=True)
''',
     '''        j = r.get("judged") or {}   # ETEXT_WITNESS_2026_10_11 (judge v2): each kind of debris
        print("  [%d/%d] %-56s %-9s debris %5.1f%% (misread %4.1f%% of verses, %4.2f%% of letters; furniture %4.1f%%; "
              "notes %4.1f%%) | %s" % (i, len(todo), code[:56], lvl, r["debris_pct"], j.get("misread_pct", 0),
                                       j.get("misread_letters_pct", 0), j.get("furniture_pct", 0), j.get("notes_pct", 0),
                                       v[:70]), flush=True)
''')
edit(R, "a witness waits for its translation",
     '''        if cur.get("status") == "in_repair" and not a.force:
            r0 = assess(a)
            if not r0.get("error"):
''',
     '''        if cur.get("status") in ("in_repair", "witness") and not a.force:   # ETEXT_WITNESS_2026_10_11: a witness too
            r0 = assess(a)
            if r0.get("error") and cur.get("status") == "witness":
                print("REFUSE: %s is a witness not yet in the database: ingest it (python scripts\\\\etext_witness.py "
                      "--doc %s --ingest --witness %s), then translate it" % (a.doc, cur.get("of") or "?", a.doc))
                print("VERDICT: a witness, not yet ingested"); print("NEXT: ")
                return 1
            if not r0.get("error"):
''')

# ---- corpus_sync.py: a witness is local until adopted ------------------------------------------------------
C = "scripts/corpus_sync.py"
edit(C, "the witnesses",
     '''def live_docs(con, include_retired: bool = False):
''',
     '''def _witness_docs() -> set:
    """ETEXT_WITNESS_2026_10_11: e-text witnesses (scripts/etext_witness.py) stay local until they are adopted:
    the latest record of their code in data/source_verdicts.jsonl is "witness" (repair_text.py --release, once
    translated, makes it "released"). SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "witness"}


def live_docs(con, include_retired: bool = False):
''')
edit(C, "live_docs leaves them out",
     '''    out = []
    for r in rows:
        code = r[1]
        if not code:
            continue
        if not include_retired and (code.endswith("-RETIRED") or code in retired):
            continue
''',
     '''    out = []
    witness = _witness_docs()   # ETEXT_WITNESS_2026_10_11: local until adopted
    for r in rows:
        code = r[1]
        if not code:
            continue
        if not include_retired and (code.endswith("-RETIRED") or code in retired):
            continue
        if code in witness:
            continue
''')

# ---- source_desk.py: a fetched OCR text goes to etext_witness.py -----------------------------------------
S = "scripts/source_desk.py"
edit(S, "the next step of a fetched text",
     '''        print("NEXT: read it beside the scan; ingesting an e-text as a witness is the next build (SOURCE_DESK S2)")
''',
     '''        print('NEXT: python scripts\\\\etext_witness.py --doc %s --file "%s"   (ETEXT_WITNESS_2026_10_11: read it as a '
              'witness, free)' % (a.doc, target))
''')

# ---- dashboard.py -----------------------------------------------------------------------------------------
D = "scripts/dashboard.py"
edit(D, "the witness step",
     '''                 "find", "fetch", "judge_all")   # JUDGE_DESK_2026_10_11: judge_all
''',
     '''                 "find", "fetch", "judge_all", "witness")   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
''')
edit(D, "the witness state",
     '''_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair")
''',
     '''_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness")   # ETEXT_WITNESS_2026_10_11: witness
SOURCES_DIR = ROOT / "sources"                       # ETEXT_WITNESS_2026_10_11: what source_desk.py and etext_witness.py fetch
WITNESS_DIR = ROOT / "data" / "raw_witness"          # the witnesses' pages, witness.json and align.json
WITNESSES_LOG = ROOT / "data" / "witnesses.jsonl"
''')
edit(D, "the step's words",
     "                 judge_all: 'judging the texts (about a minute)...'};",
     "                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...'};")
edit(D, "the next step of a witness",
     '''function _rpNext(next){
  var n = String(next || ''), m;
''',
     '''function _rpNext(next){
  var n = String(next || ''), m;
  if (n.indexOf('etext_witness.py') >= 0){   /* ETEXT_WITNESS_2026_10_11 */
    if (n.indexOf('--ingest') >= 0){
      m = n.match(/--witness ([A-Za-z0-9_-]+)/);
      return m ? {step: 'witness', ingest: m[1], label: 'Ingest the witness as its own text'} : null;
    }
    m = n.match(/--file "([^"]+)"/);
    if (!m || n.indexOf('--page') >= 0) return null;
    var fname = m[1].split(_RP_BS).pop().split('/').pop();
    return n.indexOf('--write') >= 0 ? {step: 'witness', write: 1, file: fname, label: 'Make it a witness (its pages; not the database)'}
                                     : {step: 'witness', file: fname, label: 'Read it as a witness (free)'};
  }
''')
edit(D, "what a witness step sends",
     '''  var orig = btn ? btn.textContent : '';
''',
     '''  if (step === 'witness'){   /* ETEXT_WITNESS_2026_10_11 */
    if (opt.file) body.file = opt.file;
    if (opt.url) body.url = opt.url;
    if (opt.write){
      body.write = 1;
      if (!confirm('Make the witness of ' + doc + ': its pages go to data' + _RP_BS + 'raw_witness, a line to data' + _RP_BS
                   + 'witnesses.jsonl, and the register keeps it off the site until you adopt it. The database is not '
                   + 'touched. Go?')) return;
    }
    if (opt.ingest){
      body.ingest = opt.ingest;
      if (!confirm('Ingest ' + opt.ingest + ' as its own text: a backup first, then its passages go into the database '
                   + '(after the running translation). The scan is not touched, and the site does not have it until you '
                   + 'adopt it. Go?')) return;
    }
  }
  var orig = btn ? btn.textContent : '';
''')
edit(D, "the Source desk again after a witness step",
     "      if ((step === 'find' || step === 'fetch') && document.getElementById('srclist-' + doc)) _rpSources(doc);",
     "      if ((step === 'find' || step === 'fetch' || step === 'witness') && document.getElementById('srclist-' + doc)) _rpSources(doc);")
edit(D, "the witnesses before a search",
     "  if (!d || d.missing){ list.innerHTML = '<p class=\"srcnone\">No search yet. Press Find a better source.</p>'; return; }",
     "  if (!d || d.missing){ list.innerHTML = '<p class=\"srcnone\">No search yet. Press Find a better source.</p>' + _rpWitness(doc, d || {}); list._data = d || {}; return; }")
edit(D, "the witnesses after a search",
     '''  list.innerHTML = h; list._data = d;
}
function _rpPreview(doc, i){
''',
     '''  h += _rpWitness(doc, d);
  list.innerHTML = h; list._data = d;
}
function _rpWitness(doc, d){
  /* ETEXT_WITNESS_2026_10_11: the e-texts fetched for this text, its witnesses, and the pages they offer */
  var f = (d && d.fetched) || [], w = (d && d.witnesses) || [], h = '';
  if (f.length) h += '<div class="srcsub">Fetched into sources' + _RP_BS + _rpEsc(doc) + _RP_BS + '</div>';
  f.forEach(function(x){
    var act = (x.kind === 'text' && x.ok)
      ? '<button class="tr-rest rp" data-f="' + _rpEsc(x.name) + '" onclick="repairStep(&#39;' + doc
        + '&#39;,&#39;witness&#39;,this,{file:this.dataset.f})">Read it as a witness (free)</button>'
      : (x.kind === 'pdf' ? '<span class="srcwhy">A PDF: import it from the dashboard (Import path to inbox) as its own '
                            + 'text, and OCR it with vision.</span>' : '');
    h += '<div class="srccard"><div class="srchead"><b>' + _rpEsc(x.name) + '</b><span class="srcmeta">'
       + Math.max(1, Math.round((x.bytes || 0) / 1024)) + ' KB' + (x.url ? ' &middot; <a href="' + _rpEsc(x.url)
       + '" target="_blank" rel="noopener">its source</a>' : '') + '</span></div><div class="srcacts">' + act + '</div></div>';
  });
  w.forEach(function(x){
    var offers = (x.offers || []).filter(function(o){ return o.text; });
    h += '<div class="srccard wit"><div class="srchead"><b>Witness</b><span>' + _rpEsc(x.witness) + '</span>'
       + (x.state ? '<span class="srctag">' + _rpEsc(x.state) + '</span>' : '') + '</div>'
       + '<div class="srcmeta">' + _rpEsc(x.site || '') + ' &middot; ' + (x.verses || 0) + ' verses in ' + (x.pages || 0) + ' pages'
       + (x.coverage != null ? ' &middot; it reads ' + Math.round(100 * x.coverage) + '% of the scan&#39;s readable pages, in order '
          + Math.round(100 * (x.order || 0)) + '%' : '')
       + (x.ingested != null ? ' &middot; ingested: ' + x.ingested + ' passages' : '') + '</div>'
       + '<div class="srcwhy">' + _rpEsc(x.opinion || '') + '</div>'
       + '<div class="repairbar wbar" id="rp-' + _rpEsc(x.witness) + '">'
       + (x.ingested == null
          ? '<button class="tr-rest rp" data-w="' + _rpEsc(x.witness) + '" onclick="repairStep(&#39;' + doc
            + '&#39;,&#39;witness&#39;,this,{ingest:this.dataset.w})">Ingest it as its own text</button>'
          : '<button class="tr-rest rp" data-w="' + _rpEsc(x.witness) + '" onclick="repairStep(this.dataset.w,&#39;translate&#39;,this)">'
            + 'Translate it: English, then Hindi</button><button class="tr-rest rp" data-w="' + _rpEsc(x.witness)
            + '" onclick="repairStep(this.dataset.w,&#39;release&#39;,this)">Adopt it: publish it to the site</button>')
       + '<div class="rpout"></div></div>';
    if (offers.length){
      h += '<div class="srcsub">The pages the scan cannot read, as this witness reads them (' + offers.length + ')</div>';
      offers.slice(0, 40).forEach(function(o){
        h += '<details class="srcoffer"><summary>page ' + o.page + (o.refs ? ' &middot; ' + _rpEsc(o.refs) : '')
           + ' &middot; ' + _rpEsc(o.why) + '</summary><pre class="srcpre">' + _rpEsc(o.text) + '</pre></details>';
      });
    }
    h += '</div>';
  });
  return h;
}
function _rpPreview(doc, i){
''')
edit(D, "api_repair: the witness step",
     '''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
''',
     '''    elif step == "witness":   # ETEXT_WITNESS_2026_10_11: read, write or ingest an e-text witness
        argv = [script("etext_witness.py"), "--doc", doc, "--from-dashboard"]
        f, url, ing = str(data.get("file") or ""), str(data.get("url") or "").strip(), str(data.get("ingest") or "")
        if ing:
            if not re.match(r"^[A-Za-z0-9_\\-]{1,200}$", ing) or not ing.startswith(doc + "__w_"):
                return jsonify({"error": "ingest needs a witness of this text (<doc>__w_<site>)"}), 400
            argv += ["--ingest", "--witness", ing]
        elif f:
            if not re.match(r"^[A-Za-z0-9._\\- ()]{1,160}$", f) or f.startswith("."):
                return jsonify({"error": "file must be the name of a file in sources\\\\<doc>\\\\"}), 400
            argv += ["--file", str(SOURCES_DIR / doc / f)]
        elif url:
            if not re.match(r"^https?://[^\\s\\"'<>]{4,500}$", url):
                return jsonify({"error": "url must be an http(s) link"}), 400
            argv += ["--url", url]
        else:
            return jsonify({"error": "witness needs a file, a url, or a witness to ingest"}), 400
        if data.get("write") and not ing:
            argv.append("--write")
    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
''')
edit(D, "an ingest is a database writer",
     '''    kind = "repair_use" if step == "use" else "repair"
''',
     '''    kind = "repair_use" if step == "use" or (step == "witness" and data.get("ingest")) else "repair"   # ETEXT_WITNESS_2026_10_11
''')
edit(D, "the Source desk's answer holds the witnesses",
     '''    p = SOURCE_DESK_DIR / ("%s.json" % doc)
    try:
        return jsonify(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return jsonify({"doc": doc, "missing": True, "candidates": []})
''',
     '''    p = SOURCE_DESK_DIR / ("%s.json" % doc)
    try:
        out = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out = {"doc": doc, "missing": True, "candidates": []}
    if isinstance(out, dict):   # ETEXT_WITNESS_2026_10_11
        out.update(_witness_info(doc))
    return jsonify(out)
''')
edit(D, "_witness_info",
     '''@app.get("/api/repair/sources")
''',
     '''def _witness_info(doc: str) -> dict:
    """ETEXT_WITNESS_2026_10_11: the files fetched into sources/<doc>/ and the witnesses of the text (from
    data/witnesses.jsonl, their align.json and the register), for the repair page. Small files only."""
    import re as _re
    ok_name = _re.compile(r"^[A-Za-z0-9._\\- ()]{1,160}$")
    ok_url = _re.compile(r"^https?://[^\\s\\"'<>]{4,500}$")
    fetched, wits = [], []
    try:
        for f in sorted((SOURCES_DIR / doc).iterdir()):
            if not f.is_file() or f.name.endswith((".json", ".part")):
                continue
            side = {}
            try:
                side = json.loads(f.with_name(f.name + ".json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            url = str(side.get("url") or side.get("details") or "")
            fetched.append({"name": f.name, "bytes": f.stat().st_size, "ok": bool(ok_name.match(f.name)) and not f.name.startswith("."),
                            "kind": "pdf" if f.suffix.lower() == ".pdf" else "text", "url": url if ok_url.match(url) else ""})
    except OSError:
        pass
    seen = {}
    try:
        for line in WITNESSES_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc") == doc and r.get("witness"):
                seen[r["witness"]] = dict(seen.get(r["witness"], {}), **r)
    except OSError:
        pass
    reg = {}
    try:
        for line in (WITNESSES_LOG.parent / "source_verdicts.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc") in seen:
                reg[r["doc"]] = r.get("status")
    except OSError:
        pass
    for w, r in sorted(seen.items(), key=lambda x: str(x[1].get("at") or "")):
        al = {}
        try:
            al = json.loads((WITNESS_DIR / w / "align.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        offers = [dict(o, text=str(o.get("text") or "")[:1500]) for o in (al.get("offers") or [])[:40] if isinstance(o, dict)]
        url = str(r.get("url") or "")
        wits.append({"witness": w, "site": r.get("site"), "verses": r.get("verses"), "pages": r.get("pages"),
                     "coverage": r.get("coverage"), "order": r.get("order"), "opinion": r.get("opinion"),
                     "ingested": r.get("ingested"), "at": r.get("at"), "url": url if ok_url.match(url) else "",
                     "state": {"witness": "local only", "released": "adopted"}.get(reg.get(w), reg.get(w) or ""),
                     "offers": offers})
    return {"fetched": fetched, "witnesses": wits}


@app.get("/api/repair/sources")
''')
edit(D, "a pasted e-text link",
     '''<div class="srclist" id="srclist-__CODE__"></div>
''',
     '''<div class="srcbar"><input class="srcurl" id="srcurl-__CODE__" placeholder="Paste an e-text link (a .htm or .txt file on GRETIL, sanskritdocuments.org or archive.org)"/>
<button class="tr-rest rp" data-doc="__CODE__" onclick="var u=document.getElementById('srcurl-'+this.dataset.doc).value.trim(); if(u) repairStep(this.dataset.doc,'witness',this,{url:u});">Fetch it and read it as a witness</button></div>
<div class="srclist" id="srclist-__CODE__"></div>
''')
edit(D, "the witness styles",
     '''.srcviewbar a{color:var(--gold)}
</style></head><body>
''',
     '''.srcviewbar a{color:var(--gold)}
.srcurl{flex:1 1 320px;min-width:0;background:var(--card);border:1px solid var(--border);color:var(--cream);border-radius:7px;padding:6px 9px;font-size:12px}
.srcsub{font-size:11px;color:var(--gold);letter-spacing:.5px;text-transform:uppercase;margin:14px 0 4px}
.srccard.wit{border-color:#3d5a3a}
.srcoffer{margin:4px 0;font-size:12px}
.srcoffer summary{cursor:pointer;color:var(--cream)}
.srcpre{white-space:pre-wrap;word-break:break-word;background:var(--card2);border:1px solid var(--border);border-radius:6px;padding:8px;margin-top:4px;font-family:'EB Garamond',Georgia,serif;font-size:15px;line-height:1.5}
</style></head><body>
''')
edit(D, "the Library's card of a witness",
     '''    elif st == "in_repair":
        acts_html += ('<div class="cardnote state">In repair since''',
     '''    elif st == "witness":   # ETEXT_WITNESS_2026_10_11
        acts_html += ('<div class="cardnote state">A witness of %s (%s), made on %s: an e-text, local only. The site '
                      'does not have it until you adopt it (publish it), once it is translated.</div>'
                      % (_html.escape(str(rec.get("of") or "?")), _html.escape(str(rec.get("site") or "e-text")), at))
    elif st == "in_repair":
        acts_html += ('<div class="cardnote state">In repair since''')
edit(D, "a witness's bar",
     '''    if st == "in_repair":
        acts_html += _repair_bar(code, "in_repair")
    elif "repaired" in kinds:
''',
     '''    if st in ("in_repair", "witness"):   # ETEXT_WITNESS_2026_10_11: a witness too
        acts_html += _repair_bar(code, "in_repair")
    elif "repaired" in kinds:
''')

GITIGNORE_BLOCK = """
# ETEXT_WITNESS_2026_10_11: the witnesses' pages are made again from sources/ (etext_witness.py --write);
# the debris judged is made again by repair_text.py --judge-all (it changed on every run)
data/raw_witness/
data/source_judged/
"""


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    ew = Path("scripts/etext_witness.py")
    if not ew.exists() or MARK.encode() not in ew.read_bytes():
        print("REFUSE: scripts\\etext_witness.py with %s is not there (it comes with this patcher). Nothing written." % MARK)
        return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in (R, C, S, D):
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out = src
        for f, name, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    gi = Path(".gitignore")
    if gi.exists():
        gsrc, gnl = load(gi)
        if MARK not in gsrc:
            todo.append((gi, (gsrc.rstrip("\n") + "\n" + GITIGNORE_BLOCK).replace("\n", gnl).encode("utf-8")))
        else:
            print("skip .gitignore (already carries %s)" % MARK)
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
        shutil.copy2(p, p.with_name(p.name + ".bak_etextwitness_" + stamp))
        t = p.with_name(p.name + ".tmp_etextwitness"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("dashboard.py takes the witnesses on the repair page when restarted, only when idle: scripts\\restart_dashboard.ps1.")
    print("The mirror leaves witnesses alone from its next run. Then: python scripts\\repair_text.py --judge-all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
