#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_triage_2026_10_16.py  (2026-10-16)  TRIAGE_2026_10_16

The Hayasirsa Pancaratra and the Karanagama are done on claude-sonnet-5-5 (15 Oct, 13:36 to 16:12 UTC): 1,418 and
1,018 verses; 242 and 151 not passed. A person reads them; this sorts them so the serious come first, and lets
another engine read the serious again. Follows REJUDGE_2026_10_15.

scripts/scholar_translate.py:
  - triage_of(row): the tier of a row not passed, and why:
      rejected  a person rejected it;
      source    a source doubt (the printed text or its reading is in doubt: the source is checked, not the English);
      serious   the critic's answer not read; a major issue in the last critique (the critic's or the audit's); the
                judge's fidelity 2 or less, or no answer; a major error found by the second judge;
      mild      the rest: the judge's fidelity 3, or fluency below 4; a last critique "revise" with no major issue;
    a row a person accepted is not listed;
  - --triage (with --engine, read-only, free): the tiers and their reasons, counted; exports/scholar_triage_<doc>.csv
    (UTF-8 with a BOM, for Excel): one line a verse, rejected, source, serious, mild, in the text's order;
  - --only-flagged ENGINE [--serious]: the run reads again only the verses ENGINE did not pass (not accepted by a
    person; with --serious, the rejected and the serious): a verse already read again by --engine since is left
    (--redo reads it once more); the context is every engine's rows;
  - --status adds, per engine, "not passed: N serious, M mild, K source";
  - the re-judge prices a judge call as measured (usage_log, kind judge, since METERED_SINCE, 20 calls or more), else
    $0.0027 (gemini-2.5-flash with its thinking, 15 Oct: 2,079 calls, $0.00274 each); the prior of 0.0002 did not
    count the thinking.

Needs REJUDGE_2026_10_15. Anchored, all-or-nothing, marker-idempotent; keeps line endings; ASCII; py_compile before
the atomic replace; backup .bak_triage_<date>.
  python scripts\\patch_triage_2026_10_16.py --check
  python scripts\\patch_triage_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "TRIAGE_2026_10_16"
NEEDS = {"scripts/scholar_translate.py": "REJUDGE_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15, REJUDGE_2026_10_15
''', r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15, REJUDGE_2026_10_15,
TRIAGE_2026_10_16
''')

edit(ST, 2, r'''a Claude judge read, and decides their status again; a new version of each, the same English.
''', r'''a Claude judge read, and decides their status again; a new version of each, the same English.

TRIAGE_2026_10_16: --triage sorts the verses not passed (rejected, source, serious, mild) into a CSV for a person;
--only-flagged ENGINE [--serious] reads again only what ENGINE did not pass; --status counts the tiers.
''')

edit(ST, 3, r'''        if a.only_page is not None and (x["page"] != a.only_page or (a.only_idx is not None and x["idx"] != a.only_idx)):
            continue
''', r'''        if a.only_page is not None and (x["page"] != a.only_page or (a.only_idx is not None and x["idx"] != a.only_idx)):
            continue
        if getattr(a, "only_ids", None) is not None and x["id"] not in a.only_ids:   # TRIAGE_2026_10_16
            continue
''')

edit(ST, 4, r'''        if current(done.get(x["id"]), x) and not a.redo:
            skipped.append(x)
            continue
        picked.append(i)
''', r'''        if getattr(a, "only_ids", None) is not None:   # TRIAGE_2026_10_16: read again what another engine did not pass
            if x["id"] in (getattr(a, "skip_ids", None) or set()) and not a.redo:
                skipped.append(x)
                continue
        elif current(done.get(x["id"]), x) and not a.redo:
            skipped.append(x)
            continue
        picked.append(i)
''')

edit(ST, 5, r'''    return out or ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]
''', r'''    try:   # TRIAGE_2026_10_16: what a person reads first
        ext = []
        for ln, (eng, _e) in zip(out, sorted(per.items())):
            ext.append(ln)
            t = triage_counts(con, doc, eng, sel)
            if t["serious"] or t["mild"] or t["source"] or t["rejected"]:
                ext.append("    not passed: %d serious, %d mild, %d source%s (--triage lists them)"
                           % (t["serious"], t["mild"], t["source"],
                              (", %d rejected by a person" % t["rejected"]) if t["rejected"] else ""))
        out = ext
    except Exception:
        pass
    return out or ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]


TIERS = ("rejected", "source", "serious", "mild")


def triage_of(r: dict) -> tuple:
    """TRIAGE_2026_10_16: (tier, [reason, ...]) of a row not passed; ("", []) when it passed or a person accepted it.
    Tiers: rejected (by a person), source (a source doubt), serious, mild (the module's docstring says which is
    which)."""
    if r.get("review_verdict") == "accept" or (r.get("status") == "passed" and r.get("review_verdict") != "reject"):
        return "", []
    crits = _loads(r.get("critique"), [])
    final = crits[-1] if crits else None
    rs, serious = [], False
    if not isinstance(final, dict):
        rs.append("the critic's answer was not read"); serious = True
    else:
        who = "the audit" if final.get("by") else "the critic"
        maj = [i for i in (final.get("issues") or []) if isinstance(i, dict) and i.get("severity") == "major"]
        if maj:
            rs.append("%s: a major %s" % (who, "/".join(sorted({str(i.get("type") or "?") for i in maj}))))
            serious = True
        elif final.get("verdict") != "accept":
            rs.append("%s: revise, no major issue" % who)
    fid, flu = r.get("fidelity"), r.get("fluency")
    if fid is None or flu is None:
        rs.append("the judge did not answer"); serious = True
    else:
        if fid <= 3:
            rs.append("the judge: fidelity %s" % fid)
            serious = serious or fid <= 2
        if flu < 4:
            rs.append("the judge: fluency %s" % flu)
    cm = _loads(r.get("compare"), {})
    if any(isinstance(e, dict) and e.get("severity") == "major" for e in ((cm.get("scholarly") or {}).get("errors") or [])):
        rs.append("the second judge: a major error"); serious = True
    if r.get("review_verdict") == "reject":
        tier = "rejected"
    elif r.get("status") == "source_doubt":
        tier = "source"
    else:
        tier = "serious" if serious else "mild"
    return tier, rs


def triage_rows(con, doc: str, engine: str, sel: list) -> list:
    """TRIAGE_2026_10_16: [(tier, reasons, row, passage)] of engine's latest rows not passed, current, within sel, in the
    text's order."""
    byid = {x["id"]: x for x in sel}
    out = []
    for pid, r in latest_rows(con, doc, engine).items():
        x = byid.get(pid)
        if x is None or not current(r, x):
            continue
        tier, rs = triage_of(r)
        if tier:
            out.append((tier, rs, r, x))
    out.sort(key=lambda t: (t[3]["page"] or 0, t[3]["idx"] or 0))
    return out


def triage_counts(con, doc: str, engine: str, sel: list) -> dict:
    c = {k: 0 for k in TIERS}
    for tier, _rs, _r, _x in triage_rows(con, doc, engine, sel):
        c[tier] += 1
    return c


def triage_main(a) -> int:
    """TRIAGE_2026_10_16: --triage, read-only and free: the tiers counted, and exports/scholar_triage_<doc>.csv."""
    import csv
    from collections import Counter
    con = open_ro(a.db)
    try:
        allp = load_text(con, a.doc)
        pages = parse_pages(getattr(a, "pages", None))
        sel = [x for x in allp if pages is None or x["page"] in pages]
        rows = triage_rows(con, a.doc, a.engine, sel)
        accepted = sum(1 for r in latest_rows(con, a.doc, a.engine).values() if r.get("review_verdict") == "accept")
    finally:
        con.close()
    rank = {k: i for i, k in enumerate(TIERS)}
    rows.sort(key=lambda t: (rank[t[0]], t[3]["page"] or 0, t[3]["idx"] or 0))
    out = Path(a.exports) / ("scholar_triage_%s.csv" % _safe(a.doc))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["tier", "verse", "page", "idx", "status", "reasons", "fidelity", "fluency", "judge", "last critique by",
                    "sanskrit", "english", "doubts", "passage_id"])
        for tier, rs, r, x in rows:
            crits = _loads(r.get("critique"), [])
            final = crits[-1] if crits and isinstance(crits[-1], dict) else {}
            w.writerow([tier, r.get("group_ref") or r.get("verse_ref"), x["page"], x["idx"], r.get("status"), "; ".join(rs),
                        r.get("fidelity"), r.get("fluency"), r.get("judge_engine"),
                        final.get("by") or ("the critic" if final else ""), (x.get("text") or "")[:300],
                        ((r.get("group_translation") if r.get("group_ref") else None) or r.get("translation") or "")[:600],
                        (r.get("doubts") or "")[:400], r.get("passage_id")])
    c = Counter(t[0] for t in rows)
    why = Counter(x for t in rows for x in t[1])
    print("scholar_translate.py  %s  the triage of %s%s, %s (read-only)" % (MARK_TRIAGE, a.doc, (" pages %s" % a.pages)
                                                                          if a.pages else "", a.engine))
    print("  not passed: %d; %s" % (len(rows), ", ".join("%s %d" % (k, c.get(k, 0)) for k in TIERS)))
    print("  accepted by a person: %d (not listed)" % accepted)
    for k, v in why.most_common(8):
        print("  why: %-40s %d" % (k, v))
    print("VERDICT: written %s (%d rows)" % (out, len(rows)))
    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (then --review with --verdict and --by, as you "
          "read them)" % a.doc)
    return 0
''')

edit(ST, 6, r'''    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
''', r'''    ap.add_argument("--triage", action="store_true", help="TRIAGE_2026_10_16: the verses of --engine not passed, sorted "
                    "for a person (exports/scholar_triage_<doc>.csv; free, read-only)")
    ap.add_argument("--only-flagged", default=None, metavar="ENGINE", help="TRIAGE_2026_10_16: read again only the "
                    "verses ENGINE did not pass")
    ap.add_argument("--serious", action="store_true", help="TRIAGE_2026_10_16: with --only-flagged, the rejected and "
                    "the serious only")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
''')

edit(ST, 7, r'''    if getattr(a, "rejudge", False):   # REJUDGE_2026_10_15
        return rejudge_main(a)
''', r'''    if getattr(a, "rejudge", False):   # REJUDGE_2026_10_15
        return rejudge_main(a)
    if getattr(a, "triage", False):   # TRIAGE_2026_10_16
        return triage_main(a)
''')

edit(ST, 8, r'''        done = latest_rows(con, a.doc, a.engine if getattr(a, "fill_engine", False) else None)   # PILOT_FIX_2026_10_15
''', r'''        done = latest_rows(con, a.doc, a.engine if getattr(a, "fill_engine", False) else None)   # PILOT_FIX_2026_10_15
        if getattr(a, "only_flagged", None):   # TRIAGE_2026_10_16: what another engine did not pass
            byid0 = {x["id"]: x for x in allp}
            fl = latest_rows(con, a.doc, a.only_flagged)
            want = ("rejected", "serious") if getattr(a, "serious", False) else TIERS
            a.only_ids = {pid for pid, r in fl.items() if pid in byid0 and current(r, byid0[pid])
                          and triage_of(r)[0] in want}
            mine = latest_rows(con, a.doc, a.engine)
            a.skip_ids = {pid for pid in a.only_ids if pid in mine and mine[pid]["id"] != fl[pid]["id"]
                          and current(mine[pid], byid0[pid])
                          and (mine[pid].get("created_at") or "") >= (fl[pid].get("created_at") or "")}
            done = latest_rows(con, a.doc, None)   # the context: every engine's rows
''')

edit(ST, 9, r'''    if getattr(a, "fill_engine", False):   # PILOT_FIX_2026_10_15
        print("  --fill-engine: only %s's own rows count as done and as the context" % a.engine)
''', r'''    if getattr(a, "fill_engine", False):   # PILOT_FIX_2026_10_15
        print("  --fill-engine: only %s's own rows count as done and as the context" % a.engine)
    if getattr(a, "only_flagged", None):   # TRIAGE_2026_10_16
        print("  --only-flagged: the verses %s did not pass%s: %d, read again by %s (%d of them already); the context: "
              "every engine's rows" % (a.only_flagged, " (the rejected and the serious)" if getattr(a, "serious", False)
                                      else "", len(a.only_ids), a.engine, len(a.skip_ids)))
''')

edit(ST, 10, r'''                 + ((" --compare-engine %s" % a.compare_engine) if a.compare_engine != COMPARE_ENGINE else ""), cap))
''', r'''                 + ((" --compare-engine %s" % a.compare_engine) if a.compare_engine != COMPARE_ENGINE else "")
                 + ((" --only-flagged %s" % a.only_flagged) if getattr(a, "only_flagged", None) else "")   # TRIAGE_2026_10_16
                 + (" --serious" if getattr(a, "serious", False) else ""), cap))
''')

edit(ST, 11, r'''        units = rejudge_targets(con, a, allp)
''', r'''        units = rejudge_targets(con, a, allp)
        jp = judge_price(con, a.judge_engine)   # TRIAGE_2026_10_16: as measured
''')

edit(ST, 12, r'''    est = JUDGE_COST_PRIOR * 2 * len(units)
''', r'''    byid_e = {x["id"]: x for x in allp}
    est = jp * sum(1 + (1 if all((byid_e[r["passage_id"]].get("english") or "").strip() for r in u) else 0) for u in units)
''')

edit(ST, 13, r'''            if budget_ok is not None and not budget_ok(con, JUDGE_COST_PRIOR * 2):
''', r'''            if budget_ok is not None and not budget_ok(con, jp * 2):
''')

edit(ST, 14, r'''MARK_REJUDGE = "REJUDGE_2026_10_15"
''', r'''MARK_REJUDGE = "REJUDGE_2026_10_15"
MARK_TRIAGE = "TRIAGE_2026_10_16"
JUDGE_COST_NOW = 0.0027   # TRIAGE_2026_10_16: gemini-2.5-flash with its thinking (15 Oct: 2,079 calls, $0.00274 each)


def judge_price(con, engine) -> float:
    """TRIAGE_2026_10_16: $ a judge call, as measured (usage_log, kind judge, this engine, since METERED_SINCE, 20 calls
    or more); else JUDGE_COST_NOW. JUDGE_COST_PRIOR (0.0002, 12 Oct) did not count the thinking."""
    try:
        n, avg = con.execute("SELECT COUNT(*), AVG(cost_usd) FROM usage_log WHERE kind = 'judge' AND engine = ? AND "
                             "ts >= ? AND cost_usd > 0", (engine, METERED_SINCE)).fetchone()
        if n and n >= 20:
            return float(avg)
    except sqlite3.Error:
        pass
    return JUDGE_COST_NOW
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
    if not Path("scripts/scholar_translate.py").exists():
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
        data = out.replace("\n", nl).encode("utf-8")
        if not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_triage_" + stamp))
        t = p.with_name(p.name + ".tmp_triage"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_triage_2026_10_16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
