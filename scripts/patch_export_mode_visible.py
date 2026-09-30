#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_export_mode_visible.py  (2026-09-30)  EXPORT_MODE_VISIBLE_2026_09_30

WHAT HAPPENED
On 2026-09-30 a trilingual export "did not work". It did work - as a Hindi
export. The job at 20:16 IST (kind=export, doc=2015_405693_Shatpath-Brahmanam,
rc 0, 0.8 s) wrote exports/2015_405693_Shatpath-Brahmanam_1-320_hi.html.
The "Export As" select persists its value in localStorage (restoreSettings),
and it had been left on "hi" after the nirukta Hindi export at 12:32. Nothing
on the row's Export button said so; the mode appeared only in the toast
AFTER the click, and data/jobs.jsonl does not record the mode at all.

WHAT THIS CHANGES (dashboard_static.html only - served per request by
@app.get("/"), so a browser reload picks it up; NO dashboard restart)
  1. Every row's Export button shows the edition it will produce:
     "Export (Sa/En/Hi)", "Export (Hindi)", "Export (English)".
  2. Changing "Export As" relabels every row button immediately.
  3. "Export All" asks for confirmation naming the edition and the count.
Unchanged: /api/export, export_html.py, the persisted choice, file names.

Run from the repo root:
  python scripts/patch_export_mode_visible.py --check   # anchors only
  python scripts/patch_export_mode_visible.py           # backup + atomic write
Test:  python -m unittest tests.test_export_mode_ui -v   (fails before, passes after)
"""
from __future__ import annotations
import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

MARK = "EXPORT_MODE_VISIBLE_2026_09_30"
HTML = Path("scripts/dashboard_static.html")

SELECT_OLD = """onchange="localStorage.setItem('exportMode',this.value)">"""
SELECT_NEW = """onchange="localStorage.setItem('exportMode',this.value);syncExportLabels()">"""

BUTTON_OLD = """data-act="export" data-doc="' + esc(r.doc) + '">Export</button>' +"""
BUTTON_NEW = ("""data-act="export" data-doc="' + esc(r.doc) + '"""
              """" title="Edition set by Export As in the left panel">"""
              """Export <span class="exp-mode">' + esc(exportModeShort()) + '</span></button>' +""")

GETMODE_OLD = """function getExportMode() {
  const el = document.getElementById('exportMode');
  return (el && el.value) || 'en';
}"""
GETMODE_NEW = GETMODE_OLD + """
// EXPORT_MODE_VISIBLE_2026_09_30 - the persisted Export As value was invisible
// at the moment of clicking, so a Hindi-only export was taken for a broken
// trilingual one. The row button now names the edition it will produce.
function exportModeShort(m) {
  m = m || getExportMode();
  return m === 'tri' ? '(Sa/En/Hi)' : (m === 'hi' ? '(Hindi)' : '(English)');
}
function syncExportLabels() {
  var t = exportModeShort();
  document.querySelectorAll('.exp-mode').forEach(function(s) { s.textContent = t; });
}"""

BATCH_OLD = """  document.querySelectorAll('button[data-act="' + act + '"]').forEach(async function(b) {"""
BATCH_NEW = """  if (act === 'export') {  // EXPORT_MODE_VISIBLE_2026_09_30
    var nExp = document.querySelectorAll('button[data-act="export"]').length;
    if (!confirm('Export ALL ' + nExp + ' docs as ' + exportModeShort() + '?\\n\\n'
        + 'Change "Export As" in the left panel first if this is not the edition you want.')) return;
  }
""" + BATCH_OLD


def replace_one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        return text, ["%s: matched %d times, expected exactly 1" % (label, n)]
    return text.replace(old, new), []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not HTML.exists():
        print("FAIL: %s not found. Run from the repo root." % HTML)
        return 2
    raw = HTML.read_bytes()
    crlf = raw.count(b"\r\n")
    newline = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("Already patched (%s). Nothing to do." % MARK)
        return 0
    problems = []
    src, p = replace_one(src, SELECT_OLD, SELECT_NEW, "Export As onchange"); problems += p
    src, p = replace_one(src, BUTTON_OLD, BUTTON_NEW, "row Export button"); problems += p
    src, p = replace_one(src, GETMODE_OLD, GETMODE_NEW, "getExportMode"); problems += p
    src, p = replace_one(src, BATCH_OLD, BATCH_NEW, "batchAction loop"); problems += p
    if problems:
        print("REFUSING TO WRITE. Anchors did not match cleanly:")
        for x in problems:
            print("  " + x)
        return 1
    if args.check:
        print("CHECK OK: all 4 anchors match exactly once. Nothing written.")
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    bak = HTML.with_name(HTML.name + ".bak_expmode_" + stamp)
    shutil.copy2(HTML, bak)
    tmp = HTML.with_name(HTML.name + ".tmp_expmode")
    tmp.write_bytes(src.replace("\n", newline).encode("utf-8"))
    os.replace(tmp, HTML)
    print("PATCHED %s (backup %s). Reload the dashboard page; no restart needed." % (HTML, bak))
    return 0


if __name__ == "__main__":
    sys.exit(main())
