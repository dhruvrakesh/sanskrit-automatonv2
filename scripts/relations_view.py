# -*- coding: ascii -*-
"""RELATIONS_UI_2026_10_24: what the dashboard's Relations page reads (/relations, /api/relations).

For one of our names it gathers, read-only:
  * whom our own texts name it with: the table entity_links (together: in one passage; near: within a few), with the
    passages where they first meet;
  * what the three indexes state of each PERSON of that name (data/shelf/kin.db: the relations kept after the checks,
    the words they rest on, the reference, the verdict against our verses, Raychaudhuri's view). The indexes number
    the persons who share a name (Janamejaya (I), Janamejaya (II)); each is shown apart, by its own entry;
  * the line of descent through each such person, joined only through the index's own entries (the rule of
    KIN_LINES_2026_10_24: one entry of the name, or the homonym's number, or the one homonym that names the other);
  * Raychaudhuri's claims about the name (data/shelf/claims.db, the latest read of each page).
Nothing is written, no model is called, data/context.db is opened read-only. The relations are the indexes' own
statements, checked only as far as the page says; they are evidence to weigh, not facts settled.
"""
from __future__ import annotations

import collections, json, re, sqlite3, threading, unicodedata
from pathlib import Path

MARK = "RELATIONS_UI_2026_10_24"
SHELF_TITLES = {"pui": "Purana Index (V. R. R. Dikshitar, 1951-55)",
                "vei": "Vedic Index of Names and Subjects (Macdonell and Keith, 1912)",
                "inm": "An Index to the Names in the Mahabharata (S. Soerensen, 1904)"}
SHORT = {"pui": "Purana Index", "vei": "Vedic Index", "inm": "Soerensen"}
GROUPS = {"son_of": "family", "daughter_of": "family", "father_of": "family", "mother_of": "family",
          "grandson_of": "family", "granddaughter_of": "family", "grandfather_of": "family",
          "descendant_of": "family", "ancestor_of": "family",
          "wife_of": "marriage", "husband_of": "marriage", "married": "marriage",
          "brother_of": "siblings", "sister_of": "siblings",
          "pupil_of": "learning", "teacher_of": "learning", "priest_of": "learning", "patron_of": "learning",
          "king_of": "rule", "queen_of": "rule", "successor_of": "rule", "predecessor_of": "rule",
          "contemporary_of": "time"}
PARENT = {"son_of": "o", "daughter_of": "o", "father_of": "s", "mother_of": "s"}   # which side is the elder
CLAIMS_SOURCE = "Raychaudhuri, Political History of Ancient India (1923)"
_LOCK = threading.Lock()
_CACHE = {}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman(t: str) -> int:
    n, prev = 0, 0
    for ch in reversed(t.lower()):
        v = _ROMAN.get(ch, 0)
        n, prev = (n - v, prev) if v < prev else (n + v, v)
    return n


def split_mark(name: str) -> tuple:
    """(the folded name, the homonym's number or 0), as kin_index.split_mark (KIN_LINES_2026_10_24)."""
    s, mark = (name or "").strip(), 0
    m = re.match(r"^(\d{1,2})\.\s+(.+)$", s)
    if m:
        mark, s = int(m.group(1)), m.group(2)
    else:
        m = re.search(r"\s*(?:\((\d{1,2}|[ivxlc]{1,6})\)|\[(\d{1,2})\])\s*$", s, flags=re.I)
        if m:
            g = m.group(1) or m.group(2)
            mark, s = (int(g) if g.isdigit() else _roman(g)), s[:m.start()]
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    return fold(s), mark


def ro(path) -> sqlite3.Connection:
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)


def has(con, table: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
                            (table,)).fetchone())


def _stamp(*paths) -> tuple:
    out = []
    for p in paths:
        try:
            st = Path(p).stat()
            out.append((str(p), st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((str(p), 0, 0))
    return tuple(out)


# ---- the names -----------------------------------------------------------------------------------------------
def _names(db: str) -> dict:
    """{id: (canonical, kind, mentions)}, {folded name: [ids]}, {folded variant: [ids]}: cached until context.db's
    size changes. A variant is any form our texts use for the name, epithets among them (Janamejaya's include
    Bharata and Pariksita, as the frame of the Mahabharata addresses him), so it finds a name but never ties an
    index's person."""
    key = ("names",) + _stamp(db)
    with _LOCK:
        got = _CACHE.get("names")
        if got and got[0] == key:
            return got[1]
    con = ro(db)
    try:
        n = dict(con.execute("SELECT entity_id, COUNT(*) FROM entity_mentions GROUP BY entity_id"))
        ents = {i: (c, k or "", n.get(i, 0)) for i, c, k in con.execute("SELECT id, canonical, kind FROM entities")}
        idx, var = collections.defaultdict(set), collections.defaultdict(set)
        for i, (c, _k, _n) in ents.items():
            idx[fold(c)].add(i)
        if has(con, "entity_variants"):
            for i, v in con.execute("SELECT entity_id, variant FROM entity_variants"):
                if i in ents and v:
                    var[fold(v)].add(i)
    finally:
        con.close()
    val = {"ents": ents, "idx": {k: sorted(v) for k, v in idx.items()}, "var": {k: sorted(v) for k, v in var.items()}}
    with _LOCK:
        _CACHE["names"] = (key, val)
    return val


def find(db: str, q: str, limit: int = 12) -> list:
    """Our names that match q: the name itself, then names one of whose forms in our texts it is, then names that
    begin with it; most often named first, persons before others. Each says how it matched (name, variant, begins)."""
    nm = _names(db)
    f = fold(q)
    if not f:
        top = sorted(nm["ents"].items(), key=lambda kv: (-kv[1][2], kv[1][0]))[:limit]
        return [{"id": i, "name": c, "kind": k, "mentions": n, "via": "most named"} for i, (c, k, n) in top]
    exact = set(nm["idx"].get(f, ()))
    var = set(nm["var"].get(f, ())) - exact
    pre = set()
    if len(f) >= 2:
        for k, ids in nm["idx"].items():
            if k.startswith(f):
                pre.update(ids)
                if len(pre) > 400:
                    break
    pre -= exact | var

    def rank(i):
        e = nm["ents"][i]
        return (0 if i in exact else 1 if i in var else 2, e[1] != "person", -e[2], e[0])
    order = sorted(exact | var | pre, key=rank)
    return [{"id": i, "name": nm["ents"][i][0], "kind": nm["ents"][i][1], "mentions": nm["ents"][i][2],
             "exact": i in exact, "via": "name" if i in exact else "variant" if i in var else "begins"}
            for i in order[:limit]]


# ---- the indexes ---------------------------------------------------------------------------------------------
def _model(db: str, kin_db: str) -> dict:
    """Every kept relation of the three indexes with its tie and verdict, and the index's entries by name: cached
    until kin.db changes (the checks rewrite it; the hourly task's step d runs kin_index.py --check)."""
    key = ("model",) + _stamp(kin_db)
    with _LOCK:
        got = _CACHE.get("model")
        if got and got[0] == key:
            return got[1]
    by = {s: collections.defaultdict(list) for s in SHELF_TITLES}
    shown, links = {}, collections.defaultdict(set)
    con = ro(db)
    try:
        if has(con, "shelf_entries"):
            q = "SELECT id, source, head FROM shelf_entries WHERE source IN (%s)" % ",".join("?" * len(SHELF_TITLES))
            for eid, src, head in con.execute(q, tuple(SHELF_TITLES)):
                base, mark = split_mark(head)
                if base:
                    by[src][base].append((eid, mark))
                    shown[(src, eid)] = head
        if has(con, "shelf_links"):
            cols = {r[1] for r in con.execute("PRAGMA table_info(shelf_links)")}
            q = "SELECT entry_id, entity_id FROM shelf_links" + (" WHERE how = 'exact'" if "how" in cols else "")
            for e, x in con.execute(q):
                links[x].add(e)
    finally:
        con.close()
    rows = []
    if Path(kin_db).exists():
        k = ro(kin_db)
        try:
            if has(k, "kin") and has(k, "kin_done"):
                tie = has(k, "kin_ties")
                sql = ("SELECT k.id, k.source, k.entry_id, k.head, k.subject, k.relation, k.object, k.words, k.refs, "
                       "k.words_check, k.direction, %s FROM kin k JOIN kin_done d ON d.entry_id = k.entry_id AND "
                       "d.read_id = k.read_id %s" % (
                           "t.subject_entity, t.object_entity, t.verdict, t.passages, t.texts, t.places, t.scholar, "
                           "t.scholar_note" if tie else "NULL, NULL, '', 0, 0, '[]', '', ''",
                           "LEFT JOIN kin_ties t ON t.kin_id = k.id" if tie else ""))
                for r in k.execute(sql):
                    if r[9] not in ("exact", "close") or r[10] == "disagrees":
                        continue
                    try:
                        refs = json.loads(r[8] or "[]")
                    except ValueError:
                        refs = []
                    try:
                        places = json.loads(r[16] or "[]")
                    except ValueError:
                        places = []
                    rows.append({"kin_id": r[0], "source": r[1], "entry_id": r[2], "head": r[3], "subject": r[4],
                                 "relation": r[5], "object": r[6], "words": r[7] or "", "refs": refs,
                                 "subject_entity": r[11], "object_entity": r[12], "verdict": r[13] or "unchecked",
                                 "passages": r[14] or 0, "texts": r[15] or 0, "places": places[:3],
                                 "raychaudhuri": r[17] or "", "raychaudhuri_note": r[18] or ""})
        finally:
            k.close()
    names_in = collections.defaultdict(set)
    for r in rows:
        names_in[(r["source"], r["entry_id"])].update((split_mark(r["subject"])[0], split_mark(r["object"])[0]))

    def resolve(src: str, name: str, other: str):
        base, mark = split_mark(name)
        cands = by.get(src, {}).get(base, [])
        if mark:
            got = [e for e, m in cands if m == mark]
            return got[0] if len(got) == 1 else None
        if len(cands) == 1:
            return cands[0][0]
        got = [e for e, _m in cands if other and other in names_in.get((src, e), ())]
        return got[0] if len(got) == 1 else None

    own, named_in = collections.defaultdict(list), collections.defaultdict(list)
    parents, children, said = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        src = r["source"]
        hb, hm = split_mark(r["head"])
        sb, sm = split_mark(r["subject"])
        s = r["entry_id"] if sb == hb and sm in (0, hm) else resolve(src, r["subject"], hb)
        o = resolve(src, r["object"], sb)
        r["subject_entry"], r["object_entry"] = s, o
        own[(src, r["entry_id"])].append(r)
        for node in (s, o):
            if node is not None and node != r["entry_id"]:
                named_in[(src, node)].append(r)
        if r["relation"] in PARENT and s is not None and o is not None and s != o:
            p, c = (o, s) if PARENT[r["relation"]] == "o" else (s, o)
            parents[(src, c)].add(p)
            children[(src, p)].add(c)
            said[(src, p, c)].add(r["entry_id"])
    val = {"by": by, "shown": shown, "links": links, "own": own, "named_in": named_in, "parents": parents,
           "children": children, "said": said, "rows": len(rows)}
    with _LOCK:
        _CACHE["model"] = (key, val)
    return val


def _generations(m: dict, src: str, start: int, way: str, depth: int) -> list:
    """[[{entry, head, both}]]: the parents (way "up") or the children ("down") of an entry, generation by
    generation, each step marked when both entries state it; at most 12 persons a generation."""
    out, level, seen = [], [start], {start}
    edges = m["parents"] if way == "up" else m["children"]
    for _ in range(depth):
        nxt = []
        for e in level:
            for x in sorted(edges.get((src, e), ()), key=lambda z: m["shown"].get((src, z), "")):
                if x in seen:
                    continue
                seen.add(x)
                p, c = (x, e) if way == "up" else (e, x)
                nxt.append({"entry": x, "head": m["shown"].get((src, x), str(x)), "of": e,
                            "both": {p, c} <= m["said"].get((src, p, c), set())})
        if not nxt:
            break
        out.append(nxt[:12])
        level = [n["entry"] for n in nxt[:12]]
    return out


def _item(r: dict, me: int, m: dict) -> dict:
    """One relation, said from the side of the entry `me`: the other person as the index names him."""
    src = r["source"]
    if r.get("subject_entry") == me:
        other, other_entry, other_entity, rel, said_as = r["object"], r.get("object_entry"), r["object_entity"], \
            r["relation"], "subject"
    else:
        other, other_entry, other_entity, rel, said_as = r["subject"], r.get("subject_entry"), r["subject_entity"], \
            r["relation"], "object"
    return {"relation": rel, "label": rel.replace("_", " "), "group": GROUPS.get(rel, "other"), "as": said_as,
            "subject": r["subject"], "object": r["object"], "other": other,
            "other_head": m["shown"].get((src, other_entry), "") if other_entry else "",
            "other_entity": other_entity, "words": r["words"], "refs": r["refs"],
            "entry_head": r["head"], "verdict": r["verdict"], "passages": r["passages"], "texts": r["texts"],
            "places": r["places"], "raychaudhuri": r["raychaudhuri"], "raychaudhuri_note": r["raychaudhuri_note"]}


def view(db: str, entity_id: int, shelf_dir, k: int = 24, depth: int = 6) -> dict:
    """The page's whole answer for one of our names (see the module's note)."""
    shelf = Path(shelf_dir)
    nm = _names(db)
    if entity_id not in nm["ents"]:
        return {"error": "no such name", "mark": MARK}
    canon, kind, mentions = nm["ents"][entity_id]
    out = {"mark": MARK, "entity": {"id": entity_id, "name": canon, "kind": kind, "mentions": mentions},
           "together": [], "near": [], "persons": [], "claims": [], "read": {}, "titles": SHELF_TITLES}
    con = ro(db)
    try:
        if has(con, "entity_links"):
            for rel in ("together", "near"):
                for a, b, n, t, places in con.execute(
                        "SELECT a, b, passages, texts, places FROM entity_links WHERE (a = ? OR b = ?) AND rel = ? "
                        "ORDER BY passages DESC, texts DESC LIMIT ?", (entity_id, entity_id, rel, int(k))):
                    other = b if a == entity_id else a
                    oc, ok, _on = nm["ents"].get(other, (str(other), "", 0))
                    try:
                        pl = json.loads(places or "[]")[:3]
                    except ValueError:
                        pl = []
                    out[rel].append({"id": other, "name": oc, "kind": ok, "passages": n, "texts": t,
                                     "places": [{"doc": p[1], "ref": p[2]} for p in pl if len(p) >= 3]})
            out["read"]["links"] = True
        else:
            out["read"]["links"] = False
        t = con.execute("SELECT COUNT(DISTINCT p.doc_id) FROM entity_mentions m JOIN passages p ON p.id = m.passage_id "
                        "WHERE m.entity_id = ?", (entity_id,)).fetchone()
        out["entity"]["texts"] = t[0] if t else 0
    finally:
        con.close()
    m = _model(db, str(shelf / "kin.db"))
    out["read"]["indexes"] = m["rows"]
    entries = set()   # the index's persons of this name: the head is the name, or the shelf ties the entry exactly
    for src in SHELF_TITLES:
        for e, _mark in m["by"].get(src, {}).get(fold(canon), ()):
            entries.add((src, e))
    for e in m["links"].get(entity_id, ()):
        for src in SHELF_TITLES:
            if (src, e) in m["shown"]:
                entries.add((src, e))
    persons = []
    for src, e in entries:
        own = [_item(r, e, m) for r in m["own"].get((src, e), ())]
        named = [dict(_item(r, e, m), stated_in=r["head"]) for r in m["named_in"].get((src, e), ())]
        if not own and not named:
            continue
        persons.append({"source": src, "index": SHORT[src], "title": SHELF_TITLES[src], "entry": e,
                        "head": m["shown"].get((src, e), str(e)), "own": own, "named_in": named[:40],
                        "up": _generations(m, src, e, "up", depth), "down": _generations(m, src, e, "down", 3)})
    persons.sort(key=lambda p: (-(len(p["own"]) + len(p["named_in"])), p["source"], p["head"]))
    out["persons"] = persons
    cp = shelf / "claims.db"
    out["read"]["claims"] = False
    if cp.exists():
        c2 = ro(cp)
        try:
            if has(c2, "claims") and has(c2, "claim_links") and has(c2, "claim_reads"):
                for cid, printed, rel, claim in c2.execute(
                        "SELECT DISTINCT c.id, c.printed, c.relation, c.claim FROM claim_links l JOIN claims c ON "
                        "c.id = l.claim_id WHERE l.entity_id = ? AND c.read_id IN (SELECT MAX(id) FROM claim_reads "
                        "WHERE status = 'ok' GROUP BY work, pdf_page) ORDER BY c.id LIMIT 60", (entity_id,)):
                    out["claims"].append({"page": printed or "", "relation": rel or "", "claim": claim or "",
                                          "source": CLAIMS_SOURCE})
                out["read"]["claims"] = True
        finally:
            c2.close()
    return out
