#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iast_utils.py — Devanagari ↔ IAST transliteration helpers.

Uses indic_transliteration (already in requirements.txt).
Falls back gracefully if library not available.
"""
from __future__ import annotations
import re

_LIB_OK = False

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    _LIB_OK = True
except ImportError:
    pass


def devanagari_to_iast(text: str) -> str:
    """Transliterate Devanagari Sanskrit to IAST romanization.
    
    Returns empty string if input has no Devanagari or library unavailable.
    Non-Devanagari portions (English words, punctuation, verse numbers) are kept as-is.
    """
    if not text or not text.strip():
        return ""
    if not _LIB_OK:
        return ""   # library not available — caller should handle gracefully

    try:
        return transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
    except Exception as e:
        # Partial failure — return empty rather than garble
        return ""


def iast_to_devanagari(text: str) -> str:
    """Transliterate IAST to Devanagari."""
    if not text or not _LIB_OK:
        return ""
    try:
        return transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
    except Exception:
        return ""


def normalize_iast(text: str) -> str:
    """Normalize IAST string: standardize diacritics, lowercase proper names."""
    if not text:
        return ""
    # Normalize combining characters
    import unicodedata
    return unicodedata.normalize("NFC", text)


def extract_proper_nouns_iast(text: str, iast: str) -> list[dict]:
    """Extract proper nouns from IAST text (heuristic: capitalized words after transliteration).
    
    Returns list of {devanagari, iast, start, end}.
    """
    if not iast:
        return []
    # In IAST, proper nouns typically start with uppercase
    results = []
    for m in re.finditer(r"\b([A-ZĀĪŪṚṜḶṄÑṬḌṆŚṢḤṂ][a-zāīūṛṝḷṅñṭḍṇśṣḥṃ]+)", iast):
        results.append({
            "iast": m.group(1),
            "start": m.start(),
            "end": m.end(),
        })
    return results


def is_library_available() -> bool:
    return _LIB_OK
