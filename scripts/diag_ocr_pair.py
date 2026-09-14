#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_ocr_pair.py - are these two documents the same book, and if so which
scan is cleaner?  v1, 2026-09-14.

READ-ONLY. Writes nothing, calls no API, needs no external data.
Run it on WINDOWS - SQLite over the Claude device bridge fails with
'disk I/O error' because the -shm lock file cannot be mapped.

WHY THIS IS A DIFFERENT QUESTION FROM diag_retire_check
--------------------------------------------------------
diag_retire_check answers "is the keeper derived from the retiree", by
applying the same transform and matching verse for verse. That works when one
document was MADE from the other, as nilamata_seg was.

It is the wrong tool for two independent OCR passes over one printed book.
Those share no exact strings at all - every character is a separate guess by a
separate engine - so the check would report near-total loss and refuse, which
would be true and useless.

  shiva_dhanur_veda   ... vatimtah SI: slacsah savamkama saho yudhi 48
  dhanur_veda_shiva.. ... vartitah syadunah slaksnah sarvakarmasaho yudhi 48

Same half-verse, same verse number, not one matching substring of length 40.

WHAT ACTUALLY DISCRIMINATES
---------------------------
Three signals, none of which needs the texts to agree character by character:

  1. VERSE NUMBERS. A printed edition numbers its verses, and OCR reads those
     numerals far more reliably than it reads conjuncts. If page 5 of both
     documents ends at verse 48 and page 7 at 72, they are the same setting of
     the same book. This is the strongest signal available and it is almost
     free.

  2. PER-PAGE n-GRAM CONTAINMENT, in both directions, as
     diag_corpus_overlap.py does corpus-wide. Two passes over one page still
     agree on the words the engine got right.

  3. CONTAMINATION, which decides which pass to keep:
       latin_share      Latin letters as a share of all letters. A Devanagari
                        text has none except where the scanner swept in a
                        running head or a library stamp.
       furniture        hits on the printed page's own apparatus - press and
                        collection names, bracketed running titles.
       broken_share     rows carrying the debris characters OCR leaves when a
                        conjunct defeats it.

Nothing here decides anything for you. It prints the three signals and says
what they jointly imply, and the reason it can do that honestly is that the
signals are independent: verse numbers say whether it is one book, and
contamination says which scan to keep. A single blended score would hide both.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import zlib

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

MARK = "OCR_PAIR_2026_09_14"
DEV_LETTER = re.compile("[\\u0900-\\u0963\\u0970-\\u097F]")
DEV_DIGIT_RUN = re.compile("[\\u0966-\\u096F]+")
LATIN = re.compile("[A-Za-z]")
NGRAM = 5

# The printed page's own apparatus. Deliberately conservative and ASCII-only:
# a press name or a bracketed running title is furniture in any book, whereas
# a Devanagari pattern would need tuning per edition and would be one more
# place to be wrong.
FURNITURE = re.compile(
    r"UNIVERSITY|COLLECTION|MANAGEMENT|LITERATURE|PRESS|ACADEMY|LIBRARY"
    r"|MAHARISHI|Reference:|\[[^\]]{4,40}\]", re.I)
# What OCR leaves when a conjunct defeats it: stray combining marks stranded
# after a space, the danda-like vertical bar, and runs of isolated capitals.
BROKEN = re.compile("(?:^|\\s)[\\u0951-\\u0954\\u093C\\u094D]|[A-Z]{2,}\\s+[A-Z]{2,}")

DEV2AR = dict(zip("".join(chr(c) for c in range(0x0966, 0x0970)), "0123456789"))


def dev_int(run):
    try:
        return int("".join(DEV2AR.get(c, "") for c in run))
    except ValueError:
        return None


def grams(s, sample=4):
    out = set()
    for i in range(len(s) - NGRAM + 1):
        h = zlib.crc32(s[i:i + NGRAM].encode("utf-8"))
        if h % sample == 0:
            out.add(h)
    return out


def letters_only(t):
    return "".join(DEV_LETTER.findall(t or ""))


def measure(rows):
    """Contamination for one document."""
    dev = lat = 0
    furn = brok = nrows = 0
    for _pg, t in rows:
        t = t or ""
        nrows += 1
        dev += len(DEV_LETTER.findall(t))
        lat += len(LATIN.findall(t))
        if FURNITURE.search(t):
            furn += 1
        if BROKEN.search(t):
            brok += 1
    tot = dev + lat
    return {
        "rows": nrows,
        "dev_letters": dev,
        "latin_letters": lat,
        "latin_share": round(100.0 * lat / tot, 2) if tot else 0.0,
        "furniture_rows": furn,
        "furniture_share": round(100.0 * furn / nrows, 1) if nrows else 0.0,
        "broken_rows": brok,
        "broken_share": round(100.0 * brok / nrows, 1) if nrows else 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--sample", type=int, default=4)
    ap.add_argument("--show-pages", type=int, default=12)
    x = ap.parse_args()

    if not os.path.exists(x.db):
        sys.exit("not found: %s - run from the repo root" % x.db)
    con = sqlite3.connect("file:%s?mode=ro" % x.db.replace("\\", "/"), uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")

    def rows_of(code):
        r = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
        if not r:
            sys.exit("doc code %r not found" % code)
        return con.execute(
            "SELECT page_no, text FROM passages WHERE doc_id=? "
            "AND TRIM(COALESCE(text,''))<>'' ORDER BY page_no, idx", (r[0],)).fetchall()

    A, B = rows_of(x.a), rows_of(x.b)
    print("%s" % MARK)
    print("  A  %-40s %4d row(s)" % (x.a, len(A)))
    print("  B  %-40s %4d row(s)" % (x.b, len(B)))
    print("")

    # ---------------------------------------------------------------- 1
    print("1. VERSE NUMBERS PER PAGE")
    print("   OCR reads numerals far more reliably than conjuncts. If both")
    print("   documents close the same pages on the same verse, it is one book.")
    print("")
    def nums(rows):
        d = {}
        for pg, t in rows:
            got = [dev_int(m) for m in DEV_DIGIT_RUN.findall(t or "")]
            d.setdefault(pg, []).extend([g for g in got if g is not None and 0 < g < 2000])
        return d
    na, nb = nums(A), nums(B)
    pages = sorted(set(na) & set(nb))
    print("   %-6s %-30s %-30s %s" % ("page", "A: verse numbers", "B: verse numbers", "last"))
    agree = 0
    for pg in pages[:x.show_pages]:
        a_s, b_s = na[pg], nb[pg]
        la = max(a_s) if a_s else None
        lb = max(b_s) if b_s else None
        same = (la is not None and la == lb)
        agree += 1 if same else 0
        print("   %-6s %-30s %-30s %s" % (
            pg, ",".join(str(v) for v in a_s[:8]), ",".join(str(v) for v in b_s[:8]),
            ("SAME (%s)" % la) if same else "differ"))
    for pg in pages[x.show_pages:]:
        if na[pg] and nb[pg] and max(na[pg]) == max(nb[pg]):
            agree += 1
    if len(pages) > x.show_pages:
        print("   ... %d more shared page number(s)" % (len(pages) - x.show_pages))
    share = 100.0 * agree / max(1, len(pages))
    print("")
    print("   pages where the highest verse number agrees: %d of %d  (%.0f%%)"
          % (agree, len(pages), share))
    print("")

    # ---------------------------------------------------------------- 2
    print("2. PER-PAGE n-GRAM CONTAINMENT, both directions")
    ga = {}
    gb = {}
    for pg, t in A:
        ga.setdefault(pg, set()).update(grams(letters_only(t), x.sample))
    for pg, t in B:
        gb.setdefault(pg, set()).update(grams(letters_only(t), x.sample))
    mins = []
    print("   %-6s %8s %8s %8s %8s" % ("page", "C(A|B)", "C(B|A)", "gramsA", "gramsB"))
    for pg in pages[:x.show_pages]:
        sa, sb = ga.get(pg, set()), gb.get(pg, set())
        if not sa or not sb:
            continue
        inter = len(sa & sb)
        cab, cba = inter / float(len(sa)), inter / float(len(sb))
        mins.append(min(cab, cba))
        print("   %-6s %7.1f%% %7.1f%% %8d %8d" % (pg, 100 * cab, 100 * cba, len(sa), len(sb)))
    for pg in pages[x.show_pages:]:
        sa, sb = ga.get(pg, set()), gb.get(pg, set())
        if sa and sb:
            inter = len(sa & sb)
            mins.append(min(inter / float(len(sa)), inter / float(len(sb))))
    med = 0.0
    if mins:
        mm = sorted(mins)
        med = mm[len(mm) // 2] if len(mm) % 2 else (mm[len(mm) // 2 - 1] + mm[len(mm) // 2]) / 2.0
    print("")
    print("   median per-page containment, weaker direction: %.1f%%" % (100 * med))
    print("")

    # ---------------------------------------------------------------- 3
    print("3. CONTAMINATION - which scan to keep")
    ma, mb = measure(A), measure(B)
    print("")
    print("   %-24s %14s %14s" % ("", x.a[:14], x.b[:14]))
    for k, label in (("rows", "rows"),
                     ("dev_letters", "Devanagari letters"),
                     ("latin_letters", "Latin letters"),
                     ("latin_share", "Latin share %"),
                     ("furniture_rows", "rows with furniture"),
                     ("furniture_share", "furniture rows %"),
                     ("broken_rows", "rows with debris"),
                     ("broken_share", "debris rows %")):
        print("   %-24s %14s %14s" % (label, ma[k], mb[k]))
    print("")

    en_a = con.execute("SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id "
                       "WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''", (x.a,)).fetchone()[0]
    en_b = con.execute("SELECT COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id "
                       "WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''", (x.b,)).fetchone()[0]
    print("   English translations already paid for:  %s %d,  %s %d" % (x.a, en_a, x.b, en_b))
    print("")

    # ---------------------------------------------------------------- verdict
    print("WHAT THE THREE SIGNALS JOINTLY IMPLY")
    print("")
    same_book = share >= 60.0 or med >= 0.35
    if same_book:
        print("   SAME BOOK. %.0f%% of shared pages close on the same verse number"
              % share)
        print("   and the median weaker-direction containment is %.1f%%. Two OCR"
              % (100 * med))
        print("   passes over one printed setting.")
    else:
        print("   NOT the same book on this evidence: %.0f%% page agreement,"
              % share)
        print("   %.1f%% median containment. Leave both." % (100 * med))
    print("")
    dirty_a = ma["latin_share"] + ma["furniture_share"] + ma["broken_share"]
    dirty_b = mb["latin_share"] + mb["furniture_share"] + mb["broken_share"]
    cleaner = x.a if dirty_a < dirty_b else x.b
    dirtier = x.b if cleaner == x.a else x.a
    if same_book:
        print("   CLEANER SCAN: %s" % cleaner)
        print("   (Latin share + furniture rows + debris rows: %.1f vs %.1f. Three"
              % (min(dirty_a, dirty_b), max(dirty_a, dirty_b)))
        print("   independent contamination measures, added only to rank them -")
        print("   the individual figures above are what you should read.)")
        print("")
        paid = en_a if dirtier == x.a else en_b
        if paid > 0:
            print("   NOTE: %s is the DIRTIER scan and already carries %d paid"
                  % (dirtier, paid))
            print("   translations. The cleaner scan is the one that should be")
            print("   translated and kept. That is the reverse of the usual case,")
            print("   and it is why this needs a decision rather than a default.")
        print("")
        print("   Neither diag_retire_check nor retire_doc is the right tool for")
        print("   this pair: the check matches text verbatim and two OCR passes")
        print("   never match verbatim. Retiring one is a judgement about which")
        print("   scan to trust, and ENTERPRISE_PATH item 12 records that this")
        print("   project has no adjudicator for engine disagreement yet:")
        print("   'ocr_variants records both readings and no code chooses between")
        print("   them.' This file is the measurement that adjudicator would need.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())