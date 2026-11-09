# Load times measured, the stories mended, the Claude credit planned (9 Nov 2026)

DOCS102_2026_11_09, with these patches:

- LOAD_CARDS_2026_11_09 (Srangam);
- STORY_QUALITY_2026_11_09 (scripts\stories.py, scripts\images.py);
- docs\cloud\C25_article_cards_2026-11-09.sql.

The asks of 9 Nov were:

- "the quality of stories being mined and generated can be much better, can't it?";
- whether stories and images reach Srangam;
- the $200 of Anthropic credit used to best effect;
- the Raychaudhuri and tribes ask again;
- "IS LOCAL AND CLOUD DB and ui/ux and navigation and benchmarked interface and load times COMING ALONG WELL?"

## 1. Load times, measured for the first time

Playwright (Chromium) loaded each page of https://srangam.nartiang.org twice on 9 Nov: cold, in a new browser
context, then warm, in the same context. The load ran from Anthropic's cloud, not from India, so add the network
from a reader's phone to these figures. Times are in milliseconds; LCP is the largest contentful paint. "To idle" is
the time until the network went quiet. The corpus pages ask a reader to sign in, so what was measured there is the
shell of each page, not its data.

| Page | Cold TTFB | Cold LCP | Cold to idle | Warm LCP | Transferred (cold) |
|---|---|---|---|---|---|
| / (home) | 831 | 2,504 | 5,920 | 592 | 3,091 KB |
| /corpus | 221 | 1,936 | 2,448 | 376 | about 1.4 MB uncompressed |
| /corpus/stories | 205 | 2,096 | 2,572 | 336 | the same |
| /corpus/genealogies | 160 | 1,944 | 2,416 | 452 | the same |
| /corpus/scholarly | 162 | 1,452 | 2,038 | 480 | the same |
| /corpus/library | 178 | 1,664 | 2,266 | 456 | the same |

**The finding: one query is 75% of the home page.** The home page and /articles transferred 3,091 and 3,166 KB.
Of that, 2,329 KB was one query: `srangam_articles?select=*&status=eq.published`, run by `useAllArticles`
(src/hooks/useArticles.ts).

- It reads all 50 published articles, with every column.
- `content` is 4.64 MB of the reply's 4.73 MB uncompressed.
- It was read only to learn which languages have a body.

**The mend (LOAD_CARDS_2026_11_09):**

- C25 makes a view, `public.srangam_article_cards`: the cards' twelve columns, plus `body_languages`, computed in the
  database by the same rule. It runs with the invoker's rights and is granted to anon and authenticated.
- The hook reads the view, bounded at 1000. While the view is not there, it falls back to the old read (now bounded
  too), so the order of pasting C25 and publishing does not matter.
- Srangam's ratchet of unbounded reads falls by one.
- Expected: about 2.3 MB less on the home page and on /articles, for a cold visit. Measure again after Publish with
  the same script (section 6).

**What is still heavy, for the next round:**

- Every page loads about 1 MB of JavaScript, uncompressed. index-*.js alone is 574 KB uncompressed (160 KB
  transferred). The rest is vendor-react, vendor-supabase, vendor-i18n and the page's own chunk.
- Fonts for four Indic scripts are asked for on the home page.
- The hero image is 173 KB.

None of these is cut here; each wants its own measured round.

## 2. The stories

What the Stories page showed on 28 Oct, read against stories.py:

- **#66 (MBh01, Parasurama) "NEEDS REVIEW: names not found in the cited passages: ksatriyas".** The check took every
  IAST word for a name, so the lowercase common noun ksatriyas failed it. This was a false failure.
- **The Ganita Yukti Bhasa: 8 "episodes" mined from a mathematical treatise.** The 8 were calculations, a
  construction and an east-west line. The miner had no way to say "no story here".
- **#81: "Proposing an image" FAILED twice.** The model's JSON had something after it (an extra brace), and the parse
  stopped on it.
- **The Ganita's "Write found episodes" failed twice on HTTP 429.** The 4-second and 8-second waits could not outlast
  the per-minute limit.
- **The English given to the writer was the working English, even where a scholarly English stood.** For example,
  MBh01 has 38 verses with a passed scholarly English.

What STORY_QUALITY_2026_11_09 changes:

- **The best English for each passage.**
  - The writer, the miner and the check all read a passage's scholarly English where its latest scholarly row
    passed, or was accepted by a person, and its Sanskrit is unchanged since. Otherwise they read its working English.
  - Such lines are marked "(scholarly)" in the prompt.
  - A witness with only scholarly English can now be mined and written; its stories stay on the PC until the
    witness is adopted. The Markandeya's GRETIL witness has 1,291 passed verses.
  - `SA_STORY_SCHOLARLY=0` turns this off.
- **Claude as the writer, by choice.**
  - Set `SA_STORY_WRITER=anthropic:claude-sonnet-5-5@medium` in .env and the stories and the versions for younger
    readers are written by Claude Sonnet 5.5, through claude_engine.py.
  - Each call is paid from the Claude credit, stopped by its meter, and recorded in usage_log.
  - Unset, Gemini writes them as before.
  - Mining and the image ideas stay with Gemini.
  - A test's stub always takes the Gemini path, so no test reaches a paid API.
- **A storyteller's telling, within the rules.** Rule (7) of the writer's instruction: begin in the scene, keep the
  order of events, let the speakers' own words carry the turns, keep the concrete details, and add no summing-up or
  moral the passages do not state.
- **The miner and a treatise.** "If the passages tell no such episode (a treatise: a calculation, a rule, a
  definition, a commentary), return no episode."
- **The check.**
  - A lowercase IAST word is a common noun, not a name.
  - A name spelt otherwise in the passages is found: Krishna and krsna, Kshatriya and ksatriya, an English plural on
    an IAST stem.
  - An invented name still fails, as the Mrnjiga of 5 Oct did.
- **images.py.**
  - A reply with something after its JSON gives its first value.
  - A 429 waits as Google's retryDelay asks, at most 60 seconds, and gets a fourth try.

What stays the same: nothing is published until a person approves it.

**What reaches Srangam, and when:**

- **Stories:** corpus_sync.py sends every story of a live text, at every tick (every two hours). Srangam's
  /corpus/stories shows readers the approved ones only; editors see the rest marked "not approved". So a story
  approved on the desk is on the site within two hours. On 9 Nov the desk had 27 approved stories (the Markandeya 13,
  the Nilamata 14), and 82 in all.
- **Images:** corpus_media.py renders each picture twice and puts the renditions on Google Drive (folder
  1A9yLVNC4iLWuYoueP6b3aECEyne2XQXa), then tells the site. On 9 Nov all 124 renditions of the 62 pictures (19
  approved) were on Drive, and the site's pictures equalled the desk's. Image #111 (Parasurama), drawn and approved
  on 28 Oct, is among them.
- **"Update brain":** builds the PC's own index (brain_items: stories, episodes and images, embedded for the PC's
  Ask). It stays on the PC. The site's search reads its own vectors.

## 3. The Claude credit (written by Claude: a model recommending its own maker's models; the costs are the project's measured ones)

**The credit, as the Console shows it on 9 Nov:**

- $10.57 left of the grant of 15 Oct, which ends 11 Nov.
- $200 granted on 9 Nov, which ends 11 Dec.
- The grant of 15 Oct was spent, $189.09 of it through this project's meter:

| Spent on | Amount |
|---|---|
| The Hayasirsa's scholarly English | $62.11 |
| The Karanagama's scholarly English | $42.19 |
| The Markandeya witness's scholarly English | $36.65 |
| The Surya's scholarly English | $22.22 |
| The benchmarks and judges | the rest |

**The meter.** claude_engine.py still holds the old grant: $190 since 15 Oct, ending 11 Nov, with $0.92 left. So it
sends nothing until .env names the new one:

```
SA_CLAUDE_CREDIT_USD=200
SA_CLAUDE_CREDIT_SINCE=2026-11-09
SA_CLAUDE_CREDIT_EXPIRES=2026-12-11
```

The $10.57 of the old grant is left out of the cap, as a margin.

**The plan, in the order it pays.** Each run is a dry run first, then a trial of 20 when the step is new. The costs
are measured:

- scholarly English: $0.0128 to $0.0205 a verse (Claude Sonnet 5.5, 15 to 21 Oct);
- working English: $0.0064 a passage (the Ganita, 18 Oct);
- a story: about $0.06 (estimated from the prices).

| # | What | Why first | About |
|---|---|---|---|
| 1 | Stories with Claude: the candidates (MBh01 11, Nilamata 9, Markandeya 5, Mallapurana 5, Nirukta 11) | Visible quality; small | $3 |
| 2 | The Hayasirsa's working English and Hindi (1,453 passages), and the Karanagama's (755) | Releases two texts; saves Google's cap ($17.55 left) for vision and the claims | $28 |
| 3 | The Nirukta witness's Hindi (648), then its release | It waits on its Hindi alone | $4 |
| 4 | The Nirukta witness's scholarly English (648) | Yaska, in the highest-fidelity open text | $11 |
| 5 | The Markandeya witness's 593 flagged verses judged and remade | The scholarly English there has a known gap | $10 |
| 6 | The Ganita Yukti Bhasa's scholarly English | Open since 22 Oct (ganita-scholarly) | $42 |
| 7 | The Gandharva Veda: GRETIL's Natyasastra (4,423) as its text, with English and Hindi; the Tesseract text on the site gives way when it is adopted | The site's Gandharva is OCR with no English | $57 |
| | In all | | about $155, about $45 kept back |

**The rules kept:**

- MT_ENGINE stays gemini; Claude is named per run (`--engine`, or SA_STORY_WRITER).
- The Professor and the claims stay with Gemini.
- Nothing runs without its dry run.

## 4. Raychaudhuri and the tribes, since 28 Oct

- **Part II is read and linked:**
  - 215 of its 216 pages, $2.09 for the pages read and $0.11 for the failed attempts. Page 252 (pdf 270) failed twice
    ("the reply is not the JSON asked for").
  - 4,228 claims, 4,158 of them with the quotation found on the page.
  - `--link` run on 9 Nov.
  - The site's claims went from 1,904 to 6,062 at the next index tick.
- **peoples_index.py, run again on 9 Nov:** Raychaudhuri now speaks of 54 of the 289 peoples of the lists, in 757
  claims (39 and 371 with Part I alone).
- **Not done yet:**
  - The Appendix (`--part app`, 4 pages, about $0.04).
  - Page 252 (`--pages 252`).
  - The hypotheses, P4. These need the Professor's room (ASK_ROOM, applied) and its re-asked answer to be judged first.
  - B. C. Law, for whom a copy held lawfully is yours to give.

## 5. Local and cloud

- **The mirror:** 374 groups equal, 0 different, at every tick from 28 Oct to 9 Nov.
- **One tick failed, on 8 Nov at 10:31:** the PC's network did not resolve the site's name. The next tick, at
  12:31, sent everything.
- **One tick ran 8 hours (22:50 to 07:15).** It waited 501 minutes for its first answer, as a PC asleep would. It sent
  nothing wrong: everything was equal when it ended.
- **The rights checks of 28 Oct, read on 9 Nov:**
  - N1: the editions' noise withheld (38, 9, 5, 44; the Hayasirsa held at 61).
  - N2: the Karanagama's own matter withheld (993 and 5, no words).
  - N3: no Hindi of that matter live.
  - N4: the Gandharva Veda live, with no English.

## 6. Measuring again

After Publish, the same measurement from the cloud (Claude runs it: Playwright, a cold and a warm load of each page).
On the PC, Chrome's DevTools give the same figure without installing anything:

1. Open the Network tab and tick "Disable cache".
2. Load https://srangam.nartiang.org/.
3. Read "transferred" at the bottom.
4. Filter on "rest/v1": the articles read should be a few KB (srangam_article_cards), not 2.3 MB (srangam_articles).
