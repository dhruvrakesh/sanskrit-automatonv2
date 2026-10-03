#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
images_web.py  (2026-10-03)  IMAGES_UI_2026_10_03   (phase I2 of docs/EDITIONS_AND_IMAGES_2026-10-03.md)

The Images tab: a page at http://127.0.0.1:5057/images and a small JSON API,
registered onto the running dashboard's Flask app by register(). All library
logic lives in images.py; this module only exposes it.

  * Reads and small edits (captions, anchor, status) run in the request, with a
    30 s busy timeout, like every other dashboard writer of a few rows.
  * Anything that calls a model (propose ideas, generate, regenerate) is launched
    as a dashboard job through launch(), so it appears in the job list and
    data/jobs.jsonl, and the page polls /api/job/<id>.
  * Thumbnails (360 px JPEG) are made once and cached in data/images/<doc>/_thumbs/,
    so the grid loads fast however large the originals are.
Nothing here generates an image on view or on click of anything but "Generate".
"""
from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import images as lib  # noqa: E402

MARK = "IMAGES_UI_2026_10_03"
DOC_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
EDITABLE = {"title": "title", "brief": "brief", "context_note": "context_note", "caption_en": "caption_en",
            "caption_hi": "caption_hi", "license": "license"}
_DOCS_CACHE = {"at": 0.0, "data": None}


def _resolve(root: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (root / q)


def thumb_for(root: Path, row: dict, width: int = 360) -> Path | None:
    """Cached JPEG thumbnail for an image row; None if the row has no image file."""
    src = _resolve(root, row.get("path"))
    if not src or not src.exists():
        return None
    tdir = src.parent / "_thumbs"
    out = tdir / ("%d_v%d.jpg" % (row["id"], row.get("version") or 1))
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    try:
        from PIL import Image
        tdir.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, max(1, round(im.height * width / im.width))))
            im.save(out, "JPEG", quality=82)
        return out
    except Exception:
        return src


def register(app, *, launch, root, py, script, db=None):
    """Attach the Images page and API to `app`. `launch(kind, doc, argv)` starts a job."""
    from flask import jsonify, request, Response, send_from_directory

    root = Path(root)
    dbp = Path(db) if db else root / "data" / "context.db"
    if not dbp.is_absolute():
        dbp = root / dbp

    def con():
        c = lib._connect(str(dbp))
        lib.ensure_schema(c)
        return c

    def bad(msg, code=400):
        return jsonify({"error": msg}), code

    @app.get("/images")
    def images_page():
        return send_from_directory(str(root / "scripts"), "images_static.html")

    @app.get("/api/images/docs")
    def images_docs():
        if _DOCS_CACHE["data"] is None or time.time() - _DOCS_CACHE["at"] > 60:
            c = con()
            try:
                rows = c.execute("""SELECT d.code, COUNT(*) FROM passages p JOIN docs d ON d.id=p.doc_id
                                    WHERE TRIM(COALESCE(p.translation,''))<>'' GROUP BY d.code""").fetchall()
                _DOCS_CACHE["data"] = {r[0]: r[1] for r in rows}
                _DOCS_CACHE["at"] = time.time()
            finally:
                c.close()
        c = con()
        try:
            counts = {}
            for code, st, n in c.execute("""SELECT d.code, i.status, COUNT(*) FROM doc_images i
                                            JOIN docs d ON d.id=i.doc_id GROUP BY d.code, i.status"""):
                counts.setdefault(code, {})[st] = n
        finally:
            c.close()
        out = [{"doc": k, "translated": v, "images": counts.get(k, {})} for k, v in _DOCS_CACHE["data"].items()]
        out.sort(key=lambda d: (-sum(d["images"].values()), d["doc"].lower()))
        return jsonify(out)

    @app.get("/api/images/list")
    def images_list():
        doc = request.args.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        c = con()
        try:
            did = c.execute("SELECT id FROM docs WHERE code=?", (doc,)).fetchone()
            if not did:
                return bad("unknown doc", 404)
            c.row_factory = sqlite3.Row
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM doc_images WHERE doc_id=? ORDER BY anchor_page, anchor_idx, version", (did[0],))]
        finally:
            c.close()
        for r in rows:
            r["has_image"] = bool(r.get("path")) and bool((_resolve(root, r["path"]) or Path("")).exists())
            r.pop("provenance", None)
        return jsonify(rows)

    @app.get("/api/images/passage")
    def images_passage():
        doc = request.args.get("doc", "")
        try:
            page, idx = int(request.args.get("page", "")), int(request.args.get("idx", ""))
        except ValueError:
            return bad("page and idx must be integers")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        c = con()
        try:
            r = c.execute("""SELECT p.id, p.text, p.translation, l.translation FROM passages p JOIN docs d ON d.id=p.doc_id
                             LEFT JOIN translations_l10n l ON l.passage_id=p.id AND l.lang='hi'
                             WHERE d.code=? AND p.page_no=? AND p.idx=?""", (doc, page, idx)).fetchone()
        finally:
            c.close()
        if not r:
            return bad("no passage at %d.%d" % (page, idx), 404)
        return jsonify({"id": r[0], "sa": r[1], "en": r[2], "hi": r[3]})

    def _image_response(iid: int, thumb: bool):
        c = con()
        try:
            row = lib.get(c, iid)
        except SystemExit:
            return bad("not found", 404)
        finally:
            c.close()
        p = thumb_for(root, row) if thumb else _resolve(root, row.get("path"))
        if not p or not p.exists():
            return bad("no image file", 404)
        mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else (row.get("mime") or "image/png")
        resp = Response(p.read_bytes(), mimetype=mime)
        resp.headers["Cache-Control"] = "private, max-age=86400"
        return resp

    @app.get("/api/images/thumb/<int:iid>")
    def images_thumb(iid):
        return _image_response(iid, True)

    @app.get("/api/images/file/<int:iid>")
    def images_file(iid):
        return _image_response(iid, False)

    @app.post("/api/images/<int:iid>/edit")
    def images_edit(iid):
        data = request.get_json(force=True) or {}
        fields = {col: str(data[k]) for k, col in EDITABLE.items() if k in data and data[k] is not None}
        if "anchor" in data and data["anchor"]:
            m = re.match(r"^\s*(\d+)(?:\.(\d+))?\s*$", str(data["anchor"]))
            if not m:
                return bad("anchor must look like 66.2")
            fields["anchor_page"], fields["anchor_idx"] = int(m.group(1)), int(m.group(2) or 1)
        if not fields:
            return bad("nothing to change")
        c = con()
        try:
            row = lib.get(c, iid)
            lib.set_status(c, iid, row["status"], **fields)
            note = ("The idea changed after its image was made; use Regenerate for a new version."
                    if "brief" in fields and row["status"] in ("draft", "approved") else "")
            return jsonify({"ok": True, "note": note})
        except SystemExit as e:
            return bad(str(e), 404)
        finally:
            c.close()

    @app.post("/api/images/<int:iid>/action")
    def images_action(iid):
        act = (request.get_json(force=True) or {}).get("action")
        c = con()
        try:
            row = lib.get(c, iid)
            if act == "approve-brief":
                if row["status"] != "brief":
                    return bad("only an idea in 'brief' can be approved")
                lib.set_status(c, iid, "brief-approved")
            elif act == "approve":
                lib.approve(c, iid)
            elif act == "retire":
                lib.set_status(c, iid, "retired")
            elif act == "restore":
                if row["status"] != "retired":
                    return bad("only a retired row can be restored")
                lib.set_status(c, iid, "draft" if row.get("path") else "brief")
            else:
                return bad("unknown action")
            return jsonify({"ok": True, "status": lib.get(c, iid)["status"]})
        except SystemExit as e:
            return bad(str(e).replace("FAIL: ", ""))
        finally:
            c.close()

    @app.post("/api/images/dedupe")
    def images_dedupe():
        doc = (request.get_json(force=True) or {}).get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        c = con()
        try:
            res = lib.dedupe(c, doc, apply=True)
        finally:
            c.close()
        return jsonify({"retired": [r[0] for r in res]})

    def _job(kind, doc, argv, mode="all"):
        # mode is part of the dashboard's duplicate-job identity: generating image 3
        # must not be swallowed by a running generation of image 5.
        try:
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv), mode=mode)
        except TypeError:   # a dashboard without EXPORT_MODE_JOBLOG (no mode argument)
            jid = launch(kind, doc, py(script("images.py"), "--db", str(dbp), *argv))
        return jsonify({"job": jid})

    @app.post("/api/images/brief")
    def images_brief():
        data = request.get_json(force=True) or {}
        doc = data.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        n = max(1, min(int(data.get("max") or 6), lib.HARD_CAP))
        argv = ["brief", "--doc", doc, "--max", str(n), "--yes"] + (["--more"] if data.get("more") else [])
        return _job("images_brief", doc, argv)

    @app.post("/api/images/generate")
    def images_generate():
        data = request.get_json(force=True) or {}
        doc = data.get("doc", "")
        if not DOC_RE.match(doc):
            return bad("invalid doc")
        argv = ["generate", "--doc", doc, "--yes"]
        mode = "all"
        if data.get("id"):
            argv += ["--id", str(int(data["id"]))]
            mode = "id%d" % int(data["id"])
        return _job("images_gen", doc, argv, mode)

    @app.post("/api/images/<int:iid>/regenerate")
    def images_regenerate(iid):
        c = con()
        try:
            row = lib.get(c, iid)
            code = c.execute("SELECT code FROM docs WHERE id=?", (row["doc_id"],)).fetchone()[0]
        except SystemExit:
            return bad("not found", 404)
        finally:
            c.close()
        return _job("images_gen", code, ["regenerate", str(iid), "--yes"], "regen%d" % iid)

    return app
