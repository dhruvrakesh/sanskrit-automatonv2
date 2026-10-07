#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_verify_names_2026_10_07.py  (2026-10-07)  VERIFY_NAMES_2026_10_07

After the bulk re-check (STORY_RECHECK) five markandeya_purana stories still failed.
Each was read against its own passages (backup context_pre_heal_20261007_143003.db,
read-only). Three of the five failures were the check's own mistakes:

  #6  "went to Mount Meru [29.9 ...]"  ->  "names not found: Mount".
      "Mount" is an English title word, not a name the passages must give (29.9 says
      "the peak of meru"). Fixed: a short list of English title words is not a name.
  #11 'Tormented by grief, he cried, "Alas! This is Saivya, and this is that boy," and
      fell into a swoon. [60.10]'  ->  "1 sentence without a citation".
      The splitter cut inside the quotation after "Alas!". Fixed: for the citation
      check only, a fragment that ends inside a quotation is joined to the next one
      (at most 4), so the citation after the closing quote covers the sentence.
  #3  "the Apsara Vapuh"  ->  "names not found: Vapuh" (PowerShell showed "Vapu?").
      10.3 gives the name in another case, "vapum apsarasam". Fixed: a name ending in a
      visarga is also looked for as its stem at the start of a word.
      NOTE: #3 then passes the check, but it has a real error the check cannot see: it
      makes Vapu the rakshasa's widow, while 10.2-10.3 say the widow (Menaka's daughter)
      bore Kandhara a daughter, Taci, who was the apsaras Vapu under a sage's curse.
      Edit before approving.

Unchanged, because they are real:
  #5  "Draupadi": 25.8 says "that one daughter of Drupada"; the passages never give the
      name. Edit the name, or "Approve anyway" with a note.
  #10 8 of 9 sentences carry no citation (one list of 6+ tags at the end). Rewrite.

scripts/stories.py: NAME_STOP gains English title words; helpers _cite_units and
_name_in; verify() uses them. Hindi and the length / quotation / outside checks are
untouched. No API. All-or-nothing, marker-idempotent, backup .bak_vnames_<date>,
py_compile.
  python scripts\\patch_verify_names_2026_10_07.py --check
  python scripts\\patch_verify_names_2026_10_07.py
Then: python scripts\\stories.py verify-all --doc markandeya_purana
Test: python -m unittest tests.test_verify_names_2026_10_07 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "VERIFY_NAMES_2026_10_07"

BLOCK = r'''# ------------------------------------------------------------------ VERIFY_NAMES_2026_10_07
# Three false failures found by re-checking markandeya_purana on 2026-10-07, each read against its
# passages: "Mount Meru" ("Mount" is a title word), 'he cried, "Alas! This is ..." [60.10]' (the
# splitter cut inside the quotation), "Vapuh" (10.3 gives the name inflected, "vapum apsarasam").
# Real problems still fail: a name the passages do not give, a sentence with no citation.
NAME_STOP |= {"mount", "mountain", "river", "lake", "forest", "ocean", "sea", "queen", "prince",
              "princess", "goddess", "lady", "mother", "father"}


def _open_quote(s: str) -> bool:
    """True when a text ends inside a quotation: an odd number of straight double quotes, or more
    opening than closing curly ones. Single quotes are left alone (they are mostly apostrophes)."""
    return s.count("\"") % 2 == 1 or s.count("\u201c") > s.count("\u201d")


def _cite_units(en: str, join_max: int = 4) -> list:
    """Sentences for the citation check. A fragment that ends inside a quotation is joined to the
    next (at most join_max fragments), so the citation after the closing quote covers the sentence."""
    out, buf, n = [], "", 0
    for f in SENT_RE.split((en or "").strip()):
        buf, n = ((buf + " " + f) if buf else f), n + 1
        if not _open_quote(buf) or n >= join_max:
            out.append(buf); buf, n = "", 0
    if buf:
        out.append(buf)
    return out


def _name_in(t: str, src: str) -> bool:
    """A name is supported when the folded cited passages contain it. A name ending in a visarga
    (the nominative ending) may stand in another case there, so its stem is looked for at the start
    of a word ("Vapu\u1e25" -> "vapu" in "vapumapsaras\u0101\u1e43")."""
    f = _fold(t)
    if f in src:
        return True
    if t.endswith("\u1e25") and len(f) >= 4:
        return re.search(r"(?<![a-z])" + re.escape(f[:-1]), src) is not None
    return False


'''

EDITS = [
    ("helpers", "# ------------------------------------------------------------------ verify (no API)\n",
     BLOCK + "# ------------------------------------------------------------------ verify (no API)\n", 1),
    ("citation units",
     "    uncited = [s for s in SENT_RE.split(en.strip()) if len(WORD_RE.findall(s)) >= 4 and not BRACKET_RE.search(s)]\n",
     "    uncited = [s for s in _cite_units(en) if len(WORD_RE.findall(s)) >= 4 and not BRACKET_RE.search(s)]"
     "   # VERIFY_NAMES_2026_10_07\n", 1),
    ("name match",
     "            if is_name and len(t2) > 2 and t2.lower() not in NAME_STOP and _fold(t2) not in src:\n",
     "            if is_name and len(t2) > 2 and t2.lower() not in NAME_STOP and not _name_in(t2, src):"
     "   # VERIFY_NAMES_2026_10_07\n", 1),
]
TARGETS = [(Path("scripts/stories.py"), EDITS)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), e) for p, e in TARGETS]
    if all(MARK in s for _, s, _, _ in loaded):
        print("Already patched (%s). Nothing to do." % MARK); return 0
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
        print("CHECK OK: %d anchored edits in %d files. Nothing written." % (sum(len(e) for _, e in TARGETS), len(TARGETS)))
        return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_vnames")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_vnames_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
