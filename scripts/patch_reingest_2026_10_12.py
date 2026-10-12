#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_reingest_2026_10_12.py  (2026-10-12)  REINGEST_2026_10_12

After QUALITY_2026_10_11, on the morning of 12 Oct: the repaired Tantric Texts and Karan Aagama were merged again
(7 garbage pages each refused), and --use-repaired refused both, as it should: the Tantric Texts had 1,333 English
translations by then, Karan 13 pictures. scripts/reingest_pages.py (new, R3) puts only the changed pages into the
database. This patch wires it in, and mends four things the run showed:
  merge_ocr_sources.py: the stray-mark pattern said "\\[" in a plain string; Python 3.13 printed "SyntaxWarning:
    invalid escape sequence" on every merge. The same pattern, written without the warning.
  repair_text.py: the assessment priced vision at $0.0004 a page ("269 pages, about $0.11" for the Natyasastra);
    its pages had cost $0.011 each. It now prices from usage_log, by text where it can (ocr_consensus.py's measure,
    as ocr_vision.py does). Where --use-repaired would replace translations or pictures, it offers
    reingest_pages.py beside it.
  benchmark_sources.py: the LLM judge's figures (judge_sample.py, first run on 12 Oct) now say how many passages
    have a serious error of meaning (fidelity 2 or less), and how much that is.
  .gitignore: data/reingest/ (what a re-ingest removed) stays local.
  dashboard.py (on a restart): "Plan: only the changed pages" and "Re-ingest the changed pages" on the repair page;
    "Use the repaired text" now sends --replace 0 (for a text with pictures and no English it was never sent, and
    the press refused for ever); /benchmarks shows the judge.

Needs QUALITY_2026_10_11 (merge_ocr_sources.py, benchmark_sources.py, dashboard.py), BENCHMARK_2026_10_11
(repair_text.py), and scripts/reingest_pages.py. Anchored, all-or-nothing, marker-idempotent per file; keeps line
endings and encodings; each .py is compiled before it replaces the original; backups .bak_reingest_<date>.
  python scripts\\patch_reingest_2026_10_12.py --check
  python scripts\\patch_reingest_2026_10_12.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REINGEST_2026_10_12"
NEEDS = {"scripts/merge_ocr_sources.py": "QUALITY_2026_10_11", "scripts/repair_text.py": "BENCHMARK_2026_10_11",
         "scripts/benchmark_sources.py": "QUALITY_2026_10_11", "scripts/dashboard.py": "QUALITY_2026_10_11"}
FILES = list(NEEDS)
GITIGNORE_BLOCK = ("# REINGEST_2026_10_12: what the in-place re-ingest removed stays local (data/reingest/<doc>_<stamp>.jsonl)\n"
                   "data/reingest/\n")

E = []   # (file, number, old, new): hunks with their context, applied in order
def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/merge_ocr_sources.py', 1,
     r'''DEV_LETTER = re.compile("[\u0904-\u0939\u0958-\u0961]")
LATIN_WORD = re.compile(r"[A-Za-z]+")
STRAY = re.compile("[~^=+*<>|\\{}\[\]_`$#@%&\u00a2\u00a3\u00a5\u2020\u2021\u00a9\u00ae\u00b6\u00a7"
                   "\u201c\u201d\u2018\u2019\u201e\u00bb\u00ab\u2022]")

''',
     r'''DEV_LETTER = re.compile("[\u0904-\u0939\u0958-\u0961]")
LATIN_WORD = re.compile(r"[A-Za-z]+")
# REINGEST_2026_10_12: "\\[" and "\\]" (Python 3.13 warned "invalid escape sequence '\\['" on every run); the same pattern
STRAY = re.compile("[~^=+*<>|\\{}\\[\\]_`$#@%&\u00a2\u00a3\u00a5\u2020\u2021\u00a9\u00ae\u00b6\u00a7"
                   "\u201c\u201d\u2018\u2019\u201e\u00bb\u00ab\u2022]")

''')
edit('scripts/repair_text.py', 2,
     r'''
LEVELS = ("cosmetic", "moderate", "material")


''',
     r'''
LEVELS = ("cosmetic", "moderate", "material")
# REINGEST_2026_10_12: the in-place re-ingest, offered where --use-repaired would replace translations or pictures
REINGEST = ("python scripts\\reingest_pages.py --doc %s   (only the pages that changed: the rest keep their translations "
            "and pictures; the plan is free)")


def measured_cost_per_page(db: str, doc: str) -> float:
    """REINGEST_2026_10_12: what a vision page of this text really costs, from usage_log (ocr_consensus.py's measure,
    as ocr_vision.py prices its pre-flight). The assessment said "269 pages, about $0.11" for the Natyasastra on
    12 Oct, at COST_PER_PAGE; its pages had cost $0.011 each, 27 times as much. COST_PER_PAGE when nothing is measured."""
    try:
        import ocr_consensus as _oc
        return float(_oc.measured_cost_per_page(db, fallback=COST_PER_PAGE, doc=doc))
    except Exception:
        return COST_PER_PAGE


''')
edit('scripts/repair_text.py', 3,
     r'''        "nothing_to_lose": en <= NOTHING_TO_LOSE_EN and hi == 0 and pictures == 0 and stories == 0,
        "aside": state, "state": state,
    })
    res["held"] = res["guard"] and not (state and state.get("status") == "translate_as_is")
''',
     r'''        "nothing_to_lose": en <= NOTHING_TO_LOSE_EN and hi == 0 and pictures == 0 and stories == 0,
        "aside": state, "state": state,
        "cost_per_page": measured_cost_per_page(a.db, a.doc),   # REINGEST_2026_10_12
    })
    res["held"] = res["guard"] and not (state and state.get("status") == "translate_as_is")
''')
edit('scripts/repair_text.py', 4,
     r'''        pages = r["queued"] or r["pdfs"]
        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f" % (left, left * COST_PER_PAGE),
                q + " --repair   (capped at --max-usd 1.00)", also)
    if r["queued"] and r["vision_pages"] < 0.8 * r["queued"]:
''',
     r'''        pages = r["queued"] or r["pdfs"]
        left = max(0, pages - r["vision_pages"]) if r["vision_pages"] else pages
        cpp = r.get("cost_per_page") or COST_PER_PAGE   # REINGEST_2026_10_12: measured on this text where it can be
        return (why + "; the scan can be repaired: vision OCR on about %d page(s), about $%.2f ($%.4f a page)"
                % (left, left * cpp, cpp),
                q + " --repair   (capped at --max-usd 1.00)", also)
    if r["queued"] and r["vision_pages"] < 0.8 * r["queued"]:
''')
edit('scripts/repair_text.py', 5,
     r'''                "at the old passages" % (r["english"], r["hindi"], r["vectors"], r["pictures"], r["stories"]))
        nxt = q + " --use-repaired" + ("" if r["nothing_to_lose"] else " --replace %d" % r["english"])
        return (why + "; the repaired text is ready (%s pages differ from the database); %s" % (s.get("stale", 0), lose),
                nxt, also)
''',
     r'''                "at the old passages" % (r["english"], r["hindi"], r["vectors"], r["pictures"], r["stories"]))
        nxt = q + " --use-repaired" + ("" if r["nothing_to_lose"] else " --replace %d" % r["english"])
        if not r["nothing_to_lose"]:   # REINGEST_2026_10_12: only the pages that changed
            also = [REINGEST % doc] + also
        return (why + "; the repaired text is ready (%s pages differ from the database); %s" % (s.get("stale", 0), lose),
                nxt, also)
''')
edit('scripts/repair_text.py', 6,
     r'''        print("VERDICT: a decision is needed")
        print("NEXT: python scripts\\repair_text.py --doc %s --use-repaired --replace %d" % (doc, r["english"]))
        return 1
    w = writers_running(a.from_dashboard, doc)
''',
     r'''        print("VERDICT: a decision is needed")
        print("NEXT: python scripts\\repair_text.py --doc %s --use-repaired --replace %d" % (doc, r["english"]))
        print("ALSO: " + REINGEST % doc)   # REINGEST_2026_10_12
        return 1
    w = writers_running(a.from_dashboard, doc)
''')
edit('scripts/benchmark_sources.py', 7,
     r'''        if "mt_reviews" in tables:
            try:
                r = con.execute("SELECT COUNT(*), AVG(m.score_fidelity), AVG(m.score_fluency) FROM mt_reviews m JOIN passages p "
                                "ON p.id=m.passage_id WHERE p.doc_id=? AND m.lang='en'", (did,)).fetchone()
                if r and r[0]:
                    rev = {"n": int(r[0]), "fidelity": round(float(r[1] or 0), 2), "fluency": round(float(r[2] or 0), 2)}
            except sqlite3.Error:
                rev = None
''',
     r'''        if "mt_reviews" in tables:
            try:
                r = con.execute("SELECT COUNT(*), AVG(m.score_fidelity), AVG(m.score_fluency), SUM(CASE WHEN m.score_fidelity "
                                "<= 2 THEN 1 ELSE 0 END) FROM mt_reviews m JOIN passages p "
                                "ON p.id=m.passage_id WHERE p.doc_id=? AND m.lang='en'", (did,)).fetchone()
                if r and r[0]:
                    rev = {"n": int(r[0]), "fidelity": round(float(r[1] or 0), 2), "fluency": round(float(r[2] or 0), 2),
                           "serious": int(r[3] or 0)}   # REINGEST_2026_10_12: fidelity 2 or less, a wrong meaning
            except sqlite3.Error:
                rev = None
''')
edit('scripts/benchmark_sources.py', 8,
     r'''                                                  share, nzs, lv, "" if n.get("reviews") else "; no LLM judge has read it yet"))
        if n.get("reviews"):
            L.append("The LLM judge (mt_reviews) graded %d English passages: fidelity %.2f, fluency %.2f of 5." % (
                n["reviews"]["n"], n["reviews"]["fidelity"], n["reviews"]["fluency"]))
    elif n.get("passages"):
        L.append("Translation now: none of its %d passages has English yet." % n["passages"])
''',
     r'''                                                  share, nzs, lv, "" if n.get("reviews") else "; no LLM judge has read it yet"))
        if n.get("reviews"):
            rv = n["reviews"]
            line = "The LLM judge (mt_reviews) graded %d English passages: fidelity %.2f, fluency %.2f of 5." % (
                rv["n"], rv["fidelity"], rv["fluency"])
            if rv.get("serious") is not None:   # REINGEST_2026_10_12: the share with a wrong meaning, and what it is
                sh = 100.0 * rv["serious"] / rv["n"]
                lv = "material" if sh >= 10 else ("moderate" if sh >= 5 else "cosmetic")
                line += (" %d of them (%.0f%%) have a serious error of meaning (fidelity 2 or less: an omission, a "
                         "negation lost, a word misread): %s. It is a sample, judged by a model of the translator's "
                         "family; read the passages it marks (python scripts\\judge_sample.py --report)." % (
                             rv["serious"], sh, lv))
            L.append(line)
    elif n.get("passages"):
        L.append("Translation now: none of its %d passages has English yet." % n["passages"])
''')
edit('scripts/dashboard.py', 9,
     r'''_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore", "as_is", "accept", "hold", "release",
                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all")              # BENCHMARK_2026_10_11
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness")   # ETEXT_WITNESS_2026_10_11: witness
''',
     r'''_REPAIR_STEPS = ("assess", "repair", "use", "set_aside", "restore", "as_is", "accept", "hold", "release",
                 "find", "fetch", "judge_all", "witness",   # JUDGE_DESK_2026_10_11: judge_all; ETEXT_WITNESS_2026_10_11: witness
                 "benchmark", "benchmark_all",              # BENCHMARK_2026_10_11
                 "reingest_plan", "reingest")               # REINGEST_2026_10_12: only the pages that changed
_REPAIR_MAX_USD = 5.0      # the most one press spends on vision OCR; above it, run repair_text.py by hand
_REPAIR_STATES = ("set_aside", "translate_as_is", "complete", "in_repair", "witness")   # ETEXT_WITNESS_2026_10_11: witness
''')
edit('scripts/dashboard.py', 10,
     r'''                 find: 'looking for a better edition...', fetch: 'fetching...', translate: 'translating...',
                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...',
                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...'};
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''',
     r'''                 find: 'looking for a better edition...', fetch: 'fetching...', translate: 'translating...',
                 judge_all: 'judging the texts (about a minute)...', witness: 'reading the e-text as a witness...',
                 benchmark: 'benchmarking the readings (free)...', benchmark_all: 'benchmarking every text (a minute or two)...',
                 reingest_plan: 'planning the re-ingest (free)...', reingest: 're-ingesting the changed pages...'};   /* REINGEST_2026_10_12 */
var _RP_NL = String.fromCharCode(10), _RP_CR = String.fromCharCode(13), _RP_BS = String.fromCharCode(92);
function _rpLines(s){
''')
edit('scripts/dashboard.py', 11,
     r'''function _rpNext(next){
  var n = String(next || ''), m;
  if (n.indexOf('etext_witness.py') >= 0){   /* ETEXT_WITNESS_2026_10_11 */
    if (n.indexOf('--ingest') >= 0){
''',
     r'''function _rpNext(next){
  var n = String(next || ''), m;
  if (n.indexOf('reingest_pages.py') >= 0){   /* REINGEST_2026_10_12: only the pages that changed */
    m = n.match(/--replace ([0-9]+)/);
    var pg = n.match(/--pages ([0-9,-]+)/);
    if (n.indexOf('--apply') < 0) return {step: 'reingest_plan', pages: pg ? pg[1] : '', label: 'Plan: only the changed pages (free)'};
    return {step: 'reingest', pages: pg ? pg[1] : '', replace: m ? +m[1] : null,
            label: (m && +m[1]) ? 'Re-ingest the changed pages (removes ' + m[1] + ' English)' : 'Re-ingest the changed pages'};
  }
  if (n.indexOf('etext_witness.py') >= 0){   /* ETEXT_WITNESS_2026_10_11 */
    if (n.indexOf('--ingest') >= 0){
''')
edit('scripts/dashboard.py', 12,
     r'''           + 'site keeps its last version until you publish the new one. Go?')
        : ('Use the repaired text of ' + doc + '. Nothing translated is lost; a backup is made first. Go?'))) return;
    if (opt.replace) body.replace = opt.replace;
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold'){
''',
     r'''           + 'site keeps its last version until you publish the new one. Go?')
        : ('Use the repaired text of ' + doc + '. Nothing translated is lost; a backup is made first. Go?'))) return;
    if (opt.replace != null) body.replace = opt.replace;   /* REINGEST_2026_10_12: --replace 0 (pictures) was never sent */
  }
  if (step === 'reingest_plan' || step === 'reingest'){   /* REINGEST_2026_10_12 */
    if (opt.pages) body.pages = opt.pages;
    if (step === 'reingest'){
      if (!confirm('Re-ingest the pages of ' + doc + ' that differ from its repaired text. A backup first; on those pages a '
                   + 'passage whose text is unchanged keeps its translations, the others are replaced'
                   + (opt.replace ? ' (' + opt.replace + ' English translations go)' : '') + '; the other pages are not '
                   + 'touched. Go?')) return;
      if (opt.replace != null) body.replace = opt.replace;
    }
  }
  if (step === 'set_aside' || step === 'as_is' || step === 'accept' || step === 'hold'){
''')
edit('scripts/dashboard.py', 13,
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|as_is|accept|hold|release|translate|judge_all|benchmark_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''',
     r'''      if ((step === 'find' || step === 'fetch' || step === 'witness' || step === 'benchmark') && document.getElementById('srclist-' + doc)) _rpSources(doc);
      if (j.ok && pre && step === 'translate') repairStep(doc, 'assess', null);
      if (j.ok && !pre && /^(set_aside|restore|use|reingest|as_is|accept|hold|release|translate|judge_all|benchmark_all)$/.test(step))
        setTimeout(function(){ location.reload(); }, 3000);
      return;
''')
edit('scripts/dashboard.py', 14,
     r'''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    kind = "repair_use" if step == "use" or (step == "witness" and data.get("ingest")) else "repair"   # ETEXT_WITNESS_2026_10_11
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})

''',
     r'''    elif step == "judge_all":   # JUDGE_DESK_2026_10_11
        argv = [script("repair_text.py"), "--judge-all"]
    elif step in ("reingest_plan", "reingest"):   # REINGEST_2026_10_12: the plan is read-only; the re-ingest a writer
        argv = [script("reingest_pages.py"), "--doc", doc, "--from-dashboard"]
        pages = str(data.get("pages") or "")
        if pages:
            if not re.match(r"^[0-9][0-9,\-]{0,199}$", pages):
                return jsonify({"error": "pages must be numbers and ranges: 2,20-21"}), 400
            argv += ["--pages", pages]
        if step == "reingest":
            argv.append("--apply")
            if data.get("replace") not in (None, ""):
                try:
                    argv += ["--replace", str(int(data.get("replace")))]
                except (TypeError, ValueError):
                    return jsonify({"error": "replace must be a whole number"}), 400
    kind = "repair_use" if step in ("use", "reingest") or (step == "witness" and data.get("ingest")) else "repair"   # ETEXT_WITNESS_2026_10_11; REINGEST_2026_10_12
    return jsonify({"job": launch(kind, doc, py(*argv), mode=step), "kind": kind, "step": step})

''')
edit('scripts/dashboard.py', 15,
     r'''                                      ('<br><span class="muted">%s</span>' % e(ours["label"])) if ours else "",
                                      e("; ".join("%s %s" % (x["label"], pct(x)) for x in arch)) or "-", e(ref), e(before),
                                      e("%s of %s EN, %s HI" % (n.get("english", 0), n.get("passages", 0), n.get("hindi", 0)))
                                      if n else "-"))
        if r.get("lines"):
''',
     r'''                                      ('<br><span class="muted">%s</span>' % e(ours["label"])) if ours else "",
                                      e("; ".join("%s %s" % (x["label"], pct(x)) for x in arch)) or "-", e(ref), e(before),
                                      e(("%s of %s EN, %s HI" % (n.get("english", 0), n.get("passages", 0), n.get("hindi", 0)))
                                        + (("; judged %.2f of 5 on %d, %d%% a wrong meaning" % (   # REINGEST_2026_10_12
                                            n["reviews"]["fidelity"], n["reviews"]["n"],
                                            round(100.0 * n["reviews"]["serious"] / n["reviews"]["n"])))
                                           if (n.get("reviews") or {}).get("serious") is not None else ""))
                                      if n else "-"))
        if r.get("lines"):
''')
edit('scripts/dashboard.py', 16,
     r'''<li><b>Repair the scan</b>: vision OCR on its pages, with a cap on the spend. The database is not touched.</li>
<li><b>Use the repaired text</b>: a backup first; then its passages are replaced by the repaired text, under the translate lock. The site keeps its last version until you publish the new one.</li>
<li><b>Translate as is</b>, when the debris is cosmetic; <b>set aside</b> and <b>find a better source</b>, when the scan cannot be repaired.</li>
</ol>
''',
     r'''<li><b>Repair the scan</b>: vision OCR on its pages, with a cap on the spend. The database is not touched.</li>
<li><b>Use the repaired text</b>: a backup first; then its passages are replaced by the repaired text, under the translate lock. The site keeps its last version until you publish the new one.</li>
<li><b>Re-ingest the changed pages</b> (REINGEST_2026_10_12): when the text has translations or pictures, only the pages that differ from the repaired text change; a passage whose text is unchanged keeps its translations. The plan is free.</li>
<li><b>Translate as is</b>, when the debris is cosmetic; <b>set aside</b> and <b>find a better source</b>, when the scan cannot be repaired.</li>
</ol>
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
    tool = Path("scripts/reingest_pages.py")
    if not tool.exists() or MARK.encode() not in tool.read_bytes():
        problems.append("scripts/reingest_pages.py (REINGEST_2026_10_12) is not there: copy it in first")
    for rel in FILES:
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        if NEEDS[rel] not in src:
            problems.append("%s does not carry %s: apply its patch first" % (rel, NEEDS[rel])); continue
        out = src
        for f, n, old, new in E:
            if f != rel:
                continue
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor %d found %d times (want 1): this is not the file released" % (rel, n, c)); continue
            out = out.replace(old, new, 1)
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
        shutil.copy2(p, p.with_name(p.name + ".bak_reingest_" + stamp))
        t = p.with_name(p.name + ".tmp_reingest"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Nothing in the database changed. The plan of the in-place re-ingest is free:")
    print("  python scripts\\reingest_pages.py --doc tantric_texts_series_edited_by_arthur_av")
    print("dashboard.py shows the new steps when restarted (only when idle: scripts\\restart_dashboard.ps1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
