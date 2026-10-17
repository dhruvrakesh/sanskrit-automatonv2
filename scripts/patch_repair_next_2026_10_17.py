#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_repair_next_2026_10_17.py  (2026-10-17)  REPAIR_NEXT_2026_10_17

On 17 Oct the vision repair of the Padma Purana's Patala Khanda stopped at its cap ($1.90) with 218 of its 364
pages read, and repair_text.py's assessment ended "VERDICT: nothing holds it ... NEXT: translate it", although it
had itself judged the debris material ("Repair first: translating now translates the OCR's errors"), the drift
check had found 203 pages of the repair not in the database, and the path (text_path.py) says repair. The debris
guard did not hold it (16% of its verses carry Latin letters, under the guard's threshold), so the assessment fell
to "nothing holds it". Now, in that case, a text whose reading is Tesseract's, whose debris is judged moderate or
material and whose scan is here gets the path's next step: the pages vision has not read (--repair --max-usd, the
price measured on this text), or, when they are read, the re-ingest of the changed pages; the translation after.
The same advice reaches the Library's cards and the Sources page (data/source_judged).

scripts/repair_text.py (needs READ_IN_2026_10_13). Anchored, all-or-nothing, marker-idempotent; keeps line endings;
py_compile before the atomic replace; backups .bak_repairnext_<date>. No database change.
  python scripts\\patch_repair_next_2026_10_17.py --check
  python scripts\\patch_repair_next_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'REPAIR_NEXT_2026_10_17'
NEEDS = {'scripts/repair_text.py': 'READ_IN_2026_10_13'}
FILES = list(NEEDS)
TAG = 'repairnext'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/repair_text.py', 1, r'''def advise(r: dict, doc: str):
''', r'''def repair_first(r: dict, doc: str, q: str, tr: str):
    """REPAIR_NEXT_2026_10_17: the debris guard lets a text through (it is under the guard's threshold), but its reading
    is Tesseract's, its debris judged moderate or material and its scan is here. The path (text_path.py,
    PATH_2026_10_12) says repair first; so does this now, with the same reckoning: the pages vision has not read, less
    those it failed on twice, at the price measured on this text where there is one. (why, next, also), or None.
    On 17 Oct the Padma Purana's Patala Khanda was assessed "nothing holds it ... NEXT: translate it" with 146 of its
    364 pages unread by vision (the run had stopped at its cap) and 203 pages of the repair not in the database."""
    j = r.get("judged") or {}
    if j.get("level") not in ("moderate", "material") or float(r.get("vision_pct") or 0) >= 50.0:
        return None
    pdfs, vp, raw = int(r.get("pdfs") or 0), int(r.get("vision_pages") or 0), int(r.get("raw_pages") or 0)
    if not pdfs or pdfs < 0.9 * max(1, raw):
        return None
    gave = int(r.get("vision_gave_up") or 0)
    todo = max(0, pdfs - vp - gave)
    stale = int((r.get("consensus") or {}).get("stale") or 0)
    then = "then: " + tr
    if todo:
        cpp = float(r.get("cost_per_page") or COST_PER_PAGE)
        cap = max(1.0, math.ceil(todo * cpp * 1.25 * 10) / 10.0)
        why = ("but its reading is Tesseract's and its debris %s: repair first, as its path says, so that the English is "
               "made from a clean reading; vision has read %d of its %d pages%s, %d to go, about $%.2f at $%.4f a page"
               % (j["level"], vp, pdfs, (" (%d left to Tesseract: vision failed on them twice)" % gave) if gave else "",
                  todo, todo * cpp, cpp))
        also = ([REINGEST % doc + "   (the %d page(s) of the repair that differ from the database can go in now)" % stale]
                if stale else []) + [then]
        return (why, q + " --repair --max-usd %.2f   (the pages vision has not read; it stops before spending more)" % cap,
                also)
    if stale:
        return ("but %d page(s) of its repair differ from the database: they go in first" % stale, REINGEST % doc, [then])
    return None


def advise(r: dict, doc: str):
''')

edit('scripts/repair_text.py', 2, r'''        return (v, tr if r["untranslated"] or r["hindi"] < r["english"] else "", [])
''', r'''        rf = repair_first(r, doc, q, tr)   # REPAIR_NEXT_2026_10_17: as the path, repair first
        if rf:
            return (v + "; " + rf[0], rf[1], rf[2])
        return (v, tr if r["untranslated"] or r["hindi"] < r["english"] else "", [])
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
    print('  python -m unittest tests.test_repair_next_2026_10_17')
    return 0


if __name__ == "__main__":
    sys.exit(main())
