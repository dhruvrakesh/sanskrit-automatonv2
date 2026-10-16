#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_classify_hindi_2026_10_16.py  (2026-10-16)  CLASSIFY_HINDI_2026_10_16

Asked on 16 Oct: "why do we not get our own scholarly English and Hindi translations directly from the Sanskrit
source? I thought our automaton was separating contextual Sanskrit text for translation at the ingestion stage
itself." It was meant to: classify_doc.py, the stage after every ingest, sorts a text into mula, frontmatter
("genuine English/Hindi body text and front matter") and noise. But classify_frontmatter.py reads Latin letters
only, so an edition's own Hindi in Devanagari stayed 'mula' and was translated. scripts/edition_hindi.py reads the
words, and scripts/classify_hindi.py tags such passages 'frontmatter'. This patch puts them in the pipeline:

scripts/classify_doc.py:
  - a stage after classify_frontmatter.py: classify_hindi.py. Without --with-english it tags only the passages that
    carry no English, so a freshly ingested text arrives sorted.
scripts/scholar_translate.py (needs READY_PRICE_2026_10_16):
  - readiness(): a passage edition_hindi.py reads as Hindi is "the edition's own Hindi", as one with three of the old
    list's words was. The old rule missed 99 of the Karanagama's (two of its words, or other words);
  - --status counts no row on a passage typed noise or frontmatter, and says how many it set aside; --triage lists
    none.
scripts/dashboard.py (needs LIBRARY_SCHOLAR_2026_10_16):
  - the Library's count of the scholarly English sets aside the rows on passages typed noise or frontmatter, and its
    line says how many; the reader shows no scholarly English on them;
  - the reader does not offer to translate a passage typed noise or frontmatter: "the edition's own matter".

Anchored, all-or-nothing, marker-idempotent; keeps line endings; the new text ASCII; py_compile before the atomic
replace; backups .bak_hindi_<date>.
  python scripts\\patch_classify_hindi_2026_10_16.py --check
  python scripts\\patch_classify_hindi_2026_10_16.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "CLASSIFY_HINDI_2026_10_16"
CD, ST, D = "scripts/classify_doc.py", "scripts/scholar_translate.py", "scripts/dashboard.py"
NEEDS = {CD: "classify_frontmatter.py", ST: "READY_PRICE_2026_10_16", D: "LIBRARY_SCHOLAR_2026_10_16"}
FILES = [CD, ST, D]
TAG = "hindi"

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit(CD, 1, r'''STAGES = [
    ("frontmatter", "classify_frontmatter.py",
     "English / Hindi body text and front matter"),
''', r'''STAGES = [
    ("frontmatter", "classify_frontmatter.py",
     "English body text and front matter"),
    # CLASSIFY_HINDI_2026_10_16: classify_frontmatter.py reads Latin letters only, so an edition's own Hindi
    # (Devanagari) stayed 'mula' and was translated. Without --with-english this tags only what carries no English.
    ("frontmatter", "classify_hindi.py",
     "an edition's own Hindi: its translation, commentary, preface"),
''')

edit(ST, 1, r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16
''', r'''TRIAGE_2026_10_16, READY_PRICE_2026_10_16, CLASSIFY_HINDI_2026_10_16
''')

edit(ST, 2, r'''def readiness(text, text_type=None, quality=None, min_quality: float = 0.35):
''', r'''def edition_hindi(text) -> bool:
    """CLASSIFY_HINDI_2026_10_16: scripts/edition_hindi.py's reading of a passage as an edition's own Hindi (six words
    or more; Hindi words Sanskrit does not have; more of them than Sanskrit marks); False when it cannot be read."""
    try:
        import edition_hindi as _eh
        return bool(_eh.is_hindi(text))
    except Exception:
        return False


def readiness(text, text_type=None, quality=None, min_quality: float = 0.35):
''')

edit(ST, 3, r'''    if len(hindi_words(t)) >= 3:
        return "Hindi prose (the edition's own Hindi), not Sanskrit"
''', r'''    if len(hindi_words(t)) >= 3 or edition_hindi(t):   # CLASSIFY_HINDI_2026_10_16
        return "Hindi prose (the edition's own Hindi), not Sanskrit"
''')

edit(ST, 4, r'''    ids = {x["id"] for x in sel}
''', r'''    ids = {x["id"] for x in sel if (x.get("type") or "") not in ("noise", "frontmatter")}   # CLASSIFY_HINDI_2026_10_16
    aside_ids, aside = {x["id"] for x in sel} - ids, 0
''')

edit(ST, 5, r'''        if pid not in ids:
            continue
        e = per.setdefault(eng,''', r'''        if pid not in ids:
            aside += 1 if pid in aside_ids else 0   # CLASSIFY_HINDI_2026_10_16
            continue
        e = per.setdefault(eng,''')

edit(ST, 6, r'''        out = ext
    except Exception:
        pass
    return out or [''', r'''        out = ext
    except Exception:
        pass
    if aside:   # CLASSIFY_HINDI_2026_10_16
        out.append("  set aside: %d row(s) on passages that are not verse (front matter, noise, an edition's own Hindi)"
                   % aside)
    return out or [''')

edit(ST, 7, r'''        x = byid.get(pid)
        if x is None or not current(r, x):
            continue
        tier, rs = triage_of(r)
''', r'''        x = byid.get(pid)
        if x is None or not current(r, x) or (x.get("type") or "") in ("noise", "frontmatter"):   # CLASSIFY_HINDI_2026_10_16
            continue
        tier, rs = triage_of(r)
''')

edit(D, 1, r'''        for doc, st, h, rv, eng, ptext in con.execute(
                "SELECT s.doc_code, s.status, s.src_hash, s.review_verdict, s.engine, p.text FROM scholar_translations s "
                "LEFT JOIN passages p ON p.id = s.passage_id WHERE s.id IN (SELECT MAX(id) FROM scholar_translations "
                "GROUP BY passage_id)"):
            c = res.setdefault(doc, {"verses": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "accepted": 0,
                                     "rejected": 0, "stale": 0, "engines": {}, "spent": 0.0, "last": ""})
            if ptext is None or _st.src_hash(ptext) != h:
                c["stale"] += 1
                continue
''', r'''        _tt = ("COALESCE(p.text_type, 'mula')" if "text_type" in {r_[1] for r_ in con.execute("PRAGMA table_info(passages)")}
               else "'mula'")   # CLASSIFY_HINDI_2026_10_16
        for doc, st, h, rv, eng, ptext, ptype in con.execute(
                "SELECT s.doc_code, s.status, s.src_hash, s.review_verdict, s.engine, p.text, %s FROM scholar_translations s "
                "LEFT JOIN passages p ON p.id = s.passage_id WHERE s.id IN (SELECT MAX(id) FROM scholar_translations "
                "GROUP BY passage_id)" % _tt):
            c = res.setdefault(doc, {"verses": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "accepted": 0,
                                     "rejected": 0, "stale": 0, "set_aside": 0, "engines": {}, "spent": 0.0,
                                     "last": ""})
            if ptext is None or _st.src_hash(ptext) != h:
                c["stale"] += 1
                continue
            if ptype in ("noise", "frontmatter"):   # CLASSIFY_HINDI_2026_10_16: not verse (an edition's own Hindi ...)
                c["set_aside"] += 1
                continue
''')

edit(D, 2, r'''    if not c or not (c.get("verses") or c.get("stale")):
''', r'''    if not c or not (c.get("verses") or c.get("stale") or c.get("set_aside")):   # CLASSIFY_HINDI_2026_10_16
''')

edit(D, 3, r'''    if c["stale"]:
        parts.append("%s stale (the Sanskrit changed)" % n_(c["stale"]))
''', r'''    if c["stale"]:
        parts.append("%s stale (the Sanskrit changed)" % n_(c["stale"]))
    if c.get("set_aside"):   # CLASSIFY_HINDI_2026_10_16
        parts.append("%s set aside (not Sanskrit verse: front matter, noise, the edition's own Hindi)"
                     % n_(c["set_aside"]))
''')

edit(D, 4, r'''        out, q = {}, quote(doc, safe="")
        for pid, page, idx, text in listed:
            g = got.get(pid)
''', r'''        out, q = {}, quote(doc, safe="")
        kinds = {}   # CLASSIFY_HINDI_2026_10_16: no scholarly English shown on a passage that is not verse
        if "text_type" in {r_[1] for r_ in con.execute("PRAGMA table_info(passages)")}:
            kinds = dict(con.execute("SELECT id, COALESCE(text_type, 'mula') FROM passages WHERE id IN (%s)"
                                     % ",".join("?" * len(ids)), ids).fetchall())
        for pid, page, idx, text in listed:
            if kinds.get(pid) in ("noise", "frontmatter"):
                continue
            g = got.get(pid)
''')

edit(D, 5, r'''            : (looksEnglish(p.text)
''', r'''            : ((ttype === 'frontmatter' || ttype === 'noise')
                ? '<div class="en-source">&#128196; The edition&#39;s own matter (front matter, noise, or its translation or commentary in a modern language): not the Sanskrit, so not translated</div>'
                : looksEnglish(p.text)
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
    if not Path("scripts/edition_hindi.py").exists() or not Path("scripts/classify_hindi.py").exists():
        print("REFUSE: scripts/edition_hindi.py and scripts/classify_hindi.py are needed beside it. Nothing written.")
        return 1
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
    print("  python -m unittest tests.test_classify_hindi_2026_10_16")
    print("  python scripts\\classify_hindi.py   (a dry run: every text)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
