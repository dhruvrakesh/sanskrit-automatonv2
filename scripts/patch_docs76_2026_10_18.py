#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs76_2026_10_18.py  DOCS76_2026_10_18

Records 18 Oct (night): the scholarly English in the mirror and in Srangam's reader (SCHOLAR_MIRROR_2026_10_18,
C18_READER_SCHOLAR_2026_10_18, SCHOLAR_READER_2026_10_18); docs/SCHOLAR_READER_2026-10-18.md.

Appends to docs/PLATFORM_2026-10-04.md (section 79), RUNBOOK.md, docs/ENTERPRISE_PATH_2026-10-04.md (addendum 66)
and docs/STATE_2026-10-18.md (section 11), each needing DOCS75_2026_10_18. And:
  - configs/editions.json: adhyayas 19 to 31 on (judged on 18 Oct: 659 passed, 76 flagged, 4 doubted of 739), with a
    subtitle from their own first verses;
  - tests/test_publish_editions_2026_10_18.py: the editions on are the Devimahatmya and adhyayas 19 to 31;
  - configs/doc_titles.json: a title for markandeya_purana__w_gretil (GRETIL's own: Markandeyapurana 1-93), shown once
    it is adopted; applying this patch is the confirmation the file asks for. Left as it is if it has one already.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs76_<date>), line endings kept.

  python scripts\\patch_docs76_2026_10_18.py --check
  python scripts\\patch_docs76_2026_10_18.py
"""
from __future__ import annotations
import argparse, datetime, json, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "DOCS76_2026_10_18"

PLATFORM = """

## 79. The scholarly English in the mirror and in Srangam's reader (DOCS76_2026_10_18)

**18 Oct (night).** docs/SCHOLAR_READER_2026-10-18.md. Asked: why only one scholarly text on Srangam, when the mirror
is complete. The mirror (8 Oct) carried everything but the scholarly English (14 Oct), which only an edition took to
the site; and the two Markandeya texts in scholarly English are a GRETIL witness, local until adopted.
- **SCHOLAR_MIRROR_2026_10_18** (corpus_sync.py): two rows of corpus.translations a verse, en-x-scholar (the English,
  fidelity, fluency) and en-x-scholar-meta (status, flag, review, notes, doubts, range); the latest current version,
  not rejected. Nothing else re-sent; every site function still reads lang 'hi'.
- **C18_READER_SCHOLAR_2026_10_18** (docs/cloud/C18): corpus_reader_scholar (a reader page's rows) and
  corpus_reader_scholar_count, behind the reader's gate.
- **SCHOLAR_READER_2026_10_18** (the Srangam kit, docs/srangam/SCHOLAR_READER_2026-10-18/): /corpus/<doc> shows the
  scholarly English first, labelled with its standing and its notes; the working English folds under it; Phase AL.
- **The editions:** adhyayas 19 to 31 on (configs/editions.json).

**Tests:** test_scholar_mirror_2026_10_18 (8), test_reader_scholar_pg_2026_10_18 (4, with a PostgreSQL),
test_srangam_scholar_reader_kit_2026_10_18 (4), test_docs76_2026_10_18 (3); the site's reader-scholar.test.tsx (16).
"""

RUNBOOK = """

## The scholarly English in the reader (DOCS76_2026_10_18)

docs/SCHOLAR_READER_2026-10-18.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`,
`$S = "D:\\srangam-42267"`.
1. **The automaton:** `Set-Location $A`; `python scripts\\patch_scholar_mirror_2026_10_18.py --check`, then without
   --check; the same for `scripts\\patch_docs76_2026_10_18.py`; `python -m unittest tests.test_scholar_mirror_2026_10_18
   tests.test_corpus_sync_2026_10_08 tests.test_mirror_cap_2026_10_12 tests.test_publish_editions_2026_10_18
   tests.test_srangam_scholar_reader_kit_2026_10_18 tests.test_docs76_2026_10_18`; `python scripts\\corpus_sync.py` (the
   plan: the scholarly rows of MBh01 and the Tantrabhidhana); release.ps1 with COMMIT_MSG_scholarreader_20261018.txt.
2. **The site's SQL** (Lovable Cloud SQL editor): docs/cloud/C18_checks_2026-10-18.sql E1 and P1, one per paste; then
   `Get-Content -Raw -Encoding UTF8 "$A\\docs\\cloud\\C18_reader_scholar_2026-10-18.sql" | Set-Clipboard`, paste it whole,
   Run; then V1 and V2.
3. **Srangam:** `Set-Location $S`; `git pull --rebase --autostash`; `python
   "$A\\scripts\\patch_srangam_scholar_reader_2026_10_18.py" --check`, then without --check; `npm run typecheck`; `npx
   vitest run`; `npm run build`. Then the editions: `Set-Location $A`; `python scripts\\publish_editions.py`, then
   `--apply`. Then `Set-Location $S`; `git add --` the files the kit printed and `public/scholarly`; `git commit -F
   "$A\\docs\\srangam\\SCHOLAR_READER_2026-10-18\\COMMIT_MSG.txt"`; `git push`.
4. **The GRETIL Markandeya on the site (your decision):** `python scripts\\repair_text.py --doc
   markandeya_purana__w_gretil --release --force`; `python scripts\\corpus_sync.py` (the plan); the scheduled mirror
   sends it. Then E1 and E2 of the checks.
"""

EP = """

## Addendum 2026-10-18 (66) (DOCS76_2026_10_18)

| # | Item | State |
|---|---|---|
| X1b | The scholarly English in the reader | Built: SCHOLAR_MIRROR_2026_10_18, C18, SCHOLAR_READER_2026_10_18 |
| X1c | The scholarly English in search (words and meaning) | To build |
| X1d | The scholarly English in the published reader (/texts) | To build |
| E4 | Adhyayas 19 to 31 as an edition | On (configs/editions.json) |
| W1 | The GRETIL Markandeya adopted as a text of its own | Yours: repair_text.py --release --force |
"""

STATE = """

## 11. The night of 18 Oct (DOCS76_2026_10_18)

- **Why one scholarly text on Srangam:** the mirror carried everything but the scholarly English, which came six
  days after it; an edition is published only for a finished, judged text; and both Markandeya texts in scholarly
  English are a GRETIL witness, local until adopted. docs/SCHOLAR_READER_2026-10-18.md.
- **Built:** the scholarly English in the mirror (two rows a verse), the site's reader functions (C18) and the
  reader (Srangam kit, Phase AL); adhyayas 19 to 31 as an edition.
- **The scholarly layer:** the Devimahatmya 669 (632 passed, 37 flagged); adhyayas 19 to 31 739 (659, 76, 4
  doubted); the Hayasirsa 1,431 (held in repair); the Karanagama 1,018 (withdrawn); MBh01 24; the Tantrabhidhana 16;
  the Surya 20 of 515.
- **The screen's wrong meanings:** 181 of 4,591 (4%) after the Ganita's T2 (55 mended): the Markandeya 55, the Ganita
  45, the Mallapurana 45, the Sandilya 18.
- **Section 9's table** now reads to docs/cloud C18 and Srangam's RELIABILITY_AUDIT Phase AL.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM, "DOCS75_2026_10_18"),
           (Path("RUNBOOK.md"), RUNBOOK, "DOCS75_2026_10_18"),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP, "DOCS75_2026_10_18"),
           (Path("docs/STATE_2026-10-18.md"), STATE, "DOCS75_2026_10_18")]

EDITIONS = Path("configs/editions.json")
ED_NEEDS = "EDITIONS_SITE_2026_10_18"
ED_OLD = ('   "slug": "markandeya-purana-19-31",\n'
          '   "enabled": false,\n'
          '   "why_off": "482 of its 740 verses wait for the judge (scholar_translate.py --rejudge); turn it on after the '
          're-judge",\n'
          '   "doc": "markandeya_purana__w_gretil",\n'
          '   "pages": [81, 124],\n'
          '   "title": "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a, adhy\u0101yas 19 to 31",\n'
          '   "subtitle": "the Datt\u0101treya and Alarka chapters: the Sanskrit with a scholarly English and notes",\n')
ED_NEW = ('   "slug": "markandeya-purana-19-31",\n'
          '   "enabled": true,\n'
          '   "why_on": "DOCS76_2026_10_18: judged on 18 Oct (659 passed, 76 flagged, 4 doubted of 739)",\n'
          '   "doc": "markandeya_purana__w_gretil",\n'
          '   "pages": [81, 124],\n'
          '   "title": "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a, adhy\u0101yas 19 to 31",\n'
          '   "subtitle": "K\u0101rtav\u012brya and Datt\u0101treya; Kuvalay\u0101\u015bva and Mad\u0101las\u0101; '
          'Mad\u0101las\u0101\'s teaching of Alarka on the householder\'s duties and the \u015br\u0101ddha: the Sanskrit '
          'with a scholarly English and notes",\n')

TEST = Path("tests/test_publish_editions_2026_10_18.py")
TEST_NEEDS = "EDITIONS_SITE_2026_10_18"
TEST_OLD = ('            self.assertEqual([e["slug"] for e in c["editions"] if e.get("enabled", True)], ["devimahatmya"])\n')
TEST_NEW = ('            self.assertEqual([e["slug"] for e in c["editions"] if e.get("enabled", True)],\n'
            '                             ["devimahatmya", "markandeya-purana-19-31"])   # DOCS76_2026_10_18\n')

TITLES = Path("configs/doc_titles.json")
TITLE_CODE = "markandeya_purana__w_gretil"
TITLE = "M\u0101rka\u1e47\u1e0deya Pur\u0101\u1e47a (GRETIL e-text)"
TITLE_SOURCE = ("DOCS76_2026_10_18: GRETIL's own title of the file, M\u0101rka\u1e47\u1e0deyapur\u0101\u1e47a 1-93 "
                "(data entry by the Sansknet Project); confirmed by applying patch_docs76_2026_10_18.py on 18 Oct")


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def compiles(data: bytes) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        Path(tmp).write_bytes(data)
        py_compile.compile(tmp, doraise=True, cfile=tmp + "c")
        return ""
    except py_compile.PyCompileError as e:
        return str(e).splitlines()[-1] if str(e) else "does not compile"
    finally:
        for x in (tmp, tmp + "c"):
            try:
                os.remove(x)
            except OSError:
                pass


def edit_text(p: Path, needs: str, old: str, new: str, problems: list):
    """(path, data) for an anchored edit, None when it is already there."""
    if not p.exists():
        problems.append("%s not found" % p); return None
    raw = p.read_bytes()
    nl = nl_of(raw)
    src = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in src:
        print("skip %s (already carries %s)" % (p, MARK)); return None
    if needs not in src:
        problems.append("%s does not carry %s: this is not the file released" % (p, needs)); return None
    if src.count(old) != 1:
        problems.append("%s: its anchor is there %d times (want 1): it changed since; edit it by hand" % (p, src.count(old)))
        return None
    out = src.replace(old, new, 1).replace("\n", nl).encode("utf-8")
    if p.suffix == ".json":
        try:
            json.loads(out.decode("utf-8"))
        except ValueError as e:
            problems.append("%s would not be JSON: %s" % (p, e)); return None
    if p.suffix == ".py":
        if not all(x < 128 for x in out):
            problems.append("%s would not be ASCII" % p); return None
        err = compiles(out)
        if err:
            problems.append("%s would not compile: %s" % (p, err)); return None
    return (p, out)


def edit_titles(problems: list):
    if not TITLES.exists():
        problems.append("%s not found" % TITLES); return None
    raw = TITLES.read_bytes()
    try:
        d = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        problems.append("%s is not JSON: %s" % (TITLES, e)); return None
    if not isinstance(d, dict) or not isinstance(d.get("titles"), dict):
        problems.append("%s has no titles" % TITLES); return None
    if TITLE_CODE in d["titles"]:
        print("skip %s (%s has a title already: %s)" % (TITLES, TITLE_CODE, d["titles"][TITLE_CODE])); return None
    nl = nl_of(raw)
    if (json.dumps(d, indent=2, ensure_ascii=False) + "\n").replace("\n", nl).encode("utf-8") != raw:
        problems.append("%s is not laid out as json.dumps(indent=2) writes it: add the title in the Shelf instead" % TITLES)
        return None
    d.setdefault("_sources", {})[TITLE_CODE] = TITLE_SOURCE
    d["titles"][TITLE_CODE] = TITLE
    return (TITLES, (json.dumps(d, indent=2, ensure_ascii=False) + "\n").replace("\n", nl).encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for p, text, needs in TARGETS:
        if not p.exists():
            problems.append("%s not found" % p); continue
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        if needs.encode() not in raw:
            problems.append("%s has no %s section (apply it first)" % (p, needs)); continue
        nl = nl_of(raw)
        sep = b"" if raw.endswith(b"\n") else nl.encode()
        todo.append((p, raw + sep + text.replace("\n", nl).encode("utf-8")))
    for x in (edit_text(EDITIONS, ED_NEEDS, ED_OLD, ED_NEW, problems), edit_text(TEST, TEST_NEEDS, TEST_OLD, TEST_NEW, problems),
              edit_titles(problems)):
        if x:
            todo.append(x)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs76_" + stamp))
        t = p.with_name(p.name + ".tmp_docs76"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next:")
    print("  python -m unittest tests.test_docs76_2026_10_18 tests.test_publish_editions_2026_10_18")
    print("  python scripts\\publish_editions.py   (the plan: adhyayas 19 to 31 new)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
