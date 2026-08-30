#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_probe.py - decide, per document, whether Tesseract is good enough.
(2026-08-29)

THE PROBLEM WITH EVERY CHEAPER TEST
-----------------------------------
`quality_score` (0.6*devanagari + 0.4*danda) measures how Devanagari a page
LOOKS. Latin-intrusion "contamination" measures how much junk leaked in. Neither
can see Tesseract's worst failure: confident, well-formed, WRONG Devanagari.
`विषयालक्रमगिका` for `विषयानुक्रमणिका` and `शातपथवाहणम्` for `शतपथब्राह्मणम्`
are pure Devanagari and pure nonsense, and they sail through both tests.

Character similarity does not separate them either - measured on Shatpatha
(known bad) it is 0.732 and on AphorismsOfSandilya 0.803, because garbled
Tesseract still gets ~73% of individual characters right while destroying every
word they belong to.

WHAT THIS MEASURES INSTEAD
--------------------------
TOKEN AGREEMENT: of Tesseract's Devanagari words on a page, what fraction appear
verbatim in a vision transcription of the SAME page? A word is a hard target -
one misread character makes it a non-match - so this measures word integrity,
which is what a translator actually needs. Measured on the two documents where
both engines exist: Shatpatha 0.376, AphorismsOfSandilya 0.367. Both are books
we independently judged unusable, so those figures anchor the BAD end of the
scale. Running this on a document the contamination table calls clean is what
supplies the good-end anchor and therefore the threshold.

COST
----
Five pages per document at roughly $0.00087/page is about $0.004 per document -
around $0.10 to probe an entire 32-document corpus, one time. Dry-run by
default; every call is metered through usage_meter.

  python scripts/ocr_probe.py --doc smriti_14manu_smriti
  python scripts/ocr_probe.py --doc smriti_14manu_smriti --yes
  python scripts/ocr_probe.py --all --pages 5 --yes
  python scripts/ocr_probe.py --report          # re-read results, no API calls
"""
from __future__ import annotations
import argparse, glob as globmod, json, os, re, statistics, sys, time
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

DEV = re.compile(r"[ऀ-ॣ॰-ॿ]")
LAT = re.compile(r"[A-Za-z]")
JUNK = re.compile(r"[©®¢£§¶†‡~^_=<>{}\\|@#$%*+]")
PAGE_RE = re.compile(r"^(.*)_(\d{4})(_norm)?\.jsonl$")

# Anchors measured 2026-08-29 on the two documents that have both engines.
BAD_ANCHOR = 0.38          # Shatpatha 0.376, AphorismsOfSandilya 0.367
GOOD_ENOUGH = 0.75         # provisional; the probe's own results refine it


def jtext(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            line = next((l for l in f if l.strip()), None)
        return (json.loads(line).get("text") or "") if line else ""
    except Exception:
        return None


def toks(t: str) -> list[str]:
    """Devanagari word tokens of 3+ characters. Shorter strings are particles
    and numerals, which match by chance and would flatter the score."""
    return [w for w in re.split(r"[^ऀ-ॣ॰-ॿ]+", t or "") if len(w) >= 3]


def contamination(t: str) -> float:
    d, l, j = len(DEV.findall(t)), len(LAT.findall(t)), len(JUNK.findall(t))
    return (l + j) / (d + l + j) if (d + l + j) else 0.0


def sample_pages(doc: str, raw: str, inbox: str, n: int,
                 min_tokens: int = 40, skip_front: float = 0.05) -> list[tuple[str, str]]:
    """The DENSEST pages of the book, not evenly spaced ones.

    The first version took cands[::step], which starts at index 0 - the first
    qualifying page - so a six-page volume was judged on its title page and its
    opening chapter heading. A 40-token floor does not keep out indexes,
    colophons or running heads either. What we actually want to know is how the
    engines compare on solid blocks of Devanagari, because that is what gets
    translated. So: drop the front matter, then take the pages with the most
    Devanagari word tokens. (2026-08-29)
    """
    cands = []
    for p in sorted(globmod.glob(os.path.join(raw, f"{doc}_*.jsonl"))):
        m = PAGE_RE.match(os.path.basename(p))
        if not m or m.group(1) != doc:
            continue
        t = jtext(p)
        if not t:
            continue
        ntok = len(toks(t))
        if ntok < min_tokens:
            continue
        pdf = os.path.join(inbox, f"{doc}_{m.group(2)}.pdf")
        if os.path.exists(pdf):
            cands.append((pdf, p, ntok, int(m.group(2))))
    if not cands:
        return []
    # Drop front matter, but never drop so much that nothing is left.
    if len(cands) > 10:
        cut = max(cands, key=lambda c: c[3])[3] * skip_front
        trimmed = [c for c in cands if c[3] > cut]
        if len(trimmed) >= n:
            cands = trimmed
    cands.sort(key=lambda c: -c[2])            # densest first
    return [(c[0], c[1]) for c in cands[:n]]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", default=None)
    ap.add_argument("--all", action="store_true", help="probe every document found in --raw")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--probe-dir", default="data/probe")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--poppler-bin", default=os.environ.get("POPPLER_BIN") or os.environ.get("POPPLER_PATH"))
    ap.add_argument("--results", default="data/ocr_probe_results.json")
    ap.add_argument("--report", action="store_true", help="print stored results, make no calls")
    ap.add_argument("--self-check", action="store_true",
                    help="CONTROL EXPERIMENT: transcribe already-probed pages a SECOND time "
                         "at a different temperature and measure vision-vs-vision agreement. "
                         "This is the metric's ceiling. Without it, a Tesseract score of 0.73 "
                         "cannot be told apart from 'this is as high as the number ever goes'.")
    ap.add_argument("--self-temp", type=float, default=0.3)
    ap.add_argument("--self-pages", type=int, default=12)
    ap.add_argument("--yes", action="store_true", help="actually call the API")
    args = ap.parse_args()

    if args.report:
        try:
            stored = json.load(open(args.results, encoding="utf-8"))
        except Exception as exc:
            sys.exit(f"no stored results at {args.results} ({exc})")
        render(stored)
        return

    if args.self_check:
        self_check(args); return

    if not args.doc and not args.all:
        ap.error("give --doc <CODE> or --all")

    docs = []
    if args.doc:
        docs = [args.doc]
    else:
        seen = set()
        for p in globmod.glob(os.path.join(args.raw, "*.jsonl")):
            m = PAGE_RE.match(os.path.basename(p))
            if m:
                seen.add(m.group(1))
        docs = sorted(seen)

    plan = {d: sample_pages(d, args.raw, args.inbox, args.pages) for d in docs}
    plan = {d: v for d, v in plan.items() if v}
    total = sum(len(v) for v in plan.values())
    print(f"documents: {len(plan)}   pages to probe: {total}   "
          f"est. ${total*0.00087:.3f}   ({'LIVE' if args.yes else 'DRY-RUN'})")
    for d, v in plan.items():
        print(f"  {d[:52]:52s} {len(v)} page(s)")
    if not args.yes:
        print("\nRe-run with --yes to probe. Nothing was called or written.")
        return

    import ocr_vision  # reuse the audited transcription path, incl. retry ladder
    meter = None
    mcon = None
    try:
        import sqlite3
        from usage_meter import meter as _meter, budget_ok
        mcon = sqlite3.connect(args.db, timeout=30)
        mcon.execute("PRAGMA busy_timeout=30000")
        if not budget_ok(mcon):
            print("Refusing to start: spend cap reached."); return
        meter = _meter
    except Exception as exc:
        print(f"  [warn] metering unavailable ({exc}); spend will NOT be recorded")

    Path(args.probe_dir).mkdir(parents=True, exist_ok=True)
    results = {}
    spend = 0.0
    for d, pages in plan.items():
        rates, contam_t, contam_v, back, ntok = [], [], [], [], []
        for pdf, tess_json in pages:
            stem = Path(pdf).stem
            out = Path(args.probe_dir) / f"{stem}.jsonl"
            try:
                if out.exists():
                    vtext = jtext(str(out)) or ""
                else:
                    t0 = time.time()
                    img = ocr_vision.render_page(pdf, args.dpi, args.poppler_bin)
                    vtext, resp, _raw = ocr_vision.transcribe(img, args.model)
                    if meter is not None:
                        spend += meter(kind="ocr_probe", doc=d,
                                       engine=f"gemini-vision:{args.model}", resp=resp,
                                       out_chars=len(vtext), units=1,
                                       duration_s=time.time() - t0, con=mcon)
                    out.write_text(json.dumps(
                        {"engine": f"gemini-vision:{args.model}", "text": vtext,
                         "src_pdf": Path(pdf).name, "probe": True},
                        ensure_ascii=False) + "\n", encoding="utf-8")
            except Exception as exc:
                print(f"  [err] {stem}: {type(exc).__name__}: {exc}")
                continue
            ttext = jtext(tess_json) or ""
            tt, vt = toks(ttext), set(toks(vtext))
            if len(tt) < 40:
                continue
            rates.append(sum(1 for w in tt if w in vt) / len(tt))
            vtl = toks(vtext)
            st = set(tt)
            if vtl:
                back.append(sum(1 for w in vtl if w in st) / len(vtl))
            ntok.append(len(tt))
            contam_t.append(contamination(ttext))
            contam_v.append(contamination(vtext))
        if rates:
            results[d] = {
                "pages": len(rates),
                "token_agreement": round(statistics.median(rates), 4),
                # V->T is reported because the two together tell you WHO is wrong.
                # Symmetric values mean vision is the better reading and the figure
                # approximates Tesseract's word accuracy; a large gap would mean one
                # engine is simply producing more text than the other.
                "reverse_agreement": round(statistics.median(back), 4) if back else None,
                "median_tokens": int(statistics.median(ntok)) if ntok else 0,
                "contam_tesseract": round(statistics.median(contam_t), 4),
                "contam_vision": round(statistics.median(contam_v), 4),
            }
            # Save after EVERY document: the first probe run was interrupted and
            # lost all verdicts although the pages were already cached and paid for.
            try:
                _prev = {}
                if os.path.exists(args.results):
                    _prev = json.load(open(args.results, encoding="utf-8"))
                _prev.update(results)
                json.dump(_prev, open(args.results, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
            except Exception:
                pass
            print(f"  {d[:52]:52s} agreement={results[d]['token_agreement']:.3f}")

    if mcon is not None:
        mcon.close()
    try:
        prev = json.load(open(args.results, encoding="utf-8"))
    except Exception:
        prev = {}
    prev.update(results)
    json.dump(prev, open(args.results, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nMEASURED spend this run: ${spend:.4f}   results -> {args.results}")
    render(prev)


def self_check(args):
    """Vision vs vision on the SAME pages: what does 'perfect' actually score?

    Every per-document figure in this tool is a comparison against vision. If
    vision only agrees with ITSELF at, say, 0.80, then a Tesseract score of 0.73
    is close to the ceiling and means something very different from what it
    looks like. Measuring the ceiling costs about a cent and is the difference
    between a finding and an assumption. (2026-08-29)
    """
    import ocr_vision
    cached = sorted(globmod.glob(os.path.join(args.probe_dir, "*.jsonl")))
    if not cached:
        sys.exit("no cached probe pages; run the probe first")
    step = max(1, len(cached) // args.self_pages)
    picks = cached[::step][:args.self_pages]
    print(f"self-consistency control: {len(picks)} pages, second pass at "
          f"temperature={args.self_temp}   est. ${len(picks)*0.00087:.3f}   "
          f"({'LIVE' if args.yes else 'DRY-RUN'})")
    if not args.yes:
        for p in picks:
            print(f"  would re-transcribe: {os.path.basename(p)}")
        print("Re-run with --yes.")
        return

    meter = mcon = None
    try:
        import sqlite3
        from usage_meter import meter as _m
        mcon = sqlite3.connect(args.db, timeout=30)
        mcon.execute("PRAGMA busy_timeout=30000"); meter = _m
    except Exception:
        pass

    rates, spend = [], 0.0
    for cp in picks:
        stem = os.path.splitext(os.path.basename(cp))[0]
        pdf = os.path.join(args.inbox, stem + ".pdf")
        if not os.path.exists(pdf):
            continue
        first = jtext(cp) or ""
        if len(toks(first)) < 40:
            continue
        try:
            t0 = time.time()
            img = ocr_vision.render_page(pdf, args.dpi, args.poppler_bin)
            second, resp, _ = ocr_vision.transcribe(img, args.model,
                                                    temperature=args.self_temp)
            if meter is not None:
                spend += meter(kind="ocr_probe", doc="(self-check)",
                               engine=f"gemini-vision:{args.model}", resp=resp,
                               out_chars=len(second), units=1,
                               duration_s=time.time() - t0, con=mcon)
        except Exception as exc:
            print(f"  [err] {stem}: {exc}"); continue
        a, b = toks(first), set(toks(second))
        if not a:
            continue
        r = sum(1 for w in a if w in b) / len(a)
        rates.append(r)
        print(f"  {stem[:52]:52s} vision-vs-vision = {r:.3f}")

    if mcon is not None:
        mcon.close()
    if not rates:
        print("no comparable pages."); return
    med = statistics.median(rates)
    print(f"\n  CEILING (median vision-vs-vision agreement): {med:.3f}")
    print(f"  measured spend: ${spend:.4f}")
    print("\n  How to read this against the per-document table:")
    print(f"    A document scoring near {med:.2f} is as good as this metric can show.")
    print(f"    A document well below {med:.2f} has genuinely different words.")
    print("    If the ceiling is ~0.95, the 0.34-0.73 spread is real Tesseract error.")
    print("    If the ceiling is ~0.75, the top of that spread is measurement noise")
    print("    and the whole per-document ranking needs re-interpreting.")


def render(results: dict):
    print("\n" + "=" * 78)
    print("PER-DOCUMENT OCR VERDICT")
    print("=" * 78)
    print(f"  {'document':40s} {'pg':>3} {'T->V':>6} {'V->T':>6} {'tok':>4} "
          f"{'contam_T':>8}   verdict")
    print("  " + "-" * 84)
    rows = sorted(results.items(), key=lambda kv: kv[1]["token_agreement"])
    for d, r in rows:
        a = r["token_agreement"]
        v = ("VISION NEEDED" if a < 0.55 else
             "probe more" if a < GOOD_ENOUGH else "tesseract OK")
        rev = r.get("reverse_agreement")
        print(f"  {d[:40]:40s} {r['pages']:>3} {a:>6.3f} "
              f"{(f'{rev:.3f}' if rev is not None else '   -'):>6} "
              f"{r.get('median_tokens',0):>4} {r['contam_tesseract']:>8.4f}   {v}")
    if rows:
        vals = [r["token_agreement"] for _, r in rows]
        print(f"\n  range {min(vals):.3f} - {max(vals):.3f}")
        print(f"  BAD anchor (Shatpatha, AphorismsOfSandilya): ~{BAD_ANCHOR}")
        print("  If every document lands near the bad anchor, Tesseract is unusable")
        print("  across this corpus and the honest answer is vision everywhere.")
        print("  If a clear high band appears, the midpoint is your real threshold -")
        print("  set it from THIS data, not from the provisional 0.55/0.75 above.")


if __name__ == "__main__":
    main()
