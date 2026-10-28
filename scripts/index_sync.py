#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
index_sync.py  (2026-10-25)  INDEX_SITE_2026_10_25

The genealogies of the three indexes, on the site. What the dashboard's Vamsa page draws (scripts/vamsa_view.py: the
lines of descent of the Purana Index, the Vedic Index and Soerensen's Index, each step with what it rests on) is
computed here from the same stores, read-only, and sent to the site's private mirror (docs/cloud/C21): the persons,
their lines up and down, the steps, every kept relation the indexes state (all kinds), the longest lines, and the
GRETIL verses where both names stand. The site's /corpus/genealogies reads them (Srangam INDEX_SITE_2026_10_25).
B2_SITE_2026_10_28 (scheme i2, docs/cloud/C23): and the scholars' claims beside them: each relation's verdict in
Raychaudhuri's Political History of Ancient India (1923; public domain) as the desk weighs it (kin_index.py: agrees,
reversed, differs), with the claims it rests on, and those claims themselves (data/shelf/claims.db: scholar_claims.py),
only the public-domain works', only the claims whose quotation was found on the page (exact or close), their names tied
to ours only where one name of ours is the candidate. Until C23 is pasted the claims are left out, the rest is sent.

  read     data/context.db (the shelf's entries, our names and their ties, our passages), data/shelf/kin.db (the
           kinships read: kin_index.py), data/shelf/vamsa.db (their citations read in GRETIL: vamsa_check.py),
           data/shelf/claims.db (the scholars' claims: scholar_claims.py); all read-only (--immutable for a backup
           copy). No model is called.
  send     what differs only: the server's digest of each table first, then its keys and hashes; a row the desk no
           longer has is deleted there (these tables are derived, recomputed every run).
  not sent a work not in the public domain; a claim whose quotation was not found on its page; the Mahabharata e-text's words (BORI asks that the text not be
           given to others: its references and counts only); the shelf's entries themselves (the Cologne files: only
           the relations derived from them, with the words they rest on, as H2 decided, with the credit and the
           licence's notice, CC BY-NC-SA 3.0, while the site is non-commercial).

Sinks, as corpus_sync.py's: --sink edge (the edge function corpus-index, HMAC-signed with CORPUS_SYNC_SECRET; the URL
and publishable key from the Srangam repo's .env), --sink pg (a PostgreSQL with C21: --dsn or CORPUS_SYNC_DSN, for the
tests), --sink none (no network: the plan), --sink auto (edge when CORPUS_SYNC_SECRET is set, else none).

  python scripts\\index_sync.py                    the plan: what would be sent (free)
  python scripts\\index_sync.py --apply            send it
  python scripts\\index_sync.py --status           the counts here and there
  python scripts\\index_sync.py --dump exports\\index_site.json.gz   the rows, for a look (nothing sent)
  python scripts\\index_sync.py --apply --if-configured   the scheduled tick (scripts\\corpus_mirror_task.ps1): exits 0
           doing nothing until CORPUS_SYNC_SECRET is set, the stores are there, C21 is pasted and corpus-index is
           deployed

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations

import argparse, collections, gzip, hashlib, json, os, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

MARK = "INDEX_SITE_2026_10_25"
SCHEME = "i2"   # B2_SITE_2026_10_28: i2 adds the claims
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
TABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "meta")
OPTIONAL = ("claims",)   # sent only when the site has the table (C23) and corpus-index takes it
MAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000
INDEX_RIGHTS = ("the relations derived from the index, with the entry's own words: Cologne Digital Sanskrit "
                "Dictionaries, CC BY-NC-SA 3.0 (https://creativecommons.org/licenses/by-nc-sa/3.0/)")
INDEX_EDITIONS = {"pui": "Madras: University of Madras, 1951-55; digitized by the Cologne Digital Sanskrit Dictionaries",
                  "vei": "London: John Murray, 1912; digitized by the Cologne Digital Sanskrit Dictionaries",
                  "inm": "London: Williams and Norgate, 1904-25; digitized by the Cologne Digital Sanskrit Dictionaries"}
STATEMENT_FIELDS = ("source", "entry_id", "head", "subject", "relation", "object", "words")
# a citation's check: the forms (the two names as the verse writes them, to mark them) only for a text shown
CITE_FIELDS = ("text", "ref", "verdict", "printed", "at", "subject_form", "object_form")
CLAIM_QUOTES = ("exact", "close")          # a claim goes to the site only when its quotation was found on its page
CERTAIN_TIES = ("exact", "numbered exact")  # the others are probable; the site says how each was made
SCHOLAR_ORDER = ["agrees", "differs", "reversed"]   # vamsa_view's order of the scholars' verdicts


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def ro_immutable(path) -> sqlite3.Connection:
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=10)


def digest(pairs) -> str:
    """md5 of "key:hash" joined by commas in byte order: as the server's corpus_index_manifest()."""
    return hashlib.md5(",".join("%s:%s" % kv for kv in sorted(pairs)).encode("utf-8")).hexdigest()


def finish(row: dict) -> dict:
    body = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row["row_hash"] = hashlib.md5(body.encode("utf-8")).hexdigest()
    return row


def statement_key(r: dict) -> str:
    raw = "\x1f".join(str(r.get(k) or "") for k in STATEMENT_FIELDS)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def _places(con, pairs: dict, live=None) -> dict:
    """{(a, b): [{doc, page, idx, ref}]}: where our live texts first name both (entity_links, together before near);
    only texts the mirror carries (corpus_sync.live_docs: a witness, a withdrawn or a retired text is not on the site,
    so the site is never sent a place it cannot open)."""
    out = {}
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'entity_links'").fetchone():
        return out
    pid_of = {}
    for (a, b) in pairs:
        got = []
        for rel, pl in con.execute("SELECT rel, places FROM entity_links WHERE a = ? AND b = ? ORDER BY rel = 'near'",
                                   (min(a, b), max(a, b))):
            try:
                for p in json.loads(pl or "[]"):
                    if isinstance(p, list) and len(p) >= 3 and len(got) < 3 and (live is None or p[1] in live):
                        got.append(p)
            except ValueError:
                continue
            if got:
                break
        out[(a, b)] = got
        for p in got:
            pid_of[p[0]] = None
    if pid_of:
        ids = list(pid_of)
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            for pid, page, idx in con.execute("SELECT id, page_no, idx FROM passages WHERE id IN (%s)"
                                              % ",".join("?" * len(chunk)), chunk):
                pid_of[pid] = (page, idx)
    for k, got in out.items():
        out[k] = [{"doc": p[1], "page": pid_of[p[0]][0], "idx": pid_of[p[0]][1], "ref": str(p[2] or "")}
                  for p in got if pid_of.get(p[0])]
    return out


def _claims(claims_db: str, live, immutable: bool = False):
    """(works rows, claim rows, (key_ix, pair_ix)) from data/shelf/claims.db, read-only. Only the public-domain works,
    only the claims whose quotation was found on the page. The indexes match the claims to the kinships as kin_index.py
    does (claims_index, norm: by our entities on both sides, every tie counted), so a verdict the site shows always has
    a claim on the site beside it."""
    if not claims_db or not Path(claims_db).exists():
        return [], [], ({}, {})
    import kin_index as ki
    con = (ro_immutable(claims_db) if immutable else
           sqlite3.connect(Path(claims_db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10))
    try:
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"claims", "claim_works", "claim_links"} <= have:
            return [], [], ({}, {})
        works = {}
        for code, author, title, pub, year, source, handle, licence in con.execute(
                "SELECT code, author, title, publisher, year, source, handle, licence FROM claim_works"):
            if (licence or "").lower().startswith("public domain"):
                works[code] = {"key": "work:" + code, "kind": "work", "code": code,
                               "title": "%s, %s" % (author, title), "show": True, "rights": licence or "",
                               "edition": "; ".join(x for x in ("%s, %s" % (pub, year) if pub else str(year or ""),
                                                               "the scan: %s" % source if source else "",
                                                               "handle %s" % handle if handle else "") if x)}
        sides = collections.defaultdict(lambda: {"subject": set(), "object": set()})
        tie_rows = collections.defaultdict(list)
        for cid, role, eid, canonical, how, cands in con.execute(
                "SELECT claim_id, role, entity_id, canonical, how, cands FROM claim_links"):
            if role in ("subject", "object"):
                sides[cid][role].add(eid)
                tie_rows[(cid, role)].append((canonical, how, cands))
        cites = collections.defaultdict(list)
        if "claim_cites" in have:
            for cid, printed, work, locus, ours, note in con.execute(
                    "SELECT claim_id, printed, work, locus, ours, note FROM claim_cites ORDER BY claim_id, n"):
                held = ours if ours and ours in live else None
                cites[cid].append({"printed": printed or "", "work": work or "", "locus": locus or "",
                                   "ours": held, "note": (note or "") if held else ""})
        rows, key_of = [], {}
        for (cid, work, page, printed, n, subj, rel, obj, claim, quote, qc, stance, hedge) in con.execute(
                "SELECT id, work, pdf_page, printed, n, subject, relation, object, claim, quote, quote_check, stance, "
                "hedge FROM claims ORDER BY work, pdf_page, n"):
            if work not in works or qc not in CLAIM_QUOTES:
                continue
            key = "%s:%d:%d" % (work, page, n)
            key_of[cid] = (key, rel)

            def tie(role):
                tr = tie_rows.get((cid, role), [])
                if len(tr) == 1 and int(tr[0][2] or 0) == 1 and tr[0][0]:
                    return tr[0][0], tr[0][1] or ""
                return None, ""
            sc, sh = tie("subject")
            oc, oh = tie("object")
            rows.append(finish({"key": key, "work": work, "pdf_page": page, "printed": printed or "", "n": n,
                                "subject": subj or "", "relation": rel or "", "object": obj or "",
                                "claim": claim or "", "quote": quote or "", "quote_check": qc, "stance": stance or "",
                                "hedge": hedge or "", "subject_canonical": sc, "subject_how": sh,
                                "object_canonical": oc, "object_how": oh, "cites": cites.get(cid, [])[:8]}))
    finally:
        con.close()
    key_ix, pair_ix = collections.defaultdict(list), collections.defaultdict(list)
    for cid, sd in sorted(sides.items()):
        if cid not in key_of:
            continue
        ck, rel = key_of[cid]
        for s in sorted(sd["subject"]):
            for o in sorted(sd["object"]):
                if s == o:
                    continue
                if ck not in pair_ix[(min(s, o), max(s, o))]:
                    pair_ix[(min(s, o), max(s, o))].append(ck)
                if rel in ki.CLASS and ck not in key_ix[ki.norm(rel, s, o)]:
                    key_ix[ki.norm(rel, s, o)].append(ck)
    return [finish(w) for _c, w in sorted(works.items())], rows, (key_ix, pair_ix)


def scholar_view(r: dict, ix) -> list:
    """[{work, verdict, note, claims}]: the desk's verdict on a relation (kin_index.py, stored in kin_ties), with the
    claims on the site it rests on; nothing when none of them is on the site."""
    import kin_index as ki
    verdict = r.get("raychaudhuri") or ""
    s, o, rel = r.get("subject_entity"), r.get("object_entity"), r.get("relation")
    if verdict not in SCHOLAR_ORDER or not s or not o or s == o:
        return []
    key_ix, pair_ix = ix
    if verdict == "differs" or rel not in ki.CLASS:
        keys = pair_ix.get((min(s, o), max(s, o)), [])
    else:
        k = ki.norm(rel, s, o)
        keys = key_ix.get(k if verdict == "agrees" else (k[0], k[2], k[1]), [])
    if not keys:
        return []
    by = collections.OrderedDict()
    for ck in keys:
        by.setdefault(ck.split(":")[0], []).append(ck)
    return [{"work": w, "verdict": verdict, "note": r.get("raychaudhuri_note") or "", "claims": ks[:3]}
            for w, ks in by.items()]


def _best_scholar(stmts: dict, keys: list) -> str:
    """A step's scholar: the best verdict of its statements' (agrees before differs before reversed), as /vamsa."""
    vs = [sv["verdict"] for k in keys for sv in (stmts.get(k) or {}).get("scholars", [])]
    vs = [x for x in vs if x in SCHOLAR_ORDER]
    return min(vs, key=SCHOLAR_ORDER.index) if vs else ""


def build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "") -> dict:
    """{table: [row]}: the site's rows, from the stores the dashboard's Vamsa page reads; read-only."""
    import relations_view as rv
    if immutable:
        rv.ro = ro_immutable
    import vamsa_view as vv
    g = vv._graph(db, kin_db)
    v = vv._vamsa(vamsa_db)
    names = rv._names(db)["ents"]
    canon = lambda ent: names[ent][0] if ent in names else None
    out = {t: [] for t in TABLES}

    # the sources and the texts, with their credits
    for code, title in rv.SHELF_TITLES.items():
        out["texts"].append(finish({"key": "index:" + code, "kind": "index", "code": code, "title": title,
                                    "edition": INDEX_EDITIONS.get(code, ""), "rights": INDEX_RIGHTS, "show": True}))
    for code, t in sorted(v["texts"].items()):
        out["texts"].append(finish({"key": "text:" + code, "kind": "text", "code": code, "title": t.get("title") or code,
                                    "edition": t.get("edition") or "", "rights": t.get("rights") or "",
                                    "show": bool(t.get("show"))}))
    shown_text = {c for c, t in v["texts"].items() if t.get("show")}

    # every kept relation (the model's rows), the step rows carrying the graph's joins
    joins = {}
    for rows in g["edges"].values():
        for r in rows:
            joins[r["kin_id"]] = (r.get("subject_entry"), r.get("object_entry"))
    seen_kin, rows_all = set(), []
    for rows in g["m"]["own"].values():
        for r in rows:
            if r["kin_id"] not in seen_kin:
                seen_kin.add(r["kin_id"])
                rows_all.append(r)
    rows_all.sort(key=lambda r: r["kin_id"])
    import corpus_sync as cs
    con = (ro_immutable if immutable else rv.ro)(db)
    try:
        pairs = {(r["subject_entity"], r["object_entity"]) for r in rows_all
                 if r.get("subject_entity") and r.get("object_entity") and r["subject_entity"] != r["object_entity"]}
        live = {r[1] for r in cs.live_docs(con)}
        places = _places(con, pairs, live)
    finally:
        con.close()
    works, claims, cix = _claims(claims_db, live, immutable)   # B2_SITE_2026_10_28
    out["texts"].extend(works)
    out["claims"] = claims
    key_of, stmts = {}, collections.OrderedDict()
    for r in rows_all:
        k = statement_key(r)
        key_of[r["kin_id"]] = k
        if k in stmts:
            stmts[k]["n"] += 1
            if not stmts[k]["scholars"]:
                stmts[k]["scholars"] = scholar_view(r, cix)
            continue
        x = v["rel"].get(r["kin_id"], {})
        s_entry, o_entry = joins.get(r["kin_id"], (r.get("subject_entry"), r.get("object_entry")))
        se, oe = r.get("subject_entity"), r.get("object_entity")
        stmts[k] = {"key": k, "source": r["source"], "entry_id": r["entry_id"], "head": r["head"],
                    "subject": r["subject"], "relation": r["relation"], "object": r["object"], "words": r["words"],
                    "refs": r["refs"] or [], "n": 1, "subject_entry": s_entry, "object_entry": o_entry,
                    "subject_canonical": canon(se) if se else None, "object_canonical": canon(oe) if oe else None,
                    "ours": r.get("verdict") or "", "passages": int(r.get("passages") or 0),
                    "texts": int(r.get("texts") or 0),
                    "places": places.get((se, oe), []) if (se and oe) else [],
                    "cited": x.get("cited", ""),
                    "cites": [{k2: c.get(k2) for k2 in (CITE_FIELDS if c.get("text") in shown_text else CITE_FIELDS[:5])
                               if k2 in c} for c in (x.get("cites") or [])[:6]],
                    "best_text": x.get("best_text", ""), "best_ref": x.get("best_ref", ""),
                    "together": x.get("together", {}), "scholars": scholar_view(r, cix)}
    for s in stmts.values():
        if not s["scholars"]:
            del s["scholars"]   # a relation without a scholar's view keeps the row (and the hash) it had in i1
    out["statements"] = [finish(s) for s in stmts.values()]

    # the steps, as the desk weighs them
    for (src, p, c) in sorted(g["edges"]):
        ev = vv._evidence(g, v, src, p, c)
        keys = []
        for it in ev["items"]:
            k = key_of.get(it["kin_id"])
            if k and k not in keys:
                keys.append(k)
        vk = []
        for it in ev["items"]:
            for d in it["cites"]:
                if d.get("verdict") in ("both", "one") and d.get("text") in shown_text:
                    for ref in (d.get("at") or [d.get("ref")])[:3]:
                        kk = "%s|%s" % (d["text"], ref)
                        if ref and kk not in vk:
                            vk.append(kk)
            for code in ("hv", "ram"):
                f = (it["together"].get(code) or [0, ""])[1]
                if f and code in shown_text and "%s|%s" % (code, f) not in vk:
                    vk.append("%s|%s" % (code, f))
        out["steps"].append(finish({"key": "%s:%d:%d" % (src, p, c), "source": src, "parent": p, "child": c,
                                    "joined": ev["joined"], "both_entries": bool(ev["both_entries"]),
                                    "cited": ev["cited"], "ours": ev["ours"], "epic": ev["epic"],
                                    "statements": keys, "verse_keys": vk,
                                    **({"scholar": sb} if (sb := _best_scholar(stmts, keys)) else {})}))

    # the persons: every one with a parent, a child or a spouse in the index
    nodes = set(g["par"]) | set(g["chi"])
    for n in list(nodes):
        for s in g["spouses"].get(n, ()):
            nodes.add((n[0], s))
    for (src, e) in sorted(nodes):
        pr = vv._person(g, src, e)
        has_line = (src, e) in g["par"] or (src, e) in g["chi"]
        up = vv._main_up(g, src, e) if has_line else [e]
        down = vv._main_down(g, src, e) if has_line else []
        out["persons"].append(finish({
            "key": "%s:%d" % (src, e), "source": src, "entry": e, "head": pr["head"],
            "fold": rv.split_mark(vv._hon(pr["head"]))[0], "sex": pr["sex"], "named_only": bool(pr["named_only"]),
            "has_line": has_line, "up": pr["up"], "down": pr["down"], "parents_n": pr["parents"],
            "children_n": pr["children"], "canonical": canon(pr["entity"]) if pr["entity"] else None,
            "spouses": pr["spouses"], "main_up": up[:-1], "main_down": down}))

    # the longest lines, and the verses
    for src, ls in vv.lines(db, kin_db)["lines"].items():
        for rank, ln in enumerate(ls, 1):
            out["lines"].append(finish({"key": "%s:%d" % (src, rank), "source": src, "rank": rank,
                                        "entries": ln["entries"], "heads": ln["heads"], "length": ln["length"],
                                        "both_steps": ln["both_steps"]}))
    for (t, ref), w in sorted(v["verses"].items()):
        if t in shown_text and w:
            out["verses"].append(finish({"key": "%s|%s" % (t, ref), "text": t, "ref": ref, "words": w}))

    counts = {t: len(out[t]) for t in TABLES if t != "meta"}
    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,
                                                       "checked": v["meta"].get("at", ""),
                                                       "kin": v["meta"].get("kin", "")}}))
    return out


# ---- the sinks -------------------------------------------------------------------------------------------------------
class SinkError(Exception):
    pass


class NoneSink:
    name = "none"

    def manifest(self):
        return {t: {"n": 0, "digest": digest([])} for t in TABLES}

    def keys(self, table):
        return {}


class PgSink:
    name = "pg"

    def __init__(self, dsn: str):
        import psycopg
        self.con = psycopg.connect(dsn, autocommit=True)

    def _one(self, sql: str, args: tuple):
        try:
            v = self.con.execute(sql, args).fetchone()[0]
        except Exception as e:
            raise SinkError(str(e).strip().splitlines()[0][:400])
        return json.loads(v) if isinstance(v, str) else v

    def manifest(self):
        return self._one("SELECT public.corpus_index_manifest()", ())

    def keys(self, table):
        return self._one("SELECT public.corpus_index_keys(%s)", (table,))

    def ingest(self, table, rows):
        return self._one("SELECT public.corpus_index_ingest(%s, %s::jsonb)",
                         (table, json.dumps(rows, ensure_ascii=False)))

    def delete(self, table, keys):
        return self._one("SELECT public.corpus_index_delete(%s, %s::jsonb)", (table, json.dumps(keys)))


class EdgeSink:
    name = "edge"

    def __init__(self, base_url: str, anon_key: str, secret: str, timeout: int = 150, retries: int = 3):
        self.url = base_url.rstrip("/") + "/functions/v1/corpus-index"
        self.anon, self.secret, self.timeout, self.retries = anon_key, secret, timeout, retries
        self.bytes_sent = 0

    def _call(self, payload: dict):
        import corpus_sync as cs
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        body = gzip.compress(raw, 6)
        last = None
        for attempt in range(self.retries):
            ts = str(int(time.time()))
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Content-Type": "application/octet-stream", "x-corpus-encoding": "gzip", "x-corpus-ts": ts,
                "x-corpus-sig": cs.sign(self.secret, ts, body), "apikey": self.anon,
                "Authorization": "Bearer " + self.anon})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                self.bytes_sent += len(body)
                if not data.get("ok"):
                    raise SinkError("corpus-index: %s" % str(data.get("error"))[:400])
                return data.get("result")
            except urllib.error.HTTPError as e:
                text = e.read()[:600].decode("utf-8", "replace")
                last = SinkError("corpus-index HTTP %d: %s" % (e.code, text))
                if e.code == 404:
                    raise SinkError("corpus-index is not deployed yet (HTTP 404): ask Lovable to deploy "
                                    "supabase/functions/corpus-index as it is")
                if e.code in (429, 500, 502, 503, 504) and attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = SinkError("corpus-index unreachable: %s" % e)
                if attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
        raise last or SinkError("corpus-index: no answer")

    def manifest(self):
        return self._call({"action": "manifest"})

    def keys(self, table):
        return self._call({"action": "keys", "table": table})

    def ingest(self, table, rows):
        return self._call({"action": "ingest", "table": table, "rows": rows})

    def delete(self, table, keys):
        return self._call({"action": "delete", "table": table, "keys": keys})


_NOT_READY = ("not deployed yet", "pgrst202", "could not find the function", "schema cache", "does not exist")


def not_ready(message: str) -> bool:
    """True when the site cannot take the rows yet: corpus-index not deployed (HTTP 404) or C21 not pasted (the
    function is not there); the scheduled tick waits quietly for both instead of failing every night."""
    m = (message or "").lower()
    return any(k in m for k in _NOT_READY)


def make_sink(kind: str, dsn: str = ""):
    import corpus_sync as cs
    cfg = cs.load_config()
    if kind == "auto":
        kind = "edge" if cfg.get("secret") else "none"
    if kind == "none":
        return NoneSink()
    if kind == "pg":
        d = dsn or cfg.get("dsn")
        if not d:
            raise SystemExit("--sink pg needs --dsn or CORPUS_SYNC_DSN")
        return PgSink(d)
    if kind == "edge":
        missing = [n for n, k in (("CORPUS_SYNC_SECRET", "secret"), ("the site URL", "url"),
                                  ("the publishable key", "anon")) if not cfg.get(k)]
        if missing:
            raise SystemExit("edge sink is not configured: missing %s" % ", ".join(missing))
        return EdgeSink(cfg["url"], cfg["anon"], cfg["secret"])
    raise SystemExit("unknown sink %r" % kind)


def chunks(rows: list):
    cur, size = [], 2
    for r in rows:
        n = len(json.dumps(r, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1
        if cur and (size + n > MAX_BYTES or len(cur) >= MAX_ROWS):
            yield cur
            cur, size = [], 2
        cur.append(r)
        size += n
    if cur:
        yield cur


def without_claims(rows: dict) -> dict:
    """The rows as a site without C23 stores them: no scholars' verdicts on the statements and the steps (C21's ingest
    has no column for them). Their hashes are then the ones such a site keeps, so once C23 is pasted they differ and
    the rows go again with the verdicts (else a site that took them before C23 would never get the verdicts)."""
    out = dict(rows)
    for t, field in (("statements", "scholars"), ("steps", "scholar")):
        out[t] = [finish({k: v for k, v in r.items() if k not in (field, "row_hash")}) for r in rows.get(t, [])]
    return out


def sync(rows: dict, sink, apply: bool, log=print) -> dict:
    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,
    and the keys the desk no longer has are deleted. The run's row (meta) goes last."""
    man = sink.manifest() or {}
    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": []}
    if not all(t in man for t in OPTIONAL):
        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet
    for t in TABLES:
        if t in OPTIONAL and t not in man:
            got["waiting"].append(t)   # B2_SITE_2026_10_28: the site has no such table yet (C23 not pasted)
            log("  %-10s here %6d, the site has no table for them yet (C23): left for later" % (t, len(rows.get(t, []))))
            continue
        mine = {r["key"]: r for r in rows.get(t, [])}
        d = digest((k, r["row_hash"]) for k, r in mine.items())
        there = man.get(t) or {}
        if there.get("digest") == d and int(there.get("n") or 0) == len(mine):
            got["tables"][t] = {"here": len(mine), "there": len(mine), "send": 0, "delete": 0}
            continue
        try:
            keys = sink.keys(t) or {}
        except SinkError as e:
            if t in OPTIONAL and "unknown table" in str(e):
                got["waiting"].append(t)   # corpus-index not yet deployed again with the table
                log("  %-10s corpus-index does not take them yet (deploy it again): left for later" % t)
                continue
            raise
        send = [r for k, r in mine.items() if keys.get(k) != r["row_hash"]]
        gone = sorted(k for k in keys if k not in mine)
        got["tables"][t] = {"here": len(mine), "there": len(keys), "send": len(send), "delete": len(gone)}
        log("  %-10s here %6d, there %6d: %d to send, %d to delete" % (t, len(mine), len(keys), len(send), len(gone)))
        if not apply:
            continue
        for part in chunks(send):
            res = sink.ingest(t, part) or {}
            got["sent"] += len(part)
            got["changed"] += int(res.get("changed") or 0)
        for i in range(0, len(gone), MAX_KEYS):
            res = sink.delete(t, gone[i:i + MAX_KEYS]) or {}
            got["deleted"] += int(res.get("deleted") or 0)
    if apply:
        after = sink.manifest() or {}
        tabs = [t for t in TABLES if t not in got["waiting"]]
        bad = [t for t in tabs if (after.get(t) or {}).get("digest") !=
               digest((r["key"], r["row_hash"]) for r in rows.get(t, []))]
        got["verified"] = {"tables_equal": len(tabs) - len(bad), "tables_different": bad}
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the indexes' genealogies to the site (%s)" % MARK)
    ap.add_argument("--db", default="")
    ap.add_argument("--kin-db", default="")
    ap.add_argument("--vamsa-db", default="")
    ap.add_argument("--claims-db", default="", help="the scholars' claims (default data\\shelf\\claims.db; none there: none sent)")
    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")
    ap.add_argument("--sink", default="auto", choices=("auto", "edge", "pg", "none"))
    ap.add_argument("--dsn", default="")
    ap.add_argument("--apply", action="store_true", help="send (else the plan)")
    ap.add_argument("--status", action="store_true", help="the counts here and there")
    ap.add_argument("--dump", default="", help="write the rows to this file (.json or .json.gz); nothing sent")
    ap.add_argument("--if-configured", action="store_true",
                    help="the scheduled tick: exit 0 doing nothing until the secret, the stores, C21 and corpus-index "
                         "are all there")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    db = a.db or str(ROOT / "data" / "context.db")
    kin = a.kin_db or str(ROOT / "data" / "shelf" / "kin.db")
    vam = a.vamsa_db or str(ROOT / "data" / "shelf" / "vamsa.db")
    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")
    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))
    if a.if_configured and not a.dump and a.sink in ("auto", "edge"):
        import corpus_sync as cs
        if not cs.load_config().get("secret"):
            say("not configured: CORPUS_SYNC_SECRET is not in .env; nothing built or sent", "")
            return 0
    for p, what, how in ((db, "the database", ""), (kin, "the kinships", "python scripts\\kin_index.py --check"),
                         (vam, "the verse checks", "python scripts\\vamsa_check.py --yes")):
        if not Path(p).exists():
            say("refused: %s not found (%s)" % (what, p), how)
            return 0 if a.if_configured else 1
    t0 = time.time()
    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm)
    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}
    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)
                                                               for t in TABLES)))
    if a.dump:
        data = json.dumps(rows, ensure_ascii=False).encode("utf-8")
        Path(a.dump).parent.mkdir(parents=True, exist_ok=True)
        Path(a.dump).write_bytes(gzip.compress(data, 6) if a.dump.endswith(".gz") else data)
        say("the rows are in %s (%.1f MB); nothing sent" % (a.dump, Path(a.dump).stat().st_size / 1e6), "")
        return 0
    try:
        sink = make_sink(a.sink, a.dsn)
        got = sync(rows, sink, a.apply and not a.status)
    except SinkError as e:
        if a.if_configured and not_ready(str(e)):
            say("waiting: %s" % e, "paste docs/cloud/C21_index_site_2026-10-25.sql, then ask Lovable to deploy "
                "supabase/functions/corpus-index as it is")
            return 0
        say("stopped: %s" % e, "python scripts\\index_sync.py   (the plan, again)")
        return 1
    wait = (["the claims wait (%s): paste docs\\cloud\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "
             "supabase/functions/corpus-index again" % ", ".join(got["waiting"])] if got.get("waiting") else [])
    if a.status or not a.apply:
        todo = sum(x["send"] + x["delete"] for x in got["tables"].values())
        say("%s: %d row(s) to send or delete%s" % ("the site is current" if not todo else "the plan", todo,
                                                     " (no network: --sink none)" if sink.name == "none" else ""),
            "python scripts\\index_sync.py --apply" if todo else "", wait)
        return 0
    v = got.get("verified") or {}
    if v.get("tables_different"):
        say("sent %d row(s), deleted %d; the site differs still in %s" % (got["sent"], got["deleted"],
                                                                        ", ".join(v["tables_different"])),
            "python scripts\\index_sync.py --apply   (again: a run finishes what another left)")
        return 1
    say("sent %d row(s) (%d changed), deleted %d; the site's genealogies equal the desk's (%d tables)" % (
        got["sent"], got["changed"], got["deleted"], v.get("tables_equal", 0)),
        "open /corpus/genealogies on the site (signed in)", wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
