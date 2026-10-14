#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_v2_2026_10_14.py  (2026-10-14)  SCHOLAR_V2_2026_10_14

A follow-up to SCHOLAR_2026_10_14 (released 838e6a4), after its pilot on the evening of 14 Oct: MBh01 1.1.0 to 1.1.24,
24 verses, $0.238 ($0.0099 a verse; the prior said $0.051), 23 passed, 1.1.8 flagged and accepted by a person. It got
the persons right where the working English does not (1.1.5 Lomaharsani, 1.1.8 the son of Pariksit), and it showed
three things to mend:
  - a Sanskrit sentence that runs over several verses came out verse by verse as fragments ("of that best of
    narratives, ...", 1.1.15-1.1.19 being one sentence);
  - the flash judge reads each verse alone: it gave the working English of 1.1.5 (the narrator called by his father's
    name) 5 of 5, so it cannot measure what the critic mends;
  - the notes ran to six a verse, glossed common words ("kings: narendra") and misspelt the Sanskrit ("amitategas").
This patch:
  scholar_translate.py (scholar-v2):
    --groups (on): one call (scholar-groups-v1, 40 verses a call) marks where each Sanskrit sentence ends; a sentence
      over several verses is drafted, read by the critic and judged as one passage, and stored verse by verse in its
      segments (group_ref, group_translation, moved);
    --compare (on): a second judge with the context (scholar-compare-v1, gemini-2.5-pro): the scholarly and the working
      English side by side, in an order it is not told, with the errors of each and the more faithful; a major error
      it finds in the scholarly English flags the verse;
    the prompt: three notes a verse at most, none for a common word, the Sanskrit in a note spelt as the IAST is;
      a speaker's line opens the translation without its own " //"; the critic reads the notes too;
    the price: the scholar-v2 rows' own mean once there are 10; before, scholar-v1's with a compare at half of it;
    the pages: a sentence over verses as one block with its verse numbers; the second judge's verdict; the earlier
      version under the fold; and render_prose: the text read as prose, chapter by chapter, its notes at the end of
      each chapter (--report writes it beside the verses: exports\\scholar_<doc>_prose.html).
    The rows are new columns (group_ref, group_translation, moved, compare, compare_better), added in place.
  dashboard.py: /scholar/<doc>/prose (read-only).
  import_mbh_gretil.py: a --src that is not there is said, not a traceback.

Needs SCHOLAR_2026_10_14 (scholar_translate.py, dashboard.py) and MBH_PROSE_2026_10_14 (import_mbh_gretil.py).
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and encodings; each .py is compiled before it
replaces the original; backups .bak_scholarv2_<date>.
  python scripts\\patch_scholar_v2_2026_10_14.py --check
  python scripts\\patch_scholar_v2_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "SCHOLAR_V2_2026_10_14"
NEEDS = {"scripts/scholar_translate.py": "SCHOLAR_2026_10_14", "scripts/dashboard.py": "SCHOLAR_2026_10_14",
         "scripts/import_mbh_gretil.py": "MBH_PROSE_2026_10_14"}
FILES = list(NEEDS)

E = []   # (file, number, old, new)
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = 'scripts/scholar_translate.py'

edit(ST, 1,
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14

A scholarly English beside the working one: verse by verse, with the context, a glossary that grows, notes, a critic
and revisions, and an independent judge. The working English (passages.translation) is never touched.
''',
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14

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
''')

edit(ST, 2,
     r'''MARK = "SCHOLAR_2026_10_14"
PROMPT_VERSION = "scholar-v1"
CRITIC_VERSION = "scholar-critic-v1"
''',
     r'''MARK = "SCHOLAR_2026_10_14"
MARK2 = "SCHOLAR_V2_2026_10_14"
PROMPT_VERSION = "scholar-v2"          # SCHOLAR_V2_2026_10_14 (scholar-v1 made the pilot's rows of 14 Oct)
CRITIC_VERSION = "scholar-critic-v2"
GROUPS_VERSION = "scholar-groups-v1"
COMPARE_VERSION = "scholar-compare-v1"
GROUP_MAX = 6          # verses in one sentence at most
GROUP_WINDOW = 40      # verses one groups call reads
''')

edit(ST, 3,
     r'''8. NOTES. Short, factual notes, only where a reader needs one: an epithet or patronymic, an allusion to a story told elsewhere, a technical or ritual term, a word with two possible readings, a textual problem. No note for what the translation already makes plain. Each note: {"anchor": the English word or words it explains, exactly as they stand in your translation, "kind": one of name|epithet|term|allusion|grammar|textual, "note": the note}.
9. DOUBTS. When a word can be read more than one way, or the Sanskrit looks corrupt or misprinted, say so in "doubts": the word, the readings, the one you chose and why. Otherwise leave "doubts" empty.
10. ONE VERSE. Translate only THE VERSE TO TRANSLATE. The verses before it (with an English that may be a working draft, and may be wrong) and after it are there only so that you understand this one: do not translate or repeat them. When the sentence runs on into the next verse, translate this verse's words as the opening of that sentence. End the translation with " //".
11. GLOSSARY. Propose an entry for each name or term this verse brings in that the glossary does not have: {"term": the IAST stem, "rendering": how the translation writes it, "kind": person|place|people|deity|term|epithet|other, "note": a gloss of a few words}.

Reply with one JSON object and nothing else:
{"translation": "...", "notes": [...], "glossary": [...], "doubts": "..."}"""
''',
     r'''8. NOTES. Short, factual notes, only where a reader needs one: an epithet or patronymic, an allusion to a story told elsewhere, a technical or ritual term, a word with two possible readings, a textual problem. At most three a verse. No note for a common word (king, sage, great-souled, lord, best of men), and none that says again what the translation makes plain. Spell every Sanskrit word in a note exactly as the IAST given spells it. Each note: {"anchor": the English word or words it explains, exactly as they stand in your translation, "kind": one of name|epithet|term|allusion|grammar|textual, "note": the note}.
9. DOUBTS. When a word can be read more than one way, or the Sanskrit looks corrupt or misprinted, say so in "doubts": the word, the readings, the one you chose and why. Otherwise leave "doubts" empty.
10. WHAT TO TRANSLATE. Translate only THE VERSE TO TRANSLATE, or THE VERSES TO TRANSLATE when one Sanskrit sentence runs over several verses. The verses before (with an English that may be a working draft, and may be wrong) and after are there only so that you understand: do not translate or repeat them. One verse whose sentence runs on into the next: translate its words as the opening of that sentence. Several verses: write their English as one passage of natural English prose, in the order English needs, and give it cut at the verse boundaries in "segments", [{"ref": the verse, "english": its part}], one for each verse, in order; joined with spaces the segments must read as that passage. Where English must move a word or a clause into another verse's part, do so, and say what moved in "moved". End the translation (the last segment) with " //".
11. GLOSSARY. Propose an entry for each name or term this verse brings in that the glossary does not have: {"term": the IAST stem, "rendering": how the translation writes it, "kind": person|place|people|deity|term|epithet|other, "note": a gloss of a few words}.
12. SPEAKERS. A speaker's line (... uv\u0101ca) opens the translation ("The s\u016bta said:"), and the speech follows it with no " //" after the speaker's line.

Reply with one JSON object and nothing else:
{"translation": "...", "segments": [], "moved": "", "notes": [...], "glossary": [...], "doubts": "..."}
("segments" and "moved" only when several verses are given.)"""
''')

edit(ST, 4,
     r'''SYSTEM_CRITIC = """You are a senior Sanskritist reviewing one verse of a draft scholarly English translation of {title}, as the editor of a critical-edition translation would. Compare the draft with the Sanskrit word by word. The verses before and after are there only to help you understand: judge only THE VERSE TO TRANSLATE.
''',
     r'''SYSTEM_CRITIC = """You are a senior Sanskritist reviewing one verse, or one sentence that runs over several verses, of a draft scholarly English translation of {title}, as the editor of a critical-edition translation would. Compare the draft with the Sanskrit word by word. The verses before and after are there only to help you understand: judge only THE VERSE (or THE VERSES) TO TRANSLATE. For several verses, judge the passage as a whole, and whether each segment holds its verse's words (or says what moved). Read the notes too: a wrong fact, or a Sanskrit word spelt otherwise than the IAST given, is an issue of type note.
''')

edit(ST, 5,
     r'''REVISE_ASK = ("Revise the translation. Make each change a finding rightly asks for; where a finding is wrong, keep your "
              "reading and say why in \"doubts\". Keep everything that was right. Reply with the same JSON object.")
''',
     r'''REVISE_ASK = ("Revise the translation. Make each change a finding rightly asks for; where a finding is wrong, keep your "
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
''')

edit(ST, 6,
     r'''    mine = json.dumps({"translation": cur["translation"], "notes": cur["notes"], "doubts": cur.get("doubts") or ""},
                      ensure_ascii=False)
    return base + "\n\nYOUR DRAFT:\n" + mine + "\n\nTHE REVIEWER'S FINDINGS:\n" + finds + "\n\n" + REVISE_ASK
''',
     r'''    mine = {"translation": cur["translation"], "notes": cur["notes"], "doubts": cur.get("doubts") or ""}
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
''')

edit(ST, 7,
     r'''    return {"translation": _s(d.get("translation"), 8000), "notes": notes[:12], "glossary": gl[:8],
            "doubts": _s(d.get("doubts"), 1000)}
''',
     r'''    segs = [{"ref": _s(x.get("ref"), 40), "english": _s(x.get("english"), 4000)}
            for x in (d.get("segments") or []) if isinstance(x, dict)]   # SCHOLAR_V2_2026_10_14: a sentence over verses
    return {"translation": _s(d.get("translation"), 8000), "notes": notes[:12], "glossary": gl[:8],
            "doubts": _s(d.get("doubts"), 1000), "segment_list": segs, "moved": _s(d.get("moved"), 400)}
''')

edit(ST, 8,
     r'''    if accepted(c) and (fid or 0) >= 4 and (flu or 0) >= 4:
        return "passed"
    return "flagged"
''',
     r'''    if accepted(c) and (fid or 0) >= 4 and (flu or 0) >= 4:
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
            cur["translation"] = " ".join(s_["english"] for s_ in segs if s_["english"])
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
''')

edit(ST, 9,
     r'''                system = (SYSTEM_DRAFT if kind == "draft" else SYSTEM_CRITIC).replace("{title}", self.meta["title"])
''',
     r'''                system = {"draft": SYSTEM_DRAFT, "groups": SYSTEM_GROUPS, "compare": SYSTEM_COMPARE}.get(
                    kind, SYSTEM_CRITIC).replace("{title}", self.meta["title"])   # SCHOLAR_V2_2026_10_14
''')

edit(ST, 10,
     r'''        system_len = len(SYSTEM_DRAFT if kind == "draft" else SYSTEM_CRITIC)
''',
     r'''        system_len = len({"draft": SYSTEM_DRAFT, "groups": SYSTEM_GROUPS, "compare": SYSTEM_COMPARE}.get(
            kind, SYSTEM_CRITIC))   # SCHOLAR_V2_2026_10_14
''')

edit(ST, 11,
     r'''      note TEXT, source TEXT, created_at TEXT, UNIQUE(doc_code, term));
    """)
    con.commit()
''',
     r'''      note TEXT, source TEXT, created_at TEXT, UNIQUE(doc_code, term));
    """)
    have = {r[1] for r in con.execute("PRAGMA table_info(scholar_translations)")}
    for c, t in (("group_ref", "TEXT"), ("group_translation", "TEXT"), ("moved", "TEXT"), ("compare", "TEXT"),
                 ("compare_better", "TEXT")):   # SCHOLAR_V2_2026_10_14: added in place
        if c not in have:
            con.execute("ALTER TABLE scholar_translations ADD COLUMN %s %s" % (c, t))
    con.commit()
''')

edit(ST, 12,
     r'''    try:
        if has_table(con, "scholar_translations"):
            n, avg, mx = con.execute("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE "
                                     "engine = ? AND cost_usd > 0", (a.engine,)).fetchone()
            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d verses" % n
    except sqlite3.Error:
        pass
''',
     r'''    try:   # SCHOLAR_V2_2026_10_14: this prompt's rows when there are 10; before, scholar-v1's with a compare at half
        if has_table(con, "scholar_translations"):
            q = ("SELECT COUNT(*), AVG(cost_usd), MAX(cost_usd) FROM scholar_translations WHERE engine = ? AND "
                 "cost_usd > 0 AND prompt_version LIKE ?")
            n, avg, mx = con.execute(q, (a.engine, PROMPT_VERSION + "+%")).fetchone()
            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d %s verses" % (n, PROMPT_VERSION)
            else:
                n1, avg1, mx1 = con.execute(q, (a.engine, "scholar-v1+%")).fetchone()
                if n1 and n1 >= MEASURED_AFTER:
                    k = 1.5 if getattr(a, "compare", False) else 1.0
                    typ, top = float(avg1) * k, float(mx1) * k
                    how = "measured on %d scholar-v1 verses%s" % (n1, ", with a compare call at half of it" if k > 1 else "")
    except sqlite3.Error:
        pass
''')

edit(ST, 13,
     r'''def one_verse(a, allp, i, meta, done, asker, con, call: float) -> dict:
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
''',
     r'''def compare(asker, base: str, scholarly: str, working: str, pid: int):
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
    spent0 = asker.spent
    d, _c = asker.ask("draft", base)
    cur = clean_unit(d, refs)
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
        rv = clean_unit(rv, refs)
        if rv is None:
            note = "the revision came back without a translation; the last version is kept"
            break
        cur = rv
        revisions += 1
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
    if getattr(a, "compare", False) and working:
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
                     "prompt_version": "%s+%s" % (PROMPT_VERSION, CRITIC_VERSION), "cost_usd": round(cost / len(xs), 6),
                     "created_at": at, "group_ref": gref, "group_translation": cur["translation"] if gref else None,
                     "moved": cur.get("moved") or None,
                     "compare": json.dumps(cmp_, ensure_ascii=False) if cmp_ else None,
                     "compare_better": cmp_["better"] if cmp_ else None,
                     "_glossary": cur["glossary"] if k == 0 else []})
    return rows


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
''')

edit(ST, 14,
     r'''        "status", "engine", "judge_engine", "prompt_version", "cost_usd", "created_at")
''',
     r'''        "status", "engine", "judge_engine", "prompt_version", "cost_usd", "created_at",
        "group_ref", "group_translation", "moved", "compare", "compare_better")   # SCHOLAR_V2_2026_10_14
''')

edit(ST, 15,
     r'''def run(a, allp: list, picked: list, meta: dict, done: dict, asker, con, price: dict, budget_ok=None) -> dict:
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
''',
     r'''def run(a, allp: list, picked: list, meta: dict, done: dict, asker, con, price: dict, budget_ok=None) -> dict:
    out = {"passed": [], "flagged": [], "source_doubt": [], "failed": [], "stopped": "", "spent": 0.0, "grouped": 0}
    logp = Path(a.log_dir) / ("%s_%s.jsonl" % (re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc),
                                              datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    logp.parent.mkdir(parents=True, exist_ok=True)
    out["log"] = str(logp)
    units = units_of(a, allp, picked, meta, asker, out, price["call"])   # SCHOLAR_V2_2026_10_14: sentences
    fails = n = 0
    for u in units:
        xs = [allp[i] for i in u]
        need = price["typical"] * len(u)
        if budget_ok is not None and not budget_ok(con, need):
            out["stopped"] = "the spend cap is reached (python scripts\\set_budget.py shows it)"
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
                     ("  [the second judge: %s]" % rec["compare_better"]) if rec.get("compare_better") else ""))
            log = {k: rec[k] for k in COLS if k not in ("draft",)}
            log.update(version=v, where=ref_of(x), mark=MARK, working_english=x.get("english") or "", draft=rec["draft"])
            with open(logp, "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
    out["spent"] = asker.spent
    return out
''')

edit(ST, 16,
     r'''header,.pager,details{display:none}.v{break-inside:avoid}}
"""
''',
     r'''header,.pager,details{display:none}.v{break-inside:avoid}}
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
''')

edit(ST, 17,
     r'''def render_doc(con, doc: str, offset: int = 0, limit=200, nav: bool = False) -> str:
    """One text's scholarly English beside its Sanskrit and its working English, verse by verse."""
    e = html.escape
    if not has_table(con, "scholar_translations"):
        rows = []
    else:
        q = ("SELECT s.*, p.text AS p_text, p.iast AS p_iast, p.translation AS p_english FROM scholar_translations s LEFT "
             "JOIN passages p ON p.id = s.passage_id WHERE s.doc_code = ? AND s.id IN (SELECT MAX(id) FROM "
             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx")
''',
     r'''def _safe(doc: str) -> str:
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
        iss += ('<div>Critic, reading %d: fidelity %s, completeness %s, %s%s</div>'
                % (k, c.get("fidelity"), c.get("completeness"), e(c.get("verdict") or ""),
                   ('<ul class="iss">%s</ul>' % items) if items else ""))
    return iss


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
    if any(r.get("translation") for r in u[1:]):
        english = _marks_html([(r["verse_ref"], r.get("translation") or "") for r in u], notes)
    else:
        english = _marks_html([(r0["verse_ref"], r0.get("group_translation") or r0.get("translation") or "")], notes)
    notes_html = ("<ol class=\"notes\">%s</ol>" % "".join(
        '<li><span class="k">%s</span> <b>%s</b>: %s</li>' % (e(n.get("kind") or ""), e(n.get("anchor") or ""),
                                                               e(n.get("note") or "")) for n in notes)) if notes else ""
    extra = ""
    if r0.get("doubts"):
        extra += '<div class="doubt">Doubts: %s</div>' % e(r0["doubts"])
    if r0.get("moved"):
        extra += '<div class="doubt">Moved between the verses: %s</div>' % e(r0["moved"])
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
             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx")
''')

edit(ST, 18,
     r'''    if sc_f:
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
''',
     r'''    if sc_f:
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
''')

edit(ST, 19,
     r'''        det = ('<details><summary>The working English, the first draft, the critic</summary><div class="lbl" '
               'style="margin-top:8px">The working English (on the site)</div><p class="wk">%s</p>%s%s<div>The judge: %s'
               '</div></details>'
               % (e(r.get("p_english") or "-"),
                  ('<div class="lbl">The first draft</div><p class="wk">%s</p>' % e(r["draft"]))
                  if r.get("draft") and r.get("draft") != r.get("translation") else "", iss, e(r.get("judge_reason") or "")))
''',
     r'''        chip, cmp_lines = _compare_html(_loads(r.get("compare"), {}) or None)   # SCHOLAR_V2_2026_10_14
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
''')

edit(ST, 20,
     r'''    body = intro + '<div class="sum">%s</div>' % chips + arts + pager
    return _page("Scholarly English: " + doc, body, nav)
''',
     r'''    body = intro + '<div class="sum">%s</div>' % chips + arts + pager
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
                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx",
                          (doc, doc))
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
            if len(u) > 1 and any(r.get("translation") for r in u[1:]):
                pairs = [(r["verse_ref"], r.get("translation") or "") for r in u]
            else:
                pairs = [(r0["verse_ref"], r0.get("group_translation") or r0.get("translation") or "")]
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
''')

edit(ST, 21,
     r'''    ap.add_argument("--log-dir", default="data/scholar")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
''',
     r'''    ap.add_argument("--log-dir", default="data/scholar")
    ap.add_argument("--no-groups", action="store_true", help="SCHOLAR_V2_2026_10_14: every verse alone")
    ap.add_argument("--no-compare", action="store_true", help="SCHOLAR_V2_2026_10_14: no second judge")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    a.groups, a.compare = not a.no_groups, not a.no_compare   # SCHOLAR_V2_2026_10_14
''')

edit(ST, 22,
     r'''            page = render_doc(con, a.doc, limit=None)
        finally:
            con.close()
        out = Path(a.exports) / ("scholar_%s.html" % re.sub(r"[^A-Za-z0-9_.-]", "_", a.doc))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print("VERDICT: written %s (%d bytes)" % (out, out.stat().st_size))
''',
     r'''            page = render_doc(con, a.doc, limit=None)
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
''')

edit(ST, 23,
     r'''    print("  cost: about %s a verse, up to %s with %d revisions (%s): about %s for %d, at most %s"
          % (usd(price["typical"]), usd(price["most"]), a.rounds, price["how"], usd(est), len(picked), usd(most)))
''',
     r'''    print("  cost: about %s a verse, up to %s with %d revisions (%s): about %s for %d, at most %s"
          % (usd(price["typical"]), usd(price["most"]), a.rounds, price["how"], usd(est), len(picked), usd(most)))
    print("  sentences: %s; the second judge: %s   (%s)" % (
        ("one over several verses is translated whole (%s)" % GROUPS_VERSION) if a.groups else "every verse alone",
        ("the scholarly and the working English side by side (%s)" % COMPARE_VERSION) if a.compare else "none",
        MARK2))
''')

edit(ST, 24,
     r'''              % (a.doc, sel, a.limit, " --redo" if a.redo else "", cap))
''',
     r'''              % (a.doc, sel, a.limit, (" --redo" if a.redo else "") + (" --no-groups" if a.no_groups else "")
                 + (" --no-compare" if a.no_compare else ""), cap))
''')

edit(ST, 25,
     r'''    if res["stopped"]:
        print("  STOPPED: %s" % res["stopped"])
''',
     r'''    if res.get("grouped"):   # SCHOLAR_V2_2026_10_14
        print("  sentences over several verses, each translated whole: %d" % res["grouped"])
    if res["stopped"]:
        print("  STOPPED: %s" % res["stopped"])
''')

edit(ST, 26,
     r'''    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (then read it: http://127.0.0.1:5057/scholar/%s)"
          % (a.doc, a.doc))
    return 0
''',
     r'''    print("NEXT: python scripts\\scholar_translate.py --doc %s --report   (then read it: http://127.0.0.1:5057/scholar/%s)"
          % (a.doc, a.doc))
    print("ALSO: as prose: http://127.0.0.1:5057/scholar/%s/prose   (SCHOLAR_V2_2026_10_14)" % a.doc)
    return 0
''')

# ---------------------------------------------------------------------------------------------- dashboard.py
edit('scripts/dashboard.py', 1,
     r'''    return _scholar_page(doc)


def _scholar_page(doc):
''',
     r'''    return _scholar_page(doc)


@app.get("/scholar/<doc>/prose")
def scholar_prose_page(doc):
    """SCHOLAR_V2_2026_10_14: one text's scholarly English read as prose, chapter by chapter, its notes at each
    chapter's end. Reads the database read-only."""
    doc = _validate_doc(doc)
    if not doc:
        return "invalid doc", 400
    return _scholar_page(doc, prose=True)


def _scholar_page(doc, prose=False):
''')

edit('scripts/dashboard.py', 2,
     r'''            if doc:
                try:
                    off = max(0, int(request.args.get("offset", 0) or 0))
''',
     r'''            if doc and prose:   # SCHOLAR_V2_2026_10_14
                return _st.render_prose(con, doc, nav=True)
            if doc:
                try:
                    off = max(0, int(request.args.get("offset", 0) or 0))
''')

# ---------------------------------------------------------------------------------------------- import_mbh_gretil.py
edit('scripts/import_mbh_gretil.py', 1,
     r'''    if src:
        return pathlib.Path(src).read_text(encoding="utf-8", errors="ignore")
''',
     r'''    if src:
        if not pathlib.Path(src).is_file():   # SCHOLAR_V2_2026_10_14: said, not a traceback
            sys.exit("REFUSE: %s not found. Save the book's e-text there first (from the GRETIL or the BORI page), or "
                     "leave --src out to download it from GRETIL." % src)
        return pathlib.Path(src).read_text(encoding="utf-8", errors="ignore")
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_scholarv2_" + stamp))
        t = p.with_name(p.name + ".tmp_scholarv2"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed (the new columns are added at the next --yes or --review). The dry run:")
    print("  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --limit 24 --redo")
    print("dashboard.py shows /scholar/<doc>/prose when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
