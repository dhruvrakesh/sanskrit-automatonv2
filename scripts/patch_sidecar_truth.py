#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_sidecar_truth.py  (2026-09-13)  SIDECAR_TRUTH_2026_09_13

A sidecar under the bare name is supposed to be the TRILINGUAL edition's own
account of itself. Until LIBRARY_MODES_2026_09_13 the name carried no mode, so
whichever edition built last wrote there. One such file is on disk right now:

  exports/booksmith/2015_405693_Shatpath-Brahmanam.json
    "slug":  "2015-405693-shatpath-brahmanam-hi"
    "mode":  "hi"
    "ok":    false
    "error": "UnicodeEncodeError: 'charmap' codec can't encode character
              '\\ufffd' in position 28"
    "started_at": "2026-09-13T15:04:54Z"

That is the Hindi run that crashed, sitting under the trilingual name. The
trilingual edition built successfully at 17:37 and has a 3,401 KB book.pdf.
Without a guard, _bs_state_one() reads that file as the TRILINGUAL card's
"last", so the Library reports a healthy edition as a failed one - and names
an encoding error that had nothing to do with it.

Every sidecar records its own mode. Believe the file over its filename, and
return nothing rather than something false. That heals this file and any
other legacy sidecar, without deleting or rewriting anything on disk - the
crashed run's record stays exactly where it is, for forensics, and simply
stops being presented as a different edition's state.

A sidecar with no "mode" key at all predates the field; it is accepted, since
no edition other than trilingual existed when it was written.

The audit counts in the Shatpath Hindi build are NOT addressed here, and are
not a defect in this repo. See the notes at the end of this docstring.

Usage
    python scripts\\patch_sidecar_truth.py --check
    python scripts\\patch_sidecar_truth.py
    python scripts\\patch_sidecar_truth.py --verify

----------------------------------------------------------------------
Why the Hindi edition reported 2,720 findings, and why that is Booksmith's
design rather than our bug - recorded here so it is not rediscovered:

  counts: missing-language 2351, ocr-intrusion 368, duplicate-reference 1

  src/nartiang_booksmith/audit.py, audit_source():

      for unit in document.units:
          for language in Language:          # <- the ENUM, all four
              if not unit.text.get(language, "").strip():
                  ... missing-language ...

  It iterates Language, not config.policy.reading_languages. The Hindi
  edition has 2,259 units, English absent from every one by design, and
  Hindi absent from 92:

      2259 + 92 = 2351          exactly the reported count

  So 2,259 of those findings say "no English text" about a book that is
  deliberately not in English. They are WARNING severity, so the AUDIT
  edition builds - 940 pages, QA passed, all seven checks green.

  A READING edition is a different matter. readiness.py blocks on

      unresolved = {i.unit_id for i in audit.issues if i.requires_review ...}

  and AuditIssue.requires_review defaults to True and is never set False by
  audit_source. So every unit is "unresolved" and a Hindi reading edition is
  unreachable until 2,259 findings about absent English are resolved one by
  one. analyse_readiness() DOES respect reading_languages for its
  missing_by_language warning - so the language-awareness exists, it just is
  not applied to the audit or to the blocker.

  That is a Booksmith-side change, in a vendored v0.1.0 tree, and it is not
  being made blind. It is the thing to settle before Phase 5 (MBh01 as the
  first reading edition) and before any single-language reading edition.
"""

import argparse
import json
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path

MARK = "SIDECAR_TRUTH_2026_09_13"
NEEDS = "LIBRARY_MODES_2026_09_13"

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "scripts" / "dashboard.py"


def read_src(p: Path):
    s = p.read_bytes().decode("utf-8")
    crlf, lf = s.count("\r\n"), s.count("\n")
    if crlf and crlf != lf:
        raise SystemExit("FAIL: %s has mixed line endings (%d CRLF of %d LF)."
                         % (p.name, crlf, lf))
    return s.replace("\r\n", "\n"), ("\r\n" if crlf else "\n")


OLD = r'''
def _bs_sidecar(doc: str, mode: str = "tri"):
    """The last build's own account of itself, or None. Mode-aware since
    LIBRARY_MODES_2026_09_13; the bare name is the trilingual one."""
    name = ("%s.json" % doc) if mode == "tri" else ("%s__%s.json" % (doc, mode))
    p = ROOT / "exports" / "booksmith" / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
'''

NEW = r'''
def _bs_sidecar(doc: str, mode: str = "tri"):
    """The last build's own account of itself, or None. Mode-aware since
    LIBRARY_MODES_2026_09_13; the bare name is the trilingual one.

    SIDECAR_TRUTH_2026_09_13 - the bare name was mode-blind until today, so a
    single-language run could land under it and still sits there:
    exports/booksmith/2015_405693_Shatpath-Brahmanam.json holds the Hindi
    build that crashed at 15:04:55, while the trilingual edition built
    cleanly at 17:37. Without this guard the TRILINGUAL card reports that
    failure, and quotes an encoding error that had nothing to do with it.

    Every sidecar records its own mode. Believe the file over its filename.
    A sidecar with no "mode" key predates the field and is accepted, because
    no edition other than trilingual existed when it was written."""
    name = ("%s.json" % doc) if mode == "tri" else ("%s__%s.json" % (doc, mode))
    p = ROOT / "exports" / "booksmith" / name
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    recorded = data.get("mode")
    if recorded is not None and recorded != mode:
        return None          # someone else's build, under this one's name
    return data
'''


def check(apply: bool) -> int:
    if not DASH.exists():
        print("FAIL: scripts/dashboard.py not found - run from the repo.")
        return 2
    src, nl = read_src(DASH)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if NEEDS not in src:
        print("FAIL: this patch builds on %s (Block AA)." % NEEDS)
        return 2
    n = src.count(OLD)
    print("anchor: _bs_sidecar believes the file over the filename ... %s"
          % ("OK" if n == 1 else ("MISSING" if n == 0 else "%d TIMES" % n)))
    if n != 1:
        print("FAIL: the anchor must match exactly once. Nothing written.")
        return 2
    if not apply:
        print("--check only: nothing written.")
        return 0

    src = src.replace(OLD, NEW, 1)
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    Path(tmp).write_bytes(src.replace("\n", nl).encode("utf-8"))
    try:
        py_compile.compile(tmp, cfile=tmp + "c", doraise=True)
    except py_compile.PyCompileError as e:
        print("FAIL: patched file does not compile:\n%s" % e)
        return 2
    finally:
        for f in (tmp, tmp + "c"):
            try:
                os.remove(f)
            except OSError:
                pass
    DASH.write_bytes(src.replace("\n", nl).encode("utf-8"))
    print("Patched scripts/dashboard.py (%s endings preserved)"
          % ("CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    return 0


def _load_fns(exports_root: Path):
    """Execute the real Booksmith block out of dashboard.py, rooted wherever
    we point it. No Flask, no server, no stubs of the function under test."""
    src, _ = read_src(DASH)
    i = src.index("BOOKSMITH_ROOT = pathlib.Path(")
    j = src.index('@app.get("/api/booksmith/state")')
    import pathlib as _pl
    import time as _t
    ns = {"pathlib": _pl, "os": os, "re": re, "json": json, "time": _t,
          "ROOT": exports_root, "JOBS": {}}
    exec(src[i:j], ns)
    return ns


def verify() -> int:
    rc = 0

    def say(name, good, detail=""):
        nonlocal rc
        print("  [%s] %s%s" % ("PASS" if good else "FAIL", name,
                               ("  - " + detail) if detail else ""))
        if not good:
            rc = 1

    src, _ = read_src(DASH)
    print("guards")
    say("marker present", MARK in src)

    # Truth table on fixtures, using the real function.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        d = root / "exports" / "booksmith"
        d.mkdir(parents=True)
        (d / "A.json").write_text(json.dumps({"mode": "tri", "ok": True}))
        (d / "B.json").write_text(json.dumps({"mode": "hi", "ok": False}))
        (d / "B__hi.json").write_text(json.dumps({"mode": "hi", "ok": True}))
        (d / "C.json").write_text(json.dumps({"ok": True}))       # legacy
        (d / "D.json").write_text("{ not json")
        ns = _load_fns(root)
        f = ns["_bs_sidecar"]
        cases = [
            ("bare + tri content, asked for tri", ("A", "tri"), True),
            ("bare + HI content, asked for tri",  ("B", "tri"), False),
            ("suffixed hi, asked for hi",         ("B", "hi"),  True),
            ("legacy, no mode key, asked for tri", ("C", "tri"), True),
            ("unparseable json",                  ("D", "tri"), False),
            ("absent",                            ("E", "tri"), False),
        ]
        print("\n  _bs_sidecar truth table")
        print("  %-40s %-6s %-6s" % ("case", "want", "got"))
        bad = 0
        for label, (doc, mode), want in cases:
            got = f(doc, mode) is not None
            bad += (got != want)
            print("  %-40s %-6s %-6s%s" % (label, want, got,
                                           "" if got == want else "  <-- WRONG"))
        print()
        say("_bs_sidecar truth table (%d cases)" % len(cases), bad == 0)

    # The real repo, as it actually is right now.
    ns = _load_fns(ROOT)
    f, state = ns["_bs_sidecar"], ns["_bs_state_one"]
    doc = "2015_405693_Shatpath-Brahmanam"
    bare = ROOT / "exports" / "booksmith" / ("%s.json" % doc)
    if bare.exists():
        raw = json.loads(bare.read_text(encoding="utf-8"))
        say("the stale file is still on disk, unmodified",
            raw.get("mode") == "hi" and raw.get("ok") is False,
            "mode=%s ok=%s" % (raw.get("mode"), raw.get("ok")))
        say("but it is no longer served as the trilingual state",
            f(doc, "tri") is None)
        st = state(doc)
        say("Shatpath's card carries no false 'last'", "last" not in st)
        tri = [v for v in st["variants"] if v["mode"] == "tri"]
        say("the trilingual variant carries no false 'last'",
            bool(tri) and "last" not in tri[0])
        hi = [v for v in st["variants"] if v["mode"] == "hi"]
        say("the Hindi variant still reports its own successful build",
            bool(hi) and hi[0].get("last", {}).get("ok") is True)
    else:
        print("  (note: the stale sidecar is not present; fixture table stands)")

    # Nothing else regressed: a healthy trilingual doc still reports.
    for other in ("nilamata_seg", "AphorismsOfSandilya"):
        p = ROOT / "exports" / "booksmith" / ("%s.json" % other)
        if p.exists():
            say("%s still reports its trilingual build" % other,
                (f(other, "tri") or {}).get("ok") is True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    return verify() if a.verify else check(apply=not a.check)


if __name__ == "__main__":
    sys.exit(main())