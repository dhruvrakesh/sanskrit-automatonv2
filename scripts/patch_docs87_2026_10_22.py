#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs87_2026_10_22.py  DOCS87_2026_10_22

Records the evening of 22 Oct: the release ef43359b as tested; the Nirukta's witness written again and measured; why
nine test modules failed on the PC (eight: a cp1252 pipe; one: the hygiene replay) and TEST_ENV_2026_10_22, which
mends them; GRETIL's two zips read as a library (GRETIL_LIBRARY_2026_10_22: what is in them, under what licence or
notice, which of our 64 texts each reads); the verses GRETIL's html prints twice (ETEXT_ANALYSIS_2026_10_22); the
rights to weigh; Srangam's SEO Phase AN, found uncommitted.

Appends docs/DEBT_2026-10-22.md section 8, STATE section 22, a RUNBOOK section, PLATFORM section 90 and
ENTERPRISE_PATH addendum 77, each needing DOCS86_2026_10_22; adds data/gretil/ to .gitignore (after
data/source_fidelity/). Refuses unless the code it records is here: scripts/gretil_library.py (GRETIL_LIBRARY),
scripts/run_tests.ps1 and tests/test_repo_hygiene_2026_10_15.py (TEST_ENV), scripts/etext_witness.py
(ETEXT_ANALYSIS). Marker-idempotent per file, all-or-nothing, backup first (.bak_docs87_<date>), line endings kept.

  python scripts\\patch_docs87_2026_10_22.py --check
  python scripts\\patch_docs87_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS87_2026_10_22"
NEEDS = "DOCS86_2026_10_22"
REQUIRES = {"scripts/gretil_library.py": "GRETIL_LIBRARY_2026_10_22",
            "scripts/run_tests.ps1": "TEST_ENV_2026_10_22",
            "tests/test_repo_hygiene_2026_10_15.py": "TEST_ENV_2026_10_22",
            "scripts/etext_witness.py": "ETEXT_ANALYSIS_2026_10_22"}

DEBT = """
## 8. GRETIL's library; the suite on the PC; the Nirukta measured (DOCS87_2026_10_22)

- **Released:** `ef43359b` (WITNESS_FIX, LEGACY_TESTS, DOCS86), pushed; every file it wrote is the copy tested (md5,
  read from the PC).
- **The Nirukta's witness, written again (16:57):** 649 verses in 54 pages, 4,676 dandas, 57 avagrahas, 804 quotation
  marks; the old pages kept (`data\\raw_witness\\nirukta__w_gretil.bak_20261022_165647`), the database backed up first
  (`D:\\backups\\context_pre_witness_nirukta__w_gretil_20261022_165648.db`). Measured against it (645 units): our vision
  reading agrees 75.33%, Tesseract's, which is the text in the database, 70.74%; 97.8% of the units under 90%. The
  two readings misread on their own 4.95 (vision) and 9.57 (Tesseract) aksharas in 100, and agree against GRETIL in
  16.37: there our print reads otherwise, or both misread alike (GRETIL's is Lakshman Sarup's edition). The working
  English (96.95% of the 2,095 passages) was made from the Tesseract text. Whether GRETIL's text becomes the
  Nirukta's, as for the Markandeya and the Surya, is yours: read the report's examples first.
- **The suite on the PC: nine modules failed; why, and the mends.** Eight failed only because Python on Windows writes
  to a pipe in the console's code page (cp1252): a test whose script prints Devanagari or IAST passes in the console
  and fails with UnicodeEncodeError once its output is piped (`2>&1 | Out-String`); test_mbh_prose's three errors were
  this. The dashboard runs every job with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (scripts\\dashboard.py);
  `scripts\\run_tests.ps1` (TEST_ENV_2026_10_22) runs the tests so, for its own window only, and prints each failing
  module's verdict. The ninth, test_repo_hygiene: its replay compared with a .gitignore DOCS78 and DOCS84 wrote again;
  it accepts a later patch's backup now (as test_docs76 does since LEGACY_TESTS).
- **GRETIL's library: the two zips** you downloaded from gretil.html (in `inbox\\`; to go to `sources\\gretil\\`, which
  git ignores):
  - `1_sanskr.zip` (295,862,698 bytes, 3,803 entries): 801 TEI texts (the conversion of 2019-20, with their plain-text
    and html transformations), each with its licence in its header: 800 CC BY-NC-SA 4.0 (credit, non-commercial,
    share alike), 1 CC BY-SA 4.0; 387 typed from an edition of 1960 or later (the latest year its source line names;
    a reprint counts), whose editor's rights may stand. And
    1,335 legacy files: 955 taken by the conversion (they, or another version of their work); 380 not, of which 332
    are texts (26 pada indexes and 22 second versions of a work left out). Every one of the 332 says "THIS GRETIL
    TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE.": no licence; a
    witness to check our readings against, published only where its source edition is free; 58 name an edition of
    1960 or later.
  - `6_sres.zip` (75,253,180 bytes): 23 resources: the dictionaries (Monier-Williams 1899, 1872 and 1851, Apte both
    ways, Boehtlingk and Roth, Boehtlingk, the Vacaspatyam, the Sabdakalpadruma, Grassmann, Macdonell, Cappeller,
    Bopp, Benfey, Burnouf, Borooah, Schmidt), Bloomfield's Vedic Concordance, Aufrecht's Catalogus Catalogorum: 21 old
    enough to be free (1822 to 1928); two under copyright, for private reading only: Vettam Mani's Puranic
    Encyclopaedia (1964) and Stchoupak, Nitti and Renou's dictionary (1932). Nothing of it is used yet.
  - The zip's copies are the ones fetched: the Nirukta's and the Markandeya's html byte for byte; the Satapatha's
    thirteen kandas but for their line endings (CRLF in the zip). GRETIL forbids directory listings (403); the zip
    is the listing.
- **scripts\\gretil_library.py (GRETIL_LIBRARY_2026_10_22), free and read-only:** `--catalog` (each text's header: the
  edition and its year, who typed it, the licence or the notice) -> data\\gretil\\catalog.jsonl and --csv; `--match`
  (40 pages of each of our texts, their consonant skeleton in 6-letter grams, against every GRETIL text read the
  same way; the lift over each file's baseline and the ratio to it) -> data\\gretil\\match.jsonl and --csv, resumable;
  `--extract MEMBER --doc DOC` (one file into sources\\DOC\\, its provenance beside it). The skeleton reads Aufrecht's
  Vedic l with a line below as the consonant, and an m with a candrabindu as a nasal sign.
- **What GRETIL reads of our 64 texts** (the VM's run on your pages; lift, and its ratio to the file's baseline):
  - a witness (11): the Yamasmrti (78 verses) 0.72, 352x; the Manusmrti 0.66, 14x; the Markandeya 0.63, 10x
    (adopted); the Narasimha 0.58, 11x; the Yajnavalkya 0.56, 27x; the Parasara 0.55, 40x; the Nirukta 0.49, 16x (a
    witness, above); the Surya 0.45, 57x (adopted); the Gautama Dharmasutra 0.37, 45x; the Samaveda 0.36, 27x; the
    Bodhicaryavatara 0.34, 24x. Eight are new, each a TEI file, each read clean in the preview (no Latin left, noise
    0.8% at most): the Yama 82 verses, the Manu 3,058, the Narasimha 3,586, the Yajnavalkya 1,392, the Parasara 955,
    the Gautama 1,023 sutras, the Samaveda 469 verses as it reads them, the Bodhicaryavatara 935.
  - a part or a parallel (3): our Visnusmrti (of the eighteen) and the Santiparvan (0.34, 3x: half its sampled
    letters are in the Mahabharata; GRETIL's Visnusmrti, Krishnamacharya's, reads less of it); the Satapatha and the
    Kanva Brhadaranyaka (0.31, 4x; its witness is GRETIL's Madhyandina text already); the Taittiriya and the
    Maitrayani Samhita (0.25, 4x: a sister samhita, not a witness).
  - possible (16): by name the Astadhyayi, the Lalitavistara, the Rgveda (vol. ii); the Natyasastra 0.21; the Sukla
    Yajurveda in the Maitrayani 0.25 (a parallel too: 4x); six minor smrtis (Likhita, Apastamba, Atri, Samvarta,
    Sankha, Angirasa) in the Mitaksara, a commentary that quotes them; the Brhaspati in the Bhrgusamhita, the Daksa in
    the Garuda; the Sandilya in a Gita with four commentaries; the Siva-dhanurveda in the Mahasubhasitasamgraha; the
    Hayasirsa in the Agnipurana 0.11 (which borrows from it).
  - none (34), among them the Siksas, the Harita's sthanas, the upapuranas (Kapila, Parasara, Samba, Saura), the
    Nilamata, the Siddhanta Siromani, the Dhanurvedas, the Padma's Patala-khanda, the Yogavasistha, the Karana Agama
    and the Daivat-Sanhita (Aufrecht's Rgveda reads 0.18 of its Tesseract pages, twice its baseline): GRETIL has no
    witness for them; our scans are the only one here, and better editions are to be sought elsewhere.
- **Found, and mended (ETEXT_ANALYSIS_2026_10_22):** 43 of GRETIL's 802 html transformations print each verse twice,
  the verse and then its analysis (`<p class="analysis">`, the sandhi undone), and etext_witness.py read both: the
  Manusmrti as 5,748 verses (3,058), the Yajnavalkya 2,403 (1,392), the Parasara 1,540 (955). html_to_text() leaves
  the analysis out; the Markandeya, the Nirukta and the Surya read byte for byte as before (5,231, 649, 504 units).
- **Rights to weigh, before any of it reaches the site:** GRETIL's typing is CC BY-NC-SA 4.0; under it are the
  editions: the Narasimha's is Siddheswar Jena's (Delhi 1987), the Yama's the Smriti Sandarbha (Calcutta 1952/57),
  the Yajnavalkya's Narayan Ram Acharya's (Bombay 1949), the Lalitavistara's P. L. Vaidya's (Darbhanga 1958), the
  Astadhyayi's from Aryendra Sharma's Kasika (Hyderabad 1969-85). A witness on the PC checks our readings; what of it
  is published is yours.
- **Srangam, found uncommitted:** another session's SEO Phase AN (22 Oct, 09:37 to 09:58): index.html (the static
  canonical gone, five data-rh tags), src/pages/NotFound.tsx, src/components/oceanic/article/ArticleError.tsx,
  src/pages/articles/ArticlesRouter.tsx (three Navigate redirects), public/sitemap.xml (74 URLs, no retired slug),
  docs/SEO_GSC_STATUS_2026-10-22.md, docs/RELIABILITY_AUDIT.md (Phase AN), docs/SEO_CONFIGURATION.md,
  docs/SEO_DISCOVERY_AUDIT_AND_PLAN_2026-07-19.md; beside them their .bak_gsc_20261022 copies, which Srangam's
  .gitignore does not ignore (so: an explicit git add). /editions is in the sitemap, not in
  supabase/functions/generate-sitemap/index.ts. Companion changes, uncommitted too, in nartiang-legacy-web and
  remix-of-dkegl-website. SEO_GSC_STATUS's checks use Invoke-WebRequest, which fails on this PC: the RUNBOOK gives
  them with curl.exe.
- **Open:** the Nirukta's text (yours); the eight new witnesses (free); the Daivat-Sanhita (CHECKS_followup J1, J2);
  the Pro pilot (about $0.31); the Hayasirsa's English (about $0.94).
"""

STATE = """
## 22. 22 Oct, evening: GRETIL's library; the suite on the PC (DOCS87_2026_10_22)

- **Released:** the Automaton `ef43359b`; Srangam `aec5d41`, with another session's SEO Phase AN uncommitted.
- **New:** scripts\\gretil_library.py (GRETIL's two zips catalogued; 11 of our texts with a GRETIL witness, 8 of them
  new); scripts\\run_tests.ps1 (the suite as the dashboard runs it). **Mended:** ETEXT_ANALYSIS_2026_10_22 (verses
  read twice), TEST_ENV_2026_10_22 (the hygiene replay).
- **The Nirukta:** its witness written again and measured (vision 75.33%, Tesseract 70.74%); its text is yours to
  decide.
"""

RUNBOOK = """
## GRETIL's library; the suite as the dashboard runs it (DOCS87_2026_10_22)

docs/DEBT_2026-10-22.md, section 8. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`,
then `Set-Location $A`. Nothing below spends.
1. Apply, each with `--check` first: `scripts\\patch_test_env_2026_10_22.py`, `scripts\\patch_etext_analysis_2026_10_22.py`,
   `scripts\\patch_docs87_2026_10_22.py`. Then the whole suite: `powershell -ExecutionPolicy Bypass -File
   scripts\\run_tests.ps1` (it ends "every module passes"; `-Show` prints a failing module's output). A test piped in
   a plain window (`python -m unittest ... 2>&1 | ...`) writes cp1252 and can fail for that alone.
2. The library: `New-Item -ItemType Directory -Force sources\\gretil`, `Move-Item inbox\\1_sanskr.zip sources\\gretil\\`,
   `Move-Item inbox\\6_sres.zip sources\\gretil\\`; then `python scripts\\gretil_library.py --catalog --csv
   exports\\gretil_catalog.csv` and `python scripts\\gretil_library.py --match --csv exports\\gretil_match.csv` (some
   minutes; `--budget 600` stops it and the next run goes on).
3. A witness for each text the match calls strong and has none yet; the html transformation of each:
   smriti_18yama_smriti sa_yamasmRti-78v.htm; smriti_14manu_smriti_seg sa_manusmRti.htm; upapurana_narasimha_purana
   sa_narasiMhapurANa.htm; smriti_06yagyavalkya_smriti sa_yAjJavalkyasmRti.htm; smriti_13parashara_smriti
   sa_parAzarasmRti-AcAra-prAyazcitta.htm; smriti_17gautama_smriti sa_gautama-dharmasUtra.htm; sama_veda_sama_veda
   sa_sAmavedasaMhitA.htm; Bodhicaryavatara sa_zAntideva-bodhicaryAvatAra.htm. For the Manu, and so for each:
   `python scripts\\gretil_library.py --extract 1_sanskr/tei/transformations/html/sa_manusmRti.htm --doc
   smriti_14manu_smriti_seg`; the preview (it measures our scan against it, writes nothing): `python
   scripts\\etext_witness.py --doc smriti_14manu_smriti_seg --file sources\\smriti_14manu_smriti_seg\\sa_manusmRti.htm`;
   with the dashboard idle, the same with `--write`, then `python scripts\\etext_witness.py --doc
   smriti_14manu_smriti_seg --ingest --witness smriti_14manu_smriti_seg__w_gretil` (its own backup first; a witness is
   local, the mirror does not send it), then `python scripts\\source_fidelity.py --ref
   db:smriti_14manu_smriti_seg__w_gretil --cand db:smriti_14manu_smriti_seg`.
4. Before any of it is adopted or published: its edition and licence in `exports\\gretil_catalog.csv` (DEBT section 8,
   the rights to weigh).
5. Srangam (another session's SEO Phase AN): `git add` the nine files by name (not `-A`: their .bak_gsc_20261022
   copies are not ignored), `git pull --rebase --autostash`, commit, push, Lovable Publish; then, read-only, SEO_GSC_STATUS
   section 5's checks with `$h = curl.exe -s https://srangam.nartiang.org/ | Out-String` and `$s = curl.exe -s
   https://srangam.nartiang.org/sitemap.xml | Out-String` in place of its two Invoke-WebRequest lines (expected:
   static canonical gone: True, data-rh tags 5, sitemap urls 74, retired slugs left 0).
6. The site, read-only: `docs\\cloud\\CHECKS_followup_2026-10-22.sql` J1 to J3, if not yet run.
"""

PLATFORM = """
## 90. GRETIL's library; the suite as the dashboard runs it (DOCS87_2026_10_22)

| Marker | Files | What |
|---|---|---|
| GRETIL_LIBRARY_2026_10_22 | scripts/gretil_library.py, tests/test_gretil_library_2026_10_22.py | GRETIL's zips as a library: --catalog (801 TEI texts and 380 legacy files, each its licence or notice), --match (which GRETIL text reads which of our texts: the lift over its baseline, the ratio to it), --extract (one file and its provenance) |
| ETEXT_ANALYSIS_2026_10_22 | scripts/etext_witness.py (+ test_witness_fix's replay) | html_to_text() leaves out GRETIL's analysis column: each verse read once |
| TEST_ENV_2026_10_22 | scripts/run_tests.ps1, tests/test_repo_hygiene_2026_10_15.py | the suite with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8, as the dashboard runs jobs; the hygiene replay accepts a later backup |
| DOCS87_2026_10_22 | DEBT 8, STATE 22, RUNBOOK, this section, ENTERPRISE_PATH 77, .gitignore (data/gretil/) | the record |

- **Released before them:** `ef43359b`; every file as tested.
- **Read, not changed:** Srangam's SEO Phase AN (another session's), uncommitted; the two GRETIL zips (`sources\\gretil\\`).
"""

EP = """
## Addendum 2026-10-22 (77) (DOCS87_2026_10_22)

| # | Item | State |
|---|---|---|
| F4 | GRETIL's library: 801 TEI texts and 332 legacy texts catalogued, matched against our 64 | Done: GRETIL_LIBRARY_2026_10_22; yours: run it on the PC (free) |
| F4a | Eight new witnesses: the Yama, Manu, Narasimha, Yajnavalkya, Parasara, Gautama, Samaveda, Bodhicaryavatara | Yours: extract, preview, write, ingest, measure (free) |
| F4b | Translate from the better text: the Manu (0.7% English), the Samaveda (0%), the Narasimha (2.9%), the Parasara (0%); measure before any English is bought | Next, after F4a |
| F4c | 34 texts GRETIL does not read | Open: other sources; our scans are their witness |
| T11 | The suite on the PC: a cp1252 pipe | Mended: TEST_ENV_2026_10_22 (run_tests.ps1) |
| T5c | Verses read twice (GRETIL's analysis column) | Mended: ETEXT_ANALYSIS_2026_10_22 |
| Y3 | The Nirukta's text: GRETIL's (ours agrees 75.33% vision, 70.74% Tesseract) | Yours |
| Y4 | GRETIL's terms (CC BY-NC-SA 4.0; legacy files: reference only) and the editions of 1960 or later | Yours |
| S1 | Srangam's SEO Phase AN, uncommitted | Yours: add by name, commit, push, Publish, the curl.exe checks |
"""

GITIGNORE_OLD = "\ndata/source_fidelity/\n"
GITIGNORE_NEW = ("\ndata/source_fidelity/\n"
                 "# GRETIL_LIBRARY_2026_10_22 (DOCS87_2026_10_22): GRETIL's catalog and the match are made again by\n"
                 "# scripts/gretil_library.py (free, read-only); the zips are under sources/, ignored above\n"
                 "data/gretil/\n")

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]
GI = Path(".gitignore")
GI_NEEDS = "DOCS84_2026_10_22"


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first; it comes with this release). Nothing written." % (f, m))
            return 1
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
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (p, NEEDS)); return 1
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if not GI.exists():
        print("FAIL: .gitignore not found. Run from the repo root."); return 2
    raw = GI.read_bytes()
    if MARK.encode() in raw:
        print("skip .gitignore (already carries %s)" % MARK)
    else:
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if GI_NEEDS not in src:
            print("REFUSE: .gitignore has no %s (apply it first). Nothing written." % GI_NEEDS); return 1
        if src.count(GITIGNORE_OLD) != 1:
            print("REFUSE: .gitignore: the data/source_fidelity/ line found %d times (want 1). Nothing written."
                  % src.count(GITIGNORE_OLD)); return 1
        plan[GI] = src.replace(GITIGNORE_OLD, GITIGNORE_NEW, 1).replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs87_" + stamp))
        t = p.with_name(p.name + ".tmp_docs87"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
