#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_benchmark_2026_10_11.py  (2026-10-11)  BENCHMARK_2026_10_11

The readings of each text benchmarked, and shown: where the automaton improved the text and its
translation, against what archive.org already had and against a critical e-text, and where it did not.
Asked on 11 Oct: "this would also give us a window into benchmarking our own efforts against pre-existing
data at archive.org etc and rate where we have improved things and translations and ocr+vision, if at all".

  scripts/benchmark_sources.py (delivered beside this patcher): free and read-only; Tesseract, vision, the
    repair, the database, the text before its repair (the oldest repair backup, read immutable), the
    witnesses and every text file in sources\\<doc>\\, compared page by page; the debris's effect on the
    translation made before the repair, and on the one now; data\\benchmarks\\<doc>.json.
  scripts/dashboard.py (on a restart): the repair page's Source desk has "Benchmark the readings (free)"
    and shows the table and the opinion; /benchmarks lists every text benchmarked, with "Benchmark every
    text again"; Sources & repairs links to it.
  scripts/repair_text.py: --release refuses a text that is not in the database (on 11 Oct, 22:17, a
    command with a placeholder wrote "released" for Bodhicaryavatara__w_gretil, which does not exist).
  scripts/etext_witness.py: --write always marks the witness local; a stale "released" of its name (as
    that one) no longer makes it public when it is ingested.
  .gitignore: data/benchmarks/ stays local (made again on demand).

Needs ETEXT_WITNESS_2026_10_11 in repair_text.py, etext_witness.py and dashboard.py. Anchored,
all-or-nothing, marker-idempotent per file; keeps line endings; each .py is compiled before it replaces
the original; backups .bak_benchmark_<date>.
  python scripts\\patch_benchmark_2026_10_11.py --check
  python scripts\\patch_benchmark_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "BENCHMARK_2026_10_11"
NEEDS = "ETEXT_WITNESS_2026_10_11"

E = []   # (file, name, old, new)
def edit(f, name, old, new):
    E.append((f, name, old, new))


R = "scripts/repair_text.py"
edit(R, "release refuses a text that is not there",
     '''        cur = verdicts(Path(a.verdicts)).get(a.doc) or {}
        if cur.get("status") in ("in_repair", "witness") and not a.force:   # ETEXT_WITNESS_2026_10_11: a witness too
''',
     '''        cur = verdicts(Path(a.verdicts)).get(a.doc) or {}
        if not a.force and cur.get("status") != "witness":   # BENCHMARK_2026_10_11: nothing to publish
            r00 = assess(a)
            if r00.get("error"):
                print("REFUSE: %s: %s; nothing is published. --force writes the record all the same." % (a.doc, r00["error"]))
                print("VERDICT: not published: %s is not in the database" % a.doc); print("NEXT: ")
                return 1
        if cur.get("status") in ("in_repair", "witness") and not a.force:   # ETEXT_WITNESS_2026_10_11: a witness too
''')

W = "scripts/etext_witness.py"
edit(W, "a written witness is always local",
     '''    cur = rt.verdicts(Path(a.verdicts)).get(wcode) or {}
    if cur.get("status") != "released":
        _append(Path(a.verdicts), {"doc": wcode, "status": "witness", "of": doc, "site": site,
                                   "reason": "an e-text witness of %s (%s): local only until it is adopted" % (doc, site),
                                   "at": meta["at"], "by": "etext_witness.py", "mark": MARK})
''',
     '''    # BENCHMARK_2026_10_11: always. The witness is not in the database (refused above), so a "released" of its
    # name is stale (on 11 Oct a placeholder command wrote one for Bodhicaryavatara__w_gretil)
    _append(Path(a.verdicts), {"doc": wcode, "status": "witness", "of": doc, "site": site,
                               "reason": "an e-text witness of %s (%s): local only until it is adopted" % (doc, site),
                               "at": meta["at"], "by": "etext_witness.py", "mark": MARK})
''')

D = "scripts/dashboard.py"
edit(D, "the benchmark steps",
     '''                 "find", "fetch", "judge_all", "witness")   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
''',
     '''                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all")              # BENCHMARK_2026_10_11
''')
edit(D, "benchmark_all needs no text",
     '''    doc = "corpus" if step == "judge_all" else _validate_doc(data.get("doc"))   # JUDGE_DESK_2026_10_11
''',
     '''    doc = "corpus" if step in ("judge_all", "benchmark_all") else _validate_doc(data.get("doc"))   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
''')
edit(D, "api_repair: the benchmark",
     '''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
''',
     '''    elif step == "benchmark":   # BENCHMARK_2026_10_11: free and read-only
        argv = [script("benchmark_sources.py"), "--doc", doc, "--from-dashboard"]
    elif step == "benchmark_all":
        argv = [script("benchmark_sources.py"), "--all", "--from-dashboard"]
    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
''')
edit(D, "the steps' words",
     "witness: 'reading the e-text as a witness...'};",
     "witness: 'reading the e-text as a witness...',\n                 benchmark: 'benchmarking the readings (free)...', "
     "benchmark_all: 'benchmarking every text (a minute or two)...'};")
edit(D, "the Source desk again after a benchmark",
     "(step === 'find' || step === 'fetch' || step === 'witness') && document.getElementById('srclist-' + doc)",
     "(step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)")
edit(D, "reload after benchmarking every text",
     "/^(set_aside|restore|use|as_is|accept|hold|release|translate|judge_all)$/.test(step)",
     "/^(set_aside|restore|use|as_is|accept|hold|release|translate|judge_all|benchmark_all)$/.test(step)")
edit(D, "the benchmark before a search",
     "+ _rpWitness(doc, d || {}); list._data = d || {}; return; }",
     "+ _rpWitness(doc, d || {}) + _rpBench(doc, d || {}); list._data = d || {}; return; }")
edit(D, "the benchmark after a search",
     '''  h += _rpWitness(doc, d);
''',
     '''  h += _rpWitness(doc, d) + _rpBench(doc, d);   // BENCHMARK_2026_10_11
''')
edit(D, "_rpBench",
     '''function _rpPreview(doc, i){
''',
     '''function _rpBench(doc, d){
  /* BENCHMARK_2026_10_11: the readings of the text compared (benchmark_sources.py), and the opinion */
  var b = d && d.benchmark;
  if (!b || !(b.readings || []).length)
    return '<div class="srcsub">Benchmark</div><p class="srcnone">Not benchmarked yet: press Benchmark the readings (free).</p>';
  var f = function(v, k){ return v == null ? '-' : (+v).toFixed(k == null ? 2 : k); };
  var h = '<div class="srcsub">Benchmark, ' + _rpEsc(String(b.at || '').replace('T', ' ').slice(0, 16))
        + (b.reference ? ', against ' + _rpEsc(b.reference) : '') + '</div><div class="benchwrap"><table class="bench"><thead><tr>'
        + '<th>Reading</th><th>Pages</th><th>Letters</th><th>Misread</th><th>Pages hit</th><th>Level</th><th>F1 with ours</th>'
        + '<th>F1 with the critical text</th></tr></thead><tbody>';
  (b.readings || []).forEach(function(x){
    h += '<tr><td>' + _rpEsc(x.label) + '</td><td>' + x.pages + '</td><td>' + x.letters + '</td><td>' + f(x.misread_letters_pct)
       + '%</td><td>' + f(x.pages_misread_pct, 0) + '%</td><td><span class="lv" data-level="' + _rpEsc(x.level || '') + '">'
       + _rpEsc(x.level || '-') + '</span></td><td>' + f(x.f1_ours) + '</td><td>' + f(x.f1_ref) + '</td></tr>';
  });
  h += '</tbody></table></div>';
  (b.lines || []).forEach(function(l){ h += '<p class="benchline">' + _rpEsc(l) + '</p>'; });
  return h;
}
function _rpPreview(doc, i){
''')
edit(D, "the Source desk's answer holds the benchmark",
     '''        out.update(_witness_info(doc))
''',
     '''        out.update(_witness_info(doc))
        out["benchmark"] = _bench(doc)   # BENCHMARK_2026_10_11
''')
edit(D, "the benchmark button",
     '''<label class="srcai"><input type="checkbox" id="srcai-__CODE__"/> let the AI judge the editions (about $0.002)</label></div>
''',
     '''<label class="srcai"><input type="checkbox" id="srcai-__CODE__"/> let the AI judge the editions (about $0.002)</label>
<button class="tr-rest rp" data-doc="__CODE__" onclick="repairStep(this.dataset.doc,'benchmark',this)">Benchmark the readings (free)</button></div>
''')
edit(D, "the benchmark styles",
     '''.srcoffer summary{cursor:pointer;color:var(--cream)}
''',
     '''.srcoffer summary{cursor:pointer;color:var(--cream)}
.benchwrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px;margin-top:4px}
table.bench{border-collapse:collapse;width:100%;font-size:11.5px;min-width:640px}
table.bench th,table.bench td{border-bottom:1px solid var(--border);padding:5px 8px;text-align:right;white-space:nowrap}
table.bench th:first-child,table.bench td:first-child{text-align:left}
table.bench th{color:var(--muted);font-weight:600;background:var(--card)}
.benchline{font-size:12.5px;line-height:1.5;margin:7px 0;color:var(--cream)}
.lv{display:inline-block;border-radius:5px;padding:0 6px;font-size:10.5px;border:1px solid var(--border)}
.lv[data-level=material]{border-color:#7a3a3a;color:#e8a3a3}
.lv[data-level=moderate]{border-color:#6b5420;color:#e6c27a}
.lv[data-level=cosmetic]{border-color:#2f6b4a;color:#9fd8b5}
''')
edit(D, "Sources & repairs links to the benchmarks",
     '''<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><h1>Sources &amp; repairs</h1></header>
''',
     '''<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/benchmarks">Benchmarks</a><h1>Sources &amp; repairs</h1></header>
''')

BLOCK = r'''# BENCHMARK_2026_10_11 -------------------------------------------------------------------------
# The readings of each text compared (scripts/benchmark_sources.py: Tesseract, vision, the repair, the
# database, the text before its repair, archive.org's OCR, the witnesses and the critical e-texts), and
# the effect of the debris on the translation, measured. Small files only (data/benchmarks/).
BENCH_DIR = ROOT / "data" / "benchmarks"


def _bench(doc: str):
    """The last benchmark of a text (data/benchmarks/<doc>.json), or None."""
    try:
        r = json.loads((BENCH_DIR / ("%s.json" % doc)).read_text(encoding="utf-8"))
        return r if isinstance(r, dict) else None
    except (OSError, ValueError):
        return None


@app.get("/benchmarks")
def benchmarks_page():
    """Every text benchmarked: misread letters in Tesseract, in ours (the repair, else the database) and in
    archive.org's OCR; the critical e-text's F1; the English before the repair and how much of it was made
    from damaged text; the English now; and the opinion. Reads small files only."""
    import html as _html
    e = _html.escape
    rows = []
    try:
        for p in sorted(BENCH_DIR.glob("*.json")):
            if p.name.startswith("_"):
                continue
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict) and r.get("doc") and r.get("readings"):
                rows.append(r)
    except OSError:
        pass

    def red(r, label):
        return next((x for x in r.get("readings") or [] if x.get("label") == label), None)

    pct = lambda x: ("%.2f%%" % float(x.get("misread_letters_pct") or 0)) if x else "-"
    trs, improved = "", 0
    for r in rows:
        te, ours = red(r, "tesseract"), (red(r, "consensus") or red(r, "database"))
        if te and ours and ours.get("label") == "consensus" and ours["misread_letters_pct"] < te["misread_letters_pct"]:
            improved += 1
        tr = r.get("translations") or {}
        b, n = tr.get("before") or {}, tr.get("now") or {}
        arch = [x for x in r.get("readings") or [] if x.get("kind") == "archive-ocr"]
        ref = ("%s: ours %s" % (r.get("reference"), "-" if not ours or ours.get("f1_ref") is None else "%.2f" % ours["f1_ref"])
               if r.get("reference") else "-")
        before = "-"
        if b.get("english"):
            before = "%s EN; %s%% of it from damaged text" % (b["english"], "?" if b.get("translated_misread_pct") is None
                                                               else "%.0f" % float(b["translated_misread_pct"]))
        trs += ('<tr><td><a href="/repair/%s">%s</a></td><td>%s</td><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td>'
                '<td>%s</td></tr>' % (e(r["doc"], quote=True), e(r["doc"]), pct(te), pct(ours),
                                      ('<br><span class="muted">%s</span>' % e(ours["label"])) if ours else "",
                                      e("; ".join("%s %s" % (x["label"], pct(x)) for x in arch)) or "-", e(ref), e(before),
                                      e("%s of %s EN, %s HI" % (n.get("english", 0), n.get("passages", 0), n.get("hindi", 0)))
                                      if n else "-"))
        if r.get("lines"):
            trs += '<tr><td colspan="7" class="muted" style="line-height:1.55">%s</td></tr>' % "<br>".join(
                e(x) for x in r["lines"])
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Each text\'s readings compared on the same pages: '
            'Tesseract, vision, the repair (ours), the text before its repair, archive.org\'s OCR and the critical '
            'e-texts, by the share of letters misread and, where a critical text is fetched, by how much of it each '
            'reading has. The translation: how much of the English made before the repair came from damaged text, '
            'and how much there is now. %d text(s) benchmarked; the repair cut the misreading in %d.</p>'
            '<div class="repairbar" id="rp-corpus" style="margin-top:10px"><button class="tr-rest rp" data-doc="corpus" '
            'onclick="repairStep(this.dataset.doc,&#39;benchmark_all&#39;,this)">Benchmark every text again (free, a minute '
            'or two)</button><div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>Tesseract '
            'misreads</th><th>Ours misreads</th><th>archive.org OCR</th><th>Critical e-text</th><th>English before the '
            'repair</th><th>Now</th></tr></thead><tbody>%s</tbody></table></div>%s</div>'
            % (len(rows), improved, trs, "" if rows else '<p class="srcnone">Nothing benchmarked yet. Press Benchmark '
                                                           'every text again.</p>'))
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Benchmarks</title>
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
""" + _REPAIR_CSS + _SOURCES_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><h1>Benchmarks</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


'''
edit(D, "the benchmarks page", '''

@app.get("/api/repair/sources")
''', "\n\n" + BLOCK + '''@app.get("/api/repair/sources")
''')

GITIGNORE_BLOCK = """
# BENCHMARK_2026_10_11: the benchmarks are made again by scripts/benchmark_sources.py (free, read-only)
data/benchmarks/
"""


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    bs = Path("scripts/benchmark_sources.py")
    if not bs.exists() or MARK.encode() not in bs.read_bytes():
        print("REFUSE: scripts\\benchmark_sources.py with %s is not there (it comes with this patcher). Nothing written." % MARK)
        return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in (R, W, D):
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS not in src:
            problems.append("%s does not carry %s: apply scripts\\patch_etext_witness_2026_10_11.py first" % (rel, NEEDS)); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_benchmark_" + stamp))
        t = p.with_name(p.name + ".tmp_benchmark"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("dashboard.py takes the benchmarks (repair page, /benchmarks) when restarted, only when idle:")
    print("scripts\\restart_dashboard.ps1. Then: python scripts\\benchmark_sources.py --all (free, read-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
