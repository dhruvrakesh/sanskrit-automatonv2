#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
scholar_shelf.py  (2026-10-21)  SHELF_2026_10_21

The scholars' shelf, step 1: three indexes of names, as the Cologne Digital Sanskrit Lexicon digitized them
(CC BY-NC-SA 3.0; the credit as each file's header gives it), tied to the names our texts hold (entities):

  vei  A. A. Macdonell and A. B. Keith, Vedic Index of Names and Subjects (London 1912): 3,834 entries; each name
       with what the Vedic texts say of it and where (its footnotes), and the other names it refers to (in bold).
  inm  S. Soerensen, An Index to the Names in the Mahabharata (1904): 12,647 entries; its references are to the
       Calcutta edition (parvan, adhyaya, sloka); our MBh01 is the critical edition's first book, numbered otherwise.
  pui  V. R. Ramachandra Dikshitar, The Purana Index (Madras 1951-55): 17,512 entries; its references are by the
       abbreviations it prints (Va., Br., M., Bha., Vi.; Ib. for ibidem), whose key is in the printed front matter,
       which the digitization does not hold.

Read from --dir (data/shelf/cologne/<code>/txt/<code>.txt and <code>header.xml, as the zips unpack); each entry
with its page and column, its headword (k1, SLP1, read into IAST), its homonym number, its text without the markup,
its footnotes, the bold names it refers to (vei), and its references as printed, each with the work it names (a
footnote's own, or the one the sentence names before the footnote mark) and whether our corpus holds that place
(ours): only where the text is ours and, for the Satapatha, the book too (ours is book 14, the Brihadaranyaka).
Tied to our entities by name: exact (the IAST spelling, without hyphens or spaces), or loose (only the length of a
vowel differs: Parikshit, Pariikshit); a homonym entry ties to the same name, and the report says which entry it is.

Local only: corpus_sync.py does not know the shelf_ tables, and data/shelf/ is not committed (.gitignore). Nothing
is called; no model; free.

  python scripts\\scholar_shelf.py                    (the plan: reads the files and the database; writes nothing)
  python scripts\\scholar_shelf.py --yes              (a backup first, then the tables shelf_*)
  python scripts\\scholar_shelf.py --show Janaka      (what the indexes say of a name, and where our texts name it)
  python scripts\\scholar_shelf.py --credits          (the credit line of each index, from its header)

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, sqlite3, sys, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

MARK = "SHELF_2026_10_21"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

SOURCES = {
    "vei": {"title": "Vedic Index of Names and Subjects", "authors": "A. A. Macdonell and A. B. Keith", "year": "1912"},
    "inm": {"title": "An Index to the Names in the Mahabharata", "authors": "S. S\u00f8rensen", "year": "1904"},
    "pui": {"title": "The Purana Index", "authors": "V. R. Ramachandra Dikshitar", "year": "1951-1955"},
}
ORDER = ("vei", "inm", "pui")
MIN_ENTRIES = 100   # a file with fewer entries is not the index

META = re.compile(r"^<L>(\d+)<pc>([^<]+)<k1>([^<]+)<k2>([^<]+?)(?:<h>([^<]+))?\s*$")
PAGE = re.compile(r"^\[Page[^\]]*\]\s*$")
FOOT = re.compile(r"<F>(.*?)</F>", re.S)
SUP = re.compile(r"<sup>(\d+)</sup>")
BOLD = re.compile(r"\{@(.*?)@\}", re.S)

# The Vedic texts the Vedic Index names, as it spells them (a line break may cut a word: "Vaja- saneyi").
WORKS = [
    ("\u015aatapatha Br\u0101hma\u1e47a", r"[\u015aS]ata\s*patha\s+Br\u0101h\s*ma\u1e47a"),
    ("B\u1e5bhad\u0101ra\u1e47yaka Upani\u1e63ad", r"B\u1e5bhad\u0101\s*ra\u1e47\s*yaka\s+Upani\s*\u1e63ad"),
    ("V\u0101jasaneyi Sa\u1e43hit\u0101", r"V\u0101ja\s*saneyi\s+Sa\u1e43\s*hit\u0101"),
    ("Taittir\u012bya Sa\u1e43hit\u0101", r"Tait\s*tir\u012bya\s+Sa\u1e43\s*hit\u0101"),
    ("Taittir\u012bya Br\u0101hma\u1e47a", r"Tait\s*tir\u012bya\s+Br\u0101h\s*ma\u1e47a"),
    ("Taittir\u012bya \u0100ra\u1e47yaka", r"Tait\s*tir\u012bya\s+\u0100ra\u1e47\s*yaka"),
    ("K\u0101\u1e6dhaka Sa\u1e43hit\u0101", r"K\u0101\u1e6dhaka\s+Sa\u1e43\s*hit\u0101"),
    ("Maitr\u0101ya\u1e47\u012b Sa\u1e43hit\u0101", r"Maitr\u0101\s*ya\u1e47\u012b\s+Sa\u1e43\s*hit\u0101"),
    ("Aitareya Br\u0101hma\u1e47a", r"Aitareya\s+Br\u0101h\s*ma\u1e47a"),
    ("Aitareya \u0100ra\u1e47yaka", r"Aitareya\s+\u0100ra\u1e47\s*yaka"),
    ("Pa\u00f1cavi\u1e43\u015ba Br\u0101hma\u1e47a", r"Pa\u00f1ca\s*vi\u1e43\u015ba\s+Br\u0101h\s*ma\u1e47a"),
    ("Kau\u1e63\u012btaki Br\u0101hma\u1e47a", r"Kau\u1e63\u012btaki\s+Br\u0101h\s*ma\u1e47a"),
    ("Kau\u1e63\u012btaki Upani\u1e63ad", r"Kau\u1e63\u012btaki\s+Upani\s*\u1e63ad"),
    ("Ch\u0101ndogya Upani\u1e63ad", r"Ch\u0101n\s*dogya\s+Upani\s*\u1e63ad"),
    ("Jaimin\u012bya Upani\u1e63ad Br\u0101hma\u1e47a", r"Jaimin\u012bya\s+Upani\s*\u1e63ad\s+Br\u0101h\s*ma\u1e47a"),
    ("Jaimin\u012bya Br\u0101hma\u1e47a", r"Jaimin\u012bya\s+Br\u0101h\s*ma\u1e47a"),
    ("Gopatha Br\u0101hma\u1e47a", r"Gopatha\s+Br\u0101h\s*ma\u1e47a"),
    ("\u015a\u0101\u1e45kh\u0101yana \u015arauta S\u016btra", r"\u015a\u0101\u1e45kh\u0101yana\s+\u015arauta\s+S\u016btra"),
    ("\u015a\u0101\u1e45kh\u0101yana \u0100ra\u1e47yaka", r"\u015a\u0101\u1e45kh\u0101yana\s+\u0100ra\u1e47\s*yaka"),
    ("\u0100\u015bval\u0101yana \u015arauta S\u016btra", r"\u0100\u015bval\u0101yana\s+\u015arauta\s+S\u016btra"),
    ("\u0100\u015bval\u0101yana G\u1e5bhya S\u016btra", r"\u0100\u015bval\u0101yana\s+G\u1e5bhya\s+S\u016btra"),
    ("K\u0101ty\u0101yana \u015arauta S\u016btra", r"K\u0101ty\u0101yana\s+\u015arauta\s+S\u016btra"),
    ("L\u0101\u1e6dy\u0101yana \u015arauta S\u016btra", r"L\u0101\u1e6dy\u0101yana\s+\u015arauta\s+S\u016btra"),
    ("Nirukta", r"Nirukta"),
    ("\u1e5agveda", r"(?:Rig\s*veda|\u1e5ag\s*veda)(?!-Noten)"),
    ("Atharvaveda", r"Atharva\s*veda"),
    ("S\u0101maveda", r"S\u0101ma\s*veda"),
]
WORK_RX = [(name, re.compile(rx)) for name, rx in WORKS]

# Where our corpus holds the text a reference names (doc code, and what to say of the numbering).
OURS = {
    "\u015aatapatha Br\u0101hma\u1e47a": ("2015_405693_Shatpath-Brahmanam", "ours is book 14 only"),
    "B\u1e5bhad\u0101ra\u1e47yaka Upani\u1e63ad": ("2015_405693_Shatpath-Brahmanam",
                                                  "ours is the Madhyandina recension (Satapatha book 14): its numbering may differ"),
    "V\u0101jasaneyi Sa\u1e43hit\u0101": ("yajur_veda_shukla_yajur_veda", "ours is an OCR reading of a scan: whether it holds this place is not checked"),
    "Taittir\u012bya Sa\u1e43hit\u0101": ("yajur_veda_taittiriya_krishna_yajur_veda", "ours is an OCR reading of a scan: whether it holds this place is not checked"),
    "Nirukta": ("nirukta", ""),
    "S\u0101maveda": ("sama_veda_sama_veda", "ours is an OCR reading of a scan: whether it holds this place is not checked"),
    "Mah\u0101bh\u0101rata": ("MBh01", "Soerensen cites the Calcutta edition; ours is the critical edition's book 1, numbered otherwise"),
}
# Not counted as ours: the Rgveda (476948-Rgveda-samhita_Vol-ii is one volume of a scan, not yet read: which hymns it
# holds is not known), and every text the corpus does not have.
ROMAN_BOOK = re.compile(r"^\s*([ivxlc]+)\.\s")
INM_REF = re.compile(r"(?<![A-Za-z])([IVXL]+),\s*\{@(\d+)@\}([\u03b1-\u03c9]?),\s*[\u2020\u2021(]*(\d+)")
PUI_ABBR = re.compile(r"^\s*(V\u0101|Br|M|Bh\u0101|Vi|Ib|Va|Bha|V\u012b)\.\s*")
PUI_NUM = re.compile(r"^\s*((?:[IVX]+\.\s*)?\d+(?:[.,]\s*\d+)*(?:\s*[-\u2013]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-\u2013]\s*\d+)?)*)")
FOLD = str.maketrans({"\u0101": "a", "\u012b": "i", "\u016b": "u", "\u1e5d": "\u1e5b", "\u1e39": "\u1e37", "\u1e41": "\u1e43"})


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def slp1_to_iast(k1: str) -> str:
    from indic_transliteration import sanscript
    return unicodedata.normalize("NFC", sanscript.transliterate(k1, sanscript.SLP1, sanscript.IAST))


def key_of(name: str) -> str:
    """A name's key: NFC, lower case, without hyphens, spaces or dots."""
    s = unicodedata.normalize("NFC", str(name or "")).lower().replace("\u1e41", "\u1e43")
    return re.sub(r"[\s\-.\u00b7']", "", s)


def loose_of(key: str) -> str:
    return (key or "").translate(FOLD)


def prejoin(s: str) -> str:
    """The page breaks taken out, and a bold name cut at a line's end joined ({@Yajnavalkya Vaja-@} / {@saneya,@})."""
    s = re.sub(r"(?m)^\[Page[^\]]*\]\s*$\n?", "", s)
    return re.sub(r"-@\}\n\{@", "", s)


def clean(s: str) -> str:
    """The markup taken away; a word cut at a printed line's end joined; a printed line break a space; a paragraph
    (<div n="P">) a line of its own."""
    s = re.sub(r"(?m)^\[Page[^\]]*\]\s*$\n?", "", s)
    s = re.sub(r"(?<=[a-z\u00e0-\u024f\u1e00-\u1eff])-\n(?=[a-z\u00e0-\u024f\u1e00-\u1eff])", "", s)
    s = s.replace("\n", " ")
    s = re.sub(r"<div n=\"(?:P|HI)\"\s*/?>", "\n", s)
    s = re.sub(r"<div n=\"lb\"\s*/?>", " ", s)
    s = re.sub(r"<C n=\"\d+\"\s*/?>", " | ", s)
    s = SUP.sub(r"[\1]", s)
    s = re.sub(r"\{[@%#](.*?)[@%#]\}", r"\1", s, flags=re.S)
    s = s.replace("{??}", "[?]")
    s = re.sub(r"<[^>\n]{1,60}>", "", s)
    return "\n".join(x for x in (re.sub(r"[ \t]+", " ", y).strip() for y in s.split("\n")) if x).strip()


def work_in(text: str, last: bool = True) -> str:
    """The Vedic text a passage names (the last one named, or the first), else ''."""
    best, pos = "", -1
    for name, rx in WORK_RX:
        for m in rx.finditer(text or ""):
            if (last and m.start() > pos) or (not last and (pos < 0 or m.start() < pos)):
                best, pos = name, m.start()
    return best


def read_entries(path: Path) -> list:
    """[{"lnum", "page", "k1", "h", "raw"}] of an index file, in order."""
    out, cur = [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = META.match(line) if line.startswith("<L>") else None
            if m:
                cur = {"lnum": int(m.group(1)), "page": m.group(2), "k1": m.group(3), "h": (m.group(5) or "").strip(),
                       "lines": []}
                continue
            if cur is None:
                continue
            if line.startswith("<LEND>"):
                cur["raw"] = "\n".join(cur.pop("lines"))
                out.append(cur)
                cur = None
                continue
            cur["lines"].append(line)
    return out


def ours_of(work: str, ref: str, book: str):
    """(doc code, note) when our corpus holds the place a reference names, else ("", "")."""
    hit = OURS.get(work)
    if not hit:
        return "", ""
    code, note = hit
    if work == "\u015aatapatha Br\u0101hma\u1e47a" and book != "xiv":
        return "", ""
    return code, note


def parse_entry(code: str, e: dict) -> dict:
    raw = e["raw"]
    notes = []
    for m in FOOT.finditer(raw):
        t = m.group(1)
        n = re.match(r"\s*(\d+)\)\s*", t)
        notes.append((int(n.group(1)) if n else 0, t[n.end():] if n else t))
    raw = prejoin(raw)
    body_raw = FOOT.sub("", raw)
    head_raw, _sep, rest = body_raw.partition("\u00a6")
    if not _sep:
        head_raw, rest = "", body_raw
    name = slp1_to_iast(e["k1"])
    name = name[:1].upper() + name[1:]
    ent = {"lnum": e["lnum"], "page": e["page"], "k1": e["k1"], "h": e["h"], "name": name, "key": key_of(name),
           "head": clean(head_raw).strip(" ,.;:"), "body": clean(rest), "notes": [(n, clean(t)) for n, t in notes], "refs": [],
           "xrefs": []}
    if code == "vei":
        own = key_of(name)
        seen = set()
        for m in BOLD.finditer(rest):
            x = clean(m.group(1)).strip(" ,.;:")
            x = re.sub(r"^\d+\.\s*", "", x)
            k = key_of(x)
            if re.search(r"[A-Za-z]", x) and k and k != own and k not in seen and len(x) <= 60:
                seen.add(k)
                ent["xrefs"].append((x, k))
        body_for_marks = clean(rest)
        for n, t in ent["notes"]:
            i = body_for_marks.find("[%d]" % n)
            cur_work = work_in(body_for_marks[max(0, i - 160):i]) if i >= 0 else ""   # the text the sentence names
            book = ""
            for seg in [x.strip() for x in t.split(";") if x.strip()]:
                lead = ""
                for nm, rx in WORK_RX:   # a segment that begins with a text's name names it
                    m2 = rx.match(seg)
                    if m2 and (not lead or m2.end() > len(lead)):
                        lead, cur_work = seg[:m2.end()], nm
                ref = seg[len(lead):].lstrip(" ,") if lead else seg
                numeric = re.match(r"\s*(?:[ivxlc]+\.|\d)", ref) is not None
                b = ROMAN_BOOK.match(ref)
                if b:
                    book = b.group(1)
                ours, note = ours_of(cur_work, ref, book) if numeric else ("", "")
                ent["refs"].append({"n": n, "work": cur_work if numeric else "", "ref": seg[:300] if not numeric else ref[:300],
                                    "ours": ours, "note": note})
    elif code == "inm":
        for m in INM_REF.finditer(rest):
            ref = "%s.%s%s.%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
            ours, note = OURS["Mah\u0101bh\u0101rata"] if m.group(1) == "I" else ("", "")
            ent["refs"].append({"n": 0, "work": "Mah\u0101bh\u0101rata (Calcutta ed.)", "ref": ref, "ours": ours,
                                "note": note})
    elif code == "pui":
        parts = [p for p in re.split(r"<div n=\"P\"\s*/?>", rest)[1:]] + [t for _n, t in notes]
        for p in parts:
            text = clean(p)
            cur = ""
            for seg in [x.strip() for x in text.split(";") if x.strip()]:
                m = PUI_ABBR.match(seg)
                if m:
                    cur = cur if m.group(1) == "Ib" and cur else m.group(1) + "."
                    seg = seg[m.end():]
                if not cur:
                    continue
                n = PUI_NUM.match(seg)
                if n:
                    ent["refs"].append({"n": 0, "work": cur, "ref": n.group(1).strip(), "ours": "", "note": ""})
    return ent


def header_credit(path: Path) -> dict:
    """The credit of an index, from its TEI header, in its own words."""
    out = {"credit": "", "licence": "", "copyright": "", "edition": ""}
    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError):
        return out

    def txt(el):
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""
    title = txt(root.find(".//{*}titleStmt/{*}title[@type='main']"))
    desc = txt(root.find(".//{*}titleStmt/{*}title[@type='desc']"))
    edition = txt(root.find(".//{*}editionStmt/{*}edition"))
    editors = [txt(x) for x in root.findall(".//{*}titleStmt/{*}editor")]
    pubs = [txt(x) for x in root.findall(".//{*}publicationStmt/{*}publisher")]
    places = [txt(x) for x in root.findall(".//{*}publicationStmt/{*}pubPlace")]
    date = txt(root.find(".//{*}publicationStmt/{*}date"))
    avail = [txt(x) for x in root.findall(".//{*}publicationStmt/{*}availability/{*}p")]
    lic = ""
    for r in root.findall(".//{*}availability//{*}ref"):
        t = r.get("target") or ""
        if "creativecommons" in t and not t.endswith("legalcode"):
            lic = "https:" + t if t.startswith("//") else t
    pub = "; ".join("%s, %s" % (p, places[i]) if i < len(places) else p for i, p in enumerate(pubs))
    parts = [x for x in ("%s%s" % (title, (", " + desc) if desc else ""), edition and ("version " + edition.replace("xml version, ", "")),
                         editors and ("edited by " + ", ".join(editors)), pub, date) if x]
    out.update(credit=". ".join(parts) + ".", licence=lic, copyright=avail[0] if avail else "", edition=edition)
    return out


def find_file(d: Path, code: str, name: str):
    for p in (d / code / "txt" / name, d / code / name, d / name):
        if p.exists():
            return p
    return None


def load_sources(a) -> dict:
    d = Path(a.dir)
    got = {}
    for code in ORDER:
        if a.only and code not in a.only:
            continue
        f = find_file(d, code, "%s.txt" % code)
        if f is None:
            got[code] = {"missing": str(d / code / "txt" / ("%s.txt" % code))}
            continue
        entries = read_entries(f)
        h = find_file(d, code, "%sheader.xml" % code)
        got[code] = {"file": f, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "entries": entries,
                     "header": header_credit(h) if h else {"credit": "", "licence": "", "copyright": "", "edition": ""}}
    return got


def entities(con) -> list:
    try:
        return con.execute("SELECT id, canonical, kind FROM entities").fetchall()
    except sqlite3.Error:
        return []


def links_for(parsed: dict, ents: list) -> list:
    """[(source, lnum, entity_id, how)]: exact by key, loose where only a vowel's length differs and no exact tie."""
    by_key, by_loose = {}, {}
    for eid, canon, _kind in ents:
        k = key_of(canon)
        if k:
            by_key.setdefault(k, []).append(eid)
            by_loose.setdefault(loose_of(k), []).append(eid)
    out = []
    for code, entries in parsed.items():
        for e in entries:
            exact = by_key.get(e["key"], [])
            for eid in exact:
                out.append((code, e["lnum"], eid, "exact"))
            for eid in by_loose.get(loose_of(e["key"]), []):
                if eid not in exact:
                    out.append((code, e["lnum"], eid, "loose"))
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS shelf_sources(code TEXT PRIMARY KEY, title TEXT, authors TEXT, year TEXT, credit TEXT,
  licence TEXT, copyright TEXT, file TEXT, sha256 TEXT, entries INTEGER, refs INTEGER, loaded_at TEXT, mark TEXT);
CREATE TABLE IF NOT EXISTS shelf_entries(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, lnum INTEGER NOT NULL,
  page TEXT, k1 TEXT, name TEXT, key TEXT, homonym TEXT, head TEXT, body TEXT, notes TEXT, UNIQUE(source, lnum));
CREATE INDEX IF NOT EXISTS ix_shelf_entries_key ON shelf_entries(key);
CREATE TABLE IF NOT EXISTS shelf_refs(id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, n INTEGER,
  work TEXT, ref TEXT, ours TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS ix_shelf_refs_entry ON shelf_refs(entry_id);
CREATE TABLE IF NOT EXISTS shelf_xrefs(entry_id INTEGER NOT NULL, name TEXT, key TEXT);
CREATE INDEX IF NOT EXISTS ix_shelf_xrefs_entry ON shelf_xrefs(entry_id);
CREATE TABLE IF NOT EXISTS shelf_links(entry_id INTEGER NOT NULL, entity_id INTEGER NOT NULL, how TEXT,
  UNIQUE(entry_id, entity_id));
CREATE INDEX IF NOT EXISTS ix_shelf_links_entity ON shelf_links(entity_id);
"""


def write(con, code: str, src: dict, entries: list, links: list):
    """One index's rows, replacing what an earlier load of it wrote; in the caller's transaction."""
    old = [r[0] for r in con.execute("SELECT id FROM shelf_entries WHERE source = ?", (code,))]
    for i in range(0, len(old), 500):
        q = ",".join("?" * len(old[i:i + 500]))
        for t in ("shelf_refs", "shelf_xrefs", "shelf_links"):
            con.execute("DELETE FROM %s WHERE entry_id IN (%s)" % (t, q), old[i:i + 500])
    con.execute("DELETE FROM shelf_entries WHERE source = ?", (code,))
    ids, nrefs = {}, 0
    for e in entries:
        cur = con.execute("INSERT INTO shelf_entries(source, lnum, page, k1, name, key, homonym, head, body, notes) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (code, e["lnum"], e["page"], e["k1"], e["name"], e["key"], e["h"] or None, e["head"], e["body"],
                           json.dumps(e["notes"], ensure_ascii=False) if e["notes"] else None))
        ids[e["lnum"]] = cur.lastrowid
        for r in e["refs"]:
            con.execute("INSERT INTO shelf_refs(entry_id, n, work, ref, ours, note) VALUES (?,?,?,?,?,?)",
                        (cur.lastrowid, r["n"], r["work"] or None, r["ref"], r["ours"] or None, r["note"] or None))
            nrefs += 1
        for x, k in e["xrefs"]:
            con.execute("INSERT INTO shelf_xrefs(entry_id, name, key) VALUES (?,?,?)", (cur.lastrowid, x, k))
    for c, lnum, eid, how in links:
        if c == code and lnum in ids:
            con.execute("INSERT OR IGNORE INTO shelf_links(entry_id, entity_id, how) VALUES (?,?,?)", (ids[lnum], eid, how))
    meta = SOURCES[code]
    con.execute("INSERT OR REPLACE INTO shelf_sources(code, title, authors, year, credit, licence, copyright, file, sha256, "
                "entries, refs, loaded_at, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (code, meta["title"], meta["authors"], meta["year"], src["header"]["credit"], src["header"]["licence"],
                 src["header"]["copyright"], str(src["file"]), src["sha256"], len(entries), nrefs, now(), MARK))
    return nrefs


def coverage(ents: list, links: list) -> dict:
    tied = {}
    for c, _l, eid, how in links:
        tied.setdefault(eid, set()).add(how)
    out = {}
    for eid, _canon, kind in ents:
        k = kind or "other"
        row = out.setdefault(k, [0, 0, 0])
        row[0] += 1
        if "exact" in tied.get(eid, set()):
            row[1] += 1
        elif "loose" in tied.get(eid, set()):
            row[2] += 1
    return out


def connect_ro(db: str, immutable: bool = False):
    q = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return sqlite3.connect(Path(db).resolve().as_uri() + q, uri=True, timeout=30)


def show_name(a) -> int:
    con = connect_ro(a.db, a.immutable)
    try:
        try:
            con.execute("SELECT 1 FROM shelf_entries LIMIT 1")
        except sqlite3.Error:
            say("the shelf is not loaded yet", "python scripts\\scholar_shelf.py --yes")
            return 1
        k = key_of(a.show)
        ents = [r for r in entities(con) if key_of(r[1]) in (k,) or loose_of(key_of(r[1])) == loose_of(k)]
        rows = con.execute("SELECT id, source, lnum, page, name, homonym, body FROM shelf_entries WHERE key = ? OR "
                           "id IN (SELECT entry_id FROM shelf_links WHERE entity_id IN (%s)) ORDER BY source, lnum"
                           % (",".join(str(e[0]) for e in ents) or "0"), (k,)).fetchall()
        print("scholar_shelf %s: %s" % (MARK, a.show))
        for eid, canon, kind in ents:
            docs = con.execute("SELECT d.code, COUNT(*) FROM entity_mentions m JOIN passages p ON p.id = m.passage_id JOIN "
                               "docs d ON d.id = p.doc_id WHERE m.entity_id = ? GROUP BY d.code ORDER BY 2 DESC",
                               (eid,)).fetchall()
            print("  ours: entity %d %s (%s): named %d time(s) in %s" % (eid, canon, kind, sum(n for _c, n in docs),
                                                                       ", ".join("%s %d" % (c, n) for c, n in docs) or "no text"))
        eids = ",".join(str(e[0]) for e in ents) or "0"
        for rid, src, lnum, page, name, hom, body in rows:
            how = sorted({r[0] for r in con.execute("SELECT how FROM shelf_links WHERE entry_id = ? AND entity_id IN (%s)"
                                                    % eids, (rid,))})
            print("  %s %s, page %s: %s%s%s" % (src.upper(), lnum, page, name, (" (%s)" % hom) if hom else "",
                                               ("   [tied to ours: %s]" % ", ".join(how)) if how else ""))
            print("      " + (body or "")[:a.width].replace("\n", " "))
            refs = con.execute("SELECT work, ref, ours, note FROM shelf_refs WHERE entry_id = ? ORDER BY id", (rid,)).fetchall()
            if refs:
                mine = [r for r in refs if r[2]]
                print("      references: %d; in our texts: %d" % (len(refs), len(mine)))
                for w, ref, ours, note in refs[:a.refs]:
                    print("        %s %s%s" % (w or "?", ref, ("   [ours: %s%s]" % (ours, "; " + note if note else "")) if ours else ""))
            xs = [r[0] for r in con.execute("SELECT name FROM shelf_xrefs WHERE entry_id = ?", (rid,))]
            if xs:
                print("      names it refers to: " + ", ".join(xs))
        if not rows:
            say("no index names %s" % a.show, "")
            return 0
        say("%d entr%s on %s" % (len(rows), "y" if len(rows) == 1 else "ies", a.show), "")
        return 0
    finally:
        con.close()


def credits(a) -> int:
    got = load_sources(a)
    for code in ORDER:
        s = got.get(code)
        if not s or s.get("missing"):
            print("  %s: not here (%s)" % (code, s.get("missing") if s else "?"))
            continue
        h = s["header"]
        print("  %s: %s %s Licence: %s" % (code, h["credit"], h["copyright"], h["licence"] or "?"))
    say("the credit lines, as each header gives them", "")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The scholars' shelf, step 1: three indexes of names (%s)" % MARK)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--dir", default="data/shelf/cologne")
    ap.add_argument("--only", nargs="*", choices=ORDER)
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--immutable", action="store_true", help="read the database as immutable (a backup copy)")
    ap.add_argument("--show", metavar="NAME")
    ap.add_argument("--refs", type=int, default=12, help="with --show: references listed per entry")
    ap.add_argument("--width", type=int, default=600, help="with --show: characters of each entry's text")
    ap.add_argument("--credits", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    try:   # a console that cannot show the diacritics gets \u escapes, not an error
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    os.chdir(ROOT)
    if a.show:
        return show_name(a)
    if a.credits:
        return credits(a)
    got = load_sources(a)
    missing = [c for c, s in got.items() if s.get("missing")]
    present = [c for c in ORDER if c in got and not got[c].get("missing")]
    small = [c for c in present if len(got[c]["entries"]) < MIN_ENTRIES]
    print("scholar_shelf %s" % MARK)
    for c in missing:
        print("  %s: not here: %s" % (c, got[c]["missing"]))
    if small:
        print("REFUSE: %s hold fewer than %d entries: not the index files" % (", ".join(small), MIN_ENTRIES))
        say("nothing written", "")
        return 1
    if not present:
        say("no index here (%s)" % a.dir, "download them first: see docs/SHELF_AND_SURYA_2026-10-21.md, section 2")
        return 1
    parsed = {c: [parse_entry(c, e) for e in got[c]["entries"]] for c in present}
    if not Path(a.db).exists():
        say("%s not found" % a.db, "")
        return 1
    con = connect_ro(a.db, a.immutable)
    try:
        ents = entities(con)
    finally:
        con.close()
    links = links_for(parsed, ents)
    for c in present:
        es = parsed[c]
        nref = sum(len(e["refs"]) for e in es)
        ours = sum(1 for e in es for r in e["refs"] if r["ours"])
        nl = {h: len({(l[1], l[2]) for l in links if l[0] == c and l[3] == h}) for h in ("exact", "loose")}
        tied = len({l[1] for l in links if l[0] == c})
        print("  %s: %d entries (%s), %d references (%d in our texts), %d bold names it refers to; %d entries tied to our "
              "names (%d exact ties, %d loose)" % (c, len(es), got[c]["file"], nref, ours, sum(len(e["xrefs"]) for e in es),
                                                   tied, nl["exact"], nl["loose"]))
        if not got[c]["header"]["credit"]:
            print("      (no header beside it: the credit line is missing)")
    cov = coverage(ents, links)
    for k in ("person", "place", "people", "river", "mountain", "deity", "other"):
        if k in cov:
            n, ex, lo = cov[k]
            print("  our %s names: %d; in an index: %d exactly, %d loosely; in none: %d" % (k, n, ex, lo, n - ex - lo))
    if not a.yes:
        say("%d index(es) read, %d entries, %d ties to our names; nothing written" % (
            len(present), sum(len(parsed[c]) for c in present), len(links)),
            "python scripts\\scholar_shelf.py --yes   (a backup first)",
            ["python scripts\\scholar_shelf.py --show Janaka   (after --yes)"])
        return 0
    import repair_text as rt
    if not os.environ.get("SA_SHELF_NO_DASHBOARD"):
        w = rt.writers_running(False, "")
        if w:
            say("not now: the dashboard runs a database writer (%s)" % ", ".join("%s %s" % (j.get("kind"), j.get("doc"))
                                                                              for j in w),
                "python scripts\\scholar_shelf.py --yes")
            return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(a.backup_dir) / ("context_pre_shelf_%s.db" % stamp)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if rt.run([rt.PY, rt.SCRIPTS / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        say("the backup failed; nothing was changed", "")
        return 1
    con = sqlite3.connect(a.db, timeout=60)
    try:
        con.executescript(SCHEMA)
        n = 0
        with con:
            for c in present:
                n += write(con, c, got[c], parsed[c], links)
    finally:
        con.close()
    say("the shelf holds %d entries from %s, %d references, %d ties to our names; backup %s" % (
        sum(len(parsed[c]) for c in present), ", ".join(present), n, len(links), backup),
        "python scripts\\scholar_shelf.py --show Janaka",
        ["python scripts\\scholar_shelf.py --credits   (the credit lines to print beside any use of it)"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
