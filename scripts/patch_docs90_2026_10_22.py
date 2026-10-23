#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs90_2026_10_22.py  DOCS90_2026_10_22

Records the round asked for with "go with recommendations" (read as the approval of R1, U1, CI and the vision pass,
as recommended): the links our texts make between the names, stored (ENTITY_LINKS_2026_10_22); Raychaudhuri's claims
checked against our verses; one Ask page (ASK_UI_2026_10_22); the suite on GitHub (CI_TESTS_2026_10_22); the vision
round, priced; and the two questions answered: "is gretil nirukta better than our own reading, ingestion and
translation?" and "how are we building on the inter relationships and reviving hemchandra?"

Appends docs/DEBT_2026-10-22.md section 11, STATE section 25, a RUNBOOK section, PLATFORM section 93,
ENTERPRISE_PATH addendum 80, docs/ASKS_2026-10-22.md section 7 and docs/RELATIONS_AND_ASK_2026-10-22.md section 5,
each needing DOCS89_2026_10_22. Refuses unless scripts/entity_links.py, scripts/patch_ask_ui_2026_10_22.py and
.github/workflows/tests.yml (they come with this release) are here. Marker-idempotent per file, all-or-nothing,
backup first (.bak_docs90_<date>), line endings kept.

  python scripts\\patch_docs90_2026_10_22.py --check
  python scripts\\patch_docs90_2026_10_22.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS90_2026_10_22"
NEEDS = "DOCS89_2026_10_22"
REQUIRES = {"scripts/entity_links.py": "ENTITY_LINKS_2026_10_22",
            "scripts/patch_ask_ui_2026_10_22.py": "ASK_UI_2026_10_22",
            ".github/workflows/tests.yml": "CI_TESTS_2026_10_22"}

DEBT = """
## 11. The links stored, the scholars checked, one Ask page, the suite on GitHub; the Nirukta (DOCS90_2026_10_22)

- **Released:** `cdba881c` (RELATIONS_CENSUS, DOCS89), pushed; the suite on the PC: 175 modules, 1,363 tests, 185
  skipped, every module passing. "Go with recommendations" is read as the approval of what was recommended: R1, U1,
  CI and the vision pass (alerts, the kinship trial, H2 and the Daivat-Sanhita stay yours).
- **R1, the links stored (ENTITY_LINKS_2026_10_22, `scripts\\entity_links.py`, new, free):** "together" (two names in
  one passage) and "near" (in two passages of one text no more than 5 apart); lists of more than 12 names and retired
  texts left out, as relations_census.py. On the 19:04 backup, read immutable in the VM, in 11 seconds: 45,994 pairs
  together (the census's number), 235,002 near. `--apply` makes a backup, then rebuilds the table `entity_links`
  whole in one transaction; refuses while the dashboard runs a writer. Not applied yet: yours to run.
- **Raychaudhuri's claims against our verses (`--claims`, read-only):** of Part I's 2,010 claims, 387 name two of our
  names as subject and object: 78 are named together in a passage of ours, 64 near, 237 both named but never near, 8
  with a name not in our live texts. Synchronisms (contemporary_of, 32): 5 together, 1 near, 26 not. Borne out:
  Janaka with Yajnavalkya (33 passages), with Ajatasatru (3), with Budila Asvatarasvi (2); Yajnavalkya the pupil of
  Uddalaka Aruni (1); Devapi and Santanu brothers, in our Nirukta (p38.2, p38.3). Not: Uddalaka Aruni, Svetaketu,
  Pravahana Jaivali or Asvapati with Janaka (named in our Satapatha more than 5 passages apart, or in texts we do not
  hold). A wider window finds more and adds noise: 10 passages, 409,203 pairs and 78 claims near; 25, 806,123 and 99.
  The unit wanted is the chapter, but `passages.chapter` holds labels ("kanda", "sarga" in Devanagari), not numbers,
  and the Satapatha scan has a verse reference on 390 of its 2,441 passages.
- **What the claims cite (1,280 citations):** the Jataka 171, the Mahabharata 121 (we hold the Adiparvan), the Vayu
  Purana 84, the Satapatha 72, the Aitareya Brahmana 71, the Visnu Purana 59, the Vedic Index 53, the Matsya 40, the
  Ramayana 34, the Rgveda 28 (we hold vol. ii, without English), the Chandogya 17. GRETIL's TEI has the Visnu Purana
  (critical), the Matsya (1-176), the Chandogya (with commentary), the Ramayana and the Kausitaki Brahmana; of the
  Vayu only the Revakhanda. Names are found in the English, so a text adds links once it is translated (E).
- **U1, one Ask page (ASK_UI_2026_10_22, `scripts\\patch_ask_ui_2026_10_22.py`):** scripts/ask.html rewritten (the
  answer with numbered citations; the verses beside it in Devanagari, IAST and English, the scholarly English first;
  badges; the names as questions; what the answer read; copy; recent questions; phone) and `_ask_enrich` in
  dashboard.py (the sources also carry the Sanskrit, the IAST, the engines, the register's state, the scholarly
  English where it passed and its Sanskrit is unchanged, and the names; read-only, free). The model is sent the same
  as before. Rendered in Chromium, wide and phone, with a made-up answer. The site's Ask waits for ask-site (A2).
- **CI (CI_TESTS_2026_10_22, `.github/workflows/tests.yml`, new):** the suite as the PC runs it (scripts/run_tests.ps1,
  checked under PowerShell 7 on Linux), Python 3.13 (requirements.txt resolves there); on Ubuntu for each push to main
  and each pull request, on Windows by hand only; the token reads the repository and nothing more; no secret; never
  deploys. Its first run says what a clean checkout lacks.
- **Found:** `scripts/backfill_missing.py` is in the repository and does not parse (its function body lost its
  indentation); nothing imports it. `scripts/diag_coverage.py` needs Python 3.12 or later (quotes inside an f-string):
  fine on the PC, not on 3.10.
- **The spend:** at 19:04 the cap's counter read $85.58 of $95, $9.42 left (the $4.42 in DOCS84 was under the $85
  cap, raised to $95 at 09:53).
- **The Nirukta, asked "is gretil nirukta better than our own reading, ingestion and translation?":** our text
  (`nirukta`, 2,095 passages, 2,031 with English; the engine recorded is Flash on 1,922, Pro on 146) is read from
  inbox\\nirukta_0001-0224.pdf, which is not a scan of a printed book but a typeset, accented PDF of the Maharishi
  University of Management's Vedic Literature Collection (its running head). Pages 1-15 are the Nighantu (836
  passages: its word lists cut into a word or two each); pages 16-224 the Nirukta (1,259). Its PDF carries a text
  layer in an old font encoding, unreadable as is. GRETIL's `sa_yAska-nirukta` is Lakshman Sarup's edition (CC
  BY-NC-SA 4.0, published with credit by L1), the Nirukta only: GRETIL has no Nighantu of Yaska. Measured against it:
  ours (Tesseract) 70.74%, vision 75.33%; their own misreadings 9.57 and 4.95 in 100 aksharas; 16.37 shared, read
  alike by both engines and so in the print, not the OCR: the e-text writes vowel sandhi open (a short a the print
  elides, 232 times; ti + i for the print's long ti, 158; tha + a, 73) and has a dental where the print has a
  retroflex (s and s-dot 79, n and n-dot 65, ni 74); which side is right there is read on a sample of pages before
  adoption (an e-text typed in a Latin scheme can lose a retroflex to a slip of the shift key). So for the Nirukta
  proper, Sarup's text is the better text to translate, our reading the weaker; for the Nighantu ours is the only
  text, and the weakest part (Tesseract on accented type, Latin debris, lists cut up). GRETIL has no English.
- **The vision round, priced:** six texts have their page PDFs in the inbox under their own names: Narasimha 309
  pages, Samaveda 257, Yajnavalkya 82, Surya 55, Parasara 47, Gautama 27; 777 pages, about $3.01 at $0.00387 a page.
  Manu's 208 page PDFs are named smriti_14manu_smriti (the _seg text was cut from them): about $0.80, its plan first.
  The Bodhicaryavatara has no page image here: its text is archive.org's OCR of the 1960 edition
  (sources\\Bodhicaryavatara\\...djvu.txt), which ocr_benchmark.py counts as "unrecorded"; its vision reading waits for
  the scan. In all about $3.81.
"""

STATE = """
## 25. 22 Oct, night: the links, the scholars' check, one Ask page, CI (DOCS90_2026_10_22)

| What | State |
|---|---|
| Release | `cdba881c` pushed; DOCS90 and its code ready (ENTITY_LINKS, ASK_UI, CI_TESTS) |
| entity_links | built and tested; not applied: `python scripts\\entity_links.py --apply` (a backup first) |
| The scholars' check | 387 of Part I's claims checked: 78 together, 64 near, 237 not near, 8 not ours |
| Ask on the PC | the new page with the patch; the sources' new fields after a restart of the dashboard |
| Ask on the site | none yet (A2) |
| CI | the workflow comes with the release; Ubuntu on each push, Windows by hand |
| The vision round | 7 texts, about $3.81; the Bodhicaryavatara waits for its scan |
| The Nirukta | the GRETIL witness to be translated (about $2.40 by Flash); the Nighantu to be mended |
| The spend | $85.58 of $95 at 19:04 |
"""

RUNBOOK = """
## The links, the scholars' check, the Ask page, CI and the vision round (DOCS90_2026_10_22)

From the repository root, in a PowerShell window (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`).

1. The release's patches: `python scripts\\patch_ask_ui_2026_10_22.py --check`, then without --check; the same for
   `scripts\\patch_docs90_2026_10_22.py`. Then `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.
2. The links (free): `python scripts\\entity_links.py --name Janaka` counts and writes nothing; with the dashboard idle,
   `python scripts\\entity_links.py --apply` (a backup to D:\\backups first, then the table rebuilt whole).
   Undo: restore the backup, or `DROP TABLE entity_links; DROP TABLE entity_link_runs;`.
3. The scholars' check (free, read-only): `python scripts\\entity_links.py --claims data\\shelf\\claims.db`; it writes
   exports\\claims_in_our_texts.csv and .json.
4. The Ask page: open http://127.0.0.1:5057/ask; the Sanskrit, the names and the scholarly English beside each verse
   come after the dashboard is restarted, when it is idle.
5. CI: the workflow runs on GitHub after the push (Actions, "tests"); Windows: Actions, "tests", Run workflow. To stop
   it, disable the workflow there, or delete .github\\workflows\\tests.yml.
6. The vision round (paid, about $3.81): for each text, the plan first (free:
   `python scripts\\ocr_consensus.py --doc upapurana_narasimha_purana --threshold 101 --include-unassessed`), then with
   `--yes --max-usd 1.40`; then `python scripts\\source_fidelity.py --ref db:upapurana_narasimha_purana__w_gretil
   --cand db:upapurana_narasimha_purana --cand vision:upapurana_narasimha_purana --pair
   vision:upapurana_narasimha_purana,db:upapurana_narasimha_purana`; at the end `python scripts\\ocr_benchmark.py`.
   It writes data\\raw_vision and data\\raw_merged, never the database.
"""

PLATFORM = """
## 93. entity_links; what Ask's sources carry; the suite on GitHub (DOCS90_2026_10_22)

- **entity_links** (data/context.db, by `scripts\\entity_links.py --apply`, rebuilt whole): a, b (entities.id, a < b),
  rel ("together": one passage; "near": two passages of one text no more than 5 apart), passages, texts, docs (up to
  8 codes), places (JSON, up to 3 [passage_id, code, ref]), built_at, mark; PRIMARY KEY (a, b, rel), an index on b.
  entity_link_runs: one row per --apply. Lists (more than 12 names) and retired texts are left out. Only this script
  writes them; nothing reads them yet (Ask v2, the name page and the mirror C20 will).
- **Ask's sources** (`/api/ask`, ASK_UI_2026_10_22): n, tag, doc, verse_ref, page_no, idx, english as before; and pid,
  sanskrit (700 characters), iast, mt (the English's engine), ocr (the reading's engine), witness, state (the
  register's), scholar, scholar_engine, scholar_state ("passed" or "accepted"; only when its Sanskrit is unchanged and
  it was not rejected), names ([{name, kind}], up to 8), each only when the database has it. The prompt is unchanged.
- **CI** (`.github/workflows/tests.yml`): scripts/run_tests.ps1 under PowerShell 7 with Python 3.13, Ubuntu on each
  push to main and pull request, Windows by hand; `permissions: contents: read`; no secret; no deploy.
"""

EP = """
## Addendum 2026-10-22 (80) (DOCS90_2026_10_22)

| Key | Item | State |
|---|---|---|
| relations-together | The named-together links stored (entity_links) | Built and tested: yours to apply (--apply, a backup first) |
| claims-check | Raychaudhuri's claims checked against our verses | Done for Part I: 78 together, 64 near, 237 not near, 8 not ours |
| ask-ui | One Ask page | Built for the PC (ASK_UI); the site waits for ask-site |
| ci-tests | The suite on GitHub | Built: Ubuntu on each push, Windows by hand |
| witness-vision-pairs | The vision round | Commands given: 7 texts, about $3.81; the Bodhicaryavatara waits for its scan |
| nirukta-witness | The GRETIL Nirukta (Sarup) translated, judged against ours, released | Yours: about $2.40 by Flash |
| nighantu-mend | The Nighantu (pages 1-15 of the Nirukta's PDF): its lists regrouped, read again from vision | Next |
| nirukta-source | The Nirukta's PDF is the Maharishi University of Management's typeset text; its terms | Yours to read |
| texts-to-seek | The texts Raychaudhuri cites that we lack (Visnu, Matsya, Chandogya, Ramayana, Kausitaki in GRETIL) | Next: after nirukta-witness |
| broken-script | scripts/backfill_missing.py does not parse | Next: mend or retire |
"""

ASKS = """
## 7. 22 Oct, night: answered (DOCS90_2026_10_22)

- **"go with recommendations":** read as the approval of R1, U1, CI and the vision pass. Built: entity_links.py,
  the Ask page (ASK_UI), the workflow (CI_TESTS); the vision round priced and its commands given (yours to run).
- **"is gretil nirukta better than our own reading, ingestion and translation?":** for the Nirukta proper, yes as the
  text to translate: Sarup's edition, typed, against our Tesseract reading of a typeset PDF (9.57 misreadings in 100
  aksharas of its own; vision 4.95). Not for the Nighantu, which GRETIL does not have. Our English (2,031 passages)
  was made from the weaker text; GRETIL has none. The path: translate the witness, judge it against ours, release it;
  mend the Nighantu. DEBT section 11.
- **"how are we building on the inter relationships and reviving hemchandra?":** the links are stored by
  entity_links.py (R1), and Raychaudhuri's Part I is checked against them: 387 claims name two of our names; 78 are
  borne out by a passage that names both, 64 by passages near each other, 237 not yet. The ones not borne out name
  the texts to seek (texts-to-seek). Next: the claims on the site (B2), "What the scholars say" (B3), the kinship
  trial (R2, yours), Part II.
"""

RELATIONS = """
## 5. 22 Oct, night: R1 built, the scholars checked, U1 and CI built (DOCS90_2026_10_22)

- **R1:** `scripts\\entity_links.py` (ENTITY_LINKS_2026_10_22). "Near" is added to "together" because a court or a
  debate is told over several passages: in the Brhadaranyaka, Janaka is named where the debate opens and Uddalaka
  Aruni where he questions Yajnavalkya, many passages on. The window is 5 passages (235,002 pairs); 10 and 25 were
  measured (409,203 and 806,123) and not taken: more claims found, more noise. A chapter is the right unit once the
  texts carry chapter numbers (the e-text witnesses do; the scans mostly do not).
- **The scholars' check** (B, with R1): Part I's claims whose subject and object are both ours: 387. Named together
  78, near 64, both named but never near 237, a name not ours 8. By relation: son_of 16 together, 6 near, 14 not;
  king_of 9, 8, 26; contemporary_of 5, 1, 26; brother_of 3, 17, 0. The report: exports\\claims_in_our_texts.csv.
- **U1:** the PC's page is built (ASK_UI_2026_10_22). For the site, the same page waits for A2 (an Ask behind the
  readers' gate); its search page can take the same source card meanwhile (a Srangam change, yours to ask Lovable for).
- **CI:** built (CI_TESTS_2026_10_22). Staging and alerts are still open (section 4).
- **Order now:** apply R1; the claims on the site (B2) and the named-together links (C20) as one mirror step (R4); then
  A1 (Ask reads the links and the claims); the Nirukta witness translated; the texts to seek.
"""

TARGETS = [(Path("docs/DEBT_2026-10-22.md"), DEBT),
           (Path("docs/STATE_2026-10-18.md"), STATE),
           (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/PLATFORM_2026-10-04.md"), PLATFORM),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP),
           (Path("docs/ASKS_2026-10-22.md"), ASKS),
           (Path("docs/RELATIONS_AND_ASK_2026-10-22.md"), RELATIONS)]


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (it comes with this release). Nothing written." % (f, m))
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs90_" + stamp))
        t = p.with_name(p.name + ".tmp_docs90"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
