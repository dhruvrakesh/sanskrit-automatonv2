#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_stories_ui_2026_10_05.py  (2026-10-05)  STORIES_UI_2026_10_05

Wires the Stories page (scripts/stories_web.py + scripts/stories_static.html, new
files beside this patch) into the dashboard, and firms up two things in
scripts/stories.py found on the first real run (markandeya_purana, stories #1-#4):

  dashboard.py         registers /stories after the Shelf, inside try/except, so a
                       fault in the Stories module cannot stop the dashboard.
  dashboard_static.html  a "Stories" link in the header, before Shelf.
  stories.py  verify   a citation written AFTER the full stop ("... fled. [11.5] Later,
                       he ...") no longer glues two sentences together, so the first
                       word of the next sentence ("Later", "Simultaneously", "Enraged",
                       "Despite") is no longer reported as an unknown name; nor is a
                       capitalised word that opens quoted speech or follows a colon.
                       Names are still checked everywhere else (IAST words always).
  stories.py  prompt   rule (6): a translated detail that makes no sense in the
                       narrative (story #1's "ash-buffalo") is left out and noted,
                       not retold. The prompt hash stored per story changes with it.

No schema change, no API call, no change to stories already written (re-run
"Check again" or `stories.py verify --id N` to re-check them).
All-or-nothing, marker-idempotent, backup .bak_stui_<date>, py_compile.

  python scripts\\patch_stories_ui_2026_10_05.py --check
  python scripts\\patch_stories_ui_2026_10_05.py
Test: python -m unittest tests.test_stories_ui_2026_10_05 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "STORIES_UI_2026_10_05"

DASH_EDITS = [
    ("register the Stories page",
     '''except Exception as _shelf_err:
    print(f"[shelf] Shelf not loaded: {type(_shelf_err).__name__}: {_shelf_err}")
''',
     '''except Exception as _shelf_err:
    print(f"[shelf] Shelf not loaded: {type(_shelf_err).__name__}: {_shelf_err}")

# STORIES_UI_2026_10_05: the Stories page (/stories) - see scripts/stories_web.py. Guarded like the Shelf.
try:
    import stories_web as _stories_web
    _stories_web.register(app, launch=launch, root=ROOT, py=py, script=script)
except Exception as _stories_err:
    print(f"[stories] Stories page not loaded: {type(_stories_err).__name__}: {_stories_err}")
''', 1),
]

HTML_EDITS = [
    ("Stories link",
     '''    <a href="/shelf" title="Shelf:''',
     '''    <a href="/stories" title="Stories: cited retellings beside the images, for the anthology (STORIES_UI_2026_10_05)" style="color:var(--gold);text-decoration:none;font-size:13px;margin-right:12px">&#x1F4DC; Stories</a>
    <a href="/shelf" title="Shelf:''', 1),
]

ST_EDITS = [
    ("sentence split after a citation",
     r'''SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c%s])" % IAST)
''',
     r'''# STORIES_UI_2026_10_05: also split after a citation that follows the full stop ("fled. [11.5] Later ...").
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c%s])|(?<=\])\s+(?=[A-Z\"'\u201c%s])" % (IAST, IAST))
OPENERS = "\"'\u201c\u2018:;(\u2014"   # a capital after these starts speech or a clause, not a name
''', 1),
    ("names: sentence and speech openers",
     r'''        toks = WORD_RE.findall(s)
        for k, t in enumerate(toks):
            t2 = t.strip("'\u2019").removesuffix("'s").removesuffix("\u2019s")
            is_name = any(c in IAST for c in t2) or (k > 0 and t2[:1].isupper())
''',
     r'''        for k, mt in enumerate(WORD_RE.finditer(s)):   # STORIES_UI_2026_10_05
            t = mt.group(0)
            t2 = t.strip("'\u2019").removesuffix("'s").removesuffix("\u2019s")
            lead = s[:mt.start()].rstrip()[-1:]
            opens = k == 0 or (lead != "" and lead in OPENERS)
            is_name = any(c in IAST for c in t2) or (not opens and t2[:1].isupper())
''', 1),
    ("prompt rule 6",
     '''    "tag in quote_ref. Choose a line whose printed text looks sound. "
''',
     '''    "tag in quote_ref. Choose a line whose printed text looks sound. "
    "(6) If a translated detail makes no sense in the story (an animal, object or act that does not belong, "
    "which usually means the translation or the OCR is wrong there), leave it out of story_en and story_hi "
    "and describe it in 'notes' with its tag. "   # STORIES_UI_2026_10_05
''', 1),
]

TARGETS = [(Path("scripts/dashboard.py"), DASH_EDITS),
           (Path("scripts/dashboard_static.html"), HTML_EDITS),
           (Path("scripts/stories.py"), ST_EDITS)]
NEW_FILES = [Path("scripts/stories_web.py"), Path("scripts/stories_static.html")]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    missing = [str(p) for p in NEW_FILES if not p.exists()]
    if missing:
        print("FAIL: copy these new files into scripts\\ first: " + ", ".join(missing)); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    marks = [MARK in s for _, s, _, _ in loaded]
    if all(marks):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marks):
        print("REFUSING: marker in some files only - inspect by hand:")
        for (p, _s, _n, _e), m in zip(loaded, marks):
            print("  %-32s %s" % (p, "patched" if m else "not patched"))
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
    for p in NEW_FILES:
        if p.suffix == ".py":
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                print("REFUSING: %s does not compile:\n%s" % (p, e)); return 1
    if args.check:
        print("CHECK OK: %d anchored edits in %d files; new files present. Nothing written."
              % (sum(len(e) for _, e in TARGETS), len(TARGETS))); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_stui")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        if p.suffix == ".py":
            try:
                py_compile.compile(str(t), doraise=True)
            except py_compile.PyCompileError as e:
                for x, _ in tmps + [(t, p)]:
                    x.unlink(missing_ok=True)
                print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_stui_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Restart the dashboard when no job is running; then open http://127.0.0.1:5057/stories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
