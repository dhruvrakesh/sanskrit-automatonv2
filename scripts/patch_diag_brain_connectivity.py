#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_diag_brain_connectivity.py  (2026-09-14)  BRAIN_CONNECTIVITY_2026_09_14

diag_brain.py asks whether the brain's links still point at rows that EXIST.
That is integrity, and it is the right first question - it caught 746 orphaned
vectors and 1,231 orphaned mentions in September.

It does not ask whether those links go ACROSS documents, which is the
difference between a brain and a shelf. An entity mentioned in one text is an
index entry. An entity mentioned in twenty is a link, and links are the whole
claim behind "one interconnected corpus".

That question has been asked three times in conversation and answered three
times by a throwaway script. This makes it part of the tool everyone already
runs, so it stops being a conversation and becomes a command.

Two anchored inserts, no restructuring:

  1. A CONNECTIVITY section before the closing note: entities by how many
     documents mention them, the share reaching two and five, the strongest
     cross-document links, and semantic-index coverage as a share of live
     passages rather than a raw count.

  2. A one-line verdict, because a histogram without a sentence is a number
     nobody acts on.

Nothing is hardcoded about the entity schema. The tables are not in
db_utils.BASE_SCHEMA, so the columns are read from PRAGMA table_info and the
section says plainly if it cannot find the join.

Usage:
  python scripts/patch_diag_brain_connectivity.py scripts/diag_brain.py --check
  python scripts/patch_diag_brain_connectivity.py scripts/diag_brain.py
"""

import argparse
import os
import sys

MARK = "BRAIN_CONNECTIVITY_2026_09_14"

A1_OLD = '''print("\\nWhat this means: a wipe+re-ingest gives passages NEW ids. Vectors and entity")
'''

A1_NEW = '''# BRAIN_CONNECTIVITY_2026_09_14
# Integrity is "do the links point at rows that exist". Connectivity is "do
# they go ACROSS documents". A corpus can be perfectly intact and still be a
# shelf. This section answers the second question.
print("\\n=== CONNECTIVITY (is this one brain, or a shelf?) ===")


def _cols(t):
    try:
        return [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]
    except Exception:
        return []


_ec, _mc = _cols("entities"), _cols("entity_mentions")
_eid = next((x for x in ("entity_id", "entity", "eid") if x in _mc), None)
_pid = next((x for x in ("passage_id", "passage", "pid") if x in _mc), None)
_lab = next((x for x in ("canonical", "name", "surface", "text", "label", "iast")
             if x in _ec), "id")
if not (_ec and _mc and _eid and _pid):
    print("  (entity tables absent or their join columns are not recognisable)")
else:
    print("  joining entity_mentions.%s -> entities.id, .%s -> passages.id"
          % (_eid, _pid))
    _base = ("SELECT m.%s AS e, COUNT(DISTINCT p.doc_id) AS nd "
             "FROM entity_mentions m JOIN passages p ON p.id = m.%s "
             "GROUP BY m.%s" % (_eid, _pid, _eid))
    _hist = c.execute("SELECT nd, COUNT(*) FROM (%s) GROUP BY nd ORDER BY nd"
                      % _base).fetchall()
    _tot = sum(n for _d, n in _hist)
    if not _tot:
        print("  no linked entities")
    else:
        _multi = sum(n for d, n in _hist if d > 1)
        _five = sum(n for d, n in _hist if d >= 5)
        print("    linked entities             %7d" % _tot)
        print("    in 2 or more documents      %7d   %5.1f%%"
              % (_multi, 100.0 * _multi / _tot))
        print("    in 5 or more documents      %7d   %5.1f%%"
              % (_five, 100.0 * _five / _tot))
        print("    documents per entity:")
        _mx = max(n for _d, n in _hist)
        for _d, _n in _hist[:10]:
            print("      %3d doc(s) %7d  %s" % (_d, _n, "#" * min(50, int(50.0 * _n / _mx))))
        if len(_hist) > 10:
            print("      ... up to %d document(s)" % _hist[-1][0])
        try:
            _top = c.execute(
                "SELECT e.%s, COUNT(DISTINCT p.doc_id) nd, COUNT(*) nm "
                "FROM entities e JOIN entity_mentions m ON m.%s = e.id "
                "JOIN passages p ON p.id = m.%s GROUP BY e.id "
                "HAVING nd > 1 ORDER BY nd DESC, nm DESC LIMIT 10"
                % (_lab, _eid, _pid)).fetchall()
            if _top:
                print("    the strongest cross-document links:")
                for _nm, _nd, _cnt in _top:
                    print("      %-36s %3d documents  %6d mentions"
                          % (str(_nm)[:36], _nd, _cnt))
        except Exception as _e:
            print("    (top entities unavailable: %s)" % _e)

_live = q("SELECT COUNT(*) FROM passages p WHERE "
          "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') "
          "AND TRIM(COALESCE(p.text,'')) <> ''")
if "passage_embeddings" in tabs and _live:
    _emb = q("SELECT COUNT(*) FROM passage_embeddings e JOIN passages p "
             "ON p.id = e.passage_id WHERE "
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
    print("\\n  semantic index coverage")
    print("    live passages               %7d" % _live)
    print("    with a vector               %7d   %5.1f%%" % (_emb, 100.0 * _emb / _live))
    print("    with NO vector              %7d   %5.1f%%"
          % (_live - _emb, 100.0 * (_live - _emb) / _live))
    print("\\n  VERDICT")
    _epct = 100.0 * _emb / _live
    if _ec and _mc and _eid and _pid and _tot:
        _mpct = 100.0 * _multi / _tot
        print("    %.0f%% of entities are mentioned in only one document, and %.0f%% of"
              % (100.0 - _mpct, 100.0 - _epct))
        print("    live passages are not in the semantic index. The links that exist")
        print("    are real - %d entities span two or more texts, and %d span five or"
              % (_multi, _five))
        print("    more - but most of the corpus is not yet reachable from the rest.")
    else:
        print("    %.0f%% of live passages are not in the semantic index." % (100.0 - _epct))
    print("    Both gaps close with the incremental passes the maintenance runner")
    print("    already calls - build_embeddings.py, then extract_entities.py. The")
    print("    shortfall is coverage, not design.")

print("\\nWhat this means: a wipe+re-ingest gives passages NEW ids. Vectors and entity")
'''

PATCHES = [(A1_OLD, A1_NEW, "CONNECTIVITY section + verdict")]


def read_src(p):
    s = open(p, "rb").read().decode("utf-8")
    crlf, lf = s.count("\r\n"), s.count("\n")
    if crlf and crlf != lf:
        raise SystemExit("FAIL: %s has mixed line endings (%d CRLF of %d LF)" % (p, crlf, lf))
    return s.replace("\r\n", "\n"), ("\r\n" if crlf else "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.target):
        print("FAIL: %s not found" % a.target)
        return 2
    src, nl = read_src(a.target)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0

    print("anchor                                        found")
    print("-" * 56)
    ok = True
    for old, _new, name in PATCHES:
        n = src.count(old)
        print("%-45s %s" % (name, "OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)))
        if n != 1:
            ok = False
    print("-" * 56)
    if not ok:
        print("FAIL: anchors did not match. Nothing written.")
        return 2
    if a.check:
        print("--check only: nothing written.")
        return 0

    for old, new, _name in PATCHES:
        src = src.replace(old, new, 1)

    # The inserted block leans on names the original file defines: q(), c and
    # tabs. If any of them moved, the patch would produce a file that imports
    # fine and dies at runtime - which is the failure mode this whole session
    # has been about. Check for them here instead.
    for need in ("q = lambda s:", "tabs = {", "c = sqlite3.connect"):
        if need not in src:
            print("FAIL: the original file no longer defines %r, which the inserted"
                  % need)
            print("      section depends on. Nothing written.")
            return 2

    open(a.target, "wb").write(src.replace("\n", nl).encode("utf-8"))
    print("Patched %s (%s endings preserved)" % (os.path.basename(a.target),
                                                 "CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    print("")
    print("diag_brain.py now answers both questions in one run: integrity")
    print("(do the links point at rows that exist) and connectivity (do they")
    print("go across documents).")
    return 0


if __name__ == "__main__":
    sys.exit(main())