#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge_sample.py — Phase Q4: sampled LLM-judge for SEMANTIC fidelity (2026-08-27).

Heuristic translation_qa measures STRUCTURAL health only (emptiness, ratios, residue,
style). It cannot see whether the meaning is faithful. This adds the semantic layer the
design (docs/QUALITY_LOOP_DESIGN §Q4) specified but never shipped: sample a small % of
translated verses per doc, ask the engine to grade FIDELITY and FLUENCY 1–5 against the
Sanskrit source (+ IAST), and store the verdicts in a new mt_reviews table.

Design guarantees honoured:
  * NON-DESTRUCTIVE — creates mt_reviews (additive); never touches translations.
  * COPYRIGHT — compares only to the stored SOURCE; never fetches/holds any external
    reference translation (Debroy/Gita Press stay eyes-only, per HINDI_TRACK_DESIGN).
  * BOUNDED + DRY-RUN BY DEFAULT — prints the sample size and a cost estimate and does
    NOT call the API unless --yes is given; --limit hard-caps total calls.
  * Writes through db_utils.connect() (WAL + busy_timeout=30000).

Usage:
  python scripts/judge_sample.py --doc MBh01 --sample-pct 5            # dry-run preview
  python scripts/judge_sample.py --doc MBh01 --sample-pct 5 --yes      # run the judge
  python scripts/judge_sample.py --all --sample-pct 3 --limit 400 --yes
  python scripts/judge_sample.py --report                             # aggregate existing verdicts

JUDGE_SCREEN_2026_10_17 (docs/JUDGE_SCREEN_2026-10-17.md): the same judge-v1 by a Claude model (--engine
anthropic:claude-haiku-5-5, on the Claude credit), the screen's filters, a calibration beside another judge's verdicts:
  python scripts/judge_sample.py --all --calibrate --engine anthropic:claude-haiku-5-5            # dry run, free
  python scripts/judge_sample.py --doc MBh01 --sample-pct 100 --limit 8000 --skip-judged --clean-only --engine anthropic:claude-haiku-5-5
"""
from __future__ import annotations
import argparse, json, math, os, re, sys, time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass
try:
    from db_utils import connect as _connect          # WAL + busy_timeout
except Exception:
    import sqlite3
    def _connect(p):
        c = sqlite3.connect(p, timeout=30)
        c.execute("PRAGMA busy_timeout=30000")
        return c

PROMPT_VERSION = "judge-v1"
# Rough Flash pricing: a graded verse is a few hundred tokens in + ~60 out.
COST_PER_CALL_USD = 0.00015
# JUDGE_SCREEN_2026_10_17: what a verdict costs, as billed. Since COST_TRUTH_2026_10_15 counts the thinking Google bills
# as output, the flash judge reads $0.00274 a verdict (2,079 calls on 15 Oct, docs/TRIAGE_2026-10-16.md), not the
# $0.00015 above: every verse of the English kept would be some $60 on the spend cap. The same judge-v1 (this file's
# prompt, read as _judge_one reads it) by Claude Haiku 5.5 was $0.000247 a verdict (74 calls, 15 Oct), on the Claude
# credit, and it is of another family than flash, which made the English. usage_log decides once it has 20 rows.
SCREEN_MARK = "JUDGE_SCREEN_2026_10_17"
METERED_SINCE = "2026-10-15"
JUDGE_PRICES = {"gemini:gemini-2.5-flash": 0.00274, "anthropic:claude-haiku-5-5": 0.00025,
                "anthropic:claude-sonnet-5-5": 0.005, "anthropic:claude-opus-5-5": 0.047}
CLAUDE_JUDGE_MAX_TOKENS = 4000   # as scholar_translate.py's ClaudeCheck.judge: one line; twice it when cut off
DEV_RE = re.compile("[\u0900-\u097f]")
JUNK_RE = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")   # retranslate_marked.py's: Latin letters in the Devanagari

_SYS = (
    "You are a strict, fair Sanskrit-translation quality judge. You are given a Sanskrit "
    "verse (Devanagari, optionally IAST) and a proposed {lang_name} translation. Judge ONLY "
    "the translation against the Sanskrit source — you have no other reference. Score two "
    "axes as integers 1-5:\n"
    "  fidelity = is the MEANING of the Sanskrit preserved (no additions, omissions, "
    "or misreadings)? 5=faithful, 1=wrong/hallucinated.\n"
    "  fluency  = is it natural, readable {lang_name}? 5=elegant, 1=broken.\n"
    "Reply with ONE LINE of minified JSON, no whitespace, no code fence, reason first "
    "so scores are never lost to truncation:\n"
    '{{"reason":"<=10 words","fidelity":<1-5>,"fluency":<1-5>}}'
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _ensure_reviews(con):
    con.execute("""
      CREATE TABLE IF NOT EXISTS mt_reviews(
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        passage_id     INTEGER NOT NULL,
        lang           TEXT NOT NULL DEFAULT 'en',
        engine         TEXT,
        prompt_version TEXT,
        score_fidelity INTEGER,
        score_fluency  INTEGER,
        comment        TEXT,
        created_at     TEXT,
        FOREIGN KEY(passage_id) REFERENCES passages(id)
      )""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_mt_reviews_passage ON mt_reviews(passage_id, lang)")
    con.commit()


def _cols(con, t):
    return {r[1] for r in con.execute(f"PRAGMA table_info({t})")}


def _candidates(con, lang, doc, sample_pct, min_per_doc, keep=None):   # JUDGE_SCREEN_2026_10_17: keep
    pc = _cols(con, "passages")
    has_iast = "iast" in pc
    has_vref = "verse_ref" in pc
    iast_sel = "p.iast" if has_iast else "NULL"
    vref_sel = "p.verse_ref" if has_vref else "NULL"
    # doc filter
    where_doc = "AND d.code = ?" if doc else ""
    params = [doc] if doc else []
    if lang == "en":
        sql = f"""SELECT p.id, d.code, {vref_sel}, p.text, {iast_sel}, p.translation
                  FROM passages p JOIN docs d ON d.id = p.doc_id
                  WHERE TRIM(COALESCE(p.translation,'')) <> '' {where_doc}
                  ORDER BY d.code, p.page_no, p.idx"""
    else:
        sql = f"""SELECT p.id, d.code, {vref_sel}, p.text, {iast_sel}, l.translation
                  FROM passages p JOIN docs d ON d.id = p.doc_id
                  JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = ?
                  WHERE TRIM(COALESCE(l.translation,'')) <> '' {where_doc}
                  ORDER BY d.code, p.page_no, p.idx"""
        params = [lang] + params
    rows = con.execute(sql, params).fetchall()
    if keep is not None:   # JUDGE_SCREEN_2026_10_17: what the screen leaves out goes before the sample is drawn
        rows = [r for r in rows if keep(r)]
    # group by doc, systematic (stratified-by-position) sample
    bydoc = {}
    for r in rows:
        bydoc.setdefault(r[1], []).append(r)
    picked = []
    for code, rs in bydoc.items():
        n = len(rs)
        target = max(min_per_doc, math.ceil(n * sample_pct / 100.0))
        target = min(target, n)
        step = max(1, n // target)
        sample = rs[::step][:target]
        picked.extend(sample)
    return picked


# ---- JUDGE_SCREEN_2026_10_17 ----------------------------------------------------------------------------------------
def judge_price(con, engine):
    """$ a verdict by this engine: usage_log's own (kind judge, since METERED_SINCE, the thinking counted) once it has
    20 rows; else JUDGE_PRICES (the dearest there for an engine not in it)."""
    eng = str(engine or "").split("@", 1)[0]
    try:
        r = con.execute("SELECT COUNT(*), SUM(cost_usd) FROM usage_log WHERE kind = 'judge' AND engine = ? AND ts >= ?",
                        (eng, METERED_SINCE)).fetchone()
        if r and r[0] and r[0] >= 20 and r[1]:
            return float(r[1]) / r[0]
    except Exception:
        pass
    return JUDGE_PRICES.get(eng, max(JUDGE_PRICES.values()))


class ClaudeJudge:
    """judge-v1 by a Claude model, read as scholar_translate.py's ClaudeCheck.judge reads it: this file's system
    prompt, the same message, one line of JSON; asked once more with twice the room when it is cut off before its
    scores. generate_content() answers as Gemini's model does, for _judge_one(). Each answer is metered on the Claude
    credit (claude_engine.meter: usage_log, kind judge); .con and .doc say where; .spent sums it. Built first: without
    the key or the SDK it raises RuntimeError, and nothing is called."""
    credit_metered = True

    def __init__(self, engine, lang_name="English", con=None, sdk=None):
        import claude_engine as ce
        try:
            model, effort = ce.parse_engine(engine)
        except ValueError as e:
            raise RuntimeError(str(e))
        self.ce, self.con, self.doc, self.engine = ce, con, "", engine
        self.client = ce.Client(model, effort, sdk=sdk)
        self.system = _SYS.format(lang_name=lang_name)
        self.spent = 0.0

    def _once(self, prompt, maxtok):
        t0 = time.time()
        resp = self.client.create(self.system, prompt, maxtok)
        txt = self.ce.text_of(resp)
        self.spent += self.ce.meter(self.con, "judge", self.doc, self.client.model, getattr(resp, "usage", None),
                                    time.time() - t0, bool(txt))
        return txt, self.ce.stop_of(resp)

    def generate_content(self, prompt):
        txt, stop = self._once(prompt, CLAUDE_JUDGE_MAX_TOKENS)
        if stop == "max_tokens" and not re.search(r'"fluency"\s*:\s*[1-5]', txt or ""):   # its scores not read
            txt, stop = self._once(prompt, 2 * CLAUDE_JUDGE_MAX_TOKENS)
        return argparse.Namespace(text=txt, candidates=[argparse.Namespace(finish_reason=stop)])


def _gemini_model(engine, lang_name):
    """The Gemini judge as main() builds it (its system prompt, JSON out, temperature 0). RuntimeError without the SDK
    or the key: nothing is called."""
    try:
        import google.generativeai as genai
    except Exception:
        raise RuntimeError("google-generativeai not installed")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    try:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048, response_mime_type="application/json")
    except TypeError:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048)
    name = engine.split(":", 1)[1] if ":" in engine else engine
    return genai.GenerativeModel(model_name=name, generation_config=cfg,
                                 system_instruction=_SYS.format(lang_name=lang_name))


def _read_ids(path):
    """{passage id: its line} from a file of ids: a number a line, or JSON lines with passage_id (a calibration's)."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except ValueError:
                continue
            if isinstance(r, int) and not isinstance(r, bool):
                out[r] = {}
            elif isinstance(r, dict) and isinstance(r.get("passage_id"), int):
                out[r["passage_id"]] = r
    return out


def _tat(con):
    return "p.translated_at" if "translated_at" in _cols(con, "passages") else "NULL"


def _other_verdicts(con, lang, engine):
    """{passage id: its verdict (judge-v1) by another engine than this one, made after the English it read}."""
    out = {}
    for pid, eng, fid, flu, why, at, t in con.execute(
            "SELECT m.passage_id, m.engine, m.score_fidelity, m.score_fluency, m.comment, m.created_at, %s FROM "
            "mt_reviews m JOIN passages p ON p.id = m.passage_id WHERE m.lang = ? AND m.prompt_version = ? ORDER BY m.id"
            % _tat(con), (lang, PROMPT_VERSION)):
        out[pid] = {"engine": eng or "", "fidelity": fid, "fluency": flu, "why": why or "", "at": at or "", "tat": t or ""}
    want = str(engine or "").split("@", 1)[0]
    return {pid: v for pid, v in out.items() if v["fidelity"] is not None and v["engine"].split("@", 1)[0] != want
            and (lang != "en" or not v["tat"] or str(v["at"])[:19] >= str(v["tat"])[:19])}


def _judged(con, lang):
    """The passages with a verdict (judge-v1) made after the English it read."""
    out = set()
    for pid, at, t in con.execute(
            "SELECT m.passage_id, MAX(m.created_at), %s FROM mt_reviews m JOIN passages p ON p.id = m.passage_id WHERE "
            "m.lang = ? AND m.prompt_version = ? AND m.score_fidelity IS NOT NULL GROUP BY m.passage_id" % _tat(con),
            (lang, PROMPT_VERSION)):
        if lang != "en" or not t or str(at or "")[:19] >= str(t)[:19]:
            out.add(pid)
    return out


def screen_keep(con, args):
    """(keep(row) for _candidates, {why left out: n}, {passage id: the other judge's verdict} for a calibration,
    {passage id: its line} of --only-ids or None). OSError when --only-ids cannot be read."""
    cal = bool(getattr(args, "calibrate", False))
    only = _read_ids(args.only_ids) if getattr(args, "only_ids", None) else None
    other = _other_verdicts(con, args.lang, args.engine) if cal else {}
    judged = _judged(con, args.lang) if getattr(args, "skip_judged", False) and not cal else set()
    clean = bool(getattr(args, "clean_only", False))
    why = {}

    def left(reason):
        why[reason] = why.get(reason, 0) + 1
        return False

    def keep(row):
        pid, src = row[0], row[3] or ""
        if only is not None and pid not in only:
            return False
        if cal and pid not in other:
            return False
        if pid in judged:
            return left("a verdict (%s) newer than its English: --skip-judged" % PROMPT_VERSION)
        if clean and len(DEV_RE.findall(src)) >= 8 and JUNK_RE.search(src):
            return left("its Sanskrit carries OCR debris: the source first (--clean-only)")
        return True
    return keep, why, other, only


def _calibration(args, got):
    """A calibration's files in --out-dir (calibrate_<model>.jsonl, the latest, a dated copy beside it, and
    calibrate_<model>_disagree.jsonl: where one judge marks a passage, fidelity 2 or less, and the other does not),
    and what they say."""
    from pathlib import Path
    slug = re.sub(r"[^A-Za-z0-9.\-]", "", args.engine.split(":", 1)[-1].split("@", 1)[0]) or "judge"
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    both = [r for r in got if r["fidelity"] is not None and r["other_fidelity"] is not None]
    dis = [r for r in both if (r["fidelity"] <= 2) != (r["other_fidelity"] <= 2)]
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in got)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_f, dis_f = out / ("calibrate_%s.jsonl" % slug), out / ("calibrate_%s_disagree.jsonl" % slug)
    for p in (main_f, out / ("calibrate_%s_%s.jsonl" % (slug, stamp))):
        p.write_text(body, encoding="utf-8")
    dis_f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in dis), encoding="utf-8")
    n = len(both)
    if not n:
        print("CALIBRATION: no pair of verdicts to compare. Nothing was written to mt_reviews.")
        return
    others = ", ".join(sorted({r["other_engine"] for r in both}))
    om = sum(1 for r in both if r["other_fidelity"] <= 2)
    tm = sum(1 for r in both if r["fidelity"] <= 2)
    bm = sum(1 for r in both if r["fidelity"] <= 2 and r["other_fidelity"] <= 2)
    same = sum(1 for r in both if r["fidelity"] == r["other_fidelity"])
    near = sum(1 for r in both if abs(r["fidelity"] - r["other_fidelity"]) <= 1)
    mo = sum(r["other_fidelity"] for r in both) / n
    mt = sum(r["fidelity"] for r in both) / n
    print("CALIBRATION (%s): %s beside %s on %d passage(s)" % (PROMPT_VERSION, args.engine, others, n))
    print("  marked (fidelity 2 or less): by both %d; by the other only %d; by this one only %d; by neither %d"
          % (bm, om - bm, tm - bm, n - om - tm + bm))
    print("  of the other's %d mark(s), this one finds %d%s" % (om, bm, (" (%.0f%%)" % (100.0 * bm / om)) if om else ""))
    print("  the same score %d (%.0f%%); within one %d (%.0f%%); mean fidelity %.2f (the other) and %.2f (this one)"
          % (same, 100.0 * same / n, near, 100.0 * near / n, mo, mt))
    tri = [r for r in both if r.get("prev_fidelity") is not None and (r["prev_fidelity"] <= 2) != (r["other_fidelity"] <= 2)]
    if tri:
        so = sum(1 for r in tri if (r["fidelity"] <= 2) == (r["other_fidelity"] <= 2))
        print("  where %s and %s disagree (%d): this one sides with %s in %d, with %s in %d"
              % (tri[0]["other_engine"], tri[0]["prev_engine"], len(tri), tri[0]["other_engine"], so,
                 tri[0]["prev_engine"], len(tri) - so))
    print("  files: %s; where they disagree (%d): %s" % (main_f, len(dis), dis_f))
    print("  Nothing was written to mt_reviews.")


def _screen(con, args, picked, price, lang_name, other, only):
    """A run by a Claude judge, a calibration, or a run with --max-usd: judge-v1 as main() runs it, each call gated
    (the Claude credit, or the spend cap) and capped (--max-usd). A calibration writes its files, not mt_reviews."""
    claude = args.engine.startswith("anthropic:")
    try:   # a reason in IAST to a console or a file in cp1252 is not an error of the run
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    try:
        model = ClaudeJudge(args.engine, lang_name, con) if claude else _gemini_model(args.engine, lang_name)
    except RuntimeError as e:
        print(f"REFUSE: {e}. Nothing was called.")
        con.close()
        sys.exit(2)
    try:
        from usage_meter import meter as _meter
    except Exception:
        _meter = None
    try:
        from usage_meter import budget_ok as _bok
    except Exception:
        _bok = None
    now = datetime.now(timezone.utc).isoformat()
    ok = err = 0
    spend_usd, stopped, got = 0.0, "", []
    for i, (pid, code, vref, src, iast, tr) in enumerate(picked, 1):
        if args.max_usd is not None and spend_usd + price > args.max_usd:
            stopped = "this run's --max-usd $%.2f is reached ($%.4f spent)" % (args.max_usd, spend_usd)
            break
        if claude:
            if not model.ce.budget_ok(con, price):
                stopped = "the Claude credit is spent or expired (python scripts\\claude_engine.py --credit shows it)"
                break
            model.doc = code
        elif _bok is not None and not _bok(args.db):
            stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        before = model.spent if claude else 0.0
        try:
            _t0 = time.time()
            fid, flu, reason = _judge_one(model, lang_name, src, iast, tr)
            if not claude and _meter is not None:
                _r, _inc, _outc = getattr(_judge_one, "last", (None, 0, 0))
                spend_usd += _meter(kind="judge", doc=code, engine=args.engine, resp=_r, in_chars=_inc,
                                    out_chars=_outc, units=1, duration_s=time.time() - _t0, con=con)
            if args.calibrate:
                o = other.get(pid) or {}
                rec = {"passage_id": pid, "doc": code, "ref": vref or "", "text": src or "", "english": tr or "",
                       "engine": args.engine, "fidelity": fid, "fluency": flu, "why": reason,
                       "other_engine": o.get("engine", ""), "other_fidelity": o.get("fidelity"),
                       "other_fluency": o.get("fluency"), "other_why": o.get("why", ""), "at": now, "mark": SCREEN_MARK}
                prev = (only or {}).get(pid) or {}
                if prev.get("engine") and prev.get("fidelity") is not None:
                    rec["prev_engine"], rec["prev_fidelity"] = prev["engine"], prev["fidelity"]
                got.append(rec)
            else:
                # idempotent: replace any prior verdict for this (passage, lang, judge version), as main() does
                con.execute("DELETE FROM mt_reviews WHERE passage_id=? AND lang=? AND prompt_version=?",
                            (pid, args.lang, PROMPT_VERSION))
                con.execute(
                    "INSERT INTO mt_reviews(passage_id,lang,engine,prompt_version,"
                    "score_fidelity,score_fluency,comment,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (pid, args.lang, args.engine, PROMPT_VERSION, fid, flu, reason, now))
                con.commit()
            ok += 1
            print(f"  [{i}/{len(picked)}] {code} {vref or ''} fid={fid} flu={flu}: {reason[:60]}")
        except Exception as e:
            err += 1
            print(f"  [{i}/{len(picked)}] {code}: ERROR {type(e).__name__}: {e}")
        if claude:
            spend_usd += model.spent - before
        if args.sleep:
            time.sleep(args.sleep)
    if stopped:
        print("  STOPPED: " + stopped)
    print(f"\nDone. graded={ok} errors={err}.  MEASURED spend this run: ${spend_usd:.4f}"
          + (f" (${spend_usd/ok:.5f}/verse)" if ok else "")
          + f"   [pre-flight estimate was ${len(picked) * price:.4f}]")
    if args.calibrate:
        _calibration(args, got)
    else:
        print(f"Aggregate: python scripts/judge_sample.py --report --lang {args.lang}")
    con.close()


def _judge_one(model, lang_name, src, iast, translation):
    parts = [f"SANSKRIT:\n{src}"]
    if iast:
        parts.append(f"IAST:\n{iast}")
    parts.append(f"{lang_name.upper()} TRANSLATION:\n{translation}")
    prompt = "\n\n".join(parts)
    resp = model.generate_content(prompt)
    try:
        txt = (resp.text or "").strip()
    except Exception:
        txt = ""
    _judge_one.last = (resp, len(prompt), len(txt))   # for the caller's cost meter
    # strip ```json ... ``` fences the model adds despite instructions
    if txt.startswith("```"):
        txt = re.sub(r"^```[A-Za-z]*\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt).strip()
    d = None
    try:
        d = json.loads(txt)
    except Exception:
        m = _JSON_RE.search(txt)
        if m:
            try: d = json.loads(m.group(0))
            except Exception: d = None
    if not isinstance(d, dict):
        # Salvage the integer scores by regex even if the JSON was truncated mid-string
        # (2.5-* thinking models can hit MAX_TOKENS in the reason field). Scores are what
        # matter; a lost reason is acceptable, a lost score is not.
        fm = re.search(r'"fidelity"\s*:\s*([1-5])', txt)
        um = re.search(r'"fluency"\s*:\s*([1-5])', txt)
        rm = re.search(r'"reason"\s*:\s*"([^"]*)', txt)
        if fm or um:
            return (int(fm.group(1)) if fm else None,
                    int(um.group(1)) if um else None,
                    (rm.group(1)[:200] if rm else "[salvaged from truncated JSON]"))
        fr = None
        try: fr = resp.candidates[0].finish_reason
        except Exception: pass
        return None, None, f"[parse-fail fr={fr}] {txt[:80]}"
    def _int(v):
        try: return int(v)
        except Exception: return None
    return _int(d.get("fidelity")), _int(d.get("fluency")), str(d.get("reason", ""))[:200]


def cmd_report(con, lang):
    _ensure_reviews(con)
    rows = con.execute("""
      SELECT d.code, COUNT(*) n,
             ROUND(AVG(r.score_fidelity),2) fid, ROUND(AVG(r.score_fluency),2) flu,
             SUM(CASE WHEN r.score_fidelity <= 2 THEN 1 ELSE 0 END) low_fid
      FROM mt_reviews r JOIN passages p ON p.id = r.passage_id JOIN docs d ON d.id = p.doc_id
      WHERE r.lang = ?
      GROUP BY d.code ORDER BY fid
    """, [lang]).fetchall()
    if not rows:
        print(f"No mt_reviews yet for lang={lang}. Run a judge pass first."); return
    print(f"{'doc':40s} {'n':>5} {'fidelity':>9} {'fluency':>8} {'fid<=2':>7}")
    print("-" * 74)
    for code, n, fid, flu, low in rows:
        print(f"{(code or '')[:40]:40s} {n:>5} {str(fid):>9} {str(flu):>8} {low:>7}")
    by = con.execute("SELECT r.engine, COUNT(*), ROUND(AVG(r.score_fidelity),2), SUM(CASE WHEN r.score_fidelity <= 2 "
                     "THEN 1 ELSE 0 END) FROM mt_reviews r WHERE r.lang = ? GROUP BY r.engine ORDER BY r.engine",
                     [lang]).fetchall()
    if len(by) > 1:   # JUDGE_SCREEN_2026_10_17: which judge read them
        print("by judge: " + "; ".join("%s %d (fidelity %s, %d at 2 or less)" % (e or "?", k, f, lo or 0)
                                       for e, k, f, lo in by))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="single doc code; omit with --all for whole corpus")
    ap.add_argument("--all", action="store_true", help="sample across all docs")
    ap.add_argument("--lang", default="en", help="'en' (passages.translation) or 'hi' (translations_l10n)")
    ap.add_argument("--engine", default="gemini:gemini-2.5-flash")
    ap.add_argument("--sample-pct", type=float, default=5.0)
    ap.add_argument("--min-per-doc", type=int, default=3)
    ap.add_argument("--limit", type=int, default=400, help="hard cap on total judged verses")
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--report", action="store_true", help="print aggregate verdicts and exit")
    ap.add_argument("--yes", action="store_true", help="actually call the API (default is dry-run)")
    # JUDGE_SCREEN_2026_10_17
    ap.add_argument("--skip-judged", action="store_true",
                    help="leave out a passage with a verdict (judge-v1) made after its English")
    ap.add_argument("--clean-only", action="store_true",
                    help="leave out a passage whose Sanskrit carries Latin letters (OCR debris): the source first")
    ap.add_argument("--only-ids", default=None,
                    help="only these passages: a file of ids (a number a line, or JSON lines with passage_id)")
    ap.add_argument("--calibrate", action="store_true",
                    help="read again what another judge read (judge-v1, on the English it read) and compare; writes "
                         "data/retranslate/judge_screen/calibrate_<model>*.jsonl and nothing in mt_reviews")
    ap.add_argument("--max-usd", type=float, default=None, help="stop before this run spends more than this")
    ap.add_argument("--out-dir", default="data/retranslate/judge_screen",
                    help="where a calibration writes its files (inside data/retranslate/: kept local, as the T2 logs)")
    args = ap.parse_args()

    if not args.doc and not args.all and not args.report:
        ap.error("specify --doc <code>, or --all, or --report")

    con = _connect(args.db)
    if args.report:
        cmd_report(con, args.lang); con.close(); return

    _ensure_reviews(con)
    lang_name = {"en": "English", "hi": "Hindi"}.get(args.lang, args.lang)
    try:   # JUDGE_SCREEN_2026_10_17: what the screen leaves out; a calibration reads what another judge read
        keep, why_left, other, only = screen_keep(con, args)
    except OSError as e:
        print(f"REFUSE: --only-ids: {e}"); con.close(); return
    picked = _candidates(con, args.lang, args.doc, 100.0 if args.calibrate else args.sample_pct, args.min_per_doc, keep)
    if args.calibrate and not picked:
        print("REFUSE: nothing to calibrate on: no passage here has a verdict (%s) of another judge on the English it "
              "read" % PROMPT_VERSION); con.close(); return
    if len(picked) > args.limit:
        print(f"[cap] sample {len(picked)} > --limit {args.limit}; taking first {args.limit}.")
        picked = picked[:args.limit]

    price = judge_price(con, args.engine)   # JUDGE_SCREEN_2026_10_17: as measured, the thinking counted
    est = len(picked) * price
    print(f"lang={args.lang}  engine={args.engine}  sample={len(picked)} verses  "
          f"~${est:.3f} est.  ({'LIVE' if args.yes else 'DRY-RUN'})")
    print(f"  ${price:.5f} a verdict ({SCREEN_MARK}: usage_log's own since {METERED_SINCE}, else as measured)")
    for _w, _n in sorted(why_left.items(), key=lambda kv: -kv[1]):
        print(f"  left out: {_n} ({_w})")
    if args.calibrate:
        print(f"  CALIBRATION: {len(picked)} passage(s) another judge read; nothing is written to mt_reviews")
    if args.engine.startswith("anthropic:"):
        try:
            import claude_engine as _ce
            print("  " + _ce.credit_line(_ce.credit(con)))
        except Exception as _e:
            print(f"  the Claude credit cannot be read ({_e})")
    if not args.yes:
        by = {}
        for r in picked:
            by[r[1]] = by.get(r[1], 0) + 1
        for code, n in sorted(by.items()):
            print(f"  {code[:40]:40s} {n}")
        print("Re-run with --yes to grade these. Nothing was called or written.")
        con.close(); return

    if args.engine.startswith("anthropic:") or args.calibrate or args.max_usd is not None:   # JUDGE_SCREEN_2026_10_17
        return _screen(con, args, picked, price, lang_name, other, only)
    model_name = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine
    try:
        import google.generativeai as genai
    except Exception:
        print("google-generativeai not installed.", file=sys.stderr); sys.exit(2)
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set in .env", file=sys.stderr); sys.exit(2)
    genai.configure(api_key=key)
    try:   # METER_GATES_2026_10_04
        from usage_meter import budget_ok as _bok
        if not _bok(args.db):
            print("Refusing: the spend cap is reached."); con.close(); return
    except Exception:
        pass
    # response_mime_type forces pure JSON (no ``` fence); max_output_tokens must be
    # generous because gemini-2.5-* spend "thinking" tokens from this same budget —
    # 120 truncated the JSON, which is why the first pilot returned all-None (2026-08-27).
    try:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048,
                                     response_mime_type="application/json")
    except TypeError:  # older SDK without response_mime_type
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048)
    model = genai.GenerativeModel(model_name=model_name, generation_config=cfg,
                                  system_instruction=_SYS.format(lang_name=lang_name))

    now = datetime.now(timezone.utc).isoformat()
    ok = err = 0
    spend_usd = 0.0
    try:
        from usage_meter import meter as _meter
    except Exception:
        _meter = None
    for i, (pid, code, vref, src, iast, tr) in enumerate(picked, 1):
        try:
            _t0 = time.time()
            fid, flu, reason = _judge_one(model, lang_name, src, iast, tr)
            # 2026-08-29: the QA judge is itself a paid model call. It used to
            # cost money that never appeared in usage_log or against the cap.
            if _meter is not None:
                _r, _inc, _outc = getattr(_judge_one, "last", (None, 0, 0))
                spend_usd += _meter(kind="judge", doc=code, engine=args.engine,
                                    resp=_r, in_chars=_inc, out_chars=_outc,
                                    units=1, duration_s=time.time() - _t0, con=con)
            # idempotent: replace any prior verdict for this (passage, lang, judge version)
            con.execute("DELETE FROM mt_reviews WHERE passage_id=? AND lang=? AND prompt_version=?",
                        (pid, args.lang, PROMPT_VERSION))
            con.execute(
                "INSERT INTO mt_reviews(passage_id,lang,engine,prompt_version,"
                "score_fidelity,score_fluency,comment,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (pid, args.lang, args.engine, PROMPT_VERSION, fid, flu, reason, now))
            con.commit()
            ok += 1
            tag = f"fid={fid} flu={flu}"
            print(f"  [{i}/{len(picked)}] {code} {vref or ''} {tag}: {reason[:60]}")
        except Exception as e:
            err += 1
            print(f"  [{i}/{len(picked)}] {code}: ERROR {type(e).__name__}: {e}")
        time.sleep(args.sleep)

    print(f"\nDone. graded={ok} errors={err}.  MEASURED spend this run: ${spend_usd:.4f}"
          + (f" (${spend_usd/ok:.5f}/verse)" if ok else "")
          + f"   [pre-flight estimate was ${est:.4f}]")
    print(f"Aggregate: python scripts/judge_sample.py --report --lang {args.lang}")
    con.close()


if __name__ == "__main__":
    main()
