#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
reingest_pages.py  (2026-10-12)  REINGEST_2026_10_12   (R3, the in-place re-ingest)

The repaired text into the database page by page, keeping what is right.

repair_text.py --use-repaired wipes a text and ingests it again: every English and Hindi translation, vector and
review goes with it, on the pages that did not change too. On 12 Oct it refused twice, as it should: the Tantric
Texts had 1,333 English translations by then, and Karan Aagama 13 pictures. Yet only 7 pages of each had
changed: the garbage Tesseract made of plates and title pages, which QUALITY_2026_10_11 refused.

This cuts each page of the repaired text (data/raw_merged) as the ingest would (ingest_jsonl_fast.upsert_passages,
run on a scratch table in memory), compares it with the database, and changes only the pages that differ:
  a passage whose text is unchanged keeps its row: its English, Hindi, vector, reviews and history stay. If its
    place on the page moved, its index moves, and a picture or a story anchored to it moves with it;
  a passage whose text changed or went is deleted, with its English, Hindi, vector and reviews (written first to
    data/reingest/<doc>_<stamp>.jsonl); a new one is inserted, untranslated;
  a page written blank (a plate) loses its passages.
Pages the repaired text does not hold, and pages that did not change, are not touched. The passages it leaves
are those a full re-ingest would make (tested). A backup first (db_backup.py), then one transaction; then
classify_doc.py and the drift check, as --use-repaired does. The register is not changed: a text held in repair
stays held. The site gets the change at the next mirror run (corpus_sync.py), the changed passages only.

  python scripts\\reingest_pages.py --doc X                  the plan: free, read-only
  python scripts\\reingest_pages.py --doc X --apply          a backup, then the changed pages
  python scripts\\reingest_pages.py --doc X --pages 2,20-21  only these pages
A translation, a picture or a story that would lose its passage must be said: --replace N (N = the English
translations it removes), as with --use-repaired. Refused while the dashboard runs another database writer.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

MARK = "REINGEST_2026_10_12"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
STEPS = Path(os.environ.get("SA_REINGEST_SCRIPTS") or SCRIPTS)   # backup, classify, drift (the tests stub them)
PY = sys.executable
sys.path.insert(0, str(SCRIPTS))

INSERT_COLS = ("text", "norm", "iast", "verse_ref", "chapter", "text_type", "chandas", "padas", "quality_score",
               "ocr_engine", "ocr_variants")
KEEP_COLS = ("norm", "iast", "verse_ref", "chapter", "chandas", "padas", "quality_score", "ocr_engine", "ocr_variants")


def page_files(merged: Path, doc: str) -> dict:
    """{page_no: path} of the repaired text; a plain file is preferred to its _norm twin."""
    rx = re.compile(r"^%s_(\d{4})(_norm)?\.jsonl$" % re.escape(doc))
    out = {}
    if merged.is_dir():
        for p in sorted(merged.iterdir()):
            m = rx.match(p.name)
            if m and (int(m.group(1)) not in out or not m.group(2)):
                out[int(m.group(1))] = p
    return out


def parse_pages(spec: str) -> set:
    want = set()
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("-")
        lo, hi = int(a), int(b or a)
        want.update(range(min(lo, hi), max(lo, hi) + 1))
    return want


def cut(live: sqlite3.Connection, files: dict, segment: bool = True) -> dict:
    """{page_no: [row]} as ingest_jsonl_fast would write them, on a scratch table in memory. segment=False: each
    record one passage, as ingest_jsonl_fast.py --no-segment (MBH_PROSE_2026_10_14: an e-text, MBh01)."""
    import ingest_jsonl_fast as ij
    sql = live.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='passages'").fetchone()[0]
    mem = sqlite3.connect(":memory:")
    mem.execute(sql)
    mem.execute("CREATE TABLE passages_fts(text, iast, translation)")   # a plain table: the ingest writes it too
    for pg, path in sorted(files.items()):
        ij.upsert_passages(mem, 1, pg, ij.read_jsonl(path), do_segment=segment)
    cols = [r[1] for r in mem.execute("PRAGMA table_info(passages)")]
    out = {pg: [] for pg in files}
    for row in mem.execute("SELECT * FROM passages ORDER BY page_no, idx"):
        d = dict(zip(cols, row))
        out.setdefault(d["page_no"], []).append(d)
    mem.close()
    return out


def tables(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def live_rows(con, doc_id: int, pages) -> dict:
    out = {pg: [] for pg in pages}
    for pid, pg, idx, text, tr, eng, var in con.execute(
            "SELECT id, page_no, idx, text, translation, ocr_engine, ocr_variants FROM passages WHERE doc_id=? "
            "ORDER BY page_no, idx", (doc_id,)):
        if pg in out:
            out[pg].append({"id": pid, "page_no": pg, "idx": idx, "text": text, "translation": tr or "",
                            "ocr_engine": eng, "ocr_variants": var})
    return out


def plan_page(old: list, new: list) -> dict:
    """Match the page's passages by their text, in order: kept (perhaps moved), new, gone."""
    if [o["text"] for o in old] == [n["text"] for n in new]:
        meta = [(o, n) for o, n in zip(old, new)
                if (o["ocr_engine"], o["ocr_variants"]) != (n.get("ocr_engine"), n.get("ocr_variants"))]
        return {"changed": False, "meta": meta, "keep": [], "insert": [], "gone": []}
    pool = {}
    for o in old:
        pool.setdefault(o["text"], []).append(o)
    keep, insert, used = [], [], set()
    for n in new:
        same = pool.get(n["text"])
        if same:
            o = same.pop(0)
            keep.append((o, n)); used.add(o["id"])
        else:
            insert.append(n)
    gone = [o for o in old if o["id"] not in used]
    return {"changed": True, "meta": [], "keep": keep, "insert": insert, "gone": gone}


def count_children(con, ids: list) -> dict:
    """What goes with these passages: English, Hindi rows, reviews, vectors."""
    res = {"english": 0, "hindi": 0, "reviews": 0, "vectors": 0, "hindi_rows": {}}
    if not ids:
        return res
    have = tables(con)
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        q = ",".join("?" * len(part))
        res["english"] += con.execute("SELECT COUNT(*) FROM passages WHERE id IN (%s) AND TRIM(COALESCE(translation,''))<>''"
                                      % q, part).fetchone()[0]
        if "translations_l10n" in have:
            for pid, lang, tr in con.execute("SELECT passage_id, lang, translation FROM translations_l10n WHERE passage_id "
                                             "IN (%s)" % q, part):
                res["hindi_rows"].setdefault(pid, []).append({"lang": lang, "translation": tr})
                if (tr or "").strip():
                    res["hindi"] += 1
        if "mt_reviews" in have:
            res["reviews"] += con.execute("SELECT COUNT(*) FROM mt_reviews WHERE passage_id IN (%s)" % q, part).fetchone()[0]
        if "passage_embeddings" in have:
            res["vectors"] += con.execute("SELECT COUNT(*) FROM passage_embeddings WHERE passage_id IN (%s)" % q,
                                          part).fetchone()[0]
    return res


def anchors(con, doc_id: int, pages) -> dict:
    """The pictures and stories anchored on these pages: {"images": [...], "stories": [...]}."""
    have, pages = tables(con), set(pages)
    out = {"images": [], "stories": []}
    if "doc_images" in have:
        for iid, pg, ix, title, st in con.execute("SELECT id, anchor_page, anchor_idx, title, status FROM doc_images WHERE "
                                                  "doc_id=? AND COALESCE(status,'')<>'retired'", (doc_id,)):
            if pg in pages:
                out["images"].append({"id": iid, "page": pg, "idx": ix, "title": title, "status": st})
    if "doc_stories" in have:
        for sid, fp, fi, tp, ti, title in con.execute("SELECT id, from_page, from_idx, to_page, to_idx, title FROM "
                                                      "doc_stories WHERE doc_id=?", (doc_id,)):
            if fp in pages or tp in pages:
                out["stories"].append({"id": sid, "from": (fp, fi), "to": (tp, ti), "title": title})
    return out


def plan(con, doc: str, merged: Path, only: set, segment: bool = True):
    row = con.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()
    if not row:
        return None, "%s is not in the database" % doc
    doc_id = row[0]
    files = page_files(merged, doc)
    if not files:
        return None, "%s holds no repaired page of %s" % (merged, doc)
    if only:
        files = {pg: p for pg, p in files.items() if pg in only}
        if not files:
            return None, "none of the pages asked for is in %s" % merged
    db_pages = {r[0] for r in con.execute("SELECT DISTINCT page_no FROM passages WHERE doc_id=?", (doc_id,))}
    new = cut(con, files, segment)
    old = live_rows(con, doc_id, files)
    pages = {pg: plan_page(old[pg], new.get(pg, [])) for pg in sorted(files)}
    changed = [pg for pg, p in pages.items() if p["changed"]]
    gone_ids = [o["id"] for pg in changed for o in pages[pg]["gone"]]
    kids = count_children(con, gone_ids)
    anc = anchors(con, doc_id, changed)
    moved_map = {}
    for pg in changed:
        for o, n in pages[pg]["keep"]:
            moved_map[(pg, o["idx"])] = n["idx"]
    gone_keys = {(pg, o["idx"]) for pg in changed for o in pages[pg]["gone"]}
    for im in anc["images"]:
        k = (im["page"], im["idx"])
        im["fate"] = "loses its passage" if k in gone_keys else ("moves to passage %d" % moved_map[k] if k in moved_map
                                                                 and moved_map[k] != im["idx"] else "stays")
    for st in anc["stories"]:
        ks = [st["from"], st["to"]]
        st["fate"] = "loses an end passage" if any(k in gone_keys for k in ks) else (
            "its range moves" if any(k in moved_map and moved_map[k] != k[1] for k in ks) else "stays")
    return {"doc": doc, "doc_id": doc_id, "files": files, "pages": pages, "changed": changed, "kids": kids,
            "anchors": anc, "db_pages": db_pages, "only_db": sorted(db_pages - set(page_files(merged, doc))),
            "gone_ids": gone_ids}, ""


def report(p: dict, q: str, apply: bool) -> tuple:
    """Prints the plan; -> (needs_say, next_command, sums)."""
    pages, changed, k = p["pages"], p["changed"], p["kids"]
    kept = sum(len(pages[pg]["keep"]) for pg in changed)
    moved = sum(1 for pg in changed for o, n in pages[pg]["keep"] if o["idx"] != n["idx"])
    new = sum(len(pages[pg]["insert"]) for pg in changed)
    gone = len(p["gone_ids"])
    meta = sum(len(v["meta"]) for v in pages.values())
    print("reingest_pages.py  %s  %s   %s" % (MARK, p["doc"], "APPLY" if apply else "PLAN (nothing written)"))
    print("  repaired pages %d | in the database %d | unchanged %d | changed %d | only in the database %d (not touched)"
          % (len(pages), len(p["db_pages"]), len(pages) - len(changed), len(changed), len(p["only_db"])))
    for pg in changed[:60]:
        v = pages[pg]
        en = sum(1 for o in v["gone"] if (o["translation"] or "").strip())
        print("  page %04d  kept %d (moved %d)  new %d  gone %d%s" % (
            pg, len(v["keep"]), sum(1 for o, n in v["keep"] if o["idx"] != n["idx"]), len(v["insert"]), len(v["gone"]),
            ("  English lost %d" % en) if en else ""))
    if len(changed) > 60:
        print("  ... and %d more pages" % (len(changed) - 60))
    print("  passages on the changed pages: kept %d (moved %d), new %d (untranslated), gone %d" % (kept, moved, new, gone))
    print("  what goes with them: English %d, Hindi %d, reviews %d, vectors %d" % (
        k["english"], k["hindi"], k["reviews"], k["vectors"]))
    if meta:
        print("  unchanged text, new engine or variants: %d passages (their translations stay)" % meta)
    for im in p["anchors"]["images"]:
        print("  picture %d (%s, page %d passage %s): %s" % (im["id"], im["status"], im["page"], im["idx"], im["fate"]))
    for st in p["anchors"]["stories"]:
        print("  story %d (%s): %s; check its citations of these pages" % (st["id"], st["title"], st["fate"]))
    lost_anchor = any(im["fate"] == "loses its passage" for im in p["anchors"]["images"]) or any(
        st["fate"] == "loses an end passage" for st in p["anchors"]["stories"])
    needs_say = bool(k["english"] or k["hindi"] or lost_anchor)
    nxt = q + " --apply" + ((" --replace %d" % k["english"]) if needs_say else "")
    return needs_say, nxt, {"kept": kept, "moved": moved, "new": new, "gone": gone, "meta": meta,
                            "lost_anchor": lost_anchor}


def run(argv, env_extra=None) -> int:
    print("$ " + " ".join(str(x) for x in argv), flush=True)
    return subprocess.call([str(x) for x in argv], cwd=str(ROOT), env=dict(os.environ, PYTHONUNBUFFERED="1",
                                                                           **(env_extra or {})))


def apply(con, p: dict, log_path: Path) -> dict:
    """One transaction: the changed pages only."""
    doc_id, pages = p["doc_id"], p["pages"]
    have = tables(con)
    fts = "passages_fts" in have
    hindi = p["kids"]["hindi_rows"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"mark": MARK, "doc": p["doc"], "at": datetime.datetime.now().isoformat(timespec="seconds"),
                            "status": "planned", "changed_pages": p["changed"]}) + "\n")
        for pg in p["changed"]:
            for o in pages[pg]["gone"]:
                f.write(json.dumps({"gone": o["id"], "page": pg, "idx": o["idx"], "text": o["text"],
                                    "translation": o["translation"], "l10n": hindi.get(o["id"], [])},
                                   ensure_ascii=False) + "\n")
    done = {"deleted": 0, "inserted": 0, "moved": 0, "meta": 0, "images": 0, "stories": 0}
    cur = con.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        # the database must still be what was planned on (a translation may have landed meanwhile)
        now = live_rows(con, doc_id, p["changed"])
        for pg in p["changed"]:
            v = pages[pg]
            was = sorted((o["id"], o["idx"], o["text"]) for o in [o for o, _ in v["keep"]] + v["gone"])
            if sorted((o["id"], o["idx"], o["text"]) for o in now[pg]) != was:
                raise RuntimeError("page %d changed in the database since the plan; run it again" % pg)
        if count_children(con, p["gone_ids"])["english"] != p["kids"]["english"]:
            raise RuntimeError("an English translation was added to a passage that goes; run it again")
        for pg, v in pages.items():
            for o, n in v["meta"]:
                cur.execute("UPDATE passages SET ocr_engine=?, ocr_variants=? WHERE id=?",
                            (n.get("ocr_engine"), n.get("ocr_variants"), o["id"]))
                done["meta"] += 1
        for pg in p["changed"]:
            v = pages[pg]
            remap = {o["idx"]: n["idx"] for o, n in v["keep"]}
            # anchors first, by id, from the old places (no chain of updates)
            if "doc_images" in have:
                for iid, ix in cur.execute("SELECT id, anchor_idx FROM doc_images WHERE doc_id=? AND anchor_page=?",
                                           (doc_id, pg)).fetchall():
                    if ix in remap and remap[ix] != ix:
                        cur.execute("UPDATE doc_images SET anchor_idx=? WHERE id=?", (remap[ix], iid)); done["images"] += 1
            if "doc_stories" in have:
                for sid, fp, fi, tp, ti in cur.execute("SELECT id, from_page, from_idx, to_page, to_idx FROM doc_stories "
                                                       "WHERE doc_id=? AND (from_page=? OR to_page=?)",
                                                       (doc_id, pg, pg)).fetchall():
                    nf = remap.get(fi, fi) if fp == pg else fi
                    nt = remap.get(ti, ti) if tp == pg else ti
                    if (nf, nt) != (fi, ti):
                        cur.execute("UPDATE doc_stories SET from_idx=?, to_idx=? WHERE id=?", (nf, nt, sid)); done["stories"] += 1
            # free the page's places, then delete, move and insert
            for o in [o for o, _ in v["keep"]] + v["gone"]:
                cur.execute("UPDATE passages SET idx=? WHERE id=?", (-o["id"], o["id"]))
            for o in v["gone"]:
                if fts:
                    cur.execute("DELETE FROM passages_fts WHERE rowid=?", (o["id"],))
                cur.execute("DELETE FROM passages WHERE id=?", (o["id"],))   # its children go by the cascade triggers
                for t in ("translations_l10n", "passage_embeddings", "mt_reviews", "entity_mentions", "footnotes"):
                    if t in have:   # where a trigger is missing
                        cur.execute("DELETE FROM %s WHERE passage_id=?" % t, (o["id"],))
                done["deleted"] += 1
            for o, n in v["keep"]:   # its translations stay; what the ingest derives is the new cut's, as a full ingest
                cur.execute("UPDATE passages SET idx=?, %s WHERE id=?" % ", ".join("%s=?" % c for c in KEEP_COLS),
                            [n["idx"]] + [n.get(c) for c in KEEP_COLS] + [o["id"]])
                done["moved"] += int(o["idx"] != n["idx"])
            for n in v["insert"]:
                cur.execute("INSERT INTO passages(doc_id, page_no, idx, %s, translation) VALUES(?,?,?,%s,'')"
                            % (", ".join(INSERT_COLS), ",".join("?" * len(INSERT_COLS))),
                            [doc_id, pg, n["idx"]] + [n.get(c) for c in INSERT_COLS])
                rid = cur.lastrowid
                if fts:
                    cur.execute("DELETE FROM passages_fts WHERE rowid=?", (rid,))
                    cur.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES(?,?,?,?)",
                                (rid, n.get("text") or "", n.get("iast") or "", ""))
                done["inserted"] += 1
            left = cur.execute("SELECT COUNT(*) FROM passages WHERE doc_id=? AND page_no=? AND idx<0", (doc_id, pg)).fetchone()[0]
            if left:
                raise RuntimeError("page %d: %d passage(s) left without a place" % (pg, left))
        con.commit()
    except Exception:
        con.rollback()
        raise
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"mark": MARK, "doc": p["doc"], "status": "applied", "done": done,
                            "at": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--pages", default="", help="only these pages: 2,20-21")
    ap.add_argument("--apply", action="store_true", help="a backup, then the changed pages")
    ap.add_argument("--replace", type=int, default=None, help="the English translations it may remove")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--log-dir", default="data/reingest")
    ap.add_argument("--from-dashboard", action="store_true")
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
    if not Path(a.db).exists():
        print("REFUSE: %s not found" % a.db); print("VERDICT: no database"); return 1
    try:
        only = parse_pages(a.pages)
    except ValueError:
        print("REFUSE: --pages takes numbers and ranges: 2,20-21"); return 2
    uri = Path(a.db).resolve().as_uri() + "?mode=ro"
    ro = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        p, err = plan(ro, doc, Path(a.merged_dir), only, not a.no_segment)
    finally:
        ro.close()
    if not p:
        print("REFUSE: " + err); print("VERDICT: nothing to compare"); print("NEXT: "); return 1
    needs_say, nxt, sums = report(p, q, a.apply)
    if not p["changed"] and not sums["meta"]:
        print("VERDICT: the database already holds the repaired text of %s, page for page: nothing to do" % doc)
        print("NEXT: ")
        return 0
    k = p["kids"]
    what = ("%d of %d pages differ from the database: %d passages go (English %d, Hindi %d), %d come in "
            "untranslated, %d stay (%d moved on their page)" % (len(p["changed"]), len(p["pages"]), sums["gone"],
                                                                k["english"], k["hindi"], sums["new"], sums["kept"],
                                                                sums["moved"]))
    if not a.apply:
        print("VERDICT: " + what)
        print("NEXT: " + nxt)
        if len(p["changed"]) > 0.5 * len(p["pages"]):
            print("ALSO: python scripts\\repair_text.py --doc %s --use-repaired   (most pages changed: the whole text "
                  "again does the same)" % doc)
        return 0
    if needs_say and (a.replace is None or a.replace < k["english"]):
        print("REFUSE: this removes %d English and %d Hindi translations%s. Say so: --replace %d" % (
            k["english"], k["hindi"], ", and a picture or a story loses its passage" if sums["lost_anchor"] else "",
            k["english"]))
        print("VERDICT: a decision is needed")
        print("NEXT: " + nxt)
        return 1
    import repair_text as rt
    w = rt.writers_running(a.from_dashboard, doc)
    if w:
        print("REFUSE: the dashboard runs a database writer: %s. Wait for it, or run this from the repair page."
              % ", ".join("%s %s" % (j.get("kind"), j.get("doc")) for j in w))
        print("VERDICT: not now: another job is running"); print("NEXT: " + q)
        return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(a.backup_dir) / ("context_pre_reingest_%s_%s.db" % (doc, stamp))
    try:
        backup.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print("REFUSE: the backup folder %s cannot be made (%s); nothing was changed." % (backup.parent, e)); return 1
    if run([PY, STEPS / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        print("REFUSE: the backup failed; nothing was changed."); print("VERDICT: not done"); return 1
    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    log = Path(a.log_dir) / ("%s_%s.jsonl" % (doc, stamp))
    try:
        done = apply(con, p, log)
    except Exception as e:
        print("FAILED: %s. Nothing was changed (the transaction was rolled back); the backup is %s." % (e, backup))
        print("VERDICT: not done"); return 1
    finally:
        con.close()
    print("  done: %(deleted)d deleted, %(inserted)d inserted, %(moved)d moved, %(meta)d engine updates; anchors moved: "
          "%(images)d pictures, %(stories)d stories" % done)
    run([PY, STEPS / "classify_doc.py", "--doc", doc, "--db", a.db, "--apply"])
    rc = run([PY, STEPS / "ocr_consensus.py", "--doc", doc, "--db", a.db, "--merged-dir", a.merged_dir, "--drift-only"],
             env_extra={"SA_CONSENSUS_SELF_KIND": "repair,repair_use"})
    print("VERDICT: the changed pages of %s are in the database%s; backup %s; what went is in %s" % (
        doc, "" if rc == 0 else " (the drift check still finds pages to look at)", backup, log))
    print("NEXT: translate it: Finish EN and Add Hindi in the Library (only the %d new passages need it)" % done["inserted"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
