#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_align.py  (2026-11-17)  VAMSA_ALIGN_2026_11_17   (G6c: one dynasty, generation by generation, across the works)

Asked on 15 Nov: "authoritative genealogies of these kings ... and then use our own corelations to add to and/or comment
on the inferences". vamsa_read.py (G5a, G6a, G6b) reads each work's genealogical chapters into kinship statements, checks
each against its verse, and draws each work's father-to-son lines (vamsa_read.persons: a person is a name and the father
the text gives; homonyms apart; a mother is not a father). This sets the same dynasty side by side in every work that has
it, generation by generation. Free (no call) and read-only of the readings:

  - one person by two names in one work: a verified "other" statement whose Sanskrit words say he was called so
    ("Vikukshi other Sasada: sasadasamjnam avapa") makes the second name the first in that chapter and the chapters
    beside it, so a son given to Sasada is Vikukshi's (aliases(); within a work only: across the works is G6d);
  - a dynasty is named by its founder and his father (ANCHORS: Ikshvaku son of Manu, Yadu son of Yayati, Kuru son of
    Samvarana, Brhadratha son of Vasu, ...); in each work the person of that name (and father), or the root of that
    name, is taken and his line walked down: of his sons, and theirs, the line with the most names the other works'
    lines also have, then the longest;
  - the lines are aligned together (a progressive dynamic alignment, the longest first: two names are one when their
    letters agree at SAME or more, the diacritics, the visarga and the nasals set aside, and a name of four letters or
    fewer only when equal: Duhsanta and Dusyanta, Samtanu and Santanu are one, Anu and Manu are two);
  - each generation says how the works stand: "agree" (every work that has it gives one name), "most" (more than half
    give one name), "differ", "one" (a single work has it); and each two works how often they agree.

Only verified statements make a line (vamsa_read's checks). What it shows is where the texts agree and where they part:
a correlation of the texts, not a ruling between them, and no person is joined to another across the works here (that
is G6d, the person register).

Writes exports\\vamsa_align.md (each dynasty: the works, the agreement, the generations where they part),
exports\\vamsa_align_<dynasty>.csv (a row a generation, two columns a work: the name and its verse) and
data\\vamsa_read\\aligned.json. Nothing is called, nothing else written.

  python scripts\\vamsa_align.py                                   every dynasty: the summary and the files
  python scripts\\vamsa_align.py --anchor Yadu                     one dynasty, printed generation by generation
  python scripts\\vamsa_align.py --anchor Bharata --father Dusyanta  any founder (and his father), printed
  python scripts\\vamsa_align.py --list                            the dynasties and their works (writes nothing)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

MARK = "VAMSA_ALIGN_2026_11_17"
ROOT = Path(__file__).resolve().parents[1]
SAME = 0.82          # two names are one at this ratio of their letters, or more
SHORT = 4            # a name of this many letters or fewer is one with another only when equal
MIN_LINE = 3         # a work's line of fewer persons is left out
# The words that say a person was called by another name (folded: no diacritics): samjna, nama, ahuh, smrta, khyata,
# ucyate, visruta, prathita.
ALIAS_MARKS = ("samjn", "nama", "namn", "ahu", "smrt", "khyat", "ucyat", "visrut", "prathit")
# VAMSA_NAMES_2026_11_18: words that say the second name is another person or a place, not a second name (a minister,
# a daughter's marriage, a wife, a mother, a sister, a friend, a priest, a land, a city)
NOT_ALIAS = ("amaty", "mantri", "duhit", "sambandh", "bharya", "patni", "matr", "bhagin", "sakh", "purohit",
             "jangal", "desa", "nagar")
# The founders of the dynasties the genealogical chapters tell, and their fathers (the solar and the lunar lines).
ANCHORS = [
    ("solar", "Ik\u1e63v\u0101ku", "Manu", "the solar line (Aik\u1e63v\u0101kas) from Ik\u1e63v\u0101ku"),
    ("videha", "Nimi", "Ik\u1e63v\u0101ku", "the Videhas (Janakas) from Nimi"),
    ("lunar", "Pur\u016bravas", "Budha", "the lunar line from Pur\u016bravas"),
    ("yadu", "Yadu", "Yay\u0101ti", "the Y\u0101davas from Yadu"),
    ("haihaya", "Sahasrajit", "Yadu", "the Haihayas from Sahasrajit"),
    ("kroshtu", "Kro\u1e63\u1e6du", "Yadu", "the V\u1e5b\u1e63\u1e47is and Andhakas from Kro\u1e63\u1e6du"),
    ("turvasu", "Turvasu", "Yay\u0101ti", "the line of Turvasu"),
    ("druhyu", "Druhyu", "Yay\u0101ti", "the line of Druhyu"),
    ("anu", "Anu", "Yay\u0101ti", "the \u0100navas from Anu"),
    ("puru", "P\u016bru", "Yay\u0101ti", "the Pauravas from P\u016bru"),
    ("kuru", "Kuru", "Sa\u1e43vara\u1e47a", "the Kurus from Kuru"),
    ("magadha", "B\u1e5bhadratha", "Vasu", "the B\u0101rhadrathas of Magadha from B\u1e5bhadratha son of Vasu"),
]


def nkey(name: str) -> str:
    """A name as names are compared across works: lower case, the visarga dropped, every nasal an n, the diacritics
    off, the letters only (Duhsanta: dusanta; Samtanu, Santanu: santanu)."""
    s = unicodedata.normalize("NFC", str(name or "")).lower()
    s = s.replace("\u1e25", "")                                   # the visarga
    for ch in ("\u1e43", "\u1e45", "\u00f1", "\u1e47", "m\u0310"):    # the anusvara, the nasals
        s = s.replace(ch, "n")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s if c.isalpha())


def ratio(ka: str, kb: str) -> float:
    if not ka or not kb:
        return 0.0
    if ka == kb:
        return 1.0
    if min(len(ka), len(kb)) <= SHORT:
        return 0.0
    return difflib.SequenceMatcher(None, ka, kb, autojunk=False).ratio()


def sim(a: str, b: str) -> float:
    """How alike two names are, 0 to 1 (their keys' letters; a short name only when equal)."""
    return ratio(nkey(a), nkey(b))


def same(a: str, b: str) -> bool:
    return sim(a, b) >= SAME


def father_is(given: str, actual: str) -> bool:
    """The father a founder is given (Manu) is the father a work names (Manu Vaivasvata, Vasu Caidyoparicara)."""
    g, a = nkey(given), nkey(actual)
    return bool(g) and bool(a) and (ratio(g, a) >= SAME or a.startswith(g) or (len(g) > SHORT and g in a)
                                    or any(ratio(g, nkey(x)) >= SAME for x in str(actual or "").split()))


def chnum(x):
    m = re.match(r"\d+", str(x if x is not None else ""))
    return int(m.group()) if m else None


# --------------------------------------------------------------------------------------------- a work's lines
def statements_of(out_dir, work: str) -> list:
    import vamsa_read as VR
    return [dict(s, chapter=r.get("chapter")) for r in VR.records(out_dir, work) for s in (r.get("statements") or [])]


def aliases_said(statements: list) -> list:
    """[(chapter, keep, other, ref, words)]: one person by two names, from the verified "other" statements whose words
    say he was called so; the name kept is the one that is a son (has a father) in these statements, else the first.
    VAMSA_NAMES_2026_11_18: the second name must stand in the words; never a woman of these statements (a wife, a
    daughter, a sister, a mother) nor words that make him another person or a place (NOT_ALIAS)."""
    import vamsa_read as VR
    sons = {VR.letters(s.get("a")) for s in statements if s.get("rel") == "son_of" and s.get("check") == "verified"}
    said = [s for s in statements if s.get("check") in ("verified", "words")]
    female = {VR.letters(s.get("a")) for s in said if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}
    female |= {VR.letters(s.get("b")) for s in said if s.get("rel") == "born_of"}
    out = []
    for s in statements:
        if s.get("rel") != "other" or s.get("check") != "verified":
            continue
        w = VR.folded(s.get("words"))
        if any(m in w for m in NOT_ALIAS):
            continue
        a, b = str(s.get("a") or ""), str(s.get("b") or "")
        if not VR.letters(a) or not VR.letters(b) or same(a, b):
            continue
        keep, other = (b, a) if VR.letters(b) in sons and VR.letters(a) not in sons else (a, b)
        ko, kw = nkey(other), nkey(s.get("words"))
        if not ko or ko[:5] not in kw or VR.letters(other) in female or VR.letters(keep) in female:
            continue
        rest = kw.replace(ko[:5], " ", 1)   # the word that says "called" stands apart from the name (not Samjna's own)
        if not any(m in rest for m in ALIAS_MARKS):
            continue
        out.append((chnum(s.get("chapter")), keep, other, s.get("ref"), s.get("words")))
    return out


def aliases(statements: list) -> list:
    """[(chapter, name, as)]: aliases_said() as renamed() takes them."""
    return [(ch, other, keep) for ch, keep, other, _r, _w in aliases_said(statements)]


def renamed(statements: list) -> list:
    """The statements with each second name made the first (aliases()), in its chapter and the chapters beside it;
    the name the verse gives is kept in a_said / b_said."""
    import vamsa_read as VR
    al = aliases(statements)
    if not al:
        return statements
    out = []
    for s in statements:
        x = dict(s)
        if x.get("rel") != "other":
            c = chnum(x.get("chapter"))
            for k in ("a", "b"):
                for ch, other, keep in al:
                    if VR.letters(x.get(k)) == VR.letters(other) and c is not None and ch is not None \
                            and abs(c - ch) <= 1:
                        x[k + "_said"], x[k] = x[k], keep
                        break
        out.append(x)
    return out


def tree(statements: list) -> tuple:
    """(persons, children): vamsa_read's persons (after renamed()), and each person's sons (a root, a father who is no
    son here, is "root:" and his name)."""
    import vamsa_read as VR
    ps = VR.persons(renamed(statements))
    kids = {}
    for k, p in ps.items():
        kids.setdefault(p["up"] or "root:" + VR.letters(p["father"]), []).append(k)
    return ps, kids


def line_from(anchor: str, ps: dict, kids: dict, prefer=(), father: str = "") -> list:
    """The line of sons below the person named anchor (whose father is father, when given) or below the root of that
    name: [(name, ref, words)], the anchor first. Of his sons, and theirs, the line taken is the one with the most
    names that prefer (the other works' lines) also has, then the longest. [] when the work has no such person."""
    pk = {nkey(x) for x in prefer if nkey(x)}
    hit = {}

    def named(k):
        if k not in hit:
            n = nkey(k[5:] if k.startswith("root:") else ps[k]["name"])
            hit[k] = 1 if n and (n in pk or any(ratio(n, x) >= SAME for x in pk)) else 0
        return hit[k]
    memo = {}

    def down(k):
        if k not in memo:
            memo[k] = (0, [k])    # a guard: no person is his own ancestor (vamsa_read.persons sees to it too)
            best = (0, [])
            for c in kids.get(k, ()):
                got = down(c)
                if (got[0], len(got[1]), c) > (best[0], len(best[1]), best[1][0] if best[1] else ""):
                    best = got
            memo[k] = (best[0] + named(k), [k] + best[1])
        return memo[k]
    ak = nkey(anchor)
    starts = [k for k, p in ps.items() if nkey(p["name"]) == ak and (not father or father_is(father, p["father"]))]
    starts += [r for r in kids if r.startswith("root:") and nkey(r[5:]) == ak]
    if not starts:
        return []
    best = max((down(k) for k in starts), key=lambda g: (g[0], len(g[1]), g[1][0]))[1]
    out = []
    for k in best:
        if k.startswith("root:"):
            out.append((anchor, None, None))
        else:
            p = ps[k]
            out.append((p["name"], p["ref"], p["words"]))
    return out


# --------------------------------------------------------------------------------------------- the alignment
def align(a: list, b: list, eq=None) -> list:
    """Needleman-Wunsch over two lines: [(i or None, j or None)], in order. eq(a[i], b[j]) (default: same names) scores
    2, else -1; a gap -1."""
    eq = eq or same
    n, m = len(a), len(b)
    hit = [[eq(a[i], b[j]) for j in range(m)] for i in range(n)]
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = -i
    for j in range(1, m + 1):
        score[0][j] = -j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = 2 if hit[i - 1][j - 1] else -1
            score[i][j] = max(score[i - 1][j - 1] + s, score[i - 1][j] - 1, score[i][j - 1] - 1)
    out, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and score[i][j] == score[i - 1][j - 1] + (2 if hit[i - 1][j - 1] else -1):
            out.append((i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and score[i][j] == score[i - 1][j] - 1:
            out.append((i - 1, None)); i -= 1
        else:
            out.append((None, j - 1)); j -= 1
    return out[::-1]


def status_of(names: list) -> tuple:
    """(status, the name most give, how many give it)."""
    groups = []
    for x in names:
        for g in groups:
            if same(g[0], x):
                g.append(x)
                break
        else:
            groups.append([x])
    top = max(groups, key=len)
    n = len(names)
    st = "one" if n == 1 else "agree" if len(top) == n else "most" if 2 * len(top) > n else "differ"
    return st, top[0], len(top)


def table(lines: dict) -> dict:
    """{"order": works, "rows": [{"gen", "cells": {work: (name, ref, words)}, "status", "name", "n"}],
    "pairs": {"w1 & w2": [agree, shared]}}: the lines aligned together, the longest first; a generation one work has
    and the others not is a row of its own."""
    if not lines:
        return {"order": [], "rows": [], "pairs": {}}
    order = sorted(lines, key=lambda w: (-len(lines[w]), w))
    cols = [{order[0]: e} for e in lines[order[0]]]
    for w in order[1:]:
        ln = lines[w]
        new = []
        for i, j in align(cols, [e[0] for e in ln], lambda col, nm: any(same(c[0], nm) for c in col.values())):
            if i is not None:
                if j is not None:
                    cols[i][w] = ln[j]
                new.append(cols[i])
            else:
                new.append({w: ln[j]})
        cols = new
    rows = []
    for g, c in enumerate(cols):
        st, nm, n = status_of([x[0] for x in c.values()])
        rows.append({"gen": g, "cells": c, "status": st, "name": nm, "n": n})
    pairs = {}
    for x in range(len(order)):
        for y in range(x + 1, len(order)):
            u, v = order[x], order[y]
            both = [r for r in rows if u in r["cells"] and v in r["cells"]]
            pairs["%s & %s" % (u, v)] = [sum(1 for r in both if same(r["cells"][u][0], r["cells"][v][0])), len(both)]
    return {"order": order, "rows": rows, "pairs": pairs}


def works_here(out_dir) -> list:
    import vamsa_read as VR
    order = list(VR.WORKS) + [w for w in VR.G6_WORKS if w not in VR.WORKS]
    have = {p.name for p in Path(out_dir).iterdir() if p.is_dir()} if Path(out_dir).exists() else set()
    return [w for w in order if w in have]


def dynasties(out_dir, anchors=None, works=None) -> list:
    """[{"slug", "anchor", "father", "title", "lines": {work: line}, "order", "rows", "pairs", "counts"}] for each
    dynasty two works or more have (a line of MIN_LINE persons or more)."""
    trees = {}
    for w in (works or works_here(out_dir)):
        st = statements_of(out_dir, w)
        if st:
            trees[w] = tree(st)
    out = []
    for slug, anchor, father, title in (anchors or ANCHORS):
        first = {w: line_from(anchor, ps, kids, (), father) for w, (ps, kids) in trees.items()}
        lines = {}
        for w, (ps, kids) in trees.items():   # again, each work leaning to the names the others have
            prefer = [n for v, ln in first.items() if v != w for n, _r, _w in ln[1:]]
            ln = line_from(anchor, ps, kids, prefer, father)
            if len(ln) >= MIN_LINE:
                lines[w] = ln
        if len(lines) < 2:
            continue
        t = table(lines)
        c = {"agree": 0, "most": 0, "differ": 0, "one": 0}
        for r in t["rows"]:
            c[r["status"]] += 1
        shared = c["agree"] + c["most"] + c["differ"]
        c["share_agree"] = round(c["agree"] / shared, 3) if shared else None
        out.append({"slug": slug, "anchor": anchor, "father": father, "title": title, "lines": lines,
                    "order": t["order"], "rows": t["rows"], "pairs": t["pairs"], "counts": c})
    return out


# --------------------------------------------------------------------------------------------- the files
def title_of(work: str) -> str:
    import vamsa_read as VR
    try:
        return VR.work_of(work)["title"]
    except Exception:
        return work


def write(dyn: list, out_dir, exports) -> list:
    ex = Path(exports)
    ex.mkdir(parents=True, exist_ok=True)
    written = []
    for d in dyn:
        works = d["order"]
        p = ex / ("vamsa_align_%s.csv" % d["slug"])
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["generation", "status", "name most give", "works giving it", "works having it"]
                        + [x for w in works for x in (w, w + " verse")])
            for r in d["rows"]:
                cells = []
                for w in works:
                    c = r["cells"].get(w)
                    cells += [c[0], c[1] or ""] if c else ["", ""]
                wr.writerow([r["gen"], r["status"], r["name"], r["n"], len(r["cells"])] + cells)
        written.append(p)
    md = ["# The dynasties across the works (%s)" % MARK, "",
          "Made %s by scripts\\vamsa_align.py from the verified statements of data\\vamsa_read. A generation \"agrees\""
          " when every work that has it gives one name, \"most\" when more than half do, \"differs\" otherwise, \"one\""
          " when a single work has it. Names are one when their letters agree (diacritics, visarga and nasals set"
          " aside). A correlation of the texts, not a ruling between them; no person is joined across the works"
          " here (G6d)." % datetime.date.today().isoformat(), ""]
    md += ["| Dynasty | Works (persons in the line) | Generations | Agree | Most | Differ | One work |",
           "|---|---|---|---|---|---|---|"]
    for d in dyn:
        c = d["counts"]
        md.append("| %s | %s | %d | %d | %d | %d | %d |" % (
            d["title"], ", ".join("%s (%d)" % (w, len(d["lines"][w])) for w in d["order"]), len(d["rows"]),
            c["agree"], c["most"], c["differ"], c["one"]))
    for d in dyn:
        md += ["", "## %s" % d["title"], "",
               "Works: %s." % "; ".join("%s, %s" % (w, title_of(w)) for w in d["order"]), "",
               "Two works side by side (the generations both have, how many give one name): %s." % "; ".join(
                   "%s %d of %d" % (k, a, n) for k, (a, n) in d["pairs"].items() if n), "",
               "The line as most give it (a ? where the works part): %s." % " > ".join(
                   r["name"] + ("" if r["status"] in ("agree", "one") else "?") for r in d["rows"]), "",
               "Where they part:", ""]
        parts = [r for r in d["rows"] if r["status"] in ("most", "differ")]
        if not parts:
            md.append("- nowhere: every generation two works share gives one name")
        for r in parts:
            md.append("- generation %d (%s): %s" % (r["gen"], r["status"], "; ".join(
                "%s %s (%s)" % (w, c[0], c[1] or "a root") for w, c in r["cells"].items())))
    p = ex / "vamsa_align.md"
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
    written.append(p)
    j = Path(out_dir) / "aligned.json"
    data = []
    for d in dyn:
        data.append({"slug": d["slug"], "anchor": d["anchor"], "father": d["father"], "title": d["title"],
                     "order": d["order"], "counts": d["counts"], "pairs": d["pairs"],
                     "rows": [{"gen": r["gen"], "status": r["status"], "name": r["name"], "n": r["n"],
                               "cells": {w: {"name": c[0], "ref": c[1], "words": c[2]} for w, c in r["cells"].items()}}
                              for r in d["rows"]]})
    j.write_text(json.dumps({"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "same": SAME,
                             "dynasties": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    written.append(j)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor", default="", help="one founder's dynasty, printed generation by generation")
    ap.add_argument("--father", default="", help="with --anchor: the founder's father (homonyms apart)")
    ap.add_argument("--list", action="store_true", help="the dynasties and the works that have each (writes nothing)")
    ap.add_argument("--out", default="data/vamsa_read")
    ap.add_argument("--exports", default="exports")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.path.insert(0, str(ROOT / "scripts"))
    if not works_here(a.out):
        print("REFUSE: nothing read in %s yet (vamsa_read.py first)" % a.out)
        print("VERDICT: nothing aligned")
        print("NEXT: python scripts\\vamsa_read.py --work g6")
        return 1
    anchors = ANCHORS
    if a.anchor:
        anchors = [x for x in ANCHORS if (nkey(x[1]) == nkey(a.anchor) and (not a.father or father_is(a.father, x[2])))
                   or x[0] == a.anchor.lower()]
        if not anchors:
            anchors = [("custom", a.anchor, a.father, "the line of %s" % a.anchor)]
    dyn = dynasties(a.out, anchors)
    for d in dyn:
        c = d["counts"]
        print("  %-52s %d works, %3d generations: %3d agree, %3d most, %3d differ, %3d one work" % (
            d["title"][:52], len(d["lines"]), len(d["rows"]), c["agree"], c["most"], c["differ"], c["one"]))
        if a.anchor:
            for r in d["rows"]:
                print("    %-3s %-6s %s" % (r["gen"], r["status"], " | ".join(
                    "%s %s" % (w, r["cells"][w][0]) if w in r["cells"] else "%s -" % w for w in d["order"])))
            print("    pairs: %s" % "; ".join("%s %d/%d" % (k, x, n) for k, (x, n) in d["pairs"].items() if n))
    if not dyn:
        print("VERDICT: no dynasty is in two works yet")
        print("NEXT: python scripts\\vamsa_read.py --work g6")
        return 0
    if a.list or a.anchor:
        print("VERDICT: %d dynasties in two works or more (nothing written)" % len(dyn))
        print("NEXT: python scripts\\vamsa_align.py")
        return 0
    files = write(dyn, a.out, a.exports)
    print("  wrote %s" % ", ".join(str(p) for p in files))
    tot = {k: sum(d["counts"][k] for d in dyn) for k in ("agree", "most", "differ", "one")}
    print("VERDICT: %d dynasties aligned: %d generations agree, %d mostly, %d differ, %d in one work only (free)" % (
        len(dyn), tot["agree"], tot["most"], tot["differ"], tot["one"]))
    print("NEXT: open exports\\vamsa_align.md; then G6d (the person register) joins the persons the works agree on")
    return 0


if __name__ == "__main__":
    sys.exit(main())
