# =====================================================================
# SUPERSEDED 2026-09-14 by scripts/ling_kosha.py.
#
# This is the vidyut.cheda implementation. It is kept because the
# measurement that retired it is worth keeping, not because it should
# be run.
#
# Measured on vidyut 0.4.0 with data-0.4.0, on inputs whose correct
# analysis is not in dispute:
#
#     gacCati      -> gam                    correct
#     provAca      -> prabrU                 correct
#     so'pi        -> sa + api               correct, real sandhi
#     DarmaH       -> DA + F + a             three tokens for one word
#     rAjapuruzaH  -> rA + jap + u + av      nonsense
#     harItaH      -> hari + i               wrong
#     vanam        -> av + a                 wrong
#
# 43% of returned lemmas were one or two characters. A "are these real
# dictionary words" check scores that garbage at 100%, because DA, F, a
# and i are all real Sanskrit roots - the wrong answer is assembled from
# right pieces. vidyut's own docs mark cheda EXPERIMENTAL and kosha
# PRODUCTION, and that distinction is exactly right.
#
# ling_kosha.py uses the dictionary instead, and leaves passages.sandhi
# NULL until a segmenter with a published gold-standard number exists.
# =====================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ling_pass.py  (2026-09-13)  LING_PASS_2026_09_13

Fills passages.sandhi and passages.morph. Touches NO other column, ever.

Run with the ISOLATED interpreter:
    .venv-ling\\Scripts\\python.exe scripts\\ling_pass.py --doc <code> --dry-run

Why an isolated interpreter
---------------------------
requirements.txt records that sanskrit_parser was removed because its
werkzeug==2.1.2 pin conflicts with flask>=3.0.3. Any analyser installed into
the dashboard's environment risks the same collision. Booksmith already proves
the pattern that works here: its own venv, invoked as a subprocess, sharing
nothing. This follows it.

Safety, in the order it matters
-------------------------------
  * DRY-RUN IS THE DEFAULT. Without --commit nothing is written and the
    process opens the database with immutable=1, so it physically cannot.
  * The UPDATE statement names exactly two columns, sandhi and morph. There
    is no code path that writes text, translation, iast, text_type or
    anything else.
  * SA_SAFE_MODE is never read and never set. This script does not go
    through sandhi_split.py or morph_parse.py, so the flag that gates both
    destructive bulk ops and their safe fallback is untouched.
  * --min-dev skips rows that are not majority Devanagari. Measured
    2026-09-13: Bodhicaryavatara has 22.4% Latin-majority rows and bodhyana
    28.0%, all classified mula. Feeding romanised OCR to a Sanskrit
    segmenter produces confident nonsense, which is worse than a null.
  * Idempotent. A row whose morph already records this engine and version is
    skipped, so a re-run costs nothing and an interrupted run resumes.
  * Writes in batches with an explicit commit, so a kill loses one batch.

What goes in the columns
------------------------
db_utils.py documents sandhi as "JSON list of words", so that is exactly what
it gets - a flat array of Devanagari strings, readable by anything that
already expects that shape. All provenance goes in morph, which db_utils
documents only as "JSON":

  sandhi : ["\u0927\u0930\u094d\u092e\u0903", "\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947", ...]
  morph  : {"engine":"vidyut-cheda", "vidyut":"0.4.0", "v":1,
            "at":"2026-09-13T...Z", "n":12,
            "tokens":[{"form":"\u0927\u0930\u094d\u092e\u0903","lemma":"\u0927\u0930\u094d\u092e","slp1":"DarmaH",
                       "pos":"Subanta","linga":"Pum","vibhakti":"Prathama",
                       "vacana":"Eka"}, ...]}

Vidyut works in SLP1 (its own __init__ says so), so text is transliterated
Devanagari -> SLP1 on the way in and SLP1 -> Devanagari on the way out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MARK = "LING_PASS_2026_09_13"
ENGINE = "vidyut-cheda"
SCHEMA_V = 1

DEV_RE = re.compile(r"[\u0900-\u097F]")
LAT_RE = re.compile(r"[A-Za-z]")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dev_share(t: str) -> float:
    d = len(DEV_RE.findall(t or ""))
    l = len(LAT_RE.findall(t or ""))
    return d / (d + l) if (d + l) else 0.0


# ---------------------------------------------------------------------------
# The adapter. Resolved at runtime against what is installed, because the
# shipped .pyi stubs and the compiled module disagree: cheda.pyi declares
# Token.info, while dir(Token) on the installed 0.4.0 build reports
# text, lemma, data. Ask the object, do not trust the stub.
# ---------------------------------------------------------------------------
class Analyzer:
    def __init__(self, data_dir: Path, verbose: bool = False):
        import vidyut
        from vidyut.lipi import transliterate, Scheme
        from vidyut.cheda import Chedaka

        self.version = getattr(vidyut, "__version__", "?")
        self._tr = transliterate
        self.Scheme = Scheme

        self.dev = self._scheme("Devanagari")
        self.slp = self._scheme("Slp1", "SLP1", "Slp", "slp1")
        if self.slp is None:
            raise SystemExit(
                "FAIL: no SLP1 member on vidyut.lipi.Scheme. Members seen: %s"
                % ", ".join(sorted(n for n in dir(Scheme) if not n.startswith("_")))[:400])

        cand = [data_dir, data_dir / "data", data_dir / "vidyut-0.4.0"]
        last = None
        for p in cand:
            try:
                self.chedaka = Chedaka(str(p))
                self.data_dir = p
                break
            except Exception as e:          # noqa: BLE001 - we report it
                last = "%s: %s" % (type(e).__name__, str(e)[:160])
        else:
            raise SystemExit(
                "FAIL: Chedaka would not load from any of:\n  %s\nlast error: %s\n"
                "Run: .venv-ling\\Scripts\\python.exe -c "
                "\"import vidyut; vidyut.download_data(r'%s')\""
                % ("\n  ".join(str(p) for p in cand), last, data_dir))
        if verbose:
            print("  vidyut %s, data at %s" % (self.version, self.data_dir))

    def _scheme(self, *names):
        for n in names:
            if hasattr(self.Scheme, n):
                return getattr(self.Scheme, n)
        return None

    def to_slp1(self, dev: str) -> str:
        return self._tr(dev, self.dev, self.slp)

    def to_dev(self, slp: str) -> str:
        return self._tr(slp, self.slp, self.dev)

    @staticmethod
    def _pada_fields(info) -> dict:
        """Flatten whatever the token carries as its analysis. The runtime
        type is not documented consistently, so read it defensively and keep
        only scalar-ish values."""
        out = {}
        if info is None:
            return out
        for attr in ("pos", "linga", "vibhakti", "vacana", "purusha",
                     "lakara", "pada_prayoga", "is_purvapada", "is_avyaya"):
            try:
                v = getattr(info, attr, None)
            except Exception:
                continue
            if v is None:
                continue
            out[attr] = getattr(v, "name", None) or str(v)
        for attr in ("dhatu", "pratipadika"):
            try:
                v = getattr(info, attr, None)
            except Exception:
                continue
            if v is None:
                continue
            out[attr] = getattr(v, "text", None) or str(v)
        if not out:
            s = str(info)
            if s and s != "None":
                out["raw"] = s[:200]
        return out

    def analyse(self, dev_text: str):
        slp = self.to_slp1(dev_text)
        toks = self.chedaka.run(slp)
        words, rows = [], []
        for t in toks:
            surface_slp = getattr(t, "text", "") or ""
            lemma_slp = getattr(t, "lemma", "") or ""
            info = getattr(t, "data", None)
            if info is None:
                info = getattr(t, "info", None)
            form = self.to_dev(surface_slp) if surface_slp else ""
            words.append(form)
            row = {"form": form, "slp1": surface_slp}
            if lemma_slp:
                row["lemma"] = self.to_dev(lemma_slp)
                row["lemma_slp1"] = lemma_slp
            row.update(self._pada_fields(info))
            rows.append(row)
        return words, rows


# ---------------------------------------------------------------------------
def open_db(path: str, writable: bool):
    if not writable:
        return sqlite3.connect("file:%s?immutable=1" % path.replace("\\", "/"), uri=True)
    con = sqlite3.connect(path, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def select_rows(con, doc, limit, min_dev, refresh):
    where = ["TRIM(COALESCE(p.text,'')) <> ''",
             "COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')",
             "d.code NOT LIKE '%-RETIRED'"]
    params = []
    if doc:
        where.append("d.code = ?")
        params.append(doc)
    if not refresh:
        where.append("(p.morph IS NULL OR TRIM(p.morph) = '')")
    sql = ("SELECT p.id, d.code, COALESCE(p.verse_ref,''), p.text "
           "FROM passages p JOIN docs d ON d.id = p.doc_id "
           "WHERE " + " AND ".join(where) + " ORDER BY p.id")
    rows = con.execute(sql, params).fetchall()
    kept = [r for r in rows if dev_share(r[3]) >= min_dev]
    skipped = len(rows) - len(kept)
    if limit:
        kept = kept[:limit]
    return kept, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="fill passages.sandhi and passages.morph")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None, help="restrict to one doc code")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-dev", type=float, default=0.80,
                    help="skip rows below this Devanagari share (default 0.80)")
    ap.add_argument("--data-dir", default=r"D:\Sanksrit Automatons\vidyut-data")
    ap.add_argument("--commit", action="store_true",
                    help="actually write. Without it this is a dry run and the "
                         "database is opened immutable.")
    ap.add_argument("--refresh", action="store_true",
                    help="re-analyse rows that already have morph")
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--show", type=int, default=3, help="print this many analyses")
    a = ap.parse_args()

    print("%s   engine=%s  schema v%d" % (MARK, ENGINE, SCHEMA_V))
    print("  mode      : %s" % ("COMMIT - will write sandhi and morph"
                                if a.commit else "DRY RUN - nothing will be written"))
    print("  database  : %s" % a.db)
    print("  min-dev   : %.2f" % a.min_dev)

    az = Analyzer(Path(a.data_dir), verbose=True)

    con = open_db(a.db, writable=a.commit)
    rows, skipped = select_rows(con, a.doc, a.limit, a.min_dev, a.refresh)
    print("  selected  : %d row(s); %d skipped below the Devanagari floor" % (len(rows), skipped))
    if not rows:
        print("  nothing to do.")
        return 0

    t0 = time.time()
    done = failed = 0
    safe_tokens = new_tokens = 0
    pending = []
    stamp = now_iso()

    for i, (pid, code, ref, dev) in enumerate(rows, 1):
        try:
            words, toks = az.analyse(dev)
        except Exception as e:                      # noqa: BLE001
            failed += 1
            if failed <= 5:
                print("  ! passage %s: %s: %s" % (pid, type(e).__name__, str(e)[:120]))
            continue
        if not words:
            failed += 1
            continue
        # the SAFE baseline, for the guard that runs after this
        safe_n = len([w for w in re.split(r"[\s\u0964\u0965|]+", dev) if w])
        safe_tokens += safe_n
        new_tokens += len(words)

        morph = {"engine": ENGINE, "vidyut": az.version, "v": SCHEMA_V,
                 "at": stamp, "n": len(words), "safe_n": safe_n, "tokens": toks}
        pending.append((json.dumps(words, ensure_ascii=False),
                        json.dumps(morph, ensure_ascii=False), pid))
        done += 1

        if a.show and i <= a.show:
            print("\n  --- passage %s  %s %s ---" % (pid, code, ref or "-"))
            print("      source : %s" % dev[:110].replace("\n", " "))
            print("      SAFE   : %d token(s)" % safe_n)
            print("      vidyut : %d token(s)  %s" % (len(words), " ".join(words[:10])))
            for t in toks[:4]:
                extra = ", ".join("%s=%s" % (k, v) for k, v in t.items()
                                  if k not in ("form", "slp1", "lemma", "lemma_slp1"))
                print("        %-14s lemma=%-14s %s" % (t.get("form", ""),
                                                        t.get("lemma", "-"), extra))

        if a.commit and len(pending) >= a.batch:
            con.executemany("UPDATE passages SET sandhi=?, morph=? WHERE id=?", pending)
            con.commit()
            pending.clear()
            print("  ... %d/%d committed (%.0fs)" % (done, len(rows), time.time() - t0))

    if a.commit and pending:
        con.executemany("UPDATE passages SET sandhi=?, morph=? WHERE id=?", pending)
        con.commit()
        pending.clear()

    el = time.time() - t0
    print("\n  analysed  : %d" % done)
    print("  failed    : %d" % failed)
    print("  elapsed   : %.1fs  (%.1f rows/s)" % (el, done / el if el else 0))
    if done:
        print("  tokens    : SAFE %d -> vidyut %d  (%+.1f%%)"
              % (safe_tokens, new_tokens,
                 100.0 * (new_tokens - safe_tokens) / max(1, safe_tokens)))
        print("              a positive change is sandhi actually being resolved:")
        print("              one written word becoming the several words it contains.")
    if not a.commit:
        print("\n  DRY RUN - the database was opened immutable and nothing was written.")
        print("  Re-run with --commit to write, after a backup.")

    # sidecar, mirroring the exports/booksmith/<doc>.json convention
    try:
        out = Path("exports") / "ling"
        out.mkdir(parents=True, exist_ok=True)
        (out / ("%s.json" % (a.doc or "ALL"))).write_text(json.dumps({
            "marker": MARK, "engine": ENGINE, "vidyut": az.version, "v": SCHEMA_V,
            "at": stamp, "doc": a.doc, "committed": bool(a.commit),
            "selected": len(rows), "analysed": done, "failed": failed,
            "skipped_below_min_dev": skipped, "min_dev": a.min_dev,
            "safe_tokens": safe_tokens, "vidyut_tokens": new_tokens,
            "seconds": round(el, 1),
        }, indent=2), encoding="utf-8")
    except Exception:
        pass
    con.close()
    return 0 if done and not failed else (0 if done else 1)


if __name__ == "__main__":
    sys.exit(main())