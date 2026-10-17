#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_tier_r_2026_10_17.py  (2026-10-17)  TIER_R_2026_10_17

Decided on 17 Oct: the working English by Claude Sonnet 5.5 in one pass (the SOP's Tier R), as BM1, BM3 and BM2 put it
above flash at about flash's price; and the scholarly English of the Markandeya Purana. This makes both a press:
  - the desk (/desk/<doc>): a box "The working English by Sonnet in one pass": the rest of the verses, or every
    verse again (the English before goes to translation_history), each with its price at BM1's $0.0052 a verse and
    the Claude credit left; English only; it asks first;
  - /api/translate: {"retranslate": true} runs translate_passages.py --retranslate;
  - the scholarly English begins at a verse ("Begin at": --from-ref, as 81.1 of an e-text), to take one part of a
    text (the Devimahatmya, adhyayas 81 to 93 of the Markandeya Purana) before the rest;
  - the main page: Claude Sonnet 5.5 among the engines (the header and each row), for one text at a time; Translate
    All refuses to run Claude, as the credit is spent verse by verse.
MT_ENGINE is unchanged (gemini-2.5-flash): Ask and extract_entities call Gemini directly.

scripts/translation_desk.py (needs TRANSLATION_DESK_2026_10_17), scripts/dashboard.py (needs
BENCH_GOLD_FAIR_2026_10_17), scripts/dashboard_static.html (needs BUTTONS_2026_10_17). Anchored, all-or-nothing,
marker-idempotent; keeps line endings; py_compile before the atomic replace; backups .bak_tierr_<date>. No database
change.
  python scripts\\patch_tier_r_2026_10_17.py --check
  python scripts\\patch_tier_r_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'TIER_R_2026_10_17'
NEEDS = {'scripts/translation_desk.py': 'TRANSLATION_DESK_2026_10_17', 'scripts/dashboard.py': 'BENCH_GOLD_FAIR_2026_10_17', 'scripts/dashboard_static.html': 'BUTTONS_2026_10_17'}
FILES = list(NEEDS)
TAG = 'tierr'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/translation_desk.py', 1, r'''MAX_USD = 12.0            # the most one press may spend (as the benchmarks' buttons)
''', r'''MAX_USD = 12.0            # the most one press may spend (as the benchmarks' buttons)
TIER_R_ENGINE = "anthropic:claude-sonnet-5-5"   # TIER_R_2026_10_17: the working English, Sonnet in one pass
TIER_R_PER_VERSE = 0.0052                        # $ a verse, BM1's measure (the Claude credit)
REF_RE = re.compile(r"^\d{1,4}(\.\d{1,4}){0,3}$")   # TIER_R_2026_10_17: a verse to begin at (81.1)
''')

edit('scripts/translation_desk.py', 2, r'''def scholar_argv(doc: str, step: str, pages: str = "", limit: int = STEP_VERSES, max_usd: float = 0.0,
                 held_ok: bool = False):
''', r'''def scholar_argv(doc: str, step: str, pages: str = "", limit: int = STEP_VERSES, max_usd: float = 0.0,
                 held_ok: bool = False, from_ref: str = ""):   # TIER_R_2026_10_17: from_ref
''')

edit('scripts/translation_desk.py', 3, r'''    if pages and not PAGES_RE.match(pages):
        return None, "pages: a page, a range or a list (2, or 1-3,5)"
''', r'''    if pages and not PAGES_RE.match(pages):
        return None, "pages: a page, a range or a list (2, or 1-3,5)"
    from_ref = str(from_ref or "").strip()   # TIER_R_2026_10_17
    if from_ref and not REF_RE.match(from_ref):
        return None, "begin at: a verse's reference (81.1)"
''')

edit('scripts/translation_desk.py', 4, r'''    argv = ["--doc", doc, "--limit", str(limit)] + (["--pages", pages] if pages else []) + list(SCHOLAR_SOP)
''', r'''    argv = ["--doc", doc, "--limit", str(limit)] + (["--pages", pages] if pages else []) + (
        ["--from-ref", from_ref] if from_ref else []) + list(SCHOLAR_SOP)
''')

edit('scripts/dashboard.py', 1, r'''    argv, why = td.scholar_argv(doc, step, data.get("pages") or "", data.get("limit") or td.STEP_VERSES,
                                data.get("max_usd") or 0, reg.get("status") == "in_repair")
''', r'''    argv, why = td.scholar_argv(doc, step, data.get("pages") or "", data.get("limit") or td.STEP_VERSES,
                                data.get("max_usd") or 0, reg.get("status") == "in_repair",
                                from_ref=str(data.get("from_ref") or ""))   # TIER_R_2026_10_17
''')

edit('scripts/dashboard.py', 2, r'''        ctl += ('<div class="row">Pages <input type="text" id="dkpages" placeholder="all" title="a page, a range or a list: '
                '2, or 1-3,5"> Verses <input''', r'''        ctl += ('<div class="row">Pages <input type="text" id="dkpages" placeholder="all" title="a page, a range or a list: '
                '2, or 1-3,5"> Begin at <input type="text" id="dkfrom" placeholder="the first" title="TIER_R_2026_10_17: a '
                'verse reference, as 81.1 (an e-text\'s numbering)" style="width:80px"> Verses <input''')

edit('scripts/dashboard.py', 3, r'''  var body = {doc: doc, step: step, pages: pages, limit: limit};
''', r'''  var body = {doc: doc, step: step, pages: pages, limit: limit, from_ref: (document.getElementById('dkfrom') || {}).value || ''};   /* TIER_R_2026_10_17 */
''')

edit('scripts/dashboard.py', 4, r'''async function deskTranslate(doc, btn){
  if (!confirm('The working English of ' + doc + ': one pass, gemini-2.5-flash, the verses not yet translated. Go?')) return;
  btn.disabled = true;
  var r = await fetch('/api/translate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({doc: doc, lang: 'en', limit: 0})});
''', r'''async function deskTranslate(doc, btn, engine, again){   /* TIER_R_2026_10_17: engine, again */
  var claude = !!engine && engine.indexOf('anthropic:') === 0;
  var ask = claude ? ('The working English of ' + doc + ' by Claude Sonnet 5.5 in one pass, ' + (again ? 'every verse again (the English before is kept in the history)' : 'the verses not yet translated') + '. It bills the Claude credit and stops when the credit does. Go?')
                   : ('The working English of ' + doc + ': one pass, gemini-2.5-flash, the verses not yet translated. Go?');
  if (!confirm(ask)) return;
  btn.disabled = true;
  var body = {doc: doc, lang: 'en', limit: 0};
  if (engine) body.engine = engine;
  if (again) body.retranslate = true;
  var r = await fetch('/api/translate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
''')

edit('scripts/dashboard.py', 5, r'''        and not r.get("guard") and r.get("held") not in td.HOLDS else ""))
    run = _desk_jobs(r["doc"])
''', r'''        and not r.get("guard") and r.get("held") not in td.HOLDS else ""))
    if not r.get("guard") and r.get("held") not in td.HOLDS and r["mula"]:   # TIER_R_2026_10_17
        _left = max(0, r["mula"] - r["en"])
        _cp = s.get("caps") or {}
        _cr = ("$%.2f left, until %s" % (_cp["credit_left"], str(_cp.get("credit_expires") or "?")[:10])
               if _cp.get("credit_left") is not None else "its state not read")
        _b = ""
        if _left:
            _b += ('<button class="btn dkbtn" onclick="deskTranslate(\'%s\', this, \'%s\', false)">The rest: %d verse(s), '
                   'about $%.2f</button> ' % (e(r["doc"], quote=True), td.TIER_R_ENGINE, _left, _left * td.TIER_R_PER_VERSE))
        if r["en"]:
            _b += ('<button class="btn dkbtn" onclick="deskTranslate(\'%s\', this, \'%s\', true)">Every verse again: %d, about '
                   '$%.2f (the English before is kept in the history)</button>' % (
                       e(r["doc"], quote=True), td.TIER_R_ENGINE, r["mula"], r["mula"] * td.TIER_R_PER_VERSE))
        h.append('<div class="box"><h3>The working English by Sonnet in one pass (Tier R)</h3><p class="small">BM1 (nearness '
                 'to published translations), BM3 (both judges) and BM2 (a person, blind) put Claude Sonnet 5.5 in one pass '
                 'above flash for the working English, at about its price ($%.4f a verse, BM1). It bills the Claude credit '
                 '(%s) and stops when the credit does. English only; one text at a time; MT_ENGINE stays flash.</p>'
                 '<div class="row">%s</div></div>' % (td.TIER_R_PER_VERSE, e(_cr), _b))
    run = _desk_jobs(r["doc"])
''')

edit('scripts/dashboard.py', 6, r'''             "--min-quality", min_quality) + _win
    kind = "translate"
''', r'''             "--min-quality", min_quality) + _win
    if data.get("retranslate"):   # TIER_R_2026_10_17: every verse again; the English before goes to translation_history
        cmd.append("--retranslate")
    kind = "translate"
''')

edit('scripts/dashboard_static.html', 1, r'''        <option value="openai:gpt-4o-mini">&#x1F535; GPT-4o-mini (cheap)</option>
''', r'''        <option value="openai:gpt-4o-mini">&#x1F535; GPT-4o-mini (cheap)</option>
        <option value="anthropic:claude-sonnet-5-5" title="TIER_R_2026_10_17: the working English by Claude Sonnet 5.5 in one pass (BM1, BM3, BM2); it bills the Claude credit; one text at a time">&#9670; Claude Sonnet 5.5, one pass (Tier R; the Claude credit)</option>
''')

edit('scripts/dashboard_static.html', 2, r'''          '<option value="openai:gpt-4o">''', r'''          '<option value="anthropic:claude-sonnet-5-5" title="Tier R: the Claude credit">&#9670; Sonnet</option>' +   // TIER_R_2026_10_17
          '<option value="openai:gpt-4o">''')

edit('scripts/dashboard_static.html', 3, r'''    if (!docs.length) { toast('No documents loaded', 'fail'); return; }
''', r'''    if (!docs.length) { toast('No documents loaded', 'fail'); return; }
    var _cl = docs.filter(function(d) { return String(getEngine(d) || '').indexOf('anthropic:') === 0; });   // TIER_R_2026_10_17
    if (_cl.length) { toast('Translate All does not run Claude (' + _cl.length + ' text(s) would): one text at a time, from its row or the desk, as the credit is spent verse by verse.', 'fail'); return; }
''')


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
    print('  python -m unittest tests.test_tier_r_2026_10_17')
    print('  .\\scripts\\restart_dashboard.ps1 -Status   (then restart it when idle: the page needs the new server)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
