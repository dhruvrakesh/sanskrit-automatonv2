#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_bench_gold_fair_2026_10_17.py  (2026-10-17)  BENCH_GOLD_FAIR_2026_10_17

BM2's report set each judge's best beside the reader's using BM3's pilot readings, in which the judges were shown
the scholarly arm's notes; the reader reads without them (they would name the arm). On 17 Oct (24 units) that gave
Claude Opus 0.08 and gemini-2.5-pro 0.12 (chance 0.20). BM3's check read the same units with the notes withheld; now
the report sets the reader beside those readings too ("the judges as the reader read"), in the summary
(judges_as_read), the report, the command's output and the Benchmarks page. The pilot's comparison is kept. Free.

scripts/bench_gold.py (needs BENCH_GOLD_2026_10_16), scripts/dashboard.py (needs BUTTONS_2026_10_17). Anchored,
all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_goldfair_<date>.
  python scripts\\patch_bench_gold_fair_2026_10_17.py --check
  python scripts\\patch_bench_gold_fair_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'BENCH_GOLD_FAIR_2026_10_17'
NEEDS = {'scripts/bench_gold.py': 'BENCH_GOLD_2026_10_16', 'scripts/dashboard.py': 'BUTTONS_2026_10_17'}
FILES = list(NEEDS)
TAG = 'goldfair'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/bench_gold.py', 1, r'''        sh = bd.shas(t)
        got.append({"it": it, "m": m, "key": it["f"]["key"], "unit": bm.unit_name(m), "n": len(m), "texts": t,
                    "shas": sh, "token": bm.sha(json.dumps(sh, sort_keys=True))})
''', r'''        sh = bd.shas(t)
        sh0 = bd.shas({a: {"text": v["text"], "notes": []} for a, v in t.items()})   # BENCH_GOLD_FAIR_2026_10_17
        got.append({"it": it, "m": m, "key": it["f"]["key"], "unit": bm.unit_name(m), "n": len(m), "texts": t,
                    "shas": sh, "shas0": sh0, "token": bm.sha(json.dumps(sh, sort_keys=True))})
''')

edit('scripts/bench_gold.py', 2, r'''        j = {jj: r for (k, un, jj, s), r in jx.items() if k == u["key"] and un == u["unit"] and s == sh}
        got.append(dict(u, p=p, j=j))
''', r'''        j = {jj: r for (k, un, jj, s), r in jx.items() if k == u["key"] and un == u["unit"] and s == sh}
        sh0 = json.dumps(u.get("shas0") or {}, sort_keys=True)   # BENCH_GOLD_FAIR_2026_10_17: as the person read
        j0 = {jj: r for (k, un, jj, s), r in jx.items() if k == u["key"] and un == u["unit"] and s == sh0
              and (r.get("notes_shown") is False or sh0 == sh)}
        got.append(dict(u, p=p, j=j, j0=j0))
''')

edit('scripts/bench_gold.py', 3, r'''    for j in sorted({j for u in xs for j in u["j"]}):
        both = [u for u in xs if j in u["j"]]
        rows = [(1.0 if u["j"][j]["best"] == u["p"][by]["best"] else 0.0, u["n"]) for u in both]
        chance = sum(1.0 / (len(u["p"][by]["order"]) + 1) for u in both) / len(both)
        caught = alarm = marked = clean = 0
        for u in both:
            for a, v in (u["j"][j].get("by_arm") or {}).items():
                maj = any(e.get("severity") == "major" for e in v.get("errors") or [])
                if a in u["p"][by].get("majors", []):
                    marked += 1
                    caught += 1 if maj else 0
                else:
                    clean += 1
                    alarm += 1 if maj else 0
        out["judges"][j] = {"units": len(both), "same_best": round(_share(rows), 3),
                            "same_best_ci": bm.boot_ci(len(rows), lambda ix: _share([rows[i] for i in ix]), rng),
                            "chance": round(chance, 3), "wrong_marked": marked, "judge_caught": caught,
                            "not_marked": clean, "judge_major_anyway": alarm}
    return out
''', r'''    out["judges"] = judge_numbers(xs, by, rng, "j")
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
''')

edit('scripts/bench_gold.py', 4, r'''                         for j, d in pn["judges"].items()))
    h.append("<h2>Unit by unit</h2>")
''', r'''                         for j, d in pn["judges"].items()))
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
''')

edit('scripts/bench_gold.py', 5, r'''            "%s same best %.2f (chance %.2f)" % (j, d["same_best"], d["chance"]) for j, d in pn["judges"].items())))
''', r'''            "%s same best %.2f (chance %.2f)" % (j, d["same_best"], d["chance"]) for j, d in pn["judges"].items())))
        if pn.get("judges_as_read"):   # BENCH_GOLD_FAIR_2026_10_17
            print("    the judges as the reader read (the notes withheld): %s" % "; ".join(
                "%s same best %.2f of %d units" % (j, d["same_best"], d["units"]) for j, d in pn["judges_as_read"].items()))
''')

edit('scripts/dashboard.py', 1, r'''                e("; ".join("%s: same best %.2f (chance %.2f); caught %d of %d you marked wrong" % (
                    _BM3_SHORT.get(j, j), d["same_best"], d["chance"], d["judge_caught"], d["wrong_marked"])
                    for j, d in (pn.get("judges") or {}).items())))
''', r'''                e("; ".join("%s: same best %.2f with the notes shown%s (chance %.2f); caught %d of %d you marked wrong" % (
                    _BM3_SHORT.get(j, j), d["same_best"],
                    (", %.2f with them withheld, as you read (%d units)" % (
                        (pn.get("judges_as_read") or {})[j]["same_best"], (pn.get("judges_as_read") or {})[j]["units"]))
                    if j in (pn.get("judges_as_read") or {}) else "",   # BENCH_GOLD_FAIR_2026_10_17
                    d["chance"], d["judge_caught"], d["wrong_marked"])
                    for j, d in (pn.get("judges") or {}).items())))
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_bench_gold_fair_2026_10_17')
    print('  python scripts\\bench_gold.py --report')
    return 0


if __name__ == "__main__":
    sys.exit(main())
