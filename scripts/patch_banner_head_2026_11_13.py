#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_banner_head_2026_11_13.py  (2026-11-13)  BANNER_HEAD_2026_11_13 (with DESK_SCHOLAR_NEXT_2026_11_13)

1. BANNER_HEAD (scripts/text_filters.py). The Maharishi University of Management's Vedic Literature Collection prints a
   running head on every page ("MAHARISHI UNIVERSITY OF MANAGEMENT / VEDIC LITERATURE COLLECTION", with the work's name
   in Latin and Devanagari), and the segmenter puts it at the front of the page's first passage. looks_like_frontmatter()
   finds "vedic literature" in the passage and calls all of it front matter, so should_translate() said no: the first
   verses of every page of those editions were never translated, in English or Hindi. On the backup of 13 Nov: 1,924
   passages of 21 texts become translatable, 1,745 of them untranslated (the Gandharva Veda 501, its English stopped at
   379 of 884; the Taittiriya 444; the Sukla Yajurveda 280; the Samaveda 241; the smrtis, dhanurvedas and siksas the rest), counted as debris by their charts.
   strip_banner_head() takes such a head off the front of a passage (whole leading lines, only when one names the
   publisher, only when Sanskrit is left); should_translate() and clean_for_mt() use it. Nothing else changes: a banner
   alone, or inside a passage, is front matter as before.
2. DESK_SCHOLAR_NEXT (scripts/translation_desk.py, scripts/dashboard.py). Asked on 13 Nov: "why dont we have prose type
   scholarly editions for mallapurana or a ui/ux locally to get to one?" The desk called a text whose working English
   is done "nothing to do". Now its next step says that its scholarly English (the edition, also read as prose) is not
   begun, with its verses and the measured price, and its page begins with a press of 250 verses (under the $12 a press).

3. tests/test_leak_guard_2026_10_19.py: its replay compares with the copy from before this patch.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_bannerhead_<date> copies.

  python scripts\\patch_banner_head_2026_11_13.py --check
  python scripts\\patch_banner_head_2026_11_13.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'BANNER_HEAD_2026_11_13'
TAG = 'bannerhead'
FILES = ['scripts/text_filters.py', 'scripts/translation_desk.py', 'scripts/dashboard.py', 'tests/test_leak_guard_2026_10_19.py']
NEEDS = {'scripts/text_filters.py': 'PAGE_FURNITURE_2026_09_06', 'scripts/translation_desk.py': 'DESK_FRESH_2026_11_11', 'scripts/dashboard.py': 'DESK_FRESH_2026_11_11'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/text_filters.py', 1, '\n\ndef should_translate(s: str, *, min_dev: float = 0.05) -> bool:\n    """Return True if this passage contains enough Sanskrit to warrant translation.',
     '\n\n# BANNER_HEAD_2026_11_13: a page\'s running head that names its publisher. The editions of the Maharishi University of\n# Management\'s Vedic Literature Collection (the Gandharva Veda, the Yajur and Sama Vedas, the smrtis, the dhanurvedas,\n# the siksas) print on every page a head such as "[Gandharva Veda] / (the name in Devanagari) / GANDHARVA VEDA /\n# MAHARISHI UNIVERSITY OF MANAGEMENT / VEDIC LITERATURE COLLECTION", and the segmenter puts it at the front of the\n# page\'s first passage, before that page\'s verses. looks_like_frontmatter() finds "vedic literature" anywhere in a\n# passage and calls all of it front matter, so should_translate() said no and the translators passed over each page\'s\n# first verses without a word. On the backup of 13 Nov: 1,924 passages of 21 texts, 1,745 of them untranslated: 501\n# the Gandharva Veda\'s (its English stopped at 379 of 884), 444 the Taittiriya\'s, 280 the Sukla Yajurveda\'s, 241 the Samaveda\'s; their\n# charts counted them as debris (the Gandharva 57%). strip_banner_head() takes such a head off the front of a passage:\n# whole leading lines only, and only when one of them is a publisher\'s banner; the rest is judged and translated as any\n# passage. A passage that is nothing but the banner, or has no Sanskrit after it, is left as it was (front matter).\n_BH_STOP = re.compile(r"[\u0964\u0965\u0966-\u096f0-9]")\n_BH_HEADING = re.compile(r"(?:\\u0927\\u094d\\u092f\\u093e\\u092f|\\u0907\\u0924\\u093f|\\u0938\\u0930\\u094d\\u0917|\\u092a\\u091f\\u0932|\\u0915\\u093e\\u0923\\u094d\\u0921|\\u092e\\u0923\\u094d\\u0921\\u0932|\\u0905\\u0928\\u0941\\u0935\\u093e\\u0915|\\u0916\\u0923\\u094d\\u0921|\\u092a\\u094d\\u0930\\u092a\\u093e\\u0920\\u0915)")\n_BH_ATHA = re.compile(r"^\u0905\u0925(?:\\s|$)")\n\n\ndef _bh_banner(t: str) -> bool:\n    """A line that names the publisher (_PUBLISHER_BANNERS) and is not Sanskrit."""\n    low = t.lower()\n    return len(t) <= 90 and frac_devanagari(t) < 0.05 and any(sig in low for sig in _PUBLISHER_BANNERS)\n\n\ndef _bh_title(t: str, banner_seen: bool) -> bool:\n    """A line of a running head: a Latin title in brackets or in capitals ("[Gandharva Veda]", "GANDHARVA VEDA",\n    "MAHARISHI UNIVERSITY OF MANAGEMENT"), or the work\'s name in Devanagari: one word (two once the banner is seen), no\n    danda, no numeral, no word of a chapter\'s heading (dhyaya as in adhyaya, iti, sarga, patala, kanda, mandala, anuvaka, khanda,\n    prapathaka) and not beginning with atha."""\n    if len(t) > 40:\n        return False\n    if frac_devanagari(t) < 0.05:\n        letters = [c for c in t if c.isalpha()]\n        return bool(letters) and ((t.startswith("[") and t.endswith("]")) or not any(c.islower() for c in letters))\n    if frac_devanagari(t) < 0.5 or _BH_STOP.search(t) or _BH_HEADING.search(t) or _BH_ATHA.search(t):\n        return False\n    return len(t.split()) <= (2 if banner_seen else 1)\n\n\ndef strip_banner_head(s: str, max_lines: int = 10) -> str:\n    """BANNER_HEAD_2026_11_13: the passage without a publisher\'s running head at its front, or the passage as it was.\n\n    Only whole leading lines go, at most max_lines, and never the last line; only when one of them names the publisher;\n    and only when Sanskrit is left after them."""\n    if not s:\n        return s\n    lines = s.split("\\n")\n    n, banner = 0, False\n    while n < min(max_lines, len(lines) - 1):\n        t = lines[n].strip()\n        if t and _bh_banner(t):\n            banner = True\n        elif t and not _bh_title(t, banner):\n            break\n        n += 1\n    if not banner:\n        return s\n    t = lines[n].strip() if n < len(lines) else ""\n    if n >= max_lines and t and (_bh_banner(t) or _bh_title(t, banner)):\n        return s   # a head longer than max_lines: not taken apart\n    rest = "\\n".join(lines[n:]).strip()\n    return rest if rest and has_any_devanagari(rest) else s\n\n\ndef should_translate(s: str, *, min_dev: float = 0.05) -> bool:\n    """Return True if this passage contains enough Sanskrit to warrant translation.')

edit('scripts/text_filters.py', 2, '    Lowered default min_dev from 0.08 \u2192 0.05 to catch mixed Sanskrit-English commentary.\n    """\n    if is_noise(s): return False\n    if looks_like_heading(s): return False',
     '    Lowered default min_dev from 0.08 \u2192 0.05 to catch mixed Sanskrit-English commentary.\n    """\n    s = strip_banner_head(s)   # BANNER_HEAD_2026_11_13: a publisher\'s running head is not the passage\n    if is_noise(s): return False\n    if looks_like_heading(s): return False')

edit('scripts/text_filters.py', 3, '    # and cannot see a running head like "(\u096e\u0968) \u0936\u0924\u092a\u0925\u092c\u094d\u0930\u093e\u0939\u094d\u092e\u0923\u092e\u094d \u0964 [ \u0967\u096a \u0915\u093e\u0966 ]".\n    # (PAGE_FURNITURE_2026_09_06)\n    s = strip_page_furniture(s)\n    # Remove leading bullet/list markers',
     '    # and cannot see a running head like "(\u096e\u0968) \u0936\u0924\u092a\u0925\u092c\u094d\u0930\u093e\u0939\u094d\u092e\u0923\u092e\u094d \u0964 [ \u0967\u096a \u0915\u093e\u0966 ]".\n    # (PAGE_FURNITURE_2026_09_06)\n    s = strip_banner_head(s)   # BANNER_HEAD_2026_11_13: the publisher\'s running head, before the page\'s furniture\n    s = strip_page_furniture(s)\n    # Remove leading bullet/list markers')

edit('scripts/translation_desk.py', 1, 'MAX_VERSES = 400          # the most verses a press plans or runs\nMAX_USD = 12.0            # the most one press may spend (as the benchmarks\' buttons)\nTIER_R_ENGINE = "anthropic:claude-sonnet-5-5"   # TIER_R_2026_10_17: the working English, Sonnet in one pass\nTIER_R_PER_VERSE = 0.0052                        # $ a verse, BM1\'s measure (the Claude credit)',
     'MAX_VERSES = 400          # the most verses a press plans or runs\nMAX_USD = 12.0            # the most one press may spend (as the benchmarks\' buttons)\n# DESK_SCHOLAR_NEXT_2026_11_13 (patch BANNER_HEAD_2026_11_13): the scholarly English\'s price a verse as the meter has it (usage_log, kind scholar,\n# claude-sonnet-5-5, 15 to 21 Oct): the Markandeya witness $36.65 for 1,408 verses ($0.026), the Karanagama $42.19 for\n# 1,018 ($0.041), the Hayasirsa $62.11 for 1,431 ($0.043), the Surya $22.22 for 492 ($0.045). A plan (free) prices a\n# text from the measured rows; this is the desk\'s word before any plan. A press of SCHOLAR_PRESS verses stays under\n# MAX_USD at the dearer rate.\nSCHOLAR_PER_VERSE = (0.026, 0.045)\nSCHOLAR_PRESS = 250\nTIER_R_ENGINE = "anthropic:claude-sonnet-5-5"   # TIER_R_2026_10_17: the working English, Sonnet in one pass\nTIER_R_PER_VERSE = 0.0052                        # $ a verse, BM1\'s measure (the Claude credit)')

edit('scripts/translation_desk.py', 2, '        return ("the working English and its Hindi (one pass), about $%.2f by the path; or begin its scholarly English"\n                % float(prow.get("cost") or 0))\n    if stage in ("judged", "source", "done"):\n        return _first(prow) or ("nothing to do" if stage == "done" else "-")',
     '        return ("the working English and its Hindi (one pass), about $%.2f by the path; or begin its scholarly English"\n                % float(prow.get("cost") or 0))\n    if stage == "done" and not _first(prow) and int(mula or 0) > 0 and not int(cover.get("verses") or 0):\n        # DESK_SCHOLAR_NEXT_2026_11_13: asked on 13 Nov, "why dont we have prose type scholarly editions for mallapurana\n        # or a ui/ux locally to get to one?": a text whose working English is done was called "nothing to do", and the\n        # scholarly English (the edition, and the edition read as prose) was never offered from the list.\n        lo, hi = SCHOLAR_PER_VERSE\n        return ("the working English is done; its scholarly English (the edition, also read as prose) is not begun: "\n                "%d verses, about $%.0f to $%.0f; on its page, plan the first %d (free), then run them"\n                % (int(mula), int(mula) * lo, int(mula) * hi, min(SCHOLAR_PRESS, int(mula))))\n    if stage in ("judged", "source", "done"):\n        return _first(prow) or ("nothing to do" if stage == "done" else "-")')

edit('scripts/dashboard.py', 1, '                \'<button class="btn go dkbtn" id="dkrun" style="display:none" data-cap="0" onclick="deskStep(\\\'%s\\\', \\\'run\\\', \'\n                \'this)">Run</button></div>%s\' % (\n                    td.STEP_VERSES, td.MAX_VERSES, e(r["doc"], quote=True), e(r["doc"], quote=True),\n                    \'<p class="small">In repair: run with --held-ok, as on 15 Oct (nothing is written to the site or to \'\n                    \'its passages; a row goes stale, not wrong, if the reading changes).</p>\' if held_ok else ""))',
     '                \'<button class="btn go dkbtn" id="dkrun" style="display:none" data-cap="0" onclick="deskStep(\\\'%s\\\', \\\'run\\\', \'\n                \'this)">Run</button></div>%s\' % (\n                    (td.STEP_VERSES if sc.get("verses") else getattr(td, "SCHOLAR_PRESS", td.STEP_VERSES)),   # DESK_SCHOLAR_NEXT_2026_11_13 (BANNER_HEAD_2026_11_13)\n                    td.MAX_VERSES, e(r["doc"], quote=True), e(r["doc"], quote=True),\n                    \'<p class="small">In repair: run with --held-ok, as on 15 Oct (nothing is written to the site or to \'\n                    \'its passages; a row goes stale, not wrong, if the reading changes).</p>\' if held_ok else ""))')

edit('tests/test_leak_guard_2026_10_19.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                self.assertEqual((t / f).read_bytes(), (REPO / f).read_bytes(), f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for f in self.FILES:\n                want = (REPO / f).read_bytes()\n                later = sorted((REPO / f).parent.glob(Path(f).name + ".bak_bannerhead_*"))   # BANNER_HEAD_2026_11_13 came after\n                if later and b"BANNER_HEAD_2026_11_13" in want:\n                    want = later[0].read_bytes()\n                self.assertEqual((t / f).read_bytes(), want, f)\n            self.assertIn("Nothing to do", subprocess.run(pat, cwd=td, capture_output=True, text=True).stdout)\n            for f in self.FILES:')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

