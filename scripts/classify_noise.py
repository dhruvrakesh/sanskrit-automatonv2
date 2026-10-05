#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_noise.py - tag OCR fragments (page furniture, running heads, stray marks) as
text_type='noise', so they stop inflating the untranslated count. (2026-08-28)

Examples this catches, all seen in AphorismsOfSandilya:
    "।"                                  (a bare dandas)
    "Ind । . 212, 35"                    (a running head + page ref)
    "0 011९1 . JAS 181... 0$ 1939 क् ।"  (catalogue junk)

DELIBERATELY CONSERVATIVE - a passage is noise only when it has almost no real content:
fewer than `--min-dev` Devanagari letters AND fewer than `--min-lat` Latin letters. A
genuine short verse ("ॐ नमः शिवाय") has plenty of Devanagari and is never touched.

SAFE: dry-run by default; only considers passages with NO stored translation; never
re-tags something already 'frontmatter'/'noise'. Reversible (set text_type back to
'mula'). Writes via db_utils.connect (WAL + busy_timeout); run with the dashboard idle.

  python scripts/classify_noise.py                       # preview all docs
  python scripts/classify_noise.py --doc AphorismsOfSandilya --show
  python scripts/classify_noise.py --apply
"""
from __future__ import annotations
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import connect as _connect


def content_counts(s: str) -> tuple[int, int]:
    """(devanagari_letters, latin_letters) - the only things that carry meaning.
    Devanagari DIGITS (U+0966-U+096F) and the DANDAS (U+0964 danda, U+0965 double
    danda) are excluded: a page number like '५४०७' and verse punctuation are furniture,
    not content. Counting them hid catalogue junk from the filter."""
    return (len(re.findall(r"[ऀ-ॣ॰-ॿ]", s or "")),
            len(re.findall(r"[A-Za-z]", s or "")))


def is_noise(s: str, min_dev: int, min_lat: int) -> bool:
    dev, lat = content_counts(s)
    return dev < min_dev and lat < min_lat


# GAPS_2026_10_05: running heads and footers - the same short line at the top or foot of many pages.
_UVACA = "\u0909\u0935\u093e\u091a"   # 'uvaca' (said): a speaker line repeats too, and is real text


def head_key(s: str) -> str:
    """The line with digits (ASCII and Devanagari), dandas and punctuation removed, spaces collapsed."""
    import unicodedata
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[0-9\u0966-\u096f\u0964\u0965|.,;:!?()\[\]{}'\"\u2018\u2019\u201c\u201d*_/\\~`+=<>\u2013\u2014-]+",
               " ", s)
    return " ".join(s.split()).lower()


def running_heads(con, doc=None, min_repeat=3, max_len=60):
    """(hits, groups). hits: [(id, code, text)] untranslated passages that are the first or last line of
    their page and whose head_key is the first/last line of >= min_repeat pages of the same doc.
    Never: a line with a danda (verse, incl. refrains), a speaker line (uvaca), a line over max_len.
    groups: [(code, key, pages, untranslated, translated, sample)] for --show."""
    where = "WHERE COALESCE(p.text_type,'mula') NOT IN ('frontmatter','noise')"
    params = []
    if doc:
        where += " AND d.code=?"; params.append(doc)
    pages = {}
    for pid, code, page, idx, text, done in con.execute(
            f"""SELECT p.id, d.code, p.page_no, p.idx, p.text, TRIM(COALESCE(p.translation,''))<>''
                FROM passages p JOIN docs d ON d.id=p.doc_id {where} ORDER BY d.code, p.page_no, p.idx""", params):
        pages.setdefault((code, page), []).append((pid, text or "", bool(done)))
    by = {}
    for (code, page), rows in pages.items():
        for pid, text, done in {rows[0][0]: rows[0], rows[-1][0]: rows[-1]}.values():
            t = " ".join(text.split())
            k = head_key(t)
            if not k or len(t) > max_len or _UVACA in t or "\u0964" in t or "\u0965" in t:
                continue   # a danda marks verse (a refrain can close many pages); a head has none
            g = by.setdefault((code, k), {"pages": set(), "todo": [], "done": 0, "sample": t})
            g["pages"].add(page)
            if done:
                g["done"] += 1
            else:
                g["todo"].append((pid, code, text))
    hits, groups = [], []
    for (code, k), g in by.items():
        if len(g["pages"]) >= min_repeat and len(g["todo"]) > g["done"]:
            hits += g["todo"]
            groups.append((code, k, len(g["pages"]), len(g["todo"]), g["done"], g["sample"]))
    groups.sort(key=lambda x: (x[0], -x[2]))
    return hits, groups


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--min-dev", type=int, default=3, help="fewer than this many Devanagari letters (default 3)")
    ap.add_argument("--min-lat", type=int, default=10, help="AND fewer than this many Latin letters (default 10)")
    ap.add_argument("--show", action="store_true", help="print a sample of what would be tagged")
    ap.add_argument("--running-heads", action="store_true",
                    help="instead: untranslated first/last lines of a page that repeat on --min-repeat pages "
                         "(GAPS_2026_10_05)")
    ap.add_argument("--min-repeat", type=int, default=3, help="with --running-heads: pages (default 3)")
    ap.add_argument("--max-len", type=int, default=60, help="with --running-heads: characters (default 60)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = _connect(args.db)
    if "text_type" not in {r[1] for r in con.execute("PRAGMA table_info(passages)")}:
        print("passages has no text_type column; nothing to do."); con.close(); return

    where = ("WHERE TRIM(COALESCE(p.translation,''))='' "
             "AND COALESCE(p.text_type,'mula') NOT IN ('frontmatter','noise')")
    params = []
    if args.doc:
        where += " AND d.code=?"; params.append(args.doc)
    rows = con.execute(
        f"SELECT p.id, d.code, p.text FROM passages p JOIN docs d ON d.id=p.doc_id {where}",
        params).fetchall()

    hits = [(pid, code, text) for pid, code, text in rows if is_noise(text or "", args.min_dev, args.min_lat)]
    if args.running_heads:   # GAPS_2026_10_05
        try:   # a cp1252 console must not crash on a Devanagari sample line
            sys.stdout.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
        hits, groups = running_heads(con, args.doc, args.min_repeat, args.max_len)
        print(f"Running heads/footers ({'APPLY' if args.apply else 'DRY-RUN'}): first or last line of a page, "
              f"no danda, <= {args.max_len} chars, repeated on >= {args.min_repeat} pages, untranslated:")
        for code, k, npg, todo, done, sample in groups[:40]:
            print(f"  [{code[:22]:22s}] {npg:4d} pages  {todo:4d} untranslated  {done:3d} translated  {sample!r}")
        if len(groups) > 40:
            print(f"  ... and {len(groups) - 40} more repeated lines")
    by = {}
    for _, code, _ in hits:
        by[code] = by.get(code, 0) + 1

    if not args.running_heads:   # GAPS_2026_10_05: running-heads mode printed its own header
        print(f"OCR fragments to tag as 'noise'  ({'APPLY' if args.apply else 'DRY-RUN'}; "
              f"dev<{args.min_dev} AND lat<{args.min_lat}):")
    if not hits:
        print("  none found."); con.close(); return
    for code, n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {code}: {n}")
    print(f"Total: {len(hits)}")

    if args.show:
        print("\nsample (first 15):")
        for _, code, text in hits[:15]:
            flat = " ".join((text or "").split())[:70]
            print(f"  [{code[:22]:22s}] {flat!r}")

    if not args.apply:
        print("\nDRY-RUN. Inspect with --show, then re-run with --apply. Reversible.")
        con.close(); return

    con.executemany("UPDATE passages SET text_type='noise' WHERE id=?", [(pid,) for pid, _, _ in hits])
    con.commit(); con.close()
    print(f"\nTagged {len(hits)} passages as 'noise'. Coverage now counts real verses only.")


if __name__ == "__main__":
    main()
