#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_refs_2026_10_21.py  (2026-10-21)  ETEXT_REFS_2026_10_21

Found on the evening of 21 Oct, in the Surya Siddhanta's e-text witness (GRETIL; Michio Yano's input): each verse is
a line that begins with its pada label (1.31a: ... 1.31b: ...//), and the e-text gives the value of a verse's
numerals in brackets at its end ((364220): Jupiter's revolutions in a yuga). etext_witness.take_ref() read that value
(R_PAR) as the verse's reference: 18 verses had a verse_ref of 364220, 39, 225, 260.40 (chapter "260"), and the value
had been taken out of their text and their romanized line; the other verses had no reference, and the chapter of all
came from the colophons (1, then 2), not from the labels (1 to 14).

scripts/etext_witness.py (needs ETEXT_ORTHO_2026_10_21):
  - take_ref(line, labels=True): a line that begins with a pada label keeps all its text, the label and the value in
    brackets too, and its reference is the label's verse (1.31), its chapter the label's chapter (1); labels=False
    reads as before (mend_witness.py compares the two).
scripts/mend_witness.py (needs WITNESS_MEND_2026_10_21):
  - the plan reads each line again from the witness's source file, when its sha256 is the one the witness was read
    from: "the reference only" (the label's verse and chapter; the text the same) or respelled ("the value in
    brackets" put back; the scholarly English re-based, the same English, with the verse's reference); the latest
    scholarly English of a verse whose reference alone changes has its reference set (the English untouched); a
    reference the e-text gives two verses (its labels' slips) is named, not mended. --yes writes the reference and the
    chapter into the page files and the database (ingest_jsonl_fast.py, the ids kept) and checks them.
tests/test_etext_ortho_2026_10_21.py (its replay chain): etext_witness.py's later backup may be .bak_etextrefs_.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_etextrefs_<date>. No database change; nothing is called. The Surya Siddhanta is mended afterwards by
  python scripts\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext          (the plan)
  python scripts\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext --yes    (a backup first)

  python scripts\\patch_etext_refs_2026_10_21.py --check
  python scripts\\patch_etext_refs_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_REFS_2026_10_21'
NEEDS = {'scripts/etext_witness.py': 'ETEXT_ORTHO_2026_10_21', 'scripts/mend_witness.py': 'WITNESS_MEND_2026_10_21',
         'tests/test_etext_ortho_2026_10_21.py': 'ETEXT_ORTHO_2026_10_21'}
FILES = list(NEEDS)
TAG = 'etextrefs'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


# ---- scripts/etext_witness.py -----------------------------------------------------------------------
edit('scripts/etext_witness.py', 1, r'''def take_ref(line: str):
    """(text without its reference, ref, where): where is "end", "start" or "part" (a pada, a line of a verse)."""
''', r'''# ETEXT_REFS_2026_10_21: a line that begins with the e-text's pada label (1.31a: ... 1.31b: ...//(364220)) has its
# reference there; the number in brackets at its end is the e-text's value of the verse's numerals (364220, Jupiter's
# revolutions in a yuga), not a reference: read as one (R_PAR) until 21 Oct, it was taken out of the text of 18 of the
# Surya Siddhanta's verses, and the chapter came from the colophons (1, then 2), not from the labels (1 to 14). A
# chapter's first verse begins with its title in brackets ([spa\u1e63\u1e6d\u0101dhik\u0101raH] 2.01a: ...).
G_LABEL_HEAD = re.compile(r"^\s*(?:\[[^\]\n]{1,80}\]\s*)?(\d+\.\d+)[a-f]?:")   # [bh\u016bgola] 12.01a: a chapter's first


def take_ref(line: str, labels: bool = True):
    """(text without its reference, ref, where): where is "end", "start" or "part" (a pada, a line of a verse).
    ETEXT_REFS_2026_10_21: a line that begins with a pada label (1.31a:) keeps all its text, the label too, and its
    reference is the label's verse; labels=False reads as before (mend_witness.py compares the two)."""
    if labels:
        m = G_LABEL_HEAD.match(line)
        if m:
            return line, norm_ref(m.group(1)), "part"
''')

# ---- scripts/mend_witness.py ------------------------------------------------------------------------
edit('scripts/mend_witness.py', 1, r'''"Text") stood on page 1 as Sanskrit; the scholarly English had "translated" seven of them.
''', r'''"Text") stood on page 1 as Sanskrit; the scholarly English had "translated" seven of them.

ETEXT_REFS_2026_10_21 (the evening of 21 Oct): the number in brackets at the end of 18 of its verses (1.31b: ...//
(364220), the value of the verse's numerals) had been read as the verse's reference and taken out of its text and
its romanized line; the other verses had no reference, and the chapter of all was the colophons' (1, then 2), not the
pada labels' (1 to 14). The plan reads each line again from the witness's source file, when its sha256 is the one the
witness was read from (else from the romanized line kept): "the reference only" (the label's verse and chapter, the
text the same; the latest scholarly English has its reference set, the English untouched), or respelled ("the value
in brackets" put back; the scholarly English re-based, as below). A reference the e-text gives two verses is named.
''')

edit('scripts/mend_witness.py', 2, r'''MARK = "WITNESS_MEND_2026_10_21"
''', r'''MARK = "WITNESS_MEND_2026_10_21"
MARK_REFS = "ETEXT_REFS_2026_10_21"
''')

edit('scripts/mend_witness.py', 3, r'''def plan(a) -> dict:
    """What the mend would do; writes nothing. {"refuse": str} when it cannot be done."""
''', r'''def source_lines(meta: dict):
    """ETEXT_REFS_2026_10_21: the source file's lines as etext_witness.parse() numbers them (from 1), when its sha256
    is the one the witness was read from; else None (the romanized lines kept in the page files are read alone)."""
    f = str(meta.get("file") or "")
    want = str(meta.get("sha256") or "")
    if not f or not want:
        return None
    p = Path(f.replace("\\", os.sep))
    if not p.is_absolute():
        p = ROOT / p
    try:
        text, info = EW.read_text(p)
    except OSError:
        return None
    if info.get("sha256") != want:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def from_source(lines, start, roman: str):
    """ETEXT_REFS_2026_10_21: (the record's romanized lines as etext_witness.take_ref() reads them now, its first
    reference) for a record whose first line is source line `start`: each kept line must be what take_ref() gave (as
    before, or as now) from a source line, in order, at most 4 lines on; else None."""
    if not lines or not start or not roman:
        return None
    try:
        i = int(start) - 1
    except (TypeError, ValueError):
        return None
    body, ref = [], ""
    for want in roman.split("\n"):
        for j in range(max(i, 0), min(i + 5, len(lines))):
            ln = lines[j].strip().replace(EW.DANDA + EW.DANDA, EW.DDANDA)
            if not ln:
                continue
            b, r, _w = EW.take_ref(ln, labels=True)
            if want in (EW.take_ref(ln, labels=False)[0], b):
                body.append(b)
                ref = ref or r
                i = j + 1
                break
        else:
            return None
    return "\n".join(body), ref


def chapter_of(ref: str) -> str:
    """ETEXT_REFS_2026_10_21: a verse's chapter from its reference, as etext_witness.parse() gives it (1.31: 1)."""
    return ".".join(ref.split(".")[:-1]) if ref and ref.count(".") else ""


def _txt(x):
    return None if x is None or str(x).strip() == "" else str(x).strip()


def plan(a) -> dict:
    """What the mend would do; writes nothing. {"refuse": str} when it cannot be done."""
''')

edit('scripts/mend_witness.py', 4, r'''        rows = con.execute("SELECT p.id, p.page_no, p.idx, p.text, p.text_type FROM passages p JOIN docs d ON "
''', r'''        rows = con.execute("SELECT p.id, p.page_no, p.idx, p.text, p.text_type, p.verse_ref, p.chapter FROM passages p "
                           "JOIN docs d ON "
''')

edit('scripts/mend_witness.py', 5, r'''    gretil = source_is_gretil(meta) or str(meta.get("site") or "") == "gretil"
''', r'''    gretil = source_is_gretil(meta) or str(meta.get("site") or "") == "gretil"
    src = source_lines(meta)   # ETEXT_REFS_2026_10_21: the lines read again from the source file, when it is the same
''')

edit('scripts/mend_witness.py', 6, r'''            head = k in zone
            target = (roman.strip() if head else convert(roman, scheme, True)) if roman else old.strip()
            target_type = "noise" if head else it["type_old"]
            if not roman or (old.strip() == target and it["type_old"] == target_type):
                it.update(kind="same", new=old, type_new=it["type_old"])   # as the e-text means it (mended already)
            elif convert(roman, scheme, False) != old.strip():
                it.update(kind="unreproducible", new=old, type_new=it["type_old"])
            elif head:
                it.update(kind="header", new=target, type_new="noise", what=["GRETIL's English header"])
            else:
                it.update(kind="respelled", new=target, type_new=it["type_old"], what=what_changed(roman))
            r0 = latest.get(it["pid"]) if it["pid"] else None
            it["scholar"] = None
            if r0 is not None and it["kind"] in ("respelled", "header"):
                if r0.get("src_hash") != ST.src_hash(row[3]):
                    it["scholar"] = "stale already"
                else:
                    it["scholar"] = "rebase" if it["kind"] == "respelled" else "dropped"
                it["row"] = r0
''', r'''            head = k in zone
            # ETEXT_REFS_2026_10_21: the line read again from the source file (the value in brackets kept, the
            # reference the pada label's), else from the romanized line kept
            ref_old, ch_old = (_txt(row[5]), _txt(row[6])) if row else (None, None)
            fs = from_source(src, (rec.get("meta") or {}).get("src_line"), roman) if (roman and not head) else None
            roman_now = fs[0] if fs else roman
            ref = "" if (head or not roman) else (fs[1] if fs else EW.take_ref(roman.split("\n")[0].strip())[1])
            ref_new = _txt(ref) or ref_old
            ch_new = (_txt(chapter_of(ref)) or ch_old) if ref else ch_old
            rw = ([] if ref_new == ref_old else ["the reference"]) + ([] if ch_new == ch_old else ["the chapter"])
            it.update(roman_now=roman_now, ref_old=ref_old, ref=ref_new, ch_old=ch_old, chapter=ch_new)
            target = (roman.strip() if head else convert(roman_now, scheme, True)) if roman else old.strip()
            target_type = "noise" if head else it["type_old"]
            if not roman or (old.strip() == target and it["type_old"] == target_type and not rw):
                it.update(kind="same", new=old, type_new=it["type_old"])   # as the e-text means it (mended already)
            elif old.strip() not in (convert(roman, scheme, False), convert(roman, scheme, True)):
                it.update(kind="unreproducible", new=old, type_new=it["type_old"])
            elif head:
                it.update(kind="header", new=target, type_new="noise", what=["GRETIL's English header"])
            elif old.strip() == target:
                it.update(kind="refs", new=old, type_new=it["type_old"], what=rw)
            else:
                what = what_changed(roman) if convert(roman, scheme, True) != old.strip() else []
                if roman_now != roman:
                    what.append("the value in brackets")
                it.update(kind="respelled", new=target, type_new=it["type_old"], what=what + rw)
            r0 = latest.get(it["pid"]) if it["pid"] else None
            it["scholar"] = None
            if r0 is not None and it["kind"] in ("respelled", "header"):
                if r0.get("src_hash") != ST.src_hash(row[3]):
                    it["scholar"] = "stale already"
                else:
                    it["scholar"] = "rebase" if it["kind"] == "respelled" else "dropped"
                it["row"] = r0
            elif (r0 is not None and it["kind"] == "refs" and it.get("ref") and r0.get("src_hash") == ST.src_hash(row[3])
                  and _txt(r0.get("verse_ref")) != it["ref"]):
                it["scholar"] = "label"   # ETEXT_REFS_2026_10_21: the latest row's reference set; its English untouched
                it["row"] = r0
''')

edit('scripts/mend_witness.py', 7, r'''    print("  passages: %d; respelled %d; header %d; the same %d; left alone (the old reading does not give it) %d"
          % (len(items), c.get("respelled", 0), c.get("header", 0), c.get("same", 0), c.get("unreproducible", 0)))
''', r'''    print("  passages: %d; respelled %d; header %d; the same %d; the reference only %d; left alone (the old reading "
          "does not give it) %d" % (len(items), c.get("respelled", 0), c.get("header", 0), c.get("same", 0),
                                    c.get("refs", 0), c.get("unreproducible", 0)))
''')

edit('scripts/mend_witness.py', 8, r'''          % (c.get("scholar rebase", 0), c.get("scholar dropped", 0), c.get("scholar stale already", 0)))
    seen = {}
    for it in items:
        k = it["kind"]
        if k in ("respelled", "header", "unreproducible") and seen.get(k, 0) < limit:
''', r'''          % (c.get("scholar rebase", 0), c.get("scholar dropped", 0), c.get("scholar stale already", 0)))
    if c.get("scholar label"):   # ETEXT_REFS_2026_10_21
        print("  scholarly English given the verse's reference (the English untouched): %d" % c["scholar label"])
    dup = {}   # ETEXT_REFS_2026_10_21: a reference the e-text gives more than one passage (its labels' slips)
    for it in items:
        if it.get("ref") and it.get("type_new") != "noise":
            dup.setdefault(it["ref"], []).append("%d.%d" % (it["page"], it["idx"]))
    two = sorted((r, w) for r, w in dup.items() if len(w) > 1)
    if two:
        print("  the e-text gives %d reference(s) to more than one passage (its labels, left as written): %s"
              % (len(two), "; ".join("%s at %s" % (r, ", ".join(w)) for r, w in two[:12])))
    seen = {}
    for it in items:
        k = it["kind"]
        if k in ("respelled", "header", "unreproducible", "refs") and seen.get(k, 0) < limit:
''')

edit('scripts/mend_witness.py', 9, r'''            print("      now: %s" % it["new"][:150].replace("\n", " / "))
    return c
''', r'''            print("      now: %s" % it["new"][:150].replace("\n", " / "))
            if (it.get("ref"), it.get("chapter")) != (it.get("ref_old"), it.get("ch_old")):   # ETEXT_REFS_2026_10_21
                print("      the reference: %s, chapter %s (was %s, chapter %s)" % (
                    it.get("ref") or "-", it.get("chapter") or "-", it.get("ref_old") or "-", it.get("ch_old") or "-"))
    return c
''')

edit('scripts/mend_witness.py', 10, r'''    todo = [it for it in items if it["kind"] in ("respelled", "header")]
''', r'''    todo = [it for it in items if it["kind"] in ("respelled", "header", "refs")]   # ETEXT_REFS_2026_10_21: refs
''')

edit('scripts/mend_witness.py', 11, r'''        if not any(it["kind"] in ("respelled", "header") for it in out):
''', r'''        if not any(it["kind"] in ("respelled", "header", "refs") for it in out):
''')

edit('scripts/mend_witness.py', 12, r'''            if it["kind"] in ("respelled", "header"):
                rec = dict(rec)
                rec["text"] = it["new"]
                rec["text_type"] = it["type_new"]
                rec["meta"] = dict(rec.get("meta") or {}, mend=MARK)
''', r'''            if it["kind"] in ("respelled", "header", "refs"):
                rec = dict(rec)
                rec["text"] = it["new"]
                rec["text_type"] = it["type_new"]
                rec["meta"] = dict(rec.get("meta") or {}, mend=MARK)
                if it["kind"] != "header":   # ETEXT_REFS_2026_10_21: the reference, the chapter, the line as read now
                    rec["verse_ref"] = it.get("ref") or rec.get("verse_ref")
                    rec["chapter"] = it.get("chapter") or rec.get("chapter")
                    if it.get("roman_now") and it["roman_now"] != it["roman"]:
                        rec["meta"]["roman_source"] = it["roman_now"]
                    rec["meta"]["mend_refs"] = MARK_REFS
''')

edit('scripts/mend_witness.py', 13, r'''            "SELECT p.id, p.page_no, p.idx, p.text, p.text_type FROM passages p JOIN docs d ON d.id = p.doc_id "
            "WHERE d.code = ?", (wcode,))}
        bad = [it for it in items if it["pid"] not in now_rows or (now_rows[it["pid"]][1], now_rows[it["pid"]][2]) !=
               (it["page"], it["idx"]) or now_rows[it["pid"]][3] != normalize_sanskrit(it["new"].strip())]
''', r'''            "SELECT p.id, p.page_no, p.idx, p.text, p.text_type, p.verse_ref, p.chapter FROM passages p JOIN docs d "
            "ON d.id = p.doc_id WHERE d.code = ?", (wcode,))}
        bad = [it for it in items if it["pid"] not in now_rows or (now_rows[it["pid"]][1], now_rows[it["pid"]][2]) !=
               (it["page"], it["idx"]) or now_rows[it["pid"]][3] != normalize_sanskrit(it["new"].strip())
               or (it["kind"] in ("respelled", "refs") and it.get("ref")   # ETEXT_REFS_2026_10_21: the reference too
                   and (_txt(now_rows[it["pid"]][5]), _txt(now_rows[it["pid"]][6])) != (it["ref"], it.get("chapter")))]
''')

edit('scripts/mend_witness.py', 14, r'''        n = 0
        cols = list(ST.COLS) + [c for c in REVIEW_COLS if c in have]
        with con:
            for it in items:
                if it.get("scholar") != "rebase":
                    continue
                rec = rebase_rec(it["row"], now_rows[it["pid"]][3], it["what"], at, have)
''', r'''        n = lab = 0
        cols = list(ST.COLS) + [c for c in REVIEW_COLS if c in have]
        with con:
            for it in items:
                if it.get("scholar") == "label":   # ETEXT_REFS_2026_10_21: the latest row's reference; the English untouched
                    con.execute("UPDATE scholar_translations SET verse_ref = ? WHERE id = ?", (it["ref"], it["row"]["id"]))
                    lab += 1
                    continue
                if it.get("scholar") != "rebase":
                    continue
                rec = rebase_rec(it["row"], now_rows[it["pid"]][3], it["what"], at, have)
                if it.get("ref"):
                    rec["verse_ref"] = it["ref"]   # ETEXT_REFS_2026_10_21
''')

edit('scripts/mend_witness.py', 15, r'''                                "type_new": it["type_new"], "scholar": it.get("scholar"), "mark": MARK},
''', r'''                                "type_new": it["type_new"], "scholar": it.get("scholar"), "mark": MARK,
                                "ref": it.get("ref"), "chapter": it.get("chapter"), "ref_old": it.get("ref_old"),
                                "chapter_old": it.get("ch_old"), "scholar_row": (it.get("row") or {}).get("id"),
                                "mark_refs": MARK_REFS},
''')

edit('scripts/mend_witness.py', 16, r'''                                   "log": str(logp), "at": now(), "mark": MARK})
''', r'''                                   "log": str(logp), "at": now(), "mark": MARK, "refs": c.get("refs", 0),
                                   "labelled": lab, "mark_refs": MARK_REFS})
''')

edit('scripts/mend_witness.py', 17, r'''    say("%s mended: %d passages respelled, %d header line(s) kept in Latin letters as noise; %d scholarly English "
        "re-based (the same English), %d dropped (header lines); the ids unchanged; backup %s; log %s"
        % (wcode, c.get("respelled", 0), c.get("header", 0), n, c.get("scholar dropped", 0), backup, logp), nxt,
''', r'''    say("%s mended: %d passages respelled, %d header line(s) kept in Latin letters as noise, %d given their reference "
        "only; %d scholarly English re-based (the same English), %d given the verse's reference (the English "
        "untouched), %d dropped (header lines); the ids unchanged; backup %s; log %s"
        % (wcode, c.get("respelled", 0), c.get("header", 0), c.get("refs", 0), n, lab, c.get("scholar dropped", 0),
           backup, logp), nxt,
''')

edit('scripts/mend_witness.py', 18, r'''        n = c.get("respelled", 0) + c.get("header", 0)
        if not n:
            say("nothing to mend in %s: every passage reads as the e-text means it" % a.doc, "")
            return 0
        say("%d passage(s) of %s to mend (%d respelled, %d header); %d scholarly English to re-base, %d to drop; "
            "nothing written" % (n, a.doc, c.get("respelled", 0), c.get("header", 0), c.get("scholar rebase", 0),
                                 c.get("scholar dropped", 0)),
''', r'''        n = c.get("respelled", 0) + c.get("header", 0) + c.get("refs", 0)   # ETEXT_REFS_2026_10_21: refs
        if not n:
            say("nothing to mend in %s: every passage reads as the e-text means it" % a.doc, "")
            return 0
        say("%d passage(s) of %s to mend (%d respelled, %d header, %d the reference only); %d scholarly English to "
            "re-base, %d to give the verse's reference, %d to drop; nothing written"
            % (n, a.doc, c.get("respelled", 0), c.get("header", 0), c.get("refs", 0), c.get("scholar rebase", 0),
               c.get("scholar label", 0), c.get("scholar dropped", 0)),
''')

# ---- tests/test_etext_ortho_2026_10_21.py (its replay chain) ----------------------------------------
edit('tests/test_etext_ortho_2026_10_21.py', 1, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:   # ETEXT_REFS_2026_10_21: etext_witness.py's later backup may be .bak_etextrefs_
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextrefs_*"))
                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)
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
    print("DONE: %s; backups .bak_%s_%s" % (MARK, TAG, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
