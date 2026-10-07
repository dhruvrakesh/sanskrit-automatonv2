#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_gaps2_2026_10_07.py  (2026-10-07)  GAPS2_2026_10_07

corpus_status kept markandeya_purana at NEEDS-TRANSLATION with "1 passages without
English; 1 passages without Hindi" and an estimate of $0.00, and the commands it
printed translated nothing (2026-10-07 13:1x: "todo=1 ... 0/1 translated" in English,
"3/4 translated" with three echo-filter empties in Hindi). The row it counted is one
translate_passages.py never sends: it skips, silently and without an outcome record,
  * a page numbered below 1 (--since-page defaults to 1),
  * text that should_translate() rejects (too little Devanagari, --min-dev 0.05),
  * text that clean_for_mt() reduces to nothing.
corpus_status now counts those as gaps too ("never sent"), with the same functions
translate_passages uses, so its verdict and the translator agree. Read-only, as before.
If text_filters / normalize_text cannot be imported, nothing changes.

All-or-nothing, marker-idempotent, backup .bak_gaps2_<date>, py_compile.
  python scripts\\patch_gaps2_2026_10_07.py --check
  python scripts\\patch_gaps2_2026_10_07.py
Test: python -m unittest tests.test_heal_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "GAPS2_2026_10_07"

EDITS = [
    ("never-sent helper",
     '''def gap_measures(con: sqlite3.Connection, doc: str, tried: dict) -> dict:
''',
     '''def _never_sent(page, text) -> bool:
    """GAPS2_2026_10_07: True when translate_passages.py would skip this passage silently (no call, no
    outcome record): page below 1, should_translate() false, or clean_for_mt() empty. Same functions."""
    try:
        from normalize_text import normalize_sanskrit
        from text_filters import should_translate, clean_for_mt
    except Exception:
        return False
    try:
        if int(page or 0) < 1:
            return True
        normed = normalize_sanskrit(text or "")
        return (not should_translate(normed, min_dev=0.05)) or not clean_for_mt(normed)
    except Exception:
        return False


def gap_measures(con: sqlite3.Connection, doc: str, tried: dict) -> dict:
''', 1),
    ("counters",
     '''        res.update({lang + "_gap": 0, lang + "_gap_tried": 0, lang + "_gap_lowq": 0, lang + "_gap_refs": []})
''',
     '''        res.update({lang + "_gap": 0, lang + "_gap_tried": 0, lang + "_gap_lowq": 0, lang + "_gap_refs": [],
                    lang + "_gap_never": 0})   # GAPS2_2026_10_07
''', 1),
    ("text in the query",
     '''        f"""SELECT p.page_no, p.idx, {q}, TRIM(COALESCE(p.translation,'')) <> '',
                   TRIM(COALESCE(l.translation,'')) <> ''
            FROM passages p JOIN docs d ON d.id = p.doc_id''',
     '''        f"""SELECT p.page_no, p.idx, {q}, TRIM(COALESCE(p.translation,'')) <> '',
                   TRIM(COALESCE(l.translation,'')) <> '', COALESCE(p.text,'')
            FROM passages p JOIN docs d ON d.id = p.doc_id''', 1),
    ("classify",
     '''    for page, idx, qs, has_en, has_hi in rows:
        try:
            low = qs is not None and 0.0 < float(qs) < GAP_MIN_QUALITY
        except (TypeError, ValueError):
            low = False
        for lang, has in (("en", has_en), ("hi", has_hi)):
            if has:
                continue
            was_tried = (int(page or 0), int(idx or 0)) in tried.get((doc, lang), ())
            if was_tried or low:
                res[lang + "_gap"] += 1
                res[lang + ("_gap_tried" if was_tried else "_gap_lowq")] += 1
''',
     '''    for page, idx, qs, has_en, has_hi, text in rows:
        try:
            low = qs is not None and 0.0 < float(qs) < GAP_MIN_QUALITY
        except (TypeError, ValueError):
            low = False
        never = None   # computed only for an untranslated row (GAPS2_2026_10_07)
        for lang, has in (("en", has_en), ("hi", has_hi)):
            if has:
                continue
            was_tried = (int(page or 0), int(idx or 0)) in tried.get((doc, lang), ())
            if not (was_tried or low) and never is None:
                never = _never_sent(page, text)
            if was_tried or low or never:
                res[lang + "_gap"] += 1
                res[lang + ("_gap_tried" if was_tried else "_gap_lowq" if low else "_gap_never")] += 1
''', 1),
    ("message",
     '''        what = ("%d passage(s) without %s cannot be translated as printed (%d tried with unusable output, "
                "%d below OCR quality %.2f; e.g. %s)" % (gap, name, s.get(lang + "_gap_tried", 0),
                                                        s.get(lang + "_gap_lowq", 0), GAP_MIN_QUALITY,
                                                        ", ".join(s.get(lang + "_gap_refs") or [])))
''',
     '''        what = ("%d passage(s) without %s cannot be translated as printed (%d tried with unusable output, "
                "%d below OCR quality %.2f, %d never sent: page 0 or no translatable Sanskrit; e.g. %s)"
                % (gap, name, s.get(lang + "_gap_tried", 0), s.get(lang + "_gap_lowq", 0), GAP_MIN_QUALITY,
                   s.get(lang + "_gap_never", 0), ", ".join(s.get(lang + "_gap_refs") or [])))   # GAPS2_2026_10_07
''', 1),
]

TARGETS = [(Path("scripts/corpus_status.py"), EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_gaps2")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_gaps2_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
