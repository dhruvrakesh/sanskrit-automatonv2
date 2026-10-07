#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_booksmith_stories_2026_10_07.py  (2026-10-07)  BOOKSMITH_STORIES_2026_10_07

booksmith_build.py can build a book from a witness it did not export: a story
collection written by `stories.py booksmith-source`. Additive; every existing
call (--doc X --mode tri|en|hi) runs exactly as before.

  --source-html FILE   use this witness; skip step 1 (export_html)
  --mode story         reading languages sanskrit, english, hindi (no IAST: a
                       retelling has none); only with --source-html
  --plate-ids 12,15    plates = these APPROVED images, in this order (implies
                       plates; Booksmith places them evenly, at most 12)

Verified 2026-10-07 against a copy of Booksmith 0.2.1: init, ingest (one leaf
per story, mode=leaf), audit (0 issues), build (book.pdf, release record).

All-or-nothing, marker-idempotent, backup .bak_bsstory_<date>, py_compile.
  python scripts\\patch_booksmith_stories_2026_10_07.py --check
  python scripts\\patch_booksmith_stories_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "BOOKSMITH_STORIES_2026_10_07"

EDITS = [
    ("story mode",
     '''            ["sanskrit", "iast", "hindi"]),
}
''',
     '''            ["sanskrit", "iast", "hindi"]),
    # BOOKSMITH_STORIES_2026_10_07: a story collection (stories.py booksmith-source); --source-html only
    "story": ([], "", ["sanskrit", "english", "hindi"]),
}
''', 1),
    ("plates from given images",
     '''def sync_plates(bs: Path, project: Path, db: str, doc: str, config_io=None) -> dict:
''',
     '''def images_by_ids(db: str, ids: list) -> list[dict]:
    """BOOKSMITH_STORIES_2026_10_07: APPROVED images with these ids, in the order given. Read-only."""
    import sqlite3
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        con.execute("PRAGMA query_only=1")
        got = {r[0]: r for r in con.execute(
            "SELECT id, version, path, anchor_page, anchor_idx FROM doc_images WHERE status='approved' "
            "AND path IS NOT NULL AND id IN (%s)" % ",".join("?" * len(ids)), list(ids))} if ids else {}
    finally:
        con.close()
    out = []
    for i in ids:
        if i in got:
            iid, ver, path, pg, ix = got[i]
            src = Path(path) if os.path.isabs(path) else ROOT / path
            out.append({"id": iid, "version": ver, "src": src, "page": pg, "idx": ix})
    return out


def sync_plates(bs: Path, project: Path, db: str, doc: str, config_io=None, images=None) -> dict:
''', 1),
    ("images argument used",
     '''    images = approved_generated_images(db, doc)
''',
     '''    images = approved_generated_images(db, doc) if images is None else images   # BOOKSMITH_STORIES_2026_10_07
''', 1),
    ("arguments",
     '''    ap.add_argument("--selftest", action="store_true")
''',
     '''    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--source-html", default=None,
                    help="BOOKSMITH_STORIES_2026_10_07: build this witness instead of exporting --doc")
    ap.add_argument("--plate-ids", default=None, help="approved image ids, in order, as the plates")
''', 1),
    ("story mode needs a witness",
     '''    doc = args.doc
''',
     '''    doc = args.doc
    if args.mode == "story" and not args.source_html:   # BOOKSMITH_STORIES_2026_10_07
        raise SystemExit("--mode story needs --source-html (python scripts\\\\stories.py booksmith-source ...)")
''', 1),
    ("given witness",
     '''        log("[1/6] export HTML")
        html = export_html(args.db, doc, args.mode, exports)
''',
     '''        if args.source_html:   # BOOKSMITH_STORIES_2026_10_07
            log("[1/6] witness given (--source-html); nothing exported")
            html = Path(args.source_html).resolve()
            if not html.is_file():
                raise RuntimeError("no such witness: %s" % html)
        else:
            log("[1/6] export HTML")
            html = export_html(args.db, doc, args.mode, exports)
''', 1),
    ("plates by id",
     '''        if args.plates == "approved":   # BOOKSMITH_PLATES_2026_10_04
''',
     '''        if args.plates == "approved" or args.plate_ids:   # BOOKSMITH_PLATES_2026_10_04 / BOOKSMITH_STORIES
''', 1),
    ("plates call",
     '''            state["plates"] = sync_plates(exe, project, args.db, doc)
''',
     '''            state["plates"] = sync_plates(exe, project, args.db, doc, images=(
                images_by_ids(args.db, [int(x) for x in re.findall(r"\\d+", args.plate_ids)])
                if args.plate_ids else None))
''', 1),
]

TARGETS = [(Path("scripts/booksmith_build.py"), EDITS)]


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
        t = p.with_name(p.name + ".tmp_bsstory")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_bsstory_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
