#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs82_2026_10_21.py  DOCS82_2026_10_21

Records what the night's checks settled: the 175 passages between the site and the PC are the Hayasirsa's (held in
repair: 1,531 there, 1,706 here), every other live text being equal text by text; the PC's --link run equal to the
copy's (1,706 of 3,917 names tied); the Satapatha's sources read again (its typists and its editor; GRETIL's thirteen
files and their shape, read now by ETEXT_PROSE_2026_10_21; the Sanskrit Library's and TITUS's editions; Satyavrata
Samasrami's Bibliotheca Indica print with its dandas; the Vedic Heritage Portal's page images and their terms); the
Carmichael Lectures' scans (NVLI's host does not answer, HathiTrust serves its copies in full only in the United
States); and why the PC could not download (Invoke-WebRequest goes through Windows' proxy settings; curl.exe does not).

Appends section 8 of docs/BRAIN_PATH_2026-10-21.md, PLATFORM section 85, a RUNBOOK section, ENTERPRISE_PATH addendum
72 and STATE section 17, each needing DOCS81_2026_10_21. Marker-idempotent per file, all-or-nothing, backup first
(.bak_docs82_<date>), line endings kept.

  python scripts\\patch_docs82_2026_10_21.py --check
  python scripts\\patch_docs82_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS82_2026_10_21"
BP = "docs/BRAIN_PATH_2026-10-21.md"

BRAIN = """

## 8. The counts explained; the Satapatha's sources; the Carmichael Lectures' (DOCS82_2026_10_21)

**The counts, explained** (your SQL of 21 Oct, 21:41 to 21:44 IST, beside the 18:41 backup and your list of the
texts). Every live text has on the site exactly the passages it has here but one: the Hayasirsa, 1,531 there (sent on
8 Oct, 10:07 UTC) and 1,706 here, held in repair, so the mirror keeps its last version. That is the 175. The withdrawn
texts have no live passage there (the Yoga Vasistha 70,292 retired; the Karanagama 2,084 retired, its version before
the repair; the Bodhicaryavatara's scan 1,677 retired). The site's live rows: 65 texts, 99,966 passages, 19,573
translation rows (1,671 of them the scholarly English), 13,145 names, 40,054 mentions, 25,504 vectors (28,166 with the
retired). Here, in the live texts but the Hayasirsa: 39,808 mentions and 25,346 vectors; the Hayasirsa's new passages
have 0 mentions and 1 vector. So the site's 246 more mentions and 158 more vectors should be the Hayasirsa's held
version: docs/cloud/CHECKS_held_2026-10-21.sql, H1, will say.

**B1 on the PC** (21:32 IST): what the copy gave, 1,706 of 3,917 names tied, 1,816 tie rows, 110 to more than one of
ours.

**The Satapatha's sources, read again:**
- Its makers: H. S. Anantanarayana typed kandas 1 to 11, 13 and 14 (GRETIL's file headers: "Data input by H.S.
  Ananthanarayana and W. P. Lehman"), Makoto Fushimi kanda 12, and J. R. Gardner re-edited them; GRETIL's index names
  Gardner, the Sanskrit Library all three. The edition: Weber's (Berlin, 1855; issued from 1849, the year the Sanskrit
  Library gives; reprinted at Varanasi in 1964 as Chowkhamba Sanskrit Series 96).
- GRETIL: thirteen files, sb_01_u.htm to sb_14_u.htm without 12, under gretil/1_sanskr/1_veda/2_bra/satapath/; each
  kandika under its own line (13.1.1.[1]); IAST without the Vedic accents and without dandas; the pluti written 3, the
  avagraha an apostrophe. etext_witness.py reads that shape now (ETEXT_PROSE_2026_10_21): each kandika a passage with
  its reference, the adhyaya its chapter, no danda added.
- The Sanskrit Library's XML edition (2010, version 0.1, CC BY-NC-SA 3.0) has all fourteen kandas; its page gives no
  download. TITUS (Frankfurt) has Gippert's edition, its download restricted.
- A print with its dandas, by an Indian editor: Satyavrata Samasrami's Satapatha with Sayana's commentary (Bibliotheca
  Indica, the Asiatic Society, Calcutta, 1903 to 1912; Samasrami died in 1911: public domain), on archive.org in the
  item Bibliotheca_Indica_Series (volumes 2 and 7 seen there). It is the witness for the dandas: its pages read by
  vision OCR beside GRETIL's kandikas, the danda taken where the print has it.
- The Vedic Heritage Portal (IGNCA, the Ministry of Culture) shows a Madhyandina Satapatha in two volumes as page
  images; its copyright policy forbids reproducing them without IGNCA's written permission: to read beside ours, not
  to ingest.

**The Carmichael Lectures of 1918:** NVLI's host (icvtesting.nvli.in) does not answer, from the PC or from here;
HathiTrust gives its copies in full only in the United States ("public domain only when viewed in the US"), and
outside a member library a page at a time. Found on the way: D. R. Bhandarkar's Lectures on Ancient Indian
Numismatics (the Carmichael Lectures of 1921; Calcutta, 1921) on rarebooksocietyofindia.org, public domain, for
later. The 1918 lectures wait for NVLI's host or another scan.

**Why the PC could not download:** Invoke-WebRequest gives "Unable to connect to the remote server" where curl.exe
reaches GRETIL (HTTP 200): PowerShell goes through Windows' proxy settings and curl.exe does not. The RUNBOOK shows
the settings; the downloads use curl.exe.
"""

PLATFORM = """

## 85. The counts explained; the Satapatha readable as prose (DOCS82_2026_10_21)

**21 Oct, late night.** docs/BRAIN_PATH_2026-10-21.md, section 8.
- **The 175 passages** between the site and the PC are the Hayasirsa's, held in repair (1,531 there, 1,706 here);
  every other live text is equal, text by text. The site's 246 more mentions and 158 more vectors are to be checked
  as its held version (docs/cloud/CHECKS_held_2026-10-21.sql).
- **ETEXT_PROSE_2026_10_21:** etext_witness.py reads a prose e-text whose units stand under their reference lines
  (GRETIL's Satapatha, 13.1.1.[1]): a kandika a passage with its reference, the adhyaya its chapter, never cut at 12
  lines, no danda added; a folder of files is one text; --category for a new text.
- **The Satapatha's sources:** GRETIL's thirteen files (reachable with curl.exe); the Sanskrit Library's and TITUS's
  editions (no open download); Samasrami's Bibliotheca Indica print (Calcutta, 1903 to 1912) for the dandas; the
  Vedic Heritage Portal's page images (IGNCA's written permission needed).
- **The Carmichael Lectures of 1918:** no scan reachable yet (NVLI's host does not answer; HathiTrust, the US only).

**Tests:** test_etext_prose_2026_10_21 (5), test_docs82_2026_10_21 (3); test_etext_refs_2026_10_21's replay now ends at
the copy ETEXT_PROSE backed up.
"""

RUNBOOK = """

## The Satapatha from GRETIL; the held counts (DOCS82_2026_10_21)

docs/BRAIN_PATH_2026-10-21.md, section 8. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\\patch_etext_prose_2026_10_21.py` and `python scripts\\patch_docs82_2026_10_21.py`, each
   with `--check`, then without it; then `python -m unittest tests.test_etext_prose_2026_10_21
   tests.test_etext_refs_2026_10_21 tests.test_etext_ortho_2026_10_21 tests.test_etext_witness_2026_10_11
   tests.test_docs82_2026_10_21 tests.test_docs81_2026_10_21`.
2. Why Invoke-WebRequest fails: `netsh winhttp show proxy` and the Internet Settings' ProxyEnable, ProxyServer and
   AutoConfigURL; the downloads below use curl.exe.
3. GRETIL's Satapatha, the sizes first (curl.exe -sI), then, if you approve, the thirteen files into
   `sources\\satapatha_gretil\\` with each one's provenance beside it.
4. The preview (free, writes nothing): `python scripts\\etext_witness.py --doc satapatha_madhyandina --file
   sources\\satapatha_gretil --category brahmana --per-page 10`; kanda 14 against our scan: `python scripts\\etext_witness.py
   --doc 2015_405693_Shatpath-Brahmanam --file sources\\satapatha_gretil\\sb_14_u.htm --per-page 10`.
5. The held counts: docs/cloud/CHECKS_held_2026-10-21.sql, H1 to H3 (read-only).
6. Release with COMMIT_MSG_etextprose_20261021.txt.
"""

EP = """

## Addendum 2026-10-21 (72) (DOCS82_2026_10_21)

| # | Item | State |
|---|---|---|
| K1 | The 175 passages between the site and the PC | Explained: the Hayasirsa, held in repair; every other text equal |
| K2 | The site's 246 more mentions and 158 more vectors | To check: the Hayasirsa's held version (CHECKS_held, H1) |
| D1 | The Satapatha as prose, kandika by kandika | Built: ETEXT_PROSE_2026_10_21; yours: GRETIL's download (curl.exe) |
| D1b | The Satapatha's dandas | Samasrami's Bibliotheca Indica print (Calcutta, 1903 to 1912), by vision OCR, as the witness |
| C1 | D. R. Bhandarkar's Carmichael Lectures (1918) | Waiting: NVLI's host does not answer; HathiTrust in full only in the US |
| B2 | The claims on the site | Next: C19, corpus-ingest's second list, corpus_sync |
"""

STATE = """

## 17. 21 Oct, late night: the counts explained; the Satapatha readable (DOCS82_2026_10_21)

- **The counts:** the 175 passages are the Hayasirsa's (held in repair); every other live text is equal.
- **The Satapatha:** ETEXT_PROSE_2026_10_21 reads GRETIL's kandikas; the thirteen files wait for your download
  (curl.exe; Invoke-WebRequest goes through Windows' proxy settings).
- **The repos:** the Automaton `9ecf0b97` and Srangam `aec5d41`, pushed (Srangam's e-text noise test: 2 passed), until
  this release.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path(BP), BRAIN)]
NEEDS = "DOCS81_2026_10_21"


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    plan = {}
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS not in src:
            print("REFUSE: %s has no %s section (apply it first). Nothing written." % (p, NEEDS)); return 1
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs82_" + stamp))
        t = p.with_name(p.name + ".tmp_docs82"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
