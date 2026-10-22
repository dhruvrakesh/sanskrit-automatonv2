#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_analysis_2026_10_22.py  (2026-10-22)  ETEXT_ANALYSIS_2026_10_22

Found reading GRETIL's cumulative download (22 Oct): 43 of its 802 TEI html transformations set each verse beside
its analysis, the same verse with its sandhi undone, in a second column (<p class="analysis">): the Manusmrti, the
Yajnavalkyasmrti and the Parasarasmrti among them, three of the texts gretil_library.py found ours in. Read as text,
every verse came twice (the Manusmrti 5,748 units; 3,058 without the analysis, its verses with its headings and
contents). scripts/etext_witness.py (needs WITNESS_FIX_2026_10_22) leaves the analysis out; the e-texts read before
(the Markandeya, the Nirukta, the Surya Siddhanta) have none and read byte for byte as before (checked on 22 Oct).
Also tests/test_witness_fix_2026_10_22.py's replay chain (.bak_etextanalysis_). Anchored, all or nothing,
marker-idempotent; keeps line endings; backups .bak_etextanalysis_<date>; py_compile first.
  python scripts\\patch_etext_analysis_2026_10_22.py --check
  python scripts\\patch_etext_analysis_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_ANALYSIS_2026_10_22'
TAG = 'etextanalysis'
FILES = ['scripts/etext_witness.py', 'tests/test_witness_fix_2026_10_22.py']
NEEDS = {'scripts/etext_witness.py': 'WITNESS_FIX_2026_10_22', 'tests/test_witness_fix_2026_10_22.py': 'WITNESS_FIX_2026_10_22'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1, '\n\ndef html_to_text(s: str) -> str:\n    s = re.sub(r"(?is)<(script|style|head)\\b.*?</\\1\\s*>", " ", s)\n    if len(re.findall(r"(?i)<br\\b", s)) >= 10:\n        # the lines are marked by <br>: a newline in the source is only a space, except inside <pre>',
     '\n\n# ETEXT_ANALYSIS_2026_10_22: 43 of GRETIL\'s 802 TEI html transformations (the Manusmrti, the Yajnavalkyasmrti, the\n# Parasarasmrti among them) set each verse beside its analysis, the same verse with its sandhi undone, in a second\n# column (<p class="analysis">): read as text, every verse came twice (the Manusmrti read as 5,748 units; without the\n# analysis 3,058, its verses with its headings and contents). The analysis is left out; the e-texts read before (the\n# Markandeya, the Nirukta, the Surya Siddhanta) have none, and read byte for byte as before.\nG_ANALYSIS = re.compile(r"(?is)<p\\b[^>]*class=\\"analysis\\"[^>]*>.*?</p\\s*>")\n\n\ndef html_to_text(s: str) -> str:\n    s = re.sub(r"(?is)<(script|style|head)\\b.*?</\\1\\s*>", " ", s)\n    s = G_ANALYSIS.sub(" ", s)   # ETEXT_ANALYSIS_2026_10_22\n    if len(re.findall(r"(?i)<br\\b", s)) >= 10:\n        # the lines are marked by <br>: a newline in the source is only a space, except inside <pre>')

edit('tests/test_witness_fix_2026_10_22.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # ETEXT_ANALYSIS_2026_10_22: etext_witness.py\'s later backup may be .bak_etextanalysis_\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextanalysis_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n')


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
