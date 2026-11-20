#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_entity_allowance_2026_11_20.py  (2026-11-20)  ENTITY_ALLOWANCE_2026_11_20

The scheduled entity extraction gets a daily allowance. On 17 to 19 Nov the 3-hourly maintenance run (step c) read
7,937 newly translated verses with Gemini 2.5 Flash for $12.13 (usage_log, kind entities) with nobody asking; only the
budget cap stopped it ($161.36 of $162). Now:

  scripts/extract_entities.py    --per-day-usd (a scheduled run's allowance: today's entity spend, the UTC day, as
                                 usage_log records it) and --max-usd (this run's ceiling); past either it stops and
                                 prints "ASK (allowance)" with the verses that wait, about their cost and the command
                                 that reads them; without the flags it runs as before
  scripts/maintenance_runner.ps1 step c passes --per-day-usd 0.25

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_entityallow_<date> copies.

  python scripts\\patch_entity_allowance_2026_11_20.py --check
  python scripts\\patch_entity_allowance_2026_11_20.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ENTITY_ALLOWANCE_2026_11_20'
TAG = 'entityallow'
FILES = ['scripts/extract_entities.py', 'scripts/maintenance_runner.ps1']
NEEDS = {'scripts/extract_entities.py': 'METER_GATES_2026_10_04', 'scripts/maintenance_runner.ps1': 'ENTITY_LINKS_SCHED_2026_10_23'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/extract_entities.py', 1, '  python scripts/extract_entities.py --db data/context.db --doc MBh01      # one text\n  python scripts/extract_entities.py --db data/context.db --refresh        # redo all\n"""\nfrom __future__ import annotations',
     '  python scripts/extract_entities.py --db data/context.db --doc MBh01      # one text\n  python scripts/extract_entities.py --db data/context.db --refresh        # redo all\n  python scripts/extract_entities.py --db data/context.db --limit 1500 --per-day-usd 0.25   # the scheduled run\n\nENTITY_ALLOWANCE_2026_11_20: --per-day-usd is a scheduled run\'s allowance (today\'s entity spend, the UTC day, as\nusage_log records it); --max-usd is this run\'s ceiling. Past either the run stops, says how many verses wait, about\nwhat they cost and the command that spends it, as repair_auto.py\'s allowance does. Why: on 17 to 19 Nov the 3-hourly\nmaintenance run read 7,937 newly translated verses here for $12.13 of Gemini with nobody asking; only the budget cap\nstopped it. The budget cap (usage_meter.budget_ok) still applies to every run.\n"""\nfrom __future__ import annotations')

edit('scripts/extract_entities.py', 2, 'def _now():\n    return datetime.now(timezone.utc).isoformat()\n\n',
     'def _now():\n    return datetime.now(timezone.utc).isoformat()\n\n\nPER_VERSE_USD = 0.0015   # ENTITY_ALLOWANCE_2026_11_20: a verse\'s cost when usage_log has none (17-19 Nov: $0.00153)\n\n\ndef _spent_since(con, since_iso: str) -> float:\n    """ENTITY_ALLOWANCE_2026_11_20: the entity extraction\'s recorded spend since an ISO time (usage_log keeps UTC)."""\n    try:\n        v = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE kind = \'entities\' AND ts >= ?",\n                        (since_iso,)).fetchone()[0]\n        return float(v or 0)\n    except sqlite3.Error:\n        return 0.0\n\n\ndef _per_verse(con) -> float:\n    """ENTITY_ALLOWANCE_2026_11_20: what a verse has cost here, from usage_log."""\n    try:\n        v = con.execute("SELECT SUM(cost_usd) / NULLIF(SUM(passages), 0) FROM usage_log "\n                        "WHERE kind = \'entities\' AND cost_usd > 0").fetchone()[0]\n        return float(v) if v else PER_VERSE_USD\n    except sqlite3.Error:\n        return PER_VERSE_USD\n\n\ndef _ask(why: str, waiting: int, per_verse: float, db: str) -> str:\n    """ENTITY_ALLOWANCE_2026_11_20: what waits, about what it costs, and the one command that spends it."""\n    usd = max(0.01, round(waiting * per_verse + 0.005, 2))\n    return ("ASK (allowance): entity extraction waits: %s; %d verse(s) wait, about $%.2f; more: "\n            "python scripts\\\\extract_entities.py --db %s --limit %d --max-usd %.2f" % (why, waiting, usd, db, waiting, usd))\n\n')

edit('scripts/extract_entities.py', 3, '                    help="also re-process verses whose ents is \'[]\' (e.g. left empty by an "\n                         "earlier JSON-parse failure) \u2014 recovers dropped verses")\n    ap.add_argument("--debug-raw", action="store_true",\n                    help="print the first 400 chars of each raw model reply \u2014 use this when a "',
     '                    help="also re-process verses whose ents is \'[]\' (e.g. left empty by an "\n                         "earlier JSON-parse failure) \u2014 recovers dropped verses")\n    ap.add_argument("--per-day-usd", type=float, default=None,\n                    help="ENTITY_ALLOWANCE_2026_11_20: a scheduled run\'s allowance: stop once today\'s entity spend "\n                         "(the UTC day) reaches it")\n    ap.add_argument("--max-usd", type=float, default=None,\n                    help="ENTITY_ALLOWANCE_2026_11_20: this run\'s ceiling in dollars")\n    ap.add_argument("--debug-raw", action="store_true",\n                    help="print the first 400 chars of each raw model reply \u2014 use this when a "')

edit('scripts/extract_entities.py', 4, '            WHERE {\' AND \'.join(where)}\n            ORDER BY p.id""", params).fetchall()\n    if args.limit:\n        rows = rows[: args.limit]',
     '            WHERE {\' AND \'.join(where)}\n            ORDER BY p.id""", params).fetchall()\n    waiting_all = len(rows)   # ENTITY_ALLOWANCE_2026_11_20: every verse that waits, before --limit\n    if args.limit:\n        rows = rows[: args.limit]')

edit('scripts/extract_entities.py', 5, '        return\n\n    print(f"Extracting entities from {total} verses with {model} (batch={args.batch})\u2026")\n    cur = con.cursor()',
     '        return\n\n    import datetime as _dt   # ENTITY_ALLOWANCE_2026_11_20\n    _utc = _dt.datetime.now(_dt.timezone.utc)\n    day0, run0 = _utc.strftime("%Y-%m-%dT00:00:00"), _utc.strftime("%Y-%m-%dT%H:%M:%S")\n    per_verse = _per_verse(con)\n\n    def _over():\n        if args.per_day_usd is not None and _spent_since(con, day0) >= args.per_day_usd:\n            return "today\'s allowance is spent ($%.2f of $%.2f)" % (_spent_since(con, day0), args.per_day_usd)\n        if args.max_usd is not None and _spent_since(con, run0) >= args.max_usd:\n            return "this run\'s ceiling is reached ($%.2f of $%.2f)" % (_spent_since(con, run0), args.max_usd)\n        return ""\n    why = _over()\n    if why:\n        print(_ask(why, waiting_all, per_verse, args.db))\n        con.close()\n        return\n    print(f"Extracting entities from {total} verses with {model} (batch={args.batch})\u2026")\n    cur = con.cursor()')

edit('scripts/extract_entities.py', 6, '        if not _budget_ok(con):\n            print("  Stopping: the spend cap is reached. Raise it, then re-run to resume.")\n            break\n        try:',
     '        if not _budget_ok(con):\n            print("  Stopping: the spend cap is reached. Raise it, then re-run to resume.")\n            break\n        why = _over()   # ENTITY_ALLOWANCE_2026_11_20\n        if why:\n            print("  Stopping. " + _ask(why, waiting_all - start, per_verse, args.db))\n            break\n        try:')

edit('scripts/maintenance_runner.ps1', 1, '    # an old JSON-parse failure, run --retry-empty BY HAND with a --limit.\n    $tc = Get-Date\n    & $py scripts\\extract_entities.py --db data\\context.db --limit 1500 2>&1 | Add-Content $log\n    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)\n    if (Test-Writer "c") { exit 0 }   # ENTITY_LINKS_SCHED_2026_10_23',
     '    # an old JSON-parse failure, run --retry-empty BY HAND with a --limit.\n    $tc = Get-Date\n    # ENTITY_ALLOWANCE_2026_11_20: at most $0.25 a day of Gemini here; past it the log says ASK (allowance) with what\n    # waits and the one command that reads it (17-19 Nov: 7,937 new verses read for $12.13 with nobody asking).\n    & $py scripts\\extract_entities.py --db data\\context.db --limit 1500 --per-day-usd 0.25 2>&1 | Add-Content $log\n    Log ("STEP c entities     {0:n0}s" -f ((Get-Date) - $tc).TotalSeconds)\n    if (Test-Writer "c") { exit 0 }   # ENTITY_LINKS_SCHED_2026_10_23')


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

