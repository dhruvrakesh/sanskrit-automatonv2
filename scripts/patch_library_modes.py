#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_library_modes.py  (2026-09-13)  LIBRARY_MODES_2026_09_13

Block Y gave every language composition its own Booksmith project, because
Booksmith's model is one project = one witness and sharing a project between
modes is what made a Hindi re-export collide with a frozen trilingual
manifest:

    ValueError: Frozen manifest is stale; refreeze after changes to:
                source_sha256, release_identity

That fixed the build. It did not fix the Library, which still assumes one
project and one PDF per text. Two consequences, both observable today:

  1. A -hi or -en edition builds correctly into
     <slug>-hi / <slug>-en and then gets NO link on its Library card,
     because _bs_pdf_path() only ever looks in the bare trilingual slug.
     The user sees a build succeed and nothing appear. That is the
     "single language imports not working" report.

  2. booksmith_build.py writes its sidecar to exports/booksmith/<doc>.json
     with no mode in the name, so a Hindi build overwrites the trilingual
     build's account of itself. The card's "reading edition blocked"
     warning then describes whichever mode ran last. The six sidecars on
     disk right now are all bare names, and two of them were rewritten at
     14:57 today by the two rebuilds that failed.

This patch closes both, and changes nothing else.

  booksmith_build.py  (1 anchor)
    sidecar path follows the SAME rule as slug_for(): tri keeps the bare
    name, en and hi are suffixed. The six sidecars written before today are
    all trilingual, so they keep resolving untouched.

  dashboard.py  (7 anchors)
    BOOKSMITH_MODES_ORDER / BOOKSMITH_MODE_LABEL  - display order and names
    _bs_mode_slug(doc, mode)   - mirrors slug_for(doc, mode) exactly
    _bs_slug(doc)              - kept, now defined as the tri case
    _bs_pdf_path(doc, mode=None) - arity preserved; scans tri, hi, en
    _bs_variants(doc)          - every edition that exists on disk
    _bs_sidecar(doc, mode)     - mode-aware sidecar read
    _bs_state_one              - adds variants[]; flat keys still tri
    /api/booksmith/pdf/<doc>   - accepts ?mode=; unknown mode is a 400
    bsRender()                 - one row of links per edition, not one link
                                 for whichever edition built last

Design decisions worth defending:

  * An unknown ?mode= is a 400, not a silent fall back to trilingual.
    Handing someone the wrong language is worse than an error.

  * _bs_pdf_path keeps its 2-tuple return and its old behaviour when no
    mode is passed, so both existing callers keep working and a text that
    has only ever had a trilingual build renders exactly as it did before.

  * The flat project/ui/pdf/last keys stay in the state payload pointing at
    the trilingual edition. variants[] is additive. Nothing that reads this
    endpoint has to change at once.

  * The JS keeps a fallback path for a server that predates this change, so
    a half-updated deployment degrades to today's behaviour instead of a
    blank card.

Usage
    python scripts\\patch_library_modes.py --check     # report, write nothing
    python scripts\\patch_library_modes.py             # apply
    python scripts\\patch_library_modes.py --verify    # post-apply guards

Line endings are detected per file and preserved. dashboard.py is pure CRLF
and must stay that way; read_text + write_text(newline="\\n") would silently
rewrite all 2,987 lines and bury this change in the diff.
"""

import argparse
import importlib.util
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path

MARK = "LIBRARY_MODES_2026_09_13"
NEEDS = "BOOKSMITH_MODES_2026_09_13"          # Block Y must have run first

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "scripts" / "dashboard.py"
BUILD = ROOT / "scripts" / "booksmith_build.py"


# ─────────────────────────────────────────────────────────────────────────
# line-ending discipline
# ─────────────────────────────────────────────────────────────────────────
def read_src(p: Path):
    """Return (text_with_LF, newline) so the file can be written back in the
    ending it actually had."""
    raw = p.read_bytes()
    s = raw.decode("utf-8")
    crlf = s.count("\r\n")
    lf = s.count("\n")
    nl = "\r\n" if crlf and crlf == lf else "\n"
    if crlf and crlf != lf:
        raise SystemExit(
            "FAIL: %s has mixed line endings (%d CRLF of %d LF). Refusing to "
            "guess." % (p.name, crlf, lf))
    return s.replace("\r\n", "\n"), nl


def write_src(p: Path, text_lf: str, nl: str) -> None:
    p.write_bytes(text_lf.replace("\n", nl).encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────
# anchors.  Every one is newline-prefixed: a 4-space-indented line is a
# substring of its 8-space sibling, and that collision has bitten before.
# ─────────────────────────────────────────────────────────────────────────

SIDECAR_OLD = r'''
    sidecar = sidecar_dir / ("%s.json" % doc)
'''

SIDECAR_NEW = r'''
    # LIBRARY_MODES_2026_09_13 - one sidecar per witness, not per doc code.
    # slug_for() suffixes en and hi and leaves tri bare; the sidecar follows
    # the same rule, so a Hindi build can no longer overwrite the trilingual
    # card's account of itself. Every sidecar written before today is
    # trilingual and keeps resolving under its bare name.
    sidecar = sidecar_dir / (("%s.json" % doc) if args.mode == "tri"
                             else ("%s__%s.json" % (doc, args.mode)))
'''

MODES_OLD = r'''
BOOKSMITH_MODES = ("tri", "en", "hi")
'''

MODES_NEW = r'''
BOOKSMITH_MODES = ("tri", "en", "hi")
# LIBRARY_MODES_2026_09_13 - display order on a Library card, and what each
# edition is called there. tri comes first because every project created
# before 2026-09-13 is trilingual, so a text that has only ever had one
# build looks exactly as it did.
BOOKSMITH_MODES_ORDER = ("tri", "hi", "en")
BOOKSMITH_MODE_LABEL = {"tri": "Trilingual", "hi": "Hindi", "en": "English"}
'''

SLUG_OLD = r'''
def _bs_slug(doc: str) -> str:
    """Must agree with slug_for() in booksmith_build.py. Verified against the
    six projects created by hand: harita_caturtha_sthanam ->
    harita-caturtha-sthanam, and so on for all six."""
    s = re.sub(r"[^a-z0-9_-]+", "-", (doc or "").strip().lower().replace("_", "-"))
    return re.sub(r"-{2,}", "-", s).strip("-")[:64]
'''

SLUG_NEW = r'''
# LIBRARY_MODES_2026_09_13
def _bs_mode_slug(doc: str, mode: str = "tri") -> str:
    """Must agree with slug_for(doc, mode) in booksmith_build.py, which since
    BOOKSMITH_MODES_2026_09_13 gives every language composition its own
    project - one project = one witness. tri keeps the bare slug so the
    projects created by hand on 2026-09-08 continue to resolve; en and hi are
    suffixed. The steps below are in the same order as there, and truncation
    happens before the suffix, so the two agree on over-long doc codes too.
    --verify checks that agreement against the real function."""
    s = (doc or "").strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    suffix = "" if mode == "tri" else ("-" + mode)
    return s[: 64 - len(suffix)] + suffix


def _bs_slug(doc: str) -> str:
    """The trilingual project id - the name every existing caller uses."""
    return _bs_mode_slug(doc, "tri")
'''

PDF_OLD = r'''
def _bs_pdf_path(doc: str):
    """The PDF for a doc, preferring the full audit build over the sampled
    layout proof. Returns (path, kind) or (None, None)."""
    project = BOOKSMITH_ROOT / "projects" / _bs_slug(doc)
    for name, kind in (("book.pdf", "book"), ("layout-proof.pdf", "proof")):
        p = project / "build" / name
        if p.exists():
            return p, kind
    return None, None
'''

PDF_NEW = r'''
# LIBRARY_MODES_2026_09_13
def _bs_pdf_path(doc: str, mode=None):
    """The PDF for a doc, preferring the full audit build over the sampled
    layout proof. With mode given, looks only in that edition's project;
    without, scans tri, hi, en in that order, so a text that has only ever
    had a trilingual build answers exactly as it did before today.
    Returns (path, kind) or (None, None) - arity deliberately unchanged."""
    modes = (mode,) if mode else BOOKSMITH_MODES_ORDER
    for m in modes:
        project = BOOKSMITH_ROOT / "projects" / _bs_mode_slug(doc, m)
        for name, kind in (("book.pdf", "book"), ("layout-proof.pdf", "proof")):
            p = project / "build" / name
            if p.exists():
                return p, kind
    return None, None


def _bs_sidecar(doc: str, mode: str = "tri"):
    """The last build's own account of itself, or None. Mode-aware since
    LIBRARY_MODES_2026_09_13; the bare name is the trilingual one."""
    name = ("%s.json" % doc) if mode == "tri" else ("%s__%s.json" % (doc, mode))
    p = ROOT / "exports" / "booksmith" / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _bs_variants(doc: str) -> list:
    """Every edition of this text that exists on disk. A project counts once
    it has a book.yaml; a download is offered once it also has a PDF. This is
    what lets one Library card carry a trilingual and a Hindi edition side by
    side instead of the second one being invisible."""
    out = []
    for m in BOOKSMITH_MODES_ORDER:
        slug = _bs_mode_slug(doc, m)
        project = BOOKSMITH_ROOT / "projects" / slug
        if not (project / "book.yaml").exists():
            continue
        v = {"mode": m, "slug": slug, "label": BOOKSMITH_MODE_LABEL[m],
             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}
        pdf, kind = _bs_pdf_path(doc, m)
        if pdf:
            st = pdf.stat()
            v["pdf"] = {"kind": kind, "bytes": st.st_size,
                        "mtime": time.strftime("%Y-%m-%d %H:%M",
                                               time.localtime(st.st_mtime))}
        side = _bs_sidecar(doc, m)
        if side is not None:
            v["last"] = side
        out.append(v)
    return out
'''

STATE_OLD = r'''
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
'''

STATE_NEW = r'''
# LIBRARY_MODES_2026_09_13
def _bs_state_one(doc: str) -> dict:
    """One Library card's Booksmith state. variants[] is the new truth - one
    entry per edition that exists on disk. The flat project/ui/pdf/last keys
    are kept, pointing at the trilingual edition, so nothing that reads this
    endpoint has to change at the same moment."""
    slug = _bs_slug(doc)
    project = BOOKSMITH_ROOT / "projects" / slug
    state = {"doc": doc, "slug": slug, "variants": _bs_variants(doc),
             "project": project.exists() and (project / "book.yaml").exists(),
             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}
    side = _bs_sidecar(doc, "tri")
    if side is not None:
        state["last"] = side
    pdf, kind = _bs_pdf_path(doc)
'''

ROUTE_OLD = r'''
@app.get("/api/booksmith/pdf/<doc>")
def api_booksmith_pdf(doc):
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    pdf, kind = _bs_pdf_path(doc)
    if not pdf:
        return jsonify({"error": "no PDF built yet for this text"}), 404
'''

ROUTE_NEW = r'''
@app.get("/api/booksmith/pdf/<doc>")
def api_booksmith_pdf(doc):
    doc = _validate_doc(doc)
    if not doc:
        return jsonify({"error": "invalid doc"}), 400
    # LIBRARY_MODES_2026_09_13 - ?mode=tri|en|hi picks the edition. Without
    # it the old behaviour stands: the first edition that has a PDF, tri
    # first. An unknown mode is a 400 rather than a quiet fall back to
    # trilingual - handing someone the wrong language is worse than an error.
    mode = (request.args.get("mode") or "").strip()
    if mode and mode not in BOOKSMITH_MODES:
        return jsonify({"error": f"mode must be one of {BOOKSMITH_MODES}"}), 400
    pdf, kind = _bs_pdf_path(doc, mode or None)
    if not pdf:
        return jsonify({"error": "no PDF built yet for this text"
                                 + (f" in mode {mode}" if mode else "")}), 404
'''

NAME_OLD = r'''
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{doc}_{kind}") + ".pdf"
'''

NAME_NEW = r'''
    # LIBRARY_MODES_2026_09_13 - the language belongs in the filename, or a
    # folder of downloads becomes three files that cannot be told apart.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_",
                  f"{doc}_{mode or 'tri'}_{kind}") + ".pdf"
'''

JS_OLD = r'''
function bsRender(s){{
  var el=document.getElementById('bs-'+s.doc);
  if(!el) return;
  var h='';
  if(s.job){{ h+='<span class="busy">building\u2026</span>'; }}
  if(s.pdf){{
    var kb=Math.round(s.pdf.bytes/1024);
    var label = s.pdf.kind==='book' ? 'Download PDF' : 'Download layout proof';
    h+='<a class="pdf" href="/api/booksmith/pdf/'+encodeURIComponent(s.doc)+'" '+
       'title="'+kb+' KB, built '+s.pdf.mtime+'">\u2b07 '+label+'</a>';
  }}
  if(s.project){{
    h+='<a class="bsui" target="_blank" rel="noopener" href="'+s.ui+'" '+
       'title="Open this project in Booksmith to review findings and build the reading edition">Booksmith \u2197</a>';
  }}
  if(s.last && s.last.blocked){{
    h+='<span class="warn" title="'+(s.last.blockers||[]).join(' ').replace(/"/g,'')+
       '">reading edition blocked</span>';
  }}
  el.innerHTML=h;
}}
'''

JS_NEW = r'''
function bsRender(s){{
  var el=document.getElementById('bs-'+s.doc);
  if(!el) return;
  var h='';
  if(s.job){{ h+='<span class="busy">building\u2026</span>'; }}
  // LIBRARY_MODES_2026_09_13 - one set of links per edition that exists,
  // instead of one link for whichever edition happened to build last. A
  // server from before this change sends no variants[]; render what it used
  // to rather than a blank card.
  var vs=(s.variants&&s.variants.length)?s.variants:null;
  if(!vs){{
    vs=[];
    if(s.pdf||s.project){{
      vs.push({{mode:'tri',label:'Trilingual',ui:s.ui,pdf:s.pdf,last:s.last}});
    }}
  }}
  var many=vs.length>1;
  vs.forEach(function(v){{
    if(v.pdf){{
      var kb=Math.round(v.pdf.bytes/1024);
      var what=(v.pdf.kind==='book')?'PDF':'layout proof';
      h+='<a class="pdf" href="/api/booksmith/pdf/'+encodeURIComponent(s.doc)+
         '?mode='+encodeURIComponent(v.mode)+'" '+
         'title="'+v.label+' '+what+', '+kb+' KB, built '+v.pdf.mtime+'">'+
         '\u2b07 '+v.label+' '+what+'</a>';
    }}
    h+='<a class="bsui" target="_blank" rel="noopener" href="'+v.ui+'" '+
       'title="Open the '+v.label+' project in Booksmith to '+
       'review findings and build the reading edition">Booksmith \u2197'+
       (many?(' '+v.mode):'')+'</a>';
    if(v.last && v.last.blocked){{
      h+='<span class="warn" title="'+v.label+': '+
         (v.last.blockers||[]).join(' ').replace(/"/g,'')+'">'+
         (many?(v.label+' '):'')+'reading edition blocked</span>';
    }}
  }});
  el.innerHTML=h;
}}
'''

# (old, new, file, human name)
PATCHES = [
    (SIDECAR_OLD, SIDECAR_NEW, "build", "sidecar path is mode-aware"),
    (MODES_OLD, MODES_NEW, "dash", "mode display order and labels"),
    (SLUG_OLD, SLUG_NEW, "dash", "_bs_mode_slug mirrors slug_for"),
    (PDF_OLD, PDF_NEW, "dash", "_bs_pdf_path takes a mode; variants; sidecar"),
    (STATE_OLD, STATE_NEW, "dash", "_bs_state_one carries variants[]"),
    (ROUTE_OLD, ROUTE_NEW, "dash", "pdf route accepts ?mode="),
    (NAME_OLD, NAME_NEW, "dash", "download filename carries the language"),
    (JS_OLD, JS_NEW, "dash", "card renders one row per edition"),
]


# ─────────────────────────────────────────────────────────────────────────
def brace_runs_even(text: str) -> bool:
    """Inside the Library page f-string every literal brace is doubled. A
    single stray brace would become a format field - and `{mode:'tri'}` is a
    perfectly valid Python dict display, so py_compile would NOT catch it.
    Check the doubling directly."""
    for ch in "{}":
        for m in re.finditer(re.escape(ch) + "+", text):
            if len(m.group(0)) % 2:
                return False
    return True


def check(apply: bool) -> int:
    if not DASH.exists() or not BUILD.exists():
        print("FAIL: run this from the repo - scripts/dashboard.py and "
              "scripts/booksmith_build.py must both exist.")
        return 2

    dash, dash_nl = read_src(DASH)
    build, build_nl = read_src(BUILD)

    if MARK in dash or MARK in build:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if NEEDS not in build:
        print("FAIL: this patch builds on %s (Block Y), which has not been "
              "applied to scripts/booksmith_build.py yet." % NEEDS)
        print("      Run block_Y_booksmith_modes.ps1 first, then this.")
        return 2

    if not brace_runs_even(JS_NEW):
        print("FAIL: the replacement JS has an odd run of braces - it would "
              "become an f-string format field. Refusing to write.")
        return 2

    bodies = {"dash": dash, "build": build}
    ok = True
    print("anchor                                        file  found")
    print("-" * 62)
    for old, new, which, name in PATCHES:
        n = bodies[which].count(old)
        flag = "OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)
        print("%-45s %-5s %s" % (name[:45], which, flag))
        if n != 1:
            ok = False
    print("-" * 62)
    if not ok:
        print("FAIL: every anchor must match exactly once. Nothing written.")
        return 2
    if not apply:
        print("--check only: all %d anchors matched. Nothing written."
              % len(PATCHES))
        return 0

    # Count again at replacement time, not only before the loop. An earlier
    # replacement could in principle destroy a later anchor, and .replace()
    # would then silently do nothing - which is exactly how --keep-frontmatter
    # shipped inert on 2026-09-13.
    for old, new, which, name in PATCHES:
        n = bodies[which].count(old)
        if n != 1:
            print("FAIL: anchor %r matched %d times at apply time (an earlier "
                  "edit disturbed it). Nothing written." % (name, n))
            return 2
        bodies[which] = bodies[which].replace(old, new, 1)
        if new.strip() not in bodies[which]:
            print("FAIL: replacement for %r did not land. Nothing written."
                  % name)
            return 2

    # Compile both before either lands on disk.
    for which, path, text, nl in (("dash", DASH, bodies["dash"], dash_nl),
                                  ("build", BUILD, bodies["build"], build_nl)):
        fd, tmp = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        Path(tmp).write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(tmp, cfile=tmp + "c", doraise=True)
        except py_compile.PyCompileError as e:
            print("FAIL: patched %s does not compile:\n%s" % (path.name, e))
            return 2
        finally:
            for f in (tmp, tmp + "c"):
                try:
                    os.remove(f)
                except OSError:
                    pass

    write_src(DASH, bodies["dash"], dash_nl)
    write_src(BUILD, bodies["build"], build_nl)
    print("Patched scripts/dashboard.py      (%s endings preserved)"
          % ("CRLF" if dash_nl == "\r\n" else "LF"))
    print("Patched scripts/booksmith_build.py (%s endings preserved)"
          % ("CRLF" if build_nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    return 0


# ─────────────────────────────────────────────────────────────────────────
def verify() -> int:
    """Post-apply guards that observe rather than assert presence."""
    rc = 0
    dash, dash_nl = read_src(DASH)
    build, build_nl = read_src(BUILD)

    def say(name, good, detail=""):
        nonlocal rc
        print("  [%s] %s%s" % ("PASS" if good else "FAIL", name,
                               ("  - " + detail) if detail else ""))
        if not good:
            rc = 1

    print("guards")
    say("marker in dashboard.py", MARK in dash)
    say("marker in booksmith_build.py", MARK in build)
    say("dashboard.py still pure CRLF", dash_nl == "\r\n",
        "got %s" % ("CRLF" if dash_nl == "\r\n" else "LF"))

    # 1. the f-string braces are still doubled everywhere in the JS region
    i = dash.find("function bsRender(s)")
    j = dash.find("var BS_TIMER", i)
    say("Library page braces still doubled", i > 0 and j > i
        and brace_runs_even(dash[i:j]))

    # 2. _bs_mode_slug and slug_for agree - executed, not eyeballed
    m = re.search(r"\ndef _bs_mode_slug\(.*?\n    return s\[: 64 - len\(suffix\)\] \+ suffix\n",
                  dash, re.S)
    if not m:
        say("_bs_mode_slug extractable", False)
        return rc
    ns = {"re": re}
    exec(m.group(0), ns)
    mine = ns["_bs_mode_slug"]

    spec = importlib.util.spec_from_file_location("_bsbuild", BUILD)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        say("booksmith_build.py importable", False, repr(e)[:120])
        return rc
    theirs = getattr(mod, "slug_for", None)
    if theirs is None:
        say("slug_for present", False)
        return rc

    docs = ["nilamata_seg", "AphorismsOfSandilya",
            "2015_405693_Shatpath-Brahmanam", "MBh01",
            "harita_pancamam_kalpa_sthanam", "harita_caturtha_sthanam",
            "shukla yajur veda", "Bodhicaryavatara", "a", "A--B__C",
            "x" * 80, "x" * 63, "x" * 64]
    bad = []
    for d in docs:
        for md in ("tri", "hi", "en"):
            a, b = mine(d, md), theirs(d, md)
            if a != b:
                bad.append("%r/%s: dashboard=%r build=%r" % (d[:24], md, a, b))
    say("slug agreement over %d doc/mode pairs" % (len(docs) * 3), not bad,
        bad[0] if bad else "")

    # 3. the seven projects created by hand still resolve under tri
    known = ["nilamata_seg", "AphorismsOfSandilya",
             "2015_405693_Shatpath-Brahmanam", "harita_caturtha_sthanam",
             "harita_dvitiya_sthanam", "harita_tritiya_sthanam",
             "harita_prathama_sthanam", "harita_pancamam_kalpa_sthanam"]
    expect = {"nilamata_seg": "nilamata-seg",
              "AphorismsOfSandilya": "aphorismsofsandilya",
              "2015_405693_Shatpath-Brahmanam": "2015-405693-shatpath-brahmanam",
              "harita_caturtha_sthanam": "harita-caturtha-sthanam",
              "harita_dvitiya_sthanam": "harita-dvitiya-sthanam",
              "harita_tritiya_sthanam": "harita-tritiya-sthanam",
              "harita_prathama_sthanam": "harita-prathama-sthanam",
              "harita_pancamam_kalpa_sthanam": "harita-pancamam-kalpa-sthanam"}
    wrong = [d for d in known if mine(d, "tri") != expect[d]]
    say("existing projects still resolve under tri", not wrong,
        ",".join(wrong))

    # 4. the mode suffix actually differs
    say("hi and en get their own project ids",
        mine("nilamata_seg", "hi") == "nilamata-seg-hi"
        and mine("nilamata_seg", "en") == "nilamata-seg-en")

    # 5. the sidecar rule matches on both sides of the bridge
    say("sidecar rule is stated in both files",
        '"%s__%s.json" % (doc, args.mode)' in build
        and '("%s__%s.json" % (doc, mode))' in dash)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report anchor matches, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run post-apply guards")
    a = ap.parse_args()
    if a.verify:
        return verify()
    return check(apply=not a.check)


if __name__ == "__main__":
    sys.exit(main())
