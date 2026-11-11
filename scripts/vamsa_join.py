#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_join.py  (2026-11-11)  VAMSA_JOIN_2026_11_11   (G5b: the dynasties joined to the index's persons)

G5a (scripts\\vamsa_read.py) read the Visnupurana's book 4 and the Bhagavatapurana's books 9 and 12.1 verse by verse into
kinship statements and drew their father-to-son lines, keeping homonyms apart by the father the text gives; a father
named in another chapter was left a line of his own (VAMSA_HEAL_2026_11_11). This joins them to the Purana Index's
persons (V. R. R. Dikshitar's, the "pui" of the genealogy pages), free and read-only:

  - a person of a line (a name and the father the text gives) is the index's person of that name whose father in the
    index has the text's father's name ("father": both names agree); else, when the index has one person of that name
    only, that one ("name": the father not known to the index, or another);
  - a line's root, a father the text names in another chapter, is joined to the person of the line whose index person
    is his ("joined by the index"): the lines run on across the chapters, homonyms still apart;
  - each step says what the index says of it: "agrees" (the index has this father and son), "differs" (the index gives
    the son another father), "new" (the index has the son, no father) or "absent" (the index has not the son).

Writes data\\vamsa_read\\dynasties.json (the lines, each step with its verse, its Sanskrit words and its index person) and
exports\\vamsa_dynasties.csv; prints the counts and the longest lines. index_sync.py sends the same lines to the site
(the table dynasties, docs\\cloud\\C28_index_dynasties_2026-11-11.sql), for the Dynasties page. Nothing is called and
nothing written but the two files.

  python scripts\\vamsa_join.py                 the join (free)
  python scripts\\vamsa_join.py --work vip4     one work
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

MARK = "VAMSA_JOIN_2026_11_11"
ROOT = Path(__file__).resolve().parents[1]
INDEX = "pui"                                   # the Purana Index: the persons of the Puranas
TEXT_OF = {"vip4": "vi", "bhp9": "bh", "bhp12": "bh"}   # the codes of vamsa.db's texts (GRETIL's same files)
MIN_SHOWN = 3                                   # a line of fewer persons is not sent


def key_of(name: str) -> str:
    """A name as the index's head words are compared: the honorific, the homonym's number and the diacritics off."""
    import relations_view as rv
    import vamsa_view as vv
    return rv.split_mark(vv._hon(str(name or "")))[0]


class Index:
    """The index's persons by their names, with their fathers (vamsa_view's graph: the steps the genealogy pages draw)."""

    def __init__(self, g: dict, src: str = INDEX):
        self.g, self.src = g, src
        self.by_name = {}
        for (s, e), head in g["shown"].items():
            if s == src and e is not None and e >= 0:
                k = key_of(head)
                if k:
                    self.by_name.setdefault(k, []).append(e)
        for k in self.by_name:
            self.by_name[k].sort()

    def head(self, e) -> str:
        return self.g["shown"].get((self.src, e), str(e))

    def fathers(self, e) -> list:
        """The parents the index gives, not marked female."""
        out = []
        for (_s, p) in sorted(self.g["par"].get((self.src, e), ())):
            if self.g["sex"].get((self.src, p)) != "f":
                out.append(p)
        return out

    def person(self, name: str, father: str):
        """(entry, how, the father's entry or None): how is "father", "name" or "" (not told apart, or not there)."""
        cands = self.by_name.get(key_of(name), [])
        fk = key_of(father)
        both = [(e, p) for e in cands for p in self.fathers(e) if key_of(self.head(p)) == fk]
        if len({e for e, _p in both}) == 1:
            return both[0][0], "father", both[0][1]
        if not both and len(cands) == 1:
            return cands[0], "name", None
        return None, "", None

    def verdict(self, entry, how: str) -> str:
        if entry is None:
            return "absent"
        if how == "father":
            return "agrees"
        return "differs" if self.fathers(entry) else "new"


def join(statements: list, ix: Index) -> dict:
    """{"persons": {key: person}, "lines": [[step]], "counts": {...}}: vamsa_read.persons, each with its index person,
    the roots joined by the index, the lines drawn again."""
    import vamsa_read as VR
    ps = VR.persons(statements)
    by_entry = {}
    for k, p in ps.items():
        e, how, fe = ix.person(p["name"], p["father"])
        p.update(entry=e, how=how, father_entry=fe, index=ix.verdict(e, how), joined="chapter" if p["up"] else "")
        if e is not None:
            by_entry.setdefault(e, []).append(k)
    joined = 0
    for k, p in ps.items():
        if p["up"] or p["father_entry"] is None:
            continue
        cand = [q for q in by_entry.get(p["father_entry"], ()) if q != k]
        if len(cand) != 1:
            continue
        q, seen, ok = cand[0], {k}, True
        while q:   # no person his own ancestor
            if q in seen:
                ok = False
                break
            seen.add(q)
            q = ps[q]["up"]
        if ok:
            p["up"], p["joined"] = cand[0], "index"
            joined += 1
    lines = lines_of(ps)
    counts = {"persons": len(ps), "father": sum(1 for p in ps.values() if p["how"] == "father"),
              "name": sum(1 for p in ps.values() if p["how"] == "name"),
              "none": sum(1 for p in ps.values() if not p["how"]), "joined": joined}
    for v in ("agrees", "differs", "new", "absent"):
        counts[v] = sum(1 for p in ps.values() if p["index"] == v)
    return {"persons": ps, "lines": lines, "counts": counts}


def lines_of(ps: dict) -> list:
    """The father-to-son lines, longest first: [[{"name", "father", "ref", "words", "entry", "how", "index",
    "joined"}]]; the first step is the root (a father who is not a son here: his name only)."""
    import vamsa_read as VR
    kids = {}
    for k, p in ps.items():
        kids.setdefault(p["up"] or "root:" + VR.letters(p["father"]), []).append(k)
    memo = {}

    def down(k):
        if k not in memo:
            best = []
            for c in sorted(kids.get(k, ()), key=lambda x: ps[x]["pos"]):
                got = down(c)
                if len(got) > len(best):
                    best = got
            memo[k] = [k] + best
        return memo[k]
    out = []
    for r in (k for k in kids if k.startswith("root:")):
        chain = down(r)[1:]
        if not chain:
            continue
        first = ps[chain[0]]
        steps = [{"name": first["father"], "father": "", "ref": None, "words": None, "entry": first.get("father_entry"),
                  "how": "", "index": "", "joined": ""}]
        for k in chain:
            p = ps[k]
            steps.append({"name": p["name"], "father": p["father"], "ref": p["ref"], "words": p["words"],
                          "entry": p.get("entry"), "how": p.get("how", ""), "index": p.get("index", ""),
                          "joined": p.get("joined", "")})
        out.append(steps)
    return sorted(out, key=lambda x: (-len(x), VR.letters(x[0]["name"])))


def labels(statements: list, line: list) -> str:
    """The line's name from the text's own line_of statements ("the Yadavas, named after Yadu"), else ""."""
    import vamsa_read as VR
    names = {VR.letters(s["name"]) for s in line}
    for s in statements:
        if s.get("check") == "verified" and s.get("rel") == "line_of" and VR.letters(s.get("b")) in names:
            if VR.letters(s.get("a")) == VR.letters(s.get("b")):
                return "the line of %s" % s.get("b")
            return "%s (after %s)" % (s.get("a"), s.get("b"))
    return ""


def dynasties(out_dir, db: str, kin_db: str, works=None, graph=None) -> dict:
    """{work: {"title", "text", "counts", "lines": [{"n", "label", "length", "steps"}]}} from the stored readings
    (data\\vamsa_read) and the index (kin.db through vamsa_view's graph); {} when nothing is read yet."""
    import vamsa_read as VR
    import vamsa_view as vv
    recs = {wk: VR.records(out_dir, wk) for wk in (works or list(VR.WORKS))}
    if not any(recs.values()):
        return {}
    g = graph if graph is not None else vv._graph(db, kin_db)
    ix = Index(g)
    out = {}
    for wk, rs in recs.items():
        if not rs:
            continue
        st = [dict(s, chapter=r.get("chapter")) for r in rs for s in (r.get("statements") or [])]
        j = join(st, ix)
        lines = []
        for n, ln in enumerate((l for l in j["lines"] if len(l) >= MIN_SHOWN), 1):
            for s in ln:
                s["person"] = "%s:%d" % (INDEX, s["entry"]) if s.get("entry") is not None else None
                s["index_head"] = ix.head(s["entry"]) if s.get("entry") is not None else None
            lines.append({"n": n, "label": labels(st, ln), "length": len(ln), "steps": ln})
        out[wk] = {"title": VR.WORKS[wk]["title"], "text": TEXT_OF.get(wk, ""), "counts": j["counts"],
                   "source": "%s; %s (data entry: %s)" % (VR.WORKS[wk]["member"], VR.GRETIL, VR.WORKS[wk]["entry"]),
                   "lines": lines}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="all")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--kin-db", default="data/shelf/kin.db")
    ap.add_argument("--out", default="data/vamsa_read")
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.path.insert(0, str(ROOT / "scripts"))
    import vamsa_read as VR
    if a.work != "all" and a.work not in VR.WORKS:
        print("REFUSE: --work is all or one of %s" % ", ".join(VR.WORKS)); print("VERDICT: nothing joined"); print("NEXT: ")
        return 1
    for p, what in ((a.db, "the database"), (a.kin_db, "the kinships (kin_index.py)")):
        if not Path(p).exists():
            print("REFUSE: %s not found (%s)" % (what, p)); print("VERDICT: nothing joined"); print("NEXT: ")
            return 1
    if a.immutable:
        import relations_view as rv
        import index_sync
        rv.ro = index_sync.ro_immutable
    d = dynasties(a.out, a.db, a.kin_db, None if a.work == "all" else [a.work])
    if not d:
        print("VERDICT: nothing read yet: run vamsa_read.py first")
        print("NEXT: python scripts\\vamsa_read.py")
        return 0
    for wk, w in d.items():
        c = w["counts"]
        print("  %-6s %s: %d persons; the index's person found for %d (%d by the father, %d by the name alone); %d roots "
              "joined across chapters by the index" % (wk, w["title"], c["persons"], c["father"] + c["name"], c["father"],
                                                       c["name"], c["joined"]))
        print("         the steps against the index: %d agree, %d differ (another father), %d new (no father there), "
              "%d absent (no such person)" % (c["agrees"], c["differs"], c["new"], c["absent"]))
        for ln in w["lines"][:5]:
            print("         a line of %d%s: %s" % (ln["length"], (" (%s)" % ln["label"]) if ln["label"] else "",
                                                  " > ".join(s["name"] for s in ln["steps"])))
    p = Path(a.out) / "dynasties.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": d},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    ex = Path(a.exports)
    ex.mkdir(parents=True, exist_ok=True)
    q = ex / "vamsa_dynasties.csv"
    with open(q, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["work", "line", "label", "step", "name", "father", "ref", "words", "index_person", "index_head",
                     "found_by", "index_says", "joined"])
        for wk, w in d.items():
            for ln in w["lines"]:
                for i, s in enumerate(ln["steps"]):
                    wr.writerow([wk, ln["n"], ln["label"], i, s["name"], s["father"], s["ref"] or "", s["words"] or "",
                                 s["person"] or "", s["index_head"] or "", s["how"], s["index"], s["joined"]])
    print("  wrote %s and %s" % (p, q))
    n = sum(len(w["lines"]) for w in d.values())
    print("VERDICT: %d lines of %d persons or more joined to the Purana Index; index_sync.py sends them once C28 is "
          "pasted and corpus-index deployed again" % (n, MIN_SHOWN))
    print("NEXT: python scripts\\index_sync.py   (the plan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
