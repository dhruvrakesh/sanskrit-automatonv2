#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_mbh01.py — Translation-quality benchmark harness (M1).

Samples N passages from a document (default MBh01 — Mahābhārata Book 1,
critical-edition source), translates each with TWO engines side by side
(default: gemini-2.5-flash vs gemini-2.5-pro), and emits an HTML evaluation
sheet with a blank "Debroy (your print edition)" column and a 1–5 rubric,
so YOU judge fidelity against the published translation you own.

Deliberate design choices (see JYOTISH/automaton fidelity practice):
  * Debroy's translation is copyrighted — it is NEVER fetched, ingested or
    stored by this script. The comparison column is filled by the human
    evaluator from their own copy. No text of his enters the pipeline.
  * Uses the automaton's own translate_batch() (same prompts, cache, cost
    tracking) so the benchmark measures the REAL pipeline, not a lab replica.
  * Read-only against context.db. Fresh translations go only into the HTML
    report (and the normal MT cache), never into passages.translation.

Usage (from sanskrit-automatonv2 root, venv active, keys in .env):
  python scripts/benchmark_mbh01.py --list-docs
  python scripts/benchmark_mbh01.py --doc MBh01 --n 30 --dry-run
  python scripts/benchmark_mbh01.py --doc MBh01 --n 30
  python scripts/benchmark_mbh01.py --doc MBh01 --n 30 --engines gemini:gemini-2.5-flash gemini:gemini-2.5-pro

Output: exports/<doc>_benchmark_<n>.html
"""
import argparse
import html
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))  # scripts/ imports

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass


def open_db(path: str) -> sqlite3.Connection:
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"ERROR: {path} not found — run from the sanskrit-automatonv2 root.")
    con = sqlite3.connect(path)  # translate_batch needs write for its MT cache
    con.row_factory = sqlite3.Row
    return con


def pick_samples(con, doc_code: str, n: int):
    doc = con.execute("SELECT id, code, category FROM docs WHERE code=?",
                      (doc_code,)).fetchone()
    if doc is None:
        sys.exit(f"ERROR: doc {doc_code!r} not in context.db (use --list-docs).")
    rows = con.execute("""
        SELECT id, page_no, idx, text, iast, verse_ref, chapter, chandas,
               text_type, quality_score
        FROM passages
        WHERE doc_id=? AND LENGTH(TRIM(text)) > 40
          AND COALESCE(quality_score, 0) >= 0.5
        ORDER BY page_no, idx
    """, (doc["id"],)).fetchall()
    if not rows:
        sys.exit(f"ERROR: no passages with quality_score>=0.5 for {doc_code!r}.")
    if len(rows) <= n:
        return doc, list(rows)
    # Stratified: evenly spaced through the book so all parvans/adhyāyas sampled
    step = len(rows) / n
    return doc, [rows[int(i * step)] for i in range(n)]


def run(args):
    con = open_db(args.db)

    if args.list_docs:
        for r in con.execute("""
            SELECT d.code, d.category, COUNT(p.id) AS n,
                   ROUND(AVG(COALESCE(p.quality_score,0)),2) AS avg_q
            FROM docs d LEFT JOIN passages p ON p.doc_id=d.id
            GROUP BY d.id ORDER BY d.code"""):
            print(f"{r['code']:40s} {(r['category'] or '-'):14s} "
                  f"passages={r['n']:6d} avg_q={r['avg_q']}")
        return

    doc, samples = pick_samples(con, args.doc, args.n)
    print(f"{args.doc}: sampled {len(samples)} passages "
          f"(quality>=0.5, evenly spaced). Engines: {', '.join(args.engines)}")

    if args.dry_run:
        for s in samples[:5]:
            print(f"  p{s['page_no']}.{s['idx']} q={s['quality_score']:.2f} "
                  f"{s['text'][:60]}…")
        print(f"--dry-run: no API calls. Estimated calls: "
              f"{len(samples) * len(args.engines)}")
        return

    from infer_mt import translate_batch  # real pipeline, real prompts, real cache

    texts = [s["text"] for s in samples]
    kw = dict(
        iast_list=[s["iast"] for s in samples],
        doc_code=doc["code"], category=doc["category"],
        chapters=[s["chapter"] for s in samples],
        verse_refs=[s["verse_ref"] for s in samples],
        chandas_list=[s["chandas"] for s in samples],
        text_types=[s["text_type"] for s in samples],
    )
    results = {}
    for eng in args.engines:
        print(f"translating {len(texts)} passages with {eng} …")
        results[eng] = translate_batch(con, texts, engine=eng, **kw)

    out_dir = pathlib.Path("exports")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{doc['code']}_benchmark_{len(samples)}.html"

    e = html.escape
    eng_heads = "".join(f"<th>{e(eng)}</th>" for eng in args.engines)
    rows_html = []
    for i, s in enumerate(samples):
        cells = "".join(
            f"<td class='tr'>{e(results[eng][i] or '')}</td>" for eng in args.engines)
        rows_html.append(f"""
<tr>
  <td class="ref">p{s['page_no']}.{s['idx']}<br>
      <span class="meta">{e(s['verse_ref'] or '')} q={s['quality_score']:.2f}</span></td>
  <td class="sa">{e(s['text'])}<div class="iast">{e(s['iast'] or '')}</div></td>
  {cells}
  <td class="debroy" contenteditable="true">(type notes from your Debroy edition here)</td>
  <td class="score">
    <select><option>—</option><option>1 poor</option><option>2 weak</option>
    <option>3 fair</option><option>4 good</option><option>5 Debroy-grade</option></select>
  </td>
</tr>""")

    out.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{e(doc['code'])} translation benchmark</title><style>
body{{font-family:Georgia,serif;margin:20px;background:#faf7f2;color:#2a2118}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
td,th{{border:1px solid #d9d0c0;padding:8px;vertical-align:top}}
th{{background:#efe7d8}} .sa{{font-size:16px;max-width:26em}}
.iast{{color:#7a6f61;font-size:12px;margin-top:6px}}
.ref{{white-space:nowrap;color:#7a6f61}} .meta{{font-size:11px}}
.tr{{max-width:28em}} .debroy{{background:#fffdf5;max-width:22em;color:#555}}
.note{{background:#fff;border:1px solid #d9d0c0;border-radius:8px;padding:12px;margin-bottom:16px}}
</style></head><body>
<h1>{e(doc['code'])} — translation benchmark ({len(samples)} sampled passages)</h1>
<div class="note"><b>How to evaluate:</b> open your own copy of Bibek Debroy's
translation (Penguin) at each verse reference, type brief comparison notes in the
editable Debroy column, and score each engine row 1–5 for: fidelity (no additions/
omissions), proper-noun handling (IAST kept), and readability. Copyright note:
Debroy's text stays in your book — nothing of it is stored by the pipeline.
Notes typed here live only until the page is closed — copy the page (Ctrl+A/Ctrl+C into a doc)
or print to PDF when done.</div>
<table><tr><th>Ref</th><th>Sanskrit (source)</th>{eng_heads}
<th>Debroy comparison (manual)</th><th>Score</th></tr>
{''.join(rows_html)}
</table></body></html>""", encoding="utf-8")
    print(f"\nWrote {out}")
    print("Open it, compare against your Debroy edition, then print-to-PDF to keep scores.")


def main():
    ap = argparse.ArgumentParser(description="Side-by-side MT benchmark for a doc")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default="MBh01")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--engines", nargs="+",
                    default=["gemini:gemini-2.5-flash", "gemini:gemini-2.5-pro"])
    ap.add_argument("--list-docs", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
