#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_repair_partial_2026_10_28.py  (2026-10-28)  REPAIR_PARTIAL_2026_10_28

The repair rounds, unstuck. Each round of scripts\\repair_auto.py gives a text's vision step $0.10 at most; when the
pages it has left cost more (the Padma's Patala-khanda: $1.27 for 146 pages), ocr_consensus.py refused the whole run,
nothing was spent, and the round was used up: from 22 to 28 Oct every round tried that text and nothing behind it
ran (data\\auto_repair_log.jsonl; 9 refusals of that $1.2727 in the maintenance log). Now:
  - scripts\\ocr_consensus.py --partial: when the estimate is above --max-usd, the pages that fit under it go now (the
    first of its order), the rest in later runs; without --partial the refusal is as before (fit_pages);
  - scripts\\repair_text.py --repair --partial passes it on; its refusal names the --partial way too;
  - scripts\\repair_auto.py's vision step asks for --partial, so each round reads a part (about 11 pages of the
    Patala-khanda) within its $0.10 and today's allowance.

The replays of READ_IN (tests\\test_read_in_2026_10_13.py, ocr_consensus.py) and REPAIR_NEXT
(tests\\test_repair_next_2026_10_17.py, repair_text.py) compare with this patch's backup (.bak_repairpartial_) when
there is one, as each replay does with the patch after it.

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_repairpartial_<date> copies; py_compile first.

  python scripts\\patch_repair_partial_2026_10_28.py --check
  python scripts\\patch_repair_partial_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'REPAIR_PARTIAL_2026_10_28'
TAG = 'repairpartial'
FILES = ['scripts/ocr_consensus.py', 'scripts/repair_text.py', 'scripts/repair_auto.py', 'tests/test_read_in_2026_10_13.py', 'tests/test_repair_next_2026_10_17.py']
NEEDS = {'scripts/ocr_consensus.py': 'PATH_2026_10_12', 'scripts/repair_text.py': 'REPAIR_HEAL_2026_10_11', 'scripts/repair_auto.py': 'AUTO_TRANSLATE_2026_10_25', 'tests/test_read_in_2026_10_13.py': 'REPAIR_NEXT_2026_10_17', 'tests/test_repair_next_2026_10_17.py': 'REPAIR_NEXT_2026_10_17'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/ocr_consensus.py', 1, '\n# ---------------------------------------------------------------------- main\ndef main() -> int:\n    ap = argparse.ArgumentParser(description="Idempotent OCR consensus for one doc (no DB writes)")',
     '\n# ---------------------------------------------------------------------- main\ndef fit_pages(todo: list, cpp: float, max_usd: float, partial: bool) -> tuple:\n    """REPAIR_PARTIAL_2026_10_28: (the pages to read now, their estimate, what to print) when the estimate of all of\n    them is above max_usd. Without partial: none (the refusal, as before). With it: the first pages of the order that\n    fit under max_usd at cpp a page; none when not even one fits. The repair rounds give $0.10 a round; a text whose\n    pages left cost more was refused every round, and nothing behind it ran (the Padma\'s Patala-khanda, 22 to 28 Oct)."""\n    est = len(todo) * cpp\n    fit = int((max_usd + 1e-9) // cpp) if (partial and cpp > 0) else 0\n    if fit < 1:\n        return [], 0.0, "  REFUSING: estimate $%.4f exceeds --max-usd %.4f" % (est, max_usd)\n    part = list(todo[:fit])\n    return part, len(part) * cpp, ("  PARTIAL: estimate $%.4f exceeds --max-usd %.4f: %d of %d page(s) this run, the "\n                                   "rest later" % (est, max_usd, len(part), len(todo)))\n\n\ndef main() -> int:\n    ap = argparse.ArgumentParser(description="Idempotent OCR consensus for one doc (no DB writes)")')

edit('scripts/ocr_consensus.py', 2, '    ap.add_argument("--max-usd", type=float, default=1.00, help="refuse the vision step above this estimate")\n    ap.add_argument("--max-pages", type=int, default=0, help="cap vision pages this run (0 = no cap)")\n    ap.add_argument("--model", default=None, help="passed to ocr_vision.py --model")\n    ap.add_argument("--yes", action="store_true", help="spend (vision) and write (repair, merge)")',
     '    ap.add_argument("--max-usd", type=float, default=1.00, help="refuse the vision step above this estimate")\n    ap.add_argument("--max-pages", type=int, default=0, help="cap vision pages this run (0 = no cap)")\n    ap.add_argument("--partial", action="store_true",   # REPAIR_PARTIAL_2026_10_28\n                    help="when the estimate is above --max-usd, read the pages that fit under it (the first in the "\n                         "order below), not none")\n    ap.add_argument("--model", default=None, help="passed to ocr_vision.py --model")\n    ap.add_argument("--yes", action="store_true", help="spend (vision) and write (repair, merge)")')

edit('scripts/ocr_consensus.py', 3, '        if todo and args.yes:\n            if est > args.max_usd:\n                print("  REFUSING: estimate $%.4f exceeds --max-usd %.4f" % (est, args.max_usd))\n                return 1\n            vdir.mkdir(parents=True, exist_ok=True)\n            try:   # PATH_2026_10_12: the cap is asked before each page',
     '        if todo and args.yes:\n            if est > args.max_usd:\n                # REPAIR_PARTIAL_2026_10_28: with --partial, the pages that fit under the cap go now, the rest later\n                todo, est, said_ = fit_pages(todo, cpp, args.max_usd, args.partial)\n                print(said_)\n                if not todo:\n                    return 1\n            vdir.mkdir(parents=True, exist_ok=True)\n            try:   # PATH_2026_10_12: the cap is asked before each page')

edit('scripts/repair_text.py', 1, '    ap.add_argument("--replace", type=int, default=None, help="with --use-repaired: the English translations it replaces")\n    ap.add_argument("--max-usd", type=float, default=1.00)\n    ap.add_argument("--ai", action="store_true", help="with --find-source: let the AI judge the editions (about $0.002)")\n    ap.add_argument("--force", action="store_true", help="with --release: publish even before the translation is back")',
     '    ap.add_argument("--replace", type=int, default=None, help="with --use-repaired: the English translations it replaces")\n    ap.add_argument("--max-usd", type=float, default=1.00)\n    ap.add_argument("--partial", action="store_true",   # REPAIR_PARTIAL_2026_10_28\n                    help="with --repair: read the pages that fit under --max-usd when all of them do not")\n    ap.add_argument("--ai", action="store_true", help="with --find-source: let the AI judge the editions (about $0.002)")\n    ap.add_argument("--force", action="store_true", help="with --release: publish even before the translation is back")')

edit('scripts/repair_text.py', 2, '        # this repair is such a job (kind "repair"), so it is told to look past it\n        rc = run([PY, SCRIPTS / "ocr_consensus.py", "--doc", a.doc, "--threshold", thr, "--include-unassessed",\n                  "--yes", "--max-usd", "%.2f" % a.max_usd], keep=out, env_extra={"SA_CONSENSUS_SELF_KIND": "repair"})\n        text = "".join(out)\n        m = re.search(r"REFUSING: estimate \\$([0-9.]+) exceeds --max-usd", text)',
     '        # this repair is such a job (kind "repair"), so it is told to look past it\n        rc = run([PY, SCRIPTS / "ocr_consensus.py", "--doc", a.doc, "--threshold", thr, "--include-unassessed",\n                  "--yes", "--max-usd", "%.2f" % a.max_usd] + (["--partial"] if a.partial else []),   # REPAIR_PARTIAL_2026_10_28\n                 keep=out, env_extra={"SA_CONSENSUS_SELF_KIND": "repair"})\n        text = "".join(out)\n        m = re.search(r"REFUSING: estimate \\$([0-9.]+) exceeds --max-usd", text)')

edit('scripts/repair_text.py', 3, '                  "estimate)" % (est, a.max_usd))\n            print("NEXT: python scripts\\\\repair_text.py --doc %s --repair --max-usd %.2f" % (a.doc, math.ceil(est * 110) / 100.0))\n            return 1\n        if rc not in (0, 3) and "stop them first" in text:',
     '                  "estimate)" % (est, a.max_usd))\n            print("NEXT: python scripts\\\\repair_text.py --doc %s --repair --max-usd %.2f" % (a.doc, math.ceil(est * 110) / 100.0))\n            print("ALSO: or a part now, within $%.2f: python scripts\\\\repair_text.py --doc %s --repair --max-usd %.2f "\n                  "--partial (REPAIR_PARTIAL_2026_10_28)" % (a.max_usd, a.doc, a.max_usd))\n            return 1\n        if rc not in (0, 3) and "stop them first" in text:')

edit('scripts/repair_auto.py', 1, "               most one step, of one text, after repair_text.py --doc X has said what the step is:\n                 vision  NEXT: ... --repair --max-usd N: run with --max-usd the least of N, the round's limit ($0.10),\n                         what is left of today's allowance and what the cap leaves above its reserve ($1.00). Vision\n                         OCR of the pages not read, the audit and the merge: page files only, the database untouched;\n                         repair_text.py and ocr_consensus.py stop before spending more",
     "               most one step, of one text, after repair_text.py --doc X has said what the step is:\n                 vision  NEXT: ... --repair --max-usd N: run with --max-usd the least of N, the round's limit ($0.10),\n                         what is left of today's allowance and what the cap leaves above its reserve ($1.00), and\n                         --partial (REPAIR_PARTIAL_2026_10_28: the pages that fit under it go now, the rest in later\n                         rounds; before, a text whose pages left cost more than the round was refused each round). Vision\n                         OCR of the pages not read, the audit and the merge: page files only, the database untouched;\n                         repair_text.py and ocr_consensus.py stop before spending more")

edit('scripts/repair_auto.py', 2, '            if spend < 0.02:\n                continue\n            argv = [PY, SCRIPTS / "repair_text.py", "--doc", doc, "--repair", "--max-usd", "%.2f" % spend]\n            if a.dry_run:\n                st["did"] = {"doc": doc, "step": "vision", "would_run": " ".join(str(x) for x in argv[1:])}',
     '            if spend < 0.02:\n                continue\n            argv = [PY, SCRIPTS / "repair_text.py", "--doc", doc, "--repair", "--max-usd", "%.2f" % spend,\n                    "--partial"]   # REPAIR_PARTIAL_2026_10_28\n            if a.dry_run:\n                st["did"] = {"doc": doc, "step": "vision", "would_run": " ".join(str(x) for x in argv[1:])}')

edit('tests/test_read_in_2026_10_13.py', 1, '                later = sorted(SCRIPTS.glob(f + ".bak_redeem_*"))   # REDEEM_2026_10_14 came after (text_path.py)\n                later = later or sorted(SCRIPTS.glob(f + ".bak_repairnext_*"))   # REPAIR_NEXT_2026_10_17 came after (repair_text.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)',
     '                later = sorted(SCRIPTS.glob(f + ".bak_redeem_*"))   # REDEEM_2026_10_14 came after (text_path.py)\n                later = later or sorted(SCRIPTS.glob(f + ".bak_repairnext_*"))   # REPAIR_NEXT_2026_10_17 came after (repair_text.py)\n                later = later or sorted(SCRIPTS.glob(f + ".bak_repairpartial_*"))   # REPAIR_PARTIAL_2026_10_28 (ocr_consensus.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)')

edit('tests/test_repair_next_2026_10_17.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            self.assertEqual((t / "scripts" / "repair_text.py").read_bytes(), (SCRIPTS / "repair_text.py").read_bytes())\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[0], t / "scripts" / "repair_text.py")',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            later = sorted(SCRIPTS.glob("repair_text.py.bak_repairpartial_*"))   # REPAIR_PARTIAL_2026_10_28 came after\n            self.assertEqual((t / "scripts" / "repair_text.py").read_bytes(),\n                             (later[0] if later else SCRIPTS / "repair_text.py").read_bytes())\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            shutil.copy2(baks[0], t / "scripts" / "repair_text.py")')


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

