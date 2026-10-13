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


def refused(p: Path) -> bool:
    """CONSENSUS_REFUSED_2026_10_03: the vision file records that the provider refused
    the page (finish RECITATION or SAFETY). Retrying costs a call and changes nothing."""
    try:
        with open(p, encoding="utf-8") as f:
            rec = json.loads(next((l for l in f if l.strip()), "{}"))
        return ((rec.get("meta") or {}).get("finish") in ("RECITATION", "SAFETY")
                and not (rec.get("text") or "").strip())
    except Exception:
        return False


def measured_cost_per_page(db, fallback: float = 0.0015, doc: str | None = None) -> float:
    """USD per DELIVERED vision page, from usage_log, repriced with cost_tracker's table.

    COST_RATIO_2026_10_05: total cost of the calls / pages they delivered (a ratio of
    sums). The mean and median used before (SPEND_TRUTH, CREDITS_COST) counted only
    rows with passages > 0, and so left out the ladder attempts that ocr_vision meters
    with units=0 - which are billed. On 2026-10-03/04: 93 such calls cost $1.08 of
    $3.02 (36%), almost all on Rgveda. Pages differ by book too (Rgveda $0.00646 a
    page, Mallapurana $0.00115), so with doc= a text that already has >= 20 delivered
    pages is priced from its own last 600 calls; otherwise the last 300 calls
    corpus-wide are used."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import cost_tracker
        uri = Path(db).resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            base = ("SELECT engine, in_tokens, out_tokens, passages FROM usage_log "
                    "WHERE kind='ocr_vision' AND token_source='provider'")
            rows = []
            if doc:
                rows = con.execute(base + " AND doc=? ORDER BY id DESC LIMIT 600", (doc,)).fetchall()
                if sum((r[3] or 0) for r in rows) < 20:
                    rows = []
            if not rows:
                rows = con.execute(base + " ORDER BY id DESC LIMIT 300").fetchall()
        finally:
            con.close()
        usd = pages = 0.0
        for eng, tin, tout, n in rows:
            pin, pout = cost_tracker._get_pricing(eng or "")
            usd += ((tin or 0) * pin + (tout or 0) * pout) / 1e6
            pages += max(0, n or 0)
        return (usd / pages) if (pages >= 5 and usd > 0) else fallback
    except Exception:
        return fallback


def gave_up(p: Path) -> bool:
    """SPEND_TRUTH_2026_10_04: an EMPTY vision file that already had >= 2 retries is a
    blank or unreadable page; re-sending it every run only bills it again."""
    try:
        with open(p, encoding="utf-8") as f:
            rec = json.loads(next((l for l in f if l.strip()), "{}"))
        return (not (rec.get("text") or "").strip()) and int((rec.get("meta") or {}).get("retries") or 0) >= 2
    except Exception:
        return False


def plan_vision(queue_lines: list[str], vision_dir: Path, retry_refused: bool = False):
    """Split the queue into (todo, done). Done = a non-empty vision file exists, or the
    provider refused the page before (unless retry_refused) - merge keeps Tesseract."""
    todo, done = [], []
    for q in queue_lines:
        q = q.strip()
        if not q:
            continue
        stem = Path(q.replace("\\", "/")).stem
        vf = vision_dir / (stem + ".jsonl")
        ok = nonempty_jsonl(vf) or (not retry_refused and (refused(vf) or gave_up(vf)))   # SPEND_TRUTH_2026_10_04
        (done if ok else todo).append(q)
    return todo, done


# PATH_2026_10_12: the pages vision failed on. On 12 Oct the Natyasastra's repair (278 pages to read, $3.08) read
# none: its queue began with five pages vision had failed on the night before (0026, 0032, 0038, 0040, 0044), they
# failed again, and five failures in a row stopped the run as "quota or key?" - after about half an hour of billed
# retries. A page vision fails on is now written down (data/ocr_consensus/<doc>_vision_failed.json); it is tried
# after the others, its failures do not stop a run, and after VISION_GIVE_UP failed runs it is left to Tesseract
# (--retry-refused tries it again). The spend cap is asked before each page: a cap reached stops the run as such.
# The ledger is new: a page below the last page vision read that has no reading failed before (the runs go in page
# order), and is written down once on the first run, so the Natyasastra's 24 such pages (below page 292) go last.
VISION_GIVE_UP = 2


def failed_ledger(work: Path, doc: str) -> Path:
    return work / ("%s_vision_failed.json" % doc)


def read_failed(work: Path, doc: str) -> dict:
    try:
        d = json.loads(failed_ledger(work, doc).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def write_failed(work: Path, doc: str, led: dict) -> None:
    p = failed_ledger(work, doc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(led, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def last_read_page(vdir: Path, doc: str) -> int:
    """The highest page vision has read for this text (0 when none)."""
    rx = re.compile(r"^%s_(\d{4})\.jsonl$" % re.escape(doc))
    pages = []
    try:
        for e in os.scandir(vdir):
            m = rx.match(e.name)
            if m:
                pages.append(int(m.group(1)))
    except OSError:
        return 0
    for pg in sorted(pages, reverse=True):
        if nonempty_jsonl(vdir / ("%s_%04d.jsonl" % (doc, pg))):
            return pg
    return 0


def seed_failed(todo: list, led: dict, last_read: int) -> int:
    """A page to read below the last page vision read, and not in the ledger, was tried before and failed: it is
    written down once (fails 1), so it goes after the others. -> how many were written down."""
    n = 0
    for q in todo:
        stem = Path(q.replace("\\", "/")).stem
        tail = stem[-4:]
        if stem not in led and tail.isdigit() and int(tail) < last_read:
            led[stem] = {"fails": 1, "last": "", "inferred": "no reading below page %d" % last_read}
            n += 1
    return n


def order_vision(todo: list, led: dict, retry: bool = False):
    """(the pages to read: never failed first, then those that failed before; the pages left to Tesseract)."""
    fresh, again, skipped = [], [], []
    for q in todo:
        n = int((led.get(Path(q.replace("\\", "/")).stem) or {}).get("fails") or 0)
        if n >= VISION_GIVE_UP and not retry:
            skipped.append(q)
        else:
            (again if n else fresh).append(q)
    return fresh + again, skipped


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
    stopped = ""
    for i, pdf in enumerate(todo, 1):
        stem = Path(pdf.replace("\\", "/")).stem
        if budget is not None and not budget():
            stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        why = cap() if cap is not None else ""
        if why:
            stopped = why
            break
        before = int((led.get(stem) or {}).get("fails") or 0)
        out = vdir / (stem + ".jsonl")
        argv = [PY, str(SCRIPTS / "ocr_vision.py"), "--pdf", pdf, "--out", str(out), "--doc", doc, "--yes"] + (
            ["--model", model] if model else [])
        print("  (%d/%d)%s" % (i, len(todo), ("  (vision failed on it %d time(s) before)" % before) if before else ""))
        if runner(argv) != 0 or not nonempty_jsonl(out):
            if budget is not None and not budget():   # ocr_vision.py refused it for the cap: not the page's fault
                stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
            fails += 1
            led[stem] = {"fails": before + 1, "last": datetime.datetime.now().isoformat(timespec="seconds")}
            if not before:
                consec += 1
                if consec >= 5:
                    stopped = "5 vision failures in a row on pages never failed before (quota or key?)"
                    break
        else:
            ok += 1
            consec = 0
            led.pop(stem, None)
    return ok, fails, stopped


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
        # REPAIR_HEAL_2026_10_11: repair_text.py runs this as the dashboard's own job (kind "repair"); it names
        # its kind here, so the job that asked for the repair is not taken for one in its way
        skip = {k.strip() for k in os.environ.get("SA_CONSENSUS_SELF_KIND", "").split(",") if k.strip()}
        return [j for j in data.get("running", []) if j.get("doc") == doc and j.get("kind") not in skip]
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
        if rec.get("engine") == "blank" and not text.strip():
            # QUALITY_2026_10_11: a blank page (a plate): current when the database has nothing for it; stale when it
            # still has Tesseract's garbage of the picture
            entry.update(similarity=None, db_engine=(",".join(sorted(db_pages[n][1])) or None) if n in db_pages else None,
                         status="stale" if n in db_pages else "current")
        elif n not in db_pages:
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
        # READ_IN_2026_10_13: the changed pages only, in place (REINGEST_2026_10_12) come first; the whole text again
        # (below) deletes every translation, vector and review of the text
        "# --- the changed pages only: the unchanged passages keep their translations, vectors and reviews ---",
        "python scripts\\reingest_pages.py --doc %s                  # the plan, free" % doc,
        "python scripts\\reingest_pages.py --doc %s --apply          # a backup first; it asks for --replace N "
        "if it removes English" % doc,
        "python scripts\\ocr_consensus.py --doc %s --drift-only     # expect: 0 stale" % doc,
        "# --- or the whole text again: its translations, vectors and reviews are deleted ---",
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
    ap.add_argument("--retry-refused", action="store_true",
                    help="also re-send pages the provider refused (RECITATION/SAFETY) before")
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
        todo, done = plan_vision(queue, vdir, args.retry_refused)
        led = read_failed(work, doc)   # PATH_2026_10_12
        seeded = seed_failed(todo, led, last_read_page(vdir, doc))
        if seeded:
            print("  %d page(s) below the last page vision read have no reading: vision failed on them before, so they "
                  "go after the others" % seeded)
        todo, gave = order_vision(todo, led, args.retry_refused)
        if gave:
            print("  %d page(s) left to Tesseract: vision failed on them in %d runs or more (%s). --retry-refused to "
                  "try again." % (len(gave), VISION_GIVE_UP, ", ".join(Path(x.replace("\\", "/")).stem[-4:] for x in gave[:12])))
        n_ref = sum(1 for q in done if refused(vdir / (Path(q.replace("\\", "/")).stem + ".jsonl")))
        if n_ref:
            print("  %d page(s) skipped: the provider refused them before (RECITATION/SAFETY); "
                  "Tesseract is kept. --retry-refused to try again." % n_ref)
        if args.max_pages and len(todo) > args.max_pages:
            todo = todo[:args.max_pages]
        _mark = usage_mark(args.db)   # MIRROR_CAP_2026_10_12: what this run spends comes after it
        cpp = measured_cost_per_page(args.db, doc=doc)   # COST_RATIO_2026_10_05: this text's own rate
        est = len(todo) * cpp
        print("\n[2] vision    queued %d | already done %d | to run %d | est $%.4f at $%.5f/page"
              % (len(queue), len(done), len(todo), est, cpp))
        if todo and args.yes:
            if est > args.max_usd:
                print("  REFUSING: estimate $%.4f exceeds --max-usd %.4f" % (est, args.max_usd))
                return 1
            vdir.mkdir(parents=True, exist_ok=True)
            try:   # PATH_2026_10_12: the cap is asked before each page
                import usage_meter as _um
                _budget = lambda: _um.budget_ok(args.db)
            except Exception:
                _budget = None
            _cap = run_cap(args.db, doc, args.max_usd, cpp, _mark)   # MIRROR_CAP_2026_10_12
            try:
                n_ok, fails, stopped = run_vision(todo, vdir, doc, led, args.model, _budget, cap=_cap)
            finally:
                write_failed(work, doc, led)
            if stopped:
                print("  STOPPING: %s. Re-run later; done pages are kept." % stopped)
            print("  vision: %d page(s) read, %d failed%s" % (n_ok, fails, (" (written down in %s: tried last next "
                  "time, left to Tesseract after %d failed runs)" % (failed_ledger(work, doc), VISION_GIVE_UP)) if fails else ""))
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
                    why = run_cap(args.db, doc, args.max_usd, measured_cost_per_page(args.db, doc=doc), _mark)()
                    if why:   # MIRROR_CAP_2026_10_12: the redo round is under the same --max-usd
                        print("  STOPPING the redo round: %s. The pages not redone keep their reading." % why)
                        break
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
