#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_hub_v2_2026_10_10.py  (2026-10-10)  HUB_V2_2026_10_10

Installs the Srangam Hub v2 (docs/hub/HUB_V2_2026-10-10/hub.py and hub.html) into the hub's own folder
(D:\\Sanksrit Automatons\\srangam-hub, its own git repository) and adds a section to its README.md.
docs/DESK_HEAL_2026-10-10.md says why:

  * v1 called the dashboard "down (ReadTimeout)" while it ran: it asked /api/status, the dashboard's
    heaviest read (7.2 s measured), every 5 s with a 2.5 s limit, and so slowed the dashboard itself.
    v2 asks /api/health (or /api/jobs/running on a dashboard from before DESK_HEAL_2026_10_10), at most
    once every 8 s however many hub pages are open, and calls a dashboard that holds its port but
    answers slowly "busy".
  * v1's Start ran run.bat, a visible window whose closing ends the dashboard and its runs. v2 runs
    scripts\\restart_dashboard.ps1 (no window, logs in D:\\backups\\dashboard_logs).
  * v2 shows the corpus end to end: this PC (the engine, the database, the Gemini brain), the cloud
    (the mirror to Supabase, the pictures on Drive, the Corner desk and its mail, from their own logs,
    with the scheduled tasks' next runs) and the site (srangam.nartiang.org and its working corpus).

The hub reads the database read-only (mode=ro) in the background, every 10 min, and never writes it.

Guards: each file is replaced only when it is exactly the v1 this was written against (md5, line
endings ignored), or is left alone when it already carries the marker; the payload is checked (md5,
ASCII, compiles). All or nothing. Backups <name>.bak_og_hubv2_<date> (the hub's .gitignore already
ignores *.bak_og_*). Line endings LF, as the hub repository keeps them.

Run from the automaton repository root:
  python scripts\\patch_hub_v2_2026_10_10.py --check
  python scripts\\patch_hub_v2_2026_10_10.py
  python scripts\\patch_hub_v2_2026_10_10.py --hub "D:\\Sanksrit Automatons\\srangam-hub"   (the default)
Then close the hub's console window and start it again with start-hub.bat.
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "HUB_V2_2026_10_10"
REPO = Path(__file__).resolve().parent.parent
PAYLOAD = REPO / "docs" / "hub" / "HUB_V2_2026-10-10"
DEFAULT_HUB = REPO.parent / "srangam-hub"

# v1 as found on 2026-10-10 (LF-normalised md5) and the v2 payload
V1 = {"hub.py": "948121e15dece25b94c88f54ea8ba948", "hub.html": "ff6856eb2e4c3f23d5fd7fbcb9279965"}
V2 = {"hub.py": "1f5b0d3176b6d65291accfb568460c61", "hub.html": "5840237dcff08ffa07e9e64b882e380d"}

README_SECTION = """

## U4 - v2, the corpus end to end (HUB_V2_2026_10_10, 2026-10-10)

What changed, and why (the automaton's `docs/DESK_HEAL_2026-10-10.md` has the measurements):

- **"Automaton down (ReadTimeout)" while it ran.** v1 asked the dashboard's `/api/status`, its
  heaviest read (7.2 s with 68 texts and 2,166 inbox pages), every 5 s with a 2.5 s limit: the hub
  itself slowed the dashboard. v2 asks `/api/health` (the dashboard answers it from memory, in
  milliseconds; `/api/jobs/running` on a dashboard from before DESK_HEAL_2026_10_10), at most once
  every 8 s however many hub pages are open. A dashboard that holds its port but answers slowly is
  shown as *busy*, not down. The proxy no longer forwards `/api/status`.
- **Start** runs `scripts\\restart_dashboard.ps1` instead of `run.bat`: no window to close by mistake
  (closing run.bat's window ended the dashboard and every run it had started), logs in
  `D:\\backups\\dashboard_logs`. It is still refused while the dashboard's port is held.
- **The page shows the corpus end to end**, in three columns:
  - *This PC makes it*: the translation engine (what runs, the spend cap), the database (texts,
    verses, English and Hindi, names, stories, pictures, graphic novels; counted read-only in the
    background every 10 min) and the Gemini brain (passage vectors, what is left to embed, when the
    SanskritMaintenance task last kept it current and why it skipped).
  - *The cloud carries it*: the mirror to Supabase (SanskritCorpusMirror, every 2 h), the pictures on
    Drive (after each mirror run) and the Corner desk (SanskritCornerWorker, every 10 min) with its
    mail, each from its own log file in `data\\`, with the task's next run from the Task Scheduler.
  - *The site serves it*: srangam.nartiang.org and links into its working corpus.
- Panchang, Booksmith and the wisdomlib crawl actions are as in v1.

`HOW_TO.html` describes v1; its daily rhythm still holds, except that the Automaton card's Start now
uses the detached launcher.

Install or update from the automaton repository root: `python scripts\\patch_hub_v2_2026_10_10.py --check`,
then without `--check`; close this hub's console window and start it again with `start-hub.bat`.
<!-- HUB_V2_2026_10_10 -->
"""


def md5n(b: bytes) -> str:
    return hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--hub", default=str(DEFAULT_HUB))
    a = ap.parse_args()
    hub = Path(a.hub)
    if not (hub / "hub.py").exists():
        print("FAIL: no hub.py in %s (pass --hub <folder>)." % hub); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []

    for name in ("hub.py", "hub.html"):
        src = PAYLOAD / name
        if not src.exists():
            problems.append("payload %s not found" % src); continue
        data = src.read_bytes()
        if md5n(data) != V2[name]:
            problems.append("payload %s md5 %s, want %s" % (name, md5n(data), V2[name])); continue
        if any(b > 127 for b in data) or MARK.encode() not in data:
            problems.append("payload %s is not ASCII or lacks %s" % (name, MARK)); continue
        if name.endswith(".py"):
            fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
            Path(tmp).write_bytes(data)
            try:
                py_compile.compile(tmp, doraise=True)
            except py_compile.PyCompileError as e:
                problems.append("payload %s does not compile: %s" % (name, e)); continue
            finally:
                os.unlink(tmp)
        dst = hub / name
        cur = dst.read_bytes()
        if MARK.encode() in cur:
            if md5n(cur) == V2[name]:
                print("skip %s (v2 is in place)" % dst)
            else:
                print("skip %s (carries %s but differs from this payload: edited by hand? left alone)" % (dst, MARK))
            continue
        if md5n(cur) != V1[name]:
            problems.append("%s md5 %s is not the v1 this was written against (%s): changed since 2026-10-10? "
                            "Nothing is replaced; compare it with %s" % (dst, md5n(cur), V1[name], src))
            continue
        todo.append((dst, data.replace(b"\r\n", b"\n")))

    readme = hub / "README.md"
    if readme.exists():
        txt = readme.read_bytes()
        if MARK.encode() in txt:
            print("skip %s (already carries %s)" % (readme, MARK))
        else:
            nl = b"\r\n" if txt.count(b"\r\n") > txt.count(b"\n") / 2 else b"\n"
            body = txt.rstrip(b"\r\n") + README_SECTION.replace("\n", nl.decode()).encode("utf-8")
            todo.append((readme, body))
    else:
        problems.append("%s not found" % readme)

    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write in %s: %s. Nothing written."
              % (len(todo), hub, ", ".join(p.name for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_og_hubv2_" + stamp))
        t = p.with_name(p.name + ".tmp_hubv2"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Now close the hub's console window and start it again: start-hub.bat (http://127.0.0.1:5050).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
