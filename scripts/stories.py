#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
stories.py  (2026-10-05)  VIGNETTES_2026_10_05

Short, cited retellings ("vignettes") of episodes in a text: one beside each
generated image, and a way to mine a book for its readable episodes and compile
the approved ones into an illustrated, cited anthology.

WHY THE CARE
------------
A retelling is an interpretation, and these texts reach us through OCR and machine
translation. Measured on markandeya_purana (2026-10-05): image idea #86 calls the
sage "Mrnjiga". The passages name him Samika (11.5, 11.8, 21.8). The one
"Mrnjiga" (14.11, "saha putrena mrnjiga") is an OCR misreading - most likely of
the name of Samika's son - which the translation then took as the sage's name.
So every story here:
  - is written ONLY from the passages it is given (Sanskrit + English);
  - cites a passage after every sentence, as [page.idx];
  - quotes one Sanskrit line, which must be found verbatim in a cited passage;
  - carries editorial NOTES for readings that look damaged, instead of guessing;
  - is checked by `verify` (deterministic, no API): every sentence cited, cites
    inside the range given, the quote found, and every proper name present in
    the cited passages. A story that fails cannot be approved without --force.
Nothing is published until a person approves it.

STORAGE
-------
New table doc_stories, created on first use. It references passages by
(page, idx) like doc_images, not by passage id, so a re-ingest does not orphan it.

  candidate -> draft -> approved | retired

COMMANDS (dry run unless --yes; every paid call is metered and asks the budget)
  python scripts\\stories.py mine    --doc markandeya_purana [--max 12] [--chunk 150] [--yes]
  python scripts\\stories.py write   --doc markandeya_purana --images [--max 6] [--yes]
  python scripts\\stories.py write   --id 7 [--yes]          (a mined candidate)
  python scripts\\stories.py write   --image 86 [--yes]      (one image)
  python scripts\\stories.py verify  --id 7
  python scripts\\stories.py list    --doc markandeya_purana [--status draft]
  python scripts\\stories.py show    --id 7
  python scripts\\stories.py approve --id 7 [--force] | retire --id 7
  python scripts\\stories.py anthology --docs markandeya_purana,Mallapurana [--title "..."]
         -> exports\\anthology_<date>.html  (then: python scripts\\export_pdf.py <that file>)
An approved story linked to an approved image also appears under that image in
export_html --images approved (patch_vignettes_2026_10_05.py).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import images as im  # noqa: E402  (REST client, metering, connection helpers)

MARK = "VIGNETTES_2026_10_05"
MODEL = os.environ.get("SA_STORY_MODEL", im.BRIEF_MODEL)
ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("candidate", "draft", "approved", "retired")

SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_stories(
  id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, image_id INTEGER,
  status TEXT NOT NULL DEFAULT 'candidate',
  title TEXT, title_hi TEXT, why TEXT,
  from_page INTEGER, from_idx INTEGER, to_page INTEGER, to_idx INTEGER,
  story_en TEXT, story_hi TEXT, quote_sa TEXT, quote_ref TEXT, notes TEXT,
  cites TEXT, verify TEXT, model TEXT, prompt_hash TEXT, provenance TEXT,
  created_at TEXT, updated_at TEXT, approved_at TEXT);
CREATE INDEX IF NOT EXISTS ix_doc_stories_doc ON doc_stories(doc_id, status);
CREATE INDEX IF NOT EXISTS ix_doc_stories_image ON doc_stories(image_id);
"""

MINE_SYSTEM = (
    "You read an English translation of part of a Sanskrit text, passage by passage, each tagged [page.idx]. "
    "Find the EPISODES a general reader would enjoy as a short story: a narrated event with people, a place "
    "and a turn (a meeting, a curse, a rescue, a contest, a vow, a journey, a dialogue that changes something). "
    "Skip lists, rules, praise and doctrine. Use only what these passages say. Respond with JSON only: "
    "{\"episodes\": [{\"title\": str (6-10 words), \"title_hi\": str, \"from\": \"page.idx\", "
    "\"to\": \"page.idx\", \"why\": str (one sentence: what happens)}]}. 'from' and 'to' must be tags that "
    "appear below, with from before to, spanning the whole episode (usually 4-40 passages). At most %d episodes.")

STORY_SYSTEM = (
    "You retell ONE episode from a Sanskrit text for an illustrated, cited anthology. You are given the passages: "
    "each has a tag [page.idx], the Sanskrit as printed (from OCR, sometimes damaged) and an English translation "
    "(machine-made, sometimes wrong where the Sanskrit is damaged). Rules: "
    "(1) Use ONLY these passages. Add no events, motives, speech, places or descriptions that they do not give. "
    "(2) After EVERY sentence, cite the passage(s) it rests on, as [page.idx] or [page.idx, page.idx]. "
    "(3) Give names exactly as the passages give them, in IAST. If one passage gives a name that the others do "
    "not support, or the Sanskrit looks damaged, do not build on it: say so in 'notes' (you may suggest a likely "
    "reading there, marked 'reading uncertain'). "
    "(4) story_en: 120-220 words, plain and vivid, past tense. story_hi: the same story in natural Hindi, same "
    "citations. "
    "(5) quote_sa: one line of the Sanskrit copied EXACTLY from one passage (at most 120 characters), with its "
    "tag in quote_ref. Choose a line whose printed text looks sound. "
    "(6) If a translated detail makes no sense in the story (an animal, object or act that does not belong, "
    "which usually means the translation or the OCR is wrong there), leave it out of story_en and story_hi "
    "and describe it in 'notes' with its tag. "   # STORIES_UI_2026_10_05
    "Respond with JSON only: {\"title\": str, \"title_hi\": str, \"story_en\": str, \"story_hi\": str, "
    "\"quote_sa\": str, \"quote_ref\": \"page.idx\", \"notes\": str, \"cites\": [\"page.idx\", ...]}")

REF_RE = re.compile(r"(\d+)\.(\d+)")
BRACKET_RE = re.compile(r"\[([^\]]*\d+\.\d+[^\]]*)\]")
IAST = "\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e45\u00f1\u1e6d\u1e0d\u1e47\u015b\u1e63\u1e43\u1e25" \
       "\u0100\u012a\u016a\u1e5a\u1e5c\u1e36\u1e44\u00d1\u1e6c\u1e0c\u1e46\u015a\u1e62\u1e42\u1e24"
WORD_RE = re.compile(r"[A-Za-z%s'\u2019]+" % IAST)
# STORIES_UI_2026_10_05: also split after a citation that follows the full stop ("fled. [11.5] Later ...").
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\u201c%s])|(?<=\])\s+(?=[A-Z\"'\u201c%s])" % (IAST, IAST))
OPENERS = "\"'\u201c\u2018:;(\u2014"   # a capital after these starts speech or a clause, not a name
NAME_STOP = {"i", "o", "god", "lord", "king", "sage", "the", "a", "an", "he", "she", "they", "his", "her"}


# ------------------------------------------------------------------ helpers
def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_schema(con) -> None:
    con.executescript(SCHEMA + VARIANT_SCHEMA)   # STORY_VARIANTS_2026_10_07
    con.commit()


def ref(p, i) -> str:
    return "%d.%d" % (int(p), int(i))


def parse_ref(s) -> tuple | None:
    m = REF_RE.search(str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def passages(con, code: str) -> list:
    """[(page, idx, sanskrit, iast, english)] translated, non-noise, in reading order."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
    iast = "COALESCE(p.iast,'')" if "iast" in cols else "''"
    return con.execute(
        """SELECT p.page_no, p.idx, COALESCE(p.text,''), %s, p.translation FROM passages p
           JOIN docs d ON d.id = p.doc_id
           WHERE d.code = ? AND TRIM(COALESCE(p.translation,'')) <> ''
             AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
           ORDER BY p.page_no, p.idx""" % iast, (code,)).fetchall()


def window(rows: list, lo: tuple, hi: tuple, pad: int = 2, cap: int = 40) -> list:
    keys = [(r[0], r[1]) for r in rows]
    a = next((k for k, x in enumerate(keys) if x >= lo), None)
    b = max((k for k, x in enumerate(keys) if x <= hi), default=None)
    if a is None or b is None or b < a:
        return []
    a, b = max(0, a - pad), min(len(rows) - 1, b + pad)
    if b - a + 1 > cap:
        b = a + cap - 1
    return rows[a:b + 1]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _norm_sa(s: str) -> str:
    return re.sub(r"[\s\u0964\u0965|/0-9\u0966-\u096f]+", "", unicodedata.normalize("NFC", s or ""))


def budget_ok(db: str) -> bool:
    try:
        from usage_meter import budget_ok as _b
        return _b(db)
    except Exception:
        return True


# ------------------------------------------------------------------ verify (no API)
def verify(story: dict, given: list) -> dict:
    """Deterministic checks of a written story against the passages it was given."""
    problems = []
    refs = {ref(r[0], r[1]): r for r in given}
    en = story.get("story_en") or ""
    words = len(WORD_RE.findall(en))
    if words < 80 or words > 300:
        problems.append("English length %d words (want 120-220)" % words)
    cited = set()
    for b in BRACKET_RE.findall(en) + BRACKET_RE.findall(story.get("story_hi") or ""):
        for m in REF_RE.finditer(b):
            cited.add(ref(m.group(1), m.group(2)))
    outside = sorted(c for c in cited if c not in refs)
    if outside:
        problems.append("cites outside the passages given: " + ", ".join(outside))
    uncited = [s for s in SENT_RE.split(en.strip()) if len(WORD_RE.findall(s)) >= 4 and not BRACKET_RE.search(s)]
    if uncited:
        problems.append("%d sentence(s) without a citation, e.g. %r" % (len(uncited), uncited[0][:80]))
    q, qr = story.get("quote_sa") or "", ref(*parse_ref(story.get("quote_ref"))) if parse_ref(story.get("quote_ref")) else ""
    if not q:
        problems.append("no Sanskrit quotation")
    elif qr not in refs or _norm_sa(q) not in _norm_sa(refs[qr][2]):
        problems.append("the Sanskrit quotation is not found verbatim in passage %s" % (qr or "?"))
    src = _fold(" ".join("%s %s" % (refs[c][3], refs[c][4]) for c in cited if c in refs))
    unknown = []
    for s in SENT_RE.split(en):
        for k, mt in enumerate(WORD_RE.finditer(s)):   # STORIES_UI_2026_10_05
            t = mt.group(0)
            t2 = t.strip("'\u2019").removesuffix("'s").removesuffix("\u2019s")
            lead = s[:mt.start()].rstrip()[-1:]
            opens = k == 0 or (lead != "" and lead in OPENERS)
            is_name = any(c in IAST for c in t2) or (not opens and t2[:1].isupper())
            if is_name and len(t2) > 2 and t2.lower() not in NAME_STOP and _fold(t2) not in src:
                unknown.append(t2)
    if unknown:
        problems.append("names not found in the cited passages: " + ", ".join(sorted(set(unknown))[:12]))
    return {"ok": not problems, "problems": problems, "cited": sorted(cited, key=parse_ref),
            "words": words, "checked_at": now()}


# ------------------------------------------------------------------ paid steps
def _prompt_block(rows: list, with_sa: bool) -> str:
    out = []
    for p, i, sa, ia, en in rows:
        line = "[%s]" % ref(p, i)
        if with_sa:
            line += "\nSA: " + sa.strip().replace("\n", " ")
        line += "\nEN: " + (en or "").strip().replace("\n", " ")
        out.append(line)
    return "\n\n".join(out)


def mine(con, code: str, did: int, db: str, max_n: int = 12, chunk: int = 150, yes: bool = False,
         http=None) -> list:
    rows = passages(con, code)
    if not rows:
        print("Nothing to mine: no translated passages for %s." % code); return []
    chunks = [rows[i:i + chunk] for i in range(0, len(rows), chunk)]
    chars = sum(len(_prompt_block(c, False)) for c in chunks)
    est = (chars / 4 * 0.30 + len(chunks) * 1500 * 2.50) / 1e6
    print("mine %s: %d passages in %d chunk(s), about %d input tokens, est $%.3f with %s"
          % (code, len(rows), len(chunks), chars // 4, est, MODEL))
    if not yes:
        print("Dry run. Add --yes."); return []
    per = max(2, -(-max_n // len(chunks)))
    have = {im._norm_title(r[0]) for r in con.execute("SELECT title FROM doc_stories WHERE doc_id=?", (did,))}
    made = []
    for n, c in enumerate(chunks, 1):
        if len(made) >= max_n:
            break
        if not budget_ok(db):
            print("Stopping: the spend cap is reached."); break
        valid = {(r[0], r[1]) for r in c}
        t0 = time.time()
        data, resp = im.call_text_json(MODEL, MINE_SYSTEM % per, _prompt_block(c, False), http=http)
        im.meter("story_mine", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=len(c))
        for e in (data.get("episodes") if isinstance(data, dict) else data) or []:
            a, b = parse_ref(e.get("from")), parse_ref(e.get("to"))
            t = (e.get("title") or "").strip()
            if not (a and b and a in valid and b in valid and a <= b and t) or im._norm_title(t) in have:
                continue
            cur = con.execute(
                """INSERT INTO doc_stories(doc_id, status, title, title_hi, why, from_page, from_idx, to_page, to_idx,
                                           model, provenance, created_at, updated_at)
                   VALUES(?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (did, t, e.get("title_hi") or "", e.get("why") or "", a[0], a[1], b[0], b[1], MODEL,
                 json.dumps({"mined_from": [ref(*c[0][:2]), ref(*c[-1][:2])]}), now(), now()))
            have.add(im._norm_title(t)); made.append(cur.lastrowid)
            if len(made) >= max_n:
                break
        con.commit()
        print("  chunk %d/%d: %d candidate(s) so far" % (n, len(chunks), len(made)))
    return made


def write_story(con, sid: int, code: str, db: str, pad: int = 2, http=None, cap: int = 60) -> dict:
    s = dict(zip([c[1] for c in con.execute("PRAGMA table_info(doc_stories)")],
                 con.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone()))
    rows = window(passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=pad, cap=cap)
    if not rows:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)
    user = "Episode: %s\n%s\n\nPASSAGES\n\n%s" % (s.get("title") or "", s.get("why") or "", _prompt_block(rows, True))
    t0 = time.time()
    data, resp = im.call_text_json(MODEL, STORY_SYSTEM, user, http=http)
    im.meter("story", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)
    data = data if isinstance(data, dict) else {}
    v = verify(data, rows)
    ph = hashlib.sha256((MODEL + STORY_SYSTEM + user).encode("utf-8")).hexdigest()[:16]
    con.execute(
        """UPDATE doc_stories SET status='draft', title=COALESCE(NULLIF(?,''), title), title_hi=COALESCE(NULLIF(?,''), title_hi),
             story_en=?, story_hi=?, quote_sa=?, quote_ref=?, notes=?, cites=?, verify=?, model=?, prompt_hash=?,
             provenance=?, updated_at=? WHERE id=?""",
        (data.get("title") or "", data.get("title_hi") or "", data.get("story_en") or "", data.get("story_hi") or "",
         data.get("quote_sa") or "", data.get("quote_ref") or "", data.get("notes") or "",
         json.dumps(v["cited"]), json.dumps(v), MODEL, ph,
         json.dumps({"given": [ref(*rows[0][:2]), ref(*rows[-1][:2])], "n_given": len(rows),
                     "written_at": now()}), now(), sid))
    con.commit()
    return v


def story_for_image(con, image_id: int, before: int = 6, after: int = 6) -> int:
    r = con.execute("""SELECT i.doc_id, i.title, i.context_note, i.anchor_page, i.anchor_idx, i.kind
                       FROM doc_images i WHERE i.id=?""", (image_id,)).fetchone()
    if not r:
        raise SystemExit("FAIL: image #%d not found." % image_id)
    did, title, note, pg, ix, kind = r
    if kind == "cover" or pg is None:
        raise SystemExit("image #%d is a cover or has no anchor; covers carry no story." % image_id)
    old = con.execute("SELECT id FROM doc_stories WHERE image_id=? AND status<>'retired' ORDER BY id DESC",
                      (image_id,)).fetchone()
    if old:
        return old[0]
    code = con.execute("SELECT code FROM docs WHERE id=?", (did,)).fetchone()[0]
    rows = passages(con, code)
    keys = [(x[0], x[1]) for x in rows]
    at = min(range(len(keys)), key=lambda k: (abs(keys[k][0] - pg), abs(keys[k][1] - ix))) if keys else None
    if at is None:
        raise SystemExit("FAIL: %s has no translated passages." % code)
    a, b = keys[max(0, at - before)], keys[min(len(keys) - 1, at + after)]
    cur = con.execute(
        """INSERT INTO doc_stories(doc_id, image_id, status, title, why, from_page, from_idx, to_page, to_idx,
                                   provenance, created_at, updated_at)
           VALUES(?, ?, 'candidate', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (did, image_id, title or "", note or "", a[0], a[1], b[0], b[1],
         json.dumps({"from_image": image_id, "anchor": ref(pg, ix)}), now(), now()))
    con.commit()
    return cur.lastrowid


# ------------------------------------------------------------------ anthology
def _cite_html(text: str) -> str:
    t = html.escape(text or "")
    return BRACKET_RE.sub(lambda m: "<sup class='cite'>[%s]</sup>" % m.group(1), t)


def anthology(con, codes: list, title: str, out: Path) -> tuple:
    import export_html as ex
    try:
        import collections_cfg as cc
        titles = cc.load_titles(ROOT / "configs" / "doc_titles.json")
    except Exception:
        titles = {}
    parts, appendix, n = [], [], 0
    for code in codes:
        did = im.doc_id(con, code)
        book = titles.get(code) or code.replace("_", " ")
        rows = {ref(r[0], r[1]): r for r in passages(con, code)}
        for s in con.execute("""SELECT id, image_id, title, title_hi, story_en, story_hi, quote_sa, quote_ref, notes,
                                       cites, from_page, from_idx, to_page, to_idx FROM doc_stories
                                WHERE doc_id=? AND status='approved' ORDER BY from_page, from_idx""", (did,)).fetchall():
            n += 1
            sid, iid, t, th, en, hi, q, qr, notes, cites, fp, fi, tp, ti = s
            fig = ""
            img = con.execute("""SELECT path, title FROM doc_images WHERE id=? AND status='approved' AND path IS NOT NULL""",
                              (iid,)).fetchone() if iid else None
            if img:
                full = img[0] if os.path.isabs(img[0]) else str(ROOT / img[0])
                uri = ex._fig_embed(full)
                if uri:
                    fig = ("<figure class='plate'><img src='%s' alt='%s'/><figcaption><span class='plate-label'>%s"
                           "</span></figcaption></figure>" % (uri, html.escape(img[1] or t or "", quote=True),
                                                              html.escape(im.GENERATED_LABEL)))
            parts.append(
                "<section class='story' id='s%d'><h2>%d. %s</h2>%s<div class='src'>%s, %s-%s</div>"
                "<blockquote class='sa'>%s<span class='qref'> [%s]</span></blockquote>%s"
                "<div class='en'>%s</div>%s%s</section>"
                % (n, n, html.escape(t or ""), ("<div class='th'>%s</div>" % html.escape(th)) if th else "",
                   html.escape(book), ref(fp, fi), ref(tp, ti), html.escape(q or ""), html.escape(qr or ""), fig,
                   _cite_html(en), ("<div class='hi'>%s</div>" % _cite_html(hi)) if hi else "",
                   ("<div class='notes'>Editorial notes: %s</div>" % html.escape(notes)) if notes else ""))
            for c in json.loads(cites or "[]"):
                r = rows.get(c)
                if r:
                    appendix.append("<tr><td>%s</td><td>%s %s</td><td class='sa'>%s</td><td>%s</td></tr>"
                                    % (n, html.escape(book), c, html.escape(r[2]), html.escape(r[4])))
    css = ("body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#222}"
           "h1{text-align:center}h2{margin-top:3rem}.th,.hi,.sa{font-family:'Nirmala UI','Noto Serif Devanagari',serif}"
           ".src{color:#666;font-size:.9rem}.qref{color:#888;font-size:.8rem}.cite{color:#8a6d1d;font-size:.7rem}"
           "blockquote.sa{border-left:3px solid #c9a24a;padding-left:1rem;margin-left:0}.notes{font-size:.85rem;"
           "color:#7a4b00;background:#fdf6e3;padding:.5rem .8rem;margin-top:.8rem}figure.plate{margin:1rem 0;"
           "text-align:center}figure.plate img{max-width:100%;max-height:70vh}.plate-label{font-size:.75rem;color:#888}"
           "table{border-collapse:collapse;font-size:.85rem}td{border-top:1px solid #ddd;padding:.3rem;vertical-align:top}"
           ".story{page-break-before:always}")
    body = ("<h1>%s</h1><p style='text-align:center;color:#666'>%d retellings, each cited to the passages it rests "
            "on. Illustrations are generated, not historical sources. Retellings were drafted by a model from the "
            "passages and approved by an editor.</p>%s<h2>Sources</h2><table><tr><th>#</th><th>Passage</th>"
            "<th>Sanskrit (as printed)</th><th>English (machine translation)</th></tr>%s</table>"
            % (html.escape(title), n, "".join(parts), "".join(appendix)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s</style>"
                   "</head><body><!-- %s -->%s</body></html>" % (html.escape(title), css, MARK, body), encoding="utf-8")
    return out, n


# ------------------------------------------------------------------ STORY_BOOKS_2026_10_07
ILLUSTRATE_SYSTEM = (
    "You write ONE illustration brief for an episode of a Sanskrit text, for an illustrated, cited anthology. "
    "You are given the episode's passages (tag [page.idx], machine English) and, when there is one, the "
    "editor's retelling and editorial notes. Choose a single concrete moment the passages describe. Add no "
    "people, animals, objects or events that the passages do not give, and do not depict anything the notes "
    "call doubtful or damaged. For any deity or sage, state the iconography (heads, arms, attributes, vehicle, "
    "posture, dress) as the passages or standard iconography give it; if unsure, choose a place, object or act "
    "instead of a figure. Historically plausible dress and architecture; nothing modern; no text in the image. "
    "Respond with one JSON object only: {\"anchor\": \"page.idx\" (one of the tags given: the passage the "
    "moment rests on), \"title\": str (4-9 words), \"brief\": str (what to draw, 40-90 words), "
    "\"context_note\": str (why this moment, citing [page.idx]), \"caption_en\": str, \"caption_hi\": str}")
AUDIENCES = ("young", "teen", "general", "scholar")   # teen: STORY_VARIANTS_2026_10_07


def illustrate(con, sid: int, db: str, http=None, cap: int = 40) -> int:
    """Store one image idea (doc_images status 'brief') for story sid and link it. Returns the image id."""
    s = _row(con, sid)
    if s["status"] == "retired":
        raise SystemExit("FAIL: story #%d is retired." % sid)
    if s.get("image_id"):
        r = con.execute("SELECT status FROM doc_images WHERE id=?", (s["image_id"],)).fetchone()
        if r and r[0] != "retired":
            raise SystemExit("FAIL: story #%d already has image #%d (%s). Retire that image first to propose "
                             "another." % (sid, s["image_id"], r[0]))
    code = _code_of(con, s["doc_id"])
    rows = window(passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=0, cap=cap)
    if not rows:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)
    parts = ["Episode: %s" % (s.get("title") or ""), s.get("why") or ""]
    if (s.get("story_en") or "").strip():
        parts.append("RETELLING (%s):\n%s" % (s["status"], s["story_en"].strip()))
    if (s.get("notes") or "").strip():
        parts.append("EDITORIAL NOTES (do not depict what these doubt):\n%s" % s["notes"].strip())
    user = "\n\n".join(p for p in parts if p) + "\n\nPASSAGES\n\n" + _prompt_block(rows, False)
    t0 = time.time()
    data, resp = im.call_text_json(im.BRIEF_MODEL, ILLUSTRATE_SYSTEM, user, http=http)
    im.meter("image_brief", code, "gemini:" + im.BRIEF_MODEL, resp, db, time.time() - t0)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict) or not str(data.get("brief") or "").strip():
        raise SystemExit("FAIL: the model returned no usable image idea for story #%d." % sid)
    valid = {(r[0], r[1]) for r in rows}
    a = parse_ref(data.get("anchor"))
    if not a or a not in valid:
        mid = rows[len(rows) // 2]
        a = (mid[0], mid[1])
    cur = con.execute(
        """INSERT INTO doc_images(doc_id, kind, status, title, brief, context_note, caption_en, caption_hi,
                                  anchor_page, anchor_idx, model, provenance, created_at, updated_at)
           VALUES(?, 'generated', 'brief', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (s["doc_id"], data.get("title") or s.get("title") or "", data.get("brief"), data.get("context_note") or "",
         data.get("caption_en") or "", data.get("caption_hi") or "", a[0], a[1], im.BRIEF_MODEL,
         json.dumps({"brief_model": im.BRIEF_MODEL, "source": "stories.py illustrate", "story": sid}), now(), now()))
    iid = cur.lastrowid
    con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (iid,))
    con.execute("UPDATE doc_stories SET image_id=?, updated_at=? WHERE id=?", (iid, now(), sid))
    con.commit()
    return iid


def _book_rows(con, ids: list, proof: bool = False) -> list:
    """Stories in the order given; approved only unless proof. Each: (story dict, code, image path or None)."""
    out = []
    for sid in ids:
        try:
            s = _row(con, int(sid))
        except SystemExit:
            continue
        if s["status"] == "approved" or (proof and s["status"] == "draft"):
            code = _code_of(con, s["doc_id"])
            img = None
            if s.get("image_id"):
                r = con.execute("SELECT path, title FROM doc_images WHERE id=? AND path IS NOT NULL AND status IN (%s)"
                                % ("'approved','draft'" if proof else "'approved'"), (s["image_id"],)).fetchone()
                if r:
                    img = (r[0] if os.path.isabs(r[0]) else str(ROOT / r[0]), r[1])
            out.append((s, code, img))
    return out


def _titles():
    try:
        import collections_cfg as cc
        return cc.load_titles(ROOT / "configs" / "doc_titles.json")
    except Exception:
        return {}


def _plain(text: str) -> str:
    """The retelling without its [page.idx] citations (for young readers)."""
    return re.sub(r"\s*\[[^\]]*\d+\.\d+[^\]]*\]", "", text or "")


def book(con, ids: list, title: str, out: Path, audience: str = "general", hindi: bool = True,
         proof: bool = False) -> tuple:
    import export_html as ex
    audience = audience if audience in AUDIENCES else "general"
    titles = _titles()
    rows = _book_rows(con, ids, proof)
    parts, src, n = [], [], 0
    for s, code, img in rows:
        n += 1
        book_t = titles.get(code) or code.replace("_", " ")
        rng = "%s-%s" % (ref(s["from_page"], s["from_idx"]), ref(s["to_page"], s["to_idx"]))
        fig = ""
        if img:
            uri = ex._fig_embed(img[0])
            if uri:
                fig = ("<figure class='plate'><img src='%s' alt='%s'/><figcaption>%s</figcaption></figure>"
                       % (uri, html.escape(img[1] or s.get("title") or "", quote=True), html.escape(im.GENERATED_LABEL)))
        vv = _variant_for(con, s["id"], audience)   # STORY_VARIANTS_2026_10_07
        if vv:
            s = dict(s, title=vv.get("title") or s.get("title"), title_hi=vv.get("title_hi") or s.get("title_hi"),
                     story_en=vv.get("story_en") or "", story_hi=vv.get("story_hi") or "", cites=vv.get("cites"))
        en = s.get("story_en") or ""
        hi = s.get("story_hi") or ""
        body_en = ("<p>%s</p>" % html.escape(_plain(en))) if audience == "young" else ("<div class='en'>%s</div>" % _cite_html(en))
        body_hi = ""
        if hindi and hi:
            body_hi = ("<p class='hi'>%s</p>" % html.escape(_plain(hi))) if audience == "young" else (
                "<div class='hi'>%s</div>" % _cite_html(hi))
        epi = ""
        if s.get("quote_sa"):
            epi = ("<blockquote class='sa'>%s<span class='qref'> [%s]</span></blockquote>"
                   % (html.escape(s["quote_sa"]), html.escape(s.get("quote_ref") or "")))
        notes = ""
        if s.get("notes") and audience not in ("young", "teen"):
            notes = "<div class='notes'>Editorial notes: %s</div>" % html.escape(s["notes"])
        badge = "<div class='proof'>PROOF - not yet approved</div>" if s["status"] != "approved" else ""
        parts.append("<section class='story' id='s%d'>%s<h2>%d. %s</h2>%s<div class='src'>%s, passages %s</div>%s%s%s%s%s"
                     "</section>" % (s["id"], badge, n, html.escape(s.get("title") or ""),
                                     ("<div class='th'>%s</div>" % html.escape(s["title_hi"])) if hindi and s.get("title_hi") else "",
                                     html.escape(book_t), rng, fig if audience == "young" else "", epi,
                                     "" if audience == "young" else fig, body_en, body_hi + notes))
        allp = {ref(r[0], r[1]): r for r in passages(con, code)}
        for c in json.loads(s.get("cites") or "[]"):
            r = allp.get(c)
            if not r:
                continue
            if audience == "scholar":
                src.append("<tr><td>%d</td><td>%s %s</td><td class='sa'>%s</td><td>%s</td></tr>"
                           % (n, html.escape(book_t), c, html.escape(r[2]), html.escape(r[4])))
            else:
                src.append("<tr><td>%d</td><td>%s %s</td><td>%s</td></tr>" % (n, html.escape(book_t), c, html.escape(r[4])))
    base = ("body{font-family:Georgia,'Noto Serif',serif;max-width:44rem;margin:2rem auto;padding:0 1rem;color:#222}"
            ".th,.hi,.sa{font-family:'Nirmala UI','Noto Serif Devanagari',serif}.src{color:#666;font-size:.9rem}"
            ".qref{color:#888;font-size:.8rem}.cite{color:#8a6d1d;font-size:.7rem}figure.plate{margin:1rem 0;"
            "text-align:center}figure.plate img{max-width:100%;max-height:70vh;border-radius:4px}figcaption{font-size:.75rem;"
            "color:#888}blockquote.sa{border-left:3px solid #c9a24a;padding-left:1rem;margin-left:0}.notes{font-size:.85rem;"
            "color:#7a4b00;background:#fdf6e3;padding:.5rem .8rem;margin-top:.8rem}.proof{color:#a33;font-weight:bold;"
            "font-size:.8rem;letter-spacing:.08em}table{border-collapse:collapse;font-size:.85rem}td{border-top:1px solid #ddd;"
            "padding:.3rem;vertical-align:top}.story{page-break-before:always}h1{text-align:center}")
    aud = {"young": "body{font-size:1.25rem;line-height:1.75}h2{font-size:1.7rem;color:#7a3d00}p{margin:.8rem 0}"
                    "figure.plate img{max-height:80vh}",
           "teen": "body{font-size:1.12rem;line-height:1.7}h2{color:#5a3a12}",
           "general": "body{font-size:1.05rem;line-height:1.65}",
           "scholar": "body{font-size:1rem;line-height:1.6}.notes{font-size:.9rem}"}[audience]
    intro = {"young": "Stories retold from an old Sanskrit book. The pictures are new paintings made for this book.",
             "teen": "Episodes retold from a Sanskrit text, each resting on the passages cited after its sentences. "
                     "The pictures are new paintings made for this book, not historical sources.",
             "general": "Retellings, each cited to the passages it rests on. Illustrations are generated, not historical "
                        "sources. Retellings were drafted by a model from the passages and approved by an editor.",
             "scholar": "Retellings with a citation after every sentence, the Sanskrit as printed, the machine English "
                        "of every cited passage, and the editor's notes. Illustrations are generated, not sources."}[audience]
    if src:
        head = ("<tr><th>#</th><th>Passage</th><th>Sanskrit (as printed)</th><th>English (machine translation)</th></tr>"
                if audience == "scholar" else "<tr><th>#</th><th>Passage</th><th>English (machine translation)</th></tr>")
        sources = "<h2>%s</h2><table>%s%s</table>" % ("Where these stories come from" if audience == "young" else "Sources",
                                                     head, "".join(src))
    else:
        sources = ""
    doc_html = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s%s</style></head>"
                "<body><!-- %s audience=%s --><h1>%s</h1><p style='text-align:center;color:#666'>%s</p>%s%s</body></html>"
                % (html.escape(title), base, aud, MARK, audience, html.escape(title), intro, "".join(parts), sources))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc_html, encoding="utf-8")
    return out, n


def booksmith_source(con, ids: list, title: str, out: Path) -> tuple:
    """The chosen APPROVED stories as a Booksmith witness: one section.chapter per story, one div.verse
    (vref = number, title, book and range; sa = the quotation; en, hi = the retelling), and footnotes =
    the cited passages (Sanskrit as printed, machine English) and the editorial notes."""
    titles = _titles()
    secs, n = [], 0
    for s, code, _img in _book_rows(con, ids, False):
        n += 1
        book_t = titles.get(code) or code.replace("_", " ")
        rng = "%s-%s" % (ref(s["from_page"], s["from_idx"]), ref(s["to_page"], s["to_idx"]))
        allp = {ref(r[0], r[1]): r for r in passages(con, code)}
        notes = []
        for k, c in enumerate(json.loads(s.get("cites") or "[]"), 1):
            r = allp.get(c)
            if r:
                notes.append("<li id='n%d-%d'>%s %s: %s | %s</li>" % (n, k, html.escape(book_t), c, html.escape(r[2]),
                                                                    html.escape(r[4])))
        if s.get("notes"):
            notes.append("<li id='n%d-ed'>Editorial note: %s</li>" % (n, html.escape(s["notes"])))
        secs.append("<section class='chapter' id='s%d'><div class='verse'><span class='vref'>%d. %s - %s %s</span>"
                    "<div class='sa'>%s</div><div class='en'>%s</div><div class='hi'>%s</div></div>"
                    "<div class='footnotes'><ol>%s</ol></div></section>"
                    % (s["id"], n, html.escape(s.get("title") or ""), html.escape(book_t), rng,
                       html.escape(s.get("quote_sa") or ""), html.escape(s.get("story_en") or ""),
                       html.escape(s.get("story_hi") or ""), "".join(notes)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title></head><body>"
                   "<!-- %s booksmith witness --><h1>%s</h1>%s</body></html>"
                   % (html.escape(title), MARK, html.escape(title), "".join(secs)), encoding="utf-8")
    return out, n


def _slug(t: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")
    return (s or "stories")[:40]


# ------------------------------------------------------------------ STORY_VARIANTS_2026_10_07
VARIANT_AUDIENCES = ("young", "teen")
VARIANT_SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_story_variants(
  id INTEGER PRIMARY KEY, story_id INTEGER NOT NULL, audience TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', title TEXT, title_hi TEXT, story_en TEXT, story_hi TEXT, notes TEXT,
  cites TEXT, verify TEXT, model TEXT, prompt_hash TEXT, provenance TEXT,
  created_at TEXT, updated_at TEXT, approved_at TEXT, UNIQUE(story_id, audience));
"""
AUDIENCE_SPEC = {
    "young": ("children aged 8 to 12",
              "Use short sentences and everyday words, 150-230 words, past tense. Tell hard moments (death, curses, "
              "war) plainly and gently, without gore."),
    "teen": ("readers aged 13 to 16",
             "Use clear, vivid prose, 180-260 words, past tense. Keep the motives the passages give; no gore."),
}
RETELL_SYSTEM = (
    "You retell ONE episode from a Sanskrit text for %s, for an illustrated book. You are given the passages "
    "(tag [page.idx], the Sanskrit as printed and a machine English translation) and the editor-approved retelling "
    "for adults with its editorial notes. Rules: (1) Use ONLY what the passages say. The approved retelling shows "
    "what the editor accepted; the notes say what to leave out. Add no events, motives, speech, places or "
    "descriptions that the passages do not give. (2) After EVERY sentence, cite the passage(s) it rests on, as "
    "[page.idx] or [page.idx, page.idx]. (3) Give every name exactly as the passages give it, in IAST. Where a word "
    "may be unfamiliar, add a few plain words that explain it (for example 'Samika, a forest sage'), never a new "
    "fact. (4) %s (5) story_hi: the same retelling in simple, natural Hindi, with the same citations. "
    "Respond with JSON only: {\"title\": str, \"title_hi\": str, \"story_en\": str, \"story_hi\": str, "
    "\"notes\": str (what you left out or simplified, and why)}")


def ensure_variants(con) -> None:
    con.executescript(VARIANT_SCHEMA)
    con.commit()


def _variant_row(con, sid: int, audience: str) -> dict | None:
    if "doc_story_variants" not in {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
        return None
    cols = [c[1] for c in con.execute("PRAGMA table_info(doc_story_variants)")]
    r = con.execute("SELECT * FROM doc_story_variants WHERE story_id=? AND audience=?", (sid, audience)).fetchone()
    return dict(zip(cols, r)) if r else None


def _variant_for(con, sid: int, audience: str) -> dict | None:
    """The APPROVED version of story sid for this audience, or None."""
    if audience not in VARIANT_AUDIENCES:
        return None
    v = _variant_row(con, sid, audience)
    return v if v and v["status"] == "approved" else None


def variant_verify(con, s: dict, v: dict) -> dict:
    rows = window(passages(con, _code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                  (s["to_page"], s["to_idx"]), pad=2, cap=60)
    return verify({"story_en": v.get("story_en") or "", "story_hi": v.get("story_hi") or "",
                   "quote_sa": s.get("quote_sa") or "", "quote_ref": s.get("quote_ref") or ""}, rows)


def retell(con, sid: int, audience: str, db: str, http=None, cap: int = 60, force: bool = False) -> dict:
    if audience not in VARIANT_AUDIENCES:
        raise SystemExit("FAIL: audience must be one of %s" % ", ".join(VARIANT_AUDIENCES))
    s = _row(con, sid)
    if s["status"] != "approved" and not (force and s["status"] == "draft"):
        raise SystemExit("FAIL: story #%d is %s; a version for younger readers is made from an approved story "
                         "(--force for a draft)." % (sid, s["status"]))
    ensure_variants(con)
    code = _code_of(con, s["doc_id"])
    rows = window(passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=2, cap=cap)
    if not rows:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % sid)
    who, how = AUDIENCE_SPEC[audience]
    system = RETELL_SYSTEM % (who, how)
    user = ("Episode: %s\n\nAPPROVED RETELLING (for adults):\n%s\n\nEDITORIAL NOTES:\n%s\n\nPASSAGES\n\n%s"
            % (s.get("title") or "", s.get("story_en") or "", s.get("notes") or "(none)", _prompt_block(rows, True)))
    t0 = time.time()
    data, resp = im.call_text_json(MODEL, system, user, http=http)
    im.meter("story", code, "gemini:" + MODEL, resp, db, time.time() - t0, units=1)
    data = data if isinstance(data, dict) else {}
    v = variant_verify(con, s, data)
    ph = hashlib.sha256((MODEL + system + user).encode("utf-8")).hexdigest()[:16]
    con.execute(
        """INSERT INTO doc_story_variants(story_id, audience, status, title, title_hi, story_en, story_hi, notes, cites,
                                          verify, model, prompt_hash, provenance, created_at, updated_at)
           VALUES(?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(story_id, audience) DO UPDATE SET status='draft', title=excluded.title,
             title_hi=excluded.title_hi, story_en=excluded.story_en, story_hi=excluded.story_hi, notes=excluded.notes,
             cites=excluded.cites, verify=excluded.verify, model=excluded.model, prompt_hash=excluded.prompt_hash,
             provenance=excluded.provenance, updated_at=excluded.updated_at, approved_at=NULL""",
        (sid, audience, data.get("title") or s.get("title") or "", data.get("title_hi") or s.get("title_hi") or "",
         data.get("story_en") or "", data.get("story_hi") or "", data.get("notes") or "", json.dumps(v["cited"]),
         json.dumps(v), MODEL, ph, json.dumps({"from_story": sid, "story_status": s["status"], "written_at": now()}),
         now(), now()))
    con.commit()
    return v


# ------------------------------------------------------------------ STORY_RECHECK_2026_10_07
def verify_all(con, code: str, statuses=("draft", "approved")) -> dict:
    """Re-run the check on every written story of a text (and its versions for younger readers).
    No API call. Stores each result; approves nothing. Returns a summary."""
    did = im.doc_id(con, code)
    rows = passages(con, code)
    out = {"checked": 0, "ok": 0, "failed": 0, "now_ok": [], "now_failing": [], "still_failing": [], "variants": 0}
    ph = ",".join("?" * len(statuses))
    ids = [r[0] for r in con.execute(
        "SELECT id FROM doc_stories WHERE doc_id=? AND status IN (%s) AND TRIM(COALESCE(story_en,''))<>'' "
        "ORDER BY from_page, from_idx, id" % ph, (did, *statuses))]
    for sid in ids:
        s = _row(con, sid)
        given = window(rows, (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]), pad=2, cap=60)
        v = verify(s, given)
        try:
            was = (json.loads(s.get("verify") or "null") or {}).get("ok")
        except ValueError:
            was = None
        con.execute("UPDATE doc_stories SET verify=?, updated_at=? WHERE id=?", (json.dumps(v), now(), sid))
        out["checked"] += 1
        out["ok" if v["ok"] else "failed"] += 1
        if v["ok"] and not was:
            out["now_ok"].append(sid)
        elif not v["ok"] and was:
            out["now_failing"].append((sid, v["problems"][0] if v["problems"] else ""))
        elif not v["ok"]:
            out["still_failing"].append((sid, v["problems"][0] if v["problems"] else ""))
        vt = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "doc_story_variants" in vt:
            for (vid,) in con.execute("SELECT id FROM doc_story_variants WHERE story_id=? AND status IN ('draft','approved')",
                                      (sid,)).fetchall():
                cols = [c[1] for c in con.execute("PRAGMA table_info(doc_story_variants)")]
                vrow = dict(zip(cols, con.execute("SELECT * FROM doc_story_variants WHERE id=?", (vid,)).fetchone()))
                vv = variant_verify(con, s, vrow)
                con.execute("UPDATE doc_story_variants SET verify=?, updated_at=? WHERE id=?", (json.dumps(vv), now(), vid))
                out["variants"] += 1
    con.commit()
    return out


# ------------------------------------------------------------------ CLI
def _row(con, sid: int) -> dict:
    cols = [c[1] for c in con.execute("PRAGMA table_info(doc_stories)")]
    r = con.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone()
    if not r:
        raise SystemExit("FAIL: story #%d not found." % sid)
    return dict(zip(cols, r))


def _code_of(con, did: int) -> str:
    return con.execute("SELECT code FROM docs WHERE id=?", (did,)).fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Cited retellings of episodes, for images and anthologies")
    ap.add_argument("--db", default="data/context.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mine"); m.add_argument("--doc", required=True); m.add_argument("--max", type=int, default=12)
    m.add_argument("--chunk", type=int, default=150); m.add_argument("--yes", action="store_true")
    w = sub.add_parser("write"); w.add_argument("--id", type=int); w.add_argument("--image", type=int)
    w.add_argument("--doc"); w.add_argument("--images", action="store_true", help="one story per drawn image of --doc")
    w.add_argument("--candidates", action="store_true", help="write the mined candidates of --doc")
    w.add_argument("--max", type=int, default=6); w.add_argument("--yes", action="store_true")
    w.add_argument("--before", type=int, default=6, help="with --image/--images: passages before the anchor")
    w.add_argument("--after", type=int, default=6, help="with --image/--images: passages after the anchor")
    w.add_argument("--cap", type=int, default=60, help="most passages sent for one story")
    v = sub.add_parser("verify"); v.add_argument("--id", type=int, required=True)
    va_ = sub.add_parser("verify-all"); va_.add_argument("--doc", required=True)   # STORY_RECHECK_2026_10_07
    va_.add_argument("--status", default="draft,approved", help="comma list, default draft,approved")
    ls = sub.add_parser("list"); ls.add_argument("--doc", required=True); ls.add_argument("--status", default=None)
    sh = sub.add_parser("show"); sh.add_argument("--id", type=int, required=True)
    a = sub.add_parser("approve"); a.add_argument("--id", type=int, required=True); a.add_argument("--force", action="store_true")
    r = sub.add_parser("retire"); r.add_argument("--id", type=int, required=True)
    an = sub.add_parser("anthology"); an.add_argument("--docs", required=True); an.add_argument("--title", default=None)
    an.add_argument("--out", default=None)
    il = sub.add_parser("illustrate"); il.add_argument("--id", type=int, required=True)   # STORY_BOOKS_2026_10_07
    il.add_argument("--yes", action="store_true")
    bk = sub.add_parser("book"); bk.add_argument("--ids", required=True); bk.add_argument("--title", required=True)
    bk.add_argument("--audience", default="general", choices=AUDIENCES); bk.add_argument("--no-hindi", action="store_true")
    bk.add_argument("--proof", action="store_true"); bk.add_argument("--out", default=None)
    rt = sub.add_parser("retell"); rt.add_argument("--id", type=int, required=True)   # STORY_VARIANTS_2026_10_07
    rt.add_argument("--audience", required=True, choices=VARIANT_AUDIENCES); rt.add_argument("--yes", action="store_true")
    rt.add_argument("--force", action="store_true", help="also from a draft story")
    va = sub.add_parser("variant"); va.add_argument("--id", type=int, required=True)
    va.add_argument("--audience", required=True, choices=VARIANT_AUDIENCES)
    va.add_argument("--action", required=True, choices=["approve", "force", "retire", "verify"])
    bsx = sub.add_parser("booksmith-source"); bsx.add_argument("--ids", required=True)
    bsx.add_argument("--title", required=True); bsx.add_argument("--out", required=True)
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2

    con = im._connect(args.db)
    try:
        ensure_schema(con)
        if args.cmd == "mine":
            did = im.doc_id(con, args.doc)
            made = mine(con, args.doc, did, args.db, args.max, args.chunk, args.yes)
            if made:
                print("%d candidate(s): %s. Next: list, then write --doc %s --candidates" % (len(made), made, args.doc))
            return 0
        if args.cmd == "write":
            ids = []
            if args.id:
                ids = [args.id]
            elif args.image:
                ids = [story_for_image(con, args.image, args.before, args.after)]
            elif args.doc and args.images:
                did = im.doc_id(con, args.doc)
                for (iid,) in con.execute("""SELECT id FROM doc_images WHERE doc_id=? AND kind='generated'
                                             AND status IN ('draft','approved') AND path IS NOT NULL
                                             ORDER BY anchor_page, anchor_idx""", (did,)).fetchall():
                    ids.append(story_for_image(con, iid, args.before, args.after))
            elif args.doc and args.candidates:
                did = im.doc_id(con, args.doc)
                ids = [x for (x,) in con.execute("SELECT id FROM doc_stories WHERE doc_id=? AND status='candidate' "
                                                  "ORDER BY from_page, from_idx", (did,))]
            else:
                print("give --id, --image, or --doc with --images or --candidates"); return 2
            ids = [i for i in ids if _row(con, i)["status"] in ("candidate", "draft")][:args.max]
            print("write: %d story(ies) with %s, about $0.01 each" % (len(ids), MODEL))
            for i in ids:
                s = _row(con, i)
                print("  #%d  %s-%s  %s" % (i, ref(s["from_page"], s["from_idx"]), ref(s["to_page"], s["to_idx"]),
                                           s["title"] or ""))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            bad = 0
            for i in ids:
                if not budget_ok(args.db):
                    print("Stopping: the spend cap is reached."); break
                s = _row(con, i)
                res = write_story(con, i, _code_of(con, s["doc_id"]), args.db, cap=args.cap)
                print("  #%d %s %s" % (i, "verified" if res["ok"] else "NEEDS REVIEW:", "; ".join(res["problems"])))
                bad += 0 if res["ok"] else 1
            print("Next: show --id N, then approve --id N (a failed check needs --force after you read it).")
            return 0
        if args.cmd == "retell":   # STORY_VARIANTS_2026_10_07
            s = _row(con, args.id)
            print("retell #%d %s for %s with %s, about $0.01" % (args.id, s.get("title") or "",
                                                                 AUDIENCE_SPEC[args.audience][0], MODEL))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if not budget_ok(args.db):
                print("Refusing: the spend cap is reached."); return 1
            res = retell(con, args.id, args.audience, args.db, force=args.force)
            print("  #%d %s: %s %s" % (args.id, args.audience, "verified" if res["ok"] else "NEEDS REVIEW:",
                                       "; ".join(res["problems"])))
            return 0
        if args.cmd == "variant":
            s = _row(con, args.id)
            v = _variant_row(con, args.id, args.audience)
            if not v:
                print("No %s version of #%d yet (retell --id %d --audience %s)." % (args.audience, args.id, args.id,
                                                                                    args.audience)); return 1
            if args.action == "verify":
                res = variant_verify(con, s, v)
                con.execute("UPDATE doc_story_variants SET verify=?, updated_at=? WHERE id=?", (json.dumps(res), now(), v["id"]))
                con.commit(); print(json.dumps(res, ensure_ascii=False, indent=1)); return 0 if res["ok"] else 1
            if args.action == "retire":
                con.execute("UPDATE doc_story_variants SET status='retired', updated_at=? WHERE id=?", (now(), v["id"]))
                con.commit(); print("#%d %s version retired" % (args.id, args.audience)); return 0
            if v["status"] != "draft":
                print("Refusing: the %s version of #%d is %s." % (args.audience, args.id, v["status"])); return 1
            if not (json.loads(v["verify"] or "{}").get("ok")) and args.action != "force":
                print("Refusing: the check failed. Read it; --action force approves anyway."); return 1
            con.execute("UPDATE doc_story_variants SET status='approved', approved_at=?, updated_at=? WHERE id=?",
                        (now(), now(), v["id"]))
            con.commit(); print("#%d %s version approved" % (args.id, args.audience)); return 0
        if args.cmd == "illustrate":   # STORY_BOOKS_2026_10_07
            s = _row(con, args.id)
            print("illustrate #%d %s: one image idea with %s, about $0.003" % (args.id, s.get("title") or "",
                                                                              im.BRIEF_MODEL))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if not budget_ok(args.db):
                print("Refusing: the spend cap is reached."); return 1
            iid = illustrate(con, args.id, args.db)
            print("image idea #%d stored (status brief) and linked to story #%d. Next: approve the idea and draw it "
                  "(Stories page, or images.py approve-brief %d then generate --doc %s --id %d --yes)."
                  % (iid, args.id, iid, _code_of(con, s["doc_id"]), iid))
            return 0
        if args.cmd in ("book", "booksmith-source"):
            ids = [int(x) for x in re.findall(r"\d+", args.ids)]
            if args.cmd == "booksmith-source":
                path, n = booksmith_source(con, ids, args.title, Path(args.out))
                print("wrote %s (%d approved stories, Booksmith witness)" % (path, n)); return 0 if n else 1
            out = Path(args.out) if args.out else ROOT / "exports" / ("book_%s_%s.html" % (
                _slug(args.title), datetime.date.today().strftime("%Y%m%d")))
            path, n = book(con, ids, args.title, out, args.audience, not args.no_hindi, args.proof)
            print("wrote %s (%d stories, audience %s). PDF: python scripts\\export_pdf.py \"%s\"" % (path, n, args.audience, path))
            return 0 if n else 1
        if args.cmd == "verify-all":   # STORY_RECHECK_2026_10_07
            sts = tuple(x.strip() for x in args.status.split(",") if x.strip() in ("draft", "approved"))
            r = verify_all(con, args.doc, sts or ("draft", "approved"))
            print("checked %d stor(ies) of %s (and %d version(s) for younger readers): %d pass, %d fail. No API call."
                  % (r["checked"], args.doc, r["variants"], r["ok"], r["failed"]))
            if r["now_ok"]:
                print("  now passing (read, then approve): " + ", ".join("#%d" % i for i in r["now_ok"]))
            for i, p in r["now_failing"]:
                print("  NOW FAILING #%d: %s" % (i, p))
            for i, p in r["still_failing"]:
                print("  still failing #%d: %s" % (i, p))
            return 0
        if args.cmd == "verify":
            s = _row(con, args.id)
            rows = window(passages(con, _code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                          (s["to_page"], s["to_idx"]), pad=2, cap=60)   # STORY_RECHECK_2026_10_07: as write and the page
            res = verify(s, rows)
            con.execute("UPDATE doc_stories SET verify=?, updated_at=? WHERE id=?", (json.dumps(res), now(), args.id))
            con.commit()
            print(json.dumps(res, ensure_ascii=False, indent=1)); return 0 if res["ok"] else 1
        if args.cmd == "list":
            did = im.doc_id(con, args.doc)
            q = "SELECT id, status, image_id, from_page, from_idx, to_page, to_idx, title, verify FROM doc_stories WHERE doc_id=?"
            p = [did]
            if args.status:
                q += " AND status=?"; p.append(args.status)
            n = 0
            for sid, st, iid, fp, fi, tp, ti, t, vj in con.execute(q + " ORDER BY from_page, from_idx", p):
                ok = (json.loads(vj).get("ok") if vj else None)
                print("%4d  %-9s img=%-5s %8s-%-8s %-6s %s" % (sid, st, iid or "-", ref(fp, fi), ref(tp, ti),
                                                           {True: "ok", False: "CHECK", None: ""}[ok], t or ""))
                n += 1
            print("%d row(s)" % n); return 0
        if args.cmd == "show":
            s = _row(con, args.id)
            for k in ("title", "title_hi", "status", "image_id", "quote_sa", "quote_ref", "story_en", "story_hi", "notes"):
                print("%-9s %s" % (k, s.get(k) or ""))
            print("verify   ", s.get("verify") or "(not written yet)"); return 0
        if args.cmd == "approve":
            s = _row(con, args.id)
            if s["status"] != "draft":
                print("Refusing: #%d is %s; only a written draft can be approved." % (args.id, s["status"])); return 1
            ok = json.loads(s["verify"] or "{}").get("ok")
            if not ok and not args.force:
                print("Refusing: the check failed (show --id %d). Read it; --force approves anyway." % args.id); return 1
            con.execute("UPDATE doc_stories SET status='approved', approved_at=?, updated_at=? WHERE id=?",
                        (now(), now(), args.id)); con.commit()
            print("#%d approved" % args.id); return 0
        if args.cmd == "retire":
            con.execute("UPDATE doc_stories SET status='retired', updated_at=? WHERE id=?", (now(), args.id)); con.commit()
            print("#%d retired" % args.id); return 0
        if args.cmd == "anthology":
            codes = [c.strip() for c in args.docs.split(",") if c.strip()]
            out = Path(args.out) if args.out else ROOT / "exports" / ("anthology_%s.html"
                                                                       % datetime.date.today().strftime("%Y%m%d"))
            path, n = anthology(con, codes, args.title or "Episodes from the Sanskrit corpus", out)
            print("wrote %s (%d approved stories). PDF: python scripts\\export_pdf.py \"%s\"" % (path, n, path))
            return 0
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
