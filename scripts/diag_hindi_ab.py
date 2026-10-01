#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
diag_hindi_ab.py  (2026-09-30)  HINDI_REF_AB_2026_09_30

QUESTION: should Hindi be translated from the Sanskrit ALONE, or with the
QA-passed English passed as a meaning reference (the current default,
TRANSLATION_FILTERS2_2026_09_27)?

The two are not independent today. English never sees Hindi. Hindi sees the
English of the same verse whenever translation_qa >= 0.6. That can help
(names, hard compounds) or hurt: English errors are copied into Hindi, and the
Hindi drifts toward an English paraphrase instead of keeping the Sanskrit
(tatsama) vocabulary that Hindi can carry over directly.

This script MEASURES it on a deterministic sample. It changes nothing:
  * Arm A: the production message (Sanskrit + IAST + Hindi context + English reference)
  * Arm B: the identical message WITHOUT the English reference
  Same system prompt, same context, same model, same verse. One variable.
  * mt_cache is bypassed on purpose (its key ignores the reference, so a cached
    answer would make the two arms identical). Nothing is written to mt_cache,
    passages or translations_l10n.
  * Spend is metered to api_usage under the doc (use --no-meter to skip).

Metrics per arm (all computed locally, no second model):
  qa        text_filters.score_translation_quality(src, out, lang='hi')  - the production scorer
  lacuna    outputs containing [asphuta]
  tatsama   share of the output's Devanagari words (>= 3 letters) that also occur
            in the Sanskrit source - how much Sanskrit vocabulary is carried over
  a_vs_b    character similarity between the two arms (1.0 = the reference changed nothing)
And a side-by-side HTML for reading by eye, which is the real test.

  python scripts\\diag_hindi_ab.py --doc markandeya_purana                # dry run: sample + cost estimate
  python scripts\\diag_hindi_ab.py --doc markandeya_purana --n 40 --yes   # call the API (2 calls per verse)
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

MARK = "HINDI_REF_AB_2026_09_30"
DEV_WORD = re.compile(r"[\u0900-\u0963\u0970-\u097f]+")
LACUNA = re.compile(r"\[\s*\u0905\u0938\u094d\u092a\u0937\u094d\u091f\s*\]")


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


def open_ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    return con


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B: Hindi with vs without the English reference (no DB writes)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--engine", default="gemini:gemini-2.5-flash")
    ap.add_argument("--anchor-min-qa", type=float, default=0.6)
    ap.add_argument("--context", type=int, default=5)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--no-meter", action="store_true")
    ap.add_argument("--yes", action="store_true", help="call the API (default: dry run)")
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db)
        return 2
    if not args.engine.startswith("gemini:"):
        print("FAIL: only gemini:* engines are wired here (production engine).")
        return 2

    from normalize_text import normalize_sanskrit
    from text_filters import should_translate, clean_for_mt, score_translation_quality
    import infer_mt
    from translate_passages import _fetch_context_l10n, _get_doc_meta

    con = open_ro(args.db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    opt = [c for c in ("verse_ref", "chapter", "chandas", "text_type", "iast") if c in cols]
    sel = ", ".join("p." + c for c in opt)
    rows = con.execute(
        f"""SELECT p.id, p.page_no, p.idx, p.text, p.translation, {sel}
            FROM passages p JOIN docs d ON d.id = p.doc_id
            WHERE d.code = ? AND TRIM(COALESCE(p.translation,'')) <> ''
              AND COALESCE(p.translation_qa, 0.0) >= ?
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
            ORDER BY p.page_no, p.idx""", (args.doc, args.anchor_min_qa)).fetchall()
    usable = []
    for r in rows:
        cleaned = clean_for_mt(normalize_sanskrit(r[3] or ""))
        if cleaned and should_translate(normalize_sanskrit(r[3] or ""), min_dev=0.05):
            usable.append((r, cleaned))
    sample = pick_sample(usable, args.n)
    meta = _get_doc_meta(con, args.doc)
    stored = {}
    if sample:
        ids = [s[0][0] for s in sample]
        q = ",".join("?" * len(ids))
        stored = dict(con.execute(f"SELECT passage_id, translation FROM translations_l10n "
                                  f"WHERE lang='hi' AND passage_id IN ({q})", ids).fetchall())
    print("=" * 74)
    print("HINDI REFERENCE A/B  %s   %s   %s" % (args.doc, "RUN" if args.yes else "DRY RUN", MARK))
    print("=" * 74)
    print("  QA-passed English verses: %d   usable: %d   sample: %d" % (len(rows), len(usable), len(sample)))
    if not sample:
        print("  Nothing to sample (no English with translation_qa >= %.2f)." % args.anchor_min_qa)
        return 1

    items = []
    in_chars = 0
    for (r, cleaned) in sample:
        m = dict(zip(opt, r[5:]))
        ctx = _fetch_context_l10n(con, args.doc, "hi", r[1], r[2], n=args.context)
        sp = infer_mt._build_system_prompt(doc_code=args.doc, category=meta.get("category"),
                                           chapter=m.get("chapter"), verse_ref=m.get("verse_ref"),
                                           chandas=m.get("chandas"), text_type=m.get("text_type"), tgt="hi")
        ma = infer_mt._build_user_message(cleaned, m.get("iast"), ctx or None, r[4])
        mb = infer_mt._build_user_message(cleaned, m.get("iast"), ctx or None, None)
        in_chars += 2 * len(sp) + len(ma) + len(mb)
        items.append({"passage_id": r[0], "page": r[1], "idx": r[2], "verse_ref": m.get("verse_ref"),
                      "sa": cleaned, "en_ref": r[4], "hi_stored": stored.get(r[0]),
                      "_sp": sp, "_ma": ma, "_mb": mb})
    con.close()
    try:
        from cost_tracker import estimate_cost_usd
        est = estimate_cost_usd(args.engine, in_chars, in_chars)
        print("  calls: %d   input chars: %d   est cost: ~$%.4f (output assumed = input)" % (2 * len(items), in_chars, est))
    except Exception:
        print("  calls: %d   input chars: %d" % (2 * len(items), in_chars))
    if not args.yes:
        print("\n  Dry run. Add --yes to call the API. Nothing was written.")
        return 0

    model = args.engine.split(":", 1)[1]
    t0 = time.time()
    out_chars = 0
    for i, it in enumerate(items, 1):
        for arm, msg in (("a", it["_ma"]), ("b", it["_mb"])):
            try:
                res = infer_mt._gemini_translate([it["sa"]], model=model, system_prompt=it["_sp"], user_messages=[msg])
                it["hi_" + arm] = (res[0] if res else "") or ""
            except Exception as e:
                it["hi_" + arm] = ""
                it["err_" + arm] = str(e)[:200]
            out_chars += len(it["hi_" + arm])
            time.sleep(args.sleep)
        print("  (%d/%d) p%s.%s  A %d chars | B %d chars" % (i, len(items), it["page"], it["idx"],
                                                           len(it["hi_a"]), len(it["hi_b"])), flush=True)
    dur = time.time() - t0
    if not args.no_meter:
        try:
            from cost_tracker import log_translation_call
            wcon = sqlite3.connect(args.db, timeout=30)
            log_translation_call(wcon, args.doc, args.engine, in_chars=in_chars, out_chars=out_chars,
                                 duration_s=dur, passages=2 * len(items), ok=True)
            wcon.commit(); wcon.close()
        except Exception as e:
            print("  [meter] could not log spend: %s" % e)

    agg = {"a": [0.0, 0, 0.0, 0], "b": [0.0, 0, 0.0, 0]}
    sims = []
    for it in items:
        for arm in ("a", "b"):
            o = it["hi_" + arm]
            if not o:
                continue
            it["qa_" + arm] = round(score_translation_quality(it["sa"], o, lang="hi"), 3)
            it["tatsama_" + arm] = round(tatsama_share(it["sa"], o), 3)
            it["lacuna_" + arm] = bool(LACUNA.search(o))
            a = agg[arm]; a[0] += it["qa_" + arm]; a[1] += int(it["lacuna_" + arm]); a[2] += it["tatsama_" + arm]; a[3] += 1
        if it["hi_a"] and it["hi_b"]:
            it["a_vs_b"] = round(difflib.SequenceMatcher(None, it["hi_a"], it["hi_b"]).ratio(), 3)
            sims.append(it["a_vs_b"])
    print("\n  %-28s %8s %8s %8s %6s" % ("arm", "mean qa", "lacuna", "tatsama", "n"))
    for arm, label in (("a", "A  with English reference"), ("b", "B  Sanskrit only")):
        s, l, t, n = agg[arm]
        print("  %-28s %8.3f %8d %8.3f %6d" % (label, s / n if n else 0, l, t / n if n else 0, n))
    if sims:
        print("  mean A-vs-B similarity: %.3f   (1.0 = the reference changes nothing)" % (sum(sims) / len(sims)))

    outdir = Path("data/ab"); outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = outdir / ("hindi_ref_%s_%s" % (args.doc, stamp))
    with open(str(base) + ".jsonl", "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps({k: v for k, v in it.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")
    e = html.escape
    rows_html = "".join(
        "<tr><td>%s.%s<br><small>%s</small></td><td class=sa>%s</td><td>%s</td>"
        "<td>%s<br><small>qa %s | tatsama %s</small></td><td>%s<br><small>qa %s | tatsama %s</small></td></tr>"
        % (it["page"], it["idx"], e(str(it.get("verse_ref") or "")), e(it["sa"]), e(it["en_ref"] or ""),
           e(it.get("hi_a") or it.get("err_a", "")), it.get("qa_a", "-"), it.get("tatsama_a", "-"),
           e(it.get("hi_b") or it.get("err_b", "")), it.get("qa_b", "-"), it.get("tatsama_b", "-"))
        for it in items)
    Path(str(base) + ".html").write_text(
        "<!doctype html><meta charset=utf-8><title>Hindi reference A/B %s</title>"
        "<style>body{font:15px/1.5 system-ui;margin:16px}table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}.sa{font-size:17px}small{color:#666}</style>"
        "<h2>%s: Hindi with vs without the English reference</h2>"
        "<p>Read B against the Sanskrit. Does it keep meaning the English lost, or lose meaning the English supplied?</p>"
        "<table><tr><th>page.idx</th><th>Sanskrit</th><th>English reference</th>"
        "<th>A: with reference</th><th>B: Sanskrit only</th></tr>%s</table>" % (e(args.doc), e(args.doc), rows_html),
        encoding="utf-8")
    print("\n  wrote %s.jsonl and .html" % base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
