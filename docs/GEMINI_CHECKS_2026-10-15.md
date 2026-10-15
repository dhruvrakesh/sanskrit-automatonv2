# Gemini checks a Claude English; the re-judge (REJUDGE_2026_10_15)

Markers:
- **REJUDGE_2026_10_15:** `scripts/scholar_translate.py`, patched by `scripts/patch_rejudge_2026_10_15.py`.
- **DOCS61_2026_10_15:** `scripts/patch_docs61_2026_10_15.py`.

It follows CLAUDE_FIRST_2026_10_15 (docs/CLAUDE_FIRST_2026-10-15.md), released in 4cdbb95.

## 1. The decision (15 Oct, about 18:55 IST, Dhruv)

"Gemini being used to check makes sense." So the standing configuration of a Claude run of the scholarly English is:

| Role | Engine | Paid from |
|---|---|---|
| The translator and its critic | claude-sonnet-5-5 | the Claude credit |
| The judge of every verse (judge-v1), and of the working English where there is one | gemini-2.5-flash, the default `--judge-engine` | Google's bill, in the spend cap |
| The audit (1 in 10) and the second judge (1 in 10, where there is working English) | claude-opus-5-5, `--compare-engine` | the Claude credit |

**Why:** a reading from another family on every verse.
- On the Kāraṇāgama's canary, 28.4 was flagged by the Gemini judge (fidelity 2), and the Gemini audit found a major
  misreading that Claude's critic had accepted.
- The flash judge costs about $0.0002 a call, so some ₹80 for the rest of both texts.
- Google's spend cap gates these runs again: a run stops when it is reached ("STOPPED: the spend cap is reached").

## 2. The Claude-only windows (18:47 to the switch)

**What ran:**
- The three windows of the Hayaśīrṣa ran with `--judge-engine anthropic:claude-haiku-5-5 --compare-engine
  anthropic:claude-opus-5-5`, from 18:47 IST.
- They were not stuck. Each window's first sentence took about 2 to 3 minutes (the page's sentence grouping, the
  draft, the critic, the judge).
- By 18:58 IST (13:28 UTC) they had made 82 verses: 65 passed, 17 flagged, none failed. That came to $2.80, $0.034 a
  verse, with 7 audits by Opus.

**What happens to those verses:** their judge was Haiku's, and the re-judge (section 3) gives them the Gemini
reading.

## 3. REJUDGE_2026_10_15 (CF2)

`scholar_translate.py --doc ... --engine anthropic:claude-sonnet-5-5 --rejudge`:

**What it reads again.** The latest row of each verse of that engine, when:
- its judge was a Claude model;
- the Sanskrit is unchanged;
- no person has reviewed it (a person's reading stands);
- it falls within `--pages`.

A sentence is read whole, as it was made (its group's English).

**How it reads.** `--judge-engine` (gemini-2.5-flash) reads it again, and the working English where there is one.
Its status is decided as a run decides it:
- the last critique stands, the audit included;
- the judge's scores are applied;
- a major error found by the second judge flags it.

**What it stores.** A new version of each verse:
- the same English, notes, critique and comparison as before;
- the new scores, `judge_engine` and status;
- the reason says what it was: `[re-judged; was anthropic:claude-haiku-5-5 4/4, passed] ...`.

Nothing is overwritten.

**What it leaves alone:**
- a verse redone meanwhile (a newer row of that engine, for example from a window still running);
- a verse whose judge does not answer: its row stays as it was.

**Cost and gates:**
- Google's spend cap gates it.
- The dry run (no `--yes`) counts and prices it, free: about $0.0004 a sentence.
- `--limit` caps the sentences (24 by default).

**Tests:**
- `tests/test_rejudge_2026_10_15.py` (7).
- `test_claude_first_2026_10_15`: its replay chain ends at the .bak_rejudge_ copy.
- The sandbox suite: 660 passed; the 36 failures are the same environment ones as before.

## 4. After the credit (from 11 Nov)

**The translator:** gemini-2.5-pro, the default `--engine`, as before CLAUDE_ENGINE. The checks then go back to their
defaults (gemini-2.5-flash, gemini-2.5-pro).

**Rows judged by Claude later:** if any Claude run is judged by Claude after this (a benchmark, say), `--rejudge` reads
those rows again.
