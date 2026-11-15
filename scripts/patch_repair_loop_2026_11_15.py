#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_repair_loop_2026_11_15.py  (2026-11-15)  REPAIR_LOOP_2026_11_15

Asked on 15 Nov: "ganita yuktibhasa scan repair seems to be stuck in a loop on local frontend". Found: the assessment
(repair_text.repair_first) says "repair first: vision has read 112 of its 339 pages, 227 to go" and offers --repair;
--repair sends the scan to ocr_consensus.py with the triage's threshold of 72, which queues only the pages of low OCR
confidence: the 112 that vision has read. So the repair ran for 4.5 seconds (13 Nov, job e1dee20b), read nothing, and
the assessment asked for it again. Now, when the assessment asks for the repair (debris moderate or material, vision
under half of the scan), --repair queues every page (threshold 101) and vision skips the pages it has read: the 227.
An explicit --threshold, and the guard's 101, are as before.

  scripts/repair_text.py    repair_todo(); --repair uses it

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_repairloop_<date> copies.

  python scripts\\patch_repair_loop_2026_11_15.py --check
  python scripts\\patch_repair_loop_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'REPAIR_LOOP_2026_11_15'
TAG = 'repairloop'
FILES = ['scripts/repair_text.py']
NEEDS = {'scripts/repair_text.py': 'REPAIR_PARTIAL_2026_10_28'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/repair_text.py', 1, '        return ("but %d page(s) of its repair differ from the database: they go in first" % stale, REINGEST % doc, [then])\n    return None\n\n',
     '        return ("but %d page(s) of its repair differ from the database: they go in first" % stale, REINGEST % doc, [then])\n    return None\n\n\ndef repair_todo(r: dict) -> int:\n    """REPAIR_LOOP_2026_11_15: the pages repair_first counts when it says "repair first" (vision has not read them and\n    has not given up on them), else 0. --repair now reads exactly these. On 13 Nov the Ganita Yuktibhasa\'s repair ran\n    for 4.5 seconds and read nothing: the triage\'s threshold (72) let through only the 112 pages of low confidence,\n    which vision had read already, while the assessment counted the other 227 and asked for the same repair again, so\n    the desk\'s button led back to itself."""\n    j = r.get("judged") or {}\n    if j.get("level") not in ("moderate", "material") or float(r.get("vision_pct") or 0) >= 50.0:\n        return 0\n    pdfs, vp, raw = int(r.get("pdfs") or 0), int(r.get("vision_pages") or 0), int(r.get("raw_pages") or 0)\n    if not pdfs or pdfs < 0.9 * max(1, raw):\n        return 0\n    return max(0, pdfs - vp - int(r.get("vision_gave_up") or 0))\n\n')

edit('scripts/repair_text.py', 2, '            print("REFUSE: " + r["error"]); return 1\n        thr = a.threshold if a.threshold is not None else (101 if r["guard"] else 72)\n        out = []\n        # REPAIR_HEAL_2026_10_11: ocr_consensus.py refuses while the dashboard runs a job for this text;',
     '            print("REFUSE: " + r["error"]); return 1\n        thr = a.threshold if a.threshold is not None else (101 if r["guard"] else 72)\n        _todo = repair_todo(r) if a.threshold is None and thr < 101 else 0   # REPAIR_LOOP_2026_11_15\n        if _todo:\n            thr = 101\n            print("REPAIR_LOOP_2026_11_15: the %d page(s) vision has not read go to vision: every page is queued "\n                  "(threshold 101) and the pages vision read already are skipped" % _todo, flush=True)\n        out = []\n        # REPAIR_HEAL_2026_10_11: ocr_consensus.py refuses while the dashboard runs a job for this text;')


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

