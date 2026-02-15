#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re, unicodedata

# zero-widths and odd spaces
ZW = "".join(["\u200B","\u200C","\u200D","\uFEFF","\u2060"])
ZW_RE = re.compile(f"[{re.escape(ZW)}]")
SPACE_RE = re.compile(r"[ \t\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+")

# punctuation (escaped codepoints only)
QUOTE_RE = re.compile(r"[\u201C\u201D\u201E\u201F\u00AB\u00BB\u2039\u203A\"\u2033\u2036]")
APOS_RE  = re.compile(r"[\u2018\u2019\u201A\u201B\u00B4\u0060\u2032\u2035]")
DASH_RE  = re.compile(r"[\u2013\u2014\u2012\u2015]+")
SOFT_HYPHEN_RE = re.compile(r"\u00AD")
HYPHEN_BREAK_RE = re.compile(r"-\s*\n\s*")

DANDA_RE = re.compile(r"[\u0964|]")       # danda or stray pipe -> "."
DOUBLE_DANDA_RE = re.compile(r"[\u0965]") # double danda -> "."

def _norm_common(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = SOFT_HYPHEN_RE.sub("", s)
    s = ZW_RE.sub("", s)
    s = s.replace("\r\n","\n").replace("\r","\n")
    s = HYPHEN_BREAK_RE.sub("", s)
    s = QUOTE_RE.sub('"', s); s = APOS_RE.sub("'", s)
    s = DASH_RE.sub("-", s)
    s = SPACE_RE.sub(" ", s)
    return s.strip()

def normalize_sanskrit(s: str) -> str:
    s = _norm_common(s)
    s = DOUBLE_DANDA_RE.sub(".", s)
    s = DANDA_RE.sub(".", s)
    return s

def normalize_english(s: str) -> str:
    return _norm_common(s)

