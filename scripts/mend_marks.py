#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
mend_marks.py  (2026-10-28)  INLINE_MARKS_2026_10_28

An edition's footnote numbers, read into its Sanskrit. A critical edition prints a small raised number after the word
its apparatus speaks of, or before the word that opens a reading; vision OCR writes it as ASCII digits glued to the
word ("caiva21", "dvara13mucyate", "4amita"). On the 28 Oct backup: the Hayasirsa (Asiatic Society, 1976), 586 of its
1,407 verses read by vision (854 numbers); the Natyasastra (GOS), 900 of 2,697 (1,801). They are in the text we
read, search and show, and in its IAST. The scholarly English was made past them (its translator reads the verse, not
the note number), so it stays good.

What it does, for the text named with --doc only:
  - in its passages typed mula, prose or colophon and read by vision (passages.ocr_engine gemini-vision...), an ASCII
    number of one to three digits glued after a Devanagari letter or sign, or glued before one after a space, a line's
    start or a bracket (never after a danda, never a decimal or part of a longer number, never a Devanagari numeral)
    is taken out; the passage's IAST is made again from the mended text (iast_utils: on the 28 Oct backup it gives
    back the stored IAST of all 847 unmarked Hayasirsa verses exactly), its search row (passages_fts) made again;
  - a passage Tesseract read is left as it is: there a 5 is often the avagraha (Rgveda vol. II: 568 passages, the
    Daivat-Sanhita 255, the Yogavasistha 254) and wants its own mend, or a better witness;
  - a scholarly English made from the passage as it read (scholar_translations.src_hash of the old text) is carried
    to the mended text (its hash set to the new text's): only the note numbers changed, so it is still the English
    of that verse (corpus_sync.py sends a scholarly row only when its hash is the text's);
  - the English, the Hindi, the names and the vectors are not touched; nor the raw OCR page (passages.norm) and the
    OCR variants, which are the evidence of what the scan reads and stay as read.
Refused for a text where fewer than 5 in 100 of its vision-read verses carry such a number (the Sama Veda's 1, 2 and
3 are its svaras, not notes: --force only after looking). A dry run by default (counts and examples); --apply writes
data/mend_marks_<doc>_<stamp>.json first (every passage's old text and IAST, every hash carried) and --undo FILE puts
back exactly that, where the passage still reads as this tool left it. Each --apply backs the database up first
(scripts\\db_backup.py, to --backup-dir: D:\\backups, as context_pre_mendmarks_<doc>_<stamp>.db) and writes nothing
when the backup fails. Run it with the dashboard idle.

  python scripts\\mend_marks.py --doc HAYASHIRSHA_PANCARATRA --show 8
  python scripts\\mend_marks.py --doc HAYASHIRSHA_PANCARATRA --apply
  python scripts\\mend_marks.py --undo data\\mend_marks_HAYASHIRSHA_PANCARATRA_20261028_150000.json --apply
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, sqlite3, subprocess, sys
from pathlib import Path

MARK = "INLINE_MARKS_2026_10_28"
ROOT = Path(__file__).resolve().parent.parent
TYPES = ("mula", "prose", "colophon")
MIN_SHARE = 0.05
VISION = "gemini-vision"   # passages.ocr_engine of a page vision read (a Tesseract reading's 5 is often an avagraha)
# 1 to 3 ASCII digits, not part of a longer number or a decimal, either glued after a Devanagari letter or sign
# (U+0900-U+0963, U+0970-U+097F: not the dandas U+0964-5, not the numerals U+0966-F), where an edition prints the
# number that closes a reading, or glued before one and after a space, a line's start or a bracket, where it prints
# the number that opens it ("4amita..." in the Natyasastra)
LETTER = re.compile(r"[\u0900-\u0963\u0970-\u097f]")
MARKS = re.compile(r"(?<=[\u0900-\u0963\u0970-\u097f])[0-9]{1,3}(?![0-9]|\.[0-9])"
                   r"|(?<![0-9.\u0900-\u0963\u0970-\u097f])[0-9]{1,3}(?=[\u0900-\u0963\u0970-\u097f])")


def src_hash(text) -> str:
    """= scholar_translate.src_hash: the hash a scholarly row keeps of the Sanskrit it was made from."""
    return hashlib.sha256(" ".join(str(text or "").split()).encode("utf-8")).hexdigest()[:16]


def mend(text):
    """(the text without its glued note numbers, how many were taken out)."""
    if not text:
        return text, 0
    out, n = MARKS.subn("", text)
    return out, n


def to_iast(text, old_iast):
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from iast_utils import devanagari_to_iast
        return devanagari_to_iast(text)
    except Exception:
        return old_iast   # no transliterator here: the IAST is left as it was


def tables(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}


def cols(con, t) -> set:
    return {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def plan(con, doc: str) -> dict:
    d = con.execute("SELECT id FROM docs WHERE code = ?", (doc,)).fetchone()
    if not d:
        return {"error": "no text %s in the database" % doc}
    pc = cols(con, "passages")
    sel = ", ".join(c if c in pc else "NULL" for c in ("text", "iast", "text_type", "translation", "ocr_engine"))
    known = "ocr_engine" in pc   # an older database without it: every passage is taken as read
    rows = con.execute("SELECT id, page_no, idx, %s FROM passages WHERE doc_id = ? ORDER BY page_no, idx" % sel,
                       (d[0],)).fetchall()
    verses = [r for r in rows if (r[5] or "mula") == "mula" and (not known or str(r[7] or "").startswith(VISION))]
    changes, marks, left = [], 0, 0
    for pid, page, idx, text, iast, tt, en, oe in rows:
        if (tt or "mula") not in TYPES:
            continue
        new, n = mend(text)
        if n and known and not str(oe or "").startswith(VISION):
            left += 1   # not read by vision: its digits may be an avagraha or a danda, so left as they are
            continue
        if n:
            marks += n
            changes.append({"id": pid, "page": page, "idx": idx, "type": tt or "mula", "text_old": text, "text_new": new,
                            "iast_old": iast, "english": en or "", "marks": n})
    with_marks = sum(1 for c in changes if c["type"] == "mula")
    # ten or more numbers, one to every five letters or closer: a svara notation (the Sama Veda's 1 2 3), not notes
    svara = sum(1 for c in changes if c["marks"] >= 10 and c["marks"] >= 0.2 * len(LETTER.findall(c["text_old"] or "")))
    share = with_marks / float(len(verses)) if verses else 0.0
    sch = []
    if "scholar_translations" in tables(con) and changes:
        sc = cols(con, "scholar_translations")
        if {"passage_id", "src_hash"} <= sc:
            by = {c["id"]: c for c in changes}
            for sid, pid, h in con.execute("SELECT id, passage_id, src_hash FROM scholar_translations WHERE doc_code = ?",
                                           (doc,)):
                c = by.get(pid)
                if c and h == src_hash(c["text_old"]):
                    sch.append({"id": sid, "passage_id": pid, "hash_old": h, "hash_new": src_hash(c["text_new"])})
    return {"doc": doc, "passages": len(rows), "verses": len(verses), "changes": changes, "marks": marks,
            "verses_with_marks": with_marks, "share": share, "scholar": sch, "left": left, "svara": svara}


def prepare(p: dict) -> None:
    """The mended IAST of each change, before anything is written (it goes into the manifest)."""
    for c in p["changes"]:
        c["iast_new"] = to_iast(c["text_new"], c["iast_old"]) if c.get("iast_old") is not None else None


def apply_plan(con, p: dict) -> None:
    has_fts = "passages_fts" in tables(con)
    pc = cols(con, "passages")
    for c in p["changes"]:
        iast = c.get("iast_new")
        sets = ["text = ?"] + (["iast = ?"] if "iast" in pc else [])
        vals = [c["text_new"]] + ([iast] if "iast" in pc else [])
        con.execute("UPDATE passages SET %s WHERE id = ?" % ", ".join(sets), vals + [c["id"]])
        if has_fts:
            con.execute("DELETE FROM passages_fts WHERE rowid = ?", (c["id"],))
            con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES (?, ?, ?, ?)",
                        (c["id"], c["text_new"] or "", iast or "", c["english"]))
    for s in p["scholar"]:
        con.execute("UPDATE scholar_translations SET src_hash = ? WHERE id = ? AND src_hash = ?",
                    (s["hash_new"], s["id"], s["hash_old"]))


def undo(con, man: dict) -> tuple:
    has_fts = "passages_fts" in tables(con)
    pc = cols(con, "passages")
    put, skipped = 0, 0
    for c in man.get("changes") or []:
        r = con.execute("SELECT text, coalesce(translation, '') FROM passages WHERE id = ?", (c["id"],)).fetchone()
        if not r or r[0] != c["text_new"]:
            skipped += 1   # changed since: left as it is
            continue
        sets = ["text = ?"] + (["iast = ?"] if "iast" in pc else [])
        vals = [c["text_old"]] + ([c.get("iast_old")] if "iast" in pc else [])
        con.execute("UPDATE passages SET %s WHERE id = ?" % ", ".join(sets), vals + [c["id"]])
        if has_fts:
            con.execute("DELETE FROM passages_fts WHERE rowid = ?", (c["id"],))
            con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES (?, ?, ?, ?)",
                        (c["id"], c["text_old"] or "", c.get("iast_old") or "", r[1]))
        put += 1
    for s in man.get("scholar") or []:
        con.execute("UPDATE scholar_translations SET src_hash = ? WHERE id = ? AND src_hash = ?",
                    (s["hash_old"], s["id"], s["hash_new"]))
    return put, skipped


def backup(a, doc: str) -> str:
    """A consistent copy of the database before anything is written (db_backup.py); '' when it failed."""
    if a.no_backup:
        return "(no backup: --no-backup)"
    d = Path(a.backup_dir)
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ""
    dst = d / ("context_pre_mendmarks_%s_%s.db" % (re.sub(r"[^A-Za-z0-9_.-]", "_", doc or "undo"), stamp()))
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "db_backup.py"), str(a.db), str(dst)])
    return str(dst) if r.returncode == 0 and dst.exists() else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the edition's note numbers out of the Sanskrit (%s)" % MARK)
    ap.add_argument("--db", default=str(ROOT / "data" / "context.db"))
    ap.add_argument("--doc", help="the text to mend (one)")
    ap.add_argument("--undo", metavar="MANIFEST", help="put back what this manifest says")
    ap.add_argument("--apply", action="store_true", help="write (else a dry run)")
    ap.add_argument("--force", action="store_true", help="mend a text where fewer than 5 in 100 verses carry a number")
    ap.add_argument("--show", type=int, default=5, help="examples shown in a dry run")
    ap.add_argument("--out", default=str(ROOT / "data"), help="where the manifest is written")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups",
                    help="where --apply's backup of the database goes")
    ap.add_argument("--no-backup", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not a.doc and not a.undo:
        print("REFUSE: name the text: --doc CODE (or --undo MANIFEST)."); return 2
    if not Path(a.db).exists():
        print("FAIL: no database at %s" % a.db); return 2
    if a.undo:
        man = json.loads(Path(a.undo).read_text(encoding="utf-8"))
        if man.get("mark") != MARK:
            print("REFUSE: %s is not a manifest of this tool." % a.undo); return 2
        if not a.apply:
            print("VERDICT: the undo would put back %d passage(s) and %d scholarly hash(es) of %s (dry run)"
                  % (len(man.get("changes") or []), len(man.get("scholar") or []), man.get("doc")))
            print("NEXT: the same with --apply"); return 0
        bk = backup(a, str(man.get("doc") or ""))
        if not bk:
            print("FAIL: the backup of the database failed; nothing written"); return 1
        print("backup: %s" % bk)
        con = sqlite3.connect(a.db, timeout=30)
        try:
            with con:
                put, skipped = undo(con, man)
        finally:
            con.close()
        print("VERDICT: put back %d passage(s) of %s; %d left as they are (changed since)" % (put, man.get("doc"), skipped))
        print("NEXT: python scripts\\mend_marks.py --doc %s   (the dry run, again)" % man.get("doc")); return 0
    uri = Path(a.db).resolve().as_uri() + ("" if a.apply else "?mode=ro")
    con = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        p = plan(con, a.doc)
        if p.get("error"):
            print("REFUSE: " + p["error"]); return 2
        print("%s  %s: %d passage(s), %d verse(s) read by vision; %d note number(s) in %d passage(s); %d of those "
              "verses (%.1f%%); %d scholarly row(s) carried; %d passage(s) with digits left (not read by vision)"
              % (MARK, a.doc, p["passages"], p["verses"], p["marks"], len(p["changes"]), p["verses_with_marks"],
                 100.0 * p["share"], len(p["scholar"]), p["left"]))
        for c in p["changes"][:max(0, a.show)]:
            m = MARKS.search(c["text_old"] or "")
            k = m.start() if m else 0
            print("  p%d.%d  ...%s...  ->  ...%s..." % (c["page"], c["idx"], (c["text_old"] or "")[max(0, k - 24):k + 12],
                                                       (c["text_new"] or "")[max(0, k - 24):k + 10]))
        if not p["changes"]:
            print("VERDICT: nothing to mend in %s" % a.doc); print("NEXT: "); return 0
        if p["svara"] and not a.force:
            print("REFUSE: %d passage(s) carry a number after nearly every syllable: a svara notation (the Sama Veda's "
                  "1 2 3), not an edition's notes. --force only after looking." % p["svara"])
            return 1
        if p["share"] < MIN_SHARE and not a.force:
            print("REFUSE: only %.1f%% of its verses read by vision carry such a number: too few to be an edition's "
                  "notes (look at them first). --force to mend it all the same." % (100.0 * p["share"]))
            return 1
        if not a.apply:
            print("VERDICT: a dry run; nothing written")
            print("NEXT: python scripts\\mend_marks.py --doc %s --apply   (it backs the database up first)" % a.doc)
            return 0
        bk = backup(a, a.doc)
        if not bk:
            print("FAIL: the backup of the database failed; nothing written"); return 1
        print("backup: %s" % bk)
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        man_path = out / ("mend_marks_%s_%s.json" % (a.doc, stamp()))
        prepare(p)
        man = {"mark": MARK, "doc": a.doc, "at": datetime.datetime.now().isoformat(timespec="seconds"),
               "changes": p["changes"], "scholar": p["scholar"]}
        tmp = man_path.with_name(man_path.name + ".tmp")
        tmp.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, man_path)   # the manifest first: what is written can always be put back
        with con:
            apply_plan(con, p)
    finally:
        con.close()
    print("VERDICT: mended %d passage(s) of %s (%d note numbers out); %d scholarly row(s) carried; the manifest: %s"
          % (len(p["changes"]), a.doc, p["marks"], len(p["scholar"]), man_path))
    print("NEXT: python scripts\\mend_marks.py --doc %s   (it finds nothing now)" % a.doc)
    print("ALSO: to put it back: python scripts\\mend_marks.py --undo %s --apply" % man_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
