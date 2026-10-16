#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ready_price_2026_10_16.py  (2026-10-16)  READY_PRICE_2026_10_16

Two small truths found on 16 Oct, while asking whether the Hayasirsa Pancaratra and the Karanagama are done.

scripts/scholar_translate.py (needs TRIAGE_2026_10_16):
  - readiness(): a vision OCR's footnote mark, <sup>6</sup>, is not OCR debris. gemini-2.5-flash vision wrote the
    printed edition's footnote numbers as <sup>n</sup>, and the debris test (two Latin letters in a row: "sup") left
    out 15 verses of the Hayasirsa Pancaratra (pages 18 to 100) that are otherwise clean. The mark is still in the
    Sanskrit the translator reads; the Agama rule already says a footnote number is not the text. The edition's
    footnotes themselves (the variant readings: "This verse is omitted in B,C") are still left out: they are the
    apparatus, given to the translator beside the verse, not a verse.

scripts/redeem.py (needs REDEEM_FIX_2026_10_14):
  - the price of a passage of working English is measured on the rows since METERED_SINCE (2026-10-15, when
    COST_TRUTH_2026_10_15 began counting the thinking that Google bills as output), when there are 100 passages of
    them or more (pro: 50); before, on all the rows. On 15 Oct gemini-2.5-flash cost $0.00247 a passage (1,917
    passages, $4.73, 808 output tokens a call); the rows before it read $0.0006, and the Library's "about $0.731" to
    translate the Hayasirsa's 1,614 verses again came from them. Since 15 Oct only Gemini's flash rows price flash,
    and its pro rows pro: a Claude engine's rows (CLAUDE_FIRST_2026_10_15) price neither. Before it, the rows are
    counted as before.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; ASCII; py_compile before the atomic replace; backups
.bak_readyprice_<date>.
  python scripts\\patch_ready_price_2026_10_16.py --check
  python scripts\\patch_ready_price_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "READY_PRICE_2026_10_16"
NEEDS = {"scripts/scholar_translate.py": "TRIAGE_2026_10_16", "scripts/redeem.py": "REDEEM_FIX_2026_10_14"}
FILES = list(NEEDS)
TAG = "readyprice"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"
RD = "scripts/redeem.py"

edit(ST, 1, r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15, REJUDGE_2026_10_15,
TRIAGE_2026_10_16
''', r'''AUDIT_2026_10_15, RUN_FIX_2026_10_15, CLAUDE_FIRST_2026_10_15, REJUDGE_2026_10_15,
TRIAGE_2026_10_16, READY_PRICE_2026_10_16
''')

edit(ST, 2, r'''JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")       # = redeem.JUNK, repair_text.JUNK
''', r'''JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")       # = redeem.JUNK, repair_text.JUNK
SUP_TAG = re.compile(r"(?i)</?sup>")   # READY_PRICE_2026_10_16: a vision OCR's footnote mark, <sup>6</sup>, is not debris
''')

edit(ST, 3, r'''    if JUNK.search(t):
        return "OCR debris (Latin letters in the Devanagari): mend the reading first"
''', r'''    if JUNK.search(SUP_TAG.sub(" ", t)):   # READY_PRICE_2026_10_16: <sup>n</sup> is the edition's footnote number
        return "OCR debris (Latin letters in the Devanagari): mend the reading first"
''')

edit(RD, 1, r'''FLASH_DEFAULT, PRO_DEFAULT = 0.00048, 0.00099   # $ a passage, measured on 13 Oct; usage_log decides
''', r'''FLASH_DEFAULT, PRO_DEFAULT = 0.00048, 0.00099   # $ a passage, measured on 13 Oct; usage_log decides
METERED_SINCE = "2026-10-15"   # READY_PRICE_2026_10_16: = scholar_translate.METERED_SINCE (COST_TRUTH_2026_10_15)
''')

edit(RD, 2, r'''def spend_by_doc(con) -> tuple:
    """({doc: $ of its translation calls}, $ a passage on flash, $ a passage on pro), from usage_log."""
    by, flash, pro = {}, [0.0, 0], [0.0, 0]
    try:
        rows = con.execute("SELECT doc, engine, in_tokens, out_tokens, cost_usd, passages FROM usage_log "
                           "WHERE kind='translation'").fetchall()
    except sqlite3.Error:
        return by, FLASH_DEFAULT, PRO_DEFAULT
    for doc, eng, tin, tout, cost, n in rows:
        x = price(eng, tin, tout, cost)
        by[doc] = by.get(doc, 0.0) + x
        acc = pro if "pro" in (eng or "") else flash
        acc[0] += x
        acc[1] += max(0, n or 0)
    f = (flash[0] / flash[1]) if flash[1] >= 100 else FLASH_DEFAULT
    p = (pro[0] / pro[1]) if pro[1] >= 50 else PRO_DEFAULT
    return by, round(f, 6), round(p, 6)
''', r'''def spend_by_doc(con) -> tuple:
    """({doc: $ of its translation calls}, $ a passage on flash, $ a passage on pro), from usage_log.
    READY_PRICE_2026_10_16: a passage's price is measured on the rows since METERED_SINCE (the thinking counted) when
    there are enough of them (flash 100 passages, pro 50), else on all the rows as before; since METERED_SINCE only
    Gemini's flash rows price flash, and its pro rows pro (a Claude engine's rows price neither)."""
    by, flash, pro = {}, [0.0, 0], [0.0, 0]
    flash_now, pro_now = [0.0, 0], [0.0, 0]
    try:
        rows = con.execute("SELECT doc, engine, in_tokens, out_tokens, cost_usd, passages, ts FROM usage_log "
                           "WHERE kind='translation'").fetchall()
    except sqlite3.Error:
        return by, FLASH_DEFAULT, PRO_DEFAULT
    for doc, eng, tin, tout, cost, n, ts in rows:
        x = price(eng, tin, tout, cost)
        by[doc] = by.get(doc, 0.0) + x
        acc = pro if "pro" in (eng or "") else flash
        acc[0] += x
        acc[1] += max(0, n or 0)
        e = (eng or "").lower()   # READY_PRICE_2026_10_16: the rows since the thinking is counted, Gemini's only
        if str(ts or "") >= METERED_SINCE and "gemini" in e and ("pro" in e or "flash" in e):
            now_ = pro_now if "pro" in e else flash_now
            now_[0] += x
            now_[1] += max(0, n or 0)
    f = (flash_now[0] / flash_now[1]) if flash_now[1] >= 100 else (
        (flash[0] / flash[1]) if flash[1] >= 100 else FLASH_DEFAULT)
    p = (pro_now[0] / pro_now[1]) if pro_now[1] >= 50 else ((pro[0] / pro[1]) if pro[1] >= 50 else PRO_DEFAULT)
    return by, round(f, 6), round(p, 6)
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
    print("  python -m unittest tests.test_ready_price_2026_10_16")
    print("  python scripts\\redeem.py   (free, read-only: the Library's prices again)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
