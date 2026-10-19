#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
heal_english.py  (2026-10-19)  HEAL_ENGLISH_2026_10_19

Mends what LEAK_GUARD_2026_10_19 and KEEP_ON_EMPTY_2026_10_19 (scripts/patch_leak_guard_2026_10_19.py) found stored,
always through translate_passages.py, which archives what it replaces in translation_history; never by hand:
  1. LOST: a re-translation (retranslate_marked.py, T2) that came back empty wiped the passage's English and nothing went
     to translation_history (Mallapurana 11.5 and 11.9, markandeya_purana 28.2, Ganita 217.6). The old English is in the
     T2 log (data/retranslate/*.jsonl, "old_english"); where mt_cache still holds it, translate_passages.py
     --retranslate with that engine reads it back from the cache: free, and the passage has its English again.
  2. CHATTER: the model's words to us inside a translation (text_filters.model_chatter): 12 English and 2 Hindi of
     41,932 on 19 Oct. translate_passages.py --retranslate with the engine that made it reads the same answer back from
     mt_cache, free, and the guard keeps only the translation; where nothing is left that is a translation (the model
     reasoning aloud), the row is archived and emptied, and the passage waits for a fresh translation (--fresh).
The plan (the default) is free and read-only. --yes runs the free steps, one passage at a time, then reads each
passage again and says what it holds; --fresh also asks --fresh-engine for the passages left empty (a few cents).
Back up first: python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_heal_<date>.db (the plan
prints it). Run it when no translation job is running.

  python scripts\\heal_english.py                  the plan (free)
  python scripts\\heal_english.py --yes            the free steps
  python scripts\\heal_english.py --yes --fresh    and a fresh translation where nothing is left
  python scripts\\heal_english.py --db "D:\\backups\\context_20261019.db" --immutable   the plan on a backup
Test: python -m unittest tests.test_heal_english_2026_10_19 -v
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

MARK = "HEAL_ENGLISH_2026_10_19"
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
PY = sys.executable
FRESH_ENGINE = "anthropic:claude-sonnet-5-5"   # T2's engine for the working English (docs/SOP_TRANSLATION_2026-10-17.md)


def open_ro(db: str, immutable: bool = False) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro"), uri=True,
                          timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con


def guard_ready() -> str:
    """'' when the guard is in place (text_filters and translate_passages carry LEAK_GUARD_2026_10_19), else why not."""
    for f in ("text_filters.py", "translate_passages.py"):
        p = SCRIPTS / f
        if not p.exists() or b"LEAK_GUARD_2026_10_19" not in p.read_bytes():
            return "%s has no LEAK_GUARD_2026_10_19: apply scripts\\patch_leak_guard_2026_10_19.py first" % f
    return ""


def lost_items(con, log_dir: Path, only=None) -> list:
    """The passages a T2 run emptied: its log says failed, the passage has no English now, and nothing of it is in
    translation_history. engine: the engine whose mt_cache answer is the old English (None: not in the cache)."""
    out, seen = [], set()
    for f in sorted(glob.glob(str(log_dir / "*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("result") != "failed" or not (r.get("old_english") or "").strip():
                continue
            pid = r.get("passage_id")
            if pid in seen or (only and r.get("doc") != only):
                continue
            row = con.execute("SELECT p.page_no, p.idx, coalesce(p.translation, ''), d.code, p.text FROM passages p "
                              "JOIN docs d ON d.id = p.doc_id WHERE p.id = ?", (pid,)).fetchone()
            if not row or row[2].strip():
                continue
            seen.add(pid)
            engines = [e for (e,) in con.execute("SELECT DISTINCT engine FROM mt_cache WHERE lang_out = 'en' AND output = ?",
                                                 (r["old_english"],))]
            hit = next((e for e in engines if cache_has(con, row[4], "en", e, r["old_english"])), None)
            out.append({"kind": "lost", "lang": "en", "doc": row[3], "page": row[0], "idx": row[1], "pid": pid,
                        "engine": hit or (engines[0] if engines else None), "cached": bool(hit), "now": "",
                        "keep": r["old_english"], "left": "", "log": os.path.basename(f)})
    return out


def chatter_items(con, only=None) -> list:
    """Every stored English and Hindi translation that holds the model's words to us, with what the guard keeps."""
    import text_filters as tf
    from normalize_text import normalize_sanskrit
    out = []
    q = [("en", "SELECT p.id, d.code, p.page_no, p.idx, p.translation, p.engine, 'en', p.text FROM passages p JOIN docs d "
                "ON d.id = p.doc_id WHERE trim(coalesce(p.translation, '')) <> ''"),
         ("l10n", "SELECT p.id, d.code, p.page_no, p.idx, l.translation, l.engine, l.lang, p.text FROM translations_l10n l "
                  "JOIN passages p ON p.id = l.passage_id JOIN docs d ON d.id = p.doc_id "
                  "WHERE trim(coalesce(l.translation, '')) <> '' AND l.lang <> 'both'")]
    for kind, sql in q:
        for r in con.execute(sql).fetchall():
            if only and r[1] != only:
                continue
            said = tf.model_chatter(r[4])
            if not said:
                continue
            lang = "en" if kind == "en" else r[6]
            keep, _what = tf.strip_model_chatter(r[4])
            left = tf.model_chatter(keep)
            # what translate_passages.py will keep of the same answer: the guard, then its own filters (a bare
            # [ILLEGIBLE] is nothing; an echo of the source is nothing)
            kept = "" if left else tf.salvage_translation(keep, lang=lang)
            if kept and tf.is_source_echo(tf.clean_for_mt(normalize_sanskrit(r[7] or "")), kept, lang):
                kept = ""
            why = left or ("only the lacuna mark" if "ILLEGIBLE" in keep.upper() else "an echo of the source")
            cached = cache_has(con, r[7], lang, r[5], r[4])
            out.append({"kind": "chatter", "lang": lang, "doc": r[1], "page": r[2], "idx": r[3], "pid": r[0],
                        "engine": r[5], "cached": cached, "now": r[4], "said": said,
                        "keep": kept, "empties": not kept, "why": "" if kept else why})
    return out


def dropped_items(con, only=None) -> list:
    """The translations the guard archived and emptied (translation_history reason chatter-dropped) that have nothing
    yet: they wait for a fresh translation (--fresh)."""
    out = []
    rows = con.execute("SELECT DISTINCT h.passage_id, coalesce(h.lang, 'en'), d.code, p.page_no, p.idx FROM "
                       "translation_history h JOIN passages p ON p.id = h.passage_id JOIN docs d ON d.id = p.doc_id "
                       "WHERE h.reason = 'chatter-dropped'").fetchall()
    for pid, lang, code, page, idx in rows:
        x = {"kind": "dropped", "lang": lang, "doc": code, "page": page, "idx": idx, "pid": pid, "engine": None,
             "cached": False, "now": "", "keep": "", "empties": True, "why": "archived earlier"}
        if (only and code != only) or now_of(con, x).strip():
            continue
        out.append(x)
    return out


def command(x: dict, db: str, engine: str, tmp: str) -> list:
    """translate_passages.py on one passage again; its runtime config and progress in a folder of its own, so that the
    dashboard's config cannot switch the engine and its progress page is left alone."""
    return [PY, str(SCRIPTS / "translate_passages.py"), "--db", db, "--doc", x["doc"], "--only-page", str(x["page"]),
            "--only-idx", str(x["idx"]), "--retranslate", "--min-quality", "0", "--sleep", "0", "--lang", x["lang"],
            "--engine", engine, "--config", os.path.join(tmp, "config.json"),
            "--progress", os.path.join(tmp, "progress.json")]


def shown(x: dict, engine: str) -> str:
    return ("python scripts\\translate_passages.py --doc %s --only-page %s --only-idx %s --retranslate --min-quality 0 "
            "--sleep 0 --lang %s --engine %s" % (x["doc"], x["page"], x["idx"], x["lang"], engine))


def cache_has(con, text: str, lang: str, engine: str, output: str) -> bool:
    """True when mt_cache holds output for this passage's Sanskrit as translate_passages.py will ask for it (the same
    cleaning, the same key): its --retranslate then reads it back, free."""
    import infer_mt
    from normalize_text import normalize_sanskrit
    from text_filters import clean_for_mt
    if not engine or not text:
        return False
    key = infer_mt._hash(clean_for_mt(normalize_sanskrit(text)), lang)
    return con.execute("SELECT 1 FROM mt_cache WHERE engine = ? AND lang_in = 'sa' AND lang_out = ? AND text_hash = ? "
                       "AND output = ? LIMIT 1", (engine, lang, key, output)).fetchone() is not None


def now_of(con, x: dict) -> str:
    if x["lang"] == "en":
        r = con.execute("SELECT coalesce(translation, '') FROM passages WHERE id = ?", (x["pid"],)).fetchone()
    else:
        r = con.execute("SELECT coalesce(translation, '') FROM translations_l10n WHERE passage_id = ? AND lang = ?",
                        (x["pid"], x["lang"])).fetchone()
    return r[0] if r else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mend the English a T2 run emptied and the model's words in translations.")
    ap.add_argument("--db", default=str(ROOT / "data" / "context.db"))
    ap.add_argument("--log-dir", default=str(ROOT / "data" / "retranslate"))
    ap.add_argument("--doc", default=None, help="one text only")
    ap.add_argument("--yes", action="store_true", help="run the free steps (answers read back from mt_cache)")
    ap.add_argument("--fresh", action="store_true", help="with --yes: a fresh translation where nothing is left")
    ap.add_argument("--fresh-engine", default=FRESH_ENGINE)
    ap.add_argument("--immutable", action="store_true", help="the plan on a backup copy (read as it is; no --yes)")
    a = ap.parse_args(argv)
    print("heal_english.py  %s  (%s)" % (MARK, "runs the steps" if a.yes else "the plan; nothing is written"))
    why = guard_ready()
    if why:
        print("REFUSE: " + why)
        print("VERDICT: nothing done: the guard is not in place")
        print("NEXT: python scripts\\patch_leak_guard_2026_10_19.py --check")
        return 1
    if not Path(a.db).exists():
        print("FAIL: no database at %s" % a.db)
        return 2
    import text_filters as tf
    if a.immutable and a.yes:
        print("REFUSE: --immutable reads a backup copy: plan only")
        return 2
    con = open_ro(a.db, a.immutable)
    try:
        items = lost_items(con, Path(a.log_dir), a.doc) + chatter_items(con, a.doc) + dropped_items(con, a.doc)
    finally:
        con.close()
    if not items:
        print("VERDICT: nothing to mend: no English a T2 run emptied, no model's words in a translation, none waiting")
        print("NEXT: ")
        return 0
    tmp = tempfile.mkdtemp(prefix="heal_english_")
    Path(tmp, "config.json").write_text("{}", encoding="utf-8")
    free = [x for x in items if x["kind"] != "dropped" and x["cached"] and x["engine"]]
    fresh = [x for x in items if x not in free or x.get("empties")]
    print("  %-7s %-4s %-44s %-26s %s" % ("what", "lang", "passage", "engine", "what it will hold"))
    for x in items:
        if x["kind"] == "lost":
            after = ("its English back from the cache" if x["cached"] else
                     "not in the cache: the old English is in data\\retranslate\\%s; a fresh one with --fresh" % x["log"])
        elif x["kind"] == "dropped":
            after = "emptied earlier (the model's words, archived): a fresh translation with --fresh"
        elif not x["cached"]:
            after = "not in the cache: a fresh translation with --fresh (the guard alone would %s)" % (
                ("keep %r" % x["keep"][:40]) if x["keep"] else "keep nothing")
        elif x["keep"]:
            after = "from the cache, keeps: %r" % x["keep"][:60]
        else:
            after = "from the cache: nothing in it is a translation (%s): archived and emptied; then --fresh" % x["why"][:30]
        print("  %-7s %-4s %-44s %-26s %s" % (x["kind"], x["lang"], "%s %s.%s" % (x["doc"][:34], x["page"], x["idx"]),
                                              (x["engine"] or "-")[:26], after))
    ch = [x for x in items if x["kind"] == "chatter"]
    print("VERDICT: %d to mend: %d English a T2 run emptied; %d translations with the model's words (%d kept without "
          "them from the cache, %d archived and emptied: nothing in them is a translation, %d not in the cache: a fresh "
          "translation with --fresh); %d emptied earlier, waiting for a fresh translation"
          % (len(items), sum(1 for x in items if x["kind"] == "lost"), len(ch),
             sum(1 for x in ch if x["cached"] and not x["empties"]), sum(1 for x in ch if x["cached"] and x["empties"]),
             sum(1 for x in ch if not x["cached"]), sum(1 for x in items if x["kind"] == "dropped")))
    each = "about $0.01 each" if a.fresh_engine.startswith("anthropic:") else "a fraction of a cent each"
    if not a.yes:
        print("  each, as it will run: " + shown(items[0], items[0]["engine"] if items[0] in free else a.fresh_engine))
        bk = "python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_heal_%s.db" % (
            datetime.date.today().strftime("%Y%m%d"))
        later = "python scripts\\heal_english.py --yes --fresh   (%d passage(s) by %s, %s)" % (len(fresh), a.fresh_engine, each)
        print("NEXT: " + ((bk + " ; python scripts\\heal_english.py --yes" + ((" ; then " + later) if fresh else ""))
                          if free else later))
        shutil.rmtree(tmp, ignore_errors=True)
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log = Path(a.log_dir) / ("heal_%s.jsonl" % stamp)
    log.parent.mkdir(parents=True, exist_ok=True)
    done = {"mended": 0, "emptied": 0, "failed": 0, "fresh": 0}
    runs = [(x, x["engine"]) for x in free]
    if a.fresh:
        runs += [(x, a.fresh_engine) for x in fresh]
    try:
        for x, engine in runs:
            r = subprocess.run(command(x, a.db, engine, tmp), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=str(ROOT), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            con = open_ro(a.db)
            try:
                now = now_of(con, x)
            finally:
                con.close()
            ok = r.returncode == 0 and not tf.model_chatter(now) and (bool(now.strip()) or x["kind"] != "lost")
            res = ("mended" if now.strip() else "emptied") if ok else "failed"
            done[res] += 1
            if engine != x["engine"]:
                done["fresh"] += 1
            print("  %-8s %s %s.%s %s (%s)%s" % (res, x["doc"], x["page"], x["idx"], x["lang"], engine,
                                                 "" if ok else ": " + (r.stdout + r.stderr).strip().splitlines()[-1][:160]
                                                 if (r.stdout + r.stderr).strip() else ""))
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"mark": MARK, "kind": x["kind"], "doc": x["doc"], "where": "%s.%s" % (x["page"], x["idx"]),
                                    "lang": x["lang"], "passage_id": x["pid"], "engine": engine, "before": x["now"],
                                    "after": now, "result": res, "rc": r.returncode}, ensure_ascii=False) + "\n")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    left = [] if a.fresh else fresh
    print("VERDICT: %d mended, %d emptied (archived; nothing in them was a translation), %d failed%s; log %s"
          % (done["mended"], done["emptied"], done["failed"],
             (", %d by %s" % (done["fresh"], a.fresh_engine)) if done["fresh"] else "", log.name))
    print("NEXT: " + ("python scripts\\heal_english.py --yes --fresh   (%d passage(s) by %s, %s)" % (len(left), a.fresh_engine, each)
                      if left else "python scripts\\corpus_sync.py   (the mirror sends what changed)"))
    return 1 if done["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
