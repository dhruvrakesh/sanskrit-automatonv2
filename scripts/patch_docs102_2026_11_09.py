#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs102_2026_11_09.py  (2026-11-09)  DOCS102_2026_11_09

The asks of 9 Nov recorded. docs\\ASKS_2026-10-22.md gains section 15: the stories (STORY_QUALITY), what reaches
Srangam, the Claude credit and its plan, Raychaudhuri's Part II and the peoples, local and cloud, the load times
measured (LOAD_CARDS, C25), the asks of 28 Oct read again, the new keys. docs\\STATE_2026-10-18.md gains section 37;
RUNBOOK.md the commands of 9 Nov.

Needs DOCS101_2026_10_28 in the three files; requires the STORY_QUALITY and LOAD_CARDS patchers,
docs\\LOAD_AND_STORIES_2026-11-09.md and docs\\cloud\\C25_article_cards_2026-11-09.sql. Anchored, all-or-nothing,
marker-idempotent; line endings kept; .bak_docs102_<date> copies.

  python scripts\\patch_docs102_2026_11_09.py --check
  python scripts\\patch_docs102_2026_11_09.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS102_2026_11_09'
TAG = 'docs102'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS101_2026_10_28', 'docs/STATE_2026-10-18.md': 'DOCS101_2026_10_28', 'RUNBOOK.md': 'DOCS101_2026_10_28'}
REQUIRES = {'scripts/patch_story_quality_2026_11_09.py': 'STORY_QUALITY_2026_11_09', 'scripts/patch_srangam_load_cards_2026_11_09.py': 'LOAD_CARDS_2026_11_09', 'docs/LOAD_AND_STORIES_2026-11-09.md': 'DOCS102_2026_11_09', 'docs/cloud/C25_article_cards_2026-11-09.sql': 'LOAD_CARDS_2026_11_09'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| gandharva-site | Yours |\n| cap-order | Yours: what to spend the $22.56 on |\n',
     '| gandharva-site | Yours |\n| cap-order | Yours: what to spend the $22.56 on |\n## 15. 9 Nov: the stories, the Claude credit, the load times; the asks of 28 Oct read again (DOCS102_2026_11_09)\n\nRead on 9 Nov from these sources:\n\n- the daily backup `D:\\backups\\context_20261109.db` (read-only, immutable);\n- the mirror\'s and the maintenance logs to 07:22 IST;\n- data\\jobs.jsonl, data\\shelf\\claims.db and data\\shelf\\peoples_index.json;\n- the checks you pasted (N1 to N4);\n- the Console\'s Billing page (your screenshot);\n- a measurement of the site\'s load (docs\\LOAD_AND_STORIES_2026-11-09.md, section 1).\n\n**Done in full? No.** Since 28 Oct you applied the night\'s three patches (225 modules, 1,665 tests) and read\nRaychaudhuri\'s Part II. The Professor was not asked again: usage_log\'s last ask_prof row is of 28 Oct, 17:46 IST. The\nHayasirsa\'s, Karanagama\'s and Nirukta\'s translations were not run, and the Gandharva Veda\'s text is still the\nTesseract reading on the site.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 9 Nov | "the quality of stories ... can be much better, can\'t it?" | Yes, it can. Five faults were found on the Stories page and in stories.py, and mended (STORY_QUALITY): the best English to the writer (the scholarly where it stands), Claude as the writer by choice, a storyteller\'s rule (7), no episodes from a treatise, the check\'s false failure (#66 on "ksatriyas"), the image idea\'s JSON (#81), the 429 waits | Yours: apply it; set SA_STORY_WRITER; write the candidates again (Money: about $3 from the Claude credit) |\n| 9 Nov | Will the stories and images reach Srangam? | Yes. Every story goes at each tick; readers see the approved ones (27 on 9 Nov). All 62 pictures\' 124 renditions are on Drive, and the site\'s pictures equal the desk\'s. "Update brain" builds the PC\'s own index for its Ask, which stays on the PC | Done; a story is public within two hours of its approval |\n| 9 Nov | The $200 of Anthropic credit, to best effect | The credit read: $10.57 to 11 Nov and $200 to 11 Dec; the meter still holds the old grant ($0.92 left). A plan of seven steps, about $155, at measured prices (LOAD_AND_STORIES section 3) | Yours: the three .env lines; then the steps in order, each with its dry run |\n| 9 Nov | Raychaudhuri carried forward; the tribes (B. C. Law) | Part II read (215 of 216 pages, 4,228 claims) and linked; 6,062 claims on the site; peoples_index.py: 54 of the 289 peoples now beside his claims (757) | Next: page 252 and the Appendix (about $0.05). Money: the hypotheses (P4, about $2 to $3, after the Professor\'s re-asked answer). Yours: B. C. Law\'s copy |\n| 9 Nov | Local and cloud | 374 groups equal, 0 different, at every tick from 28 Oct to 9 Nov. N1 to N4 as expected. One tick failed on a DNS error (8 Nov, 10:31); one waited 8 hours while the PC slept | Done |\n| 9 Nov | UI/UX, navigation, a benchmarked interface, load times | Measured for the first time: the home page transfers 3,091 KB cold, 2,329 KB of it one query of the articles\' bodies. LOAD_CARDS and C25 cut it; the rest of the weight (about 1 MB of JavaScript a page, the fonts) is named | Yours: C25, the Srangam patch, Publish; then measured again. Navigation not reviewed this round |\n| 9 Nov | The asks of 28 Oct, read again | ASK_ROOM, CLAIMS_PART2, PEOPLES and DOCS101 applied (225 modules, 1,665 tests); the Padma reingested (21,128 passages to 20,014) | Yours: the Professor asked again; the Hayasirsa, Karanagama and Nirukta translations (now planned on the Claude credit); the Gandharva Veda |\n\n**The cap and the credit:** Google\'s cap stands at $117.45 of $135 spent. The Claude credit is $210.57 in the\nConsole, $200 of it to 11 Dec.\n\n**New keys (9 Nov):**\n\n| Key | State |\n|---|---|\n| story-quality | Yours: apply |\n| claude-credit | Yours: the .env lines, then the plan |\n| load-cards | Yours: C25, the patch, Publish |\n| load-js | Next: the 1 MB of JavaScript on every page, measured, then split |\n| claims-p252 | Next |\n| dashboard-job | Yours: the rounds still say "translating yajur_veda_shukla_yajur_veda waits: the dashboard runs 1 job(s)" (8 Nov); a job shown running with no process behind it holds them |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Decisions | the cap's order ($22.56 left, about $35 asked); the Gandharva Veda on the site; B. C. Law's copy |\n| Next | Part II (Money); the hypotheses (Money); vamsa-skeleton; thinking-ab; proxy-limit; load-ux |\n",
     "| Decisions | the cap's order ($22.56 left, about $35 asked); the Gandharva Veda on the site; B. C. Law's copy |\n| Next | Part II (Money); the hypotheses (Money); vamsa-skeleton; thinking-ab; proxy-limit; load-ux |\n## 37. 9 Nov: load times measured; the stories mended; the Claude credit planned (DOCS102_2026_11_09)\n\n| What | State |\n|---|---|\n| Release | `e737e299` pushed on 28 Oct (DOCS101). Applied by you since: the three patches of 28 Oct, night; Part II read (215 of 216 pages) and linked; peoples_index.py run again; the Padma reingested |\n| Verified | the backup of 9 Nov; the mirror equal at every tick to 9 Nov; N1 to N4; usage_log ($117.45 of $135 on Google's cap) |\n| The asks | docs\\ASKS_2026-10-22.md section 15: not done in full; the stories, the credit and the load times this round |\n| Found | the home page: 3,091 KB, 2,329 KB of it the articles' bodies; the stories' check failing on common nouns; a treatise mined for episodes; an image idea lost to a trailing brace; 429s outlasting the waits; the Claude meter still on the old grant |\n| Built | STORY_QUALITY_2026_11_09 (stories.py, images.py); LOAD_CARDS_2026_11_09 (Srangam's useArticles.ts) and C25 (the view); docs\\LOAD_AND_STORIES_2026-11-09.md; DOCS102 |\n| To do | the two automaton patchers, docs_map.py --write, run_tests; the .env lines; C25 in Lovable Cloud; the Srangam patch, typecheck, vitest, build, commit, Publish |\n| Decisions | the credit's order (seven steps, about $155); the Gandharva Veda; B. C. Law's copy |\n| Next | the load measured again; the JavaScript; page 252 and the Appendix; the hypotheses |\n")

edit('RUNBOOK.md', 1, '   `python scripts\\reingest_pages.py --doc SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press`, then\n   the same with `--apply`.\n',
     '   `python scripts\\reingest_pages.py --doc SP_4214_Pataal_Khanda_from_Padma_Puran_1895_-_Sri_Venkateshwar_Press`, then\n   the same with `--apply`.\n## 9 Nov: the stories, the Claude credit, the load times (DOCS102_2026_11_09)\n\ndocs\\LOAD_AND_STORIES_2026-11-09.md; docs\\ASKS_2026-10-22.md, section 15. From the automaton\'s root unless said:\n\n1. `python scripts\\patch_story_quality_2026_11_09.py --check`, then without --check; the same for\n   `patch_docs102_2026_11_09.py`. Then `python scripts\\docs_map.py --write` and\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`. Restart the dashboard when it is idle.\n2. The Claude credit (the new grant, to 11 Dec): three lines appended to .env (section 3 of the page gives them;\n   the RUNBOOK\'s commands check first that .env does not hold them already, printing names only). Then\n   `python scripts\\claude_engine.py --credit` (free): "$0.00 spent of $200.00 since 2026-11-09".\n3. The stories with Claude: `SA_STORY_WRITER=anthropic:claude-sonnet-5-5@medium` in .env, the dashboard restarted;\n   `python scripts\\stories.py write --doc MBh01 --candidates --max 12` (the dry run), then with `--yes`. Read each in the\n   Stories page; approve what stands. The next tick sends them.\n4. Srangam\'s load: C25 in the Lovable Cloud SQL editor (B1, B2, V, A1, A2, one block a paste). Then, in D:\\srangam-42267:\n   `git pull --rebase --autostash`; `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_cards_2026_11_09.py" --check`,\n   then without --check; `npm run typecheck`; `npx vitest run`; `npm run build`; `git add -- src/hooks/useArticles.ts`;\n   `git commit -m "LOAD_CARDS_2026_11_09: the article cards without their bodies"`; `git push`; Publish in Lovable.\n5. Raychaudhuri: `python scripts\\scholar_claims.py --pages 252` (the plan), then with `--yes`;\n   `python scripts\\scholar_claims.py --part app` then with `--yes`; `python scripts\\scholar_claims.py --link`;\n   `python scripts\\peoples_index.py --yes`.\n')


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

