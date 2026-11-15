#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs113_2026_11_15.py  (2026-11-15)  DOCS113_2026_11_15

Nothing paid for is dropped (REINGEST_KEEP: a repaired reading keeps the translations of the sentences that are the same
but for their letters), the pick when the repair is made, local first (every text read whole on this PC), the brain's
five layers, a page for the team. This patch adds:

  docs/ASKS_2026-10-22.md    section 26: each ask of 15 Nov (afternoon), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 48
  RUNBOOK.md                 "15 Nov, afternoon": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs113_<date> copies.

  python scripts\\patch_docs113_2026_11_15.py --check
  python scripts\\patch_docs113_2026_11_15.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS113_2026_11_15'
TAG = 'docs113'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS112_2026_11_15', 'docs/STATE_2026-10-18.md': 'DOCS112_2026_11_15', 'RUNBOOK.md': 'DOCS112_2026_11_15'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 15 Nov | The order of the genealogies' work (G6) | Planned, priced: G6a (free) the work table of vamsa_read for these files (their verse marks differ: two levels, half-verses, the Ramayana without its marks, the Mahabharata in HTML); G6b (about $5 to $8 at G5a's $2.00 for 2,346 verses) the reading; G6c (free) the same dynasty aligned across the works, generation by generation: where they agree and differ is our correlation; G6d one person register (a stable id, the index entries, our entities, the dynasties' persons and the claims tied to it, homonyms apart); G6e one page model here and on the site (a dynasty, a person, the evidence), the Dynasties page on the desk too; G6f our findings on a line (R1), approved by a person | Next |\n",
     '| 15 Nov | The order of the genealogies\' work (G6) | Planned, priced: G6a (free) the work table of vamsa_read for these files (their verse marks differ: two levels, half-verses, the Ramayana without its marks, the Mahabharata in HTML); G6b (about $5 to $8 at G5a\'s $2.00 for 2,346 verses) the reading; G6c (free) the same dynasty aligned across the works, generation by generation: where they agree and differ is our correlation; G6d one person register (a stable id, the index entries, our entities, the dynasties\' persons and the claims tied to it, homonyms apart); G6e one page model here and on the site (a dynasty, a person, the evidence), the Dynasties page on the desk too; G6f our findings on a line (R1), approved by a person | Next |\n\n## 26. 15 Nov, afternoon: nothing paid for is dropped; a page for the team (DOCS113_2026_11_15)\n\nAsked on 15 Nov, 12:42, with the Ganita\'s reingest plan (178 of 339 pages changed, 1,838 English and 1,837 Hindi to go)\nand its refusal: "i am tired of wasting out APIs on translating works that you then make me drop ... stop worrying\nabout license etc. this is first a local only study project. are we done in full? give me a layperson\'s one pager for\nmy erp team so that they can use the features developed over the past 2-3 days". Read from the output pasted, the\npage files of the Ganita (Tesseract\'s, vision\'s, the merged), the backup of 15 Nov (immutable) and reingest_pages.py.\n\n**Done in full? No.** The repair of the Ganita is made and waits to go into the database, now without losing half of\nits translations; the genealogies\' reading (G6a, G6b) is the next build; R1, kin-long, U2 and U3 follow.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 15 Nov | "tired of wasting our APIs on translating works that you then make me drop" | Found: reingest_pages.py matched a passage only by its exact text, so a sentence mended by one letter was deleted with its English, Hindi, vector and reviews. On the Ganita the repair reads the grammar\'s marks Tesseract lost (page 66: gunakaram for gunakara, adyakhandena for adyakhandana) and Tesseract\'s noise in the Devanagari falls from 4.5% to 0.2%. Built REINGEST_KEEP_2026_11_15: with --keep (0.9), a new passage and one that would go, on the same page, whose Devanagari letters agree at nine tenths or more, are one passage: the row stays with its translations, pictures and stories and takes the mended text. Measured on the backup of 15 Nov: English lost 914 in place of 1,838, Hindi 913 in place of 1,837, 971 passages mended in place, 813 new in place of 1,784; what is left in the database is still what a full ingest of the repair makes (tested). The plan says what --keep would keep; without --keep nothing changes; the log keeps the reading each kept translation was made from | Yours: the patch; the plan with --keep; then --apply |\n| 15 Nov | What the Ganita\'s working translations cost | The meter: $2.83 by gemini-2.5-flash for its English and Hindi (5,036 calls, 3 Oct to 14 Nov), $0.60 by Sonnet (93), $0.54 the judge; its vision reading $0.39 before today. The edition (about $65 to $230) is not begun: the reading is settled before it, so that it is made once | - |\n| 15 Nov | The pick said "repair it first" after the repair | Found: pick_reading looked only at the count of Latin letters (1.53%, moderate), which in this edition is partly its own English (the introduction, the glossary of technical terms: Celestial, Rsine, Circle). Mended: when vision has read four fifths of the scan, the pick says to bring the repair into the database (with --keep), or that the text is ready | With the patch |\n| 15 Nov | "stop worrying about license etc. this is first a local only study project" | Settled: on this PC every text is read and used whole. The Harivamsa is read as the other GRETIL texts; the Mahabharata\'s Adiparvan genealogies (1.59-61, 1.89-92 and the others dense in kinship) are read whole, with their words. What the site shows of them is decided when the pages are built (G6e), not before | G6a, G6b next |\n| 15 Nov | "is our sanskritic brain a giant db file?" | Answered: five layers: the working database (data\\context.db, 2.4 GB: 87 texts, 212,745 passages, 30,428 in English), the shelf (kin.db, claims.db, vamsa.db), the evidence on disk (scans, readings, stored replies), the cloud mirror behind Srangam, and the brain document | Done |\n| 15 Nov | "a layperson\'s one pager for my erp team" | Written as a Claude document: what is new on the site and on the desk (11 to 15 Nov), how to make a readable edition, three rules that stop waste, what is not ready | Done |\n| 15 Nov | The Ganita\'s repair | Run by you: vision read the pages it had not (290 of 339 now; some failed twice and keep Tesseract\'s). The reingest was refused, rightly, without --replace | Yours: with --keep |\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | G6a to G6f (the genealogies); R1; kin-long; U2, U3; the free prose view of the working English; prompt caching and the Batch API, measured first |\n',
     "| Next | G6a to G6f (the genealogies); R1; kin-long; U2, U3; the free prose view of the working English; prompt caching and the Batch API, measured first |\n\n## 48. 15 Nov, afternoon: nothing paid for is dropped (DOCS113_2026_11_15)\n\n| What | State |\n|---|---|\n| Verified | The release of REPAIR_LOOP and DOCS112 (15 Nov); the Ganita's repair read the unread pages (vision 290 of 339) |\n| The asks | docs\\ASKS_2026-10-22.md section 26 |\n| Built | REINGEST_KEEP_2026_11_15 (reingest_pages.py --keep; the pick when the repair is made); DOCS113 |\n| Measured | The Ganita with --keep 0.9: 971 passages mended in place; English lost 914 of 1,838, Hindi 913 of 1,837; new 813 of 1,784 |\n| Decided | Local first: every text read whole on this PC (the Harivamsa, the Adiparvan's genealogies) |\n| To do | the patch, run_tests, release; the Ganita: the plan with --keep, --apply, its 813 new passages, its edition |\n| Next | G6a, G6b (the genealogies' reading); R1; kin-long; U2, U3; the free prose view of the working English |\n")

edit('RUNBOOK.md', 1, '3. The genealogies (G6): nothing to run yet; the plan is in section 25 of the register and in the brain document.\n',
     "3. The genealogies (G6): nothing to run yet; the plan is in section 25 of the register and in the brain document.\n\n## 15 Nov, afternoon: a repaired reading keeps its translations (DOCS113_2026_11_15)\n\ndocs\\ASKS_2026-10-22.md, section 26. From the automaton's root:\n\n1. The patches: `python scripts\\patch_reingest_keep_2026_11_15.py --check`, then without; the same for\n   `patch_docs113_2026_11_15.py`; `python -m unittest tests.test_reingest_keep_2026_11_15 tests.test_reingest_2026_10_12\n   tests.test_source_pick_2026_11_13 tests.test_mbh_prose_2026_10_14 tests.test_docs113_2026_11_15`; `powershell\n   -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_reingestkeep_20261115.txt.\n2. The Ganita: `python scripts\\reingest_pages.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V --keep` (the plan,\n   free: about 971 mended in place, English lost about 914); then its NEXT line (`--keep --apply --replace` and the\n   number it prints). A backup is made first; what goes is written to data\\reingest.\n3. `python scripts\\text_path.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V --write` and\n   `python scripts\\benchmark_sources.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (free: the pick says ready).\n4. Its new passages' English (about 813) by Sonnet through the dashboard (`/api/translate`, engine\n   anthropic:claude-sonnet-5-5, limit 0); its Hindi by flash when Google's cap allows.\n5. Its edition: 40 verses first from its desk page (Plan, Run), then presses of 250.\n")


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

