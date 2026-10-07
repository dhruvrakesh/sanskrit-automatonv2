#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_doc_hint_2026_10_07.py  (2026-10-07)  DOC_HINT_2026_10_07

`python scripts\\corpus_status.py --doc Ganita_Yukti_Bhasa` printed an empty table and
"0 docs" with no word of why (2026-10-07 14:30). The code is
Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V; the shorter name came from my own command.
Worse, had every --doc been unknown, an empty list would have fallen through to
"all docs" in collect().

corpus_status now checks each --doc against the docs table first:
  * exact code                                  -> used
  * same code, other case                        -> used, with a note
  * exactly one code starts with what was given  -> used, with a note naming it
  * otherwise                                    -> a note with the closest codes
If no --doc is left, it stops (exit 2) instead of reporting everything. Notes start
with "# " so a copied --commands block stays runnable. Read-only, as before.

All-or-nothing, marker-idempotent, backup .bak_dochint_<date>, py_compile.
  python scripts\\patch_doc_hint_2026_10_07.py --check
  python scripts\\patch_doc_hint_2026_10_07.py
Test: python -m unittest tests.test_doc_hint_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "DOC_HINT_2026_10_07"

HELPER = r'''# ------------------------------------------------------------------ DOC_HINT_2026_10_07
def resolve_docs(db: str, wanted: list | None) -> tuple:
    """(codes to report, notes). Each --doc is checked against the docs table: an exact code is used;
    another case of a code, or the only code that starts with what was given, is used with a note;
    anything else gets a note with the closest codes. 2026-10-07: '--doc Ganita_Yukti_Bhasa' printed
    '0 docs' with no reason (the code is Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V)."""
    if not wanted:
        return wanted, []
    import difflib
    con = open_ro(db)
    try:
        codes = [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code")]
    finally:
        con.close()
    have, low = set(codes), {c.lower(): c for c in codes}
    out, notes = [], []
    for w in wanted:
        lw = w.lower()
        if w in have:
            out.append(w)
        elif lw in low:
            out.append(low[lw]); notes.append("# note: --doc %s -> %s (case)" % (w, low[lw]))
        else:
            pre = [c for c in codes if c.lower().startswith(lw)]
            if len(pre) == 1:
                out.append(pre[0]); notes.append("# note: --doc %s is not a code; using %s" % (w, pre[0]))
            else:
                toks = [t for t in re.split(r"[^0-9a-z]+", lw) if t]
                near = pre[:8] or [c for c in codes if lw in c.lower()][:8] \
                    or [c for c in codes if toks and all(t in c.lower() for t in toks)][:8] \
                    or difflib.get_close_matches(w, codes, n=5, cutoff=0.5)
                notes.append("# note: no text has the code %r.%s" % (
                    w, (" Did you mean: " + ", ".join(near)) if near else " Run without --doc to list every text."))
    return out, notes


'''

EDITS = [
    ("helper", "def main() -> int:\n", HELPER + "def main() -> int:\n", 1),
    ("main check",
     '''        print("FAIL: %s not found. Run from the repo root." % args.db); return 2

    stats, (en_ver, hi_ver, hi_src), peers, cpp = collect(
''',
     '''        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    if args.doc:   # DOC_HINT_2026_10_07
        args.doc, _notes = resolve_docs(args.db, args.doc)
        for _n in _notes:
            print(_n)
        if not args.doc:
            print("# nothing to report: no --doc matched a text."); return 2

    stats, (en_ver, hi_ver, hi_src), peers, cpp = collect(
''', 1),
]
TARGETS = [(Path("scripts/corpus_status.py"), EDITS)]


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
        t = p.with_name(p.name + ".tmp_dochint")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_dochint_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
