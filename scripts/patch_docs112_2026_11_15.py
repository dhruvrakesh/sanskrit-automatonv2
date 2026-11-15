#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs112_2026_11_15.py  (2026-11-15)  DOCS112_2026_11_15

The genealogies made one (what is there, what the texts offer, the plan G6a to G6f, priced), the evolution of the
project traced from both histories, the repair's loop mended (REPAIR_LOOP). This patch adds:

  docs/ASKS_2026-10-22.md    section 25: each ask of 15 Nov, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 47
  RUNBOOK.md                 "15 Nov": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs112_<date> copies.

  python scripts\\patch_docs112_2026_11_15.py --check
  python scripts\\patch_docs112_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS112_2026_11_15'
TAG = 'docs112'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS111_2026_11_14', 'docs/STATE_2026-10-18.md': 'DOCS111_2026_11_14', 'RUNBOOK.md': 'DOCS111_2026_11_14'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 14 Nov | The Markandeya's 113; the Nirukta | Runs of yours, priced on 13 Nov (about $3 to $5; about $16 to $28) | Yours: the commands below |\n",
     '| 14 Nov | The Markandeya\'s 113; the Nirukta | Runs of yours, priced on 13 Nov (about $3 to $5; about $16 to $28) | Yours: the commands below |\n\n## 25. 15 Nov: the genealogies made one; the evolution traced; the repair\'s loop (DOCS112_2026_11_15)\n\nAsked on 15 Nov, with the key\'s check, the probe, the seventeen jobs queued and the Samaveda\'s benchmark: "use the\ncharacters from mahabharata, major mahapuranas, ramayana that we already have on list and record and then have\nauthoritative genealogies of these kings with an easy intuitive ui/ux locally and online ... the sanskrit texts (primary\nand critical editions, wherever possible) and then use our own corelations to add to and/or comment on the inferences\n... update our brain document also and trace evolution of this project now. also, ganita yuktibhasa scan repair seems\nto be stuck in a loop on local frontend. use multiple agents as needed". Three agents read the repositories, the\nshelf (kin.db, claims.db, vamsa.db, read immutable), the backup of 15 Nov (immutable), GRETIL\'s archive here and both\ngit histories, read only; their findings are below with their sources.\n\n**Done in full? No.** The repair\'s loop is mended and the plan for one coherent genealogy is made and priced; the\ngenealogy itself (G6) is a build of several rounds.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 15 Nov | The Claude key | It answered "401 invalid x-api-key" from 14 Nov, 15:06 IST (the Markandeya\'s run stopped, nothing spent). No key in PowerShell or in Windows overrode .env; you put a new key in .env; the probe answered ($0.00002) | Done |\n| 15 Nov | The working English of the small texts and the Siddhanta Siromani | Queued by you: 17 jobs by Sonnet (1 running, 16 waiting) | They run one at a time |\n| 15 Nov | The Samaveda | The benchmark\'s pick: ours (the consensus misreads 0.29%); GRETIL\'s text agrees with it on F1 0.47 only, page by page: another recension | Its working English from ours |\n| 15 Nov | "authoritative genealogies of these kings with an easy intuitive ui/ux locally and online" | Read (agent 1): four layers of lineage that share no person key: the indexes\' lines (/vamsa here, /corpus/genealogies on the site), the Puranas\' dynasties (on the site only: the desk has no Dynasties page), exports\\kin_lineages.md, and RishiLineageChart.tsx (hard-coded, imported by nothing). The shelf: kin.db 23,295 relations (Purana Index 12,211, Sorensen 9,489, Vedic Index 1,595); vamsa.db checks 4,910 of the Purana Index\'s relations with both names in the cited verse; data\\vamsa_read 2,098 statements, 1,767 verified, read from the Visnu\'s 1910 Venkatesvara print (not Pathak\'s critical edition, which is here) and the Bhagavata; our entities 14,546 (persons 3,015), and 1,382 of them tied to more than one Sorensen entry (homonyms). The dynasties link to the index\'s persons, not back; Arjuna\'s line still runs through Vyasa, not Vicitravirya and Santanu; vamsa_read and vamsa_join are on no schedule | Next: G6 (below) |\n| 15 Nov | The Sanskrit texts of the genealogies | Read (agent 2), GRETIL\'s archive here, all IAST: the Ramayana (critical edition\'s numbering; Bala 69-70, Ayodhya 102), the Harivamsa (Vaidya\'s constituted text, BORI 1969), the Matsya (1-176 only), Brahmanda, Brahma, Linga, Kurma, Garuda, Agni, Markandeya (1-93), CC BY-NC-SA 4.0; the Mahabharata only as BORI\'s file "for reference purposes only" (no licence: counts and references, never its text on the site). Not in it: the Vayu, Padma, Bhavisya, Varaha, Brahmavaivarta. Chapters dense in kinship words (3.0 or more in 100): 9,290 verses in 197 chapters, without the false hits (4.0 or more: 6,260) | G6a, G6b |\n| 15 Nov | The evolution of the project | Traced (agent 3) from both git histories: the automaton 240 commits from 15 Feb (31 in June, 51 in August, 104 in October), Srangam 88 from 12 Jul; the phases, the aim\'s turns and the numbers now, in the brain document | Done |\n| 15 Nov | "ganita yuktibhasa scan repair seems to be stuck in a loop" | Found: the assessment counts the 227 pages vision has not read and offers --repair; --repair sent the scan to ocr_consensus.py with the triage\'s threshold of 72, which queues only the pages of low confidence, the 112 vision had read; the repair ran 4.5 seconds (13 Nov, job e1dee20b), read nothing, and the assessment asked again. Built REPAIR_LOOP_2026_11_15: when the assessment asks for the repair, every page is queued and vision skips those it read | Yours: the patch, then the repair (about $0.79) |\n| 15 Nov | The order of the genealogies\' work (G6) | Planned, priced: G6a (free) the work table of vamsa_read for these files (their verse marks differ: two levels, half-verses, the Ramayana without its marks, the Mahabharata in HTML); G6b (about $5 to $8 at G5a\'s $2.00 for 2,346 verses) the reading; G6c (free) the same dynasty aligned across the works, generation by generation: where they agree and differ is our correlation; G6d one person register (a stable id, the index entries, our entities, the dynasties\' persons and the claims tied to it, homonyms apart); G6e one page model here and on the site (a dynasty, a person, the evidence), the Dynasties page on the desk too; G6f our findings on a line (R1), approved by a person | Next |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | U1's second half, U2, U3; R1; kin-long; the Markandeya's 113; the Nirukta; load-js |\n",
     "| Next | U1's second half, U2, U3; R1; kin-long; the Markandeya's 113; the Nirukta; load-js |\n\n## 47. 15 Nov: the genealogies made one; the repair's loop (DOCS112_2026_11_15)\n\n| What | State |\n|---|---|\n| Verified | The new Claude key (the probe); 17 working-English jobs queued; the Samaveda's pick (ours, F1 0.47 with GRETIL's) |\n| The asks | docs\\ASKS_2026-10-22.md section 25 |\n| Built | REPAIR_LOOP_2026_11_15 (repair_text.repair_todo; --repair reads the pages the assessment counts); DOCS112 |\n| Measured | Four lineage layers, no shared person key; GRETIL here: 9,290 verses in genealogical chapters (density 3.0), 6,260 (4.0); the automaton's 240 commits since 15 Feb, Srangam's 88 since 12 Jul |\n| To do | the patches, run_tests, release; the Ganita's repair |\n| Next | G6a to G6f (the genealogies); R1; kin-long; U2, U3; the free prose view of the working English; prompt caching and the Batch API, measured first |\n")

edit('RUNBOOK.md', 1, '   run first). The Nirukta: its desk page (/desk/nirukta__w_gretil), Plan (free), Run, 250 verses a press.\n',
     '   run first). The Nirukta: its desk page (/desk/nirukta__w_gretil), Plan (free), Run, 250 verses a press.\n\n## 15 Nov: the repair\'s loop; the genealogies\' plan (DOCS112_2026_11_15)\n\ndocs\\ASKS_2026-10-22.md, section 25.\n\n1. The patches: `python scripts\\patch_repair_loop_2026_11_15.py --check`, then without; the same for\n   `patch_docs112_2026_11_15.py`; `python -m unittest tests.test_repair_loop_2026_11_15 tests.test_docs112_2026_11_15\n   tests.test_repair_next_2026_10_17 tests.test_repair_partial_2026_10_28`; `powershell -ExecutionPolicy Bypass -File\n   scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_repairloop_20261115.txt.\n2. The Ganita (repair_text.py runs afresh for each job: no restart is needed): `python scripts\\repair_text.py --doc\n   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V --repair --max-usd 1.00`. It says REPAIR_LOOP_2026_11_15 and "[2] vision\n   queued 339 | already done 112 | to run 227". Then `python scripts\\reingest_pages.py --doc\n   Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (the plan) and with `--apply`; its English and Hindi for the changed\n   passages; the benchmark again.\n3. The genealogies (G6): nothing to run yet; the plan is in section 25 of the register and in the brain document.\n')


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

