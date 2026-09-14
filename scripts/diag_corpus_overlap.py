#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_corpus_overlap.py - is any text in this corpus present twice?  v1, 2026-09-14.

READ-ONLY. mode=ro plus a busy timeout, safe beside a running translation.
Run it on WINDOWS - SQLite over the Claude device bridge fails with
'disk I/O error' because the -shm lock file cannot be mapped.

WHY THIS FILE EXISTS, AND WHY IT IS BUILT THIS WAY
--------------------------------------------------
diag_duplicate_verses.py answers this question WITHIN one document, and the v2
header of that file records exactly what v1 of it got wrong: it called 1,705 of
2,059 signatures duplicates - 83% - by deciding damage from Devanagari share
and never checking fan-out. Its own words: "That is not a finding, it is a
broken gate, and acting on it would have damaged the corpus."

On 2026-09-14 I shipped the same class of error ACROSS documents. automaton.py
--duplicates paired any two documents with the same ROW COUNT and duly reported
that shiksha_lomashi_shiksha (8 rows) might be smriti_07likhita_smriti (8
rows), and that harita_caturtha_sthanam (17) might be smriti_03apastamba_smriti
(17). Row count is not evidence. Nine of the eleven pairs it printed were
noise, and the one real derived pair in the corpus - upapurana_nilamata_purana
and nilamata_seg - it missed entirely, because 111 is not 1,393.

This file replaces that gate with the method this project already validated.
Three independent signals, reported separately and never summed:

  1. EXACT ROW MATCH. Normalise a passage to its Devanagari characters only and
     hash it. The same hash in two documents is the same text. No threshold, no
     judgement call, no way to over-fire.

  2. DOCUMENT CONTAINMENT. Devanagari 5-gram sets, exactly as
     diag_duplicate_verses.sig() builds them, compared as |A and B| / |A|.
     This is the signal that catches a RE-SEGMENTED copy: nilamata_seg holds
     the same text as upapurana_nilamata_purana cut at different boundaries, so
     not one row matches exactly while containment is near total.

     Memory discipline: grams are hashed and kept only where the hash is
     divisible by SAMPLE. Because the sample is taken on the gram's own value,
     the same gram is sampled in every document it appears in, so containment measured on the
     sample is an unbiased estimate of containment on the whole. Every
     document's sample size is printed, and any pair whose smaller sample falls
     under --min-sample is reported as UNRELIABLE rather than as a finding.

  3. PROVENANCE. resegment_doc.py stamps engine='resegment-devnum' on the rows
     it emits, so a derived document says so about itself. This is the only one
     of the three that is evidence rather than inference.

Nothing here writes. Nothing here decides. It prints candidates, says how
strong each signal is, and puts the cost of each candidate beside it - how many
rows of each member already carry a paid translation - so the question "are we
paying twice" has a number and not an opinion.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import zlib

DEV_RUN = re.compile("[\u0900-\u097F]+")
NGRAM = 5
MARK = "CORPUS_OVERLAP_2026_09_14"


def dev_only(text):
    return "".join(DEV_RUN.findall(text or ""))


def grams(s, sample):
    """Sampled 5-gram hashes. Sampling on the gram value keeps the estimate
    unbiased: a gram present in two documents is sampled in both or neither."""
    out = set()
    # crc32, not the builtin hash(): PYTHONHASHSEED randomises str hashing per
    # process, so two runs of this file would disagree. An audit that cannot be
    # reproduced is not an audit.
    for i in range(len(s) - NGRAM + 1):
        h = zlib.crc32(s[i:i + NGRAM].encode("utf-8"))
        if h % sample == 0:
            out.add(h)
    return out


def rowhash(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--sample", type=int, default=16,
                    help="keep 1 gram in N (default 16). Lower is more accurate "
                         "and uses more memory.")
    ap.add_argument("--min-sample", type=int, default=200,
                    help="a pair whose smaller document has fewer sampled grams "
                         "than this is reported as unreliable, not as a finding")
    ap.add_argument("--min-chars", type=int, default=24,
                    help="ignore rows with fewer Devanagari characters than this "
                         "for exact matching; short rows collide for trivial reasons")
    ap.add_argument("--containment", type=float, default=0.30,
                    help="report document pairs at or above this containment")
    ap.add_argument("--show", type=int, default=25)
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit("not found: %s - run from the repo root" % a.db)
    con = sqlite3.connect("file:%s?mode=ro" % a.db.replace("\\", "/"), uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")

    print("%s  cross-document overlap" % MARK)
    print("sample 1 gram in %d; a pair needs %d sampled grams to be called anything"
          % (a.sample, a.min_sample))
    print("")

    live = ("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
    rows = con.execute(
        "SELECT d.code, p.id, p.text, "
        "       CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END "
        "FROM passages p JOIN docs d ON d.id=p.doc_id "
        "WHERE %s AND TRIM(COALESCE(p.text,''))<>''" % live)

    gsets = {}
    exact = {}
    docrows = {}
    doctrans = {}
    within = {}
    seen_in_doc = {}
    n = 0
    for code, _pid, text, has_en in rows:
        n += 1
        docrows[code] = docrows.get(code, 0) + 1
        doctrans[code] = doctrans.get(code, 0) + has_en
        d = dev_only(text)
        if not d:
            continue
        gsets.setdefault(code, set()).update(grams(d, a.sample))
        if len(d) >= a.min_chars:
            h = rowhash(d)
            key = (code, h)
            if key in seen_in_doc:
                within[code] = within.get(code, 0) + 1
            else:
                seen_in_doc[key] = True
            exact.setdefault(h, {})
            exact[h][code] = exact[h].get(code, 0) + 1
    print("scanned %d live rows across %d documents" % (n, len(docrows)))
    print("")

    # ------------------------------------------------------------------
    print("1. EXACT ROW MATCH - the same Devanagari text in two documents")
    print("   No threshold. If this is non-empty the text is literally present twice.")
    print("")
    pair_exact = {}
    for h, byc in exact.items():
        if len(byc) < 2:
            continue
        cs = sorted(byc)
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                k = (cs[i], cs[j])
                pair_exact[k] = pair_exact.get(k, 0) + 1
    if not pair_exact:
        print("   (none - no passage's Devanagari text appears in two documents)")
    else:
        print("   %-30s %-30s %8s" % ("document A", "document B", "rows"))
        for (x, y), c in sorted(pair_exact.items(), key=lambda kv: -kv[1])[:a.show]:
            print("   %-30s %-30s %8d" % (x[:30], y[:30], c))
    print("")
    print("   same text twice WITHIN one document (the diag_duplicate_verses case):")
    if not within:
        print("   (none)")
    for code, c in sorted(within.items(), key=lambda kv: -kv[1])[:12]:
        print("   %-30s %6d repeated row(s) of %d" % (code[:30], c, docrows.get(code, 0)))
    print("")

    # ------------------------------------------------------------------
    print("2. DOCUMENT CONTAINMENT - share of A's 5-grams that also occur in B")
    print("   This is what catches a re-segmented copy, where no row matches exactly.")
    print("")
    codes = sorted(gsets, key=lambda c: -len(gsets[c]))
    print("   sampled gram counts (reliability of every number below):")
    for c in codes[:8]:
        print("     %-32s %7d" % (c[:32], len(gsets[c])))
    small = [c for c in codes if len(gsets[c]) < a.min_sample]
    print("     ... %d document(s) below the %d-gram floor: %s"
          % (len(small), a.min_sample, ", ".join(small[:6]) + (" ..." if len(small) > 6 else "")))
    print("")
    found = []
    for i in range(len(codes)):
        A = gsets[codes[i]]
        if not A:
            continue
        for j in range(len(codes)):
            if i == j:
                continue
            B = gsets[codes[j]]
            if not B:
                continue
            inter = len(A & B)
            if not inter:
                continue
            cab = inter / float(len(A))
            if cab >= a.containment:
                reliable = min(len(A), len(B)) >= a.min_sample
                found.append((cab, codes[i], codes[j], len(A), len(B), reliable))
    found.sort(reverse=True)
    if not found:
        print("   (no pair reaches containment %.2f)" % a.containment)
    else:
        print("   %-28s %-28s %7s %7s %7s  %s"
              % ("A (contained)", "B (container)", "C(A|B)", "gramsA", "gramsB", "verdict"))
        for cab, x, y, na, nb, ok in found[:a.show]:
            print("   %-28s %-28s %6.1f%% %7d %7d  %s"
                  % (x[:28], y[:28], 100.0 * cab, na, nb,
                     "candidate" if ok else "UNRELIABLE (sample too small)"))
    print("")

    # ------------------------------------------------------------------
    print("3. PROVENANCE - documents that say for themselves that they are derived")
    print("")
    try:
        eng = con.execute(
            "SELECT d.code, COALESCE(p.engine,'(null)'), COUNT(*) "
            "FROM passages p JOIN docs d ON d.id=p.doc_id "
            "GROUP BY d.code, p.engine ORDER BY d.code").fetchall()
    except Exception as e:
        eng = []
        print("   (engine column unreadable: %s)" % e)
    derived = [(c, e, n2) for c, e, n2 in eng if e and "resegment" in e.lower()]
    if derived:
        for c, e, n2 in derived:
            print("   %-32s engine=%-24s %6d row(s)" % (c[:32], e, n2))
        print("")
        print("   resegment_doc.py writes these. Its own docstring: 'It is")
        print("   NON-DESTRUCTIVE: the source doc is never touched. Ingest the output")
        print("   as a NEW doc, translate it, compare, and only then adopt it as")
        print("   canonical.' If both members are translated below, adoption never")
        print("   happened and the corpus paid for the text twice.")
    else:
        print("   (no document carries a resegment engine stamp)")
    print("")
    print("   engines present, by document:")
    for c, e, n2 in eng[:40]:
        print("     %-32s %-28s %6d" % (c[:32], (e or "")[:28], n2))
    if len(eng) > 40:
        print("     ... %d more rows" % (len(eng) - 40))
    print("")

    # ------------------------------------------------------------------
    print("4. WHAT EACH CANDIDATE COST - translated rows on both sides")
    print("")
    cand = set()
    for k in pair_exact:
        cand.add(k)
    for _c, x, y, _a2, _b2, ok in found:
        if ok:
            cand.add(tuple(sorted((x, y))))
    if not cand:
        print("   (no candidates)")
    else:
        print("   %-28s %6s %6s   %-28s %6s %6s" % (
            "document A", "rows", "EN", "document B", "rows", "EN"))
        for x, y in sorted(cand):
            print("   %-28s %6d %6d   %-28s %6d %6d" % (
                x[:28], docrows.get(x, 0), doctrans.get(x, 0),
                y[:28], docrows.get(y, 0), doctrans.get(y, 0)))
        print("")
        print("   Both columns non-zero on one row means both copies were translated.")
        print("   Nothing here is deleted, merged or reclassified. Adoption is a")
        print("   decision, and diag_duplicate_verses.py --sql is the pattern for")
        print("   making one: write the statements, read them, run them by hand.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())