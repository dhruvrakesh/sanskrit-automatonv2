#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_escapes_2026_10_25.py  (2026-10-25)  ESCAPES_2026_10_25

The two patchers of 25 Oct (patch_vamsa_ui_2026_10_25.py, patch_auto_repair_2026_10_25.py) printed SyntaxWarnings on
Python 3.12 and later ("invalid escape sequence '\\s'"): their docstrings were written with single backslashes in
Windows paths (scripts\\vamsa_check.py). Python 3.13 still runs them; a later Python will refuse them. Their docstrings'
backslashes are written as two; nothing else changes (their edits, already applied, are the same). The generator that
wrote them (mkpatcher, in the session's workspace) writes two since.

Needs VAMSA_UI_2026_10_25 and AUTO_REPAIR_2026_10_25 in the two files. Anchored, all-or-nothing, marker-idempotent;
line endings kept; a .bak_escapes_<date> copy of each; both compiled before anything is written.

  python scripts\\patch_escapes_2026_10_25.py --check
  python scripts\\patch_escapes_2026_10_25.py
  python -W error -m py_compile scripts\\patch_vamsa_ui_2026_10_25.py scripts\\patch_auto_repair_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ESCAPES_2026_10_25'
TAG = 'escapes'
FILES = ['scripts/patch_vamsa_ui_2026_10_25.py', 'scripts/patch_auto_repair_2026_10_25.py']
NEEDS = {'scripts/patch_vamsa_ui_2026_10_25.py': 'VAMSA_UI_2026_10_25', 'scripts/patch_auto_repair_2026_10_25.py': 'AUTO_REPAIR_2026_10_25'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/patch_vamsa_ui_2026_10_25.py', 1, "\nThe Vamsa page on the dashboard: the lines of descent of the three indexes, generation by generation, each step with\nthe index's words, the Sanskrit verse where both names stand (GRETIL's editions, read by scripts\\vamsa_check.py), the\nverses of the Mahabharata, the Harivamsa and the Ramayana that name both, our own passages and Raychaudhuri's view.\n",
     "\nThe Vamsa page on the dashboard: the lines of descent of the three indexes, generation by generation, each step with\nthe index's words, the Sanskrit verse where both names stand (GRETIL's editions, read by scripts\\\\vamsa_check.py), the\nverses of the Mahabharata, the Harivamsa and the Ramayana that name both, our own passages and Raychaudhuri's view.\n")

edit('scripts/patch_vamsa_ui_2026_10_25.py', 2, 'Needs RELATIONS_UI_2026_10_24 in each file, and scripts/vamsa_view.py, scripts/vamsa.html and scripts/vamsa_check.py\nin place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_vamsaui_<date> copy of each file;\ndashboard.py compiled before anything is written. Restart the dashboard (scripts\\restart_dashboard.ps1) when it is\nidle; the page reads data\\shelf\\vamsa.db (python scripts\\vamsa_check.py --yes, free).\n\n  python scripts\\patch_vamsa_ui_2026_10_25.py --check\n  python scripts\\patch_vamsa_ui_2026_10_25.py\n"""\nfrom __future__ import annotations',
     'Needs RELATIONS_UI_2026_10_24 in each file, and scripts/vamsa_view.py, scripts/vamsa.html and scripts/vamsa_check.py\nin place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_vamsaui_<date> copy of each file;\ndashboard.py compiled before anything is written. Restart the dashboard (scripts\\\\restart_dashboard.ps1) when it is\nidle; the page reads data\\\\shelf\\\\vamsa.db (python scripts\\\\vamsa_check.py --yes, free).\n\n  python scripts\\\\patch_vamsa_ui_2026_10_25.py --check\n  python scripts\\\\patch_vamsa_ui_2026_10_25.py\n\nESCAPES_2026_10_25: this docstring\'s backslashes are written as two (Python 3.12 and later warned).\n"""\nfrom __future__ import annotations')

edit('scripts/patch_auto_repair_2026_10_25.py', 1, 'patch_auto_repair_2026_10_25.py  (2026-10-25)  AUTO_REPAIR_2026_10_25\n\nThe scheduled maintenance task (scripts\\maintenance_runner.ps1, every 3 hours) gains two steps, and health_watch.py a\ncheck:\n\n  step d    VAMSA_CHECK_2026_10_25: after kin_index.py --check, python scripts\\vamsa_check.py --scheduled: the Purana\n            Index\'s kinships read in GRETIL\'s verses, and the epics\' verses that name both (FREE: no model); it writes\n            only when kin.db or GRETIL\'s zip changed since its last run\n  step e    python scripts\\repair_auto.py --round: one round of the scans\' repair: the first round of each day judges\n            every text (repair_text.py --judge-all, free); each other round does one step of one text, the step\n            repair_text.py names: vision OCR within the allowance (repair_auto.py --allow, $0.25 a day unless set) and\n            above the cap\'s reserve ($1.00), or a repaired text into the database when it replaces nothing (a backup\n            first; only while the dashboard answers and runs no job). A failure is logged and skipped\n  health    health_watch.py reads data\\auto_repair_state.json when there is one: "blocked" (the cap, or only\n            decisions left) is a warn, so the site mails the super admin; no round for 30 hours, a warn\n\n  .gitignore  the rounds\' own files (data\\auto_repair.json, _log.jsonl, _state.json, .lock) stay out of the repository\n\nNeeds MAINT_GUARD_2026_10_24 in the runner, HEALTH_2026_10_23 in health_watch.py and GRETIL_LIBRARY_2026_10_22 in\n.gitignore, and scripts\\repair_auto.py and scripts\\vamsa_check.py in place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_autorepair_<date>\ncopy of each file; health_watch.py compiled before anything is written.\n\n  python scripts\\patch_auto_repair_2026_10_25.py --check\n  python scripts\\patch_auto_repair_2026_10_25.py\n"""\nfrom __future__ import annotations',
     'patch_auto_repair_2026_10_25.py  (2026-10-25)  AUTO_REPAIR_2026_10_25\n\nThe scheduled maintenance task (scripts\\\\maintenance_runner.ps1, every 3 hours) gains two steps, and health_watch.py a\ncheck:\n\n  step d    VAMSA_CHECK_2026_10_25: after kin_index.py --check, python scripts\\\\vamsa_check.py --scheduled: the Purana\n            Index\'s kinships read in GRETIL\'s verses, and the epics\' verses that name both (FREE: no model); it writes\n            only when kin.db or GRETIL\'s zip changed since its last run\n  step e    python scripts\\\\repair_auto.py --round: one round of the scans\' repair: the first round of each day judges\n            every text (repair_text.py --judge-all, free); each other round does one step of one text, the step\n            repair_text.py names: vision OCR within the allowance (repair_auto.py --allow, $0.25 a day unless set) and\n            above the cap\'s reserve ($1.00), or a repaired text into the database when it replaces nothing (a backup\n            first; only while the dashboard answers and runs no job). A failure is logged and skipped\n  health    health_watch.py reads data\\\\auto_repair_state.json when there is one: "blocked" (the cap, or only\n            decisions left) is a warn, so the site mails the super admin; no round for 30 hours, a warn\n\n  .gitignore  the rounds\' own files (data\\\\auto_repair.json, _log.jsonl, _state.json, .lock) stay out of the repository\n\nNeeds MAINT_GUARD_2026_10_24 in the runner, HEALTH_2026_10_23 in health_watch.py and GRETIL_LIBRARY_2026_10_22 in\n.gitignore, and scripts\\\\repair_auto.py and scripts\\\\vamsa_check.py in place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_autorepair_<date>\ncopy of each file; health_watch.py compiled before anything is written.\n\n  python scripts\\\\patch_auto_repair_2026_10_25.py --check\n  python scripts\\\\patch_auto_repair_2026_10_25.py\n\nESCAPES_2026_10_25: this docstring\'s backslashes are written as two (Python 3.12 and later warned).\n"""\nfrom __future__ import annotations')


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
