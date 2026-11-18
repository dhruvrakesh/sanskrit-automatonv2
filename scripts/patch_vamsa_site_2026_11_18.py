#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_site_2026_11_18.py  (2026-11-18)  VAMSA_SITE_2026_11_18

P2a of the path of 17 Nov, night: the dynasties of the 17 works read can travel to the site by the road the three of
G5a already take (vamsa_join.py, index_sync.py, corpus.index_dynasties of C28; no new table, no schema change). What
is sent by default is unchanged: G5a's three works (106 rows on the site on 18 Nov, as the dump of 18 Nov shows).

  scripts/vamsa_join.py   dynasties(): a G6 work's title and source from vamsa_read (work_of, source_of), no index
                          text code; works_for(): "all" G5a's three (as before), "g6" the works of G6 read, "every"
                          both, or one work; --work takes them; a run other than "all" writes dynasties_<name>.json
                          and exports\\vamsa_dynasties_<name>.csv, so G5a's files are as before.
  scripts/index_sync.py   --dynasty-works all|every (default all, as before): every sends G6's dynasties too.
                          Measured on 18 Nov (the backup of 04:00, read immutable): all 106 rows, 218 kB of rows;
                          every 517 rows, 911 kB. The site's Dynasties page loads all its rows at once, so send every
                          only after the Srangam kit that loads one work at a time (P2b) is live, and from then on
                          with every run, the scheduled one too (or the site's G6 rows are taken away again).

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsasite_<date> copies.

  python scripts\\patch_vamsa_site_2026_11_18.py --check
  python scripts\\patch_vamsa_site_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_SITE_2026_11_18'
TAG = 'vamsasite'
FILES = ['scripts/vamsa_join.py', 'scripts/index_sync.py']
NEEDS = {'scripts/vamsa_join.py': 'VAMSA_JOIN_2026_11_11', 'scripts/index_sync.py': 'VAMSA_JOIN_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_join.py', 1, '                s["index_head"] = ix.head(s["entry"]) if s.get("entry") is not None else None\n            lines.append({"n": n, "label": labels(st, ln), "length": len(ln), "steps": ln})\n        out[wk] = {"title": VR.WORKS[wk]["title"], "text": TEXT_OF.get(wk, ""), "counts": j["counts"],\n                   "source": "%s; %s (data entry: %s)" % (VR.WORKS[wk]["member"], VR.GRETIL, VR.WORKS[wk]["entry"]),\n                   "lines": lines}\n    return out\n\n',
     '                s["index_head"] = ix.head(s["entry"]) if s.get("entry") is not None else None\n            lines.append({"n": n, "label": labels(st, ln), "length": len(ln), "steps": ln})\n        # VAMSA_SITE_2026_11_18: G6\'s works too (their title and source from vamsa_read; no index text code)\n        out[wk] = {"title": VR.work_of(wk)["title"], "text": TEXT_OF.get(wk, ""), "counts": j["counts"],\n                   "source": VR.source_of(wk),\n                   "lines": lines}\n    return out\n\n\ndef works_for(name: str, out_dir) -> list:\n    """VAMSA_SITE_2026_11_18: which works\' dynasties: "all" G5a\'s three (as before), "g6" the works of G6 read, "every"\n    both, or one work\'s code. Only the works read (a folder in out_dir) are given."""\n    import vamsa_read as VR\n    here = {p.name for p in Path(out_dir).iterdir() if p.is_dir()} if Path(out_dir).exists() else set()\n    g6 = [w for w in VR.G6_WORKS if w not in VR.WORKS]\n    want = {"all": list(VR.WORKS), "g6": g6, "every": list(VR.WORKS) + g6}.get(name, [name])\n    return [w for w in want if w in here and (w in VR.WORKS or w in VR.G6_WORKS)]\n\n')

edit('scripts/vamsa_join.py', 2, '    sys.path.insert(0, str(ROOT / "scripts"))\n    import vamsa_read as VR\n    if a.work != "all" and a.work not in VR.WORKS:\n        print("REFUSE: --work is all or one of %s" % ", ".join(VR.WORKS)); print("VERDICT: nothing joined"); print("NEXT: ")\n        return 1\n    for p, what in ((a.db, "the database"), (a.kin_db, "the kinships (kin_index.py)")):\n        if not Path(p).exists():',
     '    sys.path.insert(0, str(ROOT / "scripts"))\n    import vamsa_read as VR\n    if a.work not in ("all", "g6", "every") and a.work not in VR.WORKS and a.work not in VR.G6_WORKS:\n        print("REFUSE: --work is all, g6, every or one of %s" % ", ".join(list(VR.WORKS) + [w for w in VR.G6_WORKS\n                                                                                         if w not in VR.WORKS]))\n        print("VERDICT: nothing joined"); print("NEXT: python scripts\\\\vamsa_join.py --work every"); return 1\n    for p, what in ((a.db, "the database"), (a.kin_db, "the kinships (kin_index.py)")):\n        if not Path(p).exists():')

edit('scripts/vamsa_join.py', 3, '        import index_sync\n        rv.ro = index_sync.ro_immutable\n    d = dynasties(a.out, a.db, a.kin_db, None if a.work == "all" else [a.work])\n    if not d:\n        print("VERDICT: nothing read yet: run vamsa_read.py first")',
     '        import index_sync\n        rv.ro = index_sync.ro_immutable\n    d = dynasties(a.out, a.db, a.kin_db, None if a.work == "all" else (works_for(a.work, a.out) or ["-"]))\n    if not d:\n        print("VERDICT: nothing read yet: run vamsa_read.py first")')

edit('scripts/vamsa_join.py', 4, '            print("         a line of %d%s: %s" % (ln["length"], (" (%s)" % ln["label"]) if ln["label"] else "",\n                                                  " > ".join(s["name"] for s in ln["steps"])))\n    p = Path(a.out) / "dynasties.json"\n    p.parent.mkdir(parents=True, exist_ok=True)\n    p.write_text(json.dumps({"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": d},',
     '            print("         a line of %d%s: %s" % (ln["length"], (" (%s)" % ln["label"]) if ln["label"] else "",\n                                                  " > ".join(s["name"] for s in ln["steps"])))\n    tail = "" if a.work == "all" else "_" + a.work   # VAMSA_SITE_2026_11_18: G5a\'s files as before\n    p = Path(a.out) / ("dynasties%s.json" % tail)\n    p.parent.mkdir(parents=True, exist_ok=True)\n    p.write_text(json.dumps({"mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "works": d},')

edit('scripts/vamsa_join.py', 5, '    ex = Path(a.exports)\n    ex.mkdir(parents=True, exist_ok=True)\n    q = ex / "vamsa_dynasties.csv"\n    with open(q, "w", encoding="utf-8-sig", newline="") as f:\n        wr = csv.writer(f)',
     '    ex = Path(a.exports)\n    ex.mkdir(parents=True, exist_ok=True)\n    q = ex / ("vamsa_dynasties%s.csv" % tail)\n    with open(q, "w", encoding="utf-8-sig", newline="") as f:\n        wr = csv.writer(f)')

edit('scripts/index_sync.py', 1, '\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "",\n          vamsa_read_dir: str = "") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only. vamsa_read_dir:\n    G5a\'s readings (data\\\\vamsa_read), for the dynasties (VAMSA_JOIN_2026_11_11); none given, none sent."""',
     '\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "",\n          vamsa_read_dir: str = "", dynasty_works: str = "all") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only. vamsa_read_dir:\n    G5a\'s readings (data\\\\vamsa_read), for the dynasties (VAMSA_JOIN_2026_11_11); none given, none sent."""')

edit('scripts/index_sync.py', 2, '    # VAMSA_JOIN_2026_11_11: the dynasties, the Puranas\' own lines joined to the index\'s persons (vamsa_join.py)\n    if vamsa_read_dir and Path(vamsa_read_dir).exists():\n        out["dynasties"] = dynasty_rows(vamsa_read_dir, db, kin_db, g, {r["key"] for r in out["persons"]})\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,',
     '    # VAMSA_JOIN_2026_11_11: the dynasties, the Puranas\' own lines joined to the index\'s persons (vamsa_join.py)\n    if vamsa_read_dir and Path(vamsa_read_dir).exists():\n        out["dynasties"] = dynasty_rows(vamsa_read_dir, db, kin_db, g, {r["key"] for r in out["persons"]},\n                                        dynasty_works)   # VAMSA_SITE_2026_11_18\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,')

edit('scripts/index_sync.py', 3, '\n\ndef dynasty_rows(vamsa_read_dir: str, db: str, kin_db: str, g: dict, persons: set) -> list:\n    """VAMSA_JOIN_2026_11_11: one row a line ("<work>:<n>"), and one a work ("<work>:0", its counts); a step\'s person\n    is linked ("page") only when the site has a page for it (a person with a line)."""\n    import vamsa_join as vj\n    d = vj.dynasties(vamsa_read_dir, db, kin_db, graph=g)\n    rows = []\n    for wk, w in sorted(d.items()):',
     '\n\ndef dynasty_rows(vamsa_read_dir: str, db: str, kin_db: str, g: dict, persons: set, dynasty_works: str = "all") -> list:\n    """VAMSA_JOIN_2026_11_11: one row a line ("<work>:<n>"), and one a work ("<work>:0", its counts); a step\'s person\n    is linked ("page") only when the site has a page for it (a person with a line)."""\n    import vamsa_join as vj\n    # VAMSA_SITE_2026_11_18: "all" G5a\'s three (as before); "every" with G6\'s works read (--dynasty-works every)\n    d = vj.dynasties(vamsa_read_dir, db, kin_db, works=vj.works_for(dynasty_works, vamsa_read_dir) or None, graph=g)\n    rows = []\n    for wk, w in sorted(d.items()):')

edit('scripts/index_sync.py', 4, '    ap.add_argument("--status", action="store_true", help="the counts here and there")\n    ap.add_argument("--dump", default="", help="write the rows to this file (.json or .json.gz); nothing sent")\n    ap.add_argument("--if-configured", action="store_true",\n                    help="the scheduled tick: exit 0 doing nothing until the secret, the stores, C21 and corpus-index "',
     '    ap.add_argument("--status", action="store_true", help="the counts here and there")\n    ap.add_argument("--dump", default="", help="write the rows to this file (.json or .json.gz); nothing sent")\n    ap.add_argument("--dynasty-works", default="all", choices=("all", "every"),\n                    help="VAMSA_SITE_2026_11_18: the dynasties of G5a\'s three works (all, as before) or of every work "\n                         "read (every: with G6\'s); send every only once the site\'s page loads one work at a time")\n    ap.add_argument("--if-configured", action="store_true",\n                    help="the scheduled tick: exit 0 doing nothing until the secret, the stores, C21 and corpus-index "')

edit('scripts/index_sync.py', 5, '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm, vamsa_read_dir=vrd)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)',
     '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm, vamsa_read_dir=vrd,\n                 dynasty_works=a.dynasty_works)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)')


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

