#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
translation_desk.py  (2026-10-17)  TRANSLATION_DESK_2026_10_17

The translation desk's rules, in one place, read by the dashboard (/desk, /desk/<doc>, the guard on its translate
buttons) and by the tests. Nothing here calls a model or writes anything.

Asked on 17 Oct: "translation via this frontend does not offer path to scholarly translation and our new honed
method. why cant i make/use my ui/ux for translation better and retaining a separate frontend for well translated
texts or on path to it." What was so (16 Oct):
  - the dashboard's Translate and Start buttons ran one thing only, the working English in one pass
    (translate_passages.py, gemini-2.5-flash by default), on any text, whatever its path said: on 16 Oct the Padma
    Purana's Patala Khanda was started on its Tesseract reading, which the path (text_path.py, 14 Oct) says to repair
    first (vision has read none of its 364 pages);
  - the scholarly English (scholar_translate.py) ran from PowerShell only; the dashboard showed it (the Library, the
    reader, /scholar) but could not start, plan or price it;
  - the path of every text (/path), the register (withdrawn, set aside, in repair), the scholarly English and the
    benchmarks were each on a page of their own.

What this gives the dashboard:
  - a stage for every text, from the path, the register and the scholarly English: the source first, ready to
    translate, translated (to judge or translate again), the scholarly edition, done;
  - the guard: a working translation of a text whose path says the reading comes first is held, with the path's own
    reason and next step; the person may go on (force), the button asks;
  - the scholarly English's steps, with the standard flags of 15 Oct that BM1 and BM3 measured.

The stages, in the desk's order:
  edition   the scholarly English is begun (scholar_translations has current verses of it)
  ready     a clean reading not yet translated (the path: translate, and its next step is the translation)
  judged    translated: a sample to judge, or to translate again (the path: judge, retranslate)
  done      the path says done
  source    the reading comes first (the path: repair, use the repair, ingest, find a source, retire; a translate
            path whose first step is not the translation, such as a re-ingest of changed pages; or the register
            holds it withdrawn or set aside)
  uncharted the path has not charted it (chart the path again: python scripts\\text_path.py, free)
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

MARK = "TRANSLATION_DESK_2026_10_17"

# The scholarly English as the 15 Oct runs made it, and as BM1 and BM3 measured it (bench_mitra.SCHOLAR_FLAGS): Claude
# Sonnet 5.5 drafts and criticises, Claude Opus 5.5 audits one sentence in ten, judge-v1 (gemini-2.5-flash) reads
# every sentence, no second judge.
SCHOLAR_SOP = ("--engine", "anthropic:claude-sonnet-5-5", "--compare-engine", "anthropic:claude-opus-5-5",
               "--audit-every", "10", "--no-compare")
SCHOLAR_ENGINE = "anthropic:claude-sonnet-5-5"
STEP_VERSES = 40          # a plan's verses by default
MAX_VERSES = 400          # the most verses a press plans or runs
MAX_USD = 12.0            # the most one press may spend (as the benchmarks' buttons)
SOURCE_FIRST = ("repair", "use_repair", "ingest", "source", "retire")
HOLDS = ("withdrawn", "set_aside")
STALE_DAYS = 3
PAGES_RE = re.compile(r"^\d{1,4}(-\d{1,4})?(,\d{1,4}(-\d{1,4})?)*$")
CAP_RE = re.compile(r"--max-usd ([0-9]+(?:\.[0-9]+)?)")
STAGES = (("edition", "The scholarly edition"), ("ready", "Ready to translate"), ("judged", "Translated: to judge"),
          ("done", "Done"), ("source", "The reading first"), ("uncharted", "Not charted"))
PATH_LABEL = {"use_repair": "use the repair", "retire": "retire", "ingest": "ingest", "repair": "repair the scan",
              "source": "find a source", "translate": "translate", "retranslate": "translate again",
              "judge": "judge a sample", "in_repair": "in repair", "done": "done"}


_LOADED = {}   # str(path) -> ((path, mtime_ns, size), the chart): read again only when the file changes


def load_path(p) -> dict:
    """{"at": the chart's time, "texts": {doc: its row}} of data/text_path.json; empty when it cannot be read. Kept
    while the file's time and size are the same (the main dashboard asks on every status poll); read it, never change
    it."""
    try:
        pp = Path(p)
        st = pp.stat()
        key = (str(pp), st.st_mtime_ns, st.st_size)
        hit = _LOADED.get(key[0])
        if hit is not None and hit[0] == key:
            return hit[1]
        d = json.loads(pp.read_text(encoding="utf-8"))
        res = {"at": str(d.get("at") or ""), "texts": {r["doc"]: r for r in d.get("texts") or [] if r.get("doc")}}
        _LOADED[key[0]] = (key, res)
        return res
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {"at": "", "texts": {}}


def chart_age_days(at: str, now: float = None):
    """Days since the chart was made; None when it cannot be read."""
    try:
        t = time.mktime(time.strptime(at[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None
    return max(0.0, ((now if now is not None else time.time()) - t) / 86400.0)


def _first(prow: dict) -> str:
    nx = prow.get("next") or []
    return str(nx[0]) if nx else ""


def translation_first(prow: dict) -> bool:
    """The path's first step is a translation (its NEXT begins with "translate")."""
    return _first(prow).strip().lower().startswith("translate")


def guard(prow, reg=None, chart_at: str = "", now: float = None):
    """Why a working translation of this text is held now, or None. prow: its row in the path chart (None when
    uncharted: not held, the chart has nothing to say); reg: its register record."""
    reg = reg or {}
    if reg.get("status") in HOLDS:
        return None   # translate_passages.py holds it itself (HOLD_2026_10_14), with its own message
    if not prow:
        return None
    path = prow.get("path") or ""
    if path in SOURCE_FIRST or (path in ("translate", "in_repair") and not translation_first(prow)):
        age = chart_age_days(chart_at, now)
        when = (" (the chart of %s%s)" % (chart_at[:10], ", %d days old: chart it again, free" % age
                                         if age is not None and age >= STALE_DAYS else "")) if chart_at else ""
        say = ("Its path says the reading comes first: %s. %s Next: %s%s. Translating it now makes the English from a "
               "reading that is to be replaced." % (PATH_LABEL.get(path, path), str(prow.get("why") or "").rstrip("."),
                                                   _first(prow) or "-", when))
        return {"path": path, "label": PATH_LABEL.get(path, path), "why": str(prow.get("why") or ""),
                "next": _first(prow), "at": chart_at, "say": say, "mark": MARK}
    return None


def stage_of(prow, cover=None, reg=None) -> str:
    """The text's stage (STAGES)."""
    cover = cover or {}
    reg = reg or {}
    if int(cover.get("verses") or 0) > 0:
        return "edition"
    if reg.get("status") in HOLDS:
        return "source"
    if not prow:
        return "uncharted"
    path = prow.get("path") or ""
    if path in SOURCE_FIRST:
        return "source"
    if path in ("translate", "in_repair"):
        return "ready" if translation_first(prow) else "source"
    if path in ("judge", "retranslate"):
        return "judged"
    if path == "done":
        return "done"
    return "uncharted"


def next_step(stage: str, prow=None, cover=None, mula: int = 0) -> str:
    """The desk's one next step for a text, in words."""
    prow = prow or {}
    cover = cover or {}
    if stage == "edition":
        left = max(0, int(mula or 0) - int(cover.get("verses") or 0))
        fl = int(cover.get("flagged") or 0) + int(cover.get("source_doubt") or 0)
        if left:
            return "the scholarly English: plan the next %d verses (free), then run them" % min(STEP_VERSES, left)
        if fl:
            return "read the %d flagged and doubted verses (triage, free)" % fl
        return "the scholarly English is made: a person reads it; then the site's layer (S4)"
    if stage == "ready":
        return ("the working English and its Hindi (one pass), about $%.2f by the path; or begin its scholarly English"
                % float(prow.get("cost") or 0))
    if stage in ("judged", "source", "done"):
        return _first(prow) or ("nothing to do" if stage == "done" else "-")
    return "chart the path again (free): python scripts\\text_path.py"


def scholar_argv(doc: str, step: str, pages: str = "", limit: int = STEP_VERSES, max_usd: float = 0.0,
                 held_ok: bool = False):
    """The arguments of scholar_translate.py for a step of the desk: plan (the dry run), run (paid, --yes --max-usd),
    report, triage, status (free). (argv, None) or (None, why)."""
    if step in ("report", "triage", "status"):
        return ["--doc", doc, "--" + step] + (list(SCHOLAR_SOP[:2]) if step == "triage" else []), None
    if step not in ("plan", "run"):
        return None, "unknown step %r (plan, run, report, triage, status)" % step
    pages = str(pages or "").strip()
    if pages and not PAGES_RE.match(pages):
        return None, "pages: a page, a range or a list (2, or 1-3,5)"
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return None, "verses: a whole number"
    if not 1 <= limit <= MAX_VERSES:
        return None, "verses: 1 to %d a press" % MAX_VERSES
    argv = ["--doc", doc, "--limit", str(limit)] + (["--pages", pages] if pages else []) + list(SCHOLAR_SOP)
    if held_ok:
        argv.append("--held-ok")
    if step == "run":
        try:
            usd = float(max_usd)
        except (TypeError, ValueError):
            return None, "max_usd: a number"
        if not 0 < usd <= MAX_USD:
            return None, ("$%.2f is outside what one press may spend (up to $%.2f): plan fewer verses, or run it by hand"
                          % (usd, MAX_USD))
        argv += ["--yes", "--max-usd", "%.2f" % usd]
    return argv, None


def cap_of(out: str):
    """The cap a dry run's NEXT line proposes (--max-usd), or None."""
    for line in reversed(str(out or "").splitlines()):
        if line.startswith("NEXT: "):
            m = CAP_RE.search(line)
            return float(m.group(1)) if m else None
    return None
