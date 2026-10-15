#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_pilot_fix_2026_10_15.py  (2026-10-15)  PILOT_FIX_2026_10_15

After the pilot of 15 Oct, 15:18 to 15:40 IST (the Hayasirsa 20.5-21.4 on four engines; two runs stopped by Ctrl-C;
the head to head on five spans). Follows CLAUDE_ENGINE_2026_10_15 (88370ae).

scripts/scholar_translate.py:
  - ref_of: an OCR reading's verse_ref is a number it found, not a reference (the Hayasirsa's 20.10 was called "4", its
    sentence "20.5-4", its first verse "2"). A verse_ref counts where the edition numbers its verses (an e-text: etext,
    gretil, bori), or has a dot when the engine is not known; else page.idx;
  - --fill-engine: only this engine's own rows count as done, and only they are the context of the verses after: a
    run stopped half way goes on where it stopped, without --redo (which redoes all) and without another engine's
    English as its context. latest_rows takes an engine;
  - --compare-every N: the second judge (gemini-2.5-pro beside the working English) on one sentence in N, chosen by
    the hash of its first passage (not by its parity, which sets the order A/B); 1 (every one) as before;
  - the dry run says both; the NEXT line keeps them.
scripts/scholar_duel.py:
  - a span is its verses: a judge's reading counts as done by its rows, whatever the span was called when it was read,
    and the page shows one span for the same verses (the refs change with ref_of); --pick takes the old name too;
  - the tally: "best, its own model left out": the judge's ranking without the translations of its own model (the
    Opus judge chose Opus in three spans of five; the Gemini judge chose Sonnet in three).

Needs CLAUDE_ENGINE_2026_10_15 in both. Anchored, all-or-nothing, marker-idempotent per file; keeps line endings;
py_compile before the atomic replace; backups .bak_pilotfix_<date>.
  python scripts\\patch_pilot_fix_2026_10_15.py --check
  python scripts\\patch_pilot_fix_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "PILOT_FIX_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "CLAUDE_ENGINE_2026_10_15", "scripts/scholar_duel.py": "CLAUDE_ENGINE_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''COST_TRUTH_2026_10_15, CLAUDE_ENGINE_2026_10_15

A scholarly English''', r'''COST_TRUTH_2026_10_15, CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15

A scholarly English''')

edit(ST, 2, r'''--no-glossary-adds: a benchmark run. scripts/scholar_duel.py reads the engines side by side, blind.
''', r'''--no-glossary-adds: a benchmark run. scripts/scholar_duel.py reads the engines side by side, blind.

PILOT_FIX_2026_10_15: an OCR reading's verse_ref is not a reference (page.idx instead); --fill-engine goes on where a
run of this engine stopped, with only its own rows as done and as context; --compare-every N puts the second judge on
one sentence in N.
''')

edit(ST, 3, r'''def ref_of(x: dict) -> str:
    return str(x.get("ref") or "%s.%s" % (x.get("page"), x.get("idx")))
''', r'''REF_TRUSTED = ("etext", "gretil", "bori")   # PILOT_FIX_2026_10_15: the engines whose verse numbers are the edition's


def ref_of(x: dict) -> str:
    """The verse's reference: its verse_ref where the edition numbers its verses (an e-text), or one with a dot when the
    engine is not known; else page.idx. PILOT_FIX_2026_10_15: an OCR reading's verse_ref is a number it found (the
    Hayasirsa's 20.10 was called "4"), not a reference."""
    r = x.get("ref")
    eng = str(x.get("engine") or "").lower()
    if r and (any(k in eng for k in REF_TRUSTED) or (not eng and "." in str(r))):
        return str(r)
    return "%s.%s" % (x.get("page"), x.get("idx"))
''')

edit(ST, 4, r'''def latest_rows(con, doc: str) -> dict:
    """{passage_id: the latest scholar row} of this text."""
    if not has_table(con, "scholar_translations"):
        return {}
    cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM "
                      "scholar_translations WHERE doc_code = ? GROUP BY passage_id)", (doc, doc))
''', r'''def latest_rows(con, doc: str, engine=None) -> dict:
    """{passage_id: the latest scholar row} of this text (PILOT_FIX_2026_10_15: of one engine, when it is named)."""
    if not has_table(con, "scholar_translations"):
        return {}
    if engine:
        cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND engine = ? AND id IN (SELECT MAX(id) "
                          "FROM scholar_translations WHERE doc_code = ? AND engine = ? GROUP BY passage_id)",
                          (doc, engine, doc, engine))
    else:
        cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM "
                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id)", (doc, doc))
''')

edit(ST, 5, r'''    if getattr(a, "compare", False) and working:
        if asker.spent + call > a.max_usd:
''', r'''    if getattr(a, "compare", False) and working and compare_this(a, x):   # PILOT_FIX_2026_10_15: one in N
        if asker.spent + call > a.max_usd:
''')

edit(ST, 6, r'''def one_verse(a, allp, i, meta, done, asker, con, call: float) -> dict:
''', r'''def compare_this(a, x) -> bool:
    """PILOT_FIX_2026_10_15: whether the second judge reads this sentence (its first passage x): every one, or one in
    --compare-every, chosen by the hash of the passage id (its parity sets the order A/B in compare())."""
    n = max(1, int(getattr(a, "compare_every", 1) or 1))
    return n == 1 or int(src_hash("compare:%s" % x["id"]), 16) % n == 0


def one_verse(a, allp, i, meta, done, asker, con, call: float) -> dict:
''')

edit(ST, 7, r'''    ap.add_argument("--title", default=None, help="CLAUDE_ENGINE_2026_10_15: the text's name in the prompts")
''', r'''    ap.add_argument("--title", default=None, help="CLAUDE_ENGINE_2026_10_15: the text's name in the prompts")
    ap.add_argument("--fill-engine", action="store_true", help="PILOT_FIX_2026_10_15: only this engine's own rows count "
                    "as done and as context: a run stopped half way goes on where it stopped")
    ap.add_argument("--compare-every", type=int, default=1, help="PILOT_FIX_2026_10_15: the second judge on one sentence "
                    "in N (1: every one)")
''')

edit(ST, 8, r'''        done = latest_rows(con, a.doc)
        picked, left, skipped = choose(a, allp, done)
''', r'''        done = latest_rows(con, a.doc, a.engine if getattr(a, "fill_engine", False) else None)   # PILOT_FIX_2026_10_15
        picked, left, skipped = choose(a, allp, done)
''')

edit(ST, 9, r'''    if meta.get("agama"):   # CLAUDE_ENGINE_2026_10_15
        print("  the Agamas and Tantras: one rule more''', r'''    if getattr(a, "fill_engine", False):   # PILOT_FIX_2026_10_15
        print("  --fill-engine: only %s's own rows count as done and as the context" % a.engine)
    if a.compare and getattr(a, "compare_every", 1) > 1:
        print("  the second judge: one sentence in %d (--compare-every)" % a.compare_every)
    if meta.get("agama"):   # CLAUDE_ENGINE_2026_10_15
        print("  the Agamas and Tantras: one rule more''')

edit(ST, 10, r'''                 + (" --no-glossary-adds" if getattr(a, "no_glossary_adds", False) else "")
''', r'''                 + (" --no-glossary-adds" if getattr(a, "no_glossary_adds", False) else "")
                 + (" --fill-engine" if getattr(a, "fill_engine", False) else "")   # PILOT_FIX_2026_10_15
                 + ((" --compare-every %d" % a.compare_every) if getattr(a, "compare_every", 1) > 1 else "")
''')


SD = "scripts/scholar_duel.py"

edit(SD, 1, r'''scholar_duel.py  (2026-10-15)  CLAUDE_ENGINE_2026_10_15 (duel-v1)
''', r'''scholar_duel.py  (2026-10-15)  CLAUDE_ENGINE_2026_10_15 (duel-v1), PILOT_FIX_2026_10_15

PILOT_FIX_2026_10_15: a span is its verses (a reading counts as done by its rows, whatever the span was called; the page
shows one span for the same verses; --pick takes its old name too); the tally gives each judge's best with its own
model's translations left out.
''')

edit(SD, 2, r'''def already(con, doc: str, sref: str, judge: str, row_ids: dict) -> bool:
    want = json.dumps(row_ids, sort_keys=True)
    for (r,) in con.execute("SELECT row_ids FROM scholar_duels WHERE doc_code = ? AND span_ref = ? AND judge_engine = ? "
                            "AND prompt_version = ?", (doc, sref, judge, DUEL_VERSION)):
''', r'''def already(con, doc: str, sref: str, judge: str, row_ids: dict) -> bool:
    """PILOT_FIX_2026_10_15: the same rows read by the same judge, whatever the span was called then."""
    want = json.dumps(row_ids, sort_keys=True)
    for (r,) in con.execute("SELECT row_ids FROM scholar_duels WHERE doc_code = ? AND judge_engine = ? "
                            "AND prompt_version = ?", (doc, judge, DUEL_VERSION)):
''')

edit(SD, 3, r'''def canonical(con, doc: str) -> dict:
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
''', r'''def span_key(r) -> str:
    """PILOT_FIX_2026_10_15: a span is its verses."""
    return json.dumps(ST._loads(r.get("passage_ids"), []))


def canonical(con, doc: str, aliases=None) -> dict:
    """{span_ref: the judges' latest row with the most engines} (the rows the page shows), one for the same verses
    (PILOT_FIX_2026_10_15), under the name of its latest reading; aliases (a dict) gets every name a span was read
    under."""
    by = {}
    if not ST.has_table(con, "scholar_duels"):
        return {}
    cur = con.execute("SELECT * FROM scholar_duels WHERE doc_code = ? AND judge_engine NOT LIKE ? ORDER BY id",
                      (doc, PERSON + "%"))
    names = [d[0] for d in cur.description]
    seen = {}
    for r in cur.fetchall():
        r = dict(zip(names, r))
        k = span_key(r)
        seen.setdefault(k, set()).add(r["span_ref"])
        n = len(ST._loads(r.get("row_ids"), {}))
        old = by.get(k)
        if old is None or n >= len(ST._loads(old.get("row_ids"), {})):
            by[k] = r
    out = {r["span_ref"]: r for r in by.values()}
    if aliases is not None:
        for k, refs in seen.items():
            for ref in refs:
                aliases[ref] = by[k]["span_ref"]
    return out
''')

edit(SD, 4, r'''def pick(con, a) -> int:
    canon = canonical(con, a.doc)
    n = 0
    for part in [p.strip() for p in a.pick.split(",") if p.strip()]:
        sref, _, num = part.rpartition("=")
        c = canon.get(sref.strip())
''', r'''def pick(con, a) -> int:
    alias = {}
    canon = canonical(con, a.doc, alias)
    n = 0
    for part in [p.strip() for p in a.pick.split(",") if p.strip()]:
        sref, _, num = part.rpartition("=")
        c = canon.get(alias.get(sref.strip(), sref.strip()))   # PILOT_FIX_2026_10_15: its old name too
''')

edit(SD, 5, r'''        for d in alld:
            if d["span_ref"] != sref or json.dumps(ST._loads(d.get("row_ids"), {}), sort_keys=True) != want:
                continue
''', r'''        for d in alld:
            if span_key(d) != span_key(c) or json.dumps(ST._loads(d.get("row_ids"), {}), sort_keys=True) != want:
                continue   # PILOT_FIX_2026_10_15: the same verses, whatever the span was called
''')

edit(SD, 6, r'''                tj = t["judges"].setdefault(jn, {"best": 0, "rank": [], "fid": [], "prose": [], "notes": [], "major": 0})
                tj["best"] += 1 if v.get("best") == eng else 0
''', r'''                tj = t["judges"].setdefault(jn, {"best": 0, "rank": [], "fid": [], "prose": [], "notes": [], "major": 0,
                                                 "best_wo": 0})
                tj["best"] += 1 if v.get("best") == eng else 0
                tj["best_wo"] += 1 if best_without_own(v, jn) == eng else 0   # PILOT_FIX_2026_10_15
''')

edit(SD, 7, r'''        js = "".join('<td class="num">%d</td><td class="num">%s</td><td class="num">%s / %s / %s</td><td class="num">%d</td>'
                     % (t["judges"].get(j, {}).get("best", 0), _f(_mean(t["judges"].get(j, {}).get("rank", []))),
''', r'''        js = "".join('<td class="num">%d</td><td class="num">%d</td><td class="num">%s</td><td class="num">%s / %s / %s</td>'
                     '<td class="num">%d</td>'
                     % (t["judges"].get(j, {}).get("best", 0), t["judges"].get(j, {}).get("best_wo", 0),
                        _f(_mean(t["judges"].get(j, {}).get("rank", []))),
''')

edit(SD, 8, r'''    jh = "".join("<th>%s: best</th><th>mean rank</th><th>fidelity / prose / notes</th><th>major errors</th>" % e(j)
                 for j in judges)
''', r'''    jh = "".join("<th>%s: best</th><th>best, its own model left out</th><th>mean rank</th><th>fidelity / prose / notes</th>"
                 "<th>major errors</th>" % e(j) for j in judges)   # PILOT_FIX_2026_10_15
''')

edit(SD, 9, r'''def Counter_(it) -> dict:
''', r'''def _model(engine) -> str:
    return str(engine or "").split("@")[0]


def best_without_own(v: dict, judge: str):
    """PILOT_FIX_2026_10_15: the judge's best among the translations not made by its own model (any effort); None when
    it called them equal or ranked none else."""
    if not isinstance(v, dict) or v.get("best") == "equal":
        return None
    for eng in v.get("ranking") or []:
        if _model(eng) != _model(judge):
            return eng
    return None


def Counter_(it) -> dict:
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


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
        src, nl = load(p)
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
        shutil.copy2(p, p.with_name(p.name + ".bak_pilotfix_" + stamp))
        t = p.with_name(p.name + ".tmp_pilotfix"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_pilot_fix_2026_10_15 tests.test_claude_engine_2026_10_15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
