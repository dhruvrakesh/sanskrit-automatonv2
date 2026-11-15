#!/usr/bin/env python3
# -*- coding: ascii -*-
"""


patch_reingest_keep_2026_11_15.py  (2026-11-15)  REINGEST_KEEP_2026_11_15

Asked on 15 Nov: "i am tired of wasting our APIs on translating works that you then make me drop."

1. scripts/reingest_pages.py: --keep. A repaired page changes most of its sentences by a few letters, and a sentence
   whose text changed at all was deleted with its English, its Hindi, its vector and its reviews (the Ganita
   Yuktibhasa's repair: 1,838 English). With --keep (0.9, or a share given), a new passage and one that would go, on
   the same page, whose Devanagari letters agree at that share or more, are one passage: the row stays with its
   translations, pictures and stories, and takes the mended text and what the ingest derives from it. The plan says
   what --keep would keep. Without --keep nothing changes. The log keeps the reading each kept translation was made from.
2. scripts/benchmark_sources.py: the pick no longer says "repair it first" when vision has read the scan: it says to
   bring the repair into the database (with --keep), or that the text is ready.
3. tests/test_source_pick_2026_11_13.py, tests/test_mbh_prose_2026_10_14.py: their replays compare with the copies from
   before this patch.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_reingestkeep_<date> copies.

  python scripts\\patch_reingest_keep_2026_11_15.py --check
  python scripts\\patch_reingest_keep_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'REINGEST_KEEP_2026_11_15'
TAG = 'reingestkeep'
FILES = ['scripts/reingest_pages.py', 'scripts/benchmark_sources.py', 'tests/test_source_pick_2026_11_13.py', 'tests/test_mbh_prose_2026_10_14.py']
NEEDS = {'scripts/reingest_pages.py': 'MBH_PROSE_2026_10_14', 'scripts/benchmark_sources.py': 'SOURCE_PICK_2026_11_13', 'tests/test_source_pick_2026_11_13.py': 'SOURCE_PICK_2026_11_13'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/reingest_pages.py', 1, '  python scripts\\\\reingest_pages.py --doc X                  the plan: free, read-only\n  python scripts\\\\reingest_pages.py --doc X --apply          a backup, then the changed pages\n  python scripts\\\\reingest_pages.py --doc X --pages 2,20-21  only these pages\nA translation, a picture or a story that would lose its passage must be said: --replace N (N = the English',
     '  python scripts\\\\reingest_pages.py --doc X                  the plan: free, read-only\n  python scripts\\\\reingest_pages.py --doc X --apply          a backup, then the changed pages\n  python scripts\\\\reingest_pages.py --doc X --keep           REINGEST_KEEP_2026_11_15: the plan when a sentence whose\n                                                             letters were mended keeps its row, English and Hindi\n  python scripts\\\\reingest_pages.py --doc X --pages 2,20-21  only these pages\nA translation, a picture or a story that would lose its passage must be said: --replace N (N = the English')

edit('scripts/reingest_pages.py', 2, '               "ocr_engine", "ocr_variants")\nKEEP_COLS = ("norm", "iast", "verse_ref", "chapter", "chandas", "padas", "quality_score", "ocr_engine", "ocr_variants")\n\n',
     '               "ocr_engine", "ocr_variants")\nKEEP_COLS = ("norm", "iast", "verse_ref", "chapter", "chandas", "padas", "quality_score", "ocr_engine", "ocr_variants")\n\n# REINGEST_KEEP_2026_11_15. Asked on 15 Nov: "i am tired of wasting our APIs on translating works that you then make me\n# drop". A repaired page changes most of its sentences by a few letters (vision restores the anusvaras and matras that\n# Tesseract lost), and a sentence whose text changed at all was deleted with its English, its Hindi, its vector and its\n# reviews: the Ganita Yuktibhasa\'s repair of 15 Nov would have removed 1,838 English translations, 925 of them of\n# sentences nine tenths the same. With --keep, a new passage and a passage that would go, on the same page, whose\n# Devanagari letters agree at KEEP (0.9) or more, are one passage: its row stays (its English, Hindi, vector, reviews,\n# pictures and stories with it) and takes the mended text and what the ingest derives from it. The translation was\n# made from the reading before: the log keeps that reading, and the scholarly English is made from the mended one.\nKEEP = 0.9\nKEEP_MIN = 12          # Devanagari letters: a shorter passage is not paired\n_DEV = re.compile(r"[^\\u0900-\\u0963\\u0970-\\u097f]")\n\n\ndef _letters(t) -> str:\n    return _DEV.sub("", t or "")\n\n\ndef mend_pairs(gone: list, insert: list, thr: float) -> list:\n    """REINGEST_KEEP_2026_11_15: [(old, new, ratio)], each new passage with the passage that goes whose letters it\n    shares most, at thr or more; the best pairs first, each passage once."""\n    from difflib import SequenceMatcher\n    cand = []\n    for i, n in enumerate(insert):\n        a = _letters(n.get("text"))\n        if len(a) < KEEP_MIN:\n            continue\n        for j, o in enumerate(gone):\n            b = _letters(o.get("text"))\n            if len(b) < KEEP_MIN or not 0.5 <= len(a) / float(len(b)) <= 2.0:\n                continue\n            m = SequenceMatcher(None, a, b, autojunk=False)\n            if m.real_quick_ratio() < thr or m.quick_ratio() < thr:\n                continue\n            r = m.ratio()\n            if r >= thr:\n                cand.append((r, i, j))\n    out, ui, uj = [], set(), set()\n    for r, i, j in sorted(cand, key=lambda x: (-x[0], x[1], x[2])):\n        if i in ui or j in uj:\n            continue\n        ui.add(i); uj.add(j)\n        out.append((gone[j], insert[i], round(r, 3)))\n    return out\n\n')

edit('scripts/reingest_pages.py', 3, '\n\ndef plan_page(old: list, new: list) -> dict:\n    """Match the page\'s passages by their text, in order: kept (perhaps moved), new, gone."""\n    if [o["text"] for o in old] == [n["text"] for n in new]:\n        meta = [(o, n) for o, n in zip(old, new)\n                if (o["ocr_engine"], o["ocr_variants"]) != (n.get("ocr_engine"), n.get("ocr_variants"))]\n        return {"changed": False, "meta": meta, "keep": [], "insert": [], "gone": []}\n    pool = {}\n    for o in old:',
     '\n\ndef plan_page(old: list, new: list, thr: float = 0.0) -> dict:\n    """Match the page\'s passages by their text, in order: kept (perhaps moved), new, gone; with thr (--keep), mended\n    too: a new passage and one that would go, the same but for its letters (REINGEST_KEEP_2026_11_15)."""\n    if [o["text"] for o in old] == [n["text"] for n in new]:\n        meta = [(o, n) for o, n in zip(old, new)\n                if (o["ocr_engine"], o["ocr_variants"]) != (n.get("ocr_engine"), n.get("ocr_variants"))]\n        return {"changed": False, "meta": meta, "keep": [], "insert": [], "gone": [], "mend": []}\n    pool = {}\n    for o in old:')

edit('scripts/reingest_pages.py', 4, '            insert.append(n)\n    gone = [o for o in old if o["id"] not in used]\n    return {"changed": True, "meta": [], "keep": keep, "insert": insert, "gone": gone}\n\n',
     '            insert.append(n)\n    gone = [o for o in old if o["id"] not in used]\n    mend = mend_pairs(gone, insert, thr) if thr else []   # REINGEST_KEEP_2026_11_15\n    if mend:\n        mo, mn = {id(o) for o, _n, _r in mend}, {id(n) for _o, n, _r in mend}\n        gone = [o for o in gone if id(o) not in mo]\n        insert = [n for n in insert if id(n) not in mn]\n    return {"changed": True, "meta": [], "keep": keep, "insert": insert, "gone": gone, "mend": mend}\n\n')

edit('scripts/reingest_pages.py', 5, '\n\ndef plan(con, doc: str, merged: Path, only: set, segment: bool = True):\n    row = con.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()\n    if not row:',
     '\n\ndef plan(con, doc: str, merged: Path, only: set, segment: bool = True, keep: float = 0.0):\n    row = con.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()\n    if not row:')

edit('scripts/reingest_pages.py', 6, '    new = cut(con, files, segment)\n    old = live_rows(con, doc_id, files)\n    pages = {pg: plan_page(old[pg], new.get(pg, [])) for pg in sorted(files)}\n    changed = [pg for pg, p in pages.items() if p["changed"]]\n    gone_ids = [o["id"] for pg in changed for o in pages[pg]["gone"]]',
     '    new = cut(con, files, segment)\n    old = live_rows(con, doc_id, files)\n    pages = {pg: plan_page(old[pg], new.get(pg, []), keep) for pg in sorted(files)}\n    changed = [pg for pg, p in pages.items() if p["changed"]]\n    gone_ids = [o["id"] for pg in changed for o in pages[pg]["gone"]]')

edit('scripts/reingest_pages.py', 7, '    for pg in changed:\n        for o, n in pages[pg]["keep"]:\n            moved_map[(pg, o["idx"])] = n["idx"]\n    gone_keys = {(pg, o["idx"]) for pg in changed for o in pages[pg]["gone"]}',
     '    for pg in changed:\n        for o, n in pages[pg]["keep"]:\n            moved_map[(pg, o["idx"])] = n["idx"]\n        for o, n, _r in pages[pg]["mend"]:   # REINGEST_KEEP_2026_11_15: a mended passage keeps its pictures and stories\n            moved_map[(pg, o["idx"])] = n["idx"]\n    gone_keys = {(pg, o["idx"]) for pg in changed for o in pages[pg]["gone"]}')

edit('scripts/reingest_pages.py', 8, '        st["fate"] = "loses an end passage" if any(k in gone_keys for k in ks) else (\n            "its range moves" if any(k in moved_map and moved_map[k] != k[1] for k in ks) else "stays")\n    return {"doc": doc, "doc_id": doc_id, "files": files, "pages": pages, "changed": changed, "kids": kids,\n            "anchors": anc, "db_pages": db_pages, "only_db": sorted(db_pages - set(page_files(merged, doc))),\n            "gone_ids": gone_ids}, ""\n\n',
     '        st["fate"] = "loses an end passage" if any(k in gone_keys for k in ks) else (\n            "its range moves" if any(k in moved_map and moved_map[k] != k[1] for k in ks) else "stays")\n    could = 0   # REINGEST_KEEP_2026_11_15: what --keep would keep, said in the plan\n    if not keep:\n        for pg in changed:\n            could += sum(1 for o, _n, _r in mend_pairs(pages[pg]["gone"], pages[pg]["insert"], KEEP)\n                         if (o["translation"] or "").strip())\n    return {"doc": doc, "doc_id": doc_id, "files": files, "pages": pages, "changed": changed, "kids": kids,\n            "anchors": anc, "db_pages": db_pages, "only_db": sorted(db_pages - set(page_files(merged, doc))),\n            "gone_ids": gone_ids, "could_keep": could, "keep": keep}, ""\n\n')

edit('scripts/reingest_pages.py', 9, '    new = sum(len(pages[pg]["insert"]) for pg in changed)\n    gone = len(p["gone_ids"])\n    meta = sum(len(v["meta"]) for v in pages.values())\n    print("reingest_pages.py  %s  %s   %s" % (MARK, p["doc"], "APPLY" if apply else "PLAN (nothing written)"))',
     '    new = sum(len(pages[pg]["insert"]) for pg in changed)\n    gone = len(p["gone_ids"])\n    mended = sum(len(pages[pg]["mend"]) for pg in changed)   # REINGEST_KEEP_2026_11_15\n    meta = sum(len(v["meta"]) for v in pages.values())\n    print("reingest_pages.py  %s  %s   %s" % (MARK, p["doc"], "APPLY" if apply else "PLAN (nothing written)"))')

edit('scripts/reingest_pages.py', 10, '        v = pages[pg]\n        en = sum(1 for o in v["gone"] if (o["translation"] or "").strip())\n        print("  page %04d  kept %d (moved %d)  new %d  gone %d%s" % (\n            pg, len(v["keep"]), sum(1 for o, n in v["keep"] if o["idx"] != n["idx"]), len(v["insert"]), len(v["gone"]),\n            ("  English lost %d" % en) if en else ""))\n    if len(changed) > 60:\n        print("  ... and %d more pages" % (len(changed) - 60))\n    print("  passages on the changed pages: kept %d (moved %d), new %d (untranslated), gone %d" % (kept, moved, new, gone))\n    print("  what goes with them: English %d, Hindi %d, reviews %d, vectors %d" % (\n        k["english"], k["hindi"], k["reviews"], k["vectors"]))',
     '        v = pages[pg]\n        en = sum(1 for o in v["gone"] if (o["translation"] or "").strip())\n        print("  page %04d  kept %d (moved %d)  new %d  gone %d%s%s" % (\n            pg, len(v["keep"]), sum(1 for o, n in v["keep"] if o["idx"] != n["idx"]), len(v["insert"]), len(v["gone"]),\n            ("  mended %d" % len(v["mend"])) if v["mend"] else "", ("  English lost %d" % en) if en else ""))\n    if len(changed) > 60:\n        print("  ... and %d more pages" % (len(changed) - 60))\n    print("  passages on the changed pages: kept %d (moved %d), new %d (untranslated), gone %d" % (kept, moved, new, gone))\n    if mended:\n        print("  mended in place (--keep %.2f): %d passage(s) keep their row, their English and their Hindi; the text "\n              "is the repair\'s, the translation was made from the reading before (the log keeps that reading)"\n              % (p.get("keep") or KEEP, mended))\n    print("  what goes with them: English %d, Hindi %d, reviews %d, vectors %d" % (\n        k["english"], k["hindi"], k["reviews"], k["vectors"]))')

edit('scripts/reingest_pages.py', 11, '    nxt = q + " --apply" + ((" --replace %d" % k["english"]) if needs_say else "")\n    return needs_say, nxt, {"kept": kept, "moved": moved, "new": new, "gone": gone, "meta": meta,\n                            "lost_anchor": lost_anchor}\n\n',
     '    nxt = q + " --apply" + ((" --replace %d" % k["english"]) if needs_say else "")\n    return needs_say, nxt, {"kept": kept, "moved": moved, "new": new, "gone": gone, "meta": meta,\n                            "lost_anchor": lost_anchor, "mended": mended}\n\n')

edit('scripts/reingest_pages.py', 12, '                                    "translation": o["translation"], "l10n": hindi.get(o["id"], [])},\n                                   ensure_ascii=False) + "\\n")\n    done = {"deleted": 0, "inserted": 0, "moved": 0, "meta": 0, "images": 0, "stories": 0}\n    cur = con.cursor()\n    cur.execute("BEGIN IMMEDIATE")',
     '                                    "translation": o["translation"], "l10n": hindi.get(o["id"], [])},\n                                   ensure_ascii=False) + "\\n")\n            for o, n, r in pages[pg]["mend"]:   # REINGEST_KEEP_2026_11_15: the reading its translation was made from\n                f.write(json.dumps({"mended": o["id"], "page": pg, "idx": o["idx"], "text": o["text"], "ratio": r,\n                                    "translation": o["translation"]}, ensure_ascii=False) + "\\n")\n    done = {"deleted": 0, "inserted": 0, "moved": 0, "meta": 0, "images": 0, "stories": 0, "mended": 0}\n    cur = con.cursor()\n    cur.execute("BEGIN IMMEDIATE")')

edit('scripts/reingest_pages.py', 13, '        for pg in p["changed"]:\n            v = pages[pg]\n            was = sorted((o["id"], o["idx"], o["text"]) for o in [o for o, _ in v["keep"]] + v["gone"])\n            if sorted((o["id"], o["idx"], o["text"]) for o in now[pg]) != was:\n                raise RuntimeError("page %d changed in the database since the plan; run it again" % pg)',
     '        for pg in p["changed"]:\n            v = pages[pg]\n            was = sorted((o["id"], o["idx"], o["text"]) for o in [o for o, _ in v["keep"]] + v["gone"]\n                         + [o for o, _n, _r in v["mend"]])\n            if sorted((o["id"], o["idx"], o["text"]) for o in now[pg]) != was:\n                raise RuntimeError("page %d changed in the database since the plan; run it again" % pg)')

edit('scripts/reingest_pages.py', 14, '            v = pages[pg]\n            remap = {o["idx"]: n["idx"] for o, n in v["keep"]}\n            # anchors first, by id, from the old places (no chain of updates)\n            if "doc_images" in have:',
     '            v = pages[pg]\n            remap = {o["idx"]: n["idx"] for o, n in v["keep"]}\n            remap.update({o["idx"]: n["idx"] for o, n, _r in v["mend"]})   # REINGEST_KEEP_2026_11_15\n            # anchors first, by id, from the old places (no chain of updates)\n            if "doc_images" in have:')

edit('scripts/reingest_pages.py', 15, '                        cur.execute("UPDATE doc_stories SET from_idx=?, to_idx=? WHERE id=?", (nf, nt, sid)); done["stories"] += 1\n            # free the page\'s places, then delete, move and insert\n            for o in [o for o, _ in v["keep"]] + v["gone"]:\n                cur.execute("UPDATE passages SET idx=? WHERE id=?", (-o["id"], o["id"]))\n            for o in v["gone"]:',
     '                        cur.execute("UPDATE doc_stories SET from_idx=?, to_idx=? WHERE id=?", (nf, nt, sid)); done["stories"] += 1\n            # free the page\'s places, then delete, move and insert\n            for o in [o for o, _ in v["keep"]] + v["gone"] + [o for o, _n, _r in v["mend"]]:\n                cur.execute("UPDATE passages SET idx=? WHERE id=?", (-o["id"], o["id"]))\n            for o in v["gone"]:')

edit('scripts/reingest_pages.py', 16, '                            [n["idx"]] + [n.get(c) for c in KEEP_COLS] + [o["id"]])\n                done["moved"] += int(o["idx"] != n["idx"])\n            for n in v["insert"]:\n                cur.execute("INSERT INTO passages(doc_id, page_no, idx, %s, translation) VALUES(?,?,?,%s,\'\')"',
     '                            [n["idx"]] + [n.get(c) for c in KEEP_COLS] + [o["id"]])\n                done["moved"] += int(o["idx"] != n["idx"])\n            for o, n, _r in v["mend"]:   # REINGEST_KEEP_2026_11_15: the row stays, with its translations; the text is the repair\'s\n                cur.execute("UPDATE passages SET idx=?, %s WHERE id=?" % ", ".join("%s=?" % c for c in INSERT_COLS),\n                            [n["idx"]] + [n.get(c) for c in INSERT_COLS] + [o["id"]])\n                if fts:\n                    cur.execute("DELETE FROM passages_fts WHERE rowid=?", (o["id"],))\n                    cur.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",\n                                (o["id"], n.get("text") or "", n.get("iast") or "", o["translation"] or ""))\n                done["mended"] += 1\n            for n in v["insert"]:\n                cur.execute("INSERT INTO passages(doc_id, page_no, idx, %s, translation) VALUES(?,?,?,%s,\'\')"')

edit('scripts/reingest_pages.py', 17, '    ap.add_argument("--apply", action="store_true", help="a backup, then the changed pages")\n    ap.add_argument("--replace", type=int, default=None, help="the English translations it may remove")\n    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\\backups")\n    ap.add_argument("--log-dir", default="data/reingest")',
     '    ap.add_argument("--apply", action="store_true", help="a backup, then the changed pages")\n    ap.add_argument("--replace", type=int, default=None, help="the English translations it may remove")\n    ap.add_argument("--keep", type=float, nargs="?", const=KEEP, default=0.0,\n                    help="REINGEST_KEEP_2026_11_15: a passage whose Devanagari letters agree with one that would go, at "\n                         "this share or more (0.9 when no number is given), keeps its row, English and Hindi")\n    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\\backups")\n    ap.add_argument("--log-dir", default="data/reingest")')

edit('scripts/reingest_pages.py', 18, '    if a.no_segment:\n        q += " --no-segment"\n    if not Path(a.db).exists():\n        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); return 1',
     '    if a.no_segment:\n        q += " --no-segment"\n    if a.keep and not 0.5 <= a.keep <= 1.0:\n        print("REFUSE: --keep takes a share between 0.5 and 1 (0.9 when no number is given)"); return 2\n    q0 = q\n    if a.keep:   # REINGEST_KEEP_2026_11_15\n        q += " --keep" + ("" if a.keep == KEEP else " %.2f" % a.keep)\n    if not Path(a.db).exists():\n        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); return 1')

edit('scripts/reingest_pages.py', 19, '    ro = sqlite3.connect(uri, uri=True, timeout=30)\n    try:\n        p, err = plan(ro, doc, Path(a.merged_dir), only, not a.no_segment)\n    finally:\n        ro.close()',
     '    ro = sqlite3.connect(uri, uri=True, timeout=30)\n    try:\n        p, err = plan(ro, doc, Path(a.merged_dir), only, not a.no_segment, a.keep)\n    finally:\n        ro.close()')

edit('scripts/reingest_pages.py', 20, '                                                                k["english"], k["hindi"], sums["new"], sums["kept"],\n                                                                sums["moved"]))\n    if not a.apply:\n        print("VERDICT: " + what)\n        print("NEXT: " + nxt)\n        if len(p["changed"]) > 0.5 * len(p["pages"]):\n            print("ALSO: python scripts\\\\repair_text.py --doc %s --use-repaired   (most pages changed: the whole text "',
     '                                                                k["english"], k["hindi"], sums["new"], sums["kept"],\n                                                                sums["moved"]))\n    if sums["mended"]:\n        what += "; %d mended in place keep their English and Hindi" % sums["mended"]\n    if not a.apply:\n        print("VERDICT: " + what)\n        print("NEXT: " + nxt)\n        if not a.keep and p.get("could_keep"):   # REINGEST_KEEP_2026_11_15\n            print("ALSO: %s --keep   (%d of the %d English translations stay with their sentences: the same sentence, "\n                  "its letters mended; the plan is free)" % (q0, p["could_keep"], k["english"]))\n        if len(p["changed"]) > 0.5 * len(p["pages"]):\n            print("ALSO: python scripts\\\\repair_text.py --doc %s --use-repaired   (most pages changed: the whole text "')

edit('scripts/reingest_pages.py', 21, '        print("VERDICT: a decision is needed")\n        print("NEXT: " + nxt)\n        return 1\n    import repair_text as rt',
     '        print("VERDICT: a decision is needed")\n        print("NEXT: " + nxt)\n        if not a.keep and p.get("could_keep"):   # REINGEST_KEEP_2026_11_15\n            print("ALSO: %s --keep   (%d of the %d English translations stay with their sentences; the plan is free)"\n                  % (q0, p["could_keep"], k["english"]))\n        return 1\n    import repair_text as rt')

edit('scripts/reingest_pages.py', 22, '    print("  done: %(deleted)d deleted, %(inserted)d inserted, %(moved)d moved, %(meta)d engine updates; anchors moved: "\n          "%(images)d pictures, %(stories)d stories" % done)\n    run([PY, STEPS / "classify_doc.py", "--doc", doc, "--db", a.db, "--apply"])\n    rc = run([PY, STEPS / "ocr_consensus.py", "--doc", doc, "--db", a.db, "--merged-dir", a.merged_dir, "--drift-only"],',
     '    print("  done: %(deleted)d deleted, %(inserted)d inserted, %(moved)d moved, %(meta)d engine updates; anchors moved: "\n          "%(images)d pictures, %(stories)d stories" % done)\n    if done.get("mended"):\n        print("  mended in place: %d passage(s) kept their English and Hindi (REINGEST_KEEP_2026_11_15)" % done["mended"])\n    run([PY, STEPS / "classify_doc.py", "--doc", doc, "--db", a.db, "--apply"])\n    rc = run([PY, STEPS / "ocr_consensus.py", "--doc", doc, "--db", a.db, "--merged-dir", a.merged_dir, "--drift-only"],')

edit('scripts/benchmark_sources.py', 1, '\n\ndef pick_reading(res: dict, doc: str) -> dict:\n    """{doc, reading, why, then}: the reading to make the scholarly English and its prose from (SOURCE_PICK_2026_11_13)."""',
     '\n\ndef repair_state(rd: list, ours: dict, doc: str):\n    """PICK_REPAIRED (patch REINGEST_KEEP_2026_11_15): when ours is not cosmetic, is there a repair still to make?\n    (why, then) or None (repair first, as before). On 15 Nov the Ganita Yuktibhasa\'s pick still said "repair it first"\n    after vision had read 290 of its 339 pages: the repair was made, and was not yet in the database; and what the\n    count of Latin letters calls misread was partly the edition\'s own English (its introduction, its glossary)."""\n    v = next((x for x in rd if x.get("label") == "vision"), None)\n    pages = int((ours or {}).get("pages") or 0)\n    if not v or not pages or int(v.get("pages") or 0) < 0.8 * pages:\n        return None\n    db = next((x for x in rd if x.get("kind") == "db"), None)\n    read = "vision has read %d of its %d pages: the repair is made" % (int(v.get("pages") or 0), pages)\n    if db and db.get("f1_ours") is not None and db["f1_ours"] < 0.98:\n        return ("%s, but the database still holds the reading before (it agrees with the repair on F1 %.2f): bring "\n                "the repair in, keeping the translations of the sentences that are the same but for their letters, "\n                "then its scholarly English" % (read, db["f1_ours"]),\n                "python scripts\\\\reingest_pages.py --doc %s --keep   (free: the plan)" % doc)\n    return ("%s and the database holds it; what is still counted as misread (%.2f%% of the letters) is Latin inside "\n            "the Devanagari, which in an edition with English pages (an introduction, a glossary) is partly the "\n            "edition\'s own English: ready for its scholarly English and its prose"\n            % (read, (ours or {}).get("misread_letters_pct") or 0.0), "")\n\n\ndef pick_reading(res: dict, doc: str) -> dict:\n    """{doc, reading, why, then}: the reading to make the scholarly English and its prose from (SOURCE_PICK_2026_11_13)."""')

edit('scripts/benchmark_sources.py', 2, '               "otherwise; ours for the edition, the e-text to compare" % (w["label"], f1) if f1 is not None else\n               "the e-text (%s) could not be aligned with ours: ours for the edition, the e-text to compare" % w["label"])\n        if ours and ours.get("level") not in ("cosmetic", None, "-"):\n            why += "; ours misreads %.2f%% (%s): repair it first" % (om or 0.0, ours.get("level"))\n        return {"doc": doc, "reading": (ours or {}).get("label", ""), "why": why,\n                "then": "python scripts\\\\repair_text.py --doc %s   (free: what the repair would cost)" % doc\n                if ours and ours.get("level") not in ("cosmetic", None, "-") else ""}\n    if not ours:\n        return {"doc": doc, "reading": "", "why": "nothing of this text is read yet", "then": ""}',
     '               "otherwise; ours for the edition, the e-text to compare" % (w["label"], f1) if f1 is not None else\n               "the e-text (%s) could not be aligned with ours: ours for the edition, the e-text to compare" % w["label"])\n        then = ""\n        if ours and ours.get("level") not in ("cosmetic", None, "-"):\n            st = repair_state(rd, ours, doc)   # PICK_REPAIRED (REINGEST_KEEP_2026_11_15)\n            if st:\n                why += "; " + st[0]\n                then = st[1]\n            else:\n                why += "; ours misreads %.2f%% (%s): repair it first" % (om or 0.0, ours.get("level"))\n                then = "python scripts\\\\repair_text.py --doc %s   (free: what the repair would cost)" % doc\n        return {"doc": doc, "reading": (ours or {}).get("label", ""), "why": why, "then": then}\n    if not ours:\n        return {"doc": doc, "reading": "", "why": "nothing of this text is read yet", "then": ""}')

edit('scripts/benchmark_sources.py', 3, '                "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (cosmetic): ready for its scholarly "\n                       "English and its prose" % (ours["label"], om or 0.0), "then": ""}\n    return {"doc": doc, "reading": ours["label"],\n            "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (%s): repair it first (vision reads "',
     '                "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (cosmetic): ready for its scholarly "\n                       "English and its prose" % (ours["label"], om or 0.0), "then": ""}\n    st = repair_state(rd, ours, doc)   # PICK_REPAIRED (REINGEST_KEEP_2026_11_15)\n    if st:\n        return {"doc": doc, "reading": ours["label"], "why": "no e-text of it here; " + st[0], "then": st[1]}\n    return {"doc": doc, "reading": ours["label"],\n            "why": "no e-text of it here; ours (%s) misreads %.2f%% of the letters (%s): repair it first (vision reads "')

edit('tests/test_source_pick_2026_11_13.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in FILES:\n                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in FILES:\n                want = (REPO / rel).read_bytes()\n                later = sorted((REPO / rel).parent.glob(Path(rel).name + ".bak_reingestkeep_*"))   # REINGEST_KEEP_2026_11_15 came after\n                if later and b"REINGEST_KEEP_2026_11_15" in want:\n                    want = later[0].read_bytes()\n                self.assertEqual((t / rel).read_bytes(), want, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')

edit('tests/test_mbh_prose_2026_10_14.py', 1, '            for f in baks:\n                later = sorted(SCRIPTS.glob(f + ".bak_scholarv2_*"))   # SCHOLAR_V2_2026_10_14 came after (the importer)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)',
     '            for f in baks:\n                later = sorted(SCRIPTS.glob(f + ".bak_scholarv2_*"))   # SCHOLAR_V2_2026_10_14 came after (the importer)\n                later = later or sorted(SCRIPTS.glob(f + ".bak_reingestkeep_*"))   # REINGEST_KEEP_2026_11_15 came after (reingest_pages.py)\n                want = later[0] if later else (SCRIPTS / f)\n                self.assertEqual((t / "scripts" / f).read_bytes(), want.read_bytes(), f)')


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

