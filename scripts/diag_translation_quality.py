#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_translation_quality.py - does translation_qa mean anything?

FILE_VERSION = "2026-09-14.01"
MARK = "TRANSLATION_QUALITY_2026_09_14"

THE CASE THAT PROMPTED THIS
---------------------------
Two scans of one Dhanurveda text, both translated on 2026-09-14.

  page 5, clean scan, qa=0.6
    "The bowstring should be twisted, smooth, and capable of enduring
     all actions in battle. // In the absence of silk thread, a deer's
     sinew is recommended..."

  page 5, dirty scan, qa=1.0
    "ERS =F JEMENT Dhanavaidata Samhita / Shiva Dhanur Veda / In battle,
     the one who is skilled in the art of archery is praised."

The dirty scan holds qa=1.0 on fourteen of nineteen rows while carrying
"MAHARISHI UNIVERSITY OF MANAGEMENT", "New Vedic Literature Collection"
and "[Shiva Dhanur Ved]" into the English. The score rewards fluency and
does not look at whether the thing made fluent was the text or the
scanner's running head.

WHAT THIS MEASURES, AND WHAT IT DOES NOT
----------------------------------------
It does NOT re-score translations. It asks one falsifiable question:
does the share of rows carrying OCR furniture DIFFER between high-qa and
low-qa rows? If a row scoring 1.0 is as likely to carry furniture as one
scoring 0.2, the score is not seeing it. That is a cross-tabulation, and
it can come back saying the scorer is fine.

FOUR SIGNALS, each cheap and each separately reported so no single one
can carry a verdict on its own:

  caps_run     three or more consecutive ALL-CAPS words of 3+ letters.
               "MAHARISHI UNIVERSITY OF MANAGEMENT", "ERS =F JEMENT".
  iast_passthru a long row dense with IAST diacritics and almost no
               English function words. Catches transliteration passed
               straight through as if it were a translation - page 14
               of the dirty Dhanurveda scan, which scored 0.15 rather
               than 0.
  symbol_noise more than 8% of characters are neither letter, digit,
               space nor ordinary punctuation.
  title_echo   the row opens with a bracketed or repeated form of the
               document's own name - a running head, translated.

A row is FLAGGED if any of the four fires. The flag is a suspicion, not
a verdict, and --show prints the rows so a human can overrule it.

TUNED, NOT GUESSED. The first draft of these signals was run against the
Dhanurveda pair and got both directions wrong: a regex demanding three
consecutive words of three-plus capitals missed BOTH "ERS =F JEMENT" and
"MAHARISHI UNIVERSITY OF MANAGEMENT", because "=F" and "OF" break the
chain; counting DISTINCT function words rather than occurrences flagged
three of the clean scan's best rows, since a correct sentence can contain
only one distinct one; and a title key built from
dhanur_veda_shiva_dhanur_veda listed "dhanur" twice, so any row merely
mentioning Dhanurveda looked like a running head. After the fixes the
clean scan flags 0 of 17 rows and the dirty one 18 of 19.

  python scripts/diag_translation_quality.py
  python scripts/diag_translation_quality.py --doc shiva_dhanur_veda --show 10
"""

import argparse
import re
import sqlite3
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FILE_VERSION = "2026-09-14.01"
MARK = "TRANSLATION_QUALITY_2026_09_14"

# Tuned against the real Dhanurveda pair on 2026-09-14. The first draft
# over-fired on good English and under-fired on the exact garbage it was
# written for, so each signal below says what broke it.
FUNC = (" the ", " and ", " of ", " in ", " to ", " is ", " with ", " for ",
        " that ", " his ", " one ", " should ", " a ", " an ", " as ",
        " at ", " by ", " be ", " on ", " from ", " who ", " are ", " was ",
        " not ", " it ", " this ", " which ", " he ", " should ")
# The diacritics IAST uses and English does not. If a row is dense with
# these and has almost no English function words, it is not a translation -
# it is transliteration passed through. Page 14 of the dirty Dhanurveda
# scan is exactly that, and it scored 0.15 rather than 0.
IAST = set(u"\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e43\u1e25\u1e47"
           u"\u1e6d\u1e0d\u015b\u1e63\u00f1\u1e45\u1e41"
           u"\u0100\u012a\u016a\u1e5a\u1e36\u1e42\u1e24\u1e46"
           u"\u1e6c\u1e0c\u015a\u1e62\u00d1\u1e44\u1e40")
OKCH = set(" \t\n.,;:!?'\"()[]{}/-*_`")


def caps_run(t):
    """Three or more consecutive shouting tokens, at least one of them a
    real word. A regex demanding three words of 3+ capitals in a row missed
    both "ERS =F JEMENT" and "MAHARISHI UNIVERSITY OF MANAGEMENT", because
    "=F" and "OF" break the chain - which is how the first version of this
    scored zero on the two headers it was written to catch."""
    run = 0
    long_seen = False
    for w in t.split():
        core = "".join(ch for ch in w if ch.isalpha())
        if not core:
            continue
        if core.isupper():
            run += 1
            if len(core) >= 3:
                long_seen = True
            if run >= 3 and long_seen:
                return True
        else:
            run = 0
            long_seen = False
    return False


def signals(text, title_words):
    t = text or ""
    low = " " + " ".join(t.lower().split()) + " "
    out = set()
    if caps_run(t):
        out.add("caps_run")
    # Occurrences, not distinct entries. A correct 120-character sentence can
    # easily contain only one DISTINCT function word, and counting distinct
    # entries flagged three of the clean scan's best rows.
    words = len(t.split())
    if words >= 25:
        hits = sum(low.count(f) for f in FUNC)
        dens = 0.0
        if t:
            dens = 100.0 * sum(1 for ch in t if ch in IAST) / len(t)
        if hits < 3 and dens >= 1.0:
            out.add("iast_passthru")
    if t:
        bad = sum(1 for ch in t if not (ch.isalnum() or ch in OKCH))
        if 100.0 * bad / len(t) > 8.0:
            out.add("symbol_noise")
    head = " ".join(t[:90].lower().split())
    if title_words and sum(1 for w in title_words if w in head) >= 2:
        out.add("title_echo")
    return out


def title_key(code):
    """Deduplicated. dhanur_veda_shiva_dhanur_veda yields dhanur twice, and
    counting it twice made any row merely mentioning Dhanurveda look like a
    running head."""
    seen = []
    for p in re.split(r"[^a-z0-9]+", code.lower()):
        if len(p) >= 4 and p not in ("veda", "smriti", "purana") and p not in seen:
            seen.append(p)
    return seen[:4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--min-rows", type=int, default=8)
    a = ap.parse_args()

    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA query_only=ON")
    LIVE = ("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') "
            "AND TRIM(COALESCE(p.text,''))<>''")

    where = "WHERE %s AND TRIM(COALESCE(p.translation,''))<>''" % LIVE
    args = []
    if a.doc:
        where += " AND d.code=?"
        args.append(a.doc)

    rows = con.execute(
        "SELECT d.code, p.page_no, p.id, p.translation, p.translation_qa "
        "FROM passages p JOIN docs d ON d.id=p.doc_id %s "
        "ORDER BY d.code, p.page_no" % where, args).fetchall()
    con.close()

    if not rows:
        print("no translated rows matched")
        return 0

    BUCKETS = [(0.0, 0.3, "0.0-0.3"), (0.3, 0.6, "0.3-0.6"),
               (0.6, 0.8, "0.6-0.8"), (0.8, 0.95, "0.8-0.95"),
               (0.95, 1.01, "0.95-1.0")]
    tally = {}
    per_doc = {}
    flagged_rows = []
    tkeys = {}
    for code, page, pid, txt, qa in rows:
        if code not in tkeys:
            tkeys[code] = title_key(code)
        sig = signals(txt, tkeys[code])
        try:
            q = float(qa)
        except Exception:
            q = -1.0
        b = "no score"
        for lo, hi, name in BUCKETS:
            if lo <= q < hi:
                b = name
                break
        d = tally.setdefault(b, {"n": 0, "flag": 0, "caps_run": 0,
                                 "iast_passthru": 0, "symbol_noise": 0,
                                 "title_echo": 0})
        d["n"] += 1
        if sig:
            d["flag"] += 1
            for s in sig:
                d[s] += 1
            flagged_rows.append((code, page, pid, q, sorted(sig), txt))
        pd = per_doc.setdefault(code, {"n": 0, "flag": 0, "qsum": 0.0, "qn": 0})
        pd["n"] += 1
        if sig:
            pd["flag"] += 1
        if q >= 0:
            pd["qsum"] += q
            pd["qn"] += 1

    print("%s  %d translated row(s)" % (MARK, len(rows)))
    print("")
    print("  THE QUESTION: does a high qa score mean fewer rows carry OCR")
    print("  furniture? If the flagged share is flat across the buckets, the")
    print("  score is not seeing furniture at all.")
    print("")
    print("  %-10s %8s %8s %8s   %8s %10s %12s %10s"
          % ("qa bucket", "rows", "flagged", "share",
             "caps_run", "iast_passthru", "symbol_noise", "title_echo"))
    print("  " + "-" * 86)
    order = [n for _l, _h, n in BUCKETS] + ["no score"]
    for b in order:
        d = tally.get(b)
        if not d:
            continue
        print("  %-10s %8d %8d %7.1f%%   %8d %10d %12d %10d"
              % (b, d["n"], d["flag"], 100.0 * d["flag"] / d["n"],
                 d["caps_run"], d["iast_passthru"], d["symbol_noise"],
                 d["title_echo"]))
    print("")
    hi = tally.get("0.95-1.0")
    lo = None
    for b in ("0.0-0.3", "0.3-0.6"):
        if tally.get(b):
            lo = tally[b] if lo is None else {
                "n": lo["n"] + tally[b]["n"], "flag": lo["flag"] + tally[b]["flag"]}
    print("  VERDICT")
    if hi and lo and lo["n"] >= 20 and hi["n"] >= 20:
        hs = 100.0 * hi["flag"] / hi["n"]
        ls = 100.0 * lo["flag"] / lo["n"]
        print("    rows scoring 0.95-1.0 carry furniture %.1f%% of the time." % hs)
        print("    rows scoring below 0.6 carry it %.1f%% of the time." % ls)
        if hs >= ls * 0.8:
            print("    The score is NOT separating them. A translation can be fluent")
            print("    and still be a translation of the scanner's running head, and")
            print("    nothing downstream would know.")
        else:
            print("    The score does separate them, by a factor of %.1f." % (ls / max(hs, 0.01)))
    else:
        print("    not enough rows in both tails to compare - run without --doc")
        print("    for the corpus-wide answer.")
    print("")
    print("  the worst documents by flagged share (%d+ translated rows):" % a.min_rows)
    print("  %-44s %6s %8s %8s %7s" % ("document", "rows", "flagged", "share", "avg_qa"))
    worst = sorted(((c, v) for c, v in per_doc.items() if v["n"] >= a.min_rows),
                   key=lambda kv: -(100.0 * kv[1]["flag"] / kv[1]["n"]))
    for code, v in worst[:20]:
        avg = (v["qsum"] / v["qn"]) if v["qn"] else -1
        print("  %-44s %6d %8d %7.1f%% %7s"
              % (code[:44], v["n"], v["flag"], 100.0 * v["flag"] / v["n"],
                 ("%.2f" % avg) if avg >= 0 else "-"))

    if a.show:
        print("")
        print("  %d flagged row(s); showing the %d with the HIGHEST qa, because"
              % (len(flagged_rows), a.show))
        print("  those are the ones the score got most wrong:")
        for code, page, pid, q, sig, txt in sorted(
                flagged_rows, key=lambda r: -r[3])[:a.show]:
            print("")
            print("    %-36s page %-5s id %-7d qa=%-5s %s"
                  % (code[:36], page, pid, ("%.2f" % q) if q >= 0 else "-",
                     "+".join(sig)))
            print("      %s" % " ".join((txt or "").split())[:220])
    return 0


if __name__ == "__main__":
    sys.exit(main())