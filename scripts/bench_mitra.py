#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
bench_mitra.py  (2026-10-16)  BENCH_MITRA_2026_10_16   BM1: our English against published translations

Asked on 16 Oct: benchmark our translations against what exists, and "establish a worthy baseline" without changing
too many variables. BM1 does that and changes nothing in the pipeline: the same 200 verses of eight texts of the Hindu
traditions are translated three ways, exactly as the automaton translates today, and scored two ways: against the
published English of the Mitrasamgraha test set (chrF, the metric of the dataset's paper; also with the diacritics
and the case folded), and by our own judge on the Sanskrit alone (judge-v1, gemini-2.5-flash with its thinking,
unchanged). Paired 95% intervals (bootstrap over the sentences) say which differences are more than chance.

The three ways (the arms):
  flash    gemini-2.5-flash, one pass: translate_passages.py, as the working English is made (its prompt, the five
           verses before as context)
  sonnet1  Claude Sonnet 5.5, one pass: translate_passages.py --engine anthropic:claude-sonnet-5-5 (the same prompt):
           the model without the pipeline
  scholar  the scholarly pipeline: scholar_translate.py as the 15 Oct runs of the Hayasirsa and the Karanagama were
           made (read from their logs): Sonnet 5.5 drafts and criticises, up to 2 revisions, a sentence over several
           verses translated whole, the glossary growing; Opus 5.5 audits one sentence in ten; judge-v1; no second
           judge (--no-compare)

The verses: the test files of the Mitrasamgraha dataset (cloned by hand to
D:\\Sanksrit Automatons\\benchmarks\\mitrasamgraha-dataset) of eight texts: the Kathasaritsagara, the Bhagavata and
Skanda Puranas, the Manusmrti, the Yogavasistha, the Rgveda, the Satapatha Brahmana and the Ramayana. Not the Gita (a
sectarian translation) and not the three Buddhist texts. From each file, 25 lines in a row (the window: chosen by a
fixed seed among the windows whose every line converts cleanly and would be sent by both scripts), with the 6 lines
before it and the 2 after it as the context the pipeline reads. The IAST is written in Devanagari by the project's
own transliterator (iast_utils: indic-transliteration), as passages are stored. The published English is never sent
to a translator; with --judge-reference the judge reads it as it reads ours, not told what it is (a calibration).

The dataset is for private evaluation here: never trained on, never published, never put on the site. The sample,
the bench databases, the English and the report stay in D:\\Sanksrit Automatons\\benchmarks\\bm1, outside every
repository (this script refuses an --out inside one); BM1_summary.json holds numbers only.

The money: each step runs the pipeline's own scripts on a bench database whose ledger is a copy of the real one (the
Claude credit's rows and the spend cap are copied in before each text), so their caps hold as in a real run. After
each text the step's calls are written into data/context.db's usage_log as kind bench_<kind>, doc BM1:<text>, with
usage_totals and (Gemini only) the spend cap's spent_usd, as cost_tracker writes them: the Claude credit and the
spend cap count them; the prices the Library measures (kinds translation, scholar, judge) do not. A step stopped
half way is settled by the next one, or by --settle. Nothing else of data/context.db is read or written; the site
mirror reads data/context.db only, so nothing of BM1 reaches the site.

  python scripts\\bench_mitra.py                    what is done, what each step would send and cost (free, read-only)
  python scripts\\bench_mitra.py --sample           the sample and the bench databases (free; nothing is called)
  python scripts\\bench_mitra.py --arm flash --yes --max-usd 0.75
  python scripts\\bench_mitra.py --arm sonnet1 --yes --max-usd 4.00
  python scripts\\bench_mitra.py --arm scholar --yes --max-usd 11.00
  python scripts\\bench_mitra.py --score --judge-reference --yes --max-usd 2.75
  python scripts\\bench_mitra.py --report           BM1_report.html and BM1_summary.json (free)
  python scripts\\bench_mitra.py --settle           writes into the ledger what a stopped step left (free)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import scholar_translate as ST   # noqa: E402  (its readiness, its judge, its rows; nothing is called on import)

MARK = "BENCH_MITRA_2026_10_16"
BENCH = "BM1"
SEED = "BM1-2026-10-16"
PER_FILE = 25
LEAD, TAIL = ST.CONTEXT_BEFORE, ST.CONTEXT_AFTER     # the context the pipeline reads: 6 before, 2 after
DATA_DEFAULT = ROOT.parent / "benchmarks" / "mitrasamgraha-dataset"
OUT_DEFAULT = ROOT.parent / "benchmarks" / "bm1"
ME = "python scripts\\bench_mitra.py"   # main() adds the options of this run (--files, --out, --data, --db)
KIND_PREFIX = "bench_"
DOC_PREFIX = BENCH + ":"
BOOT = 1000
CHRF_ORDER, CHRF_BETA = 6, 2.0        # sacrebleu's chrF defaults (chrF2: characters 1 to 6, whitespace removed)
MISALIGN = 10.0     # chrF points: a neighbouring line's published English fits the arms better by this much

FILES = (
    {"key": "GK21sokss", "file": "GK21sokss_test.tsv", "code": "Kathasaritsagara", "title": "Kath\u0101sarits\u0101gara",
     "category": "kavya", "ref": "C. H. Tawney", "note": "free Victorian prose"},
    {"key": "GP10bhp", "file": "GP10bhp_test.tsv", "code": "Bhagavata_Purana", "title": "Bh\u0101gavata Pur\u0101\u1e47a",
     "category": "purana", "ref": "not named by the catalogue; it reads as the Bhaktivedanta Book Trust's",
     "note": "devotional and interpretive (\"back home, back to Godhead\"); the Sanskrit is split word by word. The "
             "summary is also given without it"},
    {"key": "GP12skp", "file": "GP12skp_test.tsv", "code": "Skanda_Purana", "title": "Skanda Pur\u0101\u1e47a",
     "category": "purana", "ref": "G. V. Tagare (the catalogue)", "note": "a line often holds two verses, numbered"},
    {"key": "GSD36manu", "file": "GSD36manu_test.tsv", "code": "Manusmrti", "title": "Manusm\u1e5bti",
     "category": "smriti", "ref": "G. Buhler (the catalogue)", "note": "close, with words supplied in brackets"},
    {"key": "GSP27yogva", "file": "GSP27yogva_test.tsv", "code": "Yogavasistha", "title": "Yogav\u0101si\u1e63\u1e6dha",
     "category": None, "ref": "Vihari-Lala Mitra (the catalogue)", "note": "loose and expansive"},
    {"key": "GV01rvh", "file": "GV01rvh_test.tsv", "code": "Rgveda", "title": "\u1e5agveda", "category": "veda",
     "ref": "the catalogue says Oldenberg; the lines read as R. T. H. Griffith's",
     "note": "archaic verse; the Sanskrit is split word by word, without accents"},
    {"key": "GV03sb", "file": "GV03sb_test.tsv", "code": "Satapatha_Brahmana", "title": "\u015aatapatha Br\u0101hma\u1e47a",
     "category": "brahmana", "ref": "J. Eggeling (the catalogue)", "note": "close, the formulas quoted"},
    {"key": "itihasa", "file": "itihasa-test-extract.tsv", "code": "Ramayana", "title": "R\u0101m\u0101ya\u1e47a",
     "category": "itihasa", "ref": "M. N. Dutt, by way of the Itihasa corpus (as read)",
     "note": "Victorian prose with OCR slips in the English; the file jumps between passages, so a window may cross a "
             "seam"},
)
EXCLUDED = ("GE07bhg (the Bhagavad Gita: a sectarian translation)",
            "GK19asvbh, K10vimkn_u, T04tat (Buddhist texts)")
NOT_CORE = ("GP10bhp",)        # the summary is given with all eight and without it

ARMS = ("flash", "sonnet1", "scholar")
ARM = {
    "flash": {"db": "F.db", "engine": "gemini:gemini-2.5-flash",
              "label": "gemini-2.5-flash, one pass (translate_passages.py: the working English)"},
    "sonnet1": {"db": "P.db", "engine": "anthropic:claude-sonnet-5-5",
                "label": "Claude Sonnet 5.5, one pass (translate_passages.py, the same prompt)"},
    "scholar": {"db": "S.db", "engine": "anthropic:claude-sonnet-5-5",
                "label": "the scholarly pipeline (scholar_translate.py, as the 15 Oct runs)"},
}
SCHOLAR_FLAGS = ("--engine", "anthropic:claude-sonnet-5-5", "--compare-engine", "anthropic:claude-opus-5-5",
                 "--audit-every", "10", "--no-compare")
JUDGE_DB = "J.db"
PRIOR = {"flash": 0.00247, "sonnet1": 0.012, "scholar": 0.0438}   # $ a verse, 16 Oct (measured; sonnet1 a guess)
DEV_OK = re.compile(r"^[\u0900-\u097f\s.,;:!?()\[\]'\-]*$")
ISO = (("r\u0325\u0304", "\u1e5d"), ("R\u0325\u0304", "\u1e5c"), ("r\u0325", "\u1e5b"), ("R\u0325", "\u1e5a"),
       ("l\u0325\u0304", "\u1e39"), ("L\u0325\u0304", "\u1e38"), ("l\u0325", "\u1e37"), ("L\u0325", "\u1e36"),
       ("\u1e41", "\u1e43"), ("\u1e40", "\u1e42"))   # ISO 15919 (r with a ring below, m with a dot above) to IAST


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def usd(x) -> str:
    return ST.usd(float(x or 0.0))


# --------------------------------------------------------------------------------------------- the text
def norm_iast(s) -> str:
    """The dataset's IAST as the project writes it: NFC, ISO 15919's r and l with a ring below and m with a dot above
    as IAST's, one space between words."""
    s = unicodedata.normalize("NFC", s or "")
    for a, b in ISO:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


VEDIC_L = re.compile("\u1e37(?=[a\u0101i\u012bu\u016b\u1e5b\u1e5deoh])")   # l with a dot below before a vowel (or h): the consonant \u0933


def to_dev(iast: str) -> str:
    """Devanagari by iast_utils (indic-transliteration, requirements.txt), as passages are stored; "" when it fails.
    The Vedic consonant \u0933 (\u012b\u1e37e, \u1e63\u0101\u1e37ha) is written \u1e37 before a vowel, which the IAST scheme reads as the vowel \u090c
    ("\u0908\u090c\u090f"): it is given as \u1e3b, whose \u0934 is then written \u0933 (Sanskrit has no \u0934). The vowel (k\u1e37pta) is kept."""
    import iast_utils
    if not iast_utils.is_library_available():
        raise RuntimeError("indic-transliteration is not installed: python -m pip install -r requirements.txt")
    dev = iast_utils.iast_to_devanagari(VEDIC_L.sub("\u1e3b", iast or "")) or ""
    dev = dev.replace("\u0933\u093c", "\u0933").replace("\u0934", "\u0933")
    return re.sub(r"[ \t]+", " ", dev).strip()


def why_not(dev: str, ref: str):
    """Why a line is not used (None: it is). The same tests the two scripts make before they send a passage."""
    if not dev:
        return "the transliteration failed"
    if not DEV_OK.match(dev):
        return "a sign the transliteration did not convert"
    w = ST.readiness(dev, "mula", 1.0)
    if w:
        return "scholar_translate.py would leave it out: " + w
    try:
        from normalize_text import normalize_sanskrit
        from text_filters import should_translate, clean_for_mt
        normed = normalize_sanskrit(dev)
        if not should_translate(normed, min_dev=0.05) or not clean_for_mt(normed):
            return "translate_passages.py would not send it"
    except ImportError:
        pass
    if len((ref or "").split()) < 3:
        return "the published English is too short"
    return None


def read_tsv(path: Path) -> list:
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                rows.append({"line": n, "iast": "", "ref": "", "dev": "", "why": "no tab"})
                continue
            iast = norm_iast(parts[0])
            ref = re.sub(r"\s+", " ", unicodedata.normalize("NFC", " ".join(parts[1:]))).strip()
            dev = to_dev(iast) if iast else ""
            rows.append({"line": n, "iast": iast, "ref": ref, "dev": dev, "why": why_not(dev, ref)})
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def window_of(rows: list, key: str, per: int = PER_FILE):
    """The window's first row (an index into rows), or None: a fixed seed's choice among the starts whose 25 lines
    are all used, with room for the context before and after."""
    ok = [r["why"] is None for r in rows]
    starts = [s for s in range(LEAD, len(rows) - per - TAIL + 1) if all(ok[s:s + per])]
    if not starts:
        return None
    return random.Random("%s:%s" % (SEED, key)).choice(starts)


def make_sample(data: Path, specs, per: int = PER_FILE) -> dict:
    """{"head": ..., "lines": [...]}: for each file its window (page 2), the context before (page 1) and after
    (page 3); the published English kept for the window's lines only (it is never sent to a translator)."""
    head = {"mark": MARK, "bench": BENCH, "seed": SEED, "per_file": per, "lead": LEAD, "tail": TAIL,
            "dataset": str(data), "files": {}, "excluded": list(EXCLUDED)}
    lines = []
    for f in specs:
        p = data / "data" / "test" / f["file"]
        rows = read_tsv(p)
        s = window_of(rows, f["key"], per)
        info = {"file": f["file"], "sha256": sha256(p), "lines": len(rows),
                "used": sum(1 for r in rows if r["why"] is None), "start": None}
        why = Counter(r["why"] for r in rows if r["why"])
        info["left_out"] = dict(why.most_common())
        if s is None:
            info["refused"] = "no %d lines in a row that are all used" % per
            head["files"][f["key"]] = info
            continue
        info["start"] = rows[s]["line"]
        parts = [(1, [r for r in rows[s - LEAD:s] if r["why"] is None], "lead"),
                 (2, rows[s:s + per], "window"),
                 (3, [r for r in rows[s + per:s + per + TAIL] if r["why"] is None], "tail")]
        for page, rs, role in parts:
            for k, r in enumerate(rs, 1):
                lines.append({"key": f["key"], "line": r["line"], "role": role, "page": page, "idx": k,
                              "iast": r["iast"], "dev": r["dev"], "ref": r["ref"] if role == "window" else ""})
        head["files"][f["key"]] = info
    return {"head": head, "lines": lines}


def write_sample(out: Path, sm: dict) -> Path:
    p = out / "sample.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(sm["head"], ensure_ascii=False) + "\n")
        for x in sm["lines"]:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return p


def load_sample(out: Path):
    p = out / "sample.jsonl"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return {"head": rows[0], "lines": rows[1:]} if rows else None


def same_sample(a: dict, b: dict) -> bool:
    key = lambda x: (x["key"], x["page"], x["idx"], x["dev"], x["iast"], x["ref"], x["line"])
    return sorted(map(key, a["lines"])) == sorted(map(key, b["lines"]))


# --------------------------------------------------------------------------------------------- the bench databases
def connect(path) -> sqlite3.Connection:
    import db_utils
    return db_utils.connect(str(path))


def open_ro(path) -> sqlite3.Connection:
    return ST.open_ro(str(path))


def db_file(con) -> str:
    for _n, name, f in con.execute("PRAGMA database_list"):
        if name == "main":
            return str(Path(f).resolve()) if f else ""
    return ""


def ledger_schema(con) -> None:
    import cost_tracker
    cost_tracker.ensure_usage_schema(con)
    con.execute("CREATE TABLE IF NOT EXISTS bench_ledger(key TEXT PRIMARY KEY, value TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS bench_settled(id INTEGER PRIMARY KEY)")
    con.commit()


def build_db(path: Path, specs, lines: list) -> int:
    """A bench database as the pipeline's (db_utils' schema, scholar_translate's tables, the usage tables): one doc a
    text, its window on page 2. Rows already there must be the same; nothing else is changed. The passages added."""
    import db_utils
    path.parent.mkdir(parents=True, exist_ok=True)
    con = connect(path)
    added = 0
    try:
        db_utils.ensure_schema(con)
        ST.ensure_schema(con)
        ledger_schema(con)
        by = {f["key"]: f for f in specs}
        for x in lines:
            f = by.get(x["key"])
            if f is None:
                continue
            did = db_utils.ensure_doc(con, f["code"], f["category"], "mitrasamgraha:" + f["file"])
            row = con.execute("SELECT text FROM passages WHERE doc_id = ? AND page_no = ? AND idx = ?",
                              (did, x["page"], x["idx"])).fetchone()
            if row:
                if row[0] != x["dev"]:
                    raise RuntimeError("%s: %s %d.%d holds another reading: this database is not this sample's"
                                       % (path.name, f["code"], x["page"], x["idx"]))
                continue
            con.execute("INSERT INTO passages(doc_id, page_no, idx, text, iast, translation, text_type, quality_score, "
                        "source) VALUES (?,?,?,?,?,'','mula',1.0,?)",
                        (did, x["page"], x["idx"], x["dev"], x["iast"], "mitrasamgraha:%s:%d" % (f["file"], x["line"])))
            added += 1
        con.commit()
    finally:
        con.close()
    return added


# --------------------------------------------------------------------------------------------- the ledger
def _cols(con, table: str) -> list:
    return [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]


def _shared(bcon, mcon) -> list:
    m = set(_cols(mcon, "usage_log"))
    return [c for c in _cols(bcon, "usage_log") if c != "id" and c in m]


def pull(bcon, mcon) -> int:
    """The real ledger into a bench database: the Claude credit's rows (engine anthropic:..., since its start) and the
    spend cap, so that a step's caps hold as they would in data/context.db. The rows copied."""
    import claude_engine as ce
    if db_file(bcon) and db_file(bcon) == db_file(mcon):
        raise RuntimeError("a bench database cannot be the ledger itself")
    ledger_schema(bcon)
    if unsettled(bcon):
        raise RuntimeError("the bench database holds calls not yet in the ledger: push them first")
    cols = _shared(bcon, mcon)
    rows = mcon.execute("SELECT %s FROM usage_log WHERE engine LIKE 'anthropic:%%' AND ts >= ?" % ", ".join(cols),
                        (ce.settings()["since"],)).fetchall()
    bs = mcon.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
    bcon.execute("DELETE FROM usage_log")
    bcon.execute("DELETE FROM bench_settled")
    bcon.executemany("INSERT INTO usage_log(%s) VALUES (%s)" % (", ".join(cols), ",".join("?" * len(cols))), rows)
    if bs:
        bcon.execute("UPDATE budget_state SET budget_usd = ?, spent_usd = ?, paused = ? WHERE id = 1", tuple(bs))
    seed = bcon.execute("SELECT COALESCE(MAX(id), 0) FROM usage_log").fetchone()[0]
    bcon.execute("INSERT OR REPLACE INTO bench_ledger(key, value) VALUES ('seed_max', ?)", (str(seed),))
    bcon.execute("INSERT OR REPLACE INTO bench_ledger(key, value) VALUES ('pulled_at', ?)", (now(),))
    bcon.commit()
    return len(rows)


def unsettled(bcon, cols=None) -> list:
    """The bench database's own calls not yet in the ledger: after the copy (seed_max), not marked settled."""
    r = bcon.execute("SELECT value FROM bench_ledger WHERE key = 'seed_max'").fetchone()
    seed = int(r[0]) if r else 0
    sel = ", ".join(["id"] + list(cols or []))
    return bcon.execute("SELECT %s FROM usage_log WHERE id > ? AND id NOT IN (SELECT id FROM bench_settled) ORDER BY id"
                        % sel, (seed,)).fetchall()


def push(bcon, mcon, arm: str, log: Path = None) -> dict:
    """A bench database's own calls (after the copy) into data/context.db: usage_log as kind bench_<kind>, doc
    BM1:<text>; usage_totals; the spend cap's spent_usd for a Gemini call (cost_tracker's statements); in one
    transaction, then marked settled in the bench database, so that a call is never written twice. (Were the computer
    to stop between the two commits, the calls would be counted twice: the caps then stop sooner, never later.)"""
    if db_file(bcon) and db_file(bcon) == db_file(mcon):
        raise RuntimeError("a bench database cannot be the ledger itself")
    ledger_schema(bcon)
    cols = _shared(bcon, mcon)
    got = unsettled(bcon, cols)
    ids = [x[0] for x in got]
    rows = [dict(zip(cols, x[1:])) for x in got]
    res = {"rows": 0, "claude": 0.0, "google": 0.0, "by_doc": {}}
    if not rows:
        return res
    old = mcon.isolation_level
    mcon.isolation_level = None
    try:
        mcon.execute("BEGIN IMMEDIATE")
        for d in rows:
            d["kind"] = d["kind"] if str(d["kind"]).startswith(KIND_PREFIX) else KIND_PREFIX + str(d["kind"])
            d["doc"] = d["doc"] if str(d["doc"] or "").startswith(DOC_PREFIX) else DOC_PREFIX + str(d["doc"] or "")
            mcon.execute("INSERT INTO usage_log(%s) VALUES (%s)" % (", ".join(cols), ",".join("?" * len(cols))),
                         [d[c] for c in cols])
            cost = float(d.get("cost_usd") or 0.0)
            mcon.execute("INSERT INTO usage_totals(engine, total_calls, total_in_chars, total_out_chars, total_cost_usd, "
                         "total_duration_s, total_passages) VALUES (?,1,?,?,?,?,?) ON CONFLICT(engine) DO UPDATE SET "
                         "total_calls = total_calls + 1, total_in_chars = total_in_chars + excluded.total_in_chars, "
                         "total_out_chars = total_out_chars + excluded.total_out_chars, "
                         "total_cost_usd = total_cost_usd + excluded.total_cost_usd, "
                         "total_duration_s = total_duration_s + excluded.total_duration_s, "
                         "total_passages = total_passages + excluded.total_passages, "
                         "last_updated = strftime('%Y-%m-%dT%H:%M:%fZ','now')",
                         (d.get("engine"), int(d.get("in_chars") or 0), int(d.get("out_chars") or 0), cost,
                          float(d.get("duration_s") or 0.0), int(d.get("passages") or 0)))
            if str(d.get("engine") or "").startswith("anthropic:"):
                res["claude"] += cost
            else:
                mcon.execute("UPDATE budget_state SET spent_usd = spent_usd + ?, "
                             "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 1", (cost,))
                res["google"] += cost
            res["rows"] += 1
            res["by_doc"][d["doc"]] = round(res["by_doc"].get(d["doc"], 0.0) + cost, 6)
        mcon.execute("COMMIT")
    except Exception:
        try:
            mcon.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        mcon.isolation_level = old
    bcon.executemany("INSERT OR IGNORE INTO bench_settled(id) VALUES (?)", [(i,) for i in ids])
    bcon.commit()
    if log is not None and res["rows"]:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(res, arm=arm, at=now(), mark=MARK)) + "\n")
    return res


def sync(bpath: Path, mcon, arm: str, log: Path) -> dict:
    """push, then pull: what the bench database spent is in the ledger, and the bench database has the ledger again."""
    bcon = connect(bpath)
    try:
        res = push(bcon, mcon, arm, log)
        pull(bcon, mcon)
    finally:
        bcon.close()
    return res


def main_ledger(db: str):
    con = sqlite3.connect(db, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con


def caps(mcon) -> dict:
    """The Claude credit and the spend cap, as data/context.db has them."""
    import claude_engine as ce
    c = ce.credit(mcon)
    b = mcon.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone() or (0.0, 0.0, 0)
    return {"credit_left": max(0.0, c["left"]), "credit_cap": c["cap"], "credit_expired": c["expired"],
            "credit_expires": c["expires"], "cap": float(b[0] or 0.0), "spent": float(b[1] or 0.0),
            "paused": bool(b[2]), "cap_left": max(0.0, float(b[0] or 0.0) - float(b[1] or 0.0))}


def prices(mcon) -> dict:
    """$ a verse for each arm and $ a judge call, measured in data/context.db where there are enough rows."""
    p = dict(PRIOR, judge=ST.JUDGE_COST_NOW)
    how = {k: "the price of 16 Oct" for k in PRIOR}
    how["sonnet1"] = "a guess (no Sonnet one-pass rows yet)"
    how["judge"] = "the price of 16 Oct"
    try:
        p["judge"] = ST.judge_price(mcon, ST.JUDGE)
        how["judge"] = "measured"
        n, s = mcon.execute("SELECT SUM(passages), SUM(cost_usd) FROM usage_log WHERE kind = 'translation' AND "
                            "engine = ? AND ts >= ?", (ARM["flash"]["engine"], ST.METERED_SINCE)).fetchone()
        if n and n >= 100:
            p["flash"], how["flash"] = float(s) / float(n), "measured on %s passages" % "{:,}".format(int(n))
        n, s = mcon.execute("SELECT SUM(passages), SUM(cost_usd) FROM usage_log WHERE kind IN ('translation', ?) AND "
                            "engine = ?", (KIND_PREFIX + "translation", ARM["sonnet1"]["engine"])).fetchone()
        if n and n >= 20:
            p["sonnet1"], how["sonnet1"] = float(s) / float(n), "measured on %s passages" % "{:,}".format(int(n))
        if ST.has_table(mcon, "scholar_translations"):
            n, avg = mcon.execute("SELECT COUNT(*), AVG(cost_usd) FROM scholar_translations WHERE engine = ? AND "
                                  "cost_usd > 0 AND created_at >= ?", (ARM["scholar"]["engine"], ST.METERED_SINCE)).fetchone()
            if n and n >= 10:
                p["scholar"], how["scholar"] = float(avg), "measured on %s verses" % "{:,}".format(int(n))
    except sqlite3.Error:
        pass
    p["how"] = how
    return p


def split_cost(arm: str, n: int, p: dict) -> tuple:
    """(the Claude credit's part, Google's part) of n verses of an arm."""
    if arm == "flash":
        return 0.0, n * p["flash"]
    if arm == "sonnet1":
        return n * p["sonnet1"], 0.0
    g = n * p["judge"]          # the pipeline's judge-v1 (Gemini) reads each sentence
    return max(0.0, n * p["scholar"] - g), g


# --------------------------------------------------------------------------------------------- what each arm made
def window(sample: dict, key: str) -> list:
    return sorted((x for x in sample["lines"] if x["key"] == key and x["role"] == "window"), key=lambda x: x["idx"])


def outputs(bcon, arm: str, code: str) -> dict:
    """{idx: English} of the window (page 2); for the scholarly arm {idx: its latest row whose Sanskrit is unchanged}."""
    if arm == "scholar":
        if not ST.has_table(bcon, "scholar_translations"):
            return {}
        allp = ST.load_text(bcon, code)
        byid = {x["id"]: x for x in allp if x["page"] == 2}
        out = {}
        for pid, r in ST.latest_rows(bcon, code, ARM["scholar"]["engine"]).items():
            x = byid.get(pid)
            if x is not None and ST.current(r, x) and (r.get("translation") or r.get("group_translation")):
                out[x["idx"]] = r
        return out
    rows = bcon.execute("SELECT p.idx, p.translation FROM passages p JOIN docs d ON d.id = p.doc_id WHERE d.code = ? "
                        "AND p.page_no = 2 AND TRIM(COALESCE(p.translation, '')) <> ''", (code,)).fetchall()
    return {i: t for i, t in rows}


def units_of(srows: dict, n: int) -> list:
    """The sentences: the scholarly arm's (a sentence over several verses is one unit), else one verse each; the same
    units for every arm, so that every score is paired."""
    units, seen = [], set()
    for i in range(1, n + 1):
        if i in seen:
            continue
        g = (srows.get(i) or {}).get("group_ref")
        members = sorted(j for j, r in srows.items() if g and r.get("group_ref") == g) if g else [i]
        members = [j for j in members if 1 <= j <= n] or [i]
        units.append(members)
        seen.update(members)
    return units


def unit_text(arm: str, members: list, outs: dict, refs: dict = None):
    """The English of a unit by an arm (None when a verse of it has none): the scholarly arm's sentence as it wrote it
    whole; one-pass arms' verses joined; the published English joined."""
    if arm == "reference":
        return " ".join(refs[m] for m in members) if refs and all(refs.get(m) for m in members) else None
    if any(m not in outs for m in members):
        return None
    if arm == "scholar":
        r0 = outs[members[0]]
        if len(members) > 1:
            return (r0.get("group_translation") or " ".join((outs[m].get("translation") or "") for m in members)).strip()
        return (r0.get("translation") or "").strip()
    return " ".join(outs[m].strip() for m in members)


def unit_name(members: list) -> str:
    return "2.%d" % members[0] if len(members) == 1 else "2.%d-2.%d" % (members[0], members[-1])


# --------------------------------------------------------------------------------------------- chrF
def clean(s) -> str:
    """The English as compared: NFC; the house's emphasis (*term*) and verse-end marks (//) removed."""
    s = unicodedata.normalize("NFC", s or "").replace("*", "")
    s = re.sub(r"\s*//\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fold(s) -> str:
    """clean(), then the diacritics and the case folded (Tawney's Satav\u00e1hana and our Satavahana meet)."""
    s = unicodedata.normalize("NFKD", clean(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def chrf_stats(hyp: str, ref: str, order: int = CHRF_ORDER) -> list:
    """sacrebleu's chrF statistics of one segment: for each n, the hypothesis' n-grams, the reference's, the matches
    (whitespace removed)."""
    h, r = "".join((hyp or "").split()), "".join((ref or "").split())
    out = []
    for n in range(1, order + 1):
        hc = Counter(h[i:i + n] for i in range(len(h) - n + 1))
        rc = Counter(r[i:i + n] for i in range(len(r) - n + 1))
        out += [sum(hc.values()), sum(rc.values()), sum((hc & rc).values())]
    return out


def chrf(stats, order: int = CHRF_ORDER, beta: float = CHRF_BETA) -> float:
    """sacrebleu's chrF from summed statistics (CHRF._compute_f_score, eps_smoothing off)."""
    factor = beta ** 2
    ap = ar = 0.0
    eff = 0
    for i in range(order):
        nh, nr, m = stats[3 * i:3 * i + 3]
        if nh > 0 and nr > 0:
            ap += m / nh
            ar += m / nr
            eff += 1
    if not eff:
        return 0.0
    ap, ar = ap / eff, ar / eff
    return 100.0 * (1 + factor) * ap * ar / (factor * ap + ar) if ap + ar else 0.0


def add(a: list, b: list) -> list:
    return [x + y for x, y in zip(a, b)]


def corpus_chrf(stats_list: list) -> float:
    tot = [0] * (3 * CHRF_ORDER)
    for s in stats_list:
        tot = add(tot, s)
    return chrf(tot)


def boot_ci(n: int, fn, rng, b: int = BOOT) -> tuple:
    """A 95% interval of fn(indices) over b resamples of n units (paired: the same indices for every arm)."""
    if n < 2:
        return None
    vals = sorted(fn([rng.randrange(n) for _ in range(n)]) for _ in range(b))
    return round(vals[int(0.025 * b)], 2), round(vals[int(0.975 * b) - 1], 2)


# --------------------------------------------------------------------------------------------- the commands
def arm_cmd(arm: str, f: dict, bpath: Path, work: Path, logs: Path, max_usd: float, n: int) -> list:
    py = sys.executable
    if arm == "scholar":
        return [py, str(SCRIPTS / "scholar_translate.py"), "--db", str(bpath), "--doc", f["code"], "--pages", "2",
                "--limit", str(n)] + list(SCHOLAR_FLAGS) + [
                "--title", f["title"], "--verdicts", str(work / "register.jsonl"), "--log-dir", str(logs),
                "--max-usd", "%.2f" % max_usd, "--yes"]
    return [py, str(SCRIPTS / "translate_passages.py"), "--db", str(bpath), "--doc", f["code"],
            "--engine", ARM[arm]["engine"], "--since-page", "2", "--until-page", "2", "--min-quality", "0",
            "--progress", str(work / ("progress_%s.json" % arm)), "--config", str(work / ("config_%s.json" % arm)),
            "--max-consecutive-failures", "5"]


def child_env(work: Path) -> dict:
    env = dict(os.environ)
    env["SA_SOURCE_VERDICTS"] = str(work / "register.jsonl")   # an empty register: no bench text is held
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# --------------------------------------------------------------------------------------------- the report
def gather(out: Path, sample: dict, specs) -> list:
    """Per text: its window, each arm's English, the units, the scholarly rows' status and the pipeline's own judge."""
    res = []
    dbs = {arm: out / "db" / ARM[arm]["db"] for arm in ARMS}
    cons = {arm: open_ro(p) for arm, p in dbs.items() if p.exists()}
    try:
        for f in specs:
            w = window(sample, f["key"])
            if not w:
                continue
            refs = {x["idx"]: x["ref"] for x in w}
            outs = {arm: (outputs(c, arm, f["code"]) if c else {}) for arm, c in
                    ((a, cons.get(a)) for a in ARMS)}
            units = units_of(outs["scholar"], len(w))
            res.append({"f": f, "w": w, "refs": refs, "outs": outs, "units": units})
    finally:
        for c in cons.values():
            c.close()
    return res


def judged(out: Path) -> dict:
    """{(key, unit, arm, sha): the latest judgement that gave scores}."""
    p = out / "judge.jsonl"
    got = {}
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("fidelity") is not None and r.get("fluency") is not None:
                    got[(r["key"], r["unit"], r["arm"], r["sha"])] = r
    return got


def sha(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def misaligned(m: list, refs: dict, t: dict, arms: list):
    """"the line before" or "the line after" when that line's published English fits the arms' English of this unit
    better, on average, by MISALIGN chrF points or more than its own: the dataset's pair is likely shifted (the
    Satapatha's test file has such pairs). None otherwise. The same for every arm, so no arm is favoured."""
    own = unit_text("reference", m, {}, refs)
    if not own or not arms:
        return None
    mean = lambda ref: sum(chrf(chrf_stats(clean(t[a]), clean(ref))) for a in arms) / len(arms)
    base, best, where = mean(own), None, None
    for d, name in ((-1, "the line before"), (1, "the line after")):
        mm = [i + d for i in m]
        if all(refs.get(i) for i in mm):
            v = mean(" ".join(refs[i] for i in mm))
            if best is None or v > best:
                best, where = v, name
    return where if best is not None and best >= base + MISALIGN else None


def scope_numbers(items: list, arms: list, jd: dict, rng, aligned_only: bool = False) -> dict:
    """The numbers of one scope (a text, or several): chrF and folded chrF per arm, judge-v1's means and pass share
    per arm (and the reference's), paired intervals of the differences, over the units every arm translated
    (aligned_only: and whose published English is not a neighbour's, misaligned())."""
    units = []
    for it in items:
        for m in it["units"]:
            t = {a: unit_text(a, m, it["outs"][a]) for a in ARMS}
            if any(t[a] is None for a in arms):
                continue
            ref = unit_text("reference", m, {}, it["refs"])
            mis = misaligned(m, it["refs"], t, arms)
            if aligned_only and mis:
                continue
            u = {"key": it["f"]["key"], "unit": unit_name(m), "n": len(m), "ref": ref, "t": t, "chrf": {}, "fold": {},
                 "judge": {}, "misaligned": mis}
            for a in arms:
                u["chrf"][a] = chrf_stats(clean(t[a]), clean(ref))
                u["fold"][a] = chrf_stats(fold(t[a]), fold(ref))
            for a in list(arms) + ["reference"]:
                txt = ref if a == "reference" else t[a]
                r = jd.get((u["key"], u["unit"], a, sha(txt)))
                if r:
                    u["judge"][a] = (int(r["fidelity"]), int(r["fluency"]))
            srow = it["outs"]["scholar"].get(m[0]) if "scholar" in it["outs"] else None
            if srow:
                u["status"] = srow.get("status")
                u["pipeline_judge"] = (srow.get("fidelity"), srow.get("fluency"))
            units.append(u)
    n = len(units)
    out = {"units": n, "verses": sum(u["n"] for u in units), "arms": list(arms), "chrf": {}, "chrf_folded": {},
           "judge": {}, "diff": {}, "misaligned": sum(1 for u in units if u.get("misaligned"))}
    if not n:
        return out
    for a in arms:
        out["chrf"][a] = round(corpus_chrf([u["chrf"][a] for u in units]), 2)
        out["chrf_folded"][a] = round(corpus_chrf([u["fold"][a] for u in units]), 2)
    for a in list(arms) + ["reference"]:
        js = [(u["judge"][a], u["n"]) for u in units if a in u["judge"]]
        if js:
            w = sum(k for _s, k in js)
            out["judge"][a] = {"units": len(js), "fidelity": round(sum(s[0] * k for s, k in js) / w, 2),
                               "fluency": round(sum(s[1] * k for s, k in js) / w, 2),
                               "pass": round(100.0 * sum(k for s, k in js if s[0] >= 4 and s[1] >= 4) / w, 1)}
    pairs = [(x, y) for x, y in (("scholar", "flash"), ("scholar", "sonnet1"), ("sonnet1", "flash"))
             if x in arms and y in arms]   # x minus y: above nought, x is the closer (or the more faithful)
    for x, y in pairs:
        d = {"chrf": round(out["chrf"][x] - out["chrf"][y], 2),
             "chrf_ci": boot_ci(n, lambda ix: corpus_chrf([units[i]["chrf"][x] for i in ix])
                                - corpus_chrf([units[i]["chrf"][y] for i in ix]), rng),
             "folded": round(out["chrf_folded"][x] - out["chrf_folded"][y], 2),
             "folded_ci": boot_ci(n, lambda ix: corpus_chrf([units[i]["fold"][x] for i in ix])
                                  - corpus_chrf([units[i]["fold"][y] for i in ix]), rng)}
        both = [u for u in units if x in u["judge"] and y in u["judge"]]
        if len(both) >= 2:
            def fid(ix, both=both, x=x, y=y):
                w = sum(both[i]["n"] for i in ix)
                return sum((both[i]["judge"][x][0] - both[i]["judge"][y][0]) * both[i]["n"] for i in ix) / w
            d["fidelity"] = round(fid(range(len(both))), 2)
            d["fidelity_ci"] = boot_ci(len(both), fid, rng)
        out["diff"]["%s-%s" % (x, y)] = d
    st = Counter(u.get("status") for u in units if u.get("status"))
    if st:
        out["scholar_status"] = dict(st)
    agree = [(u["judge"]["scholar"], u["pipeline_judge"]) for u in units
             if "scholar" in u["judge"] and u.get("pipeline_judge") and u["pipeline_judge"][0] is not None]
    if agree:
        out["judge_again"] = {"units": len(agree),
                              "fidelity_same": sum(1 for a_, b_ in agree if a_[0] == b_[0]),
                              "fidelity_within_one": sum(1 for a_, b_ in agree if abs(a_[0] - int(b_[0])) <= 1)}
    out["_units"] = units
    return out


def spend(out: Path) -> dict:
    """{arm: {"claude", "google", "by_doc"}} from the steps' settlements (spend.jsonl)."""
    got = {}
    p = out / "spend.jsonl"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                a = got.setdefault(r.get("arm") or "?", {"claude": 0.0, "google": 0.0, "by_doc": {}})
                a["claude"] += float(r.get("claude") or 0.0)
                a["google"] += float(r.get("google") or 0.0)
                for k, v in (r.get("by_doc") or {}).items():
                    a["by_doc"][k] = a["by_doc"].get(k, 0.0) + float(v)
    return got


def _fmt_ci(ci) -> str:
    return "[%+.2f, %+.2f]" % ci if ci else "-"


def report(out: Path, sample: dict, specs) -> tuple:
    items = gather(out, sample, specs)
    jd = judged(out)
    have = [a for a in ARMS if any(it["outs"][a] for it in items)]
    rng = random.Random(SEED + ":boot")
    scopes = [("all", "all eight texts", items, False),
              ("core", "without the Bhagavata (%s)" % ", ".join(NOT_CORE),
               [it for it in items if it["f"]["key"] not in NOT_CORE], False),
              ("aligned", "all eight, without the units whose published English seems a neighbour's", items, True)]
    scopes += [(it["f"]["key"], it["f"]["title"], [it], False) for it in items]
    nums = {k: dict(scope_numbers(its, have, jd, rng, al), name=name) for k, name, its, al in scopes}
    sp = spend(out)
    summary = {"mark": MARK, "bench": BENCH, "made_at": now(), "seed": SEED, "per_file": sample["head"]["per_file"],
               "judge": "%s (%s)" % (ST.JUDGE, ST.JUDGE_PROMPT), "metric": "chrF (sacrebleu chrF2: characters 1-6, "
               "whitespace removed); also with the diacritics and the case folded", "arms": {a: ARM[a]["label"] for a in have},
               "scholar_flags": " ".join(SCHOLAR_FLAGS), "excluded": list(EXCLUDED),
               "files": {it["f"]["key"]: {"text": it["f"]["title"], "reference": it["f"]["ref"], "note": it["f"]["note"],
                                          "start_line": sample["head"]["files"].get(it["f"]["key"], {}).get("start")}
                         for it in items},
               "scopes": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in nums.items()},
               "spend": {a: {"claude": round(v["claude"], 4), "google": round(v["google"], 4)} for a, v in sp.items()}}
    jp = out / "BM1_summary.json"
    jp.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    hp = out / "BM1_report.html"
    hp.write_text(page(summary, nums, have), encoding="utf-8")
    return jp, hp, summary


def page(summary: dict, nums: dict, have: list) -> str:
    e = html.escape
    css = ("body{font-family:Georgia,serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}"
           "table{border-collapse:collapse;margin:1rem 0;font-size:14px}td,th{border:1px solid #ccc;padding:4px 8px;"
           "vertical-align:top;text-align:left}th{background:#f4f1ea}.n{text-align:right;font-variant-numeric:"
           "tabular-nums}.warn{background:#fff4e5;border:1px solid #f0c27b;padding:.6rem 1rem}details{margin:.4rem 0}"
           ".sa{font-size:13px;color:#555;font-style:italic}.small{font-size:12px;color:#666}")
    h = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
         "initial-scale=1'><title>BM1 report</title><style>%s</style></head><body>" % css,
         "<h1>BM1: our English against published translations</h1>",
         "<p class='warn'>Private evaluation. The published English and the Sanskrit here are the Mitrasamgraha "
         "dataset's: do not share, publish or put this page on the site.</p>",
         "<p class='small'>%s. Made %s. The judge: %s, on the Sanskrit alone. %s. Excluded: %s.</p>"
         % (e(MARK), e(summary["made_at"]), e(summary["judge"]), e(summary["metric"]), e("; ".join(EXCLUDED)))]
    h.append("<h2>The arms</h2><ul>%s</ul><p class='small'>The scholarly arm's flags: %s</p>"
             % ("".join("<li><b>%s</b>: %s</li>" % (e(a), e(ARM[a]["label"])) for a in have), e(summary["scholar_flags"])))
    h.append("<h2>The summary</h2><table><tr><th>Scope</th><th>Units (verses)</th>%s%s<th>Differences (95%% interval)"
             "</th></tr>" % ("".join("<th>chrF %s</th>" % e(a) for a in have),
                            "".join("<th>judge %s</th>" % e(a) for a in list(have) + ["reference"])))
    for k, v in nums.items():
        js = "".join("<td class='n'>%s</td>" % (("%.2f / %.2f, %.0f%% pass" % (v["judge"][a]["fidelity"],
                                                  v["judge"][a]["fluency"], v["judge"][a]["pass"]))
                                                 if a in v.get("judge", {}) else "-") for a in list(have) + ["reference"])
        cs = "".join("<td class='n'>%s<br><span class='small'>folded %s</span></td>"
                     % (v["chrf"].get(a, "-"), v["chrf_folded"].get(a, "-")) for a in have)
        ds = "<br>".join("%s: chrF %+.2f %s; folded %+.2f %s%s" % (
            e(p.replace("-", " \u2212 ")), d["chrf"], _fmt_ci(d["chrf_ci"]), d["folded"], _fmt_ci(d["folded_ci"]),
            ("; fidelity %+.2f %s" % (d["fidelity"], _fmt_ci(d.get("fidelity_ci")))) if "fidelity" in d else "")
            for p, d in v.get("diff", {}).items())
        h.append("<tr><td>%s%s</td><td class='n'>%d (%d)</td>%s%s<td class='small'>%s</td></tr>"
                 % (e(v["name"]), ("<br><span class='small'>%d unit(s) whose published English seems a neighbour's</span>"
                                   % v["misaligned"]) if v.get("misaligned") else "", v["units"], v["verses"], cs, js, ds))
    h.append("</table>")
    for k, v in nums.items():
        if k in ("all", "core", "aligned"):
            continue
        fi = summary["files"].get(k, {})
        h.append("<h2>%s</h2><p class='small'>The published English: %s; %s. The window starts at line %s of the "
                 "file.%s%s</p>" % (e(v["name"]), e(fi.get("reference") or ""), e(fi.get("note") or ""),
                                    fi.get("start_line"), (" The scholarly rows: %s." % e(json.dumps(v["scholar_status"])))
                                    if v.get("scholar_status") else "",
                                    (" judge-v1 again on the scholarly English: the same fidelity in %d of %d, within "
                                     "one in %d." % (v["judge_again"]["fidelity_same"], v["judge_again"]["units"],
                                                     v["judge_again"]["fidelity_within_one"])) if v.get("judge_again") else ""))
        for u in v.get("_units", []):
            rows = ["<tr><th>published</th><td>%s</td><td class='n'>%s</td></tr>"
                    % (e(u["ref"] or ""), ("%d/%d" % u["judge"]["reference"]) if "reference" in u["judge"] else "")]
            for a in have:
                rows.append("<tr><th>%s</th><td>%s</td><td class='n'>chrF %.1f%s</td></tr>" % (
                    e(a), e(u["t"][a] or ""), chrf(u["chrf"][a]),
                    ("<br>judge %d/%d" % u["judge"][a]) if a in u["judge"] else ""))
            h.append("<details><summary>%s%s%s</summary><table>%s</table></details>"
                     % (e(u["unit"]), (" (%s)" % e(u["status"])) if u.get("status") else "",
                        (" <b>the published English seems to belong to %s</b>" % e(u["misaligned"]))
                        if u.get("misaligned") else "", "".join(rows)))
    h.append("<p class='small'>The spend, as settled into the ledger: %s</p></body></html>"
             % e(json.dumps(summary.get("spend") or {})))
    return "\n".join(h)


# --------------------------------------------------------------------------------------------- the steps
def outside_repos(out: Path) -> bool:
    o = out.resolve()
    for r in (ROOT.resolve(),):
        if o == r or r in o.parents:
            return False
    return not any((q / ".git").exists() for q in [o] + list(o.parents))


def todo_of(out: Path, sample: dict, specs, arm: str) -> dict:
    """{key: verses of the window the arm has not translated}."""
    p = out / "db" / ARM[arm]["db"]
    got = {}
    con = open_ro(p) if p.exists() else None
    try:
        for f in specs:
            w = window(sample, f["key"])
            have = outputs(con, arm, f["code"]) if con else {}
            got[f["key"]] = sum(1 for x in w if x["idx"] not in have)
    finally:
        if con:
            con.close()
    return got


def run_arm(a, out: Path, sample: dict, specs, mdb: str) -> int:
    arm = a.arm
    bpath = out / "db" / ARM[arm]["db"]
    if not bpath.exists():
        print("REFUSE: %s is not made: %s --sample" % (bpath, ME))
        print("VERDICT: nothing sent"); print("NEXT: " + ME + " --sample"); return 1
    work, logs, slog = out / "work", out / "logs" / arm, out / "spend.jsonl"
    work.mkdir(parents=True, exist_ok=True)
    (work / "register.jsonl").touch()
    mcon = main_ledger(mdb)
    try:
        p = prices(mcon)
        todo = todo_of(out, sample, specs, arm)
        n_all = sum(todo.values())
        cl, gg = split_cost(arm, n_all, p)
        cp = caps(mcon)
        cap = a.max_usd if a.max_usd is not None else max(0.25, round((cl + gg) * 1.3 + 0.05, 2))
        print("bench_mitra.py  %s  %s  RUN  %s" % (MARK, BENCH, ARM[arm]["label"]))
        print("  to send: %d verse(s); about %s (%s the Claude credit, %s Google); --max-usd %s"
              % (n_all, usd(cl + gg), usd(cl), usd(gg), usd(cap)))
        if not n_all:
            print("VERDICT: nothing to send: every verse of the sample has its English (%s)" % arm)
            print("NEXT: " + ME + " --score --judge-reference   (the dry run)"); return 0
        if cl and (cp["credit_expired"] or cp["credit_left"] < cl):
            print("REFUSE: the Claude credit has %s left (%s): this arm needs about %s"
                  % (usd(cp["credit_left"]), "expired" if cp["credit_expired"] else "expires " + cp["credit_expires"], usd(cl)))
            print("VERDICT: nothing sent"); print("NEXT: python scripts\\claude_engine.py --credit"); return 1
        if gg and (cp["paused"] or cp["cap_left"] < gg):
            print("REFUSE: the spend cap has %s left (%s of %s spent%s): this arm needs about %s of it"
                  % (usd(cp["cap_left"]), usd(cp["spent"]), usd(cp["cap"]), ", paused" if cp["paused"] else "", usd(gg)))
            print("VERDICT: nothing sent"); print("NEXT: python scripts\\set_budget.py   (what it is; a person raises it)")
            return 1
        spent, done_n, why = 0.0, 0, ""
        first = sync(bpath, mcon, arm, slog)
        if first["rows"]:
            print("  settled first: %d call(s) a stopped step left, %s" % (first["rows"], usd(first["claude"] + first["google"])))
        try:
            for f in specs:
                n = todo.get(f["key"], 0)
                if not n:
                    continue
                c_, g_ = split_cost(arm, n, p)
                left = cap - spent
                if c_ + g_ > left:
                    why = "--max-usd %s is reached (%s spent)" % (usd(cap), usd(spent)); break
                print("\n----- %s (%s): %d verse(s), about %s -----" % (f["title"], f["code"], n, usd(c_ + g_)))
                cmd = arm_cmd(arm, f, bpath, work, logs, left, n)
                try:
                    rc = subprocess.run(cmd, cwd=str(ROOT), env=child_env(work)).returncode
                finally:
                    got = sync(bpath, mcon, arm, slog)
                    spent += got["claude"] + got["google"]
                bcon = open_ro(bpath)
                try:
                    have = len(outputs(bcon, arm, f["code"]))
                finally:
                    bcon.close()
                done_n += have
                print("----- %s: %d of %d verses have their English; %s settled into the ledger (%d call(s)) -----"
                      % (f["code"], have, len(window(sample, f["key"])), usd(got["claude"] + got["google"]), got["rows"]))
                if rc not in (0,):
                    why = "%s stopped with %d on %s (its output above)" % (Path(cmd[1]).name, rc, f["code"]); break
        except KeyboardInterrupt:
            why = "stopped by hand (what was spent is settled)"
        cp2 = caps(mcon)
    finally:
        mcon.close()
    if why:
        print("  STOPPED: " + why)
    print("  the Claude credit: %s left; the spend cap: %s left of %s" % (usd(cp2["credit_left"]), usd(cp2["cap_left"]),
                                                                      usd(cp2["cap"])))
    left_n = sum(todo_of(out, sample, specs, arm).values())
    print("VERDICT: %s: %d verse(s) still without English; %s spent in this step (settled as kind bench_*, doc BM1:*)"
          % (arm, left_n, usd(spent)))
    print("NEXT: " + ME + "   (the state)" if left_n else
          "NEXT: " + ME + " --score --judge-reference   (the dry run of the scoring)")
    return 0 if not why else 3


def judge_tasks(out: Path, sample: dict, specs, with_ref: bool) -> list:
    items = gather(out, sample, specs)
    jd = judged(out)
    tasks = []
    for it in items:
        dev = {x["idx"]: x["dev"] for x in it["w"]}
        ia = {x["idx"]: x["iast"] for x in it["w"]}
        for m in it["units"]:
            for arm in list(ARMS) + (["reference"] if with_ref else []):
                t = unit_text(arm, m, it["outs"].get(arm, {}), it["refs"])
                if not t or (it["f"]["key"], unit_name(m), arm, sha(t)) in jd:
                    continue
                tasks.append({"f": it["f"], "unit": unit_name(m), "arm": arm, "text": t,
                              "src": "\n".join(dev[i].strip() for i in m), "iast": "\n".join(ia[i].strip() for i in m)})
    random.Random(SEED + ":judge").shuffle(tasks)   # the arms interleaved: no arm is judged all at one hour
    return tasks


def missing_arms(out: Path, sample: dict, specs) -> list:
    """[(arm, text)] with no English at all: the scholarly arm's sentences decide the units every arm is judged on, so
    the judge waits for the three."""
    got = []
    for arm in ARMS:
        p = out / "db" / ARM[arm]["db"]
        con = open_ro(p) if p.exists() else None
        try:
            for f in specs:
                if window(sample, f["key"]) and not (outputs(con, arm, f["code"]) if con else {}):
                    got.append((arm, f["key"]))
        finally:
            if con:
                con.close()
    return got


def run_score(a, out: Path, sample: dict, specs, mdb: str) -> int:
    miss = missing_arms(out, sample, specs)
    if miss:
        print("REFUSE: no English yet from %s: the scholarly arm's sentences decide the units every arm is judged on, "
              "so the judge waits for the three arms" % ", ".join("%s on %s" % m for m in miss[:6]))
        print("VERDICT: nothing sent"); print("NEXT: " + ME + "   (the state)"); return 1
    tasks = judge_tasks(out, sample, specs, a.judge_reference)
    mcon = main_ledger(mdb)
    try:
        p = prices(mcon)
        cp = caps(mcon)
        est = len(tasks) * p["judge"]
        cap = a.max_usd if a.max_usd is not None else max(0.25, round(est * 1.3 + 0.05, 2))
        print("bench_mitra.py  %s  %s  %s  the judge (%s, %s) on %d English"
              % (MARK, BENCH, "RUN" if a.yes else "DRY RUN (nothing called, nothing written)", ST.JUDGE, ST.JUDGE_PROMPT,
                 len(tasks)))
        by = Counter(t["arm"] for t in tasks)
        print("  to judge: %s; about %s (Google; %s a call, %s); --max-usd %s"
              % (", ".join("%s %d" % kv for kv in sorted(by.items())) or "nothing", usd(est), usd(p["judge"]),
                 p["how"]["judge"], usd(cap)))
        print("  the spend cap: %s left of %s" % (usd(cp["cap_left"]), usd(cp["cap"])))
        if not tasks:
            print("VERDICT: nothing to judge"); print("NEXT: " + ME + " --report"); return 0
        if not a.yes:
            print("VERDICT: %d to judge, about %s" % (len(tasks), usd(est)))
            print("NEXT: " + ME + " --score%s --yes --max-usd %.2f"
                  % (" --judge-reference" if a.judge_reference else "", cap)); return 0
        if cp["paused"] or cp["cap_left"] < est:
            print("REFUSE: the spend cap has %s left: the judge needs about %s" % (usd(cp["cap_left"]), usd(est)))
            print("VERDICT: nothing sent"); print("NEXT: python scripts\\set_budget.py"); return 1
        jpath = out / "db" / JUDGE_DB
        jpath.parent.mkdir(parents=True, exist_ok=True)
        jcon = connect(jpath)
        ledger_schema(jcon)
        jcon.close()
        sync(jpath, mcon, "score", out / "spend.jsonl")
        jcon = connect(jpath)
        try:
            ga = argparse.Namespace(engine=ST.COMPARE_ENGINE, judge_engine=ST.JUDGE)
            g = ST.Gemini(ga, {"doc": "judge", "title": "", "category": None, "source": "", "engine": "", "agama": False},
                          jcon)
        except RuntimeError as e:
            jcon.close()
            print("REFUSE: %s" % e); print("VERDICT: nothing called"); print("NEXT: "); return 1
        from usage_meter import budget_ok
        spent, n, fails, why = 0.0, 0, 0, ""
        jl = out / "judge.jsonl"
        try:
            for t in tasks:
                if spent + p["judge"] > cap:
                    why = "--max-usd %s is reached" % usd(cap); break
                if not budget_ok(jcon, p["judge"]):
                    why = "the spend cap is reached (python scripts\\set_budget.py shows it)"; break
                g.meta["doc"] = t["f"]["code"]
                fid, flu, reason, cost = g.judge(t["src"], t["iast"], t["text"])
                spent += cost
                n += 1
                rec = {"key": t["f"]["key"], "unit": t["unit"], "arm": t["arm"], "sha": sha(t["text"]),
                       "fidelity": fid, "fluency": flu, "reason": reason, "cost": round(cost, 6), "judge": ST.JUDGE,
                       "prompt": ST.JUDGE_PROMPT, "at": now(), "mark": MARK}
                with open(jl, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fails = fails + 1 if fid is None else 0
                if n % 25 == 0:
                    print("  %d of %d judged, %s" % (n, len(tasks), usd(spent)))
                    jcon.close(); sync(jpath, mcon, "score", out / "spend.jsonl"); jcon = connect(jpath); g.con = jcon
                if fails >= 5:
                    why = "five judgements running failed: the API (or the key) is not answering"; break
        except KeyboardInterrupt:
            why = "stopped by hand (what was spent is settled)"
        finally:
            jcon.close()
            sync(jpath, mcon, "score", out / "spend.jsonl")
    finally:
        mcon.close()
    if why:
        print("  STOPPED: " + why)
    left = len(judge_tasks(out, sample, specs, a.judge_reference))
    print("VERDICT: %d judged, %s spent (settled as kind bench_judge); %d still to judge" % (n, usd(spent), left))
    print("NEXT: " + ME + " --report")
    return 0 if not why else 3


def status(a, out: Path, data: Path, specs, mdb: str) -> int:
    print("bench_mitra.py  %s  %s  DRY RUN (nothing called, nothing written)" % (MARK, BENCH))
    found = [f for f in specs if (data / "data" / "test" / f["file"]).exists()]
    print("  the dataset: %s (%d of %d test files found)" % (data, len(found), len(specs)))
    print("  the output: %s (outside the repositories; private)" % out)
    sample = load_sample(out)
    if not sample:
        print("  the sample: not made")
        print("VERDICT: make the sample first (free)")
        print("NEXT: " + ME + " --sample"); return 0
    nw = sum(1 for x in sample["lines"] if x["role"] == "window")
    print("  the sample: %d verses (%d a text), %d lines of context; made with seed %s"
          % (nw, sample["head"]["per_file"], len(sample["lines"]) - nw, sample["head"]["seed"]))
    for k, v in sample["head"]["files"].items():
        if v.get("refused"):
            print("    %-11s REFUSED: %s" % (k, v["refused"]))
    mcon = open_ro(mdb) if Path(mdb).exists() else None
    p = prices(mcon) if mcon else dict(PRIOR, judge=ST.JUDGE_COST_NOW, how={})
    cp = caps(mcon) if mcon else None
    if mcon:
        mcon.close()
    if cp:
        print("  the ledger: the Claude credit %s left of %s (%s); the spend cap %s left (%s of %s spent%s)"
              % (usd(cp["credit_left"]), usd(cp["credit_cap"]), "EXPIRED" if cp["credit_expired"] else "expires " +
                 cp["credit_expires"], usd(cp["cap_left"]), usd(cp["spent"]), usd(cp["cap"]), ", PAUSED" if cp["paused"] else ""))
    tot_c = tot_g = 0.0
    for arm in ARMS:
        todo = sum(todo_of(out, sample, specs, arm).values())
        c_, g_ = split_cost(arm, todo, p)
        tot_c += c_; tot_g += g_
        print("  %-8s %s: %d of %d done; to send %d, about %s (%s a verse, %s)"
              % (arm, ARM[arm]["label"], nw - todo, nw, todo, usd(c_ + g_), usd(p[arm]), p.get("how", {}).get(arm, "")))
    left = {arm: sum(todo_of(out, sample, specs, arm).values()) for arm in ARMS}
    nj = max(0, (len(ARMS) + 1) * nw - len(judged(out)))   # at most a call a verse for each arm and the reference
    print("  score    judge-v1 (%s) on each arm's English and the published English: at most %d calls, about %s "
          "(Google; %s a call)" % (ST.JUDGE, nj, usd(nj * p["judge"]), usd(p["judge"])))
    tot_g += nj * p["judge"]
    print("  in all, still to spend: about %s: %s the Claude credit, %s Google" % (usd(tot_c + tot_g), usd(tot_c), usd(tot_g)))
    if cp and tot_g > cp["cap_left"]:
        print("  WARNING: the spend cap has %s left: Google's part (%s) does not fit; the arms and the judge refuse past it"
              % (usd(cp["cap_left"]), usd(tot_g)))
    nxt = next((arm for arm in ARMS if left[arm]), None)
    print("VERDICT: %s" % ("every arm has its English" if not nxt else "%s next" % nxt))
    if nxt:
        c_, g_ = split_cost(nxt, left[nxt], p)
        print("NEXT: " + ME + " --arm %s --yes --max-usd %.2f" % (nxt, max(0.25, round((c_ + g_) * 1.3 + 0.05, 2))))
    else:
        print("NEXT: " + ME + " --score --judge-reference")
    return 0


def do_sample(a, out: Path, data: Path, specs) -> int:
    missing = [f["file"] for f in specs if not (data / "data" / "test" / f["file"]).exists()]
    if missing:
        print("REFUSE: not found in %s: %s" % (data / "data" / "test", ", ".join(missing)))
        print("VERDICT: nothing written"); print("NEXT: "); return 1
    try:
        sm = make_sample(data, specs, a.per_file)
    except RuntimeError as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing written"); print("NEXT: "); return 1
    old = load_sample(out)
    print("bench_mitra.py  %s  %s  the sample (free; nothing is called)" % (MARK, BENCH))
    for f in specs:
        v = sm["head"]["files"][f["key"]]
        print("  %-11s %-22s %d lines, %d used; %s" % (f["key"], f["code"], v["lines"], v["used"],
              ("REFUSED: " + v["refused"]) if v.get("refused") else "the window from line %d" % v["start"]))
        for w, k in list(v["left_out"].items())[:3]:
            print("              left out: %d (%s)" % (k, w))
    if old and not same_sample(old, sm):
        print("REFUSE: %s holds another sample (the dataset or the seed changed): its English would no longer match. "
              "Move the folder aside to begin again." % (out / "sample.jsonl"))
        print("VERDICT: nothing written"); print("NEXT: "); return 1
    if not old:
        write_sample(out, sm)
    added = {arm: build_db(out / "db" / ARM[arm]["db"], specs, sm["lines"]) for arm in ARMS}
    nw = sum(1 for x in sm["lines"] if x["role"] == "window")
    print("VERDICT: the sample %s: %d verses, %d lines of context; the bench databases: %s"
          % ("kept (the same)" if old else "written", nw, len(sm["lines"]) - nw,
             ", ".join("%s +%d" % (ARM[arm]["db"], added[arm]) for arm in ARMS)))
    print("NEXT: " + ME + "   (what each arm would cost)")
    return 0


def settle(out: Path, mdb: str) -> int:
    mcon = main_ledger(mdb)
    tot = {"rows": 0, "claude": 0.0, "google": 0.0}
    try:
        for name, arm in [(ARM[a_]["db"], a_) for a_ in ARMS] + [(JUDGE_DB, "score")]:
            p = out / "db" / name
            if p.exists():
                r = sync(p, mcon, arm, out / "spend.jsonl")
                for k in tot:
                    tot[k] += r[k]
    finally:
        mcon.close()
    print("VERDICT: %d call(s) settled into the ledger, %s (the Claude credit %s, Google %s)"
          % (tot["rows"], usd(tot["claude"] + tot["google"]), usd(tot["claude"]), usd(tot["google"])))
    print("NEXT: " + ME + "")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db", help="the real ledger (usage_log, budget_state)")
    ap.add_argument("--data", default=str(DATA_DEFAULT), help="the Mitrasamgraha dataset (cloned by hand)")
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="the bench folder, outside every repository")
    ap.add_argument("--files", default=None, help="some texts only: GSD36manu,GV01rvh")
    ap.add_argument("--per-file", type=int, default=PER_FILE)
    ap.add_argument("--sample", action="store_true", help="make the sample and the bench databases (free)")
    ap.add_argument("--arm", choices=ARMS, default=None)
    ap.add_argument("--score", action="store_true", help="judge-v1 on each arm's English (a dry run without --yes)")
    ap.add_argument("--judge-reference", action="store_true", help="the judge reads the published English too")
    ap.add_argument("--report", action="store_true", help="BM1_report.html and BM1_summary.json (free)")
    ap.add_argument("--settle", action="store_true", help="what a stopped step left, into the ledger (free)")
    ap.add_argument("--max-usd", type=float, default=None)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    out, data = Path(a.out), Path(a.data)
    global ME
    ME = "python scripts\\bench_mitra.py" + (" --files %s" % a.files if a.files else "") + (
        (' --out "%s"' % a.out) if Path(a.out) != OUT_DEFAULT else "") + (
        (' --data "%s"' % a.data) if Path(a.data) != DATA_DEFAULT else "") + (
        (' --db "%s"' % a.db) if a.db != "data/context.db" else "")
    specs = list(FILES)
    if a.files:
        want = [k.strip() for k in a.files.split(",") if k.strip()]
        bad = [k for k in want if k not in {f["key"] for f in FILES}]
        if bad:
            print("REFUSE: --files: not a BM1 text: %s (they are %s)" % (", ".join(bad), ", ".join(f["key"] for f in FILES)))
            print("VERDICT: nothing done"); print("NEXT: "); return 1
        specs = [f for f in FILES if f["key"] in want]
    if not outside_repos(out):
        print("REFUSE: --out %s is inside a repository: the dataset's text must not be committed" % out)
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    if (a.arm or a.score or a.settle) and not Path(a.db).exists():
        print("REFUSE: %s not found (run from the automaton's folder)" % a.db)
        print("VERDICT: nothing done"); print("NEXT: "); return 1
    if a.sample:
        return do_sample(a, out, data, specs)
    if a.settle:
        return settle(out, a.db)
    sample = load_sample(out)
    if (a.arm or a.score or a.report) and not sample:
        print("REFUSE: no sample in %s" % out); print("VERDICT: nothing done")
        print("NEXT: " + ME + " --sample"); return 1
    if a.arm:
        if not a.yes:
            return status(a, out, data, specs, a.db)
        return run_arm(a, out, sample, specs, a.db)
    if a.score:
        return run_score(a, out, sample, specs, a.db)
    if a.report:
        jp, hp, summ = report(out, sample, specs)
        al = summ["scopes"].get("all", {})
        print("bench_mitra.py  %s  %s  the report (free)" % (MARK, BENCH))
        for k in ("all", "core", "aligned"):
            v = summ["scopes"].get(k) or {}
            if v.get("units"):
                print("  %-7s %d units (%d verses, %d seemingly misaligned): chrF %s; folded %s; judge %s" % (
                    k, v["units"], v["verses"], v.get("misaligned", 0), json.dumps(v["chrf"]), json.dumps(v["chrf_folded"]),
                    json.dumps({x: (y["fidelity"], y["fluency"], y["pass"]) for x, y in v.get("judge", {}).items()})))
        print("VERDICT: written %s and %s%s" % (hp, jp, "" if al.get("units") else " (nothing scored yet)"))
        print("NEXT: start \"\" \"%s\"" % hp)
        return 0
    return status(a, out, data, specs, a.db)


if __name__ == "__main__":
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
