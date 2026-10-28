#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs99_2026_10_28.py  (2026-10-28)  DOCS99_2026_10_28

The corpus read again and the open texts weighed, recorded: docs\\STATE_2026-10-18.md gains section 34 (28 Oct,
afternoon), RUNBOOK.md the steps in order, README.md the texts and their sources; the full account is
docs\\REPAIR_AND_SOURCES_2026-10-28.md (a new file, beside them). tests\\test_docs98_2026_10_28.py's replay compares
with this patch's backup (.bak_docs99_) when there is one, and not with a file this record changed again.

Needs DOCS98_2026_10_28 in all four; requires the account, scripts\\mend_marks.py and the three patchers of the day
(REPAIR_PARTIAL, RIGHTS_FRONTMATTER, VEDIC_LLA) to be here. Anchored, all-or-nothing, marker-idempotent; line endings
kept; .bak_docs99_<date> copies.

  python scripts\\patch_docs99_2026_10_28.py --check
  python scripts\\patch_docs99_2026_10_28.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS99_2026_10_28'
TAG = 'docs99'
FILES = ['docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'README.md', 'tests/test_docs98_2026_10_28.py']
NEEDS = {'docs/STATE_2026-10-18.md': 'DOCS98_2026_10_28', 'RUNBOOK.md': 'DOCS98_2026_10_28', 'README.md': 'DOCS98_2026_10_28', 'tests/test_docs98_2026_10_28.py': 'DOCS98_2026_10_28'}
REQUIRES = {'docs/REPAIR_AND_SOURCES_2026-10-28.md': 'DOCS99_2026_10_28', 'scripts/mend_marks.py': 'INLINE_MARKS_2026_10_28', 'scripts/patch_repair_partial_2026_10_28.py': 'REPAIR_PARTIAL_2026_10_28', 'scripts/patch_rights_frontmatter_2026_10_28.py': 'RIGHTS_FRONTMATTER_2026_10_28', 'scripts/patch_vedic_lla_2026_10_28.py': 'VEDIC_LLA_2026_10_28'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/STATE_2026-10-18.md', 1, '| Decisions | the Hayasirsa: its English and Hindi translated first (about $16) or released now; the Karanagama stays withdrawn |\n| Next | G3c (a graph of a line), one person across the three indexes; G2 and G4 priced first; E2 |\n',
     "| Decisions | the Hayasirsa: its English and Hindi translated first (about $16) or released now; the Karanagama stays withdrawn |\n| Next | G3c (a graph of a line), one person across the three indexes; G2 and G4 priced first; E2 |\n## 34. 28 Oct, afternoon: the corpus read again, the open texts weighed; four mends (DOCS99_2026_10_28)\n\n| What | State |\n|---|---|\n| Release | `471dd836` pushed (HEAL, B2, DOCS98); Srangam `7c7767f` pushed; C23 and C24 pasted; corpus-index deployed; the claims sent (the 14:33 tick: 8 tables equal, 0 rows) |\n| Local and cloud | 368 groups equal, 0 different; the scholarly English the desk's to the row; held by design: the two Yajurvedas and the Hayasirsa; 7 Surya verses stale |\n| Found | the rounds refused 9 times on the Padma Patala ($1.2727 against $0.10); a modern edition's own matter was sent to the site; the Hayasirsa's footnote numbers in its Sanskrit (854 in 586 verses); the Vedic l read as a vowel in GRETIL's Vedic texts (the Nirukta: 41 passages); about 33 of the Karanagama's verses wholly the editor's Hindi or notes; 13 open e-texts in the database, 2 on the site |\n| Built | REPAIR_PARTIAL, RIGHTS_FRONTMATTER (configs\\edition_rights.json), INLINE_MARKS (scripts\\mend_marks.py), VEDIC_LLA (etext_witness, mend_witness); docs\\REPAIR_AND_SOURCES_2026-10-28.md |\n| Weighed | GRETIL against four scans: the Astadhyayi and the Rgveda padapatha the same work in order (71%, 76%); the Natyasastra in part (58%); the Lalitavistara scan too garbled (14%) |\n| Verified | mend_marks on an extract of the Hayasirsa: 597 mended, 667 scholarly rows carried, the undo byte for byte; mend_witness's plan on the Nirukta: 41 respelled, 608 the same; the suites of the files touched |\n| To do | the four patchers, docs_map.py --write, run_tests; mend_marks on the Hayasirsa (it backs up first); mend_witness on the Nirukta |\n| Decisions | the Hayasirsa: path A (its English through the rounds, about $7.75), B (release now) or C (both languages, about $15.50); the Karanagama: the 33 tagged, then its 1994 rights; the Nirukta released; Muktabodha asked; the thinking A/B |\n| Next | the Astadhyayi and the Rgveda padapatha witnesses; the smaller smrtis translated; GRETIL's Pancaratra and Saiva texts on the Agama shelf; a documentation map for Srangam |\n")

edit('RUNBOOK.md', 1, "5. Until C23 is pasted and corpus-index deployed again, the mirror task's tick sends everything but the claims and\n   says that they wait.\n",
     '5. Until C23 is pasted and corpus-index deployed again, the mirror task\'s tick sends everything but the claims and\n   says that they wait.\n## 28 Oct, afternoon: the corpus read again, the open texts weighed (DOCS99_2026_10_28)\n\ndocs\\REPAIR_AND_SOURCES_2026-10-28.md. From the repository root, with the dashboard idle:\n\n1. `python scripts\\patch_repair_partial_2026_10_28.py --check`, then without --check; the same for\n   `patch_rights_frontmatter_2026_10_28.py`, `patch_vedic_lla_2026_10_28.py` and `patch_docs99_2026_10_28.py`. Then\n   `python scripts\\docs_map.py --write` and `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.\n2. `python scripts\\mend_marks.py --doc HAYASHIRSHA_PANCARATRA --show 8` (the dry run: 854 numbers in 597 passages,\n   667 scholarly rows carried), then the same with `--apply` (it backs the database up to D:\\backups first). Its ALSO\n   line is the undo.\n3. `python scripts\\mend_witness.py --doc nirukta__w_gretil` (the plan: 41 respelled, "the Vedic l"), then `--yes`.\n4. `python scripts\\repair_auto.py --round --dry-run`: the Padma Patala\'s round now reads the pages that fit\n   ("PARTIAL"), not none.\n5. The next mirror tick sends the six editions\' own matter as a notice (RIGHTS_FRONTMATTER); the Hayasirsa stays\n   held until it is released.\n6. The Karanagama (section 4 of the account): mark_passages.py on the 33 passages, a dry run first; the two mixed\n   ones read by a person; then the decision on its rights before `repair_text.py --restore`.\n')

edit('README.md', 1, "  Mahabharata e-text counted, never quoted. Raychaudhuri's view beside each step and on a name's page (B2,\n  docs/cloud/C23), and a search over the scholarly English (X1c, C24): DOCS98_2026_10_28.\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n",
     "  Mahabharata e-text counted, never quoted. Raychaudhuri's view beside each step and on a name's page (B2,\n  docs/cloud/C23), and a search over the scholarly English (X1c, C24): DOCS98_2026_10_28.\n- **Texts and their sources** (DOCS99_2026_10_28): a scan is repaired by its rounds page by page within the day's\n  allowance (scripts/repair_auto.py; REPAIR_PARTIAL lets a round read part of a text); an open e-text (GRETIL, CC\n  BY-NC-SA 4.0) is a witness of a scan or a text of its own (scripts/gretil_library.py, scripts/etext_witness.py);\n  an edition's note numbers are taken out of its Sanskrit (scripts/mend_marks.py); a modern edition's own matter is\n  never sent to the site (configs/edition_rights.json). docs/REPAIR_AND_SOURCES_2026-10-28.md.\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n")

edit('tests/test_docs98_2026_10_28.py', 1, '                got = (t / rel).read_bytes()\n                self.assertIn(MARK.encode(), got, rel)\n                if MARK.encode() in (REPO / rel).read_bytes():\n                    self.assertEqual(got, (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '                got = (t / rel).read_bytes()\n                self.assertIn(MARK.encode(), got, rel)\n                now = (REPO / rel).read_bytes()\n                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_docs99_*"))   # DOCS99_2026_10_28 came after\n                if later:\n                    now = later[0].read_bytes()\n                if MARK.encode() in now and b"DOCS99_2026_10_28" not in now:\n                    self.assertEqual(got, now, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')


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

