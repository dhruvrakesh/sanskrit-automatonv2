#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_token_ratio.py - is the chars/4 assumption actually true for OUR corpus?
(2026-08-29)  READ-ONLY on the DB. Uses count_tokens, which is not billed.

WHY THIS MATTERS
----------------
cost_tracker prices every translation call as `chars / 4 = tokens`. That ratio
comes from English prose. Our inputs are Devanagari and IAST:

  * Devanagari is 3 bytes per character in UTF-8 and is not well covered by a
    byte-pair vocabulary trained mostly on Latin script, so it can cost
    MORE than one token per character - the opposite direction from 4.
  * IAST carries combining diacritics, which frequently split.
  * The English output side is ordinary prose and should be near 4.

If the real input ratio is, say, 1.2 chars/token, then every input token count
in usage_log is understated by ~3.3x and $6.98 of recorded translation spend is
not $6.98. This script measures it instead of assuming it, per script kind, and
prints the correction factor to apply.

  python scripts\\diag_token_ratio.py --sample 40
  python scripts\\diag_token_ratio.py --sample 40 --engine gemini:gemini-2.5-flash
"""
from __future__ import annotations
import argparse, os, sqlite3, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from env_loader import load_env
    load_env()          # importing the module is NOT enough - it must be CALLED.
except Exception as _exc:
    print(f"[warn] env_loader.load_env() failed: {_exc}", file=sys.stderr)

CHARS_PER_TOKEN_ASSUMED = 4.0


def _script_of(s: str) -> str:
    dev = sum(1 for ch in s if "ऀ" <= ch <= "ॿ")
    lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
    dia = sum(1 for ch in s if unicodedata.combining(ch))
    if dev > max(10, lat):
        return "devanagari"
    if dia > len(s) * 0.02:
        return "iast"
    return "latin"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--sample", type=int, default=40, help="passages per script class")
    ap.add_argument("--engine", default=os.environ.get("MT_ENGINE", "gemini:gemini-2.5-flash"))
    args = ap.parse_args()

    try:
        import google.generativeai as genai
    except Exception:
        sys.exit("google-generativeai is required.")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set in .env")
    genai.configure(api_key=key)
    model_name = args.engine.split(":", 1)[1] if ":" in args.engine else args.engine
    gm = genai.GenerativeModel(model_name=model_name)

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=30)
    rows = con.execute("""
        SELECT COALESCE(p.text,''), COALESCE(p.iast,''), COALESCE(p.translation,'')
        FROM passages p JOIN docs d ON d.id = p.doc_id
        WHERE TRIM(COALESCE(p.text,'')) <> '' AND TRIM(COALESCE(p.translation,'')) <> ''
          AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
          AND d.code NOT LIKE '%-RETIRED'
        ORDER BY p.id
    """).fetchall()
    con.close()
    if not rows:
        sys.exit("no translated passages to sample.")

    step = max(1, len(rows) // max(1, args.sample))
    picked = rows[::step][: args.sample]
    print(f"Sampling {len(picked)} passages of {len(rows)} translated "
          f"(count_tokens on {model_name}; this call is not billed)\n")

    buckets: dict[str, list[tuple[int, int]]] = {}

    def add(label: str, text: str):
        text = (text or "").strip()
        if len(text) < 20:
            return
        try:
            n = gm.count_tokens(text).total_tokens
        except Exception as exc:
            print(f"  count_tokens failed: {exc}")
            return
        buckets.setdefault(label, []).append((len(text), n))

    for i, (src, iast, tr) in enumerate(picked, 1):
        add(f"source:{_script_of(src)}", src)
        if iast:
            add("source:iast", iast)
        add("output:english", tr)
        if i % 10 == 0:
            print(f"  ...{i}/{len(picked)}", flush=True)

    print("\n" + "=" * 72)
    print(f"{'text class':22s} {'n':>4} {'chars':>8} {'tokens':>8} {'chars/tok':>10} {'vs 4.0':>9}")
    print("=" * 72)
    worst = None
    for label in sorted(buckets):
        pairs = buckets[label]
        ch = sum(c for c, _ in pairs)
        tk = sum(t for _, t in pairs)
        ratio = ch / tk if tk else 0
        factor = CHARS_PER_TOKEN_ASSUMED / ratio if ratio else 0
        print(f"{label:22s} {len(pairs):>4} {ch:>8} {tk:>8} {ratio:>10.2f} {factor:>8.2f}x")
        if label.startswith("source") and (worst is None or factor > worst[1]):
            worst = (label, factor)

    print("\nHOW TO READ 'vs 4.0': it is the multiplier by which cost_tracker")
    print("UNDER-counts tokens for that text class. 1.00x means chars/4 was right.")
    print("3.00x means the real token count is three times what we logged.\n")

    if worst and worst[1] > 1.25:
        print(f"VERDICT: chars/4 is wrong for our inputs. Worst class '{worst[0]}' is")
        print(f"  under-counted {worst[1]:.2f}x. Recorded translation spend is a FLOOR,")
        print(f"  not an estimate. Two honest fixes, in order of preference:")
        print(f"    1. capture the provider's own token counts at the call site")
        print(f"       (usage_meter.meter(..., resp=resp)) - exact, no ratio needed;")
        print(f"    2. failing that, set _CHARS_PER_TOKEN in cost_tracker.py per script.")
    elif worst:
        print(f"VERDICT: chars/4 holds within {abs(worst[1]-1)*100:.0f}% for our inputs.")
        print("  The recorded figures are defensible as estimates.")
    print("\nEither way, check the provider console for the ground truth.")


if __name__ == "__main__":
    main()
