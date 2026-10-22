#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_engines_2026_10_22.py  (2026-10-22)  ENGINES_2026_10_22

Asked on 22 Oct: to OCR the esoteric texts with the best engines, open ones too, but to ingest only what passes "our
hard won checks". scripts/source_fidelity.py (needs TRIANGULATE_2026_10_22) read our scan's readings only from
data/raw (Tesseract) and data/raw_vision (Gemini 2.5 Flash). It now reads any engine's pages from any folder:
--cand pages:<dir>/<doc> (<dir>/<doc>_NNNN.jsonl, one JSON line with its "text" a line of the page, as ocr_vision.py
writes them; the folder relative to --root, or absolute), measured by the same checks: its agreement with an e-text,
its own misreadings beside a second reading (--pair), whether its mistakes are another engine's (the independence of
TRIANGULATE), and where two readings outvote ours. pages: is one of our readings (our scan). Nothing else changes.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_engines_<date>; py_compile first.
  python scripts\\patch_engines_2026_10_22.py --check
  python scripts\\patch_engines_2026_10_22.py
  python scripts\\source_fidelity.py --ref db:markandeya_purana__w_gretil --cand pages:data/raw_vision_pro/markandeya_purana --cand raw:markandeya_purana --pair pages:data/raw_vision_pro/markandeya_purana,raw:markandeya_purana
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ENGINES_2026_10_22'
TAG = 'engines'
FILES = ['scripts/source_fidelity.py']
NEEDS = {'scripts/source_fidelity.py': 'TRIANGULATE_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/source_fidelity.py', 1, '                   vision:<doc>     data/raw_vision/<doc>_NNNN.jsonl, the vision OCR of our scan\n                   raw:<doc>        data/raw/<doc>_NNNN.jsonl, the first OCR of our scan (Tesseract, mostly)\n                   file:<path>      a text file: an archive.org OCR (_djvu.txt), an e-text\n                   witness:<code>   another witness',
     '                   vision:<doc>     data/raw_vision/<doc>_NNNN.jsonl, the vision OCR of our scan\n                   raw:<doc>        data/raw/<doc>_NNNN.jsonl, the first OCR of our scan (Tesseract, mostly)\n                   pages:<dir>/<doc> <dir>/<doc>_NNNN.jsonl, any other engine\'s OCR of our scan, one JSON line\n                                    with its "text" a line of the page (ENGINES_2026_10_22: another engine is\n                                    measured by the same checks as ours before its reading is trusted or ingested),\n                                    e.g. pages:data/raw_vision_pro/markandeya_purana\n                   file:<path>      a text file: an archive.org OCR (_djvu.txt), an e-text\n                   witness:<code>   another witness')

edit('scripts/source_fidelity.py', 2, '            pages.setdefault(int(r.get("page_no") or 0), []).append(r.get("text") or "")\n        return sorted((p, "\\n".join(v)) for p, v in pages.items()), "%d records" % len(recs)\n    if kind in ("vision", "raw"):\n        folder = root / "data" / ("raw_vision" if kind == "vision" else "raw")\n        pages, engines = jsonl_pages(folder, name)\n        if not pages:',
     '            pages.setdefault(int(r.get("page_no") or 0), []).append(r.get("text") or "")\n        return sorted((p, "\\n".join(v)) for p, v in pages.items()), "%d records" % len(recs)\n    if kind in ("vision", "raw", "pages"):\n        folder = root / "data" / ("raw_vision" if kind == "vision" else "raw")\n        if kind == "pages":   # ENGINES_2026_10_22: pages:<dir>/<doc>, the folder relative to --root or absolute\n            d, _, name = name.replace("\\\\", "/").rpartition("/")\n            if not d or not name:\n                raise SystemExit("pages: wants a folder and a doc: pages:data/raw_vision_pro/<doc>")\n            folder = Path(d) if Path(d).is_absolute() else root / d\n        pages, engines = jsonl_pages(folder, name)\n        if not pages:')

edit('scripts/source_fidelity.py', 3, '\n\nOUR_READINGS = ("db", "vision", "raw")\n\n',
     '\n\nOUR_READINGS = ("db", "vision", "raw", "pages")   # ENGINES_2026_10_22: pages: is our scan too\n\n')

edit('scripts/source_fidelity.py', 4, '        pass\n    ap = argparse.ArgumentParser(description="FIDELITY_2026_10_22: the letters of a reading against an e-text")\n    ap.add_argument("--ref", help="the reference: witness:CODE, db:DOC or file:PATH")\n    ap.add_argument("--cand", action="append", default=[], help="a reading: db:, vision:, raw:, file:, witness:")\n    ap.add_argument("--pair", action="append", help="A,B: two readings of one print (both among --cand)")\n    ap.add_argument("--prefix", default="", help="only reference units whose reference starts so (14. for kanda 14)")',
     '        pass\n    ap = argparse.ArgumentParser(description="FIDELITY_2026_10_22: the letters of a reading against an e-text")\n    ap.add_argument("--ref", help="the reference: witness:CODE, db:DOC, file:PATH (or a reading)")\n    ap.add_argument("--cand", action="append", default=[],\n                    help="a reading: db:, vision:, raw:, pages:, file:, witness:")\n    ap.add_argument("--pair", action="append", help="A,B: two readings of one print (both among --cand)")\n    ap.add_argument("--prefix", default="", help="only reference units whose reference starts so (14. for kanda 14)")')


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
