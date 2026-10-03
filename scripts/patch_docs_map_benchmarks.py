#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs_map_benchmarks.py  (2026-10-02)  DOCS_MAP_2026_10_02

Docs only. All-or-nothing across two files, marker-idempotent, backups, atomic.

RUNBOOK.md section 0 (documentation map):
  * adds the dated design/state documents written since 2026-09-06, which the map
    did not list (an operator reading section 0 could not find them);
  * marks the "keep both in sync (section 6)" sentence as superseded by
    SOURCES_OF_TRUTH.md rule 2 (section 6 itself was marked on 2026-09-30).
BENCHMARKS.md: appends the dated measurements of 2026-10-01/02 (OCR consensus
  on Mallapurana, the Hindi lacuna census, the reference A/B), because the
  map says BENCHMARKS is where dated baselines live.

  python scripts/patch_docs_map_benchmarks.py --check
  python scripts/patch_docs_map_benchmarks.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS_MAP_2026_10_02"
RB, BM = Path("RUNBOOK.md"), Path("BENCHMARKS.md")
ROW_PREFIX = "| `QUALITY_METHODOLOGY.md` |"
SYNC_OLD = "keep both in sync (\u00a76)."
SYNC_NEW = ("keep both in sync (\u00a76). **Superseded 2026-09-30:** SOURCES_OF_TRUTH.md rule 2 - "
            "the symphony repo holds cross-project docs only; release this repo with \u00a76b. "
            "(" + MARK + ")")
NEW_ROWS = [
    "| `docs/ENTERPRISE_PATH_2026-09-06.md` | Measured state and ordered plan as of 2026-09-06 | planning (read with ENTERPRISE_ROADMAP) |",
    "| `docs/RETIREMENT_AND_BACKUP_POLICY_2026-09-14.md` | retire_doc / graft_verses / backup policy | before retiring or grafting a doc |",
    "| `docs/OPERATING_MODEL_2026-09-27.md` | What feeds what, how often, who presses the button; guardrails | operating the system |",
    "| `docs/TRANSLATION_EMPTY_OUTCOMES_2026-09-27.md` | Why valid Sanskrit got empty translations; the outcome ledger | empty / filtered translations |",
    "| `docs/PARK_AND_TITLE_2026-09-27.md` | Parking lacuna-only verses; Srangam display titles | lacunas, publishing titles |",
    "| `docs/SRANGAM_BRIDGE_2026-09-27.md` | Automaton -> Srangam publish bridge and SQL-editor route | publishing to Srangam |",
    "| `docs/PIPELINE_STATE_2026-09-30.md` | Why a book stops between stages; the plan | a book is stuck |",
    "| `docs/OCR_CONSENSUS_2026-09-30.md` | One-command OCR consensus, drift, lacuna census, Hindi A/B and findings | OCR or lacuna work |",
]
BENCH = """

## OCR consensus and Hindi lacunas - measured 2026-10-01/02 (DOCS_MAP_2026_10_02)

Tools: `scripts/ocr_consensus.py`, `scripts/measure_lacunae.py`, `scripts/diag_hindi_ab.py`.
Details and caveats: `docs/OCR_CONSENSUS_2026-09-30.md` sections 4-5.

| Measure | Value |
|---|---|
| Mallapurana English lacuna rate, before (all Tesseract) | 237 / 370 = 64 % |
| after consensus, vision pages | 35 / 548 = 6.4 % |
| after consensus, Tesseract pages (58 triage-accepted at conf >= 72, plus 4 vision failures) | 87 / 157 = 55.4 % |
| Mallapurana Hindi lacuna rate, vision pages / Tesseract pages | 5.7 % / 57.2 % |
| Paired lacunas, Mallapurana (both / en only / hi only) | 122 / 0 / 4 - the cause is OCR |
| Paired lacunas, nilamata_seg, harita_tritiya, HAYASHIRSHA (hi only / both) | 125/0, 123/8, 43/0 - the cause is the Hindi prompt |
| Hindi with vs without English reference, 200 verse-pairs, lacunas | 65 vs 76 |
| same, tatsama share | lower with reference in 5 of 5 runs |
| same-sample run-to-run noise (40 verses, 3 runs) | 15/20/17 vs 18/18/21 |
| vision cost per page, measured | $0.00028 |

**Lacuna counts are not fidelity.** The judge-graded question in the section
above ("The measurement still missing", `ab_source_quality.py`) is still open.
Mallapurana's lacuna drop is strong evidence for that one book. The rule above
stands: no corpus-wide rebuild before ab_source_quality has run.
"""


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    nl = "\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p in (RB, BM):
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    rb, rb_nl = load(RB); bm, bm_nl = load(BM)
    if MARK in rb or MARK in bm:
        if MARK in rb and MARK in bm:
            print("Already patched (%s). Nothing to do." % MARK); return 0
        print("REFUSING: marker present in only one file - inspect by hand."); return 1
    problems = []
    lines = rb.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith(ROW_PREFIX)]
    if len(idx) != 1:
        problems.append("documentation-map anchor row matched %d times" % len(idx))
    if rb.count(SYNC_OLD) != 1:
        problems.append("sync sentence matched %d times" % rb.count(SYNC_OLD))
    table = "\n".join(l for l in lines if l.startswith("| "))
    present = [r for r in NEW_ROWS if r.split("|")[1].strip() in table]
    if present:
        problems.append("rows already present: %s" % ", ".join(r.split("|")[1].strip() for r in present))
    for r in NEW_ROWS:
        f = r.split("`")[1]
        if not Path(f).exists():
            problems.append("listed doc does not exist: %s" % f)
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    lines[idx[0] + 1:idx[0] + 1] = NEW_ROWS
    rb2 = "\n".join(lines).replace(SYNC_OLD, SYNC_NEW, 1)
    bm2 = bm.rstrip("\n") + BENCH
    if args.check:
        print("CHECK OK: %d rows, sync note, BENCHMARKS section. Nothing written." % len(NEW_ROWS)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    for p, text, nl in ((RB, rb2, rb_nl), (BM, bm2, bm_nl)):
        shutil.copy2(p, p.with_name(p.name + ".bak_docmap_" + stamp))
    tmps = []
    for p, text, nl in ((RB, rb2, rb_nl), (BM, bm2, bm_nl)):
        t = p.with_name(p.name + ".tmp_docmap"); t.write_bytes(text.replace("\n", nl).encode("utf-8")); tmps.append((t, p))
    for t, p in tmps:
        os.replace(t, p)
    print("PATCHED RUNBOOK.md and BENCHMARKS.md (backups *.bak_docmap_%s)." % stamp); return 0


if __name__ == "__main__":
    sys.exit(main())
