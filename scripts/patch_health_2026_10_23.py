#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_health_2026_10_23.py  HEALTH_2026_10_23

The desk's health in its heartbeat (the alerts): scripts/corner_worker.py's round sends, beside "sync", "health":
scripts/health_watch.py (new, in this release; free and read-only) read from the maintenance log, the mirror's log,
the daily backup's log, the disk, the cap and the links. With docs/cloud/C19 pasted in the Lovable Cloud SQL editor,
the site mails the super admin when the desk reports warn or fail (again only after 12 hours or a change), and once
when all is well again. The health is the first thing cut when the heartbeat is too long, to its status. Only the
desk's own round sets it (main()); a round without it is as before.

Needs CORNER_STATE_C10A_2026_10_09 and scripts/health_watch.py. Marker-idempotent, all-or-nothing, backup first
(.bak_health_<date>), line endings kept, py_compile before anything is written.

  python scripts\\patch_health_2026_10_23.py --check
  python scripts\\patch_health_2026_10_23.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'HEALTH_2026_10_23'
TAG = 'health'
FILES = ['scripts/corner_worker.py']
NEEDS = {'scripts/corner_worker.py': 'CORNER_STATE_C10A_2026_10_09'}
REQUIRES = {'scripts/health_watch.py': 'HEALTH_2026_10_23'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corner_worker.py', 1, 'LOG_TAIL_MAX_BYTES = 4 * 1024 * 1024    # a last line longer than this is not read\nINFO_MAX_CHARS = 3900                   # corner_desk_heartbeat and corpus-desk keep info up to 4000\nERROR_MAX_CHARS = 160\nPROGRESS_GAP_S = 5.0                    # at most one progress report this often (but the first and the last)',
     "LOG_TAIL_MAX_BYTES = 4 * 1024 * 1024    # a last line longer than this is not read\nINFO_MAX_CHARS = 3900                   # corner_desk_heartbeat and corpus-desk keep info up to 4000\nHEALTH = None                           # HEALTH_2026_10_23: main() sets it: the desk's health for the heartbeat\nERROR_MAX_CHARS = 160\nPROGRESS_GAP_S = 5.0                    # at most one progress report this often (but the first and the last)")

edit('scripts/corner_worker.py', 2, '\n\ndef heartbeat_info(budget, logs=None) -> dict:\n    """What the desk says about itself on each round (corner.worker.info; editors see it in corner_me()),\n    always under INFO_MAX_CHARS: the errors go first, then the sync channels."""\n    info = {"client": CLIENT, "budget": budget, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),\n            "sync": sync_state(*(tuple(logs) if logs else (None, None)))}\n    sync = info["sync"]\n    for cut in ("error", "channel"):',
     '\n\ndef heartbeat_info(budget, logs=None, health=None) -> dict:\n    """What the desk says about itself on each round (corner.worker.info; editors see it in corner_me()),\n    always under INFO_MAX_CHARS: the errors go first, then the sync channels. HEALTH_2026_10_23: with `health`\n    (scripts/health_watch.py\'s compact()), it is there too, and it is the first to be cut (to its status)."""\n    info = {"client": CLIENT, "budget": budget, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),\n            "sync": sync_state(*(tuple(logs) if logs else (None, None)))}\n    if isinstance(health, dict):   # HEALTH_2026_10_23\n        info["health"] = health\n        if info_chars(info) > INFO_MAX_CHARS:\n            info["health"] = {"status": health.get("status"), "at": health.get("at"),\n                              "problems": [str(p)[:60] for p in (health.get("problems") or [])[:2]]}\n        if info_chars(info) > INFO_MAX_CHARS:\n            info["health"] = {"status": health.get("status")}\n    sync = info["sync"]\n    for cut in ("error", "channel"):')

edit('scripts/corner_worker.py', 3, '\n\ndef run_once(desk, worker: Worker, limit: int, name: str = "desk", progress: bool = False, logs=None) -> dict:\n    """One round. progress: tell the site where each request is (CORNER_STATE_C10A_2026_10_09); logs:',
     '\n\ndef _desk_health():\n    """HEALTH_2026_10_23: the desk\'s health (scripts/health_watch.py), compact, for the heartbeat."""\n    import health_watch\n    return health_watch.compact(health_watch.health(ROOT))\n\n\ndef _health_now():\n    """HEALTH_2026_10_23: best effort; never the round\'s failure. None unless main() set HEALTH."""\n    if HEALTH is None:\n        return None\n    try:\n        return HEALTH()\n    except Exception as e:\n        return {"status": "warn", "problems": ["the health check failed: %s" % type(e).__name__]}\n\n\ndef run_once(desk, worker: Worker, limit: int, name: str = "desk", progress: bool = False, logs=None) -> dict:\n    """One round. progress: tell the site where each request is (CORNER_STATE_C10A_2026_10_09); logs:')

edit('scripts/corner_worker.py', 4, '    finally:\n        con.close()\n    hb = desk.heartbeat(heartbeat_info(b, logs)) or {}\n    if hb.get("scheme") not in (None, SCHEME):\n        raise SinkError("the site answers scheme %r, this script speaks %r" % (hb.get("scheme"), SCHEME))',
     '    finally:\n        con.close()\n    hb = desk.heartbeat(heartbeat_info(b, logs, _health_now())) or {}   # HEALTH_2026_10_23\n    if hb.get("scheme") not in (None, SCHEME):\n        raise SinkError("the site answers scheme %r, this script speaks %r" % (hb.get("scheme"), SCHEME))')

edit('scripts/corner_worker.py', 5, '            say = (lambda m: print("[%5.0fs] %s" % (time.time() - t0, m), flush=True)) if not a.json else None\n            w = Worker(a.db, sync=not a.no_sync, say=say)\n            s = run_once(desk, w, max(1, min(20, a.max)), "desk", progress=True, logs=(SYNC_LOG_PATH, MEDIA_LOG_PATH))\n            s["seconds"] = round(time.time() - t0, 1)',
     '            say = (lambda m: print("[%5.0fs] %s" % (time.time() - t0, m), flush=True)) if not a.json else None\n            w = Worker(a.db, sync=not a.no_sync, say=say)\n            globals()["HEALTH"] = _desk_health   # HEALTH_2026_10_23: the round\'s heartbeat carries the desk\'s health\n            s = run_once(desk, w, max(1, min(20, a.max)), "desk", progress=True, logs=(SYNC_LOG_PATH, MEDIA_LOG_PATH))\n            s["seconds"] = round(time.time() - t0, 1)')


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
