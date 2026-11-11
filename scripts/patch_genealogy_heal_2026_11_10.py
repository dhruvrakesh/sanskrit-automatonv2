#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_genealogy_heal_2026_11_10.py  (2026-11-10)  GENEALOGY_HEAL_2026_11_10

Asked on 10 Nov: "such a genealogy front end does not make sense for anybody ... we cant even get the genealogy of
Kaunteya (Arjun) right". docs\\GENEALOGY_2026-11-10.md. From the indexes' own words, no model:

  scripts/vamsa_view.py   a son begotten by another (Arjuna by Indra) is drawn up through his mother's husband
                          (Pandu), the begetter beside him; down, a son before a daughter, and the longest lines are
                          fathers' lines (no woman on them); no line passes to a person
                          married to one already on it; a name of several entries is joined to the one whose entry
                          gives three or more of the names the stating entry gives ("shared"); an entry the index
                          defines as another ("Kaunteya (the son of Kunti) = Arjuna", "a name of Rama") is tied to
                          that person's entry (aliases)
  scripts/index_sync.py   the epithets (same_as, gloss) on the persons' rows, and a row of an epithet's own, sent only
                          to a site with C26 (docs\\cloud\\C26_index_aliases_2026-11-10.sql); before it, the rows
                          without them

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_genheal_<date> copies.

  python scripts\\patch_genealogy_heal_2026_11_10.py --check
  python scripts\\patch_genealogy_heal_2026_11_10.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'GENEALOGY_HEAL_2026_11_10'
TAG = 'genheal'
FILES = ['scripts/vamsa_view.py', 'scripts/index_sync.py']
NEEDS = {'scripts/vamsa_view.py': 'HEAL_2026_10_28', 'scripts/index_sync.py': 'B2_SITE_2026_10_28'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_view.py', 1, 'Nothing is written, no model is called, every store is opened read-only. The relations are the indexes\' statements;\na verse where both names stand says where to read, not that it states the relation.\n"""\nfrom __future__ import annotations',
     'Nothing is written, no model is called, every store is opened read-only. The relations are the indexes\' statements;\na verse where both names stand says where to read, not that it states the relation.\n\nGENEALOGY_HEAL_2026_11_10 (docs/GENEALOGY_2026-11-10.md), asked on 10 Nov: "we cant even get the genealogy of Kaunteya\n(Arjun) right". Three mends, each from the index\'s own statements:\n  the line\'s father    a son begotten by another (Arjuna by Indra, Pandu by Vyasa: the index states both fathers)\n                       is drawn up through his mother\'s husband, as the dynasties count him (Arjuna: Pandu, then the\n                       Kurus); the begetter stays beside him as another parent ("line through" draws his line); down,\n                       a son before a daughter, and never into another father\'s line;\n  the joins            a name the index gives with several entries is joined to the one entry that gives at least\n                       three of the names the stating entry gives, and more than any other ("shared"): Pandu\'s\n                       "father of Arjuna" is the Pandava\'s entry, not Kartavirya\'s;\n  no line turned back  a line never passes to a person married to one already on it (Soerensen\'s longest line ran\n                       Daksa, Aditi, Visnu, Brahman, Marici, Kasyapa: Kasyapa is Aditi\'s husband);\n  the epithets         an entry the index defines as another ("Kaunteya (the son of Kunti) = Arjuna", Soerensen; "a\n                       name of Rama", the Purana Index) is tied to that person\'s entry (aliases): Soerensen defines\n                       5,525 of his 12,647 entries so; a plural ("the sons of Kunti") is tied to the persons its\n                       singular entries name.\n"""\nfrom __future__ import annotations')

edit('scripts/vamsa_view.py', 2, 'MALE_AS_SUBJECT = {"son_of", "father_of", "husband_of", "brother_of", "grandson_of", "grandfather_of", "king_of"}\nMARRIAGE = {"wife_of", "husband_of", "married", "queen_of"}\nJOIN_ORDER = ["rule", "verse", "named"]   # how a step\'s two persons were told apart, the surest first\nCITED_ORDER = ["both", "one", "neither", "no verse", "not held", "no citation", "not looked for", ""]\nOURS_ORDER = ["named together", "named near", "both named, never near", "one not in our texts", "not tied", "unchecked", ""]',
     'MALE_AS_SUBJECT = {"son_of", "father_of", "husband_of", "brother_of", "grandson_of", "grandfather_of", "king_of"}\nMARRIAGE = {"wife_of", "husband_of", "married", "queen_of"}\nJOIN_ORDER = ["rule", "verse", "shared", "named"]   # how a step\'s two persons were told apart, the surest first\nSHARED_MIN = 3   # GENEALOGY_HEAL_2026_11_10: the names two entries must give in common, and more than any other homonym\nCITED_ORDER = ["both", "one", "neither", "no verse", "not held", "no citation", "not looked for", ""]\nOURS_ORDER = ["named together", "named near", "both named, never near", "one not in our texts", "not tied", "unchecked", ""]')

edit('scripts/vamsa_view.py', 3, '        if len(got) == 1:\n            return got[0], "verse"\n    return None, ""\n',
     '        if len(got) == 1:\n            return got[0], "verse"\n    # GENEALOGY_HEAL_2026_11_10: the one homonym whose own entry gives the most of the names this row\'s entry gives, at\n    # least SHARED_MIN and more than any other ("shared"): Pandu\'s entry names Kunti, Madri, Yudhisthira, Bhimasena,\n    # Nakula and Sahadeva; of the entries "Arjuna" only the Pandava\'s names them too, Kartavirya\'s none\n    own = rv.split_mark(_hon(r["head"]))[0]\n    ctx = set(names_in.get((src, r["entry_id"]), ())) - {base, ob, own, ""}\n    if len(ctx) >= SHARED_MIN:\n        sc = sorted(((len((set(names_in.get((src, e), ())) - {base}) & ctx), e) for e, _mk in cands), reverse=True)\n        if sc[0][0] >= SHARED_MIN and (len(sc) == 1 or sc[0][0] > sc[1][0]):\n            return sc[0][1], "shared"\n    return None, ""\n')

edit('scripts/vamsa_view.py', 4, '\n\ndef _main_up(g: dict, src: str, e, limit: int = 160) -> list:\n    """From the person up: the father where the index says who is male, else the parent whose line runs longest."""\n    out, seen, node = [e], {e}, (src, e)\n    while len(out) < limit:\n        ps = [p for p in g["par"].get(node, ()) if p[1] not in seen]\n        if not ps:\n            break\n        # HEAL_2026_10_28: the entry last, so a tie (two name-only parents of one name) is the same in every run\n        ps.sort(key=lambda p: (p[1] < 0, g["sex"].get(p) != "m", g["sex"].get(p) == "f", -_strength(g, src, p[1], node[1]),\n                               -g["up"].get(p, 1), _head(g, src, p[1]), p[1]))\n        node = ps[0]\n        seen.add(node[1]); out.append(node[1])',
     '\n\nHEAL_MARK = "GENEALOGY_HEAL_2026_11_10"\n\n\ndef _legal(g: dict, node) -> set:\n    """GENEALOGY_HEAL_2026_11_10: the child\'s fathers (not marked female) married to another of its parents: the\n    mother\'s husband. A son begotten by another (a god, a sage) is counted in his mother\'s husband\'s line."""\n    ps = g["par"].get(node, ())\n    out = set()\n    for p in ps:\n        if g["sex"].get(p) == "f":\n            continue\n        sp = g.get("spouses", {}).get(p, ())\n        if any(q != p and q[1] in sp for q in ps):\n            out.add(p)\n    return out\n\n\ndef _turns_back(g: dict, node, seen: set) -> bool:\n    """GENEALOGY_HEAL_2026_11_10: the person is married to one already on the line (a line that turned back)."""\n    return bool(set(g.get("spouses", {}).get(node, ())) & seen)\n\n\ndef _main_up(g: dict, src: str, e, limit: int = 160) -> list:\n    """From the person up: the father where the index says who is male, else the parent whose line runs longest."""\n    out, seen, node = [e], {e}, (src, e)\n    while len(out) < limit:\n        ps = [p for p in g["par"].get(node, ()) if p[1] not in seen and not _turns_back(g, p, seen)]\n        if not ps:\n            break\n        lg = _legal(g, node)   # GENEALOGY_HEAL_2026_11_10: the mother\'s husband first\n        # HEAL_2026_10_28: the entry last, so a tie (two name-only parents of one name) is the same in every run\n        ps.sort(key=lambda p: (p[1] < 0, bool(lg) and p not in lg, g["sex"].get(p) != "m", g["sex"].get(p) == "f",\n                               -_strength(g, src, p[1], node[1]), -g["up"].get(p, 1), _head(g, src, p[1]), p[1]))\n        node = ps[0]\n        seen.add(node[1]); out.append(node[1])')

edit('scripts/vamsa_view.py', 5, '    out, seen, node = [], {e}, (src, e)\n    while len(out) < limit:\n        cs = [c for c in g["chi"].get(node, ()) if c[1] not in seen]\n        if not cs:\n            break\n        cs.sort(key=lambda c: (c[1] < 0, -g["down"].get(c, 1), g["sex"].get(c) == "f", _head(g, src, c[1]), c[1]))\n        node = cs[0]\n        seen.add(node[1]); out.append(node[1])\n    return out\n',
     '    out, seen, node = [], {e}, (src, e)\n    while len(out) < limit:\n        # GENEALOGY_HEAL_2026_11_10: not down to a child counted in another father\'s line, nor to one married on the line\n        cs = [c for c in g["chi"].get(node, ()) if c[1] not in seen and not _turns_back(g, c, seen)\n              and not (_legal(g, c) and node not in _legal(g, c))]\n        if not cs:\n            break\n        # GENEALOGY_HEAL_2026_11_10: a son before a daughter (a line of descent is counted through the sons, as the\n        # line up is through the father), then the longer line\n        cs.sort(key=lambda c: (c[1] < 0, g["sex"].get(c) == "f", -g["down"].get(c, 1), _head(g, src, c[1]), c[1]))\n        node = cs[0]\n        seen.add(node[1]); out.append(node[1])\n    return out\n\n\n# ---- GENEALOGY_HEAL_2026_11_10: the epithets: an entry the index defines as another person --------------------------\nGLOSS = re.compile(r"\\(\\s*[\\u201c\\"]([^\\u201d\\"]{2,90})[\\u201d\\"]\\s*\\)")\nNUMBER = re.compile(r"^\\s*(pl\\.|dual|du\\.|sg\\.)", re.I)\nPUI_NAME = re.compile(r"^\\s*\\u2014\\s*(?:a |an |another )?(?:name|epithet|title) (?:of|for) ([^\\s,.;:(]+)")\n\n\ndef _targets(s: str) -> list:\n    """[(name, as printed)] of \'Yudhisthira, Bhimasena, and Arjuna\' or \'Rama[1]\': capitalized names only."""\n    s = re.split(r"\\(|\\)|;|:|\\u2014| q\\.v|\\.(?=\\s|$)", s, maxsplit=1)[0]\n    out = []\n    for x in re.split(r",\\s*(?:and\\s+)?|\\s+and\\s+", s):\n        x = x.strip().strip(".,")\n        if not x or not (x[:1].isalpha() and x[:1].isupper()) or x.split()[0].rstrip(".") in ("No", "Do", "The"):\n            continue\n        if len(x.split()) > 3:\n            continue\n        out.append(x)\n    return out\n\n\ndef _alias_parse(src: str, body: str) -> dict:\n    """{gloss, number, targets} from an entry\'s first words; {} when the entry defines no other."""\n    b = (body or "").strip()[:500]\n    if src == "pui":\n        m = PUI_NAME.match(b)\n        return {"gloss": "", "number": "", "targets": [m.group(1)], "do": False} if m else {}\n    if src != "inm":\n        return {}\n    head = re.split(r":|\\u00a7", b, maxsplit=1)[0]\n    num = NUMBER.match(head)\n    gl = GLOSS.search(head)\n    out = {"gloss": gl.group(1).strip() if gl else "", "number": num.group(1).lower().rstrip(".") if num else "",\n           "targets": [], "do": bool(re.match(r"^\\s*(?:(?:pl\\.|dual|du\\.|sg\\.)(?:\\[\\d+\\])?\\s*)?\\(do\\.\\)", head))}\n    m = re.search(r"(?:^|[\\s(])=\\s*(.+)$", head)\n    if m:\n        out["targets"] = _targets(m.group(1))\n    return out if (out["targets"] or out["gloss"] or out["do"]) else {}\n\n\ndef _resolve(g: dict, src: str, name: str) -> tuple:\n    """([entry], how) for a name the index gives: its homonym\'s number; its only entry; the only one with a line; the\n    one with the most kin; else every entry of the name ("not told apart")."""\n    base, mark = rv.split_mark(_hon(name))\n    cands = [e for e, mk in g["m"]["by"].get(src, {}).get(base, []) if not mark or mk == mark]\n    if not cands:\n        return [], ""\n    exact = re.sub(r"\\s*(?:\\[\\d+\\]|\\((?:[ivxlc]+|\\d+)\\))\\s*$", "", _hon(name), flags=re.I).strip().lower()\n    same = [e for e in cands if re.sub(r"\\s*(?:\\[\\d+\\]|\\((?:[ivxlc]+|\\d+)\\))\\s*$", "", _head(g, src, e),\n                                       flags=re.I).strip().lower().lstrip("*") == exact]\n    cands = same or cands   # the folded key makes Krsna and Krsna (Draupadi) one: the letters as printed first\n    if len(cands) == 1:\n        return cands, "the entry\'s number" if mark else "the index\'s only entry of that name"\n    lined = [e for e in cands if (src, e) in g["par"] or (src, e) in g["chi"]]\n    if len(lined) == 1:\n        return lined, "the only entry of that name with a line"\n    pool = lined or cands\n\n    def kin(e):\n        return len(g["par"].get((src, e), ())) + len(g["chi"].get((src, e), ())) + len(g["spouses"].get((src, e), ()))\n    best = max(kin(e) for e in pool)\n    top = [e for e in pool if kin(e) == best]\n    if len(top) == 1 and best > 0:\n        return top, "the entry of that name with the most kin in the index"\n    return sorted(pool), "several entries of that name, not told apart"\n\n\ndef aliases(db: str, kin_db: str) -> dict:\n    """{(source, entry): {gloss, number, same_as: [{entry, head, how}]}}: the entries the index defines as another\n    person, read from context.db\'s shelf_entries (read-only); cached with the graph."""\n    g = _graph(db, kin_db)\n    key = ("aliases",) + rv._stamp(db, kin_db)\n    with _LOCK:\n        got = _CACHE.get("aliases")\n        if got and got[0] == key:\n            return got[1]\n    parsed = {}\n    con = rv.ro(db)\n    try:\n        if rv.has(con, "shelf_entries"):\n            cols = {r[1] for r in con.execute("PRAGMA table_info(shelf_entries)")}\n            for eid, src, name, head, body in con.execute(\n                    "SELECT id, source, %s, head, substr(body, 1, 500) FROM shelf_entries WHERE source IN (\'inm\', \'pui\') "\n                    "ORDER BY source, %s" % ("name" if "name" in cols else "NULL", "lnum, id" if "lnum" in cols else "id")):\n                a = _alias_parse(src, body or "")\n                parsed[(src, eid)] = (name or rv.split_mark(head or "")[0], a)\n    finally:\n        con.close()\n    out, last_gloss, singular = {}, {}, collections.defaultdict(list)\n    for (src, eid), (name, a) in parsed.items():\n        if not a:\n            continue\n        if a.get("do") and not a.get("gloss"):\n            a = dict(a, gloss=last_gloss.get((src, name), ""))\n        if a.get("gloss"):\n            last_gloss[(src, name)] = a["gloss"]\n        same = []\n        for tname in a["targets"]:\n            es, how = _resolve(g, src, tname)\n            for e in es:\n                if e != eid and all(x["entry"] != e for x in same):\n                    same.append({"entry": e, "head": _head(g, src, e), "how": how})\n        if same and a.get("number") in ("", "sg"):\n            singular[(src, name)].extend(x for x in same if x["how"] != "several entries of that name, not told apart")\n        out[(src, eid)] = {"gloss": a.get("gloss", ""), "number": a.get("number", ""), "same_as": same}\n    for (src, eid), v in out.items():   # a plural without its own \'=\': the persons its singular entries name\n        if not v["same_as"] and v["number"] in ("pl", "dual", "du"):\n            name = parsed[(src, eid)][0]\n            seen = set()\n            for x in singular.get((src, name), []):\n                if x["entry"] not in seen:\n                    seen.add(x["entry"])\n                    v["same_as"].append(dict(x, how="the singular entries of this name"))\n    out = {k: v for k, v in out.items() if v["same_as"] or v["gloss"]}\n    with _LOCK:\n        _CACHE["aliases"] = (key, out)\n    return out\n')

edit('scripts/vamsa_view.py', 6, '        if src and s != src:\n            continue\n        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n)]\n        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1]), n[1]))\n        kept = []',
     '        if src and s != src:\n            continue\n        # GENEALOGY_HEAL_2026_11_10: a line of descent is a father\'s line: it starts from a man (or one the index does\n        # not say is a woman) and ends before a daughter, so a list of lines is not read as a dynasty that runs\n        # through mothers (Svarbhanavi, Nahusa\'s mother, had been a step of Soerensen\'s third line)\n        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n) and g["sex"].get(n) != "f"]\n        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1]), n[1]))\n        kept = []')

edit('scripts/vamsa_view.py', 7, '            if g["down"].get(n, 1) < min_len or len(kept) >= top:\n                break\n            chain = [n[1]] + _main_down(g, s, n[1])\n            if len(chain) < min_len:\n                continue',
     '            if g["down"].get(n, 1) < min_len or len(kept) >= top:\n                break\n            chain = [n[1]]\n            for x in _main_down(g, s, n[1]):\n                if g["sex"].get((s, x)) == "f":\n                    break\n                chain.append(x)\n            if len(chain) < min_len:\n                continue')

edit('scripts/vamsa_view.py', 8, '                    want.add((code, f))\n    verses = {"%s|%s" % k: v["verses"][k] for k in want if k in v["verses"]}\n    return {"mark": MARK, "source": src, "index": rv.SHORT[src], "title": rv.SHELF_TITLES[src], "entry": entry,\n            "person": _person(g, src, entry), "line": rungs, "steps": steps, "me": me, "down": gens,\n            "verses": verses, "texts": v["texts"], "checked": v["meta"].get("at", ""),\n            "checked_mark": v["meta"].get("mark", "")}',
     '                    want.add((code, f))\n    verses = {"%s|%s" % k: v["verses"][k] for k in want if k in v["verses"]}\n    try:   # GENEALOGY_HEAL_2026_11_10: the entry\'s own definition ("= Arjuna"), when it gives one\n        al = aliases(db, kin_db).get((src, entry)) or {}\n    except sqlite3.Error:\n        al = {}\n    return {"mark": MARK, "source": src, "index": rv.SHORT[src], "title": rv.SHELF_TITLES[src], "entry": entry,\n            "person": dict(_person(g, src, entry), same_as=al.get("same_as", []), gloss=al.get("gloss", "")),\n            "line": rungs, "steps": steps, "me": me, "down": gens,\n            "verses": verses, "texts": v["texts"], "checked": v["meta"].get("at", ""),\n            "checked_mark": v["meta"].get("mark", "")}')

edit('scripts/index_sync.py', 1, '\nMARK = "INDEX_SITE_2026_10_25"\nSCHEME = "i2"   # B2_SITE_2026_10_28: i2 adds the claims\nHERE = Path(__file__).resolve().parent\nROOT = HERE.parent',
     '\nMARK = "INDEX_SITE_2026_10_25"\nSCHEME = "i2"   # B2_SITE_2026_10_28: i2 adds the claims (GENEALOGY_HEAL_2026_11_10\'s epithets are fields of i2\'s persons)\nHERE = Path(__file__).resolve().parent\nROOT = HERE.parent')

edit('scripts/index_sync.py', 2, '        for s in g["spouses"].get(n, ()):\n            nodes.add((n[0], s))\n    for (src, e) in sorted(nodes):\n        pr = vv._person(g, src, e)',
     '        for s in g["spouses"].get(n, ()):\n            nodes.add((n[0], s))\n    # GENEALOGY_HEAL_2026_11_10: the epithets ("Kaunteya = Arjuna"): on the person\'s row when it has a line, else a row\n    # of its own (no line, no spouse) so that a search for the epithet finds the person; only when the entry names one\n    try:\n        als = vv.aliases(db, kin_db)\n    except sqlite3.Error:\n        als = {}\n    for (src, e), a in als.items():\n        if a.get("same_as") and src in rv.SHELF_TITLES:\n            nodes.add((src, e))\n    for (src, e) in sorted(nodes):\n        pr = vv._person(g, src, e)')

edit('scripts/index_sync.py', 3, '        up = vv._main_up(g, src, e) if has_line else [e]\n        down = vv._main_down(g, src, e) if has_line else []\n        out["persons"].append(finish({\n            "key": "%s:%d" % (src, e), "source": src, "entry": e, "head": pr["head"],',
     '        up = vv._main_up(g, src, e) if has_line else [e]\n        down = vv._main_down(g, src, e) if has_line else []\n        al = als.get((src, e)) or {}\n        out["persons"].append(finish({\n            "key": "%s:%d" % (src, e), "source": src, "entry": e, "head": pr["head"],')

edit('scripts/index_sync.py', 4, '            "has_line": has_line, "up": pr["up"], "down": pr["down"], "parents_n": pr["parents"],\n            "children_n": pr["children"], "canonical": canon(pr["entity"]) if pr["entity"] else None,\n            "spouses": pr["spouses"], "main_up": up[:-1], "main_down": down}))\n\n    # the longest lines, and the verses',
     '            "has_line": has_line, "up": pr["up"], "down": pr["down"], "parents_n": pr["parents"],\n            "children_n": pr["children"], "canonical": canon(pr["entity"]) if pr["entity"] else None,\n            "spouses": pr["spouses"], "main_up": up[:-1], "main_down": down,\n            **({"same_as": al["same_as"]} if al.get("same_as") else {}),\n            **({"gloss": al["gloss"]} if al.get("gloss") else {})}))\n\n    # the longest lines, and the verses')

edit('scripts/index_sync.py', 5, '\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,\n    and the keys the desk no longer has are deleted. The run\'s row (meta) goes last."""\n    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": []}\n    if not all(t in man for t in OPTIONAL):\n        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet\n    for t in TABLES:\n        if t in OPTIONAL and t not in man:',
     '\n\ndef without_aliases(rows: dict) -> dict:\n    """GENEALOGY_HEAL_2026_11_10: the rows as a site without C26 stores them: no epithets on the persons, and no row of\n    an epithet\'s own (no line, no spouse). Their hashes are then the ones such a site keeps, so once C26 is pasted they\n    differ and go again with the epithets."""\n    out = dict(rows)\n    keep = []\n    for r in rows.get("persons", []):\n        if "same_as" not in r and "gloss" not in r:\n            keep.append(r)\n        elif r.get("has_line") or r.get("spouses"):\n            keep.append(finish({k: v for k, v in r.items() if k not in ("same_as", "gloss", "row_hash")}))\n    out["persons"] = keep\n    return out\n\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,\n    and the keys the desk no longer has are deleted. The run\'s row (meta) goes last."""\n    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": [], "features_waiting": []}\n    if not all(t in man for t in OPTIONAL):\n        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet\n    if not (man.get("features") or {}).get("aliases"):\n        rows = without_aliases(rows)   # GENEALOGY_HEAL_2026_11_10: C26 not pasted yet\n        got["features_waiting"].append("aliases")\n    for t in TABLES:\n        if t in OPTIONAL and t not in man:')

edit('scripts/index_sync.py', 6, '    wait = (["the claims wait (%s): paste docs\\\\cloud\\\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "\n             "supabase/functions/corpus-index again" % ", ".join(got["waiting"])] if got.get("waiting") else [])\n    if a.status or not a.apply:\n        todo = sum(x["send"] + x["delete"] for x in got["tables"].values())',
     '    wait = (["the claims wait (%s): paste docs\\\\cloud\\\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "\n             "supabase/functions/corpus-index again" % ", ".join(got["waiting"])] if got.get("waiting") else [])\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "\n                    "paste, then python scripts\\\\index_sync.py --apply")\n    if a.status or not a.apply:\n        todo = sum(x["send"] + x["delete"] for x in got["tables"].values())')


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

