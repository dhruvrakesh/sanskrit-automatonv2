#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_rights_frontmatter_2026_10_28.py  (2026-10-28)  RIGHTS_FRONTMATTER_2026_10_28

An edition in copyright keeps its own matter off the site. configs\\edition_rights.json (a new file, beside this one)
lists the texts whose scan is a modern edition, each with its edition, its notice and the evidence on the scan's own
title pages (docs\\REPAIR_AND_SOURCES_2026-10-28.md). Of such a text, scripts\\corpus_sync.py sends a passage typed 'frontmatter'
(its preface, introduction and notes, its editor's translation: the edition's own words, not the Sanskrit) with its
place and type only, its words replaced by "[The edition's own matter, not shown on the site: <its notice>.]"; its
IAST, English, Hindi, names, vector and scholarly rows stay on the desk. The Sanskrit is sent as before. A text not
listed, listed with "withhold_frontmatter": false, or no register at all: as before. On the next tick the mirror
sends the changed rows (the Ganitayuktibhasa's 48, the Mallapurana's 43, the Akasabhairava's 194, the Astadhyayi's
1); the held and withdrawn texts (the Hayasirsa, the Karanagama) only when they are released.

The replay of SCHOLAR_MIRROR (tests\\test_scholar_mirror_2026_10_18.py) compares corpus_sync.py with this patch's
backup (.bak_rightsfront_) when there is one.

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_rightsfront_<date> copies; py_compile first.

  python scripts\\patch_rights_frontmatter_2026_10_28.py --check
  python scripts\\patch_rights_frontmatter_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'RIGHTS_FRONTMATTER_2026_10_28'
TAG = 'rightsfront'
FILES = ['scripts/corpus_sync.py', 'tests/test_scholar_mirror_2026_10_18.py']
NEEDS = {'scripts/corpus_sync.py': 'SCHOLAR_MIRROR_2026_10_18', 'tests/test_scholar_mirror_2026_10_18.py': 'SCHOLAR_MIRROR_2026_10_18'}
REQUIRES = {'configs/edition_rights.json': 'RIGHTS_FRONTMATTER_2026_10_28'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/corpus_sync.py', 1, '                "translated_at", "ocr_engine", "sandhi", "morph", "source")\nL10N_COLS = ("translation", "engine", "mt_prompt_version", "translation_score", "translation_qa", "translated_at")\nSTORY_COLS = ("image_id", "status", "title", "title_hi", "why", "from_page", "from_idx", "to_page", "to_idx",\n              "story_en", "story_hi", "quote_sa", "quote_ref", "notes", "cites", "verify", "model", "provenance",',
     '                "translated_at", "ocr_engine", "sandhi", "morph", "source")\nL10N_COLS = ("translation", "engine", "mt_prompt_version", "translation_score", "translation_qa", "translated_at")\n\n# --- RIGHTS_FRONTMATTER_2026_10_28: an edition in copyright keeps its own matter off the site ----------------------\n# configs/edition_rights.json names the texts whose scan is a modern edition with a copyright notice of its own (the\n# publisher\'s or the editor\'s, as its title page prints it). Of such a text, a passage typed \'frontmatter\' (its\n# preface, introduction and notes, its editor\'s translation: the edition\'s own words, not the Sanskrit) goes to the\n# mirror with its place and its type only: its words, IAST, English, Hindi, names and vector stay on the desk. The\n# Sanskrit goes as before (whether an edition\'s Sanskrit may be shown is decided apart, as for the BORI text).\n# A text not listed, or listed with "withhold_frontmatter": false, is sent as before.\nRIGHTS_PATH = ROOT / "configs" / "edition_rights.json"\nWITHHELD_TEXT = "[The edition\'s own matter, not shown on the site: %s.]"\n_RIGHTS = {}\n\n\ndef edition_rights(path=None) -> dict:\n    """RIGHTS_FRONTMATTER_2026_10_28: {doc_code: entry} of configs/edition_rights.json (SA_EDITION_RIGHTS overrides\n    the path); {} when it is missing or unreadable."""\n    p = Path(path or os.environ.get("SA_EDITION_RIGHTS") or RIGHTS_PATH)\n    key = str(p)\n    if key not in _RIGHTS:\n        try:\n            j = json.loads(p.read_text(encoding="utf-8"))\n            texts = j.get("texts") if isinstance(j, dict) else None\n            _RIGHTS[key] = {k: v for k, v in (texts or {}).items() if isinstance(v, dict)}\n        except (OSError, ValueError):\n            _RIGHTS[key] = {}\n    return _RIGHTS[key]\n\n\ndef withheld_notice(code) -> str:\n    """RIGHTS_FRONTMATTER_2026_10_28: the notice of a text whose own matter is withheld, else \'\'."""\n    r = edition_rights().get(code) or {}\n    if not r.get("withhold_frontmatter"):\n        return ""\n    return str(r.get("notice") or "its edition is in copyright").strip()\n\n\ndef _withheld(vals: list, notice: str) -> list:\n    """A passage row (doc_code, page_no, idx, local_id, PASSAGE_COLS...) with the edition\'s words taken out."""\n    out = list(vals)\n    for c, v in (("text", WITHHELD_TEXT % notice), ("iast", None), ("translation", None), ("sandhi", None),\n                 ("morph", None), ("padas", None), ("chandas", None), ("translation_score", None),\n                 ("translation_qa", None), ("engine", None), ("mt_prompt_version", None), ("translated_at", None)):\n        out[4 + PASSAGE_COLS.index(c)] = v\n    return out\nSTORY_COLS = ("image_id", "status", "title", "title_hi", "why", "from_page", "from_idx", "to_page", "to_idx",\n              "story_en", "story_hi", "quote_sa", "quote_ref", "notes", "cites", "verify", "model", "provenance",')

edit('scripts/corpus_sync.py', 2, '            % _sel(pcols, PASSAGE_COLS, "p"), (did,)).fetchall()\n        g = Group("passages", code)\n        for r in rows:\n            pid, page, idx = r[0], r[1], r[2]',
     '            % _sel(pcols, PASSAGE_COLS, "p"), (did,)).fetchall()\n        g = Group("passages", code)\n        notice = withheld_notice(code)   # RIGHTS_FRONTMATTER_2026_10_28\n        held = set()\n        for r in rows:\n            pid, page, idx = r[0], r[1], r[2]')

edit('scripts/corpus_sync.py', 3, '            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])\n            vals = [code, page, idx, pid] + [_clean(x) for x in r[3:]]\n            row = dict(zip(("doc_code", "page_no", "idx", "local_id") + PASSAGE_COLS, vals))\n            g.add(key, vals, row)',
     '            pinfo[pid] = (r[3 + PASSAGE_COLS.index("text")], r[3 + PASSAGE_COLS.index("verse_ref")])\n            vals = [code, page, idx, pid] + [_clean(x) for x in r[3:]]\n            if notice and r[3 + PASSAGE_COLS.index("text_type")] == "frontmatter":\n                held.add(pid)\n                vals = _withheld(vals, notice)\n            row = dict(zip(("doc_code", "page_no", "idx", "local_id") + PASSAGE_COLS, vals))\n            g.add(key, vals, row)')

edit('scripts/corpus_sync.py', 4, '                        "WHERE p.doc_id=?" % _sel(lcols, L10N_COLS, "l"), (did,)):\n                    pos = passages.get(r[0])\n                    if pos is None or not r[1]:\n                        g.skipped += 1\n                        continue',
     '                        "WHERE p.doc_id=?" % _sel(lcols, L10N_COLS, "l"), (did,)):\n                    pos = passages.get(r[0])\n                    if pos is None or not r[1] or r[0] in held:   # RIGHTS_FRONTMATTER_2026_10_28\n                        g.skipped += 1\n                        continue')

edit('scripts/corpus_sync.py', 5, '                    row = dict(zip(("doc_code", "page_no", "idx", "lang") + L10N_COLS, vals))\n                    g.add(key, vals, row)\n            for key, vals, row in scholar_rows(con, code, passages, pinfo):   # SCHOLAR_MIRROR_2026_10_18\n                if key in g.rows:\n                    g.skipped += 1\n                    continue',
     '                    row = dict(zip(("doc_code", "page_no", "idx", "lang") + L10N_COLS, vals))\n                    g.add(key, vals, row)\n            held_at = {passages[x] for x in held}   # RIGHTS_FRONTMATTER_2026_10_28\n            for key, vals, row in scholar_rows(con, code, passages, pinfo):   # SCHOLAR_MIRROR_2026_10_18\n                if key in g.rows or (vals[1], vals[2]) in held_at:\n                    g.skipped += 1\n                    continue')

edit('scripts/corpus_sync.py', 6, '                    pos = passages.get(pid)\n                    canonical = _clean(canonical)\n                    if pos is None or canonical not in ent_ok:\n                        g.skipped += 1\n                        continue',
     '                    pos = passages.get(pid)\n                    canonical = _clean(canonical)\n                    if pos is None or canonical not in ent_ok or pid in held:   # RIGHTS_FRONTMATTER_2026_10_28\n                        g.skipped += 1\n                        continue')

edit('scripts/corpus_sync.py', 7, '                        "JOIN passages p ON p.id = e.passage_id WHERE p.doc_id=?", (did,)):\n                    pos = passages.get(pid)\n                    if pos is None or blob is None or not dim or int(dim) < VEC_DIMS or len(blob) != 4 * int(dim):\n                        g.skipped += 1\n                        continue',
     '                        "JOIN passages p ON p.id = e.passage_id WHERE p.doc_id=?", (did,)):\n                    pos = passages.get(pid)\n                    if (pos is None or blob is None or not dim or int(dim) < VEC_DIMS or len(blob) != 4 * int(dim)\n                            or pid in held):   # RIGHTS_FRONTMATTER_2026_10_28\n                        g.skipped += 1\n                        continue')

edit('tests/test_scholar_mirror_2026_10_18.py', 1, '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:',
     '            r = subprocess.run(pat, cwd=td, capture_output=True, text=True)\n            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:   # RIGHTS_FRONTMATTER_2026_10_28 came after: its backup of corpus_sync.py is this patch\'s\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_rightsfront_*"))\n                self.assertEqual((t / f).read_bytes(), (later[0] if later else REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:')


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

