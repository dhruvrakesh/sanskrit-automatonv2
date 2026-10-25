#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_prose_edition_2026_10_25.py  (2026-10-25)  PROSE_EDITION_2026_10_25

The scholarly editions read as prose, for everyone (asked on 25 Oct: "why isnt scholary and prose available on
srangam?"): the desk's /scholar/<doc>/prose as a static page beside each edition on Srangam.

  scripts\\export_html.py      --scholar --prose: the scholarly edition read as prose: no Sanskrit, the verse numbers
                               small, a sentence over verses whole after its range, a paragraph where a speaker begins
                               (or after eight verses), the chapter's notes at its end; the chapters, the daggers and
                               the title page are the edition's own (file name gains _prose; never overwrites the
                               verse edition). --prose without --scholar is refused
  scripts\\publish_editions.py each edition is also written as public/scholarly/<slug>-prose.html, each page's bar
                               linking the other; the index gives "prose", its size and digest; "prose": false in an
                               entry keeps it out. The verse editions are written once more (their bar gains the link)
  tests\\test_publish_editions_2026_10_18.py   the plan now writes 3 files (the edition, its prose, the index)

Needs EDITION_REFS_2026_10_18 in export_html.py and EDITIONS_SITE_2026_10_18 in publish_editions.py and its test.
Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_proseedition_<date> copy of each file; the .py
files compiled before anything is written. Test: tests\\test_prose_edition_2026_10_25.py.

  python scripts\\patch_prose_edition_2026_10_25.py --check
  python scripts\\patch_prose_edition_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'PROSE_EDITION_2026_10_25'
TAG = 'proseedition'
FILES = ['scripts/export_html.py', 'scripts/publish_editions.py', 'tests/test_publish_editions_2026_10_18.py']
NEEDS = {'scripts/export_html.py': 'EDITION_REFS_2026_10_18', 'scripts/publish_editions.py': 'EDITIONS_SITE_2026_10_18', 'tests/test_publish_editions_2026_10_18.py': 'EDITIONS_SITE_2026_10_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/export_html.py', 1, 'def _render(doc, recs, prov, *, include_san, include_en, include_hi, hi_label,\n            side_by_side, number_pages, drop_junk_en, want_toc=True, want_footnotes=True,\n            title=None, figures=None):   # EXPORT_IMAGES_2026_10_04: figures\n    # Group into ordered sections.\n    sections = OrderedDict()',
     'def _render(doc, recs, prov, *, include_san, include_en, include_hi, hi_label,\n            side_by_side, number_pages, drop_junk_en, want_toc=True, want_footnotes=True,\n            title=None, figures=None, prose=False):   # EXPORT_IMAGES_2026_10_04: figures; PROSE_EDITION_2026_10_25: prose\n    # Group into ordered sections.\n    sections = OrderedDict()')

edit('scripts/export_html.py', 2, '        subtitle = "The scholarly English" + (", with the Sanskrit" if include_san else "") + (\n            " and the working " + hi_label if include_hi else "")\n    out.append("<div class=\'titlepage\'>")\n    out.append(f"<h1>{html.escape(disp_title)}</h1>")',
     '        subtitle = "The scholarly English" + (", with the Sanskrit" if include_san else "") + (\n            " and the working " + hi_label if include_hi else "")\n        if prose:   # PROSE_EDITION_2026_10_25\n            subtitle = "The scholarly English, read as prose"\n    out.append("<div class=\'titlepage\'>")\n    out.append(f"<h1>{html.escape(disp_title)}</h1>")')

edit('scripts/export_html.py', 3, '        out.append(f"<h2>{html.escape(label)}</h2>")\n        fn_counter = [0]; fn_notes: List[Tuple[int,str]] = []\n        for r in rows:\n            san = (r["san"] or "").strip()',
     '        out.append(f"<h2>{html.escape(label)}</h2>")\n        fn_counter = [0]; fn_notes: List[Tuple[int,str]] = []\n        paras, cur_p = [], []   # PROSE_EDITION_2026_10_25\n        for r in rows:\n            san = (r["san"] or "").strip()')

edit('scripts/export_html.py', 4, "                # they share the section's footnote numbering with English.\n                return _extract_footnotes(base, fn_counter, fn_notes) if want_footnotes else base\n            if side_by_side:\n                cols = []",
     '                # they share the section\'s footnote numbering with English.\n                return _extract_footnotes(base, fn_counter, fn_notes) if want_footnotes else base\n            if prose:   # PROSE_EDITION_2026_10_25: the verses run on as a book\'s paragraphs, a speaker opening one\n                sch_ = r.get("sch")\n                if not (include_en and en) or (sch_ or {}).get("with"):\n                    continue\n                num = str(vref).split(".")[-1] if vlabel else ""   # a line without a reference has no number\n                if sch_ is not None and sch_.get("range"):\n                    num = str(sch_["range"]).split(".")[-1]\n                    sch_ = dict(sch_, range="")\n                body_ = (_sch_en_html(en, sch_, fn_counter, fn_notes, want_footnotes) if sch_ is not None\n                         else _inline_format(html.escape(en)))\n                if cur_p and (_PROSE_SPEECH.match(en) or len(cur_p) >= 8):\n                    paras.append(cur_p)\n                    cur_p = []\n                cur_p.append(("<span class=\'vr\'>%s</span>" % html.escape(num) if num else "") + body_)\n                kept += 1\n                continue\n            if side_by_side:\n                cols = []')

edit('scripts/export_html.py', 5, '                    _fg["_late"] = True\n                    out.append(_figure_html(_fg, include_en, include_hi))\n        # footnotes for this section\n        if want_footnotes and fn_notes:',
     '                    _fg["_late"] = True\n                    out.append(_figure_html(_fg, include_en, include_hi))\n        if prose:   # PROSE_EDITION_2026_10_25\n            if cur_p:\n                paras.append(cur_p)\n            out.extend("<p class=\'prose\'>%s</p>" % " ".join(p_) for p_ in paras)\n        # footnotes for this section\n        if want_footnotes and fn_notes:')

edit('scripts/export_html.py', 6, '\n\ndef _sch_meth(stats: dict) -> str:\n    """The title page\'s methodology, for the scholarly edition."""',
     '\n\n# PROSE_EDITION_2026_10_25: the scholarly edition read as prose (--scholar --prose), as the desk\'s /scholar/<doc>/prose\n# reads it: no Sanskrit, the verse numbers small, a sentence over verses whole, a paragraph where a speaker begins (or\n# after eight verses), the chapter\'s notes at its end; the chapters, the notes, the daggers and the title page are the\n# edition\'s own.\n_PROSE_CSS = ("p.prose { text-align: justify; line-height: 1.9; margin: 0 0 1.1rem; }"\n              "p.prose .vr { font-size: .62rem; color: var(--muted); vertical-align: super; margin: 0 .2em 0 .15em; "\n              "font-family: \'JetBrains Mono\',ui-monospace,monospace; }")\n_PROSE_SPEECH = re.compile(r"^[A-Z][^.:;]{0,60} said:")   # scholar_translate.py _SPEECH\n\n\ndef _sch_meth(stats: dict) -> str:\n    """The title page\'s methodology, for the scholarly edition."""')

edit('scripts/export_html.py', 7, '                side_by_side, number_pages, drop_junk_en, force_san, force_en,\n                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False,\n                keep_frontmatter=False, images="none", scholar=False):   # SCHOLAR_EDITION_2026_10_17: scholar\n    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07\n    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)',
     '                side_by_side, number_pages, drop_junk_en, force_san, force_en,\n                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False,\n                keep_frontmatter=False, images="none", scholar=False,\n                prose=False):   # SCHOLAR_EDITION_2026_10_17: scholar; PROSE_EDITION_2026_10_25: prose\n    title = _display_title(title, doc)   # EXPORT_EMPTY_2026_10_07\n    san_col, en_col = _detect_cols(con, doc, force_san, force_en, debug=debug)')

edit('scripts/export_html.py', 8, '                         number_pages=number_pages, drop_junk_en=drop_junk_en,\n                         want_toc=want_toc, want_footnotes=want_footnotes, title=title,\n                         figures=_fig_copy(figs) if figs else None)\n    if kept == 0 and include_en and not include_san and drop_junk_en:\n        body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,\n                          include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,\n                          number_pages=number_pages, drop_junk_en=False,\n                          want_toc=want_toc, want_footnotes=want_footnotes, title=title,\n                         figures=_fig_copy(figs) if figs else None)\n    os.makedirs(dest, exist_ok=True)\n    suffix = f"_{hi_lang}" if (include_hi and not include_en) else ("_tri" if include_hi else "")\n    if scholar:   # SCHOLAR_EDITION_2026_10_17: never overwrite the working edition\n        suffix += "_scholar"\n    if images == "approved":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition\n        suffix += "_img"',
     '                         number_pages=number_pages, drop_junk_en=drop_junk_en,\n                         want_toc=want_toc, want_footnotes=want_footnotes, title=title,\n                         figures=_fig_copy(figs) if figs else None, prose=prose)\n    if kept == 0 and include_en and not include_san and drop_junk_en:\n        body, kept = _render(doc, recs, prov, include_san=include_san, include_en=include_en,\n                          include_hi=include_hi, hi_label=hi_label, side_by_side=side_by_side,\n                          number_pages=number_pages, drop_junk_en=False,\n                          want_toc=want_toc, want_footnotes=want_footnotes, title=title,\n                         figures=_fig_copy(figs) if figs else None, prose=prose)\n    os.makedirs(dest, exist_ok=True)\n    suffix = f"_{hi_lang}" if (include_hi and not include_en) else ("_tri" if include_hi else "")\n    if scholar:   # SCHOLAR_EDITION_2026_10_17: never overwrite the working edition\n        suffix += "_scholar"\n    if prose:   # PROSE_EDITION_2026_10_25: never overwrite the verse edition\n        suffix += "_prose"\n    if images == "approved":   # EXPORT_IMAGES_2026_10_04: never overwrite the plain edition\n        suffix += "_img"')

edit('scripts/export_html.py', 9, '        if scholar:   # SCHOLAR_EDITION_2026_10_17\n            _doc_html = _doc_html.replace("</style>", _SCH_CSS + "</style>", 1)\n        f.write(_doc_html)\n    if images == "approved":   # EXPORT_IMAGES_2026_10_04',
     '        if scholar:   # SCHOLAR_EDITION_2026_10_17\n            _doc_html = _doc_html.replace("</style>", _SCH_CSS + "</style>", 1)\n        if prose:   # PROSE_EDITION_2026_10_25\n            _doc_html = _doc_html.replace("</style>", _PROSE_CSS + "</style>", 1)\n        f.write(_doc_html)\n    if images == "approved":   # EXPORT_IMAGES_2026_10_04')

edit('scripts/export_html.py', 10, '                         "place of the working English, which stands, marked, where there is none (file name "\n                         "gains _scholar)")\n    ap.add_argument("--debug", action="store_true")\n    args = ap.parse_args()\n\n    hi_lang = None; hi_label = "Hindi"\n    if args.hindi or args.hindi_only:\n        hi_lang = (args.lang or "hi").strip()\n        hi_label = "\u0939\u093f\u0928\u094d\u0926\u0940" if hi_lang == "hi" else hi_lang\n    include_san = bool(args.sanskrit and not args.no_sanskrit)\n    include_en  = not args.hindi_only\n    side_by_side = bool(args.side_by_side and (include_san or (hi_lang and include_en)))',
     '                         "place of the working English, which stands, marked, where there is none (file name "\n                         "gains _scholar)")\n    ap.add_argument("--prose", action="store_true",\n                    help="PROSE_EDITION_2026_10_25: with --scholar, the scholarly English read as prose: no Sanskrit, "\n                         "the verse numbers small, the notes at each chapter\'s end (file name gains _prose)")\n    ap.add_argument("--debug", action="store_true")\n    args = ap.parse_args()\n    if args.prose and not args.scholar:   # PROSE_EDITION_2026_10_25\n        raise SystemExit("--prose reads the scholarly English: give --scholar too")\n\n    hi_lang = None; hi_label = "Hindi"\n    if args.hindi or args.hindi_only:\n        hi_lang = (args.lang or "hi").strip()\n        hi_label = "\u0939\u093f\u0928\u094d\u0926\u0940" if hi_lang == "hi" else hi_lang\n    include_san = bool(args.sanskrit and not args.no_sanskrit) and not args.prose   # PROSE_EDITION_2026_10_25\n    include_en  = not args.hindi_only\n    side_by_side = bool(args.side_by_side and (include_san or (hi_lang and include_en)))')

edit('scripts/export_html.py', 11, '                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,\n                            keep_frontmatter=args.keep_frontmatter, images=args.images,\n                            scholar=args.scholar)   # SCHOLAR_EDITION_2026_10_17\n        else:\n            if args.doc:',
     '                            hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,\n                            keep_frontmatter=args.keep_frontmatter, images=args.images,\n                            scholar=args.scholar, prose=args.prose)   # SCHOLAR_EDITION_2026_10_17; PROSE_EDITION_2026_10_25\n        else:\n            if args.doc:')

edit('scripts/export_html.py', 12, '                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,\n                        keep_frontmatter=args.keep_frontmatter, images=args.images,\n                        scholar=args.scholar)   # SCHOLAR_EDITION_2026_10_17\n\nif __name__ == "__main__":',
     '                        hi_label=hi_label, want_toc=want_toc, want_footnotes=want_footnotes, debug=args.debug,\n                        keep_frontmatter=args.keep_frontmatter, images=args.images,\n                        scholar=args.scholar, prose=args.prose)   # SCHOLAR_EDITION_2026_10_17; PROSE_EDITION_2026_10_25\n\nif __name__ == "__main__":')

edit('scripts/publish_editions.py', 1, 'content has not changed is left as it is (its date too).\n\n  python scripts\\\\publish_editions.py                      (the plan: what would be written; free, nothing written)\n  python scripts\\\\publish_editions.py --apply              (writes into the Srangam repo; never runs git)',
     'content has not changed is left as it is (its date too).\n\nPROSE_EDITION_2026_10_25: each edition is also written read as prose (export_html.py --scholar --prose), as\npublic/scholarly/<slug>-prose.html, its bar linking the verses and the verses\' bar linking it; the index gives its\nfile ("prose"), size and digest, and the site\'s /editions page links it. "prose": false in an entry keeps it out.\n\n  python scripts\\\\publish_editions.py                      (the plan: what would be written; free, nothing written)\n  python scripts\\\\publish_editions.py --apply              (writes into the Srangam repo; never runs git)')

edit('scripts/publish_editions.py', 2, '\nMARK = "EDITIONS_SITE_2026_10_18"\nROOT = Path(__file__).resolve().parent.parent\nSCRIPTS = ROOT / "scripts"',
     '\nMARK = "EDITIONS_SITE_2026_10_18"\nMARK_PROSE = "PROSE_EDITION_2026_10_25"\nROOT = Path(__file__).resolve().parent.parent\nSCRIPTS = ROOT / "scripts"')

edit('scripts/publish_editions.py', 3, '\n\ndef export(db: Path, e: dict, out: Path, py: str = sys.executable) -> Path:\n    cmd = [py, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", e["doc"], "--scholar", "--sanskrit",\n           "--side-by-side", "--from", str(e["pages"][0]), "--to", str(e["pages"][1]), "--title", e["title"],\n           "--out", str(out)]\n    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))\n    files = sorted(out.glob("*_scholar.html"))\n    if r.returncode != 0 or len(files) != 1:\n        raise RuntimeError("export_html.py: rc %s, %d file(s): %s" % (r.returncode, len(files), (r.stderr or r.stdout)[-400:]))',
     '\n\ndef export(db: Path, e: dict, out: Path, py: str = sys.executable, prose: bool = False) -> Path:\n    cmd = [py, str(SCRIPTS / "export_html.py"), "--db", str(db), "--doc", e["doc"], "--scholar"]\n    cmd += ["--prose"] if prose else ["--sanskrit", "--side-by-side"]   # PROSE_EDITION_2026_10_25\n    cmd += ["--from", str(e["pages"][0]), "--to", str(e["pages"][1]), "--title", e["title"], "--out", str(out)]\n    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))\n    files = sorted(out.glob("*_scholar_prose.html" if prose else "*_scholar.html"))\n    if r.returncode != 0 or len(files) != 1:\n        raise RuntimeError("export_html.py: rc %s, %d file(s): %s" % (r.returncode, len(files), (r.stderr or r.stdout)[-400:]))')

edit('scripts/publish_editions.py', 4, '\n\ndef dress(page: str, e: dict, st: dict) -> str:\n    """The exported edition, given its place on the site: a bar back to /editions, its credits, its canonical address."""\n    slug = e["slug"]\n    url = "%s/scholarly/%s.html" % (SITE_URL, slug)\n    desc = "%s: %s" % (e["title"], e.get("subtitle") or "the Sanskrit with a scholarly English and notes")\n    head = ("<link rel=\'canonical\' href=\'%s\'/><meta name=\'description\' content=\'%s\'/>"\n            "<meta name=\'robots\' content=\'index,follow\'/><!-- %s -->"\n            % (html.escape(url, quote=True), html.escape(desc, quote=True), MARK))\n    page = page.replace("</head>", head + "</head>", 1)\n    page = page.replace("</style>", BAR_CSS + "</style>", 1)\n    bar = ("<div class=\'site-bar\'><a href=\'/editions\'>&larr; Srangam: the scholarly editions</a>"\n           "<span>%s</span></div>" % html.escape(e.get("subtitle") or ""))\n    m = re.search(r"<body[^>]*>", page)\n    if not m:',
     '\n\ndef wants_prose(e: dict) -> bool:\n    """PROSE_EDITION_2026_10_25: an edition is also read as prose unless its entry says "prose": false."""\n    return e.get("prose", True) is not False\n\n\ndef dress(page: str, e: dict, st: dict, prose: bool = False) -> str:\n    """The exported edition, given its place on the site: a bar back to /editions, its credits, its canonical address.\n    PROSE_EDITION_2026_10_25: the prose\'s bar links the verses, the verses\' bar the prose."""\n    slug = e["slug"]\n    url = "%s/scholarly/%s%s.html" % (SITE_URL, slug, "-prose" if prose else "")\n    desc = "%s: %s" % (e["title"], e.get("subtitle") or "the Sanskrit with a scholarly English and notes")\n    if prose:\n        desc = "%s, read as prose: the scholarly English with its notes" % e["title"]\n    head = ("<link rel=\'canonical\' href=\'%s\'/><meta name=\'description\' content=\'%s\'/>"\n            "<meta name=\'robots\' content=\'index,follow\'/><!-- %s -->"\n            % (html.escape(url, quote=True), html.escape(desc, quote=True), MARK))\n    page = page.replace("</head>", head + "</head>", 1)\n    page = page.replace("</style>", BAR_CSS + "</style>", 1)\n    other = ""\n    if prose:   # PROSE_EDITION_2026_10_25\n        other = "<a href=\'/scholarly/%s.html\'>The verses, beside the Sanskrit</a>" % html.escape(slug, quote=True)\n    elif wants_prose(e):\n        other = "<a href=\'/scholarly/%s-prose.html\'>Read it as prose</a>" % html.escape(slug, quote=True)\n    bar = ("<div class=\'site-bar\'><a href=\'/editions\'>&larr; Srangam: the scholarly editions</a>%s"\n           "<span>%s</span></div>" % (other, html.escape(e.get("subtitle") or "")))\n    m = re.search(r"<body[^>]*>", page)\n    if not m:')

edit('scripts/publish_editions.py', 5, '        if not same:\n            writes.append((out_dir / ("%s.html" % slug), body))\n    gone = [s for s in old if s not in {r.get("slug") for r in rows} and not (a.only and s not in a.only)]\n    for s in gone:',
     '        if not same:\n            writes.append((out_dir / ("%s.html" % slug), body))\n        if wants_prose(e):   # PROSE_EDITION_2026_10_25: the edition read as prose, beside it\n            with tempfile.TemporaryDirectory() as td:\n                try:\n                    pp = dress(export(Path(a.db), e, Path(td), prose=True).read_text(encoding="utf-8"), e, st, prose=True)\n                except RuntimeError as x:\n                    problems.append("%s (as prose): %s" % (slug, x)); pp = None\n            if pp is not None:\n                pb = pp.replace("\\r\\n", "\\n").encode("utf-8")\n                ph = sha(pb)\n                psame = prev.get("prose_sha256") == ph and (out_dir / ("%s-prose.html" % slug)).exists()\n                rec.update({"prose": "/scholarly/%s-prose.html" % slug, "prose_bytes": len(pb), "prose_sha256": ph,\n                            "mark_prose": MARK_PROSE})\n                print("  %-22s %s  as prose, %.2f MB%s" % ("", "unchanged" if psame else ("new" if not prev.get("prose")\n                                                                                        else "changed"), len(pb) / 1e6,\n                                                         "" if psame else " -> %s" % (SUBDIR / ("%s-prose.html" % slug)).as_posix()))\n                if not psame:\n                    writes.append((out_dir / ("%s-prose.html" % slug), pb))\n    gone = [s for s in old if s not in {r.get("slug") for r in rows} and not (a.only and s not in a.only)]\n    for s in gone:')

edit('tests/test_publish_editions_2026_10_18.py', 1, '        self.assertEqual(rc, 0, out)\n        self.assertIn("devi", out); self.assertIn("new", out)\n        self.assertIn("VERDICT: 2 file(s) to write", out)\n        self.assertIn("NEXT: python scripts\\\\publish_editions.py --apply", out)\n        self.assertFalse((self.site / "public").exists())',
     '        self.assertEqual(rc, 0, out)\n        self.assertIn("devi", out); self.assertIn("new", out)\n        self.assertIn("VERDICT: 3 file(s) to write", out)   # PROSE_EDITION_2026_10_25: the edition, its prose, the index\n        self.assertIn("NEXT: python scripts\\\\publish_editions.py --apply", out)\n        self.assertFalse((self.site / "public").exists())')


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
