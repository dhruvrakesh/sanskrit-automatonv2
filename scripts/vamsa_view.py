# -*- coding: ascii -*-
"""VAMSA_UI_2026_10_25: what the dashboard's Vamsa page reads (/vamsa, /api/vamsa): the lines of descent of the three
indexes, generation by generation, each step with what it rests on.

  lines    the longest lines of each index (a person without a parent in the index, down through the child whose
           own line is longest), as KIN_LINES_2026_10_24 joins them: only through the index's own entries (one entry
           of the name, or the homonym's number, or the one homonym that names the other), never across indexes;
  find     the index's persons by name (the index's own head words: most of them are not among our names);
  tree     one person: the line up (the father where the index says who is male, else the parent whose own line is
           longest), the line down, the person's children and grandchildren, and for each step (parent, child) the
           index's statements of it: the words, the printed reference, the verse where both names stand
           (data/shelf/vamsa.db, vamsa_check.py), the verses of the Mahabharata, the Harivamsa and the Ramayana that
           name both, our own passages (the verdict of kin_index.py's check) and Raychaudhuri's view.
Nothing is written, no model is called, every store is opened read-only. The relations are the indexes' statements;
a verse where both names stand says where to read, not that it states the relation.

GENEALOGY_HEAL_2026_11_10 (docs/GENEALOGY_2026-11-10.md), asked on 10 Nov: "we cant even get the genealogy of Kaunteya
(Arjun) right". Three mends, each from the index's own statements:
  the line's father    a son begotten by another (Arjuna by Indra, Pandu by Vyasa: the index states both fathers)
                       is drawn up through his mother's husband, as the dynasties count him (Arjuna: Pandu, then the
                       Kurus); the begetter stays beside him as another parent ("line through" draws his line); down,
                       a son before a daughter, and never into another father's line;
  the joins            a name the index gives with several entries is joined to the one entry that gives at least
                       three of the names the stating entry gives, and more than any other ("shared"): Pandu's
                       "father of Arjuna" is the Pandava's entry, not Kartavirya's;
  no line turned back  a line never passes to a person married to one already on it (Soerensen's longest line ran
                       Daksa, Aditi, Visnu, Brahman, Marici, Kasyapa: Kasyapa is Aditi's husband);
  the epithets         an entry the index defines as another ("Kaunteya (the son of Kunti) = Arjuna", Soerensen; "a
                       name of Rama", the Purana Index) is tied to that person's entry (aliases): Soerensen defines
                       5,525 of his 12,647 entries so; a plural ("the sons of Kunti") is tied to the persons its
                       singular entries name.
"""
from __future__ import annotations

import collections, json, re, sqlite3, threading
from pathlib import Path

import relations_view as rv
import vamsa_check as vc

MARK = "VAMSA_UI_2026_10_25"
FEMALE_AS_SUBJECT = {"wife_of", "daughter_of", "mother_of", "queen_of", "sister_of", "granddaughter_of"}
MALE_AS_SUBJECT = {"son_of", "father_of", "husband_of", "brother_of", "grandson_of", "grandfather_of", "king_of"}
MARRIAGE = {"wife_of", "husband_of", "married", "queen_of"}
JOIN_ORDER = ["rule", "verse", "shared", "named"]   # how a step's two persons were told apart, the surest first
SHARED_MIN = 3   # GENEALOGY_HEAL_2026_11_10: the names two entries must give in common, and more than any other homonym
CITED_ORDER = ["both", "one", "neither", "no verse", "not held", "no citation", "not looked for", ""]
OURS_ORDER = ["named together", "named near", "both named, never near", "one not in our texts", "not tied", "unchecked", ""]
_LOCK = threading.Lock()
_CACHE = {}


def _vamsa(store: str) -> dict:
    """{kin_id: checks}, {(text, ref): words}, {text: facts}; cached until vamsa.db changes."""
    key = ("vamsa",) + rv._stamp(store)
    with _LOCK:
        got = _CACHE.get("vamsa")
        if got and got[0] == key:
            return got[1]
    rel, verses, texts, meta = {}, {}, {}, {}
    if Path(store).exists():
        con = rv.ro(store)
        try:
            if rv.has(con, "vamsa_rel"):
                for r in con.execute("SELECT kin_id, cited, cites, best_text, best_ref, subject_form, object_form, mbh, "
                                     "mbh_first, hv, hv_first, ram, ram_first FROM vamsa_rel"):
                    try:
                        cites = json.loads(r[2] or "[]")
                    except ValueError:
                        cites = []
                    rel[r[0]] = {"cited": r[1] or "", "cites": cites, "best_text": r[3] or "", "best_ref": r[4] or "",
                                 "forms": [r[5] or "", r[6] or ""],
                                 "together": {"mbh": [r[7] or 0, r[8] or ""], "hv": [r[9] or 0, r[10] or ""],
                                              "ram": [r[11] or 0, r[12] or ""]}}
            if rv.has(con, "vamsa_verses"):
                for t, ref, w in con.execute("SELECT text, ref, words FROM vamsa_verses"):
                    verses[(t, ref)] = w
            if rv.has(con, "vamsa_texts"):
                for c, title, ed, rights, show in con.execute("SELECT code, title, edition, rights, show FROM vamsa_texts"):
                    texts[c] = {"title": title, "edition": ed, "rights": rights, "show": bool(show)}
            if rv.has(con, "vamsa_meta"):
                meta = dict(con.execute("SELECT k, v FROM vamsa_meta"))
        finally:
            con.close()
    val = {"rel": rel, "verses": verses, "texts": texts, "meta": meta}
    with _LOCK:
        _CACHE["vamsa"] = (key, val)
    return val


HONORIFIC = re.compile(r"^\s*(?:\u015br\u012b|\u015ar\u012b|sri|shri|\u015br\u012bmat|bhagavat)\s+", re.I)


def _hon(name: str) -> str:
    """Sri Rama -> Rama: an honorific the index's prose adds before a name its head word lacks."""
    return HONORIFIC.sub("", name or "")


def _refkeys(r: dict) -> set:
    """The verses a row cites, comparable across entries: the Purana Index's parsed (text, part, chapter, verse); for
    the other two the printed reference itself, when it names a book and a verse number (Soerensen's 'I, 66, 2616')."""
    if r["source"] == "pui":
        out = set()
        for code, where, vs, _p in vc.parse_cites(r["refs"]):
            for v in vs:
                out.add((code,) + tuple(where) + (v,))
        return out
    out = set()
    for x in r["refs"] or []:
        k = re.sub(r"\s+", "", str(x).lower()).rstrip(".")
        if re.search(r"[a-z\u00c0-\u024f\u1e00-\u1eff]", k) and re.search(r"\d{2,}", k):
            out.add(("raw", k))
    return out


def _join(m: dict, r: dict, side: str, other: str, refs_of: dict, names_in: dict):
    """(entry, how) for a name the index's rule left open: without an honorific, by the same rule (the homonym's number,
    the one entry of the name, the one homonym that names the other); else the one homonym of the name whose entry cites
    a verse this row cites ("verse"); else (None, "")."""
    src = r["source"]
    base, mark = rv.split_mark(_hon(r[side]))
    cands = [(e, mk) for e, mk in m["by"].get(src, {}).get(base, []) if not (side == "object" and e == r["entry_id"])]
    if not cands:
        return None, ""
    if mark:
        got = [e for e, mk in cands if mk == mark]
        return (got[0], "rule") if len(got) == 1 else (None, "")
    if len(cands) == 1:
        return cands[0][0], "rule"
    ob = rv.split_mark(_hon(r[other]))[0]
    got = [e for e, _mk in cands if ob and ob in names_in.get((src, e), ())]
    if len(got) == 1:
        return got[0], "rule"
    mine = _refkeys(r)
    if mine:
        got = [e for e, _mk in cands if refs_of.get((src, e), set()) & mine]
        if len(got) == 1:
            return got[0], "verse"
    # GENEALOGY_HEAL_2026_11_10: the one homonym whose own entry gives the most of the names this row's entry gives, at
    # least SHARED_MIN and more than any other ("shared"): Pandu's entry names Kunti, Madri, Yudhisthira, Bhimasena,
    # Nakula and Sahadeva; of the entries "Arjuna" only the Pandava's names them too, Kartavirya's none
    own = rv.split_mark(_hon(r["head"]))[0]
    ctx = set(names_in.get((src, r["entry_id"]), ())) - {base, ob, own, ""}
    if len(ctx) >= SHARED_MIN:
        sc = sorted(((len((set(names_in.get((src, e), ())) - {base}) & ctx), e) for e, _mk in cands), reverse=True)
        if sc[0][0] >= SHARED_MIN and (len(sc) == 1 or sc[0][0] > sc[1][0]):
            return sc[0][1], "shared"
    return None, ""


def _graph(db: str, kin_db: str) -> dict:
    """The parent-child steps of each index with the rows that state them, the persons' sex where the index says it,
    their marriages, how deep each one's line runs up and down; cached with relations_view's model."""
    m = rv._model(db, kin_db)
    key = ("graph",) + tuple(rv._CACHE.get("model", ((),))[0])
    with _LOCK:
        got = _CACHE.get("graph")
        if got and got[0] == key:
            return got[1]
    edges, sex, spouses = collections.defaultdict(list), {}, collections.defaultdict(set)
    rows_all, seen_rows = [], set()
    for rows in m["own"].values():
        for r in rows:
            if r["kin_id"] not in seen_rows:
                seen_rows.add(r["kin_id"])
                rows_all.append(r)
    rows_all.sort(key=lambda r: r["kin_id"])
    refs_of, names_in = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows_all:
        refs_of[(r["source"], r["entry_id"])] |= _refkeys(r)
        names_in[(r["source"], r["entry_id"])].update((rv.split_mark(_hon(r["subject"]))[0],
                                                       rv.split_mark(_hon(r["object"]))[0]))
    shown = dict(m["shown"])
    joined = collections.Counter()
    out_rows = []
    for r in rows_all:
        r2 = dict(r, join_subject="rule" if r.get("subject_entry") is not None else "",
                  join_object="rule" if r.get("object_entry") is not None else "")
        if r["relation"] in rv.PARENT or r["relation"] in MARRIAGE:
            for side, other in (("subject", "object"), ("object", "subject")):
                if r2.get(side + "_entry") is not None:
                    continue
                e, how = _join(m, r2, side, other, refs_of, names_in)
                if e is None:   # a person the index names but whose entry cannot be told apart: a leaf of this row
                    e, how = -(r["kin_id"] * 2 + (0 if side == "subject" else 1)), "named"
                    shown[(r["source"], e)] = r[side]
                r2[side + "_entry"], r2["join_" + side] = e, how
                joined[how] += 1
        out_rows.append(r2)
    for r in out_rows:
        src, s, o, rel = r["source"], r.get("subject_entry"), r.get("object_entry"), r["relation"]
        if s is not None:
            if rel in FEMALE_AS_SUBJECT:
                sex.setdefault((src, s), "f")
            elif rel in MALE_AS_SUBJECT:
                sex.setdefault((src, s), "m")
        if o is not None:
            if rel in ("husband_of",):
                sex.setdefault((src, o), "f")
            elif rel in ("wife_of", "queen_of"):
                sex.setdefault((src, o), "m")
        if rel in rv.PARENT and s is not None and o is not None and s != o:
            p, c = (o, s) if rv.PARENT[rel] == "o" else (s, o)
            edges[(src, p, c)].append(r)
            if rel == "father_of":
                sex.setdefault((src, s), "m")
            elif rel == "mother_of":
                sex[(src, s)] = "f"
        if rel in MARRIAGE and s is not None and o is not None and s != o:
            spouses[(src, s)].add(o)
            spouses[(src, o)].add(s)
    up_depth, down_depth = {}, {}

    def depth(node, table, nxt):
        # iterative longest path with a guard against the index's few loops
        if node in table:
            return table[node]
        stack, on = [(node, iter(sorted(nxt.get(node, ()))))], {node}
        best = {node: 1}
        while stack:
            cur, it = stack[-1]
            ch = next(it, None)
            if ch is None:
                stack.pop(); on.discard(cur)
                table[cur] = best.get(cur, 1)
                if stack:
                    par = stack[-1][0]
                    best[par] = max(best.get(par, 1), table[cur] + 1)
                continue
            if ch in table:
                best[cur] = max(best.get(cur, 1), table[ch] + 1)
            elif ch not in on and len(stack) < 400:
                on.add(ch); best[ch] = 1
                stack.append((ch, iter(sorted(nxt.get(ch, ())))))
        return table[node]
    par = {(src, c): set() for (src, _p, c) in edges}
    chi = {(src, p): set() for (src, p, _c) in edges}
    for (src, p, c) in edges:
        par[(src, c)].add((src, p))
        chi[(src, p)].add((src, c))
    for n in list(par) + list(chi):
        depth(n, up_depth, par)
        depth(n, down_depth, chi)
    entity_of = {}
    for ent, entries in m["links"].items():
        for e in entries:
            for src in rv.SHELF_TITLES:
                if (src, e) in m["shown"]:
                    entity_of.setdefault((src, e), ent)
    val = {"m": m, "edges": edges, "sex": sex, "spouses": spouses, "par": par, "chi": chi, "up": up_depth,
           "down": down_depth, "entity_of": entity_of, "shown": shown, "joined": dict(joined)}
    with _LOCK:
        _CACHE["graph"] = (key, val)
    return val


def _head(g: dict, src: str, e) -> str:
    return g["shown"].get((src, e), str(e))


HEAL_MARK = "GENEALOGY_HEAL_2026_11_10"


def _legal(g: dict, node) -> set:
    """GENEALOGY_HEAL_2026_11_10: the child's fathers (not marked female) married to another of its parents: the
    mother's husband. A son begotten by another (a god, a sage) is counted in his mother's husband's line."""
    ps = g["par"].get(node, ())
    out = set()
    for p in ps:
        if g["sex"].get(p) == "f":
            continue
        sp = g.get("spouses", {}).get(p, ())
        if any(q != p and q[1] in sp for q in ps):
            out.add(p)
    return out


def _turns_back(g: dict, node, seen: set) -> bool:
    """GENEALOGY_HEAL_2026_11_10: the person is married to one already on the line (a line that turned back)."""
    return bool(set(g.get("spouses", {}).get(node, ())) & seen)


def _main_up(g: dict, src: str, e, limit: int = 160) -> list:
    """From the person up: the father where the index says who is male, else the parent whose line runs longest."""
    out, seen, node = [e], {e}, (src, e)
    while len(out) < limit:
        ps = [p for p in g["par"].get(node, ()) if p[1] not in seen and not _turns_back(g, p, seen)]
        if not ps:
            break
        lg = _legal(g, node)   # GENEALOGY_HEAL_2026_11_10: the mother's husband first
        # HEAL_2026_10_28: the entry last, so a tie (two name-only parents of one name) is the same in every run
        ps.sort(key=lambda p: (p[1] < 0, bool(lg) and p not in lg, g["sex"].get(p) != "m", g["sex"].get(p) == "f",
                               -_strength(g, src, p[1], node[1]), -g["up"].get(p, 1), _head(g, src, p[1]), p[1]))
        node = ps[0]
        seen.add(node[1]); out.append(node[1])
    return list(reversed(out))


def _strength(g: dict, src: str, p, c) -> int:
    """How surely the index states the step: 2 when both entries state it, 1 when one does."""
    rows = g["edges"].get((src, p, c), [])
    return 2 if {p, c} <= {r["entry_id"] for r in rows} else 1 if rows else 0


def _main_down(g: dict, src: str, e, limit: int = 160) -> list:
    out, seen, node = [], {e}, (src, e)
    while len(out) < limit:
        # GENEALOGY_HEAL_2026_11_10: not down to a child counted in another father's line, nor to one married on the line
        cs = [c for c in g["chi"].get(node, ()) if c[1] not in seen and not _turns_back(g, c, seen)
              and not (_legal(g, c) and node not in _legal(g, c))]
        if not cs:
            break
        # GENEALOGY_HEAL_2026_11_10: a son before a daughter (a line of descent is counted through the sons, as the
        # line up is through the father), then the longer line
        cs.sort(key=lambda c: (c[1] < 0, g["sex"].get(c) == "f", -g["down"].get(c, 1), _head(g, src, c[1]), c[1]))
        node = cs[0]
        seen.add(node[1]); out.append(node[1])
    return out


# ---- GENEALOGY_HEAL_2026_11_10: the epithets: an entry the index defines as another person --------------------------
GLOSS = re.compile(r"\(\s*[\u201c\"]([^\u201d\"]{2,90})[\u201d\"]\s*\)")
NUMBER = re.compile(r"^\s*(pl\.|dual|du\.|sg\.)", re.I)
PUI_NAME = re.compile(r"^\s*\u2014\s*(?:a |an |another )?(?:name|epithet|title) (?:of|for) ([^\s,.;:(]+)")


def _targets(s: str) -> list:
    """[(name, as printed)] of 'Yudhisthira, Bhimasena, and Arjuna' or 'Rama[1]': capitalized names only."""
    s = re.split(r"\(|\)|;|:|\u2014| q\.v|\.(?=\s|$)", s, maxsplit=1)[0]
    out = []
    for x in re.split(r",\s*(?:and\s+)?|\s+and\s+", s):
        x = x.strip().strip(".,")
        if not x or not (x[:1].isalpha() and x[:1].isupper()) or x.split()[0].rstrip(".") in ("No", "Do", "The"):
            continue
        if len(x.split()) > 3:
            continue
        out.append(x)
    return out


def _alias_parse(src: str, body: str) -> dict:
    """{gloss, number, targets} from an entry's first words; {} when the entry defines no other."""
    b = (body or "").strip()[:500]
    if src == "pui":
        m = PUI_NAME.match(b)
        return {"gloss": "", "number": "", "targets": [m.group(1)], "do": False} if m else {}
    if src != "inm":
        return {}
    head = re.split(r":|\u00a7", b, maxsplit=1)[0]
    num = NUMBER.match(head)
    gl = GLOSS.search(head)
    out = {"gloss": gl.group(1).strip() if gl else "", "number": num.group(1).lower().rstrip(".") if num else "",
           "targets": [], "do": bool(re.match(r"^\s*(?:(?:pl\.|dual|du\.|sg\.)(?:\[\d+\])?\s*)?\(do\.\)", head))}
    m = re.search(r"(?:^|[\s(])=\s*(.+)$", head)
    if m:
        out["targets"] = _targets(m.group(1))
    return out if (out["targets"] or out["gloss"] or out["do"]) else {}


def _resolve(g: dict, src: str, name: str) -> tuple:
    """([entry], how) for a name the index gives: its homonym's number; its only entry; the only one with a line; the
    one with the most kin; else every entry of the name ("not told apart")."""
    base, mark = rv.split_mark(_hon(name))
    cands = [e for e, mk in g["m"]["by"].get(src, {}).get(base, []) if not mark or mk == mark]
    if not cands:
        return [], ""
    exact = re.sub(r"\s*(?:\[\d+\]|\((?:[ivxlc]+|\d+)\))\s*$", "", _hon(name), flags=re.I).strip().lower()
    same = [e for e in cands if re.sub(r"\s*(?:\[\d+\]|\((?:[ivxlc]+|\d+)\))\s*$", "", _head(g, src, e),
                                       flags=re.I).strip().lower().lstrip("*") == exact]
    cands = same or cands   # the folded key makes Krsna and Krsna (Draupadi) one: the letters as printed first
    if len(cands) == 1:
        return cands, "the entry's number" if mark else "the index's only entry of that name"
    lined = [e for e in cands if (src, e) in g["par"] or (src, e) in g["chi"]]
    if len(lined) == 1:
        return lined, "the only entry of that name with a line"
    pool = lined or cands

    def kin(e):
        return len(g["par"].get((src, e), ())) + len(g["chi"].get((src, e), ())) + len(g["spouses"].get((src, e), ()))
    best = max(kin(e) for e in pool)
    top = [e for e in pool if kin(e) == best]
    if len(top) == 1 and best > 0:
        return top, "the entry of that name with the most kin in the index"
    return sorted(pool), "several entries of that name, not told apart"


def aliases(db: str, kin_db: str) -> dict:
    """{(source, entry): {gloss, number, same_as: [{entry, head, how}]}}: the entries the index defines as another
    person, read from context.db's shelf_entries (read-only); cached with the graph."""
    g = _graph(db, kin_db)
    key = ("aliases",) + rv._stamp(db, kin_db)
    with _LOCK:
        got = _CACHE.get("aliases")
        if got and got[0] == key:
            return got[1]
    parsed = {}
    con = rv.ro(db)
    try:
        if rv.has(con, "shelf_entries"):
            cols = {r[1] for r in con.execute("PRAGMA table_info(shelf_entries)")}
            for eid, src, name, head, body in con.execute(
                    "SELECT id, source, %s, head, substr(body, 1, 500) FROM shelf_entries WHERE source IN ('inm', 'pui') "
                    "ORDER BY source, %s" % ("name" if "name" in cols else "NULL", "lnum, id" if "lnum" in cols else "id")):
                a = _alias_parse(src, body or "")
                parsed[(src, eid)] = (name or rv.split_mark(head or "")[0], a)
    finally:
        con.close()
    out, last_gloss, singular = {}, {}, collections.defaultdict(list)
    for (src, eid), (name, a) in parsed.items():
        if not a:
            continue
        if a.get("do") and not a.get("gloss"):
            a = dict(a, gloss=last_gloss.get((src, name), ""))
        if a.get("gloss"):
            last_gloss[(src, name)] = a["gloss"]
        same = []
        for tname in a["targets"]:
            es, how = _resolve(g, src, tname)
            for e in es:
                if e != eid and all(x["entry"] != e for x in same):
                    same.append({"entry": e, "head": _head(g, src, e), "how": how})
        if same and a.get("number") in ("", "sg"):
            singular[(src, name)].extend(x for x in same if x["how"] != "several entries of that name, not told apart")
        out[(src, eid)] = {"gloss": a.get("gloss", ""), "number": a.get("number", ""), "same_as": same}
    for (src, eid), v in out.items():   # a plural without its own '=': the persons its singular entries name
        if not v["same_as"] and v["number"] in ("pl", "dual", "du"):
            name = parsed[(src, eid)][0]
            seen = set()
            for x in singular.get((src, name), []):
                if x["entry"] not in seen:
                    seen.add(x["entry"])
                    v["same_as"].append(dict(x, how="the singular entries of this name"))
    out = {k: v for k, v in out.items() if v["same_as"] or v["gloss"]}
    with _LOCK:
        _CACHE["aliases"] = (key, out)
    return out


def _best(values, order):
    vals = [v for v in values if v in order]
    return min(vals, key=order.index) if vals else ""


def _evidence(g: dict, v: dict, src: str, p, c) -> dict:
    rows = g["edges"].get((src, p, c), [])
    items = []
    for r in rows:
        x = v["rel"].get(r["kin_id"], {})
        items.append({"kin_id": r["kin_id"], "stated_in": r["head"], "relation": r["relation"],
                      "label": r["relation"].replace("_", " "), "subject": r["subject"], "object": r["object"],
                      "words": r["words"], "refs": r["refs"], "ours": r["verdict"], "passages": r["passages"],
                      "texts": r["texts"], "places": r["places"], "raychaudhuri": r["raychaudhuri"],
                      "raychaudhuri_note": r["raychaudhuri_note"], "cited": x.get("cited", ""),
                      "cites": x.get("cites", [])[:6], "best_text": x.get("best_text", ""),
                      "best_ref": x.get("best_ref", ""), "forms": x.get("forms", ["", ""]),
                      "together": x.get("together", {}),
                      "join": [r.get("join_subject", ""), r.get("join_object", "")]})
    stated = {r["entry_id"] for r in rows}
    epic = {}
    for code in ("mbh", "hv", "ram"):
        best = max((it["together"].get(code, [0, ""]) for it in items), key=lambda t: t[0], default=[0, ""])
        epic[code] = best
    joins = [max(it["join"], key=lambda j: JOIN_ORDER.index(j) if j in JOIN_ORDER else 9) for it in items]
    return {"parent": p, "child": c, "items": items,
            "joined": min(joins, key=lambda j: JOIN_ORDER.index(j) if j in JOIN_ORDER else 9) if joins else "",
            "both_entries": {p, c} <= stated,
            "cited": _best([it["cited"] for it in items], CITED_ORDER),
            "ours": _best([it["ours"] for it in items], OURS_ORDER),
            "scholar": _best([it["raychaudhuri"] for it in items], ["agrees", "differs", "reversed"]),
            "epic": epic}


def _person(g: dict, src: str, e) -> dict:
    node = (src, e)
    return {"entry": e, "head": _head(g, src, e), "sex": g["sex"].get(node, ""), "named_only": e < 0,
            "parents": len(g["par"].get(node, ())), "children": len(g["chi"].get(node, ())),
            "up": g["up"].get(node, 1), "down": g["down"].get(node, 1),
            "entity": g["entity_of"].get(node),
            "spouses": [{"entry": s, "head": _head(g, src, s)} for s in sorted(g["spouses"].get(node, ()),
                                                                              key=lambda z: (_head(g, src, z), z))][:6]}


def lines(db: str, kin_db: str, src: str = "", top: int = 30, min_len: int = 6) -> dict:
    """The longest lines of each index (or of one): each from a person without a parent in it, down the child whose
    own line is longest; a line that shares three quarters of its persons with a longer one is left out."""
    g = _graph(db, kin_db)
    out = {}
    for s in rv.SHELF_TITLES:
        if src and s != src:
            continue
        # GENEALOGY_HEAL_2026_11_10: a line of descent is a father's line: it starts from a man (or one the index does
        # not say is a woman) and ends before a daughter, so a list of lines is not read as a dynasty that runs
        # through mothers (Svarbhanavi, Nahusa's mother, had been a step of Soerensen's third line)
        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n) and g["sex"].get(n) != "f"]
        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1]), n[1]))
        kept = []
        for n in roots:
            if g["down"].get(n, 1) < min_len or len(kept) >= top:
                break
            chain = [n[1]]
            for x in _main_down(g, s, n[1]):
                if g["sex"].get((s, x)) == "f":
                    break
                chain.append(x)
            if len(chain) < min_len:
                continue
            sc = set(chain)
            if any(len(sc & set(k["entries"])) >= 0.75 * len(sc) for k in kept):
                continue
            steps = [(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]
            both = sum(1 for p, c in steps if {p, c} <= {r["entry_id"] for r in g["edges"].get((s, p, c), [])})
            kept.append({"source": s, "index": rv.SHORT[s], "entries": chain,
                         "heads": [_head(g, s, x) for x in chain], "length": len(chain), "both_steps": both})
        out[s] = kept
    return {"mark": MARK, "lines": out, "titles": rv.SHELF_TITLES}


def find(db: str, kin_db: str, q: str, src: str = "", limit: int = 20) -> list:
    """The index's persons whose head word is q, or begins with it: the exact first, then by how long their lines
    run; only persons that have a parent or a child in the index."""
    g = _graph(db, kin_db)
    f = rv.fold(q)
    if not f:
        return []
    hits = []
    for (s, e), head in g["m"]["shown"].items():
        if src and s != src:
            continue
        node = (s, e)
        if node not in g["par"] and node not in g["chi"]:
            continue
        base, _mark = rv.split_mark(head)
        if base == f or base.startswith(f):
            hits.append((base != f, -(g["up"].get(node, 1) + g["down"].get(node, 1)), head, s, e))
    hits.sort()
    return [dict(_person(g, s, e), source=s, index=rv.SHORT[s], exact=not ne) for ne, _d, _h, s, e in hits[:limit]]


def tree(db: str, kin_db: str, store: str, src: str, entry: int, path=None, down: int = 3, via=None) -> dict:
    """One person of one index, with the line up and down and each step's evidence (see the module's note). path, when
    given, is a line chosen from lines(): its steps are kept if each is a step of the index; via, a parent of the person:
    the line up runs through that parent (a son by niyoga has two fathers: the index states both)."""
    g = _graph(db, kin_db)
    v = _vamsa(store)
    if src not in rv.SHELF_TITLES or (src, entry) not in g["shown"]:
        return {"error": "no such person in the index", "mark": MARK}
    line = None
    if path:
        ok = all((src, path[i], path[i + 1]) in g["edges"] for i in range(len(path) - 1))
        if ok and entry in path:
            line = list(path)
    if line is None and via is not None and (src, via, entry) in g["edges"]:
        up = _main_up(g, src, via)
        if entry not in up:
            line = up + [entry] + _main_down(g, src, entry)
    if line is None:
        line = _main_up(g, src, entry) + _main_down(g, src, entry)
    me = line.index(entry)
    steps = [_evidence(g, v, src, line[i], line[i + 1]) for i in range(len(line) - 1)]
    rungs = []
    for i, e in enumerate(line):
        node = (src, e)
        par = line[i - 1] if i else None
        sibs = sorted((c[1] for c in g["chi"].get((src, par), ()) if c[1] != e), key=lambda z: (_head(g, src, z), z)) \
            if par is not None else []
        others = sorted((p[1] for p in g["par"].get(node, ()) if p[1] != par), key=lambda z: (_head(g, src, z), z))
        rungs.append(dict(_person(g, src, e), generation=i - me,
                          siblings=[{"entry": s, "head": _head(g, src, s)} for s in sibs[:16]],
                          siblings_n=len(sibs),
                          other_parents=[dict(_person(g, src, p), evidence=_evidence(g, v, src, p, e))
                                         for p in others[:4]]))
    gens, level, seen = [], [entry], set(line[:me + 1])
    on_line = set(line[me + 1:])
    for _ in range(max(0, min(int(down), 6))):
        nxt = []
        for p in level:
            for c in sorted((c[1] for c in g["chi"].get((src, p), ())), key=lambda z: (_head(g, src, z), z)):
                if c in seen:
                    continue
                seen.add(c)
                nxt.append(dict(_person(g, src, c), of=p, on_line=c in on_line,
                                evidence=_evidence(g, v, src, p, c)))
        if not nxt:
            break
        gens.append(nxt[:24])
        level = [n["entry"] for n in nxt[:24]]
    want = set()
    for st in steps + [op["evidence"] for r in rungs for op in r["other_parents"]] + \
            [n["evidence"] for gen in gens for n in gen]:
        for it in st["items"]:
            for d in it["cites"]:
                if d.get("verdict") in ("both", "one"):
                    for ref in (d.get("at") or [d.get("ref")])[:3]:
                        want.add((d["text"], ref))
            for code in ("hv", "ram"):
                f = (it["together"].get(code) or [0, ""])[1]
                if f:
                    want.add((code, f))
    verses = {"%s|%s" % k: v["verses"][k] for k in want if k in v["verses"]}
    try:   # GENEALOGY_HEAL_2026_11_10: the entry's own definition ("= Arjuna"), when it gives one
        al = aliases(db, kin_db).get((src, entry)) or {}
    except sqlite3.Error:
        al = {}
    return {"mark": MARK, "source": src, "index": rv.SHORT[src], "title": rv.SHELF_TITLES[src], "entry": entry,
            "person": dict(_person(g, src, entry), same_as=al.get("same_as", []), gloss=al.get("gloss", "")),
            "line": rungs, "steps": steps, "me": me, "down": gens,
            "verses": verses, "texts": v["texts"], "checked": v["meta"].get("at", ""),
            "checked_mark": v["meta"].get("mark", "")}
