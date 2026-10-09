#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
corpus_media.py  (2026-10-09)  CORPUS_MEDIA_C8_2026_10_09

Puts the desk's pictures on the site, privately: the image library (doc_images, draft and
approved) and the graphic novels (doc_novels: the plan, and every page and cast sheet).
Design and commands: docs/MEDIA_AND_CORNER_2026-10-09.md. Schema: docs/cloud/C8_corpus_media_2026-10-09.sql.
Edge function: supabase/functions/corpus-media in the Srangam repo (docs/cloud/C8_corpus-media here).

What travels:
  - per picture, two JPEG renditions made here with Pillow: 'thumb' (480 px on the long side) and
    'display' (1600 px). The original stays on this PC. The renditions go, one request each, to
    the corpus-media edge function, which puts them in the Srangam Shared Drive, folder
    "Srangam corpus media", NOT shared by link. A rendition is uploaded once: it is named by the
    original's sha256, and the server is asked which ones it already has.
  - per picture, one row of corpus.media (caption, verse anchor, status, model, the label
    "generated, not a historical source", the generation prompt); per novel, one row of
    corpus.novels (title, the plan: pages with English and Hindi captions, citations, speech and
    the scene asked for; the citation check; status).
What stays here: the originals, briefs not yet drawn, retired pictures, stale novel pages.
Who sees what is decided by the database (C8), not here: readers see approved pictures and
approved novels; admins also see drafts and novels still being drawn.

How it is idempotent: every row gets row_hash = sha256 of its columns; corpus_media_state() gives
the server's (key, row_hash) and the renditions it has; only what differs is sent; a row whose
renditions are not all on Drive yet is HELD (not sent), so the site never lists a picture it
cannot show. A picture gone here is RETIRED there (never deleted); it comes back if it returns.
Read-only on context.db (mode=ro; immutable=1 with --immutable for a backup copy).

Sinks (as corpus_sync.py, with the same CORPUS_SYNC_SECRET, URL and publishable key):
  --sink edge   the corpus-media edge function (HMAC-signed requests; the service role and the
                Drive service account never leave Supabase).
  --sink pg     a PostgreSQL you own with C8 applied (--dsn or CORPUS_SYNC_DSN); uploads are
                recorded with a stand-in file id and nothing goes to Drive. For tests.
  --sink none   no network: what a first push would send (with --apply it makes the renditions
                and counts their size, and sends nothing).
  --sink auto   (default) edge when CORPUS_SYNC_SECRET is set, else none.

  python scripts\\corpus_media.py                      # plan only: what would be sent
  python scripts\\corpus_media.py --hello              # the function answers? (version, Drive key present)
  python scripts\\corpus_media.py --status             # what the site has against what is here
  python scripts\\corpus_media.py --apply              # send it
  python scripts\\corpus_media.py --apply --max-mb 40 --if-configured   # the scheduled step
  python scripts\\corpus_media.py --sink none --apply --db "D:\\backups\\context_20261009.db" --immutable
Test: python -m unittest tests.test_corpus_media_2026_10_09 -v
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import ntpath
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_sync as cs  # noqa: E402  (open_ro, live_docs, load_config, sign: one implementation)

MARK = "CORPUS_MEDIA_C8_2026_10_09"
SCHEME = "media.1"                 # must match corpus_media_state()'s "scheme"
CLIENT_VERSION = "1.0"
CLIENT = "corpus_media.py %s (%s)" % (CLIENT_VERSION, SCHEME)
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "context.db"
LOG_PATH = ROOT / "data" / "corpus_media_log.jsonl"
GENERATED_LABEL = "Illustration - generated, not a historical source."
RENDITIONS = (("thumb", 480, 80), ("display", 1600, 84))   # name, long side in px, JPEG quality
MAX_FILE_BYTES = 4_000_000          # the server takes up to 4 MiB a rendition
MEDIA_KINDS = ("generated", "cover", "edition-plate", "diagram", "photo")
NOVEL_STATUSES = ("plan", "drawing", "approved")
PICTURE_STATUSES = ("draft", "approved")
MAX_MEDIA_PER_CALL = 200            # server limit 500
MAX_NOVELS_PER_CALL = 20            # server limit 100; a plan is a few KB
MAX_TEXT = 4000                     # any one text field of a plan
PROV_KEYS = ("label", "source", "image_model", "brief_model", "prompt", "aspect", "size", "generated_at",
             "credit", "edition", "page", "story", "variant", "prompt_hash", "novel", "at")
MASS_RETIRE_SHARE = 0.5             # refuse to retire more than half of what the site has ...
MASS_RETIRE_MIN = 10                # ... when that is more than this many, unless --allow-mass-retire


class SinkError(RuntimeError):
    def __init__(self, msg: str, status: int | None = None):
        super().__init__(msg)
        self.status = status


class Budget(Exception):
    """Raised inside a run when --max-mb is reached; the next run carries on."""


# --------------------------------------------------------------------------- local side

def _int(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v if -2 ** 31 <= v < 2 ** 31 else None
    if isinstance(v, float) and v.is_integer():
        return _int(int(v))
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return _int(int(v.strip()))
    return None


def _text(v, limit: int = MAX_TEXT):
    v = cs._clean(v)
    if v is None:
        return None
    if not isinstance(v, str):
        v = str(v)
    v = v.strip()
    return v[:limit] if v else None


def _json(v) -> dict | list | None:
    if v is None or isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return None


def provenance(raw, extra: dict | None = None, label: str | None = GENERATED_LABEL) -> str:
    """The provenance the site may show: only the known keys (the prompt is one of them)."""
    p = _json(raw)
    p = p if isinstance(p, dict) else {}
    out = {k: p[k] for k in PROV_KEYS if k in p and p[k] not in (None, "")}
    out.update({k: v for k, v in (extra or {}).items() if v not in (None, "")})
    if label and not out.get("label"):
        out["label"] = label
    for k, v in list(out.items()):
        if isinstance(v, str):
            out[k] = _text(v, 6000)
        elif not isinstance(v, (int, float, bool)):
            out[k] = _text(json.dumps(v, ensure_ascii=False), 2000)
    return json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def resolve_path(p, root: Path = ROOT) -> Path | None:
    """The file of a picture: a relative path is under the repo; an absolute one is used as it is,
    else (written on another drive, or before a move) taken from its data\\images\\ part on."""
    if not p:
        return None
    s = str(p)
    cands = []
    if ntpath.isabs(s) or os.path.isabs(s):
        cands.append(Path(s))
        flat = s.replace("\\", "/")
        i = flat.lower().find("data/images/")
        if i >= 0:
            cands.append(root / flat[i:])
    else:
        cands.append(root / s.replace("\\", "/"))
    for c in cands:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(path: Path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return (None, None)


def row_hash(table: str, row: dict) -> str:
    s = json.dumps([SCHEME, table, row], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def trim_plan(plan) -> dict:
    p = _json(plan)
    p = p if isinstance(p, dict) else {}
    cast = []
    for c in (p.get("cast") or [])[:40]:
        if isinstance(c, dict):
            cast.append({"name": _text(c.get("name"), 200), "look": _text(c.get("look"))})
    pages = []
    for q in (p.get("pages") or [])[:200]:
        if not isinstance(q, dict) or _int(q.get("n")) is None:
            continue
        speech = []
        for sp in (q.get("speech") or [])[:20]:
            if isinstance(sp, dict):
                speech.append({"who": _text(sp.get("who"), 200), "line": _text(sp.get("line")),
                               "cite": _text(sp.get("cite"), 40)})
        cites = [c for c in (q.get("cites") or []) if isinstance(c, str) and len(c) <= 20][:100]
        pages.append({"n": _int(q.get("n")), "scene": _text(q.get("scene")), "caption": _text(q.get("caption")),
                      "caption_hi": _text(q.get("caption_hi")), "speech": speech, "cites": cites})
    return {"title": _text(p.get("title"), 500), "title_hi": _text(p.get("title_hi"), 500),
            "cast": cast, "pages": pages}


def trim_verify(v):
    v = _json(v)
    if not isinstance(v, dict):
        return None
    out = {"ok": v.get("ok") if isinstance(v.get("ok"), bool) else None,
           "problems": [_text(x, 500) for x in (v.get("problems") or [])[:20]],
           "cited": [c for c in (v.get("cited") or []) if isinstance(c, str) and len(c) <= 20][:400],
           "pages": _int(v.get("pages")), "checked_at": _text(v.get("checked_at"), 40)}
    return out


class Picture:
    """One picture to put on the site: its row (without row_hash) and its file here."""
    __slots__ = ("key", "row", "path", "doc", "novel")

    def __init__(self, key, row, path, doc, novel=None):
        self.key, self.row, self.path, self.doc, self.novel = key, row, path, doc, novel


def _sel(cols: set, want, alias: str) -> str:
    return ", ".join("%s.%s" % (alias, c) if c in cols else "NULL" for c in want)


IMG_COLS = ("kind", "status", "title", "caption_en", "caption_hi", "context_note", "anchor_page", "anchor_idx",
            "anchor_verse_ref", "version", "width", "height", "sha256", "model", "license", "provenance",
            "created_at", "approved_at", "retired_at", "path")
NOVEL_COLS = ("story_id", "status", "audience", "title", "title_hi", "pages", "plan", "verify", "cast_sheets",
              "page_images", "model", "image_model", "aspect", "provenance", "created_at", "updated_at",
              "approved_at")


def collect(con, docs, only=None, root: Path = ROOT):
    """-> (pictures {key: Picture}, novels {id: row}, notes [str], stats). `docs` as cs.live_docs().
    A picture whose file is missing here is kept on the site as it is (stats["keep"]), not retired."""
    code_of = {d[0]: d[1] for d in docs if not only or d[1] in only}
    pictures, novels, notes = {}, {}, []
    stats = {"briefs": 0, "retired": 0, "stale": 0, "keep": set()}   # keep: here but not ready; never retired

    def add(key, row, path, code, novel=None, recorded_sha=None):
        sha = file_sha256(path)
        if recorded_sha and recorded_sha != sha:
            notes.append("%s: the file is not the one recorded (sha256 differs); the file is sent" % key)
        row["sha256"] = sha
        if row.get("width") is None or row.get("height") is None:
            w, h = image_size(path)
            row["width"], row["height"] = _int(w), _int(h)
        pictures[key] = Picture(key, row, path, code, novel)

    if cs._has_table(con, "doc_images"):
        story_of = {}
        if cs._has_table(con, "doc_stories") and "image_id" in cs._cols(con, "doc_stories"):
            for iid, sid in con.execute("SELECT image_id, min(id) FROM doc_stories WHERE image_id IS NOT NULL "
                                        "GROUP BY image_id"):
                story_of[iid] = sid
        cols = cs._cols(con, "doc_images")
        for r in con.execute("SELECT i.id, i.doc_id, %s FROM doc_images i ORDER BY i.id" % _sel(cols, IMG_COLS, "i")):
            iid, did = r[0], r[1]
            v = dict(zip(IMG_COLS, r[2:]))
            code = code_of.get(did)
            if code is None:
                continue
            key = "img:%d" % iid
            if v["retired_at"] or v["status"] == "retired":
                stats["retired"] += 1
                continue
            if v["status"] not in PICTURE_STATUSES:
                stats["briefs"] += 1            # brief, brief-approved: nothing drawn yet
                continue
            kind = v["kind"] or "generated"
            if kind not in MEDIA_KINDS:
                notes.append("%s: kind %r is not one the site knows; left here" % (key, kind))
                stats["keep"].add(key)
                continue
            path = resolve_path(v["path"], root)
            if path is None:
                notes.append("%s: its file is missing (%s); left here" % (key, v["path"]))
                stats["keep"].add(key)
                continue
            label = GENERATED_LABEL if kind in ("generated", "cover") else None
            row = {"media_key": key, "doc_code": code, "kind": kind, "status": v["status"],
                   "title": _text(v["title"], 500), "caption_en": _text(v["caption_en"]),
                   "caption_hi": _text(v["caption_hi"]), "context_note": _text(v["context_note"]),
                   "anchor_page": _int(v["anchor_page"]), "anchor_idx": _int(v["anchor_idx"]),
                   "anchor_verse_ref": _text(v["anchor_verse_ref"], 100), "story_id": _int(story_of.get(iid)),
                   "novel_id": None, "seq": None, "version": _int(v["version"]), "width": _int(v["width"]),
                   "height": _int(v["height"]), "sha256": None, "model": _text(v["model"], 200),
                   "license": _text(v["license"], 200), "provenance": provenance(v["provenance"], label=label),
                   "created_at_local": _text(v["created_at"], 40), "approved_at_local": _text(v["approved_at"], 40)}
            add(key, row, path, code, recorded_sha=_text(v["sha256"], 64))

    if cs._has_table(con, "doc_novels"):
        cols = cs._cols(con, "doc_novels")
        for r in con.execute("SELECT n.id, n.doc_id, %s FROM doc_novels n ORDER BY n.id" % _sel(cols, NOVEL_COLS, "n")):
            nid, did = r[0], r[1]
            v = dict(zip(NOVEL_COLS, r[2:]))
            code = code_of.get(did)
            if code is None:
                continue
            if v["status"] not in NOVEL_STATUSES:
                if v["status"] != "retired":
                    notes.append("novel #%d: status %r is not one the site knows; left here" % (nid, v["status"]))
                continue
            plan = trim_plan(v["plan"])
            imodel = _text(v["image_model"], 200)
            novels[nid] = {
                "novel_id": nid, "doc_code": code, "story_id": _int(v["story_id"]), "status": v["status"],
                "audience": _text(v["audience"], 40), "title": _text(v["title"], 500) or plan["title"],
                "title_hi": _text(v["title_hi"], 500) or plan["title_hi"], "pages": _int(v["pages"]),
                "plan": plan, "verify": trim_verify(v["verify"]), "cover_seq": 1, "model": _text(v["model"], 200),
                "image_model": imodel, "aspect": _text(v["aspect"], 20),
                "provenance": provenance(v["provenance"], label=None),
                "created_at_local": _text(v["created_at"], 40), "updated_at_local": _text(v["updated_at"], 40),
                "approved_at_local": _text(v["approved_at"], 40)}
            for part, field in (("page", "page_images"), ("cast", "cast_sheets")):
                d = _json(v[field])
                for k, img in sorted((d if isinstance(d, dict) else {}).items(), key=lambda kv: _int(kv[0]) or 0):
                    seq = _int(k)
                    if seq is None or not 1 <= seq <= 999 or not isinstance(img, dict):
                        continue
                    key = "novel:%d:%s:%d" % (nid, part, seq)
                    st = img.get("status") or "draft"
                    if st == "stale":
                        stats["stale"] += 1     # no longer matches its scene; it is drawn again first
                        continue
                    if st not in PICTURE_STATUSES:
                        continue
                    path = resolve_path(img.get("path"), root)
                    if path is None:
                        notes.append("%s: its file is missing (%s); left here" % (key, img.get("path")))
                        stats["keep"].add(key)
                        continue
                    title = ("Page %d" % seq) if part == "page" else (_text(img.get("name"), 200) or "Figure %d" % seq)
                    row = {"media_key": key, "doc_code": code, "kind": "novel_" + part, "status": st, "title": title,
                           "caption_en": None, "caption_hi": None, "context_note": None, "anchor_page": None,
                           "anchor_idx": None, "anchor_verse_ref": None, "story_id": _int(v["story_id"]),
                           "novel_id": nid, "seq": seq, "version": _int(img.get("version")), "width": None,
                           "height": None, "sha256": None, "model": imodel, "license": None,
                           "provenance": provenance({}, {"novel": nid, "at": img.get("at")}),
                           "created_at_local": _text(img.get("at"), 40), "approved_at_local": None}
                    add(key, row, path, code, novel=nid, recorded_sha=_text(img.get("sha256"), 64))
    return pictures, novels, notes, stats


# --------------------------------------------------------------------------- renditions

def make_rendition(path: Path, max_px: int, quality: int):
    """-> (jpeg bytes, width, height). Never enlarges; transparency goes on white."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise SystemExit("corpus_media.py needs Pillow for the renditions: pip install pillow")
    with Image.open(path) as im0:
        im = ImageOps.exif_transpose(im0)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px), Image.LANCZOS)
        q = quality
        while True:
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
            data = buf.getvalue()
            if len(data) <= MAX_FILE_BYTES or q <= 50:
                break
            q -= 10
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("%s: the %d px rendition is still %d bytes at quality 50" % (path.name, max_px, len(data)))
        return data, im.size[0], im.size[1]


# --------------------------------------------------------------------------- sinks

class NoneSink:
    """No network. Behaves as an empty site that has every document, so the plan is a full push."""
    name = "none"

    def __init__(self, docs=()):
        self.docs = sorted(docs)

    def hello(self):
        return {"fn": "none"}

    def state(self):
        return {"scheme": SCHEME, "docs": self.docs, "media": {}, "novels": {}, "files": [], "drive_folder": None}

    def upsert_media(self, rows):
        return len(rows)

    def upsert_novels(self, rows):
        return len(rows)

    def retire(self, media, novels):
        return {"media": len(media), "novels": len(novels)}

    def upload(self, meta: dict, data: bytes):
        return {"uploaded": True, "file_id": "none"}


class PgSink:
    """A PostgreSQL you own with C8 applied. Uploads are recorded, not stored (no Drive)."""
    name = "pg"

    def __init__(self, dsn: str):
        self._pg = cs.PgSink(dsn)
        self.con = self._pg.con

    def _one(self, sql, args):
        try:
            return self._pg._one(sql, args)
        except cs.SinkError as e:
            raise SinkError(str(e))

    def hello(self):
        st = self.state()
        return {"fn": "pg", "pictures_in_mirror": len(st.get("media") or {})}

    def state(self):
        return self._one("SELECT public.corpus_media_state()", ())

    def upsert_media(self, rows):
        return self._one("SELECT public.corpus_media_upsert(%s::jsonb)",
                         (json.dumps(rows, ensure_ascii=False, separators=(",", ":")),))

    def upsert_novels(self, rows):
        return self._one("SELECT public.corpus_novels_upsert(%s::jsonb)",
                         (json.dumps(rows, ensure_ascii=False, separators=(",", ":")),))

    def retire(self, media, novels):
        return self._one("SELECT public.corpus_media_retire(%s::text[], %s::integer[])", (list(media), list(novels)))

    def upload(self, meta: dict, data: bytes):
        have = self._one("SELECT public.corpus_media_file_get(%s, %s)", (meta["sha256"], meta["rendition"]))
        if have:
            return {"skipped": True, "file_id": have.get("file_id")}
        row = dict(meta, storage="gdrive", file_id="pg-" + meta["file_sha256"][:32], bytes=len(data))
        put = self._one("SELECT to_jsonb(public.corpus_media_file_put(%s::jsonb))", (json.dumps(row),))
        return {"uploaded": True, "file_id": row["file_id"], "recorded": put is True}


class EdgeSink:
    name = "edge"

    def __init__(self, base_url: str, anon_key: str, secret: str, timeout: int = 150, retries: int = 3):
        self.url = base_url.rstrip("/") + "/functions/v1/corpus-media"
        self.anon, self.secret, self.timeout, self.retries = anon_key, secret, timeout, retries

    def _call(self, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        body = gzip.compress(raw, 6)
        last = None
        for attempt in range(self.retries):
            ts = str(int(time.time()))
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Content-Type": "application/octet-stream",
                "x-corpus-encoding": "gzip",
                "x-corpus-ts": ts,
                "x-corpus-sig": cs.sign(self.secret, ts, body),
                "apikey": self.anon,
                "Authorization": "Bearer " + self.anon,
            })
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                if not data.get("ok"):
                    raise SinkError("corpus-media: %s" % str(data.get("error"))[:400])
                return data.get("result"), len(body)
            except urllib.error.HTTPError as e:
                text = e.read()[:600].decode("utf-8", "replace")
                last = SinkError("corpus-media HTTP %d: %s" % (e.code, text), e.code)
                if e.code in (429, 500, 502, 503, 504) and attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = SinkError("corpus-media unreachable: %s" % e)
                if attempt + 1 < self.retries:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise last
        raise last or SinkError("corpus-media: no answer")

    def hello(self):
        return self._call({"action": "hello"})[0]

    def state(self):
        return self._call({"action": "state"})[0]

    def upsert_media(self, rows):
        return self._call({"action": "upsert_media", "rows": rows})[0]

    def upsert_novels(self, rows):
        return self._call({"action": "upsert_novels", "rows": rows})[0]

    def retire(self, media, novels):
        return self._call({"action": "retire", "media": list(media), "novels": list(novels)})[0]

    def upload(self, meta: dict, data: bytes):
        result, sent = self._call(dict(meta, action="upload", data=base64.b64encode(data).decode("ascii")))
        result = dict(result or {})
        result["_sent"] = sent
        return result


def make_sink(kind: str, cfg: dict, dsn: str | None = None, docs=()):
    if kind == "auto":
        kind = "edge" if cfg.get("secret") else "none"
    if kind == "none":
        return NoneSink(docs)
    if kind == "pg":
        d = dsn or cfg.get("dsn")
        if not d:
            raise SystemExit("--sink pg needs --dsn or CORPUS_SYNC_DSN")
        return PgSink(d)
    if kind == "edge":
        missing = [n for n, k in (("CORPUS_SYNC_SECRET", "secret"), ("the site URL", "url"),
                                  ("the publishable key", "anon")) if not cfg.get(k)]
        if missing:
            raise SystemExit("edge sink is not configured: missing %s (docs/CORPUS_MIRROR_2026-10-08.md, step 3)"
                             % ", ".join(missing))
        return EdgeSink(cfg["url"], cfg["anon"], cfg["secret"])
    raise SystemExit("unknown sink %r" % kind)


def not_ready(e: SinkError) -> str | None:
    """Why the site cannot take pictures yet (function not deployed, C8 not applied), or None."""
    msg = str(e)
    if e.status == 404 or "Requested function was not found" in msg:
        return "the corpus-media edge function is not deployed yet"
    if "corpus_media_state" in msg and ("Could not find" in msg or "does not exist" in msg or "PGRST202" in msg):
        return "C8 is not applied in the database yet"
    return None


# --------------------------------------------------------------------------- the run

class Run:
    def __init__(self, sink, apply: bool, max_bytes: int | None, allow_mass_retire=False, no_retire=False,
                 progress=None):
        self.sink, self.apply, self.max_bytes = sink, apply, max_bytes
        self.allow_mass_retire, self.no_retire = allow_mass_retire, no_retire
        self.t0 = time.time()
        self.bytes = 0
        self.say = progress or (lambda m: None)

    def _spent(self, n: int):
        self.bytes += n
        if self.max_bytes is not None and self.bytes >= self.max_bytes:
            raise Budget()

    def execute(self, pictures: dict, novels: dict, notes: list, stats: dict, only=None) -> dict:
        s = {"apply": self.apply, "sink": self.sink.name, "stopped": "done", "error": None,
             "here": {"pictures": len(pictures), "approved": sum(1 for p in pictures.values() if p.row["status"] == "approved"),
                      "novels": len(novels), "novel_pictures": sum(1 for p in pictures.values() if p.novel),
                      "briefs": stats.get("briefs", 0), "stale_pages": stats.get("stale", 0)},
             "files": {"needed": 0, "on_drive": 0, "to_upload": 0, "uploaded": 0, "skipped": 0, "bytes": 0},
             "media": {"upsert": 0, "changed": 0, "retire": 0, "retired": 0},
             "novels": {"upsert": 0, "changed": 0, "retire": 0, "retired": 0},
             "held": [], "notes": list(notes), "bytes": 0, "seconds": 0.0, "drive_folder": None}
        st = self.sink.state() or {}
        if st.get("scheme") != SCHEME:
            raise SinkError("the site answers scheme %r, this script speaks %r" % (st.get("scheme"), SCHEME))
        s["drive_folder"] = st.get("drive_folder")
        site_docs = set(st.get("docs") or [])
        have = set(st.get("files") or [])
        site_media = dict(st.get("media") or {})
        site_novels = {int(k): v for k, v in (st.get("novels") or {}).items()}

        # 1. what may go: the document must be in the mirror (corpus_sync.py puts it there)
        nov_ok = {}
        for nid, row in novels.items():
            if row["doc_code"] not in site_docs:
                s["held"].append("novel #%d: %s is not in the mirror yet (corpus_sync.py first)" % (nid, row["doc_code"]))
            else:
                nov_ok[nid] = row
        pics_ok = {}
        for key, p in pictures.items():
            if p.doc not in site_docs:
                s["held"].append("%s: %s is not in the mirror yet (corpus_sync.py first)" % (key, p.doc))
            elif p.novel is not None and p.novel not in nov_ok:
                s["held"].append("%s: its novel is held" % key)
            else:
                pics_ok[key] = p

        # 2. the renditions the site does not have, one upload each (a sha is uploaded once)
        need = []
        seen = set()
        for key in sorted(pics_ok):
            p = pics_ok[key]
            for name, px, q in RENDITIONS:
                k = "%s:%s" % (p.row["sha256"], name)
                if k in seen:
                    continue
                seen.add(k)
                if k in have:
                    s["files"]["on_drive"] += 1
                else:
                    need.append((k, p, name, px, q))
        s["files"]["needed"] = len(seen)
        s["files"]["to_upload"] = len(need)

        try:
            if self.apply:
                for i, (k, p, name, px, q) in enumerate(need, 1):
                    try:
                        data, w, h = make_rendition(p.path, px, q)
                    except (OSError, ValueError) as e:
                        s["held"].append("%s: the %s rendition could not be made (%s)" % (p.key, name, e))
                        continue
                    meta = {"sha256": p.row["sha256"], "rendition": name, "mime": "image/jpeg", "width": w,
                            "height": h, "file_sha256": hashlib.sha256(data).hexdigest()}
                    r = self.sink.upload(meta, data) or {}
                    if r.get("skipped"):
                        s["files"]["skipped"] += 1
                    else:
                        s["files"]["uploaded"] += 1
                    s["files"]["bytes"] += len(data)
                    have.add(k)
                    if i % 10 == 0 or i == len(need):
                        self.say("uploaded %d/%d renditions (%.1f MB)" % (i, len(need), s["files"]["bytes"] / 1e6))
                    self._spent(int(r.get("_sent") or len(data)))

            # 3. novels, then the pictures whose renditions are all there
            nrows = []
            for nid in sorted(nov_ok):
                row = dict(nov_ok[nid])
                row["row_hash"] = row_hash("novels", row)
                if site_novels.get(nid) != row["row_hash"]:
                    nrows.append(row)
            s["novels"]["upsert"] = len(nrows)
            mrows = []
            for key in sorted(pics_ok):
                p = pics_ok[key]
                missing = [n for n, _px, _q in RENDITIONS if "%s:%s" % (p.row["sha256"], n) not in have]
                row = dict(p.row)
                row["row_hash"] = row_hash("media", row)
                if site_media.get(key) == row["row_hash"]:
                    continue
                if missing and self.apply:
                    s["held"].append("%s: its %s rendition is not on Drive yet" % (key, " and ".join(missing)))
                    continue
                mrows.append(row)
            s["media"]["upsert"] = len(mrows)
            if self.apply:
                for i in range(0, len(nrows), MAX_NOVELS_PER_CALL):
                    s["novels"]["changed"] += int(self.sink.upsert_novels(nrows[i:i + MAX_NOVELS_PER_CALL]) or 0)
                for i in range(0, len(mrows), MAX_MEDIA_PER_CALL):
                    s["media"]["changed"] += int(self.sink.upsert_media(mrows[i:i + MAX_MEDIA_PER_CALL]) or 0)

            # 4. what is gone here is retired there (never with --doc: the site's state has no documents)
            if only or self.no_retire:
                s["notes"].append("retire skipped (%s)" % ("--doc" if only else "--no-retire"))
            else:
                gone_m = sorted(set(site_media) - set(pictures) - set(stats.get("keep") or ()))
                gone_n = sorted(set(site_novels) - set(novels))
                s["media"]["retire"], s["novels"]["retire"] = len(gone_m), len(gone_n)
                for what, gone, site in (("pictures", gone_m, site_media), ("novels", gone_n, site_novels)):
                    if (len(gone) > MASS_RETIRE_MIN and len(gone) > MASS_RETIRE_SHARE * len(site)
                            and not self.allow_mass_retire):
                        raise SinkError("refusing to retire %d of the site's %d %s: is --db the right database? "
                                        "(--allow-mass-retire if it is)" % (len(gone), len(site), what))
                if self.apply and (gone_m or gone_n):
                    r = self.sink.retire(gone_m, gone_n) or {}
                    s["media"]["retired"], s["novels"]["retired"] = int(r.get("media") or 0), int(r.get("novels") or 0)
        except Budget:
            s["stopped"] = "budget"
        s["bytes"] = self.bytes
        s["seconds"] = round(time.time() - self.t0, 1)
        return s


def print_summary(s: dict, out=print):
    h, f, m, n = s["here"], s["files"], s["media"], s["novels"]
    out("corpus_media %s  sink=%s  %s" % (CLIENT_VERSION, s["sink"], "SENT" if s["apply"] else "PLAN (nothing sent)"))
    out("  here: %d pictures (%d approved), %d of them in %d graphic novel(s); %d briefs not drawn, %d stale pages"
        % (h["pictures"], h["approved"], h["novel_pictures"], h["novels"], h["briefs"], h["stale_pages"]))
    out("  renditions: %d needed, %d on Drive already, %d to upload%s"
        % (f["needed"], f["on_drive"], f["to_upload"],
           (", %d uploaded (%.1f MB)" % (f["uploaded"], f["bytes"] / 1e6)) if s["apply"] else ""))
    out("  pictures: %d to add or update%s, %d to retire%s"
        % (m["upsert"], (" (%d changed)" % m["changed"]) if s["apply"] else "", m["retire"],
           (" (%d retired)" % m["retired"]) if s["apply"] else ""))
    out("  novels:   %d to add or update%s, %d to retire%s"
        % (n["upsert"], (" (%d changed)" % n["changed"]) if s["apply"] else "", n["retire"],
           (" (%d retired)" % n["retired"]) if s["apply"] else ""))
    for x in s["held"]:
        out("  HELD: " + x)
    for x in s["notes"]:
        out("  note: " + x)
    if s.get("drive_folder"):
        out("  Drive folder id: %s" % s["drive_folder"])
    out("  stopped=%s  %.1f s  %.1f MB sent%s" % (s["stopped"], s["seconds"], s["bytes"] / 1e6,
                                                 ("  ERROR: " + s["error"]) if s["error"] else ""))
    if s["stopped"] == "budget":
        out("  --max-mb reached; the next run carries on from here.")


def log_run(s: dict, path: Path = LOG_PATH):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = dict(s)
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec["client"] = CLIENT
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except OSError:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Put the desk's pictures and graphic novels on the site, privately (C8).")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--immutable", action="store_true", help="the --db file is a backup copy (adds immutable=1)")
    ap.add_argument("--sink", default="auto", choices=["auto", "edge", "pg", "none"])
    ap.add_argument("--dsn", default=None, help="for --sink pg (else CORPUS_SYNC_DSN)")
    ap.add_argument("--apply", action="store_true", help="send; without it only the plan is printed")
    ap.add_argument("--doc", action="append", default=[], help="only this document (repeatable); never retires")
    ap.add_argument("--max-mb", type=float, default=None, help="stop after sending about this many MB (resume next run)")
    ap.add_argument("--no-retire", action="store_true")
    ap.add_argument("--allow-mass-retire", action="store_true")
    ap.add_argument("--if-configured", action="store_true",
                    help="exit 0 quietly when the edge sink is not configured, the function is not deployed or C8 "
                         "is not applied (for the scheduled task)")
    ap.add_argument("--hello", action="store_true", help="check the sink answers, then exit")
    ap.add_argument("--status", action="store_true", help="what the site has against what is here, then exit")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    a = ap.parse_args(argv)
    try:   # the scheduled task pipes this into a log in the console's codepage: never fail on a character
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    cfg = cs.load_config()
    if a.if_configured and a.sink in ("auto", "edge") and not (cfg["secret"] and cfg["url"] and cfg["anon"]):
        print("corpus media: not configured (CORPUS_SYNC_SECRET); skipped")
        return 0
    con = None
    docs = []
    if not a.hello:
        con = cs.open_ro(a.db, a.immutable)
        docs = cs.live_docs(con)
    sink = make_sink(a.sink, cfg, a.dsn, [d[1] for d in docs])
    try:
        if a.hello:
            print(json.dumps(sink.hello()))
            return 0
        only = set(a.doc) if a.doc else None
        if only:
            missing = sorted(only - {d[1] for d in docs})
            if missing:
                print("not a live document here: %s" % ", ".join(missing))
                return 1
        pictures, novels, notes, stats = collect(con, docs, only)
        if a.status:
            st = sink.state() or {}
            files = set(st.get("files") or [])
            on = sum(1 for p in pictures.values()
                     if all("%s:%s" % (p.row["sha256"], n) in files for n, _p, _q in RENDITIONS))
            print("site:  %d pictures, %d novels, %d renditions on Drive; folder %s"
                  % (len(st.get("media") or {}), len(st.get("novels") or {}), len(files), st.get("drive_folder")))
            print("here:  %d pictures (%d with both renditions on Drive), %d novels"
                  % (len(pictures), on, len(novels)))
            return 0
        say = (lambda m: print("[%5.0fs] %s" % (time.time() - t0, m), flush=True))
        t0 = time.time()
        run = Run(sink, a.apply, None if a.max_mb is None else int(a.max_mb * 1e6), a.allow_mass_retire,
                  a.no_retire, None if a.json else say)
        s = run.execute(pictures, novels, notes, stats, only)
    except SinkError as e:
        why = not_ready(e)
        if why and a.if_configured:
            print("corpus media: %s; skipped" % why)
            return 0
        print("corpus_media: %s%s" % (e, (" (%s)" % why) if why else ""))
        if a.apply:
            log_run({"sink": sink.name, "apply": True, "stopped": "error", "error": str(e)[:500]})
        return 2
    print(json.dumps(s, indent=1, ensure_ascii=True)) if a.json else print_summary(s)
    if a.apply:
        log_run(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
