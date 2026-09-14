#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ling_probe.py  (2026-09-13)  LING_PROBE_2026_09_13

READ-ONLY. Opens no database for writing, makes no API call, installs nothing.

Why this exists
---------------
passages.sandhi and passages.morph are at 0 of 49,555. The reason is not that
the work is hard; it is that nothing has ever written them:

  * scripts/sandhi_split.py and scripts/morph_parse.py are stdin -> stdout
    one-shot probes. Neither takes --db. Neither contains an UPDATE.
  * Both default to SAFE mode, where "sandhi splitting" is re.split on
    whitespace and dandas, and a "lemma" is the token transliterated to SLP1.
    That is not analysis; it is tokenisation wearing analysis's clothes.
  * SAFE mode is keyed off SA_SAFE_MODE, which .env pins to 1 and which
    RUNBOOK 0 calls a house rule because it ALSO disables destructive bulk
    operations. One flag, two unrelated meanings. Turning it off to get real
    morphology would simultaneously unlock destructive ops, which is why
    nobody has turned it off.
  * requirements.txt records that sanskrit_parser was REMOVED because its
    werkzeug==2.1.2 pin conflicts with flask>=3.0.3. So the obvious analyser
    cannot live in the dashboard's environment at all.

This script does not fix any of that. It answers the one question that has to
be answered before a line of the real pass is written:

    what does the installed analyser ACTUALLY expose, and what does it
    ACTUALLY return for a verse from this corpus?

Everything downstream should be written against what this prints, not against
what an API is assumed to look like.

Usage
    python scripts\\ling_probe.py --surface
    python scripts\\ling_probe.py --sample --db data/context.db --doc nilamata_seg
    python scripts\\ling_probe.py --compare --db data/context.db --doc nilamata_seg -n 3
"""

import argparse
import importlib
import json
import os
import re
import sqlite3
import sys
import textwrap

MARK = "LING_PROBE_2026_09_13"
BAR = "=" * 78


def hr(t):
    print("\n" + BAR)
    print(t)
    print(BAR)


# ---------------------------------------------------------------------------
# 1. What is installed, and what does it expose?
# ---------------------------------------------------------------------------
CANDIDATES = [
    ("vidyut", "Ambuda's Rust toolkit, Python bindings. kosha/prakriya/lipi are "
               "production; chandas/cheda/sandhi are experimental."),
    ("indic_transliteration", "script conversion; already in requirements.txt"),
    ("sanskrit_parser", "DELIBERATELY absent from requirements - werkzeug pin "
                        "conflicts with flask>=3.0.3"),
    ("transformers", "only needed for the ByT5-Sanskrit tier, not for tier 1"),
    ("torch", "same"),
]


def surface():
    hr("1. WHAT IS IMPORTABLE IN *THIS* INTERPRETER")
    print("  interpreter : %s" % sys.executable)
    print("  version     : %s" % sys.version.split()[0])
    print()
    found = {}
    for name, why in CANDIDATES:
        try:
            m = importlib.import_module(name)
            v = getattr(m, "__version__", None) or getattr(m, "VERSION", None) or "?"
            print("  [YES] %-22s %s" % (name, v))
            found[name] = m
        except Exception as e:
            print("  [ NO] %-22s %s" % (name, type(e).__name__))
        print("        %s" % textwrap.fill(why, 68, subsequent_indent=" " * 8))

    if "vidyut" not in found:
        print("\n  vidyut is not importable here. Nothing below can run.")
        return found

    hr("2. THE vidyut SURFACE, AS INSTALLED (not as assumed)")
    v = found["vidyut"]
    print("  vidyut.__file__ : %s" % getattr(v, "__file__", "?"))
    print("  top-level names : %s" % ", ".join(
        sorted(n for n in dir(v) if not n.startswith("_"))))
    print()
    for sub in ("lipi", "kosha", "cheda", "sandhi", "chandas", "prakriya"):
        try:
            m = importlib.import_module("vidyut." + sub)
            names = sorted(n for n in dir(m) if not n.startswith("_"))
            print("  vidyut.%-9s IMPORTS  -> %s" % (sub, ", ".join(names[:14])))
            if len(names) > 14:
                print("  %s   ... and %d more" % (" " * 20, len(names) - 14))
            # one level deeper on the classes that matter
            for n in names:
                obj = getattr(m, n)
                if isinstance(obj, type):
                    meth = sorted(x for x in dir(obj) if not x.startswith("_"))
                    if meth:
                        print("  %s   %s.%s: %s" % (" " * 18, sub, n, ", ".join(meth[:10])))
        except Exception as e:
            print("  vidyut.%-9s NO       -> %s: %s" % (sub, type(e).__name__, str(e)[:60]))
    return found


# ---------------------------------------------------------------------------
# 2. A real verse out of the real corpus
# ---------------------------------------------------------------------------
def pick(db, doc, n):
    """Read-only. immutable=1 so a running dashboard is never disturbed."""
    uri = "file:%s?immutable=1" % db.replace("\\", "/")
    c = sqlite3.connect(uri, uri=True)
    where = ["TRIM(COALESCE(p.text,'')) <> ''",
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')"]
    params = []
    if doc:
        where.append("d.code = ?")
        params.append(doc)
    rows = c.execute(
        "SELECT p.id, d.code, COALESCE(p.verse_ref,''), p.text, COALESCE(p.iast,'') "
        "FROM passages p JOIN docs d ON d.id = p.doc_id "
        "WHERE " + " AND ".join(where) +
        " ORDER BY p.id LIMIT ?", params + [n]).fetchall()
    c.close()
    return rows


def safe_split(dev_text):
    """EXACTLY what scripts/sandhi_split.py does in SAFE mode today, copied so
    the comparison is against the real current behaviour and not a paraphrase
    of it."""
    text = dev_text.strip()
    parts = [p.strip() for p in re.split("[|\\u0964\\u0965]+", text) if p.strip()] or [text]
    return [[t for t in re.split(r"\s+", p) if t] for p in parts]


def sample(db, doc, n):
    hr("3. VERSES FROM THE CORPUS (read-only, immutable)")
    rows = pick(db, doc, n)
    if not rows:
        print("  no rows matched. Is --doc %r a real code?" % doc)
        return []
    for pid, code, ref, dev, iast in rows:
        print("\n  passage %s   %s %s   %d chars" % (pid, code, ref or "-", len(dev)))
        print("  dev  : %s" % dev[:150].replace("\n", " "))
        print("  iast : %s" % (iast[:150].replace("\n", " ") or "(none)"))
    return rows


def compare(db, doc, n):
    rows = sample(db, doc, n)
    if not rows:
        return
    hr("4. WHAT THE CURRENT 'SAFE' PATH PRODUCES vs WHAT vidyut PRODUCES")
    try:
        from vidyut import lipi  # noqa: F401
        have = True
    except Exception as e:
        have = False
        print("  vidyut not importable (%s) - showing the SAFE path only, which" % type(e).__name__)
        print("  is what the corpus would get today if anything called it.\n")

    for pid, code, ref, dev, iast in rows:
        print("\n  --- passage %s (%s %s) ---" % (pid, code, ref or "-"))
        sp = safe_split(dev)
        flat = [w for seg in sp for w in seg]
        print("  SAFE  : %d token(s) across %d segment(s)" % (len(flat), len(sp)))
        print("          %s" % " | ".join(flat[:12]))
        print("          ^ this is re.split on whitespace and dandas. No sandhi")
        print("            is resolved: a compound stays one token.")
        if not have:
            continue
        print("  VIDYUT: see section 2 for the surface actually installed.")
        print("          The adapter is written against that surface, not")
        print("          guessed here - this probe deliberately stops short of")
        print("          calling an API it has not confirmed exists.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", action="store_true", help="what is installed and what it exposes")
    ap.add_argument("--sample", action="store_true", help="show real verses")
    ap.add_argument("--compare", action="store_true", help="safe path vs analyser")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("-n", type=int, default=3)
    a = ap.parse_args()

    print("%s   %s" % (MARK, "read-only probe; writes nothing, costs nothing"))
    if not (a.surface or a.sample or a.compare):
        a.surface = True
    if a.surface:
        surface()
    if a.sample and not a.compare:
        sample(a.db, a.doc, a.n)
    if a.compare:
        compare(a.db, a.doc, a.n)

    hr("WHAT THIS DOES NOT DO")
    print("  It does not write to the database. It does not set SA_SAFE_MODE.")
    print("  It does not install anything. The corpus pass that fills")
    print("  passages.sandhi and passages.morph is written only after the")
    print("  surface above is known, so that it targets the real API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())