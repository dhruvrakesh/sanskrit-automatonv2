#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
health_watch.py  (2026-10-23)  HEALTH_2026_10_23

The desk's health, read from what its scheduled tasks leave behind. Free and read-only: logs are read from their
ends, the database is opened read-only, nothing is written but the optional log line.

  maintenance  D:\\backups\\maintenance_log.txt (the hourly maintenance task): the task fires (a TICK in the last 6
               hours, else fail); it finishes (a DONE in the last 24 hours, else warn: every tick skipped, the
               dashboard busy); it did not fail after its last DONE (else fail)
  mirror       data\\corpus_sync_log.jsonl (corpus_sync.py, the mirror's task): its last run stopped done and found no
               group different (else fail), within 26 hours (else warn)
  backup       D:\\backups\\backup_log.txt (the 04:00 backup task): an OK in the last 26 hours (else warn; 50, fail)
  disk         the drive that holds the backups: under 50 GB free warn, under 15 GB fail
  spend        the cap (budget_state): paused, or under $2 left, warn
  links        entity_link_runs: the links last rebuilt more than 26 hours ago while the names changed since, warn
  repair       data\auto_repair_state.json (repair_auto.py's rounds, AUTO_REPAIR_2026_10_25), when there is one: blocked
               (the cap, or only decisions left) warn, with what it asks; no round for 30 hours while it has an
               allowance, warn

  python scripts\\health_watch.py               one line a check, then the verdict
  python scripts\\health_watch.py --json        the same as JSON
  python scripts\\health_watch.py --log         and one line in D:\\backups\\health_log.txt

The desk's round (corner_worker.py) sends health() with its heartbeat, compact(); with docs/cloud/C19 applied, the
site mails the super admin when it is warn or fail (again only after 12 hours or a change), and once when all is well
again. The last line is VERDICT:, as repair_text.py's.
"""
from __future__ import annotations
import argparse, datetime, json, os, re, shutil, sqlite3, sys, urllib.parse
from pathlib import Path

MARK = "HEALTH_2026_10_23"
ROOT = Path(__file__).resolve().parent.parent
TAIL_BYTES = 256 * 1024
TICK_H, DONE_H = 6, 24
MIRROR_H = 26
BACKUP_WARN_H, BACKUP_FAIL_H = 26, 50
DISK_WARN_GB, DISK_FAIL_GB = 50, 15
SPEND_WARN_USD = 2.0
LINE = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] (.*)$")
RANK = {"ok": 0, "warn": 1, "fail": 2}


def tail_lines(path: Path, nbytes: int = TAIL_BYTES) -> list:
    try:
        with open(path, "rb") as f:
            end = f.seek(0, os.SEEK_END)
            f.seek(max(0, end - nbytes))
            data = f.read()
    except OSError:
        return []
    lines = data.decode("utf-8", "replace").splitlines()
    return lines[1:] if end > nbytes else lines


def stamped(lines: list) -> list:
    out = []
    for ln in lines:
        m = LINE.match(ln.strip())
        if m:
            try:
                out.append((datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"), m.group(2)))
            except ValueError:
                pass
    return out


def hours(since: datetime.datetime, now: datetime.datetime) -> float:
    return (now - since).total_seconds() / 3600.0


def check_maintenance(path: Path, now) -> dict:
    ev = stamped(tail_lines(path))
    if not ev:
        return {"state": "fail", "say": "maintenance: no log at %s" % path}
    ticks = [t for t, m in ev if m.startswith("TICK")]
    dones = [t for t, m in ev if m.startswith("DONE")]
    fails = [(t, m) for t, m in ev if m.startswith("FAIL")]
    if not ticks or hours(ticks[-1], now) > TICK_H:
        return {"state": "fail", "say": "maintenance: the task has not fired since %s" % (
            ticks[-1].strftime("%d %b %H:%M") if ticks else "the log began")}
    if fails and (not dones or fails[-1][0] > dones[-1]):
        return {"state": "fail", "say": "maintenance: failed at %s (%s)" % (fails[-1][0].strftime("%d %b %H:%M"),
                                                                          fails[-1][1][:80])}
    if not dones or hours(dones[-1], now) > DONE_H:
        return {"state": "warn", "say": "maintenance: no run finished since %s (every tick skipped)" % (
            dones[-1].strftime("%d %b %H:%M") if dones else "the log began")}
    return {"state": "ok", "say": "maintenance: last finished %s" % dones[-1].strftime("%d %b %H:%M")}


def last_json(path: Path):
    for ln in reversed(tail_lines(path)):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict):
            return rec
    return None


def parse_ts(v):
    s = str(v or "").strip().replace("Z", "+00:00")
    try:
        t = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if t.tzinfo is not None:
        t = t.astimezone().replace(tzinfo=None)
    return t


def check_mirror(path: Path, now) -> dict:
    rec = last_json(path)
    if rec is None:
        return {"state": "warn", "say": "mirror: no run recorded (%s)" % path.name}
    v = rec.get("verified") if isinstance(rec.get("verified"), dict) else {}
    diff = v.get("groups_different")
    t = parse_ts(rec.get("ts"))
    if rec.get("stopped") != "done" or (isinstance(diff, int) and diff > 0):
        return {"state": "fail", "say": "mirror: the last run stopped %s%s" % (
            rec.get("stopped") or "?", (", %d groups different" % diff) if isinstance(diff, int) and diff else "")}
    if t is None or hours(t, now) > MIRROR_H:
        return {"state": "warn", "say": "mirror: no run since %s" % (t.strftime("%d %b %H:%M") if t else "?")}
    return {"state": "ok", "say": "mirror: %s groups equal, %s" % (v.get("groups_equal", "?"), t.strftime("%d %b %H:%M"))}


def check_backup(path: Path, now) -> dict:
    oks = [t for t, m in stamped(tail_lines(path)) if m.startswith("OK")]
    if not oks:
        return {"state": "warn", "say": "backup: no daily backup recorded (%s)" % path.name}
    h = hours(oks[-1], now)
    state = "fail" if h > BACKUP_FAIL_H else ("warn" if h > BACKUP_WARN_H else "ok")
    return {"state": state, "say": "backup: the last daily copy %s" % oks[-1].strftime("%d %b %H:%M")}


def check_disk(folder: Path) -> dict:
    try:
        free = shutil.disk_usage(folder).free / 1e9
    except OSError:
        return {"state": "warn", "say": "disk: %s not readable" % folder}
    state = "fail" if free < DISK_FAIL_GB else ("warn" if free < DISK_WARN_GB else "ok")
    return {"state": state, "say": "disk: %.0f GB free where the backups are" % free}


def _ro(db: Path):
    p = db.resolve().as_posix()
    p = p if p.startswith("/") else "/" + p
    return sqlite3.connect("file://%s?mode=ro" % urllib.parse.quote(p, safe="/:"), uri=True, timeout=10)


def check_db(db: Path, now) -> list:
    if not db.exists():
        return [{"state": "warn", "say": "database: none at %s" % db}]
    out = []
    try:
        con = _ro(db)
        try:
            tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "budget_state" in tabs:
                r = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
                if r:
                    left = (r[0] or 0) - (r[1] or 0)
                    state = "warn" if r[2] or left < SPEND_WARN_USD else "ok"
                    out.append({"state": state, "say": "spend: $%.2f of $%.2f%s" % (r[1] or 0, r[0] or 0,
                                                                                  ", paused" if r[2] else "")})
            if "entity_link_runs" in tabs and "entity_mentions" in tabs:
                r = con.execute("SELECT at, mentions FROM entity_link_runs ORDER BY id DESC LIMIT 1").fetchone()
                if r:
                    n = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
                    t = parse_ts(r[0])
                    stale = t is not None and hours(t, now) > MIRROR_H and n != r[1]
                    out.append({"state": "warn" if stale else "ok", "say": "links: rebuilt %s%s" % (
                        t.strftime("%d %b %H:%M") if t else "?", ", the names changed since" if stale else "")})
        finally:
            con.close()
    except sqlite3.Error as e:
        out.append({"state": "warn", "say": "database: not read (%s)" % str(e)[:60]})
    return out


REPAIR_H = 30


def check_repair(path: Path, now):
    """AUTO_REPAIR_2026_10_25: the state the last round left; None when the rounds have never run."""
    if not path.exists():
        return None
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "warn", "say": "repair: the rounds' state does not read"}
    t = parse_ts(st.get("at"))
    asks = [a.get("say", "") for a in (st.get("asks") or []) if isinstance(a, dict)]
    if st.get("status") == "blocked":
        return {"state": "warn", "say": "repair: " + (asks[0] if asks else "blocked")}
    if t is not None and hours(t, now) > REPAIR_H and float(st.get("allowance") or 0) > 0:
        return {"state": "warn", "say": "repair: no round since %s" % t.strftime("%d %b %H:%M")}
    d = st.get("did") or {}
    return {"state": "ok", "say": "repair: %s%s" % (st.get("status", "?"), (", %s %s" % (d.get("step"), d.get("doc")))
                                                      if d.get("doc") else "")}


def health(root: Path = ROOT, backup_dir: str = "", now=None) -> dict:
    now = now or datetime.datetime.now()
    bdir = Path(backup_dir or os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    checks = {"maintenance": check_maintenance(bdir / "maintenance_log.txt", now),
              "mirror": check_mirror(root / "data" / "corpus_sync_log.jsonl", now),
              "backup": check_backup(bdir / "backup_log.txt", now),
              "disk": check_disk(bdir if bdir.exists() else root)}
    for c in check_db(root / "data" / "context.db", now):
        checks[c["say"].split(":", 1)[0]] = c
    rep = check_repair(root / "data" / "auto_repair_state.json", now)   # AUTO_REPAIR_2026_10_25
    if rep:
        checks["repair"] = rep
    status = max((c["state"] for c in checks.values()), key=lambda s: RANK[s])
    return {"mark": MARK, "status": status, "at": now.strftime("%Y-%m-%dT%H:%M:%S"), "checks": checks,
            "problems": [c["say"] for c in checks.values() if c["state"] != "ok"]}


def compact(h: dict) -> dict:
    """What the heartbeat carries (corner.worker.info.health): the status, when, and the problems, short."""
    return {"status": h.get("status"), "at": h.get("at"), "problems": [str(p)[:120] for p in (h.get("problems") or [])[:6]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the desk's health (%s)" % MARK)
    ap.add_argument("--root", default="")
    ap.add_argument("--backup-dir", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--log", action="store_true", help="one line in the backup folder's health_log.txt")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    root = Path(a.root).resolve() if a.root else ROOT
    h = health(root, a.backup_dir)
    if a.json:
        print(json.dumps(h, ensure_ascii=False, indent=1))
    else:
        for name, c in h["checks"].items():
            print("  %-4s %s" % (c["state"], c["say"]))
    if a.log:
        bdir = Path(a.backup_dir or os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
        try:
            with open(bdir / "health_log.txt", "a", encoding="utf-8") as f:
                f.write("[%s] %s %s\n" % (h["at"].replace("T", " "), h["status"].upper(), "; ".join(h["problems"]) or "all well"))
        except OSError as e:
            print("the log line was not written: %s" % e)
    print("VERDICT: %s%s" % (h["status"], (": " + "; ".join(h["problems"])) if h["problems"] else ": all well"))
    return 0 if h["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
