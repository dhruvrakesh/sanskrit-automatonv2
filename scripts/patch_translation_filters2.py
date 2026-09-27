#!/usr/bin/env python3
"""patch_translation_filters2.py  (MARK TRANSLATION_FILTERS2_2026_09_27)

Second pass, from the paid probe on the live corpus (block_AY -Probe, 12 verses):

  text_filters.py   "[ILLEGIBLE]" / "[asphuta]" INSIDE a translation is a lacuna
                    mark, not a refusal; only an output that is nothing but the
                    token is empty. (Shatapatha p131.2, p251.3: full faithful
                    translations with one damaged word, both emptied.)
  infer_mt.py       rule 12 (en) and rule 10 (hi): the token alone ONLY when no
                    part is readable; otherwise translate and mark the gap.
                    Prompts -> v3-2026-09-27 / hi-v3-2026-09-27 (new cache keys;
                    already-translated rows are never re-requested, so no re-bill).
  translate_passages.py  --lang help text records the direct sa->hi decision.
  dashboard.py      /api/translate accepts optional since_page / until_page, so a
                    retry of the verses a run went past stays inside that window.
                    Additive; omitted keys behave exactly as before.

  python scripts/patch_translation_filters2.py --root .           # check
  python scripts/patch_translation_filters2.py --root . --apply   # write

Requires the first pass (TRANSLATION_FILTERS_2026_09_27) in text_filters.py.
All anchors must match exactly once before anything is written; each file is
backed up as <name>.bak_tf2_20260927; line endings are preserved.
dashboard.py only takes effect after a dashboard restart.
"""
import argparse, py_compile, shutil, sys
from pathlib import Path

MARK = "TRANSLATION_FILTERS2_2026_09_27"
PREREQ = ("scripts/text_filters.py", "TRANSLATION_FILTERS_2026_09_27")
EDITS = [
  ('scripts/text_filters.py', [
    ('lacuna tokens are marks, not refusals',
     '    if not t:\n        return -1\n    if lang == "hi" and _bare_token_hi(t):\n        return 0\n    low = t.lower()\n    cut = -1\n',
     '    if not t:\n        return -1\n    if lang == "hi" and _bare_token_hi(t):\n        return 0\n    # TRANSLATION_FILTERS2_2026_09_27. The prompt\'s hard-fail token INSIDE a\n    # translation is a lacuna mark, not a refusal. Measured on the live\n    # corpus: Shatapatha p131.2 and p251.3 came back as full, faithful\n    # translations with one "[ILLEGIBLE]" where a word is damaged, and the\n    # old test emptied both because "illegible" is a refusal phrase. An output\n    # that is ONLY the token (and punctuation) is still empty; everywhere else\n    # the token is masked, length-preserving, before the phrase scan.\n    if _bare_lacuna(t):\n        return 0\n    t = _LACUNA_RE.sub(lambda m: " " * len(m.group(0)), t)\n    low = t.lower()\n    cut = -1\n'),
    ('lacuna helpers',
     'def _refusal_cut(t: str, lang: str = "en", caveats: bool = True) -> int:',
     '_LACUNA_RE = re.compile(r"\\[\\s*(?:illegible|\\u0905\\u0938\\u094d\\u092a\\u0937\\u094d\\u091f)\\s*\\]", re.I)\n\n\ndef _bare_lacuna(t: str) -> bool:\n    """True when t is nothing but lacuna token(s) - [ILLEGIBLE] / [asphuta] -\n    and punctuation. (TRANSLATION_FILTERS2_2026_09_27)"""\n    rest = _LACUNA_RE.sub(" ", t).strip()\n    return rest != t.strip() and (not rest or bool(ONLY_PUNCT_RE.match(rest)))\n\n\ndef _refusal_cut(t: str, lang: str = "en", caveats: bool = True) -> int:'),
  ]),
  ('scripts/infer_mt.py', [
    ('prompt versions',
     '    "en": "v2-2026-07-20",\n    "hi": "hi-v2-2026-09-27",   # TRANSLATION_FILTERS_2026_09_27: rule 7\n',
     '    "en": "v3-2026-09-27",      # TRANSLATION_FILTERS2_2026_09_27: rule 12\n    "hi": "hi-v3-2026-09-27",   # _2026_09_27 rule 7; FILTERS2: rule 10\n'),
    ('en rule 12',
     '12. OUTPUT: Produce ONLY the English translation \u2014 no preamble, no "Translation:", no meta-commentary. If the text is illegible OCR noise, output exactly: [ILLEGIBLE]"""',
     '12. OUTPUT: Produce ONLY the English translation \u2014 no preamble, no "Translation:", no meta-commentary. Output exactly [ILLEGIBLE] ONLY when no part of the text can be read. If some words are damaged, translate everything that can be read and write [ILLEGIBLE] only where the unreadable words stand \u2014 never withhold a readable passage because part of it is damaged."""'),
    ('hi rule 10',
     '10. \u0928\u093f\u0930\u094d\u0917\u092e: \u0915\u0947\u0935\u0932 \u0939\u093f\u0928\u094d\u0926\u0940 \u0905\u0928\u0941\u0935\u093e\u0926 \u0926\u0947\u0902 \u2014 \u0915\u094b\u0908 \u092d\u0942\u092e\u093f\u0915\u093e, "\u0905\u0928\u0941\u0935\u093e\u0926:" \u0936\u0940\u0930\u094d\u0937\u0915 \u092f\u093e \u091f\u093f\u092a\u094d\u092a\u0923\u0940 \u0928\u0939\u0940\u0902\u0964 \u092f\u0926\u093f \u092a\u093e\u0920 \u0905\u092a\u0920\u0928\u0940\u092f OCR \u0915\u094b\u0932\u093e\u0939\u0932 \u0939\u0948 \u0924\u094b \u0920\u0940\u0915 \u092f\u0939\u0940 \u0932\u093f\u0916\u0947\u0902: [\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"""',
     '10. \u0928\u093f\u0930\u094d\u0917\u092e: \u0915\u0947\u0935\u0932 \u0939\u093f\u0928\u094d\u0926\u0940 \u0905\u0928\u0941\u0935\u093e\u0926 \u0926\u0947\u0902 \u2014 \u0915\u094b\u0908 \u092d\u0942\u092e\u093f\u0915\u093e, "\u0905\u0928\u0941\u0935\u093e\u0926:" \u0936\u0940\u0930\u094d\u0937\u0915 \u092f\u093e \u091f\u093f\u092a\u094d\u092a\u0923\u0940 \u0928\u0939\u0940\u0902\u0964 \u0915\u0947\u0935\u0932 [\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0924\u092d\u0940 \u0932\u093f\u0916\u0947\u0902 \u091c\u092c \u092a\u093e\u0920 \u0915\u093e \u0915\u094b\u0908 \u092d\u0940 \u0905\u0902\u0936 \u092a\u0922\u093c\u093e \u0928 \u091c\u093e \u0938\u0915\u0947\u0964 \u092f\u0926\u093f \u0915\u0941\u091b \u0936\u092c\u094d\u0926 \u0915\u094d\u0937\u0924\u093f\u0917\u094d\u0930\u0938\u094d\u0924 \u0939\u094b\u0902, \u0924\u094b \u091c\u094b \u092a\u0922\u093c\u093e \u091c\u093e \u0938\u0915\u0924\u093e \u0939\u0948 \u0909\u0938 \u0938\u092c\u0915\u093e \u0905\u0928\u0941\u0935\u093e\u0926 \u0915\u0930\u0947\u0902 \u0914\u0930 [\u0905\u0938\u094d\u092a\u0937\u094d\u091f] \u0915\u0947\u0935\u0932 \u0935\u0939\u0940\u0902 \u0932\u093f\u0916\u0947\u0902 \u091c\u0939\u093e\u0901 \u0905\u092a\u0920\u0928\u0940\u092f \u0936\u092c\u094d\u0926 \u0939\u0948\u0902 \u2014 \u0906\u0902\u0936\u093f\u0915 \u0915\u094d\u0937\u0924\u093f \u0915\u0947 \u0915\u093e\u0930\u0923 \u092a\u0920\u0928\u0940\u092f \u0905\u0902\u0936 \u0915\u093e \u0905\u0928\u0941\u0935\u093e\u0926 \u0915\u092d\u0940 \u0928 \u091b\u094b\u0921\u093c\u0947\u0902\u0964"""'),
  ]),
  ('scripts/translate_passages.py', [
    ('--lang help states the decision',
     '                    help="Target language. \'en\' (default) writes passages."\n                         "translation as always. \'hi\' (Phase HI) translates "\n                         "Sanskrit\u2192Hindi, anchored by the verified English, and "\n                         "writes translations_l10n \u2014 only for passages whose "\n                         "English exists and passed QA (>= --anchor-min-qa).")\n',
     '                    help="Target language. \'en\' (default) writes passages."\n                         "translation as always. \'hi\' (Phase HI) translates "\n                         "Sanskrit->Hindi DIRECTLY and writes translations_l10n; "\n                         "a QA-passed English, when one exists, is passed only as "\n                         "a meaning reference. Decision 2026-09-27 "\n                         "(TRANSLATION_FILTERS2_2026_09_27): direct sa->hi for "\n                         "fidelity; --require-anchor restores English gating.")\n'),
  ]),
  ('scripts/dashboard.py', [
    ('until_page for retries',
     '    lang    = (data.get("lang") or "en").strip()   # Phase HI (\'both\' => EN then HI)\n',
     '    lang    = (data.get("lang") or "en").strip()   # Phase HI (\'both\' => EN then HI)\n    # TRANSLATION_FILTERS2_2026_09_27: optional page window, so a retry of the\n    # verses a run already went past does not also start the untranslated rest.\n    _win = []\n    for _k, _flag in (("since_page", "--since-page"), ("until_page", "--until-page")):\n        try:\n            _v = int(data.get(_k) or 0)\n        except (TypeError, ValueError):\n            _v = 0\n        if _v > 0:\n            _win += [_flag, str(_v)]\n'),
    ('window passed to the single-language run',
     '             "--sleep", sleep, "--limit", limit, "--context", context,\n             "--min-quality", min_quality)\n    kind = "translate"\n',
     '             "--sleep", sleep, "--limit", limit, "--context", context,\n             "--min-quality", min_quality) + _win\n    kind = "translate"\n'),
    ('variant carries its output mode',
     '        v = {"mode": m, "slug": slug, "label": BOOKSMITH_MODE_LABEL[m],\n             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}\n',
     '        v = {"mode": m, "slug": slug, "label": BOOKSMITH_MODE_LABEL[m],\n             "ui": f"{BOOKSMITH_UI}/projects/{slug}"}\n        # TRANSLATION_FILTERS2_2026_09_27: say what the PDF is. booksmith_build\n        # makes every project it creates an AUDIT proof ("not a textual\n        # release"); only policy.output_mode \'reading\' passes the reading gate.\n        try:\n            _om = re.search(r"^\\s*output_mode:\\s*([a-z_]+)",\n                            (project / "book.yaml").read_text(encoding="utf-8", errors="replace"),\n                            re.M)\n            v["output_mode"] = _om.group(1) if _om else "reading"\n        except OSError:\n            v["output_mode"] = None\n'),
    ('Library link names audit proofs',
     "      var what=(v.pdf.kind==='book')?'PDF':'layout proof';\n",
     "      var what=(v.pdf.kind!=='book')?'layout proof':(v.output_mode==='audit'?'audit proof PDF':'PDF');\n"),
  ]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1] not in pre.read_text(encoding="utf-8"):
        print("REFUSED: the first pass (%s) is not in %s." % (PREREQ[1], PREREQ[0]))
        return 2
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
                bad += 1; continue
            new = new.replace(old, rep, 1)
            print("  ok       %s :: %s" % (rel, name))
        if MARK not in new:
            print("  ANCHOR   %s :: marker not present after edits" % rel); bad += 1
        plan.append((p, crlf, new))
    if bad:
        print("REFUSED: %d problem(s); nothing written." % bad); return 2
    if not plan:
        print("nothing to do - every file already patched."); return 0
    if not a.apply:
        print("CHECK PASSED for %d file(s). Re-run with --apply to write." % len(plan)); return 0
    for p, crlf, new in plan:
        bak = p.with_name(p.name + ".bak_tf2_20260927")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
        py_compile.compile(str(p), doraise=True)
        print("  WROTE    %s  (backup %s)" % (p.name, bak.name))
    print("APPLIED. To undo: copy each .bak_tf2_20260927 back over its file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
