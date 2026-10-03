#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
ocr_consensus.py  (2026-09-30)  OCR_CONSENSUS_2026_09_30

ONE idempotent command for the agreed OCR standard (RUNBOOK 3b, 3e, 3f):

    Tesseract on every page  ->  deterministic triage (confidence < threshold)
    ->  vision ONLY on the queued pages  ->  audit / repair the vision output
    ->  merge (vision is the source of record, Tesseract kept as the apparatus
        criticus and as the per-page fallback)  ->  DRIFT REPORT: which pages
        of the database are no longer the best reading we have on disk.

Before this script the chain existed only as five manual CLI steps, and
nothing told you when the database text had fallen behind the consensus. So
books other than Shatpatha were translated from raw Tesseract.

Every step is idempotent. Run it as often as you like:
  * triage is free and deterministic; the queue is rewritten each run
  * vision skips pages that already have a non-empty vision file
  * the repair audit is lossless (originals copied to _pre_repair first)
  * merge is deterministic and rewrites data/raw_merged/<doc>_NNNN.jsonl
  * the drift report is read-only against data/context.db

What it does NOT do: it never touches the database. Re-ingest stays an
explicit, backed-up step (the script prints the exact commands). That is
deliberate: wipe + re-ingest must happen while the dashboard is idle.

Why re-translation after re-ingest is cheap: infer_mt's cache key is
sha256(prompt_version + source text). A page whose text did not change
(Tesseract-accepted, or vision identical) is answered from mt_cache at zero
cost. Only passages whose source text actually changed make an API call. The
cache IS the change detector for translation.

  python scripts\\ocr_consensus.py --doc Mallapurana             # PLAN: no API, no writes except the plan files
  python scripts\\ocr_consensus.py --doc Mallapurana --yes       # run vision (metered), repair, merge --apply
  python scripts\\ocr_consensus.py --doc Mallapurana --drift-only

Plan files (safe to delete): data/ocr_consensus/<doc>_queue.txt,
<doc>_redo.txt, <doc>.json (the manifest: per page engine, sha256, similarity
to the DB text, status).
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

MARK = "OCR_CONSENSUS_2026_09_30"
PY = sys.executable
SCRIPTS = Path(__file__).resolve().parent
COST_PER_PAGE_MEASURED = 0.00028   # measured 2026-09-30 on Mallapurana_0010 (ocr_vision printed it)
DEV_WORD = re.compile(r"[\u0900-\u0963\u0970-\u097f]+")
STALE_BELOW = 0.92                 # token-sequence similarity DB page vs consensus page


# ---------------------------------------------------------------- pure helpers
def page_map(folder: Path, doc: str, ext: str) -> dict[str, Path]:
    """{'0082': path} for <doc>_NNNN.<ext> (and _NNNN_norm.jsonl) in folder."""
    rx = re.compile(r"^%s_(\d{4})(?:_norm)?\.%s$" % (re.escape(doc), re.escape(ext)))
    out: dict[str, Path] = {}
    if folder.is_dir():
        for p in sorted(folder.iterdir()):
            m = rx.match(p.name)
            if m:
                out.setdefault(m.group(1), p)
    return out


def nonempty_jsonl(p: Path) -> bool:
    try:
        with open(p, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return bool(line and (json.loads(line).get("text") or "").strip())
    except Exception:
        return False


def plan_vision(queue_lines: list[str], vision_dir: Path) -> tuple[list[str], list[str]]:
    """Split the queue into (todo, done). Done = a non-empty vision file exists."""
    todo, done = [], []
    for q in queue_lines:
        q = q.strip()
        if not q:
            continue
        stem = Path(q.replace("\\", "/")).stem
        (done if nonempty_jsonl(vision_dir / (stem + ".jsonl")) else todo).append(q)
    return todo, done


def dev_tokens(t: str) -> list[str]:
    return [w for w in DEV_WORD.findall(t or "") if len(w) >= 3]


_NORM = None


def ingest_view(text: str) -> str:
    """OCR_CONSENSUS_NORM_2026_10_02: the text exactly as ingest stores it.
    ingest_jsonl_fast.py runs normalize_sanskrit() before segmenting, and that
    joins words hyphenated across line breaks (`jatu-\\n karnya` -> one word). The
    first drift report compared the RAW consensus text, so every line-wrapped
    prose page (Shatapatha) looked 'stale' at 0.81-0.89 while its DB text was in
    fact byte-for-byte what ingest would write today (verified on pages 0001,
    0093, 0164, 0225, 0291: token counts 17/144/26/99/102 equal the DB's)."""
    global _NORM
    if _NORM is None:
        try:
            sys.path.insert(0, str(SCRIPTS))
            from normalize_text import normalize_sanskrit as _n
            _NORM = _n
        except Exception:
            print("  [warn] normalize_text not importable; using the line-break rule only")
            _NORM = lambda t: re.sub(r"-\s*\n\s*", "", t or "")
    return _NORM(text or "")


def similarity(a: str, b: str) -> float:
    ta, tb = dev_tokens(a), dev_tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()


def read_rec(p: Path) -> dict:
    try:
        with open(p, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return json.loads(line) if line else {}
    except Exception:
        return {}


# ------------------------------------------------------------------- effects
def run(argv: list[str]) -> int:
    print("  $ " + " ".join('"%s"' % a if " " in a else a for a in argv), flush=True)
    return subprocess.call(argv)


def dashboard_jobs(doc: str) -> list[dict] | None:
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never via a proxy
        with opener.open("http://127.0.0.1:5057/api/jobs/running", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [j for j in data.get("running", []) if j.get("doc") == doc]
    except Exception:
        return None


def drift(db: Path, doc: str, merged: dict[str, Path]) -> list[dict]:
    uri = db.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.execute("PRAGMA query_only=1")
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    eng_col = "p.ocr_engine" if "ocr_engine" in cols else "NULL"
    db_pages: dict[int, list] = {}
    for page_no, text, eng in con.execute(
            f"""SELECT p.page_no, p.text, {eng_col} FROM passages p JOIN docs d ON d.id=p.doc_id
                WHERE d.code=? ORDER BY p.page_no, p.idx""", (doc,)):
        db_pages.setdefault(page_no, [[], set()])
        db_pages[page_no][0].append(text or "")
        if eng:
            db_pages[page_no][1].add(eng)
    con.close()
    rows = []
    for pg, path in sorted(merged.items()):
        rec = read_rec(path)
        text = rec.get("text") or ""
        n = int(pg)
        entry = {"page": pg, "consensus_engine": rec.get("engine"),
                 "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                 "variants": len(((rec.get("meta") or {}).get("variants")) or [])}
        if n not in db_pages:
            entry.update(similarity=None, db_engine=None, status="missing-in-db")
        else:
            s = similarity("\n".join(db_pages[n][0]), ingest_view(text))
            entry.update(similarity=round(s, 3), db_engine=",".join(sorted(db_pages[n][1])) or None,
                         status="current" if s >= STALE_BELOW else "stale")
        rows.append(entry)
    return rows


def explain(db: Path, doc: str, page: str, merged_path: Path, n_ops: int = 15) -> dict:
    """OCR_CONSENSUS_EXPLAIN_2026_10_01 - read-only. Why is this page stale?
    Prints the DB rows for the page (idx, text_type, engine, tokens) and the
    word-level differences between the DB text and the consensus text."""
    uri = db.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.execute("PRAGMA query_only=1")
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    tt = "p.text_type" if "text_type" in cols else "NULL"
    eng = "p.ocr_engine" if "ocr_engine" in cols else "NULL"
    rows = con.execute(f"""SELECT p.idx, {tt}, {eng}, p.text FROM passages p JOIN docs d ON d.id=p.doc_id
                           WHERE d.code=? AND p.page_no=? ORDER BY p.idx""", (doc, int(page))).fetchall()
    con.close()
    cons = ingest_view(read_rec(merged_path).get("text") or "")   # compare what ingest would store
    db_all = "\n".join(r[3] or "" for r in rows)
    db_main = "\n".join(r[3] or "" for r in rows if (r[1] or "mula") not in ("noise", "frontmatter"))
    ta, tb = dev_tokens(db_all), dev_tokens(cons)
    res = {"page": page, "db_rows": len(rows), "db_tokens": len(ta), "consensus_tokens": len(tb),
           "sim_all_rows": round(similarity(db_all, cons), 3),
           "sim_without_noise_frontmatter": round(similarity(db_main, cons), 3),
           "text_types": {}, "ops": []}
    for r in rows:
        k = r[1] or "(none)"
        res["text_types"][k] = res["text_types"].get(k, 0) + 1
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        res["ops"].append({"op": tag, "db": " ".join(ta[i1:i2][:12]), "db_n": i2 - i1,
                           "consensus": " ".join(tb[j1:j2][:12]), "cons_n": j2 - j1})
    big = sorted(res["ops"], key=lambda o: -(o["db_n"] + o["cons_n"]))[:n_ops]
    print("  page %s: %d DB rows %s | tokens DB %d vs consensus %d" % (
        page, len(rows), res["text_types"], len(ta), len(tb)))
    print("  similarity: all rows %.3f | without noise/frontmatter rows %.3f" % (
        res["sim_all_rows"], res["sim_without_noise_frontmatter"]))
    n = {"insert": 0, "delete": 0, "replace": 0}
    for o in res["ops"]:
        n[o["op"]] += 1
    print("  diff blocks: only-in-consensus %(insert)d | only-in-DB %(delete)d | changed %(replace)d" % n)
    for o in big:
        print("   [%s] DB(%d): %s" % (o["op"], o["db_n"], o["db"]))
        print("   %s  CONS(%d): %s" % (" " * len(o["op"]), o["cons_n"], o["consensus"]))
    return res


def reingest_commands(doc: str) -> str:
    stamp = "$(Get-Date -Format yyyyMMdd_HHmmss)"
    return "\n".join([
        '# --- only when the dashboard header reads "idle" (RUNBOOK 1). Backup first. ---',
        'python scripts\\db_backup.py "data\\context.db" "D:\\backups\\context_pre_consensus_%s_%s.db"' % (doc, stamp),
        "python scripts\\wipe_doc.py --db data\\context.db --doc %s --dry-run" % doc,
        "python scripts\\wipe_doc.py --db data\\context.db --doc %s --yes" % doc,
        'python scripts\\ingest_jsonl_fast.py --doc %s --glob "data\\raw_merged\\%s_*.jsonl" --db data\\context.db' % (doc, doc),
        "python scripts\\classify_frontmatter.py --doc %s          # preview, then add --apply" % doc,
        "python scripts\\classify_noise.py --doc %s --show         # preview, then --apply" % doc,
        "python scripts\\translate_passages.py --db data\\context.db --doc %s --engine gemini:gemini-2.5-flash" % doc,
        "python scripts\\qa_scan.py --db data\\context.db --doc %s --lang en --write" % doc,
        "python scripts\\translate_passages.py --db data\\context.db --doc %s --lang hi --engine gemini:gemini-2.5-flash" % doc,
        "python scripts\\measure_lacunae.py --doc %s" % doc,
        "python scripts\\ocr_consensus.py --doc %s --drift-only     # expect: 0 stale" % doc,
    ])


# ---------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="Idempotent OCR consensus for one doc (no DB writes)")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--tesseract-dir", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--threshold", type=float, default=72.0)
    ap.add_argument("--include-unassessed", action="store_true",
                    help="also vision pages whose Tesseract output carries no confidence")
    ap.add_argument("--max-usd", type=float, default=1.00, help="refuse the vision step above this estimate")
    ap.add_argument("--max-pages", type=int, default=0, help="cap vision pages this run (0 = no cap)")
    ap.add_argument("--model", default=None, help="passed to ocr_vision.py --model")
    ap.add_argument("--yes", action="store_true", help="spend (vision) and write (repair, merge)")
    ap.add_argument("--drift-only", action="store_true")
    ap.add_argument("--explain", default=None,
                    help="comma-separated page numbers (e.g. 0291,0164): show why each is stale; read-only, implies --drift-only")
    args = ap.parse_args()
    if args.explain:
        args.drift_only = True

    doc = args.doc
    if not re.match(r"^[A-Za-z0-9_\-]+$", doc):
        print("FAIL: unexpected characters in doc code.")
        return 2
    if not Path("scripts").is_dir():
        print("FAIL: run from the repo root.")
        return 2
    work = Path("data/ocr_consensus"); work.mkdir(parents=True, exist_ok=True)
    tdir, vdir, mdir = Path(args.tesseract_dir), Path(args.vision_dir), Path(args.merged_dir)
    mode = "RUN" if args.yes else ("DRIFT ONLY" if args.drift_only else "PLAN (no spend, no merge writes)")
    print("=" * 74)
    print("OCR CONSENSUS  %s   %s   %s" % (doc, mode, MARK))
    print("=" * 74)

    jobs = dashboard_jobs(doc)
    if jobs is None:
        print("  dashboard      : not reachable on 127.0.0.1:5057 (fine for file steps)")
    elif jobs:
        print("  dashboard      : %d job(s) running for %s: %s" % (
            len(jobs), doc, ", ".join("%s(%s)" % (j["kind"], j["state"]) for j in jobs)))
        if args.yes:
            print("  REFUSING: stop them first (a running ingest/translate reads these files).")
            return 1
    else:
        print("  dashboard      : reachable, no jobs for %s" % doc)

    inbox = page_map(Path(args.inbox), doc, "pdf")
    tess = page_map(tdir, doc, "jsonl")
    print("  inbox pages    : %d" % len(inbox))
    print("  tesseract pages: %d%s" % (len(tess), "" if len(tess) >= len(inbox) else
          "   (%d missing - run OCR from the dashboard first)" % (len(inbox) - len(tess))))

    if not args.drift_only:
        # 1. TRIAGE (free, deterministic)
        print("\n[1] triage  (confidence < %.0f)" % args.threshold)
        q = work / ("%s_queue.txt" % doc)
        if q.exists():
            q.unlink()
        rc = run([PY, str(SCRIPTS / "ocr_triage.py"), "--doc", doc, "--threshold", str(args.threshold),
                  "--tesseract-dir", str(tdir), "--vision-dir", str(vdir), "--write-queue", "--queue", str(q)])
        queue = q.read_text(encoding="utf-8").splitlines() if q.exists() else []
        if rc != 0 and not args.include_unassessed:
            print("  triage failed (rc %d). With no confidence recorded, re-run Tesseract, or pass"
                  " --include-unassessed to vision every page." % rc)
            return 1
        if args.include_unassessed:
            assessed = {Path(x.replace("\\", "/")).stem for x in queue}
            for pg, p in tess.items():
                rec = read_rec(p)
                if (rec.get("meta") or {}).get("conf_mean") is None:
                    stem = "%s_%s" % (doc, pg)
                    if stem not in assessed and pg in inbox:
                        queue.append(os.path.join(args.inbox, stem + ".pdf"))
        # 2. VISION (metered, skip-existing)
        todo, done = plan_vision(queue, vdir)
        if args.max_pages and len(todo) > args.max_pages:
            todo = todo[:args.max_pages]
        est = len(todo) * COST_PER_PAGE_MEASURED
        print("\n[2] vision    queued %d | already done %d | to run %d | est $%.4f at $%.5f/page"
              % (len(queue), len(done), len(todo), est, COST_PER_PAGE_MEASURED))
        if todo and args.yes:
            if est > args.max_usd:
                print("  REFUSING: estimate $%.4f exceeds --max-usd %.4f" % (est, args.max_usd))
                return 1
            vdir.mkdir(parents=True, exist_ok=True)
            fails = consec = 0
            for i, pdf in enumerate(todo, 1):
                stem = Path(pdf.replace("\\", "/")).stem
                argv = [PY, str(SCRIPTS / "ocr_vision.py"), "--pdf", pdf, "--out", str(vdir / (stem + ".jsonl")),
                        "--doc", doc, "--yes"] + (["--model", args.model] if args.model else [])
                print("  (%d/%d)" % (i, len(todo)))
                if run(argv) != 0 or not nonempty_jsonl(vdir / (stem + ".jsonl")):
                    fails += 1; consec += 1
                    if consec >= 5:
                        print("  STOPPING: 5 consecutive vision failures (quota or key?). Re-run later; done pages are kept.")
                        break
                else:
                    consec = 0
            print("  vision failures: %d" % fails)
        # 3. AUDIT / REPAIR (lossless) with one redo round
        vis = page_map(vdir, doc, "jsonl")
        if vis:
            print("\n[3] audit     %d vision page(s)" % len(vis))
            redo = work / ("%s_redo.txt" % doc)
            base = [PY, str(SCRIPTS / "repair_vision_jsonl.py"), "--glob", str(vdir / ("%s_*.jsonl" % doc)),
                    "--redo-list", str(redo), "--tesseract-dir", str(tdir)]
            rc = run(base + (["--apply"] if args.yes else []))
            if rc != 0 and args.yes and redo.exists():
                rej = vdir / "_rejected"; rej.mkdir(exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                for pdf in [l.strip() for l in redo.read_text(encoding="utf-8").splitlines() if l.strip()]:
                    stem = Path(pdf.replace("\\", "/")).stem
                    if not stem.startswith(doc + "_"):
                        continue
                    old = vdir / (stem + ".jsonl")
                    if old.exists():
                        shutil.move(str(old), str(rej / ("%s.%s.jsonl" % (stem, ts))))
                    run([PY, str(SCRIPTS / "ocr_vision.py"), "--pdf", pdf, "--out", str(old), "--doc", doc, "--yes"]
                        + (["--model", args.model] if args.model else []))
                rc = run(base + ["--apply"])
            if rc != 0:
                print("  audit still reports damaged pages; merge falls back to Tesseract for them (verdict()).")
        else:
            print("\n[3] audit     no vision pages for %s - merge will use Tesseract for every page" % doc)
        # 4. MERGE (deterministic)
        print("\n[4] merge")
        rc = run([PY, str(SCRIPTS / "merge_ocr_sources.py"), "--doc", doc, "--vision-dir", str(vdir),
                  "--tesseract-dir", str(tdir), "--outdir", str(mdir)] + (["--apply"] if args.yes else []))
        if rc != 0:
            print("  merge failed (rc %d)" % rc)
            return 1

    # 5. DRIFT (read-only)
    merged = page_map(mdir, doc, "jsonl")
    print("\n[5] drift     consensus pages on disk: %d" % len(merged))
    if not merged:
        print("  nothing merged yet%s." % ("" if args.yes else " (a PLAN run does not write data/raw_merged; re-run with --yes)"))
        return 0
    if not Path(args.db).exists():
        print("  %s not found; skipping drift." % args.db)
        return 0
    if args.explain:
        out = []
        for pg in [x.strip().zfill(4) for x in args.explain.split(",") if x.strip()]:
            if pg not in merged:
                print("  page %s: no consensus file" % pg)
                continue
            out.append(explain(Path(args.db), doc, pg, merged[pg]))
        ex = work / ("%s_explain.json" % doc)
        ex.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  full diff: %s" % ex)
        return 0
    rows = drift(Path(args.db), doc, merged)
    st = {k: sum(1 for r in rows if r["status"] == k) for k in ("current", "stale", "missing-in-db")}
    by_eng: dict[str, int] = {}
    for r in rows:
        if r["status"] != "current":
            by_eng[r["consensus_engine"] or "?"] = by_eng.get(r["consensus_engine"] or "?", 0) + 1
    print("  current %(current)d | stale %(stale)d | missing-in-db %(missing-in-db)d" % st)
    if by_eng:
        print("  not-current pages by consensus engine: " + ", ".join("%s %d" % kv for kv in sorted(by_eng.items())))
    worst = sorted([r for r in rows if r["similarity"] is not None], key=lambda r: r["similarity"])[:10]
    if worst:
        print("  lowest similarity (page: sim db_engine -> consensus_engine):")
        for r in worst:
            print("    %s: %.3f  %s -> %s" % (r["page"], r["similarity"], r["db_engine"], r["consensus_engine"]))
    man = work / ("%s.json" % doc)
    man.write_text(json.dumps({"doc": doc, "marker": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"),
                               "stale_below": STALE_BELOW, "summary": st, "pages": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("  manifest: %s" % man)
    if st["stale"] or st["missing-in-db"]:
        print("\nThe database is behind the consensus for %s. To bring it up to date:\n" % doc)
        print(reingest_commands(doc))
        return 3
    print("\nDatabase text matches the consensus. Nothing to re-ingest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
