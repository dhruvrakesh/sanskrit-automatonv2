#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_audit_2026_10_15.py  (2026-10-15)  AUDIT_2026_10_15

Before the two Agamas go to claude-sonnet-5-5 whole (about 2,440 verses), an independent reading of a sample, and a
way to watch the runs. Follows PILOT_FIX_2026_10_15.

Why: in a Claude run the critic is the same model as the translator (a self-review), judge-v1 (gemini-2.5-flash) gave
5 of 5 to nearly every verse of the pilot, and the second judge needs a working English, which the Hayasirsa does not
have yet. So no other family read most of the verses.

scripts/scholar_translate.py:
  - --audit-every N (a Claude engine): after the critic has accepted (or the revisions are spent), Gemini's critic
    (--compare-engine, gemini-2.5-pro, the same critic prompt) reads the last version of one sentence in N, chosen by
    hash. Its reading is the last critique of the row, so it decides the status: a major issue, or fidelity or
    completeness below 4, flags it for a person; a source issue makes a source doubt. It does not revise. It is stored
    in the critique list with "by", and the pages say "The audit by ...". 0 (none) by default;
  - --status: per engine, what this text has (verses of those ready, passed, flagged, source doubts, stale, audited,
    $ spent, the last row's time) and the Claude credit; free and read-only, for watching a run from another window;
  - the dry run says the audit; the NEXT line keeps --audit-every; a run prints "[the audit: accept|revise]".

Needs PILOT_FIX_2026_10_15. Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the
atomic replace; backup .bak_audit_<date>.
  python scripts\\patch_audit_2026_10_15.py --check
  python scripts\\patch_audit_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "AUDIT_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "PILOT_FIX_2026_10_15"}
FILES = list(NEEDS)

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15

A scholarly English''', r'''CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15,
AUDIT_2026_10_15

A scholarly English''')

edit(ST, 2, r'''run of this engine stopped, with only its own rows as done and as context; --compare-every N puts the second judge on
one sentence in N.
''', r'''run of this engine stopped, with only its own rows as done and as context; --compare-every N puts the second judge on
one sentence in N.

AUDIT_2026_10_15: --audit-every N: in a Claude run, Gemini's critic (gemini-2.5-pro) reads the last version of one
sentence in N; its reading decides the status (a person reads what it flags). --status: what a text has, per engine
(free, read-only).
''')

edit(ST, 3, r'''    def judge(self, src: str, iast: str, english: str) -> tuple:
        return self.gem.judge(src, iast, english)
''', r'''    def judge(self, src: str, iast: str, english: str) -> tuple:
        return self.gem.judge(src, iast, english)

    def audit(self, base: str, cur: dict):
        """AUDIT_2026_10_15: Gemini's critic (--compare-engine) reads the last version: an independent reading of a
        Claude English. The critique, with "by"; None when it does not answer."""
        try:
            d, _c = self.gem.ask("critic", critic_message(base, cur))
        except CallFailed:
            return None
        c = clean_critique(d)
        if c is not None:
            c["by"] = self.gem.a.engine
        return c
''')

edit(ST, 4, r'''    final = crits[-1] if crits else None
    src = "\n".join((y["text"] or "").strip() for y in xs)
''', r'''    audit = None   # AUDIT_2026_10_15: another family reads the last version; its reading decides the status
    if getattr(a, "audit_every", 0) and hasattr(asker, "audit") and audit_this(a, x):
        if asker.spent + call > a.max_usd:
            note = "; ".join(s_ for s_ in (note, "not audited: --max-usd $%.2f would be passed" % a.max_usd) if s_)
        else:
            audit = asker.audit(base, cur)
            if audit is not None:
                crits.append(audit)
    final = crits[-1] if crits else None
    src = "\n".join((y["text"] or "").strip() for y in xs)
''')

edit(ST, 5, r'''                     "_glossary": cur["glossary"] if k == 0 and not getattr(a, "no_glossary_adds", False) else []})
''', r'''                     "_glossary": cur["glossary"] if k == 0 and not getattr(a, "no_glossary_adds", False) else [],
                     "_audit": audit["verdict"] if audit else None})   # AUDIT_2026_10_15
''')

edit(ST, 6, r'''def compare_this(a, x) -> bool:
''', r'''def audit_this(a, x) -> bool:
    """AUDIT_2026_10_15: whether Gemini's critic reads this sentence (its first passage x): one in --audit-every, by
    hash (another seed than the second judge's)."""
    n = int(getattr(a, "audit_every", 0) or 0)
    return n > 0 and (n == 1 or int(src_hash("audit:%s" % x["id"]), 16) % n == 0)


def status_lines(con, doc: str, allp: list, a) -> list:
    """AUDIT_2026_10_15: per engine, what this text has: verses (of those ready), passed, flagged, source doubts, stale,
    audited, $ spent, the last row's time."""
    pages = parse_pages(getattr(a, "pages", None))
    sel = [x for x in allp if pages is None or x["page"] in pages]
    ready = sum(1 for x in sel if not readiness(x["text"], x["type"], x["quality"], a.min_quality))
    ids = {x["id"] for x in sel}
    if not has_table(con, "scholar_translations"):
        return ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]
    text = {x["id"]: x["text"] for x in allp}
    per = {}
    for eng, pid, st_, h, crit, at in con.execute(
            "SELECT engine, passage_id, status, src_hash, critique, created_at FROM scholar_translations WHERE doc_code = ? "
            "AND id IN (SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY engine, passage_id)",
            (doc, doc)):
        if pid not in ids:
            continue
        e = per.setdefault(eng, {"n": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "stale": 0, "audited": 0,
                                 "last": ""})
        e["n"] += 1
        if text.get(pid) is None or src_hash(text.get(pid)) != h:
            e["stale"] += 1
        elif st_ in e:
            e[st_] += 1
        if '"by":' in (crit or ""):
            e["audited"] += 1
        e["last"] = max(e["last"], at or "")
    spent = dict(con.execute("SELECT engine, COALESCE(SUM(cost_usd), 0) FROM scholar_translations WHERE doc_code = ? "
                             "GROUP BY engine", (doc,)).fetchall())
    out = []
    for eng, e in sorted(per.items()):
        out.append("  %s: %s of %s verses (%d%%); passed %d, flagged %d, source doubts %d, stale %d; audited %d; %s spent "
                   "(all its rows here); the last at %s"
                   % (eng, "{:,}".format(e["n"]), "{:,}".format(ready), round(100.0 * e["n"] / max(1, ready)), e["passed"],
                      e["flagged"], e["source_doubt"], e["stale"], e["audited"], usd(spent.get(eng) or 0.0),
                      (e["last"] or "?")[:16].replace("T", " ")))
    return out or ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]


def compare_this(a, x) -> bool:
''')

edit(ST, 7, r'''                     ("  [the second judge: %s]" % rec["compare_better"]) if rec.get("compare_better") else ""))
''', r'''                     (("  [the second judge: %s]" % rec["compare_better"]) if rec.get("compare_better") else "")
                     + (("  [the audit: %s]" % rec["_audit"]) if rec.get("_audit") else "")))   # AUDIT_2026_10_15
''')

edit(ST, 8, r'''        iss += ('<div>Critic, reading %d: fidelity %s, completeness %s, %s%s</div>'
                % (k, c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                   ('<ul class="iss">%s</ul>' % items) if items else ""))
''', r'''        iss += ('<div>%s: fidelity %s, completeness %s, %s%s</div>'
                % (("Critic, reading %d" % k) if not c.get("by") else ("The audit by %s" % e(str(c["by"]))),
                   c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                   ('<ul class="iss">%s</ul>' % items) if items else ""))   # AUDIT_2026_10_15
''')

edit(ST, 9, r'''            iss += ('<div>Critic, reading %d: fidelity %s, completeness %s, %s%s</div>'
                    % (k, c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                       ('<ul class="iss">%s</ul>' % items) if items else ""))
''', r'''            iss += ('<div>%s: fidelity %s, completeness %s, %s%s</div>'
                    % (("Critic, reading %d" % k) if not c.get("by") else ("The audit by %s" % e(str(c["by"]))),
                       c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                       ('<ul class="iss">%s</ul>' % items) if items else ""))   # AUDIT_2026_10_15
''')

edit(ST, 10, r'''    ap.add_argument("--compare-every", type=int, default=1, help="PILOT_FIX_2026_10_15: the second judge on one sentence "
                    "in N (1: every one)")
''', r'''    ap.add_argument("--compare-every", type=int, default=1, help="PILOT_FIX_2026_10_15: the second judge on one sentence "
                    "in N (1: every one)")
    ap.add_argument("--audit-every", type=int, default=0, help="AUDIT_2026_10_15: in a Claude run, Gemini's critic reads "
                    "one sentence in N after the critic; its reading decides the status (0: none)")
    ap.add_argument("--status", action="store_true", help="AUDIT_2026_10_15: what this text has, per engine (free)")
''')

edit(ST, 11, r'''    if a.review or a.term:
        if a.review and not a.by:
''', r'''    if getattr(a, "status", False):   # AUDIT_2026_10_15: free, read-only
        con = open_ro(a.db)
        try:
            allp = load_text(con, a.doc)
            lines = status_lines(con, a.doc, allp, a)
            cl = ""
            if any(" anthropic:" in ln for ln in lines) or claude:
                try:
                    import claude_engine
                    cl = claude_engine.credit_line(claude_engine.credit(con))
                except Exception:
                    cl = ""
        finally:
            con.close()
        print("scholar_translate.py  %s  the status of %s%s (read-only)" % (MARK, a.doc, (" pages %s" % a.pages) if a.pages
                                                                            else ""))
        for ln in lines:
            print(ln)
        if cl:
            print("  " + cl)
        print("VERDICT: %d engine(s) here" % sum(1 for ln in lines if ln.startswith("  ") and " verses (" in ln))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (the pages: the flagged first to read)" % a.doc)
        return 0
    if a.review or a.term:
        if a.review and not a.by:
''')

edit(ST, 12, r'''    if a.compare and getattr(a, "compare_every", 1) > 1:
        print("  the second judge: one sentence in %d (--compare-every)" % a.compare_every)
''', r'''    if a.compare and getattr(a, "compare_every", 1) > 1:
        print("  the second judge: one sentence in %d (--compare-every)" % a.compare_every)
    if getattr(a, "audit_every", 0):   # AUDIT_2026_10_15
        print("  the audit: %s" % (("%s reads one sentence in %d after the critic; its reading decides the status"
                                    % (a.compare_engine, a.audit_every)) if claude else
                                   "--audit-every is for a Claude engine: nothing is audited"))
''')

edit(ST, 13, r'''                 + ((" --compare-every %d" % a.compare_every) if getattr(a, "compare_every", 1) > 1 else "")
''', r'''                 + ((" --compare-every %d" % a.compare_every) if getattr(a, "compare_every", 1) > 1 else "")
                 + ((" --audit-every %d" % a.audit_every) if getattr(a, "audit_every", 0) else "")   # AUDIT_2026_10_15
                 + ((" --min-quality %.2f" % a.min_quality) if a.min_quality != 0.35 else "")
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
        shutil.copy2(p, p.with_name(p.name + ".bak_audit_" + stamp))
        t = p.with_name(p.name + ".tmp_audit"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_audit_2026_10_15 tests.test_pilot_fix_2026_10_15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
