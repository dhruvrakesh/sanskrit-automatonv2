# Consolidation: the scans repaired by themselves (25 Oct 2026)

AUTO_REPAIR_2026_10_25. Asked on 25 Oct: "start this new phase of consolidation and keep on repairing texts using
OCR + vision so that repairing of texts is automated and user approval is only sought to increase the usage limit and
any such things."

## 1. What was there

The repair path for one text has stood since 10-11 Oct (REPAIR_PATH, REPAIR_HEAL, JUDGE_DESK, docs/REPAIR_PATH and
REPAIR_HEAL): repair_text.py judges a text (free), prints its next step (NEXT:), and each step is one command:
--repair (vision OCR of the pages Tesseract misreads, the audit, the merge, through ocr_consensus.py; page files only,
capped by --max-usd), --use-repaired (a backup, then the text wiped and ingested again from the repaired pages;
refused while the dashboard runs a writer, and refused when it would replace paid translations unless --replace N is
said), reingest_pages.py (only the pages that changed), --release. What was missing was someone to run the next step.

## 2. What runs now (scripts/repair_auto.py, the maintenance task's step e, every 3 hours)

- **The first round of each day judges** every text (repair_text.py --judge-all: free, read-only on the database; the
  judgements of 12-23 Oct were stale) and does nothing else: the maintenance task has an hour.
- **Each other round does one step of one text**, the step repair_text.py --doc X names, after asking it afresh:
  - vision (NEXT: ... --repair --max-usd N): run with --max-usd the least of N, $0.10 a round, what is left of the
    day's allowance, and what the cap leaves above its reserve ($1.00). Measured: budget_state's spent_usd before and
    after, written to the round's record;
  - into the database (NEXT: ... --use-repaired, nothing replaced): only when the dashboard answers and runs no job,
    the drive holds the backup and 15 GB besides, and no such step ran today; repair_text.py makes the backup first;
  - a decision (NEXT: --use-repaired --replace N, reingest_pages.py, translate it): written down, and the next text is
    tried (five at most a round).
- **The queue:** the judged texts less those withdrawn, set aside, accepted, being re-translated, the e-text witnesses
  and the Daivat-Sanhita (withdrawn until 1 January 2029: never). Ranked: one step from the database first; then the
  pages vision has not read, material before moderate, the fewest pages left first (texts finished rather than
  begun); then the decisions.
- **The allowance:** $0.25 a day unless set (python scripts\repair_auto.py --allow 0.30; --allow 0 stops the paid
  steps), inside the cap, never past its reserve.
- **What it asks, and how:** data\auto_repair_state.json says "blocked" when the cap is paused or less than its reserve
  is left, or when only decisions are left. health_watch.py reads it: blocked is a warn, and the site mails the super
  admin (C19), as for the other checks. A spent day's allowance is not an ask: the rounds wait for the next day.
- **What it never does:** translate, release to the site, replace paid translations, retire or withdraw a text, open a
  text whose rights forbid it, or run two rounds at once (data\auto_repair.lock).

## 3. The queue on 25 Oct (the judgements of 12-23 Oct; the first round refreshes them)

29 texts. One step from the database, nothing replaced: seven of the short smritis (Yama, Atri, Visnu, Likhita,
Samvarta, Sankha, Ausanasa). Vision to read, material: the Patala Khanda of the Padma Purana (146 pages left), the
Siddhanta Siromani (180), the Harita's third sthana (220), the Taittiriya (496), the Rgveda vol. ii (618); moderate:
Vyasa (20), Gautama (27), Katyayana (43), the Niti Prakasika (44), Parasara (47), the Surya Siddhanta (55),
Yajnavalkya (82), the Kapila Purana (85), the Saura Purana (289). Decisions (eight): five short texts whose swap
replaces 6 to 16 translations each, the Natyasastra's in-place re-ingest, the Ganita Yukti Bhasa (2,374 translations)
and the Nirukta (2,031). The Shukla Yajurveda is being re-translated (in repair), so the rounds leave it alone; its
translation (about $12.2) is an ask of its own.

At $0.25 a day and the vision's measured price (about $0.0007 a page on Flash, measured 29 Aug; repair_text.py uses
each text's own measured price where there is one), the 2,352 pages left would take some days of rounds and a few
dollars; the cap, $8.57 left on 25 Oct with $1.00 kept in reserve, is the limit, and the first ask.

## 4. Safety, as the guardrails have it

- The database is written only by repair_text.py's own --use-repaired, after its own backup and its own refusals.
- Every paid step is capped twice: by repair_text.py's --max-usd and by the round's limit; the spend is measured.
- The rounds run only inside the maintenance task, which skips a tick when the dashboard runs a writer.
- A step that runs past 25 minutes is stopped (taskkill /T of that process tree on Windows).

## 5. Commands

```powershell
python scripts\repair_auto.py                    # the queue and the next step: free
python scripts\repair_auto.py --round --dry-run  # what the next round would run
python scripts\repair_auto.py --allow 0.25       # the allowance a day (0 stops the paid steps)
python scripts\repair_auto.py --log              # the last rounds
```
