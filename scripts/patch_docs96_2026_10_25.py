#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs96_2026_10_25.py  (2026-10-25)  DOCS96_2026_10_25

docs\\STATE_2026-10-18.md gains section 31 (25 Oct, evening): the scholarly English and its prose on the site, the
rounds and the kinships mended; the full account is docs\\SCHOLAR_SITE_2026-10-25.md (a new file, beside it).

Needs DOCS95_2026_10_25. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_docs96_<date> copy.

  python scripts\\patch_docs96_2026_10_25.py --check
  python scripts\\patch_docs96_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS96_2026_10_25'
TAG = 'docs96'
FILES = ['docs/STATE_2026-10-18.md']
NEEDS = {'docs/STATE_2026-10-18.md': 'DOCS95_2026_10_25'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/STATE_2026-10-18.md', 1, '| The cap | $106.43 spent of $115.00 ($8.57 left; the rounds keep $1.00) |\n| The site | named together live; Publish Srangam if not yet; the genealogy is G3 (after H2) |\n',
     "| The cap | $106.43 spent of $115.00 ($8.57 left; the rounds keep $1.00) |\n| The site | named together live; Publish Srangam if not yet; the genealogy is G3 (after H2) |\n## 31. 25 Oct, evening: the scholarly English and its prose on the site; the rounds mended (DOCS96_2026_10_25)\n\n| What | State |\n|---|---|\n| Release | `422cb349` pushed; SCHOLAR_SITE (and C22), PROSE_EDITION, KIN_SALVAGE, VAMSA_NAMES, AUTO_TRANSLATE, ESCAPES and DOCS96 ready |\n| The scholarly English on the site | verse by verse in the reader for 4 texts (C18); the list of texts and the prose built (C22 to paste; Srangam kit); the editions gain their prose (publish_editions.py --apply) |\n| The scholarly English on the desk | 4,407 verses of 6 texts; the Hayasirsa (1,431) held in repair, the Karanagama (1,018) withdrawn |\n| Kinships | the two cut readings (Soerensen 12641, 7692: $0.388 in six calls) salvaged free (kin_index.py --salvage); an entry failing twice is given up |\n| The repair rounds | decisions no longer spend the tries; translation by --allow-translate only (English, then Hindi; $0.25 a round); the Shukla Yajurveda the first candidate |\n| The cap | $111.28 spent of $125.00 at 15:01 IST (the rounds keep $1.00) |\n| Next | G3: the indexes' relations and lines of descent on the site (C21) |\n")


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
