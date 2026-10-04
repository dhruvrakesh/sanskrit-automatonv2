#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_guards_2026_10_04.py  (2026-10-04)  INGEST_SOURCE_2026_10_04 + TRANSLATE_DEBRIS_GUARD_2026_10_04

Two guards at the two doors every path goes through (dashboard buttons,
advance_pipeline.py "Translate All OCR'd", the CLI). All-or-nothing across both
files, marker-idempotent, backups, py_compile, atomic replace.

scripts/ingest_jsonl_fast.py  - INGEST_SOURCE_2026_10_04
  Found on 2026-10-04, read from the code and the files:
  (a) The glob "<doc>_*.jsonl" also matches OTHER docs whose code starts with
      <doc>_. data/raw holds smriti_14manu_smriti_0001..0208 AND
      smriti_14manu_smriti_seg_0001..0208 (same for smriti_16harita_smriti), so an
      ingest of the source doc also ingested the derived doc's files on the same
      page numbers. Both docs show 2,568 rows in corpus_status - consistent with
      that. Now, when --glob is the plain "<doc>_*.jsonl", only files named
      <doc>_NNNN.jsonl / <doc>_NNNN_norm.jsonl are taken, and the rest are named.
  (b) The dashboard Ingest button and advance_pipeline.py both pass
      data/raw/<doc>_*.jsonl (Tesseract). For a doc whose OCR consensus is in
      data/raw_merged, that silently put Tesseract text back over consensus text
      (and upsert keeps the old translations on the new text). Now:
        raw_merged covers every page  -> ingest raw_merged instead, and say so;
        raw_merged covers some pages  -> REFUSE (exit 3), say how many;
        --source raw                  -> Tesseract, knowingly;
        --source given                -> the glob exactly as given (old behaviour).
      A glob that names any other folder (raw_merged, a derived doc's raw files)
      is used as given, except for (a).

scripts/translate_passages.py  - TRANSLATE_DEBRIS_GUARD_2026_10_04
  Refuses (exit 3, before any API call) to translate a doc whose stored text is
  Tesseract debris that can be repaired first:
      debris share > --debris-max (default 30%, env SA_DEBRIS_MAX)
      AND under half the passages from vision OCR
      AND inbox holds page PDFs for the doc (so consensus can run).
  Debris = passages (>= 8 Devanagari chars) with Latin-letter runs, the
  corpus_status test; measured 2026-10-04: Tesseract 10-71%, vision 0-2%.
  At 30% it stops Rgveda Vol-ii (53.9% in its page files), Pataal Khanda (48.5%),
  HAYASHIRSHA (36.0%), and lets Ganita (10.3%), Natyasastra (29.6%) and books with
  no source PDF through. Override: --allow-debris, or env SA_ALLOW_DEBRIS=1 (for
  dashboard runs). Single-verse reader requests (--only-page) are never blocked.

  python scripts/patch_guards_2026_10_04.py --check
  python scripts/patch_guards_2026_10_04.py
Test: python -m unittest tests.test_guards_2026_10_04 -v   (fails before, passes after)
Running jobs are unaffected (each ingest/translate run is a new process).
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK_I = "INGEST_SOURCE_2026_10_04"
MARK_T = "TRANSLATE_DEBRIS_GUARD_2026_10_04"
ING = Path("scripts/ingest_jsonl_fast.py")
TRN = Path("scripts/translate_passages.py")

ING_HELPER = r'''

# INGEST_SOURCE_2026_10_04 ---------------------------------------------------
def _resolve_source(doc, pattern, paths, mode="auto"):
    """(paths, note, refuse). See patch_guards_2026_10_04.py for why."""
    rx = re.compile(r"^%s_(\d{4})(?:_norm)?\.jsonl$" % re.escape(doc))
    pat = pathlib.Path(pattern)
    simple = pat.name == "%s_*.jsonl" % doc
    notes = []
    if not simple or mode == "given":
        return paths, "", False
    kept = [p for p in paths if rx.match(p.name)]
    if len(kept) != len(paths):
        other = sorted(p.name for p in paths if not rx.match(p.name))
        notes.append("[ingest] %s: %d file(s) matched %s but belong to another doc (e.g. %s) - skipped"
                     % (MARK_SOURCE, len(other), pat.name, other[0]))
    paths = kept
    if mode == "auto" and pat.parent.name.lower() == "raw":
        mdir = pat.parent.parent / "raw_merged"
        merged = sorted(p for p in mdir.glob("%s_*.jsonl" % doc) if rx.match(p.name)) if mdir.is_dir() else []
        if merged:
            raw_pages = {rx.match(p.name).group(1) for p in paths}
            m_pages = {rx.match(p.name).group(1) for p in merged}
            if raw_pages <= m_pages:
                notes.append("[ingest] %s: data/raw_merged holds OCR consensus for all %d page(s) of %s - "
                             "ingesting those instead of data/raw (Tesseract). --source raw forces Tesseract."
                             % (MARK_SOURCE, len(m_pages), doc))
                return merged, "\n".join(notes), False
            notes.append("REFUSING (%s): data/raw_merged holds consensus for %d of %d page(s) of %s. Ingesting "
                         "data/raw would put Tesseract text back over consensus text. Finish the consensus "
                         "(python scripts\\ocr_consensus.py --doc %s ...) or pass --source raw."
                         % (MARK_SOURCE, len(raw_pages & m_pages), len(raw_pages), doc, doc))
            return paths, "\n".join(notes), True
    return paths, "\n".join(notes), False


MARK_SOURCE = "INGEST_SOURCE_2026_10_04"
'''

ING_EDITS = [
    ("helper", "\n\ndef main():\n", ING_HELPER + "\n\ndef main():\n", 1),
    ("arg", '    ap.add_argument("--no-iast",     action="store_true", help="skip IAST generation")\n',
     '    ap.add_argument("--no-iast",     action="store_true", help="skip IAST generation")\n'
     '    ap.add_argument("--source", choices=["auto", "raw", "given"], default="auto",\n'
     '                    help="INGEST_SOURCE_2026_10_04: auto = for data/raw/<doc>_*.jsonl prefer complete "\n'
     '                         "OCR consensus in data/raw_merged; raw = Tesseract; given = the glob as is")\n', 1),
    ("resolve", "    paths = sorted(pathlib.Path(p) for p in _glob.glob(args.glob))\n",
     "    paths = sorted(pathlib.Path(p) for p in _glob.glob(args.glob))\n"
     "    paths, _src_note, _src_refuse = _resolve_source(args.doc, args.glob, paths, args.source)  # INGEST_SOURCE_2026_10_04\n"
     "    if _src_note:\n"
     "        print(_src_note)\n"
     "    if _src_refuse:\n"
     "        sys.exit(3)\n", 1),
]

TRN_HELPER = r'''
# TRANSLATE_DEBRIS_GUARD_2026_10_04 -------------------------------------------
def _debris_guard(con, doc, debris_max, inbox=None):
    """A refusal message when the doc's stored text is repairable Tesseract debris, else None."""
    import re as _re
    junk = _re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")     # = diag_hindi_ab.JUNK
    dev = _re.compile(r"[\u0900-\u097f]")
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    eng = "p.ocr_engine" if "ocr_engine" in cols else "NULL"
    scope = ("AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in cols else "")
    n = dn = bad = vis = 0
    for text, oe in con.execute(f"""SELECT p.text, {eng} FROM passages p JOIN docs d ON d.id = p.doc_id
                                    WHERE d.code = ? {scope}""", (doc,)):
        n += 1
        vis += 1 if "vision" in (oe or "").lower() else 0
        if len(dev.findall(text or "")) >= 8:
            dn += 1
            bad += 1 if junk.search(text) else 0
    if not dn:
        return None
    share, vshare = 100.0 * bad / dn, 100.0 * vis / max(1, n)
    inbox = Path(inbox or os.environ.get("SA_INBOX_DIR") or Path(__file__).resolve().parent.parent / "inbox")
    rx = _re.compile(r"^%s_\d{4}\.pdf$" % _re.escape(doc), _re.I)
    pdfs = sum(1 for p in inbox.iterdir() if rx.match(p.name)) if inbox.is_dir() else 0
    if share <= debris_max or vshare >= 50.0 or not pdfs:
        return None
    return ("REFUSING (TRANSLATE_DEBRIS_GUARD_2026_10_04): %.1f%% of %s's passages carry Tesseract debris "
            "(Latin letters inside Devanagari; vision text measures 0-2%%), %.0f%% come from vision OCR, and inbox "
            "holds %d page PDF(s), so the source can be repaired first. Translating now pays for text that "
            "consensus will replace.\n  Next (plan, no spend): python scripts\\ocr_consensus.py --doc %s "
            "--threshold 101 --include-unassessed\n  Translate anyway: add --allow-debris "
            "(dashboard: set SA_ALLOW_DEBRIS=1)." % (share, doc, vshare, pdfs, doc))


'''

TRN_EDITS = [
    ("helper", "\ndef main():\n", TRN_HELPER + "def main():\n", 1),
    ("args", '    ap.add_argument("--reference", choices=["auto", "none"], default="auto",\n',
     '    ap.add_argument("--allow-debris", action="store_true",\n'
     '                    help="TRANSLATE_DEBRIS_GUARD_2026_10_04: translate even when the source is repairable "\n'
     '                         "Tesseract debris (env SA_ALLOW_DEBRIS=1 does the same)")\n'
     '    ap.add_argument("--debris-max", type=float, default=float(os.environ.get("SA_DEBRIS_MAX") or 30.0),\n'
     '                    help="TRANSLATE_DEBRIS_GUARD_2026_10_04: refuse above this %% of debris passages")\n'
     '    ap.add_argument("--reference", choices=["auto", "none"], default="auto",\n', 1),
    ("guard",
     '    if doc_meta["id"] is None:\n        print(f"ERROR: doc \'{args.doc}\' not found in DB")\n        sys.exit(1)\n',
     '    if doc_meta["id"] is None:\n        print(f"ERROR: doc \'{args.doc}\' not found in DB")\n        sys.exit(1)\n'
     '    if (args.only_page is None and not args.allow_debris\n'
     '            and os.environ.get("SA_ALLOW_DEBRIS", "") not in ("1", "true", "yes")):   # TRANSLATE_DEBRIS_GUARD_2026_10_04\n'
     '        _msg = _debris_guard(con, args.doc, args.debris_max)\n'
     '        if _msg:\n'
     '            print(_msg)\n'
     '            sys.exit(3)\n', 1),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def apply(src, edits):
    probs = []
    for label, old, new, n in edits:
        c = src.count(old)
        if c != n:
            probs.append("%s: matched %d times, expected %d" % (label, c, n))
        else:
            src = src.replace(old, new)
    return src, probs


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (ING, TRN):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    i_src, i_nl = load(ING); t_src, t_nl = load(TRN)
    have = (MARK_I in i_src, MARK_T in t_src)
    if all(have):
        print("Already patched. Nothing to do."); return 0
    if any(have):
        print("REFUSING: marker in one file only - inspect by hand."); return 1
    i_new, p1 = apply(i_src, ING_EDITS)
    t_new, p2 = apply(t_src, TRN_EDITS)
    if "import argparse, json, sqlite3, sys, re, pathlib" not in i_src:
        p1.append("ingest_jsonl_fast: expected 're' and 'pathlib' imported on the import line")
    if "from pathlib import Path" not in t_src or "import argparse, sqlite3, time, sys, json, os" not in t_src:
        p2.append("translate_passages: expected 'os' and 'Path' imported")
    if p1 or p2:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in p1 + p2]; return 1
    if args.check:
        print("CHECK OK: %d + %d anchored edits. Nothing written." % (len(ING_EDITS), len(TRN_EDITS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in ((ING, i_new, i_nl), (TRN, t_new, t_nl)):
        t = p.with_name(p.name + ".tmp_guards")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_guards_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
