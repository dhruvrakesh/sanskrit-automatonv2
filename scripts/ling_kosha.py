#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ling_kosha.py  (2026-09-13)  LING_KOSHA_2026_09_13

Fills passages.morph from vidyut's DICTIONARY. Deliberately does NOT fill
passages.sandhi.

Run with the isolated interpreter:
    .venv-ling\\Scripts\\python.exe scripts\\ling_kosha.py --doc <code>

Why this replaces the cheda approach
------------------------------------
Block AD wired vidyut.cheda, the segmenter. Measured on inputs whose correct
analysis is not in dispute, it over-segments badly:

    gacCati        -> gam                          correct
    provAca        -> prabrU                       correct
    DarmakzetraM   -> Darmakzetra                  correct
    so'pi          -> sa + api                     correct, real sandhi

    DarmaH         -> DA + F + a        THREE tokens for one word
    rAjapuruzaH    -> rA + jap + u + av nonsense
    harItaH        -> hari + i          wrong
    vanam          -> av + a            wrong

43% of the lemmas it returned were one or two characters. And a dictionary
check CANNOT catch this, because DA, F, a and i are all real Sanskrit roots -
the wrong answer is made of right pieces. vidyut's own documentation marks
cheda, sandhi and chandas as EXPERIMENTAL while kosha, prakriya and lipi are
production. That distinction turns out to be exactly right.

So this pass uses the production part and declines the experimental part.

What it does
------------
For each whitespace/danda-delimited word:
  1. transliterate Devanagari -> SLP1 (vidyut.lipi, production, exact)
  2. try the word against vidyut.kosha under the forms the kosha actually
     stores. The kosha holds PRE-final-sandhi forms, so a word ending in
     visarga must be tried as -s and -r, and anusvara as -m:

        DarmaH      miss  ->  Darmas       hit, lemma Darma
        rAmaH       miss  ->  rAmas        hit
        vanaM       miss  ->  vanam        hit
        yuyutsavaH  miss  ->  yuyutsavas   hit, lemma yuyutsa
        rAjapuruzaH miss  ->  rAjapuruzas  hit, lemma rAjapuruza

     Measured on a 12-word probe, that normalisation lifts coverage from
     5/12 to 11/12.
  3. record EVERY candidate analysis the kosha returns, and pick none.
     vanam has 62 entries; out of context the word genuinely is ambiguous.
     Silently choosing one would be the same class of error as a translator
     that declares uncertainty 8 times in 17,412 units.
  4. words the kosha does not know get recorded as unknown. An honest null.

What it deliberately does NOT do
--------------------------------
  * It does not write passages.sandhi. We have no segmenter we trust, and a
    scholarly column filled with guesses is worse than an empty one. That
    column stays NULL until a gold-standard-measured segmenter is in place -
    ByT5-Sanskrit reports 90.11% perfect match on DCS 2018, and the number
    matters because it was measured against a gold standard, which is
    precisely what vidyut-cheda has never published.
  * It does not resolve ambiguity.
  * It does not read or set SA_SAFE_MODE.
  * Without --commit it opens the database immutable and cannot write.

morph shape
-----------
  {"engine":"vidyut-kosha","vidyut":"0.4.0","v":2,"at":"...",
   "n_words":8,"n_known":6,"coverage":0.75,
   "residue":["U+FFFD"],
   "words":[{"w":"<devanagari>","slp1":"DarmaH","key":"Darmas",
             "lemmas":["Darma"],"n":1}, ...]}
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MARK = "LING_KOSHA_2026_09_13"
ENGINE = "vidyut-kosha"
SCHEMA_V = 2

DEV_RE = re.compile(r"[\u0900-\u097F]")
LAT_RE = re.compile(r"[A-Za-z]")
SPLIT_RE = re.compile(r"[\s\u0964\u0965|]+")
ZERO_WIDTH = "\u200b\u200c\u200d\u2060\ufeff\u200e\u200f"
PUNCT = {0x00A0: 32, 0x2007: 32, 0x202F: 32,
         0x2018: 39, 0x2019: 39, 0x201A: 39,
         0x201C: 34, 0x201D: 34, 0x201E: 34,
         0x2013: 45, 0x2014: 45, 0x2015: 45, 0x2212: 45,
         0x2026: 46, 0x2022: 32, 0x00B7: 32, 0x2027: 32,
         0x0970: 46}
STRIP_EDGE = "\"'`.,;:()[]{}<>!?-\u2013\u2014*_/\\|0123456789"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dev_share(t):
    d, l = len(DEV_RE.findall(t or "")), len(LAT_RE.findall(t or ""))
    return d / (d + l) if (d + l) else 0.0


def clean(dev):
    s = unicodedata.normalize("NFC", dev or "")
    for z in ZERO_WIDTH:
        s = s.replace(z, "")
    s = s.translate(PUNCT)
    return re.sub(r"\s+", " ", s).strip()


class Kosha:
    """vidyut.kosha with the final-sandhi normalisation the kosha's own key
    format requires."""

    def __init__(self, data_dir: Path, verbose=False):
        import vidyut
        from vidyut.lipi import transliterate, Scheme
        from vidyut.kosha import Kosha as _K

        self.version = getattr(vidyut, "__version__", "?")
        self._tr = transliterate
        self.dev = getattr(Scheme, "Devanagari")
        self.slp = None
        for n in ("Slp1", "SLP1", "Slp", "slp1"):
            if hasattr(Scheme, n):
                self.slp = getattr(Scheme, n)
                break
        if self.slp is None:
            raise SystemExit("FAIL: no SLP1 member on vidyut.lipi.Scheme")

        tried = []
        for p in (data_dir / "kosha", data_dir, data_dir / "data" / "kosha"):
            tried.append(str(p))
            try:
                self.k = _K(str(p))
                self.kosha_dir = p
                break
            except Exception:
                continue
        else:
            raise SystemExit("FAIL: kosha not loadable from any of:\n  " +
                             "\n  ".join(tried) +
                             "\nRun download_data first (Block AD step 1).")
        if verbose:
            print("  vidyut %s, kosha at %s" % (self.version, self.kosha_dir))

    def to_slp1(self, dev):
        out = self._tr(dev, self.dev, self.slp)
        residue = sorted({c for c in out if ord(c) > 127})
        if residue:
            out = "".join(c for c in out if ord(c) < 128)
        return out, residue

    @staticmethod
    def keys_for(slp_word):
        """The kosha stores pre-final-sandhi forms. Measured: DarmaH misses,
        Darmas hits. Try the written form first so an exact hit wins."""
        w = slp_word.strip(STRIP_EDGE)
        if not w:
            return []
        out = [w]
        if w.endswith("H"):
            out += [w[:-1] + "s", w[:-1] + "r", w[:-1]]
        elif w.endswith("M"):
            out += [w[:-1] + "m", w[:-1]]
        elif w.endswith("o"):
            # -aH becomes -o before a voiced sound. Safe because the written
            # form is tried FIRST, so genuine -o words (go, namo-as-namas is
            # a real ambiguity) are not stolen: go hits directly with 4
            # entries, dvO with 18.
            out += [w[:-1] + "as", w[:-1] + "a"]
        elif w.endswith("m") or w.endswith("s"):
            out += [w[:-1]]
        seen, uniq = set(), []
        for k in out:
            if k and k not in seen:
                seen.add(k)
                uniq.append(k)
        return uniq

    def lookup(self, slp_word):
        for key in self.keys_for(slp_word):
            try:
                ent = self.k.get(key)
            except Exception:
                continue
            if ent:
                lem, seen = [], set()
                for e in ent:
                    L = getattr(e, "lemma", None)
                    if L and L not in seen:
                        seen.add(L)
                        lem.append(L)
                return key, lem[:8], len(ent), None
        return None, [], 0, self.near_miss(slp_word)

    def near_miss(self, slp_word):
        """A word the kosha rejects, that it WOULD accept with one vowel
        lengthened, is almost always an orthography or OCR defect in the
        source rather than an unknown word. Measured: the corpus writes
        harItaH where the kosha has hArItas - Harita for Harita. This is
        reported as a finding and is NEVER used as the lemma."""
        base = slp_word.strip(STRIP_EDGE)
        if not base or len(base) > 24:
            return None
        for i, ch in enumerate(base[:6]):
            if ch not in "aiu":
                continue
            cand = base[:i] + ch.upper() + base[i + 1:]
            for key in self.keys_for(cand):
                try:
                    if self.k.get(key):
                        return {"would_hit": key, "changed": "%s->%s at %d"
                                % (ch, ch.upper(), i)}
                except Exception:
                    pass
        return None

    def analyse(self, dev_text):
        cleaned = clean(dev_text)
        slp_all, residue = self.to_slp1(cleaned)
        words_dev = [w for w in SPLIT_RE.split(cleaned) if w.strip(STRIP_EDGE)]
        rows, known = [], 0
        for wd in words_dev:
            slp_w, _ = self.to_slp1(wd)
            key, lemmas, n, near = self.lookup(slp_w)
            r = {"w": wd, "slp1": slp_w}
            if key:
                known += 1
                r["key"] = key
                r["lemmas"] = lemmas
                r["n"] = n
            elif near:
                r["near"] = near
            rows.append(r)
        return rows, known, residue


def open_db(path, writable):
    if not writable:
        return sqlite3.connect("file:%s?immutable=1" % path.replace("\\", "/"), uri=True)
    con = sqlite3.connect(path, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    return con


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-dev", type=float, default=0.80)
    ap.add_argument("--data-dir", default=r"D:\Sanksrit Automatons\vidyut-data")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--batch", type=int, default=300)
    ap.add_argument("--show", type=int, default=3)
    ap.add_argument("--survey", action="store_true",
                    help="read-only: report kosha coverage per document and exit")
    a = ap.parse_args()

    print("%s   engine=%s  schema v%d" % (MARK, ENGINE, SCHEMA_V))
    print("  mode     : %s" % ("SURVEY (read-only)" if a.survey else
                               ("COMMIT - writes morph only" if a.commit else
                                "DRY RUN - nothing written")))
    kk = Kosha(Path(a.data_dir), verbose=True)
    con = open_db(a.db, writable=(a.commit and not a.survey))

    where = ["TRIM(COALESCE(p.text,'')) <> ''",
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')",
             "d.code NOT LIKE '%-RETIRED'"]
    params = []
    if a.doc:
        where.append("d.code = ?")
        params.append(a.doc)
    if not a.refresh and not a.survey:
        where.append("(p.morph IS NULL OR TRIM(p.morph) = '')")

    rows = con.execute(
        "SELECT p.id, d.code, COALESCE(p.verse_ref,''), p.text "
        "FROM passages p JOIN docs d ON d.id = p.doc_id "
        "WHERE " + " AND ".join(where) + " ORDER BY p.id", params).fetchall()
    rows = [r for r in rows if dev_share(r[3]) >= a.min_dev]
    if a.limit:
        rows = rows[: a.limit]
    print("  rows     : %d" % len(rows))
    if not rows:
        print("  nothing to do."); return 0

    t0 = time.time()
    per_doc = {}
    tot_w = tot_k = tot_near = 0
    residues = Counter()
    pending = []
    stamp = now_iso()
    done = 0

    for i, (pid, code, ref, dev) in enumerate(rows, 1):
        try:
            words, known, residue = kk.analyse(dev)
        except Exception as e:
            print("  ! passage %s: %s: %s" % (pid, type(e).__name__, str(e)[:110]))
            continue
        n = len(words)
        if not n:
            continue
        tot_w += n; tot_k += known
        tot_near += sum(1 for w in words if "near" in w)
        d = per_doc.setdefault(code, [0, 0, 0])
        d[0] += 1; d[1] += n; d[2] += known
        for c in residue:
            residues["U+%04X" % ord(c)] += 1
        done += 1

        if a.show and i <= a.show and not a.survey:
            print("\n  --- passage %s  %s %s   coverage %d/%d ---" % (pid, code, ref or "-", known, n))
            for w in words[:8]:
                if "lemmas" in w:
                    print("      %-16s %-14s -> %-14s %s candidate(s)"
                          % (w["w"][:16], w["slp1"][:14], ", ".join(w["lemmas"][:2])[:14], w["n"]))
                elif "near" in w:
                    print("      %-16s %-14s    NOT in the dictionary, but %s would hit (%s)"
                          % (w["w"][:16], w["slp1"][:14], w["near"]["would_hit"],
                             w["near"]["changed"]))
                else:
                    print("      %-16s %-14s    not in the dictionary" % (w["w"][:16], w["slp1"][:14]))

        if a.commit and not a.survey:
            morph = {"engine": ENGINE, "vidyut": kk.version, "v": SCHEMA_V,
                     "at": stamp, "n_words": n, "n_known": known,
                     "coverage": round(known / n, 3),
                     "residue": ["U+%04X" % ord(c) for c in residue],
                     "words": words}
            pending.append((json.dumps(morph, ensure_ascii=False), pid))
            if len(pending) >= a.batch:
                con.executemany("UPDATE passages SET morph=? WHERE id=?", pending)
                con.commit(); pending.clear()
                print("  ... %d/%d committed (%.0fs)" % (done, len(rows), time.time() - t0))

    if a.commit and not a.survey and pending:
        con.executemany("UPDATE passages SET morph=? WHERE id=?", pending)
        con.commit(); pending.clear()

    el = time.time() - t0
    print("\n  %-44s %8s %8s %9s" % ("document", "rows", "words", "in kosha"))
    print("  " + "-" * 72)
    for code, (r, w, k) in sorted(per_doc.items(), key=lambda kv: -kv[1][1]):
        print("  %-44s %8d %8d %8.1f%%" % (code[:44], r, w, 100.0 * k / max(1, w)))
    print("  " + "-" * 72)
    print("  %-44s %8d %8d %8.1f%%" % ("TOTAL", done, tot_w, 100.0 * tot_k / max(1, tot_w)))
    print("\n  %.1fs, %.0f rows/s" % (el, done / el if el else 0))
    if tot_near:
        print("\n  %d word(s) the kosha rejects but WOULD accept with one vowel"
              % tot_near)
        print("  lengthened. Those are orthography or OCR defects in the source,")
        print("  not unknown words, and they are recorded as findings - never")
        print("  used as a lemma. harItaH for hArItas is the pattern.")
    if residues:
        print("\n  characters vidyut could not transliterate (OCR residue):")
        for c, n in residues.most_common(12):
            print("    %-10s %6d row(s)" % (c, n))
        print("    these are a direct measure of scanning noise still in the text")
    print("\n  passages.sandhi was NOT written and remains NULL. See the header:")
    print("  vidyut-cheda over-segments and we have no gold-standard number for it.")
    if not a.commit or a.survey:
        print("  Nothing was written.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())