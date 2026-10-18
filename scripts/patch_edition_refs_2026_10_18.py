#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_edition_refs_2026_10_18.py  (2026-10-18)  EDITION_REFS_2026_10_18

Found on 18 Oct in the Devimahatmya's scholarly edition (export_html.py --scholar, markandeya_purana__w_gretil, pages
626 to 780), before it goes on Srangam:
  - its contents read "Adhyaya 77, 81, 78, 82, 79, 83, 80, 84 ...": the GRETIL file's speaker lines and headings carry
    the chapter of an earlier heading ("77" within adhyaya 81), and the edition groups by that field;
  - a sentence begun by a speaker's line ("vaisya uvaca", no reference of its own) was labelled by that line's
    page.idx: "628.1-18".

scripts/export_html.py (needs SCHOLAR_EDITION_2026_10_17), the scholarly edition only:
  - _ref_chapters(): when half or more of the passages carry a two-part reference of their own (an e-text's 81.1), the chapter is the
    reference's; a passage without one (a heading, a speaker's line) goes with the next verse that has one, a
    colophon (iti ...) with the one before. Three-part references (MBh 1.1.8) and texts without references are
    unchanged;
  - _own_range(): a sentence's range from its verses' own references (81.18-19), ST._range when none has one;
  - the notes numbered in the order their anchors are read, an italic *term* found as printed (the first
    sentence's notes read 1, 4, 3, 2); a note's *term* in italics, as in the English.
tests/test_scholar_edition_2026_10_17.py (its replay chain): export_html.py's later backup may be .bak_editionrefs_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_editionrefs_<date>. No database change; nothing is called.
  python scripts\\patch_edition_refs_2026_10_18.py --check
  python scripts\\patch_edition_refs_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'EDITION_REFS_2026_10_18'
NEEDS = {'scripts/export_html.py': 'SCHOLAR_EDITION_2026_10_17', 'tests/test_scholar_edition_2026_10_17.py': 'SCHOLAR_EDITION_2026_10_17'}
FILES = list(NEEDS)
TAG = 'editionrefs'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/export_html.py', 1, r'''# --- SCHOLAR_EDITION_2026_10_17: the scholarly English as an edition ----------
''', r'''# --- EDITION_REFS_2026_10_18: an e-text's own references for its chapters and its sentences ----------
_REF2_RE = re.compile(r"^\D*?(\d+)\.(\d+)$")
_ITI = "\u0907\u0924\u093f"


def _ref_chapters(recs):
    """EDITION_REFS_2026_10_18: in an e-text whose verses carry their own two-part references (GRETIL's 81.1), the
    chapter is the reference's, not the file's headings (the GRETIL Markandeya's speaker lines carried "77" within
    adhyaya 81). A passage without a reference goes with the next verse that has one (a heading, a speaker's line), a
    colophon (iti ...) with the one before. Only when half or more of the passages that show Sanskrit have such a reference; three-part
    references (MBh 1.1.8) and texts without references are left as they were."""
    chs = []
    for r in recs:
        m = _REF2_RE.match(str(r.get("vref") or "").strip())
        chs.append(m.group(1) if m else None)
    shown = [c for r, c in zip(recs, chs) if (r.get("san") or "").strip()]
    if not shown or sum(1 for c in shown if c) < 0.5 * len(shown):
        return recs
    after, nxt = [None] * len(recs), None
    for i in range(len(recs) - 1, -1, -1):
        if chs[i]:
            nxt = chs[i]
        after[i] = nxt
    prev = None
    for i, r in enumerate(recs):
        if chs[i]:
            prev = r["chap"] = chs[i]
            continue
        san = (r.get("san") or "").strip()
        if prev and (san.startswith(_ITI) or after[i] is None):
            r["chap"] = prev
        elif after[i]:
            r["chap"] = after[i]
    return recs


def _own_range(u, pref):
    """EDITION_REFS_2026_10_18: a sentence's range from its verses' own references, so that one begun by a speaker's line
    (no reference of its own) is not labelled by that line's page.idx ("628.1-18"); ST._range when none has one."""
    import scholar_translate as ST
    refs = [pref.get(r.get("passage_id")) for r in u]
    refs = [x for x in refs if x]
    if not refs:
        return ST._range(u)
    a_, b_ = refs[0], refs[-1]
    return a_ if a_ == b_ else "%s\u2013%s" % (a_, b_.split(".")[-1])


# --- SCHOLAR_EDITION_2026_10_17: the scholarly English as an edition ----------
''')

edit('scripts/export_html.py', 2, r'''    ptext, pkey = {}, {}
''', r'''    ptext, pkey = {}, {}
    pref = {}   # EDITION_REFS_2026_10_18: each passage's own reference
    if "verse_ref" in _colnames(con, "passages"):
        for pid_, vr_ in con.execute("SELECT p.id, p.verse_ref FROM passages p JOIN docs d ON d.id = p.doc_id "
                                     "WHERE d.code = ?", (doc,)):
            if vr_ not in (None, ""):
                pref[pid_] = str(vr_).strip()
''')

edit('scripts/export_html.py', 3, r'''        rng = ST._range(u) if len(u) > 1 else ""
''', r'''        rng = _own_range(u, pref) if len(u) > 1 else ""   # EDITION_REFS_2026_10_18
''')

edit('scripts/export_html.py', 4, r'''        recs, prov["scholar"] = _scholar_recs(con, doc, recs)
''', r'''        recs, prov["scholar"] = _scholar_recs(con, doc, recs)
        recs = _ref_chapters(recs)   # EDITION_REFS_2026_10_18: an e-text's chapters from its own references
''')

edit('scripts/export_html.py', 5, r'''        for n in sch.get("notes") or []:
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "%s: %s" % (str(n.get("anchor") or "").strip(), str(n.get("note") or "").strip())))
            mark = "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>" % (k, k, k)
            a = html.escape(str(n.get("anchor") or "").strip())
            pos = s.find(a) if a else -1
            s = (s[:pos + len(a)] + mark + s[pos + len(a):]) if pos >= 0 else s + mark
''', r'''        # EDITION_REFS_2026_10_18: the notes numbered in the order their anchors are read (they came in the order the
        # translator listed them: 1, 4, 3, 2 in the Devimahatmya's first sentence), an italic *term* found as printed;
        # a note whose anchor is not found comes last
        placed = []
        for j, n in enumerate(sch.get("notes") or []):
            pos, a = _note_at(s, str(n.get("anchor") or "").strip())
            placed.append((pos if pos >= 0 else len(s) + 1 + j, j, n, pos, a))
        placed.sort(key=lambda t: (t[0], t[1]))
        marks = []
        for _o, _j, n, pos, a in placed:
            counter[0] += 1
            k = counter[0]
            notes_out.append((k, "%s: %s" % (str(n.get("anchor") or "").strip(), str(n.get("note") or "").strip())))
            marks.append((pos + len(a) if pos >= 0 else -1, "<sup class='fn-ref' id='fnr-%d'><a href='#fn-%d'>%d</a></sup>"
                          % (k, k, k)))
        for i_, (p_, m_) in sorted(enumerate(marks), key=lambda t: (-t[1][0], -t[0])):
            if p_ >= 0:
                s = s[:p_] + m_ + s[p_:]
        s += "".join(m_ for p_, m_ in marks if p_ < 0)
''')

edit('scripts/export_html.py', 6, r'''def _sch_en_html(en, sch, counter, notes_out, want_footnotes=True):
''', r'''def _note_at(s, raw_a):
    # EDITION_REFS_2026_10_18: (position, form) of a note's anchor in a verse's English as printed (escaped, *terms* in
    # italics), or (-1, '')
    if not raw_a:
        return -1, ""
    for a in (html.escape(raw_a), _inline_format(html.escape(raw_a)), html.escape(raw_a.replace("*", ""))):
        if a:
            p = s.find(a)
            if p >= 0:
                return p, a
    return -1, ""


def _sch_en_html(en, sch, counter, notes_out, want_footnotes=True):
''')

edit('scripts/export_html.py', 7, r'''                out.append(f"<li id='fn-{n}'>{html.escape(note)} "
''', r'''                out.append(f"<li id='fn-{n}'>{_note_html(note)} "   # EDITION_REFS_2026_10_18: *terms* in italics
''')

edit('scripts/export_html.py', 8, r'''def _note_at(s, raw_a):
''', r'''def _note_html(note):
    # EDITION_REFS_2026_10_18: a chapter's note as printed: escaped, a *term* in italics as in the English
    return _EM_RE.sub(r"<em>\1</em>", html.escape(note))


def _note_at(s, raw_a):
''')

edit('tests/test_scholar_edition_2026_10_17.py', 1, r'''                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_buttons_*"))   # BUTTONS_2026_10_17 came after
''', r'''                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_buttons_*")) \
                    or sorted((REPO / f).parent.glob(Path(f).name + ".bak_editionrefs_*"))   # BUTTONS; EDITION_REFS_2026_10_18
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
    print('  python -m unittest tests.test_edition_refs_2026_10_18 tests.test_scholar_edition_2026_10_17 tests.test_export_mode_ui')
    return 0


if __name__ == "__main__":
    sys.exit(main())
