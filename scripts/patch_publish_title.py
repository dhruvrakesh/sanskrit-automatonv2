#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_publish_title.py - publish_srangam.py queries a column that does not
exist. (B2c, 2026-09-06)

THE CRASH
    sqlite3.OperationalError: no such column: d.title
    publish_srangam.py:114  list_docs()

THE CAUSE
db_utils.py, the schema of record:

    CREATE TABLE IF NOT EXISTS docs(
      id, code, category, src_path, glossary, created_at
    );

There is no `title`. The publisher was written on 2026-07-18 and recorded in
APPS_AND_CORPUS_INTEGRATION as "delivered and tested", but `--list` crashes on
the first statement it runs, so it was never executed against this database. It
sat inert for seven weeks with a bug in its front door.

That is worth naming plainly, because the same document says the B1 migration is
"delivered and tested" too — and B1 has never been applied to Supabase either.
"Delivered" and "verified against the live system" are different claims, and
this file is the evidence.

THE FIX
`title` is genuinely useful on the srangam side (srangam_texts.title is NOT
NULL), so rather than drop it, derive it from the data that does exist. The
automaton's doc codes are human-derived already:

    2015_405693_Shatpath-Brahmanam        -> Shatpath Brahmanam
    Karan_Aagama_by_Prof_Rama_Chandra...  -> Karan Aagama by Prof Rama Chandra...
    476948-Rgveda-samhita                 -> Rgveda samhita
    wl_buddha_carita_sanskrit             -> Buddha Carita Sanskrit

doc_title() strips a leading numeric accession block, replaces separators with
spaces, collapses whitespace and title-cases only words that are already
lowercase (so 'Rgveda' and roman numerals survive). It is a display label, not
an identity: doc_code remains the key on both sides.

  python scripts\\patch_publish_title.py            # dry run
  python scripts\\patch_publish_title.py --apply
  python scripts\\publish_srangam.py --list
"""
from __future__ import annotations
import argparse, io, os, py_compile, shutil, sys, time

MARKER = "PUBLISH_TITLE_2026_09_06"
PUB = os.path.join("scripts", "publish_srangam.py")

HELPER = '''

# ── Display title (PUBLISH_TITLE_2026_09_06) ─────────────────────────────────
# `docs` has no `title` column (db_utils.py: id, code, category, src_path,
# glossary, created_at). publish_srangam.py asked for d.title and crashed on
# its own --list. srangam_texts.title is NOT NULL, so derive a label from the
# code rather than drop the column.
import re as _title_re

_TITLE_LEAD_ACCESSION = _title_re.compile(r"^(?:\\d{4}[_-])?\\d{4,}[_-]")
_TITLE_SEPS = _title_re.compile(r"[_\\-]+")


def doc_title(code: str) -> str:
    """A human label for a doc code. Display only — doc_code stays the key.

    '2015_405693_Shatpath-Brahmanam'  -> 'Shatpath Brahmanam'
    '476948-Rgveda-samhita'           -> 'Rgveda samhita'
    'wl_buddha_carita_sanskrit'       -> 'Buddha Carita Sanskrit'
    """
    s = (code or "").strip()
    if not s:
        return "(untitled)"
    s = _TITLE_LEAD_ACCESSION.sub("", s)          # drop the accession prefix
    if s.startswith("wl_"):
        s = s[3:]                                 # wisdomlib adapter prefix
    s = _TITLE_SEPS.sub(" ", s)
    s = _title_re.sub(r"\\s+", " ", s).strip()
    if not s:
        return code
    # Title-case ONLY words that are entirely lowercase, so 'Rgveda', 'IAST'
    # and roman numerals are not mangled.
    return " ".join(w.capitalize() if w.islower() else w for w in s.split(" "))
'''

EDITS = [
    ('''        SELECT d.id, d.code, d.title, d.category,''',
     '''        SELECT d.id, d.code, d.category,'''),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(PUB):
        sys.exit(f"not found: {PUB} - run from the automaton repo root")
    s = io.open(PUB, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return

    n_title_uses = s.count('["title"]') + s.count("['title']") + s.count(".title")
    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    print(f"  other references to a title field: {n_title_uses} "
          f"(handled by doc_title(); see --apply output)")
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAnchors OK. Re-run with --apply, then: python scripts\\publish_srangam.py --list")
        return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"publish_srangam.py.preTitle.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(PUB, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        # any remaining row["title"] / row.get("title") now resolves via the code
        s = s.replace('row["title"]', 'doc_title(row["code"])')
        s = s.replace("row['title']", 'doc_title(row["code"])')
        s = s.replace('d["title"]', 'doc_title(d["code"])')
        s = s.replace('doc["title"]', 'doc_title(doc["code"])')
        s = s.rstrip() + "\n" + HELPER
        io.open(PUB, "w", encoding="utf-8", newline="\n").write(s)
        py_compile.compile(PUB, doraise=True)
    except Exception as exc:
        shutil.copy2(b, PUB)
        sys.exit(f"FAILED ({exc}) - restored from backup.")

    print("\nApplied and compiles. Verify:")
    print("  python scripts\\publish_srangam.py --list")
    print("\nIf any 'title' reference remains, --list will name it; report the line.")


if __name__ == "__main__":
    main()
