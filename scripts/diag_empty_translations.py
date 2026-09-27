#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_empty_translations.py - why valid Sanskrit comes back empty.
(TRANSLATION_FILTERS_2026_09_27)  READ-ONLY: PRAGMA query_only=ON.

Five sections, every number measured from context.db:

  1  budget      the cap, what is spent, and whether it is paused. A capped
                 run used to return silent empties for every verse.
  2  per doc     eligible verses (the gate translate_passages applies), how
                 many have English, how many are empty although a LATER verse
                 of the same doc is translated (so the run reached them), the
                 Hindi hard-fail token [asphuta] stored as a translation, and
                 the invented speaker "Vaisampayana said -" in Hindi where the
                 Sanskrit names no Vaisampayana.
  3  replay      every stored English and Hindi translation through the
                 filters as they are in scripts/text_filters.py NOW, and
                 through a frozen copy of the pre-2026-09-27 filters. Shows
                 what the patch would newly reject (it should be only the
                 [asphuta] token) - the safety proof for the patch.
  4  ledger      data/translate_outcomes.jsonl (written by the patched
                 translator): every empty or salvaged result with its cause
                 and the model's raw output.
  5  examples    the attempted-but-empty verses of --doc, for the probe.

  python scripts/diag_empty_translations.py --db data/context.db
  python scripts/diag_empty_translations.py --db data/context.db --doc AphorismsOfSandilya --examples 15

"attempted" is a heuristic and is labelled as one: the doc has a translated
verse on the same or a later page, so the ordered run went past this verse.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text_filters as tf                      # noqa: E402
from normalize_text import normalize_sanskrit  # noqa: E402

TOKEN_HI = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
VAIS = "\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928"
SPEAKER_RE = re.compile(r"^\s*" + VAIS + r"\s+\u0928\u0947\s+\u0915\u0939\u093e")
LIVE = ("COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter') "
        "AND TRIM(COALESCE(p.text,''))<>''")
PATCHED = hasattr(tf, "_refusal_cut")


# ---- frozen copy of the pre-patch filters (text_filters.py as of 2026-09-06) --
def legacy_salvage(out, lang="en"):
    if not out or not out.strip():
        return ""
    t = out.strip(); low = t.lower()
    cut = len(t); found = False
    for ph in tf.JUNK_PHRASES + tf._CAVEAT_EXTRA:
        i = low.find(ph)
        if 0 <= i < cut:
            cut = i; found = True
    if lang == "hi":
        for ph in tf.JUNK_PHRASES_HI + tf._CAVEAT_HI_EXTRA:
            i = t.find(ph)
            if 0 <= i < cut:
                cut = i; found = True
    if not found:
        return t
    head = t[:cut]
    ends = list(tf._SENT_END_RE.finditer(head))
    if not ends:
        return ""
    s = head[:ends[-1].end()].strip()
    return s + " [\u2026]" if len(s) >= 15 else ""


def legacy_echo_en(o):
    o = (o or "").strip()
    if not o:
        return False
    return bool(tf.DEV_DIGIT_RE.search(o)) or tf.frac_devanagari(o) > 0.5


def verdict(salv, echo, text):
    if salv == "":
        return "empty"
    if echo:
        return "echo"
    return "keep" if salv == text.strip() else "cut"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--examples", type=int, default=10)
    ap.add_argument("--min-quality", type=float, default=0.35)
    ap.add_argument("--min-dev", type=float, default=0.05)
    a = ap.parse_args()

    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA query_only=ON")
    print("diag_empty_translations  db=%s  text_filters=%s" % (
        a.db, "PATCHED (TRANSLATION_FILTERS_2026_09_27)" if PATCHED else "pre-patch"))

    # 1 ---------------------------------------------------------------- budget
    print("\n1  BUDGET")
    try:
        b = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id=1").fetchone()
        if b:
            print("   cap $%.2f   spent $%.4f   paused=%s   headroom $%.4f"
                  % (b[0], b[1], b[2], b[0] - b[1]))
            if b[2] or b[1] >= b[0]:
                print("   ** CAPPED: pre-patch, every call returns '' and the run carries on.")
        else:
            print("   no budget_state row")
    except sqlite3.OperationalError as e:
        print("   budget_state unreadable: %s" % e)

    # 2 --------------------------------------------------------------- per doc
    print("\n2  PER DOCUMENT  (live rows only: not noise/frontmatter, non-blank)")
    q = ("SELECT d.code, p.id, p.page_no, p.idx, p.text, COALESCE(p.quality_score,0), "
         "COALESCE(p.translation,''), COALESCE(l.translation,'') "
         "FROM passages p JOIN docs d ON d.id=p.doc_id "
         "LEFT JOIN translations_l10n l ON l.passage_id=p.id AND l.lang='hi' "
         "WHERE " + LIVE)
    params = []
    if a.doc:
        q += " AND d.code=?"; params.append(a.doc)
    rows = con.execute(q + " ORDER BY d.code, p.page_no, p.idx", params).fetchall()
    last_en_page = {}
    for code, _pid, page, _i, _t, _q, en, _hi in rows:
        if en.strip():
            last_en_page[code] = max(last_en_page.get(code, 0), page)
    stats = {}
    empties = []
    for code, pid, page, idx, text, qs, en, hi in rows:
        s = stats.setdefault(code, Counter())
        s["live"] += 1
        normed = normalize_sanskrit(text or "")
        elig = tf.should_translate(normed, min_dev=a.min_dev) and bool(tf.clean_for_mt(normed))
        gated = qs > 0 and qs < a.min_quality
        if elig and not gated:
            s["eligible"] += 1
            if en.strip():
                s["en"] += 1
            elif page <= last_en_page.get(code, 0):
                s["en_empty_attempted"] += 1
                empties.append((code, pid, page, idx, qs, tf.clean_for_mt(normed)))
        if hi.strip():
            s["hi"] += 1
            if hi.strip() == TOKEN_HI:
                s["hi_token_only"] += 1
            elif TOKEN_HI in hi:
                s["hi_token_inline"] += 1
            if not en.strip():
                s["hi_without_en"] += 1
            if SPEAKER_RE.search(hi) and VAIS not in (text or ""):
                s["hi_invented_speaker"] += 1
    cols = ["live", "eligible", "en", "en_empty_attempted", "hi", "hi_without_en",
            "hi_token_only", "hi_token_inline", "hi_invented_speaker"]
    hdr = ["live", "elig", "en", "EMPTY*", "hi", "hi-en", "tok", "tok+", "spkr"]
    print("   %-44s " % "doc" + " ".join("%6s" % h for h in hdr))
    tot = Counter()
    for code in sorted(stats):
        s = stats[code]; tot.update(s)
        if not (s["en_empty_attempted"] or s["hi_token_only"] or s["hi_invented_speaker"]
                or s["hi_without_en"] or a.doc):
            continue
        print("   %-44s " % code[:44] + " ".join("%6d" % s[c] for c in cols))
    print("   %-44s " % "TOTAL (all docs)" + " ".join("%6d" % tot[c] for c in cols))
    print("   EMPTY* = eligible, no English, and a verse on the same or a later page")
    print("            IS translated (heuristic: the run went past it).")
    print("   hi-en  = Hindi stored where English is empty (direct sa->hi is the")
    print("            current default; --require-anchor restores HINDI D1).")
    print("   tok    = Hindi row that is ONLY the hard-fail token [asphuta];")
    print("   tok+   = token inside a longer Hindi row;  spkr = 'Vaisampayana said -'")
    print("            in Hindi, source names no Vaisampayana (Hindi rule 7 example).")

    # 3 ---------------------------------------------------------------- replay
    print("\n3  REPLAY of every stored translation: pre-patch filters vs current file")
    trans = Counter()
    ex = {}
    rq = ("SELECT p.id, p.text, p.translation FROM passages p JOIN docs d ON d.id=p.doc_id "
          "WHERE TRIM(COALESCE(p.translation,''))<>''")
    hq = ("SELECT p.id, p.text, l.translation FROM translations_l10n l JOIN passages p "
          "ON p.id=l.passage_id JOIN docs d ON d.id=p.doc_id "
          "WHERE l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>''")
    if a.doc:
        rq += " AND d.code=?"; hq += " AND d.code=?"
    for lang, sql in (("en", rq), ("hi", hq)):
        for pid, src, out in con.execute(sql, params):
            ls = legacy_salvage(out, lang)
            le = lang == "en" and bool(ls) and legacy_echo_en(ls)
            ns = tf.salvage_translation(out, lang=lang)
            ne = bool(ns) and tf.is_source_echo(src or "", ns, lang) if lang == "en" else False
            old, new = verdict(ls, le, out), verdict(ns, ne, out)
            trans[(lang, old, new)] += 1
            if old != new and (lang, old, new) not in ex:
                ex[(lang, old, new)] = (pid, out[:110].replace("\n", " "))
    print("   %-4s %-7s -> %-7s %8s" % ("lang", "before", "after", "rows"))
    for (lang, old, new), n in sorted(trans.items()):
        flag = "" if old == new else ("   <- patch LOOSENS" if old in ("empty", "echo", "cut") and new == "keep"
                                      else "   <- patch TIGHTENS")
        print("   %-4s %-7s -> %-7s %8d%s" % (lang, old, new, n, flag))
    for k, (pid, t) in sorted(ex.items()):
        print("     e.g. %s %s->%s  id %s: %s" % (k[0], k[1], k[2], pid, t))
    if not PATCHED:
        print("   (text_filters is not patched yet, so 'after' equals 'before' by construction.)")
    print("   Stored rows are survivors of the old filter, so this cannot show what the")
    print("   old filter threw away - section 4 and the probe can.")

    # 4 ---------------------------------------------------------------- ledger
    print("\n4  OUTCOME LEDGER  data/translate_outcomes.jsonl")
    led = Path(a.db).resolve().parent / "translate_outcomes.jsonl"
    if not led.exists():
        print("   not present yet - the patched translator writes it.")
    else:
        recs = []
        for line in led.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if a.doc and r.get("doc") != a.doc:
                continue
            recs.append(r)
        c = Counter((r.get("doc", "?"), r.get("lang", "?"), r.get("cause", "?")) for r in recs)
        for (d, lg, cause), n in sorted(c.items()):
            print("   %-44s %-3s %-15s %6d" % (d[:44], lg, cause, n))
        for r in recs[-a.examples:]:
            print("   - %s p%s.%s q=%.2f %s" % (r.get("doc"), r.get("page"), r.get("idx"),
                                              float(r.get("quality") or 0), r.get("cause")))
            print("       src: %s" % (r.get("source") or "")[:120].replace("\n", " / "))
            print("       raw: %s" % (r.get("raw") or "[nothing returned]")[:160].replace("\n", " / "))

    # 5 -------------------------------------------------------------- examples
    print("\n5  ATTEMPTED-BUT-EMPTY EXAMPLES%s" % ((" - " + a.doc) if a.doc else ""))
    feats = Counter()
    for code, pid, page, idx, qs, cleaned in empties:
        if "\u0936\u0947\u0937" in cleaned:
            feats["contains sesa (remainder) -> 'the remainder of'"] += 1
        if re.search(r"[\(\[][^()\[\]]{0,90}[\u0966-\u096f][^()\[\]]{0,90}[\)\]]", cleaned):
            feats["bracketed Devanagari citation -> echo test"] += 1
        if len(cleaned) < 40:
            feats["shorter than 40 chars"] += 1
    for k, n in feats.most_common():
        print("   %6d  %s" % (n, k))
    for code, pid, page, idx, qs, cleaned in sorted(empties, key=lambda e: -e[4])[:a.examples]:
        print("   %-28s id %-7s p%s.%s q=%.2f  %s" % (code[:28], pid, page, idx, qs,
                                                  cleaned[:90].replace("\n", " / ")))
    print("\nread-only; nothing was written.")


if __name__ == "__main__":
    main()
