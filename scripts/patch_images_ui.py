#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_images_ui.py  (2026-10-03)  IMAGES_UI_2026_10_03

Wires the Images tab (scripts/images_web.py + scripts/images_static.html) into
the dashboard. Two anchored, all-or-nothing edits, with backups:
  1. scripts/dashboard.py - register the routes just before `if __name__`.
     Wrapped in try/except: a broken images module can never stop the dashboard.
  2. scripts/dashboard_static.html - an "Images" link in the top bar.
Needs ONE dashboard restart, only when the header reads "idle" (RUNBOOK 1).
The HTML link works on reload; /images itself appears after the restart.

  python scripts/patch_images_ui.py --check
  python scripts/patch_images_ui.py
Test: python -m unittest tests.test_images_web -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "IMAGES_UI_2026_10_03"
DASH = Path("scripts/dashboard.py")
HTML = Path("scripts/dashboard_static.html")

OLD_PY = '\nif __name__ == "__main__":\n'
NEW_PY = '''
# IMAGES_UI_2026_10_03: the Images tab (/images) - see scripts/images_web.py.
# Guarded: if the module is missing or broken the dashboard still starts.
try:
    import images_web as _images_web
    _images_web.register(app, launch=launch, root=ROOT, py=py, script=script)
except Exception as _images_err:
    print(f"[images] Images tab not loaded: {type(_images_err).__name__}: {_images_err}")
''' + OLD_PY

OLD_HTML = '    <div class="top-bar-spacer"></div>\n'
NEW_HTML = OLD_HTML + ('    <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)" '
                       'style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F5BC; Images</a>\n')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (DASH, HTML, Path("scripts/images_web.py"), Path("scripts/images_static.html"), Path("scripts/images.py")):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    py_src, py_nl = load(DASH); html_src, html_nl = load(HTML)
    if MARK in py_src and MARK in html_src:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if (MARK in py_src) != (MARK in html_src):
        print("REFUSING: marker in only one of the two files - inspect by hand."); return 1
    problems = []
    if py_src.count(OLD_PY) != 1:
        problems.append("dashboard.py `if __name__` matched %d times" % py_src.count(OLD_PY))
    if html_src.count(OLD_HTML) != 1:
        problems.append("dashboard_static.html top-bar-spacer matched %d times" % html_src.count(OLD_HTML))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    py_new = py_src.replace(OLD_PY, NEW_PY, 1); html_new = html_src.replace(OLD_HTML, NEW_HTML, 1)
    if args.check:
        print("CHECK OK: both anchors match exactly once. Nothing written."); return 0
    tmp = DASH.with_name(DASH.name + ".tmp_imgui")
    tmp.write_bytes(py_new.replace("\n", py_nl).encode("utf-8"))
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        tmp.unlink(); print("REFUSING TO WRITE: dashboard.py would not compile:\n%s" % e); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(DASH, DASH.with_name(DASH.name + ".bak_imgui_" + stamp))
    shutil.copy2(HTML, HTML.with_name(HTML.name + ".bak_imgui_" + stamp))
    t2 = HTML.with_name(HTML.name + ".tmp_imgui"); t2.write_bytes(html_new.replace("\n", html_nl).encode("utf-8"))
    os.replace(tmp, DASH); os.replace(t2, HTML)
    print("PATCHED dashboard.py and dashboard_static.html (backups *.bak_imgui_%s)." % stamp)
    print("Restart the dashboard ONLY when the header reads 'idle', then open http://127.0.0.1:5057/images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
