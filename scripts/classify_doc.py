#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_doc.py - the language/util classification stage of the pipeline.
(2026-08-29)

WHY THIS EXISTS
---------------
Many of our sources are not pure Sanskrit. A scanned edition typically carries
an English title page and preface, an English or Hindi commentary beside the
mula, running heads, page numbers and OCR crumbs. Until now the two classifiers
that recognise these -- classify_frontmatter.py (English body/front matter) and
classify_noise.py (OCR fragments) -- had to be remembered and run by hand from
the CLI, after the fact. If you forgot, the dashboard counted preface pages as
untranslated Sanskrit, the coverage percentage was wrong, and the translator
spent money on English prose it had no business translating.

This wraps both into ONE pipeline stage the dashboard chains automatically
after every ingest, so a freshly ingested book arrives already sorted into:

    mula        - the Sanskrit to translate
    frontmatter - genuine English/Hindi body text and front matter
    noise       - OCR fragments, page numbers, running heads

Nothing here re-cuts passage rows; it only labels them. The Library, reader,
QA panel and pipeline counters already exclude 'noise' and 'frontmatter' from
their denominators, so labelling is all that is needed to make every number in
the UI mean "real Sanskrit verses".

  python scripts/classify_doc.py --doc <CODE>            # dry run, shows counts
  python scripts/classify_doc.py --doc <CODE> --apply    # write the tags
  python scripts/classify_doc.py --apply                 # whole corpus
"""
from __future__ import annotations
import argparse, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

STAGES = [
    ("frontmatter", "classify_frontmatter.py",
     "English / Hindi body text and front matter"),
    ("noise", "classify_noise.py",
     "OCR fragments, page numbers, running heads"),
]


def run(script: str, argv: list[str]) -> int:
    cmd = [sys.executable, str(SCRIPTS / script)] + argv
    print(f"\n$ {' '.join(cmd[1:])}", flush=True)
    pr = subprocess.run(cmd, cwd=str(ROOT))
    return pr.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="limit to one doc code")
    ap.add_argument("--apply", action="store_true",
                    help="write the tags (default is a dry run)")
    args = ap.parse_args()

    scope = args.doc or "(whole corpus)"
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Classification stage: {scope}   [{mode}]")

    failed = []
    for label, script, what in STAGES:
        if not (SCRIPTS / script).exists():
            print(f"  [skip] {script} not present"); continue
        argv = ["--db", args.db]
        if args.doc:
            argv += ["--doc", args.doc]
        if args.apply:
            argv += ["--apply"]
        print(f"\n--- {label}: {what} ---")
        rc = run(script, argv)
        if rc != 0:
            failed.append((label, rc))
            print(f"  [WARN] {script} exited {rc}")

    # Report the resulting composition so the operator sees what the book IS,
    # not just that a job finished.
    try:
        import sqlite3
        con = sqlite3.connect(args.db, timeout=60)
        con.execute("PRAGMA busy_timeout=60000")
        con.execute("PRAGMA query_only=ON")
        where, params = "d.code NOT LIKE '%-RETIRED'", []
        if args.doc:
            where, params = "d.code = ?", [args.doc]
        rows = con.execute(
            f"""SELECT COALESCE(p.text_type,'mula'), COUNT(*)
                FROM passages p JOIN docs d ON d.id = p.doc_id
                WHERE {where} GROUP BY 1 ORDER BY 2 DESC""", params).fetchall()
        con.close()
        total = sum(n for _, n in rows) or 1
        print("\n" + "=" * 58)
        print(f"COMPOSITION{'' if not args.doc else ': ' + args.doc}")
        print("=" * 58)
        for tt, n in rows:
            bar = "#" * int(38 * n / total)
            print(f"  {tt:12s} {n:>7,} ({100.0*n/total:5.1f}%) {bar}")
        mula = dict(rows).get("mula", 0)
        print(f"\n  Translatable Sanskrit: {mula:,} of {total:,} passages "
              f"({100.0*mula/total:.1f}%).")
        if not args.apply:
            print("  (dry run - nothing was written. Re-run with --apply.)")
    except Exception as exc:
        print(f"  [warn] could not read composition: {exc}")

    if failed:
        print("\nStage(s) reported a non-zero exit: " +
              ", ".join(f"{l}(rc={r})" for l, r in failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
