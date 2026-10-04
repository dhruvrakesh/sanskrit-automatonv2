#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_shelf_2026_10_04.py  (2026-10-04)  SHELF_2026_10_04

Adds the Shelf (http://127.0.0.1:5057/shelf): every text under its collection header,
with covers, titles, series numbers, translation progress and every edition that
exists, the reader and the image library one click away. See scripts/library_web.py.

  scripts/dashboard.py         registers library_web inside try/except, after the
                               Images tab (a fault there cannot stop the dashboard)
  scripts/dashboard_static.html  a "Shelf" link beside "Images" in the top bar

Needs: scripts/library_web.py, scripts/shelf_static.html, scripts/collections_cfg.py.
Takes effect at the next dashboard restart, done while idle.

  python scripts/patch_shelf_2026_10_04.py --check
  python scripts/patch_shelf_2026_10_04.py
Test: python -m unittest tests.test_shelf_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "SHELF_2026_10_04"
DASH = Path("scripts/dashboard.py")
STATIC = Path("scripts/dashboard_static.html")
NEEDS = [Path("scripts/library_web.py"), Path("scripts/shelf_static.html"), Path("scripts/collections_cfg.py")]

D_OLD = '    print(f"[images] Images tab not loaded: {type(_images_err).__name__}: {_images_err}")\n'
D_NEW = D_OLD + '''
# SHELF_2026_10_04: the Shelf (/shelf) - see scripts/library_web.py. Guarded like the Images tab.
try:
    import library_web as _library_web
    _library_web.register(app, root=ROOT, bs_pdf=_bs_pdf_path, bs_modes=BOOKSMITH_MODES)
except Exception as _shelf_err:
    print(f"[shelf] Shelf not loaded: {type(_shelf_err).__name__}: {_shelf_err}")
'''
S_OLD = '    <a href="/images" title="Image library: ideas, generation, captions (IMAGES_UI_2026_10_03)"'
S_NEW = ('    <a href="/shelf" title="Shelf: every text by collection, with covers and editions (SHELF_2026_10_04)" '
         'style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DA; Shelf</a>\n' + S_OLD)


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in [DASH, STATIC] + NEEDS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    d, dnl = load(DASH); s, snl = load(STATIC)
    if MARK in d and MARK in s:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if (MARK in d) != (MARK in s):
        print("REFUSING: marker in one file only - inspect by hand."); return 1
    probs = []
    for name, src, old in (("dashboard.py", d, D_OLD), ("dashboard_static.html", s, S_OLD)):
        if src.count(old) != 1:
            probs.append("%s: anchor matched %d times" % (name, src.count(old)))
    for need in ("def _bs_pdf_path(", "BOOKSMITH_MODES = "):
        if need not in d:
            probs.append("dashboard.py lacks %r" % need)
    if probs:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in probs]; return 1
    if args.check:
        print("CHECK OK: 2 anchored edits. Nothing written."); return 0
    d2, s2 = d.replace(D_OLD, D_NEW), s.replace(S_OLD, S_NEW)
    stamp = datetime.date.today().strftime("%Y%m%d")
    td = DASH.with_name(DASH.name + ".tmp_shelf"); td.write_bytes(d2.replace("\n", dnl).encode("utf-8"))
    try:
        py_compile.compile(str(td), doraise=True)
    except py_compile.PyCompileError as e:
        td.unlink(missing_ok=True); print("REFUSING TO WRITE: dashboard.py would not compile:\n%s" % e); return 1
    ts = STATIC.with_name(STATIC.name + ".tmp_shelf"); ts.write_bytes(s2.replace("\n", snl).encode("utf-8"))
    for p in (DASH, STATIC):
        shutil.copy2(p, p.with_name(p.name + ".bak_shelf_" + stamp))
    os.replace(td, DASH); os.replace(ts, STATIC)
    print("PATCHED dashboard.py and dashboard_static.html. Restart the dashboard while idle, then open /shelf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
