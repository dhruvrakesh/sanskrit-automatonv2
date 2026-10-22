#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
gretil_library.py  (2026-10-22)  GRETIL_LIBRARY_2026_10_22

GRETIL's cumulative download (gretil.html, "Download All Sanskrit Texts": 1_sanskr.zip) as a library of witnesses:
what is in it, under what licence, and which of our texts each of its files reads. Read-only and free: no API is
called, the database is not opened, the zip is only read; --extract alone writes, one file into sources\\<doc>\\ with
its provenance beside it, for etext_witness.py --file.

  catalog   --catalog: every text of the zip's TEI plain-text transformations (1_sanskr/tei/transformations/
            plaintext/*.txt, 801, the mass conversion of 2019-20 of most of the legacy corpus): its title line, data entry,
            contribution, source edition, date and licence, as its header gives them -> data/gretil/catalog.jsonl
            (and --csv). The licence is read, not assumed: most say Creative Commons BY-NC-SA 4.0 (credit,
            non-commercial, share alike).
  match     --match: which GRETIL text reads which of our texts. Our OCR pages (data/raw_merged, else raw_vision,
            else raw; the texts of exports\\source_ledger.csv, or --doc) are sampled (--pages, 40), cut into their
            consonant skeleton (as etext_witness.skel cuts it: the consonants only, a nasal before a consonant
            dropped, so sandhi spacing, vowel signs and most OCR slips do not count) and into 6-letter grams. Each
            GRETIL text (IAST, read letter by letter into the same skeleton) is cut the same way. A text's score
            is the share of our sampled grams found in it: what of our scan it reads; less its baseline (what it
            reads of our texts at large, the median), the lift. "strong": a lift of 0.25 or more and 5 times its
            baseline; "a part or a parallel": the lift without the ratio (a big file that holds a part of our text,
            or a parallel text: the Maitrayani beside the Taittiriya); "possible": 0.10. Of a TEI file and a legacy
            file within 0.05 of each other the TEI file comes first (its licence). Written to data/gretil/
            match.jsonl (and --csv), the best five per text; --budget N stops after N seconds and the next run
            resumes (data/gretil/match_cache.jsonl).
  legacy    The zip holds GRETIL's legacy files too (1_sanskr/1_veda/... *.htm, 1,335 of them), and the mass
            conversion did not take them all: 380 have no TEI file, nor has any version of their work (the
            Satapatha's kandas, the Rgveda by mandala from Aufrecht's edition, the Atharvaveda, the Maitrayani
            Samhita, Akamatsu's Katyayana and Brhaspati, Hellwig's Angirasa). --catalog and --match read those as
            well, from their own headers: the edition, who typed
            it, the kind (a pada index is not a text and is left out; of a plain text, a text with pada markers
            and an analytic text of one work in one folder only the first is read) and the notice they carry:
            "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE
            FILE." -- no Creative Commons licence: such a witness is for checking our readings, and what may be
            published of it is the source edition's to say. --tei-only reads the TEI files alone.
  extract   --extract MEMBER --doc DOC: the member (the html transformation is the one etext_witness.py reads, as
            for the Markandeya and the Nirukta; a legacy file is read as it is, as for the Satapatha) into
            sources\\<doc>\\, with <file>.json beside it: the zip and its sha256, the member and its sha256, its
            GRETIL URL (the html transformation's, or the legacy file's own), the licence or the notice.

  python scripts\\gretil_library.py --catalog --csv exports\\gretil_catalog.csv
  python scripts\\gretil_library.py --match --csv exports\\gretil_match.csv
  python scripts\\gretil_library.py --extract 1_sanskr/tei/transformations/html/sa_yAska-nirukta.htm --doc nirukta

The zip: --zip, else sources\\gretil\\1_sanskr.zip, else inbox\\1_sanskr.zip. GRETIL's secondary resources
(6_sres.zip: dictionaries, concordances, an encyclopaedia) are listed by --catalog with the rights each needs; two
are under copyright (Vettam Mani's Puranic Encyclopaedia, 1964; Stchoupak, Nitti and Renou's dictionary, 1932):
private reading only.
"""
from __future__ import annotations
import argparse, csv, datetime, hashlib, html, json, os, random, re, sys, time, unicodedata, zipfile
from pathlib import Path

MARK = "GRETIL_LIBRARY_2026_10_22"
ROOT = Path(__file__).resolve().parent.parent
PLAIN = "/tei/transformations/plaintext/"
HTMLT = "/tei/transformations/html/"
TEI_URL = "https://gretil.sub.uni-goettingen.de/gretil/corpustei/"
GRETIL_URL = "https://gretil.sub.uni-goettingen.de/gretil/"   # + the member: a legacy file's own address
SKEL_V = 2                 # 2: Aufrecht's Vedic l with a line below, an m with a candrabindu (the cache is read again)
LEGACY_NOTE = re.compile(r"THIS\s+GRETIL\s+TEXT\s+FILE\s+IS\s+FOR\s+REFERENCE\s+PURPOSES\s+ONLY!?\s*COPYRIGHT\s+AND\s+"
                         r"TERMS\s+OF\s+USAGE\s+AS\s+FOR\s+SOURCE\s+FILE\.?", re.I)
REF_ONLY = "reference only (rights as the source edition's)"
KIND_RANK = {"plain": 0, "text": 1, "pada markers": 2, "analytic": 3, "pausa": 3}
INDEX = re.compile(r"PADA[- ]INDEX|VERSE INDEX|INDEX OF VERSES|INDEX OF PADAS")
N = 6                     # gram length, in skeleton letters (as etext_witness.py measures a witness)
CAP = 30000                # sampled grams kept per text of ours
STRONG, POSSIBLE = 0.25, 0.10   # on the lift; set on 22 Oct on texts whose e-text is known (Nirukta, Markandeya, Surya)
RATIO = 5.0      # a witness reads our text 5 times what it reads of our texts at large (the known pairs: the Markandeya
                 # 9.8, the Nirukta 15.8, the Surya 57); a big file that reads a part or a parallel does not (the
                 # Maitrayani beside the Taittiriya 4.1, the Santiparvan beside a smrti 3.1): "a part or a parallel"
PREFER_TEI = 0.05   # a TEI file (its CC licence, its html) within this lift of a legacy file is put first

# The secondary resources (6_sres.zip) and what they may be used for: the two under copyright are for private reading.
SRES = {
    "aufrcc": ("Aufrecht, Catalogus Catalogorum (1891-1903)", "public domain"),
    "vedconc": ("Bloomfield, A Vedic Concordance (1906)", "public domain"),
    "aptees": ("Apte, English-Sanskrit dictionary (1884)", "public domain"),
    "aptese": ("Apte, Sanskrit-English dictionary (1890)", "public domain"),
    "benfse": ("Benfey, Sanskrit-English dictionary (1866)", "public domain"),
    "boppsl": ("Bopp, Glossarium comparativum (1867)", "public domain"),
    "bores": ("Borooah, English-Sanskrit dictionary (1877)", "public domain"),
    "bursf": ("Burnouf, Dictionnaire classique sanscrit-francais (1866)", "public domain"),
    "cappse": ("Cappeller, Sanskrit-English dictionary (1891)", "public domain"),
    "cappsg": ("Cappeller, Sanskrit-Woerterbuch (1887)", "public domain"),
    "grasg_a": ("Grassmann, Woerterbuch zum Rig-Veda (1873)", "public domain"),
    "grasg_p": ("Grassmann, Woerterbuch zum Rig-Veda (1873)", "public domain"),
    "macdse": ("Macdonell, A Practical Sanskrit Dictionary (1924)", "public domain"),
    "mwes": ("Monier-Williams, English-Sanskrit dictionary (1851)", "public domain"),
    "mwse72": ("Monier-Williams, Sanskrit-English dictionary (1872)", "public domain"),
    "mwse": ("Monier-Williams, Sanskrit-English dictionary (1899)", "public domain"),
    "pwg": ("Boehtlingk and Roth, Sanskrit-Woerterbuch (1855-75)", "public domain"),
    "pwk": ("Boehtlingk, Sanskrit-Woerterbuch in kuerzerer Fassung (1879-89)", "public domain"),
    "schnzsw": ("Schmidt, Nachtraege zum Sanskrit-Woerterbuch (1928)", "public domain"),
    "skdss": ("Radhakantadeva, Sabdakalpadruma (1822-58)", "public domain"),
    "vcpss": ("Taranatha Tarkavacaspati, Vacaspatyam (1873-84)", "public domain"),
    "stcsf": ("Stchoupak, Nitti and Renou, Dictionnaire sanskrit-francais (1932)", "PROTECTED: private reading only"),
    "pese": ("Vettam Mani, Puranic Encyclopaedia (1964; English 1975)", "PROTECTED: private reading only"),
}

DEV_SKEL = re.compile("[\u0915-\u0939\u0958-\u095f]")
DEV_NASAL = re.compile("[\u0919\u091e\u0923\u0928\u092e]\u094d(?=[\u0915-\u0939])")
IAST_TOK = re.compile("(kh|gh|ch|jh|\u1e6dh|\u1e0dh|th|dh|ph|bh|\u1e37h|\u1e3bh|[kg\u1e45cj\u00f1\u1e6d\u1e0d\u1e47tdnpbmyrlv\u015b\u1e63sh\u1e3b])"
                      "|([a\u0101i\u012bu\u016b\u1e5b\u1e5d\u1e37\u1e39eo])|(\\s+)")
IAST_DEV = {"k": "\u0915", "kh": "\u0916", "g": "\u0917", "gh": "\u0918", "\u1e45": "\u0919", "c": "\u091a",
            "ch": "\u091b", "j": "\u091c", "jh": "\u091d", "\u00f1": "\u091e", "\u1e6d": "\u091f", "\u1e6dh": "\u0920",
            "\u1e0d": "\u0921", "\u1e0dh": "\u0922", "\u1e47": "\u0923", "t": "\u0924", "th": "\u0925", "d": "\u0926",
            "dh": "\u0927", "n": "\u0928", "p": "\u092a", "ph": "\u092b", "b": "\u092c", "bh": "\u092d", "m": "\u092e",
            "y": "\u092f", "r": "\u0930", "l": "\u0932", "v": "\u0935", "\u015b": "\u0936", "\u1e63": "\u0937",
            "s": "\u0938", "h": "\u0939", "\u1e37h": "\u0933\u0939", "\u1e3b": "\u0933", "\u1e3bh": "\u0933\u0939"}
CC = re.compile(r"Creative Commons ((?:Attribution|NonCommercial|ShareAlike|NoDerivatives|NoDerivs)(?:-(?:Attribution|"
                r"NonCommercial|ShareAlike|NoDerivatives|NoDerivs))*) (\d\.\d)")
CC_SHORT = {"Attribution": "BY", "NonCommercial": "NC", "ShareAlike": "SA", "NoDerivatives": "ND", "NoDerivs": "ND"}
NASALS = set("\u1e45\u00f1\u1e47nm")


def dev_skel(s: str) -> str:
    """The consonant skeleton of Devanagari, as etext_witness.skel() makes it."""
    return "".join(DEV_SKEL.findall(DEV_NASAL.sub("", s or "")))


def iast_skel(s: str) -> str:
    """The same skeleton read from IAST: each consonant (aspirates as one) in Devanagari, a nasal before a
    consonant dropped (as the anusvara), the Vedic l-dot between vowels read as the consonant it is, as is the l
    with a line below (Aufrecht's Rgveda: agnim \u012b\u1e3be); an m with a candrabindu is a nasal sign, not a consonant."""
    s = unicodedata.normalize("NFC", s or "").lower().replace("\u1e41", "\u1e43").replace("m\u0310", "\u1e43")
    out, prev_vowel, pending = [], False, None
    for cons, vow, space in IAST_TOK.findall(s):
        if cons:
            if pending is not None:
                if pending not in NASALS:
                    out.append(IAST_DEV[pending])
            pending = cons
            prev_vowel = False
        else:
            if pending is not None:
                out.append(IAST_DEV[pending])
                pending = None
            if vow == "\u1e37" and prev_vowel:       # agnim ILe: the Vedic consonant
                out.append("\u0933")
                prev_vowel = False
                continue
            prev_vowel = bool(vow)
    if pending is not None:
        out.append(IAST_DEV[pending])
    return "".join(out)


def grams(skel: str) -> set:
    return {skel[i:i + N] for i in range(0, max(0, len(skel) - N + 1))}


# ---- the zip -----------------------------------------------------------------------------------------------------
def find_zip(a) -> Path:
    for z in ([a.zip] if a.zip else []) + [ROOT / "sources" / "gretil" / "1_sanskr.zip", ROOT / "inbox" / "1_sanskr.zip"]:
        if z and Path(z).exists():
            return Path(z)
    raise SystemExit("no 1_sanskr.zip: give --zip, or put it in sources\\gretil\\ (GRETIL, gretil.html, "
                     "Download All Sanskrit Texts)")


def plain_members(zf) -> list:
    return sorted(n for n in zf.namelist() if PLAIN in n and n.endswith(".txt"))


def header_of(text: str) -> dict:
    """The plain-text transformation's own header: its title line and its ## fields."""
    lines = text.splitlines()
    h = {"title": (lines[0].strip() if lines else ""), "data_entry": "", "contribution": "", "date": "", "source": "",
         "licence": "", "legacy": ""}
    key = None
    for ln in lines[1:400]:
        t = ln.strip()
        if t == "# Text":
            break
        m = re.match(r"##\s*([^:]+):\s*(.*)$", t)
        if m:
            k = m.group(1).strip().lower()
            key = {"data entry": "data_entry", "contribution": "contribution", "date of this version": "date",
                   "source": "source", "licence": "licence", "license": "licence"}.get(k)
            if key and m.group(2).strip():
                h[key] = m.group(2).strip()
            continue
        if t.startswith("#"):
            key = None
            continue
        if key in ("source", "licence") and t:
            h[key] = (h[key] + " " + t.lstrip("- ").strip()).strip()
        lm = re.search(r"from\s+(\S+\.htm)\b", t)
        if lm and not h["legacy"]:
            h["legacy"] = lm.group(1)
    h["licence"] = h["licence"][:1000]
    m = CC.search(h["licence"])
    h["cc"] = ("CC " + "-".join(CC_SHORT.get(w, w) for w in m.group(1).split("-")) + " " + m.group(2)) if m else ""
    ys = [int(y) for y in re.findall(r"\b(1[6-9]\d\d|20[0-2]\d)\b", h["source"])]
    h["source_year"] = max(ys) if ys else None
    return h


def body_of(text: str) -> str:
    i = text.find("\n# Text")
    return text[i + 7:] if i >= 0 else text


def tei_url(member: str) -> str:
    return TEI_URL + Path(member).stem + ".xml"


def url_of(member: str) -> str:
    """The member's own address on GRETIL: a transformation is at corpustei/transformations/html/X.htm (whence the
    Nirukta's and the Markandeya's were fetched, the same bytes as the zip's), a legacy file at its path (whence the
    Satapatha's kandas were, the same text as the zip's but for its line endings)."""
    if "/tei/" in member:
        return GRETIL_URL + "corpustei/" + member.split("/tei/", 1)[1]
    return GRETIL_URL + member


# ---- the legacy files --------------------------------------------------------------------------------------------
def html_text(raw: bytes) -> str:
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style|head)\b.*?</\1\s*>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p\s*>|</h\d\s*>|</div\s*>|</tr\s*>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _header_end(lines: list) -> int:
    """Where a legacy file's header ends: after GRETIL's own address (For further information see: .../gretil.htm),
    else a few lines after the notice, else at line 40."""
    for i, l in enumerate(lines[:120]):
        if re.search(r"gretil(?:/gretil)?\.htm\b", l, re.I) and "gretdia" not in l:
            return i + 1
    for i, l in enumerate(lines[:120]):
        if re.search(r"FOR\s+REFERENCE\s+PURPOSES", l, re.I):
            return min(len(lines), i + 8)
    return min(len(lines), 40)


SRC_START = re.compile(r"(?i)\b(based on|edition|ed\.|edited|text used|source:)")
NOTICE_LINE = re.compile(r"(?i)FOR\s+REFERENCE\s+PURPOSES|COPYRIGHT\s+AND\s+TERMS\s+OF\s+USAGE")
SRC_STOP = re.compile(r"(?i)^(input|text input|data input|data entry|entered|typed|version|revised|this\s+gretil|unless|"
                      r"note\b|n\.\s?b\.|\(\d+\)|for\s+a\s+comprehensive|text converted)")


def legacy_header(raw: bytes) -> dict:
    """A legacy file's header, which is free text: its title, the edition it was typed from (and that edition's
    year), who typed it, what kind of file it is, and the notice or licence it carries."""
    s = raw.decode("utf-8", "replace")
    tm = re.search(r"(?is)<title[^>]*>(.*?)</title\s*>", s)
    lines = [re.sub(r"\s+", " ", l).strip() for l in html_text(raw).splitlines()]
    lines = [l for l in lines if l]
    head = lines[:_header_end(lines)]
    flat = " ".join(head)
    title = re.sub(r"\s+", " ", html.unescape(tm.group(1))).strip() if tm else (head[0] if head else "")
    src, on = [], False
    for l in head[1:]:
        if not on and SRC_START.search(l) and not NOTICE_LINE.search(l):
            on = True
        elif on and (SRC_STOP.search(l) or NOTICE_LINE.search(l) or re.fullmatch(r"[A-Z0-9 ,.;:'()\-]{6,}", l) or len(src) >= 6):
            break
        if on:
            src.append(l)
    source = " ".join(src)[:600]
    de = ""
    for l in head:
        m = re.search(r"(?i)\b(?:input|entered|typed)\s+by\s+(.+)$", l)
        if m:
            de = m.group(1).strip().rstrip(".")
            break
    kind = ("index" if INDEX.search(flat) or INDEX.search(title.upper()) else
            "pada markers" if "PADA MARKERS" in flat else
            "analytic" if re.search(r"ANALYTIC|COMPOUND ANALYSIS", flat) else
            "pausa" if "TEXT IN PAUSA" in flat else
            "plain" if re.search(r"PLAIN TEXT|PLAIN VERSION", flat) else "text")
    note = LEGACY_NOTE.search(flat)
    if note:
        lic = "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE."
    else:
        m = CC.search(flat) or re.search(r"(?i)[^.]{0,120}\bcopyright\b[^.]{0,160}", flat)
        lic = m.group(0).strip() if m else ""
    m = CC.search(flat)
    cc = ("CC " + "-".join(CC_SHORT.get(w, w) for w in m.group(1).split("-")) + " " + m.group(2)) if m else ""
    ys = [int(y) for y in re.findall(r"\b(1[6-9]\d\d|20[0-2]\d)\b", source)]
    return {"title": title, "data_entry": de, "contribution": "", "date": "", "source": source, "licence": lic[:1000],
            "legacy": "", "cc": cc, "source_year": max(ys) if ys else None, "kind": kind,
            "rights": REF_ONLY if note else (cc or "read its header")}


def legacy_body(raw: bytes) -> str:
    lines = html_text(raw).splitlines()
    kept = [l for l in lines if l.strip()]
    return "\n".join(kept[_header_end([re.sub(r"\s+", " ", l).strip() for l in kept]):])


def _work(title: str) -> str:
    t = re.sub(r"(?i)[,;:.\s(]*(plain text version|plain version|plain text|text with pada markers|pada index|"
               r"analytic(?:al)? (?:text )?version|analytic text|text with compound analysis|unaccented text|"
               r"accented text)[)\s.]*$", "", title or "")
    return re.sub(r"\s+", " ", t).strip().lower()


def _base(name: str) -> str:
    """GRETIL's name for a work without its version letter: ram_03pu, ram_03au -> ram_03; manu2p_u, manu2a_u -> manu2;
    sb_01_u -> sb_01 (asvbc_1u and asvbc_2u stay two: the two halves of the Buddhacarita)."""
    return re.sub(r"(?i)_*[apixms]?_*u\.htm$", "", name).lower()


def legacy_members(zf, converted: set) -> list:
    """The legacy files the TEI conversion did not take (their name is in no TEI file's "from X.htm"), each with its
    header (a file is taken when its name, or that of another version of its work, is a TEI file's "from X.htm");
    a pada index is not a text, and of the versions of one work (one folder, one name but for the version
    letter, one title but for "plain text", "analytic text"...: plain, text, with pada markers, analytic or in pausa)
    only the first by that order is read: the others are marked variant_of."""
    rows = []
    cb = {_base(x) for x in converted}
    for n in sorted(zf.namelist()):
        if "/tei/" in n or not n.lower().endswith(".htm") or Path(n).name in converted or _base(Path(n).name) in cb:
            continue
        with zf.open(n) as f:
            head = f.read(16000)
        h = legacy_header(head)
        rows.append(dict(member=n, html=n, bytes=zf.getinfo(n).file_size, tei="", url=url_of(n), section="legacy",
                         variant_of="", **h))
    best = {}
    for r in rows:
        if r["kind"] == "index":
            continue
        k = (str(Path(r["member"]).parent), _base(Path(r["member"]).name), _work(r["title"]))
        if k not in best or (KIND_RANK[r["kind"]], r["member"]) < (KIND_RANK[best[k]["kind"]], best[k]["member"]):
            best[k] = r
    for r in rows:
        if r["kind"] == "index":
            continue
        b = best[(str(Path(r["member"]).parent), _base(Path(r["member"]).name), _work(r["title"]))]
        if b is not r:
            r["variant_of"] = b["member"]
    return rows


def readable(r: dict) -> bool:
    return r.get("kind") != "index" and not r.get("variant_of")


# ---- catalog -----------------------------------------------------------------------------------------------------
def catalog(a) -> int:
    z = find_zip(a)
    out = Path(a.out_dir) / "catalog.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with zipfile.ZipFile(z) as zf:
        for m in plain_members(zf):
            info = zf.getinfo(m)
            t = zf.read(m).decode("utf-8", "replace")
            h = header_of(t)
            rows.append(dict(member=m, html=m.replace(PLAIN, HTMLT)[:-4] + ".htm", bytes=info.file_size,
                             tei=tei_url(m), url=url_of(m.replace(PLAIN, HTMLT)[:-4] + ".htm"), section="tei", kind="text", variant_of="",
                             rights=h["cc"] or "read its header", **h))
        tei_rows = list(rows)
        if not a.tei_only:
            rows += legacy_members(zf, {r["legacy"] for r in tei_rows if r["legacy"]})
    legacy = [r for r in rows if r["section"] == "legacy"]
    lic = {}
    for r in tei_rows:
        lic[r["cc"] or "no CC licence named"] = lic.get(r["cc"] or "no CC licence named", 0) + 1
    recent = sum(1 for r in tei_rows if (r["source_year"] or 0) >= 1960)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if a.csv:
        Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["member", "title", "source", "source_year", "data_entry", "date", "cc", "licence", "bytes",
                        "section", "kind", "variant_of", "rights", "url"])
            for r in rows:
                w.writerow([r["member"], r["title"], r["source"], r["source_year"] or "", r["data_entry"], r["date"],
                            r["cc"], r["licence"], r["bytes"], r["section"], r["kind"], r["variant_of"], r["rights"],
                            r["url"]])
    sres = Path(z).with_name("6_sres.zip")
    if sres.exists():
        with zipfile.ZipFile(sres) as zs:
            for n in sorted(x for x in zs.namelist() if x.endswith(".htm")):
                k = Path(n).stem.replace("_u", "").replace("_au", "_a").replace("_pu", "_p")
                k = k[:-1] if k.endswith("u") and k[:-1] in SRES else k
                what, rights = SRES.get(k, ("(not in this list)", "read its header"))
                print("  6_sres: %-34s %-58s %s" % (Path(n).name, what, rights))
    print("%s: %d texts in %s, written %s" % (MARK, len(tei_rows), z.name, out))
    print("  licences: " + "; ".join("%s %d" % (k, v) for k, v in sorted(lic.items(), key=lambda x: -x[1])))
    print("  typed from an edition of 1960 or later (its editor's rights may stand): %d" % recent)
    if legacy:
        read = [r for r in legacy if readable(r)]
        print("  legacy files the TEI conversion did not take: %d; read by --match: %d (pada indexes %d and variants "
              "%d left out)" % (len(legacy), len(read), sum(1 for r in legacy if r["kind"] == "index"),
                                sum(1 for r in legacy if r["variant_of"])))
        print("  of those read, %s: %d; of an edition of 1960 or later: %d" % (
            REF_ONLY, sum(1 for r in read if r["rights"] == REF_ONLY),
            sum(1 for r in read if (r["source_year"] or 0) >= 1960)))
    print("VERDICT: %d GRETIL texts catalogued (%d TEI, %d legacy), each with its own licence line or notice" % (
        len(rows), len(tei_rows), len(legacy)))
    print("NEXT: python scripts\\gretil_library.py --match --csv exports\\gretil_match.csv")
    return 0


# ---- match -------------------------------------------------------------------------------------------------------
def our_docs(a) -> list:
    if a.doc:
        return list(a.doc)
    led = ROOT / "exports" / "source_ledger.csv"
    if not led.exists():
        raise SystemExit("no exports\\source_ledger.csv: run python scripts\\source_fidelity.py --ledger --csv "
                         "exports\\source_ledger.csv, or give --doc")
    out = []
    with open(led, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            d = r.get("doc") or ""
            if d and "__w_" not in d and (r.get("source") or "") != "e-text" and (r.get("register") or "") != "witness":
                out.append(d)
    return out


def page_files(doc: str):
    for sub in ("raw_merged", "raw_vision", "raw"):
        folder = ROOT / "data" / sub
        if not folder.exists():
            continue
        fs = sorted(p for p in folder.glob("%s_[0-9]*.jsonl" % doc) if re.fullmatch(re.escape(doc) + r"_\d{3,5}\.jsonl", p.name))
        if fs:
            return sub, fs
    return "", []


def doc_grams(doc: str, pages: int):
    sub, fs = page_files(doc)
    if not fs:
        return sub, 0, set()
    step = max(1, len(fs) // pages) if pages else 1
    pick = fs[::step][:pages] if pages else fs
    g = set()
    for p in pick:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                t = json.loads(line).get("text") or ""
            except ValueError:
                continue
            g |= grams(dev_skel(t))
    if len(g) > CAP:
        g = set(random.Random(doc).sample(sorted(g), CAP))
    return sub, len(pick), g


def match(a) -> int:
    z = find_zip(a)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = our_docs(a)
    t0 = time.time()
    D = {}
    for d in docs:
        sub, n, g = doc_grams(d, a.pages)
        D[d] = (sub, n, g)
    have = {d: v for d, v in D.items() if v[2]}
    print("%s: %d of our texts with OCR pages here (%s); %d without" % (
        MARK, len(have), ", ".join(sorted({v[0] for v in have.values()})), len(D) - len(have)))
    idx = {}
    for d, (_, _, g) in have.items():
        for x in g:
            idx.setdefault(x, []).append(d)
    union = set(idx)
    sig = hashlib.sha256(json.dumps(sorted((d, len(v[2])) for d, v in have.items())).encode() + str(a.pages).encode()
                         + (b"" if SKEL_V == 1 else ("skel%d" % SKEL_V).encode())).hexdigest()[:16]
    cache_p = out_dir / "match_cache.jsonl"
    cache = {}
    if cache_p.exists():
        lines = cache_p.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[0]).get("sig") == sig:
            for ln in lines[1:]:
                r = json.loads(ln)
                cache[r["member"]] = r
        else:
            cache_p.replace(cache_p.with_name("match_cache.jsonl.old"))
    if not cache_p.exists():
        cache_p.write_text(json.dumps({"sig": sig, "mark": MARK, "zip": z.name}) + "\n", encoding="utf-8")
    stopped = False

    def score(m, G, **extra):
        hits = {}
        for x in G & union:
            for d in idx[x]:
                hits[d] = hits.get(d, 0) + 1
        r = dict({"member": m, "grams": len(G), "hits": {d: n for d, n in hits.items() if n >= 20}}, **extra)
        cache[m] = r
        cf.write(json.dumps(r, ensure_ascii=False) + "\n")
        cf.flush()

    with zipfile.ZipFile(z) as zf, open(cache_p, "a", encoding="utf-8") as cf:
        members = plain_members(zf)
        for m in members:
            if m in cache:
                continue
            if a.budget and time.time() - t0 > a.budget:
                stopped = True
                break
            t = zf.read(m).decode("utf-8", "replace")
            h = header_of(t)
            score(m, grams(iast_skel(body_of(t))), title=h["title"], legacy=h["legacy"], section="tei",
                  rights=h["cc"] or "read its header")
        if not stopped and not a.tei_only:
            converted = {cache[m].get("legacy") for m in members if cache[m].get("legacy")}
            leg = [r for r in legacy_members(zf, converted) if readable(r)]
            for r in leg:
                m = r["member"]
                members.append(m)
                if m in cache:
                    continue
                if a.budget and time.time() - t0 > a.budget:
                    stopped = True
                    break
                score(m, grams(iast_skel(legacy_body(zf.read(m)))), title=r["title"], section="legacy",
                      kind=r["kind"], rights=r["rights"], source_year=r["source_year"])
    done = sum(1 for m in members if m in cache)
    scope = [m for m in members if m in cache]
    # A large GRETIL text holds most common 6-letter sequences: it "reads" a share of any text of ours by chance (the
    # Moksopaya, the Naradapurana, about 0.2). Its baseline is the median of what it reads of all our texts; the lift
    # over it is the score.
    base = {}
    for m in scope:
        vals = sorted(cache[m]["hits"].get(d, 0) / max(1, len(v[2])) for d, v in have.items())
        base[m] = vals[len(vals) // 2] if vals else 0.0
    rows = []
    for d, (sub, n, g) in D.items():
        cands = []
        for m in scope:
            r = cache[m]
            h = r["hits"].get(d)
            if h:
                reads = h / max(1, len(g))
                cands.append({"member": m, "html": m.replace(PLAIN, HTMLT)[:-4] + ".htm" if PLAIN in m else m,
                              "title": r.get("title", ""), "section": r.get("section", "tei"),
                              "rights": r.get("rights", ""), "hits": h, "reads": round(reads, 4),
                              "baseline": round(base.get(m, 0.0), 4), "lift": round(reads - base.get(m, 0.0), 4),
                              "ratio": round(reads / max(base.get(m, 0.0), 0.001), 1),
                              "of_gretil": round(h / max(1, r.get("grams", 1)), 4),
                              "named": named(d, m) or (r.get("section") == "legacy" and
                                                       named(d, r.get("title", "") + ".htm"))})
        cands.sort(key=lambda c: -c["lift"])
        if cands and cands[0]["section"] == "legacy":
            tei = [c for c in cands if c["section"] == "tei" and c["lift"] >= cands[0]["lift"] - PREFER_TEI]
            if tei:
                cands.remove(tei[0])
                cands.insert(0, dict(tei[0], preferred="its CC licence, within %.2f of %s" % (
                    PREFER_TEI, Path(cands[0]["member"]).name)))
        best = cands[0]["lift"] if cands else 0.0
        ratio = cands[0]["ratio"] if cands else 0.0
        verdict = ("no OCR pages here" if not g else "strong" if best >= STRONG and ratio >= RATIO else
                   "a part or a parallel" if best >= STRONG else "possible" if best >= POSSIBLE else "none")
        if verdict in ("none", "possible") and any(c["named"] and c["lift"] >= POSSIBLE / 2 for c in cands[:10]):
            verdict = "possible, by name"
            cands.sort(key=lambda c: (not c["named"], -c["lift"]))
        rows.append({"doc": d, "pages_from": sub, "pages_sampled": n, "grams": len(g), "verdict": verdict,
                     "top": cands[:5]})
    with open(out_dir / "match.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if a.csv:
        Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["doc", "verdict", "lift", "reads", "baseline", "gretil_title", "member", "of_gretil", "second",
                        "pages_from", "section", "rights", "ratio"])
            for r in rows:
                t = r["top"]
                w.writerow([r["doc"], r["verdict"], t[0]["lift"] if t else "", t[0]["reads"] if t else "",
                            t[0]["baseline"] if t else "", t[0]["title"] if t else "", t[0]["html"] if t else "",
                            t[0]["of_gretil"] if t else "",
                            ("%s %s" % (t[1]["lift"], t[1]["title"])) if len(t) > 1 else "", r["pages_from"],
                            t[0]["section"] if t else "", t[0]["rights"] if t else "", t[0]["ratio"] if t else ""])
    for r in sorted(rows, key=lambda r: -(r["top"][0]["lift"] if r["top"] else 0)):
        t = r["top"]
        print("  %-44s %-20s %s" % (r["doc"][:44], r["verdict"], ("lift %.2f (reads %.2f, %.0fx) %s [%s%s]" % (
            t[0]["lift"], t[0]["reads"], t[0]["ratio"], t[0]["title"][:44], Path(t[0]["html"]).name,
            (", legacy" + (": reference only" if t[0]["rights"] == REF_ONLY else "")) if t[0]["section"] == "legacy"
            else "")) if t else ""))
    n_strong = sum(1 for r in rows if r["verdict"] == "strong")
    print("written: %s" % (out_dir / "match.jsonl"))
    if stopped:
        print("VERDICT: stopped after %ds with %d of %d GRETIL texts read; run it again to go on" % (a.budget, done, len(members)))
    else:
        print("VERDICT: %d of our texts have a GRETIL text that reads %d%% or more of their sampled letters above its "
              "baseline, %d times what it reads of our texts at large; %d a part or a parallel; %d possible" % (
                  n_strong, int(STRONG * 100), RATIO, sum(1 for r in rows if r["verdict"] == "a part or a parallel"),
                  sum(1 for r in rows if r["verdict"].startswith("possible"))))
    # GRETIL_NEXT_2026_10_22: the commands themselves, for the strong matches that have no witness yet (on 22 Oct
    # "--extract MEMBER --doc DOC" was run as printed)
    todo = [r for r in sorted(rows, key=lambda r: -(r["top"][0]["lift"] if r["top"] else 0))
            if r["verdict"] == "strong" and not any((ROOT / "data" / "raw_witness").glob(r["doc"] + "__w_*"))
            ] if not stopped else []
    for r in todo[:3]:
        m = r["top"][0]["html"]
        print("NEXT: python scripts\\gretil_library.py --extract %s --doc %s" % (m, r["doc"]))
        print("      python scripts\\etext_witness.py --doc %s --file sources\\%s\\%s   (the preview)" % (
            r["doc"], r["doc"], Path(m).name))
    if len(todo) > 3:
        print("ALSO: %d more strong matches without a witness: %s" % (len(todo) - 3, ", ".join(r["doc"] for r in todo[3:])))
    if not todo and not stopped:
        print("NEXT: every strong match has its witness (data\\raw_witness); python scripts\\ocr_benchmark.py measures "
              "our readings against them all")
    return 0


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").lower()
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)))


def named(doc: str, member: str) -> bool:
    """Our text's code names the GRETIL file (lalitavistara, markandeya, nirukta): a hint for a scan too damaged for
    its letters to show it."""
    m = _plain(Path(member).stem)
    toks = [_plain(t) for t in re.split(r"[_\-\s]+|(?<=[a-z])(?=[A-Z])", doc)]
    stop = {"smriti", "purana", "upapurana", "sanhita", "samhita", "with", "veda", "shiksha", "sthanam", "dhanur"}
    return any(len(t) >= 6 and t not in stop and t in m for t in toks)


# ---- extract -----------------------------------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def extract(a) -> int:
    if not a.doc or len(a.doc) != 1 or not re.fullmatch(r"[A-Za-z0-9_\-]+", a.doc[0]):
        raise SystemExit("--extract needs one --doc (letters, digits, _ and -)")
    doc = a.doc[0]
    z = find_zip(a)
    with zipfile.ZipFile(z) as zf:
        if a.extract not in zf.namelist():
            raise SystemExit("not in %s: %s" % (z.name, a.extract))
        data = zf.read(a.extract)
        if "/tei/" in a.extract:
            plain = a.extract.replace(HTMLT, PLAIN)[:-4] + ".txt" if a.extract.endswith(".htm") else a.extract
            lic = header_of(zf.read(plain).decode("utf-8", "replace"))["licence"] if plain in zf.namelist() else ""
            source = ""
        else:   # a legacy file: its own header, its notice
            lh = legacy_header(data[:16000])
            lic, source = lh["licence"], lh["source"]
    dest_dir = ROOT / "sources" / doc
    dest = dest_dir / Path(a.extract).name
    if dest.exists():
        if dest.read_bytes() == data:
            print("already there: %s (the same bytes)" % dest)
            print("NEXT: python scripts\\etext_witness.py --doc %s --file %s" % (doc, dest.relative_to(ROOT)))
            return 0
        if not a.force:
            print("REFUSE: %s exists with other bytes; --force keeps it as .bak_gretil_<date> and writes this one" % dest)
            return 1
        dest.replace(dest.with_name(dest.name + ".bak_gretil_" + datetime.date.today().strftime("%Y%m%d")))
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    side = {"doc": doc, "kind": "etext", "url": url_of(a.extract), "zip": z.name, "zip_sha256": sha256_of(z),
            "member": a.extract, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "licence": lic,
            "at": datetime.datetime.now().isoformat(timespec="seconds"), "mark": MARK}
    if source:
        side["source"] = source
    dest.with_name(dest.name + ".json").write_text(json.dumps(side, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote %s (%d bytes) and its provenance beside it" % (dest, len(data)))
    print("VERDICT: %s is in sources\\%s; nothing else written; its licence: %s" % (dest.name, doc, lic or "(read its header)"))
    print("NEXT: python scripts\\etext_witness.py --doc %s --file %s   (the preview; then --write)"
          % (doc, dest.relative_to(ROOT)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GRETIL's cumulative download as a library of witnesses (read-only)")
    ap.add_argument("--zip", default="")
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--match", action="store_true")
    ap.add_argument("--extract", default="", metavar="MEMBER")
    ap.add_argument("--doc", action="append", default=[])
    ap.add_argument("--pages", type=int, default=40, help="pages of ours sampled per text (0: all)")
    ap.add_argument("--budget", type=int, default=0, help="seconds; 0: no limit (the next run resumes)")
    ap.add_argument("--root", default="", help="the repository (default: the one this script is in)")
    ap.add_argument("--out-dir", default="", help="where the catalog and the match go (data/gretil)")
    ap.add_argument("--csv", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tei-only", action="store_true", help="the TEI files alone, not the legacy files")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):   # a pipe on Windows is cp1252: a title in IAST must not stop the run
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    global ROOT
    if a.root:
        ROOT = Path(a.root).resolve()
    a.out_dir = a.out_dir or str(ROOT / "data" / "gretil")
    if a.extract:
        return extract(a)
    if a.match:
        return match(a)
    if a.catalog:
        return catalog(a)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
