# The two Āgamas on claude-sonnet-5-5: the decision, its guardrails, the runs (2026-10-15)

Markers:
- **AUDIT_2026_10_15:** `scripts/scholar_translate.py`, patched by `scripts/patch_audit_2026_10_15.py`.
- **DOCS58_2026_10_15:** `scripts/patch_docs58_2026_10_15.py`.

It follows PILOT_FIX (docs/PILOT_2026-10-15.md), which is applied on the PC and not yet released.

## 1. The decision

**15 Oct (Dhruv):** claude-sonnet-5-5, at its own effort (high), makes the scholarly English of the Hayaśīrṣa
Pañcarātra and the Kāraṇāgama.

**For it:**
- **Cost:** $0.036 a verse, against Opus's $0.063 and gemini-2.5-pro's $0.071.
- **Speed:** about 20 seconds a verse, against 1.4 and 2.4 minutes.
- **The judge of the other family:** gemini-2.5-pro read it as the best in 3 of 5 spans and found no major error in it.
- **The credit:** the two texts fit in it with half to spare.

**Against it, or not yet known:**
- The evidence is ten verses of one text.
- The two judges agreed on the best in 1 of 4 spans.
- The Opus judge preferred Opus, its own model.
- The Kāraṇāgama was not in the pilot.
- In a Claude run the critic is the translator's own model.

**So the decision stands on guardrails that would show it to be wrong early and cheaply** (section 2), rather than
on more benchmarking.

## 2. The guardrails

1. **A canary first:** the first paṭala of each text (the Hayaśīrṣa's pages 17 to 19, 21 verses; the Kāraṇāgama's
   pages 27 to 29, 16 verses), with the audit on 1 sentence in 3. It goes on to the whole only if:
   - at least 70% pass after the audit;
   - no error repeats across verses (a name, a term, a misread construction);
   - the cost is at most $0.05 a verse.
2. **The audit (AUDIT_2026_10_15)** on 1 sentence in 10 in the whole run. Gemini's critic (gemini-2.5-pro, the same
   critic prompt) reads the last version, and its reading decides the status:
   - a major issue, or a fidelity or completeness below 4, flags the verse for a person;
   - a source issue makes it a source doubt;
   - it does not revise.
3. **The second judge** on 1 sentence in 10 where the working English exists (`--compare-every 10`). The Kāraṇāgama's
   working English is being made now; the Hayaśīrṣa's is queued.
4. **Caps:**
   - `--max-usd` for each window;
   - the Claude credit's $190, which fails closed and stops on 11 Nov;
   - Google's spend cap for the judges.
5. **Resumable:** `--fill-engine`. A window that stops (Ctrl-C, a rate limit, three failures running) goes on with the
   same command. Each window is its own process.
6. **Nothing is overwritten:**
   - scholar_translations is append-only (a row a verse a version, with its engine, prompt_version and src_hash);
   - any verse can be redone later by another engine (Opus for the flagged, for one);
   - a row whose Sanskrit changes goes stale, not wrong;
   - the working English and the site are not touched.
7. **A person reads** the flagged verses and the source doubts (`--review ... --verdict accept|reject --by`).
8. **A backup of the database** before the whole run (db_backup.py: SQLite's online backup).
9. **The code in git before the run** (the release), so that every row's engine and prompt_version point at code that
   is kept.
10. **A watch:** `scholar_translate.py --doc ... --status` (free, read-only) gives, per engine:
    - the verses done of those ready;
    - passed, flagged, source doubts, stale, audited;
    - the spend and the last row's time;
    - and the credit.

## 3. AUDIT_2026_10_15

- `--audit-every N` (a Claude engine; 0, none, by default). The sentences are chosen by the hash of their first
  passage, with another seed than the second judge's.
- The audit is stored as the last entry of the row's critique, with `"by": "gemini:gemini-2.5-pro"`.
  - The pages say "The audit by ...".
  - A run prints `[the audit: accept|revise]`.
  - Its cost is the row's.
- `--status`: see section 2, item 10.
- The dry run says the audit; the NEXT line keeps `--audit-every` and `--min-quality`.

## 4. The runs

**The ranges** (by the dry runs on the backup of 14 Oct):
- The Hayaśīrṣa: pages 6 and 7 are its table of contents, and the text begins on page 17. 1,420 verses are ready from
  page 17 (1,418 at `--min-quality 0.5`). Thirds: pages 17-61, 62-110, 111-189.
- The Kāraṇāgama: its front matter is Hindi or OCR noise, and the text begins on page 27. 1,028 verses are ready
  (1,019 at 0.5, which leaves out nine short Hindi notes). Thirds: pages 27-79, 80-122, 123-183.

**The cost, by the pilot's measure:**
- **The canary:** about $1.30 of the credit and $0.40 of Google's.
- **The whole:** about $88 of the credit; about $7 of Google's for the audit, and some $3 for the second judge on the
  Kāraṇāgama.
- **The credit left after both:** about $95. That is the Tantrik Texts vol. I after its re-ingest (2,538 verses, about
  $91), or Opus on the flagged.

**Time:** about 20 seconds a verse, so some 2.7 hours for a third of the Hayaśīrṣa and 2 for a third of the
Kāraṇāgama. Run the three windows of one text at a time; add the other text's three only if no rate-limit failures
show.

**After:**
- `--report`: read the flagged verses first;
- `--review`;
- `repair_text.py --release` for each text only after its working English is back (the dashboard is making the
  Kāraṇāgama's now);
- then S4 (the scholarly English in Srangam's reader) and Hindi from the accepted English.
