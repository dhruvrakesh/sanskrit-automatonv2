#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_vision.py - LLM-vision OCR for pages Tesseract cannot read (2026-08-28).

WHY THIS EXISTS (measured, not assumed):
  Tesseract misreads pre-1900 Devanagari founts (e.g. the 1861 Bibliotheca Indica) into
  confident but WRONG Devanagari - "प्राख्डिल्यग्रतखनीयं भाव्यम् [अव्शब्यान््र]". An A/B at
  400 vs 600 DPI with every preprocessing variant produced dev=0.98 both times: no gain
  (see BENCHMARKS.md). The scans themselves are clean and perfectly legible - a vision
  model reads them without difficulty. So the fix is a better READER, not a better scan.

Writes the SAME JSONL record shape as ocr_pdf.py, so the existing ingest path
(ingest_jsonl_fast.py) consumes it unchanged. engine='gemini-vision' marks provenance.

COST-AWARE: dry-run by default (renders + reports, no API call). MEASURED $0.00073/page
on flash (2026-08-29) - a 300-page book is about $0.22. Use --limit to bound any run.
Every page is metered from the provider's own token counts; the estimate above is only
a pre-flight figure and the run prints what it actually cost.

  python scripts/ocr_vision.py --pdf inbox\\AphorismsOfSandilya_0050.pdf --out tmp.jsonl
  python scripts/ocr_vision.py --pdf inbox\\AphorismsOfSandilya_0050.pdf --out tmp.jsonl --yes
  python scripts/ocr_vision.py --glob "inbox\\AphorismsOfSandilya_*.pdf" --outdir data\\raw --yes
"""
from __future__ import annotations
import argparse, glob as globmod, io, json, os, re, sys, time, zlib
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

DEV_LETTER_RE = re.compile(r"[ऀ-ॣ॰-ॿ]")
LAT_RE        = re.compile(r"[A-Za-z]")
COST_PER_PAGE = 0.00028   # VISION_FINISH_2026_10_03: re-measured 2026-09-30 (Mallapurana);
                          # was 0.00073, MEASURED 2026-08-29 from provider token counts on a
                          # 300-dpi Shatpatha page (was 0.0004, an unverified guess).
                          # Re-measure if the model, DPI or prompt changes.
MODEL_DEFAULT = "gemini-2.5-flash"

PROMPT = (
    "You are transcribing a page from a printed Sanskrit book (19th-century Indian press, "
    "Devanagari with occasional Latin footnote markers).\n"
    "Transcribe EXACTLY what is printed. Rules:\n"
    "1. Output the Devanagari text verbatim, preserving line breaks, dandas (। ॥) and "
    "verse numbers as printed.\n"
    "2. Do NOT translate, explain, correct, normalise or add anything.\n"
    "3. If a portion of the page is printed in English (running heads, footnotes, an "
    "English translation section), transcribe it as English, in place.\n"
    "4. If a character is genuinely illegible use a single '?' - never guess a whole word.\n"
    "5. Ignore page furniture that is not text (library stamps, scan watermarks).\n"
    "6. Output ONLY the transcription. No preamble, no commentary, no code fences."
)


def dev_frac(s: str) -> float:
    """Devanagari share of the LETTERS only.

    Careful: this deliberately ignores everything that is not a letter, so it
    cannot see runaway punctuation. A page of 129,000 underscores containing 200
    real Devanagari characters scores 1.00 here, which is exactly how nine bad
    Shatpatha pages slipped past the progress line on 2026-08-29. dev_frac is
    NOT a health check on its own - collapse_runs() and the length checks are.
    """
    d, l = len(DEV_LETTER_RE.findall(s or "")), len(LAT_RE.findall(s or ""))
    t = d + l
    return d / t if t else 0.0


# A vision model can latch onto a horizontal rule, a dotted leader or a row of
# dashes and emit tens of thousands of identical characters until its output
# budget runs out. Observed on 9 of 194 Shatpatha pages: page 0003 returned
# 129,421 chars of which the genuine transcription was the first ~200 and the
# rest one unbroken run of "_". No Sanskrit text repeats a single character
# eight times, so collapsing such runs is lossless for real content.
_RUN_RE = re.compile(r"(.)\1{7,}", re.S)
RUNAWAY_CHARS = 20000          # a printed book page is ~2,500 chars

# The nastier failure: the model repeats a whole PHRASE hundreds of times inside
# one line. The text is real Sanskrit, so no character rule and no quality score
# can see it. Compression ratio can, and it is alignment-free. Measured over 194
# Shatpatha pages: 9 degenerate pages scored 0.0035-0.0292, 185 ordinary pages
# scored 0.1347-0.4766. 0.08 sits in the empty band between them. Such pages are
# FLAGGED, never auto-truncated - Brahmana texts do repeat formulae, and cutting
# a genuine refrain would be worse than the bug.
# KNOWN LIMIT: a synthetic page of a genuinely repeated Vedic refrain scores
# ~0.049, i.e. below this cut-off; it escapes only because of LOOP_MIN_CHARS.
# On 185 real pages the worst ordinary score was 0.1347, so the margin holds in
# practice - but a truly refrain-heavy long page WILL be flagged. The cost of
# that false positive is one wasted re-OCR, never lost text, which is why this
# flags and never truncates.
LOOP_RATIO = 0.08
LOOP_MIN_CHARS = 3000
# Retry ladder. 0.0 is used for the first attempt because verbatim transcription
# wants determinism; these only apply once a page has already failed, where the
# determinism is precisely the problem.
RETRY_TEMPS = (0.3, 0.7)
# VISION_FINISH_2026_10_03 - output-budget ladder for finish_reason=MAX_TOKENS,
# the same remedy infer_mt.py uses (thinking tokens count against the budget).
MAXTOK_LADDER = tuple(int(x) for x in
                      os.environ.get("OCR_MAXTOK_LADDER", "16384,32768").split(",") if x.strip())


def _finish_name(resp):
    """Provider finish_reason as a name: STOP, MAX_TOKENS, SAFETY, RECITATION, or None."""
    try:
        cands = getattr(resp, "candidates", None)
        fr = cands[0].finish_reason if cands else None
    except Exception:
        return None
    if fr is None:
        return None
    name = getattr(fr, "name", None)
    if name:
        return str(name)
    try:
        return {1: "STOP", 2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION"}.get(int(fr), str(fr))
    except Exception:
        return str(fr)


NEAR_EMPTY = 5   # VISION_FINISH2_2026_10_03: same threshold as merge_ocr_sources.DEFINITELY_EMPTY
LAST_TILES = [0]  # bands used for the most recent page (0 = whole page); read into meta
# VISION_FINISH3_2026_10_03: banding did not beat RECITATION on any of 5 pages; off by default.
RECITATION_TILES = tuple(int(x) for x in os.environ.get("OCR_RECITATION_TILES", "").split(",") if x.strip())
_TRANSIENT = ("DeadlineExceeded", "ServiceUnavailable", "InternalServerError", "TooManyRequests",
              "ResourceExhausted", " 429", " 500", " 503", " 504")


def _with_retry(fn, wait_s=6.0):
    """Retry a call once on a transient provider error (VISION_FINISH3_2026_10_03)."""
    def call(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            tag = type(e).__name__ + " " + str(e)[:200]
            if not any(t in tag for t in _TRANSIENT):
                raise
            print(f"      [retry] transient {type(e).__name__}; once more in {wait_s:.0f}s")
            if wait_s:
                time.sleep(wait_s)
            return fn(*a, **k)
    return call


def _page_problem(t):
    if len((t or "").strip()) < NEAR_EMPTY:
        return "empty"
    if len(t) >= LOOP_MIN_CHARS and compress_ratio(t) < LOOP_RATIO:
        return "phrase loop"
    return None


def _cut_rows(img, n):
    """Row indices that split the page into n bands, each cut placed on the whitest
    row (least ink) within +-8% of the even split, so no printed line is cut."""
    g = img.convert("L").resize((48, img.height))
    w, h = g.size
    px = list(g.getdata())
    ink = [sum(255 - px[r * w + c] for c in range(w)) for r in range(h)]
    win = max(3, h // 300)
    smooth = [sum(ink[max(0, r - win):r + win + 1]) for r in range(h)]
    cuts = []
    for k in range(1, n):
        target = h * k // n
        lo, hi = max(1, target - h * 8 // 100), min(h - 1, target + h * 8 // 100)
        least = min(smooth[lo:hi])
        cuts.append(min((r for r in range(lo, hi) if smooth[r] <= least), key=lambda r: abs(r - target)))
    return sorted(set(cuts))


def _transcribe_tiled(img, model_name, name, tfn, n, budget):
    """Transcribe n horizontal bands. Returns (text or "", resps). All-or-nothing."""
    cuts = [0] + _cut_rows(img, n) + [img.height]
    texts, resps = [], []
    for i in range(len(cuts) - 1):
        band = img.crop((0, cuts[i], img.width, cuts[i + 1]))
        t, r, _ = tfn(band, model_name, max_tokens=budget)
        resps.append(r)
        if _page_problem(t):
            print(f"      [tiles] {name}: band {i + 1}/{len(cuts) - 1} failed ({_finish_name(r)})")
            return "", resps
        texts.append(t.strip())
    return "\n".join(texts), resps


def transcribe_robust(img, model_name, name, tfn=None, sleep_s=2.0):
    """One page with the recovery ladders. Returns (text, resp, raw_len, discarded).
    discarded = responses that were paid for but are not `resp` (retries, bands)."""
    tfn = _with_retry(tfn or transcribe, 0.0 if sleep_s == 0 else 6.0)   # VISION_FINISH3_2026_10_03
    discarded = []
    budget = 8192
    LAST_TILES[0] = 0
    text, resp, raw_len = tfn(img, model_name)
    if _finish_name(resp) == "MAX_TOKENS":
        # VISION_FINISH2_2026_10_03: MAX_TOKENS means truncated, at any length.
        best = (text, resp, raw_len)
        for b in MAXTOK_LADDER:
            print(f"      [retry] {name}: MAX_TOKENS ({len((text or '').strip())} chars), max_output_tokens={b}")
            budget = b
            t3, r3, rl3 = tfn(img, model_name, max_tokens=b)
            if len((t3 or "").strip()) >= len((best[0] or "").strip()):
                discarded.append(best[1]); best = (t3, r3, rl3)
            else:
                discarded.append(r3)
            if _finish_name(r3) != "MAX_TOKENS":
                break
        text, resp, raw_len = best
    problem = _page_problem(text)
    for temp in RETRY_TEMPS:
        if not problem:
            break
        if _finish_name(resp) == "RECITATION":   # VISION_FINISH3_2026_10_03: temperature never helps
            break
        print(f"      [retry] {name}: {problem}, retrying at temperature={temp}")
        if sleep_s:
            time.sleep(sleep_s)
        t2, r2, rl2 = tfn(img, model_name, temperature=temp, max_tokens=budget)
        if not _page_problem(t2):
            print(f"      [retry] {name}: clean at temperature={temp}, using it")
            discarded.append(resp)
            text, resp, raw_len = t2, r2, rl2
            problem = None
        elif (t2 or "").strip() and problem == "empty":
            # still imperfect, but text beats nothing - keep the best so far
            discarded.append(resp)
            text, resp, raw_len = t2, r2, rl2
            problem = _page_problem(text)
        else:
            discarded.append(r2)
    if problem == "empty" and _finish_name(resp) == "RECITATION" and img is not None:
        # VISION_FINISH2_2026_10_03: shorter passages are not refused as recitation.
        for n in RECITATION_TILES:   # VISION_FINISH3_2026_10_03: empty unless OCR_RECITATION_TILES is set
            print(f"      [tiles] {name}: RECITATION, transcribing in {n} bands")
            tt, rs = _transcribe_tiled(img, model_name, name, tfn, n, budget)
            if tt:
                discarded.append(resp); discarded.extend(rs[:-1])
                text, resp, raw_len = tt, rs[-1], len(tt)
                LAST_TILES[0] = n
                break
            discarded.extend(rs)
    return text, resp, raw_len, discarded


def compress_ratio(s: str) -> float:
    b = (s or "").encode("utf-8")
    return len(zlib.compress(b, 6)) / len(b) if b else 1.0


def collapse_runs(s: str, keep: int = 8) -> str:
    return _RUN_RE.sub(lambda m: m.group(1) * keep, s or "")


def render_page(pdf: str, dpi: int, poppler_bin: str | None):
    from pdf2image import convert_from_path
    kw = dict(dpi=dpi)
    if poppler_bin:
        kw["poppler_path"] = poppler_bin
    pages = convert_from_path(pdf, **kw)
    if not pages:
        raise RuntimeError(f"no pages rendered from {pdf}")
    return pages[0]


def transcribe(img, model_name: str, timeout_s: int = 120, temperature: float = 0.0,
               max_tokens: int = 8192):  # VISION_FINISH_2026_10_03: budget is a parameter
    """Returns (text, resp). The response is handed back so the caller can read
    the provider's own token counts out of it - an image's cost cannot be
    derived from character counts, so anything else would be a guess."""
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # temperature is a parameter, not a constant. At 0.0 sampling is deterministic,
    # so retrying a page that fell into a degenerate repetition loop reproduces the
    # SAME loop byte for byte - observed 2026-08-29 on pages 0215 and 0302, which
    # looped identically on two independent calls. Breaking the cycle needs a
    # different sampling path, which means a non-zero temperature on the retry.
    cfg = genai.GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
    gm = genai.GenerativeModel(model_name=model_name, generation_config=cfg,
                               system_instruction=PROMPT)
    resp = gm.generate_content([{"mime_type": "image/png", "data": buf.getvalue()}],
                               request_options={"timeout": timeout_s})
    try:
        txt = (resp.text or "").strip()
    except Exception:
        txt = ""
    if txt.startswith("```"):
        txt = re.sub(r"^```[A-Za-z]*\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt).strip()
    raw_len = len(txt)
    txt = collapse_runs(txt)
    return txt, resp, raw_len


def page_no_from_name(name: str) -> int:
    m = re.search(r"_(\d{4})\.pdf$", name, re.IGNORECASE)
    return int(m.group(1)) if m else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", help="single page-PDF")
    ap.add_argument("--glob", dest="globpat", help="glob of page-PDFs, e.g. \"inbox\\Doc_*.pdf\"")
    ap.add_argument("--out", help="output JSONL (single --pdf mode)")
    ap.add_argument("--outdir", help="output dir (glob mode); one .jsonl per page-PDF")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--dpi", type=int, default=300, help="render DPI sent to the model (300 is plenty)")
    ap.add_argument("--poppler-bin", default=os.environ.get("POPPLER_BIN") or os.environ.get("POPPLER_PATH"))
    ap.add_argument("--limit", type=int, default=0, help="cap pages processed (0 = no cap)")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--skip-existing", action="store_true", help="glob mode: skip pages whose .jsonl exists")
    ap.add_argument("--db", default="data/context.db",
                    help="DB to record spend into (usage_log / budget_state)")
    ap.add_argument("--doc", default=None, help="doc code to attribute this spend to")
    ap.add_argument("--no-meter", action="store_true",
                    help="do not record spend (diagnostics only; leaves the budget blind)")
    ap.add_argument("--yes", action="store_true", help="actually call the API (default: dry-run)")
    args = ap.parse_args()

    if not args.pdf and not args.globpat:
        ap.error("give --pdf <file> or --glob <pattern>")

    targets = [args.pdf] if args.pdf else sorted(globmod.glob(args.globpat))
    if args.outdir and args.skip_existing:
        targets = [t for t in targets
                   if not (Path(args.outdir) / (Path(t).stem + ".jsonl")).exists()]
    if args.limit:
        targets = targets[:args.limit]
    if not targets:
        print("nothing to do."); return

    print(f"pages: {len(targets)}   model: {args.model}   dpi: {args.dpi}   "
          f"({'LIVE' if args.yes else 'DRY-RUN'})")
    print(f"  pre-flight estimate: ${len(targets)*COST_PER_PAGE:.3f} at ${COST_PER_PAGE}/page "
          f"-- this is an ESTIMATE ONLY. The real per-page cost is measured from the "
          f"provider's own token counts after each call and totalled at the end.")
    if not args.yes:
        for t in targets[:10]:
            print(f"  would transcribe: {Path(t).name}")
        if len(targets) > 10:
            print(f"  ... and {len(targets)-10} more")
        print("Re-run with --yes to transcribe. Nothing was called or written.")
        return

    # Metering: opened once for the whole run so we are not reconnecting per page.
    meter = None
    mcon = None
    if not args.no_meter:
        try:
            import sqlite3 as _sq
            from usage_meter import meter as _meter, budget_ok as _budget_ok
            mcon = _sq.connect(args.db, timeout=30)
            mcon.execute("PRAGMA busy_timeout=30000")
            meter = _meter
            if not _budget_ok(mcon):
                print("Refusing to start: the spend cap is already reached.")
                mcon.close(); return
        except Exception as exc:
            print(f"  [warn] spend metering unavailable ({type(exc).__name__}: {exc}); "
                  f"this run's cost will NOT be recorded.")

    ok = err = 0
    spend = 0.0
    engine_tag = f"gemini-vision:{args.model}"
    for n, pdf in enumerate(targets, 1):
        name = Path(pdf).name
        try:
            t0 = time.time()
            img = render_page(pdf, args.dpi, args.poppler_bin)
            # VISION_FINISH_2026_10_03: budget ladder, then temperature ladder.
            text, resp, raw_len, discarded = transcribe_robust(img, args.model, name)
            if meter is not None:
                spend += meter(kind="ocr_vision", doc=args.doc, engine=engine_tag,
                               resp=resp, out_chars=len(text), units=1,
                               duration_s=time.time() - t0, con=mcon)
                for _r in discarded:   # VISION_FINISH_2026_10_03: paid retries are recorded too
                    spend += meter(kind="ocr_vision", doc=args.doc, engine=engine_tag,
                                   resp=_r, out_chars=0, units=0, duration_s=0.0, con=mcon)
            rec = {
                "engine": f"gemini-vision:{args.model}",
                "page_no": page_no_from_name(name),
                "text": text,
                "meta": {"dpi": args.dpi, "model": args.model, "dev": round(dev_frac(text), 3),
                         "finish": _finish_name(resp), "retries": len(discarded),
                         "tiles": LAST_TILES[0],  # VISION_FINISH2_2026_10_03
                         "raw_len": raw_len, "collapsed": bool(raw_len > len(text)),
                         "compress": round(compress_ratio(text), 4),
                         "suspect": bool(len(text) > RUNAWAY_CHARS
                                         or len(text.strip()) < 40
                                         or (len(text) >= LOOP_MIN_CHARS
                                             and compress_ratio(text) < LOOP_RATIO))},
                "src_pdf": name,
            }
            out_path = Path(args.out) if args.pdf else Path(args.outdir) / (Path(pdf).stem + ".jsonl")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ok += 1
            flags = ""
            if raw_len > len(text):
                flags += f"  COLLAPSED {raw_len:,}->{len(text):,} (runaway repeat)"
            if len(text) > RUNAWAY_CHARS:
                flags += f"  WARN {len(text):,} chars - inspect this page"
            if len(text.strip()) < 40:
                flags += "  WARN near-empty - needs re-OCR"
            _cr = compress_ratio(text)
            if len(text) >= LOOP_MIN_CHARS and _cr < LOOP_RATIO:
                flags += (f"  WARN phrase loop (compress={_cr:.4f}) - "
                          f"re-OCR this page, do not ingest")
            print(f"  [{n}/{len(targets)}] {name}: {len(text)} chars  "
                  f"dev={dev_frac(text):.2f} -> {out_path}{flags}")
        except Exception as e:
            err += 1
            print(f"  [{n}/{len(targets)}] {name}: ERROR {type(e).__name__}: {e}")
        time.sleep(args.sleep)

    print(f"\nDone. transcribed={ok} errors={err}")
    if meter is not None:
        per = (spend / ok) if ok else 0.0
        print(f"MEASURED spend this run: ${spend:.4f}  ({ok} pages, ${per:.5f}/page) "
              f"-- from the provider's token counts, recorded as kind='ocr_vision'.")
        if ok and abs(per - COST_PER_PAGE) / max(per, 1e-9) > 0.25:
            print(f"  NOTE: the ${COST_PER_PAGE}/page pre-flight estimate is off by more than "
                  f"25%. Update COST_PER_PAGE to {per:.5f} in ocr_vision.py.")
    if mcon is not None:
        mcon.close()
    if args.outdir:
        print("Next: ingest with  python scripts\\ingest_jsonl_fast.py --doc <CODE> "
              f"--glob \"{args.outdir}\\<CODE>_*.jsonl\" --db data\\context.db")


if __name__ == "__main__":
    main()
