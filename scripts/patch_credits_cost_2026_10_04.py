#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_credits_cost_2026_10_04.py  (2026-10-04)  CREDITS_COST_2026_10_04

Five measured problems, five surgical fixes.

1. PREPAID CREDITS. data/jobs.jsonl, 2026-10-04 10:55 UTC: two images_gen jobs
   failed with "HTTP 402 ... Your prepayment credits are depleted. Please go to
   AI Studio". The Gemini key draws on PREPAID credit, so the account itself
   stops all spending when the credit runs out. The pipeline did not recognise
   that answer:
     infer_mt.py treated it as an ordinary error: three short retries per verse,
     then an EMPTY translation, verse after verse, for the rest of the run (the
     exact failure its own comment warns about for quota errors).
   Now a 402 / "prepayment credits are depleted" raises CreditsDepleted, a
   QuotaExhausted, so translate_passages aborts the run at once with the reason
   ("[ABORT] ..."), the same path the budget cap and quota errors already use.
   (ocr_consensus already stops after 5 consecutive vision failures;
   extract_entities, images and embeddings already stop on a non-transient
   error.)
2. DEAD FALLBACK MODEL. The MAX_TOKENS ladder's default fallback is
   gemini-2.0-flash. The key's model list (list_models, 2026-10-04 19:49) does
   not contain it, so that rung always failed (no cost, but no recovery either).
   The default is now gemini-2.5-flash-lite, which the list does contain.
   MT_FALLBACK_MODEL in .env still overrides it. cost_tracker has no 2.5
   Flash-Lite row, so its calls are priced as 2.5 Flash (substring match): the
   ledger reads high there, which is the safe direction.
3. VISION ESTIMATE: MEDIAN -> MEAN. ocr_consensus.measured_cost_per_page() took
   the MEDIAN of the last 300 metered pages. A total is n x MEAN, not n x median,
   and page cost is right-skewed. Measured on the 17:58 backup (repriced):
   median $0.00282, mean $0.00313, p90 $0.00350, max $0.04282 per page; all
   provider-metered vision since metering began: $0.00407 per page delivered
   (1,278 calls for 1,086 pages - retries cost too). It now returns the mean.
   corpus_status uses the same function, so its --max-usd stays in step.
   corpus_status's fallback (used only with fewer than 5 measured pages) was
   $0.0054; that figure was wrong (it is not what the ledger shows). It is now
   $0.0041, the all-time per-page figure above.
4. SHELF. Screenshots, 2026-10-04 19:41/19:44:
     - the "N ed." badge covers the series number ("EIGHTEEN SMRTIS . 1" reads
       "EIGHTEEN SMRTIS 1 ed.");
     - two books in one collection can carry the same title (Shiva Dhanur Veda
       x2, Vasishtha Dhanur Veda x2 - different documents, diag_retire_check
       NOT SAFE for retirement), and the shelf gave no way to tell them apart.
   Now the typographic cover keeps its bottom line clear of the badge, and when
   a title repeats inside a collection each copy shows its document code.
5. BACKUP READS. diag_orphans.py --db <backup> opened the file mode=ro. On a
   WAL-mode file that leaves -wal (0 bytes) and -shm files beside it - seen
   beside context_pre_orphanfix_20261004_171631.db after a read on 2026-10-04.
   New --backup flag opens immutable=1 (no sidecars) and refuses the live DB.

All-or-nothing, marker-idempotent, backups (.bak_credits_<date>), py_compile on
.py files, atomic replace.

  python scripts/patch_credits_cost_2026_10_04.py --check
  python scripts/patch_credits_cost_2026_10_04.py
Test: python -m unittest tests.test_credits_cost_2026_10_04 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "CREDITS_COST_2026_10_04"

MT_EDITS = [
    ("CreditsDepleted class",
     '''class BudgetBlocked(QuotaExhausted):
''',
     '''class CreditsDepleted(QuotaExhausted):
    """CREDITS_COST_2026_10_04. The provider answered HTTP 402 "Your prepayment
    credits are depleted". Not transient: every further call gets the same
    answer. As a QuotaExhausted it aborts the run with the reason."""
    pass


def _credits_depleted(err: str) -> bool:
    """CREDITS_COST_2026_10_04: True for the prepaid-credit 402, never for a page number."""
    low = (err or "").lower()
    if "prepayment" in low or "credits are depleted" in low:
        return True
    return bool(re.search(r"\\b402\\b", err or "")) and any(w in low for w in ("payment", "credit", "billing"))


class BudgetBlocked(QuotaExhausted):
''', 1),
    ("abort on 402",
     '''            except Exception as exc:
                err_str = str(exc)
                low = err_str.lower()
''',
     '''            except Exception as exc:
                err_str = str(exc)
                low = err_str.lower()
                # CREDITS_COST_2026_10_04: prepaid credit exhausted -> stop the run now, send nothing more.
                if _credits_depleted(err_str):
                    raise CreditsDepleted("Gemini prepaid credits are depleted (HTTP 402). Top up in "
                                          "AI Studio, then re-run; done verses are kept. %s" % err_str[:300])
''', 1),
    ("fallback model",
     '''_FALLBACK_MODEL = os.environ.get("MT_FALLBACK_MODEL", "gemini-2.0-flash").strip()
''',
     '''# CREDITS_COST_2026_10_04: was gemini-2.0-flash, which this key's model list no longer has
# (list_models, 2026-10-04), so the rung always failed. MT_FALLBACK_MODEL still overrides.
_FALLBACK_MODEL = os.environ.get("MT_FALLBACK_MODEL", "gemini-2.5-flash-lite").strip()
''', 1),
]

OC_EDITS = [
    ("docstring",
     '''    """SPEND_TRUTH_2026_10_04: median USD per vision page from usage_log (last 300
    provider-metered ocr_vision rows), repriced with cost_tracker's current table."""
''',
     '''    """SPEND_TRUTH_2026_10_04: USD per vision page from usage_log (last 300
    provider-metered ocr_vision rows), repriced with cost_tracker's current table.
    CREDITS_COST_2026_10_04: the MEAN, not the median - an estimate of a total is
    n x mean, and page cost is right-skewed (2026-10-04: median $0.00282, mean
    $0.00313, max $0.04282)."""
''', 1),
    ("mean",
     "        return vals[len(vals) // 2] if len(vals) >= 5 else fallback\n",
     "        return (sum(vals) / len(vals)) if len(vals) >= 5 else fallback   # CREDITS_COST_2026_10_04: mean\n", 1),
]

CS_EDITS = [
    ("fallback",
     "# Was 0.0015 (the old 2.5 Flash price). Repriced median, ocr_vision, 24 h to 2026-10-04: ~$0.0054.\n"
     "VISION_COST_PER_PAGE = 0.0054\n",
     "# Was 0.0015 (the old 2.5 Flash price). CREDITS_COST_2026_10_04: 0.0041 = all provider-metered\n"
     "# vision since metering began, repriced, per page delivered (retries included), on 2026-10-04.\n"
     "# (The 0.0054 written here before was not a ledger figure.)\n"
     "VISION_COST_PER_PAGE = 0.0041\n", 1),
    ("label",
     'source="measured: median of the last 300 metered vision pages, today\'s prices")',
     'source="measured: mean of the last 300 metered vision pages, today\'s prices")', 1),
    ("headroom comment",
     "# 15% headroom: the median moves between runs\n",
     "# 15% headroom: retries and outliers (p90 = 1.12 x mean on 2026-10-04)\n", 1),
]

SH_EDITS = [
    ("cover padding",
     ".tcover{width:100%;height:100%;display:flex;flex-direction:column;justify-content:space-between;padding:14px 10px;text-align:center;color:#f5ead0}\n",
     "/* CREDITS_COST_2026_10_04 (SHELF_UI2): bottom padding keeps the series line clear of the ed. badge */\n"
     ".tcover{width:100%;height:100%;display:flex;flex-direction:column;justify-content:space-between;padding:14px 10px 30px;text-align:center;color:#f5ead0}\n"
     ".bcode{font-size:10.5px;color:var(--muted);font-family:Consolas,monospace;word-break:break-all}\n", 1),
    ("count titles",
     "    const books = col.books.filter(visible); nb += col.books.length; shown += books.length;\n",
     "    const books = col.books.filter(visible); nb += col.books.length; shown += books.length;\n"
     "    const dup = {}; col.books.forEach(x => { dup[x.title] = (dup[x.title] || 0) + 1; });   // SHELF_UI2\n", 1),
    ("show code on repeats",
     "        <div class=\"bmeta\">${b.passages} passages &middot;",
     "        ${dup[b.title] > 1 ? `<div class=\"bcode\" title=\"another text here has the same title\">${esc(b.code)}</div>` : ''}\n"
     "        <div class=\"bmeta\">${b.passages} passages &middot;", 1),
]

DO_EDITS = [
    ("docstring",
     '  python scripts\\\\diag_orphans.py --db "D:\\\\backups\\\\context_pre_guards_20261004_122916.db"\n',
     '  python scripts\\\\diag_orphans.py --db "D:\\\\backups\\\\context_pre_guards_20261004_122916.db" --backup\n'
     '(CREDITS_COST_2026_10_04: --backup opens the file immutable=1. A plain mode=ro open of a\n'
     'WAL-mode backup leaves -wal/-shm files beside it; immutable never does. Never use --backup\n'
     'on the live data/context.db - it would ignore the live WAL.)\n', 1),
    ("open_ro",
     'def open_ro(db: str) -> sqlite3.Connection:\n'
     '    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=60)\n',
     'def open_ro(db: str, immutable: bool = False) -> sqlite3.Connection:\n'
     '    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else ""),\n'
     '                          uri=True, timeout=60)\n', 1),
    ("run signature",
     "def run(db: str, samples: int = 3, out=print) -> dict:\n    con = open_ro(db)\n",
     "def run(db: str, samples: int = 3, out=print, immutable: bool = False) -> dict:\n    con = open_ro(db, immutable)\n", 1),
    ("flag",
     '    ap.add_argument("--samples", type=int, default=3)\n',
     '    ap.add_argument("--samples", type=int, default=3)\n'
     '    ap.add_argument("--backup", action="store_true", help="the file is a backup: open it immutable (no sidecar files)")\n', 1),
    ("call",
     "    run(a.db, a.samples)\n",
     "    if a.backup and Path(a.db).resolve() == Path(\"data/context.db\").resolve():\n"
     "        print(\"REFUSING: --backup is for backup files, never the live database.\"); return 2\n"
     "    run(a.db, a.samples, immutable=a.backup)\n", 1),
]

TARGETS = [(Path("scripts/infer_mt.py"), MT_EDITS), (Path("scripts/ocr_consensus.py"), OC_EDITS),
           (Path("scripts/corpus_status.py"), CS_EDITS), (Path("scripts/shelf_static.html"), SH_EDITS),
           (Path("scripts/diag_orphans.py"), DO_EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    marks = [MARK in s for _, s, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand:")
        for (p, _s, _n, _e), m in zip(loaded, marks):
            print("  %-30s %s" % (p, "patched" if m else "not patched"))
        return 1
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written."
              % (sum(len(e) for _, e in TARGETS), len(TARGETS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_credits")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        if p.suffix == ".py":
            try:
                py_compile.compile(str(t), doraise=True)
            except py_compile.PyCompileError as e:
                for x, _ in tmps + [(t, p)]:
                    x.unlink(missing_ok=True)
                print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_credits_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Scripts: next run. The Shelf page: reload it (static file, no restart).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
