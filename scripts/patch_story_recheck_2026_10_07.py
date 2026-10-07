#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_story_recheck_2026_10_07.py  (2026-10-07)  STORY_RECHECK_2026_10_07

Why most drafts on /stories read "check failed": the stored check result is the one
made when the story was written. Stories #3-#13 of markandeya_purana were written at
19:45 on 2026-10-05, BEFORE the verify fix of STORIES_UI_2026_10_05 (a citation after
the full stop no longer glues two sentences; "Later", "Simultaneously" are no longer
taken for names). Their stored results were never recomputed, so they still fail, and
with nothing approved the book and graphic-novel buttons stay disabled.

scripts/stories.py
  verify-all --doc CODE [--status draft,approved]
      Re-runs the check (no API, free) on every written story of the text and on its
      versions for younger readers, with the same window the page and write_story use
      (60 passages), stores the result, and prints what changed: now passing, still
      failing (with the first problem), unchanged. Nothing is approved by it.
  The single `verify --id N` now uses the same 60-passage window (it used 40, so a
  long episode could be reported as citing outside its own range).

All-or-nothing, marker-idempotent, backup .bak_recheck_<date>, py_compile.
  python scripts\\patch_story_recheck_2026_10_07.py --check
  python scripts\\patch_story_recheck_2026_10_07.py
Test: python -m unittest tests.test_heal_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "STORY_RECHECK_2026_10_07"

BLOCK = r'''# ------------------------------------------------------------------ STORY_RECHECK_2026_10_07
def verify_all(con, code: str, statuses=("draft", "approved")) -> dict:
    """Re-run the check on every written story of a text (and its versions for younger readers).
    No API call. Stores each result; approves nothing. Returns a summary."""
    did = im.doc_id(con, code)
    rows = passages(con, code)
    out = {"checked": 0, "ok": 0, "failed": 0, "now_ok": [], "now_failing": [], "still_failing": [], "variants": 0}
    ph = ",".join("?" * len(statuses))
    ids = [r[0] for r in con.execute(
        "SELECT id FROM doc_stories WHERE doc_id=? AND status IN (%s) AND TRIM(COALESCE(story_en,''))<>'' "
        "ORDER BY from_page, from_idx, id" % ph, (did, *statuses))]
    for sid in ids:
        s = _row(con, sid)
        given = window(rows, (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=2, cap=60)
        v = verify(s, given)
        try:
            was = (json.loads(s.get("verify") or "null") or {}).get("ok")
        except ValueError:
            was = None
        con.execute("UPDATE doc_stories SET verify=?, updated_at=? WHERE id=?", (json.dumps(v), now(), sid))
        out["checked"] += 1
        out["ok" if v["ok"] else "failed"] += 1
        if v["ok"] and not was:
            out["now_ok"].append(sid)
        elif not v["ok"] and was:
            out["now_failing"].append((sid, v["problems"][0] if v["problems"] else ""))
        elif not v["ok"]:
            out["still_failing"].append((sid, v["problems"][0] if v["problems"] else ""))
        vt = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "doc_story_variants" in vt:
            for (vid,) in con.execute("SELECT id FROM doc_story_variants WHERE story_id=? AND status IN ('draft','approved')",
                                      (sid,)).fetchall():
                cols = [c[1] for c in con.execute("PRAGMA table_info(doc_story_variants)")]
                vrow = dict(zip(cols, con.execute("SELECT * FROM doc_story_variants WHERE id=?", (vid,)).fetchone()))
                vv = variant_verify(con, s, vrow)
                con.execute("UPDATE doc_story_variants SET verify=?, updated_at=? WHERE id=?", (json.dumps(vv), now(), vid))
                out["variants"] += 1
    con.commit()
    return out


# ------------------------------------------------------------------ CLI
'''

EDITS = [
    ("verify_all", "# ------------------------------------------------------------------ CLI\n", BLOCK, 1),
    ("cli parser",
     '''    v = sub.add_parser("verify"); v.add_argument("--id", type=int, required=True)
''',
     '''    v = sub.add_parser("verify"); v.add_argument("--id", type=int, required=True)
    va_ = sub.add_parser("verify-all"); va_.add_argument("--doc", required=True)   # STORY_RECHECK_2026_10_07
    va_.add_argument("--status", default="draft,approved", help="comma list, default draft,approved")
''', 1),
    ("cli dispatch",
     '''        if args.cmd == "verify":
''',
     '''        if args.cmd == "verify-all":   # STORY_RECHECK_2026_10_07
            sts = tuple(x.strip() for x in args.status.split(",") if x.strip() in ("draft", "approved"))
            r = verify_all(con, args.doc, sts or ("draft", "approved"))
            print("checked %d stor(ies) of %s (and %d version(s) for younger readers): %d pass, %d fail. No API call."
                  % (r["checked"], args.doc, r["variants"], r["ok"], r["failed"]))
            if r["now_ok"]:
                print("  now passing (read, then approve): " + ", ".join("#%d" % i for i in r["now_ok"]))
            for i, p in r["now_failing"]:
                print("  NOW FAILING #%d: %s" % (i, p))
            for i, p in r["still_failing"]:
                print("  still failing #%d: %s" % (i, p))
            return 0
        if args.cmd == "verify":
''', 1),
    ("single verify uses the same window",
     '''            rows = window(passages(con, _code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                          (s["to_page"], s["to_idx"]), pad=2)
''',
     '''            rows = window(passages(con, _code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                          (s["to_page"], s["to_idx"]), pad=2, cap=60)   # STORY_RECHECK_2026_10_07: as write and the page
''', 1),
]

TARGETS = [(Path("scripts/stories.py"), EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_recheck")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_recheck_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
