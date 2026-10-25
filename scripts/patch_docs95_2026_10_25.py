#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs95_2026_10_25.py  DOCS95_2026_10_25

Records 25 Oct: the release 101644c6 (RELATIONS_UI, MAINT_GUARD, KIN_ALSO, DOCS94) applied and pushed; the kinships
as they stand; the new phase asked for (authoritative genealogies; the texts repaired by themselves); what was built
for it: the Purana Index's citations read in GRETIL's Sanskrit (VAMSA_CHECK_2026_10_25), the Vamsa page
(VAMSA_UI_2026_10_25), the scans' repair kept going within an allowance (AUTO_REPAIR_2026_10_25); and the project's
evolution traced (docs/EVOLUTION_2026-10-25.md).

Appends docs/DEBT_2026-10-22.md section 16, STATE section 30, a RUNBOOK section, PLATFORM section 98, ENTERPRISE_PATH
addendum 85, docs/ASKS_2026-10-22.md section 12 and docs/RELATIONS_AND_ASK_2026-10-22.md section 10, each needing
DOCS94_2026_10_24; and adds the Vamsa page to README.md's list of the web UI (after its /relations entry). Refuses
unless what it records comes with this release. Marker-idempotent per file, all-or-nothing, backup first
(.bak_docs95_ and the date), line endings kept.

  python scripts\\patch_docs95_2026_10_25.py --check
  python scripts\\patch_docs95_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS95_2026_10_25"
NEEDS = "DOCS94_2026_10_24"
REQUIRES = {"scripts/vamsa_check.py": "VAMSA_CHECK_2026_10_25",
            "scripts/vamsa_view.py": "VAMSA_UI_2026_10_25",
            "scripts/vamsa.html": "VAMSA_UI_2026_10_25",
            "scripts/patch_vamsa_ui_2026_10_25.py": "VAMSA_UI_2026_10_25",
            "tests/test_vamsa_2026_10_25.py": "VAMSA_UI_2026_10_25",
            "scripts/repair_auto.py": "AUTO_REPAIR_2026_10_25",
            "scripts/patch_auto_repair_2026_10_25.py": "AUTO_REPAIR_2026_10_25",
            "tests/test_auto_repair_2026_10_25.py": "AUTO_REPAIR_2026_10_25",
            "docs/VAMSA_2026-10-25.md": "VAMSA_CHECK_2026_10_25",
            "docs/CONSOLIDATION_2026-10-25.md": "AUTO_REPAIR_2026_10_25",
            "docs/EVOLUTION_2026-10-25.md": "EVOLUTION_2026_10_25"}

DEBT = """
## 16. 25 Oct: the release applied; genealogies from the Sanskrit; the repair kept going (DOCS95_2026_10_25)

- **Applied and pushed:** 101644c6 ("A Relations page on the dashboard; the maintenance task never stops in silence;
  kin_index's ALSO line; the night of 24 Oct recorded"); every file at the hash the release named (dashboard.py
  1903f1dd, maintenance_runner.ps1 340bff5b, kin_index.py a6a001b6, README 295afbbe).
- **The kinships at 09:00:** 22,431 relations read, 21,847 kept, 9,971 tied. Soerensen 8,625 read (8,319 kept, 5,334
  tied; Raychaudhuri agrees 118, differs 41); the last run stopped at its --max-usd 0.50 after 93 calls and 411
  entries ($0.5013). The plan names the full run of what is left in all three indexes: about $4
  (python scripts\\kin_index.py --yes --per-source 0 --max-usd 4.50). The cap: $106.43 spent of $115.00, $8.57 left.
- **Asked:** authoritative genealogies of the kings of the Mahabharata, the Puranas and the Ramayana from the persons
  we hold, the Sanskrit texts in their critical editions wherever they exist, our own correlations to comment on the
  inferences; the repair of the texts automated, the user asked only to raise the limit.
- **Built (G1, free):** VAMSA_CHECK (scripts/vamsa_check.py): the Purana Index's citations read in GRETIL's TEI texts
  (the Visnu in two editions, the Bhagavata, the Brahmanda, the Matsya 1-176) and every relation's names looked for in
  the critical editions of the Mahabharata (counts and references only: BORI's e-text), the Harivamsa and the
  Ramayana: of 7,098 citations of a text we hold, both names stand in the cited verse for 4,910. VAMSA_UI
  (scripts/vamsa_view.py, scripts/vamsa.html, /vamsa): the lines of descent, each step with its verse; two more
  joins, each shown (the honorific aside, a shared verse). docs/VAMSA_2026-10-25.md.
- **Built (consolidation):** AUTO_REPAIR (scripts/repair_auto.py, step e of the maintenance task): the first round
  of each day judges every text; each other round does one step of one text, the step repair_text.py names, vision
  within $0.25 a day and above a $1.00 reserve of the cap; blocked by the cap, it warns through health_watch.py and the
  site mails. docs/CONSOLIDATION_2026-10-25.md.
- **Tuned on the real data:** a first version of the name match compared consonants only; it took Daksa for Rksa and
  Kusadhvaja for Kesidhvaja. The vowels now count (by quality): 4,910 relations with both names, each a match the
  verse shows.
- **Not yet:** the Vayu (3,387 citations) is not in GRETIL; Soerensen's numbering is the Calcutta edition's; 7,607 sides
  of parent relations are names the index's entries cannot tell apart; the site's genealogy (G3, after H2); a
  model's commentary on a line (G2); the genealogical chapters translated (G4, needs the cap).
"""

STATE = """
## 30. 25 Oct (DOCS95_2026_10_25)

| What | State |
|---|---|
| Release | `101644c6` pushed; VAMSA_CHECK, VAMSA_UI, AUTO_REPAIR and DOCS95 ready |
| Kinships | 22,431 read, 21,847 kept, 9,971 tied; the rest of the three indexes about $4 by the plan |
| The verses | 4,910 of the Purana Index's relations with both names in the cited Sanskrit verse (python scripts\\vamsa_check.py --yes, free) |
| The Vamsa page (PC) | built: /vamsa, read-only; restart the dashboard to load it |
| The repair rounds | built: step e of the maintenance task; $0.25 a day unless set; the first round of each day judges |
| The cap | $106.43 spent of $115.00 ($8.57 left; the rounds keep $1.00) |
| The site | named together live; Publish Srangam if not yet; the genealogy is G3 (after H2) |
"""

RUNBOOK = """
## 25 Oct: the verses read, the Vamsa page, the repair rounds (DOCS95_2026_10_25)

From the repository root (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`), not in the minutes :00 to
:03 of a tick (00:00, 03:00 ... 21:00):

1. `python scripts\\patch_vamsa_ui_2026_10_25.py --check`, then without --check; the same for
   `patch_auto_repair_2026_10_25.py` and `patch_docs95_2026_10_25.py`. Then
   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.
2. `python scripts\\vamsa_check.py` (the plan: every check counted, nothing written), then
   `python scripts\\vamsa_check.py --yes` (free; writes data\\shelf\\vamsa.db and two exports, about half a minute).
3. Restart the dashboard when it is idle; open http://127.0.0.1:5057/vamsa (or the Vamsa button on the dashboard's
   top bar, the Library's header, the Relations page beside each line of descent).
4. The repair rounds: `python scripts\\repair_auto.py` (the queue), `python scripts\\repair_auto.py --round --dry-run`
   (what the next round would run); the allowance: `python scripts\\repair_auto.py --allow 0.25` (0 stops the paid
   steps). The maintenance task runs a round at each tick; `python scripts\\repair_auto.py --log` shows them.
"""

PLATFORM = """
## 98. The verses read; the Vamsa page; the repair rounds (DOCS95_2026_10_25)

- **scripts/vamsa_check.py** (VAMSA_CHECK_2026_10_25, SCHEME 8): reads sources\\gretil\\1_sanskr.zip and
  data\\shelf\\kin.db (mode=ro); --yes writes data\\shelf\\vamsa.db: vamsa_meta (kin, zip, mark, scheme, at),
  vamsa_texts (code, title, edition, rights, member, sha256, verses, show), vamsa_rel (kin_id, source, entry_id, cited:
  both | one | neither | no verse | not held | no citation | not looked for, cites JSON, both_texts, best_text,
  best_ref, subject_form, object_form, mbh, mbh_first, hv, hv_first, ram, ram_first), vamsa_verses (text, ref, words:
  the TEI verses only, never the Mahabharata's); exports\\vamsa_checks.csv, exports\\vamsa_summary.json.
  --scheduled writes only when kin.db's (count, max id) or the zip's (size, mtime) changed.
- **/vamsa** (scripts/vamsa.html) and **/api/vamsa** (scripts/dashboard.py, VAMSA_UI_2026_10_25): `?lines=1[&src=]` ->
  {lines: {src: [{source, index, entries, heads, length, both_steps}]}}; `?find=<text>[&src=]` -> {persons: [{source,
  index, entry, head, sex, named_only, parents, children, up, down, entity, spouses, exact}]};
  `?src=&entry=[&path=|&via=]` -> {person, line: [person + generation, siblings, siblings_n, other_parents], steps:
  [{parent, child, items, both_entries, cited, ours, scholar, epic, joined: rule | verse | named}], me, down,
  verses: {"text|ref": words}, texts, checked}.
- **scripts/vamsa_view.py:** builds on relations_view._model; a name the rule leaves open is joined the honorific aside
  (rule), else by a shared verse (verse), else stays a leaf of its row (named, a negative entry id).
- **scripts/repair_auto.py** (AUTO_REPAIR_2026_10_25): data\\auto_repair.json (usd_per_day 0.25, round_usd 0.10,
  reserve_usd 1.00, swap, max_tries 5, step_minutes 25), data\\auto_repair_log.jsonl, data\\auto_repair_state.json
  (status: working | waiting | blocked | off | idle; asks), data\\auto_repair.lock. Runs repair_text.py (SA_REPAIR_SCRIPTS
  for the tests).
- **scripts/maintenance_runner.ps1** (AUTO_REPAIR_2026_10_25): step d runs vamsa_check.py --scheduled after
  kin_index.py --check; step e runs repair_auto.py --round before the DONE line. **scripts/health_watch.py:**
  check_repair (blocked or 30 hours without a round: warn).
- **scripts/ask.html:** `/ask?q=...&mode=professor` fills the question and the mode; it never asks by itself.
- **.gitignore** (AUTO_REPAIR_2026_10_25): data/auto_repair.json, _log.jsonl, _state.json and .lock stay on the PC.
"""

EP = """
## Addendum 2026-10-25 (85): genealogies and consolidation (DOCS95_2026_10_25)

| Phase | Key | Item | State | Cost |
|---|---|---|---|---|
| G1 | vamsa-check | The Purana Index's citations read in GRETIL's Sanskrit; the epics' verses that name both | Built (VAMSA_CHECK): 4,910 with both names | free |
| G1 | vamsa-ui | The Vamsa page on the PC: lines, steps, verses, joins shown | Built (VAMSA_UI) | free |
| C1 | auto-repair | The scans' repair kept going: one step a round, the next step repair_text.py names | Built (AUTO_REPAIR) | $0.25 a day unless set |
| G2 | vamsa-comment | The Professor's commentary on a whole line, citing the index, the verses, the epics, our passages, Raychaudhuri; marked as a reading; cached | Next | per line, priced first |
| G3 | h2, vamsa-site | C21 (corpus.index_relations with the checks, a reader function behind the gate, the credit and the notice); corpus_sync; Srangam's genealogy | Next | free |
| G4 | vamsa-corpus | The genealogical chapters as texts of their own and translated: the first slice the Visnu's book IV (1,341) and the Bhagavata's book IX and XII.1 (1,005) | Next: the importer (as import_mbh_gretil.py), then the plan's price | about $24 at $0.01 a verse; needs the cap |
| - | relations-index | What is left of the three indexes | Yours | about $4 by the plan |
| - | yajur-shukla | The Shukla Yajurveda translated, then --release | Yours | about $12.2; needs the cap |
"""

ASKS = """
## 12. 25 Oct: "authoritative genealogies ... the Sanskrit texts ... repairing automated, approval only to increase the usage limit" (DOCS95_2026_10_25)

- **Genealogies:** the Vamsa page (DEBT section 16, docs/VAMSA_2026-10-25.md). Authoritative in the sense the
  Relations page is: each step shows the index's words and reference, the Sanskrit verse in its edition with both
  names marked, the epics' verses, our passages and Raychaudhuri; the page draws no conclusion of its own.
- **Critical editions:** the Visnu (Pathak), the Harivamsa and the Ramayana in GRETIL's TEI; the Mahabharata's (BORI)
  by reference only. The Vayu is not in GRETIL.
- **Our correlations and inferences:** our passages and the epics' counts on each step now; a model's commentary on a
  line is G2, priced before it runs.
- **Repair automated:** the rounds (docs/CONSOLIDATION_2026-10-25.md). They ask only when the cap stands in the way,
  or when a step would replace paid translations.
- **"Trace the evolution of the project":** docs/EVOLUTION_2026-10-25.md, and the brain page.
"""

RELATIONS = """
## 10. 25 Oct: the lines read against the Sanskrit (DOCS95_2026_10_25)

- **The Purana Index's citations, read:** 4,910 of its 12,211 relations have both names in the cited verse (of the
  7,098 citations of a text GRETIL holds).
- **The lines, longer:** a shared verse joins a name the rule left open (891 sides), the honorific aside (586 sides);
  the Iksvaku line through Dasaratha (II) runs 38 generations, 29 of its 37 steps with both names in the verse.
- **The page:** /vamsa; the Relations page links each line of descent to it.
"""

README_ANCHOR = "  reads the same relations (ASK_PROF_2026_10_23).\n"
README_ADD = ("- **/vamsa** - **Vamsa** (VAMSA_UI_2026_10_25, DOCS95_2026_10_25): the lines of descent of the three\n"
              "  indexes, generation by generation; each step with the index's words, the Sanskrit verse where both\n"
              "  names stand (GRETIL's editions, read by scripts/vamsa_check.py), the epics' verses that name both, our\n"
              "  passages and Raychaudhuri's view. Read-only; no model is called.\n")

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
    p = Path("README.md")
    if not p.exists():
        print("FAIL: README.md not found. Run from the repo root."); return 2
    raw = p.read_bytes()
    if MARK.encode() in raw:
        print("skip README.md (already carries %s)" % MARK)
    else:
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if src.count(README_ANCHOR) != 1:
            print("REFUSE: README.md: its /relations entry's last line is not there once. Nothing written."); return 1
        src = src.replace(README_ANCHOR, README_ANCHOR + README_ADD, 1)
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs95_" + stamp))
        t = p.with_name(p.name + ".tmp_docs95"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
