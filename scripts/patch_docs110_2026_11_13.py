#!/usr/bin/env python3
# -*- coding: ascii -*-
"""



patch_docs110_2026_11_13.py  (2026-11-13)  DOCS110_2026_11_13

The best reading for each text (SOURCE_PICK), the Surya Siddhanta and the Ganita Yuktibhasa, the dynasties live, the
Gandharva's English whole, Mallapurana's edition begun. This patch adds:

  docs/ASKS_2026-10-22.md    section 23: each ask of 13 Nov (evening), done or not, with its evidence
  docs/STATE_2026-10-18.md   section 45
  RUNBOOK.md                 "13 Nov, evening": the commands in order

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_docs110_<date> copies.

  python scripts\\patch_docs110_2026_11_13.py --check
  python scripts\\patch_docs110_2026_11_13.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS110_2026_11_13'
TAG = 'docs110'
FILES = ['docs/ASKS_2026-10-22.md', 'docs/STATE_2026-10-18.md', 'RUNBOOK.md']
NEEDS = {'docs/ASKS_2026-10-22.md': 'DOCS109_2026_11_13', 'docs/STATE_2026-10-18.md': 'DOCS109_2026_11_13', 'RUNBOOK.md': 'DOCS109_2026_11_13'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/ASKS_2026-10-22.md', 1, "| 13 Nov | R1, kin-long, the credit's steps 4 to 7 | Not begun: the two faults above came first | Next: R1 (about $1 to $3 of the credit); kin-long (about $1 to $2 of Google's cap) |\n",
     '| 13 Nov | R1, kin-long, the credit\'s steps 4 to 7 | Not begun: the two faults above came first | Next: R1 (about $1 to $3 of the credit); kin-long (about $1 to $2 of Google\'s cap) |\n\n## 23. 13 Nov, evening: the best reading for each text; the Surya and the Ganita first (DOCS110_2026_11_13)\n\nAsked on 13 Nov, evening, with A2 exported, the release of DOCS109, the dashboard\'s restart, the Gandharva\'s run,\nindex_sync\'s send, the Dynasties page on the site and Mallapurana\'s first press: "are we able to choose the best\navailable from etext and our own ocr+vision text for translation and then get to the scholarly prose and edition for\neach. Ganita Yuktibhasa and Surya Siddhanta are on the top of our list", with the asks of 11 and 13 Nov again. Read from\nthe exports, the screenshots, data\\jobs.jsonl, data\\text_path.json, data\\source_verdicts.jsonl, data\\witnesses.jsonl,\ndata\\benchmarks, GRETIL\'s archive here (sources\\gretil\\1_sanskr.zip) and the backup of 13 Nov (read immutable).\n\n**Done in full? No.** The dynasties are live and the Gandharva\'s English is whole; the choice of reading is now made by\nthe benchmark and shown on the desk (SOURCE_PICK), but the Surya\'s flagged verses, the Ganita\'s repair and its edition,\nMallapurana\'s edition (begun), R1, kin-long and the readers\' pages (U1 to U3) are ahead.\n\n| Date | Ask | Done (the evidence) | Left (its state) |\n|---|---|---|---|\n| 13 Nov | "are we able to choose the best available from etext and our own ocr+vision text ... then get to the scholarly prose and edition for each" | Partly, before today. Within a scan, yes: the repair merges Tesseract and vision page by page (the consensus). Between a scan and an e-text, no: the e-text is kept as its own text (a witness, as jyotish_surya_siddhanta__w_etext), benchmark_sources.py measured both (letters misread, F1 page by page, aksharas agreeing) and named no reading to use, and the desk did not say. Built SOURCE_PICK_2026_11_13: the benchmark picks the reading for the scholarly English and its prose (the e-text when it is the same text as ours, F1 at least 0.6, and misreads no more; else ours, ready when its misreading is cosmetic, else after its repair), keeps it in the text\'s file in data\\benchmarks, prints PICK:, and the text\'s desk page shows it with a link to the text picked. A person confirms | Yours: the patch; the benchmarks of the two texts (free) |\n| 13 Nov | The Surya Siddhanta | Two readings here. The e-text (jyotish_surya_siddhanta__w_etext, 503 passages): its working English 503 and Hindi 503 (today, job 4b3cffe3), released; its scholarly English made for all 502 verses (the latest of each: 415 passed, 94 flagged, 1 source doubt), so its edition and its prose are there (/scholar/jyotish_surya_siddhanta__w_etext/prose; on the site /corpus/jyotish_surya_siddhanta__w_etext/prose). The scan (jyotish_surya_siddhanta, 55 pages, 58 passages) is in repair since today. A third, the Kashi Sanskrit Series edition, is one PDF in the inbox, not read | Yours: the benchmark (free); the 95 not passed sorted for a person (triage, free); the serious read again by Opus, as the SOP of 16 Oct says (its dry run prices it: about $3 to $9) |\n| 13 Nov | The Ganita Yuktibhasa | No e-text of it here: GRETIL\'s archive on this PC has Bhaskara\'s Bijaganita, not the Yuktibhasa. Its scan (339 pages) is read by Tesseract in the database (1.84% of the letters misread: moderate); vision has read 112 of its 339 pages; its working English 2,266 of 2,443 passages, Hindi 2,235; no scholarly English. The plan of 12 Nov: 1,795 verses ready, the rest left out as debris | Yours: the benchmark (free; it will say repair first); the repair (vision on the other pages, about $1.2 to $2 of Google\'s cap); then its scholarly English, 1,795 to 2,440 verses at about $0.036 a verse: about $65 to $88, in presses of 250 |\n| 13 Nov | The dynasties | Live: corpus-index deployed by Lovable; index_sync sent 114 rows, the site\'s genealogies equal the desk\'s (9 tables); A2: vip4 54 lines (the longest 29), bhp9 50 (27), bhp12 7 (10); the page at /corpus/genealogies/dynasties shows them (your screenshots) | Done |\n| 13 Nov | The Gandharva English | The rest by Sonnet after BANNER_HEAD (job c2c25e26, 2 h 31 min): 499 of 501, 4 left by the quality check, 2 empty answers; its English now 878 of 884 passages | The chart again (`text_path.py` was typed as "text_path.pycls" and did not run) |\n| 13 Nov | Mallapurana\'s edition | Begun by you from its desk page: a press of 250 verses (10.2 to 70.2), at most $11.33; the plan measured $0.036 a verse ($9.06 for 250) on 4,983 verses of scholar-v2.1, and left out 63 passages of noise or front matter, 18 with OCR debris and 7 with fewer than 8 Devanagari signs | Yours: the next presses (about 720 verses, about $26) |\n| 13 Nov | The order of the credit ($167.73 left, 13 Nov) | The Surya\'s flagged verses (about $3 to $9); the Ganita\'s edition after its repair (about $65 to $88); Mallapurana\'s edition (about $26 more); R1 (about $1 to $3); the Markandeya\'s 113 (about $3 to $5); the Nirukta (about $16 to $28) if the credit holds | Yours: the order |\n| 13 Nov | Readers and makers who are not technical (U1 to U3); R1; kin-long | Not begun | Next |\n')

edit('docs/STATE_2026-10-18.md', 1, "| Next | U1 to U3 (for amateur readers and makers); R1; kin-long; the credit's steps 4 to 6 at the measured price; Mallapurana's edition when you choose; load-js |\n",
     '| Next | U1 to U3 (for amateur readers and makers); R1; kin-long; the credit\'s steps 4 to 6 at the measured price; Mallapurana\'s edition when you choose; load-js |\n\n## 45. 13 Nov, evening: the best reading for each text (DOCS110_2026_11_13)\n\n| What | State |\n|---|---|\n| Verified | The release of DOCS109 (5284a25, pushed); the dashboard restarted (13:47 IST); corpus-index deployed; index_sync: 114 dynasties sent, 9 tables equal; A2 as expected; the Dynasties page live; the Gandharva\'s 499 of 501 |\n| The asks | docs\\ASKS_2026-10-22.md section 23 |\n| Built | SOURCE_PICK_2026_11_13 (benchmark_sources.pick_reading, PICK: and "pick" in data\\benchmarks; translation_desk.pick_of; the desk\'s line); DOCS110 |\n| Measured | The Surya\'s e-text: 502 verses with a scholarly English (415 passed, 94 flagged, 1 doubt). The Ganita: no e-text here; Tesseract 1.84% misread; vision 112 of 339 pages |\n| To do | the patches, run_tests, release; `text_path.py`; the two benchmarks; the Surya\'s flagged verses; the Ganita\'s repair, then its edition; Mallapurana\'s next presses |\n| Next | U1 to U3; R1; kin-long; the Markandeya\'s 113; the Nirukta; load-js |\n')

edit('RUNBOOK.md', 1, '   then "Run"; again until done; then "As prose".\n',
     '   then "Run"; again until done; then "As prose".\n\n## 13 Nov, evening: the best reading for each text; the Surya and the Ganita (DOCS110_2026_11_13)\n\ndocs\\ASKS_2026-10-22.md, section 23. From the automaton\'s root:\n\n1. The patches: `python scripts\\patch_source_pick_2026_11_13.py --check`, then without; the same for\n   `patch_docs110_2026_11_13.py`; `python -m unittest tests.test_source_pick_2026_11_13 tests.test_banner_head_2026_11_13\n   tests.test_bench_letters_2026_10_22 tests.test_docs110_2026_11_13`; `powershell -ExecutionPolicy Bypass -File\n   scripts\\run_tests.ps1`; release.ps1 with COMMIT_MSG_sourcepick_20261113.txt. The dashboard restarted when no job runs.\n2. `python scripts\\text_path.py` (every text charted again, free).\n3. The benchmarks (free): `python scripts\\benchmark_sources.py --doc jyotish_surya_siddhanta` and\n   `python scripts\\benchmark_sources.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`; each ends with PICK:, and the\n   text\'s desk page shows it.\n4. The Surya: `python scripts\\scholar_translate.py --doc jyotish_surya_siddhanta__w_etext --engine\n   anthropic:claude-sonnet-5-5 --triage` (free: exports\\scholar_triage_jyotish_surya_siddhanta__w_etext.csv, the 95 not\n   passed); then, as on 16 Oct, `--engine anthropic:claude-opus-5-5 --only-flagged anthropic:claude-sonnet-5-5 --serious\n   --compare-engine anthropic:claude-sonnet-5-5 --audit-every 1` (a dry run first; then `--yes --max-usd 9`).\n5. The Ganita: `python scripts\\repair_text.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V` (free: the price), then\n   its `--repair --max-usd` as it says; when the repair is released, its edition from /desk/Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V\n   in presses of 250.\n6. Mallapurana: the next presses from /desk/Mallapurana; then "As prose".\n')


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

