#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
relations_census.py  (2026-10-22)  RELATIONS_CENSUS_2026_10_22

How the brain's names are joined to one another, measured. Free and read-only: the database is opened read-only
(--immutable for a backup copy), nothing is written to it, no API is called.

What it counts
  names        entities by kind, their mentions, the passages that name anyone
  together     two names in one passage ("named together"): how many pairs, in how many passages, in how many
               texts. This is our own evidence, from our texts; it says the two belong to one story or one list,
               not how they are related.
  index        the scholars' shelf (shelf_entries: Dikshitar's Purana Index, the Vedic Index, Soerensen's index of
               the Mahabharata's names): the entries whose own words state a kinship or a school ("son of",
               "daughter of", "wife of", "pupil of", "king of", "contemporary", "patronymic"). These are candidate
               relations, as the index prints them; a pattern cannot tell their direction ("married the daughter
               of Ugrasena" is not "daughter of"), so none is stored as a relation here.
  --name N     one name's neighbours: who is named with it most, in how many passages and texts, with places.

  python scripts\\relations_census.py
  python scripts\\relations_census.py --name Janaka
  python scripts\\relations_census.py --db D:\\backups\\some_backup.db --immutable

Writes exports\\relations_census.json and exports\\names_together.csv (the pairs named together in two passages or
more) unless --no-write.
"""
from __future__ import annotations
import argparse, collections, csv, itertools, json, re, sqlite3, sys, unicodedata, urllib.parse
from pathlib import Path

MARK = "RELATIONS_CENSUS_2026_10_22"
ROOT = Path(__file__).resolve().parent.parent
MAX_NAMES = 12   # a passage naming more is a list (a genealogy, a catalogue): its pairs are not counted
PHRASES = {
    "son of": r"\bsons? of\b", "daughter of": r"\bdaughters? of\b", "father of": r"\bfather of\b",
    "mother of": r"\bmother of\b", "wife of": r"\bwi(fe|ves) of\b", "husband of": r"\bhusband of\b",
    "brother of": r"\bbrothers? of\b", "pupil of": r"\b(pupil|disciple)s? of\b",
    "teacher of": r"\b(teacher|preceptor|guru) of\b", "king of": r"\bking of\b", "contemporary": r"\bcontemporar",
    "patronymic": r"\b(patronymic|descendant)\b",
}


def connect(db: str, immutable: bool):
    p = Path(db).resolve().as_posix()
    p = p if p.startswith("/") else "/" + p          # D:/x -> /D:/x, so file:///D:/x as SQLite reads it on Windows
    uri = "file://%s?mode=ro%s" % (urllib.parse.quote(p, safe="/:"), "&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)


def has(con, table: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def census(con) -> dict:
    out = {"mark": MARK}
    kinds = collections.Counter(k or "other" for (k,) in con.execute("SELECT kind FROM entities"))
    out["entities"] = sum(kinds.values())
    out["kinds"] = dict(kinds.most_common())
    name = {i: (c, k) for i, c, k in con.execute("SELECT id, canonical, kind FROM entities")}
    rows = con.execute("""SELECT m.entity_id, m.passage_id, d.code, p.verse_ref, p.page_no, p.idx
                          FROM entity_mentions m JOIN passages p ON p.id = m.passage_id
                          JOIN docs d ON d.id = p.doc_id
                          WHERE d.code NOT LIKE '%-RETIRED'""").fetchall()
    out["mentions"] = len(rows)
    by_passage = collections.defaultdict(set)
    where = {}
    for eid, pid, code, vref, page, idx in rows:
        by_passage[pid].add(eid)
        where[pid] = (code, vref or "p%s.%s" % (page, idx))
    out["passages_named"] = len(by_passage)
    pairs = collections.Counter()
    texts = collections.defaultdict(set)
    places = collections.defaultdict(list)
    lists = 0
    for pid, es in by_passage.items():
        if len(es) > MAX_NAMES:
            lists += 1
            continue
        for a, b in itertools.combinations(sorted(es), 2):
            pairs[(a, b)] += 1
            texts[(a, b)].add(where[pid][0])
            if len(places[(a, b)]) < 3:
                places[(a, b)].append("%s %s" % where[pid])
    out["together"] = {"pairs": len(pairs), "in_2_passages": sum(1 for v in pairs.values() if v >= 2),
                       "in_5_passages": sum(1 for v in pairs.values() if v >= 5),
                       "in_2_texts": sum(1 for k in pairs if len(texts[k]) >= 2),
                       "lists_left_out": lists, "max_names": MAX_NAMES}
    out["_pairs"], out["_texts"], out["_places"], out["_name"] = pairs, texts, places, name
    idx = {}
    if has(con, "shelf_entries"):
        src_title = dict(con.execute("SELECT code, title FROM shelf_sources")) if has(con, "shelf_sources") else {}
        counts = collections.defaultdict(collections.Counter)
        totals = collections.Counter()
        for src, text in con.execute("SELECT source, coalesce(head,'') || ' ' || coalesce(body,'') FROM shelf_entries"):
            totals[src] += 1
            low = text.lower()
            for k, p in PHRASES.items():
                if re.search(p, low):
                    counts[src][k] += 1
        for src in totals:
            idx[src] = {"title": src_title.get(src, src), "entries": totals[src], "with_phrase": dict(counts[src])}
    out["index"] = idx
    return out


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").lower()
    return "".join(c for c in s if not unicodedata.combining(c))


def neighbours(c: dict, who: str, k: int = 12) -> list:
    name = c["_name"]
    ids = [i for i, (n, _) in name.items() if fold(n) == fold(who)]
    res = []
    for i in ids:
        co = collections.Counter()
        for (a, b), n in c["_pairs"].items():
            if a == i:
                co[b] += n
            elif b == i:
                co[a] += n
        for j, n in co.most_common(k):
            key = (min(i, j), max(i, j))
            res.append({"name": name[i][0], "with": name[j][0], "kind": name[j][1], "passages": n,
                        "texts": len(c["_texts"][key]), "places": c["_places"][key]})
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="how the brain's names are joined (read-only)")
    ap.add_argument("--db", default="")
    ap.add_argument("--immutable", action="store_true", help="the file is a backup copy: open it immutable")
    ap.add_argument("--name", default="")
    ap.add_argument("--root", default="")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a name in IAST must not stop it
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    root = Path(a.root).resolve() if a.root else ROOT
    db = a.db or str(root / "data" / "context.db")
    if not Path(db).exists():
        print("%s: no database at %s" % (MARK, db))
        return 2
    con = connect(db, a.immutable)
    for t in ("entities", "entity_mentions", "passages", "docs"):
        if not has(con, t):
            print("%s: the database has no %s table" % (MARK, t))
            return 2
    c = census(con)
    t = c["together"]
    print("%s: %d names (%s); %d mentions in %d passages" % (
        MARK, c["entities"], ", ".join("%s %d" % kv for kv in list(c["kinds"].items())[:7]), c["mentions"],
        c["passages_named"]))
    print("  named together: %d pairs; %d in two passages or more, %d in five or more; %d in two texts or more "
          "(%d passages naming more than %d left out as lists)" % (
              t["pairs"], t["in_2_passages"], t["in_5_passages"], t["in_2_texts"], t["lists_left_out"], MAX_NAMES))
    for (x, y), n in c["_pairs"].most_common(8):
        print("    %4d  %s + %s" % (n, c["_name"][x][0], c["_name"][y][0]))
    if c["index"]:
        print("  the scholars' shelf: entries that state a kinship or a school, as printed (candidates, not stored):")
        for src, v in c["index"].items():
            print("    %-46s %6d entries; %s" % (v["title"][:46], v["entries"], ", ".join(
                "%s %d" % kv for kv in sorted(v["with_phrase"].items(), key=lambda kv: -kv[1]))))
    nb = neighbours(c, a.name) if a.name else []
    if a.name:
        print("\n  %s is named with:" % a.name)
        if not nb:
            print("    (no name of that spelling, or never named with another)")
        for r in nb:
            print("    %4d passages, %d texts  %-28s (%s)  e.g. %s" % (r["passages"], r["texts"], r["with"][:28],
                                                                 r["kind"], "; ".join(r["places"])))
    if not a.no_write:
        out = root / "exports"
        out.mkdir(parents=True, exist_ok=True)
        keep = {k: v for k, v in c.items() if not k.startswith("_")}
        if nb:
            keep["name"] = {"asked": a.name, "with": nb}
        (out / "relations_census.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(out / "names_together.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["name_a", "kind_a", "name_b", "kind_b", "passages", "texts", "places"])
            for (x, y), n in c["_pairs"].most_common():
                if n < 2:
                    break
                w.writerow([c["_name"][x][0], c["_name"][x][1], c["_name"][y][0], c["_name"][y][1], n,
                            len(c["_texts"][(x, y)]), "; ".join(c["_places"][(x, y)])])
        print("written: %s, names_together.csv" % (out / "relations_census.json"))
    print("VERDICT: the names are joined through the passages (named together: %d pairs in two passages or more); "
          "no relation of kinship or school is stored yet" % t["in_2_passages"])
    print("NEXT: docs\\RELATIONS_AND_ASK_2026-10-22.md, phase R1 (the named-together links stored, free)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
