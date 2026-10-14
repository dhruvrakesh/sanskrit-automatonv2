#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14

A scholarly English beside the working one: verse by verse, with the context, a glossary that grows, notes, a critic
and revisions, and an independent judge. The working English (passages.translation) is never touched.

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
PROMPT_VERSION = "scholar-v1"
CRITIC_VERSION = "scholar-critic-v1"
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
ENGINE = "gemini:gemini-2.5-pro"
JUDGE = "gemini:gemini-2.5-flash"
JUDGE_PROMPT = "judge-v1"
CONTEXT_BEFORE = 6
CONTEXT_AFTER = 2
GLOSSARY_MAX = 40
OUT_TOKENS_PRIOR = 1500      # a pro call's output with its thinking, before 10 verses are measured
JUDGE_COST_PRIOR = 0.0002    # $ a judged verse (12 Oct: 200 calls, $0.0377)
MEASURED_AFTER = 10
# The dashboard's jobs that do not change a text's Sanskrit or English: they do not stop a run
QUIET_KINDS = ("translate_hi", "ocr", "judge", "judge_all", "benchmark", "benchmark_all", "redeem_all", "path_all",
               "export", "pdf", "booksmith")

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
WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")
HELD = {"withdrawn": "withdrawn from the site: a better source first",
        "set_aside": "set aside: a better scan first",
        "in_repair": "in repair: its reading may still change (repair_text.py --release first)"}

SYSTEM_DRAFT = """You are a Sanskritist preparing a scholarly English translation of {title}, for a critical-edition translation series. The register is that of an unabridged translation made from a critical edition, as Bibek Debroy's Mahabharata is from the BORI Critical Edition: complete, faithful to every word, in plain modern English prose, with Sanskrit names and key terms kept and explained in notes. Translate afresh from the Sanskrit given. Never quote or reconstruct any published translation.

Rules:
1. COMPLETENESS. Render every word of THE VERSE TO TRANSLATE: every name, epithet, vocative and number, and every particle that carries meaning. Add nothing that is not in the Sanskrit.
2. FIDELITY. Case relations, voice, tense, number and who does what to whom must match the Sanskrit. Resolve every absolutive and participle to its true agent. A patronymic or an epithet that qualifies a person named in the verse is that same person, not another one: janamejayasya ... p\u0101rik\u1e63itasya is "of Janamejaya, the son of Parik\u1e63it", one man.
3. REGISTER. Plain, dignified modern English prose. No archaism (thee, thou, verily, lo, unto), no paraphrase, no explanation inside the sentence. Leave out purely emphatic particles (eva, hi, vai, tu, ha, khalu) unless the emphasis carries meaning.
4. NAMES. Proper names in IAST, never translated, spelled exactly as the GLOSSARY spells them. A name the glossary does not have: its stem in IAST (Arjuna, not Arjuna\u1e25).
5. EPITHETS. Translate an epithet where its meaning matters to the sentence, or keep it in IAST and explain it in a note: one or the other, consistently, as the glossary has it.
6. TERMS. A technical term English cannot render without loss stays in IAST between asterisks (*dharma*, *tapas*, *yaj\u00f1a*) with a note the first time this text uses it. The glossary lists the terms already explained: do not explain them again.
7. BRACKETS. [Square brackets] only for a word the Sanskrit implies but does not say, needed for the English to parse. Never an explanation in brackets: explanations go in the notes.
8. NOTES. Short, factual notes, only where a reader needs one: an epithet or patronymic, an allusion to a story told elsewhere, a technical or ritual term, a word with two possible readings, a textual problem. No note for what the translation already makes plain. Each note: {"anchor": the English word or words it explains, exactly as they stand in your translation, "kind": one of name|epithet|term|allusion|grammar|textual, "note": the note}.
9. DOUBTS. When a word can be read more than one way, or the Sanskrit looks corrupt or misprinted, say so in "doubts": the word, the readings, the one you chose and why. Otherwise leave "doubts" empty.
10. ONE VERSE. Translate only THE VERSE TO TRANSLATE. The verses before it (with an English that may be a working draft, and may be wrong) and after it are there only so that you understand this one: do not translate or repeat them. When the sentence runs on into the next verse, translate this verse's words as the opening of that sentence. End the translation with " //".
11. GLOSSARY. Propose an entry for each name or term this verse brings in that the glossary does not have: {"term": the IAST stem, "rendering": how the translation writes it, "kind": person|place|people|deity|term|epithet|other, "note": a gloss of a few words}.

Reply with one JSON object and nothing else:
{"translation": "...", "notes": [...], "glossary": [...], "doubts": "..."}"""

SYSTEM_CRITIC = """You are a senior Sanskritist reviewing one verse of a draft scholarly English translation of {title}, as the editor of a critical-edition translation would. Compare the draft with the Sanskrit word by word. The verses before and after are there only to help you understand: judge only THE VERSE TO TRANSLATE.

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


def ref_of(x: dict) -> str:
    return str(x.get("ref") or "%s.%s" % (x.get("page"), x.get("idx")))


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
    return {"doc": doc, "category": cat, "title": title, "source": source, "engine": top}


def latest_rows(con, doc: str) -> dict:
    """{passage_id: the latest scholar row} of this text."""
    if not has_table(con, "scholar_translations"):
        return {}
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
    mine = json.dumps({"translation": cur["translation"], "notes": cur["notes"], "doubts": cur.get("doubts") or ""},
                      ensure_ascii=False)
    return base + "\n\nYOUR DRAFT:\n" + mine + "\n\nTHE REVIEWER'S FINDINGS:\n" + finds + "\n\n" + REVISE_ASK


# --------------------------------------------------------------------------------------------- the answers
def parse_json(txt: str):
    s = (txt or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[A-Za-z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        d = json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except ValueError:
            return None
    return d if isinstance(d, dict) else None


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
    return {"translation": _s(d.get("translation"), 8000), "notes": notes[:12], "glossary": gl[:8],
            "doubts": _s(d.get("doubts"), 1000)}


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
                system = (SYSTEM_DRAFT if kind == "draft" else SYSTEM_CRITIC).replace("{title}", self.meta["title"])
                self.models[key] = self.genai.GenerativeModel(
                    model_name=name(self.a.engine), generation_config=self._cfg(0.1 if kind == "draft" else 0.0, maxtok),
                    safety_settings=self.safety, system_instruction=system)
        return self.models[key]

    def _once(self, kind, msg, maxtok):
        system_len = len(SYSTEM_DRAFT if kind == "draft" else SYSTEM_CRITIC)
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
            cost = _charge("scholar", self.meta["doc"], self.a.engine, resp, system_len + len(msg), len(txt),
                           time.time() - t0, bool(txt), self.con)
            self.spent += cost
            return txt, finish, cost
        raise CallFailed("%s: %s" % (type(last).__name__, str(last)[:160]))

    def ask(self, kind: str, msg: str) -> tuple:
        """(the JSON answer or None, $)."""
        txt, finish, cost = self._once(kind, msg, 8192)
        if not txt and ("MAX_TOKENS" in str(finish) or str(finish) == "2"):
            txt, finish, more = self._once(kind, msg, 16384)   # its thinking took the budget: once more, with room
            cost += more
        return parse_json(txt), cost

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
    try:
        if has_table(con, "scholar_translations"):
            n, avg, mx = con.execute("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE "
                                     "engine = ? AND cost_usd > 0", (a.engine,)).fetchone()
            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d verses" % n
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
    return [j for j in jobs if j.get("doc") == doc and j.get("kind") not in QUIET_KINDS]


def one_verse(a, allp, i, meta, done, asker, con, call: float) -> dict:
    """The draft, the critic and the revisions, the judge: the row to store. asker.spent counts every call it made."""
    x = allp[i]
    before, after = context(allp, i, done)
    gl = glossary(con, a.doc, x, before)
    base = verse_message(meta, x, before, after, gl)
    spent0 = asker.spent
    d, _c = asker.ask("draft", base)
    cur = clean_draft(d)
    if cur is None:
        raise CallFailed("the draft came back without a translation")
    draft = cur["translation"]
    crits, revisions, note = [], 0, ""
    while True:
        cr, _c = asker.ask("critic", critic_message(base, cur))
        cr = clean_critique(cr)
        crits.append(cr)
        if accepted(cr) or revisions >= a.rounds or cr is None:
            break
        if asker.spent + 2 * call > a.max_usd:
            note = "not revised: --max-usd $%.2f would be passed" % a.max_usd
            break
        rv, _c = asker.ask("draft", revise_message(base, cur, cr))
        rv = clean_draft(rv)
        if rv is None:
            note = "the revision came back without a translation; the last version is kept"
            break
        cur = rv
        revisions += 1
    final = crits[-1] if crits else None
    fid, flu, why, _c = asker.judge(x["text"], iast_of(x), cur["translation"])
    wfid = wflu = None
    if (x.get("english") or "").strip():
        wfid, wflu, _w, _c = asker.judge(x["text"], iast_of(x), x["english"])
    cost = asker.spent - spent0
    st = status_of(final, fid, flu)
    return {"passage_id": x["id"], "doc_code": a.doc, "page_no": x["page"], "idx": x["idx"], "verse_ref": ref_of(x),
            "src_hash": src_hash(x["text"]), "translation": cur["translation"],
            "notes": json.dumps(cur["notes"], ensure_ascii=False), "doubts": "; ".join(s for s in (cur.get("doubts"), note) if s),
            "draft": draft, "critique": json.dumps(crits, ensure_ascii=False), "passes": 1 + revisions, "fidelity": fid,
            "fluency": flu, "judge_reason": (why or "")[:200], "working_fidelity": wfid, "working_fluency": wflu,
            "status": st, "engine": a.engine, "judge_engine": a.judge_engine,
            "prompt_version": "%s+%s" % (PROMPT_VERSION, CRITIC_VERSION), "cost_usd": round(cost, 6),
            "created_at": now(), "_glossary": cur["glossary"]}


COLS = ("passage_id", "doc_code", "page_no", "idx", "verse_ref", "src_hash", "version", "translation", "notes", "doubts",
        "draft", "critique", "passes", "fidelity", "fluency", "judge_reason", "working_fidelity", "working_fluency",
        "status", "engine", "judge_engine", "prompt_version", "cost_usd", "created_at")


def store(con, rec: dict) -> int:
    v = (con.execute("SELECT MAX(version) FROM scholar_translations WHERE passage_id = ?",
                     (rec["passage_id"],)).fetchone()[0] or 0) + 1
    rec["version"] = v
    con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(COLS), ",".join("?" * len(COLS))),
                [rec.get(c) for c in COLS])
    if rec["status"] == "passed":   # the glossary grows only from verses that passed
        for g in rec.get("_glossary") or []:
            con.execute("INSERT OR IGNORE INTO scholar_glossary(doc_code, term, rendering, kind, note, source, created_at) "
                        "VALUES (?,?,?,?,?,?,?)", (rec["doc_code"], g["term"], g["rendering"], g["kind"], g["note"],
                                                   "scholar", rec["created_at"]))
    con.commit()
    return v


def run(a, allp: list, picked: list, meta: dict, done: dict, asker, con, price: dict, budget_ok=None) -> dict:
    out = {"passed": [], "flagged": [], "source_doubt": [], "failed": [], "stopped": "", "spent": 0.0}
    logp = Path(a.log_dir) / ("%s_%s.jsonl" % (re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc),
                                              datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    logp.parent.mkdir(parents=True, exist_ok=True)
    out["log"] = str(logp)
    fails = 0
    for n, i in enumerate(picked, 1):
        x = allp[i]
        if budget_ok is not None and not budget_ok(con, price["typical"]):
            out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        if asker.spent + price["typical"] > a.max_usd:
            out["stopped"] = "this run's --max-usd $%.2f is reached (%s spent)" % (a.max_usd, usd(asker.spent))
            break
        busy = busy_with(a.doc)
        if busy:
            out["stopped"] = ("the dashboard changes %s now (%s): run this when it is done"
                              % (a.doc, ", ".join(str(j.get("kind")) for j in busy)))
            break
        try:
            rec = one_verse(a, allp, i, meta, done, asker, con, price["call"])
        except CallFailed as e:
            out["spent"] = asker.spent
            fails += 1
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
        v = store(con, rec)
        done[x["id"]] = dict(rec, version=v)
        out[rec["status"]].append(ref_of(x))
        print("  (%d/%d) %s  %-12s fidelity %s, fluency %s (the working English: %s, %s)  %d pass%s  %s"
              % (n, len(picked), ref_of(x), rec["status"], rec["fidelity"], rec["fluency"], rec["working_fidelity"],
                 rec["working_fluency"], rec["passes"], "" if rec["passes"] == 1 else "es", usd(rec["cost_usd"])))
        log = {k: rec[k] for k in COLS if k not in ("draft",)}
        log.update(version=v, where=ref_of(x), mark=MARK, working_english=x.get("english") or "", draft=rec["draft"])
        with open(logp, "a", encoding="utf-8") as f:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
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


def render_doc(con, doc: str, offset: int = 0, limit=200, nav: bool = False) -> str:
    """One text's scholarly English beside its Sanskrit and its working English, verse by verse."""
    e = html.escape
    if not has_table(con, "scholar_translations"):
        rows = []
    else:
        q = ("SELECT s.*, p.text AS p_text, p.iast AS p_iast, p.translation AS p_english FROM scholar_translations s LEFT "
             "JOIN passages p ON p.id = s.passage_id WHERE s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM "
             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx")
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
    intro = ('<p class="intro">The scholarly English (%s) of <b>%s</b>, beside its Sanskrit and the working English. '
             'Each verse was drafted with its context and the text\'s glossary, read word by word by a critic, revised '
             'where the critic asked, and judged; the judge read the working English of the same verse too. '
             '<b>Passed</b>: the critic accepts it and the judge gives 4 or more for fidelity and fluency. '
             '<b>Flagged</b>: a person reads it. <b>Source doubt</b>: the Sanskrit itself looks corrupt or misread; '
             'another edition is wanted for that verse. The working English on the site is unchanged.</p>'
             % (e(PROMPT_VERSION), e(doc)))
    arts = ""
    for r in rows:
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
            iss += ('<div>Critic, reading %d: fidelity %s, completeness %s, %s%s</div>'
                    % (k, c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                       ('<ul class="iss">%s</ul>' % items) if items else ""))
        det = ('<details><summary>The working English, the first draft, the critic</summary><div class="lbl" '
               'style="margin-top:8px">The working English (on the site)</div><p class="wk">%s</p>%s%s<div>The judge: %s'
               '</div></details>'
               % (e(r.get("p_english") or "-"),
                  ('<div class="lbl">The first draft</div><p class="wk">%s</p>' % e(r["draft"]))
                  if r.get("draft") and r.get("draft") != r.get("translation") else "", iss, e(r.get("judge_reason") or "")))
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
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); print("NEXT: "); return 1
    reg = register(Path(a.verdicts) if a.verdicts else Path(a.db).resolve().parent / "source_verdicts.jsonl")
    st = (reg.get(a.doc) or {}).get("status")

    if a.report:
        con = open_ro(a.db)
        try:
            page = render_doc(con, a.doc, limit=None)
        finally:
            con.close()
        out = Path(a.exports) / ("scholar_%s.html" % re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print("VERDICT: written %s (%d bytes)" % (out, out.stat().st_size))
        print("NEXT: start %s   (or http://127.0.0.1:5057/scholar/%s)" % (out, a.doc))
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
        done = latest_rows(con, a.doc)
        picked, left, skipped = choose(a, allp, done)
        first = None
        if picked:
            i = picked[0]
            b, af = context(allp, i, done)
            first = verse_message(meta, allp[i], b, af, glossary(con, a.doc, allp[i], b))
        price = prices(con, a, len(first or ""))
    finally:
        con.close()
    print("scholar_translate.py  %s  %s   %s and its critic, up to %d revision(s); the judge %s"
          % (MARK, "RUN" if a.yes else "DRY RUN (nothing called, nothing written)", a.engine, a.rounds, a.judge_engine))
    print("  %s: %s passages; the source: %s (%s)" % (a.doc, "{:,}".format(len(allp)), meta["source"], meta["engine"] or "?"))
    if st in HELD:
        print("REFUSE: %s is %s (the register, %s: %s)" % (a.doc, HELD[st], str((reg.get(a.doc) or {}).get("at") or "?")[:16],
                                                           (reg.get(a.doc) or {}).get("reason") or ""))
        print("VERDICT: nothing sent, nothing written")
        print("NEXT: python scripts\\text_path.py --doc %s   (its path)" % a.doc)
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
              % (PROMPT_VERSION, SYSTEM_DRAFT.replace("{title}", meta["title"]), first))
    if not picked:
        print("VERDICT: nothing to send%s" % ("; %d left out" % len(left) if left else ""))
        print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (what is there)" % a.doc)
        return 0
    est, most = price["typical"] * len(picked), price["most"] * len(picked)
    print("  cost: about %s a verse, up to %s with %d revisions (%s): about %s for %d, at most %s"
          % (usd(price["typical"]), usd(price["most"]), a.rounds, price["how"], usd(est), len(picked), usd(most)))
    if not a.yes:
        cap = max(0.25, round(est * 1.25 + 0.005, 2))
        print("VERDICT: %d verse(s) ready, about %s; %d left out" % (len(picked), usd(est), len(left)))
        sel = (" --pages %s" % a.pages if a.pages else "") + (" --from-ref %s" % a.from_ref if a.from_ref else "") + (
            " --only-page %d" % a.only_page if a.only_page is not None else "") + (
            " --only-idx %d" % a.only_idx if a.only_idx is not None else "")
        print("NEXT: python scripts\\scholar_translate.py --doc %s%s --limit %d%s --yes --max-usd %.2f"
              % (a.doc, sel, a.limit, " --redo" if a.redo else "", cap))
        return 0
    try:
        asker = Gemini(a, meta, None)   # first: without a key or the SDK nothing is called, and the database is not opened
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
        res = run(a, allp, picked, meta, done, asker, con, price, budget_ok)
    finally:
        con.close()
    if res["stopped"]:
        print("  STOPPED: %s" % res["stopped"])
    print("VERDICT: %d passed, %d flagged (a person reads them), %d source doubt(s), %d failed; %s spent; the log: %s"
          % (len(res["passed"]), len(res["flagged"]), len(res["source_doubt"]), len(res["failed"]), usd(res["spent"]),
             res["log"]))
    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (then read it: http://127.0.0.1:5057/scholar/%s)"
          % (a.doc, a.doc))
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
