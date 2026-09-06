#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ui_phase_g_fix.py - Phase G hotfix: the splitters landed in the wrong
grid cells, which scrambled all three panes. (2026-09-06)

WHAT WENT WRONG
---------------
Phase G widened .app from 3 grid columns to 5:

    grid-template-columns: var(--lw,320px) 6px 1fr 6px var(--rw,340px)

and inserted two <div class="splitter"> elements between the panes in DOM
order:  sidebar, splitL, main, splitR, log-panel.

DOM order is NOT what CSS Grid places by. .sidebar, .main and .log-panel each
carry `grid-row:2`; the new .splitter divs carried no row at all. CSS Grid's
auto-placement algorithm (css-grid-1 s8.5) runs in phases: items with a
definite ROW are positioned first, in document order, then the fully-auto items
fill whatever cells are left. So the three panes claimed columns 1, 2 and 3 -
and the splitters were swept into the leftovers, columns 4 and 5.

Measured in a headless Chromium against the patched file:

    sidebar    x=0     w=320     column 1   (correct by accident)
    splitL     x=1334  w=6       column 4   WRONG
    main       x=320   w=40      column 2   WRONG - squeezed into the 6px track
    splitR     x=1340  w=340     column 5   WRONG
    log-panel  x=326   w=1008    column 3   WRONG

The pipeline table - the entire point of the screen - was crushed into a 40px
strip and the job log sprawled across the middle. The page threw no JavaScript
error, /api/status answered correctly, node --check passed, the CSS braces
balanced and py_compile was clean. Every static check Phase G ran was GREEN.
Only rendering it caught this.

THE FIX
-------
One declaration: .splitter gets `grid-row:2` like the panes it sits between.
All five items then have a definite row and are placed in document order, so
columns 1..5 are sidebar, splitL, main, splitR, log-panel.

    sidebar 0..320 | splitL 320..326 | main 326..1334 | splitR 1334..1340 |
    log-panel 1340..1680          (verified, same headless run)

SECOND, SMALLER FIX
-------------------
Phase G added Embed and Entities to an already-crowded actions cell, which
pushed the buttons onto a fourth wrapped line: row height went 132.5px ->
162.5px, so one fewer document fits on screen. Tightening .btn-act padding
INSIDE the pipeline table only (the same class is used elsewhere) brings it
back to 143.5px. Net cost of the two new buttons: 11px a row, not 30px.

  python scripts\\patch_ui_phase_g_fix.py            # dry run
  python scripts\\patch_ui_phase_g_fix.py --apply
"""
from __future__ import annotations
import argparse, io, os, shutil, sys, time

MARKER = "PHASE_G_FIX_2026_09_06"
HTML = os.path.join("scripts", "dashboard_static.html")

EDITS = [
    # 1. THE FIX. Without grid-row:2 the splitters are auto-placed AFTER the
    #    three panes, which scrambles every column.
    (".splitter{cursor:col-resize;background:var(--border-v,#2a2a2a);transition:background .12s}",
     ".splitter{grid-row:2;cursor:col-resize;background:var(--border-v,#2a2a2a);transition:background .12s}\n"
     "/* PHASE_G_FIX_2026_09_06: grid-row:2 above is load-bearing. .sidebar/.main/\n"
     "   .log-panel all declare grid-row:2, so Grid places THEM first (definite row)\n"
     "   and sweeps anything auto-placed to the end - which put the splitters in\n"
     "   columns 4 and 5 and squeezed .main into the 6px track. */"),

    # 2. give back most of the row height the two new buttons cost.
    ("th.sortable .arrow{opacity:.45;font-size:9px;margin-left:3px}",
     "th.sortable .arrow{opacity:.45;font-size:9px;margin-left:3px}\n"
     "/* Embed + Entities pushed the actions cell to a 4th wrapped line\n"
     "   (132.5px -> 162.5px a row). Scoped to the pipeline table because\n"
     "   .btn-act is used in other panels too. Measured back to 143.5px. */\n"
     ".pipeline-table .btn-act{padding:3px 7px;font-size:10px}\n"
     "/* Third fix. Now that the panes really DO resize, dragging the middle one\n"
     "   narrow clips the Actions column - and with overflow visible there is no\n"
     "   way to scroll to it, so Export/Full/Reader become unreachable. Measured\n"
     "   at --lw 200px / --rw 620px: table 900px in an 808px box. */\n"
     "#pipelineWrap{overflow-x:auto}"),
]


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
    if "PHASE_G_2026_09_06" not in s:
        sys.exit("Phase G is not applied to this file; there is nothing to fix.")

    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    if bad:
        sys.exit("\nABORTED - nothing written.")
    if not args.apply:
        print("\nAll anchors OK. Re-run with --apply."); return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"dashboard_static.html.preGfix.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(HTML, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        s = s.replace("<style>", f"<style>\n/* {MARKER} */", 1)
        io.open(HTML, "w", encoding="utf-8", newline="\n").write(s)
    except Exception as exc:
        shutil.copy2(b, HTML)
        sys.exit(f"FAILED ({exc}) - restored from backup.")
    print("\nApplied. This is a STATIC file: the dashboard serves it from disk,")
    print("so a hard refresh (Ctrl+F5) is enough. No restart, no job interruption.")


if __name__ == "__main__":
    main()
