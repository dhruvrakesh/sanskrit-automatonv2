#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_claude_engine_2026_10_15.py  (2026-10-15)  CLAUDE_ENGINE_2026_10_15

Claude as an engine of the scholarly English, beside gemini-2.5-pro, paid from the API credit of the Max plan ($200, to
11 Nov 2026) and capped by it; the Agamas and Tantras read as such; the engines read side by side (scholar_duel.py).

scripts/scholar_translate.py:
  - --engine anthropic:claude-sonnet-5-5 (or claude-opus-5-5, claude-haiku-5-5; an effort after "@":
    anthropic:claude-sonnet-5-5@medium): the translator, the critic and the groups call by Claude (class Claude, from
    scripts/claude_engine.py). The judge stays judge-v1 (gemini-2.5-flash) and the second judge gemini-2.5-pro
    (--compare-engine), so that a Claude English is never judged by Claude. A run is capped by the credit
    (claude_engine.budget_ok) for its Claude calls and by the spend cap for the Google part, and the dry run shows the
    credit;
  - one place for the system prompts (SYSTEMS, system_for), so that Gemini and Claude send the same;
  - a text of the Agamas and Tantras (its category, or its name: agama, tantra, pancaratra, bhairava) gets a rule more
    (agama-1, recorded in prompt_version): a mantra, a seed-syllable or a ritual formula stays in IAST; a Latin digit in
    a word is the printed edition's footnote number. The critic and the judges are told the same;
  - an edition's apparatus on the page (the manuscripts' variant readings by footnote number: "7 yat (?)-B,C.") is
    given with the verse, for understanding: a variant that changes the meaning is a textual note;
  - TITLES: the Hayasirsa Pancaratra, the Karanagama and the Tantrik Texts vol. I by their names in the prompts;
    --title for any other;
  - Hindi prose: more words that are Hindi only (lie, chahie, vala ...): the Karanagama's Hindi rendering under each
    verse was sent as Sanskrit where it had two of the old words only;
  - --held-ok: a text held from the site while its working English is redone (in_repair) is translated (nothing is
    written to the site or to its passages; a row goes stale, not wrong, if the reading changes); without it the refusal
    says so;
  - --no-glossary-adds: a benchmark run that does not grow the glossary (the engines see the same one);
  - the NEXT line keeps --engine, --held-ok, --no-glossary-adds and --title.
  - store: two runs that number the same verse at once number it again (the engines of a pilot run side by side).
scripts/cost_tracker.py: the three Claude models in the price table (claude_engine.py prices the cache and the thinking
  itself; this is for the priors and anything else that prices an engine by name).

Needs COST_TRUTH_2026_10_15 (scholar_translate.py), SPEND_TRUTH_2026_10_04 (cost_tracker.py), and the new
scripts/claude_engine.py and scripts/scholar_duel.py beside them.
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings; py_compile before the atomic replace;
backups .bak_claude_<date>.
  python scripts\\patch_claude_engine_2026_10_15.py --check
  python scripts\\patch_claude_engine_2026_10_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "CLAUDE_ENGINE_2026_10_15"
NEEDS = {"scripts/scholar_translate.py": "COST_TRUTH_2026_10_15", "scripts/cost_tracker.py": "SPEND_TRUTH_2026_10_04"}
NEW_FILES = ("scripts/claude_engine.py", "scripts/scholar_duel.py")
FILES = list(NEEDS)

E = []   # (file, number, old, new)
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = "scripts/scholar_translate.py"

edit(ST, 1, r'''SCHOLAR_V21_2026_10_14,
COST_TRUTH_2026_10_15

A scholarly English''', r'''SCHOLAR_V21_2026_10_14,
COST_TRUTH_2026_10_15, CLAUDE_ENGINE_2026_10_15

A scholarly English''')

edit(ST, 2, r'''METERED_SINCE); before 10 of them, the prior of 3,000 output tokens a call. A job that only adds working English does
not stop a run.
''', r'''METERED_SINCE); before 10 of them, the prior of 3,000 output tokens a call. A job that only adds working English does
not stop a run.

CLAUDE_ENGINE_2026_10_15: Claude as the translator and the critic (--engine anthropic:claude-sonnet-5-5, or
anthropic:claude-opus-5-5@medium: the effort after the "@"), by scripts/claude_engine.py: metered in usage_log as
Anthropic bills it, paid from the API credit and capped by it, not by the spend cap. The judge stays judge-v1
(gemini-2.5-flash) and the second judge gemini-2.5-pro (--compare-engine): a Claude English is never judged by Claude.
A text of the Agamas and Tantras gets a rule more (agama-1): a mantra or a seed-syllable stays in IAST, a Latin digit in
a word is the edition's footnote number; the edition's apparatus on the page goes with the verse. --held-ok translates a
text held from the site while its working English is redone (nothing is written to the site or to its passages).
--no-glossary-adds: a benchmark run. scripts/scholar_duel.py reads the engines side by side, blind.
''')

edit(ST, 3, r'''MARK3 = "SCHOLAR_V21_2026_10_14"
''', r'''MARK3 = "SCHOLAR_V21_2026_10_14"
MARK4 = "CLAUDE_ENGINE_2026_10_15"
''')

edit(ST, 4, r'''               "translate", "translate_both", "translate_one")   # COST_TRUTH_2026_10_15: they add working English
''', r'''               "translate", "translate_both", "translate_one")   # COST_TRUTH_2026_10_15: they add working English
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
''')

edit(ST, 5, r'''    "\u0935\u0939", "\u091c\u094b"))
''', r'''    "\u0935\u0939", "\u091c\u094b"))
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
''')

edit(ST, 6, r'''        "in_repair": "in repair: its reading may still change (repair_text.py --release first)"}
''', r'''        "in_repair": "in repair: its reading may still change (repair_text.py --release first)"}
HELD_OK = "--held-ok translates it while it is held from the site: nothing is written to the site or to its passages"
''')

edit(ST, 7, r'''{"A": {"fidelity": 0, "errors": []}, "B": {"fidelity": 0, "errors": []}, "better": "equal", "reason": ""}"""
''', r'''{"A": {"fidelity": 0, "errors": []}, "B": {"fidelity": 0, "errors": []}, "better": "equal", "reason": ""}"""

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
''')

edit(ST, 8, r'''    return {"doc": doc, "category": cat, "title": title, "source": source, "engine": top}
''', r'''    title = TITLES.get(doc) or title   # CLAUDE_ENGINE_2026_10_15
    return {"doc": doc, "category": cat, "title": title, "source": source, "engine": top,
            "agama": bool(AGAMA.search("%s %s" % (cat or "", doc)))}
''')

edit(ST, 9, r'''                system = {"draft": SYSTEM_DRAFT, "groups": SYSTEM_GROUPS, "compare": SYSTEM_COMPARE}.get(
                    kind, SYSTEM_CRITIC).replace("{title}", self.meta["title"])   # SCHOLAR_V2_2026_10_14
''', r'''                system = system_for(kind, self.meta)   # CLAUDE_ENGINE_2026_10_15 (SCHOLAR_V2_2026_10_14)
''')

edit(ST, 10, r'''        system_len = len({"draft": SYSTEM_DRAFT, "groups": SYSTEM_GROUPS, "compare": SYSTEM_COMPARE}.get(
            kind, SYSTEM_CRITIC))   # SCHOLAR_V2_2026_10_14
''', r'''        system_len = len(system_for(kind, self.meta))   # CLAUDE_ENGINE_2026_10_15 (SCHOLAR_V2_2026_10_14)
''')

edit(ST, 11, r'''            cost = _charge("scholar", self.meta["doc"], self.a.engine, resp, system_len + len(msg), len(txt),
                           time.time() - t0, bool(txt), self.con)
''', r'''            cost = _charge(getattr(self, "meter_kind", "scholar"), self.meta["doc"], self.a.engine, resp,
                           system_len + len(msg), len(txt), time.time() - t0, bool(txt), self.con)   # CLAUDE_ENGINE
''')

edit(ST, 12, r'''        cost = _charge("judge", self.meta["doc"], self.a.judge_engine, r, inc, outc, time.time() - t0, fid is not None,
                       self.con)
        self.spent += cost
        return fid, flu, why, cost
''', r'''        cost = _charge("judge", self.meta["doc"], self.a.judge_engine, r, inc, outc, time.time() - t0, fid is not None,
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
        if d is None and kind == "draft" and stop != "refusal":
            txt, stop, more = self._once(kind, msg, 2 * CLAUDE_MAX_TOKENS)
            cost += more
            d = parse_json(txt)
        self.last = {"kind": kind, "finish": stop, "chars": len(txt or ""), "json": d is not None}
        return d, cost

    def judge(self, src: str, iast: str, english: str) -> tuple:
        return self.gem.judge(src, iast, english)


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
''')

edit(ST, 13, r'''    base = verse_message(meta, x, before, after, gl) if len(xs) == 1 else group_message(meta, xs, before, after, gl)
''', r'''    base = verse_message(meta, x, before, after, gl) if len(xs) == 1 else group_message(meta, xs, before, after, gl)
    base = with_apparatus(base, allp, xs)   # CLAUDE_ENGINE_2026_10_15: the edition's variants on the page
''')

edit(ST, 14, r'''                     "prompt_version": "%s+%s" % (PROMPT_VERSION, CRITIC_VERSION), "cost_usd": round(cost / len(xs), 6),
''', r'''                     "prompt_version": "%s+%s%s" % (PROMPT_VERSION, CRITIC_VERSION, ("+" + AGAMA_VERSION) if meta.get(
                         "agama") else ""), "cost_usd": round(cost / len(xs), 6),   # CLAUDE_ENGINE_2026_10_15
''')

edit(ST, 15, r'''                     "_glossary": cur["glossary"] if k == 0 else []})
''', r'''                     "_glossary": cur["glossary"] if k == 0 and not getattr(a, "no_glossary_adds", False) else []})
''')

edit(ST, 16, r'''            out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
''', r'''            out["stopped"] = (getattr(budget_ok, "why", "") or   # CLAUDE_ENGINE_2026_10_15: the credit's own
                              "the spend cap is reached (python scripts\\set_budget.py shows it)")
''')

edit(ST, 17, r'''    ap.add_argument("--no-compare", action="store_true", help="SCHOLAR_V2_2026_10_14: no second judge")
''', r'''    ap.add_argument("--no-compare", action="store_true", help="SCHOLAR_V2_2026_10_14: no second judge")
    ap.add_argument("--compare-engine", default=COMPARE_ENGINE, help="CLAUDE_ENGINE_2026_10_15: the second judge of a "
                    "Claude English (a Gemini model)")
    ap.add_argument("--held-ok", action="store_true", help="CLAUDE_ENGINE_2026_10_15: translate a text held from the site "
                    "while its working English is redone (in_repair); nothing is written to the site")
    ap.add_argument("--no-glossary-adds", action="store_true", help="CLAUDE_ENGINE_2026_10_15: a benchmark run; the "
                    "glossary does not grow from it")
    ap.add_argument("--title", default=None, help="CLAUDE_ENGINE_2026_10_15: the text's name in the prompts")
''')

edit(ST, 18, r'''    a.groups, a.compare = not a.no_groups, not a.no_compare   # SCHOLAR_V2_2026_10_14
''', r'''    a.groups, a.compare = not a.no_groups, not a.no_compare   # SCHOLAR_V2_2026_10_14
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
''')

edit(ST, 19, r'''        meta = doc_meta(con, a.doc, allp, Path(a.db).resolve().parent / "raw")
''', r'''        meta = doc_meta(con, a.doc, allp, Path(a.db).resolve().parent / "raw")
        if getattr(a, "title", None):   # CLAUDE_ENGINE_2026_10_15
            meta["title"] = a.title
''')

edit(ST, 20, r'''            first = verse_message(meta, allp[i], b, af, glossary(con, a.doc, allp[i], b))
        price = prices(con, a, len(first or ""))
''', r'''            first = verse_message(meta, allp[i], b, af, glossary(con, a.doc, allp[i], b))
            first = with_apparatus(first, allp, [allp[i]])   # CLAUDE_ENGINE_2026_10_15
        price = prices(con, a, len(first or ""))
        credit = None
        if claude:   # CLAUDE_ENGINE_2026_10_15
            try:
                credit = claude_engine.credit(con)
            except RuntimeError as e:
                credit = {"error": str(e)}
''')

edit(ST, 21, r'''    if st in HELD:
        print("REFUSE: %s is %s (the register''', r'''    if st == "in_repair" and getattr(a, "held_ok", False):   # CLAUDE_ENGINE_2026_10_15
        print("  NOTE: %s is held from the site (the register, %s: %s); --held-ok: the scholarly English writes nothing "
              "to the site or to its passages, and a row goes stale, not wrong, if its reading changes"
              % (a.doc, str((reg.get(a.doc) or {}).get("at") or "?")[:16], (reg.get(a.doc) or {}).get("reason") or ""))
    elif st in HELD:
        print("REFUSE: %s is %s (the register''')

edit(ST, 22, r'''        print("NEXT: python scripts\\text_path.py --doc %s   (its path)" % a.doc)
        return 3
''', r'''        print("NEXT: python scripts\\text_path.py --doc %s   (its path)" % a.doc)
        if st == "in_repair":   # CLAUDE_ENGINE_2026_10_15
            print("ALSO: " + HELD_OK)
        return 3
''')

edit(ST, 23, r'''        MARK2))
    if not a.yes:
''', r'''        MARK2))
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
''')

edit(ST, 24, r'''                 + (" --no-compare" if a.no_compare else ""), cap))
''', r'''                 + (" --no-compare" if a.no_compare else "") + ((" --engine %s" % a.engine) if a.engine != ENGINE else "")
                 + (" --held-ok" if getattr(a, "held_ok", False) else "")
                 + (" --no-glossary-adds" if getattr(a, "no_glossary_adds", False) else "")
                 + ((' --title "%s"' % a.title) if getattr(a, "title", None) else ""), cap))   # CLAUDE_ENGINE_2026_10_15
''')

edit(ST, 25, r'''        asker = Gemini(a, meta, None)   # first: without a key or the SDK nothing is called, and the database is not opened
''', r'''        asker = (Claude if claude else Gemini)(a, meta, None)   # first: without a key or the SDK nothing is called, and
        # the database is not opened (CLAUDE_ENGINE_2026_10_15: Claude, or Gemini)
''')

edit(ST, 26, r'''            budget_ok = None
        res = run(a, allp, picked, meta, done, asker, con, price, budget_ok)
''', r'''            budget_ok = None
        if claude:   # CLAUDE_ENGINE_2026_10_15: the credit pays the Claude calls, Google the judges
            budget_ok = CreditGate(asker.ce, budget_ok)
        res = run(a, allp, picked, meta, done, asker, con, price, budget_ok)
        if claude:
            try:
                res["credit"] = asker.ce.credit_line(asker.ce.credit(con))
            except Exception:
                pass
''')

edit(ST, 27, r'''        print("  STOPPED: %s" % res["stopped"])
''', r'''        print("  STOPPED: %s" % res["stopped"])
    if res.get("credit"):   # CLAUDE_ENGINE_2026_10_15
        print("  " + res["credit"])
''')

edit(ST, 28, r"""              % (PROMPT_VERSION, SYSTEM_DRAFT.replace("{title}", meta["title"]), first))
""", r"""              % (PROMPT_VERSION, system_for("draft", meta), first))   # CLAUDE_ENGINE_2026_10_15: as it is sent
""")

edit(ST, 29, r"""def store(con, rec: dict) -> int:
    v = (con.execute("SELECT MAX(version) FROM scholar_translations WHERE passage_id = ?",
                     (rec["passage_id"],)).fetchone()[0] or 0) + 1
    rec["version"] = v
    con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(COLS), ",".join("?" * len(COLS))),
                [rec.get(c) for c in COLS])
""", r"""def store(con, rec: dict) -> int:
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
""")

CT = "scripts/cost_tracker.py"
edit(CT, 1, r'''    "tesseract":                   (0.00,   0.00),   # local compute, no API cost
}''', r'''    "tesseract":                   (0.00,   0.00),   # local compute, no API cost
    # CLAUDE_ENGINE_2026_10_15: Anthropic's API, $ a million tokens (platform.claude.com pricing, 2026-10-15); an effort
    # after "@" (anthropic:claude-sonnet-5-5@medium) finds its model here by name. claude_engine.py prices the cache and
    # the Batch API itself.
    "anthropic:claude-opus-5-5":   (4.00,  20.00),
    "anthropic:claude-sonnet-5-5": (2.00,  10.00),
    "anthropic:claude-haiku-5-5":  (0.10,   0.50),
}''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(rel: str, data: bytes) -> str:
    """'' when the new source compiles; else the error."""
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/scholar_translate.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in NEW_FILES:
        p = Path(rel)
        if not p.exists() or MARK.encode() not in p.read_bytes():
            problems.append("%s (%s) is not there: put it beside the scripts first" % (rel, MARK))
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: this is not the file released" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if bad:
            continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in p.read_bytes()) and not all(x < 128 for x in data):   # an ASCII file stays ASCII
            problems.append("%s would not be ASCII" % rel); continue
        err = compiles(rel, data)
        if err:
            problems.append("%s would not compile: %s" % (rel, err)); continue
        todo.append((p, data))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_claude_" + stamp))
        t = p.with_name(p.name + ".tmp_claude"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_claude_engine_2026_10_15 -v")
    print("  python scripts\\claude_engine.py --credit   (free)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
