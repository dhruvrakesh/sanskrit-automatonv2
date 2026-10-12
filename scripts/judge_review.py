#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
judge_review.py  (2026-10-12)  REINGEST_2026_10_12   READ-ONLY

What the LLM judge (judge_sample.py, table mt_reviews) said of the English, text by text, and the passages it
marked: so that a person can check the judge, and the translations it doubts.

On 12 Oct the judge read 200 English passages of five texts (gemini-2.5-flash, about $0.04). It found a serious
error of meaning (fidelity 2 or less: an omission, a negation lost, a word misread) in 5% to 18% of the passages
of the texts read from vision, and in 38% of the Bodhicaryavatara's, whose Sanskrit is Tesseract's. A sample,
and a judge of the translator's family: these figures are its opinion until a person has read what it marks.

For each marked passage: where it is (page.idx), the scores, the judge's reason, the Sanskrit and the English.
A reason that blames the Sanskrit (garbled, corrupted, a typo, illegible) is counted apart: there the source,
not the translation, is to be mended first.

  python scripts\\judge_review.py                       every text the judge read: the figures
  python scripts\\judge_review.py --doc Mallapurana     and its passages of fidelity 2 or less
  python scripts\\judge_review.py --html exports\\judge_review.html   the same as a page to read (Devanagari)
"""
from __future__ import annotations

import argparse
import html
import re
import sqlite3
import sys
from pathlib import Path

MARK = "REINGEST_2026_10_12"
SOURCE_BLAMED = re.compile(r"garbl|corrupt|typo|ocr|illegib|damaged|unclear w|source (text )?is", re.I)


def open_ro(db: str):
    return sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def figures(con, lang: str) -> list:
    rows = con.execute(
        "SELECT d.code, COUNT(*), AVG(m.score_fidelity), AVG(m.score_fluency), "
        "SUM(CASE WHEN m.score_fidelity <= 2 THEN 1 ELSE 0 END), MIN(m.created_at), MAX(m.created_at) "
        "FROM mt_reviews m JOIN passages p ON p.id = m.passage_id JOIN docs d ON d.id = p.doc_id "
        "WHERE m.lang = ? GROUP BY d.code ORDER BY d.code", (lang,)).fetchall()
    return [{"doc": r[0], "n": r[1], "fidelity": round(r[2] or 0, 2), "fluency": round(r[3] or 0, 2),
             "serious": int(r[4] or 0), "first": r[5], "last": r[6]} for r in rows]


def marked(con, doc: str, lang: str, max_fid: int) -> list:
    out = []
    for pg, idx, text, tr, hi, fid, flu, why, eng in con.execute(
            "SELECT p.page_no, p.idx, p.text, p.translation, "
            "(SELECT l.translation FROM translations_l10n l WHERE l.passage_id = p.id AND l.lang = 'hi'), "
            "m.score_fidelity, m.score_fluency, m.comment, m.engine "
            "FROM mt_reviews m JOIN passages p ON p.id = m.passage_id JOIN docs d ON d.id = p.doc_id "
            "WHERE d.code = ? AND m.lang = ? AND m.score_fidelity <= ? ORDER BY m.score_fidelity, p.page_no, p.idx",
            (doc, lang, max_fid)):
        out.append({"where": "%d.%d" % (pg, idx), "text": text or "", "english": tr or "", "hindi": hi or "",
                    "fidelity": fid, "fluency": flu, "why": why or "", "engine": eng or "",
                    "source_blamed": bool(SOURCE_BLAMED.search(why or ""))})
    return out


def page(figs: list, marks: dict) -> str:
    e = lambda s: html.escape(str(s))
    rows = "".join("<tr><td>%s</td><td>%d</td><td>%.2f</td><td>%.2f</td><td>%d (%.0f%%)</td></tr>" % (
        e(f["doc"]), f["n"], f["fidelity"], f["fluency"], f["serious"], 100.0 * f["serious"] / f["n"]) for f in figs)
    body = ""
    for doc, ms in marks.items():
        body += "<h2>%s: %d passage(s) of fidelity 2 or less</h2>" % (e(doc), len(ms))
        for m in ms:
            body += ('<div class="m"><div class="h">%s &middot; fidelity %s, fluency %s%s</div><div class="why">%s</div>'
                     '<div class="sa" lang="sa">%s</div><div class="en">%s</div></div>' % (
                         e(m["where"]), e(m["fidelity"]), e(m["fluency"]),
                         " &middot; the judge blames the Sanskrit" if m["source_blamed"] else "", e(m["why"]),
                         e(m["text"]), e(m["english"])))
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\"><title>Judge review</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;background:#fff;color:#1d1d1f}"
            "table{border-collapse:collapse}td,th{border-bottom:1px solid #ddd;padding:4px 10px;text-align:left}"
            ".m{border:1px solid #ddd;border-radius:8px;padding:10px 12px;margin:10px 0}.h{font-weight:600}"
            ".why{color:#8a3b12;margin:4px 0}.sa{font-size:1.15em;margin:6px 0}.en{color:#333}"
            "</style></head><body><h1>What the judge said (judge_sample.py)</h1><p>A sample per text, judged by a model of "
            "the translator's family: its opinion until a person has read what it marks.</p><table><tr><th>Text</th>"
            "<th>Judged</th><th>Fidelity</th><th>Fluency</th><th>A wrong meaning</th></tr>%s</table>%s</body></html>"
            % (rows, body))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--max-fidelity", type=int, default=2)
    ap.add_argument("--html", default=None, help="write the review as a page to read")
    a = ap.parse_args()
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); return 1
    con = open_ro(a.db)
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "mt_reviews" not in have:
            print("VERDICT: the judge has read nothing yet (no mt_reviews table)")
            print("NEXT: python scripts\\judge_sample.py --doc 2015_405693_Shatpath-Brahmanam --sample-pct 2 --limit 60")
            return 0
        figs = figures(con, a.lang)
        docs = [a.doc] if a.doc else [f["doc"] for f in figs]
        marks = {d: marked(con, d, a.lang, a.max_fidelity) for d in docs}
    finally:
        con.close()
    out = sys.stdout
    print("judge_review.py  %s  (read-only)" % MARK)
    print("  %-62s %6s %9s %8s  %s" % ("text", "judged", "fidelity", "fluency", "a wrong meaning (fidelity <= 2)"))
    for f in figs:
        if a.doc and f["doc"] != a.doc:
            continue
        ms = marks.get(f["doc"], [])
        blamed = sum(1 for m in ms if m["source_blamed"])
        print("  %-62s %6d %9.2f %8.2f  %d (%.0f%%)%s" % (f["doc"][:62], f["n"], f["fidelity"], f["fluency"], f["serious"],
                                                       100.0 * f["serious"] / f["n"],
                                                       ("; %d of them blame the Sanskrit" % blamed) if blamed else ""))
    if a.doc:
        for m in marks.get(a.doc, []):
            out.write("\n  %s  fidelity %s fluency %s%s\n    judge: %s\n    sa: %s\n    en: %s\n" % (
                m["where"], m["fidelity"], m["fluency"], "  (blames the Sanskrit)" if m["source_blamed"] else "",
                m["why"], m["text"][:300], m["english"][:400]))
    if a.html:
        p = Path(a.html)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(page([f for f in figs if not a.doc or f["doc"] == a.doc], marks), encoding="utf-8")
        print("  wrote %s (open it in a browser)" % p)
    n = sum(f["n"] for f in figs if not a.doc or f["doc"] == a.doc)
    s = sum(f["serious"] for f in figs if not a.doc or f["doc"] == a.doc)
    print("VERDICT: %d passage(s) judged; %d (%.0f%%) with a wrong meaning, by the judge" % (n, s, 100.0 * s / n if n else 0))
    print("NEXT: " + ("python scripts\\judge_review.py --html exports\\judge_review.html   (read the marked passages)"
                      if not a.html else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
