#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_scholar_v21_2026_10_14.py  (2026-10-14)  SCHOLAR_V21_2026_10_14

A follow-up to SCHOLAR_V2_2026_10_14 (released 23c9ede), after scholar-v2's pilot of 14 Oct, 21:13: MBh01 1.1.0 to
1.1.24, 24 verses, $0.256; 15 passed, 5 flagged (1.1.15-1.1.19, one sentence), 4 failed (1.1.20-1.1.23, one sentence:
"the draft came back without a translation"). Three sentences over verses came out whole and passed (1.1.8-1.1.11,
1.1.13-1.1.14). What it showed to mend:
  - scholar-v2 replaced a sentence's passage by its segments joined. The segments hold each verse's words in the
    Sanskrit's order, so the passage the draft wrote in the order English needs (its "moved" says it put "we wish to
    hear" first) was lost, and 1.1.15-1.1.19 read as a chain of fragments again; the critic flagged it after two
    revisions (fidelity 3: "breaks the single, complex Sanskrit sentence into a series of sentence fragments");
  - a draft cut off at the token limit was asked again only when no text at all came back, and the log does not say
    how an answer ended; a sentence whose draft failed failed whole, its verses with it;
  - the pages order the rows by the place they had when they were made: MBh01's prose comes in (reingest_pages.py)
    and moves the verses of its pages.
This patch:
  scholar_translate.py (scholar-v2.1; the critic stays scholar-critic-v2):
    clean_unit: the passage is the draft's "translation"; the segments say which of its words render which verse and
      need not read in its order. Only a passage much shorter than its segments (not a passage) gives way to them;
    the prompt's rule 10 says so ("the main clause may come first, as English wants it");
    Gemini.ask: an answer cut off at the token limit (MAX_TOKENS) and not JSON is asked again with room even when some
      text came back; a draft that is still not JSON is asked once more; self.last says how the answer ended, and a
      failed draft says it ("it ended MAX_TOKENS, 31,204 characters, not JSON");
    run(): a sentence whose draft fails is translated verse by verse ("split");
    prices(): scholar-v2.1 is priced by the scholar-v2 rows until 10 of its own are measured;
    the header names the prompt version; the summary counts the sentences split;
    the pages: the rows ordered by their passage's place now; a sentence whose passage is not its segments joined
      is shown whole after its verse range (1.1.15-19), its segments under the fold; the prose view the same.
  import_mbh_gretil.py: the e-text's appendix passages (01,001.053b@002_0001: lines the critical edition prints in its
    appendix, not in the constituted text) are counted as excluded, not "NOT READ" (5,028 lines in book 1); the Next
    lines name the --out directory, and for a book already in the database the reingest plan.

Needs SCHOLAR_V2_2026_10_14 (scholar_translate.py, import_mbh_gretil.py).
Anchored, all-or-nothing, marker-idempotent per file; keeps line endings and encodings; each .py is compiled before it
replaces the original; backups .bak_scholarv21_<date>.
  python scripts\\patch_scholar_v21_2026_10_14.py --check
  python scripts\\patch_scholar_v21_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "SCHOLAR_V21_2026_10_14"
NEEDS = {"scripts/scholar_translate.py": "SCHOLAR_V2_2026_10_14", "scripts/import_mbh_gretil.py": "SCHOLAR_V2_2026_10_14"}
FILES = list(NEEDS)

E = []   # (file, number, old, new)
def edit(f, n, old, new):
    E.append((f, n, old, new))


ST = 'scripts/scholar_translate.py'

edit(ST, 1,
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14
''',
     r'''scholar_translate.py  (2026-10-14)  SCHOLAR_2026_10_14, SCHOLAR_V2_2026_10_14, SCHOLAR_V21_2026_10_14
''')

edit(ST, 2,
     r'''  - render_prose (/scholar/<doc>/prose; --report writes it too): the text read as prose, chapter by chapter, the notes
    at each chapter's end.
''',
     r'''  - render_prose (/scholar/<doc>/prose; --report writes it too): the text read as prose, chapter by chapter, the notes
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
''')

edit(ST, 3,
     r'''PROMPT_VERSION = "scholar-v2"          # SCHOLAR_V2_2026_10_14 (scholar-v1 made the pilot's rows of 14 Oct)
''',
     r'''MARK3 = "SCHOLAR_V21_2026_10_14"
PROMPT_VERSION = "scholar-v2.1"        # SCHOLAR_V21_2026_10_14 (scholar-v2: 14 Oct 21:13; scholar-v1: the pilot of 18:25)
''')

edit(ST, 4,
     r'''Several verses: write their English as one passage of natural English prose, in the order English needs, and give it cut at the verse boundaries in "segments", [{"ref": the verse, "english": its part}], one for each verse, in order; joined with spaces the segments must read as that passage. Where English must move a word or a clause into another verse's part, do so, and say what moved in "moved". End the translation (the last segment) with " //".''',
     r'''Several verses: write "translation" as one passage of natural English prose in the order English needs (the main clause may come first, as English wants it), and give in "segments", [{"ref": the verse, "english": its part}], one for each verse, in order, the words of your passage that render that verse. The segments need not read as the passage, nor in its order; together they hold all of it. Say in "moved" what English moved, and from which verse. End the passage with " //".''')

edit(ST, 5,
     r'''        if [s_["ref"] for s_ in segs] == list(refs) and any(s_["english"] for s_ in segs):
            cur["segments"] = {s_["ref"]: s_["english"] for s_ in segs}
            cur["translation"] = " ".join(s_["english"] for s_ in segs if s_["english"])
    return cur
''',
     r'''        if [s_["ref"] for s_ in segs] == list(refs) and any(s_["english"] for s_ in segs):
            cur["segments"] = {s_["ref"]: s_["english"] for s_ in segs}
            joined = " ".join(s_["english"] for s_ in segs if s_["english"])
            # SCHOLAR_V21_2026_10_14: the passage stays as the draft wrote it (in the order English needs); only one much
            # shorter than its segments, which is no passage, gives way to them
            if len(cur["translation"]) < 0.6 * len(joined):
                cur["translation"] = joined
    return cur
''')

edit(ST, 6,
     r'''class Gemini:
    """The real calls:''',
     r'''_FINISH = {"1": "STOP", "2": "MAX_TOKENS", "3": "SAFETY", "4": "RECITATION", "5": "OTHER"}


def _finish_name(f) -> str:
    """SCHOLAR_V21_2026_10_14: how an answer ended, by name (the SDK gives an enum, or its number)."""
    n = getattr(f, "name", None)
    if n:
        return str(n)
    s = str(f if f is not None else "")
    return _FINISH.get(s, s.split(".")[-1] or "?")


class Gemini:
    """The real calls:''')

edit(ST, 7,
     r'''    def ask(self, kind: str, msg: str) -> tuple:
        """(the JSON answer or None, $)."""
        txt, finish, cost = self._once(kind, msg, 8192)
        if not txt and ("MAX_TOKENS" in str(finish) or str(finish) == "2"):
            txt, finish, more = self._once(kind, msg, 16384)   # its thinking took the budget: once more, with room
            cost += more
        return parse_json(txt), cost
''',
     r'''    def ask(self, kind: str, msg: str) -> tuple:
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
''')

edit(ST, 8,
     r'''    if cur is None:
        raise CallFailed("the draft came back without a translation")
''',
     r'''    if cur is None:
        last = getattr(asker, "last", None) or {}   # SCHOLAR_V21_2026_10_14: how it ended
        raise CallFailed("the draft came back without a translation%s" % (
            (" (it ended %s, %s characters%s)" % (last.get("finish") or "?", "{:,}".format(last.get("chars") or 0),
                                                 "" if last.get("json") else ", not JSON")) if last else ""))
''')

edit(ST, 9,
     r'''            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d %s verses" % (n, PROMPT_VERSION)
            else:
''',
     r'''            fam = PROMPT_VERSION.split(".")[0]   # SCHOLAR_V21_2026_10_14: scholar-v2.1 is priced by scholar-v2's rows
            nf, avgf, mxf = (con.execute(q, (a.engine, fam + "+%")).fetchone() if fam != PROMPT_VERSION
                             else (0, None, None))
            if n and n >= MEASURED_AFTER:
                typ, top, how = float(avg), float(mx), "measured on %d %s verses" % (n, PROMPT_VERSION)
            elif nf and nf >= MEASURED_AFTER:
                typ, top, how = float(avgf), float(mxf), "measured on %d %s verses" % (nf, fam)
            else:
''')

edit(ST, 10,
     r'''    out = {"passed": [], "flagged": [], "source_doubt": [], "failed": [], "stopped": "", "spent": 0.0, "grouped": 0}
''',
     r'''    out = {"passed": [], "flagged": [], "source_doubt": [], "failed": [], "stopped": "", "spent": 0.0, "grouped": 0,
           "split": 0}   # SCHOLAR_V21_2026_10_14: split, the sentences that failed whole and went verse by verse
''')

edit(ST, 11,
     r'''    fails = n = 0
    for u in units:
        xs = [allp[i] for i in u]
''',
     r'''    fails = n = 0
    queue = list(units)   # SCHOLAR_V21_2026_10_14: a sentence that fails whole goes back verse by verse
    while queue:
        u = queue.pop(0)
        xs = [allp[i] for i in u]
''')

edit(ST, 12,
     r'''        except CallFailed as e:
            out["spent"] = asker.spent
            fails += 1
''',
     r'''        except CallFailed as e:
            out["spent"] = asker.spent
            if len(u) > 1:   # SCHOLAR_V21_2026_10_14: the sentence failed whole: each of its verses alone
                out["split"] += 1
                print("  %s to %s: the sentence failed (%s); each verse alone" % (ref_of(xs[0]), ref_of(xs[-1]), e))
                queue[0:0] = [[i] for i in u]
                continue
            fails += 1
''')

edit(ST, 13,
     r'''def _group_article(u: list) -> str:
''',
     r'''def _ws(t) -> str:
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
''')

edit(ST, 14,
     r'''    if any(r.get("translation") for r in u[1:]):
        english = _marks_html([(r["verse_ref"], r.get("translation") or "") for r in u], notes)
    else:
        english = _marks_html([(r0["verse_ref"], r0.get("group_translation") or r0.get("translation") or "")], notes)
''',
     r'''    if _inline(u):
        english = _marks_html([(r["verse_ref"], r.get("translation") or "") for r in u], notes)
    else:   # SCHOLAR_V21_2026_10_14: the passage whole, after its verse range; its segments under the fold
        english = _marks_html([(_range(u), r0.get("group_translation") or r0.get("translation") or "")], notes)
''')

edit(ST, 15,
     r'''    if r0.get("moved"):
        extra += '<div class="doubt">Moved between the verses: %s</div>' % e(r0["moved"])
''',
     r'''    if r0.get("moved"):
        extra += '<div class="doubt">Moved between the verses: %s</div>' % e(r0["moved"])
    if not _inline(u) and any(r.get("translation") for r in u[1:]):   # SCHOLAR_V21_2026_10_14
        extra += ('<details class="segs"><summary>Verse by verse: the words of the passage that render each verse'
                  '</summary>%s</details>' % "".join('<p class="wk"><span class="vr">%s</span>%s</p>'
                                                     % (e(r["verse_ref"] or ""), e(r.get("translation") or "-"))
                                                     for r in u))
''')

edit(ST, 16,
     r'''            if len(u) > 1 and any(r.get("translation") for r in u[1:]):
                pairs = [(r["verse_ref"], r.get("translation") or "") for r in u]
            else:
                pairs = [(r0["verse_ref"], r0.get("group_translation") or r0.get("translation") or "")]
''',
     r'''            if _inline(u):
                pairs = [(r["verse_ref"], r.get("translation") or "") for r in u]
            else:   # SCHOLAR_V21_2026_10_14: the passage whole, after its verse range
                pairs = [(_range(u), r0.get("group_translation") or r0.get("translation") or "")]
''')

edit(ST, 17,
     r'''             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx")
        cur = con.execute(q + ''',
     r'''             "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY COALESCE(p.page_no, s.page_no), "
             "COALESCE(p.idx, s.idx), s.id")   # SCHOLAR_V21_2026_10_14: the passage's place now
        cur = con.execute(q + ''')

edit(ST, 18,
     r'''                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY s.page_no, s.idx",
                          (doc, doc))''',
     r'''                          "scholar_translations WHERE doc_code = ? GROUP BY passage_id) ORDER BY COALESCE(p.page_no, "
                          "s.page_no), COALESCE(p.idx, s.idx), s.id", (doc, doc))   # SCHOLAR_V21_2026_10_14''')

edit(ST, 19,
     r'''          % (MARK, "RUN" if a.yes else "DRY RUN (nothing called, nothing written)", a.engine, a.rounds, a.judge_engine))
''',
     r'''          % ("%s (%s)" % (MARK3, PROMPT_VERSION), "RUN" if a.yes else "DRY RUN (nothing called, nothing written)",
             a.engine, a.rounds, a.judge_engine))
''')

edit(ST, 20,
     r'''    if res.get("grouped"):   # SCHOLAR_V2_2026_10_14
        print("  sentences over several verses, each translated whole: %d" % res["grouped"])
''',
     r'''    if res.get("grouped"):   # SCHOLAR_V2_2026_10_14
        print("  sentences over several verses, each translated whole: %d" % res["grouped"])
    if res.get("split"):   # SCHOLAR_V21_2026_10_14
        print("  sentences that failed whole, then translated verse by verse: %d" % res["split"])
''')


IM = 'scripts/import_mbh_gretil.py'

edit(IM, 1,
     r'''REF_RE = re.compile(r"^\d{2},?\d{3}\.?\d{3}")
''',
     r'''REF_RE = re.compile(r"^\d{2},?\d{3}\.?\d{3}")
# SCHOLAR_V21_2026_10_14: an appendix passage of the e-text (01,001.053b@002_0001): the critical edition prints it in its
# appendix, not in the constituted text. It is left out as the star passages are, and counted, not "NOT READ".
APPX_RE = re.compile(r"^\d{2},?\d{3}\.?\d{3}[A-Za-z]?@\d")
''')

edit(IM, 2,
     r'''    kept = skipped_star = prose_lines = 0
''',
     r'''    kept = skipped_star = prose_lines = appendix = 0   # SCHOLAR_V21_2026_10_14: appendix
''')

edit(IM, 3,
     r'''        if not m:
            if REF_RE.match(line):
                unread.append(line[:60])
            continue
''',
     r'''        if not m:
            if APPX_RE.match(line):   # SCHOLAR_V21_2026_10_14
                appendix += 1
            elif REF_RE.match(line):
                unread.append(line[:60])
            continue
''')

edit(IM, 4,
     r'''    if unread:
        print("  NOT READ: %d lines that look like a reference (the first: %s)" % (len(unread), unread[0]))
''',
     r'''    if appendix:   # SCHOLAR_V21_2026_10_14
        print("  appendix passages excluded: %d lines (the edition prints them in its appendix, not in the constituted "
              "text)" % appendix)
    if unread:
        print("  NOT READ: %d lines that look like a reference (the first: %s)" % (len(unread), unread[0]))
''')

edit(IM, 5,
     r'''        print(f"\nNext:\n  python scripts/ingest_jsonl_fast.py --doc {doc_code} "
              f'--glob "data/raw/{doc_code}_*.jsonl" --category mahabharata --no-segment')
''',
     r'''        print(f"\nNext, a book not yet in the database:\n  python scripts/ingest_jsonl_fast.py --doc {doc_code} "
              f'--glob "{out_dir.as_posix()}/{doc_code}_*.jsonl" --category mahabharata --no-segment')
        print(f"Next, a book already in the database (the plan, free):\n  python scripts/reingest_pages.py --doc {doc_code} "
              f"--merged-dir {out_dir} --no-segment")   # SCHOLAR_V21_2026_10_14
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/scholar_translate.py").exists():
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
            py_compile.compile(tmp, cfile=tmp + "c", doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            for t_ in (tmp, tmp + "c"):
                if os.path.exists(t_):
                    os.unlink(t_)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_scholarv21_" + stamp))
        t = p.with_name(p.name + ".tmp_scholarv21"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The two runs it is for (dry runs first, free):")
    print("  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --from-ref 1.1.15 --limit 9 --redo")
    print("  python scripts\\scholar_translate.py --doc MBh01 --pages 1 --from-ref 1.1.1 --limit 1   (once the prose is in)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
