#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs104_2026_11_10.py  (2026-11-10)  DOCS104_2026_11_10

The genealogies mended and explained; the epithets on the site (C26); B. C. Law made ready as private reading.
docs\\GENEALOGY_2026-11-10.md (new, beside this patch) says what was asked, found, built and measured. This patch adds:

  docs/ASKS_2026-10-22.md    section 17: each ask of 10 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 39
  RUNBOOK.md                 "10 Nov: the genealogies, C26 and B. C. Law": the commands in order
  scripts/docs_map.py        GENEALOGY and PEOPLES files under "Names, relations and genealogies"

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs104_<date> copies.

  python scripts\\patch_docs104_2026_11_10.py --check
  python scripts\\patch_docs104_2026_11_10.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS104_2026_11_10'
TAG = 'docs104'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'scripts/docs_map.py']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS103_2026_11_09', 'docs/STATE_2026-10-18.md': 'DOCS103_2026_11_09', 'RUNBOOK.md': 'DOCS103_2026_11_09', 'scripts/docs_map.py': 'DOCS98_2026_10_28'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| | In all | about $142 of the $200 |\n',
     '| | In all | about $142 of the $200 |\n\n## 17. 10 Nov: the genealogies mended and explained; B. C. Law made ready (DOCS104_2026_11_10)\n\nAsked on 10 Nov, with screenshots of Sorensen\'s Anga and Kaunteya: "such a genealogy front end does not make sense for\nanybody. at least explain what you are putting in graphs here. has to be an api call thing. we cant even get the\ngenealogy of Kaunteya (Arjun) right, not to say what will happen if we start looking for specific dynasties, vanshas\n... are we done in full? ... EPUB of BC Law book in source to ingest as per our algo now." Read from the repositories,\nthe backup of 10 Nov (09:05), kin.db and claims.db of the afternoon, the mirror\'s log and your screenshot of the credit\n(16:32). Written up in docs\\GENEALOGY_2026-11-10.md.\n\n**Done in full? No.** The genealogy pages are mended where the indexes\' own words allow it and explained on the page;\nthe dynasties need the Puranas\' genealogical chapters read verse by verse (G5), and Sorensen\'s longest entries read\nwhole (kin-long).\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 10 Nov | Explain the genealogy pages | Built (GENEALOGY_HEAL, the Srangam kit): "How to read this page" on both pages (a line; the numbers; the strip\'s colours; the chips; the rails; two fathers; epithets; "a name only"; what a line is not); Sorensen\'s pages say why no cited verse can show and count the epics\' verses; "the longest fathers\' lines" | Yours: the kit, typecheck, vitest, build, commit, push, Publish |\n| 10 Nov | Kaunteya (Arjuna) right | Kaunteya[1] to [4] are Sorensen\'s epithets ("= Arjuna" ...): 5,602 entries now name their person (C26 sends them); Arjuna\'s line runs up through Pandu, not Indra; 125 names of several entries joined by the names both entries give; no line turns back; the lines are fathers\' lines | Yours: the two automaton patchers, C26, index_sync. Left: Pandu\'s line runs on through Vyasa (the index never names Ambalika his mother); Sorensen\'s 52 longest entries were read only to 12,000 characters (kin-long, about $1 to $2) |\n| 10 Nov | The dynasties, the vamsas | Planned, priced (G5a to G5d): Claude reads the Visnu\'s book IV and the Bhagavata\'s book IX verse by verse into kinships, each checked against its verse by machine; a Dynasties page | Money: G5a, about $3 to $8 of the credit. Then free: G5b, G5c |\n| 10 Nov | "An API call thing" | The model reads the Sanskrit once on the desk (metered); the site asks the mirror\'s reader functions; no model at view time | as above |\n| 10 Nov | B. C. Law\'s book, ingested as Raychaudhuri was | CLAIMS_EPUB built: `--work law1926` reads the EPUB\'s pages and their scans (Ancient Indian Tribes, Lahore 1926: Kasis, Kosalas, Asmakas, Magadhas, Bhojas); tested on the real EPUB (226 pages, extract free); private: never on the site | Yours: move the EPUB, extract, a trial, the five chapters (about $2.34, Google\'s cap); link; peoples_index |\n| 10 Nov | The Claude credit, steps 1 to 3 | Done by you: $36.61 of $200 (5,180 calls): the Hayasirsa 2,899 translations $17.08, the Karanagama 1,570 $9.40, the Nirukta\'s Hindi 669 $9.17, 41 stories $0.96. The Hayasirsa and the Nirukta released (15:48, 15:50) and on the site (the 18:33 tick: 386 groups equal) | Next: steps 4 to 7 (about $112); four Nirukta passages came back as the Sanskrit (echo filter; $0.03) |\n| 10 Nov | Raychaudhuri\'s page 252 and Appendix | The Appendix read on 9 Nov (pdf 329-332, 61 claims); linked again at 16:34; peoples_index: 54 peoples, 758 claims. Page 252 refused six times: the model copies the scan\'s `"\'uccessors` into its JSON. Mended (CLAIMS_EPUB: the quote escaped): `--reparse` reads it again from the stored reply, free | Yours: `--reparse`, `--link` |\n| 10 Nov | The Professor asked again | Not in the backup of 10 Nov (the last ask_prof row is of 28 Oct) | Yours |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | load-js: /articles loads 2.0 MB of JavaScript uncompressed (the glossary chunk alone 330 KB, 130 KB transferred); the build's chunks over 500 kB |\n",
     '| Next | load-js: /articles loads 2.0 MB of JavaScript uncompressed (the glossary chunk alone 330 KB, 130 KB transferred); the build\'s chunks over 500 kB |\n\n## 39. 10 Nov: the genealogies mended and explained; B. C. Law made ready (DOCS104_2026_11_10)\n\n| What | State |\n|---|---|\n| Release | Automaton `321f542f` pushed (DOCS103); Srangam `9a22055` published; C25 live |\n| Verified | the backup of 10 Nov; the mirror equal at the 18:33 tick (386 groups; the genealogies\' 8 tables); the credit\'s screenshot ($36.61 of $200) |\n| The asks | docs\\ASKS_2026-10-22.md section 17 |\n| Found | Sorensen\'s epithets drawn as persons (5,525 entries "= X"); Arjuna\'s line through Indra (Pandu\'s statement unjoined); lines through mothers and turning back; the page\'s marks unexplained; 52 long entries read only to 12,000 characters; Raychaudhuri p. 252 refused for a quote in the OCR |\n| Built | GENEALOGY_HEAL_2026_11_10 (vamsa_view.py, index_sync.py; the Srangam kit); C26 (the epithets on the site); CLAIMS_EPUB_2026_11_10 (scholar_claims.py --work law1926; kin_index.py, relations_view.py, peoples_index.py); docs\\GENEALOGY_2026-11-10.md; DOCS104 |\n| To do | the three automaton patchers, docs_map.py --write, run_tests; C26; the Srangam kit; index_sync --apply; B. C. Law\'s five chapters; Raychaudhuri --reparse |\n| Next | G5a (the dynasties: about $3 to $8 of the credit); kin-long (about $1 to $2); the credit\'s steps 4 to 7; load-js |\n')

edit('RUNBOOK.md', 1, '   then `python scripts\\repair_text.py --doc nirukta__w_gretil --release`.\n',
     "   then `python scripts\\repair_text.py --doc nirukta__w_gretil --release`.\n\n## 10 Nov: the genealogies, C26 and B. C. Law (DOCS104_2026_11_10)\n\ndocs\\GENEALOGY_2026-11-10.md; docs\\ASKS_2026-10-22.md, section 17. From the automaton's root unless said:\n\n1. The patches: `python scripts\\patch_claims_epub_2026_11_10.py --check`, then without; the same for\n   `patch_genealogy_heal_2026_11_10.py` and `patch_docs104_2026_11_10.py`; `python scripts\\docs_map.py --write`;\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1` (231 modules); release.ps1 with\n   COMMIT_MSG_genealogy_20261110.txt.\n2. C26 in the Lovable Cloud SQL editor (docs\\cloud\\C26_index_aliases_2026-11-10.sql): B1, B2, the change (one paste,\n   BEGIN to COMMIT), A1, A3. Expected A1: true, true, true; A3: false, true, false.\n3. Srangam (D:\\srangam-42267): `git pull --rebase --autostash`; the kit's patcher (`--check`, then without);\n   `npm run typecheck`; `npx vitest run`; `npm run build`; `git add` the five files by name; commit; push; Publish.\n4. `python scripts\\index_sync.py` (the plan: about 6,800 persons, 87 statements and 76 steps to send, about 200 rows\n   to delete), then\n   `python scripts\\index_sync.py --apply`; then A2 of C26. Open /corpus/genealogies/inm/9364 (Kaunteya[1]) and\n   /corpus/genealogies/inm/4635 (Arjuna) signed in.\n5. B. C. Law: `New-Item -ItemType Directory -Force data\\shelf\\law1926`; `Move-Item\n   inbox\\2015.78161.Ancient-Indian-Tribes.epub data\\shelf\\law1926\\`; then `python scripts\\scholar_claims.py --work\n   law1926` with `--extract` (free); `--pages 1-3 --yes` (a trial, about $0.04); `--part pre --yes`, then `--part 1 --yes`\n   to `--part 5 --yes` (about $2.30 in all); `--link`; `--report`. Then `python scripts\\peoples_index.py --yes`.\n6. Raychaudhuri's page 252: `python scripts\\scholar_claims.py --reparse` (free), `python scripts\\scholar_claims.py --link`.\n")

edit('scripts/docs_map.py', 1, '    ("Plans and paths", r"^(ENTERPRISE|PATH|BRAIN_PATH|OPERATING_MODEL|PLATFORM|CLOUD_BRAIN|PIPELINE_STATE|"\n                        r"RETIREMENT|SOP_|QUALITY_METHODOLOGY|DEBT|.*_DESIGN_)"),\n    ("Names, relations and genealogies", r"^(RELATIONS|VAMSA|INDEX_SITE|B2_AND_X1C|CLAIMS_AND_REFS|SHELF_AND)"),\n    ("The site and the mirror", r"^(CORPUS_MIRROR|SRANGAM|SYNC_COMMANDS|MIRROR_CAP|SCHOLAR_READER|SCHOLAR_SITE|"\n                                r"EDITIONS_SITE|LOAD_|MEDIA_AND_CORNER|RESEARCHERS?_|CORNER_)"),',
     '    ("Plans and paths", r"^(ENTERPRISE|PATH|BRAIN_PATH|OPERATING_MODEL|PLATFORM|CLOUD_BRAIN|PIPELINE_STATE|"\n                        r"RETIREMENT|SOP_|QUALITY_METHODOLOGY|DEBT|.*_DESIGN_)"),\n    ("Names, relations and genealogies", r"^(RELATIONS|VAMSA|INDEX_SITE|B2_AND_X1C|CLAIMS_AND_REFS|SHELF_AND|"\n                                         r"GENEALOGY|PEOPLES)"),   # DOCS104_2026_11_10: and the genealogies, the peoples\n    ("The site and the mirror", r"^(CORPUS_MIRROR|SRANGAM|SYNC_COMMANDS|MIRROR_CAP|SCHOLAR_READER|SCHOLAR_SITE|"\n                                r"EDITIONS_SITE|LOAD_|MEDIA_AND_CORNER|RESEARCHERS?_|CORNER_)"),')


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

