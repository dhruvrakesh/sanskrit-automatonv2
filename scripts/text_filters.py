#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
text_filters.py — Pre/post translation filters for Sanskrit passages.

Phase Q (2026-07-20): adds score_translation_quality() — a free (no-API)
heuristic QA score for stored translations, used by qa_scan.py, retranslate.py
and the translate write-path.
"""
from __future__ import annotations
import re

DEV_RE = re.compile(r"[ऀ-ॿ]")          # Devanagari block
DEV_DIGIT_RE = re.compile(r"[०-९]")     # Devanagari digits (verse-numbers in raw OCR)
ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—–\*'\"` ~^=।॥]+$")
MQQ_RE = re.compile(r"^[\"']{1,4}$")
LATIN_RE = re.compile(r"[A-Za-z]")

# Common Hindi function words / postpositions. A genuine Hindi translation of
# any length contains several; raw Sanskrit OCR echoed as "Hindi" contains none.
_HI_FUNC_WORDS = (
    "है", "हैं", "था", "थे", "थी", "के", "में", "और", "ने", "को", "से",
    "का", "की", "हुआ", "गया", "कहा", "यह", "वह", "पर", "भी", "तथा", "किया", "हो",
)

# Model refusal / boilerplate strings — anything containing these → junk
JUNK_PHRASES = tuple(s.lower() for s in [
    # Generic refusals
    "i am not able to provide a translation",
    "i am not able to translate this snippet",
    "i cannot translate",
    "i'm unable to translate",
    "i'm sorry, but",
    "i'm sorry, i cannot",
    "i am sorry",
    "sorry, but",
    # Content assessment refusals
    "the translation is unclear",
    "does not form a coherent",
    "appears to be a mix of",
    "please provide a complete and coherent snippet",
    "not enough context to translate",
    "unable to translate",
    "this text is not in sanskrit",
    "this does not appear to be",
    "does not appear to be in sanskrit",
    "does not appear to be",
    "the provided text",
    "the text you provided",
    "the text appears to be",
    "this appears to be",
    "cannot be translated",
    "not recognizable as",
    "not a valid sanskrit",
    "not in sanskrit",
    "no valid text",
    "cannot identify",
    "incomplete text",
    "appears to be noise",
    "seems to be noise",
    # Technical/OCR artifact responses
    "garbled",
    "illegible",
    "the text is too",
    "insufficient text",
    "no sanskrit text",
    # Transliteration-only responses (model echoing garble)
    "[echo]",
    "<<no translation>>",
    "n/a",
])

def frac_devanagari(s: str) -> float:
    """Fraction of Devanagari characters (U+0900–U+097F) in string."""
    if not s: return 0.0
    d = len(DEV_RE.findall(s))
    return d / max(1, len(s))

def has_any_devanagari(s: str) -> bool:
    return bool(DEV_RE.search(s))

def looks_like_heading(s: str) -> bool:
    if not s: return False
    t = s.strip()
    if len(t) <= 2: return True
    if t.endswith(":"): return True
    if t.isupper() and not DEV_RE.search(t): return True
    return False

def looks_like_table_fragment(s: str) -> bool:
    return bool(re.search(r"\b[ivxlcdm]+\b\s*[.)]", s, flags=re.I)) \
        or bool(re.search(r"^\s*[\-•*]\s+\w+", s))

# Publisher/collection banners that appear ON text pages (mixed with
# Devanagari), so they must be checked BEFORE the Devanagari guard below.
# Observed 2026-08-01: "VEDIC LITERATURECOLLECTION नीलमतपुराणम् ..." (q:0.27)
# slipped through and produced a nonsense "translation" of a header page.
_PUBLISHER_BANNERS = (
    "vedic literature", "literaturecollection", "digital library",
    "gretil", "www.", "http://", "https://", "sanskritdocuments",
    "all rights reserved", "e-text", "input by",
)

def looks_like_frontmatter(s: str) -> bool:
    """Detect preface/intro/TOC/publisher-header content that should not be
    translated. Publisher banners are caught even when Devanagari is present."""
    lower_all = s.lower()
    if any(sig in lower_all for sig in _PUBLISHER_BANNERS):
        return True
    if frac_devanagari(s) > 0.05:
        return False  # has significant Devanagari — not frontmatter
    lower = s.lower()
    frontmatter_signals = [
        "table of contents", "preface", "foreword", "introduction",
        "bibliography", "index", "copyright", "all rights reserved",
        "printed in", "published by", "isbn", "transliteration scheme",
        "abbreviations", "acknowledgements",
    ]
    return any(sig in lower for sig in frontmatter_signals)

def is_noise(s: str) -> bool:
    if not s: return True
    t = s.strip()
    if not t: return True
    if ONLY_PUNCT_RE.match(t): return True
    if MQQ_RE.match(t): return True
    return False

# Hindi-side refusal boilerplate (Phase HI). The model may refuse in Hindi;
# these must be caught so a Hindi refusal is stored empty, not as a "translation".
JUNK_PHRASES_HI = tuple([
    "अनुवाद नहीं", "अनुवाद करने में असमर्थ", "यह पाठ",
    "स्पष्ट नहीं", "संस्कृत नहीं", "प्रदान नहीं कर",
    "क्षमा कर", "मैं असमर्थ", "पठनीय नहीं",
])

_SENT_END_RE = re.compile(r"[.।॥!?](?:\s|$)|//")

# Trailing OCR/meta caveat phrases the model appends after faithfully
# translating the legible part of a partly-garbled verse. Curated
# conservatively — clear source/translation-quality meta only, so salvage
# never strips legitimate content. Union of the hard refusals (JUNK_PHRASES)
# plus a few partial phrasings the refusal list misses.
_CAVEAT_EXTRA = (
    "appears to be a mix", "the rest is unclear", "the rest of the text",
    "the remaining text", "the remainder of", "the provided text",
    "unclear due to", "due to ocr", "due to the ocr", "the ocr",
    "illegible portion", "difficult to render", "cannot be reliably",
    "translator's note", "the sanskrit here is",
)
_CAVEAT_HI_EXTRA = (
    "शेष पाठ", "शेष भाग", "अस्पष्ट है", "ओसीआर", "पाठ अस्पष्ट",
)

def salvage_translation(out: str, lang: str = "en") -> str:
    """Fidelity guard (2026-08-02). Three outcomes:

      * no caveat present            -> the input is returned UNCHANGED
      * legible translation + caveat -> the faithful part is kept, the trailing
                                        OCR/meta caveat dropped, and a " […]"
                                        lacuna marker appended (Debroy convention)
      * pure refusal / nothing before the caveat -> "" (empty)

    This keeps the original thought when the model translates the readable part
    of a partly-garbled verse and then comments on the illegible remainder,
    instead of emptying the whole verse and losing a faithful rendering.
    Errs toward UNDER-stripping: only a complete sentence before a clear caveat
    is salvaged.
    """
    if not out or not out.strip():
        return ""
    t = out.strip()
    low = t.lower()
    cut = len(t); found = False
    for ph in JUNK_PHRASES + _CAVEAT_EXTRA:
        i = low.find(ph)
        if 0 <= i < cut:
            cut = i; found = True
    if lang == "hi":
        for ph in JUNK_PHRASES_HI + _CAVEAT_HI_EXTRA:
            i = t.find(ph)
            if 0 <= i < cut:
                cut = i; found = True
    if not found:
        return t  # no caveat — unchanged
    head = t[:cut]
    ends = list(_SENT_END_RE.finditer(head))
    if not ends:
        return ""  # no complete sentence before the caveat — do not salvage
    salvaged = head[:ends[-1].end()].strip()
    if (len(salvaged) >= 15
            and not is_translation_boilerplate(salvaged, lang=lang)
            and not is_source_echo("", salvaged, lang)):
        return salvaged + " […]"
    return ""


def is_translation_boilerplate(en: str, lang: str = "en") -> bool:
    """Return True if the translation string is a model refusal or garbage.

    lang='hi' also screens the Hindi refusal phrases (Phase HI). The English
    phrase list is always applied too, since the model sometimes refuses in
    English even when asked for Hindi.
    """
    if not en: return True
    t = en.strip().lower()
    if not t: return True
    if ONLY_PUNCT_RE.match(t): return True
    if MQQ_RE.match(t): return True
    if len(t) < 4: return True
    if any(x in t for x in JUNK_PHRASES): return True
    if lang == "hi" and any(x in en for x in JUNK_PHRASES_HI): return True
    return False

def should_translate(s: str, *, min_dev: float = 0.05) -> bool:
    """Return True if this passage contains enough Sanskrit to warrant translation.

    Lowered default min_dev from 0.08 → 0.05 to catch mixed Sanskrit-English commentary.
    """
    if is_noise(s): return False
    if looks_like_heading(s): return False
    if looks_like_table_fragment(s): return False
    if looks_like_frontmatter(s): return False
    return frac_devanagari(s) >= min_dev

def clean_for_mt(s: str) -> str:
    """Clean passage for machine translation — remove OCR artifacts, preserve Sanskrit."""
    # Remove leading bullet/list markers
    s = re.sub(r"^\s*[\-•*]\s+", "", s)
    # Remove standalone page labels
    s = re.sub(r"^\s*Page\s+\d+\s*$", "", s, flags=re.I)
    # Remove OCR bracket artifacts like [5°], [12*], [fol. 3]
    s = re.sub(r"\[\s*\d+[°*]\s*\]", "", s)
    s = re.sub(r"\[fol\.\s*\d+\w*\]", "", s, flags=re.I)
    # Normalize multiple spaces
    s = re.sub(r"  +", " ", s)
    return s.strip()

def score_passage_quality(s: str) -> float:
    """Quality score 0.0–1.0 for a Sanskrit passage.
    Based on Devanagari density, presence of dandas, and absence of noise.
    """
    if not s or is_noise(s): return 0.0
    from normalize_text import count_dandas
    dev_frac = frac_devanagari(s)
    single_d, double_d = count_dandas(s)
    # Weight: 60% Devanagari density + 40% danda presence (capped)
    danda_score = min(1.0, (single_d + double_d * 2) / 5.0)
    return round(0.6 * dev_frac + 0.4 * danda_score, 3)


# ── Source-echo detection (2026-08-02) ───────────────────────────────────────
# A "translation" that is really the untranslated source echoed back — raw
# Sanskrit for a Hindi target, or Devanagari/OCR-gibberish for an English
# target. These slipped past the QA scorer (they can be Devanagari-dominant, or
# for English carried embedded verse-number digits) and reached the reader as
# garbled non-translations. Measured 2026-08-02: 2 Hindi + 15 English rows.

def is_source_echo(src: str, out: str, lang: str = "en") -> bool:
    """True if `out` is the source echoed rather than a real translation.

    Calibrated against the live corpus: flags exactly the known echoes, zero
    false positives on 10,300 good rows.
    """
    o = (out or "").strip()
    if not o:
        return False
    if lang == "hi":
        # Hindi echoes are Devanagari-dominant raw Sanskrit.
        if frac_devanagari(o) < 0.5:
            return False
        has_func = any(w in o for w in _HI_FUNC_WORDS)
        has_vnum = bool(DEV_DIGIT_RE.search(o))
        overlap = 0.0
        if src:
            ss = set(src.split()); oo = set(o.split())
            overlap = len(ss & oo) / max(1, len(ss))
        # A substantial Devanagari block with NO Hindi grammar = raw Sanskrit.
        if not has_func and len(o) > 30:
            return True
        # Embedded verse-number digits + notable overlap with the source.
        if has_vnum and overlap > 0.4:
            return True
        # Near-verbatim copy of the source.
        if overlap > 0.6:
            return True
        return False
    # Latin-script target (English): the output is the Devanagari source, or
    # carries embedded Devanagari verse-number digits / OCR gibberish.
    if DEV_DIGIT_RE.search(o):
        return True
    if frac_devanagari(o) > 0.5:
        return True
    return False


# ── Phase Q: translation QA (heuristic, no API calls) ────────────────────────

_GLOSS_PAIR_RE = re.compile(r"^\s*([^|/\n]{2,60})\s*\|\s*([^|/\n]{2,60})\s*$")

def score_translation_quality(src: str, translation: str, lang: str = "en") -> float:
    """Heuristic QA score 0.0–1.0 for a stored translation against its source.

    Free — no API calls. Deductive scoring from 1.0.

    lang='en' (default): expects Latin-script English output; Devanagari in the
    output is untranslated residue (penalty); no Latin letters at all is fatal.

    lang='hi' (Phase HI): polarity INVERTS — the output must be Devanagari-
    dominant; Latin-script residue is the penalty, and absence of Devanagari is
    fatal. Length band recalibrated (hi/sa char ratio ~0.9–2.5 vs en/sa 1.0–3.5,
    because Hindi tatsama vocabulary tracks the Sanskrit closely). The gloss-pair
    and empty/boilerplate checks are shared; the " / " pāda-slash artifact check
    is English-specific and skipped for Hindi.
    """
    if not translation:
        return 0.0
    t = translation.strip()
    # Honest-refusal tokens: [ILLEGIBLE] (en) and [अस्पष्ट] (hi)
    if not t or t in ("[ILLEGIBLE]", "[अस्पष्ट]"):
        return 0.0
    if is_translation_boilerplate(t, lang=lang):
        return 0.0
    # Source echoed back is not a translation (2026-08-02).
    if is_source_echo(src, t, lang):
        return 0.0

    score = 1.0
    src_len = max(1, len((src or "").strip()))
    ratio = len(t) / src_len
    dev = frac_devanagari(t)

    # Shared: repeated gloss-pair ("X | X")
    m = _GLOSS_PAIR_RE.match(t)
    if m and m.group(1).strip().lower() == m.group(2).strip().lower():
        score -= 0.6

    if lang == "hi":
        # Length band for Sanskrit→Hindi
        if ratio < 0.5:
            score -= 0.4          # truncation
        elif ratio < 0.8:
            score -= 0.15
        elif ratio > 3.5:
            score -= 0.3          # ramble
        elif ratio > 2.5:
            score -= 0.1
        # Hindi output MUST be Devanagari-dominant
        if dev < 0.30:
            score -= 0.5          # not actually Hindi
        elif dev < 0.55:
            score -= 0.2
        # Latin residue is the penalty here (proper nouns in IAST are a few
        # chars; a wall of Latin means untranslated English leaked in)
        latin = len(LATIN_RE.findall(t)) / max(1, len(t))
        if latin > 0.25:
            score -= 0.3
        elif latin > 0.12:
            score -= 0.1
        return round(max(0.0, min(1.0, score)), 3)

    # ── English (default) ──
    if ratio < 0.6:
        score -= 0.4          # suspiciously short → likely truncation
    elif ratio < 1.0:
        score -= 0.15
    elif ratio > 5.0:
        score -= 0.3          # ramble / meta-commentary
    elif ratio > 3.5:
        score -= 0.1

    if dev > 0.30:
        score -= 0.5          # mostly untranslated
    elif dev > 0.05:
        score -= 0.2

    n_slash = t.count(" / ")
    words = max(1, len(t.split()))
    slash_density = n_slash / words
    if slash_density > 0.08:
        score -= 0.2          # heavy pāda-literalism (v1 style artifact)
    elif slash_density > 0.04:
        score -= 0.1

    if not LATIN_RE.search(t):
        score -= 0.5          # no English letters at all

    return round(max(0.0, min(1.0, score)), 3)
