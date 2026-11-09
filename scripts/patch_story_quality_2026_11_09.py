#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_story_quality_2026_11_09.py  (2026-11-09)  STORY_QUALITY_2026_11_09

"The quality of stories being mined and generated can be much better, can't it?" (9 Nov). scripts\\stories.py and
scripts\\images.py, read against the Stories page of 28 Oct:

  - The English given to the model is the passage's scholarly English where its latest scholarly row passed (or was
    accepted) and its Sanskrit is unchanged since, else the working English; such lines are marked (scholarly). A
    witness with scholarly English alone can now be mined and written (SA_STORY_SCHOLARLY=0 turns this off).
  - SA_STORY_WRITER=anthropic:claude-sonnet-5-5@medium (in .env) writes the stories and the versions for younger
    readers with Claude, through claude_engine.py: paid from the Claude credit, stopped by its meter. Unset, gemini
    writes them as before. Mining and the image ideas stay with Gemini.
  - The writer is asked to tell the episode as a storyteller would, within the six rules: (7).
  - The miner returns no episode for a treatise: the Ganita Yukti Bhasa's 8 "episodes" were calculations.
  - The check: a lowercase IAST word (ksatriyas) is a common noun, not a name; a name spelt otherwise in the passages
    (Krishna, krsna) is found. #66 failed on "ksatriyas" alone.
  - images.py: a reply with something after its JSON gives its first value (#81's image idea failed so); a 429 waits
    as Google's retryDelay asks, at most 60 s, and a fourth try (the Ganita's two 429 failures).

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_storyquality_<date> copies; py_compile.

  python scripts\\patch_story_quality_2026_11_09.py --check
  python scripts\\patch_story_quality_2026_11_09.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'STORY_QUALITY_2026_11_09'
TAG = 'storyquality'
FILES = ['scripts/stories.py', 'scripts/images.py']
NEEDS = {'scripts/stories.py': 'VERIFY_NAMES_2026_10_07', 'scripts/images.py': 'IMAGE_QUALITY_2026_10_04'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/stories.py', 1, 'An approved story linked to an approved image also appears under that image in\nexport_html --images approved (patch_vignettes_2026_10_05.py).\n"""\nfrom __future__ import annotations',
     'An approved story linked to an approved image also appears under that image in\nexport_html --images approved (patch_vignettes_2026_10_05.py).\n\nSTORY_QUALITY_2026_11_09\n------------------------\n- The English given to the model is the best the passage has: its scholarly English where the latest scholarly\n  row passed (or a person accepted it) and its Sanskrit is unchanged since; else the working English. A witness\n  with scholarly English and no working English can now be mined and written too (its stories stay on this PC\n  until the witness is adopted, as the witness does). SA_STORY_SCHOLARLY=0 turns this off.\n- The writer may be Claude: SA_STORY_WRITER=anthropic:claude-sonnet-5-5@medium (in .env) writes the stories and\n  the versions for younger readers through claude_engine.py, paid from the Claude credit and stopped by its meter;\n  unset, gemini (SA_STORY_MODEL) writes them as before. Mining and the image ideas stay with Gemini.\n- The miner returns no episode for a treatise (a calculation, a rule, a definition is not a story).\n- The check: a lowercase word in IAST (ksatriya, rsi, yuga) is a common noun, not a name; a name is also found\n  when the passages spell it otherwise (Krishna and krsna, Kshatriya and ksatriya, an English plural on an IAST\n  stem). A name the passages do not give still fails.\n"""\nfrom __future__ import annotations')

edit('scripts/stories.py', 2, 'MARK = "VIGNETTES_2026_10_05"\nMODEL = os.environ.get("SA_STORY_MODEL", im.BRIEF_MODEL)\nROOT = Path(__file__).resolve().parents[1]\nSTATUSES = ("candidate", "draft", "approved", "retired")',
     'MARK = "VIGNETTES_2026_10_05"\nMODEL = os.environ.get("SA_STORY_MODEL", im.BRIEF_MODEL)\nQUALITY = "STORY_QUALITY_2026_11_09"\nWRITER = os.environ.get("SA_STORY_WRITER", "").strip()   # STORY_QUALITY_2026_11_09: "" = MODEL (gemini), as before\nROOT = Path(__file__).resolve().parents[1]\nSTATUSES = ("candidate", "draft", "approved", "retired")')

edit('scripts/stories.py', 3, '    "Find the EPISODES a general reader would enjoy as a short story: a narrated event with people, a place "\n    "and a turn (a meeting, a curse, a rescue, a contest, a vow, a journey, a dialogue that changes something). "\n    "Skip lists, rules, praise and doctrine. Use only what these passages say. Respond with JSON only: "\n    "{\\"episodes\\": [{\\"title\\": str (6-10 words), \\"title_hi\\": str, \\"from\\": \\"page.idx\\", "\n    "\\"to\\": \\"page.idx\\", \\"why\\": str (one sentence: what happens)}]}. \'from\' and \'to\' must be tags that "',
     '    "Find the EPISODES a general reader would enjoy as a short story: a narrated event with people, a place "\n    "and a turn (a meeting, a curse, a rescue, a contest, a vow, a journey, a dialogue that changes something). "\n    "Skip lists, rules, praise and doctrine. If the passages tell no such episode (a treatise: a calculation, a "\n    "rule, a definition, a commentary), return {\\"episodes\\": []}: an explanation is not a story. "   # STORY_QUALITY_2026_11_09\n    "Use only what these passages say. Respond with JSON only: "\n    "{\\"episodes\\": [{\\"title\\": str (6-10 words), \\"title_hi\\": str, \\"from\\": \\"page.idx\\", "\n    "\\"to\\": \\"page.idx\\", \\"why\\": str (one sentence: what happens)}]}. \'from\' and \'to\' must be tags that "')

edit('scripts/stories.py', 4, '    "which usually means the translation or the OCR is wrong there), leave it out of story_en and story_hi "\n    "and describe it in \'notes\' with its tag. "   # STORIES_UI_2026_10_05\n    "Respond with JSON only: {\\"title\\": str, \\"title_hi\\": str, \\"story_en\\": str, \\"story_hi\\": str, "\n    "\\"quote_sa\\": str, \\"quote_ref\\": \\"page.idx\\", \\"notes\\": str, \\"cites\\": [\\"page.idx\\", ...]}")',
     '    "which usually means the translation or the OCR is wrong there), leave it out of story_en and story_hi "\n    "and describe it in \'notes\' with its tag. "   # STORIES_UI_2026_10_05\n    "(7) Tell it as a storyteller would, within rules 1-6: begin in the scene, keep the order of events, let the "\n    "speakers\' own words (as the passages give them) carry the turns, and keep the passages\' concrete details; no "\n    "summing-up or moral that the passages do not state. Where an ENGLISH line is marked (scholarly), prefer it to "\n    "the others for the meaning. "   # STORY_QUALITY_2026_11_09\n    "Respond with JSON only: {\\"title\\": str, \\"title_hi\\": str, \\"story_en\\": str, \\"story_hi\\": str, "\n    "\\"quote_sa\\": str, \\"quote_ref\\": \\"page.idx\\", \\"notes\\": str, \\"cites\\": [\\"page.idx\\", ...]}")')

edit('scripts/stories.py', 5, '\n\ndef passages(con, code: str) -> list:\n    """[(page, idx, sanskrit, iast, english)] translated, non-noise, in reading order."""\n    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}\n    iast = "COALESCE(p.iast,\'\')" if "iast" in cols else "\'\'"\n    return con.execute(\n        """SELECT p.page_no, p.idx, COALESCE(p.text,\'\'), %s, p.translation FROM passages p\n           JOIN docs d ON d.id = p.doc_id\n           WHERE d.code = ? AND TRIM(COALESCE(p.translation,\'\')) <> \'\'\n             AND COALESCE(p.text_type,\'mula\') NOT IN (\'noise\',\'frontmatter\')\n           ORDER BY p.page_no, p.idx""" % iast, (code,)).fetchall()\n\n',
     '\n\ndef _src_hash(text) -> str:\n    """scholar_translate.src_hash: the Sanskrit a scholarly row was made from, its spaces aside."""\n    return hashlib.sha256(" ".join(str(text or "").split()).encode("utf-8")).hexdigest()[:16]\n\n\ndef scholarly(con, code: str) -> dict:\n    """STORY_QUALITY_2026_11_09: {(page, idx): scholarly English} of a text\'s verses whose latest scholarly row passed\n    (or a person accepted it, and none rejected it) and whose Sanskrit is unchanged since. {} without the table, or\n    with SA_STORY_SCHOLARLY=0."""\n    if os.environ.get("SA_STORY_SCHOLARLY", "1").strip() == "0":\n        return {}\n    try:\n        if not con.execute("SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=\'scholar_translations\'").fetchone():\n            return {}\n        out = {}\n        for pg, ix, text, tr, status, verdict, h in con.execute(\n                """SELECT p.page_no, p.idx, p.text, s.translation, s.status, s.review_verdict, s.src_hash\n                   FROM scholar_translations s JOIN passages p ON p.id = s.passage_id JOIN docs d ON d.id = p.doc_id\n                   WHERE d.code = ? AND s.id IN (SELECT MAX(id) FROM scholar_translations WHERE doc_code = ?\n                                                 GROUP BY passage_id)""", (code, code)):\n            if (tr or "").strip() and verdict != "reject" and (status == "passed" or verdict == "accept") \\\n                    and h == _src_hash(text):\n                out[(pg, ix)] = tr.strip()\n        return out\n    except sqlite3.Error:\n        return {}\n\n\ndef passages(con, code: str) -> list:\n    """[(page, idx, sanskrit, iast, english)] translated, non-noise, in reading order. STORY_QUALITY_2026_11_09: the\n    English is the verse\'s scholarly English where it has one that stands (scholarly()), else its working English."""\n    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}\n    iast = "COALESCE(p.iast,\'\')" if "iast" in cols else "\'\'"\n    rows = con.execute(\n        """SELECT p.page_no, p.idx, COALESCE(p.text,\'\'), %s, p.translation FROM passages p\n           JOIN docs d ON d.id = p.doc_id\n           WHERE d.code = ? AND COALESCE(p.text_type,\'mula\') NOT IN (\'noise\',\'frontmatter\')\n           ORDER BY p.page_no, p.idx""" % iast, (code,)).fetchall()\n    sch = scholarly(con, code)\n    out = []\n    for pg, ix, sa, ia, en in rows:\n        best = sch.get((pg, ix)) or en\n        if (best or "").strip():\n            out.append((pg, ix, sa, ia, best))\n    return out\n\n')

edit('scripts/stories.py', 6, '\n\n# ------------------------------------------------------------------ verify (no API)\ndef verify(story: dict, given: list) -> dict:',
     '\n\ndef _loose(s: str) -> str:\n    """STORY_QUALITY_2026_11_09: a word as an English spelling and the IAST are compared: diacritics off, sh and ch\n    as s and c, ri as r (Kshatriya and ksatriya; Krishna and krsna)."""\n    return _fold(s).replace("sh", "s").replace("ch", "c").replace("ri", "r")\n\n\ndef _name_loose(t: str, lsrc: str) -> bool:\n    """A name found in the passages when both are spelt loosely (_loose), or its stem at the start of a word there\n    when the story adds an English plural to an IAST stem (ksatriyas: ksatriyan)."""\n    lt = _loose(t)\n    if len(lt) < 4:\n        return False\n    if re.search(r"(?<![a-z])" + re.escape(lt), lsrc):\n        return True\n    stem = lt[:-1] if lt.endswith("s") else lt\n    return len(stem) >= 5 and re.search(r"(?<![a-z])" + re.escape(stem), lsrc) is not None\n\n\n# ------------------------------------------------------------------ verify (no API)\ndef verify(story: dict, given: list) -> dict:')

edit('scripts/stories.py', 7, '        problems.append("the Sanskrit quotation is not found verbatim in passage %s" % (qr or "?"))\n    src = _fold(" ".join("%s %s" % (refs[c][3], refs[c][4]) for c in cited if c in refs))\n    unknown = []\n    for s in SENT_RE.split(en):',
     '        problems.append("the Sanskrit quotation is not found verbatim in passage %s" % (qr or "?"))\n    src = _fold(" ".join("%s %s" % (refs[c][3], refs[c][4]) for c in cited if c in refs))\n    lsrc = _loose(src)   # STORY_QUALITY_2026_11_09\n    unknown = []\n    for s in SENT_RE.split(en):')

edit('scripts/stories.py', 8, '            lead = s[:mt.start()].rstrip()[-1:]\n            opens = k == 0 or (lead != "" and lead in OPENERS)\n            is_name = any(c in IAST for c in t2) or (not opens and t2[:1].isupper())\n            if is_name and len(t2) > 2 and t2.lower() not in NAME_STOP and not _name_in(t2, src):   # VERIFY_NAMES_2026_10_07\n                unknown.append(t2)\n    if unknown:',
     '            lead = s[:mt.start()].rstrip()[-1:]\n            opens = k == 0 or (lead != "" and lead in OPENERS)\n            # STORY_QUALITY_2026_11_09: a lowercase IAST word (ksatriya, rsi, yuga) is a common noun, not a name\n            is_name = (any(c in IAST for c in t2) and t2[:1].isupper()) or (not opens and t2[:1].isupper())\n            if is_name and len(t2) > 2 and t2.lower() not in NAME_STOP and not _name_in(t2, src) \\\n                    and not _name_loose(t2, lsrc):   # VERIFY_NAMES_2026_10_07, STORY_QUALITY_2026_11_09\n                unknown.append(t2)\n    if unknown:')

edit('scripts/stories.py', 9, '\n# ------------------------------------------------------------------ paid steps\ndef _prompt_block(rows: list, with_sa: bool) -> str:\n    out = []\n    for p, i, sa, ia, en in rows:',
     '\n# ------------------------------------------------------------------ paid steps\ndef _prompt_block(rows: list, with_sa: bool, sch=None) -> str:\n    out = []\n    for p, i, sa, ia, en in rows:')

edit('scripts/stories.py', 10, '        if with_sa:\n            line += "\\nSA: " + sa.strip().replace("\\n", " ")\n        line += "\\nEN: " + (en or "").strip().replace("\\n", " ")\n        out.append(line)\n    return "\\n\\n".join(out)\n\n',
     '        if with_sa:\n            line += "\\nSA: " + sa.strip().replace("\\n", " ")\n        mark = " (scholarly)" if sch and (p, i) in sch else ""   # STORY_QUALITY_2026_11_09\n        line += "\\nEN%s: " % mark + (en or "").strip().replace("\\n", " ")\n        out.append(line)\n    return "\\n\\n".join(out)\n\n\ndef writer_name() -> str:\n    return WRITER if WRITER.startswith("anthropic:") else MODEL\n\n\ndef writer_cost() -> str:\n    """The estimate a dry run prints: gemini as measured since 5 Oct; Claude Sonnet 5.5 from its prices (about 8k\n    tokens in, 4k out with the Hindi and its thinking at medium effort)."""\n    return ("about $0.06 each, from the Claude credit" if WRITER.startswith("anthropic:") else "about $0.01 each")\n\n\ndef write_json(system: str, user: str, code: str, db: str, http=None, kind: str = "story") -> tuple:\n    """STORY_QUALITY_2026_11_09: (the JSON answer, the engine that wrote it). WRITER (SA_STORY_WRITER) names a Claude\n    engine: the call goes through claude_engine.py, paid from the Claude credit, refused when its meter says the\n    credit is spent or expired, recorded in usage_log. Unset: gemini (MODEL), as before, through images.py. An http\n    client given (the tests\' stubs) always means the gemini path: a test never reaches a paid API."""\n    if WRITER.startswith("anthropic:") and http is None:\n        import claude_engine as ce\n        model, effort = ce.parse_engine(WRITER)\n        con = sqlite3.connect(db, timeout=30)\n        try:\n            if not ce.budget_ok(con):\n                raise SystemExit("FAIL: the Claude credit allows no more calls: python scripts\\\\claude_engine.py "\n                                 "--credit (SA_CLAUDE_CREDIT_USD, _SINCE, _EXPIRES in .env).")\n            t0 = time.time()\n            msg = ce.Client(model, effort).create(system + " Respond with one JSON object only, nothing before or "\n                                                  "after it.", user, 8000)\n            ce.meter(con, kind, code, model, ce._get(msg, "usage"), time.time() - t0, units=1)\n        finally:\n            con.close()\n        return im.parse_json_text(ce.text_of(msg)), ce.engine_name(model, effort)\n    t0 = time.time()\n    data, resp = im.call_text_json(MODEL, system, user, http=http)\n    im.meter(kind, code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)\n    return data, MODEL\n\n')

edit('scripts/stories.py', 11, '    if not rows:\n        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)\n    user = "Episode: %s\\n%s\\n\\nPASSAGES\\n\\n%s" % (s.get("title") or "", s.get("why") or "", _prompt_block(rows, True))\n    t0 = time.time()\n    data, resp = im.call_text_json(MODEL, STORY_SYSTEM, user, http=http)\n    im.meter("story", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)\n    data = data if isinstance(data, dict) else {}\n    v = verify(data, rows)\n    ph = hashlib.sha256((MODEL + STORY_SYSTEM + user).encode("utf-8")).hexdigest()[:16]\n    con.execute(\n        """UPDATE doc_stories SET status=\'draft\', title=COALESCE(NULLIF(?,\'\'), title), title_hi=COALESCE(NULLIF(?,\'\'), title_hi),',
     '    if not rows:\n        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)\n    sch = scholarly(con, code)   # STORY_QUALITY_2026_11_09\n    user = "Episode: %s\\n%s\\n\\nPASSAGES\\n\\n%s" % (s.get("title") or "", s.get("why") or "",\n                                                  _prompt_block(rows, True, sch))\n    data, engine = write_json(STORY_SYSTEM, user, code, db, http=http)\n    data = data if isinstance(data, dict) else {}\n    v = verify(data, rows)\n    ph = hashlib.sha256((engine + STORY_SYSTEM + user).encode("utf-8")).hexdigest()[:16]\n    con.execute(\n        """UPDATE doc_stories SET status=\'draft\', title=COALESCE(NULLIF(?,\'\'), title), title_hi=COALESCE(NULLIF(?,\'\'), title_hi),')

edit('scripts/stories.py', 12, '        (data.get("title") or "", data.get("title_hi") or "", data.get("story_en") or "", data.get("story_hi") or "",\n         data.get("quote_sa") or "", data.get("quote_ref") or "", data.get("notes") or "",\n         json.dumps(v["cited"]), json.dumps(v), MODEL, ph,\n         json.dumps({"given": [ref(*rows[0][:2]), ref(*rows[-1][:2])], "n_given": len(rows),\n                     "written_at": now()}), now(), sid))\n    con.commit()',
     '        (data.get("title") or "", data.get("title_hi") or "", data.get("story_en") or "", data.get("story_hi") or "",\n         data.get("quote_sa") or "", data.get("quote_ref") or "", data.get("notes") or "",\n         json.dumps(v["cited"]), json.dumps(v), engine, ph,\n         json.dumps({"given": [ref(*rows[0][:2]), ref(*rows[-1][:2])], "n_given": len(rows),\n                     "scholarly": sum(1 for r in rows if (r[0], r[1]) in sch), "writer": engine,\n                     "written_at": now()}), now(), sid))\n    con.commit()')

edit('scripts/stories.py', 13, '    system = RETELL_SYSTEM % (who, how)\n    user = ("Episode: %s\\n\\nAPPROVED RETELLING (for adults):\\n%s\\n\\nEDITORIAL NOTES:\\n%s\\n\\nPASSAGES\\n\\n%s"\n            % (s.get("title") or "", s.get("story_en") or "", s.get("notes") or "(none)", _prompt_block(rows, True)))\n    t0 = time.time()\n    data, resp = im.call_text_json(MODEL, system, user, http=http)\n    im.meter("story", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)\n    data = data if isinstance(data, dict) else {}\n    v = variant_verify(con, s, data)\n    ph = hashlib.sha256((MODEL + system + user).encode("utf-8")).hexdigest()[:16]\n    con.execute(\n        """INSERT INTO doc_story_variants(story_id, audience, status, title, title_hi, story_en, story_hi, notes, cites,',
     '    system = RETELL_SYSTEM % (who, how)\n    user = ("Episode: %s\\n\\nAPPROVED RETELLING (for adults):\\n%s\\n\\nEDITORIAL NOTES:\\n%s\\n\\nPASSAGES\\n\\n%s"\n            % (s.get("title") or "", s.get("story_en") or "", s.get("notes") or "(none)",\n               _prompt_block(rows, True, scholarly(con, code))))\n    data, engine = write_json(system, user, code, db, http=http)   # STORY_QUALITY_2026_11_09\n    data = data if isinstance(data, dict) else {}\n    v = variant_verify(con, s, data)\n    ph = hashlib.sha256((engine + system + user).encode("utf-8")).hexdigest()[:16]\n    con.execute(\n        """INSERT INTO doc_story_variants(story_id, audience, status, title, title_hi, story_en, story_hi, notes, cites,')

edit('scripts/stories.py', 14, '        (sid, audience, data.get("title") or s.get("title") or "", data.get("title_hi") or s.get("title_hi") or "",\n         data.get("story_en") or "", data.get("story_hi") or "", data.get("notes") or "", json.dumps(v["cited"]),\n         json.dumps(v), MODEL, ph, json.dumps({"from_story": sid, "story_status": s["status"], "written_at": now()}),\n         now(), now()))\n    con.commit()',
     '        (sid, audience, data.get("title") or s.get("title") or "", data.get("title_hi") or s.get("title_hi") or "",\n         data.get("story_en") or "", data.get("story_hi") or "", data.get("notes") or "", json.dumps(v["cited"]),\n         json.dumps(v), engine, ph, json.dumps({"from_story": sid, "story_status": s["status"], "written_at": now()}),\n         now(), now()))\n    con.commit()')

edit('scripts/stories.py', 15, '                print("give --id, --image, or --doc with --images or --candidates"); return 2\n            ids = [i for i in ids if _row(con, i)["status"] in ("candidate", "draft")][:args.max]\n            print("write: %d story(ies) with %s, about $0.01 each" % (len(ids), MODEL))\n            for i in ids:\n                s = _row(con, i)',
     '                print("give --id, --image, or --doc with --images or --candidates"); return 2\n            ids = [i for i in ids if _row(con, i)["status"] in ("candidate", "draft")][:args.max]\n            print("write: %d story(ies) with %s, %s" % (len(ids), writer_name(), writer_cost()))   # STORY_QUALITY_2026_11_09\n            for i in ids:\n                s = _row(con, i)')

edit('scripts/stories.py', 16, '        if args.cmd == "retell":   # STORY_VARIANTS_2026_10_07\n            s = _row(con, args.id)\n            print("retell #%d %s for %s with %s, about $0.01" % (args.id, s.get("title") or "",\n                                                                 AUDIENCE_SPEC[args.audience][0], MODEL))\n            if not args.yes:\n                print("Dry run. Add --yes."); return 0',
     '        if args.cmd == "retell":   # STORY_VARIANTS_2026_10_07\n            s = _row(con, args.id)\n            print("retell #%d %s for %s with %s, %s" % (args.id, s.get("title") or "", AUDIENCE_SPEC[args.audience][0],\n                                                        writer_name(), writer_cost()))   # STORY_QUALITY_2026_11_09\n            if not args.yes:\n                print("Dry run. Add --yes."); return 0')

edit('scripts/images.py', 1, '\n\ndef http_json(url: str, body: dict | None = None, timeout: int = 180) -> dict:\n    data = None if body is None else json.dumps(body).encode("utf-8")\n    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",\n                                 headers={"Content-Type": "application/json", "x-goog-api-key": _key()})\n    for attempt in range(3):\n        try:\n            with urllib.request.urlopen(req, timeout=timeout) as r:\n                return json.loads(r.read().decode("utf-8"))\n        except urllib.error.HTTPError as e:\n            msg = e.read().decode("utf-8", "replace")[:400]\n            if e.code in (429, 500, 503, 504) and attempt < 2:\n                time.sleep(4 * (attempt + 1)); continue\n            raise SystemExit("FAIL: HTTP %d from the API: %s" % (e.code, msg))\n        except (urllib.error.URLError, TimeoutError) as e:',
     '\n\ndef retry_wait(code: int, body: str, attempt: int) -> float:\n    """STORY_QUALITY_2026_11_09: seconds to wait before the next try. A 429 (the requests a minute used up) waits as\n    long as Google\'s RetryInfo asks ("retryDelay": "37s"), at most 60 s, else 15, 30, 45 s; a server error 4, 8, 12 s\n    as before. On 28 Oct "Write found episodes" failed twice on a 429 that the 4 and 8 s waits could not outlast."""\n    if code == 429:\n        m = re.search(r\'"retryDelay"\\s*:\\s*"(\\d+(?:\\.\\d+)?)s"\', body or "")\n        return min(60.0, float(m.group(1)) + 1.0) if m else 15.0 * (attempt + 1)\n    return 4.0 * (attempt + 1)\n\n\ndef http_json(url: str, body: dict | None = None, timeout: int = 180) -> dict:\n    data = None if body is None else json.dumps(body).encode("utf-8")\n    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",\n                                 headers={"Content-Type": "application/json", "x-goog-api-key": _key()})\n    for attempt in range(4):   # STORY_QUALITY_2026_11_09: a fourth try, and Google\'s own wait after a 429\n        try:\n            with urllib.request.urlopen(req, timeout=timeout) as r:\n                return json.loads(r.read().decode("utf-8"))\n        except urllib.error.HTTPError as e:\n            body = e.read().decode("utf-8", "replace")\n            msg = body[:400]\n            if e.code in (429, 500, 503, 504) and attempt < 3:\n                time.sleep(retry_wait(e.code, body, attempt)); continue\n            raise SystemExit("FAIL: HTTP %d from the API: %s" % (e.code, msg))\n        except (urllib.error.URLError, TimeoutError) as e:')

edit('scripts/images.py', 2, '    text = "".join(p.get("text", "") for c in resp.get("candidates") or []\n                   for p in (c.get("content") or {}).get("parts") or [])\n    text = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", text.strip())\n    return json.loads(text), resp\n\n',
     '    text = "".join(p.get("text", "") for c in resp.get("candidates") or []\n                   for p in (c.get("content") or {}).get("parts") or [])\n    return parse_json_text(text), resp\n\n\ndef parse_json_text(text: str):\n    """STORY_QUALITY_2026_11_09: the JSON a model returned. Fences are taken off; a reply with something after its\n    JSON (an extra brace, a second object: "Proposing an image" failed so on 28 Oct) gives its first value; a reply\n    with no JSON at all stops with what it said, not a traceback."""\n    text = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", (text or "").strip())\n    try:\n        return json.loads(text)\n    except ValueError:\n        pass\n    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]\n    if starts:\n        try:\n            return json.JSONDecoder().raw_decode(text[min(starts):])[0]\n        except ValueError:\n            pass\n    raise SystemExit("FAIL: the model\'s reply is not the JSON asked for: %r" % text[:200])\n\n')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

