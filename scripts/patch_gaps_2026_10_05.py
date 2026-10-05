#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_gaps_2026_10_05.py  (2026-10-05)  GAPS_2026_10_05

Two read-mostly fixes for texts that can never reach CURRENT because a few passages
cannot be translated as printed (markandeya_purana, 2026-10-05: 10 English / 24 Hindi
rows missing after every retry; the retry log says echo-filter 21 - the model hands
the damaged line back).

corpus_status.py (still READ-ONLY)
  A passage without English (or Hindi) is a GAP, not work to do, when
    (a) translate_passages.py already tried it and recorded unusable output in
        data/translate_outcomes.jsonl (any cause except 'salvaged'), matched by
        doc + lang + page + idx, or
    (b) its OCR quality_score is above 0 and below 0.35, which translate_passages
        skips by default (--min-quality 0.35), so it is never sent.
  Gaps count with the lacunae against --lacuna-ok (as a share of all passages).
  Within the allowance they are a note; above it the text stays NEEDS-TRANSLATION
  with a pointer to the source (no paid command - a re-run returns the same).
  New --outcomes PATH (default: translate_outcomes.jsonl beside the DB); new CSV/JSON
  columns en_gap, hi_gap. Nothing else in the table or the verdicts changes.

classify_noise.py --running-heads  (dry run unless --apply, as before)
  Tags as noise an UNTRANSLATED passage that is the first or last line of its page
  and whose text (digits and punctuation ignored) is the first/last line of at least
  --min-repeat pages (default 3), at most --max-len characters (default 60). Never
  tagged: a line with a danda (verse, refrains included), a speaker line (... uvaca),
  a line translated more often than not elsewhere. It lists each repeated line with
  its page count; --show adds the usual sample. Reversible:
  UPDATE passages SET text_type='mula' WHERE id IN (...).

All-or-nothing, marker-idempotent, backup .bak_gaps_<date>, py_compile.
  python scripts\\patch_gaps_2026_10_05.py --check
  python scripts\\patch_gaps_2026_10_05.py
Test: python -m unittest tests.test_gaps_2026_10_05 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "GAPS_2026_10_05"

CS_EDITS = [
    ("gap functions",
     '''def db_measures(con: sqlite3.Connection, doc: str, en_ver: str, hi_ver: str) -> dict:
''',
     r'''# GAPS_2026_10_05: passages that cannot be translated as printed are gaps, not work to do.
GAP_MIN_QUALITY = 0.35   # translate_passages.py --min-quality default: below it a passage is never sent


def tried_unusable(path) -> dict:
    """{(doc, lang): {(page, idx)}} from translate_outcomes.jsonl: attempts whose output was unusable
    (every cause except 'salvaged', where the cleaned output was kept). Missing file: {}. Never raises."""
    out: dict = {}
    try:
        fh = open(str(path), encoding="utf-8")
    except (OSError, TypeError):
        return out
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("cause") in (None, "salvaged"):
                continue
            try:
                k = (int(r["page"]), int(r["idx"]))
            except (KeyError, TypeError, ValueError):
                continue
            out.setdefault((str(r.get("doc")), str(r.get("lang") or "en")), set()).add(k)
    return out


def gap_measures(con: sqlite3.Connection, doc: str, tried: dict) -> dict:
    """en_gap / hi_gap: untranslated in-scope passages that were tried with unusable output, or that
    translate_passages skips for OCR quality. *_gap_tried, *_gap_lowq split them; *_gap_refs: examples."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    q = "p.quality_score" if "quality_score" in cols else "NULL"
    res: dict = {}
    for lang in ("en", "hi"):
        res.update({lang + "_gap": 0, lang + "_gap_tried": 0, lang + "_gap_lowq": 0, lang + "_gap_refs": []})
    rows = con.execute(
        f"""SELECT p.page_no, p.idx, {q}, TRIM(COALESCE(p.translation,'')) <> '',
                   TRIM(COALESCE(l.translation,'')) <> ''
            FROM passages p JOIN docs d ON d.id = p.doc_id
            LEFT JOIN translations_l10n l ON l.passage_id = p.id AND l.lang = 'hi'
            WHERE d.code = ? AND {SCOPE}""", (doc,)).fetchall()
    for page, idx, qs, has_en, has_hi in rows:
        try:
            low = qs is not None and 0.0 < float(qs) < GAP_MIN_QUALITY
        except (TypeError, ValueError):
            low = False
        for lang, has in (("en", has_en), ("hi", has_hi)):
            if has:
                continue
            was_tried = (int(page or 0), int(idx or 0)) in tried.get((doc, lang), ())
            if was_tried or low:
                res[lang + "_gap"] += 1
                res[lang + ("_gap_tried" if was_tried else "_gap_lowq")] += 1
                if len(res[lang + "_gap_refs"]) < 8:
                    res[lang + "_gap_refs"].append("%s.%s" % (page, idx))
    return res


def db_measures(con: sqlite3.Connection, doc: str, en_ver: str, hi_ver: str) -> dict:
''', 1),
    ("todo excludes gaps",
     '''    en_todo, hi_todo = n - s.get("en_done", 0), n - s.get("hi_done", 0)
''',
     '''    # GAPS_2026_10_05: gaps (tried with unusable output, or skipped for OCR quality) are not work to do.
    en_gap, hi_gap = s.get("en_gap", 0), s.get("hi_gap", 0)
    en_todo, hi_todo = n - s.get("en_done", 0) - en_gap, n - s.get("hi_done", 0) - hi_gap
''', 1),
    ("gaps against the lacuna allowance",
     r'''    if cmds:
        cmds.append("python scripts\\measure_lacunae.py --doc %s" % doc)
''',
     r'''    for lang, name, gap in (("en", "English", en_gap), ("hi", "Hindi", hi_gap)):   # GAPS_2026_10_05
        if not gap:
            continue
        share = pct(gap + s.get(lang + "_lacuna", 0), n)
        what = ("%d passage(s) without %s cannot be translated as printed (%d tried with unusable output, "
                "%d below OCR quality %.2f; e.g. %s)" % (gap, name, s.get(lang + "_gap_tried", 0),
                                                        s.get(lang + "_gap_lowq", 0), GAP_MIN_QUALITY,
                                                        ", ".join(s.get(lang + "_gap_refs") or [])))
        if share > lacuna_ok:
            reasons.append("%s; with the lacunae that is %.1f%% of passages > %.1f%%" % (what, share, lacuna_ok))
            v = "NEEDS-TRANSLATION"
            cmds.append("# %s gaps are a SOURCE problem (a re-run returns the same). Running heads first:" % name)
            cmds.append("python scripts\\classify_noise.py --doc %s --running-heads --show" % doc)
        else:
            reasons.append("note: %s; counted as gaps (%.1f%% of passages with the lacunae, within %.1f%%)"
                           % (what, share, lacuna_ok))
    if cmds:
        cmds.append("python scripts\\measure_lacunae.py --doc %s" % doc)
''', 1),
    ("collect: outcomes argument",
     '''            do_drift: bool = True, min_passages: int = 1) -> tuple[list[dict], tuple, dict, float | None]:
''',
     '''            do_drift: bool = True, min_passages: int = 1,
            outcomes: Path | None = None) -> tuple[list[dict], tuple, dict, float | None]:
''', 1),
    ("collect: read the outcomes once",
     '''    en_ver, hi_ver, hi_src = current_versions()
    con = open_ro(db)
''',
     '''    en_ver, hi_ver, hi_src = current_versions()
    tried = tried_unusable(outcomes if outcomes is not None
                           else Path(db).parent / "translate_outcomes.jsonl")   # GAPS_2026_10_05
    con = open_ro(db)
''', 1),
    ("collect: gap measures",
     '''            s.update(db_measures(con, code, en_ver, hi_ver))
''',
     '''            s.update(db_measures(con, code, en_ver, hi_ver))
            s.update(gap_measures(con, code, tried))   # GAPS_2026_10_05
''', 1),
    ("csv columns",
     '''        "img_approved", "est_usd"]
''',
     '''        "img_approved", "est_usd", "en_gap", "hi_gap"]
''', 1),
    ("row columns",
     '''            "est_usd": round(s.get("est_usd", 0.0), 2)}
''',
     '''            "est_usd": round(s.get("est_usd", 0.0), 2),
            "en_gap": s.get("en_gap", 0), "hi_gap": s.get("hi_gap", 0)}   # GAPS_2026_10_05
''', 1),
    ("--outcomes",
     '''    ap.add_argument("--no-drift", action="store_true", help="skip the raw_merged drift check (faster)")
''',
     '''    ap.add_argument("--no-drift", action="store_true", help="skip the raw_merged drift check (faster)")
    ap.add_argument("--outcomes", default=None,
                    help="translate_outcomes.jsonl (default: beside the DB) - GAPS_2026_10_05")
''', 1),
    ("main passes --outcomes",
     '''        not args.no_drift, args.min_passages)
''',
     '''        not args.no_drift, args.min_passages, Path(args.outcomes) if args.outcomes else None)
''', 1),
]

CN_EDITS = [
    ("running-heads function",
     '''def main():
''',
     r'''# GAPS_2026_10_05: running heads and footers - the same short line at the top or foot of many pages.
_UVACA = "\u0909\u0935\u093e\u091a"   # 'uvaca' (said): a speaker line repeats too, and is real text


def head_key(s: str) -> str:
    """The line with digits (ASCII and Devanagari), dandas and punctuation removed, spaces collapsed."""
    import unicodedata
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[0-9\u0966-\u096f\u0964\u0965|.,;:!?()\[\]{}'\"\u2018\u2019\u201c\u201d*_/\\~`+=<>\u2013\u2014-]+",
               " ", s)
    return " ".join(s.split()).lower()


def running_heads(con, doc=None, min_repeat=3, max_len=60):
    """(hits, groups). hits: [(id, code, text)] untranslated passages that are the first or last line of
    their page and whose head_key is the first/last line of >= min_repeat pages of the same doc.
    Never: a line with a danda (verse, incl. refrains), a speaker line (uvaca), a line over max_len.
    groups: [(code, key, pages, untranslated, translated, sample)] for --show."""
    where = "WHERE COALESCE(p.text_type,'mula') NOT IN ('frontmatter','noise')"
    params = []
    if doc:
        where += " AND d.code=?"; params.append(doc)
    pages = {}
    for pid, code, page, idx, text, done in con.execute(
            f"""SELECT p.id, d.code, p.page_no, p.idx, p.text, TRIM(COALESCE(p.translation,''))<>''
                FROM passages p JOIN docs d ON d.id=p.doc_id {where} ORDER BY d.code, p.page_no, p.idx""", params):
        pages.setdefault((code, page), []).append((pid, text or "", bool(done)))
    by = {}
    for (code, page), rows in pages.items():
        for pid, text, done in {rows[0][0]: rows[0], rows[-1][0]: rows[-1]}.values():
            t = " ".join(text.split())
            k = head_key(t)
            if not k or len(t) > max_len or _UVACA in t or "\u0964" in t or "\u0965" in t:
                continue   # a danda marks verse (a refrain can close many pages); a head has none
            g = by.setdefault((code, k), {"pages": set(), "todo": [], "done": 0, "sample": t})
            g["pages"].add(page)
            if done:
                g["done"] += 1
            else:
                g["todo"].append((pid, code, text))
    hits, groups = [], []
    for (code, k), g in by.items():
        if len(g["pages"]) >= min_repeat and len(g["todo"]) > g["done"]:
            hits += g["todo"]
            groups.append((code, k, len(g["pages"]), len(g["todo"]), g["done"], g["sample"]))
    groups.sort(key=lambda x: (x[0], -x[2]))
    return hits, groups


def main():
''', 1),
    ("running-heads options",
     '''    ap.add_argument("--show", action="store_true", help="print a sample of what would be tagged")
''',
     '''    ap.add_argument("--show", action="store_true", help="print a sample of what would be tagged")
    ap.add_argument("--running-heads", action="store_true",
                    help="instead: untranslated first/last lines of a page that repeat on --min-repeat pages "
                         "(GAPS_2026_10_05)")
    ap.add_argument("--min-repeat", type=int, default=3, help="with --running-heads: pages (default 3)")
    ap.add_argument("--max-len", type=int, default=60, help="with --running-heads: characters (default 60)")
''', 1),
    ("running-heads mode",
     '''    hits = [(pid, code, text) for pid, code, text in rows if is_noise(text or "", args.min_dev, args.min_lat)]
''',
     '''    hits = [(pid, code, text) for pid, code, text in rows if is_noise(text or "", args.min_dev, args.min_lat)]
    if args.running_heads:   # GAPS_2026_10_05
        try:   # a cp1252 console must not crash on a Devanagari sample line
            sys.stdout.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
        hits, groups = running_heads(con, args.doc, args.min_repeat, args.max_len)
        print(f"Running heads/footers ({'APPLY' if args.apply else 'DRY-RUN'}): first or last line of a page, "
              f"no danda, <= {args.max_len} chars, repeated on >= {args.min_repeat} pages, untranslated:")
        for code, k, npg, todo, done, sample in groups[:40]:
            print(f"  [{code[:22]:22s}] {npg:4d} pages  {todo:4d} untranslated  {done:3d} translated  {sample!r}")
        if len(groups) > 40:
            print(f"  ... and {len(groups) - 40} more repeated lines")
''', 1),
]

CN_EDITS.append(
    ("running-heads header",
     '''    print(f"OCR fragments to tag as 'noise'  ({'APPLY' if args.apply else 'DRY-RUN'}; "
          f"dev<{args.min_dev} AND lat<{args.min_lat}):")
''',
     '''    if not args.running_heads:   # GAPS_2026_10_05: running-heads mode printed its own header
        print(f"OCR fragments to tag as 'noise'  ({'APPLY' if args.apply else 'DRY-RUN'}; "
              f"dev<{args.min_dev} AND lat<{args.min_lat}):")
''', 1))

TARGETS = [(Path("scripts/corpus_status.py"), CS_EDITS), (Path("scripts/classify_noise.py"), CN_EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    marks = [MARK in s for _, s, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand:")
        for (p, _s, _n, _e), m in zip(loaded, marks):
            print("  %-30s %s" % (p, "patched" if m else "not patched"))
        return 1
    problems, out = [], []
    for p, src, nl, edits in loaded:
        for label, old, new, n in edits:
            c = src.count(old)
            if c != n:
                problems.append("%s %s: matched %d times, expected %d" % (p.name, label, c, n))
            else:
                src = src.replace(old, new)
        out.append((p, src, nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files. Nothing written."
              % (sum(len(e) for _, e in TARGETS), len(TARGETS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_gaps")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_gaps_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("corpus_status is read-only; classify_noise --running-heads is a dry run until --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
