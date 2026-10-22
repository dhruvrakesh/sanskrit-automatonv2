#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_prose2_2026_10_22.py  (2026-10-22)  ETEXT_PROSE2_2026_10_22

GRETIL's Satapatha, read in full (its thirteen files, on the PC since 21 Oct, 22:07 IST), has its kandikas' numbers
in more shapes than "13.1.1.[1]", the one ETEXT_PROSE_2026_10_21 read. Kanda 14 was written and ingested with it on 21
Oct (2015_405693_Shatpath-Brahmanam__w_gretil, 745 passages, local only): its 33 kandikas of 14.4.1, numbered without
brackets, ran into 14.3.2.31; three brahmanas of one kandika each (14.6.4 to 14.6.6), under their own number only, ran
into the kandika before; and an appendix after a line of asterisks (five passages under "14.3.1." and 14.3.2.1 to 31
again, word for word) ran into 14.9.4.33, the last kandika: 6,085 characters where the vamsa is about 1,000.
Measured in the thirteen files: 19 numbers with their brackets put in wrongly (1.1.3[.1]1 for 1.1.3.11, 1.1.3[[.]]5 for
1.1.3.5; 4.5.7.[9]] and 14.9.1.[19]] with one too many), 66 without brackets (14.4.1.1 ...), brahmana headings (2.1.1.,
14.6.4.), one number glued to its text and mistyped (11.7.4.2prajapatirha ... for 1.7.4.2, between 1.7.4.1 and 1.7.4.3).

scripts/etext_witness.py (needs ETEXT_PROSE_2026_10_21): once a bracketed reference has been seen (so verse texts read
as before):
  - a number with its brackets wrong, or without brackets (four parts), starts a unit; a brahmana's own number (three
    parts: 14.6.4.) starts one too when text follows it before a kandika's number (a brahmana of one kandika), else it
    is a heading and nothing more;
  - a number glued to its text starts a unit with that text; where it is one digit off its neighbours' sequence
    (11.7.4.2 after 1.7.4.1) it is read as the sequence has it, and counted;
  - a line of asterisks ends the unit before it; what follows it numbered below what came before it is an appendix
    (kanda 14's after 14.9.4.33), each passage's meta says so; the separators of a file's header and the one before the
    Brhadaranyaka (14.4) mark nothing; a unit repeated word for word (the appendix's 14.3.2) is left out once seen;
  - a kandika is prose (its text type, no padas), with the danda kandas 1 to 9 put after its first clause or without
    it (kandas 10 to 14 have a double space there), and never a colophon (5 kandikas were read as one: a word such as
    khandika or sarga in them);
  - the preview counts each shape, and the units out of order.
tests/test_etext_prose_2026_10_21.py: its replay compares with the copy ETEXT_PROSE2 backed up, when there is one.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_etextprose2_<date>. No database change; nothing is fetched. The kanda 14 already ingested is mended by writing it
again and ingesting it again (the RUNBOOK's DOCS83 section): it has no translation yet.

  python scripts\\patch_etext_prose2_2026_10_22.py --check
  python scripts\\patch_etext_prose2_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_PROSE2_2026_10_22'
NEEDS = {'scripts/etext_witness.py': 'ETEXT_PROSE_2026_10_21', 'tests/test_etext_prose_2026_10_21.py': 'ETEXT_PROSE_2026_10_21'}
FILES = list(NEEDS)
TAG = 'etextprose2'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


F = 'scripts/etext_witness.py'

edit(F, 1, r'''G_PROSE_REF = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){1,4})\.\[(\d{1,4})\](?:\s+(.*\S))?\s*$")
''', r'''G_PROSE_REF = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){1,4})\.\[(\d{1,4})\](?:\s+(.*\S))?\s*$")
# ETEXT_PROSE2_2026_10_22: GRETIL's Satapatha in full has its numbers in other shapes too, read once a bracketed one has
# been seen: the brackets put in wrongly (1.1.3[.1]1, 1.1.3[[.]]5, 4.5.7.[9]]), none (14.4.1.1), a brahmana's own number
# (14.6.4.), a number glued to its text (11.7.4.2prajapatirha); and an appendix after a line of asterisks
G_PROSE_GLUED = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){3})(?=[^\W\d_])(.+)$")
G_SEPARATOR = re.compile(r"^\s*[*=~_-]{5,}\s*$")


def prose_ref(ln: str, on: bool):
    """(ref, rest, kind) of a prose unit's reference line, or None. kind: "unit" (13.1.1.[1]; once on, 1.1.3[.1]1 and
    14.4.1.1), "glued" (once on: 11.7.4.2text) or "heading" (once on: 14.6.4., a brahmana's own number)."""
    m = G_PROSE_REF.match(ln)
    if m:
        return norm_ref(m.group(1) + "." + m.group(2)), (m.group(3) or "").strip(), "unit"
    if not on:
        return None
    if re.fullmatch(r"[\d.\[\]\s]+", ln):
        parts = re.sub(r"[\[\]\s]", "", ln).strip(".").split(".")
        if all(p.isdigit() and len(p) <= 3 for p in parts) and len(parts) in (3, 4):
            return ".".join(str(int(p)) for p in parts), "", ("unit" if len(parts) == 4 else "heading")
        return None
    m = G_PROSE_GLUED.match(ln)
    if m:
        return norm_ref(m.group(1)), m.group(2).strip(), "glued"
    return None
''')

edit(F, 2, r'''    prose = [False]   # ETEXT_PROSE_2026_10_21: a unit's reference line seen: each unit runs to the next
''', r'''    prose = [False]   # ETEXT_PROSE_2026_10_21: a unit's reference line seen: each unit runs to the next
    appendix, last_unit, top = [()], [""], [()]   # ETEXT_PROSE2_2026_10_22: the highest number before a separator line,
                                                  # the last unit's number, the highest number so far
''')

edit(F, 3, r'''                               "roman": "\n".join(cur["roman"]) if cur["roman"] else ""})
''', r'''                               "roman": "\n".join(cur["roman"]) if cur["roman"] else ""})
                if appendix[0] and ref.replace(".", "").isdigit() and \
                        tuple(int(x) for x in ref.split(".")) < appendix[0]:   # ETEXT_PROSE2_2026_10_22: an appendix,
                    verses[-1]["appendix"] = True                              # numbered below what came before it
''')

edit(F, 10, r'''                                              ("frontmatter" if not verses and len(DEV_LETTER.findall(deva)) < 25 else "prose"))
''', r'''                                              ("frontmatter" if not verses and len(DEV_LETTER.findall(deva)) < 25 else "prose"))
                if prose[0]:   # ETEXT_PROSE2_2026_10_22: a numbered kandika is prose, with its danda (kandas 1 to 9 put
                    tt, has_danda, colo = "prose", False, False   # one after its first clause) or not; never a colophon
''')

edit(F, 4, r'''        pm = G_PROSE_REF.match(ln) if ln else None   # ETEXT_PROSE_2026_10_21: 13.1.1.[1], the unit's own line
        if pm:
            flush()
            prose[0] = True
            cur["ref"] = norm_ref(pm.group(1) + "." + pm.group(2))
            st["refs"] += 1
            st["prose_units"] = st.get("prose_units", 0) + 1
            if not pm.group(3):
                continue
            ln = pm.group(3).strip()
''', r'''        if prose[0] and G_SEPARATOR.match(ln or ""):   # ETEXT_PROSE2_2026_10_22: ****: what follows it, numbered below
            flush()                                    # what came before it, is an appendix
            appendix[0] = top[0]
            st["separators"] = st.get("separators", 0) + 1
            continue
        pr = prose_ref(ln, prose[0]) if ln else None   # ETEXT_PROSE_2026_10_21 (13.1.1.[1]); ETEXT_PROSE2_2026_10_22
        if pr:
            flush()
            ref_, rest_, kind_ = pr
            if kind_ == "glued" and last_unit[0]:   # ETEXT_PROSE2_2026_10_22: the typist's slip, 11.7.4.2 after 1.7.4.1
                a_ = last_unit[0].split(".")
                want = ".".join(a_[:-1] + [str(int(a_[-1]) + 1)])
                if ref_ != want and ref_[1:] == want:
                    ref_ = want
                    st["repaired"] = st.get("repaired", 0) + 1
            prose[0] = True
            cur["ref"] = ref_
            st["refs"] += 1
            if ref_.replace(".", "").isdigit():
                top[0] = max(top[0], tuple(int(x) for x in ref_.split(".")))
            if kind_ == "heading":
                st["headings"] = st.get("headings", 0) + 1
            else:
                st["prose_units"] = st.get("prose_units", 0) + 1
                last_unit[0] = ref_
            if not rest_:
                continue
            ln = rest_
''')

edit(F, 9, r'''        if raw.strip() == FILE_BREAK:   # ETEXT_PROSE_2026_10_21: the next file: what follows its title is a new unit
            flush()
            continue
''', r'''        if raw.strip() == FILE_BREAK:   # ETEXT_PROSE_2026_10_21: the next file: what follows its title is a new unit
            flush()
            appendix[0] = ()   # ETEXT_PROSE2_2026_10_22: a separator's appendix ends with its file
            continue
''')

edit(F, 5, r'''        keep = [v for v in verses if v["ref"]]
        st["outside"] = len(verses) - len(keep)
        verses[:] = keep
''', r'''        keep = [v for v in verses if v["ref"]]
        st["outside"] = len(verses) - len(keep)
        verses[:] = keep
        seen, keep = set(), []   # ETEXT_PROSE2_2026_10_22: a unit repeated word for word (the appendix's 14.3.2) once
        for v in verses:
            key = (v["ref"], re.sub(r"\s+", " ", v["text"]).strip())
            if key in seen:
                st["repeats"] = st.get("repeats", 0) + 1
                continue
            seen.add(key)
            keep.append(v)
        verses[:] = keep
        st["appendix_units"] = sum(1 for v in verses if v.get("appendix"))
        order = [tuple(int(x) for x in v["ref"].split(".")) for v in verses if v["ref"].replace(".", "").isdigit()]
        st["out_of_order"] = sum(1 for a_, b_ in zip(order, order[1:]) if b_ <= a_)
''')

edit(F, 6, r'''                r["meta"]["roman_source"] = v["roman"]
''', r'''                r["meta"]["roman_source"] = v["roman"]
            if v.get("appendix"):   # ETEXT_PROSE2_2026_10_22: after the e-text's separator line
                r["meta"]["after_separator"] = True
''')

edit(F, 7, r'''              "title, its notes); the longest unit %d characters; no danda added" % (st["prose_units"],
                                                                                    st.get("outside", 0), longest))
''', r'''              "title, its notes); the longest unit %d characters; no danda added" % (st["prose_units"],
                                                                                    st.get("outside", 0), longest))
        if any(st.get(k) for k in ("headings", "repeats", "repaired", "separators", "out_of_order")):   # ETEXT_PROSE2_2026_10_22
            print("  prose, the e-text's other shapes: %d brahmana number(s) over its text or as a heading (14.6.4.); %d "
                  "unit(s) repeated word for word left out; %d number(s) mistyped and read by their neighbours (11.7.4.2 "
                  "for 1.7.4.2); %d separator line(s), %d unit(s) after one (an appendix: read them beside the text); %d "
                  "unit(s) out of order" % (st.get("headings", 0), st.get("repeats", 0), st.get("repaired", 0),
                                            st.get("separators", 0), st.get("appendix_units", 0),
                                            st.get("out_of_order", 0)))
''')

T = 'tests/test_etext_prose_2026_10_21.py'

edit(T, 8, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:   # ETEXT_PROSE2_2026_10_22 came after: its backup of etext_witness.py is this patch's
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose2_*"))
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
