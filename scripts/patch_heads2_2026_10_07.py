#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_heads2_2026_10_07.py  (2026-10-07)  HEADS2_2026_10_07

classify_noise --running-heads found nothing in markandeya_purana. The running heads
there are printed as "<page number> markandeya puranam ||" - with a double danda -
and the first version refused every line carrying a danda (to protect refrains).
Seen in data/translate_outcomes.jsonl: 6.1, 36.1, 40.1, 46.1, 48.1, 54.1, 58.1, 60.1,
64.1, 92.1, 94.1, 96.1 (English) and 23 Hindi rows of the same kind.

Rule now:
  * a line with a danda can be a head only if it is the FIRST line of its page,
    carries a page number, and has at most 24 Devanagari letters;
  * a group qualifies when it repeats on >= --min-repeat pages and EITHER its
    numbers vary from page to page (page numbering: then it is a head even where
    some copies were translated) OR it has no danda and is untranslated more often
    than translated (the first rule, unchanged);
  * speaker lines (... uvaca) are never tagged; nor any line over --max-len.
  * --include-translated (running-heads mode only): also tag the translated copies
    of a qualifying head (their "translation" is the title of the book). Off by
    default. Reversible like every tag: UPDATE passages SET text_type='mula' ...

All-or-nothing, marker-idempotent, backup .bak_heads2_<date>, py_compile.
  python scripts\\patch_heads2_2026_10_07.py --check
  python scripts\\patch_heads2_2026_10_07.py
Test: python -m unittest tests.test_heads2_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "HEADS2_2026_10_07"

OLD_LOOP = r'''    by = {}
    for (code, page), rows in pages.items():
        for pid, text, done in {rows[0][0]: rows[0], rows[-1][0]: rows[-1]}.values():
            t = " ".join(text.split())
            k = head_key(t)
            if not k or len(t) > max_len or _UVACA in t or "\u0964" in t or "\u0965" in t:
                continue   # a danda marks verse (a refrain can close many pages); a head has none
            g = by.setdefault((code, k), {"pages": set(), "todo": [], "done": 0, "sample": t})
            g["pages"].add(page)
            if done:
                g["done"] += 1
            else:
                g["todo"].append((pid, code, text))
    hits, groups = [], []
    for (code, k), g in by.items():
        if len(g["pages"]) >= min_repeat and len(g["todo"]) > g["done"]:
            hits += g["todo"]
            groups.append((code, k, len(g["pages"]), len(g["todo"]), g["done"], g["sample"]))
'''

NEW_LOOP = r'''    by = {}
    for (code, page), rows in pages.items():
        edge = [(rows[0], True)] + ([(rows[-1], False)] if len(rows) > 1 else [])
        for (pid, text, done), first in edge:
            t = " ".join(text.split())
            k = head_key(t)
            if not k or len(t) > max_len or _UVACA in t:
                continue
            # HEADS2_2026_10_07: a danda marks verse (a refrain can close many pages), EXCEPT in a short first
            # line that carries a page number - "6 markandeya puranam ||" is how this edition prints its head.
            danda = "\u0964" in t or "\u0965" in t
            nums = "".join(re.findall(r"[0-9\u0966-\u096f]+", t))
            letters = len(re.findall(r"[\u0900-\u0963\u0971-\u097f]", t))
            if danda and not (first and nums and letters <= 24):
                continue
            g = by.setdefault((code, k), {"pages": set(), "todo": [], "done": [], "sample": t, "nums": set(),
                                          "danda": False})
            g["pages"].add(page)
            g["nums"].add(nums)
            g["danda"] = g["danda"] or danda
            (g["done"] if done else g["todo"]).append((pid, code, text))
    hits, groups = [], []
    for (code, k), g in by.items():
        numbered = len(g["nums"] - {""}) >= 2          # page numbers that change: a running head
        plain = not g["danda"] and len(g["todo"]) > len(g["done"])
        if len(g["pages"]) >= min_repeat and (numbered or plain):
            hits += g["todo"] + (g["done"] if include_translated else [])
            groups.append((code, k, len(g["pages"]), len(g["todo"]), len(g["done"]), g["sample"]))
'''

EDITS = [
    ("signature", "def running_heads(con, doc=None, min_repeat=3, max_len=60):\n",
     "def running_heads(con, doc=None, min_repeat=3, max_len=60, include_translated=False):   # HEADS2_2026_10_07\n", 1),
    ("rule", OLD_LOOP, NEW_LOOP, 1),
    ("option",
     '''    ap.add_argument("--max-len", type=int, default=60, help="with --running-heads: characters (default 60)")
''',
     '''    ap.add_argument("--max-len", type=int, default=60, help="with --running-heads: characters (default 60)")
    ap.add_argument("--include-translated", action="store_true",
                    help="with --running-heads: also tag translated copies of a running head (HEADS2_2026_10_07)")
''', 1),
    ("option passed",
     '''        hits, groups = running_heads(con, args.doc, args.min_repeat, args.max_len)
''',
     '''        hits, groups = running_heads(con, args.doc, args.min_repeat, args.max_len, args.include_translated)
''', 1),
    ("header text",
     '''f"no danda, <= {args.max_len} chars, repeated on >= {args.min_repeat} pages, untranslated:")''',
     '''f"<= {args.max_len} chars, repeated on >= {args.min_repeat} pages, numbered or untranslated "
              f"(a danda only in a short numbered first line){' - translated copies too' if args.include_translated else ''}:")''', 1),
]

TARGETS = [(Path("scripts/classify_noise.py"), EDITS)]


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
        t = p.with_name(p.name + ".tmp_heads2")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_heads2_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
