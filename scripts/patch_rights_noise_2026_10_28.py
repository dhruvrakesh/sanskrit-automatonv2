#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_rights_noise_2026_10_28.py  (2026-10-28)  RIGHTS_NOISE_2026_10_28

The editions' apparatus, kept on the desk. RIGHTS_FRONTMATTER sends a listed edition's own matter (passages typed
'frontmatter') as a notice. Its passages typed 'noise' were still sent with their words; in such an edition they are
its apparatus of variant readings (the Mallapurana's, tagged on 3 Oct by classify_apparatus.py; the Hayasirsa's 141,
read clearly since its vision repair: "15 maheshvarah-A,B. 16 shirodharam-A,B,C.") or a page's debris, never its
Sanskrit. scripts\\corpus_sync.py now sends them the same way (WITHHELD_TYPES); their scholarly rows, Hindi, names and
vectors stay on the desk too. A text not listed: as before.

Needs RIGHTS_FRONTMATTER_2026_10_28 in corpus_sync.py. Anchored, all-or-nothing, marker-idempotent; line endings
kept; py_compile; .bak_rightsnoise_<date> copies.

  python scripts\\patch_rights_noise_2026_10_28.py --check
  python scripts\\patch_rights_noise_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'RIGHTS_NOISE_2026_10_28'
TAG = 'rightsnoise'
FILES = ['scripts/corpus_sync.py']
NEEDS = {'scripts/corpus_sync.py': 'RIGHTS_FRONTMATTER_2026_10_28'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_sync.py', 1, '# Sanskrit goes as before (whether an edition\'s Sanskrit may be shown is decided apart, as for the BORI text).\n# A text not listed, or listed with "withhold_frontmatter": false, is sent as before.\nRIGHTS_PATH = ROOT / "configs" / "edition_rights.json"\nWITHHELD_TEXT = "[The edition\'s own matter, not shown on the site: %s.]"',
     '# Sanskrit goes as before (whether an edition\'s Sanskrit may be shown is decided apart, as for the BORI text).\n# A text not listed, or listed with "withhold_frontmatter": false, is sent as before.\n# RIGHTS_NOISE_2026_10_28: a passage of such a text typed \'noise\' goes the same way: there it is the edition\'s\n# apparatus of variant readings (the Mallapurana\'s, tagged on 3 Oct by classify_apparatus.py; the Hayasirsa\'s, read\n# clearly since its vision repair) or a page\'s debris, never its Sanskrit.\nWITHHELD_TYPES = ("frontmatter", "noise")\nRIGHTS_PATH = ROOT / "configs" / "edition_rights.json"\nWITHHELD_TEXT = "[The edition\'s own matter, not shown on the site: %s.]"')

edit('scripts/corpus_sync.py', 2, '            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])\n            vals = [code, page, idx, pid] + [_clean(x) for x in r[3:]]\n            if notice and r[3 + PASSAGE_COLS.index("text_type")] == "frontmatter":\n                held.add(pid)\n                vals = _withheld(vals, notice)',
     '            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])\n            vals = [code, page, idx, pid] + [_clean(x) for x in r[3:]]\n            if notice and r[3 + PASSAGE_COLS.index("text_type")] in WITHHELD_TYPES:   # RIGHTS_NOISE_2026_10_28\n                held.add(pid)\n                vals = _withheld(vals, notice)')


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

