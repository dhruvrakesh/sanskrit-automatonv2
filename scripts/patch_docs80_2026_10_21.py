#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs80_2026_10_21.py  DOCS80_2026_10_21

Records the night of 21 Oct: the refs mend done (18:41 IST) and sent with the 20:31 mirror run; the run of Raychaudhuri's
Part I audited (83 pages, 1,703 claims; 13 failed for one reason, 4 not read) and mended (CLAIMS_FIX_2026_10_21:
--reparse, --recite, cites-v2, every attempt's cost on its read); the brain's wiring measured and the path from here
(docs/BRAIN_PATH_2026-10-21.md); and a figure corrected: the verses of numbers cost $2.10 by the run's own count (its
log's rows sum to $2.01, which DOCS79 gave).

Corrects that figure in docs/STATE_2026-10-18.md (section 14), docs/ENTERPRISE_PATH_2026-10-04.md (addendum 69),
docs/PLATFORM_2026-10-04.md (section 82) and docs/CLAIMS_AND_REFS_2026-10-21.md; appends PLATFORM section 83, a RUNBOOK
section, ENTERPRISE_PATH addendum 70 and STATE section 15, each needing DOCS79_2026_10_21. Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs80_<date>), line endings kept.

  python scripts\\patch_docs80_2026_10_21.py --check
  python scripts\\patch_docs80_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS80_2026_10_21"
FIXED = " (the run's own count; DOCS80_2026_10_21: its log's rows sum to $2.01)"

EDITS = {
    "docs/STATE_2026-10-18.md": [("(17:48 IST: 15 passed, 3 flagged, $2.01; data/scholar/",
                                  "(17:48 IST: 15 passed, 3 flagged, $2.10%s; data/scholar/" % FIXED)],
    "docs/ENTERPRISE_PATH_2026-10-04.md": [("15 passed, 3 flagged, $2.01. Addendum 68",
                                            "15 passed, 3 flagged, $2.10%s. Addendum 68" % FIXED)],
    "docs/PLATFORM_2026-10-04.md": [("18 verses: 15 passed, 3 flagged, $2.01.",
                                     "18 verses: 15 passed, 3 flagged, $2.10%s." % FIXED)],
    "docs/CLAIMS_AND_REFS_2026-10-21.md": [("flagged, $2.01); its rows still carry",
                                            "flagged, $2.10%s); its rows still carry" % FIXED),
                                           ("the Gemini run was the one made: 18 verses, 15 passed, 3\nflagged, $2.01.",
                                            "the Gemini run was the one made: 18 verses, 15 passed, 3\nflagged, $2.10%s." % FIXED)],
}

PLATFORM = """

## 83. The claims audited and mended; the brain's wiring measured (DOCS80_2026_10_21)

**21 Oct, night.** docs/BRAIN_PATH_2026-10-21.md.
- **The Surya's references** mended at 18:41 IST (18 values put back and re-based, 485 references, 14 chapters; a backup
  first); the second plan found nothing; the 20:31 mirror run sends 503 passages and 156 scholarly rows.
- **Raychaudhuri, Part I:** 83 of 99 pages read, 1,703 claims (quotations 1,423 exact, 179 close, 15 not on the page,
  86 too short); 13 pages failed, all because the model copied the scan's backslashes (the OCR's M, 1\\f) into a
  quotation, which JSON does not allow; 4 pages (pdf 109 to 112) not read. About $1.43 from the stored replies.
- **CLAIMS_FIX_2026_10_21:** --reparse reads a failed page again from its stored reply (12 pages, 260 claims, free);
  every attempt's cost stays on its read and --report prints the meter's sum; cites-v2 reads the scan's misread cites
  (on a copy: 1,037 of 1,245 read, 208 left as printed; cites to a text we hold 23 to 62); the Purana Index first on a
  name.
- **The wiring:** names, passages, the scholarly English and the vectors are mirrored and read by the site; the shelf
  and the claims are on the PC only, and joined only when read. The path: B1 the links stored, B2 the mirror (C19),
  B3 the name page's "What the scholars say", B4 the Professor Bot; then more scholars, Indian first.

**Tests:** test_claims_fix_2026_10_21 (6), test_docs80_2026_10_21 (3); test_scholar_claims_2026_10_21 changed (Hopkins's
Great Epic is now read as the work it is).
"""

RUNBOOK = """

## The claims mended; the brain's path (DOCS80_2026_10_21)

docs/BRAIN_PATH_2026-10-21.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `scripts\\patch_claims_fix_2026_10_21.py` and `scripts\\patch_docs80_2026_10_21.py`, each with
   `--check`, then without it; then `python -m unittest tests.test_claims_fix_2026_10_21 tests.test_scholar_claims_2026_10_21
   tests.test_docs80_2026_10_21 tests.test_docs79_2026_10_21`.
2. `python scripts\\scholar_claims.py --reparse` (free), `--recite` (free), `--part 1 --yes` (the last 4 pages, about
   $0.03), `--report`, `--show Janamejaya`, `--csv data\\shelf\\phai1923_claims.csv`.
3. After the 20:31 IST mirror run: docs/cloud/CHECKS_surya_refs_2026-10-21.sql, R1 to R4 (read-only).
4. The Satapatha from GRETIL, if you approve the download: kandas 11 and 13 (or 1 to 11, 13, 14) into
   `sources\\satapatha_gretil\\`, their sha256 recorded; nothing is ingested until its kit comes.
5. Release with COMMIT_MSG_claimsfix_20261021.txt.
"""

EP = """

## Addendum 2026-10-21 (70) (DOCS80_2026_10_21)

| # | Item | State |
|---|---|---|
| S2 | The Surya's verses of numbers: the figure | $2.10 by the run's own count (DOCS79 gave $2.01, its log's rows) |
| S4 | The Surya's references and chapters | Mended 18:41 IST; sent with the 20:31 mirror run |
| H3 | Raychaudhuri, Part I, as claims | 95 of 99 pages once --reparse is run; 4 to read (about $0.03); about $1.43 spent |
| H5 | The claims' cites read (cites-v2) | Built: CLAIMS_FIX_2026_10_21; 83% of the cites read on a copy |
| B1 to B4 | The scholars' layer linked, mirrored (C19), on the name page, and the Professor Bot | Planned: docs/BRAIN_PATH_2026-10-21.md |
| D1 | GRETIL's Satapatha (kandas 1 to 11, 13, 14; Gardner's input) | Yours: the download |
"""

STATE = """

## 15. 21 Oct, night: the claims audited; the brain's path (DOCS80_2026_10_21)

- **The Surya Siddhanta's references:** mended 18:41 IST; the site gets them with the 20:31 mirror run.
- **Raychaudhuri, Part I:** 83 pages read (1,703 claims), 13 failed for one reason (the scan's backslashes in a
  quotation), 4 not read; mended by CLAIMS_FIX_2026_10_21 (--reparse: 12 pages back, free; cites-v2).
- **The figure of the verses of numbers:** $2.10 by the run's own count, not the $2.01 of section 14 (its log's rows).
- **The brain:** what is wired and what is not, measured, and the path from here: docs/BRAIN_PATH_2026-10-21.md.
- **The repos:** the Automaton `df8b35ae` and Srangam `aec5d41`, pushed, until this release.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/STATE_2026-10-18.md"), STATE)]
NEEDS = "DOCS79_2026_10_21"


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    plan = {}
    for rel in sorted(set(EDITS) | {str(p).replace("\\", "/") for p, _t in TARGETS}):
        p = Path(rel)
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if rel in EDITS:
            for k, (old, new) in enumerate(EDITS[rel], 1):
                if src.count(old) != 1:
                    print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (p, k, src.count(old))); return 1
                src = src.replace(old, new, 1)
        add = [t for q, t in TARGETS if str(q).replace("\\", "/") == rel]
        if add:
            if NEEDS not in src:
                print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, NEEDS)); return 1
            src = (src if src.endswith("\n") else src + "\n") + add[0].lstrip("\n").join(["\n", ""])
        if MARK not in src:
            src = src + ("" if src.endswith("\n") else "\n") + "<!-- %s -->\n" % MARK
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs80_" + stamp))
        t = p.with_name(p.name + ".tmp_docs80"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
