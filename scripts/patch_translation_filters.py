#!/usr/bin/env python3
"""patch_translation_filters.py  (MARK TRANSLATION_FILTERS_2026_09_27)

Why valid Sanskrit came back EMPTY, and the Hindi hard-fail token was printed.
Anchored, all-or-nothing, idempotent. Three files:

  text_filters.py        refusal phrases that are ordinary language ("the
                         remainder of" = vakyasesa, "I am sorry", Hindi "yah
                         patha") count only in a sentence about the input;
                         the Hindi token [asphuta] is caught like [ILLEGIBLE];
                         a Devanagari citation copied into English is not an
                         echo of the verse.
  infer_mt.py            the budget gate raises BudgetBlocked (a QuotaExhausted)
                         instead of returning silent empties; Hindi rule 7 no
                         longer invents a speaker; hi prompt -> hi-v2-2026-09-27.
  translate_passages.py  every empty or salvaged result is kept, raw, with its
                         cause, in data/translate_outcomes.jsonl.

  python scripts/patch_translation_filters.py --root .            # check only
  python scripts/patch_translation_filters.py --root . --apply    # write

Every anchor must match exactly once in every file before anything is
written. Each file is backed up as <name>.bak_tf_20260927 first. Line
endings are preserved. A file that already carries the marker is skipped.
Running jobs keep the code they imported; new jobs pick this up.
"""
import argparse, py_compile, shutil, sys
from pathlib import Path

MARK = "TRANSLATION_FILTERS_2026_09_27"
EDITS = [
  ('scripts/text_filters.py', [
    ('refusal helpers',
     'def salvage_translation(out: str, lang: str = "en") -> str:\n',
     '# -- Sentence-scoped refusal detection (TRANSLATION_FILTERS_2026_09_27) --------\n# The phrase lists above are plain substring tests over the whole output, and\n# some of their phrases are ordinary language that a FAITHFUL translation uses.\n# Replayed 2026-09-27 on faithful translations, the old test empties:\n#   vakyasesa         -> "the remainder of the sentence ..."   (the remainder of)\n#   a speaker\'s words -> "I am sorry, O king ..."               (i am sorry)\n#   Hindi commentary  -> "yah patha ..." / "sesa patha ..."\n# An AMBIGUOUS phrase therefore counts only when the sentence it sits in also\n# talks about the INPUT - OCR, legibility, the text supplied, translating it.\n# Every other phrase is unchanged and still counts wherever it appears, so a\n# real refusal is caught exactly as before. A Hindi output that is NOTHING\n# BUT the hard-fail token the prompt asks for, "[asphuta]", is now empty like\n# its English twin "[ILLEGIBLE]" always was; until today it was stored and\n# printed as a translation. The token INSIDE a translation is a lacuna mark\n# and is left alone.\n_AMBIGUOUS_EN = frozenset((\n    "i am sorry", "sorry, but", "i\'m sorry, but", "i\'m sorry, i cannot",\n    "cannot identify", "the remainder of", "the rest of the text",\n    "the remaining text",\n))\n_META_CUES_EN = (\n    "ocr", "illegib", "legible", "garbl", "unclear", "corrupt", "snippet",\n    "provided", "translat", "transcri", "the input", "source text",\n    "sanskrit text", "this passage", "the passage", "noise", "misprint",\n    "scan", "sanskrit", "coherent",\n)\n_TOKEN_HI = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"          # [asphuta]\n_AMBIGUOUS_HI = frozenset((\n    "\u092f\u0939 \u092a\u093e\u0920",                                  # yah patha\n    "\u0938\u094d\u092a\u0937\u094d\u091f \u0928\u0939\u0940\u0902",    # spasta nahim\n    "\u092a\u094d\u0930\u0926\u093e\u0928 \u0928\u0939\u0940\u0902 \u0915\u0930",  # pradana nahim kara\n    "\u0915\u094d\u0937\u092e\u093e \u0915\u0930",                      # ksama kara\n    "\u092e\u0948\u0902 \u0905\u0938\u092e\u0930\u094d\u0925",          # maim asamartha\n    "\u0936\u0947\u0937 \u092a\u093e\u0920",                            # sesa patha\n    "\u0936\u0947\u0937 \u092d\u093e\u0917",                            # sesa bhaga\n))\n_META_CUES_HI = (\n    "\u0913\u0938\u0940\u0906\u0930",                  # osiar (OCR)\n    "\u092a\u0920\u0928\u0940\u092f",                  # pathaniya (legible)\n    "\u0905\u0938\u094d\u092a\u0937\u094d\u091f",      # asphuta (unclear)\n    "\u0905\u0928\u0941\u0935\u093e\u0926",            # anuvada (translation)\n    "\u0926\u093f\u092f\u093e \u0917\u092f\u093e",     # diya gaya (given)\n    "\u092a\u094d\u0930\u0926\u0924\u094d\u0924",      # pradatta (supplied)\n    "\u0938\u094d\u0915\u0948\u0928",                  # scan\n    "ocr", "translat",\n)\n_SENT_BOUND_RE = re.compile(r"[.!?\u0964\u0965\\n]|//")\n\n\ndef _sentence_around(s: str, i: int, n: int) -> str:\n    """The sentence of s that contains s[i:i+n]."""\n    start = 0\n    for m in _SENT_BOUND_RE.finditer(s, 0, i):\n        start = m.end()\n    m = _SENT_BOUND_RE.search(s, i + n)\n    return s[start:(m.start() if m else len(s))]\n\n\ndef _bare_token_hi(t: str) -> bool:\n    """True when t is only the [asphuta] token(s) and punctuation."""\n    rest = t.replace(_TOKEN_HI, " ").strip()\n    return rest != t.strip() and (not rest or bool(ONLY_PUNCT_RE.match(rest)))\n\n\ndef _refusal_cut(t: str, lang: str = "en", caveats: bool = True) -> int:\n    """Earliest index in t where a refusal or OCR caveat begins, else -1.\n\n    caveats=False tests the refusal lists only (is_translation_boilerplate\'s\n    historical scope); True adds the caveat lists (salvage_translation\'s).\n    """\n    if not t:\n        return -1\n    if lang == "hi" and _bare_token_hi(t):\n        return 0\n    low = t.lower()\n    cut = -1\n\n    def scan(hay, phrases, ambiguous, cues):\n        nonlocal cut\n        for ph in phrases:\n            pos = hay.find(ph)\n            while pos >= 0:\n                if ph not in ambiguous or any(\n                        c in _sentence_around(hay, pos, len(ph)) for c in cues):\n                    if cut < 0 or pos < cut:\n                        cut = pos\n                    break\n                pos = hay.find(ph, pos + 1)\n\n    scan(low, JUNK_PHRASES + (_CAVEAT_EXTRA if caveats else ()),\n         _AMBIGUOUS_EN, _META_CUES_EN)\n    if lang == "hi":\n        scan(t, JUNK_PHRASES_HI + (_CAVEAT_HI_EXTRA if caveats else ()),\n             _AMBIGUOUS_HI, _META_CUES_HI)\n    return cut\n\n\ndef salvage_translation(out: str, lang: str = "en") -> str:\n'),
    ('salvage uses the helper',
     '    t = out.strip()\n    low = t.lower()\n    cut = len(t); found = False\n    for ph in JUNK_PHRASES + _CAVEAT_EXTRA:\n        i = low.find(ph)\n        if 0 <= i < cut:\n            cut = i; found = True\n    if lang == "hi":\n        for ph in JUNK_PHRASES_HI + _CAVEAT_HI_EXTRA:\n            i = t.find(ph)\n            if 0 <= i < cut:\n                cut = i; found = True\n    if not found:\n',
     '    t = out.strip()\n    cut = _refusal_cut(t, lang, caveats=True)   # TRANSLATION_FILTERS_2026_09_27\n    found = cut >= 0\n    if not found:\n'),
    ('boilerplate uses the helper',
     '    if any(x in t for x in JUNK_PHRASES): return True\n    if lang == "hi" and any(x in en for x in JUNK_PHRASES_HI): return True\n',
     '    # TRANSLATION_FILTERS_2026_09_27: the same lists, sentence-scoped for the\n    # ambiguous phrases, plus the Hindi hard-fail token.\n    if _refusal_cut(en.strip(), lang, caveats=False) >= 0: return True\n'),
    ('echo tolerates copied citations',
     '    # Latin-script target (English): the output is the Devanagari source, or\n    # carries embedded Devanagari verse-number digits / OCR gibberish.\n    if DEV_DIGIT_RE.search(o):\n        return True\n    if frac_devanagari(o) > 0.5:\n        return True\n    return False\n',
     '    # Latin-script target (English): the output is the Devanagari source, or\n    # carries embedded Devanagari verse-number digits / OCR gibberish.\n    # TRANSLATION_FILTERS_2026_09_27: a citation the model kept verbatim in\n    # Devanagari - "(ma. sa. pa. bra. 7 | 2 | 1 | 24)" as printed - or a\n    # printed verse number between dandas is not an echo of the verse, and it\n    # emptied whole commentary translations. Test what is left once those\n    # are set aside. Unbracketed digits, an output that is mostly Devanagari,\n    # and an output with no English left in it are still echoes.\n    core = _EN_CITATION_RE.sub(\n        lambda m: " " if DEV_RE.search(m.group(0)) else m.group(0), o)\n    core = _EN_VNUM_RE.sub(" ", core)\n    if not LATIN_RE.search(core):\n        return True\n    if DEV_DIGIT_RE.search(core):\n        return True\n    if frac_devanagari(core) > 0.5 or frac_devanagari(o) > 0.5:\n        return True\n    return False\n\n\n_EN_CITATION_RE = re.compile(r"[\\(\\[][^()\\[\\]\\n]{1,90}[\\)\\]]")\n_EN_VNUM_RE = re.compile(r"[\\u0964\\u0965|]+\\s*[\\u0966-\\u096f]{1,4}\\s*[\\u0964\\u0965|]*")\n'),
  ]),
  ('scripts/infer_mt.py', [
    ('BudgetBlocked',
     '    than grind on \u2014 continuing produces empty results for every verse."""\n    pass\n',
     '    than grind on \u2014 continuing produces empty results for every verse."""\n    pass\n\n\nclass BudgetBlocked(QuotaExhausted):\n    """TRANSLATION_FILTERS_2026_09_27. The budget cap refused the call. It used\n    to return empty strings, which translate_passages counts as untranslatable\n    source and carries on - so a capped run walked the whole queue, wrote\n    nothing and reported success. As a QuotaExhausted it aborts the run with\n    the reason, exactly like a provider quota does."""\n    pass\n'),
    ('budget gate raises',
     '                # Return empty strings for uncached \u2014 don\'t call API\n                return [outs[i] or "" for i in range(len(texts))]\n',
     '                # TRANSLATION_FILTERS_2026_09_27: refuse loudly - an empty\n                # result here would be recorded as untranslatable source.\n                raise BudgetBlocked(\n                    f"budget cap reached: spent ${spent:.4f} of ${budget:.2f}; "\n                    f"next batch ~${est_cost:.4f}. Raise it with set_budget.py.")\n'),
    ('hi prompt version',
     '    "hi": "hi-v1-2026-08-01",\n',
     '    "hi": "hi-v2-2026-09-27",   # TRANSLATION_FILTERS_2026_09_27: rule 7\n'),
    ('hi rule 7',
     '7. \u0935\u0915\u094d\u0924\u093e-\u0938\u0942\u091a\u0928\u093e: "\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928 \u0928\u0947 \u0915\u0939\u093e \u2014" \u0907\u0938 \u0936\u0948\u0932\u0940 \u092e\u0947\u0902 \u0935\u0915\u094d\u0924\u093e-\u092a\u0902\u0915\u094d\u0924\u093f\u092f\u093e\u0901 \u0930\u0916\u0947\u0902\u0964\n',
     '7. \u0935\u0915\u094d\u0924\u093e-\u0938\u0942\u091a\u0928\u093e: \u0935\u0915\u094d\u0924\u093e-\u092a\u0902\u0915\u094d\u0924\u093f \u0915\u0947\u0935\u0932 \u0924\u092d\u0940 \u0926\u0947\u0902 \u091c\u092c \u0938\u0902\u0938\u094d\u0915\u0943\u0924 \u092a\u093e\u0920 \u092e\u0947\u0902 \u0938\u094d\u0935\u092f\u0902 \u0935\u0915\u094d\u0924\u093e \u0939\u094b (\u091c\u0948\u0938\u0947 "<\u0928\u093e\u092e> \u0909\u0935\u093e\u091a" \u2192 "<\u0928\u093e\u092e> \u0928\u0947 \u0915\u0939\u093e \u2014")\u0964 \u091c\u0939\u093e\u0901 \u0938\u0902\u0938\u094d\u0915\u0943\u0924 \u092e\u0947\u0902 \u0935\u0915\u094d\u0924\u093e \u0928\u0939\u0940\u0902 \u0939\u0948, \u0935\u0939\u093e\u0901 \u0915\u094b\u0908 \u0935\u0915\u094d\u0924\u093e \u0928 \u091c\u094b\u0921\u093c\u0947\u0902\u0964\n'),
  ]),
  ('scripts/translate_passages.py', [
    ('outcome ledger helper',
     'def _get_doc_meta(con, doc):\n',
     '# TRANSLATION_FILTERS_2026_09_27. Every verse that ends EMPTY after a paid call,\n# and every verse whose output was cut back by salvage, is recorded here with\n# the model\'s raw output and the cause. Until now the raw output was thrown\n# away, so "valid Sanskrit came back empty" could not be told apart from a\n# model refusal, a filter false positive or a copied citation. Append-only,\n# one JSON object per line, never raises.\ndef _log_outcome(rec):\n    try:\n        path = _PROGRESS_PATH.parent / "translate_outcomes.jsonl"\n        path.parent.mkdir(parents=True, exist_ok=True)\n        rec = dict(rec, ts=datetime.now(timezone.utc).isoformat())\n        with open(path, "a", encoding="utf-8") as fh:\n            fh.write(json.dumps(rec, ensure_ascii=False) + "\\n")\n    except Exception:\n        pass\n\n\ndef _get_doc_meta(con, doc):\n'),
    ('tally init',
     '    recent       = []\n',
     '    recent       = []\n    empty_by     = {}   # TRANSLATION_FILTERS_2026_09_27: cause -> count\n'),
    ('raw output kept',
     '            translation = outs[0] if outs else ""\n',
     '            translation = outs[0] if outs else ""\n            raw_out = translation      # TRANSLATION_FILTERS_2026_09_27\n            empty_why = None if translation else "model-empty"\n'),
    ('junk cause',
     '                        print(f"  [SKIP-JUNK] p{page_no}.{idx}: {translation[:60]!r}")\n',
     '                        print(f"  [SKIP-JUNK] p{page_no}.{idx}: {translation[:60]!r}")\n                        empty_why = "refusal-filter"\n'),
    ('echo cause',
     '                    print(f"  [SKIP-ECHO] p{page_no}.{idx}: source echoed, not translated")\n                    translation = ""\n',
     '                    print(f"  [SKIP-ECHO] p{page_no}.{idx}: source echoed, not translated")\n                    translation = ""\n                    empty_why = "echo-filter"\n'),
    ('salvage recorded',
     '            if translation:\n                consec_fail = 0\n            else:\n',
     '            if translation:\n                consec_fail = 0\n                if translation != raw_out:\n                    _log_outcome({"doc": args.doc, "lang": TGT, "passage_id": rowid,\n                                  "page": page_no, "idx": idx, "quality": quality,\n                                  "cause": "salvaged", "kept": translation,\n                                  "raw": raw_out, "source": cleaned[:2000]})\n            else:\n'),
    ('empty recorded',
     '                skip_quality += 1\n                consec_fail = 0\n',
     '                skip_quality += 1\n                consec_fail = 0\n                why = empty_why or "model-empty"\n                empty_by[why] = empty_by.get(why, 0) + 1\n                print(f"  [EMPTY:{why}] p{page_no}.{idx} q={quality:.2f}")\n                _log_outcome({"doc": args.doc, "lang": TGT, "passage_id": rowid,\n                              "page": page_no, "idx": idx, "quality": quality,\n                              "cause": why, "raw": raw_out, "source": cleaned[:2000]})\n'),
    ('summary line',
     '    print(f"\\nDone. {ok_count}/{len(todo)} translated | "\n          f"{skip_quality} quality-skipped | {err_count} errors")\n',
     '    print(f"\\nDone. {ok_count}/{len(todo)} translated | "\n          f"{skip_quality} quality-skipped | {err_count} errors")\n    if empty_by:   # TRANSLATION_FILTERS_2026_09_27\n        print("  of those, empty after a paid call: " + ", ".join(\n            f"{k}={v}" for k, v in sorted(empty_by.items()))\n              + "  (raw outputs: data/translate_outcomes.jsonl)")\n'),
  ]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    plan, bad = [], 0
    for rel, eds in EDITS:
        p = root / rel
        if not p.exists():
            print("  MISSING  %s" % rel); bad += 1; continue
        raw = p.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        if MARK in text:
            print("  already  %s (marker present) - skipped" % rel); continue
        new = text
        for name, old, rep in eds:
            n = new.count(old)
            if n != 1:
                print("  ANCHOR   %s :: %s matched %d time(s), need exactly 1" % (rel, name, n))
                bad += 1
                continue
            new = new.replace(old, rep, 1)
            print("  ok       %s :: %s" % (rel, name))
        if MARK not in new:
            print("  ANCHOR   %s :: marker not present after edits" % rel); bad += 1
        plan.append((p, crlf, new))
    if bad:
        print("REFUSED: %d problem(s); nothing written." % bad)
        return 2
    if not plan:
        print("nothing to do - every file already patched.")
        return 0
    if not a.apply:
        print("CHECK PASSED for %d file(s). Re-run with --apply to write." % len(plan))
        return 0
    for p, crlf, new in plan:
        bak = p.with_name(p.name + ".bak_tf_20260927")
        if not bak.exists():
            shutil.copy2(p, bak)
        data = new.replace("\n", "\r\n") if crlf else new
        p.write_bytes(data.encode("utf-8"))
        py_compile.compile(str(p), doraise=True)
        print("  WROTE    %s  (backup %s)" % (p.name, bak.name))
    print("APPLIED. To undo: copy each .bak_tf_20260927 back over its file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
