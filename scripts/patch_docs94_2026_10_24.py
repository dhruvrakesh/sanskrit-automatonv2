#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs94_2026_10_24.py  DOCS94_2026_10_24

Records the night of 24 Oct: "Named together" filled on the site (C20d, C20b) and checked; the PC's release 9a840934;
the Soerensen run as it went; the Relations page for the PC's dashboard (RELATIONS_UI_2026_10_24) and what the site
still lacks; the maintenance task's silent stop mended (MAINT_GUARD_2026_10_24); kin_index's ALSO line mended
(KIN_ALSO_2026_10_24); and a correction: the maintenance task fires every 3 hours, not every hour.

Appends docs/DEBT_2026-10-22.md section 15, STATE section 29, a RUNBOOK section, PLATFORM section 97, ENTERPRISE_PATH
addendum 84, docs/ASKS_2026-10-22.md section 11 and docs/RELATIONS_AND_ASK_2026-10-22.md section 9, each needing
DOCS93_2026_10_24; and adds the Relations page to README.md's list of the web UI (after its /ask entry). Refuses
unless what it records comes with this release. Marker-idempotent per file, all-or-nothing, backup first
(.bak_docs94_ and the date), line endings kept.

  python scripts\\patch_docs94_2026_10_24.py --check
  python scripts\\patch_docs94_2026_10_24.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS94_2026_10_24"
NEEDS = "DOCS93_2026_10_24"
REQUIRES = {"scripts/relations_view.py": "RELATIONS_UI_2026_10_24",
            "scripts/relations.html": "RELATIONS_UI_2026_10_24",
            "scripts/patch_relations_ui_2026_10_24.py": "RELATIONS_UI_2026_10_24",
            "tests/test_relations_ui_2026_10_24.py": "RELATIONS_UI_2026_10_24",
            "scripts/patch_maint_guard_2026_10_24.py": "MAINT_GUARD_2026_10_24",
            "tests/test_maint_guard_2026_10_24.py": "MAINT_GUARD_2026_10_24",
            "scripts/patch_kin_also_2026_10_24.py": "KIN_ALSO_2026_10_24",
            "tests/test_kin_also_2026_10_24.py": "KIN_ALSO_2026_10_24"}

DEBT = """
## 15. 24 Oct, night: named together live on the site, a Relations page, the silent tick (DOCS94_2026_10_24)

- **On the site (your pastes, 20:03 to 20:05):** C20d succeeded; F1 said fast_query true, filled false; C20b filled the
  view in 3.1 s (`{"ms":3104,"pairs":45183,"was_filled":false}`), the same 45,183 pairs the site counted on 23 Oct; F1
  then filled true; F2: job 10, `40 4 * * *`, `SET statement_timeout = '5min'; SELECT corpus._refresh_name_links();`,
  active. V2: 45,183 pairs, 4,822 in two passages or more, 1,516 in two texts or more, 86 in five texts or more. V3:
  Janaka with Yajnavalkya 33 passages, Videha 29 (first in the Satapatha, pages 97 and 95). The name pages show
  "Named together with" once Srangam is published.
- **On the PC:** KIN_LINES, NAME_LINKS_FAST, ASK_HOMONYM and DOCS93 applied (every hash as released), `9a840934`
  pushed, the dashboard restarted at 19:57 (the Professor's guard live). You raised the cap to $115.00 ($103.48 spent
  before Soerensen's run).
- **Soerensen's last entries (your run from 20:03, --max-usd 2.00):** at 20:18, 1,016 of 2,941 of its candidate
  entries read, $1.04 in all for that index; this run $0.36 for 318 entries, $0.00114 an entry, about twice the plan's
  $0.0005 (its entries are long: one or two go to a call). At that rate its $2.00 stops it with about 500 entries left.
- **A correction:** the maintenance task fires every 3 hours (00:00, 03:00 ... 21:00), not every hour as DOCS91 to
  DOCS93 said; step d (the links, the scholars' check, the kinships' check) runs at each tick that maintains.
- **A tick that stopped in silence (mended, MAINT_GUARD_2026_10_24):** at 15:00 the runner wrote "TICK" and
  "dashboard idle - ok to maintain" and nothing more. Under `$ErrorActionPreference = "Stop"` an error in the API check
  (Test-NetConnection) or any line outside a step's try ends the script without a word. Now the API check's error is a
  logged SKIP and any error no step catches is a logged FAIL with exit 1, which health_watch.py reads.
- **kin_index's ALSO line (mended, KIN_ALSO_2026_10_24):** after the full run's plan it said "entries of the trial are
  not read yet: python scripts\\kin_index.py --yes", a command that reads nothing then; it now gives --per-source and a
  --max-usd.
- **Asked: "do we have an authoritative local and Srangam UI for these interrelationships, visually explaining them,
  and selections?"** Not until now. Locally the relations were in exports (CSV, Markdown) and in the Professor's
  evidence; on the site only "Named together with". **Built (RELATIONS_UI_2026_10_24):** the PC's dashboard has a
  Relations page (http://127.0.0.1:5057/relations): a name with suggestions; a drawing (the inner ring whom our texts
  name it with, the line's width by passages; the outer ring whom the indexes relate to it, coloured by the kind of
  relation, dashed where our texts never name the two together); "Named together in our texts" with the passages where
  they first meet; "In the indexes", each person of the name as one index enters him or her, homonyms apart, each
  relation with its words, reference, verdict against our verses and Raychaudhuri's view; the line of descent through
  each, by the index's own entries; Raychaudhuri's claims. Selections: the index, the kind of relation, "named together
  only", the inner ring. Read-only (scripts/relations_view.py). Measured on a copy of the 04:00 backup: Janamejaya, 12
  persons in the three indexes (Soerensen's Janamejaya[1] with 15 relations and five generations above him: Pariksit,
  Abhimanyu, Partha, Prtha, Kuntibhoja); the first view 1.3 s (the indexes' model is built once), then 0.1 to 0.3 s.
- **A lesson kept in the code:** our names' variants include epithets (Janamejaya's: Bharata, naradhipa, pariksita,
  bharatarsabha, as the Mahabharata's frame addresses him), so a variant finds a name but never ties an index's person;
  the first build showed Bharata (I) to (III) under Janamejaya, and was mended before release.
- **The site still lacks:** the indexes' relations, the lines of descent and a drawing (phase U3 below, needing H2's
  mirror of the kept relations).
"""

STATE = """
## 29. 24 Oct, night (DOCS94_2026_10_24)

| What | State |
|---|---|
| Release | `9a840934` pushed; RELATIONS_UI, MAINT_GUARD, KIN_ALSO and DOCS94 ready |
| Named together online | **filled and checked** (45,183 pairs, 3.1 s); refreshed nightly 04:40 UTC with a 5-minute limit; Publish Srangam |
| The Relations page (PC) | built: /relations on the dashboard, read-only; restart the dashboard to load it |
| The Professor (PC) | live with the guard for numbered persons (restart of 19:57) |
| The maintenance task | every 3 hours; step d at each tick that maintains; a silent stop mended (MAINT_GUARD) |
| Kinships | Soerensen's run under way (1,016 of 2,941 read at 20:18; its $2.00 stops it short of the end) |
| The cap | $115.00 ($103.48 spent before the Soerensen run) |
| The site's relations UI | not yet: the indexes' relations and lines (U3, after H2's mirror) |
"""

RUNBOOK = """
## 24 Oct, night: the Relations page, the guard, the ALSO line (DOCS94_2026_10_24)

From the repository root (`Set-Location "D:\\Sanksrit Automatons\\sanskrit-automatonv2"`), not in the minutes :00 to
:03 of a tick (00:00, 03:00 ... 21:00), and after the Soerensen run has ended (kin_index.py is one of the files):

1. `python scripts\\patch_relations_ui_2026_10_24.py --check`, then without --check; the same for
   `patch_maint_guard_2026_10_24.py`, `patch_kin_also_2026_10_24.py` and `patch_docs94_2026_10_24.py`. Then
   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`, and the dashboard restarted when it is idle.
2. Open http://127.0.0.1:5057/relations (or the Relations button on the dashboard's top bar, the Library, the Ask
   page; a name under a Professor's answer leads there too).
3. On the site: Publish Srangam in Lovable; after 04:40 UTC, V6 of docs\\cloud\\C20_checks_2026-10-24.sql (the
   nightly job's runs).
4. What Soerensen's run leaves: `python scripts\\kin_index.py --per-source 0` (the plan) names the command.
"""

PLATFORM = """
## 97. The Relations page; the runner's guards (DOCS94_2026_10_24)

- **/relations** (scripts/relations.html) and **/api/relations** (scripts/dashboard.py, RELATIONS_UI_2026_10_24):
  `?find=<text>` -> {names: [{id, name, kind, mentions, exact, via: name | variant | begins | most named}]};
  `?id=<entity id>&k=24` -> {entity: {id, name, kind, mentions, texts}, together: [...], near: [...] (each {id, name,
  kind, passages, texts, places: [{doc, ref}]}), persons: [{source, index, title, entry, head, own: [relation],
  named_in: [relation + stated_in], up: [[{entry, head, of, both}]], down: [...]}], claims: [{page, relation, claim,
  source}], read, titles}; a relation is {relation, label, group, as, subject, object, other, other_head, other_entity,
  words, refs, entry_head, verdict, passages, texts, places, raychaudhuri, raychaudhuri_note}.
- **scripts/relations_view.py:** find(db, q), view(db, entity_id, shelf_dir); the names cached until context.db's size
  changes, the indexes' model until kin.db changes; persons are the entries whose head is the name or that shelf_links
  ties exactly (how = 'exact'), never through a variant.
- **scripts/maintenance_runner.ps1** (MAINT_GUARD_2026_10_24): a trap (FAIL line, exit 1) and the API check in a try.
  The task's trigger: every 3 hours.
"""

EP = """
## Addendum 2026-10-24 (84): the relations, seen (DOCS94_2026_10_24)

| Key | Item | State |
|---|---|---|
| names-ui | "Named together with" on the site | Filled (45,183 pairs) and refreshed nightly; Publish Srangam |
| relations-ui-local | The Relations page on the PC (drawing, persons apart, lines, claims, selections) | Built (RELATIONS_UI) |
| relations-ui-site (U3) | The same on the site's name page | Next, after H2: C21 (corpus.index_relations, a reader function behind the gate, the credit and the licence's notice), corpus_sync sending the kept relations, Srangam's name page reading them; free (no model) |
| maint-guard | The maintenance task never stops in silence | Built (MAINT_GUARD) |
| kin-also | kin_index's ALSO line names the right command | Built (KIN_ALSO) |
| relations-index | Soerensen's last entries | Under way; what is left after the $2.00, about $0.60 |
"""

ASKS = """
## 11. 24 Oct, night: "do we have an authoritative local and Srangam UI for these interrelationships ... and selections?" (DOCS94_2026_10_24)

- **Local:** now yes, once RELATIONS_UI is applied: the Relations page (DEBT section 15). It is authoritative in the
  sense that each statement shows its source, its words, its reference and its check; it is not a verdict of its own.
- **Srangam:** "Named together with" on each name page (filled tonight); the indexes' relations, the lines and a
  drawing are phase U3 (ENTERPRISE_PATH addendum 84).
- **"Update our 18 Oct document also":** the brain page (the Claude Doc "Our Sanskritic Brain") now opens with where we
  stand on 24 Oct; STATE_2026-10-18.md's last section is the state (section 29).
"""

RELATIONS = """
## 9. 24 Oct, night: U2 live, the local view, U3 next (DOCS94_2026_10_24)

- **U2** (names-ui): live on the site's database (45,183 pairs, 3.1 s to fill); seen once Srangam is published.
- **The local view** (RELATIONS_UI): the drawing and the cards read the same tables the Professor reads, so what the
  page shows and what the Professor may cite agree.
- **U3** (relations-ui-site): needs H2's mirror of the kept relations (decided: with credit and the licence's notice
  while the site stays non-commercial).
"""

README_ANCHOR = "  the embedding index isn't built.\n"
README_ADD = ("- **/relations** - **Relations** (RELATIONS_UI_2026_10_24, DOCS94_2026_10_24): one of our names; whom our\n"
              "  texts name it with; what the Purana Index, the Vedic Index and Soerensen state of each person of that\n"
              "  name (homonyms apart); the line of descent through each; Raychaudhuri's claims. A drawing and\n"
              "  selections (index, kind of relation, named together only). Read-only. The Ask page's Professor mode\n"
              "  reads the same relations (ASK_PROF_2026_10_23).\n")

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
            print("REFUSE: README.md: its /ask entry's last line is not there once. Nothing written."); return 1
        src = src.replace(README_ANCHOR, README_ANCHOR + README_ADD, 1)
        plan[p] = src.replace("\n", nl).encode("utf-8")
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for p, data in plan.items():
        shutil.copy2(p, p.with_name(p.name + ".bak_docs94_" + stamp))
        t = p.with_name(p.name + ".tmp_docs94"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
