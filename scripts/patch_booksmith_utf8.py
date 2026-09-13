#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_booksmith_utf8.py  (2026-09-13)  BOOKSMITH_UTF8_2026_09_13

The first Hindi build of Shatpath did not fail on its merits. It failed on an
encoding, and it failed in the worst possible place.

exports/booksmith/2015_405693_Shatpath-Brahmanam.json, 15:04:55 today:

    "slug":  "2015-405693-shatpath-brahmanam-hi",
    "mode":  "hi",
    "ok":    false,
    "error": "UnicodeEncodeError: 'charmap' codec can't encode character
              '\\ufffd' in position 28: character maps to <undefined>"

The chain, all of it observable:

  * run() decodes every Booksmith subprocess with
    encoding="utf-8", errors="replace". A child that wrote cp1252 bytes -
    which the Booksmith venv's python does whenever PYTHONIOENCODING is
    unset - therefore arrives here as U+FFFD REPLACEMENT CHARACTER.
  * run() then echoes those lines through log(), which is a bare print().
  * Block Y ran booksmith_build.py from a PowerShell console, where stdout
    is cp1252. print() of U+FFFD raises UnicodeEncodeError.
  * The dashboard was never exposed to this: _child_env() at dashboard.py:141
    already sets PYTHONIOENCODING=utf-8:replace for the jobs it launches. Only
    the console path was unprotected, which is exactly the path Block Y used.

The damage was not the crash. It was WHERE the crash landed: between

    run([exe, ..., "init", slug, ...])          <- succeeded, book.yaml written
    set_audit_policy(exe, project, langs)       <- never reached

So 2015-405693-shatpath-brahmanam-hi exists on disk today with Booksmith's
init defaults:

    output_mode:       reading          (should be audit)
    reading_languages: [sanskrit, iast, english, hindi]   (should be 3, no en)
    subtitle:          Sanskrit - IAST - English - Hindi
    edition_label:     Editorial proof  (should be Audit proof)

A Hindi-only edition advertising English on its cover, gated behind a reading
policy it cannot satisfy. And booksmith_build.py deliberately leaves an
existing book.yaml alone, so no number of rebuilds would ever have fixed it.

Three changes:

  1. _force_utf8_streams() at import. booksmith_build.py stops depending on
     its caller's environment for the ability to print its own log.

  2. _utf8_env() on every run(). Stops U+FFFD being MADE in the first place,
     rather than only surviving it - the Devanagari and IAST that Booksmith
     reports on comes back intact instead of as replacement characters.

  3. _half_created() + a repair branch. A project whose init succeeded and
     whose policy step did not gets its policy applied on the next build.

Change 3 is scoped deliberately and narrowly:

    mode != "tri"                      en/hi projects only exist because this
                                       script made them
    no work/manifest.json              nothing has been frozen against it
    no non-empty work/decisions.jsonl  no human has reviewed anything
    "output_mode: audit" not already in book.yaml

harita-prathama-sthanam, harita-shashtham-sharira-sthanam and
harita-tritiya-sthanam ALSO have a work/ directory and no manifest. They are
trilingual and were made by hand, and whether they should move to
output_mode: audit is the operator's decision (the --adopt-audit question),
not this script's. The mode != "tri" test is what keeps this patch out of
that decision. --verify proves it on a truth table.

Usage
    python scripts\\patch_booksmith_utf8.py --check
    python scripts\\patch_booksmith_utf8.py
    python scripts\\patch_booksmith_utf8.py --verify
"""

import argparse
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

MARK = "BOOKSMITH_UTF8_2026_09_13"
NEEDS = "BOOKSMITH_MODES_2026_09_13"

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "booksmith_build.py"


def read_src(p: Path):
    s = p.read_bytes().decode("utf-8")
    crlf, lf = s.count("\r\n"), s.count("\n")
    if crlf and crlf != lf:
        raise SystemExit("FAIL: %s has mixed line endings (%d CRLF of %d LF)."
                         % (p.name, crlf, lf))
    return s.replace("\r\n", "\n"), ("\r\n" if crlf else "\n")


def write_src(p: Path, text_lf: str, nl: str) -> None:
    p.write_bytes(text_lf.replace("\n", nl).encode("utf-8"))


# -------------------------------------------------------------------------
LOG_OLD = r'''
def log(msg: str) -> None:
    print(msg, flush=True)
'''

LOG_NEW = r'''
# BOOKSMITH_UTF8_2026_09_13
# run() decodes every Booksmith subprocess as UTF-8 with errors="replace", so
# a byte the child wrote in cp1252 arrives here as U+FFFD. Echoing that to a
# Windows console whose encoding is cp1252 then raises
#
#   UnicodeEncodeError: 'charmap' codec can't encode character U+FFFD
#
# which is what killed the first Hindi build of Shatpath at 15:04 on
# 2026-09-13 - after init had created the project, before the audit policy
# was applied. The dashboard sets PYTHONIOENCODING for the jobs it launches;
# a console does not. This script should not depend on who started it.
def _force_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_force_utf8_streams()


def log(msg: str) -> None:
    print(msg, flush=True)
'''

RUN_OLD = r'''
def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    log("  $ " + " ".join(str(c) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
'''

RUN_NEW = r'''
def _utf8_env() -> dict:
    """BOOKSMITH_UTF8_2026_09_13 - stop U+FFFD being created in the first
    place rather than only surviving it. Without this the Booksmith venv's
    python encodes its own output in the console's cp1252, and the Devanagari
    and IAST it is reporting on comes back here as replacement characters -
    unreadable in the log and, worse, unprintable."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    log("  $ " + " ".join(str(c) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=_utf8_env())
'''

HALF_OLD = r'''
def set_audit_policy(bs: Path, project: Path, languages: list[str]) -> None:
'''

HALF_NEW = r'''
def _half_created(project: Path, mode: str) -> bool:
    """BOOKSMITH_UTF8_2026_09_13 - True for a project whose init succeeded and
    whose policy step did not.

    Deliberately narrow. tri is excluded because the trilingual projects were
    made by hand and three of them (harita-prathama-sthanam,
    harita-shashtham-sharira-sthanam, harita-tritiya-sthanam) also have a
    work/ directory and no manifest, so a looser test would silently flip
    their output_mode - a decision that belongs to the operator, not here.
    en and hi projects only exist because this script created them."""
    if mode == "tri":
        return False
    cfg = project / "book.yaml"
    if not cfg.exists():
        return False
    if (project / "work" / "manifest.json").exists():
        return False                      # a witness is frozen against it
    decisions = project / "work" / "decisions.jsonl"
    try:
        if decisions.exists() and decisions.read_text(
                encoding="utf-8", errors="replace").strip():
            return False                  # a human has reviewed something
    except OSError:
        return False
    try:
        return "output_mode: audit" not in cfg.read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return False


def set_audit_policy(bs: Path, project: Path, languages: list[str]) -> None:
'''

INIT_OLD = r'''
        created = not (project / "book.yaml").exists()
        if created:
            log("[2/6] init project (new)")
            run([exe, "--home", home, "init", slug,
                 "--title", title_for(doc, args.title)])
            set_audit_policy(exe, project, MODE_FLAGS[args.mode][2])
        else:
            log("[2/6] project exists - its book.yaml is left exactly as it is")
'''

INIT_NEW = r'''
        created = not (project / "book.yaml").exists()
        if created:
            log("[2/6] init project (new)")
            run([exe, "--home", home, "init", slug,
                 "--title", title_for(doc, args.title)])
            set_audit_policy(exe, project, MODE_FLAGS[args.mode][2])
        elif _half_created(project, args.mode):
            # BOOKSMITH_UTF8_2026_09_13 - init landed, the policy did not.
            # Without this branch the project keeps Booksmith's init defaults
            # for ever, because the else branch below deliberately never
            # touches an existing book.yaml.
            log("[2/6] project exists but its policy was never applied "
                "- applying it now")
            set_audit_policy(exe, project, MODE_FLAGS[args.mode][2])
            state["policy_repaired"] = True
        else:
            log("[2/6] project exists - its book.yaml is left exactly as it is")
'''

PATCHES = [
    (LOG_OLD, LOG_NEW, "UTF-8 stdout, independent of the caller"),
    (RUN_OLD, RUN_NEW, "UTF-8 environment for every Booksmith subprocess"),
    (HALF_OLD, HALF_NEW, "_half_created()"),
    (INIT_OLD, INIT_NEW, "repair a project whose policy step never ran"),
]


def check(apply: bool) -> int:
    if not BUILD.exists():
        print("FAIL: scripts/booksmith_build.py not found - run from the repo.")
        return 2
    src, nl = read_src(BUILD)
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    if NEEDS not in src:
        print("FAIL: this patch builds on %s (Block Y). Run "
              "block_Y_booksmith_modes.ps1 first." % NEEDS)
        return 2

    print("anchor                                              found")
    print("-" * 60)
    ok = True
    for old, _new, name in PATCHES:
        n = src.count(old)
        print("%-51s %s" % (name[:51],
                            "OK" if n == 1 else
                            ("MISSING" if n == 0 else "%d TIMES" % n)))
        if n != 1:
            ok = False
    print("-" * 60)
    if not ok:
        print("FAIL: every anchor must match exactly once. Nothing written.")
        return 2
    if not apply:
        print("--check only: all %d anchors matched. Nothing written."
              % len(PATCHES))
        return 0

    for old, new, name in PATCHES:
        if src.count(old) != 1:
            print("FAIL: anchor %r disturbed by an earlier edit." % name)
            return 2
        src = src.replace(old, new, 1)

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

    write_src(BUILD, src, nl)
    print("Patched scripts/booksmith_build.py (%s endings preserved)"
          % ("CRLF" if nl == "\r\n" else "LF"))
    print("Marker: %s" % MARK)
    return 0


def verify() -> int:
    rc = 0

    def say(name, good, detail=""):
        nonlocal rc
        print("  [%s] %s%s" % ("PASS" if good else "FAIL", name,
                               ("  - " + detail) if detail else ""))
        if not good:
            rc = 1

    src, _nl = read_src(BUILD)
    print("guards")
    say("marker present", MARK in src)

    # 1. The real defect, reproduced and then shown not to reproduce.
    #    A cp1252 stdout printing U+FFFD is exactly what crashed at 15:04.
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    env.pop("PYTHONUTF8", None)
    code = ("import sys; sys.path.insert(0, %r); import booksmith_build as b; "
            "b.log('x' * 28 + '\\ufffd'); sys.exit(0)"
            % str(ROOT / "scripts"))
    p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env)
    say("log() survives U+FFFD on a cp1252 stdout", p.returncode == 0,
        (p.stderr or "").strip().splitlines()[-1:][0]
        if p.returncode else "")

    # 2. _utf8_env actually sets what it claims
    code2 = ("import sys; sys.path.insert(0, %r); import booksmith_build as b; "
             "e = b._utf8_env(); "
             "print(e.get('PYTHONIOENCODING'), e.get('PYTHONUTF8'))"
             % str(ROOT / "scripts"))
    q = subprocess.run([sys.executable, "-c", code2], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    say("_utf8_env sets PYTHONIOENCODING=utf-8 PYTHONUTF8=1",
        q.returncode == 0 and q.stdout.strip() == "utf-8 1",
        (q.stdout or q.stderr).strip()[:120])

    # 3. _half_created truth table, on real directories
    spec_code = r'''
import sys, json, tempfile, pathlib
sys.path.insert(0, %r)
import booksmith_build as b
rows = []
with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    def mk(name, *, yaml="output_mode: reading\n", manifest=False,
           decisions=None, nowork=False):
        p = root / name
        (p / "work").mkdir(parents=True, exist_ok=True)
        (p / "book.yaml").write_text(yaml, encoding="utf-8")
        if manifest:
            (p / "work" / "manifest.json").write_text("{}", encoding="utf-8")
        if decisions is not None:
            (p / "work" / "decisions.jsonl").write_text(decisions,
                                                        encoding="utf-8")
        if nowork:
            pass
        return p
    cases = [
        ("hi, bare project from a half-run init",  mk("a"), "hi", True),
        ("tri, identical shape - must be ignored", mk("b"), "tri", False),
        ("en, bare project from a half-run init",  mk("c"), "en", True),
        ("hi, a witness is already frozen",
         mk("d", manifest=True), "hi", False),
        ("hi, a human has reviewed something",
         mk("e", decisions='{"id":1}\n'), "hi", False),
        ("hi, empty decisions file is not a review",
         mk("f", decisions="\n"), "hi", True),
        ("hi, policy already applied",
         mk("g", yaml="output_mode: audit\n"), "hi", False),
    ]
    for label, proj, mode, want in cases:
        got = b._half_created(proj, mode)
        rows.append([label, mode, want, got])
    missing = root / "zzz"
    rows.append(["hi, project does not exist at all", "hi", False,
                 b._half_created(missing, "hi")])
print(json.dumps(rows))
''' % str(ROOT / "scripts")
    r = subprocess.run([sys.executable, "-c", spec_code], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        say("_half_created truth table", False,
            (r.stderr or "").strip().splitlines()[-1:][0] if r.stderr else "")
        return rc
    import json as _json
    rows = _json.loads(r.stdout.strip().splitlines()[-1])
    print("\n  _half_created truth table")
    print("  %-42s %-4s %-6s %-6s %s" % ("case", "mode", "want", "got", ""))
    bad = 0
    for label, mode, want, got in rows:
        hit = (want == got)
        bad += (not hit)
        print("  %-42s %-4s %-6s %-6s %s"
              % (label[:42], mode, want, got, "" if hit else "  <-- WRONG"))
    print()
    say("_half_created truth table (%d cases)" % len(rows), bad == 0)

    # 4. the three hand-made trilingual projects with no manifest are
    #    provably untouched by this patch
    say("tri is excluded by construction",
        "if mode == \"tri\":\n        return False" in src)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    return verify() if a.verify else check(apply=not a.check)


if __name__ == "__main__":
    sys.exit(main())