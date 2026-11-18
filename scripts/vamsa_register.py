#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_register.py  (2026-11-17)  VAMSA_REGISTER_2026_11_17   (G6d: one register of the persons of every work read)

vamsa_read.py reads each work's genealogical chapters into kinship statements checked against their verses (G5a, G6a,
G6b); vamsa_read.persons makes each work's persons (a name and the father the text gives); vamsa_align.py (G6c) sets
each dynasty side by side across the works. This joins the persons of all the works into one register, free and
read-only of the readings:

  - one person in two works is one entry when his names are one, his fathers are one, and his grandfathers, where both
    works give them, are one ("name, father and grandfather"); where a grandfather is not given, when G6c sets the two
    in one generation of one dynasty ("name and father, one generation of a dynasty"), else on name and father alone
    ("name and father"); never two whose grandfathers differ, nor through a third (an entry never holds two
    grandfathers that differ, nor two persons of one work whose fathers differ);
  - one name of two persons stays two: a son whose father is named by a statement whose words stand in the verse but
    whose name the verse does not give ("words": Parikshit son of Abhimanyu, "tasyam asya parasur garbho 'jayata") is
    taken for his sons' line when a verified statement names him as a father in that chapter or the next, so that
    mbh1's Janamejaya of 1.90.93 is the son of Abhimanyu's Parikshit, not of Arugvan's; such a step rests on "words";
  - two names of one person: a verified "other" statement whose words say he was called so (Paryasravas "yam ahuh
    pratipam nama", Devavrata "yam ahur bhisma iti") gives the entry both names, and a work that says Pratipa meets the
    one that says Paryasravas; where G6c's works give two names in one generation between one father and one son, the
    two are proposed as one ("proposed", ours, with both verses), never joined here.

Only verified statements (and the "words" above) make a person. A person who is no one's son in his work (a root) is
not an entry of his own (his name stands as his sons' father). A correlation of the texts, not a ruling between them.

Writes data\\vamsa_read\\register.json, exports\\vamsa_register.csv (an entry a row) and exports\\vamsa_register.md (the
counts, the homonyms kept apart, the two names said, the two names proposed, the persons of three works or more).

  python scripts\\vamsa_register.py                    the register and its files (free)
  python scripts\\vamsa_register.py --name Pariksit    the entries of a name, on screen (writes nothing)
  python scripts\\vamsa_register.py --stats            the counts only (writes nothing)
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import json
import sys
from pathlib import Path

MARK = "VAMSA_REGISTER_2026_11_17"
ROOT = Path(__file__).resolve().parents[1]
HOW = ("name, father and grandfather", "name and father, one generation of a dynasty", "name and father")


def _va():
    import vamsa_align as VA
    return VA


def _vr():
    import vamsa_read as VR
    return VR


# --------------------------------------------------------------------------------------------- a work's persons
def promoted(statements: list) -> list:
    """The "words" son_of statements whose son a verified son_of statement names as a father in that chapter or the
    next, taken for the line (promoted: True); the rest as they are."""
    VA, VR = _va(), _vr()
    fathers = {}
    for s in statements:
        if s.get("rel") == "son_of" and s.get("check") == "verified":
            fathers.setdefault(VR.letters(s.get("b")), set()).add(VA.chnum(s.get("chapter")))
    out = []
    for s in statements:
        if s.get("rel") == "son_of" and s.get("check") == "words" and VR.letters(s.get("a")):
            c = VA.chnum(s.get("chapter"))
            if c is not None and any(x is not None and 0 <= x - c <= 1 for x in fathers.get(VR.letters(s.get("a")), ())):
                s = dict(s, check="verified", promoted=True)
        out.append(s)
    return out


def said_aliases(statements: list) -> list:
    """[(chapter, keep, other, ref, words)]: vamsa_align.aliases_said (VAMSA_NAMES_2026_11_18: the stricter rule)."""
    return _va().aliases_said(statements)


def nodes_of(work: str, statements: list) -> dict:
    """{node id: node} for one work: each person of vamsa_read.persons (after vamsa_align.renamed and promoted()), with
    his grandfather where the work gives him, his other names said, and what he rests on."""
    VA, VR = _va(), _vr()
    st = promoted(VA.renamed(statements))
    lifted = {(VR.letters(s.get("a")), VR.letters(s.get("b")), s.get("ref")) for s in st if s.get("promoted")}
    ps = VR.persons(st)
    al = said_aliases(statements)
    out = {}
    for k, p in ps.items():
        aka = [{"name": o, "as": keep, "ref": r, "words": w} for ch, keep, o, r, w in al
               if VR.letters(keep) == VR.letters(p["name"]) and ch is not None and p.get("chapter") is not None
               and abs(VA.chnum(p["chapter"]) - ch) <= 1]
        def said(name):
            return [o for ch, keep, o, r, w in al
                    if name and VR.letters(keep) == VR.letters(name) and ch is not None and p.get("chapter") is not None
                    and abs(VA.chnum(p["chapter"]) - ch) <= 1]
        faka = said(p["father"])
        up = ps.get(p["up"]) if p.get("up") else None
        out["%s:%s" % (work, k)] = {
            "work": work, "key": k, "name": p["name"], "father": p["father"], "grand": up["father"] if up else None,
            "up": "%s:%s" % (work, p["up"]) if p.get("up") else None, "ref": p["ref"], "words": p["words"],
            "chapter": p.get("chapter"),
            "rests": "words" if (VR.letters(p["name"]), VR.letters(p["father"]), p["ref"]) in lifted else "verified",
            "aka": aka, "names": [p["name"]] + [a["name"] for a in aka], "fathers": [p["father"]] + faka,
            "grands": ([up["father"]] + said(up["father"])) if up else []}
    return out


# --------------------------------------------------------------------------------------------- the joins
def names_meet(xs, ys) -> bool:
    VA = _va()
    return any(VA.same(x, y) for x in xs for y in ys)


def fathers_meet(xs, ys) -> bool:
    VA = _va()
    return any(VA.same(x, y) or VA.father_is(x, y) or VA.father_is(y, x) for x in xs for y in ys if x and y)


class Sets:
    """Union-find over the nodes; a union is refused when the joined entry would hold two grandfathers that differ or
    two persons of one work whose fathers differ."""
    def __init__(self, nodes: dict):
        self.nodes = nodes
        self.up = {n: n for n in nodes}
        self.members = {n: [n] for n in nodes}

    def find(self, n):
        while self.up[n] != n:
            self.up[n] = self.up[self.up[n]]
            n = self.up[n]
        return n

    def clash(self, a, b):
        A, B = self.members[a], self.members[b]
        for x in A:
            nx = self.nodes[x]
            for y in B:
                ny = self.nodes[y]
                if nx["grands"] and ny["grands"] and not fathers_meet(nx["grands"], ny["grands"]):
                    return "grandfathers %s (%s) and %s (%s)" % (nx["grand"], nx["work"], ny["grand"], ny["work"])
                if nx["work"] == ny["work"] and not fathers_meet(nx["fathers"], ny["fathers"]):
                    return "two persons of %s, sons of %s and %s" % (nx["work"], nx["father"], ny["father"])
        return ""

    def union(self, x, y):
        a, b = self.find(x), self.find(y)
        if a == b:
            return "same"
        why = self.clash(a, b)
        if why:
            return why
        if len(self.members[a]) < len(self.members[b]):
            a, b = b, a
        self.up[b] = a
        self.members[a] += self.members.pop(b)
        return ""


def rows_of(dyn: list, nodes: dict) -> dict:
    """{node id: {"slug:gen"}}: where G6c set each person."""
    VR = _vr()
    at = {(n["work"], n["ref"], VR.letters(n["name"])): i for i, n in nodes.items()}
    out = {}
    for d in dyn:
        for r in d["rows"]:
            for w, c in r["cells"].items():
                i = at.get((w, c[1], VR.letters(c[0])))
                if i:
                    out.setdefault(i, set()).add("%s:%d" % (d["slug"], r["gen"]))
    return out


def pairs(nodes: dict) -> list:
    """[(strength, u, v)]: two persons whose names and fathers meet (0, 1, 2 as HOW), or (-1, u, v) when their
    grandfathers differ (two persons)."""
    VA = _va()
    bucket = collections.defaultdict(set)
    for i, n in nodes.items():
        for nm in n["names"]:
            k = VA.nkey(nm)
            if k:
                bucket[k[:2]].add(i)
    seen, out = set(), []
    for ids in bucket.values():
        ids = sorted(ids)
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                u, v = ids[x], ids[y]
                if (u, v) in seen:
                    continue
                seen.add((u, v))
                nu, nv = nodes[u], nodes[v]
                if not names_meet(nu["names"], nv["names"]) or not fathers_meet(nu["fathers"], nv["fathers"]):
                    continue
                if nu["grands"] and nv["grands"]:
                    out.append((0 if fathers_meet(nu["grands"], nv["grands"]) else -1, u, v))
                else:
                    out.append((2, u, v))
    return out


def proposed(dyn: list, said: set) -> list:
    """Two names in one generation of a G6c dynasty, between one father and one son in two works: proposed as one."""
    VA = _va()
    out, seen = [], set()
    for d in dyn:
        pos = {w: {(c[0], c[1]): i for i, c in enumerate(ln)} for w, ln in d["lines"].items()}
        for r in d["rows"]:
            if r["status"] not in ("most", "differ"):
                continue
            ws = list(r["cells"])
            for x in range(len(ws)):
                for y in range(x + 1, len(ws)):
                    a, b = ws[x], ws[y]
                    ca, cb = r["cells"][a], r["cells"][b]
                    if VA.same(ca[0], cb[0]):
                        continue
                    ia, ib = pos[a].get((ca[0], ca[1])), pos[b].get((cb[0], cb[1]))
                    la, lb = d["lines"][a], d["lines"][b]
                    if ia is None or ib is None or ia == 0 or ib == 0 or ia + 1 >= len(la) or ib + 1 >= len(lb):
                        continue
                    if not (VA.same(la[ia - 1][0], lb[ib - 1][0]) and VA.same(la[ia + 1][0], lb[ib + 1][0])):
                        continue
                    key = tuple(sorted((VA.nkey(ca[0]), VA.nkey(cb[0]))))
                    if key in seen or key in said:
                        continue
                    seen.add(key)
                    out.append({"dynasty": d["slug"], "gen": r["gen"], "father": la[ia - 1][0], "son": la[ia + 1][0],
                                "a": {"work": a, "name": ca[0], "ref": ca[1]}, "b": {"work": b, "name": cb[0],
                                                                                 "ref": cb[1]}})
    return out


# --------------------------------------------------------------------------------------------- the register
def build(out_dir, works=None, dyn=None) -> dict:
    VA = _va()
    works = works or VA.works_here(out_dir)
    nodes = {}
    for w in works:
        st = VA.statements_of(out_dir, w)
        if st:
            nodes.update(nodes_of(w, st))
    if dyn is None:
        dyn = VA.dynasties(out_dir, None, works)
    where = rows_of(dyn, nodes)
    S = Sets(nodes)
    joins, apart = collections.defaultdict(list), []
    found = pairs(nodes)
    for strength, u, v in found:
        if strength == 2 and where.get(u, set()) & where.get(v, set()):
            strength = 1
        if strength < 0:
            apart.append((u, v, "grandfathers %s and %s" % (nodes[u]["grand"], nodes[v]["grand"])))
    for level in (0, 1, 2):
        for strength, u, v in found:
            if strength == 2 and where.get(u, set()) & where.get(v, set()):
                strength = 1
            if strength != level:
                continue
            why = S.union(u, v)
            if why == "":
                joins[S.find(u)].append({"how": HOW[level], "a": u, "b": v})
            elif why != "same":
                apart.append((u, v, why))
    order = {w: i for i, w in enumerate(works)}
    entries = []
    for root, mem in S.members.items():
        mem = sorted(mem, key=lambda i: (order.get(nodes[i]["work"], 99), i))
        names = collections.Counter(VA.nkey(nodes[i]["name"]) for i in mem)
        top = names.most_common(1)[0][0]
        name = next(nodes[i]["name"] for i in mem if VA.nkey(nodes[i]["name"]) == top)
        fat = collections.Counter(nodes[i]["father"] for i in mem).most_common(1)[0][0]
        allnames, aka = [], []
        for i in mem:
            for nm in [nodes[i]["name"]] + [a["name"] for a in nodes[i]["aka"]]:
                if not any(VA.same(nm, x) for x in allnames):
                    allnames.append(nm)
            for a in nodes[i]["aka"]:   # VAMSA_NAMES_2026_11_18: each name said once
                if not any(x["ref"] == a["ref"] and x["name"] == a["name"] for x in aka):
                    aka.append(dict(a, work=nodes[i]["work"]))
        ws = []
        for i in mem:
            if nodes[i]["work"] not in ws:
                ws.append(nodes[i]["work"])
        entries.append({"id": mem[0], "name": name, "names": allnames, "father": fat, "works": ws,
                        "persons": [dict({k: nodes[i][k] for k in ("work", "name", "father", "grand", "ref", "words",
                                                                   "rests", "up")}, node=i) for i in mem],
                        "aka": aka, "joins": [], "dynasties": sorted(set().union(*(where.get(i, set())
                                                                                        for i in mem)))})
    allj = [j for js in joins.values() for j in js]
    by_node = {}
    for e in entries:
        for p in e["persons"]:
            by_node[p["node"]] = e
    for j in allj:   # a join is filed under the root of its moment; each goes to its entry
        by_node[j["a"]]["joins"].append(j)
    for e in entries:   # VAMSA_NAMES_2026_11_18: the father's entry and the sons' entries (through the works' lines)
        ups = collections.Counter(by_node[p["up"]]["id"] for p in e["persons"] if p.get("up") in by_node)
        top = ups.most_common(1)[0] if ups else None
        # the father's entry only where more than half the works that give him agree; else the works part, said so
        e["father_entry"] = top[0] if top and 2 * top[1] > sum(ups.values()) else None
        e["father_entries"] = [[k, n] for k, n in ups.most_common()] if top and e["father_entry"] is None else []
        e["sons"] = []
    ids = {e["id"]: e for e in entries}
    for e in entries:
        if e["father_entry"] in ids and e["id"] not in ids[e["father_entry"]]["sons"]:
            ids[e["father_entry"]]["sons"].append(e["id"])
    entries.sort(key=lambda e: (-len(e["works"]), VA.nkey(e["name"]), e["id"]))
    said = {tuple(sorted((VA.nkey(e["name"]), VA.nkey(a["name"])))) for e in entries for a in e["aka"]}
    for e in entries:
        for a in e["names"]:
            for b in e["names"]:
                if a != b:
                    said.add(tuple(sorted((VA.nkey(a), VA.nkey(b)))))
    homs, seen = [], set()
    for u, v, why in apart:
        eu, ev = by_node[u], by_node[v]
        if eu is ev:
            continue
        key = tuple(sorted((eu["id"], ev["id"])))
        if key in seen:
            continue
        seen.add(key)
        homs.append({"name": nodes[u]["name"], "a": {"entry": eu["id"], "work": nodes[u]["work"], "father":
                     nodes[u]["father"], "grand": nodes[u]["grand"], "ref": nodes[u]["ref"]},
                     "b": {"entry": ev["id"], "work": nodes[v]["work"], "father": nodes[v]["father"],
                           "grand": nodes[v]["grand"], "ref": nodes[v]["ref"]}, "why": why})
    prop = proposed(dyn, said)
    c = collections.Counter(j["how"] for j in allj)
    counts = {"works": len([w for w in works if any(n["work"] == w for n in nodes.values())]), "persons": len(nodes),
              "entries": len(entries), "in_two_works_or_more": sum(1 for e in entries if len(e["works"]) >= 2),
              "in_three_works_or_more": sum(1 for e in entries if len(e["works"]) >= 3),
              "joins": {h: c.get(h, 0) for h in HOW}, "homonyms_kept_apart": len(homs),
              "two_names_said": len({(a["work"], a["ref"], a["name"]) for e in entries for a in e["aka"]}),
              "two_names_proposed": len(prop),
              "rest_on_words": sum(1 for n in nodes.values() if n["rests"] == "words")}
    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": works,
            "counts": counts, "entries": entries, "homonyms": homs, "proposed": prop}


def write(reg: dict, out_dir, exports) -> list:
    VA = _va()
    ex = Path(exports)
    ex.mkdir(parents=True, exist_ok=True)
    p = ex / "vamsa_register.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["entry", "name", "other names", "father", "works", "how many works", "verses", "rests on",
                     "joined by", "dynasties (G6c generation)"])
        for e in reg["entries"]:
            wr.writerow([e["id"], e["name"], "; ".join(n for n in e["names"] if n != e["name"]), e["father"],
                         ", ".join(e["works"]), len(e["works"]),
                         "; ".join("%s %s" % (x["work"], x["ref"]) for x in e["persons"]),
                         ", ".join(sorted({x["rests"] for x in e["persons"]})),
                         "; ".join(sorted({j["how"] for j in e["joins"]})), ", ".join(e["dynasties"])])
    c = reg["counts"]
    md = ["# One register of the persons of the works read (%s)" % MARK, "",
          "Made %s by scripts\\vamsa_register.py from data\\vamsa_read (%s). A correlation of the texts, not a ruling"
          " between them: a join says the works give one name, one father and (where both give him) one"
          " grandfather; a proposed name is ours." % (reg["at"][:10], ", ".join(reg["works"])), "",
          "| Count | |", "|---|---|"]
    for k in ("works", "persons", "entries", "in_two_works_or_more", "in_three_works_or_more", "homonyms_kept_apart",
              "two_names_said", "two_names_proposed", "rest_on_words"):
        md.append("| %s | %d |" % (k.replace("_", " "), c[k]))
    for h in HOW:
        md.append("| joined by %s | %d |" % (h, c["joins"][h]))
    md += ["", "## One name kept as two (their grandfathers differ: two persons, or one told two ways)", ""]
    for h in reg["homonyms"][:200]:
        md.append("- %s: %s's, son of %s, grandson of %s (%s) and %s's, son of %s, grandson of %s (%s): %s" % (
            h["name"], h["a"]["work"], h["a"]["father"], h["a"]["grand"] or "?", h["a"]["ref"], h["b"]["work"],
            h["b"]["father"], h["b"]["grand"] or "?", h["b"]["ref"], h["why"]))
    md += ["", "## Two names of one person, said in a verse", ""]
    seen_aka = set()
    for e in reg["entries"]:
        for a in e["aka"]:
            if (a["work"], a["ref"], a["name"]) in seen_aka:
                continue
            seen_aka.add((a["work"], a["ref"], a["name"]))
            md.append("- %s is also %s (%s %s: %s)" % (a.get("as") or e["name"], a["name"], a["work"], a["ref"],
                                                       a["words"]))
    md += ["", "## Two names of one person, proposed (ours: one father and one son, two names)", ""]
    for p_ in reg["proposed"]:
        md.append("- %s (%s %s) and %s (%s %s): son of %s, father of %s (G6c %s, generation %d)" % (
            p_["a"]["name"], p_["a"]["work"], p_["a"]["ref"], p_["b"]["name"], p_["b"]["work"], p_["b"]["ref"],
            p_["father"], p_["son"], p_["dynasty"], p_["gen"]))
    md += ["", "## The persons of three works or more", ""]
    for e in [e for e in reg["entries"] if len(e["works"]) >= 3][:300]:
        md.append("- %s%s, son of %s: %s" % (e["name"], " (also %s)" % ", ".join(n for n in e["names"]
                                                                                if n != e["name"])
                                             if len(e["names"]) > 1 else "", e["father"],
                                             "; ".join("%s %s" % (x["work"], x["ref"]) for x in e["persons"])))
    q = ex / "vamsa_register.md"
    q.write_text("\n".join(md) + "\n", encoding="utf-8")
    j = Path(out_dir) / "register.json"
    j.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    return [p, q, j]


def qkey(name: str) -> str:
    """VAMSA_NAMES_2026_11_18: a name as typed in plain letters meets it in IAST: Krishna, Krsna and Krsna are one;
    Bhishma and Bhisma; Parikshit and Pariksit (sh, ch, double vowels and ri set aside on both sides)."""
    k = _va().nkey(name)
    for a, b in (("sh", "s"), ("ch", "c"), ("aa", "a"), ("ii", "i"), ("uu", "u"), ("ri", "r"), ("w", "v")):
        k = k.replace(a, b)
    return k


def show(reg: dict, name: str) -> list:
    """The entries of a name: those whose names meet it letter for letter (qkey); none, those near it (same())."""
    VA = _va()
    k = qkey(name)
    got = [e for e in reg["entries"] if any(qkey(n) == k for n in e["names"])]
    return got or [e for e in reg["entries"] if any(VA.same(name, n) for n in e["names"])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="", help="the entries of a name, on screen (writes nothing)")
    ap.add_argument("--stats", action="store_true", help="the counts only (writes nothing)")
    ap.add_argument("--out", default="data/vamsa_read")
    ap.add_argument("--exports", default="exports")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.path.insert(0, str(ROOT / "scripts"))
    VA = _va()
    if not VA.works_here(a.out):
        print("REFUSE: nothing read in %s yet (vamsa_read.py first)" % a.out)
        print("VERDICT: no register")
        print("NEXT: python scripts\\vamsa_read.py --work g6")
        return 1
    reg = build(a.out)
    c = reg["counts"]
    print("  %d works, %d persons: %d entries, %d in two works or more, %d in three or more" % (
        c["works"], c["persons"], c["entries"], c["in_two_works_or_more"], c["in_three_works_or_more"]))
    print("  joined: %s" % "; ".join("%d by %s" % (c["joins"][h], h) for h in HOW))
    print("  kept apart (one name, two persons): %d; two names said: %d; proposed: %d; resting on words: %d" % (
        c["homonyms_kept_apart"], c["two_names_said"], c["two_names_proposed"], c["rest_on_words"]))
    if a.name:
        got = show(reg, a.name)
        for e in got:
            print("  %s: %s%s, son of %s; %d works; %s" % (e["id"], e["name"], " (also %s)" % ", ".join(
                n for n in e["names"] if n != e["name"]) if len(e["names"]) > 1 else "", e["father"], len(e["works"]),
                "; ".join(sorted({j["how"] for j in e["joins"]})) or "not joined"))
            for x in e["persons"]:
                print("      %-7s %s son of %s%s, %s (%s)" % (x["work"], x["name"], x["father"], ", grandson of %s"
                                                         % x["grand"] if x["grand"] else "", x["ref"], x["rests"]))
        print("VERDICT: %d entries named %s (nothing written)" % (len(got), a.name))
        print("NEXT: python scripts\\vamsa_register.py")
        return 0
    if a.stats:
        print("VERDICT: the register counted (nothing written)")
        print("NEXT: python scripts\\vamsa_register.py")
        return 0
    files = write(reg, a.out, a.exports)
    print("  wrote %s" % ", ".join(str(p) for p in files))
    print("VERDICT: %d persons in %d entries; %d in two works or more; %d homonyms kept apart (free)" % (
        c["persons"], c["entries"], c["in_two_works_or_more"], c["homonyms_kept_apart"]))
    print("NEXT: open exports\\vamsa_register.md; python scripts\\vamsa_register.py --name Pariksit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
