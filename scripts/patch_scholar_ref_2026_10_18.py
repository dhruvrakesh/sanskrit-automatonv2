#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_ref_2026_10_18.py  (2026-10-18)  SCHOLAR_REF_2026_10_18

Found on 18 Oct, in the scholarly run of 17 Oct on markandeya_purana__w_gretil (GRETIL's Markandeya Purana, 1 to 93):
  - "--from-ref 81.1" began at page 81, passage 1 (a chapter heading with no reference of its own), not at MarkP_81.1
    on page 627: ref_of() gives a passage without a reference its page.idx, and "81.1" was that too. The run's 740
    verses are adhyayas 19 to 31 (good English, of the wrong chapters); the Devimahatmya was not begun.
  - the flash judge answered "ResourceExhausted" (Google's quota) from 23:34 IST to the end: 482 verses have no score,
    and so are "flagged"; --rejudge read again only the verses a Claude judge had read.

scripts/scholar_translate.py (needs ORNAMENT_2026_10_16):
  - choose(): --from-ref is matched against the verses' own references whenever one of them has it (an e-text's);
    the page.idx fallback is used only when none has (an OCR reading, as before);
  - rejudge_targets(): --rejudge reads again, too, the verses whose judge did not answer (no fidelity, English there),
    whoever the judge was; the dry run and the help say so.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_scholarref_<date>. No database change; nothing is called.
  python scripts\\patch_scholar_ref_2026_10_18.py --check
  python scripts\\patch_scholar_ref_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'SCHOLAR_REF_2026_10_18'
NEEDS = {'scripts/scholar_translate.py': 'ORNAMENT_2026_10_16'}
FILES = list(NEEDS)
TAG = 'scholarref'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/scholar_translate.py', 1, r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16, ORNAMENT_2026_10_16
''', r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16, ORNAMENT_2026_10_16, SCHOLAR_REF_2026_10_18
''')

edit('scripts/scholar_translate.py', 2, r'''    return "%s.%s" % (x.get("page"), x.get("idx"))
''', r'''    return "%s.%s" % (x.get("page"), x.get("idx"))


def own_ref(x: dict) -> str:
    """SCHOLAR_REF_2026_10_18: the verse's own reference, as ref_of trusts it (an e-text's, or one with a dot when the
    engine is not known), or "": never the page.idx ref_of falls back to. On 17 Oct "--from-ref 81.1" meant MarkP_81.1
    (page 627 of the GRETIL Markandeya) and found page 81, passage 1 first: a chapter heading with no reference."""
    r = x.get("ref")
    eng = str(x.get("engine") or "").lower()
    if r and (any(k in eng for k in REF_TRUSTED) or (not eng and "." in str(r))):
        return str(r)
    return ""


def judge_unanswered(r: dict) -> bool:
    """SCHOLAR_REF_2026_10_18: a row with English whose judge gave no score (an error, a quota: "[judge failed: ...]")."""
    return r.get("fidelity") is None and bool((r.get("translation") or "").strip())
''')

edit('scripts/scholar_translate.py', 3, r'''    started = not a.from_ref
    picked, left, skipped = [], [], []
''', r'''    started = not a.from_ref
    picked, left, skipped = [], [], []
    own = bool(a.from_ref) and any(own_ref(x) == a.from_ref for x in allp)   # SCHOLAR_REF_2026_10_18
''')

edit('scripts/scholar_translate.py', 4, r'''            if ref_of(x) != a.from_ref:
''', r'''            if (own_ref(x) if own else ref_of(x)) != a.from_ref:   # SCHOLAR_REF_2026_10_18: its own reference first
''')

edit('scripts/scholar_translate.py', 5, r'''            if is_claude(r.get("judge_engine")) and not r.get("review_verdict")
''', r'''            if (is_claude(r.get("judge_engine")) or judge_unanswered(r)) and not r.get("review_verdict")   # SCHOLAR_REF_2026_10_18
''')

edit('scripts/scholar_translate.py', 6, r'''    print("scholar_translate.py  %s  %s   the judge %s reads again the verses of %s that a Claude judge read"
''', r'''    print("scholar_translate.py  %s  %s   the judge %s reads again the verses of %s that a Claude judge read, or that no "
          "judge answered"   # SCHOLAR_REF_2026_10_18
''')

edit('scripts/scholar_translate.py', 7, r'''                    "of --engine that a Claude judge read (a new version of each, the same English)")
''', r'''                    "of --engine that a Claude judge read, or whose judge did not answer (SCHOLAR_REF_2026_10_18); a "
                    "new version of each, the same English")
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
    print("Next:")
    print('  python -m unittest tests.test_scholar_ref_2026_10_18 tests.test_rejudge_2026_10_15 tests.test_ornament_2026_10_16 tests.test_scholar_2026_10_14 tests.test_tier_r_2026_10_17')
    return 0


if __name__ == "__main__":
    sys.exit(main())
