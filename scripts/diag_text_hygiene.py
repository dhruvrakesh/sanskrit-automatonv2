#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
diag_text_hygiene.py  (2026-10-03)  TEXT_HYGIENE_2026_10_03

READ-ONLY census of three defects seen in the Mallapurana re-translation of
2026-10-02/03. Each one costs API spend and puts non-text into the corpus.
Nothing is changed; this measures how widespread each defect is before any fix
is written.

  apparatus  An edition's footnote apparatus segmented as if it were a verse:
             numbered variant readings with manuscript sigla, for example
             "<25> sukham P. <26> agnivrddhau vinasasca P." (Devanagari
             numerals, the reading, then a siglum such as B. or P.). These rows are
             translated today ("Now, that [bold person] is indeed...").
  unitloop   A vision run-on loop of a 2-4 character unit ("chchchch..." 6 or more
             times). merge_ocr_sources.collapse_runs() shortens runs of ONE
             repeated character only, so these pass through to ingest.
  meta       A "translation" that is only a bracketed note from the model about
             the input, e.g. "[The Sanskrit verse to be translated is missing from
             the prompt.]" - stored with translation_qa 0.85. The refusal filters
             do not recognise this wording.

Scope: text_type not in (noise, frontmatter), the same as translate_passages.py.
Opens the DB with mode=ro + PRAGMA query_only. Safe while jobs run.

  python scripts\\diag_text_hygiene.py
  python scripts\\diag_text_hygiene.py --doc Mallapurana --show 5
  python scripts\\diag_text_hygiene.py --csv exports\\hygiene_20261003.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

MARK = "TEXT_HYGIENE_2026_10_03"
_NUM = r"[\u0966-\u096f0-9]{1,3}"
_WORD = r"[^\s\u0966-\u096f0-9.]{2,}"
APPARATUS_HIT = re.compile(_NUM + r"\s+" + _WORD + r"(?:\s+" + _WORD + r"){0,3}\s+[A-Z][a-z]{0,2}\.")
UNIT_LOOP = re.compile(r"(\S{2,4}?)\1{5,}")
_META_EN = re.compile(
    r"^\s*\[[^\]]{0,240}?\b(missing|not provided|no (?:sanskrit|text|verse|source)|is empty|"
    r"cannot be translated|unable to translate|nothing to translate|not included|was not given)\b[^\]]{0,240}\]\s*$",
    re.I)
_META_HI = re.compile(r"^\s*\[[^\]]{0,240}?(\u0909\u092a\u0932\u092c\u094d\u0927 \u0928\u0939\u0940\u0902|"
                      r"\u0928\u0939\u0940\u0902 \u0926\u093f\u092f\u093e|\u0905\u0928\u0941\u092a\u0938\u094d\u0925\u093f\u0924)"
                      r"[^\]]{0,240}\]\s*$")


def is_apparatus(text: str, min_hits: int = 2) -> bool:
    return len(APPARATUS_HIT.findall(text or "")) >= min_hits


def has_unit_loop(text: str) -> bool:
    return bool(UNIT_LOOP.search(text or ""))


def is_meta(translation: str) -> bool:
    t = translation or ""
    return bool(_META_EN.match(t) or _META_HI.match(t))


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    return con


def census(con: sqlite3.Connection, doc: str | None = None, show: int = 0) -> tuple[list[dict], dict]:
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    tt = "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
    has_l10n = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='translations_l10n'").fetchone()
    hi_join = "LEFT JOIN translations_l10n l ON l.passage_id=p.id AND l.lang='hi'" if has_l10n else ""
    hi_col = "l.translation" if has_l10n else "NULL"
    sql = f"""SELECT d.code, p.id, p.page_no, p.idx, p.text, p.translation, {hi_col}
              FROM passages p JOIN docs d ON d.id=p.doc_id {hi_join}
              WHERE 1=1 {tt} {"AND d.code=?" if doc else ""}"""
    agg: dict = defaultdict(lambda: defaultdict(int))
    samples: dict = defaultdict(list)
    for code, pid, pg, idx, text, en, hi in con.execute(sql, [doc] if doc else []):
        a = agg[code]
        a["passages"] += 1
        en_ok = bool(en and en.strip()); hi_ok = bool(hi and hi.strip())
        if is_apparatus(text):
            a["apparatus"] += 1
            a["apparatus_en_paid"] += int(en_ok); a["apparatus_hi_paid"] += int(hi_ok)
            if len(samples[(code, "apparatus")]) < show:
                samples[(code, "apparatus")].append((pid, pg, idx, (text or "")[:90]))
        if has_unit_loop(text):
            a["unitloop"] += 1
            if len(samples[(code, "unitloop")]) < show:
                samples[(code, "unitloop")].append((pid, pg, idx, (text or "")[:90]))
        if en_ok and is_meta(en):
            a["meta_en"] += 1
            if len(samples[(code, "meta_en")]) < show:
                samples[(code, "meta_en")].append((pid, pg, idx, en[:90]))
        if hi_ok and is_meta(hi):
            a["meta_hi"] += 1
            if len(samples[(code, "meta_hi")]) < show:
                samples[(code, "meta_hi")].append((pid, pg, idx, hi[:90]))
    rows = []
    for code, a in agg.items():
        r = {"doc": code}
        for k in COLS[1:]:
            r[k] = a[k]
        rows.append(r)
    rows.sort(key=lambda r: -(r["apparatus"] + r["unitloop"] + r["meta_en"] + r["meta_hi"]))
    return rows, samples


COLS = ["doc", "passages", "apparatus", "apparatus_en_paid", "apparatus_hi_paid", "unitloop", "meta_en", "meta_hi"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only census: apparatus rows, unit loops, meta outputs")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--show", type=int, default=0, help="print up to N sample rows per defect per doc")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db)
        return 2
    con = open_ro(args.db)
    try:
        rows, samples = census(con, args.doc, args.show)
    finally:
        con.close()
    shown = [r for r in rows if r["apparatus"] + r["unitloop"] + r["meta_en"] + r["meta_hi"]]
    w = {c: max([len(c)] + [len(str(r[c])) for r in shown]) for c in COLS}
    print("  ".join(c.ljust(w[c]) for c in COLS))
    for r in shown:
        print("  ".join(str(r[c]).ljust(w[c]) for c in COLS))
    tot = {k: sum(r[k] for r in rows) for k in COLS[1:]}
    print("\nTOTAL  " + " | ".join("%s %d" % (k, v) for k, v in tot.items()))
    for (code, kind), lst in sorted(samples.items()):
        print("\n  %s / %s:" % (code, kind))
        for pid, pg, idx, snippet in lst:
            print("    id %d  p%s.%s  %s" % (pid, pg, idx, snippet.replace("\n", " ")))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=COLS); wr.writeheader()
            for r in rows:
                wr.writerow(r)
        print("CSV: %s" % args.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
