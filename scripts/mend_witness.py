#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
mend_witness.py  (2026-10-21)  WITNESS_MEND_2026_10_21

An e-text witness already in the database read again from its own romanized lines with the reading of
ETEXT_ORTHO_2026_10_21 (scripts/etext_witness.py): its passages keep their ids, and a scholarly English made from
the old spelling is kept, as a new version made from the new one.

Found on 21 Oct in the Surya Siddhanta's GRETIL e-text: the visarga written H had become h with a virama in 362 of
its 515 passages (namaH: n-m-h), +a (an a merged into the vowel before it) had stayed "+", the pada labels and sigla
had become Devanagari consonants, and eleven lines of GRETIL's English header ("Header", "Contribution: Michio Yano",
"Source:", ... "Text") stood on page 1 as Sanskrit; the scholarly English had "translated" seven of them.

  the plan (the default; writes nothing): each passage's old reading must be what the old reading of its
            romanized line gives (else it is left alone and named), and the database's text what was ingested
            (else nothing is done); then: respelled (the visarga, the avagraha, the pada labels, the sigla, the
            inputter's note "checked"), header (GRETIL's English header between a line "Header" and a line "Text"
            on page 1: kept in Latin letters as noise, not a verse), or the same.
  the scholarly English: a verse's latest row made from the old reading gets a new version made from the new one,
            with the same English, notes, doubts, scores and review, its reason saying so (as --rejudge does); a
            header line's row is not carried over: the guard (src_hash) takes it off the site and the edition.
  --yes     the dashboard must not be running a writer; a backup (db_backup.py) to --backup-dir; the page files
            data/raw_witness/<witness>/<witness>_NNNN.jsonl rewritten (each kept as .bak_mend_<date>); the same
            ingest as etext_witness.py --ingest (ingest_jsonl_fast.py, which updates by page and index, so the ids
            stay); the ids and texts checked; the new versions in one transaction; a log in --log-dir; a line in
            data/witnesses.jsonl.

  python scripts\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext
  python scripts\\mend_witness.py --doc jyotish_surya_siddhanta__w_etext --yes
  python scripts\\mend_witness.py --doc markandeya_purana__w_gretil

The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's.
"""
from __future__ import annotations
import argparse, datetime, json, os, re, shutil, sqlite3, sys
from pathlib import Path

MARK = "WITNESS_MEND_2026_10_21"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import etext_witness as EW        # noqa: E402  (to_deva, gretil_header, read_text, witnesses, the marks)
import repair_text as rt          # noqa: E402  (run, writers_running, PY, SCRIPTS)
import scholar_translate as ST    # noqa: E402  (src_hash, COLS, latest_rows, has_table)
from normalize_text import normalize_sanskrit   # noqa: E402  (as ingest_jsonl_fast.py stores a text)

REVIEW_COLS = ("reviewed_by", "reviewed_at", "review_verdict", "review_note")


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def say(verdict: str, nxt: str = "", also=()):
    print("VERDICT: " + verdict)
    print("NEXT: " + nxt)
    for x in also:
        print("ALSO: " + x)


def connect_ro(db: str, immutable: bool = False):
    q = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return sqlite3.connect(Path(db).resolve().as_uri() + q, uri=True, timeout=30)


def page_files(out_dir, wcode: str) -> list:
    """[(page, path)] of a witness's page files, in order."""
    rx = re.compile(r"^%s_(\d{4})\.jsonl$" % re.escape(wcode))
    d = Path(out_dir) / wcode
    if not d.is_dir():
        return []
    return sorted((int(rx.match(p.name).group(1)), p) for p in d.glob("%s_*.jsonl" % wcode) if rx.match(p.name))


def read_records(path: Path) -> list:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def convert(roman: str, scheme: str, ortho: bool) -> str:
    """A record's Devanagari from its romanized lines, as etext_witness.parse() joins them."""
    return "\n".join(x for x in (EW.to_deva(y, scheme, ortho=ortho).strip() for y in roman.split("\n")) if x).strip()


def what_changed(roman: str) -> list:
    w = []
    if EW.G_VISARGA.search(roman):
        w.append("the visarga")
    if "+a" in roman:
        w.append("the avagraha")
    if EW.G_LABEL.search(roman):
        w.append("the pada labels")
    if EW.G_SIGLUM.search(roman):
        w.append("the sigla")
    if EW.G_NOTE.search(roman):
        w.append("a note")
    return w


def source_is_gretil(meta: dict) -> bool:
    """The witness's source file has GRETIL's TEI header (a line "Header" to a line "Text" naming GRETIL)."""
    f = str(meta.get("file") or "")
    if not f:
        return False
    p = Path(f.replace("\\", os.sep))
    if not p.is_absolute():
        p = ROOT / p
    try:
        text, _info = EW.read_text(p)
    except OSError:
        return False
    return bool(EW.gretil_header(text.replace("\r\n", "\n").split("\n")))


def header_zone(recs: list) -> set:
    """The indexes (from 0) of page 1's records from one whose line is "Header" to one whose line is "Text"."""
    first = None
    for k, r in enumerate(recs):
        t = str((r.get("meta") or {}).get("roman_source") or "").strip()
        if first is None and t == "Header":
            first = k
        elif first is not None and t == "Text":
            return set(range(first, k + 1))
    return set()


def plan(a) -> dict:
    """What the mend would do; writes nothing. {"refuse": str} when it cannot be done."""
    wcode = a.doc
    meta = None
    try:
        meta = json.loads((Path(a.out_dir) / wcode / "witness.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"refuse": "%s has no witness.json in %s" % (wcode, a.out_dir)}
    scheme = meta.get("scheme") or ""
    if meta.get("mode") == "pages" or scheme in ("", "devanagari", "unknown"):
        return {"refuse": "%s was not read from a romanized text (%s, %s): nothing to read again"
                          % (wcode, meta.get("mode"), scheme or "no scheme")}
    files = page_files(a.out_dir, wcode)
    if not files:
        return {"refuse": "%s holds no page files" % (Path(a.out_dir) / wcode)}
    gretil = source_is_gretil(meta) or str(meta.get("site") or "") == "gretil"
    con = connect_ro(a.db, a.immutable)
    try:
        rows = con.execute("SELECT p.id, p.page_no, p.idx, p.text, p.text_type FROM passages p JOIN docs d ON "
                           "d.id = p.doc_id WHERE d.code = ? ORDER BY p.page_no, p.idx", (wcode,)).fetchall()
        latest = ST.latest_rows(con, wcode) if ST.has_table(con, "scholar_translations") else {}
    finally:
        con.close()
    if not rows:
        return {"refuse": "%s is not in the database: ingest it first (etext_witness.py --ingest)" % wcode}
    db = {(r[1], r[2]): r for r in rows}
    items, pages, mismatch = [], {}, []
    for page, path in files:
        recs = read_records(path)
        zone = header_zone(recs) if (page == 1 and gretil) else set()
        out = []
        for k, rec in enumerate(recs):
            row = db.get((page, k + 1))
            roman = str((rec.get("meta") or {}).get("roman_source") or "")
            old = rec.get("text") or ""
            it = {"page": page, "idx": k + 1, "old": old, "type_old": rec.get("text_type"), "roman": roman,
                  "pid": row[0] if row else None, "what": []}
            if row is None or row[3] != normalize_sanskrit(old.strip()):
                mismatch.append("%d.%d" % (page, k + 1))
            head = k in zone
            target = (roman.strip() if head else convert(roman, scheme, True)) if roman else old.strip()
            target_type = "noise" if head else it["type_old"]
            if not roman or (old.strip() == target and it["type_old"] == target_type):
                it.update(kind="same", new=old, type_new=it["type_old"])   # as the e-text means it (mended already)
            elif convert(roman, scheme, False) != old.strip():
                it.update(kind="unreproducible", new=old, type_new=it["type_old"])
            elif head:
                it.update(kind="header", new=target, type_new="noise", what=["GRETIL's English header"])
            else:
                it.update(kind="respelled", new=target, type_new=it["type_old"], what=what_changed(roman))
            r0 = latest.get(it["pid"]) if it["pid"] else None
            it["scholar"] = None
            if r0 is not None and it["kind"] in ("respelled", "header"):
                if r0.get("src_hash") != ST.src_hash(row[3]):
                    it["scholar"] = "stale already"
                else:
                    it["scholar"] = "rebase" if it["kind"] == "respelled" else "dropped"
                it["row"] = r0
            out.append(it)
            items.append(it)
        pages[page] = (path, recs, out)
    if len(rows) != len(items):
        mismatch.append("the database holds %d passages, the page files %d" % (len(rows), len(items)))
    if mismatch:
        return {"refuse": "the database's text is not what was ingested from the page files (%d place(s), e.g. %s): "
                          "nothing is done" % (len(mismatch), ", ".join(mismatch[:5]))}
    return {"wcode": wcode, "meta": meta, "scheme": scheme, "items": items, "pages": pages, "gretil": gretil}


def counts(items: list) -> dict:
    c = {}
    for it in items:
        c[it["kind"]] = c.get(it["kind"], 0) + 1
        if it.get("scholar"):
            c["scholar " + it["scholar"]] = c.get("scholar " + it["scholar"], 0) + 1
    return c


def show(p: dict, limit: int = 3):
    items = p["items"]
    c = counts(items)
    print("mend_witness %s  %s (%s); the e-text %s" % (MARK, p["wcode"], p["scheme"], "GRETIL's" if p["gretil"] else "not GRETIL's"))
    print("  passages: %d; respelled %d; header %d; the same %d; left alone (the old reading does not give it) %d"
          % (len(items), c.get("respelled", 0), c.get("header", 0), c.get("same", 0), c.get("unreproducible", 0)))
    print("  scholarly English: %d re-based (the same English, a new version from the new spelling); %d dropped "
          "(a header line, not a verse); %d stale already (left as they are)"
          % (c.get("scholar rebase", 0), c.get("scholar dropped", 0), c.get("scholar stale already", 0)))
    seen = {}
    for it in items:
        k = it["kind"]
        if k in ("respelled", "header", "unreproducible") and seen.get(k, 0) < limit:
            seen[k] = seen.get(k, 0) + 1
            print("  %s %d.%d (%s)%s" % (k, it["page"], it["idx"], ", ".join(it["what"]) or "-",
                                         ", its scholarly English " + it["scholar"] if it.get("scholar") else ""))
            print("      was: %s" % it["old"][:150].replace("\n", " / "))
            print("      now: %s" % it["new"][:150].replace("\n", " / "))
    return c


def rebase_rec(r0: dict, new_text: str, what: list, at: str, have: set) -> dict:
    rec = {c: r0.get(c) for c in ST.COLS}
    for c in REVIEW_COLS:
        if c in have:
            rec[c] = r0.get(c)
    rec.update(src_hash=ST.src_hash(new_text), cost_usd=0.0, created_at=at,
               judge_reason="[re-based %s by %s: the e-text's spelling mended (%s); the English, notes, scores and "
                            "review unchanged] %s" % (at[:10], MARK, ", ".join(what) or "its reading", r0.get("judge_reason") or ""))
    return rec


def apply(a, p: dict) -> int:
    wcode, items = p["wcode"], p["items"]
    todo = [it for it in items if it["kind"] in ("respelled", "header")]
    if not todo:
        say("nothing to mend in %s: every passage reads as the e-text means it" % wcode, "")
        return 0
    if not os.environ.get("SA_MEND_NO_DASHBOARD"):
        w = rt.writers_running(False, wcode)
        if w:
            say("not now: the dashboard runs a database writer (%s)" % ", ".join("%s %s" % (j.get("kind"), j.get("doc")) for j in w),
                "python scripts\\mend_witness.py --doc %s --yes" % wcode)
            return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(a.backup_dir) / ("context_pre_mend_%s_%s.db" % (wcode, stamp))
    backup.parent.mkdir(parents=True, exist_ok=True)
    if rt.run([rt.PY, rt.SCRIPTS / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        say("the backup failed; nothing was changed", "")
        return 1
    day = stamp[:8]
    for page, (path, recs, out) in sorted(p["pages"].items()):
        if not any(it["kind"] in ("respelled", "header") for it in out):
            continue
        bak = path.with_name(path.name + ".bak_mend_%s" % day)
        if not bak.exists():
            shutil.copy2(path, bak)
        lines = []
        for rec, it in zip(recs, out):
            if it["kind"] in ("respelled", "header"):
                rec = dict(rec)
                rec["text"] = it["new"]
                rec["text_type"] = it["type_new"]
                rec["meta"] = dict(rec.get("meta") or {}, mend=MARK)
            lines.append(json.dumps(rec, ensure_ascii=False))
        tmp = path.with_name(path.name + ".tmp_mend")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    out_dir = Path(a.out_dir) / wcode
    argv = [rt.PY, rt.SCRIPTS / "ingest_jsonl_fast.py", "--doc", wcode, "--glob", str(out_dir / ("%s_*.jsonl" % wcode)),
            "--db", a.db, "--source", "given", "--no-segment"]
    if p["meta"].get("category"):
        argv += ["--category", str(p["meta"]["category"])]
    if rt.run(argv) != 0:
        say("the ingest failed; the page files are rewritten (their .bak_mend_%s copies beside them) and the backup "
            "made before is %s" % (day, backup), "")
        return 1
    con = sqlite3.connect(a.db, timeout=60)
    try:
        now_rows = {r[0]: r for r in con.execute(
            "SELECT p.id, p.page_no, p.idx, p.text, p.text_type FROM passages p JOIN docs d ON d.id = p.doc_id "
            "WHERE d.code = ?", (wcode,))}
        bad = [it for it in items if it["pid"] not in now_rows or (now_rows[it["pid"]][1], now_rows[it["pid"]][2]) !=
               (it["page"], it["idx"]) or now_rows[it["pid"]][3] != normalize_sanskrit(it["new"].strip())]
        if bad or len(now_rows) != len(items):
            say("the ingest did not give the texts expected (%d place(s), e.g. %d.%d); no scholarly English was changed; "
                "the backup made before is %s" % (len(bad), bad[0]["page"] if bad else 0, bad[0]["idx"] if bad else 0,
                                                    backup), "")
            return 1
        have = {r[1] for r in con.execute("PRAGMA table_info(scholar_translations)")} if ST.has_table(con, "scholar_translations") else set()
        at = now()
        n = 0
        cols = list(ST.COLS) + [c for c in REVIEW_COLS if c in have]
        with con:
            for it in items:
                if it.get("scholar") != "rebase":
                    continue
                rec = rebase_rec(it["row"], now_rows[it["pid"]][3], it["what"], at, have)
                rec["version"] = (con.execute("SELECT MAX(version) FROM scholar_translations WHERE passage_id = ?",
                                              (it["pid"],)).fetchone()[0] or 0) + 1
                con.execute("INSERT INTO scholar_translations(%s) VALUES (%s)" % (", ".join(cols), ",".join("?" * len(cols))),
                            [rec.get(c) for c in cols])
                n += 1
    finally:
        con.close()
    logd = Path(a.log_dir)
    logd.mkdir(parents=True, exist_ok=True)
    logp = logd / ("%s_%s.jsonl" % (wcode, stamp))
    with open(logp, "w", encoding="utf-8") as f:
        for it in todo:
            f.write(json.dumps({"passage_id": it["pid"], "page": it["page"], "idx": it["idx"], "kind": it["kind"],
                                "what": it["what"], "old": it["old"], "new": it["new"], "type_old": it["type_old"],
                                "type_new": it["type_new"], "scholar": it.get("scholar"), "mark": MARK},
                               ensure_ascii=False) + "\n")
    c = counts(items)
    EW._append(Path(a.witnesses), {"doc": p["meta"].get("doc"), "witness": wcode, "mended": len(todo),
                                   "rebased": n, "dropped": c.get("scholar dropped", 0), "backup": str(backup),
                                   "log": str(logp), "at": now(), "mark": MARK})
    state = (rt.verdicts(Path(a.verdicts)).get(wcode) or {}).get("status")
    nxt = ("the scheduled mirror sends the mended text on its next run (python scripts\\corpus_sync.py shows the plan)"
           if state == "released" else
           "python scripts\\repair_text.py --doc %s --release --force   (then the mirror sends it on its next run)" % wcode)
    say("%s mended: %d passages respelled, %d header line(s) kept in Latin letters as noise; %d scholarly English "
        "re-based (the same English), %d dropped (header lines); the ids unchanged; backup %s; log %s"
        % (wcode, c.get("respelled", 0), c.get("header", 0), n, c.get("scholar dropped", 0), backup, logp), nxt,
        ["python scripts\\scholar_translate.py --doc %s --pages 1-99 --limit 600   (what is left to translate, "
         "free)" % wcode])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read an e-text witness again from its romanized lines (%s)" % MARK)
    ap.add_argument("--doc", required=True, help="the witness's code, <doc>__w_<site>")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--out-dir", default="data/raw_witness")
    ap.add_argument("--witnesses", default="data/witnesses.jsonl")
    ap.add_argument("--log-dir", default="data/witness_mend")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl", help="the register: is the witness released?")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--immutable", action="store_true", help="the plan only, on a backup copy (read as immutable)")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    try:   # a console that cannot show Devanagari gets \\u escapes, not an error
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    os.chdir(ROOT)
    if not re.match(r"^[A-Za-z0-9_\-]+__w_[A-Za-z0-9_\-]+$", a.doc):
        say("--doc names a witness, <doc>__w_<site>: %s is not one" % a.doc, "python scripts\\etext_witness.py --list")
        return 2
    if a.yes and a.immutable:
        say("--immutable is for the plan on a backup copy; --yes writes the database itself", "")
        return 2
    if not Path(a.db).exists():
        say("%s not found" % a.db, "")
        return 1
    p = plan(a)
    if p.get("refuse"):
        print("REFUSE: " + p["refuse"])
        say("nothing done", "")
        return 1
    c = show(p)
    if not a.yes:
        n = c.get("respelled", 0) + c.get("header", 0)
        if not n:
            say("nothing to mend in %s: every passage reads as the e-text means it" % a.doc, "")
            return 0
        say("%d passage(s) of %s to mend (%d respelled, %d header); %d scholarly English to re-base, %d to drop; "
            "nothing written" % (n, a.doc, c.get("respelled", 0), c.get("header", 0), c.get("scholar rebase", 0),
                                 c.get("scholar dropped", 0)),
            "python scripts\\mend_witness.py --doc %s --yes   (a backup first)" % a.doc)
        return 0
    return apply(a, p)


if __name__ == "__main__":
    sys.exit(main())
