#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
text_filters.py — Pre/post translation filters for Sanskrit passages.
"""
from __future__ import annotations
import re

DEV_RE = re.compile(r"[\u0900-\u097F]")          # Devanagari block
ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—–\*'\"` ~^=\u0964\u0965]+$")
MQQ_RE = re.compile(r"^[\"']{1,4}$")

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

def looks_like_frontmatter(s: str) -> bool:
    """Detect English-only preface/intro/TOC pages that should not be translated."""
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

def is_translation_boilerplate(en: str) -> bool:
    """Return True if the translation string is a model refusal or garbage."""
    if not en: return True
    t = en.strip().lower()
    if not t: return True
    if ONLY_PUNCT_RE.match(t): return True
    if MQQ_RE.match(t): return True
    if len(t) < 4: return True
    return any(x in t for x in JUNK_PHRASES)

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
