#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
classify_hindi.py  (2026-10-16)  CLASSIFY_HINDI_2026_10_16

An edition's own Hindi (the editor's translation under each verse, his commentary, his preface) is tagged text_type
'frontmatter', the label classify_doc.py gives "genuine English/Hindi body text and front matter". The translators,
the scholarly English, the QA, the exports, the embeddings, the Library and the site's reader all leave that label
out, so the English and the Hindi are made from the Sanskrit only.

Why it is needed: classify_doc.py, the stage the dashboard runs after every ingest, promised it, but its
classify_frontmatter.py recognises English only (Latin letters). Devanagari Hindi stayed 'mula' and was translated.
On the 15 Oct backup, of the Karanagama's passages that read as Hindi (scripts/edition_hindi.py), 194 carried working
English made from the Hindi, and 99 scholarly English.

What it does:
  - by default (the stage; safe): a passage that reads as Hindi and carries no English is tagged 'frontmatter';
  - --with-english: a passage that carries English is tagged too. That English was made from the Hindi, so it is
    archived (translation_history, reason "edition-hindi CLASSIFY_HINDI_2026_10_16") and cleared; its search row
    (passages_fts) is made again without it, and its vector (passage_embeddings) is removed;
  - --reject-scholarly (with --by): the latest scholarly row of each such passage gets a person's verdict 'reject',
    with the note "the passage is the edition's own Hindi, not Sanskrit";
  - translations_l10n is never touched: its rows on such passages are counted and reported;
  - --undo: puts back the logged types and English (build_embeddings.py makes the vector again) and clears the
    verdicts it set.
Every change is logged (data/classify_hindi_log.jsonl). A dry run by default. It writes through db_utils.connect;
run it with the dashboard idle.

  python scripts\\classify_hindi.py                                    every text (a dry run)
  python scripts\\classify_hindi.py --doc AkashBhairavaKalpam --show 5
  python scripts\\classify_hindi.py --doc AkashBhairavaKalpam --apply
  python scripts\\classify_hindi.py --doc AkashBhairavaKalpam --undo --apply
"""
from __future__ import annotations
import argparse, datetime, json, os, sqlite3, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MARK = "CLASSIFY_HINDI_2026_10_16"
NEW_TYPE = "frontmatter"
REASON = "edition-hindi " + MARK
NOTE = "the passage is the edition's own Hindi, not Sanskrit (%s)" % MARK
META = ("translation", "engine", "mt_prompt_version", "translation_score", "translation_qa", "translated_at")


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def tables(con) -> set:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}


def cols(con, t: str) -> set:
    return {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}


def candidates(con, doc=None) -> list:
    """[{id, doc, page, idx, type, text, iast, english, why}] of the passages that read as Hindi, not typed noise or
    frontmatter, of texts not retired; in the texts' order."""
    import edition_hindi as EH
    pc = cols(con, "passages")
    ia = "p.iast" if "iast" in pc else "NULL"
    q = ("SELECT p.id, d.code, p.page_no, p.idx, COALESCE(p.text_type, 'mula'), p.text, %s, COALESCE(p.translation, '') "
         "FROM passages p JOIN docs d ON d.id = p.doc_id WHERE COALESCE(p.text_type, 'mula') NOT IN ('noise', "
         "'frontmatter') AND d.code NOT LIKE '%%-RETIRED'" % ia)
    args = []
    if doc:
        q += " AND d.code = ?"
        args.append(doc)
    out = []
    for pid, code, page, idx, tt, text, iast, en in con.execute(q + " ORDER BY d.code, p.page_no, p.idx", args):
        ok, why = EH.hindi_of(text)
        if ok:
            out.append({"id": pid, "doc": code, "page": page, "idx": idx, "type": tt, "text": text or "",
                        "iast": iast or "", "english": (en or "").strip(), "why": why})
    return out


def counts_on(con, ids: list) -> dict:
    """{passage_id: {l10n, scholar, vectors}} for those passages (0 where a table is missing)."""
    t = tables(con)
    out = {i: {"l10n": 0, "scholar": None, "vectors": 0} for i in ids}
    for k in range(0, len(ids), 500):
        part = ids[k:k + 500]
        qs = ",".join("?" * len(part))
        if "translations_l10n" in t:
            for pid, n in con.execute("SELECT passage_id, COUNT(*) FROM translations_l10n WHERE passage_id IN (%s) AND "
                                      "TRIM(COALESCE(translation, '')) <> '' GROUP BY passage_id" % qs, part):
                out[pid]["l10n"] = n
        if "scholar_translations" in t:
            for pid, sid in con.execute("SELECT passage_id, MAX(id) FROM scholar_translations WHERE passage_id IN (%s) "
                                        "GROUP BY passage_id" % qs, part):
                out[pid]["scholar"] = sid
        if "passage_embeddings" in t:
            for pid, n in con.execute("SELECT passage_id, COUNT(*) FROM passage_embeddings WHERE passage_id IN (%s) "
                                      "GROUP BY passage_id" % qs, part):
                out[pid]["vectors"] = n
    return out


def logged(log: Path, doc=None) -> dict:
    """{passage_id: its last logged record} (of doc, when named)."""
    out = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("passage_id") is not None and (doc is None or d.get("doc") == doc):
                out[d["passage_id"]] = d
    return out


def fts_row(con, pid: int, text: str, iast: str, english: str) -> None:
    if "passages_fts" not in tables(con):
        return
    con.execute("DELETE FROM passages_fts WHERE rowid = ?", (pid,))
    con.execute("INSERT INTO passages_fts(rowid, text, iast, translation) VALUES (?, ?, ?, ?)",
                (pid, text or "", iast or "", english or ""))


def tag(con, c: dict, info: dict, a, f, by: str) -> dict:
    """Tag one passage (and, with --with-english, clear its English); log it to f; the counts it changed."""
    got = {"tagged": 1, "cleared": 0, "vectors": 0, "rejected": 0}
    rec = {"at": now(), "doc": c["doc"], "passage_id": c["id"], "page": c["page"], "idx": c["idx"], "old": c["type"],
           "new": NEW_TYPE, "why": c["why"], "by": by, "mark": MARK, "action": "tag", "english": None,
           "scholar_row": None, "prev_review": None, "vectors_removed": 0}
    con.execute("UPDATE passages SET text_type = ? WHERE id = ?", (NEW_TYPE, c["id"]))
    if c["english"]:
        row = con.execute("SELECT %s FROM passages WHERE id = ?" % ", ".join(META), (c["id"],)).fetchone()
        rec["english"] = dict(zip(META, row))
        hc = cols(con, "translation_history") if "translation_history" in tables(con) else set()
        if hc:
            names = ["passage_id"] + list(META) + ["reason"] + (["lang"] if "lang" in hc else [])
            vals = [c["id"]] + list(row) + [REASON] + (["en"] if "lang" in hc else [])
            con.execute("INSERT INTO translation_history(%s) VALUES (%s)" % (", ".join(names), ",".join("?" * len(names))),
                        vals)
        con.execute("UPDATE passages SET translation = '', translation_score = NULL, translation_qa = NULL, "
                    "mt_prompt_version = NULL, translated_at = NULL WHERE id = ?", (c["id"],))
        fts_row(con, c["id"], c["text"], c["iast"], "")
        if info.get("vectors"):
            got["vectors"] = con.execute("DELETE FROM passage_embeddings WHERE passage_id = ?", (c["id"],)).rowcount
            rec["vectors_removed"] = got["vectors"]
        got["cleared"] = 1
    if a.reject_scholarly and info.get("scholar"):
        prev = con.execute("SELECT reviewed_by, reviewed_at, review_verdict, review_note FROM scholar_translations "
                           "WHERE id = ?", (info["scholar"],)).fetchone()
        rec["scholar_row"] = info["scholar"]
        rec["prev_review"] = list(prev) if prev else None
        con.execute("UPDATE scholar_translations SET reviewed_by = ?, reviewed_at = ?, review_verdict = 'reject', "
                    "review_note = ? WHERE id = ?", (by, now(), NOTE, info["scholar"]))
        got["rejected"] = 1
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return got


def undo_one(con, d: dict, f, by: str) -> int:
    """Put back one logged tag (when the passage still carries it); 1 when it did."""
    row = con.execute("SELECT COALESCE(text_type, 'mula'), COALESCE(translation, ''), text, "
                      + ("iast" if "iast" in cols(con, "passages") else "NULL") + " FROM passages WHERE id = ?",
                      (d["passage_id"],)).fetchone()
    if not row or row[0] != d.get("new"):
        return 0
    con.execute("UPDATE passages SET text_type = ? WHERE id = ?", (d.get("old") or None, d["passage_id"]))
    en = d.get("english")
    if isinstance(en, dict) and not row[1].strip():
        con.execute("UPDATE passages SET %s WHERE id = ?" % ", ".join("%s = ?" % k for k in META),
                    [en.get(k) for k in META] + [d["passage_id"]])
        fts_row(con, d["passage_id"], row[2], row[3], en.get("translation") or "")
    if d.get("scholar_row"):
        cur = con.execute("SELECT review_note FROM scholar_translations WHERE id = ?", (d["scholar_row"],)).fetchone()
        if cur and cur[0] == NOTE:
            p = d.get("prev_review") or [None, None, None, None]
            con.execute("UPDATE scholar_translations SET reviewed_by = ?, reviewed_at = ?, review_verdict = ?, "
                        "review_note = ? WHERE id = ?", (p[0], p[1], p[2], p[3], d["scholar_row"]))
    f.write(json.dumps({"at": now(), "doc": d.get("doc"), "passage_id": d["passage_id"], "page": d.get("page"),
                        "idx": d.get("idx"), "old": d.get("new"), "new": d.get("old"), "by": by, "mark": MARK,
                        "action": "undo"}, ensure_ascii=False) + "\n")
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="An edition's own Hindi tagged frontmatter (a dry run unless --apply)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="one text (default: every text)")
    ap.add_argument("--with-english", action="store_true", help="tag those that carry English too; archive and clear it")
    ap.add_argument("--reject-scholarly", action="store_true", help="a person's 'reject' on their scholarly rows (--by)")
    ap.add_argument("--undo", action="store_true", help="put back what the log says this tool changed")
    ap.add_argument("--show", type=int, default=3, help="passages shown a text (dry run)")
    ap.add_argument("--log", default="data/classify_hindi_log.jsonl")
    ap.add_argument("--by", default=None)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except Exception:
        pass
    if not Path(a.db).exists():
        print("REFUSE: %s not found (run from the repo root)" % a.db); print("VERDICT: nothing written"); print("NEXT: ")
        return 2
    if a.reject_scholarly and not (a.by or "").strip():
        print("REFUSE: --reject-scholarly is a person's verdict: --by is needed"); print("VERDICT: nothing written")
        print("NEXT: "); return 1
    by = a.by or "classify_hindi.py"
    log = Path(a.log)
    import db_utils
    con = (db_utils.connect(a.db) if a.apply else
           sqlite3.connect(Path(a.db).resolve().as_uri() + "?mode=ro", uri=True))
    try:
        mode = "APPLY" if a.apply else "DRY RUN (nothing written)"
        if a.undo:
            recs = [d for d in logged(log, a.doc).values() if d.get("action") == "tag"]
            print("classify_hindi.py  %s  UNDO  %s  %s: %d logged tag(s)" % (MARK, mode, a.doc or "every text", len(recs)))
            if not a.apply:
                live = 0
                for d in recs:
                    r = con.execute("SELECT COALESCE(text_type, 'mula') FROM passages WHERE id = ?",
                                    (d["passage_id"],)).fetchone()
                    live += 1 if r and r[0] == d.get("new") else 0
                print("VERDICT: %d passage(s) would be put back; nothing written" % live)
                print("NEXT: the same command with --apply"); return 0
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                n = sum(undo_one(con, d, f, by) for d in recs)
            con.commit()
            print("VERDICT: %d passage(s) put back; the log: %s" % (n, log))
            print("NEXT: python scripts\\build_embeddings.py%s   (the vectors of the English put back)"
                  % ((" --doc %s" % a.doc) if a.doc else ""))
            return 0
        cands = candidates(con, a.doc)
        info = counts_on(con, [c["id"] for c in cands])
        by_doc = {}
        for c in cands:
            by_doc.setdefault(c["doc"], []).append(c)
        print("classify_hindi.py  %s  %s  %s%s%s" % (MARK, mode, a.doc or "every text",
                                                   "  --with-english" if a.with_english else "",
                                                   "  --reject-scholarly" if a.reject_scholarly else ""))
        todo = []
        for doc, cs in by_doc.items():
            en = sum(1 for c in cs if c["english"])
            sc = sum(1 for c in cs if info[c["id"]]["scholar"])
            hi = sum(1 for c in cs if info[c["id"]]["l10n"])
            vec = sum(info[c["id"]]["vectors"] for c in cs if c["english"])
            take = [c for c in cs if a.with_english or not c["english"]]
            todo.extend(take)
            print("  %s: %d passage(s) read as Hindi; %d carry English%s; %d scholarly English; %d a Hindi translation "
                  "(translations_l10n: not touched); %d to tag" % (doc, len(cs), en, (" (made from the Hindi; %d vector(s))"
                                                                                % vec) if en else "", sc, hi, len(take)))
            for c in cs[:max(0, a.show)]:
                print("      p%s.%s  %s%s   %s" % (c["page"], c["idx"], c["type"], "  [English]" if c["english"] else "",
                                                 c["text"].replace("\n", " / ")[:70]))
        left = len(cands) - len(todo)
        if not todo:
            print("VERDICT: nothing to tag%s" % (" (%d carry English: --with-english)" % left if left else ""))
            print("NEXT: "); return 0
        if not a.apply:
            print("VERDICT: %d passage(s) would be tagged %s%s; nothing written"
                  % (len(todo), NEW_TYPE, (", %d left (they carry English: --with-english)" % left) if left else ""))
            print("NEXT: the same command with --apply")
            return 0
        tot = {"tagged": 0, "cleared": 0, "vectors": 0, "rejected": 0}
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            for c in todo:
                for k, v in tag(con, c, info[c["id"]], a, f, by).items():
                    tot[k] += v
        con.commit()
    finally:
        con.close()
    print("VERDICT: %d tagged %s; %d English archived and cleared (%d vector(s) removed); %d scholarly row(s) rejected%s;"
          " the log: %s" % (tot["tagged"], NEW_TYPE, tot["cleared"], tot["vectors"], tot["rejected"],
                            (", %d left (they carry English)" % left) if left else "", log))
    print("NEXT: the Library and the reader count verses only; the site after the next mirror run; --undo --apply puts "
          "it back")
    return 0


if __name__ == "__main__":
    sys.exit(main())
