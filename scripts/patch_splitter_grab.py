#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_splitter_grab.py - make the pane dividers actually draggable in a real
browser. (PHASE_G_GRAB, 2026-09-06)

WHY THE TESTS PASSED AND THE UI DID NOT
---------------------------------------
verify_ui.py asserts "drag resizes the left pane" and it passes, 19/19, against
the exact file on disk. The panes still could not be resized by hand. The gap is
the test's own mechanism:

  Playwright's mouse.down/move/up dispatches SYNTHETIC pointer events. A real
  mouse press on a divider, followed by a move, ALSO starts a native text
  selection over whatever is under the cursor. The sidebar is full of text. The
  browser begins selecting it, the drag reads as a selection gesture, and the
  divider appears dead. Synthetic events never do this, so the test cannot see
  it.

Three defects, each fixed here:

1. NO POINTER CAPTURE. The handler listened on `document` for mousemove. Once
   the cursor leaves the 6px divider - which it does immediately, that being the
   point of dragging - events still arrive, but the browser is now also
   selecting text, and any element that swallows the event (an iframe, a
   scrollbar, a re-render) ends the drag silently.
   -> pointerdown + setPointerCapture: the divider owns every subsequent move
      until release, regardless of what the cursor is over.

2. TEXT SELECTION DURING DRAG. Nothing set user-select:none, so the gesture
   competed with a selection.
   -> body gets user-select:none and cursor:col-resize for the drag's duration,
      restored on release.

3. A 6px HIT TARGET, adjacent to the sidebar's scrollbar. At 125-150% Windows
   scaling the visible line is a few device pixels, and the sidebar's own
   scrollbar sits immediately to its left, so an aimed click usually lands on
   the scrollbar instead.
   -> the visual line stays 6px (the layout is unchanged), but an invisible
      ::before extends the grabbable area to 16px, and a visible grip is drawn
      so it is obvious the divider is a control.

Also: touch-action:none, so a pen or touch drag is not stolen by scrolling.

NOTHING ABOUT THE LAYOUT CHANGES. The grid tracks, the clamp (200-700px), the
localStorage persistence and the double-click reset all behave exactly as
before. This is the grab, not the geometry.

  python scripts\\patch_splitter_grab.py            # dry run
  python scripts\\patch_splitter_grab.py --apply
  python scripts\\verify_ui.py                      # gate (now 22 checks)

STATIC FILE: dashboard.py serves it with send_from_directory, so a hard refresh
(Ctrl+F5) is enough. No restart, no job interrupted.
"""
from __future__ import annotations
import argparse, io, os, shutil, sys, time

MARKER = "PHASE_G_GRAB_2026_09_06"
HTML = os.path.join("scripts", "dashboard_static.html")

CSS_OLD = ".splitter{grid-row:2;cursor:col-resize;background:var(--border-v,#2a2a2a);transition:background .12s}"
CSS_NEW = """.splitter{grid-row:2;cursor:col-resize;background:var(--border-v,#2a2a2a);transition:background .12s;
   position:relative;touch-action:none}
/* PHASE_G_GRAB_2026_09_06: the visible line stays 6px so the layout is
   unchanged, but the GRABBABLE area is widened to 16px by an invisible
   overlay. A 6px target at 150% Windows scaling, sitting right beside the
   sidebar's scrollbar, is why "drag the divider" kept landing on the
   scrollbar instead. */
.splitter::before{content:"";position:absolute;top:0;bottom:0;left:-5px;right:-5px;cursor:col-resize}
/* A visible grip, so the divider reads as a control rather than a border. */
.splitter::after{content:"";position:absolute;left:1px;width:4px;top:50%;height:34px;
   margin-top:-17px;border-radius:2px;background:var(--gold-dim,#9a721080);opacity:.55;
   transition:opacity .12s,background .12s;pointer-events:none}
.splitter:hover::after,.splitter.dragging::after{opacity:1;background:var(--gold,#c9a227)}"""

JS_OLD = """  function drag(id, varName, storeKey, fromLeft){
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('mousedown', function(ev){
      ev.preventDefault();
      el.classList.add('dragging');
      function move(e){
        var w = fromLeft ? e.clientX : (window.innerWidth - e.clientX);
        w = Math.max(200, Math.min(700, w));          // keep both panes usable
        var px = w + 'px';
        document.documentElement.style.setProperty(varName, px);
        try { localStorage.setItem(storeKey, px); } catch(_) {}
      }
      function up(){
        el.classList.remove('dragging');
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', up);
    });"""

JS_NEW = """  function drag(id, varName, storeKey, fromLeft){
    var el = document.getElementById(id);
    if (!el) return;
    // PHASE_G_GRAB_2026_09_06 — pointer events + capture, not mouse events.
    // The old handler listened on `document` for mousemove without capture and
    // without suppressing selection, so a REAL press-and-move started a native
    // text selection over the sidebar and the drag read as dead. Synthetic
    // (Playwright) events never select text, which is why the suite passed
    // 19/19 while the UI could not be resized by hand.
    el.addEventListener('pointerdown', function(ev){
      if (ev.button !== 0) return;                    // left button only
      ev.preventDefault();
      el.classList.add('dragging');
      var prevUS = document.body.style.userSelect;
      var prevCur = document.body.style.cursor;
      document.body.style.userSelect = 'none';        // stop the selection race
      document.body.style.cursor = 'col-resize';
      try { el.setPointerCapture(ev.pointerId); } catch(_) {}
      function move(e){
        var w = fromLeft ? e.clientX : (window.innerWidth - e.clientX);
        w = Math.max(200, Math.min(700, w));          // keep both panes usable
        var px = w + 'px';
        document.documentElement.style.setProperty(varName, px);
        try { localStorage.setItem(storeKey, px); } catch(_) {}
      }
      function up(e){
        el.classList.remove('dragging');
        document.body.style.userSelect = prevUS;
        document.body.style.cursor = prevCur;
        try { el.releasePointerCapture(ev.pointerId); } catch(_) {}
        el.removeEventListener('pointermove', move);
        el.removeEventListener('pointerup', up);
        el.removeEventListener('pointercancel', up);
      }
      el.addEventListener('pointermove', move);
      el.addEventListener('pointerup', up);
      el.addEventListener('pointercancel', up);       // alt-tab, lost focus
    });"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(HTML):
        sys.exit(f"not found: {HTML} - run from the repo root")
    s = io.open(HTML, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return
    if "PHASE_G_FIX_2026_09_06" not in s:
        sys.exit("Run patch_ui_phase_g_fix.py first - this builds on the grid fix.")

    edits = [(CSS_OLD, CSS_NEW), (JS_OLD, JS_NEW)]
    bad = False
    for i, (old, _new) in enumerate(edits, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAnchors OK. Re-run with --apply, then: python scripts\\verify_ui.py")
        return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"dashboard_static.html.preGrab.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(HTML, b)
    print(f"  backup: {b}")
    try:
        for old, new in edits:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        s = s.replace("<style>", f"<style>\n/* {MARKER} */", 1)
        io.open(HTML, "w", encoding="utf-8", newline="\n").write(s)
    except Exception as exc:
        shutil.copy2(b, HTML)
        sys.exit(f"FAILED ({exc}) - restored from backup.")

    print("\nApplied. Static file - Ctrl+F5 is enough, no restart.")
    print("The divider now shows a gold grip; grab anywhere within ~16px of it.")


if __name__ == "__main__":
    main()
