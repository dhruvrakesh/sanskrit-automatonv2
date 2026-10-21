#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_etext_prose_2026_10_21.py  (2026-10-21)  ETEXT_PROSE_2026_10_21

The Satapatha for the translator (docs/BRAIN_PATH_2026-10-21.md, section 7). GRETIL's Satapatha (the Madhyandina
recension, from Weber's edition; kandas 1 to 11, 13 and 14, one file each) is prose: each kandika stands under its own
line, "13.1.1.[1]" (kanda, adhyaya, brahmana, [kandika]; "Bracketted numbering added mechanically"), and its lines
carry no danda. etext_witness.py read only verses: such a line has no letters and was skipped, the kandikas ran
together and were cut every 12 lines, and none kept its number. It also read one file at a time and needed a scan.

scripts/etext_witness.py (needs ETEXT_REFS_2026_10_21):
  - a line that is a unit's reference (13.1.1.[1], with or without the unit's first words after it) starts the unit
    and gives it its reference (13.1.1.1); the unit runs to the next reference, blank lines and all, and is never cut
    at 12 lines; its chapter is the adhyaya (13.1); what stands outside a unit (a file's title, its notes) is left out
    and counted; the text is put into Devanagari as before (the avagraha, the pluti's 3), with no danda added: a
    kandika's end is its number, and a danda inside one would be ours, not the edition's;
  - --file may name a folder: its .htm, .html and .txt files, in the order of their names, are one text (a break
    between files, so that a file's title never joins the kandika before it); each file's name, size and sha256 are
    kept in witness.json;
  - --category: the category of a new text, one that is no scan's witness (the Satapatha's kandas 1 to 13: ours is
    kanda 14 only), for its ingest;
  - verse texts read as before: the reference line is the only new shape.
tests/test_etext_refs_2026_10_21.py: its replay compares with the copy ETEXT_PROSE backed up, when there is one.
Anchored, all-or-nothing, marker-idempotent; keeps line endings; py_compile before the atomic replace; backups
.bak_etextprose_<date>. No database change; nothing is fetched.

  python scripts\\patch_etext_prose_2026_10_21.py --check
  python scripts\\patch_etext_prose_2026_10_21.py
  python scripts\\etext_witness.py --doc satapatha_madhyandina --file sources\\satapatha_gretil --category brahmana --per-page 10
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'ETEXT_PROSE_2026_10_21'
NEEDS = {'scripts/etext_witness.py': 'ETEXT_REFS_2026_10_21', 'tests/test_etext_refs_2026_10_21.py': 'ETEXT_REFS_2026_10_21'}
FILES = list(NEEDS)
TAG = 'etextprose'

E = []
def edit(f, n, old, new):
    E.append((f, n, old, new))


F = 'scripts/etext_witness.py'

edit(F, 1, r'''The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.
"""''', r'''ETEXT_PROSE_2026_10_21: a prose e-text whose units stand under their own reference lines (GRETIL's Satapatha:
"13.1.1.[1]") is read unit by unit, each with its reference, never cut at 12 lines, with no danda added; --file may
name a folder (its .htm, .html and .txt files in the order of their names are one text); --category names a new
text's category when it is no scan's witness.

  python scripts\\etext_witness.py --doc satapatha_madhyandina --file sources\\satapatha_gretil --category brahmana --per-page 10

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.
"""''')

edit(F, 2, r'''

def detect_scheme(lines: list) -> str:
''', r'''

# ETEXT_PROSE_2026_10_21: a folder of files is one text, a break between them
FILE_BREAK = "@@ETEXT_FILE_BREAK@@"


def read_source(src: Path):
    """(text, info) of a file (read_text), or of a folder: its .htm, .html and .txt files in the order of their names
    (GRETIL's Satapatha, a file a kanda), joined with FILE_BREAK; info["files"]: each one's name, bytes and sha256."""
    if not src.is_dir():
        return read_text(src)
    files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in (".htm", ".html", ".txt"))
    texts, infos = [], []
    for p in files:
        t, i = read_text(p)
        texts.append(t)
        infos.append(dict(i, name=p.name))
    info = {"bytes": sum(i["bytes"] for i in infos),
            "sha256": hashlib.sha256("".join(i["sha256"] for i in infos).encode("ascii")).hexdigest(),
            "encoding": ", ".join(sorted({i["encoding"] for i in infos})) or "-",
            "kind": ", ".join(sorted({i["kind"] for i in infos})) or "-",
            "note": "; ".join(i["note"] for i in infos if i["note"]),
            "files": [{"name": i["name"], "bytes": i["bytes"], "sha256": i["sha256"]} for i in infos]}
    return ("\n%s\n" % FILE_BREAK).join(texts), info


def detect_scheme(lines: list) -> str:
''')

edit(F, 3, r'''

def take_ref(line: str, labels: bool = True):
''', r'''
# ETEXT_PROSE_2026_10_21: a prose unit's reference on a line of its own (GRETIL's Satapatha: 13.1.1.[1], kanda, adhyaya,
# brahmana, [kandika]), or followed by the unit's first words
G_PROSE_REF = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,3}){1,4})\.\[(\d{1,4})\](?:\s+(.*\S))?\s*$")


def take_ref(line: str, labels: bool = True):
''')

edit(F, 4, r'''    cur = {"lines": [], "roman": [], "ref": "", "src": 0}
    chap = [1]
''', r'''    cur = {"lines": [], "roman": [], "ref": "", "src": 0}
    chap = [1]
    prose = [False]   # ETEXT_PROSE_2026_10_21: a unit's reference line seen: each unit runs to the next
''')

edit(F, 5, r'''                chapter = ".".join(ref.split(".")[:-1]) if ref.count(".") else ""
''', r'''                chapter = ".".join(ref.split(".")[:-1]) if ref.count(".") else ""
                if prose[0] and ref.count(".") >= 2:   # ETEXT_PROSE_2026_10_21: the adhyaya (13.1), not the brahmana
                    chapter = ".".join(ref.split(".")[:2])
''')

edit(F, 6, r'''        if i in skip and ln:
            st["dropped_english"] += 1
            continue
        if not ln:
            st["blank"] += 1
            flush()
            continue
        body, ref, where = take_ref(ln)
''', r'''        if i in skip and ln:
            st["dropped_english"] += 1
            continue
        if raw.strip() == FILE_BREAK:   # ETEXT_PROSE_2026_10_21: the next file: what follows its title is a new unit
            flush()
            continue
        pm = G_PROSE_REF.match(ln) if ln else None   # ETEXT_PROSE_2026_10_21: 13.1.1.[1], the unit's own line
        if pm:
            flush()
            prose[0] = True
            cur["ref"] = norm_ref(pm.group(1) + "." + pm.group(2))
            st["refs"] += 1
            st["prose_units"] = st.get("prose_units", 0) + 1
            if not pm.group(3):
                continue
            ln = pm.group(3).strip()
        if not ln:
            st["blank"] += 1
            if not prose[0]:   # ETEXT_PROSE_2026_10_21: a prose unit runs to the next reference, blank lines and all
                flush()
            continue
        body, ref, where = take_ref(ln) if not prose[0] else (ln, "", "")
''')

edit(F, 7, r'''        if _ends_verse(body) or (ref and where == "end") or len(cur["lines"]) >= 12:
            flush()
    flush()
    return out
''', r'''        if not prose[0] and (_ends_verse(body) or (ref and where == "end") or len(cur["lines"]) >= 12):
            flush()   # ETEXT_PROSE_2026_10_21: a prose unit is not cut at 12 lines
    flush()
    if prose[0]:   # ETEXT_PROSE_2026_10_21: what stands outside a unit (a file's title, its notes) is not the text
        keep = [v for v in verses if v["ref"]]
        st["outside"] = len(verses) - len(keep)
        verses[:] = keep
    return out
''')

edit(F, 8, r'''    if not src or not src.is_file():
        say("no such file: %s" % (src or "(none)"), "")
        return 1
    text, info = read_text(src)
''', r'''    if not src or not (src.is_file() or src.is_dir()):   # ETEXT_PROSE_2026_10_21: a folder of files is one text
        say("no such file: %s" % (src or "(none)"), "")
        return 1
    text, info = read_source(src)
''')

edit(F, 9, r'''    if info["note"]:
        print("  note: " + info["note"])
''', r'''    if info["note"]:
        print("  note: " + info["note"])
    if info.get("files"):   # ETEXT_PROSE_2026_10_21
        print("  files: %d, read in this order: %s" % (len(info["files"]), ", ".join(f["name"] for f in info["files"])))
''')

edit(F, 10, r'''    for v in verses[:3]:
''', r'''    if st.get("prose_units"):   # ETEXT_PROSE_2026_10_21
        longest = max((len(v["text"]) for v in verses), default=0)
        print("  prose: %d units by their reference lines (13.1.1.[1]); %d passage(s) outside a unit left out (a file's "
              "title, its notes); the longest unit %d characters; no danda added" % (st["prose_units"],
                                                                                    st.get("outside", 0), longest))
    for v in verses[:3]:
''')

edit(F, 11, r'''"category": scan_facts.get("category"), "stats": parsed["stats"],''',
     r'''"category": scan_facts.get("category") or a.category or None,   # ETEXT_PROSE_2026_10_21: a new text's
            "files": info.get("files"), "stats": parsed["stats"],''')

edit(F, 12, r'''    ap.add_argument("--slug", default=None, help="the witness's name after __w_ (default: the site)")
''', r'''    ap.add_argument("--slug", default=None, help="the witness's name after __w_ (default: the site)")
    ap.add_argument("--category", default=None,   # ETEXT_PROSE_2026_10_21
                    help="a new text's category (brahmana, veda, ...), when it is no scan's witness")
''')

edit(F, 13, r'''    if a.slug and not re.match(r"^[A-Za-z0-9]{1,20}$", a.slug):
        print("FAIL: --slug is letters and digits (up to 20)."); return 2
''', r'''    if a.slug and not re.match(r"^[A-Za-z0-9]{1,20}$", a.slug):
        print("FAIL: --slug is letters and digits (up to 20)."); return 2
    if a.category and not re.match(r"^[a-z][a-z_]{1,30}$", a.category):   # ETEXT_PROSE_2026_10_21
        print("FAIL: --category is lower-case letters and _ (brahmana, veda, ...)."); return 2
''')

T = 'tests/test_etext_refs_2026_10_21.py'

edit(T, 14, r'''            for f in self.FILES:
                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)
''', r'''            for f in self.FILES:   # ETEXT_PROSE_2026_10_21 came after: its backup of etext_witness.py is this patch's
                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_etextprose_*"))
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
