#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_retire_check.py - prove a document can be retired before deleting it.
v1, 2026-09-14.

READ-ONLY. Writes nothing, deletes nothing, calls no API.
Run it on WINDOWS - SQLite over the Claude device bridge fails with
'disk I/O error' because the -shm lock file cannot be mapped.

WHY
---
resegment_doc.py produces a NEW document from an old one and its docstring is
explicit about the workflow: "Ingest the output as a NEW doc, translate it,
COMPARE, and only then adopt it as canonical." The compare step has never been
run for any pair. This is that step, made mechanical.

Retiring a document deletes rows. Before that happens, one question has to be
answered with evidence and not with confidence: is every piece of text in the
retiree also present in the keeper? Not "probably", not "it was derived from
it" - actually present, verse by verse.

HOW
---
The keeper was produced by running split_verses() over the retiree's page
blobs. So this applies the same transform to the retiree and looks up every
resulting verse in the keeper, on three progressively looser keys:

  exact      Devanagari characters only, digits and dandas included
  no-digits  the same with the sloka numbers removed - the splitter consumes
             the number that terminates a verse, so it is absent from the
             keeper by construction and its absence is not a loss
  prefix     the first 40 Devanagari letters, which survives a differing tail

Anything still unmatched is text that retirement would destroy. Those are
printed in full so you can read them and decide, rather than being summarised
into a percentage.

It also prices the retirement in links: how many entity mentions and
embedding vectors point into the retiree, and how many entities would be left
with no mention anywhere - because diag_brain.py's whole warning is that
deleting passages turns the links that point at them into orphans.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def _force_utf8_streams():
    """patch_booksmith_utf8.py's reason, and it applies here too: PowerShell
    5.1 hands a console whose codepage is not UTF-8, so Devanagari prints as
    mojibake. The transcript file is still correct; this makes the console
    correct too, where the font can draw it."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_force_utf8_streams()

try:
    from resegment_doc import split_verses
except Exception as e:  # pragma: no cover
    sys.exit("cannot import resegment_doc.py from %s: %s" % (HERE, e))

# IAST beside every unmatched verse, because IAST is ASCII and will render in
# any console whatever its codepage or font. A verse you cannot read is a
# verse you cannot make a decision about.
_IAST = None
try:
    import iast_utils as _iu
    for _n in ("to_iast", "dev_to_iast", "devanagari_to_iast", "iast", "transliterate"):
        _f = getattr(_iu, _n, None)
        if callable(_f):
            _IAST = _f
            break
except Exception:
    _IAST = None


def iast_of(s):
    if not _IAST:
        return None
    try:
        out = _IAST(s)
        return out if isinstance(out, str) else None
    except Exception:
        return None

MARK = "RETIRE_CHECK_2026_09_14"
DEV_ALL = re.compile("[\\u0900-\\u097F]+")
DEV_DIGIT = re.compile("[\\u0966-\\u096F]+")
DEV_DANDA = re.compile("[\\u0964\\u0965]+")
PREFIX = 40


def k_exact(t):
    return "".join(DEV_ALL.findall(t or ""))


def k_nodigit(t):
    s = k_exact(t)
    s = DEV_DIGIT.sub("", s)
    return DEV_DANDA.sub("", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--src", required=True, help="the document proposed for retirement")
    ap.add_argument("--keep", required=True, help="the document that supersedes it")
    ap.add_argument("--show", type=int, default=12)
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit("not found: %s - run from the repo root" % a.db)
    con = sqlite3.connect("file:%s?mode=ro" % a.db.replace("\\", "/"), uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")

    def did(code):
        r = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
        if not r:
            sys.exit("doc code %r not found" % code)
        return r[0]

    sid, kid = did(a.src), did(a.keep)
    live = "COALESCE(text_type,'mula') NOT IN ('noise','frontmatter')"

    keep_rows = con.execute(
        "SELECT text FROM passages WHERE doc_id=? AND %s "
        "AND TRIM(COALESCE(text,''))<>''" % live, (kid,)).fetchall()
    src_rows = con.execute(
        "SELECT page_no, idx, text FROM passages WHERE doc_id=? AND %s "
        "AND TRIM(COALESCE(text,''))<>'' ORDER BY page_no, idx" % live, (sid,)).fetchall()

    print("%s" % MARK)
    print("  retire : %-40s %6d live row(s)" % (a.src, len(src_rows)))
    print("  keep   : %-40s %6d live row(s)" % (a.keep, len(keep_rows)))
    print("")

    k_ex, k_nd, k_pf = set(), set(), set()
    for (t,) in keep_rows:
        e, n = k_exact(t), k_nodigit(t)
        k_ex.add(e)
        k_nd.add(n)
        if len(n) >= PREFIX:
            k_pf.add(n[:PREFIX])

    tot = ex = nd = pf = 0
    missing = []
    for page_no, idx, t in src_rows:
        vs = split_verses(t or "")
        if not vs:
            vs = [{"text": t, "verse_ref": None}]
        for v in vs:
            txt = v["text"]
            e, n = k_exact(txt), k_nodigit(txt)
            if not n:
                continue
            tot += 1
            if e in k_ex:
                ex += 1
            elif n in k_nd:
                nd += 1
            elif len(n) >= PREFIX and n[:PREFIX] in k_pf:
                pf += 1
            else:
                missing.append((page_no, idx, v.get("verse_ref"), txt))

    print("  every verse the splitter finds in the retiree, looked up in the keeper")
    print("")
    print("    verses examined                        %6d" % tot)
    print("    matched exactly                        %6d   %5.1f%%" % (ex, 100.0 * ex / max(1, tot)))
    print("    matched once sloka numbers are ignored %6d   %5.1f%%" % (nd, 100.0 * nd / max(1, tot)))
    print("    matched on a 40-character prefix       %6d   %5.1f%%" % (pf, 100.0 * pf / max(1, tot)))
    print("    NOT FOUND anywhere in the keeper       %6d   %5.1f%%"
          % (len(missing), 100.0 * len(missing) / max(1, tot)))
    print("")
    cov = 100.0 * (tot - len(missing)) / max(1, tot)
    if missing:
        print("  the unmatched text, in full - this is what retirement would destroy:")
        for page_no, idx, ref, txt in missing[:a.show]:
            flat = " ".join((txt or "").split())
            print("")
            dev = sum(1 for ch in flat if "\u0900" <= ch <= "\u097f")
            print("    page %s idx %s  ref=%s  (%d chars, %.0f%% Devanagari)"
                  % (page_no, idx, ref, len(flat),
                     100.0 * dev / max(1, len(flat.replace(" ", "")))))
            print("      %s" % flat[:300])
            ia = iast_of(flat)
            if ia:
                print("      IAST: %s" % " ".join(ia.split())[:300])
        if len(missing) > a.show:
            print("")
            print("    ... and %d more" % (len(missing) - a.show))
    else:
        print("  nothing is unmatched.")
    print("")

    # the reverse direction: material in the keeper with no origin in the retiree
    s_nd = set()
    for _p, _i, t in src_rows:
        for v in split_verses(t or "") or [{"text": t}]:
            s_nd.add(k_nodigit(v["text"]))
    orphan_keep = sum(1 for (t,) in keep_rows if k_nodigit(t) and k_nodigit(t) not in s_nd)
    print("  and the other direction: %d of the keeper's %d rows have no counterpart"
          % (orphan_keep, len(keep_rows)))
    print("  in the retiree. That is expected to be small; a large number would mean")
    print("  the keeper is not actually derived from this document.")
    print("")

    # -----------------------------------------------------------------------
    print("  WHAT RETIREMENT COSTS IN LINKS")
    print("")

    def scalar(sql, *args):
        try:
            return con.execute(sql, args).fetchone()[0]
        except Exception:
            return -1

    n_all = scalar("SELECT COUNT(*) FROM passages WHERE doc_id=?", sid)
    n_en = scalar("SELECT COUNT(*) FROM passages WHERE doc_id=? "
                  "AND TRIM(COALESCE(translation,''))<>''", sid)
    n_hi = scalar("SELECT COUNT(*) FROM translations_l10n l JOIN passages p "
                  "ON p.id=l.passage_id WHERE p.doc_id=? AND l.lang='hi'", sid)
    n_vec = scalar("SELECT COUNT(*) FROM passage_embeddings e JOIN passages p "
                   "ON p.id=e.passage_id WHERE p.doc_id=?", sid)
    n_men = scalar("SELECT COUNT(*) FROM entity_mentions m JOIN passages p "
                   "ON p.id=m.passage_id WHERE p.doc_id=?", sid)
    n_hist = scalar("SELECT COUNT(*) FROM translation_history h JOIN passages p "
                    "ON p.id=h.passage_id WHERE p.doc_id=?", sid)
    n_only = scalar(
        "SELECT COUNT(*) FROM (SELECT m.entity_id FROM entity_mentions m "
        "JOIN passages p ON p.id=m.passage_id GROUP BY m.entity_id "
        "HAVING SUM(CASE WHEN p.doc_id=? THEN 0 ELSE 1 END)=0)", sid)
    print("    passages (all, live and not)       %6d" % n_all)
    print("    English translations               %6d" % n_en)
    print("    Hindi translations                 %6d" % n_hi)
    print("    embedding vectors                  %6d" % n_vec)
    print("    entity mentions                    %6d" % n_men)
    print("    translation_history rows           %6d" % n_hist)
    print("    entities mentioned ONLY here       %6d" % n_only)
    print("")
    print("    Every one of those has to be deleted in the same transaction as the")
    print("    passages. wipe_doc.py deletes passages and FTS rows only, so using it")
    print("    alone would leave %d orphaned vectors and %d orphaned mentions -"
          % (max(0, n_vec), max(0, n_men)))
    print("    exactly the condition diag_brain.py exists to detect, and which is")
    print("    currently at zero.")
    print("")
    print("  VERDICT")
    if not missing and orphan_keep <= max(2, len(keep_rows) // 100):
        print("    SAFE. %.1f%% of the retiree's verses are present in the keeper and" % cov)
        print("    nothing is unaccounted for. retire_doc.py will write the statements.")
        rc = 0
    elif not missing:
        print("    SAFE on content (%.1f%% covered), but the keeper carries %d rows with" % (cov, orphan_keep))
        print("    no counterpart here - read those before proceeding.")
        rc = 0
    else:
        print("    NOT SAFE. %d verse(s) exist only in the document you propose to" % len(missing))
        print("    retire. Read them above. Either they are noise you are content to")
        print("    lose, in which case say so explicitly, or the keeper is incomplete")
        print("    and should be rebuilt before anything is deleted.")
        rc = 1
    con.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())