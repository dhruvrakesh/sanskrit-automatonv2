#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
repair_text.py  (2026-10-10, healed 2026-10-11)  REPAIR_PATH_2026_10_10  REPAIR_HEAL_2026_10_11

The repair path for one text, there and then, instead of a run that stops. A translation can stop
for two reasons, both about the scan rather than the translator:
  * held by the OCR-debris guard (translate_passages.py, exit 3): the stored text carries Latin
    letters inside the Devanagari, the page PDFs are in the inbox, so the source is repaired first;
  * most of what is left is below the OCR quality bar (quality_score < 0.35), so it is not sent.
Each step says what it found and what comes next, on its last lines (JUDGED:, VERDICT:, NEXT:, ALSO:),
so the dashboard can offer the next step as a button.

The debris, judged (REPAIR_HEAL_2026_10_11). "Latin letters inside the Devanagari" is not one thing:
  furniture   a run repeated on many pages: a scan's watermark ("CC-0 Jangamwadi Math Collection.
              Digitized by eGangotri"), a running head ("Yajur Veda Adhyaya");
  notes       English words and prose: an editor's apparatus ("This line omitted in ..."), an index;
  numbering   Roman numerals: chapter and page numbers;
  misread     short Latin runs standing where akshara should be ("aa", "ON", "TAT", "ee"): Tesseract
              read the Devanagari as Latin. Only this damages the text that is translated.
The judgement counts the verses with misread letters (3% of their letters or more) and, where vision
pages exist, how far the stored text agrees with vision OCR (characters, page by page):
  cosmetic   misread in under 10% of verses, and vision agreement (when measured) 0.97 or more:
             translate as is; the guard can be told so (--as-is);
  moderate   10-25%, or agreement 0.90-0.97: a translation reads through most of it; the critical
             edition wants the repair;
  material   25% or more, or agreement under 0.90: repair first, or find a better source.

  python scripts\\repair_text.py --doc X                    assess and judge: free, read-only
  python scripts\\repair_text.py --doc X --repair           vision OCR, audit, merge (ocr_consensus.py
                                                           --yes; capped by --max-usd)
  python scripts\\repair_text.py --doc X --use-repaired     back up, wipe, ingest the repaired text,
                                                           classify, check the drift. Only when nothing
                                                           is lost; else add --replace N. A text whose
                                                           translations were replaced is held from the
                                                           site until it is published (--release)
  python scripts\\repair_text.py --doc X --as-is "why"      translate as is: the debris guard lets it by
  python scripts\\repair_text.py --doc X --accept "why"     what is left is not to be translated
  python scripts\\repair_text.py --doc X --hold "why"       the site keeps its last version of the text
  python scripts\\repair_text.py --doc X --release          publish it to the site again
  python scripts\\repair_text.py --doc X --set-aside "why"  the scan cannot be repaired: a better scan
                                                           is wanted; the Library stops offering it
  python scripts\\repair_text.py --doc X --find-source [--ai]  look for a better edition (source_desk.py)
  python scripts\\repair_text.py --doc X --restore          undo --set-aside, --as-is or --accept
  python scripts\\repair_text.py --list                     the register: texts not in the ordinary state

Safety: the assessment opens the database read-only. --repair never writes it (ocr_consensus.py does
not). --use-repaired refuses unless the repaired text covers every page, the dashboard runs no other
database writer and no vision repair of this text (or this runs as the dashboard's own job, under its
translate lock), and a consistent backup was made first (db_backup.py). The page PDFs are never
deleted. data/source_verdicts.jsonl is the register; its latest record per text is the text's state.
"""
from __future__ import annotations
import argparse, datetime, json, math, os, re, sqlite3, statistics, subprocess, sys, urllib.request
from difflib import SequenceMatcher
from pathlib import Path

MARK = "REPAIR_PATH_2026_10_10"
HEAL = "REPAIR_HEAL_2026_10_11"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(os.environ.get("SA_REPAIR_SCRIPTS") or (ROOT / "scripts"))   # the override is for the tests
PY = sys.executable
DEBRIS_MAX = float(os.environ.get("SA_DEBRIS_MAX") or 30.0)     # as translate_passages.py
MIN_QUALITY = 0.35                                              # as translate_passages.py
NOTHING_TO_LOSE_EN = 5          # at most this many English translations count as nothing to lose
COST_PER_PAGE = 0.0004          # measured on Karan Aagama, 2026-10-10 ($0.00017-0.00038 a page)
DASHBOARD = os.environ.get("SA_DASHBOARD_URL") or "http://127.0.0.1:5057"
STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "withdrawn")   # the rest ("restored", "released") are ordinary; withdrawn: PATH_2026_10_12

JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")      # = translate_passages._debris_guard
DEV = re.compile(r"[\u0900-\u097f]")
DEVW = re.compile(r"[\u0900-\u097f]+")
LATIN_RUN = re.compile(r"(?:(?<![A-Za-z])[A-Za-z][A-Za-z'.,;:()\-]*(?:[ \t]+|$))+")
LATIN_TOK = re.compile(r"[A-Za-z][A-Za-z']*")
ROMAN = re.compile(r"^(?=[IVXLCDM]+$|[ivxlcdm]+$)[IVXLCDMivxlcdm]{1,7}$")
MIXED = re.compile(r"[\u0900-\u097f][0-9/{}\[\]<>$#@%^&*_=+]|[0-9/{}\[\]<>$#@%^&*_=+][\u0900-\u097f]")
PUNCT_ONLY = re.compile(r"^[\s\u0964\u0965|0-9\u0966-\u096f.\-()\[\]]*$")
ENGLISH = set("""a an and are as at be been but by cf chapter ed eds edition editor for from has have
in index introduction is it its line lines ms mss not note notes of om omitted on or p page pages part
read reads see text texts that the this to var verse verses vol was were which with appendix appendices
also all one two here there these those than then after before into upon""".split())

LEVELS = ("cosmetic", "moderate", "material")
# REINGEST_2026_10_12: the in-place re-ingest, offered where --use-repaired would replace translations or pictures
REINGEST = ("python scripts\\reingest_pages.py --doc %s   (only the pages that changed: the rest keep their translations "
            "and pictures; the plan is free)")


def measured_cost_per_page(db: str, doc: str) -> float:
    """REINGEST_2026_10_12: what a vision page of this text really costs, from usage_log (ocr_consensus.py's measure,
    as ocr_vision.py prices its pre-flight). The assessment said "269 pages, about $0.11" for the Natyasastra on
    12 Oct, at COST_PER_PAGE; its pages had cost $0.011 each, 27 times as much. COST_PER_PAGE when nothing is measured."""
    try:
        import ocr_consensus as _oc
        return float(_oc.measured_cost_per_page(db, fallback=COST_PER_PAGE, doc=doc))
    except Exception:
        return COST_PER_PAGE


def vision_gave_up(work: Path, doc: str) -> int:
    """READ_IN_2026_10_13: the pages vision failed on in two runs or more, left to Tesseract (PATH_2026_10_12's
    ledger, data/ocr_consensus/<doc>_vision_failed.json); 0 when there is none."""
    try:
        import ocr_consensus as _oc
        return sum(1 for v in _oc.read_failed(Path(work), doc).values()
                   if int((v or {}).get("fails") or 0) >= _oc.VISION_GIVE_UP)
    except Exception:
        return 0


def page_rx(doc: str, ext: str):
    return re.compile(r"^%s_(\d{4})(?:_norm)?\.%s$" % (re.escape(doc), ext), re.I)


def pages_in(folder: Path, doc: str, ext: str) -> set:
    rx = page_rx(doc, ext)
    if not folder.is_dir():
        return set()
    return {m.group(1) for m in (rx.match(e.name) for e in os.scandir(folder)) if m}


def verdicts(path: Path) -> dict:
    """doc -> its latest record in the register."""
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("doc"):
                out[r["doc"]] = r
    return out


# ---- the debris, judged ------------------------------------------------------------------------
def _latin_runs(text: str) -> list:
    out = []
    for m in LATIN_RUN.finditer(text):
        toks = LATIN_TOK.findall(m.group(0))
        if toks and not (len(toks) == 1 and len(toks[0]) < 2):
            out.append(toks)
    return out


def _vision_text(path: Path) -> str:
    parts = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    parts.append(json.loads(line).get("text") or "")
                except ValueError:
                    continue
    except OSError:
        return ""
    return " ".join(parts)


def judge(rows: list, vision_dir: Path, doc: str, max_pages: int = 40) -> dict:
    """rows: (page_no, text, engine, has_translation, quality) of the verses in scope. Returns what the
    Latin letters in them are, how many verses lose letters to misreading, and (where vision pages are
    on disk) how far the stored text agrees with vision OCR."""
    per, pages_of = [], {}
    for pg, text, eng, has_tr, q in rows:
        text = text or ""
        if len(DEV.findall(text)) < 8:
            continue
        rs = _latin_runs(text)
        per.append((pg, text, rs))
        for r in rs:
            # furniture is a phrase or a word, repeated: a watermark, a running head. Short runs of short
            # tokens ("aa on", "fan tat") are misreadings even when they repeat, so they are not counted.
            if sum(len(t) for t in r) >= 5 and max(len(t) for t in r) >= 4:
                pages_of.setdefault(" ".join(t.lower() for t in r), set()).add(pg)
    npages = len({p for p, _, _ in per}) or 1
    furn = {k for k, v in pages_of.items() if len(v) >= max(5, 0.05 * npages)}
    nv = len(per)
    c = {"furniture": 0, "notes": 0, "numbering": 0, "misread": 0}
    gchars = tchars = 0
    gtok, ftop = {}, {}
    for pg, text, rs in per:
        tc = len(re.sub(r"\s", "", text)) or 1
        tchars += tc
        g, kinds = 0, set()
        for r in rs:
            key = " ".join(t.lower() for t in r)
            if key in furn:
                kinds.add("furniture"); ftop[key] = len(pages_of.get(key, ()))
                continue
            if len(r) >= 3 and sum(len(t) for t in r) / len(r) >= 3.0:
                kinds.add("notes")
                continue
            for t in r:
                if ROMAN.match(t):
                    kinds.add("numbering")
                elif t.lower() in ENGLISH:
                    kinds.add("notes")
                elif len(t) >= 2:
                    g += len(t); gtok[t] = gtok.get(t, 0) + 1
        gchars += g
        if g and g >= 0.03 * tc:
            kinds.add("misread")
        for k in kinds:
            c[k] += 1
    pct = lambda x: round(100.0 * x / nv, 1) if nv else 0.0
    out = {"verses": nv, "misread_pct": pct(c["misread"]), "furniture_pct": pct(c["furniture"]),
           "notes_pct": pct(c["notes"]), "numbering_pct": pct(c["numbering"]),
           "misread_letters_pct": round(100.0 * gchars / tchars, 2) if tchars else 0.0,
           "misread_top": [t for t, _ in sorted(gtok.items(), key=lambda x: -x[1])[:10]],
           "furniture_top": [k for k, _ in sorted(ftop.items(), key=lambda x: -x[1])[:3]]}
    # vision agreement: pages whose stored text is not vision OCR and that have a vision page on disk
    stored, skip = {}, set()
    for pg, text, eng, has_tr, q in rows:
        e = (eng or "").lower()
        if "fallback" in e:          # ETEXT_WITNESS_2026_10_11 (judge v2): the merge kept Tesseract, vision failed there
            skip.add(pg)
        elif "vision" not in e:
            stored.setdefault(pg, []).append(text or "")
    vis = pages_in(vision_dir, doc, "jsonl") if max_pages else set()
    both = sorted(int(p) for p in vis if int(p) in stored and int(p) not in skip)
    if len(both) > max_pages:
        step = len(both) / float(max_pages)
        both = [both[int(i * step)] for i in range(max_pages)]
    sims = []
    for pg in both:
        a = " ".join(DEVW.findall(" ".join(stored[pg])))
        b = " ".join(DEVW.findall(_vision_text(vision_dir / ("%s_%04d.jsonl" % (doc, pg)))))
        if len(a) < 80 or len(b) < 80 or len(a) > 8000 or len(b) < 0.5 * len(a):
            continue                 # a short vision page is a failed one, not a disagreement (judge v2)
        sims.append(SequenceMatcher(None, a, b, autojunk=False).ratio())
    if sims:
        sims.sort()
        out.update(agree_median=round(statistics.median(sims), 3), agree_p10=round(sims[len(sims) // 10], 3),
                   agree_pages=len(sims))
    lvl = 0
    if out["misread_pct"] >= 25:
        lvl = 2
    elif out["misread_pct"] >= 10:
        lvl = 1
    # ETEXT_WITNESS_2026_10_11 (judge v2): a text cut into long passages (a page each) hides its misreadings
    # under the 3% a verse; there the share of all letters misread counts (2% material, 1% moderate: where
    # 25% of verses are misread, 2.0-2.5% of the letters are, on the 47 texts judged on 11 Oct). Not for
    # verses, where 1.5% of letters would have made ten of the eleven moderate texts, and three cosmetic, material.
    if nv and tchars / float(nv) >= 600:
        lvl = max(lvl, 2 if out["misread_letters_pct"] >= 2.0 else (1 if out["misread_letters_pct"] >= 1.0 else 0))
    if len(sims) >= 5:               # two pages are not a measurement
        lvl = max(lvl, 2 if out["agree_median"] < 0.90 else (1 if out["agree_median"] < 0.97 else 0))
    out["level"] = LEVELS[lvl]
    return out


def leftovers(rows: list) -> dict:
    """What the untranslated verses below the OCR bar are: English pages read as Devanagari, lone
    dandas and numbers, Latin text, or Sanskrit."""
    below = misread = punct = latin = 0
    for pg, text, eng, has_tr, q in rows:
        if has_tr or q is None or float(q) >= MIN_QUALITY:
            continue
        below += 1
        t = text or ""
        toks = t.split()
        dev, lat = len(DEV.findall(t)), len(re.findall(r"[A-Za-z]", t))
        if PUNCT_ONLY.match(t):
            punct += 1
        elif toks and sum(1 for w in toks if MIXED.search(w)) >= 0.25 * len(toks):
            misread += 1
        elif lat > dev:
            latin += 1
    return {"below": below, "misread_english": misread, "punctuation": punct, "latin": latin,
            "not_sanskrit": misread + punct + latin}


def explain(j: dict) -> str:
    if not j or not j.get("verses"):
        return ""
    bits = []
    if j["furniture_pct"]:
        bits.append("page furniture in %.0f%% of verses%s" % (j["furniture_pct"],
                    (" (\"%s\")" % j["furniture_top"][0]) if j.get("furniture_top") else ""))
    if j["notes_pct"]:
        bits.append("English notes in %.0f%%" % j["notes_pct"])
    if j["numbering_pct"]:
        bits.append("numbering in %.0f%%" % j["numbering_pct"])
    mis = ("misread letters in %.0f%% of verses (%.1f%% of the letters%s)"
           % (j["misread_pct"], j["misread_letters_pct"],
              (": " + ", ".join(j["misread_top"][:5])) if j.get("misread_top") else ""))
    agree = ("; vision OCR agrees with the stored text on %.0f%% of the characters (median of %d pages)"
             % (100 * j["agree_median"], j["agree_pages"])) if j.get("agree_pages") else ""
    tail = {"cosmetic": "translate as is",
            "moderate": "a translation reads through most of it; the critical edition wants the repair",
            "material": "repair first: translating now translates the OCR's errors"}[j["level"]]
    return "%s: %s%s%s. %s." % (j["level"], mis, ("; " + "; ".join(bits)) if bits else "", agree, tail[0].upper() + tail[1:])


# ---- the assessment ----------------------------------------------------------------------------
def assess(a) -> dict:
    db = Path(a.db)
    res = {"doc": a.doc, "mark": MARK}
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db.as_posix(), uri=True, timeout=10)
    except sqlite3.Error as e:
        return {"doc": a.doc, "error": "cannot open %s read-only: %s" % (db, e)}
    try:
        row = con.execute("SELECT id FROM docs WHERE code=?", (a.doc,)).fetchone()
        if not row:
            return {"doc": a.doc, "error": "no text %r in the database" % a.doc}
        did = row[0]
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        scope = " AND COALESCE(text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
        eng = "ocr_engine" if "ocr_engine" in cols else "NULL"
        qcol = "quality_score" if "quality_score" in cols else "1.0"
        n = dn = bad = vis = low = 0
        en = 0
        rows = []
        for pg, text, oe, tr, q in con.execute(
                "SELECT page_no, text, %s, translation, %s FROM passages WHERE doc_id=?%s" % (eng, qcol, scope), (did,)):
            n += 1
            vis += 1 if "vision" in (oe or "").lower() else 0
            has_en = bool((tr or "").strip())
            en += 1 if has_en else 0
            if not has_en and q is not None and float(q) < MIN_QUALITY:
                low += 1
            if len(DEV.findall(text or "")) >= 8:
                dn += 1
                bad += 1 if JUNK.search(text) else 0
            rows.append((pg, text, oe, has_en, q))
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def count(sql):
            try:
                return int(con.execute(sql, (did,)).fetchone()[0] or 0)
            except sqlite3.Error:
                return 0
        hi = count("SELECT COUNT(*) FROM translations_l10n l JOIN passages p ON p.id=l.passage_id "
                   "WHERE p.doc_id=? AND l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>''") \
            if "translations_l10n" in tables else 0
        vectors = count("SELECT COUNT(*) FROM passage_embeddings e JOIN passages p ON p.id=e.passage_id WHERE p.doc_id=?") \
            if "passage_embeddings" in tables else 0
        pictures = count("SELECT COUNT(*) FROM doc_images WHERE doc_id=? AND COALESCE(status,'')<>'retired'") \
            if "doc_images" in tables else 0
        stories = count("SELECT COUNT(*) FROM doc_stories WHERE doc_id=?") if "doc_stories" in tables else 0
    finally:
        con.close()
    share = 100.0 * bad / dn if dn else 0.0
    vshare = 100.0 * vis / n if n else 0.0
    inbox, raw, merged, vision = Path(a.inbox), Path(a.raw), Path(a.merged_dir), Path(a.vision_dir)
    pdfs, rawp, mergedp, visionp = (pages_in(inbox, a.doc, "pdf"), pages_in(raw, a.doc, "jsonl"),
                                    pages_in(merged, a.doc, "jsonl"), pages_in(vision, a.doc, "jsonl"))
    work = Path(a.work)
    man, queue = work / ("%s.json" % a.doc), work / ("%s_queue.txt" % a.doc)
    summary = None
    if man.exists():
        try:
            m = json.loads(man.read_text(encoding="utf-8"))
            summary = dict(m.get("summary") or {}, at=m.get("at"))
        except ValueError:
            summary = None
    queued = len([x for x in queue.read_text(encoding="utf-8").splitlines() if x.strip()]) if queue.exists() else 0
    rec = verdicts(Path(a.verdicts)).get(a.doc)
    state = rec if rec and rec.get("status") in STATES else None
    res.update({
        "passages": n, "english": en, "hindi": hi, "vectors": vectors, "pictures": pictures, "stories": stories,
        "debris_pct": round(share, 1), "vision_pct": round(vshare, 1), "below_quality": low,
        "guard": share > DEBRIS_MAX and vshare < 50.0 and len(pdfs) > 0,
        "pdfs": len(pdfs), "raw_pages": len(rawp), "vision_pages": len(visionp), "merged_pages": len(mergedp),
        "merged_complete": bool(rawp) and rawp <= mergedp, "queued": queued, "consensus": summary,
        "nothing_to_lose": en <= NOTHING_TO_LOSE_EN and hi == 0 and pictures == 0 and stories == 0,
        "aside": state, "state": state,
        "cost_per_page": measured_cost_per_page(a.db, a.doc),   # REINGEST_2026_10_12
        "vision_gave_up": vision_gave_up(work, a.doc),   # READ_IN_2026_10_13
    })
    res["held"] = res["guard"] and not (state and state.get("status") == "translate_as_is")
    untranslated = max(0, n - en)
    res["untranslated"] = untranslated
    res["quality_stuck"] = untranslated > 0 and low >= 0.5 * untranslated
    res["judged"] = judge(rows, vision, a.doc, max_pages=40 if share else 0)
    res["leftovers"] = leftovers(rows) if res["quality_stuck"] else None
    return res


def repair_first(r: dict, doc: str, q: str, tr: str):
    """REPAIR_NEXT_2026_10_17: the debris guard lets a text through (it is under the guard's threshold), but its reading
    is Tesseract's, its debris judged moderate or material and its scan is here. The path (text_path.py,
    PATH_2026_10_12) says repair first; so does this now, with the same reckoning: the pages vision has not read, less
    those it failed on twice, at the price measured on this text where there is one. (why, next, also), or None.
    On 17 Oct the Padma Purana's Patala Khanda was assessed "nothing holds it ... NEXT: translate it" with 146 of its
    364 pages unread by vision (the run had stopped at its cap) and 203 pages of the repair not in the database."""
    j = r.get("judged") or {}
    if j.get("level") not in ("moderate", "material") or float(r.get("vision_pct") or 0) >= 50.0:
        return None
    pdfs, vp, raw = int(r.get("pdfs") or 0), int(r.get("vision_pages") or 0), int(r.get("raw_pages") or 0)
    if not pdfs or pdfs < 0.9 * max(1, raw):
        return None
    gave = int(r.get("vision_gave_up") or 0)
    todo = max(0, pdfs - vp - gave)
    stale = int((r.get("consensus") or {}).get("stale") or 0)
    then = "then: " + tr
    if todo:
        cpp = float(r.get("cost_per_page") or COST_PER_PAGE)
        cap = max(1.0, math.ceil(todo * cpp * 1.25 * 10) / 10.0)
        why = ("but its reading is Tesseract's and its debris %s: repair first, as its path says, so that the English is "
               "made from a clean reading; vision has read %d of its %d pages%s, %d to go, about $%.2f at $%.4f a page"
               % (j["level"], vp, pdfs, (" (%d left to Tesseract: vision failed on them twice)" % gave) if gave else "",
                  todo, todo * cpp, cpp))
        also = ([REINGEST % doc + "   (the %d page(s) of the repair that differ from the database can go in now)" % stale]
                if stale else []) + [then]
        return (why, q + " --repair --max-usd %.2f   (the pages vision has not read; it stops before spending more)" % cap,
                also)
    if stale:
        return ("but %d page(s) of its repair differ from the database: they go in first" % stale, REINGEST % doc, [then])
    return None


def advise(r: dict, doc: str):
    """(verdict, next, also) for the assessment."""
    q = 'python scripts\\repair_text.py --doc %s' % doc
    tr = "translate it: Finish EN and Add Hindi in the Library (unchanged passages come from the cache at no cost)"
    if r.get("error"):
        return r["error"], "", []
    st = r.get("state") or {}
    s_at, s_why = str(st.get("at") or "?")[:10], st.get("reason") or "?"
    status = st.get("status")
    if status == "set_aside":
        return ("set aside on %s: %s. A better scan is wanted; its files are kept." % (s_at, s_why),
                q + " --restore   (when a better scan is in the inbox)", [q + " --find-source"])
    if status == "withdrawn":   # PATH_2026_10_12
        return ("withdrawn from the site on %s: %s. The site has retired its passages; they are kept here, out of Ask the "
                "Corpus, until a better source replaces them" % (s_at, s_why), q + " --find-source",
                [q + " --restore   (send it to the site again as it is)"])
    if status == "complete":
        return ("accepted as complete on %s: %s. %d of %d passages have English; what is left is not translated."
                % (s_at, s_why, r["english"], r["passages"]), "", [q + " --restore"])
    if status == "in_repair":
        enb, hib = int(st.get("en_before") or 0), int(st.get("hi_before") or 0)
        # held by hand after the re-ingest, the counts before are not known: then 90% of the passages
        t_en = enb or int(0.9 * r["passages"])
        t_hi = hib or int(0.9 * t_en)
        ready = r["english"] >= 0.95 * t_en and r["hindi"] >= 0.95 * t_hi
        v = ("in repair since %s (%s): the site keeps its last version. English now %d of %d (was %d), Hindi %d (was %d)"
             % (s_at, s_why, r["english"], r["passages"], enb, r["hindi"], hib))
        if ready:
            return v + "; the translation is back: publish it", q + " --release", []
        return v, tr, [q + " --release   (publish it as it is)"]
    j = r.get("judged") or {}
    jx = explain(j)
    if status == "translate_as_is" and r["untranslated"]:
        return ("to be translated as is (since %s: %s); the debris guard lets it through" % (s_at, s_why), tr,
                [q + " --restore"])
    if r["held"]:
        why = ("held by the OCR-debris guard (%.0f%% of its verses carry Latin letters, %.0f%% from vision OCR)"
               % (r["debris_pct"], r["vision_pct"]))
        if j.get("level") == "cosmetic":
            return (why + "; but the debris is cosmetic: " + jx, q + ' --as-is "debris judged cosmetic"',
                    [q + " --repair   (for the critical edition)"] if r["pdfs"] else [])
        also = [q + ' --as-is "debris judged moderate: translate now, repair for the edition"'] \
            if j.get("level") == "moderate" else [q + " --find-source"]
    elif r["quality_stuck"]:
        lo = r.get("leftovers") or {}
        if lo.get("below") and lo.get("not_sanskrit", 0) >= 0.7 * lo["below"]:
            return ("what is left is not Sanskrit: of the %d untranslated verses below the OCR bar, %d are English or Latin "
                    "pages read as Devanagari or Latin and %d are lone dandas and numbers; %d of %d passages have English"
                    % (lo["below"], lo["misread_english"] + lo["latin"], lo["punctuation"], r["english"], r["passages"]),
                    q + ' --accept "what is left is not Sanskrit"', [q + " --repair"] if r["pdfs"] else [])
        why = "%d of its untranslated verses are below the OCR quality bar" % r["below_quality"]
        also = [q + " --find-source"]
    else:
        v = ("nothing holds it: %d passages, %d with English, %d with Hindi; debris %.0f%%, vision %.0f%%"
             % (r["passages"], r["english"], r["hindi"], r["debris_pct"], r["vision_pct"]))
        rf = repair_first(r, doc, q, tr)   # REPAIR_NEXT_2026_10_17: as the path, repair first
        if rf:
            return (v + "; " + rf[0], rf[1], rf[2])
        return (v, tr if r["untranslated"] or r["hindi"] < r["english"] else "", [])
    if not r["pdfs"]:
        return (why + "; its page PDFs are not in the inbox, so it cannot be repaired here",
                q + ' --set-aside "needs a better scan"   (or put its page PDFs back in the inbox)', [q + " --find-source"])
    s = r.get("consensus") or {}
    if not r["merged_complete"]:
        pages = r["queued"] or r["pdfs"]
        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        gave = int(r.get("vision_gave_up") or 0)   # READ_IN_2026_10_13
        left = max(0, left - gave)
        cap = max(1.0, math.ceil(left * cpp * 1.25 * 10) / 10.0)   # PATH_2026_10_12: a cap the estimate fits under
        if (r["vision_pages"] >= 0.8 * max(1, r["pdfs"]) and
                (r.get("merged_pages") or 0) >= 0.95 * max(1, r.get("raw_pages") or r["pdfs"])):
            # READ_IN_2026_10_13: the scan is read (the Natyasastra: 513 of 546 pages, 538 merged; the merge leaves
            # out blank pages, so it is never "complete"): the pages read go in now, in place
            more = ([q + " --repair --max-usd %.2f   (the %d page(s) vision has not read yet; after)" % (cap, left)]
                    if left else [])
            return (why + "; vision has read %d of its %d pages%s and %d are merged: they can go in now; the others keep "
                    "Tesseract's reading" % (r["vision_pages"], r["pdfs"],
                                             (" (%d left to Tesseract: vision failed on them twice)" % gave) if gave else "",
                                             r.get("merged_pages") or 0),
                    REINGEST % doc, more + also)
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
                q + " --repair --max-usd %.2f   (it stops before spending more)" % cap, also)
    if r["queued"] and r["vision_pages"] < 0.8 * r["queued"]:
        return (why + "; vision read only %d of the %d queued pages: the scan resists repair" % (r["vision_pages"], r["queued"]),
                q + ' --set-aside "needs a better scan"   (or --repair again for the pages that failed)',
                [q + " --repair", q + " --find-source"])
    if (s.get("stale") or 0) or (s.get("missing-in-db") or 0):
        lose = ("nothing is lost" if r["nothing_to_lose"] else
                "it replaces %d English translations; %d Hindi rows, %d vectors, %d pictures and %d stories point "
                "at the old passages" % (r["english"], r["hindi"], r["vectors"], r["pictures"], r["stories"]))
        nxt = q + " --use-repaired" + ("" if r["nothing_to_lose"] else " --replace %d" % r["english"])
        if not r["nothing_to_lose"]:   # REINGEST_2026_10_12: only the pages that changed
            also = [REINGEST % doc] + also
        return (why + "; the repaired text is ready (%s pages differ from the database); %s" % (s.get("stale", 0), lose),
                nxt, also)
    if s:
        return (why + "; the database already holds the repaired text, and it is still held: the repair did not help",
                q + ' --set-aside "needs a better scan"', [q + " --find-source"])
    return (why + "; the repaired pages are on disk but not yet compared with the database",
            q + " --repair   (compares them; costs nothing for pages already read)", also)


def write_judged(a, r: dict, verdict: str, nxt: str, also: list):
    """JUDGE_DESK_2026_10_11: the last assessment of a text, for the Library's cards and the Sources page
    (data/source_judged/<doc>.json). Small, rewritten on every assessment; never the database."""
    if a is None or not getattr(a, "judged_dir", None):
        return
    j = r.get("judged") or {}
    rec = {"doc": r["doc"], "mark": "JUDGE_DESK_2026_10_11", "at": datetime.datetime.now().isoformat(timespec="seconds"),
           "level": j.get("level"), "judged": explain(j) if j.get("verses") and r.get("debris_pct") else "",
           "verdict": verdict, "next": nxt, "also": also, "state": (r.get("state") or {}).get("status")}
    for k in ("misread_pct", "misread_letters_pct", "furniture_pct", "notes_pct", "numbering_pct", "agree_median",
              "agree_pages", "misread_top", "furniture_top"):
        if k in j:
            rec[k] = j[k]
    for k in ("passages", "english", "hindi", "pictures", "debris_pct", "vision_pct", "below_quality", "guard", "held",
              "quality_stuck", "pdfs", "vision_pages", "merged_pages"):
        rec[k] = r.get(k)
    try:
        d = Path(a.judged_dir); d.mkdir(parents=True, exist_ok=True)
        t = d / ("%s.json.part" % r["doc"])
        t.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(t, d / ("%s.json" % r["doc"]))
    except OSError as e:
        print("  note: the judgement was not cached (%s)" % e)


def report(r: dict, doc: str, a=None) -> int:
    if r.get("error"):
        print("VERDICT: " + r["error"]); print("NEXT: "); return 1
    print("%s  %s  %s" % (doc, MARK, HEAL))
    print("  passages %(passages)d | English %(english)d | Hindi %(hindi)d | vectors %(vectors)d | pictures %(pictures)d "
          "| stories %(stories)d" % r)
    print("  debris %(debris_pct).1f%% | vision %(vision_pct).1f%% | below the OCR bar (untranslated) %(below_quality)d" % r)
    print("  page PDFs %(pdfs)d | Tesseract pages %(raw_pages)d | vision pages %(vision_pages)d | repaired pages "
          "%(merged_pages)d | queued for vision %(queued)d" % r)
    if r.get("consensus"):
        c = r["consensus"]
        print("  last drift check %s: current %s, stale %s, missing %s" % (c.get("at"), c.get("current"), c.get("stale"),
                                                                           c.get("missing-in-db")))
    j = r.get("judged") or {}
    if j.get("verses") and r["debris_pct"]:
        print("  debris judged %s: misread %.1f%% of verses (%.2f%% of letters) | furniture %.1f%% | notes %.1f%% | "
              "numbering %.1f%%" % (j["level"].upper(), j["misread_pct"], j["misread_letters_pct"], j["furniture_pct"],
                                    j["notes_pct"], j["numbering_pct"]))
        if j.get("misread_top"):
            print("    misread runs: " + ", ".join(j["misread_top"]))
        if j.get("furniture_top"):
            print("    furniture: " + "; ".join(j["furniture_top"]))
        if j.get("agree_pages"):
            print("    vision agreement: median %.3f, lowest tenth %.3f, on %d pages" % (j["agree_median"], j["agree_p10"],
                                                                                         j["agree_pages"]))
        print("JUDGED: " + explain(j))
    lo = r.get("leftovers")
    if lo:
        print("  below the OCR bar: %(below)d | English pages read as Devanagari %(misread_english)d | lone dandas and "
              "numbers %(punctuation)d | Latin %(latin)d" % lo)
    v, n, also = advise(r, doc)
    write_judged(a, r, v, n, also)
    print("VERDICT: " + v)
    print("NEXT: " + n)
    for x in also:
        print("ALSO: " + x)
    return 0


def run(argv, keep=None, env_extra=None) -> int:
    """Run one step. Its children print unbuffered, so the dashboard's Log follows a long vision run
    page by page. With keep=[], its lines are also kept, to read its refusals."""
    print("$ " + " ".join(str(x) for x in argv), flush=True)
    env = dict(os.environ, PYTHONUNBUFFERED="1", **(env_extra or {}))
    if keep is None:
        return subprocess.call([str(x) for x in argv], cwd=str(ROOT), env=env)
    p = subprocess.Popen([str(x) for x in argv], cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for line in p.stdout:
        sys.stdout.write(line); sys.stdout.flush(); keep.append(line)
    return p.wait()


def dashboard_jobs():
    """The dashboard's unfinished jobs, or None when it does not answer."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(DASHBOARD + "/api/jobs/running", timeout=6) as f:
            return json.loads(f.read().decode("utf-8")).get("running") or []
    except Exception:
        return None


def writers_running(from_dashboard: bool, doc: str = "", jobs=None):
    """The dashboard's jobs that may write the database: every job but an OCR (page files only). Run by
    hand, a queued job counts too (it may start meanwhile). As the dashboard's own job this runs under
    its translate lock, so only other jobs executing now count, and the repair jobs themselves do not;
    a vision repair of this same text does count (it writes the pages this reads). None when the
    dashboard does not answer."""
    jobs = dashboard_jobs() if jobs is None else jobs
    if jobs is None:
        return None
    w = [j for j in jobs if j.get("kind") != "ocr"]
    if from_dashboard:
        w = [j for j in w if j.get("state") == "running" and (not str(j.get("kind", "")).startswith("repair") or (
            j.get("kind") == "repair" and j.get("mode") == "repair" and j.get("doc") == doc))]
    return w


def write_state(a, status: str, reason: str = "", **extra) -> dict:
    rec = {"doc": a.doc, "status": status, "reason": (reason or "")[:300],
           "at": datetime.datetime.now().isoformat(timespec="seconds"), "by": "repair_text.py", "mark": HEAL}
    rec.update(extra)
    p = Path(a.verdicts)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def use_repaired(a, r: dict) -> int:
    doc = a.doc
    if r.get("error"):
        print("REFUSE: " + r["error"]); return 1
    if not r["merged_complete"]:
        print("REFUSE: the repaired text covers %d of %d pages; run --repair first." % (r["merged_pages"], r["raw_pages"]))
        print("VERDICT: not ready"); print("NEXT: python scripts\\repair_text.py --doc %s --repair" % doc); return 1
    if not r["nothing_to_lose"] and (a.replace is None or a.replace < r["english"]):
        print("REFUSE: this replaces %d English translations (%d Hindi rows, %d vectors, %d pictures, %d stories point at "
              "the old passages). Say so: --replace %d" % (r["english"], r["hindi"], r["vectors"], r["pictures"],
                                                          r["stories"], r["english"]))
        print("VERDICT: a decision is needed")
        print("NEXT: python scripts\\repair_text.py --doc %s --use-repaired --replace %d" % (doc, r["english"]))
        print("ALSO: " + REINGEST % doc)   # REINGEST_2026_10_12
        return 1
    w = writers_running(a.from_dashboard, doc)
    if w:
        print("REFUSE: the dashboard runs a database writer or a vision repair of this text: %s. Wait for it, or run "
              "this from the Library." % ", ".join("%s %s" % (j.get("kind"), j.get("doc")) for j in w))
        print("VERDICT: not now: another job is running"); print("NEXT: python scripts\\repair_text.py --doc %s" % doc)
        return 1
    # every repaired page must be readable before anything is deleted
    rx = page_rx(doc, "jsonl")
    for p in sorted(Path(a.merged_dir).iterdir()):
        if rx.match(p.name):
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
            except (OSError, ValueError) as e:
                print("REFUSE: %s does not read (%s); nothing was changed." % (p, e)); return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(a.backup_dir) / ("context_pre_repair_%s_%s.db" % (doc, stamp))
    if run([PY, SCRIPTS / "db_backup.py", a.db, backup]) != 0 or not backup.exists():
        print("REFUSE: the backup failed; nothing was changed."); return 1
    held = not r["nothing_to_lose"]
    if held:   # REPAIR_HEAL_2026_10_11: the site keeps its version until the new one is translated
        write_state(a, "in_repair", "re-translating after the repair", en_before=r["english"], hi_before=r["hindi"],
                    backup=str(backup))
    steps = [
        [PY, SCRIPTS / "wipe_doc.py", "--db", a.db, "--doc", doc, "--yes"],
        [PY, SCRIPTS / "ingest_jsonl_fast.py", "--doc", doc, "--glob", str(Path(a.raw) / ("%s_*.jsonl" % doc)), "--db", a.db],
        [PY, SCRIPTS / "classify_doc.py", "--doc", doc, "--db", a.db, "--apply"],
    ]
    for i, s in enumerate(steps):
        if run(s) != 0:
            print("FAILED at step %d of %d. The backup made before is %s. To put the database back: stop the "
                  "dashboard (scripts\\restart_dashboard.ps1 -Stop), then copy the backup over data\\context.db, then "
                  "start it again." % (i + 1, len(steps), backup))
            print("VERDICT: the re-ingest failed; restore from %s" % backup)
            print("NEXT: ")
            return 1
    rc = run([PY, SCRIPTS / "ocr_consensus.py", "--doc", doc, "--drift-only"],
             env_extra={"SA_CONSENSUS_SELF_KIND": "repair,repair_use"})
    r2 = assess(a)
    print("  now: passages %s | English %s | Hindi %s | debris %s%% | vision %s%%"
          % (r2.get("passages"), r2.get("english"), r2.get("hindi"), r2.get("debris_pct"), r2.get("vision_pct")))
    print("VERDICT: the repaired text is in the database%s; backup %s%s"
          % ("" if rc == 0 else " (the drift check still finds pages to look at)", backup,
             "; the site keeps its last version until you publish it" if held else ""))
    print("NEXT: translate it: Finish EN and Add Hindi in the Library (the translation cache answers unchanged "
          "passages at no cost)")
    if held:
        print("ALSO: python scripts\\repair_text.py --doc %s --release   (publish it to the site when translated)" % doc)
    return 0


def say_state(a, rec: dict) -> int:
    doc, st = a.doc, rec["status"]
    q = "python scripts\\repair_text.py --doc %s" % doc
    msg = {
        "set_aside": ("%s set aside: %s. Its files are kept; the Library stops offering its translation." % (doc, rec["reason"]),
                      "put a better scan's page PDFs in the inbox (OCR them), then %s --restore" % q),
        "withdrawn": ("%s withdrawn from the site: %s. At the next mirror run the site retires its passages, English and "
                      "Hindi (--restore brings them back); they are kept here, and Ask the Corpus here leaves them out."
                      % (doc, rec["reason"]), "%s --find-source   (a critical e-text or a better scan)" % q),   # PATH_2026_10_12
        "translate_as_is": ("%s is to be translated as is: %s. The debris guard lets it through." % (doc, rec["reason"]),
                            "translate it: Finish EN and Add Hindi in the Library"),
        "complete": ("%s accepted as complete: %s. The Library stops offering what is left." % (doc, rec["reason"]), ""),
        "in_repair": ("%s held from the site: %s. The site keeps its last version until it is published." % (doc, rec["reason"]),
                      "translate it: Finish EN and Add Hindi in the Library"),
        "restored": ("%s restored: the Library offers it again, and the debris guard judges it again." % doc, q),
        "released": ("%s published: the next mirror run sends it to the site." % doc, ""),
    }[st]
    print("VERDICT: " + msg[0]); print("NEXT: " + msg[1])
    if st == "in_repair":
        print("ALSO: %s --release   (publish it to the site when translated)" % q)
    return 0


def judge_all(a) -> int:
    """JUDGE_DESK_2026_10_11: every text with untranslated passages, or a state in the register, assessed and
    judged (read-only), each cached for the Library's cards and the Sources page."""
    try:
        con = sqlite3.connect("file:%s?mode=ro" % Path(a.db).as_posix(), uri=True, timeout=10)
    except sqlite3.Error as e:
        print("VERDICT: cannot open %s read-only: %s" % (a.db, e)); print("NEXT: "); return 1
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        scope = " AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else ""
        rows = con.execute("SELECT d.code, COUNT(p.id), SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END) "
                           "FROM docs d JOIN passages p ON p.doc_id=d.id%s GROUP BY d.code" % scope).fetchall()
    finally:
        con.close()
    reg = {d for d, r in verdicts(Path(a.verdicts)).items() if r.get("status") in STATES}
    todo = sorted(code for code, n, en in rows if code and not code.endswith("-RETIRED")
                  and ((n or 0) > (en or 0) or code in reg))
    counts, out = {}, []
    t0 = datetime.datetime.now()
    for i, code in enumerate(todo, 1):
        a.doc = code
        r = assess(a)
        if r.get("error"):
            continue
        v, n, also = advise(r, code)
        write_judged(a, r, v, n, also)
        lvl = (r.get("judged") or {}).get("level") if r.get("debris_pct") else "-"
        counts[lvl] = counts.get(lvl, 0) + 1
        out.append((code, r, lvl, v))
        j = r.get("judged") or {}   # ETEXT_WITNESS_2026_10_11 (judge v2): each kind of debris
        print("  [%d/%d] %-56s %-9s debris %5.1f%% (misread %4.1f%% of verses, %4.2f%% of letters; furniture %4.1f%%; "
              "notes %4.1f%%) | %s" % (i, len(todo), code[:56], lvl, r["debris_pct"], j.get("misread_pct", 0),
                                       j.get("misread_letters_pct", 0), j.get("furniture_pct", 0), j.get("notes_pct", 0),
                                       v[:70]), flush=True)
    held = sum(1 for _, r, _, _ in out if r.get("held"))
    print("VERDICT: judged %d text(s) in %ds: %d material, %d moderate, %d cosmetic, %d without debris; %d held by the guard"
          % (len(out), (datetime.datetime.now() - t0).seconds, counts.get("material", 0), counts.get("moderate", 0),
             counts.get("cosmetic", 0), counts.get("-", 0), held))
    print("NEXT: open the Sources page (http://127.0.0.1:5057/sources) or each text's repair page")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The repair path for one text (REPAIR_PATH_2026_10_10, REPAIR_HEAL_2026_10_11)")
    ap.add_argument("--doc")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--inbox", default="inbox")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--vision-dir", default="data/raw_vision")
    ap.add_argument("--merged-dir", default="data/raw_merged")
    ap.add_argument("--work", default="data/ocr_consensus")
    ap.add_argument("--verdicts", default="data/source_verdicts.jsonl")
    ap.add_argument("--backup-dir", default=os.environ.get("SA_BACKUP_DIR") or r"D:\backups")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--repair", action="store_true")
    g.add_argument("--use-repaired", action="store_true")
    g.add_argument("--set-aside", metavar="REASON")
    g.add_argument("--as-is", metavar="REASON", help="translate as is: the debris guard lets this text through")
    g.add_argument("--accept", metavar="REASON", help="what is left of this text is not to be translated")
    g.add_argument("--hold", metavar="REASON", nargs="?", const="re-translating after the repair",
                   help="the site keeps its last version of this text (corpus_sync.py skips it)")
    g.add_argument("--release", action="store_true", help="publish the text to the site again")
    g.add_argument("--withdraw", metavar="REASON", help="PATH_2026_10_12: take the text off the site (the mirror retires "
                   "it there) and out of Ask the Corpus, keeping it here; --restore undoes it")
    g.add_argument("--find-source", action="store_true", help="look for a better edition (scripts/source_desk.py)")
    g.add_argument("--restore", action="store_true")
    g.add_argument("--list", action="store_true")
    g.add_argument("--judge-all", action="store_true", help="assess and judge every text with something untranslated or "
                   "a state in the register; cache each for the Library and the Sources page")
    ap.add_argument("--replace", type=int, default=None, help="with --use-repaired: the English translations it replaces")
    ap.add_argument("--max-usd", type=float, default=1.00)
    ap.add_argument("--ai", action="store_true", help="with --find-source: let the AI judge the editions (about $0.002)")
    ap.add_argument("--force", action="store_true", help="with --release: publish even before the translation is back")
    ap.add_argument("--judged-dir", default="data/source_judged")
    ap.add_argument("--threshold", type=float, default=None, help="OCR confidence below which a page goes to vision "
                    "(default: 101, every page, when held by the guard; else 72)")
    ap.add_argument("--from-dashboard", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    os.chdir(ROOT)
    if a.judge_all:
        return judge_all(a)
    if a.list:
        v = [r for r in verdicts(Path(a.verdicts)).values() if r.get("status") in STATES]
        for r in sorted(v, key=lambda x: x.get("at", "")):
            print("%s  %-16s %s  %s" % (r.get("at", "?")[:16], r.get("status"), r["doc"], r.get("reason", "")))
        print("VERDICT: %d text(s) not in the ordinary state (%d set aside)"
              % (len(v), sum(1 for r in v if r.get("status") == "set_aside")))
        print("NEXT: "); return 0
    if not a.doc or not re.match(r"^[A-Za-z0-9_\-]+$", a.doc):
        print("FAIL: --doc <code> is needed (letters, digits, _ and -)."); return 2
    for flag, status in (("set_aside", "set_aside"), ("as_is", "translate_as_is"), ("accept", "complete"),
                         ("hold", "in_repair"), ("withdraw", "withdrawn")):   # PATH_2026_10_12: withdraw
        reason = getattr(a, flag)
        if reason is not None:
            extra = {}
            if status == "in_repair":
                r0 = assess(a)
                extra = {"en_before": r0.get("english", 0), "hi_before": r0.get("hindi", 0)}
            return say_state(a, write_state(a, status, reason or {"set_aside": "needs a better scan"}.get(status, ""), **extra))
    if a.restore:
        return say_state(a, write_state(a, "restored"))
    if a.release:
        # JUDGE_DESK_2026_10_11: publishing a text whose translation is not back would put it on the site
        # without its English (as on 11 Oct, 19:47); say so, unless --force
        cur = verdicts(Path(a.verdicts)).get(a.doc) or {}
        if not a.force and cur.get("status") != "witness":   # BENCHMARK_2026_10_11: nothing to publish
            r00 = assess(a)
            if r00.get("error"):
                print("REFUSE: %s: %s; nothing is published. --force writes the record all the same." % (a.doc, r00["error"]))
                print("VERDICT: not published: %s is not in the database" % a.doc); print("NEXT: ")
                return 1
        if cur.get("status") in ("in_repair", "witness") and not a.force:   # ETEXT_WITNESS_2026_10_11: a witness too
            r0 = assess(a)
            if r0.get("error") and cur.get("status") == "witness":
                print("REFUSE: %s is a witness not yet in the database: ingest it (python scripts\\etext_witness.py "
                      "--doc %s --ingest --witness %s), then translate it" % (a.doc, cur.get("of") or "?", a.doc))
                print("VERDICT: a witness, not yet ingested"); print("NEXT: ")
                return 1
            if not r0.get("error"):
                enb, hib = int(cur.get("en_before") or 0), int(cur.get("hi_before") or 0)
                t_en = enb or int(0.9 * r0["passages"]); t_hi = hib or int(0.9 * t_en)
                if r0["english"] < 0.95 * t_en or r0["hindi"] < 0.95 * t_hi:
                    print("REFUSE: not yet: English %d of %d passages (it had %d), Hindi %d (it had %d). Publishing now puts "
                          "it on the site without its translation. Translate it first, or add --force to publish it as "
                          "it is." % (r0["english"], r0["passages"], enb, r0["hindi"], hib))
                    print("VERDICT: still in repair: the translation is not back (English %d, Hindi %d)" % (r0["english"], r0["hindi"]))
                    print("NEXT: translate it: Finish EN and Add Hindi in the Library")
                    return 1
        return say_state(a, write_state(a, "released"))
    if a.find_source:
        argv2 = [PY, SCRIPTS / "source_desk.py", "--doc", a.doc, "--db", a.db]
        if a.ai:
            argv2 += ["--ai"]
        return run(argv2)
    r = assess(a)
    if a.repair:
        if r.get("error"):
            print("REFUSE: " + r["error"]); return 1
        thr = a.threshold if a.threshold is not None else (101 if r["guard"] else 72)
        out = []
        # REPAIR_HEAL_2026_10_11: ocr_consensus.py refuses while the dashboard runs a job for this text;
        # this repair is such a job (kind "repair"), so it is told to look past it
        rc = run([PY, SCRIPTS / "ocr_consensus.py", "--doc", a.doc, "--threshold", thr, "--include-unassessed",
                  "--yes", "--max-usd", "%.2f" % a.max_usd], keep=out, env_extra={"SA_CONSENSUS_SELF_KIND": "repair"})
        text = "".join(out)
        m = re.search(r"REFUSING: estimate \$([0-9.]+) exceeds --max-usd", text)
        if rc not in (0, 3) and m:
            est = float(m.group(1))
            print("VERDICT: the vision meter estimates $%.2f for the pages left, above the cap of $%.2f; nothing was "
                  "spent (it prices a new text from the corpus's recent pages; Karan Aagama cost a tenth of its "
                  "estimate)" % (est, a.max_usd))
            print("NEXT: python scripts\\repair_text.py --doc %s --repair --max-usd %.2f" % (a.doc, math.ceil(est * 110) / 100.0))
            return 1
        if rc not in (0, 3) and "stop them first" in text:
            print("VERDICT: ocr_consensus.py saw this repair as a job in its way: it is older than REPAIR_HEAL_2026_10_11 "
                  "(apply scripts\\patch_repair_heal_2026_10_11.py), or another job for this text runs")
            print("NEXT: python scripts\\repair_text.py --doc %s" % a.doc)
            return 1
        if rc not in (0, 3):
            print("VERDICT: the repair stopped (ocr_consensus.py exit %d): its lines above say why" % rc)
            print("NEXT: python scripts\\repair_text.py --doc %s" % a.doc)
            return 1
        return report(assess(a), a.doc, a)
    if a.use_repaired:
        return use_repaired(a, r)
    return report(r, a.doc, a)


if __name__ == "__main__":
    sys.exit(main())
