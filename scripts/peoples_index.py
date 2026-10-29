#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
peoples_index.py  (2026-10-28)  PEOPLES_2026_10_28

The peoples of ancient India as the Puranas list them, the first step of carrying H. C. Raychaudhuri's work on to the
peoples and tribes (the asks of 25 and 28 Oct: "our own correlations", "carrying forward Raychaudhuri's work and
correlating it with the tribes of ancient India"). Free: no model is called; every database is only read.

  The lists   The Puranas' account of the lands of Bharatavarsa names its peoples (janapadas) region by region:
              Matsya 114.34-56, Brahmanda II.16.40-68 (GRETIL's part 1, chapter 16), Vayu 45.109-137 and, in short,
              Visnu II.3.15-17. The regions are the texts' own words: the Matsya closes its first list with
              "madhyadesa janapadah" (114.36), the northern with "ete desa udicyah" (43), the eastern with "pracya
              janapadah" (45), opens the southern with "daksinapathavasinah" (46) and closes the western with "ity
              ete aparantah" (51), with no boundary between those two; then "vindhyaprsthanivasinah" (54) and
              "parvatasrayinah" (55). The Brahmanda marks the same seven, the southern and the western apart (55,
              59). Chapter by chapter the verses are numbered as GRETIL's TEI numbers them.
  Who is in   An entry of V. R. Ramachandra Dikshitar's Purana Index (1951-55; data/context.db's shelf_entries,
              the Cologne edition, CC BY-NC-SA 3.0) that cites a verse of those lists: his citations, not ours,
              decide who is a people of the lists. Entries of one name (Kuntala (II) and Kuntalas) are one row.
  The verse   Each cited verse of a text we hold (the Matsya, the Brahmanda, the Visnu in both editions: GRETIL's
              TEI, CC BY-NC-SA 4.0) is read for the name as vamsa_check.py reads one (VAMSA_CHECK_2026_10_25: the
              verse and two either side, a name inside a compound as the prints join them); the region is the one
              of the verse it stands in. The Vayu is not in GRETIL (only the Revakhanda ascribed to it): its
              citations are counted, "not held".
  Ours        The entry's tie to our names (shelf_links), and how often our live texts name them (entity_mentions).
  The scholar What Raychaudhuri's Political History of Ancient India (1923; data/shelf/claims.db, the latest read of
              each page, the quotation found on the page) says of the same names: his claims, with page and relation.
              Part I only until scholar_claims.py --part 2 has read Part II (CLAIMS_PART2_2026_10_28).

It is a concordance, not a reading: "named in the verse" says where to read, and the region is the list's, as the text
words it; what the verse, the index and the historian each say is kept apart, and nothing is inferred here. Where
the Matsya and the Brahmanda place one people in different regions, or Raychaudhuri says where a people lived, the
row says so, for a person or the Professor to weigh.

B. C. Law's Tribes in Ancient India (1943) is in copyright in India to the end of 2029: it is not read here. Read
from a copy held lawfully, its statements may go into claims.db as private reading (index_sync.py sends only the
public-domain works to the site); from 1 Jan 2030 it may be read as Raychaudhuri is.

  python scripts\\peoples_index.py                    the report; nothing written
  python scripts\\peoples_index.py --yes              and written: data\\shelf\\peoples_index.json and .csv
                                                      (data\\shelf\\ stays on this PC, as the Cologne shelf does)
  python scripts\\peoples_index.py --name Kekaya      one people's row
  python scripts\\peoples_index.py --db D:\\backups\\x.db --immutable   read a backup

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations

import argparse, collections, csv, datetime, json, re, sqlite3, sys, urllib.parse, zipfile
from pathlib import Path

MARK = "PEOPLES_2026_10_28"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import vamsa_check as vc   # noqa: E402  the reading of a name in a verse (VAMSA_CHECK_2026_10_25)

# The lists: Dikshitar's citation of the text and chapter -> the verses of the list (as he numbers them)
LISTS = collections.OrderedDict([
    ("m", {"title": "Matsyapur\u0101\u1e47a 114", "where": (114,),
           "verses": tuple(range(34, 37)) + tuple(range(40, 57)), "held": True}),
    ("br", {"title": "Brahm\u0101\u1e47\u1e0dapur\u0101\u1e47a II.16 (GRETIL: part 1, chapter 16)", "where": (2, 16),
            "verses": (40, 41, 42) + tuple(range(46, 66)) + (67, 68), "held": True}),
    ("vi", {"title": "Vi\u1e63\u1e47upur\u0101\u1e47a II.3", "where": (2, 3), "verses": (15, 16, 17), "held": True}),
    ("va", {"title": "V\u0101yupur\u0101\u1e47a 45", "where": (45,), "verses": tuple(range(109, 138)), "held": False}),
])
MADHYA, UDICYA, PRACYA = "madhyade\u015ba", "ud\u012bcya", "pr\u0101cya"
DAKSINA, APARANTA = "dak\u1e63i\u1e47\u0101patha", "apar\u0101nta"
VINDHYA, PARVATA = "vindhyap\u1e5b\u1e63\u1e6dha", "parvat\u0101\u015braya"
REGION_ORDER = (MADHYA, UDICYA, PRACYA, DAKSINA, APARANTA, VINDHYA, PARVATA)
# the regions of GRETIL's verses, from the words that open or close each list (read on 28 Oct); a verse not here
# (the Matsya's 37-39 and the Brahmanda's 43-45 and 66: Govardhana and the Godavari, the closing words) has none
REGIONS = {
    "m": [((114, 34), (114, 36), (MADHYA,)), ((114, 40), (114, 43), (UDICYA,)), ((114, 44), (114, 45), (PRACYA,)),
          ((114, 46), (114, 51), (DAKSINA, APARANTA)), ((114, 52), (114, 54), (VINDHYA,)),
          ((114, 55), (114, 56), (PARVATA,))],
    "br": [((1, 16, 40), (1, 16, 42), (MADHYA,)), ((1, 16, 46), (1, 16, 50), (UDICYA,)),
           ((1, 16, 51), (1, 16, 55), (PRACYA,)), ((1, 16, 56), (1, 16, 59), (DAKSINA,)),
           ((1, 16, 60), (1, 16, 62), (APARANTA,)), ((1, 16, 63), (1, 16, 65), (VINDHYA,)),
           ((1, 16, 67), (1, 16, 68), (PARVATA,))],
}
# the words that name a region where it opens or closes, as GRETIL prints them: never taken for a people's name
# (the Matsya's "ity ete aparantas tu" closes the western list; the Brahmanda's 46 names a people Aparanta)
MARKERS = {
    "m": {(114, 36): ("madhyade\u015b\u0101",), (114, 43): ("ud\u012bcy\u0101stu", "pr\u0101cy\u0101nde\u015b\u0101nnibodhata"),
          (114, 45): ("pr\u0101cy\u0101",), (114, 46): ("dak\u1e63i\u1e47\u0101pathav\u0101sina\u1e25",),
          (114, 51): ("apar\u0101nt\u0101stu", "vindhyav\u0101sina\u1e25"), (114, 54): ("vindhyap\u1e5b\u1e63\u1e6dhaniv\u0101sina\u1e25",),
          (114, 55): ("parvat\u0101\u015brayi\u1e47a\u015bca",)},
    "br": {(1, 16, 42): ("madhyade\u015by\u0101",), (1, 16, 51): ("ud\u012bcy\u0101", "pr\u0101cy\u0101nde\u015b\u0101nnibodhata"),
           (1, 16, 55): ("pr\u0101cy\u0101\u1e43", "dak\u1e63i\u1e47\u0101pathav\u0101sina\u1e25"),
           (1, 16, 59): ("d\u0101k\u1e63i\u1e47\u0101\u015bcaiva", "apar\u0101\u1e43st\u0101nnibodhata"),
           (1, 16, 63): ("apar\u0101nt\u0101\u015bca", "vindhyav\u0101sina\u1e25"),
           (1, 16, 66): ("vindhyap\u1e5b\u1e63\u1e6dhaniv\u0101sina\u1e25", "parvat\u0101\u015brayi\u1e47a\u015bca")},
}
VOWEL_KEYS = set("aiueo\u1e5b\u1e37")   # the vowels as vamsa_check.lkey writes them (by quality)
CODES = ("m", "br", "vi", "vic")   # the GRETIL texts read (vic: the Visnu's critical edition)
LAW = ("B. C. Law, Tribes in Ancient India (Poona: Bhandarkar Oriental Research Institute, 1943): in copyright in "
       "India to the end of 2029 (the author died in 1969); not read here. Private reading only, from a copy held "
       "lawfully; from 1 Jan 2030 as Raychaudhuri is read.")
RAYCHAUDHURI = "phai1923"


def now() -> str:
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def connect_ro(db: str, immutable: bool = False):
    p = Path(db).resolve().as_posix()
    p = p if p.startswith("/") else "/" + p
    return sqlite3.connect("file://%s?mode=ro%s" % (urllib.parse.quote(p, safe="/:"), "&immutable=1" if immutable else ""),
                           uri=True, timeout=60)


def has(con, table: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def region_of(code: str, key: tuple) -> tuple:
    for a, b, reg in REGIONS.get(code, ()):
        if a <= key <= b and len(key) == len(a):
            return reg
    return ()


def first_clause(body: str, n: int = 160) -> str:
    """Dikshitar's description up to its first reference or note mark (for the desk: the shelf stays on this PC)."""
    s = re.sub(r"\[\d+\]|<[^>]+>", "", body or "")
    s = re.sub(r"\s+", " ", s).strip().lstrip("\u2014-").strip()
    s = re.split(r"\s(?:Bh[a\u0101]|Br|M|Vi|V[a\u0101]|Ib)\.\s*[IVX\d]", s)[0].strip()
    return s[:n]


# ---- what is read ----------------------------------------------------------------------------------------------
def read_texts(zp: Path) -> tuple:
    """({code: verses}, {code: facts}) of the four GRETIL texts the lists need; a text not in the zip is absent."""
    texts, facts = {}, {}
    if not zp.exists():
        return texts, facts
    with zipfile.ZipFile(str(zp)) as z:
        mem = vc.members(z)
        for code in CODES:
            if code not in mem:
                continue
            member, prefix, title, edition, rights, _show = vc.TEXTS[code]
            texts[code] = vc.read_tei(z.read(mem[code]).decode("utf-8", "replace"), prefix)
            facts[code] = {"title": title, "edition": edition, "rights": rights, "member": mem[code],
                           "verses": len(texts[code])}
    return texts, facts


ABBR = {"Bha": "bh", "Bh\u0101": "bh", "Br": "br", "M": "m", "Vi": "vi", "Va": "va", "V\u0101": "va"}
SPLIT = re.compile(r";|(?=(?<![A-Za-z])(?:Bh[a\u0101]|Br|M|Vi|V[a\u0101]|Ib)\.\s*[IVX\d])")
SEG_HEAD = re.compile(r"^\s*(Bh[a\u0101]|Br|M|Vi|V[a\u0101]|Ib)\.\s*(.*)$", re.S)


def text_cites(raw: str) -> list:
    """[(text, where, [verses])] read from an entry's own words (its body and its notes), as the index prints them:
    an "Ib." or a bare reference takes the text before it, and a bare "16. 47" after "Br. II. 18. 50" its pada (II).
    shelf_refs (scholar_shelf.py) keeps most of them, but not a reference after a bracketed one ("52. 11 [14] Br. II.
    16. 48", the Kekayas' Brahmanda): both are read, and a citation is kept once."""
    s = re.sub(r"\[[^\]]*\]", " ", raw or "")
    out, cur, pada = [], None, None
    for seg in SPLIT.split(s):
        seg = re.sub(r"\s+", " ", seg or "").strip().rstrip(".")
        if not seg:
            continue
        mo = SEG_HEAD.match(seg)
        if mo:
            if mo.group(1) != "Ib":
                cur, pada = ABBR.get(mo.group(1)), None
            rest = mo.group(2)
        elif cur and re.match(r"^\s*([IVX]+\.|\d)", seg):
            rest = seg
        else:
            continue
        if cur in ("vi", "bh", "br"):
            m2 = re.match(r"^\s*([IVX]+)\s*[.,]\s*(\d+)\s*[.,]\s*([\d\s,&\-]+(?:\s*and\s*[\d\s,&\-]+)*)", rest)
            if m2 and m2.group(1) in vc.ROMAN:
                pada = vc.ROMAN[m2.group(1)]
                out.append((cur, (pada, int(m2.group(2))), vc.verse_list(m2.group(3))))
                continue
            m3 = re.match(r"^\s*(\d+)\s*[.,]\s*([\d\s,&\-]+(?:\s*and\s*[\d\s,&\-]+)*)", rest)
            if m3 and pada:
                out.append((cur, (pada, int(m3.group(1))), vc.verse_list(m3.group(2))))
        elif cur in ("m", "va"):
            m2 = re.match(r"^\s*(\d+)\s*[.,]\s*([\d\s,&\-]+(?:\s*and\s*[\d\s,&\-]+)*)", rest)
            if m2:
                out.append((cur, (int(m2.group(1)),), vc.verse_list(m2.group(2))))
    return out


def entries_cited(con) -> dict:
    """{entry id: {"head", "name", "key", "words", "cites": {list: [verse, ...]}}} of the Purana Index's entries that
    cite a verse of the lists: from shelf_refs (an "Ib." takes the work before it) and from the entry's own words."""
    refs = collections.defaultdict(list)
    for eid, work, ref in con.execute(
            "SELECT r.entry_id, r.work, r.ref FROM shelf_refs r JOIN shelf_entries e ON e.id = r.entry_id "
            "WHERE e.source = 'pui' ORDER BY r.entry_id, r.n, r.id"):
        refs[eid].append("%s %s" % (work or "", ref or ""))
    raw = {eid: (body or "") + " ; " + (notes or "") for eid, body, notes in con.execute(
        "SELECT id, body, notes FROM shelf_entries WHERE source = 'pui'")}
    out = {}
    for eid in sorted(set(refs) | set(raw)):
        cites = collections.defaultdict(list)
        found = [(c, w, vs) for c, w, vs, _p in vc.parse_cites(refs.get(eid, []))] + text_cites(raw.get(eid, ""))
        for code, where, vs in found:
            spec = LISTS.get(code)
            if not spec or tuple(where) != spec["where"]:
                continue
            for v in vs:
                if v in spec["verses"] and v not in cites[code]:
                    cites[code].append(v)
        if cites:
            out[eid] = {"cites": {c: sorted(v) for c, v in cites.items()}}
    if out:
        ph = ",".join("?" * len(out))
        for eid, name, key, head, body in con.execute(
                "SELECT id, name, key, head, body FROM shelf_entries WHERE id IN (%s)" % ph, list(out)):
            out[eid].update({"name": name or "", "key": key or (name or "").lower(), "head": head or "",
                             "words": first_clause(body)})
    return out


def fold(s: str) -> str:
    """A word's letters as vamsa_check.lkey compares them, b and v one (the e-texts confuse them: vahlikah for the
    index's Bahlika, bahyah for its Vahya)."""
    return re.sub(r"b(?!h)", "v", vc.lkey(s))


def name_info(name: str) -> dict:
    """What a people's name is looked for by: vamsa_check's keys; its case forms (fold); its stem as the member of a
    compound, less its last vowel (Kasi: kas, as in kasikosalah; Magadha: magadh, as in magadhagonardah), when that
    leaves three letters or more; and, for a name that opens with a vowel, the stem as a vowel's sandhi leaves it
    after a word ending in a (caivandhakaih: ca + eva + andhakaih; cotkalaih: ca + utkalaih)."""
    w = vc.nfc(re.sub(r"[(\[].*?[)\]]", " ", name or "")).strip()
    w = max(re.findall(r"[^\s,;:.'-]+", w) or [""], key=len)
    info = {"keys": vc.keys_of(name) if name else [], "forms": set(), "stem": "", "sandhi": ""}
    if not w:
        return info
    base = w[:-1] if w[-1] in vc.VOWELS else w
    if w[-1] in vc.ENDINGS:
        ends = vc.ENDINGS[w[-1]] + vc.ENDINGS.get({"i": "\u012b", "\u012b": "i"}.get(w[-1], ""), ())
        info["forms"] = {fold(base + e) for e in ends} | {fold(w)}
    if len(vc.letters(base)) >= 3:
        info["stem"] = fold(base)
    s = info["stem"]
    if len(s) >= 4 and s[0] in "aiueo\u1e5b":
        info["sandhi"] = {"a": "a", "i": "e", "u": "o", "e": "ai", "o": "au", "\u1e5b": "ar"}[s[0]] + s[1:]
    return info


SANDHI_BEFORE = set("s\u015b\u1e63r")   # a visarga as sandhi leaves it before a word joined to it (kasmirastanganah)


def tier(info: dict, word: str) -> str:
    """How a word is the name, or "": a case form ("form"); the last member of a compound ("last member": sajangalah,
    sahakacchah); the first ("first member": kasikosalah, barbarascaiva); a member inside, after a member's vowel or a
    visarga's sandhi ("member": salvamagadhagonardah, kupathastanganah); the stem after a vowel's sandhi ("sandhi":
    cotkalaih). Short stems only as a whole form or a first member."""
    lw = fold(word)
    if lw in info["forms"]:
        return "form"
    for f in info["forms"]:
        if len(f) >= 4 and len(lw) > len(f) and lw.endswith(f) and lw[-len(f) - 1] in VOWEL_KEYS:
            return "last member"
    s, n = info["stem"], len(info["stem"])
    if s and lw.startswith(s) and len(lw) > n + 2 and lw[n] in VOWEL_KEYS:
        return "first member"
    if n >= 4:
        i = lw.find(s, 1)
        while i > 0:
            if (lw[i - 1] in VOWEL_KEYS or lw[i - 1] in SANDHI_BEFORE) and i + n < len(lw) and lw[i + n] in VOWEL_KEYS:
                return "member"
            i = lw.find(s, i + 1)
    v = info["sandhi"]
    if v:
        i = lw.find(v, 1)
        while i > 0:
            if i + len(v) < len(lw) and lw[i + len(v)] in VOWEL_KEYS:
                return "sandhi"
            i = lw.find(v, i + 1)
    return ""


TIERS = ("form", "last member", "first member", "member", "sandhi", "prefix")


def match(info: dict, words: str, skip=()) -> tuple:
    """(the word of a verse that is the name, how), the best way first across the verse; ("", "") when none. Last,
    vamsa_check's strict reading (the name's letters opening a word: "prefix"). Its loose reading (a short name's form
    after any consonant) is not used: in these lists it takes the anga of tanganah for the Angas."""
    ws = [w for w in vc.words_of(words) if vc.nfc(w) not in skip]
    found = {}
    for w in ws:
        h = tier(info, w)
        if h and h not in found:
            found[h] = w
    for h in TIERS[:-1]:
        if h in found:
            return found[h], h
    for w in ws:
        if any(vc.word_form(k, w, loose=False) for k in info["keys"]):
            return w, "prefix"
    return "", ""


def find(texts: dict, code: str, where: tuple, verse: int, info: dict) -> list:
    """[(GRETIL text, verse key, the word found, how, region)] of a citation: the cited verse, else the nearest of the
    two either side where the name stands (the index's edition and GRETIL's may number a verse or two apart)."""
    out = []
    for tcode, key in vc.gretil_keys(code, where, verse):
        if tcode not in texts:
            continue
        for d in (0, -1, 1, -2, 2):
            k = key[:-1] + (key[-1] + d,)
            if k not in texts[tcode]:
                continue
            skip = {vc.nfc(x) for x in MARKERS.get(tcode, {}).get(k, ())}
            w, how = match(info, texts[tcode][k], skip)
            if w:
                out.append((tcode, k, w, how, region_of(tcode, k)))
                break
    return out


def ties(con, ids: list) -> dict:
    """{entry id: [(entity id, canonical, kind, how)]} from shelf_links."""
    out = collections.defaultdict(list)
    if not ids or not has(con, "shelf_links"):
        return out
    ph = ",".join("?" * len(ids))
    for eid, ent, canon, kind, how in con.execute(
            "SELECT l.entry_id, l.entity_id, e.canonical, e.kind, l.how FROM shelf_links l JOIN entities e ON "
            "e.id = l.entity_id WHERE l.entry_id IN (%s) ORDER BY l.entry_id, l.entity_id" % ph, ids):
        out[eid].append((ent, canon or "", kind or "", how or ""))
    return out


def mentions(con, ents: list) -> dict:
    """{entity id: {"passages", "texts", "docs": {doc: passages}}} in our live texts."""
    out = {}
    if not ents or not has(con, "entity_mentions"):
        return out
    ph = ",".join("?" * len(ents))
    per = collections.defaultdict(collections.Counter)
    for ent, code, n in con.execute(
            "SELECT m.entity_id, d.code, COUNT(DISTINCT m.passage_id) FROM entity_mentions m JOIN passages p ON "
            "p.id = m.passage_id JOIN docs d ON d.id = p.doc_id WHERE m.entity_id IN (%s) AND d.code NOT LIKE "
            "'%%-RETIRED' GROUP BY m.entity_id, d.code" % ph, ents):
        per[ent][code] += n
    for ent, c in per.items():   # a passage naming two entities of one row is counted under each (an upper bound)
        out[ent] = {"passages": sum(c.values()), "texts": len(c), "docs": dict(c)}
    return out


def claims_of(path: str, ents: list) -> tuple:
    """({entity id: [claim]}, {work: facts}) from claims.db: the latest read of each page, the quotation found on
    the page (exact or close), as the site's claims are chosen (index_sync.py)."""
    out, works = collections.defaultdict(list), {}
    if not ents or not path or not Path(path).exists():
        return out, works
    con = connect_ro(path)
    try:
        if not {"claims", "claim_links", "claim_reads"} <= {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}:
            return out, works
        if has(con, "claim_works"):
            for code, author, title, year, licence in con.execute(
                    "SELECT code, author, title, year, licence FROM claim_works"):
                works[code] = {"author": author, "title": title, "year": year, "licence": licence or ""}
        ph = ",".join("?" * len(ents))
        seen = set()
        for ent, cid, work, printed, rel, claim, check in con.execute(
                "SELECT l.entity_id, c.id, c.work, c.printed, c.relation, c.claim, c.quote_check FROM claim_links l "
                "JOIN claims c ON c.id = l.claim_id WHERE l.entity_id IN (%s) AND c.read_id IN (SELECT MAX(id) FROM "
                "claim_reads WHERE status = 'ok' GROUP BY work, pdf_page) AND c.quote_check IN ('exact', 'close') "
                "ORDER BY c.id" % ph, ents):
            if (ent, cid) in seen:
                continue
            seen.add((ent, cid))
            out[ent].append({"id": cid, "work": work, "page": printed or "", "relation": rel or "",
                             "claim": claim or "", "check": check or ""})
    finally:
        con.close()
    return out, works


# ---- the rows --------------------------------------------------------------------------------------------------
def build(db: str, claims_db: str, zp: Path, immutable: bool = False) -> dict:
    texts, facts = read_texts(zp)
    con = connect_ro(db, immutable)
    try:
        if not {"shelf_entries", "shelf_refs"} <= {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}:
            return {"error": "the Purana Index is not on the shelf of %s (scholar_shelf.py loads it)" % db}
        cited = entries_cited(con)
        tie = ties(con, list(cited))
        ents = sorted({t[0] for v in tie.values() for t in v})
        ment = mentions(con, ents)
    finally:
        con.close()
    cl, works = claims_of(claims_db, ents)
    groups = collections.OrderedDict()
    for eid in sorted(cited, key=lambda e: (cited[e]["key"], e)):
        groups.setdefault(cited[eid]["key"], []).append(eid)
    rows = []
    for key, eids in groups.items():
        e0 = cited[eids[0]]
        info = name_info(e0["name"])
        row = {"key": key, "name": e0["name"],
               "entries": [{"id": e, "head": cited[e]["head"], "words": cited[e]["words"],
                            "cites": {c: sorted(v) for c, v in cited[e]["cites"].items()}} for e in eids],
               "lists": {}, "regions": {}, "entities": [], "ours": {"passages": 0, "texts": 0, "top": []},
               "raychaudhuri": []}
        for code, spec in LISTS.items():
            vs = sorted({v for e in eids for v in cited[e]["cites"].get(code, [])})
            if not vs:
                continue
            got = []
            for v in vs:
                if not spec["held"]:
                    got.append({"cited": v, "found": [], "verdict": "not held"})
                    continue
                f = find(texts, code, spec["where"], v, info) if (info["keys"] or info["stem"] or info["forms"]) else []
                got.append({"cited": v, "verdict": ("named" if f else ("not held" if not any(
                                t in texts for t, _k in vc.gretil_keys(code, spec["where"], v)) else "not found")),
                            "found": [{"text": t, "verse": ".".join(map(str, k)), "form": w, "how": h,
                                       "region": list(r)} for t, k, w, h, r in f]})
            row["lists"][code] = got
            regs = sorted({r for g in got for f in g["found"] for r in f["region"]}, key=REGION_ORDER.index)
            if regs:
                row["regions"][code] = regs
        rm, rb = row["regions"].get("m"), row["regions"].get("br")
        row["agree"] = "" if not (rm and rb) else ("agree" if set(rm) & set(rb) else "differ")
        seen, docs = set(), collections.Counter()
        for e in eids:
            for ent, canon, kind, how in tie.get(e, []):
                if ent in seen:
                    continue
                seen.add(ent)
                row["entities"].append({"id": ent, "canonical": canon, "kind": kind, "how": how})
                for d, n in (ment.get(ent) or {}).get("docs", {}).items():
                    docs[d] += n
                for c in cl.get(ent, []):
                    if all(c["id"] != x["id"] for x in row["raychaudhuri"]):
                        row["raychaudhuri"].append(c)
        row["ours"] = {"passages": sum(docs.values()), "texts": len(docs), "top": [[d, n] for d, n in docs.most_common(3)]}
        rows.append(row)
    return {"mark": MARK, "at": now(), "db": db, "claims_db": claims_db, "zip": str(zp), "texts": facts,
            "lists": {c: {"title": s["title"], "held": s["held"] and any(
                t in texts for t in (("vi", "vic") if c == "vi" else (c,))),
                "verses": "%d-%d" % (s["verses"][0], s["verses"][-1])} for c, s in LISTS.items()},
            "works": works, "law": LAW, "rows": rows, "summary": summarize(rows)}


def summarize(rows: list) -> dict:
    n_in = collections.Counter(c for r in rows for c in r["lists"])
    named = collections.Counter(c for r in rows for c, g in r["lists"].items() if any(x["verdict"] == "named" for x in g))
    cited_held = collections.Counter(c for r in rows for c, g in r["lists"].items()
                                     if any(x["verdict"] in ("named", "not found") for x in g))
    region = collections.Counter((c, reg) for r in rows for c, regs in r["regions"].items() for reg in regs)
    return {"peoples": len(rows), "entries": sum(len(r["entries"]) for r in rows),
            "in_list": dict(n_in), "named_in_verse": dict(named), "looked_for": dict(cited_held),
            "in_lists_2plus": sum(1 for r in rows if len(r["lists"]) >= 2),
            "in_all_four": sum(1 for r in rows if len(r["lists"]) == 4),
            "vayu_only": sum(1 for r in rows if list(r["lists"]) == ["va"]),
            "m_br_both": sum(1 for r in rows if r["agree"]), "m_br_agree": sum(1 for r in rows if r["agree"] == "agree"),
            "m_br_differ": sum(1 for r in rows if r["agree"] == "differ"),
            "tied": sum(1 for r in rows if r["entities"]), "in_our_texts": sum(1 for r in rows if r["ours"]["passages"]),
            "raychaudhuri": sum(1 for r in rows if r["raychaudhuri"]),
            "raychaudhuri_claims": sum(len(r["raychaudhuri"]) for r in rows),
            "regions": {"%s %s" % k: v for k, v in sorted(region.items())}}


# ---- the report ------------------------------------------------------------------------------------------------
def where_line(r: dict) -> str:
    parts = []
    for code, g in r["lists"].items():
        vs = ",".join(str(x["cited"]) for x in g)
        regs = "/".join(r["regions"].get(code, []))
        parts.append("%s %s%s" % (code, vs, (" " + regs) if regs else ""))
    return "; ".join(parts)


def show_row(r: dict, out=print):
    out("  %s (%s): %s" % (r["name"], ", ".join(e["head"] for e in r["entries"]), where_line(r)))
    for e in r["entries"]:
        out("    Dikshitar s.v. %s: %s" % (e["head"], e["words"]))
    for code, g in r["lists"].items():
        for x in g:
            if x["found"]:
                out("    %s %s: %s" % (code, x["cited"], "; ".join("%s %s %s%s" % (
                    f["text"], f["verse"], f["form"], (" (%s)" % "/".join(f["region"])) if f["region"] else "")
                    for f in x["found"])))
            else:
                out("    %s %s: %s" % (code, x["cited"], x["verdict"]))
    if r["entities"]:
        out("    ours: %s; named in %d passage(s) of %d text(s)%s" % (
            ", ".join("%s (%s, %s)" % (e["canonical"], e["kind"], e["how"]) for e in r["entities"]),
            r["ours"]["passages"], r["ours"]["texts"],
            (": " + ", ".join("%s %d" % (d, n) for d, n in r["ours"]["top"])) if r["ours"]["top"] else ""))
    else:
        out("    ours: not tied to our names")
    for c in r["raychaudhuri"][:6]:
        out("    Raychaudhuri p. %s (%s): %s" % (c["page"], c["relation"], c["claim"]))


def report(res: dict, limit: int = 30, out=print):
    s = res["summary"]
    out("peoples_index %s" % MARK)
    for code, f in res["lists"].items():
        out("  %-3s %-55s verses %s, %s" % (code, f["title"], f["verses"], "held" if f["held"] else "not held"))
    out("  the peoples the lists name (the Purana Index's entries that cite them): %d (%d entries)"
        % (s["peoples"], s["entries"]))
    out("  in each list: %s; in two lists or more %d; in all four %d; in the Vayu's alone %d"
        % (", ".join("%s %d" % (c, s["in_list"].get(c, 0)) for c in LISTS), s["in_lists_2plus"], s["in_all_four"],
           s["vayu_only"]))
    out("  named in the cited verse (or two either side): %s" % ", ".join(
        "%s %d of %d" % (c, s["named_in_verse"].get(c, 0), s["looked_for"].get(c, 0)) for c in ("m", "br", "vi")))
    out("  the Matsya and the Brahmanda both place %d: the same region %d, a different one %d"
        % (s["m_br_both"], s["m_br_agree"], s["m_br_differ"]))
    out("  tied to our names %d; named in our texts %d; Raychaudhuri speaks of %d (%d claims)"
        % (s["tied"], s["in_our_texts"], s["raychaudhuri"], s["raychaudhuri_claims"]))
    rows = res["rows"]
    diff = [r for r in rows if r["agree"] == "differ"]
    out("")
    out("Placed differently by the Matsya and the Brahmanda (%d):" % len(diff))
    for r in diff[:limit]:
        out("  %s: m %s; br %s" % (r["name"], "/".join(r["regions"]["m"]), "/".join(r["regions"]["br"])))
    ray = sorted([r for r in rows if r["raychaudhuri"]], key=lambda r: (-len(r["raychaudhuri"]), r["key"]))
    out("")
    out("The lists and Raychaudhuri, side by side (%d):" % len(ray))
    for r in ray[:limit]:
        show_row(r, out)
    out("")
    out("Not read: " + res["law"])


def write(res: dict, jpath: Path, cpath: Path):
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(cpath, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "name", "entries", "matsya", "matsya_region", "brahmanda", "brahmanda_region", "visnu",
                    "vayu", "m_br", "ours", "our_passages", "our_texts", "raychaudhuri_claims", "raychaudhuri_pages"])
        for r in res["rows"]:
            def vs(c):
                return " ".join("%s%s" % (x["cited"], "" if x["verdict"] == "named" else "?" if x["verdict"] ==
                                          "not found" else "") for x in r["lists"].get(c, []))
            w.writerow([r["key"], r["name"], "; ".join(e["head"] for e in r["entries"]), vs("m"),
                        "/".join(r["regions"].get("m", [])), vs("br"), "/".join(r["regions"].get("br", [])), vs("vi"),
                        vs("va"), r["agree"], "; ".join(e["canonical"] for e in r["entities"]), r["ours"]["passages"],
                        r["ours"]["texts"], len(r["raychaudhuri"]),
                        " ".join(sorted({c["page"] for c in r["raychaudhuri"]}, key=lambda p: (len(p), p)))])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The peoples of the Puranas' lists, the Purana Index, our names and "
                                             "Raychaudhuri (free, read-only; --yes writes data/shelf/peoples_index.*)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--claims-db", default="data/shelf/claims.db")
    ap.add_argument("--zip", default="")
    ap.add_argument("--immutable", action="store_true", help="read --db as an immutable copy (a backup)")
    ap.add_argument("--name", default="")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json", default="data/shelf/peoples_index.json")
    ap.add_argument("--csv", default="data/shelf/peoples_index.csv")
    ap.add_argument("--yes", action="store_true", help="write the json and the csv (nothing else is written)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    db = a.db if Path(a.db).is_absolute() else str(ROOT / a.db)
    cdb = a.claims_db if Path(a.claims_db).is_absolute() else str(ROOT / a.claims_db)
    if not Path(db).exists():
        say("%s not found" % db, "")
        return 1
    zp = vc.zip_path(a.zip)
    res = build(db, cdb, zp, a.immutable)
    if res.get("error"):
        say(res["error"], "python scripts\\scholar_shelf.py")
        return 1
    held = [c for c in ("m", "br", "vi") if res["lists"][c]["held"]]
    if a.name:
        want = vc.lkey(a.name) if hasattr(vc, "lkey") else a.name.lower()
        hit = [r for r in res["rows"] if vc.lkey(r["name"]) == want or a.name.lower() in r["name"].lower()]
        print("peoples_index %s: %s" % (MARK, a.name))
        for r in hit[:a.limit]:
            show_row(r)
        say("%d row(s) for %s" % (len(hit), a.name) if hit else "%s is not among the peoples of the lists" % a.name,
            "python scripts\\peoples_index.py")
        return 0 if hit else 1
    report(res, a.limit)
    s = res["summary"]
    verdict = ("%d peoples in the Puranas' lists (Dikshitar's citations); the Matsya and the Brahmanda agree on the "
               "region of %d of %d; Raychaudhuri speaks of %d" % (s["peoples"], s["m_br_agree"], s["m_br_both"],
                                                                  s["raychaudhuri"]))
    if not held:
        verdict += "; GRETIL's zip not found, so no verse was read (%s)" % zp
    also = ["python scripts\\peoples_index.py --name Kekaya",
            "python scripts\\scholar_claims.py --part 2   (Part II, the plan: free)"]
    if a.yes:
        jp = Path(a.json) if Path(a.json).is_absolute() else ROOT / a.json
        cp = Path(a.csv) if Path(a.csv).is_absolute() else ROOT / a.csv
        write(res, jp, cp)
        say(verdict + "; written: %s, %s" % (jp, cp), "open %s" % cp, also)
    else:
        say(verdict + "; nothing written", "python scripts\\peoples_index.py --yes", also)
    return 0


if __name__ == "__main__":
    sys.exit(main())
