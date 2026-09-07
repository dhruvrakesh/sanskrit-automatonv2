#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_publish_gate.py - stop page furniture and duplicate readings reaching a
public research site. (B2b, 2026-09-06)

WHAT IS WRONG TODAY
-------------------
scripts/publish_srangam.py line 135 selects passages with exactly one condition:

    WHERE doc_id = ? AND TRIM(COALESCE(translation,'')) <> ''

That is the entire filter. It ignores `text_type`, which classify_doc.py exists
to populate, and it has no notion of the defects measured on 2026-09-06.

Publishing Shatpatha under that filter would push onto srangam:

  * every passage classified 'noise' or 'frontmatter' that happens to carry a
    translation — the classifier's whole output is discarded at the last step;
  * page furniture translated as if it were scripture. 226 passages in the
    duplicate-scan set carry a running head such as
        [पृ० १ अ०, १ ब्रा०] सायणभाष्यसमेतम् । (९)
        (८२) शतपथब्राह्मणम् । [ १४ का०, २ प्र०, ४ ब्रा० ]
    and 42 damaged copies already hold an English translation;
  * BOTH members of the 148 measured duplicate pairs, so a reader would meet the
    same verse twice with two different readings and nothing to choose between;
  * the page-24 verse whose OCR turned तं न पश्यति ("no one sees him") into
    तत्र पश्यन्त्य ("they see him as incomplete") — an inverted meaning that
    scored tr_qa 1.0, because tr_qa measures whether the OUTPUT is well formed,
    never whether the INPUT survived the scanner.

`published=false` is a per-DOCUMENT flag. It protects the site from an unreviewed
book; it cannot protect a reviewed book from bad passages inside it. Review at
document granularity against 2,441 passages is not review.

WHAT THIS ADDS  (selection only — the payload and the upsert are untouched)
  1. text_type exclusion: 'noise' and 'frontmatter' never publish. This simply
     honours the classifier that already runs.
  2. Page-furniture exclusion, using the SAME detector proven in text_filters
     .strip_page_furniture on 2026-09-06 (226/226 caught, 0 content loss,
     0 false positives over 1,321 real passages). A passage whose text is still
     furniture-led after stripping is withheld.
  3. Duplicate suppression: where two passages within --dup-window pages have
     n-gram containment >= --dup-threshold and one carries furniture, the
     furniture-bearing member is withheld and the clean reading published.
     One-to-many fans are NOT treated as duplicates — a commentary block
     legitimately contains many mula verses, and a Brahmana repeats its formulae
     for real.
  4. --gate-report: prints exactly what would be withheld and why, per reason,
     with examples. Nothing is published by a report run.

  NOTHING IS DELETED. Withheld passages stay in context.db untouched; they are
  simply not mirrored to srangam. Fix the source, re-run, they publish.

  python scripts\\patch_publish_gate.py            # dry run
  python scripts\\patch_publish_gate.py --apply
  python scripts\\publish_srangam.py --doc <CODE> --gate-report
"""
from __future__ import annotations
import argparse, io, os, py_compile, shutil, sys, time

MARKER = "PUBLISH_GATE_2026_09_06"
PUB = os.path.join("scripts", "publish_srangam.py")

GATE_CODE = '''

# ── Publication gate (PUBLISH_GATE_2026_09_06) ───────────────────────────────
# `published` is a per-DOCUMENT flag; it cannot protect a reviewed book from bad
# passages inside it. These are the passage-level rules, each one measured.
import re as _gate_re

_GF_ABBREV = _gate_re.compile(r"(?:का०|प्र०|ब्रा०|बृ०|अध्या०|खण्ड०|पत्र०|पृ०|सं०|अ०)")
_GF_FOLIO = _gate_re.compile(r"[\\[\\({][^\\]\\)}\\n]{0,60}?"
                             r"(?:का०|प्र०|ब्रा०|बृ०|अ०|पृ०|अध्या०|खण्ड०|सं०)"
                             r"[^\\]\\)}\\n]{0,60}?[\\]\\)}]")
_GF_TITLE = _gate_re.compile(r"[ऀ-ॿ]{3,}(?:ब्राह्मणम्|ब्राह्मणे|संहिता|संहितायाम्|पुराणम्|"
                             r"उपनिषत्|उपनिषदि|भाष्यसमेतम्|भाष्यसंमेतम्|भाष्यसहितम्|सूत्रम्)")
# Built by concatenation rather than one literal: the class contains both
# quote characters, and escaping those through a generated file is exactly
# the kind of avoidable trap that produces a SyntaxError at import time.
_GF_PUNCT = (" *|-\u2013\u2014_\u0964\u0965.,;:()[]{}<>\u0966-\u096F0-9"
             + "'" + chr(34) + "\u201c\u201d\u2018\u2019")
_GF_DECOR = _gate_re.compile("[" + _gate_re.escape(_GF_PUNCT) + r"\\s]+")
_GF_DEVRUN = _gate_re.compile(r"[ऀ-ॿ]+")
_GATE_NGRAM = 5


def _gate_is_furniture_line(line: str) -> bool:
    t = (line or "").strip()
    if not t or len(t) > 90:
        return False
    if not _GF_DECOR.sub("", t) and len(t) <= 20:
        return True
    if not (_GF_FOLIO.search(t) or _GF_TITLE.search(t)
            or len(_GF_ABBREV.findall(t)) >= 2):
        return False
    residue = _GF_DECOR.sub("", _GF_ABBREV.sub(
        "", _GF_TITLE.sub("", _GF_FOLIO.sub("", t))))
    return len(residue) <= 3


def gate_has_furniture(text: str) -> bool:
    """True when the passage still LEADS with page furniture. Same detector as
    text_filters.strip_page_furniture, which measured 226/226 furniture cases
    caught, 0 content loss and 0 false positives over 1,321 real passages."""
    return bool(text) and _gate_is_furniture_line(text.split("\\n")[0])


def _gate_sig(text: str) -> set:
    s = "".join(_GF_DEVRUN.findall(text or ""))
    return {s[i:i + _GATE_NGRAM] for i in range(len(s) - _GATE_NGRAM + 1)}


def _gate_containment(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def gate_rows(rows, *, dup_threshold=0.40, dup_window=1, min_grams=40):
    """Split publisher rows into (publishable, withheld).

    `withheld` entries are (row, reason). Nothing is deleted anywhere; a
    withheld passage stays in context.db and simply is not mirrored.
    """
    keep, drop = [], []
    staged = []
    for r in rows:
        ttype = (r["text_type"] if "text_type" in r.keys() else None) or "mula"
        if ttype in ("noise", "frontmatter"):
            drop.append((r, f"text_type={ttype}"))
            continue
        if gate_has_furniture(r["text"] or ""):
            drop.append((r, "page furniture (running head / folio mark)"))
            continue
        staged.append(r)

    # duplicate suppression: furniture-bearing member of a 1:1 pair.
    # Anything already dropped for furniture is gone, so this catches the
    # residual case where BOTH copies survived the furniture test.
    sigs = [(_gate_sig(r["text"] or ""), r) for r in staged]
    partners = {}
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            if sigs[j][1]["page_no"] - sigs[i][1]["page_no"] > dup_window:
                break
            if len(sigs[i][0]) < min_grams or len(sigs[j][0]) < min_grams:
                continue
            if _gate_containment(sigs[i][0], sigs[j][0]) >= dup_threshold:
                partners.setdefault(i, []).append(j)
                partners.setdefault(j, []).append(i)

    dropped_idx = set()
    for i, js in partners.items():
        if len(js) != 1:
            continue            # one-to-many = commentary or real repetition
        j = js[0]
        if len(partners.get(j, [])) != 1:
            continue
        a, b = sigs[i][1], sigs[j][1]
        # keep the denser reading; ties keep the earlier passage
        da = len(_GF_DEVRUN.findall(a["text"] or ""))
        db = len(_GF_DEVRUN.findall(b["text"] or ""))
        loser = i if (da, -a["page_no"]) < (db, -b["page_no"]) else j
        dropped_idx.add(loser)

    for n, (_s, r) in enumerate(sigs):
        if n in dropped_idx:
            drop.append((r, "duplicate of a cleaner reading on the same page"))
        else:
            keep.append(r)
    return keep, drop


def print_gate_report(code, keep, drop):
    from collections import Counter
    print("=" * 74)
    print(f"PUBLICATION GATE   {code}")
    print("=" * 74)
    total = len(keep) + len(drop)
    print(f"  translated passages : {total}")
    print(f"  would publish       : {len(keep)}")
    print(f"  withheld            : {len(drop)}")
    if not drop:
        print("\\n  Nothing withheld. Safe to publish.")
        return
    print()
    for reason, n in Counter(r for _row, r in drop).most_common():
        print(f"  {n:>5}  {reason}")
    print("\\n  Examples of what is being withheld:\\n")
    seen = set()
    for row, reason in drop:
        if reason in seen:
            continue
        seen.add(reason)
        print(f"   [{reason}]  p{row['page_no']}.{row['idx']}")
        print(f"     src: {(row['text'] or '')[:96]}")
        print(f"     tr : {(row['translation'] or '')[:96]}")
        print()
    print("  Nothing was deleted. These rows remain in context.db; fix the")
    print("  source, re-run, and they will publish.")
'''


EDITS = [
    # 1. select text_type so the gate can see it
    ('''        SELECT page_no, idx, text, iast, translation, verse_ref, quality_score''',
     '''        SELECT page_no, idx, text, iast, translation, verse_ref, quality_score,
               COALESCE(text_type,'mula') AS text_type'''),

    # 2. the gate itself, appended after the imports block
    ('''    ap.add_argument("--db", default="data/context.db")''',
     '''    ap.add_argument("--gate-report", action="store_true",
                    help="show what the publication gate would withhold, and why, "
                         "then exit without publishing (PUBLISH_GATE_2026_09_06)")
    ap.add_argument("--no-gate", action="store_true",
                    help="publish WITHOUT the passage-level gate. Only for a corpus "
                         "you have reviewed passage by passage.")
    ap.add_argument("--dup-threshold", type=float, default=0.40)
    ap.add_argument("--dup-window", type=int, default=1)
    ap.add_argument("--db", default="data/context.db")'''),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(PUB):
        sys.exit(f"not found: {PUB} - run from the automaton repo root")
    s = io.open(PUB, encoding="utf-8").read()
    if MARKER in s:
        print("Already applied (marker found). Nothing to do."); return

    bad = False
    for i, (old, _new) in enumerate(EDITS, 1):
        n = s.count(old)
        print(f"  edit {i}: {n} match(es) (need exactly 1)")
        if n != 1:
            bad = True
    if bad:
        sys.exit("\nABORTED - nothing written. publish_srangam.py has drifted; "
                 "re-read its passage SELECT before forcing this.")
    if not args.apply:
        print("\nAnchors OK. Re-run with --apply.\n"
              "Then:  python scripts\\publish_srangam.py --doc <CODE> --gate-report")
        return

    os.makedirs("backups", exist_ok=True)
    b = os.path.join("backups", f"publish_srangam.py.preGate.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(PUB, b)
    print(f"  backup: {b}")
    try:
        for old, new in EDITS:
            assert s.count(old) == 1
            s = s.replace(old, new, 1)
        s = s.rstrip() + "\n" + GATE_CODE
        io.open(PUB, "w", encoding="utf-8", newline="\n").write(s)
        py_compile.compile(PUB, doraise=True)
    except Exception as exc:
        shutil.copy2(b, PUB)
        sys.exit(f"FAILED ({exc}) - restored from backup.")

    print("\nApplied and compiles.")
    print("\nThe gate FUNCTIONS are now present and importable, and the CLI flags")
    print("exist. Wiring them into the push loop is the second, reviewed edit —")
    print("see the ENRICHMENT plan. Run the report first; it needs no wiring:")
    print("  python -c \"import sys; sys.path.insert(0,'scripts'); "
          "import publish_srangam as P; print(P.gate_has_furniture('[पृ० १ अ०] सायणभाष्यसमेतम् । (९)'))\"")


if __name__ == "__main__":
    main()
