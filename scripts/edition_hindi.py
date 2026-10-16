#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
edition_hindi.py  (2026-10-16)  CLASSIFY_HINDI_2026_10_16

Is a passage an edition's own Hindi (the editor's translation under a verse, his commentary, his preface) and not
Sanskrit? Both are written in Devanagari, so the script cannot tell them apart; the words can. Hindi's postpositions
and verbs (hai, mein, nahin, chahie, karna, kiya ...) are not Sanskrit, and Sanskrit's visarga and its words ending
in a virama are rare in Hindi.

hindi_of(text) -> (bool, why). True when all of these hold:
  - six Devanagari words or more;
  - no OCR debris: fewer than two Latin words, once a scan's watermark line ("Digitized by eGangotri", "Jangamwadi
    Math Collection") is taken out;
  - two different Hindi words or more, one of them of STRONG (words Sanskrit does not have); WEAK holds words that
    are Hindi but also Sanskrit forms (ka, ke, ko, par, dvara, kare, hota, gaya, jata, jate, bhi);
  - the Hindi words (with a word ending in -on or -aen, Hindi's plural oblique and its subjunctive) are 12% of the
    words or more, and more than the Sanskrit marks (a visarga, a word ending in a virama).

Measured on the 15 Oct backup (passages not typed noise or frontmatter): nothing in the Hayasirsa Pancaratra, MBh01
or the Tantrik Texts vol. I; 815 passages of the Karanagama (Prof. Rama Chandra Pandey's Hindi), 107 of the
AkashBhairavaKalpam, 17 of the Daivat-Sanhita, 10 of the Rgveda-samhita vol. ii (its Hindi notes), 8,485 of the
Yoga-vasistha (Lala Baijnath's Hindi; the text is withdrawn); 4 garbled readings elsewhere. A person reads the dry run
of scripts/classify_hindi.py before anything is tagged.
"""
from __future__ import annotations
import re

MARK = "CLASSIFY_HINDI_2026_10_16"

STRONG = frozenset((
    "\u0939\u0948", "\u0939\u0948\u0902", "\u0925\u093e", "\u0925\u0947", "\u0915\u0940", "\u0938\u0947", "\u092e\u0947\u0902", "\u0928\u0947",
    "\u0914\u0930", "\u0928\u0939\u0940\u0902", "\u0915\u0930\u0947\u0902", "\u0915\u0930\u0928\u093e", "\u0915\u0930\u0915\u0947", "\u0915\u093f\u092f\u093e", "\u0915\u0930\u093e\u090f\u0901", "\u0915\u0930\u093e\u092f\u0947",
    "\u0915\u0930\u093e\u090f", "\u0915\u0930\u093e\u090f\u0902", "\u0939\u094b\u0924\u0940", "\u0939\u094b\u0924\u0947", "\u0939\u094b\u0928\u093e", "\u0939\u094b\u0917\u093e", "\u0939\u094b\u0917\u0940", "\u091c\u093e\u0924\u0940",
    "\u091a\u093e\u0939\u093f\u090f", "\u0932\u093f\u090f", "\u0932\u093f\u092f\u0947", "\u0907\u0938\u0932\u093f\u092f\u0947", "\u0907\u0938\u0932\u093f\u090f", "\u0935\u0939", "\u092f\u0939", "\u091c\u094b",
    "\u0909\u0938", "\u0907\u0938", "\u0909\u0938\u0915\u0947", "\u0907\u0938\u0915\u0947", "\u0909\u0928\u0915\u0947", "\u0907\u0928\u0915\u0947", "\u0905\u092a\u0928\u0947", "\u0935\u093e\u0932\u093e",
    "\u0935\u093e\u0932\u0947", "\u0935\u093e\u0932\u0940", "\u0938\u093e\u0925", "\u092c\u093e\u0926", "\u092a\u0939\u0932\u0947", "\u0939\u0941\u0906", "\u0939\u0941\u090f", "\u0939\u0941\u0908",
    "\u0917\u092f\u0947", "\u0917\u092f\u0940", "\u0917\u090f", "\u0917\u0908", "\u0926\u093f\u092f\u093e", "\u0926\u093f\u090f", "\u0926\u0947\u0924\u093e", "\u0926\u0947\u0924\u0947",
    "\u0926\u0947\u0928\u093e", "\u0932\u0947\u0915\u0930", "\u0915\u0930\u0924\u0947", "\u0915\u0930\u0924\u093e", "\u0915\u0930\u0924\u0940", "\u092b\u093f\u0930", "\u0930\u0916\u0947", "\u0930\u0916\u0947\u0902",
    "\u0921\u093e\u0932\u0947", "\u092c\u0928\u093e\u090f\u0901", "\u092c\u0928\u093e\u092f\u0947", "\u0915\u0939\u093e", "\u0915\u0939\u0924\u0947",
))
WEAK = frozenset((
    "\u0915\u093e", "\u0915\u0947", "\u0915\u094b", "\u092a\u0930", "\u0926\u094d\u0935\u093e\u0930\u093e", "\u0915\u0930\u0947", "\u0939\u094b\u0924\u093e", "\u0917\u092f\u093e",
    "\u091c\u093e\u0924\u093e", "\u091c\u093e\u0924\u0947", "\u092d\u0940",
))
WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")
JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")       # = scholar_translate.JUNK, redeem.JUNK
WATERMARK = re.compile(r"(?im)^.*(Digiti[sz]?z?ed by|eGangotri|Jangamwadi|Math Collection|\bCC-?0\b).*$")
VISARGA, VIRAMA = "\u0903", "\u094d"
OBLIQUE = ("\u094b\u0902", "\u093e\u090f\u0901")   # -on, -aen
MIN_WORDS, MIN_SHARE = 6, 0.12


def hindi_of(text) -> tuple:
    """(True, why) when the passage reads as Hindi, else (False, why); never raises."""
    t = WATERMARK.sub(" ", str(text or ""))
    ws = WORD.findall(t)
    n = len(ws)
    if n < MIN_WORDS:
        return False, "fewer than %d words" % MIN_WORDS
    if len(JUNK.findall(t)) >= 2:
        return False, "OCR debris (Latin words)"
    strong = {w for w in ws if w in STRONG}
    weak = {w for w in ws if w in WEAK}
    hits = sum(1 for w in ws if w in STRONG or w in WEAK or w.endswith(OBLIQUE))
    marks = t.count(VISARGA) + sum(1 for w in ws if w.endswith(VIRAMA))
    why = "%d of %d words Hindi (%d different), %d Sanskrit mark(s)" % (hits, n, len(strong | weak), marks)
    ok = bool(strong) and len(strong | weak) >= 2 and hits >= MIN_SHARE * n and hits > marks
    return ok, why


def is_hindi(text) -> bool:
    return hindi_of(text)[0]
