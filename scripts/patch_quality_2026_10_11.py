#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_quality_2026_10_11.py  (2026-10-11)  QUALITY_2026_10_11

Are we sure of the texts? Asked on 11 Oct, after the first benchmarks: "are we sure about our results and the
quality of the texts, their translation". Not yet, and three things measured that night say where:

  1. The repair took Tesseract's garbage on plates and title pages. Where vision rightly read nothing or a line
     (a yantra, a figure, a title page), the merge fell back to Tesseract, whose text there is the garbage it makes
     of the picture: 19 pages in 5 texts (7 in the Tantric Texts, 7 in Karan, 3 in the Shatapatha, 1 each in the
     Rgveda vol. ii and the Mallapurana). The Tantric Texts' repair has noise in 3.3% of its Devanagari words where vision alone has 0.9%;
     Karan's 1.9% against 0.07%. merge_ocr_sources.py now uses Tesseract only where it read Devanagari or English;
     elsewhere vision's line is kept, or the page is written blank (measured on the page files: the Tantric Texts
     0.9%, Karan 0.2%). ocr_consensus.py's drift counts a blank page current when the database has nothing for it,
     stale when it still has the garbage.
  2. The benchmark measured Latin debris only. archive.org's OCR of the 1960 Bodhicaryavatara has no Latin and noise
     in 9.4% of its words (our Tesseract 5.6%); it was called "the better reading: make it a witness". etext_witness.py
     now measures the Devanagari itself (words with a Latin letter or a stray mark glued on, malformed words, stray
     marks; and the plausibility of its letter trigrams against the BORI Adiparvan from GRETIL, which has none of
     that noise); the benchmark compares readings by all three, and calls neither clean when both are damaged; the
     witness refuses to be written from a text no cleaner than Tesseract (noise over 3% of its words) unless --force;
     a scan too damaged to have readable pages is measured by all its pages. The vision model's "V" for a printed
     pratika mark (the Rgveda vol. ii: 8,602 words on 230 of its 446 vision pages) is counted and shown.
  3. The translation's figures are structural. The heuristic QA (0.93-0.995) measures length, residue and script,
     not meaning; no LLM judge has read these texts. The benchmark now says so, and how much of the English was
     made from passages whose Devanagari is noise.
  source_desk.py: loads .env (the AI judge said "GEMINI_API_KEY is not set"); an archive.org error on a fetch is
    a verdict, not a traceback; a link to the Digital Sanskrit Buddhist Canon, also an e-text host for
    etext_witness.py --url.
  dashboard.py (on a restart): the benchmark's noise and plausibility on the repair page and on /benchmarks.

Needs BENCHMARK_2026_10_11 (etext_witness.py, benchmark_sources.py, dashboard.py), ETEXT_WITNESS_2026_10_11
(source_desk.py), REPAIR_HEAL_2026_10_11 (ocr_consensus.py). Anchored, all-or-nothing, marker-idempotent per file;
keeps line endings and encodings; each .py is compiled before it replaces the original; backups .bak_quality_<date>.
  python scripts\\patch_quality_2026_10_11.py --check
  python scripts\\patch_quality_2026_10_11.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "QUALITY_2026_10_11"
NEEDS = {"scripts/etext_witness.py": "BENCHMARK_2026_10_11", "scripts/benchmark_sources.py": "BENCHMARK_2026_10_11",
         "scripts/merge_ocr_sources.py": "DEFINITELY_EMPTY", "scripts/ocr_consensus.py": "REPAIR_HEAL_2026_10_11",
         "scripts/source_desk.py": "ETEXT_WITNESS_2026_10_11", "scripts/dashboard.py": "BENCHMARK_2026_10_11"}
FILES = list(NEEDS)

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/etext_witness.py', 1,
     r'''
UA = {"User-Agent": "SanskritAutomaton-EtextWitness/1.0 (scholarly, non-commercial)"}
HOSTS = ["gretil.sub.uni-goettingen.de", "sanskritdocuments.org", "archive.org", "raw.githubusercontent.com"] + [
    h.strip().lower() for h in (os.environ.get("SA_ETEXT_HOSTS") or "").split(",") if h.strip()]
MAX_BYTES = 40_000_000
''',
     r'''
UA = {"User-Agent": "SanskritAutomaton-EtextWitness/1.0 (scholarly, non-commercial)"}
HOSTS = ["gretil.sub.uni-goettingen.de", "sanskritdocuments.org", "archive.org", "raw.githubusercontent.com",
         "dsbcproject.org"] + [   # QUALITY_2026_10_11: the Digital Sanskrit Buddhist Canon
    h.strip().lower() for h in (os.environ.get("SA_ETEXT_HOSTS") or "").split(",") if h.strip()]
MAX_BYTES = 40_000_000
''')
edit('scripts/etext_witness.py', 2,
     r'''                       "text": "\n".join(verses[i]["text"] for i in range(v0, v1 + 1))[:4000], "note": ""})
    return {"pages": res, "scan_pages": len(pages_all), "readable": len(readable_pages), "matched": len(matched),
            "coverage": round(cov, 3), "order": round(order, 3), "span": span, "verses": n_v, "offers": offers,
            "verses_per_page": round(vpp, 2)}
''',
     r'''                       "text": "\n".join(verses[i]["text"] for i in range(v0, v1 + 1))[:4000], "note": ""})
    return {"pages": res, "scan_pages": len(pages_all), "readable": len(readable_pages), "matched": len(matched),
            "matched_readable": len([p for p in readable_pages if res[p]["status"] == "match"]),   # QUALITY_2026_10_11
            "coverage": round(cov, 3), "order": round(order, 3), "span": span, "verses": n_v, "offers": offers,
            "verses_per_page": round(vpp, 2)}
''')
edit('scripts/etext_witness.py', 3,
     r'''    if m is None:
        return "the scan is not in the database: nothing to measure; the witness can still be its own text"
    if m["readable"] < 3:
        return ("the scan has %d readable page(s) of %d: too few to tell whether it is the same text; the witness "
                "can stand in for it" % (m["readable"], m["scan_pages"]))
    if m["coverage"] >= 0.6 and m["order"] >= 0.8:
        return "the same work, in the same order: it reads %d of the scan's %d readable pages (%.0f%%, in order %.0f%%)" % (
            m["matched"], m["readable"], 100 * m["coverage"], 100 * m["order"])
    if m["coverage"] >= 0.25:
        return ("the same work in part, or another recension: it reads %d of %d readable pages (%.0f%%, in order %.0f%%)"
                % (m["matched"], m["readable"], 100 * m["coverage"], 100 * m["order"]))
    lv = judged_level(doc)
    return ("not the same text as the scan, or the scan is too garbled to tell (%d of %d readable pages read%s)"
            % (m["matched"], m["readable"], "; its debris is judged %s" % lv if lv else ""))


''',
     r'''    if m is None:
        return "the scan is not in the database: nothing to measure; the witness can still be its own text"
    mr, rd, n = m.get("matched_readable", m["matched"]), m["readable"], m["scan_pages"]
    if rd < max(3, 0.1 * n):
        # QUALITY_2026_10_11: a scan this damaged is measured by all its pages; the witness still finds a damaged
        # page when enough of its letters survive (on 11 Oct the Bodhicaryavatara read 3 of 253 pages, and
        # "159 of 3 readable pages" was printed)
        share = m["matched"] / float(n) if n else 0.0
        if m["matched"] >= 10 and share >= 0.5 and m["order"] >= 0.8:
            return ("the same work, in the same order, by the scan's damaged pages: the scan reads %d of its %d pages, and "
                    "the witness still finds %d of them (%.0f%%, in order %.0f%%)" % (rd, n, m["matched"], 100 * share,
                                                                                   100 * m["order"]))
        if m["matched"] >= 10 and share >= 0.2:
            return ("probably the same work, in part: the scan reads %d of its %d pages, and the witness finds %d of them "
                    "(%.0f%%, in order %.0f%%)" % (rd, n, m["matched"], 100 * share, 100 * m["order"]))
        return ("the scan reads %d of its %d pages: too few to tell whether it is the same text (the witness finds %d); "
                "the witness can stand in for it" % (rd, n, m["matched"]))
    if m["coverage"] >= 0.6 and m["order"] >= 0.8:
        return "the same work, in the same order: it reads %d of the scan's %d readable pages (%.0f%%, in order %.0f%%)" % (
            mr, rd, 100 * m["coverage"], 100 * m["order"])
    if m["coverage"] >= 0.25:
        return ("the same work in part, or another recension: it reads %d of %d readable pages (%.0f%%, in order %.0f%%)"
                % (mr, rd, 100 * m["coverage"], 100 * m["order"]))
    lv = judged_level(doc)
    return ("not the same text as the scan, or the scan is too garbled to tell (%d of %d readable pages read%s)"
            % (mr, rd, "; its debris is judged %s" % lv if lv else ""))


# ---- the Devanagari judged (QUALITY_2026_10_11) ---------------------------------------------------
# A reading can be free of Latin letters and still be noise: archive.org's OCR of the 1960 Bodhicaryavatara
# has no Latin, and noise in 9.4% of its words (malformed 3.2%, stray marks 5.5%). Three measures; the first two need
# no reference text:
#   glued      a Latin letter or a stray mark stuck to Devanagari in one word: the vision model's "V" for
#              a printed pratika mark (Rgveda vol. ii: 8,602 words on 230 of its 446 vision pages), OCR's "^", "~", "+"
#   malformed  a Devanagari word that cannot be written so: it starts with a vowel sign, an anusvara or a
#              virama, or has two vowel signs, a vowel sign after a virama or after an independent vowel;
#              and the marks that are no Sanskrit (^ ~ + = < > ...) standing alone
#   plausible  the share of its letter trigrams (within words) that occur twice or more in a clean Sanskrit
#              text: the BORI Mahabharata, Adiparvan, from GRETIL (data/raw/MBh01_*, SA_QUALITY_REF names
#              another). It depends on the genre (an agama reads 87-89%, the Shatapatha 93%), so it compares
#              readings of one text; it is no grade by itself.
# Critical apparatus ("-B, C."), Vedic accents, numerals and dandas are not counted as noise.
QA_ACCENTS = re.compile("[\u0951-\u0954\u1cd0-\u1cff\ua8e0-\ua8ff]")
QA_STRIP = re.compile("[\u0964\u0965\u0966-\u096f\u0970\u0971.,;:!?()\\[\\]{}'\"\u2018\u2019\u201c\u201d\u2013\u2014\\-_*|/\\\\0-9\u00b7\u2022]")
QA_START = re.compile("^[\u0900-\u0903\u093a\u093b\u093c\u093e-\u094d\u094e\u094f\u0955-\u0957\u0962\u0963]")
QA_MATRA = "[\u093e-\u094c\u0962\u0963]"
QA_BAD = re.compile(QA_MATRA + QA_MATRA + "|\u094d" + QA_MATRA + "|\u094d\u094d|[\u0905-\u0914]" + QA_MATRA)
QA_GLUED = re.compile("[\u0900-\u097f][A-Za-z^~`$#@%&=+<>]|[A-Za-z^~`$#@%&=+<>][\u0900-\u097f]")
QA_GLUE = re.compile(r"[A-Za-z^~`$#@%&=+<>]+")
QA_JUNKSYM = re.compile(r"^[\^~`$#@%&=+<>]+$")
QA_WORD = re.compile("[\u0900-\u0963\u0971-\u097f]+")
QA_REF = os.environ.get("SA_QUALITY_REF") or "data/raw/MBh01_*.jsonl"
# Measured on 11 Oct: the GRETIL Adiparvan 0.0% of its words; vision OCR of a clean print 0.06-0.86% (the Shatapatha,
# Karan, the Markandeya, the Mallapurana, Sandilya, Hayashirsha, the Tantric Texts); Tesseract 2.7-7.4%; archive.org's
# OCR of the 1960 Bodhicaryavatara 9.4%. A witness no cleaner than Tesseract adds nothing to the scan.
NOISY, NOISE_WARN = 3.0, 1.5      # % of words: a damaged OCR text (Tesseract's grade) / some noise (above vision's)
_REF = []


def _trigrams(text: str) -> list:
    out = []
    for w in QA_WORD.findall(QA_ACCENTS.sub("", text or "")):
        w = " " + w + " "
        out.extend(w[i:i + 3] for i in range(len(w) - 2))
    return out


def reference_trigrams() -> set:
    """The letter trigrams seen twice or more in the clean reference text (read once); empty when it is not there."""
    if _REF:
        return _REF[0]
    import glob as _glob
    counts = {}
    for p in sorted(_glob.glob(QA_REF)):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        try:
                            for g in _trigrams(json.loads(line).get("text") or ""):
                                counts[g] = counts.get(g, 0) + 1
                        except ValueError:
                            continue
        except OSError:
            continue
    _REF.append({g for g, c in counts.items() if c >= 2})
    return _REF[0]


def quality(texts, plausible: bool = True) -> dict:
    """The noise in the Devanagari of a reading (see above): {words, glued_pct, malformed_pct, symbols_pct,
    noise_pct, plausible_pct, glued_top}. Latin-only words are the judge's (repair_text.judge), not counted here."""
    words = glued = malformed = junk = tg = hit = 0
    ref = reference_trigrams() if plausible else set()
    top = {}
    for t in texts:
        for tok in (t or "").split():
            raw = QA_ACCENTS.sub("", tok)
            if QA_JUNKSYM.match(raw):
                words += 1; junk += 1
                continue
            if not DEV_LETTER.search(raw):
                continue
            words += 1
            if QA_GLUED.search(raw):
                glued += 1
                for g in QA_GLUE.findall(raw):
                    top[g] = top.get(g, 0) + 1
                continue
            core = QA_STRIP.sub("", raw)
            if core and (QA_START.search(core) or QA_BAD.search(core)):
                malformed += 1
        if ref:
            for g in _trigrams(t):
                tg += 1
                hit += g in ref
    pct = lambda x: round(100.0 * x / words, 2) if words else 0.0
    return {"words": words, "glued_pct": pct(glued), "malformed_pct": pct(malformed), "symbols_pct": pct(junk),
            "noise_pct": pct(glued + malformed + junk), "plausible_pct": round(100.0 * hit / tg, 1) if (ref and tg) else None,
            "glued_top": [g for g, _ in sorted(top.items(), key=lambda x: -x[1])[:3]]}


def quality_line(label: str, q) -> str:
    if not q:
        return "%s: -" % label
    return ("%s: noise in %.1f%% of its words (glued %.1f, malformed %.1f, stray marks %.1f)%s"
            % (label, q["noise_pct"], q["glued_pct"], q["malformed_pct"], q["symbols_pct"],
               (", plausible %.1f%%" % q["plausible_pct"]) if q.get("plausible_pct") is not None else ""))


''')
edit('scripts/etext_witness.py', 4,
     r'''    scan = load_scan(a.db, doc)
    m = measure(verses, scan) if scan else None
    if m:
        print("  against the scan (%s): %d pages, %d readable; the witness reads %d of them (%.0f%%), in the scan's "
              "order %.0f%%" % (a.db, m["scan_pages"], m["readable"], m["matched"], 100 * m["coverage"], 100 * m["order"]))
        if m["span"]:
            print("  the scan's pages run over the witness's verses %d-%d of %d" % (m["span"][0] + 1, m["span"][1] + 1, len(verses)))
''',
     r'''    scan = load_scan(a.db, doc)
    m = measure(verses, scan) if scan else None
    wq = quality(v["text"] for v in verses)                      # QUALITY_2026_10_11: the witness's own Devanagari
    info["quality"] = wq
    sq = quality(scan.values()) if scan else None
    print("  quality: " + quality_line("the witness", wq) + ((" | " + quality_line("the scan", sq)) if sq else ""))
    if m:
        print("  against the scan (%s): %d pages, %d readable; the witness finds %d of the readable ones (%.0f%%) and %d "
              "pages in all, in the scan's order %.0f%%" % (a.db, m["scan_pages"], m["readable"], m.get("matched_readable", 0),
                                                         100 * m["coverage"], m["matched"], 100 * m["order"]))
        if m["span"]:
            print("  the scan's pages run over the witness's verses %d-%d of %d" % (m["span"][0] + 1, m["span"][1] + 1, len(verses)))
''')
edit('scripts/etext_witness.py', 5,
     r'''        return 1
    weak = bool(m) and m["readable"] >= 10 and m["coverage"] < 0.10
    if not a.write:
        if weak:
            print("  (--write --force makes it a witness all the same)")
            say("%s: %s; it should not be made a witness of this text" % (src.name, op), "")
            return 0
        say("%s reads as %d verses in %d pages: %s" % (src.name, len(verses), len(pages), op), q + " --write",
            [q + " --page N   (the witness's reading of one page of the scan)"])
        return 0
    if weak and not a.force:
        say("refused: %s; --force makes it a witness all the same" % op, "")
        return 1
    return write(a, doc, wcode, parsed, pages, verses, m, src, info, site, engine, op)
''',
     r'''        return 1
    weak = bool(m) and m["readable"] >= 10 and m["coverage"] < 0.10
    # QUALITY_2026_10_11: an OCR text as damaged as the scan does not repair it; it trades the scan's Latin debris
    # for its own Devanagari debris
    noisy = wq["noise_pct"] > NOISY
    if noisy:
        print("  the witness is itself a damaged OCR text: %.1f%% of its words are malformed or carry stray marks "
              "(vision OCR of a clean print has under 1.5%%; a clean e-text none)" % wq["noise_pct"])
    elif wq["noise_pct"] > NOISE_WARN:
        print("  the witness has some noise of its own (%.1f%% of its words): read its pages beside the scan" % wq["noise_pct"])
    if not a.write:
        if weak or noisy:
            print("  (--write --force makes it a witness all the same)")
            say("%s: %s; it should not be made a witness of this text%s" % (
                src.name, op, ": its own text is damaged (noise %.1f%%)" % wq["noise_pct"] if noisy else ""), "",
                [q + " --page N   (the witness's reading of one page of the scan)"])
            return 0
        say("%s reads as %d verses in %d pages: %s" % (src.name, len(verses), len(pages), op), q + " --write",
            [q + " --page N   (the witness's reading of one page of the scan)"])
        return 0
    if (weak or noisy) and not a.force:
        say("refused: %s; --force makes it a witness all the same" % (
            op if weak else "the witness is itself a damaged OCR text (noise in %.1f%% of its words)" % wq["noise_pct"]), "")
        return 1
    return write(a, doc, wcode, parsed, pages, verses, m, src, info, site, engine, op)
''')
edit('scripts/etext_witness.py', 6,
     r'''            "scheme": parsed["scheme"], "file": str(src), "url": a.url or side.get("url") or side.get("details") or "",
            "sha256": info["sha256"], "bytes": info["bytes"], "pages": len(recs), "verses": len(verses),
            "category": scan_facts.get("category"), "stats": parsed["stats"], "opinion": op, "at": _now(), "mark": MARK}
    (out / "witness.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    align = {"doc": doc, "witness": wcode, "at": meta["at"], "mark": MARK, "k": K, "opinion": op}
''',
     r'''            "scheme": parsed["scheme"], "file": str(src), "url": a.url or side.get("url") or side.get("details") or "",
            "sha256": info["sha256"], "bytes": info["bytes"], "pages": len(recs), "verses": len(verses),
            "category": scan_facts.get("category"), "stats": parsed["stats"], "opinion": op, "at": _now(), "mark": MARK,
            "quality": info.get("quality")}   # QUALITY_2026_10_11
    (out / "witness.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    align = {"doc": doc, "witness": wcode, "at": meta["at"], "mark": MARK, "k": K, "opinion": op}
''')
edit('scripts/etext_witness.py', 7,
     r'''            "coverage": m["coverage"] if m else None, "order": m["order"] if m else None,
            "offered": len([o for o in (m or {}).get("offers", []) if o.get("text")]), "opinion": op,
            "at": meta["at"], "mark": MARK}
    _append(Path(a.witnesses), line)
''',
     r'''            "coverage": m["coverage"] if m else None, "order": m["order"] if m else None,
            "offered": len([o for o in (m or {}).get("offers", []) if o.get("text")]), "opinion": op,
            "noise_pct": (info.get("quality") or {}).get("noise_pct"),   # QUALITY_2026_10_11
            "at": meta["at"], "mark": MARK}
    _append(Path(a.witnesses), line)
''')
edit('scripts/benchmark_sources.py', 8,
     r'''        facts["translated_misread_pct"] = j["misread_pct"]          # of the translated passages
        facts["translated_letters_misread_pct"] = j["misread_letters_pct"]
    return {p: "\n".join(v) for p, v in pages.items()}, facts


''',
     r'''        facts["translated_misread_pct"] = j["misread_pct"]          # of the translated passages
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


''')
edit('scripts/benchmark_sources.py', 9,
     r'''    lat = sum(len(ew.ASCII_LETTER.findall(t)) for t in pages.values())
    j = rt.judge(rows, Path("/nonexistent"), doc, max_pages=0) if rows else {}
    return {"label": label, "kind": kind, "pages": len(pages), "letters": dev,
            "latin_pct": round(100.0 * lat / (lat + dev), 2) if lat + dev else 0.0,
            "misread_letters_pct": j.get("misread_letters_pct", 0.0), "pages_misread_pct": j.get("misread_pct", 0.0),
            "level": j.get("level") if rows else None, "misread_top": (j.get("misread_top") or [])[:6]}


''',
     r'''    lat = sum(len(ew.ASCII_LETTER.findall(t)) for t in pages.values())
    j = rt.judge(rows, Path("/nonexistent"), doc, max_pages=0) if rows else {}
    q = ew.quality(pages.values())   # QUALITY_2026_10_11: the Devanagari itself, not only the Latin in it
    return {"label": label, "kind": kind, "pages": len(pages), "letters": dev,
            "latin_pct": round(100.0 * lat / (lat + dev), 2) if lat + dev else 0.0,
            "misread_letters_pct": j.get("misread_letters_pct", 0.0), "pages_misread_pct": j.get("misread_pct", 0.0),
            "level": j.get("level") if rows else None, "misread_top": (j.get("misread_top") or [])[:6],
            "noise_pct": q["noise_pct"], "glued_pct": q["glued_pct"], "malformed_pct": q["malformed_pct"],
            "symbols_pct": q["symbols_pct"], "plausible_pct": q["plausible_pct"], "glued_top": q["glued_top"]}


''')
edit('scripts/benchmark_sources.py', 10,
     r'''        res["readings"].append(d)
    res["translations"] = {"now": now, "before": before}
    return opine(res, doc, a)


''',
     r'''        res["readings"].append(d)
    res["translations"] = {"now": now, "before": before}
    res["merged_engines"] = page_engines(merged, doc)   # QUALITY_2026_10_11
    return opine(res, doc, a)


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


''')
edit('scripts/benchmark_sources.py', 11,
     r'''        cut = (100.0 * (t - o) / t) if t else 0.0
        more = (100.0 * (ours["letters"] - te["letters"]) / te["letters"]) if te["letters"] else 0.0
        if ours["label"] != "consensus":
            L.append("OCR: not repaired: the text in the database misreads %.2f%% of the letters (Tesseract's pages %.2f%%, "
                     "%.0f%% of them damaged)." % (o, t, te["pages_misread_pct"]))
        elif t >= 0.3 and o < t:
            L.append("OCR: Tesseract misread %.2f%% of the letters (%.0f%% of its pages damaged); the repair %.2f%% (%.0f%% "
                     "of pages): it removed %.0f%% of the misreading%s." % (
                         t, te["pages_misread_pct"], o, ours["pages_misread_pct"], cut,
                         ("; it reads %+.0f%% Devanagari letters" % more) if abs(more) >= 3 else ""))
        else:
            L.append("OCR: Tesseract misread %.2f%% of the letters, the repair %.2f%%: little to gain here." % (t, o))
    arch = [x for x in res["readings"] if x["kind"] == "archive-ocr"]
    for x in arch:
''',
     r'''        cut = (100.0 * (t - o) / t) if t else 0.0
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
''')
edit('scripts/benchmark_sources.py', 12,
     r'''            how = "F1 with the critical text %.2f, ours %.2f" % (x["f1_ref"], ours["f1_ref"])
        else:
            d = ours["misread_letters_pct"] - x["misread_letters_pct"]
            d = d / 10.0 if abs(d) >= 0.1 else 0.0     # a tenth of a point of letters is level
            how = "misread letters %.2f%%, ours %.2f%%" % (x["misread_letters_pct"], ours["misread_letters_pct"])
        word = ("archive.org's reading is the better one here: make it a witness" if d > 0.02 else
                ("ours is the better one" if d < -0.02 else "the two are level"))
        L.append("archive.org's OCR (%s), on the %d pages it shares with this scan: %s; %s." % (x["label"], x["pages"], how, word))
    if res["reference"]:
''',
     r'''            how = "F1 with the critical text %.2f, ours %.2f" % (x["f1_ref"], ours["f1_ref"])
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
        L.append("archive.org's OCR (%s), on the %d pages it shares with this scan: %s; %s." % (x["label"], x["pages"], how, word))
    if res["reference"]:
''')
edit('scripts/benchmark_sources.py', 13,
     r'''            L.append("Vision alone reads the critical text better than the consensus (F1 %.2f against %.2f): the merge "
                     "keeps some Tesseract readings it should not." % (vi["f1_ref"], co["f1_ref"]))
    tr = res.get("translations") or {}
    b, n = tr.get("before") or {}, tr.get("now") or {}
    if b.get("english"):
        share = b.get("translated_misread_pct") or 0.0
        lv = "material" if share >= MATERIAL_TR else ("moderate" if share >= MODERATE_TR else "cosmetic")
        L.append("Translation before the repair: %d English, %d Hindi; %.0f%% of the passages translated carried misread "
                 "letters (%.2f%% of their letters): the debris's effect on that translation was %s." % (
                     b["english"], b.get("hindi", 0), share, b.get("translated_letters_misread_pct") or 0.0, lv.upper()))
    if n.get("english"):
        share = n.get("translated_misread_pct") or 0.0
        lv = "material" if share >= MATERIAL_TR else ("moderate" if share >= MODERATE_TR else "cosmetic")
        L.append("Translation now: %d English of %d passages, %d Hindi%s; %.0f%% of the passages translated carry misread "
                 "letters: %s." % (n["english"], n["passages"], n.get("hindi", 0),
                                   ("; heuristic QA %.2f" % n["qa_mean"]) if n.get("qa_mean") is not None else "",
                                   share, lv))
        if n.get("reviews"):
            L.append("The LLM judge (mt_reviews) graded %d English passages: fidelity %.2f, fluency %.2f of 5." % (
''',
     r'''            L.append("Vision alone reads the critical text better than the consensus (F1 %.2f against %.2f): the merge "
                     "keeps some Tesseract readings it should not." % (vi["f1_ref"], co["f1_ref"]))
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
            L.append("The LLM judge (mt_reviews) graded %d English passages: fidelity %.2f, fluency %.2f of 5." % (
''')
edit('scripts/benchmark_sources.py', 14,
     r'''def show(res: dict):
    print("%s  %s" % (res["doc"], MARK))
    hdr = "  %-22s %-11s %6s %9s %7s %8s %7s %-9s %7s %7s %7s"
    print(hdr % ("reading", "kind", "pages", "letters", "latin%", "misread%", "pages%", "level", "F1ours", "F1ref", "ref%"))
    for x in res["readings"]:
        f = lambda k, fmt="%.2f": (fmt % x[k]) if x.get(k) is not None else "-"
        print(hdr % (x["label"][:22], x["kind"], x["pages"], x["letters"], f("latin_pct"), f("misread_letters_pct"),
                     f("pages_misread_pct", "%.0f"), x.get("level") or "-", f("f1_ours"), f("f1_ref"),
                     ("%.0f" % (100 * x["recall_ref"])) if x.get("recall_ref") is not None else "-"))
    for line in res.get("lines") or []:
        print("  " + line)
''',
     r'''def show(res: dict):
    print("%s  %s" % (res["doc"], MARK))
    hdr = "  %-22s %-11s %6s %9s %7s %8s %7s %-9s %6s %6s %7s %7s %7s"   # QUALITY_2026_10_11: noise, plausible
    print(hdr % ("reading", "kind", "pages", "letters", "latin%", "misread%", "pages%", "level", "noise%", "plaus%",
                 "F1ours", "F1ref", "ref%"))
    for x in res["readings"]:
        f = lambda k, fmt="%.2f": (fmt % x[k]) if x.get(k) is not None else "-"
        print(hdr % (x["label"][:22], x["kind"], x["pages"], x["letters"], f("latin_pct"), f("misread_letters_pct"),
                     f("pages_misread_pct", "%.0f"), x.get("level") or "-", f("noise_pct", "%.1f"), f("plausible_pct", "%.1f"),
                     f("f1_ours"), f("f1_ref"), ("%.0f" % (100 * x["recall_ref"])) if x.get("recall_ref") is not None else "-"))
    for line in res.get("lines") or []:
        print("  " + line)
''')
edit('scripts/benchmark_sources.py', 15,
     r'''            n = (res.get("translations") or {}).get("now") or {}
            rows.append({"doc": d, "tesseract": te and te["misread_letters_pct"], "ours": ours and ours["misread_letters_pct"],
                         "ours_label": ours and ours["label"], "reference": res.get("reference"),
                         "f1_ref": ours and ours.get("f1_ref"), "en_before": b.get("english"),
''',
     r'''            n = (res.get("translations") or {}).get("now") or {}
            rows.append({"doc": d, "tesseract": te and te["misread_letters_pct"], "ours": ours and ours["misread_letters_pct"],
                         "ours_noise": ours and ours.get("noise_pct"), "tesseract_noise": te and te.get("noise_pct"),
                         "ours_label": ours and ours["label"], "reference": res.get("reference"),
                         "f1_ref": ours and ours.get("f1_ref"), "en_before": b.get("english"),
''')
edit('scripts/benchmark_sources.py', 16,
     r'''                         "passages": n.get("passages"), "lines": res.get("lines")})
            print("  [%d/%d] %-56s tesseract %s | ours %s | English before %s (%s%% from damaged text) | now %s/%s" % (
                i, len(docs), d[:56], "-" if te is None else "%.2f%%" % te["misread_letters_pct"],
                "-" if ours is None else "%.2f%% (%s)" % (ours["misread_letters_pct"], ours["label"]),
                b.get("english", "-"), "-" if b.get("translated_misread_pct") is None else "%.0f" % b["translated_misread_pct"],
                n.get("english", "-"), n.get("passages", "-")), flush=True)
''',
     r'''                         "passages": n.get("passages"), "lines": res.get("lines")})
            print("  [%d/%d] %-56s tesseract %s | ours %s | English before %s (%s%% from damaged text) | now %s/%s" % (
                i, len(docs), d[:56], "-" if te is None else "%.2f%%/%s" % (te["misread_letters_pct"], _p(te, "noise_pct")),
                "-" if ours is None else "%.2f%%/%s (%s)" % (ours["misread_letters_pct"], _p(ours, "noise_pct"), ours["label"]),
                b.get("english", "-"), "-" if b.get("translated_misread_pct") is None else "%.0f" % b["translated_misread_pct"],
                n.get("english", "-"), n.get("passages", "-")), flush=True)
''')
edit('scripts/merge_ocr_sources.py', 17,
     r'''LOOP_RATIO = 0.08       # see BENCHMARKS.md; degenerate <=0.029, ordinary >=0.135
LOOP_MIN_CHARS = 3000


''',
     r'''LOOP_RATIO = 0.08       # see BENCHMARKS.md; degenerate <=0.029, ordinary >=0.135
LOOP_MIN_CHARS = 3000
# QUALITY_2026_10_11: Tesseract is a fallback only where it read text. On a plate (a yantra, a figure), a title
# page or a blank page, vision rightly returns nothing or a line, and Tesseract makes Devanagari-and-Latin garbage
# of the picture; the merge took that garbage (on 11 Oct: Tantric Texts pages 1, 2, 19, 20, 157, 158, 211;
# Karan Aagama 8, 152, 154; Shatapatha 149, 213, 222; Rgveda vol. ii 9; Mallapurana 32). Measured on the 678
# fallback pages then in the corpus: the 655 that are text are 70% Devanagari or more (Shatapatha 0009, the page
# this fallback was made for, 83%); the 8 English pages Tesseract read right (Mallapurana's introduction,
# Hayashirsha's notes, the Rgveda's preface) have Latin words 4.5-5.4 letters long and under 1% stray marks; the 15
# garbage pages are under half Devanagari, with "words" of 1.4-2.6 letters and 9-55% stray marks. Garbage can also
# be mostly Devanagari fragments among marks (Karan Aagama 2, 16, 26, 182: 1.1-1.2 letters a word, 14-27% stray
# marks), where the 650 pages of text have 2.85 letters a word or more and under 4% stray marks.
TESS_MIN_DEV = 0.5
ENGLISH_MIN_WORD = 3.5
STRAY_MAX = 0.10
FRAGMENT_MAX = 2.0
FRAGMENT_STRAY = 0.08
DEV_LETTER = re.compile("[\u0904-\u0939\u0958-\u0961]")
LATIN_WORD = re.compile(r"[A-Za-z]+")
STRAY = re.compile("[~^=+*<>|\\{}\[\]_`$#@%&\u00a2\u00a3\u00a5\u2020\u2021\u00a9\u00ae\u00b6\u00a7"
                   "\u201c\u201d\u2018\u2019\u201e\u00bb\u00ab\u2022]")


def tesseract_garbage(t: str) -> tuple[bool, str]:
    """(True, why) when Tesseract's page is neither Devanagari nor English: OCR of a picture."""
    t = t or ""
    d = len(DEV_LETTER.findall(t))
    words = LATIN_WORD.findall(t)
    lat = sum(len(w) for w in words)
    if len(t.strip()) < DEFINITELY_EMPTY or d + lat == 0:
        return False, ""
    share = d / float(d + lat)
    stray = len(STRAY.findall(t)) / float(max(1, len(re.sub(r"\s", "", t))))
    if share >= TESS_MIN_DEV:
        toks = [w for w in t.split() if DEV_LETTER.search(w)]
        per = sum(len(DEV_LETTER.findall(w)) for w in toks) / float(len(toks))
        if per < FRAGMENT_MAX and stray > FRAGMENT_STRAY:
            return True, ("Tesseract's page is Devanagari fragments among marks (%.1f letters a word, %.0f%% stray marks)"
                          % (per, 100 * stray))
        return False, ""
    avg = lat / float(len(words)) if words else 0.0
    if avg >= ENGLISH_MIN_WORD and stray <= STRAY_MAX:
        return False, ""                     # English that Tesseract read: an introduction, a note
    return True, ("Tesseract's page is %.0f%% Devanagari, its Latin words %.1f letters long, %.0f%% stray marks"
                  % (100 * share, avg, 100 * stray))


''')
edit('scripts/merge_ocr_sources.py', 18,
     r'''    v = collapse_runs(vtext or "").strip()
    t = (ttext or "").strip()
    if len(v) < DEFINITELY_EMPTY:
        return ("tesseract-fallback" if len(t) >= DEFINITELY_EMPTY else "none",
''',
     r'''    v = collapse_runs(vtext or "").strip()
    t = (ttext or "").strip()
    garbage, gwhy = tesseract_garbage(t)   # QUALITY_2026_10_11
    if garbage:
        if len(v) < DEFINITELY_EMPTY or (len(v) >= LOOP_MIN_CHARS and compress_ratio(v) < LOOP_RATIO):
            return "blank", "neither engine read text: vision found none, and " + gwhy + " (a plate or a blank page)"
        return "vision", gwhy + ": vision's %d chars kept" % len(v)
    if len(v) < DEFINITELY_EMPTY:
        return ("tesseract-fallback" if len(t) >= DEFINITELY_EMPTY else "none",
''')
edit('scripts/merge_ocr_sources.py', 19,
     r'''        sys.exit(f"no pages found for {args.doc}")

    counts = {"vision": 0, "tesseract-fallback": 0, "none": 0}
    notes = []
    n_variants = 0
''',
     r'''        sys.exit(f"no pages found for {args.doc}")

    counts = {"vision": 0, "tesseract-fallback": 0, "none": 0, "blank": 0}   # QUALITY_2026_10_11: blank
    notes = []
    n_variants = 0
''')
edit('scripts/merge_ocr_sources.py', 20,
     r'''        src, why = verdict(vtext, ttext)
        counts[src] += 1
        if src != "vision":
            notes.append((pg, src, why, len(vtext), len(ttext)))
        if not args.apply:
''',
     r'''        src, why = verdict(vtext, ttext)
        counts[src] += 1
        if src != "vision" or why:   # QUALITY_2026_10_11: and a page where Tesseract's garbage was refused
            notes.append((pg, src, why, len(vtext), len(ttext)))
        if not args.apply:
''')
edit('scripts/merge_ocr_sources.py', 21,
     r'''        if src == "vision":
            text, engine = collapse_runs(vtext), (vrec or {}).get("engine") or "gemini-vision"
        else:
            text, engine = ttext, "tesseract-fallback"
        vars_ = variants(ttext, vtext) if (ttext and vtext) else []
        out = {
            "engine": engine,
''',
     r'''        if src == "vision":
            text, engine = collapse_runs(vtext), (vrec or {}).get("engine") or "gemini-vision"
        elif src == "blank":   # QUALITY_2026_10_11: written empty, so the page is accounted for and nothing false goes in
            text, engine = "", "blank"
        else:
            text, engine = ttext, "tesseract-fallback"
        vars_ = variants(ttext, vtext) if (ttext and vtext and not tesseract_garbage(ttext)[0]) else []
        out = {
            "engine": engine,
''')
edit('scripts/merge_ocr_sources.py', 22,
     r'''          f"{'WRITING' if args.apply else 'DRY RUN'}")
    print("=" * 74)
    for k in ("vision", "tesseract-fallback", "none"):
        pct = 100.0 * counts[k] / total
        print(f"  {k:20s} {counts[k]:>5}  ({pct:5.1f}%)")
    if notes:
        print("\n  pages NOT taken from vision:")
        for pg, src, why, nv, nt in notes[:25]:
            print(f"    page {pg}  {src:19s} {why}")
        if len(notes) > 25:
            print(f"    ... and {len(notes)-25} more")
    if counts["none"]:
        print(f"\n  {counts['none']} page(s) have NO usable text from either engine.")
''',
     r'''          f"{'WRITING' if args.apply else 'DRY RUN'}")
    print("=" * 74)
    for k in ("vision", "tesseract-fallback", "blank", "none"):   # QUALITY_2026_10_11: blank
        pct = 100.0 * counts[k] / total
        print(f"  {k:20s} {counts[k]:>5}  ({pct:5.1f}%)")
    if notes:
        print("\n  pages not simply taken from vision:")   # QUALITY_2026_10_11: and why
        for pg, src, why, nv, nt in notes[:25]:
            print(f"    page {pg}  {src:19s} {why}")
        if len(notes) > 25:
            print(f"    ... and {len(notes)-25} more")
    if counts["blank"]:   # QUALITY_2026_10_11
        print(f"\n  {counts['blank']} page(s) are blank: vision found no text, and Tesseract's is the garbage it makes of")
        print("  a picture (a plate, a yantra, a title page). They are written empty: nothing false goes in.")
    if counts["none"]:
        print(f"\n  {counts['none']} page(s) have NO usable text from either engine.")
''')
edit('scripts/ocr_consensus.py', 23,
     r'''                 "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                 "variants": len(((rec.get("meta") or {}).get("variants")) or [])}
        if n not in db_pages:
            entry.update(similarity=None, db_engine=None, status="missing-in-db")
        else:
''',
     r'''                 "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                 "variants": len(((rec.get("meta") or {}).get("variants")) or [])}
        if rec.get("engine") == "blank" and not text.strip():
            # QUALITY_2026_10_11: a blank page (a plate): current when the database has nothing for it; stale when it
            # still has Tesseract's garbage of the picture
            entry.update(similarity=None, db_engine=(",".join(sorted(db_pages[n][1])) or None) if n in db_pages else None,
                         status="stale" if n in db_pages else "current")
        elif n not in db_pages:
            entry.update(similarity=None, db_engine=None, status="missing-in-db")
        else:
''')
edit('scripts/source_desk.py', 24,
     r'''ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
UA = {"User-Agent": "SanskritAutomaton-SourceDesk/1.0 (scholarly, non-commercial)"}
BASE = "https://archive.org"
''',
     r'''ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:   # QUALITY_2026_10_11: the AI judge's key is in .env, as ocr_vision.py's ("AI: GEMINI_API_KEY is not set" on 11 Oct)
    from env_loader import load_env
    load_env()
except Exception:
    pass
UA = {"User-Agent": "SanskritAutomaton-SourceDesk/1.0 (scholarly, non-commercial)"}
BASE = "https://archive.org"
''')
edit('scripts/source_desk.py', 25,
     r'''        {"name": "GRETIL (Unicode e-texts)", "url": "https://www.google.com/search?q=" + e("site:gretil.sub.uni-goettingen.de " + q)},
        {"name": "sanskritdocuments.org", "url": "https://www.google.com/search?q=" + e("site:sanskritdocuments.org " + q)},
        {"name": "wisdomlib.org", "url": "https://www.wisdomlib.org/index.php?type=search&query=" + e(q)},
        {"name": "archive.org", "url": BASE + "/search?query=" + e(q) + "&sin=TXT"},
''',
     r'''        {"name": "GRETIL (Unicode e-texts)", "url": "https://www.google.com/search?q=" + e("site:gretil.sub.uni-goettingen.de " + q)},
        {"name": "sanskritdocuments.org", "url": "https://www.google.com/search?q=" + e("site:sanskritdocuments.org " + q)},
        {"name": "Digital Sanskrit Buddhist Canon", "url": "https://www.google.com/search?q=" + e("site:dsbcproject.org " + q)},
        {"name": "wisdomlib.org", "url": "https://www.wisdomlib.org/index.php?type=search&query=" + e(q)},
        {"name": "archive.org", "url": BASE + "/search?query=" + e(q) + "&sin=TXT"},
''')
edit('scripts/source_desk.py', 26,
     r'''        if not info.get("txt_url"):
            print("VERDICT: %s has no OCR text; try --kind pdf" % ident); print("NEXT: "); return 1
        sample = _http(info["txt_url"], timeout=60, rng=PURITY_BYTES).decode("utf-8", "replace")
        pur = asf.dev_ratio(sample)
        if pur < 0.85 and not a.force:
''',
     r'''        if not info.get("txt_url"):
            print("VERDICT: %s has no OCR text; try --kind pdf" % ident); print("NEXT: "); return 1
        try:   # QUALITY_2026_10_11: archive.org answered 500 for the Natyasastra's OCR text on 11 Oct (a traceback)
            sample = _http(info["txt_url"], timeout=60, rng=PURITY_BYTES).decode("utf-8", "replace")
        except Exception as e:
            print("VERDICT: archive.org did not give %s's OCR text (%s): %s" % (ident, str(e)[:120], info["txt_url"]))
            print("NEXT: python scripts\\source_desk.py --doc %s --fetch %s --kind pdf   (or try again later)" % (a.doc, ident))
            return 1
        pur = asf.dev_ratio(sample)
        if pur < 0.85 and not a.force:
''')
edit('scripts/source_desk.py', 27,
     r'''    target = dest / name
    print("fetching %s (%s MB) ..." % (url, info.get("pdf_mb") if a.kind == "pdf" else "?"), flush=True)
    data = _http(url, timeout=600)
    tmp = target.with_name(target.name + ".part"); tmp.write_bytes(data); os.replace(tmp, target)
    side = {"doc": a.doc, "identifier": ident, "kind": a.kind, "url": url, "details": BASE + "/details/" + ident,
''',
     r'''    target = dest / name
    print("fetching %s (%s MB) ..." % (url, info.get("pdf_mb") if a.kind == "pdf" else "?"), flush=True)
    try:   # QUALITY_2026_10_11
        data = _http(url, timeout=600)
    except Exception as e:
        print("VERDICT: the download of %s failed (%s); nothing was saved" % (url, str(e)[:160]))
        print("NEXT: python scripts\\source_desk.py --doc %s --fetch %s --kind %s   (try again later)" % (a.doc, ident, a.kind))
        return 1
    tmp = target.with_name(target.name + ".part"); tmp.write_bytes(data); os.replace(tmp, target)
    side = {"doc": a.doc, "identifier": ident, "kind": a.kind, "url": url, "details": BASE + "/details/" + ident,
''')
edit('scripts/dashboard.py', 28,
     r'''  var h = '<div class="srcsub">Benchmark, ' + _rpEsc(String(b.at || '').replace('T', ' ').slice(0, 16))
        + (b.reference ? ', against ' + _rpEsc(b.reference) : '') + '</div><div class="benchwrap"><table class="bench"><thead><tr>'
        + '<th>Reading</th><th>Pages</th><th>Letters</th><th>Misread</th><th>Pages hit</th><th>Level</th><th>F1 with ours</th>'
        + '<th>F1 with the critical text</th></tr></thead><tbody>';
  (b.readings || []).forEach(function(x){
    h += '<tr><td>' + _rpEsc(x.label) + '</td><td>' + x.pages + '</td><td>' + x.letters + '</td><td>' + f(x.misread_letters_pct)
       + '%</td><td>' + f(x.pages_misread_pct, 0) + '%</td><td><span class="lv" data-level="' + _rpEsc(x.level || '') + '">'
       + _rpEsc(x.level || '-') + '</span></td><td>' + f(x.f1_ours) + '</td><td>' + f(x.f1_ref) + '</td></tr>';
  });
  h += '</tbody></table></div>';
''',
     r'''  var h = '<div class="srcsub">Benchmark, ' + _rpEsc(String(b.at || '').replace('T', ' ').slice(0, 16))
        + (b.reference ? ', against ' + _rpEsc(b.reference) : '') + '</div><div class="benchwrap"><table class="bench"><thead><tr>'
        + '<th>Reading</th><th>Pages</th><th>Letters</th><th>Misread</th><th>Pages hit</th><th>Level</th><th>Noise</th>'
        + '<th>Plausible</th><th>F1 with ours</th>'   /* QUALITY_2026_10_11: noise in the Devanagari, plausibility */
        + '<th>F1 with the critical text</th></tr></thead><tbody>';
  (b.readings || []).forEach(function(x){
    h += '<tr><td>' + _rpEsc(x.label) + '</td><td>' + x.pages + '</td><td>' + x.letters + '</td><td>' + f(x.misread_letters_pct)
       + '%</td><td>' + f(x.pages_misread_pct, 0) + '%</td><td><span class="lv" data-level="' + _rpEsc(x.level || '') + '">'
       + _rpEsc(x.level || '-') + '</span></td><td>' + (x.noise_pct == null ? '-' : f(x.noise_pct, 1) + '%') + '</td><td>'
       + (x.plausible_pct == null ? '-' : f(x.plausible_pct, 1) + '%') + '</td><td>' + f(x.f1_ours) + '</td><td>' + f(x.f1_ref) + '</td></tr>';
  });
  h += '</tbody></table></div>';
''')
edit('scripts/dashboard.py', 29,
     r'''        return next((x for x in r.get("readings") or [] if x.get("label") == label), None)

    pct = lambda x: ("%.2f%%" % float(x.get("misread_letters_pct") or 0)) if x else "-"
    trs, improved = "", 0
    for r in rows:
''',
     r'''        return next((x for x in r.get("readings") or [] if x.get("label") == label), None)

    pct = lambda x: (("%.2f%%" % float(x.get("misread_letters_pct") or 0)) + (   # QUALITY_2026_10_11: and the noise
        " / %.1f%%" % float(x["noise_pct"]) if x.get("noise_pct") is not None else "")) if x else "-"
    trs, improved = "", 0
    for r in rows:
''')
edit('scripts/dashboard.py', 30,
     r'''            'or two)</button><div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>Tesseract '
            'misreads</th><th>Ours misreads</th><th>archive.org OCR</th><th>Critical e-text</th><th>English before the '
            'repair</th><th>Now</th></tr></thead><tbody>%s</tbody></table></div>%s</div>'
            % (len(rows), improved, trs, "" if rows else '<p class="srcnone">Nothing benchmarked yet. Press Benchmark '
''',
     r'''            'or two)</button><div class="rpout"></div></div>'
            '<div class="srcwrap" style="margin-top:12px"><table class="srct"><thead><tr><th>Text</th><th>Tesseract '
            'misreads / noise</th><th>Ours misreads / noise</th><th>archive.org OCR</th><th>Critical e-text</th><th>English before the '
            'repair</th><th>Now</th></tr></thead><tbody>%s</tbody></table></div>%s</div>'
            % (len(rows), improved, trs, "" if rows else '<p class="srcnone">Nothing benchmarked yet. Press Benchmark '
''')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out = src
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_quality_" + stamp))
        t = p.with_name(p.name + ".tmp_quality"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("The merge refuses Tesseract's garbage from its next run; nothing already merged or ingested changes until you")
    print("merge a text again. dashboard.py shows the noise when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    print("Then: python scripts\\benchmark_sources.py --all (free, read-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
