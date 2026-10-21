#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
scholar_claims.py  (2026-10-21)  CLAIMS_2026_10_21

The scholars' shelf, step 2: a scholar's book read into claims, page by page, each with its printed page, a short
quotation checked against the page's own text, and the sources the scholar cites for it, read into the works they
name and whether our corpus holds that place. Step 1 (scholar_shelf.py) holds the indexes of names (the Vedic Index,
Soerensen's Mahabharata index, the Purana Index); --show puts a name's claims beside them and beside our own texts,
so that what we add can be checked against the scholars, and what they say against the texts they cite.

The first work: H. C. Raychaudhuri, Political History of Ancient India, from the Accession of Parikshit to the
Extinction of the Gupta Dynasty (University of Calcutta, 1923; first edition), from the scan in the Dhananjayarao
Gadgil Library, Gokhale Institute of Politics and Economics, Pune (GIPE-004595, handle 10973/29602; 372 pdf pages;
md5 75e8d7bd429f9396997cc9e1c2e9f4bd). Published 1923, its author died in 1957: in the public domain in India (60
years after the author's death) and in the United States (published before 1929). The page numbers: pdf pages
14-18 are Part I's Foreword (i-v), pdf page 19 is page 1 and so on (pdf - 18); Part I (From the Accession of
Parikshit to the Coronation of Bimbisara) is pdf 14-112 (pp. i-v, 1-94).

Each page's text is the scan's own text layer (Adobe Paper Capture, 2014: it misreads, Brahma1;1a for Brahmana),
read with pypdf (free). A page is read by gemini-2.5-flash (Google's cap, metered as kind "claims"; the cap is asked
before each page; its thinking capped by --think), which gives JSON: the subject and object in standard IAST and as
printed, a relation from a fixed list, the claim (at most 35 words, nothing added), a quotation of 8-30 words, the
cites as printed, the stance (asserts, reports, rejects, doubts), the hedge, and the scholar whose view is reported.
The quotation is checked mechanically against the page's text: exact (the same words, diacritics and case aside),
close (the OCR's misreadings: similarity at least 0.85), or none (not on the page: a person checks it). Nothing is
taken on the model's word: every claim keeps its page, its quotation and its check.

Local only: data/shelf/claims.db (data/shelf/ is not committed; corpus_sync.py does not know it). The database
data/context.db is only read (the shelf, our entities) and gets the meter's row of each call (usage_log), as every
paid call does. A page read again (--redo, or a new prompt) gets a new read; the latest read is the page's claims.

  python scripts\\scholar_claims.py                                  (the plan: what is read, what it would cost)
  python scripts\\scholar_claims.py --extract                        (free: the pages' text into claims.db)
  python scripts\\scholar_claims.py --pages 1-3 --yes                (a trial: printed pages 1-3, pdf 19-21)
  python scripts\\scholar_claims.py --part 1 --yes                   (Part I; resumes: a page read is not read again)
  python scripts\\scholar_claims.py --show Janamejaya                (a name's claims, the indexes, our texts)
  python scripts\\scholar_claims.py --report                         (what was read; the cites to texts we hold)
  python scripts\\scholar_claims.py --csv data\\shelf\\phai1923_claims.csv

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations
import argparse, csv, datetime, difflib, hashlib, json, os, re, sqlite3, sys, time, types, unicodedata
from pathlib import Path

MARK = "CLAIMS_2026_10_21"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

PROMPT_VERSION = "claims-v1"
API = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
PER_PAGE = 0.007   # the estimate of a page: about 1.5k tokens in, 2.2k out (the thinking capped at 1024)

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
WORKS = {
    "phai1923": {
        "author": "Hemchandra Raychaudhuri",
        "title": "Political History of Ancient India, from the Accession of Parikshit to the Extinction of the Gupta Dynasty",
        "short": "Raychaudhuri, Political History of Ancient India (1923)",
        "publisher": "University of Calcutta", "year": "1923", "edition": "first",
        "source": "Dhananjayarao Gadgil Library, Gokhale Institute of Politics and Economics, Pune: GIPE-004595",
        "handle": "10973/29602", "md5": "75e8d7bd429f9396997cc9e1c2e9f4bd", "pdf_pages": 372,
        "pdf": "data/shelf/phai1923/GIPE-004595.pdf",
        "licence": "public domain: published 1923; the author died in 1957 (India: 60 years after; USA: before 1929)",
        "front": (14, 18), "offset": 18,
        "parts": {"1": (14, 112, "Part I: From the Accession of Parikshit to the Coronation of Bimbisara")},
    },
}

RELATIONS = ("son_of", "father_of", "grandson_of", "descendant_of", "ancestor_of", "brother_of", "wife_of", "married",
             "successor_of", "predecessor_of", "contemporary_of", "priest_of", "teacher_of", "pupil_of", "king_of",
             "capital_of", "located_in", "fought", "defeated", "allied_with", "performed", "dated_to",
             "identified_with", "distinct_from", "named_in", "composed", "other")
STANCES = ("asserts", "reports", "rejects", "doubts")

SYSTEM = """You read one printed page of a work of history and list the historical claims its author makes on that \
page, for a database that checks each claim against the texts he cites. The page is the OCR reading of a print of \
1923: its words may be misread (Brahma1;1a for Br\u0101hma\u1e47a, ,J anamejaya for Janamejaya); read them as the \
author printed them.

Return JSON: {"claims": [...]}. Each claim is an object:
 "subject": the person, people, dynasty, place, text or event the claim is about, in standard IAST (Janamejaya, \
Parik\u1e63it, \u015aatapatha Br\u0101hma\u1e47a, Kuru, Pa\u00f1c\u0101la);
 "subject_printed": the subject as the page prints it, without the OCR's misreadings (Parikshit, Satapatha Brahmana);
 "relation": one of RELATIONS;
 "object": the other term, in standard IAST; a date or a number as the page gives it; or "";
 "claim": the claim in one sentence of at most 35 words, faithful to the author, adding nothing he does not say;
 "quote": 8 to 30 consecutive words of the page that carry the claim, copied from the page's text exactly as it is \
given here, its misreadings too;
 "cites": the sources the author gives for this claim on this page, each as printed (Mbh. I. 95. 85; Mat. 50. 57; \
Sat. Br. XIII. 5. 4. 1-3; Ved. Ind. I. 274; Hopkins, The Great Epic of India, p. 385); [] if none;
 "stance": "asserts" (his own view), "reports" (what a source or a scholar says, given without judging it), \
"rejects" (a view he argues against) or "doubts" (one he leaves open);
 "hedge": his own qualifier of it (probably, apparently, according to tradition, it seems), else "";
 "who": when he reports or rejects another scholar's view, that scholar (Hopkins, Pargiter, Oldenberg), else "".

List every claim the page makes about persons, peoples, dynasties, places, dates, genealogies, priests, sacrifices, \
wars, capitals and texts (which text names whom, and where), and no claim the page does not make. A verse or a \
sentence quoted in Sanskrit or Pali is the source speaking: its claim is "reports", with the source in "cites". The \
running head (POLITICAL HISTORY OF INDIA) and the page number are not claims. A page with no claims (a title, a list \
of contents, an index) gives {"claims": []}.""".replace("RELATIONS", ", ".join(RELATIONS))

# The works a cite names, as the book abbreviates them (its list of abbreviations, pp. xv-xvi) or names them in full.
CITE_WORKS = [
    ("\u015aatapatha Br\u0101hma\u1e47a", r"(?:[S\u015a]at(?:apatha)?[.,]?\s*Br|[S\u015a]atapatha)"),
    ("Aitareya Br\u0101hma\u1e47a", r"Ait(?:areya)?[.,]?\s*Br"),
    ("Aitareya \u0100ra\u1e47yaka", r"Ait(?:areya)?[.,]?\s*\u0100?Ar"),
    ("Gopatha Br\u0101hma\u1e47a", r"Gop(?:atha)?[.,]?\s*Br"),
    ("Taittir\u012bya Br\u0101hma\u1e47a", r"Tait(?:t)?(?:ir\u012bya|iriya)?[.,]?\s*Br"),
    ("Taittir\u012bya Sa\u1e43hit\u0101", r"Tait(?:t)?(?:ir\u012bya|iriya)?[.,]?\s*S(?:a[m\u1e43]h)?"),
    ("Taittir\u012bya \u0100ra\u1e47yaka", r"Tait(?:t)?(?:ir\u012bya|iriya)?[.,]?\s*\u0100?Ar"),
    ("Pa\u00f1cavi\u1e43\u015ba Br\u0101hma\u1e47a", r"Pa[n\u00f1]c(?:h)?(?:avi[m\u1e43][s\u015b]a)?[.,]?\s*Br"),
    ("Jaimin\u012bya Upani\u1e63ad Br\u0101hma\u1e47a", r"Jaim(?:in\u012bya|iniya)?[.,]?\s*Up[.,]?\s*Br"),
    ("B\u1e5bhad\u0101ra\u1e47yaka Upani\u1e63ad", r"B(?:r|\u1e5b)i?h(?:ad\u0101ra\u1e47yaka|adaranyaka)?[.,]?\s*Up"),
    ("Ch\u0101ndogya Upani\u1e63ad", r"Ch(?:h)?(?:\u0101|a)?(?:ndogya)?[.,]?\s*Up"),
    ("Kau\u1e63\u012btaki Upani\u1e63ad", r"Kau(?:sh|\u1e63)(?:\u012btaki|itaki)?[.,]?\s*Up"),
    ("\u1e5agveda", r"(?:R\.\s*V\.|Rig[\s-]*Veda|\u1e5ag[\s-]*veda|Rv\.)"),
    ("Atharvaveda", r"(?:A\.\s*V\.|Atharva[\s-]*Veda)"),
    ("V\u0101jasaneyi Sa\u1e43hit\u0101", r"V(?:\u0101|a)j(?:asaneyi)?[.,]?\s*S"),
    ("Nirukta", r"Nir(?:ukta)?\b"),
    ("\u0100\u015bval\u0101yana G\u1e5bhya S\u016btra", r"(?:\u0100\u015b|As)v(?:al\u0101yana|alayana)?[.,]?\s*G(?:\u1e5b|ri)h"),
    ("\u0100\u015bval\u0101yana \u015arauta S\u016btra", r"(?:\u0100\u015b|As)v(?:al\u0101yana|alayana)?[.,]?\s*(?:\u015a|S)r"),
    ("\u015a\u0101\u1e45kh\u0101yana \u015arauta S\u016btra", r"(?:\u015a\u0101\u1e45kh|Sankh|S\u0101nkh)(?:\u0101yana|ayana)?[.,]?\s*(?:\u015a|S)r"),
    ("K\u0101ty\u0101yana \u015arauta S\u016btra", r"K(?:\u0101|a)ty(?:\u0101yana|ayana)?[.,]?\s*(?:\u015a|S)r"),
    ("Baudh\u0101yana Dharma S\u016btra", r"Bau(?:dh(?:\u0101|a)yana)?[.,]?\s*(?:Dh|S\u016b|Su)"),
    ("Vedic Index", r"Ved(?:ic)?[.,]?\s*Ind(?:ex\b|\.)"),
    ("Mah\u0101bh\u0101rata", r"(?:Mbh|Mah\u0101bh\u0101rata|Mahabharata)"),
    ("Harivam\u015ba", r"Hariv"),
    ("R\u0101m\u0101ya\u1e47a", r"(?:R\u0101m|Ram)(?:\u0101ya\u1e47a|ayana)?\b"),
    ("Matsya Pur\u0101\u1e47a", r"(?:Mat\.|Matsya\s+P)"),                   # not the Matsyas, a people
    ("V\u0101yu Pur\u0101\u1e47a", r"V(?:\u0101|a)yu(?:\s*P|[.,]?\s*\d)"),
    ("Vi\u1e63\u1e47u Pur\u0101\u1e47a", r"Vi(?:sh|\u1e63)(?:\u1e47u|nu)\s*P"),          # not the god
    ("Bh\u0101gavata Pur\u0101\u1e47a", r"Bh(?:\u0101|a)g(?:avata)?(?:\s*P|[.,]?\s*[IVX\d])"),
    ("J\u0101taka", r"J(?:\u0101|a)?t(?:aka)?[.,]?\s*(?:No|\d|[IVX])|J\.\s*(?:No|\d|[IVX])|J\u0101taka|Jataka"),
    ("D\u012bgha Nik\u0101ya", r"(?:D\.\s*(?:N\.|[IVX])|D\u012bgha|Digha)"),
    ("Majjhima Nik\u0101ya", r"(?:M\.\s*(?:N\.|[IVX])|Majjhima)"),
    ("A\u1e45guttara Nik\u0101ya", r"(?:A\u1e45g|Ang(?:uttara)?)[.,]?\s*(?:N|[IVX])"),
    ("Artha\u015b\u0101stra", r"(?:Kau[t\u1e6d]|Artha[s\u015b](?:\u0101|a)stra)"),
    ("A\u1e63\u1e6d\u0101dhy\u0101y\u012b", r"(?:P\u0101\u1e47ini|Panini|Ash[t\u1e6d](?:\u0101|a)dhy|A\u1e63\u1e6d\u0101dhy)"),
    ("Indian Antiquary", r"Ind[.,]?\s*Ant"),
    ("Epigraphia Indica", r"Ep[.,]?\s*Ind"),
    ("Journal of the Royal Asiatic Society", r"J[.,]?\s*R[.,]?\s*A[.,]?\s*S"),
    ("Journal of the Asiatic Society of Bengal", r"J[.,]?\s*A[.,]?\s*S[.,]?\s*B"),
    ("Sacred Books of the East", r"S[.,]?\s*B[.,]?\s*E\b"),
    ("Buddhist India", r"(?:Bud[.,]?\s*Ind|Buddhist\s+India)"),
    ("Carmichael Lectures, 1918", r"Carm[.,]?\s*Lec"),
    ("Early History of India, 1914", r"E[.,]?\s*H[.,]?\s*I\b"),
    ("Ancient Geography of India", r"A[.,]?\s*G[.,]?\s*I\b"),
    ("Corpus Inscriptionum Indicarum, iii", r"C[.,]?\s*I[.,]?\s*I\b"),
]
CITE_RX = [(name, re.compile(r"^\s*(?:" + rx + r")", re.I)) for name, rx in CITE_WORKS]
NAMED_RX = [(name, re.compile(r"\b(?:" + rx + r")", re.I)) for name, rx in CITE_WORKS if len(name) > 6]
LOCUS = re.compile(r"(?<![A-Za-z])(?:[IVXLCivxlc]+(?=[.,])|\d)")
ROMAN_TOKEN = re.compile(r"^[\s.,;:(]*([IVXLC]+)\b", re.I)
VEI_PAGE = re.compile(r"^[\s.,;:]*(?:Vol\.?\s*)?([IV]+)[.,]?\s*(?:p+\.?\s*)?(\d{1,3})\b", re.I)


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


# ---- pages ------------------------------------------------------------------------------------------
def printed_of(work: dict, pdf_page: int) -> str:
    """The page number the book prints: the Foreword's i-v, then pdf - offset; "" for the front matter before."""
    f0, f1 = work["front"]
    if f0 <= pdf_page <= f1:
        return [k for k, v in ROMAN.items() if v == pdf_page - f0 + 1][0]
    if pdf_page > f1:
        return str(pdf_page - work["offset"])
    return ""


def pdf_of(work: dict, printed: str):
    p = str(printed).strip().lower()
    if p in ROMAN:
        n = work["front"][0] + ROMAN[p] - 1
        return n if n <= work["front"][1] else None
    if p.isdigit() and int(p) >= 1:
        return int(p) + work["offset"]
    return None


def parse_pages(work: dict, spec: str) -> list:
    """Printed pages (1-3, i-v, 12, 40-44) into pdf pages, in order; a page the book does not print is refused."""
    out = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        a_, _sep, b_ = part.partition("-")
        x, y = pdf_of(work, a_), pdf_of(work, b_ or a_)
        if x is None or y is None or y < x:
            raise ValueError("not a page the book prints: %s" % part)
        out.extend(range(x, y + 1))
    return sorted(set(out))


def page_join(text: str) -> str:
    """A word cut at a line's end joined (Abhi-\\nmanyu); the soft hyphen taken away."""
    t = (text or "").replace("\r\n", "\n")
    t = re.sub(r"[\u00ad\-]\s*\n\s*", "", t)
    return t.replace("\u00ad", "")


def norm_words(s: str) -> list:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).split()


def quote_check(quote: str, page_text: str):
    """("exact" | "close" | "none" | "short", score): the quotation against the page's own text."""
    q = norm_words(quote)
    if len(q) < 4:
        return "short", 0.0
    w = norm_words(page_join(page_text))
    qs = " ".join(q)
    if qs in " ".join(w):
        return "exact", 1.0
    best = 0.0
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(qs)
    for n in range(max(1, len(q) - 2), len(q) + 3):
        for i in range(0, max(1, len(w) - n + 1)):
            sm.set_seq1(" ".join(w[i:i + n]))
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= max(best, 0.6):
                continue
            best = max(best, sm.ratio())
    return ("close" if best >= 0.85 else "none"), round(best, 3)


# ---- names and cites --------------------------------------------------------------------------------
def pkey(name: str) -> str:
    """A name's key across spellings: diacritics, case and the 1923 transcription aside (Parikshit, Parik\u1e63it;
    Chhandogya, Ch\u0101ndogya; Rig-Veda, \u1e5agveda; Panchala, Pa\u00f1c\u0101la)."""
    s = unicodedata.normalize("NFKD", name or "")
    s = re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())
    for x, y in (("chh", "c"), ("ch", "c"), ("ksh", "ks"), ("sh", "s"), ("ri", "r"), ("w", "v"), ("ee", "i"),
                 ("oo", "u")):
        s = s.replace(x, y)
    return re.sub(r"(.)\1+", r"\1", s)


# CLAIMS_FIX_2026_10_21: cites-v2 ------------------------------------------------------------------------
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


def ours_of(work: str, book: str):
    """(doc code, note) when our corpus holds the place (scholar_shelf.ours_of), else ("", ""). The Mahabharata: ours
    is the critical edition's first book (MBh01; its Adiparvan was published at Poona in 1933), so only a cite of book
    i is ours, and its numbering is not the one an edition of 1923 gives."""
    if work == "Mah\u0101bh\u0101rata":
        return (("MBh01", "ours is the critical edition's book 1 (Poona, 1933): numbered otherwise than the editions "
                          "of 1923") if book == "i" else ("", ""))
    if work in OURS_MORE:   # CLAIMS_FIX_2026_10_21
        return OURS_MORE[work]
    try:
        import scholar_shelf as SH
    except Exception:
        return "", ""
    return SH.ours_of(work, "", book)


def vei_page(cite: dict) -> str:
    """A Vedic Index cite's page as the Cologne file numbers it (Ved. Ind. I. 274: 1-274), else ""."""
    if cite.get("work") != "Vedic Index":
        return ""
    m = VEI_PAGE.match(cite.get("locus") or "")
    if not m or m.group(1).upper() not in ("I", "II"):
        return ""
    return "%d-%03d" % (1 if m.group(1).upper() == "I" else 2, int(m.group(2)))


# ---- the store ----------------------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS claim_works(code TEXT PRIMARY KEY, author TEXT, title TEXT, publisher TEXT, year TEXT,
  source TEXT, handle TEXT, md5 TEXT, licence TEXT, pdf TEXT, pages INTEGER, loaded_at TEXT, mark TEXT);
CREATE TABLE IF NOT EXISTS claim_pages(work TEXT NOT NULL, pdf_page INTEGER NOT NULL, printed TEXT, part TEXT,
  text TEXT, sha256 TEXT, chars INTEGER, PRIMARY KEY(work, pdf_page));
CREATE TABLE IF NOT EXISTS claim_reads(id INTEGER PRIMARY KEY AUTOINCREMENT, work TEXT NOT NULL, pdf_page INTEGER NOT NULL,
  page_sha256 TEXT, prompt_version TEXT, engine TEXT, status TEXT, claims INTEGER, cost_usd REAL, in_tokens INTEGER,
  out_tokens INTEGER, raw TEXT, error TEXT, at TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS ix_claim_reads_page ON claim_reads(work, pdf_page);
CREATE TABLE IF NOT EXISTS claims(id INTEGER PRIMARY KEY AUTOINCREMENT, read_id INTEGER NOT NULL, work TEXT NOT NULL,
  pdf_page INTEGER NOT NULL, printed TEXT, n INTEGER, subject TEXT, subject_printed TEXT, relation TEXT, object TEXT,
  claim TEXT, quote TEXT, quote_check TEXT, quote_score REAL, stance TEXT, hedge TEXT, who TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS ix_claims_read ON claims(read_id);
CREATE TABLE IF NOT EXISTS claim_cites(claim_id INTEGER NOT NULL, n INTEGER, printed TEXT, work TEXT, locus TEXT,
  book TEXT, how TEXT, ours TEXT, note TEXT, vei_page TEXT, reader TEXT, score REAL);
CREATE INDEX IF NOT EXISTS ix_claim_cites_claim ON claim_cites(claim_id);
CREATE TABLE IF NOT EXISTS claim_names(claim_id INTEGER NOT NULL, role TEXT, name TEXT, printed TEXT, pkey TEXT);
CREATE INDEX IF NOT EXISTS ix_claim_names_pkey ON claim_names(pkey);
"""
CURRENT = ("SELECT MAX(id) FROM claim_reads WHERE work = ? AND status = 'ok' GROUP BY pdf_page")


def open_store(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.executescript(SCHEMA)
    for t, col, ty in (("claim_cites", "reader", "TEXT"), ("claim_cites", "score", "REAL"),
                       ("claim_reads", "note", "TEXT")):   # CLAIMS_FIX_2026_10_21
        if col not in {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}:
            con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (t, col, ty))
    con.commit()
    return con


def store_pages(con, code: str, work: dict, pages: list, pdf: str = ""):
    """pages: [(pdf_page, text)]; the work's row and its pages (a page whose text is the same is left as it is)."""
    with con:
        con.execute("INSERT OR REPLACE INTO claim_works(code, author, title, publisher, year, source, handle, md5, licence, "
                    "pdf, pages, loaded_at, mark) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (code, work["author"], work["title"], work["publisher"], work["year"], work["source"], work["handle"],
                     work["md5"], work["licence"], pdf, work["pdf_pages"], now(), MARK))
        for n, text in pages:
            part = next((k for k, (a_, b_, _t) in work["parts"].items() if a_ <= n <= b_), "")
            con.execute("INSERT OR REPLACE INTO claim_pages(work, pdf_page, printed, part, text, sha256, chars) "
                        "VALUES (?,?,?,?,?,?,?)", (code, n, printed_of(work, n), part, text,
                                                   hashlib.sha256((text or "").encode("utf-8")).hexdigest(), len(text or "")))


def extract(pdf: Path) -> list:
    """[(pdf_page, text)] of every page: the scan's own text layer, read with pypdf."""
    from pypdf import PdfReader
    r = PdfReader(str(pdf))
    return [(i, (pg.extract_text() or "")) for i, pg in enumerate(r.pages, 1)]


def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def done_pages(con, code: str, engine: str) -> dict:
    """{pdf_page: read id} of the pages read with this prompt and engine from the text they hold now."""
    rows = con.execute("SELECT r.pdf_page, MAX(r.id) FROM claim_reads r JOIN claim_pages p ON p.work = r.work AND "
                       "p.pdf_page = r.pdf_page AND p.sha256 = r.page_sha256 WHERE r.work = ? AND r.status = 'ok' AND "
                       "r.prompt_version = ? AND r.engine = ? GROUP BY r.pdf_page", (code, PROMPT_VERSION, engine)).fetchall()
    return {p: i for p, i in rows}


# ---- the model --------------------------------------------------------------------------------------
def rest_call(model: str, system: str, prompt: str, key: str, think: int, timeout: float = 180.0, opener=None):
    """One generateContent call (JSON out; the thinking capped); a response shaped as the SDK's, for usage_meter."""
    import urllib.request
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 8192, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": int(think)}}}
    req = urllib.request.Request(API % model, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    op = opener or urllib.request.build_opener()
    with op.open(req, timeout=timeout) as f:
        d = json.loads(f.read().decode("utf-8"))
    cand = (d.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    um = d.get("usageMetadata") or {}
    ns = types.SimpleNamespace
    return ns(text="".join(p.get("text", "") for p in parts if not p.get("thought")),
              candidates=[ns(finish_reason=cand.get("finishReason"))],
              usage_metadata=ns(prompt_token_count=um.get("promptTokenCount"),
                                candidates_token_count=um.get("candidatesTokenCount"),
                                thoughts_token_count=um.get("thoughtsTokenCount") or 0,
                                total_token_count=um.get("totalTokenCount")))


def page_prompt(work: dict, printed: str, text: str) -> str:
    return ("The work: %s.\nThe page: %s (as the book numbers it).\n\nThe page's text (OCR):\n<<<\n%s\n>>>"
            % (work["short"], printed or "unnumbered", (text or "").strip()))


BAD_ESCAPE = re.compile(r'\\(u[0-9a-fA-F]{4}|["\\/nrt]|.|$)', re.S)


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
    if isinstance(d, list):
        d = {"claims": d}
    if not isinstance(d, dict) or not isinstance(d.get("claims"), list):
        return None
    return d["claims"]


def _s(x, n: int) -> str:
    return re.sub(r"\s+", " ", str(x if x is not None else "")).strip()[:n]


def clean_claim(c) -> dict:
    """A claim as stored, or None: the fields cut to their length, the relation and the stance from their lists."""
    if not isinstance(c, dict):
        return None
    out = {"subject": _s(c.get("subject"), 160), "subject_printed": _s(c.get("subject_printed"), 160),
           "relation": _s(c.get("relation"), 40).lower(), "object": _s(c.get("object"), 200),
           "claim": _s(c.get("claim"), 400), "quote": _s(c.get("quote"), 400), "stance": _s(c.get("stance"), 20).lower(),
           "hedge": _s(c.get("hedge"), 80), "who": _s(c.get("who"), 120)}
    if not out["subject"] or not out["claim"]:
        return None
    if out["relation"] not in RELATIONS:
        out["relation"] = "other"
    if out["stance"] not in STANCES:
        out["stance"] = "asserts"
    cites = c.get("cites") or []
    if isinstance(cites, str):
        cites = [x for x in re.split(r";\s*", cites) if x.strip()]
    out["cites"] = [_s(x, 200) for x in cites if isinstance(x, (str, int, float)) and _s(x, 200)][:12]
    return out


def save_read(con, code: str, work: dict, pg: tuple, engine: str, status: str, claims: list, cost: float, usage,
              raw: str, error: str = "", note: str = "") -> int:
    """One read and its claims, in one transaction. pg: (pdf_page, printed, text, sha256)."""
    n_page, printed, text, sha = pg
    pin = getattr(usage, "prompt_token_count", None) if usage is not None else None
    pout = None
    if usage is not None:
        pout = (getattr(usage, "candidates_token_count", None) or 0) + (getattr(usage, "thoughts_token_count", None) or 0)
    at = now()
    with con:
        cur = con.execute("INSERT INTO claim_reads(work, pdf_page, page_sha256, prompt_version, engine, status, claims, "
                          "cost_usd, in_tokens, out_tokens, raw, error, at, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (code, n_page, sha, PROMPT_VERSION, engine, status, len(claims), cost, pin, pout,
                           (raw or "")[:200000], error[:2000] if error else None, at, note or None))
        rid = cur.lastrowid
        prev = ""   # CLAIMS_FIX_2026_10_21: the cite before, for an Ibid
        for k, c in enumerate(claims, 1):
            chk, score = quote_check(c["quote"], text)
            cc = con.execute("INSERT INTO claims(read_id, work, pdf_page, printed, n, subject, subject_printed, relation, "
                             "object, claim, quote, quote_check, quote_score, stance, hedge, who, at) VALUES "
                             "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (rid, code, n_page, printed, k, c["subject"], c["subject_printed"], c["relation"], c["object"],
                              c["claim"], c["quote"], chk, score, c["stance"], c["hedge"], c["who"], at))
            cid = cc.lastrowid
            ctx = c["claim"] + " " + c["quote"]
            for j, p in enumerate(c["cites"], 1):
                r = read_cite(p, ctx, prev)
                prev = r["work"] or prev
                ours, onote = ours_of(r["work"], r["book"]) if r["work"] else ("", "")
                con.execute("INSERT INTO claim_cites(claim_id, n, printed, work, locus, book, how, ours, note, vei_page, "
                            "reader, score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (cid, j, r["printed"], r["work"] or None, r["locus"], r["book"] or None, r["how"] or None,
                             ours or None, onote or None, vei_page(r) or None, CITE_READER, r.get("score")))
            for role, name, printed_name in (("subject", c["subject"], c["subject_printed"]), ("object", c["object"], "")):
                if name and not re.match(r"^[\d\s.,:/-]+$", name):
                    con.execute("INSERT INTO claim_names(claim_id, role, name, printed, pkey) VALUES (?,?,?,?,?)",
                                (cid, role, name, printed_name or None, pkey(name)))
    return rid


def read_pages(a, con, code: str, work: dict, todo: list, caller=None) -> dict:
    """The paid part: each page in todo read, metered, stored; stops at the cap, at --max-usd, or on a hard error."""
    import usage_meter
    engine = "gemini:%s" % a.model
    key = os.environ.get("GEMINI_API_KEY", "") if caller is None else "stub"
    if not key:
        return {"refuse": "GEMINI_API_KEY is not set (.env)"}
    call = caller or (lambda system, prompt: rest_call(a.model, system, prompt, key, a.think))
    got = {"read": 0, "claims": 0, "failed": 0, "cost": 0.0, "stopped": ""}
    for pg in todo:
        if got["cost"] + PER_PAGE > a.max_usd:
            got["stopped"] = "--max-usd %.2f reached (spent %.4f in this run)" % (a.max_usd, got["cost"])
            break
        if not usage_meter.budget_ok(a.db, PER_PAGE):
            got["stopped"] = "the spend cap (python scripts\\set_budget.py shows it)"
            break
        prompt = page_prompt(work, pg[1], pg[2])
        reply, resp, err = "", None, ""
        spent = 0.0   # CLAIMS_FIX_2026_10_21: every attempt's cost, on the page's read
        for attempt in range(4):
            t0 = time.time()
            try:
                resp = call(SYSTEM, prompt)
                reply = getattr(resp, "text", "") or ""
                err = ""
            except Exception as e:   # a network error, a quota, a timeout: waited for, then tried again
                err = "%s: %s" % (type(e).__name__, str(e)[:300])
                resp = None
            cost = 0.0
            if resp is not None:   # a call that failed (a network error, a quota) is not billed
                cost = usage_meter.meter(kind="claims", doc=code, engine=engine, resp=resp, in_chars=len(SYSTEM) + len(prompt),
                                         out_chars=len(reply), units=1, duration_s=time.time() - t0, ok=not err,
                                         db=a.db) or 0.0
            got["cost"] += cost
            spent += cost
            claims = parse_reply(reply) if not err else None
            if claims is not None:
                kept = [x for x in (clean_claim(c) for c in claims) if x]
                save_read(con, code, work, pg, engine, "ok", kept, spent, getattr(resp, "usage_metadata", None), reply,
                          note=("after %d attempt(s)" % (attempt + 1)) if attempt else "")
                got["read"] += 1
                got["claims"] += len(kept)
                print("  page %s (pdf %d): %d claim(s), $%.4f" % (pg[1] or "-", pg[0], len(kept), cost), flush=True)
                break
            if attempt < 3:
                time.sleep(min(30, 2 ** (attempt + 1)) if caller is None else 0)
        else:
            save_read(con, code, work, pg, engine, "failed", [], spent, getattr(resp, "usage_metadata", None), reply,
                      err or "the reply is not the JSON asked for")
            got["failed"] += 1
            print("  page %s (pdf %d): failed (%s)" % (pg[1] or "-", pg[0], (err or "not JSON")[:120]), flush=True)
    return got


# ---- what the shelf and our texts say -----------------------------------------------------------------
def connect_ro(db: str, immutable: bool = False):
    q = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return sqlite3.connect(Path(db).resolve().as_uri() + q, uri=True, timeout=30)


def shelf_and_ours(db: str, immutable: bool, key: str) -> tuple:
    """([(source, lnum, page, name, homonym, body)], [(entity id, canonical, kind, mentions)]) for a name's key."""
    if not Path(db).exists():
        return [], []
    con = connect_ro(db, immutable)
    try:
        shelf, ours = [], []
        try:
            for src, lnum, page, name, hom, body in con.execute(
                    "SELECT source, lnum, page, name, homonym, body FROM shelf_entries ORDER BY source, lnum"):
                if pkey(name) == key:
                    shelf.append((src, lnum, page, name, hom, body))
        except sqlite3.Error:
            pass
        try:
            for eid, canon, kind in con.execute("SELECT id, canonical, kind FROM entities"):
                if pkey(canon) == key:
                    n = con.execute("SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?", (eid,)).fetchone()[0]
                    ours.append((eid, canon, kind, n))
        except sqlite3.Error:
            pass
        return shelf, ours
    finally:
        con.close()


def current_claims(con, code: str, where: str = "", args=()) -> list:
    q = ("SELECT c.id, c.pdf_page, c.printed, c.subject, c.relation, c.object, c.claim, c.quote, c.quote_check, "
         "c.quote_score, c.stance, c.hedge, c.who FROM claims c WHERE c.work = ? AND c.read_id IN (%s)%s "
         "ORDER BY c.pdf_page, c.n" % (CURRENT, where))
    return con.execute(q, (code, code) + tuple(args)).fetchall()


def cites_of(con, cid: int) -> list:
    return con.execute("SELECT printed, work, locus, ours, note, vei_page FROM claim_cites WHERE claim_id = ? ORDER BY n",
                       (cid,)).fetchall()


SHELF_ORDER = {"pui": 0, "vei": 1, "inm": 2}   # CLAIMS_FIX_2026_10_21
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
    k = pkey(a.show)
    rows = current_claims(con, code, " AND c.id IN (SELECT claim_id FROM claim_names WHERE pkey = ?)", (k,))
    print("scholar_claims %s: %s (the key %s)" % (MARK, a.show, k))
    print("  %s:" % work["short"])
    checks = {}
    for cid, n_pdf, printed, subj, rel, obj, claim, quote, chk, score, stance, hedge, who in rows:
        checks[chk] = checks.get(chk, 0) + 1
        print("    p. %s (pdf %d) [%s%s%s] %s %s %s" % (printed or "-", n_pdf, stance, ("; " + hedge) if hedge else "",
                                                     ("; after " + who) if who else "", subj, rel, obj or ""))
        print("        %s" % claim)
        print("        quote (%s%s): \"%s\"" % (chk, (" %.2f" % score) if chk == "close" else "", quote))
        for printed_c, w, locus, ours, note, vp in cites_of(con, cid):
            print("        cites %s%s%s%s" % (printed_c, ("  [%s %s]" % (w, locus)) if w else "",
                                             ("  [ours: %s%s]" % (ours, "; " + note if note else "")) if ours else "",
                                             ("  [the Vedic Index's page %s]" % vp) if vp else ""))
    shelf, ours = shelf_and_ours(a.db, a.immutable, k)
    shelf.sort(key=lambda e: (SHELF_ORDER.get(e[0], 9), e[1]))   # CLAIMS_FIX_2026_10_21: Dikshitar first
    if shelf:
        print("  the indexes (scholar_shelf.py --show %s for all they say):" % a.show)
        for src in sorted({e[0] for e in shelf}, key=lambda s: SHELF_ORDER.get(s, 9)):
            print("    %s: %s" % (src.upper(), SHELF_CREDIT.get(src, src)))
        for src, lnum, page, name, hom, body in shelf[:a.limit]:
            print("    %s %s, page %s: %s%s  %s" % (src.upper(), lnum, page, name, (" (%s)" % hom) if hom else "",
                                                 (body or "")[:a.width].replace("\n", " ")))
    for eid, canon, kind, nm in ours:
        print("  ours: entity %d %s (%s), named %d time(s) in our texts" % (eid, canon, kind, nm))
    if not rows:
        say("no claim of %s names %s yet" % (work["short"], a.show),
            "python scripts\\scholar_claims.py --part 1 --yes" if not con.execute(
                "SELECT 1 FROM claim_reads WHERE work = ? AND status = 'ok' LIMIT 1", (code,)).fetchone() else "")
        return 0
    pages = sorted({r[2] or "-" for r in rows}, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, x))
    say("%d claim(s) on %s on %d page(s) (%s); quotations: %s; %d entr%s of the indexes; %d of our entities"
        % (len(rows), a.show, len(pages), ", ".join(pages[:20]),
           ", ".join("%s %d" % (x, checks[x]) for x in ("exact", "close", "none", "short") if checks.get(x)),
           len(shelf), "y" if len(shelf) == 1 else "ies", len(ours)), "")
    return 0


def report(a, con, code: str, work: dict) -> int:
    rows = current_claims(con, code)
    reads = con.execute("SELECT status, COUNT(*), SUM(cost_usd) FROM claim_reads WHERE work = ? GROUP BY status",
                        (code,)).fetchall()
    print("scholar_claims %s: %s" % (MARK, work["short"]))
    for st, n, c in reads:
        print("  reads %s: %d ($%.4f)" % (st, n, c or 0.0))
    print(meter_line(a.db, a.immutable, code))   # CLAIMS_FIX_2026_10_21: before the fix a failed read recorded $0
    pages = {r[1] for r in rows}
    chk, rel, stn = {}, {}, {}
    for r in rows:
        chk[r[8]] = chk.get(r[8], 0) + 1
        rel[r[4]] = rel.get(r[4], 0) + 1
        stn[r[10]] = stn.get(r[10], 0) + 1
    nread = len(con.execute(CURRENT, (code,)).fetchall())
    print("  claims: %d from %d page(s) read (%d with a claim); quotations exact %d, close %d, not on the page %d, too "
          "short %d" % (len(rows), nread, len(pages), chk.get("exact", 0), chk.get("close", 0), chk.get("none", 0),
                        chk.get("short", 0)))
    print("  stances: " + ", ".join("%s %d" % (k, v) for k, v in sorted(stn.items(), key=lambda x: -x[1])))
    print("  relations: " + ", ".join("%s %d" % (k, v) for k, v in sorted(rel.items(), key=lambda x: -x[1])))
    works = con.execute("SELECT x.work, COUNT(*), SUM(x.ours IS NOT NULL) FROM claim_cites x JOIN claims c ON c.id = x.claim_id "
                        "WHERE c.work = ? AND c.read_id IN (%s) GROUP BY x.work ORDER BY 2 DESC" % CURRENT,
                        (code, code)).fetchall()
    print("  cites by the work they name (and those in a text we hold):")
    for w, n, o in works[:30]:
        print("    %-44s %4d%s" % (w or "(not read: as printed)", n, ("   ours %d" % o) if o else ""))
    mine = con.execute("SELECT c.printed, c.pdf_page, c.subject, x.printed, x.ours, x.note FROM claim_cites x JOIN claims c "
                       "ON c.id = x.claim_id WHERE c.work = ? AND c.read_id IN (%s) AND x.ours IS NOT NULL ORDER BY "
                       "c.pdf_page" % CURRENT, (code, code)).fetchall()
    if mine:
        print("  to check against our texts (%d):" % len(mine))
        for printed, n_pdf, subj, cp, ours, note in mine[:a.limit]:
            print("    p. %s: %s: %s -> %s%s" % (printed, subj, cp, ours, ("; " + note) if note else ""))
    bad = [r for r in rows if r[8] == "none"]
    if bad:
        print("  quotations not on the page (a person checks them; the claim stands only with its page):")
        for r in bad[:a.limit]:
            print("    p. %s (pdf %d) %s: \"%s\" (%.2f)" % (r[2], r[1], r[3], r[7][:120], r[9] or 0))
    say("%d claim(s) of %s on %d page(s); %d cite(s) to texts we hold" % (len(rows), work["short"], len(pages), len(mine)),
        "python scripts\\scholar_claims.py --show Janamejaya" if rows else "python scripts\\scholar_claims.py --part 1 --yes")
    return 0


def to_csv(a, con, code: str) -> int:
    rows = current_claims(con, code)
    with open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["work", "page", "pdf_page", "subject", "relation", "object", "claim", "quote", "quote_check",
                    "quote_score", "stance", "hedge", "who", "cites", "ours"])
        for r in rows:
            cs = cites_of(con, r[0])
            w.writerow([code, r[2], r[1], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12],
                        "; ".join(c[0] for c in cs), "; ".join(sorted({c[3] for c in cs if c[3]}))])
    say("%d claim(s) written to %s" % (len(rows), a.csv), "")
    return 0


# ---- main ---------------------------------------------------------------------------------------------
def budget_line(db: str, immutable: bool) -> str:
    try:
        con = connect_ro(db, immutable)
        try:
            r = con.execute("SELECT budget_usd, spent_usd, paused FROM budget_state WHERE id = 1").fetchone()
        finally:
            con.close()
        if r:
            return "the spend cap: $%.2f spent of $%.2f%s" % (r[1] or 0, r[0] or 0, " (PAUSED)" if r[2] else "")
    except sqlite3.Error:
        pass
    return "the spend cap: not read"


def main(argv=None, caller=None) -> int:
    ap = argparse.ArgumentParser(description="A scholar's book read into claims with their pages (%s)" % MARK)
    ap.add_argument("--work", default="phai1923", choices=sorted(WORKS))
    ap.add_argument("--pdf", default="", help="the scan (default: the work's place under data/shelf)")
    ap.add_argument("--claims-db", default="data/shelf/claims.db")
    ap.add_argument("--db", default="data/context.db", help="the shelf and our entities (read); the meter's rows")
    ap.add_argument("--extract", action="store_true", help="free: the pages' text from the scan into the claims database")
    ap.add_argument("--part", default="", help="a part of the book: 1 (Part I)")
    ap.add_argument("--pages", default="", help="printed pages: 1-3, i-v, 12, 40-44")
    ap.add_argument("--redo", action="store_true", help="read again pages read already (a new read; the old one kept)")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--think", type=int, default=1024, help="the thinking budget of each call (tokens)")
    ap.add_argument("--max-usd", type=float, default=1.50, help="stop this run once it has spent this much")
    ap.add_argument("--yes", action="store_true", help="read the pages (paid; metered; the cap asked before each)")
    ap.add_argument("--show", default="")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--csv", default="")
    ap.add_argument("--reparse", action="store_true", help="free: a failed page read again from its stored reply")
    ap.add_argument("--recite", action="store_true", help="free: the cites read again (cites-v2)")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--width", type=int, default=160)
    ap.add_argument("--immutable", action="store_true", help="read --db as an immutable copy (a backup)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    os.chdir(ROOT)
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    code, work = a.work, WORKS[a.work]
    if a.model.startswith(("claude", "anthropic")):
        say("this tool reads with Gemini (Google's cap): --model names a Gemini model", "")
        return 2
    if not Path(a.claims_db).exists() and not (a.extract or a.yes):   # the plan makes nothing
        print("scholar_claims %s: %s" % (MARK, work["short"]))
        pdf = Path(a.pdf or work["pdf"])
        print("  the scan: %s (%s); the claims database %s: not made yet" % (pdf, "here" if pdf.exists() else "NOT HERE",
                                                                             a.claims_db))
        say("nothing read from %s yet" % work["short"], "python scripts\\scholar_claims.py --extract   (free)")
        return 0
    con = open_store(a.claims_db)
    try:
        if a.show:
            return show_name(a, con, code, work)
        if a.report:
            return report(a, con, code, work)
        if a.csv:
            return to_csv(a, con, code)
        if a.reparse:   # CLAIMS_FIX_2026_10_21
            return reparse(a, con, code, work)
        if a.recite:
            return recite(a, con, code, work)
        have = con.execute("SELECT COUNT(*) FROM claim_pages WHERE work = ?", (code,)).fetchone()[0]
        pdf = Path(a.pdf or work["pdf"])
        print("scholar_claims %s: %s" % (MARK, work["short"]))
        print("  the scan: %s (%s)" % (pdf, "here" if pdf.exists() else "NOT HERE"))
        if a.extract or (a.yes and not have):
            if not pdf.exists():
                say("the scan is not at %s" % pdf, "")
                return 1
            m5 = md5_of(pdf)
            if m5 != work["md5"]:
                say("the scan at %s is not the copy registered (md5 %s, not %s): nothing read" % (pdf, m5, work["md5"]), "")
                return 1
            pages = extract(pdf)
            if len(pages) != work["pdf_pages"]:
                say("the scan has %d pages, not %d: nothing read" % (len(pages), work["pdf_pages"]), "")
                return 1
            store_pages(con, code, work, pages, str(pdf))
            have = len(pages)
            empty = sum(1 for _n, t in pages if len((t or "").strip()) < 40)
            print("  extracted: %d pages (%d with almost no text) into %s" % (have, empty, a.claims_db))
            if a.extract and not a.yes:
                say("the text of %d pages of %s is in %s (free)" % (have, work["short"], a.claims_db),
                    "python scripts\\scholar_claims.py --pages 1-3 --yes   (a trial: about $%.2f)" % (3 * PER_PAGE))
                return 0
        if not have:
            say("the pages are not read from the scan yet", "python scripts\\scholar_claims.py --extract   (free)")
            return 1
        try:
            if a.pages:
                want = parse_pages(work, a.pages)
            elif a.part:
                if a.part not in work["parts"]:
                    say("the parts defined: %s" % ", ".join(sorted(work["parts"])), "")
                    return 2
                want = list(range(work["parts"][a.part][0], work["parts"][a.part][1] + 1))
            else:
                want = list(range(work["parts"]["1"][0], work["parts"]["1"][1] + 1))
        except ValueError as e:
            say(str(e), "")
            return 2
        engine = "gemini:%s" % a.model
        done = done_pages(con, code, engine)
        pages = {r[0]: r for r in con.execute("SELECT pdf_page, printed, text, sha256 FROM claim_pages WHERE work = ?", (code,))}
        todo = [pages[n] for n in want if n in pages and (a.redo or n not in done)]
        print("  pages asked: %d (printed %s to %s); read already %d; to read %d; about $%.2f (%s)"
              % (len(want), printed_of(work, want[0]) if want else "-", printed_of(work, want[-1]) if want else "-",
                 len([n for n in want if n in done]), len(todo), len(todo) * PER_PAGE, engine))
        print("  " + budget_line(a.db, a.immutable))
        if not a.yes:
            if not todo:
                say("every page asked is read already (--redo reads again)", "python scripts\\scholar_claims.py --report")
                return 0
            say("%d page(s) of %s to read, about $%.2f; nothing sent" % (len(todo), work["short"], len(todo) * PER_PAGE),
                "python scripts\\scholar_claims.py %s --yes" % (("--pages %s" % a.pages) if a.pages else
                                                               ("--part %s" % (a.part or "1"))))
            return 0
        if not todo:
            say("every page asked is read already", "python scripts\\scholar_claims.py --report")
            return 0
        if not Path(a.db).exists():
            say("%s not found: the meter and the cap live there" % a.db, "")
            return 1
        got = read_pages(a, con, code, work, todo, caller)
        if got.get("refuse"):
            say(got["refuse"], "")
            return 1
        left = len(todo) - got["read"] - got["failed"]
        verdict = ("%d page(s) of %s read: %d claim(s); %d failed; $%.4f" % (got["read"], work["short"], got["claims"],
                                                                           got["failed"], got["cost"]))
        if got["stopped"]:
            verdict += "; stopped: %s (%d left)" % (got["stopped"], left)
        say(verdict, "python scripts\\scholar_claims.py --report",
            ["python scripts\\scholar_claims.py --show Janamejaya",
             "python scripts\\scholar_claims.py --csv data\\shelf\\%s_claims.csv" % code])
        return 0 if not got["failed"] and not got["stopped"] else 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
