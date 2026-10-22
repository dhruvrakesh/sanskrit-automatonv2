#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs89_2026_10_22.py  DOCS89_2026_10_22

Records the last of 22 Oct: the release 8f503ad2; Srangam's SEO Phase AN published and checked; who reads the corpus
(J1: the readers' list) and the Daivat-Sanhita (J2: not a site text); the companion repositories' changes, read, not
committed; how the names are joined, measured (RELATIONS_CENSUS_2026_10_22); what Ask reads, on the PC and the site;
whether this is the enterprise way; the path to a better Ask (docs/RELATIONS_AND_ASK_2026-10-22.md).

Appends docs/DEBT_2026-10-22.md section 10, STATE section 24, a RUNBOOK section, PLATFORM section 92, ENTERPRISE_PATH
addendum 79 and docs/ASKS_2026-10-22.md section 6, each needing DOCS88_2026_10_22. Refuses unless
docs/RELATIONS_AND_ASK_2026-10-22.md and scripts/relations_census.py (they come with this release) are here.
Marker-idempotent per file, all-or-nothing, backup first (.bak_docs89_<date>), line endings kept.

  python scripts\\patch_docs89_2026_10_22.py --check
  python scripts\\patch_docs89_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS89_2026_10_22"
NEEDS = "DOCS88_2026_10_22"
REQUIRES = {"docs/RELATIONS_AND_ASK_2026-10-22.md": "DOCS89_2026_10_22",
            "scripts/relations_census.py": "RELATIONS_CENSUS_2026_10_22"}

DEBT = """
## 10. Published; who reads the corpus; how the names are joined; what Ask reads (DOCS89_2026_10_22)

- **Released:** `8f503ad2` (OCR_BENCHMARK, DOC_REGISTER, GRETIL_NEXT, DOCS88), pushed. **Published:** Srangam's
  `c4849e8` (SEO Phase AN); the curl.exe checks after Publish read the new page: the static canonical gone, 5 data-rh
  tags, 74 sitemap URLs, no retired slug.
- **Who reads the corpus (J1):** `corpus.reader_access` mode `readers`, set 9 Oct 01:29 UTC: the readers' list only,
  not every account. **The Daivat-Sanhita (J2):** not a site text (no row in public.srangam_texts); it is in the
  corpus, read by the readers' list alone. Its rights (daivat-rights) concern invited readers, not the public.
- **The companion repositories, read, not committed:** nartiang-legacy-web 3 files (+51, -5: CHANGELOG.md,
  docs/SEO.md, index.html); remix-of-dkegl-website 17 files (+298, -38), the largest scripts/generate-sitemap.mjs
  (154 lines changed), scripts/seo-guards.mjs (52), vite.config.ts (27) and index.html (22): its build changes, and
  its own CI (.github/workflows/ci.yml) runs on the push. Each is to be read before it is committed (another
  session's work).
- **The mirror at 20:31:** 386 groups equal, 0 different; the Hayasirsa held; the eight new witnesses stay on the PC.
- **How the names are joined (RELATIONS_CENSUS_2026_10_22, `scripts\\relations_census.py`, free, read-only),** from
  the 19:04 backup read immutable: 13,233 names and 41,744 mentions in 15,394 passages (15,239 of them with English:
  names are found in the English). Named together in one passage: 45,994 pairs, 4,983 in two passages or more, 681 in
  five or more, 1,539 in two texts or more. Janaka is named with Yajnavalkya in 33 passages, Videha 29, Ajatasatru,
  Gargya, Hasabalaki and Asvala 3 each, all in the Satapatha's book 14. No kinship or school is stored. The shelf
  prints them: the Purana Index "son of" in 4,759 entries, "father of" 1,424; Soerensen "son of" 1,490; the Vedic
  Index "patronymic" 645, "pupil of" 202. A pattern misreads them ("married the daughter of Ugrasena" as "daughter of
  Ugrasena"): they are to be read whole and checked (relations-index).
- **What Ask reads:** on the PC, the working English of the 12 passages nearest the question by meaning (26,848
  have vectors) and up to three editorial items, answered by Gemini Flash with citations, metered, under the cap; no
  Sanskrit, no scholarly English, no names, no links, no claims. On the site, search-corpus finds passages and
  generates no text: there is no Ask on the site. The name page lists the passages that name a name, nothing more.
- **Is this the enterprise way?** The discipline is (patches, tests, backups, the meter and the cap, the reader
  gate, the mirror's check, provenance); the process around it is not yet: no CI, no staging before Publish, no
  alert when a scheduled run fails, documents that only grow. docs/RELATIONS_AND_ASK_2026-10-22.md, section 4, says
  what each would take; CI and the alert are standing configurations, so yours to approve.
- **The path:** docs/RELATIONS_AND_ASK_2026-10-22.md, section 3 (R1 to R4, A1, A2, U1 to U3, E); R1 and U1 first.
"""

STATE = """
## 24. 22 Oct, last: published; the names measured; Ask read (DOCS89_2026_10_22)

- **Released:** the Automaton `8f503ad2`; Srangam `c4849e8`, published (the checks as expected).
- **Measured:** the names named together (45,994 pairs; 4,983 in two passages or more); no kinship stored; Ask reads
  the working English only, and the site has none.
- **Next:** R1 (the named-together links stored) and U1 (one Ask page), both free; then A1 (Ask reads the names,
  the scholarly English and the claims).
"""

RUNBOOK = """
## The names, measured; the companion repositories (DOCS89_2026_10_22)

docs/RELATIONS_AND_ASK_2026-10-22.md. In a new PowerShell window: `$A = "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`,
then `Set-Location $A`. Nothing below spends.
1. Apply: `python scripts\\patch_docs89_2026_10_22.py --check`, then without it. Then `powershell -ExecutionPolicy
   Bypass -File scripts\\run_tests.ps1`.
2. The census (reads data\\context.db read-only; the dashboard may run): `python scripts\\relations_census.py`, then
   `python scripts\\relations_census.py --name Janaka --no-write`. exports\\names_together.csv holds the pairs.
3. The companion repositories, read before any commit: `git -C "D:\\remix-of-dkegl-website" diff --stat` and
   `git -C "D:\\remix-of-dkegl-website" diff -- scripts/generate-sitemap.mjs`; the same for nartiang-legacy-web.
4. The decisions: ASKS section 6.
"""

PLATFORM = """
## 92. The names measured; the path to a better Ask (DOCS89_2026_10_22)

| Marker | Files | What |
|---|---|---|
| RELATIONS_CENSUS_2026_10_22 | scripts/relations_census.py, tests/test_relations_census_2026_10_22.py | names by kind; pairs named together (passages, texts, places); one name's neighbours; the shelf's kinship phrases counted, never stored; read-only |
| DOCS89_2026_10_22 | docs/RELATIONS_AND_ASK_2026-10-22.md (new), DEBT 10, STATE 24, RUNBOOK, this section, ENTERPRISE_PATH 79, ASKS 6 | the record and the path |

- **Ask, as built:** dashboard.py `api_ask` (the working English, by meaning, Gemini Flash, metered); Srangam's
  search-corpus (passages only). Neither reads the names or their links.
"""

EP = """
## Addendum 2026-10-22 (79) (DOCS89_2026_10_22)

| Key | Item | State |
|---|---|---|
| srangam-seo-publish | Srangam's SEO Phase AN | Done: c4849e8 published; the checks as expected |
| daivat-rights | The Daivat-Sanhita | Yours: J1 (the readers' list) and J2 (not a site text) answered; keep for the readers or --withdraw |
| companion-seo-commits | nartiang-legacy-web (3 files) and remix-of-dkegl-website (17 files) | Yours: read the diffs, then commit by name |
| relations-together | The named-together links stored (entity_links) | Next: free |
| relations-index | The shelf's kinships read whole and checked (a 100-entry trial) | Yours: the trial, priced by a dry run |
| relations-check | Each kinship checked against our verses | Next, after relations-index |
| relations-mirror | C19 (claims) and C20 (named together) on the site | Next, after relations-together; the index's kinships only by H2 |
| ask-v2 | Ask on the PC reads the scholarly English, the Sanskrit, the names, their links and claims | Next, after relations-together |
| ask-site | Ask on the site, behind the readers' gate, with a daily limit | Next, after ask-v2 is measured |
| ask-ui | One Ask page on the PC and the site | Next: free |
| names-ui | The name page: named together, the scholars, the indexes | Next, after relations-mirror |
| load-measure | Measured before any cut (test:perf, EXPLAIN) | Next: free |
| ci-tests | The suite on GitHub on every push (Ubuntu and Windows), never deploying | Yours: a standing configuration |
| alerts | A mail when the mirror or a task fails | Yours: a mail you receive |
| docs-consolidation | ASKS as the state; one ARCHITECTURE page; a RUNBOOK of current procedures | Next |
"""

ASKS = """
## 6. 22 Oct, last: answered, and the new keys (DOCS89_2026_10_22)

- **Answered:** J1, the corpus is read by the readers' list only (mode `readers`, 9 Oct). J2, the Daivat-Sanhita is
  not a site text. Srangam's SEO Phase AN is published and checked (srangam-seo-publish: Done).
- **Asked:** "how are we on the inter relationships and does that reflect in ask the corpus ... are you sure this is
  the enterprise way?" Answered in docs/RELATIONS_AND_ASK_2026-10-22.md: the names are joined through the passages
  only; no kinship is stored; Ask reads the working English only, and the site has no Ask; the discipline is
  enterprise-grade, the process around it not yet.
- **New keys** (ENTERPRISE_PATH 79): relations-together, relations-index, relations-check, relations-mirror, ask-v2,
  ask-site, ask-ui, names-ui, load-measure, ci-tests, alerts, docs-consolidation.
"""

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/ASKS_2026-10-22.md"), ASKS)]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first, or it comes with this release). Nothing written." % (f, m))
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
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs89_" + stamp))
        t = p.with_name(p.name + ".tmp_docs89"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
