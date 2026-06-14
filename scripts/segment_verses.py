#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
segment_verses.py — Sanskrit-aware within-page verse segmentation.

Splits a raw OCR page blob into individual ślokas/verses/passages,
each with structural metadata: verse_ref, chapter, text_type, chandas,
padas, quality_score.

This replaces the old approach of treating one page = one DB passage.
After segmentation, each śloka is stored as its own row in passages.

Segmentation strategy (priority order):
1. Double-danda split (॥) — primary verse boundary
2. Verse number extraction from OCR text
3. Adhyāya/chapter header detection
4. Pada-aware merging (join orphaned half-verses)
5. Quality scoring and text_type tagging
6. Prose fallback if no dandas found

Usage (standalone test):
  python scripts/segment_verses.py "Sanskrit text with ॥ verse ॥ markers"
"""
from __future__ import annotations
import re, sys
from dataclasses import dataclass, field
from typing import Optional

# ── Patterns ─────────────────────────────────────────────────────────────────

# Devanagari digits
DEV_DIGIT = "[\u0966-\u096F]"   # ०–९
ARABIC_DIGIT = r"\d"

# Verse number patterns: "१२॥" "12॥" "॥ 12 ॥" "।। 12 ।।" "15." at line end
VERSE_NUM_INLINE_RE = re.compile(
    rf"[।॥\s]*({DEV_DIGIT}{{1,3}}|{ARABIC_DIGIT}{{1,3}})[।॥\s]*$",
    re.UNICODE
)
# Verse ref like "1.2.3" or "12.5"
VERSE_REF_DOT_RE = re.compile(
    rf"[।॥\s]*({DEV_DIGIT}{{1,3}}|{ARABIC_DIGIT}{{1,3}})"
    rf"\.({DEV_DIGIT}{{1,3}}|{ARABIC_DIGIT}{{1,3}})"
    rf"(?:\.({DEV_DIGIT}{{1,3}}|{ARABIC_DIGIT}{{1,3}}))?"
    r"[।॥\s]*$",
    re.UNICODE
)
# Adhyāya / chapter header patterns
CHAPTER_HDR_RE = re.compile(
    r"(?:अध्याय[ःस]?|अध्यायः|पर्व[ण]?|काण्ड[ः]?|सर्ग[ः]?|स्कन्ध[ः]?|प्रकरण[ः]?)"
    r"\s*(?:[\u0966-\u096F\d]+)?",
    re.UNICODE
)
# Colophon patterns: "इति ... समाप्तम्" "इति ... पर्व" "अध्याय: समाप्तः"
COLOPHON_RE = re.compile(
    r"इति\s+.{5,80}(?:समाप्त[ःम्]?|पर्व|अध्याय|समाप्[तिः])",
    re.UNICODE
)
# Commentary/tika signals
TIKA_SIGNALS = re.compile(
    r"(?:तात्पर्यम्|विवरण[मं]|व्याख्या|भाष्य[मं]|टीका|अर्थः|अत्र|यथा\s+\-)",
    re.UNICODE
)

# Devanagari block
DEV_RE = re.compile(r"[\u0900-\u097F]")


@dataclass
class Verse:
    text: str
    verse_ref: Optional[str]    = None   # "1.2.3" | "12" | None
    chapter:   Optional[str]    = None   # chapter/adhyāya id
    text_type: str              = "mula" # mula|tika|prose|colophon|noise|frontmatter
    chandas:   Optional[str]    = None   # anustubh|tristubh|etc.
    padas:     int              = 0      # 0=unknown, 2=half, 4=full
    quality_score: float        = 0.0   # 0.0–1.0


# ── Devanagari helpers ────────────────────────────────────────────────────────

def _frac_dev(s: str) -> float:
    if not s: return 0.0
    return len(DEV_RE.findall(s)) / max(1, len(s))

def _dev_numeral_to_arabic(s: str) -> str:
    """Convert Devanagari numerals ०–९ to 0–9."""
    table = str.maketrans("०१२३४५६७८९", "0123456789")
    return s.translate(table)

def _quality(text: str) -> float:
    """0.0–1.0 quality score: 60% Devanagari density + 40% danda presence."""
    dev = _frac_dev(text)
    single = text.count("।"); double = text.count("॥")
    danda_score = min(1.0, (single + double * 2) / 5.0)
    return round(0.6 * dev + 0.4 * danda_score, 3)


# ── Chandas detection ─────────────────────────────────────────────────────────

def _count_syllables_approx(iast_or_devanagari: str) -> int:
    """Approximate syllable count from IAST or Devanagari text.
    
    Uses vowel counting as a proxy for syllable count.
    Sanskrit: each vowel = one syllable (approximate for non-compound texts).
    """
    # Count Devanagari vowel matras + independent vowels
    # Independent vowels: अ आ इ ई उ ऊ ऋ ॠ ए ऐ ओ औ
    # Vowel matras: ा ि ी ु ू ृ ॄ े ै ो ौ
    dev_vowels = re.compile(
        r"[\u0904-\u0914\u093E-\u094C\u0960-\u0963]",  # matras + independent vowels
        re.UNICODE
    )
    # Also count implied 'a' after consonants (every consonant not followed by matra or halant)
    dev_consonants = re.compile(r"[\u0915-\u0939\u0958-\u095F]", re.UNICODE)
    matra_or_halant = re.compile(r"[\u093E-\u094D]", re.UNICODE)

    text = iast_or_devanagari
    vowel_count = len(dev_vowels.findall(text))
    # Count consonants that have implicit 'a' (not followed by matra/halant)
    pos = 0
    implicit_a = 0
    chars = list(text)
    for i, c in enumerate(chars):
        if dev_consonants.match(c):
            # Check if next char is a matra or halant
            next_c = chars[i+1] if i+1 < len(chars) else ""
            if not matra_or_halant.match(next_c):
                implicit_a += 1

    return vowel_count + implicit_a

def _detect_chandas(text: str) -> Optional[str]:
    """Detect Sanskrit meter (chandas) from verse text.
    
    Returns meter name or None if undetected.
    Uses syllable counting per pāda (line).
    
    Common meters:
    - Anuṣṭubh (Śloka): 4 pādas × 8 syllables = 32 total
    - Triṣṭubh: 4 pādas × 11 syllables = 44 total
    - Jagatī: 4 pādas × 12 syllables = 48 total
    - Āryā: variable, based on morae
    - Śārdūlavikrīḍita: 4 × 19 syllables
    - Vasantatilakā: 4 × 14 syllables
    - Mālinī: 4 × 15 syllables
    - Mandākrāntā: 4 × 17 syllables
    """
    syllables = _count_syllables_approx(text)
    if syllables == 0:
        return None

    # Also try library detection if available
    try:
        from chandas import identify_metre  # type: ignore
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            result = identify_metre(lines)
            if result and result != "Unknown":
                return result
    except ImportError:
        pass  # chandas library not installed — use rule-based
    except Exception:
        pass

    # Rule-based by syllable count
    # Anuṣṭubh: 32 syllables (most common — Mahābhārata, Rāmāyaṇa, Purāṇas)
    if 28 <= syllables <= 36:
        return "anustubh"
    # Triṣṭubh: 44 syllables (Ṛgveda)
    if 40 <= syllables <= 48:
        return "tristubh"
    # Jagatī: 48 syllables
    if 44 <= syllables <= 52:
        return "jagati"
    # Śārdūlavikrīḍita: 76 syllables (4×19)
    if 70 <= syllables <= 82:
        return "sardula_vikridata"
    # Mālinī: 60 syllables (4×15)
    if 56 <= syllables <= 64:
        return "malini"
    # Vasantatilakā: 56 syllables (4×14)
    if 52 <= syllables <= 60:
        return "vasantatilaka"

    return None  # unidentified


# ── Verse number extraction ───────────────────────────────────────────────────

def _extract_verse_ref(text: str) -> tuple[Optional[str], str]:
    """Extract verse reference from end of text segment.
    
    Returns (verse_ref, cleaned_text).
    verse_ref: "1.2.3" or "12" or None
    """
    stripped = text.rstrip()

    # Try dotted reference first (e.g. "1.2.3॥" or "12.5")
    m = VERSE_REF_DOT_RE.search(stripped)
    if m:
        parts = [_dev_numeral_to_arabic(p) for p in m.groups() if p]
        ref = ".".join(parts)
        cleaned = stripped[:m.start()].rstrip()
        return ref, cleaned

    # Simple verse number at end
    m = VERSE_NUM_INLINE_RE.search(stripped)
    if m:
        num = _dev_numeral_to_arabic(m.group(1))
        cleaned = stripped[:m.start()].rstrip()
        return num, cleaned

    return None, text


# ── Text type detection ───────────────────────────────────────────────────────

def _detect_text_type(text: str) -> str:
    """Classify text segment as: mula|tika|prose|colophon|noise|frontmatter."""
    if not text or not text.strip():
        return "noise"

    dev_frac = _frac_dev(text)

    # Noise: < 5% Devanagari and < 20 chars
    if dev_frac < 0.03 and len(text.strip()) < 30:
        return "noise"

    # Frontmatter: English-dominant, academic markers
    if dev_frac < 0.05:
        lower = text.lower()
        for sig in ["table of contents", "preface", "foreword", "introduction",
                    "bibliography", "isbn", "copyright", "printed in", "published by",
                    "transliteration", "abbreviations"]:
            if sig in lower:
                return "frontmatter"
        return "prose"

    # Colophon: "इति ... समाप्तम्"
    if COLOPHON_RE.search(text):
        return "colophon"

    # Chapter header: standalone line with adhyaya marker
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) <= 2 and CHAPTER_HDR_RE.search(text):
        return "colophon"

    # Tika/commentary: low Devanagari density with commentary signals
    if dev_frac < 0.40 and TIKA_SIGNALS.search(text):
        return "tika"

    # Prose: no dandas, moderate Devanagari
    if "।" not in text and "॥" not in text and dev_frac < 0.60:
        return "prose"

    # Default: mūla (root Sanskrit verse)
    return "mula"


# ── Chapter header extraction ─────────────────────────────────────────────────

def _extract_chapter(text: str) -> Optional[str]:
    """Extract chapter/adhyāya number/name from text."""
    m = CHAPTER_HDR_RE.search(text)
    if not m:
        return None
    # Try to find a number after the header word
    after = text[m.end():].strip()
    num_m = re.match(r"([\u0966-\u096F\d]+)", after)
    if num_m:
        return _dev_numeral_to_arabic(num_m.group(1))
    return m.group(0).strip()


# ── Main segmentation function ────────────────────────────────────────────────

def segment_page(raw_text: str) -> list[Verse]:
    """Segment a raw OCR page blob into individual verses/passages.
    
    Args:
        raw_text: Full OCR text of one PDF page (dandas preserved as ।॥)
    
    Returns:
        List of Verse objects, each representing one śloka or passage.
    """
    if not raw_text or not raw_text.strip():
        return []

    # ── Step 1: Detect current chapter (if page starts with header) ──────────
    current_chapter = _extract_chapter(raw_text)

    # ── Step 2: Split on double-danda ॥ (primary verse boundary) ────────────
    # Strategy: split at ॥ keeping the marker with the verse
    raw_segments: list[str] = []

    if "॥" in raw_text:
        parts = re.split(r"(॥)", raw_text)
        current = ""
        for part in parts:
            if part == "॥":
                current += "॥"
                if current.strip():
                    raw_segments.append(current.strip())
                current = ""
            else:
                current += part
        if current.strip():
            raw_segments.append(current.strip())
    elif "।" in raw_text:
        # No double-dandas: split at single dandas (half-verses → try to pair)
        halves = re.split(r"(।)", raw_text)
        current = ""
        pairs: list[str] = []
        for part in halves:
            if part == "।":
                current += "।"
                pairs.append(current.strip())
                current = ""
            else:
                current += part
        if current.strip():
            pairs.append(current.strip())
        # Pair up consecutive half-verses into full shlokas
        i = 0
        while i < len(pairs):
            if i + 1 < len(pairs) and pairs[i] and pairs[i+1]:
                raw_segments.append(pairs[i] + "\n" + pairs[i+1])
                i += 2
            else:
                raw_segments.append(pairs[i])
                i += 1
    else:
        # No dandas at all — treat whole page as prose
        raw_segments = [raw_text.strip()]

    # ── Step 3: Build Verse objects with metadata ────────────────────────────
    verses: list[Verse] = []
    running_chapter = current_chapter

    for seg in raw_segments:
        seg = seg.strip()
        if not seg:
            continue

        # Extract chapter if segment contains header
        seg_chapter = _extract_chapter(seg)
        if seg_chapter:
            running_chapter = seg_chapter

        # Extract verse ref from end of segment
        verse_ref, clean_text = _extract_verse_ref(seg)
        clean_text = clean_text.strip()

        if not clean_text:
            continue

        # Detect text type
        text_type = _detect_text_type(clean_text)

        # Detect chandas (meter)
        chandas = None
        padas = 0
        if text_type in ("mula",):
            chandas = _detect_chandas(clean_text)
            # Count padas: each ।  = one pada boundary; ॥ = verse end
            single_d = clean_text.count("।")
            double_d = clean_text.count("॥")
            padas = single_d + double_d * 2  # rough estimate

        quality = _quality(clean_text)

        v = Verse(
            text=clean_text,
            verse_ref=verse_ref,
            chapter=running_chapter or seg_chapter,
            text_type=text_type,
            chandas=chandas,
            padas=padas,
            quality_score=quality,
        )
        verses.append(v)

    # ── Step 4: Filter pure noise (< 3% Devanagari, < 10 chars) ─────────────
    verses = [
        v for v in verses
        if v.text_type != "noise" or len(v.text) > 30
    ]

    return verses


def segment_page_to_dicts(raw_text: str) -> list[dict]:
    """Segment and return as list of dicts (for JSON serialization)."""
    return [
        {
            "text":          v.text,
            "verse_ref":     v.verse_ref,
            "chapter":       v.chapter,
            "text_type":     v.text_type,
            "chandas":       v.chandas,
            "padas":         v.padas,
            "quality_score": v.quality_score,
        }
        for v in segment_page(raw_text)
    ]


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        # Demo text
        text = """
        धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।
        मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥
        दृष्ट्वा तु पाण्डवानीकं व्यूढं दुर्योधनस्तदा ।
        आचार्यमुपसङ्गम्य राजा वचनमब्रवीत् ॥ २ ॥
        """
    print("=== INPUT ===")
    print(text)
    print("\n=== SEGMENTS ===")
    results = segment_page_to_dicts(text)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nTotal verses: {len(results)}")
