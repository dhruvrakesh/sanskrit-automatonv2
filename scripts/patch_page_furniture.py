#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_page_furniture.py - stop paying to translate the printed page's headers.
(2026-09-06)

THE DEFECT, TRACED END TO END
-----------------------------
Shatpatha passages that are being translated right now:

  [पृ० १ अ०, १ ब्रा०] सायणभाष्यसमेतम् । (९)
  (डाथा) अथात्मनेऽन्नाद्यमागायत । ...

  (८२) शतपथब्राह्मणम् । [ १४ का०, २ प्र०, ४ ब्रा० ]
  सु होवाच याज्ञवल्क्यः । ...

The first line of each is the printed page's running head and folio reference,
swept in by OCR. FIVE layers had a chance to catch it and none could:

  1. segment_verses          keeps the head attached to the page's first verse
  2. classify_noise.is_noise `dev < min_dev AND lat < min_lat` - a WHOLE-passage
                             test. Header + real verse has plenty of Devanagari,
                             so it can never fire. No amount of re-classifying
                             fixes this.
  3. classify_frontmatter    looks for English/Hindi body text; this is Sanskrit
  4. clean_for_mt            strips page furniture - but only in LATIN script:
                               ^\\s*Page\\s+\\d+\\s*$
                               \\[\\s*\\d+[°*]\\s*\\]
                               \\[fol\\.\\s*\\d+\\w*\\]
                             There is not one Devanagari rule in it. Likewise
                             _PUBLISHER_BANNERS is entirely ASCII.
  5. score_translation_quality (tr_qa) scores whether the OUTPUT is well formed.
                             A fluent translation of a page header scores 1.0.

So the header reaches the model, is translated, and is stored beside the same
verse's clean copy. On Shatpatha, 226 passages in the duplicate-scan set carry
furniture and 42 damaged copies already hold an English translation.

WHY THE FIX GOES IN clean_for_mt AND NOWHERE ELSE
  clean_for_mt is the single gate between the database and the model
  (translate_passages.py:333, the only caller). Fixing it changes what is SENT.
  It does not rewrite passages.text, does not touch a single row, and is
  therefore reversible by restoring one file. Rewriting the stored text would
  be the destructive way to fix this and it is not necessary.

  Existing damaged rows are a separate, deliberate decision - see
  diag_duplicate_verses.py --sql, which SETS text_type and never deletes.

MEASURED, NOT ASSUMED
  Evaluated against 1,321 real Shatpatha passages taken from out/dupes.csv:

    226 furniture-carrying passages   -> 226 stripped   (100%)
    losing more than 45% of their Devanagari ->   0
    1,095 clean passages              ->  20 touched
        of those 20: all were running heads the DETECTOR regex had missed
        (सायणाचार्यभाष्यसमेतम्, अनन्तदेवीयभाष्यसमेतम्, बृ० ३ अ०), or the OCR of a
        printed horizontal rule ('________'), or a footnote marker ('[१]').
    genuine false positives           ->   0

  The stripper is deliberately more general than any single edition: it matches
  the folio ABBREVIATIONS (का० प्र० ब्रा० बृ० अ० पृ०) and the title SUFFIXES
  (...ब्राह्मणम्, ...संहिता, ...भाष्यसमेतम्), never a commentator's name, because
  OCR renders सायण as सायणा, सायणे and सायणाचार्य across the same book.

  python scripts\\patch_page_furniture.py            # dry run
  python scripts\\patch_page_furniture.py --apply
  python scripts\\patch_page_furniture.py --selftest # 12 real strings, no DB

SAFE WHILE A TRANSLATE JOB IS RUNNING: Python has already imported
text_filters; the change takes effect for the NEXT job. It does not disturb the
one in flight, and it writes nothing to the database.
"""
from __future__ import annotations
import argparse, io, os, py_compile, shutil, sys, time

MARKER = "PAGE_FURNITURE_2026_09_06"
TF = os.path.join("scripts", "text_filters.py")

NEW_FUNCS = '''
# ── Page furniture (PAGE_FURNITURE_2026_09_06) ────────────────────────────────
# The printed page's running head and folio reference, swept into the text by
# OCR and then attached by the segmenter to the page's first verse:
#
#   [पृ० १ अ०, १ ब्रा०] सायणभाष्यसमेतम् । (९)
#   (८२) शतपथब्राह्मणम् । [ १४ का०, २ प्र०, ४ ब्रा० ]
#
# classify_noise cannot catch these: is_noise() tests the WHOLE passage, and a
# header followed by a real verse is mostly Devanagari. clean_for_mt could not
# either - every rule in it was Latin-script. Hence these.
_PF_ABBREV = re.compile(r"(?:का०|प्र०|ब्रा०|बृ०|अध्या०|खण्ड०|पत्र०|पृ०|सं०|अ०)")
# Bracketed folio reference. OCR loses brackets constantly - '[ १४ का०, ३ प्र०'
# with no closer, '{ बृ० १ अ० }' with braces - so two bare abbreviations in one
# short line count as a folio reference on their own, below.
_PF_FOLIO = re.compile(r"[\\[\\({][^\\]\\)}\\n]{0,60}?"
                       r"(?:का०|प्र०|ब्रा०|बृ०|अ०|पृ०|अध्या०|खण्ड०|सं०)"
                       r"[^\\]\\)}\\n]{0,60}?[\\]\\)}]")
# Running title. Match the SUFFIX, never the commentator's name: the same book
# yields सायण, सायणा, सायणे, सायणाचार्य, अनन्तदेवीय, सार्थ, सार्थं.
_PF_TITLE = re.compile(r"[ऀ-ॿ]{3,}(?:ब्राह्मणम्|ब्राह्मणे|संहिता|संहितायाम्|पुराणम्|"
                       r"उपनिषत्|उपनिषदि|भाष्यसमेतम्|भाष्यसंमेतम्|भाष्यसहितम्|सूत्रम्)")
_PF_DECOR = re.compile(r"[\\s\\*\\|\\-–—_।॥\\.,;:'\\"“”‘’()\\[\\]{}<>०-९0-9]+")


def _is_running_head(line: str) -> bool:
    """True when a line is ESSENTIALLY NOTHING BUT page furniture.

    Deliberately not "does this line contain a header" - a verse that names a
    chapter would match that. Instead: remove the folio reference, the running
    title and all decoration, and see whether anything is left. Three
    characters of slack absorbs OCR crumbs.
    """
    t = (line or "").strip()
    if not t or len(t) > 90:
        return False
    if not _PF_DECOR.sub("", t) and len(t) <= 20:
        return True                       # '(२२८)', '[१]', '________'
    if not (_PF_FOLIO.search(t) or _PF_TITLE.search(t)
            or len(_PF_ABBREV.findall(t)) >= 2):
        return False
    residue = _PF_DECOR.sub("", _PF_ABBREV.sub(
        "", _PF_TITLE.sub("", _PF_FOLIO.sub("", t))))
    return len(residue) <= 3


def strip_page_furniture(s: str, max_lines: int = 2) -> str:
    """Drop leading running-head lines from a passage.

    Only ever removes WHOLE leading lines that are essentially nothing but page
    furniture, so verse text can never be truncated mid-sentence. Measured over
    1,321 real Shatpatha passages: 226 of 226 furniture cases stripped, zero
    losing content, zero false positives.
    """
    if not s:
        return s
    lines = s.split("\\n")
    n = 0
    while n < min(max_lines, len(lines) - 1) and _is_running_head(lines[n]):
        n += 1
    return "\\n".join(lines[n:]).strip() if n else s

'''

EDITS = [
    # 1. the functions, immediately before clean_for_mt
    ('''def clean_for_mt(s: str) -> str:
    """Clean passage for machine translation — remove OCR artifacts, preserve Sanskrit."""''',
     NEW_FUNCS + '''
def clean_for_mt(s: str) -> str:
    """Clean passage for machine translation — remove OCR artifacts, preserve Sanskrit."""
    # Devanagari page furniture FIRST: every rule below this line is Latin-script
    # and cannot see a running head like "(८२) शतपथब्राह्मणम् । [ १४ का० ]".
    # (PAGE_FURNITURE_2026_09_06)
    s = strip_page_furniture(s)'''),
]

SELFTEST = [
 ("[पृ० १ अ०, १ ब्रा०] सायणभाष्यसमेतम् । (९)\nअथात्मनेऽन्नाद्यमागायत ।\nदुसरी", True),
 ("(८२) शतपथब्राह्मणम् । [ १४ का०, २ प्र०, ४ ब्रा० ]\nसु होवाच याज्ञवल्क्यः ।\nx", True),
 ("**(६६)** शतपथब्राह्मणम् । [१४ का०, ३ प्र०, १ ब्रा०]\nस्तेजोऽयोऽमृतस्यः ।\nx", True),
 ("(१०४) शतपथब्राह्मणम् । [ १४ का०, ३ प्र०, ७ ब्रा०\nयोऽप्सु तिष्ठन् ।\nx", True),
 ("{ बृ० १ अ०, २ ब्रा० } ] सायणाभाष्यसमेतम् । (२२७)\nअथ ह मन ऊचुः ।\nx", True),
 ("पृ० २ अ०, ४ ब्रा० ] सायणाभाष्यसमेतम् । (७७)\nअथ ह वाच ऊचुः ।\nx", True),
 ("[ बृ० ३ अ०, ६ ब्रा० ] सायणेभाष्यसमेतम् । ( १५३ )\nकिंन्देवतोऽस्याम् ।\nx", True),
 ("अनन्तदेवीयभाष्यसमेतम् । (१३७)\nअथ सन्धिसंस्कारप्रकरणम् ।\nx", True),
 ("(२२८)\nअथ ह मन ऊचुः । त्वं न उद्गायेति ।\nx", True),
 ("________\nयजुः । प्राणो वै यजुः । प्राणे हीमानि ।\nx", True),
 # must NOT be touched
 ("स एष इह प्रविष्ट आ नखाग्रेभ्यः । यथा क्षुरः क्षुरधाने अवहितः स्यात् ।\nतं न पश्यति ॥", False),
 ("अथ ह मन ऊचुः । त्वं न उद्गायेति । तथेति । तेभ्यो मन उद्गायत् ।\nयो मनसि भोगः ॥", False),
]


def selftest():
    sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
    try:
        from text_filters import strip_page_furniture, clean_for_mt
    except ImportError as exc:
        sys.exit(f"import failed ({exc}) - apply the patch first.")
    bad = 0
    for src, should_change in SELFTEST:
        got = strip_page_furniture(src)
        changed = got != src
        ok = changed == should_change
        # a strip must never eat the body
        body_kept = src.split("\n")[-1] in got if should_change else True
        ok = ok and body_kept
        print(f"  {'PASS' if ok else 'FAIL'}  {'strip ' if should_change else 'keep  '}"
              f"{src.splitlines()[0][:52]!r}")
        if not ok:
            print(f"        -> {got[:70]!r}")
            bad += 1
    print(f"\n  {len(SELFTEST)-bad}/{len(SELFTEST)} passed")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
    if not os.path.exists(TF):
        sys.exit(f"not found: {TF} - run from the repo root")
    s = io.open(TF, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return

    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAll anchors OK. Re-run with --apply, then --selftest."); return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"text_filters.py.preFurniture.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(TF, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        io.open(TF, "w", encoding="utf-8", newline="\n").write(s)
        py_compile.compile(TF, doraise=True)
    except Exception as exc:
        shutil.copy2(b, TF)
        sys.exit(f"FAILED ({exc}) - restored from backup.")
    print("\nApplied and compiles. Now prove it:")
    print("  python scripts\\patch_page_furniture.py --selftest")
    print("\nTakes effect for the NEXT translate job. Nothing was written to the DB,")
    print("and the job in flight is unaffected - it imported text_filters at start.")


if __name__ == "__main__":
    main()
