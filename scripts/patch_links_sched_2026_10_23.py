#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_links_sched_2026_10_23.py  ENTITY_LINKS_SCHED_2026_10_23

The links our texts make between the names, kept current by the hourly maintenance task (the context and the
interrelationships "cronning"):

  scripts/entity_links.py        --scheduled: it writes only when the names changed since the last rebuild (the
                                 counts differ); the day's backup (D:\\backups\\context_daily.db or context_YYYYMMDD.db,
                                 made by the 04:00 task, under 26 hours old) stands for the backup the rebuild wants, else
                                 one is made; a writer running in the dashboard leaves it to the next tick (exit 0). A
                                 missing claims database does not stop the rebuild.
  scripts/maintenance_runner.ps1 step d after step c (the names): entity_links.py --scheduled --claims
                                 data\\shelf\\claims.db (the scholars' check refreshed), then kin_index.py --check once
                                 data\\shelf\\kin.db is there. Free. A failure is logged and skipped.

Needs ENTITY_LINKS_2026_10_22 and DESK_HEAL_2026_10_10. Marker-idempotent per file, all-or-nothing, backup first
(.bak_linkssched_<date>), line endings kept, py_compile before anything is written.

  python scripts\\patch_links_sched_2026_10_23.py --check
  python scripts\\patch_links_sched_2026_10_23.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ENTITY_LINKS_SCHED_2026_10_23'
TAG = 'linkssched'
FILES = ['scripts/entity_links.py', 'scripts/maintenance_runner.ps1']
NEEDS = {'scripts/entity_links.py': 'ENTITY_LINKS_2026_10_22', 'scripts/maintenance_runner.ps1': 'DESK_HEAL_2026_10_10'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/entity_links.py', 1, '                                                      writes exports\\\\claims_in_our_texts.csv and .json\n  python scripts\\\\entity_links.py --db D:\\\\backups\\\\some_backup.db --immutable --claims data\\\\shelf\\\\claims.db\n\nThe tables (nothing else in the database is written; to undo: DROP TABLE entity_links; DROP TABLE entity_link_runs;',
     "                                                      writes exports\\\\claims_in_our_texts.csv and .json\n  python scripts\\\\entity_links.py --db D:\\\\backups\\\\some_backup.db --immutable --claims data\\\\shelf\\\\claims.db\n  python scripts\\\\entity_links.py --scheduled --claims data\\\\shelf\\\\claims.db\n                                                      ENTITY_LINKS_SCHED_2026_10_23: the maintenance runner's step (every\n                                                      tick): it writes only when the names changed since the last run\n                                                      (the counts differ), and the day's backup (D:\\\\backups\\\\\n                                                      context_daily.db, under 26 hours old) stands for the backup the\n                                                      table's rebuild wants, else one is made; a writer running in the\n                                                      dashboard leaves it to the next tick\n\nThe tables (nothing else in the database is written; to undo: DROP TABLE entity_links; DROP TABLE entity_link_runs;")

edit('scripts/entity_links.py', 2, '\n\ndef apply(a, c: dict) -> int:\n    sys.path.insert(0, str(HERE))\n    import repair_text as rt   # noqa: E402  (writers_running, run: one way of doing each)\n    w = rt.writers_running(False)\n    if w:\n        print("REFUSE: the dashboard runs a database writer (%s); nothing was changed" % ", ".join(\n            "%s %s" % (j.get("kind"), j.get("doc")) for j in w))\n        print("NEXT: python scripts\\\\entity_links.py --apply   (when the dashboard is idle)")\n        return 1\n    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")\n    bdir = Path(a.backup_dir)\n    bdir.mkdir(parents=True, exist_ok=True)\n    backup = bdir / ("context_pre_links_%s.db" % stamp)\n    if rt.run([sys.executable, HERE / "db_backup.py", a.db, backup]) != 0 or not backup.exists():\n        print("REFUSE: the backup failed; nothing was changed")\n        return 1\n    at = datetime.datetime.now().isoformat(timespec="seconds")\n    con = sqlite3.connect(a.db, timeout=60)',
     '\n\nDAILY_MAX_AGE_H = 26   # ENTITY_LINKS_SCHED_2026_10_23: the 04:00 backup task\'s copy stands for a scheduled rebuild\'s\n\n\ndef recent_backup(bdir: Path, hours: float = DAILY_MAX_AGE_H):\n    """ENTITY_LINKS_SCHED_2026_10_23: the newest whole copy of the database in the backup folder made in the last\n    `hours` (the daily task\'s context_daily.db or context_YYYYMMDD.db, or this script\'s own), or None."""\n    best, now_ = None, datetime.datetime.now().timestamp()\n    for pat in ("context_daily.db", "context_2*.db", "context_pre_links_*.db"):\n        for f in bdir.glob(pat):\n            try:\n                t = f.stat().st_mtime\n            except OSError:\n                continue\n            if now_ - t <= hours * 3600 and (best is None or t > best[0]):\n                best = (t, f)\n    return best[1] if best else None\n\n\ndef last_run(db: str):\n    """ENTITY_LINKS_SCHED_2026_10_23: the last --apply\'s counts, or None."""\n    con = connect_ro(db)\n    try:\n        if not has(con, "entity_link_runs"):\n            return None\n        r = con.execute("SELECT at, entities, mentions, passages_named, lists_left_out, together, near, window FROM "\n                        "entity_link_runs ORDER BY id DESC LIMIT 1").fetchone()\n    finally:\n        con.close()\n    if not r:\n        return None\n    return {"at": r[0], "counts": tuple(r[1:])}\n\n\ndef counts_of(c: dict) -> tuple:\n    return (c["entities"], c["mentions"], c["passages_named"], c["lists_left_out"], c["together"], c["near"],\n            c["window"])\n\n\ndef apply(a, c: dict, scheduled: bool = False) -> int:\n    sys.path.insert(0, str(HERE))\n    import repair_text as rt   # noqa: E402  (writers_running, run: one way of doing each)\n    w = rt.writers_running(False)\n    if w:\n        print("%s: the dashboard runs a database writer (%s); nothing was changed" % (\n            "SKIP" if scheduled else "REFUSE", ", ".join("%s %s" % (j.get("kind"), j.get("doc")) for j in w)))\n        print("NEXT: python scripts\\\\entity_links.py --apply   (when the dashboard is idle)")\n        return 0 if scheduled else 1\n    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")\n    bdir = Path(a.backup_dir)\n    bdir.mkdir(parents=True, exist_ok=True)\n    backup = recent_backup(bdir) if scheduled else None\n    if backup is not None:\n        print("the backup: %s (made within %d hours) stands for this rebuild" % (backup, DAILY_MAX_AGE_H))\n    else:\n        backup = bdir / ("context_pre_links_%s.db" % stamp)\n        if rt.run([sys.executable, HERE / "db_backup.py", a.db, backup]) != 0 or not backup.exists():\n            print("REFUSE: the backup failed; nothing was changed")\n            return 1\n    at = datetime.datetime.now().isoformat(timespec="seconds")\n    con = sqlite3.connect(a.db, timeout=60)')

edit('scripts/entity_links.py', 3, '    ap.add_argument("--window", type=int, default=WINDOW)\n    ap.add_argument("--no-write", action="store_true", help="with --claims: write no export")\n    a = ap.parse_args(argv)\n    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a name in IAST must not stop it',
     '    ap.add_argument("--window", type=int, default=WINDOW)\n    ap.add_argument("--no-write", action="store_true", help="with --claims: write no export")\n    ap.add_argument("--scheduled", action="store_true", help="ENTITY_LINKS_SCHED_2026_10_23: the maintenance step")\n    a = ap.parse_args(argv)\n    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a name in IAST must not stop it')

edit('scripts/entity_links.py', 4, '        print("%s: no database at %s" % (MARK, a.db))\n        return 2\n    if a.apply and a.immutable:\n        print("REFUSE: --apply writes the database; an immutable copy is read only")\n        return 2',
     '        print("%s: no database at %s" % (MARK, a.db))\n        return 2\n    if (a.apply or a.scheduled) and a.immutable:\n        print("REFUSE: --apply writes the database; an immutable copy is read only")\n        return 2')

edit('scripts/entity_links.py', 5, '        con.close()\n    print(summary_line(c))\n    if built:\n        n = collections.Counter(k[2] for k in built)',
     '        con.close()\n    print(summary_line(c))\n    if a.scheduled:   # ENTITY_LINKS_SCHED_2026_10_23: nothing to write when the names did not change\n        last = last_run(a.db)\n        if last and last["counts"] == counts_of(c):\n            print("SCHEDULED: the names are as at the last rebuild (%s); nothing written" % last["at"])\n            return 0\n        a.apply = True\n    if built:\n        n = collections.Counter(k[2] for k in built)')

edit('scripts/entity_links.py', 6, '            print("    %-8s %4d passages, %d texts  %-28s (%s)  e.g. %s" % (\n                r["rel"], r["passages"], r["texts"], r["with"][:28], r["kind"], "; ".join(r["places"][:2])))\n    if a.claims:\n        if not Path(a.claims).exists():\n            print("%s: no claims database at %s" % (MARK, a.claims))\n            return 2\n        k = claims_check(c, a.claims)\n        v = k["verdicts"]',
     '            print("    %-8s %4d passages, %d texts  %-28s (%s)  e.g. %s" % (\n                r["rel"], r["passages"], r["texts"], r["with"][:28], r["kind"], "; ".join(r["places"][:2])))\n    if a.claims and not Path(a.claims).exists():\n        print("%s: no claims database at %s" % (MARK, a.claims))\n        if not a.scheduled:\n            return 2\n        a.claims = ""   # ENTITY_LINKS_SCHED_2026_10_23: the links are rebuilt all the same\n    if a.claims:\n        k = claims_check(c, a.claims)\n        v = k["verdicts"]')

edit('scripts/entity_links.py', 7, '            print("written: %s, claims_in_our_texts.json" % (out / "claims_in_our_texts.csv"))\n    if a.apply:\n        return apply(a, c)\n    if not built:\n        print("NEXT: python scripts\\\\entity_links.py --apply   (a backup first; the dashboard idle)")',
     '            print("written: %s, claims_in_our_texts.json" % (out / "claims_in_our_texts.csv"))\n    if a.apply:\n        return apply(a, c, scheduled=a.scheduled)\n    if not built:\n        print("NEXT: python scripts\\\\entity_links.py --apply   (a backup first; the dashboard idle)")')

edit('scripts/maintenance_runner.ps1', 1, '    & $py scripts\\extract_entities.py --db data\\context.db --limit 1500 2>&1 | Add-Content $log\n    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)\n\n    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)',
     '    & $py scripts\\extract_entities.py --db data\\context.db --limit 1500 2>&1 | Add-Content $log\n    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)\n    if (Test-Writer "c") { exit 0 }   # ENTITY_LINKS_SCHED_2026_10_23\n\n    # d) ENTITY_LINKS_SCHED_2026_10_23: the links our texts make between the names (FREE): entity_links rebuilt only\n    #    when the names changed (step c adds them), the day\'s backup standing for its own; then the scholars\' claims\n    #    and, once read, the indexes\' kinships checked against the links (FREE, read-only; the exports refreshed).\n    #    A failure here is logged and skipped. docs/RELATIONS_AND_ASK_2026-10-22.md.\n    $td = Get-Date\n    try {\n        & $py scripts\\entity_links.py --scheduled --claims data\\shelf\\claims.db 2>&1 | Add-Content $log\n        if (Test-Path "data\\shelf\\kin.db") { & $py scripts\\kin_index.py --check 2>&1 | Add-Content $log }\n        Log ("STEP d links        {0:n0}s" -f ((Get-Date) - $td).TotalSeconds)\n    } catch {\n        Log ("STEP d links SKIPPED after {0:n0}s: {1}" -f ((Get-Date) - $td).TotalSeconds, $_)\n    }\n\n    Log ("DONE maintenance - total {0:n0}s" -f ((Get-Date) - $t0).TotalSeconds)')


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
