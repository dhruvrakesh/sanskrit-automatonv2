#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_witness_fix_2026_10_22.py  (2026-10-22)  WITNESS_FIX_2026_10_22

Found by your run of 22 Oct, 14:05 (DOCS85's RUNBOOK, step 2):
  1. scripts/etext_witness.py (needs ETEXT_DOTS_2026_10_22): the Nirukta's witness was not written again. ETEXT_DOTS
     keeps its references, sigla and English notes in Latin ((RV X,84,2), (ca Bh), [i.e., from su]); the Latin guard
     counted them as debris (16.5% of its verses; it refuses above 10%: "not a witness yet"), so --write stopped, the
     wipe had run, and --ingest took the pages of 11:00 again (34,183 dandas). kept_out() now leaves out what is kept
     in Latin, as it did for the Surya's labels and sigla (the Nirukta: 1.1%); Latin debris still counts. Checked end
     to end on 22 Oct: 649 verses in 54 pages, 4,676 dandas, 57 avagrahas, 804 quotation marks.
  2. scripts/source_fidelity.py (needs ENGINES_2026_10_22): with the reference a witness in the database
     (db:<doc>__w_<site>, an e-text), TRIANGULATE took it for one of our readings and called GRETIL's Nirukta "usable:
     mend it before the edition; outvoted ... in 11.27 aksharas per 100 (its likely misreadings)". Where two readings
     of our print agree against an e-text, the print reads otherwise (another edition, or the e-text's slip): is_ours()
     now says so, and the verdict is the e-text verdict, as before TRIANGULATE.
  tests/test_etext_dots_2026_10_22.py and tests/test_engines_2026_10_22.py: their replays end at the copies this patch
  backed up.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; backups .bak_witnessfix_<date>; py_compile first.
  python scripts\\patch_witness_fix_2026_10_22.py --check
  python scripts\\patch_witness_fix_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'WITNESS_FIX_2026_10_22'
TAG = 'witnessfix'
FILES = ['scripts/etext_witness.py', 'scripts/source_fidelity.py', 'tests/test_etext_dots_2026_10_22.py', 'tests/test_engines_2026_10_22.py']
NEEDS = {'scripts/etext_witness.py': 'ETEXT_DOTS_2026_10_22', 'scripts/source_fidelity.py': 'ENGINES_2026_10_22', 'tests/test_etext_dots_2026_10_22.py': 'ETEXT_DOTS_2026_10_22', 'tests/test_engines_2026_10_22.py': 'ENGINES_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, '\n\ndef kept_out(text: str) -> str:\n    """ETEXT_ORTHO_2026_10_21: a verse without the labels and sigla gretil_marks() keeps in Latin letters."""\n    return G_SIGLUM_OUT.sub("(", G_LABEL.sub(" ", text or ""))\n\n',
     '\n\nK_CITE_OUT = re.compile(r"\\((?=[^()]*[A-Z])(?=[^()]*[0-9])[^()]{1,80}\\)")       # WITNESS_FIX_2026_10_22: (RV X,84,2)\nK_SIGLUM_OUT = re.compile(r"(?<=\\s)[A-Z][a-z]?(?=[\\])])")                         # (ca Bh), [etAni Bh]\nK_NOTE_OUT = re.compile("\\\\[[^\\\\[\\\\]\\u0900-\\u097f]{3,200}\\\\]")                    # [used in a derivative sense]\n\n\ndef kept_out(text: str) -> str:\n    """ETEXT_ORTHO_2026_10_21: a verse without the labels and sigla gretil_marks() keeps in Latin letters.\n    WITNESS_FIX_2026_10_22: nor what dotted_words() keeps so (a reference, a siglum, an English note): read as Latin\n    debris, 16.5% of the Nirukta\'s verses held some, and the guard (more than 10%) refused to write its witness."""\n    t = G_SIGLUM_OUT.sub("(", G_LABEL.sub(" ", text or ""))\n    return K_NOTE_OUT.sub(" ", K_SIGLUM_OUT.sub(" ", K_CITE_OUT.sub(" ", t)))\n\n')

edit('scripts/source_fidelity.py', 1, '\n\ndef verdict_of_ours(ref: str, pairs: list) -> str:\n    """TRIANGULATE_2026_10_22: no e-text, three readings of one print: the reference (ours) is judged by where the other',
     '\n\ndef is_ours(spec: str) -> bool:\n    """WITNESS_FIX_2026_10_22: a reading of our scan: db:, vision:, raw:, pages:; but not a witness in the database\n    (db:<doc>__w_<site>: an e-text, or another\'s OCR), which TRIANGULATE read as ours: GRETIL\'s Nirukta was called\n    "usable: mend it" where two readings of our print agreed against it, which is where the print reads otherwise."""\n    kind, _, name = (spec or "").partition(":")\n    return kind in OUR_READINGS and not (kind == "db" and "__w_" in name)\n\n\ndef verdict_of_ours(ref: str, pairs: list) -> str:\n    """TRIANGULATE_2026_10_22: no e-text, three readings of one print: the reference (ours) is judged by where the other')

edit('scripts/source_fidelity.py', 2, '          "and a final m as the anusvara; a final consonant joined to the vowel after it; a colon as the visarga%s" % (\n              "; ccha and cha as ca" if a.fold_ch else ""))\n    ours = a.ref.split(":", 1)[0] in OUR_READINGS       # TRIANGULATE_2026_10_22: the reference is one of our readings\n    report = {"mark": MARK, "at": _now(), "ref": a.ref, "prefix": a.prefix or "", "fold_ch": bool(a.fold_ch),\n              "ours": ours,',
     '          "and a final m as the anusvara; a final consonant joined to the vowel after it; a colon as the visarga%s" % (\n              "; ccha and cha as ca" if a.fold_ch else ""))\n    ours = is_ours(a.ref)       # TRIANGULATE_2026_10_22: the reference is one of our readings; WITNESS_FIX_2026_10_22\n    report = {"mark": MARK, "at": _now(), "ref": a.ref, "prefix": a.prefix or "", "fold_ch": bool(a.fold_ch),\n              "ours": ours,')

edit('tests/test_etext_dots_2026_10_22.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # WITNESS_FIX_2026_10_22: etext_witness.py\'s later backup may be .bak_witnessfix_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_witnessfix_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:')

edit('tests/test_engines_2026_10_22.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            self.assertEqual((t / "scripts" / "source_fidelity.py").read_bytes(), TOOL.read_bytes())\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            later = sorted(SCRIPTS.glob("source_fidelity.py.bak_witnessfix_*"))   # WITNESS_FIX_2026_10_22\n            self.assertEqual((t / "scripts" / "source_fidelity.py").read_bytes(), (later[0] if later else TOOL).read_bytes())\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n')


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
