#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_publish_engine_2026_10_07.py  (2026-10-07)  PUBLISH_ENGINE_2026_10_07

markandeya_purana went live on /texts (2026-10-07 16:1x) without the "translated with ..."
line that the Sandilya Bhakti Sutra shows, because --engine was not passed and
srangam_texts.translation_engine stayed NULL. All 1,258 of its translated passages record
the same engine (passages.engine = gemini:gemini-2.5-flash).

scripts/publish_srangam.py: when --engine is not given, the text row is labelled with the one
engine that every translated passage of the doc records. If they record more than one (or
none), nothing is guessed: the counts are printed and the label stays empty, as before.
The SQL bridge already keeps an existing label when a new one is NULL (COALESCE), so a
re-publish never erases one. Read-only on context.db, as before.

All-or-nothing, marker-idempotent, backup .bak_pubengine_<date>, py_compile.
  python scripts\\patch_publish_engine_2026_10_07.py --check
  python scripts\\patch_publish_engine_2026_10_07.py
Test: python -m unittest tests.test_publish_engine_2026_10_07 tests.test_publish_bridge -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "PUBLISH_ENGINE_2026_10_07"

HELPER = r'''# ----------------------------------------------------------------------------- PUBLISH_ENGINE_2026_10_07
def single_engine(con, doc_id):
    """The engine to label a text with when --engine is not given: the one engine that every
    translated passage of the doc records (passages.engine). None when they differ, when none is
    recorded, or when the column is absent; then the counts are printed and nothing is guessed."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    if "engine" not in cols:
        return None
    rows = [tuple(r) for r in con.execute(
        "SELECT engine, COUNT(*) FROM passages WHERE doc_id = ? AND TRIM(COALESCE(translation,'')) <> '' "
        "GROUP BY engine ORDER BY 2 DESC", (doc_id,))]
    if len(rows) == 1 and (rows[0][0] or "").strip():
        return rows[0][0].strip()
    if rows:
        print("note: the translated passages record %d engine label(s): %s - pass --engine to label the text"
              % (len(rows), ", ".join("%s x%d" % (e or "(none)", n) for e, n in rows)))
    return None


'''

EDITS = [
    ("helper", "def main():\n", HELPER + "def main():\n", 1),
    ("use it",
     '''    pages = len({r["page_no"] for r in rows})
    print(f"{args.doc}: {len(rows)} translated passages across {pages} pages")
''',
     '''    pages = len({r["page_no"] for r in rows})
    print(f"{args.doc}: {len(rows)} translated passages across {pages} pages")
    if args.engine is None:   # PUBLISH_ENGINE_2026_10_07
        args.engine = single_engine(con, doc["id"])
        if args.engine:
            print(f"{args.doc}: engine label {args.engine} (recorded by every translated passage)")
''', 1),
]
TARGETS = [(Path("scripts/publish_srangam.py"), EDITS)]


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
        t = p.with_name(p.name + ".tmp_pubengine")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_pubengine_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
