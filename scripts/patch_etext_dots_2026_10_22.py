#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_dots_2026_10_22.py  (2026-10-22)  ETEXT_DOTS_2026_10_22

GRETIL's Nirukta (sources\\nirukta\\sa_yAska-nirukta.htm) separates its words with a full stop and no space
(samAmnAyaH.samAmnAtaH.sa.vyAkhyAtavyaH), quotes its mantras between `` and '', cites them in Latin ((RV.X,84,2;.106,3)),
marks an edition's reading with its siglum ((yugapad.Bh), [etAni.Bh]) and types h for the visarga before a comma
(karmaNah,). indic_transliteration read each full stop as a danda and each ` and ' as an avagraha: the witness had
34,183 dandas and 3,439 avagrahas; read as written, 4,676 (the e-text's 4,617 / and its double stops) and 57.
etext_witness.to_deva() now reads such a line as written (dotted_words()): a full stop between two words a space, two
or more a danda, one at the line's end nothing; `` and '' quotation marks; a word's last h after a vowel the visarga;
a reference, a siglum and an English note in brackets kept as the e-text writes them. Only a line whose words are
joined by full stops more often than they are spaced is read so: every other e-text reads byte for byte as before
(checked on 22 Oct: the Surya Siddhanta, the Markandeya, the Satapatha's kandas 1 and 14, the Mahabharata's book 1,
where '' is two avagrahas); ortho=False (mend_witness.py's comparison) reads as before. Also
tests/test_etext_prose2_2026_10_22.py's replay chain (.bak_etextdots_). Needs ETEXT_PROSE2_2026_10_22.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_etextdots_<date>; py_compile first.
  python scripts\\patch_etext_dots_2026_10_22.py --check
  python scripts\\patch_etext_dots_2026_10_22.py
Then the Nirukta's witness is written again, free and local (the RUNBOOK's DOCS85 section has the commands).
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_DOTS_2026_10_22'
TAG = 'etextdots'
FILES = ['scripts/etext_witness.py', 'tests/test_etext_prose2_2026_10_22.py']
NEEDS = {'scripts/etext_witness.py': 'ETEXT_PROSE2_2026_10_22', 'tests/test_etext_prose2_2026_10_22.py': 'ETEXT_PROSE2_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, 'G_NOTE = re.compile(r"(\\(\\s*\\d[\\d,\\s]*\\))\\s*checked\\b")                  # 1.30b: "(2296832) checked", the inputter\'s\n\n\ndef gretil_marks(s: str):',
     'G_NOTE = re.compile(r"(\\(\\s*\\d[\\d,\\s]*\\))\\s*checked\\b")                  # 1.30b: "(2296832) checked", the inputter\'s\n\n# ETEXT_DOTS_2026_10_22: GRETIL\'s Nirukta (sa_yAska-nirukta.htm, 22 Oct) separates its words with a full stop and no\n# space (samAmnAyaH.samAmnAtaH.sa.vyAkhyAtavyaH), quotes its mantras between `` and \'\', cites them in Latin\n# ((RV.X,84,2;.106,3)) and marks an edition\'s reading with its siglum ([etAni.Bh], (yugapad.Bh)). indic_transliteration\n# reads the full stop as a danda and each ` and \' as an avagraha: the witness had a danda between every two words, two\n# avagrahas at each quotation, and its references and sigla in Devanagari letters. A line whose words are joined by\n# full stops more often than they are spaced (its label not counted) is read as written: a full stop between two words\n# is a space, two or more together a danda, one at the line\'s end (the next word is on the next line) nothing; `` and\n# \'\' are its quotation marks; an h that ends a word after a vowel is the visarga (karmaNah, 62 times); a reference in\n# brackets (it has a numeral), a siglum and an English note in square brackets stay as the e-text writes them, put back\n# after the transliteration. Any other line is read as before: a full stop\n# there is the danda of other IAST e-texts, and \'\' two avagrahas (the Mahabharata\'s gartE \'\'rtAMs).\nG_DOT_WORD = re.compile(r"(?<=[^\\W\\d_])\\.(?=[^\\W\\d_])")                       # a.b: words joined\nG_DOT_CITE = re.compile(r"\\((?=[^()]*\\d)([^()]{1,80})\\)")                        # (RV.X,84,2;.106,3): a reference\nG_DOT_SIGLUM = re.compile(r"\\.([A-Z][a-z]?)(?=[\\])])")                            # [etAni.Bh], (yugapad.Bh): a siglum\nG_SPACED = re.compile(r"(?<=[^\\W\\d_]) +(?=[^\\W\\d_])")                           # a b: words spaced, not a label\nG_DOT_NOTE = re.compile(r"\\[([^\\[\\]]{1,200})\\]")                                 # [used.in.a.derivative.sense]\nG_DOT_RUN = re.compile(r"\\.{2,}")                                                # su.Rtas..bhASA: more than a word\nG_DOT_END = re.compile(r"\\.\\s*$")\nG_DOT_JOIN = re.compile(r"(?<=\\S)\\.(?=\\S)")                                    # a.b, a.[b, \'\'.(: a separator\nG_DOT_VISARGA = re.compile("(?<=[aeiou\\u0101\\u012b\\u016b\\u1e5b\\u1e5d])h(?=[\\\\s,;/|]|$)")      # karmaNah,: the visarga\nQ_OPEN, Q_CLOSE = "\\u201c", "\\u201d"\n\n\ndef latin_words(x: str) -> str:\n    """ETEXT_DOTS_2026_10_22: a reference or a note of a dotted line in Latin, its full stops spaces but for i.e., e.g.,\n    cf. and viz."""\n    x = re.sub(r"\\b(i\\.e|e\\.g|cf|viz)\\.", lambda m: m.group(0).replace(".", "\\x00"), x)\n    return re.sub(r" {2,}", " ", re.sub(r"\\.+", " ", x).replace("\\x00", ".")).strip()\n\n\ndef dotted_words(s: str, kept: list) -> str:\n    """ETEXT_DOTS_2026_10_22: an IAST line written with its words joined by full stops, read as written (see above);\n    what stays in Latin goes into kept, as gretil_marks() keeps its labels. Any other line as it was (in the\n    Mahabharata\'s e-text, gartE \'\'rtAMs: \'\' is two avagrahas, the long a elided)."""\n    def put(text):\n        kept.append(text)\n        return chr(KEEP0 + len(kept) - 1)\n    n = len(G_DOT_WORD.findall(s))\n    if not n or n <= len(G_SPACED.findall(s)):\n        return s\n    s = s.replace("``", Q_OPEN).replace("\'\'", Q_CLOSE)   # not in another e-text: the Mahabharata\'s \'\' is two avagrahas\n    s = G_DOT_CITE.sub(lambda m: "(" + put(latin_words(m.group(1))) + ")", s)\n    s = G_DOT_SIGLUM.sub(lambda m: " " + put(m.group(1)), s)\n    s = G_DOT_NOTE.sub(lambda m: ("[" + put(latin_words(m.group(1))) + "]" if is_english(latin_words(m.group(1)))\n                                  else m.group(0)), s)\n    s = G_DOT_RUN.sub(" | ", G_DOT_END.sub("", s))\n    s = G_DOT_VISARGA.sub("\\u1e25", G_DOT_JOIN.sub(" ", s))\n    return re.sub(r" {2,}", " ", s).replace(Q_OPEN + " ", Q_OPEN).replace(" " + Q_CLOSE, Q_CLOSE)\n\n\ndef gretil_marks(s: str):')

edit('scripts/etext_witness.py', 2, '        if ortho:   # ETEXT_ORTHO_2026_10_21: ortho=False reads as before 21 Oct (mend_witness.py compares the two)\n            s, kept = gretil_marks(s)\n        s = s.lower()\n    s = re.sub(r"(?<=[^\\W\\d_])-(?=[^\\W\\d_])", "", s)          # compound hyphens: one word in Devanagari',
     '        if ortho:   # ETEXT_ORTHO_2026_10_21: ortho=False reads as before 21 Oct (mend_witness.py compares the two)\n            s, kept = gretil_marks(s)\n            s = dotted_words(s, kept)   # ETEXT_DOTS_2026_10_22: words joined by full stops; `` and \'\' quotes\n        s = s.lower()\n    s = re.sub(r"(?<=[^\\W\\d_])-(?=[^\\W\\d_])", "", s)          # compound hyphens: one word in Devanagari')

edit('tests/test_etext_prose2_2026_10_22.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_DOTS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextdots_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextdots_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[self.FILES[0]][0], t / self.FILES[0])')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
