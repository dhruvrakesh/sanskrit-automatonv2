#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
corpus_status.py  (2026-10-04)  CORPUS_STATUS_2026_10_04 + CORPUS_STATUS2_2026_10_04

READ-ONLY. One question, answered per text: "is this text up to date with what
the pipeline can do today, and if not, what is the next command?"

WHAT v1 GOT WRONG (first run on the live corpus, 2026-10-04 09:16)
------------------------------------------------------------------
v1 judged "the source is damaged" from LACUNA RATES. That is the wrong evidence:

  * It sent books to OCR for Hindi lacunae alone (vasishtha_dhanur_veda: en 0.0%,
    hi 72.7%) - lacunae that older Hindi prompts produce, which a prompt re-run
    can remove.
  * It sent untranslated Tesseract books (Rgveda Vol-ii, Pataal Khanda, 19,071
    passages) straight to TRANSLATION: no translation means no lacunae, so v1
    saw "clean". Translating Tesseract debris is the most expensive mistake
    available here.
  * It could not see that nilamata_seg is DERIVED (resegment_doc.py) from
    upapurana_nilamata_purana, so it proposed vision on a doc code with no page
    PDFs in inbox.
  * It recommended vision for books whose page PDFs are not in inbox at all.

v2 measures the source directly. SOURCE DEBRIS = share of passages (with at
least 8 Devanagari characters) that contain Latin-letter runs inside the
Devanagari, the same JUNK test diag_hindi_ab.py uses. Calibrated on page files
on 2026-10-04, per text line:

    Tesseract  10% - 71%   (Ganita 10.3, Karan 13.5, Rgveda 53.9, bodhyana 70.9)
    vision      0% -  2%   (Shatpath 0.0, Rgveda 0.5, Sandilya 1.8; Mallapurana 10.4
                            because of plate captions and 5 refused pages)
    e-text      0%         (MBh01, GRETIL)

so --debris-ok defaults to 5%. Provenance comes from the page files themselves:
engine 'resegment-devnum' with meta.src_doc marks a derived doc (evidence, not
inference - the lesson diag_corpus_overlap.py records about row-count matching).

VERDICTS, in pipeline order, so the next step is never premature
  DERIVED-NEEDS-OCR   derived doc whose text carries debris: repair OCR on the
                      source doc, re-ingest it, re-derive with resegment_doc.py.
  NEEDS-OCR           debris above --debris-ok and under half the passages from
                      vision; page PDFs are in inbox. Consensus first; no
                      translation is recommended until it is done.
  NO-SOURCE-PDF       same, but inbox has no page PDFs for this code. Upload or
                      split the source PDF first.
  NEEDS-REINGEST      raw_merged exists and the DB is behind it.
  NEEDS-TRANSLATION   rows without English/Hindi, or lacuna rows above --lacuna-ok.
  AGED                complete and clean; some rows on older prompt versions.
  CURRENT             complete, current, clean.

Costs beside each command are estimates: vision at $0.0015/page (planning
figure; measured $0.0003-$0.0014, retries to $0.005), translation at the
measured average $/passage in usage_log (kind='translation'). cost_tracker
prices gemini-2.5-flash at the 2025 list price, so treat $ as a lower bound.

  python scripts\\corpus_status.py
  python scripts\\corpus_status.py --doc markandeya_purana
  python scripts\\corpus_status.py --commands | Out-File -Encoding utf8 exports\\next_steps.txt
  python scripts\\corpus_status.py --no-drift --csv exports\\corpus_status.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

MARK = "CORPUS_STATUS_2026_10_04"
MARK2 = "CORPUS_STATUS2_2026_10_04"
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

LACUNA_RE = re.compile(r"\[\s*(?:illegible|\u0905\u0938\u094d\u092a\u0937\u094d\u091f)\s*\]", re.I)
JUNK_RE = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")     # = diag_hindi_ab.JUNK
DEV_RE = re.compile(r"[\u0900-\u097f]")
PAGE_RX = r"^%s_(\d{4})(?:_norm)?\.%s$"
# METER_GATES_2026_10_04: fallback only, used when usage_log has fewer than 5 measured pages.
# Was 0.0015 (the old 2.5 Flash price). CREDITS_COST_2026_10_04: 0.0041 = all provider-metered
# vision since metering began, repriced, per page delivered (retries included), on 2026-10-04.
# (The 0.0054 written here before was not a ledger figure.)
VISION_COST_PER_PAGE = 0.0041
VISION_CPP = {"value": None, "source": "fallback $%.4f" % VISION_COST_PER_PAGE}
CPP_SOURCE = {"source": "?"}
SCOPE = "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"
ENGINE = "gemini:gemini-2.5-flash"


def current_versions() -> tuple[str, str, str]:
    """(en, hi, hi_source) exactly as a translate run would use them now."""
    try:
        import infer_mt
        return (infer_mt.PROMPT_VERSIONS["en"], infer_mt.PROMPT_VERSIONS["hi"],
                getattr(infer_mt, "HI_PROMPT_SOURCE", "built-in"))
    except Exception as e:  # never fail a read-only report on an import
        print("  [warn] infer_mt not importable (%s); prompt currency not judged" % e)
        return ("?", "?", "?")


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def page_files(folder: Path, doc: str, ext: str = "jsonl") -> dict[str, Path]:
    rx = re.compile(PAGE_RX % (re.escape(doc), re.escape(ext)), re.I)
    out: dict[str, Path] = {}
    if folder.is_dir():
        for p in sorted(folder.iterdir()):
            m = rx.match(p.name)
            if m:
                out.setdefault(m.group(1), p)
    return out


def _first(p: Path) -> dict:
    try:
        with open(p, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return json.loads(line) if line else {}
    except Exception:
        return {}


def ocr_files(doc: str, raw: Path, vision: Path, merged: Path, inbox: Path) -> dict:
    t, v, m = page_files(raw, doc), page_files(vision, doc), page_files(merged, doc)
    v_ok = v_refused = 0
    for p in v.values():
        rec = _first(p)
        if (rec.get("text") or "").strip():
            v_ok += 1
        elif (rec.get("meta") or {}).get("finish") in ("RECITATION", "SAFETY"):
            v_refused += 1
    # provenance from the page files themselves (a sample is enough: one doc, one producer)
    engines, src_docs = Counter(), Counter()
    for p in list(t.values())[:40]:
        rec = _first(p)
        engines[(rec.get("engine") or "(none)")] += 1
        sd = (rec.get("meta") or {}).get("src_doc")
        if sd:
            src_docs[sd] += 1
    return {"pages_tesseract": len(t), "pages_vision": v_ok, "pages_refused": v_refused,
            "pages_merged": len(m), "pages_inbox": len(page_files(inbox, doc, "pdf")),
            "raw_engine": engines.most_common(1)[0][0] if engines else "",
            "src_doc": src_docs.most_common(1)[0][0] if src_docs else "", "_merged": m}


def engine_class(e: str | None) -> str:
    e = (e or "").lower()
    if "vision" in e:
        return "vision"
    if "tesseract" in e:
        return "tesseract"
    if "etext" in e or "gretil" in e:
        return "etext"
    return "unrecorded"


def is_debris(text: str) -> bool | None:
    """True/False for a passage with >= 8 Devanagari characters; None otherwise."""
    if len(DEV_RE.findall(text or "")) < 8:
        return None
    return bool(JUNK_RE.search(text))


# GAPS_2026_10_05: passages that cannot be translated as printed are gaps, not work to do.
GAP_MIN_QUALITY = 0.35   # translate_passages.py --min-quality default: below it a passage is never sent


def tried_unusable(path) -> dict:
    """{(doc, lang): {(page, idx)}} from translate_outcomes.jsonl: attempts whose output was unusable
    (every cause except 'salvaged', where the cleaned output was kept). Missing file: {}. Never raises."""
    out: dict = {}
    try:
        fh = open(str(path), encoding="utf-8")
    except (OSError, TypeError):
        return out
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("cause") in (None, "salvaged"):
                continue
            try:
                k = (int(r["page"]), int(r["idx"]))
            except (KeyError, TypeError, ValueError):
                continue
            out.setdefault((str(r.get("doc")), str(r.get("lang") or "en")), set()).add(k)
    return out


def _never_sent(page, text) -> bool:
    """GAPS2_2026_10_07: True when translate_passages.py would skip this passage silently (no call, no
    outcome record): page below 1, should_translate() false, or clean_for_mt() empty. Same functions."""
    try:
        from normalize_text import normalize_sanskrit
        from text_filters import should_translate, clean_for_mt
    except Exception:
        return False
    try:
        if int(page or 0) < 1:
            return True
        normed = normalize_sanskrit(text or "")
        return (not should_translate(normed, min_dev=0.05)) or not clean_for_mt(normed)
    except Exception:
        return False


def gap_measures(con: sqlite3.Connection, doc: str, tried: dict) -> dict:
    """en_gap / hi_gap: untranslated in-scope passages that were tried with unusable output, or that
    translate_passages skips for OCR quality. *_gap_tried, *_gap_lowq split them; *_gap_refs: examples."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    q = "p.quality_score" if "quality_score" in cols else "NULL"
    res: dict = {}
    for lang in ("en", "hi"):
        res.update({lang + "_gap": 0, lang + "_gap_tried": 0, lang + "_gap_lowq": 0, lang + "_gap_refs": [],
                    lang + "_gap_never": 0})   # GAPS2_2026_10_07
    rows = con.execute(
        f"""SELECT p.page_no, p.idx, {q}, TRIM(COALESCE(p.translation,'')) <> '',
                   TRIM(COALESCE(l.translation,'')) <> '', COALESCE(p.text,'')
            FROM passages p JOIN docs d ON d.id = p.doc_id
            LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
            WHERE d.code = ? AND {SCOPE}""", (doc,)).fetchall()
    for page, idx, qs, has_en, has_hi, text in rows:
        try:
            low = qs is not None and 0.0 < float(qs) < GAP_MIN_QUALITY
        except (TypeError, ValueError):
            low = False
        never = None   # computed only for an untranslated row (GAPS2_2026_10_07)
        for lang, has in (("en", has_en), ("hi", has_hi)):
            if has:
                continue
            was_tried = (int(page or 0), int(idx or 0)) in tried.get((doc, lang), ())
            if not (was_tried or low) and never is None:
                never = _never_sent(page, text)
            if was_tried or low or never:
                res[lang + "_gap"] += 1
                res[lang + ("_gap_tried" if was_tried else "_gap_lowq" if low else "_gap_never")] += 1
                if len(res[lang + "_gap_refs"]) < 8:
                    res[lang + "_gap_refs"].append("%s.%s" % (page, idx))
    return res


def db_measures(con: sqlite3.Connection, doc: str, en_ver: str, hi_ver: str) -> dict:
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    eng = "p.ocr_engine" if "ocr_engine" in cols else "NULL"
    rows = con.execute(
        f"""SELECT p.id, {eng}, p.text, p.translation, p.mt_prompt_version, p.translated_at,
                   l.translation, l.mt_prompt_version, l.translated_at
            FROM passages p JOIN docs d ON d.id = p.doc_id
            LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
            WHERE d.code = ? AND {SCOPE}""", (doc,)).fetchall()
    r = Counter({k: 0 for k in ("passages", "ocr_vision", "ocr_tesseract", "ocr_etext", "ocr_unrecorded", "ocr_reseg",
                                "dev_rows", "debris_rows", "en_done", "en_current", "en_lacuna",
                                "hi_done", "hi_current", "hi_lacuna", "hi_ref_older")})
    en_vers, hi_vers = Counter(), Counter()
    for (_pid, oe, text, en, ev, eat, hi, hv, hat) in rows:
        r["passages"] += 1
        r["ocr_" + engine_class(oe)] += 1
        if (oe or "") == "resegment-devnum":
            r["ocr_reseg"] += 1
        d = is_debris(text)
        if d is not None:
            r["dev_rows"] += 1
            r["debris_rows"] += 1 if d else 0
        if en and en.strip():
            r["en_done"] += 1
            en_vers[ev or "(none)"] += 1
            if ev == en_ver:
                r["en_current"] += 1
            if LACUNA_RE.search(en):
                r["en_lacuna"] += 1
        if hi and hi.strip():
            r["hi_done"] += 1
            hi_vers[hv or "(none)"] += 1
            if hv in (hi_ver, hi_ver + "+noref"):
                r["hi_current"] += 1
            if LACUNA_RE.search(hi):
                r["hi_lacuna"] += 1
            if hv and not hv.endswith("+noref") and hat and eat and str(hat) < str(eat):
                r["hi_ref_older"] += 1   # made WITH an English reference that was replaced later
    out = dict(r)
    out["en_versions"] = dict(en_vers.most_common(4))
    out["hi_versions"] = dict(hi_vers.most_common(4))
    return out


def doc_meta(con: sqlite3.Connection, doc: str) -> dict:
    r = con.execute("SELECT category FROM docs WHERE code=?", (doc,)).fetchone()
    return {"category": (r[0] if r else None) or ""}


def image_counts(con: sqlite3.Connection, doc: str) -> dict:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='doc_images'").fetchone():
        return {}
    c = Counter()
    for st, n in con.execute("""SELECT i.status, COUNT(*) FROM doc_images i JOIN docs d ON d.id = i.doc_id
                                WHERE d.code = ? GROUP BY i.status""", (doc,)):
        c[st] = n
    return dict(c)


def translation_cost_per_passage(con: sqlite3.Connection) -> float | None:
    """USD per translated passage at TODAY's prices (METER_GATES_2026_10_04).

    Prefers provider-metered rows (token_source='provider', which count thinking
    tokens and the MAX_TOKENS ladder) once they cover 200+ passages; else every
    row's stored tokens repriced (chars/4 estimates: reads low); else the recorded
    cost, as before, when usage_log has no token columns."""
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(usage_log)")}
        if {"engine", "in_tokens", "out_tokens"} <= cols:
            import cost_tracker

            def priced(rows):
                usd = n = 0.0
                for eng, tin, tout, k in rows:
                    pin, pout = cost_tracker._get_pricing(eng or "")
                    usd += ((tin or 0) * pin + (tout or 0) * pout) / 1e6
                    n += k or 0
                return (usd / n) if n and usd else None
            base = ("SELECT engine, in_tokens, out_tokens, passages FROM usage_log WHERE kind = 'translation' "
                    "AND passages > 0 AND COALESCE(ok, 1) = 1")
            if "token_source" in cols:
                rows = con.execute(base + " AND token_source = 'provider' ORDER BY rowid DESC LIMIT 3000").fetchall()
                if sum(r[3] or 0 for r in rows) >= 200:
                    v = priced(rows)
                    if v:
                        CPP_SOURCE["source"] = "provider tokens, last %d calls, today's prices" % len(rows)
                        return v
            v = priced(con.execute(base).fetchall())
            if v:
                CPP_SOURCE["source"] = "chars/4 estimates repriced (no thinking tokens: reads low)"
                return v
        r = con.execute("""SELECT SUM(cost_usd), SUM(passages) FROM usage_log
                           WHERE kind = 'translation' AND passages > 0 AND COALESCE(ok, 1) = 1""").fetchone()
        CPP_SOURCE["source"] = "recorded cost"
        return (r[0] / r[1]) if r and r[0] and r[1] else None
    except sqlite3.Error:
        return None


def vision_cost_per_page(db: str) -> float | None:
    """METER_GATES_2026_10_04: the same measured figure ocr_consensus uses for --max-usd."""
    try:
        import ocr_consensus
        v = ocr_consensus.measured_cost_per_page(db, fallback=0.0)
    except Exception:
        v = 0.0
    if v:
        VISION_CPP.update(value=v, db=db, source="measured: cost / pages delivered, last 300 vision calls "
                                                  "incl. ladder retries, today's prices; per text where it has its own")
        return v
    VISION_CPP.update(value=None, source="fallback $%.4f (fewer than 5 measured pages)" % VISION_COST_PER_PAGE)
    return None


def _doc_vision_cpp(code: str) -> float:
    """COST_RATIO_2026_10_05: this text's own measured $/page when it has >= 20 delivered pages."""
    base = VISION_CPP["value"] or VISION_COST_PER_PAGE
    db = VISION_CPP.get("db")
    if not db:
        return base
    try:
        import ocr_consensus
        return ocr_consensus.measured_cost_per_page(db, fallback=base, doc=code)
    except Exception:
        return base


def drift_counts(db: str, doc: str, merged: dict) -> dict:
    if not merged:
        return {}
    try:
        import ocr_consensus
        rows = ocr_consensus.drift(Path(db), doc, merged)
    except Exception as e:
        return {"drift_error": "%s: %s" % (type(e).__name__, e)}
    c = Counter(x["status"] for x in rows)
    return {"drift_current": c.get("current", 0), "drift_stale": c.get("stale", 0),
            "drift_missing": c.get("missing-in-db", 0)}


def pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 1) if b else 0.0


def _usd(x: float | None) -> str:
    return "?" if x is None else ("$%.2f" % x)


def consensus_cmds(code: str, s: dict) -> tuple[list[str], float]:
    todo = max(0, s.get("pages_inbox", 0) - s.get("pages_vision", 0) - s.get("pages_refused", 0))
    cpp = _doc_vision_cpp(code)   # COST_RATIO_2026_10_05 (was the corpus-wide figure for every text)
    usd = max(0.05, round(todo * cpp * 1.15 + 0.01, 2))   # 15% headroom: retries and outliers (p90 = 1.12 x mean on 2026-10-04)
    # --include-unassessed: pages OCR'd before 2026-08-30 carry no Tesseract confidence, and triage then
    # fails (seen on markandeya_purana, 2026-10-04 12:21). With it, every inbox page is queued.
    return (["python scripts\\ocr_consensus.py --doc %s --threshold 101 --include-unassessed            # PLAN: no spend" % code,
             "python scripts\\ocr_consensus.py --doc %s --threshold 101 --include-unassessed --yes --max-usd %.2f   # ~%d pages to vision"
             % (code, usd, todo)], todo * cpp)


def verdict(s: dict, lacuna_ok: float, debris_ok: float = 5.0, cpp: float | None = None,
            peers: dict | None = None) -> tuple[str, list[str], list[str]]:
    """(verdict, reasons, commands). Judged only from measured dicts (s, and peers by code)."""
    doc, n = s["doc"], s.get("passages", 0)
    peers = peers or {}
    reasons: list[str] = []
    cmds: list[str] = []
    s["est_usd"] = 0.0
    if n == 0:
        return "EMPTY", ["no passages in scope"], []
    en_lp, hi_lp = pct(s.get("en_lacuna", 0), s.get("en_done", 0)), pct(s.get("hi_lacuna", 0), s.get("hi_done", 0))
    debris = pct(s.get("debris_rows", 0), s.get("dev_rows", 0))
    vision_share = pct(s.get("ocr_vision", 0), n)
    etext = s.get("ocr_etext", 0) > n / 2 or engine_class(s.get("raw_engine")) == "etext"
    damaged = (not etext) and debris > debris_ok and vision_share < 50.0

    # CORPUS_STATUS3_2026_10_04: rows that came from ANOTHER doc's files (the old
    # "<doc>_*.jsonl" glob took <doc>_seg_* too). Evidence: their ocr_engine says
    # resegment-devnum while this doc's own page files do not.
    if s.get("ocr_reseg", 0) and s.get("raw_engine") != "resegment-devnum":
        keep = s.get("derived_by") or "<the derived doc>"
        reasons.append("%d of %d rows carry engine resegment-devnum although this doc's own page files are %s: "
                       "they were ingested from %s's files by the old glob. This doc's text is now a copy "
                       "of %s, not its own." % (s["ocr_reseg"], n, s.get("raw_engine") or "unrecorded", keep, keep))
        cmds += ["python scripts\\diag_retire_check.py --src %s --keep %s" % (doc, keep),
                 "python scripts\\retire_doc.py --doc %s --supersedes %s --dry-run" % (doc, keep),
                 "# only when the check reports zero unmatched verses, after a fresh backup:",
                 "python scripts\\retire_doc.py --doc %s --supersedes %s --yes" % (doc, keep)]
        return "CONTAMINATED", reasons, cmds

    if damaged and s.get("src_doc"):
        # CORPUS_STATUS3_2026_10_04: follow RETIREMENT_AND_BACKUP_POLICY_2026-09-14. The derived
        # doc may hold grafted verses (graft_verses.py) and its source may be RETIRED, so it is
        # never wiped and re-split in place. The repaired text becomes NEW codes; the existing
        # doc is retired only after diag_retire_check passes.
        src = s["src_doc"]
        sp = peers.get(src, {})
        new_src, new_doc = src + "_v2", doc + "_v2"
        reasons.append("source debris %.1f%% of passages; this doc is DERIVED from %s by resegment_doc.py "
                       "(page files say so)%s. The repaired text goes to NEW codes %s / %s; %s is kept until "
                       "diag_retire_check passes (RETIREMENT_AND_BACKUP_POLICY)"
                       % (debris, src, " and %s is retired in the DB" % src if sp.get("retired") else "",
                          new_src, new_doc, doc))
        if sp.get("pages_inbox", 0):
            c, usd = consensus_cmds(src, sp)
            cmds += ["# 1. vision on the SOURCE pages (writes files only, never the DB)"] + c
            s["est_usd"] += usd
        else:
            reasons.append("inbox holds no page PDFs named %s_NNNN.pdf, so vision cannot run on the source" % src)
            cmds += ['python inbox\\split_pdf_pages.py "<source.pdf>" -o inbox -p %s --zero-pad 4' % src]
            return "DERIVED-NEEDS-OCR", reasons, cmds
        cat = s.get("category") or "upapurana"
        cmds += ["# 2. the repaired source as a NEW page-blob doc, then a NEW split (the current docs are untouched)",
                 'python scripts\\ingest_jsonl_fast.py --doc %s --glob "data\\raw_merged\\%s_*.jsonl" --db data\\context.db '
                 '--category %s --no-segment' % (new_src, src, cat),
                 "python scripts\\resegment_doc.py --src-doc %s --new-doc %s --dry-run" % (new_src, new_doc),
                 "python scripts\\resegment_doc.py --src-doc %s --new-doc %s --yes" % (new_src, new_doc),
                 'python scripts\\ingest_jsonl_fast.py --doc %s --glob "data\\raw\\%s_*.jsonl" --db data\\context.db '
                 '--category %s --no-segment' % (new_doc, new_doc, cat),
                 "# 3. translate %s (corpus_status --doc %s prints the commands), then compare and adopt:" % (new_doc, new_doc),
                 "python scripts\\diag_retire_check.py --src %s --keep %s" % (doc, new_doc),
                 "#    graft_verses.py for any verse the check names; then retire_doc.py --doc %s --supersedes %s"
                 % (doc, new_doc),
                 "#    and retire_doc.py --doc %s --supersedes %s (a page-blob source is never translated)"
                 % (new_src, new_doc)]
        return "DERIVED-NEEDS-OCR", reasons, cmds

    if damaged:
        reasons.append("source debris %.1f%% of passages (Tesseract-like; vision is 0-2%%), only %.0f%% of "
                       "passages from vision" % (debris, vision_share))
        if s.get("pages_vision", 0):
            reasons.append("%d page(s) already have vision, %d merged - consensus resumes, done pages are free"
                           % (s["pages_vision"], s.get("pages_merged", 0)))
        if not s.get("pages_inbox", 0):
            reasons.append("inbox holds no page PDFs named %s_NNNN.pdf, so vision cannot run" % doc)
            for alias in s.get("inbox_alias") or []:
                # A HINT, not evidence: a name that contains this code and has the same page count.
                reasons.append("possible source in inbox: %s_NNNN.pdf (%d pages, same count) - open two pages "
                               "and compare before copying" % (alias, s.get("pages_tesseract", 0)))
                cmds += ["# only after checking that %s IS this book:" % alias,
                         "Get-ChildItem inbox -Filter '%s_*.pdf' | ForEach-Object { Copy-Item $_.FullName "
                         "(Join-Path inbox ($_.Name -replace '^%s_', '%s_')) }" % (alias, re.escape(alias), doc),
                         "python scripts\\corpus_status.py --doc %s      # then it prints the consensus commands" % doc]
            if not s.get("inbox_alias"):
                cmds += ["# upload the source PDF in the dashboard (it splits into inbox), or:",
                         'python inbox\\split_pdf_pages.py "<source.pdf>" -o inbox -p %s --zero-pad 4' % doc]
            return "NO-SOURCE-PDF", reasons, cmds
        if s.get("en_done", 0) or s.get("hi_done", 0):
            reasons.append("its %d English / %d Hindi rows were made from this text; re-ingest replaces the text, "
                           "and only changed verses are paid for again" % (s.get("en_done", 0), s.get("hi_done", 0)))
        c, usd = consensus_cmds(doc, s)
        cmds += c; s["est_usd"] += usd
        cmds.append("python scripts\\ocr_consensus.py --doc %s --drift-only     # prints the re-ingest block" % doc)
        return "NEEDS-OCR", reasons, cmds

    if s.get("drift_stale", 0) or s.get("drift_missing", 0):
        reasons.append("DB behind raw_merged: %d stale, %d missing pages"
                       % (s.get("drift_stale", 0), s.get("drift_missing", 0)))
        try:
            import ocr_consensus
            cmds += ocr_consensus.reingest_commands(doc).splitlines()
        except Exception:
            cmds.append("python scripts\\ocr_consensus.py --doc %s --drift-only   # prints the re-ingest block" % doc)
        return "NEEDS-REINGEST", reasons, cmds

    v = "CURRENT"
    # GAPS_2026_10_05: gaps (tried with unusable output, or skipped for OCR quality) are not work to do.
    en_gap, hi_gap = s.get("en_gap", 0), s.get("hi_gap", 0)
    en_todo, hi_todo = n - s.get("en_done", 0) - en_gap, n - s.get("hi_done", 0) - hi_gap

    def add(cmd: str, rows: int):
        cost = (rows * cpp) if cpp else None
        if cost is not None:
            s["est_usd"] += cost
        cmds.append(cmd + "   # %d rows, est %s" % (rows, _usd(cost)))

    base = "python scripts\\translate_passages.py --db data\\context.db --doc %s --engine %s" % (doc, ENGINE)
    if en_todo > 0:
        reasons.append("%d passages without English" % en_todo)
        add(base, en_todo); v = "NEEDS-TRANSLATION"
    if en_lp > lacuna_ok:
        reasons.append("English lacunae %.1f%% > %.1f%%" % (en_lp, lacuna_ok))
        add(base + " --only-lacuna", s.get("en_lacuna", 0)); v = "NEEDS-TRANSLATION"
    if hi_todo > 0:
        reasons.append("%d passages without Hindi" % hi_todo)
        add(base + " --lang hi --reference none", hi_todo); v = "NEEDS-TRANSLATION"
    if hi_lp > lacuna_ok:
        reasons.append("Hindi lacunae %.1f%% > %.1f%% (source is clean, so the prompt can fix these)" % (hi_lp, lacuna_ok))
        add(base + " --lang hi --reference none --only-lacuna", s.get("hi_lacuna", 0)); v = "NEEDS-TRANSLATION"
    for lang, name, gap in (("en", "English", en_gap), ("hi", "Hindi", hi_gap)):   # GAPS_2026_10_05
        if not gap:
            continue
        share = pct(gap + s.get(lang + "_lacuna", 0), n)
        what = ("%d passage(s) without %s cannot be translated as printed (%d tried with unusable output, "
                "%d below OCR quality %.2f, %d never sent: page 0 or no translatable Sanskrit; e.g. %s)"
                % (gap, name, s.get(lang + "_gap_tried", 0), s.get(lang + "_gap_lowq", 0), GAP_MIN_QUALITY,
                   s.get(lang + "_gap_never", 0), ", ".join(s.get(lang + "_gap_refs") or [])))   # GAPS2_2026_10_07
        if share > lacuna_ok:
            reasons.append("%s; with the lacunae that is %.1f%% of passages > %.1f%%" % (what, share, lacuna_ok))
            v = "NEEDS-TRANSLATION"
            cmds.append("# %s gaps are a SOURCE problem (a re-run returns the same). Running heads first:" % name)
            cmds.append("python scripts\\classify_noise.py --doc %s --running-heads --show" % doc)
        else:
            reasons.append("note: %s; counted as gaps (%.1f%% of passages with the lacunae, within %.1f%%)"
                           % (what, share, lacuna_ok))
    if cmds:
        cmds.append("python scripts\\measure_lacunae.py --doc %s" % doc)
    if debris > debris_ok and not etext:
        reasons.append("note: debris %.1f%% but %.0f%% from vision - check the refused/fallback pages"
                       % (debris, vision_share))
    if v == "CURRENT":
        old_en = s.get("en_done", 0) - s.get("en_current", 0)
        old_hi = s.get("hi_done", 0) - s.get("hi_current", 0)
        if old_en or old_hi:
            v = "AGED"
            reasons.append("%d English and %d Hindi rows on older prompt versions (lacunae within %.1f%%)"
                           % (old_en, old_hi, lacuna_ok))
    if s.get("hi_ref_older"):
        reasons.append("%d Hindi rows were made with an English reference that was re-translated later"
                       % s["hi_ref_older"])
    return v, reasons, cmds


def collect(db: str, docs: list[str] | None, raw: Path, vision: Path, merged: Path, inbox: Path = Path("inbox"),
            do_drift: bool = True, min_passages: int = 1,
            outcomes: Path | None = None) -> tuple[list[dict], tuple, dict, float | None]:
    """(stats for the requested docs, versions, all docs' file facts by code (for derived sources), cost/passage)."""
    en_ver, hi_ver, hi_src = current_versions()
    tried = tried_unusable(outcomes if outcomes is not None
                           else Path(db).parent / "translate_outcomes.jsonl")   # GAPS_2026_10_05
    con = open_ro(db)
    try:
        all_codes = [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code")]
        codes = docs or all_codes
        cpp = translation_cost_per_passage(con)
        vision_cost_per_page(db)   # METER_GATES_2026_10_04
        inbox_codes = Counter()
        if inbox.is_dir():
            for p in inbox.iterdir():
                m = re.match(r"^(.+)_(\d{4})\.pdf$", p.name, re.I)
                if m:
                    inbox_codes[m.group(1)] += 1
        out, peers = [], {}
        for code in codes:
            s = {"doc": code}
            s.update(db_measures(con, code, en_ver, hi_ver))
            s.update(gap_measures(con, code, tried))   # GAPS_2026_10_05
            s.update(doc_meta(con, code))
            f = ocr_files(code, raw, vision, merged, inbox)
            s.update(f)
            s["images"] = image_counts(con, code)
            s["inbox_alias"] = sorted(c for c, n in inbox_codes.items()
                                      if c != code and (c.endswith("_" + code) or code.endswith("_" + c))
                                      and n == s.get("pages_tesseract", -1))
            if s.get("passages", 0) >= min_passages:
                out.append(s)
        for s in out:   # facts about a derived doc's source, even when that source is not in the DB
            sd = s.get("src_doc")
            if sd and sd not in peers:
                f = ocr_files(sd, raw, vision, merged, inbox); f.pop("_merged", None)
                f["in_db"] = sd in all_codes
                peers[sd] = f
        try:   # CORPUS_STATUS3_2026_10_04: retired codes (retire_doc.py writes doc_stage 'retired')
            retired = {r[0] for r in con.execute("SELECT doc_code FROM doc_stage WHERE stage='retired'")}
        except sqlite3.Error:
            retired = set()
        for sd, f in peers.items():
            f["retired"] = sd in retired
        by_src = {}
        for s in out:
            if s.get("src_doc"):
                by_src.setdefault(s["src_doc"], s["doc"])
        for s in out:
            if s["doc"] in by_src:
                s["derived_by"] = by_src[s["doc"]]
    finally:
        con.close()
    for s in out:
        m = s.pop("_merged")
        if do_drift:
            s.update(drift_counts(db, s["doc"], m))
    return out, (en_ver, hi_ver, hi_src), peers, cpp


COLS = ["doc", "verdict", "passages", "debris_pct", "vision_pct", "raw_engine", "src_doc", "pages_inbox",
        "pages_tesseract", "pages_vision", "pages_refused", "pages_merged", "drift_stale", "drift_missing",
        "en_done", "en_current", "en_lac_pct", "hi_done", "hi_current", "hi_lac_pct", "hi_ref_older",
        "img_approved", "est_usd", "en_gap", "hi_gap"]


def row_for(s: dict) -> dict:
    return {"doc": s["doc"], "verdict": s["verdict"], "passages": s.get("passages", 0),
            "debris_pct": pct(s.get("debris_rows", 0), s.get("dev_rows", 0)),
            "vision_pct": pct(s.get("ocr_vision", 0), s.get("passages", 0)),
            "raw_engine": s.get("raw_engine", ""), "src_doc": s.get("src_doc", ""),
            "pages_inbox": s.get("pages_inbox", 0),
            "pages_tesseract": s.get("pages_tesseract", 0), "pages_vision": s.get("pages_vision", 0),
            "pages_refused": s.get("pages_refused", 0), "pages_merged": s.get("pages_merged", 0),
            "drift_stale": s.get("drift_stale", ""), "drift_missing": s.get("drift_missing", ""),
            "en_done": s.get("en_done", 0), "en_current": s.get("en_current", 0),
            "en_lac_pct": pct(s.get("en_lacuna", 0), s.get("en_done", 0)),
            "hi_done": s.get("hi_done", 0), "hi_current": s.get("hi_current", 0),
            "hi_lac_pct": pct(s.get("hi_lacuna", 0), s.get("hi_done", 0)),
            "hi_ref_older": s.get("hi_ref_older", 0), "img_approved": (s.get("images") or {}).get("approved", 0),
            "est_usd": round(s.get("est_usd", 0.0), 2),
            "en_gap": s.get("en_gap", 0), "hi_gap": s.get("hi_gap", 0)}   # GAPS_2026_10_05


ORDER = {"CONTAMINATED": -1, "DERIVED-NEEDS-OCR": 0, "NEEDS-OCR": 1, "NO-SOURCE-PDF": 2, "NEEDS-REINGEST": 3,
         "NEEDS-TRANSLATION": 4, "AGED": 5, "CURRENT": 6, "EMPTY": 7}


# ------------------------------------------------------------------ DOC_HINT_2026_10_07
def resolve_docs(db: str, wanted: list | None) -> tuple:
    """(codes to report, notes). Each --doc is checked against the docs table: an exact code is used;
    another case of a code, or the only code that starts with what was given, is used with a note;
    anything else gets a note with the closest codes. 2026-10-07: '--doc Ganita_Yukti_Bhasa' printed
    '0 docs' with no reason (the code is Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V)."""
    if not wanted:
        return wanted, []
    import difflib
    con = open_ro(db)
    try:
        codes = [r[0] for r in con.execute("SELECT code FROM docs ORDER BY code")]
    finally:
        con.close()
    have, low = set(codes), {c.lower(): c for c in codes}
    out, notes = [], []
    for w in wanted:
        lw = w.lower()
        if w in have:
            out.append(w)
        elif lw in low:
            out.append(low[lw]); notes.append("# note: --doc %s -> %s (case)" % (w, low[lw]))
        else:
            pre = [c for c in codes if c.lower().startswith(lw)]
            if len(pre) == 1:
                out.append(pre[0]); notes.append("# note: --doc %s is not a code; using %s" % (w, pre[0]))
            else:
                toks = [t for t in re.split(r"[^0-9a-z]+", lw) if t]
                near = pre[:8] or [c for c in codes if lw in c.lower()][:8] \
                    or [c for c in codes if toks and all(t in c.lower() for t in toks)][:8] \
                    or difflib.get_close_matches(w, codes, n=5, cutoff=0.5)
                notes.append("# note: no text has the code %r.%s" % (
                    w, (" Did you mean: " + ", ".join(near)) if near else " Run without --doc to list every text."))
    return out, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only per-text currency report with next commands")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", action="append", help="repeatable; default all docs")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--lacuna-ok", type=float, default=5.0, help="lacuna rows %% that counts as negligible")
    ap.add_argument("--debris-ok", type=float, default=5.0, help="source-debris passages %% that counts as clean")
    ap.add_argument("--min-passages", type=int, default=20, help="skip docs smaller than this")
    ap.add_argument("--no-drift", action="store_true", help="skip the raw_merged drift check (faster)")
    ap.add_argument("--outcomes", default=None,
                    help="translate_outcomes.jsonl (default: beside the DB) - GAPS_2026_10_05")
    ap.add_argument("--commands", action="store_true", help="print only the recommended commands, in order")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    if args.doc:   # DOC_HINT_2026_10_07
        args.doc, _notes = resolve_docs(args.db, args.doc)
        for _n in _notes:
            print(_n)
        if not args.doc:
            print("# nothing to report: no --doc matched a text."); return 2

    stats, (en_ver, hi_ver, hi_src), peers, cpp = collect(
        args.db, args.doc, Path(args.raw_dir), Path(args.vision_dir), Path(args.merged_dir), Path(args.inbox),
        not args.no_drift, args.min_passages, Path(args.outcomes) if args.outcomes else None)
    by_code = {s["doc"]: s for s in stats}
    for s in stats:
        sd = s.get("src_doc")
        peer = by_code.get(sd) or peers.get(sd) if sd else None
        s["verdict"], s["reasons"], s["commands"] = verdict(s, args.lacuna_ok, args.debris_ok, cpp,
                                                            {sd: peer} if sd and peer else {})
    stats.sort(key=lambda s: (ORDER.get(s["verdict"], 9), -s.get("passages", 0)))

    if args.commands:
        print("# corpus_status %s/%s  en=%s  hi=%s  translation $/passage=%s"
              % (MARK, MARK2, en_ver, hi_ver, ("%.5f" % cpp) if cpp else "?"))
        print("# vision $/page %.4f (%s); translation $/passage from %s"   # METER_GATES_2026_10_04
              % (VISION_CPP["value"] or VISION_COST_PER_PAGE, VISION_CPP["source"], CPP_SOURCE["source"]))
        print("# Back up first:  python scripts\\db_backup.py \"data\\context.db\" "
              "\"D:\\backups\\context_pre_status_$(Get-Date -Format yyyyMMdd_HHmmss).db\"")
        print("# Run one book at a time, only when the dashboard header reads idle; re-run corpus_status after each.")
        for s in stats:
            if s["commands"]:
                print("\n# --- %s  [%s]  est %s  %s" % (s["doc"], s["verdict"], _usd(s.get("est_usd")),
                                                      "; ".join(s["reasons"])))
                for c in s["commands"]:
                    print(c)
        return 0

    print("%s/%s   prompts: en=%s  hi=%s (%s)   lacunae ok <= %.1f%%   debris ok <= %.1f%%   translation $/passage %s"
          % (MARK, MARK2, en_ver, hi_ver, hi_src, args.lacuna_ok, args.debris_ok, ("%.5f" % cpp) if cpp else "?"))
    print("vision $/page %.4f (%s); translation $/passage from %s"   # METER_GATES_2026_10_04
          % (VISION_CPP["value"] or VISION_COST_PER_PAGE, VISION_CPP["source"], CPP_SOURCE["source"]))
    hdr = "%-40s %-18s %6s %5s %4s %5s %6s %6s %6s %6s %6s %4s %8s" % (
        "doc", "verdict", "rows", "deb%", "vis%", "inbox", "en", "en_lac", "hi", "hi_lac", "hi_cur", "img", "est$")
    print(hdr); print("-" * len(hdr))
    for s in stats:
        r = row_for(s)
        print("%-40s %-18s %6d %5.1f %4.0f %5d %6d %5.1f%% %6d %5.1f%% %6d %4d %8.2f" % (
            r["doc"][:40], r["verdict"], r["passages"], r["debris_pct"], r["vision_pct"], r["pages_inbox"],
            r["en_done"], r["en_lac_pct"], r["hi_done"], r["hi_lac_pct"], r["hi_current"], r["img_approved"],
            r["est_usd"]))
    print()
    for s in stats:
        if s["reasons"]:
            print("%s [%s]: %s" % (s["doc"], s["verdict"], "; ".join(s["reasons"])))
    tally = Counter(s["verdict"] for s in stats)
    spend = Counter()
    for s in stats:
        spend[s["verdict"]] += s.get("est_usd", 0.0)
    print("\n%d docs: %s" % (len(stats), ", ".join("%s %d (est $%.2f)" % (k, tally[k], spend[k])
                                                   for k in sorted(tally, key=ORDER.get))))
    print("Next commands:  python scripts\\corpus_status.py --commands")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
            for s in stats:
                w.writerow(row_for(s))
        print("wrote", args.csv)
    if args.json:
        Path(args.json).write_text(json.dumps({"marker": MARK2, "en": en_ver, "hi": hi_ver, "cost_per_passage": cpp,
                                               "docs": stats, "derived_sources": peers},
                                              ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
