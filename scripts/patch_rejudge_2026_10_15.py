#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_rejudge_2026_10_15.py  (2026-10-15)  REJUDGE_2026_10_15

Gemini checks a Claude English (Dhruv, 15 Oct, evening): the judge of every verse stays Gemini's (gemini-2.5-flash, a
reading from another family); the audit and the second judge go to claude-opus-5-5 on the Claude credit. The verses
that a Claude judge (claude-haiku-5-5) read between 18:47 and the switch get the Gemini reading after all: CF2.
Follows CLAUDE_FIRST_2026_10_15.

scripts/scholar_translate.py, --rejudge (with --engine anthropic:..., the run whose rows are read again):
  - the latest row of each verse of that engine whose judge was a Claude model, the Sanskrit unchanged, not reviewed
    by a person (a person's reading stands), within --pages; one sentence (its group) read whole, as it was made;
  - --judge-engine (gemini-2.5-flash) reads it again, and the working English where there is one;
  - its status is decided again as a run decides it (the last critique, the audit included; the judge; a major error
    of the second judge's), and stored as a new version of each verse: the same English, notes, critique and
    comparison; the new scores, judge_engine and status; the reason says what it was ("[re-judged; was ...]");
  - a verse redone meanwhile (a newer row of that engine) is left alone; a judge that does not answer leaves the row
    as it was;
  - Google's spend cap gates it; the dry run (no --yes) counts and prices it, free.

Needs CLAUDE_FIRST_2026_10_15. Anchored, all-or-nothing, marker-idempotent; keeps line endings; ASCII; py_compile
before the atomic replace; backup .bak_rejudge_<date>.
  python scripts\\patch_rejudge_2026_10_15.py --check
  python scripts\\patch_rejudge_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REJUDGE_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "CLAUDE_FIRST_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15
''', r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15, REJUDGE_2026_10_15
''')

edit(ST, 2, r'''Claude credit only (Google's spend cap is not consulted, no Gemini key is needed).
''', r'''Claude credit only (Google's spend cap is not consulted, no Gemini key is needed).

REJUDGE_2026_10_15: --rejudge: the Gemini judge (--judge-engine) reads again the verses of a Claude run (--engine) that
a Claude judge read, and decides their status again; a new version of each, the same English.
''')

edit(ST, 3, r'''    ap.add_argument("--status", action="store_true", help="AUDIT_2026_10_15: what this text has, per engine (free)")
''', r'''    ap.add_argument("--status", action="store_true", help="AUDIT_2026_10_15: what this text has, per engine (free)")
    ap.add_argument("--rejudge", action="store_true", help="REJUDGE_2026_10_15: the Gemini judge reads again the verses "
                    "of --engine that a Claude judge read (a new version of each, the same English)")
''')

edit(ST, 4, r'''    if a.review or a.term:
''', r'''    if getattr(a, "rejudge", False):   # REJUDGE_2026_10_15
        return rejudge_main(a)
    if a.review or a.term:
''')

edit(ST, 5, r'''def main(argv=None) -> int:
''', r'''MARK_REJUDGE = "REJUDGE_2026_10_15"


def rejudge_targets(con, a, allp: list) -> list:
    """REJUDGE_2026_10_15: the sentences to read again, in order: the latest row of each verse of --engine whose judge
    was a Claude model, the Sanskrit unchanged, not reviewed, within --pages; [[row, ...], ...] (a sentence whole)."""
    pages = parse_pages(getattr(a, "pages", None))
    byid = {x["id"]: x for x in allp}
    rows = [r for r in latest_rows(con, a.doc, a.engine).values()
            if is_claude(r.get("judge_engine")) and not r.get("review_verdict")
            and r["passage_id"] in byid and current(r, byid[r["passage_id"]])
            and (pages is None or r.get("page_no") in pages)]
    rows.sort(key=lambda r: (r.get("page_no") or 0, r.get("idx") or 0))
    return _units(rows)


def still_latest(con, r: dict) -> bool:
    """REJUDGE_2026_10_15: no newer row of this verse and engine was made since it was chosen."""
    got = con.execute("SELECT MAX(id) FROM scholar_translations WHERE passage_id = ? AND engine = ?",
                      (r["passage_id"], r["engine"])).fetchone()[0]
    return got == r["id"]


def rejudge_unit(asker, unit: list, byid: dict) -> list:
    """REJUDGE_2026_10_15: one sentence read again by asker's judge: the new rows to store (the same English, notes,
    critique, comparison; the new scores, judge_engine, status, the reason saying what it was), or [] when the judge
    does not answer."""
    xs = [byid[r["passage_id"]] for r in unit]
    r0 = unit[0]
    english = ((r0.get("group_translation") if r0.get("group_ref") else None)
               or " ".join((r.get("translation") or "").strip() for r in unit))
    src = "\n".join((x["text"] or "").strip() for x in xs)
    ia = "\n".join(iast_of(x) for x in xs)
    spent0 = asker.spent
    fid, flu, why, _c = asker.judge(src, ia, english)
    if fid is None or flu is None:
        return []
    wk = [(x.get("english") or "").strip() for x in xs]
    working = " ".join(wk) if all(wk) else ""
    wfid = wflu = None
    if working:
        wfid, wflu, _w, _c = asker.judge(src, ia, working)
    crits = _loads(r0.get("critique"), [])
    final = crits[-1] if crits and isinstance(crits[-1], dict) else None
    st = status_of(final, fid, flu)
    cmp_ = _loads(r0.get("compare"), {})
    if st == "passed" and any(e_.get("severity") == "major" for e_ in ((cmp_.get("scholarly") or {}).get("errors") or [])):
        st = "flagged"   # the second judge found a major error in it, as a run decides
    cost = asker.spent - spent0
    at = now()
    was = "%s %s/%s, %s" % (r0.get("judge_engine"), r0.get("fidelity"), r0.get("fluency"), r0.get("status"))
    out = []
    for r in unit:
        rec = {c: r.get(c) for c in COLS}
        rec.update(fidelity=fid, fluency=flu, judge_reason=("[re-judged; was %s] %s" % (was, why or ""))[:200],
                   working_fidelity=wfid, working_fluency=wflu, status=st, judge_engine=asker.a.judge_engine,
                   cost_usd=round(cost / len(unit), 6), created_at=at)
        out.append(rec)
    return out


def rejudge_main(a) -> int:
    """REJUDGE_2026_10_15 (CF2): the Gemini judge reads again what a Claude judge read; the dry run counts it, free."""
    if not is_claude(a.engine):
        print("REFUSE: --rejudge reads the rows of a Claude run: --engine anthropic:..."); print("VERDICT: nothing sent")
        print("NEXT: "); return 1
    if is_claude(a.judge_engine):
        print("REFUSE: --rejudge is a Gemini judge's (--judge-engine %s, the default)" % JUDGE)
        print("VERDICT: nothing sent"); print("NEXT: "); return 1
    con = open_ro(a.db)
    try:
        allp = load_text(con, a.doc)
        meta = doc_meta(con, a.doc, allp, Path(a.db).resolve().parent / "raw")
        units = rejudge_targets(con, a, allp)
    finally:
        con.close()
    units = units[:max(0, int(a.limit))]
    n = sum(len(u) for u in units)
    est = JUDGE_COST_PRIOR * 2 * len(units)
    print("scholar_translate.py  %s  %s   the judge %s reads again the verses of %s that a Claude judge read"
          % (MARK_REJUDGE, "RUN" if a.yes else "DRY RUN (nothing called, nothing written)", a.judge_engine, a.engine))
    print("  %s%s: %d sentence(s), %d verse(s); about %s (Google's bill, in the spend cap)"
          % (a.doc, (" pages %s" % a.pages) if a.pages else "", len(units), n, usd(est)))
    if not units:
        print("VERDICT: nothing to read again")
        print("NEXT: python scripts\\scholar_translate.py --doc %s --status" % a.doc)
        return 0
    if not a.yes:
        print("VERDICT: %d verse(s) to read again, about %s" % (n, usd(est)))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --engine %s --rejudge%s --limit %d --yes"
              % (a.doc, a.engine, (" --pages %s" % a.pages) if a.pages else "", max(int(a.limit), len(units))))
        return 0
    try:
        gem = Gemini(a, meta, None)   # the judge only (--judge-engine); without the key nothing is called
    except RuntimeError as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing called, nothing written"); print("NEXT: "); return 1
    import db_utils
    con = db_utils.connect(a.db)
    done = moved = unanswered = 0
    stopped, changes = "", []
    try:
        gem.con = con
        ensure_schema(con)
        try:
            from usage_meter import budget_ok
        except Exception:
            budget_ok = None
        byid = {x["id"]: x for x in load_text(con, a.doc)}
        for k, u in enumerate(units, 1):
            if budget_ok is not None and not budget_ok(con, JUDGE_COST_PRIOR * 2):
                stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
            if not all(r["passage_id"] in byid and current(r, byid[r["passage_id"]]) and still_latest(con, r) for r in u):
                moved += 1
                continue
            recs = rejudge_unit(gem, u, byid)
            if not recs:
                unanswered += 1
                print("  (%d/%d) %s: the judge did not answer; the row stays as it was"
                      % (k, len(units), u[0].get("verse_ref")))
                continue
            for rec in recs:
                store(con, rec)
            done += 1
            ref = str(u[0].get("verse_ref")) + (("-%s" % u[-1].get("verse_ref")) if len(u) > 1 else "")
            if recs[0]["status"] != u[0].get("status"):
                changes.append("%s %s->%s" % (ref, u[0].get("status"), recs[0]["status"]))
            print("  (%d/%d) %s  %-12s fidelity %s, fluency %s (was %s/%s by %s)"
                  % (k, len(units), ref, recs[0]["status"], recs[0]["fidelity"], recs[0]["fluency"],
                     u[0].get("fidelity"), u[0].get("fluency"), u[0].get("judge_engine")))
    finally:
        con.close()
    if stopped:
        print("  STOPPED: %s" % stopped)
    print("VERDICT: %d sentence(s) read again; %d changed status%s; %d redone meanwhile, left alone; %d not answered; "
          "%s spent" % (done, len(changes), (" (%s)" % ", ".join(changes[:20])) if changes else "", moved, unanswered,
                        usd(gem.spent)))
    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (the flagged first to read)" % a.doc)
    return 0


def main(argv=None) -> int:
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
        shutil.copy2(p, p.with_name(p.name + ".bak_rejudge_" + stamp))
        t = p.with_name(p.name + ".tmp_rejudge"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_rejudge_2026_10_15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
