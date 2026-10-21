#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs81_2026_10_21.py  DOCS81_2026_10_21

Records the rest of the night of 21 Oct: Part I of Raychaudhuri complete (2,010 claims of 99 pages, after --reparse,
--recite and the last pages read); the claims' names tied to our entities (CLAIMS_LINK_2026_10_21, phase B1 of
docs/BRAIN_PATH_2026-10-21.md); the site's counts as measured, which correct that page's table (it said all 174,019
passages are mirrored: the site holds 99,966 live, the three withdrawn texts holding 73,878 here); the Satapatha for
the translator (what we hold, the edition of record, the two e-texts, the dandas); D. R. Bhandarkar's Carmichael
Lectures found; and phase B2 designed from the code of corpus-ingest and C4, additive so that nothing the mirror runs on
is replaced.

Corrects four rows and one sentence of docs/BRAIN_PATH_2026-10-21.md and appends its section 7; appends PLATFORM section
84, a RUNBOOK section, ENTERPRISE_PATH addendum 71 and STATE section 16, each needing DOCS80_2026_10_21. Marker-idempotent
per file, all-or-nothing, backup first (.bak_docs81_<date>), line endings kept.

  python scripts\\patch_docs81_2026_10_21.py --check
  python scripts\\patch_docs81_2026_10_21.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS81_2026_10_21"
BP = "docs/BRAIN_PATH_2026-10-21.md"

EDITS = {
    BP: [
        ("| Passages | 174,019 | mirrored (row hashes, digests) | the reader (C5, C17) |",
         "| Passages | 174,019 (100,141 in the live texts; the three withdrawn hold 73,878) | 99,966 live, measured 21 Oct "
         "20:45 IST (DOCS81_2026_10_21: this row had said all are mirrored; section 7) | the reader (C5, C17) |"),
        ("| Scholarly English | `scholar_translations` 5,569 rows | mirrored as `en-x-scholar` rows |",
         "| Scholarly English | `scholar_translations` 5,569 rows (every version) | mirrored as `en-x-scholar` rows, 1,671 "
         "live (measured 21 Oct): each verse's latest English, made from its Sanskrit as it reads now, not rejected; one "
         "row for a sentence over several verses |"),
        ("`entity_mentions` 41,059 | `corpus.entities`, `corpus.mentions` |",
         "`entity_mentions` 41,059 | `corpus.entities` 13,145, `corpus.mentions` 40,054 (measured 21 Oct) |"),
        ("| Meaning | `passage_embeddings` 26,345 | `corpus.passage_vectors` |",
         "| Meaning | `passage_embeddings` 26,345 | `corpus.passage_vectors` (28,166 counted with the retired rows; the live "
         "count by section 7's check) |"),
        ("| The shelf, step 2 | data/shelf/claims.db: 1,703 claims of 83 pages (1,963 of 95 once `--reparse` is run) | not "
         "mirrored | no |",
         "| The shelf, step 2 | data/shelf/claims.db: Part I complete, 2,010 claims of 99 pages; their names tied to our "
         "entities by `--link` (CLAIMS_LINK_2026_10_21, section 7) | not mirrored (B2) | no |"),
        ("(GRETIL's general\n  terms apply).",
         "(GRETIL's general\n  terms apply; DOCS81_2026_10_21: so GRETIL's index says; the kanda 11 file's own header credits "
         "H. S. Ananthanarayana\n  and W. P. Lehman: section 7)."),
    ],
}

BRAIN = """

## 7. B1 done; the counts corrected; the Satapatha and the Carmichael Lectures; B2 designed (DOCS81_2026_10_21)

**B1, the claims tied to our names (CLAIMS_LINK_2026_10_21).** `scholar_claims.py --link` (free; data/context.db only
read) ties each name of the current claims (their subjects and objects) to our entities and stores the ties in
claims.db (`claim_links`, `claim_link_runs`). The tiers, the first that ties winning: exact (the shelf's own key); a
variant our texts record; a vowel's length; a 1923 spelling (Rigveda, Kurukshetra, Asvapati, Chhandogya: only for a
name without diacritics, the vowel r read as ri on both sides, doubled letters kept); then a numbered namesake
(Parikshit I and II, Janaka I and II, Satanika II: our texts name one of each) and an English plural (the Mallas).
Never tied: a common English word (king, god, goddess, raja: our variants hold such English glosses); a variant or a
spelling of a name without a capital; a plural by a variant, or where its last letter is not the entity's (the
Gandharis are not Gandhari). A name that could be more than one of ours keeps each, with how many it could be.

Measured on a copy of claims.db against the 18:41 backup of context.db (the PC's own run prints its numbers):

| What | Count |
|---|---|
| Names on the 2,010 current claims | 3,917 |
| Tied | 1,706 (44%), in 1,816 tie rows |
| How | exact 1,342; a 1923 spelling 172; a vowel's length 88; a variant 36; a numbered namesake 28; plurals 40 |
| Tied to more than one of ours | 110 |
| The most claimed of ours | Janamejaya 91, Parikshit 75, Janaka 60, Kosala 51, Kuru 45, Pancala 40, Anga 31, Nimi 30 |
| Untied, the most named | Brahmadatta 31, the Aitareya Brahmana 28, the Licchavis 23 (and Licchavi 9), Assaka 18, the Bhagavati Sutra 18, Bimbisara 18 |

**For the entity mender (nothing merged here):** our own doubles, one key and two entities: Satapatha Brahmana 5726
and Satapathabrahmana 5767 (20 names), Rajasuya 95 and rajasuya 5371 (10), Matsyapurana 7715 and Matsya Purana 7769
(5), Visnupurana 5882 and Visnu Purana 5885 (4), Kurupancala 5838 and Kuru-Pancala 7089, Suci 12386 and suci 12433,
Uttarakuru 1573 and Uttara Kuru 3635, Taittiriyasamhita 2257 and Taittiriya Samhita 2415. Some kinds are wrong: Anga,
a kingdom, is "other". The untied names are names our entity list does not have; most are of texts we do not hold
(the Jatakas, the Aitareya Brahmana, the Jaina and Buddhist canon): phase D.

**Only an exact tie is certain.** The site will show an exact or a numbered tie as the name's; the others as probable,
with how each was made; and a name that could be more than one of ours not at all until our doubles are merged.

**The counts, corrected.** Section 1 said every passage is mirrored. The site holds 99,966 live passages (your count,
21 Oct, 20:45 IST). The three withdrawn texts (data/source_verdicts.jsonl) hold 73,878 here (the Yoga Vasistha 70,292,
the Karanagama 1,909, the Bodhicaryavatara's scan 1,677) and are off the site by design, which leaves 100,141 here. The
mirror's own check at 20:31 found its 386 groups equal, so the 175 between are differences it makes by design; the
first to look at is the Hayasirsa (1,706 here), held in repair, whose last version the site keeps. The names: 13,145
entities on both; mentions 40,054 there, 41,059 here. The vectors: 28,166 was counted with the retired rows.
docs/cloud/CHECKS_brain_counts_2026-10-21.sql counts the live rows text by text; the RUNBOOK's command counts them here.

**The Satapatha, for the translator.**
- Ours: `2015_405693_Shatpath-Brahmanam`, an OCR of kanda 14 only (its register: complete, "what is left is not
  Sanskrit").
- The edition of record is Albrecht Weber's of the Madhyandina recension (Berlin, 1855): its numbering (kanda,
  adhyaya, brahmana, kandika) is the one Raychaudhuri cites (Sat. Br. XIII. 5. 4. 1-3). There is no critical edition in
  the modern sense.
- Two e-texts: the Sanskrit Library's TEI text of the Madhyandina Satapatha (all fourteen kandas, from Weber's edition;
  kanda 12 input by Makoto Fushimi; CC BY-NC-SA 3.0), the better text of record; and GRETIL's (kandas 1 to 11, 13 and
  14; 12 not available), unaccented IAST, numbered 11.1.1.[1], the numbers "added mechanically", "for reference
  purposes only", copyright and terms "as for source file".
- The dandas: the Satapatha is prose and its unit is the kandika; neither e-text prints dandas within one. Ours would
  take them from a scan of Weber's print as a witness (Weber died in 1901: public domain), or mark what we add as
  editorial, never as the edition's. A kandika's end, with its number, is certain.
- With the whole text in, the Satapatha's cites in Part I can be located (the same numbering).
- Yours: which e-text (the Sanskrit Library's licence is non-commercial and share-alike, so our English of it would
  carry the same terms; GRETIL's asks for credit), and the download. From the PC, GRETIL gave "Unable to connect to
  the remote server"; the RUNBOOK's commands show why.

**D. R. Bhandarkar's Carmichael Lectures, 1918** (Lectures on the Ancient History of India on the Period from 650 to
325 B.C., University of Calcutta, 1919; public domain in India since 2011). Raychaudhuri cites them 15 times in Part I.
The scans: the National Virtual Library of India (the Central Secretariat Library's repository), AS-002576.pdf; and
HathiTrust's record 001867818 (full view). Yours: the download (the RUNBOOK's command asks for the size first). Then
its entry in scholar_claims.py's WORKS (md5, pages, the page map, its parts) and a three-page trial, about $0.03.

**B2, designed from the code (not built).** corpus-ingest (Srangam, `supabase/functions/corpus-ingest/lib.ts`) accepts
only its eight tables (`TABLES`) and maps each action to one C4 function; C4's `corpus_ingest` is one function with a
branch per table, and `corpus._spec` lists their keys. So B2 adds and replaces nothing the mirror runs on:
1. C19 (Lovable Cloud SQL): `corpus.claim_works`, `corpus.claims` (keyed by work, pdf page and n), `corpus.claim_cites`,
   `corpus.claim_links` (with the entity's canonical, the site's key of a name, how and cands); their own functions
   (`corpus_claims_manifest`, `_keys`, `_ingest`, `_retire`; service_role only), C4's untouched; a reader function,
   `corpus_reader_name_claims(canonical)`, behind the reader's gate, giving only claims whose quotation is exact or
   close, and only exact or numbered ties.
2. corpus-ingest: a second list of tables routed to those functions, tested beside lib_test.ts, deployed by Lovable.
3. corpus_sync.py: a claims group read from data/shelf/claims.db (only read), public-domain works only.
4. B3: the name page (CorpusNames.tsx) gets "What the scholars say": the claim, its page, its quotation, its stance,
   its cites and where we hold them.
"""

PLATFORM = """

## 84. The claims tied to our names; the counts corrected (DOCS81_2026_10_21)

**21 Oct, late night.** docs/BRAIN_PATH_2026-10-21.md, section 7.
- **Raychaudhuri, Part I, complete:** 99 pages, 2,010 claims (quotations 1,675 exact, 229 close, 18 not on the page, 88
  too short); reads ok 99 ($0.8893 on the reads), 13 failed reads kept with their cost.
- **CLAIMS_LINK_2026_10_21:** `--link` (free; context.db only read) ties the claims' names to our entities in tiers
  (exact, a variant, a vowel's length, a 1923 spelling, a numbered namesake, a plural), never a common English word;
  stored in claims.db (`claim_links`, `claim_link_runs`); `--show`, `--report` and `--csv` use them. On a copy: 1,706 of
  3,917 names tied (1,342 exact); 110 could be more than one of ours, among them our own doubles (the Satapatha Brahmana
  twice).
- **The counts:** the site holds 99,966 live passages (100,141 here in the live texts; the withdrawn hold 73,878); the
  page's table said all were mirrored, and is corrected.
- **The Satapatha:** ours is kanda 14 only; Weber's edition (1855) is the one of record; the Sanskrit Library's TEI
  text (all 14, CC BY-NC-SA 3.0) or GRETIL's (13 of 14): your choice and download.
- **B2:** additive (C19's own tables and functions; corpus-ingest's second list); designed, not built.

**Tests:** test_claims_link_2026_10_21 (6), test_docs81_2026_10_21 (3); test_claims_fix_2026_10_21's replay now ends at
the copy CLAIMS_LINK backed up.
"""

RUNBOOK = """

## The claims tied to our names; the counts checked (DOCS81_2026_10_21)

docs/BRAIN_PATH_2026-10-21.md, section 7. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`.
1. `Set-Location $A`; `python scripts\\patch_claims_link_2026_10_21.py` and `python scripts\\patch_docs81_2026_10_21.py`, each
   with `--check`, then without it; then `python -m unittest tests.test_claims_link_2026_10_21
   tests.test_claims_fix_2026_10_21 tests.test_scholar_claims_2026_10_21 tests.test_docs81_2026_10_21
   tests.test_docs80_2026_10_21`.
2. `python scripts\\scholar_claims.py --link` (free), then `--report`, `--show Parikshit`, `--csv
   data\\shelf\\phai1923_claims.csv`.
3. The counts: docs/cloud/CHECKS_brain_counts_2026-10-21.sql, B1 to B4 (read-only, one block at a time), beside the count
   of each text here.
4. The Carmichael Lectures and the Satapatha: the size first, then the download if you approve it.
5. Release with COMMIT_MSG_claimslink_20261021.txt.
"""

EP = """

## Addendum 2026-10-21 (71) (DOCS81_2026_10_21)

| # | Item | State |
|---|---|---|
| H3 | Raychaudhuri, Part I, as claims | Done: 99 pages, 2,010 claims |
| B1 | The claims' names tied to our entities | Built: CLAIMS_LINK_2026_10_21 (free); yours to run on the PC |
| B2 | The claims on the site (C19, corpus-ingest, corpus_sync) | Designed, additive: docs/BRAIN_PATH_2026-10-21.md section 7 |
| E1 | Our own doubles among the entities (the Satapatha Brahmana twice, and more) | Found by --link; for the entity mender |
| D1 | The Satapatha: the Sanskrit Library's TEI text or GRETIL's, Weber's scan as the witness | Yours: the choice and the download |
| C1 | D. R. Bhandarkar's Carmichael Lectures (1918) | Found (NVLI AS-002576, HathiTrust 001867818); yours: the download |
| K1 | The counts of section 1 | Corrected: 99,966 live passages on the site, not all 174,019 |
"""

STATE = """

## 16. 21 Oct, late night: the claims tied to our names (DOCS81_2026_10_21)

- **Raychaudhuri, Part I:** complete, 2,010 claims of 99 pages; the 20:31 mirror run sent the Surya's references and
  chapters (503 passages, 156 scholarly rows; its check: 386 groups equal).
- **B1:** `scholar_claims.py --link` (CLAIMS_LINK_2026_10_21): on a copy, 1,706 of 3,917 names tied; ties stored in
  claims.db.
- **The site's counts:** 99,966 live passages, 13,145 names, 40,054 mentions, 1,671 scholarly English rows; the brain
  page's table is corrected.
- **The repos:** the Automaton `d1f76ca9` and Srangam `aec5d41`, pushed, until this release.
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path(BP), BRAIN)]
NEEDS = "DOCS80_2026_10_21"


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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs81_" + stamp))
        t = p.with_name(p.name + ".tmp_docs81"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
