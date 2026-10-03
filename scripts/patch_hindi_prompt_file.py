#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_hindi_prompt_file.py  (2026-10-03)  HI_PROMPT_FILE_2026_10_03

Makes the Hindi prompt a reviewed DATA file instead of a code edit, and adds the
two switches the 2026-10-01/03 measurements asked for. Changes nothing in
production until prompts/hi-production.txt exists.

scripts/infer_mt.py
  * If prompts/hi-production.txt exists (or SA_HI_PROMPT_FILE points to a file),
    it becomes the Hindi base prompt, and PROMPT_VERSIONS['hi'] becomes
    'hi-file-<sha256 of the text, first 10 hex>'. A new text is therefore a new
    cache key and a new mt_prompt_version on every row it writes - automatically.
    Line endings are normalised before hashing (git may check the file out CRLF).
  * No file: the built-in hi-v3 prompt and version, byte for byte as today.

scripts/translate_passages.py
  * --reference {auto,none}  (Hindi only; default auto = today's behaviour).
    none: the English of the verse is not shown to the model. The prompt version
    gains '+noref', so a cached answer made WITH the reference is never reused.
  * --only-lacuna  re-translate ONLY rows whose stored translation carries the
    lacuna mark ([ILLEGIBLE] for en, [asphuta] for hi). Implies --retranslate; the
    previous row is archived to translation_history first, as --retranslate does.

  python scripts/patch_hindi_prompt_file.py --check
  python scripts/patch_hindi_prompt_file.py
Test: python -m unittest tests.test_hindi_prompt_file -v   (fails before, passes after)
Running jobs are unaffected (each translate run is a new process).
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "HI_PROMPT_FILE_2026_10_03"
MT = Path("scripts/infer_mt.py")
TP = Path("scripts/translate_passages.py")

MT_START = '_SYSTEM_PROMPT_HI = """'
MT_INSERT = '''

# HI_PROMPT_FILE_2026_10_03: the production Hindi prompt may live in a reviewed
# file (prompts/hi-production.txt, or SA_HI_PROMPT_FILE). Its version is derived
# from its content, so changing the text is a new cache key automatically.
# No file -> the built-in prompt above and PROMPT_VERSIONS['hi'], unchanged.
HI_PROMPT_SOURCE = "built-in"
_HI_PROMPT_FILE = os.environ.get("SA_HI_PROMPT_FILE") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "hi-production.txt")
try:
    if os.path.isfile(_HI_PROMPT_FILE):
        with open(_HI_PROMPT_FILE, encoding="utf-8") as _hf:
            _hi_txt = _hf.read().replace("\\r\\n", "\\n").strip()
        if len(_hi_txt) >= 200:
            _SYSTEM_PROMPT_HI = _hi_txt
            PROMPT_VERSIONS["hi"] = "hi-file-" + hashlib.sha256(_hi_txt.encode("utf-8")).hexdigest()[:10]
            HI_PROMPT_SOURCE = _HI_PROMPT_FILE
        else:
            print(f"[infer_mt] {_HI_PROMPT_FILE} is too short ({len(_hi_txt)} chars); built-in Hindi prompt used")
except Exception as _hi_err:   # never let a bad file stop translation
    print(f"[infer_mt] Hindi prompt file ignored: {type(_hi_err).__name__}: {_hi_err}")
'''

TP_EDITS = [
    ("args",
     '    ap.add_argument("--retry-illegible", action="store_true",\n',
     '    ap.add_argument("--reference", choices=["auto", "none"], default="auto",\n'
     '                    help="HI_PROMPT_FILE_2026_10_03: Hindi only. none = do not show the model the "\n'
     '                         "English of the verse (prompt version gains +noref).")\n'
     '    ap.add_argument("--only-lacuna", action="store_true",\n'
     '                    help="HI_PROMPT_FILE_2026_10_03: re-translate only rows whose stored translation "\n'
     '                         "carries the lacuna mark; implies --retranslate (old rows are archived).")\n'
     '    ap.add_argument("--retry-illegible", action="store_true",\n'),
    ("parse",
     '    args = ap.parse_args()\n',
     '    args = ap.parse_args()\n'
     '    if args.only_lacuna:   # HI_PROMPT_FILE_2026_10_03\n'
     '        args.retranslate = True\n'),
    ("noref version",
     '    IS_L10N = TGT != "en"   # Phase HI: additional-language mode \u2192 translations_l10n\n',
     '    IS_L10N = TGT != "en"   # Phase HI: additional-language mode \u2192 translations_l10n\n'
     '    if IS_L10N and args.reference == "none":   # HI_PROMPT_FILE_2026_10_03\n'
     '        # A distinct prompt version: the cache key and mt_prompt_version both carry it,\n'
     '        # so an answer made WITH the English reference is never served as one without.\n'
     '        PROMPT_VERSIONS[TGT] = PROMPT_VERSIONS.get(TGT, PROMPT_VERSION) + "+noref"\n'),
    ("l10n only-lacuna",
     '        if not args.retranslate:\n'
     '            where_extra.append("NOT EXISTS (SELECT 1 FROM translations_l10n l "\n',
     '        if args.only_lacuna:   # HI_PROMPT_FILE_2026_10_03\n'
     '            where_extra.append("EXISTS (SELECT 1 FROM translations_l10n l2 WHERE l2.passage_id=p.id "\n'
     '                               "AND l2.lang=? AND l2.translation LIKE ?)")\n'
     '            params.extend([TGT, "%[\\u0905\\u0938\\u094d\\u092a\\u0937\\u094d\\u091f]%"])\n'
     '        if not args.retranslate:\n'
     '            where_extra.append("NOT EXISTS (SELECT 1 FROM translations_l10n l "\n'),
    ("en only-lacuna",
     '        translation_filter = ("" if args.retranslate\n',
     '        translation_filter = ("AND p.translation LIKE \'%[ILLEGIBLE]%\'" if args.only_lacuna  # HI_PROMPT_FILE_2026_10_03\n'
     '                              else "" if args.retranslate\n'),
    ("use_ref",
     '        use_ref = bool(IS_L10N and eng_ref and str(eng_ref).strip()\n',
     '        use_ref = bool(IS_L10N and args.reference != "none"   # HI_PROMPT_FILE_2026_10_03\n'
     '                       and eng_ref and str(eng_ref).strip()\n'),
]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def patch_mt(src: str) -> tuple[str, str | None]:
    if src.count(MT_START) != 1:
        return src, "infer_mt: '_SYSTEM_PROMPT_HI = \"\"\"' matched %d times" % src.count(MT_START)
    i = src.index(MT_START) + len(MT_START)
    j = src.find('"""', i)
    if j < 0:
        return src, "infer_mt: end of the Hindi prompt not found"
    k = src.find("\n", j) + 1
    for need in ("import os", "hashlib", "PROMPT_VERSIONS = {"):
        if need not in src[:i]:
            return src, "infer_mt: %r must appear before the Hindi prompt" % need
    return src[:k] + MT_INSERT + src[k:], None


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (MT, TP):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    mt, mt_nl = load(MT); tp, tp_nl = load(TP)
    if MARK in mt and MARK in tp:
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if (MARK in mt) != (MARK in tp):
        print("REFUSING: marker in only one of the two files - inspect by hand."); return 1
    problems = []
    mt2, err = patch_mt(mt)
    if err:
        problems.append(err)
    tp2 = tp
    for label, old, new in TP_EDITS:
        n = tp2.count(old)
        if n != 1:
            problems.append("translate_passages %s: matched %d times, expected 1" % (label, n))
        else:
            tp2 = tp2.replace(old, new)
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: infer_mt insert + %d translate_passages anchors. Nothing written." % len(TP_EDITS)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in ((MT, mt2, mt_nl), (TP, tp2, tp_nl)):
        t = p.with_name(p.name + ".tmp_hifile")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_hifile_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
    print("PATCHED infer_mt.py and translate_passages.py (backups *.bak_hifile_%s)." % stamp)
    print("Nothing changes until prompts\\hi-production.txt exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
