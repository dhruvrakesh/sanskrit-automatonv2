#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_names_2026_11_18.py  (2026-11-18)  VAMSA_NAMES_2026_11_18

P1 of the path of 17 Nov, night (ASKS section 32 of the plan): the register's second names healed, alone (the page of
17 Nov is held, not released). Seen in exports\\vamsa_register.md of 17 Nov, 23:36:

  scripts/vamsa_align.py     aliases_said(): a second name is taken from a verified "other" statement only when the
                             name stands in the words, the word that says "called" stands apart from it, neither name
                             is a woman of the statements, and no word makes him another person or a place (NOT_ALIAS:
                             a minister, a daughter's marriage, a wife, a mother, a land). Gone: Ripunjaya "also Munika"
                             (his minister), Sraddhadeva "also Samjna" (his mother), Saubhari in Mandhatr's entry,
                             Kuru "also Kuruksetra"; kept: Vikukshi Sasada, Devavrata Bhisma, Paryasravas Pratipa.
                             aliases() is the same list as renamed() takes it.
  scripts/vamsa_register.py  uses it; each name said once ("Devavrata is also Bhisma"); --name takes plain letters
                             (Bhishma, Krishna, Parikshit) and the exact name before the near ones; each entry has its
                             father's entry and its sons' (the father's only where more than half the works that give
                             him agree; else the works part, and the entries they point to are kept).

Free and read-only of the readings. Anchored edits, all or nothing; a file that already carries the marker is skipped;
.bak_vamsanames_<date> copies.

  python scripts\\patch_vamsa_names_2026_11_18.py --check
  python scripts\\patch_vamsa_names_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_NAMES_2026_11_18'
TAG = 'vamsanames'
FILES = ['scripts/vamsa_align.py', 'scripts/vamsa_register.py']
NEEDS = {'scripts/vamsa_align.py': 'VAMSA_ALIGN_2026_11_17', 'scripts/vamsa_register.py': 'VAMSA_REGISTER_2026_11_17'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_align.py', 1, '# ucyate, visruta, prathita.\nALIAS_MARKS = ("samjn", "nama", "namn", "ahu", "smrt", "khyat", "ucyat", "visrut", "prathit")\n# The founders of the dynasties the genealogical chapters tell, and their fathers (the solar and the lunar lines).\nANCHORS = [',
     '# ucyate, visruta, prathita.\nALIAS_MARKS = ("samjn", "nama", "namn", "ahu", "smrt", "khyat", "ucyat", "visrut", "prathit")\n# VAMSA_NAMES_2026_11_18: words that say the second name is another person or a place, not a second name (a minister,\n# a daughter\'s marriage, a wife, a mother, a sister, a friend, a priest, a land, a city)\nNOT_ALIAS = ("amaty", "mantri", "duhit", "sambandh", "bharya", "patni", "matr", "bhagin", "sakh", "purohit",\n             "jangal", "desa", "nagar")\n# The founders of the dynasties the genealogical chapters tell, and their fathers (the solar and the lunar lines).\nANCHORS = [')

edit('scripts/vamsa_align.py', 2, '\n\ndef aliases(statements: list) -> list:\n    """[(chapter, name, as)]: one person by two names, from the verified "other" statements whose words say he was\n    called so; the name kept is the one that is a son (has a father) in these statements, else the first."""\n    import vamsa_read as VR\n    sons = {VR.letters(s.get("a")) for s in statements if s.get("rel") == "son_of" and s.get("check") == "verified"}\n    out = []\n    for s in statements:',
     '\n\ndef aliases_said(statements: list) -> list:\n    """[(chapter, keep, other, ref, words)]: one person by two names, from the verified "other" statements whose words\n    say he was called so; the name kept is the one that is a son (has a father) in these statements, else the first.\n    VAMSA_NAMES_2026_11_18: the second name must stand in the words; never a woman of these statements (a wife, a\n    daughter, a sister, a mother) nor words that make him another person or a place (NOT_ALIAS)."""\n    import vamsa_read as VR\n    sons = {VR.letters(s.get("a")) for s in statements if s.get("rel") == "son_of" and s.get("check") == "verified"}\n    said = [s for s in statements if s.get("check") in ("verified", "words")]\n    female = {VR.letters(s.get("a")) for s in said if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}\n    female |= {VR.letters(s.get("b")) for s in said if s.get("rel") == "born_of"}\n    out = []\n    for s in statements:')

edit('scripts/vamsa_align.py', 3, '            continue\n        w = VR.folded(s.get("words"))\n        if not any(m in w for m in ALIAS_MARKS):\n            continue\n        a, b = str(s.get("a") or ""), str(s.get("b") or "")',
     '            continue\n        w = VR.folded(s.get("words"))\n        if any(m in w for m in NOT_ALIAS):\n            continue\n        a, b = str(s.get("a") or ""), str(s.get("b") or "")')

edit('scripts/vamsa_align.py', 4, '            continue\n        keep, other = (b, a) if VR.letters(b) in sons and VR.letters(a) not in sons else (a, b)\n        out.append((chnum(s.get("chapter")), other, keep))\n    return out\n\n',
     '            continue\n        keep, other = (b, a) if VR.letters(b) in sons and VR.letters(a) not in sons else (a, b)\n        ko, kw = nkey(other), nkey(s.get("words"))\n        if not ko or ko[:5] not in kw or VR.letters(other) in female or VR.letters(keep) in female:\n            continue\n        rest = kw.replace(ko[:5], " ", 1)   # the word that says "called" stands apart from the name (not Samjna\'s own)\n        if not any(m in rest for m in ALIAS_MARKS):\n            continue\n        out.append((chnum(s.get("chapter")), keep, other, s.get("ref"), s.get("words")))\n    return out\n\n\ndef aliases(statements: list) -> list:\n    """[(chapter, name, as)]: aliases_said() as renamed() takes them."""\n    return [(ch, other, keep) for ch, keep, other, _r, _w in aliases_said(statements)]\n\n')

edit('scripts/vamsa_register.py', 1, '\ndef said_aliases(statements: list) -> list:\n    """[(chapter, keep, other, ref, words)]: vamsa_align.aliases with the verse."""\n    VA, VR = _va(), _vr()\n    sons = {VR.letters(s.get("a")) for s in statements if s.get("rel") == "son_of" and s.get("check") == "verified"}\n    out = []\n    for s in statements:\n        if s.get("rel") != "other" or s.get("check") != "verified":\n            continue\n        if not any(m in VR.folded(s.get("words")) for m in VA.ALIAS_MARKS):\n            continue\n        a, b = str(s.get("a") or ""), str(s.get("b") or "")\n        if not VR.letters(a) or not VR.letters(b) or VA.same(a, b):\n            continue\n        keep, other = (b, a) if VR.letters(b) in sons and VR.letters(a) not in sons else (a, b)\n        out.append((VA.chnum(s.get("chapter")), keep, other, s.get("ref"), s.get("words")))\n    return out\n\n',
     '\ndef said_aliases(statements: list) -> list:\n    """[(chapter, keep, other, ref, words)]: vamsa_align.aliases_said (VAMSA_NAMES_2026_11_18: the stricter rule)."""\n    return _va().aliases_said(statements)\n\n')

edit('scripts/vamsa_register.py', 2, '    out = {}\n    for k, p in ps.items():\n        aka = [{"name": o, "ref": r, "words": w} for ch, keep, o, r, w in al\n               if VR.letters(keep) == VR.letters(p["name"]) and ch is not None and p.get("chapter") is not None\n               and abs(VA.chnum(p["chapter"]) - ch) <= 1]',
     '    out = {}\n    for k, p in ps.items():\n        aka = [{"name": o, "as": keep, "ref": r, "words": w} for ch, keep, o, r, w in al\n               if VR.letters(keep) == VR.letters(p["name"]) and ch is not None and p.get("chapter") is not None\n               and abs(VA.chnum(p["chapter"]) - ch) <= 1]')

edit('scripts/vamsa_register.py', 3, '                if not any(VA.same(nm, x) for x in allnames):\n                    allnames.append(nm)\n            aka += [dict(a, work=nodes[i]["work"]) for a in nodes[i]["aka"]]\n        ws = []\n        for i in mem:',
     '                if not any(VA.same(nm, x) for x in allnames):\n                    allnames.append(nm)\n            for a in nodes[i]["aka"]:   # VAMSA_NAMES_2026_11_18: each name said once\n                if not any(x["ref"] == a["ref"] and x["name"] == a["name"] for x in aka):\n                    aka.append(dict(a, work=nodes[i]["work"]))\n        ws = []\n        for i in mem:')

edit('scripts/vamsa_register.py', 4, '        entries.append({"id": mem[0], "name": name, "names": allnames, "father": fat, "works": ws,\n                        "persons": [dict({k: nodes[i][k] for k in ("work", "name", "father", "grand", "ref", "words",\n                                                                   "rests")}, node=i) for i in mem],\n                        "aka": aka, "joins": [], "dynasties": sorted(set().union(*(where.get(i, set())\n                                                                                        for i in mem)))})',
     '        entries.append({"id": mem[0], "name": name, "names": allnames, "father": fat, "works": ws,\n                        "persons": [dict({k: nodes[i][k] for k in ("work", "name", "father", "grand", "ref", "words",\n                                                                   "rests", "up")}, node=i) for i in mem],\n                        "aka": aka, "joins": [], "dynasties": sorted(set().union(*(where.get(i, set())\n                                                                                        for i in mem)))})')

edit('scripts/vamsa_register.py', 5, '    for j in allj:   # a join is filed under the root of its moment; each goes to its entry\n        by_node[j["a"]]["joins"].append(j)\n    entries.sort(key=lambda e: (-len(e["works"]), VA.nkey(e["name"]), e["id"]))\n    said = {tuple(sorted((VA.nkey(e["name"]), VA.nkey(a["name"])))) for e in entries for a in e["aka"]}',
     '    for j in allj:   # a join is filed under the root of its moment; each goes to its entry\n        by_node[j["a"]]["joins"].append(j)\n    for e in entries:   # VAMSA_NAMES_2026_11_18: the father\'s entry and the sons\' entries (through the works\' lines)\n        ups = collections.Counter(by_node[p["up"]]["id"] for p in e["persons"] if p.get("up") in by_node)\n        top = ups.most_common(1)[0] if ups else None\n        # the father\'s entry only where more than half the works that give him agree; else the works part, said so\n        e["father_entry"] = top[0] if top and 2 * top[1] > sum(ups.values()) else None\n        e["father_entries"] = [[k, n] for k, n in ups.most_common()] if top and e["father_entry"] is None else []\n        e["sons"] = []\n    ids = {e["id"]: e for e in entries}\n    for e in entries:\n        if e["father_entry"] in ids and e["id"] not in ids[e["father_entry"]]["sons"]:\n            ids[e["father_entry"]]["sons"].append(e["id"])\n    entries.sort(key=lambda e: (-len(e["works"]), VA.nkey(e["name"]), e["id"]))\n    said = {tuple(sorted((VA.nkey(e["name"]), VA.nkey(a["name"])))) for e in entries for a in e["aka"]}')

edit('scripts/vamsa_register.py', 6, '              "in_three_works_or_more": sum(1 for e in entries if len(e["works"]) >= 3),\n              "joins": {h: c.get(h, 0) for h in HOW}, "homonyms_kept_apart": len(homs),\n              "two_names_said": sum(len(e["aka"]) for e in entries), "two_names_proposed": len(prop),\n              "rest_on_words": sum(1 for n in nodes.values() if n["rests"] == "words")}\n    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": works,',
     '              "in_three_works_or_more": sum(1 for e in entries if len(e["works"]) >= 3),\n              "joins": {h: c.get(h, 0) for h in HOW}, "homonyms_kept_apart": len(homs),\n              "two_names_said": len({(a["work"], a["ref"], a["name"]) for e in entries for a in e["aka"]}),\n              "two_names_proposed": len(prop),\n              "rest_on_words": sum(1 for n in nodes.values() if n["rests"] == "words")}\n    return {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": works,')

edit('scripts/vamsa_register.py', 7, '            h["b"]["father"], h["b"]["grand"] or "?", h["b"]["ref"], h["why"]))\n    md += ["", "## Two names of one person, said in a verse", ""]\n    for e in reg["entries"]:\n        for a in e["aka"]:\n            md.append("- %s is also %s (%s %s: %s)" % (e["name"], a["name"], a["work"], a["ref"], a["words"]))\n    md += ["", "## Two names of one person, proposed (ours: one father and one son, two names)", ""]\n    for p_ in reg["proposed"]:',
     '            h["b"]["father"], h["b"]["grand"] or "?", h["b"]["ref"], h["why"]))\n    md += ["", "## Two names of one person, said in a verse", ""]\n    seen_aka = set()\n    for e in reg["entries"]:\n        for a in e["aka"]:\n            if (a["work"], a["ref"], a["name"]) in seen_aka:\n                continue\n            seen_aka.add((a["work"], a["ref"], a["name"]))\n            md.append("- %s is also %s (%s %s: %s)" % (a.get("as") or e["name"], a["name"], a["work"], a["ref"],\n                                                       a["words"]))\n    md += ["", "## Two names of one person, proposed (ours: one father and one son, two names)", ""]\n    for p_ in reg["proposed"]:')

edit('scripts/vamsa_register.py', 8, '\n\ndef show(reg: dict, name: str) -> list:\n    VA = _va()\n    return [e for e in reg["entries"] if any(VA.same(name, n) for n in e["names"])]\n\n',
     '\n\ndef qkey(name: str) -> str:\n    """VAMSA_NAMES_2026_11_18: a name as typed in plain letters meets it in IAST: Krishna, Krsna and Krsna are one;\n    Bhishma and Bhisma; Parikshit and Pariksit (sh, ch, double vowels and ri set aside on both sides)."""\n    k = _va().nkey(name)\n    for a, b in (("sh", "s"), ("ch", "c"), ("aa", "a"), ("ii", "i"), ("uu", "u"), ("ri", "r"), ("w", "v")):\n        k = k.replace(a, b)\n    return k\n\n\ndef show(reg: dict, name: str) -> list:\n    """The entries of a name: those whose names meet it letter for letter (qkey); none, those near it (same())."""\n    VA = _va()\n    k = qkey(name)\n    got = [e for e in reg["entries"] if any(qkey(n) == k for n in e["names"])]\n    return got or [e for e in reg["entries"] if any(VA.same(name, n) for n in e["names"])]\n\n')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

