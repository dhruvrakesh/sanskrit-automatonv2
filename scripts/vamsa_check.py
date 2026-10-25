#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_check.py  (2026-10-25)  VAMSA_CHECK_2026_10_25

The indexes' kinships read against the Sanskrit itself. Free: no model is called, data/context.db is not opened,
GRETIL's zip and data/shelf/kin.db are only read; --yes alone writes, and only its own store (data/shelf/vamsa.db)
and two exports.

  cited     The Purana Index (V. R. R. Dikshitar, 1951-55) gives the verse of each statement: "Vi. IV. 19. 10",
            "Bh\u0101. IX. 22. 7", "Br. III. 70. 46", "M. 49. 42", "V\u0101. 99. 160". Where the text is in GRETIL's TEI the
            verse is found and read: the Vi\u1e63\u1e47u in two editions (the Venkatesvara print of 1910, and M. M. Pathak's
            critical edition), the Bh\u0101gavata, the Brahm\u0101\u1e47\u1e0da (Venkatesvara print; the index's p\u0101da II is GRETIL's
            part 1, as its colophons show, III is part 2, IV part 3) and the Matsya (chapters 1-176 only). Both
            names stand in the verse or within two verses of it (the index's edition and GRETIL's may number a verse
            or two apart), one of them, or neither. GRETIL has no V\u0101yu but the Rev\u0101kha\u1e47\u1e0da ascribed to it: the V\u0101yu's
            citations are "not held", as are the Matsya's after chapter 176.
  together  For every relation of the three indexes: the verses of the Mah\u0101bh\u0101rata (the critical edition's e-text,
            (C) BORI 1999; GRETIL's file is "for reference purposes only", so only counts and references are kept,
            never its words), of the Hariva\u1e43\u015ba (critical edition) and of the R\u0101m\u0101ya\u1e47a (critical edition) in which
            both names stand: how many, and the first.
How a name is found: by its letters, as compared (the vowels by quality, a and a-long one, e and o and r apart; the
anusvara and any nasal before a consonant one sign; the visarga left out; an avagraha read as its a): the name less its
last vowel (or, ending in a consonant, its last letter) at the start of a word. In the cited verse and the two either
side of it a name of four letters or more may also stand inside a word, as the prints that join the sandhi have it
(tasmaccandrah). A name of two consonants or fewer is looked for by its case forms (Aja: ajah, ajad, ajasya ...; the
neuter plural left out). An old spelling (Chola, Shiva) is tried as c and s' when the name is not found as printed. A
name the index gives in English ("Gods", "Paurava race") is not looked for. It is a match of words, not a reading:
"both names in the verse" says where to read, not that the verse states the relation; a reading that differs (the
index's Daksa where the verse has Rksa) is "one name", and the verse shows it.

  python scripts\\vamsa_check.py                  the plan: every check made and counted, nothing written
  python scripts\\vamsa_check.py --yes            and written: data\\shelf\\vamsa.db, exports\\vamsa_checks.csv,
                                                  exports\\vamsa_summary.json
  python scripts\\vamsa_check.py --name Janamejaya   the checks of the relations that name him (from vamsa.db)
  python scripts\\vamsa_check.py --scheduled      for the maintenance task: --yes only when kin.db or the zip
                                                  changed since the last run

The zip: --zip, else sources\\gretil\\1_sanskr.zip, else inbox\\1_sanskr.zip (gretil_library.py's). The last lines
are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations

import argparse, bisect, collections, csv, datetime, hashlib, html, json, os, re, sqlite3, sys, time, unicodedata, zipfile
from pathlib import Path

MARK = "VAMSA_CHECK_2026_10_25"
SCHEME = 8                       # the matching rules: a change re-checks everything
ROOT = Path(__file__).resolve().parent.parent
SOURCES = ("pui", "vei", "inm")
SHORT = {"pui": "Purana Index", "vei": "Vedic Index", "inm": "Soerensen"}
PLAIN = "/tei/transformations/plaintext/"

# the texts: code -> (zip member, the ref's prefix, title, edition, rights, the words may be shown)
TEXTS = {
    "vi": ("sa_viSNupurANa.txt", "vip", "Vi\u1e63\u1e47upur\u0101\u1e47a",
           "Bombay: Venkatesvara Steam Press, 1910; data entry: the Sansknet Project", "CC BY-NC-SA 4.0", True),
    "vic": ("sa_viSNupurANa-crit.txt", "ViP", "Vi\u1e63\u1e47upur\u0101\u1e47a, critical edition",
            "M. M. Pathak, Vadodara: Oriental Institute, 1997-99; data entry: Peter Schreiner", "CC BY-NC-SA 4.0", True),
    "bh": ("sa_bhAgavatapurANa.txt", "bhp", "Bh\u0101gavatapur\u0101\u1e47a", "data entry: Ulrich Stiehl", "CC BY-NC-SA 4.0", True),
    "br": ("sa_brahmANDapurANa.txt", "bndp", "Brahm\u0101\u1e47\u1e0dapur\u0101\u1e47a",
           "Bombay: Venkatesvara Steam Press; data entry: the Sansknet Project", "CC BY-NC-SA 4.0", True),
    "m": ("sa_matsyapurANa1-176.txt", "MatsP", "Matsyapur\u0101\u1e47a, 1-176",
          "Calcutta: Caukhamba Vidyabhavan, 1954; data entry: Oliver Hellwig", "CC BY-NC-SA 4.0", True),
    "hv": ("sa_harivaMza.txt", "HV", "Hariva\u1e43\u015ba, critical edition",
           "the constituted text of the critical edition; data entry: Atul Agarwala and others", "CC BY-NC-SA 4.0", True),
    "ram": ("sa_rAmAyaNa.txt", "R", "V\u0101lm\u012bki: R\u0101m\u0101ya\u1e47a, critical edition",
            "data entry: Muneo Tokunaga; revised by John Smith", "CC BY-NC-SA 4.0", True),
    "mbh": ("mbh1-18u.htm", "", "Mah\u0101bh\u0101rata, critical edition",
            "e-text (C) Bhandarkar Oriental Research Institute, Pune, 1999; Muneo Tokunaga et al., revised by John "
            "Smith", "reference only: GRETIL's file is for reference purposes only (BORI asks that copies of the text "
            "not be given to others); counts and references alone are kept", False),
}
SHOWN = {"vi": "Vi\u1e63\u1e47u (1910)", "vic": "Vi\u1e63\u1e47u (crit.)", "bh": "Bh\u0101gavata", "br": "Brahm\u0101\u1e47\u1e0da", "m": "Matsya",
         "hv": "Hariva\u1e43\u015ba", "ram": "R\u0101m\u0101ya\u1e47a", "mbh": "Mah\u0101bh\u0101rata"}
EPICS = ("mbh", "hv", "ram")
CITED = {"vi": ("vi", "vic"), "bh": ("bh",), "br": ("br",), "m": ("m",)}
BR_PART = {1: 1, 2: 1, 3: 2, 4: 3}        # the index's pada -> GRETIL's part (pada II's chapters run on in part 1)
MATSYA_LAST = 176
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
         "XII": 12}
ORDER = ["both", "one", "neither", "no verse", "not held", "no citation", "not looked for"]
ENGLISH = {"gods", "god", "race", "family", "people", "kings", "king", "sons", "son", "daughters", "daughter", "the",
           "of", "and", "tribe", "clan", "dynasty", "line", "brothers", "wives", "children", "asuras", "devas",
           "sages", "seers", "demons", "brahmanas", "descendants", "ancestors", "others", "all", "his", "her",
           "their", "country", "city", "kingdom", "mother", "father", "wife", "husband"}

# ---- the letters ---------------------------------------------------------------------------------------------
ASP = ("kh", "gh", "ch", "jh", "\u1e6dh", "\u1e0dh", "th", "dh", "ph", "bh")
ONE = {"kh": "K", "gh": "G", "ch": "C", "jh": "J", "\u1e6dh": "\u1e6c", "\u1e0dh": "\u1e0c", "th": "T", "dh": "D",
       "ph": "P", "bh": "B"}            # an aspirate is one consonant, written as one capital
# the case forms a short name is looked for in (masculine and feminine; the neuter plural, -ani, is left out: it would
# take bhutani, "beings", for Bhuta)
ENDINGS = {
    "a": ("a", "a\u1e25", "o", "as", "a\u015b", "ar", "am", "a\u1e43", "ena", "e\u1e47a", "\u0101ya", "\u0101t",
          "\u0101d", "\u0101c", "\u0101j", "\u0101n", "asya", "e", "au", "\u0101v", "\u0101\u1e25", "\u0101",
          "ai\u1e25", "ais", "ai\u015b", "ebhya\u1e25", "\u0101n\u0101m", "\u0101\u1e47\u0101m", "e\u1e63u"),
    "\u0101": ("\u0101", "\u0101m", "\u0101\u1e43", "ay\u0101", "\u0101yai", "\u0101y\u0101\u1e25",
               "\u0101y\u0101s", "\u0101y\u0101\u015b", "\u0101y\u0101m", "\u0101y\u0101\u1e43", "e",
               "\u0101\u1e25", "\u0101s", "\u0101\u015b"),
    "i": ("i", "i\u1e25", "is", "i\u015b", "ir", "im", "i\u1e43", "in\u0101", "i\u1e47\u0101", "aye", "e\u1e25",
          "es", "e\u015b", "er", "au", "\u012b", "aya\u1e25", "\u012bn"),
    "\u012b": ("\u012b", "\u012bm", "\u012b\u1e43", "y\u0101", "yai", "y\u0101\u1e25", "y\u0101s", "y\u0101m",
               "ya\u1e25", "yau", "\u012b\u1e25"),
    "u": ("u", "u\u1e25", "us", "u\u015b", "ur", "um", "u\u1e43", "un\u0101", "u\u1e47\u0101", "ave", "o\u1e25",
          "os", "o\u015b", "or", "au", "\u016b", "ava\u1e25", "\u016bn"),
}
ENDINGS = {k: tuple(dict.fromkeys(v + tuple(e[:-1] + "\u1e43" for e in v if e.endswith("m"))))
           for k, v in ENDINGS.items()}   # -am and -am with the anusvara's sign, as the prints have both
CONS = set("kg\u1e45cj\u00f1\u1e6d\u1e0d\u1e47tdnpbmyrlv\u015b\u1e63sh")
CLASS = {"k": "\u1e45", "kh": "\u1e45", "g": "\u1e45", "gh": "\u1e45", "c": "\u00f1", "ch": "\u00f1", "j": "\u00f1", "jh": "\u00f1", "\u1e6d": "\u1e47", "\u1e6dh": "\u1e47",
         "\u1e0d": "\u1e47", "\u1e0dh": "\u1e47", "t": "n", "th": "n", "d": "n", "dh": "n", "p": "m", "ph": "m", "b": "m", "bh": "m"}
VOWELS = "a\u0101i\u012bu\u016b\u1e5b\u1e5d\u1e37eo"
NASALS = "\u1e45\u00f1\u1e47nm"
SANDHI_FINAL = set("tdcjnmsrkg\u015b\u1e63\u1e6d\u1e0dpb\u1e45")   # a word's last consonant as sandhi leaves it (not n-tilde)
CONS_START = set("kgcjtdpbmnyrlvsh\u1e6d\u1e0d\u015b\u1e63\u1e47\u00f1\u1e45")
WORD = re.compile(r"[^\s/|;,.!?()\[\]{}\"'\u2018\u2019\u201c\u201d%*+=<>_0-9-]+")


STOPS = {"k", "g", "c", "j", "\u1e6d", "\u1e0d", "t", "d", "p", "b"} | set(ASP)


def anusvara(c: str, nxt: str) -> bool:
    """Whether a nasal stands for the anusvara: always the anusvara's own signs; any nasal before a stop (sanjaya,
    samjaya; the Purana Index's Mamgu for Mangu). Not the n of punyam or puskarinyam, nor the m of bhumyam."""
    if c in ("\u1e43", "\u1e41"):
        return True
    return c in NASALS and nxt in STOPS


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").lower())


def letters(s: str) -> list:
    s, out, i = nfc(s), [], 0
    while i < len(s):
        if s[i:i + 2] in ASP:
            out.append(s[i:i + 2]); i += 2
        else:
            out.append(s[i]); i += 1
    return out


def skel(s: str) -> str:
    """The consonants of an IAST word: an anusvara, and any nasal before a consonant, left out (samjaya, sanjaya and
    the index's Samjaya are one; Karamdhama and karandhama); an aspirate is one consonant (written as one capital)."""
    t = [x for x in letters(s) if x in CONS or x in ASP or x in ("\u1e43", "\u1e41")]
    out = []
    for j, c in enumerate(t):
        if anusvara(c, t[j + 1] if j + 1 < len(t) else ""):
            continue
        out.append(ONE.get(c, c))
    return "".join(out)


LONG = {"\u0101": "a", "\u012b": "i", "\u016b": "u", "\u1e5d": "\u1e5b"}


def lkey(s: str) -> str:
    """The letters of an IAST word as they are compared: the vowels by quality (a and a-long one; e, o, ai, au and r
    apart), the anusvara and any nasal before a consonant as one sign, the visarga left out. Daksa and Rksa, Kusadhvaja
    and Kesidhvaja, stay apart, as a comparison of consonants alone would join them."""
    t = letters(s)
    out = []
    for j, c in enumerate(t):
        if c == "\u1e25":
            continue
        if anusvara(c, t[j + 1] if j + 1 < len(t) else ""):
            out.append("N")
            continue
        out.append(LONG.get(c, c))
    return "".join(out)


def old_spelling(name: str) -> str:
    """Chola -> cola, Shiva -> siva: the English spellings of the index's day, tried when the printed form is not
    found. Only for a name printed without diacritics."""
    if any(ord(c) > 127 for c in name):
        return ""
    s = re.sub(r"sh", "\u015b", name.lower())
    s = re.sub(r"ch", "c", s)
    return s if s != name.lower() else ""


def name_variants(name: str) -> list:
    """The forms of a printed name to look for: the homonym's number, a gloss after a space and a leading number
    aside; a part in brackets inside a word (Vidyu(t)jjihva, Karambha(ka)) both with and without it."""
    alt = [g for g in re.findall(r"\s[(\[]([^)\]\s]{4,})[)\]]", name or "")
           if not re.fullmatch(r"[IVXLCivxlc]+|\d+", g)]          # Ghrta (Dhrta): the other form the index gives
    n = re.sub(r"\s+[(\[][^)\]]*[)\]]", " ", " " + (name or "")).strip()
    n = re.sub(r"^\d{1,2}\.\s+", "", n)
    if alt:
        return name_variants(n) + alt
    if re.search(r"[^\s(\[][(\[][^)\]\s]{1,4}[)\]]", n):
        return [re.sub(r"[(\[]([^)\]\s]{1,4})[)\]]", r"\1", n), re.sub(r"[(\[][^)\]\s]{1,4}[)\]]", "", n)]
    return [re.sub(r"[(\[].*?[)\]]", " ", n)]


def name_key(name: str):
    """(consonants, letters, begins with a vowel, case forms) of the longest word of a name, the homonym's number and
    any gloss in brackets aside; None when the name is English or empty. A name of two consonants or fewer that ends
    in a, a-long, i, i-long or u is looked for by its case forms (Aja: ajah, ajad, ajasya ...); else by its letters."""
    n = re.sub(r"[(\[].*?[)\]]", " ", name or "")
    n = re.sub(r"^\s*\d{1,2}\.\s+", "", n).replace("-", "")
    words = [w for w in re.findall(r"[^\s,;:]+", n) if w]
    if not words:
        return None
    if all(w.lower().strip(".") in ENGLISH or (w.isascii() and w[:1].islower()) for w in words):
        return None
    w = nfc(max(words, key=len)).strip(".'")
    if not w:
        return None
    k = skel(w)
    ends_v = w[-1] in VOWELS
    if not ends_v and len(k) >= 3:          # Purudvan, Satyajit: the stem's last consonant changes with the case
        k = k[:-1]
    stem = w.rstrip(VOWELS + "\u1e25\u1e43") if ends_v else w[:-1]
    forms = frozenset()
    if len(k) < 3 and ends_v and w[-1] in ENDINGS and len(w) >= 3:
        base = w[:-1]
        ends = ENDINGS[w[-1]] + ENDINGS.get({"i": "\u012b", "\u012b": "i"}.get(w[-1], ""), ())   # Kunti, Kunteh
        forms = frozenset(base + e for e in ends)
    return (k, lkey(stem), w[:1] in VOWELS, forms)


def word_form(key, word: str, loose: bool = False) -> bool:
    """Whether a word is a form of the name. loose (a cited verse and the two either side, where the index says the
    name stands): a name of three consonants or more inside a word too, as the e-texts that print the sandhi joined
    (the Venkatesvara prints: tasmaccandrah) have it; a short name's form after a joined word's last consonant."""
    k, stem, vinit, forms = key
    w = nfc(word)
    if len(k) >= 3:
        lw = lkey(w)
        return lw.startswith(stem) or ((vinit or loose) and len(stem) >= 4 and stem in lw)
    if forms and loose:
        for f in forms:
            if len(f) < 4:
                continue
            i = w.find(f)
            while i > 0:
                if w[i - 1] in SANDHI_FINAL and (i + len(f) == len(w) or w[i + len(f)] in CONS_START):
                    return True
                i = w.find(f, i + 1)
    if forms:
        # the form, or a form ending in its sandhi consonant joined to the next word (sucis tasmat, printed sucistasmat)
        return w in forms or any(len(f) >= 4 and f[-1] in CONS_START and w.startswith(f) and
                                 w[len(f):len(f) + 1] in CONS_START for f in forms)
    if len(stem) >= 3:
        return lkey(w).startswith(stem)
    return False


def can_look(key) -> bool:
    return bool(key) and (len(key[0]) >= 3 or bool(key[3]) or len(key[1]) >= 3)


def keys_of(name: str) -> list:
    """The keys to try, the printed form first, then the form without its bracketed part, then an old spelling."""
    out = []
    for v in name_variants(name):
        for form in (v, old_spelling(v.strip())):
            if not form:
                continue
            k = name_key(form)
            if k and can_look(k) and k not in out:
                out.append(k)
    return out


AVAGRAHA = re.compile(r"(?:(?<=\s)|^)'(?=[^\s'])")


def words_of(text: str) -> list:
    """The words of a verse, an avagraha read as the a it stands for ('jakah -> ajakah)."""
    return WORD.findall(AVAGRAHA.sub("a", text or ""))


def find_in(keys: list, text: str, loose: bool = False):
    """The first word of text that is a form of the name, or None (the strict reading first, then the loose)."""
    for strict in ((True, False) if loose else (True,)):
        for key in keys:
            for w in words_of(text):
                if word_form(key, w, loose=not strict):
                    return w
    return None


# ---- the texts -----------------------------------------------------------------------------------------------
def zip_path(arg: str = "") -> Path:
    for p in ([Path(arg)] if arg else []) + [ROOT / "sources" / "gretil" / "1_sanskr.zip", ROOT / "inbox" / "1_sanskr.zip"]:
        if p.exists():
            return p
    return Path(arg) if arg else ROOT / "sources" / "gretil" / "1_sanskr.zip"


def members(z: zipfile.ZipFile) -> dict:
    want = {v[0]: k for k, v in TEXTS.items()}
    out = {}
    for n in z.namelist():
        base = n.rsplit("/", 1)[-1]
        if base in want and (PLAIN in n or not TEXTS[want[base]][1]):
            out[want[base]] = n
    return out


STAR = re.compile(r"\|\|\*.*?\*\|\|", re.S)


def read_tei(raw: str, prefix: str) -> "collections.OrderedDict":
    """{(numbers): the verse's words}: the words before each reference; a star passage or an appendix (a reference
    with * or @ and a number) is left out, half-verses (ab, cd) joined."""
    body = raw.split("# Text", 1)[-1]
    body = STAR.sub(" ", body)
    rx = re.compile(r"(?<![A-Za-z_])%s_(\d+(?:[.,]\d+)+)([a-z]{0,2})([*@]\d[\d:]*)?" % re.escape(prefix))
    out, pos = collections.OrderedDict(), 0
    for mo in rx.finditer(body):
        seg, pos = body[pos:mo.start()], mo.end()
        if mo.group(3):
            continue
        key = tuple(int(x) for x in re.split(r"[.,]", mo.group(1)) if x)
        seg = re.sub(r"(?m)^#.*$", " ", seg)
        seg = re.sub(r"[/|]+", " ", seg)
        out[key] = (out.get(key, "") + " " + " ".join(seg.split())).strip()
    return out


MBH_LINE = re.compile(r"^(\d\d),(\d\d\d)\.(\d\d\d)([a-z]*)\t(.*?)(?:<BR>|<br>)?\s*$", re.M)


def read_mbh(raw: str) -> "collections.OrderedDict":
    """{(parvan, adhyaya, verse): words}: the constituted text only (a star passage's reference has a *)."""
    out = collections.OrderedDict()
    for mo in MBH_LINE.finditer(raw):
        key = (int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))
        words = html.unescape(re.sub(r"<[^>]+>", " ", mo.group(5)))
        out[key] = (out.get(key, "") + " " + " ".join(words.split())).strip()
    return out


def load_texts(zp: Path) -> tuple:
    """({code: verses}, {code: facts}); a text not in the zip is absent from both."""
    texts, facts = {}, {}
    with zipfile.ZipFile(str(zp)) as z:
        mem = members(z)
        for code, (member, prefix, title, edition, rights, show) in TEXTS.items():
            if code not in mem:
                continue
            data = z.read(mem[code])
            raw = data.decode("utf-8", "replace")
            texts[code] = read_mbh(raw) if not prefix else read_tei(raw, prefix)
            facts[code] = {"code": code, "member": mem[code], "sha256": hashlib.sha256(data).hexdigest(),
                           "title": title, "edition": edition, "rights": rights, "show": show,
                           "verses": len(texts[code])}
    return texts, facts


def ref_text(code: str, key: tuple) -> str:
    return "%s %s" % (SHOWN.get(code, code), ".".join(str(x) for x in key))


# ---- the index's citations -------------------------------------------------------------------------------------
SEG = re.compile(r"^\s*(?:(Vi|Bh[a\u0101]|Br|M|V[a\u0101]|Ib)\s*[.,]?\s*,?\s*)(.*)$")


def verse_list(spec: str) -> list:
    """'63-5' -> [63, 64, 65]; '30, 33' -> [30, 33]; '145 & 189'; '22 and 25'; at most 8."""
    out = []
    for a, b in re.findall(r"(\d+)(?:\s*-\s*(\d+))?", spec):
        a = int(a)
        if b:
            if len(b) < len(str(a)):
                b = str(a)[:len(str(a)) - len(b)] + b
            b = int(b)
            out.extend(range(a, min(b, a + 7) + 1) if b >= a else [a])
        else:
            out.append(a)
    return out[:8]


def parse_cites(refs: list) -> list:
    """[(text code, (part, chapter) or (chapter,), [verses], the words printed)] of a relation's references; a bare
    reference ("50. 78", "IV. 29. 123") takes the text of the one before it, as the index prints them."""
    out, cur = [], None
    for r in refs or []:
        for seg in re.split(r";", str(r)):
            seg = seg.strip().rstrip(".")
            if not seg:
                continue
            mo = SEG.match(seg)
            if mo:
                t = mo.group(1)
                if t != "Ib":
                    cur = {"Vi": "vi", "Bha": "bh", "Bh\u0101": "bh", "Br": "br", "M": "m", "Va": "va", "V\u0101": "va"}[t]
                rest = mo.group(2)
            elif cur and re.match(r"^\s*([IVX]+\.|\d)", seg):
                rest = seg
            else:
                continue
            if cur is None:
                continue
            if cur in ("vi", "bh", "br"):
                m2 = re.match(r"^\s*([IVX]+)\s*[.,]\s*(\d+)\s*[.,]\s*(.+)$", rest)
                if not m2 or m2.group(1) not in ROMAN:
                    continue
                vs = verse_list(m2.group(3))
                if vs:
                    out.append((cur, (ROMAN[m2.group(1)], int(m2.group(2))), vs, seg))
            else:
                m2 = re.match(r"^\s*(\d+)\s*[.,]\s*(.+)$", rest)
                if not m2:
                    continue
                vs = verse_list(m2.group(2))
                if vs:
                    out.append((cur, (int(m2.group(1)),), vs, seg))
    return out


def gretil_keys(code: str, where: tuple, verse: int) -> list:
    """The GRETIL texts and verse keys a citation points at: [(text, key)]; [] when we hold no such text."""
    if code == "vi":
        return [(t, (where[0], where[1], verse)) for t in CITED["vi"]]
    if code == "bh":
        return [("bh", (where[0], where[1], verse))]
    if code == "br":
        part = BR_PART.get(where[0])
        return [("br", (part, where[1], verse))] if part else []
    if code == "m":
        return [("m", (where[0], verse))] if where[0] <= MATSYA_LAST else []
    return []


def window(verses: dict, key: tuple, span: int = 2) -> list:
    """[(key, words)] of the verse and the two on each side, in the same chapter."""
    out = []
    for d in range(-span, span + 1):
        k = key[:-1] + (key[-1] + d,)
        if k in verses:
            out.append((k, verses[k]))
    return out


def check_cited(row: dict, texts: dict, ks: list, ko: list) -> dict:
    """The relation's citations read in the texts we hold: the best verdict, and each citation's."""
    cites = parse_cites(row["refs"])
    if not cites:
        return {"verdict": "no citation", "cites": []}
    if not ks or not ko:
        return {"verdict": "not looked for", "cites": []}
    done, best = [], "not held"
    for code, where, vs, printed in cites:
        for v in vs:
            for tcode, key in gretil_keys(code, where, v):
                if tcode not in texts:
                    continue
                win = window(texts[tcode], key)
                if not win:
                    done.append({"text": tcode, "ref": ".".join(map(str, key)), "verdict": "no verse",
                                 "printed": printed})
                    best = min(best, "no verse", key=ORDER.index)
                    continue
                fs = [(k, find_in(ks, w, loose=True)) for k, w in win]
                fo = [(k, find_in(ko, w, loose=True)) for k, w in win]
                hs = [(k, f) for k, f in fs if f]
                ho = [(k, f) for k, f in fo if f]
                v2 = "both" if hs and ho else "one" if hs or ho else "neither"
                at = sorted({".".join(map(str, k)) for k, _f in hs + ho})
                done.append({"text": tcode, "ref": ".".join(map(str, key)), "verdict": v2, "printed": printed,
                             "subject_form": hs[0][1] if hs else "", "object_form": ho[0][1] if ho else "",
                             "at": at})
                best = min(best, v2, key=ORDER.index)
    if not done:
        return {"verdict": "not held", "cites": [{"printed": c[3]} for c in cites][:6]}
    done.sort(key=lambda d: (ORDER.index(d["verdict"]), d["text"] != "vi"))
    return {"verdict": best, "cites": done[:12]}


# ---- the epics: both names in one verse ---------------------------------------------------------------------
class WordIndex:
    """Every word of a text's verses, as compared (lkey) and as written, sorted for a search by beginnings."""

    def __init__(self, verses: dict):
        self.keys = list(verses)
        sk, wd = collections.defaultdict(set), collections.defaultdict(set)
        for i, k in enumerate(self.keys):
            for w in words_of(verses[k]):
                w = nfc(w)
                sk[lkey(w)].add(i)
                wd[w].add(i)
        self.sk, self.wd = sk, wd
        self.sk_sorted, self.wd_sorted = sorted(sk), sorted(wd)

    def _prefix(self, table: dict, sorted_keys: list, p: str) -> set:
        out = set()
        j = bisect.bisect_left(sorted_keys, p)
        while j < len(sorted_keys) and sorted_keys[j].startswith(p):
            out |= table[sorted_keys[j]]
            j += 1
        return out

    def verses_of(self, keys: list) -> set:
        out = set()
        for k, stem, _v, forms in keys:
            if len(k) >= 3 or (not forms and len(stem) >= 3):
                out |= self._prefix(self.sk, self.sk_sorted, stem)
            elif forms:
                for f in forms:
                    out |= self.wd.get(f, set())
        return out


def check_together(ks: list, ko: list, idx: dict, cache: dict, names: tuple) -> dict:
    out = {}
    if not ks or not ko:
        return out
    for code, wi in idx.items():
        a = cache.setdefault((code, names[0]), wi.verses_of(ks))
        b = cache.setdefault((code, names[1]), wi.verses_of(ko))
        both = a & b
        out[code] = (len(both), ".".join(map(str, wi.keys[min(both)])) if both else "")
    return out


# ---- the run -------------------------------------------------------------------------------------------------
def ro(path: Path, immutable: bool = False) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else ""), uri=True,
                           timeout=10)


def kin_rows(kin: Path, immutable: bool = False) -> list:
    con = ro(kin, immutable)
    try:
        rows = []
        for kid, src, eid, head, subj, rel, obj, refs in con.execute(
                "SELECT id, source, entry_id, head, subject, relation, object, refs FROM kin ORDER BY id"):
            try:
                rl = json.loads(refs or "[]")
            except ValueError:
                rl = []
            rows.append({"kin_id": kid, "source": src, "entry_id": eid, "head": head or "", "subject": subj or "",
                         "relation": rel or "", "object": obj or "", "refs": rl if isinstance(rl, list) else []})
        return rows
    finally:
        con.close()


def kin_stamp(kin: Path, immutable: bool = False) -> str:
    con = ro(kin, immutable)
    try:
        n, mx = con.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM kin").fetchone()
    finally:
        con.close()
    return "%d:%d" % (n, mx)


def zip_stamp(zp: Path) -> str:
    st = zp.stat()
    return "%d:%d" % (st.st_size, int(st.st_mtime))


def check_all(rows: list, texts: dict, log=print) -> list:
    t0 = time.time()
    idx = {c: WordIndex(texts[c]) for c in EPICS if c in texts}
    log("  the epics indexed: %s (%ds)" % (", ".join("%s %d verses" % (SHOWN[c], len(texts[c])) for c in idx),
                                            time.time() - t0))
    cache, keycache, out = {}, {}, []
    for i, r in enumerate(rows, 1):
        ks = keycache.setdefault(r["subject"], keys_of(r["subject"]))
        ko = keycache.setdefault(r["object"], keys_of(r["object"]))
        c = check_cited(r, texts, ks, ko) if r["source"] == "pui" else {"verdict": "", "cites": []}
        tg = check_together(ks, ko, idx, cache, (r["subject"], r["object"]))
        best = next((d for d in c["cites"] if d.get("verdict") == "both"), None) or \
            next((d for d in c["cites"] if d.get("verdict") == "one"), None)
        out.append({"kin_id": r["kin_id"], "source": r["source"], "entry_id": r["entry_id"], "head": r["head"],
                    "subject": r["subject"], "relation": r["relation"], "object": r["object"],
                    "printed": "; ".join(r["refs"])[:300],
                    "cited": c["verdict"], "cites": c["cites"],
                    "both_texts": sorted({d["text"] for d in c["cites"] if d.get("verdict") == "both"}),
                    "best_text": best["text"] if best else "", "best_ref": best["ref"] if best else "",
                    "subject_form": (best or {}).get("subject_form", ""), "object_form": (best or {}).get("object_form", ""),
                    "looked": bool(ks and ko),
                    "together": {k: {"verses": v[0], "first": v[1]} for k, v in tg.items()}})
        if i % 5000 == 0:
            log("  %d of %d relations (%ds)" % (i, len(rows), time.time() - t0))
    return out


def summary(res: list, facts: dict) -> dict:
    s = {"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "texts": facts, "by": {}}
    for src in SOURCES:
        rs = [r for r in res if r["source"] == src]
        d = {"relations": len(rs), "looked": sum(1 for r in rs if r["looked"])}
        if src == "pui":
            d["cited"] = dict(collections.Counter(r["cited"] for r in rs))
            d["both_by_text"] = dict(collections.Counter(t for r in rs for t in r["both_texts"]))
        for code in EPICS:
            if code in facts:
                d["together_" + code] = sum(1 for r in rs if (r["together"].get(code) or {}).get("verses"))
        d["together_any"] = sum(1 for r in rs if any((v or {}).get("verses") for v in r["together"].values()))
        s["by"][src] = d
    return s


SCHEMA = """
CREATE TABLE vamsa_meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE vamsa_texts (code TEXT PRIMARY KEY, title TEXT, edition TEXT, rights TEXT, member TEXT, sha256 TEXT,
  verses INTEGER, show INTEGER);
CREATE TABLE vamsa_rel (kin_id INTEGER PRIMARY KEY, source TEXT, entry_id INTEGER, cited TEXT, cites TEXT,
  both_texts TEXT, best_text TEXT, best_ref TEXT, subject_form TEXT, object_form TEXT, mbh INTEGER, mbh_first TEXT,
  hv INTEGER, hv_first TEXT, ram INTEGER, ram_first TEXT);
CREATE TABLE vamsa_verses (text TEXT, ref TEXT, words TEXT, PRIMARY KEY (text, ref));
CREATE INDEX vamsa_rel_source ON vamsa_rel (source, cited);
"""


def write_store(path: Path, res: list, texts: dict, facts: dict, stamps: dict) -> int:
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(str(tmp))
    try:
        con.executescript(SCHEMA)
        for k, v in dict(stamps, mark=MARK, scheme=str(SCHEME),
                         at=datetime.datetime.now().isoformat(timespec="seconds")).items():
            con.execute("INSERT INTO vamsa_meta VALUES (?, ?)", (k, str(v)))
        for f in facts.values():
            con.execute("INSERT INTO vamsa_texts VALUES (?,?,?,?,?,?,?,?)", (f["code"], f["title"], f["edition"],
                        f["rights"], f["member"], f["sha256"], f["verses"], 1 if f["show"] else 0))
        want = set()
        for r in res:
            t = r["together"]
            con.execute("INSERT INTO vamsa_rel VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                r["kin_id"], r["source"], r["entry_id"], r["cited"], json.dumps(r["cites"], ensure_ascii=False),
                ",".join(r["both_texts"]), r["best_text"], r["best_ref"], r["subject_form"], r["object_form"],
                (t.get("mbh") or {}).get("verses", 0), (t.get("mbh") or {}).get("first", ""),
                (t.get("hv") or {}).get("verses", 0), (t.get("hv") or {}).get("first", ""),
                (t.get("ram") or {}).get("verses", 0), (t.get("ram") or {}).get("first", "")))
            for d in r["cites"]:
                if d.get("verdict") in ("both", "one") and facts.get(d["text"], {}).get("show"):
                    for ref in set(d.get("at") or []) | {d["ref"]}:
                        want.add((d["text"], ref))
            for code in ("hv", "ram"):
                f = (t.get(code) or {}).get("first")
                if f and facts.get(code, {}).get("show"):
                    want.add((code, f))
        for code, ref in sorted(want):
            key = tuple(int(x) for x in ref.split("."))
            w = texts.get(code, {}).get(key)
            if w:
                con.execute("INSERT OR IGNORE INTO vamsa_verses VALUES (?,?,?)", (code, ref, w[:1200]))
        con.commit()
    finally:
        con.close()
    for i in range(5):
        try:
            os.replace(str(tmp), str(path))
            return len(want)
        except PermissionError:
            time.sleep(1.0 + i)
    raise PermissionError("%s is in use; the new store is left at %s" % (path, tmp))


def write_exports(out_dir: Path, res: list, summ: dict) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    p1, p2 = out_dir / "vamsa_checks.csv", out_dir / "vamsa_summary.json"
    with open(p1, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kin_id", "index", "entry", "subject", "relation", "object", "printed", "cited", "where",
                    "subject_form", "object_form", "mbh_verses", "mbh_first", "hv_verses", "hv_first", "ram_verses",
                    "ram_first"])
        for r in res:
            t = r["together"]
            w.writerow([r["kin_id"], SHORT.get(r["source"], r["source"]), r["head"], r["subject"], r["relation"],
                        r["object"], r["printed"], r["cited"],
                        ref_text(r["best_text"], tuple(int(x) for x in r["best_ref"].split("."))) if r["best_ref"] else "",
                        r["subject_form"], r["object_form"]] +
                       [x for code in EPICS for x in ((t.get(code) or {}).get("verses", ""), (t.get(code) or {}).get("first", ""))])
    p2.write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    return [p1, p2]


def stored_stamps(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        con = ro(path)
        try:
            return dict(con.execute("SELECT k, v FROM vamsa_meta"))
        finally:
            con.close()
    except sqlite3.Error:
        return {}


def show_name(store: Path, kin: Path, who: str) -> int:
    if not store.exists():
        print("VERDICT: no checks yet"); print("NEXT: python scripts\\vamsa_check.py --yes"); return 1
    f = nfc(who)
    rows = [r for r in kin_rows(kin) if f in (nfc(r["subject"]), nfc(r["object"])) or
            nfc(re.sub(r"\s*[(\[].*?[)\]]", "", r["subject"])).strip() == f or
            nfc(re.sub(r"\s*[(\[].*?[)\]]", "", r["object"])).strip() == f]
    con = ro(store)
    try:
        got = {r[0]: r for r in con.execute("SELECT kin_id, cited, best_text, best_ref, subject_form, object_form, mbh, "
                                            "mbh_first, hv, hv_first, ram, ram_first FROM vamsa_rel")}
    finally:
        con.close()
    # VAMSA_NAMES_2026_10_25: a statement an index makes more than once (the same subject, relation and object in one
    # source: an entry that lists it twice, or two entries of the name) is shown once, "x n", with its best check
    groups = collections.OrderedDict()
    for r in rows:
        g = got.get(r["kin_id"])
        if g:
            groups.setdefault((r["source"], nfc(r["subject"]), r["relation"], nfc(r["object"])), []).append((r, g))
    print("%s: %d relation(s) name %s, %d distinct statement(s)" % (MARK, len(rows), who, len(groups)))
    for items in list(groups.values())[:200]:
        r, g = min(items, key=lambda x: (ORDER.index(x[1][1]) if x[1][1] in ORDER else len(ORDER), -(x[1][6] or 0),
                                         x[0]["kin_id"]))
        where = ref_text(g[2], tuple(int(x) for x in g[3].split("."))) if g[3] else ""
        print("  [%s] %s %s %s%s | cited: %s%s%s | together: MBh %s%s, HV %s, Ram %s" % (
            SHORT[r["source"]], r["subject"], r["relation"], r["object"], (" x%d" % len(items)) if len(items) > 1 else "",
            g[1] or "-", (" at " + where) if where else "", (" (%s / %s)" % (g[4], g[5])) if (g[4] or g[5]) else "",
            g[6] or 0, (" first " + g[7]) if g[7] else "", g[8] or 0, g[10] or 0))
    print("VERDICT: %d relation(s) of %s shown as %d distinct statement(s)" % (len(rows), who, len(groups)))
    print("NEXT: open /vamsa on the dashboard")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--yes", action="store_true", help="write the store and the exports")
    ap.add_argument("--scheduled", action="store_true", help="write only when kin.db or the zip changed")
    ap.add_argument("--name", default="", help="show the checks of the relations that name this person")
    ap.add_argument("--zip", default="")
    ap.add_argument("--kin", default=str(ROOT / "data" / "shelf" / "kin.db"))
    ap.add_argument("--store", default=str(ROOT / "data" / "shelf" / "vamsa.db"))
    ap.add_argument("--exports", default=str(ROOT / "exports"))
    ap.add_argument("--immutable", action="store_true", help="read kin.db as a frozen copy (tests, a backup)")
    a = ap.parse_args(argv)
    kin, store = Path(a.kin), Path(a.store)
    if a.name:
        return show_name(store, kin, a.name)
    if not kin.exists():
        print("VERDICT: %s is not there: the indexes' kinships are not read yet" % kin)
        print("NEXT: python scripts\\kin_index.py"); return 1
    zp = zip_path(a.zip)
    if not zp.exists():
        print("VERDICT: GRETIL's zip is not there (%s)" % zp)
        print("NEXT: put 1_sanskr.zip in sources\\gretil (gretil_library.py reads the same file)"); return 1
    stamps = {"kin": kin_stamp(kin, a.immutable), "zip": zip_stamp(zp)}
    if a.scheduled:
        old = stored_stamps(store)
        if old.get("kin") == stamps["kin"] and old.get("zip") == stamps["zip"] and old.get("scheme") == str(SCHEME) \
                and old.get("mark") == MARK:
            print("%s: nothing new (kin.db %s, the zip unchanged); the checks of %s stand" % (MARK, stamps["kin"],
                                                                                        old.get("at", "?")))
            print("VERDICT: nothing new"); print("NEXT: "); return 0
        a.yes = True
    t0 = time.time()
    texts, facts = load_texts(zp)
    print("%s: the texts read from %s (%ds): %s" % (MARK, zp.name, time.time() - t0, "; ".join(
        "%s %d verses" % (SHOWN[c], f["verses"]) for c, f in facts.items())))
    missing = [SHOWN[c] for c in TEXTS if c not in facts]
    if missing:
        print("  not in the zip: %s" % ", ".join(missing))
    rows = kin_rows(kin, a.immutable)
    res = check_all(rows, texts)
    summ = summary(res, facts)
    for src in SOURCES:
        d = summ["by"][src]
        if not d["relations"]:
            continue
        line = "  %-13s %6d relations, %d with names to look for" % (SHORT[src], d["relations"], d["looked"])
        if src == "pui":
            c = d["cited"]
            line += "; the cited verse: both names %d, one %d, neither %d, no such verse %d, a text we lack %d " \
                    "(the Vayu; the Matsya after 176), no citation %d" % (
                        c.get("both", 0), c.get("one", 0), c.get("neither", 0), c.get("no verse", 0),
                        c.get("not held", 0), c.get("no citation", 0))
        line += "; both names in one verse of the MBh %d, the Harivamsa %d, the Ramayana %d" % (
            d.get("together_mbh", 0), d.get("together_hv", 0), d.get("together_ram", 0))
        print(line)
    p = summ["by"].get("pui", {})
    c = p.get("cited", {})
    held = sum(c.get(k, 0) for k in ("both", "one", "neither", "no verse"))
    if not a.yes:
        print("VERDICT: the plan: %d relations checked, nothing written; of the Purana Index's %d citations of a text "
              "we hold, both names stand in the verse for %d" % (len(res), held, c.get("both", 0)))
        print("NEXT: python scripts\\vamsa_check.py --yes   (free: no model; writes data\\shelf\\vamsa.db and two "
              "exports)")
        return 0
    store.parent.mkdir(parents=True, exist_ok=True)
    nv = write_store(store, res, texts, facts, stamps)
    outs = write_exports(Path(a.exports), res, summ)
    print("written: %s (%d relations, %d verses kept to show), %s" % (store, len(res), nv,
                                                                   ", ".join(str(o) for o in outs)))
    print("VERDICT: %d relations checked in %ds; of the Purana Index's %d citations of a text we hold, both names "
          "stand in the verse for %d, one for %d" % (len(res), time.time() - t0, held, c.get("both", 0),
                                                   c.get("one", 0)))
    print("NEXT: open /vamsa on the dashboard (the lines of descent, each step with its verse)")
    print("ALSO: python scripts\\vamsa_check.py --name Janamejaya")
    return 0


if __name__ == "__main__":
    sys.exit(main())
