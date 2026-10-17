#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
retranslate_marked.py  (2026-10-14)  T2_2026_10_14

The passages the LLM judge marked (fidelity 2 or less) translated again with the stronger engine, then judged again.
A dry run by default (free): what it would do, and what it costs. --yes runs it, capped by --max-usd.

Which: the latest English verdict of each passage, fidelity --max-fidelity (2) or less, of a translation that has not
changed since the judge read it. Left out, and listed: the verdicts that blame the Sanskrit (garbled, OCR, corrupt,
illegible) and the passages whose Devanagari carries Latin letters (Tesseract's misreads): there the source is mended
first; and the texts withdrawn from the site.

How, for each, with --yes:
  1. translate_passages.py --doc D --only-page P --only-idx I --retranslate --engine E (gemini:gemini-2.5-pro): the
     old English goes to translation_history, as with every re-translation;
  2. the judge (judge_sample.py's prompt and model, judge-v1) reads the new English; its verdict replaces the old,
     as judge_sample.py does;
  3. the old English and verdict and the new ones are written to data/retranslate/<stamp>.jsonl;
  4. a passage the new English does not mend (fidelity 2 or less again) is listed for a person to read.
It stops before a passage would take this run past --max-usd (what usage_log says it has spent), when the spend cap
is reached, and it stops while the dashboard writes the same text. The Hindi of a mended passage is made again too
(it was made with the old English beside it); --no-hindi leaves it.

  python scripts\\retranslate_marked.py                               every marked passage: the dry run, free
  python scripts\\retranslate_marked.py --doc Mallapurana             one text
  python scripts\\retranslate_marked.py --doc Mallapurana --yes --max-usd 0.10

JUDGE_SCREEN_2026_10_17 (docs/JUDGE_SCREEN_2026-10-17.md): --engine and --judge-engine may be Claude's
(anthropic:claude-sonnet-5-5, anthropic:claude-haiku-5-5): priced by their own rows in usage_log (else by the model's
prices on BM1's one pass), stopped when the Claude credit is; a run in which nothing bills Google (both Claude's, and
--no-hindi) is not stopped by the spend cap. The dry run's NEXT carries the options it was given.
  python scripts\\retranslate_marked.py --doc markandeya_purana --engine anthropic:claude-sonnet-5-5 --judge-engine anthropic:claude-haiku-5-5 --no-hindi
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

MARK = "T2_2026_10_14"
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
PY = sys.executable
ENGINE = "gemini:gemini-2.5-pro"
JUDGE = "gemini:gemini-2.5-flash"
JUDGE_PROMPT = "judge-v1"
JUDGE_COST = 0.00025     # $ a judged passage, measured on 12 Oct (201 calls, $0.049); usage_log decides
JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")
DEV = re.compile("[\u0900-\u097f]")
SOURCE_BLAMED = re.compile(r"garbl|corrupt|typo|ocr|illegib|damaged|unclear w|source (text )?is", re.I)


def open_ro(db: str):
    return sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def usd(x: float) -> str:
    return "$%.2f" % x if x >= 0.995 else ("$%.3f" % x if x >= 0.0095 else "$%.4f" % x)


def withdrawn(path: Path) -> set:
    last = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        pass
    return {d for d, s in last.items() if s == "withdrawn"}


def marked(con, doc: str | None, max_fid: int, gone: set) -> tuple:
    """(to translate again, left out with the reason): one dict a passage."""
    sql = ("SELECT d.code, p.id, p.page_no, p.idx, p.text, p.iast, p.translation, p.translated_at, m.score_fidelity, "
           "m.comment, m.created_at FROM mt_reviews m JOIN passages p ON p.id = m.passage_id JOIN docs d ON "
           "d.id = p.doc_id WHERE m.lang = 'en' AND m.id = (SELECT MAX(m2.id) FROM mt_reviews m2 WHERE m2.passage_id = "
           "m.passage_id AND m2.lang = 'en') AND m.score_fidelity IS NOT NULL AND m.score_fidelity <= ? AND d.code NOT "
           "LIKE '%-RETIRED'")
    args = [max_fid]
    if doc:
        sql += " AND d.code = ?"
        args.append(doc)
    todo, left = [], []
    for code, pid, pg, idx, text, iast, tr, tat, fid, why, rat in con.execute(sql + " ORDER BY d.code, p.page_no, p.idx",
                                                                                args):
        x = {"doc": code, "id": pid, "page": pg, "idx": idx, "where": "%s.%s" % (pg, idx), "text": text or "",
             "iast": iast or "", "english": tr or "", "fidelity": fid, "why": why or "", "judged_at": rat or ""}
        if code in gone:
            x["left"] = "withdrawn from the site"
        elif not (tr or "").strip():
            x["left"] = "no English now"
        elif tat and rat and str(tat)[:19] > str(rat)[:19]:
            x["left"] = "translated again since the judge read it"
        elif len(DEV.findall(text or "")) >= 8 and JUNK.search(text or ""):
            x["left"] = "its Sanskrit carries OCR debris: the source first"
        elif SOURCE_BLAMED.search(why or ""):
            x["left"] = "the judge blames the Sanskrit: the source first"
        (left if x.get("left") else todo).append(x)
    return todo, left


def prices(con) -> tuple:
    """($ a passage on the stronger engine, $ a judged passage, $ a Hindi passage), from usage_log."""
    flash = 0.00048
    try:
        import redeem
        _by, flash, pro = redeem.spend_by_doc(con)
    except Exception:
        pro = 0.00099
    judge = JUDGE_COST
    try:
        r = con.execute("SELECT SUM(cost_usd), COUNT(*) FROM usage_log WHERE kind='judge'").fetchone()
        if r and r[1] and r[1] >= 50 and r[0]:
            judge = float(r[0]) / r[1]
    except sqlite3.Error:
        pass
    return pro, judge, flash


def claude_prices(con, engine: str, judge_engine: str, pro: float, judge: float) -> tuple:
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
    """$ of this text's translation and judge calls in usage_log after mark, as recorded."""
    try:
        con = open_ro(db)
        try:
            r = con.execute("SELECT SUM(cost_usd) FROM usage_log WHERE kind IN ('translation','judge') AND doc=? AND "
                            "id > ?", (doc, mark)).fetchone()
        finally:
            con.close()
        return float((r or [0])[0] or 0.0)
    except sqlite3.Error:
        return 0.0


def usage_mark(db: str) -> int:
    try:
        con = open_ro(db)
        try:
            return int(con.execute("SELECT MAX(id) FROM usage_log").fetchone()[0] or 0)
        finally:
            con.close()
    except sqlite3.Error:
        return 0


def translate_one(a, x: dict, lang: str = "en") -> int:
    """translate_passages.py on one verse, again (the old translation goes to translation_history)."""
    argv = [PY, str(SCRIPTS / "translate_passages.py"), "--db", a.db, "--doc", x["doc"], "--only-page", str(x["page"]),
            "--only-idx", str(x["idx"]), "--retranslate", "--min-quality", "0", "--sleep", "0", "--lang", lang]
    if lang == "en":
        argv += ["--engine", a.engine]
    r = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode


def judge_model(engine: str):
    """judge_sample.py's model, as it builds it (its system prompt, JSON out, temperature 0). RuntimeError when the
    key or the SDK is missing: nothing is called."""
    if str(engine or "").startswith("anthropic:"):   # JUDGE_SCREEN_2026_10_17: judge-v1 by Claude, on the Claude credit
        import judge_sample as js
        return js.ClaudeJudge(engine, "English", None)
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set (.env)")
    try:
        import judge_sample as js
        import google.generativeai as genai
    except ImportError as e:
        raise RuntimeError("the judge cannot be loaded (%s): pip install google-generativeai" % e)
    genai.configure(api_key=key)
    try:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048, response_mime_type="application/json")
    except TypeError:
        cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=2048)
    name = engine.split(":", 1)[1] if ":" in engine else engine
    return genai.GenerativeModel(model_name=name, generation_config=cfg,
                                 system_instruction=js._SYS.format(lang_name="English"))


def judge_one(a, model, x: dict, english: str, con) -> tuple:
    """(fidelity, fluency, reason) of the new English; the verdict replaces the old (judge-v1), as judge_sample does."""
    import judge_sample as js
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
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    con.execute("DELETE FROM mt_reviews WHERE passage_id=? AND lang='en' AND prompt_version=?", (x["id"], JUDGE_PROMPT))
    con.execute("INSERT INTO mt_reviews(passage_id, lang, engine, prompt_version, score_fidelity, score_fluency, comment, "
                "created_at) VALUES (?,?,?,?,?,?,?,?)", (x["id"], "en", a.judge_engine, JUDGE_PROMPT, fid, flu,
                                                          (why or "")[:200], now))
    con.commit()
    return fid, flu, why


def busy_with(doc: str):
    """The dashboard's jobs running or queued on this text that write it (None when the dashboard does not answer)."""
    try:
        import repair_text as rt
        jobs = rt.dashboard_jobs()
    except Exception:
        return None
    if jobs is None:
        return None
    return [j for j in jobs if j.get("doc") == doc and j.get("kind") != "ocr"]


def run(a, todo: list, pro: float, judge_cost: float, translate=None, judge=None, model=None, flash: float = 0.00048) -> dict:
    """The --yes run over todo. translate(a, x, lang) and judge(a, model, x, english, con) can be stubs (the tests)."""
    translate = translate or translate_one
    judge = judge or judge_one
    each = pro + judge_cost + (0.0 if a.no_hindi else flash)
    out = {"mended": [], "not_mended": [], "failed": [], "stopped": ""}
    if model is None and judge is judge_one:
        model = judge_model(a.judge_engine)   # first: without a key or the SDK nothing is called or written
    logp = Path(a.log_dir) / ("%s_%s.jsonl" % (datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), a.only or "all"))
    logp.parent.mkdir(parents=True, exist_ok=True)
    mark = usage_mark(a.db)
    try:
        from usage_meter import budget_ok
    except Exception:
        budget_ok = None
    import db_utils
    con = db_utils.connect(a.db)
    try:
        claude = [e for e in (a.engine, a.judge_engine) if str(e or "").startswith("anthropic:")]   # JUDGE_SCREEN_2026_10_17
        google = not (len(claude) == 2 and a.no_hindi)   # nothing in this run bills Google: its spend cap does not stop it
        for i, x in enumerate(todo, 1):
            if google and budget_ok is not None and not budget_ok(a.db):
                out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
            if claude and not credit_ok(con, each):
                out["stopped"] = "the Claude credit is spent or expired (python scripts\\claude_engine.py --credit shows it)"
                break
            spent = sum(spent_since(a.db, d, mark) for d in {y["doc"] for y in todo})
            if spent + each > a.max_usd:
                out["stopped"] = "this run's --max-usd $%.2f is reached ($%.4f spent)" % (a.max_usd, spent)
                break
            busy = busy_with(x["doc"])
            if busy:
                out["stopped"] = ("the dashboard writes %s now (%s): run this when it is done"
                                  % (x["doc"], ", ".join(str(j.get("kind")) for j in busy)))
                break
            rc = translate(a, x, "en")
            row = con.execute("SELECT translation FROM passages WHERE id=?", (x["id"],)).fetchone()
            new = (row[0] if row else "") or ""
            rec = {"doc": x["doc"], "where": x["where"], "passage_id": x["id"], "old_english": x["english"],
                   "old_fidelity": x["fidelity"], "old_why": x["why"], "engine": a.engine, "rc": rc, "mark": MARK}
            if rc != 0 or not new.strip() or new.strip() == x["english"].strip():
                rec["result"] = "failed" if rc != 0 or not new.strip() else "unchanged"
                out["failed"].append("%s %s" % (x["doc"], x["where"]))
                print("  (%d/%d) %s %s: %s" % (i, len(todo), x["doc"], x["where"], rec["result"]))
            else:
                fid, flu, why = judge(a, model, x, new, con)
                rec.update(new_english=new, new_fidelity=fid, new_fluency=flu, new_why=why, judge=a.judge_engine)
                ok = fid is not None and fid >= 3
                rec["result"] = "mended" if ok else "not mended"
                (out["mended"] if ok else out["not_mended"]).append("%s %s" % (x["doc"], x["where"]))
                print("  (%d/%d) %s %s: fidelity %s -> %s%s" % (i, len(todo), x["doc"], x["where"], x["fidelity"], fid,
                                                               "" if ok else "  (a person should read it)"))
                if ok and not a.no_hindi:
                    rec["hindi_rc"] = translate(a, x, "hi")
            with open(logp, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        con.close()
    out["log"] = str(logp)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", dest="only", default=None)
    ap.add_argument("--max-fidelity", type=int, default=2)
    ap.add_argument("--engine", default=ENGINE)
    ap.add_argument("--judge-engine", default=JUDGE)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--max-usd", type=float, default=0.50)
    ap.add_argument("--no-hindi", action="store_true", help="leave the Hindi of a mended passage as it is")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--log-dir", default="data/retranslate")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    con = open_ro(a.db)
    try:
        todo, left = marked(con, a.only, a.max_fidelity, withdrawn(Path(a.verdicts)))
        pro, judge_cost, flash = prices(con)
        pro, judge_cost = claude_prices(con, a.engine, a.judge_engine, pro, judge_cost)   # JUDGE_SCREEN_2026_10_17
    finally:
        con.close()
    todo = todo[:a.limit]
    est = len(todo) * (pro + judge_cost + (0.0 if a.no_hindi else flash))
    print("retranslate_marked.py  %s  %s   engine %s (%s a passage), judge %s (%s a passage)"
          % (MARK, "RUN" if a.yes else "DRY RUN (nothing called, nothing written)", a.engine, usd(pro),
             a.judge_engine, usd(judge_cost)))
    by = {}
    for x in todo:
        by[x["doc"]] = by.get(x["doc"], 0) + 1
    for d, n in sorted(by.items()):
        print("  %-52s %d to translate again" % (d[:52], n))
    for x in todo[:12]:
        print("    %s %s  fidelity %s: %s" % (x["doc"][:30], x["where"], x["fidelity"], x["why"][:90]))
    reasons = {}
    for x in left:
        reasons[x["left"]] = reasons.get(x["left"], 0) + 1
    for r, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("  left out: %d (%s)" % (n, r))
    if not todo:
        print("VERDICT: nothing the judge marked can be translated again now%s" %
              ("; %d left out" % len(left) if left else ""))
        print("NEXT: python scripts\\judge_sample.py --doc MBh01 --sample-pct 2 --limit 40   (judge more: the dry run, free)"
              if not left else "NEXT: python scripts\\judge_review.py   (read what the judge marks)")
        return 0
    if not a.yes:
        cap = max(0.10, round(est * 1.25 + 0.005, 2))
        print("VERDICT: %d passage(s) to translate again and judge again, about %s; %d left out"
              % (len(todo), usd(est), len(left)))
        print("NEXT: python scripts\\retranslate_marked.py%s%s --yes --max-usd %.2f"
              % ((" --doc %s" % a.only) if a.only else "", same_flags(a), cap))   # JUDGE_SCREEN_2026_10_17: its options
        return 0
    try:
        res = run(a, todo, pro, judge_cost, flash=flash)
    except RuntimeError as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing called"); print("NEXT: "); return 1
    if res["stopped"]:
        print("  STOPPED: %s" % res["stopped"])
    print("VERDICT: %d mended, %d not mended (a person should read them), %d failed; the log: %s"
          % (len(res["mended"]), len(res["not_mended"]), len(res["failed"]), res["log"]))
    print("NEXT: python scripts\\judge_review.py%s   (what the judge says now)" % ((" --doc %s" % a.only) if a.only else ""))
    if res["mended"] and a.no_hindi:
        print("ALSO: their Hindi was made beside the old English; it is left as it is (--no-hindi)")
    return 0


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
