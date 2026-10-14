#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_mbh_prose_2026_10_14.py  (2026-10-14)  MBH_PROSE_2026_10_14

MBh01 (the BORI Critical Edition e-text) lacks every prose passage of the critical edition: 1.1.1 (lomaharsanaputra
ugrasravah ...), 1.3.2 to 1.3.59 (the Pausya story), 1.4.1-3, most of chapter 90, and the rest. On 14 Oct the
e-text's own readme (John Smith, MBh00.txt) gave the reason: a prose line's last letter is a capital (01003001A),
and import_mbh_gretil.py read [a-z] only, so it passed over each prose line and kept the speaker's line ("suta
uvaca") above it. An unabridged translation needs them. This patch:
  import_mbh_gretil.py: reads the capital (prose) and the BORI form of the reference (01003001A) as well as GRETIL's
    (01,003.001A); marks those passages prose; says how many prose lines it read, and how many lines that look like a
    reference it did not read (none, when the file is read whole).
  reingest_pages.py: --no-segment, so that an e-text's records are compared one passage each, as
    ingest_jsonl_fast.py --no-segment cut them (MBh01 went in so). Its NEXT lines carry --merged-dir and --no-segment
    when they were given.
Nothing is downloaded and nothing in the database changes. The order (each step free until --apply):
  1. a person saves the book's e-text from the GRETIL or BORI page (the BORI terms: not to be passed on);
  2. python scripts\\import_mbh_gretil.py --book 1 --src sources\\mbh_01_u.htm --out data\\raw_mbh01_ce --dry-run
  3. the same without --dry-run (it writes data\\raw_mbh01_ce\\MBh01_0001.jsonl ...);
  4. python scripts\\reingest_pages.py --doc MBh01 --merged-dir data\\raw_mbh01_ce --no-segment   (the plan)
  5. its --apply line, when the plan says the verses stay and only the prose comes in.

Anchored, all-or-nothing, marker-idempotent per file; import_mbh_gretil.py must be the file as it is (md5), as it
carries no release mark; keeps line endings and encodings; each .py is compiled first; backups .bak_mbhprose_<date>.
  python scripts\\patch_mbh_prose_2026_10_14.py --check
  python scripts\\patch_mbh_prose_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "MBH_PROSE_2026_10_14"
NEEDS = {"scripts/import_mbh_gretil.py": None, "scripts/reingest_pages.py": "REINGEST_2026_10_12"}
MD5 = {"scripts/import_mbh_gretil.py": "55cc5755ffcf6f8f488bb77198944b78"}
FILES = list(NEEDS)

E = []   # (file, number, old, new)
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/import_mbh_gretil.py', 1,
     r'''MAIN_RE = re.compile(r"^(\d{2}),(\d{3})\.(\d{3})([a-z]?)\s+(.*)$")
''',
     r'''# MBH_PROSE_2026_10_14: a prose line's last letter is a capital (01,003.001A; the e-text's readme, MBh00.txt), and
# [a-z] left every prose passage of the critical edition out (1.1.1, 1.3.2-59, 1.4.1-3 ...). The BORI form of the
# reference (01003001A) is read too. PROSE: the (chapter, verse) that were prose in the last parse.
MAIN_RE = re.compile(r"^(\d{2}),?(\d{3})\.?(\d{3})([A-Za-z]?)\s+(.*)$")
REF_RE = re.compile(r"^\d{2},?\d{3}\.?\d{3}")
PROSE = set()
''')
edit('scripts/import_mbh_gretil.py', 2,
     r'''    kept = skipped_star = 0
''',
     r'''    kept = skipped_star = prose_lines = 0
    unread = []   # MBH_PROSE_2026_10_14: lines that look like a reference and were not read
    PROSE.clear()
''')
edit('scripts/import_mbh_gretil.py', 3,
     r'''        m = MAIN_RE.match(line)
        if not m:
            continue
''',
     r'''        m = MAIN_RE.match(line)
        if not m:
            if REF_RE.match(line):
                unread.append(line[:60])
            continue
''')
edit('scripts/import_mbh_gretil.py', 4,
     r'''        chapters.setdefault(ch, {}).setdefault(vs, []).append(payload)
        kept += 1
''',
     r'''        chapters.setdefault(ch, {}).setdefault(vs, []).append(payload)
        kept += 1
        if m.group(4).isupper():   # MBH_PROSE_2026_10_14
            PROSE.add((ch, vs))
            prose_lines += 1
''')
edit('scripts/import_mbh_gretil.py', 5,
     r'''    return chapters


def to_devanagari''',
     r'''    print("  of them prose: %d lines in %d passages (MBH_PROSE_2026_10_14)" % (prose_lines, len(PROSE)))
    if unread:
        print("  NOT READ: %d lines that look like a reference (the first: %s)" % (len(unread), unread[0]))
    return chapters


def to_devanagari''')
edit('scripts/import_mbh_gretil.py', 6,
     r'''                "text_type": "verse" if len(iast_lines) > 1 else "prose",
''',
     r'''                "text_type": "prose" if (ch, vs) in PROSE else ("verse" if len(iast_lines) > 1 else "prose"),
''')

edit('scripts/reingest_pages.py', 1,
     r'''def cut(live: sqlite3.Connection, files: dict) -> dict:
    """{page_no: [row]} as ingest_jsonl_fast would write them, on a scratch table in memory."""
''',
     r'''def cut(live: sqlite3.Connection, files: dict, segment: bool = True) -> dict:
    """{page_no: [row]} as ingest_jsonl_fast would write them, on a scratch table in memory. segment=False: each
    record one passage, as ingest_jsonl_fast.py --no-segment (MBH_PROSE_2026_10_14: an e-text, MBh01)."""
''')
edit('scripts/reingest_pages.py', 2,
     r'''        ij.upsert_passages(mem, 1, pg, ij.read_jsonl(path))
''',
     r'''        ij.upsert_passages(mem, 1, pg, ij.read_jsonl(path), do_segment=segment)
''')
edit('scripts/reingest_pages.py', 3,
     r'''def plan(con, doc: str, merged: Path, only: set):
''',
     r'''def plan(con, doc: str, merged: Path, only: set, segment: bool = True):
''')
edit('scripts/reingest_pages.py', 4,
     r'''    new = cut(con, files)
''',
     r'''    new = cut(con, files, segment)
''')
edit('scripts/reingest_pages.py', 5,
     r'''    ap.add_argument("--from-dashboard", action="store_true")
    a = ap.parse_args()
    doc = a.doc
    q = "python scripts\\reingest_pages.py --doc %s" % doc + ((" --pages %s" % a.pages) if a.pages else "")
''',
     r'''    ap.add_argument("--from-dashboard", action="store_true")
    ap.add_argument("--no-segment", action="store_true",
                    help="MBH_PROSE_2026_10_14: an e-text's records as they are, one passage each, as "
                         "ingest_jsonl_fast.py --no-segment cut them (MBh01)")
    a = ap.parse_args()
    doc = a.doc
    q = "python scripts\\reingest_pages.py --doc %s" % doc + ((" --pages %s" % a.pages) if a.pages else "")
    if Path(a.merged_dir) != Path("data/raw_merged"):   # MBH_PROSE_2026_10_14: the NEXT lines say where it read
        q += " --merged-dir %s" % a.merged_dir
    if a.no_segment:
        q += " --no-segment"
''')
edit('scripts/reingest_pages.py', 6,
     r'''        p, err = plan(ro, doc, Path(a.merged_dir), only)
''',
     r'''        p, err = plan(ro, doc, Path(a.merged_dir), only, not a.no_segment)
''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/reingest_pages.py").exists():
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
        if NEEDS[rel] and NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        if rel in MD5 and hashlib.md5(p.read_bytes()).hexdigest() != MD5[rel]:
            problems.append("%s is not the file this patch was made for (md5 %s): this is not the file released"
                            % (rel, hashlib.md5(p.read_bytes()).hexdigest())); continue
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
        shutil.copy2(p, p.with_name(p.name + ".bak_mbhprose_" + stamp))
        t = p.with_name(p.name + ".tmp_mbhprose"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing was downloaded and nothing in the database changed. With the book's e-text saved by hand:")
    print("  python scripts\\import_mbh_gretil.py --book 1 --src sources\\mbh_01_u.htm --out data\\raw_mbh01_ce --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
