#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_auto_repair_2026_10_25.py  (2026-10-25)  AUTO_REPAIR_2026_10_25

The scheduled maintenance task (scripts\\maintenance_runner.ps1, every 3 hours) gains two steps, and health_watch.py a
check:

  step d    VAMSA_CHECK_2026_10_25: after kin_index.py --check, python scripts\\vamsa_check.py --scheduled: the Purana
            Index's kinships read in GRETIL's verses, and the epics' verses that name both (FREE: no model); it writes
            only when kin.db or GRETIL's zip changed since its last run
  step e    python scripts\\repair_auto.py --round: one round of the scans' repair: the first round of each day judges
            every text (repair_text.py --judge-all, free); each other round does one step of one text, the step
            repair_text.py names: vision OCR within the allowance (repair_auto.py --allow, $0.25 a day unless set) and
            above the cap's reserve ($1.00), or a repaired text into the database when it replaces nothing (a backup
            first; only while the dashboard answers and runs no job). A failure is logged and skipped
  health    health_watch.py reads data\\auto_repair_state.json when there is one: "blocked" (the cap, or only
            decisions left) is a warn, so the site mails the super admin; no round for 30 hours, a warn

  .gitignore  the rounds' own files (data\\auto_repair.json, _log.jsonl, _state.json, .lock) stay out of the repository

Needs MAINT_GUARD_2026_10_24 in the runner, HEALTH_2026_10_23 in health_watch.py and GRETIL_LIBRARY_2026_10_22 in
.gitignore, and scripts\\repair_auto.py and scripts\\vamsa_check.py in place. Anchored, all-or-nothing, marker-idempotent; line endings kept; a .bak_autorepair_<date>
copy of each file; health_watch.py compiled before anything is written.

  python scripts\\patch_auto_repair_2026_10_25.py --check
  python scripts\\patch_auto_repair_2026_10_25.py

ESCAPES_2026_10_25: this docstring's backslashes are written as two (Python 3.12 and later warned).
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'AUTO_REPAIR_2026_10_25'
TAG = 'autorepair'
FILES = ['scripts/maintenance_runner.ps1', 'scripts/health_watch.py', '.gitignore']
NEEDS = {'scripts/maintenance_runner.ps1': 'MAINT_GUARD_2026_10_24', 'scripts/health_watch.py': 'HEALTH_2026_10_23', '.gitignore': 'GRETIL_LIBRARY_2026_10_22'}
REQUIRES = {'scripts/repair_auto.py': 'AUTO_REPAIR_2026_10_25', 'scripts/vamsa_check.py': 'VAMSA_CHECK_2026_10_25'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/maintenance_runner.ps1', 1, '        & $py scripts\\entity_links.py --scheduled --claims data\\shelf\\claims.db 2>&1 | Add-Content $log\n        if (Test-Path "data\\shelf\\kin.db") { & $py scripts\\kin_index.py --check 2>&1 | Add-Content $log }\n        Log ("STEP d links        {0:n0}s" -f ((Get-Date) - $td).TotalSeconds)\n    } catch {\n        Log ("STEP d links SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $td).TotalSeconds, $_)\n    }\n',
     '        & $py scripts\\entity_links.py --scheduled --claims data\\shelf\\claims.db 2>&1 | Add-Content $log\n        if (Test-Path "data\\shelf\\kin.db") { & $py scripts\\kin_index.py --check 2>&1 | Add-Content $log }\n        # VAMSA_CHECK_2026_10_25: the Purana Index\'s kinships read in GRETIL\'s verses (FREE); only when kin.db changed\n        if ((Test-Path "data\\shelf\\kin.db") -and (Test-Path "scripts\\vamsa_check.py")) {\n            & $py scripts\\vamsa_check.py --scheduled 2>&1 | Add-Content $log\n        }\n        Log ("STEP d links        {0:n0}s" -f ((Get-Date) - $td).TotalSeconds)\n    } catch {\n        Log ("STEP d links SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $td).TotalSeconds, $_)\n    }\n\n    # e) AUTO_REPAIR_2026_10_25: one round of the scans\' repair (repair_auto.py): one step of one text, the step\n    #    repair_text.py names; the paid one (vision) within the allowance (repair_auto.py --allow) and above the cap\'s\n    #    reserve. A failure here is logged and skipped; it never stops the DONE line.\n    if (Test-Writer "d") { exit 0 }\n    $te = Get-Date\n    try {\n        if (Test-Path "scripts\\repair_auto.py") { & $py scripts\\repair_auto.py --round 2>&1 | Add-Content $log }\n        Log ("STEP e repair       {0:n0}s" -f ((Get-Date) - $te).TotalSeconds)\n    } catch {\n        Log ("STEP e repair SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $te).TotalSeconds, $_)\n    }\n')

edit('scripts/health_watch.py', 1, '  spend        the cap (budget_state): paused, or under $2 left, warn\n  links        entity_link_runs: the links last rebuilt more than 26 hours ago while the names changed since, warn\n\n  python scripts\\\\health_watch.py               one line a check, then the verdict',
     "  spend        the cap (budget_state): paused, or under $2 left, warn\n  links        entity_link_runs: the links last rebuilt more than 26 hours ago while the names changed since, warn\n  repair       data\\auto_repair_state.json (repair_auto.py's rounds, AUTO_REPAIR_2026_10_25), when there is one: blocked\n               (the cap, or only decisions left) warn, with what it asks; no round for 30 hours while it has an\n               allowance, warn\n\n  python scripts\\\\health_watch.py               one line a check, then the verdict")

edit('scripts/health_watch.py', 2, '\n\ndef health(root: Path = ROOT, backup_dir: str = "", now=None) -> dict:\n    now = now or datetime.datetime.now()',
     '\n\nREPAIR_H = 30\n\n\ndef check_repair(path: Path, now):\n    """AUTO_REPAIR_2026_10_25: the state the last round left; None when the rounds have never run."""\n    if not path.exists():\n        return None\n    try:\n        st = json.loads(path.read_text(encoding="utf-8"))\n    except (OSError, ValueError):\n        return {"state": "warn", "say": "repair: the rounds\' state does not read"}\n    t = parse_ts(st.get("at"))\n    asks = [a.get("say", "") for a in (st.get("asks") or []) if isinstance(a, dict)]\n    if st.get("status") == "blocked":\n        return {"state": "warn", "say": "repair: " + (asks[0] if asks else "blocked")}\n    if t is not None and hours(t, now) > REPAIR_H and float(st.get("allowance") or 0) > 0:\n        return {"state": "warn", "say": "repair: no round since %s" % t.strftime("%d %b %H:%M")}\n    d = st.get("did") or {}\n    return {"state": "ok", "say": "repair: %s%s" % (st.get("status", "?"), (", %s %s" % (d.get("step"), d.get("doc")))\n                                                      if d.get("doc") else "")}\n\n\ndef health(root: Path = ROOT, backup_dir: str = "", now=None) -> dict:\n    now = now or datetime.datetime.now()')

edit('scripts/health_watch.py', 3, '    for c in check_db(root / "data" / "context.db", now):\n        checks[c["say"].split(":", 1)[0]] = c\n    status = max((c["state"] for c in checks.values()), key=lambda s: RANK[s])\n    return {"mark": MARK, "status": status, "at": now.strftime("%Y-%m-%dT%H:%M:%S"), "checks": checks,',
     '    for c in check_db(root / "data" / "context.db", now):\n        checks[c["say"].split(":", 1)[0]] = c\n    rep = check_repair(root / "data" / "auto_repair_state.json", now)   # AUTO_REPAIR_2026_10_25\n    if rep:\n        checks["repair"] = rep\n    status = max((c["state"] for c in checks.values()), key=lambda s: RANK[s])\n    return {"mark": MARK, "status": status, "at": now.strftime("%Y-%m-%dT%H:%M:%S"), "checks": checks,')

edit('.gitignore', 1, '# scripts/gretil_library.py (free, read-only); the zips are under sources/, ignored above\ndata/gretil/\n',
     "# scripts/gretil_library.py (free, read-only); the zips are under sources/, ignored above\ndata/gretil/\n# AUTO_REPAIR_2026_10_25: the repair rounds' allowance, log, state and lock are the desk's own (scripts/repair_auto.py)\ndata/auto_repair.json\ndata/auto_repair_log.jsonl\ndata/auto_repair_state.json\ndata/auto_repair.lock\ndata/auto_repair*.tmp\n")


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
