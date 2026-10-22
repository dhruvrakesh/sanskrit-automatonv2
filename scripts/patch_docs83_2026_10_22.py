#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs83_2026_10_22.py  DOCS83_2026_10_22

Records the morning of 22 Oct: the held counts confirmed (the Hayasirsa's held version is the site's 246 mentions,
158 vectors and 1,184 translation rows; every other text equal); what the brain reaches (25% of the live passages have
the working English, and only those a vector and names); what the meter says each step costs; GRETIL's Satapatha read
in full (7,173 kandikas, the numbers' other shapes, ETEXT_PROSE2_2026_10_22) and what it lacks (every ch: gacati for
gacchati); the kanda 14 ingested on 21 Oct to be written again as part of the whole; Samasrami's Bibliotheca Indica
print as the witness for the ch and the dandas; NVLI's server down; Raychaudhuri's Satapatha cites counted.

Corrects two things DOCS82 (and DOCS81) said: that Invoke-WebRequest failed through a proxy (the PC has none), and
that GRETIL's Satapatha has no dandas (kandas 1 to 9 have one a kandika; 10 to 14 a double space in its place).

Edits docs/BRAIN_PATH_2026-10-21.md (three sentences) and docs/STATE_2026-10-18.md (one), and appends the brain page's
section 9, PLATFORM section 86, a RUNBOOK section, ENTERPRISE_PATH addendum 73 and STATE section 18, each needing
DOCS82_2026_10_21. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs83_<date>), line endings kept.

  python scripts\\patch_docs83_2026_10_22.py --check
  python scripts\\patch_docs83_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS83_2026_10_22"
BP = "docs/BRAIN_PATH_2026-10-21.md"
ST = "docs/STATE_2026-10-18.md"

EDITS = {
    BP: [
        ("neither e-text prints dandas within one. Ours would",
         "GRETIL marks one pause a kandika (DOCS83_2026_10_22: section 9). Ours would"),
        ("IAST without the Vedic accents and without dandas; the pluti written 3, the",
         "IAST without the Vedic accents (DOCS83_2026_10_22: and without its ch; one danda a kandika in kandas 1 to 9, a\n"
         "  double space in its place in 10 to 14: section 9); the pluti written 3, the"),
        ("reaches GRETIL (HTTP 200): PowerShell goes through Windows' proxy settings and curl.exe does not. The RUNBOOK shows\n"
         "the settings; the downloads use curl.exe.",
         "reaches GRETIL (HTTP 200). DOCS83_2026_10_22: not a proxy, as this said: the PC has none (WinHTTP: direct access;\n"
         "ProxyEnable 0); why Invoke-WebRequest fails is not known. The downloads use curl.exe."),
    ],
    ST: [
        ("(curl.exe; Invoke-WebRequest goes through Windows' proxy settings).",
         "(curl.exe; DOCS83_2026_10_22: no proxy is set, so why Invoke-WebRequest fails is not known)."),
    ],
}

BRAIN = """

## 9. The Satapatha read in full, and what it lacks; the held counts confirmed (DOCS83_2026_10_22)

**The held counts, confirmed** (your H1 to H3, 22 Oct, 08:31 to 08:35 IST): the Hayasirsa's held version has 246
mentions, 158 vectors and 1,184 translation rows on the site, and every other text's mentions and vectors equal the
PC's, text by text. The site and the PC differ only where the mirror means them to.

**What the brain reaches** (the backup of 21 Oct, 22:08): of 100,141 live passages, 25,335 have the working English
(25%), and only those have a vector (25,347) and names (14,535 passages name someone), because build_embeddings.py and
extract_entities.py read the working English only. Outside the search by meaning and the names: the Padma's Patala
Khanda (21,128 passages, 2 with English), the Daivata Samhita (13,887, none), the Rgveda's volume ii (12,112, none),
the Markandeya from GRETIL (5,240, none, though 1,408 have the scholarly English), the Lalitavistara (4,335, 47), the
Manu and Harita smritis (2,568 and 2,477; 18 and 59), the Krishna Yajurveda (2,250, 42), the Akashabhairava Kalpa
(2,113, none), the Siddhanta Shiromani (1,146, none); the Surya's scholarly English (510) reaches neither. Phase E, two
ways: a vector and names from the scholarly English where there is no working English; the working English for the
large texts, priced by the meter.

**What the meter says each costs** (usage_log, the calls that succeeded): the working English with gemini-2.5-flash
$0.00058 a passage in October ($0.00033 over July to October); the names $0.00019 a passage; a vector $0.000015; the
scholarly English with Claude Sonnet $0.0128 (the Markandeya) to $0.0205 (the Surya) a passage. Google's cap: $80.39 of
$85 spent at 21 Oct, 21:21 IST.

**GRETIL's Satapatha, read in full (ETEXT_PROSE2_2026_10_22).** Its thirteen files (2,203,647 bytes, on the PC since
21 Oct, 22:07 IST) give 7,173 kandikas: kandas 1 to 11, 13 and 14 (835, 548, 859, 649, 470, 529, 398, 437, 402, 369,
437, 430, 810), 1,375,765 Devanagari characters, the longest 952. Beside the 13.1.1.[1] ETEXT_PROSE read, the numbers
come in other shapes: 18 with their brackets put in wrongly (1.1.3[.1]1 is 1.1.3.11), 2 with one bracket too many, 64
with none (all of 14.4.1, and the appendix's 14.3.2), 81 brahmanas' own numbers (as headings, or over a brahmana of one
kandika: 14.6.4.; 14.8.13 three times), one number glued to its text and mistyped (11.7.4.2 for 1.7.4.2); and in
kanda 14, after a line of asterisks, an appendix: five passages under 14.3.1. and 14.3.2.1 to 31 again, 21 word for
word (left out) and 10 not (kept, marked). Every kandika is prose: five had been typed colophons for a word in them.
The kanda 14 ingested on 21 Oct (2015_405693_Shatpath-Brahmanam__w_gretil, 745 passages, measured against our OCR:
50% of its readable pages, in order 98%) was read before these were known: its 14.4.1, its brahmanas of one kandika
and the appendix ran into the kandika before them (14.9.4.33 held 6,085 characters). It has no translation; the
RUNBOOK writes the whole Satapatha again as one text.

**What GRETIL's Satapatha lacks: its ch.** Not one ch or cch in the thirteen files: gacati for gacchati, candas for
chandas, papraca for papraccha. GRETIL's Mahabharata and Markandeya, beside them, have theirs (1,279 and 501). At their
share (0.8% of the words) about 1,200 words of the Satapatha have lost it; 246 of them could be put back from the words
of those two texts alone (gacati, prayacati), the rest only from another witness. So GRETIL's Satapatha is the
skeleton, every kandika with Weber's number, not yet the text of record: a witness, local, untranslated and
unreleased, until its ch is restored.

**The dandas GRETIL has:** one a kandika, after its first clause, written | in kandas 1 to 9 (801 in kanda 1's 835
kandikas) and as a double space in 10 to 14 (365 in kanda 10's 369). Whether the print has more inside a kandika is
to be seen on its pages.

**The witness for both, an Indian edition:** Satyavrata Samasrami's Satapatha (Bibliotheca Indica, Calcutta, 1903 to
1912) on archive.org, each volume as a PDF (volume 5 16.9 MB, 6 20.3 MB, 7 17.8 MB, 9 7.3 MB), a PDF with a text
layer, and archive.org's own reading (volume 5 973 KB of text, 6 1.18 MB, 7 1.05 MB, 9 391 KB, 4 only 44 KB). The
path: those readings first (free), measured against the skeleton; where poor, the pages by vision ($0.0034 a page);
then the skeleton's kandikas aligned with the print, the ch and the dandas taken where the print has them, each change
with its source. Kanda 12, not in GRETIL, comes from the print.

**Raychaudhuri's Satapatha:** 72 cites in Part I; 40 read to a kandika (13.5.4.1, Janamejaya's horse sacrifice, among
them), 5 of those in kanda 12; the rest misread by the scan (XIll. 5.1.11) or without a place.

**The Carmichael Lectures:** NVLI's server does not answer (TCP to 117.250.156.42:443 failed; ping timed out).
"""

PLATFORM = """

## 86. The Satapatha read in full; its missing ch; the brain's reach (DOCS83_2026_10_22)

**22 Oct, morning.** docs/BRAIN_PATH_2026-10-21.md, section 9.
- **The held counts confirmed:** the Hayasirsa's held version is the site's 246 mentions, 158 vectors and 1,184
  translation rows; every other text equal.
- **The brain's reach:** 25% of the live passages have the working English, and only those a vector and names.
- **ETEXT_PROSE2_2026_10_22:** GRETIL's Satapatha in full, 7,173 kandikas, every number's shape read (brackets wrong
  or missing, brahmanas' own numbers, a glued and mistyped number, the appendix after a separator), every kandika prose.
- **GRETIL's Satapatha lacks every ch** (gacati for gacchati): the skeleton, not yet the text of record; Samasrami's
  print (Calcutta, 1903 to 1912) is the witness for the ch and the dandas.
- **Corrected:** no proxy is set on the PC (DOCS82 said one was); GRETIL's Satapatha has one danda a kandika in kandas 1
  to 9 (DOCS81 and DOCS82 said none).

**Tests:** test_etext_prose2_2026_10_22 (6), test_docs83_2026_10_22 (3); test_etext_prose_2026_10_21's replay now ends at
the copy ETEXT_PROSE2 backed up.
"""

RUNBOOK = """

## The Satapatha written again in full; Samasrami's readings (DOCS83_2026_10_22)

docs/BRAIN_PATH_2026-10-21.md, section 9. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\\patch_etext_prose2_2026_10_22.py` and `python scripts\\patch_docs83_2026_10_22.py`,
   each with `--check`, then without it; then the tests named in COMMIT_MSG_etextprose2_20261022.txt.
2. The kanda 14 of 21 Oct: what depends on its passages (read-only), a backup (db_backup.py), then `python
   scripts\\wipe_doc.py --doc 2015_405693_Shatpath-Brahmanam__w_gretil --dry-run` and, if nothing depends on it, `--yes`.
3. The whole Satapatha, free, local: `python scripts\\etext_witness.py --doc satapatha_madhyandina --file
   sources\\satapatha_gretil --slug gretil --category brahmana --per-page 10` (the preview), then `--write`, then `python
   scripts\\etext_witness.py --doc satapatha_madhyandina --ingest --witness satapatha_madhyandina__w_gretil`. Not to
   be translated or released until its ch is restored.
4. Samasrami's volumes: the listing, then, if you approve, archive.org's readings (_djvu.txt) into
   `sources\\satapatha_samasrami\\`, and each previewed against the skeleton (free).
5. Release with COMMIT_MSG_etextprose2_20261022.txt.
"""

EP = """

## Addendum 2026-10-22 (73) (DOCS83_2026_10_22)

| # | Item | State |
|---|---|---|
| K2 | The site's 246 more mentions and 158 more vectors | Confirmed: the Hayasirsa's held version |
| E2 | Vectors and names only from the working English (25% of the live passages) | Found; phase E: from the scholarly English too, then the large texts' English |
| D1 | GRETIL's Satapatha in full (7,173 kandikas) | Built: ETEXT_PROSE2_2026_10_22; yours: write and ingest it as a local witness |
| D1a | GRETIL's Satapatha lacks every ch | Found: about 1,200 words; the skeleton, not the text of record |
| D1b | The ch and the dandas from Samasrami's print (Calcutta, 1903 to 1912) | Next: archive.org's readings measured; then vision where poor; then the alignment |
| D1c | Kanda 12 | From the print (GRETIL has none) |
| C1 | The Carmichael Lectures (1918) | Waiting: NVLI's server does not answer |
"""

STATE = """

## 18. 22 Oct, morning: the Satapatha read in full, and its missing ch (DOCS83_2026_10_22)

- **The counts:** the site's extra mentions and vectors are the Hayasirsa's held version; every other text equal.
- **The Satapatha:** GRETIL's thirteen files read in full (ETEXT_PROSE2_2026_10_22: 7,173 kandikas); every ch is
  missing in them, so it is ingested as a local witness, the skeleton for Samasrami's print.
- **The repos:** the Automaton `3bae7d1e` and Srangam `aec5d41`, pushed, until this release.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path(ST), STATE),
           (Path(BP), BRAIN)]
NEEDS = "DOCS82_2026_10_21"


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
        for k, (old, new) in enumerate(EDITS.get(str(p).replace("\\", "/"), []), 1):
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (p, k, src.count(old))); return 1
            src = src.replace(old, new, 1)
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs83_" + stamp))
        t = p.with_name(p.name + ".tmp_docs83"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
