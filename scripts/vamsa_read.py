#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
vamsa_read.py  (2026-11-11)  VAMSA_READ_2026_11_11   (G5a: the dynasties read from the Puranas, verse by verse)

Asked on 10 and 11 Nov: "we cant even get the genealogy of Kaunteya (Arjun) right, not to say what will happen if we
start looking for specific dynasties, vanshas ... has to be an API call thing". The genealogy pages are built from two
indexes (Sorensen's of the Mahabharata, the Purana Index): what they say of a person, not the lines of the dynasties
as the Puranas tell them. This reads the Puranas' own genealogical books with Claude, one chapter (adhyaya) at a time,
into kinship statements, and checks each statement against its verse by machine (no statement is kept as "verified"
unless the Sanskrit words it rests on are in the verse it cites and both names are in them).

The texts (GRETIL's plain text, in sources\\gretil\\1_sanskr.zip, already on this PC; CC BY-NC-SA 4.0: the statements
cite the verse and GRETIL, and stay private until you decide):
  vip4    the Visnupurana, book 4 (24 chapters: the solar and lunar dynasties, the kings of the Kali age)
  bhp9    the Bhagavatapurana, book 9 (24 chapters: Manu's sons, the Iksvakus, the Somavamsa, the Yadus, the Pauravas)
  bhp12   the Bhagavatapurana 12.1 (the kings of the Kali age: Magadha, the Sungas, Kanvas, Andhras)

A statement: {"ref", "a", "rel", "b", "words", "doubt"}: a is the rel of b, in the verse ref, said by the Sanskrit
words (copied from the verse). rel: son_of, daughter_of, wife_of, brother_of, sister_of, succeeded (a reigned after b),
descendant_of, line_of (a dynasty or clan named after b), other. The check: "verified" (the words are in the verse, or
the verse and the next, and both names are in them or in the verse before, where a pronoun's person is named), "words" (the words are there, a name is not), "unsupported"
(the words are not in the verse cited), "bad" (no ref of this chapter, or a field missing).

What it writes: data\\vamsa_read\\<work>\\<chapter>[_<part>].json (the reply as it came, its statements, the checks,
its cost); usage_log rows (kind vamsa_read, the Claude credit). --report writes exports\\vamsa_read_<work>.csv and
prints the longest father-to-son lines it found (verified statements only). Nothing is sent to the site: that is G5b
(the statements joined to the index's persons) and G5c (C28 and the Dynasties page).

  python scripts\\vamsa_read.py                                  the plan: chapters, verses, the estimate (free)
  python scripts\\vamsa_read.py --work vip4 --chapters 1-2 --yes  a trial: two chapters (about $0.30)
  python scripts\\vamsa_read.py --work all --yes --max-usd 8      every chapter not read yet, at most $8
  python scripts\\vamsa_read.py --reparse                         the stored replies parsed and checked again (free)
  python scripts\\vamsa_read.py --report                          the counts, the CSVs, the longest lines (free)

VAMSA_HEAL_2026_11_11 (after the first run, 11 Nov: 56 parts, 1,975 statements, 1,449 verified, $2.00):
  - a reply that corrects itself ("Correction: ... a corrected reply follows", "Final answer:") is read by its last
    JSON object of statements (four parts were not read: "Extra data");
  - a statement without its verse's reference (a whole part, 35 statements, "bad") takes the verse its words are in;
  - the words are looked for as Sanskrit is written: the end of each word may change by sandhi (putrah, putras,
    putro), and "..." stands for words left out (281 of 309 "unsupported" were such);
  - the lines: a person is a name and the father the text gives; a father's name is joined to a person of that name
    only in the same chapter or the one before (never across the book: the first report drew one "line of 42" through
    Srnjaya, Candra and Nara of different dynasties, homonyms); a mother is not a father. --report writes each line
    with its verses (data\\vamsa_read\\<work>_lines.json, exports\\vamsa_lines_<work>.csv). The persons of the
    indexes (G5b) are what joins a line across chapters and books.
  python scripts\\vamsa_read.py --reparse   then   python scripts\\vamsa_read.py --report      (free)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

MARK = "VAMSA_READ_2026_11_11"
HEAL = "VAMSA_HEAL_2026_11_11"
PROMPT_VERSION = "vamsa-read-v1"
ROOT = Path(__file__).resolve().parents[1]
ZIP = "sources/gretil/1_sanskr.zip"
GRETIL = "GRETIL (gretil.sub.uni-goettingen.de), CC BY-NC-SA 4.0"
WORKS = {
    "vip4": {"member": "sa_viSNupurANa.txt", "marker": r"//\s*vip_(\d+),(\d+)\.(\d+)\s*//", "book": 4, "chapters": None,
             "title": "Visnupurana, book 4", "entry": "members of the Sansknet Project", "ref": "ViP %d,%d.%d"},
    "bhp9": {"member": "sa_bhAgavatapurANa.txt", "marker": r"//\s*bhp_(\d+)\.(\d+)\.(\d+)\*?\s*//", "book": 9,
             "chapters": None, "title": "Bhagavatapurana, book 9", "entry": "Ulrich Stiehl", "ref": "BhP %d.%d.%d"},
    "bhp12": {"member": "sa_bhAgavatapurANa.txt", "marker": r"//\s*bhp_(\d+)\.(\d+)\.(\d+)\*?\s*//", "book": 12,
              "chapters": [1], "title": "Bhagavatapurana 12.1", "entry": "Ulrich Stiehl", "ref": "BhP %d.%d.%d"},
}
RELS = ("son_of", "daughter_of", "wife_of", "brother_of", "sister_of", "succeeded", "descendant_of", "line_of", "other")
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
CHUNK_CHARS = 6000          # one call reads at most this much of a chapter's text
MAX_TOKENS = 24000          # the answer and the thinking
SYSTEM_TOKENS = 900         # about the system prompt, for the estimate
OUT_PER_IN = 1.6            # the answer's tokens per token of verse (measured on the trial; the estimate's guess first)
THINK_SHARE = 0.5           # the thinking, as a share of the answer
CAP_USD = 8.0               # the default most one run spends

SYSTEM = """You read Sanskrit genealogical passages (vamsanucarita) of a Purana, given in IAST with each verse's reference.
List every statement of kinship or succession that the text itself makes: who is whose son or daughter, whose wife,
whose brother or sister, who reigned after whom, who descends from whom, which line or clan is named after whom.

Rules:
- Only what these verses say. No knowledge from other texts, no inference beyond the words, no persons the verses do
  not name. A verse that only praises or narrates gives nothing.
- One statement per relation. "a" is the rel of "b": {"a": "Vikuk\u1e63i", "rel": "son_of", "b": "Ik\u1e63v\u0101ku"}.
- rel is one of: son_of, daughter_of, wife_of, brother_of, sister_of, succeeded, descendant_of, line_of, other.
  succeeded: a reigned after b. line_of: a is a dynasty or clan (Y\u0101davas, Haihayas) named after b.
- Names in IAST, as the stem (Ik\u1e63v\u0101ku, not Ik\u1e63v\u0101ku\u1e25 or Ik\u1e63v\u0101ko\u1e25), with every diacritic as
  in the text.
- "ref": the reference of the verse that says it, exactly as given in square brackets.
- "words": the Sanskrit words of that verse that say it, copied exactly from the verse (a few words, not the verse).
- "doubt": true when the text is ambiguous (two persons of one name, a pronoun whose person is unclear), else false.
- Keep the order of the text. When a verse names several sons, give one statement for each.

Reply with JSON only, no prose: {"statements": [{"ref": "...", "a": "...", "rel": "...", "b": "...", "words": "...",
"doubt": false}]}. If the verses give nothing, reply {"statements": []}."""


# --------------------------------------------------------------------------------------------- the text
def read_member(zip_path, member: str) -> str:
    z = zipfile.ZipFile(str(zip_path))
    names = [n for n in z.namelist() if n.endswith("/" + member) or n == member]
    if not names:
        raise FileNotFoundError("%s is not in %s" % (member, zip_path))
    return z.read(names[0]).decode("utf-8", errors="replace")


SPEAKER = re.compile(r"\b[a-z]+_\d+(?:[.,]\d+)+/\d+\b")
COLOPHON = re.compile(r"(?m)^\s*iti\s.*?(?:adhy|\(\d+\)).*$")


def clean(seg: str) -> str:
    s = SPEAKER.sub(" ", seg.replace("&amp;", " "))
    s = COLOPHON.sub(" ", s)
    s = re.sub(r"[$%&]", " ", s)
    return " ".join(s.split())


def verses_of(work: str, text: str) -> list:
    """[(chapter, verse, ref, text)] of the work's book (and chapters), in order: the text before each marker."""
    w = WORKS[work]
    out, last = [], 0
    for m in re.finditer(w["marker"], text):
        seg, last = text[last:m.start()], m.end()
        b, c, v = (int(x) for x in m.groups())
        if b != w["book"] or (w["chapters"] and c not in w["chapters"]):
            continue
        t = clean(seg)
        if t:
            out.append((c, v, w["ref"] % (b, c, v), t))
    return out


def chunks(verses: list, size: int = CHUNK_CHARS) -> list:
    """[{"chapter", "part", "verses": [(ref, text)]}]: each chapter, in parts of at most size characters."""
    out, cur, ch, n = [], [], None, 0
    for c, v, ref, t in verses:
        if cur and (c != ch or n + len(t) > size):
            out.append({"chapter": ch, "verses": cur})
            cur, n = [], 0
        ch = c
        cur.append((ref, t))
        n += len(t) + len(ref) + 4
    if cur:
        out.append({"chapter": ch, "verses": cur})
    parts = {}
    for u in out:
        parts[u["chapter"]] = parts.get(u["chapter"], 0) + 1
    seen = {}
    for u in out:
        seen[u["chapter"]] = seen.get(u["chapter"], 0) + 1
        u["part"] = seen[u["chapter"]] if parts[u["chapter"]] > 1 else 0
        u["chars"] = sum(len(t) for _r, t in u["verses"])
    return out


def unit_name(u: dict) -> str:
    return "%02d" % u["chapter"] + ("_%d" % u["part"] if u["part"] else "")


def user_message(work: str, u: dict) -> str:
    w = WORKS[work]
    lines = ["%s, chapter %d%s (GRETIL's text). The verses:" % (w["title"], u["chapter"],
                                                                 ", part %d" % u["part"] if u["part"] else ""), ""]
    lines += ["[%s] %s" % (r, t) for r, t in u["verses"]]
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------- the money
def estimate(chars: int, model: str = MODEL) -> float:
    import claude_engine as CE
    p_in, p_out = CE.PRICES[model][:2]
    tin = chars / 3.0 + SYSTEM_TOKENS
    tout = chars / 3.0 * OUT_PER_IN * (1.0 + THINK_SHARE)
    return (tin * p_in + tout * p_out) / 1e6


# --------------------------------------------------------------------------------------------- the reply
def json_objects(s: str) -> list:
    """Every JSON object at the top level of s, in order (the text between them left out)."""
    dec, out, i = json.JSONDecoder(strict=False), [], 0
    while True:
        i = s.find("{", i)
        if i < 0:
            return out
        try:
            obj, end = dec.raw_decode(s, i)
        except ValueError:
            i += 1
            continue
        out.append(obj)
        i = end


def parse_reply(text: str) -> list:
    """The statements of a reply; raises ValueError when it is not the JSON asked for. VAMSA_HEAL_2026_11_11: a reply
    that corrects itself is read by its last object of statements."""
    s = (text or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    if s.find("{") < 0:
        raise ValueError("no JSON object in the reply")
    objs = [o for o in json_objects(s) if isinstance(o, dict) and isinstance(o.get("statements"), list)]
    if not objs:
        raise ValueError("the reply has no list of statements")
    return [x for x in objs[-1]["statements"] if isinstance(x, dict)]


def letters(s: str) -> str:
    """Only the letters, lower case (IAST's diacritics kept): sandhi's spaces and the punctuation do not count."""
    s = unicodedata.normalize("NFC", str(s or "")).lower()
    return "".join(ch for ch in s if ch.isalpha())


def folded(s: str) -> str:
    """The letters without their diacritics (a name written without them still found)."""
    s = unicodedata.normalize("NFD", letters(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def stem_key(name: str) -> str:
    """The part of a name that its declined forms keep: the first five letters, or all but the last of a short one."""
    k = letters(name)
    return k[:5] if len(k) > 5 else (k[:-1] if len(k) > 3 else k)


def words_in(words: str, span: str, fold: bool = False) -> bool:
    """VAMSA_HEAL_2026_11_11: the words are in span (letters only) as Sanskrit is written: the last letter of each word
    of four letters or more may differ (sandhi: putrah, putras, putro), at most three letters may come between two
    words, and "..." stands for words left out (each part found in order)."""
    f = folded if fold else letters
    pos = 0
    for frag in re.split(r"\.{2,}|\u2026", str(words or "")):
        toks = [f(x) for x in frag.split() if f(x)]
        if not toks:
            continue
        cores = [x[:-1] if len(x) > 3 else x for x in toks]
        if sum(len(c) for c in cores) < 4:
            return False
        m = re.compile(".{0,3}".join(re.escape(c) for c in cores)).search(span, pos)
        if not m:
            return False
        pos = m.end()
    return pos > 0


def ref_of(words: str, refs: dict, order: list):
    """VAMSA_HEAL_2026_11_11: the verse of the part whose words these are (the first, alone or with the next), or None."""
    for r in order:
        if words_in(words, letters(refs[r])):
            return r
    for k, r in enumerate(order):
        if words_in(words, letters(refs[r]) + "".join(letters(refs[x]) for x in order[k + 1:k + 2])):
            return r
    return None


def check(st: dict, refs: dict, order: list) -> str:
    """verified, words, unsupported or bad (see the docstring). refs: {ref: text}; order: the refs in order."""
    a, b, rel, ref, words = (str(st.get(k) or "").strip() for k in ("a", "b", "rel", "ref", "words"))
    if not (a and b and ref and words) or rel not in RELS or ref not in refs:
        return "bad"
    k = order.index(ref)
    here = letters(refs[ref])
    near = here + "".join(letters(refs[r]) for r in order[k + 1:k + 2])
    if not (words_in(words, near) or words_in(words, folded(near), fold=True)):
        return "unsupported"
    span = "".join(letters(refs[r]) for r in order[max(0, k - 1):k]) + near   # a pronoun's person: the verse before
    if stem_key(a) in span and stem_key(b) in span:
        return "verified"
    fspan = folded(span)
    if stem_key(folded(a)) in fspan and stem_key(folded(b)) in fspan:
        return "verified"
    return "words"


def checked(statements: list, u: dict) -> list:
    refs = dict(u["verses"])
    order = [r for r, _t in u["verses"]]
    out = []
    for st in statements:
        x = {k: st.get(k) for k in ("ref", "a", "rel", "b", "words", "doubt")}
        if not x.get("ref"):   # VAMSA_HEAL_2026_11_11: the reference under another name, or none
            x["ref"] = st.get("reference") or st.get("verse") or st.get("verse_ref")
        if x.get("ref") not in refs and x.get("words"):
            got = ref_of(str(x["words"]), refs, order)
            if got:
                x["ref"], x["ref_from"] = got, "words"
        x["doubt"] = bool(x.get("doubt"))
        x["check"] = check(x, refs, order)
        out.append(x)
    return out


# --------------------------------------------------------------------------------------------- the store
def out_path(out_dir, work: str, u: dict) -> Path:
    return Path(out_dir) / work / ("%s.json" % unit_name(u))


def done(out_dir, work: str, u: dict) -> bool:
    p = out_path(out_dir, work, u)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return d.get("prompt_version") == PROMPT_VERSION and not d.get("error")


def store(out_dir, work: str, u: dict, rec: dict) -> Path:
    p = out_path(out_dir, work, u)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return p


def records(out_dir, work: str) -> list:
    out = []
    for p in sorted((Path(out_dir) / work).glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


# --------------------------------------------------------------------------------------------- the lines
def persons(statements: list) -> dict:
    """VAMSA_HEAL_2026_11_11: the persons of the verified son_of statements, homonyms kept apart. A person is a name and
    the father the text gives; his father is the person of that name who is a son in the same chapter or the one
    before (the nearest before him, else the nearest after); when there is none, the father is a person of his own
    (a root). A mother (a wife_of, daughter_of or sister_of in these statements) is not a father.
    {key: {"name", "father", "up": key or None, "chapter", "ref", "words", "pos"}}"""
    ver = [s for s in statements if s.get("check") == "verified"]
    female = {letters(s.get("a")) for s in ver if s.get("rel") in ("wife_of", "daughter_of", "sister_of")}
    sons = [s for s in ver if s.get("rel") == "son_of" and letters(s.get("b")) not in female
            and letters(s.get("a")) and letters(s.get("b")) and letters(s.get("a")) != letters(s.get("b"))]
    out = {}
    for pos, s in enumerate(sons):
        key = "%s|%s" % (letters(s["a"]), letters(s["b"]))
        if key not in out:
            out[key] = {"name": s["a"], "father": s["b"], "up": None, "chapter": s.get("chapter"), "ref": s.get("ref"),
                        "words": s.get("words"), "pos": pos}
    by_name = {}
    for key, p in out.items():
        by_name.setdefault(key.split("|")[0], []).append(key)
    for key, p in out.items():
        fk = letters(p["father"])
        near = [k for k in by_name.get(fk, ()) if k != key and p["chapter"] is not None
                and out[k]["chapter"] is not None and 0 <= p["chapter"] - out[k]["chapter"] <= 1]
        if not near:
            continue
        before = [k for k in near if out[k]["pos"] < p["pos"]]
        pick = max(before, key=lambda k: out[k]["pos"]) if before else min(near, key=lambda k: out[k]["pos"])
        if pick != key:
            p["up"] = pick
    for key, p in out.items():   # no person his own ancestor
        seen, k = {key}, p["up"]
        while k:
            if k in seen:
                p["up"] = None
                break
            seen.add(k)
            k = out[k]["up"]
    return out


def lines_of(statements: list) -> list:
    """VAMSA_HEAL_2026_11_11: the father-to-son lines of persons(), longest first: [[(name, ref, words), ...]], each
    from a root (a father who is not a son here: his name and no verse) down to a person with no son here."""
    ps = persons(statements)
    kids = {}
    for key, p in ps.items():
        kids.setdefault(p["up"] or "root:" + letters(p["father"]), []).append(key)
    memo = {}

    def down(k):
        if k not in memo:
            best = []
            for c in kids.get(k, ()):
                got = down(c)
                if len(got) > len(best):
                    best = got
            memo[k] = [k] + best
        return memo[k]
    roots = [k for k in kids if k.startswith("root:")]
    out = []
    for r in roots:
        chain = down(r)
        first = ps[chain[1]]["father"] if len(chain) > 1 else r[5:]
        out.append([(first, None, None)] + [(ps[k]["name"], ps[k]["ref"], ps[k]["words"]) for k in chain[1:]])
    return sorted(out, key=lambda x: (-len(x), letters(x[0][0])))


def longest_lines(statements: list, top: int = 5) -> list:
    """The longest father-to-son lines (lines_of: homonyms kept apart): [[ancestor, ..., descendant]]."""
    return [[n for n, _r, _w in ln] for ln in lines_of(statements)[:top] if len(ln) > 2]


def longest_lines_by_name(statements: list, top: int = 5) -> list:
    """The first report's lines (before VAMSA_HEAL_2026_11_11): persons joined by their names alone, homonyms merged."""
    kids = {}
    for s in statements:
        if s.get("check") == "verified" and s.get("rel") == "son_of":
            f, c = letters(s["b"]), letters(s["a"])
            if f and c and f != c:
                kids.setdefault(f, {}).setdefault(c, s["a"])
    names = {}
    for s in statements:
        if s.get("check") == "verified":
            names.setdefault(letters(s["a"]), s["a"]); names.setdefault(letters(s["b"]), s["b"])
    memo = {}

    def down(n, path):
        if n in memo:
            return memo[n]
        best = [n]
        for c in kids.get(n, {}):
            if c in path:
                continue
            got = down(c, path | {c})
            if len(got) + 1 > len(best):
                best = [n] + got
        memo[n] = best
        return best
    has_parent = {c for f in kids for c in kids[f]}
    roots = [f for f in kids if f not in has_parent] or list(kids)
    lines = sorted((down(r, {r}) for r in roots), key=lambda x: (-len(x), x[0]))
    return [[names.get(n, n) for n in ln] for ln in lines[:top] if len(ln) > 2]


# --------------------------------------------------------------------------------------------- the run
def parse_chapters(spec: str):
    if not spec:
        return None
    got = set()
    for part in spec.split(","):
        part = part.strip()
        if re.match(r"^\d+-\d+$", part):
            a, b = (int(x) for x in part.split("-"))
            got.update(range(a, b + 1))
        elif part.isdigit():
            got.add(int(part))
        else:
            raise ValueError("chapters: numbers and ranges, such as 1-3,7")
    return got


def plan_units(a) -> dict:
    works = list(WORKS) if a.work == "all" else [a.work]
    texts, out = {}, {}
    want = parse_chapters(a.chapters)
    for wk in works:
        m = WORKS[wk]["member"]
        if m not in texts:
            texts[m] = read_member(a.zip, m)
        us = chunks(verses_of(wk, texts[m]))
        out[wk] = [u for u in us if not want or u["chapter"] in want]
    return out


def credit_line(db) -> str:
    try:
        import sqlite3
        import claude_engine as CE
        if not Path(db).exists():
            return "the credit: no database here"
        con = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            return CE.credit_line(CE.credit(con))
        finally:
            con.close()
    except Exception as e:
        return "the credit could not be read (%s)" % e


def do_plan(a, units: dict) -> int:
    total, todo_n, todo_usd = 0.0, 0, 0.0
    for wk, us in units.items():
        n_v = sum(len(u["verses"]) for u in us)
        chars = sum(u["chars"] for u in us)
        left = [u for u in us if not done(a.out, wk, u)]
        usd = sum(estimate(u["chars"], a.model) for u in left)
        todo_n += len(left); todo_usd += usd; total += sum(estimate(u["chars"], a.model) for u in us)
        print("  %-6s %-28s %3d chapter part(s), %5d verses, %7d characters; %d to read, about $%.2f"
              % (wk, WORKS[wk]["title"], len(us), n_v, chars, len(left), usd))
    print("  %s" % credit_line(a.db))
    print("VERDICT: %d part(s) to read, about $%.2f (the whole: about $%.2f; the estimate is a guess until the trial "
          "measures it), %s with %s" % (todo_n, todo_usd, total, "the Claude credit", a.model))
    first = next(iter(units))
    print("NEXT: python scripts\\vamsa_read.py --work %s --chapters 1-2 --yes   (a trial)" % first
          if todo_n else "NEXT: python scripts\\vamsa_read.py --report")
    return 0


def do_run(a, units: dict, client=None, con=None) -> int:
    import claude_engine as CE
    todo = [(wk, u) for wk, us in units.items() for u in us if not done(a.out, wk, u)]
    need = sum(estimate(u["chars"], a.model) for _w, u in todo)
    if not todo:
        print("VERDICT: nothing to read: every part asked for is read"); print("NEXT: python scripts\\vamsa_read.py --report")
        return 0
    if need > a.max_usd * 1.5:
        print("REFUSE: the estimate is $%.2f, above --max-usd %.2f by half again: read fewer chapters (--chapters), or "
              "raise --max-usd" % (need, a.max_usd))
        print("VERDICT: nothing sent"); print("NEXT: python scripts\\vamsa_read.py --work %s --chapters 1-2 --yes"
                                               % todo[0][0])
        return 1
    own = None
    if con is None:
        import db_utils
        con = own = db_utils.connect(a.db)
    try:
        if client is None:
            try:
                client = CE.Client(a.model, a.effort)
            except RuntimeError as e:
                print("REFUSE: %s" % e); print("VERDICT: nothing sent"); print("NEXT: "); return 1
        spent, n_ok, n_st, n_ver = 0.0, 0, 0, 0
        for i, (wk, u) in enumerate(todo, 1):
            est = estimate(u["chars"], a.model)
            if spent + est > a.max_usd:
                print("  stopped before %s %s: $%.2f spent, the next about $%.2f, --max-usd %.2f"
                      % (wk, unit_name(u), spent, est, a.max_usd))
                break
            if not CE.budget_ok(con, est):
                print("  stopped: the Claude credit (python scripts\\claude_engine.py --credit)")
                break
            t0 = time.time()
            rec = {"mark": MARK, "work": wk, "title": WORKS[wk]["title"], "chapter": u["chapter"], "part": u["part"],
                   "refs": [r for r, _t in u["verses"]], "model": a.model, "effort": a.effort,
                   "prompt_version": PROMPT_VERSION, "source": "%s; %s (data entry: %s)" % (
                       WORKS[wk]["member"], GRETIL, WORKS[wk]["entry"]),
                   "at": datetime.datetime.now().isoformat(timespec="seconds")}
            try:
                msg = client.create(SYSTEM, user_message(wk, u), MAX_TOKENS)
            except Exception as e:
                rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
                store(a.out, wk, u, rec)
                print("  [%d/%d] %s %s: the API did not answer (%s)" % (i, len(todo), wk, unit_name(u), rec["error"][:120]))
                break
            cost = CE.meter(con, "vamsa_read", wk, a.model, msg.usage, time.time() - t0, units=len(u["verses"]))
            spent += cost
            rec.update(reply=CE.text_of(msg), stop=CE.stop_of(msg), cost_usd=round(cost, 5), tokens=CE.tokens(msg.usage))
            try:
                rec["statements"] = checked(parse_reply(rec["reply"]), u)
            except ValueError as e:
                rec["error"] = "the reply was not read: %s%s" % (e, "; it was cut (max_tokens)" if rec["stop"] == "max_tokens"
                                                                 else "")
            store(a.out, wk, u, rec)
            st = rec.get("statements") or []
            v = sum(1 for s in st if s["check"] == "verified")
            n_ok += 0 if rec.get("error") else 1; n_st += len(st); n_ver += v
            print("  [%d/%d] %s %s: %d verses, %d statements, %d verified, $%.4f%s"
                  % (i, len(todo), wk, unit_name(u), len(u["verses"]), len(st), v, cost,
                     ("  (%s)" % rec["error"][:100]) if rec.get("error") else ""), flush=True)
        print("VERDICT: %d part(s) read, %d statements, %d verified (%s); $%.2f spent of the Claude credit"
              % (n_ok, n_st, n_ver, "%d%%" % (100 * n_ver // n_st) if n_st else "-", spent))
        print("NEXT: python scripts\\vamsa_read.py --report")
        return 0
    finally:
        if own is not None:
            own.close()


def do_reparse(a, units: dict) -> int:
    n, bad = 0, 0
    for wk, us in units.items():
        for u in us:
            p = out_path(a.out, wk, u)
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not rec.get("reply"):
                continue
            rec.pop("error", None)
            try:
                rec["statements"] = checked(parse_reply(rec["reply"]), u)
            except ValueError as e:
                rec["error"] = "the reply was not read: %s" % e
                bad += 1
            store(a.out, wk, u, rec)
            n += 1
    print("VERDICT: %d stored repl(ies) parsed and checked again, %d not read (free)" % (n, bad))
    print("NEXT: python scripts\\vamsa_read.py --report")
    return 0


def do_report(a) -> int:
    works = list(WORKS) if a.work == "all" else [a.work]
    ex = Path(a.exports)
    ex.mkdir(parents=True, exist_ok=True)
    total = 0
    for wk in works:
        recs = records(a.out, wk)
        st = [dict(s, chapter=r.get("chapter")) for r in recs for s in (r.get("statements") or [])]
        if not recs:
            print("  %-6s not read yet" % wk)
            continue
        total += len(st)
        by = {}
        for s in st:
            by[s["check"]] = by.get(s["check"], 0) + 1
        cost = sum(float(r.get("cost_usd") or 0) for r in recs)
        errs = sum(1 for r in recs if r.get("error"))
        print("  %-6s %d part(s) read (%d not), %d statements: %s; $%.2f" % (
            wk, len(recs) - errs, errs, len(st), ", ".join("%s %d" % kv for kv in sorted(by.items())), cost))
        lines = lines_of(st)   # VAMSA_HEAL_2026_11_11: homonyms kept apart
        for ln in lines[:5]:
            if len(ln) > 2:
                print("         a line of %d: %s" % (len(ln), " > ".join(n for n, _r, _w in ln)))
        lp = Path(a.out) / ("%s_lines.json" % wk)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps({"mark": HEAL, "work": wk, "title": WORKS[wk]["title"], "lines": [
            [{"name": n, "ref": r, "words": w} for n, r, w in ln] for ln in lines if len(ln) > 1]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        lc = ex / ("vamsa_lines_%s.csv" % wk)
        with open(lc, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["line", "step", "name", "father", "ref", "words"])
            for i, ln in enumerate(l for l in lines if len(l) > 1):
                for j, (n, r, w) in enumerate(ln):
                    wr.writerow([i + 1, j, n, ln[j - 1][0] if j else "", r or "", w or ""])
        print("         wrote %s, %s (%d lines of 3 or more)" % (lp, lc, sum(1 for l in lines if len(l) > 2)))
        p = ex / ("vamsa_read_%s.csv" % wk)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["chapter", "ref", "a", "rel", "b", "words", "doubt", "check"])
            for s in st:
                wr.writerow([s.get("chapter"), s.get("ref"), s.get("a"), s.get("rel"), s.get("b"), s.get("words"),
                             s.get("doubt"), s.get("check")])
        print("         wrote %s" % p)
    print("VERDICT: %d statements in all; the verified ones are what G5b joins to the index's persons" % total)
    print("NEXT: python scripts\\vamsa_read.py   (the plan: what is left to read)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default="all", choices=["all"] + list(WORKS))
    ap.add_argument("--chapters", default="", help="numbers and ranges: 1-3,7")
    ap.add_argument("--yes", action="store_true", help="read (the Claude credit); without it, the plan")
    ap.add_argument("--max-usd", type=float, default=CAP_USD)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--reparse", action="store_true", help="the stored replies parsed and checked again (free)")
    ap.add_argument("--report", action="store_true", help="the counts, the CSVs, the longest lines (free)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--zip", default=ZIP)
    ap.add_argument("--out", default="data/vamsa_read")
    ap.add_argument("--exports", default="exports")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        import env_loader
        env_loader.load_env()
    except Exception:
        pass
    sys.path.insert(0, str(ROOT / "scripts"))
    import claude_engine as CE
    if a.model not in CE.PRICES:
        print("REFUSE: %s is not one of %s" % (a.model, ", ".join(sorted(CE.PRICES))))
        print("VERDICT: nothing read"); print("NEXT: "); return 1
    if a.report:
        return do_report(a)
    if not Path(a.zip).exists():
        print("REFUSE: %s is not here (GRETIL's Sanskrit, fetched by etext_witness.py)" % a.zip)
        print("VERDICT: nothing read"); print("NEXT: "); return 1
    try:
        units = plan_units(a)
    except (ValueError, FileNotFoundError) as e:
        print("REFUSE: %s" % e); print("VERDICT: nothing read"); print("NEXT: "); return 1
    if a.reparse:
        return do_reparse(a, units)
    if a.yes:
        return do_run(a, units)
    return do_plan(a, units)


if __name__ == "__main__":
    sys.exit(main())
