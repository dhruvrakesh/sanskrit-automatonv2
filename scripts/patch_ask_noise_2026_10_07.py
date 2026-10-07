#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_ask_noise_2026_10_07.py  (2026-10-07)  ASK_NOISE_2026_10_07

Ask (/api/ask) retrieved passages without looking at passages.text_type. On
2026-10-07 46 running heads of markandeya_purana were tagged 'noise' (checked one by
one against the 12:15 backup: "<n> markandeya puranam ||" and "<n> astamo 'dhyayah ||";
31 of them carry translations such as "Markandeya Purana //" and all keep their
vectors). A question that names the Purana would retrieve those heads first.

  * keyword (FTS) and semantic retrieval skip text_type noise / frontmatter, as the
    export, the reader counts and the publication gate already do;
  * the semantic path over-fetches 64 more candidates before filtering, so a cluster
    of near-identical heads cannot crowd out the passages.
Nothing is deleted: the vectors stay (build_embeddings no longer adds new ones for
noise rows), and re-tagging a row 'mula' brings it back at once.

All-or-nothing, marker-idempotent, backup .bak_asknoise_<date>, py_compile.
  python scripts\\patch_ask_noise_2026_10_07.py --check
  python scripts\\patch_ask_noise_2026_10_07.py
Test: python -m unittest tests.test_ask_noise_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "ASK_NOISE_2026_10_07"

EDITS = [
    ("keyword retrieval",
     """               WHERE passages_fts MATCH ?
                 AND TRIM(COALESCE(p.translation,'')) <> ''
                 AND d.code NOT LIKE '%-RETIRED'
               ORDER BY bm25(passages_fts) LIMIT ?\"\"\",
""",
     """               WHERE passages_fts MATCH ?
                 AND TRIM(COALESCE(p.translation,'')) <> ''
                 AND d.code NOT LIKE '%-RETIRED'
                 AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
               ORDER BY bm25(passages_fts) LIMIT ?\"\"\",
""", 1),
    ("over-fetch",
     """    order = np.argsort(-sims)[: max(k * 3, k)]   # over-fetch, then filter retired
""",
     """    order = np.argsort(-sims)[: k * 3 + 64]   # over-fetch, then filter retired and noise (ASK_NOISE_2026_10_07)
""", 1),
    ("semantic retrieval",
     """            WHERE p.id IN ({ph}) AND d.code NOT LIKE '%-RETIRED'
              AND TRIM(COALESCE(p.translation,'')) <> ''\"\"\", top_ids)}
""",
     """            WHERE p.id IN ({ph}) AND d.code NOT LIKE '%-RETIRED'
              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
              AND TRIM(COALESCE(p.translation,'')) <> ''\"\"\", top_ids)}
""", 1),
]

TARGETS = [(Path("scripts/dashboard.py"), EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_asknoise")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_asknoise_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
