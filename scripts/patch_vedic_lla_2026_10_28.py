#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vedic_lla_2026_10_28.py  (2026-10-28)  VEDIC_LLA_2026_10_28

The Vedic l read as the consonant. In a romanized e-text the l with a dot below between vowels is the Vedic l (U+0933:
the Rgveda's "iile", the Nirukta's "parivrlham"); indic_transliteration writes it as the vowel l (U+090C), a letter of
its own followed by the next vowel as a letter too. On the 28 Oct backup: 52 such words in 41 of the Nirukta witness's
passages (nirukta__w_gretil, local only); GRETIL's Rgveda padapatha has the l 598 times, so its witness waits for this.

  scripts\\etext_witness.py: vedic_lla(), applied in to_deva() with ortho (lla=False reads as before);
  scripts\\mend_witness.py: the old reading may be the one of 21-27 Oct (lla=False), the change named "the Vedic l"
    (so a witness already in the database is mended in place: its ids, English, names and vectors kept);
  the replays of the six patches before it (tests\\test_etext_refs, _prose, _prose2, _dots, test_witness_fix and
    test_etext_analysis): each compares with this patch's backup (.bak_vedlla_) when the next one has none, as each
    replay before them does with the patch after it.

Needs ETEXT_ANALYSIS_2026_10_22 in etext_witness.py and ETEXT_REFS_2026_10_21 in mend_witness.py, and in each test
the marker of the patch after it. Anchored, all-or-nothing, marker-idempotent; line endings kept; py_compile;
.bak_vedlla_<date> copies.

  python scripts\\patch_vedic_lla_2026_10_28.py --check
  python scripts\\patch_vedic_lla_2026_10_28.py
  python scripts\\mend_witness.py --doc nirukta__w_gretil          (the plan: 41 respelled, "the Vedic l")
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VEDIC_LLA_2026_10_28'
TAG = 'vedlla'
FILES = ['scripts/etext_witness.py', 'scripts/mend_witness.py', 'tests/test_etext_refs_2026_10_21.py', 'tests/test_etext_prose_2026_10_21.py', 'tests/test_etext_prose2_2026_10_22.py', 'tests/test_etext_dots_2026_10_22.py', 'tests/test_witness_fix_2026_10_22.py', 'tests/test_etext_analysis_2026_10_22.py']
NEEDS = {'scripts/etext_witness.py': 'ETEXT_ANALYSIS_2026_10_22', 'scripts/mend_witness.py': 'ETEXT_REFS_2026_10_21', 'tests/test_etext_refs_2026_10_21.py': 'ETEXT_PROSE_2026_10_21', 'tests/test_etext_prose_2026_10_21.py': 'ETEXT_PROSE2_2026_10_22', 'tests/test_etext_prose2_2026_10_22.py': 'ETEXT_DOTS_2026_10_22', 'tests/test_etext_dots_2026_10_22.py': 'WITNESS_FIX_2026_10_22', 'tests/test_witness_fix_2026_10_22.py': 'ETEXT_ANALYSIS_2026_10_22', 'tests/test_etext_analysis_2026_10_22.py': 'ETEXT_ANALYSIS_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, "\n  python scripts\\\\etext_witness.py --doc satapatha_madhyandina --file sources\\\\satapatha_gretil --category brahmana --per-page 10\n\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.",
     "\n  python scripts\\\\etext_witness.py --doc satapatha_madhyandina --file sources\\\\satapatha_gretil --category brahmana --per-page 10\n\nVEDIC_LLA_2026_10_28: the Vedic l (l with a dot below between vowels) is read as the consonant U+0933, not the vowel\nl that indic_transliteration writes (the Nirukta's witness had it in 41 passages; GRETIL's Rgveda padapatha has it\n598 times); mend_witness.py reads a witness already in the database again with it.\n\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.")

edit('scripts/etext_witness.py', 2, '\n\ndef to_deva(s: str, scheme: str, ortho: bool = True) -> str:\n    if scheme == "devanagari":\n        return s.replace(DANDA + DANDA, DDANDA).replace("||", DDANDA).replace("|", DANDA)',
     '\n\n# VEDIC_LLA_2026_10_28: the Vedic l (IAST l with a dot below between vowels: the Rgveda\'s "\\u012b\\u1e37e", the\n# Nirukta\'s "parivr\\u0325\\u1e37ham") is the consonant U+0933 there; indic_transliteration writes the vowel l\n# (U+090C) as a letter of its own ("\\u0908\\u090c\\u090f"). A vowel l stands after a consonant as its sign (U+0962:\n# "k\\u1e37pta") or at a word\'s start, so a letter U+090C after a Devanagari letter or sign is that misreading: it\n# becomes U+0933 with the vowel after it as its sign (an a as none), or with a virama before a consonant.\nLLA_BAD = re.compile("(?<=[\\u0900-\\u0963\\u0970-\\u097f])\\u090c([\\u0905-\\u0914\\u0960]?)")\nVOWEL_SIGN = {"\\u0905": "", "\\u0906": "\\u093e", "\\u0907": "\\u093f", "\\u0908": "\\u0940", "\\u0909": "\\u0941",\n              "\\u090a": "\\u0942", "\\u090b": "\\u0943", "\\u0960": "\\u0944", "\\u090f": "\\u0947", "\\u0910": "\\u0948",\n              "\\u0913": "\\u094b", "\\u0914": "\\u094c"}\n\n\ndef vedic_lla(out: str) -> str:\n    """VEDIC_LLA_2026_10_28: a Devanagari reading with each misread Vedic l made U+0933."""\n    def put(m):\n        v = m.group(1)\n        return "\\u0933" + VOWEL_SIGN[v] if v in VOWEL_SIGN else "\\u0933\\u094d" + v\n    return LLA_BAD.sub(put, out)\n\n\ndef to_deva(s: str, scheme: str, ortho: bool = True, lla: bool = True) -> str:\n    """lla=False (with ortho) reads as before VEDIC_LLA_2026_10_28 (mend_witness.py compares the two)."""\n    if scheme == "devanagari":\n        return s.replace(DANDA + DANDA, DDANDA).replace("||", DDANDA).replace("|", DANDA)')

edit('scripts/etext_witness.py', 3, '    out = sanscript.transliterate(s, sch, sanscript.DEVANAGARI)\n    out = out.replace("\\x01", DDANDA).replace("\\x02", DANDA)\n    for k, v in enumerate(kept):   # ETEXT_ORTHO_2026_10_21: the labels and sigla, as the e-text writes them\n        out = out.replace(chr(KEEP0 + k), v)',
     '    out = sanscript.transliterate(s, sch, sanscript.DEVANAGARI)\n    out = out.replace("\\x01", DDANDA).replace("\\x02", DANDA)\n    if ortho and lla:   # VEDIC_LLA_2026_10_28\n        out = vedic_lla(out)\n    for k, v in enumerate(kept):   # ETEXT_ORTHO_2026_10_21: the labels and sigla, as the e-text writes them\n        out = out.replace(chr(KEEP0 + k), v)')

edit('scripts/mend_witness.py', 1, "  python scripts\\\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext --yes\n  python scripts\\\\mend_witness.py --doc markandeya_purana__w_gretil\n\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.",
     '  python scripts\\\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext --yes\n  python scripts\\\\mend_witness.py --doc markandeya_purana__w_gretil\n\nVEDIC_LLA_2026_10_28 (28 Oct): the Vedic l (l with a dot below between vowels) had been read as the vowel l\n(U+090C) in 41 of the Nirukta witness\'s passages ("parivr\\u0325\\u1e37ham" as a vowel l and an h); read again,\nit is U+0933 ("respelled", "the Vedic l"), its scholarly English re-based as above.\n\n  python scripts\\\\mend_witness.py --doc nirukta__w_gretil\n\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py\'s.')

edit('scripts/mend_witness.py', 2, '\n\ndef convert(roman: str, scheme: str, ortho: bool) -> str:\n    """A record\'s Devanagari from its romanized lines, as etext_witness.parse() joins them."""\n    return "\\n".join(x for x in (EW.to_deva(y, scheme, ortho=ortho).strip() for y in roman.split("\\n")) if x).strip()\n\n',
     '\n\ndef convert(roman: str, scheme: str, ortho: bool, lla: bool = True) -> str:\n    """A record\'s Devanagari from its romanized lines, as etext_witness.parse() joins them (lla=False: as before\n    VEDIC_LLA_2026_10_28)."""\n    return "\\n".join(x for x in (EW.to_deva(y, scheme, ortho=ortho, lla=lla).strip() for y in roman.split("\\n"))\n                     if x).strip()\n\n')

edit('scripts/mend_witness.py', 3, '            if not roman or (old.strip() == target and it["type_old"] == target_type and not rw):\n                it.update(kind="same", new=old, type_new=it["type_old"])   # as the e-text means it (mended already)\n            elif old.strip() not in (convert(roman, scheme, False), convert(roman, scheme, True)):\n                it.update(kind="unreproducible", new=old, type_new=it["type_old"])\n            elif head:',
     '            if not roman or (old.strip() == target and it["type_old"] == target_type and not rw):\n                it.update(kind="same", new=old, type_new=it["type_old"])   # as the e-text means it (mended already)\n            elif old.strip() not in (convert(roman, scheme, False), convert(roman, scheme, True, lla=False),\n                                     convert(roman, scheme, True)):   # VEDIC_LLA_2026_10_28: the reading of 21-27 Oct\n                it.update(kind="unreproducible", new=old, type_new=it["type_old"])\n            elif head:')

edit('scripts/mend_witness.py', 4, '            else:\n                what = what_changed(roman) if convert(roman, scheme, True) != old.strip() else []\n                if roman_now != roman:\n                    what.append("the value in brackets")',
     '            else:\n                what = what_changed(roman) if convert(roman, scheme, True) != old.strip() else []\n                if convert(roman, scheme, True, lla=False) != convert(roman, scheme, True):   # VEDIC_LLA_2026_10_28\n                    what.append("the Vedic l")\n                if roman_now != roman:\n                    what.append("the value in brackets")')

edit('tests/test_etext_refs_2026_10_21.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_PROSE_2026_10_21 came after: its backup of etext_witness.py is this patch\'s\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_PROSE_2026_10_21 came after: its backup of etext_witness.py is this patch\'s\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose_*")) or\n                         sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*")))   # VEDIC_LLA_2026_10_28: mend_witness.py\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_etext_prose_2026_10_21.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_PROSE2_2026_10_22 came after: its backup of etext_witness.py is this patch\'s\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose2_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_PROSE2_2026_10_22 came after: its backup of etext_witness.py is this patch\'s\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose2_*")) or\n                         sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*")))   # VEDIC_LLA_2026_10_28\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_etext_prose2_2026_10_22.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_DOTS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextdots_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextdots_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_DOTS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextdots_\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextdots_*")) or\n                         sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*")))   # VEDIC_LLA_2026_10_28\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_etext_dots_2026_10_22.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # WITNESS_FIX_2026_10_22: etext_witness.py\'s later backup may be .bak_witnessfix_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_witnessfix_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # WITNESS_FIX_2026_10_22: etext_witness.py\'s later backup may be .bak_witnessfix_\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_witnessfix_*")) or\n                         sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*")))   # VEDIC_LLA_2026_10_28\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_witness_fix_2026_10_22.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_ANALYSIS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextanalysis_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextanalysis_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_ANALYSIS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextanalysis_\n                later = (sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextanalysis_*")) or\n                         sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*")))   # VEDIC_LLA_2026_10_28\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)')

edit('tests/test_etext_analysis_2026_10_22.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # VEDIC_LLA_2026_10_28 came after: its backup of etext_witness.py is this patch\'s\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_vedlla_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n')


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
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

