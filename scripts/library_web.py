#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
library_web.py  (2026-10-04)  SHELF_2026_10_04

The Shelf: a catalogue of every text, the way a reader's library shows it - grouped
under headers (collections), each book with its cover, its titles, its series
number, how far it is translated, and every edition that exists for it (HTML and
PDF exports, Booksmith builds), plus the reader and the image library one click away.

It is a VIEW over what the pipeline already produces; it creates nothing and runs no
job. Two small writes, both to human-edited config files, both with a backup:
  POST /api/shelf/title  a person-confirmed display title (configs/doc_titles.json)
  POST /api/shelf/move   which collection a text belongs to (configs/collections.json)

  GET  /shelf                       the page (scripts/shelf_static.html)
  GET  /api/shelf                   collections -> books (cached 60 s; ?fresh=1 to rebuild)
  GET  /api/shelf/file?name=X       an export file from exports/ (html or pdf only)

Registered from dashboard.py inside try/except (patch_shelf_2026_10_04.py), so a fault
here cannot stop the dashboard.
"""
from __future__ import annotations

import datetime
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collections_cfg as cc  # noqa: E402

MARK = "SHELF_2026_10_04"
CODE_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
FILE_RE = re.compile(r"^[\w.\-]+\.(html|pdf)$")


def _ro(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def measure(db: Path) -> dict:
    """{code: {...}} for live (not retired) docs. Read-only."""
    con = _ro(db)
    try:
        t = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        pc = {r[1] for r in con.execute("PRAGMA table_info(passages)")}
        scope = "AND COALESCE(p.text_type,'mula') NOT IN ('noise','frontmatter')" if "text_type" in pc else ""
        retired = set()
        if "doc_stage" in t:
            retired = {r[0] for r in con.execute("SELECT doc_code FROM doc_stage WHERE stage='retired'")}
        out = {}
        for code, cat, n, en in con.execute(
                f"""SELECT d.code, d.category, COUNT(p.id),
                           SUM(CASE WHEN TRIM(COALESCE(p.translation,''))<>'' THEN 1 ELSE 0 END)
                    FROM docs d LEFT JOIN passages p ON p.doc_id = d.id {scope}
                    GROUP BY d.id"""):
            if code in retired or code.endswith("-RETIRED"):
                continue
            out[code] = {"code": code, "category": cat or "", "passages": n or 0, "en": en or 0, "hi": 0,
                         "images_approved": 0, "cover_id": None}
        if "translations_l10n" in t:
            for code, n in con.execute(
                    f"""SELECT d.code, COUNT(*) FROM translations_l10n l JOIN passages p ON p.id = l.passage_id
                        JOIN docs d ON d.id = p.doc_id WHERE l.lang='hi' AND TRIM(COALESCE(l.translation,''))<>''
                        {scope} GROUP BY d.code"""):
                if code in out:
                    out[code]["hi"] = n
        if "doc_images" in t:
            for code, kind, n, newest in con.execute(
                    """SELECT d.code, COALESCE(i.kind,''), COUNT(*), MAX(i.id) FROM doc_images i
                       JOIN docs d ON d.id = i.doc_id WHERE i.status='approved' AND i.path IS NOT NULL
                       GROUP BY d.code, COALESCE(i.kind,'')"""):
                if code not in out:
                    continue
                if kind == "cover":
                    out[code]["cover_id"] = newest
                else:
                    out[code]["images_approved"] += n
        return out
    finally:
        con.close()


def editions(exports: Path, code: str, listing=None) -> list[dict]:
    rx = re.compile(r"^%s_\d+-\d+(?:_[a-z]+)*\.(html|pdf)$" % re.escape(code))
    out = []
    for p in (listing if listing is not None else (sorted(exports.iterdir()) if exports.is_dir() else [])):
        if p.is_file() and rx.match(p.name):
            st = p.stat()
            parts = p.stem.split("_")
            tags = [x for x in parts[len(code.split("_")) + 1:] if x]
            out.append({"name": p.name, "format": p.suffix[1:], "size": st.st_size,
                        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "tags": tags})
    out.sort(key=lambda e: (e["format"], e["name"]))
    return out


def build(db: Path, exports: Path, root: Path, bs_pdf=None, bs_modes=()) -> dict:
    m = measure(db)
    docs = [(c, v["category"]) for c, v in m.items()]
    cols, from_file = cc.resolve(docs, root / "configs" / "collections.json")
    titles = cc.load_titles(root / "configs" / "doc_titles.json")
    try:
        raw = json.loads((root / "configs" / "doc_titles.json").read_text(encoding="utf-8"))
        titles_sa = raw.get("titles_sa", {}) if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        titles_sa = {}
    listing = sorted(exports.iterdir()) if exports.is_dir() else []
    out_cols = []
    for c in cols:
        books = []
        for code in c["members"]:
            b = dict(m[code])
            b["title"] = titles.get(code) or cc.derived_title(code)
            b["title_confirmed"] = code in titles
            b["title_sa"] = titles_sa.get(code, "")
            b["series"] = cc.series_of(code)
            b["editions"] = editions(exports, code, listing)
            b["booksmith"] = []
            if bs_pdf:
                for mode in bs_modes:
                    try:
                        p, kind = bs_pdf(code, mode)
                    except Exception:
                        p, kind = None, None
                    if p:
                        b["booksmith"].append({"mode": mode, "kind": kind})
            books.append(b)
        out_cols.append({"key": c["key"], "title": c["title"], "title_sa": c["title_sa"], "books": books})
    keys = [{"key": k, "title": t} for k, t, _s, _o, _r in cc.COLLECTIONS] + [{"key": cc.OTHER[0], "title": cc.OTHER[1]}]
    return {"from_file": from_file, "collections": out_cols, "keys": keys, "built": time.time()}


def register(app, *, root, db=None, bs_pdf=None, bs_modes=()):
    from flask import jsonify, request, send_from_directory
    root = Path(root)
    dbp = Path(db) if db else root / "data" / "context.db"
    if not dbp.is_absolute():
        dbp = root / dbp
    exports = root / "exports"
    cache = {"data": None, "at": 0.0}

    def data(fresh=False):
        if fresh or cache["data"] is None or time.time() - cache["at"] > 60:
            cache["data"] = build(dbp, exports, root, bs_pdf, bs_modes)
            cache["at"] = time.time()
        return cache["data"]

    @app.get("/shelf")
    def shelf_page():
        return send_from_directory(str(root / "scripts"), "shelf_static.html")

    @app.get("/api/shelf")
    def shelf_api():
        try:
            return jsonify(data(request.args.get("fresh") == "1"))
        except Exception as e:
            return jsonify({"error": "%s: %s" % (type(e).__name__, e)}), 500

    @app.get("/api/shelf/file")
    def shelf_file():
        name = request.args.get("name", "")
        if not FILE_RE.match(name) or not (exports / name).is_file():
            return jsonify({"error": "not found"}), 404
        return send_from_directory(str(exports), name)

    @app.post("/api/shelf/title")
    def shelf_title():
        d = request.get_json(force=True) or {}
        code = d.get("code", "")
        if not CODE_RE.match(code):
            return jsonify({"error": "invalid code"}), 400
        title, title_sa = str(d.get("title") or "")[:200], str(d.get("title_sa") or "")[:200]
        if not (title.strip() or title_sa.strip()):
            return jsonify({"error": "nothing to save"}), 400
        cc.set_title(code, title, title_sa, root / "configs" / "doc_titles.json")
        cache["data"] = None
        return jsonify({"ok": True})

    @app.post("/api/shelf/move")
    def shelf_move():
        d = request.get_json(force=True) or {}
        code, key = d.get("code", ""), d.get("key", "")
        if not CODE_RE.match(code) or not CODE_RE.match(key):
            return jsonify({"error": "invalid"}), 400
        m = measure(dbp)
        if code not in m:
            return jsonify({"error": "unknown text"}), 404
        try:
            cc.move(code, key, [(c, v["category"]) for c, v in m.items()], root / "configs" / "collections.json")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        cache["data"] = None
        return jsonify({"ok": True})

    return app
