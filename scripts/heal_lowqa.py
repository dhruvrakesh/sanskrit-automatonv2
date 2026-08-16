#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
heal_lowqa.py — one-click QA heal for a single doc (2026-08-16).

Runs the full NON-DESTRUCTIVE heal loop for one document, in order:
  1. qa_scan.py            --write   → refresh translation_qa so the selection
                                       reflects the current scorer (idempotent)
  2. retranslate.py --below-qa T --yes → archive the low-QA translations to
                                       translation_history, then clear their
                                       slots (history-preserving; nothing lost)
  3. translate_passages.py           → refill the cleared slots under the
                                       current prompt/engine

This is the single operation the dashboard "Heal low-QA" button invokes, so the
operator never has to remember the scan -> clear -> refill sequence by hand.

Lang-aware: --lang hi heals the Hindi track in translations_l10n and never
touches the English translation. Because step 3 refills every empty slot in the
doc, a heal also completes any verses that were never translated in that
language — that is intentional (heal = make the doc whole), not a side effect.

Each step runs as its own subprocess reusing the already-tested CLIs, so their
argument handling and safety guards (dry-run refusal, single-writer discipline)
are preserved exactly. Steps run strictly in sequence — never concurrently —
so the SQLite single-writer invariant holds.

Usage:
  python scripts/heal_lowqa.py --doc MBh01 --below-qa 0.2
  python scripts/heal_lowqa.py --doc nilamata_seg --lang hi --below-qa 0.2 \
         --engine gemini:gemini-2.5-flash
  python scripts/heal_lowqa.py --doc shiksha --below-qa 0.4 --skip-scan
"""
from __future__ import annotations
import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _run(step: str, argv: list[str]) -> int:
    print(f"\n{'=' * 64}\n[heal] {step}\n{'=' * 64}", flush=True)
    print("  $ " + " ".join(argv), flush=True)
    try:
        r = subprocess.run(argv, cwd=str(ROOT))
        rc = r.returncode
    except Exception as e:  # never let a step crash the whole heal silently
        print(f"[heal] {step} raised {type(e).__name__}: {e}", flush=True)
        return 1
    print(f"[heal] {step} exit={rc}", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser(
        description="One-click QA heal for a doc (scan -> archive+clear -> refill)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True, help="doc code to heal")
    ap.add_argument("--below-qa", type=float, default=0.2,
                    help="archive+clear+refill rows scoring below this (default 0.2)")
    ap.add_argument("--lang", default="en",
                    help="'en' (default) heals passages.translation; any other "
                         "code (e.g. 'hi') heals translations_l10n of that "
                         "language and leaves English untouched.")
    ap.add_argument("--engine", default="gemini:gemini-2.5-flash")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap how many low-QA rows are cleared for retranslation")
    ap.add_argument("--context", default="5")
    ap.add_argument("--sleep", default="0.8")
    ap.add_argument("--min-quality", default="0.35")
    ap.add_argument("--skip-scan", action="store_true",
                    help="skip step 1 and heal against the QA scores already stored")
    args = ap.parse_args()

    py = sys.executable
    def s(name: str) -> str:
        return str(SCRIPTS / name)
    lang = (args.lang or "en").strip()

    print(f"[heal] doc={args.doc} lang={lang} below-qa={args.below_qa} "
          f"engine={args.engine}", flush=True)

    # ── Step 1: refresh QA scores (free, idempotent, safe to re-run) ──────────
    if not args.skip_scan:
        _run("1/3  qa_scan --write",
             [py, s("qa_scan.py"), "--db", args.db, "--doc", args.doc,
              "--lang", lang, "--write"])
    else:
        print("\n[heal] step 1 skipped (--skip-scan): using stored QA scores.",
              flush=True)

    # ── Step 2: archive + clear the low-QA rows (history-preserving) ──────────
    # retranslate.py archives each translation into translation_history before
    # clearing it, so nothing is destroyed. If nothing matches the threshold it
    # prints "Nothing matches" and exits 0 — the refill below is then a no-op.
    clear_argv = [py, s("retranslate.py"), "--db", args.db, "--doc", args.doc,
                  "--below-qa", str(args.below_qa), "--lang", lang, "--yes"]
    if args.limit:
        clear_argv += ["--limit", str(args.limit)]
    _run(f"2/3  retranslate --below-qa {args.below_qa} --yes", clear_argv)

    # ── Step 3: refill the cleared slots under the current prompt/engine ──────
    refill = [py, s("translate_passages.py"), "--db", args.db, "--doc", args.doc,
              "--engine", args.engine, "--context", args.context,
              "--sleep", args.sleep, "--min-quality", args.min_quality]
    if lang != "en":
        refill += ["--lang", lang]
    _run("3/3  translate_passages (refill)", refill)

    print(f"\n[heal] complete for {args.doc} ({lang}). "
          f"Re-open the QA panel (or run qa_scan) to see the new scores.",
          flush=True)


if __name__ == "__main__":
    main()
