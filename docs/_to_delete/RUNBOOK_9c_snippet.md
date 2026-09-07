## 9c. Verifying a UI change before it is served (2026-09-06)

Phase G shipped a layout bug past every check the project had. The checks were
not weak — they were the wrong kind:

| check                                   | result on the broken file |
|-----------------------------------------|---------------------------|
| `py_compile dashboard.py`               | clean                     |
| `node --check` on the extracted script  | clean                     |
| CSS braces balanced                     | 138 / 138                 |
| both patch markers present              | yes                       |
| `/api/embeddings`, `/api/entities` present | yes                    |
| JavaScript errors in the browser        | **none**                  |
| the page as a human sees it             | **destroyed**             |

`.sidebar`, `.main` and `.log-panel` each declare `grid-row:2`. The two new
`.splitter` divs did not. CSS Grid's auto-placement (css-grid-1 §8.5) positions
definite-row items first, in document order, and only then fills the leftover
cells with fully-auto items. So the three panes took columns 1–3 and the
splitters were swept into 4 and 5:

```
                       measured, headless Chromium 1680x980
  sidebar    x=0     w=320    column 1
  splitL     x=1334  w=6      column 4     <- wrong
  main       x=320   w=40     column 2     <- crushed into the 6px track
  splitR     x=1340  w=340    column 5     <- wrong
  log-panel  x=326   w=1008   column 3     <- wrong
```

The pipeline table — the entire screen — rendered 40px wide. Nothing threw.

**The rule this establishes: a layout change is not verified until something
has laid the page out.** Parsing it is not laying it out.

### The harness

`scripts/verify_ui.py` serves `dashboard_static.html` on 127.0.0.1:8899 with a
stand-in API (six documents chosen to hit the edges, including one with no
dates at all) and asserts 19 properties in a real browser. It never opens
`data/context.db`, never calls a provider and never touches the running
dashboard.

```powershell
# once, on a dev machine only - NOT a runtime dependency
pip install playwright
playwright install chromium

# every time dashboard_static.html changes
python scripts\verify_ui.py
python scripts\verify_ui.py --shots out\ui   # + screenshots for the record
```

Exit 0 means every assertion held. Non-zero means do not restart the dashboard.

The first three assertions are the ones that would have caught this:

```
  pane order left to right          panes appear in DOM order
  main is the widest pane           the content pane is not a sliver
  neither splitter is wider than 8px
```

Confirmed against the broken file as a negative control: 5/9, with the failure
naming the cause (`got ['sidebar','main','log-panel','splitL','splitR']`).

### Two further defects the render caught

* **Row height.** Embed + Entities pushed the actions cell onto a fourth
  wrapped line: 132.5px → 162.5px a row, one fewer book per screen. Tightening
  `.btn-act` padding *inside `.pipeline-table` only* (the class is used in other
  panels) brings it to 143.5px. Net cost of the two buttons: 11px, not 30px.
* **Reachability.** Once the panes genuinely resize, dragging the middle one
  narrow clips the Actions column, and with `overflow:visible` there is no way
  to scroll to it — Export, Full and the reader link become unclickable.
  Measured at `--lw 200px / --rw 620px`: a 900px table in an 808px box.
  `#pipelineWrap{overflow-x:auto}` fixes it. This defect did not exist before
  Phase G, because the panes could not be resized.

All three are in `scripts/patch_ui_phase_g_fix.py`, and folded into
`patch_ui_phase_g.py` so a fresh application is correct from the start.

### Applying the hotfix

`dashboard.py` serves the HTML with `send_from_directory` (line 511), i.e. it is
read from disk on every request. **The HTML fix therefore needs a hard refresh,
not a restart** — no job is interrupted:

```powershell
python scripts\patch_ui_phase_g_fix.py            # dry run
python scripts\patch_ui_phase_g_fix.py --apply
# then Ctrl+F5 in the browser
```

The `/api/embeddings` and `/api/entities` endpoints live in `dashboard.py` and
do require a restart — see §1, and the correction in §9d.
