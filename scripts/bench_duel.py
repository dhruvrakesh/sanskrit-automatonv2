#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
bench_duel.py  (2026-10-16)  BENCH_DUEL_2026_10_16  (BM3)

BM3: the blind side-by-side of BM1's English. BM1 (scripts/bench_mitra.py) scored each arm alone: chrF against the
published English, and judge-v1 (gemini-2.5-flash) on the Sanskrit. Its judge gave every arm 4.7 to 4.9 of 5 and
passed 92 to 95% of their sentences, so it barely tells them apart; it is gemini-2.5-flash judging gemini-2.5-flash's
English among others; and the scholarly arm was revised against that same judge. BM3 asks the question differently:
the arms' English of the same sentence side by side, read by judges of both families, who rank them.

What is read: BM1's units (a sentence the scholarly arm translated whole over several verses is one unit, for every
arm), each with the three arms' English (flash, sonnet1, scholar) and, with --with-reference, the published English
as a fourth: a private evaluation, so it is sent to both judges (Google's and Anthropic's API), never published.

How (scholar_duel.py's duel-v1, unchanged: the same system prompt, the same judges, gemini-2.5-pro and
claude-opus-5-5, one of each family, as either may favour its own): who made each translation is not said; the order
is shuffled for each unit and each judge; the verse is given with its context (the Sanskrit before and after: no
arm's English); the glossary the scholarly runs grew is not shown (it would carry one arm's spellings); the scholarly
arm's notes are shown as its notes, the others have none. Each judge gives every translation fidelity, prose and notes
(1 to 5) and its errors (major or minor), then a ranking and the best.

The order of reading: fixed (seed BM3-2026-10-16), the eight texts in turn, each text's units shuffled; so a run
stopped at any point (--units N, --max-usd) has read a balanced random part, and a later run goes on from there. A unit
a judge has read on the same English is not asked again.

What is reported (BM3_report.html, private; BM3_summary.json, numbers only), for all eight texts, without the
Bhagavata, and text by text:
  - per judge, for each pair of arms: how often the first is ranked above the second (a tie counts a half), weighted
    by verses, with a 95% bootstrap interval; each arm's fidelity, prose and notes, its major and minor errors per ten
    verses, how often it is ranked first; whether the first translation shown wins more often than chance (the order);
  - both judges together: how often they order a pair alike, the pair's share where they agree (a tie where not), and
    how often they split by family (each ranking its own family's English above the other's).

Its files: D:\\Sanksrit Automatons\\benchmarks\\bm3 (outside every repository): duel.jsonl (append-only),
spend.jsonl, db\\D.db (its ledger, a copy of the real one's credit rows and spend cap), logs\\. BM1's folder is read
only. Its calls: data/context.db's usage_log as kind bench_duel, doc BM3:<text>; the Gemini part in the spend cap,
the Claude part in the Claude credit; both checked before each call, settled every 10 calls and at the end.

  python scripts\\bench_duel.py                                                   the state and the price (free)
  python scripts\\bench_duel.py --units 40 --with-reference                       the dry run of 40 units (free)
  python scripts\\bench_duel.py --units 40 --with-reference --yes --max-usd 6.00
  python scripts\\bench_duel.py --report                                          BM3_report.html (free)
  python scripts\\bench_duel.py --settle                                          what a stopped run left (free)
  python scripts\\bench_duel.py --units 40 --with-reference --no-notes --yes --max-usd 4.50
      BENCH_DUEL_NOTES_2026_10_16: the check of the pilot, the scholarly arm's notes withheld (only it has notes, so
      they name it, and a judge may rank an annotated translation higher for its notes); its own report,
      BM3_nonotes_report.html and BM3_nonotes_summary.json (python scripts\\bench_duel.py --report --no-notes).
"""
from __future__ import annotations

import argparse
import contextlib
import html
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import bench_mitra as bm     # noqa: E402  (BM1's sample, units, English, ledger)
import scholar_duel as SD    # noqa: E402  (duel-v1: its prompt is registered on import; nothing is called)

ST = bm.ST
MARK = "BENCH_DUEL_2026_10_16"
BENCH = "BM3"
SEED = "BM3-2026-10-16"
OUT_DEFAULT = ROOT.parent / "benchmarks" / "bm3"
BM1_DEFAULT = bm.OUT_DEFAULT
DUEL_DB = "D.db"
KIND = "duel"                  # usage_log: bench_duel
DOC_PREFIX = BENCH + ":"
SETTLE_EVERY = 10
BOOT = 1000
CORE_OUT = bm.NOT_CORE
FAMILY = {"flash": "gemini", "sonnet1": "anthropic", "scholar": "anthropic", "reference": None}
PAIRS = (("scholar", "flash"), ("scholar", "sonnet1"), ("sonnet1", "flash"),
         ("scholar", "reference"), ("sonnet1", "reference"), ("flash", "reference"))
PRIOR_CALL = {"gemini:gemini-2.5-pro": 0.065, "anthropic:claude-opus-5-5": 0.047}   # $ a duel call, 15 Oct (Hayasirsa)
SOURCE = "a digital e-text"
NOTES_SHOWN = True   # BENCH_DUEL_NOTES_2026_10_16: --no-notes withholds the scholarly arm's notes (a check)
NAME = "BM3"         # the report's files: BM3_report.html, BM3_summary.json (BM3_nonotes_* with --no-notes)
ME = "python scripts\\bench_duel.py"


def family(engine: str) -> str:
    return "anthropic" if str(engine or "").startswith("anthropic:") else "gemini"


def usd(x) -> str:
    return bm.usd(x)


# --------------------------------------------------------------------------------------------- what is read
def contestants(with_ref: bool) -> list:
    return list(bm.ARMS) + (["reference"] if with_ref else [])


def load(bm1: Path, specs=None):
    """(sample, items): BM1's sample and, per text, its units and every arm's English (bench_mitra.gather)."""
    sample = bm.load_sample(bm1)
    if not sample:
        return None, []
    return sample, bm.gather(bm1, sample, list(specs or bm.FILES))


def order_of(items: list) -> list:
    """[(text index, unit index)]: the texts in a fixed shuffled turn, each text's units shuffled; any prefix is a
    balanced random part."""
    per = []
    for it in items:
        us = list(range(len(it["units"])))
        random.Random(SEED + ":" + it["f"]["key"]).shuffle(us)
        per.append(us)
    turn = list(range(len(items)))
    random.Random(SEED + ":texts").shuffle(turn)
    out = []
    for r in range(max([len(p) for p in per] or [0])):
        for ti in turn:
            if r < len(per[ti]):
                out.append((ti, per[ti][r]))
    return out


def texts_of(it: dict, m: list, with_ref: bool):
    """{arm: {"text", "notes"}} of a unit, or None when an arm has no English for it."""
    got = {}
    for arm in contestants(with_ref):
        t = bm.unit_text(arm, m, it["outs"].get(arm, {}), it["refs"])
        if not t:
            return None
        notes = []
        if arm == "scholar" and NOTES_SHOWN:   # BENCH_DUEL_NOTES_2026_10_16: --no-notes withholds them
            notes = ST._loads((it["outs"]["scholar"].get(m[0]) or {}).get("notes"), [])
        got[arm] = {"text": t, "notes": notes}
    return got


def shas(texts: dict) -> dict:
    return {a: bm.sha(t["text"] + "\n" + json.dumps(t["notes"], ensure_ascii=False, sort_keys=True))
            for a, t in texts.items()}


def readings(out: Path) -> list:
    p = out / "duel.jsonl"
    got = []
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("ranking") and r.get("by_arm"):
                    got.append(r)
    return got


def index_of(rs: list) -> dict:
    """{(key, unit, judge, shas as JSON): the latest reading}."""
    ix = {}
    for r in rs:
        ix[(r["key"], r["unit"], r["judge"], json.dumps(r.get("shas") or {}, sort_keys=True))] = r
    return ix


class Bases:
    """The judges' message without the translations, from the scholarly arm's bench database (its passages: the
    Sanskrit of the window and of its context; no English), as scholar_duel.judge_base makes it."""

    def __init__(self, bm1: Path):
        self.path = bm1 / "db" / bm.ARM["scholar"]["db"]
        self.cache = {}

    def get(self, it: dict, m: list) -> str:
        f = it["f"]
        if f["code"] not in self.cache:
            con = bm.open_ro(self.path)
            try:
                allp = ST.load_text(con, f["code"])
                meta = ST.doc_meta(con, f["code"], allp, None)
                meta.update(title=f["title"], source=SOURCE, doc=f["code"])
                pos = {x["idx"]: i for i, x in enumerate(allp) if x["page"] == 2}
            finally:
                con.close()
            self.cache[f["code"]] = (allp, meta, pos)
        allp, meta, pos = self.cache[f["code"]]
        con = bm.open_ro(self.path)
        try:
            return SD.judge_base(con, argparse.Namespace(doc=f["code"]), allp, pos[m[0]], pos[m[-1]], meta)
        finally:
            con.close()

    def meta(self, it: dict) -> dict:
        return dict(self.cache[it["f"]["code"]][1])


def work_of(items: list, ix: dict, judges: list, with_ref: bool, units=None) -> tuple:
    """(the units of this run in the order of reading, the (unit, judge) readings still to make)."""
    order = order_of(items)
    if units is not None:
        order = order[:max(0, int(units))]
    todo, chosen = [], []
    for ti, ui in order:
        it = items[ti]
        m = it["units"][ui]
        t = texts_of(it, m, with_ref)
        if t is None:
            continue
        sh = shas(t)
        chosen.append((ti, ui))
        for j in judges:
            if (it["f"]["key"], bm.unit_name(m), j, json.dumps(sh, sort_keys=True)) not in ix:
                todo.append({"ti": ti, "ui": ui, "it": it, "m": m, "texts": t, "shas": sh, "judge": j})
    return chosen, todo


# --------------------------------------------------------------------------------------------- the price and the caps
def price(mcon, judge: str) -> tuple:
    """($ a call, how): BM3's own calls once there are 10; before, scholar_duel's duel calls of that judge since 15 Oct
    (longer passages: an upper estimate); else the prior of 15 Oct."""
    try:
        n, avg = mcon.execute("SELECT COUNT(*), AVG(cost_usd) FROM usage_log WHERE kind = ? AND engine = ? AND "
                              "cost_usd > 0", (bm.KIND_PREFIX + KIND, judge)).fetchone()
        if n and n >= 10:
            return float(avg), "measured on BM3's own %d calls" % n
        n, avg = mcon.execute("SELECT COUNT(*), AVG(cost_usd) FROM usage_log WHERE kind = 'judge' AND engine = ? AND "
                              "cost_usd > 0 AND ts >= ?", (judge, ST.METERED_SINCE)).fetchone()
        if n and n >= 3:
            return float(avg), "scholar_duel's %d calls of 15 Oct (longer passages: an upper estimate)" % n
    except Exception:
        pass
    if judge in PRIOR_CALL:
        return PRIOR_CALL[judge], "the price of 15 Oct"
    return ST.call_price(6000, judge), "the pricing table (a guess)"


def estimate(mcon, todo: list, judges: list) -> dict:
    """{judge: {"calls", "usd", "each", "how", "bill"}}."""
    est = {}
    for j in judges:
        each, how = price(mcon, j)
        n = sum(1 for t in todo if t["judge"] == j)
        est[j] = {"calls": n, "usd": round(n * each, 4), "each": round(each, 4), "how": how,
                  "bill": "the Claude credit" if family(j) == "anthropic" else "the spend cap (Google)"}
    return est


@contextlib.contextmanager
def _as_bm3():
    """bench_mitra.push writes doc BM1:<text>; BM3's calls are BM3:<text>."""
    old = bm.DOC_PREFIX
    bm.DOC_PREFIX = DOC_PREFIX
    try:
        yield
    finally:
        bm.DOC_PREFIX = old


def sync(dpath: Path, mcon, out: Path) -> dict:
    with _as_bm3():
        return bm.sync(dpath, mcon, KIND, out / "spend.jsonl")


def spend(out: Path) -> dict:
    v = bm.spend(out).get(KIND) or {"claude": 0.0, "google": 0.0}
    return {"claude": round(v["claude"], 4), "google": round(v["google"], 4)}


def make_judge(engine: str, out: Path, meta: dict):
    """A judge's asker (scholar_duel.make_judge), its calls metered as kind duel. Raises RuntimeError without a key."""
    a = argparse.Namespace(engine=engine, judge_engine=ST.JUDGE, compare_engine=ST.COMPARE_ENGINE,
                           log_dir=str(out / "logs"))
    j = SD.make_judge(engine, a, meta)
    j.meter_kind = KIND
    return j


# --------------------------------------------------------------------------------------------- the run
def run(a, out: Path, bm1: Path, items: list, judges: list) -> int:
    rs = readings(out)
    chosen, todo = work_of(items, index_of(rs), judges, a.with_reference, a.units)
    mcon = bm.main_ledger(a.db)
    try:
        est = estimate(mcon, todo, judges)
        cp = bm.caps(mcon)
    finally:
        mcon.close()
    total = sum(v["usd"] for v in est.values())
    claude = sum(v["usd"] for j, v in est.items() if family(j) == "anthropic")
    google = total - claude
    cap = a.max_usd if a.max_usd is not None else max(0.25, round(total * 1.3 + 0.05, 2))
    print("bench_duel.py  %s  %s  %s  (%s, %s)" % (MARK, BENCH, "RUN" if a.yes else "DRY RUN (nothing called, nothing "
                                                   "written)", SD.DUEL_VERSION, ", ".join(contestants(a.with_reference))))
    print("  units: %d of %d in the order of reading%s; readings to make: %d (%s)"
          % (len(chosen), len(order_of(items)), (" (--units %d)" % a.units) if a.units is not None else "", len(todo),
             ", ".join("%s %d" % (j, v["calls"]) for j, v in est.items())))
    for j, v in est.items():
        print("  %-28s about %s (%s a call, %s; %s)" % (j, usd(v["usd"]), usd(v["each"]), v["how"], v["bill"]))
    print("  the Claude credit: %s left; the spend cap: %s left of %s%s; --max-usd %s"
          % (usd(cp["credit_left"]), usd(cp["cap_left"]), usd(cp["cap"]), ", paused" if cp["paused"] else "", usd(cap)))
    if not NOTES_SHOWN:   # BENCH_DUEL_NOTES_2026_10_16
        print("  the scholarly arm's notes are withheld (the check: only it has notes, so they name it)")
    if a.with_reference:
        print("  the published English is the fourth translation: it is sent to both judges (a private evaluation)")
    if not todo:
        print("VERDICT: nothing to read")
        print("NEXT: " + ME + " --report"); return 0
    if not a.yes:
        print("VERDICT: %d reading(s) to make, about %s (Claude %s, Google %s)" % (len(todo), usd(total), usd(claude),
                                                                                usd(google)))
        print("NEXT: " + ME + "%s%s --yes --max-usd %.2f" % ((" --units %d" % a.units) if a.units is not None else "",
                                                             " --with-reference" if a.with_reference else "", cap))
        return 0
    if claude > cp["credit_left"] or cp["credit_expired"]:
        print("REFUSE: the Claude credit has %s left: this run's Claude part is about %s (fewer --units)"
              % (usd(cp["credit_left"]), usd(claude)))
        print("VERDICT: nothing sent"); print("NEXT: " + ME + " --units 20"); return 1
    if google > 0 and (cp["paused"] or google > cp["cap_left"]):
        print("REFUSE: the spend cap has %s left: this run's Google part is about %s (fewer --units, or "
              "python scripts\\set_budget.py)" % (usd(cp["cap_left"]), usd(google)))
        print("VERDICT: nothing sent"); print("NEXT: python scripts\\set_budget.py"); return 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    dpath = out / "db" / DUEL_DB
    dpath.parent.mkdir(parents=True, exist_ok=True)
    dcon = bm.connect(dpath)
    bm.ledger_schema(dcon)
    dcon.close()
    bases = Bases(bm1)
    mcon = bm.main_ledger(a.db)
    stopped, done_n, failed, calls = "", 0, 0, 0
    spent = 0.0
    askers, fails = {}, {j: 0 for j in judges}
    try:
        sync(dpath, mcon, out)
        dcon = bm.connect(dpath)
        try:
            from usage_meter import budget_ok as google_ok
        except Exception:
            google_ok = None
        import claude_engine
        try:
            for t in todo:
                j = t["judge"]
                if j in fails and fails[j] < 0:
                    continue
                base = bases.get(t["it"], t["m"])
                ak = (j, t["it"]["f"]["code"])   # one asker a judge and a text: its system prompt names the text
                if ak not in askers:
                    try:
                        askers[ak] = make_judge(j, out, bases.meta(t["it"]))
                    except (RuntimeError, ValueError) as e:
                        print("REFUSE: %s: %s" % (j, e)); fails[j] = -1; continue
                    askers[ak].con = dcon
                asker = askers[ak]
                each = est[j]["each"]
                if spent + each > cap:
                    stopped = "--max-usd %s is reached (%s spent)" % (usd(cap), usd(spent)); break
                if family(j) == "anthropic" and not claude_engine.budget_ok(dcon, each):
                    print("  %s: stopped (the Claude credit)" % j); fails[j] = -1; continue
                if family(j) == "gemini" and google_ok is not None and not google_ok(dcon, each):
                    print("  %s: stopped (the spend cap)" % j); fails[j] = -1; continue
                s0 = asker.spent
                try:
                    v = SD.duel_one(asker, j, base, t["texts"], "%s|%s|%s" % (SEED, t["it"]["f"]["key"],
                                                                             bm.unit_name(t["m"])))
                except ST.CallFailed as e:
                    v = None
                    print("  %s %s  %s: failed (%s)" % (t["it"]["f"]["key"], bm.unit_name(t["m"]), j, e))
                cost = asker.spent - s0
                spent += cost
                calls += 1
                if v is None:
                    failed += 1
                    fails[j] += 1
                    if fails[j] >= 3:
                        print("  %s: three readings running failed: stopped" % j); fails[j] = -1
                else:
                    fails[j] = 0
                    rec = {"key": t["it"]["f"]["key"], "unit": bm.unit_name(t["m"]), "n": len(t["m"]), "judge": j,
                           "version": SD.DUEL_VERSION, "notes_shown": NOTES_SHOWN,   # BENCH_DUEL_NOTES_2026_10_16
                           "contestants": sorted(t["texts"]), "shas": t["shas"],
                           "labels": v["labels"], "by_arm": v["by_engine"], "ranking": v["ranking"], "best": v["best"],
                           "reason": v["reason"], "cost": round(cost, 6), "at": bm.now(), "mark": MARK}
                    with open(out / "duel.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    done_n += 1
                    print("  %-11s %-10s %-28s best: %-9s %s" % (t["it"]["f"]["key"], bm.unit_name(t["m"]), j, v["best"],
                                                                 usd(cost)))
                if calls % SETTLE_EVERY == 0:
                    dcon.close()
                    sync(dpath, mcon, out)
                    dcon = bm.connect(dpath)
                    for x in askers.values():
                        x.con = dcon
                if all(v_ < 0 for v_ in fails.values()):
                    stopped = "no judge can go on"; break
        except KeyboardInterrupt:
            stopped = "stopped by hand (what was spent is settled)"
        finally:
            dcon.close()
            res = sync(dpath, mcon, out)
    finally:
        mcon.close()
    if stopped:
        print("  STOPPED: " + stopped)
    left = len(work_of(items, index_of(readings(out)), judges, a.with_reference, a.units)[1])
    print("VERDICT: %d reading(s) stored, %d failed, %s spent (settled as kind bench_duel, doc BM3:*); %d still to read"
          % (done_n, failed, usd(spent), left))
    print("NEXT: " + ME + " --report")
    return 0 if not stopped or stopped.startswith("--max-usd") else 3


def settle(out: Path, mdb: str) -> int:
    dpath = out / "db" / DUEL_DB
    res = {"rows": 0, "claude": 0.0, "google": 0.0}
    if dpath.exists():
        mcon = bm.main_ledger(mdb)
        try:
            res = sync(dpath, mcon, out)
        finally:
            mcon.close()
    print("VERDICT: %d call(s) settled into the ledger, %s (the Claude credit %s, Google %s)"
          % (res["rows"], usd(res["claude"] + res["google"]), usd(res["claude"]), usd(res["google"])))
    print("NEXT: " + ME)
    return 0


# --------------------------------------------------------------------------------------------- the numbers
def outcome(r: dict, x: str, y: str):
    """1 when the judge ranked x above y, 0 below, 0.5 when it called them equal; None when either is missing."""
    rk = r.get("ranking") or []
    if x not in rk or y not in rk:
        return None
    if r.get("best") == "equal":
        return 0.5
    return 1.0 if rk.index(x) < rk.index(y) else 0.0


def _share(rows: list) -> float:
    w = sum(n for _o, n in rows)
    return sum(o * n for o, n in rows) / w if w else 0.0


def judge_numbers(units: list, judge: str, rng) -> dict:
    """units: [{"key", "unit", "n", "r": {judge: reading}}]."""
    us = [u for u in units if judge in u["r"]]
    out = {"units": len(us), "verses": sum(u["n"] for u in us), "pairs": {}, "means": {}}
    if not us:
        return out
    arms = sorted({a for u in us for a in u["r"][judge]["by_arm"]})
    for x, y in PAIRS:
        rows = [(outcome(u["r"][judge], x, y), u["n"]) for u in us]
        rows = [(o, n) for o, n in rows if o is not None]
        if not rows:
            continue
        out["pairs"]["%s>%s" % (x, y)] = {
            "share": round(_share(rows), 3), "ci": bm.boot_ci(len(rows), lambda ix: _share([rows[i] for i in ix]), rng),
            "wins": sum(1 for o, _n in rows if o == 1.0), "ties": sum(1 for o, _n in rows if o == 0.5),
            "losses": sum(1 for o, _n in rows if o == 0.0), "units": len(rows)}
    for a in arms:
        got = [(u["r"][judge]["by_arm"][a], u["n"], u["r"][judge]) for u in us if a in u["r"][judge]["by_arm"]]
        w = sum(n for _s, n, _r in got)
        m = {}
        for k in ("fidelity", "prose", "notes"):
            xs = [(s.get(k), n) for s, n, _r in got if s.get(k) is not None]
            if xs:
                m[k] = round(sum(v * n for v, n in xs) / sum(n for _v, n in xs), 2)
        maj = sum(sum(1 for e in (s.get("errors") or []) if e.get("severity") == "major") for s, _n, _r in got)
        mino = sum(sum(1 for e in (s.get("errors") or []) if e.get("severity") != "major") for s, _n, _r in got)
        m["major_per_10"] = round(10.0 * maj / w, 2) if w else None
        m["minor_per_10"] = round(10.0 * mino / w, 2) if w else None
        m["first"] = round(sum(n for _s, n, r in got if r.get("best") == a) / w, 3) if w else None
        out["means"][a] = m
    shown = [u["r"][judge] for u in us if u["r"][judge].get("labels") and u["r"][judge].get("best") != "equal"]
    if shown:
        firsts = sum(1 for r in shown if r["ranking"][0] == r["labels"].get("A"))
        out["order"] = {"first_shown_ranked_first": round(firsts / len(shown), 3),
                        "chance": round(sum(1.0 / len(r["labels"]) for r in shown) / len(shown), 3)}
    return out


def both_numbers(units: list, judges: list, rng) -> dict:
    """The two judges together, on the units both read: agreement per pair, the pair's share where they agree (a tie
    where not), and the splits by family."""
    if len(judges) < 2:
        return {}
    j1, j2 = judges[0], judges[1]
    us = [u for u in units if j1 in u["r"] and j2 in u["r"]]
    out = {"units": len(us), "judges": [j1, j2], "pairs": {}}
    for x, y in PAIRS:
        rows = []
        for u in us:
            o1, o2 = outcome(u["r"][j1], x, y), outcome(u["r"][j2], x, y)
            if o1 is None or o2 is None:
                continue
            rows.append((o1, o2, u["n"]))
        if not rows:
            continue
        agree = [o1 == o2 for o1, o2, _n in rows]
        cons = [((o1 if o1 == o2 else 0.5), n) for o1, o2, n in rows]
        d = {"units": len(rows), "agree": round(sum(agree) / len(rows), 3), "consensus": round(_share(cons), 3),
             "consensus_ci": bm.boot_ci(len(cons), lambda ix: _share([cons[i] for i in ix]), rng)}
        fx, fy = FAMILY.get(x), FAMILY.get(y)
        f1, f2 = family(j1), family(j2)
        if fx and fy and fx != fy and {fx, fy} == {f1, f2}:
            own = other = 0
            for o1, o2, _n in rows:
                p1 = {1.0: x, 0.0: y}.get(o1)   # whom j1 put above
                p2 = {1.0: x, 0.0: y}.get(o2)
                if p1 and p2 and p1 != p2:
                    if FAMILY[p1] == f1 and FAMILY[p2] == f2:
                        own += 1
                    else:
                        other += 1
            d["split_own_family"], d["split_other_family"] = own, other
        out["pairs"]["%s>%s" % (x, y)] = d
    return out


def gather_units(items: list, rs: list, with_ref) -> list:
    """The units with their current readings: {"key", "unit", "n", "r": {judge: the latest reading on the English
    the unit has now}}; with_ref None takes either set of contestants (the four where there are both)."""
    ix = index_of(rs)
    units = []
    for it in items:
        for m in it["units"]:
            u = {"key": it["f"]["key"], "unit": bm.unit_name(m), "n": len(m), "r": {}, "it": it, "m": m}
            for wr in ([with_ref] if with_ref is not None else [False, True]):
                t = texts_of(it, m, wr)
                if t is None:
                    continue
                sh = json.dumps(shas(t), sort_keys=True)
                for (k, un, j, s), r in ix.items():
                    if k == u["key"] and un == u["unit"] and s == sh:
                        u["r"][j] = r
            if u["r"]:
                units.append(u)
    return units


def report(out: Path, bm1: Path, items: list, judges: list, with_ref) -> tuple:
    rs = readings(out)
    units = gather_units(items, rs, with_ref)
    used = sorted({j for u in units for j in u["r"]}, key=lambda j: (family(j) != "gemini", j)) or list(judges)
    rng = random.Random(SEED + ":boot")
    scopes = [("all", "all eight texts", None), ("core", "without the Bhagavata (%s)" % ", ".join(CORE_OUT), "core")]
    scopes += [(it["f"]["key"], it["f"]["title"], it["f"]["key"]) for it in items]
    nums = {}
    for k, name, sel in scopes:
        us = [u for u in units if sel is None or (sel == "core" and u["key"] not in CORE_OUT) or u["key"] == sel]
        nums[k] = {"name": name, "units": len(us), "verses": sum(u["n"] for u in us),
                   "by_judge": {j: judge_numbers(us, j, rng) for j in used}, "both": both_numbers(us, used, rng)}
    sp = spend(out)
    summary = {"mark": MARK, "bench": BENCH, "made_at": bm.now(), "seed": SEED, "version": SD.DUEL_VERSION,
               "judges": used, "families": {j: family(j) for j in used}, "arm_family": FAMILY,
               "units_total": len(order_of(items)), "with_reference": with_ref, "scopes": nums, "spend": sp,
               "notes_shown": NOTES_SHOWN,   # BENCH_DUEL_NOTES_2026_10_16
               "how": "each judge ranks the translations of a unit, blind, in its own shuffled order; a pair's share is "
                      "how often the first is ranked above the second (a tie a half), weighted by verses; intervals "
                      "by %d bootstrap resamples of the units" % BOOT}
    jp = out / (NAME + "_summary.json")   # BENCH_DUEL_NOTES_2026_10_16: BM3_nonotes_* with --no-notes
    jp.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    hp = out / (NAME + "_report.html")
    hp.write_text(page(summary, units, used), encoding="utf-8")
    return jp, hp, summary


def _ci(ci) -> str:
    return "[%.2f, %.2f]" % tuple(ci) if ci else "-"


def _bold(v, ci) -> str:
    s = "%.2f %s" % (v, _ci(ci))
    return ("<b>%s</b>" % s) if ci and (ci[0] > 0.5 or ci[1] < 0.5) else s


def page(summary: dict, units: list, used: list) -> str:
    e = html.escape
    css = ("body{font-family:Georgia,serif;max-width:1150px;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}"
           "table{border-collapse:collapse;margin:1rem 0;font-size:14px}td,th{border:1px solid #ccc;padding:4px 8px;"
           "vertical-align:top;text-align:left}th{background:#f4f1ea}.n{text-align:right;font-variant-numeric:"
           "tabular-nums}.warn{background:#fff4e5;border:1px solid #f0c27b;padding:.6rem 1rem}details{margin:.4rem 0}"
           ".sa{font-size:13px;color:#555;font-style:italic}.small{font-size:12px;color:#666}")
    h = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
         "initial-scale=1'><title>BM3 report</title><style>%s</style></head><body>" % css,
         "<h1>BM3: the blind side-by-side of BM1's English%s</h1>" % ("" if NOTES_SHOWN else ": the check, the scholarly "
                                                                         "arm's notes withheld"),
         "<p class='warn'><b>Private evaluation.</b> This page holds the Mitrasamgraha test set's Sanskrit and, where it "
         "was read, its published English: it stays in this folder and is never published or put on the site.</p>",
         "<p class='small'>%s. The judges: %s (%s). Made %s.</p>" % (
             e(summary["how"]), e(", ".join("%s (%s)" % (j, summary["families"][j]) for j in used)),
             e(summary["version"]), e(summary["made_at"]))]
    for k in ["all", "core"] + [x for x in summary["scopes"] if x not in ("all", "core")]:
        v = summary["scopes"][k]
        if not v["units"]:
            continue
        h.append("<h2>%s: %d units (%d verses)</h2>" % (e(v["name"]), v["units"], v["verses"]))
        for j in used:
            jn = v["by_judge"].get(j) or {}
            if not jn.get("units"):
                continue
            rows = "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%d / %d / %d</td></tr>" % (
                e(p.replace(">", " above ")), _bold(d["share"], d["ci"]), d["wins"], d["ties"], d["losses"])
                for p, d in jn["pairs"].items())
            means = "".join("<tr><td>%s</td><td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td>"
                            "<td class='n'>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>" % (
                                e(a), m.get("fidelity", "-"), m.get("prose", "-"), m.get("notes", "-"),
                                m.get("major_per_10", "-"), m.get("minor_per_10", "-"),
                                "%.0f%%" % (100 * m["first"]) if m.get("first") is not None else "-")
                            for a, m in jn["means"].items())
            od = jn.get("order") or {}
            h.append("<h3>%s: %d units</h3><table><tr><th>Pair</th><th>Share [95%%]</th><th>Above / equal / below"
                     "</th></tr>%s</table><table><tr><th>Arm</th><th>Fidelity</th><th>Prose</th><th>Notes</th><th>Major "
                     "errors / 10 verses</th><th>Minor / 10</th><th>Ranked first</th></tr>%s</table>%s" % (
                         e(j), jn["units"], rows, means,
                         ("<p class='small'>The order: the first translation shown was ranked first %.0f%% of the time "
                          "(chance %.0f%%).</p>" % (100 * od["first_shown_ranked_first"], 100 * od["chance"])) if od else ""))
        b = v.get("both") or {}
        if b.get("units"):
            rows = "".join("<tr><td>%s</td><td class='n'>%d</td><td class='n'>%.0f%%</td><td class='n'>%s</td>"
                           "<td class='n'>%s</td></tr>" % (
                               e(p.replace(">", " above ")), d["units"], 100 * d["agree"], _bold(d["consensus"],
                                                                                              d["consensus_ci"]),
                               ("%d / %d" % (d["split_own_family"], d["split_other_family"]))
                               if "split_own_family" in d else "-") for p, d in b["pairs"].items())
            h.append("<h3>Both judges: %d units</h3><table><tr><th>Pair</th><th>Units</th><th>They order it alike</th>"
                     "<th>Share where they agree [95%%]</th><th>Split by family: each its own / each the other's</th></tr>"
                     "%s</table>" % (b["units"], rows))
    h.append("<p class='small'>How to read it: a pair's share above 0.5 means the first is preferred; in bold when the "
             "interval leaves out 0.5. A judge may favour its own family's English (gemini-2.5-pro and the flash arm; "
             "Claude Opus and the Sonnet arms): read each judge's numbers apart, and the splits by family.</p>")
    h.append("<h2>Unit by unit</h2>")
    for u in units:
        it, m = u["it"], u["m"]
        dev = {x["idx"]: x["dev"] for x in it["w"]}
        rows = []
        for j, r in sorted(u["r"].items()):
            for a in r["ranking"]:
                s = r["by_arm"].get(a) or {}
                errs = "; ".join("%s: %s (%s)" % (x.get("where", ""), x.get("error", ""), x.get("severity", ""))
                                 for x in s.get("errors") or [])
                rows.append("<tr><td>%s</td><td>%s</td><td class='n'>%s / %s / %s</td><td>%s</td></tr>" % (
                    e(j), e(a), s.get("fidelity"), s.get("prose"), s.get("notes"), e(errs) or "-"))
            rows.append("<tr><td colspan='4' class='small'>%s: best %s. %s</td></tr>" % (e(j), e(r["best"]),
                                                                                      e(r.get("reason") or "")))
        tx = texts_of(it, m, "reference" in (next(iter(u["r"].values())).get("contestants") or []))
        eng = "".join("<p><b>%s</b>: %s</p>" % (e(a), e(t["text"])) for a, t in (tx or {}).items())
        h.append("<details><summary>%s %s</summary><p class='sa'>%s</p>%s<table><tr><th>Judge</th><th>Arm (by its rank)"
                 "</th><th>Fidelity / prose / notes</th><th>Errors</th></tr>%s</table></details>" % (
                     e(u["key"]), e(u["unit"]), e(" ".join(dev[i] for i in m)), eng, "".join(rows)))
    h.append("</body></html>")
    return "".join(h)


# --------------------------------------------------------------------------------------------- the state (dashboard)
def state(bm1: Path = BM1_DEFAULT, out: Path = OUT_DEFAULT, mdb: str = "data/context.db",
          judges=None, step: int = 40) -> dict:
    """BM3 as it stands, read only: whether BM1 is complete, the units, what each judge has read, the price, the
    spend, the caps, the last report; the plans (with the published English): the pilot (the first 40 units), the
    next part (step units more than the most a judge has read) and all. Never writes."""
    judges = list(judges or SD.JUDGES)
    res = {"dir": str(out), "bm1": str(bm1), "mark": MARK, "judges": judges}
    sample, items = load(bm1)
    if not sample:
        res["ready"] = False
        res["why"] = "BM1 has no sample"
        return res
    miss = bm.missing_arms(bm1, sample, list(bm.FILES))
    res["ready"] = not miss
    res["missing"] = [list(x) for x in miss]
    if miss:
        res["why"] = "BM1's arms are not complete"
        return res
    order = order_of(items)
    rs = readings(out)
    ix = index_of(rs)
    res["units_total"] = len(order)
    res["read"] = {j: len({(r["key"], r["unit"]) for r in rs if r["judge"] == j}) for j in judges}
    res["with_reference"] = any("reference" in (r.get("contestants") or []) for r in rs) if rs else None
    p = Path(mdb)
    if p.exists():
        mcon = bm.open_ro(p)
        try:
            res["caps"] = bm.caps(mcon)
            res["prices"] = {j: dict(zip(("each", "how"), price(mcon, j))) for j in judges}
        finally:
            mcon.close()
    res["spend"] = spend(out)
    plans = {}
    done = max(list(res["read"].values()) or [0])
    for name, n in (("pilot", min(len(order), 40)), ("next", min(len(order), max(step, done + step))), ("all", None)):
        _c, todo = work_of(items, ix, judges, True, n)
        each = {j: (res.get("prices") or {}).get(j, {}).get("each") or PRIOR_CALL.get(j, 0.05) for j in judges}
        cl = sum(each[t["judge"]] for t in todo if family(t["judge"]) == "anthropic")
        gg = sum(each[t["judge"]] for t in todo if family(t["judge"]) == "gemini")
        plans[name] = {"units": n if n is not None else len(order), "calls": len(todo), "claude": round(cl, 4),
                       "google": round(gg, 4), "usd": round(cl + gg, 4),
                       "max_usd": max(0.25, round((cl + gg) * 1.3 + 0.05, 2))}
    res["plans"] = plans
    sj = out / "BM3_summary.json"
    if sj.exists():
        try:
            res["summary"] = json.loads(sj.read_text(encoding="utf-8"))
            res["summary_mtime"] = sj.stat().st_mtime
            dj = out / "duel.jsonl"
            res["stale"] = dj.exists() and dj.stat().st_mtime > sj.stat().st_mtime
        except (OSError, ValueError):
            pass
    return res


# --------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db", help="the real ledger (usage_log, budget_state)")
    ap.add_argument("--bm1", default=str(BM1_DEFAULT), help="BM1's folder (read only)")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="BM3's folder, outside every repository")
    ap.add_argument("--judges", default=",".join(SD.JUDGES))
    ap.add_argument("--units", type=int, default=None, help="the first N units of the order of reading")
    ap.add_argument("--with-reference", action="store_true", help="the published English as a fourth translation")
    ap.add_argument("--no-notes", action="store_true", help="the scholarly arm's notes withheld (a check: they name it); "
                    "its report is BM3_nonotes_report.html")   # BENCH_DUEL_NOTES_2026_10_16
    ap.add_argument("--report", action="store_true", help="BM3_report.html and BM3_summary.json (free)")
    ap.add_argument("--settle", action="store_true", help="what a stopped run left, into the ledger (free)")
    ap.add_argument("--max-usd", type=float, default=None)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    out, bm1 = Path(a.out), Path(a.bm1)
    global ME, NOTES_SHOWN, NAME
    NOTES_SHOWN, NAME = (False, "BM3_nonotes") if a.no_notes else (True, "BM3")   # BENCH_DUEL_NOTES_2026_10_16
    ME = "python scripts\\bench_duel.py" + ((' --out "%s"' % a.out) if out != OUT_DEFAULT else "") + (
        (' --bm1 "%s"' % a.bm1) if bm1 != BM1_DEFAULT else "") + ((' --db "%s"' % a.db) if a.db != "data/context.db"
                                                                   else "") + (
        (" --judges %s" % a.judges) if a.judges != ",".join(SD.JUDGES) else "") + (" --no-notes" if a.no_notes else "")
    judges = [x.strip() for x in a.judges.split(",") if x.strip()]
    if not bm.outside_repos(out):
        print("REFUSE: --out %s is inside a repository: the dataset's text must not be committed" % out)
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    if a.settle:
        return settle(out, a.db)
    if not hasattr(ST, "SYSTEMS") or "duel" not in ST.SYSTEMS:
        print("REFUSE: duel-v1's prompt is not registered (scholar_duel.py)"); print("VERDICT: nothing done")
        print("NEXT: "); return 1
    sample, items = load(bm1)
    if not sample:
        print("REFUSE: BM1 has no sample in %s" % bm1); print("VERDICT: nothing done")
        print("NEXT: python scripts\\bench_mitra.py --sample"); return 1
    miss = bm.missing_arms(bm1, sample, list(bm.FILES))
    if miss:
        print("REFUSE: BM1's arms are not complete (%s): BM3 reads the three side by side"
              % ", ".join("%s on %s" % x for x in miss[:6]))
        print("VERDICT: nothing done"); print("NEXT: python scripts\\bench_mitra.py"); return 1
    if a.report:
        jp, hp, summ = report(out, bm1, items, judges, True if a.with_reference else None)
        al = summ["scopes"]["all"]
        print("bench_duel.py  %s  %s  the report (free)" % (MARK, BENCH))
        for j, v in al["by_judge"].items():
            if v.get("units"):
                print("  %-28s %d units: %s" % (j, v["units"], "; ".join("%s %.2f %s" % (p, d["share"], _ci(d["ci"]))
                                                                        for p, d in v["pairs"].items())))
        b = al.get("both") or {}
        if b.get("units"):
            print("  both judges, %d units: %s" % (b["units"], "; ".join("%s agree %.0f%%" % (p, 100 * d["agree"])
                                                                        for p, d in b["pairs"].items())))
        print("VERDICT: written %s and %s%s" % (hp, jp, "" if al["units"] else " (nothing read yet)"))
        print('NEXT: Start-Process "%s"   (or the Benchmarks page)' % hp)
        return 0
    if not Path(a.db).exists():
        print("REFUSE: %s not found (run from the automaton's folder)" % a.db)
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    return run(a, out, bm1, items, judges)


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
