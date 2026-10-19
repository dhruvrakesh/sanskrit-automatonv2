#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_leak_guard_2026_10_19.py  (2026-10-19)  LEAK_GUARD_2026_10_19, KEEP_ON_EMPTY_2026_10_19

Two faults found on 19 Oct, reading the judge's lists (judge_review.py) and the T2 logs:
  1. The model's words to us inside a translation. 14 of 41,932 stored translations (12 English, 2 Hindi): a
     preamble ("Here is the translation of the verse, adhering to your specified principles:"), a second version
     after the first ("Let me give a cleaner rendering:", "Final rendering:", "Correction to the above"), the model
     reasoning aloud ("I will translate `dagdham` as ..."). The prompt asks for none of it (infer_mt rule 12); no
     filter caught it.
  2. A re-translation that came back empty wiped the English it was meant to improve, and nothing went to
     translation_history: four passages on 14 and 18 Oct (Mallapurana 11.5 and 11.9, markandeya_purana 28.2,
     Ganita 217.6); their old English survives only in data/retranslate/*.jsonl and in mt_cache.

scripts/text_filters.py: model_chatter() (the first phrase that is the model talking to us, else '') and
  strip_model_chatter() (the translation without it: the version after the last "... rendering:" line, without a
  leading preamble paragraph or a "Note: the text reads ..." line). Only the model's own phrases: "let me be
  suffering", "according to the rules", "Certainly, O son" are the Sanskrit's and are left alone.
scripts/translate_passages.py:
  - every answer goes through strip_model_chatter() first ([UNCHATTER]); what still talks to us is kept as nothing
    ([SKIP-CHATTER], chatter-filter);
  - KEEP_ON_EMPTY_2026_10_19: an English attempt that comes back empty never wipes the English a passage has
    ([KEPT]); only English that is itself the model's words is let go, archived first ([DROPPED], chatter-dropped).
    A Hindi row that is the model's words is archived and taken away the same way (the Hindi was never wiped).
scripts/infer_mt.py: the model's words to us are never cached (as refusals and echoes are not), so a retry asks again.
tests/test_claude_first_2026_10_15.py, tests/test_scholar_2026_10_14.py (their replay chains): infer_mt.py's and
  translate_passages.py's later backups may be .bak_leakguard_.
The mending of what is stored is scripts/heal_english.py (through translate_passages.py, which archives).
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_leakguard_<date>. No database change; nothing is called.
  python scripts\\patch_leak_guard_2026_10_19.py --check
  python scripts\\patch_leak_guard_2026_10_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'LEAK_GUARD_2026_10_19'
NEEDS = {'scripts/text_filters.py': 'PARK_ILLEGIBLE_2026_09_27', 'scripts/translate_passages.py': 'SCHOLAR_2026_10_14', 'scripts/infer_mt.py': 'CLAUDE_FIRST_2026_10_15', 'tests/test_claude_first_2026_10_15.py': 'CLAUDE_FIRST_2026_10_15', 'tests/test_scholar_2026_10_14.py': 'SCHOLAR_2026_10_14'}
FILES = list(NEEDS)
TAG = 'leakguard'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/text_filters.py', 1, r'''def should_translate(s: str, *, min_dev: float = 0.05) -> bool:
''', r'''# --- LEAK_GUARD_2026_10_19: the model's words to us are not the translation ----------
# Found on 19 Oct in the working English (26,330 passages) and the Hindi: a preamble ("Here is the translation of the
# verse, adhering to your specified principles:", yajur 38.5, nirukta 178.3), a second version after the first ("Let
# me give a cleaner rendering:", markandeya 94.8; "Final rendering:", Mallapurana 112.4; "Correction to the above",
# Ganita 229.12), and the model reasoning aloud ("I will translate `dagdham` as ...", harita 66.1). The prompt asks
# for none of it (infer_mt rule 12). strip_model_chatter() keeps the translation: the text after the last
# "... rendering:" line, without a leading preamble paragraph; model_chatter() names what is left that is not a
# translation, else ''. Only the model's own phrases: "let me be suffering", "according to the rules", "Certainly, O
# son", "I will provide you assistance" are the Sanskrit's words and are left alone.
_CHAT_PREAMBLE = re.compile(
    r"^\s*(?:(?:okay|ok|sure|certainly|of course)[,!.]?\s+)?"
    r"(?:(?:here is|here's|here are|below is|the following is|following is)\b[^\n]{0,200}?"
    r"\b(?:translation|rendering|version)s?\b[^\n]*"
    r"|let'?s (?:translate|render)\b[^\n]*)$", re.I | re.M)
_CHAT_ADDRESS = re.compile(   # only with a word of translating in the same opening paragraph (_CHAT_TRANSLAT)
    r"\b(?:your|the) (?:specified|given|stated) (?:principles|instructions|guidelines|requirements|rules)\b"
    r"|\b(?:applying|adhering to|following) your (?:principles|instructions|guidelines|rules)\b"
    r"|\bthe provided (?:sanskrit|hindi|english|devanagari)\b", re.I)
_CHAT_TRANSLAT = re.compile(r"\btranslat", re.I)
_CHAT_REDRAFT = re.compile(
    r"^[ \t]*(?:let me (?:give|offer|provide) (?:a |an )?(?:cleaner|better|clearer|smoother|more literal|more natural|"
    r"revised|corrected|final)[^\n:]{0,40}|(?:a |the )?(?:final|revised|corrected|cleaner|improved|better|clearer) "
    r"(?:rendering|translation|version)[^\n:]{0,40}|correction to the above[^\n:]{0,80})\s*:\s*$", re.I | re.M)
_CHAT_RESIDUAL = re.compile(
    r"\blet me (?:give|offer|provide) (?:a |an )?(?:cleaner|better|clearer|revised|corrected|final|more)\b"
    r"|\blet me (?:re-?translate|refine|rephrase|revise)\b(?=[^\n]{0,40}\b(?:translation|rendering|reading|word|text|"
    r"line|verse)\b|[^\n]{0,20}`)"
    r"|\blet'?s (?:refine|re-?translate|rephrase|reconsider|re-?examine|try again)\b"
    r"|\bI (?:will|'ll|shall) (?:translate|render|read|take) `"
    r"|\bcorrection to the above\b|\bfinal rendering\s*:"
    r"|\bas an AI\b|\b(?:a|the) language model\b", re.I)
_CHAT_NOTE = re.compile(r"^[ \t]*note\s*:\s*(?:the text reads|I have|I've|this translation|the translation)\b[^\n]*$",
                        re.I | re.M)


def model_chatter(t: str) -> str:
    """LEAK_GUARD_2026_10_19: the first phrase in t that is the model talking to us (a preamble, a second version, its
    reasoning), else ''."""
    if not t:
        return ""
    for rx in (_CHAT_REDRAFT, _CHAT_RESIDUAL, _CHAT_NOTE):
        m = rx.search(t)
        if m:
            return m.group(0).strip()[:80]
    first = re.split(r"\n\s*\n|\n", t.strip(), maxsplit=1)[0]
    m = _CHAT_PREAMBLE.match(first)
    if m:
        return m.group(0).strip()[:80]
    if len(first) < 300 and _CHAT_TRANSLAT.search(first):
        m = _CHAT_ADDRESS.search(first)
        if m:
            return m.group(0).strip()[:80]
    return ""


def strip_model_chatter(out: str):
    """LEAK_GUARD_2026_10_19: (text, what): the translation without the model's words around it. A second version
    after a "... rendering:" line replaces the first; a leading paragraph that introduces the translation is dropped;
    a "Note: the text reads ..." line is dropped. what names what went ('' when nothing did). What is left may still
    hold the model's reasoning: model_chatter() says so, and the write path then keeps nothing."""
    if not out or not out.strip():
        return out or "", ""
    t, what = out.strip(), []
    marks = list(_CHAT_REDRAFT.finditer(t))
    if marks:
        rest = t[marks[-1].end():].strip()
        if rest:
            t = rest
            what.append("first version")
    parts = re.split(r"(\n\s*\n|\n)", t, maxsplit=1)
    first = parts[0]
    if len(parts) == 3 and parts[2].strip() and (
            _CHAT_PREAMBLE.match(first) or (len(first) < 300 and _CHAT_TRANSLAT.search(first)
                                             and _CHAT_ADDRESS.search(first))):
        t = parts[2].strip()
        what.append("preamble")
    if _CHAT_NOTE.search(t):
        t2 = _CHAT_NOTE.sub("", t).strip()
        if t2:
            t = re.sub(r"\n{3,}", "\n\n", t2)
            what.append("note")
    return t, " and ".join(what)


def should_translate(s: str, *, min_dev: float = 0.05) -> bool:
''')

edit('scripts/translate_passages.py', 1, r'''                          load_parked)                 # PARK_ILLEGIBLE_2026_09_27
''', r'''                          load_parked,                 # PARK_ILLEGIBLE_2026_09_27
                          strip_model_chatter, model_chatter)   # LEAK_GUARD_2026_10_19
''')

edit('scripts/translate_passages.py', 2, r'''            empty_why = None if translation else "model-empty"
''', r'''            empty_why = None if translation else "model-empty"
            if translation:   # LEAK_GUARD_2026_10_19: the model's words to us are not the translation
                _unchat, _what = strip_model_chatter(translation)
                if _what:
                    print(f"  [UNCHATTER] p{page_no}.{idx}: dropped the model's {_what}")
                    translation = _unchat
                _chat = model_chatter(translation)
                if _chat:
                    print(f"  [SKIP-CHATTER] p{page_no}.{idx}: {_chat!r}")
                    translation = ""
                    empty_why = "chatter-filter"
''')

edit('scripts/translate_passages.py', 3, r'''                # l10n rows are not in passages_fts (English FTS is unchanged).
''', r'''                if not translation and prev and model_chatter(prev[0] or ""):
                    # LEAK_GUARD_2026_10_19: a row that is the model's words (its reasoning; a preamble over an echo of
                    # the source) was never a translation: archived, then taken away, so it is made again
                    cur.execute(
                        "INSERT INTO translation_history(passage_id, translation, "
                        "engine, mt_prompt_version, translation_score, "
                        "translation_qa, translated_at, reason, lang) "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        (rowid, prev[0], prev[1], prev[2], prev[3], prev[4],
                         prev[5], "chatter-dropped", TGT),
                    )
                    cur.execute("DELETE FROM translations_l10n WHERE passage_id=? AND lang=?", (rowid, TGT))
                    print(f"  [DROPPED] p{page_no}.{idx}: its {TGT} was the model's words; archived to translation_history")
                # l10n rows are not in passages_fts (English FTS is unchanged).
''')

edit('scripts/translate_passages.py', 4, r'''            else:
                # Phase Q: archive any existing English translation before
                # overwriting (no-op in default runs; preserves on --retranslate).
                if translation:
                    _archive_previous_translation(con, cur, rowid)

                update_parts = ["translation=?", "mt_prompt_version=?",
                                "translated_at=?", "translation_qa=?"]
                update_vals  = [translation,
                                ver if translation else None,
                                now_iso if translation else None,
                                tr_qa]
                if has_eng_col and active_engine:
                    update_parts.append("engine=?")
                    update_vals.append(active_engine)
                if has_tr_score and tr_score is not None:
                    update_parts.append("translation_score=?")
                    update_vals.append(tr_score)
                update_vals.append(rowid)
                cur.execute(
                    f"UPDATE passages SET {', '.join(update_parts)} WHERE rowid=?",
                    update_vals,
                )
                iast_val = meta_row.get("iast") or ""
                _update_fts(cur, rowid, cleaned, iast_val, translation or "")
                con.commit()
''', r'''            else:
                # KEEP_ON_EMPTY_2026_10_19: an attempt that comes back empty (a refusal, an echo, the model's own words)
                # never wipes the English a passage has. On 14 and 18 Oct four T2 re-translations emptied their passages
                # and nothing went to translation_history. Only English that is itself the model's words is let go,
                # archived first.
                _prev_en = con.execute("SELECT translation FROM passages WHERE rowid=?", (rowid,)).fetchone()
                _prev_en = (_prev_en[0] or "") if _prev_en else ""
                _keep = not translation and bool(_prev_en.strip()) and not model_chatter(_prev_en)
                if _keep:
                    print(f"  [KEPT] p{page_no}.{idx}: the new attempt came back empty; the English it had is kept")
                # Phase Q: archive any existing English translation before
                # overwriting (no-op in default runs; preserves on --retranslate).
                if translation:
                    _archive_previous_translation(con, cur, rowid)
                elif _prev_en.strip() and not _keep:   # LEAK_GUARD_2026_10_19
                    _archive_previous_translation(con, cur, rowid, reason="chatter-dropped")
                    print(f"  [DROPPED] p{page_no}.{idx}: its English was the model's words; archived to translation_history")

                if not _keep:   # KEEP_ON_EMPTY_2026_10_19
                    update_parts = ["translation=?", "mt_prompt_version=?",
                                    "translated_at=?", "translation_qa=?"]
                    update_vals  = [translation,
                                    ver if translation else None,
                                    now_iso if translation else None,
                                    tr_qa]
                    if has_eng_col and active_engine:
                        update_parts.append("engine=?")
                        update_vals.append(active_engine)
                    if has_tr_score and tr_score is not None:
                        update_parts.append("translation_score=?")
                        update_vals.append(tr_score)
                    update_vals.append(rowid)
                    cur.execute(
                        f"UPDATE passages SET {', '.join(update_parts)} WHERE rowid=?",
                        update_vals,
                    )
                    iast_val = meta_row.get("iast") or ""
                    _update_fts(cur, rowid, cleaned, iast_val, translation or "")
                con.commit()
''')

edit('scripts/infer_mt.py', 1, r'''    except ImportError:
        _is_junk = None; _is_echo = None
''', r'''    except ImportError:
        _is_junk = None; _is_echo = None
    try:   # LEAK_GUARD_2026_10_19
        from text_filters import model_chatter as _chat
    except ImportError:
        _chat = None
''')

edit('scripts/infer_mt.py', 2, r'''        if _is_echo is not None and _is_echo(t, out, tgt):
            continue  # never cache source-echoes (2026-08-02)
''', r'''        if _is_echo is not None and _is_echo(t, out, tgt):
            continue  # never cache source-echoes (2026-08-02)
        if _chat is not None and _chat(out):
            continue  # LEAK_GUARD_2026_10_19: never cache the model's words to us; a retry asks again
''')

edit('tests/test_claude_first_2026_10_15.py', 1, r'''                later = sorted(SCRIPTS.glob(f + ".bak_rejudge_*"))   # REJUDGE_2026_10_15 came after (scholar_translate.py)
''', r'''                later = sorted(SCRIPTS.glob(f + ".bak_rejudge_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_leakguard_*"))   # REJUDGE (scholar_translate.py); LEAK_GUARD_2026_10_19
''')

edit('tests/test_scholar_2026_10_14.py', 1, r'''                later = sorted(SCRIPTS.glob(f + ".bak_scholarv2_*"))   # SCHOLAR_V2_2026_10_14 came after (dashboard.py)
''', r'''                later = sorted(SCRIPTS.glob(f + ".bak_scholarv2_*")) \
                    or sorted(SCRIPTS.glob(f + ".bak_leakguard_*"))   # SCHOLAR_V2 (dashboard.py); LEAK_GUARD_2026_10_19
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw, raw.decode("utf-8").replace("\r\n", "\n"), nl


def compiles(data: bytes) -> str:
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
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        raw, src, nl = load(p)
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
        if MARK not in out:
            problems.append("%s: the edits do not carry %s" % (rel, MARK)); continue
        data = out.replace("\n", nl).encode("utf-8")
        if all(x < 128 for x in raw) and not all(x < 128 for x in data):
            problems.append("%s would not be ASCII" % rel); continue
        if rel.endswith(".py"):
            err = compiles(data)
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
        shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print('  python -m unittest tests.test_leak_guard_2026_10_19 tests.test_translation_filters tests.test_guards_2026_10_04')
    print('  python scripts\\heal_english.py   (the plan: what is stored that the guard mends)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
