#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_retire_doc_unify.py  (2026-09-14)  RETIRE_UNIFY_2026_09_14

retire_doc.py writes a doc_stage row at stage='retired'. Eleven other
scripts - dashboard.py, build_embeddings.py, extract_entities.py,
ling_kosha.py among them - do not read doc_stage at all. They filter
with

    d.code NOT LIKE '%-RETIRED'

a suffix convention that predates the ledger. So a retirement that
writes only the ledger row leaves eleven of twelve consumers treating
the document as live. That is not hypothetical: after
smriti_16harita_smriti was retired on 2026-09-14 the corpus carried one
retired code with the suffix and one without, and the one without had
zero passages and no explanation - a fourth empty shell beside the three
already unaccounted for.

_unify_retired.py in the ops folder repairs an instance. This removes
the need for it, by making retire_doc.py write BOTH conventions in the
SAME transaction as the deletes. Either a document is retired everywhere
or the transaction rolls back and it is retired nowhere.

Renaming also frees the original code for a future re-ingest, which the
existing docstring already promises and could not deliver while the code
was still occupied.

One anchored insert. Nothing is restructured.

Usage:
  python scripts/patch_retire_doc_unify.py scripts/retire_doc.py --check
  python scripts/patch_retire_doc_unify.py scripts/retire_doc.py
"""

import argparse
import os
import sys

MARK = "RETIRE_UNIFY_2026_09_14"

A1_OLD = '''        stmts.append("DELETE FROM doc_stage WHERE doc_code='%s' AND stage<>'retired';" % a.doc)

    body = ("-- %s\\n-- retire %s, superseded by %s\\n"
'''

A1_NEW = '''        stmts.append("DELETE FROM doc_stage WHERE doc_code='%s' AND stage<>'retired';" % a.doc)

    # RETIRE_UNIFY_2026_09_14
    # Two conventions, one transaction. Eleven scripts filter retired
    # documents with  d.code NOT LIKE '%-RETIRED'  and only automaton.py
    # reads doc_stage. Writing the ledger row alone leaves those eleven
    # treating the retiree as live, which is exactly what happened to
    # smriti_16harita_smriti. The rename goes in the SAME statement list
    # as the deletes, so a retirement is either complete or rolled back.
    # It also frees the original code for a future re-ingest, which this
    # tool's docstring already promised.
    if not a.doc.endswith("-RETIRED"):
        stmts.append("UPDATE docs SET code='%s-RETIRED' WHERE id=%d;" % (a.doc, sid))
        if has_table(con, "doc_stage"):
            stmts.append("UPDATE doc_stage SET doc_code='%s-RETIRED' "
                         "WHERE doc_code='%s';" % (a.doc, a.doc))

    body = ("-- %s\\n-- retire %s, superseded by %s\\n"
'''

PATCHES = [(A1_OLD, A1_NEW, "rename the code inside the retirement transaction")]


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
    print("anchor                                             found")
    print("-" * 60)
    ok = True
    for old, _new, name in PATCHES:
        n = src.count(old)
        print("%-50s %s" % (name, "OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)))
        if n != 1:
            ok = False
    print("-" * 60)
    if not ok:
        print("FAIL: anchors did not match. Nothing written.")
        return 2
    if a.check:
        print("--check only: nothing written.")
        return 0
    for old, new, _name in PATCHES:
        src = src.replace(old, new, 1)
    # The inserted lines lean on names the original defines. If any moved,
    # the patch would produce a file that imports fine and dies at the one
    # moment it is trusted - mid-retirement, inside a transaction.
    for need in ("def has_table(", "sid = ", "stmts = "):
        if need not in src:
            print("FAIL: the original no longer provides %r, which the inserted" % need)
            print("      lines depend on. Nothing written.")
            return 2
    open(a.target, "wb").write(src.replace("\n", nl).encode("utf-8"))
    print("Patched %s (%s endings preserved)"
          % (os.path.basename(a.target), "CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    print("")
    print("A retirement now renames the code and updates the ledger in the")
    print("same transaction as the deletes. _unify_retired.py stays in the ops")
    print("folder for the documents retired before this patch, and should")
    print("never be needed again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())