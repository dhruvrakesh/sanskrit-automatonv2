#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
novel.py  (2026-10-07)  NOVEL_2026_10_07

Illustrated graphic-novel pages (8-16) of ONE approved story, made with the Gemini key
this project already uses, and held to the same rule as the stories: nothing is
drawn or captioned without a passage behind it.

  plan   --story N [--pages 12] [--audience young|teen|general] [--yes]
         one text call (about $0.01): the pages in story order, each with what to
         draw (scene), a caption with a [page.idx] citation after every sentence, its
         Hindi, speech only where a passage gives a speaker words, and a cast sheet
         that fixes each recurring figure's look and iconography. Checked like a
         story (citations present and inside the episode, names found in the cited
         passages). Stored as doc_novels (status plan).
  cast   --id K [--yes]          one reference picture per cast member (at most 4)
  draw   --id K [--pages 1-12] [--redo] [--yes]
         one picture per page, the cast sheets given to the image model as
         reference images so figures stay the same from page to page. No lettering
         in any picture: captions and speech are typeset by `build`.
  approve-page --id K --page n | approve --id K [--force] | retire --id K
  build  --id K [--out FILE]     exports/novel_<slug>_<date>.html (PDF: export_pdf.py)
  show   --id K | list [--doc CODE]

Cost: plan about $0.01; each picture about $0.09 at 1K, $0.13 at 2K (images.py's
measured rate); a 12-page novel with 3 cast sheets about $1.4-1.9 before redraws.
Every paid call asks the budget first and is metered (novel_plan, image).
Files: data/images/<doc>/novel_<K>/ (cast_<n>_v<ver>.<ext>, page_<nn>_v<ver>.<ext>).
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import images as im   # noqa: E402
import stories as st  # noqa: E402

MARK = "NOVEL_2026_10_07"
ROOT = Path(__file__).resolve().parents[1]
PLAN_MODEL = os.environ.get("SA_NOVEL_MODEL", st.MODEL)
IMAGE_MODEL = os.environ.get("SA_NOVEL_IMAGE_MODEL", im.IMAGE_MODEL)
ASPECT = os.environ.get("SA_NOVEL_ASPECT", "3:4")
MIN_PAGES, MAX_PAGES, MAX_CAST = 8, 16, 4
AUDIENCES = {"young": "children aged 8 to 12", "teen": "readers aged 13 to 16", "general": "general readers"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_novels(
  id INTEGER PRIMARY KEY, story_id INTEGER NOT NULL, doc_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'plan', audience TEXT, title TEXT, title_hi TEXT, pages INTEGER,
  plan TEXT, verify TEXT, cast_sheets TEXT, page_images TEXT,
  model TEXT, image_model TEXT, aspect TEXT, provenance TEXT,
  created_at TEXT, updated_at TEXT, approved_at TEXT);
CREATE INDEX IF NOT EXISTS ix_doc_novels_story ON doc_novels(story_id);
"""

NOVEL_SYSTEM = (
    "You plan an illustrated graphic novel of %d pages that retells ONE episode from a Sanskrit text, for %s. You "
    "are given the passages (tag [page.idx], the Sanskrit as printed and a machine English translation), the "
    "editor-approved retelling and its editorial notes. Rules: (1) Each page shows one moment that the passages "
    "describe, in story order. Add no events, people, creatures, objects or speech that the passages do not give, "
    "and nothing the notes call doubtful or damaged. (2) caption: one to three short sentences telling that moment, "
    "with its citation [page.idx] after EVERY sentence; caption_hi: the same in simple, natural Hindi with the same "
    "citations. (3) speech: only words a passage gives a speaker, at most one short line per page, as "
    "{\"who\": name, \"line\": words, \"cite\": \"page.idx\"}; otherwise an empty list. (4) scene: what to draw, "
    "40-90 words: setting, figures, poses, expressions, light. Never ask for text, letters or speech balloons in the "
    "picture. (5) cast: every figure who appears on more than one page (at most 4), named exactly as the passages "
    "name them (IAST), with look: a fixed description (age, build, hair, dress, colours, attributes; for deities "
    "and sages the iconography as the passages or standard iconography give it; when unsure, keep it plain). Use "
    "those names in the scenes. Respond with JSON only: {\"title\": str, \"title_hi\": str, \"cast\": [{\"name\": "
    "str, \"look\": str}], \"pages\": [{\"n\": int, \"scene\": str, \"caption\": str, \"caption_hi\": str, "
    "\"speech\": [], \"cites\": [\"page.idx\"]}]}")
NO_TEXT = (" No letters, words, numerals, captions, speech balloons, seals or script-like marks anywhere in the "
           "picture.")


# ------------------------------------------------------------------ storage
def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_schema(con) -> None:
    con.executescript(SCHEMA)
    con.commit()


def get(con, nid: int) -> dict:
    cols = [c[1] for c in con.execute("PRAGMA table_info(doc_novels)")]
    r = con.execute("SELECT * FROM doc_novels WHERE id=?", (nid,)).fetchone()
    if not r:
        raise SystemExit("FAIL: novel #%d not found." % nid)
    d = dict(zip(cols, r))
    for k, empty in (("plan", {}), ("verify", None), ("cast_sheets", {}), ("page_images", {})):
        try:
            d[k] = json.loads(d.get(k) or "null") or empty
        except ValueError:
            d[k] = empty
    return d


def save(con, nid: int, **fields) -> None:
    for k in ("plan", "verify", "cast_sheets", "page_images"):
        if k in fields and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k], ensure_ascii=False)
    fields["updated_at"] = now()
    con.execute("UPDATE doc_novels SET %s WHERE id=?" % ", ".join("%s=?" % k for k in fields),
                list(fields.values()) + [nid])
    con.commit()


def folder(con, n: dict, root: Path | None = None) -> Path:
    code = st._code_of(con, n["doc_id"])
    return (root or ROOT / "data" / "images") / code / ("novel_%d" % n["id"])


def _given(con, s: dict) -> list:
    return st.window(st.passages(con, st._code_of(con, s["doc_id"])), (s["from_page"], s["from_idx"]),
                     (s["to_page"], s["to_idx"]), pad=2, cap=60)


# ------------------------------------------------------------------ checks (no API)
def check_plan(plan: dict, story: dict, given: list, want_pages: int | None = None) -> dict:
    """stories.verify over the captions (and speech), plus the novel's own rules."""
    pages = plan.get("pages") or []
    problems = []
    n = len(pages)
    if not MIN_PAGES <= n <= MAX_PAGES:
        problems.append("%d pages (want %d-%d)" % (n, MIN_PAGES, MAX_PAGES))
    elif want_pages and n != want_pages:
        problems.append("%d pages, asked for %d" % (n, want_pages))
    for k, p in enumerate(pages, 1):
        if not str(p.get("scene") or "").strip():
            problems.append("page %d has no scene" % k)
        for sp in p.get("speech") or []:
            if not st.parse_ref(sp.get("cite")):
                problems.append("page %d: speech without a citation" % k)
    cast = plan.get("cast") or []
    if len(cast) > MAX_CAST:
        problems.append("%d cast members (at most %d)" % (len(cast), MAX_CAST))
    text = " ".join(str(p.get("caption") or "").strip() for p in pages)
    text += " " + " ".join("%s [%s]" % (sp.get("line") or "", sp.get("cite") or "")
                           for p in pages for sp in (p.get("speech") or []))
    v = st.verify({"story_en": text, "story_hi": " ".join(str(p.get("caption_hi") or "") for p in pages),
                   "quote_sa": story.get("quote_sa") or "", "quote_ref": story.get("quote_ref") or ""}, given)
    problems += [x for x in v["problems"] if not x.startswith("English length")]
    return {"ok": not problems, "problems": problems, "cited": v["cited"], "pages": n, "checked_at": now()}


# ------------------------------------------------------------------ paid steps
def _cost_per_image(model: str) -> float:
    _in, out_p = im.IMAGE_PRICING.get(model, (0.5, 60.0))
    tok = im.IMAGE_OUT_TOKENS.get((im.IMAGE_SIZE or "1K").upper(), 1120) + im.IMAGE_OVERHEAD_TOKENS
    return tok * out_p / 1e6


def plan(con, story_id: int, db: str, pages: int = 12, audience: str = "general", http=None) -> int:
    ensure_schema(con)
    s = st._row(con, story_id)
    if s["status"] != "approved":
        raise SystemExit("FAIL: story #%d is %s; a graphic novel is planned from an approved story." % (story_id, s["status"]))
    pages = max(MIN_PAGES, min(MAX_PAGES, int(pages)))
    audience = audience if audience in AUDIENCES else "general"
    given = _given(con, s)
    if not given:
        raise SystemExit("FAIL: story #%d: no translated passages in its range." % story_id)
    code = st._code_of(con, s["doc_id"])
    retold = s.get("story_en") or ""
    vv = st._variant_for(con, story_id, audience) if hasattr(st, "_variant_for") else None
    if vv:
        retold = vv.get("story_en") or retold
    system = NOVEL_SYSTEM % (pages, AUDIENCES[audience])
    user = ("Episode: %s\n\nAPPROVED RETELLING:\n%s\n\nEDITORIAL NOTES:\n%s\n\nPASSAGES\n\n%s"
            % (s.get("title") or "", retold, s.get("notes") or "(none)", st._prompt_block(given, True)))
    t0 = time.time()
    data, resp = im.call_text_json(PLAN_MODEL, system, user, http=http)
    im.meter("novel_plan", code, "gemini:" + PLAN_MODEL, resp, db, time.time() - t0)
    data = data if isinstance(data, dict) else {}
    pl = {"title": data.get("title") or s.get("title") or "", "title_hi": data.get("title_hi") or "",
          "cast": [{"name": str(c.get("name") or "").strip(), "look": str(c.get("look") or "").strip()}
                   for c in (data.get("cast") or [])[:MAX_CAST] if str(c.get("name") or "").strip()],
          "pages": []}
    for k, p in enumerate(data.get("pages") or [], 1):
        pl["pages"].append({"n": k, "scene": str(p.get("scene") or ""), "caption": str(p.get("caption") or ""),
                            "caption_hi": str(p.get("caption_hi") or ""), "speech": list(p.get("speech") or [])[:1],
                            "cites": list(p.get("cites") or [])})
    v = check_plan(pl, s, given, pages)
    cur = con.execute(
        """INSERT INTO doc_novels(story_id, doc_id, status, audience, title, title_hi, pages, plan, verify, cast_sheets,
                                  page_images, model, image_model, aspect, provenance, created_at, updated_at)
           VALUES(?, ?, 'plan', ?, ?, ?, ?, ?, ?, '{}', '{}', ?, ?, ?, ?, ?, ?)""",
        (story_id, s["doc_id"], audience, pl["title"], pl["title_hi"], len(pl["pages"]),
         json.dumps(pl, ensure_ascii=False), json.dumps(v), PLAN_MODEL, IMAGE_MODEL, ASPECT,
         json.dumps({"story": story_id, "variant": bool(vv), "prompt_hash":
                     hashlib.sha256((PLAN_MODEL + system + user).encode("utf-8")).hexdigest()[:16]}), now(), now()))
    con.commit()
    return cur.lastrowid


def call_image_refs(model: str, prompt: str, refs: list, http=None, aspect=None, size=None) -> tuple:
    """images.call_image, with reference pictures given first as inline images."""
    http = http or im.http_json
    gc = {"responseModalities": ["IMAGE"]}
    if aspect or size:
        ic = {k: v for k, v in (("aspectRatio", aspect), ("imageSize", size)) if v}
        if im.IMAGE_CONFIG_FIELD == "responseFormat":
            gc["responseFormat"] = {"image": ic}
        else:
            gc["imageConfig"] = ic
    parts = []
    for label, path in refs:
        p = Path(path)
        mime = {".png": "image/png", ".webp": "image/webp"}.get(p.suffix.lower(), "image/jpeg")
        parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(p.read_bytes()).decode("ascii")}})
        parts.append({"text": "Reference sheet: %s. Keep this figure exactly as shown." % label})
    parts.append({"text": prompt})
    resp = http("%s/models/%s:generateContent" % (im.API, model),
                {"contents": [{"role": "user", "parts": parts}], "generationConfig": gc})
    for cand in resp.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"]), inline.get("mimeType", "image/png"), resp
    finish = ((resp.get("candidates") or [{}])[0]).get("finishReason")
    raise RuntimeError("no image returned (finishReason=%s)" % finish)


def _store(out: Path, stem: str, data: bytes, mime: str) -> dict:
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    out.mkdir(parents=True, exist_ok=True)
    ver = 1 + sum(1 for _ in out.glob(stem + "_v*.*"))
    path = out / ("%s_v%d.%s" % (stem, ver, ext))
    path.write_bytes(data)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "mime": mime, "version": ver,
            "status": "draft", "at": now()}


def draw_cast(con, nid: int, db: str, http=None, root: Path | None = None, redo: bool = False) -> list:
    n = get(con, nid)
    code = st._code_of(con, n["doc_id"])
    sheets = dict(n["cast_sheets"])
    made = []
    for k, c in enumerate(n["plan"].get("cast") or [], 1):
        key = str(k)
        if key in sheets and not redo:
            continue
        if not st.budget_ok(db):
            print("Stopping: the spend cap is reached."); break
        prompt = (im.STYLE + "\n\nCharacter reference sheet for an illustrated book: %s. %s. One full figure, front "
                  "view, standing, plain light background, even light." % (c["name"], c["look"]) + NO_TEXT)
        t0 = time.time()
        data, mime, resp = call_image_refs(n["image_model"] or IMAGE_MODEL, prompt, [], http=http, aspect="3:4",
                                           size=im.IMAGE_SIZE)
        im.meter("image", code, "gemini-image:" + (n["image_model"] or IMAGE_MODEL), resp, db, time.time() - t0)
        sheets[key] = dict(_store(folder(con, n, root), "cast_%d" % k, data, mime), name=c["name"])
        save(con, nid, cast_sheets=sheets)
        made.append(k)
        print("  cast %d %s: %s" % (k, c["name"], sheets[key]["path"]))
    return made


def page_prompt(n: dict, p: dict) -> str:
    cast = "; ".join("%s: %s" % (c["name"], c["look"]) for c in (n["plan"].get("cast") or []))
    return (im.STYLE + "\n\nAn illustrated page of a graphic novel, portrait, one picture filling the page."
            + ("\n\nCAST (keep every figure exactly as in the reference sheets): " + cast if cast else "")
            + "\n\nPAGE %d: %s" % (p.get("n") or 0, p.get("scene") or "") + NO_TEXT)


def draw_pages(con, nid: int, db: str, which: list | None = None, redo: bool = False, http=None,
               root: Path | None = None) -> list:
    n = get(con, nid)
    if n["status"] == "retired":
        raise SystemExit("FAIL: novel #%d is retired." % nid)
    code = st._code_of(con, n["doc_id"])
    imgs = dict(n["page_images"])
    refs = [(sh.get("name") or "figure", sh["path"]) for _k, sh in sorted(n["cast_sheets"].items())
            if sh.get("status") != "retired" and Path(sh.get("path") or "").is_file()]
    made = []
    for p in n["plan"].get("pages") or []:
        key = str(p["n"])
        if which and p["n"] not in which:
            continue
        if key in imgs and not redo and imgs[key].get("status") != "stale":
            continue
        if not st.budget_ok(db):
            print("Stopping: the spend cap is reached."); break
        t0 = time.time()
        data, mime, resp = call_image_refs(n["image_model"] or IMAGE_MODEL, page_prompt(n, p), refs, http=http,
                                           aspect=n.get("aspect") or ASPECT, size=im.IMAGE_SIZE)
        im.meter("image", code, "gemini-image:" + (n["image_model"] or IMAGE_MODEL), resp, db, time.time() - t0)
        imgs[key] = _store(folder(con, n, root), "page_%02d" % p["n"], data, mime)
        save(con, nid, page_images=imgs, status="drawing" if n["status"] == "plan" else n["status"])
        made.append(p["n"])
        print("  page %d: %s (%.1f s)" % (p["n"], imgs[key]["path"], time.time() - t0))
    return made


# ------------------------------------------------------------------ edit / approve (no API)
def edit_page(con, nid: int, page: int, fields: dict) -> dict:
    n = get(con, nid)
    pages = n["plan"].get("pages") or []
    p = next((x for x in pages if x.get("n") == page), None)
    if p is None:
        raise SystemExit("FAIL: novel #%d has no page %d." % (nid, page))
    scene_changed = "scene" in fields and fields["scene"] != p.get("scene")
    for k in ("scene", "caption", "caption_hi"):
        if k in fields:
            p[k] = str(fields[k])[:2000]
    s = st._row(con, n["story_id"])
    v = check_plan(n["plan"], s, _given(con, s), None)
    imgs = dict(n["page_images"])
    if scene_changed and str(page) in imgs:
        imgs[str(page)]["status"] = "stale"     # the picture no longer matches its scene; draw it again
    save(con, nid, plan=n["plan"], verify=v, page_images=imgs,
         status="plan" if n["status"] == "approved" else n["status"], approved_at=None)
    return v


def approve_page(con, nid: int, page: int) -> None:
    n = get(con, nid)
    imgs = dict(n["page_images"])
    if str(page) not in imgs or imgs[str(page)].get("status") == "stale":
        raise SystemExit("FAIL: page %d has no current picture." % page)
    imgs[str(page)]["status"] = "approved"
    save(con, nid, page_images=imgs)


def approve(con, nid: int, force: bool = False) -> None:
    n = get(con, nid)
    pages = [p["n"] for p in n["plan"].get("pages") or []]
    missing = [k for k in pages if (n["page_images"].get(str(k)) or {}).get("status") != "approved"]
    if missing and not force:
        raise SystemExit("FAIL: pages not approved yet: %s" % ", ".join(map(str, missing)))
    if not (n["verify"] or {}).get("ok") and not force:
        raise SystemExit("FAIL: the plan's check failed; read it, then approve with --force.")
    save(con, nid, status="approved", approved_at=now())


# ------------------------------------------------------------------ the book
def build(con, nid: int, out: Path) -> Path:
    import export_html as ex
    n = get(con, nid)
    s = st._row(con, n["story_id"])
    code = st._code_of(con, s["doc_id"])
    book_t = st._titles().get(code) or code.replace("_", " ")
    young = n.get("audience") == "young"
    proof = n["status"] != "approved"
    cap = (lambda t: html.escape(st._plain(t))) if young else st._cite_html
    secs = []
    for p in n["plan"].get("pages") or []:
        img = (n["page_images"].get(str(p["n"])) or {})
        uri = ex._fig_embed(img["path"]) if img.get("path") and Path(img["path"]).is_file() else None
        pic = "<img src='%s' alt='page %d'/>" % (uri, p["n"]) if uri else "<div class='nopic'>picture to come</div>"
        speech = "".join("<div class='say'><b>%s:</b> &ldquo;%s&rdquo;%s</div>"
                         % (html.escape(sp.get("who") or ""), html.escape(sp.get("line") or ""),
                            "" if young else " <sup class='cite'>[%s]</sup>" % html.escape(sp.get("cite") or ""))
                         for sp in p.get("speech") or [])
        secs.append("<section class='pg'>%s<div class='cap'>%s%s<div class='hi'>%s</div></div><div class='no'>%d</div>"
                    "</section>" % (pic, cap(p.get("caption") or ""), speech, cap(p.get("caption_hi") or ""), p["n"]))
    rows = {st.ref(r[0], r[1]): r for r in st.passages(con, code)}
    src = "".join("<tr><td>%s</td><td>%s</td></tr>" % (c, html.escape(rows[c][4]))
                  for c in (n["verify"] or {}).get("cited", []) if c in rows)
    first = (n["page_images"].get("1") or {}).get("path")
    cover_uri = ex._fig_embed(first) if first and Path(first).is_file() else None
    css = ("@page{size:A4;margin:12mm}body{font-family:Georgia,'Noto Serif',serif;margin:0;color:#1d1d1d}"
           ".hi{font-family:'Nirmala UI','Noto Serif Devanagari',serif;color:#444;margin-top:.3rem}"
           ".cover,.pg{page-break-after:always;min-height:95vh;display:flex;flex-direction:column;align-items:center;"
           "justify-content:center;padding:0 6mm}.cover h1{font-size:2.2rem;text-align:center;margin:.6rem 0}"
           ".cover img,.pg img{max-width:100%;max-height:72vh;border-radius:4px}.cap{max-width:42rem;font-size:"
           + ("1.3rem" if young else "1.08rem") + ";line-height:1.55;margin-top:.8rem;background:#fbf6ea;border:1px "
           "solid #e3d4ad;border-radius:6px;padding:.6rem .9rem}.say{margin-top:.4rem;font-style:italic}.no{color:#999;"
           "font-size:.8rem;margin-top:.4rem}.cite{color:#8a6d1d;font-size:.7rem}.nopic{width:60%;height:50vh;border:2px "
           "dashed #ccc;display:flex;align-items:center;justify-content:center;color:#999}.proof{color:#a33;"
           "font-weight:bold;letter-spacing:.08em}table{border-collapse:collapse;font-size:.85rem;margin:0 8mm}td{border-top:"
           "1px solid #ddd;padding:.3rem;vertical-align:top}")
    body = ("<section class='cover'>%s%s<h1>%s</h1>%s<p>A graphic retelling of &ldquo;%s&rdquo;, from %s, passages %s-%s."
            "</p><p style='color:#777;font-size:.85rem'>Every caption rests on the passages cited; the pictures are new "
            "illustrations, not historical sources.</p></section>%s<section><h2 style='margin:8mm'>%s</h2><table>%s"
            "</table></section>"
            % ("<div class='proof'>PROOF - not yet approved</div>" if proof else "",
               "<img src='%s' alt='cover'/>" % cover_uri if cover_uri else "", html.escape(n.get("title") or ""),
               "<div class='hi'>%s</div>" % html.escape(n["title_hi"]) if n.get("title_hi") else "",
               html.escape(s.get("title") or ""), html.escape(book_t), st.ref(s["from_page"], s["from_idx"]),
               st.ref(s["to_page"], s["to_idx"]), "".join(secs),
               "Where this story comes from" if young else "Sources (machine English of the cited passages)", src))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s</style></head>"
                   "<body><!-- %s novel=%d -->%s</body></html>" % (html.escape(n.get("title") or ""), css, MARK, nid, body),
                   encoding="utf-8")
    return out


# ------------------------------------------------------------------ CLI
def _pages_arg(s: str | None) -> list | None:
    if not s:
        return None
    out = []
    for part in s.split(","):
        a, _, b = part.strip().partition("-")
        if a.isdigit():
            out += list(range(int(a), int(b) + 1)) if b.isdigit() else [int(a)]
    return out or None


def main() -> int:
    ap = argparse.ArgumentParser(description="Graphic-novel pages of an approved story")
    ap.add_argument("--db", default="data/context.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--story", type=int, required=True)
    p.add_argument("--pages", type=int, default=12); p.add_argument("--audience", default="general", choices=list(AUDIENCES))
    p.add_argument("--yes", action="store_true")
    c = sub.add_parser("cast"); c.add_argument("--id", type=int, required=True); c.add_argument("--redo", action="store_true")
    c.add_argument("--yes", action="store_true")
    d = sub.add_parser("draw"); d.add_argument("--id", type=int, required=True); d.add_argument("--pages", default=None)
    d.add_argument("--redo", action="store_true"); d.add_argument("--yes", action="store_true")
    ap1 = sub.add_parser("approve-page"); ap1.add_argument("--id", type=int, required=True)
    ap1.add_argument("--page", type=int, required=True)
    a = sub.add_parser("approve"); a.add_argument("--id", type=int, required=True); a.add_argument("--force", action="store_true")
    r = sub.add_parser("retire"); r.add_argument("--id", type=int, required=True)
    b = sub.add_parser("build"); b.add_argument("--id", type=int, required=True); b.add_argument("--out", default=None)
    sh = sub.add_parser("show"); sh.add_argument("--id", type=int, required=True)
    ls = sub.add_parser("list"); ls.add_argument("--doc", default=None)
    args = ap.parse_args()
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    con = im._connect(args.db)
    try:
        ensure_schema(con)
        if args.cmd == "plan":
            s = st._row(con, args.story)
            print("plan story #%d %s: %d pages for %s with %s, about $0.01"
                  % (args.story, s.get("title") or "", args.pages, args.audience, PLAN_MODEL))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if not st.budget_ok(args.db):
                print("Refusing: the spend cap is reached."); return 1
            nid = plan(con, args.story, args.db, args.pages, args.audience)
            n = get(con, nid)
            print("novel #%d planned: %d pages, %d cast; check %s %s" % (nid, len(n["plan"]["pages"]), len(n["plan"]["cast"]),
                  "ok" if n["verify"]["ok"] else "FAILED:", "; ".join(n["verify"]["problems"])))
            print("Next: cast --id %d (about $%.2f), then draw --id %d (about $%.2f)."
                  % (nid, len(n["plan"]["cast"]) * _cost_per_image(n["image_model"]), nid,
                     len(n["plan"]["pages"]) * _cost_per_image(n["image_model"])))
            return 0
        if args.cmd in ("cast", "draw"):
            n = get(con, args.id)
            if args.cmd == "cast":
                todo = [k for k, _c in enumerate(n["plan"].get("cast") or [], 1) if args.redo or str(k) not in n["cast_sheets"]]
            else:
                which = _pages_arg(args.pages)
                todo = [q["n"] for q in n["plan"].get("pages") or [] if (not which or q["n"] in which) and
                        (args.redo or str(q["n"]) not in n["page_images"]
                         or n["page_images"][str(q["n"])].get("status") == "stale")]
            print("%s novel #%d: %d picture(s) with %s at %s, about $%.2f"
                  % (args.cmd, args.id, len(todo), n["image_model"], im.IMAGE_SIZE or "1K",
                     len(todo) * _cost_per_image(n["image_model"])))
            if not args.yes:
                print("Dry run. Add --yes."); return 0
            if args.cmd == "cast":
                made = draw_cast(con, args.id, args.db, redo=args.redo)
            else:
                made = draw_pages(con, args.id, args.db, _pages_arg(args.pages), args.redo)
            print("%d picture(s) made." % len(made)); return 0
        if args.cmd == "approve-page":
            approve_page(con, args.id, args.page); print("novel #%d page %d approved" % (args.id, args.page)); return 0
        if args.cmd == "approve":
            approve(con, args.id, args.force); print("novel #%d approved" % args.id); return 0
        if args.cmd == "retire":
            get(con, args.id); save(con, args.id, status="retired"); print("novel #%d retired" % args.id); return 0
        if args.cmd == "build":
            n = get(con, args.id)
            out = Path(args.out) if args.out else ROOT / "exports" / ("novel_%s_%s.html" % (
                st._slug(n.get("title") or "novel"), datetime.date.today().strftime("%Y%m%d")))
            path = build(con, args.id, out)
            print("wrote %s. PDF: python scripts\\export_pdf.py \"%s\"" % (path, path)); return 0
        if args.cmd == "show":
            print(json.dumps(get(con, args.id), ensure_ascii=False, indent=1)); return 0
        if args.cmd == "list":
            q = "SELECT n.id, d.code, n.story_id, n.status, n.pages, n.title FROM doc_novels n JOIN docs d ON d.id=n.doc_id"
            rows = con.execute(q + (" WHERE d.code=?" if args.doc else "") + " ORDER BY n.id",
                               (args.doc,) if args.doc else ()).fetchall()
            for r in rows:
                print("%4d  %-30s story %-4d %-9s %2s pages  %s" % r)
            print("%d novel(s)" % len(rows)); return 0
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
