#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
images.py  (2026-10-03)  IMAGE_LIBRARY_2026_10_03   (phase I1 of docs/EDITIONS_AND_IMAGES_2026-10-03.md)

A managed, per-text library of illustrations: briefs proposed from the text,
approved by a person, generated ONCE, captioned in English and Hindi, anchored
to a verse, versioned, and never deleted (retired instead - the Srangam
media-asset semantics). Nothing here ever generates on view or on click.

    brief --(approve-brief)--> brief-approved --(generate)--> draft --(approve)--> approved
      any status --(retire)--> retired          approved --(regenerate)--> new version (draft)

Files: data/images/<doc>/<id>_v<version>.<ext>   (gitignored; included in backups)
Table: doc_images in data/context.db (additive; created by `init`)

  python scripts\\images.py init
  python scripts\\images.py models                                  # image-capable models on this key
  python scripts\\images.py brief    --doc Mallapurana --max 6        # dry run: prompt size + cost
  python scripts\\images.py brief    --doc Mallapurana --max 6 --yes  # stores proposals as status 'brief'
  python scripts\\images.py list     --doc Mallapurana
  python scripts\\images.py edit     7 --title "..." --caption-en "..." --caption-hi "..." --anchor 46.3
  python scripts\\images.py approve-brief 7
  python scripts\\images.py generate --doc Mallapurana               # dry run
  python scripts\\images.py generate --doc Mallapurana --yes         # one call per approved brief, cached
  python scripts\\images.py approve 7        |  retire 7  |  regenerate 7 --yes
  python scripts\\images.py add --doc Mallapurana --file scan.png --kind edition-plate --anchor 12.1 --title "..."
  python scripts\\images.py manifest --doc Mallapurana               # approved images as JSON (for the export)

Every generated image is labelled in its record and its caption as a generated
illustration, not a historical source.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass

MARK = "IMAGE_LIBRARY_2026_10_03"  # + IMAGE_DEDUPE_2026_10_03
API = "https://generativelanguage.googleapis.com/v1beta"
IMAGE_MODEL = os.environ.get("SA_IMAGE_MODEL", "gemini-3.1-flash-image")
BRIEF_MODEL = os.environ.get("SA_BRIEF_MODEL", "gemini-2.5-flash")
HARD_CAP = 12
# USD per 1M tokens (input, output). Image output is billed as tokens. From the
# Gemini pricing page as read 2026-10-03 (3.1 models); 2.5-flash-image as of 2025.
IMAGE_PRICING = {"gemini-3.1-flash-image": (0.50, 60.00), "gemini-3.1-flash-lite-image": (0.25, 30.00),
                 "gemini-2.5-flash-image": (0.30, 30.00)}
STYLE = ("Illustration for a scholarly reading edition of a Sanskrit text. Style: restrained line and wash "
         "in the manner of Indian manuscript painting, muted natural pigments, plain parchment ground, "
         "generous margins. No letters, words, numerals or captions anywhere in the image. Historically "
         "plausible dress, objects and architecture; nothing modern. Respectful depiction of persons and "
         "deities; no caricature.")
GENERATED_LABEL = "Illustration - generated, not a historical source."
STATUSES = ("brief", "brief-approved", "draft", "approved", "retired")

SCHEMA = """
CREATE TABLE IF NOT EXISTS doc_images(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id           INTEGER NOT NULL,
  lineage_id       INTEGER,            -- id of the first version; all versions share it
  version          INTEGER NOT NULL DEFAULT 1,
  kind             TEXT NOT NULL DEFAULT 'generated',   -- generated | edition-plate | diagram | photo
  status           TEXT NOT NULL DEFAULT 'brief',       -- brief | brief-approved | draft | approved | retired
  title            TEXT,
  brief            TEXT,               -- what the image should show (for generated)
  context_note     TEXT,               -- why it belongs at this point of the text
  caption_en       TEXT,
  caption_hi       TEXT,
  anchor_page      INTEGER,
  anchor_idx       INTEGER,
  anchor_verse_ref TEXT,
  path             TEXT,
  sha256           TEXT,
  mime             TEXT,
  width            INTEGER,
  height           INTEGER,
  model            TEXT,
  prompt_hash      TEXT,
  provenance       TEXT,               -- JSON
  license          TEXT,
  created_at       TEXT,
  updated_at       TEXT,
  approved_at      TEXT,
  retired_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_images_doc ON doc_images(doc_id, status);
CREATE INDEX IF NOT EXISTS idx_doc_images_hash ON doc_images(prompt_hash);
"""


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def doc_id(con: sqlite3.Connection, code: str) -> int:
    r = con.execute("SELECT id FROM docs WHERE code=?", (code,)).fetchone()
    if not r:
        raise SystemExit("FAIL: doc %r not found." % code)
    return r[0]


def prompt_for(brief: str) -> str:
    return STYLE + "\n\nSubject: " + (brief or "").strip()


def prompt_hash(model: str, brief: str) -> str:
    return hashlib.sha256((model + "\x00" + prompt_for(brief)).encode("utf-8")).hexdigest()


def get(con, image_id: int) -> dict:
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM doc_images WHERE id=?", (image_id,)).fetchone()
    con.row_factory = None
    if not r:
        raise SystemExit("FAIL: image %d not found." % image_id)
    return dict(r)


def set_status(con, image_id: int, status: str, **fields) -> None:
    assert status in STATUSES
    cur = con.execute("SELECT status FROM doc_images WHERE id=?", (image_id,)).fetchone()
    was = cur[0] if cur else None
    fields["status"] = status
    fields["updated_at"] = now()
    if status == "approved" and was != "approved":
        fields["approved_at"] = now()
    if status == "retired" and was != "retired":
        fields["retired_at"] = now()
    cols = ", ".join("%s=?" % k for k in fields)
    con.execute("UPDATE doc_images SET %s WHERE id=?" % cols, list(fields.values()) + [image_id])
    con.commit()


# ------------------------------------------------------------------ the API
class _Usage:
    """Adapter so usage_meter.usage_from_response() can read REST usageMetadata."""
    def __init__(self, um: dict):
        self.usage_metadata = type("U", (), {
            "prompt_token_count": um.get("promptTokenCount"),
            "candidates_token_count": um.get("candidatesTokenCount"),
            "thoughts_token_count": um.get("thoughtsTokenCount") or 0})()


def _key() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise SystemExit("FAIL: GEMINI_API_KEY not set (.env).")
    return k


def http_json(url: str, body: dict | None = None, timeout: int = 180) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": _key()})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 503, 504) and attempt < 2:
                time.sleep(4 * (attempt + 1)); continue
            raise SystemExit("FAIL: HTTP %d from the API: %s" % (e.code, msg))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(4 * (attempt + 1)); continue
            raise SystemExit("FAIL: network error: %s" % e)
    return {}


def meter(kind: str, doc: str, engine: str, resp: dict, db: str, duration: float, units: int = 1) -> float:
    try:
        import cost_tracker
        from usage_meter import meter as _m
        model = engine.split(":", 1)[-1]
        if model in IMAGE_PRICING:
            cost_tracker._PRICING.setdefault(engine, IMAGE_PRICING[model])   # runtime only; file unchanged
        return _m(kind=kind, doc=doc, engine=engine, resp=_Usage(resp.get("usageMetadata") or {}),
                  units=units, duration_s=duration, db=db)
    except Exception as e:
        print("  [meter] not recorded: %s" % e)
        return 0.0


def call_image(model: str, prompt: str, http=None) -> tuple[bytes, str, dict]:
    http = http or http_json
    resp = http("%s/models/%s:generateContent" % (API, model),
                {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                 "generationConfig": {"responseModalities": ["IMAGE"]}})
    for cand in resp.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"]), inline.get("mimeType", "image/png"), resp
    finish = ((resp.get("candidates") or [{}])[0]).get("finishReason")
    raise RuntimeError("no image returned (finishReason=%s)" % finish)


def call_text_json(model: str, system: str, user: str, http=None) -> tuple[object, dict]:
    http = http or http_json
    resp = http("%s/models/%s:generateContent" % (API, model),
                {"systemInstruction": {"parts": [{"text": system}]},
                 "contents": [{"role": "user", "parts": [{"text": user}]}],
                 "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}})
    text = "".join(p.get("text", "") for c in resp.get("candidates") or []
                   for p in (c.get("content") or {}).get("parts") or [])
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(text), resp


# --------------------------------------------------------------- the briefs
BRIEF_SYSTEM = (
    "You select a FEW places in a Sanskrit text where an illustration would genuinely help a reader, "
    "and write an image brief for each. Prefer concrete, depictable scenes, objects, postures, places or "
    "processes that the text itself describes. Never illustrate doctrine as if it were evidence; never "
    "invent events. Respond with a JSON array only. Each item: {\"page\": int, \"idx\": int, "
    "\"title\": str, \"brief\": str (what to draw, 40-90 words, no text in the image), "
    "\"context_note\": str (why here, citing the passage), \"caption_en\": str, \"caption_hi\": str}.")


def gather_text(con, code: str, budget_chars: int = 40000, sections: int = 24) -> tuple[str, set]:
    rows = con.execute(
        """SELECT p.page_no, p.idx, COALESCE(p.verse_ref,''), p.translation FROM passages p JOIN docs d ON d.id=p.doc_id
           WHERE d.code=? AND TRIM(COALESCE(p.translation,''))<>''
             AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')
           ORDER BY p.page_no, p.idx""", (code,)).fetchall()
    valid = {(r[0], r[1]) for r in rows}
    if not rows:
        return "", valid
    step = max(1, len(rows) // sections)
    per = max(400, budget_chars // max(1, min(sections, len(rows))))
    out, used = [], 0
    for i in range(0, len(rows), step):
        chunk = rows[i:i + step]
        txt = " ".join("[p%d.%d] %s" % (r[0], r[1], r[3].strip()) for r in chunk)[:per]
        out.append(txt); used += len(txt)
        if used >= budget_chars:
            break
    return "\n\n".join(out), valid


def snap_anchor(valid: set, page: int, idx: int) -> tuple[int, int] | None:
    if (page, idx) in valid:
        return page, idx
    same = sorted(i for p, i in valid if p == page)
    if same:
        return page, min(same, key=lambda i: abs(i - idx))
    return None


def _norm_title(t) -> str:
    return re.sub(r"[^a-z]", "", (t or "").lower())


def open_briefs(con, code: str) -> int:
    did = doc_id(con, code)
    return con.execute("SELECT COUNT(*) FROM doc_images WHERE doc_id=? AND status IN ('brief','brief-approved')",
                       (did,)).fetchone()[0]


def dedupe(con, code: str, apply: bool = False) -> list[tuple]:
    """IMAGE_DEDUPE_2026_10_03: among not-yet-generated rows (brief / brief-approved) of a
    doc, keep the FIRST at each anchor and retire later ones at the same anchor.
    Returns [(retired_id, kept_id, page, idx)]. Generated / approved rows are never touched."""
    did = doc_id(con, code)
    rows = con.execute("""SELECT id, anchor_page, anchor_idx FROM doc_images WHERE doc_id=?
                          AND status IN ('brief','brief-approved') ORDER BY id""", (did,)).fetchall()
    first, out = {}, []
    for iid, pg, ix in rows:
        key = (pg, ix)
        if key in first:
            out.append((iid, first[key], pg, ix))
        else:
            first[key] = iid
    if apply:
        for iid, *_ in out:
            set_status(con, iid, "retired")
    return out


def store_briefs(con, code: str, items: list, valid: set, max_n: int, model: str) -> list[int]:
    did = doc_id(con, code)
    ids = []
    for it in items[:max_n]:
        try:
            a = snap_anchor(valid, int(it.get("page")), int(it.get("idx", 1)))
        except Exception:
            a = None
        if not a or not str(it.get("brief") or "").strip():
            continue
        dup = con.execute("""SELECT title FROM doc_images WHERE doc_id=? AND anchor_page=? AND anchor_idx=?
                             AND status<>'retired'""", (did, a[0], a[1])).fetchall()
        if any(_norm_title(t) == _norm_title(it.get("title")) for (t,) in dup):
            continue   # IMAGE_DEDUPE_2026_10_03: same idea at the same verse already exists
        cur = con.execute(
            """INSERT INTO doc_images(doc_id, kind, status, title, brief, context_note, caption_en, caption_hi,
                                      anchor_page, anchor_idx, model, provenance, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (did, "generated", "brief", it.get("title"), it.get("brief"), it.get("context_note"),
             it.get("caption_en"), it.get("caption_hi"), a[0], a[1], model,
             json.dumps({"brief_model": model, "source": "images.py brief"}), now(), now()))
        con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (cur.lastrowid,))
        ids.append(cur.lastrowid)
    con.commit()
    return ids


# ---------------------------------------------------------------- generation
def generate_one(con, row: dict, model: str, root: Path, code: str, db: str, http=None) -> int:
    ph = prompt_hash(model, row["brief"] or "")
    cached = con.execute("SELECT path, sha256, mime, width, height FROM doc_images WHERE prompt_hash=? "
                         "AND path IS NOT NULL AND id<>? LIMIT 1", (ph, row["id"])).fetchone()
    if cached and Path(cached[0]).exists():
        print("  #%d: identical brief already generated - reusing %s (no API call)" % (row["id"], cached[0]))
        set_status(con, row["id"], "draft", path=cached[0], sha256=cached[1], mime=cached[2],
                   width=cached[3], height=cached[4], prompt_hash=ph, model=model)
        return row["id"]
    t0 = time.time()
    data, mime, resp = call_image(model, prompt_for(row["brief"] or ""), http=http)
    meter("image", code, "gemini-image:" + model, resp, db, time.time() - t0)
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    folder = root / code
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("%d_v%d.%s" % (row["id"], row["version"], ext))
    path.write_bytes(data)
    w = h = None
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        pass
    prov = json.loads(row.get("provenance") or "{}")
    prov.update({"image_model": model, "prompt": prompt_for(row["brief"] or ""), "generated_at": now(),
                 "label": GENERATED_LABEL})
    set_status(con, row["id"], "draft", path=str(path), sha256=hashlib.sha256(data).hexdigest(), mime=mime,
               width=w, height=h, prompt_hash=ph, model=model, provenance=json.dumps(prov, ensure_ascii=False))
    print("  #%d: generated %s (%s x %s, %.0f KB, %.1f s)" % (row["id"], path, w, h, len(data) / 1024, time.time() - t0))
    return row["id"]


def approve(con, image_id: int) -> None:
    row = get(con, image_id)
    if row["status"] != "draft" or not row["path"]:
        raise SystemExit("FAIL: only a 'draft' with an image can be approved (#%d is %s)." % (image_id, row["status"]))
    for (other,) in con.execute("SELECT id FROM doc_images WHERE lineage_id=? AND status='approved' AND id<>?",
                                (row["lineage_id"], image_id)).fetchall():
        set_status(con, other, "retired")       # one approved version per lineage
    set_status(con, image_id, "approved")


def new_version(con, image_id: int) -> int:
    row = get(con, image_id)
    v = con.execute("SELECT MAX(version) FROM doc_images WHERE lineage_id=?", (row["lineage_id"],)).fetchone()[0]
    cur = con.execute(
        """INSERT INTO doc_images(doc_id, lineage_id, version, kind, status, title, brief, context_note, caption_en,
                                  caption_hi, anchor_page, anchor_idx, anchor_verse_ref, model, provenance,
                                  created_at, updated_at)
           VALUES(?,?,?,?,'brief-approved',?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["doc_id"], row["lineage_id"], (v or 1) + 1, row["kind"], row["title"], row["brief"], row["context_note"],
         row["caption_en"], row["caption_hi"], row["anchor_page"], row["anchor_idx"], row["anchor_verse_ref"],
         row["model"], row["provenance"], now(), now()))
    con.commit()
    return cur.lastrowid


def manifest(con, code: str) -> list[dict]:
    did = doc_id(con, code)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM doc_images WHERE doc_id=? AND status='approved' ORDER BY anchor_page, anchor_idx", (did,))]
    con.row_factory = None
    out = []
    for r in rows:
        cap_en = r["caption_en"] or ""
        if r["kind"] == "generated":
            cap_en = (cap_en + " " if cap_en else "") + "(" + GENERATED_LABEL + ")"
        out.append({"id": r["id"], "version": r["version"], "page": r["anchor_page"], "idx": r["anchor_idx"],
                    "kind": r["kind"], "title": r["title"], "path": r["path"], "caption_en": cap_en,
                    "caption_hi": r["caption_hi"], "context_note": r["context_note"], "sha256": r["sha256"]})
    return out


# ---------------------------------------------------------------------- CLI
def _connect(db: str) -> sqlite3.Connection:
    try:
        from db_utils import connect
        con = connect(db)
        con.execute("PRAGMA busy_timeout=30000")
        return con
    except Exception:
        con = sqlite3.connect(db, timeout=30); con.execute("PRAGMA busy_timeout=30000"); return con


def _print_rows(con, code: str, status: str | None) -> None:
    did = doc_id(con, code)
    q = "SELECT id, version, status, kind, anchor_page, anchor_idx, title, path FROM doc_images WHERE doc_id=?"
    p = [did]
    if status:
        q += " AND status=?"; p.append(status)
    rows = con.execute(q + " ORDER BY anchor_page, anchor_idx, version", p).fetchall()
    print("%-5s %-3s %-15s %-14s %-9s %s" % ("id", "v", "status", "kind", "anchor", "title"))
    for r in rows:
        print("%-5d %-3d %-15s %-14s %-9s %s%s" % (r[0], r[1], r[2], r[3], "%s.%s" % (r[4], r[5]), (r[6] or "")[:60],
                                                "" if r[7] else "   (no image yet)"))
    print("%d row(s)" % len(rows))


def main() -> int:
    ap = argparse.ArgumentParser(description="Managed per-text image library (I1)")
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--root", default="data/images")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("models")
    b = sub.add_parser("brief"); b.add_argument("--doc", required=True); b.add_argument("--max", type=int, default=6)
    b.add_argument("--model", default=BRIEF_MODEL); b.add_argument("--yes", action="store_true")
    b.add_argument("--more", action="store_true", help="ask again although unreviewed briefs exist")
    ls = sub.add_parser("list"); ls.add_argument("--doc", required=True); ls.add_argument("--status", default=None)
    e = sub.add_parser("edit"); e.add_argument("id", type=int)
    for f in ("title", "brief", "context", "caption-en", "caption-hi", "anchor", "license"):
        e.add_argument("--" + f, default=None)
    for name in ("approve-brief", "approve", "retire"):
        s = sub.add_parser(name); s.add_argument("id", type=int, nargs="+")
    dd = sub.add_parser("dedupe"); dd.add_argument("--doc", required=True); dd.add_argument("--yes", action="store_true")
    g = sub.add_parser("generate"); g.add_argument("--doc", required=True); g.add_argument("--id", type=int, default=None)
    g.add_argument("--model", default=IMAGE_MODEL); g.add_argument("--yes", action="store_true")
    r = sub.add_parser("regenerate"); r.add_argument("id", type=int); r.add_argument("--model", default=IMAGE_MODEL)
    r.add_argument("--yes", action="store_true")
    a = sub.add_parser("add"); a.add_argument("--doc", required=True); a.add_argument("--file", required=True)
    a.add_argument("--kind", default="edition-plate", choices=["edition-plate", "diagram", "photo", "generated"])
    a.add_argument("--anchor", required=True); a.add_argument("--title", default=None)
    a.add_argument("--caption-en", default=None); a.add_argument("--caption-hi", default=None)
    a.add_argument("--context", default=None); a.add_argument("--license", default=None)
    m = sub.add_parser("manifest"); m.add_argument("--doc", required=True)
    args = ap.parse_args()

    if args.cmd == "models":
        res = http_json("%s/models?pageSize=200" % API)
        names = [x["name"].split("/", 1)[-1] for x in res.get("models", [])]
        print("image-capable (by name):", ", ".join(n for n in names if "image" in n) or "(none listed)")
        print("current default IMAGE_MODEL:", IMAGE_MODEL, "(override with SA_IMAGE_MODEL or --model)")
        return 0
    if not Path(args.db).exists():
        print("FAIL: %s not found. Run from the repo root." % args.db); return 2
    con = _connect(args.db)
    try:
        ensure_schema(con)
        root = Path(args.root)
        if args.cmd == "init":
            n = con.execute("SELECT COUNT(*) FROM doc_images").fetchone()[0]
            print("doc_images ready (%d rows). Files under %s\\<doc>\\." % (n, root)); return 0
        if args.cmd == "list":
            _print_rows(con, args.doc, args.status); return 0
        if args.cmd == "manifest":
            print(json.dumps(manifest(con, args.doc), ensure_ascii=False, indent=1)); return 0
        if args.cmd == "dedupe":
            res = dedupe(con, args.doc, apply=args.yes)
            for iid, kept, pg, ix in res:
                print("  #%d duplicates #%d at %s.%s%s" % (iid, kept, pg, ix, " -> retired" if args.yes else ""))
            print("%d duplicate(s)%s" % (len(res), "" if args.yes else ". Dry run; add --yes to retire them."))
            return 0
        if args.cmd == "brief":
            n = min(max(1, args.max), HARD_CAP)
            pending = open_briefs(con, args.doc)
            if pending and not args.more:
                print("REFUSING: %s already has %d unreviewed brief(s). Review them first "
                      "(`list`, `approve-brief`, `retire`), or pass --more." % (args.doc, pending))
                return 1
            text, valid = gather_text(con, args.doc)
            if not text:
                print("FAIL: no translated passages for %s." % args.doc); return 1
            user = ("Text: %s\nPropose at most %d illustrations, spread through the text, fewer if fewer are "
                    "warranted. Anchors must be [pPAGE.IDX] markers that appear below.\n\n%s" % (args.doc, n, text))
            print("brief: %s  up to %d  model %s  prompt %d chars (~%d tokens)" % (args.doc, n, args.model,
                                                                                len(user), len(user) // 4))
            if not args.yes:
                print("Dry run. Add --yes to ask the model. Nothing was written."); return 0
            t0 = time.time()
            items, resp = call_text_json(args.model, BRIEF_SYSTEM, user)
            meter("image_brief", args.doc, "gemini:" + args.model, resp, args.db, time.time() - t0)
            ids = store_briefs(con, args.doc, items if isinstance(items, list) else [], valid, n, args.model)
            print("stored %d brief(s): %s" % (len(ids), ids))
            _print_rows(con, args.doc, "brief"); return 0
        if args.cmd == "edit":
            row = get(con, args.id); f = {}
            for k, col in (("title", "title"), ("brief", "brief"), ("context", "context_note"),
                           ("caption_en", "caption_en"), ("caption_hi", "caption_hi"), ("license", "license")):
                v = getattr(args, k)
                if v is not None:
                    f[col] = v
            if args.anchor:
                pg, _, ix = args.anchor.partition(".")
                f["anchor_page"], f["anchor_idx"] = int(pg), int(ix or 1)
            if "brief" in f and row["status"] in ("draft", "approved"):
                print("NOTE: the brief changed after generation; use `regenerate` to make a new version.")
            set_status(con, args.id, row["status"], **f)
            print("updated #%d" % args.id); return 0
        if args.cmd == "approve-brief":
            bad = 0
            for i in args.id:
                row = get(con, i)
                if row["status"] != "brief":
                    print("  skip #%d: it is %s, not 'brief'" % (i, row["status"])); bad += 1; continue
                set_status(con, i, "brief-approved"); print("  #%d brief approved" % i)
            return 1 if bad else 0
        if args.cmd == "approve":
            for i in args.id:
                approve(con, i); print("  #%d approved" % i)
            return 0
        if args.cmd == "retire":
            for i in args.id:
                get(con, i); set_status(con, i, "retired"); print("  #%d retired (file kept)" % i)
            return 0
        if args.cmd in ("generate", "regenerate"):
            if args.cmd == "regenerate":
                new = new_version(con, args.id) if args.yes else None
                if not args.yes:
                    print("Dry run: would create version +1 of #%d and generate it once." % args.id); return 0
                todo = [get(con, new)]; code = con.execute(
                    "SELECT code FROM docs WHERE id=?", (todo[0]["doc_id"],)).fetchone()[0]
            else:
                code = args.doc; did = doc_id(con, code)
                q = "SELECT id FROM doc_images WHERE doc_id=? AND status='brief-approved'"
                p = [did]
                if args.id:
                    q += " AND id=?"; p.append(args.id)
                todo = [get(con, i) for (i,) in con.execute(q, p).fetchall()]
            if not todo:
                print("Nothing to generate (approve a brief first)."); return 0
            in_p, out_p = IMAGE_PRICING.get(args.model, (0.5, 60.0))
            print("generate: %d image(s) with %s, ~$%.3f each (about 1,300 output tokens at $%.0f/M)"
                  % (len(todo), args.model, 1300 * out_p / 1e6, out_p))
            if args.cmd == "generate" and not args.yes:
                for t in todo:
                    print("  would generate #%d p%s.%s %s" % (t["id"], t["anchor_page"], t["anchor_idx"], t["title"]))
                print("Dry run. Add --yes. Each image is generated once and cached."); return 0
            try:
                from usage_meter import budget_ok
                if not budget_ok(args.db):
                    print("Refusing: the spend cap is reached."); return 1
            except Exception:
                pass
            bad = 0
            for t in todo:
                try:
                    generate_one(con, t, args.model, root, code, args.db)
                except Exception as ex:
                    bad += 1; print("  #%d: FAILED %s" % (t["id"], ex))
            return 1 if bad else 0
        if args.cmd == "add":
            did = doc_id(con, args.doc)
            src = Path(args.file)
            if not src.exists():
                print("FAIL: %s not found." % src); return 2
            pg, _, ix = args.anchor.partition(".")
            cur = con.execute(
                """INSERT INTO doc_images(doc_id, kind, status, title, context_note, caption_en, caption_hi,
                                          anchor_page, anchor_idx, license, provenance, created_at, updated_at)
                   VALUES(?,?,'draft',?,?,?,?,?,?,?,?,?,?)""",
                (did, args.kind, args.title, args.context, args.caption_en, args.caption_hi, int(pg), int(ix or 1),
                 args.license, json.dumps({"source_file": str(src.resolve()), "added_at": now()}), now(), now()))
            iid = cur.lastrowid
            con.execute("UPDATE doc_images SET lineage_id=id WHERE id=?", (iid,))
            folder = root / args.doc; folder.mkdir(parents=True, exist_ok=True)
            dest = folder / ("%d_v1%s" % (iid, src.suffix.lower() or ".png"))
            shutil.copy2(src, dest)
            data = dest.read_bytes()
            con.execute("UPDATE doc_images SET path=?, sha256=? WHERE id=?", (str(dest), hashlib.sha256(data).hexdigest(), iid))
            con.commit()
            print("added #%d -> %s (status draft; `approve %d` to publish)" % (iid, dest, iid)); return 0
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
