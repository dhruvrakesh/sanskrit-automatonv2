#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_report.py — read-only corpus QA + truncation report (2026-08-20).

Safe to run ANY time, even while translate jobs are writing: it opens the DB
read-only (mode=ro), so it never contends for the writer lock. It replaces the
fragile inline `python -c "...SQL..."` one-liners that PowerShell mangles.

Per doc it reports: translated count, stored QA<0.2 count, mean QA, and a LIVE
truncation count — translations that end mid-sentence — computed with the same
rule the QA scorer uses. That means you can see the true scope of truncation
WITHOUT first running `qa_scan --write` (which is a writer and should wait for
idle).

Usage (from the automaton/ root):
  python scripts/qa_report.py                                    # docs with issues
  python scripts/qa_report.py --all                             # every doc
  python scripts/qa_report.py --doc upapurana_nilamata_purana --samples 8
  python scripts/qa_report.py --lang hi                         # Hindi track
"""
from __future__ import annotations
import argparse
import re
import sqlite3

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

# Same terminal set the QA scorer accepts as a complete ending. The pāda/verse
# marker "//" (ends in '/') is terminal — verses legitimately end "…, //".
_END_OK = ('.', '!', '?', '।', '॥', '…', ']', '"', "'", '”', '’', ')', '/')
# A trailing verse number after a daṇḍa/slash ("…// 41", "…॥ ४१") = complete verse
# (kept in sync with text_filters.score_translation_quality, 2026-08-23).
_VERSENUM_TAIL_RE = re.compile(r"(?://|/|।|॥)\s*[\d०-९]+\s*$")


def is_truncated(t: str) -> bool:
    if not t:
        return False
    tail = t.rstrip()
    if not tail or len(t) <= 40:
        return False
    if _VERSENUM_TAIL_RE.search(tail):
        return False  # ends in a verse number → complete verse, not truncated
    return not tail.endswith(_END_OK)


def main():
    ap = argparse.ArgumentParser(description="Read-only corpus QA + truncation report")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="limit to one doc code")
    ap.add_argument("--lang", default="en", help="'en' (passages) or e.g. 'hi' (translations_l10n)")
    ap.add_argument("--all", action="store_true", help="show every doc, not just ones with issues")
    ap.add_argument("--samples", type=int, default=0, help="with --doc: print N truncated samples")
    ap.add_argument("--ocr", action="store_true",
                    help="report SOURCE OCR legibility per doc (the re-OCR pile) "
                         "instead of translation QA — this is where empties come from")
    ap.add_argument("--coverage", action="store_true",
                    help="report EN vs HI translation COVERAGE per doc "
                         "(how many verses have English vs Hindi vs total). "
                         "Read-only; safe while jobs write.")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    # ── Coverage mode: EN (passages.translation) vs HI (translations_l10n) per doc.
    #    Replaces the hand-quoted SQL one-liners that PowerShell mangles. ──────────
    if args.coverage:
        cov_doc = "AND d.code = ?" if args.doc else ""
        rows = con.execute(
            f"""SELECT d.code AS code,
                       SUM(TRIM(COALESCE(p.translation,'')) <> '') AS en_done,
                       SUM(l.passage_id IS NOT NULL
                           AND TRIM(COALESCE(l.translation,'')) <> '') AS hi_done,
                       COUNT(*) AS verses
                FROM passages p
                JOIN docs d ON d.id = p.doc_id
                LEFT JOIN translations_l10n l
                       ON l.passage_id = p.id AND l.lang = 'hi'
                WHERE COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
                  {cov_doc}
                GROUP BY d.code
                ORDER BY d.code""",
            [args.doc] if args.doc else [],
        ).fetchall()
        print("EN vs HI translation coverage (verses with a stored translation)\n")
        print(f"{'doc':40}{'verses':>7}{'EN':>7}{'EN%':>6}{'HI':>7}{'HI%':>6}")
        print("-" * 73)
        t_v = t_en = t_hi = 0
        for r in rows:
            v = r["verses"] or 0
            en = r["en_done"] or 0
            hi = r["hi_done"] or 0
            if not args.all and en == 0 and hi == 0:
                continue
            t_v += v; t_en += en; t_hi += hi
            enp = (100 * en / v) if v else 0
            hip = (100 * hi / v) if v else 0
            print(f"{r['code']:40}{v:7}{en:7}{enp:5.0f}%{hi:7}{hip:5.0f}%")
        print("-" * 73)
        tenp = (100 * t_en / t_v) if t_v else 0
        thip = (100 * t_hi / t_v) if t_v else 0
        print(f"{'TOTAL':40}{t_v:7}{t_en:7}{tenp:5.0f}%{t_hi:7}{thip:5.0f}%")
        print("\nEN and HI are separate passes — a doc can be 100% EN and 0% HI. "
              "HI is translated directly from Sanskrit, not from the English.")
        con.close()
        return

    where_doc = "AND d.code = ?" if args.doc else ""
    params = [args.doc] if args.doc else []

    # ── OCR-legibility mode: which docs are garbled OCR (source unreadable), the
    #    real cause of empty translations. Read-only, safe any time. ──────────────
    if args.ocr:
        import re as _re
        DEV = _re.compile(r'[ऀ-ॿ]')
        LAT = _re.compile(r'[A-Za-z]')
        rows = con.execute(
            f"""SELECT d.code AS code, p.text AS txt, p.translation AS tr
                FROM passages p JOIN docs d ON d.id = p.doc_id
                WHERE TRIM(COALESCE(p.text,'')) <> ''
                  AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') {where_doc}""",
            params,
        ).fetchall()
        per = {}
        for r in rows:
            t = r["txt"] or ""
            nb = len(t.replace(" ", "").replace("\n", "")) or 1
            d = per.setdefault(r["code"], {"n": 0, "devsum": 0.0, "latsum": 0.0, "empty": 0})
            d["n"] += 1
            d["devsum"] += len(DEV.findall(t)) / nb
            d["latsum"] += len(LAT.findall(t)) / nb
            if not (r["tr"] or "").strip():
                d["empty"] += 1
        print("Source OCR legibility (low Dev% / high Lat% = garbled OCR -> re-OCR)\n")
        print(f"{'doc':32}{'verses':>7}{'srcDev%':>8}{'srcLat%':>8}{'untr':>6}")
        print("-" * 63)
        shown = 0
        for code in sorted(per, key=lambda c: per[c]["devsum"] / max(1, per[c]["n"])):
            d = per[code]
            dev = 100 * d["devsum"] / d["n"]
            lat = 100 * d["latsum"] / d["n"]
            # Garble shows up two ways: low Devanagari OR notable Latin noise in a
            # Sanskrit text (clean scans are ~0% Latin). The Latin signal catches
            # garbled-Devanagari docs like LalitaVistara that a Dev%-only test
            # misses, while sparing clean-but-unfinished docs (nilamata_seg ~0%).
            garbled = (dev < 60) or (lat > 8)
            if not args.all and not garbled:
                continue
            flag = "  <-- RE-OCR" if garbled else ""
            print(f"{code:32}{d['n']:7}{dev:8.0f}{lat:8.0f}{d['empty']:6}{flag}")
            shown += 1
        print("-" * 63)
        print(f"Shown {shown} doc(s) flagged for re-OCR (low Devanagari OR >8% Latin noise; "
              f"use --all for every doc).")
        print("A clean Sanskrit scan is ~90%+ Devanagari and ~0% Latin. Flagged docs translate")
        print("to empties because the SOURCE is unreadable — the fix is re-OCR, not re-translation.")
        con.close()
        return

    lang = (args.lang or "en").strip()
    is_l10n = lang != "en"

    if is_l10n:
        rows = con.execute(
            f"""SELECT d.code AS code, l.translation AS tr, l.translation_qa AS qa
                FROM translations_l10n l JOIN passages p ON p.id = l.passage_id
                JOIN docs d ON d.id = p.doc_id
                WHERE l.lang = ? AND TRIM(COALESCE(l.translation,'')) <> '' {where_doc}""",
            [lang] + params,
        ).fetchall()
    else:
        rows = con.execute(
            f"""SELECT d.code AS code, p.translation AS tr, p.translation_qa AS qa
                FROM passages p JOIN docs d ON d.id = p.doc_id
                WHERE TRIM(COALESCE(p.translation,'')) <> '' {where_doc}""",
            params,
        ).fetchall()

    per: dict[str, dict] = {}
    for r in rows:
        d = per.setdefault(r["code"], {"n": 0, "low": 0, "trunc": 0, "qasum": 0.0, "qan": 0})
        d["n"] += 1
        if r["qa"] is not None:
            d["qasum"] += r["qa"]; d["qan"] += 1
            if r["qa"] < 0.2:
                d["low"] += 1
        if is_truncated(r["tr"] or ""):
            d["trunc"] += 1

    print(f"lang={lang}  docs scanned={len(per)}\n")
    print(f"{'doc':32} {'transl':>7} {'QA<0.2':>7} {'trunc':>6} {'meanQA':>7}")
    print("-" * 66)
    total_tr = total_trunc = total_low = 0
    for code in sorted(per, key=lambda c: (-per[c]["trunc"], -per[c]["low"])):
        d = per[code]
        total_tr += d["n"]; total_trunc += d["trunc"]; total_low += d["low"]
        if not args.all and d["trunc"] == 0 and d["low"] == 0:
            continue
        mean = (d["qasum"] / d["qan"]) if d["qan"] else float("nan")
        print(f"{code:32} {d['n']:7} {d['low']:7} {d['trunc']:6} {mean:7.3f}")
    print("-" * 66)
    print(f"TOTAL translated={total_tr}  QA<0.2={total_low}  truncated={total_trunc}")

    if args.doc and args.samples:
        print(f"\n--- up to {args.samples} truncated tails in {args.doc} ---")
        shown = 0
        for r in rows:
            if r["code"] == args.doc and is_truncated(r["tr"] or ""):
                print(f"  qa={r['qa']}  ...{(r['tr'] or '')[-72:]!r}")
                shown += 1
                if shown >= args.samples:
                    break


if __name__ == "__main__":
    main()
