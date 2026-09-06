#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ui.py - render dashboard_static.html in a headless browser and ASSERT
its structure, BEFORE it is served to anyone. (2026-09-06)

WHY THIS EXISTS
---------------
Phase G passed every static check it had: py_compile clean, `node --check`
clean, CSS braces balanced 138/138, both patch markers present, both new
endpoints present in dashboard.py. It was still broken. .sidebar, .main and
.log-panel each declare `grid-row:2`; the two new .splitter divs did not, and
CSS Grid places definite-row items before auto-placed ones - so the splitters
were swept into columns 4 and 5 and .main was squeezed into the 6px track.
The pipeline table rendered 40px wide. No JavaScript error was thrown.

A layout bug is invisible to every check that does not lay the page out. So
this script lays it out.

It never touches data/context.db, never calls a provider, and never talks to
the running dashboard. It serves the HTML itself with a stand-in API.

INSTALL (dev machine only - this is not a runtime dependency)
    pip install playwright
    playwright install chromium

RUN
    python scripts\\verify_ui.py                 # assert only
    python scripts\\verify_ui.py --shots out\\ui  # also write screenshots

Exit code 0 = every assertion held. Non-zero = do not ship it.
"""
from __future__ import annotations
import argparse, http.server, io, json, os, socketserver, sys, threading, time

HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_static.html")
PORT = 8899
NOW = time.time()
D = 86400

# Six rows chosen to exercise the edges: a book mid-translation, one never
# OCR'd, two finished, and one with NO dates at all (a legacy row) because the
# "missing date sorts last" rule is the part most likely to be got wrong.
DOCS = [
    ("2015_405693_Shatpath-Brahmanam", 320, 320, 320, 2441, 185, 0, NOW-41*D, NOW-0.02*D,
     {"mula": 2150, "frontmatter": 208, "noise": 83}),
    ("rgveda_samhita_wilson",          1065, 0,   0,    0,   0, 0, NOW-9*D,  NOW-9*D,  {}),
    ("mahabharata_bori_01",             118, 118, 118, 3310, 3310, 2, NOW-96*D, NOW-3*D,
     {"mula": 2984, "frontmatter": 271, "noise": 55}),
    ("arthashastra_kangle",              64, 64,  64, 1204,  902, 1, NOW-63*D, NOW-5*D,
     {"mula": 1010, "frontmatter": 160, "noise": 34}),
    ("bhagavata_purana_skandha_01",      92, 92,  92, 1876, 1876, 3, NOW-150*D, NOW-31*D,
     {"mula": 1702, "frontmatter": 141, "noise": 33}),
    ("no_dates_legacy_doc",               0,  0,  44,  210,   96, 0, None, None, {}),
]


def status_rows():
    return [{"doc": d, "pdf_count": p, "jsonl_count": j, "ingested_pages": i,
             "total_lines": l, "translated_lines": t, "exports": e,
             "composition": c, "first_seen": fs, "last_ocr": la, "last_activity": la}
            for (d, p, j, i, l, t, e, fs, la, c) in DOCS]


GET = {
    "/api/status":        status_rows,
    "/api/progress":      lambda: {"status": "idle"},
    "/api/corpus":        lambda: {"corpus_root": "E:\\Sanskrit\\corpus", "categories": []},
    "/api/jobs/history":  lambda: [],
    "/api/jobs/running":  lambda: [],
    "/api/qa/summary":    lambda: {"docs": [], "totals": {}},
    "/api/usage":         lambda: {
        "total_calls": 4127, "total_out_chars": 9318442, "cost_estimate_usd": 8.73,
        "budget": {"spent_usd": 8.73, "cap_usd": 25.0},
        "note": "stand-in data - verify_ui.py",
        "by_engine": [{"engine": "gemini:gemini-2.5-flash", "calls": 3811,
                       "out_chars": 8402119, "cost_usd": 6.91}]},
}


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _j(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            b = io.open(HTML, encoding="utf-8").read().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        return self._j(GET[path]() if path in GET else {})

    def do_POST(self):
        return self._j({"error": "verify_ui stub - no job is launched"})


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


CHECKS = []


def check(name, got, want, how=lambda a, b: a == b):
    ok = how(got, want)
    CHECKS.append((ok, name, got, want))
    return ok


def run(shots=None):
    from playwright.sync_api import sync_playwright
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1680, "height": 980})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text)
              if m.type == "error" and "fonts.g" not in m.location.get("url", "")
              and "ERR_TUNNEL" not in m.text else None)
        pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
        pg.wait_for_timeout(1200)

        # ---- THE BUG THAT GOT THROUGH. Every pane must be in its own column,
        #      in document order. This is the assertion Phase G lacked.
        geo = pg.evaluate("""() => [...document.querySelector('.app').children]
            .filter(c => !c.classList.contains('top-bar'))
            .map(c => { const r = c.getBoundingClientRect();
                        return [c.id || c.className, Math.round(r.x), Math.round(r.width)]; })""")
        order = [g[0] for g in geo]
        check("pane order left to right", [g[0] for g in sorted(geo, key=lambda g: g[1])], order)
        check("main is the widest pane", max(geo, key=lambda g: g[2])[0], "main")
        check("neither splitter is wider than 8px",
              max(g[2] for g in geo if g[0].startswith("split")) <= 8, True)

        check("grid has 5 tracks",
              len(pg.evaluate("getComputedStyle(document.querySelector('.app'))"
                              ".gridTemplateColumns").split()), 5)
        check("pipeline table rendered",
              pg.eval_on_selector_all(".pipeline-table tbody tr", "e => e.length"), len(DOCS))
        check("date columns present",
              pg.eval_on_selector_all(".pipeline-table thead th", "e => e.map(x => x.textContent.trim())"),
              ["Document", "PDFs", "Ingested", "Added", "Last run",
               "Lines", "Translated", "Exports", "Actions"])
        check("Embed and Entities buttons present",
              set(pg.eval_on_selector_all(".pipeline-table tbody tr:first-child .btn-act",
                                          "e => e.map(x => x.dataset.act)")) >=
              {"embeddings", "entities"}, True)
        check("a row with no dates shows em-dashes, not 1970",
              pg.eval_on_selector_all(
                  "tr[data-doc='no_dates_legacy_doc'] td:nth-child(4),"
                  "tr[data-doc='no_dates_legacy_doc'] td:nth-child(5)",
                  "e => e.map(x => x.textContent.trim())"), ["\u2014", "\u2014"])

        if shots:
            os.makedirs(shots, exist_ok=True)
            pg.eval_on_selector("#pipelineWrap", "e => e.scrollIntoView({block:'start'})")
            pg.screenshot(path=os.path.join(shots, "ui_1_pipeline.png"))

        # ---- sorting, both directions, missing values last in BOTH
        pg.click("th.sortable[data-sort='first_seen']")
        pg.wait_for_timeout(250)
        desc = pg.eval_on_selector_all(".pipeline-table tbody tr", "e => e.map(x => x.dataset.doc)")
        pg.click("th.sortable[data-sort='first_seen']")
        pg.wait_for_timeout(250)
        asc = pg.eval_on_selector_all(".pipeline-table tbody tr", "e => e.map(x => x.dataset.doc)")
        check("descending by Added", desc[0], "rgveda_samhita_wilson")
        check("ascending by Added", asc[0], "bhagavata_purana_skandha_01")
        check("undated row last DESCENDING", desc[-1], "no_dates_legacy_doc")
        check("undated row last ASCENDING", asc[-1], "no_dates_legacy_doc")
        check("sort persisted", json.loads(pg.evaluate("localStorage.getItem('pipeSort')"))["k"],
              "first_seen")

        # ---- splitter drag, clamp, persistence, reset
        box = pg.query_selector("#splitL").bounding_box()
        pg.mouse.move(box["x"] + 3, box["y"] + box["height"] / 2)
        pg.mouse.down(); pg.mouse.move(470, box["y"] + box["height"] / 2, steps=12); pg.mouse.up()
        pg.wait_for_timeout(250)
        check("drag resizes the left pane",
              pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--lw')").strip(),
              "470px")
        box = pg.query_selector("#splitL").bounding_box()
        pg.mouse.move(box["x"] + 3, box["y"] + box["height"] / 2)
        pg.mouse.down(); pg.mouse.move(15, box["y"] + box["height"] / 2, steps=10); pg.mouse.up()
        pg.wait_for_timeout(200)
        check("a pane cannot be dragged shut (clamped at 200px)",
              pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--lw')").strip(),
              "200px")

        # ---- narrow middle pane must still reach the Actions column
        pg.evaluate("document.documentElement.style.setProperty('--lw','200px');"
                    "document.documentElement.style.setProperty('--rw','620px')")
        pg.wait_for_timeout(250)
        check("Actions stay reachable when the middle pane is narrow",
              pg.eval_on_selector("#pipelineWrap",
                  "e => e.scrollWidth <= e.clientWidth || getComputedStyle(e).overflowX === 'auto'"),
              True)
        if shots:
            pg.screenshot(path=os.path.join(shots, "ui_2_narrow.png"))

        pg.reload(wait_until="networkidle"); pg.wait_for_timeout(900)
        check("pane width survives a reload",
              pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--lw')").strip(),
              "200px")
        pg.dblclick("#splitL"); pg.wait_for_timeout(200)
        check("double-click resets the pane", pg.evaluate("localStorage.getItem('paneL')"), None)

        check("no JavaScript errors", errs, [])
        b.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shots", default=None, help="directory for screenshots")
    args = ap.parse_args()
    if not os.path.exists(HTML):
        sys.exit(f"not found: {HTML}")
    httpd = serve()
    try:
        run(args.shots)
    except Exception as exc:
        # A broken layout can make an element unclickable, so the run may DIE
        # rather than merely fail. Keep the checks collected so far and report
        # the crash as the failure it is.
        CHECKS.append((False, f"harness completed without error ({type(exc).__name__})",
                       str(exc).splitlines()[0][:120], "no exception"))
    finally:
        httpd.shutdown()

    print("=" * 74)
    print("UI VERIFICATION - dashboard_static.html rendered in headless Chromium")
    print("=" * 74)
    bad = 0
    for ok, name, got, want in CHECKS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        got  : {got}")
            print(f"        want : {want}")
            bad += 1
    print("-" * 74)
    print(f"  {len(CHECKS)-bad}/{len(CHECKS)} checks passed")
    if bad:
        print("\n  DO NOT SHIP. Fix the layout before restarting the dashboard.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
