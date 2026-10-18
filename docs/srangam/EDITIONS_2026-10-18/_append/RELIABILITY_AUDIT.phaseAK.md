## Phase AK - The scholarly editions, open to everyone (EDITIONS_SITE_2026_10_18, 2026-10-18)

Asked on 18 Oct: the scholarly works on Srangam "for max effect and distribution", the GRETIL texts published with
their credit. The automaton's scholarly English (the Sanskrit beside an English in the register of an unabridged
translation, notes at each chapter's end, a dagger on what a person has not yet read) was on the PC only.

### AK.1 - What changes
- The automaton's scripts/publish_editions.py writes each edition named in its configs/editions.json as a static
  page, public/scholarly/<slug>.html, with public/scholarly/index.json. Each page carries a bar back to /editions, the
  credits of its Sanskrit (GRETIL's file, its data entry, CC BY-NC-SA 4.0) and the licence of its English, and its
  canonical address. A text held in repair or withdrawn, a witness without its source and licence, or an edition
  with no scholarly English is refused there; nothing is published by this repo's code.
- src/pages/Editions.tsx at /editions, src/lib/editions.ts: the list from the index, each edition with its counts,
  credits and a link to its page. No index yet (404, or the site's own page answering for it) is "none yet"; any
  other failure is shown as a failure. An entry with an unsafe file or a non-https link is dropped.
- public/config/nav.config.json: "Editions" in the header for everyone (and so in the phone's menu);
  src/components/navigation/CorpusMenu.tsx: "Scholarly editions" in the Corpus menu; public/sitemap.xml: /editions.
- src/__tests__/editions-page.test.tsx (4 tests).

### AK.2 - Load
- /editions reads one small JSON file (cached five minutes); an edition is a static page of about 1 MB, with no
  script, served as it is. No question to the database.

### Invariants added (Phase AK)
58. An edition on /editions is a static file the automaton published from its own config, with its sources credited
    and its licence stated; the page links only to /scholarly/<slug>.html and to https addresses, and a failed load
    is never shown as an empty list.
