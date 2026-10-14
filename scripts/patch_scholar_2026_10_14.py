#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_2026_10_14.py  (2026-10-14)  SCHOLAR_2026_10_14 (with HOLD_2026_10_14)

Asked on 14 Oct: "we need accurate authoritative high fidelity Debroy-esque translations with all the reiteration and
expense and context ... each text should either be fixable, retirable, or a critical edition / better scan searched
for." scripts/scholar_translate.py (new) makes a scholarly English beside the working one. This patch wires it in,
and stops the Library from offering paid translation where the path says the scan or the source comes first:
  dashboard.py (on a restart):
    /scholar and /scholar/<doc>: the scholarly English, read-only (scholar_translate.py renders them); a link in the
      Library's header;
    HOLD_2026_10_14: no Finish EN / Add Hindi on a text withdrawn or set aside, or whose path (data/text_path.json) is
      "repair the scan", "a better source" or "retire" (for a text the path has not charted, the count's "to translate
      again" or "a source first"); the card says why, and The path has the next step. A finished job held by
      translate_passages.py says "held", not "failed".
  translate_passages.py: a whole-text run on a text the register has withdrawn or set aside is refused before anything
    is sent ("REFUSING (HOLD_2026_10_14)", exit 4: exit 3 stays the debris guard's). --allow-held or SA_ALLOW_HELD=1
    lets it through; one page (--only-page) is never held.
  .gitignore: data/scholar/ (the runs' logs) stays local.

Needs REDEEM_2026_10_14 (dashboard.py), REPAIR_HEAL_2026_10_11 (translate_passages.py) and scripts/scholar_translate.py.
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and encodings; each .py is compiled before
it replaces the original; backups .bak_scholar_<date>.
  python scripts\\patch_scholar_2026_10_14.py --check
  python scripts\\patch_scholar_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "SCHOLAR_2026_10_14"
NEEDS = {"scripts/dashboard.py": "REDEEM_2026_10_14", "scripts/translate_passages.py": "REPAIR_HEAL_2026_10_11"}
FILES = list(NEEDS)
GITIGNORE_BLOCK = "# SCHOLAR_2026_10_14: the scholarly English runs' logs stay local\ndata/scholar/\n"

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


# ---------------------------------------------------------------------------------------------- dashboard.py
edit('scripts/dashboard.py', 1,
     r'''@app.get("/redeem")
def redeem_page():
''',
     r'''# SCHOLAR_2026_10_14 / HOLD_2026_10_14 -------------------------------------------------------------------------
_PATH_CACHE = {"key": None, "by": {}}
_HOLD_PATHS = {"repair": "repair its scan first", "source": "a better source first", "retire": "it is to be retired"}


def _path_texts() -> Dict[str, dict]:
    """HOLD_2026_10_14: the last chart of the path (data/text_path.json) as {doc: its row}, read again only when the
    file changes; {} when there is none."""
    try:
        st = PATH_FILE.stat()
        key = (str(PATH_FILE), st.st_mtime, st.st_size)
    except OSError:
        return {}
    if _PATH_CACHE["key"] != key:
        try:
            res = json.loads(PATH_FILE.read_text(encoding="utf-8"))
            _PATH_CACHE["by"] = {str(t.get("doc")): t for t in (res.get("texts") or []) if isinstance(t, dict)}
        except (OSError, ValueError, AttributeError):
            _PATH_CACHE["by"] = {}
        _PATH_CACHE["key"] = key
    return _PATH_CACHE["by"]


def _hold_reason(code: str, rec=None, rdm=None) -> str:
    """HOLD_2026_10_14: why the Library does not offer Finish EN and Add Hindi on this text now ('' when it does).
    The register first (withdrawn, set aside); then the path (repair the scan, a better source, retire); for a text
    the path has not charted, the count (redeem.py: to translate again after the repair, a source first). Translating
    now would pay for English made from the same misreading."""
    st = (rec or {}).get("status")
    if st == "withdrawn":
        return "withdrawn from the site: a better source first"
    if st == "set_aside":
        return "set aside: a better scan first"
    p = _path_texts().get(code)
    if p is not None:
        step = p.get("path")
        return ("%s (the path: %s)" % (_HOLD_PATHS[step], p.get("why") or step)) if step in _HOLD_PATHS else ""
    for t in (rdm or {}).get("texts") or []:
        if t.get("doc") == code:
            if t.get("verdict") == "redo":
                return "repair its scan first (less than half of its English can be kept)"
            if t.get("verdict") == "source":
                return "a better source first (its scan is not here)"
            return ""
    return ""


def _hold_note(code: str, reason: str, rec=None) -> str:
    """HOLD_2026_10_14: the card's line for a hold ('' for a text whose register state the card already explains)."""
    import html as _html
    if not reason or (rec or {}).get("status") in ("withdrawn", "set_aside"):
        return ""
    return ('<div class="cardnote state" title="HOLD_2026_10_14: data/text_path.json, data/redeem.json">Finish EN and Add '
            'Hindi are not offered now: %s. <a href="/path" style="color:inherit">The path</a> has the next step; chart '
            'it again there after a repair.</div>' % _html.escape(reason))


@app.get("/scholar")
def scholar_index_page():
    """SCHOLAR_2026_10_14: the scholarly English (scripts/scholar_translate.py), text by text. Reads the database
    read-only."""
    return _scholar_page(None)


@app.get("/scholar/<doc>")
def scholar_doc_page(doc):
    """SCHOLAR_2026_10_14: one text's scholarly English beside its Sanskrit and its working English, verse by verse."""
    doc = _validate_doc(doc)
    if not doc:
        return "invalid doc", 400
    return _scholar_page(doc)


def _scholar_page(doc):
    import html as _html
    db_path = request.args.get("db", "data/context.db")
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import scholar_translate as _st
        con = sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            if doc:
                try:
                    off = max(0, int(request.args.get("offset", 0) or 0))
                except ValueError:
                    off = 0
                return _st.render_doc(con, doc, offset=off, limit=200, nav=True)
            return _st.render_index(con, nav=True)
        finally:
            con.close()
    except Exception as e:
        return "<pre>Scholarly English: %s</pre>" % _html.escape("%s: %s" % (type(e).__name__, e)), 500


@app.get("/redeem")
def redeem_page():
''')

edit('scripts/dashboard.py', 2,
     r'''            acts = ''
            if pct < 100:
                acts += (f'<button class="tr-rest" title="Translate the remaining English verses"'
                         f' onclick="translateRest(\'{code}\',\'en\',this)">&#9889; Finish EN</button>')
            if h < en:
                acts += (f'<button class="tr-rest hi" title="Translate Hindi for verses that have English but no Hindi"'
                         f' onclick="translateRest(\'{code}\',\'hi\',this)">&#2361;&#2367; Add Hindi</button>')
            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
''',
     r'''            acts = ''
            _hold = _hold_reason(code, aside.get(code), rdm) if (pct < 100 or h < en) else ''   # HOLD_2026_10_14
            if pct < 100 and not _hold:
                acts += (f'<button class="tr-rest" title="Translate the remaining English verses"'
                         f' onclick="translateRest(\'{code}\',\'en\',this)">&#9889; Finish EN</button>')
            if h < en and not _hold:
                acts += (f'<button class="tr-rest hi" title="Translate Hindi for verses that have English but no Hindi"'
                         f' onclick="translateRest(\'{code}\',\'hi\',this)">&#2361;&#2367; Add Hindi</button>')
            acts_html = f'<div class="cardacts">{acts}</div>' if acts else ''
            acts_html += _hold_note(code, _hold, aside.get(code))   # HOLD_2026_10_14
''')

edit('scripts/dashboard.py', 3,
     r'''        rec = aside.get(code) or {}
        c = _html.escape(str(code), quote=True)
        acts = "" if rec.get("status") == "set_aside" else (
''',
     r'''        rec = aside.get(code) or {}
        c = _html.escape(str(code), quote=True)
        _hold = _hold_reason(code, rec, rdm)   # HOLD_2026_10_14: no translate buttons while the scan or the source comes first
        acts = _hold_note(code, _hold, rec) if (rec.get("status") == "set_aside" or _hold) else (
''')

edit('scripts/dashboard.py', 4,
     r'''  <a class="back" href="/redeem" title="REDEEM_2026_10_14: what of the translation already paid for is kept, and what is not" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878; What is redeemed</a>
''',
     r'''  <a class="back" href="/redeem" title="REDEEM_2026_10_14: what of the translation already paid for is kept, and what is not" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878; What is redeemed</a>
  <a class="back" href="/scholar" title="SCHOLAR_2026_10_14: the scholarly English, verse by verse: drafted with its context and glossary, read by a critic, revised, judged" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128220; Scholarly English</a>
''')

edit('scripts/dashboard.py', 5,
     r'''  if(j.ok===false && /KILLED/.test(out)) return {{word:'stopped', text:'Stopped by hand.'}};
''',
     r'''  if(j.ok===false && /HOLD_2026_10_14/.test(out)) return {{word:'held', text:'Held: this text is withdrawn or set aside (data/source_verdicts.jsonl), so it is not translated further: a better source first. Nothing was spent.'}};
  if(j.ok===false && /KILLED/.test(out)) return {{word:'stopped', text:'Stopped by hand.'}};
''')

# ---------------------------------------------------------------------------------------------- translate_passages.py
edit('scripts/translate_passages.py', 1,
     r'''def _debris_guard(con, doc, debris_max, inbox=None):
''',
     r'''def _hold_message(doc):
    """HOLD_2026_10_14: the refusal when the register has this text withdrawn or set aside, else None. Its pages are
    kept, and one page (--only-page) is never held. Exit 4, so that the Library does not take it for the debris
    guard's hold (exit 3)."""
    st = _source_state(doc) or {}
    if st.get("status") not in ("withdrawn", "set_aside"):
        return None
    w = st["status"] == "withdrawn"
    return ("REFUSING (HOLD_2026_10_14): %s is %s in data/source_verdicts.jsonl (%s: %s). Nothing was sent. A better "
            "%s first.\n  Translate it anyway: add --allow-held (dashboard: set SA_ALLOW_HELD=1)."
            % (doc, "withdrawn from the site" if w else "set aside", str(st.get("at") or "?")[:16],
               st.get("reason") or "", "source" if w else "scan"))


def _debris_guard(con, doc, debris_max, inbox=None):
''')

edit('scripts/translate_passages.py', 2,
     r'''    ap.add_argument("--allow-debris", action="store_true",
                    help="TRANSLATE_DEBRIS_GUARD_2026_10_04: translate even when the source is repairable "
                         "Tesseract debris (env SA_ALLOW_DEBRIS=1 does the same)")
''',
     r'''    ap.add_argument("--allow-debris", action="store_true",
                    help="TRANSLATE_DEBRIS_GUARD_2026_10_04: translate even when the source is repairable "
                         "Tesseract debris (env SA_ALLOW_DEBRIS=1 does the same)")
    ap.add_argument("--allow-held", action="store_true",
                    help="HOLD_2026_10_14: translate a whole text the register (data/source_verdicts.jsonl) has "
                         "withdrawn or set aside (env SA_ALLOW_HELD=1 does the same)")
''')

edit('scripts/translate_passages.py', 3,
     r'''    if (args.only_page is None and not args.allow_debris
            and os.environ.get("SA_ALLOW_DEBRIS", "") not in ("1", "true", "yes")):   # TRANSLATE_DEBRIS_GUARD_2026_10_04
''',
     r'''    if (args.only_page is None and not args.allow_held
            and os.environ.get("SA_ALLOW_HELD", "") not in ("1", "true", "yes")):   # HOLD_2026_10_14 (SCHOLAR_2026_10_14)
        _held = _hold_message(args.doc)
        if _held:
            print(_held)
            sys.exit(4)
    if (args.only_page is None and not args.allow_debris
            and os.environ.get("SA_ALLOW_DEBRIS", "") not in ("1", "true", "yes")):   # TRANSLATE_DEBRIS_GUARD_2026_10_04
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    tool = Path("scripts/scholar_translate.py")
    if not tool.exists() or MARK.encode() not in tool.read_bytes():
        problems.append("%s (%s) is not there: copy it in first" % (tool.as_posix(), MARK))
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
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
        if p.suffix != ".py":
            continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_scholar_" + stamp))
        t = p.with_name(p.name + ".tmp_scholar"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The scholarly English, the dry run (free, read-only):")
    print("  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24")
    print("dashboard.py shows /scholar and the Library's holds when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
