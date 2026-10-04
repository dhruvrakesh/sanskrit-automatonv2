#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
diag_hindi_ab.py  (2026-09-30, v2 2026-10-02)  HINDI_REF_AB_2026_09_30  HINDI_AB_ARMS_2026_10_02

MEASURES Hindi translation choices on a deterministic sample. Changes nothing:
mt_cache is bypassed (its key ignores the reference and the prompt text would
make arms identical), nothing is written to mt_cache, passages or
translations_l10n. Spend is metered to api_usage (use --no-meter to skip).

ARMS (one variable at a time; same verse, context, model):
  a  production Hindi prompt  + English reference (when QA-passed)   = today's behaviour
  b  production Hindi prompt  , Sanskrit only
  c  CANDIDATE prompt (--candidate-prompt FILE) + English reference
  d  CANDIDATE prompt , Sanskrit only
Default arms: a,b (the 2026-09-30 test). With --candidate-prompt: a,b,c,d.

POPULATION (--population):
  anchored  verses with a QA-passed English (the 2026-09-30 default)
  lacuna    verses whose STORED Hindi contains the lacuna mark - the rows a fix must repair
  all       every translatable verse with a stored Hindi
Verses without a QA-passed English get no reference in arms a/c either; the
summary reports how many verses actually carried one.

METRICS per arm (local, no second model):
  qa       text_filters.score_translation_quality(src, out, 'hi') - production scorer (saturates near 1.0)
  lacuna   verses whose output contains [asphuta]; tokens = total marks
  conj     marked conjectures U+27E8 ... U+27E9 (the candidate prompt asks for them)
  tatsama  share of output Devanagari words found in the Sanskrit source
  vs_a     character similarity to arm a
Measured noise (2026-10-01, markandeya, same 40 verses, 3 runs): arm a lacuna
15/20/17, arm b 18/18/21. Differences under ~4 per 40 verses are noise; use
--n 80 and pool several books before deciding.

  python scripts\\diag_hindi_ab.py --doc nilamata_seg --population lacuna --n 40 --candidate-prompt prompts\\hi-v4-candidate.txt
  ... add --yes to call the API.
Output: data\\ab\\hindi_ref_<doc>_<stamp>.jsonl and .html
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import html
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

MARK = "HINDI_AB_ARMS_2026_10_02"
DEV_WORD = re.compile(r"[\u0900-\u0963\u0970-\u097f]+")
LACUNA = re.compile(r"\[\s*\u0905\u0938\u094d\u092a\u0937\u094d\u091f\s*\]")
CONJ = re.compile(r"\u27e8[^\u27e9]{1,80}\u27e9")
ARM_LABEL = {"a": "a  production + English ref", "b": "b  production, Sanskrit only",
             "c": "c  candidate + English ref", "d": "d  candidate, Sanskrit only"}


def tatsama_share(src: str, out: str) -> float:
    s = set(w for w in DEV_WORD.findall(src or "") if len(w) >= 3)
    o = [w for w in DEV_WORD.findall(out or "") if len(w) >= 3]
    if not o:
        return 0.0
    return sum(1 for w in o if w in s or any(w in x for x in s if len(w) >= 4)) / len(o)


def pick_sample(rows: list, n: int) -> list:
    """Deterministic, spread evenly across the book (every k-th row)."""
    if n <= 0 or len(rows) <= n:
        return list(rows)
    step = len(rows) / float(n)
    return [rows[int(i * step)] for i in range(n)]


def parse_arms(spec: str, have_candidate: bool) -> list[str]:
    arms = [a.strip().lower() for a in (spec or "").split(",") if a.strip()]
    if not arms:
        arms = ["a", "b", "c", "d"] if have_candidate else ["a", "b"]
    bad = [a for a in arms if a not in ARM_LABEL]
    if bad:
        raise ValueError("unknown arm(s): %s" % ",".join(bad))
    if any(a in ("c", "d") for a in arms) and not have_candidate:
        raise ValueError("arms c/d need --candidate-prompt")
    return arms


JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")   # Latin OCR debris inside Devanagari


def unmarked(sa: str, out: str) -> bool:
    """HINDI_AB_UNMARKED_2026_10_03: the source carries OCR debris but the output marks
    nothing (no lacuna, no conjecture) - the damage was dropped or guessed silently."""
    return bool(JUNK.search(sa or "")) and not LACUNA.search(out or "") and not CONJ.search(out or "")


def score_output(sa: str, out: str, ref_out: str | None, scorer) -> dict:
    r = {"lacuna": bool(LACUNA.search(out or "")), "lacuna_tokens": len(LACUNA.findall(out or "")),
         "conj": len(CONJ.findall(out or "")), "tatsama": round(tatsama_share(sa, out), 3),
         "unmarked": unmarked(sa, out)}
    r["qa"] = round(scorer(sa, out, lang="hi"), 3) if (out and scorer) else None
    if ref_out is not None and out:
        r["vs_a"] = round(difflib.SequenceMatcher(None, ref_out, out).ratio(), 3)
    return r


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    return con


def report(paths: list) -> dict:
    """Pool every v2 result file (records carrying "arms") by doc and arm.
    Returns {doc: {arm: [n, lacuna_verses, lacuna_tokens, conj, tatsama_sum]}} plus '_all'."""
    out: dict = {}
    for p in paths:
        try:
            lines = Path(p).read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for l in lines:
            if not l.strip():
                continue
            try:
                r = json.loads(l)
            except Exception:
                continue
            arms = r.get("arms") or ["a", "b"]
            doc = Path(p).name.replace("hindi_ref_", "").rsplit("_", 2)[0]
            for key in (doc, "_all"):
                for arm in arms:
                    o = r.get("hi_" + arm)
                    if not o:
                        continue
                    g = out.setdefault(key, {}).setdefault(arm, [0, 0, 0, 0, 0.0, 0])
                    g[0] += 1; g[1] += 1 if LACUNA.search(o) else 0; g[2] += len(LACUNA.findall(o))
                    g[3] += len(CONJ.findall(o)); g[4] += tatsama_share(r.get("sa") or "", o)
                    g[5] += 1 if unmarked(r.get("sa") or "", o) else 0
    return out


def _first_population(path) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.loads(f.readline()).get("population")
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B/C/D for Hindi: reference and prompt (no DB writes)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--report", action="store_true", help="pool data/ab/hindi_ref_*.jsonl by doc and arm; no API")
    ap.add_argument("--population-only", default=None, choices=["anchored", "lacuna", "all"],
                    help="with --report: pool only runs of this population")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--population", choices=["anchored", "lacuna", "all"], default="anchored")
    ap.add_argument("--candidate-prompt", default=None, help="UTF-8 file: a full replacement Hindi base prompt")
    ap.add_argument("--arms", default="", help="comma list of a,b,c,d (default a,b; a,b,c,d with a candidate)")
    ap.add_argument("--engine", default="gemini:gemini-2.5-flash")
    ap.add_argument("--anchor-min-qa", type=float, default=0.6)
    ap.add_argument("--context", type=int, default=5)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--no-meter", action="store_true")
    ap.add_argument("--yes", action="store_true", help="call the API (default: dry run)")
    args = ap.parse_args()
    if args.report:
        import glob as _g
        res = report(sorted(_g.glob(str(Path("data") / "ab" / "hindi_ref_*.jsonl"))))
        if args.population_only:
            res = report([p for p in sorted(_g.glob(str(Path("data") / "ab" / "hindi_ref_*.jsonl")))
                          if _first_population(p) == args.population_only])
        print("%-34s %-4s %5s %8s %7s %6s %8s %9s" % ("doc", "arm", "n", "lac_vs", "lac_tok", "conj", "tatsama", "unmarked"))
        for doc in sorted(k for k in res if k != "_all") + (["_all"] if "_all" in res else []):
            for arm in sorted(res[doc]):
                n, lv, lt, cj, ts, um = res[doc][arm]
                print("%-34s %-4s %5d %7.1f%% %7d %6d %8.3f %9d" % (doc, arm, n, 100.0 * lv / n if n else 0, lt, cj,
                                                               ts / n if n else 0, um))
        return 0
    if not args.doc:
        print("FAIL: --doc is required (or use --report).")
        return 2
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db)
        return 2
    if not args.engine.startswith("gemini:"):
        print("FAIL: only gemini:* engines are wired here (production engine).")
        return 2
    cand_text = None
    if args.candidate_prompt:
        p = Path(args.candidate_prompt)
        if not p.exists():
            print("FAIL: %s not found." % p)
            return 2
        cand_text = p.read_text(encoding="utf-8").strip()
        if len(cand_text) < 200:
            print("FAIL: candidate prompt looks too short (%d chars)." % len(cand_text))
            return 2
    try:
        arms = parse_arms(args.arms, cand_text is not None)
    except ValueError as e:
        print("FAIL: %s" % e)
        return 2

    from normalize_text import normalize_sanskrit
    from text_filters import should_translate, clean_for_mt, score_translation_quality
    import infer_mt
    from translate_passages import _fetch_context_l10n, _get_doc_meta

    con = open_ro(args.db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    opt = [c for c in ("verse_ref", "chapter", "chandas", "text_type", "iast") if c in cols]
    sel = (", " + ", ".join("p." + c for c in opt)) if opt else ""
    if args.population == "anchored":
        where = ("AND TRIM(COALESCE(p.translation,'')) <> '' AND COALESCE(p.translation_qa, 0.0) >= ?")
        params = [args.doc, args.anchor_min_qa]
    else:
        where = "AND TRIM(COALESCE(l.translation,'')) <> ''"
        params = [args.doc]
    rows = con.execute(
        f"""SELECT p.id, p.page_no, p.idx, p.text, p.translation, COALESCE(p.translation_qa,0.0), l.translation{sel}
            FROM passages p JOIN docs d ON d.id = p.doc_id
            LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
            WHERE d.code = ? {where}
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
            ORDER BY p.page_no, p.idx""", params).fetchall()
    if args.population == "lacuna":
        rows = [r for r in rows if LACUNA.search(r[6] or "")]
    usable = []
    for r in rows:
        normed = normalize_sanskrit(r[3] or "")
        cleaned = clean_for_mt(normed)
        if cleaned and should_translate(normed, min_dev=0.05):
            usable.append((r, cleaned))
    sample = pick_sample(usable, args.n)
    meta = _get_doc_meta(con, args.doc)
    print("=" * 74)
    print("HINDI A/B  %s   population=%s   arms=%s   %s   %s" % (
        args.doc, args.population, ",".join(arms), "RUN" if args.yes else "DRY RUN", MARK))
    print("=" * 74)
    print("  candidates: %d   usable: %d   sample: %d" % (len(rows), len(usable), len(sample)))
    if not sample:
        print("  Nothing to sample.")
        return 1

    def system_prompt(m, use_candidate):
        saved = infer_mt._SYSTEM_PROMPT_HI
        try:
            if use_candidate:
                infer_mt._SYSTEM_PROMPT_HI = cand_text
            return infer_mt._build_system_prompt(
                doc_code=args.doc, category=meta.get("category"), chapter=m.get("chapter"),
                verse_ref=m.get("verse_ref"), chandas=m.get("chandas"), text_type=m.get("text_type"), tgt="hi")
        finally:
            infer_mt._SYSTEM_PROMPT_HI = saved

    items, in_chars, n_ref = [], 0, 0
    for (r, cleaned) in sample:
        m = dict(zip(opt, r[7:]))
        ref = r[4] if (r[4] and str(r[4]).strip() and (r[5] or 0.0) >= args.anchor_min_qa) else None
        n_ref += 1 if ref else 0
        ctx = _fetch_context_l10n(con, args.doc, "hi", r[1], r[2], n=args.context)
        it = {"passage_id": r[0], "page": r[1], "idx": r[2], "verse_ref": m.get("verse_ref"),
              "sa": cleaned, "en_ref": ref, "hi_stored": r[6], "_calls": {}}
        for arm in arms:
            sp = system_prompt(m, arm in ("c", "d"))
            msg = infer_mt._build_user_message(cleaned, m.get("iast"), ctx or None, ref if arm in ("a", "c") else None)
            it["_calls"][arm] = (sp, msg)
            in_chars += len(sp) + len(msg)
        items.append(it)
    con.close()
    n_calls = len(items) * len(arms)
    print("  verses carrying an English reference: %d of %d" % (n_ref, len(items)))
    try:
        from cost_tracker import estimate_cost_usd
        print("  calls: %d   input chars: %d   est cost: ~$%.4f (output assumed = input)" % (
            n_calls, in_chars, estimate_cost_usd(args.engine, in_chars, in_chars)))
    except Exception:
        print("  calls: %d   input chars: %d" % (n_calls, in_chars))
    if not args.yes:
        print("\n  Dry run. Add --yes to call the API. Nothing was written.")
        return 0

    try:   # METER_GATES_2026_10_04
        from usage_meter import budget_ok as _bok
        if not _bok(args.db):
            print("  Refusing: the spend cap is reached."); return 1
    except Exception:
        pass
    if hasattr(infer_mt, "_usage_reset"):
        infer_mt._usage_reset()
    model = args.engine.split(":", 1)[1]
    t0, out_chars = time.time(), 0
    for i, it in enumerate(items, 1):
        for arm in arms:
            sp, msg = it["_calls"][arm]
            try:
                res = infer_mt._gemini_translate([it["sa"]], model=model, system_prompt=sp, user_messages=[msg])
                it["hi_" + arm] = (res[0] if res else "") or ""
            except Exception as e:
                it["hi_" + arm] = ""
                it["err_" + arm] = str(e)[:200]
            out_chars += len(it["hi_" + arm])
            time.sleep(args.sleep)
        print("  (%d/%d) p%s.%s  " % (i, len(items), it["page"], it["idx"])
              + " | ".join("%s %d" % (a, len(it["hi_" + a])) for a in arms), flush=True)
    dur = time.time() - t0
    if not args.no_meter:
        try:
            from cost_tracker import log_translation_call, log_api_call
            wcon = sqlite3.connect(args.db, timeout=30)
            _u = getattr(infer_mt, "_USAGE", None) or {}
            if _u.get("calls"):   # METER_GATES_2026_10_04: provider counts, and not booked as 'translation'
                log_api_call(wcon, kind="ab_test", doc=args.doc or "", engine=args.engine, in_chars=in_chars,
                             out_chars=out_chars, duration_s=dur, passages=n_calls, ok=True,
                             in_tokens=_u["in"], out_tokens=_u["out"])
            else:
                log_translation_call(wcon, args.doc, args.engine, in_chars=in_chars, out_chars=out_chars,
                                     duration_s=dur, passages=n_calls, ok=True)
            wcon.commit(); wcon.close()
        except Exception as e:
            print("  [meter] could not log spend: %s" % e)

    agg = {a: {"n": 0, "qa": 0.0, "lacuna": 0, "lacuna_tokens": 0, "conj": 0, "tatsama": 0.0, "vs_a": []}
           for a in arms}
    for it in items:
        base = it.get("hi_a") if "a" in arms else None
        for arm in arms:
            o = it["hi_" + arm]
            if not o:
                continue
            sc = score_output(it["sa"], o, base if arm != "a" else None, score_translation_quality)
            for k, v in sc.items():
                it["%s_%s" % (k, arm)] = v
            g = agg[arm]; g["n"] += 1
            g["qa"] += sc["qa"] or 0.0; g["lacuna"] += int(sc["lacuna"]); g["lacuna_tokens"] += sc["lacuna_tokens"]
            g["conj"] += sc["conj"]; g["tatsama"] += sc["tatsama"]
            if "vs_a" in sc:
                g["vs_a"].append(sc["vs_a"])
    stored_lac = sum(1 for it in items if LACUNA.search(it["hi_stored"] or ""))
    print("\n  %-30s %7s %7s %7s %6s %8s %6s %4s" % ("arm", "qa", "lacuna", "tokens", "conj", "tatsama", "vs_a", "n"))
    for arm in arms:
        g = agg[arm]; n = g["n"] or 1
        vs = ("%.3f" % (sum(g["vs_a"]) / len(g["vs_a"]))) if g["vs_a"] else "  -  "
        print("  %-30s %7.3f %7d %7d %6d %8.3f %6s %4d" % (
            ARM_LABEL[arm], g["qa"] / n, g["lacuna"], g["lacuna_tokens"], g["conj"], g["tatsama"] / n, vs, g["n"]))
    print("  stored Hindi in this sample: %d of %d with a lacuna" % (stored_lac, len(items)))

    outdir = Path("data/ab"); outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = outdir / ("hindi_ref_%s_%s" % (args.doc, stamp))
    with open(str(base) + ".jsonl", "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            rec = {k: v for k, v in it.items() if not k.startswith("_")}
            rec["arms"] = arms; rec["population"] = args.population
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    e = html.escape
    head = "".join("<th>%s</th>" % e(ARM_LABEL[a]) for a in arms)
    body = []
    for it in items:
        cells = "".join("<td>%s<br><small>lacuna %s | conj %s | tatsama %s</small></td>" % (
            e(it.get("hi_" + a) or it.get("err_" + a, "")), it.get("lacuna_tokens_" + a, "-"),
            it.get("conj_" + a, "-"), it.get("tatsama_" + a, "-")) for a in arms)
        body.append("<tr><td>%s.%s</td><td class=sa>%s</td><td>%s</td><td>%s</td>%s</tr>" % (
            it["page"], it["idx"], e(it["sa"]), e(it["en_ref"] or ""), e(it["hi_stored"] or ""), cells))
    Path(str(base) + ".html").write_text(
        "<!doctype html><meta charset=utf-8><title>Hindi A/B %s</title>"
        "<style>body{font:15px/1.5 system-ui;margin:16px}table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}.sa{font-size:17px}small{color:#666}</style>"
        "<h2>%s - Hindi arms (%s population)</h2><p>Read each arm against the Sanskrit. A conjecture in "
        "\u27e8 \u27e9 is the model's marked guess at an OCR-damaged word.</p>"
        "<table><tr><th>page.idx</th><th>Sanskrit</th><th>English ref</th><th>stored Hindi</th>%s</tr>%s</table>"
        % (e(args.doc), e(args.doc), e(args.population), head, "".join(body)), encoding="utf-8")
    print("\n  wrote %s.jsonl and .html" % base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
