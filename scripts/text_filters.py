#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re

DEV_RE = re.compile(r"[\u0900-\u097F]")          # Devanagari
ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—–\*'\"`~^=]+$")
MQQ_RE = re.compile(r"^[\"']{1,4}$")

JUNK_PHRASES = tuple(s.lower() for s in [
    "i am not able to provide a translation",
    "i am not able to translate this snippet",
    "the translation is unclear",
    "does not form a coherent",
    "appears to be a mix of",
    "please provide a complete and coherent snippet",
    "not enough context to translate",
    "unable to translate",
    "garbled",
])

def frac_devanagari(s: str) -> float:
    if not s: return 0.0
    d = len(DEV_RE.findall(s))
    return d / max(1, len(s))

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

def is_noise(s: str) -> bool:
    if not s: return True
    t = s.strip()
    if not t: return True
    if ONLY_PUNCT_RE.match(t): return True
    if MQQ_RE.match(t): return True
    return False

def is_translation_boilerplate(en: str) -> bool:
    if not en: return True
    t = en.strip().lower()
    if not t: return True
    if ONLY_PUNCT_RE.match(t): return True
    if MQQ_RE.match(t): return True
    return any(x in t for x in JUNK_PHRASES)

def should_translate(s: str, *, min_dev: float = 0.08) -> bool:
    if is_noise(s): return False
    if looks_like_heading(s): return False
    if looks_like_table_fragment(s): return False
    return frac_devanagari(s) >= min_dev

def clean_for_mt(s: str) -> str:
    s = re.sub(r"^\s*[\-•*]\s+", "", s)
    s = re.sub(r"^\s*Page\s+\d+\s*$", "", s, flags=re.I)
    return s.strip()
