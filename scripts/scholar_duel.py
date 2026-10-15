#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
scholar_duel.py  (2026-10-15)  CLAUDE_ENGINE_2026_10_15 (duel-v1)

The scholarly Englishes of the same verses by different engines (gemini-2.5-pro, Claude Sonnet 5.5, Claude Opus 5.5 ...),
read side by side by judges of both families, blind: who made each is not said, and the order is shuffled for each judge.
The page is blind too: the person reads "Translation 1, 2, 3" and picks (--pick); the names are under a fold. The
judges' verdicts are advice; the person's reading decides.

What is compared: for each verse, each engine's latest scholarly English whose Sanskrit is unchanged (src_hash). A
Sanskrit sentence that one engine translated whole over several verses is read whole, for every engine (a span). An
engine without a current English for every verse of a span is left out of that span.

The judges (--judges): gemini:gemini-2.5-pro and anthropic:claude-opus-5-5, one of each family, as either may favour its
own. Each gives every translation fidelity, prose and notes (1 to 5) and its errors, then a ranking and the best. The
glossary the scholarly runs grew is not shown to them (it would carry one engine's spellings). Stored: scholar_duels,
append-only; a span a judge has read on the same rows is not asked again (--redo asks). Spend: usage_log (kind
"judge"); the Gemini part in the spend cap, the Claude part in the Claude credit (claude_engine.py).

  python scripts\\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --pages 20-21 --limit 12               the dry run, free
  python scripts\\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --pages 20-21 --limit 12 --yes --max-usd 1.50
  python scripts\\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --report      exports\\scholar_duel_<doc>.html (free)
  python scripts\\scholar_duel.py --doc HAYASHIRSHA_PANCARATRA --pick 20.5=2,20.6-20.9=1 --by Dhruv   the person's
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import scholar_translate as ST   # noqa: E402

MARK = "CLAUDE_ENGINE_2026_10_15"
DUEL_VERSION = "duel-v1"
JUDGES = ("gemini:gemini-2.5-pro", "anthropic:claude-opus-5-5")
LABELS = "ABCDEFGH"
PERSON = "person:"

SYSTEM_DUEL = """You are a senior Sanskritist judging several English translations of the same Sanskrit of {title}, for a critical-edition translation series. The register wanted is that of an unabridged translation made from a critical edition, as Bibek Debroy's Mahabharata is from the BORI Critical Edition: every word rendered and nothing added, names and terms kept in IAST and explained in short notes, in plain, dignified modern English prose. Judge against the Sanskrit given; the verses before and after are there to help you see who is who and how the sentence runs. Who made each translation is not said, and their order means nothing.
For each translation, by its letter: "fidelity", 1 to 5 (5 = every word's meaning and every grammatical relation kept, every person rightly named); "prose", 1 to 5 (5 = natural, dignified English that reads as a good book reads, with no archaism and no paraphrase); "notes", 1 to 5 (5 = the notes a reader needs, right and brief; 3 = none, and none was needed; lower for a wrong note, or a needed one missing); and "errors", each {"where": the Sanskrit word or words, "error": what is wrong, "severity": major|minor}. Major: a wrong meaning, a wrong person, a word that matters left out or added. Do not invent errors: an empty list is right for a faithful translation. Then "ranking": every letter, from the best to the least good (fidelity first, then prose, then notes); "best": the letter of the best, or "equal" when none is better; and "reason": a sentence or two.

Reply with one JSON object and nothing else:
{"A": {"fidelity": 0, "prose": 0, "notes": 0, "errors": []}, "B": {"fidelity": 0, "prose": 0, "notes": 0, "errors": []}, "ranking": ["A", "B"], "best": "A", "reason": ""}"""

if hasattr(ST, "SYSTEMS"):
    ST.SYSTEMS["duel"] = SYSTEM_DUEL


# --------------------------------------------------------------------------------------------- the rows
def ensure_schema(con) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS scholar_duels(
      id INTEGER PRIMARY KEY AUTOINCREMENT, doc_code TEXT NOT NULL, span_ref TEXT NOT NULL, passage_ids TEXT NOT NULL,
      judge_engine TEXT NOT NULL, prompt_version TEXT, engines TEXT, row_ids TEXT, verdict TEXT, best TEXT,
      cost_usd REAL, created_at TEXT);
    CREATE INDEX IF NOT EXISTS ix_scholar_duels_doc ON scholar_duels(doc_code, span_ref);
    """)
    con.commit()


def engine_rows(con, doc: str) -> dict:
    """{engine: {passage_id: its latest row}} of this text."""
    if not ST.has_table(con, "scholar_translations"):
        return {}
    cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? ORDER BY id", (doc,))
    names = [d[0] for d in cur.description]
    out = {}
    for r in cur.fetchall():
        r = dict(zip(names, r))
        out.setdefault(r["engine"], {})[r["passage_id"]] = r
    return out


def group_counts(con, doc: str) -> dict:
    """{(engine, group_ref, created_at): rows}: how many verses each sentence was stored in."""
    if not ST.has_table(con, "scholar_translations"):
        return {}
    return {(e, g, c): n for e, g, c, n in con.execute(
        "SELECT engine, group_ref, created_at, COUNT(*) FROM scholar_translations WHERE doc_code = ? AND group_ref IS NOT "
        "NULL GROUP BY engine, group_ref, created_at", (doc,))}


def units_for(engine: str, rows: dict, counts: dict, pos: dict) -> dict:
    """{passage_id: unit} of one engine: a unit is one sentence's rows (one group_ref, made together) or one row; whole
    when none of its verses has a later row of this engine."""
    by = {}
    for pid, r in rows.items():
        key = (r["group_ref"], r["created_at"]) if r.get("group_ref") else ("#%d" % r["id"], None)
        by.setdefault(key, []).append(r)
    out = {}
    for key, rs in by.items():
        rs.sort(key=lambda r: pos.get(r["passage_id"], 1 << 30))
        whole = (not rs[0].get("group_ref")) or len(rs) == counts.get((engine, key[0], key[1]), len(rs))
        u = {"rows": rs, "whole": whole, "pids": [r["passage_id"] for r in rs]}
        for r in rs:
            out[r["passage_id"]] = u
    return out


def unit_text(u: dict) -> str:
    r0 = u["rows"][0]
    if r0.get("group_ref"):
        return (r0.get("group_translation") or " ".join(r.get("translation") or "" for r in u["rows"])).strip()
    return (r0.get("translation") or "").strip()


def pick_verses(a, allp: list, er: dict, engines: list) -> list:
    """The places in allp of the verses chosen (--pages, --from-ref, --only-page, --limit) that two engines or more have
    a current English for."""
    pages = ST.parse_pages(a.pages)
    started = not a.from_ref
    out = []
    for i, x in enumerate(allp):
        if pages is not None and x["page"] not in pages:
            continue
        if a.only_page is not None and x["page"] != a.only_page:
            continue
        if not started:
            if ST.ref_of(x) != a.from_ref:
                continue
            started = True
        if sum(1 for e in engines if ST.current(er.get(e, {}).get(x["id"]), x)) >= 2:
            out.append(i)
            if len(out) >= a.limit:
                break
    return out


def spans_of(picked: list, allp: list, ub: dict, engines: list) -> list:
    """[(lo, hi)] in allp: each picked verse, widened to every sentence an engine translated whole over it, the
    overlaps joined."""
    pos = {x["id"]: i for i, x in enumerate(allp)}
    iv = [[i, i] for i in picked]
    for e in engines:
        seen = set()
        for i in picked:
            u = ub.get(e, {}).get(allp[i]["id"])
            if u and id(u) not in seen and len(u["pids"]) > 1:
                seen.add(id(u))
                ps = [pos[p] for p in u["pids"] if p in pos]
                iv.append([min(ps), max(ps)])
    iv.sort()
    out = []
    for lo, hi in iv:
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [tuple(s) for s in out]


def span_ref(xs: list) -> str:
    return ST.ref_of(xs[0]) if len(xs) == 1 else "%s-%s" % (ST.ref_of(xs[0]), ST.ref_of(xs[-1]))


def engine_text(e: str, xs: list, er: dict, ub: dict):
    """{text, notes, doubts, row_ids, rows} of engine e over the verses xs, or None when it has not each of them whole
    and current."""
    ids = {x["id"] for x in xs}
    us, seen = [], set()
    for x in xs:
        r = er.get(e, {}).get(x["id"])
        u = ub.get(e, {}).get(x["id"])
        if not ST.current(r, x) or u is None or not u["whole"] or not set(u["pids"]) <= ids:
            return None
        if id(u) not in seen:
            seen.add(id(u))
            us.append(u)
    notes, doubts = [], []
    for u in us:
        notes.extend(ST._loads(u["rows"][0].get("notes"), []))
        if u["rows"][0].get("doubts"):
            doubts.append(u["rows"][0]["doubts"])
    rows = [r for u in us for r in u["rows"]]
    return {"text": " ".join(unit_text(u) for u in us), "notes": notes, "doubts": "; ".join(doubts),
            "row_ids": sorted(r["id"] for r in rows), "rows": rows}


def judge_base(con, a, allp: list, lo: int, hi: int, meta: dict) -> str:
    """The judges' message without the translations: the verse(s) with the context (the working English), the glossary
    without the entries the scholarly runs added, the edition's apparatus."""
    xs = allp[lo:hi + 1]
    before, after = ST.context(allp, lo, {})
    if len(xs) > 1:
        after = ST.context(allp, hi, {})[1]
    gl = [g for g in ST.glossary(con, a.doc, xs[0], before + [(y, "") for y in xs[1:]]) if g.get("source") != "scholar"]
    base = ST.verse_message(meta, xs[0], before, after, gl) if len(xs) == 1 else ST.group_message(meta, xs, before,
                                                                                                   after, gl)
    return ST.with_apparatus(base, allp, xs)


def duel_message(base: str, shown: list) -> str:
    """shown: [(letter, English, notes)]."""
    parts = [base]
    for lab, en, notes in shown:
        parts.append("TRANSLATION %s:\n%s\nITS NOTES:\n%s" % (lab, en, ST.notes_text(notes)))
    return "\n\n".join(parts)


def clean_duel(d, labels: str):
    """The judge's answer, cleaned; None when it is not one."""
    if not isinstance(d, dict):
        return None
    sides = {}
    for L in labels:
        v = d.get(L) if isinstance(d.get(L), dict) else {}
        errs = []
        for x in v.get("errors") or []:
            if isinstance(x, dict) and ST._s(x.get("error"), 300):
                sev = ST._s(x.get("severity"), 10).lower()
                errs.append({"where": ST._s(x.get("where"), 200), "error": ST._s(x.get("error"), 300),
                             "severity": "major" if sev == "major" else "minor"})
        sides[L] = {"fidelity": ST._int15(v.get("fidelity")), "prose": ST._int15(v.get("prose")),
                    "notes": ST._int15(v.get("notes")), "errors": errs[:12]}
    if all(sides[L]["fidelity"] is None for L in labels):
        return None
    rk = []
    for x in d.get("ranking") or []:
        x = str(x).strip().upper()
        if x in labels and x not in rk:
            rk.append(x)
    rk += [L for L in sorted(labels, key=lambda L: -(sides[L]["fidelity"] or 0)) if L not in rk]
    best = str(d.get("best") or "").strip()
    best = best.upper() if best.upper() in labels else ("equal" if best.lower() == "equal" else rk[0])
    return {"sides": sides, "ranking": rk, "best": best, "reason": ST._s(d.get("reason"), 600)}


def order_for(engines, seed: str) -> list:
    out = sorted(engines)
    random.Random(seed).shuffle(out)
    return out


def duel_one(asker, judge: str, base: str, texts: dict, seed: str):
    """One judge's reading of one span: {labels, by_engine, ranking, best, reason}, or None."""
    engs = order_for(texts, seed + "|" + judge)
    labels = LABELS[:len(engs)]
    d, _c = asker.ask("duel", duel_message(base, [(L, texts[e]["text"], texts[e]["notes"]) for L, e in zip(labels, engs)]))
    c = clean_duel(d, labels)
    if c is None:
        return None
    m = dict(zip(labels, engs))
    return {"labels": m, "by_engine": {m[L]: c["sides"][L] for L in labels}, "ranking": [m[L] for L in c["ranking"]],
            "best": m.get(c["best"], "equal"), "reason": c["reason"], "version": DUEL_VERSION}


def already(con, doc: str, sref: str, judge: str, row_ids: dict) -> bool:
    want = json.dumps(row_ids, sort_keys=True)
    for (r,) in con.execute("SELECT row_ids FROM scholar_duels WHERE doc_code = ? AND span_ref = ? AND judge_engine = ? "
                            "AND prompt_version = ?", (doc, sref, judge, DUEL_VERSION)):
        try:
            if json.dumps(json.loads(r), sort_keys=True) == want:
                return True
        except (TypeError, ValueError):
            continue
    return False


def store(con, doc: str, sref: str, pids: list, judge: str, engines: list, row_ids: dict, verdict: dict, best: str,
          cost: float) -> None:
    con.execute("INSERT INTO scholar_duels(doc_code, span_ref, passage_ids, judge_engine, prompt_version, engines, row_ids, "
                "verdict, best, cost_usd, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (doc, sref, json.dumps(pids), judge, DUEL_VERSION, json.dumps(engines), json.dumps(row_ids, sort_keys=True),
                 json.dumps(verdict, ensure_ascii=False), best, round(float(cost or 0.0), 6), ST.now()))
    con.commit()


def make_judge(engine: str, a, meta: dict):
    """A judge's asker: ST.Claude or ST.Gemini, recording its calls as kind "judge". Raises RuntimeError without a key."""
    ga = argparse.Namespace(**vars(a))
    ga.engine, ga.judge_engine, ga.compare_engine = engine, ST.JUDGE, ST.COMPARE_ENGINE
    j = (ST.Claude if engine.startswith("anthropic:") else ST.Gemini)(ga, meta, None)
    j.meter_kind = "judge"
    return j


# --------------------------------------------------------------------------------------------- the person
def canonical(con, doc: str) -> dict:
    """{span_ref: the judges' latest row with the most engines} (the rows the page shows)."""
    out = {}
    if not ST.has_table(con, "scholar_duels"):
        return out
    cur = con.execute("SELECT * FROM scholar_duels WHERE doc_code = ? AND judge_engine NOT LIKE ? ORDER BY id",
                      (doc, PERSON + "%"))
    names = [d[0] for d in cur.description]
    for r in cur.fetchall():
        r = dict(zip(names, r))
        n = len(ST._loads(r.get("row_ids"), {}))
        old = out.get(r["span_ref"])
        if old is None or n >= len(ST._loads(old.get("row_ids"), {})):
            out[r["span_ref"]] = r
    return out


def person_order(doc: str, sref: str, row_ids: dict) -> list:
    return order_for(row_ids, "%s|%s|person" % (doc, sref))


def pick(con, a) -> int:
    canon = canonical(con, a.doc)
    n = 0
    for part in [p.strip() for p in a.pick.split(",") if p.strip()]:
        sref, _, num = part.rpartition("=")
        c = canon.get(sref.strip())
        if not c:
            print("  %s: no span read by the judges (python scripts\\scholar_duel.py --doc %s --report lists them)"
                  % (sref, a.doc)); continue
        rid = ST._loads(c.get("row_ids"), {})
        order = person_order(a.doc, c["span_ref"], rid)
        try:
            k = int(num)
        except ValueError:
            k = 0
        best = order[k - 1] if 1 <= k <= len(order) else ("equal" if num.strip().lower() == "equal" else None)
        if best is None:
            print("  %s: %r is not a translation's number (1 to %d, or equal)" % (sref, num, len(order))); continue
        store(con, a.doc, c["span_ref"], ST._loads(c.get("passage_ids"), []), PERSON + a.by, order, rid,
              {"best": best, "by": a.by, "number": num.strip()}, best, 0.0)
        n += 1
        print("  %s: Translation %s, the pick of %s" % (c["span_ref"], num.strip(), a.by))
    return n


# --------------------------------------------------------------------------------------------- the page
_CSS = ST._CSS + """
.duo{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:12px}
.tr{background:var(--card2);border:1px solid var(--border);border-radius:9px;padding:12px 14px}
.tr h3{font-size:12px;color:var(--gold);font-family:'Inter',sans-serif;margin-bottom:6px;letter-spacing:.04em}
.best{color:var(--ok);font-weight:700}
.tally td,.tally th{font-size:12px}
"""


def _page(title: str, body: str) -> str:
    e = html.escape
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"/>'
            '<meta name="viewport" content="width=device-width,initial-scale=1"/><title>%s</title>'
            '<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital@0;1&family=Inter:wght@400;600;700&'
            'family=Noto+Serif+Devanagari&display=swap" rel="stylesheet"/><style>%s</style></head><body>'
            '<header><h1>%s</h1></header><main class="sch">%s</main></body></html>' % (e(title), _CSS, e(title), body))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def _f(x, fmt="%.2f"):
    return (fmt % x) if x is not None else "-"


def render(con, doc: str, named: bool = False) -> str:
    e = html.escape
    allp = ST.load_text(con, doc)
    pos = {x["id"]: i for i, x in enumerate(allp)}
    byid = {x["id"]: x for x in allp}
    canon = canonical(con, doc)
    if not canon:
        return _page("Head to head: " + doc, '<p class="intro">No span of <b>%s</b> read by the judges yet: '
                     '<code>python scripts\\scholar_duel.py --doc %s --pages 1 --limit 12</code> (the dry run).</p>'
                     % (e(doc), e(doc)))
    cur = con.execute("SELECT * FROM scholar_duels WHERE doc_code = ? ORDER BY id", (doc,))
    names = [d[0] for d in cur.description]
    alld = [dict(zip(names, r)) for r in cur.fetchall()]
    rows_by_id = {}
    ids = sorted({i for c in canon.values() for v in ST._loads(c.get("row_ids"), {}).values() for i in v})
    for k in range(0, len(ids), 500):
        q = con.execute("SELECT * FROM scholar_translations WHERE id IN (%s)" % ",".join("?" * len(ids[k:k + 500])),
                        ids[k:k + 500])
        nm = [d[0] for d in q.description]
        for r in q.fetchall():
            r = dict(zip(nm, r))
            rows_by_id[r["id"]] = r
    spans = sorted(canon.values(), key=lambda c: pos.get((ST._loads(c.get("passage_ids"), [None]) or [None])[0], 1 << 30))
    tally = {}
    agree = [0, 0]
    arts = ""
    for c in spans:
        sref = c["span_ref"]
        rid = ST._loads(c.get("row_ids"), {})
        want = json.dumps(rid, sort_keys=True)
        verdicts, persons = {}, {}
        for d in alld:
            if d["span_ref"] != sref or json.dumps(ST._loads(d.get("row_ids"), {}), sort_keys=True) != want:
                continue
            (persons if d["judge_engine"].startswith(PERSON) else verdicts)[d["judge_engine"]] = d
        order = person_order(doc, sref, rid)
        pids = ST._loads(c.get("passage_ids"), [])
        left = "".join('<div class="gv"><span class="vref">%s</span><div class="sa">%s</div><div class="ia">%s</div></div>'
                       % (e(ST.ref_of(byid[p])), e((byid[p].get("text") or "").strip()), e((byid[p].get("iast") or "").strip()))
                       for p in pids if p in byid)
        cols = ""
        facts = ""
        for k, eng in enumerate(order, 1):
            rs = sorted((rows_by_id[i] for i in rid.get(eng, []) if i in rows_by_id), key=lambda r: pos.get(r["passage_id"], 0))
            if not rs:
                continue
            us, seen = [], set()
            for r in rs:
                key = (r.get("group_ref"), r.get("created_at")) if r.get("group_ref") else ("#%d" % r["id"], None)
                if key not in seen:
                    seen.add(key)
                    us.append({"rows": [x for x in rs if ((x.get("group_ref"), x.get("created_at")) if x.get("group_ref")
                                                          else ("#%d" % x["id"], None)) == key]})
            text = " ".join(unit_text(u) for u in us)
            notes = [n for u in us for n in ST._loads(u["rows"][0].get("notes"), [])]
            doubts = "; ".join(u["rows"][0]["doubts"] for u in us if u["rows"][0].get("doubts"))
            head = ("Translation %d" % k) + ((" &middot; %s" % e(eng)) if named else "")
            notes_html = ("<ol class=\"notes\">%s</ol>" % "".join(
                '<li><span class="k">%s</span> <b>%s</b>: %s</li>' % (e(n.get("kind") or ""), e(n.get("anchor") or ""),
                                                                       e(n.get("note") or "")) for n in notes)) if notes else ""
            cols += ('<div class="tr"><h3>%s</h3><div class="en">%s</div>%s%s</div>'
                     % (head, ST._english_html(text, notes), notes_html,
                        ('<div class="doubt">Doubts: %s</div>' % e(doubts)) if doubts else ""))
            t = tally.setdefault(eng, {"spans": 0, "verses": 0, "cost": 0.0, "status": {}, "jf": [], "judges": {},
                                       "person": 0})
            t["spans"] += 1
            t["verses"] += len(rs)
            t["cost"] += sum(r.get("cost_usd") or 0.0 for r in rs)
            for r in rs:
                t["status"][r.get("status") or "?"] = t["status"].get(r.get("status") or "?", 0) + 1
                t["jf"].append(r.get("fidelity"))
            jl = []
            for jn, d in sorted(verdicts.items()):
                v = ST._loads(d.get("verdict"), {})
                s = (v.get("by_engine") or {}).get(eng) or {}
                rank = (v.get("ranking") or []).index(eng) + 1 if eng in (v.get("ranking") or []) else None
                errs = "".join('<li class="%s">%s, at %s: %s</li>' % (e(x.get("severity", ""), quote=True),
                                                                      e(x.get("severity", "")), e(x.get("where", "")),
                                                                      e(x.get("error", ""))) for x in s.get("errors") or [])
                jl.append('<div>%s%s: fidelity %s, prose %s, notes %s; rank %s%s</div>'
                          % ('<span class="best">best</span> ' if v.get("best") == eng else "", e(jn),
                             s.get("fidelity"), s.get("prose"), s.get("notes"), rank or "-",
                             ('<ul class="iss">%s</ul>' % errs) if errs else ""))
                tj = t["judges"].setdefault(jn, {"best": 0, "rank": [], "fid": [], "prose": [], "notes": [], "major": 0})
                tj["best"] += 1 if v.get("best") == eng else 0
                tj["rank"].append(rank)
                tj["fid"].append(s.get("fidelity")); tj["prose"].append(s.get("prose")); tj["notes"].append(s.get("notes"))
                tj["major"] += sum(1 for x in s.get("errors") or [] if x.get("severity") == "major")
            for pn, d in persons.items():
                if d.get("best") == eng:
                    t["person"] += 1
                    jl.append('<div><span class="best">picked</span> by %s</div>' % e(pn[len(PERSON):]))
            st_ = ", ".join("%s %d" % (k_, n_) for k_, n_ in sorted(Counter_(r.get("status") for r in rs).items()))
            facts += ('<div class="tr"><h3>Translation %d</h3>%s<div>the critic and judge-v1: %s; judge-v1 fidelity %s; '
                      '%s pass(es); %s</div></div>'
                      % (k, "".join(jl), e(st_), _f(_mean([r.get("fidelity") for r in rs]), "%.1f"),
                         max(r.get("passes") or 1 for r in rs), ST.usd(sum(r.get("cost_usd") or 0 for r in rs))))
        bests = [ST._loads(d.get("verdict"), {}).get("best") for d in verdicts.values()]
        if len(bests) >= 2:
            agree[1] += 1
            agree[0] += 1 if len(set(bests)) == 1 else 0
        who = "".join("<li>Translation %d: %s</li>" % (k, e(eng)) for k, eng in enumerate(order, 1))
        reasons = "".join("<div>%s: %s</div>" % (e(jn), e(ST._loads(d.get("verdict"), {}).get("reason") or ""))
                          for jn, d in sorted(verdicts.items()))
        arts += ('<article class="v"><div class="vh"><a class="ref" id="s-%s" href="#s-%s">%s</a><span>%d verse(s)</span>'
                 '<span>pick: <code>--pick %s=N</code></span></div><div>%s</div><div class="duo">%s</div>'
                 '<details><summary>The judges (blind to who made which)</summary><div class="duo">%s</div>%s</details>'
                 '<details><summary>Who made which</summary><ul class="notes">%s</ul></details></article>'
                 % (e(sref, quote=True), e(sref, quote=True), e(sref), len(pids), e(sref), left, cols, facts, reasons, who))
    trs = ""
    judges = sorted({j for t in tally.values() for j in t["judges"]})
    for eng, t in sorted(tally.items()):
        js = "".join('<td class="num">%d</td><td class="num">%s</td><td class="num">%s / %s / %s</td><td class="num">%d</td>'
                     % (t["judges"].get(j, {}).get("best", 0), _f(_mean(t["judges"].get(j, {}).get("rank", []))),
                        _f(_mean(t["judges"].get(j, {}).get("fid", [])), "%.1f"),
                        _f(_mean(t["judges"].get(j, {}).get("prose", [])), "%.1f"),
                        _f(_mean(t["judges"].get(j, {}).get("notes", [])), "%.1f"),
                        t["judges"].get(j, {}).get("major", 0)) for j in judges)
        trs += ('<tr><td>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td>%s<td class="num">%d</td></tr>'
                % (e(eng), t["spans"], t["verses"], e(", ".join("%s %d" % kv for kv in sorted(t["status"].items()))),
                   _f(_mean(t["jf"]), "%.2f"), ST.usd(t["cost"] / max(1, t["verses"])), js, t["person"]))
    jh = "".join("<th>%s: best</th><th>mean rank</th><th>fidelity / prose / notes</th><th>major errors</th>" % e(j)
                 for j in judges)
    tally_html = ('<details><summary>The tally (open it after reading)</summary><div class="wrap"><table class="tally">'
                  '<thead><tr><th>Engine</th><th>Spans</th><th>Verses</th><th>Status</th><th>judge-v1 fidelity</th>'
                  '<th>$ a verse</th>%s<th>Picked by a person</th></tr></thead><tbody>%s</tbody></table></div>'
                  '<p class="intro">The judges agree on the best in %d of %d spans both read.</p></details>'
                  % (jh, trs, agree[0], agree[1]))
    intro = ('<p class="intro">The scholarly Englishes of <b>%s</b> by different engines, side by side and <b>blind</b>: '
             'read each span, choose the translation you would print, and record it: <code>python scripts\\'
             'scholar_duel.py --doc %s --pick SPAN=N --by NAME</code>. The judges are two, one of each family '
             '(Google\'s and Anthropic\'s), each blind to who made which, the order shuffled for each; either may favour '
             'its own. The tool that made this page was written by Claude, one of the contestants: weigh the Gemini '
             'judge at least as much as the Claude one, and your own reading above both.</p>' % (e(doc), e(doc)))
    return _page("Head to head: " + doc, intro + arts + tally_html)


def Counter_(it) -> dict:
    out = {}
    for x in it:
        out[x or "?"] = out.get(x or "?", 0) + 1
    return out


# --------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--from-ref", default=None)
    ap.add_argument("--only-page", type=int, default=None)
    ap.add_argument("--limit", type=int, default=12, help="verses at most")
    ap.add_argument("--engines", default=None, help="the engines compared (default: every engine with rows here)")
    ap.add_argument("--judges", default=",".join(JUDGES))
    ap.add_argument("--max-usd", type=float, default=1.00)
    ap.add_argument("--redo", action="store_true", help="ask a judge again where it has read the same rows")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--report", action="store_true", help="write exports\\scholar_duel_<doc>.html (free)")
    ap.add_argument("--named", action="store_true", help="with --report: the engines named on the page, not blind")
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--pick", default=None, help="the person's choice: SPAN=N[,SPAN=N] (N: the page's Translation N)")
    ap.add_argument("--by", default=None)
    a = ap.parse_args(argv)
    print("scholar_duel.py  %s (%s)  %s" % (MARK, DUEL_VERSION, "RUN" if a.yes else (
        "the page" if a.report else ("the person's pick" if a.pick else "DRY RUN (nothing called, nothing written)"))))
    if not hasattr(ST, "SYSTEMS"):
        print("REFUSE: scholar_translate.py is not patched (python scripts\\patch_claude_engine_2026_10_15.py)")
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    if a.report:
        con = ST.open_ro(a.db)
        try:
            page = render(con, a.doc, a.named)
        finally:
            con.close()
        out = Path(a.exports) / ("scholar_duel_%s.html" % ST._safe(a.doc))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print("VERDICT: written %s (%d bytes)%s" % (out, out.stat().st_size, "" if a.named else ", blind"))
        print("NEXT: start %s" % out)
        return 0
    if a.pick:
        if not a.by:
            print("REFUSE: --pick needs --by (who read them)"); print("VERDICT: nothing written"); print("NEXT: "); return 1
        import db_utils
        con = db_utils.connect(a.db)
        try:
            ensure_schema(con)
            n = pick(con, a)
        finally:
            con.close()
        print("VERDICT: %d pick(s) recorded" % n)
        print("NEXT: python scripts\\scholar_duel.py --doc %s --report" % a.doc)
        return 0

    con = ST.open_ro(a.db)
    try:
        allp = ST.load_text(con, a.doc)
        if not allp:
            print("REFUSE: %s has no passages" % a.doc); print("VERDICT: nothing to do"); print("NEXT: "); return 1
        meta = ST.doc_meta(con, a.doc, allp, Path(a.db).resolve().parent / "raw")
        pos = {x["id"]: i for i, x in enumerate(allp)}
        er = engine_rows(con, a.doc)
        engines = [x.strip() for x in a.engines.split(",") if x.strip()] if a.engines else sorted(er)
        counts = group_counts(con, a.doc)
        ub = {e: units_for(e, er.get(e, {}), counts, pos) for e in engines}
        picked = pick_verses(a, allp, er, engines)
        spans = spans_of(picked, allp, ub, engines)
        judges = [x.strip() for x in a.judges.split(",") if x.strip()]
        work = []
        for lo, hi in spans:
            xs = allp[lo:hi + 1]
            texts = {}
            for e in engines:
                t = engine_text(e, xs, er, ub)
                if t:
                    texts[e] = t
            if len(texts) < 2:
                continue
            sref = span_ref(xs)
            rid = {e: t["row_ids"] for e, t in texts.items()}
            base = judge_base(con, a, allp, lo, hi, meta)
            todo = [j for j in judges if a.redo or not (ST.has_table(con, "scholar_duels") and already(con, a.doc, sref, j, rid))]
            work.append({"lo": lo, "hi": hi, "xs": xs, "sref": sref, "texts": texts, "rid": rid, "base": base, "todo": todo})
        est = {}
        for w in work:
            msg = duel_message(w["base"], [(L, w["texts"][e]["text"], w["texts"][e]["notes"]) for L, e in
                                           zip(LABELS, sorted(w["texts"]))])
            for j in w["todo"]:
                est[j] = est.get(j, 0.0) + ST.call_price(len(SYSTEM_DUEL) + len(msg), j)
        credit = None
        if any(j.startswith("anthropic:") for j in judges):
            import claude_engine
            try:
                credit = claude_engine.credit(con)
            except RuntimeError as e:
                credit = {"error": str(e)}
    finally:
        con.close()
    have = {e: sum(1 for i in picked if ST.current(er.get(e, {}).get(allp[i]["id"]), allp[i])) for e in engines}
    print("  %s: %s" % (a.doc, ", ".join("%s %d" % kv for kv in sorted(have.items())) or "no scholarly English"))
    print("  verses with two engines or more: %d; spans: %d (%s)" % (len(picked), len(work),
                                                                     ", ".join(w["sref"] for w in work[:12])
                                                                     + (" ..." if len(work) > 12 else "")))
    print("  the judges: %s   (%s)" % (", ".join("%s (%s)" % (j, "the Claude credit" if j.startswith("anthropic:")
                                                               else "Google: the spend cap") for j in judges), DUEL_VERSION))
    n_calls = sum(len(w["todo"]) for w in work)
    skipped = sum(len(judges) - len(w["todo"]) for w in work)
    if skipped:
        print("  already read on the same rows: %d (--redo asks again)" % skipped)
    total = sum(est.values())
    print("  cost: about %s for %d call(s) (%s)" % (ST.usd(total), n_calls, ", ".join("%s %s" % (j, ST.usd(v))
                                                                                     for j, v in sorted(est.items()))))
    if credit is not None:
        import claude_engine
        print("  " + (claude_engine.credit_line(credit) if "error" not in credit else "the Claude credit: " + credit["error"]))
    if not n_calls:
        print("VERDICT: nothing to ask")
        print("NEXT: python scripts\\scholar_duel.py --doc %s --report" % a.doc)
        return 0
    if not a.yes:
        cap = max(0.25, round(total * 1.3 + 0.005, 2))
        sel = (" --pages %s" % a.pages if a.pages else "") + (" --from-ref %s" % a.from_ref if a.from_ref else "") + (
            " --only-page %d" % a.only_page if a.only_page is not None else "")
        print("VERDICT: %d span(s) to read, about %s" % (len(work), ST.usd(total)))
        print("NEXT: python scripts\\scholar_duel.py --doc %s%s --limit %d%s%s%s --yes --max-usd %.2f"
              % (a.doc, sel, a.limit, (" --engines %s" % a.engines) if a.engines else "",
                 (" --judges %s" % a.judges) if a.judges != ",".join(JUDGES) else "", " --redo" if a.redo else "", cap))
        return 0
    try:
        askers = {j: make_judge(j, a, meta) for j in judges}
    except (RuntimeError, ValueError) as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing called, nothing written"); print("NEXT: "); return 1
    import db_utils
    con = db_utils.connect(a.db)
    stopped, done_n, failed = "", 0, 0
    fails = {j: 0 for j in judges}
    try:
        for j in askers.values():
            j.con = con
        ensure_schema(con)
        try:
            from usage_meter import budget_ok as google_ok
        except Exception:
            google_ok = None
        import claude_engine
        for w in work:
            for jn in list(w["todo"]):
                if jn not in askers:
                    continue
                spent = sum(x.spent for x in askers.values())
                need = ST.call_price(len(SYSTEM_DUEL) + len(w["base"]) + sum(len(t["text"]) for t in w["texts"].values()), jn)
                if spent + need > a.max_usd:
                    stopped = "this run's --max-usd $%.2f is reached (%s spent)" % (a.max_usd, ST.usd(spent))
                    break
                if jn.startswith("anthropic:") and not claude_engine.budget_ok(con, need):
                    askers.pop(jn); print("  %s: stopped (the Claude credit)" % jn); continue
                if not jn.startswith("anthropic:") and google_ok is not None and not google_ok(con, need):
                    askers.pop(jn); print("  %s: stopped (the spend cap)" % jn); continue
                asker = askers[jn]
                s0 = asker.spent
                try:
                    v = duel_one(asker, jn, w["base"], w["texts"], "%s|%s" % (a.doc, w["sref"]))
                except ST.CallFailed as e:
                    v = None
                    print("  %s  %s: failed (%s)" % (w["sref"], jn, e))
                cost = asker.spent - s0
                if v is None:
                    failed += 1
                    fails[jn] += 1
                    if fails[jn] >= 3:
                        askers.pop(jn, None); print("  %s: three spans running failed: stopped" % jn)
                    continue
                fails[jn] = 0
                store(con, a.doc, w["sref"], [x["id"] for x in w["xs"]], jn, list(v["labels"].values()), w["rid"], v,
                      v["best"], cost)
                done_n += 1
                print("  %-16s %-26s best: %-30s %s" % (w["sref"], jn, v["best"], ST.usd(cost)))
            if stopped or not askers:
                break
        try:
            cl = claude_engine.credit_line(claude_engine.credit(con)) if any(j.startswith("anthropic:") for j in judges) else ""
        except Exception:
            cl = ""
    finally:
        con.close()
    if stopped:
        print("  STOPPED: %s" % stopped)
    if cl:
        print("  " + cl)
    print("VERDICT: %d reading(s) stored, %d failed" % (done_n, failed))
    print("NEXT: python scripts\\scholar_duel.py --doc %s --report   (then: start exports\\scholar_duel_%s.html)"
          % (a.doc, ST._safe(a.doc)))
    return 0


if __name__ == "__main__":
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
