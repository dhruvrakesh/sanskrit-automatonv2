"""Write a house-style patcher from base/new file pairs: anchored edits (each unique in the base), all-or-nothing,
marker-idempotent per file, needs-markers, line endings kept, .bak_<tag>_<date> backups, py_compile of .py targets."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mkpatch import edits


def lit(s) -> str:
    return ascii(s)


def build(out_path, mark, tag, doc, files, needs, requires=None, base="/home/claude/base", new="/home/claude/new"):
    E = []
    for f in files:
        o = open(os.path.join(base, f), encoding="utf-8").read().replace("\r\n", "\n")
        n = open(os.path.join(new, f), encoding="utf-8").read().replace("\r\n", "\n")
        assert mark in n and mark not in o, (f, "the marker must be new in the file")
        for k, (a, b) in enumerate(edits(o, n), 1):
            E.append((f, k, a, b))
    L = ["#!/usr/bin/env python3", "# -*- coding: ascii -*-", '"""', doc.rstrip("\n").replace("\\", "\\\\"), '"""',
         "from __future__ import annotations", "import argparse, datetime, os, py_compile, shutil, sys, tempfile",
         "from pathlib import Path", "", "MARK = %s" % lit(mark), "TAG = %s" % lit(tag), "FILES = %s" % lit(list(files)),
         "NEEDS = %s" % lit(dict(needs)), "REQUIRES = %s   # another file that must carry a marker first" % lit(dict(requires or {})),
         "E = []", "", "", "def edit(f, n, old, new):", "    E.append((f, n, old, new))", "", ""]
    for f, k, a, b in E:
        L.append("edit(%s, %d, %s,\n     %s)" % (lit(f), k, lit(a), lit(b)))
        L.append("")
    L.append(TAIL)
    src = "\n".join(L) + "\n"
    assert all(ord(c) < 128 for c in src)
    open(out_path, "w", encoding="ascii", newline="").write(src)
    return len(E)


TAIL = r'''
def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
