#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_mirror_cap_2026_10_12.py  (2026-10-12)  MIRROR_CAP_2026_10_12

After PATH_2026_10_12 (408e11b), the afternoon of 12 Oct:
  corpus_sync.py: the mirror run that was to retire the withdrawn Bodhicaryavatara and the two retired Dhanur Veda
    copies stopped: "corpus_retire: canceling statement due to statement timeout" (13:57 IST, and the scheduled
    run at 14:32 again). Their documents were retired on the site, their passages are still live. The first call
    retired the Bodhicaryavatara's 824 vectors at once, and a vector retired is a new entry in the HNSW index, as an
    insert is (the vectors are sent 25 to a call for that reason since 9 Oct). Vectors are now retired 25 to a call,
    and a retire the database cancels for its timeout is sent again in halves, as an ingest is (corpus_retire only
    retires rows still live, so a second call is safe).
  ocr_consensus.py: --max-usd refused a run whose estimate was above it, and nothing more; a text dearer than its
    estimate could spend past it. What the run has spent is read from usage_log before each page (the vision calls
    of this text after the run began), and the run stops before a page would take it past --max-usd; the redo
    round too.
  text_path.py: the corpus price (the last 300 vision calls) was $0.0100 a page after the Natyasastra's run, four
    times the median text's ($0.0024): the chart said about $38 for the 28 repairs. The estimate and the cap stay
    at the corpus price (the run refuses an estimate above its cap), and the median text's price is given beside
    them.
  dashboard.py (on a restart): /path shows the median text's price beside the corpus's.

Needs PATH_2026_10_12 in each file. Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and
encodings; each .py is compiled before it replaces the original; backups .bak_mirrorcap_<date>.
  python scripts\\patch_mirror_cap_2026_10_12.py --check
  python scripts\\patch_mirror_cap_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "MIRROR_CAP_2026_10_12"
NEEDS = {"scripts/corpus_sync.py": "PATH_2026_10_12", "scripts/ocr_consensus.py": "PATH_2026_10_12",
         "scripts/text_path.py": "PATH_2026_10_12", "scripts/dashboard.py": "PATH_2026_10_12"}
FILES = list(NEEDS)

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_sync.py', 1,
     r'''                                 # timed out on 2026-10-09, each row an insert into the HNSW index
MAX_KEYS_PER_RETIRE = 5000
DEFAULT_BATCH_BYTES = 1_500_000  # JSON bytes per call, before gzip

''',
     r'''                                 # timed out on 2026-10-09, each row an insert into the HNSW index
MAX_KEYS_PER_RETIRE = 5000
MAX_VEC_KEYS_PER_RETIRE = 25     # MIRROR_CAP_2026_10_12: a vector retired is a new entry in the HNSW index, as an
                                 # insert is: the Bodhicaryavatara's 824 in one call timed out on 2026-10-12
DEFAULT_BATCH_BYTES = 1_500_000  # JSON bytes per call, before gzip

''')
edit('scripts/corpus_sync.py', 2,
     r'''        st["retire"] += len(keys)
        if self.apply:
            for i in range(0, len(keys), MAX_KEYS_PER_RETIRE):
                res = self.sink.retire(table, group, keys[i:i + MAX_KEYS_PER_RETIRE], self.run_id) or {}
                st["retired"] += int(res.get("retired", 0))
        return True

    def diff_group(self, g: Group, remote_manifest: dict, retire: bool = True):
''',
     r'''        st["retire"] += len(keys)
        if self.apply:
            step = MAX_VEC_KEYS_PER_RETIRE if table == "vectors" else MAX_KEYS_PER_RETIRE
            for i in range(0, len(keys), step):
                st["retired"] += self._retire_keys(table, group, keys[i:i + step])
        return True

    def _retire_keys(self, table: str, group: str, keys: list) -> int:
        """MIRROR_CAP_2026_10_12: as _ingest: a call the database cancels for its statement timeout was rolled back
        whole, and corpus_retire is idempotent (it retires only rows still live), so it is sent again as two
        halves, down to one key. Any other error, and a one-key timeout, is raised as before."""
        try:
            res = self.sink.retire(table, group, keys, self.run_id) or {}
            return int(res.get("retired", 0))
        except SinkError as e:
            if "statement timeout" not in str(e) or len(keys) <= 1:
                raise
            half = len(keys) // 2
            self._p("    %s %s: the database timed out retiring %d rows; sending them as %d + %d"
                    % (table, group, len(keys), half, len(keys) - half))
            return self._retire_keys(table, group, keys[:half]) + self._retire_keys(table, group, keys[half:])

    def diff_group(self, g: Group, remote_manifest: dict, retire: bool = True):
''')
edit('scripts/ocr_consensus.py', 3,
     r'''

def run_vision(todo: list, vdir: Path, doc: str, led: dict, model=None, budget=None, runner=None):
    """Vision on each page -> (read, failed, why it stopped or ""). A failed page goes into led; only pages
    that never failed before count towards the five failures in a row that stop the run. The cap (budget) is
    asked before each page, and after a failure: ocr_vision.py exits 0 with nothing when the cap refuses it."""
    runner = runner or run
    ok = fails = consec = 0
''',
     r'''

# MIRROR_CAP_2026_10_12: --max-usd refused a run whose estimate was above it, and nothing more: a text dearer than
# its estimate (the Natyasastra's pages cost $0.0111, not the corpus's $0.0024) could spend past it. What this run
# has spent is now read from usage_log (the calls after its start, priced as measured_cost_per_page prices them)
# before each page, and the run stops before a page would take it past --max-usd.
def usage_mark(db) -> int:
    """The last usage_log id (0 when none or unreadable): this run's calls are the ones after it."""
    try:
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            r = con.execute("SELECT MAX(id) FROM usage_log").fetchone()
        finally:
            con.close()
        return int((r or [0])[0] or 0)
    except Exception:
        return 0


def spent_since(db, doc: str, mark: int) -> float:
    """USD of this text's vision calls in usage_log after mark (0.0 when unreadable)."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import cost_tracker
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            rows = con.execute("SELECT engine, in_tokens, out_tokens FROM usage_log WHERE kind='ocr_vision' AND doc=? "
                               "AND id > ?", (doc, int(mark or 0))).fetchall()
        finally:
            con.close()
        usd = 0.0
        for eng, tin, tout in rows:
            pin, pout = cost_tracker._get_pricing(eng or "")
            usd += ((tin or 0) * pin + (tout or 0) * pout) / 1e6
        return usd
    except Exception:
        return 0.0


def run_cap(db, doc: str, max_usd: float, per_page: float, mark: int):
    """-> a callable: "" while one more page fits under --max-usd, else why the run stops."""
    def check() -> str:
        spent = spent_since(db, doc, mark)
        if spent + max(0.0, per_page) > max_usd:
            return ("this run's --max-usd $%.2f is reached ($%.2f spent; a page costs about $%.4f)"
                    % (max_usd, spent, per_page))
        return ""
    return check


def run_vision(todo: list, vdir: Path, doc: str, led: dict, model=None, budget=None, runner=None, cap=None):
    """Vision on each page -> (read, failed, why it stopped or ""). A failed page goes into led; only pages
    that never failed before count towards the five failures in a row that stop the run. The spend cap (budget)
    is asked before each page, and after a failure: ocr_vision.py exits 0 with nothing when the cap refuses it.
    cap (MIRROR_CAP_2026_10_12) is this run's --max-usd, asked before each page."""
    runner = runner or run
    ok = fails = consec = 0
''')
edit('scripts/ocr_consensus.py', 4,
     r'''        if budget is not None and not budget():
            stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        before = int((led.get(stem) or {}).get("fails") or 0)
''',
     r'''        if budget is not None and not budget():
            stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        why = cap() if cap is not None else ""
        if why:
            stopped = why
            break
        before = int((led.get(stem) or {}).get("fails") or 0)
''')
edit('scripts/ocr_consensus.py', 5,
     r'''        if args.max_pages and len(todo) > args.max_pages:
            todo = todo[:args.max_pages]
        cpp = measured_cost_per_page(args.db, doc=doc)   # COST_RATIO_2026_10_05: this text's own rate
        est = len(todo) * cpp
''',
     r'''        if args.max_pages and len(todo) > args.max_pages:
            todo = todo[:args.max_pages]
        _mark = usage_mark(args.db)   # MIRROR_CAP_2026_10_12: what this run spends comes after it
        cpp = measured_cost_per_page(args.db, doc=doc)   # COST_RATIO_2026_10_05: this text's own rate
        est = len(todo) * cpp
''')
edit('scripts/ocr_consensus.py', 6,
     r'''            except Exception:
                _budget = None
            try:
                n_ok, fails, stopped = run_vision(todo, vdir, doc, led, args.model, _budget)
            finally:
                write_failed(work, doc, led)
''',
     r'''            except Exception:
                _budget = None
            _cap = run_cap(args.db, doc, args.max_usd, cpp, _mark)   # MIRROR_CAP_2026_10_12
            try:
                n_ok, fails, stopped = run_vision(todo, vdir, doc, led, args.model, _budget, cap=_cap)
            finally:
                write_failed(work, doc, led)
''')
edit('scripts/ocr_consensus.py', 7,
     r'''                    if not stem.startswith(doc + "_"):
                        continue
                    old = vdir / (stem + ".jsonl")
                    if old.exists():
''',
     r'''                    if not stem.startswith(doc + "_"):
                        continue
                    why = run_cap(args.db, doc, args.max_usd, measured_cost_per_page(args.db, doc=doc), _mark)()
                    if why:   # MIRROR_CAP_2026_10_12: the redo round is under the same --max-usd
                        print("  STOPPING the redo round: %s. The pages not redone keep their reading." % why)
                        break
                    old = vdir / (stem + ".jsonl")
                    if old.exists():
''')
edit('scripts/text_path.py', 8,
     r'''a page so far). --max-usd is set from the estimate; a run that reaches it stops before spending more, and
its first pages measure the text's own price for the next chart.

It opens the database read-only (repair_text.assess, as the Sources page does), reads the page folders, the
''',
     r'''a page so far). --max-usd is set from the estimate; a run that reaches it stops before spending more, and
its first pages measure the text's own price for the next chart.
MIRROR_CAP_2026_10_12: the corpus price is that of the last 300 vision calls, so one dear text read last
raises it for all (on 12 Oct, $0.0100 a page after the Natyasastra's run; the median text $0.0024). The
estimate and the cap stay at the corpus price (ocr_consensus.py refuses a run whose estimate is above
--max-usd, and since this patch stops a run before a page would take it past), and the median of the
texts measured is given beside it, as what a text not yet measured most likely costs.

It opens the database read-only (repair_text.assess, as the Sources page does), reads the page folders, the
''')
edit('scripts/text_path.py', 9,
     r'''            pass
    out["vision_dear"] = round(max(dear, out["vision_page"] or 0.0), 5)
    return out


def money_line(tt: dict) -> str:
    """'about $X now (up to $Y at the dearest text's price); then about $Z to translate', the parts that are not 0."""
    parts = []
    if tt.get("cost"):
        hi = tt.get("cost_hi") or 0.0
        parts.append("about %s now%s" % (usd(tt["cost"]), (" (up to %s at the dearest text's price)" % usd(hi))
                                         if hi > 1.05 * tt["cost"] else ""))
    if tt.get("then"):
        parts.append("then about %s to translate" % usd(tt["then"]))
''',
     r'''            pass
    out["vision_dear"] = round(max(dear, out["vision_page"] or 0.0), 5)
    each = []   # MIRROR_CAP_2026_10_12: the median of the texts measured
    for d in mine:
        try:
            x = float(oc.measured_cost_per_page(db, fallback=0.0, doc=d)) if oc else 0.0
        except Exception:
            x = 0.0
        if x > 0:
            each.append(x)
    each.sort()
    out["vision_median"] = (round(each[len(each) // 2] if len(each) % 2 else
                                  (each[len(each) // 2 - 1] + each[len(each) // 2]) / 2.0, 5) if len(each) >= 3 else None)
    return out


def money_line(tt: dict) -> str:
    """'about $X now (from $W at the median text's price; up to $Y at the dearest text's price); then about $Z to
    translate', the parts that are not 0."""
    parts = []
    if tt.get("cost"):
        hi, lo = tt.get("cost_hi") or 0.0, tt.get("cost_lo")
        side = []
        if lo is not None and lo < 0.95 * tt["cost"]:   # MIRROR_CAP_2026_10_12
            side.append("from %s at the median text's price" % usd(lo))
        if hi > 1.05 * tt["cost"]:
            side.append("up to %s at the dearest text's price" % usd(hi))
        parts.append("about %s now%s" % (usd(tt["cost"]), (" (%s)" % "; ".join(side)) if side else ""))
    if tt.get("then"):
        parts.append("then about %s to translate" % usd(tt["then"]))
''')
edit('scripts/text_path.py', 10,
     r'''            dear = max(cpp, pr.get("vision_dear") or cpp)
            est_hi = est if own else todo * dear
            note = ("about %d pages at %s a page, measured on this text" % (todo, per_page(cpp)) if own else
                    "about %d pages at %s a page, the corpus price: not measured on this text yet; up to %s at the "
                    "dearest text's %s; it stops at the cap" % (todo, per_page(cpp), usd(est_hi), per_page(dear)))
            o.update(path="repair", why=("Tesseract's text: %s; %s; vision has read %d of its %d pages"
                                         % (lvl, ("%d of %d passages translated from it" % (en, n)) if en else
''',
     r'''            dear = max(cpp, pr.get("vision_dear") or cpp)
            est_hi = est if own else todo * dear
            med = pr.get("vision_median")
            est_lo = est if (own or not med) else min(est, todo * med)   # MIRROR_CAP_2026_10_12
            note = ("about %d pages at %s a page, measured on this text" % (todo, per_page(cpp)) if own else
                    "about %d pages at %s a page, the corpus price: not measured on this text yet; up to %s at the "
                    "dearest text's %s%s; it stops at the cap" % (
                        todo, per_page(cpp), usd(est_hi), per_page(dear),
                        ("; about %s at the median text's %s" % (usd(todo * med), per_page(med))) if med else ""))
            o.update(path="repair", why=("Tesseract's text: %s; %s; vision has read %d of its %d pages"
                                         % (lvl, ("%d of %d passages translated from it" % (en, n)) if en else
''')
edit('scripts/text_path.py', 11,
     r'''                     next=[q0 + " --repair --max-usd %.2f   (%s)" % (cap, note),
                           rp + "   (after it: the changed pages, the plan, free)"],
                     cost=est, cost_hi=est_hi, then=tr_cost(n, n, pr))
            if f.get("changed", 0) > 0 and vpages:
                o["also"].append("the %d page(s) vision has read can go in now: %s   (the plan, free)" % (f["changed"], rp))
''',
     r'''                     next=[q0 + " --repair --max-usd %.2f   (%s)" % (cap, note),
                           rp + "   (after it: the changed pages, the plan, free)"],
                     cost=est, cost_hi=est_hi, cost_lo=est_lo, then=tr_cost(n, n, pr))
            if f.get("changed", 0) > 0 and vpages:
                o["also"].append("the %d page(s) vision has read can go in now: %s   (the plan, free)" % (f["changed"], rp))
''')
edit('scripts/text_path.py', 12,
     r'''        if t.get("retired"):
            continue
        x = totals.setdefault(t["path"], {"texts": 0, "cost": 0.0, "cost_hi": 0.0, "then": 0.0})
        x["texts"] += 1; x["cost"] += t.get("cost") or 0.0; x["then"] += t.get("then") or 0.0
        x["cost_hi"] += t.get("cost_hi") or t.get("cost") or 0.0
    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices": pr, "texts": texts,
            "totals": totals, "paths": [list(p) for p in PATHS]}
''',
     r'''        if t.get("retired"):
            continue
        x = totals.setdefault(t["path"], {"texts": 0, "cost": 0.0, "cost_hi": 0.0, "cost_lo": 0.0, "then": 0.0})
        x["texts"] += 1; x["cost"] += t.get("cost") or 0.0; x["then"] += t.get("then") or 0.0
        x["cost_hi"] += t.get("cost_hi") or t.get("cost") or 0.0
        x["cost_lo"] += t["cost_lo"] if t.get("cost_lo") is not None else (t.get("cost") or 0.0)
    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "prices": pr, "texts": texts,
            "totals": totals, "paths": [list(p) for p in PATHS]}
''')
edit('scripts/text_path.py', 13,
     r'''def show(res: dict, one: bool) -> None:
    pr = res["prices"]
    print("text_path.py  %s  (read-only)   vision %s a page (the corpus; %d text(s) priced from their own calls, the "
          "dearest %s), translation %s a passage (%s)"
          % (MARK, per_page(pr["vision_page"] or 0), len(pr.get("measured") or []), per_page(pr.get("vision_dear") or 0),
             "$%.5f" % pr["passage"], pr["passage_from"]))
    names = {k: label for k, label, _ in PATHS}
    cur = None
''',
     r'''def show(res: dict, one: bool) -> None:
    pr = res["prices"]
    print("text_path.py  %s  (read-only)   vision %s a page (the corpus, its last 300 calls; %d text(s) priced from "
          "their own calls, the median %s, the dearest %s), translation %s a passage (%s)"
          % (MARK, per_page(pr["vision_page"] or 0), len(pr.get("measured") or []),
             per_page(pr.get("vision_median") or 0) if pr.get("vision_median") else "-",
             per_page(pr.get("vision_dear") or 0), "$%.5f" % pr["passage"], pr["passage_from"]))
    names = {k: label for k, label, _ in PATHS}
    cur = None
''')
edit('scripts/text_path.py', 14,
     r'''    c = sum(v["cost"] for v in res["totals"].values())
    hi = sum(v.get("cost_hi") or v["cost"] for v in res["totals"].values())
    th = sum(v["then"] for v in res["totals"].values())
    print("\nVERDICT: %d text(s) charted: %s; about %s now%s, then about %s of translation"
          % (sum(v["texts"] for v in res["totals"].values()),
             ", ".join("%d %s" % (res["totals"][k]["texts"], names[k].lower()) for k, _, _ in PATHS if k in res["totals"]),
             usd(c), (" (up to %s at the dearest text's price)" % usd(hi)) if hi > 1.05 * c else "", usd(th)))


''',
     r'''    c = sum(v["cost"] for v in res["totals"].values())
    hi = sum(v.get("cost_hi") or v["cost"] for v in res["totals"].values())
    lo = sum(v["cost_lo"] if v.get("cost_lo") is not None else v["cost"] for v in res["totals"].values())
    th = sum(v["then"] for v in res["totals"].values())
    ml = money_line({"cost": c, "cost_hi": hi, "cost_lo": lo})
    print("\nVERDICT: %d text(s) charted: %s; %s, then about %s of translation"
          % (sum(v["texts"] for v in res["totals"].values()),
             ", ".join("%d %s" % (res["totals"][k]["texts"], names[k].lower()) for k, _, _ in PATHS if k in res["totals"]),
             ml or "about $0.0000 now", usd(th)))


''')
edit('scripts/text_path.py', 15,
     r'''            "word-break:break-all}.a{font-family:monospace;font-size:12px;color:#8a3b12;margin-top:3px;word-break:"
            "break-all}</style></head><body><h1>The path of every text</h1><p>Charted %s by text_path.py (%s): vision "
            "%s a page at the corpus price (a text with its own vision calls is priced from them; the dearest so far "
            "%s), translation %s a passage.</p>%s</body></html>"
            % (e(res["at"]), MARK, per_page(res["prices"]["vision_page"] or 0),
               per_page(res["prices"].get("vision_dear") or 0), "$%.5f" % res["prices"]["passage"], body))

''',
     r'''            "word-break:break-all}.a{font-family:monospace;font-size:12px;color:#8a3b12;margin-top:3px;word-break:"
            "break-all}</style></head><body><h1>The path of every text</h1><p>Charted %s by text_path.py (%s): vision "
            "%s a page at the corpus price (a text with its own vision calls is priced from them; the median so far "
            "%s, the dearest %s), translation %s a passage.</p>%s</body></html>"
            % (e(res["at"]), MARK, per_page(res["prices"]["vision_page"] or 0),
               per_page(res["prices"].get("vision_median") or 0) if res["prices"].get("vision_median") else "-",
               per_page(res["prices"].get("vision_dear") or 0), "$%.5f" % res["prices"]["passage"], body))

''')
edit('scripts/dashboard.py', 16,
     r'''                continue
            tt = tot.get(key) or {}
            hi = tt.get("cost_hi") or 0
            cost = ((" &middot; about %s now" % money(tt["cost"])) if tt.get("cost") else "") + (
                (" (up to %s at the dearest text's price)" % money(hi)) if tt.get("cost") and hi > 1.05 * tt["cost"] else "") + (
                (" &middot; then %s to translate" % money(tt["then"])) if tt.get("then") else "")
            chips += '<a class="pchip" href="#p-%s">%s <b>%d</b></a>' % (e(key, quote=True), e(label), len(rows))
''',
     r'''                continue
            tt = tot.get(key) or {}
            hi, lo = tt.get("cost_hi") or 0, tt.get("cost_lo")
            side = []   # MIRROR_CAP_2026_10_12: the median text's price beside the corpus's
            if tt.get("cost") and lo is not None and lo < 0.95 * tt["cost"]:
                side.append("from %s at the median text's price" % money(lo))
            if tt.get("cost") and hi > 1.05 * tt["cost"]:
                side.append("up to %s at the dearest text's price" % money(hi))
            cost = ((" &middot; about %s now" % money(tt["cost"])) if tt.get("cost") else "") + (
                (" (%s)" % "; ".join(side)) if side else "") + (
                (" &middot; then %s to translate" % money(tt["then"])) if tt.get("then") else "")
            chips += '<a class="pchip" href="#p-%s">%s <b>%d</b></a>' % (e(key, quote=True), e(label), len(rows))
''')
edit('scripts/dashboard.py', 17,
     r'''                                                                              e(desc), cost, trs))
        pr = res.get("prices") or {}
        head = ('Charted %s: vision %s a page at the corpus price (%d text(s) priced from their own calls; the dearest '
                'so far %s a page), translation %s a passage, measured in usage_log.'
                % (e(str(res.get("at", "?")).replace("T", " ")), "$%.4f" % (pr.get("vision_page") or 0),
                   len(pr.get("measured") or []), "$%.4f" % (pr.get("vision_dear") or 0), "$%.5f" % (pr.get("passage") or 0)))
    else:
        head = "Not charted yet: press Chart the path again, or run python scripts\\text_path.py (free, read-only)."
''',
     r'''                                                                              e(desc), cost, trs))
        pr = res.get("prices") or {}
        head = ('Charted %s: vision %s a page at the corpus price, its last 300 calls (%d text(s) priced from their own '
                'calls; the median %s, the dearest %s a page), translation %s a passage, measured in usage_log.'
                % (e(str(res.get("at", "?")).replace("T", " ")), "$%.4f" % (pr.get("vision_page") or 0),
                   len(pr.get("measured") or []),
                   ("$%.4f" % pr["vision_median"]) if pr.get("vision_median") else "-",   # MIRROR_CAP_2026_10_12
                   "$%.4f" % (pr.get("vision_dear") or 0), "$%.5f" % (pr.get("passage") or 0)))
    else:
        head = "Not charted yet: press Chart the path again, or run python scripts\\text_path.py (free, read-only)."
''')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_mirrorcap_" + stamp))
        t = p.with_name(p.name + ".tmp_mirrorcap"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database or on the site changed. The mirror's retire runs again at the next run:")
    print("  python scripts\\corpus_sync.py            (the plan)")
    print("  python scripts\\corpus_sync.py --apply")
    print("dashboard.py shows the median price on /path when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
