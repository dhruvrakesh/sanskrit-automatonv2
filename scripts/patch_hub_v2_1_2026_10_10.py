#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_hub_v2_1_2026_10_10.py  (2026-10-10)  HUB_V2_1_2026_10_10

Updates the Srangam Hub from v2 (HUB_V2_2026_10_10, installed by patch_hub_v2_2026_10_10.py) to v2.1:
docs/hub/HUB_V2_1_2026-10-10/hub.py and hub.html, into the hub's own folder
(D:\\Sanksrit Automatons\\srangam-hub, its own git repository), and adds section U5 to its README.md.
docs/LIVE_LOG_2026-10-10.md says why: presses in the Library made runs that were held by the OCR-debris
guard in 0.3 s, too fast to be seen running, so the hub looked as if nothing had been queued. v2.1
shows the last runs and what each did (done N of M, held, nothing to do, stopped, failed; from
data/jobs.jsonl), the texts held for an OCR repair, and how far a running OCR has got (its page files
against its inbox pages). The page asks every 30 s instead of 60.

Guards: each file is replaced only when it is exactly the v2 this was written against (md5, line
endings ignored), or is left alone when it already carries the marker; the payload is checked (md5,
ASCII, compiles). All or nothing. Backups <name>.bak_og_hubv21_<date> (the hub's .gitignore ignores
*.bak_og_*). Line endings LF.

Run from the automaton repository root:
  python scripts\\patch_hub_v2_1_2026_10_10.py --check
  python scripts\\patch_hub_v2_1_2026_10_10.py
Then close the hub's console window and start it again with start-hub.bat.
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "HUB_V2_1_2026_10_10"
REPO = Path(__file__).resolve().parent.parent
PAYLOAD = REPO / "docs" / "hub" / "HUB_V2_1_2026-10-10"
DEFAULT_HUB = REPO.parent / "srangam-hub"

V2 = {"hub.py": "1f5b0d3176b6d65291accfb568460c61", "hub.html": "5840237dcff08ffa07e9e64b882e380d"}
V21 = {"hub.py": "c83517e35eeb5fcadf3882b07942d480", "hub.html": "6b7f0f7079db4e80f4b8184ab9fb86b0"}

README_SECTION = """

## U5 - v2.1, the last runs (HUB_V2_1_2026_10_10, 2026-10-10)

- The Translation engine card lists the **last runs and what each did**, from the dashboard's
  `data\\jobs.jsonl`: *done* (N of M translated, and how many were below the OCR quality bar), *held*
  (by the OCR-debris guard), *nothing* (nothing left to translate), *stopped*, *failed*, and today's
  totals. A press in the Library makes a run even when the run is held at once (0.3 s), too fast to be
  seen running: it shows here.
- It names the **texts held for an OCR repair**: the translator holds a text whose scan carries
  Tesseract debris until OCR consensus has repaired it. The Library's note under each text has the
  command (a plan, no spend).
- A running **OCR shows how far it has got**: its page files in `data\\raw` against its page PDFs in
  the inbox, counted at most once a minute.
- The page asks `/api/online` every 30 s (was 60).

Install from the automaton repository root: `python scripts\\patch_hub_v2_1_2026_10_10.py --check`, then
without `--check`; close this hub's console window and start it again with `start-hub.bat`.
<!-- HUB_V2_1_2026_10_10 -->
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
        if md5n(data) != V21[name]:
            problems.append("payload %s md5 %s, want %s" % (name, md5n(data), V21[name])); continue
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
            if md5n(cur) == V21[name]:
                print("skip %s (v2.1 is in place)" % dst)
            else:
                print("skip %s (carries %s but differs from this payload: edited by hand? left alone)" % (dst, MARK))
            continue
        if md5n(cur) != V2[name]:
            problems.append("%s md5 %s is not the v2 this was written against (%s). Install v2 first "
                            "(scripts\\patch_hub_v2_2026_10_10.py), or compare it with %s" % (dst, md5n(cur), V2[name], src))
            continue
        todo.append((dst, data.replace(b"\r\n", b"\n")))
    readme = hub / "README.md"
    if readme.exists():
        txt = readme.read_bytes()
        if MARK.encode() in txt:
            print("skip %s (already carries %s)" % (readme, MARK))
        else:
            nl = b"\r\n" if txt.count(b"\r\n") > txt.count(b"\n") / 2 else b"\n"
            todo.append((readme, txt.rstrip(b"\r\n") + README_SECTION.replace("\n", nl.decode()).encode("utf-8")))
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
        shutil.copy2(p, p.with_name(p.name + ".bak_og_hubv21_" + stamp))
        t = p.with_name(p.name + ".tmp_hubv21"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Now close the hub's console window and start it again: start-hub.bat (http://127.0.0.1:5050).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
