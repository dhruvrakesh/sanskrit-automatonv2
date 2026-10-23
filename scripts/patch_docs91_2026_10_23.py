#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs91_2026_10_23.py  DOCS91_2026_10_23

Records 23 Oct: the links applied and the scholars checked on the PC; the release 553b2160 and the suite on GitHub; the
site's own count of the pairs; the vision round measured; the decisions taken as "go with your understanding" (the
Nirukta's PDF and its translation, the alerts, the kinship trial for all three indexes, H2, the Daivat-Sanhita); and
what this release builds: the indexes' kinships read and checked (RELATIONS_INDEX_2026_10_23), the Professor on the
PC's Ask (ASK_PROF_2026_10_23), the links kept current hourly (ENTITY_LINKS_SCHED_2026_10_23), the desk's health
mailed (HEALTH_2026_10_23, docs/cloud/C19), and "Named together with" on the site (docs/cloud/C20, the Srangam patch
NAME_LINKS_SITE_2026_10_23).

Appends docs/DEBT_2026-10-22.md section 12, STATE section 26, a RUNBOOK section, PLATFORM section 94, ENTERPRISE_PATH
addendum 81, docs/ASKS_2026-10-22.md section 8 and docs/RELATIONS_AND_ASK_2026-10-22.md section 6, each needing
DOCS90_2026_10_22. Refuses unless what it records comes with this release. Marker-idempotent per file,
all-or-nothing, backup first (.bak_docs91_<date>), line endings kept.

  python scripts\\patch_docs91_2026_10_23.py --check
  python scripts\\patch_docs91_2026_10_23.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS91_2026_10_23"
NEEDS = "DOCS90_2026_10_22"
REQUIRES = {"scripts/kin_index.py": "RELATIONS_INDEX_2026_10_23",
            "scripts/health_watch.py": "HEALTH_2026_10_23",
            "scripts/patch_ask_prof_2026_10_23.py": "ASK_PROF_2026_10_23",
            "scripts/patch_links_sched_2026_10_23.py": "ENTITY_LINKS_SCHED_2026_10_23",
            "scripts/patch_health_2026_10_23.py": "HEALTH_2026_10_23",
            "scripts/patch_srangam_name_links_2026_10_23.py": "NAME_LINKS_SITE_2026_10_23",
            "docs/cloud/C19_health_mail_2026-10-23.sql": "HEALTH_MAIL_C19_2026_10_23",
            "docs/cloud/C20_name_links_2026-10-23.sql": "NAME_LINKS_C20_2026_10_23"}

DEBT = """
## 12. 23 Oct: the links applied, the vision round measured, the decisions, and what this release builds (DOCS91_2026_10_23)

- **Done on the PC:** `python scripts\\entity_links.py --apply`: a backup
  (D:\\backups\\context_pre_links_20261023_053008.db), then 45,994 pairs together and 235,002 near stored. The
  scholars' check on the PC gave the VM's numbers: of 387 of Raychaudhuri's claims, 78 named together, 64 near, 237
  never near, 8 not ours.
- **Released:** `553b2160` (ENTITY_LINKS, ASK_UI, CI_TESTS, DOCS90), pushed; 19 files, among them
  .github/workflows/tests.yml. The suite on the PC: 179 modules, 1,386 tests, 185 skipped, every module passing.
- **The site's own count** (Lovable Cloud SQL, read-only, the desk's list rule): 45,183 pairs, 4,822 in two passages
  or more, 675 in five or more, 1,516 in two texts or more, 241 lists left out; the PC: 45,994, 4,983, 681, 1,539, 248.
  The difference is the texts only the PC holds (the site has 40,739 live mentions, the PC 41,744).
- **The vision round, measured** (ocr_benchmark.py, 23 Oct 18:22; own misreadings in 100 aksharas, vision against the
  other reading of the same print; shared is the print's or the edition's): Narasimha 2.56 against Tesseract's 11.00
  (shared 3.01; agreement 92.80% against 83.22%); Manu 2.88 against 11.81 (4.17; 91.82% against 81.99%); Parasara 3.22
  against 12.75 (4.30; 91.36% against 80.57%); Surya 4.38 against 12.29 (5.61); Samaveda 6.76 against 11.33 (10.39);
  Gautama 4.98 against 7.39 (24.29: GRETIL's Gautama is another edition, so the witness measures little there). In all,
  vision 10 texts, 461,146 aksharas, 85.6% agreement, 3.85 own misreadings in 100; Tesseract 11.45. Not done:
  Yajnavalkya (no vision page was made); 7 pages failed vision (Narasimha 2, Samaveda 2, Surya 2, Gautama 1). The
  benchmark still lists smriti_14manu_smriti_seg as read by Tesseract alone: its vision reading is under the pages'
  name, smriti_14manu_smriti (a label to mend).
- **Decided, on "go with your understanding":**
  - *The Nirukta's PDF:* the text is ancient; the PDF is the Maharishi University of Management's typeset edition,
    shared freely, with no terms on the pages read. It stays in use for the Nighantu, with credit (the ledger's source:
    "Maharishi University of Management, Vedic Literature Collection, typeset PDF"); the PDF itself is never published.
    For the Nirukta proper, Sarup's GRETIL text becomes the text of record once translated and judged (credited, CC
    BY-NC-SA 4.0, by L1). Sought: a public-domain print of the Nighantu (Sarup's own edition, The Nighantu and the
    Nirukta, 1920-27; Sarup died in 1946), to replace the MUM text there.
  - *GRETIL's Nirukta translated:* by Flash, the working English, 649 units, about $2.40 at the measured $0.0037 a
    passage: a trial of 20 first. What we add over GRETIL: the English (GRETIL has none), the names and their links
    from it, the alignment with our print (the variants both our readings share), the Nighantu.
  - *Alerts:* built (HEALTH_2026_10_23 and C19); the mail goes to the super admin through the Corner's mailer.
  - *The kinship trial, for all three indexes:* built (RELATIONS_INDEX_2026_10_23): 100 entries of each first, then
    the full run, priced by its plan.
  - *H2, the indexes' relations on the site:* the derived relations (subject, relation, object, the index's own words
    of at most 25, its reference) may go to the site with the credit and the CC BY-NC-SA 3.0 notice, while the site
    stays non-commercial; the entries themselves stay on the PC. (The indexes are old enough to be free: Macdonell and
    Keith 1912, Soerensen 1904, Dikshitar 1951-55, who died in 1953; the Cologne edition is the licensed part.)
  - *The Daivat-Sanhita:* Satavalekar died in 1968, so his compilation is protected in India to the end of 2028. It is
    withdrawn from the site (the readers' list included) until 1 January 2029 and kept on the PC:
    `repair_text.py --withdraw` (your command; reversible with --release).
- **Built in this release:**
  - *RELATIONS_INDEX_2026_10_23, `scripts\\kin_index.py`:* the kinships, schools and rule that the Purana Index, the
    Vedic Index and Soerensen state, read by Flash several entries to a call (metered; the cap asked; --max-usd), kept
    only when their words stand in the entry and their direction agrees with the words; tied to our names; checked
    against our verses (entity_links) and Raychaudhuri; exported as edges, a matrix, the agreement of the sources, the
    father-to-son lines and sourced cards. data/shelf/kin.db. Candidates: Purana Index 7,075 entries, Vedic Index 1,186,
    Soerensen 2,941; the trial of 300 about $0.11, every one about $3.97 (the plan's estimates).
  - *ASK_PROF_2026_10_23:* the Professor on the PC's Ask: the scholarly English and the IAST, the names and their links,
    Raychaudhuri's claims and the indexes' checked relations, each statement numbered [S1] ...; told to keep apart the
    verses, the scholars and its own inference, and never to speak as any real person.
  - *ENTITY_LINKS_SCHED_2026_10_23:* the hourly maintenance task's step d: the links rebuilt when the names change (the
    04:00 backup standing for the rebuild's), the scholars' check refreshed, the kinships checked once read.
  - *HEALTH_2026_10_23 and C19:* the desk's health (maintenance, mirror, daily backup, disk, cap, links) in its
    heartbeat; the site mails the super admin on warn or fail, again after 12 hours or a change, and once when all is
    well again. A desk that does not come by at all mails nothing: its last visit shows in the Corner.
  - *C20 and NAME_LINKS_SITE_2026_10_23:* the site counts the pairs itself from its mentions (a materialized view,
    refreshed nightly by pg_cron), and a name's page lists "Named together with", each with its first shared passage.
- **Found:** D:\\backups holds 150 GB (each witness's pre-ingest copy is 2.1 GB); 173 GB free on that drive. The health
  check warns under 50 GB.
"""

STATE = """
## 26. 23 Oct: the kinships, the Professor, the links hourly, the health mailed, named together online (DOCS91_2026_10_23)

| What | State |
|---|---|
| Release | `553b2160` pushed; DOCS91 and its code ready |
| entity_links | applied on the PC (45,994 together, 235,002 near); hourly from step d once ENTITY_LINKS_SCHED is applied |
| The scholars' check | 387 claims: 78 together, 64 near, 237 not near, 8 not ours |
| The kinship trial | built; 100 entries of each index (about $0.15) yours to run |
| The Professor | built for the PC's Ask (mode Professor); the site's Ask waits for A2 |
| Health mail | built: HEALTH in the desk's heartbeat; C19 to paste |
| Named together online | built: C20 to paste; the Srangam patch to apply, test and Publish |
| The vision round | 6 of 7 read and measured; Yajnavalkya and 7 failed pages to read again |
| The Nirukta | GRETIL's to be translated (about $2.40); the Nighantu to mend; a PD print of the Nighantu sought |
| The Daivat-Sanhita | to be withdrawn from the site until 1 January 2029 |
"""

RUNBOOK = """
## The kinships, the Professor, the links hourly, the health mail, named together online (DOCS91_2026_10_23)

From the repository root (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`), the dashboard idle for the
patches to dashboard.py and corner_worker.py:

1. `python scripts\\patch_ask_prof_2026_10_23.py --check`, then without --check; the same for
   `patch_links_sched_2026_10_23.py`, `patch_health_2026_10_23.py` and `patch_docs91_2026_10_23.py`. Then
   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`. Restart the dashboard when it is idle.
2. The kinship trial: `python scripts\\kin_index.py` (the plan, free), `python scripts\\kin_index.py --yes` (100 of each
   index, --max-usd 0.50), then read exports\\kin_cards.md and kin_agreement.csv; `--show Janamejaya` for one name.
3. The Professor: http://127.0.0.1:5057/ask, Professor.
4. The health: `python scripts\\health_watch.py` (free). On the site, paste docs\\cloud\\C19_health_mail_2026-10-23.sql,
   then its checks (C19_checks_2026-10-23.sql), one query a paste.
5. Named together online: paste docs\\cloud\\C20_name_links_2026-10-23.sql and its checks; then in D:\\srangam-42267
   (`git pull --rebase --autostash` first): `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\
   patch_srangam_name_links_2026_10_23.py" --check`, then without --check; `npm run typecheck`, `npx vitest run`,
   `npm run build`; commit by name and push; Publish in Lovable.
6. The Nirukta: `python scripts\\translate_passages.py --db data\\context.db --doc nirukta__w_gretil --engine
   gemini:gemini-2.5-flash --limit 20` (a trial), then without --limit.
7. The Daivat-Sanhita: `python scripts\\repair_text.py --doc Daivat-Sanhita --withdraw "Satavalekar's compilation,
   protected in India to the end of 2028: off the site until 1 January 2029"`; the next mirror run retires it.
8. The vision round's rest: `python scripts\\ocr_consensus.py --doc smriti_06yagyavalkya_smriti --threshold 101
   --include-unassessed` (the plan), then with `--yes --max-usd 0.40`; the failed pages with `--retry-refused`.
"""

PLATFORM = """
## 94. kin.db; the Professor's sources; step d; the heartbeat's health; corpus.name_links (DOCS91_2026_10_23)

- **data/shelf/kin.db** (scripts/kin_index.py): kin_reads (one per call: the entries, the reply, the cost), kin_done
  (each entry's latest read, by the entry's sha256), kin (subject, relation, object, words, refs, words_check exact |
  close | none, direction agrees | disagrees | unknown), kin_ties (rebuilt by each check: the tied entities, the
  verdict against entity_links, Raychaudhuri agrees | reversed | differs). The relations' vocabulary is fixed (23).
- **/api/ask, mode professor** (ASK_PROF_2026_10_23): scholarly = {names: [{name, kind, in_sources, together}],
  items: [{n: "S1", kind: claim | index, about, source, where, text, note}], read: {links, claims, indexes}}; the
  model's evidence in the order PASSAGES, NAMES, SCHOLARS AND INDEXES; metered as ask_prof.
- **The maintenance task, step d** (ENTITY_LINKS_SCHED_2026_10_23): entity_links.py --scheduled --claims
  data\\shelf\\claims.db; kin_index.py --check when kin.db is there.
- **corner.worker.info.health** (HEALTH_2026_10_23): {status ok | warn | fail, at, problems}; the first thing cut.
  corner.health_state (C19): the last status and problems, when mailed. corner.outbox kind 'health'.
- **corpus.name_links** (C20): name_a < name_b, passages, texts, the first shared passage; nightly
  srangam-corpus-name-links (04:40 UTC); public.corpus_reader_name_links(p_canonical, k) for the readers.
"""

EP = """
## Addendum 2026-10-23 (81) (DOCS91_2026_10_23)

| Key | Item | State |
|---|---|---|
| relations-index | The indexes' kinships read whole and checked | Built (kin_index.py): the trial (100 of each) yours |
| relations-check | Each kinship against our verses and Raychaudhuri | Built, in kin_index.py's check |
| ask-v2 | Ask on the PC reads the names, links, claims and kinships | Built: the Professor (ASK_PROF) |
| links-sched | The links kept current by the hourly task | Built (ENTITY_LINKS_SCHED) |
| alerts | A mail when the desk's tasks fail | Built (HEALTH, C19): C19 to paste |
| names-ui | The name page: named together | Built (C20, NAME_LINKS_SITE): to paste, apply and Publish |
| nirukta-witness | GRETIL's Nirukta translated, judged, released | Decided: the trial of 20, then 649 (about $2.40) |
| nirukta-source | The Nirukta's PDF (MUM) | Decided: in use with credit for the Nighantu; never published |
| nighantu-print | A public-domain print of the Nighantu (Sarup) | Next: sought |
| h2 | The indexes' relations on the site | Decided: the derived relations with credit and the licence's notice |
| daivat-rights | The Daivat-Sanhita | Decided: withdrawn until 1 January 2029 (your command) |
| witness-vision-pairs | The vision round | 6 of 7 measured; Yajnavalkya and 7 pages to read again |
| benchmark-label | ocr_benchmark lists Manu as Tesseract alone | Next: mend the label |
| ask-site | The Professor on the site | Next (A2): an edge function behind the readers' gate |
| claims-mirror | Raychaudhuri's claims on the site (B2) | Next |
"""

ASKS = """
## 8. 23 Oct: answered and decided (DOCS91_2026_10_23)

- **"the terms of the Nirukta PDF, translating GRETIL's Nirukta - go with your understanding and improvements over
  present GRETIL etc work":** decided (DEBT section 12): the MUM PDF stays in use for the Nighantu with credit; the
  Nirukta proper is translated from Sarup's GRETIL text and judged before it is the text of record; what we add over
  GRETIL is the English, the names and links, the alignment with our print, and the Nighantu.
- **"alerts":** built (HEALTH_2026_10_23, C19).
- **"the 100-entry kinship trial for all texts ... matrices and Debroy-esque / Hemchandra-esque explanations":** built
  (kin_index.py): the three indexes; the matrix (relation by index and verdict), the sources' agreement, the father-to-
  son lines, and cards that explain each relation from its sources only. The Professor gives the explanation in prose
  from the same evidence, never in any real scholar's voice.
- **"H2 and the Daivat-Sanhita":** decided (DEBT section 12).
- **"are all UI/UX/local/online updated and cronning ... for probot in action":** the PC: the Ask page with the
  Professor; the links, the scholars' check and the kinships' check hourly (step d). Online: "Named together with" on
  the name pages with C20 and the Srangam patch, refreshed nightly; the Professor on the site is next (A2), and the
  scholars' claims there (B2).
"""

RELATIONS = """
## 6. 23 Oct: R2, R3, A1, U2 built; R4 by the site's own view (DOCS91_2026_10_23)

- **R2 and R3** (relations-index, relations-check): scripts/kin_index.py, all three indexes, a trial of 100 entries
  each (about $0.11), then the full run (11,202 candidate entries, about $3.97 by the plan). Nothing is taken on the
  model's word: the words in the entry, the direction, the names tied, our verses, Raychaudhuri.
- **A1** (ask-v2): the Professor (ASK_PROF_2026_10_23).
- **R4** (relations-mirror) for the named-together links: the site counts them from its own mentions (C20), so nothing
  new is mirrored; the claims (B2) and the indexes' relations (H2 decided) are mirrored next.
- **U2** (names-ui): "Named together with" (NAME_LINKS_SITE_2026_10_23).
- **Kept current:** the PC hourly (step d), the site nightly (pg_cron).
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
        shutil.copy2(p, p.with_name(p.name + ".bak_docs91_" + stamp))
        t = p.with_name(p.name + ".tmp_docs91"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
