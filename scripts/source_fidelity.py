#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
source_fidelity.py  (2026-10-22)  FIDELITY_2026_10_22

How faithfully does the Sanskrit we translate read? Letter by letter, against an independent e-text; and, where two
readings of one print exist (our vision OCR and Tesseract's, ours and archive.org's), which of the two is the better.
Read-only and free: no API is called, the database is opened read-only and nothing in it is written.

  reference  --ref witness:<code>   an e-text witness's page JSONL (data/raw_witness/<code>/), its appendix left out
                   db:<doc>         a text's passages in the database (noise and front matter left out)
                   file:<path>      a text file, its paragraphs the units
             --prefix 14.           only the units whose reference starts so (a kanda, a chapter)
  readings   --cand db:<doc>        what is translated: the text's passages, page by page
                   vision:<doc>     data/raw_vision/<doc>_NNNN.jsonl, the vision OCR of our scan
                   raw:<doc>        data/raw/<doc>_NNNN.jsonl, the first OCR of our scan (Tesseract, mostly)
                   pages:<dir>/<doc> <dir>/<doc>_NNNN.jsonl, any other engine's OCR of our scan, one JSON line
                                    with its "text" a line of the page (ENGINES_2026_10_22: another engine is
                                    measured by the same checks as ours before its reading is trusted or ingested),
                                    e.g. pages:data/raw_vision_pro/markandeya_purana
                   file:<path>      a text file: an archive.org OCR (_djvu.txt), an e-text
                   witness:<code>   another witness
  measured   each reference unit is found in each reading (7-letter anchors unique in the reference vote for one
             place; the first and the last anchor bound it), then aligned letter by letter with difflib's matcher,
             whose edit script is never shorter than the true edit distance: the error rates are upper bounds. What
             the reading has before the unit's first letter and after its last is not counted. Letters are compared
             after folding what the editions and the typesetting disturb and the meaning does not: spaces,
             punctuation, dandas, numbers, accents, avagraha and nukta dropped; a nasal before a consonant, a final
             m and the candrabindu read as the anusvara; a final consonant and the vowel after it written as one
             (prag astam as pragastam); a colon after a letter read as the visarga (Tesseract's);
             with --fold-ch, ccha and cha read as ca on both sides (GRETIL's Satapatha lost every "ch").
  one print, two readings  --pair A,B: for the units both read, a letter A misses and B gets is A's own error; one
             both miss is shared: the print's own reading (another edition's), a slip of the e-text, or a place
             both OCRs fail (a damaged page). The own-error rates are the fair comparison of two OCRs of one scan.
  ledger     --ledger: every text in the database with its engines, English, judged level, register, witness and
             the fidelity measured for it; --csv writes it.

  python scripts\\source_fidelity.py --ref db:markandeya_purana__w_gretil --cand db:markandeya_purana --cand raw:markandeya_purana --pair db:markandeya_purana,raw:markandeya_purana
  python scripts\\source_fidelity.py --ref witness:satapatha_madhyandina__w_gretil --prefix 14. --fold-ch --cand db:2015_405693_Shatpath-Brahmanam --cand raw:2015_405693_Shatpath-Brahmanam --pair db:2015_405693_Shatpath-Brahmanam,raw:2015_405693_Shatpath-Brahmanam
  python scripts\\source_fidelity.py --ledger --csv exports\\source_ledger.csv

Writes data/source_fidelity/<ref>[__<prefix>].json (the report) unless --no-write; never the database.
The last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py's, for the dashboard.
"""
from __future__ import annotations
import argparse, csv, datetime, json, os, re, sqlite3, statistics, sys, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

MARK = "FIDELITY_2026_10_22"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

K = 7                      # anchor length, in folded letters
BUCKET = 24                # offsets within a bucket (and its neighbours) are one place
MIN_LETTERS = 12           # a unit shorter than this (a heading, "atha") is too short to find
FOUND = 0.5                # at least half the unit's letters matched, or it is not found
# the steps of the verdict. Against the e-text (another edition's readings and spellings count as differences):
# agreement in % of the e-text's aksharas. With a second reading of the same print (--pair): the reading's own
# misread or missing aksharas per 100, which the editions do not touch. Set on 22 Oct on the three texts measured.
AGREE_FAITHFUL, AGREE_CLOSE, AGREE_DIFFERS = 97.0, 90.0, 80.0
OWN_FAITHFUL, OWN_CLOSE, OWN_USABLE = 1.0, 5.0, 12.0

DROP = re.compile("[\u0951-\u0954\u1cd0-\u1cff\ua8e0-\ua8ff\u0900\u093c\u093d\u200c\u200d]")
COLON_VISARGA = re.compile("(?<=[\u0900-\u0963\u0971-\u097f]):")
FINAL_M = re.compile("\u092e\u094d(?![\u0900-\u0963\u0971-\u097f])(?!\\s*[\u0905-\u0914\u0960\u0961])")
NASAL = re.compile("[\u0919\u091e\u0923\u0928\u092e]\u094d(?=[\u0915-\u0939\u0958-\u095f])")
NOT_LETTER = re.compile("[^\u0902\u0903\u0905-\u0939\u093e-\u094d\u0950\u0960-\u0963\u0972-\u097f]")
# an akshara: a consonant cluster with its vowel sign (or its virama), or a vowel; the anusvara or visarga with it;
# a vowel sign or a mark standing alone (a misreading) is an akshara of its own
AKSHARA = re.compile("(?:[\u0915-\u0939\u0972-\u097f](?:\u094d[\u0915-\u0939\u0972-\u097f])*"
                     "(?:[\u093e-\u094c\u0962\u0963]|\u094d)?|[\u0905-\u0914\u0960\u0961\u0950])[\u0902\u0903]?"
                     "|[\u0902\u0903\u093e-\u094d\u0962\u0963]")
# a final consonant and the vowel after it, written apart (prag astam, the e-text's) or as one (pragastam, the print's)
JOIN = re.compile("(?<=[\u0915-\u0939\u0972-\u097f])\u094d[ \t]*([\u0905-\u0914\u0960\u0961])")   # not across a danda
SIGN = {"\u0905": "", "\u0906": "\u093e", "\u0907": "\u093f", "\u0908": "\u0940", "\u0909": "\u0941",
        "\u090a": "\u0942", "\u090b": "\u0943", "\u0960": "\u0944", "\u090c": "\u0962", "\u0961": "\u0963",
        "\u090d": "\u0945", "\u090e": "\u0946", "\u090f": "\u0947", "\u0910": "\u0948", "\u0911": "\u0949",
        "\u0912": "\u094a", "\u0913": "\u094b", "\u0914": "\u094c"}
SKIP_TYPES = {"noise", "frontmatter"}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def aksharas(s: str) -> list:
    """The folded letters as aksharas: what is counted."""
    return AKSHARA.findall(s or "")


def norm(s: str, fold_ch: bool = False) -> str:
    """The letters that carry the reading (see above), folded alike on both sides."""
    s = unicodedata.normalize("NFC", s or "")
    s = COLON_VISARGA.sub("\u0903", s)
    s = DROP.sub("", s).replace("\u0901", "\u0902")
    s = FINAL_M.sub("\u0902", s)
    s = NASAL.sub("\u0902", s)
    if fold_ch:
        s = s.replace("\u091a\u094d\u091b", "\u091a").replace("\u091b", "\u091a")
    s = JOIN.sub(lambda m: SIGN[m.group(1)], s)
    return NOT_LETTER.sub("", s)


# ---------------------------------------------------------------- readers

def _uri(db: str, immutable: bool) -> str:
    return Path(db).resolve().as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")


def _connect(a):
    return sqlite3.connect(_uri(a.db, a.immutable), uri=True, timeout=10)


def db_rows(a, doc: str) -> list:
    con = _connect(a)
    try:
        return con.execute("SELECT p.page_no, p.idx, p.verse_ref, p.text_type, p.text FROM passages p JOIN docs d "
                           "ON d.id=p.doc_id WHERE d.code=? ORDER BY p.page_no, p.idx", (doc,)).fetchall()
    finally:
        con.close()


def _page_of(name: str) -> int:
    m = re.search(r"_(\d{3,5})\.jsonl$", name)
    return int(m.group(1)) if m else 0


def jsonl_pages(folder: Path, doc: str) -> tuple:
    """({page: text}, {engine: lines}) of <folder>/<doc>_NNNN.jsonl."""
    pages, engines = {}, {}
    for p in sorted(folder.glob("%s_[0-9]*.jsonl" % doc)):
        if not re.fullmatch(re.escape(doc) + r"_\d{3,5}\.jsonl", p.name):
            continue
        parts = []
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            parts.append(r.get("text") or "")
            e = r.get("engine") or ""
            engines[e] = engines.get(e, 0) + 1
        pages[_page_of(p.name)] = "\n".join(parts)
    return pages, engines


def witness_records(root: Path, code: str) -> list:
    out = []
    for p in sorted((root / "data" / "raw_witness" / code).glob("%s_[0-9]*.jsonl" % code)):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def file_text(path: Path) -> str:
    """The text of a file as etext_witness.py reads it (HTML to text, its encodings)."""
    import etext_witness as ew
    text, _info = ew.read_text(path)
    return text


def load(a, spec: str, as_ref: bool):
    """A reference (units: [(ref, text)]) or a reading (pages: [(page, text)]) from its spec; and a note."""
    kind, _, name = spec.partition(":")
    root = Path(a.root)
    if kind == "db":
        rows = db_rows(a, name)
        if not rows:
            raise SystemExit("not in the database: %s" % name)
        if as_ref:
            return [(r[2] or "p%s.%s" % (r[0], r[1]), r[4] or "") for r in rows
                    if (r[3] or "mula") not in SKIP_TYPES], "%d passages" % len(rows)
        pages = {}
        for r in rows:
            pages.setdefault(int(r[0] or 0), []).append(r[4] or "")
        return sorted((p, "\n".join(v)) for p, v in pages.items()), "%d passages on %d pages" % (len(rows), len(pages))
    if kind == "witness":
        recs = witness_records(root, name)
        if not recs:
            raise SystemExit("no witness pages: data/raw_witness/%s" % name)
        if as_ref:
            units = [(r.get("verse_ref") or "", r.get("text") or "") for r in recs
                     if (r.get("text_type") or "mula") not in SKIP_TYPES and r.get("verse_ref")
                     and not (r.get("meta") or {}).get("after_separator")]
            return units, "%d records, %d units (its appendix left out)" % (len(recs), len(units))
        pages = {}
        for r in recs:
            pages.setdefault(int(r.get("page_no") or 0), []).append(r.get("text") or "")
        return sorted((p, "\n".join(v)) for p, v in pages.items()), "%d records" % len(recs)
    if kind in ("vision", "raw", "pages"):
        folder = root / "data" / ("raw_vision" if kind == "vision" else "raw")
        if kind == "pages":   # ENGINES_2026_10_22: pages:<dir>/<doc>, the folder relative to --root or absolute
            d, _, name = name.replace("\\", "/").rpartition("/")
            if not d or not name:
                raise SystemExit("pages: wants a folder and a doc: pages:data/raw_vision_pro/<doc>")
            folder = Path(d) if Path(d).is_absolute() else root / d
        pages, engines = jsonl_pages(folder, name)
        if not pages:
            raise SystemExit("no pages: %s" % (folder / ("%s_NNNN.jsonl" % name)))
        top = ", ".join("%s %d" % (e or "?", n) for e, n in sorted(engines.items(), key=lambda x: -x[1])[:3])
        if as_ref:
            return [("p%d" % p, t) for p, t in sorted(pages.items())], "%d pages (%s)" % (len(pages), top)
        return sorted(pages.items()), "%d pages (%s)" % (len(pages), top)
    if kind == "file":
        path = Path(name) if Path(name).is_absolute() else root / name
        if not path.exists():
            raise SystemExit("no such file: %s" % path)
        text = file_text(path)
        if as_ref:
            paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
            return [("u%d" % (i + 1), p) for i, p in enumerate(paras)], "%d paragraphs" % len(paras)
        chunks = text.split("\f") if "\f" in text else None
        if not chunks:
            lines = text.splitlines()
            chunks = ["\n".join(lines[i:i + 80]) for i in range(0, len(lines), 80)]
        return [(i + 1, c) for i, c in enumerate(chunks)], "%d characters in %d pieces" % (len(text), len(chunks))
    raise SystemExit("a spec is db:, witness:, vision:, raw: or file: (%s)" % spec)


# ---------------------------------------------------------------- finding and aligning

def stream(pages: list, fold_ch: bool):
    """The reading as one string of folded letters, and where each page starts in it."""
    parts, starts, pos = [], [], 0
    for pg, text in pages:
        n = norm(text, fold_ch)
        starts.append((pos, pg))
        parts.append(n)
        pos += len(n)
    return "".join(parts), starts


def page_at(starts: list, pos: int):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid][0] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return starts[lo][1] if starts else None


def anchors(units: list, S: str, k: int = K) -> list:
    """For each unit, the places in S its anchors agree on (the best, and a second where the reading gives the unit
    twice: the mula and its words split, a commentary quoting it whole), each as (offset, position in the unit) of
    its first and its last anchor there; [] when there is none."""
    seen = {}
    for u in units:
        for g in {u[i:i + k] for i in range(len(u) - k + 1)}:
            seen[g] = seen.get(g, 0) + 1
    index = {}
    for ui, u in enumerate(units):
        for i in range(len(u) - k + 1):
            g = u[i:i + k]
            if seen[g] == 1 and g not in index:
                index[g] = (ui, i)
    del seen
    freq, hits = {}, [[] for _ in units]
    for p in range(len(S) - k + 1):
        g = S[p:p + k]
        t = index.get(g)
        if t is not None:
            freq[g] = freq.get(g, 0) + 1
            hits[t[0]].append((p - t[1], t[1], g))
    out = []
    for ui, hs in enumerate(hits):
        places = []
        if hs:
            votes = {}
            for off, _, g in hs:
                b = off // BUCKET
                votes[b] = votes.get(b, 0.0) + 1.0 / freq[g]
            floor = max(2.0, 0.05 * max(1, len(units[ui]) - k + 1))
            near = lambda b: votes.get(b - 1, 0.0) + votes.get(b, 0.0) + votes.get(b + 1, 0.0)
            taken = []
            for b in sorted(votes, key=lambda b: (-near(b), b)):
                if len(taken) == 2 or near(b) < floor:
                    break
                if any(abs(b - c) <= 3 for c in taken):
                    continue
                taken.append(b)
                sel = sorted((up, off) for off, up, _ in hs if abs(off // BUCKET - b) <= 1)
                places.append((sel[0][1], sel[0][0], sel[-1][1], sel[-1][0]))
        out.append(places)
    return out


def align(u: str, S: str, where):
    """The unit u against S where its anchors put it, akshara by akshara: errors (an upper bound of the edit
    distance), which of u's aksharas the reading has, what it adds where, and the differences. What the reading has
    before the unit's first akshara and after its last is not counted."""
    tu = aksharas(u)
    L = len(tu)
    off0, up0, off1, up1 = where
    lo = max(0, off0 - 10 - int(0.2 * up0))
    hi = min(len(S), off1 + len(u) + 10 + int(0.2 * (len(u) - up1)))
    while lo > 0 and S[lo] in "\u093e\u093f\u0940\u0941\u0942\u0943\u0944\u0945\u0946\u0947\u0948\u0949\u094a\u094b\u094c\u094d\u0902\u0903\u0962\u0963":
        lo -= 1                                        # never start inside an akshara
    tw = aksharas(S[lo:hi])
    if not L or not tw:
        return None
    ops = SequenceMatcher(None, tu, tw, autojunk=False).get_opcodes()
    ok, ins, err, diffs = bytearray(L), {}, 0, []
    got = [""] * L                                     # TRIANGULATE_2026_10_22: what the reading has at each akshara
    first_k = last_k = None
    shift0 = 0
    for n, (tag, i1, i2, k1, k2) in enumerate(ops):
        edge0, edge1 = n == 0, n == len(ops) - 1
        if tag == "insert" and (edge0 or edge1):
            continue                                   # the reading's text before or after the unit
        if tag == "replace" and (edge0 or edge1) and k2 - k1 > i2 - i1:
            if edge0:
                k1 = k2 - (i2 - i1)
            else:
                k2 = k1 + (i2 - i1)
        if tag == "replace" and i2 - i1 == 1 and k2 - k1 == 1:
            # a unit's last consonant run into the next unit's first in the reading, or its first into the last
            # one's (vakca: the aksharas of the joined letters differ, the letters do not)
            if i2 == L and tu[i1].endswith("\u094d") and tw[k1].startswith(tu[i1]):
                tag = "equal"
            elif i1 == 0 and tw[k1].endswith(tu[i1]) and tw[k1][:-len(tu[i1])].endswith("\u094d"):
                tag = "equal"
                shift0 = len(tw[k1]) - len(tu[i1])
        if first_k is None:
            first_k = k1
        last_k = k2
        if tag == "equal":
            for i in range(i1, i2):
                ok[i] = 1
                got[i] = tu[i]
        elif tag == "replace":
            for d, i in enumerate(range(i1, i2)):
                got[i] = tw[k1 + d] if k1 + d < k2 else ""
            err += max(i2 - i1, k2 - k1)
            if k2 - k1 > i2 - i1:
                ins[i2] = ins.get(i2, 0) + (k2 - k1) - (i2 - i1)
            diffs.append(("".join(tu[i1:i2]), "".join(tw[k1:k2])))
        elif tag == "delete":
            err += i2 - i1
            diffs.append(("".join(tu[i1:i2]), ""))
        elif tag == "insert":
            err += k2 - k1
            ins[i1] = ins.get(i1, 0) + (k2 - k1)
            diffs.append(("", "".join(tw[k1:k2])))
    if sum(ok) < FOUND * L:
        return None
    first_k = first_k or 0
    last_k = last_k if last_k is not None else 0
    return {"err": err, "n": L, "ok": ok, "ins": ins, "diffs": diffs, "got": got,
            "at": lo + len("".join(tw[:first_k])) + shift0, "end": lo + len("".join(tw[:last_k]))}


def measure(units: list, pages: list, fold_ch: bool) -> list:
    S, starts = stream(pages, fold_ch)
    res = []
    for u, places in zip(units, anchors(units, S)):
        best = None
        for wh in places:
            r = align(u, S, wh)
            if r and (best is None or r["err"] < best["err"]):
                best = r
        if best:
            best["page"] = page_at(starts, best["at"])
        res.append(best)
    return res


# ---------------------------------------------------------------- summing up

def _pct(x, n):
    return round(100.0 * x / n, 2) if n else None


def group_of(ref: str, depth: int) -> str:
    m = re.match(r"[pu](\d+)", ref)
    if m:
        n = int(m.group(1))
        return "%s%d-%d" % (ref[0], (n - 1) // 50 * 50 + 1, (n - 1) // 50 * 50 + 50)
    return ".".join(ref.split(".")[:depth])


def summarize(refs: list, units: list, res: list, depth: int, examples: int) -> dict:
    found = [i for i, r in enumerate(res) if r]
    n = len(units)
    letters = sum(res[i]["n"] for i in found)
    err = sum(res[i]["err"] for i in found)
    agree = [max(0.0, 1.0 - res[i]["err"] / float(res[i]["n"])) for i in found]
    out = {"units": n, "found": len(found), "aksharas": letters, "errors": err,
           "agree_pct": round(100.0 - 100.0 * err / letters, 2) if letters else None,
           "unit_median_pct": round(100.0 * statistics.median(agree), 1) if agree else None,
           "exact_pct": _pct(sum(1 for x in agree if x >= 0.99999), len(agree)),
           "ge98_pct": _pct(sum(1 for x in agree if x >= 0.98), len(agree)),
           "ge95_pct": _pct(sum(1 for x in agree if x >= 0.95), len(agree)),
           "lt90_pct": _pct(sum(1 for x in agree if x < 0.90), len(agree))}
    if found:
        fset = set(found)
        core = [i for i in found if any(j in fset for j in range(i - 5, i + 6) if j != i)] or found
        lo, hi = min(core), max(core)
        missing = [i for i in range(lo, hi + 1) if not res[i]]
        out.update(span=[refs[lo], refs[hi]], span_units=hi - lo + 1, missing_in_span=len(missing),
                   missing_refs=[refs[i] for i in missing[:40]], isolated=len(found) - len(core),
                   pages=[min(res[i]["page"] for i in found), max(res[i]["page"] for i in found)])
        order = sum(1 for x, y in zip(found, found[1:]) if res[y]["at"] >= res[x]["at"])
        out["in_order_pct"] = _pct(order, len(found) - 1) if len(found) > 1 else 100.0
    conf = {}
    for i in found:
        for x, y in res[i]["diffs"]:
            if max(len(x), len(y)) <= 3:
                conf[(x, y)] = conf.get((x, y), 0) + 1
    out["confusions"] = [[x, y, c] for (x, y), c in sorted(conf.items(), key=lambda t: -t[1])[:15]]
    groups = {}
    for i in range(n):
        g = groups.setdefault(group_of(refs[i], depth), [0, 0, 0, 0])
        g[0] += 1
        if res[i]:
            g[1] += 1
            g[2] += res[i]["n"]
            g[3] += res[i]["err"]
    out["groups"] = [[g, v[0], v[1], round(100.0 - 100.0 * v[3] / v[2], 2) if v[2] else None]
                     for g, v in groups.items()]
    worst = sorted(found, key=lambda i: res[i]["err"] / float(res[i]["n"]), reverse=True)[:examples]
    out["worst"] = [{"ref": refs[i], "page": res[i]["page"],
                     "agree_pct": round(100.0 - 100.0 * res[i]["err"] / res[i]["n"], 1),
                     "diffs": [[x, y] for x, y in res[i]["diffs"][:4]]} for i in worst]
    return out


def pair(units: list, ra: list, rb: list, refs: list = None, keep: int = 200) -> dict:
    """Two readings of one print, over the units both read: each of the reference's aksharas that one reading lacks
    (misread or missing) and the other has is the first's own error; one both lack is shared. Aksharas a reading
    adds are counted apart: where they go is less sure. TRIANGULATE_2026_10_22: where both lack it and both have the
    same akshara instead, the two readings agree against the reference ("outvoted"): when the reference is one of our
    own readings, that is where it is most likely misread (when it is an e-text, where the print reads otherwise);
    the first `keep` of them are kept as the mends to read beside the page."""
    both = [i for i in range(len(units)) if ra[i] and rb[i]]
    L = own_a = own_b = shared = add_a = add_b = add_shared = outvoted = 0
    mends = []
    ca, cb, co = {}, {}, {}                            # the substitutions: a's own, b's own, the outvoted
    for i in both:
        oa, ob = ra[i]["ok"], rb[i]["ok"]
        ga, gb = ra[i].get("got") or [], rb[i].get("got") or []
        tu = aksharas(units[i])
        L += ra[i]["n"]
        for j in range(ra[i]["n"]):
            if not oa[j] and not ob[j]:
                shared += 1
                if j < len(ga) and j < len(gb) and ga[j] and ga[j] == gb[j]:
                    outvoted += 1
                    co[(tu_j(units, i, j, tu), ga[j])] = co.get((tu_j(units, i, j, tu), ga[j]), 0) + 1
                    if len(mends) < keep:
                        mends.append({"ref": refs[i] if refs else i, "page": ra[i].get("page"),
                                      "before": "".join(tu[max(0, j - 4):j]), "reference": tu[j], "readings": ga[j],
                                      "after": "".join(tu[j + 1:j + 5])})
            elif not oa[j]:
                own_a += 1
                if j < len(ga) and ga[j]:
                    ca[(tu_j(units, i, j, tu), ga[j])] = ca.get((tu_j(units, i, j, tu), ga[j]), 0) + 1
            elif not ob[j]:
                own_b += 1
                if j < len(gb) and gb[j]:
                    cb[(tu_j(units, i, j, tu), gb[j])] = cb.get((tu_j(units, i, j, tu), gb[j]), 0) + 1
        ia, ib = ra[i]["ins"], rb[i]["ins"]
        for j in set(ia) | set(ib):
            x, y = ia.get(j, 0), ib.get(j, 0)
            add_shared += min(x, y)
            add_a += x - min(x, y)
            add_b += y - min(x, y)
    own_overlap = _overlap(ca, cb)
    out_overlap = max(_overlap(co, ca), _overlap(co, cb))
    # a reading that is the reference's own text again (the repair beside the vision it was made from) is no witness
    same = "a" if L and (own_a + shared) < SAME_TEXT * L else ("b" if L and (own_b + shared) < SAME_TEXT * L else "")
    return {"units": len(both), "aksharas": L, "own_a_per100": _pct(own_a, L), "own_b_per100": _pct(own_b, L),
            "shared_per100": _pct(shared, L), "added_a_per100": _pct(add_a, L), "added_b_per100": _pct(add_b, L),
            "added_shared_per100": _pct(add_shared, L), "outvoted_per100": _pct(outvoted, L), "outvoted": outvoted,
            "own_a": own_a, "own_b": own_b, "shared": shared, "mends": mends,
            "own_overlap": own_overlap, "outvoted_overlap": out_overlap, "same_text": same,
            "independent": not same and own_overlap < SAME_OWN and out_overlap < SAME_OUTVOTED}


# TRIANGULATE_2026_10_22: two readings that make the same mistakes are not two witnesses. On 22 Oct, Tesseract and
# archive.org's text layer of the same scan (DLI 2015.405693): their own misreadings overlapped 0.25 and the places
# they agreed against our vision text looked like their own mistakes, 0.40 (bha read ma, tha read ya); Tesseract and
# GRETIL's Markandeya: 0.04 and 0.11. The vote of a pair over these is no evidence against the reference.
# On 80 of its pages the same pair's own misreadings were alike 0.19; a pair of independent readings 0.04 to 0.06.
SAME_OWN, SAME_OUTVOTED = 0.12, 0.30
SAME_TEXT = 0.001          # a reading that lacks fewer than 1 in 1,000 of the reference's aksharas is its text again
TOP = 30


def tu_j(units, i, j, tu):
    return tu[j] if tu is not None and j < len(tu) else ""


def _overlap(x: dict, y: dict) -> float:
    """How alike two profiles of substitutions are: the shared share of their 30 commonest, 0 to 1."""
    def top(c):
        t = sorted(c.items(), key=lambda kv: -kv[1])[:TOP]
        s = float(sum(v for _, v in t)) or 1.0
        return {k: v / s for k, v in t}
    a, b = top(x), top(y)
    return round(sum(min(a[k], b[k]) for k in set(a) & set(b)), 3) if a and b else 0.0


def step_of(agree=None, own=None) -> str:
    """The step of a reading: by its own errors when a second reading of the print measured them, else by its
    agreement with the e-text, which cannot tell a misreading from another edition's reading."""
    if own is not None:
        if own <= OWN_FAITHFUL:
            return "faithful"
        if own <= OWN_CLOSE:
            return "close"
        if own <= OWN_USABLE:
            return "usable"
        return "damaged"
    if agree is None:
        return "not measured"
    if agree >= AGREE_FAITHFUL:
        return "faithful"
    if agree >= AGREE_CLOSE:
        return "close"
    if agree >= AGREE_DIFFERS:
        return "differs"
    return "damaged"


STEP_WORDS = {
    "faithful": "faithful: keep it",
    "close": "close: keep it; mend its misreadings from the other reading",
    "usable": "usable: mend it before the edition",
    "differs": "differs: misreadings or another edition; measure a second reading of the print to tell them apart",
    "damaged": "damaged: the e-text or a new OCR replaces it",
    "not measured": "not measured"}


def own_of(pairs: list, spec: str):
    """(own misread or missing per 100, the other reading's, the other's spec) of spec from the pairs, or None."""
    for p in pairs:
        if p.get("a") == spec:
            return p["own_a_per100"], p["own_b_per100"], p["b"]
        if p.get("b") == spec:
            return p["own_b_per100"], p["own_a_per100"], p["a"]
    return None


def verdict_of(name: str, s: dict, pairs: list = ()) -> str:
    if not s or s.get("agree_pct") is None:
        return "%s: the reference is not found in it" % name
    o = own_of(list(pairs), name)
    head = "%s: %s" % (name, STEP_WORDS[step_of(s["agree_pct"], o[0] if o else None)])
    if o:
        head += "; its own misreadings %s per 100 aksharas (%s's %s on the same pages)" % (o[0], o[2], o[1])
    return head + "; %.2f%% of %d aksharas agree with the e-text in the %d of %d units it reads" % (
        s["agree_pct"], s["aksharas"], s["found"], s["units"])


OUR_READINGS = ("db", "vision", "raw", "pages")   # ENGINES_2026_10_22: pages: is our scan too


def is_ours(spec: str) -> bool:
    """WITNESS_FIX_2026_10_22: a reading of our scan: db:, vision:, raw:, pages:; but not a witness in the database
    (db:<doc>__w_<site>: an e-text, or another's OCR), which TRIANGULATE read as ours: GRETIL's Nirukta was called
    "usable: mend it" where two readings of our print agreed against it, which is where the print reads otherwise."""
    kind, _, name = (spec or "").partition(":")
    return kind in OUR_READINGS and not (kind == "db" and "__w_" in name)


def verdict_of_ours(ref: str, pairs: list) -> str:
    """TRIANGULATE_2026_10_22: no e-text, three readings of one print: the reference (ours) is judged by where the other
    two agree against it, each of them by its own misreadings."""
    p = pairs[0]
    o = p["outvoted_per100"]
    if p.get("same_text"):
        return ("%s: not measured: %s is its own text again, no witness; a reading by another engine, or an e-text, "
                "measures it" % (ref, p["a"] if p["same_text"] == "a" else p["b"]))
    if not p.get("independent", True):
        return ("%s: not measured: %s and %s make the same mistakes (alike %.2f and %.2f): their vote against it is no "
                "evidence; a reading by another engine, or an e-text, measures it" % (
                    ref, p["a"], p["b"], p["own_overlap"], p["outvoted_overlap"]))
    return ("%s: %s; outvoted by %s and %s in %s aksharas per 100 (its likely misreadings, %d to read beside the page); "
            "their own misreadings %s and %s per 100" % (
                ref, STEP_WORDS[step_of(own=o)] if o is not None else "not measured", p["a"], p["b"], o,
                p["outvoted"], p["own_a_per100"], p["own_b_per100"]))


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_.")[:120]


def run(a) -> int:
    refs_units, note = load(a, a.ref, True)
    if a.prefix:
        refs_units = [(r, t) for r, t in refs_units if r.startswith(a.prefix)]
    kept = [(r, norm(t, a.fold_ch)) for r, t in refs_units]
    short = sum(1 for _, u in kept if len(u) < MIN_LETTERS)
    kept = [(r, u) for r, u in kept if len(u) >= MIN_LETTERS]
    refs, units = [r for r, _ in kept], [u for _, u in kept]
    if not units:
        raise SystemExit("no reference units%s" % (" under %s" % a.prefix if a.prefix else ""))
    parts = [len(r.split(".")) for r in refs if r[:1].isdigit()]
    depth = a.group_depth or (2 if parts and statistics.median(parts) >= 3 else 1)
    print("FIDELITY (%s): reference %s%s: %s; %d units of %d letters or more (%d aksharas), %d shorter left out" % (
        MARK, a.ref, (" under " + a.prefix) if a.prefix else "", note, len(units), MIN_LETTERS,
        sum(len(aksharas(u)) for u in units), short))
    print("  folded on both sides: spaces, punctuation, numbers, accents, avagraha, nukta; a nasal before a consonant "
          "and a final m as the anusvara; a final consonant joined to the vowel after it; a colon as the visarga%s" % (
              "; ccha and cha as ca" if a.fold_ch else ""))
    ours = is_ours(a.ref)       # TRIANGULATE_2026_10_22: the reference is one of our readings; WITNESS_FIX_2026_10_22
    report = {"mark": MARK, "at": _now(), "ref": a.ref, "prefix": a.prefix or "", "fold_ch": bool(a.fold_ch),
              "ours": ours,
              "units": len(units), "short_left_out": short, "readings": {}, "pairs": []}
    results = {}
    for spec in a.cand:
        pages, cnote = load(a, spec, False)
        res = measure(units, pages, a.fold_ch)
        results[spec] = res
        s = summarize(refs, units, res, depth, a.examples)
        s["note"] = cnote
        report["readings"][spec] = s
        print()
        print("%s  (%s)" % (spec, cnote))
        if not s["found"]:
            print("  found none of the units")
            continue
        print("  found %d of %d units (%.1f%%) on pages %s-%s; between %s and %s, %d of %d units not found "
              "(%d found far from the rest); in order %.1f%%" % (
                  s["found"], s["units"], 100.0 * s["found"] / s["units"], s["pages"][0], s["pages"][1],
                  s["span"][0], s["span"][1], s["missing_in_span"], s["span_units"], s["isolated"],
                  s["in_order_pct"] or 0))
        print("  aksharas agreeing: %.2f%% of %d (unit median %.1f%%; of the units %.1f%% exact, %.1f%% at 98%% or "
              "more, %.1f%% at 95%% or more, %.1f%% under 90%%)" % (
                  s["agree_pct"], s["aksharas"], s["unit_median_pct"], s["exact_pct"], s["ge98_pct"], s["ge95_pct"],
                  s["lt90_pct"]))
        print("  commonest differences (e-text -> reading): " + "; ".join(
            "%s->%s %d" % (x or "-", y or "-", c) for x, y, c in s["confusions"][:12]))
        if a.groups:
            print("  by part: " + "; ".join("%s %d/%d %s" % (g, f, n, ("%.1f%%" % p) if p is not None else "-")
                                           for g, n, f, p in s["groups"] if f))
        for w in s["worst"]:
            print("  worst %s (page %s) %.1f%%: %s" % (w["ref"], w["page"], w["agree_pct"], " | ".join(
                "%s => %s" % (x or "-", y or "-") for x, y in w["diffs"])))
    for pr in a.pair or []:
        x, _, y = pr.partition(",")
        if x not in results or y not in results:
            print("\npair %s: both must be among the --cand readings" % pr)
            continue
        p = pair(units, results[x], results[y], refs)
        p.update(a=x, b=y)
        report["pairs"].append(p)
        print()
        print("one print, two readings, over the %d units both read (%d aksharas of the %s), per 100 aksharas:" % (
            p["units"], p["aksharas"], "reference" if ours else "e-text"))
        print("  misread or missing: %s's own %s; %s's own %s; shared (the print's reading, the e-text's slip, or a "
              "page both fail) %s" % (x, p["own_a_per100"], y, p["own_b_per100"], p["shared_per100"]))
        print("  added: %s's own %s; %s's own %s; shared %s" % (
            x, p["added_a_per100"], y, p["added_b_per100"], p["added_shared_per100"]))
        # TRIANGULATE_2026_10_22: both readings agree with each other against the reference
        if p["same_text"]:
            print("  NOT INDEPENDENT: %s is the reference's own text again (it lacks fewer than 1 akshara in 1,000 of "
                  "it): no witness. The vote below is no evidence." % (x if p["same_text"] == "a" else y))
        elif not p["independent"]:
            print("  NOT INDEPENDENT: the two make the same mistakes (their own misreadings alike %.2f; where they agree "
                  "against the reference, it looks like their mistakes, %.2f): one engine, or the same weak letters. "
                  "Their vote below is no evidence against the reference." % (p["own_overlap"], p["outvoted_overlap"]))
        print("  the two agree against the reference: %s per 100 (%d aksharas)%s" % (
            p["outvoted_per100"], p["outvoted"],
            ": the reference's likely misreadings, the mends to read beside the page" if ours else
            ": where the print reads otherwise than the e-text (another edition, or the e-text's slip)"))
        for m in p["mends"][:a.examples]:
            print("    %s (page %s): %s[%s -> %s]%s" % (m["ref"], m["page"], m["before"], m["reference"],
                                                       m["readings"], m["after"]))
    first = report["readings"].get(a.cand[0])
    if not a.no_write:
        out_dir = Path(a.out_dir) if a.out_dir else Path(a.root) / "data" / "source_fidelity"
        out_dir.mkdir(parents=True, exist_ok=True)
        first_name = a.cand[0].split(":", 1)[-1].replace("\\", "/").rsplit("/", 1)[-1]
        name = (_safe(a.ref.split(":", 1)[-1]) + (("__" + _safe(a.prefix)) if a.prefix else "") + "__" +
                _safe(first_name)[:60] + ".json")
        report["per_unit"] = [[refs[i], len(aksharas(units[i]))] + [
            (round(100.0 - 100.0 * results[c][i]["err"] / results[c][i]["n"], 1) if results[c][i] else None)
            for c in a.cand] for i in range(len(units))]
        (out_dir / name).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nwritten: %s" % (out_dir / name))
    print()
    if ours and report["pairs"]:
        print("VERDICT: " + verdict_of_ours(a.ref, report["pairs"]))
    else:
        print("VERDICT: " + verdict_of(a.cand[0], first, report["pairs"]))
    print("NEXT: read the worst units beside the print, then decide per text (docs/FIDELITY_2026-10-22.md)")
    print("ALSO: python scripts\\source_fidelity.py --ledger")
    return 0


# ---------------------------------------------------------------- the ledger

def _jsonl_by_doc(path: Path, need: str = "") -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("doc") and (not need or need in r):
                out[r["doc"]] = r
    return out


def _fidelity(root: Path, out_dir) -> dict:
    """{doc: {agree, own, other, other_own, ref, prefix, found, units}} from the reports written: per doc, the one
    that found most of the reference."""
    out = {}
    d = Path(out_dir) if out_dir else root / "data" / "source_fidelity"
    for p in (sorted(d.glob("*.json")) if d.exists() else []):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for spec, s in (r.get("readings") or {}).items():
            if not spec.startswith("db:") or s.get("agree_pct") is None:
                continue
            o = own_of(r.get("pairs") or [], spec)
            row = {"agree": s["agree_pct"], "own": o[0] if o else None, "other": o[2] if o else "",
                   "other_own": o[1] if o else None, "ref": r.get("ref") or "", "prefix": r.get("prefix") or "",
                   "found": s.get("found") or 0, "units": s.get("units") or 0}
            doc = spec[3:]
            if doc not in out or row["found"] > out[doc]["found"]:
                out[doc] = row
    return out


def source_of(engines: list, n: int) -> str:
    """What made a text's letters, from its passages' engines: e-text, vision, tesseract, mixed, unknown."""
    share = {}
    for e, c in engines:
        e = (e or "").lower()
        k = ("e-text" if ("etext" in e or "gretil" in e) else "vision" if "vision" in e else
             "tesseract" if "tesseract" in e else "unknown")
        share[k] = share.get(k, 0) + c
    if not share:
        return "unknown"
    k, c = max(share.items(), key=lambda x: x[1])
    return k if c >= 0.5 * n else "mixed"


def reading_of(status: str, level: str, fid, source: str) -> str:
    """What the numbers say about the text we translate (the decision stays the user's)."""
    if status == "withdrawn":
        return "withdrawn"
    if status == "witness":
        return "an e-text witness, local only"
    if fid:
        return STEP_WORDS[step_of(fid["agree"], fid["own"])]
    if source == "e-text":
        return "an e-text: its letters are its edition's; read it against a print for the inputter's slips"
    if level == "material":
        return "material damage (judge): a better source wanted"
    if level == "moderate":
        return "moderate damage (judge): repair, or an e-text"
    if level == "cosmetic":
        return "cosmetic by the judge, who sees Latin debris only; its letters not measured"
    return "not judged; its letters not measured"


def ledger(a) -> int:
    root = Path(a.root)
    reg = _jsonl_by_doc(root / "data" / "source_verdicts.jsonl")
    wit = _jsonl_by_doc(root / "data" / "witnesses.jsonl", "coverage")
    fid = _fidelity(root, a.out_dir)
    judged_dir = root / "data" / "source_judged"
    rows = []
    con = _connect(a)
    try:
        has_sch = bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='scholar_translations'"
                                   ).fetchone())
        for did, code, cat in con.execute("SELECT id, code, COALESCE(category,'') FROM docs ORDER BY code").fetchall():
            n, en = con.execute("SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(translation,''))<>'' THEN 1 ELSE 0 END) "
                                "FROM passages WHERE doc_id=?", (did,)).fetchone()
            if not n:
                continue
            eng = con.execute("SELECT COALESCE(NULLIF(ocr_engine,''),'?'), COUNT(*) FROM passages WHERE doc_id=? "
                              "GROUP BY 1 ORDER BY 2 DESC", (did,)).fetchall()
            sch = con.execute("SELECT COUNT(DISTINCT st.passage_id) FROM scholar_translations st JOIN passages p "
                              "ON p.id=st.passage_id WHERE p.doc_id=?", (did,)).fetchone()[0] if has_sch else 0
            j = {}
            jp = judged_dir / ("%s.json" % code)
            if jp.exists():
                try:
                    j = json.loads(jp.read_text(encoding="utf-8"))
                except ValueError:
                    j = {}
            w = wit.get(code) or {}
            f = fid.get(code)
            st = (reg.get(code) or {}).get("status") or ""
            src = source_of(eng, n)
            rows.append({
                "doc": code, "category": cat, "register": st, "source": src, "passages": int(n),
                "english_pct": _pct(en or 0, n), "scholarly": int(sch or 0),
                "engines": "; ".join("%s %d%%" % (e, round(100.0 * c / n)) for e, c in eng[:3]),
                "judged": j.get("level") or "", "misread_pct": j.get("misread_pct"),
                "vision_agree": j.get("agree_median"), "witness": w.get("witness") or "",
                "witness_coverage": w.get("coverage"),
                "fidelity_pct": f["agree"] if f else None, "own_per100": f["own"] if f else None,
                "other_reading": f["other"] if f else "", "other_own_per100": f["other_own"] if f else None,
                "fidelity_of": ("%s%s %s/%s" % (f["ref"], (" " + f["prefix"]) if f["prefix"] else "", f["found"],
                                                 f["units"])) if f else "",
                "reading": reading_of(st, j.get("level") or "", f, src)})
    finally:
        con.close()
    print("LEDGER (%s): %d texts with passages" % (MARK, len(rows)))
    print("%-44s %-9s %-9s %8s %6s %-9s %7s %5s  %s" % ("text", "register", "source", "passages", "EN%", "judged",
                                                       "agree%", "own", "reading"))
    for r in sorted(rows, key=lambda r: -r["passages"]):
        print("%-44s %-9s %-9s %8d %6s %-9s %7s %5s  %s" % (
            r["doc"][:44], r["register"][:9], r["source"], r["passages"], r["english_pct"], r["judged"][:9],
            r["fidelity_pct"] if r["fidelity_pct"] is not None else "-",
            r["own_per100"] if r["own_per100"] is not None else "-", r["reading"]))
    if a.csv:
        Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["doc"])
            wr.writeheader()
            wr.writerows(rows)
        print("written: %s" % a.csv)
    measured = sum(1 for r in rows if r["fidelity_pct"] is not None)
    print()
    print("VERDICT: %d texts; %d measured akshara by akshara against an e-text; %d not (no e-text witness measured)" % (
        len(rows), measured, len(rows) - measured))
    print("NEXT: for a text with a witness, python scripts\\source_fidelity.py --ref db:WITNESS --cand db:TEXT")
    print("ALSO: the judge's level sees Latin debris only, not one Devanagari letter read as another; "
          "docs/FIDELITY_2026-10-22.md")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="FIDELITY_2026_10_22: the letters of a reading against an e-text")
    ap.add_argument("--ref", help="the reference: witness:CODE, db:DOC, file:PATH (or a reading)")
    ap.add_argument("--cand", action="append", default=[],
                    help="a reading: db:, vision:, raw:, pages:, file:, witness:")
    ap.add_argument("--pair", action="append", help="A,B: two readings of one print (both among --cand)")
    ap.add_argument("--prefix", default="", help="only reference units whose reference starts so (14. for kanda 14)")
    ap.add_argument("--fold-ch", action="store_true", help="read cha as ca on both sides (GRETIL's Satapatha)")
    ap.add_argument("--group-depth", type=int, default=0, help="parts of the reference that make a group")
    ap.add_argument("--groups", action="store_true", help="print the groups (chapters, adhyayas)")
    ap.add_argument("--examples", type=int, default=6, help="the worst units shown")
    ap.add_argument("--ledger", action="store_true", help="every text: engines, English, judged level, fidelity")
    ap.add_argument("--csv", default="", help="with --ledger: write it as CSV")
    ap.add_argument("--db", default="", help="the database (data/context.db), opened read-only")
    ap.add_argument("--immutable", action="store_true", help="the database is a backup file: open it immutable")
    ap.add_argument("--root", default=str(ROOT), help="the repository (for data/)")
    ap.add_argument("--out-dir", default="", help="where the reports go (data/source_fidelity)")
    ap.add_argument("--no-write", action="store_true", help="write no report")
    a = ap.parse_args(argv)
    a.root = str(Path(a.root).resolve())
    if not a.db:
        a.db = str(Path(a.root) / "data" / "context.db")
    a.db = str(Path(a.db).resolve())
    if a.csv:
        a.csv = str(Path(a.csv).resolve())
    if a.out_dir:
        a.out_dir = str(Path(a.out_dir).resolve())
    os.chdir(a.root)
    if a.ledger:
        return ledger(a)
    if not a.ref or not a.cand:
        ap.error("--ref and at least one --cand (or --ledger)")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
