#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_vignettes_2026_10_05.py  (2026-10-05)  VIGNETTES_2026_10_05

export_html --images approved: an APPROVED story from scripts/stories.py that is
linked to a placed image is printed under it (the Sanskrit line it quotes, the
English and, in Hindi editions, the Hindi retelling, citations as superscripts,
and a line saying it was drafted by a model and approved by an editor).

Byte-identical output when there is no doc_stories table or no approved story,
and for every export without --images approved (nothing else is touched).
All-or-nothing, marker-idempotent, backup .bak_vign_<date>, py_compile.

  python scripts/patch_vignettes_2026_10_05.py --check
  python scripts/patch_vignettes_2026_10_05.py
Test: python -m unittest tests.test_vignettes_2026_10_05 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "VIGNETTES_2026_10_05"

EX_EDITS = [
    ("attach stories",
     "    return out\n\n\ndef _fig_copy(figs):\n",
     '''    _attach_stories(con, out)   # VIGNETTES_2026_10_05
    return out


def _attach_stories(con, figs):
    """VIGNETTES_2026_10_05: an APPROVED story (scripts/stories.py) linked to an image placed
    here is printed under that image. No doc_stories table, or no approved story: no change."""
    if not figs or "doc_stories" not in _tables(con):
        return
    ids = [fg["id"] for v in figs.values() for fg in v]
    got = {}
    for iid, en, hi, q, qr in con.execute(
            "SELECT image_id, story_en, story_hi, quote_sa, quote_ref FROM doc_stories "
            "WHERE status = 'approved' AND image_id IN (%s) ORDER BY approved_at" % ",".join("?" * len(ids)), ids):
        got[iid] = {"en": en or "", "hi": hi or "", "q": q or "", "qr": qr or ""}
    for v in figs.values():
        for fg in v:
            if fg["id"] in got:
                fg["story"] = got[fg["id"]]


def _story_html(st, include_en, include_hi):
    """VIGNETTES_2026_10_05: the retelling under a plate, citations as superscripts."""
    if not st:
        return ""
    import re as _re
    def _cite(t):
        return _re.sub(r"\\[([^\\]]*\\d+\\.\\d+[^\\]]*)\\]", r"<sup class='cite'>[\\1]</sup>", html.escape(t))
    parts = []
    if st.get("q"):
        parts.append("<div class='plate-story-sa'>%s <span class='plate-label'>[%s]</span></div>"
                     % (html.escape(st["q"]), html.escape(st.get("qr") or "")))
    if include_en and st.get("en"):
        parts.append("<div>%s</div>" % _cite(st["en"]))
    if include_hi and st.get("hi"):
        parts.append("<div class='plate-hi'>%s</div>" % _cite(st["hi"]))
    if not parts:
        return ""
    return ("<div class='plate-story' style='text-align:left;font-size:.92em;max-width:40rem;margin:.6rem auto'>%s"
            "<div class='plate-label'>Retold from the passages cited; drafted by a model, approved by an editor."
            "</div></div>" % "".join(parts))


def _fig_copy(figs):
''', 1),
    ("story under the plate",
     '''    return ("<figure class='plate' id='img-%s' data-kind='%s'><img src='%s' alt='%s'/>"
            "<figcaption>%s</figcaption></figure>"
            % (fg["id"], html.escape(fg["kind"], quote=True), fg["uri"], alt, " ".join(cap)))
''',
     '''    _st = _story_html(fg.get("story"), include_en, include_hi)   # VIGNETTES_2026_10_05
    return ("<figure class='plate' id='img-%s' data-kind='%s'><img src='%s' alt='%s'/>"
            "<figcaption>%s</figcaption>%s</figure>"
            % (fg["id"], html.escape(fg["kind"], quote=True), fg["uri"], alt, " ".join(cap), _st))
''', 1),
]

TARGETS = [(Path("scripts/export_html.py"), EX_EDITS)]


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
        t = p.with_name(p.name + ".tmp_vign")
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
        shutil.copy2(p, p.with_name(p.name + ".bak_vign_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    print("Effective at the next export. scripts/stories.py is a new file beside this patch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
