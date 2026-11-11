# The genealogies mended, explained, and the path to the dynasties; B. C. Law read into claims (10 Nov 2026)

Markers: **GENEALOGY_HEAL_2026_11_10** (scripts/vamsa_view.py, scripts/index_sync.py; the Srangam kit
docs/srangam/GENEALOGY_HEAL_2026-11-10/ by scripts/patch_srangam_genealogy_heal_2026_11_10.py), **C26_INDEX_ALIASES_2026_11_10**
(docs/cloud/C26_index_aliases_2026-11-10.sql), **CLAIMS_EPUB_2026_11_10** (scripts/scholar_claims.py, kin_index.py,
relations_view.py, peoples_index.py) and **DOCS104_2026_11_10**. It follows docs/LOAD_AND_STORIES_2026-11-09.md (release
`321f542f`, DOCS103, pushed).

## 1. What was asked, and the short answer

Asked on 10 Nov, with screenshots of /corpus/genealogies/inm/-933 (Anga) and /corpus/genealogies/inm/9368 (Kaunteya):

> "Such a genealogy front end does not make sense for anybody. At least explain what you are putting in graphs here.
> Has to be an API call thing. We can't even get the genealogy of Kaunteya (Arjun) right, not to say what will happen
> if we start looking for specific dynasties, vamshas, etc. Why haven't you thought of all this? Are we done in full?
> ... EPUB of B. C. Law's book in source to ingest as per our algo now."

**Done in full? No.** The pages were what INDEX_SITE_2026-10-25.md section 7 already warned: one index's statements
joined by machine, with marks nobody explained. This round mends what the indexes' own words can mend, says on the page
what every mark means, and charts the dynasties (section 5), which need the Puranas' genealogical chapters read verse
by verse. B. C. Law's book is made ready to read, privately (section 6).

## 2. What was wrong, found on the real data (the backup of 10 Nov, kin.db of 12:50, read-only)

| What the screenshots showed | Why |
|---|---|
| "Kaunteya" drawn as a person, two generations (Kunti -> Kaunteya) | Sorensen's entry 9368 is the plural "the sons of Kunti"; his entries Kaunteya[1] to [4] read "= Arjuna", "= Bhimasena", "= Karna", "= Yudhisthira". He defines **5,525 of his 12,647 entries** so ("Partha = Arjuna", "Dhananjaya = Arjuna, q.v."). The desk read the kinships from the entries and left the "=" aside |
| Arjuna's line up through Indra, Kasyapa, Marici, Brahman, Visnu | The index states two fathers: Indra (the begetter) and Pandu. Pandu's statement "father of Arjuna" names "Arjuna" without saying which of Sorensen's Arjunas, so it stayed "a name only"; the rule then took the longer line, the god's |
| Anga's 24 generations: Anga, Antardhaman ... Daksa, Aditi, Visnu, Brahman, Marici, Kasyapa, Indra, Arjuna ... | A line that turned back on itself (Kasyapa is Aditi's husband, drawn four generations below her) and ran through mothers (Aditi, Svarbhanavi) |
| "0 of 23 steps with both names in the cited verse" | Sorensen cites the Calcutta edition (1834-39) by its running verse numbers, which the critical edition does not keep: none of his steps can ever show it. The page did not say so |
| A coloured strip, chips, solid and dashed rails, "a name only", "line through" | Never explained on the page |

Found besides, and not mended this round (section 5): kin_index.py cuts an entry at 12,000 characters
(ENTRY_MAX). 52 of Sorensen's entries are longer, 967,210 characters beyond the cut, and they are the great persons:
Arjuna 147,292 characters, Indra 89,301, Krsna 74,669, Siva 70,574, Yudhisthira 52,882, Karna 41,186, Bhisma 34,115 (read:
0 kinships, his entry opening with lists of references).

## 3. The mends (GENEALOGY_HEAL_2026_11_10), from the indexes' own words, no model

| Mend | The rule | On the real data |
|---|---|---|
| The epithets | An entry that defines itself as another ("(the son of Kunti) = Arjuna"; the Purana Index's "a name of Rama") is tied to that person's entry: by the entry's number; the index's only entry of that name; the only one with a line; the one the index says most of; else every entry of the name, "not told apart". A plural without its own "=" names the persons its singular entries name. The letters as printed come first (Krsna is not Krsnaa, the name of Draupadi) | 6,575 entries read; **5,602 name a person** (Sorensen 5,333, the Purana Index 269): one person 4,943, a group 72, not told apart 587 (318 of them Krsna's five entries, from the thousand names). Kaunteya[1] = Arjuna[2]; Kaunteya = Arjuna, Bhimasena, Karna, Yudhisthira; Vasudeva (I) = Krsna (I) |
| The line's father | A son with two fathers is drawn up through his mother's husband, as the dynasties count him; the begetter stays beside him, and "line through" draws his line. Down, a son before a daughter, and never into a child counted in another father's line | Arjuna: Pandu, not Indra |
| The joins | A name of several entries is joined to the one entry that gives at least three of the names the stating entry gives, and more than any other ("shared") | 125 more sides joined ("a name only" 7,624 -> 7,499); Pandu's "father of Arjuna" is now the Pandava's entry |
| No line turns back | A line never passes to a person married to one already on it | Kasyapa is no longer drawn under Aditi |
| The longest lines | Fathers' lines: from a man without a father in the index, ending before a daughter | 53 -> 46 lines. The Purana Index's first six are the Puranas' own genealogies: the Iksvakus from Kalmasapada through Raghu, Aja, Dasaratha, Rama, Kusa (38); the Anavas from Yayati's son Anu to the kings of Anga (32); the Videhas (30); the Yadavas of Vidarbha (29); Dhundhumara to Hariscandra (26); Amsumat, Dilipa, Bhagiratha (25) |

The rows for the site, built from the same stores (10 Nov backup): persons 14,979 -> 20,221 (5,351 added: 5,315 an
epithet's own row, no line), 109 removed (named-only persons now joined), 1,450 changed (the lines of 976 persons);
steps 10,861 -> 10,839 (68 added, 90 removed); statements 87 changed; lines 53 -> 46. index_sync.py sends what differs.

**What these rules cannot mend.** Arjuna's line now runs up through Pandu, then through Vyasa (Pandu's begetter,
stated in both entries) to Parasara, Sakti and Vasistha, not through Vicitravirya and Santanu: the index states
"Pandu son of Vicitravirya" but never names Ambalika as Pandu's mother, so the mother's-husband rule has nothing to
hold. Sorensen's fifth line still runs Ayus, Nahusa, Yayati, Yadu ... Vasudeva, Krsna, Brahman, Daksa: a cosmogony
joined to a dynasty by the index's own statements. And the great persons' entries are read only to their first
12,000 characters. One index's statements cannot make a dynasty; the dynasties come from the texts (section 5).

## 4. The site: explained, and the epithets (C26, the Srangam kit)

- **"How to read this page"** (closed until opened) on both pages: what a line is and is not; the numbers on the left;
  the strip's four colours; the chips (verse (check), MBh 7, ours: together); solid and dashed rails; two fathers and "line
  through"; epithets; "a name only" and "by the names both entries give"; that a line is not yet a reconciled dynasty.
- **An epithet sends the reader on**: Kaunteya[1] "is another name for Arjuna[2], not a person of its own"; the plural
  "names 4 persons: Arjuna, Bhimasena, Karna and Yudhisthira"; a search for "dhananjaya" or "partha" finds the epithet
  and links to Arjuna.
- **Sorensen's pages** count "steps named together in the epics' verses" instead of the cited verse, and say why.
- **"The longest fathers' lines"**, said to be one index's statements joined.
- C26 adds `same_as` and `gloss` to corpus.index_persons, takes them in corpus_index_ingest, gives them through
  corpus._index_person (so the tree) and corpus_reader_index_find (which finds an epithet too), and says so in the
  manifest (`features.aliases`). index_sync.py sends the epithets only to a site whose manifest says so; before C26 it
  sends the rows without them, so the order of the steps does not matter.

## 5. The path: the dynasties from the texts (G5), and the great persons read whole (kin-long)

"Has to be an API call thing": the model reads the Sanskrit once, on the desk, metered; the machine checks every
answer against the verse; the site asks the mirror (a reader function: an API call) and never a model.

| Phase | Key | What | Cost |
|---|---|---|---|
| G5a | vamsa-read | `vamsa_read.py` (to build): Claude (claude-sonnet-5-5, the credit) reads the genealogical chapters of GRETIL's texts chapter by chapter and lists every kinship the verses state: father, mother, begetter (a ksetraja son), adoptive; husband and wife; the dynasty the text names (Iksvaku, Puru, Yadu, Kuru, Brhadratha). Each with its verse and the Sanskrit words that state it, checked by machine (the words in the verse, both names found by vamsa_check's finder). First slice: the Visnu's book IV (1,341 units) and the Bhagavata's book IX with XII.1 (1,005): the chapters the Purana Index cites most | about $3 to $8 (priced by its plan before it runs) |
| G5b | vamsa-reconcile | The same generations in both Puranas aligned; each step marked where the Purana Index, Sorensen, our passages and Raychaudhuri agree or differ | free |
| G5c | vamsa-site | C27 and a "Dynasties" page: the Solar line (Manu, Iksvaku ... Raghu, Rama ... Brhadbala), the Lunar (Pururavas, Ayus, Nahusa, Yayati; the Pauravas to the Kurus, the Pandavas, Pariksit, Janamejaya; the Yadavas to Vasudeva and Krsna), the Videhas, the Kasis, the Barhadrathas of Magadha; each generation with its verse in both texts; a search that resolves epithets (C26) | free |
| G5d | vamsa-more | The Harivamsa's genealogical chapters, the Matsya's (to 176) and the Brahmanda's | about $5 to $10 |
| kin-long | kin-long | kin_index.py reads Sorensen's 52 long entries whole, in windows of 12,000 characters (967,210 characters never read: Arjuna, Krsna, Yudhisthira, Karna, Bhisma) | about $1 to $2 on Google's cap |

## 6. B. C. Law, Ancient Indian Tribes (1926), read into claims, privately (CLAIMS_EPUB_2026_11_10)

**The copy.** `inbox\2015.78161.Ancient-Indian-Tribes.epub` (232,202,489 bytes; md5 20edab5f62d1d54bf6772339d99d41f6):
the Internet Archive's EPUB of the Digital Library of India's scan 2015.78161 (Osmania University Library): B. C. Law,
*Ancient Indian Tribes* (Lahore: Motilal Banarsidass, 1926; The Punjab Oriental (Sanskrit) Series, No. XII), the five
tribes the Kasis (pp. 1-33), the Kosalas (34-85), the Asmakas or Assakas (86-92), the Magadhas (93-175) and the Bhojas
(176-191). This is not *Tribes in Ancient India* (Poona, 1943), which PEOPLES_2026-10-28.md named. 226 pages in its
spine, each a scan and its OCR; the scan lacks printed pages 113-116, and five pages are plates or blank. The DLI's own
record marks it "In_copyright": Law died in 1969, so in India it is in copyright to the end of 2029. It is read as
private reading on this PC; its licence does not begin "public domain", so index_sync.py never sends its claims, the
Professor marks each one "in copyright: private reading", and from 1 Jan 2030 it may be read as Raychaudhuri is.

**The algorithm, as Raychaudhuri's.** `scholar_claims.py --work law1926`: `--extract` (free) takes each page's OCR
text from the EPUB (the Internet Archive's note "The text on this page is estimated to be only N% accurate" set aside)
and its printed number from the running heads; `--part 1` to `--part 5` (and `pre`) read each page with Gemini
(Google's cap), as Raychaudhuri was read, the page's scan sent with its OCR text because that OCR is poor ("Ka^i" for
Kasi; "Divodasa, the son of Bimbisara" for "of Bhimasena"): the model reads the words from the scan and copies its
quotation from the OCR text, which is then checked against the page by machine. Raychaudhuri's prompt is unchanged
(tested: the same text). Then `--link` ties the names to ours, and `peoples_index.py --yes` puts his claims beside the
peoples of the Puranas' lists, under his name ("scholars"), never as Raychaudhuri's.

**What else changed for a work in copyright.** kin_index.py weighs the indexes' relations against the public-domain
works only (those verdicts are shown on the site as Raychaudhuri's); the desk's Relations page names each claim's own
work.

**Measured (free, on a copy):** `--extract` on the real EPUB: 226 pages, 330,312 characters, 23 pages with almost no
text; the parts as above. The plan for all five chapters and the preface: 195 pages (7 of them plates or nearly blank), about $2.34 at $0.012 a
page (the scan adds about $0.001 a page). Google's cap: $117.84 of $135.00 spent.

## 7. The steps, in order

1. The automaton: `python scripts\patch_claims_epub_2026_11_10.py --check`, then without;
   `python scripts\patch_genealogy_heal_2026_11_10.py --check`, then without; `python scripts\patch_docs104_2026_11_10.py`;
   `python scripts\docs_map.py --write`; run_tests (231 modules).
2. C26 in the Lovable Cloud SQL editor: B1 and B2 (read-only), the change (one paste), A1 and A3; A2 after step 4.
3. Srangam: the kit's patcher (`--check`, then without), `npm run typecheck`, `npx vitest run`, `npm run build`, commit,
   push, Publish.
4. `python scripts\index_sync.py`, then `--apply` (or the next tick of the mirror task).
5. B. C. Law: the EPUB moved to data\shelf\law1926\; `--extract`; a trial of three pages; the five chapters; `--link`;
   `--report`; `peoples_index.py --yes`.

Rollback: the `.bak_claimsepub_` and `.bak_genheal_` copies; C26's header; `git revert` of the Srangam commit.

## 8. Tested

- tests/test_genealogy_heal_2026_11_10.py (27): the rules on a made-up shelf (Arjuna up through Pandu; down from
  Indra to Jayanta, not Arjuna nor Devasena; Daksa's line stops before Kasyapa; a "shared" join; the fathers' lines),
  the epithets (Kaunteya[1], the "do." gloss, the plural, a Purana Index "name of", the parser's refusals), the rows and
  the old site's rows (without_aliases: hashes as before), C26's text; against PostgreSQL 16 with C4, C4b, C5, C21 and
  C23: before C26 the epithets wait and the rest is verified; C26 pasted twice; then they go, find gives an epithet,
  the tree a person's same_as, anon is refused, a second sync sends nothing; and B. C. Law: the work private, the
  printed pages, an EPUB's pages and scans, a page read with its scan (stubbed), the historian's verdicts from
  public-domain works only.
- The existing PostgreSQL suites (index_site 24, b2_site 14) pass with the changes; the full automaton suite on a copy
  with both patchers applied: 230 modules, none failed.
- Srangam main (`9a22055`) in the PC's Linux workspace with the kit: `tsc` clean; Vitest: genealogy-heal, index-site and
  b2-site 36 passed; the whole run 405 passed, 2 skipped, two files failing to load for want of the .env
  (texts-reader, article-dom-overflow: "supabaseUrl is required"), as without the kit; `vite build` 36 s (the two pages
  4.0 and 6.1 kB gzip).
- The real data: the build above; `--extract` and the plan of law1926 on a copy of claims.db.
