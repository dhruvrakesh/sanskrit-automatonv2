#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs93_2026_10_24.py  DOCS93_2026_10_24

Records the evening of 24 Oct: release 58cddb1c; the site's C20 steps and why its fill could not finish (a self-join
the planner misjudged), mended by NAME_LINKS_FAST_2026_10_24 (C20d); the kinship full run measured (not finished:
Soerensen's last 2,243 entries); the lines of descent mended (KIN_LINES_2026_10_24); the Professor told to keep
numbered persons apart (ASK_HOMONYM_2026_10_24); how many of the indexes' persons our English names at all; the
Shukla Yajurveda's real price; and the enterprise path from here.

Appends docs/DEBT_2026-10-22.md section 14, STATE section 28 (and, once, a line under STATE's title that the newest
state is its last section), a RUNBOOK section, PLATFORM section 96, ENTERPRISE_PATH addendum 83, docs/ASKS_2026-10-22.md
section 10 and docs/RELATIONS_AND_ASK_2026-10-22.md section 8, each needing DOCS92_2026_10_24. Refuses unless what it
records comes with this release. Marker-idempotent per file, all-or-nothing, backup first (.bak_docs93_ and the date),
line endings kept.

  python scripts\\patch_docs93_2026_10_24.py --check
  python scripts\\patch_docs93_2026_10_24.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS93_2026_10_24"
NEEDS = "DOCS92_2026_10_24"
REQUIRES = {"scripts/patch_kin_lines_2026_10_24.py": "KIN_LINES_2026_10_24",
            "tests/test_kin_lines_2026_10_24.py": "KIN_LINES_2026_10_24",
            "scripts/patch_name_links_fast_2026_10_24.py": "NAME_LINKS_FAST_2026_10_24",
            "docs/cloud/C20d_name_links_fast_2026-10-24.sql": "NAME_LINKS_FAST_2026_10_24",
            "docs/cloud/C20d_checks_2026-10-24.sql": "NAME_LINKS_FAST_2026_10_24",
            "tests/test_name_links_fast_pg_2026_10_24.py": "NAME_LINKS_FAST_2026_10_24",
            "scripts/patch_ask_homonym_2026_10_24.py": "ASK_HOMONYM_2026_10_24",
            "tests/test_ask_homonym_2026_10_24.py": "ASK_HOMONYM_2026_10_24"}

DEBT = """
## 14. 24 Oct, evening: the fill that could not finish, the lines that hopped, the price of a Veda (DOCS93_2026_10_24)

- **Released:** `58cddb1c` (KIN_CLOSE, the C20 split, DOCS92), pushed. The suite on the PC: 188 modules, 1,430 tests,
  189 skipped, every module passing (test_kin_index_2026_10_23 among them: the Windows failure is gone). The dashboard
  restarted at 14:45 when idle, so the Professor is live on the PC's Ask.
- **On the site:** P4 of the preflight ended "Server error"; C20a succeeded (V1: the view there, not filled; the reader
  and the refresh there); C20c scheduled the nightly job (jobid 10); V4: the refresh is nobody's but the owner's, the
  reader the signed-in readers' only. V2 and V3 said "materialized view name_links has not been populated": the fill
  had not run. The Daivat-Sanhita: retired on the site at 03:02:17 UTC, 0 of its 13,887 passages live.
- **Why the fill could not finish (found and measured):** C20a's query joined each passage's names to themselves.
  On a copy the size of the site here (48,491 mentions, a 917 MB passages table, a small memory) the planner guessed
  that the names left after the 12-name rule were ONE row and joined them pair by pair (some 1.6 billion
  comparisons): it ran for more than 5 minutes before it was stopped, and the editor gives up long before. The nightly job
  would have run that query every night at 04:40 UTC. **Mended by NAME_LINKS_FAST_2026_10_24:** the query takes each
  passage's names (2 to 12) as one sorted list and makes the pairs from it, with no self-join, and checks the passage
  through the index corpus_passages_live (C5) alone (0 rows read from the table). On the same copy: 0.2 s, the same
  58,913 pairs (none different either way). C20d gives the site the new view (empty, then C20b fills it) and the job a
  5-minute limit of its own; C20a, C20c and the preflight's P4 now carry the same.
- **The kinship full run (you, 24 Oct, to 17:29):** 913 calls in all, $4.67 with the trial (Purana Index $3.44, Vedic
  Index $0.55, Soerensen $0.68). 15,773 relations read, 15,409 kept after the checks, 5,813 tied to our names.
  Purana Index 12,211 read, 12,131 kept, 4,294 tied (named together 654, near 454, both named but never near 3,000, one
  not in our texts 186), Raychaudhuri agrees 30, differs 16; Vedic Index 1,595, 1,397, 343 (111, 33, 184, 15),
  Raychaudhuri agrees 41, reverses 1, differs 11; Soerensen 1,967, 1,881, 1,177 (537, 241, 388, 11), Raychaudhuri agrees
  31, differs 11. **Not finished:** the run stopped at its --max-usd 4.50 with 2,243 of Soerensen's 2,941 candidate
  entries unread (about $1.13 by the plan; the trial cost 1.5 times its plan).
- **The lines of descent were wrong, and are mended (KIN_LINES_2026_10_24):** kin_lineages.md joined the relations by
  our entity ids, and one of our ids stands for every person of a name (among the 7,870 entries with relations, 1,036
  names are borne by more than one entry of the same index). Its longest line ran 40 steps from Narayana through Karna and Janamejaya to Asvatthaman: a hop
  from one person to another of the same name at almost every step. lines() now joins a step only where the person is
  one entry of that index (one entry of the name; or the homonym's number; or the one homonym that names the other
  person), never across indexes, and says how many steps both entries state. Measured on a copy (the 04:00 backup): 29
  lines (Purana Index 20, Vedic Index 2, Soerensen 7) with their variants counted under them. Among them the line
  Raychaudhuri builds on, Indra (I) > Arjuna (III) > Abhimanyu (I) > Pariksit (I) > Janamejaya (I) > Satanika (II) >
  Sahasranika > Asvamedhaja > Asimakrsna > Nemicakra > ... (16 generations, 14 of 15 steps stated by both entries);
  the Videha line to Siradhvaja, Kusadhvaja and Kesidhvaja; the Vedic Index's Kusika > Gathin > Visvamitra; Soerensen's
  Kuntibhoja > Prtha > Partha > Abhimanyu > Pariksit > Janamejaya > Satanika.
- **The Professor and the numbered persons (ASK_HOMONYM_2026_10_24):** its evidence names each statement's entry
  (s.v. Janamejaya (II)); its instruction now says that a numbered name is one of several persons and must be kept
  apart.
- **How many of the indexes' persons our English names (measured, free):** of the 3,696 one-word names left untied in
  the kept relations, 381 (10%) appear with a capital in the English of our 27,483 translated passages, and some of
  those are common words (Brahman, King, Sun). So 90% of the persons the indexes relate are not named in our English
  at all: the gap is our corpus (the Puranas' genealogical chapters are not translated), not the tying.
- **The Shukla Yajurveda's price (your trial of 20):** $0.2021, $0.0101 a passage; the other 1,205 about $12.2 at that
  rate, more than the $6.52 left of the $110.00 cap ($103.48 spent at 18:01). The planning figure of $0.0037 a passage
  (DOCS91) is out of date: the Nirukta's units cost $0.0085 each and these mantras $0.0101 (the context of five verses
  and the thinking are in the price).
- **Still to run:** the Nirukta's judgement (judge_sample.py, about $0.30); Soerensen's last entries; the Yajnavalkya
  vision pages and the 7 failed pages; the benchmark's Manu label.
"""

STATE = """
## 28. 24 Oct, evening: what runs, what is mended, what waits (DOCS93_2026_10_24)

| What | State |
|---|---|
| Release | `58cddb1c` pushed; KIN_LINES, NAME_LINKS_FAST, ASK_HOMONYM and DOCS93 ready |
| The Professor (PC) | live since the restart of 14:45; ASK_HOMONYM to apply, then restart when idle |
| Links, scholars' check, kinships' check | hourly on the PC (step d), running |
| Kinships | 15,773 read, 15,409 kept, 5,813 tied; Soerensen's last 2,243 entries unread (about $1.13) |
| Lines of descent | were wrong (homonym hops); mended by KIN_LINES: 29 lines, each within one index |
| Named together online | C20a and C20c on the site; the fill could not finish: C20d, then C20b, to paste |
| Health mail (site) | live |
| The Nirukta (GRETIL) | translated (647 of 649, $5.51); to judge (about $0.30) |
| The Shukla Yajurveda | 20 of 1,225 translated; the rest about $12.2: past the cap's $6.52 left |
| The Daivat-Sanhita | retired on the site (03:02 UTC), 0 of 13,887 passages live; the 2017 scan local only |
"""

STATE_TOP_ANCHOR = "# The state of the project, all repos and how they join (18 Oct 2026)\n"
STATE_TOP = ("\n> **Read first:** the newest state is the LAST section of this page; DEBT_2026-10-22.md's last section holds "
             "its evidence and the RUNBOOK's last section its commands (DOCS93_2026_10_24). Sections 1 to 3 describe "
             "18 Oct.\n")

RUNBOOK = """
## 24 Oct, evening: the fast fill, the lines mended, the Professor's guard (DOCS93_2026_10_24)

From the repository root (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`), not in the minutes :00 to
:03 when the hourly task runs:

1. `python scripts\\patch_kin_lines_2026_10_24.py --check`, then without --check; the same for
   `patch_name_links_fast_2026_10_24.py`, `patch_ask_homonym_2026_10_24.py` and `patch_docs93_2026_10_24.py`. Then
   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`, and the dashboard restarted when it is idle
   (`powershell -ExecutionPolicy Bypass -File scripts\\restart_dashboard.ps1 -Status`, then without -Status).
2. `python scripts\\kin_index.py --check` (free): the exports rewritten, kin_lineages.md by the index's own entries.
3. On the site, one paste each: docs\\cloud\\C20d_name_links_fast_2026-10-24.sql; F1 of C20d_checks_2026-10-24.sql
   (fast_query true, filled false); C20b_name_links_fill_2026-10-24.sql (seconds); F1 (filled true); F2 (the job's
   command begins SET statement_timeout); V2, V3 and V5 of C20_checks_2026-10-24.sql. Then Publish Srangam.
4. Paid, within the cap: `python scripts\\kin_index.py --yes --per-source 0 --max-usd 2.00` (Soerensen's last
   entries); `python scripts\\judge_sample.py --doc nirukta__w_gretil --sample-pct 10` (the dry run), then with
   `--yes --max-usd 0.30`.
5. The Shukla Yajurveda (about $12.2) waits for your decision on the cap: `python scripts\\set_budget.py` shows it.
"""

PLATFORM = """
## 96. The fast name links; the lines by entries; the Professor's guard (DOCS93_2026_10_24)

- **corpus.name_links** (C20a as it stands, C20d for a site that had the first query): named (live mentions of live
  texts) -> few (each passage's names, 2 to 12, as one sorted array) -> live (the passage in corpus_passages_live) ->
  pairs (from the array, by ordinality: name_a < name_b) -> grouped as before. No self-join.
- **cron.job srangam-corpus-name-links**: `SET statement_timeout = '5min'; SELECT corpus._refresh_name_links();` at
  40 4 * * * (UTC).
- **scripts/kin_index.py** (KIN_LINES_2026_10_24): split_mark(name) -> (folded name, homonym number); heads_index(con)
  from shelf_entries; lines(rows, heads) -> {source: [(heads elder first, steps in both entries, variants)]};
  lines_text() writes exports/kin_lineages.md. lineages() stays, unused.
- **_ASK_SYSTEM_PROF** (ASK_HOMONYM_2026_10_24): one sentence more, on numbered persons.
"""

EP = """
## Addendum 2026-10-24 (83): the path from here (DOCS93_2026_10_24)

| Phase | Key | Item | State | Cost |
|---|---|---|---|---|
| 1 now | names-ui | "Named together" on the site: C20d, C20b, Publish | Ready | free |
| 1 now | relations-lines | Lines of descent by the index's entries (KIN_LINES) | Ready | free |
| 1 now | ask-homonym | The Professor keeps numbered persons apart | Ready | free |
| 1 now | relations-index | Soerensen's last 2,243 entries | Yours | about $1.13 |
| 1 now | nirukta-judge | The Nirukta's translation judged, then adopted | Yours | about $0.30 |
| 2 cap | yajur-shukla | The Shukla Yajurveda translated, then --release | Waits for the cap | about $12.2 |
| 3 | vamsa-corpus | The Puranas' genealogical chapters (Visnu IV, Matsya, Vayu) from GRETIL's witnesses, translated: 90% of the indexes' persons are not named in our English | Next: count the verses, price them | to price |
| 3 | relations-names | The indexes' persons as our names (variants), so the lines can be checked against the verses | Next | free |
| 4 | h2 | The indexes' relations and lines on the site, with credit and the licence's notice | Decided; after phase 3 | free |
| 4 | ask-site | The Professor on the site (A2), behind the readers' gate | Next | per question |
| 4 | claims-mirror | Raychaudhuri's claims on the site (B2) | Next | free |
| 5 | hygiene | Yajnavalkya vision and 7 failed pages; the benchmark's Manu label | Next | about $0.40 |
"""

ASKS = """
## 10. 24 Oct, evening: "are we done now ... cronning ... for probot in action" (DOCS93_2026_10_24)

- **Running on the PC:** the links, the scholars' check and the kinships' check every hour; the health in every
  heartbeat; the backup and the mirror; the Professor on the Ask page.
- **Running on the site:** the health mail; the nightly name-links job (but the view is empty until C20d and C20b).
- **Mended in this release:** the fill that could not finish (NAME_LINKS_FAST, C20d); the lines of descent that hopped
  between persons of one name (KIN_LINES); the Professor's guard for numbered persons (ASK_HOMONYM).
- **Not yet:** Soerensen's last entries; the Nirukta's judgement; the Shukla Yajurveda (past the cap); the Professor
  and the indexes' relations on the site.
- **The documentation:** STATE's last section is the state; DEBT's last section its evidence; the RUNBOOK's last
  section its commands; ENTERPRISE_PATH's last addendum the path. Each section names its marker and its release.
"""

RELATIONS = """
## 8. 24 Oct, evening: the full run, the lines, the coverage (DOCS93_2026_10_24)

- **R2 and R3, the full run:** 15,773 relations, 15,409 kept, 5,813 tied (DEBT section 14); Soerensen 2,243 entries to go.
- **The lines:** by the index's own entries only (KIN_LINES); 29 lines, the longest 20 generations, most steps stated
  by both entries; the post-war Paurava line (Pariksit, Janamejaya, Satanika, Asvamedhaja, Asimakrsna, Nemicakra) among
  them. These are the indexes' lines, not yet checked against our verses.
- **The coverage:** 90% of the untied persons are not named in our English; the next step for the relations is the
  corpus (the genealogical chapters), then our names for the indexes' persons.
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
        if p.name.startswith("STATE_"):
            if src.count(STATE_TOP_ANCHOR) != 1:
                print("REFUSE: %s: its title line is not there once. Nothing written." % p); return 1
            src = src.replace(STATE_TOP_ANCHOR, STATE_TOP_ANCHOR + STATE_TOP, 1)
        src = (src if src.endswith("\n") else src + "\n") + text.lstrip("\n")
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs93_" + stamp))
        t = p.with_name(p.name + ".tmp_docs93"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
