#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_claims_part2_2026_10_28.py  CLAIMS_PART2_2026_10_28

Raychaudhuri's Part II in scholar_claims.py: --part 2 (From the Coronation of Bimbisara to the Extinction of the Gupta
Dynasty, pdf 113-328, pp. 95-310) and --part app (the Appendix, notes to pages of both parts, pdf 329-332), as the
scan's pages show them (claim_pages, read on 28 Oct); the indexes (pdf 333-368) and the reviews (369-372) are not
read. The page's estimate is the one measured on Part I ($0.8893 for 99 pages read whole, about $0.009 a page; it
was 0.007). tests\\test_claims_link_2026_10_21.py's replay compares with this patch's backup when it is here,
as test_claims_fix's does with CLAIMS_LINK's. Nothing is read by the patch: the plan is free, the reading is paid (Google's cap, --max-usd).

  python scripts\\patch_claims_part2_2026_10_28.py --check
  python scripts\\patch_claims_part2_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'CLAIMS_PART2_2026_10_28'
TAG = 'claimspart2'
FILES = ['scripts/scholar_claims.py', 'tests/test_claims_link_2026_10_21.py']
NEEDS = {'scripts/scholar_claims.py': 'CLAIMS_LINK_2026_10_21', 'tests/test_claims_link_2026_10_21.py': 'CLAIMS_LINK_2026_10_21'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/scholar_claims.py', 1, "years after the author's death) and in the United States (published before 1929). The page numbers: pdf pages\n14-18 are Part I's Foreword (i-v), pdf page 19 is page 1 and so on (pdf - 18); Part I (From the Accession of\nParikshit to the Coronation of Bimbisara) is pdf 14-112 (pp. i-v, 1-94).\n\nEach page's text is the scan's own text layer (Adobe Paper Capture, 2014: it misreads, Brahma1;1a for Brahmana),",
     "years after the author's death) and in the United States (published before 1929). The page numbers: pdf pages\n14-18 are Part I's Foreword (i-v), pdf page 19 is page 1 and so on (pdf - 18); Part I (From the Accession of\nParikshit to the Coronation of Bimbisara) is pdf 14-112 (pp. i-v, 1-94). CLAIMS_PART2_2026_10_28: Part II (From the\nCoronation of Bimbisara to the Extinction of the Gupta Dynasty) is pdf 113-328 (pp. 95-310), --part 2; the Appendix,\nnotes to pages of both parts, pdf 329-332 (pp. 311-314), --part app; the Bibliographical and General Indexes (pdf\n333-368) and the author's other books and their reviews (pdf 369-372) are not read.\n\nEach page's text is the scan's own text layer (Adobe Paper Capture, 2014: it misreads, Brahma1;1a for Brahmana),")

edit('scripts/scholar_claims.py', 2, 'PROMPT_VERSION = "claims-v1"\nAPI = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"\nPER_PAGE = 0.007   # the estimate of a page: about 1.5k tokens in, 2.2k out (the thinking capped at 1024)\n\nROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}',
     'PROMPT_VERSION = "claims-v1"\nAPI = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"\nPER_PAGE = 0.009   # CLAIMS_PART2_2026_10_28: as measured on Part I, $0.8893 for 99 pages read whole (21 Oct; 0.007 before)\n\nROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}')

edit('scripts/scholar_claims.py', 3, '        "licence": "public domain: published 1923; the author died in 1957 (India: 60 years after; USA: before 1929)",\n        "front": (14, 18), "offset": 18,\n        "parts": {"1": (14, 112, "Part I: From the Accession of Parikshit to the Coronation of Bimbisara")},\n    },\n}',
     '        "licence": "public domain: published 1923; the author died in 1957 (India: 60 years after; USA: before 1929)",\n        "front": (14, 18), "offset": 18,\n        "parts": {"1": (14, 112, "Part I: From the Accession of Parikshit to the Coronation of Bimbisara"),\n                  # CLAIMS_PART2_2026_10_28: as the scan\'s pages show them (claim_pages, 28 Oct): Part II\'s title on\n                  # pdf 113 (p. 95), its last page pdf 328 (p. 310); the Appendix pdf 329-332; the indexes from pdf 333\n                  "2": (113, 328, "Part II: From the Coronation of Bimbisara to the Extinction of the Gupta Dynasty"),\n                  "app": (329, 332, "Appendix: notes to pages of both parts")},\n    },\n}')

edit('scripts/scholar_claims.py', 4, '    ap.add_argument("--db", default="data/context.db", help="the shelf and our entities (read); the meter\'s rows")\n    ap.add_argument("--extract", action="store_true", help="free: the pages\' text from the scan into the claims database")\n    ap.add_argument("--part", default="", help="a part of the book: 1 (Part I)")\n    ap.add_argument("--pages", default="", help="printed pages: 1-3, i-v, 12, 40-44")\n    ap.add_argument("--redo", action="store_true", help="read again pages read already (a new read; the old one kept)")',
     '    ap.add_argument("--db", default="data/context.db", help="the shelf and our entities (read); the meter\'s rows")\n    ap.add_argument("--extract", action="store_true", help="free: the pages\' text from the scan into the claims database")\n    ap.add_argument("--part", default="", help="a part of the book: 1 (Part I), 2 (Part II), app (the Appendix)")\n    ap.add_argument("--pages", default="", help="printed pages: 1-3, i-v, 12, 40-44")\n    ap.add_argument("--redo", action="store_true", help="read again pages read already (a new read; the old one kept)")')

edit('tests/test_claims_link_2026_10_21.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # CLAIMS_PART2_2026_10_28 came after: its backup is what this patch made\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_claimspart2_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

