#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_path_2026_10_12.py  (2026-10-12)  PATH_2026_10_12

Asked on 12 Oct: "each text should either be fixable, retirable, or search for critical editions, better quality
scans or Sanskrit text to find the truth." scripts/text_path.py (new, read-only) charts one way forward for every
text. This patch wires it in and mends what the morning's runs showed:
  ocr_consensus.py: the Natyasastra's repair read no page. Its queue began with five pages vision had failed on the
    night before; they failed again and "5 consecutive vision failures" stopped the run, after billed retries. A
    failed page is now written down (data/ocr_consensus/<doc>_vision_failed.json): it is tried after the others,
    its failures do not stop a run, and after 2 failed runs it is left to Tesseract (--retry-refused tries it
    again); a page below the last page vision read with no reading failed before the ledger existed, and is
    written down once. The spend cap is asked before each page, and after a failure (ocr_vision.py exits 0 with nothing
    when the cap refuses it), so a cap reached stops the run as such and marks no page.
  repair_text.py: the repair's NEXT said --max-usd 1.00 under an estimate of $3.08; it now gives a cap the estimate
    fits under. --withdraw REASON (a new state, "withdrawn"): a damaged text is taken off the site and out of Ask
    the Corpus, and kept here, until a better source replaces it; --restore undoes it.
  corpus_sync.py: a withdrawn text is not live: a full run retires its rows on the site, as for a retired text
    (the guard on many texts gone at once holds); restored, the next run sends it back.
  dashboard.py (on a restart): /path, the path of every text (data/text_path.json) with "Chart the path again";
    "Withdraw it from the site" where the repair page advises it; withdrawn texts are left out of Ask the Corpus
    (words and meaning); links to /path from the Library, /sources and /benchmarks.
  .gitignore: data/text_path.json stays local.

Needs QUALITY_2026_10_11 (ocr_consensus.py), REINGEST_2026_10_12 (repair_text.py, dashboard.py),
ETEXT_WITNESS_2026_10_11 (corpus_sync.py) and scripts/text_path.py. Anchored, all-or-nothing, marker-idempotent per
file; keeps line endings and encodings; each .py is compiled before it replaces the original; backups
.bak_path_<date>.
  python scripts\\patch_path_2026_10_12.py --check
  python scripts\\patch_path_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "PATH_2026_10_12"
NEEDS = {"scripts/ocr_consensus.py": "QUALITY_2026_10_11", "scripts/repair_text.py": "REINGEST_2026_10_12",
         "scripts/corpus_sync.py": "ETEXT_WITNESS_2026_10_11", "scripts/dashboard.py": "REINGEST_2026_10_12"}
FILES = list(NEEDS)
GITIGNORE_BLOCK = ("# PATH_2026_10_12: the path of every text (scripts/text_path.py) is charted here, and stays local\n"
                   "data/text_path.json\n")

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/ocr_consensus.py', 1,
     r'''        (done if ok else todo).append(q)
    return todo, done


''',
     r'''        (done if ok else todo).append(q)
    return todo, done


# PATH_2026_10_12: the pages vision failed on. On 12 Oct the Natyasastra's repair (278 pages to read, $3.08) read
# none: its queue began with five pages vision had failed on the night before (0026, 0032, 0038, 0040, 0044), they
# failed again, and five failures in a row stopped the run as "quota or key?" - after about half an hour of billed
# retries. A page vision fails on is now written down (data/ocr_consensus/<doc>_vision_failed.json); it is tried
# after the others, its failures do not stop a run, and after VISION_GIVE_UP failed runs it is left to Tesseract
# (--retry-refused tries it again). The spend cap is asked before each page: a cap reached stops the run as such.
# The ledger is new: a page below the last page vision read that has no reading failed before (the runs go in page
# order), and is written down once on the first run, so the Natyasastra's 24 such pages (below page 292) go last.
VISION_GIVE_UP = 2


def failed_ledger(work: Path, doc: str) -> Path:
    return work / ("%s_vision_failed.json" % doc)


def read_failed(work: Path, doc: str) -> dict:
    try:
        d = json.loads(failed_ledger(work, doc).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def write_failed(work: Path, doc: str, led: dict) -> None:
    p = failed_ledger(work, doc)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(led, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def last_read_page(vdir: Path, doc: str) -> int:
    """The highest page vision has read for this text (0 when none)."""
    rx = re.compile(r"^%s_(\d{4})\.jsonl$" % re.escape(doc))
    pages = []
    try:
        for e in os.scandir(vdir):
            m = rx.match(e.name)
            if m:
                pages.append(int(m.group(1)))
    except OSError:
        return 0
    for pg in sorted(pages, reverse=True):
        if nonempty_jsonl(vdir / ("%s_%04d.jsonl" % (doc, pg))):
            return pg
    return 0


def seed_failed(todo: list, led: dict, last_read: int) -> int:
    """A page to read below the last page vision read, and not in the ledger, was tried before and failed: it is
    written down once (fails 1), so it goes after the others. -> how many were written down."""
    n = 0
    for q in todo:
        stem = Path(q.replace("\\", "/")).stem
        tail = stem[-4:]
        if stem not in led and tail.isdigit() and int(tail) < last_read:
            led[stem] = {"fails": 1, "last": "", "inferred": "no reading below page %d" % last_read}
            n += 1
    return n


def order_vision(todo: list, led: dict, retry: bool = False):
    """(the pages to read: never failed first, then those that failed before; the pages left to Tesseract)."""
    fresh, again, skipped = [], [], []
    for q in todo:
        n = int((led.get(Path(q.replace("\\", "/")).stem) or {}).get("fails") or 0)
        if n >= VISION_GIVE_UP and not retry:
            skipped.append(q)
        else:
            (again if n else fresh).append(q)
    return fresh + again, skipped


def run_vision(todo: list, vdir: Path, doc: str, led: dict, model=None, budget=None, runner=None):
    """Vision on each page -> (read, failed, why it stopped or ""). A failed page goes into led; only pages
    that never failed before count towards the five failures in a row that stop the run. The cap (budget) is
    asked before each page, and after a failure: ocr_vision.py exits 0 with nothing when the cap refuses it."""
    runner = runner or run
    ok = fails = consec = 0
    stopped = ""
    for i, pdf in enumerate(todo, 1):
        stem = Path(pdf.replace("\\", "/")).stem
        if budget is not None and not budget():
            stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
            break
        before = int((led.get(stem) or {}).get("fails") or 0)
        out = vdir / (stem + ".jsonl")
        argv = [PY, str(SCRIPTS / "ocr_vision.py"), "--pdf", pdf, "--out", str(out), "--doc", doc, "--yes"] + (
            ["--model", model] if model else [])
        print("  (%d/%d)%s" % (i, len(todo), ("  (vision failed on it %d time(s) before)" % before) if before else ""))
        if runner(argv) != 0 or not nonempty_jsonl(out):
            if budget is not None and not budget():   # ocr_vision.py refused it for the cap: not the page's fault
                stopped = "the spend cap is reached (python scripts\\set_budget.py shows it)"
                break
            fails += 1
            led[stem] = {"fails": before + 1, "last": datetime.datetime.now().isoformat(timespec="seconds")}
            if not before:
                consec += 1
                if consec >= 5:
                    stopped = "5 vision failures in a row on pages never failed before (quota or key?)"
                    break
        else:
            ok += 1
            consec = 0
            led.pop(stem, None)
    return ok, fails, stopped


''')
edit('scripts/ocr_consensus.py', 2,
     r'''        # 2. VISION (metered, skip-existing)
        todo, done = plan_vision(queue, vdir, args.retry_refused)
        n_ref = sum(1 for q in done if refused(vdir / (Path(q.replace("\\", "/")).stem + ".jsonl")))
        if n_ref:
''',
     r'''        # 2. VISION (metered, skip-existing)
        todo, done = plan_vision(queue, vdir, args.retry_refused)
        led = read_failed(work, doc)   # PATH_2026_10_12
        seeded = seed_failed(todo, led, last_read_page(vdir, doc))
        if seeded:
            print("  %d page(s) below the last page vision read have no reading: vision failed on them before, so they "
                  "go after the others" % seeded)
        todo, gave = order_vision(todo, led, args.retry_refused)
        if gave:
            print("  %d page(s) left to Tesseract: vision failed on them in %d runs or more (%s). --retry-refused to "
                  "try again." % (len(gave), VISION_GIVE_UP, ", ".join(Path(x.replace("\\", "/")).stem[-4:] for x in gave[:12])))
        n_ref = sum(1 for q in done if refused(vdir / (Path(q.replace("\\", "/")).stem + ".jsonl")))
        if n_ref:
''')
edit('scripts/ocr_consensus.py', 3,
     r'''                return 1
            vdir.mkdir(parents=True, exist_ok=True)
            fails = consec = 0
            for i, pdf in enumerate(todo, 1):
                stem = Path(pdf.replace("\\", "/")).stem
                argv = [PY, str(SCRIPTS / "ocr_vision.py"), "--pdf", pdf, "--out", str(vdir / (stem + ".jsonl")),
                        "--doc", doc, "--yes"] + (["--model", args.model] if args.model else [])
                print("  (%d/%d)" % (i, len(todo)))
                if run(argv) != 0 or not nonempty_jsonl(vdir / (stem + ".jsonl")):
                    fails += 1; consec += 1
                    if consec >= 5:
                        print("  STOPPING: 5 consecutive vision failures (quota or key?). Re-run later; done pages are kept.")
                        break
                else:
                    consec = 0
            print("  vision failures: %d" % fails)
        # 3. AUDIT / REPAIR (lossless) with one redo round
        vis = page_map(vdir, doc, "jsonl")
''',
     r'''                return 1
            vdir.mkdir(parents=True, exist_ok=True)
            try:   # PATH_2026_10_12: the cap is asked before each page
                import usage_meter as _um
                _budget = lambda: _um.budget_ok(args.db)
            except Exception:
                _budget = None
            try:
                n_ok, fails, stopped = run_vision(todo, vdir, doc, led, args.model, _budget)
            finally:
                write_failed(work, doc, led)
            if stopped:
                print("  STOPPING: %s. Re-run later; done pages are kept." % stopped)
            print("  vision: %d page(s) read, %d failed%s" % (n_ok, fails, (" (written down in %s: tried last next "
                  "time, left to Tesseract after %d failed runs)" % (failed_ledger(work, doc), VISION_GIVE_UP)) if fails else ""))
        # 3. AUDIT / REPAIR (lossless) with one redo round
        vis = page_map(vdir, doc, "jsonl")
''')
edit('scripts/repair_text.py', 4,
     r'''COST_PER_PAGE = 0.0004          # measured on Karan Aagama, 2026-10-10 ($0.00017-0.00038 a page)
DASHBOARD = os.environ.get("SA_DASHBOARD_URL") or "http://127.0.0.1:5057"
STATES = ("set_aside", "translate_as_is", "complete", "in_repair")    # the rest ("restored", "released") are ordinary

JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")      # = translate_passages._debris_guard
''',
     r'''COST_PER_PAGE = 0.0004          # measured on Karan Aagama, 2026-10-10 ($0.00017-0.00038 a page)
DASHBOARD = os.environ.get("SA_DASHBOARD_URL") or "http://127.0.0.1:5057"
STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "withdrawn")   # the rest ("restored", "released") are ordinary; withdrawn: PATH_2026_10_12

JUNK = re.compile(r"(?<![A-Za-z])[A-Za-z][A-Za-z'!\"]{1,}")      # = translate_passages._debris_guard
''')
edit('scripts/repair_text.py', 5,
     r'''        return ("set aside on %s: %s. A better scan is wanted; its files are kept." % (s_at, s_why),
                q + " --restore   (when a better scan is in the inbox)", [q + " --find-source"])
    if status == "complete":
        return ("accepted as complete on %s: %s. %d of %d passages have English; what is left is not translated."
''',
     r'''        return ("set aside on %s: %s. A better scan is wanted; its files are kept." % (s_at, s_why),
                q + " --restore   (when a better scan is in the inbox)", [q + " --find-source"])
    if status == "withdrawn":   # PATH_2026_10_12
        return ("withdrawn from the site on %s: %s. The site has retired its passages; they are kept here, out of Ask the "
                "Corpus, until a better source replaces them" % (s_at, s_why), q + " --find-source",
                [q + " --restore   (send it to the site again as it is)"])
    if status == "complete":
        return ("accepted as complete on %s: %s. %d of %d passages have English; what is left is not translated."
''')
edit('scripts/repair_text.py', 6,
     r'''        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
                q + " --repair   (capped at --max-usd 1.00)", also)
    if r["queued"] and r["vision_pages"] < 0.8 * r["queued"]:
        return (why + "; vision read only %d of the %d queued pages: the scan resists repair" % (r["vision_pages"], r["queued"]),
''',
     r'''        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        cap = max(1.0, math.ceil(left * cpp * 1.25 * 10) / 10.0)   # PATH_2026_10_12: a cap the estimate fits under
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
                q + " --repair --max-usd %.2f   (it stops before spending more)" % cap, also)
    if r["queued"] and r["vision_pages"] < 0.8 * r["queued"]:
        return (why + "; vision read only %d of the %d queued pages: the scan resists repair" % (r["vision_pages"], r["queued"]),
''')
edit('scripts/repair_text.py', 7,
     r'''        "set_aside": ("%s set aside: %s. Its files are kept; the Library stops offering its translation." % (doc, rec["reason"]),
                      "put a better scan's page PDFs in the inbox (OCR them), then %s --restore" % q),
        "translate_as_is": ("%s is to be translated as is: %s. The debris guard lets it through." % (doc, rec["reason"]),
                            "translate it: Finish EN and Add Hindi in the Library"),
''',
     r'''        "set_aside": ("%s set aside: %s. Its files are kept; the Library stops offering its translation." % (doc, rec["reason"]),
                      "put a better scan's page PDFs in the inbox (OCR them), then %s --restore" % q),
        "withdrawn": ("%s withdrawn from the site: %s. At the next mirror run the site retires its passages, English and "
                      "Hindi (--restore brings them back); they are kept here, and Ask the Corpus here leaves them out."
                      % (doc, rec["reason"]), "%s --find-source   (a critical e-text or a better scan)" % q),   # PATH_2026_10_12
        "translate_as_is": ("%s is to be translated as is: %s. The debris guard lets it through." % (doc, rec["reason"]),
                            "translate it: Finish EN and Add Hindi in the Library"),
''')
edit('scripts/repair_text.py', 8,
     r'''                   help="the site keeps its last version of this text (corpus_sync.py skips it)")
    g.add_argument("--release", action="store_true", help="publish the text to the site again")
    g.add_argument("--find-source", action="store_true", help="look for a better edition (scripts/source_desk.py)")
    g.add_argument("--restore", action="store_true")
''',
     r'''                   help="the site keeps its last version of this text (corpus_sync.py skips it)")
    g.add_argument("--release", action="store_true", help="publish the text to the site again")
    g.add_argument("--withdraw", metavar="REASON", help="PATH_2026_10_12: take the text off the site (the mirror retires "
                   "it there) and out of Ask the Corpus, keeping it here; --restore undoes it")
    g.add_argument("--find-source", action="store_true", help="look for a better edition (scripts/source_desk.py)")
    g.add_argument("--restore", action="store_true")
''')
edit('scripts/repair_text.py', 9,
     r'''        print("FAIL: --doc <code> is needed (letters, digits, _ and -)."); return 2
    for flag, status in (("set_aside", "set_aside"), ("as_is", "translate_as_is"), ("accept", "complete"),
                         ("hold", "in_repair")):
        reason = getattr(a, flag)
        if reason is not None:
''',
     r'''        print("FAIL: --doc <code> is needed (letters, digits, _ and -)."); return 2
    for flag, status in (("set_aside", "set_aside"), ("as_is", "translate_as_is"), ("accept", "complete"),
                         ("hold", "in_repair"), ("withdraw", "withdrawn")):   # PATH_2026_10_12: withdraw
        reason = getattr(a, flag)
        if reason is not None:
''')
edit('scripts/corpus_sync.py', 10,
     r'''

def live_docs(con, include_retired: bool = False):
    """[(id, code, category, src_path, glossary, created_at)] of documents to mirror."""
''',
     r'''

def _withdrawn_docs() -> set:
    """PATH_2026_10_12: the texts withdrawn from the site (repair_text.py --withdraw): the latest record of their code in
    data/source_verdicts.jsonl is "withdrawn". They are not live here, so a full run retires their rows on the site, as
    for a retired text (and the guard on many texts gone at once holds); --restore makes them live again, and the
    next run sends them back. SA_SOURCE_VERDICTS names another file (the tests)."""
    p = Path(os.environ.get("SA_SOURCE_VERDICTS") or (ROOT / "data" / "source_verdicts.jsonl"))
    last = {}
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("doc"):
                    last[r["doc"]] = r.get("status")
    except OSError:
        return set()
    return {d for d, s in last.items() if s == "withdrawn"}


def live_docs(con, include_retired: bool = False):
    """[(id, code, category, src_path, glossary, created_at)] of documents to mirror."""
''')
edit('scripts/corpus_sync.py', 11,
     r'''    out = []
    witness = _witness_docs()   # ETEXT_WITNESS_2026_10_11: local until adopted
    for r in rows:
        code = r[1]
''',
     r'''    out = []
    witness = _witness_docs()   # ETEXT_WITNESS_2026_10_11: local until adopted
    withdrawn = _withdrawn_docs()   # PATH_2026_10_12: off the site until restored
    for r in rows:
        code = r[1]
''')
edit('scripts/corpus_sync.py', 12,
     r'''        if not include_retired and (code.endswith("-RETIRED") or code in retired):
            continue
        if code in witness:
            continue
        out.append(r)
''',
     r'''        if not include_retired and (code.endswith("-RETIRED") or code in retired):
            continue
        if code in witness or code in withdrawn:
            continue
        out.append(r)
''')
edit('scripts/dashboard.py', 13,
     r'''                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest")               # REINGEST_2026_10_12: only the pages that changed
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness")   # ETEXT_WITNESS_2026_10_11: witness
SOURCES_DIR = ROOT / "sources"                       # ETEXT_WITNESS_2026_10_11: what source_desk.py and etext_witness.py fetch
WITNESS_DIR = ROOT / "data" / "raw_witness"          # the witnesses' pages, witness.json and align.json
''',
     r'''                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest",               # REINGEST_2026_10_12: only the pages that changed
                 "withdraw", "path_all")                    # PATH_2026_10_12: off the site; the path of every text
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness",   # ETEXT_WITNESS_2026_10_11: witness
                  "withdrawn")                                                          # PATH_2026_10_12
SOURCES_DIR = ROOT / "sources"                       # ETEXT_WITNESS_2026_10_11: what source_desk.py and etext_witness.py fetch
WITNESS_DIR = ROOT / "data" / "raw_witness"          # the witnesses' pages, witness.json and align.json
''')
edit('scripts/dashboard.py', 14,
     r'''                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...',
                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...'};   /* REINGEST_2026_10_12 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''',
     r'''                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...',
                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...',   /* REINGEST_2026_10_12 */
                 withdraw: 'withdrawing it from the site...', path_all: 'charting the path of every text (a few minutes)...'};   /* PATH_2026_10_12 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''')
edit('scripts/dashboard.py', 15,
     r'''  if (n.indexOf('--accept') >= 0) return {step: 'accept', reason: _rpQuoted(n), label: 'Accept as complete'};
  if (n.indexOf('--set-aside') >= 0) return {step: 'set_aside', label: 'Set aside: a better scan is wanted'};
  if (n.indexOf('--restore') >= 0) return {step: 'restore', label: 'Restore'};
  if (n.indexOf('--release') >= 0) return {step: 'release', label: 'Publish it to the site'};
''',
     r'''  if (n.indexOf('--accept') >= 0) return {step: 'accept', reason: _rpQuoted(n), label: 'Accept as complete'};
  if (n.indexOf('--set-aside') >= 0) return {step: 'set_aside', label: 'Set aside: a better scan is wanted'};
  if (n.indexOf('--withdraw') >= 0) return {step: 'withdraw', reason: _rpQuoted(n), label: 'Withdraw it from the site'};   /* PATH_2026_10_12 */
  if (n.indexOf('--restore') >= 0) return {step: 'restore', label: 'Restore'};
  if (n.indexOf('--release') >= 0) return {step: 'release', label: 'Publish it to the site'};
''')
edit('scripts/dashboard.py', 16,
     r'''    }
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold'){
    var ask = {set_aside: 'Set ' + doc + ' aside: why? Its files are kept; the Library stops offering its translation until '
                          + 'it is restored.',
               as_is: 'Translate ' + doc + ' as is: the debris guard will let it through. Why?',
               accept: 'Accept ' + doc + ' as complete: what is left is not to be translated. Why?',
               hold: 'Hold ' + doc + ' from the site: the site keeps its last version until you publish. Why?'}[step];
    var dflt = opt.reason || {set_aside: 'needs a better scan', as_is: 'debris judged cosmetic',
                              accept: 'what is left is not Sanskrit', hold: 're-translating after the repair'}[step];
    var why = prompt(ask, dflt);
    if (why === null) return;
''',
     r'''    }
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold' || step === 'withdraw'){   /* PATH_2026_10_12: withdraw */
    var ask = {set_aside: 'Set ' + doc + ' aside: why? Its files are kept; the Library stops offering its translation until '
                          + 'it is restored.',
               as_is: 'Translate ' + doc + ' as is: the debris guard will let it through. Why?',
               accept: 'Accept ' + doc + ' as complete: what is left is not to be translated. Why?',
               hold: 'Hold ' + doc + ' from the site: the site keeps its last version until you publish. Why?',
               withdraw: 'Withdraw ' + doc + ' from the site: at the next mirror run the site retires its passages, English '
                         + 'and Hindi (Restore brings them back); they are kept here, out of Ask the Corpus. Why?'}[step];
    var dflt = opt.reason || {set_aside: 'needs a better scan', as_is: 'debris judged cosmetic',
                              accept: 'what is left is not Sanskrit', hold: 're-translating after the repair',
                              withdraw: 'its text is damaged: a better source is wanted'}[step];
    var why = prompt(ask, dflt);
    if (why === null) return;
''')
edit('scripts/dashboard.py', 17,
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|as_is|accept|hold|release|translate|judge_all|benchmark_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''',
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|withdraw|as_is|accept|hold|release|translate|judge_all|benchmark_all|path_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''')
edit('scripts/dashboard.py', 18,
     r'''                      '%s Hindi) until you publish this one.</div>'
                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))
    for n in shown:
        acts_html += ('<div class="cardnote%s" title="%s">%s</div>'
''',
     r'''                      '%s Hindi) until you publish this one.</div>'
                      % (at, why, rec.get("en_before", "?"), rec.get("hi_before", "?")))
    elif st == "withdrawn":   # PATH_2026_10_12
        acts_html += ('<div class="cardnote aside" title="data/source_verdicts.jsonl">Withdrawn from the site on %s: %s. The '
                      'site has retired its passages; they are kept here, out of Ask the Corpus, until a better source '
                      'replaces them (Restore sends them back).</div>' % (at, why))
    for n in shown:
        acts_html += ('<div class="cardnote%s" title="%s">%s</div>'
''')
edit('scripts/dashboard.py', 19,
     r'''    if st in ("in_repair", "witness"):   # ETEXT_WITNESS_2026_10_11: a witness too
        acts_html += _repair_bar(code, "in_repair")
    elif "repaired" in kinds:
        acts_html += _repair_bar(code, "repaired")
''',
     r'''    if st in ("in_repair", "witness"):   # ETEXT_WITNESS_2026_10_11: a witness too
        acts_html += _repair_bar(code, "in_repair")
    elif st == "withdrawn":   # PATH_2026_10_12: Restore, Find a better source
        acts_html += _repair_bar(code, "aside")
    elif "repaired" in kinds:
        acts_html += _repair_bar(code, "repaired")
''')
edit('scripts/dashboard.py', 20,
     r'''    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step in ("judge_all", "benchmark_all") else _validate_doc(data.get("doc"))   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
''',
     r'''    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "assess")
    doc = "corpus" if step in ("judge_all", "benchmark_all", "path_all") else _validate_doc(data.get("doc"))   # PATH_2026_10_12: path_all   # JUDGE_DESK_2026_10_11; BENCHMARK_2026_10_11
    if not doc:
        return jsonify({"error": "invalid or missing doc"}), 400
''')
edit('scripts/dashboard.py', 21,
     r'''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
''',
     r'''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    elif step == "withdraw":   # PATH_2026_10_12: off the site (the mirror retires it there), out of Ask here
        argv += ["--withdraw", reason or "its text is damaged: a better source is wanted"]
    elif step == "path_all":   # PATH_2026_10_12: free and read-only
        argv = [script("text_path.py"), "--from-dashboard"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
''')
edit('scripts/dashboard.py', 22,
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><h1>Benchmarks</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
''',
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><a href="/path">The path</a><h1>Benchmarks</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
<script>
function _toast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(function(){t.style.display='none';},6000);}
""" + _REPAIR_JS + """
</script>
</body></html>""")


PATH_FILE = ROOT / "data" / "text_path.json"   # PATH_2026_10_12: written by scripts/text_path.py


@app.get("/path")
def path_page():
    """PATH_2026_10_12: the path of every text (scripts/text_path.py): use the repair, retire, ingest, repair the scan,
    find a source, translate, translate again, judge a sample, in repair, done; each with its reason in numbers, its
    next command and its cost. Reads one small file."""
    import html as _html
    e = _html.escape
    try:
        res = json.loads(PATH_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        res = None
    money = lambda x: ("$%.2f" % x) if x >= 0.995 else ("$%.3f" % x)
    chips, groups = "", ""
    if res:
        tot = res.get("totals") or {}
        for key, label, desc in res.get("paths") or []:
            rows = [t for t in res.get("texts") or [] if t.get("path") == key and not t.get("retired")]
            if not rows:
                continue
            tt = tot.get(key) or {}
            hi = tt.get("cost_hi") or 0
            cost = ((" &middot; about %s now" % money(tt["cost"])) if tt.get("cost") else "") + (
                (" (up to %s at the dearest text's price)" % money(hi)) if tt.get("cost") and hi > 1.05 * tt["cost"] else "") + (
                (" &middot; then %s to translate" % money(tt["then"])) if tt.get("then") else "")
            chips += '<a class="pchip" href="#p-%s">%s <b>%d</b></a>' % (e(key, quote=True), e(label), len(rows))
            trs = ""
            for t in rows:
                lines = "".join('<div class="pnext">NEXT %s</div>' % e(n) for n in t.get("next") or [])
                lines += "".join('<div class="palso">ALSO %s</div>' % e(n) for n in t.get("also") or [])
                link = ('<a href="/repair/%s">%s</a>' % (e(t["doc"], quote=True), e(t["doc"]))) if not t.get("new") else e(t["doc"])
                trs += '<tr><td class="pdoc">%s</td><td>%s%s</td><td class="pcost">%s</td></tr>' % (
                    link, e(t.get("why") or ""), lines, (money(t["cost"]) if t.get("cost") else "") + (
                        ("<br><span class=\"muted\">then %s</span>" % money(t["then"])) if t.get("then") else ""))
            groups += ('<h2 id="p-%s" class="ph">%s <span>%d</span></h2><p class="pdesc">%s%s</p><div class="srcwrap">'
                       '<table class="srct"><tbody>%s</tbody></table></div>' % (e(key, quote=True), e(label), len(rows),
                                                                              e(desc), cost, trs))
        pr = res.get("prices") or {}
        head = ('Charted %s: vision %s a page at the corpus price (%d text(s) priced from their own calls; the dearest '
                'so far %s a page), translation %s a passage, measured in usage_log.'
                % (e(str(res.get("at", "?")).replace("T", " ")), "$%.4f" % (pr.get("vision_page") or 0),
                   len(pr.get("measured") or []), "$%.4f" % (pr.get("vision_dear") or 0), "$%.5f" % (pr.get("passage") or 0)))
    else:
        head = "Not charted yet: press Chart the path again, or run python scripts\\text_path.py (free, read-only)."
    body = ('<div class="srcpage"><p class="rpintro" style="margin:0">Every text has one way forward: use the repair '
            'vision has made, retire a duplicate, ingest what is not in yet, repair the scan with vision, find a critical '
            'e-text or a better scan, translate a clean reading, translate again what the judge marks, judge a sample, '
            'or nothing. %s</p><div class="pchips">%s</div><div class="repairbar" id="rp-corpus" style="margin-top:10px">'
            '<button class="tr-rest rp" data-doc="corpus" onclick="repairStep(this.dataset.doc,&#39;path_all&#39;,this)">'
            'Chart the path again (free, read-only; a few minutes)</button><div class="rpout"></div></div>%s</div>'
            % (head, chips, groups))
    css = (".pchips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.pchip{border:1px solid var(--border);"
           "border-radius:7px;padding:4px 10px;font-size:12px;color:var(--cream);text-decoration:none}.pchip b{color:var(--gold)}"
           ".ph{font-size:15px;color:var(--gold);margin:22px 0 2px}.ph span{color:var(--muted);font-weight:400}"
           ".pdesc{color:var(--muted);font-size:12px;margin-bottom:6px}.pdoc{width:28%;word-break:break-all;font-weight:600}"
           ".pdoc a{color:var(--cream)}.pnext,.palso{font-family:ui-monospace,monospace;font-size:11px;margin-top:3px;"
           "word-break:break-all}.pnext{color:#9ec3ff}.palso{color:#d9a35b}.pcost{white-space:nowrap;text-align:right}"
           ".muted{color:var(--muted)}")
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>The path</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0b0a08;--card:#161410;--card2:#1e1b16;--border:#2a271f;--gold:#c9952a;--cream:#ede4cc;--muted:#7a6d58}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--cream);font-family:'Inter',sans-serif;min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:var(--muted);font-size:12px;text-decoration:none}
header a:hover{color:var(--gold)}
header h1{font-size:18px;color:var(--gold);font-weight:700}
.tr-rest{background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:7px;padding:5px 9px;font-family:'Inter',sans-serif;font-size:11.5px;font-weight:600;cursor:pointer}
.tr-rest:hover{border-color:var(--gold);color:var(--gold)}
.tr-rest:disabled{opacity:.6;cursor:default}
.srcnone{color:var(--muted);font-size:12px;margin:10px 0}
""" + _REPAIR_CSS + _SOURCES_CSS + css + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/sources">Sources &amp; repairs</a><a href="/benchmarks">Benchmarks</a><h1>The path</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
''')
edit('scripts/dashboard.py', 23,
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + _JUDGED_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/benchmarks">Benchmarks</a><h1>Sources &amp; repairs</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
''',
     r'''""" + _REPAIR_CSS + _SOURCES_CSS + _JUDGED_CSS + """
</style></head><body>
<header><a href="/library">&larr; Library</a><a href="/">Dashboard</a><a href="/benchmarks">Benchmarks</a><a href="/path">The path</a><h1>Sources &amp; repairs</h1></header>
""" + body + """
<div id="toast" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--card2);border:1px solid var(--gold);color:var(--cream);padding:10px 18px;border-radius:8px;font-size:13px;display:none;z-index:50;max-width:90vw"></div>
''')
edit('scripts/dashboard.py', 24,
     r'''  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses</span>
  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
''',
     r'''  <span class="sub">{total_docs} readable texts &middot; {total_en:,} English &middot; {total_hi:,} Hindi verses</span>
  <a class="back" href="/sources" title="JUDGE_DESK_2026_10_11: every text whose scan stops its translation, judged, with the editions found" style="margin-left:auto;color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128269; Sources &amp; repairs</a>
  <a class="back" href="/path" title="PATH_2026_10_12: the way forward for every text: repair, find a source, retire, translate, judge" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#129517; The path</a>
  <a class="back" href="/methodology" title="How source and translation quality are measured" style="color:var(--muted);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#9878;&#65039; Quality methodology</a>
  <a class="back" href="/ask" style="color:var(--gold);border:1px solid var(--border);padding:5px 12px;border-radius:7px">&#128172; Ask the Corpus</a>
''')
edit('scripts/dashboard.py', 25,
     r'''    return " OR ".join('"%s"' % t.replace('"', '') for t in toks[:12])

def _ask_retrieve(con, q, k=12):
    m = _ask_fts_query(q)
''',
     r'''    return " OR ".join('"%s"' % t.replace('"', '') for t in toks[:12])

def _ask_withdrawn(con=None) -> set:
    """PATH_2026_10_12: the texts withdrawn from the site (repair_text.py --withdraw) are left out of Ask here too;
    the register beside the database asked (as the Library reads it), else data/."""
    try:
        folder = None
        if con is not None:
            f = (con.execute("PRAGMA database_list").fetchone() or (None, None, ""))[2]
            folder = pathlib.Path(f).parent if f else None
        return {d for d, r in _source_verdicts(folder).items() if r.get("status") == "withdrawn"}
    except Exception:
        return set()


def _ask_retrieve(con, q, k=12):
    m = _ask_fts_query(q)
''')
edit('scripts/dashboard.py', 26,
     r'''        return []
    try:
        return con.execute(
            """SELECT d.code, p.verse_ref, p.page_no, p.idx, p.translation
               FROM passages_fts f
''',
     r'''        return []
    try:
        rows = con.execute(
            """SELECT d.code, p.verse_ref, p.page_no, p.idx, p.translation
               FROM passages_fts f
''')
edit('scripts/dashboard.py', 27,
     r'''            (m, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
''',
     r'''            (m, k),
        ).fetchall()
        wd = _ask_withdrawn(con)   # PATH_2026_10_12
        return [r for r in rows if r[0] not in wd]
    except sqlite3.OperationalError:
        return []
''')
edit('scripts/dashboard.py', 28,
     r'''              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
              AND TRIM(COALESCE(p.translation,'')) <> ''""", top_ids)}
    out = []
    for pid in top_ids:
        r = got.get(pid)
        if r:
            out.append((r[1], r[2], r[3], r[4], r[5]))
        if len(out) >= k:
''',
     r'''              AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')   -- ASK_NOISE_2026_10_07
              AND TRIM(COALESCE(p.translation,'')) <> ''""", top_ids)}
    out, wd = [], _ask_withdrawn(con)   # PATH_2026_10_12: withdrawn texts left out
    for pid in top_ids:
        r = got.get(pid)
        if r and r[1] not in wd:
            out.append((r[1], r[2], r[3], r[4], r[5]))
        if len(out) >= k:
''')


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("scripts/dashboard.py").exists():
        print("FAIL: run from the automaton repo root."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    tool = Path("scripts/text_path.py")
    if not tool.exists() or MARK.encode() not in tool.read_bytes():
        problems.append("scripts/text_path.py (PATH_2026_10_12) is not there: copy it in first")
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out, bad = src, False
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c))
                bad = True; continue
            out = out.replace(old, new, 1)
        if not bad:
            todo.append((p, out.replace("\n", nl).encode("utf-8")))
    gi = Path(".gitignore")
    if gi.exists():
        gsrc, gnl = load(gi)
        if MARK not in gsrc:
            todo.append((gi, (gsrc.rstrip("\n") + "\n" + GITIGNORE_BLOCK).replace("\n", gnl).encode("utf-8")))
        else:
            print("skip .gitignore (already carries %s)" % MARK)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    for p, data in todo:
        if p.suffix != ".py":
            continue
        fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
        Path(tmp).write_bytes(data)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: %s would not compile: %s" % (p, e)); print("Nothing written."); return 1
        finally:
            os.unlink(tmp)
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_path_" + stamp))
        t = p.with_name(p.name + ".tmp_path"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The path of every text is free and read-only:")
    print("  python scripts\\text_path.py --html exports\\text_path.html")
    print("dashboard.py shows /path and the new steps when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
