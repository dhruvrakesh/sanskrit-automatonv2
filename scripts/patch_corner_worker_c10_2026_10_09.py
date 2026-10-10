#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_corner_worker_c10_2026_10_09.py  CORNER_C10_2026_10_09

Why: the Researchers' Corner comes level with the desk (SPEC C10 + E1, Part D). On the site a researcher
or an editor can now edit a story's or a picture's words, check a story again, ask for ideas for pictures
or a cover and have them drawn, restore a retired picture, edit a graphic novel's page, and draw a
novel's cast or pages again; the database side is docs/cloud/C10b_corner_kinds_2026-10-09.sql. And the
Corner sends email from nartiang.org (docs/cloud/C12_corner_mail_2026-10-09.sql, the corner-mail edge
function). This is the desk's side.

What changes in scripts/corner_worker.py (client 1.1 -> 1.2):
  1. Eight new kinds: story_edit, story_verify, picture_ideas, picture_cover, picture_draw, picture_edit,
     picture_restore, novel_page_edit. The edits are written in-process with the desk's own functions
     (stories.verify and the Stories page's UPDATE, images.set_status, novel.edit_page): their words
     never reach a command line. Each edit reads the desk's row again first: a retired one is refused,
     an approved one is changed only for an editor, a proposed episode only in its title, a picture's
     licence only by an editor. picture_ideas and picture_cover run images.py brief / cover (numbers and
     flags only) and answer the ideas they stored; picture_draw draws one of them.
  2. novel_cast and novel_draw honour "redo" (novel.py --redo; every page asked for is drawn again).
  3. Once a round, after the requests, the corner-mail function is asked to send the Corner's queued
     emails, signed as for corpus-desk. A mail problem (corner-mail not deployed, C12 not applied, ...)
     is noted in the round's summary and never fails the round.
Nothing else changes: the 1.1 kinds, refusals, argument lists, progress, heartbeat, ledger, lock, logs
and exit codes are as they were (the heartbeat's client says 1.2).

Order: this FIRST (it is harmless before the SQL: it only meets the new kinds when they are asked for,
and a corner-mail that is not there is only noted), THEN C10b and C12 in the database.

Whole-file replace from docs/desk/CORNER_C10_2026-10-09/corner_worker.py (md5 ffee71c3...),
md5-guarded (the file must be 1.1, released on 2026-10-09, md5 e80a5525...; if it is already the
payload there is nothing to do). Backup .bak_c10_<date>; LF only; py_compile before the atomic replace.

  python scripts/patch_corner_worker_c10_2026_10_09.py --check
  python scripts/patch_corner_worker_c10_2026_10_09.py
Then: python -m unittest tests.test_corner_worker_c10_2026_10_09
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "CORNER_C10_2026_10_09"
TARGET = Path("scripts/corner_worker.py")
PAYLOAD = Path("docs/desk/CORNER_C10_2026-10-09/corner_worker.py")
WANT_MD5 = "e80a552537625743b853e6d7a5eb3d39"      # corner_worker.py 1.1, released 2026-10-09
PAYLOAD_MD5 = "ffee71c3ed7e15675f349c2b3d838cee"   # corner_worker.py 1.2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes()
    have = hashlib.md5(raw).hexdigest()
    if have == PAYLOAD_MD5:
        print("Nothing to do: %s is already corner_worker.py 1.2 (%s)." % (TARGET, MARK)); return 0
    if have != WANT_MD5:
        print("REFUSE: %s has md5 %s, not the released 1.1 %s (changed since). Nothing written." % (TARGET, have, WANT_MD5))
        return 1
    if b"\r\n" in raw:
        print("REFUSE: %s has CRLF line endings; expected LF. Nothing written." % TARGET); return 1
    if not PAYLOAD.exists():
        print("FAIL: the payload %s is missing. Nothing written." % PAYLOAD); return 2
    data = PAYLOAD.read_bytes()
    got = hashlib.md5(data).hexdigest()
    if got != PAYLOAD_MD5:
        print("REFUSE: the payload %s has md5 %s, not %s. Nothing written." % (PAYLOAD, got, PAYLOAD_MD5)); return 1
    if b"\r\n" in data:
        print("REFUSE: the payload has CRLF line endings; expected LF. Nothing written."); return 1
    try:
        data.decode("ascii")
    except UnicodeDecodeError:
        print("REFUSE: the payload is not ASCII. Nothing written."); return 1
    if MARK.encode() not in data:
        print("REFUSE: the payload does not carry %s. Nothing written." % MARK); return 1
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "corner_worker_probe.py"
        probe.write_bytes(data)
        try:
            py_compile.compile(str(probe), doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: the payload does not compile: %s. Nothing written." % e); return 1
    if a.check:
        print("CHECK OK: %s (1.1, md5 %s) would be replaced by the payload (1.2, md5 %s). Nothing written."
              % (TARGET, have, PAYLOAD_MD5)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    bak = TARGET.with_name(TARGET.name + ".bak_c10_" + stamp)
    shutil.copy2(TARGET, bak)
    tmp = TARGET.with_name(TARGET.name + ".tmp_c10")
    tmp.write_bytes(data)
    os.replace(tmp, TARGET)
    print("replaced %s (corner_worker.py 1.1 -> 1.2, md5 %s). Backup: %s" % (TARGET, PAYLOAD_MD5, bak.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
