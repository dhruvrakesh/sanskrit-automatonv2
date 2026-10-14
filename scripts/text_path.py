#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
text_path.py  (2026-10-12)  PATH_2026_10_12   READ-ONLY

The path of every text: one way forward for each, with its reason in numbers, its next command and its cost.

Asked on 12 Oct: "each text should either be fixable, retirable, or search for critical editions, better
quality scans or Sanskrit text to find the truth." The Sources page shows the texts whose scan stops a
translation; this charts all of them, the translated ones and the ones never ingested too, in one of:

  use the repair    vision has read the scan; the database still holds Tesseract's text (free)
  retire            another text holds the same work, better read (the duplicate goes; the site follows)
  ingest            pages not yet read (Tesseract, free) or not yet in the database
  repair the scan   vision OCR on the pages here, at the price measured on this text (or the corpus)
  find a source     the scan is not here, or cannot be repaired: a critical e-text or a better scan
  translate         a clean reading, not yet translated
  translate again   the LLM judge (judge_sample.py) marks a wrong meaning in 10% or more of a sample
  judge a sample    translated, but nothing has read its meaning
  in repair         repaired and being translated again, or an e-text witness (here only until it is adopted); the
                    site keeps its last version until it is published
  done              clean, translated, judged (or accepted as complete)

Rules, in order (each in decide() below): a state in the register (complete, in repair, an e-text witness, set
aside, withdrawn) decides first; then a duplicate of a better-read text; then pages not read or not ingested; then a vision
reading waiting to go in; then Tesseract's text: repaired before it is translated, when its scan is here
(only clean text is translated; a text already translated from Tesseract is repaired when its debris is
moderate or material); without its scan, a source is wanted; then translation, the judge, done. A repair
whose pages are not all in the database goes in before anything is translated (in repair and translate too),
so no English is made from the old reading's debris. A text without its scan whose letters are 5% or more
misread (or whose judged sample is a quarter wrong) is offered --withdraw: off the site and out of Ask the
Corpus until the better source is in (--restore undoes it; nothing is deleted).

Prices: a text with 20 or more vision pages in usage_log is priced from its own calls; the others at the
corpus price, with the dearest text's price as the upper bound (pages differ by book: $0.0011 to $0.0111
a page so far). --max-usd is set from the estimate; a run that reaches it stops before spending more, and
its first pages measure the text's own price for the next chart.
MIRROR_CAP_2026_10_12: the corpus price is that of the last 300 vision calls, so one dear text read last
raises it for all (on 12 Oct, $0.0100 a page after the Natyasastra's run; the median text $0.0024). The
estimate and the cap stay at the corpus price (ocr_consensus.py refuses a run whose estimate is above
--max-usd, and since this patch stops a run before a page would take it past), and the median of the
texts measured is given beside it, as what a text not yet measured most likely costs.

It opens the database read-only (repair_text.assess, as the Sources page does), reads the page folders, the
register, the judge's reviews and the price of vision and translation in usage_log. It writes
data/text_path.json (for the dashboard's /path page) and, with --html, a page to read.

  python scripts\\text_path.py                       every text
  python scripts\\text_path.py --doc nirukta         one text, with every fact
  python scripts\\text_path.py --html exports\\text_path.html
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

MARK = "PATH_2026_10_12"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

PATHS = (
    ("use_repair", "Use the repair", "vision has read the scan; the database still holds Tesseract's text"),
    ("retire", "Retire", "another text holds the same work, better read"),
    ("ingest", "Ingest", "pages not yet read, or not yet in the database"),
    ("repair", "Repair the scan", "vision OCR on the pages here, then the re-ingest"),
    ("source", "Find a source", "the scan is not here or cannot be repaired: a critical e-text or a better scan"),
    ("translate", "Translate", "a clean reading, not yet translated"),
    ("retranslate", "Translate again", "the judge marks a wrong meaning in 10% or more of its sample"),
    ("judge", "Judge a sample", "translated; nothing has read its meaning yet"),
    ("in_repair", "In repair", "being translated again, or an e-text witness; the site keeps its last version until it is "
                               "published"),
    ("done", "Done", "clean, translated and judged, or accepted as complete"),
)
ORDER = {k: i for i, (k, _, _) in enumerate(PATHS)}
SERIOUS = 10.0          # % of a judged sample with fidelity <= 2: translate again
CLEAN_VISION = 80.0     # % of passages read by vision: a clean reading
DUP_SHARE = 0.5         # share of letter 4-grams two readings share: the same work
JUDGE_SAMPLE = 40
T2_PER_PASSAGE = 0.0017  # REDEEM_2026_10_14: a marked passage translated again (pro), judged again, its Hindi again
WITHDRAW_MISREAD = 5.0  # % of letters misread (or a judged sample 25% wrong): withdrawing it from the site is offered
EN_PER_PASSAGE = 0.00063   # measured on 12 Oct (gemini-2.5-flash, the last 2,258 calls); usage_log decides
W = re.compile("[\u0900-\u0963\u0971-\u097f]+")


def q(doc: str) -> str:
    return "python scripts\\repair_text.py --doc %s" % doc


def usd(x: float) -> str:
    return "$%.2f" % x if x >= 0.995 else ("$%.3f" % x if x >= 0.0095 else "$%.4f" % x)


def per_page(x: float) -> str:
    """A price a page: $0.0111, not $0.011."""
    return "$%.4f" % x


def prices(db: str, codes=None) -> dict:
    """$ a vision page (corpus-wide, as ocr_consensus.py measures it), the texts priced from their own calls (20 or
    more vision pages delivered) and the dearest of them, and $ a translated passage (usage_log)."""
    out = {"vision_page": None, "vision_dear": None, "measured": [], "passage": EN_PER_PASSAGE,
           "passage_from": "default"}
    oc = None
    try:
        import ocr_consensus as oc
        out["vision_page"] = round(oc.measured_cost_per_page(db, fallback=0.0111), 5)
    except Exception:
        out["vision_page"] = 0.0111
    mine = []
    try:
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            r = con.execute("SELECT SUM(cost_usd), SUM(passages) FROM (SELECT cost_usd, passages FROM usage_log WHERE "
                            "kind='translation' AND passages > 0 ORDER BY id DESC LIMIT 3000)").fetchone()
            mine = [d for (d,) in con.execute("SELECT doc FROM usage_log WHERE kind='ocr_vision' AND token_source="
                                              "'provider' AND doc IS NOT NULL GROUP BY doc HAVING SUM(passages) >= 20")]
        finally:
            con.close()
        if r and r[0] and r[1]:
            out["passage"], out["passage_from"] = round(float(r[0]) / float(r[1]), 6), "usage_log"
    except sqlite3.Error:
        pass
    mine = sorted(d for d in mine if codes is None or d in codes)
    out["measured"] = mine
    dear = 0.0
    for d in mine:
        try:
            dear = max(dear, float(oc.measured_cost_per_page(db, fallback=0.0, doc=d)) if oc else 0.0)
        except Exception:
            pass
    out["vision_dear"] = round(max(dear, out["vision_page"] or 0.0), 5)
    each = []   # MIRROR_CAP_2026_10_12: the median of the texts measured
    for d in mine:
        try:
            x = float(oc.measured_cost_per_page(db, fallback=0.0, doc=d)) if oc else 0.0
        except Exception:
            x = 0.0
        if x > 0:
            each.append(x)
    each.sort()
    out["vision_median"] = (round(each[len(each) // 2] if len(each) % 2 else
                                  (each[len(each) // 2 - 1] + each[len(each) // 2]) / 2.0, 5) if len(each) >= 3 else None)
    return out


def money_line(tt: dict) -> str:
    """'about $X now (from $W at the median text's price; up to $Y at the dearest text's price); then about $Z to
    translate', the parts that are not 0."""
    parts = []
    if tt.get("cost"):
        hi, lo = tt.get("cost_hi") or 0.0, tt.get("cost_lo")
        side = []
        if lo is not None and lo < 0.95 * tt["cost"]:   # MIRROR_CAP_2026_10_12
            side.append("from %s at the median text's price" % usd(lo))
        if hi > 1.05 * tt["cost"]:
            side.append("up to %s at the dearest text's price" % usd(hi))
        parts.append("about %s now%s" % (usd(tt["cost"]), (" (%s)" % "; ".join(side)) if side else ""))
    if tt.get("then"):
        parts.append("then about %s to translate" % usd(tt["then"]))
    return "; ".join(parts)


def db_facts(db: str) -> dict:
    """Per text: pages in the database, the judge's reviews; the retired texts and what replaced them."""
    out = {"pages": {}, "reviews": {}, "retired": {}, "codes": []}
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        out["codes"] = [r[0] for r in con.execute("SELECT code FROM docs WHERE code IS NOT NULL ORDER BY code")]
        out["pages"] = dict(con.execute("SELECT d.code, COUNT(DISTINCT p.page_no) FROM docs d JOIN passages p ON "
                                        "p.doc_id=d.id GROUP BY d.code"))
        if "mt_reviews" in tables:
            for code, n, fid, ser in con.execute(
                    "SELECT d.code, COUNT(*), AVG(m.score_fidelity), SUM(CASE WHEN m.score_fidelity <= 2 THEN 1 ELSE 0 END) "
                    "FROM mt_reviews m JOIN passages p ON p.id=m.passage_id JOIN docs d ON d.id=p.doc_id "
                    "WHERE m.lang='en' GROUP BY d.code"):
                out["reviews"][code] = {"n": int(n), "fidelity": round(float(fid or 0), 2), "serious": int(ser or 0)}
        if "doc_stage" in tables:
            for code, reason in con.execute("SELECT doc_code, reason FROM doc_stage WHERE stage='retired'"):
                m = re.search(r"superseded by (\S+)", reason or "")
                out["retired"][code.replace("-RETIRED", "")] = m.group(1) if m else ""
    finally:
        con.close()
    return out


def grams(con, code: str, limit: int = 400) -> set:
    s = set()
    for (t,) in con.execute("SELECT p.text FROM passages p JOIN docs d ON d.id=p.doc_id WHERE d.code=? "
                            "ORDER BY p.page_no, p.idx LIMIT ?", (code, limit)):
        for w in W.findall(t or ""):
            w = " %s " % w
            s.update(w[i:i + 4] for i in range(len(w) - 3))
    return s


def duplicates(db: str, live: list, vision: dict) -> dict:
    """{retiree: (keeper, share)}: a text whose code ends with another's ("dhanur_veda_shiva_dhanur_veda" and
    "shiva_dhanur_veda") and whose letters it shares; the keeper is the one vision read, else the larger."""
    out = {}
    pairs = [(a, b) for a in live for b in live if a != b and b.endswith("_" + a)]
    if not pairs:
        return out
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        for a, b in pairs:
            ga, gb = grams(con, a), grams(con, b)
            if not ga or not gb:
                continue
            share = len(ga & gb) / float(min(len(ga), len(gb)))
            if share < DUP_SHARE:
                continue
            keep, go = (b, a) if (vision.get(b, 0), len(gb)) >= (vision.get(a, 0), len(ga)) else (a, b)
            out[go] = (keep, round(share, 2))
    finally:
        con.close()
    return out


def page_prefixes(folder: Path, ext: str) -> dict:
    rx = re.compile(r"^(.+)_(\d{4})(?:_norm)?\.%s$" % ext, re.I)
    out = {}
    if folder.is_dir():
        for e in os.scandir(folder):
            m = rx.match(e.name)
            if m:
                out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def changed_pages(db: str, doc: str, merged: Path) -> dict:
    """Pages of the repaired text that differ from the database (reingest_pages.plan), the English and Hindi their
    re-ingest removes and whether it must be said (--replace); pages -1 when not known."""
    out = {"pages": -1, "english": 0, "hindi": 0, "say": False}
    try:
        import reingest_pages as rp
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            p, _err = rp.plan(con, doc, merged, set())
        finally:
            con.close()
        if p:
            k, anc = p.get("kids") or {}, p.get("anchors") or {}
            lost = any(im.get("fate") == "loses its passage" for im in anc.get("images", [])) or any(
                st.get("fate") == "loses an end passage" for st in anc.get("stories", []))
            out.update(pages=len(p["changed"]), english=int(k.get("english") or 0), hindi=int(k.get("hindi") or 0))
            out["say"] = bool(out["english"] or out["hindi"] or lost)
    except Exception:
        pass
    return out


def apply_cmd(f: dict, rp: str) -> str:
    """The re-ingest's --apply line, with --replace as its plan asks (the English it removes)."""
    if f.get("changed", -1) >= 0 and "changed_say" in f:
        return rp + " --apply" + ((" --replace %d" % f.get("changed_en", 0)) if f.get("changed_say") else "")
    return rp + " --apply" + ((" --replace %d" % f["english"]) if f.get("english") else "")


def tr_cost(n_en: int, n_hi: int, pr: dict) -> float:
    return (max(0, n_en) + max(0, n_hi)) * pr["passage"]


def decide(f: dict, pr: dict) -> dict:
    """The path of one text from its facts: {path, why, next, also, cost, then}."""
    doc, st = f["doc"], (f.get("state") or "")
    n, en, hi = f["passages"], f["english"], f["hindi"]
    left = max(0, n - en - f.get("below_quality", 0))
    vis_pct, level = f["vision_pct"], f.get("level") or "-"
    pdfs, raw, vpages = f["pdfs"], f["raw_pages"], f["vision_pages"]
    cpp = f.get("cost_per_page") or pr["vision_page"]
    q0 = q(doc)
    rv = f.get("reviews") or {}
    serious = (100.0 * rv["serious"] / rv["n"]) if rv.get("n") else None
    lvl = ("debris %s (%.2f%% of letters misread)" % (level, f.get("misread_letters_pct") or 0.0)
           if level != "-" else "no debris found")
    tesseract = vis_pct < 50.0
    hi_left = max(0, en - hi) if en else 0
    then = tr_cost(n, n, pr)
    rp = "python scripts\\reingest_pages.py --doc %s" % doc
    mg = "python scripts\\merge_ocr_sources.py --doc %s" % doc
    o = {"path": "", "why": "", "next": [], "also": [], "cost": 0.0, "then": 0.0}
    # READ_IN_2026_10_13: a merge without its blank pages is a merge (the Natyasastra: 538 of 546 merged, 513 read by
    # vision; "merged_complete" asks for every page, so it was charted "repair the scan" for ever)
    merged_ok = (bool(f.get("merged_complete")) or (f.get("merged_pages") or 0) >= 0.95 * max(1, raw)) and \
        vpages >= 0.8 * max(1, raw)
    gave = int(f.get("vision_gave_up") or 0)   # pages vision failed on twice: left to Tesseract (the ledger)
    tryable = max(0, pdfs - vpages - gave)
    chg = f.get("changed", -1)
    if merged_ok and chg == 0:
        tesseract = False   # the database already holds the repaired reading, page for page
    pending = merged_ok and chg > 0   # a repair not all in the database: it goes in before anything is translated
    first = ([rp + "   (first: the %d changed page(s) of the repair into the database; the plan, free)" % chg,
              apply_cmd(f, rp) + "   (a backup first; refused while a job writes)"] if pending else [])

    if st == "complete":
        o.update(path="done", why="accepted as complete: %s" % (f.get("reason") or "what is left is not Sanskrit"))
        return o
    if f.get("dup_of"):
        keep, share = f["dup_of"]
        o.update(path="retire", why=("the same work as %s, which vision read (%d%% of their letter groups shared); "
                                     "this copy is Tesseract's" % (keep, round(100 * share))),
                 next=["python scripts\\retire_doc.py --doc %s --supersedes %s --dry-run" % (doc, keep),
                       "python scripts\\retire_doc.py --doc %s --supersedes %s --yes" % (doc, keep)],
                 also=["its %d English go with it; the keeper has its own (translate what it lacks)" % en] if en else [],
                 cost=0.0, then=tr_cost(f.get("keeper_left", 0), f.get("keeper_left", 0), pr))
        return o
    if st == "in_repair":
        why = ("repaired (%s, %.0f%% vision); English %d and Hindi %d of %d; the site keeps its last version (%s English) "
               "until it is published" % (lvl, vis_pct, en, hi, n, f.get("en_before", "?")))
        if pending:
            why += ("; but the database holds %s on %d page(s): translated now, the English would be made from it"
                    % ("Tesseract's reading" if vis_pct < 50.0 else "the old reading", chg))
        o.update(path="in_repair", why=why,
                 next=first + ["translate it: Finish EN and Add Hindi in the Library", q0 + " --release   (once the "
                               "translation is back; it refuses before)"],
                 cost=tr_cost(left + (f.get("changed_en", 0) if pending else 0),
                              max(0, n - hi) + (f.get("changed_hi", 0) if pending else 0), pr))
        if chg < 0 and f.get("merged_pages"):
            o["also"].append("whether the repair is all in the database is not known: %s   (the plan, free)" % rp)
        return o
    if st == "witness":
        of = f.get("of") or doc.split("__w_")[0]
        todo_tr = left > max(2, 0.02 * n) or (en and hi_left > max(2, 0.05 * en))
        o.update(path="in_repair", why=("an e-text witness of %s (%d passages, English %d, Hindi %d): here only, until it "
                                        "is adopted" % (of, n, en, hi)),
                 next=(["translate it: Finish EN and Add Hindi in the Library"] if todo_tr else []) +
                      [q0 + " --release   (adopts it: the next mirror run sends it to the site%s)"
                       % (" once it is translated" if todo_tr else "")],
                 cost=tr_cost(left, max(0, n - hi), pr))
        return o
    if st in ("set_aside", "withdrawn"):
        o.update(path="source", why=("%s on %s: %s" % ("set aside" if st == "set_aside" else "withdrawn from the site",
                                                        f.get("at", "?"), f.get("reason") or "a better source is wanted")),
                 next=[q0 + " --find-source   (free; --ai lets the AI judge the editions, about $0.002)"],
                 also=[q0 + " --restore   (when a better scan is in the inbox, or to send it to the site again)"])
        return o
    if n == 0:
        if pdfs and not raw:
            o.update(path="ingest", why="%d page PDFs in the inbox, none read; nothing in the database" % pdfs,
                     next=["Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/ocr -ContentType "
                           "\"application/json\" -Body '{\"doc\": \"%s\"}'   (Tesseract, free; an OCR job)" % doc],
                     then=0.0)
        elif raw:
            o.update(path="ingest", why="%d pages read by Tesseract, none in the database" % raw,
                     next=["Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/ingest -ContentType "
                           "\"application/json\" -Body '{\"doc\": \"%s\"}'   (free; then it is classified)" % doc])
        else:
            o.update(path="retire", why="an empty record: no passages, no pages, no PDFs",
                     next=["nothing to keep; it is hidden where it has no passages"])
        return o
    if pdfs and raw < 0.9 * pdfs:
        o.update(path="ingest", why="the OCR is unfinished: Tesseract read %d of its %d pages" % (raw, pdfs),
                 next=["Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/ocr -ContentType \"application/json\" "
                       "-Body '{\"doc\": \"%s\"}'   (the pages not read; Tesseract, free)" % doc,
                       rp + " --merged-dir data\\raw   (then the new pages into the database: the plan, free)"])
        return o
    if raw and f.get("db_pages", 0) < 0.8 * raw:
        o.update(path="ingest", why="the ingest is unfinished: %d of the %d pages Tesseract read are in the database"
                 % (f.get("db_pages", 0), raw),
                 next=[rp + " --merged-dir data\\raw   (the plan, free: the pages not yet in, untranslated)",
                       rp + " --merged-dir data\\raw --apply"])
        return o
    if tesseract and merged_ok:
        o.update(path="use_repair", why=("vision read %d of its %d pages and the repair is merged, but the database "
                                         "holds Tesseract's text (%s, %.0f%% vision)" % (vpages, raw, lvl, vis_pct)),
                 next=[mg + " --apply   (today's merge; free)", rp + "   (the plan, free)", apply_cmd(f, rp)],
                 then=tr_cost(n, n, pr))
        if en:
            o["also"].append("its %d English were made from Tesseract's text; the changed passages are translated again"
                             % en)
        if tryable:   # READ_IN_2026_10_13: the pages vision may still read, after
            cap2 = max(1.0, math.ceil(tryable * cpp * 1.25 * 10) / 10.0)
            o["also"].append("%d page(s) vision has not read yet%s: %s --repair --max-usd %.2f   (after; their pages go in "
                             "the same way)" % (tryable, (" (%d more left to Tesseract)" % gave) if gave else "", q0, cap2))
        elif gave:
            o["also"].append("%d page(s) keep Tesseract's reading: vision failed on them twice (--retry-refused tries them "
                             "again)" % gave)
        return o
    if tesseract:
        scan_here = pdfs and pdfs >= 0.9 * max(1, raw)
        damaged = level in ("moderate", "material")
        if scan_here and (damaged or en < 0.95 * n) and gave and not tryable:   # READ_IN_2026_10_13
            o.update(path="source", why=("Tesseract's text: %s; vision read %d of its %d pages and failed twice on the "
                                         "other %d: the scan resists repair" % (lvl, vpages, pdfs, gave)),
                     next=[q0 + " --find-source   (free: archive.org, the wisdomlib archive, GRETIL, the DSBC; "
                           "--ai about $0.002)"],
                     also=["the pages vision read can go in now: %s   (the plan, free)" % rp] if f.get("changed", 0) > 0 else [])
            return o
        if scan_here and (damaged or en < 0.95 * n):
            todo = max(0, pdfs - vpages - gave)   # READ_IN_2026_10_13: not the pages left to Tesseract
            est = todo * cpp
            cap = max(1.0, math.ceil(est * 1.25 * 10) / 10.0)
            own = f.get("price_from") == "this text"
            dear = max(cpp, pr.get("vision_dear") or cpp)
            est_hi = est if own else todo * dear
            med = pr.get("vision_median")
            est_lo = est if (own or not med) else min(est, todo * med)   # MIRROR_CAP_2026_10_12
            note = ("about %d pages at %s a page, measured on this text" % (todo, per_page(cpp)) if own else
                    "about %d pages at %s a page, the corpus price: not measured on this text yet; up to %s at the "
                    "dearest text's %s%s; it stops at the cap" % (
                        todo, per_page(cpp), usd(est_hi), per_page(dear),
                        ("; about %s at the median text's %s" % (usd(todo * med), per_page(med))) if med else ""))
            o.update(path="repair", why=("Tesseract's text: %s; %s; vision has read %d of its %d pages"
                                         % (lvl, ("%d of %d passages translated from it" % (en, n)) if en else
                                                 "nothing translated: vision first, so the English is made from a clean "
                                                 "reading", vpages, pdfs)),
                     next=[q0 + " --repair --max-usd %.2f   (%s)" % (cap, note),
                           rp + "   (after it: the changed pages, the plan, free)"],
                     cost=est, cost_hi=est_hi, cost_lo=est_lo, then=tr_cost(n, n, pr))
            if f.get("changed", 0) > 0 and vpages:
                o["also"].append("the %d page(s) vision has read can go in now: %s   (the plan, free)" % (f["changed"], rp))
            if f.get("vectors") and damaged:
                o["also"].append("%d of its passages are in Ask the Corpus (the brain) as they are" % f["vectors"])
            if f.get("etext"):
                o["also"].append("its e-text %s is here (%d passages): it may be the better reading; compare them first "
                                 "(free): python scripts\\benchmark_sources.py --doc %s"
                                 % (f["etext"]["doc"], f["etext"]["passages"], doc))
            return o
        if damaged:
            o.update(path="source", why=("Tesseract's text: %s; its scan is not here (%d page PDFs)%s"
                                         % (lvl, pdfs, ("; %d English on it" % en) if en else "")),
                     next=[q0 + " --find-source   (free: archive.org, the wisdomlib archive, GRETIL, the DSBC; "
                           "--ai about $0.002)"])
            if f.get("parent"):
                o["also"].append("its scan's pages are under %s (retired): a vision repair there would need its "
                                 "re-segmentation again" % f["parent"])
            if f.get("desk"):
                o["also"].append("the Source desk found: %s" % f["desk"])
            et = f.get("etext")
            if et:
                o["also"].append("its e-text %s is here (%d passages, %d English%s): when it is translated and read, this "
                                 "copy gives way to it: %s --withdraw \"superseded by its e-text %s\""
                                 % (et["doc"], et["passages"], et["english"], "; a witness, here only" if et["witness"]
                                    else "", q0, et["doc"]))
            if en and level == "material" and ((f.get("misread_letters_pct") or 0) >= WITHDRAW_MISREAD or
                                               (serious is not None and serious >= 25.0)):
                o["also"].append(q0 + " --withdraw \"its text is damaged: a better source is wanted\"   (takes its %d "
                                 "English off the site until then; --restore brings them back)" % en)
            return o
    # a clean reading (vision, an e-text, or Tesseract with no more than cosmetic debris and no scan to repair)
    if left > max(2, 0.02 * n) or (en and hi_left > max(2, 0.05 * en)):
        why = "%s (%.0f%% vision); English %d and Hindi %d of %d passages" % (lvl, vis_pct, en, hi, n)
        if pending:
            why += ("; %d page(s) of the repair are not in the database yet: they go in first, so their old reading "
                    "is not translated" % chg)
        o.update(path="translate", why=why, next=first + ["translate it: Finish EN and Add Hindi in the Library"],
                 cost=tr_cost(left + (f.get("changed_en", 0) if pending else 0),
                              max(0, n - hi) + (f.get("changed_hi", 0) if pending else 0), pr))
        return o
    if serious is None:
        o.update(path="judge", why="translated (English %d of %d, Hindi %d); %s; the judge has not read it" % (en, n, hi, lvl),
                 next=["python scripts\\judge_sample.py --doc %s --sample-pct %d --limit %d   (the dry run, free; then "
                       "--yes)" % (doc, max(1, min(100, int(math.ceil(100.0 * JUDGE_SAMPLE / max(1, en))))), JUDGE_SAMPLE)],
                 cost=JUDGE_SAMPLE * 0.00019)
        return o
    if serious >= SERIOUS:
        o.update(path="retranslate", why=("the judge read %d passages: fidelity %.2f of 5, a wrong meaning in %d (%.0f%%)"
                                          % (rv["n"], rv["fidelity"], rv["serious"], serious)),
                 next=["python scripts\\judge_review.py --doc %s   (read what it marks)" % doc,
                       "python scripts\\retranslate_marked.py --doc %s   (T2: the marked passages again with the stronger "
                       "engine, then judged again; the dry run, free)" % doc],   # REDEEM_2026_10_14
                 also=["the judge read %d of %d English: judge more to find the rest: python scripts\\judge_sample.py --doc %s "
                       "--sample-pct %d --limit 40   (the dry run, free)"
                       % (rv["n"], en, doc, max(1, min(100, int(math.ceil(100.0 * 2 * JUDGE_SAMPLE / max(1, en))))))],
                 cost=rv["serious"] * T2_PER_PASSAGE)
        return o
    o.update(path="done", why="translated (English %d of %d, Hindi %d); %s; the judge: fidelity %.2f, a wrong meaning in "
             "%.0f%% of %d" % (en, n, hi, lvl, rv["fidelity"], serious, rv["n"]))
    return o


def facts_of(a, code: str, extra: dict) -> dict:
    import repair_text as rt
    a.doc = code
    r = rt.assess(a)
    if r.get("error"):
        return {"doc": code, "error": r["error"]}
    j = r.get("judged") or {}
    st = r.get("state") or {}
    f = {k: r.get(k) for k in ("passages", "english", "hindi", "vectors", "pictures", "stories", "debris_pct",
                                "vision_pct", "below_quality", "pdfs", "raw_pages", "vision_pages", "merged_pages",
                                "merged_complete", "cost_per_page", "vision_gave_up")}
    f.update(doc=code, level=j.get("level") if r.get("debris_pct") else "-",
             misread_letters_pct=j.get("misread_letters_pct"), state=st.get("status"), reason=st.get("reason"),
             at=str(st.get("at") or "")[:10], en_before=st.get("en_before"))
    f.update(extra)
    return f


def chart(a) -> dict:
    import repair_text as rt
    listing = {}

    def cached_pages_in(folder, doc, ext):
        """rt.pages_in, from one listing of each folder (it lists the folder for every text otherwise)."""
        key = (str(folder), ext)
        if key not in listing:
            listing[key] = page_prefixes(Path(folder), ext)
        return set(listing[key].get(doc, ()))
    rt.pages_in = cached_pages_in   # this process only
    dbf = db_facts(a.db)
    pr = prices(a.db, set(dbf["codes"]))
    own = set(pr.get("measured") or [])
    reg = rt.verdicts(Path(a.verdicts))
    live = [c for c in dbf["codes"] if not c.endswith("-RETIRED")]
    retired = [c for c in dbf["codes"] if c.endswith("-RETIRED")]
    only = [a.only] if a.only else live
    facts = {}
    for i, code in enumerate(only, 1):
        last = reg.get(code) or {}
        extra = {"db_pages": dbf["pages"].get(code, 0), "reviews": dbf["reviews"].get(code)}
        f = facts_of(a, code, extra)
        if last.get("status") == "withdrawn":   # not one of repair_text's states before PATH_2026_10_12
            f.update(state="withdrawn", reason=last.get("reason"), at=str(last.get("at") or "")[:10])
        if last.get("status") == "witness":   # ETEXT_WITNESS_2026_10_11: an e-text, here only until it is adopted
            f.update(state="witness", of=last.get("of") or code.split("__w_")[0], at=str(last.get("at") or "")[:10])
        f["price_from"] = "this text" if code in own else "the corpus"
        if f.get("merged_pages"):
            ch = changed_pages(a.db, code, Path(a.merged_dir))
            f.update(changed=ch["pages"], changed_en=ch["english"], changed_hi=ch["hindi"], changed_say=ch["say"])
        facts[code] = f
        if a.progress:
            print("  [%d/%d] %s" % (i, len(only), code[:70]), flush=True)
    vision = {c: (facts[c].get("vision_pct") or 0) for c in facts if not facts[c].get("error")}
    if not a.only:
        for go, (keep, share) in duplicates(a.db, list(facts), vision).items():
            facts[go]["dup_of"] = (keep, share)
            kf = facts.get(keep) or {}
            facts[go]["keeper_left"] = max(0, (kf.get("passages") or 0) - (kf.get("english") or 0) - (kf.get("below_quality") or 0))
    for code in list(facts):   # an e-text witness of a text ("<code>__w_<source>") is noted on the text it reads
        base = code.split("__w_")[0] if "__w_" in code else ""
        if base in facts and not facts[code].get("error"):
            w = facts[code]
            facts[base]["etext"] = {"doc": code, "passages": w.get("passages") or 0, "english": w.get("english") or 0,
                                    "witness": w.get("state") == "witness"}
    succ = {v: k for k, v in dbf["retired"].items() if v}
    for code, f in facts.items():
        if code in succ:
            f["parent"] = succ[code]
        d = Path(a.source_desk) / ("%s.json" % code)
        if d.exists():
            try:
                c = (json.loads(d.read_text(encoding="utf-8")).get("candidates") or [])[:1]
                if c:
                    f["desk"] = "%s (%s), score %s" % (c[0].get("title") or c[0].get("identifier"), c[0].get("identifier"),
                                                      c[0].get("score"))
            except (OSError, ValueError):
                pass
    texts = []
    for code, f in facts.items():
        if f.get("error"):
            texts.append({"doc": code, "path": "ingest", "why": f["error"], "next": [], "also": [], "cost": 0.0, "then": 0.0,
                          "facts": f})
            continue
        o = decide(f, pr)
        o.update(doc=code, facts={k: v for k, v in f.items() if k not in ("dup_of",)})
        texts.append(o)
    # what is in the inbox or in data/raw and not in the database at all
    if not a.only:
        pdf = page_prefixes(Path(a.inbox), "pdf")
        raw = page_prefixes(Path(a.raw), "jsonl")
        known = set(dbf["codes"]) | {c.replace("-RETIRED", "") for c in retired}
        for code in sorted((set(pdf) | set(raw)) - known):
            npdf, nraw = len(pdf.get(code, ())), len(raw.get(code, ()))
            f = {"doc": code, "passages": 0, "english": 0, "hindi": 0, "vision_pct": 0.0, "pdfs": npdf, "raw_pages": nraw,
                 "vision_pages": 0, "db_pages": 0}
            o = decide(f, pr)
            if npdf and nraw and nraw < 0.9 * npdf:
                o["why"] = "not in the database; Tesseract read %d of its %d pages" % (nraw, npdf)
                o["next"] = ["Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/ocr -ContentType "
                             "\"application/json\" -Body '{\"doc\": \"%s\"}'   (the pages not read; Tesseract, free)" % code,
                             "Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5057/api/ingest -ContentType "
                             "\"application/json\" -Body '{\"doc\": \"%s\"}'   (then into the database)" % code]
            o.update(doc=code, facts=f, new=True)
            texts.append(o)
        for c in retired:
            base = c.replace("-RETIRED", "")
            texts.append({"doc": c, "path": "done", "why": "retired%s" % (
                "; superseded by %s" % dbf["retired"][base] if dbf["retired"].get(base) else ""),
                          "next": [], "also": [], "cost": 0.0, "then": 0.0, "facts": {"doc": c}, "retired": True})
    texts.sort(key=lambda t: (ORDER.get(t["path"], 99), -(t.get("cost") or 0), t["doc"]))
    totals = {}
    for t in texts:
        if t.get("retired"):
            continue
        x = totals.setdefault(t["path"], {"texts": 0, "cost": 0.0, "cost_hi": 0.0, "cost_lo": 0.0, "then": 0.0})
        x["texts"] += 1; x["cost"] += t.get("cost") or 0.0; x["then"] += t.get("then") or 0.0
        x["cost_hi"] += t.get("cost_hi") or t.get("cost") or 0.0
        x["cost_lo"] += t["cost_lo"] if t.get("cost_lo") is not None else (t.get("cost") or 0.0)
    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices": pr, "texts": texts,
            "totals": totals, "paths": [list(p) for p in PATHS]}


def show(res: dict, one: bool) -> None:
    pr = res["prices"]
    print("text_path.py  %s  (read-only)   vision %s a page (the corpus, its last 300 calls; %d text(s) priced from "
          "their own calls, the median %s, the dearest %s), translation %s a passage (%s)"
          % (MARK, per_page(pr["vision_page"] or 0), len(pr.get("measured") or []),
             per_page(pr.get("vision_median") or 0) if pr.get("vision_median") else "-",
             per_page(pr.get("vision_dear") or 0), "$%.5f" % pr["passage"], pr["passage_from"]))
    names = {k: label for k, label, _ in PATHS}
    cur = None
    for t in res["texts"]:
        if t.get("retired") and not one:
            continue
        if t["path"] != cur and not one:
            cur = t["path"]
            tt = res["totals"].get(cur, {})
            ml = money_line(tt)
            print("\n== %s: %d text(s)%s" % (names.get(cur, cur).upper(), tt.get("texts", 0), ("; " + ml) if ml else ""))
        print("  %-58s %s" % (t["doc"][:58], t["why"]))
        for n in t["next"][:4]:
            print("      NEXT: " + n)
        for n in t.get("also", [])[:3]:
            print("      ALSO: " + n)
        if one:
            print("  facts: " + json.dumps(t.get("facts"), ensure_ascii=False, sort_keys=True))
    c = sum(v["cost"] for v in res["totals"].values())
    hi = sum(v.get("cost_hi") or v["cost"] for v in res["totals"].values())
    lo = sum(v["cost_lo"] if v.get("cost_lo") is not None else v["cost"] for v in res["totals"].values())
    th = sum(v["then"] for v in res["totals"].values())
    ml = money_line({"cost": c, "cost_hi": hi, "cost_lo": lo})
    print("\nVERDICT: %d text(s) charted: %s; %s, then about %s of translation"
          % (sum(v["texts"] for v in res["totals"].values()),
             ", ".join("%d %s" % (res["totals"][k]["texts"], names[k].lower()) for k, _, _ in PATHS if k in res["totals"]),
             ml or "about $0.0000 now", usd(th)))


def page(res: dict) -> str:
    e = lambda s: html.escape(str(s))
    body = ""
    for k, label, desc in PATHS:
        rows = [t for t in res["texts"] if t["path"] == k and not t.get("retired")]
        if not rows:
            continue
        tt = res["totals"][k]
        ml = money_line(tt)
        body += "<h2>%s <span>%d</span></h2><p class=d>%s%s</p><table>" % (
            e(label), len(rows), e(desc), (" &middot; " + e(ml)) if ml else "")
        for t in rows:
            body += "<tr><td class=c>%s</td><td>%s%s%s</td></tr>" % (
                e(t["doc"]), e(t["why"]), "".join("<div class=n>NEXT %s</div>" % e(n) for n in t["next"]),
                "".join("<div class=a>ALSO %s</div>" % e(n) for n in t.get("also", [])))
        body += "</table>"
    return ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
            "initial-scale=1'><title>The path</title><style>body{font-family:system-ui,sans-serif;max-width:1100px;"
            "margin:20px auto;padding:0 16px;background:#fff;color:#1d1d1f}h2{margin-top:26px}h2 span{font-weight:400;"
            "font-size:14px;color:#666}.d{color:#555;margin:2px 0 8px}table{border-collapse:collapse;width:100%%}"
            "td{border-bottom:1px solid #ddd;padding:6px 8px;vertical-align:top;font-size:14px}.c{width:30%%;"
            "font-weight:600;word-break:break-all}.n{font-family:monospace;font-size:12px;color:#174ea6;margin-top:3px;"
            "word-break:break-all}.a{font-family:monospace;font-size:12px;color:#8a3b12;margin-top:3px;word-break:"
            "break-all}</style></head><body><h1>The path of every text</h1><p>Charted %s by text_path.py (%s): vision "
            "%s a page at the corpus price (a text with its own vision calls is priced from them; the median so far "
            "%s, the dearest %s), translation %s a passage.</p>%s</body></html>"
            % (e(res["at"]), MARK, per_page(res["prices"]["vision_page"] or 0),
               per_page(res["prices"].get("vision_median") or 0) if res["prices"].get("vision_median") else "-",
               per_page(res["prices"].get("vision_dear") or 0), "$%.5f" % res["prices"]["passage"], body))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", dest="only", default=None)
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--work", default="data/ocr_consensus")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--source-desk", default="data/source_desk")
    ap.add_argument("--out", default="data/text_path.json")
    ap.add_argument("--html", default=None)
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    if a.from_dashboard:
        a.progress = True
    res = chart(a)
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
    print("NEXT: " + ("open http://127.0.0.1:5057/path (after a dashboard restart), or python scripts\\text_path.py --html "
                      "exports\\text_path.html" if not a.html else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
