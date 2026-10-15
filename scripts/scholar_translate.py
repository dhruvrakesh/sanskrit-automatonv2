#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14, SCHOLAR_V21_2026_10_14,
COST_TRUTH_2026_10_15, CLAUDE_ENGINE_2026_10_15, PILOT_FIX_2026_10_15,
AUDIT_2026_10_15, RUN_FIX_2026_10_15

A scholarly English beside the working one: verse by verse, with the context, a glossary that grows, notes, a critic
and revisions, and an independent judge. The working English (passages.translation) is never touched.

SCHOLAR_V2_2026_10_14 (after the pilot of 14 Oct: MBh01 1.1.0-1.1.24, $0.238, 23 passed, 1 flagged):
  - a Sanskrit sentence over several verses is translated whole (--groups, on): one call marks where each sentence
    ends (scholar-groups-v1, 40 verses a call); the sentence is drafted, read by the critic and judged as one passage,
    and stored verse by verse in its segments (group_ref, group_translation, moved). Verse by verse, 1.1.15-1.1.19 (one
    sentence) read as fragments;
  - a second judge with the context (--compare, on; scholar-compare-v1, gemini-2.5-pro): the scholarly and the working
    English side by side, in an order it is not told, the errors of each and the more faithful. The flash judge reads
    a verse alone and gave the working English of 1.1.5 (the narrator called by his father's name) 5 of 5;
  - the notes: three a verse at most, none for a common word, the Sanskrit spelt as the IAST is; a speaker's line
    opens the translation without its own " //" (scholar-v2, scholar-critic-v2);
  - the price measured: the scholar-v2 rows' mean after 10, before that scholar-v1's with a compare at half of it;
  - render_prose (/scholar/<doc>/prose; --report writes it too): the text read as prose, chapter by chapter, the notes
    at each chapter's end.

SCHOLAR_V21_2026_10_14 (after scholar-v2's pilot of 14 Oct, 21:13: 15 passed, 5 flagged, 4 failed, $0.256):
  - a sentence's passage is kept as the draft wrote it, in the order English needs (scholar-v2.1); its segments say
    which words render which verse. scholar-v2 joined the segments, which hold the Sanskrit's order, so 1.1.15-1.1.19
    read as fragments again and the critic flagged it after two revisions;
  - an answer cut off at the token limit is asked again with room, even when some text came back; a draft that is still
    not JSON is asked once more; a sentence whose draft fails is translated verse by verse (1.1.20-1.1.23 failed whole);
    a failure says how the answer ended;
  - priced by the scholar-v2 rows until 10 of scholar-v2.1 are measured;
  - the pages order the rows by their passage's place now (a re-ingest moves it), and a sentence whose passage is not
    its segments joined is shown whole after its verse range, the segments under the fold.

COST_TRUTH_2026_10_15: the meter now counts gemini-2.5-pro's thinking (billed as output; the SDK here does not name
it, and the 14 Oct runs were metered for their visible output only). The price counts only rows metered so (from
METERED_SINCE); before 10 of them, the prior of 3,000 output tokens a call. A job that only adds working English does
not stop a run.

CLAUDE_ENGINE_2026_10_15: Claude as the translator and the critic (--engine anthropic:claude-sonnet-5-5, or
anthropic:claude-opus-5-5@medium: the effort after the "@"), by scripts/claude_engine.py: metered in usage_log as
Anthropic bills it, paid from the API credit and capped by it, not by the spend cap. The judge stays judge-v1
(gemini-2.5-flash) and the second judge gemini-2.5-pro (--compare-engine): a Claude English is never judged by Claude.
A text of the Agamas and Tantras gets a rule more (agama-1): a mantra or a seed-syllable stays in IAST, a Latin digit in
a word is the edition's footnote number; the edition's apparatus on the page goes with the verse. --held-ok translates a
text held from the site while its working English is redone (nothing is written to the site or to its passages).
--no-glossary-adds: a benchmark run. scripts/scholar_duel.py reads the engines side by side, blind.

PILOT_FIX_2026_10_15: an OCR reading's verse_ref is not a reference (page.idx instead); --fill-engine goes on where a
run of this engine stopped, with only its own rows as done and as context; --compare-every N puts the second judge on
one sentence in N.

AUDIT_2026_10_15: --audit-every N: in a Claude run, Gemini's critic (gemini-2.5-pro) reads the last version of one
sentence in N; its reading decides the status (a person reads what it flags). --status: what a text has, per engine
(free, read-only).

RUN_FIX_2026_10_15: an answer's first whole JSON object is read whatever follows it; a Claude critic not answering in
JSON is asked once more, and an answer still unread is kept (data/scholar/unparsed_<doc>.jsonl); a dashboard pipeline
past its ingest (translating or exporting) does not stop a run.

Why: the working English was made in one pass by gemini-2.5-flash, with the five verses before it as its only
context: no glossary kept between verses, no notes, no review. A judge reads a sample of it. That is a draft. The
register wanted here is that of an unabridged translation from a critical edition (as Bibek Debroy's Mahabharata is
from the BORI Critical Edition): every word rendered, names and terms kept and explained, nothing added.

How, for each verse (gemini-2.5-pro unless --engine says otherwise; JSON out):
  1. the draft (scholar-v1): the verse, its IAST, the 6 verses before it (Sanskrit and English: the scholarly English
     where there is one, the working English otherwise), the 2 after it (Sanskrit), the text, chapter and verse, and the
     glossary of the names and terms it meets (the entities found in these verses, the glossary entries earlier verses
     added, and a person's corrections, which win). Out: translation, notes, new glossary entries, doubts;
  2. the critic (scholar-critic-v1), temperature 0: fidelity, completeness, the issues word by word, accept or revise;
  3. a revision when the critic asks for one, and the critic again, up to --rounds (2) revisions;
  4. the judge (judge_sample.py's judge-v1, gemini-2.5-flash) scores the scholarly English and the working English of
     the same verse, so the two can be compared.
  Passed: the critic accepts the last version and the judge gives fidelity and fluency 4 or more. Flagged otherwise
  (a person reads it). A source doubt: the critic says the Sanskrit itself looks corrupt or misread (another edition
  or a better scan is wanted for that verse).

What is not sent (counted, listed): noise and front matter; fewer than 8 Devanagari signs; OCR debris (Latin letters in
the Devanagari: mend the reading first); a reading below --min-quality; numbers among the words (an index, errata, an
apparatus or a notation, not verse); Hindi prose (a bilingual edition's own Hindi). A text withdrawn, set aside or in
repair (data/source_verdicts.jsonl) is refused whole.

Stored: scholar_translations, one row a verse a version, never overwritten; src_hash says which Sanskrit it was made
from, so a later change of the reading makes the row stale, not wrong. scholar_glossary: the entries the passed verses
added, and a person's. Spend: usage_log (kind "scholar" for the translator and the critic, "judge" for the judge), so
the spend cap counts it; redeem.py's ledger counts kind "translation" only.

A dry run by default (free, read-only): what it would send, what it leaves out, and what it costs. --yes runs it,
capped by --max-usd (it can pass the cap by one call at most), by the spend cap, and it stops while the dashboard runs
a job that changes this text's Sanskrit or English (a Hindi job does not stop it).

  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24                 the dry run, free
  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --show-prompt   the first verse's prompt
  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --yes --max-usd 1.50
  python scripts\\scholar_translate.py --doc MBh01 --report       exports\\scholar_MBh01.html (free)
  python scripts\\scholar_translate.py --doc MBh01 --review 1.1.8,1.1.9 --verdict accept --by Dhruv
  python scripts\\scholar_translate.py --doc MBh01 --term Janamejaya --rendering Janamejaya --kind person
The dashboard shows them read-only: http://127.0.0.1:5057/scholar
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

MARK = "SCHOLAR_2026_10_14"
MARK2 = "SCHOLAR_V2_2026_10_14"
MARK3 = "SCHOLAR_V21_2026_10_14"
MARK4 = "CLAUDE_ENGINE_2026_10_15"
PROMPT_VERSION = "scholar-v2.1"        # SCHOLAR_V21_2026_10_14 (scholar-v2: 14 Oct 21:13; scholar-v1: the pilot of 18:25)
CRITIC_VERSION = "scholar-critic-v2"
GROUPS_VERSION = "scholar-groups-v1"
COMPARE_VERSION = "scholar-compare-v1"
GROUP_MAX = 6          # verses in one sentence at most
GROUP_WINDOW = 40      # verses one groups call reads
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
ENGINE = "gemini:gemini-2.5-pro"
JUDGE = "gemini:gemini-2.5-flash"
JUDGE_PROMPT = "judge-v1"
CONTEXT_BEFORE = 6
CONTEXT_AFTER = 2
GLOSSARY_MAX = 40
OUT_TOKENS_PRIOR = 3000      # a pro call's output with its thinking, before 10 verses are measured (COST_TRUTH_2026_10_15:
                             # was 1500; on 14 Oct a group's draft spent 8,192 thinking tokens and was cut off)
METERED_SINCE = "2026-10-15"   # COST_TRUTH_2026_10_15: rows made before it were metered without the thinking
JUDGE_COST_PRIOR = 0.0002    # $ a judged verse (12 Oct: 200 calls, $0.0377)
MEASURED_AFTER = 10
# The dashboard's jobs that do not change a text's Sanskrit or English: they do not stop a run
QUIET_KINDS = ("translate_hi", "ocr", "judge", "judge_all", "benchmark", "benchmark_all", "redeem_all", "path_all",
               "export", "pdf", "booksmith",
               "translate", "translate_both", "translate_one")   # COST_TRUTH_2026_10_15: they add working English
# CLAUDE_ENGINE_2026_10_15
COMPARE_ENGINE = "gemini:gemini-2.5-pro"   # the second judge of a Claude English: never Claude
CLAUDE_MAX_TOKENS = 16000                  # the thinking and the answer; twice it when an answer is cut off
AGAMA_VERSION = "agama-1"
AGAMA = re.compile(r"(?i)agam|tantr|pancar|bhairav")   # a category or a name of the Agamas and Tantras
TITLES = {
    "HAYASHIRSHA_PANCARATRA": "the Haya\u015b\u012br\u1e63a Pa\u00f1car\u0101tra (\u0100dik\u0101\u1e47\u1e0da), a "
                              "P\u0101\u00f1car\u0101tra \u0100gama of the Vai\u1e63\u1e47avas",
    "Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi":
        "the K\u0101ra\u1e47\u0101gama, Kriy\u0101p\u0101da, a \u015aaiva \u0100gama (edited by R\u0101macandra "
        "P\u0101\u1e47\u1e0deya, \u015aaivabh\u0101rat\u012b \u015aodhaprati\u1e63\u1e6dh\u0101na, V\u0101r\u0101\u1e47as\u012b, 1994)",
    "tantric_texts_series_edited_by_arthur_av":
        "the Tantr\u0101bhidh\u0101na with the B\u012bjanigha\u1e47\u1e6du, B\u012bj\u0101bhidh\u0101na, "
        "Mantr\u0101rth\u0101bhidh\u0101na, Var\u1e47ab\u012bjako\u1e63a and Mudr\u0101nigha\u1e47\u1e6du, lexicons of the "
        "Tantras: the code-names of letters, seed-syllables and gestures (Tantrik Texts, vol. I, Arthur Avalon's series)",
}
APPARATUS_RE = re.compile(r"-[A-Z](?:,\s?[A-Z])*\s?[.;]")   # "7 yat (?)-B,C.": a variant and its manuscripts

DEV = re.compile("[\u0900-\u097f]")
JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")       # = redeem.JUNK, repair_text.JUNK
_DIG = "\u0966-\u096f0-9"
VERSE_NO = re.compile("[\u0964\u0965|]+\\s*[%s.]+\\s*[\u0964\u0965|]+" % _DIG)
SUTRA_NO = re.compile("(?m)^\\s*[%s]+(?:\\.[%s]+)+\\s*" % (_DIG, _DIG))
NUM_TOKEN = re.compile("^[%s.,()\\-]+$" % _DIG)
HAS_DIGIT = re.compile("[%s]" % _DIG)
INDEX_MARKS = ("\u0936\u0941\u0926\u094d\u0927\u093f\u092a\u0924\u094d\u0930",                      # errata
               "\u092a\u0943\u0937\u094d\u0920\u0947 \u092a\u0919\u094d\u0915\u094d\u0924\u094c",        # page, line
               "\u0905\u0936\u0941\u0926\u094d\u0927\u092e\u094d \u0936\u0941\u0926\u094d\u0927\u092e\u094d")  # wrong, right
HINDI_WORDS = frozenset((
    "\u0939\u0948", "\u0939\u0948\u0902", "\u0915\u0947", "\u0915\u0940", "\u0915\u094b", "\u0938\u0947",
    "\u092e\u0947\u0902", "\u0914\u0930", "\u0928\u0939\u0940\u0902", "\u0925\u093e", "\u0925\u0947",
    "\u0939\u094b\u0924\u093e", "\u0939\u094b\u0924\u0940", "\u0915\u0930\u0915\u0947", "\u0915\u093f\u092f\u093e",
    "\u0932\u093f\u092f\u0947", "\u0907\u0938\u0932\u093f\u092f\u0947", "\u0915\u0939\u093e", "\u092f\u0939",
    "\u0935\u0939", "\u091c\u094b"))
# CLAUDE_ENGINE_2026_10_15: words that are Hindi only (lie, chahie, vala, vale, vali, hone, karana, jata, jati, jate, hua,
# hue, hui, iske, uske, iska, uska, apane, sakata, sakate, karen, hoga, hogi, diya, gaye, gayi, bhi, ne, is, thik): the
# Karanagama's Hindi under each verse had two of the old ones only
HINDI_WORDS = HINDI_WORDS | frozenset((
    "\u0932\u093f\u090f", "\u091a\u093e\u0939\u093f\u090f", "\u0935\u093e\u0932\u093e", "\u0935\u093e\u0932\u0947",
    "\u0935\u093e\u0932\u0940", "\u0939\u094b\u0928\u0947", "\u0915\u0930\u0928\u093e", "\u091c\u093e\u0924\u093e",
    "\u091c\u093e\u0924\u0940", "\u091c\u093e\u0924\u0947", "\u0939\u0941\u0906", "\u0939\u0941\u090f",
    "\u0939\u0941\u0908", "\u0907\u0938\u0915\u0947", "\u0909\u0938\u0915\u0947", "\u0907\u0938\u0915\u093e",
    "\u0909\u0938\u0915\u093e", "\u0905\u092a\u0928\u0947", "\u0938\u0915\u0924\u093e", "\u0938\u0915\u0924\u0947",
    "\u0915\u0930\u0947\u0902", "\u0939\u094b\u0917\u093e", "\u0939\u094b\u0917\u0940", "\u0926\u093f\u092f\u093e",
    "\u0917\u092f\u0947", "\u0917\u092f\u0940", "\u092d\u0940", "\u0928\u0947", "\u0907\u0938", "\u0920\u0940\u0915"))
WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")
HELD = {"withdrawn": "withdrawn from the site: a better source first",
        "set_aside": "set aside: a better scan first",
        "in_repair": "in repair: its reading may still change (repair_text.py --release first)"}
HELD_OK = "--held-ok translates it while it is held from the site: nothing is written to the site or to its passages"

SYSTEM_DRAFT = """You are a Sanskritist preparing a scholarly English translation of {title}, for a critical-edition translation series. The register is that of an unabridged translation made from a critical edition, as Bibek Debroy's Mahabharata is from the BORI Critical Edition: complete, faithful to every word, in plain modern English prose, with Sanskrit names and key terms kept and explained in notes. Translate afresh from the Sanskrit given. Never quote or reconstruct any published translation.

Rules:
1. COMPLETENESS. Render every word of THE VERSE TO TRANSLATE: every name, epithet, vocative and number, and every particle that carries meaning. Add nothing that is not in the Sanskrit.
2. FIDELITY. Case relations, voice, tense, number and who does what to whom must match the Sanskrit. Resolve every absolutive and participle to its true agent. A patronymic or an epithet that qualifies a person named in the verse is that same person, not another one: janamejayasya ... p\u0101rik\u1e63itasya is "of Janamejaya, the son of Parik\u1e63it", one man.
3. REGISTER. Plain, dignified modern English prose. No archaism (thee, thou, verily, lo, unto), no paraphrase, no explanation inside the sentence. Leave out purely emphatic particles (eva, hi, vai, tu, ha, khalu) unless the emphasis carries meaning.
4. NAMES. Proper names in IAST, never translated, spelled exactly as the GLOSSARY spells them. A name the glossary does not have: its stem in IAST (Arjuna, not Arjuna\u1e25).
5. EPITHETS. Translate an epithet where its meaning matters to the sentence, or keep it in IAST and explain it in a note: one or the other, consistently, as the glossary has it.
6. TERMS. A technical term English cannot render without loss stays in IAST between asterisks (*dharma*, *tapas*, *yaj\u00f1a*) with a note the first time this text uses it. The glossary lists the terms already explained: do not explain them again.
7. BRACKETS. [Square brackets] only for a word the Sanskrit implies but does not say, needed for the English to parse. Never an explanation in brackets: explanations go in the notes.
8. NOTES. Short, factual notes, only where a reader needs one: an epithet or patronymic, an allusion to a story told elsewhere, a technical or ritual term, a word with two possible readings, a textual problem. At most three a verse. No note for a common word (king, sage, great-souled, lord, best of men), and none that says again what the translation makes plain. Spell every Sanskrit word in a note exactly as the IAST given spells it. Each note: {"anchor": the English word or words it explains, exactly as they stand in your translation, "kind": one of name|epithet|term|allusion|grammar|textual, "note": the note}.
9. DOUBTS. When a word can be read more than one way, or the Sanskrit looks corrupt or misprinted, say so in "doubts": the word, the readings, the one you chose and why. Otherwise leave "doubts" empty.
10. WHAT TO TRANSLATE. Translate only THE VERSE TO TRANSLATE, or THE VERSES TO TRANSLATE when one Sanskrit sentence runs over several verses. The verses before (with an English that may be a working draft, and may be wrong) and after are there only so that you understand: do not translate or repeat them. One verse whose sentence runs on into the next: translate its words as the opening of that sentence. Several verses: write "translation" as one passage of natural English prose in the order English needs (the main clause may come first, as English wants it), and give in "segments", [{"ref": the verse, "english": its part}], one for each verse, in order, the words of your passage that render that verse. The segments need not read as the passage, nor in its order; together they hold all of it. Say in "moved" what English moved, and from which verse. End the passage with " //".
11. GLOSSARY. Propose an entry for each name or term this verse brings in that the glossary does not have: {"term": the IAST stem, "rendering": how the translation writes it, "kind": person|place|people|deity|term|epithet|other, "note": a gloss of a few words}.
12. SPEAKERS. A speaker's line (... uv\u0101ca) opens the translation ("The s\u016bta said:"), and the speech follows it with no " //" after the speaker's line.

Reply with one JSON object and nothing else:
{"translation": "...", "segments": [], "moved": "", "notes": [...], "glossary": [...], "doubts": "..."}
("segments" and "moved" only when several verses are given.)"""

SYSTEM_CRITIC = """You are a senior Sanskritist reviewing one verse, or one sentence that runs over several verses, of a draft scholarly English translation of {title}, as the editor of a critical-edition translation would. Compare the draft with the Sanskrit word by word. The verses before and after are there only to help you understand: judge only THE VERSE (or THE VERSES) TO TRANSLATE. For several verses, judge the passage as a whole, and whether each segment holds its verse's words (or says what moved). Read the notes too: a wrong fact, or a Sanskrit word spelt otherwise than the IAST given, is an issue of type note.

Report:
- "fidelity", 1 to 5: 5 = every word's meaning and every grammatical relation is kept; 3 = the gist is right but a word or a relation is wrong; 1 = wrong.
- "completeness", 1 to 5: 5 = nothing left out and nothing added.
- "issues": each specific problem, as {"type": omission|addition|misreading|grammar|name|term|register|note|source, "where": the Sanskrit word or words, "fix": the corrected English (for a note, the corrected note), "severity": major|minor}. Major: it changes the meaning or loses a word that matters. Minor: wording. Use "source" when the Sanskrit itself looks corrupt, misprinted or misread, with the likely reading in "fix".
- "verdict": "accept" when fidelity and completeness are 4 or 5 and no issue is major; "revise" otherwise.
Be exact and brief. Do not rewrite the whole translation. Do not invent problems: an empty list is right for a good translation.

Reply with one JSON object and nothing else:
{"fidelity": 0, "completeness": 0, "issues": [], "verdict": "accept"}"""

REVISE_ASK = ("Revise the translation. Make each change a finding rightly asks for; where a finding is wrong, keep your "
              "reading and say why in \"doubts\". Keep everything that was right. Reply with the same JSON object.")

# SCHOLAR_V2_2026_10_14: where each Sanskrit sentence ends; and a second judge of both Englishes
SYSTEM_GROUPS = """You are a Sanskritist. Below are consecutive verses of {title}, each with its reference. Say where each Sanskrit sentence ends, so that a translator can render every sentence whole.
Rules: list every reference once, in the order given; a group is the verses of one sentence; most groups are of one verse; at most 6 verses a group; a speaker's line (... uv\u0101ca) belongs to the verse it opens; when unsure, keep verses apart.
Reply with one JSON object and nothing else:
{"groups": [["ref", "ref"], ["ref"]]}"""

SYSTEM_COMPARE = """You are a senior Sanskritist comparing two English translations, A and B, of the same Sanskrit of {title}, for a critical-edition translation series. Judge only against the Sanskrit given; the verses before and after are there to help you see who is who and how the sentence runs. Who made each translation is not said.
For each of A and B: "fidelity", 1 to 5 (5 = every word's meaning and every grammatical relation kept, every person rightly named), and "errors", each {"where": the Sanskrit word or words, "error": what is wrong, "severity": major|minor}. Major: a wrong meaning, a wrong person, a word that matters left out or added. Do not invent errors: an empty list is right for a faithful translation. Then "better": "A", "B" or "equal", and "reason", in a sentence.
Reply with one JSON object and nothing else:
{"A": {"fidelity": 0, "errors": []}, "B": {"fidelity": 0, "errors": []}, "better": "equal", "reason": ""}"""

# CLAUDE_ENGINE_2026_10_15: one place for the system prompts, so that every engine sends the same; and the Agamas'
AGAMA_DRAFT = """13. AGAMA AND TANTRA. This is a text of the \u0100gamas and Tantras. A mantra, a seed-syllable (b\u012bja) or a ritual formula (o\u1e43, hr\u012b\u1e43, hu\u1e43, pha\u1e6d, sv\u0101h\u0101, nama\u1e25) stays in IAST exactly as the text has it and is never translated; what it is for may go in a note. A term of ritual, iconography, architecture or measure (ma\u1e47\u1e0dapa, ku\u1e47\u1e0da, ved\u012b, stha\u1e47\u1e0dila, hasta, a\u1e45gula, ny\u0101sa, mudr\u0101, d\u012bk\u1e63\u0101, p\u012b\u1e6dha) follows Rule 6, and a measure is given as the text gives it. A Latin digit inside or just after a Devanagari word (as in \u0935\u093e24) is the printed edition's footnote number, not the text: leave it out of the translation. A word the reading plainly misprints (a letter misread) is translated as it must be read, and the reading you chose is said in "doubts"."""
AGAMA_JUDGE = """This is a text of the \u0100gamas and Tantras: a mantra, a seed-syllable or a ritual formula kept in IAST and not translated is right, not an issue; a Latin digit inside or just after a Devanagari word (as in \u0935\u093e24) is the printed edition's footnote number, not the text, and its absence from a translation is no issue."""
SYSTEMS = {"draft": SYSTEM_DRAFT, "critic": SYSTEM_CRITIC, "groups": SYSTEM_GROUPS, "compare": SYSTEM_COMPARE}
JUDGING = ("critic", "compare", "duel")
_REPLY = "Reply with one JSON object and nothing else:"


def system_for(kind: str, meta: dict) -> str:
    """The system prompt of a call of this kind for this text: its title in it; for the Agamas and Tantras, rule 13 in the
    draft's and the note in the judging ones, before the reply's shape."""
    s = SYSTEMS.get(kind, SYSTEM_CRITIC).replace("{title}", meta["title"])
    add = AGAMA_DRAFT if kind == "draft" else (AGAMA_JUDGE if kind in JUDGING else "")
    if meta.get("agama") and add:
        for gap in ("\n\n", "\n"):
            if gap + _REPLY in s:
                s = s.replace(gap + _REPLY, "\n" + add + gap + _REPLY, 1)
                break
    return s


def apparatus_of(allp: list, xs: list) -> str:
    """The edition's apparatus on these verses' pages: a passage on the page that lists variants by manuscript
    ("7 yat (?)-B,C."), three at least. Empty when there is none."""
    pages = {x.get("page") for x in xs}
    ids = {x.get("id") for x in xs}
    out = []
    for y in allp:
        if y.get("page") in pages and y.get("id") not in ids and len(APPARATUS_RE.findall(y.get("text") or "")) >= 3:
            out.append(" ".join(str(y.get("text") or "").split()))
    return "\n".join(out)


def with_apparatus(base: str, allp: list, xs: list) -> str:
    ap = apparatus_of(allp, xs)
    if not ap:
        return base
    return (base + "\n\nTHE EDITION'S APPARATUS ON THIS PAGE (for understanding only; do not translate it: the variant "
            "readings of the manuscripts A, B, C ..., by the footnote numbers in the verses, which are not the text. "
            "Where a variant would change the meaning, say so in a note of kind textual):\n" + ap)


# --------------------------------------------------------------------------------------------- small things
def usd(x: float) -> str:
    return "$%.2f" % x if x >= 0.995 else ("$%.3f" % x if x >= 0.0095 else "$%.4f" % x)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def src_hash(text) -> str:
    return hashlib.sha256(" ".join(str(text or "").split()).encode("utf-8")).hexdigest()[:16]


def open_ro(db: str):
    return sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)


def has_table(con, name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


REF_TRUSTED = ("etext", "gretil", "bori")   # PILOT_FIX_2026_10_15: the engines whose verse numbers are the edition's


def ref_of(x: dict) -> str:
    """The verse's reference: its verse_ref where the edition numbers its verses (an e-text), or one with a dot when the
    engine is not known; else page.idx. PILOT_FIX_2026_10_15: an OCR reading's verse_ref is a number it found (the
    Hayasirsa's 20.10 was called "4"), not a reference."""
    r = x.get("ref")
    eng = str(x.get("engine") or "").lower()
    if r and (any(k in eng for k in REF_TRUSTED) or (not eng and "." in str(r))):
        return str(r)
    return "%s.%s" % (x.get("page"), x.get("idx"))


def register(path: Path) -> dict:
    """The latest record of each text in data/source_verdicts.jsonl."""
    last = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[str(r["doc"])] = r
    except OSError:
        pass
    return last


# --------------------------------------------------------------------------------------------- readiness
def is_index(text: str) -> bool:
    """Numbers among the words: an index, errata, an apparatus or a notation. Verse numbers between dandas and a
    sutra's own number at the head of a line do not count."""
    t = text or ""
    if any(m in t for m in INDEX_MARKS):
        return True
    s = SUTRA_NO.sub(" ", VERSE_NO.sub(" ", t))
    toks = [w for w in s.split() if w not in ("\u0964", "\u0965", "|", "||")]
    if not toks:
        return False
    n = sum(1 for w in toks if NUM_TOKEN.match(w) and HAS_DIGIT.search(w))
    return n >= 4 and n >= 0.25 * len(toks)


def hindi_words(text: str) -> set:
    return set(WORD.findall(text or "")) & HINDI_WORDS


def readiness(text, text_type=None, quality=None, min_quality: float = 0.35):
    """Why this passage is not sent (None: it is ready)."""
    t = text or ""
    if (text_type or "") in ("noise", "frontmatter"):
        return "noise or front matter"
    if len(DEV.findall(t)) < 8:
        return "fewer than 8 Devanagari signs"
    if JUNK.search(t):
        return "OCR debris (Latin letters in the Devanagari): mend the reading first"
    if quality is not None and float(quality) < min_quality:
        return "a reading below quality %.2f" % min_quality
    if is_index(t):
        return "numbers among the words: an index, errata, apparatus or notation, not verse"
    if len(hindi_words(t)) >= 3:
        return "Hindi prose (the edition's own Hindi), not Sanskrit"
    return None


# --------------------------------------------------------------------------------------------- the text
def load_text(con, doc: str) -> list:
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    sel = lambda c: ("p.%s" % c) if c in cols else "NULL"
    rows = con.execute("SELECT p.id, p.page_no, p.idx, p.text, %s, %s, %s, %s, %s, %s, %s FROM passages p JOIN docs d "
                       "ON d.id = p.doc_id WHERE d.code = ? ORDER BY p.page_no, p.idx"
                       % (sel("iast"), sel("translation"), sel("verse_ref"), sel("chapter"), sel("text_type"),
                          sel("quality_score"), sel("ocr_engine")), (doc,)).fetchall()
    keys = ("id", "page", "idx", "text", "iast", "english", "ref", "chapter", "type", "quality", "engine")
    return [dict(zip(keys, r)) for r in rows]


def raw_engine(raw_dir, doc: str) -> str:
    """The engine its first page file names (data/raw/<doc>_0001.jsonl), when the database does not record one."""
    try:
        with open(Path(raw_dir) / ("%s_0001.jsonl" % doc), encoding="utf-8") as f:
            r = json.loads(f.readline() or "{}")
        return str(r.get("engine") or "") if isinstance(r, dict) else ""
    except (OSError, ValueError):
        return ""


def doc_meta(con, doc: str, allp: list, raw_dir=None) -> dict:
    row = con.execute("SELECT category FROM docs WHERE code = ?", (doc,)).fetchone()
    cat = row[0] if row else None
    m = re.match(r"^MBh(\d\d)$", doc)
    title = ("the Mah\u0101bh\u0101rata, Book %d" % int(m.group(1))) if m else (
        doc.replace("_", " ") + (" (%s)" % cat if cat else ""))
    engines = {}
    for x in allp:
        e = (x.get("engine") or "").lower()
        engines[e] = engines.get(e, 0) + 1
    top = max(engines.items(), key=lambda kv: kv[1])[0] if engines else ""
    if not top and raw_dir is not None:
        top = raw_engine(raw_dir, doc).lower()
    if "bori" in top:
        source = "the BORI Critical Edition e-text"
    elif "gretil" in top or "etext" in top:
        source = "an e-text (GRETIL)"
    elif "vision" in top:
        source = "a vision OCR reading of a printed edition (a letter may be misread)"
    elif "tesseract" in top:
        source = "a Tesseract OCR reading of a printed edition (letters may be misread)"
    else:
        source = "a reading of a printed edition"
    title = TITLES.get(doc) or title   # CLAUDE_ENGINE_2026_10_15
    return {"doc": doc, "category": cat, "title": title, "source": source, "engine": top,
            "agama": bool(AGAMA.search("%s %s" % (cat or "", doc)))}


def latest_rows(con, doc: str, engine=None) -> dict:
    """{passage_id: the latest scholar row} of this text (PILOT_FIX_2026_10_15: of one engine, when it is named)."""
    if not has_table(con, "scholar_translations"):
        return {}
    if engine:
        cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND engine = ? AND id IN (SELECT MAX(id) "
                          "FROM scholar_translations WHERE doc_code = ? AND engine = ? GROUP BY passage_id)",
                          (doc, engine, doc, engine))
    else:
        cur = con.execute("SELECT * FROM scholar_translations WHERE doc_code = ? AND id IN (SELECT MAX(id) FROM "
                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id)", (doc, doc))
    names = [d[0] for d in cur.description]
    rows = [dict(zip(names, row)) for row in cur.fetchall()]
    return {r["passage_id"]: r for r in rows}


def current(row, x) -> bool:
    return bool(row) and row.get("src_hash") == src_hash(x.get("text"))


def parse_pages(s):
    if not s:
        return None
    out = set()
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def choose(a, allp: list, done: dict) -> tuple:
    """(indexes of the verses to send, [(passage, why)] left out, [passage] already done)."""
    pages = parse_pages(a.pages)
    started = not a.from_ref
    picked, left, skipped = [], [], []
    for i, x in enumerate(allp):
        if pages is not None and x["page"] not in pages:
            continue
        if a.only_page is not None and (x["page"] != a.only_page or (a.only_idx is not None and x["idx"] != a.only_idx)):
            continue
        if not started:
            if ref_of(x) != a.from_ref:
                continue
            started = True
        why = readiness(x["text"], x["type"], x["quality"], a.min_quality)
        if why:
            left.append((x, why))
            continue
        if current(done.get(x["id"]), x) and not a.redo:
            skipped.append(x)
            continue
        picked.append(i)
        if len(picked) >= a.limit:
            break
    return picked, left, skipped


def usable(x: dict) -> bool:
    return (x.get("type") or "") not in ("noise", "frontmatter") and len(DEV.findall(x.get("text") or "")) >= 8


def context(allp: list, i: int, done: dict) -> tuple:
    """([(passage, English)] before, [passage] after): the scholarly English of a verse before it where it passed or a
    person accepted it, the working English otherwise."""
    before, after = [], []
    j = i - 1
    while j >= 0 and len(before) < CONTEXT_BEFORE:
        y = allp[j]
        if usable(y):
            r = done.get(y["id"])
            good = current(r, y) and (r.get("status") == "passed" or r.get("review_verdict") == "accept")
            before.append((y, (r.get("translation") if good else None) or y.get("english") or ""))
        j -= 1
    before.reverse()
    j = i + 1
    while j < len(allp) and len(after) < CONTEXT_AFTER:
        if usable(allp[j]):
            after.append(allp[j])
        j += 1
    return before, after


def iast_of(x: dict) -> str:
    if x.get("iast"):
        return x["iast"]
    try:
        import iast_utils
        return iast_utils.devanagari_to_iast(x.get("text") or "") or ""
    except Exception:
        return ""


def _stem(term: str) -> str:
    t = (term or "").lower().strip()
    for suf in ("\u0101\u1e25", "a\u1e25", "\u0101", "a", "\u012b", "i", "\u016b", "u", "e", "o", "\u1e25", "\u1e43"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[:-len(suf)]
    return t


def glossary(con, doc: str, x: dict, before: list) -> list:
    """The entries this verse's prompt carries, up to GLOSSARY_MAX: a person's and the earlier verses' entries whose
    stem is in these verses' IAST first, then the entities found in this verse, then those found in the verses before.
    A person's entry wins over the scholar's, the scholar's over the entities'."""
    pids = [x["id"]] + [y["id"] for y, _ in reversed(before)]
    window = " ".join([iast_of(x)] + [iast_of(y) for y, _ in before]).lower()
    by = {}
    order = []

    def put(term, rendering, kind, note, source, rank):
        k = (term or "").strip().lower()
        if not k:
            return
        old = by.get(k)
        if old is None or rank > old["rank"]:
            by[k] = {"term": term.strip(), "rendering": rendering or "", "kind": kind or "", "note": note or "",
                     "source": source, "rank": rank}
        if k not in order:
            order.append(k)

    if has_table(con, "entity_mentions") and has_table(con, "entities"):
        try:
            q = ("SELECT m.passage_id, e.canonical, e.kind, e.notes FROM entity_mentions m JOIN entities e ON e.id = "
                 "m.entity_id WHERE m.passage_id IN (%s)" % ",".join("?" * len(pids)))
            rows = con.execute(q, pids).fetchall()
            pos = {p: n for n, p in enumerate(pids)}
            for pid, canon, kind, note in sorted(rows, key=lambda r: (pos.get(r[0], 99), r[1] or "")):
                put(canon, canon, kind, note, "entities", 1)
        except sqlite3.Error:
            pass
    try:
        g = con.execute("SELECT glossary FROM docs WHERE code = ?", (doc,)).fetchone()
        gd = json.loads(g[0]) if g and g[0] else {}
        if isinstance(gd, dict):
            for term, v in gd.items():
                v = v if isinstance(v, dict) else {}
                if _stem(v.get("iast") or term) in window:
                    ep = v.get("epithets")
                    put(term, v.get("iast") or term, v.get("type"), ", ".join(ep) if isinstance(ep, list) else (ep or ""),
                        "docs.glossary", 2)
    except (sqlite3.Error, ValueError, TypeError):
        pass
    if has_table(con, "scholar_glossary"):
        for term, rendering, kind, note, source in con.execute(
                "SELECT term, rendering, kind, note, source FROM scholar_glossary WHERE doc_code = ?", (doc,)):
            if _stem(term) and _stem(term) in window:
                put(term, rendering, kind, note, source or "scholar", 4 if source == "person" else 3)
    first = sorted(order, key=lambda k: -by[k]["rank"] if by[k]["rank"] >= 3 else 0)
    return [by[k] for k in first][:GLOSSARY_MAX]


def gloss_lines(gl: list) -> str:
    out = []
    for g in gl:
        s = "- " + g["term"]
        if g["rendering"] and g["rendering"] != g["term"]:
            s += " = " + g["rendering"]
        if g["kind"]:
            s += " (%s)" % g["kind"]
        if g["note"]:
            s += ": " + g["note"]
        out.append(s)
    return "\n".join(out)


def verse_message(meta: dict, x: dict, before: list, after: list, gl: list) -> str:
    parts = ["TEXT: %s. SOURCE: %s." % (meta["title"][:1].upper() + meta["title"][1:], meta["source"]),
             "CHAPTER: %s. VERSE: %s." % (x.get("chapter") or "?", ref_of(x))]
    if gl:
        parts.append("GLOSSARY (keep these spellings; it does not say who is who):\n" + gloss_lines(gl))
    if before:
        parts.append("THE VERSES BEFORE (for understanding only; their English may be a working draft, and wrong):\n"
                     + "\n".join("[%s] %s\n   English: %s" % (ref_of(y), (y["text"] or "").strip(), (e or "-").strip())
                                 for y, e in before))
    parts.append("THE VERSE TO TRANSLATE [%s]:\n%s\nIAST: %s" % (ref_of(x), (x["text"] or "").strip(),
                                                                (iast_of(x) or "-").strip()))
    if after:
        parts.append("THE VERSES AFTER (Sanskrit only, for understanding only):\n"
                     + "\n".join("[%s] %s" % (ref_of(y), (y["text"] or "").strip()) for y in after))
    return "\n\n".join(parts)


def notes_text(notes: list) -> str:
    return "\n".join("- %s (%s): %s" % (n.get("anchor", ""), n.get("kind", ""), n.get("note", "")) for n in notes) or "-"


def critic_message(base: str, cur: dict) -> str:
    return (base + "\n\nTHE DRAFT TRANSLATION:\n" + cur["translation"] + "\n\nITS NOTES:\n" + notes_text(cur["notes"])
            + "\n\nTHE TRANSLATOR'S DOUBTS: " + (cur.get("doubts") or "-"))


def revise_message(base: str, cur: dict, crit: dict) -> str:
    finds = "\n".join("- [%s %s] %s: %s" % (i.get("severity", ""), i.get("type", ""), i.get("where", ""), i.get("fix", ""))
                      for i in crit.get("issues") or []) or "- (no specific issue named; fidelity %s, completeness %s)" % (
        crit.get("fidelity"), crit.get("completeness"))
    mine = {"translation": cur["translation"], "notes": cur["notes"], "doubts": cur.get("doubts") or ""}
    if cur.get("segments"):   # SCHOLAR_V2_2026_10_14: a sentence over several verses
        mine["segments"] = [{"ref": r, "english": t} for r, t in cur["segments"].items()]
    mine = json.dumps(mine, ensure_ascii=False)
    return base + "\n\nYOUR DRAFT:\n" + mine + "\n\nTHE REVIEWER'S FINDINGS:\n" + finds + "\n\n" + REVISE_ASK


def group_message(meta: dict, xs: list, before: list, after: list, gl: list) -> str:
    """SCHOLAR_V2_2026_10_14: the message for one Sanskrit sentence that runs over several verses (xs, in order)."""
    m = verse_message(meta, xs[0], before, after, gl)
    head = "THE VERSE TO TRANSLATE [%s]:" % ref_of(xs[0])
    i = m.index(head)
    j = m.find("\n\nTHE VERSES AFTER", i)
    body = ("THE VERSES TO TRANSLATE [%s] to [%s] (one Sanskrit sentence: give \"segments\", one for each verse):\n"
            % (ref_of(xs[0]), ref_of(xs[-1]))
            + "\n".join("[%s] %s\n   IAST: %s" % (ref_of(y), (y["text"] or "").strip(), (iast_of(y) or "-").strip())
                        for y in xs))
    m = m[:i] + body + (m[j:] if j >= 0 else "")
    return m.replace("CHAPTER: %s. VERSE: %s." % (xs[0].get("chapter") or "?", ref_of(xs[0])),
                     "CHAPTER: %s. VERSES: %s to %s." % (xs[0].get("chapter") or "?", ref_of(xs[0]), ref_of(xs[-1])), 1)


def groups_message(meta: dict, xs: list) -> str:
    """SCHOLAR_V2_2026_10_14: the verses whose sentences the groups call marks."""
    return ("TEXT: %s.\n\nTHE VERSES:\n" % (meta["title"][:1].upper() + meta["title"][1:])
            + "\n".join("[%s] %s" % (ref_of(y), (y["text"] or "").strip()) for y in xs))


def compare_message(base: str, a_txt: str, b_txt: str) -> str:
    """SCHOLAR_V2_2026_10_14: the second judge's message: the verse(s) with their context, and the two Englishes."""
    return base + "\n\nTRANSLATION A:\n" + a_txt + "\n\nTRANSLATION B:\n" + b_txt


# --------------------------------------------------------------------------------------------- the answers
def parse_json(txt: str):
    s = (txt or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[A-Za-z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        d = json.loads(s)
    except ValueError:
        d = first_object(s)   # RUN_FIX_2026_10_15: the first whole object, whatever follows it
        if d is None:
            m = re.search(r"\{.*\}", s, re.S)
            if not m:
                return None
            try:
                d = json.loads(m.group(0))
            except ValueError:
                return None
    return d if isinstance(d, dict) else None


def first_object(s: str, tries: int = 20):
    """RUN_FIX_2026_10_15: the first JSON object that decodes whole from a "{" of s (at most tries of them); None."""
    dec = json.JSONDecoder()
    i = s.find("{")
    while i >= 0 and tries > 0:
        try:
            d, _end = dec.raw_decode(s[i:])
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
        i = s.find("{", i + 1)
        tries -= 1
    return None


def _s(v, n: int) -> str:
    return str(v if v is not None else "").strip()[:n]


def clean_draft(d) -> dict | None:
    if not isinstance(d, dict) or not _s(d.get("translation"), 8000):
        return None
    notes = []
    for n in d.get("notes") or []:
        if isinstance(n, dict) and _s(n.get("note"), 600):
            notes.append({"anchor": _s(n.get("anchor"), 120), "kind": _s(n.get("kind"), 20), "note": _s(n.get("note"), 600)})
    gl = []
    for g in d.get("glossary") or []:
        if isinstance(g, dict) and _s(g.get("term"), 60):
            gl.append({"term": _s(g.get("term"), 60), "rendering": _s(g.get("rendering"), 80), "kind": _s(g.get("kind"), 20),
                       "note": _s(g.get("note"), 200)})
    segs = [{"ref": _s(x.get("ref"), 40), "english": _s(x.get("english"), 4000)}
            for x in (d.get("segments") or []) if isinstance(x, dict)]   # SCHOLAR_V2_2026_10_14: a sentence over verses
    return {"translation": _s(d.get("translation"), 8000), "notes": notes[:12], "glossary": gl[:8],
            "doubts": _s(d.get("doubts"), 1000), "segment_list": segs, "moved": _s(d.get("moved"), 400)}


def _int15(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return v if 1 <= v <= 5 else None


def clean_critique(d) -> dict | None:
    if not isinstance(d, dict):
        return None
    issues = []
    for i in d.get("issues") or []:
        if isinstance(i, dict):
            sev = _s(i.get("severity"), 10).lower()
            issues.append({"type": _s(i.get("type"), 20).lower(), "where": _s(i.get("where"), 200),
                           "fix": _s(i.get("fix"), 600), "severity": "major" if sev == "major" else "minor"})
    v = _s(d.get("verdict"), 10).lower()
    return {"fidelity": _int15(d.get("fidelity")), "completeness": _int15(d.get("completeness")), "issues": issues[:20],
            "verdict": "accept" if v == "accept" else "revise"}


def accepted(c) -> bool:
    return bool(c) and c["verdict"] == "accept" and (c["fidelity"] or 0) >= 4 and (c["completeness"] or 0) >= 4 \
        and not any(i["severity"] == "major" for i in c["issues"])


def status_of(c, fid, flu) -> str:
    if c and any(i["type"] == "source" and i["severity"] == "major" for i in c["issues"]):
        return "source_doubt"
    if accepted(c) and (fid or 0) >= 4 and (flu or 0) >= 4:
        return "passed"
    return "flagged"


def clean_unit(d, refs: list):
    """SCHOLAR_V2_2026_10_14: clean_draft, and for several verses their segments: {ref: English} when the answer gives
    one for each verse, in order (the translation is then the segments joined); else None, and the whole English
    stays on the first verse."""
    cur = clean_draft(d)
    if cur is None:
        return None
    cur["segments"] = None
    if len(refs) > 1:
        segs = cur.get("segment_list") or []
        if [s_["ref"] for s_ in segs] == list(refs) and any(s_["english"] for s_ in segs):
            cur["segments"] = {s_["ref"]: s_["english"] for s_ in segs}
            joined = " ".join(s_["english"] for s_ in segs if s_["english"])
            # SCHOLAR_V21_2026_10_14: the passage stays as the draft wrote it (in the order English needs); only one much
            # shorter than its segments, which is no passage, gives way to them
            if len(cur["translation"]) < 0.6 * len(joined):
                cur["translation"] = joined
    return cur


def clean_compare(d):
    """SCHOLAR_V2_2026_10_14: the second judge's answer, cleaned; None when it is not one."""
    if not isinstance(d, dict):
        return None

    def side(v):
        v = v if isinstance(v, dict) else {}
        errs = []
        for x in v.get("errors") or []:
            if isinstance(x, dict) and _s(x.get("error"), 300):
                sev = _s(x.get("severity"), 10).lower()
                errs.append({"where": _s(x.get("where"), 200), "error": _s(x.get("error"), 300),
                             "severity": "major" if sev == "major" else "minor"})
        return {"fidelity": _int15(v.get("fidelity")), "errors": errs[:12]}

    b = _s(d.get("better"), 10).upper()
    return {"A": side(d.get("A")), "B": side(d.get("B")), "better": b if b in ("A", "B") else "equal",
            "reason": _s(d.get("reason"), 400)}


def parse_groups(d, refs: list, idxs: list) -> list:
    """SCHOLAR_V2_2026_10_14: the sentences the groups call gives, as lists of idxs, when they hold every ref once, in
    order, at most GROUP_MAX each; else one verse each."""
    one = [[i] for i in idxs]
    try:
        gs = d.get("groups") if isinstance(d, dict) else None
        flat = [str(r) for g in gs for r in g]
    except TypeError:
        return one
    if flat != list(refs) or any(not g or len(g) > GROUP_MAX for g in gs):
        return one
    out, k = [], 0
    for g in gs:
        out.append(list(idxs[k:k + len(g)]))
        k += len(g)
    return out


# --------------------------------------------------------------------------------------------- the calls
class CallFailed(RuntimeError):
    pass


def _charge(kind, doc, engine, resp, in_chars, out_chars, dt, ok, con) -> float:
    """usage_meter.meter, as every paid call records itself; the cost it charged, or the pricing table's when the meter
    could not record (for this run's cap only)."""
    cost = 0.0
    try:
        from usage_meter import meter, usage_from_response
        cost = meter(kind=kind, doc=doc, engine=engine, resp=resp, in_chars=in_chars, out_chars=out_chars, units=1,
                     duration_s=dt, ok=ok, con=con) or 0.0
        if not cost:
            import cost_tracker
            i, o = usage_from_response(resp) if resp is not None else (None, None)
            if i is None:
                i, o = cost_tracker.chars_to_tokens(in_chars), cost_tracker.chars_to_tokens(out_chars)
            cost = cost_tracker.estimate_cost_from_tokens(engine, i, o)
    except Exception:
        pass
    return float(cost or 0.0)


_FINISH = {"1": "STOP", "2": "MAX_TOKENS", "3": "SAFETY", "4": "RECITATION", "5": "OTHER"}


def _finish_name(f) -> str:
    """SCHOLAR_V21_2026_10_14: how an answer ended, by name (the SDK gives an enum, or its number)."""
    n = getattr(f, "name", None)
    if n:
        return str(n)
    s = str(f if f is not None else "")
    return _FINISH.get(s, s.split(".")[-1] or "?")


class Gemini:
    """The real calls: the translator and the critic (gemini-2.5-pro), the judge (judge_sample.py's). Built first, so
    that without a key or the SDK nothing is called or written."""

    def __init__(self, a, meta: dict, con):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (.env)")
        try:
            import google.generativeai as genai
            import judge_sample as js
        except ImportError as e:
            raise RuntimeError("the models cannot be loaded (%s): pip install google-generativeai" % e)
        genai.configure(api_key=key)
        self.genai, self.js, self.a, self.meta, self.con = genai, js, a, meta, con
        try:
            import infer_mt
            self.safety, self._gen = infer_mt._GEMINI_SAFETY, infer_mt._gen
        except Exception:
            self.safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in (
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT")]
            self._gen = lambda gm, msg: gm.generate_content(msg)
        self.models = {}
        self.spent = 0.0          # every call this run made, as charged
        self.judge_model = self._model("judge")

    def _cfg(self, temp, maxtok):
        try:
            return self.genai.GenerationConfig(temperature=temp, max_output_tokens=maxtok,
                                               response_mime_type="application/json")
        except TypeError:
            return self.genai.GenerationConfig(temperature=temp, max_output_tokens=maxtok)

    def _model(self, kind: str, maxtok: int = 8192):
        key = (kind, maxtok)
        if key not in self.models:
            name = lambda e: e.split(":", 1)[1] if ":" in e else e
            if kind == "judge":
                self.models[key] = self.genai.GenerativeModel(
                    model_name=name(self.a.judge_engine), generation_config=self._cfg(0.0, 2048),
                    system_instruction=self.js._SYS.format(lang_name="English"))
            else:
                system = system_for(kind, self.meta)   # CLAUDE_ENGINE_2026_10_15 (SCHOLAR_V2_2026_10_14)
                self.models[key] = self.genai.GenerativeModel(
                    model_name=name(self.a.engine), generation_config=self._cfg(0.1 if kind == "draft" else 0.0, maxtok),
                    safety_settings=self.safety, system_instruction=system)
        return self.models[key]

    def _once(self, kind, msg, maxtok):
        system_len = len(system_for(kind, self.meta))   # CLAUDE_ENGINE_2026_10_15 (SCHOLAR_V2_2026_10_14)
        last = None
        for k in range(3):
            t0 = time.time()
            try:
                resp = self._gen(self._model(kind, maxtok), msg)
            except Exception as e:   # quota, network, server: wait and ask again
                last = e
                time.sleep((2, 6, 15)[k])
                continue
            try:
                txt = (resp.text or "").strip()
            except Exception:
                txt = ""
            finish = None
            try:
                finish = resp.candidates[0].finish_reason
            except Exception:
                pass
            cost = _charge(getattr(self, "meter_kind", "scholar"), self.meta["doc"], self.a.engine, resp,
                           system_len + len(msg), len(txt), time.time() - t0, bool(txt), self.con)   # CLAUDE_ENGINE
            self.spent += cost
            return txt, finish, cost
        raise CallFailed("%s: %s" % (type(last).__name__, str(last)[:160]))

    def ask(self, kind: str, msg: str) -> tuple:
        """(the JSON answer or None, $). SCHOLAR_V21_2026_10_14: an answer cut off at the token limit and not JSON is asked
        again with room, even when some text came back; a draft still not JSON is asked once more; self.last says how
        the last answer ended."""
        txt, finish, cost = self._once(kind, msg, 8192)
        d = parse_json(txt)
        if d is None and _finish_name(finish) == "MAX_TOKENS":
            txt, finish, more = self._once(kind, msg, 16384)   # its thinking took the budget: once more, with room
            cost += more
            d = parse_json(txt)
        if d is None and kind == "draft":
            txt, finish, more = self._once(kind, msg, 16384)
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": _finish_name(finish), "chars": len(txt or ""), "json": d is not None}
        return d, cost

    def judge(self, src: str, iast: str, english: str) -> tuple:
        """(fidelity, fluency, reason, $) by judge-v1."""
        t0 = time.time()
        try:
            fid, flu, why = self.js._judge_one(self.judge_model, "English", src, iast, english)
        except Exception as e:
            return None, None, "[judge failed: %s]" % type(e).__name__, 0.0
        r, inc, outc = getattr(self.js._judge_one, "last", (None, 0, 0))
        cost = _charge("judge", self.meta["doc"], self.a.judge_engine, r, inc, outc, time.time() - t0, fid is not None,
                       self.con)
        self.spent += cost
        return fid, flu, why, cost


class Claude:
    """CLAUDE_ENGINE_2026_10_15: the translator, the critic and the groups call by Claude (scripts/claude_engine.py);
    the judge (judge-v1) and the second judge by Gemini (--judge-engine, --compare-engine), so that a Claude English is
    never judged by Claude. Built first: without either key or SDK nothing is called or written."""

    def __init__(self, a, meta: dict, con, sdk=None):
        import claude_engine as ce
        model, effort = ce.parse_engine(a.engine)
        self.ce, self.a, self.meta = ce, a, meta
        self.client = ce.Client(model, effort, sdk=sdk)
        ga = argparse.Namespace(**vars(a))
        ga.engine = getattr(a, "compare_engine", None) or COMPARE_ENGINE
        self.gem = Gemini(ga, meta, con)
        self.own = 0.0            # the Claude calls of this run, as charged
        self.meter_kind = "scholar"
        self.con = con

    @property
    def con(self):
        return self._con

    @con.setter
    def con(self, v):
        self._con = v
        if getattr(self, "gem", None) is not None:
            self.gem.con = v

    @property
    def spent(self) -> float:
        return self.own + self.gem.spent

    def _once(self, kind, msg, maxtok):
        t0 = time.time()
        try:
            resp = self.client.create(system_for(kind, self.meta), msg, maxtok)
        except Exception as e:   # the SDK asked again already (a rate limit, an overload, a server error)
            raise CallFailed("%s: %s" % (type(e).__name__, str(e)[:200]))
        txt = self.ce.text_of(resp)
        cost = self.ce.meter(self.con, self.meter_kind, self.meta["doc"], self.client.model, getattr(resp, "usage", None),
                             time.time() - t0, bool(txt))
        self.own += cost
        return txt, self.ce.stop_of(resp), cost

    def ask(self, kind: str, msg: str) -> tuple:
        """(the JSON answer or None, $), as Gemini.ask: an answer cut off at max_tokens and not JSON is asked again with
        twice the room; a draft still not JSON once more. The second judge (compare) is Gemini's."""
        if kind == "compare":
            return self.gem.ask(kind, msg)
        txt, stop, cost = self._once(kind, msg, CLAUDE_MAX_TOKENS)
        d = parse_json(txt)
        if d is None and stop == "max_tokens":
            txt, stop, more = self._once(kind, msg, 2 * CLAUDE_MAX_TOKENS)
            cost += more
            d = parse_json(txt)
        if d is None and kind in ("draft", "critic") and stop != "refusal":   # RUN_FIX_2026_10_15: a critic too
            txt, stop, more = self._once(kind, msg, 2 * CLAUDE_MAX_TOKENS)
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": stop, "chars": len(txt or ""), "json": d is not None}
        self.kept = keep_unparsed(self.a, self.meta, kind, stop, txt, self.client.model) if d is None else None
        return d, cost

    def judge(self, src: str, iast: str, english: str) -> tuple:
        return self.gem.judge(src, iast, english)

    def audit(self, base: str, cur: dict):
        """AUDIT_2026_10_15: Gemini's critic (--compare-engine) reads the last version: an independent reading of a
        Claude English. The critique, with "by"; None when it does not answer."""
        try:
            d, _c = self.gem.ask("critic", critic_message(base, cur))
        except CallFailed:
            return None
        c = clean_critique(d)
        if c is not None:
            c["by"] = self.gem.a.engine
        return c


def keep_unparsed(a, meta: dict, kind: str, stop, txt, engine):
    """RUN_FIX_2026_10_15: an answer that is not JSON, kept so that it can be read (unparsed_<doc>.jsonl in --log-dir,
    data/scholar by default): its kind, how it ended, its length, its first and last 300 characters. The file, or None
    (no log folder, or it could not be written). Never raises."""
    d = getattr(a, "log_dir", None)
    if not d:
        return None
    try:
        p = Path(d) / ("unparsed_%s.jsonl" % _safe(meta.get("doc") or "x"))
        p.parent.mkdir(parents=True, exist_ok=True)
        t = str(txt or "")
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now(), "doc": meta.get("doc"), "kind": kind, "engine": engine, "stop": str(stop),
                                "chars": len(t), "head": t[:300], "tail": t[-300:], "mark": "RUN_FIX_2026_10_15"},
                               ensure_ascii=False) + "\n")
        return p
    except Exception:
        return None


class CreditGate:
    """CLAUDE_ENGINE_2026_10_15: run()'s cap for a Claude run: the Claude credit for its calls, the spend cap for the
    judges' part (Google's); why says which stopped it."""

    def __init__(self, ce, google_ok=None, judge_share: float = 0.05):
        self.ce, self.google_ok, self.share, self.why = ce, google_ok, judge_share, ""

    def __call__(self, con, need: float) -> bool:
        if not self.ce.budget_ok(con, need):
            self.why = "the Claude credit is spent or expired (python scripts\\claude_engine.py --credit shows it)"
            return False
        if self.google_ok is not None and not self.google_ok(con, need * self.share):
            self.why = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            return False
        return True


# --------------------------------------------------------------------------------------------- the run
def ensure_schema(con) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS scholar_translations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      passage_id INTEGER NOT NULL, doc_code TEXT NOT NULL, page_no INTEGER, idx INTEGER, verse_ref TEXT,
      src_hash TEXT NOT NULL, version INTEGER NOT NULL,
      translation TEXT, notes TEXT, doubts TEXT, draft TEXT, critique TEXT, passes INTEGER,
      fidelity INTEGER, fluency INTEGER, judge_reason TEXT, working_fidelity INTEGER, working_fluency INTEGER,
      status TEXT, engine TEXT, judge_engine TEXT, prompt_version TEXT, cost_usd REAL, created_at TEXT,
      reviewed_by TEXT, reviewed_at TEXT, review_verdict TEXT, review_note TEXT,
      UNIQUE(passage_id, version));
    CREATE INDEX IF NOT EXISTS ix_scholar_translations_doc ON scholar_translations(doc_code, page_no, idx);
    CREATE INDEX IF NOT EXISTS ix_scholar_translations_passage ON scholar_translations(passage_id);
    CREATE TABLE IF NOT EXISTS scholar_glossary(
      id INTEGER PRIMARY KEY AUTOINCREMENT, doc_code TEXT NOT NULL, term TEXT NOT NULL, rendering TEXT, kind TEXT,
      note TEXT, source TEXT, created_at TEXT, UNIQUE(doc_code, term));
    """)
    have = {r[1] for r in con.execute("PRAGMA table_info(scholar_translations)")}
    for c, t in (("group_ref", "TEXT"), ("group_translation", "TEXT"), ("moved", "TEXT"), ("compare", "TEXT"),
                 ("compare_better", "TEXT")):   # SCHOLAR_V2_2026_10_14: added in place
        if c not in have:
            con.execute("ALTER TABLE scholar_translations ADD COLUMN %s %s" % (c, t))
    con.commit()


def call_price(in_chars: int, engine: str) -> float:
    try:
        import cost_tracker
        return cost_tracker.estimate_cost_from_tokens(engine, in_chars / 3.0, OUT_TOKENS_PRIOR)
    except Exception:
        return in_chars / 3.0 * 1.25e-6 + OUT_TOKENS_PRIOR * 10e-6


def prices(con, a, first_msg_chars: int) -> dict:
    """$ a verse: typical (a draft, a critique, half the time a revision and a critique more, two judges) and the most
    (--rounds revisions); measured from scholar_translations after MEASURED_AFTER verses."""
    one = call_price(len(SYSTEM_DRAFT) + first_msg_chars, a.engine)
    rev = call_price(len(SYSTEM_DRAFT) + first_msg_chars + 1500, a.engine)
    typ = 2 * one + 0.5 * 2 * rev + 2 * JUDGE_COST_PRIOR
    top = 2 * one + a.rounds * 2 * rev + 2 * JUDGE_COST_PRIOR
    how = "a prior until %d verses are measured (output %d tokens a call, with the thinking)" % (MEASURED_AFTER,
                                                                                                  OUT_TOKENS_PRIOR)
    try:   # SCHOLAR_V2_2026_10_14: this prompt's rows when there are 10; before, scholar-v1's with a compare at half
        if has_table(con, "scholar_translations"):
            q = ("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE engine = ? AND "
                 "cost_usd > 0 AND prompt_version LIKE ? AND created_at >= ?")   # COST_TRUTH_2026_10_15
            n, avg, mx = con.execute(q, (a.engine, PROMPT_VERSION + "+%", METERED_SINCE)).fetchone()
            fam = PROMPT_VERSION.split(".")[0]   # SCHOLAR_V21_2026_10_14: scholar-v2.1 is priced by scholar-v2's rows
            nf, avgf, mxf = (con.execute(q, (a.engine, fam + "+%", METERED_SINCE)).fetchone() if fam != PROMPT_VERSION
                             else (0, None, None))
            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d %s verses" % (n, PROMPT_VERSION)
            elif nf and nf >= MEASURED_AFTER:
                typ, top, how = float(avgf), float(mxf), "measured on %d %s verses" % (nf, fam)
            else:
                n1, avg1, mx1 = con.execute(q, (a.engine, "scholar-v1+%", METERED_SINCE)).fetchone()
                if n1 and n1 >= MEASURED_AFTER:
                    k = 1.5 if getattr(a, "compare", False) else 1.0
                    typ, top = float(avg1) * k, float(mx1) * k
                    how = "measured on %d scholar-v1 verses%s" % (n1, ", with a compare call at half of it" if k > 1 else "")
    except sqlite3.Error:
        pass
    return {"typical": typ, "most": top, "call": rev, "how": how}


def busy_with(doc: str):
    """The dashboard's jobs on this text that change its Sanskrit or English (None when the dashboard does not answer)."""
    try:
        import repair_text as rt
        jobs = rt.dashboard_jobs()
    except Exception:
        return None
    if jobs is None:
        return None
    return [j for j in jobs if j.get("doc") == doc and j.get("kind") not in QUIET_KINDS
            and not (j.get("kind") == "pipeline" and pipeline_past_ingest(j, doc))]   # RUN_FIX_2026_10_15


def job_out(jid) -> str:
    """RUN_FIX_2026_10_15: a dashboard job's output, as /api/job/<id> gives it (read-only); "" when it does not answer."""
    try:
        import urllib.request
        import repair_text as rt
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(rt.DASHBOARD + "/api/job/%s" % jid, timeout=6) as f:
            return str(json.loads(f.read().decode("utf-8")).get("out") or "")
    except Exception:
        return ""


def pipeline_past_ingest(j: dict, doc: str) -> bool:
    """RUN_FIX_2026_10_15: a running pipeline job (pipeline_queue.py) whose output has reached its translate or export
    stage, after its OCR and ingest: it changes no Sanskrit any more. False when it is queued, earlier, or unknown."""
    if j.get("state") != "running" or not j.get("id"):
        return False
    out = job_out(j["id"])
    return ("  Translate %s" % doc) in out or ("  Export %s" % doc) in out


def compare(asker, base: str, scholarly: str, working: str, pid: int):
    """SCHOLAR_V2_2026_10_14: the second judge (scholar-compare-v1): both Englishes with the context, in an order it is
    not told (the passage id decides), the errors of each and the more faithful. None when it does not answer."""
    s_first = int(pid) % 2 == 0
    a_txt, b_txt = (scholarly, working) if s_first else (working, scholarly)
    d, _c = asker.ask("compare", compare_message(base, a_txt, b_txt))
    c = clean_compare(d)
    if c is None:
        return None
    s, w = (c["A"], c["B"]) if s_first else (c["B"], c["A"])
    better = {"A": "scholarly" if s_first else "working", "B": "working" if s_first else "scholarly"}.get(c["better"],
                                                                                                         "equal")
    return {"scholarly": s, "working": w, "better": better, "reason": c["reason"],
            "order": "scholarly as A" if s_first else "scholarly as B", "version": COMPARE_VERSION}


def one_unit(a, allp, idxs, meta, done, asker, con, call: float) -> list:
    """SCHOLAR_V2_2026_10_14: one verse, or one Sanskrit sentence over several (idxs: their places in allp, in order):
    the draft, the critic and the revisions, the judge, the second judge. The rows to store, one a verse; asker.spent
    counts every call it made."""
    xs = [allp[i] for i in idxs]
    x = xs[0]
    refs = [ref_of(y) for y in xs]
    before, after = context(allp, idxs[0], done)
    if len(xs) > 1:
        after = context(allp, idxs[-1], done)[1]
    gl = glossary(con, a.doc, x, before + [(y, "") for y in xs[1:]])
    base = verse_message(meta, x, before, after, gl) if len(xs) == 1 else group_message(meta, xs, before, after, gl)
    base = with_apparatus(base, allp, xs)   # CLAUDE_ENGINE_2026_10_15: the edition's variants on the page
    spent0 = asker.spent
    d, _c = asker.ask("draft", base)
    cur = clean_unit(d, refs)
    if cur is None:
        last = getattr(asker, "last", None) or {}   # SCHOLAR_V21_2026_10_14: how it ended
        raise CallFailed("the draft came back without a translation%s" % (
            (" (it ended %s, %s characters%s)" % (last.get("finish") or "?", "{:,}".format(last.get("chars") or 0),
                                                 "" if last.get("json") else ", not JSON")) if last else ""))
    draft = cur["translation"]
    crits, revisions, note = [], 0, ""
    while True:
        cr, _c = asker.ask("critic", critic_message(base, cur))
        cr = clean_critique(cr)
        crits.append(cr)
        if cr is None:   # RUN_FIX_2026_10_15: say so; the status is flagged, unless the audit reads it
            kept = getattr(asker, "kept", None)
            note = "; ".join(s_ for s_ in (note, "the critic's answer could not be read" + (
                " (it is kept in %s beside the run's log)" % kept.name if kept else "")) if s_)
        if accepted(cr) or revisions >= a.rounds or cr is None:
            break
        if asker.spent + 2 * call > a.max_usd:
            note = "not revised: --max-usd $%.2f would be passed" % a.max_usd
            break
        rv, _c = asker.ask("draft", revise_message(base, cur, cr))
        rv = clean_unit(rv, refs)
        if rv is None:
            note = "the revision came back without a translation; the last version is kept"
            break
        cur = rv
        revisions += 1
    audit = None   # AUDIT_2026_10_15: another family reads the last version; its reading decides the status
    if getattr(a, "audit_every", 0) and hasattr(asker, "audit") and audit_this(a, x):
        if asker.spent + call > a.max_usd:
            note = "; ".join(s_ for s_ in (note, "not audited: --max-usd $%.2f would be passed" % a.max_usd) if s_)
        else:
            audit = asker.audit(base, cur)
            if audit is not None:
                crits.append(audit)
    final = crits[-1] if crits else None
    src = "\n".join((y["text"] or "").strip() for y in xs)
    ia = "\n".join(iast_of(y) for y in xs)
    fid, flu, why, _c = asker.judge(src, ia, cur["translation"])
    wk = [(y.get("english") or "").strip() for y in xs]
    working = " ".join(wk) if all(wk) else ""
    wfid = wflu = None
    if working:
        wfid, wflu, _w, _c = asker.judge(src, ia, working)
    cmp_ = None
    if getattr(a, "compare", False) and working and compare_this(a, x):   # PILOT_FIX_2026_10_15: one in N
        if asker.spent + call > a.max_usd:
            note = "; ".join(s_ for s_ in (note, "not compared: --max-usd $%.2f would be passed" % a.max_usd) if s_)
        else:
            cmp_ = compare(asker, base, cur["translation"], working, x["id"])
    st = status_of(final, fid, flu)
    if st == "passed" and cmp_ and any(e_["severity"] == "major" for e_ in cmp_["scholarly"]["errors"]):
        st = "flagged"   # the second judge found a major error in it: a person reads it
    cost = asker.spent - spent0
    gref = ("%s-%s" % (refs[0], refs[-1])) if len(xs) > 1 else None
    at = now()
    segs = cur.get("segments")
    rows = []
    for k, y in enumerate(xs):
        if gref is None:
            eng = cur["translation"]
        elif segs:
            eng = segs.get(refs[k], "")
        else:
            eng = cur["translation"] if k == 0 else ""
        rows.append({"passage_id": y["id"], "doc_code": a.doc, "page_no": y["page"], "idx": y["idx"], "verse_ref": refs[k],
                     "src_hash": src_hash(y["text"]), "translation": eng,
                     "notes": json.dumps(cur["notes"], ensure_ascii=False),
                     "doubts": "; ".join(s_ for s_ in (cur.get("doubts"), note) if s_), "draft": draft,
                     "critique": json.dumps(crits, ensure_ascii=False), "passes": 1 + revisions, "fidelity": fid,
                     "fluency": flu, "judge_reason": (why or "")[:200], "working_fidelity": wfid, "working_fluency": wflu,
                     "status": st, "engine": a.engine, "judge_engine": a.judge_engine,
                     "prompt_version": "%s+%s%s" % (PROMPT_VERSION, CRITIC_VERSION, ("+" + AGAMA_VERSION) if meta.get(
                         "agama") else ""), "cost_usd": round(cost / len(xs), 6),   # CLAUDE_ENGINE_2026_10_15
                     "created_at": at, "group_ref": gref, "group_translation": cur["translation"] if gref else None,
                     "moved": cur.get("moved") or None,
                     "compare": json.dumps(cmp_, ensure_ascii=False) if cmp_ else None,
                     "compare_better": cmp_["better"] if cmp_ else None,
                     "_glossary": cur["glossary"] if k == 0 and not getattr(a, "no_glossary_adds", False) else [],
                     "_audit": audit["verdict"] if audit else None})   # AUDIT_2026_10_15
    return rows


def audit_this(a, x) -> bool:
    """AUDIT_2026_10_15: whether Gemini's critic reads this sentence (its first passage x): one in --audit-every, by
    hash (another seed than the second judge's)."""
    n = int(getattr(a, "audit_every", 0) or 0)
    return n > 0 and (n == 1 or int(src_hash("audit:%s" % x["id"]), 16) % n == 0)


def status_lines(con, doc: str, allp: list, a) -> list:
    """AUDIT_2026_10_15: per engine, what this text has: verses (of those ready), passed, flagged, source doubts, stale,
    audited, $ spent, the last row's time."""
    pages = parse_pages(getattr(a, "pages", None))
    sel = [x for x in allp if pages is None or x["page"] in pages]
    ready = sum(1 for x in sel if not readiness(x["text"], x["type"], x["quality"], a.min_quality))
    ids = {x["id"] for x in sel}
    if not has_table(con, "scholar_translations"):
        return ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]
    text = {x["id"]: x["text"] for x in allp}
    per = {}
    for eng, pid, st_, h, crit, at in con.execute(
            "SELECT engine, passage_id, status, src_hash, critique, created_at FROM scholar_translations WHERE doc_code = ? "
            "AND id IN (SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY engine, passage_id)",
            (doc, doc)):
        if pid not in ids:
            continue
        e = per.setdefault(eng, {"n": 0, "passed": 0, "flagged": 0, "source_doubt": 0, "stale": 0, "audited": 0,
                                 "last": ""})
        e["n"] += 1
        if text.get(pid) is None or src_hash(text.get(pid)) != h:
            e["stale"] += 1
        elif st_ in e:
            e[st_] += 1
        if '"by":' in (crit or ""):
            e["audited"] += 1
        e["last"] = max(e["last"], at or "")
    spent = dict(con.execute("SELECT engine, COALESCE(SUM(cost_usd), 0) FROM scholar_translations WHERE doc_code = ? "
                             "GROUP BY engine", (doc,)).fetchall())
    out = []
    for eng, e in sorted(per.items()):
        out.append("  %s: %s of %s verses (%d%%); passed %d, flagged %d, source doubts %d, stale %d; audited %d; %s spent "
                   "(all its rows here); the last at %s"
                   % (eng, "{:,}".format(e["n"]), "{:,}".format(ready), round(100.0 * e["n"] / max(1, ready)), e["passed"],
                      e["flagged"], e["source_doubt"], e["stale"], e["audited"], usd(spent.get(eng) or 0.0),
                      (e["last"] or "?")[:16].replace("T", " ")))
    return out or ["  no scholarly English yet; %s verse(s) ready" % "{:,}".format(ready)]


def compare_this(a, x) -> bool:
    """PILOT_FIX_2026_10_15: whether the second judge reads this sentence (its first passage x): every one, or one in
    --compare-every, chosen by the hash of the passage id (its parity sets the order A/B in compare())."""
    n = max(1, int(getattr(a, "compare_every", 1) or 1))
    return n == 1 or int(src_hash("compare:%s" % x["id"]), 16) % n == 0


def one_verse(a, allp, i, meta, done, asker, con, call: float) -> dict:
    """One verse alone: the row to store (as before SCHOLAR_V2_2026_10_14)."""
    return one_unit(a, allp, [i], meta, done, asker, con, call)[0]


def units_of(a, allp, picked, meta, asker, out, call: float) -> list:
    """SCHOLAR_V2_2026_10_14: the picked verses as sentences (lists of places in allp). One groups call reads up to
    GROUP_WINDOW verses that follow one another; without --groups, or when its answer does not fit, one verse each."""
    if not getattr(a, "groups", False):
        return [[i] for i in picked]
    runs, cur = [], []
    for i in picked:
        if cur and (i != cur[-1] + 1 or len(cur) >= GROUP_WINDOW):
            runs.append(cur)
            cur = []
        cur.append(i)
    if cur:
        runs.append(cur)
    units = []
    for r_ in runs:
        if len(r_) == 1 or asker.spent + call > a.max_usd:
            units.extend([i] for i in r_)
            continue
        try:
            d, _c = asker.ask("groups", groups_message(meta, [allp[i] for i in r_]))
        except CallFailed:
            d = None
        got = parse_groups(d, [ref_of(allp[i]) for i in r_], r_)
        out["grouped"] += sum(1 for g in got if len(g) > 1)
        units.extend(got)
    return units


COLS = ("passage_id", "doc_code", "page_no", "idx", "verse_ref", "src_hash", "version", "translation", "notes", "doubts",
        "draft", "critique", "passes", "fidelity", "fluency", "judge_reason", "working_fidelity", "working_fluency",
        "status", "engine", "judge_engine", "prompt_version", "cost_usd", "created_at",
        "group_ref", "group_translation", "moved", "compare", "compare_better")   # SCHOLAR_V2_2026_10_14


def store(con, rec: dict) -> int:
    for k in range(5):   # CLAUDE_ENGINE_2026_10_15: runs side by side may number the same verse at once: number it again
        v = (con.execute("SELECT MAX(version) FROM scholar_translations WHERE passage_id = ?",
                         (rec["passage_id"],)).fetchone()[0] or 0) + 1
        rec["version"] = v
        try:
            con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(COLS), ",".join("?" * len(COLS))),
                        [rec.get(c) for c in COLS])
            break
        except sqlite3.IntegrityError:
            if k == 4:
                raise
            con.rollback()
            time.sleep(0.2 * (k + 1))
    if rec["status"] == "passed":   # the glossary grows only from verses that passed
        for g in rec.get("_glossary") or []:
            con.execute("INSERT OR IGNORE INTO scholar_glossary(doc_code, term, rendering, kind, note, source, created_at) "
                        "VALUES (?,?,?,?,?,?,?)", (rec["doc_code"], g["term"], g["rendering"], g["kind"], g["note"],
                                                   "scholar", rec["created_at"]))
    con.commit()
    return v


def run(a, allp: list, picked: list, meta: dict, done: dict, asker, con, price: dict, budget_ok=None) -> dict:
    out = {"passed": [], "flagged": [], "source_doubt": [], "failed": [], "stopped": "", "spent": 0.0, "grouped": 0,
           "split": 0}   # SCHOLAR_V21_2026_10_14: split, the sentences that failed whole and went verse by verse
    logp = Path(a.log_dir) / ("%s_%s.jsonl" % (re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc),
                                              datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    logp.parent.mkdir(parents=True, exist_ok=True)
    out["log"] = str(logp)
    units = units_of(a, allp, picked, meta, asker, out, price["call"])   # SCHOLAR_V2_2026_10_14: sentences
    fails = n = 0
    queue = list(units)   # SCHOLAR_V21_2026_10_14: a sentence that fails whole goes back verse by verse
    while queue:
        u = queue.pop(0)
        xs = [allp[i] for i in u]
        need = price["typical"] * len(u)
        if budget_ok is not None and not budget_ok(con, need):
            out["stopped"] = (getattr(budget_ok, "why", "") or   # CLAUDE_ENGINE_2026_10_15: the credit's own
                              "the spend cap is reached (python scripts\\set_budget.py shows it)")
            break
        if asker.spent + need > a.max_usd:
            out["stopped"] = "this run's --max-usd $%.2f is reached (%s spent)" % (a.max_usd, usd(asker.spent))
            break
        busy = busy_with(a.doc)
        if busy:
            out["stopped"] = ("the dashboard changes %s now (%s): run this when it is done"
                              % (a.doc, ", ".join(str(j.get("kind")) for j in busy)))
            break
        try:
            recs = one_unit(a, allp, u, meta, done, asker, con, price["call"])
        except CallFailed as e:
            out["spent"] = asker.spent
            if len(u) > 1:   # SCHOLAR_V21_2026_10_14: the sentence failed whole: each of its verses alone
                out["split"] += 1
                print("  %s to %s: the sentence failed (%s); each verse alone" % (ref_of(xs[0]), ref_of(xs[-1]), e))
                queue[0:0] = [[i] for i in u]
                continue
            fails += 1
            for x in xs:
                n += 1
                out["failed"].append(ref_of(x))
                with open(logp, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"doc": a.doc, "where": ref_of(x), "passage_id": x["id"], "result": "failed",
                                        "error": str(e), "mark": MARK}, ensure_ascii=False) + "\n")
                print("  (%d/%d) %s: failed (%s)" % (n, len(picked), ref_of(x), e))
            if fails >= 3:
                out["stopped"] = "three verses running failed: the API (or the key) is not answering"
                break
            continue
        fails = 0
        out["spent"] = asker.spent
        for rec, x in zip(recs, xs):
            n += 1
            v = store(con, rec)
            done[x["id"]] = dict(rec, version=v)
            out[rec["status"]].append(ref_of(x))
            print("  (%d/%d) %s  %-12s fidelity %s, fluency %s (the working English: %s, %s)  %d pass%s  %s%s%s"
                  % (n, len(picked), ref_of(x), rec["status"], rec["fidelity"], rec["fluency"], rec["working_fidelity"],
                     rec["working_fluency"], rec["passes"], "" if rec["passes"] == 1 else "es", usd(rec["cost_usd"]),
                     ("  (one sentence: %s)" % rec["group_ref"]) if rec.get("group_ref") else "",
                     (("  [the second judge: %s]" % rec["compare_better"]) if rec.get("compare_better") else "")
                     + (("  [the audit: %s]" % rec["_audit"]) if rec.get("_audit") else "")))   # AUDIT_2026_10_15
            log = {k: rec[k] for k in COLS if k not in ("draft",)}
            log.update(version=v, where=ref_of(x), mark=MARK, working_english=x.get("english") or "", draft=rec["draft"])
            with open(logp, "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
    out["spent"] = asker.spent
    return out


# --------------------------------------------------------------------------------------------- a person's word
def review(con, a, allp: list) -> int:
    refs = [r.strip() for r in a.review.split(",") if r.strip()]
    by_ref = {}
    for x in allp:
        by_ref.setdefault(ref_of(x), x)
    done = latest_rows(con, a.doc)
    n = 0
    for r in refs:
        x = by_ref.get(r)
        row = done.get(x["id"]) if x else None
        if not row:
            print("  %s: no scholarly English to review" % r)
            continue
        if not current(row, x):
            print("  %s: stale (its Sanskrit changed since version %s): translate it again first" % (r, row["version"]))
            continue
        con.execute("UPDATE scholar_translations SET reviewed_by = ?, reviewed_at = ?, review_verdict = ?, review_note = ? "
                    "WHERE id = ?", (a.by, now(), a.verdict, a.note or "", row["id"]))
        n += 1
        print("  %s: version %s %s by %s" % (r, row["version"], "accepted" if a.verdict == "accept" else "rejected", a.by))
    con.commit()
    return n


def add_term(con, a) -> None:
    con.execute("INSERT INTO scholar_glossary(doc_code, term, rendering, kind, note, source, created_at) VALUES "
                "(?,?,?,?,?,?,?) ON CONFLICT(doc_code, term) DO UPDATE SET rendering = excluded.rendering, kind = "
                "excluded.kind, note = excluded.note, source = 'person', created_at = excluded.created_at",
                (a.doc, a.term.strip(), (a.rendering or a.term).strip(), a.kind or "", a.note or "", "person", now()))
    con.commit()


# --------------------------------------------------------------------------------------------- the pages
_CSS = """
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#8a7d66;
--ok:#7cc497;--mid:#d9b36a;--lo:#e09a9a;--blue:#a9c7e8}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.sch{max-width:1200px;margin:0 auto;padding:18px 16px 60px}
.intro{color:var(--muted);font-size:13px;line-height:1.6;max-width:920px;margin-bottom:6px}
.intro b{color:var(--cream)}
.sum{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 18px}
.chip{border:1px solid var(--border);border-radius:7px;padding:3px 9px;font-size:12px;color:var(--cream)}
.chip b{color:var(--gold)}
.v{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:12px}
.vh{display:flex;gap:10px;flex-wrap:wrap;align-items:baseline;font-size:12px;color:var(--muted);margin-bottom:10px}
.vh .ref{color:var(--gold);font-weight:700;font-size:13px;text-decoration:none}
.st{border-radius:5px;padding:1px 7px;font-size:11px;font-weight:600;border:1px solid var(--border)}
.st.passed{color:var(--ok);border-color:#2f6b45}.st.flagged{color:var(--mid);border-color:#6b5420}
.st.source_doubt{color:var(--lo);border-color:#7a2f2f}.st.stale{color:var(--muted)}
.st.accept{color:var(--blue);border-color:#3a5a7a}.st.reject{color:var(--lo);border-color:#7a2f2f}
.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:18px}
@media(max-width:820px){.cols{grid-template-columns:1fr}}
.sa{font-family:'Noto Serif Devanagari','Noto Sans Devanagari',serif;font-size:17px;line-height:1.75;white-space:pre-wrap;word-break:break-word}
.ia{font-family:'EB Garamond',serif;font-style:italic;color:var(--muted);font-size:15px;line-height:1.5;margin-top:6px;white-space:pre-wrap;word-break:break-word}
.lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px}
.en{font-family:'EB Garamond',serif;font-size:18px;line-height:1.6}
.en sup{font-family:'Inter',sans-serif;font-size:10px;color:var(--gold)}
.notes{margin:8px 0 0 20px;font-size:14px;line-height:1.5;color:#d8ceb6;font-family:'EB Garamond',serif}
.notes .k{color:var(--muted);font-size:10.5px;font-family:'Inter',sans-serif;text-transform:uppercase;letter-spacing:.04em}
.doubt{margin-top:8px;font-size:12.5px;line-height:1.5;color:var(--mid)}
details{margin-top:10px;font-size:12.5px;color:var(--muted);line-height:1.5}
summary{cursor:pointer}
.wk{font-family:'EB Garamond',serif;font-size:15.5px;color:#bfb49c;margin:6px 0}
.iss{margin:4px 0 0 18px}.iss .major{color:var(--lo)}
.pager{display:flex;gap:14px;margin-top:16px}.pager a{color:var(--gold);font-size:13px}
code{background:var(--card2);padding:2px 6px;border-radius:4px;font-size:12px;color:var(--cream);word-break:break-all}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;padding:6px 8px;border-bottom:1px solid var(--border)}
td{padding:7px 8px;border-bottom:1px solid var(--border)}
td.num{text-align:right;white-space:nowrap}
td a{color:var(--cream);font-weight:600}
.wrap{overflow-x:auto}
@media print{:root{--bg:#fff;--card:#fff;--card2:#f4f1ea;--border:#ccc;--cream:#111;--muted:#555;--gold:#7a5a10}
header,.pager,details{display:none}.v{break-inside:avoid}}
.vr{font-family:'Inter',sans-serif;font-size:9.5px;color:var(--muted);vertical-align:super;margin:0 3px 0 1px}
.gv{margin-bottom:10px}.gv .vref{font-size:11px;color:var(--gold);font-weight:600}
.cmp{border-radius:5px;padding:1px 7px;font-size:11px;border:1px solid var(--border)}
.cmp.better{color:var(--ok);border-color:#2f6b45}.cmp.worse{color:var(--lo);border-color:#7a2f2f}.cmp.same{color:var(--muted)}
.prose{max-width:760px;margin:0 auto;font-family:'EB Garamond',serif;font-size:19px;line-height:1.75}
.prose h2{font-family:'Inter',sans-serif;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);margin:34px 0 14px}
.prose p{margin:0 0 .9em;text-indent:1.4em}.prose h2+p{text-indent:0}
.prose sup{font-family:'Inter',sans-serif;font-size:10px;color:var(--gold)}
.fl{text-decoration:underline dotted var(--mid);text-underline-offset:3px}
.fn{margin:14px 0 0 22px;font-size:14.5px;line-height:1.5;color:#d8ceb6}.fn .r{color:var(--muted);font-family:'Inter',sans-serif;font-size:10.5px}
"""


def _page(title: str, body: str, nav: bool) -> str:
    e = html.escape
    links = ('<a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/path">The path</a>'
             '<a href="/redeem">What is redeemed</a><a href="/scholar">Scholarly English</a>') if nav else ""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"/>'
            '<meta name="viewport" content="width=device-width,initial-scale=1"/><title>%s</title>'
            '<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital@0;1&family=Inter:wght@400;600;700&'
            'family=Noto+Serif+Devanagari&display=swap" rel="stylesheet"/><style>%s</style></head><body>'
            '<header>%s<h1>%s</h1></header><main class="sch">%s</main></body></html>'
            % (e(title), _CSS, links, e(title), body))


def _english_html(text: str, notes: list) -> str:
    """The translation, *term* in italics, each note's number after its anchor's first appearance."""
    s = re.sub(r"\*([^*\n]{1,80})\*", r"<em>\1</em>", html.escape(text or ""))
    for k, n in enumerate(notes, 1):
        mark = '<sup>%d</sup>' % k
        a = html.escape(n.get("anchor") or "")
        pos = s.find(a) if a else -1
        if pos >= 0:
            s = s[:pos + len(a)] + mark + s[pos + len(a):]
        else:
            s += mark
    return s


def _loads(s, default):
    try:
        v = json.loads(s) if s else default
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _safe(doc: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", doc)


def _units(rows: list) -> list:
    """SCHOLAR_V2_2026_10_14: rows in order, the rows of one sentence (one group_ref, made together) as one list."""
    out, i = [], 0
    while i < len(rows):
        r = rows[i]
        j = i + 1
        if r.get("group_ref"):
            while (j < len(rows) and rows[j].get("group_ref") == r["group_ref"]
                   and rows[j].get("created_at") == r.get("created_at")):
                j += 1
        out.append(rows[i:j])
        i = j
    return out


def _marks_html(pairs: list, notes: list, base: int = 0) -> str:
    """SCHOLAR_V2_2026_10_14: an English from its parts [(ref, English)], each opened by its verse's number, *term* in
    italics, each note's number (from base + 1) after its anchor's first appearance."""
    em = lambda t: re.sub(r"\*([^*\n]{1,80})\*", r"<em>\1</em>", html.escape(t or ""))
    s = " ".join('<span class="vr">%s</span>%s' % (html.escape(str(r).split(".")[-1]), em(t)) for r, t in pairs)
    for k, n in enumerate(notes, base + 1):
        mark = '<sup>%d</sup>' % k
        a_ = html.escape(n.get("anchor") or "")
        pos = s.find(a_) if a_ else -1
        s = (s[:pos + len(a_)] + mark + s[pos + len(a_):]) if pos >= 0 else s + mark
    return s


def _compare_html(c) -> tuple:
    """SCHOLAR_V2_2026_10_14: (the head's chip, the fold's lines) of the second judge's verdict."""
    if not isinstance(c, dict):
        return "", ""
    e = html.escape
    word = {"scholarly": "more faithful than the working English", "working": "the working English is more faithful",
            "equal": "as faithful as the working English"}.get(c.get("better"), "")
    cls = {"scholarly": "better", "working": "worse"}.get(c.get("better"), "same")
    chip = ('<span class="cmp %s" title="the second judge: %s">%s</span>'
            % (cls, e(c.get("reason") or "", quote=True), e(word))) if word else ""
    lines = ""
    for side, label in (("scholarly", "the scholarly English"), ("working", "the working English")):
        v = c.get(side) or {}
        errs = "".join('<li class="%s">%s, at %s: %s</li>' % (e(x.get("severity", ""), quote=True), e(x.get("severity", "")),
                                                              e(x.get("where", "")), e(x.get("error", "")))
                       for x in v.get("errors") or [])
        lines += ('<div>The second judge on %s: fidelity %s%s</div>'
                  % (label, v.get("fidelity"), ('<ul class="iss">%s</ul>' % errs) if errs else ", no error found"))
    lines += '<div>Its verdict: %s</div>' % e(c.get("reason") or "")
    return chip, lines


def _crits_html(crits: list) -> str:
    e = html.escape
    iss = ""
    for k, c in enumerate(crits, 1):
        if not isinstance(c, dict):
            continue
        items = "".join('<li class="%s">%s %s, at %s: %s</li>' % (e(i.get("severity", ""), quote=True),
                                                                   e(i.get("severity", "")), e(i.get("type", "")),
                                                                   e(i.get("where", "")), e(i.get("fix", "")))
                        for i in c.get("issues") or [])
        iss += ('<div>%s: fidelity %s, completeness %s, %s%s</div>'
                % (("Critic, reading %d" % k) if not c.get("by") else ("The audit by %s" % e(str(c["by"]))),
                   c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                   ('<ul class="iss">%s</ul>' % items) if items else ""))   # AUDIT_2026_10_15
    return iss


def _ws(t) -> str:
    return " ".join(str(t or "").split())


def _inline(u: list) -> bool:
    """SCHOLAR_V21_2026_10_14: a sentence's English is shown part by part after each verse's number only when its parts
    joined are its passage (scholar-v2's rows); a scholar-v2.1 passage, in the order English needs, is shown whole."""
    if len(u) < 2 or not any(r.get("translation") for r in u[1:]):
        return False
    whole = u[0].get("group_translation")
    return not whole or _ws(" ".join(r.get("translation") or "" for r in u)) == _ws(whole)


def _range(u: list) -> str:
    """SCHOLAR_V21_2026_10_14: '1.1.15\u201319', the first verse and the last one's number (_marks_html shows what follows
    the last dot)."""
    a_, b_ = str(u[0].get("verse_ref") or ""), str(u[-1].get("verse_ref") or "")
    return a_ if len(u) < 2 or a_ == b_ else "%s\u2013%s" % (a_, b_.split(".")[-1])


def _group_article(u: list) -> str:
    """SCHOLAR_V2_2026_10_14: one Sanskrit sentence over several verses, as one block."""
    e = html.escape
    r0 = u[0]
    stale = any(r.get("p_text") is None or src_hash(r.get("p_text")) != r.get("src_hash") for r in u)
    st = "stale" if stale else (r0.get("status") or "")
    notes = _loads(r0.get("notes"), [])
    chip, cmp_lines = _compare_html(_loads(r0.get("compare"), {}) or None)
    head = ('<a class="ref" id="v-%s" href="#v-%s">%s to %s</a><span>one sentence</span><span class="st %s">%s</span>'
            % (e(r0["verse_ref"] or "", quote=True), e(r0["verse_ref"] or "", quote=True), e(r0["verse_ref"] or ""),
               e(u[-1]["verse_ref"] or ""), e(st, quote=True), e(st.replace("_", " "))))
    for r in u:
        if r.get("review_verdict"):
            head += '<span class="st %s">%s %s by %s</span>' % (e(r["review_verdict"], quote=True), e(r["verse_ref"] or ""), e(
                "accepted" if r["review_verdict"] == "accept" else "rejected"), e(r.get("reviewed_by") or "?"))
    head += chip + ('<span>the judge: fidelity %s, fluency %s%s</span><span>%s pass%s</span><span>%s</span><span>v%s</span>'
                    % (r0.get("fidelity") if r0.get("fidelity") is not None else "?",
                       r0.get("fluency") if r0.get("fluency") is not None else "?",
                       (" (the working English: %s, %s)" % (r0.get("working_fidelity"), r0.get("working_fluency")))
                       if r0.get("working_fidelity") is not None else "",
                       r0.get("passes") or 1, "" if (r0.get("passes") or 1) == 1 else "es",
                       usd(sum(r.get("cost_usd") or 0 for r in u)), r0.get("version")))
    left = "".join('<div class="gv"><span class="vref">%s</span><div class="sa">%s</div><div class="ia">%s</div></div>'
                   % (e(r["verse_ref"] or ""), e((r.get("p_text") or "").strip()), e((r.get("p_iast") or "").strip()))
                   for r in u)
    if _inline(u):
        english = _marks_html([(r["verse_ref"], r.get("translation") or "") for r in u], notes)
    else:   # SCHOLAR_V21_2026_10_14: the passage whole, after its verse range; its segments under the fold
        english = _marks_html([(_range(u), r0.get("group_translation") or r0.get("translation") or "")], notes)
    notes_html = ("<ol class=\"notes\">%s</ol>" % "".join(
        '<li><span class="k">%s</span> <b>%s</b>: %s</li>' % (e(n.get("kind") or ""), e(n.get("anchor") or ""),
                                                               e(n.get("note") or "")) for n in notes)) if notes else ""
    extra = ""
    if r0.get("doubts"):
        extra += '<div class="doubt">Doubts: %s</div>' % e(r0["doubts"])
    if r0.get("moved"):
        extra += '<div class="doubt">Moved between the verses: %s</div>' % e(r0["moved"])
    if not _inline(u) and any(r.get("translation") for r in u[1:]):   # SCHOLAR_V21_2026_10_14
        extra += ('<details class="segs"><summary>Verse by verse: the words of the passage that render each verse'
                  '</summary>%s</details>' % "".join('<p class="wk"><span class="vr">%s</span>%s</p>'
                                                     % (e(r["verse_ref"] or ""), e(r.get("translation") or "-"))
                                                     for r in u))
    working = "".join('<p class="wk"><span class="vr">%s</span>%s</p>' % (e(r["verse_ref"] or ""), e(r.get("p_english") or "-"))
                      for r in u)
    earlier = "".join('<p class="wk"><span class="vr">%s</span>%s</p>' % (e(r["verse_ref"] or ""), e(r["prev_translation"]))
                      for r in u if r.get("prev_translation"))
    det = ('<details><summary>The working English, the first draft, the critic, the second judge</summary>'
           '<div class="lbl" style="margin-top:8px">The working English (on the site)</div>%s%s%s%s<div>The judge: %s</div>'
           '%s</details>'
           % (working, ('<div class="lbl">The first draft</div><p class="wk">%s</p>' % e(r0["draft"]))
              if r0.get("draft") and r0.get("draft") != r0.get("group_translation") else "",
              ('<div class="lbl">The earlier version (%s)</div>%s' % (e(u[0].get("prev_prompt") or "?"), earlier))
              if earlier else "", _crits_html(_loads(r0.get("critique"), [])), e(r0.get("judge_reason") or ""),
              cmp_lines))
    return ('<article class="v"><div class="vh">%s</div><div class="cols"><div>%s</div><div><div class="lbl">Scholarly '
            'English, one sentence over %d verses</div><div class="en">%s</div>%s%s%s</div></div></article>'
            % (head, left, len(u), english, notes_html, extra, det))


def render_doc(con, doc: str, offset: int = 0, limit=200, nav: bool = False) -> str:
    """One text's scholarly English beside its Sanskrit and its working English, verse by verse (a sentence over
    several verses as one block: SCHOLAR_V2_2026_10_14)."""
    e = html.escape
    if not has_table(con, "scholar_translations"):
        rows = []
    else:
        q = ("SELECT s.*, p.text AS p_text, p.iast AS p_iast, p.translation AS p_english, (SELECT s2.translation FROM "
             "scholar_translations s2 WHERE s2.passage_id = s.passage_id AND s2.version = s.version - 1) AS "
             "prev_translation, (SELECT s2.prompt_version FROM scholar_translations s2 WHERE s2.passage_id = "
             "s.passage_id AND s2.version = s.version - 1) AS prev_prompt FROM scholar_translations s LEFT "
             "JOIN passages p ON p.id = s.passage_id WHERE s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM "
             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY COALESCE(p.page_no, s.page_no), "
             "COALESCE(p.idx, s.idx), s.id")   # SCHOLAR_V21_2026_10_14: the passage's place now
        cur = con.execute(q + (" LIMIT %d OFFSET %d" % (int(limit), int(offset)) if limit else ""), (doc, doc))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
    total = tot_cost = 0
    counts = {}
    sc_f, wk_f = [], []
    if has_table(con, "scholar_translations"):
        for st, fid, wfid, h, c, rv, ptext in con.execute(
                "SELECT s.status, s.fidelity, s.working_fidelity, s.src_hash, s.cost_usd, s.review_verdict, p.text FROM "
                "scholar_translations s LEFT JOIN passages p ON p.id = s.passage_id WHERE s.doc_code = ? AND s.id IN "
                "(SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY passage_id)", (doc, doc)):
            total += 1
            key = "stale" if (ptext is None or src_hash(ptext) != h) else st
            counts[key] = counts.get(key, 0) + 1
            if rv:
                counts["review_" + rv] = counts.get("review_" + rv, 0) + 1
            if fid is not None and wfid is not None:
                sc_f.append(fid); wk_f.append(wfid)
        tot_cost = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM scholar_translations WHERE doc_code = ?",
                               (doc,)).fetchone()[0] or 0.0
    if not total:
        body = ('<p class="intro">No scholarly English for <b>%s</b> yet. Its dry run says what would be sent and what it '
                'costs (free): <code>python scripts\\scholar_translate.py --doc %s --pages 1 --limit 24</code></p>'
                % (e(doc), e(doc)))
        return _page("Scholarly English: " + doc, body, nav)
    label = {"passed": "passed", "flagged": "flagged (a person reads it)", "source_doubt": "source doubts",
             "stale": "stale (the Sanskrit changed)", "review_accept": "accepted by a person",
             "review_reject": "rejected by a person"}
    chips = '<span class="chip">verses <b>%d</b></span>' % total + "".join(
        '<span class="chip">%s <b>%d</b></span>' % (e(label[k]), counts[k]) for k in label if counts.get(k))
    chips += '<span class="chip">spent <b>%s</b> (%s a verse)</span>' % (usd(tot_cost), usd(tot_cost / total))
    if sc_f:
        chips += ('<span class="chip">the judge\'s fidelity: scholarly <b>%.2f</b>, working <b>%.2f</b> (%d verses)</span>'
                  % (sum(sc_f) / len(sc_f), sum(wk_f) / len(wk_f), len(sc_f)))
    cols = {c_[1] for c_ in con.execute("PRAGMA table_info(scholar_translations)")}
    if "compare_better" in cols:   # SCHOLAR_V2_2026_10_14
        cb = dict(con.execute("SELECT compare_better, COUNT(*) FROM scholar_translations WHERE doc_code = ? AND id IN "
                              "(SELECT MAX(id) FROM scholar_translations WHERE doc_code = ? GROUP BY passage_id) AND "
                              "compare_better IS NOT NULL GROUP BY compare_better", (doc, doc)).fetchall())
        if cb:
            chips += ('<span class="chip">the second judge: the scholarly English more faithful <b>%d</b>, as faithful '
                      '<b>%d</b>, less <b>%d</b></span>' % (cb.get("scholarly", 0), cb.get("equal", 0), cb.get("working", 0)))
    prose = ("/scholar/%s/prose" % doc) if nav else ("scholar_%s_prose.html" % _safe(doc))
    intro = ('<p class="intro">The scholarly English of <b>%s</b>, beside its Sanskrit and the working English. Each verse, '
             'or each Sanskrit sentence that runs over several verses, was drafted with its context and the text\'s '
             'glossary, read word by word by a critic, revised where the critic asked, and judged; a second judge read it '
             'beside the working English, not told which is which. <b>Passed</b>: the critic accepts it and the judge '
             'gives 4 or more for fidelity and fluency. <b>Flagged</b>: a person reads it. <b>Source doubt</b>: the '
             'Sanskrit itself looks corrupt or misread; another edition is wanted for that verse. The working English on '
             'the site is unchanged. <a href="%s" style="color:var(--gold)">Read it as prose</a>.</p>' % (e(doc), e(prose)))
    arts = ""
    for u in _units(rows):
        if len(u) > 1 or u[0].get("group_ref"):
            arts += _group_article(u)
            continue
        r = u[0]
        stale = r.get("p_text") is None or src_hash(r.get("p_text")) != r.get("src_hash")
        notes = _loads(r.get("notes"), [])
        crits = _loads(r.get("critique"), [])
        st = "stale" if stale else (r.get("status") or "")
        head = ('<a class="ref" id="v-%s" href="#v-%s">%s</a><span class="st %s">%s</span>'
                % (e(r["verse_ref"] or "", quote=True), e(r["verse_ref"] or "", quote=True), e(r["verse_ref"] or ""),
                   e(st, quote=True), e(st.replace("_", " "))))
        if r.get("review_verdict"):
            head += '<span class="st %s">%s by %s</span>' % (e(r["review_verdict"], quote=True), e(
                "accepted" if r["review_verdict"] == "accept" else "rejected"), e(r.get("reviewed_by") or "?"))
        head += ('<span>the judge: fidelity %s, fluency %s%s</span><span>%s pass%s</span><span>%s</span><span>v%s</span>'
                 % (r.get("fidelity") if r.get("fidelity") is not None else "?",
                    r.get("fluency") if r.get("fluency") is not None else "?",
                    (" (the working English: %s, %s)" % (r.get("working_fidelity"), r.get("working_fluency")))
                    if r.get("working_fidelity") is not None else "",
                    r.get("passes") or 1, "" if (r.get("passes") or 1) == 1 else "es", usd(r.get("cost_usd") or 0),
                    r.get("version")))
        notes_html = ("<ol class=\"notes\">%s</ol>" % "".join(
            '<li><span class="k">%s</span> <b>%s</b>: %s</li>' % (e(n.get("kind") or ""), e(n.get("anchor") or ""),
                                                                   e(n.get("note") or "")) for n in notes)) if notes else ""
        doubt = '<div class="doubt">Doubts: %s</div>' % e(r["doubts"]) if r.get("doubts") else ""
        iss = ""
        for k, c in enumerate(crits, 1):
            if not isinstance(c, dict):
                continue
            items = "".join('<li class="%s">%s %s, at %s: %s</li>' % (e(i.get("severity", ""), quote=True),
                                                                       e(i.get("severity", "")), e(i.get("type", "")),
                                                                       e(i.get("where", "")), e(i.get("fix", "")))
                            for i in c.get("issues") or [])
            iss += ('<div>%s: fidelity %s, completeness %s, %s%s</div>'
                    % (("Critic, reading %d" % k) if not c.get("by") else ("The audit by %s" % e(str(c["by"]))),
                       c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                       ('<ul class="iss">%s</ul>' % items) if items else ""))   # AUDIT_2026_10_15
        chip, cmp_lines = _compare_html(_loads(r.get("compare"), {}) or None)   # SCHOLAR_V2_2026_10_14
        if chip:
            head += chip
        if r.get("prev_translation"):
            cmp_lines += ('<div class="lbl">The earlier version (%s)</div><p class="wk">%s</p>'
                          % (e(r.get("prev_prompt") or "?"), e(r["prev_translation"])))
        det = ('<details><summary>The working English, the first draft, the critic</summary><div class="lbl" '
               'style="margin-top:8px">The working English (on the site)</div><p class="wk">%s</p>%s%s<div>The judge: %s'
               '</div>%s</details>'
               % (e(r.get("p_english") or "-"),
                  ('<div class="lbl">The first draft</div><p class="wk">%s</p>' % e(r["draft"]))
                  if r.get("draft") and r.get("draft") != r.get("translation") else "", iss, e(r.get("judge_reason") or ""),
                  cmp_lines))
        arts += ('<article class="v"><div class="vh">%s</div><div class="cols"><div><div class="sa">%s</div>'
                 '<div class="ia">%s</div></div><div><div class="lbl">Scholarly English</div><div class="en">%s</div>%s%s%s'
                 '</div></div></article>'
                 % (head, e((r.get("p_text") or "").strip()), e((r.get("p_iast") or "").strip()),
                    _english_html(r.get("translation") or "", notes), notes_html, doubt, det))
    pager = ""
    if limit:
        q = lambda o: "?offset=%d" % max(0, o)
        if offset > 0:
            pager += '<a href="%s">&larr; the verses before</a>' % q(offset - limit)
        if offset + len(rows) < total:
            pager += '<a href="%s">the verses after &rarr;</a>' % q(offset + limit)
        pager = '<nav class="pager">%s</nav>' % pager if pager else ""
    body = intro + '<div class="sum">%s</div>' % chips + arts + pager
    return _page("Scholarly English: " + doc, body, nav)


_SPEECH = re.compile(r"^[A-Z][^.:;]{0,60} said:")


def render_prose(con, doc: str, nav: bool = False) -> str:
    """SCHOLAR_V2_2026_10_14: the scholarly English read as prose, chapter by chapter, as a book reads: a sentence over
    verses whole, the verse numbers small, a new paragraph where a speaker begins, the notes at each chapter's end. A
    flagged passage not yet accepted by a person is underlined; a stale one is left out."""
    e = html.escape
    rows = []
    if has_table(con, "scholar_translations"):
        cur = con.execute("SELECT s.*, p.text AS p_text, p.chapter AS p_chapter FROM scholar_translations s LEFT JOIN "
                          "passages p ON p.id = s.passage_id WHERE s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM "
                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY COALESCE(p.page_no, "
                          "s.page_no), COALESCE(p.idx, s.idx), s.id", (doc, doc))   # SCHOLAR_V21_2026_10_14
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
    live = [r for r in rows if r.get("p_text") is not None and src_hash(r["p_text"]) == r.get("src_hash")]
    back = ("/scholar/%s" % doc) if nav else ("scholar_%s.html" % _safe(doc))
    if not live:
        return _page("%s as prose" % doc, '<p class="intro">No current scholarly English for <b>%s</b> yet. '
                                          '<a href="%s" style="color:var(--gold)">The verses</a>.</p>' % (e(doc), e(back)), nav)
    body = ('<p class="intro">The scholarly English of <b>%s</b>, read as prose, chapter by chapter: the verse numbers '
            'small, a sentence that runs over verses whole, the notes at the end of each chapter. A passage underlined '
            'is flagged: a person reads it. %s <a href="%s" style="color:var(--gold)">The verses, beside the Sanskrit'
            '</a>.</p>' % (e(doc), ("%d verse(s) whose Sanskrit has changed since are left out." % (len(rows) - len(live)))
                           if len(rows) > len(live) else "", e(back)))
    chapters = []
    for u in _units(live):
        if not chapters or chapters[-1][0] != u[0]["page_no"]:
            chapters.append((u[0]["page_no"], []))
        chapters[-1][1].append(u)
    for page, us in chapters:
        fns, paras, cur_p = [], [], []
        for u in us:
            r0 = u[0]
            notes = _loads(r0.get("notes"), [])
            if _inline(u):
                pairs = [(r["verse_ref"], r.get("translation") or "") for r in u]
            else:   # SCHOLAR_V21_2026_10_14: the passage whole, after its verse range
                pairs = [(_range(u), r0.get("group_translation") or r0.get("translation") or "")]
            pairs = [(ref, re.sub(r"\s*//\s*", " ", t).strip()) for ref, t in pairs]
            text = _marks_html(pairs, notes, base=len(fns))
            fns.extend((r0["verse_ref"], n) for n in notes)
            if r0.get("status") in ("flagged", "source_doubt") and r0.get("review_verdict") != "accept":
                text = '<span class="fl" title="%s: a person reads it">%s</span>' % (e(r0["status"]), text)
            if cur_p and (_SPEECH.match(pairs[0][1] or "") or len(cur_p) >= 8):
                paras.append(cur_p)
                cur_p = []
            cur_p.append(text)
        if cur_p:
            paras.append(cur_p)
        fn_html = ('<ol class="fn">%s</ol>' % "".join('<li><span class="r">%s</span> <b>%s</b>: %s</li>'
                                                    % (e(ref or ""), e(n.get("anchor") or ""), e(n.get("note") or ""))
                                                    for ref, n in fns)) if fns else ""
        body += ('<section class="prose"><h2>Chapter %s</h2>%s%s</section>'
                 % (e(str(us[0][0].get("p_chapter") or page)), "".join("<p>%s</p>" % " ".join(p) for p in paras), fn_html))
    return _page("%s as prose" % doc, body, nav)


def render_index(con, nav: bool = False) -> str:
    e = html.escape
    rows = []
    if has_table(con, "scholar_translations"):
        rows = con.execute(
            "SELECT s.doc_code, COUNT(*), SUM(CASE WHEN s.status='passed' THEN 1 ELSE 0 END), SUM(CASE WHEN "
            "s.status='flagged' THEN 1 ELSE 0 END), SUM(CASE WHEN s.status='source_doubt' THEN 1 ELSE 0 END), SUM(CASE "
            "WHEN s.review_verdict='accept' THEN 1 ELSE 0 END), AVG(s.fidelity), AVG(s.working_fidelity), MAX(s.created_at) "
            "FROM scholar_translations s WHERE s.id IN (SELECT MAX(id) FROM scholar_translations GROUP BY passage_id) "
            "GROUP BY s.doc_code ORDER BY s.doc_code").fetchall()
        spent = dict(con.execute("SELECT doc_code, SUM(cost_usd) FROM scholar_translations GROUP BY doc_code").fetchall())
    intro = ('<p class="intro">A scholarly English beside the working one, verse by verse: the verse with its context and '
             'the text\'s glossary, a draft, a critic who reads it word by word, revisions, and a judge who scores it and '
             'the working English of the same verse. Made by <code>scripts\\scholar_translate.py</code> (a dry run first, '
             'free); this page only reads. The working English on the site is not changed.</p>')
    if not rows:
        body = intro + ('<p class="intro">None yet. The pilot is the first chapter of the Mah\u0101bh\u0101rata\'s first '
                        'book (the BORI Critical Edition e-text): <code>python scripts\\scholar_translate.py --doc MBh01 '
                        '--pages 1 --limit 24</code> (the dry run), then the command it prints.</p>')
        return _page("Scholarly English", body, nav)
    trs = ""
    for doc, n, ok, fl, sd, acc, fid, wfid, last in rows:
        trs += ('<tr><td><a href="/scholar/%s">%s</a></td><td class="num">%d</td><td class="num">%d</td><td class="num">%d'
                '</td><td class="num">%d</td><td class="num">%d</td><td class="num">%s</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td></tr>'
                % (e(doc, quote=True), e(doc), n, ok or 0, fl or 0, sd or 0, acc or 0,
                   ("%.2f" % fid) if fid is not None else "-", ("%.2f" % wfid) if wfid is not None else "-",
                   usd(spent.get(doc) or 0.0), e(str(last or "")[:16].replace("T", " "))))
    body = intro + ('<div class="wrap"><table><thead><tr><th>Text</th><th>Verses</th><th>Passed</th><th>Flagged</th>'
                    '<th>Source doubts</th><th>Accepted by a person</th><th>Fidelity, scholarly</th><th>Fidelity, working'
                    '</th><th>Spent</th><th>Last</th></tr></thead><tbody>%s</tbody></table></div>' % trs)
    return _page("Scholarly English", body, nav)


# --------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--pages", default=None, help="pages (a Mahabharata book's chapters): 1 or 1-3,5")
    ap.add_argument("--from-ref", default=None, help="start at this verse (1.1.8)")
    ap.add_argument("--only-page", type=int, default=None)
    ap.add_argument("--only-idx", type=int, default=None)
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=2, help="revisions at most, a verse")
    ap.add_argument("--engine", default=ENGINE)
    ap.add_argument("--judge-engine", default=JUDGE)
    ap.add_argument("--min-quality", type=float, default=0.35)
    ap.add_argument("--max-usd", type=float, default=1.00)
    ap.add_argument("--redo", action="store_true", help="a new version even where a current one exists")
    ap.add_argument("--show-prompt", action="store_true", help="print the first verse's prompt (free)")
    ap.add_argument("--report", action="store_true", help="write exports\\scholar_<doc>.html (free)")
    ap.add_argument("--exports", default="exports")
    ap.add_argument("--review", default=None, help="verses a person read: 1.1.8,1.1.9")
    ap.add_argument("--verdict", choices=["accept", "reject"], default="accept")
    ap.add_argument("--by", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--term", default=None, help="a person's glossary entry: the IAST term")
    ap.add_argument("--rendering", default=None)
    ap.add_argument("--kind", default=None)
    ap.add_argument("--verdicts", default=None, help="the register (default: source_verdicts.jsonl beside the database)")
    ap.add_argument("--log-dir", default="data/scholar")
    ap.add_argument("--no-groups", action="store_true", help="SCHOLAR_V2_2026_10_14: every verse alone")
    ap.add_argument("--no-compare", action="store_true", help="SCHOLAR_V2_2026_10_14: no second judge")
    ap.add_argument("--compare-engine", default=COMPARE_ENGINE, help="CLAUDE_ENGINE_2026_10_15: the second judge of a "
                    "Claude English (a Gemini model)")
    ap.add_argument("--held-ok", action="store_true", help="CLAUDE_ENGINE_2026_10_15: translate a text held from the site "
                    "while its working English is redone (in_repair); nothing is written to the site")
    ap.add_argument("--no-glossary-adds", action="store_true", help="CLAUDE_ENGINE_2026_10_15: a benchmark run; the "
                    "glossary does not grow from it")
    ap.add_argument("--title", default=None, help="CLAUDE_ENGINE_2026_10_15: the text's name in the prompts")
    ap.add_argument("--fill-engine", action="store_true", help="PILOT_FIX_2026_10_15: only this engine's own rows count "
                    "as done and as context: a run stopped half way goes on where it stopped")
    ap.add_argument("--compare-every", type=int, default=1, help="PILOT_FIX_2026_10_15: the second judge on one sentence "
                    "in N (1: every one)")
    ap.add_argument("--audit-every", type=int, default=0, help="AUDIT_2026_10_15: in a Claude run, Gemini's critic reads "
                    "one sentence in N after the critic; its reading decides the status (0: none)")
    ap.add_argument("--status", action="store_true", help="AUDIT_2026_10_15: what this text has, per engine (free)")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    a.groups, a.compare = not a.no_groups, not a.no_compare   # SCHOLAR_V2_2026_10_14
    claude = str(a.engine).startswith("anthropic:")   # CLAUDE_ENGINE_2026_10_15
    if claude:
        try:
            import claude_engine
            claude_engine.parse_engine(a.engine)
        except ValueError as e:
            print("REFUSE: --engine %s: %s" % (a.engine, e)); print("VERDICT: nothing sent"); print("NEXT: "); return 1
        if str(a.compare_engine).startswith("anthropic:") or str(a.judge_engine).startswith("anthropic:"):
            print("REFUSE: the judges of a Claude English are Gemini's (--judge-engine, --compare-engine): it is not judged "
                  "by Claude"); print("VERDICT: nothing sent"); print("NEXT: "); return 1
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    reg = register(Path(a.verdicts) if a.verdicts else Path(a.db).resolve().parent / "source_verdicts.jsonl")
    st = (reg.get(a.doc) or {}).get("status")

    if a.report:
        con = open_ro(a.db)
        try:
            page = render_doc(con, a.doc, limit=None)
            prose = render_prose(con, a.doc)   # SCHOLAR_V2_2026_10_14
        finally:
            con.close()
        out = Path(a.exports) / ("scholar_%s.html" % re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        out2 = out.with_name(out.stem + "_prose.html")
        out2.write_text(prose, encoding="utf-8")
        print("VERDICT: written %s (%d bytes), and as prose %s (%d bytes)" % (out, out.stat().st_size, out2,
                                                                               out2.stat().st_size))
        print("NEXT: start %s   (or http://127.0.0.1:5057/scholar/%s)" % (out, a.doc))
        return 0
    if getattr(a, "status", False):   # AUDIT_2026_10_15: free, read-only
        con = open_ro(a.db)
        try:
            allp = load_text(con, a.doc)
            lines = status_lines(con, a.doc, allp, a)
            cl = ""
            if any(" anthropic:" in ln for ln in lines) or claude:
                try:
                    import claude_engine
                    cl = claude_engine.credit_line(claude_engine.credit(con))
                except Exception:
                    cl = ""
        finally:
            con.close()
        print("scholar_translate.py  %s  the status of %s%s (read-only)" % (MARK, a.doc, (" pages %s" % a.pages) if a.pages
                                                                            else ""))
        for ln in lines:
            print(ln)
        if cl:
            print("  " + cl)
        print("VERDICT: %d engine(s) here" % sum(1 for ln in lines if ln.startswith("  ") and " verses (" in ln))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (the pages: the flagged first to read)" % a.doc)
        return 0
    if a.review or a.term:
        if a.review and not a.by:
            print("REFUSE: --review needs --by (who read them)"); print("VERDICT: nothing written"); print("NEXT: ")
            return 1
        import db_utils
        con = db_utils.connect(a.db)
        try:
            ensure_schema(con)
            if a.term:
                add_term(con, a)
                print("  glossary: %s = %s (%s), a person's entry: it wins over the others" % (
                    a.term, a.rendering or a.term, a.kind or "-"))
            n = review(con, a, load_text(con, a.doc)) if a.review else 0
        finally:
            con.close()
        print("VERDICT: %s%s" % (("%d verse(s) reviewed" % n) if a.review else "", "; the glossary entry kept" if a.term else ""))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --report" % a.doc)
        return 0

    con = open_ro(a.db)
    try:
        allp = load_text(con, a.doc)
        if not allp:
            print("REFUSE: %s has no passages" % a.doc); print("VERDICT: nothing to do"); print("NEXT: "); return 1
        meta = doc_meta(con, a.doc, allp, Path(a.db).resolve().parent / "raw")
        if getattr(a, "title", None):   # CLAUDE_ENGINE_2026_10_15
            meta["title"] = a.title
        done = latest_rows(con, a.doc, a.engine if getattr(a, "fill_engine", False) else None)   # PILOT_FIX_2026_10_15
        picked, left, skipped = choose(a, allp, done)
        first = None
        if picked:
            i = picked[0]
            b, af = context(allp, i, done)
            first = verse_message(meta, allp[i], b, af, glossary(con, a.doc, allp[i], b))
            first = with_apparatus(first, allp, [allp[i]])   # CLAUDE_ENGINE_2026_10_15
        price = prices(con, a, len(first or ""))
        credit = None
        if claude:   # CLAUDE_ENGINE_2026_10_15
            try:
                credit = claude_engine.credit(con)
            except RuntimeError as e:
                credit = {"error": str(e)}
    finally:
        con.close()
    print("scholar_translate.py  %s  %s   %s and its critic, up to %d revision(s); the judge %s"
          % ("%s (%s)" % (MARK3, PROMPT_VERSION), "RUN" if a.yes else "DRY RUN (nothing called, nothing written)",
             a.engine, a.rounds, a.judge_engine))
    print("  %s: %s passages; the source: %s (%s)" % (a.doc, "{:,}".format(len(allp)), meta["source"], meta["engine"] or "?"))
    if st == "in_repair" and getattr(a, "held_ok", False):   # CLAUDE_ENGINE_2026_10_15
        print("  NOTE: %s is held from the site (the register, %s: %s); --held-ok: the scholarly English writes nothing "
              "to the site or to its passages, and a row goes stale, not wrong, if its reading changes"
              % (a.doc, str((reg.get(a.doc) or {}).get("at") or "?")[:16], (reg.get(a.doc) or {}).get("reason") or ""))
    elif st in HELD:
        print("REFUSE: %s is %s (the register, %s: %s)" % (a.doc, HELD[st], str((reg.get(a.doc) or {}).get("at") or "?")[:16],
                                                           (reg.get(a.doc) or {}).get("reason") or ""))
        print("VERDICT: nothing sent, nothing written")
        print("NEXT: python scripts\\text_path.py --doc %s   (its path)" % a.doc)
        if st == "in_repair":   # CLAUDE_ENGINE_2026_10_15
            print("ALSO: " + HELD_OK)
        return 3
    if picked:
        print("  chosen: %d verse(s), %s to %s" % (len(picked), ref_of(allp[picked[0]]), ref_of(allp[picked[-1]])))
    why = {}
    for _x, w in left:
        why[w] = why.get(w, 0) + 1
    for w, n in sorted(why.items(), key=lambda kv: -kv[1]):
        print("  left out: %d (%s)" % (n, w))
    if skipped:
        print("  already done, the Sanskrit unchanged: %d (--redo makes a new version)" % len(skipped))
    if a.show_prompt and first:
        print("\n----- the system prompt (%s) -----\n%s\n----- the first verse's message -----\n%s\n-----"
              % (PROMPT_VERSION, system_for("draft", meta), first))   # CLAUDE_ENGINE_2026_10_15: as it is sent
    if not picked:
        print("VERDICT: nothing to send%s" % ("; %d left out" % len(left) if left else ""))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (what is there)" % a.doc)
        return 0
    est, most = price["typical"] * len(picked), price["most"] * len(picked)
    print("  cost: about %s a verse, up to %s with %d revisions (%s): about %s for %d, at most %s"
          % (usd(price["typical"]), usd(price["most"]), a.rounds, price["how"], usd(est), len(picked), usd(most)))
    print("  sentences: %s; the second judge: %s   (%s)" % (
        ("one over several verses is translated whole (%s)" % GROUPS_VERSION) if a.groups else "every verse alone",
        ("the scholarly and the working English side by side (%s)" % COMPARE_VERSION) if a.compare else "none",
        MARK2))
    if getattr(a, "fill_engine", False):   # PILOT_FIX_2026_10_15
        print("  --fill-engine: only %s's own rows count as done and as the context" % a.engine)
    if a.compare and getattr(a, "compare_every", 1) > 1:
        print("  the second judge: one sentence in %d (--compare-every)" % a.compare_every)
    if getattr(a, "audit_every", 0):   # AUDIT_2026_10_15
        print("  the audit: %s" % (("%s reads one sentence in %d after the critic; its reading decides the status"
                                    % (a.compare_engine, a.audit_every)) if claude else
                                   "--audit-every is for a Claude engine: nothing is audited"))
    if meta.get("agama"):   # CLAUDE_ENGINE_2026_10_15
        print("  the Agamas and Tantras: one rule more (%s): a mantra stays in IAST; a digit in a word is a footnote number"
              % AGAMA_VERSION)
    if credit is not None:
        print("  " + (claude_engine.credit_line(credit) if "error" not in credit else "the Claude credit: " + credit["error"]))
        print("  the judge %s and the second judge %s: Google's bill, in the spend cap" % (a.judge_engine, a.compare_engine))
        if "error" not in credit and (credit["expired"] or credit["left"] < est):
            print("  WARNING: the credit left ($%.2f) does not cover this run (about %s)%s"
                  % (max(0.0, credit["left"]), usd(est), "; it has expired" if credit["expired"] else ""))
    if not a.yes:
        cap = max(0.25, round(est * 1.25 + 0.005, 2))
        print("VERDICT: %d verse(s) ready, about %s; %d left out" % (len(picked), usd(est), len(left)))
        sel = (" --pages %s" % a.pages if a.pages else "") + (" --from-ref %s" % a.from_ref if a.from_ref else "") + (
            " --only-page %d" % a.only_page if a.only_page is not None else "") + (
            " --only-idx %d" % a.only_idx if a.only_idx is not None else "")
        print("NEXT: python scripts\\scholar_translate.py --doc %s%s --limit %d%s --yes --max-usd %.2f"
              % (a.doc, sel, a.limit, (" --redo" if a.redo else "") + (" --no-groups" if a.no_groups else "")
                 + (" --no-compare" if a.no_compare else "") + ((" --engine %s" % a.engine) if a.engine != ENGINE else "")
                 + (" --held-ok" if getattr(a, "held_ok", False) else "")
                 + (" --no-glossary-adds" if getattr(a, "no_glossary_adds", False) else "")
                 + (" --fill-engine" if getattr(a, "fill_engine", False) else "")   # PILOT_FIX_2026_10_15
                 + ((" --compare-every %d" % a.compare_every) if getattr(a, "compare_every", 1) > 1 else "")
                 + ((" --audit-every %d" % a.audit_every) if getattr(a, "audit_every", 0) else "")   # AUDIT_2026_10_15
                 + ((" --min-quality %.2f" % a.min_quality) if a.min_quality != 0.35 else "")
                 + ((' --title "%s"' % a.title) if getattr(a, "title", None) else ""), cap))   # CLAUDE_ENGINE_2026_10_15
        return 0
    try:
        asker = (Claude if claude else Gemini)(a, meta, None)   # first: without a key or the SDK nothing is called, and
        # the database is not opened (CLAUDE_ENGINE_2026_10_15: Claude, or Gemini)
    except RuntimeError as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing called, nothing written"); print("NEXT: "); return 1
    import db_utils
    con = db_utils.connect(a.db)
    try:
        asker.con = con
        ensure_schema(con)
        try:
            from usage_meter import budget_ok
        except Exception:
            budget_ok = None
        if claude:   # CLAUDE_ENGINE_2026_10_15: the credit pays the Claude calls, Google the judges
            budget_ok = CreditGate(asker.ce, budget_ok)
        res = run(a, allp, picked, meta, done, asker, con, price, budget_ok)
        if claude:
            try:
                res["credit"] = asker.ce.credit_line(asker.ce.credit(con))
            except Exception:
                pass
    finally:
        con.close()
    if res.get("grouped"):   # SCHOLAR_V2_2026_10_14
        print("  sentences over several verses, each translated whole: %d" % res["grouped"])
    if res.get("split"):   # SCHOLAR_V21_2026_10_14
        print("  sentences that failed whole, then translated verse by verse: %d" % res["split"])
    if res["stopped"]:
        print("  STOPPED: %s" % res["stopped"])
    if res.get("credit"):   # CLAUDE_ENGINE_2026_10_15
        print("  " + res["credit"])
    print("VERDICT: %d passed, %d flagged (a person reads them), %d source doubt(s), %d failed; %s spent; the log: %s"
          % (len(res["passed"]), len(res["flagged"]), len(res["source_doubt"]), len(res["failed"]), usd(res["spent"]),
             res["log"]))
    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (then read it: http://127.0.0.1:5057/scholar/%s)"
          % (a.doc, a.doc))
    print("ALSO: as prose: http://127.0.0.1:5057/scholar/%s/prose   (SCHOLAR_V2_2026_10_14)" % a.doc)
    return 0


if __name__ == "__main__":
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
