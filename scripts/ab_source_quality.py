#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ab_source_quality.py - does better OCR actually produce better TRANSLATIONS?
(2026-08-30)

THE GAP THIS CLOSES
-------------------
Everything measured so far is about SOURCE quality: contamination, token
agreement against a 0.927 vision-vs-vision ceiling, per-page failure modes. From
that we concluded Tesseract is 34-73% of achievable and vision should be the
source of record - and then we assumed translation quality follows.

That assumption has never been tested, and it is not obviously true. A capable
translator reads through noise: given `विषयालक्रमगिका` in a context that makes
`विषयानुक्रमणिका` obvious, it may well produce the right English anyway. If it
does, then most of the OCR programme buys provenance and tidiness rather than
better translations, and the honest thing is to say so.

THE EXPERIMENT
--------------
Page-level, so no fragile verse alignment is needed:

  OLD  the existing translations for a page, made from Tesseract source
  NEW  a fresh translation of the SAME page's vision text
  Both are graded by the Q4 judge AGAINST THE VISION TEXT, which is the best
  reading available (0.927 self-consistent, versus Tesseract's 0.34-0.73).

If NEW clearly beats OLD, the re-OCR programme is justified in the only currency
that matters. If they tie, we have learned something more valuable: the existing
14,523 translations can stand, and vision OCR is for new intake and provenance
rather than a corpus-wide rebuild costing ~$11 and discarding prior work.

COST: about 10 pages of vision (~$0.01), 10 translations (~$0.01) and 20 judge
calls (~$0.01). Under three cents to answer a two-figure question.

  python scripts\\ab_source_quality.py --doc smriti_14manu_smriti
  python scripts\\ab_source_quality.py --doc smriti_14manu_smriti --pages 10 --yes
  python scripts\\ab_source_quality.py --report
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, statistics, sys, time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

DEV = re.compile(r"[ऀ-ॣ॰-ॿ]")

JUDGE_SYS = (
    "You are grading an English translation of a Sanskrit passage.\n"
    "You are given the SANSKRIT (authoritative) and a TRANSLATION.\n"
    "Grade ONLY how well the translation renders that Sanskrit.\n"
    "fidelity: 1-5, does it say what the Sanskrit says, without invention or omission.\n"
    "fluency : 1-5, is the English clear and readable.\n"
    'Reply with minified JSON ONLY: {"reason":"<=10 words","fidelity":N,"fluency":N}'
)

TRANSLATE_SYS = (
    "Translate the following Sanskrit passage into precise, scholarly English.\n"
    "Preserve technical terms in IAST in parentheses where helpful.\n"
    "Do not add commentary. Output only the translation."
)


def connect(db):
    con = sqlite3.connect(db, timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    return con


def gemini(model_name, system, prompt, temperature=0.1, max_tokens=2048, json_out=False):
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    try:
        cfg = genai.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens,
                                     response_mime_type="application/json" if json_out else None)
    except TypeError:
        cfg = genai.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
    gm = genai.GenerativeModel(model_name=model_name, generation_config=cfg,
                               system_instruction=system)
    resp = gm.generate_content(prompt, request_options={"timeout": 180})
    try:
        return (resp.text or "").strip(), resp
    except Exception:
        return "", resp


def parse_scores(txt):
    t = (txt or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    try:
        d = json.loads(t)
        return d.get("fidelity"), d.get("fluency"), str(d.get("reason", ""))[:120]
    except Exception:
        f = re.search(r'"fidelity"\s*:\s*([1-5])', t)
        u = re.search(r'"fluency"\s*:\s*([1-5])', t)
        return (int(f.group(1)) if f else None, int(u.group(1)) if u else None,
                "[salvaged]")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--poppler-bin", default=os.environ.get("POPPLER_BIN") or os.environ.get("POPPLER_PATH"))
    ap.add_argument("--out", default="data/ab_source_quality.json")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    if args.report:
        try:
            render(json.load(open(args.out, encoding="utf-8")))
        except Exception as exc:
            sys.exit(f"no results at {args.out} ({exc})")
        return
    if not args.doc:
        ap.error("give --doc <CODE>")

    con = connect(args.db)
    did = con.execute("SELECT id FROM docs WHERE code=?", (args.doc,)).fetchone()
    if not did:
        sys.exit(f"no such doc: {args.doc}")
    did = did[0]
    # Pages that HAVE existing translations, densest first.
    rows = con.execute("""
        SELECT p.page_no,
               COUNT(*),
               SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END)
        FROM passages p
        WHERE p.doc_id=? AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
        GROUP BY p.page_no HAVING 3 > 0 ORDER BY 3 DESC, 2 DESC""", (did,)).fetchall()
    pages = [r[0] for r in rows if r[2] and r[2] >= 3][: args.pages]
    if not pages:
        sys.exit("no pages with enough existing translations")

    print(f"doc: {args.doc}   pages: {len(pages)}   "
          f"est ${len(pages)*0.0035:.3f}   ({'LIVE' if args.yes else 'DRY-RUN'})")
    for pg in pages:
        print(f"  page {pg}")
    if not args.yes:
        print("\nRe-run with --yes. Nothing was called.")
        con.close(); return

    try:
        from usage_meter import meter
    except Exception:
        meter = None
    import ocr_vision

    results = []
    for pg in pages:
        segs = con.execute("""
            SELECT p.text, COALESCE(p.translation,'')
            FROM passages p WHERE p.doc_id=? AND p.page_no=?
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
            ORDER BY p.idx""", (did, pg)).fetchall()
        old_tr = " ".join(t for _s, t in segs if t.strip())
        tess_src = " ".join(s for s, _t in segs if s.strip())
        if not old_tr.strip():
            continue

        pdf = os.path.join("inbox", f"{args.doc}_{pg:04d}.pdf")
        cache = os.path.join("data", "probe", f"{args.doc}_{pg:04d}.jsonl")
        vis_text = ""
        if os.path.exists(cache):
            try:
                vis_text = json.loads(open(cache, encoding="utf-8").readline()).get("text") or ""
            except Exception:
                vis_text = ""
        if not vis_text and os.path.exists(pdf):
            t0 = time.time()
            img = ocr_vision.render_page(pdf, args.dpi, args.poppler_bin)
            vis_text, resp, _ = ocr_vision.transcribe(img, args.model)
            if meter:
                meter(kind="ab_test", doc=args.doc, engine=f"gemini-vision:{args.model}",
                      resp=resp, out_chars=len(vis_text), units=1,
                      duration_s=time.time()-t0, db=args.db)
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            open(cache, "w", encoding="utf-8").write(
                json.dumps({"engine": f"gemini-vision:{args.model}", "text": vis_text},
                           ensure_ascii=False) + "\n")
        if not vis_text.strip():
            print(f"  page {pg}: no vision text, skipping"); continue

        # NEW translation, from the vision reading of the same page
        t0 = time.time()
        new_tr, resp = gemini(args.model, TRANSLATE_SYS, vis_text[:6000])
        if meter:
            meter(kind="ab_test", doc=args.doc, engine=f"gemini:{args.model}", resp=resp,
                  in_chars=len(vis_text), out_chars=len(new_tr), units=1,
                  duration_s=time.time()-t0, db=args.db)

        # Judge BOTH against the vision source
        scores = {}
        for label, tr in (("old", old_tr), ("new", new_tr)):
            if not tr.strip():
                continue
            t0 = time.time()
            raw, resp = gemini(args.model, JUDGE_SYS,
                               f"SANSKRIT:\n{vis_text[:4000]}\n\nTRANSLATION:\n{tr[:4000]}",
                               temperature=0.0, json_out=True)
            if meter:
                meter(kind="ab_test", doc=args.doc, engine=f"gemini:{args.model}", resp=resp,
                      in_chars=len(vis_text)+len(tr), out_chars=len(raw), units=1,
                      duration_s=time.time()-t0, db=args.db)
            f, u, why = parse_scores(raw)
            scores[label] = {"fidelity": f, "fluency": u, "reason": why}

        if "old" in scores and "new" in scores:
            results.append({"doc": args.doc, "page": pg,
                            "tesseract_chars": len(tess_src), "vision_chars": len(vis_text),
                            "old": scores["old"], "new": scores["new"]})
            o, nw = scores["old"], scores["new"]
            print(f"  page {pg}: OLD fid={o['fidelity']} flu={o['fluency']}   "
                  f"NEW fid={nw['fidelity']} flu={nw['fluency']}")
        time.sleep(0.4)

    con.close()
    prev = []
    if os.path.exists(args.out):
        try: prev = json.load(open(args.out, encoding="utf-8"))
        except Exception: prev = []
    prev.extend(results)
    json.dump(prev, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    render(prev)


def render(rows):
    if not rows:
        print("no results."); return
    print("\n" + "=" * 74)
    print("DOES BETTER OCR PRODUCE BETTER TRANSLATIONS?")
    print("=" * 74)
    print("  Both graded against the VISION source, which is the best reading we have.")
    print("  OLD = existing translation, made from Tesseract text.")
    print("  NEW = fresh translation of the same page's vision text.\n")

    def avg(k, w):
        v = [r[k][w] for r in rows if r[k].get(w) is not None]
        return statistics.mean(v) if v else None

    of, nf = avg("old", "fidelity"), avg("new", "fidelity")
    ou, nu = avg("old", "fluency"), avg("new", "fluency")
    print(f"  pages compared : {len(rows)}")
    if of is not None and nf is not None:
        print(f"  fidelity  OLD {of:.2f}  ->  NEW {nf:.2f}   ({nf-of:+.2f})")
    if ou is not None and nu is not None:
        print(f"  fluency   OLD {ou:.2f}  ->  NEW {nu:.2f}   ({nu-ou:+.2f})")

    wins = sum(1 for r in rows if (r["new"].get("fidelity") or 0) > (r["old"].get("fidelity") or 0))
    ties = sum(1 for r in rows if (r["new"].get("fidelity") or 0) == (r["old"].get("fidelity") or 0))
    loss = len(rows) - wins - ties
    print(f"  fidelity: NEW better on {wins}, tied on {ties}, WORSE on {loss}")

    print("\n  HOW TO READ THIS")
    if of is not None and nf is not None:
        d = nf - of
        if d >= 0.5:
            print("   A gap of +0.5 or more on a 1-5 scale is decisive: the corpus-wide")
            print("   re-OCR and re-translation (~$11) is justified in translation quality,")
            print("   not merely in provenance.")
        elif d >= 0.2:
            print("   A modest gain. Worth doing for the worst documents, hard to justify")
            print("   corpus-wide. Prefer the 'worst books first' path.")
        else:
            print("   NO MEANINGFUL GAIN. The translator reads through OCR noise, so the")
            print("   existing 14,523 translations can stand. Vision OCR is then for NEW")
            print("   intake, provenance and the apparatus - not a corpus rebuild. That")
            print("   would save roughly $11 and a great deal of churn.")
    print("\n  Caveat: this is a page-level, single-judge comparison on a small sample.")
    print("  Treat a result inside +/-0.2 as a tie, not as evidence either way.")


if __name__ == "__main__":
    main()
