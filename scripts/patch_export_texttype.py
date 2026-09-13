#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_export_texttype.py  (2026-09-13)  EXPORT_TEXTTYPE_2026_09_13

The exporter is the only script in this pipeline that ignores text_type.

WHAT IT PRODUCED
AphorismsOfSandilya_book.pdf, 426 pages. Its first three "source leaves",
each labelled SANSKRIT and duplicated verbatim into the IAST block as
though transliterated:

  LEAF-0001  BIBLIOTHECA INDICA; A COLLECTION OF ORIENTAL WORKS
             PUBLISHED UNDER THE SUPERINTENDENCE OF THE ASIATIC SOCIETY
             OF BENGAL ... EDITED BY J. R. BALLANTYNE, LL. D. ... 1861.
  LEAF-0002  Ind L 212.35 / HARVARD COLLEGE LIBRARY / FROM THE LIBRARY
             OF JAMES HAUSEN WOODS / 1935 / F
  LEAF-0003  ADVERTISEMENT. - THE following work was more than half
             printed, when Dr. Ballantyne left this country ...

A title page, a library bookplate and an English publisher's preface,
set as scripture, with "[No supplied english text for this unit.]"
printed underneath the English.

THE CLASSIFIER ALREADY CAUGHT ALL THREE
Passages 108993, 108994 and 108995 are classified text_type='frontmatter'
in context.db. The document holds 125 frontmatter rows, 6 noise and 11
colophon. Nothing needed detecting. The exporter simply never asked.

Twelve other scripts apply the filter - build_embeddings, classify_doc,
classify_frontmatter, classify_noise, dashboard, db_utils, and every
diag_*. /library uses it, which is why the Library's verse counts have
always been lower than the exporter's. export_html.py has no mention of
text_type anywhere in the file.

MEASURED EFFECT
  AphorismsOfSandilya       598 rows -> 467 kept,  131 dropped (21.9%)
  2015_405693_Shatpath...  2441 rows -> 2259 kept,  182 dropped (7.5%)
  nilamata_seg             1393 rows -> 1393 kept,    0 dropped
  MBh01                    6957 rows -> 6957 kept,    0 dropped

The two clean texts are untouched, which is the point: this removes
catalogue scaffolding, not text.

WHAT IT DOES NOT DO
colophon is KEPT. A colophon is textual apparatus, not scaffolding, and
the filter used everywhere else in this codebase excludes exactly noise
and frontmatter. Inventing a different policy here would put the exporter
back out of step with the rest of the system, which is the whole fault.

--keep-frontmatter restores the old behaviour, in the same spirit as the
existing --keep-junk. A filter you cannot switch off is a filter you
cannot debug.

Run from the repo root:  python scripts/patch_export_texttype.py
Add --check to verify anchors without writing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARK = "EXPORT_TEXTTYPE_2026_09_13"
EXPORT = Path("scripts/export_html.py")

FETCH_OLD = '''def _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=None):
    pg = _page_col(con); idx_sel, idx_order = _idx_expr(con)
    pcols = _colnames(con, "passages")
    vref = "p.verse_ref" if "verse_ref" in pcols else "NULL"
    chap = "p.chapter"   if "chapter"   in pcols else "NULL"
    iast = "p.iast"      if "iast"      in pcols else "NULL"
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {pg} BETWEEN ? AND ?"; prm = prm + (lo,hi)'''

FETCH_NEW = '''def _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=None, keep_frontmatter=False):
    pg = _page_col(con); idx_sel, idx_order = _idx_expr(con)
    pcols = _colnames(con, "passages")
    vref = "p.verse_ref" if "verse_ref" in pcols else "NULL"
    chap = "p.chapter"   if "chapter"   in pcols else "NULL"
    iast = "p.iast"      if "iast"      in pcols else "NULL"
    where, prm = _doc_where(con, doc)
    where = _and(where) + f" {pg} BETWEEN ? AND ?"; prm = prm + (lo,hi)
    # EXPORT_TEXTTYPE_2026_09_13
    # Every other consumer of this table filters here and this one did not,
    # so AphorismsOfSandilya shipped a Harvard bookplate and an 1861 title
    # page as Sanskrit verse. The classifier had already marked them
    # frontmatter. Same predicate as db_utils, dashboard/library,
    # build_embeddings and the diag_* scripts - colophon is deliberately
    # kept, being apparatus rather than scaffolding.
    if "text_type" in pcols and not keep_frontmatter:
        where += " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"'''

# main() has TWO _export_one call sites and both ended `debug=args.debug)`.
# They differ only by indentation, and the 24-space form is a SUBSTRING of the
# 28-space one, so each anchor carries a leading newline. This is the same
# collision that split the radial block in September.
SITE_A_OLD = ("\n                            hi_label=hi_label, want_toc=want_toc, "
              "want_footnotes=want_footnotes, debug=args.debug)")
SITE_A_NEW = ("\n                            hi_label=hi_label, want_toc=want_toc, "
              "want_footnotes=want_footnotes, debug=args.debug,\n"
              "                            keep_frontmatter=args.keep_frontmatter)")

SITE_B_OLD = ("\n                        hi_label=hi_label, want_toc=want_toc, "
              "want_footnotes=want_footnotes, debug=args.debug)")
SITE_B_NEW = ("\n                        hi_label=hi_label, want_toc=want_toc, "
              "want_footnotes=want_footnotes, debug=args.debug,\n"
              "                        keep_frontmatter=args.keep_frontmatter)")

ARG_OLD = '''    ap.add_argument("--keep-junk", action="store_true")'''
ARG_NEW = '''    ap.add_argument("--keep-junk", action="store_true")
    ap.add_argument("--keep-frontmatter", action="store_true",
                    help="EXPORT_TEXTTYPE_2026_09_13: keep rows classified "
                         "noise/frontmatter. Off by default; every other script "
                         "in this pipeline excludes them. A filter you cannot "
                         "switch off is one you cannot debug.")'''

RENDER_CALL_OLD = '''    recs = _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=hi_lang)'''
RENDER_CALL_NEW = '''    recs = _fetch(con, doc, lo, hi, san_col, en_col, hi_lang=hi_lang,
                  keep_frontmatter=keep_frontmatter)'''

SIG_OLD = '''                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False):'''
SIG_NEW = '''                hi_lang=None, hi_label="Hindi", want_toc=True, want_footnotes=True, debug=False,
                keep_frontmatter=False):'''


def replace_one(text: str, old: str, new: str, label: str):
    n = text.count(old)
    if n != 1:
        return text, ["%s: matched %d times, expected exactly 1" % (label, n)]
    return text.replace(old, new), []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not EXPORT.exists():
        print("FAIL: %s not found. Run from the repo root." % EXPORT)
        return 2

    raw = EXPORT.read_bytes()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    newline = "\r\n" if crlf > lf else "\n"

    src = EXPORT.read_text(encoding="utf-8")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if "text_type" in src:
        print("FAIL: export_html.py already mentions text_type. Read it before")
        print("      applying this - the premise of the patch is that it does not.")
        return 2

    problems: list[str] = []
    src, p = replace_one(src, FETCH_OLD, FETCH_NEW, "_fetch filter"); problems += p
    src, p = replace_one(src, SIG_OLD, SIG_NEW, "render signature"); problems += p
    src, p = replace_one(src, RENDER_CALL_OLD, RENDER_CALL_NEW, "_fetch call"); problems += p
    src, p = replace_one(src, ARG_OLD, ARG_NEW, "--keep-frontmatter"); problems += p
    src, p = replace_one(src, SITE_A_OLD, SITE_A_NEW, "call site A"); problems += p
    src, p = replace_one(src, SITE_B_OLD, SITE_B_NEW, "call site B"); problems += p

    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1

    # The flag has to reach the renderer from argv. Confirm the wiring exists
    # rather than assuming it, because a silently unused flag is worse than no
    # flag: it tells the operator the behaviour is switchable when it is not.
    # The first version of this guard only checked the INNER call and passed
    # while --keep-frontmatter was inert: argparse defined it and main() never
    # passed it on. A flag that reports itself present while doing nothing is
    # exactly the fault this patch exists to remove, so check the whole chain.
    if "keep_frontmatter=keep_frontmatter" not in src:
        print("FAIL: the flag does not reach _fetch from _export_one.")
        return 1
    n_main = src.count("keep_frontmatter=args.keep_frontmatter")
    if n_main != 2:
        print("FAIL: main() threads the flag into %d of 2 _export_one call sites."
              % n_main)
        print("      An inert switch is worse than no switch.")
        return 1

    if args.check:
        print("All 6 anchors matched exactly once, and the flag reaches both")
        print("main() call sites. --check: nothing written.")
        return 0

    EXPORT.write_text(src, encoding="utf-8", newline=newline)
    print("Patched: %s  (6 edits, endings preserved as %s)"
          % (EXPORT, "CRLF" if newline == "\r\n" else "LF"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
