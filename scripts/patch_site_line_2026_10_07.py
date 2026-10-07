#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_site_line_2026_10_07.py  (2026-10-07)  SITE_LINE_2026_10_07

Edits the SRANGAM repo's scripts/emit_project_status.py (the generator of the public status
panel, src/data/projectStatus.ts). Run it from the Srangam repo root, on main.

Why. The live panel (/sanskrit-translator, /jyotish-horoscope; checked 2026-10-07) still says
"1 Sanskrit text (439 passages) is loaded ... There is no reading page for it yet." Two things
are wrong with regenerating it as it stands:
  1. SITE_CORPUS, the site figures carried with their own date, still holds 2026-09-27:
     1 text, 439 passages, reader page false. Measured 2026-10-07: 2 texts published and
     listed on /texts (Sandilya Bhakti Sutra 439 passages, Markandeya Purana 1,216; the
     publisher's 99_verify.sql gave 1,216 on the site, 0 stale), 1,655 passages, reader live.
  2. With the reader page live, the line still sits under "Not yet true" and would read as
     a plain fact there ("2 Sanskrit texts ... are loaded ..."). What is not yet true is that
     the corpus can be read here, so the line now says that, as a share of the works.

Edits (all-or-nothing, marker-idempotent, backup .bak_siteline_<date>, py_compile):
  * SITE_CORPUS = the 2026-10-07 measurement (texts 2, passages 1655, published 2,
    readerPage True, measuredOn 2026-10-07).
  * _site_line(): when the reader page exists, "Only N of the M works in the corpus can be
    read on this site so far (P passages at /texts, measured D); the rest exist only in the
    working corpus." The earlier wording is kept for the case without a reader page.

  cd D:\\srangam-42267
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_site_line_2026_10_07.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_site_line_2026_10_07.py"
Test (automaton repo): python -m unittest tests.test_site_line_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "SITE_LINE_2026_10_07"

EDITS = [
    ("site corpus",
     '''SITE_CORPUS = {
    "measuredOn": "2026-09-27",
    "texts": 1,
    "passages": 439,
    "published": 1,
    "readerPage": False,
}
''',
     '''SITE_CORPUS = {   # SITE_LINE_2026_10_07: re-measured 2026-10-07 (99_verify.sql, /texts lists both)
    "measuredOn": "2026-10-07",
    "texts": 2,
    "passages": 1655,
    "published": 2,
    "readerPage": True,
}
''', 1),
    ("site line",
     '''    one = s["texts"] == 1
''',
     '''    one = s["texts"] == 1
    if s.get("readerPage") and c.get("works"):   # SITE_LINE_2026_10_07
        # With /texts live, "loaded" is no longer what is not yet true; that the corpus can be
        # read here is. Said as a share of the works, so the panel cannot read as finished.
        return ("Only %d of the %d works in the corpus can be read on this site so far (%s passages "
                "at /texts, measured %s); the rest exist only in the working corpus."
                % (s["published"], c["works"], f"{s['passages']:,}", s["measuredOn"]))
''', 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=".", help="the Srangam repo root (default: the current folder)")
    args = ap.parse_args()
    p = Path(args.root) / "scripts" / "emit_project_status.py"
    if not p.exists():
        print("FAIL: %s not found. Run from the Srangam repo root (D:\\srangam-42267) or pass --root." % p); return 2
    src, nl = load(p)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems = []
    for label, old, new, n in EDITS:
        c = src.count(old)
        if c != n:
            problems.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %s. Nothing written." % (len(EDITS), p)); return 0
    t = p.with_name(p.name + ".tmp_siteline")
    t.write_bytes(src.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(t), doraise=True)
    except py_compile.PyCompileError as e:
        t.unlink(missing_ok=True)
        print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
    shutil.copy2(p, p.with_name(p.name + ".bak_siteline_" + datetime.date.today().strftime("%Y%m%d")))
    os.replace(t, p)
    print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
