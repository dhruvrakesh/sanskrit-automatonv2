#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_numeral_verse_2026_10_21.py  (2026-10-21)  NUMERAL_VERSE_2026_10_21

Found on 21 Oct: 18 verses of the Surya Siddhanta's e-text (1.30, 1.41 to 1.43, 2.17 to 2.27, 2.34, 2.35, 2.53: the
revolutions of the planets, their epicycles, the sines) were never sent to the scholarly English. readiness() read them as "numbers among
the words: an index, errata, apparatus or notation, not verse": the e-text gives each word-numeral's value in brackets
after it, (57753336), (224, 449, 691), and is_index() counted those as the words of an index.

scripts/scholar_translate.py (needs SCHOLAR_REF_2026_10_18):
  - is_index(text, typed=False): in a typed edition (an e-text, GRETIL, BORI: the engines whose verse numbers ref_of()
    already trusts) the numbers in brackets are the editor's values of the words, not an index; they are not counted.
    A scan's reading (OCR) is judged as before.
  - readiness(..., engine=None) passes typed; choose() and status_lines() give it the passage's engine. Without an
    engine (bench_mitra.py, the Library) nothing changes.
tests/test_scholar_ref_2026_10_18.py (its replay chain): scholar_translate.py's later backup may be .bak_numeral_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_numeral_<date>. No database change; nothing is called.
  python scripts\\patch_numeral_verse_2026_10_21.py --check
  python scripts\\patch_numeral_verse_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'NUMERAL_VERSE_2026_10_21'
NEEDS = {'scripts/scholar_translate.py': 'SCHOLAR_REF_2026_10_18', 'tests/test_scholar_ref_2026_10_18.py': 'SCHOLAR_REF_2026_10_18'}
FILES = list(NEEDS)
TAG = 'numeral'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/scholar_translate.py', 1, r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16, ORNAMENT_2026_10_16, SCHOLAR_REF_2026_10_18
''', r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16, ORNAMENT_2026_10_16, SCHOLAR_REF_2026_10_18,
NUMERAL_VERSE_2026_10_21
''')

edit('scripts/scholar_translate.py', 2, r'''def is_index(text: str) -> bool:
    """Numbers among the words: an index, errata, an apparatus or a notation. Verse numbers between dandas and a
    sutra's own number at the head of a line do not count."""
    t = text or ""
    if any(m in t for m in INDEX_MARKS):
        return True
    s = SUTRA_NO.sub(" ", VERSE_NO.sub(" ", t))
''', r'''PAREN_NUMS = re.compile("\\(\\s*[%s]+(?:\\s*,\\s*[%s]+)*\\s*\\)" % (_DIG, _DIG))   # NUMERAL_VERSE_2026_10_21: (224, 449)


def typed_engine(engine) -> bool:
    """NUMERAL_VERSE_2026_10_21: a typed edition (an e-text, GRETIL, BORI), as ref_of() trusts its numbers."""
    eng = str(engine or "").lower()
    return bool(eng) and any(k in eng for k in REF_TRUSTED)


def is_index(text: str, typed: bool = False) -> bool:
    """Numbers among the words: an index, errata, an apparatus or a notation. Verse numbers between dandas and a
    sutra's own number at the head of a line do not count. NUMERAL_VERSE_2026_10_21: in a typed edition (typed) the
    numbers in brackets, the editor's values of the word-numerals (the Surya Siddhanta's "(57753336)"), do not count."""
    t = text or ""
    if any(m in t for m in INDEX_MARKS):
        return True
    s = SUTRA_NO.sub(" ", VERSE_NO.sub(" ", t))
    if typed:
        s = PAREN_NUMS.sub(" ", s)
''')

edit('scripts/scholar_translate.py', 3, r'''def readiness(text, text_type=None, quality=None, min_quality: float = 0.35):
''', r'''def readiness(text, text_type=None, quality=None, min_quality: float = 0.35, engine=None):
''')

edit('scripts/scholar_translate.py', 4, r'''    if is_index(t):
''', r'''    if is_index(t, typed_engine(engine)):   # NUMERAL_VERSE_2026_10_21: a typed edition's values in brackets
''')

edit('scripts/scholar_translate.py', 5, r'''        why = readiness(x["text"], x["type"], x["quality"], a.min_quality)
''', r'''        why = readiness(x["text"], x["type"], x["quality"], a.min_quality, engine=x.get("engine"))   # NUMERAL_VERSE_2026_10_21
''')

edit('scripts/scholar_translate.py', 6, r'''    ready = sum(1 for x in sel if not readiness(x["text"], x["type"], x["quality"], a.min_quality))
''', r'''    ready = sum(1 for x in sel if not readiness(x["text"], x["type"], x["quality"], a.min_quality,
                                                engine=x.get("engine")))   # NUMERAL_VERSE_2026_10_21
''')

edit('tests/test_scholar_ref_2026_10_18.py', 1, r'''            self.assertEqual(f.read_bytes(), (SCRIPTS / "scholar_translate.py").read_bytes())
''', r'''            later = sorted(SCRIPTS.glob("scholar_translate.py.bak_numeral_*"))   # NUMERAL_VERSE_2026_10_21 came after
            self.assertEqual(f.read_bytes(), (later[0] if later else SCRIPTS / "scholar_translate.py").read_bytes())
''')


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
    if not Path("scripts/dashboard.py").exists():
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
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
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
    print("DONE: %s; backups .bak_%s_%s" % (MARK, TAG, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
