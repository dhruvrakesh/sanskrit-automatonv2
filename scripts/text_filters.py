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
ONLY_PUNCT_RE = re.compile(r"^[\W_·•\-—–\*'\"` ~^=।॥]+$")
MQQ_RE = re.compile(r"^[\"']{1,4}$")
LATIN_RE = re.compile(r"[A-Za-z]")

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


# ── Phase Q: translation QA (heuristic, no API calls) ────────────────────────

_GLOSS_PAIR_RE = re.compile(r"^\s*([^|/\n]{2,60})\s*\|\s*([^|/\n]{2,60})\s*$")

def score_translation_quality(src: str, translation: str) -> float:
    """Heuristic QA score 0.0–1.0 for a stored translation against its source.

    Free — no API calls. Deductive scoring from 1.0:
      hard zeros : empty / [ILLEGIBLE] / model boilerplate
      length band: translation-chars / source-chars expected ~1.0–3.5 for
                   Devanagari→English; far outside → truncation or ramble
      residue    : Devanagari left in the output (untranslated fragments)
      gloss pair : "X | X" repeated-gloss signature (the nirukta failure mode)
      pāda slash : high " / " density mid-sentence (v1 pāda-literalism
                   artifact — flags style-stale rows for prompt-v2 upgrade)
      englishness: output must contain Latin letters at all

    Calibration notes (2026-07-20): thresholds set from observed MBh01 v1
    output and nirukta gloss failures. Tune against Q4 judge scores over time.
    """
    if not translation:
        return 0.0
    t = translation.strip()
    if not t or t == "[ILLEGIBLE]":
        return 0.0
    if is_translation_boilerplate(t):
        return 0.0

    score = 1.0
    src_len = max(1, len((src or "").strip()))
    ratio = len(t) / src_len

    if ratio < 0.6:
        score -= 0.4          # suspiciously short → likely truncation
    elif ratio < 1.0:
        score -= 0.15
    elif ratio > 5.0:
        score -= 0.3          # ramble / meta-commentary
    elif ratio > 3.5:
        score -= 0.1

    dev = frac_devanagari(t)
    if dev > 0.30:
        score -= 0.5          # mostly untranslated
    elif dev > 0.05:
        score -= 0.2

    m = _GLOSS_PAIR_RE.match(t)
    if m and m.group(1).strip().lower() == m.group(2).strip().lower():
        score -= 0.6          # "Ornament | Ornament"

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
