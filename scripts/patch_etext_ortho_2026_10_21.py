#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_ortho_2026_10_21.py  (2026-10-21)  ETEXT_ORTHO_2026_10_21

Found on 21 Oct, in the Surya Siddhanta's e-text witness (GRETIL; Michio Yano's input of 2002, GRETIL's TEI of
2020): the e-text writes IAST with H for the visarga (namaH, tejaHsahaH), +a for an a merged into the vowel before it
(puruSo +ayaM, kAlo +anyaH), N.NNa: for a verse's pada, and an edition's variant as (B kevalam), (C ...), once (D ...)
typed with a dot. to_deva() lowered the text before transliterating it, so the H became h and the visarga a h with a
virama (362 of the 515 passages), "+a" stayed "+" and a, the pada letters and the sigla became Devanagari consonants,
and the English of GRETIL's header ("Header", "Source:", "Text", ...) became Devanagari verses on page 1.

scripts/etext_witness.py (needs ETEXT_PAGE_2026_10_18):
  - gretil_marks(): before the text is lowered, H after a vowel is the visarga, +a an a merged into the vowel before
    it (written with the avagraha, as printed editions do), the inputter's note "checked" after a number is not the
    text; the pada labels (1.30a:) and the sigla ((B ...), the dotted D read as D) are kept as the e-text writes them.
    to_deva(s, scheme, ortho=True): ortho=False is the reading before this patch (mend_witness.py compares the two).
  - gretil_header(): the lines of a GRETIL TEI header, from a line "Header" to a line "Text", are dropped as English.
  - leftover_latin() does not count the labels and sigla it keeps.
tests/test_etext_page_2026_10_18.py (its replay chain): etext_witness.py's later backup may be .bak_etextortho_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_etextortho_<date>. No database change; nothing is called. The witnesses already written are mended by
scripts/mend_witness.py, which keeps their passages' ids and their scholarly English.
  python scripts\\patch_etext_ortho_2026_10_21.py --check
  python scripts\\patch_etext_ortho_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_ORTHO_2026_10_21'
NEEDS = {'scripts/etext_witness.py': 'ETEXT_PAGE_2026_10_18', 'tests/test_etext_page_2026_10_18.py': 'ETEXT_PAGE_2026_10_18'}
FILES = list(NEEDS)
TAG = 'etextortho'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, r'''def to_deva(s: str, scheme: str) -> str:
    if scheme == "devanagari":
''', r'''# ETEXT_ORTHO_2026_10_21 ---------------------------------------------------------------------------
# The Surya Siddhanta's GRETIL e-text (21 Oct) writes IAST with H for the visarga, +a for an a merged into the vowel
# before it, N.NNa: for a pada and (B ...) for an edition's variant: lowered before its transliteration, the visarga
# became h with a virama in 362 of its 515 passages. gretil_marks() reads them as the e-text means them; the labels
# and the sigla are set aside (private-use characters, which indic_transliteration passes through) and put back.
KEEP0 = 0xE100
G_LABEL = re.compile(r"(?<![\w.])(\d+\.\d+[a-f]?:)")                     # 1.30a: the e-text's pada label
G_SIGLUM = re.compile("\\(\\s*([A-Z]|\u1e0d)(?=\\s)")                  # (B kevalam); (\u1e0d ...) is its D, dotted
G_SIGLUM_OUT = re.compile(r"\(\s*[A-Z](?=\s)")
G_VISARGA = re.compile("(?<=[aeiou\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e39])H")   # namaH, tejaHsahaH
G_MERGED_SIGLUM = re.compile("([\ue100-\ue1ff]\\s)\\+a")                # (C +any\u0101 ...): after a siglum
G_MERGED = re.compile(r"\s?\+a")                                        # puru\u1e63o +aya\u1e43, v\u0101 +arka
G_NOTE = re.compile(r"(\(\s*\d[\d,\s]*\))\s*checked\b")                  # 1.30b: "(2296832) checked", the inputter's


def gretil_marks(s: str):
    """ETEXT_ORTHO_2026_10_21: (s, kept): an IAST line with the e-text's H (the visarga) and +a (an a merged into the
    vowel before it, written with the avagraha) read as meant, the note "checked" after a number dropped, and the pada
    labels and sigla replaced by private-use characters; kept[k] is what chr(KEEP0 + k) stands for."""
    kept = []

    def put(text):
        kept.append(text)
        return chr(KEEP0 + len(kept) - 1)
    s = G_NOTE.sub(r"\1", s)
    s = G_LABEL.sub(lambda m: put(m.group(1)), s)
    s = G_SIGLUM.sub(lambda m: "(" + put("D" if m.group(1) == "\u1e0d" else m.group(1)), s)
    s = G_VISARGA.sub("\u1e25", s)
    s = G_MERGED_SIGLUM.sub(r"\1'", s)
    s = G_MERGED.sub("'", s)
    return s, kept


def kept_out(text: str) -> str:
    """ETEXT_ORTHO_2026_10_21: a verse without the labels and sigla gretil_marks() keeps in Latin letters."""
    return G_SIGLUM_OUT.sub("(", G_LABEL.sub(" ", text or ""))


def gretil_header(lines: list) -> set:
    """ETEXT_ORTHO_2026_10_21: the numbers (from 1) of the lines of a GRETIL TEI header, from a line "Header" to a line
    "Text", when the block names GRETIL: its English (Contribution, Source, Licence, Notes, Revisions) is not the text;
    its short lines were read as verses on the Surya Siddhanta's page 1 and the Markandeya's. Else empty."""
    first = None
    for i, raw in enumerate(lines[:400], 1):
        t = raw.strip()
        if first is None and t == "Header":
            first = i
        elif first is not None and t == "Text":
            return set(range(first, i + 1)) if "gretil" in " ".join(lines[first - 1:i]).lower() else set()
    return set()


def to_deva(s: str, scheme: str, ortho: bool = True) -> str:
    if scheme == "devanagari":
''')

edit('scripts/etext_witness.py', 2, r'''    if scheme == "iast":
        s = s.lower()
''', r'''    kept = []
    if scheme == "iast":
        if ortho:   # ETEXT_ORTHO_2026_10_21: ortho=False reads as before 21 Oct (mend_witness.py compares the two)
            s, kept = gretil_marks(s)
        s = s.lower()
''')

edit('scripts/etext_witness.py', 3, r'''    out = sanscript.transliterate(s, sch, sanscript.DEVANAGARI)
    return out.replace("\x01", DDANDA).replace("\x02", DANDA)
''', r'''    out = sanscript.transliterate(s, sch, sanscript.DEVANAGARI)
    out = out.replace("\x01", DDANDA).replace("\x02", DANDA)
    for k, v in enumerate(kept):   # ETEXT_ORTHO_2026_10_21: the labels and sigla, as the e-text writes them
        out = out.replace(chr(KEEP0 + k), v)
    return out
''')

edit('scripts/etext_witness.py', 4, r'''    for i, raw in enumerate(lines, 1):
        ln = raw.strip().replace(DANDA + DANDA, DDANDA)     # "\u0964\u0964" typed for the double danda
''', r'''    skip = gretil_header(lines)   # ETEXT_ORTHO_2026_10_21: GRETIL's English header, "Header" to "Text"
    for i, raw in enumerate(lines, 1):
        ln = raw.strip().replace(DANDA + DANDA, DDANDA)     # "\u0964\u0964" typed for the double danda
        if i in skip and ln:
            st["dropped_english"] += 1
            continue
''')

edit('scripts/etext_witness.py', 5, r'''    return sum(1 for v in verses if ASCII_LETTER.search(v["text"])) / float(len(verses))
''', r'''    return sum(1 for v in verses if ASCII_LETTER.search(kept_out(v["text"]))) / float(len(verses))   # ETEXT_ORTHO_2026_10_21
''')

edit('tests/test_etext_page_2026_10_18.py', 1, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:   # ETEXT_ORTHO_2026_10_21: etext_witness.py's later backup may be .bak_etextortho_
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextortho_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
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
