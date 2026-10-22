# How the names are joined, what Ask reads, and the path to a better Ask (22 Oct 2026, night) (DOCS89_2026_10_22)

Asked on 22 Oct: "how are we on the inter relationships and does that reflect in ask the corpus which needs a much
better frontend on all local and online ui/ux. are you sure this is the enterprise way?"

Read for this page: docs/BRAIN_PATH_2026-10-21.md (its phases B0 to E), docs/ASKS_2026-10-22.md, scripts/dashboard.py
(`/api/ask`, `/ask`), scripts/ask.html, Srangam's `supabase/functions/search-corpus/` and `src/pages/corpus/`,
docs/cloud/C5 and C6 (the reader functions), D:\backups\corpus_mirror_log.txt (the 20:31 run: 386 groups equal, 0
different), and the backup `context_pre_witness_Bodhicaryavatara__w_gretil_20261022_190412.db`, read as immutable with
`scripts\relations_census.py` (data/context.db was not opened from the VM). Every number below was measured there.

## 1. The inter-relationships, measured

| Layer | What exists | Where |
|---|---|---|
| Names | 13,233 (deities 3,405, persons 2,914, places 779, peoples 400, rivers 201, mountains 87, others 5,447); 41,744 mentions in 15,394 passages | the PC; mirrored (`corpus.entities`, `corpus.mentions`) |
| Named together | two names in one passage: 45,994 pairs; 4,983 in two passages or more; 681 in five or more; 1,539 in two texts or more (248 passages naming more than 12 left out as lists) | computed by relations_census.py; not stored |
| Kinship and school | none stored. The scholars' shelf prints them: the Purana Index has "son of" in 4,759 entries, "father of" 1,424, "daughter of" 684, "wife of" 492, "mother of" 404, "pupil of" 235; Soerensen's index "son of" 1,490, "king of" 355, "daughter of" 336, "wife of" 335; the Vedic Index "patronymic" 645, "pupil of" 202, "son of" 144, "contemporary" 47 | the PC only (CC BY-NC-SA 3.0; the site is H2, yours) |
| The scholars' claims | Raychaudhuri's Part I: 2,010 claims, their names tied to ours (1,706 of 3,917) | the PC only (B1 done; B2 designed) |

**What it shows.** Janaka is named with Yajnavalkya in 33 passages and with Videha in 29; with Ajatasatru, Gargya,
Hasabalaki and Asvala in 3 each: the court of the Brhadaranyaka, the very web Raychaudhuri argued his synchronisms
from. But all of it lies in one text of ours (the Satapatha's book 14): names are found in the English, and 15,239 of
the 15,394 passages that name anyone have English (E2: about a quarter of the live passages have any). The links
across texts, where a historian works, are 1,539 pairs.

**Why the kinships are not read by a pattern.** A trial read "Akrura, daughter of Ugrasena" out of "married the
daughter of Ugrasena". The index's sentence has to be read whole, its direction kept, and checked: phase R2 below.

## 2. What Ask reads today

- **On the PC (`/ask`, scripts/dashboard.py `api_ask`):** the question's meaning is matched against the 26,848
  passages that have vectors (the live passages with working English number 26,836); the 12 nearest, as English cut to 600
  characters, and up to three editorial items (stories, pictures) go to Gemini Flash, which answers citing their
  tags. It is metered and stops at the cap; withdrawn texts are left out. **It reads no Sanskrit, no scholarly
  English, no names, no named-together links, no kinships and no claims.**
- **On the site:** `search-corpus` searches by meaning for the readers and returns passages; "No text is generated"
  (its own header). There is no Ask on the site. The corpus is open to the readers' list only (`corpus.reader_access`
  mode `readers`, set 9 Oct 01:29 UTC).
- **The name page on the site** (`/corpus/names/<name>`, `corpus_reader_name`) lists the passages that name it; it
  shows no one named with it, no kinship and no scholar.

So the relationships do not reach Ask, on the PC or the site.

## 3. The path (each phase surgical, tested, reversible; it extends BRAIN_PATH's B2 to B4)

| Key | Phase | What | Where | Cost |
|---|---|---|---|---|
| relations-together | R1 | The named-together links stored: a new table `entity_links` (two names, "together", passages, texts, three places, when, the marker), rebuilt whole by one script from `entity_mentions`; a backup first; nothing else changes | PC | free |
| relations-index | R2 | The shelf's kinships read: a trial of 100 Purana Index entries by Gemini Flash into subject, relation, object, the index's own words and its references; kept only if the words are in the entry and the names resolve; stored beside the shelf, on the PC | PC | priced by a dry run first |
| relations-check | R3 | Each kinship checked against our verses: "the verse names both" with its place, or "not in our texts" (the editions to seek) | PC | free |
| relations-mirror | R4 | The mirror: C19 (the claims, B2) and C20 (the named-together links: ours, from our texts); the index's kinships only if you decide H2 | PC, Lovable Cloud SQL | free |
| ask-v2 | A1 | Ask on the PC reads more: the scholarly English where a verse has it, the Sanskrit (IAST), the names in the passages found, their named-together neighbours and their claims (public domain); it cites verses, claims (page) and the index (entry); a judge of the other family reads a sample; metered | PC | Google cap, per question |
| ask-site | A2 | Ask on the site: an edge function modelled on search-corpus (it runs as the reader, never the service role; the readers' gate; a daily limit per reader; the cap); the same answer as on the PC; only after A1 is measured | Srangam kit | per question |
| ask-ui | U1 | One Ask page, on the PC and the site alike: the question; the answer with numbered citations; the sources beside it, each verse in Devanagari, IAST and English (the scholarly first), with its standing (an e-text witness, vision or Tesseract, its fidelity) and a link to the reader at that verse; the names as chips to their pages; loading and error states; keyboard and phone | PC and Srangam | free |
| names-ui | U2 | The name page: "Named together with" (R1), "What the scholars say" (B3), "What the indexes say" (H2) | Srangam | free |
| load-measure | U3 | Measured before any cut: Srangam's own `test:perf` (Playwright) and the reader functions' read-only EXPLAIN (BRAIN_PATH E) | Srangam, Lovable Cloud SQL | free |
| english-coverage | E | Names and vectors from the scholarly English, and later from the Sanskrit, so the graph grows beyond the 25% with English; the texts of record first | PC | per text |

Order: R1 and U1 first (free, and each is useful alone); A1 once R1 stands; A2, U2 and R4 after A1 is measured on
the PC; R2 and R3 when you approve the trial.

## 4. Is this the enterprise way?

**What already is:** every change is a patch that is anchored, all-or-nothing, marker-idempotent and backed up; 173
test modules pass in a copy before a release; release.ps1 refuses databases, backups and large files; the database
is written only after a backup; every paid call is metered under a cap; the site's corpus runs as the reader with
row-level security and no service role in search-corpus; the mirror checks every group after each run (386 equal at
20:31); every e-text carries its source and sha256; the rights are read, not assumed.

**What is not yet, and what each would take:**

| Gap | What it costs us | The enterprise answer | Yours? |
|---|---|---|---|
| No CI | The tests run only when you run them (the cp1252 failures were found by hand) | A GitHub Actions workflow running the same suite on Ubuntu and Windows on every push, never deploying (remix-of-dkegl-website already has one: .github/workflows/ci.yml) | Yes: a standing configuration on GitHub |
| No staging for Srangam | Publish goes straight to the live site | A preview of each change before Publish, if Lovable's plan offers one; else the checks before and after, as now | Yes |
| The corpus schema lives in the Automaton's docs/cloud, not in Srangam's migrations | Two places to read the database's shape | Keep docs/cloud as the record (the guardrail: never hand-insert into schema_migrations), with an index of what is applied; doc_register.py's pattern for SQL | Next |
| Append-only documents (PLATFORM 2,726 lines, RUNBOOK 2,456, ENTERPRISE_PATH 1,165, before DOCS89) | Hard to find what is true now; labels reused | ASKS as the state, an ARCHITECTURE page for what is, a RUNBOOK of current procedures only, the addenda kept as history | Next |
| No alert when a scheduled run fails | A failure is seen only in a log | A daily health line by mail through the Corner's mailer (corner-mail, already configured) when the mirror or a task fails | Yes: a mail you receive |
| Security review incomplete | `gdrive-image-proxy` open since 4 Oct (S5) | The edge-function review (R1), the proxy limited to the images the articles use | Next |

So: the discipline is enterprise-grade; the process around it (CI, staging, alerts, one current set of documents)
is not yet, and each of those is a decision of yours before it is built.
