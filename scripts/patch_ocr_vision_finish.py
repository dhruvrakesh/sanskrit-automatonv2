#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ocr_vision_finish.py  (2026-10-03)  VISION_FINISH_2026_10_03

WHAT HAPPENED
Ten Mallapurana pages (0022-0029, 0055, 0118, 0128, 0130) came back from vision
EMPTY while Tesseract read 900-2,550 characters on each. They fell back to
Tesseract, and those 53 passages now carry 35 of the book's 78 English lacunas
(71 % lacuna rate against 4.5 % on vision pages). The corpus has 12 such pages.

transcribe() sets max_output_tokens=8192. On gemini-2.5-* the model's internal
"thinking" tokens count against that budget, so a dense page can end with
finish_reason=MAX_TOKENS and no text at all. infer_mt.py has handled exactly this
since 2026-08-20 with a budget ladder (16384, 32768); ocr_vision.py never got it.
Its retry ladder changes TEMPERATURE, which cannot help a budget exhaustion, and
it throws the finish_reason away, so the cause was invisible.

WHAT THIS CHANGES (scripts/ocr_vision.py only, anchored, all-or-nothing)
  1. transcribe(..., max_tokens=8192): the budget is a parameter (default unchanged).
  2. _finish_name(resp): STOP / MAX_TOKENS / SAFETY / RECITATION / None.
  3. transcribe_robust(): on an EMPTY page whose finish_reason is MAX_TOKENS,
     retry with the budget ladder first (OCR_MAXTOK_LADDER, default 16384,32768),
     then the existing temperature ladder at the budget reached. Behaviour on
     every page that succeeds first time is byte-identical to today.
  4. Every discarded retry is metered (it was paid for; it was not recorded).
  5. meta gains "finish" and "retries", so an empty page says WHY.
  6. COST_PER_PAGE 0.00073 -> 0.00028 (the pre-flight estimate; measured 2026-09-30,
     and the script itself asked for this update).

Run from the repo root:
  python scripts/patch_ocr_vision_finish.py --check
  python scripts/patch_ocr_vision_finish.py
Test: python -m unittest tests.test_ocr_vision_finish -v   (fails before, passes after)
No dashboard restart is needed: ocr_vision.py runs as a fresh process per call.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "VISION_FINISH_2026_10_03"
TARGET = Path("scripts/ocr_vision.py")

OLD_SIG = "def transcribe(img, model_name: str, timeout_s: int = 120, temperature: float = 0.0):\n"
NEW_SIG = ("def transcribe(img, model_name: str, timeout_s: int = 120, temperature: float = 0.0,\n"
           "               max_tokens: int = 8192):  # VISION_FINISH_2026_10_03: budget is a parameter\n")

OLD_CFG = "    cfg = genai.GenerationConfig(temperature=temperature, max_output_tokens=8192)\n"
NEW_CFG = "    cfg = genai.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)\n"

OLD_COST = "COST_PER_PAGE = 0.00073   # MEASURED 2026-08-29 from provider token counts on a\n"
NEW_COST = ("COST_PER_PAGE = 0.00028   # VISION_FINISH_2026_10_03: re-measured 2026-09-30 (Mallapurana);\n"
            "                          # was 0.00073, MEASURED 2026-08-29 from provider token counts on a\n")

OLD_TEMPS = "RETRY_TEMPS = (0.3, 0.7)\n"
NEW_TEMPS = OLD_TEMPS + '''# VISION_FINISH_2026_10_03 - output-budget ladder for finish_reason=MAX_TOKENS,
# the same remedy infer_mt.py uses (thinking tokens count against the budget).
MAXTOK_LADDER = tuple(int(x) for x in
                      os.environ.get("OCR_MAXTOK_LADDER", "16384,32768").split(",") if x.strip())


def _finish_name(resp):
    """Provider finish_reason as a name: STOP, MAX_TOKENS, SAFETY, RECITATION, or None."""
    try:
        cands = getattr(resp, "candidates", None)
        fr = cands[0].finish_reason if cands else None
    except Exception:
        return None
    if fr is None:
        return None
    name = getattr(fr, "name", None)
    if name:
        return str(name)
    try:
        return {1: "STOP", 2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION"}.get(int(fr), str(fr))
    except Exception:
        return str(fr)


def _page_problem(t):
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
    problem = _page_problem(text)
    for temp in RETRY_TEMPS:
        if not problem:
            break
        print(f"      [retry] {name}: {problem}, retrying at temperature={temp}")
        if sleep_s:
            time.sleep(sleep_s)
        t2, r2, rl2 = tfn(img, model_name, temperature=temp, max_tokens=budget)
        if not _page_problem(t2):
            print(f"      [retry] {name}: clean at temperature={temp}, using it")
            discarded.append(resp)
            text, resp, raw_len = t2, r2, rl2
            problem = None
        elif (t2 or "").strip() and problem == "empty":
            # still imperfect, but text beats nothing - keep the best so far
            discarded.append(resp)
            text, resp, raw_len = t2, r2, rl2
            problem = _page_problem(text)
        else:
            discarded.append(r2)
    return text, resp, raw_len, discarded
'''

OLD_LOOP = '''            text, resp, raw_len = transcribe(img, args.model)
            def _bad(t):
                if not t.strip():
                    return "empty"
                if len(t) >= LOOP_MIN_CHARS and compress_ratio(t) < LOOP_RATIO:
                    return "phrase loop"
                return None

            problem = _bad(text)
            for temp in RETRY_TEMPS:
                if not problem:
                    break
                print(f"      [retry] {name}: {problem}, retrying at temperature={temp}")
                time.sleep(2.0)
                t2, r2, rl2 = transcribe(img, args.model, temperature=temp)
                if not _bad(t2):
                    print(f"      [retry] {name}: clean at temperature={temp}, using it")
                    text, resp, raw_len = t2, r2, rl2
                    problem = None
                elif t2.strip() and problem == "empty":
                    # still imperfect, but text beats nothing - keep the best so far
                    text, resp, raw_len = t2, r2, rl2
                    problem = _bad(text)
'''
NEW_LOOP = '''            # VISION_FINISH_2026_10_03: budget ladder, then temperature ladder.
            text, resp, raw_len, discarded = transcribe_robust(img, args.model, name)
'''

OLD_METER = '''                               resp=resp, out_chars=len(text), units=1,
                               duration_s=time.time() - t0, con=mcon)
'''
NEW_METER = OLD_METER + '''                for _r in discarded:   # VISION_FINISH_2026_10_03: paid retries are recorded too
                    spend += meter(kind="ocr_vision", doc=args.doc, engine=engine_tag,
                                   resp=_r, out_chars=0, units=0, duration_s=0.0, con=mcon)
'''

OLD_META = '''                "meta": {"dpi": args.dpi, "model": args.model, "dev": round(dev_frac(text), 3),
'''
NEW_META = '''                "meta": {"dpi": args.dpi, "model": args.model, "dev": round(dev_frac(text), 3),
                         "finish": _finish_name(resp), "retries": len(discarded),
'''

EDITS = [("transcribe signature", OLD_SIG, NEW_SIG), ("generation budget", OLD_CFG, NEW_CFG),
         ("COST_PER_PAGE", OLD_COST, NEW_COST), ("ladder + helpers", OLD_TEMPS, NEW_TEMPS),
         ("main retry block", OLD_LOOP, NEW_LOOP), ("meter retries", OLD_METER, NEW_METER),
         ("meta finish", OLD_META, NEW_META)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes(); crlf = raw.count(b"\r\n")
    nl = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
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
    tmp = TARGET.with_name(TARGET.name + ".tmp_vfinish")
    tmp.write_bytes(src.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(); print("REFUSING TO WRITE: patched file does not compile:\n%s" % e); return 1
    bak = TARGET.with_name(TARGET.name + ".bak_vfinish_" + datetime.date.today().strftime("%Y%m%d"))
    shutil.copy2(TARGET, bak)
    os.replace(tmp, TARGET)
    print("PATCHED %s (backup %s)." % (TARGET, bak)); return 0


if __name__ == "__main__":
    sys.exit(main())
