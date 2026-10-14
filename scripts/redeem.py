#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
redeem.py  (2026-10-14)  REDEEM_2026_10_14   READ-ONLY

What of the translation already paid for can be kept, and what cannot: text by text, passage by passage.

Asked on 14 Oct: "substantial time and money and energy have gone into translating all these texts. What can be
redeemed and what cannot should be clearly marked." Each English translation in the database is one of:

  judged sound    the LLM judge (judge_sample.py) read it: fidelity 3 or more
  judged wrong    the judge read it: fidelity 2 or less. Translated again with the stronger engine
                  (retranslate_marked.py, T2), unless the judge blames the Sanskrit: then the source first
  vision          made from a vision reading of the page (not judged)
  no debris seen  made from a reading without visible OCR debris (Tesseract, or an ingest older than the reading's
                  record). Kept; a repair keeps it too where vision reads the passage the same way
  debris          made from a passage whose Devanagari carries Latin letters (Tesseract's misreads): not
                  redeemable as it is. Translated again after the repair, or from a better source

and each text gets one verdict, by the share of its English that is kept:
  redeemed            97% or more kept, and the judge (where it read a sample) marks less than 10% of it
  mostly redeemed     half or more kept; the rest is translated again: after the scan's repair, or with the
                      stronger engine where the judge marks it (T2)
  to translate again  less than half kept: made from misread Sanskrit, made again after the repair (its scan is here)
  not redeemable      less than half kept, and its scan is not here: a better source is wanted first
  replaced            paid for, and no English here now: a repair (or a re-ingest) replaced the reading it was made
                      from; the site keeps the old English of a text in repair until it is translated again and released
  withdrawn           off the site and out of Ask the Corpus, kept here

Money: what the translation of each text cost (usage_log, repriced at today's prices where the tokens are known,
as spend_audit.py prices them), the share of it on English that cannot be kept as it is, and what translating
those passages again costs at the measured price (the stronger engine for the judged wrong). Translating again is
cheap; what the money bought that lasts is the clean reading, and the English made from one.

It opens the database read-only, reads the register (data/source_verdicts.jsonl), the page folders, and the chart
(data/text_path.json) when it is there. It writes data/redeem.json (for the dashboard's Library and /redeem page)
and, with --html or --csv, a page or a table.

  python scripts\\redeem.py                                   every text
  python scripts\\redeem.py --doc nirukta                     one text, with its classes
  python scripts\\redeem.py --html exports\\redeem.html --csv exports\\redeem.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime
import html
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

MARK = "REDEEM_2026_10_14"
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")   # = repair_text.JUNK (Latin letters in Devanagari)
DEV = re.compile("[\u0900-\u097f]")
SOURCE_BLAMED = re.compile(r"garbl|corrupt|typo|ocr|illegib|damaged|unclear w|source (text )?is", re.I)  # = judge_review
CLASSES = ("judged_sound", "judged_wrong", "vision", "no_debris", "debris")
LABEL = {"judged_sound": "judged sound", "judged_wrong": "judged wrong", "vision": "vision", "no_debris": "no debris seen",
         "debris": "debris"}
T2_SHARE = 10.0          # % of a judged sample wrong: translate again what it marks (and judge more)
KEPT_ALL = 97.0          # % of the English kept: redeemed
KEPT_MOST = 50.0         # % of the English kept: mostly redeemed (below it: translated again, or a source first)
FLASH_DEFAULT, PRO_DEFAULT = 0.00048, 0.00099   # $ a passage, measured on 13 Oct; usage_log decides
VERDICTS = (
    ("redeemed", "Redeemed", "kept as it is: 97% or more made from a clean reading, and the judge marks less than 10% "
                             "of what it read"),
    ("mostly", "Mostly redeemed", "half or more kept; the rest is translated again, after the scan's repair or with "
                                  "the stronger engine where the judge marks it (T2)"),
    ("redo", "To translate again", "less than half can be kept: made from misread Sanskrit, it is made again after the "
                                   "scan's repair (cheap: the reading is what costs)"),
    ("source", "Not redeemable as it is", "less than half can be kept, and the scan is not here: a better source "
                                          "is wanted first"),
    ("replaced", "Replaced by a better reading", "no English here now: a repair (or a re-ingest) replaced the reading it "
                                                 "was made from; translated again, cheaply, from the better reading"),
    ("withdrawn", "Withdrawn", "off the site and out of Ask the Corpus; kept here until a better source replaces it"),
)
ORDER = {k: i for i, (k, _, _) in enumerate(VERDICTS)}


def open_ro(db: str):
    return sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def usd(x: float) -> str:
    return "$%.2f" % x if x >= 0.995 else ("$%.3f" % x if x >= 0.0095 else "$%.4f" % x)


def price(engine: str, tin, tout, recorded) -> float:
    """$ of one usage_log row: repriced at today's table when its tokens are known (spend_audit.py), else as
    recorded."""
    try:
        import spend_audit
        p, _src = spend_audit.price_now(engine or "")
    except Exception:
        p = None
    if p and (tin or tout):
        return ((tin or 0) * p[0] + (tout or 0) * p[1]) / 1e6
    return float(recorded or 0.0)


def spend_by_doc(con) -> tuple:
    """({doc: $ of its translation calls}, $ a passage on flash, $ a passage on pro), from usage_log."""
    by, flash, pro = {}, [0.0, 0], [0.0, 0]
    try:
        rows = con.execute("SELECT doc, engine, in_tokens, out_tokens, cost_usd, passages FROM usage_log "
                           "WHERE kind='translation'").fetchall()
    except sqlite3.Error:
        return by, FLASH_DEFAULT, PRO_DEFAULT
    for doc, eng, tin, tout, cost, n in rows:
        x = price(eng, tin, tout, cost)
        by[doc] = by.get(doc, 0.0) + x
        acc = pro if "pro" in (eng or "") else flash
        acc[0] += x
        acc[1] += max(0, n or 0)
    f = (flash[0] / flash[1]) if flash[1] >= 100 else FLASH_DEFAULT
    p = (pro[0] / pro[1]) if pro[1] >= 50 else PRO_DEFAULT
    return by, round(f, 6), round(p, 6)


def register(path: Path) -> dict:
    last = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[str(r["doc"])] = r
    except OSError:
        pass
    return last


def page_counts(folder: Path, ext: str) -> dict:
    rx = re.compile(r"^(.+)_(\d{4})(?:_norm)?\.%s$" % ext, re.I)
    out = {}
    if folder.is_dir():
        for e in os.scandir(folder):
            m = rx.match(e.name)
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def classify(con, only: str | None = None) -> dict:
    """{doc: {"n", "en", classes..., "marked": [(page, idx, fidelity, why)]}} over the verses (not noise or front
    matter) of the live texts."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    tt = "COALESCE(p.text_type,'mula')" if "text_type" in cols else "'mula'"
    oe = "p.ocr_engine" if "ocr_engine" in cols else "NULL"
    rev = {}
    try:
        for pid, fid, why in con.execute("SELECT passage_id, score_fidelity, comment FROM mt_reviews WHERE lang='en' "
                                         "ORDER BY id"):
            rev[pid] = (fid, why or "")
    except sqlite3.Error:
        pass
    sql = ("SELECT d.code, p.id, p.page_no, p.idx, p.text, p.translation, %s, %s FROM passages p JOIN docs d ON "
           "d.id = p.doc_id WHERE d.code NOT LIKE '%%-RETIRED'" % (oe, tt))
    args = ()
    if only:
        sql += " AND d.code = ?"
        args = (only,)
    out = {}
    for code, pid, pg, idx, text, tr, eng, ttype in con.execute(sql, args):
        if ttype in ("noise", "frontmatter"):
            continue
        r = out.setdefault(code, dict({k: 0 for k in CLASSES}, n=0, en=0, marked=[], blamed=0))
        r["n"] += 1
        if not (tr or "").strip():
            continue
        r["en"] += 1
        junk = len(DEV.findall(text or "")) >= 8 and bool(JUNK.search(text or ""))
        if pid in rev and rev[pid][0] is not None:
            fid, why = rev[pid]
            if fid <= 2:
                r["judged_wrong"] += 1
                blamed = bool(SOURCE_BLAMED.search(why)) or junk
                r["blamed"] += 1 if blamed else 0
                r["marked"].append((pg, idx, fid, why[:160], blamed))
            else:
                r["judged_sound"] += 1
        elif "vision" in (eng or "").lower():
            r["vision"] += 1
        elif junk:
            r["debris"] += 1
        else:
            r["no_debris"] += 1
    return out


def judge(code: str, r: dict, reg: dict, scan_here: bool, spent: float, flash: float, pro: float, chart: dict) -> dict:
    """The verdict of one text, its line for the Library card, and its money."""
    en = r["en"]
    judged = r["judged_sound"] + r["judged_wrong"]
    wrong_pct = (100.0 * r["judged_wrong"] / judged) if judged else 0.0
    keep = r["judged_sound"] + r["vision"] + r["no_debris"]
    redo_debris = r["debris"]
    redo_wrong = r["judged_wrong"] - r["blamed"]
    st = (reg.get(code) or {}).get("status")
    kept_pct = (100.0 * keep / en) if en else 0.0
    t2 = bool(judged) and wrong_pct >= T2_SHARE
    if st == "withdrawn":
        v = "withdrawn"
    elif kept_pct >= KEPT_ALL and not t2:
        v = "redeemed"
    elif kept_pct >= KEPT_MOST:
        v = "mostly"
    elif scan_here:
        v = "redo"
    else:
        v = "source"
    at_risk = (spent * (redo_debris + r["judged_wrong"]) / en) if en else 0.0
    redo_cost = redo_debris * flash + redo_wrong * pro + r["blamed"] * flash
    n_ = lambda x: "{:,}".format(x)
    how = []   # what makes up the rest
    if redo_debris:
        how.append("%s made from misread Sanskrit, translated again %s (about %s)"
                   % (n_(redo_debris), "after the repair" if scan_here else "from a better source",
                      usd(redo_debris * flash)))
    if r["judged_wrong"]:
        how.append("the judge marks %d of %d sampled (%.0f%%)%s" % (
            r["judged_wrong"], judged, wrong_pct, (": translate them again (T2, about %s), then judge more"
                                                   % usd(redo_wrong * pro)) if redo_wrong else ""))
    if v == "withdrawn":
        line = ("Withdrawn: off the site; its %s English stay here (%s made from a clean reading) until a better source "
                "replaces it" % (n_(en), n_(keep)))
    elif v == "redeemed":
        line = "Redeemed: %s of %s English kept%s" % (n_(keep), n_(en), ("; " + "; ".join(how)) if how else "")
    elif v == "mostly":
        line = "Mostly redeemed: %s of %s English kept (%.0f%%); %s" % (n_(keep), n_(en), kept_pct, "; ".join(how))
    elif v == "redo":
        line = ("To translate again: %s of %s English kept; %s" % (n_(keep), n_(en), "; ".join(how)))
    else:
        line = ("Not redeemable as it is: %s of %s English made from misread Sanskrit, and its scan is not here: a "
                "better source first" % (n_(redo_debris), n_(en)))
    c = (chart or {}).get(code) or {}
    return {"doc": code, "verdict": v, "line": line, "passages": r["n"], "english": en,
            "classes": {k: r[k] for k in CLASSES}, "keep": keep, "redo_debris": redo_debris, "redo_wrong": redo_wrong,
            "blamed": r["blamed"], "judged": judged, "wrong_pct": round(wrong_pct, 1), "scan_here": bool(scan_here),
            "kept_pct": round(kept_pct, 1),
            "state": st, "spent": round(spent, 4), "at_risk": round(at_risk, 4), "redo_cost": round(redo_cost, 4),
            "path": c.get("path"), "changed_en": (c.get("facts") or {}).get("changed_en"),
            "marked": [{"where": "%s.%s" % (pg, idx), "fidelity": fid, "why": why, "source_blamed": b}
                       for pg, idx, fid, why, b in r["marked"][:60]]}


def replaced(code: str, r: dict, reg: dict, scan_here: bool, spent: float, flash: float, chart: dict) -> dict:
    """A text paid for that has no English here now: a repair (in place) or a re-ingest replaced its reading."""
    st = (reg.get(code) or {}).get("status")
    n_ = lambda x: "{:,}".format(x)
    again = r["n"] * flash
    if st == "in_repair":
        line = ("Replaced by the repair: its English (%s) was made from the old reading; the %s verses of the repaired "
                "reading are here, not yet translated; the site keeps the old English until they are translated and "
                "released (about %s)" % (usd(spent), n_(r["n"]), usd(again)))
    else:
        line = ("No English now: %s was spent on English that is no longer here (its passages were ingested again); "
                "its %s verses can be translated again (about %s)" % (usd(spent), n_(r["n"]), usd(again)))
    c = (chart or {}).get(code) or {}
    return {"doc": code, "verdict": "withdrawn" if st == "withdrawn" else "replaced", "line": line, "passages": r["n"],
            "english": 0, "classes": {k: r[k] for k in CLASSES}, "keep": 0, "redo_debris": 0, "redo_wrong": 0,
            "blamed": 0, "judged": 0, "wrong_pct": 0.0, "scan_here": bool(scan_here), "kept_pct": 0.0, "state": st,
            "spent": round(spent, 4), "at_risk": round(spent, 4), "redo_cost": round(again, 4), "path": c.get("path"),
            "changed_en": (c.get("facts") or {}).get("changed_en"), "marked": []}


def ledger(a) -> dict:
    con = open_ro(a.db)
    try:
        classes = classify(con, a.only)
        spent, flash, pro = spend_by_doc(con)
    finally:
        con.close()
    reg = register(Path(a.verdicts))
    pdfs, raw = page_counts(Path(a.inbox), "pdf"), page_counts(Path(a.raw), "jsonl")
    chart = {}
    try:
        for t in json.loads(Path(a.chart).read_text(encoding="utf-8")).get("texts") or []:
            chart[t.get("doc")] = t
    except (OSError, ValueError):
        pass
    texts = []
    for code, r in classes.items():
        here = pdfs.get(code, 0) > 0 and pdfs.get(code, 0) >= 0.9 * max(1, raw.get(code, 0))
        if r["en"]:
            texts.append(judge(code, r, reg, here, spent.get(code, 0.0), flash, pro, chart))
        elif spent.get(code, 0.0) > 0:   # paid for, and no English here now
            texts.append(replaced(code, r, reg, here, spent[code], flash, chart))
    texts.sort(key=lambda t: (ORDER[t["verdict"]], -t["at_risk"], t["doc"]))
    tot = {k: sum(t["classes"][k] for t in texts) for k in CLASSES}
    tot.update(english=sum(t["english"] for t in texts), keep=sum(t["keep"] for t in texts),
               redo_debris=sum(t["redo_debris"] for t in texts), redo_wrong=sum(t["redo_wrong"] for t in texts),
               blamed=sum(t["blamed"] for t in texts), spent=round(sum(t["spent"] for t in texts), 4),
               at_risk=round(sum(t["at_risk"] for t in texts), 4), redo_cost=round(sum(t["redo_cost"] for t in texts), 4),
               spent_all=round(sum(spent.values()), 4),
               spent_replaced=round(sum(t["spent"] for t in texts if not t["english"]), 4),
               replaced=sum(1 for t in texts if not t["english"]),
               spent_gone=round(sum(v for k, v in spent.items() if k not in classes), 4))
    by = {}
    for t in texts:
        by[t["verdict"]] = by.get(t["verdict"], 0) + 1
    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices":
            {"flash": flash, "pro": pro}, "verdicts": [list(v) for v in VERDICTS], "by_verdict": by, "totals": tot,
            "texts": texts}


def show(res: dict, one: bool) -> None:
    t, p = res["totals"], res["prices"]
    pct = lambda x: (100.0 * x / t["english"]) if t["english"] else 0.0
    print("redeem.py  %s  (read-only)   translation %s a passage (flash), %s (pro)" % (MARK, usd(p["flash"]),
                                                                                    usd(p["pro"])))
    names = {k: label for k, label, _ in VERDICTS}
    cur = None
    for x in res["texts"]:
        if x["verdict"] != cur and not one:
            cur = x["verdict"]
            print("\n== %s: %d text(s)" % (names[cur].upper(), res["by_verdict"].get(cur, 0)))
        c = x["classes"]
        print("  %-52s EN %6s  sound %5d  vision %5d  clean %5d  debris %5d  wrong %3d/%-3d  spent %-7s at risk %s"
              % (x["doc"][:52], "{:,}".format(x["english"]), c["judged_sound"], c["vision"], c["no_debris"], c["debris"],
                 c["judged_wrong"], x["judged"], usd(x["spent"]), usd(x["at_risk"])))
        print("      %s" % x["line"])
        if one:
            for m in x["marked"]:
                print("      marked %s  fidelity %s%s: %s" % (m["where"], m["fidelity"],
                                                            "  (the judge blames the Sanskrit)" if m["source_blamed"]
                                                            else "", m["why"]))
    rep = t.get("spent_replaced") or 0.0
    print("\nVERDICT: %s English in %d text(s): %s kept (%.0f%%): judged sound %s, vision %s, no debris seen %s; %s made "
          "from misread Sanskrit (%.0f%%), %s judged wrong (%s of them blaming the Sanskrit). The translation cost %s: "
          "%s of it on English that cannot be kept as it is%s; translating those again costs about %s."
          % ("{:,}".format(t["english"]), len(res["texts"]) - t.get("replaced", 0), "{:,}".format(t["keep"]),
             pct(t["keep"]), "{:,}".format(t["judged_sound"]), "{:,}".format(t["vision"]), "{:,}".format(t["no_debris"]),
             "{:,}".format(t["debris"]), pct(t["debris"]), "{:,}".format(t["judged_wrong"]), t["blamed"],
             usd(t["spent"]), usd(t["at_risk"] - rep),
             (", %s on English a better reading replaced (%d text(s), no English here now)" % (usd(rep), t["replaced"]))
             if t.get("replaced") else "", usd(t["redo_cost"])))
    if t.get("spent_gone"):
        print("  and %s was spent on texts no longer in the database (retired or re-segmented)" % usd(t["spent_gone"]))


def page(res: dict) -> str:
    e = lambda s: html.escape(str(s))
    t = res["totals"]
    body = ""
    for k, label, desc in VERDICTS:
        rows = [x for x in res["texts"] if x["verdict"] == k]
        if not rows:
            continue
        body += "<h2>%s <span>%d</span></h2><p class=d>%s</p><table><tr><th>Text</th><th>English</th><th>Kept</th>" \
                "<th>Debris</th><th>Judged wrong</th><th>Spent</th><th>At risk</th></tr>" % (e(label), len(rows), e(desc))
        for x in rows:
            body += "<tr><td><b>%s</b><div class=l>%s</div></td><td>%s</td><td>%s</td><td>%s</td><td>%d of %d</td>" \
                    "<td>%s</td><td>%s</td></tr>" % (e(x["doc"]), e(x["line"]), "{:,}".format(x["english"]),
                                                    "{:,}".format(x["keep"]), "{:,}".format(x["redo_debris"]),
                                                    x["classes"]["judged_wrong"], x["judged"], usd(x["spent"]),
                                                    usd(x["at_risk"]))
        body += "</table>"
    return ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
            "initial-scale=1'><title>What is redeemed</title><style>body{font-family:system-ui,sans-serif;max-width:1100px;"
            "margin:20px auto;padding:0 16px;background:#fff;color:#1d1d1f}h2 span{font-weight:400;color:#666;font-size:14px}"
            ".d{color:#555}table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid #ddd;padding:5px 8px;"
            "text-align:left;vertical-align:top;font-size:14px}.l{color:#555;font-size:12px;margin-top:2px}</style></head>"
            "<body><h1>What of the translation is redeemed</h1><p>Counted %s by redeem.py (%s): %s English, %s kept; %s "
            "made from misread Sanskrit; %s judged wrong. Spent %s, of it %s on English that cannot be kept as it is; "
            "translating those again: about %s.</p>%s</body></html>"
            % (e(res["at"]), MARK, "{:,}".format(t["english"]), "{:,}".format(t["keep"]), "{:,}".format(t["debris"]),
               "{:,}".format(t["judged_wrong"]), usd(t["spent"]), usd(t["at_risk"]), usd(t["redo_cost"]), body))


def write_csv(res: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc", "verdict", "english", "kept", "judged_sound", "vision", "no_debris_seen", "debris",
                    "judged_wrong", "judged", "wrong_pct", "scan_here", "spent_usd", "at_risk_usd", "redo_usd", "line"])
        for x in res["texts"]:
            c = x["classes"]
            w.writerow([x["doc"], x["verdict"], x["english"], x["keep"], c["judged_sound"], c["vision"], c["no_debris"],
                        c["debris"], c["judged_wrong"], x["judged"], x["wrong_pct"], int(x["scan_here"]), x["spent"],
                        x["at_risk"], x["redo_cost"], x["line"]])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", dest="only", default=None)
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--chart", default="data/text_path.json")
    ap.add_argument("--out", default="data/redeem.json")
    ap.add_argument("--html", default=None)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    res = ledger(a)
    show(res, bool(a.only))
    if not a.only:
        p = Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, p)
        print("  wrote %s" % p)
    if a.html:
        h = Path(a.html)
        h.parent.mkdir(parents=True, exist_ok=True)
        h.write_text(page(res), encoding="utf-8")
        print("  wrote %s (open it in a browser)" % h)
    if a.csv:
        write_csv(res, Path(a.csv))
        print("  wrote %s" % a.csv)
    print("NEXT: " + ("python scripts\\retranslate_marked.py   (the passages the judge marks: the dry run, free)"
                      if res["totals"].get("redo_wrong") else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
