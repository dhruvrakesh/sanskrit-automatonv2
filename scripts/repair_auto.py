#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
repair_auto.py  (2026-10-25)  AUTO_REPAIR_2026_10_25

The repair of the scans, kept going by itself. Each round takes the text that most needs it and does the next step
of its path exactly as repair_text.py prints it (NEXT:), within an allowance set once; it asks only when the cap
stands in its way, or when the next step is a decision: translations already paid for would be replaced, or a text
is ready to translate.

  the queue    the texts repair_text.py --judge-all judged (data/source_judged/*.json; refreshed by the first round of
               each day: free, read-only), less those withdrawn, set aside, accepted as complete or as they are, being
               re-translated (in repair), the e-text witnesses and the Daivat-Sanhita (its rights). Ranked: a repaired
               text one step from the database that replaces nothing; then the texts whose pages vision has not
               read, material before moderate, the fewest pages left first (texts finished, not begun); then those
               whose next step is a decision.
  a round      the first of the day judges (repair_text.py --judge-all) and does nothing else; each other round does at
               most one step, of one text, after repair_text.py --doc X has said what the step is:
                 vision  NEXT: ... --repair --max-usd N: run with --max-usd the least of N, the round's limit ($0.10),
                         what is left of today's allowance and what the cap leaves above its reserve ($1.00). Vision
                         OCR of the pages not read, the audit and the merge: page files only, the database untouched;
                         repair_text.py and ocr_consensus.py stop before spending more
                 swap    NEXT: ... --use-repaired (nothing replaced): run only when the dashboard answers and runs no job,
                         the drive holds a backup and 15 GB besides, and no swap ran today. repair_text.py makes the
                         backup first and refuses while a writer runs
                 ask     NEXT: ... --use-repaired --replace N, reingest_pages.py, translate it: written down as a decision
                         and the next text is tried (five at most a round)
  what it asks data/auto_repair_state.json: "blocked" when the cap is paused or less than its reserve is left, or when
               nothing is left that may run without a decision. health_watch.py reads it: blocked is a warn, so the
               site mails the super admin (C19). Today's allowance spent is not an ask: the rounds wait for tomorrow.

  python scripts\\repair_auto.py                     the plan: the queue and the next step of the first texts; free
  python scripts\\repair_auto.py --allow 0.30        the allowance: at most $0.30 a day (0 stops the paid steps);
                                                     data/auto_repair.json. Without it: $0.25 a day
  python scripts\\repair_auto.py --round             one round (the maintenance task's step e)
  python scripts\\repair_auto.py --round --dry-run   what the round would run; nothing run, nothing written
  python scripts\\repair_auto.py --log               the last rounds

Every round appends to data/auto_repair_log.jsonl: the text, the step, the command, its VERDICT, what it spent
(budget_state's spent_usd before and after). The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations

import argparse, datetime, glob, json, os, re, shutil, sqlite3, subprocess, sys, threading, urllib.request
from pathlib import Path

MARK = "AUTO_REPAIR_2026_10_25"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(os.environ.get("SA_REPAIR_SCRIPTS") or (ROOT / "scripts"))   # the override is for the tests
PY = sys.executable
DASHBOARD = os.environ.get("SA_DASHBOARD_URL") or "http://127.0.0.1:5057"
DEFAULTS = {"usd_per_day": 0.25, "round_usd": 0.10, "reserve_usd": 1.00, "swap": True, "max_tries": 5,
            "step_minutes": 25}
SKIP_STATES = {"withdrawn", "set_aside", "complete", "translate_as_is", "in_repair", "witness"}
NEVER = {"Daivat-Sanhita"}           # withdrawn until 1 January 2029: its 2017 scan is local and private only
LEVEL = {"material": 0, "moderate": 1, "cosmetic": 2}
FREE_GB = 15.0


# ---- small things ----------------------------------------------------------------------------------------------
def now() -> datetime.datetime:
    return datetime.datetime.now()


def stamp() -> str:
    return now().isoformat(timespec="seconds")


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(p))


def append(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def config(p: Path) -> dict:
    c = dict(DEFAULTS)
    got = read_json(p, {})
    if isinstance(got, dict):
        for k in DEFAULTS:
            if k in got:
                c[k] = got[k]
        c["set_at"] = got.get("set_at", "")
    c["from_file"] = p.exists()
    return c


def rounds(log: Path) -> list:
    out = []
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def spent_today(log: Path, day: str) -> float:
    return round(sum(float(r.get("spent") or 0) for r in rounds(log) if str(r.get("at", "")).startswith(day)), 6)


def did_today(log: Path, day: str, step: str) -> bool:
    return any(r.get("step") == step and str(r.get("at", "")).startswith(day) and r.get("rc") == 0 for r in rounds(log))


def cap(db: Path):
    """(budget, spent, paused) of budget_state, read-only; None when it cannot be read."""
    try:
        con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            r = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
        finally:
            con.close()
        return (float(r[0] or 0), float(r[1] or 0), bool(r[2])) if r else None
    except sqlite3.Error:
        return None


def dashboard_jobs():
    """The dashboard's unfinished jobs, or None when it does not answer."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(DASHBOARD + "/api/jobs/running", timeout=6) as f:
            return json.loads(f.read().decode("utf-8")).get("running") or []
    except Exception:
        return None


def room(backup_dir: Path, db: Path) -> tuple:
    """(enough, free GB): the backup a swap makes, and 15 GB besides."""
    try:
        free = shutil.disk_usage(str(backup_dir if backup_dir.exists() else ROOT)).free / 1e9
        need = (db.stat().st_size / 1e9 if db.exists() else 0) + FREE_GB
        return free >= need, round(free, 1)
    except OSError:
        return False, 0.0


# ---- the queue -------------------------------------------------------------------------------------------------
def register(path: Path) -> dict:
    """The latest record of each text in data/source_verdicts.jsonl."""
    out = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc"):
                out[r["doc"]] = r
    except OSError:
        pass
    return out


def tier(nxt: str) -> int:
    n = nxt or ""
    if "--use-repaired" in n and "--replace" not in n:
        return 0
    if "--repair" in n:
        return 1
    if "--use-repaired" in n or "reingest_pages.py" in n:
        return 2
    return 3


def queue(judged_dir: Path, verdicts: Path) -> list:
    reg = register(verdicts)
    out = []
    for p in sorted(glob.glob(str(judged_dir / "*.json"))):
        d = read_json(Path(p), {})
        doc = d.get("doc") if isinstance(d, dict) else None
        if not doc or doc in NEVER or doc.endswith("-RETIRED") or "__w_" in doc:
            continue
        st = (reg.get(doc) or {}).get("status") or d.get("state") or ""
        if st in SKIP_STATES:
            continue
        pdfs, vp = int(d.get("pdfs") or 0), int(d.get("vision_pages") or 0)
        t = tier(d.get("next") or "")
        if t == 1 and not pdfs:
            continue
        out.append({"doc": doc, "level": d.get("level") or "-", "tier": t, "pages_left": max(0, pdfs - vp),
                    "pdfs": pdfs, "english": int(d.get("english") or 0), "passages": int(d.get("passages") or 0),
                    "next": d.get("next") or "", "judged_at": d.get("at", "")})
    out.sort(key=lambda q: (q["tier"], LEVEL.get(q["level"], 3), q["pages_left"], -q["english"], q["doc"]))
    return [q for q in out if q["tier"] < 3]


# ---- one text's next step ----------------------------------------------------------------------------------------
def run(argv: list, timeout_s: int, keep: list) -> int:
    """Run a step, its lines printed as they come (the maintenance log follows it) and kept; past the time limit the
    step and its children are stopped (taskkill /T on Windows: that process tree only)."""
    print("$ " + " ".join(str(x) for x in argv), flush=True)
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    kw = {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)} if os.name == "nt" else {}
    p = subprocess.Popen([str(x) for x in argv], cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **kw)

    def pump():
        for line in p.stdout:
            sys.stdout.write(line); sys.stdout.flush(); keep.append(line.rstrip("\n"))
    th = threading.Thread(target=pump, daemon=True)
    th.start()
    try:
        rc = p.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.call(["taskkill", "/PID", str(p.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        else:
            p.kill()
        p.wait(timeout=30)
        rc = 124
        keep.append("STOPPED: the step ran past %d minutes" % (timeout_s // 60))
    th.join(timeout=10)
    return rc


def said(lines: list, key: str) -> str:
    for line in reversed(lines):
        if line.startswith(key + ":"):
            return line[len(key) + 1:].strip()
    return ""


def classify(nxt: str) -> tuple:
    """(kind, detail) of a NEXT: line: vision (its --max-usd), swap, decision (the words), or other."""
    n = nxt or ""
    if "repair_text.py" in n and "--repair" in n and "--use-repaired" not in n:
        m = re.search(r"--max-usd\s+([0-9.]+)", n)
        return "vision", float(m.group(1)) if m else 1.0
    if "repair_text.py" in n and "--use-repaired" in n:
        return ("decision", n) if "--replace" in n else ("swap", None)
    if "reingest_pages.py" in n or "translate it" in n or "Finish EN" in n or "--release" in n:
        return "decision", n
    return "other", n


# ---- the round ---------------------------------------------------------------------------------------------------
class Paths:
    def __init__(self, a):
        d = Path(a.data) if a.data else ROOT / "data"
        self.db = Path(a.db) if a.db else d / "context.db"
        self.cfg = d / "auto_repair.json"
        self.log = d / "auto_repair_log.jsonl"
        self.state = d / "auto_repair_state.json"
        self.lock = d / "auto_repair.lock"
        self.judged = d / "source_judged"
        self.verdicts = d / "source_verdicts.jsonl"
        self.backup = Path(a.backup_dir)


def take_lock(p: Paths) -> bool:
    if p.lock.exists():
        old = read_json(p.lock, {})
        try:
            age = (now() - datetime.datetime.fromisoformat(old.get("at", ""))).total_seconds()
        except (ValueError, TypeError):
            age = 1e9
        if age < 4 * 3600:
            return False
    write_json(p.lock, {"pid": os.getpid(), "at": stamp(), "mark": MARK})
    return True


def free_lock(p: Paths) -> None:
    try:
        p.lock.unlink()
    except OSError:
        pass


def plan(a, p: Paths, cfg: dict) -> dict:
    day = now().strftime("%Y-%m-%d")
    st = {"mark": MARK, "at": stamp(), "allowance": cfg["usd_per_day"], "round_usd": cfg["round_usd"],
          "reserve_usd": cfg["reserve_usd"], "spent_today": spent_today(p.log, day), "asks": [], "did": None,
          "status": "idle"}
    c = cap(p.db)
    if c:
        st["cap"] = {"budget": c[0], "spent": round(c[1], 4), "left": round(c[0] - c[1], 4), "paused": c[2]}
    q = queue(p.judged, p.verdicts)
    st["queue"] = [{k: x[k] for k in ("doc", "level", "tier", "pages_left", "english", "judged_at")} for x in q[:10]]
    st["queue_n"] = len(q)
    return st


def round_(a, p: Paths, cfg: dict) -> int:
    day = now().strftime("%Y-%m-%d")
    st = plan(a, p, cfg)
    if not a.dry_run and not take_lock(p):
        print("%s: another round holds %s; this one stands aside" % (MARK, p.lock))
        print("VERDICT: not now: a round is running"); print("NEXT: "); return 0
    try:
        return _round(a, p, cfg, st, day)
    finally:
        if not a.dry_run:
            free_lock(p)


def _round(a, p: Paths, cfg: dict, st: dict, day: str) -> int:
    log_rec = lambda rec: (None if a.dry_run else append(p.log, dict(rec, at=stamp(), mark=MARK)))
    # the day's judgement, once, and that is the round (free, read-only on the database; the maintenance task has an
    # hour, so the round that judges does nothing else)
    if not a.dry_run and not did_today(p.log, day, "judge"):
        keep = []
        rc = run([PY, SCRIPTS / "repair_text.py", "--judge-all"], 15 * 60, keep)
        rec = {"step": "judge", "rc": rc, "verdict": said(keep, "VERDICT")[:300], "spent": 0, "doc": ""}
        log_rec(rec)
        st = plan(a, p, cfg)
        st["did"], st["status"] = rec, "working"
        write_json(p.state, st)
        say(st, False)
        return 0
    c = st.get("cap")
    left_cap = (c["left"] - cfg["reserve_usd"]) if c else 0.0
    left_day = max(0.0, float(cfg["usd_per_day"]) - st["spent_today"])
    paid_ok = bool(c) and not c["paused"] and left_cap > 0.01 and left_day > 0.01
    if c and (c["paused"] or left_cap <= 0.01):
        st["asks"].append({"kind": "cap", "say": "the repair waits for the cap: $%.2f of $%.2f spent%s (it keeps $%.2f "
                           "in reserve); raise the cap on the dashboard" % (c["spent"], c["budget"],
                                                                           ", paused" if c["paused"] else "",
                                                                           cfg["reserve_usd"])})
    if not c:
        st["asks"].append({"kind": "cap", "say": "the cap was not read (budget_state): the paid steps wait"})
    tried, decided = 0, 0
    jobs = None
    for item in queue(p.judged, p.verdicts):
        if tried >= int(cfg["max_tries"]):
            break
        tried += 1
        doc = item["doc"]
        keep = []
        rc = run([PY, SCRIPTS / "repair_text.py", "--doc", doc], 10 * 60, keep)
        nxt = said(keep, "NEXT")
        kind, detail = classify(nxt)
        print("%s: %s -> %s" % (MARK, doc, kind if kind != "other" else "nothing for the round (%s)" % (nxt or "no step")))
        if kind == "vision":
            if not paid_ok:
                continue
            spend = round(min(float(detail), float(cfg["round_usd"]), left_day, left_cap), 2)
            if spend < 0.02:
                continue
            argv = [PY, SCRIPTS / "repair_text.py", "--doc", doc, "--repair", "--max-usd", "%.2f" % spend]
            if a.dry_run:
                st["did"] = {"doc": doc, "step": "vision", "would_run": " ".join(str(x) for x in argv[1:])}
                break
            before = cap(p.db)
            keep2 = []
            rc2 = run(argv, int(cfg["step_minutes"]) * 60, keep2)
            after = cap(p.db)
            spent = round(max(0.0, (after[1] if after else 0) - (before[1] if before else 0)), 6)
            rec = {"doc": doc, "step": "vision", "rc": rc2, "max_usd": spend, "spent": spent,
                   "verdict": said(keep2, "VERDICT")[:300], "next": said(keep2, "NEXT")[:300]}
            log_rec(rec); st["did"] = rec; st["status"] = "working"
            break
        if kind == "swap":
            if not cfg.get("swap", True):
                continue
            if did_today(p.log, day, "swap"):
                continue
            jobs = dashboard_jobs() if jobs is None else jobs
            enough, free = room(p.backup, p.db)
            if jobs is None or jobs or not enough:
                why = ("the dashboard does not answer" if jobs is None else "the dashboard runs %d job(s)" % len(jobs)
                       if jobs else "the drive has %.0f GB free: the backup and 15 GB besides do not fit" % free)
                print("%s: %s is ready to go into the database, but %s" % (MARK, doc, why))
                continue
            argv = [PY, SCRIPTS / "repair_text.py", "--doc", doc, "--use-repaired"]
            if a.dry_run:
                st["did"] = {"doc": doc, "step": "swap", "would_run": " ".join(str(x) for x in argv[1:])}
                break
            keep2 = []
            rc2 = run(argv, 30 * 60, keep2)
            rec = {"doc": doc, "step": "swap", "rc": rc2, "spent": 0, "verdict": said(keep2, "VERDICT")[:300],
                   "next": said(keep2, "NEXT")[:300]}
            log_rec(rec); st["did"] = rec; st["status"] = "working"
            break
        if kind == "decision":
            decided += 1
            st["asks"].append({"kind": "decision", "doc": doc, "say": "%s: %s" % (doc, detail[:220])})
    if st["did"] is None:
        cap_ask = any(x["kind"] == "cap" for x in st["asks"])
        if cap_ask:
            st["status"] = "blocked"
        elif left_day <= 0.01 and float(cfg["usd_per_day"]) > 0:
            st["status"] = "waiting"     # today's allowance spent: tomorrow, not an ask
        elif float(cfg["usd_per_day"]) <= 0:
            st["status"] = "off"
        elif st["asks"]:
            st["status"] = "blocked"     # only decisions are left
        else:
            st["status"] = "idle"
    st["tried"] = tried
    if not a.dry_run:
        write_json(p.state, st)
    say(st, a.dry_run)
    return 0


def say(st: dict, dry: bool) -> None:
    c = st.get("cap") or {}
    print("%s: the allowance $%.2f a day, $%.2f spent today; the cap $%.2f of $%.2f spent%s" % (
        MARK, st["allowance"], st["spent_today"], c.get("spent", 0), c.get("budget", 0),
        ", paused" if c.get("paused") else ""))
    for x in st["asks"]:
        print("  ASK (%s): %s" % (x["kind"], x["say"]))
    d = st.get("did")
    if d and d.get("would_run"):
        print("VERDICT: the round would run: %s" % d["would_run"])
        print("NEXT: python scripts\\repair_auto.py --round"); return
    if d:
        print("VERDICT: %s %s: rc %s, $%.4f spent; %s" % (d["step"], d["doc"], d.get("rc"), d.get("spent", 0),
                                                         d.get("verdict", "")[:160]))
        print("NEXT: the next round (the maintenance task, every 3 hours)")
        return
    print("VERDICT: %s: nothing run%s" % (st["status"], "" if not st["asks"] else "; %d ask(s)" % len(st["asks"])))
    print("NEXT: %s" % ("raise the cap on the dashboard" if any(x["kind"] == "cap" for x in st["asks"]) else
                        "python scripts\\repair_auto.py   (the queue)"))
    if any(x["kind"] == "decision" for x in st["asks"]):
        print("ALSO: the decisions: python scripts\\repair_text.py --doc <the text>   (each prints its own step)"
              .replace("<the text>", next(x["doc"] for x in st["asks"] if x["kind"] == "decision")))


def show_plan(a, p: Paths, cfg: dict) -> int:
    st = plan(a, p, cfg)
    c = st.get("cap") or {}
    print("%s: the allowance $%.2f a day%s, $%.2f spent today; a round spends at most $%.2f; the cap: $%.2f of $%.2f "
          "spent, $%.2f kept in reserve" % (MARK, cfg["usd_per_day"], "" if cfg["from_file"] else " (the default)",
                                            st["spent_today"], cfg["round_usd"], c.get("spent", 0), c.get("budget", 0),
                                            cfg["reserve_usd"]))
    names = {0: "into the database (nothing replaced)", 1: "vision to read", 2: "a decision"}
    for i, x in enumerate(queue(p.judged, p.verdicts)[:25], 1):
        print("  %2d. %-52s %-9s %-36s pages left %4d, English %5d  (judged %s)" % (
            i, x["doc"][:52], x["level"], names[x["tier"]], x["pages_left"], x["english"], x["judged_at"][:10]))
    old = read_json(p.state, {})
    if old:
        print("  the last round: %s, %s%s" % (old.get("at", "?"), old.get("status", "?"),
                                              (": " + old["did"]["step"] + " " + old["did"]["doc"]) if old.get("did") else ""))
    print("VERDICT: %d text(s) in the queue" % st["queue_n"])
    print("NEXT: python scripts\\repair_auto.py --round --dry-run   (what the next round would run)")
    print("ALSO: python scripts\\repair_auto.py --allow %.2f   (the allowance a day; 0 stops the paid steps)"
          % cfg["usd_per_day"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--round", action="store_true", help="one round: one step of one text")
    ap.add_argument("--dry-run", action="store_true", help="with --round: say what would run; run nothing")
    ap.add_argument("--allow", type=float, default=None, help="the allowance in US dollars a day (0 stops it)")
    ap.add_argument("--log", action="store_true", help="the last rounds")
    ap.add_argument("--db", default="")
    ap.add_argument("--data", default="", help=argparse.SUPPRESS)   # the data folder (the tests)
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    p = Paths(a)
    if a.allow is not None:
        if a.allow < 0 or a.allow > 20:
            print("REFUSE: --allow takes 0 to 20 (US dollars a day)."); return 2
        got = read_json(p.cfg, {})
        got = got if isinstance(got, dict) else {}
        old = got.get("usd_per_day", DEFAULTS["usd_per_day"])
        got.update({"usd_per_day": round(a.allow, 2), "set_at": stamp(), "mark": MARK})
        write_json(p.cfg, got)
        append(p.log, {"at": stamp(), "step": "allow", "rc": 0, "spent": 0, "from": old, "to": round(a.allow, 2),
                       "mark": MARK})
        print("VERDICT: the allowance is $%.2f a day (it was $%.2f)%s" % (a.allow, old,
                                                                        "; the paid steps stop" if a.allow == 0 else ""))
        print("NEXT: python scripts\\repair_auto.py"); return 0
    cfg = config(p.cfg)
    if a.log:
        for r in rounds(p.log)[-20:]:
            print("  %s %-6s %-48s rc %s $%.4f %s" % (r.get("at", "?"), r.get("step", "?"), (r.get("doc") or "")[:48],
                                                     r.get("rc"), float(r.get("spent") or 0), (r.get("verdict") or "")[:90]))
        print("VERDICT: %d round(s) recorded" % len(rounds(p.log))); print("NEXT: "); return 0
    if a.round:
        return round_(a, p, cfg)
    return show_plan(a, p, cfg)


if __name__ == "__main__":
    sys.exit(main())
