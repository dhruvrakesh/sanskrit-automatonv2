#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
bench_gold.py  (2026-10-16)  BENCH_GOLD_2026_10_16  (BM2)

BM2: a person's blind reading of BM3's units, the gold the judges are measured against. BM1 scored each arm alone;
BM3 has two machine judges, one of each family, rank the arms' English side by side. Where they disagree, or where
both may share a blind spot, a person who reads the Sanskrit decides.

What the person reads: BM3's units in BM3's order of reading (so the units both judges read come first), each with its
Sanskrit (Devanagari and IAST), the Sanskrit of the verses around it, and the four translations as "Translation 1, 2,
3, 4": the three arms' English (flash, sonnet1, scholar) and the published English, in an order shuffled for each
unit (seed BM2-2026-10-16, not the judges' orders). Nothing says who made which; the scholarly arm's notes are kept
back until the pick (they would name it). The person picks the best (or "equal") and may mark any translation as
wrong in meaning, with a note. Then, and only then, the page says who made each and what each judge chose.

Stored: D:\\Sanksrit Automatons\\benchmarks\\bm2\\person.jsonl (append-only, outside every repository; the latest
pick of a person for a unit counts, on the English the unit has now). Nothing is called and nothing is paid.

The report (BM2_report.html, private: the dataset's text and the person's notes; BM2_summary.json, numbers only), for
all eight texts and without the Bhagavata, per person:
  - how often each arm is the person's best (weighted by verses), and how often it is marked wrong in meaning, per
    ten verses;
  - for each pair of arms, of the units where the person chose one of the two, the share for the first, with a 95%
    bootstrap interval;
  - each judge against the person: how often its best is the person's best (with the chance level), and of the
    translations the person marked wrong in meaning, how many the judge gave a major error (and of the others, how
    many it did: its false alarms).

  python scripts\\bench_gold.py              the state (free)
  python scripts\\bench_gold.py --report     BM2_report.html and BM2_summary.json (free)
The reading itself is on the dashboard: /benchmarks/bm2.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import bench_duel as bd      # noqa: E402  (BM3: its units, its order, its readings)

bm = bd.bm
MARK = "BENCH_GOLD_2026_10_16"
BENCH = "BM2"
SEED = "BM2-2026-10-16"
VERSION = "bm2-v1"
OUT_DEFAULT = ROOT.parent / "benchmarks" / "bm2"
BM1_DEFAULT = bm.OUT_DEFAULT
BM3_DEFAULT = bd.OUT_DEFAULT
BOOT = 1000
BEFORE, AFTER = 3, 2          # the verses shown around a unit (Sanskrit only)
BY_OK = re.compile(r"^[A-Za-z][A-Za-z .'-]{0,39}$")
NOTE_MAX = 1000
ARM_NAME = {"flash": "gemini-2.5-flash in one pass (the working English)",
            "sonnet1": "Claude Sonnet 5.5 in one pass (the same prompt)",
            "scholar": "the scholarly pipeline (Sonnet drafts, critiques and revises; judge-v1 reads it)",
            "reference": "the published English"}
ME = "python scripts\\bench_gold.py"


# --------------------------------------------------------------------------------------------- the units
def units(bm1: Path) -> tuple:
    """(sample, [unit]) in BM3's order of reading, with the published English among the translations."""
    sample, items = bd.load(bm1)
    if not sample:
        return None, []
    got = []
    for ti, ui in bd.order_of(items):
        it = items[ti]
        m = it["units"][ui]
        t = bd.texts_of(it, m, True)
        if t is None:
            continue
        sh = bd.shas(t)
        sh0 = bd.shas({a: {"text": v["text"], "notes": []} for a, v in t.items()})   # BENCH_GOLD_FAIR_2026_10_17
        got.append({"it": it, "m": m, "key": it["f"]["key"], "unit": bm.unit_name(m), "n": len(m), "texts": t,
                    "shas": sh, "shas0": sh0, "token": bm.sha(json.dumps(sh, sort_keys=True))})
    return sample, got


def order_for(key: str, unit: str, arms) -> list:
    """The arms in the person's order for this unit: Translation 1 is the first."""
    out = sorted(arms)
    random.Random("%s|%s|%s" % (SEED, key, unit)).shuffle(out)
    return out


def picks(out: Path) -> list:
    p = out / "person.jsonl"
    got = []
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("by") and r.get("best"):
                    got.append(r)
    return got


def latest(rs: list, by=None) -> dict:
    """{(key, unit, by, shas as JSON): the latest pick}."""
    ix = {}
    for r in rs:
        if by is None or r["by"] == by:
            ix[(r["key"], r["unit"], r["by"], json.dumps(r.get("shas") or {}, sort_keys=True))] = r
    return ix


def _ctx(sample: dict, key: str, m: list) -> tuple:
    """(the verses before, the verses after) of a unit: Sanskrit only."""
    ls = sorted((x for x in sample["lines"] if x["key"] == key), key=lambda x: (x["page"], x["idx"]))
    first = next(i for i, x in enumerate(ls) if x["page"] == 2 and x["idx"] == m[0])
    last = next(i for i, x in enumerate(ls) if x["page"] == 2 and x["idx"] == m[-1])
    show = lambda x: {"dev": x["dev"], "iast": x["iast"]}
    return [show(x) for x in ls[max(0, first - BEFORE):first]], [show(x) for x in ls[last + 1:last + 1 + AFTER]]


def view(sample: dict, u: dict) -> dict:
    """What the page shows of a unit before the pick: no names, no notes, no published English apart."""
    w = {x["idx"]: x for x in u["it"]["w"]}
    before, after = _ctx(sample, u["key"], u["m"])
    arms = order_for(u["key"], u["unit"], u["texts"])
    return {"key": u["key"], "unit": u["unit"], "title": u["it"]["f"]["title"], "n": u["n"], "token": u["token"],
            "verses": [{"dev": w[i]["dev"], "iast": w[i]["iast"]} for i in u["m"]], "before": before, "after": after,
            "translations": [{"n": k + 1, "text": u["texts"][a]["text"]} for k, a in enumerate(arms)]}


def next_for(bm1: Path, out: Path, by: str) -> dict:
    """The next unit this person has not read (on its present English), with the progress."""
    sample, us = units(bm1)
    if not sample:
        return {"error": "BM1 has no sample"}
    ix = latest(picks(out), by)
    done = [u for u in us if (u["key"], u["unit"], by, json.dumps(u["shas"], sort_keys=True)) in ix]
    res = {"by": by, "read": len(done), "total": len(us), "mark": MARK}
    for u in us:
        if (u["key"], u["unit"], by, json.dumps(u["shas"], sort_keys=True)) not in ix:
            res["unit"] = view(sample, u)
            break
    res["done"] = "unit" not in res
    return res


def reveal(u: dict, bm3: Path) -> dict:
    """After the pick: who made each translation, the scholarly arm's notes, and what each judge of BM3 chose."""
    arms = order_for(u["key"], u["unit"], u["texts"])
    names = {a: ARM_NAME[a] + ((" (%s)" % u["it"]["f"]["ref"]) if a == "reference" else "") for a in arms}
    num = {a: k + 1 for k, a in enumerate(arms)}
    judges = {}
    sh = json.dumps(u["shas"], sort_keys=True)
    for (k, un, j, s), r in bd.index_of(bd.readings(bm3)).items():
        if k == u["key"] and un == u["unit"] and s == sh:
            judges[j] = {"best": r["best"], "best_n": num.get(r["best"], 0),
                         "majors": [num[a] for a, v in (r.get("by_arm") or {}).items()
                                    if a in num and any(e.get("severity") == "major" for e in v.get("errors") or [])]}
    notes = u["texts"]["scholar"]["notes"]
    return {"who": [{"n": num[a], "arm": a, "name": names[a]} for a in arms], "judges": judges,
            "scholar_n": num["scholar"],
            "scholar_notes": [{"anchor": x.get("anchor", ""), "note": x.get("note", "")} for x in notes if isinstance(x, dict)]}


def record(bm1: Path, out: Path, bm3: Path, by: str, key: str, unit: str, token: str, best, majors=(), note: str = ""):
    """A person's pick, stored; (the reveal, None) or (None, why)."""
    by = str(by or "").strip()
    if not BY_OK.match(by):
        return None, "say who is reading (letters, up to 40)"
    note = str(note or "").strip()
    if len(note) > NOTE_MAX:
        return None, "the note is longer than %d characters" % NOTE_MAX
    sample, us = units(bm1)
    u = next((x for x in us if x["key"] == key and x["unit"] == unit), None)
    if u is None:
        return None, "no such unit"
    if token != u["token"]:
        return None, "this unit's English has changed since the page was made: read it again"
    arms = order_for(u["key"], u["unit"], u["texts"])
    k = len(arms)
    if str(best) == "equal":
        best_arm, best_n = "equal", 0
    else:
        try:
            best_n = int(best)
        except (TypeError, ValueError):
            return None, "pick the best (1 to %d) or equal" % k
        if not 1 <= best_n <= k:
            return None, "pick the best (1 to %d) or equal" % k
        best_arm = arms[best_n - 1]
    mj = []
    for x in majors or []:
        try:
            x = int(x)
        except (TypeError, ValueError):
            return None, "a translation marked wrong is a number, 1 to %d" % k
        if not 1 <= x <= k:
            return None, "a translation marked wrong is a number, 1 to %d" % k
        if arms[x - 1] not in mj:
            mj.append(arms[x - 1])
    rec = {"key": u["key"], "unit": u["unit"], "n": u["n"], "by": by, "version": VERSION,
           "order": {str(i + 1): a for i, a in enumerate(arms)}, "best": best_arm, "best_n": best_n, "majors": mj,
           "note": note, "shas": u["shas"], "at": bm.now(), "mark": MARK}
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "person.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return reveal(u, bm3), None


# --------------------------------------------------------------------------------------------- the numbers
def _share(rows: list) -> float:
    w = sum(n for _o, n in rows)
    return sum(o * n for o, n in rows) / w if w else 0.0


def person_numbers(us: list, by: str, rng) -> dict:
    """us: [{"n", "p": {by: pick}, "j": {judge: reading}}]."""
    xs = [u for u in us if by in u["p"]]
    out = {"units": len(xs), "verses": sum(u["n"] for u in xs), "best": {}, "wrong_per_10": {}, "pairs": {},
           "judges": {}}
    if not xs:
        return out
    w = out["verses"]
    arms = sorted({a for u in xs for a in u["p"][by]["order"].values()})
    for a in arms + ["equal"]:
        out["best"][a] = round(sum(u["n"] for u in xs if u["p"][by]["best"] == a) / w, 3)
    for a in arms:
        out["wrong_per_10"][a] = round(10.0 * sum(u["n"] for u in xs if a in u["p"][by].get("majors", [])) / w, 2)
    for x, y in bd.PAIRS:
        rows = [(1.0 if u["p"][by]["best"] == x else 0.0, u["n"]) for u in xs if u["p"][by]["best"] in (x, y)]
        if rows:
            out["pairs"]["%s>%s" % (x, y)] = {"share": round(_share(rows), 3), "units": len(rows),
                                              "ci": bm.boot_ci(len(rows), lambda ix: _share([rows[i] for i in ix]), rng)}
    out["judges"] = judge_numbers(xs, by, rng, "j")
    out["judges_as_read"] = judge_numbers(xs, by, rng, "j0")   # BENCH_GOLD_FAIR_2026_10_17
    return out


def judge_numbers(xs: list, by: str, rng, field: str = "j") -> dict:
    """Each judge against the person. BENCH_GOLD_FAIR_2026_10_17: field "j" holds the judges' readings of BM3's pilot,
    the scholarly arm's notes shown to them; "j0" those of BM3's check, the notes withheld, as the person reads them
    here (the notes would name the arm). On 17 Oct the first was the only one: the person's 24 units were set beside
    judges who had read notes the person had not."""
    res = {}
    for j in sorted({j for u in xs for j in (u.get(field) or {})}):
        both = [u for u in xs if j in (u.get(field) or {})]
        rows = [(1.0 if u[field][j]["best"] == u["p"][by]["best"] else 0.0, u["n"]) for u in both]
        chance = sum(1.0 / (len(u["p"][by]["order"]) + 1) for u in both) / len(both)
        caught = alarm = marked = clean = 0
        for u in both:
            for a, v in (u[field][j].get("by_arm") or {}).items():
                maj = any(e.get("severity") == "major" for e in v.get("errors") or [])
                if a in u["p"][by].get("majors", []):
                    marked += 1
                    caught += 1 if maj else 0
                else:
                    clean += 1
                    alarm += 1 if maj else 0
        res[j] = {"units": len(both), "same_best": round(_share(rows), 3),
                  "same_best_ci": bm.boot_ci(len(rows), lambda ix: _share([rows[i] for i in ix]), rng),
                  "chance": round(chance, 3), "wrong_marked": marked, "judge_caught": caught,
                  "not_marked": clean, "judge_major_anyway": alarm}
    return res


def gather(bm1: Path, out: Path, bm3: Path) -> list:
    sample, us = units(bm1)
    ix = latest(picks(out))
    jx = bd.index_of(bd.readings(bm3))
    got = []
    for u in us:
        sh = json.dumps(u["shas"], sort_keys=True)
        p = {by: r for (k, un, by, s), r in ix.items() if k == u["key"] and un == u["unit"] and s == sh}
        if not p:
            continue
        j = {jj: r for (k, un, jj, s), r in jx.items() if k == u["key"] and un == u["unit"] and s == sh}
        sh0 = json.dumps(u.get("shas0") or {}, sort_keys=True)   # BENCH_GOLD_FAIR_2026_10_17: as the person read
        j0 = {jj: r for (k, un, jj, s), r in jx.items() if k == u["key"] and un == u["unit"] and s == sh0
              and (r.get("notes_shown") is False or sh0 == sh)}
        got.append(dict(u, p=p, j=j, j0=j0))
    return got


def report(bm1: Path, out: Path, bm3: Path) -> tuple:
    us = gather(bm1, out, bm3)
    people = sorted({by for u in us for by in u["p"]})
    rng = random.Random(SEED + ":boot")
    scopes = {}
    for k, name, keep in (("all", "all eight texts", lambda u: True),
                          ("core", "without the Bhagavata (%s)" % ", ".join(bd.CORE_OUT),
                           lambda u: u["key"] not in bd.CORE_OUT)):
        xs = [u for u in us if keep(u)]
        scopes[k] = {"name": name, "units": len(xs), "by_person": {p: person_numbers(xs, p, rng) for p in people}}
    summary = {"mark": MARK, "bench": BENCH, "made_at": bm.now(), "seed": SEED, "version": VERSION, "people": people,
               "units_total": len(units(bm1)[1]), "scopes": scopes,
               "how": "the person's best among the four translations of a unit, blind, in an order of its own; pairs: "
                      "of the units where the person chose one of the two, the share for the first; weighted by verses; "
                      "intervals by %d bootstrap resamples of the units" % BOOT}
    out.mkdir(parents=True, exist_ok=True)
    jp = out / "BM2_summary.json"
    jp.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    hp = out / "BM2_report.html"
    hp.write_text(page(summary, us), encoding="utf-8")
    return jp, hp, summary


def page(summary: dict, us: list) -> str:
    e = html.escape
    css = ("body{font-family:Georgia,serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}"
           "table{border-collapse:collapse;margin:1rem 0;font-size:14px}td,th{border:1px solid #ccc;padding:4px 8px;"
           "vertical-align:top;text-align:left}th{background:#f4f1ea}.n{text-align:right}.warn{background:#fff4e5;"
           "border:1px solid #f0c27b;padding:.6rem 1rem}.small{font-size:12px;color:#666}.sa{font-style:italic;color:#555}")
    h = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
         "initial-scale=1'><title>BM2 report</title><style>%s</style></head><body>" % css,
         "<h1>BM2: a person's blind reading</h1>",
         "<p class='warn'><b>Private evaluation.</b> This page holds the Mitrasamgraha test set's Sanskrit and published "
         "English, and the reader's notes: it stays in this folder and is never published or put on the site.</p>",
         "<p class='small'>%s. Made %s.</p>" % (e(summary["how"]), e(summary["made_at"]))]
    for k in ("all", "core"):
        v = summary["scopes"][k]
        for p, pn in v["by_person"].items():
            if not pn["units"]:
                continue
            h.append("<h2>%s, read by %s: %d units (%d verses)</h2>" % (e(v["name"]), e(p), pn["units"], pn["verses"]))
            h.append("<table><tr><th>Arm</th><th>The best</th><th>Wrong in meaning / 10 verses</th></tr>%s</table>" % "".join(
                "<tr><td>%s</td><td class='n'>%.0f%%</td><td class='n'>%s</td></tr>" % (
                    e(a), 100 * s, pn["wrong_per_10"].get(a, "-")) for a, s in pn["best"].items()))
            h.append("<table><tr><th>Pair</th><th>Units</th><th>Share for the first [95%%]</th></tr>%s</table>" % "".join(
                "<tr><td>%s</td><td class='n'>%d</td><td class='n'>%.2f %s</td></tr>" % (
                    e(x.replace(">", " over ")), d["units"], d["share"], bd._ci(d["ci"])) for x, d in pn["pairs"].items()))
            h.append("<table><tr><th>Judge</th><th>Units</th><th>Its best is the person's [95%%] (chance)</th><th>Marked "
                     "wrong by the person: the judge found a major error</th><th>Not marked: the judge found one anyway"
                     "</th></tr>%s</table>" % "".join(
                         "<tr><td>%s</td><td class='n'>%d</td><td class='n'>%.2f %s (%.2f)</td><td class='n'>%d of %d</td>"
                         "<td class='n'>%d of %d</td></tr>" % (e(j), d["units"], d["same_best"], bd._ci(d["same_best_ci"]),
                                                              d["chance"], d["judge_caught"], d["wrong_marked"],
                                                              d["judge_major_anyway"], d["not_marked"])
                         for j, d in pn["judges"].items()))
            if pn.get("judges_as_read"):   # BENCH_GOLD_FAIR_2026_10_17
                h.append("<p class='small'>Above: the judges of BM3's pilot, who were shown the scholarly arm's notes. "
                         "Below: the judges of BM3's check, the notes withheld from them as from the reader.</p>")
                h.append("<table><tr><th>Judge, the notes withheld</th><th>Units</th><th>Its best is the person's [95%%] "
                         "(chance)</th><th>Marked wrong by the person: the judge found a major error</th><th>Not marked: "
                         "the judge found one anyway</th></tr>%s</table>" % "".join(
                             "<tr><td>%s</td><td class='n'>%d</td><td class='n'>%.2f %s (%.2f)</td><td class='n'>%d of %d"
                             "</td><td class='n'>%d of %d</td></tr>" % (
                                 e(j), d["units"], d["same_best"], bd._ci(d["same_best_ci"]), d["chance"],
                                 d["judge_caught"], d["wrong_marked"], d["judge_major_anyway"], d["not_marked"])
                             for j, d in pn["judges_as_read"].items()))
    h.append("<h2>Unit by unit</h2>")
    for u in us:
        dev = {x["idx"]: x["dev"] for x in u["it"]["w"]}
        rows = []
        for by, r in sorted(u["p"].items()):
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                e(by), e(r["best"]), e(", ".join(r.get("majors") or []) or "-"), e(r.get("note") or "")))
        for j, r in sorted(u["j"].items()):
            rows.append("<tr><td>%s</td><td>%s</td><td colspan='2' class='small'>%s</td></tr>" % (
                e(j), e(r["best"]), e(r.get("reason") or "")))
        eng = "".join("<p><b>%s</b>: %s</p>" % (e(a), e(t["text"])) for a, t in u["texts"].items())
        h.append("<details><summary>%s %s</summary><p class='sa'>%s</p>%s<table><tr><th>Who</th><th>Best</th><th>Wrong "
                 "in meaning</th><th>Note</th></tr>%s</table></details>" % (
                     e(u["key"]), e(u["unit"]), e(" ".join(dev[i] for i in u["m"])), eng, "".join(rows)))
    h.append("</body></html>")
    return "".join(h)


def state(bm1: Path = BM1_DEFAULT, out: Path = OUT_DEFAULT, bm3: Path = BM3_DEFAULT) -> dict:
    """For the dashboard, read only: the units, what each person has read, the last report."""
    res = {"dir": str(out), "mark": MARK}
    sample, us = units(bm1)
    if not sample:
        res["ready"], res["why"] = False, "BM1 has no sample"
        return res
    miss = bm.missing_arms(bm1, sample, list(bm.FILES))
    if miss:
        res["ready"], res["why"] = False, "BM1's arms are not complete"
        return res
    res["ready"] = True
    res["units_total"] = len(us)
    cur = {(u["key"], u["unit"], json.dumps(u["shas"], sort_keys=True)) for u in us}
    rd = {}
    for (k, un, by, s), _r in latest(picks(out)).items():
        if (k, un, s) in cur:
            rd[by] = rd.get(by, 0) + 1
    res["read"] = rd
    jx = bd.index_of(bd.readings(bm3))
    cnt = {}
    for (k, un, _j, s) in jx:
        if (k, un, s) in cur:
            cnt[(k, un)] = cnt.get((k, un), 0) + 1
    res["judged_both"] = sum(1 for v in cnt.values() if v >= 2)
    sj = out / "BM2_summary.json"
    if sj.exists():
        try:
            res["summary"] = json.loads(sj.read_text(encoding="utf-8"))
            res["summary_mtime"] = sj.stat().st_mtime
            pj = out / "person.jsonl"
            res["stale"] = pj.exists() and pj.stat().st_mtime > sj.stat().st_mtime
        except (OSError, ValueError):
            pass
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bm1", default=str(BM1_DEFAULT), help="BM1's folder (read only)")
    ap.add_argument("--bm3", default=str(BM3_DEFAULT), help="BM3's folder (read only)")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="BM2's folder, outside every repository")
    ap.add_argument("--report", action="store_true", help="BM2_report.html and BM2_summary.json (free)")
    a = ap.parse_args(argv)
    out, bm1, bm3 = Path(a.out), Path(a.bm1), Path(a.bm3)
    if not bm.outside_repos(out):
        print("REFUSE: --out %s is inside a repository: the dataset's text must not be committed" % out)
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    st = state(bm1, out, bm3)
    print("bench_gold.py  %s  %s  %s" % (MARK, BENCH, "the report (free)" if a.report else "the state (free)"))
    if not st.get("ready"):
        print("REFUSE: %s" % st.get("why")); print("VERDICT: nothing done")
        print("NEXT: python scripts\\bench_mitra.py"); return 1
    print("  units: %d (BM3's order; both judges have read %d); read by: %s"
          % (st["units_total"], st["judged_both"], ", ".join("%s %d" % kv for kv in sorted(st["read"].items())) or
             "nobody yet"))
    if not a.report:
        print("VERDICT: %d pick(s) so far" % sum(st["read"].values()))
        print("NEXT: the dashboard's /benchmarks/bm2 (the reading), then " + ME + " --report")
        return 0
    jp, hp, summ = report(bm1, out, bm3)
    for p, pn in summ["scopes"]["all"]["by_person"].items():
        print("  %s, %d units: best %s; judges: %s" % (p, pn["units"], json.dumps(pn["best"]), "; ".join(
            "%s same best %.2f (chance %.2f)" % (j, d["same_best"], d["chance"]) for j, d in pn["judges"].items())))
        if pn.get("judges_as_read"):   # BENCH_GOLD_FAIR_2026_10_17
            print("    the judges as the reader read (the notes withheld): %s" % "; ".join(
                "%s same best %.2f of %d units" % (j, d["same_best"], d["units"]) for j, d in pn["judges_as_read"].items()))
    print("VERDICT: written %s and %s" % (hp, jp))
    print('NEXT: Start-Process "%s"   (or the Benchmarks page)' % hp)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
