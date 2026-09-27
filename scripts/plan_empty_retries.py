#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_empty_retries.py - which verses to ask the model again, and what it costs.
(TRANSLATION_FILTERS2_2026_09_27)  READ-ONLY: PRAGMA query_only=ON.

A retry is only honest for verses a run already WENT PAST and left empty:
eligible (the gate translate_passages applies - should_translate, cleaned
text non-empty, quality not below --min-quality), live (not noise /
frontmatter), untranslated in that language, and on or before the last
page of the doc that IS translated in that language. Pages beyond that are
new work, not a retry, and are left out on purpose.

For each doc and language it prints the page window and the count, and
writes a JSON plan (--out) that block_AZ turns into dashboard jobs:
    POST /api/translate {"doc": ..., "lang": ..., "until_page": N}
translate_passages then picks exactly the empty eligible rows up to N.

"Went past" is judged on (page, idx), not page alone (v2, 2026-09-27): a
document imported as one long page - LalitaVistara, 525 empty verses on
page 1 - would otherwise count every untranslated verse of that page as a
retry. The dashboard job can only be windowed by page, so a job on the last
page also picks up that page's never-attempted verses; the plan says how
many (new_in_window) and marks a doc "mostly-new" when they outnumber the
retries. block_AZ queues mostly-new docs only with -IncludeNew.
Verses on page_no < 1 are counted apart: translate_passages starts at
--since-page 1, so no run has ever reached them.

Cost is estimated at --per-verse USD (default 0.00023: the mean of the 12
paid probe calls on 2026-09-27, gemini-2.5-flash, context window 5).

  python scripts/plan_empty_retries.py --db data/context.db --out plan.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text_filters as tf                      # noqa: E402
from normalize_text import normalize_sanskrit  # noqa: E402

LIVE = ("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') "
        "AND TRIM(COALESCE(p.text,''))<>''")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--out", default=None)
    ap.add_argument("--langs", default="en,hi")
    ap.add_argument("--min-quality", type=float, default=0.35)
    ap.add_argument("--min-dev", type=float, default=0.05)
    ap.add_argument("--per-verse", type=float, default=0.00023)
    ap.add_argument("--min-rows", type=int, default=1)
    a = ap.parse_args()
    langs = [x.strip() for x in a.langs.split(",") if x.strip()]

    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")
    rows = con.execute(
        "SELECT d.code, p.page_no, p.idx, p.text, COALESCE(p.quality_score,0), "
        "TRIM(COALESCE(p.translation,''))<>'', "
        "EXISTS(SELECT 1 FROM translations_l10n l WHERE l.passage_id=p.id AND l.lang='hi' "
        "       AND TRIM(COALESCE(l.translation,''))<>'') "
        "FROM passages p JOIN docs d ON d.id=p.doc_id "
        "WHERE " + LIVE + " AND d.code NOT LIKE '%-RETIRED' ORDER BY d.code, p.page_no, p.idx").fetchall()
    last = {}                       # (code, lang) -> (page, idx) of the last translated verse
    for code, page, idx, _t, _q, en, hi in rows:
        for lg, done in (("en", en), ("hi", hi)):
            if done and (page, idx) > last.get((code, lg), (-1, -1)):
                last[(code, lg)] = (page, idx)
    count, fresh, below1 = {}, {}, {}
    for code, page, idx, text, qs, en, hi in rows:
        normed = normalize_sanskrit(text or "")
        if not tf.should_translate(normed, min_dev=a.min_dev) or not tf.clean_for_mt(normed):
            continue
        if 0 < qs < a.min_quality:
            continue
        for lg, done in (("en", en), ("hi", hi)):
            if lg not in langs or done or (code, lg) not in last:
                continue
            lp, li = last[(code, lg)]
            if page < 1:
                below1[(code, lg)] = below1.get((code, lg), 0) + 1
            elif (page, idx) <= (lp, li):
                count[(code, lg)] = count.get((code, lg), 0) + 1
            elif page == lp:
                fresh[(code, lg)] = fresh.get((code, lg), 0) + 1
    removed = {}
    try:
        for code, n in con.execute(
                "SELECT d.code, COUNT(*) FROM translation_history h JOIN passages p ON p.id=h.passage_id "
                "JOIN docs d ON d.id=p.doc_id WHERE h.reason='bare-illegible-token-2026-09-27' "
                "GROUP BY d.code"):
            removed[code] = n
    except sqlite3.OperationalError:
        pass
    try:
        b = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
    except sqlite3.OperationalError:
        b = None

    plan = []
    print("plan_empty_retries v2  db=%s   (read-only)" % a.db)
    print("  %-44s %-3s %7s %6s %6s %8s %6s  %s" % ("doc", "lng", "to pg", "retry", "new*", "est $", "hi-rm", "kind"))
    tot_n = tot_c = 0
    for lg in langs:
        keys = set(k for k in count if k[1] == lg) | set(k for k in fresh if k[1] == lg)
        for key in sorted(keys, key=lambda k: -(count.get(k, 0))):
            code = key[0]
            n, nf = count.get(key, 0), fresh.get(key, 0)
            if n < a.min_rows:
                continue
            up = last[key][0]
            kind = "mostly-new" if nf > n else "retry"
            cost = (n + nf) * a.per_verse
            tot_n += n + nf; tot_c += cost
            plan.append({"doc": code, "lang": lg, "until_page": up, "verses": n,
                         "new_in_window": nf, "kind": kind, "est_usd": round(cost, 4)})
            print("  %-44s %-3s %7d %6d %6d %8.4f %6s  %s" % (code[:44], lg, up, n, nf, cost,
                  removed.get(code, "") if lg == "hi" else "", kind))
    print("  %-44s %-3s %7s %6s %6s %8.4f" % ("TOTAL (retry + new in window)", "", "", tot_n, "", tot_c))
    if below1:
        print("  never reachable (page_no < 1; translate_passages starts at page 1):")
        for (code, lg), n in sorted(below1.items(), key=lambda kv: -kv[1]):
            print("    %-44s %-3s %6d" % (code[:44], lg, n))
    if b:
        print("  budget: cap $%.2f  spent $%.4f  headroom $%.4f  paused=%s" % (b[0], b[1], b[0] - b[1], b[2]))
    print("  retry = empty verse at or before the last translated (page, idx); new* = never-")
    print("  attempted verses on that last page, which the page-windowed job also takes.")
    print("  hi-rm = Hindi rows removed as bare [asphuta] by remediate_hi_artifacts.")
    if a.out:
        Path(a.out).write_text(json.dumps({"version": 2, "plan": plan, "per_verse": a.per_verse,
                                           "headroom": (b[0] - b[1]) if b else None},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
        print("  plan written: %s" % a.out)


if __name__ == "__main__":
    main()
