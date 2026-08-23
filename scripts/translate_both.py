#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_both.py — one-job convenience wrapper: translate a doc into English
AND Hindi in a single launch (2026-08-23).

Rationale
---------
English and Hindi are TWO separate passes by design (English lands in
passages.translation; Hindi in translations_l10n). Both translate the SAME
Sanskrit source DIRECTLY — Hindi is never a Sanskrit→English→Hindi pivot; the
verified English, when present and QA-passed, is offered only as an optional
meaning reference (see translate_passages.py --lang / --anchor-min-qa).

This wrapper simply runs the existing translate_passages.py twice, in order:
  1. Sanskrit → English   (fills passages.translation)
  2. Sanskrit → Hindi     (fills translations_l10n, lang='hi')

It changes NOTHING in the engine or the per-language logic — it only saves you
from launching the two passes by hand. Every argument is passed straight
through, so behaviour is identical to running the two commands yourself.

Order matters only for the optional English reference: doing English first
means the Hindi pass can consult the just-written English on hard verses. Pass
--hi-pure to run Hindi with no English influence at all (--anchor-min-qa 2.0).

Usage (from the automaton/ root):
  python scripts/translate_both.py --db data/context.db --doc nilamata_seg \
      --engine gemini:gemini-2.5-pro --context 5 --limit 100000
  python scripts/translate_both.py --db data/context.db --doc surya_siddhanta --hi-pure
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

_HERE = Path(__file__).resolve().parent
_TRANSLATE = str(_HERE / "translate_passages.py")


def _run_pass(lang: str, args, extra: list[str]) -> int:
    """Launch translate_passages.py for one language. Streams its output live so
    the dashboard job log captures each verse exactly as a normal run would.
    Returns the child's exit code."""
    cmd = [
        sys.executable, _TRANSLATE,
        "--db", args.db, "--doc", args.doc,
        "--sleep", str(args.sleep),
        "--context", str(args.context),
        "--min-quality", str(args.min_quality),
    ]
    if args.engine:
        cmd += ["--engine", args.engine]
    if args.limit is not None:
        cmd += ["--limit", str(args.limit)]
    if args.retranslate:
        cmd += ["--retranslate"]
    if lang != "en":
        cmd += ["--lang", lang]
    cmd += extra
    banner = f"Sanskrit -> {'English' if lang == 'en' else lang.upper()}"
    print(f"\n{'='*66}\n[translate_both] PASS: {banner}\n{'='*66}", flush=True)
    print("  " + " ".join(cmd), flush=True)
    # Inherit stdout/stderr so the parent job log shows the live per-verse output.
    proc = subprocess.run(cmd)
    print(f"[translate_both] {banner} finished with exit code {proc.returncode}",
          flush=True)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Translate a doc into English AND Hindi in one launch "
                    "(runs the existing per-language passes back to back).")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--engine", default=None,
                    help="e.g. gemini:gemini-2.5-pro. Used for BOTH passes.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--context", type=int, default=5)
    ap.add_argument("--sleep", type=float, default=0.8)
    ap.add_argument("--min-quality", type=float, default=0.35)
    ap.add_argument("--retranslate", action="store_true",
                    help="Passed through to both passes (re-do existing rows; "
                         "the old translation is archived first).")
    ap.add_argument("--hi-pure", action="store_true",
                    help="Run the Hindi pass with ZERO English influence "
                         "(--anchor-min-qa 2.0). Default: Hindi may consult the "
                         "QA-passed English as an optional meaning reference.")
    ap.add_argument("--skip-en", action="store_true",
                    help="Skip the English pass (Hindi only) — e.g. when English "
                         "already exists and you only need to backfill Hindi.")
    ap.add_argument("--skip-hi", action="store_true",
                    help="Skip the Hindi pass (English only).")
    args = ap.parse_args()

    rc_total = 0
    if not args.skip_en:
        rc = _run_pass("en", args, extra=[])
        rc_total = rc_total or rc
    else:
        print("[translate_both] --skip-en: skipping the English pass", flush=True)

    if not args.skip_hi:
        hi_extra: list[str] = []
        if args.hi_pure:
            # An unreachable anchor threshold => no English ever qualifies as a
            # reference => pure Sanskrit->Hindi.
            hi_extra += ["--anchor-min-qa", "2.0"]
        rc = _run_pass("hi", args, extra=hi_extra)
        rc_total = rc_total or rc
    else:
        print("[translate_both] --skip-hi: skipping the Hindi pass", flush=True)

    print(f"\n[translate_both] done for doc={args.doc!r} "
          f"(en={'skipped' if args.skip_en else 'run'}, "
          f"hi={'skipped' if args.skip_hi else ('pure' if args.hi_pure else 'run')})",
          flush=True)
    return rc_total


if __name__ == "__main__":
    sys.exit(main())
