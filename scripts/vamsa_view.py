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
JOIN_ORDER = ["rule", "verse", "named"]   # how a step's two persons were told apart, the surest first
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


def _main_up(g: dict, src: str, e, limit: int = 160) -> list:
    """From the person up: the father where the index says who is male, else the parent whose line runs longest."""
    out, seen, node = [e], {e}, (src, e)
    while len(out) < limit:
        ps = [p for p in g["par"].get(node, ()) if p[1] not in seen]
        if not ps:
            break
        # HEAL_2026_10_28: the entry last, so a tie (two name-only parents of one name) is the same in every run
        ps.sort(key=lambda p: (p[1] < 0, g["sex"].get(p) != "m", g["sex"].get(p) == "f", -_strength(g, src, p[1], node[1]),
                               -g["up"].get(p, 1), _head(g, src, p[1]), p[1]))
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
        cs = [c for c in g["chi"].get(node, ()) if c[1] not in seen]
        if not cs:
            break
        cs.sort(key=lambda c: (c[1] < 0, -g["down"].get(c, 1), g["sex"].get(c) == "f", _head(g, src, c[1]), c[1]))
        node = cs[0]
        seen.add(node[1]); out.append(node[1])
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
        roots = [n for n in g["chi"] if n[0] == s and not g["par"].get(n)]
        roots.sort(key=lambda n: (-g["down"].get(n, 1), _head(g, s, n[1]), n[1]))
        kept = []
        for n in roots:
            if g["down"].get(n, 1) < min_len or len(kept) >= top:
                break
            chain = [n[1]] + _main_down(g, s, n[1])
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
    return {"mark": MARK, "source": src, "index": rv.SHORT[src], "title": rv.SHELF_TITLES[src], "entry": entry,
            "person": _person(g, src, entry), "line": rungs, "steps": steps, "me": me, "down": gens,
            "verses": verses, "texts": v["texts"], "checked": v["meta"].get("at", ""),
            "checked_mark": v["meta"].get("mark", "")}
