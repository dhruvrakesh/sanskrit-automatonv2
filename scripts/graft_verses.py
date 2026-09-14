#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graft_verses.py - move the verses a re-segmentation lost into the keeper.
v1, 2026-09-14.

Run diag_retire_check.py FIRST. This tool exists because that check failed.

WHAT HAPPENED
-------------
nilamata_seg was produced from upapurana_nilamata_purana on 2026-08-02 and is
the better text by every measure: 1,393 verses at a median of 9 words per row
against 111 page-blobs at 137, 98.0% of rows verse-shaped against 3.6%.

But diag_retire_check found seven verses the splitter finds in the source that
are not in the keeper, and they are not noise. Decoded:

  page 1    nilamatapuranam / svasti / srigana esaya namah   the title and the
                                                             opening benediction
  page 1    namo bhagavate vasudevaya ...                    verse 1, the mangala
  page 1    pariksit's descendant Janamejaya asked ...       verse 2
  page 1    srijanamejayah: in the Mahabharata war ...       verse 3
  page 1    why did the king of Kashmir not come ...         verse 4
  page 1    kasmiramandalam caiva pradhanam jagati ...       verse 5
  page 109  vitastamahatmyam samaptam idam nilamatam         the closing colophon
            subham astu + the edition this text came from

The first five are the mangalacarana and Janamejaya's question - the frame that
opens the entire Purana. The last is its colophon, and it carries the only
record in the database of which edition the text came from: Dr Ved Kumari,
J & K Academy of Art, Culture and Languages, Srinagar 1973.

A reading edition without its opening invocation and its colophon is not the
text. The keeper is incomplete, and the answer is to complete it, not to lower
the bar on the check.

WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
It grafts the missing verses into the keeper VERBATIM. It does not clean them,
even though two carry obvious OCR debris ("x", "-----", "std"). That is the
division of labour this project already settled: the database holds what the
scanner saw, and clean_for_mt decides what the model sees. ENTERPRISE_PATH
2026-09-06 section 1c records that decision and the 1,321-passage measurement
behind it. A second cleaner here would be a second place for that judgement to
go wrong.

Placement preserves reading order. For each missing verse the tool finds its
nearest PRECEDING verse in the source that IS in the keeper, and inserts
immediately after it; a verse with no preceding match goes to the front of its
page. Only the affected pages are renumbered, in two passes inside one
transaction so the UNIQUE(doc_id, page_no, idx) constraint is never violated
mid-flight.

Grafted rows get:
  text_type      mula
  iast           from iast_utils if it imports, else NULL for the iast stage
  quality_score  the Devanagari fraction, via resegment_doc._frac_dev, which is
                 what db_utils documents the column as
  ocr_engine     resegment-graft
  source         the doc code it came from
  passages_fts   inserted explicitly - the FTS table is keyed by passages.id
                 and nothing maintains it automatically

They arrive untranslated, un-embedded and un-linked, which is correct: the
incremental passes pick them up. Seven rows is not a spend.

USAGE
  python scripts/graft_verses.py --from <src> --into <keep> --dry-run
  python scripts/graft_verses.py --from <src> --into <keep> --yes
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _force_utf8_streams():
    """Same reason patch_booksmith_utf8.py does it: PowerShell 5.1 hands a
    console whose codepage is not UTF-8, and Devanagari then prints as
    mojibake or raises UnicodeEncodeError mid-run."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_force_utf8_streams()

try:
    from resegment_doc import split_verses, _frac_dev
except Exception as e:  # pragma: no cover
    sys.exit("cannot import resegment_doc.py from %s: %s" % (HERE, e))
try:
    from diag_retire_check import k_exact, k_nodigit, PREFIX
except Exception as e:  # pragma: no cover
    sys.exit("cannot import diag_retire_check.py from %s: %s" % (HERE, e))

try:
    from iast_utils import to_iast as _to_iast
except Exception:
    _to_iast = None

MARK = "GRAFT_VERSES_2026_09_14"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--into", dest="keep", required=True)
    ap.add_argument("--text-type", default="mula")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit("not found: %s - run from the repo root" % a.db)
    con = sqlite3.connect(a.db, timeout=120)
    con.execute("PRAGMA busy_timeout=120000")

    def one(sql, *args):
        r = con.execute(sql, args).fetchone()
        return r[0] if r else None

    sid = one("SELECT id FROM docs WHERE code=?", a.src)
    kid = one("SELECT id FROM docs WHERE code=?", a.keep)
    if sid is None or kid is None:
        sys.exit("both --from and --into must exist as doc codes")

    live = "COALESCE(text_type,'mula') NOT IN ('noise','frontmatter')"
    keep_rows = con.execute(
        "SELECT id, page_no, idx, text FROM passages WHERE doc_id=? AND %s "
        "AND TRIM(COALESCE(text,''))<>'' ORDER BY page_no, idx" % live,
        (kid,)).fetchall()
    src_rows = con.execute(
        "SELECT page_no, idx, text FROM passages WHERE doc_id=? AND %s "
        "AND TRIM(COALESCE(text,''))<>'' ORDER BY page_no, idx" % live,
        (sid,)).fetchall()

    by_ex, by_nd, by_pf = {}, {}, {}
    for pid, pg, ix, t in keep_rows:
        e, n = k_exact(t), k_nodigit(t)
        by_ex.setdefault(e, (pid, pg, ix))
        by_nd.setdefault(n, (pid, pg, ix))
        if len(n) >= PREFIX:
            by_pf.setdefault(n[:PREFIX], (pid, pg, ix))

    def lookup(txt):
        e, n = k_exact(txt), k_nodigit(txt)
        if e in by_ex:
            return by_ex[e]
        if n in by_nd:
            return by_nd[n]
        if len(n) >= PREFIX and n[:PREFIX] in by_pf:
            return by_pf[n[:PREFIX]]
        return None

    # Walk the source in order. Each missing verse remembers the keeper row it
    # should follow; None means "front of this page".
    plan = []
    for pg, _ix, t in src_rows:
        prev = None
        for v in (split_verses(t or "") or [{"text": t, "verse_ref": None}]):
            txt = v["text"]
            if not k_nodigit(txt):
                continue
            hit = lookup(txt)
            if hit:
                prev = hit
            else:
                plan.append({"src_page": pg, "after": prev, "text": txt,
                             "verse_ref": v.get("verse_ref")})

    print("%s" % MARK)
    print("  from %-36s -> into %s" % (a.src, a.keep))
    print("  keeper holds %d live row(s); %d verse(s) to graft" % (len(keep_rows), len(plan)))
    print("")
    if not plan:
        print("  Nothing missing. diag_retire_check would already pass.")
        con.close()
        return 0

    # Which keeper page does each graft land on?
    first_of_page = {}
    for pid, pg, ix, _t in keep_rows:
        first_of_page.setdefault(pg, (pid, pg, ix))
    for g in plan:
        if g["after"] is not None:
            g["page"] = g["after"][1]
        elif g["src_page"] in first_of_page:
            g["page"] = g["src_page"]
        else:
            g["page"] = g["src_page"]

    pages = sorted(set(g["page"] for g in plan))
    print("  placement - each graft goes immediately after the last verse before")
    print("  it that the keeper already has; one with no predecessor goes to the")
    print("  front of its page.")
    print("")
    for g in plan:
        where = ("after keeper row id %d (page %s idx %s)" % g["after"]) if g["after"] \
            else ("front of page %s" % g["page"])
        print("    page %-5s ref=%-5s dev=%.2f  %s" % (
            g["src_page"], g["verse_ref"], _frac_dev(g["text"]), where))
        print("      %s" % " ".join(g["text"].split())[:150])
    print("")
    print("  pages that would be renumbered: %s" % ", ".join(str(p) for p in pages))
    for p in pages:
        n_now = sum(1 for _i, pg, _x, _t in keep_rows if pg == p)
        n_add = sum(1 for g in plan if g["page"] == p)
        print("    page %-5s %d row(s) now -> %d" % (p, n_now, n_now + n_add))
    print("")
    print("  every grafted row: text_type=%s, ocr_engine=resegment-graft," % a.text_type)
    print("  source=%s, quality_score=the Devanagari fraction, iast=%s." % (
        a.src, "computed" if _to_iast else "NULL, for the iast stage to fill"))
    print("  Text is grafted VERBATIM, OCR debris included. clean_for_mt is the")
    print("  single gate between the database and the model and it already")
    print("  strips page furniture - a second cleaner here would be a second place")
    print("  for that judgement to go wrong.")
    print("")

    if a.dry_run or not a.yes:
        print("  Dry run - nothing written. Re-run with --yes after a backup.")
        con.close()
        return 0

    # ---------------------------------------------------------------- apply
    print("  applying, in one transaction...")
    try:
        con.execute("BEGIN IMMEDIATE")
        inserted = []
        for p in pages:
            rows = [(pid, ix) for pid, pg, ix, _t in keep_rows if pg == p]
            order = []
            front = [g for g in plan if g["page"] == p and g["after"] is None]
            order.extend(("new", g) for g in front)
            for pid, ix in rows:
                order.append(("old", (pid, ix)))
                for g in plan:
                    if g["page"] == p and g["after"] is not None and g["after"][0] == pid:
                        order.append(("new", g))
            # park every existing row on this page out of the way first, so the
            # UNIQUE(doc_id,page_no,idx) constraint cannot bite mid-renumber
            park = -100000
            for pid, _ix in rows:
                con.execute("UPDATE passages SET idx=? WHERE id=?", (park, pid))
                park -= 1
            for newidx, (kind, payload) in enumerate(order):
                if kind == "old":
                    con.execute("UPDATE passages SET idx=? WHERE id=?", (newidx, payload[0]))
                else:
                    g = payload
                    txt = g["text"]
                    ia = None
                    if _to_iast:
                        try:
                            ia = _to_iast(txt)
                        except Exception:
                            ia = None
                    cur = con.execute(
                        "INSERT INTO passages(doc_id,page_no,idx,text,text_type,iast,"
                        "verse_ref,quality_score,ocr_engine,source) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (kid, p, newidx, txt, a.text_type, ia, g.get("verse_ref"),
                         round(_frac_dev(txt), 3), "resegment-graft", a.src))
                    nid = cur.lastrowid
                    con.execute("INSERT INTO passages_fts(rowid,text,iast,translation) "
                                "VALUES(?,?,?,?)", (nid, txt, ia, None))
                    inserted.append(nid)
        con.commit()
    except Exception as e:
        con.rollback()
        print("  ROLLED BACK: %s" % e)
        con.close()
        return 1

    n_keep = one("SELECT COUNT(*) FROM passages WHERE doc_id=?", kid)
    dup = one("SELECT COUNT(*) FROM (SELECT page_no, idx FROM passages WHERE doc_id=? "
              "GROUP BY page_no, idx HAVING COUNT(*)>1)", kid)
    # Check what THIS tool is responsible for: every row it inserted must have
    # an FTS row. A corpus-wide count would false-alarm on any pre-existing
    # gap and tell you nothing about this operation.
    got = 0
    for nid in inserted:
        if one("SELECT COUNT(*) FROM passages_fts WHERE rowid=?", nid):
            got += 1
    print("  done. grafted %d row(s); %s now holds %d passage(s)."
          % (len(inserted), a.keep, n_keep))
    print("    FTS rows for the grafted ids: %d of %d  %s"
          % (got, len(inserted), "(all present)" if got == len(inserted) else "(MISSING)"))
    print("    duplicate (page_no, idx) pairs in the keeper: %d" % dup)
    print("    corpus totals, for information: passages_fts %d, passages %d"
          % (one("SELECT COUNT(*) FROM passages_fts"), one("SELECT COUNT(*) FROM passages")))
    print("")
    print("  The grafted rows are untranslated, un-embedded and un-linked. The")
    print("  incremental passes pick them up: translate_passages.py, then")
    print("  build_embeddings.py and extract_entities.py, which the maintenance")
    print("  runner already calls.")
    con.close()
    return 1 if (got != len(inserted) or dup) else 0


if __name__ == "__main__":
    sys.exit(main())