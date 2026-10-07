#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs14_2026_10_07.py  DOCS14_2026_10_07

Appends to docs/PLATFORM_2026-10-04.md (section 17), RUNBOOK.md and
docs/ENTERPRISE_PATH_2026-10-04.md: the second pass on the story check (VERIFY_NAMES),
corpus_status code hints (DOC_HINT), the correct Ganita code (a correction to sections
15 and 16), what S1 did on Srangam and the read-only S2, and translation throughput.
Marker-idempotent per file, backup first.

  python scripts/patch_docs14_2026_10_07.py --check
  python scripts/patch_docs14_2026_10_07.py
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "DOCS14_2026_10_07"

PLATFORM = """

## 17. The story check, second pass; the right Ganita code; Srangam totals live (VERIFY_NAMES, DOC_HINT, SRANGAM S1/S2 - 2026-10-07; DOCS14_2026_10_07)

**Re-check results (14:30, release bb915898).** `verify-all` on markandeya_purana checked 13 stories: 8 passed (#1 and #4 newly), 5 failed. None is approved yet, so books, versions for younger readers and graphic novels stay greyed until stories are read and approved. Each of the five failures was read against its passages in the 14:30 backup (read-only):
- **#6 "Mount"** came from "went to Mount Meru"; 29.9 says "the peak of meru". "Mount" is an English title word, not a name. This was a false failure.
- **#11, "1 sentence without a citation".** The check split 'he cried, "Alas! This is Saivya, and this is that boy," and fell into a swoon. [60.10]' inside the quotation. This was a false failure.
- **#3 "Vapu?".** PowerShell cannot draw the visarga, so this was "Vapuh". 10.3 gives the name in another case ("vapum apsarasam"), so this was a false failure.
  - #3 has a real error the check cannot see. It makes Vapu the rakshasa's widow, but 10.2-10.3 say the widow (Menaka's daughter) bore Kandhara a daughter, Taci, who was the apsaras Vapu under a sage's curse. Edit it before approving.
- **#5 "Draupadi"** is a real failure. 25.8 says "that one daughter of Drupada"; the passages never give the name. Edit the name, or approve anyway with a note.
- **#10** is a real failure: 8 of 9 sentences carry no citation (there is one list of tags at the end). Rewrite it.

**VERIFY_NAMES_2026_10_07** (`scripts/stories.py`):
- English title words (Mount, Mountain, River, Lake, Forest, Ocean, Sea, Queen, Prince, Princess, Goddess, Lady, Mother, Father) are not taken for names.
- For the citation check only, a fragment that ends inside a quotation is joined to the next, up to 4 fragments.
- A name ending in a visarga is also found by its stem at the start of a word.
- The same 13 stories, from the same backup: 11 pass and 2 fail (#5, #10), with no story newly failing.

**DOC_HINT_2026_10_07** (`scripts/corpus_status.py`). `--doc` is checked against the docs table.
- An exact code is used. Another case, or the only code that starts with what was given, is used with a note.
- Anything else gets "no text has the code ...; did you mean ...".
- If nothing matches, it stops; it no longer falls through to every text.

**Correction to sections 15 and 16.** The Ganita text's code is `Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`. "Ganita_Yukti_Bhasa" was a short title. Used as a code it printed "0 docs" (14:30), and the docs13 addendum carried it.
- In the 14:30 backup the text has 2,706 passages: 977 without English and none with Hindi.
- The run of 6-7 Oct was the English pass, 709 of 1,460 selected.

**Translation throughput** (jobs.jsonl, the last lines of that run). One passage per call with gemini-2.5-flash took 22.9-39.7 s, which is 91-157 passages an hour. At that rate:
- the English remainder of Ganita is 6-11 hours;
- a Hindi pass over 2,706 passages is 17-30 hours.

Maintenance skips the whole time, because the dashboard is busy (1.12). Throughput is item T2. Nothing is changed until a measured comparison of quality and speed.

**Srangam, S1 applied (14:39-14:40).**
- **The recorded migration with no file.** 20260201064547 ("Phase 1.3: Batch increment function for cultural terms", by apikey@lovable.dev) created `increment_term_usage_counts(text[])`, SECURITY DEFINER.
  - Repo migration 20260517042601 (line 83, RELIABILITY_AUDIT N.7) revokes EXECUTE on it from PUBLIC, anon and authenticated.
  - No edge function calls it.
  - S2 G1-G2 confirm the live state. No file is added to supabase/migrations, and no history row is written.
- **The stats view.** PostgreSQL is 17.6 (170006). H3 created `srangam_cross_reference_stats`.
  - **As the editor's role:** 1,561 references, 2 types, average strength 6.71 (range 4-10), between 48 and 48 articles.
  - **As an anonymous visitor (block_BE_reader -Verify):** 1,392. The view is security_invoker, and the policy "Public read cross references between published articles" (20260607043411) shows a reference only when both articles are published. The other 169 touch an unpublished article; S2 G4 breaks them down by status.
- /research-network now reads exact totals instead of a 1,000-row sample.

**Also on 2026-10-07.**
- `brain_items.py` from PowerShell works: 32 items, all indexed, 0 to add.
- The 14:22 maintenance run skipped with "no API connectivity", at the time the desktop link dropped.
- Git's "LF will be replaced by CRLF" warnings on files delivered with LF endings are harmless (core.autocrlf).
"""

RUNBOOK = """

## Stories that still fail the check; the Ganita code; Srangam S2 (DOCS14_2026_10_07)

- **After `patch_verify_names_2026_10_07.py`,** run `python scripts\\stories.py verify-all --doc markandeya_purana`. Expect 11 pass and 2 fail. Approve only after reading.
  - **#3:** fix who Vapu is first (see PLATFORM section 17).
  - **#5:** change "Draupadi" to "the daughter of Drupada", or approve anyway with a note.
  - **#10:** Rewrite.
- **Ganita.** `python scripts\\corpus_status.py --doc Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V`. A wrong `--doc` now says which codes are close.
  - Resume from the dashboard (translate_both, as on 6 Oct) with the machine kept awake. Allow 6-11 hours for the English alone at the measured rate.
- **Srangam S2.** Paste `docs\\cloud\\S2_srangam_followup_2026-10-07.sql` one block at a time (G1-G5, all read-only) and keep the CSVs.
"""

EP = """

## Addendum 2026-10-07 (4): second pass (DOCS14_2026_10_07)

| # | Item | State |
|---|---|---|
| 2.18 | Story check: title words, quotations, visarga stems (VERIFY_NAMES); 11 of 13 pass, 2 real failures left | Built 2026-10-07 |
| 1.16 | corpus_status `--doc` resolves a unique prefix or case, suggests close codes, never falls through to all texts (DOC_HINT) | Built 2026-10-07 |
| S1 | `srangam_cross_reference_stats` live: 1,561 references, 1,392 public (RLS: both articles published) | Done 2026-10-07 14:40 |
| S2 | Read-only follow-up: the full 20260201064547 statement, who can execute increment_term_usage_counts, the live policies, the 169 hidden references by status, SECURITY DEFINER functions anon can run | Ready to run |
| T1 | Ganita_Yukti_Bhasa_of_Jyesthadeva_Sarma_K_V: 977 of 2,706 without English, no Hindi (corrects addendum 3) | Open: resume, machine awake |
| T2 | Translation throughput: 91-157 passages an hour, one call per passage | Open: a measured comparison (thinking budget, batching) on a sample, judged by qa_scan, before any change |
| 1.12 / 1.13 | Maintenance alongside long translations; noise vectors | Open; 1.12 matters more now (T1 keeps the dashboard busy for a day or more) |
| C0 / C1 / C2 | Cloud pre-flight, corpus brain schema, `embed-published-passages` | C0 ready to run; C1 drafted and tested, not applied; C2 after C1 |
"""

TARGETS = [(Path("docs/PLATFORM_2026-10-04.md"), PLATFORM), (Path("RUNBOOK.md"), RUNBOOK),
           (Path("docs/ENTERPRISE_PATH_2026-10-04.md"), EP)]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for p, text in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (p, MARK)); continue
        nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
        todo.append((p, raw + text.replace("\n", nl).encode("utf-8")))
    if args.check:
        print("CHECK OK: %d file(s) to append. Nothing written." % len(todo)); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_docs14_" + stamp))
        t = p.with_name(p.name + ".tmp_docs14"); t.write_bytes(data); os.replace(t, p)
        print("appended %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
