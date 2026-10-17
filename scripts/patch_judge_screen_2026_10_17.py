#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_judge_screen_2026_10_17.py  (2026-10-17)  JUDGE_SCREEN_2026_10_17

Asked on 17 Oct: has the translation already paid for (gemini-2.5-flash, about $37 of it) been properly analysed and
redeemed? What was measured on all of it is the reading it was made from (REDEEM_2026_10_14: 84% of 26,589 English
from a clean reading). Its meaning was read by the judge on 240 passages (0.9%), in 7 texts. Reading every verse with
the flash judge costs what Google bills with its thinking, $0.00274 a verdict (docs/TRIAGE_2026-10-16.md): some $60.
The same judge-v1 by Claude Haiku 5.5 was $0.000247 a verdict, on the Claude credit, and it is of another family than
the model that made the English. This lets it be used, and measured first (docs/JUDGE_SCREEN_2026-10-17.md).

scripts/judge_sample.py (needs METER_GATES_2026_10_04):
  --engine anthropic:<model>: judge-v1 by Claude (this file's prompt and reading; asked again with twice the room when
    cut off, as scholar_translate.py's ClaudeCheck.judge), metered on the Claude credit and stopped by it;
  --skip-judged (leave out a passage with a verdict newer than its English), --clean-only (leave out a passage whose
    Sanskrit carries Latin letters: the source first), --only-ids FILE, --max-usd;
  --calibrate: read again the passages another judge read, on the English it read, compare, and write
    data/retranslate/judge_screen/calibrate_<model>.jsonl (a dated copy beside it) and calibrate_<model>_disagree.jsonl; nothing is
    written to mt_reviews. Given a calibration's file (--only-ids), a third judge says whom it sides with;
  the dry run prices a verdict as measured (usage_log's own rows since 15 Oct, the thinking counted), says what it
    leaves out and why, and the credit; --report adds a line by judge when there is more than one.
  A run as before (flash, no new option) runs as before.
scripts/retranslate_marked.py (needs T2_2026_10_14): --engine and --judge-engine may be Claude's (priced by their own
  rows, stopped by the credit); a run in which nothing bills Google is not stopped by the spend cap; the dry run's NEXT
  carries its options.

Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_judgescreen_<date>. No database change; nothing is called.
  python scripts\\patch_judge_screen_2026_10_17.py --check
  python scripts\\patch_judge_screen_2026_10_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'JUDGE_SCREEN_2026_10_17'
NEEDS = {'scripts/judge_sample.py': 'METER_GATES_2026_10_04', 'scripts/retranslate_marked.py': 'T2_2026_10_14'}
FILES = list(NEEDS)
TAG = 'judgescreen'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/judge_sample.py', 1, r'''  python scripts/judge_sample.py --report                             # aggregate existing verdicts
''', r'''  python scripts/judge_sample.py --report                             # aggregate existing verdicts

JUDGE_SCREEN_2026_10_17 (docs/JUDGE_SCREEN_2026-10-17.md): the same judge-v1 by a Claude model (--engine
anthropic:claude-haiku-5-5, on the Claude credit), the screen's filters, a calibration beside another judge's verdicts:
  python scripts/judge_sample.py --all --calibrate --engine anthropic:claude-haiku-5-5            # dry run, free
  python scripts/judge_sample.py --doc MBh01 --sample-pct 100 --limit 8000 --skip-judged --clean-only --engine anthropic:claude-haiku-5-5
''')

edit('scripts/judge_sample.py', 2, r'''COST_PER_CALL_USD = 0.00015
''', r'''COST_PER_CALL_USD = 0.00015
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
''')

edit('scripts/judge_sample.py', 3, r'''def _candidates(con, lang, doc, sample_pct, min_per_doc):
''', r'''def _candidates(con, lang, doc, sample_pct, min_per_doc, keep=None):   # JUDGE_SCREEN_2026_10_17: keep
''')

edit('scripts/judge_sample.py', 4, r'''    rows = con.execute(sql, params).fetchall()
    # group by doc, systematic (stratified-by-position) sample
''', r'''    rows = con.execute(sql, params).fetchall()
    if keep is not None:   # JUDGE_SCREEN_2026_10_17: what the screen leaves out goes before the sample is drawn
        rows = [r for r in rows if keep(r)]
    # group by doc, systematic (stratified-by-position) sample
''')

edit('scripts/judge_sample.py', 5, r'''def _judge_one(model, lang_name, src, iast, translation):
''', r'''# ---- JUDGE_SCREEN_2026_10_17 ----------------------------------------------------------------------------------------
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
''')

edit('scripts/judge_sample.py', 6, r'''    for code, n, fid, flu, low in rows:
        print(f"{(code or '')[:40]:40s} {n:>5} {str(fid):>9} {str(flu):>8} {low:>7}")
''', r'''    for code, n, fid, flu, low in rows:
        print(f"{(code or '')[:40]:40s} {n:>5} {str(fid):>9} {str(flu):>8} {low:>7}")
    by = con.execute("SELECT r.engine, COUNT(*), ROUND(AVG(r.score_fidelity),2), SUM(CASE WHEN r.score_fidelity <= 2 "
                     "THEN 1 ELSE 0 END) FROM mt_reviews r WHERE r.lang = ? GROUP BY r.engine ORDER BY r.engine",
                     [lang]).fetchall()
    if len(by) > 1:   # JUDGE_SCREEN_2026_10_17: which judge read them
        print("by judge: " + "; ".join("%s %d (fidelity %s, %d at 2 or less)" % (e or "?", k, f, lo or 0)
                                       for e, k, f, lo in by))
''')

edit('scripts/judge_sample.py', 7, r'''    ap.add_argument("--yes", action="store_true", help="actually call the API (default is dry-run)")
''', r'''    ap.add_argument("--yes", action="store_true", help="actually call the API (default is dry-run)")
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
''')

edit('scripts/judge_sample.py', 8, r'''    picked = _candidates(con, args.lang, args.doc, args.sample_pct, args.min_per_doc)
''', r'''    try:   # JUDGE_SCREEN_2026_10_17: what the screen leaves out; a calibration reads what another judge read
        keep, why_left, other, only = screen_keep(con, args)
    except OSError as e:
        print(f"REFUSE: --only-ids: {e}"); con.close(); return
    picked = _candidates(con, args.lang, args.doc, 100.0 if args.calibrate else args.sample_pct, args.min_per_doc, keep)
    if args.calibrate and not picked:
        print("REFUSE: nothing to calibrate on: no passage here has a verdict (%s) of another judge on the English it "
              "read" % PROMPT_VERSION); con.close(); return
''')

edit('scripts/judge_sample.py', 9, r'''    est = len(picked) * COST_PER_CALL_USD
''', r'''    price = judge_price(con, args.engine)   # JUDGE_SCREEN_2026_10_17: as measured, the thinking counted
    est = len(picked) * price
''')

edit('scripts/judge_sample.py', 10, r'''          f"~${est:.3f} est.  ({'LIVE' if args.yes else 'DRY-RUN'})")
    if not args.yes:
''', r'''          f"~${est:.3f} est.  ({'LIVE' if args.yes else 'DRY-RUN'})")
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
''')

edit('scripts/judge_sample.py', 11, r'''    model_name = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine
''', r'''    if args.engine.startswith("anthropic:") or args.calibrate or args.max_usd is not None:   # JUDGE_SCREEN_2026_10_17
        return _screen(con, args, picked, price, lang_name, other, only)
    model_name = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine
''')

edit('scripts/retranslate_marked.py', 1, r'''  python scripts\\retranslate_marked.py --doc Mallapurana --yes --max-usd 0.10
"""
''', r'''  python scripts\\retranslate_marked.py --doc Mallapurana --yes --max-usd 0.10

JUDGE_SCREEN_2026_10_17 (docs/JUDGE_SCREEN_2026-10-17.md): --engine and --judge-engine may be Claude's
(anthropic:claude-sonnet-5-5, anthropic:claude-haiku-5-5): priced by their own rows in usage_log (else by the model's
prices on BM1's one pass), stopped when the Claude credit is; a run in which nothing bills Google (both Claude's, and
--no-hindi) is not stopped by the spend cap. The dry run's NEXT carries the options it was given.
  python scripts\\retranslate_marked.py --doc markandeya_purana --engine anthropic:claude-sonnet-5-5 --judge-engine anthropic:claude-haiku-5-5 --no-hindi
"""
''')

edit('scripts/retranslate_marked.py', 2, r'''def judge_model(engine: str):
    """judge_sample.py's model, as it builds it (its system prompt, JSON out, temperature 0). RuntimeError when the
    key or the SDK is missing: nothing is called."""
''', r'''def judge_model(engine: str):
    """judge_sample.py's model, as it builds it (its system prompt, JSON out, temperature 0). RuntimeError when the
    key or the SDK is missing: nothing is called."""
    if str(engine or "").startswith("anthropic:"):   # JUDGE_SCREEN_2026_10_17: judge-v1 by Claude, on the Claude credit
        import judge_sample as js
        return js.ClaudeJudge(engine, "English", None)
''')

edit('scripts/retranslate_marked.py', 3, r'''    import judge_sample as js
    t0 = time.time()
    fid, flu, why = js._judge_one(model, "English", x["text"], x["iast"], english)
    try:
        from usage_meter import meter
        r, inc, outc = getattr(js._judge_one, "last", (None, 0, 0))
        meter(kind="judge", doc=x["doc"], engine=a.judge_engine, resp=r, in_chars=inc, out_chars=outc, units=1,
              duration_s=time.time() - t0, con=con)
    except Exception:
        pass
''', r'''    import judge_sample as js
    claude = bool(getattr(model, "credit_metered", False))   # JUDGE_SCREEN_2026_10_17: a Claude judge meters itself
    if claude:
        model.con, model.doc = con, x["doc"]
    t0 = time.time()
    fid, flu, why = js._judge_one(model, "English", x["text"], x["iast"], english)
    try:
        from usage_meter import meter
        r, inc, outc = getattr(js._judge_one, "last", (None, 0, 0))
        if not claude:
            meter(kind="judge", doc=x["doc"], engine=a.judge_engine, resp=r, in_chars=inc, out_chars=outc, units=1,
                  duration_s=time.time() - t0, con=con)
    except Exception:
        pass
''')

edit('scripts/retranslate_marked.py', 4, r'''def spent_since(db: str, doc: str, mark: int) -> float:
''', r'''def claude_prices(con, engine: str, judge_engine: str, pro: float, judge: float) -> tuple:
    """JUDGE_SCREEN_2026_10_17: ($ a passage translated, $ a verdict) when either engine is Claude's: usage_log's own
    rows of the model since the credit began (20 or more), else the model's prices on BM1's one pass (1,584 tokens in,
    202 out a verse: Sonnet $0.0052) and judge_sample.py's price of a verdict. Gemini's, as they were."""
    def measured(kind, eng):
        try:
            r = con.execute("SELECT COUNT(*), SUM(cost_usd) FROM usage_log WHERE kind = ? AND engine = ? AND ts >= ?",
                            (kind, eng, "2026-10-15")).fetchone()
            if r and r[0] and r[0] >= 20 and r[1]:
                return float(r[1]) / r[0]
        except sqlite3.Error:
            pass
        return None
    if str(engine or "").startswith("anthropic:"):
        try:
            import claude_engine as ce
            model, _effort = ce.parse_engine(engine)
            p = ce.prices_of(model)
            pro = measured("translation", ce.PREFIX + model) or (1584 * p[0] + 202 * p[1]) / 1e6
        except Exception:
            pro = 0.0052
    if str(judge_engine or "").startswith("anthropic:"):
        try:
            import judge_sample as js
            judge = js.judge_price(con, judge_engine)
        except Exception:
            judge = 0.00025
    return pro, judge


def credit_ok(con, next_cost: float) -> bool:
    """JUDGE_SCREEN_2026_10_17: the Claude credit allows the next passage (claude_engine.budget_ok; it fails closed)."""
    try:
        import claude_engine as ce
    except ImportError:
        return False
    return ce.budget_ok(con, next_cost)


def same_flags(a) -> str:
    """JUDGE_SCREEN_2026_10_17: the options of this dry run that its NEXT must carry (none with the defaults)."""
    out = ""
    if a.engine != ENGINE:
        out += " --engine %s" % a.engine
    if a.judge_engine != JUDGE:
        out += " --judge-engine %s" % a.judge_engine
    if a.max_fidelity != 2:
        out += " --max-fidelity %d" % a.max_fidelity
    if a.limit != 200:
        out += " --limit %d" % a.limit
    if a.no_hindi:
        out += " --no-hindi"
    return out


def spent_since(db: str, doc: str, mark: int) -> float:
''')

edit('scripts/retranslate_marked.py', 5, r'''        for i, x in enumerate(todo, 1):
            if budget_ok is not None and not budget_ok(a.db):
                out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
''', r'''        claude = [e for e in (a.engine, a.judge_engine) if str(e or "").startswith("anthropic:")]   # JUDGE_SCREEN_2026_10_17
        google = not (len(claude) == 2 and a.no_hindi)   # nothing in this run bills Google: its spend cap does not stop it
        for i, x in enumerate(todo, 1):
            if google and budget_ok is not None and not budget_ok(a.db):
                out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
            if claude and not credit_ok(con, each):
                out["stopped"] = "the Claude credit is spent or expired (python scripts\\claude_engine.py --credit shows it)"
                break
''')

edit('scripts/retranslate_marked.py', 6, r'''        pro, judge_cost, flash = prices(con)
''', r'''        pro, judge_cost, flash = prices(con)
        pro, judge_cost = claude_prices(con, a.engine, a.judge_engine, pro, judge_cost)   # JUDGE_SCREEN_2026_10_17
''')

edit('scripts/retranslate_marked.py', 7, r'''        print("NEXT: python scripts\\retranslate_marked.py%s --yes --max-usd %.2f"
              % ((" --doc %s" % a.only) if a.only else "", cap))
''', r'''        print("NEXT: python scripts\\retranslate_marked.py%s%s --yes --max-usd %.2f"
              % ((" --doc %s" % a.only) if a.only else "", same_flags(a), cap))   # JUDGE_SCREEN_2026_10_17: its options
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


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
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_judge_screen_2026_10_17 tests.test_redeem_2026_10_14 tests.test_meter_gates_2026_10_04')
    print('  python scripts\\judge_sample.py --all --calibrate --engine anthropic:claude-haiku-5-5   (the dry run, free)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
