#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
next_commands.py - turn the ledger's READY list into commands you can run.

FILE_VERSION = "2026-09-14.02"
MARK = "NEXT_COMMANDS_2026_09_14"

automaton.py --next answers WHICH unit is actionable. It has never been
able to answer WHAT TO RUN, because no file recorded which script
advances which stage. docs/STAGE_PLAYBOOK.json now records it, and this
reads both.

WHY THIS IS A SEPARATE FILE

automaton.py measures. It derives every status from the data and
declares nothing, and that is the only reason its numbers are worth
anything. A tool that both measures and executes will eventually report
on its own work. So the ledger stays a ledger, this turns it into
commands, and PowerShell runs them where a human can kill the window.

NOTHING HERE IS DUPLICATED FROM automaton.py. STAGES, DEPS, STATUS_OK
and retired_codes are imported from it, so the definition of "ready"
cannot drift between the two tools. If automaton.py changes its mind
about what a prerequisite is, this changes with it.

  python scripts/next_commands.py
  python scripts/next_commands.py --free-only
  python scripts/next_commands.py --stage morph --limit 60
  python scripts/next_commands.py --free-only --out run_free.ps1
  python scripts/next_commands.py --verify smriti_16harita_smriti_seg:morph
"""

import argparse
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FILE_VERSION = "2026-09-14.02"
MARK = "NEXT_COMMANDS_2026_09_14"

# PRECHECK_2026_09_14
import subprocess

_PRECHECK_CACHE = {}


def precheck_ok(stage, expr):
    """Run a stage's one-line precheck once. Emitting a command that cannot
    run is worse than emitting nothing: it looks like work."""
    if not expr:
        return True, ""
    if stage in _PRECHECK_CACHE:
        return _PRECHECK_CACHE[stage]
    try:
        r = subprocess.run([sys.executable, "-c", expr],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120)
        if r.returncode == 0:
            out = (True, "")
        else:
            txt = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
            out = (False, txt[-1] if txt else "exit %d" % r.returncode)
    except Exception as e:
        out = (False, str(e))
    _PRECHECK_CACHE[stage] = out
    return out


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from automaton import STAGES, DEPS, STATUS_OK, retired_codes, connect
except Exception as e:
    sys.exit("cannot import automaton.py from %s: %s\n"
             "This tool deliberately has no copy of STAGES or DEPS." % (HERE, e))

PLAYBOOK = os.path.join(os.path.dirname(HERE), "docs", "STAGE_PLAYBOOK.json")


def render(t, **kw):
    # str.format would choke on any literal brace in a command. This does not.
    for k, v in kw.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def load_board(con):
    board = {}
    for code, stage, status, reason in con.execute(
            "SELECT doc_code, stage, status, COALESCE(reason,'') FROM doc_stage"):
        board.setdefault(code, {})[stage] = (status, reason)
    return board


def sizes(con):
    out = {}
    for code, n in con.execute(
            "SELECT d.code, COUNT(p.id) FROM docs d LEFT JOIN passages p "
            "ON p.doc_id = d.id AND COALESCE(p.text_type,'mula') NOT IN "
            "('noise','frontmatter') AND TRIM(COALESCE(p.text,'')) <> '' "
            "GROUP BY d.code"):
        out[code] = n or 0
    return out


def ready_units(con):
    board = load_board(con)
    for c in retired_codes(con):
        board.pop(c, None)
    for c in list(board):
        if c.endswith("-RETIRED"):
            board.pop(c, None)
    n = sizes(con)
    out = []
    for code, st in board.items():
        for s in STAGES:
            status, reason = st.get(s, ("pending", ""))
            if status in STATUS_OK or status in ("blocked", "failed"):
                continue
            if all(st.get(d, ("pending", ""))[0] in STATUS_OK for d in DEPS.get(s, [])):
                out.append((n.get(code, 0), code, s, reason))
    return sorted(out, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--playbook", default=PLAYBOOK)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--stage", default=None)
    ap.add_argument("--doc", default=None)
    ap.add_argument("--min-rows", type=int, default=1,
                    help="skip units on documents with fewer live rows than "
                         "this. Default 1, which drops the empty shells.")
    ap.add_argument("--free-only", action="store_true",
                    help="omit any stage the playbook marks cost=paid")
    ap.add_argument("--allow-supervised", action="store_true",
                    help="also emit stages the playbook marks driver=false. "
                         "These are stages where the command is only step one "
                         "of a gated sequence; a loop must never be handed them.")
    ap.add_argument("--out", default=None,
                    help="write a PowerShell script that runs each unit and "
                         "re-measures after it")
    ap.add_argument("--verify", default=None, metavar="CODE:STAGE",
                    help="print the ledger status of one unit and exit")
    a = ap.parse_args()

    if not os.path.exists(a.playbook):
        sys.exit("playbook not found: %s" % a.playbook)
    pb = json.load(open(a.playbook, "rb")).get("stages", {})

    con = connect(a.db, writable=False)

    if a.verify:
        if ":" not in a.verify:
            sys.exit("--verify wants CODE:STAGE")
        code, stage = a.verify.split(":", 1)
        r = con.execute("SELECT status, COALESCE(reason,'') FROM doc_stage "
                        "WHERE doc_code=? AND stage=?", (code, stage)).fetchone()
        # status AND reason, because a stage that goes from 0% to 50% analysed
        # is still "pending" and the driver must count that as movement. A
        # status-only comparison would halt on real progress.
        print(("%s | %s" % (r[0], r[1])) if r else "absent")
        con.close()
        return 0

    units = ready_units(con)
    cats = dict((c, k or "") for c, k in con.execute(
        "SELECT code, COALESCE(category,'') FROM docs"))
    con.close()

    if a.stage:
        units = [u for u in units if u[2] == a.stage]
    if a.doc:
        units = [u for u in units if u[1] == a.doc]
    known = [s for s in STAGES if (pb.get(s) or {}).get("cmd")]
    unknown = [s for s in STAGES if not (pb.get(s) or {}).get("cmd")]

    print("%s  %d ready unit(s); playbook knows %d of %d stages"
          % (MARK, len(units), len(known), len(STAGES)))
    print("  commands recorded : %s" % ", ".join(known))
    print("  NOT recorded      : %s" % (", ".join(unknown) or "none"))
    print("")

    emitted = []
    skipped_paid = 0
    skipped_unknown = {}
    supervised = {}
    blocked = {}
    for n, code, stage, reason in units:
        if n < a.min_rows:
            continue
        spec = pb.get(stage) or {}
        cmd = spec.get("cmd")
        cost = spec.get("cost", "unknown")
        good, why = precheck_ok(stage, spec.get("precheck"))
        if not good:
            blocked[stage] = (blocked.get(stage, (0, why))[0] + 1, why)
            continue
        if spec.get("driver") is False and not a.allow_supervised:
            supervised[stage] = supervised.get(stage, 0) + 1
            continue
        if not cmd:
            skipped_unknown[stage] = skipped_unknown.get(stage, 0) + 1
            continue
        if a.free_only and cost != "free":
            skipped_paid += 1
            continue
        if len(emitted) >= a.limit:
            break
        emitted.append((n, code, stage, cost, render(
            cmd, db=a.db, code=code, category=cats.get(code, "") or "unknown"), reason))

    seen_note = set()
    for _n, _c, stage, _cost, _cmd, _r in emitted:
        if stage in seen_note:
            continue
        seen_note.add(stage)
        note = (pb.get(stage) or {}).get("note")
        if note:
            print("  %s: %s" % (stage, note))
    if seen_note:
        print("")

    for n, code, stage, cost, cmd, reason in emitted:
        print("  %-32s %-13s %7d rows  [%s]  %s"
              % (code[:32], stage, n, cost, reason[:28]))
        print("    %s" % cmd)
    if emitted:
        print("")

    if blocked:
        print("  BLOCKED - the precheck for these stages FAILED, so no command was")
        print("  emitted. Fix the environment, not the playbook:")
        for k in sorted(blocked):
            n, why = blocked[k]
            print("    %-14s %4d unit(s)   %s" % (k, n, why[:90]))
        print("")
    if supervised:
        print("  SUPERVISED, not emitted - these are step one of a gated sequence,")
        print("  not a command a loop may run: %s"
              % ", ".join("%s=%d" % (k, v) for k, v in sorted(supervised.items())))
        print("  Use block_AR_phase2.ps1 for segment. --allow-supervised overrides")
        print("  this, and you should not need it.")
    if skipped_paid:
        print("  %d unit(s) omitted by --free-only" % skipped_paid)
    if skipped_unknown:
        print("  omitted for having no recorded command: %s"
              % ", ".join("%s=%d" % (k, v) for k, v in sorted(skipped_unknown.items())))
        print("  Add them to %s when you have confirmed the command."
              % os.path.basename(a.playbook))

    if a.out and emitted:
        lines = []
        lines.append("# generated by next_commands.py on the ledger's READY list.")
        lines.append("# Every unit re-measures after it runs. If the ledger status")
        lines.append("# does not move, the loop STOPS - a step that reports success")
        lines.append("# without changing anything is the failure this project keeps")
        lines.append("# finding, and it should halt a driver, not be counted by one.")
        lines.append("$ErrorActionPreference = 'Continue'")
        lines.append("$done = 0")
        for i, (n, code, stage, cost, cmd, _r) in enumerate(emitted, 1):
            lines.append("")
            lines.append("Write-Host ''")
            lines.append("Write-Host '--- %d/%d  %s  %s  (%d rows, %s)'"
                         % (i, len(emitted), code, stage, n, cost))
            lines.append("$before = (& python scripts/next_commands.py --db \"%s\" --verify %s:%s)"
                         % (a.db, code, stage))
            lines.append(cmd)
            lines.append("if ($LASTEXITCODE -ne 0) { Write-Host '  STOP: command failed'; exit 1 }")
            lines.append("& python scripts/automaton.py --db \"%s\" --backfill | Out-Null" % a.db)
            lines.append("$after = (& python scripts/next_commands.py --db \"%s\" --verify %s:%s)"
                         % (a.db, code, stage))
            lines.append("Write-Host ('  ledger: ' + $before + ' -> ' + $after)")
            lines.append("if ($before -eq $after) { Write-Host '  STOP: the ledger did not move.'; exit 2 }")
            lines.append("$done++")
        lines.append("")
        lines.append("Write-Host ''")
        lines.append("Write-Host (' completed ' + $done + ' unit(s)')")
        open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("")
        print("  wrote %s - %d unit(s). READ IT BEFORE RUNNING IT." % (a.out, len(emitted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())