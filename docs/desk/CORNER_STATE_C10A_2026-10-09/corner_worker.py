#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
corner_worker.py  (2026-10-09)  CORNER_C9_2026_10_09; 1.1 CORNER_STATE_C10A_2026_10_09

The desk's side of the Researchers' Corner (docs/RESEARCHERS_CORNER_2026-10-09.md; schema
docs/cloud/C9_researchers_corner_2026-10-09.sql; edge function docs/cloud/C9_corpus-desk). It takes the
requests that researchers and editors made on the site and an editor approved, and carries each one
out with the desk's own scripts, exactly as you would at the command line:

  story_range        a candidate episode over the chosen passages, then  stories.py write --id N --yes
  story_write        stories.py write --id N --yes
  story_mine         stories.py mine --doc X --max N --yes
  picture_passage    an image idea at the chosen passage, written by the person who asked, then
                     images.py approve-brief ID  and  images.py generate --doc X --id ID --yes
  story_illustrate   stories.py illustrate --id N --yes, then approve-brief and generate as above
  picture_redraw     images.py regenerate ID --yes
  novel_plan         novel.py plan --story N --pages P --audience A --yes
  novel_cast         novel.py cast --id K --yes
  novel_draw         novel.py draw --id K [--pages 1-12] --yes
  story_approve / story_retire               stories.py approve --id N [--force] / retire --id N
  picture_approve / picture_retire           images.py approve ID / retire ID
  novel_page_approve / novel_approve / novel_retire   novel.py approve-page / approve / retire
Every paid step keeps the scripts' own gate (the desk's spend cap, cost_tracker); this worker also
refuses a paid request the cap cannot cover. The results are drafts, as at the desk: an editor
approves them (on the site through the Corner, or here). After each request the text is sent on at
once (corpus_sync.py --doc X for stories, corpus_media.py --doc X for pictures and novels), so the
site shows the result within a minute of the desk finishing.

The site cannot make the desk run anything else: the request kinds are a fixed list, every
parameter is checked again here against context.db, the scripts are run with an argument list (no
shell), and nothing from a request reaches a command line but numbers, passage references and the
documented flags. Free text (a title, a brief, a reason) is stored as data, never run.

1.1 (CORNER_STATE_C10A_2026_10_09; needs docs/cloud/C10a_corner_state_2026-10-09.sql in the database
first): while a request runs, the desk tells the site where it is ("Drawing page 3 of 12"), at most
once every 5 seconds except the first and the last step; a progress report that fails is logged and
never fails the request. novel_draw counts the pages it will draw from context.db first (novel.py's
own rule) and reads novel.py's output as it comes. The heartbeat also carries the state of the mirror
and of the picture uploads: the last line of data\\corpus_sync_log.jsonl and data\\corpus_media_log.jsonl.

  python scripts\\corner_worker.py --hello          # the function answers? (version, queue)
  python scripts\\corner_worker.py                  # what is waiting on the site (nothing is taken)
  python scripts\\corner_worker.py --apply          # take up to 3 approved requests and do them
  python scripts\\corner_worker.py --apply --max 1 --if-configured   # the scheduled step
One run at a time (data\\corner_worker.lock). Log: data\\corner_worker_log.jsonl.
Test: python -m unittest tests.test_corner_worker_2026_10_09 tests.test_corner_worker_state_2026_10_09 -v
"""
from __future__ import annotations

import argparse
import gzip
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_sync as cs  # noqa: E402  (load_config, sign, open_ro, live_docs, PgSink)

MARK = "CORNER_C9_2026_10_09"
STATE_MARK = "CORNER_STATE_C10A_2026_10_09"
SCHEME = "corner.1"
CLIENT_VERSION = "1.1"
CLIENT = "corner_worker.py %s" % CLIENT_VERSION
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "context.db"
LOG_PATH = ROOT / "data" / "corner_worker_log.jsonl"
LOCK_PATH = ROOT / "data" / "corner_worker.lock"
LEDGER_PATH = ROOT / "data" / "corner_worker_made.jsonl"   # request -> the row it made (for retries)
# CORNER_STATE_C10A_2026_10_09: what the heartbeat says about the mirror and the pictures (the last
# line of each log), and how often the desk comes (corner_task.ps1: every 10 minutes).
SYNC_LOG_PATH = ROOT / "data" / "corpus_sync_log.jsonl"     # corpus_sync.py log_run
MEDIA_LOG_PATH = ROOT / "data" / "corpus_media_log.jsonl"   # corpus_media.py log_run
SYNC_EVERY_MIN = 10
LOG_TAIL_MAX_BYTES = 4 * 1024 * 1024    # a last line longer than this is not read
INFO_MAX_CHARS = 3900                   # corner_desk_heartbeat and corpus-desk keep info up to 4000
ERROR_MAX_CHARS = 160
PROGRESS_GAP_S = 5.0                    # at most one progress report this often (but the first and the last)
PAGE_LINE_RE = re.compile(r"^\s*page (\d+): ")   # novel.py draw_pages: "  page %d: <path> (%.1f s)"
LOCK_STALE_S = 3 * 3600
TIMEOUT_S = {"story_mine": 1800, "novel_cast": 1500, "novel_draw": 3600, "picture_passage": 900,
             "story_illustrate": 1200, "picture_redraw": 900}
DEFAULT_TIMEOUT_S = 900
SYNC_TIMEOUT_S = 1200
PAID = {"story_range", "story_write", "story_mine", "picture_passage", "story_illustrate", "picture_redraw",
        "novel_plan", "novel_cast", "novel_draw"}
REF_RE = re.compile(r"^\s*(\d{1,6})\.(\d{1,6})\s*$")
PAGES_RE = re.compile(r"^\d{1,2}(-\d{1,2})?(,\d{1,2}(-\d{1,2})?)*$")
CAP_TEXT = ("spend cap is reached", "[BUDGET] PAUSED", "[BUDGET] cap reached")
SECRET_RE = re.compile(r"(AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z]{20,}|eyJ[0-9A-Za-z_\-]{20,}\.[0-9A-Za-z_\-.]+)")


class SinkError(RuntimeError):
    def __init__(self, msg: str, status: int | None = None):
        super().__init__(msg)
        self.status = status


class Refuse(Exception):
    """The request cannot be carried out; the message says why (shown to the person who asked)."""


# --------------------------------------------------------------------------- the site's side

class EdgeDesk:
    name = "edge"

    def __init__(self, base_url: str, anon_key: str, secret: str, timeout: int = 60, retries: int = 3):
        self.url = base_url.rstrip("/") + "/functions/v1/corpus-desk"
        self.anon, self.secret, self.timeout, self.retries = anon_key, secret, timeout, retries

    def _call(self, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        body = gzip.compress(raw, 6)
        last = None
        for attempt in range(self.retries):
            ts = str(int(time.time()))
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Content-Type": "application/octet-stream", "x-corpus-encoding": "gzip", "x-corpus-ts": ts,
                "x-corpus-sig": cs.sign(self.secret, ts, body), "apikey": self.anon,
                "Authorization": "Bearer " + self.anon})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                if not data.get("ok"):
                    raise SinkError("corpus-desk: %s" % str(data.get("error"))[:400])
                return data.get("result")
            except urllib.error.HTTPError as e:
                text = e.read()[:600].decode("utf-8", "replace")
                last = SinkError("corpus-desk HTTP %d: %s" % (e.code, text), e.code)
                if e.code in (429, 500, 502, 503, 504) and attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = SinkError("corpus-desk unreachable: %s" % e)
                if attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
        raise last or SinkError("corpus-desk: no answer")

    def hello(self):
        return self._call({"action": "hello"})

    def state(self):
        return self._call({"action": "state"})

    def pull(self, limit: int, worker: str):
        return self._call({"action": "pull", "limit": limit, "worker": worker}) or []

    def report(self, rid: int, status: str, result=None, message=None, cost=None, log=None):
        return self._call({"action": "report", "id": rid, "status": status, "result": result, "message": message,
                           "cost_usd": cost, "log": log})

    def heartbeat(self, info: dict):
        return self._call({"action": "heartbeat", "info": info})


class PgDesk:
    """A PostgreSQL you own with C9 applied (tests)."""
    name = "pg"

    def __init__(self, dsn: str):
        self._pg = cs.PgSink(dsn)
        self.con = self._pg.con

    def _one(self, sql, args=()):
        try:
            return self._pg._one(sql, args)
        except cs.SinkError as e:
            raise SinkError(str(e))

    def hello(self):
        return {"fn": "pg", "state": self.state()}

    def state(self):
        return self._one("SELECT public.corner_desk_state()")

    def pull(self, limit: int, worker: str):
        return self._one("SELECT public.corner_desk_pull(%s::integer, %s::text)", (limit, worker)) or []

    def report(self, rid, status, result=None, message=None, cost=None, log=None):
        return self._one("SELECT to_jsonb(public.corner_desk_report(%s::bigint, %s::text, %s::jsonb, %s::text, %s::numeric, %s::text))",
                         (rid, status, None if result is None else json.dumps(result), message, cost, log))

    def heartbeat(self, info):
        return self._one("SELECT public.corner_desk_heartbeat(%s::jsonb)", (json.dumps(info),))


def make_desk(kind: str, cfg: dict, dsn: str | None = None):
    if kind == "pg":
        d = dsn or cfg.get("dsn")
        if not d:
            raise SystemExit("--sink pg needs --dsn or CORPUS_SYNC_DSN")
        return PgDesk(d)
    missing = [n for n, k in (("CORPUS_SYNC_SECRET", "secret"), ("the site URL", "url"),
                              ("the publishable key", "anon")) if not cfg.get(k)]
    if missing:
        raise SystemExit("the desk link is not configured: missing %s (docs/CORPUS_MIRROR_2026-10-08.md, step 3)"
                         % ", ".join(missing))
    return EdgeDesk(cfg["url"], cfg["anon"], cfg["secret"])


def not_ready(e: SinkError) -> str | None:
    msg = str(e)
    if e.status == 404 or "Requested function was not found" in msg:
        return "the corpus-desk edge function is not deployed yet"
    if "corner_desk_" in msg and ("Could not find" in msg or "does not exist" in msg or "PGRST202" in msg):
        return "C9 is not applied in the database yet"
    return None


# --------------------------------------------------------------------------- running the desk's scripts

def run_script(args: list, timeout: int, on_line=None) -> tuple[int, str]:
    """python scripts\\<name>.py ... from the repo root, UTF-8, no shell. -> (return code, output).
    With on_line (CORNER_STATE_C10A_2026_10_09), each line the script prints is given to on_line as it
    comes (the script runs unbuffered); the timeout and the answer are the same as without."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if on_line is not None:
        return _run_streaming([sys.executable] + [str(a) for a in args], env, timeout, on_line)
    try:
        p = subprocess.run([sys.executable] + [str(a) for a in args], cwd=str(ROOT), env=env, capture_output=True,
                           timeout=timeout, text=True, encoding="utf-8", errors="replace", shell=False)
        return p.returncode, (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        return 124, out + "\n[timed out after %d s]" % timeout


def _run_streaming(cmd: list, env: dict, timeout: int, on_line) -> tuple[int, str]:
    """run_script's streaming half: stdout read line by line here, stderr read whole by a thread (so
    neither pipe can fill and stall the script), a timer that kills the script at the timeout."""
    p = subprocess.Popen(cmd, cwd=str(ROOT), env=dict(env, PYTHONUNBUFFERED="1"), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", shell=False)
    err = []
    reader = threading.Thread(target=lambda: err.append(p.stderr.read()), daemon=True)
    reader.start()
    timed_out = threading.Event()

    def kill():
        timed_out.set()
        try:
            p.kill()
        except OSError:
            pass

    timer = threading.Timer(timeout, kill)
    timer.daemon = True
    timer.start()
    out = []
    try:
        for line in p.stdout:
            out.append(line)
            try:
                on_line(line.rstrip("\r\n"))
            except Exception:   # the callback is only for progress; it never stops the script
                pass
        p.wait()
    finally:
        timer.cancel()
        reader.join(10)
        for fh in (p.stdout, p.stderr):
            try:
                fh.close()
            except (OSError, ValueError):
                pass
    text = "".join(out)
    if timed_out.is_set():
        return 124, text + "\n[timed out after %d s]" % timeout
    e = "".join(x for x in err if x)
    return p.returncode, text + (("\n" + e) if e else "")


def takes_on_line(runner) -> bool:
    """Does this runner take on_line (run_script does; the tests' fakes, called as runner(args, timeout),
    may not)?"""
    try:
        ps = inspect.signature(runner).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.kind == p.VAR_KEYWORD or (p.name == "on_line" and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY))
               for p in ps)


def tail(text: str, lines: int = 40, chars: int = 8000) -> str:
    t = "\n".join((text or "").strip().splitlines()[-lines:])
    return SECRET_RE.sub("[redacted]", t)[-chars:]


def parse_ref(s):
    m = REF_RE.match(str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


# --------------------------------------------------------------------------- CORNER_STATE_C10A_2026_10_09: the heartbeat's sync

def last_json_line(path, tries: int = 5):
    """The last line of a .jsonl log that is a JSON object, read from the end of the file (the logs grow
    without end). A line still being written does not parse and the one before it is taken; at most
    `tries` lines are tried. None when the file is missing or unreadable, or has no such line."""
    if path is None:
        return None
    try:
        with open(path, "rb") as fh:
            end = fh.seek(0, os.SEEK_END)
            start, buf, newlines = end, b"", 0
            while start > 0 and newlines <= tries and end - start < LOG_TAIL_MAX_BYTES:
                n = min(65536, start)
                start -= n
                fh.seek(start)
                chunk = fh.read(n)
                newlines += chunk.count(b"\n")
                buf = chunk + buf
    except OSError:
        return None
    parts = buf.split(b"\n")
    if start > 0:
        parts = parts[1:]          # the first piece is the end of a line read only in part
    tried = 0
    for raw in reversed(parts):
        raw = raw.strip()
        if not raw:
            continue
        tried += 1
        if tried > tries:
            break
        try:
            rec = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue
        if isinstance(rec, dict):
            return rec
    return None


def _count(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _short(v, n: int) -> str:
    return "" if v is None else str(v)[:n]


def _error(v):
    if v is None or str(v).strip() == "":
        return None
    return SECRET_RE.sub("[redacted]", str(v))[:ERROR_MAX_CHARS]


def mirror_state(rec: dict) -> dict:
    """The last corpus_sync.py run (its log_run record): ok when it stopped done and the check found no
    group different (or could not count them)."""
    v = rec.get("verified") if isinstance(rec.get("verified"), dict) else {}
    stopped = _short(rec.get("stopped"), 20)
    diff = v.get("groups_different")
    err = rec.get("error") or (("verify: %s" % v["error"]) if v.get("error") else None)
    return {"at": _short(rec.get("ts"), 40), "ok": stopped == "done" and (diff is None or _count(diff) == 0),
            "stopped": stopped, "error": _error(err), "equal": _count(v.get("groups_equal")),
            "different": _count(diff), "client": _short(rec.get("client"), 60)}


def media_state(rec: dict) -> dict:
    """The last corpus_media.py run (its log_run record). files_on_drive: the renditions on Drive when
    the run ended (those there before it, and those it uploaded or found there)."""
    f = rec.get("files") if isinstance(rec.get("files"), dict) else {}
    h = rec.get("here") if isinstance(rec.get("here"), dict) else {}
    stopped = _short(rec.get("stopped"), 20)
    on = _count(f.get("on_drive"))
    if on is not None:
        on += (_count(f.get("uploaded")) or 0) + (_count(f.get("skipped")) or 0)
    return {"at": _short(rec.get("ts"), 40), "ok": stopped == "done", "stopped": stopped,
            "error": _error(rec.get("error")), "files_needed": _count(f.get("needed")), "files_on_drive": on,
            "pictures": _count(h.get("pictures"))}


def sync_state(mirror_log=None, media_log=None) -> dict:
    """The heartbeat's "sync": the mirror's and the pictures' last run, or null for a log that is
    missing or unreadable (or not given)."""
    out = {"every_min": SYNC_EVERY_MIN, "mirror": None, "media": None}
    for key, path, fn in (("mirror", mirror_log, mirror_state), ("media", media_log, media_state)):
        rec = last_json_line(path)
        if rec is not None:
            try:
                out[key] = fn(rec)
            except Exception:   # a record of another shape: say nothing rather than something wrong
                out[key] = None
    return out


def info_chars(info: dict) -> int:
    """At least the length the database and corpus-desk measure (jsonb's text: ", " and ": "; every
    character outside ASCII counted as its six-character escape)."""
    return len(json.dumps(info, ensure_ascii=True))


def heartbeat_info(budget, logs=None) -> dict:
    """What the desk says about itself on each round (corner.worker.info; editors see it in corner_me()),
    always under INFO_MAX_CHARS: the errors go first, then the sync channels."""
    info = {"client": CLIENT, "budget": budget, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sync": sync_state(*(tuple(logs) if logs else (None, None)))}
    sync = info["sync"]
    for cut in ("error", "channel"):
        if info_chars(info) <= INFO_MAX_CHARS:
            break
        for key in ("mirror", "media"):
            if sync.get(key) is not None:
                if cut == "error":
                    sync[key]["error"] = (sync[key]["error"] or "")[:40] or None
                else:
                    sync[key] = None
    if info_chars(info) > INFO_MAX_CHARS:
        info["sync"] = None
    return info


class Progress:
    """CORNER_STATE_C10A_2026_10_09: where the desk is with one request, told to the site as it goes
    ("Drawing page 3 of 12"). Best effort: a report that fails is logged, never the request's failure,
    and no further progress is sent for that request (the site may be unreachable, and each try can
    take minutes with the desk's retries). At most one report every `gap` seconds, except the first and
    the last step. A step held back by that is not lost while a script runs: the newest one held goes
    out before the next script starts (after the rest of the gap), or as soon as a later step may go."""
    gap = PROGRESS_GAP_S
    clock = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)

    def __init__(self, send, say=None):
        self.send = send                 # send(step, of, note)
        self.say = say or (lambda m: None)
        self.last = None                 # self.clock() when the last report went
        self.held = None                 # (step, of, note) held back by the gap
        self.dead = False                # a report failed: no more progress for this request (the site
                                         # may be unreachable; each try can take minutes with retries)

    def __call__(self, step, of, note="") -> None:
        if self.dead:
            return
        try:
            of = max(1, min(1000, int(of)))
            step = max(0, min(of, int(step)))
        except (TypeError, ValueError):
            return
        item = (step, of, str(note or "")[:200])
        if self.last is None or step >= of or self.clock() - self.last >= self.gap:
            self._send(item)
        else:
            self.held = item

    def flush(self) -> None:
        if self.held is None or self.dead:
            return
        left = self.gap - (self.clock() - self.last)
        if left > 0:
            self.sleep(min(left, self.gap))
        self._send(self.held)

    def _send(self, item) -> None:
        self.held = None
        self.last = self.clock()
        try:
            self.send(*item)
        except Exception as e:
            self.dead = True
            self.say("progress report failed; no more progress for this request (it goes on): %s" % str(e)[:200])


class Outcome:
    __slots__ = ("ok", "result", "message", "touched", "log")

    def __init__(self, ok: bool, result: dict | None, message: str, touched=(), log: str = ""):
        self.ok, self.result, self.message, self.touched, self.log = ok, result or {}, message, set(touched), log


class Worker:
    def __init__(self, db: str, runner=run_script, sync: bool = True, say=None, ledger: Path = LEDGER_PATH):
        self.db = str(db)
        self.ledger = Path(ledger)
        self.run = runner
        self.sync = sync
        self.say = say or (lambda m: None)
        self.progress = None             # CORNER_STATE_C10A_2026_10_09: run_once's Progress for the request
        self._of, self._sending = 0, "Sending it to the site"

    # ---- CORNER_STATE_C10A_2026_10_09: the steps of a request, as the site shows them

    def begin_steps(self, of: int, sending: str = "Sending it to the site"):
        """This request has `of` steps; the last one is sending the result on (send_on), with this note."""
        self._of, self._sending = int(of), sending

    def step(self, i: int, note: str):
        if self.progress is None or not self._of:
            return
        try:
            self.progress(i, self._of, note)
        except Exception as e:   # progress is best effort, never the request's failure
            self.say("progress: %s" % str(e)[:200])

    # ---- reading context.db (read-only) and writing two kinds of row (a candidate, an idea)

    def ro(self):
        return cs.open_ro(self.db)

    def rw(self):
        import images as im
        return im._connect(self.db)

    def doc_id(self, con, code: str) -> int:
        live = {d[1]: d[0] for d in cs.live_docs(con)}
        if code not in live:
            raise Refuse("the text %s is not a live text on the desk" % code)
        return live[code]

    def story(self, con, code: str, sid: int) -> dict:
        did = self.doc_id(con, code)
        cols = [c[1] for c in con.execute("PRAGMA table_info(doc_stories)")]
        r = con.execute("SELECT * FROM doc_stories WHERE id=? AND doc_id=?", (sid, did)).fetchone()
        if not r:
            raise Refuse("story #%d is not a story of %s on the desk" % (sid, code))
        return dict(zip(cols, r))

    def image(self, con, code: str, iid: int) -> dict:
        did = self.doc_id(con, code)
        cols = [c[1] for c in con.execute("PRAGMA table_info(doc_images)")]
        r = con.execute("SELECT * FROM doc_images WHERE id=? AND doc_id=?", (iid, did)).fetchone()
        if not r:
            raise Refuse("picture #%d is not a picture of %s on the desk" % (iid, code))
        return dict(zip(cols, r))

    def novel(self, con, code: str, nid: int) -> dict:
        did = self.doc_id(con, code)
        r = con.execute("SELECT id, status, pages, story_id FROM doc_novels WHERE id=? AND doc_id=?", (nid, did)).fetchone()
        if not r:
            raise Refuse("graphic novel #%d is not a novel of %s on the desk" % (nid, code))
        return {"id": r[0], "status": r[1], "pages": r[2], "story_id": r[3]}

    def budget(self, con):
        try:
            r = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
        except Exception:
            return None
        if not r:
            return None
        cap, spent, paused = float(r[0] or 0), float(r[1] or 0), bool(r[2])
        return {"cap": round(cap, 2), "spent": round(spent, 4), "left": round(max(0.0, cap - spent), 4), "paused": paused}

    def spent_since(self, con, code: str, since_iso: str) -> float:
        try:
            r = con.execute("SELECT coalesce(sum(cost_usd), 0) FROM usage_log WHERE ts >= ? AND doc = ?",
                            (since_iso, code)).fetchone()
            return round(float(r[0] or 0), 4)
        except Exception:
            return 0.0

    def by_request(self, con, table: str, rid: int):
        """A row this request already made (a retried request must not make it twice): the ledger
        data/corner_worker_made.jsonl, written the moment the row is made, then still in the table."""
        made = None
        try:
            with open(self.ledger, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    if e.get("request") == rid and e.get("table") == table:
                        made = int(e["id"])
        except OSError:
            pass
        if made is not None and con.execute("SELECT 1 FROM %s WHERE id=?" % table, (made,)).fetchone():
            return made
        return None

    def remember(self, table: str, rid: int, row_id: int):
        try:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"request": rid, "table": table, "id": row_id,
                                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
        except OSError:
            pass

    # ---- the scripts

    def script(self, kind: str, *args, on_line=None) -> tuple[int, str]:
        if self.progress is not None:
            try:
                self.progress.flush()    # a step held back by the 5-second rule goes before the script runs
            except Exception as e:
                self.say("progress: %s" % str(e)[:200])
        argv, timeout = [str(x) for x in args], TIMEOUT_S.get(kind, DEFAULT_TIMEOUT_S)
        if on_line is not None and takes_on_line(self.run):
            rc, out = self.run(argv, timeout, on_line=on_line)
        else:
            rc, out = self.run(argv, timeout)
        if any(t in out for t in CAP_TEXT):
            raise Refuse("the desk's spend cap is reached; the request waits for the cap to be raised on the desk")
        return rc, out

    def must(self, kind: str, *args, on_line=None) -> str:
        rc, out = self.script(kind, *args, on_line=on_line)
        if rc != 0:
            last = [l for l in (out or "").strip().splitlines() if l.strip()]
            raise Refuse("the desk could not do it: %s" % (last[-1][:300] if last else "rc=%d" % rc))
        return out

    def stories(self, *args):
        return ["scripts/stories.py", "--db", self.db] + list(args)

    def images(self, *args):
        return ["scripts/images.py", "--db", self.db] + list(args)

    def novels(self, *args):
        return ["scripts/novel.py", "--db", self.db] + list(args)

    def draw(self, kind: str, code: str, iid: int, log: list, approved_step=None, drawing_step=None) -> dict:
        con = self.ro()
        try:
            st = self.image(con, code, iid)["status"]
        finally:
            con.close()
        if st == "brief":
            log.append(self.must(kind, *self.images("approve-brief", iid)))
            st = "brief-approved"
        if st == "brief-approved":
            if approved_step:
                self.step(approved_step, "The idea is approved")
            if drawing_step:
                self.step(drawing_step, "Drawing the picture")
            log.append(self.must(kind, *self.images("generate", "--doc", code, "--id", iid, "--yes")))
        con = self.ro()
        try:
            row = self.image(con, code, iid)
        finally:
            con.close()
        if row["status"] not in ("draft", "approved") or not row.get("path"):
            raise Refuse("picture #%d was not drawn (it is %s)" % (iid, row["status"]))
        return {"image_id": iid, "status": row["status"]}

    # ---- the request kinds

    def handle(self, req: dict) -> Outcome:
        kind, code, p, rid = req.get("kind"), req.get("doc_code"), req.get("params") or {}, int(req["id"])
        fn = getattr(self, "k_" + str(kind), None)
        self.begin_steps(0)
        if fn is None:
            return Outcome(False, None, "this desk does not know the request kind %r" % kind)
        log = []
        try:
            if kind in PAID:
                con = self.ro()
                try:
                    b = self.budget(con)
                finally:
                    con.close()
                est = float(req.get("est_usd") or 0)
                if b and (b["paused"] or b["left"] < est):
                    raise Refuse("the desk's spend cap leaves $%.2f (it is %s); this request is estimated at $%.2f"
                                 % (b["left"], "paused" if b["paused"] else "set at $%.2f" % b["cap"], est))
            result, message, touched = fn(rid, code, p, log)
            return Outcome(True, result, message, touched, tail("\n".join(log)))
        except Refuse as e:
            return Outcome(False, None, str(e), (), tail("\n".join(log)))

    @staticmethod
    def _int(p: dict, key: str) -> int:
        v = p.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, str)) or not str(v).isdigit() or not 0 < int(v) < 2 ** 31:
            raise Refuse("%s: not a whole number" % key)
        return int(v)

    def _story_result(self, code: str, sid: int) -> dict:
        con = self.ro()
        try:
            s = self.story(con, code, sid)
        finally:
            con.close()
        v = {}
        try:
            v = json.loads(s.get("verify") or "{}")
        except ValueError:
            pass
        return {"story_id": sid, "status": s.get("status"), "title": s.get("title"),
                "check_ok": v.get("ok"), "problems": (v.get("problems") or [])[:3]}

    def k_story_range(self, rid, code, p, log):
        import stories as st
        a, b = parse_ref(p.get("from")), parse_ref(p.get("to"))
        title = str(p.get("title") or "").strip()[:200]
        if not (a and b and a <= b and len(title) >= 3):
            raise Refuse("from, to and title are needed")
        con = self.ro()
        try:
            did = self.doc_id(con, code)
            keys = [(r[0], r[1]) for r in st.passages(con, code)]
            old = self.by_request(con, "doc_stories", rid)
        finally:
            con.close()
        if a not in keys or b not in keys:
            raise Refuse("passages %d.%d and %d.%d must both be translated passages of %s on the desk" % (a + b + (code,)))
        if sum(1 for k in keys if a <= k <= b) > 60:
            raise Refuse("at most 60 passages make one story")
        sid = old
        if sid is None:
            w = self.rw()
            try:
                cur = w.execute(
                    """INSERT INTO doc_stories(doc_id, status, title, why, from_page, from_idx, to_page, to_idx,
                                               provenance, created_at, updated_at)
                       VALUES(?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (did, title, str(p.get("why") or "")[:1000], a[0], a[1], b[0], b[1],
                     json.dumps({"corner_request": rid}), st.now(), st.now()))
                w.commit()
                sid = cur.lastrowid
                self.remember("doc_stories", rid, sid)
            finally:
                w.close()
        self.begin_steps(3)
        self.step(1, "Passages %d.%d to %d.%d chosen" % (a + b))
        self.step(2, "Writing the story")
        log.append(self.must("story_range", *self.stories("write", "--id", sid, "--yes")))
        res = self._story_result(code, sid)
        if res["status"] != "draft":
            raise Refuse("story #%d was not written (it is %s)" % (sid, res["status"]))
        return res, "Story #%d written%s." % (sid, "" if res["check_ok"] else "; its check found problems"), {"stories"}

    def k_story_write(self, rid, code, p, log):
        sid = self._int(p, "story_id")
        con = self.ro()
        try:
            s = self.story(con, code, sid)
        finally:
            con.close()
        if s["status"] not in ("candidate", "draft"):
            raise Refuse("story #%d is %s; only a proposed episode or a draft is written" % (sid, s["status"]))
        self.begin_steps(2)
        self.step(1, "Writing the story")
        log.append(self.must("story_write", *self.stories("write", "--id", sid, "--yes")))
        res = self._story_result(code, sid)
        return res, "Story #%d written%s." % (sid, "" if res["check_ok"] else "; its check found problems"), {"stories"}

    def k_story_mine(self, rid, code, p, log):
        n = self._int(p, "max")
        if n > 12:
            raise Refuse("max: at most 12")
        con = self.ro()
        try:
            did = self.doc_id(con, code)
            before = con.execute("SELECT coalesce(max(id), 0) FROM doc_stories").fetchone()[0]
            try:   # what stories.py mine reads (stories.passages): for the note only
                k = con.execute("SELECT count(*) FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ? "
                                "AND TRIM(COALESCE(p.translation,'')) <> '' "
                                "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')", (code,)).fetchone()[0]
            except Exception:
                k = None
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Reading %s translated passages for episodes" % ("{:,}".format(k) if k is not None else "the"))
        log.append(self.must("story_mine", *self.stories("mine", "--doc", code, "--max", n, "--yes")))
        con = self.ro()
        try:
            ids = [r[0] for r in con.execute("SELECT id FROM doc_stories WHERE doc_id=? AND id>? ORDER BY id", (did, before))]
        finally:
            con.close()
        return ({"candidates": ids, "count": len(ids)},
                "%d episode(s) proposed; an editor or you can ask for each to be written." % len(ids), {"stories"})

    def k_picture_passage(self, rid, code, p, log):
        import images as im
        at = parse_ref(p.get("at"))
        title = str(p.get("title") or "").strip()[:200]
        brief = str(p.get("brief") or "").strip()[:2000]
        if not at or len(title) < 3 or len(brief) < 20:
            raise Refuse("at, title and brief are needed")
        import stories as st
        con = self.ro()
        try:
            self.doc_id(con, code)
            keys = {(r[0], r[1]) for r in st.passages(con, code)}
            iid = self.by_request(con, "doc_images", rid)
        finally:
            con.close()
        if at not in keys:
            raise Refuse("passage %d.%d is not a translated passage of %s on the desk" % (at + (code,)))
        if iid is None:
            w = self.rw()
            try:
                ids = im.store_briefs(w, code, [{"page": at[0], "idx": at[1], "title": title, "brief": brief,
                                                 "caption_en": str(p.get("caption_en") or "").strip()[:500] or None,
                                                 "context_note": None}], keys, 1, "researcher")
                if ids:
                    iid = ids[0]
                    self.remember("doc_images", rid, iid)
                    w.execute("UPDATE doc_images SET provenance=? WHERE id=?",
                              (json.dumps({"brief_model": "researcher", "source": "corner_worker.py",
                                           "corner_request": rid}), iid))
                    w.commit()
                else:   # the same idea at this passage exists already: draw that one
                    r = w.execute("SELECT id, title FROM doc_images WHERE doc_id=(SELECT id FROM docs WHERE code=?) "
                                  "AND anchor_page=? AND anchor_idx=? AND status<>'retired' ORDER BY id DESC",
                                  (code, at[0], at[1])).fetchall()
                    same = [x[0] for x in r if im._norm_title(x[1]) == im._norm_title(title)]
                    if not same:
                        raise Refuse("the idea could not be stored")
                    iid = same[0]
            finally:
                w.close()
        self.begin_steps(4, "Sending it to Drive")
        self.step(1, "The idea is stored")
        res = self.draw("picture_passage", code, iid, log, approved_step=2, drawing_step=3)
        return res, "Picture #%d drawn; an editor approves it." % iid, {"media"}

    def k_story_illustrate(self, rid, code, p, log):
        sid = self._int(p, "story_id")
        con = self.ro()
        try:
            s = self.story(con, code, sid)
            iid = s.get("image_id")
            if iid:
                r = con.execute("SELECT status FROM doc_images WHERE id=?", (iid,)).fetchone()
                if not r or r[0] == "retired":
                    iid = None
        finally:
            con.close()
        if s["status"] == "retired":
            raise Refuse("story #%d is retired" % sid)
        self.begin_steps(3, "Sending it to Drive")
        if iid is not None:
            con = self.ro()
            try:
                st_now = self.image(con, code, int(iid))["status"]
            finally:
                con.close()
            if st_now in ("draft", "approved"):
                return ({"image_id": int(iid), "story_id": sid, "status": st_now},
                        "Story #%d already has picture #%d (%s); nothing was drawn." % (sid, int(iid), st_now), {"media"})
        if iid is None:
            self.step(1, "Writing the idea for the picture")
            log.append(self.must("story_illustrate", *self.stories("illustrate", "--id", sid, "--yes")))
            con = self.ro()
            try:
                iid = self.story(con, code, sid).get("image_id")
            finally:
                con.close()
            if not iid:
                raise Refuse("no image idea was made for story #%d" % sid)
        else:
            self.step(1, "The idea for the picture is there")
        res = self.draw("story_illustrate", code, int(iid), log, drawing_step=2)
        res["story_id"] = sid
        return res, "Picture #%d drawn for story #%d; an editor approves it." % (int(iid), sid), {"media", "stories"}

    def k_picture_redraw(self, rid, code, p, log):
        iid = self._int(p, "image_id")
        con = self.ro()
        try:
            row = self.image(con, code, iid)
            lineage = row.get("lineage_id") or iid
            before = con.execute("SELECT coalesce(max(id), 0) FROM doc_images WHERE lineage_id=?", (lineage,)).fetchone()[0]
        finally:
            con.close()
        if row["status"] == "retired":
            raise Refuse("picture #%d is retired" % iid)
        self.begin_steps(2, "Sending it to Drive")
        self.step(1, "Drawing picture #%d again" % iid)
        log.append(self.must("picture_redraw", *self.images("regenerate", iid, "--yes")))
        con = self.ro()
        try:
            new = con.execute("SELECT id, status FROM doc_images WHERE lineage_id=? AND id>? ORDER BY id DESC",
                              (lineage, before)).fetchone()
        finally:
            con.close()
        if not new:
            raise Refuse("no new version of picture #%d was made" % iid)
        return ({"image_id": new[0], "replaces": iid, "status": new[1]},
                "Picture #%d drawn again as #%d; an editor approves the new one." % (iid, new[0]), {"media"})

    def k_novel_plan(self, rid, code, p, log):
        sid = self._int(p, "story_id")
        pages = self._int(p, "pages")
        aud = str(p.get("audience") or "general")
        if not 8 <= pages <= 16 or aud not in ("young", "teen", "general"):
            raise Refuse("pages 8 to 16; audience young, teen or general")
        con = self.ro()
        try:
            s = self.story(con, code, sid)
            before = con.execute("SELECT coalesce(max(id), 0) FROM doc_novels").fetchone()[0] \
                if cs._has_table(con, "doc_novels") else 0
        finally:
            con.close()
        if s["status"] != "approved":
            raise Refuse("story #%d is %s; a graphic novel is planned from an approved story" % (sid, s["status"]))
        self.begin_steps(2)
        self.step(1, "Planning the graphic novel (%d pages)" % pages)
        log.append(self.must("novel_plan", *self.novels("plan", "--story", sid, "--pages", pages, "--audience", aud, "--yes")))
        con = self.ro()
        try:
            r = con.execute("SELECT id, status FROM doc_novels WHERE story_id=? AND id>? ORDER BY id DESC", (sid, before)).fetchone()
        finally:
            con.close()
        if not r:
            raise Refuse("no graphic novel was planned")
        return ({"novel_id": r[0], "status": r[1], "story_id": sid},
                "Graphic novel #%d planned (%d pages); next: draw its cast, then its pages." % (r[0], pages), {"media"})

    def k_novel_cast(self, rid, code, p, log):
        nid = self._int(p, "novel_id")
        con = self.ro()
        try:
            n = self.novel(con, code, nid)
        finally:
            con.close()
        if n["status"] == "retired":
            raise Refuse("graphic novel #%d is retired" % nid)
        self.begin_steps(2, "Sending it to Drive")
        self.step(1, "Drawing the cast")
        log.append(self.must("novel_cast", *self.novels("cast", "--id", nid, "--yes")))
        return {"novel_id": nid}, "The cast of graphic novel #%d is drawn." % nid, {"media"}

    def k_novel_draw(self, rid, code, p, log):
        nid = self._int(p, "novel_id")
        spec = str(p.get("pages") or "").strip()
        if spec and not PAGES_RE.match(spec):
            raise Refuse("pages: such as 1-12 or 1,3,5-7")
        con = self.ro()
        try:
            n = self.novel(con, code, nid)
            todo, asked = self.pages_to_draw(con, nid, spec) if n["status"] != "retired" else (None, None)
        finally:
            con.close()
        if n["status"] == "retired":
            raise Refuse("graphic novel #%d is retired" % nid)
        args = ["draw", "--id", nid] + (["--pages", spec] if spec else []) + ["--yes"]
        if todo is None:     # the plan cannot be read here: novel.py decides, as in 1.0
            self.begin_steps(3, "Sending it to Drive")
            self.step(1, "Checking which pages to draw")
            self.step(2, "Drawing the pages")
            log.append(self.must("novel_draw", *self.novels(*args)))
        elif not todo:
            why = ("every page asked for has a picture" if asked else
                   "its plan has no page %s" % spec)
            self.begin_steps(2)
            self.step(2, "Nothing to draw: %s" % why)
            return ({"novel_id": nid, "pages": spec or "all missing"},
                    "Nothing to draw for graphic novel #%d: %s." % (nid, why), set())
        else:
            total = len(todo)
            self.begin_steps(1 + total + 1, "Sending it to Drive")
            self.step(1, "%d page%s to draw" % (total, "" if total == 1 else "s"))
            self.step(2, "Drawing page 1 of %d" % total)
            drawn = [0]

            def on_line(line):   # novel.py prints "  page N: <path> (S s)" as each page is drawn
                if PAGE_LINE_RE.match(line):
                    drawn[0] += 1
                    if drawn[0] < total:
                        self.step(2 + drawn[0], "Drawing page %d of %d" % (drawn[0] + 1, total))

            log.append(self.must("novel_draw", *self.novels(*args), on_line=on_line))
        return ({"novel_id": nid, "pages": spec or "all missing"},
                "Pages of graphic novel #%d drawn; an editor approves them page by page." % nid, {"media"})

    def pages_to_draw(self, con, nid: int, spec: str):
        """The pages `novel.py draw --id K [--pages spec] --yes` will draw, by its own rule (draw_pages):
        each page of the plan that was asked for (every page when no spec) and has no picture, or a stale
        one. -> (pages in plan order, how many plan pages were asked for), or (None, None) when the plan
        cannot be read here (then novel.py is run and decides)."""
        try:
            import novel as nv
            n = nv.get(con, nid)
            pages = (n["plan"] or {}).get("pages") or []
            if not pages:
                return None, None
            which = nv._pages_arg(spec or None)
            imgs = dict(n["page_images"] or {})
            todo, asked = [], 0
            for p in pages:
                if which and p["n"] not in which:
                    continue
                asked += 1
                key = str(p["n"])
                if key in imgs and imgs[key].get("status") != "stale":
                    continue
                todo.append(int(p["n"]))
            return todo, asked
        except (Exception, SystemExit):
            return None, None

    def k_story_approve(self, rid, code, p, log):
        sid = self._int(p, "story_id")
        con = self.ro()
        try:
            self.story(con, code, sid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Approving story #%d" % sid)
        log.append(self.must("story_approve", *self.stories("approve", "--id", sid, *(["--force"] if p.get("force") else []))))
        res = self._story_result(code, sid)
        if res["status"] != "approved":
            raise Refuse("story #%d was not approved" % sid)
        return res, "Story #%d approved." % sid, {"stories"}

    def k_story_retire(self, rid, code, p, log):
        sid = self._int(p, "story_id")
        con = self.ro()
        try:
            self.story(con, code, sid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Retiring story #%d" % sid)
        log.append(self.must("story_retire", *self.stories("retire", "--id", sid)))
        return {"story_id": sid, "status": "retired"}, "Story #%d retired." % sid, {"stories"}

    def k_picture_approve(self, rid, code, p, log):
        iid = self._int(p, "image_id")
        con = self.ro()
        try:
            self.image(con, code, iid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Approving picture #%d" % iid)
        log.append(self.must("picture_approve", *self.images("approve", iid)))
        return {"image_id": iid, "status": "approved"}, "Picture #%d approved." % iid, {"media"}

    def k_picture_retire(self, rid, code, p, log):
        iid = self._int(p, "image_id")
        con = self.ro()
        try:
            self.image(con, code, iid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Retiring picture #%d" % iid)
        log.append(self.must("picture_retire", *self.images("retire", iid)))
        return {"image_id": iid, "status": "retired"}, "Picture #%d retired." % iid, {"media"}

    def k_novel_page_approve(self, rid, code, p, log):
        nid, page = self._int(p, "novel_id"), self._int(p, "page")
        con = self.ro()
        try:
            self.novel(con, code, nid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Approving page %d of graphic novel #%d" % (page, nid))
        log.append(self.must("novel_page_approve", *self.novels("approve-page", "--id", nid, "--page", page)))
        return {"novel_id": nid, "page": page}, "Page %d of graphic novel #%d approved." % (page, nid), {"media"}

    def k_novel_approve(self, rid, code, p, log):
        nid = self._int(p, "novel_id")
        con = self.ro()
        try:
            self.novel(con, code, nid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Approving graphic novel #%d" % nid)
        log.append(self.must("novel_approve", *self.novels("approve", "--id", nid, *(["--force"] if p.get("force") else []))))
        return {"novel_id": nid, "status": "approved"}, "Graphic novel #%d approved." % nid, {"media"}

    def k_novel_retire(self, rid, code, p, log):
        nid = self._int(p, "novel_id")
        con = self.ro()
        try:
            self.novel(con, code, nid)
        finally:
            con.close()
        self.begin_steps(2)
        self.step(1, "Retiring graphic novel #%d" % nid)
        log.append(self.must("novel_retire", *self.novels("retire", "--id", nid)))
        return {"novel_id": nid, "status": "retired"}, "Graphic novel #%d retired." % nid, {"media"}

    # ---- sending the result on

    def send_on(self, code: str, touched: set) -> str:
        if not self.sync or not touched:
            return ""
        self.step(self._of, self._sending)      # the request's last step
        notes = []
        if "stories" in touched:
            rc, out = self.run(["scripts/corpus_sync.py", "--db", self.db, "--apply", "--if-configured",
                                "--doc", code, "--tables", "docs,stories"], SYNC_TIMEOUT_S)
            if rc != 0:
                notes.append("the story reaches the site with the next mirror run")
        if "media" in touched:
            rc, out = self.run(["scripts/corpus_media.py", "--db", self.db, "--apply", "--if-configured",
                                "--doc", code], SYNC_TIMEOUT_S)
            if rc != 0:
                notes.append("the pictures reach the site with the next mirror run")
        return "; ".join(notes)


# --------------------------------------------------------------------------- the run

class Lock:
    def __init__(self, path: Path = LOCK_PATH):
        self.path, self.held = path, False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, ("%d %d\n" % (os.getpid(), int(time.time()))).encode("ascii"))
                os.close(fd)
                self.held = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except OSError:
                    continue
                if age < LOCK_STALE_S:
                    return self
                try:
                    self.path.unlink()
                except OSError:
                    return self
        return self

    def __exit__(self, *a):
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass


def run_once(desk, worker: Worker, limit: int, name: str = "desk", progress: bool = False, logs=None) -> dict:
    """One round. progress: tell the site where each request is (CORNER_STATE_C10A_2026_10_09); logs:
    (corpus_sync log, corpus_media log) for the heartbeat's sync. main() gives both; without them a round
    is as in 1.0 but for a heartbeat whose sync says nothing (the tests)."""
    s = {"taken": 0, "done": 0, "failed": 0, "requests": [], "stopped": "done", "error": None}
    con = worker.ro()
    try:
        b = worker.budget(con)
    finally:
        con.close()
    hb = desk.heartbeat(heartbeat_info(b, logs)) or {}
    if hb.get("scheme") not in (None, SCHEME):
        raise SinkError("the site answers scheme %r, this script speaks %r" % (hb.get("scheme"), SCHEME))
    s["queued"] = hb.get("queued")
    todo = desk.pull(limit, name)
    s["taken"] = len(todo)
    for req in todo:
        rid, kind, code = int(req["id"]), req.get("kind"), req.get("doc_code")
        worker.say("request #%d %s %s: start" % (rid, kind, code))
        desk.report(rid, "running", None, "The desk is working on it.", None, None)
        if progress:
            def send(i, n, note, rid=rid):
                desk.report(rid, "running", {"progress": {"step": i, "of": n, "note": note}}, note, None, None)
            worker.progress = Progress(send, say=worker.say)
        t0 = time.time()
        since = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t0))
        try:
            out = worker.handle(req)
        except Exception as e:   # never leave a request running because of a bug here
            out = Outcome(False, None, "the desk failed: %s" % str(e)[:300])
        try:
            note = worker.send_on(code, out.touched) if out.ok else ""
        finally:
            worker.progress = None
        con = worker.ro()
        try:
            cost = worker.spent_since(con, code, since) if kind in PAID else 0.0
        finally:
            con.close()
        msg = out.message + ((" (" + note + ")") if note else "")
        desk.report(rid, "done" if out.ok else "failed", out.result or None, msg[:2000], cost, out.log or None)
        s["done" if out.ok else "failed"] += 1
        s["requests"].append({"id": rid, "kind": kind, "doc": code, "ok": out.ok, "message": msg[:300],
                              "cost_usd": cost, "seconds": round(time.time() - t0, 1)})
        worker.say("request #%d %s: %s %s" % (rid, kind, "done" if out.ok else "FAILED", msg[:200]))
    return s


def log_run(s: dict, path: Path = LOG_PATH):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = dict(s, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), client=CLIENT)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except OSError:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Carry out the Researchers' Corner's approved requests on the desk (C9).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--sink", default="edge", choices=["edge", "pg"])
    ap.add_argument("--dsn", default=None)
    ap.add_argument("--apply", action="store_true", help="take approved requests and do them; without it only the state")
    ap.add_argument("--max", type=int, default=3, help="requests to take in this run (1-20)")
    ap.add_argument("--no-sync", action="store_true", help="do not send results on (the next mirror run does)")
    ap.add_argument("--if-configured", action="store_true",
                    help="exit 0 quietly when the link is not configured, the function is not deployed or C9 is not applied")
    ap.add_argument("--hello", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    cfg = cs.load_config()
    if a.if_configured and a.sink == "edge" and not (cfg["secret"] and cfg["url"] and cfg["anon"]):
        print("corner worker: not configured (CORPUS_SYNC_SECRET); skipped")
        return 0
    desk = make_desk(a.sink, cfg, a.dsn)
    try:
        if a.hello:
            print(json.dumps(desk.hello()))
            return 0
        if not a.apply:
            st = desk.state() or {}
            print("corner: %s waiting for an editor, %s queued for the desk, %s running; the desk last came %s"
                  % (st.get("pending"), st.get("queued"), st.get("running"), st.get("last_seen") or "never"))
            return 0
        if not Path(a.db).exists():
            print("database not found: %s" % a.db)
            return 1
        with Lock() as lock:
            if not lock.held:
                print("corner worker: another run is going (data\\corner_worker.lock); skipped")
                return 0
            t0 = time.time()
            say = (lambda m: print("[%5.0fs] %s" % (time.time() - t0, m), flush=True)) if not a.json else None
            w = Worker(a.db, sync=not a.no_sync, say=say)
            s = run_once(desk, w, max(1, min(20, a.max)), "desk", progress=True, logs=(SYNC_LOG_PATH, MEDIA_LOG_PATH))
            s["seconds"] = round(time.time() - t0, 1)
    except SinkError as e:
        why = not_ready(e)
        if why and a.if_configured:
            print("corner worker: %s; skipped" % why)
            return 0
        print("corner_worker: %s%s" % (e, (" (" + why + ")") if why else ""))
        if a.apply:
            log_run({"stopped": "error", "error": str(e)[:500]})
        return 2
    if a.json:
        print(json.dumps(s, indent=1, ensure_ascii=True))
    else:
        print("corner_worker %s: %d taken, %d done, %d failed, %s queued before this run, %.1f s"
              % (CLIENT_VERSION, s["taken"], s["done"], s["failed"], s.get("queued"), s["seconds"]))
        for r in s["requests"]:
            print("  #%d %-18s %-12s %s %s" % (r["id"], r["kind"], (r["doc"] or "")[:12], "ok  " if r["ok"] else "FAIL",
                                              r["message"]))
    log_run(s)
    return 0   # a request that failed is reported to the site with its reason; the run itself went well


if __name__ == "__main__":
    sys.exit(main())
