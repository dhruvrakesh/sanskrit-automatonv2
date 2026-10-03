#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ocr_vision_finish2.py  (2026-10-03)  VISION_FINISH2_2026_10_03
Requires VISION_FINISH_2026_10_03 (patch_ocr_vision_finish.py) to be applied.

WHAT THE FIRST PATCH REVEALED (its new meta.finish field, 2026-10-03, Mallapurana)
  0022 0024 0026 0028 0029  RECITATION, 0 chars after 2 temperature retries
  0023                      STOP, 2,493 chars  (recovered)
  0055 0128 0130            MAX_TOKENS, 2 chars, retries 0  <- ladder never fired
  0118                      STOP, 2 chars, retries 0         <- no retry either
Two gaps in VISION_FINISH_2026_10_03, both mine:
  (a) the budget ladder fired only on EXACTLY empty text. Two characters is not
      empty, so a truncated page was accepted. Any MAX_TOKENS answer is truncated
      by definition - long or short - so the ladder now fires on MAX_TOKENS always
      and keeps the longest complete answer.
  (b) "empty" meant zero characters. merge_ocr_sources treats < 5 characters as
      empty (DEFINITELY_EMPTY = 5); the retry rule now uses the same threshold.
And one new remedy:
  (c) RECITATION is the provider refusing to reproduce a long passage it has seen
      before. Temperature does not change that. The page is split at the
      whitest horizontal rows into 2, then 3 bands, and each band is transcribed
      separately. The result is used ONLY if every band returns text; otherwise
      the page stays empty and merge keeps Tesseract (a half-page vision reading
      would pass merge's 10x shortfall check and silently drop text).
meta gains "tiles" (0 = whole page). Paid band and retry calls are metered.

  python scripts/patch_ocr_vision_finish2.py --check
  python scripts/patch_ocr_vision_finish2.py
Test: python -m unittest tests.test_ocr_vision_finish2 -v   (fails before, passes after)
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "VISION_FINISH2_2026_10_03"
NEEDS = "VISION_FINISH_2026_10_03"
TARGET = Path("scripts/ocr_vision.py")

OLD_FUNCS = '''def _page_problem(t):
    if not (t or "").strip():
        return "empty"
    if len(t) >= LOOP_MIN_CHARS and compress_ratio(t) < LOOP_RATIO:
        return "phrase loop"
    return None


def transcribe_robust(img, model_name, name, tfn=None, sleep_s=2.0):
    """One page with both recovery ladders. Returns (text, resp, raw_len, discarded).
    discarded = the responses of retries that were paid for but not kept."""
    tfn = tfn or transcribe
    discarded = []
    budget = 8192
    text, resp, raw_len = tfn(img, model_name)
    if not (text or "").strip() and _finish_name(resp) == "MAX_TOKENS":
        for b in MAXTOK_LADDER:
            print(f"      [retry] {name}: MAX_TOKENS with no text, max_output_tokens={b}")
            discarded.append(resp)
            budget = b
            text, resp, raw_len = tfn(img, model_name, max_tokens=b)
            if (text or "").strip() or _finish_name(resp) != "MAX_TOKENS":
                break
'''
NEW_FUNCS = '''NEAR_EMPTY = 5   # VISION_FINISH2_2026_10_03: same threshold as merge_ocr_sources.DEFINITELY_EMPTY
LAST_TILES = [0]  # bands used for the most recent page (0 = whole page); read into meta


def _page_problem(t):
    if len((t or "").strip()) < NEAR_EMPTY:
        return "empty"
    if len(t) >= LOOP_MIN_CHARS and compress_ratio(t) < LOOP_RATIO:
        return "phrase loop"
    return None


def _cut_rows(img, n):
    """Row indices that split the page into n bands, each cut placed on the whitest
    row (least ink) within +-8% of the even split, so no printed line is cut."""
    g = img.convert("L").resize((48, img.height))
    w, h = g.size
    px = list(g.getdata())
    ink = [sum(255 - px[r * w + c] for c in range(w)) for r in range(h)]
    win = max(3, h // 300)
    smooth = [sum(ink[max(0, r - win):r + win + 1]) for r in range(h)]
    cuts = []
    for k in range(1, n):
        target = h * k // n
        lo, hi = max(1, target - h * 8 // 100), min(h - 1, target + h * 8 // 100)
        least = min(smooth[lo:hi])
        cuts.append(min((r for r in range(lo, hi) if smooth[r] <= least), key=lambda r: abs(r - target)))
    return sorted(set(cuts))


def _transcribe_tiled(img, model_name, name, tfn, n, budget):
    """Transcribe n horizontal bands. Returns (text or "", resps). All-or-nothing."""
    cuts = [0] + _cut_rows(img, n) + [img.height]
    texts, resps = [], []
    for i in range(len(cuts) - 1):
        band = img.crop((0, cuts[i], img.width, cuts[i + 1]))
        t, r, _ = tfn(band, model_name, max_tokens=budget)
        resps.append(r)
        if _page_problem(t):
            print(f"      [tiles] {name}: band {i + 1}/{len(cuts) - 1} failed ({_finish_name(r)})")
            return "", resps
        texts.append(t.strip())
    return "\\n".join(texts), resps


def transcribe_robust(img, model_name, name, tfn=None, sleep_s=2.0):
    """One page with the recovery ladders. Returns (text, resp, raw_len, discarded).
    discarded = responses that were paid for but are not `resp` (retries, bands)."""
    tfn = tfn or transcribe
    discarded = []
    budget = 8192
    LAST_TILES[0] = 0
    text, resp, raw_len = tfn(img, model_name)
    if _finish_name(resp) == "MAX_TOKENS":
        # VISION_FINISH2_2026_10_03: MAX_TOKENS means truncated, at any length.
        best = (text, resp, raw_len)
        for b in MAXTOK_LADDER:
            print(f"      [retry] {name}: MAX_TOKENS ({len((text or '').strip())} chars), max_output_tokens={b}")
            budget = b
            t3, r3, rl3 = tfn(img, model_name, max_tokens=b)
            if len((t3 or "").strip()) >= len((best[0] or "").strip()):
                discarded.append(best[1]); best = (t3, r3, rl3)
            else:
                discarded.append(r3)
            if _finish_name(r3) != "MAX_TOKENS":
                break
        text, resp, raw_len = best
'''

OLD_TAIL = '''        else:
            discarded.append(r2)
    return text, resp, raw_len, discarded
'''
NEW_TAIL = '''        else:
            discarded.append(r2)
    if problem == "empty" and _finish_name(resp) == "RECITATION" and img is not None:
        # VISION_FINISH2_2026_10_03: shorter passages are not refused as recitation.
        for n in (2, 3):
            print(f"      [tiles] {name}: RECITATION, transcribing in {n} bands")
            tt, rs = _transcribe_tiled(img, model_name, name, tfn, n, budget)
            if tt:
                discarded.append(resp); discarded.extend(rs[:-1])
                text, resp, raw_len = tt, rs[-1], len(tt)
                LAST_TILES[0] = n
                break
            discarded.extend(rs)
    return text, resp, raw_len, discarded
'''

OLD_META = '''                         "finish": _finish_name(resp), "retries": len(discarded),
'''
NEW_META = '''                         "finish": _finish_name(resp), "retries": len(discarded),
                         "tiles": LAST_TILES[0],  # VISION_FINISH2_2026_10_03
'''

EDITS = [("recovery functions", OLD_FUNCS, NEW_FUNCS), ("recitation tiling", OLD_TAIL, NEW_TAIL),
         ("meta tiles", OLD_META, NEW_META)]


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
        print("REFUSING: apply patch_ocr_vision_finish.py (%s) first." % NEEDS); return 1
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
    tmp = TARGET.with_name(TARGET.name + ".tmp_vfinish2")
    tmp.write_bytes(src.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(); print("REFUSING TO WRITE: patched file does not compile:\n%s" % e); return 1
    bak = TARGET.with_name(TARGET.name + ".bak_vfinish2_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(TARGET, bak)
    os.replace(tmp, TARGET)
    print("PATCHED %s (backup %s)." % (TARGET, bak)); return 0


if __name__ == "__main__":
    sys.exit(main())
