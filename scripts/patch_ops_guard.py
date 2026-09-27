#!/usr/bin/env python3
"""patch_ops_guard.py  (MARKS SINGLE_INSTANCE_2026_09_27, MT_TIMEOUT_2026_09_27,
HUB_SINGLE_2026_09_27, RUNBOOK_OPS_2026_09_27)

Measured 2026-09-27 on this machine, from data/jobs.jsonl and the process list:

  * 14:46:42  Karan_Aagama en ended rc=0xC000013A (console closed / Ctrl+C) after
    "[gemini] retry 1/3 ... Timeout of 600.0s exceeded, last exception: 503 failed
    to connect to all addresses". The dashboard died with it; 35 queued jobs were
    lost from memory (BA -Queue rebuilt them from context.db at 14:53).
  * 15:14:49 - 15:48:19  Bodhicaryavatara wrote nothing for 33 minutes, then was
    "[KILLED by user]". One Gemini call may wait 600 s and is tried 3 times: a
    network drop can hold the single translate lane for ~30 minutes.
  * 15:05:02  a SECOND scripts\\dashboard.py (pid 21432) started beside the one
    holding the queue (pid 41088, 14:53:12). RUNBOOK section 3h: "Never: run two
    dashboards". The hub's start guard is an HTTP GET with a 2.5 s timeout, so a
    busy dashboard looks "down"; the dashboard itself never checks the port.

Changes (all additive; nothing already running is touched):
  scripts/dashboard.py  SINGLE_INSTANCE: before app.run, if something already
                        accepts TCP connections on host:port, print [REFUSED] and
                        exit 3. Only a NEW start is affected.
  scripts/infer_mt.py   MT_TIMEOUT: every generate_content call passes
                        request_options={"timeout": MT_REQUEST_TIMEOUT} (default
                        120 s; 0 disables) when the installed SDK supports it
                        (checked by signature, never by trial call).
  srangam-hub/hub.py    HUB_SINGLE: start-automaton is refused when port 5057
                        accepts a TCP connection, as well as when /api/status
                        answers. Takes effect when the hub is next started.
  RUNBOOK.md            RUNBOOK_OPS: the three rules above, and the Srangam
                        status refresh as step 5 of routine 3h.

  python scripts/patch_ops_guard.py --root . --hub "..\\srangam-hub"           # check
  python scripts/patch_ops_guard.py --root . --hub "..\\srangam-hub" --apply   # write
Backups *.bak_og_20260927; line endings preserved; atomic replace.
"""
import argparse, os, py_compile, shutil, sys
from pathlib import Path

BAK = ".bak_og_20260927"

EDITS = [
  ('root', 'scripts/dashboard.py', 'SINGLE_INSTANCE_2026_09_27', [
    ('refuse a second instance',
     '    app.run(host=args.host, port=args.port, debug=False)\n',
     '    # SINGLE_INSTANCE_2026_09_27. JOBS live in this process\'s memory, so a second\n'
     '    # dashboard beside a running one splits the queue and the translate lock in\n'
     '    # two (2026-09-27: pid 21432 started at 15:05 beside pid 41088). Refuse.\n'
     '    import socket as _si_socket\n'
     '    _si_host = "127.0.0.1" if args.host in ("", "0.0.0.0", "::") else args.host\n'
     '    try:\n'
     '        with _si_socket.create_connection((_si_host, args.port), timeout=1.5):\n'
     '            print(f"[REFUSED] something already answers on {_si_host}:{args.port} - "\n'
     '                  "not starting a second dashboard (RUNBOOK 3h). Use "\n'
     '                  "scripts\\\\restart_dashboard.ps1 to replace it.")\n'
     '            sys.exit(3)\n'
     '    except OSError:\n'
     '        pass\n'
     '    app.run(host=args.host, port=args.port, debug=False)\n'),
  ]),
  ('root', 'scripts/infer_mt.py', 'MT_TIMEOUT_2026_09_27', [
    ('timeout helper',
     '_FALLBACK_MODEL = os.environ.get("MT_FALLBACK_MODEL", "gemini-2.0-flash").strip()\n',
     '_FALLBACK_MODEL = os.environ.get("MT_FALLBACK_MODEL", "gemini-2.0-flash").strip()\n'
     '\n'
     '# MT_TIMEOUT_2026_09_27. Without a request timeout the SDK waits up to 600 s\n'
     '# per call on a dead connection, and RETRIES=3 - one network drop held the\n'
     '# single translate lane for 33 minutes on 2026-09-27. The longest real call\n'
     '# measured that day was 33.8 s. MT_REQUEST_TIMEOUT=0 restores the old wait.\n'
     '_REQ_TIMEOUT = float(os.environ.get("MT_REQUEST_TIMEOUT", "120") or 0)\n'
     '_REQ_OPTS_OK = None\n'
     '\n'
     '\n'
     'def _gen(gm, msg):\n'
     '    """gm.generate_content(msg) with a bounded wait when the SDK supports it."""\n'
     '    global _REQ_OPTS_OK\n'
     '    if _REQ_OPTS_OK is None:\n'
     '        import inspect\n'
     '        try:\n'
     '            _REQ_OPTS_OK = "request_options" in inspect.signature(gm.generate_content).parameters\n'
     '        except (TypeError, ValueError):\n'
     '            _REQ_OPTS_OK = False\n'
     '    if _REQ_OPTS_OK and _REQ_TIMEOUT > 0:\n'
     '        return gm.generate_content(msg, request_options={"timeout": _REQ_TIMEOUT})\n'
     '    return gm.generate_content(msg)\n'),
    ('escalation call bounded',
     '    resp = gm.generate_content(msg)\n',
     '    resp = _gen(gm, msg)   # MT_TIMEOUT_2026_09_27\n'),
    ('main call bounded',
     '                resp = gm.generate_content(msgs_to_use[i].strip())\n',
     '                resp = _gen(gm, msgs_to_use[i].strip())   # MT_TIMEOUT_2026_09_27\n'),
  ]),
  ('hub', 'hub.py', 'HUB_SINGLE_2026_09_27', [
    ('tcp port probe',
     'def check(url: str, timeout: float = 2.5):\n',
     'def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:\n'
     '    """HUB_SINGLE_2026_09_27: a busy dashboard can miss a 2.5 s HTTP check but\n'
     '    still owns its port; a TCP connect tells the two apart."""\n'
     '    import socket\n'
     '    try:\n'
     '        with socket.create_connection((host, port), timeout=timeout):\n'
     '            return True\n'
     '    except OSError:\n'
     '        return False\n'
     '\n'
     '\n'
     'def check(url: str, timeout: float = 2.5):\n'),
    ('start guard uses the port too',
     '    if action == "start-automaton" and check(URLS["automaton"] + "/api/status")["up"]:\n',
     '    if action == "start-automaton" and (_port_open("127.0.0.1", 5057)\n'
     '                                        or check(URLS["automaton"] + "/api/status")["up"]):\n'),
  ]),
  ('root', 'RUNBOOK.md', 'RUNBOOK_OPS_2026_09_27', [
    ('3h: status refresh + operating rules',
     'Never: run two dashboards, run `purge_empty_cache.py --yes`',
     '5. Refresh the public status on Srangam (it is a generated file, not live):\n'
     '   `& \'D:\\Sanksrit Automatons\\_ops_2026-09-10\\block_BD_status.ps1\' -Emit -Commit`, then press Publish in Lovable.\n'
     '   - This runs `D:\\srangam-42267\\scripts\\emit_project_status.py`, which measures `context.db` read-only and commits only `src/data/projectStatus.ts`.\n'
     '   - It refuses to commit if the Srangam repo has diverged from origin.\n'
     '\n'
     'Operating rules (RUNBOOK_OPS_2026_09_27):\n'
     '- **Run blocks in their own PowerShell window.** Closing the "Sanskrit Dashboard" window, or pressing Ctrl+C in it, kills the dashboard. It also drops every queued job (2026-09-27 14:46). The plan rebuilds them: `block_BA_continuity.ps1 -Queue`.\n'
     '- **A second dashboard now refuses to start** (`[REFUSED]`, exit 3). The hub also refuses when port 5057 is taken.\n'
     '  - To check for strays: `Get-CimInstance Win32_Process -Filter "Name like \'python%\'" | ? CommandLine -match \'dashboard.py\'`.\n'
     '  - More than one is a fault. Keep the one that owns port 5057, `(Get-NetTCPConnection -LocalPort 5057 -State Listen).OwningProcess`, and stop the other only if it has no child processes.\n'
     '- **Model calls are bounded** by `MT_REQUEST_TIMEOUT` (seconds, default 120, set in `.env`). A stalled job (no change to `data\\translation_progress.json` for 10+ minutes) is a network hang. Stop that job\'s `translate_passages` process, never the dashboard; the next job starts and the verse is retried by the next plan.\n'
     '\n'
     'Never: run two dashboards, run `purge_empty_cache.py --yes`'),
  ]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--hub", default=r"..\srangam-hub")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    roots = {"root": Path(a.root), "hub": Path(a.hub)}
    plan, bad = [], 0
    for rk, rel, mark, eds in EDITS:
        p = roots[rk] / rel
        if not p.exists():
            print("  MISSING  %s" % p); bad += 1; continue
        raw = p.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        if mark in text:
            print("  already  %s (%s present) - skipped" % (rel, mark)); continue
        new = text
        for name, old, rep in eds:
            n = new.count(old)
            if n != 1:
                print("  ANCHOR   %s :: %s matched %d time(s), need exactly 1" % (rel, name, n))
                bad += 1; continue
            new = new.replace(old, rep, 1)
            print("  ok       %s :: %s" % (rel, name))
        if mark not in new:
            print("  ANCHOR   %s :: marker not present after edits" % rel); bad += 1
        plan.append((p, crlf, new))
    if bad:
        print("REFUSED: %d problem(s); nothing written." % bad); return 2
    if not plan:
        print("nothing to do - every file already patched."); return 0
    for p, crlf, new in plan:
        if p.suffix == ".py":
            try:
                compile(new, str(p), "exec")
            except SyntaxError as e:
                print("REFUSED: %s would not compile: %s" % (p.name, e)); return 2
    if not a.apply:
        print("CHECK PASSED for %d file(s). Re-run with --apply to write." % len(plan)); return 0
    for p, crlf, new in plan:
        bak = p.with_name(p.name + BAK)
        if not bak.exists():
            shutil.copy2(p, bak)
        tmp = p.with_name(p.name + ".tmp_patch")
        tmp.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
        os.replace(str(tmp), str(p))
        if p.suffix == ".py":
            py_compile.compile(str(p), doraise=True)
        print("  WROTE    %s  (backup %s)" % (p, bak.name))
    print("APPLIED. To undo: copy each %s back over its file." % BAK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
