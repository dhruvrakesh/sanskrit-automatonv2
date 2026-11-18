#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs121_2026_11_18.py  (2026-11-18)  DOCS121_2026_11_18

18 Nov, evening: P1 and P2a released (ded5ed51); P2b built (the Srangam kit DYNASTIES_WORKS_2026-11-18: the Dynasties
page one work at a time, the 17 works named, a name in plain letters found) and the scheduled task's last step
(scripts\\patch_index_task_every_2026_11_18.py), beside this. Adds:

  docs/ASKS_2026-10-22.md    section 33: each ask, done or not, with its evidence
  docs/STATE_2026-10-18.md   section 55
  RUNBOOK.md                 "18 Nov, evening": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs121_<date> copies.

  python scripts\\patch_docs121_2026_11_18.py --check
  python scripts\\patch_docs121_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS121_2026_11_18'
TAG = 'docs121'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS120_2026_11_18', 'docs/STATE_2026-10-18.md': 'DOCS120_2026_11_18', 'RUNBOOK.md': 'DOCS120_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 18 Nov | Done in full? | No: P2b, P3, P4 (G6f with R1: a review list for the 44 proposed names and the 672 kept apart), P5 (ARCHITECTURE.md, the genealogies' road; I3) | In that order |\n",
     '| 18 Nov | Done in full? | No: P2b, P3, P4 (G6f with R1: a review list for the 44 proposed names and the 672 kept apart), P5 (ARCHITECTURE.md, the genealogies\' road; I3) | In that order |\n\n## 33. 18 Nov, evening: P1 and P2a released; P2b and the task\'s last step built (DOCS121_2026_11_18)\n\nAsked on 18 Nov, 17:19, with three CSV exports of the Lovable Cloud SQL editor (16:18 and 17:18) and three screens\n(15:45 to 17:1x), the standing ask again ("are we done in full? ... a layperson\'s one pager ... proceed with pending\nwork"). Read on the PC, read only: the release log, Srangam\'s CorpusDynasties.tsx, indexSite.ts and dynasties.test.tsx\n(main at eae2901), scripts\\corpus_mirror_task.ps1. Built and tested on copies; nothing on the PC was run.\n\n**Done in full? No.** Released by you: P1 and P2a. Built tonight: P2b (the Srangam kit) and the scheduled task\'s last\nstep. Not built: P2c (a way in by vamsa across the works), P3, P4, P5.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 18 Nov | The release of P1, P2a, DOCS120 | Done by you: ded5ed51 pushed (b956084..ded5ed5, 17 files; "verified: origin/main == local HEAD (ded5ed51)"); it carried data\\vamsa_read\\register.json | Done |\n| 18 Nov | P2a, measured on the PC | Your screens: vamsa_join --work every, "500 lines of 3 persons or more joined to the Purana Index"; index_sync --dynasty-works every --dump: dynasties 517 (0.9 MB), 5,565,024 bytes; the default dump: dynasties 106 (0.2 MB), 5,458,038 bytes, as the baseline | Done |\n| 18 Nov | The site\'s dynasty rows | Your SQL of 17:18, by row size: vip4 50 rows, 64 kB; bhp9 48 rows, 53 kB; bhp12 8 rows, 6,400 bytes (last sent 13 Nov); unchanged since the baseline | Done |\n| 18 Nov | The Claude credit | Your report: $103.71 spent of $173.93 (8,799 calls), $70.22 left, to 11 Dec. Translation: 3,158 calls, $49.30 at 11:33; 7,373 calls, $68.16 at 16:33 ($18.86 in five hours) | Watch: at that pace the credit lasts about 19 hours of translating |\n| 18 Nov | I1, the first call | Your SQL of 17:1x: still no row for detect-duplicate-articles or suggest-tag-categories | You: "suggest categories" once |\n| 18 Nov | Two CSV exports of 16:18 | They report weekly-export-ci-push and dkseams-export-ci-push (op-br-1.1): the DK-SEAMS work, not this project\'s; nothing here acts on them | None here |\n| 18 Nov | P2b, the Srangam kit | Built: docs\\srangam\\DYNASTIES_WORKS_2026-11-18 and scripts\\patch_srangam_dynasties_works_2026_11_18.py: the Dynasties page asks for one work\'s lines at a time (loadDynasties(work), kept 10 minutes), not every work\'s at once; its buttons name the 17 works; "No dynasty of this text has been sent from the desk yet."; a name typed in plain letters is found (foldPlain, the desk\'s rule); RELIABILITY_AUDIT Phase AT, invariant 70. Its first view asks for vip4\'s 50 rows (64 kB) where it asked for all 106 (123 kB) | You: the kit, typecheck, vitest, build, push, Publish |\n| 18 Nov | P2b, tested | tests\\test_srangam_dynasties_works_2026_11_18.py: 6 tests OK (the payload, the patch on a made-up checkout, a changed file refused); the patch on copies of main\'s files: 5 files written, the second run does nothing; TypeScript\'s typecheck (tsconfig.app.json) of a copy of src with the kit: no error in the kit\'s files (one, in reference-sections.test.ts, came of the copy lacking supabase\\). Not run here: vitest, build (your node_modules) | Your vitest and build |\n| 18 Nov | The scheduled task\'s last step | Built: scripts\\patch_index_task_every_2026_11_18.py (corpus_mirror_task.ps1: index_sync.py --apply --if-configured --dynasty-works every; refused unless index_sync.py has VAMSA_SITE_2026_11_18); tests\\test_index_task_every_2026_11_18.py: 3 tests OK | Apply only after Publish, in the same sitting as the first send with every |\n| 18 Nov | Done in full? | No: the send of every (after Publish), P2c (each line tagged with its dynasty and vamsa on the desk, then a way in by Suryavamsa and Candravamsa), P3 (the desk\'s Vamsa page), P4 (G6f with R1), P5 (ARCHITECTURE.md) | In that order |\n')

edit('docs/STATE_2026-10-18.md', 1, '| Next | P2b (the Srangam kit: one work at a time); then every sent; P3; P4; P5 |\n',
     "| Next | P2b (the Srangam kit: one work at a time); then every sent; P3; P4; P5 |\n\n## 55. 18 Nov, evening: P2b and the task's last step built (DOCS121_2026_11_18)\n\n| What | State |\n|---|---|\n| Verified | ded5ed51 released (P1, P2a); the dumps (every 517 dynasty rows, default 106); on copies: the kit (6 tests, the typecheck), the task patch (3 tests) |\n| The asks | docs\\ASKS_2026-10-22.md section 33 |\n| Built | docs\\srangam\\DYNASTIES_WORKS_2026-11-18 with scripts\\patch_srangam_dynasties_works_2026_11_18.py (P2b); scripts\\patch_index_task_every_2026_11_18.py; DOCS121 |\n| Measured | Claude credit $70.22 left, translation $18.86 in five hours; the site's dynasty rows unchanged (106) |\n| Not verified | vitest and the build with the kit; the two AI functions' first call; corpus.reader_access's mode |\n| To do | the kit, Publish; then the task patch and the first send with every, in one sitting |\n| Next | P2c; P3; P4; P5 |\n")

edit('RUNBOOK.md', 1, '4. In the Lovable Cloud SQL editor, read only: the mode of corpus.reader_access and the count of corpus.readers.\n',
     "4. In the Lovable Cloud SQL editor, read only: the mode of corpus.reader_access and the count of corpus.readers.\n\n## 18 Nov, evening: P2b, the site's page one work at a time; then every work sent (DOCS121_2026_11_18)\n\ndocs\\ASKS_2026-10-22.md, section 33. In this order:\n\n1. The desk (automaton root): `python scripts\\patch_docs121_2026_11_18.py --check`, then without; `python -m unittest\n   tests.test_srangam_dynasties_works_2026_11_18 tests.test_index_task_every_2026_11_18 tests.test_docs121_2026_11_18`;\n   release.ps1 with COMMIT_MSG_dynworks_20261118.txt (the dry run, then -Apply once).\n2. Srangam (D:\\srangam-42267): `git pull`; the kit's patch with --check, then without; `npm run typecheck`;\n   `npx vitest run src/__tests__/dynasties.test.tsx src/__tests__/dynasties-works.test.tsx`; `npx vitest run`;\n   `npm run build`; commit and push the five files; Publish in Lovable.\n3. Only when the published page shows the 17 texts' buttons: on the desk, `python scripts\\patch_index_task_every_2026_11_18.py\n   --check`, then without; `python scripts\\index_sync.py --dynasty-works every` (the plan), then\n   `python scripts\\index_sync.py --dynasty-works every --apply`; the SQL of section 33 again (17 works, 517 rows).\n")


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

