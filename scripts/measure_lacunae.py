#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
measure_lacunae.py  (2026-09-30)  LACUNA_MEASURE_2026_09_30

READ-ONLY. Counts lacuna marks per document, split by the OCR engine that
produced the source text, for English (passages.translation) and Hindi
(translations_l10n, lang='hi').

Why a script and not pasted SQL: Windows PowerShell 5 turns Devanagari in a
here-string into '?'. The Hindi column of the 2026-09-30 lacuna table was
produced by  LIKE '%[???????]%'  and cannot be trusted. Every Devanagari
literal below is a \\u escape, so nothing depends on the console encoding.

The `hi_qmark` column counts Hindi rows that contain '???' or U+FFFD. It should
be 0. If it is not, some Hindi was damaged by an encoding round-trip at write
time, which is a separate problem from lacunas.

Scope matches translate_passages.py: text_type 'noise' and 'frontmatter' are
excluded.

Opens the database with mode=ro and PRAGMA query_only=1. Safe while the
dashboard runs.

  python scripts\\measure_lacunae.py
  python scripts\\measure_lacunae.py --doc Mallapurana
  python scripts\\measure_lacunae.py --csv exports\\lacunae_20260930.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

MARK = "LACUNA_MEASURE_2026_09_30"

# [ILLEGIBLE] and [asphuta] (Devanagari, escaped). Same pattern as text_filters._LACUNA_RE.
LACUNA_RE = re.compile(r"\[\s*(?:illegible|\u0905\u0938\u094d\u092a\u0937\u094d\u091f)\s*\]", re.I)
# Only lacuna tokens, punctuation, digits and danda: the verse was not translated at all.
BARE_RE = re.compile(r"^(?:\s|[\d\u0966-\u096f.,;:|/\-\u0964\u0965()]|"
                     r"\[\s*(?:illegible|\u0905\u0938\u094d\u092a\u0937\u094d\u091f)\s*\])*$", re.I)
QMARK_RE = re.compile(r"\?{3,}|\ufffd")


def classify(text: str) -> tuple[int, int, int]:
    """(has_lacuna, n_tokens, bare) for one translation."""
    if not text or not text.strip():
        return 0, 0, 0
    n = len(LACUNA_RE.findall(text))
    if not n:
        return 0, 0, 0
    return 1, n, 1 if BARE_RE.match(text) else 0


def open_ro(db: str) -> sqlite3.Connection:
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.execute("PRAGMA query_only=1")
    return con


def measure(con: sqlite3.Connection, doc: str | None = None) -> list[dict]:
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    eng = "COALESCE(NULLIF(TRIM(p.ocr_engine),''),'(unrecorded)')" if "ocr_engine" in cols else "'(no column)'"
    tt = "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
    where_doc = "AND d.code = ?" if doc else ""
    params = [doc] if doc else []
    has_l10n = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='translations_l10n'").fetchone()
    hi_join = ("LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'"
               if has_l10n else "")
    hi_col = "l.translation" if has_l10n else "NULL"
    sql = f"""SELECT d.code, {eng}, p.translation, {hi_col}
              FROM passages p JOIN docs d ON d.id = p.doc_id
              {hi_join}
              WHERE 1=1 {tt} {where_doc}"""
    agg: dict = defaultdict(lambda: defaultdict(int))
    for code, engine, en, hi in con.execute(sql, params):
        a = agg[(code, engine)]
        a["passages"] += 1
        if en and en.strip():
            a["en_done"] += 1
            h, n, b = classify(en)
            a["en_lac"] += h; a["en_tok"] += n; a["en_bare"] += b
        if hi and hi.strip():
            a["hi_done"] += 1
            h, n, b = classify(hi)
            a["hi_lac"] += h; a["hi_tok"] += n; a["hi_bare"] += b
            if QMARK_RE.search(hi):
                a["hi_qmark"] += 1
    out = []
    for (code, engine), a in agg.items():
        r = {"doc": code, "engine": engine}
        for k in ("passages", "en_done", "en_lac", "en_tok", "en_bare",
                  "hi_done", "hi_lac", "hi_tok", "hi_bare", "hi_qmark"):
            r[k] = a[k]
        r["en_lac_pct"] = round(100.0 * r["en_lac"] / r["en_done"], 1) if r["en_done"] else 0.0
        r["hi_lac_pct"] = round(100.0 * r["hi_lac"] / r["hi_done"], 1) if r["hi_done"] else 0.0
        out.append(r)
    out.sort(key=lambda r: (-(r["en_lac"] + r["hi_lac"]), r["doc"], r["engine"]))
    return out


def breakdowns(con: sqlite3.Connection, doc: str | None = None) -> dict:
    """LACUNA_MEASURE_2026_10_01: where do the lacunas come from?
    by_prompt_en / by_prompt_hi : {mt_prompt_version: [done, with_lacuna]}
    hi_by_anchor : Hindi split by whether a QA-passed English exists NOW
                   (>= 0.6, the default --anchor-min-qa). Correlational only: it
                   is today's English, not necessarily the one the Hindi saw.
    paired       : verses translated in BOTH languages - which side marked a lacuna.
                   'hi_only' far above 'both' means the Hindi lacunas are not caused
                   by an unreadable source: English read the same text."""
    pcols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='translations_l10n'").fetchone():
        return {}
    lcols = {r[1] for r in con.execute("PRAGMA table_info(translations_l10n)")}
    pv_en = "COALESCE(p.mt_prompt_version,'(none)')" if "mt_prompt_version" in pcols else "'(no column)'"
    pv_hi = "COALESCE(l.mt_prompt_version,'(none)')" if "mt_prompt_version" in lcols else "'(no column)'"
    qa = "COALESCE(p.translation_qa,0.0)" if "translation_qa" in pcols else "0.0"
    tt = "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in pcols else ""
    where_doc = "AND d.code = ?" if doc else ""
    sql = f"""SELECT p.translation, {pv_en}, {qa}, l.translation, {pv_hi}
              FROM passages p JOIN docs d ON d.id = p.doc_id
              LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
              WHERE 1=1 {tt} {where_doc}"""
    out = {"by_prompt_en": defaultdict(lambda: [0, 0]), "by_prompt_hi": defaultdict(lambda: [0, 0]),
           "hi_by_anchor": defaultdict(lambda: [0, 0]),
           "paired": {"pairs": 0, "both": 0, "en_only": 0, "hi_only": 0, "neither": 0}}
    for en, ven, q, hi, vhi in con.execute(sql, [doc] if doc else []):
        en_ok = bool(en and en.strip()); hi_ok = bool(hi and hi.strip())
        el = classify(en)[0] if en_ok else 0
        hl = classify(hi)[0] if hi_ok else 0
        if en_ok:
            b = out["by_prompt_en"][ven]; b[0] += 1; b[1] += el
        if hi_ok:
            b = out["by_prompt_hi"][vhi]; b[0] += 1; b[1] += hl
            key = "english QA>=0.6 now" if (en_ok and q >= 0.6) else "no QA-passed English"
            b = out["hi_by_anchor"][key]; b[0] += 1; b[1] += hl
        if en_ok and hi_ok:
            pr = out["paired"]; pr["pairs"] += 1
            pr["both" if (el and hl) else "en_only" if el else "hi_only" if hl else "neither"] += 1
    return out


def _pct(d, l):
    return (100.0 * l / d) if d else 0.0


COLS = ["doc", "engine", "passages", "en_done", "en_lac", "en_lac_pct", "en_bare",
        "hi_done", "hi_lac", "hi_lac_pct", "hi_bare", "hi_qmark"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only lacuna census by doc and OCR engine")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--min", type=int, default=1, help="hide rows with fewer lacuna rows than this (default 1)")
    ap.add_argument("--csv", default=None, help="also write the full table (all rows) to this CSV")
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db)
        return 2
    con = open_ro(args.db)
    rows = measure(con, args.doc)
    bd = breakdowns(con, args.doc)
    con.close()
    shown = [r for r in rows if (r["en_lac"] + r["hi_lac"]) >= args.min]
    w = {c: max(len(c), *(len(str(r[c])) for r in shown)) if shown else len(c) for c in COLS}
    print("  ".join(c.ljust(w[c]) for c in COLS))
    for r in shown:
        print("  ".join(str(r[c]).ljust(w[c]) for c in COLS))
    tot = defaultdict(int)
    for r in rows:
        for k in ("passages", "en_done", "en_lac", "en_bare", "hi_done", "hi_lac", "hi_bare", "hi_qmark"):
            tot[k] += r[k]
    print("\nTOTAL  passages %(passages)d | en %(en_done)d done, %(en_lac)d with lacuna (%(en_bare)d bare)"
          " | hi %(hi_done)d done, %(hi_lac)d with lacuna (%(hi_bare)d bare) | hi_qmark %(hi_qmark)d" % tot)
    by_eng = defaultdict(lambda: [0, 0])
    for r in rows:
        by_eng[r["engine"]][0] += r["en_done"]; by_eng[r["engine"]][1] += r["en_lac"]
    print("English lacuna rate by OCR engine:")
    for e, (d, l) in sorted(by_eng.items()):
        print("  %-22s %6d translated  %5d with lacuna  %5.1f%%" % (e, d, l, (100.0 * l / d) if d else 0.0))
    if tot["hi_qmark"]:
        print("\nWARNING: %d Hindi rows contain '???' or U+FFFD - encoding damage at write time." % tot["hi_qmark"])
    if bd:
        for key, title in (("by_prompt_en", "English lacuna rate by prompt version:"),
                           ("by_prompt_hi", "Hindi lacuna rate by prompt version:"),
                           ("hi_by_anchor", "Hindi lacuna rate by English reference available (today's English):")):
            print("\n" + title)
            for k, (d, l) in sorted(bd[key].items(), key=lambda kv: -kv[1][0]):
                print("  %-28s %6d done  %5d with lacuna  %5.1f%%" % (k, d, l, _pct(d, l)))
        pr = bd["paired"]
        print("\nVerses translated in BOTH languages: %(pairs)d" % pr)
        print("  lacuna in both %(both)d | English only %(en_only)d | Hindi only %(hi_only)d | neither %(neither)d" % pr)
        if pr["hi_only"] > 3 * max(pr["both"], 1):
            print("  -> most Hindi lacunas sit on verses English read in full: a Hindi prompt/model effect, not OCR.")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=COLS)
            wr.writeheader()
            for r in rows:
                wr.writerow({c: r[c] for c in COLS})
        print("CSV: %s (%d rows)" % (args.csv, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
