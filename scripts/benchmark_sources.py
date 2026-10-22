#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
benchmark_sources.py  (2026-10-11)  BENCHMARK_2026_10_11

Benchmarks the readings of one text against each other, against what archive.org already had, and against
a critical e-text where there is one, and says where the automaton improved the text and its translation,
and where it did not. Free and read-only: it reads page files, the database read-only, the oldest repair
backup (read-only, immutable), the witnesses and the files fetched into sources\\<doc>\\.

The readings of the scan's pages:
  tesseract      data/raw/<doc>_NNNN.jsonl (the first OCR)
  vision         data/raw_vision/<doc>_NNNN.jsonl
  consensus      data/raw_merged/<doc>_NNNN.jsonl (the repair)
  database       the passages being translated now (noise and front matter left out)
  before repair  the passages in the oldest D:\\backups\\context_pre_repair_<doc>_*.db (what was translated
                 before the repair)
  witnesses      every witness written by etext_witness.py (data/witnesses.jsonl), through its align.json
  e-texts        every text file in sources\\<doc>\\ (an archive.org OCR text, a GRETIL file), aligned here
                 by etext_witness.measure

For each reading, on the same pages:
  the Devanagari letters it holds (how complete it is), the Latin letters in it, the letters misread
  (repair_text.judge: short Latin runs that are not watermarks, notes or numbering) and the pages they
  damage, the level; its agreement with ours (the repair, else the database) and, when a critical e-text
  is among the readings, with it: per page, the share of the e-text's six-letter skeleton n-grams the
  reading has (recall) and the F1, as their medians.
For the translation: the English and Hindi now and before the repair, the heuristic QA, the LLM judge's
fidelity (mt_reviews) where it ran, and the share of the passages translated that carried misread letters:
that is the debris's effect on the translation, measured.

BENCH_LETTERS_2026_10_22: and letter by letter. On a sample of pages (--letters-pages, 80; 40 with --all; 0: none) each
reading is read against ours akshara by akshara (source_fidelity.py: folded alike, aligned, upper bounds), and Tesseract
beside each other OCR reading: where the two agree with each other against ours, ours is most likely misread there
("outvoted"); where one lacks what the other and ours have, it is that one's own misreading. A share of Devanagari, the
Latin misread and the noise see the script; this sees the letters (on 22 Oct archive.org's text of the Satapatha's
scan was 100% Devanagari and misread 25 aksharas in 100).

Writes data\\benchmarks\\<doc>.json (and data\\benchmarks\\_summary.json with --all). Never writes the
database. The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.

  python scripts\\benchmark_sources.py --doc Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi
  python scripts\\benchmark_sources.py --doc X --etext sources\\X\\file_djvu.txt --reference gretil
  python scripts\\benchmark_sources.py --all
"""
from __future__ import annotations
import argparse, datetime, json, os, re, sqlite3, statistics, sys
from pathlib import Path

MARK = "BENCHMARK_2026_10_11"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repair_text as rt        # noqa: E402  (judge, page_rx, verdicts, JUNK, DEV)
import etext_witness as ew      # noqa: E402  (parse, measure, skel, witnesses, site_of)

TEXT_EXT = (".txt", ".htm", ".html", ".xml", ".text")
MATERIAL_TR, MODERATE_TR = 10.0, 3.0     # % of the translated passages that carried misread letters


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def page_files(folder: Path, doc: str) -> dict:
    """{page: text} of one folder of page JSONL (records joined)."""
    out = {}
    if not folder.is_dir():
        return out
    rx = rt.page_rx(doc, "jsonl")
    for e in os.scandir(folder):
        m = rx.match(e.name)
        if not m:
            continue
        parts = []
        try:
            with open(e.path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        try:
                            parts.append(json.loads(line).get("text") or "")
                        except ValueError:
                            continue
        except OSError:
            continue
        t = "\n".join(p for p in parts if p)
        if t.strip():
            out[int(m.group(1))] = t
    return out


def _connect(db: Path, immutable: bool):
    uri = db.resolve().as_uri() + ("?mode=ro&immutable=1" if immutable else "?mode=ro")
    return sqlite3.connect(uri, uri=True, timeout=10)


def db_reading(db: Path, doc: str, immutable: bool = False):
    """({page: text}, facts) of a text in a database, read-only; (None, {}) when it is not there."""
    try:
        con = _connect(db, immutable)
    except sqlite3.Error:
        return None, {}
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row = con.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()
        if not row:
            return None, {}
        did = row[0]
        scope = " AND COALESCE(text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
        qa = "translation_qa" if "translation_qa" in cols else "NULL"
        rows = con.execute("SELECT id, page_no, text, translation, %s FROM passages WHERE doc_id=?%s ORDER BY page_no, idx"
                           % (qa, scope), (did,)).fetchall()
        hi = 0
        if "translations_l10n" in tables:
            try:
                hi = con.execute("SELECT COUNT(*) FROM translations_l10n l JOIN passages p ON p.id=l.passage_id WHERE "
                                 "p.doc_id=? AND l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>''", (did,)).fetchone()[0]
            except sqlite3.Error:
                hi = 0
        rev = None
        if "mt_reviews" in tables:
            try:
                r = con.execute("SELECT COUNT(*), AVG(m.score_fidelity), AVG(m.score_fluency), SUM(CASE WHEN m.score_fidelity "
                                "<= 2 THEN 1 ELSE 0 END) FROM mt_reviews m JOIN passages p "
                                "ON p.id=m.passage_id WHERE p.doc_id=? AND m.lang='en'", (did,)).fetchone()
                if r and r[0]:
                    rev = {"n": int(r[0]), "fidelity": round(float(r[1] or 0), 2), "fluency": round(float(r[2] or 0), 2),
                           "serious": int(r[3] or 0)}   # REINGEST_2026_10_12: fidelity 2 or less, a wrong meaning
            except sqlite3.Error:
                rev = None
    except sqlite3.Error:
        return None, {}
    finally:
        con.close()
    pages, translated = {}, []
    qas = []
    for pid, pg, text, tr, q in rows:
        pages.setdefault(int(pg or 0), []).append(text or "")
        if (tr or "").strip():
            translated.append((int(pg or 0), text or "", "db", True, 1.0))
            if q is not None:
                try:
                    qas.append(float(q))
                except (TypeError, ValueError):
                    pass
    facts = {"passages": len(rows), "english": len(translated), "hindi": int(hi or 0),
             "qa_mean": round(statistics.mean(qas), 3) if qas else None, "reviews": rev}
    if translated:
        j = rt.judge(translated, Path("/nonexistent"), doc, max_pages=0)
        facts["translated_misread_pct"] = j["misread_pct"]          # of the translated passages
        facts["translated_letters_misread_pct"] = j["misread_letters_pct"]
        # QUALITY_2026_10_11: and the passages translated whose Devanagari is noise (10% of their words or more)
        nz = sum(1 for _pg, t, _k, _h, _q in translated if ew.quality([t], plausible=False)["noise_pct"] >= 10.0)
        facts["translated_noise_pct"] = round(100.0 * nz / len(translated), 1)
    return {p: "\n".join(v) for p, v in pages.items()}, facts


def page_engines(folder: Path, doc: str) -> dict:
    """QUALITY_2026_10_11: {engine: pages} of a folder of page JSONL (the repair's: vision, tesseract-fallback, blank)."""
    out = {}
    if not folder.is_dir():
        return out
    rx = rt.page_rx(doc, "jsonl")
    for e in os.scandir(folder):
        if rx.match(e.name):
            try:
                with open(e.path, encoding="utf-8", errors="replace") as fh:
                    line = next((x for x in fh if x.strip()), "")
                eng = (json.loads(line).get("engine") or "?") if line else "?"
            except (OSError, ValueError):
                eng = "?"
            key = "tesseract-fallback" if "fallback" in eng else ("blank" if eng == "blank" else (
                "vision" if "vision" in eng else eng))
            out[key] = out.get(key, 0) + 1
    return out


def oldest_backup(backup_dir: Path, doc: str):
    """The first repair's backup of this text: what was translated before it (another text whose code begins
    with this one's is not taken)."""
    rx = re.compile(r"^context_pre_repair_%s_(\d{8}_\d{6})\.db$" % re.escape(doc))
    try:
        found = sorted(p for p in backup_dir.glob("context_pre_repair_%s_*.db" % doc) if rx.match(p.name))
    except OSError:
        return None
    return found[0] if found else None


def grams(text: str) -> set:
    s = ew.skel(text)
    return {s[i:i + ew.K] for i in range(len(s) - ew.K + 1)}


def prf(a: set, ref: set):
    if not a or not ref:
        return None
    hit = len(a & ref)
    p, r = hit / float(len(a)), hit / float(len(ref))
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def describe(label: str, kind: str, pages: dict, doc: str) -> dict:
    """Completeness and debris of one reading."""
    rows = [(p, t, kind, False, 1.0) for p, t in sorted(pages.items())]
    dev = sum(len(ew.DEV_LETTER.findall(t)) for t in pages.values())
    lat = sum(len(ew.ASCII_LETTER.findall(t)) for t in pages.values())
    j = rt.judge(rows, Path("/nonexistent"), doc, max_pages=0) if rows else {}
    q = ew.quality(pages.values())   # QUALITY_2026_10_11: the Devanagari itself, not only the Latin in it
    return {"label": label, "kind": kind, "pages": len(pages), "letters": dev,
            "latin_pct": round(100.0 * lat / (lat + dev), 2) if lat + dev else 0.0,
            "misread_letters_pct": j.get("misread_letters_pct", 0.0), "pages_misread_pct": j.get("misread_pct", 0.0),
            "level": j.get("level") if rows else None, "misread_top": (j.get("misread_top") or [])[:6],
            "noise_pct": q["noise_pct"], "glued_pct": q["glued_pct"], "malformed_pct": q["malformed_pct"],
            "symbols_pct": q["symbols_pct"], "plausible_pct": q["plausible_pct"], "glued_top": q["glued_top"]}


def witness_readings(doc: str, wfile: Path, wdir: Path) -> list:
    """[(label, kind, site, {page: text}, source file name)] of the witnesses written for the text."""
    out = []
    for w, r in sorted(ew.witnesses(wfile).items()):
        if r.get("doc") != doc:
            continue
        d = wdir / w
        try:
            al = json.loads((d / "align.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        verses = []
        for p in sorted(d.glob("%s_*.jsonl" % w)):
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    try:
                        verses.append(json.loads(line).get("text") or "")
                    except ValueError:
                        continue
        pages = {}
        for k, pr in (al.get("pages") or {}).items():
            if pr.get("status") == "match" and pr.get("lo") is not None and pr["hi"] < len(verses):
                pages[int(k)] = "\n".join(verses[pr["lo"]:pr["hi"] + 1])
        site = r.get("site") or "etext"
        out.append(("witness %s" % w.split("__w_", 1)[-1], "archive-ocr" if site == "archive" else "etext", site, pages,
                    r.get("file") or ""))
    return out


def file_readings(doc: str, files: list, scan: dict, skip_names: set) -> list:
    out = []
    for f in files:
        f = Path(f)
        if f.name in skip_names or not f.is_file():
            continue
        try:
            text, info = ew.read_text(f)
        except OSError:
            continue
        parsed = ew.parse(text)
        units = parsed["pages"] if parsed["mode"] == "pages" else parsed["verses"]
        if parsed["scheme"] == "unknown" or len(units) < 5:
            continue
        verses = [{"text": u["text"], "ref": u.get("ref", "")} for u in units]
        m = ew.measure(verses, scan)
        pages = {p: "\n".join(verses[i]["text"] for i in range(r["lo"], r["hi"] + 1))
                 for p, r in m["pages"].items() if r["status"] == "match"}
        site = ew.site_of(f)
        out.append(("file %s" % f.name[:40], "archive-ocr" if site == "archive" else "etext", site, pages, f.name))
    return out


def benchmark(a, doc: str) -> dict:
    raw, vision, merged = Path(a.raw), Path(a.vision_dir), Path(a.merged_dir)
    res = {"doc": doc, "at": _now(), "mark": MARK, "readings": [], "reference": None, "lines": []}
    readings = []                                   # (label, kind, site, pages)
    for label, kind, folder in (("tesseract", "ocr", raw), ("vision", "ocr", vision), ("consensus", "ours", merged)):
        pg = page_files(folder, doc)
        if pg:
            readings.append((label, kind, "", pg))
    dbp, now = db_reading(Path(a.db), doc)
    if dbp:
        readings.append(("database", "ours" if not any(r[0] == "consensus" for r in readings) else "db", "", dbp))
    bk = Path(a.backup) if a.backup else oldest_backup(Path(a.backup_dir), doc)
    before = {}
    if bk and bk.exists():
        bp, before = db_reading(bk, doc, immutable=True)
        if bp:
            readings.append(("before repair", "before", "", bp))
            before["backup"] = str(bk)
    scan = dbp or next((r[3] for r in readings if r[0] == "consensus"), None) or next((r[3] for r in readings), None)
    wit = witness_readings(doc, Path(a.witnesses), Path(a.out_dir))
    readings += [(l, k, s, p) for l, k, s, p, _ in wit]
    skip = {Path(x[4]).name for x in wit if x[4]}
    files = list(a.etext or [])
    sd = Path(a.sources) / doc
    if sd.is_dir():
        files += [str(p) for p in sorted(sd.iterdir()) if p.suffix.lower() in TEXT_EXT and p.is_file()]
    if scan:
        readings += [(l, k, s, p) for l, k, s, p, _ in file_readings(doc, files, scan, skip)]
    if not readings:
        res["verdict"] = "nothing to benchmark: no page files, no passages, no witness of %s" % doc
        return res
    ours = next((r for r in readings if r[0] == "consensus"), None) or next((r for r in readings if r[0] == "database"), None)
    ref = None
    for r in readings:
        if r[1] == "etext" and (not a.reference or a.reference.lower() in (r[0] + " " + r[2]).lower()):
            ref = r
            break
    res["reference"] = ref[0] if ref else None
    og = {p: grams(t) for p, t in ours[3].items()} if ours else {}
    rg = {p: grams(t) for p, t in ref[3].items()} if ref else {}
    for label, kind, site, pages in readings:
        d = describe(label, kind, pages, doc)
        d["site"] = site
        if ours and label != ours[0]:
            v = [prf(grams(t), og[p]) for p, t in pages.items() if p in og]
            v = [x for x in v if x]
            d["f1_ours"] = round(statistics.median([x[2] for x in v]), 3) if v else None
            d["ours_pages"] = len(v)
        if ref and label != ref[0]:
            v = [prf(grams(t), rg[p]) for p, t in pages.items() if p in rg]
            v = [x for x in v if x]
            d["f1_ref"] = round(statistics.median([x[2] for x in v]), 3) if v else None
            d["recall_ref"] = round(statistics.median([x[1] for x in v]), 3) if v else None
            d["ref_pages"] = len(v)
        res["readings"].append(d)
    res["translations"] = {"now": now, "before": before}
    res["merged_engines"] = page_engines(merged, doc)   # QUALITY_2026_10_11
    n_pages = getattr(a, "letters_pages", None)
    if ours and n_pages:
        try:
            letters(res, readings, ours, n_pages)       # BENCH_LETTERS_2026_10_22
        except Exception as ex:                         # an addition: never the benchmark's failure
            res["letters_error"] = str(ex)[:200]
    return opine(res, doc, a)


def letters(res: dict, readings: list, ours: tuple, n_pages: int) -> None:
    """BENCH_LETTERS_2026_10_22: every reading against ours, akshara by akshara, on a sample of ours' pages; then
    Tesseract beside each other OCR reading (vision, archive.org's text, the repair): own misreadings and where the
    two agree against ours. Fills each reading's aksharas_ours (and own_per100) and res["letters"]."""
    import source_fidelity as sf
    pages = sorted(p for p, t in ours[3].items() if len(sf.norm(t)) >= sf.MIN_LETTERS)
    if not pages:
        return
    step = max(1, len(pages) // n_pages)
    sample = pages[::step][:n_pages]
    units = [sf.norm(ours[3][p]) for p in sample]
    refs = ["p%d" % p for p in sample]
    per = {}
    for label, kind, site, pg in readings:
        if label == ours[0]:
            continue
        rs = [(sf.measure([u], [(p, pg[p])], False)[0] if pg.get(p) else None) for p, u in zip(sample, units)]
        per[label] = rs
        found = [r for r in rs if r]
        n = sum(r["n"] for r in found)
        d = _r(res, label)
        if d is not None:
            d["aksharas_ours"] = round(100.0 - 100.0 * sum(r["err"] for r in found) / n, 2) if n else None
            d["aksharas_pages"] = len(found)
    # the voters: OCR readings of the scan that are not ours' own text again: the repair is made from vision (and
    # the database from the repair), so beside the repair they are its sources, not witnesses; a reading 99.9% alike
    # is a copy of ours too
    same, voters = [], []
    for label in per:
        d = _r(res, label) or {}
        if d.get("kind") not in ("ocr", "archive-ocr", "ours", "db") or d.get("aksharas_ours") is None:
            continue
        derived = ours[0] == "consensus" and label in ("vision", "database")
        (same if (derived or d["aksharas_ours"] >= 99.9) else voters).append(label)
    if "tesseract" in voters:
        combos = [("tesseract", x) for x in voters if x != "tesseract"]
    else:
        combos = [(voters[i], voters[j]) for i in range(len(voters)) for j in range(i + 1, len(voters))]
    pairs = []
    for la, lb in combos:
        pr = sf.pair(units, per[la], per[lb], refs, keep=12)
        if not pr["units"]:
            continue
        pr.update(a=la, b=lb)
        pairs.append(pr)
        d = _r(res, lb)
        d["own_per100"] = pr["own_b_per100"]
        d["outvoted_ours_per100"] = pr["outvoted_per100"]
        d["independent_of_tesseract"] = pr["independent"] if la == "tesseract" else None
    for la in {pr["a"] for pr in pairs}:
        d = _r(res, la)
        if d is not None:
            d["own_per100"] = max((x for x in pairs if x["a"] == la), key=lambda x: x["aksharas"])["own_a_per100"]
    res["letters"] = {"mark": "BENCH_LETTERS_2026_10_22", "pages": len(sample), "ours": ours[0], "pairs": pairs,
                      "same_as_ours": same}


def _p(x, k, fmt="%.1f%%"):
    return (fmt % x[k]) if x and x.get(k) is not None else "-"


def compare(a: dict, b: dict):
    """QUALITY_2026_10_11: which of two readings of the same pages is the less damaged, by the Latin misread, the noise
    in the Devanagari and the plausibility; -> (score > 0 when a is, [the reasons])."""
    score, why = 0, []
    for k, better, margin, name in (("misread_letters_pct", -1, 0.3, "Latin misread"), ("noise_pct", -1, 1.0, "noise in the "
                                    "Devanagari"), ("plausible_pct", 1, 1.0, "plausible")):
        x, y = a.get(k), b.get(k)
        if x is None or y is None:
            continue
        d = (x - y) * better
        if d > margin:
            score += 1; why.append("%s %.1f%% against %.1f%%" % (name, x, y))
        elif d < -margin:
            score -= 1; why.append("%s %.1f%% against %.1f%%" % (name, x, y))
    return score, why


def _r(res, label):
    return next((x for x in res["readings"] if x["label"] == label), None)


def opine(res: dict, doc: str, a) -> dict:
    """The expert opinion, in plain lines, from the numbers."""
    L = res["lines"]
    te, ours = _r(res, "tesseract"), (_r(res, "consensus") or _r(res, "database"))
    if te and ours:
        t, o = te["misread_letters_pct"], ours["misread_letters_pct"]
        cut = (100.0 * (t - o) / t) if t else 0.0
        more = (100.0 * (ours["letters"] - te["letters"]) / te["letters"]) if te["letters"] else 0.0
        nz = "; noise in the Devanagari %s against Tesseract's %s" % (_p(ours, "noise_pct"), _p(te, "noise_pct"))
        if ours["label"] != "consensus" and o < 0.5 * t and (ours.get("noise_pct") or 0) <= (te.get("noise_pct") or 0):
            # QUALITY_2026_10_11: a text ingested from vision earlier is no unrepaired text
            L.append("OCR: the text in the database is already a better reading than Tesseract's (it was ingested from "
                     "vision): misread letters %.2f%% against %.2f%%%s." % (o, t, nz))
        elif ours["label"] != "consensus":
            L.append("OCR: not repaired: the text in the database misreads %.2f%% of the letters (Tesseract's pages %.2f%%, "
                     "%.0f%% of them damaged)%s." % (o, t, te["pages_misread_pct"], nz))
        elif t >= 0.3 and o < t:
            L.append("OCR: Tesseract misread %.2f%% of the letters (%.0f%% of its pages damaged); the repair %.2f%% (%.0f%% "
                     "of pages): it removed %.0f%% of the misreading%s%s." % (
                         t, te["pages_misread_pct"], o, ours["pages_misread_pct"], cut,
                         ("; it reads %+.0f%% Devanagari letters" % more) if abs(more) >= 3 else "", nz))
        else:
            L.append("OCR: Tesseract misread %.2f%% of the letters, the repair %.2f%%%s: little to gain here." % (t, o, nz))
    arch = [x for x in res["readings"] if x["kind"] == "archive-ocr"]
    for x in arch:
        if not ours:
            continue
        if res["reference"] and x.get("f1_ref") is not None and ours.get("f1_ref") is not None:
            d = x["f1_ref"] - ours["f1_ref"]
            how = "F1 with the critical text %.2f, ours %.2f" % (x["f1_ref"], ours["f1_ref"])
        else:
            # QUALITY_2026_10_11: by the Latin misread alone, archive.org's 1960 Bodhicaryavatara (no Latin, noise in 9.4%
            # of its words) was called the better reading; the Devanagari counts too
            sc, why = compare(x, ours)
            d = 0.03 if sc > 0 else (-0.03 if sc < 0 else 0.0)
            how = "; ".join(why) or "misread letters %.2f%%, ours %.2f%%" % (x["misread_letters_pct"], ours["misread_letters_pct"])
            how = "archive.org's " + how if why else how
        if d > 0.02 and (x.get("noise_pct") or 0) <= ew.NOISE_WARN:
            word = "archive.org's reading is the better one here: make it a witness"
        elif d > 0.02:
            word = ("archive.org's reading is the less damaged, but its own Devanagari is noise in %.1f%% of its words: "
                    "neither is clean; look for an e-text or OCR a better scan with vision" % x["noise_pct"])
        elif d < -0.02 and (ours.get("misread_letters_pct") or 0) < 1.0 and (ours.get("noise_pct") or 0) <= ew.NOISE_WARN:
            word = "ours is the better one"
        elif d < -0.02:
            # the Bodhicaryavatara: ours misreads 11.5% of its letters; archive.org's has noise in 9.4% of its words
            word = ("ours is the less damaged by these measures, but it is damaged too (misread %.1f%%, noise %s): neither "
                    "is clean; look for an e-text or OCR a better scan with vision" % (ours["misread_letters_pct"], _p(ours, "noise_pct")))
        else:
            word = "the two are level, each damaged in its own way"
        if x.get("own_per100") is not None and x.get("independent_of_tesseract") is False:   # BENCH_LETTERS_2026_10_22
            word += ("; letter by letter it makes Tesseract's mistakes (one engine, or the same weak letters): it is no "
                     "independent reading, and its agreement with Tesseract says nothing against ours")
        elif x.get("own_per100") is not None:
            word += ("; letter by letter, its own misreadings %s aksharas in 100, and where it and Tesseract agree "
                     "against ours, %s in 100 (ours' likely misreadings)" % (x["own_per100"], x.get("outvoted_ours_per100")))
        L.append("archive.org's OCR (%s), on the %d pages it shares with this scan: %s; %s." % (x["label"], x["pages"], how, word))
    if res["reference"]:
        ranked = sorted([x for x in res["readings"] if x.get("f1_ref") is not None], key=lambda x: -x["f1_ref"])
        if ranked:
            L.append("Against the critical e-text (%s), page by page: %s." % (res["reference"], "; ".join(
                "%s reads %.0f%% of it (F1 %.2f, %d pages)" % (x["label"], 100 * (x.get("recall_ref") or 0), x["f1_ref"],
                                                             x.get("ref_pages", 0)) for x in ranked[:6])))
        vi, co = _r(res, "vision"), _r(res, "consensus")
        if vi and co and vi.get("f1_ref") is not None and co.get("f1_ref") is not None and vi["f1_ref"] > co["f1_ref"] + 0.02:
            L.append("Vision alone reads the critical text better than the consensus (F1 %.2f against %.2f): the merge "
                     "keeps some Tesseract readings it should not." % (vi["f1_ref"], co["f1_ref"]))
    lt = res.get("letters") or {}
    if lt.get("pages"):   # BENCH_LETTERS_2026_10_22
        ag = [x for x in res["readings"] if x.get("aksharas_ours") is not None]
        if ag:
            L.append("Letter by letter, on %d of ours' pages: %s agree with ours (%s) in %s of the aksharas." % (
                lt["pages"], ", ".join(x["label"] for x in ag), lt["ours"],
                ", ".join("%.1f%%" % x["aksharas_ours"] for x in ag)))
        if lt.get("same_as_ours"):
            L.append("%s: ours' own text again (the repair's sources, or 99.9%% alike): no witness of it."
                     % ", ".join(lt["same_as_ours"]))
        if not lt.get("pairs"):
            L.append("No two independent readings of the scan beside ours: its letters cannot be voted on here. A reading "
                     "by another engine (vision, where ours is Tesseract's), or an e-text, measures it.")
        for pr in lt.get("pairs") or []:
            if not pr.get("independent", True):
                L.append("%s and %s, letter by letter: their own misreadings %s and %s aksharas in 100, and they "
                         "make the same mistakes (alike %.2f and %.2f): one engine, or the same weak letters; their "
                         "agreement against ours is no evidence." % (pr["a"].capitalize(), pr["b"], pr["own_a_per100"],
                                                                     pr["own_b_per100"], pr["own_overlap"],
                                                                     pr["outvoted_overlap"]))
                continue
            L.append("%s and %s, letter by letter: their own misreadings %s and %s aksharas in 100; where they "
                     "agree with each other against ours, %s in 100: there ours is most likely misread (%d places; read "
                     "them beside the page: python scripts\\source_fidelity.py --ref db:%s --cand raw:%s --cand ...)." % (
                         pr["a"].capitalize(), pr["b"], pr["own_a_per100"], pr["own_b_per100"], pr["outvoted_per100"],
                         pr["outvoted"], res["doc"], res["doc"]))
    # QUALITY_2026_10_11: without a critical text too. On 11 Oct the Tantric Texts' repair misread 1.90% of its letters
    # where vision misread 0.17%: on 7 plates and title pages vision read nothing or a line, and the merge took
    # Tesseract's garbage of the picture
    vi, co = _r(res, "vision"), _r(res, "consensus")
    eng = res.get("merged_engines") or {}
    if vi and co and co["misread_letters_pct"] > vi["misread_letters_pct"] + 0.3:
        L.append("The repair misreads more than vision alone: %.2f%% of the letters against %.2f%%. %d of its pages are "
                 "Tesseract's (vision read nothing there, or far less)%s. Merged again under QUALITY_2026_10_11, a plate or "
                 "a title page keeps vision's line, or is blank, instead of Tesseract's garbage of the picture." % (
                     co["misread_letters_pct"], vi["misread_letters_pct"], eng.get("tesseract-fallback", 0),
                     ("; %d are blank" % eng["blank"]) if eng.get("blank") else ""))
    if ours and (ours.get("glued_pct") or 0) >= 1.0:
        L.append("%.1f%% of ours' Devanagari words have a Latin letter or a stray mark glued to them (most often %s): a "
                 "printed sign read as a letter; it goes into the translation as written." % (
                     ours["glued_pct"], ", ".join('"%s"' % g for g in ours.get("glued_top") or []) or "-"))
    tr = res.get("translations") or {}
    b, n = tr.get("before") or {}, tr.get("now") or {}
    if b.get("english"):
        share = b.get("translated_misread_pct") or 0.0
        nzs = b.get("translated_noise_pct") or 0.0      # QUALITY_2026_10_11: and the malformed Devanagari
        lv = "material" if max(share, nzs) >= MATERIAL_TR else ("moderate" if max(share, nzs) >= MODERATE_TR else "cosmetic")
        L.append("Translation before the repair: %d English, %d Hindi; %.0f%% of the passages translated carried misread "
                 "letters (%.2f%% of their letters) and %.0f%% had noise in a tenth of their Devanagari words or more: the debris's "
                 "effect on that translation "
                 "was %s." % (b["english"], b.get("hindi", 0), share, b.get("translated_letters_misread_pct") or 0.0, nzs,
                              lv.upper()))
    if n.get("english"):
        share = n.get("translated_misread_pct") or 0.0
        nzs = n.get("translated_noise_pct") or 0.0
        lv = "material" if max(share, nzs) >= MATERIAL_TR else ("moderate" if max(share, nzs) >= MODERATE_TR else "cosmetic")
        L.append("Translation now: %d English of %d passages, %d Hindi%s; %.0f%% of the passages translated carry misread "
                 "letters and %.0f%% had noise in a tenth of their Devanagari words or more: %s. The QA figure is structural "
                 "(length, residue, script), not "
                 "a reading of the meaning%s." % (n["english"], n["passages"], n.get("hindi", 0),
                                                  ("; heuristic QA %.2f" % n["qa_mean"]) if n.get("qa_mean") is not None else "",
                                                  share, nzs, lv, "" if n.get("reviews") else "; no LLM judge has read it yet"))
        if n.get("reviews"):
            rv = n["reviews"]
            line = "The LLM judge (mt_reviews) graded %d English passages: fidelity %.2f, fluency %.2f of 5." % (
                rv["n"], rv["fidelity"], rv["fluency"])
            if rv.get("serious") is not None:   # REINGEST_2026_10_12: the share with a wrong meaning, and what it is
                sh = 100.0 * rv["serious"] / rv["n"]
                lv = "material" if sh >= 10 else ("moderate" if sh >= 5 else "cosmetic")
                line += (" %d of them (%.0f%%) have a serious error of meaning (fidelity 2 or less: an omission, a "
                         "negation lost, a word misread): %s. It is a sample, judged by a model of the translator's "
                         "family; read the passages it marks (python scripts\\judge_sample.py --report)." % (
                             rv["serious"], sh, lv))
            L.append(line)
    elif n.get("passages"):
        L.append("Translation now: none of its %d passages has English yet." % n["passages"])
    q = "python scripts\\repair_text.py --doc %s" % doc
    nxt, also = "", []
    st = (rt.verdicts(Path(a.verdicts)).get(doc) or {}).get("status")
    if st in ("set_aside", "complete"):
        pass                                        # the register says it is not to be translated (further)
    elif n.get("passages") and n.get("english", 0) < 0.9 * n["passages"] and (not ours or ours["misread_letters_pct"] < 1.0):
        nxt = "translate it: Finish EN and Add Hindi in the Library"
    elif ours and ours["misread_letters_pct"] >= 1.0 and not res["reference"]:
        nxt = q + " --find-source"
    if not arch:
        cur = current_scan(doc, Path(a.source_desk))
        if cur:
            also.append("python scripts\\source_desk.py --doc %s --fetch %s --kind text --force   (archive.org's own OCR "
                        "of this scan, to compare; it is not ingested)" % (doc, cur))
    res["next"], res["also"] = nxt, also
    best = ours["label"] if ours else res["readings"][0]["label"]
    res["verdict"] = "%d reading(s) of %s compared%s; ours (%s) misreads %.2f%% of the letters" % (
        len(res["readings"]), doc, (" with the critical e-text (%s)" % res["reference"]) if res["reference"] else "",
        best, (ours or res["readings"][0])["misread_letters_pct"])
    return res


def current_scan(doc: str, sd_dir: Path):
    try:
        j = json.loads((sd_dir / ("%s.json" % doc)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    c = next((x for x in j.get("candidates") or [] if x.get("current_scan")), None)
    ident = (c or {}).get("identifier") or ""
    return ident if re.match(r"^[A-Za-z0-9._\-]+$", ident) else None


def show(res: dict):
    print("%s  %s" % (res["doc"], MARK))
    hdr = "  %-22s %-11s %6s %9s %7s %8s %7s %-9s %6s %6s %7s %7s %7s %7s %6s"   # QUALITY_2026_10_11; BENCH_LETTERS_2026_10_22
    print(hdr % ("reading", "kind", "pages", "letters", "latin%", "misread%", "pages%", "level", "noise%", "plaus%",
                 "F1ours", "F1ref", "ref%", "aksh%", "own"))
    for x in res["readings"]:
        f = lambda k, fmt="%.2f": (fmt % x[k]) if x.get(k) is not None else "-"
        print(hdr % (x["label"][:22], x["kind"], x["pages"], x["letters"], f("latin_pct"), f("misread_letters_pct"),
                     f("pages_misread_pct", "%.0f"), x.get("level") or "-", f("noise_pct", "%.1f"), f("plausible_pct", "%.1f"),
                     f("f1_ours"), f("f1_ref"), ("%.0f" % (100 * x["recall_ref"])) if x.get("recall_ref") is not None else "-",
                     f("aksharas_ours", "%.1f"), f("own_per100", "%.1f")))
    for line in res.get("lines") or []:
        print("  " + line)


def write(res: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / ("%s.json" % res["doc"])
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return p


def all_docs(a) -> list:
    found = set()
    for folder in (Path(a.vision_dir), Path(a.merged_dir)):
        if folder.is_dir():
            for e in os.scandir(folder):
                m = re.match(r"^(.+)_(\d{4})\.jsonl$", e.name)
                if m and not m.group(1).startswith("_"):
                    found.add(m.group(1))
    found |= {r.get("doc") for r in ew.witnesses(Path(a.witnesses)).values() if r.get("doc")}
    sd = Path(a.sources)
    if sd.is_dir():
        found |= {p.name for p in sd.iterdir() if p.is_dir()}
    return sorted(d for d in found if d and re.match(r"^[A-Za-z0-9_\-]+$", d))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Benchmark a text's readings and translation (BENCHMARK_2026_10_11)")
    ap.add_argument("--doc")
    ap.add_argument("--all", action="store_true", help="every text with vision or repaired pages, a witness or a fetched file")
    ap.add_argument("--etext", action="append", help="a further e-text or OCR text to compare (repeatable)")
    ap.add_argument("--reference", default=None, help="which e-text is the critical text (a word of its label or site)")
    ap.add_argument("--backup", default=None, help="the database before the repair (default: the oldest repair backup)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--sources", default="sources")
    ap.add_argument("--source-desk", default="data/source_desk")
    ap.add_argument("--out-dir", default="data/raw_witness")
    ap.add_argument("--witnesses", default="data/witnesses.jsonl")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--bench-dir", default="data/benchmarks")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--letters-pages", type=int, default=None,   # BENCH_LETTERS_2026_10_22
                    help="pages read letter by letter against ours (80; 40 with --all; 0: none)")
    a = ap.parse_args(argv)
    if a.letters_pages is None:
        a.letters_pages = 40 if a.all else 80
    os.chdir(ROOT)
    if a.all:
        rows = []
        docs = all_docs(a)
        for i, d in enumerate(docs, 1):
            res = benchmark(a, d)
            write(res, Path(a.bench_dir))
            te, ours = _r(res, "tesseract"), (_r(res, "consensus") or _r(res, "database"))
            b = (res.get("translations") or {}).get("before") or {}
            n = (res.get("translations") or {}).get("now") or {}
            rows.append({"doc": d, "tesseract": te and te["misread_letters_pct"], "ours": ours and ours["misread_letters_pct"],
                         "ours_noise": ours and ours.get("noise_pct"), "tesseract_noise": te and te.get("noise_pct"),
                         "ours_label": ours and ours["label"], "reference": res.get("reference"),
                         "f1_ref": ours and ours.get("f1_ref"), "en_before": b.get("english"),
                         "before_misread_pct": b.get("translated_misread_pct"), "en_now": n.get("english"),
                         "passages": n.get("passages"), "lines": res.get("lines")})
            print("  [%d/%d] %-56s tesseract %s | ours %s | English before %s (%s%% from damaged text) | now %s/%s" % (
                i, len(docs), d[:56], "-" if te is None else "%.2f%%/%s" % (te["misread_letters_pct"], _p(te, "noise_pct")),
                "-" if ours is None else "%.2f%%/%s (%s)" % (ours["misread_letters_pct"], _p(ours, "noise_pct"), ours["label"]),
                b.get("english", "-"), "-" if b.get("translated_misread_pct") is None else "%.0f" % b["translated_misread_pct"],
                n.get("english", "-"), n.get("passages", "-")), flush=True)
        Path(a.bench_dir).mkdir(parents=True, exist_ok=True)
        (Path(a.bench_dir) / "_summary.json").write_text(json.dumps({"at": _now(), "mark": MARK, "rows": rows},
                                                                    ensure_ascii=False, indent=1), encoding="utf-8")
        improved = [r for r in rows if r["tesseract"] is not None and r["ours"] is not None and r["ours_label"] == "consensus"
                    and r["ours"] < r["tesseract"]]
        print("VERDICT: benchmarked %d text(s); the repair cut the misread letters in %d of them" % (len(rows), len(improved)))
        print("NEXT: open the Benchmarks page (http://127.0.0.1:5057/benchmarks)")
        return 0
    if not a.doc or not re.match(r"^[A-Za-z0-9_\-]+$", a.doc):
        print("FAIL: --doc <code> is needed (letters, digits, _ and -), or --all."); return 2
    res = benchmark(a, a.doc)
    if res["readings"]:
        show(res)
    p = write(res, Path(a.bench_dir))
    print("  wrote %s" % p)
    print("VERDICT: " + res.get("verdict", ""))
    print("NEXT: " + res.get("next", ""))
    for x in res.get("also") or []:
        print("ALSO: " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
