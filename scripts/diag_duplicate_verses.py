#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_duplicate_verses.py - page furniture, real duplicates, and what is neither.
v2, 2026-09-06.

WHY v2 EXISTS: v1 OVER-FIRED, BADLY
------------------------------------
v1 reported 1,705 "candidate duplicate pairs" out of 2,059 signatures on
Shatpatha - 83%. That is not a finding, it is a broken gate, and acting on it
would have damaged the corpus. Classifying all 1,705 by cause against the real
CSV:

     726  fans out, no furniture      NOT duplicates - formulaic repetition
     306  commentary quoting mula     NOT duplicates - Sayana doing his job
     281  unexplained 1:1             needs eyes
     244  furniture, but fans out     furniture, ambiguous pairing
     148  REAL duplicate (1:1)        the actual defect

v1 got two things wrong:

1. It decided which copy was "damaged" by DEVANAGARI SHARE. But Sayana's
   bhasya quotes the mula lemma by lemma - ' वागेव ' प्रथमं ' ह ' - so it is
   full of quote marks, and legitimate commentary scored as noise. Devanagari
   share measures TYPOGRAPHIC DENSITY, not corruption.

2. It never checked FAN-OUT. One commentary passage legitimately contains many
   mula verses: id 113067 paired with 12 different verses, and 67% of all pairs
   involved a member with 2+ partners. A real duplicate is one-to-one. A
   one-to-many fan is a commentary block, and calling it duplication is the
   same mistake as calling a Brahmana's repeated formulae a phrase loop
   (RUNBOOK 3d).

WHAT ACTUALLY DISCRIMINATES: PAGE FURNITURE
-------------------------------------------
The genuine cases all carry the printed page's own furniture, which the OCR
swept into the text:

  [पृ० १ अ०, १ ब्रा०] सायणभाष्यसमेतम् । (९) (डाथा) अथात्मनेऽन्नाद्यमागायत ।
  (८२) शतपथब्राह्मणम् । [ १४ का०, २ प्र०, ४ ब्रा० ] सु होवाच याज्ञवल्क्यः ।

A running head, a folio reference, then the verse - which also appears
properly segmented a few passages later. That is deterministic and needs no
similarity measure at all, which is why PASS 1 below runs on its own.

And it points at the real upstream bug: these are classified text_type='mula',
so they are TRANSLATABLE. The corpus is paying to translate page headers, and
storing the result next to the correct reading. On Shatpatha, 226 of the
passages in the pair set carry furniture; 42 damaged copies already hold an
English translation.

  python scripts\\diag_duplicate_verses.py --doc 2015_405693_Shatpath-Brahmanam
  python scripts\\diag_duplicate_verses.py --doc <CODE> --csv out\\dupes.csv
  python scripts\\diag_duplicate_verses.py --doc <CODE> --sql out\\reclassify.sql

READ-ONLY. mode=ro plus a busy timeout, safe beside a running translation.
Run it on WINDOWS - SQLite over the Claude device bridge fails with
'disk I/O error' because the -shm lock file cannot be mapped.
"""
from __future__ import annotations
import argparse, collections, csv, os, re, sqlite3, sys

DEV_RUN  = re.compile(r"[ऀ-ॿ]+")
NGRAM    = 5

# The printed page's own furniture, swept in by OCR. Anchored on the folio
# reference and the running title; both are typographic, not textual.
FURNITURE = re.compile(
    r"\[\s*(?:पृ०|[०-९\d]+\s*का०)"          # [पृ० १ अ०…  /  [ १४ का०…
    r"|शतपथब्राह्मणम्"                        # running title
    r"|सायणा?भाष्यसमेतम्")                    # running subtitle
# Sayana quoting the mula lemma by lemma. Six or more marks in one passage is
# commentary, not a verse.
QUOTE = re.compile(r"['\"‘’“”]")


def sig(text: str) -> set:
    s = "".join(DEV_RUN.findall(text or ""))
    return {s[i:i + NGRAM] for i in range(len(s) - NGRAM + 1)}


def containment(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--threshold", type=float, default=0.40,
                    help="n-gram containment for the same verse (default 0.40)")
    ap.add_argument("--window", type=int, default=1, help="max pages apart")
    ap.add_argument("--min-grams", type=int, default=40)
    ap.add_argument("--max-partners", type=int, default=1,
                    help="a real duplicate is one-to-one. A member with more "
                         "partners than this is a commentary block (default 1)")
    ap.add_argument("--quote-marks", type=int, default=6,
                    help="passages with at least this many quote marks are "
                         "treated as lemma-quoting commentary (default 6)")
    ap.add_argument("--show", type=int, default=15)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--sql", default=None,
                    help="write (but never run) UPDATE statements that reclassify "
                         "furniture passages as frontmatter")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"not found: {args.db} - run from the repo root")

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    rows = con.execute(
        """SELECT p.id, p.page_no, p.idx, COALESCE(p.text,''),
                  COALESCE(p.quality_score,-1), COALESCE(p.text_type,'mula'),
                  CASE WHEN TRIM(COALESCE(p.translation,'')) <> '' THEN 1 ELSE 0 END
           FROM passages p JOIN docs d ON d.id = p.doc_id
           WHERE d.code = ? ORDER BY p.page_no, p.idx""", (args.doc,)).fetchall()
    if not rows:
        sys.exit(f"no passages for doc {args.doc!r}")

    hi = set()
    if "translations_l10n" in tables:
        lc = {r[1] for r in con.execute("PRAGMA table_info(translations_l10n)")}
        if "passage_id" in lc and "translation" in lc:
            hi = {r[0] for r in con.execute(
                "SELECT DISTINCT passage_id FROM translations_l10n "
                "WHERE TRIM(COALESCE(translation,'')) <> ''")}
    con.close()

    P = [{"id": i, "page": pg, "idx": ix, "text": t, "q": q, "type": tt,
          "tr": tr, "hi": 1 if i in hi else 0,
          "furn": bool(FURNITURE.search(t)),
          "quotes": len(QUOTE.findall(t))} for i, pg, ix, t, q, tt, tr in rows]

    # ── PASS 1: page furniture. No similarity needed. ────────────────────────
    furn = [p for p in P if p["furn"]]
    furn_mula = [p for p in furn if p["type"] not in ("noise", "frontmatter")]
    print("=" * 78)
    print(f"PASS 1  PAGE FURNITURE CLASSIFIED AS TEXT   {args.doc}")
    print("=" * 78)
    print(f"  passages in doc                        : {len(P)}")
    print(f"  carrying a running head / folio mark   : {len(furn)}")
    print(f"    ...of those, NOT marked noise/frontmatter (so translatable):")
    print(f"                                           {len(furn_mula)}")
    print(f"    ...already translated  en {sum(p['tr'] for p in furn_mula)}"
          f"   hi {sum(p['hi'] for p in furn_mula)}")
    print()
    print("  This is the upstream defect and it needs no similarity argument:")
    print("  the classifier let the printed page's own header into 'mula', so the")
    print("  translator is paying to translate page headers.")
    for p in furn_mula[:6]:
        print(f"    p{p['page']}.{p['idx']}  type={p['type']:<11} "
              f"{'tr' if p['tr'] else '--'} : {p['text'][:74]}")

    # ── PASS 2: pairs, then classified by cause ─────────────────────────────
    items = [p for p in P if len(sig(p["text"])) >= args.min_grams]
    for p in items:
        p["sig"] = sig(p["text"])
    raw = []
    for i in range(len(items)):
        a = items[i]
        for j in range(i + 1, len(items)):
            b = items[j]
            if b["page"] - a["page"] > args.window:
                break
            c = containment(a["sig"], b["sig"])
            if c >= args.threshold:
                # the copy carrying furniture is the damaged one; failing that,
                # the one with more quote marks is the commentary
                if a["furn"] != b["furn"]:
                    dmg, cln = (a, b) if a["furn"] else (b, a)
                else:
                    dmg, cln = (a, b) if a["quotes"] >= b["quotes"] else (b, a)
                raw.append({"cont": c, "jac": jaccard(a["sig"], b["sig"]),
                            "dmg": dmg, "cln": cln})

    fan = collections.Counter(r["dmg"]["id"] for r in raw)
    cls = collections.Counter()
    real = []
    for r in raw:
        d = r["dmg"]
        many = fan[d["id"]] > args.max_partners
        if d["furn"] and not many:
            cls["REAL duplicate (furniture, one-to-one)"] += 1; real.append(r)
        elif d["furn"]:
            cls["furniture, but fans out - ambiguous"] += 1
        elif d["quotes"] >= args.quote_marks:
            cls["commentary quoting mula - NOT a duplicate"] += 1
        elif many:
            cls["fans out - formulaic repetition, NOT a duplicate"] += 1
        else:
            cls["unexplained one-to-one - needs eyes"] += 1

    print("\n" + "=" * 78)
    print(f"PASS 2  SIMILAR PAIRS, BY CAUSE   (containment >= {args.threshold}, "
          f"window {args.window})")
    print("=" * 78)
    print(f"  similar pairs found : {len(raw)}")
    print(f"  max partners for one member : {max(fan.values()) if fan else 0}"
          f"   (a real duplicate is 1)")
    print()
    for k, v in cls.most_common():
        mark = "->" if k.startswith("REAL") else "  "
        print(f"  {mark} {v:>5}  {k}")
    print()
    print(f"  Only the first line is actionable. {len(raw) - len(real)} pairs are")
    print("  commentary or genuine repetition and must NOT be touched.")

    if real:
        real.sort(key=lambda r: r["cont"], reverse=True)
        print(f"\n  Top {min(args.show, len(real))} real duplicates:\n")
        for r in real[:args.show]:
            d, c = r["dmg"], r["cln"]
            print(f"  cont {r['cont']:.2f}   clean p{c['page']}.{c['idx']} "
                  f"q {c['q']:.2f} {'tr' if c['tr'] else '--'}   vs   "
                  f"FURNITURE p{d['page']}.{d['idx']} q {d['q']:.2f} "
                  f"{'tr' if d['tr'] else '--'}")
            print(f"      clean : {c['text'][:96].replace(chr(10), ' ')}")
            print(f"      furn  : {d['text'][:96].replace(chr(10), ' ')}")
            print()

    if args.csv:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["verdict", "containment", "jaccard", "partners",
                        "clean_id", "clean_page", "clean_idx", "clean_translated",
                        "dmg_id", "dmg_page", "dmg_idx", "dmg_furniture",
                        "dmg_quotes", "dmg_translated", "clean_text", "dmg_text"])
            for r in raw:
                d, c = r["dmg"], r["cln"]
                many = fan[d["id"]] > args.max_partners
                v = ("REAL" if d["furn"] and not many else
                     "furniture_fanout" if d["furn"] else
                     "commentary" if d["quotes"] >= args.quote_marks else
                     "fanout" if many else "unexplained")
                w.writerow([v, f"{r['cont']:.3f}", f"{r['jac']:.3f}", fan[d["id"]],
                            c["id"], c["page"], c["idx"], c["tr"],
                            d["id"], d["page"], d["idx"], int(d["furn"]),
                            d["quotes"], d["tr"], c["text"], d["text"]])
        print(f"  wrote {len(raw)} pair(s) -> {args.csv}")

    if args.sql and furn_mula:
        os.makedirs(os.path.dirname(args.sql) or ".", exist_ok=True)
        with open(args.sql, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("-- Generated by diag_duplicate_verses.py. NOT RUN.\n")
            fh.write("-- Reclassify page furniture out of the translatable set.\n")
            fh.write("-- text_type is SET, never DELETEd: the passage stays, it just\n")
            fh.write("-- stops being a translation target (RUNBOOK 3e).\n")
            fh.write("-- REVIEW EVERY LINE. Take a backup first:\n")
            fh.write("--   python scripts\\db_backup.py --db data\\context.db\n")
            fh.write("-- And do NOT run this while a translate job is writing.\n\n")
            fh.write("BEGIN;\n")
            for p in furn_mula:
                snippet = p["text"][:60].replace("\n", " ").replace("--", "-")
                fh.write(f"-- p{p['page']}.{p['idx']}  {snippet}\n")
                fh.write(f"UPDATE passages SET text_type='frontmatter' "
                         f"WHERE id={p['id']} AND text_type='{p['type']}';\n")
            fh.write("-- COMMIT;   <- uncomment deliberately\nROLLBACK;\n")
        print(f"  wrote {len(furn_mula)} UPDATE(s) -> {args.sql}  (ends in ROLLBACK)")

    print("\n  Nothing here was written to the database.")


if __name__ == "__main__":
    main()
