#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs103_2026_11_09.py  (2026-11-09)  DOCS103_2026_11_09

The cards live and measured again; the Claude credit's first runs. docs\\ASKS_2026-10-22.md gains section 16, and
docs\\STATE_2026-10-18.md section 38. docs\\LOAD_AND_STORIES_2026-11-09.md gains section 7: the site measured after
Publish, what is heavy now, and the credit's runs as measured. RUNBOOK.md gains the commands of 9 Nov, later.

Needs DOCS102_2026_11_09 in the four files. Anchored, all-or-nothing, marker-idempotent; line endings kept;
.bak_docs103_<date> copies.

  python scripts\\patch_docs103_2026_11_09.py --check
  python scripts\\patch_docs103_2026_11_09.py
  python scripts\\docs_map.py --write
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS103_2026_11_09'
TAG = 'docs103'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'docs/LOAD_AND_STORIES_2026-11-09.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS102_2026_11_09', 'docs/STATE_2026-10-18.md': 'DOCS102_2026_11_09', 'RUNBOOK.md': 'DOCS102_2026_11_09', 'docs/LOAD_AND_STORIES_2026-11-09.md': 'DOCS102_2026_11_09'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| claims-p252 | Next |\n| dashboard-job | Yours: the rounds still say "translating yajur_veda_shukla_yajur_veda waits: the dashboard runs 1 job(s)" (8 Nov); a job shown running with no process behind it holds them |\n',
     '| claims-p252 | Next |\n| dashboard-job | Yours: the rounds still say "translating yajur_veda_shukla_yajur_veda waits: the dashboard runs 1 job(s)" (8 Nov); a job shown running with no process behind it holds them |\n## 16. 9 Nov, later: the cards live and measured again; the Claude credit\'s first runs (DOCS103_2026_11_09)\n\nRead at 09:53 IST from these sources:\n\n- C25\'s checks, as you pasted them: B1 NULL; B2 50 published, 62 body languages; V succeeded; A1 50 and 62; A2 the\n  invoker\'s rights, with SELECT for anon and authenticated;\n- the site, measured again after Publish with the same script;\n- your screenshots of the story and Hayasirsa runs;\n- the automaton\'s refs, read from .git.\n\n**Done in full? No.** The load-time mend is live and measured. The credit\'s first runs cost less than estimated. The\nrelease is committed but not pushed.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 9 Nov, later | Load times (C25, LOAD_CARDS) | C25 pasted and checked. Srangam `9a22055` pushed and published. The home page, cold: 3,091 KB to 778 KB transferred; LCP 2,504 to 1,072 ms; to idle 5,920 to 2,737 ms. /articles: 3,166 KB to 853 KB. The cards\' read is 16 KB (it was 2,329 KB); 60 articles listed, as before | Done. Next: the JavaScript (load-js) |\n| 9 Nov, later | The stories with Claude | 11 of MBh01\'s candidates written by claude-sonnet-5-5 for $0.2634: $0.024 a story (the estimate was $0.06) | Yours: read them (`stories.py list --doc MBh01 --status draft`), approve. Money: the other texts\' candidates (about 30, about $0.75) |\n| 9 Nov, later | The Hayasirsa\'s translation, a trial | 20 passages in English and 20 in Hindi by claude-sonnet-5-5 for $0.221: $0.0055 a passage; every one qa=1.0, no error | Money: the rest, about 1,433 in each language (about $16 for both), then its release |\n| 9 Nov, later | The release | The commit `7cb611a2` (DOCS102) is made but not pushed: main is one commit ahead of origin/main, so release.ps1 found nothing to commit | Yours: `git push` |\n| 9 Nov, later | The Professor asked again | Not yet: usage_log\'s last ask_prof row is of 28 Oct | Yours |\n\n**The credit\'s plan, priced again at the measured rates:**\n\n| Steps | What | Cost |\n|---|---|---|\n| 1-3 | The stories (about $1); the Hayasirsa\'s English and Hindi ($16); the Karanagama\'s (755 in English, 911 in Hindi: about $9); the Nirukta witness\'s Hindi (648: $3.60) | about $30 |\n| 4 | The Nirukta\'s scholarly English | $11 |\n| 5 | The Markandeya witness\'s flagged verses | $10 |\n| 6 | The Ganita\'s scholarly English | $42 |\n| 7 | GRETIL\'s Natyasastra (4,423) in English and Hindi, at $0.0055 a passage | about $49 |\n| | In all | about $142 of the $200 |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Decisions | the credit's order (seven steps, about $155); the Gandharva Veda; B. C. Law's copy |\n| Next | the load measured again; the JavaScript; page 252 and the Appendix; the hypotheses |\n",
     "| Decisions | the credit's order (seven steps, about $155); the Gandharva Veda; B. C. Law's copy |\n| Next | the load measured again; the JavaScript; page 252 and the Appendix; the hypotheses |\n## 38. 9 Nov, later: the cards live; the Claude credit's first runs (DOCS103_2026_11_09)\n\n| What | State |\n|---|---|\n| Release | Automaton `7cb611a2` committed, not pushed (main ahead of origin by one); Srangam `9a22055` pushed and published; C25 live |\n| Verified | C25's B1, B2, A1, A2; the site measured again (home 778 KB cold, LCP 1,072 ms; /articles 853 KB; the cards' read 16 KB) |\n| The asks | docs\\ASKS_2026-10-22.md section 16 |\n| Spent | the Claude credit: 11 stories $0.2634; the Hayasirsa's trial, 40 translations $0.221 |\n| To do | git push; read and approve the 11 stories; the Hayasirsa's English and Hindi; the Karanagama's; the Nirukta's Hindi and release; the Professor asked again |\n| Next | load-js: /articles loads 2.0 MB of JavaScript uncompressed (the glossary chunk alone 330 KB, 130 KB transferred); the build's chunks over 500 kB |\n")

edit('RUNBOOK.md', 1, '   `python scripts\\scholar_claims.py --part app` then with `--yes`; `python scripts\\scholar_claims.py --link`;\n   `python scripts\\peoples_index.py --yes`.\n',
     "   `python scripts\\scholar_claims.py --part app` then with `--yes`; `python scripts\\scholar_claims.py --link`;\n   `python scripts\\peoples_index.py --yes`.\n## 9 Nov, later: the cards live; the credit's first runs (DOCS103_2026_11_09)\n\ndocs\\ASKS_2026-10-22.md, section 16. From the automaton's root:\n\n1. `git push`: the commit 7cb611a2 (DOCS102) is made but not pushed. Then `python scripts\\patch_docs103_2026_11_09.py --check`,\n   without --check, `python scripts\\docs_map.py --write`, `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`,\n   and release.ps1 with COMMIT_MSG_measured_20261109.txt.\n2. The stories: `python scripts\\stories.py list --doc MBh01 --status draft` (the 11 written by Claude, and #66);\n   `python scripts\\stories.py verify --id 66` (free: the new check); `python scripts\\stories.py show --id 66`; approve in\n   the Stories page, or `python scripts\\stories.py approve --id 66`. A story marked CHECK is read before it is approved.\n3. The Hayasirsa (the Claude credit): `python scripts\\translate_passages.py --doc HAYASHIRSHA_PANCARATRA --engine\n   anthropic:claude-sonnet-5-5`, then the same with `--lang hi`. Then `python scripts\\repair_text.py --doc\n   HAYASHIRSHA_PANCARATRA --release`.\n4. The Karanagama: the same two commands with `--doc Karan_Aagama_by_Prof_Rama_Chandra_Pandey_4_-_Shaiva_Bharati_Varanasi`.\n5. The Nirukta: `python scripts\\translate_passages.py --doc nirukta__w_gretil --engine anthropic:claude-sonnet-5-5 --lang hi`;\n   then `python scripts\\repair_text.py --doc nirukta__w_gretil --release`.\n")

edit('docs/LOAD_AND_STORIES_2026-11-09.md', 1, '4. Filter on "rest/v1": the articles read should be a few KB (srangam_article_cards), not 2.3 MB (srangam_articles).\n',
     '4. Filter on "rest/v1": the articles read should be a few KB (srangam_article_cards), not 2.3 MB (srangam_articles).\n\n## 7. After Publish (9 Nov, 09:55 IST): measured again (DOCS103_2026_11_09)\n\nThe same script and pages. Srangam `9a22055` was published, and C25 was live.\n\n| Page, cold | Before | After |\n|---|---|---|\n| / transferred | 3,091 KB | 778 KB |\n| / LCP | 2,504 ms | 1,072 ms |\n| / to idle | 5,920 ms | 2,737 ms |\n| /articles transferred | 3,166 KB | 853 KB |\n| The articles\' read | 2,329 KB (srangam_articles, select=*) | 16 KB (srangam_article_cards) |\n\nThe lists are as before: 60 articles on /articles (50 from the database, the rest from the site\'s own files).\n\n**What is heavy now.** /articles loads 2.0 MB of JavaScript uncompressed, in 49 requests, and the home page 1.0 MB.\nOn /articles, the glossary chunk (cultural-terms) alone is 330 KB, 130 KB transferred. The build reports chunks over\n500 kB (MapboxBujangNetwork 1,617 kB, MapsData 989 kB, mermaid.core 538 kB) for the pages that use them. The next\nround, load-js, measures which chunks each page loads before it cuts anything.\n\n**The Claude credit\'s first runs:**\n\n| Run | Measured | The estimate |\n|---|---|---|\n| Stories (claude-sonnet-5-5) | $0.024 a story (11 for $0.2634) | $0.06 |\n| Translation, English and Hindi | $0.0055 a passage (40 for $0.221) | $0.0064 |\n')


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

