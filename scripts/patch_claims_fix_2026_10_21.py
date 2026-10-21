#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_claims_fix_2026_10_21.py  (2026-10-21)  CLAIMS_FIX_2026_10_21

Found on the night of 21 Oct, reading data/shelf/claims.db after the run of Part I (83 pages read, 1,703 claims, 13
pages failed, 4 not read):
  - every failed page failed for one reason: the model copied the scan's own backslashes into a quotation (l\\Iahabharata,
    1\\fatsya: the OCR's M) without doubling them, and JSON allows no such escape. The replies are whole; nothing in them
    was lost. --reparse reads them again from claims.db, free.
  - a failed page's attempts were metered (usage_log) but its read recorded $0, and a page read after a failed attempt
    recorded only its last attempt: the run's own sum (which stopped it at --max-usd) was right, the report's was not.
  - 642 of the 1,072 cites named no work the reader knew: the scan's misreadings (Visht}u Puralfa, RamayaQ.a,
    Brahma1;1a), the Jatakas and suttas cited by name, the modern works (Carmichael Lectures, Corporate Life in Ancient
    India), and Ibid. A work read with no number after it had its misread letters for a place (Satapatha BrahmaQ.as:
    "ahmaQ.as"), and a place could end in a bracket it does not open ("VIII. 21)").

scripts/scholar_claims.py (needs CLAIMS_2026_10_21):
  - parse_reply(): a backslash JSON does not allow is read as a backslash (the scan's own), \\" \\\\ \\/ \\n \\r \\t and \\uXXXX
    as JSON means them;
  - read_cite() (cites-v2): the scan's misreadings cleaned (the M written 1\\f, l\\I, 1\\l; digits and brackets inside a
    word); the works the book cites, the abbreviations of its list (pp. xv-xvi) and their misreadings, read by whole words
    or, where a place follows, by a close spelling (a score of 0.82 at least, kept with the cite); a Jataka by its name;
    Ibid as the cite before it on the page; the place from the first number only, its brackets balanced; more texts of
    ours marked (the Markandeya, the Lalitavistara, the Astadhyayi, the Baudhayana, the Manu and Yajnavalkya smritis, the
    Gautama, the Natyasastra, the Bodhicaryavatara), each with what is not checked; a place the work cannot have (an
    Astadhyayi sutra is adhyaya 1-8, pada 1-4) leaves the cite not read rather than read wrongly;
  - the cost of every attempt kept on its read; the report gives the meter's sum too;
  - --reparse (free): a page whose last read failed is read again from its stored reply;
  - --recite (free): the cites of the claims read again with cites-v2 (the printed text kept; reader and score stored);
  - --show: the Purana Index (Dikshitar) first, then the Vedic Index and Soerensen, each with its credit.
tests/test_scholar_claims_2026_10_21.py: Hopkins's Great Epic of India is now read as the work it is (it had been
  asserted unread, which was all the reader of 21 Oct could say: not the Mahabharata).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_claimsfix_<date>. No database change by the patch; nothing is called.

  python scripts\\patch_claims_fix_2026_10_21.py --check
  python scripts\\patch_claims_fix_2026_10_21.py
  python scripts\\scholar_claims.py --reparse
  python scripts\\scholar_claims.py --recite
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'CLAIMS_FIX_2026_10_21'
NEEDS = {'scripts/scholar_claims.py': 'CLAIMS_2026_10_21', 'tests/test_scholar_claims_2026_10_21.py': 'CLAIMS_2026_10_21'}
FILES = list(NEEDS)
TAG = 'claimsfix'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


F = 'scripts/scholar_claims.py'

edit(F, 1, r'''def read_cite(printed: str, context: str = "") -> dict:
    """{"printed", "work", "locus", "book", "how"}: the work a cite names (as printed, or the one its sentence names)."""
    t = re.sub(r"\s+", " ", str(printed or "")).strip()
    for name, rx in CITE_RX:
        m = rx.match(t)
        if m:
            rest = t[m.end():]
            mm = LOCUS.search(rest)   # the place begins at its first number (Grihya Sutra III. 4: III. 4)
            locus = (rest[mm.start():] if mm else rest).strip(" .,;:")
            rb = ROMAN_TOKEN.match(locus)
            book = rb.group(1).lower() if rb else ""
            if name == "Mah\u0101bh\u0101rata" and re.match(r"^\W*(?:Adi|\u0100di)\b", rest):   # Mbh., Adi, 95. 85
                book, locus = "i", rest.strip(" .,;:")
            return {"printed": t, "work": name, "locus": locus, "book": book, "how": "cite"}
    best, pos = "", -1
    if not re.match(r"^[\s(]*(?:[IVXLC]+\b|\d)", t, re.I):   # a cite that names a work we do not read (Hopkins, ...)
        return {"printed": t, "work": "", "locus": t, "book": "", "how": ""}
    for name, rx in NAMED_RX:
        for m in rx.finditer(context or ""):
            if m.start() > pos:
                best, pos = name, m.start()
    if best:
        rb = ROMAN_TOKEN.match(t)
        return {"printed": t, "work": best, "locus": t, "book": rb.group(1).lower() if rb else "", "how": "sentence"}
    return {"printed": t, "work": "", "locus": t, "book": "", "how": ""}
''', r'''# CLAIMS_FIX_2026_10_21: cites-v2 ------------------------------------------------------------------------
# The cites come as the scan prints them, misread: Visht}u Puralfa, RamayaQ.a, Brahma1;1a, l\Iahabharata (the M of
# this scan is read 1\f, l\I or 1\l). A cite is cleaned of those misreadings, then read by the book's own
# abbreviations (CITE_RX), then by whole words against the works the book cites (ALIASES), and, where a place follows,
# by a close spelling (difflib, 0.82 at least, the score kept); a Jataka by its name; Ibid as the cite before it.
CITE_READER = "cites-v2"
OCR_M = re.compile(r"[1lI]\\[fliI]")
OCR_JUNK = re.compile(r"(?<=[A-Za-z])(?=[^A-Za-z\s]{0,3}[\d;!}{~|)(])[^A-Za-z\s]{1,4}(?=[A-Za-z])")
CLOSE = 0.82
ALIASES = {
    "Mah\u0101bh\u0101rata": ["mahabharata", "mbh", "mbb", "mahabh", "mahabharat"],
    "Harivam\u015ba": ["harivamsa", "hariv", "harivansa"],
    "R\u0101m\u0101ya\u1e47a": ["ramayana", "ram"],
    "Vi\u1e63\u1e47u Pur\u0101\u1e47a": ["vishnu purana", "vishnu", "visnu purana", "vishnu p", "vi p"],
    "V\u0101yu Pur\u0101\u1e47a": ["vayu purana", "vayu", "vayu p"],
    "Matsya Pur\u0101\u1e47a": ["matsya purana", "matsya", "mat", "matsya p"],
    "Bh\u0101gavata Pur\u0101\u1e47a": ["bhagavata purana", "bhagavata", "bhag p", "bhag"],
    "Brahm\u0101\u1e47\u1e0da Pur\u0101\u1e47a": ["brahmanda purana", "brahmanda"],
    "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a": ["markandeya purana", "markandeya"],
    "Pur\u0101\u1e47as": ["puranas"],
    "\u015aatapatha Br\u0101hma\u1e47a": ["satapatha brahmana", "satapatha", "sat br"],
    "Aitareya Br\u0101hma\u1e47a": ["aitareya brahmana", "ait br", "aitareya br"],
    "Aitareya \u0100ra\u1e47yaka": ["aitareya aranyaka", "ait ar"],
    "Taittir\u012bya Br\u0101hma\u1e47a": ["taittiriya brahmana", "taitt br", "tait br"],
    "Taittir\u012bya Sa\u1e43hit\u0101": ["taittiriya samhita", "taitt s", "tait s"],
    "Taittir\u012bya \u0100ra\u1e47yaka": ["taittiriya aranyaka", "taitt ar", "tait ar"],
    "Gopatha Br\u0101hma\u1e47a": ["gopatha brahmana", "gop br"],
    "Pa\u00f1cavi\u1e43\u015ba Br\u0101hma\u1e47a": ["panchavimsa brahmana", "pancavimsa brahmana", "panchavimsa", "pancavimsa",
                                                  "tandya brahmana", "tandya"],
    "Jaimin\u012bya Upani\u1e63ad Br\u0101hma\u1e47a": ["jaiminiya upanishad brahmana", "jaim up br"],
    "Jaimin\u012bya Br\u0101hma\u1e47a": ["jaiminiya brahmana"],
    "Kau\u1e63\u012btaki Br\u0101hma\u1e47a": ["kaushitaki brahmana", "kaush br"],
    "Kau\u1e63\u012btaki Upani\u1e63ad": ["kaushitaki upanishad", "kaush up"],
    "B\u1e5bhad\u0101ra\u1e47yaka Upani\u1e63ad": ["brihadaranyaka upanishad", "brihadaranyaka", "brih up", "brihad up", "brihad"],
    "Ch\u0101ndogya Upani\u1e63ad": ["chhandogya upanishad", "chandogya upanishad", "chhandogya", "chh up"],
    "\u1e5agveda": ["rig veda", "rigveda", "rv"],
    "Atharvaveda": ["atharva veda", "atharvaveda", "av"],
    "V\u0101jasaneyi Sa\u1e43hit\u0101": ["vajasaneyi samhita", "vaj s"],
    "K\u0101\u1e6dhaka Sa\u1e43hit\u0101": ["kathaka samhita"],
    "Nirukta": ["nirukta"],
    "\u015a\u0101\u1e45kh\u0101yana \u015arauta S\u016btra": ["sankhayana srauta sutra", "sankh sr"],
    "\u0100\u015bval\u0101yana G\u1e5bhya S\u016btra": ["asvalayana grihya sutra"],
    "\u0100\u015bval\u0101yana \u015arauta S\u016btra": ["asvalayana srauta sutra"],
    "K\u0101ty\u0101yana \u015arauta S\u016btra": ["katyayana srauta sutra"],
    "Baudh\u0101yana Dharma S\u016btra": ["baudhayana dharma sutra", "bau sutra"],
    "Manusm\u1e5bti": ["manusmriti", "manu smriti", "manu samhita"],
    "Y\u0101j\u00f1avalkya Sm\u1e5bti": ["yajnavalkya smriti"],
    "Gautama Dharmas\u016btra": ["gautama dharma sutra", "gautama dharmasutra"],
    "N\u0101\u1e6dya\u015b\u0101stra": ["natya sastra", "natyasastra"],
    "A\u1e63\u1e6d\u0101dhy\u0101y\u012b": ["ashtadhyayi", "panini"],
    "Artha\u015b\u0101stra": ["arthasastra", "kautilya", "kaut"],
    "A\u1e45guttara Nik\u0101ya": ["anguttara nikaya", "anguttara"],
    "D\u012bgha Nik\u0101ya": ["digha nikaya", "digha"],
    "Majjhima Nik\u0101ya": ["majjhima nikaya", "majjhima"],
    "Sa\u1e43yutta Nik\u0101ya": ["samyutta nikaya", "samyutta"],
    "Suttanip\u0101ta": ["sutta nipata"],
    "Mah\u0101vagga": ["mahavagga"],
    "Cullavagga": ["cullavagga", "chullavagga"],
    "Mah\u0101va\u1e43sa": ["mahavamsa"],
    "D\u012bpava\u1e43sa": ["dipavamsa"],
    "Divy\u0101vad\u0101na": ["divyavadana"],
    "Lalitavistara": ["lalitavistara", "lalita vistara"],
    "Bodhicary\u0101vat\u0101ra": ["bodhicaryavatara"],
    "Paramatthajotik\u0101": ["paramatthajotika"],
    "Uttar\u0101dhyayana S\u016btra": ["uttaradhyayana"],
    "Niray\u0101val\u012b S\u016btra": ["nirayavali"],
    "Vedic Index": ["vedic index", "ved ind"],
    "D. R. Bhandarkar, Carmichael Lectures, 1918": ["carmichael lectures", "carmichael lec", "carm lec"],
    "R. C. Majumdar, Corporate Life in Ancient India": ["corporate life in ancient india", "corporate life"],
    "R. G. Bhandarkar, Early History of the Dekkan": ["early history of the dekkan"],
    "H. C. Raychaudhuri, Early History of the Vaishnava Sect": ["early history of the vaishnava sect"],
    "T. W. Rhys Davids, Buddhist India": ["buddhist india", "bud ind"],
    "T. W. Rhys Davids, Dialogues of the Buddha": ["dialogues of the buddha"],
    "V. A. Smith, Early History of India, 1914": ["early history of india"],
    "F. E. Pargiter, Ancient Indian Historical Tradition": ["ancient indian historical tradition"],
    "F. E. Pargiter, The Purana Text of the Dynasties of the Kali Age": ["dynasties of the kali age"],
    "E. W. Hopkins, The Great Epic of India": ["great epic of india"],
    "E. W. Hopkins, The Religions of India": ["religions of india"],
    "A. Cunningham, Ancient Geography of India": ["ancient geography of india"],
    "The Cambridge History of India": ["cambridge history of india"],
    "Sacred Books of the East": ["sacred books of the east", "sbe"],
    "Journal of the Royal Asiatic Society": ["jras"],
    "Journal of the Asiatic Society of Bengal": ["jasb"],
    "Journal of the Bihar and Orissa Research Society": ["jbors"],
    "Indian Antiquary": ["indian antiquary", "ind ant"],
    "Epigraphia Indica": ["epigraphia indica", "ep ind"],
}
ALIAS_LIST = sorted(((w, a) for w, al in ALIASES.items() for a in al), key=lambda x: (-len(x[1].split()), -len(x[1])))
IBID = ("ibid", "ib", "ibd", "ibjd", "lbid", "lbij", "ibi")
OURS_MORE = {
    "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a": ("markandeya_purana__w_gretil", "ours is GRETIL's e-text (adhyaya.verse); a cite of a "
                                                         "translation's page is not a place in it"),
    "Lalitavistara": ("LalitaVistara", "whether ours holds this place is not checked"),
    "A\u1e63\u1e6d\u0101dhy\u0101y\u012b": ("Astadhyayi", "ours is an OCR reading of a scan: whether it holds this place is not checked"),
    "Baudh\u0101yana Dharma S\u016btra": ("bodhyana", "whether ours holds this place is not checked"),
    "Manusm\u1e5bti": ("smriti_14manu_smriti_seg", "whether ours holds this place is not checked"),
    "Y\u0101j\u00f1avalkya Sm\u1e5bti": ("smriti_06yagyavalkya_smriti", "whether ours holds this place is not checked"),
    "Gautama Dharmas\u016btra": ("smriti_17gautama_smriti", "whether ours holds this place is not checked"),
    "N\u0101\u1e6dya\u015b\u0101stra": ("2015_368408_Natyasastra-With", "ours is an OCR reading of a scan: whether it holds this place is "
                                                    "not checked"),
    "Bodhicary\u0101vat\u0101ra": ("Bodhicaryavatara", "whether ours holds this place is not checked"),
}


def ocr_clean(t: str) -> str:
    """A cite without the scan's misreadings: its M (1\\f, l\\I, 1\\l), a middle dot, digits and brackets inside a word."""
    t = OCR_M.sub("M", str(t or "")).replace("\u00b7", " ")
    t = re.sub(r"(?<=\s):(?=[A-Za-z])", "", t).lstrip(" :;.,'\"`")
    t = OCR_JUNK.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def fold_tokens(s: str) -> list:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("rri", "m")
    return re.findall(r"[a-z]+", s)


def tidy_locus(s: str) -> str:
    """A place with its brackets balanced (VIII. 21): VIII. 21; 99. 12-23}: 99. 12-23)."""
    s = (s or "").strip(" .,;:")
    for o, c in (("(", ")"), ("[", "]"), ("{", "}")):
        while s.endswith(c) and s.count(o) < s.count(c):
            s = s[:-1].rstrip(" .,;:")
        while s.startswith(o) and s.count(o) > s.count(c):
            s = s[1:].lstrip(" .,;:")
    return s


OCR_N = (("jf", "n"), ("lf", "n"), ("qq", "nd"), ("q", "n"))   # the scan's n with a dot: VishJfU, Puralfa, RamayaQa
PLACE_WORDS = {"chapter", "ch", "adhyaya", "verse", "verses", "sloka", "slokas", "no", "sec", "section"}   # not "p.": a page is a book's


def match_alias(tokens: list, placed: bool):
    """(work, score, how) by whole words, else (with a place after it) by a close spelling (and again with the scan's
    misread n read as n), else a Jataka; or None."""
    hit = _match_alias(tokens, placed)
    if hit is None and placed:
        alt = []
        for tok in tokens:
            for x, y in OCR_N:
                tok = tok.replace(x, y)
            alt.append(tok)
        if alt != tokens:
            hit = _match_alias(alt, placed)
            if hit is not None and hit[2] == "cite":
                hit = (hit[0], hit[1], "ocr")
    return hit


def _match_alias(tokens: list, placed: bool):
    for work, alias in ALIAS_LIST:
        at = alias.split()
        for i in range(len(tokens) - len(at) + 1):
            if tokens[i:i + len(at)] == at:
                return work, 1.0, "cite"
    jat = None   # a Jataka by its name (Dasa-Brahmana Jataka is a Jataka, not the Brahmanda Purana)
    for w in (1, 2):
        for i in range(len(tokens) - w + 1):
            tok = "".join(tokens[i:i + w])
            r = 1.0 if tok in ("jataka", "jatakas") else difflib.SequenceMatcher(None, tok, "jataka").ratio()
            if r >= 0.8 and (jat is None or r > jat[1]):
                jat = ("J\u0101taka", round(r, 3), "cite" if r == 1.0 else "ocr")
    if jat:
        return jat
    best = None
    if placed:
        for work, alias in ALIAS_LIST:
            aj = alias.replace(" ", "")
            if len(aj) < 6:
                continue
            n = len(alias.split())
            for w in sorted({n, n + 1, max(1, n - 1)}):
                for i in range(len(tokens) - w + 1):
                    r = difflib.SequenceMatcher(None, "".join(tokens[i:i + w]), aj).ratio()
                    if r >= CLOSE and (best is None or r > best[1]):
                        best = (work, round(r, 3), "ocr")
    return best


PANINI = re.compile(r"^\s*(?:[IV]{1,4}|VIII|[1-8])\s*[.,]\s*[1-4]\s*[.,]\s*\d{1,3}\b")   # adhyaya (1-8). pada (1-4). sutra


def fits(work: str, locus: str) -> bool:
    """A place the work can have: the Astadhyayi's is adhyaya.pada.sutra (VI. 2. 101, not II. 68. 13)."""
    if work == "A\u1e63\u1e6d\u0101dhy\u0101y\u012b" and locus and re.match(r"^\s*[\dIVXivx]", locus):
        return bool(PANINI.match(locus.upper()))
    return True


def _cite(t, work, locus, how, score=None, rest=""):
    locus = tidy_locus(locus)
    if not fits(work, locus):   # a place the work cannot have: not read, rather than read wrongly
        return {"printed": t, "work": "", "locus": locus, "book": "", "how": "", "score": None}
    rb = ROMAN_TOKEN.match(locus)
    book = rb.group(1).lower() if rb else ""
    if work == "Mah\u0101bh\u0101rata" and re.match(r"^\W*(?:Adi|\u0100di)\b", rest):   # Mbh., Adi, 95. 85
        book, locus = "i", tidy_locus(rest)
    return {"printed": t, "work": work, "locus": locus, "book": book, "how": how, "score": score}


def read_cite(printed: str, context: str = "", prev: str = "") -> dict:
    """{"printed", "work", "locus", "book", "how", "score"}: the work a cite names, and its place (cites-v2,
    CLAIMS_FIX_2026_10_21). how: cite (the book's abbreviation, or the work's words), ocr (a close spelling: score),
    ibid (the cite before it: prev), sentence (a bare place: the work its sentence names), after (a bare place whose
    sentence names no work: the work of the cite before it on the page), or "" (not read)."""
    t = re.sub(r"\s+", " ", str(printed or "")).strip()
    c = ocr_clean(t)
    mm = LOCUS.search(c)
    head = c[:mm.start()] if mm else c
    toks = fold_tokens(head)
    if toks and len(toks) <= 2 and (toks[0] in IBID or (len(toks[0]) in (3, 4, 5) and
                                                        difflib.SequenceMatcher(None, toks[0], "ibid").ratio() >= 0.75)):
        return _cite(t, prev, c[mm.start():] if mm else "", "ibid" if prev else "", None) if prev else \
            {"printed": t, "work": "", "locus": tidy_locus(c), "book": "", "how": "", "score": None}
    for name, rx in CITE_RX:
        m = rx.match(c)
        if m:
            rest = c[m.end():]
            m2 = LOCUS.search(rest)   # the place begins at its first number (Grihya Sutra III. 4: III. 4)
            return _cite(t, name, rest[m2.start():] if m2 else "", "cite", 1.0, rest)
    hit = match_alias(toks, bool(mm))
    if hit:
        return _cite(t, hit[0], c[mm.start():] if mm else "", hit[2], hit[1], c[len(head):])
    best, pos = "", -1
    bare = bool(mm) and bool(toks) and set(toks) <= PLACE_WORDS   # Chapter 95, p. 12: a place without its work
    if not bare and not re.match(r"^[\s(]*(?:[IVXLC]+\b|\d)", c, re.I):   # a work we do not read (Pargiter, ...)
        return {"printed": t, "work": "", "locus": tidy_locus(c), "book": "", "how": "", "score": None}
    for name, rx in NAMED_RX:
        for m in rx.finditer(context or ""):
            if m.start() > pos:
                best, pos = name, m.start()
    if best:
        return _cite(t, best, c, "sentence", None)
    if prev:   # a bare place after a cite on the same page: that cite's work (how "after", so it can be told apart)
        return _cite(t, prev, c, "after", None)
    return {"printed": t, "work": "", "locus": tidy_locus(c), "book": "", "how": "", "score": None}
''')

edit(F, 2, r'''    if work == "Mah\u0101bh\u0101rata":
        return (("MBh01", "ours is the critical edition's book 1 (Poona, 1933): numbered otherwise than the editions "
                          "of 1923") if book == "i" else ("", ""))
''', r'''    if work == "Mah\u0101bh\u0101rata":
        return (("MBh01", "ours is the critical edition's book 1 (Poona, 1933): numbered otherwise than the editions "
                          "of 1923") if book == "i" else ("", ""))
    if work in OURS_MORE:   # CLAIMS_FIX_2026_10_21
        return OURS_MORE[work]
''')

edit(F, 3, r'''    con.executescript(SCHEMA)
    return con
''', r'''    con.executescript(SCHEMA)
    for t, col, ty in (("claim_cites", "reader", "TEXT"), ("claim_cites", "score", "REAL"),
                       ("claim_reads", "note", "TEXT")):   # CLAIMS_FIX_2026_10_21
        if col not in {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}:
            con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (t, col, ty))
    con.commit()
    return con
''')

edit(F, 4, r'''def parse_reply(text: str):
    t = (text or "").strip()
    try:
        d = json.loads(t)
    except ValueError:
        a_, b_ = t.find("{"), t.rfind("}")
        if a_ < 0 or b_ <= a_:
            return None
        try:
            d = json.loads(t[a_:b_ + 1])
        except ValueError:
            return None
''', r'''BAD_ESCAPE = re.compile(r'\\(u[0-9a-fA-F]{4}|["\\/nrt]|.|$)', re.S)


def json_repair(t: str) -> str:
    """CLAIMS_FIX_2026_10_21: a backslash JSON does not allow (the scan's own, copied into a quotation: l\\Iahabharata)
    doubled, so it is read as a backslash; \\" \\\\ \\/ \\n \\r \\t and \\uXXXX as JSON means them."""
    return BAD_ESCAPE.sub(lambda m: m.group(0) if (m.group(1) and (len(m.group(1)) == 5 or m.group(1) in '"\\/nrt'))
                          else "\\\\" + m.group(1), t)


def parse_reply(text: str):
    t = (text or "").strip()
    d = None
    for s in (t, json_repair(t)):   # CLAIMS_FIX_2026_10_21: then with the scan's backslashes read as backslashes
        a_, b_ = s.find("{"), s.rfind("}")
        for x in (s, s[a_:b_ + 1] if 0 <= a_ < b_ else None):
            if x is None:
                continue
            try:
                d = json.loads(x, strict=False)
                break
            except ValueError:
                continue
        if d is not None:
            break
    if d is None:
        return None
''')

edit(F, 5, r'''def save_read(con, code: str, work: dict, pg: tuple, engine: str, status: str, claims: list, cost: float, usage,
              raw: str, error: str = "") -> int:
''', r'''def save_read(con, code: str, work: dict, pg: tuple, engine: str, status: str, claims: list, cost: float, usage,
              raw: str, error: str = "", note: str = "") -> int:
''')

edit(F, 6, r'''        cur = con.execute("INSERT INTO claim_reads(work, pdf_page, page_sha256, prompt_version, engine, status, claims, "
                          "cost_usd, in_tokens, out_tokens, raw, error, at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (code, n_page, sha, PROMPT_VERSION, engine, status, len(claims), cost, pin, pout,
                           (raw or "")[:200000], error[:2000] if error else None, at))
        rid = cur.lastrowid
''', r'''        cur = con.execute("INSERT INTO claim_reads(work, pdf_page, page_sha256, prompt_version, engine, status, claims, "
                          "cost_usd, in_tokens, out_tokens, raw, error, at, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (code, n_page, sha, PROMPT_VERSION, engine, status, len(claims), cost, pin, pout,
                           (raw or "")[:200000], error[:2000] if error else None, at, note or None))
        rid = cur.lastrowid
        prev = ""   # CLAIMS_FIX_2026_10_21: the cite before, for an Ibid
''')

edit(F, 7, r'''            for j, p in enumerate(c["cites"], 1):
                r = read_cite(p, ctx)
                ours, note = ours_of(r["work"], r["book"]) if r["work"] else ("", "")
                con.execute("INSERT INTO claim_cites(claim_id, n, printed, work, locus, book, how, ours, note, vei_page) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)", (cid, j, r["printed"], r["work"] or None, r["locus"],
                                                            r["book"] or None, r["how"] or None, ours or None,
                                                            note or None, vei_page(r) or None))
''', r'''            for j, p in enumerate(c["cites"], 1):
                r = read_cite(p, ctx, prev)
                prev = r["work"] or prev
                ours, onote = ours_of(r["work"], r["book"]) if r["work"] else ("", "")
                con.execute("INSERT INTO claim_cites(claim_id, n, printed, work, locus, book, how, ours, note, vei_page, "
                            "reader, score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (cid, j, r["printed"], r["work"] or None, r["locus"], r["book"] or None, r["how"] or None,
                             ours or None, onote or None, vei_page(r) or None, CITE_READER, r.get("score")))
''')

edit(F, 8, r'''        prompt = page_prompt(work, pg[1], pg[2])
        reply, resp, err = "", None, ""
        for attempt in range(4):
''', r'''        prompt = page_prompt(work, pg[1], pg[2])
        reply, resp, err = "", None, ""
        spent = 0.0   # CLAIMS_FIX_2026_10_21: every attempt's cost, on the page's read
        for attempt in range(4):
''')

edit(F, 9, r'''            got["cost"] += cost
            claims = parse_reply(reply) if not err else None
            if claims is not None:
                kept = [x for x in (clean_claim(c) for c in claims) if x]
                save_read(con, code, work, pg, engine, "ok", kept, cost, getattr(resp, "usage_metadata", None), reply)
''', r'''            got["cost"] += cost
            spent += cost
            claims = parse_reply(reply) if not err else None
            if claims is not None:
                kept = [x for x in (clean_claim(c) for c in claims) if x]
                save_read(con, code, work, pg, engine, "ok", kept, spent, getattr(resp, "usage_metadata", None), reply,
                          note=("after %d attempt(s)" % (attempt + 1)) if attempt else "")
''')

edit(F, 10, r'''            save_read(con, code, work, pg, engine, "failed", [], 0.0, getattr(resp, "usage_metadata", None), reply,
                      err or "the reply is not the JSON asked for")
''', r'''            save_read(con, code, work, pg, engine, "failed", [], spent, getattr(resp, "usage_metadata", None), reply,
                      err or "the reply is not the JSON asked for")
''')

edit(F, 11, r'''    shelf, ours = shelf_and_ours(a.db, a.immutable, k)
    if shelf:
        print("  the indexes (scholar_shelf.py --show %s for all they say):" % a.show)
        for src, lnum, page, name, hom, body in shelf[:a.limit]:
''', r'''    shelf, ours = shelf_and_ours(a.db, a.immutable, k)
    shelf.sort(key=lambda e: (SHELF_ORDER.get(e[0], 9), e[1]))   # CLAIMS_FIX_2026_10_21: Dikshitar first
    if shelf:
        print("  the indexes (scholar_shelf.py --show %s for all they say):" % a.show)
        for src in sorted({e[0] for e in shelf}, key=lambda s: SHELF_ORDER.get(s, 9)):
            print("    %s: %s" % (src.upper(), SHELF_CREDIT.get(src, src)))
        for src, lnum, page, name, hom, body in shelf[:a.limit]:
''')

edit(F, 12, r'''def show_name(a, con, code: str, work: dict) -> int:
''', r'''SHELF_ORDER = {"pui": 0, "vei": 1, "inm": 2}   # CLAIMS_FIX_2026_10_21
SHELF_CREDIT = {"pui": "V. R. Ramachandra Dikshitar, The Purana Index (Madras, 1951-55)",
                "vei": "A. A. Macdonell and A. B. Keith, Vedic Index of Names and Subjects (London, 1912)",
                "inm": "S. Soerensen, An Index to the Names in the Mahabharata (1904; the Calcutta edition)"}


def meter_line(db: str, immutable: bool, code: str) -> str:
    """CLAIMS_FIX_2026_10_21: what the meter recorded for this work's calls (every attempt), from usage_log."""
    try:
        c2 = connect_ro(db, immutable)
        try:
            n, s = c2.execute("SELECT COUNT(*), SUM(cost_usd) FROM usage_log WHERE kind = 'claims' AND doc = ?",
                              (code,)).fetchone()
        finally:
            c2.close()
        return "  the meter (usage_log, every call): %d call(s), $%.4f" % (n or 0, s or 0.0)
    except sqlite3.Error:
        return "  the meter: not read"


def reparse(a, con, code: str, work: dict) -> int:
    """CLAIMS_FIX_2026_10_21: a page whose last read failed, read again from its stored reply (free)."""
    rows = con.execute(
        "SELECT r.id, r.pdf_page, r.page_sha256, r.engine, r.raw, p.printed, p.text, p.sha256 FROM claim_reads r JOIN "
        "claim_pages p ON p.work = r.work AND p.pdf_page = r.pdf_page WHERE r.work = ? AND r.status = 'failed' AND r.id IN "
        "(SELECT MAX(id) FROM claim_reads WHERE work = ? GROUP BY pdf_page) ORDER BY r.pdf_page", (code, code)).fetchall()
    print("scholar_claims %s: %s; %d page(s) whose last read failed" % (MARK, work["short"], len(rows)))
    done, left = 0, []
    for rid, n_pdf, sha_r, engine, raw, printed, text, sha_p in rows:
        claims = parse_reply(raw) if raw else None
        if claims is None or sha_r != sha_p:
            left.append("p. %s (pdf %d)" % (printed or "-", n_pdf))
            continue
        kept = [x for x in (clean_claim(c) for c in claims) if x]
        save_read(con, code, work, (n_pdf, printed, text, sha_p), engine, "ok", kept, 0.0, None, raw,
                  note="reparsed from read %d (CLAIMS_FIX_2026_10_21): its cost is on the failed read and in the meter" % rid)
        done += 1
        print("  page %s (pdf %d): %d claim(s), from the reply stored" % (printed or "-", n_pdf, len(kept)))
    say("%d page(s) read again from their stored replies, free; %d left (%s)" % (done, len(left), ", ".join(left) or "none"),
        "python scripts\\scholar_claims.py --recite" if done else "")
    return 0


def recite(a, con, code: str, work: dict) -> int:
    """CLAIMS_FIX_2026_10_21: the cites of the claims read again with cites-v2 (free; the printed text kept)."""
    reads = [r[0] for r in con.execute(CURRENT, (code,))]
    before = dict(con.execute("SELECT COALESCE(x.how, ''), COUNT(*) FROM claim_cites x JOIN claims c ON c.id = x.claim_id "
                              "WHERE c.work = ? AND c.read_id IN (%s) GROUP BY 1" % CURRENT, (code, code)).fetchall())
    n = 0
    with con:
        for rid in reads:
            prev = ""
            for cid, claim, quote in con.execute("SELECT id, claim, quote FROM claims WHERE read_id = ? ORDER BY n", (rid,)).fetchall():
                for rowid, printed in con.execute("SELECT rowid, printed FROM claim_cites WHERE claim_id = ? ORDER BY n",
                                                  (cid,)).fetchall():
                    r = read_cite(printed, (claim or "") + " " + (quote or ""), prev)
                    prev = r["work"] or prev
                    ours, onote = ours_of(r["work"], r["book"]) if r["work"] else ("", "")
                    con.execute("UPDATE claim_cites SET work = ?, locus = ?, book = ?, how = ?, ours = ?, note = ?, vei_page = ?, "
                                "reader = ?, score = ? WHERE rowid = ?",
                                (r["work"] or None, r["locus"], r["book"] or None, r["how"] or None, ours or None,
                                 onote or None, vei_page(r) or None, CITE_READER, r.get("score"), rowid))
                    n += 1
    after = dict(con.execute("SELECT COALESCE(x.how, ''), COUNT(*) FROM claim_cites x JOIN claims c ON c.id = x.claim_id "
                             "WHERE c.work = ? AND c.read_id IN (%s) GROUP BY 1" % CURRENT, (code, code)).fetchall())
    mine = con.execute("SELECT COUNT(*) FROM claim_cites x JOIN claims c ON c.id = x.claim_id WHERE c.work = ? AND "
                       "c.read_id IN (%s) AND x.ours IS NOT NULL" % CURRENT, (code, code)).fetchone()[0]
    fmt = lambda d: ", ".join("%s %d" % (k or "not read", v) for k, v in sorted(d.items(), key=lambda x: -x[1]))
    print("scholar_claims %s: %s; %d cite(s) read again (%s)" % (MARK, work["short"], n, CITE_READER))
    print("  before: " + (fmt(before) or "none"))
    print("  now:    " + (fmt(after) or "none"))
    say("%d cite(s) of %s read again; %d not read (as printed); %d in a text we hold"
        % (n, work["short"], after.get("", 0), mine), "python scripts\\scholar_claims.py --report")
    return 0


def show_name(a, con, code: str, work: dict) -> int:
''')

edit(F, 13, r'''    for st, n, c in reads:
        print("  reads %s: %d ($%.4f)" % (st, n, c or 0.0))
''', r'''    for st, n, c in reads:
        print("  reads %s: %d ($%.4f)" % (st, n, c or 0.0))
    print(meter_line(a.db, a.immutable, code))   # CLAIMS_FIX_2026_10_21: before the fix a failed read recorded $0
''')

edit(F, 14, r'''    ap.add_argument("--csv", default="")
''', r'''    ap.add_argument("--csv", default="")
    ap.add_argument("--reparse", action="store_true", help="free: a failed page read again from its stored reply")
    ap.add_argument("--recite", action="store_true", help="free: the cites read again (cites-v2)")
''')

edit(F, 15, r'''        if a.csv:
            return to_csv(a, con, code)
''', r'''        if a.csv:
            return to_csv(a, con, code)
        if a.reparse:   # CLAIMS_FIX_2026_10_21
            return reparse(a, con, code, work)
        if a.recite:
            return recite(a, con, code, work)
''')

edit(F, 16, r'''CREATE TABLE IF NOT EXISTS claim_cites(claim_id INTEGER NOT NULL, n INTEGER, printed TEXT, work TEXT, locus TEXT,
  book TEXT, how TEXT, ours TEXT, note TEXT, vei_page TEXT);
''', r'''CREATE TABLE IF NOT EXISTS claim_cites(claim_id INTEGER NOT NULL, n INTEGER, printed TEXT, work TEXT, locus TEXT,
  book TEXT, how TEXT, ours TEXT, note TEXT, vei_page TEXT, reader TEXT, score REAL);
''')

edit(F, 17, r'''  out_tokens INTEGER, raw TEXT, error TEXT, at TEXT);
''', r'''  out_tokens INTEGER, raw TEXT, error TEXT, at TEXT, note TEXT);
''')


edit('tests/test_scholar_claims_2026_10_21.py', 1, r"""        self.assertEqual(C.read_cite("Hopkins, The Great Epic of India, p. 385", "the Mahabharata says")["work"], "",
                         "a modern work, not the text the sentence names")
""", r"""        self.assertEqual(C.read_cite("Hopkins, The Great Epic of India, p. 385", "the Mahabharata says")["work"],
                         "E. W. Hopkins, The Great Epic of India",
                         "a modern work, not the text the sentence names (CLAIMS_FIX_2026_10_21: read as the work it is)")
""")


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
            if err:
                problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("DONE: %s; backups .bak_%s_%s" % (MARK, TAG, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
