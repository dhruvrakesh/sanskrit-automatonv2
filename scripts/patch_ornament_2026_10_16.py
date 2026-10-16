#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ornament_2026_10_16.py  (2026-10-16)  ORNAMENT_2026_10_16

A printed ornament is not OCR debris. gemini-2.5-flash vision writes an ornamental rule of the printed page as a line
of its own reading "<decorative line>"; Srangam's reader hides that line and draws a short rule (READER_MARKS_2026_10_07).
But the debris test (two Latin letters in a row) read the marker's own words as the scanner's debris: Lovable found
the site calling such a clean verse "provisional English" (16 Oct), and the automaton made the same mistake. In
data/context.db (the backup of 16 Oct, 07:51) three verses carry the marker on a line of its own and are otherwise
clean: the Markandeya Purana 1.4 and 1.6, the Tantric Texts series 135.1.

scripts/scholar_translate.py (needs CLASSIFY_HINDI_2026_10_16):
  - readiness(): a line that is exactly the marker is set aside before the debris test, so such a verse is sent
    (it was left out as "OCR debris"). The translator still reads the verse as it is stored.
scripts/redeem.py (needs READY_PRICE_2026_10_16):
  - classify(): the same, so that such a verse's English counts as made from a clean reading, not from a misread one.
    Srangam's provisional test mirrors this one (RELIABILITY_AUDIT invariant 51); its own fix travels with this
    release (docs/srangam/ORNAMENT_2026-10-16, scripts/patch_srangam_ornament_2026_10_16.py).
The marker inside a line of text, or any other Latin word, is debris as before. repair_text.py and translate_passages.py
count debris over a whole text (a share): three lines do not move it, and they are left as they are.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; ASCII; py_compile before the atomic replace; backups
.bak_ornament_<date>.
  python scripts\\patch_ornament_2026_10_16.py --check
  python scripts\\patch_ornament_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "ORNAMENT_2026_10_16"
NEEDS = {"scripts/scholar_translate.py": "CLASSIFY_HINDI_2026_10_16", "scripts/redeem.py": "READY_PRICE_2026_10_16"}
FILES = list(NEEDS)
TAG = "ornament"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"
RD = "scripts/redeem.py"

edit(ST, 1, r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16
''', r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16, ORNAMENT_2026_10_16
''')

edit(ST, 2, r'''SUP_TAG = re.compile(r"(?i)</?sup>")   # READY_PRICE_2026_10_16: a vision OCR's footnote mark, <sup>6</sup>, is not debris
''', r'''SUP_TAG = re.compile(r"(?i)</?sup>")   # READY_PRICE_2026_10_16: a vision OCR's footnote mark, <sup>6</sup>, is not debris
ORNAMENT = re.compile(r"(?im)^[ \t\r]*<decorative line>[ \t\r]*$")   # ORNAMENT_2026_10_16: a printed rule, not debris
''')

edit(ST, 3, r'''    if JUNK.search(SUP_TAG.sub(" ", t)):   # READY_PRICE_2026_10_16: <sup>n</sup> is the edition's footnote number
''', r'''    if JUNK.search(ORNAMENT.sub(" ", SUP_TAG.sub(" ", t))):   # READY_PRICE_2026_10_16: <sup>n</sup>; ORNAMENT_2026_10_16
''')

edit(RD, 1, r'''DEV = re.compile("[\u0900-\u097f]")
''', r'''DEV = re.compile("[\u0900-\u097f]")
ORNAMENT = re.compile(r"(?im)^[ \t\r]*<decorative line>[ \t\r]*$")   # ORNAMENT_2026_10_16: = scholar_translate.ORNAMENT
''')

edit(RD, 2, r'''        junk = len(DEV.findall(text or "")) >= 8 and bool(JUNK.search(text or ""))
''', r'''        junk = len(DEV.findall(text or "")) >= 8 and bool(JUNK.search(ORNAMENT.sub(" ", text or "")))   # ORNAMENT_2026_10_16
''')

for _f, _n, _o, _new in E:
    assert all(ord(ch) < 128 for ch in _new), "edit %s %d is not ASCII" % (_f, _n)


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


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
    if not Path(ST).exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
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
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
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
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_ornament_2026_10_16")
    print("  python scripts\\redeem.py   (free, read-only: the Library's lines again)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
