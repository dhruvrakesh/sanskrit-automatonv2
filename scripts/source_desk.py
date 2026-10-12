#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
source_desk.py  (2026-10-11)  SOURCE_DESK_2026_10_11

Finds a better edition of one text, so that a scan that cannot be repaired is replaced by a better
witness rather than translated as it is. It looks in four places and says why each candidate is
ranked where it is:

  archive.org   the Internet Archive's search API (texts): title, creator, publisher, year, language,
                pages; for the best few, the item's files (a PDF, an OCR text) and the Devanagari purity
                of that OCR text (archive_source_finder.py's measure, first 300 KB only);
  wisdomlib     the local archive made by D:\\wisdomlib\\scraper.py (offline; books matched by title);
  link-outs     GRETIL, sanskritdocuments.org, wisdomlib.org and archive.org searches for a browser:
                Unicode e-texts there need no OCR at all and are the first choice when they exist;
  AI (--ai)     the ranked list is given to Gemini, which says for each item whether it is the same
                work and whether it is a critical, scholarly or popular edition, and why (one call,
                about $0.002, capped by --max-usd; recorded in usage_log when cost_tracker is there).

The ranking rewards: the title's words; the marks of a critical edition ("critical edition",
"critically edited", Bhandarkar / BORI, Gaekwad's Oriental Series, Anandashrama, Nirnaya Sagar,
Chowkhamba, Kashi / Trivandrum Sanskrit Series, Adyar, Bibliotheca Indica, ...); Sanskrit as the
language; an OCR text that is pure Devanagari; a full page count. It marks the scan already in the
inbox ("the scan you have", from the numbers in the text's code) instead of offering it again.

  python scripts\\source_desk.py --doc 2015_368408_Natyasastra-With
  python scripts\\source_desk.py --doc X --ai                        # and let the AI judge (~$0.002)
  python scripts\\source_desk.py --doc X --title "natyasastra abhinavabharati"
  python scripts\\source_desk.py --doc X --fetch <identifier> --kind pdf    # into sources\\X\\
  python scripts\\source_desk.py --doc X --fetch <identifier> --kind text   # purity-gated (0.85)

Writes data\\source_desk\\<doc>.json (the candidates) and, on --fetch, sources\\<doc>\\<file> with a
provenance sidecar <file>.json. Never writes the database. A fetched PDF is a new witness: import it
from the dashboard (Import path to inbox) as its own text, then OCR it with vision.
The last lines are VERDICT: and NEXT:, as repair_text.py's, for the dashboard.
"""
from __future__ import annotations
import argparse, datetime, json, math, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

MARK = "SOURCE_DESK_2026_10_11"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:   # QUALITY_2026_10_11: the AI judge's key is in .env, as ocr_vision.py's ("AI: GEMINI_API_KEY is not set" on 11 Oct)
    from env_loader import load_env
    load_env()
except Exception:
    pass
UA = {"User-Agent": "SanskritAutomaton-SourceDesk/1.0 (scholarly, non-commercial)"}
BASE = "https://archive.org"
WISDOMLIB_ARCHIVE = Path(os.environ.get("SA_WISDOMLIB_ARCHIVE") or r"D:\wisdomlib\wisdomlib_archive")
PURITY_BYTES = 300_000
TOP_ANALYSE = 6
STOP = set("""by prof dr the of with and edited edition ed series vol volume part pdf book text texts
sanskrit hindi english commentary translated translation tr publication publications press""".split())
CRITICAL = ("critical edition", "critically edited", "crit. ed", "critical ed", "critical text", "vulgate")
SERIES = ("bhandarkar", "bori", "gaekwad", "oriental series", "anandashram", "anandasram", "nirnaya sagar",
          "nirnayasagar", "nirnaya-sagar", "chowkhamba", "chaukhamba", "chowkamba", "kashi sanskrit", "trivandrum",
          "adyar", "bibliotheca indica", "asiatic society", "sahitya akademi", "motilal", "vani vilas",
          "kavyamala", "harvard oriental", "sarasvati bhavana", "saraswati bhawan", "rashtriya sanskrit",
          "oriental research institute", "venkateshwar", "venkatesvara", "gita press", "nag publishers",
          "kendriya sanskrit", "sampurnanand", "ganganath jha", "mysore oriental", "baroda", "punjab sanskrit")


def _http(url: str, timeout: int = 40, rng: int | None = None) -> bytes:
    h = dict(UA)
    if rng:
        h["Range"] = "bytes=0-%d" % (rng - 1)
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.read(rng) if rng else r.read()


def _json(url: str, timeout: int = 40) -> dict:
    return json.loads(_http(url, timeout).decode("utf-8", "replace"))


def norm(s: str) -> str:
    """lower case, no diacritics that matter for matching, aa -> a, sh -> s, w -> v"""
    s = (s or "").lower()
    for a, b in (("\u0101", "a"), ("\u012b", "i"), ("\u016b", "u"), ("\u1e5b", "r"), ("\u1e5d", "r"),
                 ("\u015b", "s"), ("\u1e63", "s"), ("\u1e47", "n"), ("\u1e45", "n"), ("\u00f1", "n"),
                 ("\u1e6d", "t"), ("\u1e0d", "d"), ("\u1e43", "m"), ("\u1e25", "h"), ("\u0113", "e"),
                 ("\u014d", "o")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    for a, b in (("aa", "a"), ("ee", "i"), ("oo", "u"), ("sh", "s"), ("w", "v"), ("ph", "p"), ("th", "t"),
                 ("dh", "d"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("ch", "c"), ("jh", "j")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def title_words(doc: str, title: str | None = None) -> list:
    """The words of the text's name worth searching for: from its title when given, else its code."""
    src = title or doc
    words = [w for w in re.split(r"[^A-Za-z]+", src) if w]
    out = []
    for w in words:
        lw = w.lower()
        if lw in STOP or len(lw) < 3:
            continue
        out.append(lw)
    return out[:6]


def scan_numbers(doc: str) -> list:
    """Numbers in the code that name the scan already held (e.g. 2015_368408 -> dli.2015.368408)."""
    return [n for n in re.findall(r"\d{5,}", doc)]


def archive_search(words: list, rows: int) -> list:
    """Search archive.org texts by title: all words first, then the first two, then each long word."""
    qs, seen, out = [], set(), []
    if words:
        qs.append(" ".join(words[:4]))
        if len(words) > 2:
            qs.append(" ".join(words[:2]))
        qs += [w for w in words[:3] if len(w) >= 6]
    fl = ("identifier", "title", "creator", "publisher", "date", "year", "language", "downloads", "imagecount",
          "description", "subject")
    for q in qs:
        query = "title:(%s) AND mediatype:(texts)" % q
        parts = [("q", query), ("rows", str(rows)), ("output", "json"), ("sort[]", "downloads desc")]
        parts += [("fl[]", f) for f in fl]
        url = BASE + "/advancedsearch.php?" + urllib.parse.urlencode(parts)
        for d in (_json(url).get("response", {}) or {}).get("docs", []) or []:
            ident = d.get("identifier")
            if ident and ident not in seen:
                seen.add(ident); out.append(d)
        if len(out) >= rows:
            break
    return out


def one(v):
    if isinstance(v, list):
        return ", ".join(str(x) for x in v[:3]) if v else ""
    return "" if v is None else str(v)


def score(c: dict, words: list, nums: list) -> tuple:
    why, sc = [], 0.0
    t = norm(c.get("title")); nw = [norm(w) for w in words]
    hit = sum(1 for w in nw if w and w in t)
    if nw:
        sc += 30.0 * hit / len(nw)
        why.append("title has %d of %d words" % (hit, len(nw)))
    blob = " ".join(one(c.get(k)) for k in ("title", "description", "publisher", "subject", "creator")).lower()
    if any(k in blob for k in CRITICAL):
        sc += 25; why.append("says critical edition")
    ser = [k for k in SERIES if k in blob]
    if ser:
        sc += 12; why.append("scholarly series or publisher: " + ser[0])
    lang = one(c.get("language")).lower()
    if "san" in lang:
        sc += 10; why.append("language Sanskrit")
    if "hin" in lang or "-h" in lang:
        sc -= 5; why.append("bilingual with Hindi")
    pages = int(c.get("imagecount") or 0)
    if pages >= 100:
        sc += 5; why.append("%d pages" % pages)
    dl = int(c.get("downloads") or 0)
    if dl:
        sc += min(5.0, math.log10(dl + 1) * 1.5)
    if any(n in (c.get("identifier") or "") for n in nums):
        sc -= 30; why.append("the scan you have")
        c["current_scan"] = True
    pur = c.get("purity")
    if pur is not None:
        if pur >= 0.85:
            sc += 15; why.append("OCR text %.0f%% Devanagari" % (100 * pur))
        elif pur >= 0.6:
            sc += 5; why.append("OCR text %.0f%% Devanagari (mixed)" % (100 * pur))
        else:
            sc -= 10; why.append("OCR text only %.0f%% Devanagari" % (100 * pur))
    ai = c.get("ai") or {}
    if ai:
        kind = ai.get("edition_kind")
        sc += {"critical": 15, "scholarly": 8, "popular": 0}.get(kind, 0)
        if ai.get("same_work") is False:
            sc -= 40
        why.append("AI: %s%s" % (kind or "?", "" if ai.get("same_work", True) else ", not the same work"))
    return round(sc, 1), why


def analyse_top(cands: list, errors: list):
    try:
        import archive_source_finder as asf
    except Exception as e:
        errors.append("archive_source_finder.py not importable: %s" % e); return
    for c in cands[:TOP_ANALYSE]:
        try:
            a = asf.analyse(c["identifier"])
            c.update(pdf=a.get("pdf"), pdf_mb=a.get("pdf_mb"), pdf_url=a.get("pdf_url"), txt=a.get("txt"),
                     txt_url=a.get("txt_url"))
            if a.get("txt_url"):
                raw = _http(a["txt_url"], timeout=60, rng=PURITY_BYTES).decode("utf-8", "replace")
                c["purity"] = round(asf.dev_ratio(raw), 3)
        except Exception as e:
            errors.append("%s: %s" % (c.get("identifier"), str(e)[:120]))


def wisdomlib_local(words: list) -> list:
    pages = WISDOMLIB_ARCHIVE / "pages"
    if not pages.is_dir() or not words:
        return []
    nw = [norm(w) for w in words]
    books = {}
    for meta in pages.glob("*/meta.json"):
        try:
            m = json.loads(meta.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        url, title = m.get("url", ""), m.get("title", "")
        mm = re.search(r"wisdomlib\.org/([a-z\-]+)/(?:book|compilation)/([^/]+)", url)
        if not mm:
            continue
        hay = norm(title + " " + mm.group(2).replace("-", " "))
        hit = sum(1 for w in nw if w in hay)
        if hit >= max(1, len(nw) // 2):
            b = books.setdefault(mm.group(2), {"book": mm.group(2), "section": mm.group(1), "pages": 0, "hit": hit,
                                               "url": "https://www.wisdomlib.org/%s/book/%s" % (mm.group(1), mm.group(2))})
            b["pages"] += 1
    return sorted(books.values(), key=lambda b: (-b["hit"], -b["pages"]))[:8]


def links(words: list) -> list:
    q = " ".join(words[:4])
    e = urllib.parse.quote_plus
    return [
        {"name": "GRETIL (Unicode e-texts)", "url": "https://www.google.com/search?q=" + e("site:gretil.sub.uni-goettingen.de " + q)},
        {"name": "sanskritdocuments.org", "url": "https://www.google.com/search?q=" + e("site:sanskritdocuments.org " + q)},
        {"name": "Digital Sanskrit Buddhist Canon", "url": "https://www.google.com/search?q=" + e("site:dsbcproject.org " + q)},
        {"name": "wisdomlib.org", "url": "https://www.wisdomlib.org/index.php?type=search&query=" + e(q)},
        {"name": "archive.org", "url": BASE + "/search?query=" + e(q) + "&sin=TXT"},
    ]


def ai_judge(doc: str, words: list, cands: list, max_usd: float, errors: list) -> float:
    """One Gemini call that says, for each candidate, whether it is the same work and what kind of
    edition it is. Returns the dollars it cost (estimated)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        errors.append("AI: GEMINI_API_KEY is not set"); return 0.0
    try:
        import google.generativeai as genai
    except Exception as e:
        errors.append("AI: google-generativeai is not installed (%s)" % e); return 0.0
    items = [{"identifier": c["identifier"], "title": one(c.get("title"))[:160], "creator": one(c.get("creator"))[:80],
              "publisher": one(c.get("publisher"))[:80], "year": one(c.get("year") or c.get("date"))[:12],
              "language": one(c.get("language"))[:30], "devanagari_purity": c.get("purity")} for c in cands[:12]]
    prompt = ("You are a Sanskrit philologist choosing the best printed edition of a text to digitise.\n"
              "The text: %s (searched as: %s).\nFor each candidate below say whether it is the same work "
              "(same_work true/false), what kind of edition it is (edition_kind: critical | scholarly | popular | "
              "unknown), and why in under 20 words. A critical edition collates manuscripts and gives variants "
              "(e.g. BORI, GOS); a scholarly edition is a careful edition with or without commentary (e.g. "
              "Anandashrama, Nirnaya Sagar, Chowkhamba, Kashi Sanskrit Series); popular is a reprint or a "
              "translation-led book. Answer only JSON: a list of {identifier, same_work, edition_kind, why}.\n\n%s"
              % (doc, " ".join(words), json.dumps(items, ensure_ascii=False)))
    est = (len(prompt) / 4 * 0.30 + 900 * 2.50) / 1e6          # gemini-2.5-flash prices, $ per token
    if est > max_usd:
        errors.append("AI: estimate $%.4f is above --max-usd %.4f" % (est, max_usd)); return 0.0
    genai.configure(api_key=key)
    gm = genai.GenerativeModel("gemini-2.5-flash", generation_config=genai.GenerationConfig(
        temperature=0.1, max_output_tokens=4096, response_mime_type="application/json"))
    t0 = time.time()
    resp = gm.generate_content(prompt)
    text = (getattr(resp, "text", "") or "").strip()
    try:
        ans = json.loads(text)
    except ValueError:
        m = re.search(r"\[.*\]", text, re.S)
        ans = json.loads(m.group(0)) if m else []
    by = {a.get("identifier"): a for a in ans if isinstance(a, dict)}
    for c in cands:
        if c["identifier"] in by:
            a = by[c["identifier"]]
            c["ai"] = {"same_work": bool(a.get("same_work", True)), "edition_kind": a.get("edition_kind"),
                       "why": str(a.get("why") or "")[:200]}
    try:
        import cost_tracker
        con = sqlite3.connect(str(ROOT / "data" / "context.db"), timeout=30)
        try:
            u = getattr(resp, "usage_metadata", None)
            cost_tracker.log_api_call(con, kind="source_desk", doc=doc, engine="gemini:gemini-2.5-flash",
                                      in_chars=len(prompt), out_chars=len(text), duration_s=time.time() - t0,
                                      passages=0, ok=bool(by),
                                      in_tokens=getattr(u, "prompt_token_count", None) if u else None,
                                      out_tokens=getattr(u, "candidates_token_count", None) if u else None)
            con.commit()
        finally:
            con.close()
    except Exception as e:
        errors.append("AI: the call was not recorded in usage_log (%s)" % str(e)[:100])
    return est


def doc_title(db: str, doc: str):
    try:
        con = sqlite3.connect("file:%s?mode=ro" % Path(db).as_posix(), uri=True, timeout=10)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(docs)")}
            if "title" in cols:
                r = con.execute("SELECT title FROM docs WHERE code=?", (doc,)).fetchone()
                return r[0] if r and r[0] else None
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return None


def find(a) -> int:
    words = title_words(a.doc, a.title or doc_title(a.db, a.doc))
    nums = scan_numbers(a.doc)
    errors, cands = [], []
    if not a.offline:
        try:
            cands = archive_search(words, a.rows)
        except (urllib.error.URLError, OSError, ValueError) as e:
            errors.append("archive.org search: %s" % str(e)[:160])
    for c in cands:
        c["source"] = "archive.org"
        c["score"], c["why"] = score(c, words, nums)
    cands.sort(key=lambda c: -c["score"])
    if cands and not a.offline:
        analyse_top([c for c in cands if not c.get("current_scan")], errors)
    usd = 0.0
    if a.ai and cands:
        try:
            usd = ai_judge(a.doc, words, cands, a.max_usd, errors)
        except Exception as e:
            errors.append("AI: %s" % str(e)[:160])
    for c in cands:
        c["score"], c["why"] = score(c, words, nums)
        ident = c["identifier"]
        c.update(details_url=BASE + "/details/" + ident, embed_url=BASE + "/embed/" + ident,
                 title=one(c.get("title")), creator=one(c.get("creator")), publisher=one(c.get("publisher")),
                 year=one(c.get("year") or c.get("date"))[:10], language=one(c.get("language")),
                 description=one(c.get("description"))[:400], pages=int(c.get("imagecount") or 0))
        c.pop("subject", None); c.pop("date", None); c.pop("imagecount", None)
    cands.sort(key=lambda c: -c["score"])
    out = {"doc": a.doc, "mark": MARK, "at": datetime.datetime.now().isoformat(timespec="seconds"), "words": words,
           "candidates": cands, "wisdomlib_local": wisdomlib_local(words), "links": links(words), "errors": errors,
           "ai_usd": round(usd, 4)}
    d = Path(a.out); d.mkdir(parents=True, exist_ok=True)
    p = d / ("%s.json" % a.doc)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("%s  %s  searched as: %s" % (a.doc, MARK, " ".join(words) or "(nothing to search by)"))
    for c in cands[:10]:
        print("  %5.1f  %-40s %-6s %-14s %s" % (c["score"], c["identifier"][:40], c["year"][:6], c["language"][:14],
                                               c["title"][:60]))
        print("         " + "; ".join(c["why"]))
    for b in out["wisdomlib_local"][:3]:
        print("  wisdomlib (local archive): %s, %d pages: %s" % (b["book"], b["pages"], b["url"]))
    for e in errors:
        print("  note: " + e)
    print("  wrote %s" % p)
    best = next((c for c in cands if not c.get("current_scan")), None)
    if best:
        print("VERDICT: %d candidate(s); the best is %s (%s%s), score %.0f: %s" % (
            len(cands), best["title"][:80] or best["identifier"], best["publisher"][:40] or "publisher not given",
            (", " + best["year"]) if best["year"] else "", best["score"], "; ".join(best["why"][:4])))
        print("NEXT: open the Source desk on the repair page to preview and fetch; or python scripts\\source_desk.py "
              "--doc %s --fetch %s --kind pdf" % (a.doc, best["identifier"]))
    else:
        print("VERDICT: no edition found on archive.org%s; look at the e-text sites (GRETIL, sanskritdocuments.org)"
              % (" (the search failed: %s)" % errors[0] if errors and not cands else ""))
        print("NEXT: " + out["links"][0]["url"])
    return 0


def fetch(a) -> int:
    ident = a.fetch
    if not re.match(r"^[A-Za-z0-9._\-]+$", ident):
        print("FAIL: unexpected characters in the identifier."); return 2
    try:
        import archive_source_finder as asf
        info = asf.analyse(ident)
    except Exception as e:
        print("VERDICT: could not read %s on archive.org: %s" % (ident, str(e)[:160])); print("NEXT: "); return 1
    dest = Path(a.dest or (ROOT / "sources" / a.doc)); dest.mkdir(parents=True, exist_ok=True)
    if a.kind == "pdf":
        if not info.get("pdf_url"):
            print("VERDICT: %s has no PDF; try --kind text" % ident); print("NEXT: "); return 1
        name, url = "%s.pdf" % ident, info["pdf_url"]
    else:
        if not info.get("txt_url"):
            print("VERDICT: %s has no OCR text; try --kind pdf" % ident); print("NEXT: "); return 1
        try:   # QUALITY_2026_10_11: archive.org answered 500 for the Natyasastra's OCR text on 11 Oct (a traceback)
            sample = _http(info["txt_url"], timeout=60, rng=PURITY_BYTES).decode("utf-8", "replace")
        except Exception as e:
            print("VERDICT: archive.org did not give %s's OCR text (%s): %s" % (ident, str(e)[:120], info["txt_url"]))
            print("NEXT: python scripts\\source_desk.py --doc %s --fetch %s --kind pdf   (or try again later)" % (a.doc, ident))
            return 1
        pur = asf.dev_ratio(sample)
        if pur < 0.85 and not a.force:
            print("VERDICT: refused: its OCR text is %.0f%% Devanagari (under 85%%); it would pollute the corpus. "
                  "Fetch the PDF and OCR it with vision instead." % (100 * pur))
            print("NEXT: python scripts\\source_desk.py --doc %s --fetch %s --kind pdf" % (a.doc, ident)); return 1
        name, url = "%s_djvu.txt" % ident, info["txt_url"]
    target = dest / name
    print("fetching %s (%s MB) ..." % (url, info.get("pdf_mb") if a.kind == "pdf" else "?"), flush=True)
    try:   # QUALITY_2026_10_11
        data = _http(url, timeout=600)
    except Exception as e:
        print("VERDICT: the download of %s failed (%s); nothing was saved" % (url, str(e)[:160]))
        print("NEXT: python scripts\\source_desk.py --doc %s --fetch %s --kind %s   (try again later)" % (a.doc, ident, a.kind))
        return 1
    tmp = target.with_name(target.name + ".part"); tmp.write_bytes(data); os.replace(tmp, target)
    side = {"doc": a.doc, "identifier": ident, "kind": a.kind, "url": url, "details": BASE + "/details/" + ident,
            "title": info.get("title"), "year": info.get("year"), "language": info.get("language"),
            "bytes": len(data), "at": datetime.datetime.now().isoformat(timespec="seconds"), "mark": MARK}
    target.with_name(target.name + ".json").write_text(json.dumps(side, ensure_ascii=False, indent=1), encoding="utf-8")
    print("VERDICT: saved %s (%.1f MB) with its provenance beside it" % (target, len(data) / 1e6))
    if a.kind == "pdf":
        print("NEXT: import it as a new witness: Dashboard, Import path to inbox: %s (it becomes its own text; OCR it "
              "with vision)" % target)
    else:
        print('NEXT: python scripts\\etext_witness.py --doc %s --file "%s"   (ETEXT_WITNESS_2026_10_11: read it as a '
              'witness, free)' % (a.doc, target))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find a better edition of one text (SOURCE_DESK_2026_10_11)")
    ap.add_argument("--doc", required=True)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--title", default=None, help="search by this title instead of the text's code")
    ap.add_argument("--rows", type=int, default=25)
    ap.add_argument("--ai", action="store_true")
    ap.add_argument("--max-usd", type=float, default=0.02)
    ap.add_argument("--offline", action="store_true", help="no network: the local wisdomlib archive and the links only")
    ap.add_argument("--out", default="data/source_desk")
    ap.add_argument("--fetch", default=None, metavar="IDENTIFIER")
    ap.add_argument("--kind", choices=("pdf", "text"), default="pdf")
    ap.add_argument("--dest", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if not re.match(r"^[A-Za-z0-9_\-]+$", a.doc):
        print("FAIL: --doc <code> is needed (letters, digits, _ and -)."); return 2
    os.chdir(ROOT)
    return fetch(a) if a.fetch else find(a)


if __name__ == "__main__":
    sys.exit(main())
