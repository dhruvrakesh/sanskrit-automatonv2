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

_SYS = (
    "You are a strict, fair Sanskrit-translation quality judge. You are given a Sanskrit "
    "verse (Devanagari, optionally IAST) and a proposed {lang_name} translation. Judge ONLY "
    "the translation against the Sanskrit source — you have no other reference. Score two "
    "axes as integers 1-5:\n"
    "  fidelity = is the MEANING of the Sanskrit preserved (no additions, omissions, "
    "or misreadings)? 5=faithful, 1=wrong/hallucinated.\n"
    "  fluency  = is it natural, readable {lang_name}? 5=elegant, 1=broken.\n"
    "Reply with STRICT JSON only, no prose, no code fence:\n"
    '{{"fidelity": <1-5>, "fluency": <1-5>, "reason": "<=15 words"}}'
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


def _candidates(con, lang, doc, sample_pct, min_per_doc):
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


def _judge_one(model, lang_name, src, iast, translation):
    parts = [f"SANSKRIT:\n{src}"]
    if iast:
        parts.append(f"IAST:\n{iast}")
    parts.append(f"{lang_name.upper()} TRANSLATION:\n{translation}")
    resp = model.generate_content("\n\n".join(parts))
    try:
        txt = (resp.text or "").strip()
    except Exception:
        txt = ""
    m = _JSON_RE.search(txt)
    if not m:
        return None, None, (txt[:120] or "[no output]")
    try:
        d = json.loads(m.group(0))
        f = int(d.get("fidelity")) if d.get("fidelity") is not None else None
        u = int(d.get("fluency"))  if d.get("fluency")  is not None else None
        return f, u, str(d.get("reason", ""))[:200]
    except Exception:
        return None, None, txt[:120]


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
    args = ap.parse_args()

    if not args.doc and not args.all and not args.report:
        ap.error("specify --doc <code>, or --all, or --report")

    con = _connect(args.db)
    if args.report:
        cmd_report(con, args.lang); con.close(); return

    _ensure_reviews(con)
    lang_name = {"en": "English", "hi": "Hindi"}.get(args.lang, args.lang)
    picked = _candidates(con, args.lang, args.doc, args.sample_pct, args.min_per_doc)
    if len(picked) > args.limit:
        print(f"[cap] sample {len(picked)} > --limit {args.limit}; taking first {args.limit}.")
        picked = picked[:args.limit]

    est = len(picked) * COST_PER_CALL_USD
    print(f"lang={args.lang}  engine={args.engine}  sample={len(picked)} verses  "
          f"~${est:.3f} est.  ({'LIVE' if args.yes else 'DRY-RUN'})")
    if not args.yes:
        by = {}
        for r in picked:
            by[r[1]] = by.get(r[1], 0) + 1
        for code, n in sorted(by.items()):
            print(f"  {code[:40]:40s} {n}")
        print("Re-run with --yes to grade these. Nothing was called or written.")
        con.close(); return

    model_name = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine
    try:
        import google.generativeai as genai
    except Exception:
        print("google-generativeai not installed.", file=sys.stderr); sys.exit(2)
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set in .env", file=sys.stderr); sys.exit(2)
    genai.configure(api_key=key)
    cfg = genai.GenerationConfig(temperature=0.0, max_output_tokens=120)
    model = genai.GenerativeModel(model_name=model_name, generation_config=cfg,
                                  system_instruction=_SYS.format(lang_name=lang_name))

    now = datetime.now(timezone.utc).isoformat()
    ok = err = 0
    for i, (pid, code, vref, src, iast, tr) in enumerate(picked, 1):
        try:
            fid, flu, reason = _judge_one(model, lang_name, src, iast, tr)
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

    print(f"\nDone. graded={ok} errors={err}. Aggregate: python scripts/judge_sample.py --report --lang {args.lang}")
    con.close()


if __name__ == "__main__":
    main()
