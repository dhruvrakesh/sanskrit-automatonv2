#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_booksmith_modes.py  (2026-09-13)  BOOKSMITH_MODES_2026_09_13

Four defects in booksmith_build.py, all found from the sidecars and the
project directories rather than from reasoning.

1. ONE PROJECT PER DOCUMENT WAS WRONG. Booksmith's model is one project =
   one witness. Re-exporting nilamata_seg in Hindi ingested the Hindi
   witness into the project frozen against the TRILINGUAL one:

       work/manifest.json  source_sha256 e96baef4c8a0a40c...  (tri)
       source/source.html                c1c16a7bf6075e31...  (hi)

   validate_manifest compares them and raises "Frozen manifest is stale;
   refreeze after changes to: source_sha256, release_identity". Both
   build() and build_layout_proof() call it, so the fallback had nowhere
   to land and the job died. Booksmith was right; the wiring was wrong.

   Worse, it left build/book.pdf - the trilingual release - sitting
   beside a Hindi source, so the download endpoint served a trilingual
   PDF that a Hindi run appeared to have produced.

   Fixed by giving each language composition its own project. tri keeps
   the bare slug, so the seven projects made by hand are untouched and
   continue to work; en and hi get -en and -hi.

2. A CHANGED WITNESS WITHIN ONE MODE HAS THE SAME PROBLEM. Translations
   grow; re-exporting the same mode later produces a different witness
   and staleness returns. Before ingest this now compares hashes and,
   if they differ:
     - REFUSES when work/decisions.jsonl holds human decisions. Those are
       frozen against a different witness and discarding them silently to
       make a build succeed would be indefensible.
     - otherwise clears manifest.json and the derived build artefacts, so
       build() re-freezes cleanly against the new source.

3. EVERY COVER CLAIMS FOUR LANGUAGES. subtitle is a hardcoded BookConfig
   default, "Sanskrit - IAST - English - Hindi", and is rendered on the
   title page and the front matter. It is independent of
   policy.reading_languages, which this script already sets correctly:
   the Shatpath project really does carry sanskrit/iast/hindi. So a
   Hindi-only edition advertised English on its cover. Now derived from
   the mode.

4. TITLES ARE FILENAMES. "2015 405693 Shatpath Brahmanam" puts an
   archive scan identifier on a book cover, and "Nilamata Seg" puts a
   pipeline segmentation suffix on one. Cleaned conservatively: leading
   scan ids and a trailing seg/ocr/raw token are dropped, existing
   capitalisation is preserved so MBh01 does not become Mbh01, and
   --title overrides everything. The doc code stays in the sidecar and on
   the Library card, and the source SHA-256 on the title page remains the
   real provenance anchor.

NOT A DEFECT, and I said it was before checking the file: error capture
already worked. The sidecar recorded the exact ValueError under
"blockers". Only my reporting of it was incomplete.

Run from the repo root:  python scripts/patch_booksmith_modes.py
Add --check to verify anchors without writing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARK = "BOOKSMITH_MODES_2026_09_13"
ORCH = Path("scripts/booksmith_build.py")

SLUG_OLD = '''def slug_for(doc: str) -> str:
    """Project id from a doc code. Booksmith's SLUG rule is 2-64 chars of
    lowercase letters, digits, underscore or hyphen; the seven projects that
    already exist use hyphens, so match them."""
    s = doc.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:64]


def title_for(doc: str) -> str:
    return doc.replace("_", " ").replace("-", " ").title()'''

SLUG_NEW = '''# BOOKSMITH_MODES_2026_09_13
# Archive scan identifiers that belong in provenance, not on a cover:
# "2015_405693_Shatpath-Brahmanam" -> "Shatpath Brahmanam".
SCAN_ID = re.compile(r"^(?:\\d{4}[_\\-]\\d{3,}[_\\-]?)+")
PIPELINE_SUFFIX = re.compile(r"[ _-](seg|segmented|ocr|raw|clean|v\\d+)$", re.I)


def slug_for(doc: str, mode: str = "tri") -> str:
    """Project id from a doc code AND its language composition.

    Booksmith's model is one project = one witness, and a different language
    composition is a different witness. Sharing one project between modes is
    what made a Hindi re-export collide with a frozen trilingual manifest.

    tri keeps the bare slug so the seven projects created by hand on
    2026-09-08 continue to resolve; en and hi are suffixed. The SLUG rule is
    2-64 chars of lowercase letters, digits, underscore or hyphen.
    """
    s = doc.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    suffix = "" if mode == "tri" else ("-" + mode)
    return s[: 64 - len(suffix)] + suffix


def title_for(doc: str, override: str | None = None) -> str:
    """A cover title, not a filename. Conservative on purpose: it drops a
    leading scan id and one trailing pipeline suffix, and nothing else. Words
    that already carry capitals keep them, so MBh01 does not become Mbh01."""
    if override:
        return override
    t = SCAN_ID.sub("", doc or "")
    t = t.replace("_", " ").replace("-", " ")
    t = re.sub(r"\\s+", " ", t).strip()
    t = PIPELINE_SUFFIX.sub("", " " + t).strip()
    if not t:
        return doc or "Untitled"
    return " ".join(w if any(ch.isupper() for ch in w) else w.capitalize()
                    for w in t.split())


def sha256_of(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_existing(project: Path, html: Path) -> tuple[str, str]:
    """Decide what to do about an existing project whose witness is about to
    change. Returns (action, detail); action is one of same / fresh /
    refrozen / refuse."""
    src = project / "source" / "source.html"
    manifest = project / "work" / "manifest.json"
    decisions = project / "work" / "decisions.jsonl"

    if not src.exists():
        return ("fresh", "no witness yet")
    if sha256_of(src) == sha256_of(html):
        return ("same", "witness unchanged")
    if not manifest.exists():
        return ("fresh", "witness changed, nothing frozen")
    if decisions.exists() and decisions.stat().st_size > 0:
        return ("refuse",
                "the witness changed and work/decisions.jsonl holds human "
                "review decisions frozen against the previous one. Re-freezing "
                "would invalidate them silently. Open the project in Booksmith "
                "and decide there.")

    derived = [manifest,
               project / "build" / "book.pdf",
               project / "build" / "layout-proof.pdf",
               project / "build" / "build-report.json",
               project / "build" / "qa-report.json"]
    removed = []
    for p in derived:
        if p.exists():
            p.unlink()
            removed.append(p.name)
    return ("refrozen", "witness changed; cleared " + (", ".join(removed) or "nothing"))'''

POLICY_OLD = '''        "d['policy']['output_mode'] = 'audit'\\n"
        "d['policy']['reading_languages'] = langs\\n"
        "d['edition_label'] = 'Audit proof'\\n"'''

POLICY_NEW = '''        "d['policy']['output_mode'] = 'audit'\\n"
        "d['policy']['reading_languages'] = langs\\n"
        "d['edition_label'] = 'Audit proof'\\n"
        # BOOKSMITH_MODES_2026_09_13. subtitle is a hardcoded BookConfig
        # default - "Sanskrit - IAST - English - Hindi" - rendered on the
        # cover and the front matter, and independent of reading_languages.
        # A Hindi-only edition was therefore advertising English. The middot
        # is written as an escape so nothing non-ASCII crosses the command
        # line on a Windows console.
        "labels = {'sanskrit':'Sanskrit','iast':'IAST','english':'English','hindi':'Hindi'}\\n"
        "d['subtitle'] = ' \\\\u00b7 '.join(labels.get(x, x.title()) for x in langs)\\n"'''

MAIN_OLD = '''    doc = args.doc
    slug = slug_for(doc)'''
MAIN_NEW = '''    doc = args.doc
    slug = slug_for(doc, args.mode)'''

TITLE_CALL_OLD = '''            run([exe, "--home", home, "init", slug, "--title", title_for(doc)])'''
TITLE_CALL_NEW = '''            run([exe, "--home", home, "init", slug,
                 "--title", title_for(doc, args.title)])'''

ARG_OLD = '''    ap.add_argument("--selftest", action="store_true")'''
ARG_NEW = '''    ap.add_argument("--title", default=None,
                    help="cover title; overrides the one derived from the doc code")
    ap.add_argument("--selftest", action="store_true")'''

INGEST_OLD = '''        log("[3/6] ingest")
        run([exe, "--home", home, "ingest", slug, str(html)])'''

INGEST_NEW = '''        # BOOKSMITH_MODES_2026_09_13 - never ingest a different witness into a
        # project that is frozen against the old one. That is what killed the
        # nilamata Hindi run.
        action, detail = prepare_existing(project, html)
        state["witness"] = action
        state["witness_detail"] = detail
        log("      witness: %s - %s" % (action, detail))
        if action == "refuse":
            raise RuntimeError("refusing to re-ingest: " + detail)
        save()

        log("[3/6] ingest")
        run([exe, "--home", home, "ingest", slug, str(html)])'''

PROOF_OLD = '''                log("      build refused - falling back to the layout proof")
                log("      %s" % blockers[0][:300])
                run([exe, "--home", home, "proof", slug])
                pdf = project / "build" / "layout-proof.pdf"'''

PROOF_NEW = '''                log("      build refused - falling back to the layout proof")
                log("      %s" % blockers[0][:300])
                # check=False: when the proof ALSO fails, a raised RuntimeError
                # replaced the informative build error with "command failed (1)"
                # in the sidecar. Record both and let the caller see the real
                # reason.
                q = run([exe, "--home", home, "proof", slug], check=False)
                if q.returncode != 0:
                    tail = (q.stderr or "").strip().splitlines()[-1:] or ["proof failed"]
                    state["proof_blockers"] = tail
                    save()
                    raise RuntimeError("build and proof both refused. build: %s | proof: %s"
                                       % (blockers[0][:200], tail[0][:200]))
                pdf = project / "build" / "layout-proof.pdf"'''


def replace_one(text: str, old: str, new: str, label: str):
    n = text.count(old)
    if n != 1:
        return text, ["%s: matched %d times, expected exactly 1" % (label, n)]
    return text.replace(old, new), []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not ORCH.exists():
        print("FAIL: %s not found. Run from the repo root." % ORCH)
        return 2
    src = ORCH.read_text(encoding="utf-8")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if "BOOKSMITH_WIRING_2026_09_12" not in src:
        print("FAIL: this patch builds on BOOKSMITH_WIRING_2026_09_12.")
        return 2

    problems: list[str] = []
    src, p = replace_one(src, SLUG_OLD, SLUG_NEW, "slug/title/prepare"); problems += p
    src, p = replace_one(src, POLICY_OLD, POLICY_NEW, "subtitle"); problems += p
    src, p = replace_one(src, ARG_OLD, ARG_NEW, "--title arg"); problems += p
    src, p = replace_one(src, MAIN_OLD, MAIN_NEW, "slug call"); problems += p
    src, p = replace_one(src, TITLE_CALL_OLD, TITLE_CALL_NEW, "title call"); problems += p
    src, p = replace_one(src, INGEST_OLD, INGEST_NEW, "witness guard"); problems += p
    src, p = replace_one(src, PROOF_OLD, PROOF_NEW, "proof fallback"); problems += p

    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1

    if args.check:
        print("All 7 anchors matched exactly once. --check: nothing written.")
        return 0

    ORCH.write_text(src, encoding="utf-8", newline="\n")
    print("Patched: %s  (7 edits)" % ORCH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
