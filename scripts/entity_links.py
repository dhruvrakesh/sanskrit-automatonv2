#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
entity_links.py  (2026-10-22)  ENTITY_LINKS_2026_10_22

Phase R1 (relations-together) of docs/RELATIONS_AND_ASK_2026-10-22.md: the links our own texts make between the
brain's names, stored once, so that a name page, Ask and the scholars' check read them without counting again.

  together   two names in one passage (relations_census.py counts the same pairs, and this agrees with it)
  near       two names in two different passages of one text, no more than WINDOW (5) passages apart: a court, a
             debate, a battle told over several verses. Janaka's court in the Brhadaranyaka is told over a whole
             book: Uddalaka Aruni speaks in one passage and Janaka is named in another, so "together" alone misses it.

A passage naming more than MAX_NAMES (12) names is a list (a genealogy, a catalogue) and is left out of both, as in
relations_census.py; a retired text is left out. A link says that our texts name the two together, or near, in so
many passages of so many texts, and where (three places). It does not say how the two are related (son, pupil,
king, enemy): that is a kinship, read from the indexes and checked (relations-index, relations-check).

  python scripts\\entity_links.py                     count, write nothing (free; the database opened read-only)
  python scripts\\entity_links.py --apply             a backup first (db_backup.py, to --backup-dir), then the table
                                                      entity_links rebuilt whole in one transaction; refuses while the
                                                      dashboard runs a database writer
  python scripts\\entity_links.py --name Janaka       one name's links (from the table when it is built)
  python scripts\\entity_links.py --claims data\\shelf\\claims.db
                                                      the scholars' check, read-only: each claim whose subject and
                                                      object are both our names, against our texts: "named together",
                                                      "named near", "both named, never near", "one not in our texts";
                                                      writes exports\\claims_in_our_texts.csv and .json
  python scripts\\entity_links.py --db D:\\backups\\some_backup.db --immutable --claims data\\shelf\\claims.db

The tables (nothing else in the database is written; to undo: DROP TABLE entity_links; DROP TABLE entity_link_runs;
or restore the backup):
  entity_links      a, b (entities.id, a < b), rel ("together" or "near"), passages, texts, docs (up to 8 text codes,
                    comma-separated), places (JSON: up to 3 [passage_id, code, ref]), built_at, mark;
                    PRIMARY KEY (a, b, rel); an index on (b)
  entity_link_runs  one row per --apply: when, the backup, the counts
"""
from __future__ import annotations
import argparse, collections, csv, datetime, itertools, json, os, sqlite3, sys, unicodedata, urllib.parse
from pathlib import Path

MARK = "ENTITY_LINKS_2026_10_22"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAX_NAMES = 12    # as relations_census.py: a passage naming more is a list
WINDOW = 5        # "near": within this many passages of one text
MAX_DOCS = 8
MAX_PLACES = 3
RELS = ("together", "near")
VERDICTS = ("named together", "named near", "both named, never near", "one not in our texts")

SCHEMA = """
CREATE TABLE IF NOT EXISTS entity_links (
  a INTEGER NOT NULL, b INTEGER NOT NULL, rel TEXT NOT NULL, passages INTEGER NOT NULL, texts INTEGER NOT NULL,
  docs TEXT, places TEXT, built_at TEXT NOT NULL, mark TEXT NOT NULL, PRIMARY KEY (a, b, rel));
CREATE INDEX IF NOT EXISTS ix_entity_links_b ON entity_links(b);
CREATE TABLE IF NOT EXISTS entity_link_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, db TEXT, backup TEXT, entities INTEGER, mentions INTEGER,
  passages_named INTEGER, lists_left_out INTEGER, together INTEGER, near INTEGER, window INTEGER, max_names INTEGER,
  mark TEXT NOT NULL);
"""


def _uri(db: str, immutable: bool) -> str:
    p = Path(db).resolve().as_posix()
    p = p if p.startswith("/") else "/" + p          # D:/x -> /D:/x, as SQLite reads a file: URI on Windows
    return "file://%s?mode=ro%s" % (urllib.parse.quote(p, safe="/:"), "&immutable=1" if immutable else "")


def connect_ro(db: str, immutable: bool = False):
    return sqlite3.connect(_uri(db, immutable), uri=True, timeout=60)


def has(con, table: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").lower()
    return "".join(c for c in s if not unicodedata.combining(c))


def compute(con, window: int = WINDOW, max_names: int = MAX_NAMES) -> dict:
    """The links, counted from entity_mentions. Read-only."""
    name = {i: (c, k) for i, c, k in con.execute("SELECT id, canonical, kind FROM entities")}
    rows = con.execute("""SELECT m.entity_id, m.passage_id, p.doc_id, d.code, p.verse_ref, p.page_no, p.idx
                          FROM entity_mentions m JOIN passages p ON p.id = m.passage_id
                          JOIN docs d ON d.id = p.doc_id
                          WHERE d.code NOT LIKE '%-RETIRED'""").fetchall()
    by_passage = collections.defaultdict(set)
    where = {}
    mentioned = collections.Counter()
    for eid, pid, did, code, vref, page, idx in rows:
        by_passage[pid].add(eid)
        mentioned[eid] += 1
        where[pid] = (did, code, vref or "p%s.%s" % (page, idx))
    lists = {pid for pid, es in by_passage.items() if len(es) > max_names}
    links = {}   # (a, b, rel) -> [passages set, docs set, places list]

    def add(a, b, rel, pid):
        key = (a, b, rel) if a < b else (b, a, rel)
        v = links.get(key)
        if v is None:
            v = links[key] = [set(), set(), []]
        if pid in v[0]:
            return
        v[0].add(pid)
        d = where[pid]
        v[1].add(d[1])
        if len(v[2]) < MAX_PLACES:
            v[2].append([pid, d[1], d[2]])

    for pid in sorted(by_passage):
        if pid in lists:
            continue
        for a, b in itertools.combinations(sorted(by_passage[pid]), 2):
            add(a, b, "together", pid)
    if window > 0:
        docs_of = {where[pid][0] for pid in by_passage}
        pos = {}
        for did in docs_of:   # the order of every passage of the text, named or not: "5 passages apart" is so read
            seq = con.execute("SELECT id FROM passages WHERE doc_id = ? ORDER BY page_no, idx, id", (did,)).fetchall()
            for i, (pid,) in enumerate(seq):
                pos[pid] = (did, i)
        per_doc = collections.defaultdict(list)
        for pid, es in by_passage.items():
            if pid not in lists and pid in pos:
                per_doc[pos[pid][0]].append((pos[pid][1], pid, es))
        for did, lst in per_doc.items():
            lst.sort()
            for k, (i, p, es) in enumerate(lst):
                m = k + 1
                while m < len(lst) and lst[m][0] - i <= window:
                    q, fs = lst[m][1], lst[m][2]
                    for x in es:
                        for y in fs:
                            if x != y:
                                add(x, y, "near", p)
                                add(x, y, "near", q)
                    m += 1
    n = collections.Counter(rel for (_, _, rel) in links)
    return {"name": name, "links": links, "mentioned": mentioned, "mentions": len(rows),
            "passages_named": len(by_passage), "lists_left_out": len(lists), "together": n["together"],
            "near": n["near"], "window": window, "max_names": max_names, "entities": len(name)}


def stored(con) -> dict:
    """The links as the table holds them (after --apply), in compute()'s shape; {} when not built."""
    if not has(con, "entity_links"):
        return {}
    links = {}
    for a, b, rel, n, t, docs, places in con.execute(
            "SELECT a, b, rel, passages, texts, docs, places FROM entity_links"):
        links[(a, b, rel)] = [n, (docs or "").split(",") if docs else [], json.loads(places or "[]"), t]
    return links


def summary_line(c: dict) -> str:
    return ("%s: %d names, %d mentions in %d passages (%d lists of more than %d names left out); links: %d named "
            "together in one passage, %d named near (within %d passages of one text)" % (
                MARK, c["entities"], c["mentions"], c["passages_named"], c["lists_left_out"], c["max_names"],
                c["together"], c["near"], c["window"]))


def rows_of(c: dict, built_at: str):
    for (a, b, rel), (ps, ds, pl) in c["links"].items():
        yield (a, b, rel, len(ps), len(ds), ",".join(sorted(ds)[:MAX_DOCS]), json.dumps(pl, ensure_ascii=True),
               built_at, MARK)


def apply(a, c: dict) -> int:
    sys.path.insert(0, str(HERE))
    import repair_text as rt   # noqa: E402  (writers_running, run: one way of doing each)
    w = rt.writers_running(False)
    if w:
        print("REFUSE: the dashboard runs a database writer (%s); nothing was changed" % ", ".join(
            "%s %s" % (j.get("kind"), j.get("doc")) for j in w))
        print("NEXT: python scripts\\entity_links.py --apply   (when the dashboard is idle)")
        return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = Path(a.backup_dir)
    bdir.mkdir(parents=True, exist_ok=True)
    backup = bdir / ("context_pre_links_%s.db" % stamp)
    if rt.run([sys.executable, HERE / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        print("REFUSE: the backup failed; nothing was changed")
        return 1
    at = datetime.datetime.now().isoformat(timespec="seconds")
    con = sqlite3.connect(a.db, timeout=60)
    try:
        con.execute("PRAGMA busy_timeout=60000")
        con.executescript(SCHEMA)
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM entity_links")
        con.executemany("INSERT INTO entity_links (a, b, rel, passages, texts, docs, places, built_at, mark) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", rows_of(c, at))
        con.execute("INSERT INTO entity_link_runs (at, db, backup, entities, mentions, passages_named, lists_left_out, "
                    "together, near, window, max_names, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (at, str(a.db), str(backup), c["entities"], c["mentions"], c["passages_named"],
                     c["lists_left_out"], c["together"], c["near"], c["window"], c["max_names"], MARK))
        con.commit()
        got = dict(con.execute("SELECT rel, COUNT(*) FROM entity_links GROUP BY rel").fetchall())
        now = con.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
    except Exception as e:
        con.rollback()
        print("REFUSE: the write failed (%s: %s); the transaction was rolled back, the backup is %s" % (
            type(e).__name__, e, backup))
        return 1
    finally:
        con.close()
    ok = got.get("together", 0) == c["together"] and got.get("near", 0) == c["near"]
    print("written: entity_links %d together, %d near (backup %s)" % (got.get("together", 0), got.get("near", 0),
                                                                     backup))
    if not ok:
        print("VERDICT: the table does not hold what was counted; restore the backup %s" % backup)
        return 1
    print("VERDICT: the named-together links are stored (%d together, %d near)%s" % (
        c["together"], c["near"], "" if now >= c["mentions"] else "; the mentions changed meanwhile: run it again"))
    print("NEXT: python scripts\\entity_links.py --claims data\\shelf\\claims.db   (the scholars' check, free)")
    return 0


def neighbours(c: dict, who: str, k: int = 12) -> list:
    name = c["name"]
    ids = {i for i, (n, _) in name.items() if fold(n) == fold(who)}
    out = []
    for (x, y, rel), v in c["links"].items():
        if x in ids or y in ids:
            me, other = (x, y) if x in ids else (y, x)
            n = len(v[0]) if isinstance(v[0], set) else v[0]
            t = len(v[1]) if isinstance(v[0], set) else v[3]
            out.append({"name": name.get(me, ("?", ""))[0], "with": name.get(other, ("?", ""))[0],
                        "kind": name.get(other, ("", ""))[1], "rel": rel, "passages": n, "texts": t,
                        "places": ["%s %s" % (p[1], p[2]) for p in v[2]]})
    out.sort(key=lambda r: (r["rel"] != "together", -r["passages"], r["with"]))
    keep, seen = [], collections.Counter()
    for r in out:
        if seen[r["rel"]] < k:
            keep.append(r)
            seen[r["rel"]] += 1
    return keep


def claims_check(c: dict, claims_db: str) -> dict:
    """Each claim whose subject and object both resolve to our names, against our texts. Read-only."""
    cl = connect_ro(claims_db, immutable=False)
    try:
        for t in ("claims", "claim_links"):
            if not has(cl, t):
                raise SystemExit("%s: %s has no %s table" % (MARK, claims_db, t))
        sides = collections.defaultdict(lambda: {"subject": set(), "object": set()})
        for cid, role, eid in cl.execute("SELECT claim_id, role, entity_id FROM claim_links"):
            if role in ("subject", "object"):
                sides[cid][role].add(eid)
        claims = {r[0]: r for r in cl.execute(
            "SELECT id, work, printed, subject, relation, object, claim, stance, hedge FROM claims")}
    finally:
        cl.close()
    name, links, mentioned = c["name"], c["links"], c["mentioned"]

    def get(x, y, rel):
        v = links.get((min(x, y), max(x, y), rel))
        if not v:
            return 0, 0, []
        if isinstance(v[0], set):
            return len(v[0]), len(v[1]), ["%s %s" % (p[1], p[2]) for p in v[2]]
        return v[0], v[3], ["%s %s" % (p[1], p[2]) for p in v[2]]

    out, by_rel, tot = [], collections.defaultdict(collections.Counter), collections.Counter()
    for cid in sorted(sides):
        s, o = sides[cid]["subject"], sides[cid]["object"]
        pairs = [(x, y) for x in sorted(s) for y in sorted(o) if x != y]
        if not pairs or cid not in claims:
            continue
        best = None
        for rank, rel in ((0, "together"), (1, "near")):
            cand = [(get(x, y, rel), x, y) for x, y in pairs]
            cand = [z for z in cand if z[0][0] > 0]
            if cand:
                (n, t, pl), x, y = max(cand, key=lambda z: z[0][0])
                best = (VERDICTS[rank], x, y, n, t, pl)
                break
        if best is None:
            x, y = pairs[0]
            both = [(x2, y2) for x2, y2 in pairs if mentioned.get(x2) and mentioned.get(y2)]
            if both:
                x, y = both[0]
            best = (VERDICTS[2] if both else VERDICTS[3], x, y, 0, 0, [])
        v, x, y, n, t, pl = best
        r = claims[cid]
        rel = r[4] or "other"
        by_rel[rel][v] += 1
        tot[v] += 1
        out.append({"claim_id": cid, "work": r[1], "page": r[2], "relation": rel, "claim": r[6], "stance": r[7] or "",
                    "hedge": r[8] or "", "subject": name.get(x, ("?",))[0], "object": name.get(y, ("?",))[0],
                    "verdict": v, "passages": n, "texts": t, "places": "; ".join(pl)})
    return {"claims": len(out), "verdicts": {k: tot[k] for k in VERDICTS},
            "by_relation": {k: {v: by_rel[k][v] for v in VERDICTS if by_rel[k][v]}
                            for k in sorted(by_rel, key=lambda k: -sum(by_rel[k].values()))},
            "rows": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the links our texts make between the names (R1)")
    ap.add_argument("--db", default="")
    ap.add_argument("--immutable", action="store_true", help="the file is a backup copy: open it immutable")
    ap.add_argument("--root", default="")
    ap.add_argument("--apply", action="store_true", help="a backup, then the table entity_links rebuilt whole")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--name", default="")
    ap.add_argument("--claims", default="", help="the scholars' claims (data\\shelf\\claims.db): the check")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--no-write", action="store_true", help="with --claims: write no export")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a name in IAST must not stop it
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    root = Path(a.root).resolve() if a.root else ROOT
    a.db = a.db or str(root / "data" / "context.db")
    if not Path(a.db).exists():
        print("%s: no database at %s" % (MARK, a.db))
        return 2
    if a.apply and a.immutable:
        print("REFUSE: --apply writes the database; an immutable copy is read only")
        return 2
    con = connect_ro(a.db, a.immutable)
    try:
        for t in ("entities", "entity_mentions", "passages", "docs"):
            if not has(con, t):
                print("%s: the database has no %s table" % (MARK, t))
                return 2
        c = compute(con, window=a.window)
        built = stored(con)
    finally:
        con.close()
    print(summary_line(c))
    if built:
        n = collections.Counter(k[2] for k in built)
        same = n["together"] == c["together"] and n["near"] == c["near"]
        print("  the table entity_links holds %d together, %d near: %s" % (
            n["together"], n["near"], "as counted now" if same else "not as counted now (--apply rebuilds it)"))
    else:
        print("  the table entity_links is not built yet")
    for rel in RELS:
        top = sorted(((len(v[0]), k) for k, v in c["links"].items() if k[2] == rel), reverse=True)[:5]
        for n, (x, y, _) in top:
            print("    %-8s %4d  %s + %s" % (rel, n, c["name"][x][0], c["name"][y][0]))
    if a.name:
        nb = neighbours(c, a.name)
        print("\n  %s:" % a.name)
        if not nb:
            print("    (no name of that spelling, or never named with another)")
        for r in nb:
            print("    %-8s %4d passages, %d texts  %-28s (%s)  e.g. %s" % (
                r["rel"], r["passages"], r["texts"], r["with"][:28], r["kind"], "; ".join(r["places"][:2])))
    if a.claims:
        if not Path(a.claims).exists():
            print("%s: no claims database at %s" % (MARK, a.claims))
            return 2
        k = claims_check(c, a.claims)
        v = k["verdicts"]
        print("\n  the scholars' check: %d claims whose subject and object are both our names: %s" % (
            k["claims"], "; ".join("%s %d" % (x, v[x]) for x in VERDICTS)))
        for rel, d in list(k["by_relation"].items())[:12]:
            print("    %-16s %s" % (rel, ", ".join("%s %d" % kv for kv in d.items())))
        for verdict in VERDICTS[:3]:
            ex = [r for r in k["rows"] if r["verdict"] == verdict and r["relation"] != "named_in"][:3]
            for r in ex:
                print("    e.g. %-22s p.%-4s %s%s" % (verdict, r["page"], r["claim"][:90],
                                                    ("  [%s]" % r["places"][:60]) if r["places"] else ""))
        if not a.no_write:
            out = root / "exports"
            out.mkdir(parents=True, exist_ok=True)
            cols = ["claim_id", "work", "page", "relation", "claim", "stance", "hedge", "subject", "object", "verdict",
                    "passages", "texts", "places"]
            with open(out / "claims_in_our_texts.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for r in k["rows"]:
                    w.writerow(r)
            keep = {x: y for x, y in k.items() if x != "rows"}
            keep.update(mark=MARK, db=a.db, claims_db=a.claims, window=c["window"])
            (out / "claims_in_our_texts.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
            print("written: %s, claims_in_our_texts.json" % (out / "claims_in_our_texts.csv"))
    if a.apply:
        return apply(a, c)
    if not built:
        print("NEXT: python scripts\\entity_links.py --apply   (a backup first; the dashboard idle)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
