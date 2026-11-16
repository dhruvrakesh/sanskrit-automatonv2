#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs114_2026_11_15.py  (2026-11-15)  DOCS114_2026_11_15

The genealogies' texts taught to the reader (VAMSA_G6A: fourteen works of GRETIL's archive beside G5a's three), the cut
measured (9,029 verses in 154 chapters), the release of REINGEST_KEEP verified, the Ganita after its repair, and the
commands of a trial reading. This patch adds:

  docs/ASKS_2026-10-22.md    section 27: each ask of 15 Nov (evening), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 49
  RUNBOOK.md                 "15 Nov, evening": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs114_<date> copies.

  python scripts\\patch_docs114_2026_11_15.py --check
  python scripts\\patch_docs114_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS114_2026_11_15'
TAG = 'docs114'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS113_2026_11_15', 'docs/STATE_2026-10-18.md': 'DOCS113_2026_11_15', 'RUNBOOK.md': 'DOCS113_2026_11_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 15 Nov | The Ganita's repair | Run by you: vision read the pages it had not (290 of 339 now; some failed twice and keep Tesseract's). The reingest was refused, rightly, without --replace | Yours: with --keep |\n",
     '| 15 Nov | The Ganita\'s repair | Run by you: vision read the pages it had not (290 of 339 now; some failed twice and keep Tesseract\'s). The reingest was refused, rightly, without --replace | Yours: with --keep |\n\n## 27. 15 Nov, evening: the genealogies\' texts taught to the reader (DOCS114_2026_11_15)\n\nAsked on 15 Nov, 16:57, with the screen of the release, the Ganita\'s chart and its benchmark: "build G6a: teach\nscripts\\vamsa_read.py the genealogical chapters of the Harivamsa, the Ramayana, the Mahabharata\'s Adiparvan and the\nPuranas listed in the handover, tested, with the commands for me to run a trial reading". Read from the handover of\n15 Nov, sections 25 and 26 here, GRETIL\'s archive on this PC (sources\\gretil\\1_sanskr.zip, read only), .git\\logs\\HEAD\n(by Python; no git was run) and data\\reingest. The database was not opened.\n\n**Done in full? Yes for G6a** (built, tested, free). The reading itself (G6b) is yours to start with the trial below;\nG6c to G6f follow it.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 15 Nov | The release of REINGEST_KEEP and DOCS113 (the screen: "nothing to commit, working tree clean", "FAIL: git commit failed") | Read: main\'s last commit in .git\\logs\\HEAD is "A repaired reading keeps the translations of its mended sentences" (b391f48). The release had been made; the screen is release.ps1 run again with nothing left to commit | Done |\n| 15 Nov | The Ganita Yuktibhasa after its repair | Read: data\\reingest says "applied" at 13:20:49 (971 passages mended in place, 813 new, 946 gone). Your screen: text_path charted it again at 16:34 (English 1,352 and Hindi 1,352 of 2,315 passages; next: translate, about $22.41 by its own estimate); the benchmark\'s pick says "ready for its scholarly English and its prose" | Yours: its 963 passages without English, then its edition (40 verses first) |\n| 15 Nov | "teach scripts\\vamsa_read.py the genealogical chapters" | Built VAMSA_G6A_2026_11_15: fourteen works beside G5a\'s three (G6_WORKS): hv, ram1, ram2, matsya, bndp1, bndp2, brahma, linga1, kurma1, garuda1, agni, markp, mbh1, vipc4 (the Visnu\'s book 4 in Pathak\'s critical edition), with the handover\'s chapters. Each work says how its verse mark is written; verses_g6() cuts it: two numbers (HV_9.1, MatsP_12.1, BrP_13.1, markp_52.1), no closing mark (the Ramayana\'s R_2,102.001, LiP_1,66.1), half-verses joined (ap_272.001ab and cd), the Mahabharata\'s lines (01,089.001a, a TAB, a pada: the padas of one number are one verse; the lines with * or @ and the speakers\' lines are left out), prose marks (the critical Visnu\'s and the Brahma\'s) | Yours: the patch |\n| 15 Nov | The cut, measured on GRETIL\'s files here (free) | 9,029 verses in 154 chapters, 248 chapter parts, about 902,000 characters: hv 816, ram1 299, ram2 31, matsya 1,024, bndp1 503, bndp2 2,080, brahma 937, linga1 649, kurma1 552, garuda1 456, agni 290, markp 134, mbh1 629, vipc4 629. Taken out: colophons, chapter headings, the Agni\'s footnotes and page marks, star passages. Mended: a chapter\'s number misprinted in a mark (ap_273.001cd inside chapter 274; BrP_7.3 inside chapter 77). Kept apart: a number given to two verses (ViP_4,3.20 twice: 20 and 20b). Twelve chapters have a gap in their numbers that is the file\'s own (--verses lists them); GRETIL\'s Brahmanda 2,70 has two verses ("verses 2,70.3 - 49 not available at present") | Not verified: no verse of these works has been read by Claude yet; the handover\'s count (9,290 verses in 197 chapters) was of every dense chapter, this is of the chapters it lists |\n| 15 Nov | What the reading would cost (G6b) | The plan\'s estimate: about $8.26 for the fourteen works (a guess from the characters; at G5a\'s measured $2.00 for 2,346 verses it is about $7.70). The dearest: bndp2 $1.72, hv $1.01, vipc4 $0.93, matsya $0.85 | G6b: a trial first |\n| 15 Nov | The site and the old readings | --work all is still G5a\'s three works; vamsa_join and index_sync read VR.WORKS, which is unchanged, so nothing of G6 reaches the site\'s Dynasties page (tested: a reading of the Harivamsa alone gives the site nothing). vip4, bhp9 and bhp12 are cut as before (their stored readings are not read again); the prompt and the checks are the same | G6e decides what the site shows |\n| 15 Nov | "the commands for me to run a trial reading" | In RUNBOOK ("15 Nov, evening"): the plan, --show and --verses (free), then the Harivamsa 9-10 (Manu\'s sons, the Iksvakus: about $0.23) and the Mahabharata 1.90 (Puru\'s line to Janamejaya in prose, where Arjuna\'s line runs through Vicitravirya and Santanu: about $0.07) | Yours |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | G6a, G6b (the genealogies' reading); R1; kin-long; U2, U3; the free prose view of the working English |\n",
     "| Next | G6a, G6b (the genealogies' reading); R1; kin-long; U2, U3; the free prose view of the working English |\n\n## 49. 15 Nov, evening: the genealogies' texts taught to the reader (DOCS114_2026_11_15)\n\n| What | State |\n|---|---|\n| Verified | The release of REINGEST_KEEP and DOCS113 (b391f48 in .git\\logs\\HEAD); the Ganita's reingest applied (971 mended, 813 new); its pick: ready |\n| The asks | docs\\ASKS_2026-10-22.md section 27 |\n| Built | VAMSA_G6A_2026_11_15 (vamsa_read.py: G6_WORKS, verses_g6, --work g6, --show, --verses); DOCS114 |\n| Measured | 9,029 verses in 154 chapters of fourteen works, 248 parts; the estimate $8.26 (about $7.70 at G5a's rate); twelve chapters with a gap that is the file's own |\n| Not verified | No verse of the new works read by Claude yet (G6b's trial is the first) |\n| To do | the patches, the tests, run_tests, release; the trial (the Harivamsa 9-10, the Mahabharata 1.90) |\n| Next | G6b (the reading, after the trial), G6c to G6f; R1; kin-long; U2, U3; the free prose view of the working English |\n")

edit('RUNBOOK.md', 1, '5. Its edition: 40 verses first from its desk page (Plan, Run), then presses of 250.\n',
     '5. Its edition: 40 verses first from its desk page (Plan, Run), then presses of 250.\n\n## 15 Nov, evening: the genealogies\' texts taught to the reader (DOCS114_2026_11_15)\n\ndocs\\ASKS_2026-10-22.md, section 27. From the automaton\'s root:\n\n1. The patches: `python scripts\\patch_vamsa_g6a_2026_11_15.py --check`, then without; the same for\n   `patch_docs114_2026_11_15.py`; `python -m unittest tests.test_vamsa_g6a_2026_11_15 tests.test_vamsa_read_2026_11_11\n   tests.test_vamsa_join_2026_11_11 tests.test_docs114_2026_11_15`; `powershell -ExecutionPolicy Bypass -File\n   scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_vamsag6a_20261115.txt.\n2. Free, nothing sent: `python scripts\\vamsa_read.py --work g6` (the plan: fourteen works, 248 parts, about $8.26);\n   `python scripts\\vamsa_read.py --work g6 --verses` (each chapter\'s verses and the gaps in their numbers);\n   `python scripts\\vamsa_read.py --work hv --chapters 9 --show 12` and\n   `python scripts\\vamsa_read.py --work mbh1 --chapters 90 --show 12` (the verses as they would be sent).\n3. The trial (the Claude credit, about $0.30 in all): `python scripts\\vamsa_read.py --work hv --chapters 9-10 --yes\n   --max-usd 0.50`, then `python scripts\\vamsa_read.py --work mbh1 --chapters 90 --yes --max-usd 0.50`.\n4. What it found (free): `python scripts\\vamsa_read.py --work hv --report` and\n   `python scripts\\vamsa_read.py --work mbh1 --report` (the counts by check, the longest father-to-son lines;\n   exports\\vamsa_read_hv.csv, exports\\vamsa_lines_hv.csv and the same for mbh1). A good trial: three statements in\n   four or more "verified" (G5a\'s first run: 1,449 of 1,975).\n5. The rest, when the trial reads well (G6b): `python scripts\\vamsa_read.py --work g6 --yes --max-usd 9`; it reads only\n   what is not read yet and stops at the cap. `--work all` is still G5a\'s three works, and nothing of G6 goes to the\n   site.\n')


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

