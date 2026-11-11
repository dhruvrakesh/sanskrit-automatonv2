# Our findings: what of the scholars' reading the site may carry (11 Nov 2026)

DOCS106_2026_11_11. Asked on 11 Nov: "we might not publish BC Law's book on the site, but our analysis through the
reading of both Law and Raychaudhuri and our own research, if pointing to something original, is our research and can
be used/published with proper citations. That is exactly the kind of research automation and self improvement we aim
at." This page writes the rule down, says what a finding is, how it will be made and checked (R1, planned), and where
the dynasties read on 11 Nov (G5a) come in. It is not legal advice: the line drawn here is the usual one (facts and
ideas are free; a work's expression is not; short quotation with acknowledgement for research and review), and it
errs on the side of the author.

## 1. The rule, from 11 Nov

| What | On the site? |
|---|---|
| B. C. Law, *Ancient Indian Tribes* (Lahore 1926; Law died in 1969, so in copyright in India to the end of 2029): its text, its page images, his claims as `scholar_claims.py` extracted them | No. Private reading on this PC, as before |
| H. C. Raychaudhuri, *Political History of Ancient India* (1923; Raychaudhuri died in 1957: in the public domain in India since 2018): his claims with their pages | Yes, as the site already carries them |
| A finding of ours: a sentence or a short paragraph in our own words that joins what the sources say (Law, Raychaudhuri, the Puranas' verses, the indexes) about a people, a king, a line or a place, each source cited by page or verse | Yes, once a person has read and approved it |
| A quotation from Law inside a finding | Only when the finding needs his words: a few words, in quotation marks, with the page. Never his paragraphs |

What makes a finding ours: it says something no one source says by itself. Four kinds:

- **agreement**: Law and Raychaudhuri (or a Purana) say the same of a people, from different evidence; the finding says
  so and cites both;
- **disagreement**: they differ (a capital, a date, a king's line), and the finding sets the readings side by side;
- **new link**: a tie the sources do not make themselves, such as a tribe of Law's matched to a line the Visnupurana
  traces verse by verse (G5a), or to a person of Sorensen's index;
- **open question**: what the sources leave unsettled, said as a question.

## 2. How a finding will be made and checked (R1: planned, priced, not built)

1. The inputs, all here already: `peoples_index.py`'s peoples (Raychaudhuri's and Law's claims, with their pages); G5a's
   verified kinship statements (with their verses); the indexes' persons (Sorensen, the Purana Index); the verses of
   our texts.
2. One Claude call per people (about 54 now): the candidate findings as JSON, each with its kind and its citations
   (claim ids, verse references), written in our words.
3. Machine checks before a person sees one: every citation names a claim or a verse we hold; no run of eight words of
   the finding is in Law's pages (an n-gram check against the EPUB's text on this PC); a "new link" cites at least two
   sources of different kinds; the people's name and the cited persons are in the cited claims or verses.
4. A person reads each on the desk and approves, rewords or drops it. Only approved findings go on.
5. C28 sends them to the site with their citations; the page says "Our finding" and lists the sources (Law by page,
   never at length).

The money: about $1 to $3 of the Claude credit (claude-sonnet-5-5), after G5a, whose lines most findings will cite.

## 3. G5a: the dynasties read verse by verse (built 11 Nov)

`scripts\vamsa_read.py` (VAMSA_READ_2026_11_11) reads GRETIL's plain text of the Visnupurana, book 4, and the
Bhagavatapurana, book 9 and 12.1, from `sources\gretil\1_sanskr.zip` (already on this PC), one chapter at a time, with
Claude, into kinship statements: who is whose son, daughter, wife, brother or sister, who reigned after whom, which
line is named after whom. Each statement carries the verse it rests on and the Sanskrit words that say it, and the
machine checks each one:

| Check | Means |
|---|---|
| verified | the words are in the cited verse (or run into the next), and both names are in it or in the verse before (where a pronoun's person is named) |
| words | the words are there; a name is not (an epithet, a spelling) |
| unsupported | the words are not in the verse cited |
| bad | no verse of this chapter, an unknown relation, a field missing |

The plan on the real archive (11 Nov): the Visnupurana book 4, 33 parts, 1,343 verses; the Bhagavatapurana book 9, 30
parts, 965 verses; 12.1, 41 verses: about $1.82 in all, a guess until the trial measures the answers' length. The
replies are kept (data\vamsa_read), so the checks can be run again for free (`--reparse`), and `--report` writes
`exports\vamsa_read_<work>.csv` and prints the longest father-to-son lines found.

GRETIL's texts are CC BY-NC-SA 4.0 (non-commercial; credit GRETIL and the data entry; share alike). The statements stay
on this PC until you decide; on the site they would carry GRETIL's credit and the same licence.

Then: G5b joins the verified statements to the index's persons (free; Arjuna's line through Pandu checked against the
Kuru line as the Bhagavatapurana's book 9 tells it); G5c sends them (C28) and adds a Dynasties page: a line, verse by verse, with
each step's verse a click away.
