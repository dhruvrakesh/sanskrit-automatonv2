#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_text.py — Sanskrit-aware text normalization.

CRITICAL: dandas (। ॥) are PRESERVED as verse boundary markers.
They are only whitespace-normalized, never converted to periods.
"""
from __future__ import annotations
import re, unicodedata

# ── Zero-width / invisible chars ─────────────────────────────────────────────
ZW = "".join(["\u200B","\u200C","\u200D","\uFEFF","\u2060"])
ZW_RE = re.compile(f"[{re.escape(ZW)}]")
SPACE_RE = re.compile(r"[ \t\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+")

# ── Punctuation normalization ─────────────────────────────────────────────────
QUOTE_RE = re.compile(r"[\u201C\u201D\u201E\u201F\u00AB\u00BB\u2039\u203A\"\u2033\u2036]")
APOS_RE  = re.compile(r"[\u2018\u2019\u201A\u201B\u00B4\u0060\u2032\u2035]")
DASH_RE  = re.compile(r"[\u2013\u2014\u2012\u2015]+")
SOFT_HYPHEN_RE  = re.compile(r"\u00AD")
HYPHEN_BREAK_RE = re.compile(r"-\s*\n\s*")

# ── Sanskrit danda markers — PRESERVE, only normalize whitespace around them ──
# U+0964 = ।  (danda / half-verse)
# U+0965 = ॥  (double danda / full verse)
# Normalize spacing: ensure exactly one space before/after each danda
# DO NOT convert to periods — dandas are the primary verse boundary markers
DANDA_SPACE_RE        = re.compile(r"\s*([\u0964\u0965])\s*")  # ।  or  ॥
STRAY_PIPE_RE         = re.compile(r"(?<!\|)\|(?!\|)")          # lone | → ।

# ── Verse number pattern (e.g. "॥ 12 ॥" or "।। 1.2 ।।") ──────────────────
# These are kept intact; the segmenter will extract numbers from them.

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
    """Normalize Sanskrit text. PRESERVES dandas (। ॥) as verse markers."""
    s = _norm_common(s)
    # Normalize lone pipe | → danda ।  (OCR sometimes substitutes)
    s = STRAY_PIPE_RE.sub("।", s)
    # Normalize whitespace around dandas (one space before, one after)
    s = DANDA_SPACE_RE.sub(r" \1 ", s)
    # Clean up any double spaces introduced
    s = re.sub(r"  +", " ", s).strip()
    return s

def normalize_english(s: str) -> str:
    return _norm_common(s)

# ── Verse utility helpers (used by segment_verses.py) ────────────────────────

DANDA_RE        = re.compile(r"\u0964")   # ।
DOUBLE_DANDA_RE = re.compile(r"\u0965")   # ॥

def count_dandas(s: str) -> tuple[int, int]:
    """Return (single_dandas, double_dandas) in string."""
    return len(DANDA_RE.findall(s)), len(DOUBLE_DANDA_RE.findall(s))

def frac_devanagari(s: str) -> float:
    """Fraction of characters in Devanagari Unicode block (U+0900–U+097F)."""
    if not s: return 0.0
    dev = sum(1 for c in s if "\u0900" <= c <= "\u097F")
    return dev / max(1, len(s))

def split_on_double_danda(s: str) -> list[str]:
    """Split text at ॥ markers, keeping the marker with its verse."""
    parts = re.split(r"(\u0965)", s)
    verses = []
    current = ""
    for part in parts:
        if part == "\u0965":
            current += part
            verses.append(current.strip())
            current = ""
        else:
            current += part
    if current.strip():
        verses.append(current.strip())
    return [v for v in verses if v]
