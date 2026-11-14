#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs111_2026_11_14.py  (2026-11-14)  DOCS111_2026_11_14

The home page healed (the Sacred Ecology card's 404) and a start for readers (the Srangam kit HOME_HEAL_2026_11_14), the
Ganita's repair plan, what is left. This patch adds:

  docs/ASKS_2026-10-22.md    section 24: each ask of 14 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 46
  RUNBOOK.md                 "14 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs111_<date> copies.

  python scripts\\patch_docs111_2026_11_14.py --check
  python scripts\\patch_docs111_2026_11_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS111_2026_11_14'
TAG = 'docs111'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS110_2026_11_13', 'docs/STATE_2026-10-18.md': 'DOCS110_2026_11_13', 'RUNBOOK.md': 'DOCS110_2026_11_13'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 13 Nov | Readers and makers who are not technical (U1 to U3); R1; kin-long | Not begun | Next |\n',
     '| 13 Nov | Readers and makers who are not technical (U1 to U3); R1; kin-long | Not begun | Next |\n\n## 24. 14 Nov: the home page healed; a start for readers (DOCS111_2026_11_14)\n\nAsked on 14 Nov, with a screenshot of the home page\'s Geomythology cards, the release of SOURCE_PICK (057c304), the\nGanita\'s benchmark, its find-source and its repair plan, and the Surya\'s commands: "SACRED eCOLOGY LINK IS BROKEN AND\n404. IS HOMEPAGE RATIONALISED AND REFLECTIVE OF OUR PRESENT IMPLEMENTATION AND STACK?", with the list left on 13 Nov\n(U1 to U3, R1, the long Sorensen entries, the Markandeya\'s 113, the Nirukta). Read from Srangam\'s code (main 6d8aad4:\nsrc/pages/Home.tsx, src/components/home, src/App.tsx, src/data/articles/meta.ts, the corpus pages) and your screenshots.\n\n**Done in full? No.** The broken link is mended and the home page now begins the texts (U1, begun); U2, U3, R1 and the\nlong Sorensen entries are builds still ahead; the Markandeya\'s 113 and the Nirukta are runs of yours.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 14 Nov | "SACRED eCOLOGY LINK IS BROKEN AND 404" | Found: the home page\'s fourth Geomythology card (src/components/home/GeomythologySection.tsx) linked /sacred-ecology; no route has that path and no article that slug (the theme "Sacred Ecology" is a theme, not an article). Built the Srangam kit HOME_HEAL_2026_11_14: the card opens Part 1 of the Sacred Ecology series, "Under the Sacred Tree" (/articles/sacred-tree-harvest-rhythms), as the Ancient India theme page does; /sacred-ecology redirects there; the other three cards link their articles directly (/articles/earth-sea-sangam, /articles/stone-purana, /articles/gondwana-to-himalaya) instead of through a redirect | Yours: the kit, typecheck, vitest, build, push, Publish |\n| 14 Nov | "IS HOMEPAGE RATIONALISED AND REFLECTIVE OF OUR PRESENT IMPLEMENTATION AND STACK?" | No. It shows the articles (featured and all), two collections, the research network, the Geomythology cards, two tools, the five themes, the field notes and the maps: Srangam as it was in 2025. Nothing on it led to the texts, the scholarly editions or the working corpus, which the articles now rest on (the Corner: 57 texts in English, 29,145 passages translated). Every other link written on it is a route (the kit\'s test reads them all) | Built: "Start here" (below) |\n| 14 Nov | U1, "start here" for amateur Sanskritists | Begun: CorpusStartSection, after the opening section and before the featured articles, lazy (3.7 kB, 1.6 kB gzipped), static (it calls nothing): seven doors in plain words, the published texts (/texts) and the scholarly editions (/editions) open to all, the scholarly English as prose, the dynasties, the names, the stories and the guided steps for invited readers, each marked so; tested: typecheck clean, vitest 52 files and 433 tests, the build | Next: a reader\'s first page inside the corpus in the same words; U2 (the desk\'s "make a scholarly edition" in plain words); U3 (three amateurs, five tasks, timed) |\n| 14 Nov | The Ganita | Your benchmark: PICK ours (consensus), repair first (1.93% of the letters misread, moderate). Find-source: 29 candidates; the best are archive.org copies of the same edition (OCR 100% Devanagari), no e-text. Your repair plan: vision has read 112 of 339 pages, 227 to go, about $0.79 at $0.0035 a page; 3 pages of the repair differ from the database | Yours: reingest_pages for the 3, then the repair (--max-usd 1.00), then reingest_pages again, its English and Hindi for the changed passages, the benchmark again, then the edition |\n| 14 Nov | The Surya | You ran its triage and the Opus reading of the serious (05:35 IST); the result is not in the screenshots | Yours: its status (free) |\n| 14 Nov | R1 (our findings); the long Sorensen entries | Not begun | Next: builds |\n| 14 Nov | The Markandeya\'s 113; the Nirukta | Runs of yours, priced on 13 Nov (about $3 to $5; about $16 to $28) | Yours: the commands below |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | U1 to U3; R1; kin-long; the Markandeya's 113; the Nirukta; load-js |\n",
     "| Next | U1 to U3; R1; kin-long; the Markandeya's 113; the Nirukta; load-js |\n\n## 46. 14 Nov: the home page healed; a start for readers (DOCS111_2026_11_14)\n\n| What | State |\n|---|---|\n| Verified | The release of SOURCE_PICK and DOCS110 (057c304); the dashboard restarted (22:35 IST, 13 Nov); the Ganita's benchmark (PICK: repair first) and its repair plan |\n| The asks | docs\\ASKS_2026-10-22.md section 24 |\n| Built | The Srangam kit HOME_HEAL_2026_11_14 (docs\\srangam\\HOME_HEAL_2026-11-14, scripts\\patch_srangam_home_heal_2026_11_14.py); DOCS111 |\n| Measured | The home page: 19 links written on it, one of them (/sacred-ecology) to no route; no link to the texts or the corpus before the kit |\n| To do | the kit, typecheck, vitest, build, push, Publish; the release; the Ganita's repair; the Surya's status |\n| Next | U1's second half, U2, U3; R1; kin-long; the Markandeya's 113; the Nirukta; load-js |\n")

edit('RUNBOOK.md', 1, '6. Mallapurana: the next presses from /desk/Mallapurana; then "As prose".\n',
     '6. Mallapurana: the next presses from /desk/Mallapurana; then "As prose".\n\n## 14 Nov: the home page healed; a start for readers (DOCS111_2026_11_14)\n\ndocs\\ASKS_2026-10-22.md, section 24.\n\n1. The automaton: `python scripts\\patch_docs111_2026_11_14.py --check`, then without; `python -m unittest\n   tests.test_docs111_2026_11_14`; `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with\n   COMMIT_MSG_homeheal_20261114.txt.\n2. Srangam (D:\\srangam-42267): `git pull --rebase --autostash`; the kit\'s patcher (`--check`, then without); `npm run\n   typecheck`; `npx vitest run`; `npm run build`; `git add` the five files by name (src/App.tsx, src/pages/Home.tsx,\n   src/components/home/GeomythologySection.tsx, src/components/home/CorpusStartSection.tsx,\n   src/__tests__/home-heal.test.tsx); commit; push; Publish. Then open the home page and /sacred-ecology.\n3. The Ganita: `python scripts\\reingest_pages.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (the plan, free), then\n   with `--apply`; `python scripts\\repair_text.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V --repair --max-usd 1.00`;\n   reingest_pages again (plan, then --apply); its English and Hindi for the changed passages (the Library, or\n   translate_passages.py with gemini:gemini-2.5-flash); `python scripts\\benchmark_sources.py --doc\n   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` again; then its edition from its desk page, in presses of 250.\n4. The Surya: `python scripts\\scholar_translate.py --doc jyotish_surya_siddhanta__w_etext --status` (free).\n5. The Markandeya\'s 113: `python scripts\\scholar_translate.py --doc markandeya_purana__w_gretil --engine\n   anthropic:claude-sonnet-5-5 --triage` (free), then the Opus reading of the serious as for the Surya on 13 Nov (a dry\n   run first). The Nirukta: its desk page (/desk/nirukta__w_gretil), Plan (free), Run, 250 verses a press.\n')


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

