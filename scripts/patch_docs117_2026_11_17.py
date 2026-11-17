#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs117_2026_11_17.py  (2026-11-17)  DOCS117_2026_11_17

Is it done? 17 Nov, night: G6c built (scripts\\vamsa_align.py: the same dynasty side by side in every work that has
it, generation by generation, free) and I1 built (the Srangam kit AI_GATEWAY_OFF_2026-11-17: detect-duplicate-articles
and suggest-tag-categories off the Lovable AI Gateway, on the project's own Gemini and OpenAI keys); G6d designed, not
built; G6b at 154 of 248 parts. This patch adds:

  docs/ASKS_2026-10-22.md    section 30: each ask of 17 Nov, night, done or not, with its evidence; G6d's design
  docs/STATE_2026-10-18.md   section 52
  RUNBOOK.md                 "17 Nov, night": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs117_<date> copies.

  python scripts\\patch_docs117_2026_11_17.py --check
  python scripts\\patch_docs117_2026_11_17.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS117_2026_11_17'
TAG = 'docs117'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS116_2026_11_16', 'docs/STATE_2026-10-18.md': 'DOCS116_2026_11_16', 'RUNBOOK.md': 'DOCS116_2026_11_16'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, '| 17 Nov | The backups | Your list: 148.0 GB in copies made before a step and older than 14 days; nothing moved | I5: the rule, then your choice |\n',
     '| 17 Nov | The backups | Your list: 148.0 GB in copies made before a step and older than 14 days; nothing moved | I5: the rule, then your choice |\n\n## 30. 17 Nov, night: G6c and I1 built; G6d next (DOCS117_2026_11_17)\n\nAsked on 17 Nov, 21:50, with a CSV of pg_cron\'s runs and four screens: "1. G6c: align the same dynasty across the\nworks (free). 2. I1: move the two site functions off the Lovable gateway (a Srangam kit). 3. G6d: the person register,\nwhich fixes the two Pariksits and the double names. IS THIS DONE", and the ask of 16 Nov again. Read on the PC, read\nonly: data\\vamsa_read (every stored reading, last written 21:41), the Srangam checkout (main at de1e346,\nHOME_HEAL_2026_11_14, equal to origin/main as last fetched). Built and tested on copies; nothing on the PC was run.\n\n**Done in full? No.** Built tonight and tested: G6c (scripts\\vamsa_align.py) and I1 (the Srangam kit\nAI_GATEWAY_OFF_2026-11-17). Neither is in use until you apply it: G6c by running it, I1 by the kit, the push, Publish\nand Lovable\'s deploy. Not built: G6d (its design below), G6e, G6f. Not finished: G6b (154 of 248 parts). Still waiting\nas in section 28: I3 to I6, Mallapurana\'s edition, the reviewers\' queue, U2, U3, R1.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 17 Nov | "IS THIS DONE" (G6c, I1, G6d) | No: G6c and I1 built and tested here, not yet applied by you; G6d not built | G6d next, after G6b |\n| 17 Nov | G6c: the same dynasty across the works | Built: scripts\\vamsa_align.py (VAMSA_ALIGN_2026_11_17), free, reads the stored readings and writes exports\\vamsa_align.md, one CSV a dynasty (exports\\vamsa_align_kuru.csv and the like) and data\\vamsa_read\\aligned.json. tests\\test_vamsa_align_2026_11_17.py: 17 tests OK. On a copy of the readings of 21:41: 10 dynasties in two works or more; of their 131 generations 55 agree, 15 most, 47 differ, 14 in one work only | You: run it; again when G6b ends |\n| 17 Nov | G6c, how | Each dynasty by its founder and his father (12: Ikshvaku son of Manu, Nimi, Pururavas, Yadu, Sahasrajit, Kroshtu, Turvasu, Druhyu, Anu, Puru, Kuru son of Samvarana, Brhadratha son of Vasu); in each work the line below him with the most names the other works share, then the longest; the lines aligned together (names one when their letters agree at 0.82 or more, diacritics, visarga and nasals set aside; a name of four letters or fewer only when equal: Anu is not Manu); each generation agree, most (more than half), differ or one; each two works how often they agree | Done |\n| 17 Nov | G6c, what it shows | The Kurus: 6 works, 21 generations, 10 agree, 3 most, 5 differ, 3 one; matsya and vip4 agree at 15 of 18 generations. The Barhadrathas of Magadha (hv, vip4, matsya): Brhadratha, Kusagra, Rsabha, Puspavan, Satyahita, Urja, Sambhava, Jarasandha, Sahadeva. The Pauravas part most (29 generations, 5 agree): the Puranas\' early Pauravas are not the Adiparvan\'s. The Anavas are not shown (no second work has a line of three below Anu son of Yayati) | A "differ" can be two brothers (each work\'s line follows one son); the reading of what differs is G6f with R1 |\n| 17 Nov | One person by two names within a work | Built into G6c: a verified "other" whose words say he was called so (samjna, nama, ahuh, smrta, khyata, ucyate, visruta, prathita) makes the second name the first in its chapter and the chapters beside it: vip4\'s Vikukshi called Sasada, so Puranjaya is Vikukshi\'s son. Within a work only; the verse\'s own name is kept | Across the works and the homonyms: G6d |\n| 17 Nov | I1: the two site functions off the Lovable gateway | Built: docs\\srangam\\AI_GATEWAY_OFF_2026-11-17 and scripts\\patch_srangam_ai_gateway_off_2026_11_17.py. detect-duplicate-articles and suggest-tag-categories call _shared/ai-provider.ts (aiExtractCitations: Gemini 2.5 Flash on GEMINI_API_KEY, one retry, then OpenAI gpt-4o-mini on OPENAI_API_KEY), logged in srangam_ai_usage (purposes duplicate_check, tag_categories); when both keys fail they say so and call nothing else. New: src/__tests__/ai-gateway-off.test.ts; RELIABILITY_AUDIT Phase AS, invariant 69 | You: the kit, typecheck, vitest, build, push, Publish; ask Lovable to deploy the two functions |\n| 17 Nov | I1, tested | tests\\test_srangam_ai_gateway_off_2026_11_17.py: 6 tests OK. The patch on copies of main\'s files (de1e346): 4 files written, CRLF kept, the second run does nothing. The two edited functions and the new test parse (TypeScript\'s transpile). Not run here: npm run typecheck, vitest, build (they need your node_modules) | Your run of the three |\n| 17 Nov | What used the gateway | Read in the checkout: only those two files under supabase\\functions name ai.gateway.lovable.dev or LOVABLE_API_KEY; 5 functions already import _shared/ai-provider.ts | Done |\n| 17 Nov | G6d: the person register | Not built (designed below) | Next, after G6b |\n| 17 Nov | G6b | linga1 11 of 15 parts at 21:41, then nothing since; in all 154 of 248 parts. Left: linga1 4, kurma1 16, garuda1 14, agni 9, markp 4, mbh1 14, vipc4 33 parts (94), about $2.95 | You: the same command again |\n| 17 Nov | Your CSV: pg_cron\'s runs | The 6 nightly jobs each succeeded on 16 and 17 Nov; with section 29\'s watchdog every 5 minutes, all 7 active jobs ran | Done |\n| 17 Nov | The Claude credit | Your meter at 21:40: $93.80 left, to 11 Dec | Section 28\'s plan for it |\n\nG6d, the design. One register of persons across the works, read from what G6c aligned, nothing bought:\n- an entry is one person; two works\' persons are joined into one entry when they stand in one aligned generation of\n  one dynasty, their names are one, and their fathers are one (or already one entry); each join keeps its works and\n  verses, and a join made by the alignment (not said by a verse) is marked as ours, never as the text\'s word;\n- one name of two persons is two entries: vamsa_read.persons keys a person by his name and his father, but a father\'s\n  own entry is chosen by the nearest chapter, which in mbh1 joins Kuru\'s Pariksit (son of Avikshit) and Abhimanyu\'s son;\n  G6d chooses it by the father\'s own father where the text gives it, and keeps the two apart;\n- two names of one person: the "other" statements of every work (G6c uses them within a work), and an aligned\n  generation whose father and son agree across works though its name differs (mbh1\'s Paryasravas where the others give\n  Pratipa, Vrkodara and Bhimasena), proposed as ours with both verses;\n- written to data\\vamsa_read\\register.json and exports\\vamsa_register.csv; then G6e (one page model: the desk\'s\n  Dynasties page, then the site) and G6f (with R1, our findings on a line).\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G6c to G6f; I1, I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3, R1 |\n",
     "| Next | G6c to G6f; I1, I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3, R1 |\n\n## 52. 17 Nov, night: G6c and I1 built (DOCS117_2026_11_17)\n\n| What | State |\n|---|---|\n| Verified | On copies: vamsa_align (17 tests), the kit AI_GATEWAY_OFF (6 tests; applied to copies of main's files, then a second run does nothing); pg_cron's 6 nightly jobs succeeded on 16 and 17 Nov (your CSV) |\n| The asks | docs\\ASKS_2026-10-22.md section 30 |\n| Built | scripts\\vamsa_align.py (G6c); docs\\srangam\\AI_GATEWAY_OFF_2026-11-17 and scripts\\patch_srangam_ai_gateway_off_2026_11_17.py (I1); DOCS117 |\n| Measured | G6c on the readings of 21:41: 10 dynasties, 131 generations: 55 agree, 15 most, 47 differ, 14 one; G6b 154 of 248 parts; $93.80 of the Claude credit left at 21:40 |\n| Not verified | Srangam's typecheck, vitest and build with the kit (your node_modules); the functions' behaviour once deployed (srangam_ai_usage will show it) |\n| To do | the patch, release; vamsa_align; the kit, push, Publish, Lovable's deploy; G6b again |\n| Next | G6d (designed in section 30); G6e, G6f; I3 to I6; Mallapurana's edition; the reviewers' queue; U2, U3, R1 |\n")

edit('RUNBOOK.md', 1, "5. The site's schema: docs\\cloud\\SITE_SCHEMA_2026-11-17.md; its two read-only queries check it again.\n",
     '5. The site\'s schema: docs\\cloud\\SITE_SCHEMA_2026-11-17.md; its two read-only queries check it again.\n\n## 17 Nov, night: G6c, the dynasties across the works; I1, the site off the Lovable gateway (DOCS117_2026_11_17)\n\ndocs\\ASKS_2026-10-22.md, section 30. From the automaton\'s root, in PowerShell:\n\n1. The patch: `python scripts\\patch_docs117_2026_11_17.py --check`, then without; `python -m unittest\n   tests.test_vamsa_align_2026_11_17 tests.test_srangam_ai_gateway_off_2026_11_17 tests.test_docs117_2026_11_17\n   tests.test_docs116_2026_11_16`; release.ps1 with COMMIT_MSG_g6c_i1_20261117.txt (the dry run, then -Apply once).\n2. G6c, free: `python scripts\\vamsa_align.py --list` (writes nothing), then `python scripts\\vamsa_align.py` (writes\n   exports\\vamsa_align.md, one CSV a dynasty, data\\vamsa_read\\aligned.json); one dynasty on screen: `python\n   scripts\\vamsa_align.py --anchor Kuru`; any founder: `python scripts\\vamsa_align.py --anchor Bharata --father\n   Dusyanta`.\n3. G6b, the rest (about $2.95): `python scripts\\vamsa_read.py --work g6 --yes --max-usd 8`; when it stops on a dropped\n   connection, the same command again; then `python scripts\\vamsa_read.py --work g6 --report` and step 2 again.\n4. I1, in D:\\srangam-42267: `git pull`; `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\\n   patch_srangam_ai_gateway_off_2026_11_17.py" --check`, then without; `npm run typecheck`; `npx vitest run`; `npm\n   run build`; commit and push; Publish in Lovable; ask Lovable\'s chat to deploy detect-duplicate-articles and\n   suggest-tag-categories. Then, in the Lovable Cloud SQL editor, srangam_ai_usage shows their calls by provider.\n5. The credit: `python scripts\\claude_engine.py --credit`.\n')


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

