#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
kin_index.py  (2026-10-23)  RELATIONS_INDEX_2026_10_23

Phases R2 and R3 of docs/RELATIONS_AND_ASK_2026-10-22.md, for the three indexes of the scholars' shelf at once (the
Purana Index of V. R. Ramachandra Dikshitar, the Vedic Index of Macdonell and Keith, Soerensen's Index to the Names
in the Mahabharata): the relations between persons that each entry states (kinship, marriage, teacher and pupil,
priest and patron, rule, succession, contemporaries) read whole, kept with the entry's own words and references,
checked, and set beside our verses and beside Raychaudhuri's claims.

  read    (--yes, paid: Gemini Flash, metered, the cap asked before each call, stopped at --max-usd) the entries that
          name a kinship or a school, several to a call, into JSON: subject, relation, object, the entry's words, its
          references. A trial of --per-source entries of each index (100), or every one (--per-source 0).
  check   (free; after each read, or --check) nothing is taken on the model's word:
            words      the words must stand in the entry (exact, or close: diacritics and punctuation aside), else the
                       relation is set aside;
            direction  "son of" read as father_of (or the reverse) is set aside;
            names      the subject and the object tied to our entities as the claims are (scholar_claims.tie), the
                       entry's head by the shelf's own link;
            verses     each tied pair against entity_links (R1): named together, named near, both named but never
                       near, or one not in our texts;
            scholars   the same pair in Raychaudhuri's claims (data/shelf/claims.db): agrees, reversed, or differs.
  export  exports/kin_edges.csv (every relation and its evidence), kin_matrix.csv (relation by index, and what our
          verses say of each), kin_agreement.csv (pairs two sources state: the indexes and Raychaudhuri),
          kin_lineages.md (the father-to-son lines the tied relations make), kin_cards.md (per person: each relation
          with the index's words and references, our verses, Raychaudhuri's claim; sourced, nothing written that the
          sources do not say), kin_summary.json.

  python scripts\\kin_index.py                         the plan (free): the candidates, the trial, its price, the cap
  python scripts\\kin_index.py --yes                   the trial: 100 entries of each index (about $0.15)
  python scripts\\kin_index.py --yes --per-source 0    every candidate entry (priced by the plan first)
  python scripts\\kin_index.py --check                 free: the checks and the exports again
  python scripts\\kin_index.py --show Janamejaya       one name's relations with their evidence
  python scripts\\kin_index.py --salvage              free: the relations whole in a stored reply that was cut short

KIN_SALVAGE_2026_10_25: a reply cut short (Soerensen's longest entries ask for more relations than one answer holds:
entries 12641 and 7692, 25 Oct) keeps the relations it gives whole, and is not asked again (asked again it was cut
again: three calls of one entry, about $0.13 a run); in a call of one entry every relation is that entry's, whatever
number the model gave it ("entry": 150); an entry whose reading failed twice is not asked again unless --retry-failed
(the plan says how many); --salvage reads again, free, the failed replies already stored.

Stored in data/shelf/kin.db (beside claims.db; data/shelf/ is not committed; the Cologne shelf's terms, CC BY-NC-SA
3.0, go with it). data/context.db is only read (the shelf, our entities, entity_links) and gets the meter's row of
each call, as every paid call does. The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations
import argparse, collections, csv, datetime, hashlib, json, os, re, sqlite3, sys, time, unicodedata, urllib.parse
from pathlib import Path

MARK = "RELATIONS_INDEX_2026_10_23"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

PROMPT_VERSION = "kin-v1"
SOURCES = ("pui", "vei", "inm")
SHORT = {"pui": "Purana Index", "vei": "Vedic Index", "inm": "Soerensen, Index to the Mahabharata",
         "phai1923": "Raychaudhuri, Political History of Ancient India (1923)"}
BATCH_CHARS = 4000      # entries to one call, up to this many characters
BATCH_MAX = 12
ENTRY_MAX = 12000       # a longer entry is cut (Soerensen's longest runs to 147,000 characters)
EST_CALL = 0.0009       # $ a call: the instructions (700 tokens), the thinking (256) ...
EST_CHAR = 0.0000001    # ... plus about 0.3/3.5 of a millionth of a dollar a character of the entries
EST_ENTRY = 0.0002      # ... plus the relations written back
GIVE_UP = 2             # KIN_SALVAGE_2026_10_25: an entry whose reading failed this often is not asked again by itself
KIN_RX = re.compile(r"\b(sons?|daughters?|father|mother|wife|wives|husband|brothers?|sisters?|grand(?:son|daughter|father)"
                    r"|pupil|disciple|teacher|preceptor|king|queen|contemporar\w*|patronymic|descendant|married"
                    r"|succeeded|successor)\b", re.I)

RELATIONS = ("son_of", "daughter_of", "father_of", "mother_of", "wife_of", "husband_of", "married", "brother_of",
             "sister_of", "grandson_of", "granddaughter_of", "grandfather_of", "descendant_of", "ancestor_of",
             "pupil_of", "teacher_of", "priest_of", "patron_of", "king_of", "queen_of", "successor_of",
             "predecessor_of", "contemporary_of")
# a relation as (class, which side is the elder: "o" the object, "s" the subject, "" none: the pair is unordered)
CLASS = {"son_of": ("parent", "o"), "daughter_of": ("parent", "o"), "father_of": ("parent", "s"),
         "mother_of": ("parent", "s"), "wife_of": ("spouse", ""), "husband_of": ("spouse", ""), "married": ("spouse", ""),
         "brother_of": ("sibling", ""), "sister_of": ("sibling", ""), "grandson_of": ("lineage", "o"),
         "granddaughter_of": ("lineage", "o"), "grandfather_of": ("lineage", "s"), "descendant_of": ("lineage", "o"),
         "ancestor_of": ("lineage", "s"), "pupil_of": ("school", "o"), "teacher_of": ("school", "s"),
         "priest_of": ("priest", "s"), "patron_of": ("priest", "o"), "king_of": ("rule", "s"), "queen_of": ("rule", "s"),
         "successor_of": ("succession", "o"), "predecessor_of": ("succession", "s"), "contemporary_of": ("contemporary", "")}
PHRASE = {"son_of": ("son of", "sons of", "son,", "son)"), "daughter_of": ("daughter of", "daughters of"),
          "father_of": ("father of",), "mother_of": ("mother of",), "wife_of": ("wife of", "wives of", "queen of"),
          "husband_of": ("husband of",), "brother_of": ("brother of", "brothers of"), "sister_of": ("sister of",),
          "grandson_of": ("grandson of",), "pupil_of": ("pupil of", "disciple of", "pupils of"),
          "teacher_of": ("teacher of", "preceptor of"), "king_of": ("king of",), "successor_of": ("succeeded",
                                                                                                 "successor of")}
INVERSE = {"son_of": ("father of", "mother of"), "daughter_of": ("father of", "mother of"),
           "father_of": ("son of", "daughter of"), "mother_of": ("son of", "daughter of"),
           "pupil_of": ("teacher of", "preceptor of"), "teacher_of": ("pupil of", "disciple of"),
           "grandson_of": ("grandfather of",), "successor_of": ("predecessor of",)}
UNNAMED = re.compile(r"^(?:the\s+|a\s+|an\s+|his\s+|her\s+|their\s+)?(?:son|daughter|wife|sons|daughters|wives|"
                     r"brother|sister|father|mother|husband|child|children|descendants?)\b", re.I)
VERDICTS = ("named together", "named near", "both named, never near", "one not in our texts", "not tied")

SYSTEM = """You read entries of a printed index of names in Sanskrit literature (the index, its author and year are \
given) and list the relations between persons that each entry itself states: kinship, marriage, teacher and pupil, \
priest and patron, rule over a people or a place, succession, being contemporaries. The relations go to a database \
that checks each one against the texts the entry cites; nothing you add can be checked, so add nothing.

Return JSON: {"relations": [...]}. Each relation is an object:
 "entry": the number of the entry it comes from, as given in brackets;
 "subject": the person the relation is about, in standard IAST, as the entry names him or her: usually the entry's \
own head word; when an entry has several persons of one name (1., 2., (a), (b)), the head word followed by that \
number in brackets, e.g. "Am\u015bu (2)";
 "relation": one of RELATIONS, read as "subject is relation object": "Akr\u016bra, a son of \u015avaphalka" gives \
{"subject": "Akr\u016bra", "relation": "son_of", "object": "\u015avaphalka"}; "father of Kuru" in the entry of \
Sa\u1e43vara\u1e47a gives {"subject": "Sa\u1e43vara\u1e47a", "relation": "father_of", "object": "Kuru"};
 "object": the other person (for king_of or queen_of, the people or the place), in standard IAST, as named;
 "words": the words of the entry that state the relation, copied exactly as they stand in the entry, 2 to 25 words;
 "refs": the references the entry gives for it, as printed ("V\u0101. 96. 104", "M. 45. 28", "I, 63, 2449", \
"\u015aatapatha Br\u0101hma\u1e47a, xi. 6. 2. 1"); [] if none.

Rules. Only what the entry states, never what you know of the person. A person the entry does not name is not an \
object: "married the daughter of Ugrasena" gives nothing. A list ("his sons were Kuru, Ja\u1e45ghu and Parik\u1e63it") \
gives one relation for each named person, the entry's head as the subject ("father_of" each). A patronymic \
("descendant of Atri", "a patronymic of Vasi\u1e63\u1e6dha's descendants") gives descendant_of. A teacher in a list \
of teachers (va\u1e43\u015ba) gives pupil_of. A relation to a god or a demon is kept as the entry states it. An \
entry that states none gives nothing. Every relation has its "words"; a relation without them is not given.""" \
    .replace("RELATIONS", ", ".join(RELATIONS))

SCHEMA = """
CREATE TABLE IF NOT EXISTS kin_reads (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, entries TEXT NOT NULL,
  prompt_version TEXT, engine TEXT, status TEXT, relations INTEGER, cost_usd REAL, raw TEXT, error TEXT, note TEXT,
  at TEXT, mark TEXT);
CREATE TABLE IF NOT EXISTS kin_done (entry_id INTEGER NOT NULL, source TEXT NOT NULL, entry_sha TEXT, read_id INTEGER,
  prompt_version TEXT NOT NULL, engine TEXT NOT NULL, PRIMARY KEY (entry_id, prompt_version, engine));
CREATE TABLE IF NOT EXISTS kin (id INTEGER PRIMARY KEY AUTOINCREMENT, read_id INTEGER NOT NULL, source TEXT NOT NULL,
  entry_id INTEGER NOT NULL, head TEXT, subject TEXT, relation TEXT, object TEXT, words TEXT, refs TEXT,
  words_check TEXT, direction TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS ix_kin_entry ON kin(entry_id);
CREATE TABLE IF NOT EXISTS kin_ties (kin_id INTEGER PRIMARY KEY, subject_entity INTEGER, object_entity INTEGER,
  how_subject TEXT, how_object TEXT, verdict TEXT, passages INTEGER, texts INTEGER, places TEXT, scholar TEXT,
  scholar_note TEXT, checked_at TEXT, mark TEXT);
CREATE INDEX IF NOT EXISTS ix_kin_ties_s ON kin_ties(subject_entity);
CREATE INDEX IF NOT EXISTS ix_kin_ties_o ON kin_ties(object_entity);
"""


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    if nxt:
        print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def uri(db: str, immutable: bool) -> str:
    p = Path(db).resolve().as_posix()
    p = p if p.startswith("/") else "/" + p
    return "file://%s?mode=ro%s" % (urllib.parse.quote(p, safe="/:"), "&immutable=1" if immutable else "")


def connect_ro(db: str, immutable: bool = False):
    return sqlite3.connect(uri(db, immutable), uri=True, timeout=60)


def has(con, table: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def fold(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.sub(r"\s+", " ", s).strip()


def fold_loose(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


def strip_number(name: str) -> str:
    return re.sub(r"\s*\((?:\d{1,2}|[a-z]|[ivx]{1,4})\)\s*$", "", (name or "").strip(), flags=re.I)


def entry_text(head: str, body: str) -> str:
    return ((head or "").strip() + " " + (body or "").strip()).strip()


def entry_sha(head: str, body: str) -> str:
    return hashlib.sha256(entry_text(head, body).encode("utf-8")).hexdigest()[:16]


# ---- what is read -----------------------------------------------------------------------------------
def candidates(con, sources) -> dict:
    """{source: [(id, head, body)]}: the entries that name a kinship or a school, in a fixed order spread over the
    alphabet (by a hash of the id), so that a trial of N is the same N each time."""
    out = {}
    for src in sources:
        rows = [(i, h, b) for i, h, b in con.execute(
            "SELECT id, head, body FROM shelf_entries WHERE source = ?", (src,)) if KIN_RX.search(entry_text(h, b))]
        rows.sort(key=lambda r: hashlib.sha1(("%s:%d" % (src, r[0])).encode()).hexdigest())
        out[src] = rows
    return out


def batches(rows: list) -> list:
    out, cur, size = [], [], 0
    for r in rows:
        n = min(len(entry_text(r[1], r[2])), ENTRY_MAX)
        if cur and (size + n > BATCH_CHARS or len(cur) >= BATCH_MAX):
            out.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += n
    if cur:
        out.append(cur)
    return out


def estimate(rows: list) -> float:
    b = batches(rows)
    chars = sum(min(len(entry_text(h, x)), ENTRY_MAX) for _, h, x in rows)
    return len(b) * EST_CALL + chars * EST_CHAR + len(rows) * EST_ENTRY


def batch_prompt(src_title: str, batch: list) -> tuple:
    cut = []
    parts = []
    for k, (eid, head, body) in enumerate(batch, 1):
        t = entry_text(head, body)
        if len(t) > ENTRY_MAX:
            t = t[:ENTRY_MAX] + " [...]"
            cut.append(eid)
        parts.append("[%d] %s" % (k, t))
    return ("The index: %s.\nThe entries, each with its number in brackets and its head word first:\n\n%s"
            % (src_title, "\n\n".join(parts)), cut)


def parse_reply(text: str):
    import scholar_claims as sc
    t = (text or "").strip()
    for s in (t, sc.json_repair(t)):
        a_, b_ = s.find("{"), s.rfind("}")
        for x in (s, s[a_:b_ + 1] if 0 <= a_ < b_ else None):
            if x is None:
                continue
            try:
                d = json.loads(x, strict=False)
            except ValueError:
                continue
            if isinstance(d, list):
                d = {"relations": d}
            if isinstance(d, dict) and isinstance(d.get("relations"), list):
                return d["relations"]
    return None


def salvage(text: str):
    """KIN_SALVAGE_2026_10_25: the relations given whole in a reply cut short ({"relations": [{...}, {...}, {"entr),
    or None when there are none."""
    t = text or ""
    i = t.find('"relations"')
    if i < 0:
        return None
    j = t.find("[", i)
    if j < 0:
        return None
    dec = json.JSONDecoder(strict=False)
    out, pos = [], j + 1
    while True:
        k = t.find("{", pos)
        if k < 0:
            break
        try:
            obj, end = dec.raw_decode(t, k)
        except ValueError:
            break
        if isinstance(obj, dict):
            out.append(obj)
        pos = end
    return out or None


def _s(x, n: int) -> str:
    return re.sub(r"\s+", " ", str(x or "")).strip()[:n]


def clean_relation(d, n_entries: int):
    if not isinstance(d, dict):
        return None
    try:
        k = int(d.get("entry"))
    except (TypeError, ValueError):
        k = None
    if n_entries == 1:   # KIN_SALVAGE_2026_10_25: one entry to the call: every relation is that entry's
        k = 1
    if k is None:
        return None
    rel = _s(d.get("relation"), 40).lower().replace(" ", "_")
    subj, obj, words = _s(d.get("subject"), 120), _s(d.get("object"), 120), _s(d.get("words"), 400)
    if not (1 <= k <= n_entries) or rel not in RELATIONS or not subj or not obj or not words:
        return None
    if UNNAMED.match(obj) or fold_loose(subj) == fold_loose(obj):
        return None
    refs = d.get("refs") if isinstance(d.get("refs"), list) else []
    return {"entry": k, "subject": subj, "relation": rel, "object": obj, "words": words,
            "refs": [_s(r, 80) for r in refs if _s(r, 80)][:10]}


def words_check(words: str, text: str) -> str:
    if fold(words) and fold(words) in fold(text):
        return "exact"
    if fold_loose(words) and fold_loose(words) in fold_loose(text):
        return "close"
    return "none"


def direction_check(rel: str, words: str) -> str:
    w = fold(words)
    if any(p in w for p in PHRASE.get(rel, ())):
        return "agrees"
    if any(p in w for p in INVERSE.get(rel, ())):
        return "disagrees"
    return "unknown"


_STORES = []   # KIN_CLOSE_2026_10_24: every store this run opened; main() closes them all when the run ends


def open_store(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=60)
    con.executescript(SCHEMA)
    _STORES.append(con)
    return con


def failures(con, engine: str) -> dict:
    """KIN_SALVAGE_2026_10_25: {entry_id: failed reads} of the entries not read since, for this prompt and engine."""
    out = collections.Counter()
    done = {e for (e,) in con.execute("SELECT entry_id FROM kin_done WHERE prompt_version = ? AND engine = ?",
                                      (PROMPT_VERSION, engine))}
    for (ids,) in con.execute("SELECT entries FROM kin_reads WHERE status = 'failed' AND prompt_version = ? AND "
                              "engine = ?", (PROMPT_VERSION, engine)):
        try:
            for e in json.loads(ids or "[]"):
                if e not in done:
                    out[e] += 1
        except (TypeError, ValueError):
            continue
    return dict(out)


def keep(store, rid: int, src: str, batch: list, rels: list, engine: str) -> int:
    """KIN_SALVAGE_2026_10_25 (from read): a read's relations checked and stored, its entries marked done."""
    kept = 0
    for d in rels:
        c = clean_relation(d, len(batch))
        if not c:
            continue
        eid, head, body = batch[c["entry"] - 1]
        text = entry_text(head, body)
        store.execute("INSERT INTO kin (read_id, source, entry_id, head, subject, relation, object, words, "
                      "refs, words_check, direction, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (rid, src, eid, head, c["subject"], c["relation"], c["object"], c["words"],
                       json.dumps(c["refs"], ensure_ascii=False), words_check(c["words"], text),
                       direction_check(c["relation"], c["words"]), now()))
        kept += 1
    for eid, head, body in batch:
        store.execute("INSERT OR REPLACE INTO kin_done (entry_id, source, entry_sha, read_id, prompt_version, "
                      "engine) VALUES (?,?,?,?,?,?)", (eid, src, entry_sha(head, body), rid, PROMPT_VERSION, engine))
    store.execute("UPDATE kin_reads SET relations = ? WHERE id = ?", (kept, rid))
    return kept


def salvage_stored(store, engine: str, cands: dict) -> dict:
    """KIN_SALVAGE_2026_10_25 (--salvage, free): each failed read whose stored reply gives relations whole, kept as
    a read would keep them; its entries marked done. A read whose entries changed since (or left the candidates) stays
    as it is."""
    by_id = {r[0]: (src, r) for src, rows in cands.items() for r in rows}
    got = {"reads": 0, "salvaged": 0, "relations": 0, "entries": 0}
    for rid, src, ids, raw in store.execute("SELECT id, source, entries, raw FROM kin_reads WHERE status = 'failed' AND "
                                            "prompt_version = ? AND engine = ? ORDER BY id",
                                            (PROMPT_VERSION, engine)).fetchall():
        got["reads"] += 1
        try:
            batch = [by_id[e][1] for e in json.loads(ids or "[]")]
        except (KeyError, TypeError, ValueError):
            continue
        rels = parse_reply(raw or "") or salvage(raw or "")
        if not batch or not rels:
            continue
        kept = keep(store, rid, src, batch, rels, engine)
        store.execute("UPDATE kin_reads SET status = 'salvaged', note = trim(coalesce(note, '') || ' salvaged by "
                      "--salvage: ' || ? || ' relation objects') WHERE id = ?", (str(len(rels)), rid))
        store.commit()
        got["salvaged"] += 1
        got["relations"] += kept
        got["entries"] += len(batch)
    return got


def done_entries(con, engine: str) -> dict:
    return {e: s for e, s in con.execute("SELECT entry_id, entry_sha FROM kin_done WHERE prompt_version = ? AND "
                                         "engine = ?", (PROMPT_VERSION, engine))}


def read(a, store, todo: dict, titles: dict, caller=None) -> dict:
    """The paid part: each batch read, metered, stored; stops at the cap, at --max-usd, or after repeated failure."""
    import usage_meter
    import scholar_claims as sc
    engine = "gemini:%s" % a.model
    key = os.environ.get("GEMINI_API_KEY", "") if caller is None else "stub"
    if not key:
        return {"refuse": "GEMINI_API_KEY is not set (.env)"}
    call = caller or (lambda system, prompt: sc.rest_call(a.model, system, prompt, key, a.think))
    got = {"calls": 0, "entries": 0, "relations": 0, "failed": 0, "cost": 0.0, "stopped": ""}
    for src, rows in todo.items():
        for batch in batches(rows):
            est = estimate(batch)
            if got["cost"] + est > a.max_usd:
                got["stopped"] = "--max-usd %.2f reached (spent %.4f in this run)" % (a.max_usd, got["cost"])
                return got
            if not usage_meter.budget_ok(a.db, est):
                got["stopped"] = "the spend cap (python scripts\\set_budget.py shows it)"
                return got
            prompt, cut = batch_prompt(titles.get(src, src), batch)
            reply, resp, err, spent, rels = "", None, "", 0.0, None
            salvaged = 0   # KIN_SALVAGE_2026_10_25
            for attempt in range(3):
                t0 = time.time()
                try:
                    resp = call(SYSTEM, prompt)
                    reply, err = getattr(resp, "text", "") or "", ""
                except Exception as e:
                    err, resp = "%s: %s" % (type(e).__name__, str(e)[:300]), None
                if resp is not None:
                    spent += usage_meter.meter(kind="kinship", doc=src, engine=engine, resp=resp,
                                               in_chars=len(SYSTEM) + len(prompt), out_chars=len(reply), units=1,
                                               duration_s=time.time() - t0, ok=not err, db=a.db) or 0.0
                rels = parse_reply(reply) if not err else None
                if rels is not None:
                    break
                if not err and reply.strip():   # KIN_SALVAGE_2026_10_25: a reply cut short keeps its whole relations,
                    sal = salvage(reply)        # and is not asked again (it would be cut again)
                    if sal:
                        rels, salvaged = sal, len(sal)
                        break
                if attempt < 2 and caller is None:
                    time.sleep(2 ** (attempt + 1))
            got["calls"] += 1
            got["cost"] += spent
            ids = [r[0] for r in batch]
            status = ("salvaged" if salvaged else "ok") if rels is not None else "failed"
            note = " ".join(x for x in (("cut: %s" % ",".join(map(str, cut))) if cut else "",
                                        ("salvaged: %d relation objects of a reply cut short" % salvaged)
                                        if salvaged else "") if x)
            cur = store.execute("INSERT INTO kin_reads (source, entries, prompt_version, engine, status, relations, "
                                "cost_usd, raw, error, note, at, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                (src, json.dumps(ids), PROMPT_VERSION, engine, status, 0, spent, reply[:200000],
                                 err or ("" if rels is not None else "the reply is not the JSON asked for"),
                                 note, now(), MARK))
            rid = cur.lastrowid
            if rels is None:
                got["failed"] += 1
                store.commit()
                print("  %s: %d entries failed (%s)" % (src, len(batch), (err or "not JSON")[:100]), flush=True)
                if got["failed"] >= 5:
                    got["stopped"] = "five calls failed"
                    return got
                continue
            kept = keep(store, rid, src, batch, rels, engine)   # KIN_SALVAGE_2026_10_25: as --salvage keeps them
            store.commit()
            got["entries"] += len(batch)
            got["relations"] += kept
            print("  %s: %d entries, %d relations, $%.4f" % (src, len(batch), kept, spent), flush=True)
    return got


# ---- the checks -------------------------------------------------------------------------------------
def current(store) -> list:
    """The relations of each entry's latest read."""
    return store.execute("""SELECT k.id, k.source, k.entry_id, k.head, k.subject, k.relation, k.object, k.words, k.refs,
                                   k.words_check, k.direction
                            FROM kin k JOIN kin_done d ON d.entry_id = k.entry_id AND d.read_id = k.read_id
                            ORDER BY k.id""").fetchall()


def norm(rel: str, s: int, o: int) -> tuple:
    cls, elder = CLASS[rel]
    if not elder:
        return (cls, min(s, o), max(s, o))
    return (cls, o, s) if elder == "o" else (cls, s, o)


def link_lookup(con):
    """(get(a, b) -> {rel: (passages, texts, places)}, the entities named in our live texts)."""
    mentioned = {e for (e,) in con.execute(
        "SELECT DISTINCT m.entity_id FROM entity_mentions m JOIN passages p ON p.id = m.passage_id "
        "JOIN docs d ON d.id = p.doc_id WHERE d.code NOT LIKE '%-RETIRED'")}
    if has(con, "entity_links"):
        def get(a, b):
            out = {}
            for rel, n, t, pl in con.execute("SELECT rel, passages, texts, places FROM entity_links WHERE a = ? AND "
                                             "b = ?", (min(a, b), max(a, b))):
                out[rel] = (n, t, ["%s %s" % (p[1], p[2]) for p in json.loads(pl or "[]")])
            return out
        return get, mentioned, "the table entity_links"
    import entity_links as el
    c = el.compute(con)

    def get2(a, b):
        out = {}
        for rel in ("together", "near"):
            v = c["links"].get((min(a, b), max(a, b), rel))
            if v:
                out[rel] = (len(v[0]), len(v[1]), ["%s %s" % (p[1], p[2]) for p in v[2]])
        return out
    return get2, mentioned, "counted now (entity_links.py --apply stores them)"


def claims_index(path: str) -> dict:
    """{normalized key or (pair): [(relation, page, claim)]} from Raychaudhuri's claims, when claims.db is here."""
    out = {"key": collections.defaultdict(list), "pair": collections.defaultdict(list)}
    if not path or not Path(path).exists():
        return out
    cl = connect_ro(path)
    try:
        if not (has(cl, "claims") and has(cl, "claim_links")):
            return out
        sides = collections.defaultdict(lambda: {"subject": set(), "object": set()})
        for cid, role, eid in cl.execute("SELECT claim_id, role, entity_id FROM claim_links"):
            if role in sides[cid]:
                sides[cid][role].add(eid)
        claims = {r[0]: r for r in cl.execute("SELECT id, printed, relation, claim FROM claims")}
    finally:
        cl.close()
    for cid, sd in sides.items():
        r = claims.get(cid)
        if not r:
            continue
        for s in sd["subject"]:
            for o in sd["object"]:
                if s == o:
                    continue
                out["pair"][(min(s, o), max(s, o))].append((r[2], r[1], r[3]))
                if r[2] in CLASS:
                    out["key"][norm(r[2], s, o)].append((r[2], r[1], r[3]))
    return out


def scholar_view(ci: dict, rel: str, s: int, o: int) -> tuple:
    k = norm(rel, s, o)
    if ci["key"].get(k):
        r = ci["key"][k][0]
        return "agrees", "p. %s: %s" % (r[1], r[2])
    if k[2] != k[1] and ci["key"].get((k[0], k[2], k[1])) and CLASS[rel][1]:
        r = ci["key"][(k[0], k[2], k[1])][0]
        return "reversed", "p. %s: %s" % (r[1], r[2])
    other = ci["pair"].get((min(s, o), max(s, o)))
    if other:
        r = other[0]
        return "differs", "p. %s (%s): %s" % (r[1], r[0], r[2])
    return "", ""


def check(a, store, root: Path, write: bool = True) -> dict:
    import scholar_claims as sc
    con = connect_ro(a.db, a.immutable)
    try:
        idx, names, _ = sc.entity_index(a.db, a.immutable)
        link_of = collections.defaultdict(set)
        if has(con, "shelf_links"):
            for e, x in con.execute("SELECT entry_id, entity_id FROM shelf_links"):
                link_of[e].add(x)
        get, mentioned, how_links = link_lookup(con)
        titles = dict(con.execute("SELECT code, title FROM shelf_sources")) if has(con, "shelf_sources") else {}
        ci = claims_index(a.claims_db)
        heads = heads_index(con)   # KIN_LINES_2026_10_24

        def tie(name: str, entry_id: int, head: str):
            base = strip_number(name)
            if fold_loose(base) == fold_loose(strip_number(head)) and len(link_of.get(entry_id, ())) == 1:
                return next(iter(link_of[entry_id])), "entry"
            how, ids = sc.tie(base, idx)
            if len(ids) == 1:
                return ids[0], how
            return None, ("many" if ids else "")

        rows, at = [], now()
        store.execute("DELETE FROM kin_ties")
        for kid, src, eid, head, subj, rel, obj, words, refs, wcheck, direc in current(store):
            s, hs = tie(subj, eid, head)
            o, ho = tie(obj, eid, "")
            ok = wcheck in ("exact", "close") and direc != "disagrees"
            verdict, n, t, pl, sch, note = "not tied", 0, 0, [], "", ""
            if s and o and s != o:
                lk = get(s, o)
                if "together" in lk:
                    verdict, (n, t, pl) = "named together", lk["together"]
                elif "near" in lk:
                    verdict, (n, t, pl) = "named near", lk["near"]
                elif s in mentioned and o in mentioned:
                    verdict = "both named, never near"
                else:
                    verdict = "one not in our texts"
                sch, note = scholar_view(ci, rel, s, o)
            store.execute("INSERT INTO kin_ties (kin_id, subject_entity, object_entity, how_subject, how_object, verdict, "
                          "passages, texts, places, scholar, scholar_note, checked_at, mark) VALUES "
                          "(?,?,?,?,?,?,?,?,?,?,?,?,?)", (kid, s, o, hs, ho, verdict, n, t, json.dumps(pl), sch, note,
                                                          at, MARK))
            rows.append({"kin_id": kid, "source": src, "index": SHORT.get(src, src), "entry_id": eid, "head": head,
                         "subject": subj, "relation": rel, "object": obj, "words": words,
                         "refs": "; ".join(json.loads(refs or "[]")), "words_check": wcheck, "direction": direc,
                         "kept": ok, "subject_entity": s, "subject_name": names.get(s, ("",))[0] if s else "",
                         "object_entity": o, "object_name": names.get(o, ("",))[0] if o else "", "verdict": verdict,
                         "passages": n, "texts": t, "places": "; ".join(pl), "raychaudhuri": sch,
                         "raychaudhuri_note": note})
        store.commit()
    finally:
        con.close()
    summary = summarize(rows, how_links, titles)
    if write:
        export(root, rows, summary, heads)
    return summary


def summarize(rows: list, how_links: str, titles: dict) -> dict:
    by_src = collections.defaultdict(collections.Counter)
    matrix = collections.defaultdict(collections.Counter)
    for r in rows:
        c = by_src[r["source"]]
        c["relations"] += 1
        c["words " + r["words_check"]] += 1
        c["direction " + r["direction"]] += 1
        if r["kept"]:
            c["kept"] += 1
            c["tied"] += 1 if r["verdict"] != "not tied" else 0
            c[r["verdict"]] += 1
            if r["raychaudhuri"]:
                c["raychaudhuri " + r["raychaudhuri"]] += 1
            matrix[(r["relation"], r["source"])][r["verdict"]] += 1
    return {"mark": MARK, "links": how_links, "titles": titles, "by_source": {k: dict(v) for k, v in by_src.items()},
            "matrix": {"%s|%s" % k: dict(v) for k, v in matrix.items()}, "relations": len(rows)}


def lineages(rows: list, min_len: int = 4, top: int = 25) -> list:
    """The father-to-son lines the kept, tied parent relations make: (chain of entity names, the edges' sources).
    KIN_LINES_2026_10_24: NOT used for the export any more. It joins the relations by OUR entity ids, and one id stands
    for every homonym of a name (among the entries read, 1,036 names are borne by more than one entry of the same
    index), so its lines jump
    from one person to another of the same name (a 40-step line from Narayana through Karna to Asvatthaman, 24 Oct).
    lines() below joins only the index's own entries."""
    child = collections.defaultdict(set)
    has_parent = set()
    name, src = {}, collections.defaultdict(set)
    for r in rows:
        if not r["kept"] or not (r["subject_entity"] and r["object_entity"]) or CLASS[r["relation"]][0] != "parent":
            continue
        _, p, c = norm(r["relation"], r["subject_entity"], r["object_entity"])
        child[p].add(c)
        has_parent.add(c)
        name[r["subject_entity"]], name[r["object_entity"]] = r["subject_name"], r["object_name"]
        src[(p, c)].add(r["source"])
    best, steps = [], 0
    for root_ in sorted(p for p in child if p not in has_parent):
        stack = [[root_]]
        while stack and steps < 200000:          # a bound: the Puranic lines branch at every generation
            steps += 1
            path = stack.pop()
            nxt = [c for c in child.get(path[-1], ()) if c not in path]
            if not nxt or len(path) >= 40:
                if len(path) >= min_len:
                    best.append(path)
                continue
            stack.extend(path + [c] for c in sorted(nxt, reverse=True))
    best.sort(key=lambda p: -len(p))
    out, seen = [], set()
    for p in best:
        k = tuple(p)
        if any(set(k) <= set(s) for s in seen):
            continue
        seen.add(k)
        out.append(([name.get(e, str(e)) for e in p],
                    [",".join(sorted(src[(p[i], p[i + 1])])) for i in range(len(p) - 1)]))
        if len(out) >= top:
            break
    return out


# ---- KIN_LINES_2026_10_24: the lines of descent by the index's own entries ---------------------------------------
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman(t: str) -> int:
    t, n, prev = t.lower(), 0, 0
    for ch in reversed(t):
        v = ROMAN.get(ch, 0)
        n, prev = (n - v, prev) if v < prev else (n + v, v)
    return n


def split_mark(name: str) -> tuple:
    """(the folded name, the homonym's number or 0): "Janamejaya (II)", "Jaratkaru[2]", "3. Rsabha", "Rsabha (3)" and
    "Sraddha(devi) (IV)" (a gloss in brackets set aside) give the number the index gives its homonyms."""
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
    return fold_loose(s), mark


def heads_index(con, sources=SOURCES) -> dict:
    """{source: {folded name: [(entry id, number)]}} and {(source, entry id): the head as printed}, from the shelf."""
    by, shown = {s: collections.defaultdict(list) for s in sources}, {}
    if not has(con, "shelf_entries"):
        return {"by": by, "shown": shown}
    q = "SELECT id, source, head FROM shelf_entries WHERE source IN (%s)" % ",".join("?" * len(sources))
    for eid, src, head in con.execute(q, tuple(sources)):
        base, mark = split_mark(head)
        if base:
            by[src][base].append((eid, mark))
            shown[(src, eid)] = head
    return {"by": by, "shown": shown}


def heads_from_rows(rows: list) -> dict:
    """The same index from the rows alone (their entries' heads), when the shelf is not at hand."""
    by, shown = collections.defaultdict(lambda: collections.defaultdict(list)), {}
    for r in rows:
        k = (r["source"], r["entry_id"])
        if k in shown:
            continue
        base, mark = split_mark(r["head"])
        if base:
            by[r["source"]][base].append((r["entry_id"], mark))
            shown[k] = r["head"]
    return {"by": by, "shown": shown}


def lines(rows: list, heads: dict, min_len: int = 4, top: int = 20) -> dict:
    """{source: [(the heads elder first, the steps stated in both entries, the lines much the same left out)]}: the
    parent relations the index states,
    joined only where a person is one entry of that index. A name is that entry when the index has one entry of that
    name, or the number names one homonym, or (homonyms, no number) exactly one of them names the other person in its
    own relations. Else the line ends there. Lines never cross from one index to another."""
    by, shown = heads["by"], heads["shown"]
    par = [r for r in rows if r["kept"] and CLASS[r["relation"]][0] == "parent"]
    names_in = collections.defaultdict(set)
    for r in par:
        names_in[(r["source"], r["entry_id"])].add(split_mark(r["object"])[0])
        names_in[(r["source"], r["entry_id"])].add(split_mark(r["subject"])[0])

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

    out = {}
    for src in sorted({r["source"] for r in par}):
        child, has_parent, said = collections.defaultdict(set), set(), collections.defaultdict(set)
        for r in (x for x in par if x["source"] == src):
            hb, hm = split_mark(r["head"])
            sb, sm = split_mark(r["subject"])
            s = r["entry_id"] if sb == hb and sm in (0, hm) else resolve(src, r["subject"], hb)
            o = resolve(src, r["object"], sb)
            if s is None or o is None or s == o:
                continue
            _, p, c = norm(r["relation"], s, o)
            child[p].add(c)
            has_parent.add(c)
            said[(p, c)].add(r["entry_id"])
        best, steps = [], 0
        for root_ in sorted(p for p in child if p not in has_parent):
            stack = [[root_]]
            while stack and steps < 200000:
                steps += 1
                path = stack.pop()
                nxt = [c for c in child.get(path[-1], ()) if c not in path]
                if not nxt or len(path) >= 60:
                    if len(path) >= min_len:
                        best.append(path)
                    continue
                stack.extend(path + [c] for c in sorted(nxt, reverse=True))
        best.sort(key=lambda p: (-len(p), p))
        got, seen = [], []
        for p in best:
            sp = set(p)
            near = [i for i, q in enumerate(seen) if sp <= q or len(sp & q) >= 0.75 * len(sp)]
            if near:   # the same line again, or with one name spelt another way (Mahadrti, Mahadhrti)
                got[near[0]][2] += 1
                continue
            if len(got) >= top:
                continue
            seen.append(sp)
            both = sum(1 for i in range(len(p) - 1) if {p[i], p[i + 1]} <= said[(p[i], p[i + 1])])
            got.append([[shown.get((src, e), str(e)) for e in p], both, 0])
        out[src] = [tuple(x) for x in got]
    return out


def lines_text(found: dict) -> str:
    text = ["# Lines of descent in the indexes (KIN_LINES_2026_10_24)", "",
            "Each line joins the parent relations one index states, elder first, and only where a person is one entry "
            "of that index: the index has one entry of the name, or its number names one homonym, or exactly one "
            "homonym names the other person in its own entry. A line never jumps from one person to another of the "
            "same name, nor from one index to another. \"Both entries\" counts the steps stated by the parent's entry "
            "and by the child's. Every step is in kin_edges.csv with its words and its reference.", ""]
    for src in ("pui", "vei", "inm"):
        if src not in found:
            continue
        text.append("## %s" % SHORT.get(src, src))
        text.append("")
        if not found[src]:
            text.append("No line of four generations or more.")
        for chain, both, variants in found[src]:
            text.append("- %s  (%d generations; %d of %d steps in both entries%s)" % (
                " > ".join(chain), len(chain), both, len(chain) - 1,
                "; %d more line(s) much the same, a name spelt otherwise or a branch" % variants if variants else ""))
        text.append("")
    return "\n".join(text) + "\n"


def agreement(rows: list) -> list:
    """The pairs two sources state (two indexes, or an index and Raychaudhuri): each source's relation."""
    by_pair = collections.defaultdict(list)
    for r in rows:
        if r["kept"] and r["subject_entity"] and r["object_entity"]:
            k = (min(r["subject_entity"], r["object_entity"]), max(r["subject_entity"], r["object_entity"]))
            by_pair[k].append(r)
    out = []
    for k, rs in by_pair.items():
        srcs = {r["source"] for r in rs}
        ray = [r for r in rs if r["raychaudhuri"]]
        if len(srcs) < 2 and not ray:
            continue
        keys = {norm(r["relation"], r["subject_entity"], r["object_entity"]) for r in rs}
        state = "agree" if len(keys) == 1 else "differ"
        if ray and any(r["raychaudhuri"] in ("reversed", "differs") for r in ray):
            state = "differ"
        out.append({"a": rs[0]["subject_name"] if rs[0]["subject_entity"] == k[0] else rs[0]["object_name"],
                    "b": rs[0]["object_name"] if rs[0]["subject_entity"] == k[0] else rs[0]["subject_name"],
                    "sources": ",".join(sorted(srcs) + (["phai1923"] if ray else [])), "state": state,
                    "relations": "; ".join(sorted({"%s: %s %s %s" % (r["source"], r["subject"], r["relation"],
                                                                      r["object"]) for r in rs})),
                    "raychaudhuri": (ray[0]["raychaudhuri"] + " " + ray[0]["raychaudhuri_note"]) if ray else ""})
    out.sort(key=lambda r: (r["state"] != "differ", r["a"]))
    return out


def cards(rows: list, top: int = 80) -> str:
    """Per person, each relation with its evidence, in the order: the index's words and references, our verses,
    Raychaudhuri. Built from the sources only."""
    by = collections.defaultdict(list)
    for r in rows:
        if r["kept"] and r["subject_entity"]:
            by[r["subject_name"]].append(r)
    order = sorted(by, key=lambda n: (-sum(1 for r in by[n] if r["verdict"] in VERDICTS[:2]), -len(by[n]), n))
    lines = ["# Kinships read from the indexes, with their evidence (%s)" % MARK, "",
             "Each line: what the index says, in its own words, with its references; whether our texts name the two "
             "together (in one passage) or near (within five passages of one text); what Raychaudhuri's Political "
             "History (Part I) says of the same pair. Nothing here is the model's own: a relation whose words are not "
             "in the entry, or whose direction the words contradict, is left out.", ""]
    for n in order[:top]:
        lines.append("## %s" % n)
        lines.append("")
        for r in sorted(by[n], key=lambda r: (VERDICTS.index(r["verdict"]), r["relation"])):
            obj = r["object_name"] or r["object"]
            ev = {"named together": "our texts name both together in %d passage(s) of %d text(s): %s",
                  "named near": "our texts name both within five passages, %d passage(s) of %d text(s): %s",
                  }.get(r["verdict"])
            ours = (ev % (r["passages"], r["texts"], r["places"])) if ev else {
                "both named, never near": "our texts name both, never near each other",
                "one not in our texts": "one of the two is not named in our texts yet",
                "not tied": "the names are not yet tied to ours"}[r["verdict"]]
            ray = ""
            if r["raychaudhuri"]:
                ray = " Raychaudhuri %s: %s." % ({"agrees": "agrees", "reversed": "states the reverse",
                                                   "differs": "relates them otherwise"}[r["raychaudhuri"]],
                                                  r["raychaudhuri_note"].rstrip("."))
            lines.append("- **%s %s.** %s, s.v. %s: \"%s\"%s. %s.%s" % (
                r["relation"].replace("_", " "), obj, r["index"], r["head"], r["words"],
                (" (%s)" % r["refs"]) if r["refs"] else "", ours[:1].upper() + ours[1:], ray))
        lines.append("")
    return "\n".join(lines) + "\n"


def export(root: Path, rows: list, summary: dict, heads: dict = None):
    out = root / "exports"
    out.mkdir(parents=True, exist_ok=True)
    cols = ["kin_id", "source", "index", "entry_id", "head", "subject", "relation", "object", "words", "refs",
            "words_check", "direction", "kept", "subject_entity", "subject_name", "object_entity", "object_name",
            "verdict", "passages", "texts", "places", "raychaudhuri", "raychaudhuri_note"]
    with open(out / "kin_edges.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out / "kin_matrix.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["relation", "index"] + list(VERDICTS) + ["kept"])
        for k in sorted(summary["matrix"]):
            rel, src = k.split("|")
            v = summary["matrix"][k]
            w.writerow([rel, SHORT.get(src, src)] + [v.get(x, 0) for x in VERDICTS] + [sum(v.values())])
    ag = agreement(rows)
    with open(out / "kin_agreement.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["a", "b", "sources", "state", "relations", "raychaudhuri"])
        w.writeheader()
        for r in ag:
            w.writerow(r)
    found = lines(rows, heads if heads and heads.get("shown") else heads_from_rows(rows))   # KIN_LINES_2026_10_24
    lin = [x for v in found.values() for x in v]
    (out / "kin_lineages.md").write_text(lines_text(found), encoding="utf-8")
    (out / "kin_cards.md").write_text(cards(rows), encoding="utf-8")
    summary = dict(summary, agreement=collections.Counter(r["state"] for r in ag), lineages=len(lin))
    (out / "kin_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


def show(a, store, who: str) -> int:
    rows = store.execute("""SELECT k.source, k.head, k.subject, k.relation, k.object, k.words, k.refs, t.verdict,
                                   t.places, t.scholar, t.scholar_note
                            FROM kin k JOIN kin_done d ON d.entry_id = k.entry_id AND d.read_id = k.read_id
                            LEFT JOIN kin_ties t ON t.kin_id = k.id""").fetchall()
    f = fold_loose(who)
    hit = [r for r in rows if f in (fold_loose(strip_number(r[2])), fold_loose(strip_number(r[4])))]
    print("%s: %d relation(s) name %s" % (MARK, len(hit), who))
    for r in hit:
        print("  [%s] %s %s %s  \"%s\" (%s)  ours: %s%s%s" % (r[0], r[2], r[3], r[4], r[5][:90], "; ".join(
            json.loads(r[6] or "[]"))[:60], r[7] or "unchecked", (" " + json.loads(r[8] or "[]")[0]) if r[8] and
            json.loads(r[8] or "[]") else "", ("  Raychaudhuri %s %s" % (r[9], r[10][:80])) if r[9] else ""))
    return 0


def budget_left(db: str, immutable: bool) -> str:
    try:
        con = connect_ro(db, immutable)
        try:
            b, s, p = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
        finally:
            con.close()
        return "the cap: $%.2f spent of $%.2f, $%.2f left%s" % (s, b, b - s, " (paused)" if p else "")
    except Exception:
        return "the cap: not read"


def main(argv=None, caller=None) -> int:
    """KIN_CLOSE_2026_10_24: the run is run(); the stores it opened are closed here, whatever it returned or raised.
    Windows will not delete, replace or back up a file that is still open, and the tests call main() in-process."""
    try:
        return run(argv, caller)
    finally:
        while _STORES:
            try:
                _STORES.pop().close()
            except sqlite3.Error:
                pass


def run(argv=None, caller=None) -> int:
    ap = argparse.ArgumentParser(description="the indexes' kinships read and checked (%s)" % MARK)
    ap.add_argument("--db", default="")
    ap.add_argument("--immutable", action="store_true")
    ap.add_argument("--root", default="")
    ap.add_argument("--kin-db", default="")
    ap.add_argument("--claims-db", default="")
    ap.add_argument("--source", default="all", choices=("all",) + SOURCES)
    ap.add_argument("--per-source", type=int, default=100, help="entries of each index (0: every candidate)")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--think", type=int, default=256)
    ap.add_argument("--max-usd", type=float, default=0.50)
    ap.add_argument("--yes", action="store_true", help="read (paid; metered; the cap asked before each call)")
    ap.add_argument("--check", action="store_true", help="free: the checks and the exports")
    ap.add_argument("--show", default="")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--salvage", action="store_true",   # KIN_SALVAGE_2026_10_25
                    help="free: the relations given whole in the stored replies that failed (a reply cut short)")
    ap.add_argument("--retry-failed", action="store_true",
                    help="ask again the entries whose reading failed %d times (KIN_SALVAGE_2026_10_25)" % GIVE_UP)
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    root = Path(a.root).resolve() if a.root else ROOT
    a.db = a.db or str(root / "data" / "context.db")
    a.kin_db = a.kin_db or str(root / "data" / "shelf" / "kin.db")
    a.claims_db = a.claims_db or str(root / "data" / "shelf" / "claims.db")
    if caller is None:
        try:
            from env_loader import load_env
            load_env()
        except Exception:
            pass
    if a.model.startswith(("claude", "anthropic")):
        say("this tool reads with Gemini (Google's cap): --model names a Gemini model")
        return 2
    if not Path(a.db).exists():
        print("%s: no database at %s" % (MARK, a.db))
        return 2
    con = connect_ro(a.db, a.immutable)
    try:
        if not has(con, "shelf_entries"):
            say("the database has no shelf (scripts\\scholar_shelf.py loads it)")
            return 2
        sources = SOURCES if a.source == "all" else (a.source,)
        cands = candidates(con, sources)
        titles = dict(con.execute("SELECT code, title FROM shelf_sources")) if has(con, "shelf_sources") else {}
        authors = {}
        if has(con, "shelf_sources"):
            authors = {c: "%s, by %s (%s)" % (t, au, y) for c, t, au, y in con.execute(
                "SELECT code, title, authors, year FROM shelf_sources")}
    finally:
        con.close()
    if a.show:
        if not Path(a.kin_db).exists():
            say("nothing read yet", "python scripts\\kin_index.py   (the plan)")
            return 0
        return show(a, open_store(a.kin_db), a.show)
    engine = "gemini:%s" % a.model
    store = open_store(a.kin_db) if (a.yes or a.check or a.salvage or Path(a.kin_db).exists()) else None
    if store is not None and a.salvage:   # KIN_SALVAGE_2026_10_25: free, before the plan
        sv = salvage_stored(store, engine, cands)
        print("salvage: %d failed read(s) stored; %d salvaged: %d entries, %d relations kept (free)" % (
            sv["reads"], sv["salvaged"], sv["entries"], sv["relations"]))
    done = done_entries(store, engine) if store else {}
    fails = failures(store, engine) if store else {}   # KIN_SALVAGE_2026_10_25
    todo, planned, given_up = {}, 0.0, 0
    for src in sources:
        rows = cands[src]
        pick = rows if a.per_source <= 0 else rows[:a.per_source]
        left = [r for r in pick if done.get(r[0]) != entry_sha(r[1], r[2])]
        gave = [r for r in left if fails.get(r[0], 0) >= GIVE_UP and not a.retry_failed]
        if gave:   # KIN_SALVAGE_2026_10_25: not asked again by themselves
            left = [r for r in left if r not in gave]
            given_up += len(gave)
        todo[src] = left
        planned += estimate(left)
        print("  %-44s %6d candidate entries; this run %d (%d read already); about $%.2f%s" % (
            SHORT.get(src, src)[:44], len(rows), len(left), len(pick) - len(left) - len(gave), estimate(left),
            ("; %d given up after %d failed reads" % (len(gave), GIVE_UP)) if gave else ""))
    if given_up:
        print("  %d entr%s given up: python scripts\\kin_index.py --salvage (free) keeps what their replies give; "
              "--retry-failed asks again" % (given_up, "y" if given_up == 1 else "ies"))
    print("%s: %d entries to read, about $%.2f in all; %s" % (MARK, sum(len(v) for v in todo.values()), planned,
                                                               budget_left(a.db, a.immutable)))
    if a.yes:
        got = read(a, store, todo, authors, caller)
        if got.get("refuse"):
            say("nothing was read: " + got["refuse"])
            return 1
        print("read: %d call(s), %d entries, %d relations, %d failed, $%.4f%s" % (
            got["calls"], got["entries"], got["relations"], got["failed"], got["cost"],
            ("; stopped: " + got["stopped"]) if got["stopped"] else ""))
    if store is None:
        full = a.per_source <= 0
        say("nothing read yet; %s costs about $%.2f" % ("every candidate entry" if full else "the trial", planned),
            "python scripts\\kin_index.py --yes%s   (%s; --max-usd %.2f)" % (
                " --per-source %d" % a.per_source if a.per_source != 100 else "",
                "every candidate entry" if full else "the trial: %d entries of each index" % a.per_source, a.max_usd))
        return 0
    s = check(a, store, root, write=not a.no_write)
    for src, c in s["by_source"].items():
        print("  %-44s %5d relations: words exact %d, close %d, none %d; direction against %d; kept %d, tied %d: "
              "together %d, near %d, never near %d, not ours %d; Raychaudhuri agrees %d, reverses %d, differs %d" % (
                  SHORT.get(src, src)[:44], c.get("relations", 0), c.get("words exact", 0), c.get("words close", 0),
                  c.get("words none", 0), c.get("direction disagrees", 0), c.get("kept", 0), c.get("tied", 0),
                  c.get("named together", 0), c.get("named near", 0), c.get("both named, never near", 0),
                  c.get("one not in our texts", 0), c.get("raychaudhuri agrees", 0), c.get("raychaudhuri reversed", 0),
                  c.get("raychaudhuri differs", 0)))
    if not a.no_write:
        print("written: %s (kin_edges.csv, kin_matrix.csv, kin_agreement.csv, kin_lineages.md, kin_cards.md, "
              "kin_summary.json)" % (root / "exports"))
    kept = sum(c.get("kept", 0) for c in s["by_source"].values())
    tied = sum(c.get("tied", 0) for c in s["by_source"].values())
    left = sum(len(v) for v in todo.values()) if not a.yes else 0
    unread = sum(1 for src in sources for r in cands[src] if done.get(r[0]) != entry_sha(r[1], r[2])) \
        if not a.yes else -1   # KIN_LINES_2026_10_24: the full run's NEXT only while entries are unread
    say("%d relations read, %d kept after the checks, %d tied to our names; our verses checked by %s" % (
        s["relations"], kept, tied, s["links"]),
        "read exports\\kin_cards.md and kin_agreement.csv; then the full run: python scripts\\kin_index.py --yes "
        "--per-source 0 --max-usd 4.50 (the plan prices it first: about $4)" if a.per_source and unread != 0 else
        "read exports\\kin_lineages.md and kin_cards.md; one name: python scripts\\kin_index.py --show Janamejaya",
        ["%d entries %s are not read yet: python scripts\\kin_index.py --yes%s" % (   # KIN_ALSO_2026_10_24
            left, "of the trial" if a.per_source else "in all",
            "" if a.per_source == 100 else " --per-source %d --max-usd %.2f (twice the plan: long entries cost more)" % (
                a.per_source, max(a.max_usd, round(planned * 2 + 0.005, 2))))] if left else [])
    return 0


if __name__ == "__main__":
    sys.exit(main())
