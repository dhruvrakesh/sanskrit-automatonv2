#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ocr_vision_finish3.py  (2026-10-03)  VISION_FINISH3_2026_10_03
Requires VISION_FINISH2_2026_10_03.

MEASURED 2026-10-03 on the 9 Mallapurana retry pages, after VISION_FINISH2:
  * RECITATION is not beaten by banding. Every band attempt was refused too
    (0024: band 1/2 refused, then a 504; 0026: band 1/2 and band 2/3 refused;
    0028: refused). Banding cost up to 5 extra paid calls per page for nothing.
  * The temperature retries never helped a RECITATION page either (2 of 2 calls
    refused on all 5 pages, here and on 2026-10-03 morning).
  * A transient 504 DeadlineExceeded ended a page as an ERROR (no file written),
    when one retry would likely have succeeded.

WHAT THIS CHANGES (scripts/ocr_vision.py, anchored, all-or-nothing)
  1. RECITATION stops the retry ladders at once: no temperature retries, and
     banding only when OCR_RECITATION_TILES is set (e.g. "2,3"). Default: off.
     The page stays empty and merge keeps Tesseract, as before.
  2. Each call is retried once, after 6 s, on a transient provider error
     (DeadlineExceeded, ServiceUnavailable, InternalServerError, TooManyRequests,
     ResourceExhausted, or HTTP 429/500/503/504 in the message).
Pages that succeed first time behave byte-identically.

  python scripts/patch_ocr_vision_finish3.py --check
  python scripts/patch_ocr_vision_finish3.py
Tests: tests.test_ocr_vision_finish, _finish2 (updated for this behaviour), _finish3.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "VISION_FINISH3_2026_10_03"
NEEDS = "VISION_FINISH2_2026_10_03"
TARGET = Path("scripts/ocr_vision.py")

OLD_HDR = '''LAST_TILES = [0]  # bands used for the most recent page (0 = whole page); read into meta
'''
NEW_HDR = OLD_HDR + '''# VISION_FINISH3_2026_10_03: banding did not beat RECITATION on any of 5 pages; off by default.
RECITATION_TILES = tuple(int(x) for x in os.environ.get("OCR_RECITATION_TILES", "").split(",") if x.strip())
_TRANSIENT = ("DeadlineExceeded", "ServiceUnavailable", "InternalServerError", "TooManyRequests",
              "ResourceExhausted", " 429", " 500", " 503", " 504")


def _with_retry(fn, wait_s=6.0):
    """Retry a call once on a transient provider error (VISION_FINISH3_2026_10_03)."""
    def call(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            tag = type(e).__name__ + " " + str(e)[:200]
            if not any(t in tag for t in _TRANSIENT):
                raise
            print(f"      [retry] transient {type(e).__name__}; once more in {wait_s:.0f}s")
            if wait_s:
                time.sleep(wait_s)
            return fn(*a, **k)
    return call
'''

OLD_TFN = '''    tfn = tfn or transcribe
    discarded = []
    budget = 8192
    LAST_TILES[0] = 0
'''
NEW_TFN = '''    tfn = _with_retry(tfn or transcribe, 0.0 if sleep_s == 0 else 6.0)   # VISION_FINISH3_2026_10_03
    discarded = []
    budget = 8192
    LAST_TILES[0] = 0
'''

OLD_LOOP = '''    problem = _page_problem(text)
    for temp in RETRY_TEMPS:
        if not problem:
            break
'''
NEW_LOOP = '''    problem = _page_problem(text)
    for temp in RETRY_TEMPS:
        if not problem:
            break
        if _finish_name(resp) == "RECITATION":   # VISION_FINISH3_2026_10_03: temperature never helps
            break
'''

OLD_TILES = '''        for n in (2, 3):
'''
NEW_TILES = '''        for n in RECITATION_TILES:   # VISION_FINISH3_2026_10_03: empty unless OCR_RECITATION_TILES is set
'''

EDITS = [("helpers", OLD_HDR, NEW_HDR), ("transient retry", OLD_TFN, NEW_TFN),
         ("recitation stops temperature", OLD_LOOP, NEW_LOOP), ("tiles opt-in", OLD_TILES, NEW_TILES)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes(); crlf = raw.count(b"\r\n")
    nl = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if NEEDS not in src:
        print("REFUSING: apply patch_ocr_vision_finish2.py (%s) first." % NEEDS); return 1
    problems = []
    for label, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            problems.append("%s: matched %d times, expected exactly 1" % (label, n))
        else:
            src = src.replace(old, new)
    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:"); [print("  " + p) for p in problems]; return 1
    if args.check:
        print("CHECK OK: all %d anchors match exactly once. Nothing written." % len(EDITS)); return 0
    tmp = TARGET.with_name(TARGET.name + ".tmp_vfinish3")
    tmp.write_bytes(src.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(); print("REFUSING TO WRITE: patched file does not compile:\n%s" % e); return 1
    bak = TARGET.with_name(TARGET.name + ".bak_vfinish3_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(TARGET, bak)
    os.replace(tmp, TARGET)
    print("PATCHED %s (backup %s)." % (TARGET, bak)); return 0


if __name__ == "__main__":
    sys.exit(main())
