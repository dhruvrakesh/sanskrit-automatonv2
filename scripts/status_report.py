#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
status_report.py  (2026-10-04)  STATUS_REPORT_2026_10_04

READ-ONLY. One page that says where everything stands, written as Markdown:

    exports/status/STATUS_<yyyymmdd_HHMM>.md   and   exports/status/STATUS_latest.md

It gathers what is otherwise spread over six places:

  code        git HEAD of this repo (read from .git, no git command)
  prompts     the English / Hindi prompt versions a translate run would use now
  corpus      corpus_status verdicts and estimated spend per verdict (same code)
  brain       vectors, orphans, passages without a vector, STALE vectors (English
              re-translated after its vector was made), entity mentions
  images      the image library by status, per text
  spend       usage_log for the last 7 days, by kind
  operations  last maintenance ticks (SanskritMaintenance task log), newest backups
              (and any 0-byte backup file), DB size
  site        age of Srangam's generated status panel (src/data/projectStatus.ts),
              which is refreshed by block_BD_status.ps1 -Emit, not by this script

Nothing is written anywhere except the two Markdown files. Safe while jobs run.

  python scripts\\status_report.py
  python scripts\\status_report.py --no-drift --print
"""
from __future__ import annotations

import argparse
import datetime
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

MARK = "STATUS_REPORT_2026_10_04"
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))


def git_head(root: Path) -> str:
    g = root / ".git"
    try:
        head = (g / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:]
            p = g / ref
            if p.exists():
                return "%s %s" % (ref.split("/")[-1], p.read_text(encoding="utf-8").strip()[:8])
            packed = g / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(" " + ref):
                        return "%s %s" % (ref.split("/")[-1], line[:8])
            return ref
        return head[:8]
    except OSError:
        return "(no .git)"


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def tables(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def brain(con) -> dict:
    t = tables(con)
    q = lambda s, *a: con.execute(s, a).fetchone()[0]
    out = {}
    if "passage_embeddings" in t:
        out["vectors"] = q("SELECT COUNT(*) FROM passage_embeddings")
        out["orphan_vectors"] = q("SELECT COUNT(*) FROM passage_embeddings e LEFT JOIN passages p "
                                  "ON p.id = e.passage_id WHERE p.id IS NULL")
        out["no_vector"] = q("SELECT COUNT(*) FROM passages p LEFT JOIN passage_embeddings e ON e.passage_id = p.id "
                             "WHERE e.passage_id IS NULL AND TRIM(COALESCE(p.translation,'')) <> '' "
                             "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')")
        out["stale_vectors"] = q("SELECT COUNT(*) FROM passage_embeddings e JOIN passages p ON p.id = e.passage_id "
                                 "WHERE p.translated_at IS NOT NULL AND e.updated_at IS NOT NULL "
                                 "AND julianday(p.translated_at) > julianday(e.updated_at)")
    if "entity_mentions" in t:
        out["mentions"] = q("SELECT COUNT(*) FROM entity_mentions")
        out["orphan_mentions"] = q("SELECT COUNT(*) FROM entity_mentions m LEFT JOIN passages p "
                                   "ON p.id = m.passage_id WHERE p.id IS NULL")
    trig = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='trigger' "
                                      "AND name LIKE 'trg_passages_delete%'")]
    out["orphan_guard_triggers"] = len(trig)
    return out


def images(con) -> list:
    if "doc_images" not in tables(con):
        return []
    rows = con.execute("""SELECT d.code, i.status, COUNT(*) FROM doc_images i JOIN docs d ON d.id = i.doc_id
                          GROUP BY d.code, i.status ORDER BY d.code""").fetchall()
    by = {}
    for code, st, n in rows:
        by.setdefault(code, Counter())[st] = n
    return sorted(by.items())


def spend(con, days: int = 7) -> list:
    if "usage_log" not in tables(con):
        return []
    return con.execute("""SELECT kind, COUNT(*), ROUND(SUM(cost_usd), 4) FROM usage_log
                          WHERE ts >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?) GROUP BY kind
                          ORDER BY SUM(cost_usd) DESC""", ("-%d days" % days,)).fetchall()


def tail_maint(path: Path, n: int = 6) -> list:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    keep = [l for l in lines if l.startswith("[") and any(k in l for k in ("DONE", "SKIP", "FAIL", "START", "STEP"))]
    return keep[-n:]


def backups(folder: Path, n: int = 4) -> tuple[list, list]:
    if not folder.is_dir():
        return [], []
    files = sorted((p for p in folder.glob("context_*.db")), key=lambda p: p.stat().st_mtime, reverse=True)
    empty = [p.name for p in files if p.stat().st_size == 0]
    return [(p.name, p.stat().st_size, p.stat().st_mtime) for p in files[:n]], empty


def fmt_t(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def build(args) -> str:
    import corpus_status as cs
    now = datetime.datetime.now()
    L = ["# Status - %s" % now.strftime("%Y-%m-%d %H:%M"), "",
         "Generated by `scripts/status_report.py` (%s). Read-only; every number below was measured just now." % MARK, ""]
    L += ["## Code and prompts", "",
          "| | |", "|---|---|",
          "| Repo HEAD | `%s` |" % git_head(ROOT)]
    stats, (en_ver, hi_ver, hi_src), peers, cpp = cs.collect(
        args.db, None, Path(args.raw_dir), Path(args.vision_dir), Path(args.merged_dir), Path(args.inbox),
        not args.no_drift, args.min_passages)
    L += ["| English prompt | `%s` |" % en_ver, "| Hindi prompt | `%s` (%s) |" % (hi_ver, hi_src),
          "| Translation cost, measured | %s per passage |" % (("$%.5f" % cpp) if cpp else "?"), ""]
    by = {s["doc"]: s for s in stats}
    for s in stats:
        sd = s.get("src_doc")
        peer = (by.get(sd) or peers.get(sd)) if sd else None
        s["verdict"], s["reasons"], s["commands"] = cs.verdict(s, args.lacuna_ok, args.debris_ok, cpp,
                                                               {sd: peer} if peer else {})
    tally, usd = Counter(), Counter()
    for s in stats:
        tally[s["verdict"]] += 1
        usd[s["verdict"]] += s.get("est_usd", 0.0)
    L += ["## Corpus (%d texts with at least %d passages)" % (len(stats), args.min_passages), "",
          "| Verdict | Texts | Estimated spend to clear |", "|---|---|---|"]
    for k in sorted(tally, key=lambda k: cs.ORDER.get(k, 9)):
        L.append("| %s | %d | $%.2f |" % (k, tally[k], usd[k]))
    L += ["", "| Text | Verdict | Rows | Debris % | Vision % | English | Hindi | Hindi gaps % |",
          "|---|---|---|---|---|---|---|---|"]
    for s in sorted(stats, key=lambda s: (cs.ORDER.get(s["verdict"], 9), -s.get("passages", 0))):
        r = cs.row_for(s)
        L.append("| %s | %s | %d | %.1f | %.0f | %d | %d | %.1f |" % (
            r["doc"], r["verdict"], r["passages"], r["debris_pct"], r["vision_pct"], r["en_done"], r["hi_done"],
            r["hi_lac_pct"]))
    L += ["", "Next commands: `python scripts\\corpus_status.py --commands`", ""]

    con = open_ro(args.db)
    try:
        b = brain(con)
        L += ["## Context engine (semantic index and entity layer)", "", "| | |", "|---|---|"]
        for k, label in (("vectors", "Vectors"), ("no_vector", "Translated passages with no vector"),
                         ("stale_vectors", "Stale vectors (English re-translated after the vector)"),
                         ("orphan_vectors", "Orphaned vectors (passage deleted)"),
                         ("mentions", "Entity mentions"), ("orphan_mentions", "Orphaned mentions"),
                         ("orphan_guard_triggers", "Orphan-guard triggers installed (fix_orphans.py --guard)")):
            if k in b:
                L.append("| %s | %d |" % (label, b[k]))
        L += ["", "The SanskritMaintenance task (every 3 h, when the dashboard is idle) runs build_embeddings; "
              "with BRAIN_FRESH_2026_10_04 that also refreshes stale vectors.", ""]
        im = images(con)
        if im:
            L += ["## Image library", "", "| Text | Ideas | Approved ideas | Drawn, to review | Approved | Retired |",
                  "|---|---|---|---|---|---|"]
            for code, c in im:
                L.append("| %s | %d | %d | %d | %d | %d |" % (code, c["brief"], c["brief-approved"], c["draft"],
                                                         c["approved"], c["retired"]))
            L.append("")
        sp = spend(con)
        if sp:
            L += ["## Spend, last 7 days (usage_log; a lower bound)", "", "| Kind | Calls | USD |", "|---|---|---|"]
            for kind, n, usd_ in sp:
                L.append("| %s | %d | %.4f |" % (kind, n, usd_ or 0))
            L.append("")
    finally:
        con.close()

    L += ["## Operations", ""]
    try:
        L.append("- Database: `%s`, %.0f MB." % (args.db, Path(args.db).stat().st_size / 1e6))
    except OSError:
        pass
    bk, empty = backups(Path(args.backups))
    for name, size, mt in bk:
        L.append("- Backup `%s`, %.0f MB, %s." % (name, size / 1e6, fmt_t(mt)))
    for name in empty:
        L.append("- **0-byte backup file** `%s`: a backup that failed; it is not a backup." % name)
    mt = tail_maint(Path(args.maint_log))
    if mt:
        L += ["- Last maintenance ticks:", "", "```"] + mt + ["```"]
    ps = Path(args.srangam) / "src" / "data" / "projectStatus.ts"
    if ps.exists():
        age = (datetime.datetime.now().timestamp() - ps.stat().st_mtime) / 86400
        L += ["", "## Srangam site status panel", "",
              "`projectStatus.ts` was generated %s (%.0f day(s) ago). It is a generated file, refreshed by "
              "`block_BD_status.ps1 -Emit`, then committed and published through Lovable." % (fmt_t(ps.stat().st_mtime), age)]
        if age > 7:
            L.append("**Stale:** older than the weekly cadence in RUNBOOK 3h step 5.")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only one-page status, written as Markdown")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--backups", default=os.environ.get("SA_BACKUP_DIR", r"D:\backups"))
    ap.add_argument("--maint-log", default=os.environ.get("SA_MAINT_LOG", r"D:\backups\maintenance_log.txt"))
    ap.add_argument("--srangam", default=os.environ.get("SRANGAM_ROOT", r"D:\srangam-42267"))
    ap.add_argument("--out", default="exports/status")
    ap.add_argument("--lacuna-ok", type=float, default=5.0)
    ap.add_argument("--debris-ok", type=float, default=5.0)
    ap.add_argument("--min-passages", type=int, default=20)
    ap.add_argument("--no-drift", action="store_true")
    ap.add_argument("--print", dest="do_print", action="store_true")
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    md = build(args)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    (out / ("STATUS_%s.md" % stamp)).write_text(md, encoding="utf-8")
    (out / "STATUS_latest.md").write_text(md, encoding="utf-8")
    if args.do_print:
        print(md)
    print("wrote %s and %s" % (out / ("STATUS_%s.md" % stamp), out / "STATUS_latest.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
